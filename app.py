import csv
import ctypes
import ctypes.wintypes
import json
import os
import queue
import shutil
import sqlite3
import subprocess
import sys
import threading
import tkinter as tk
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

from floatvocab.db import DEFAULT_LANGUAGE_CODE, initialize_database, open_connection
from floatvocab.models import WordCard
from floatvocab.repositories import LexiconRepository, NewsRepository, PlanRepository, StudyRepository
from floatvocab.services import EnrichmentService as _BaseEnrichmentService
from floatvocab.services import NewsService, SettingsService, StudyService
import news_digest
from example_pipeline import enrich_database, fetch_dictionary_payload


APP_NAME = "FloatVocab"
APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
DATA_DIR = RESOURCE_ROOT / "data"
BUILTIN_LEXICON = DATA_DIR / "kaoyan_50.json"
VOCAB_SOURCE_DIR = DATA_DIR / "vocab_sources"
EXAM_LEXICONS = [
    ("初中词汇", "ChuZhong_3_T.json"),
    ("高中词汇", "GaoZhong_3_T.json"),
    ("考研词汇", "KaoYan_3_T.json"),
    ("大学英语四级 CET-4", "CET4_T.json"),
    ("大学英语六级 CET-6", "CET6_T.json"),
    ("英语专业四级 TEM-4", "Level4luan_2_T.json"),
    ("英语专业八级 TEM-8", "Level8luan_2_T.json"),
    ("托福 TOEFL", "TOEFL_3_T.json"),
    ("雅思 IELTS", "IELTS_3_T.json"),
    ("SAT", "SAT_3_T.json"),
    ("PTE WFD", "PTE_WFD.json"),
    ("PTE FIB Listening", "PTE_FIB_L.json"),
    ("PTE FIB Reading", "PTE_FIB_R_junior.json"),
]

STATUS_NEW = "new"
STATUS_FUZZY = "fuzzy"
STATUS_MASTERED = "mastered"

THEME = {
    "bg": "#F3F7FB",
    "panel": "#FAFCFF",
    "panel_alt": "#F0F5FA",
    "hero": "#E8F0F8",
    "border": "#D9E3EC",
    "text": "#1F2D3D",
    "muted": "#607287",
    "accent": "#5C7C99",
    "accent_active": "#496983",
    "accent_soft": "#DCE7F1",
    "success": "#21A366",
    "danger": "#EF6A6A",
    "warning": "#F2A93B",
    "heat_0": "#E8F1FB",
    "heat_1": "#CAE2FF",
    "heat_2": "#8FC2FF",
    "heat_3": "#3B90F7",
}


def extract_pronunciation_audio_url(payload) -> str | None:
    for entry in payload or []:
        phonetics = entry.get("phonetics")
        if not isinstance(phonetics, list):
            continue
        for item in phonetics:
            if not isinstance(item, dict):
                continue
            audio = str(item.get("audio") or "").strip()
            if audio:
                return audio
    return None


def resolve_pronunciation_audio_url(word: str, refresh: bool = False) -> str | None:
    normalized_word = str(word or "").strip()
    if not normalized_word:
        return None
    try:
        payload = fetch_dictionary_payload(normalized_word, refresh=refresh)
    except Exception:  # noqa: BLE001
        return None
    return extract_pronunciation_audio_url(payload)


def get_user_data_dir(app_name: str = APP_NAME, env: dict[str, str] | None = None, home: Path | None = None) -> Path:
    env = os.environ if env is None else env
    appdata_root = env.get("APPDATA") or env.get("LOCALAPPDATA")
    if appdata_root:
        return Path(appdata_root) / app_name
    home_root = Path.home() if home is None else home
    return home_root / f".{app_name.lower()}"


def get_default_db_path(
    *,
    app_root: Path = APP_ROOT,
    frozen: bool | None = None,
    env: dict[str, str] | None = None,
) -> Path:
    runtime_is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    if not runtime_is_frozen:
        return app_root / "floatvocab.db"
    return get_user_data_dir(env=env) / "floatvocab.db"


def prepare_runtime_storage(db_path: Path, legacy_db_path: Path | None = None) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not legacy_db_path or legacy_db_path == db_path or not legacy_db_path.exists() or db_path.exists():
        return
    for suffix in ("", "-wal", "-shm"):
        source = Path(f"{legacy_db_path}{suffix}")
        if source.exists():
            shutil.copy2(source, Path(f"{db_path}{suffix}"))


DB_PATH = get_default_db_path()
prepare_runtime_storage(DB_PATH, APP_ROOT / "floatvocab.db")


class EnrichmentService(_BaseEnrichmentService):
    def __init__(self, db_path: Path):
        super().__init__(db_path)

    def enrich_examples(self, lexicon_id=None, limit: int = 200, refresh: bool = False):
        return globals()["enrich_database"](self.db_path, limit=limit, refresh=refresh, lexicon_id=lexicon_id)


class FloatVocabDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = open_connection(db_path)
        initialize_database(
            self.conn,
            builtin_lexicon=BUILTIN_LEXICON,
            vocab_source_dir=VOCAB_SOURCE_DIR,
            exam_lexicons=EXAM_LEXICONS,
            qwerty_item_to_word=qwerty_item_to_word,
        )
        self.lexicon_repository = LexiconRepository(self.conn)
        self.plan_repository = PlanRepository(self.conn)
        self.study_repository = StudyRepository(
            self.conn,
            calculate_srs=calculate_srs,
            row_to_card=row_to_card,
        )
        self.news_repository = NewsRepository(self.conn)
    def create_lexicon(self, name: str, source: str = 'custom', language_code: str = DEFAULT_LANGUAGE_CODE) -> int:
        return self.lexicon_repository.create_lexicon(name, source, language_code)

    def supported_languages(self):
        return self.lexicon_repository.list_supported_languages()

    def get_lexicon(self, lexicon_id: int):
        return self.lexicon_repository.get_lexicon(lexicon_id)

    def update_lexicon(self, lexicon_id: int, name: str, language_code: str):
        return self.lexicon_repository.update_lexicon(lexicon_id, name, language_code)

    def delete_lexicon(self, lexicon_id: int):
        return self.lexicon_repository.delete_lexicon(lexicon_id)

    def import_words(
        self,
        file_path: str,
        current_language_code: str = DEFAULT_LANGUAGE_CODE,
    ) -> tuple[int, str, str]:
        path = Path(file_path)
        rows = self.parse_word_file(path)
        supported_codes = {code for code, _label in self.supported_languages()}
        explicit_language_code = next((str(row.get("language_code", "")).strip() for row in rows if str(row.get("language_code", "")).strip()), "")
        explicit_lexicon_name = next((str(row.get("lexicon_name", "")).strip() for row in rows if str(row.get("lexicon_name", "")).strip()), "")
        language_code = explicit_language_code or current_language_code
        if language_code not in supported_codes:
            raise ValueError(f"Unsupported language_code: {language_code}")
        lexicon_name = explicit_lexicon_name or path.stem
        imported = self.lexicon_repository.import_word_rows(lexicon_name, rows, "import", language_code)
        return imported, lexicon_name, language_code

    @staticmethod
    def parse_word_file(path: Path) -> list[dict]:
        if path.suffix.lower() == ".json":
            with path.open("r", encoding="utf-8-sig") as file:
                payload = json.load(file)
            if isinstance(payload, list):
                return [row for row in payload if isinstance(row, dict)]
            raise ValueError("JSON word list must be an array of objects")
        if path.suffix.lower() == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as file:
                sample = file.read(2048)
                file.seek(0)
                has_header = csv.Sniffer().has_header(sample)
                if has_header:
                    return list(csv.DictReader(file))
                reader = csv.reader(file)
                return [row_to_word_dict(row) for row in reader]
        rows = []
        with path.open("r", encoding="utf-8-sig") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                delimiter = "\t" if "\t" in line else ","
                rows.append(row_to_word_dict([part.strip() for part in line.split(delimiter)]))
        return rows

    def lexicons(self, language_code: str | None = None):
        return self.lexicon_repository.list_lexicons(language_code)

    def plan(self):
        return self.plan_repository.fetch_plan()

    def save_plan(
        self,
        lexicon_id: int,
        daily_new: int,
        target_date: str,
        alpha: float,
        font_size: int,
        bg_color: str,
        widget_size: str,
        current_language_code: str | None = None,
    ):
        self.plan_repository.save_plan(
            lexicon_id,
            daily_new,
            target_date,
            alpha,
            font_size,
            bg_color,
            widget_size,
            current_language_code=current_language_code,
        )

    def save_float_style(self, alpha: float, font_size: int, bg_color: str, widget_size: str):
        self.plan_repository.save_float_style(alpha, font_size, bg_color, widget_size)

    def set_current_language(self, language_code: str):
        plan = self.plan()
        current_lexicon = None
        if plan["lexicon_id"]:
            current_lexicon = self.lexicon_repository.get_lexicon(plan["lexicon_id"])
        if current_lexicon and current_lexicon["language_code"] == language_code:
            next_lexicon_id = current_lexicon["id"]
        else:
            first_lexicon = self.lexicon_repository.first_lexicon_for_language(language_code)
            next_lexicon_id = first_lexicon["id"] if first_lexicon else None
        self.plan_repository.set_current_language(language_code, next_lexicon_id)
        return self.plan()

    def next_card(self) -> WordCard | None:
        return self.study_repository.next_card()

    def review(self, word_id: int, rating: int):
        self.study_repository.review(word_id, rating)

    def stats(self):
        return self.study_repository.stats()

    def missing_examples_count(self, lexicon_id: int | None = None) -> int:
        return self.study_repository.missing_examples_count(lexicon_id)

    def recent_words(self, lexicon_id: int, limit: int = 80):
        return self.lexicon_repository.recent_words(lexicon_id, limit)


def row_to_word_dict(row):
    cells = list(row) + ["", "", "", ""]
    return {"word": cells[0], "phonetic": cells[1], "meaning": cells[2], "example": cells[3]}


def qwerty_item_to_word(item: dict, lexicon_name: str) -> dict | None:
    word = str(item.get("name") or item.get("word") or "").strip()
    if not word:
        return None
    trans = item.get("trans")
    if isinstance(trans, list):
        meaning = "；".join(str(part).strip() for part in trans if str(part).strip())
    else:
        meaning = str(item.get("meaning") or item.get("translation") or "").strip()
    if not meaning:
        meaning = f"{lexicon_name} 词条"
    phonetic = str(item.get("usphone") or item.get("ukphone") or item.get("phonetic") or "").strip()
    if phonetic and not (phonetic.startswith("/") and phonetic.endswith("/")):
        phonetic = f"/{phonetic}/"
    example = str(item.get("sentence") or item.get("example") or "").strip()
    return {
        "word": word,
        "phonetic": phonetic,
        "meaning": meaning,
        "example": example,
    }


def row_to_card(row) -> WordCard:
    return WordCard(
        id=row["id"],
        word=row["word"],
        phonetic=row["phonetic"] or "",
        meaning=row["meaning"],
        example=row["example"] or "",
        status=row["status"],
        lexicon_name=row["lexicon_name"],
    )


def calculate_srs(row, rating: int):
    quality = max(0, min(5, int(rating)))
    ease = float(row["ease_factor"] or 2.5)
    repetitions = int(row["repetitions"] or 0)
    interval = int(row["interval_days"] or 0)
    if quality < 3:
        repetitions = 0
        interval = 1
    else:
        repetitions += 1
        if repetitions == 1:
            interval = 1
        elif repetitions == 2:
            interval = 2
        elif repetitions == 3:
            interval = 4
        else:
            interval = max(1, round(interval * ease))
        ease = max(1.3, ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
    return {
        "ease_factor": round(ease, 2),
        "repetitions": repetitions,
        "interval_days": interval,
        "next_review_date": (date.today() + timedelta(days=interval)).isoformat(),
    }


class FloatingWindow(tk.Toplevel):
    SIZE_PRESETS = {
        "small": (300, 210, 260),
        "medium": (380, 270, 340),
        "large": (500, 350, 460),
    }
    CORNER_RADIUS = 18

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.card: WordCard | None = None
        self.flipped = False
        self.move_start_x = 0
        self.move_start_y = 0
        self.move_window_x = 0
        self.move_window_y = 0
        self.resize_start_x = 0
        self.resize_start_y = 0
        self.resize_start_width = 0
        self.resize_start_height = 0
        self.round_after_id = None
        self.withdraw()
        self.title("FloatVocab Desktop Widget")
        self.attributes("-topmost", False)
        self.overrideredirect(True)
        self.geometry("380x270+960+120")

        self.panel_frame = tk.Frame(self, padx=20, pady=18, bd=0, relief="flat")
        self.panel_frame.pack(fill="both", expand=True)
        self.panel_frame.columnconfigure(0, weight=1)
        self.panel_frame.rowconfigure(1, weight=1)

        self.header_frame = tk.Frame(self.panel_frame, bd=0, relief="flat", cursor="fleur")
        self.header_frame.grid(row=0, column=0, sticky="ew")
        self.header_frame.columnconfigure(0, weight=1)
        self.card_header = tk.Label(self.header_frame, text="FloatVocab", anchor="w")
        self.card_header.grid(row=0, column=0, sticky="ew")
        self.card_subtitle = tk.Label(self.header_frame, text="", anchor="w")
        self.card_subtitle.grid(row=1, column=0, sticky="ew", pady=(4, 0))

        self.content_frame = tk.Frame(self.panel_frame, bd=0, relief="flat")
        self.content_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1, minsize=40)
        self.word_row = tk.Frame(self.content_frame, bd=0, relief="flat")
        self.word_row.grid(row=0, column=0, sticky="nsew")
        self.word_row.columnconfigure(0, weight=1)
        self.word_group = tk.Frame(self.word_row, bd=0, relief="flat")
        self.word_group.grid(row=0, column=0)
        self.word_label = tk.Label(self.word_group, text="", font=("Segoe UI", 28, "bold"), wraplength=320, justify="center")
        self.word_label.pack(side="left")
        self.pronunciation_button = tk.Button(
            self.word_group,
            text="🔊",
            command=lambda: self.play_pronunciation(),
            width=2,
            relief="flat",
            bd=0,
            cursor="hand2",
            takefocus=0,
        )
        self.pronunciation_button.pack(side="left", padx=(8, 0))
        self.detail_label = tk.Label(self.content_frame, text="", wraplength=320, justify="center", anchor="n")
        self.detail_label.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        self.action_frame = tk.Frame(self.panel_frame)
        self.action_frame.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.unknown_button = tk.Button(self.action_frame, text="不认识", command=self.mark_unknown, width=9)
        self.unknown_button.pack(side="left")
        self.flip_button = tk.Button(self.action_frame, text="翻面", command=self.flip, width=9)
        self.flip_button.pack(side="left", expand=True)
        self.known_button = tk.Button(self.action_frame, text="认识", command=self.mark_known, width=9)
        self.known_button.pack(side="right")
        self.hint_label = tk.Label(
            self.panel_frame,
            text=self.build_shortcut_hint(),
            font=("Segoe UI", 9),
        )
        self.hint_label.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.drag_bar = tk.Frame(self.panel_frame, height=10, cursor="fleur")
        self.drag_bar.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.resize_grip = tk.Label(self, text="◢", anchor="se", cursor="size_nw_se", font=("Segoe UI", 10), bd=0)
        self.resize_grip.place(relx=1.0, rely=1.0, x=0, y=0, anchor="se")

        self.bind("<space>", lambda _event: self.flip())
        self.bind("<Right>", lambda _event: self.mark_known())
        self.bind("<Left>", lambda _event: self.mark_unknown())
        self.bind("<Escape>", lambda _event: self.withdraw())
        self.bind("<Configure>", self.on_configure)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        for widget in [
            self.panel_frame,
            self.header_frame,
            self.card_header,
            self.card_subtitle,
            self.content_frame,
            self.word_row,
            self.word_group,
            self.word_label,
            self.detail_label,
            self.drag_bar,
            self.hint_label,
        ]:
            widget.bind("<ButtonPress-1>", self.start_move)
            widget.bind("<B1-Motion>", self.move)
        self.resize_grip.bind("<ButtonPress-1>", self.start_resize)
        self.resize_grip.bind("<B1-Motion>", self.resize)

    def build_header_text(self) -> str:
        if not self.card:
            return "FloatVocab · 准备开始"
        return "FloatVocab · 当前学习卡"

    def build_header_subtitle(self) -> str:
        if not self.card:
            return "拖动卡片开始今天的复习。"
        if self.flipped:
            return "释义面 · 左右键快速判断。"
        return "正面 · 点击翻面查看释义。"

    def build_shortcut_hint(self) -> str:
        return "快捷键：Space 翻面 · ← 不认识 · → 认识"

    def apply_style(self):
        plan = self.app.settings_service.get_plan_settings()
        bg = plan["bg_color"]
        surface_bg = THEME["panel"]
        alpha = float(plan["float_alpha"])
        font_size = int(plan["font_size"])
        widget_size = plan["widget_size"] if "widget_size" in plan.keys() else "medium"
        width, height, wraplength = self.SIZE_PRESETS.get(widget_size, self.SIZE_PRESETS["medium"])
        word_font_size = int(font_size)
        detail_font_size = max(11, font_size // 2)
        if widget_size == "small":
            word_font_size = min(word_font_size, 22)
            detail_font_size = min(detail_font_size, 12)
        elif widget_size == "medium":
            word_font_size = min(word_font_size, 28)
            detail_font_size = min(detail_font_size, 14)
        self.widget_size = widget_size
        self.word_font_size = word_font_size
        self.detail_font_size = detail_font_size
        self.attributes("-alpha", alpha)
        if self.winfo_width() <= 1 or self.winfo_height() <= 1:
            self.geometry(self.widget_geometry(width, height))
        self.configure(bg=bg)
        self.panel_frame.configure(bg=bg, padx=28, pady=24)
        for widget in [self.header_frame, self.content_frame, self.action_frame, self.word_row, self.word_group]:
            widget.configure(bg=bg)
        self.drag_bar.configure(bg=THEME["panel_alt"], height=8)
        self.card_header.configure(bg=bg, fg=THEME["muted"], font=("Segoe UI", 11, "bold"), text=self.build_header_text())
        self.card_subtitle.configure(bg=bg, fg=THEME["muted"], font=("Segoe UI", 9), text=self.build_header_subtitle())
        self.word_label.configure(bg=bg, fg=THEME["text"])
        self.detail_label.configure(bg=bg, fg=THEME["muted"])
        self.hint_label.configure(bg=bg, fg=THEME["muted"], font=("Segoe UI", 8), text=self.build_shortcut_hint())
        self.resize_grip.configure(bg=bg, fg=THEME["muted"])
        self.unknown_button.configure(
            bg="#FFF2F2",
            fg=THEME["danger"],
            activebackground="#FFE4E4",
            activeforeground=THEME["danger"],
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
        )
        self.flip_button.configure(
            bg=THEME["accent_soft"],
            fg=THEME["accent_active"],
            activebackground="#CBE2FF",
            activeforeground=THEME["accent_active"],
            relief="flat",
            bd=0,
            padx=18,
            pady=8,
        )
        self.known_button.configure(
            bg="#EAF8F1",
            fg=THEME["success"],
            activebackground="#D8F2E4",
            activeforeground=THEME["success"],
            relief="flat",
            bd=0,
            padx=16,
            pady=8,
        )
        self.pronunciation_button.configure(
            bg=surface_bg,
            fg=THEME["muted"],
            activebackground=THEME["panel_alt"],
            activeforeground=THEME["accent_active"],
            font=("Segoe UI Symbol", max(11, detail_font_size)),
            padx=2,
            pady=0,
        )
        self.update_wraplength(wraplength)
        self.word_label.configure(font=("Segoe UI", word_font_size, "bold"))
        self.detail_label.configure(font=("Segoe UI", detail_font_size))

    def show_next(self):
        self.card = self.app.study_service.get_next_card()
        self.flipped = False
        self.apply_style()
        self.render()
        self.deiconify()
        self.lift()
        self.focus_force()

    def widget_geometry(self, width: int, height: int):
        x = max(20, self.winfo_x())
        y = max(20, self.winfo_y())
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        if x > screen_width - width - 20:
            x = screen_width - width - 24
        if y > screen_height - height - 48:
            y = screen_height - height - 48
        return f"{width}x{height}+{x}+{y}"

    def update_wraplength(self, minimum_wraplength: int = 220):
        wraplength = max(minimum_wraplength, self.winfo_width() - 44)
        self.word_label.configure(wraplength=wraplength)
        self.detail_label.configure(wraplength=wraplength)

    def on_configure(self, _event=None):
        self.update_wraplength()
        if self.round_after_id:
            self.after_cancel(self.round_after_id)
        self.round_after_id = self.after(30, self.apply_rounded_corners)

    def apply_rounded_corners(self):
        self.round_after_id = None
        if not sys.platform.startswith("win"):
            return
        width = max(1, self.winfo_width())
        height = max(1, self.winfo_height())
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
        region = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, self.CORNER_RADIUS, self.CORNER_RADIUS)
        ctypes.windll.user32.SetWindowRgn(hwnd, region, True)

    def start_move(self, event):
        self.move_start_x = event.x_root
        self.move_start_y = event.y_root
        self.move_window_x = self.winfo_x()
        self.move_window_y = self.winfo_y()

    def move(self, event):
        dx = event.x_root - self.move_start_x
        dy = event.y_root - self.move_start_y
        x = max(0, min(self.move_window_x + dx, self.winfo_screenwidth() - self.winfo_width()))
        y = max(0, min(self.move_window_y + dy, self.winfo_screenheight() - self.winfo_height() - 40))
        self.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root
        self.resize_start_width = self.winfo_width()
        self.resize_start_height = self.winfo_height()

    def resize(self, event):
        width = max(280, self.resize_start_width + event.x_root - self.resize_start_x)
        height = max(190, self.resize_start_height + event.y_root - self.resize_start_y)
        self.geometry(f"{width}x{height}")

    def render(self):
        self.card_header.configure(text=self.build_header_text())
        self.card_subtitle.configure(text=self.build_header_subtitle())
        if not self.card:
            self.pronunciation_button.configure(state="disabled")
            self.word_label.configure(text="今天没有待复习单词")
            self.detail_label.configure(text="可以回到主界面导入词库，或者明天再来继续学习。")
            return
        has_audio = bool(self.resolve_pronunciation_audio_url(self.card.word.strip()))
        self.pronunciation_button.configure(state="normal" if has_audio else "disabled")
        if self.flipped:
            if self.should_use_compact_flipped_layout():
                self.word_label.configure(font=("Segoe UI", self.word_font_size, "bold"))
                self.word_label.configure(text=self.card.word)
                self.detail_label.configure(text=self.build_flipped_detail(include_example=False))
            else:
                meaning_font_size = max(self.detail_font_size, min(self.word_font_size, 18))
                self.word_label.configure(font=("Segoe UI", meaning_font_size, "bold"))
                self.word_label.configure(text=self.card.word)
                self.detail_label.configure(text=self.build_flipped_detail(include_example=True, include_meaning=True))
        else:
            self.word_label.configure(font=("Segoe UI", self.word_font_size, "bold"))
            self.word_label.configure(text=self.card.word)
            detail = self.card.phonetic
            if self.card.example:
                detail = f"{detail}\n{self.card.example}" if detail else self.card.example
            self.detail_label.configure(text=detail)

    def build_flipped_detail(self, include_example: bool = True, include_meaning: bool = True) -> str:
        lines = []
        if self.card.phonetic:
            lines.append(self.card.phonetic)
        meaning = self.format_meaning_lines(self.card.meaning) if include_meaning else ""
        if meaning:
            lines.append(meaning)
        if include_example and self.card.example:
            lines.append(self.card.example)
        return "\n".join(lines)

    def should_use_compact_flipped_layout(self) -> bool:
        meaning_groups = len(self.format_meaning_lines(self.card.meaning).splitlines())
        if self.widget_size == "small":
            return meaning_groups >= 2 or len(self.card.meaning) >= 18
        if self.widget_size == "medium":
            return meaning_groups >= 3 or len(self.card.meaning) >= 30
        return meaning_groups >= 4 or len(self.card.meaning) >= 48

    @staticmethod
    def format_meaning_lines(meaning: str) -> str:
        normalized = (
            meaning.replace("；", ";")
            .replace("，", ",")
            .replace("、", ",")
        )
        parts = [part.strip() for part in normalized.replace(";", ",").split(",") if part.strip()]
        if len(parts) <= 2:
            return meaning.strip()
        grouped = ["；".join(parts[index:index + 2]) for index in range(0, len(parts), 2)]
        return "\n".join(grouped)

    def flip(self):
        self.flipped = not self.flipped
        self.render()

    def play_pronunciation(self):
        if not self.card or not self.card.word.strip():
            return
        word = self.card.word.strip()
        audio_url = self.resolve_pronunciation_audio_url(word)
        if not audio_url:
            return
        threading.Thread(target=self._play_audio_url, args=(audio_url,), daemon=True).start()

    def resolve_pronunciation_audio_url(self, word: str) -> str | None:
        return resolve_pronunciation_audio_url(word)

    def _play_audio_url(self, audio_url: str):
        if not audio_url:
            return
        if sys.platform.startswith("win"):
            escaped_audio_url = audio_url.replace("'", "''")
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-NonInteractive",
                    "-Command",
                    (
                        "$player = New-Object -ComObject WMPlayer.OCX.7; "
                        f"$player.URL = '{escaped_audio_url}'; "
                        "$player.controls.play(); "
                        "$deadline = (Get-Date).AddSeconds(10); "
                        "while ($player.playState -ne 1 -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 200 }; "
                        "$player.close()"
                    ),
                ],
                startupinfo=startupinfo,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return
        self.bell()
    def mark_known(self):
        if self.card:
            self.app.study_service.submit_review(self.card.id, 4)
        self.app.refresh_all()
        self.show_next()

    def mark_unknown(self):
        if self.card:
            self.app.study_service.submit_review(self.card.id, 2)
        self.app.refresh_all()
        self.show_next()


class DailyArticleWindow(tk.Toplevel):
    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.article_id: int | None = None
        self.move_start_x = 0
        self.move_start_y = 0
        self.move_window_x = 0
        self.move_window_y = 0
        self.withdraw()
        self.title("日报内容")
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.geometry("560x640+980+90")

        self.container = tk.Frame(self, bd=0, relief="flat", bg=THEME["panel"])
        self.container.pack(fill="both", expand=True)
        self.header = tk.Frame(self.container, bg=THEME["hero"], height=48)
        self.header.pack(fill="x")
        self.title_label = tk.Label(self.header, text="日报内容", anchor="w", bg=THEME["hero"], fg=THEME["text"], font=("Segoe UI", 13, "bold"))
        self.title_label.pack(side="left", fill="x", expand=True, padx=18, pady=11)
        self.hide_label = tk.Label(self.header, text="收起", anchor="e", bg=THEME["hero"], fg=THEME["muted"], cursor="hand2", font=("Segoe UI", 10, "bold"))
        self.hide_label.pack(side="right", padx=18)

        self.meta_label = tk.Label(
            self.container,
            text="",
            anchor="w",
            justify="left",
            bg=THEME["panel"],
            fg=THEME["muted"],
            padx=18,
            pady=12,
            font=("Segoe UI", 10),
        )
        self.meta_label.pack(fill="x")

        self.text = tk.Text(
            self.container,
            wrap="word",
            bg=THEME["panel"],
            fg=THEME["text"],
            bd=0,
            padx=18,
            pady=14,
            relief="flat",
            highlightthickness=0,
            font=("Segoe UI", 11),
            spacing1=4,
            spacing2=4,
            spacing3=8,
        )
        self.text.pack(fill="both", expand=True)
        self.text.configure(state="disabled")

        for widget in [self.header, self.title_label, self.meta_label]:
            widget.bind("<ButtonPress-1>", self.start_move)
            widget.bind("<B1-Motion>", self.move)
        self.hide_label.bind("<Button-1>", lambda _event: self.withdraw())
        self.bind("<Escape>", lambda _event: self.withdraw())
        self.bind("<FocusOut>", lambda _event: self.after(120, self.hide_if_focus_lost))

    def show_article(self, article):
        self.article_id = article["id"]
        self.title_label.configure(text=article["title"])
        meta = f"{article['source_name']}  {article['published_at']}\n{article['url']}"
        self.meta_label.configure(text=meta)
        self.set_text(article["bilingual_text"] or article["content_text"])
        self.deiconify()
        self.lift()
        self.focus_force()

    def set_text(self, content: str):
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", content)
        self.text.configure(state="disabled")
        self.text.yview_moveto(0.0)

    def start_move(self, event):
        self.move_start_x = event.x_root
        self.move_start_y = event.y_root
        self.move_window_x = self.winfo_x()
        self.move_window_y = self.winfo_y()

    def move(self, event):
        dx = event.x_root - self.move_start_x
        dy = event.y_root - self.move_start_y
        x = max(0, min(self.move_window_x + dx, self.winfo_screenwidth() - self.winfo_width()))
        y = max(0, min(self.move_window_y + dy, self.winfo_screenheight() - self.winfo_height() - 40))
        self.geometry(f"+{x}+{y}")

    def hide_if_focus_lost(self):
        if not self.winfo_viewable():
            return
        if self.app.root.state() == "iconic":
            return
        if self.focus_displayof() is None and self.foreground_is_outside_app():
            self.withdraw()

    def foreground_is_outside_app(self):
        if not sys.platform.startswith("win"):
            return True
        foreground = ctypes.windll.user32.GetForegroundWindow()
        app_windows = {self.winfo_id(), self.app.root.winfo_id(), self.app.float_window.winfo_id()}
        return foreground not in app_windows


class GlobalHotkeys:
    MOD_ALT = 0x0001
    VK_LEFT = 0x25
    VK_RIGHT = 0x27
    VK_SPACE = 0x20
    WM_HOTKEY = 0x0312

    def __init__(self, event_queue: queue.Queue):
        self.event_queue = event_queue
        self.enabled = sys.platform.startswith("win")
        self.thread = None

    def start(self):
        if not self.enabled:
            return
        self.thread = threading.Thread(target=self.run, daemon=True)
        self.thread.start()

    def run(self):
        user32 = ctypes.windll.user32
        hotkeys = {
            1: self.VK_RIGHT,
            2: self.VK_LEFT,
            3: self.VK_SPACE,
        }
        for hotkey_id, key in hotkeys.items():
            user32.RegisterHotKey(None, hotkey_id, self.MOD_ALT, key)
        msg = ctypes.wintypes.MSG()
        try:
            while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
                if msg.message == self.WM_HOTKEY:
                    self.event_queue.put(int(msg.wParam))
        finally:
            for hotkey_id in hotkeys:
                user32.UnregisterHotKey(None, hotkey_id)


class FloatVocabApp:
    def __init__(
        self,
        db: FloatVocabDB | None = None,
        settings_service: SettingsService | None = None,
        study_service: StudyService | None = None,
        news_service: NewsService | None = None,
        enrichment_service: EnrichmentService | None = None,
    ):
        self.db = db or FloatVocabDB(DB_PATH)
        self.settings_service = settings_service or SettingsService(self.db)
        self.study_service = study_service or StudyService(self.db)
        service_db_path = getattr(self.db, "db_path", DB_PATH)
        self.news_service = news_service or NewsService(service_db_path)
        self.enrichment_service = enrichment_service or EnrichmentService(service_db_path)
        self.root = tk.Tk()
        self._root_destroy = self.root.destroy
        self.root.destroy = self.close
        self.poll_after_id = None
        self.closed = False
        self.configure_root()
        self.hotkey_events = queue.Queue()
        self.hotkeys = GlobalHotkeys(self.hotkey_events)
        self.loading_plan = False
        self.style_after_id = None
        self.configure_styles()
        self.float_window = FloatingWindow(self)
        self.article_window = DailyArticleWindow(self)
        self.build_ui()
        self.refresh_all()
        self.hotkeys.start()
        self.poll_after_id = self.root.after(120, self.poll_hotkeys)

    def configure_root(self):
        self.root.title("FloatVocab 悬浮背词")
        self.root.geometry("1180x860")
        self.root.minsize(1080, 760)
        self.root.configure(bg=THEME["bg"])

    def configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.root.option_add("*Font", "{Segoe UI} 10")
        self.style.configure("App.TFrame", background=THEME["bg"])
        self.style.configure("Panel.TFrame", background=THEME["panel"])
        self.style.configure("Hero.TFrame", background=THEME["hero"])
        self.style.configure("PanelTitle.TLabel", background=THEME["panel"], foreground=THEME["text"], font=("Segoe UI", 12, "bold"))
        self.style.configure("HeroTitle.TLabel", background=THEME["hero"], foreground=THEME["text"], font=("Segoe UI", 24, "bold"))
        self.style.configure("HeroBody.TLabel", background=THEME["hero"], foreground=THEME["muted"], font=("Segoe UI", 10))
        self.style.configure("WorkbenchTitle.TLabel", background=THEME["bg"], foreground=THEME["text"], font=("Segoe UI", 15, "bold"))
        self.style.configure("SectionLabel.TLabel", background=THEME["panel"], foreground=THEME["muted"], font=("Segoe UI", 9, "bold"))
        self.style.configure("Body.TLabel", background=THEME["panel"], foreground=THEME["text"], font=("Segoe UI", 10))
        self.style.configure("Muted.TLabel", background=THEME["panel"], foreground=THEME["muted"], font=("Segoe UI", 9))
        self.style.configure("Summary.TLabel", background=THEME["panel"], foreground=THEME["text"], font=("Segoe UI", 11, "bold"))
        self.style.configure(
            "Primary.TButton",
            background=THEME["accent"],
            foreground="#FFFFFF",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10, "bold"),
            padding=(16, 10),
        )
        self.style.map("Primary.TButton", background=[("active", THEME["accent_active"])], foreground=[("disabled", "#DCE7F7")])
        self.style.configure(
            "Secondary.TButton",
            background=THEME["panel_alt"],
            foreground=THEME["accent_active"],
            bordercolor=THEME["border"],
            focusthickness=0,
            padding=(14, 10),
        )
        self.style.map("Secondary.TButton", background=[("active", THEME["accent_soft"])])
        self.style.configure(
            "Quiet.TButton",
            background=THEME["panel"],
            foreground=THEME["text"],
            bordercolor=THEME["border"],
            focusthickness=0,
            padding=(12, 9),
        )
        self.style.map("Quiet.TButton", background=[("active", "#F6FAFF")])
        self.style.configure(
            "App.Horizontal.TProgressbar",
            troughcolor="#E3EEF9",
            background=THEME["accent"],
            bordercolor="#E3EEF9",
            lightcolor=THEME["accent"],
            darkcolor=THEME["accent"],
        )
        self.style.configure(
            "Treeview",
            background=THEME["panel"],
            fieldbackground=THEME["panel"],
            foreground=THEME["text"],
            rowheight=30,
            bordercolor=THEME["border"],
            lightcolor=THEME["panel"],
            darkcolor=THEME["panel"],
        )
        self.style.map("Treeview", background=[("selected", THEME["accent_soft"])], foreground=[("selected", THEME["text"])])
        self.style.configure(
            "Treeview.Heading",
            background=THEME["panel_alt"],
            foreground=THEME["text"],
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            padding=(8, 8),
        )
        self.style.map("Treeview.Heading", background=[("active", "#E4F0FF")])
        self.style.configure(
            "TCombobox",
            fieldbackground=THEME["panel"],
            background=THEME["panel"],
            bordercolor=THEME["border"],
            lightcolor=THEME["border"],
            darkcolor=THEME["border"],
            arrowsize=16,
            padding=6,
        )
        self.style.configure(
            "TEntry",
            fieldbackground=THEME["panel"],
            bordercolor=THEME["border"],
            lightcolor=THEME["border"],
            darkcolor=THEME["border"],
            padding=6,
        )
        self.style.configure(
            "TSpinbox",
            fieldbackground=THEME["panel"],
            bordercolor=THEME["border"],
            lightcolor=THEME["border"],
            darkcolor=THEME["border"],
            padding=6,
        )
        self.style.configure(
            "Horizontal.TScale",
            background=THEME["panel"],
            troughcolor="#DCE8F5",
            bordercolor=THEME["panel"],
            lightcolor=THEME["accent"],
            darkcolor=THEME["accent"],
        )
        self.style.configure("TNotebook", background=THEME["panel"], borderwidth=0, tabmargins=(0, 0, 0, 0))
        self.style.configure(
            "TNotebook.Tab",
            background=THEME["panel_alt"],
            foreground=THEME["muted"],
            padding=(16, 10),
            borderwidth=0,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", THEME["panel"]), ("active", THEME["accent_soft"])],
            foreground=[("selected", THEME["text"]), ("active", THEME["text"])],
        )

    def create_panel(self, parent, title: str, subtitle: str | None = None):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        panel.title_label = ttk.Label(panel, text=title, style="PanelTitle.TLabel")
        panel.title_label.pack(anchor="w")
        if subtitle:
            ttk.Label(panel, text=subtitle, style="Muted.TLabel", wraplength=460, justify="left").pack(anchor="w", pady=(4, 14))
        return panel
    def build_dashboard_summary_text(self) -> str:
        stats = self.study_service.get_study_stats()
        if not stats:
            return "今天还没有学习记录，先开始一轮复习。"
        summary = stats["summary"]
        total = summary["total"] or 0
        mastered = summary["mastered"] or 0
        due = summary["due"] or 0
        percent = round((mastered / total) * 100) if total else 0
        return f"今日待复习 {due} 个，已掌握 {percent}%"

    def build_dashboard_intro_text(self) -> str:
        return "今天先完成复习，再决定是否调整计划和样式。"

    @staticmethod
    def plan_value(plan, key: str, default=None):
        if not plan:
            return default
        try:
            value = plan[key]
        except (KeyError, TypeError, IndexError):
            if hasattr(plan, "get"):
                value = plan.get(key, default)
            else:
                value = default
        return default if value is None else value

    def build_dashboard_badge_items(self) -> list[tuple[str, str]]:
        stats = self.study_service.get_study_stats()
        summary = stats["summary"] if stats else {}
        total = (summary["total"] or 0) if summary else 0
        mastered = (summary["mastered"] or 0) if summary else 0
        due = (summary["due"] or 0) if summary else 0
        percent = round((mastered / total) * 100) if total else 0

        plan = self.settings_service.get_plan_settings()
        lexicon_name = "未选择"
        lexicon_id = self.plan_value(plan, "lexicon_id")
        if lexicon_id:
            lexicon = self.db.get_lexicon(lexicon_id)
            if lexicon:
                lexicon_name = lexicon["name"]
        return [("今日待复习", str(due)), ("已掌握", f"{percent}%"), ("当前词库", lexicon_name)]

    def build_dashboard_focus_steps(self) -> list[tuple[str, str, str]]:
        stats = self.study_service.get_study_stats()
        summary = stats["summary"] if stats else {}
        due = (summary["due"] or 0) if summary else 0
        plan = self.settings_service.get_plan_settings()
        daily_new = self.plan_value(plan, "daily_new", 20)
        lexicon_id = self.plan_value(plan, "lexicon_id")
        lexicon_name = "先选一个词库"
        if lexicon_id:
            lexicon = self.db.get_lexicon(lexicon_id)
            if lexicon:
                lexicon_name = lexicon["name"]
        return [
            ("01", "先清今日复习", f"把 {due} 个待复习先处理掉，今天的记忆负担会马上变轻。"),
            ("02", "再推进新词", f"当前词库：{lexicon_name}，然后按计划补充 {daily_new} 个新词。"),
            ("03", "最后调顺手感", "如果卡片太淡、太小或节奏不顺，就去右侧把悬浮窗样式调顺手。"),
        ]

    def build_plan_snapshot_items(self) -> list[tuple[str, str]]:
        plan = self.settings_service.get_plan_settings()
        language_code = self.plan_value(plan, "current_language_code", DEFAULT_LANGUAGE_CODE)
        language_map = dict(self.settings_service.list_supported_languages())
        language_name = language_map.get(language_code, language_code)
        lexicon_name = "未选择"
        lexicon_id = self.plan_value(plan, "lexicon_id")
        if lexicon_id:
            lexicon = self.db.get_lexicon(lexicon_id)
            if lexicon:
                lexicon_name = lexicon["name"]
        daily_new = self.plan_value(plan, "daily_new", 20)
        target_date = self.plan_value(plan, "target_date", "")
        target_text = f"{daily_new} 个/天"
        if target_date:
            target_text = f"{target_text} · 截止 {target_date}"
        return [
            ("学习语言", language_name),
            ("当前词库", lexicon_name),
            ("学习节奏", target_text),
        ]

    def build_style_snapshot_items(self) -> list[tuple[str, str]]:
        plan = self.settings_service.get_plan_settings()
        alpha = self.plan_value(plan, "float_alpha", 0.88)
        font_size = self.plan_value(plan, "font_size", 26)
        bg_color = self.plan_value(plan, "bg_color", "#F7FAF5")
        widget_size = str(self.plan_value(plan, "widget_size", "medium")).upper()
        return [
            ("透明度", f"{round(float(alpha) * 100)}%"),
            ("字号", f"{font_size} px"),
            ("卡片尺寸", f"{widget_size} · {bg_color}"),
        ]

    def build_stats_progress_text(self, stats: dict | None) -> str:
        if not stats:
            return "今天还没有学习记录，先开始一轮复习。"
        summary = stats["summary"]
        total = summary["total"] or 0
        mastered = summary["mastered"] or 0
        percent = round((mastered / total) * 100) if total else 0
        return f"完成度 {percent}% · 已掌握 {mastered}/{total} · 模糊 {summary['fuzzy'] or 0} · 今日待复习 {summary['due'] or 0}"

    def build_stats_spotlight_items(self, stats: dict | None) -> list[tuple[str, str]]:
        if not stats:
            return [("今日待复习", "0"), ("模糊词", "0"), ("活跃天数", "0/30")]
        summary = stats["summary"]
        active_days = sum(1 for row in stats["days"] if (row["reviewed"] or 0) > 0)
        return [
            ("今日待复习", str(summary["due"] or 0)),
            ("模糊词", str(summary["fuzzy"] or 0)),
            ("活跃天数", f"{active_days}/30"),
        ]

    def build_heatmap_caption_text(self, stats: dict | None) -> str:
        if not stats:
            return "最近 30 天还没有学习记录，热力图会在你开始复习后亮起来。"
        total_reviews = sum(row["reviewed"] or 0 for row in stats["days"])
        active_days = sum(1 for row in stats["days"] if (row["reviewed"] or 0) > 0)
        return f"最近 30 天累计复习 {total_reviews} 次，有记录的学习日是 {active_days} 天。"

    def build_words_overview_text(self) -> str:
        plan = self.settings_service.get_plan_settings()
        language_code = self.plan_value(plan, "current_language_code", DEFAULT_LANGUAGE_CODE)
        language_map = dict(self.settings_service.list_supported_languages())
        language_name = language_map.get(language_code, language_code)
        lexicon_name = "未选择词库"
        lexicon_id = self.plan_value(plan, "lexicon_id")
        if lexicon_id:
            lexicon = self.db.get_lexicon(lexicon_id)
            if lexicon:
                lexicon_name = lexicon["name"]
        return f"当前正在浏览{language_name} · {lexicon_name}，最近更新的词条会显示在这里。"

    def build_news_overview_items(self) -> list[tuple[str, str]]:
        plan = self.settings_service.get_plan_settings()
        language_code = self.plan_value(plan, "current_language_code", DEFAULT_LANGUAGE_CODE)
        language_map = dict(self.settings_service.list_supported_languages())
        language_name = language_map.get(language_code, language_code)
        return [
            ("当前语言", language_name),
            ("内容节奏", "最新 10 篇"),
            ("操作入口", "收藏并翻译"),
        ]

    def build_words_action_hint(self) -> str:
        return "切换词库后列表会立刻刷新，适合快速扫一遍最近新增或刚复习过的词条。"

    def build_news_action_hint(self) -> str:
        return "先刷新，再选中条目预览；觉得合适就直接收藏并翻译。"

    def build_words_tab_title(self, language_name: str) -> str:
        return f"{language_name} 词库概览"

    def refresh_dashboard_overview(self):
        if hasattr(self, "hero_summary_label"):
            self.hero_summary_label.configure(text=self.build_dashboard_summary_text())
        if hasattr(self, "hero_intro_label"):
            self.hero_intro_label.configure(text=self.build_dashboard_intro_text())
        badge_items = self.build_dashboard_badge_items()
        for index, (_label_text, value_text) in enumerate(badge_items):
            if index < len(getattr(self, "hero_badge_value_labels", [])):
                self.hero_badge_value_labels[index].configure(text=value_text)
        step_items = self.build_dashboard_focus_steps()
        for index, (_step_no, title_text, body_text) in enumerate(step_items):
            if index < len(getattr(self, "dashboard_focus_title_labels", [])):
                self.dashboard_focus_title_labels[index].configure(text=title_text)
            if index < len(getattr(self, "dashboard_focus_body_labels", [])):
                self.dashboard_focus_body_labels[index].configure(text=body_text)
        plan_items = self.build_plan_snapshot_items()
        for index, (_label_text, value_text) in enumerate(plan_items):
            if index < len(getattr(self, "plan_snapshot_value_labels", [])):
                self.plan_snapshot_value_labels[index].configure(text=value_text)
        style_items = self.build_style_snapshot_items()
        for index, (_label_text, value_text) in enumerate(style_items):
            if index < len(getattr(self, "style_snapshot_value_labels", [])):
                self.style_snapshot_value_labels[index].configure(text=value_text)
        if hasattr(self, "words_overview_label"):
            self.words_overview_label.configure(text=self.build_words_overview_text())
        news_items = self.build_news_overview_items()
        for index, (_label_text, value_text) in enumerate(news_items):
            if index < len(getattr(self, "news_overview_value_labels", [])):
                self.news_overview_value_labels[index].configure(text=value_text)

    def build_metric_items(self, stats: dict | None) -> list[tuple[str, str]]:
        if not stats:
            return [("今日待复习", "0"), ("已掌握", "0"), ("总词数", "0")]
        summary = stats["summary"]
        return [
            ("今日待复习", str(summary["due"] or 0)),
            ("已掌握", str(summary["mastered"] or 0)),
            ("总词数", str(summary["total"] or 0)),
        ]

    def build_heatmap_legend_items(self) -> list[tuple[str, str]]:
        return [
            ("较少", THEME["heat_0"]),
            ("稳定", THEME["heat_1"]),
            ("投入", THEME["heat_2"]),
            ("高强度", THEME["heat_3"]),
        ]

    def build_news_titles_for_language(self, language_name: str) -> tuple[str, str]:
        return (f"{language_name} 最新阅读", f"{language_name} 收藏夹")

    def build_lexicon_state_text(self, has_lexicons: bool) -> str:
        if has_lexicons:
            return "当前语言下已有词库，可以直接继续学习。"
        return "这个语言下还没有词库，先导入一个词包再开始。"

    def build_brief_preview_parts(self, row: dict) -> tuple[str, str, str, str]:
        saved = "已收藏" if row["saved"] else "可收藏并翻译"
        published = (row["published_at"] or "").replace("T", " ")[:16]
        title = row["title"]
        meta = f"{row['source_name']} · {published} · {saved}"
        summary = row["summary"]
        footer = f"双击条目或收藏后可在阅读窗查看全文。\n{row['url']}"
        return title, meta, summary, footer

    def build_brief_empty_state(self, *, has_lexicons: bool) -> tuple[str, str, str, str]:
        title = "今天还没有新内容"
        meta = "这个语言还没有配置日报源，或者今天还没有抓到新内容。"
        summary = "这个语言还没有配置日报源，或者今天还没有抓到新内容。"
        footer = "你可以稍后刷新，或者先切回学习计划继续复习。"
        if not has_lexicons:
            footer = "你可以先导入词库，或者切回学习计划继续复习。"
        return title, meta, summary, footer

    def format_brief_preview(self, row: dict) -> str:
        title, meta, summary, footer = self.build_brief_preview_parts(row)
        return (
            f"{title}\n"
            f"{meta}\n\n"
            f"{summary}\n\n"
            f"{footer}"
        )

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        shell = ttk.Frame(self.root, style="App.TFrame", padding=20)
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        hero = ttk.Frame(shell, style="Hero.TFrame", padding=22)
        hero.grid(row=0, column=0, sticky="ew")
        hero.columnconfigure(0, weight=1)
        self.hero_title_label = ttk.Label(hero, text="FloatVocab", style="HeroTitle.TLabel")
        self.hero_title_label.grid(row=0, column=0, sticky="w")
        self.hero_kicker_label = ttk.Label(
            hero,
            text="今日学习区",
            style="HeroBody.TLabel",
        )
        self.hero_kicker_label.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.hero_body_label = ttk.Label(
            hero,
            text="安静、克制的桌面学习空间，让今天的词汇计划和阅读内容更容易进入状态。",
            style="HeroBody.TLabel",
        )
        self.hero_body_label.grid(row=2, column=0, sticky="w", pady=(4, 0))
        self.hero_summary_label = ttk.Label(
            hero,
            text=self.build_dashboard_summary_text(),
            style="PanelTitle.TLabel",
        )
        self.hero_summary_label.grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.hero_intro_label = ttk.Label(
            hero,
            text=self.build_dashboard_intro_text(),
            style="HeroBody.TLabel",
        )
        self.hero_intro_label.grid(row=4, column=0, sticky="w", pady=(6, 0))
        hero_actions = ttk.Frame(hero, style="Hero.TFrame")
        hero_actions.grid(row=0, column=1, rowspan=5, sticky="e")
        ttk.Button(hero_actions, text="继续复习", style="Primary.TButton", command=self.float_window.show_next).pack(side="left", padx=(0, 10))
        ttk.Button(hero_actions, text="刷新日报", style="Secondary.TButton", command=self.refresh_daily_briefs).pack(side="left")
        hero_badges = ttk.Frame(hero, style="Hero.TFrame")
        hero_badges.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        self.hero_badge_value_labels: list[ttk.Label] = []
        for index, (label_text, value_text) in enumerate(self.build_dashboard_badge_items()):
            badge = ttk.Frame(hero_badges, style="Panel.TFrame", padding=(14, 12))
            badge.grid(row=0, column=index, padx=(0, 12), sticky="w")
            ttk.Label(badge, text=label_text, style="SectionLabel.TLabel").pack(anchor="w")
            value_label = ttk.Label(badge, text=value_text, style="PanelTitle.TLabel")
            value_label.pack(anchor="w", pady=(4, 0))
            self.hero_badge_value_labels.append(value_label)

        self.content_notebook = ttk.Notebook(shell)
        self.content_notebook.grid(row=1, column=0, sticky="nsew", pady=(18, 0))

        dashboard_tab = ttk.Frame(self.content_notebook, style="App.TFrame", padding=8)
        dashboard_tab.columnconfigure(0, weight=1)
        dashboard_tab.columnconfigure(1, weight=1)
        dashboard_tab.rowconfigure(3, weight=1)
        self.content_notebook.add(dashboard_tab, text="工作台")

        self.workbench_title_label = ttk.Label(dashboard_tab, text="今日学习", style="WorkbenchTitle.TLabel")
        self.workbench_title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        focus_box = self.create_panel(dashboard_tab, "今日路线", "首页先告诉你今天怎么学，再去碰设置和样式。")
        focus_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 18))
        focus_strip = ttk.Frame(focus_box, style="Panel.TFrame")
        focus_strip.pack(fill="x")
        self.dashboard_focus_title_labels: list[ttk.Label] = []
        self.dashboard_focus_body_labels: list[ttk.Label] = []
        for index, (step_no, title_text, body_text) in enumerate(self.build_dashboard_focus_steps()):
            card = ttk.Frame(focus_strip, style="Panel.TFrame", padding=(16, 14))
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 12 if index < 2 else 0))
            focus_strip.columnconfigure(index, weight=1)
            ttk.Label(card, text=step_no, style="SectionLabel.TLabel").pack(anchor="w")
            title_label = ttk.Label(card, text=title_text, style="PanelTitle.TLabel")
            title_label.pack(anchor="w", pady=(8, 0))
            body_label = ttk.Label(card, text=body_text, style="Muted.TLabel", wraplength=220, justify="left")
            body_label.pack(anchor="w", pady=(6, 0))
            self.dashboard_focus_title_labels.append(title_label)
            self.dashboard_focus_body_labels.append(body_label)

        plan_box = self.create_panel(dashboard_tab, "学习设置", "先确定词库和每日目标，再进入今天的背词节奏。")
        self.plan_box_title_label = plan_box.title_label
        plan_box.grid(row=2, column=0, sticky="nsew", padx=(0, 10))
        plan_snapshot = ttk.Frame(plan_box, style="Panel.TFrame")
        plan_snapshot.pack(fill="x", pady=(0, 14))
        self.plan_snapshot_value_labels: list[ttk.Label] = []
        for index, (label_text, value_text) in enumerate(self.build_plan_snapshot_items()):
            item = ttk.Frame(plan_snapshot, style="Hero.TFrame", padding=(14, 12))
            item.grid(row=0, column=index, sticky="nsew", padx=(0, 10 if index < 2 else 0))
            plan_snapshot.columnconfigure(index, weight=1)
            ttk.Label(item, text=label_text, style="SectionLabel.TLabel").pack(anchor="w")
            value_label = ttk.Label(item, text=value_text, style="PanelTitle.TLabel")
            value_label.pack(anchor="w", pady=(4, 0))
            self.plan_snapshot_value_labels.append(value_label)
        self.language_var = tk.StringVar()
        self.lexicon_var = tk.StringVar()
        plan_form = ttk.Frame(plan_box, style="Panel.TFrame")
        plan_form.pack(fill="x")
        plan_form.columnconfigure(0, weight=1)
        plan_form.columnconfigure(1, weight=1)
        ttk.Label(plan_form, text="学习语言", style="SectionLabel.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(plan_form, text="当前词库", style="SectionLabel.TLabel").grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 6))
        self.language_combo = ttk.Combobox(plan_form, textvariable=self.language_var, state="readonly")
        self.language_combo.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.language_combo.bind("<<ComboboxSelected>>", self.on_language_selected)
        self.lexicon_combo = ttk.Combobox(plan_form, textvariable=self.lexicon_var, state="readonly")
        self.lexicon_combo.bind("<<ComboboxSelected>>", lambda _event: self.refresh_words())
        self.lexicon_combo.grid(row=1, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(plan_form, text="目标日期", style="SectionLabel.TLabel").grid(row=2, column=0, sticky="w", pady=(14, 6))
        ttk.Label(plan_form, text="每日新词", style="SectionLabel.TLabel").grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(14, 6))
        self.target_date_var = tk.StringVar()
        ttk.Entry(plan_form, textvariable=self.target_date_var).grid(row=3, column=0, sticky="ew", padx=(0, 6))
        self.daily_new_var = tk.IntVar(value=20)
        ttk.Spinbox(plan_form, from_=1, to=300, textvariable=self.daily_new_var).grid(row=3, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(plan_form, text="状态", style="SectionLabel.TLabel").grid(row=4, column=0, sticky="w", pady=(14, 6))
        ttk.Label(plan_form, text="导入提示", style="SectionLabel.TLabel").grid(row=4, column=1, sticky="w", padx=(12, 0), pady=(14, 6))
        self.lexicon_state_label = ttk.Label(plan_form, text="", style="Muted.TLabel", wraplength=240, justify="left")
        self.lexicon_state_label.grid(row=5, column=0, sticky="w")
        self.import_language_label = ttk.Label(plan_form, text="", style="Muted.TLabel", wraplength=240, justify="left")
        self.import_language_label.grid(row=5, column=1, sticky="w", padx=(12, 0))
        self.example_status_label = ttk.Label(plan_form, text="", style="Muted.TLabel")
        self.example_status_label.grid(row=6, column=0, columnspan=2, sticky="w", pady=(12, 0))
        plan_actions = ttk.Frame(plan_box, style="Panel.TFrame")
        plan_actions.pack(fill="x", pady=(16, 0))
        ttk.Button(plan_actions, text="保存计划", style="Primary.TButton", command=self.save_plan).pack(side="left")
        ttk.Button(plan_actions, text="导入词库", style="Secondary.TButton", command=self.import_words).pack(side="left", padx=(10, 0))
        ttk.Button(plan_actions, text="重命名", style="Quiet.TButton", command=self.edit_selected_lexicon).pack(side="left", padx=(18, 0))
        ttk.Button(plan_actions, text="删除", style="Quiet.TButton", command=self.delete_selected_lexicon).pack(side="left", padx=(10, 0))
        ttk.Button(plan_actions, text="补全缺失例句", style="Quiet.TButton", command=self.enrich_examples).pack(side="left", padx=(10, 0))

        style_box = self.create_panel(dashboard_tab, "阅读外观", "调整透明度、字号和背景，让桌面复习卡片更顺眼。")
        self.style_box_title_label = style_box.title_label
        style_box.grid(row=2, column=1, sticky="nsew", padx=(10, 0))
        style_snapshot = ttk.Frame(style_box, style="Panel.TFrame")
        style_snapshot.pack(fill="x", pady=(0, 14))
        self.style_snapshot_value_labels: list[ttk.Label] = []
        for index, (label_text, value_text) in enumerate(self.build_style_snapshot_items()):
            item = ttk.Frame(style_snapshot, style="Hero.TFrame", padding=(14, 12))
            item.grid(row=0, column=index, sticky="nsew", padx=(0, 10 if index < 2 else 0))
            style_snapshot.columnconfigure(index, weight=1)
            ttk.Label(item, text=label_text, style="SectionLabel.TLabel").pack(anchor="w")
            value_label = ttk.Label(item, text=value_text, style="PanelTitle.TLabel")
            value_label.pack(anchor="w", pady=(4, 0))
            self.style_snapshot_value_labels.append(value_label)
        style_form = ttk.Frame(style_box, style="Panel.TFrame")
        style_form.pack(fill="x")
        style_form.columnconfigure(1, weight=1)
        ttk.Label(style_form, text="透明度", style="SectionLabel.TLabel").grid(row=0, column=0, sticky="w")
        self.alpha_var = tk.DoubleVar(value=0.88)
        ttk.Scale(style_form, from_=0.35, to=1.0, variable=self.alpha_var, orient="horizontal").grid(row=0, column=1, sticky="ew")
        ttk.Label(style_form, text="字体大小", style="SectionLabel.TLabel").grid(row=1, column=0, sticky="w", pady=(14, 0))
        self.font_size_var = tk.IntVar(value=26)
        ttk.Spinbox(style_form, from_=16, to=56, textvariable=self.font_size_var).grid(row=1, column=1, sticky="ew", pady=(14, 0))
        ttk.Label(style_form, text="背景颜色", style="SectionLabel.TLabel").grid(row=2, column=0, sticky="w", pady=(14, 0))
        self.bg_color_var = tk.StringVar(value="#F7FAF5")
        ttk.Entry(style_form, textvariable=self.bg_color_var).grid(row=2, column=1, sticky="ew", pady=(14, 0))
        ttk.Label(style_form, text="组件尺寸", style="SectionLabel.TLabel").grid(row=3, column=0, sticky="w", pady=(14, 0))
        self.widget_size_var = tk.StringVar(value="medium")
        self.widget_size_combo = ttk.Combobox(
            style_form,
            textvariable=self.widget_size_var,
            state="readonly",
            values=["small", "medium", "large"],
        )
        self.widget_size_combo.grid(row=3, column=1, sticky="ew", pady=(14, 0))
        style_actions = ttk.Frame(style_box, style="Panel.TFrame")
        style_actions.pack(fill="x", pady=(16, 0))
        ttk.Button(style_actions, text="选择颜色", style="Quiet.TButton", command=self.choose_color).pack(side="left")
        self.float_style_hint_label = ttk.Label(
            style_actions,
            text="悬浮窗会自动同步这些设置。",
            style="Muted.TLabel",
        )
        self.float_style_hint_label.pack(side="left", padx=(12, 0))
        ttk.Label(style_box, text="全局快捷键：Alt+Space 翻面，Alt+Left 不认识，Alt+Right 认识", style="Muted.TLabel", wraplength=420, justify="left").pack(anchor="w", pady=(12, 0))
        for variable in [self.alpha_var, self.font_size_var, self.bg_color_var, self.widget_size_var]:
            variable.trace_add("write", self.schedule_float_style_save)

        stats_box = self.create_panel(dashboard_tab, "学习状态", "今天的复习完成度和最近 30 天的节奏集中显示在这里。")
        self.stats_box_title_label = stats_box.title_label
        stats_box.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        self.stats_summary_label = ttk.Label(stats_box, text="最近 30 天的学习节奏会和今天的完成度一起展示。", style="Muted.TLabel")
        self.stats_summary_label.pack(anchor="w", pady=(4, 10))
        stats_header = ttk.Frame(stats_box, style="Panel.TFrame")
        stats_header.pack(fill="x")
        stats_header.columnconfigure(0, weight=2)
        stats_header.columnconfigure(1, weight=3)
        stats_lead = ttk.Frame(stats_header, style="Hero.TFrame", padding=(18, 16))
        stats_lead.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        ttk.Label(stats_lead, text="今日进度", style="SectionLabel.TLabel").pack(anchor="w")
        self.progress_label = ttk.Label(stats_lead, text="", style="Summary.TLabel", wraplength=320, justify="left")
        self.progress_label.pack(anchor="w", pady=(8, 0))
        self.heatmap_caption_label = ttk.Label(stats_lead, text="", style="Muted.TLabel", wraplength=320, justify="left")
        self.heatmap_caption_label.pack(anchor="w", pady=(8, 0))
        stats_spotlight = ttk.Frame(stats_header, style="Panel.TFrame")
        stats_spotlight.grid(row=0, column=1, sticky="nsew")
        self.stats_spotlight_value_labels: list[ttk.Label] = []
        for index, (label_text, value_text) in enumerate(self.build_stats_spotlight_items(None)):
            card = ttk.Frame(stats_spotlight, style="Panel.TFrame", padding=(14, 12))
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 10 if index < 2 else 0))
            stats_spotlight.columnconfigure(index, weight=1)
            ttk.Label(card, text=label_text, style="SectionLabel.TLabel").pack(anchor="w")
            value_label = ttk.Label(card, text=value_text, style="PanelTitle.TLabel")
            value_label.pack(anchor="w", pady=(4, 0))
            self.stats_spotlight_value_labels.append(value_label)
        self.metric_strip = ttk.Frame(stats_box, style="Panel.TFrame")
        self.metric_strip.pack(fill="x", pady=(14, 0))
        self.metric_value_labels: list[ttk.Label] = []
        for label_text, value_text in self.build_metric_items(None):
            metric_card = ttk.Frame(self.metric_strip, style="Panel.TFrame", padding=(12, 10))
            metric_card.pack(side="left", padx=(0, 10))
            ttk.Label(metric_card, text=label_text, style="SectionLabel.TLabel").pack(anchor="w")
            value_label = ttk.Label(metric_card, text=value_text, style="PanelTitle.TLabel")
            value_label.pack(anchor="w", pady=(4, 0))
            self.metric_value_labels.append(value_label)
        self.progress = ttk.Progressbar(stats_box, maximum=100, style="App.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(12, 12))
        self.heatmap_frame = tk.Frame(stats_box, bg=THEME["panel"])
        self.heatmap_frame.pack(fill="x")
        self.heatmap_legend_frame = tk.Frame(stats_box, bg=THEME["panel"])
        self.heatmap_legend_frame.pack(anchor="w", pady=(8, 0))
        for label_text, color in self.build_heatmap_legend_items():
            legend_item = tk.Frame(self.heatmap_legend_frame, bg=THEME["panel"])
            legend_item.pack(side="left", padx=(0, 12))
            tk.Label(legend_item, width=2, height=1, bg=color, relief="flat").pack(side="left")
            tk.Label(
                legend_item,
                text=label_text,
                bg=THEME["panel"],
                fg=THEME["muted"],
                font=("Segoe UI", 8),
            ).pack(side="left", padx=(6, 0))

        words_tab = ttk.Frame(self.content_notebook, style="Panel.TFrame", padding=8)
        words_tab.columnconfigure(0, weight=1)
        words_tab.rowconfigure(1, weight=1)
        self.content_notebook.add(words_tab, text="词库概览")

        words_header = ttk.Frame(words_tab, style="Panel.TFrame", padding=14)
        words_header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        words_header.columnconfigure(0, weight=1)
        ttk.Label(words_header, text="词库概览", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.words_overview_label = ttk.Label(
            words_header,
            text=self.build_words_overview_text(),
            style="Muted.TLabel",
            wraplength=860,
            justify="left",
        )
        self.words_overview_label.grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Label(
            words_header,
            text=self.build_words_action_hint(),
            style="SectionLabel.TLabel",
            wraplength=860,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(10, 0))
        words_table_frame = ttk.Frame(words_tab, style="Panel.TFrame")
        words_table_frame.grid(row=1, column=0, sticky="nsew")
        words_table_frame.columnconfigure(0, weight=1)
        words_table_frame.rowconfigure(0, weight=1)
        self.words_tree = ttk.Treeview(words_table_frame, columns=("word", "meaning", "status"), show="headings", height=14)
        self.words_tree.heading("word", text="单词")
        self.words_tree.heading("meaning", text="释义")
        self.words_tree.heading("status", text="状态")
        self.words_tree.column("word", width=160, anchor="w")
        self.words_tree.column("meaning", width=520, anchor="w")
        self.words_tree.column("status", width=100, anchor="center")
        self.words_tree.grid(row=0, column=0, sticky="nsew")
        words_scrollbar = ttk.Scrollbar(words_table_frame, orient="vertical", command=self.words_tree.yview)
        words_scrollbar.grid(row=0, column=1, sticky="ns")
        self.words_tree.configure(yscrollcommand=words_scrollbar.set)

        news_tab = ttk.Frame(self.content_notebook, style="Panel.TFrame", padding=8)
        news_tab.columnconfigure(0, weight=1)
        news_tab.rowconfigure(1, weight=1)
        self.content_notebook.add(news_tab, text="英语日报")

        news_header_card = ttk.Frame(news_tab, style="Panel.TFrame", padding=14)
        news_header_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        news_header_card.columnconfigure(0, weight=1)
        ttk.Label(news_header_card, text="阅读与日报", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.news_intro_label = ttk.Label(
            news_header_card,
            text="英语日报会跟着当前学习语言切换；未配置语言会显示空状态。",
            style="Muted.TLabel",
            wraplength=880,
            justify="left",
        )
        self.news_intro_label.grid(row=1, column=0, sticky="w", pady=(6, 0))
        news_overview = ttk.Frame(news_header_card, style="Panel.TFrame")
        news_overview.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.news_overview_value_labels: list[ttk.Label] = []
        for index, (label_text, value_text) in enumerate(self.build_news_overview_items()):
            item = ttk.Frame(news_overview, style="Hero.TFrame", padding=(14, 12))
            item.grid(row=0, column=index, sticky="nsew", padx=(0, 10 if index < 2 else 0))
            news_overview.columnconfigure(index, weight=1)
            ttk.Label(item, text=label_text, style="SectionLabel.TLabel").pack(anchor="w")
            value_label = ttk.Label(item, text=value_text, style="PanelTitle.TLabel")
            value_label.pack(anchor="w", pady=(4, 0))
            self.news_overview_value_labels.append(value_label)
        ttk.Label(
            news_header_card,
            text=self.build_news_action_hint(),
            style="SectionLabel.TLabel",
            wraplength=880,
            justify="left",
        ).grid(row=3, column=0, sticky="w", pady=(12, 0))
        news_actions = ttk.Frame(news_tab, style="Panel.TFrame")
        news_actions.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        news_actions.columnconfigure(0, weight=1)
        ttk.Button(news_actions, text="刷新最新 10 篇", style="Quiet.TButton", command=self.refresh_daily_briefs).grid(row=0, column=0, sticky="w")
        ttk.Button(news_actions, text="收藏并翻译", style="Secondary.TButton", command=self.save_selected_brief).grid(row=0, column=1, sticky="e")

        news_content = ttk.Frame(news_tab, style="Panel.TFrame")
        news_content.grid(row=2, column=0, sticky="nsew")
        news_content.columnconfigure(0, weight=3)
        news_content.columnconfigure(1, weight=2)
        news_content.rowconfigure(0, weight=1)

        latest_frame = ttk.Frame(news_content, style="Panel.TFrame")
        latest_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        latest_frame.columnconfigure(0, weight=1)
        latest_frame.rowconfigure(1, weight=1)
        latest_header = ttk.Frame(latest_frame, style="Panel.TFrame")
        latest_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        latest_header.columnconfigure(0, weight=1)
        self.latest_briefs_label = ttk.Label(latest_header, text="最新内容", style="PanelTitle.TLabel")
        self.latest_briefs_label.grid(row=0, column=0, sticky="w")
        ttk.Label(latest_header, text="双击条目可直接进入收藏与翻译。", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        self.brief_tree = ttk.Treeview(latest_frame, columns=("source", "published", "title"), show="headings", height=10)
        self.brief_tree.heading("source", text="来源")
        self.brief_tree.heading("published", text="时间")
        self.brief_tree.heading("title", text="标题")
        self.brief_tree.column("source", width=110, anchor="w")
        self.brief_tree.column("published", width=130, anchor="center")
        self.brief_tree.column("title", width=380, anchor="w")
        self.brief_tree.grid(row=1, column=0, sticky="nsew")
        self.brief_tree.bind("<Double-1>", lambda _event: self.save_selected_brief())
        self.brief_tree.bind("<<TreeviewSelect>>", lambda _event: self.show_selected_brief())
        preview_card = ttk.Frame(latest_frame, style="Panel.TFrame", padding=14)
        preview_card.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        preview_card.columnconfigure(0, weight=1)
        self.brief_preview_title = ttk.Label(preview_card, text="选择一篇日报开始预览", style="PanelTitle.TLabel")
        self.brief_preview_title.grid(row=0, column=0, sticky="w")
        self.brief_preview_meta = ttk.Label(
            preview_card,
            text="来源、时间和收藏状态会显示在这里。",
            style="Muted.TLabel",
            wraplength=520,
            justify="left",
        )
        self.brief_preview_meta.grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.brief_preview_label = ttk.Label(
            preview_card,
            text="预览摘要",
            style="SectionLabel.TLabel",
        )
        self.brief_preview_label.grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.brief_summary = tk.Text(
            preview_card,
            height=7,
            wrap="word",
            bg=THEME["panel_alt"],
            fg=THEME["text"],
            bd=0,
            padx=12,
            pady=12,
            relief="flat",
            highlightthickness=0,
            font=("Segoe UI", 10),
        )
        self.brief_summary.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.brief_summary.configure(state="disabled")
        self.brief_preview_footer = ttk.Label(
            preview_card,
            text="双击条目或收藏后可在阅读窗查看全文。",
            style="Muted.TLabel",
            wraplength=520,
            justify="left",
        )
        self.brief_preview_footer.grid(row=4, column=0, sticky="w", pady=(10, 0))

        favorite_frame = ttk.Frame(news_content, style="Panel.TFrame")
        favorite_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        favorite_frame.columnconfigure(0, weight=1)
        favorite_frame.rowconfigure(1, weight=1)
        favorite_header = ttk.Frame(favorite_frame, style="Panel.TFrame")
        favorite_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        favorite_header.columnconfigure(0, weight=1)
        self.favorite_articles_label = ttk.Label(favorite_header, text="我的收藏", style="PanelTitle.TLabel")
        self.favorite_articles_label.grid(row=0, column=0, sticky="w")
        ttk.Label(favorite_header, text="收藏后可在这里集中阅读与删除。", style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Button(favorite_header, text="删除收藏", style="Quiet.TButton", command=self.delete_selected_favorite).grid(row=0, column=1, sticky="e")
        self.favorite_tree = ttk.Treeview(favorite_frame, columns=("source", "saved", "title"), show="headings", height=10)
        self.favorite_tree.heading("source", text="来源")
        self.favorite_tree.heading("saved", text="收藏时间")
        self.favorite_tree.heading("title", text="标题")
        self.favorite_tree.column("source", width=110, anchor="w")
        self.favorite_tree.column("saved", width=130, anchor="center")
        self.favorite_tree.column("title", width=380, anchor="w")
        self.favorite_tree.grid(row=1, column=0, sticky="nsew")
        self.favorite_tree.bind("<<TreeviewSelect>>", lambda _event: self.show_selected_favorite())
        self.favorite_tree.bind("<Double-1>", lambda _event: self.show_selected_favorite())
        ttk.Label(
            favorite_frame,
            text="点击或双击收藏条目，会在阅读窗中打开完整内容；失焦后会自动收起。",
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

    def refresh_all(self):
        self.refresh_lexicons()
        self.refresh_dashboard_overview()
        self.refresh_stats()
        self.refresh_words()
        self.refresh_brief_list()
        self.refresh_favorite_list()
        self.refresh_example_status()

    def language_display(self, language_code: str) -> str:
        language_map = dict(self.settings_service.list_supported_languages())
        return f"{language_map.get(language_code, language_code)} · {language_code}"

    def selected_language_code(self) -> str | None:
        value = self.language_var.get().strip()
        if not value:
            return None
        if " · " in value:
            return value.rsplit(" · ", 1)[1]
        return value

    def active_language_code(self) -> str:
        return self.selected_language_code() or self.settings_service.get_plan_settings()["current_language_code"] or DEFAULT_LANGUAGE_CODE

    def refresh_lexicons(self):
        plan = self.settings_service.get_plan_settings()
        self.language_options = self.settings_service.list_supported_languages()
        language_values = [self.language_display(code) for code, _label in self.language_options]
        current_language_code = plan["current_language_code"] or DEFAULT_LANGUAGE_CODE
        self.lexicons = self.db.lexicons(current_language_code)
        values = [f"{row['id']} · {row['name']} ({row['mastered'] or 0}/{row['total'] or 0})" for row in self.lexicons]
        self.lexicon_combo["values"] = values
        self.language_combo["values"] = language_values
        self.loading_plan = True
        self.language_var.set(self.language_display(current_language_code))
        self.lexicon_var.set("")
        for index, row in enumerate(self.lexicons):
            if row["id"] == plan["lexicon_id"]:
                self.lexicon_combo.current(index)
                break
        self.daily_new_var.set(plan["daily_new"])
        self.target_date_var.set(plan["target_date"] or "")
        self.alpha_var.set(plan["float_alpha"])
        self.font_size_var.set(plan["font_size"])
        self.bg_color_var.set(plan["bg_color"])
        self.widget_size_var.set(plan["widget_size"] if "widget_size" in plan.keys() else "medium")
        self.loading_plan = False
        has_lexicons = bool(self.lexicons)
        self.lexicon_combo.configure(state="readonly" if has_lexicons else "disabled")
        self.lexicon_state_label.configure(text=self.build_lexicon_state_text(has_lexicons))
        self.import_language_label.configure(text=f"当前导入语言：{self.language_display(current_language_code)}")
        language_map = dict(self.language_options)
        language_name = language_map.get(current_language_code, current_language_code)
        self.content_notebook.tab(1, text=self.build_words_tab_title(language_name))
        self.content_notebook.tab(2, text=f"{language_name} 日报")
        self.news_intro_label.configure(text=f"{language_name} 日报和收藏会跟着当前学习语言切换。")
        latest_title, favorite_title = self.build_news_titles_for_language(language_name)
        self.latest_briefs_label.configure(text=latest_title)
        self.favorite_articles_label.configure(text=favorite_title)
        if not has_lexicons:
            title, meta, summary, footer = self.build_brief_empty_state(has_lexicons=False)
            self.update_brief_preview_state(title=title, meta=meta, summary=summary, footer=footer)

    def selected_lexicon_id(self):
        value = self.lexicon_var.get()
        return int(value.split(" · ", 1)[0]) if value else None

    def on_language_selected(self, _event=None):
        if self.loading_plan:
            return
        language_code = self.selected_language_code()
        if not language_code:
            return
        self.settings_service.switch_language(language_code)
        self.refresh_all()

    def save_plan(self):
        lexicon_id = self.selected_lexicon_id()
        if not lexicon_id:
            messagebox.showwarning(APP_NAME, "请先为当前学习语言选择词库。")
            return
        target_date = self.target_date_var.get().strip()
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning(APP_NAME, "目标日期格式应为 YYYY-MM-DD。")
            return
        self.settings_service.save_plan(
            lexicon_id,
            int(self.daily_new_var.get()),
            target_date,
            float(self.alpha_var.get()),
            int(self.font_size_var.get()),
            self.bg_color_var.get().strip() or "#F7FAF5",
            self.widget_size_var.get(),
            current_language_code=self.active_language_code(),
        )
        self.float_window.apply_style()
        self.refresh_all()

    def schedule_float_style_save(self, *_args):
        if self.loading_plan:
            return
        if self.style_after_id:
            self.root.after_cancel(self.style_after_id)
        self.style_after_id = self.root.after(250, self.save_float_style)

    def save_float_style(self):
        self.style_after_id = None
        bg_color = self.bg_color_var.get().strip() or "#F7FAF5"
        if not self.valid_tk_color(bg_color):
            return
        self.settings_service.save_float_style(
            float(self.alpha_var.get()),
            int(self.font_size_var.get()),
            bg_color,
            self.widget_size_var.get(),
        )
        self.float_window.apply_style()
        self.float_window.render()

    def valid_tk_color(self, color: str) -> bool:
        try:
            self.root.winfo_rgb(color)
            return True
        except tk.TclError:
            return False

    def import_words(self):
        file_path = filedialog.askopenfilename(
            title="选择词库文件",
            filetypes=[("Word list", "*.txt *.csv *.json"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            count, name, language_code = self.db.import_words(file_path, current_language_code=self.active_language_code())
        except UnicodeDecodeError:
            messagebox.showerror(APP_NAME, "导入失败：请使用 UTF-8 编码保存词库。")
            return
        except ValueError as exc:
            messagebox.showerror(APP_NAME, f"导入失败：{exc}")
            return
        self.settings_service.switch_language(language_code)
        messagebox.showinfo(APP_NAME, f"已导入 {name}：{count} 个单词，归入 {self.language_display(language_code)}。")
        self.refresh_all()

    def edit_selected_lexicon(self):
        lexicon_id = self.selected_lexicon_id() or self.settings_service.get_plan_settings()["lexicon_id"]
        if not lexicon_id:
            messagebox.showinfo(APP_NAME, "请先选择一个词库。")
            return
        lexicon = self.db.get_lexicon(lexicon_id)
        if not lexicon:
            messagebox.showwarning(APP_NAME, "当前词库不存在了，请刷新后重试。")
            self.refresh_all()
            return
        new_name = simpledialog.askstring(APP_NAME, "修改词库名称", initialvalue=lexicon["name"], parent=self.root)
        if new_name is None:
            return
        new_name = new_name.strip()
        if not new_name:
            messagebox.showwarning(APP_NAME, "词库名称不能为空。")
            return
        current_code = lexicon["language_code"]
        language_map = dict(self.supported_languages())
        options = "\n".join(f"{code} - {label}" for code, label in self.supported_languages())
        new_language_code = simpledialog.askstring(
            APP_NAME,
            f"修改词库语言\n可选：\n{options}",
            initialvalue=current_code,
            parent=self.root,
        )
        if new_language_code is None:
            return
        new_language_code = new_language_code.strip().lower()
        if new_language_code not in language_map:
            messagebox.showwarning(APP_NAME, "语言代码无效，请输入支持的语言代码。")
            return
        try:
            self.db.update_lexicon(lexicon_id, new_name, new_language_code)
        except sqlite3.IntegrityError:
            messagebox.showerror(APP_NAME, f"{language_map[new_language_code]} 下已经有同名词库了。")
            return
        self.settings_service.switch_language(new_language_code)
        self.refresh_all()
        messagebox.showinfo(APP_NAME, f"词库已更新为 {new_name}，归入 {language_map[new_language_code]}。")

    def delete_selected_lexicon(self):
        lexicon_id = self.selected_lexicon_id() or self.settings_service.get_plan_settings()["lexicon_id"]
        if not lexicon_id:
            messagebox.showinfo(APP_NAME, "请先选择一个词库。")
            return
        lexicon = self.db.get_lexicon(lexicon_id)
        if not lexicon:
            self.refresh_all()
            return
        if not messagebox.askyesno(APP_NAME, f"确定删除词库《{lexicon['name']}》吗？词条也会一起删除。"):
            return
        active_language = self.active_language_code()
        self.db.delete_lexicon(lexicon_id)
        self.settings_service.switch_language(active_language)
        self.refresh_all()

    def refresh_example_status(self):
        lexicon_id = self.selected_lexicon_id() or self.settings_service.get_plan_settings()["lexicon_id"]
        if not lexicon_id:
            self.example_status_label.configure(text="先导入当前语言的词库，再补全例句。")
            return
        missing = self.study_service.missing_examples_count(lexicon_id)
        self.example_status_label.configure(text=f"当前词库还缺 {missing} 条例句")

    def enrich_examples(self):
        lexicon_id = self.selected_lexicon_id() or self.settings_service.get_plan_settings()["lexicon_id"]
        self.example_status_label.configure(text="正在补全例句...")

        def worker():
            try:
                result = self.enrichment_service.enrich_examples(lexicon_id=lexicon_id, limit=200, refresh=False)
            except Exception as exc:
                error_message = f"例句补全失败：{exc}"
                self.root.after(0, lambda msg=error_message: messagebox.showerror(APP_NAME, msg))
                self.root.after(0, self.refresh_example_status)
                return

            def done():
                self.refresh_all()
                messagebox.showinfo(
                    APP_NAME,
                    f"例句补全完成：处理 {result['processed']}，补全 {result['updated']}，跳过 {result['skipped']}，失败 {len(result['failures'])}。",
                )

            self.root.after(0, done)

        threading.Thread(target=worker, daemon=True).start()

    def choose_color(self):
        color = colorchooser.askcolor(initialcolor=self.bg_color_var.get())[1]
        if color:
            self.bg_color_var.set(color)

    def refresh_stats(self):
        stats = self.study_service.get_study_stats()
        metric_items = self.build_metric_items(stats)
        for label, (_title, value) in zip(getattr(self, "metric_value_labels", []), metric_items):
            label.configure(text=value)
        spotlight_items = self.build_stats_spotlight_items(stats)
        for label, (_title, value) in zip(getattr(self, "stats_spotlight_value_labels", []), spotlight_items):
            label.configure(text=value)
        self.progress_label.configure(text=self.build_stats_progress_text(stats))
        if hasattr(self, "heatmap_caption_label"):
            self.heatmap_caption_label.configure(text=self.build_heatmap_caption_text(stats))
        if not stats:
            self.progress["value"] = 0
            for child in self.heatmap_frame.winfo_children():
                child.destroy()
            return
        summary = stats["summary"]
        total = summary["total"] or 0
        mastered = summary["mastered"] or 0
        percent = round((mastered / total) * 100) if total else 0
        self.progress["value"] = percent
        for child in self.heatmap_frame.winfo_children():
            child.destroy()
        day_map = {row["day"]: row["reviewed"] for row in stats["days"]}
        for i in range(30):
            day = date.today() - timedelta(days=29 - i)
            count = day_map.get(day.isoformat(), 0)
            color = (
                THEME["heat_0"]
                if count == 0
                else THEME["heat_1"]
                if count < 5
                else THEME["heat_2"]
                if count < 15
                else THEME["heat_3"]
            )
            label = tk.Label(
                self.heatmap_frame,
                text=str(day.day),
                width=3,
                height=2,
                bg=color,
                fg=THEME["text"],
                font=("Segoe UI", 9),
                relief="flat",
            )
            label.grid(row=0, column=i, padx=2, pady=4)

    def refresh_words(self):
        for item in self.words_tree.get_children():
            self.words_tree.delete(item)
        lexicon_id = self.selected_lexicon_id() or self.settings_service.get_plan_settings()["lexicon_id"]
        if not lexicon_id:
            return
        rows = self.study_service.get_recent_words(lexicon_id, limit=5000)
        for row in rows:
            self.words_tree.insert("", "end", values=(row["word"], row["meaning"], status_text(row["status"])))

    def refresh_daily_briefs(self):
        threading.Thread(target=self._refresh_daily_briefs_worker, daemon=True).start()

    def _refresh_daily_briefs_worker(self):
        language_code = self.active_language_code()
        try:
            self.news_service.refresh_latest_briefs(language_code=language_code, limit=10)
        except Exception as exc:
            error_message = f"刷新日报失败：{exc}"
            self.root.after(0, lambda msg=error_message: messagebox.showerror(APP_NAME, msg))
            return
        self.root.after(0, self.refresh_brief_list)

    def refresh_brief_list(self):
        if not hasattr(self, "brief_tree"):
            return
        for item in self.brief_tree.get_children():
            self.brief_tree.delete(item)
        language_code = self.active_language_code()
        rows = self.news_service.list_latest_briefs(language_code=language_code, limit=10)
        for row in rows:
            published = (row["published_at"] or "")[:16].replace("T", " ")
            saved_tag = " 已收藏" if row["saved"] else ""
            self.brief_tree.insert("", "end", iid=str(row["id"]), values=(row["source_name"], published, row["title"] + saved_tag))
        if rows:
            self.update_brief_preview_state()
        else:
            title, meta, summary, footer = self.build_brief_empty_state(has_lexicons=bool(self.lexicons))
            self.update_brief_preview_state(title=title, meta=meta, summary=summary, footer=footer)

    def selected_brief_id(self) -> int | None:
        selection = self.brief_tree.selection()
        return int(selection[0]) if selection else None

    def show_selected_brief(self):
        brief_id = self.selected_brief_id()
        if not brief_id:
            self.update_brief_preview_state()
            return
        row = self.news_service.get_brief(brief_id, language_code=self.active_language_code())
        if not row:
            self.update_brief_preview_state()
            return
        title, meta, summary, footer = self.build_brief_preview_parts(row)
        self.update_brief_preview_state(title=title, meta=meta, summary=summary, footer=footer)

    def save_selected_brief(self):
        brief_id = self.selected_brief_id()
        if not brief_id:
            messagebox.showinfo(APP_NAME, "请先选择一篇日报。")
            return
        threading.Thread(target=self._save_selected_brief_worker, args=(brief_id,), daemon=True).start()

    def _save_selected_brief_worker(self, brief_id: int):
        language_code = self.active_language_code()
        try:
            self.news_service.save_brief_to_favorites(brief_id, language_code=language_code)
        except Exception as exc:
            error_message = f"收藏日报失败：{exc}"
            self.root.after(0, lambda msg=error_message: messagebox.showerror(APP_NAME, msg))
            return
        self.root.after(0, self._after_brief_saved)

    def _after_brief_saved(self):
        self.refresh_brief_list()
        self.refresh_favorite_list()
        messagebox.showinfo(APP_NAME, "日报已加入个人收藏，并完成双语保存。")

    def refresh_favorite_list(self):
        if not hasattr(self, "favorite_tree"):
            return
        for item in self.favorite_tree.get_children():
            self.favorite_tree.delete(item)
        rows = self.news_service.list_favorite_articles(language_code=self.active_language_code())
        for row in rows:
            saved = (row["saved_at"] or "")[:16].replace("T", " ")
            self.favorite_tree.insert("", "end", iid=str(row["id"]), values=(row["source_name"], saved, row["title"]))

    def selected_favorite_id(self) -> int | None:
        selection = self.favorite_tree.selection()
        return int(selection[0]) if selection else None

    def show_selected_favorite(self):
        article_id = self.selected_favorite_id()
        if not article_id:
            return
        article = self.news_service.get_favorite_article(article_id, language_code=self.active_language_code())
        if article:
            self.article_window.show_article(article)

    def delete_selected_favorite(self):
        article_id = self.selected_favorite_id()
        if not article_id:
            messagebox.showinfo(APP_NAME, "请先选择一篇收藏日报。")
            return
        article = self.news_service.get_favorite_article(article_id, language_code=self.active_language_code())
        if not article:
            self.refresh_favorite_list()
            self.refresh_brief_list()
            return
        if not messagebox.askyesno(APP_NAME, f"确定删除收藏《{article['title']}》吗？"):
            return
        deleted = self.news_service.delete_favorite_article(article_id, language_code=self.active_language_code())
        if not deleted:
            messagebox.showwarning(APP_NAME, "这篇收藏已经不存在了。")
        self.refresh_favorite_list()
        self.refresh_brief_list()

    def update_text_widget(self, widget: tk.Text, content: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        if content:
            widget.insert("1.0", content)
        widget.configure(state="disabled")

    def update_brief_preview_state(
        self,
        *,
        title: str = "选择一篇日报开始预览",
        meta: str = "来源、时间和收藏状态会显示在这里。",
        summary: str = "",
        footer: str = "双击条目或收藏后可在阅读窗查看全文。",
    ):
        if hasattr(self, "brief_preview_title"):
            self.brief_preview_title.configure(text=title)
        if hasattr(self, "brief_preview_meta"):
            self.brief_preview_meta.configure(text=meta)
        if hasattr(self, "brief_preview_footer"):
            self.brief_preview_footer.configure(text=footer)
        self.update_text_widget(self.brief_summary, summary)

    def poll_hotkeys(self):
        if self.closed or not self.root.winfo_exists():
            return
        while True:
            try:
                event_id = self.hotkey_events.get_nowait()
            except queue.Empty:
                break
            if event_id == 1:
                self.float_window.mark_known()
            elif event_id == 2:
                self.float_window.mark_unknown()
            elif event_id == 3:
                self.float_window.flip()
        self.poll_after_id = self.root.after(120, self.poll_hotkeys)

    def close(self):
        if self.closed:
            if self.root.winfo_exists():
                self._root_destroy()
            return
        self.closed = True
        if self.poll_after_id:
            try:
                self.root.after_cancel(self.poll_after_id)
            except tk.TclError:
                pass
            self.poll_after_id = None
        if hasattr(self, "float_window") and getattr(self.float_window, "round_after_id", None):
            try:
                self.float_window.after_cancel(self.float_window.round_after_id)
            except tk.TclError:
                pass
            self.float_window.round_after_id = None
        if hasattr(self, "db") and getattr(self.db, "conn", None) is not None:
            try:
                self.db.conn.close()
            except sqlite3.Error:
                pass
        if self.root.winfo_exists():
            self._root_destroy()

    def run(self):
        self.root.mainloop()


def status_text(status: str) -> str:
    return {
        STATUS_NEW: "生词",
        STATUS_FUZZY: "模糊",
        STATUS_MASTERED: "已掌握",
    }.get(status, status)


__all__ = [
    "EnrichmentService",
    "FloatVocabApp",
    "FloatVocabDB",
    "NewsService",
    "SettingsService",
    "StudyService",
    "WordCard",
    "calculate_srs",
    "get_default_db_path",
    "get_user_data_dir",
    "main",
    "prepare_runtime_storage",
    "qwerty_item_to_word",
    "row_to_card",
    "row_to_word_dict",
    "status_text",
]


def main():
    app = FloatVocabApp()
    app.run()


if __name__ == "__main__":
    main()

