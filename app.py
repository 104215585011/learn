import csv
import ctypes
import ctypes.wintypes
import json
import os
import queue
import sqlite3
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

import news_digest
from example_pipeline import enrich_database


APP_NAME = "FloatVocab"
APP_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", APP_ROOT))
DATA_DIR = RESOURCE_ROOT / "data"
DB_PATH = APP_ROOT / "floatvocab.db"
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
    "bg": "#F3F8FE",
    "panel": "#FFFFFF",
    "panel_alt": "#EEF6FF",
    "hero": "#E7F3FF",
    "border": "#D7E7F7",
    "text": "#17324D",
    "muted": "#617A93",
    "accent": "#2B84F6",
    "accent_active": "#1A6ED8",
    "accent_soft": "#D8EBFF",
    "success": "#21A366",
    "danger": "#EF6A6A",
    "warning": "#F2A93B",
    "heat_0": "#E8F1FB",
    "heat_1": "#CAE2FF",
    "heat_2": "#8FC2FF",
    "heat_3": "#3B90F7",
}


@dataclass
class WordCard:
    id: int
    word: str
    phonetic: str
    meaning: str
    example: str
    status: str
    lexicon_name: str


class FloatVocabDB:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()
        news_digest.ensure_schema(self.conn)
        self.seed_builtin()
        self.seed_exam_lexicons()

    def init_schema(self):
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;

            CREATE TABLE IF NOT EXISTS lexicons (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              name TEXT NOT NULL UNIQUE,
              source TEXT NOT NULL DEFAULT 'built-in',
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS words (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              lexicon_id INTEGER NOT NULL,
              word TEXT NOT NULL,
              phonetic TEXT DEFAULT '',
              meaning TEXT NOT NULL,
              example TEXT DEFAULT '',
              example_source TEXT DEFAULT '',
              example_updated_at TEXT,
              example_attempted_at TEXT,
              example_attempts INTEGER NOT NULL DEFAULT 0,
              status TEXT NOT NULL DEFAULT 'new',
              next_review_date TEXT NOT NULL,
              interval_days INTEGER NOT NULL DEFAULT 0,
              repetitions INTEGER NOT NULL DEFAULT 0,
              ease_factor REAL NOT NULL DEFAULT 2.5,
              seen_count INTEGER NOT NULL DEFAULT 0,
              correct_count INTEGER NOT NULL DEFAULT 0,
              created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              UNIQUE(lexicon_id, word),
              FOREIGN KEY (lexicon_id) REFERENCES lexicons(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS plans (
              id INTEGER PRIMARY KEY CHECK (id = 1),
              lexicon_id INTEGER,
              daily_new INTEGER NOT NULL DEFAULT 20,
              target_date TEXT,
              float_alpha REAL NOT NULL DEFAULT 0.88,
              font_size INTEGER NOT NULL DEFAULT 26,
              bg_color TEXT NOT NULL DEFAULT '#F7FAF5',
              widget_size TEXT NOT NULL DEFAULT 'medium',
              updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (lexicon_id) REFERENCES lexicons(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS reviews (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              word_id INTEGER NOT NULL,
              rating INTEGER NOT NULL,
              old_interval_days INTEGER NOT NULL,
              new_interval_days INTEGER NOT NULL,
              reviewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
              FOREIGN KEY (word_id) REFERENCES words(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS daily_stats (
              day TEXT PRIMARY KEY,
              reviewed INTEGER NOT NULL DEFAULT 0,
              known INTEGER NOT NULL DEFAULT 0,
              unknown INTEGER NOT NULL DEFAULT 0,
              new_seen INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        self.ensure_plan_columns()
        self.ensure_word_columns()
        self.conn.execute(
            "INSERT OR IGNORE INTO plans (id, lexicon_id, daily_new, target_date) VALUES (1, NULL, 20, ?)",
            [(date.today() + timedelta(days=90)).isoformat()],
        )
        self.conn.commit()

    def ensure_plan_columns(self):
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(plans)").fetchall()}
        if "widget_size" not in columns:
            self.conn.execute("ALTER TABLE plans ADD COLUMN widget_size TEXT NOT NULL DEFAULT 'medium'")
        if "current_word_id" not in columns:
            self.conn.execute("ALTER TABLE plans ADD COLUMN current_word_id INTEGER")

    def ensure_word_columns(self):
        columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(words)").fetchall()}
        if "example_source" not in columns:
            self.conn.execute("ALTER TABLE words ADD COLUMN example_source TEXT DEFAULT ''")
        if "example_updated_at" not in columns:
            self.conn.execute("ALTER TABLE words ADD COLUMN example_updated_at TEXT")
        if "example_attempted_at" not in columns:
            self.conn.execute("ALTER TABLE words ADD COLUMN example_attempted_at TEXT")
        if "example_attempts" not in columns:
            self.conn.execute("ALTER TABLE words ADD COLUMN example_attempts INTEGER NOT NULL DEFAULT 0")

    def seed_builtin(self):
        if self.conn.execute("SELECT 1 FROM lexicons WHERE name = ?", ("考研核心 50",)).fetchone():
            return
        with BUILTIN_LEXICON.open("r", encoding="utf-8") as file:
            words = json.load(file)
        lexicon_id = self.create_lexicon("考研核心 50", "built-in")
        today = date.today().isoformat()
        for item in words:
            self.conn.execute(
                """
                INSERT OR IGNORE INTO words
                (lexicon_id, word, phonetic, meaning, example, next_review_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (lexicon_id, item["word"], item.get("phonetic", ""), item["meaning"], item.get("example", ""), today),
            )
        self.conn.execute("UPDATE plans SET lexicon_id = ? WHERE id = 1 AND lexicon_id IS NULL", (lexicon_id,))
        self.conn.commit()

    def seed_exam_lexicons(self):
        if not VOCAB_SOURCE_DIR.exists():
            return
        today = date.today().isoformat()
        for lexicon_name, file_name in EXAM_LEXICONS:
            if self.conn.execute("SELECT 1 FROM lexicons WHERE name = ?", (lexicon_name,)).fetchone():
                continue
            source_path = VOCAB_SOURCE_DIR / file_name
            if not source_path.exists():
                continue
            with source_path.open("r", encoding="utf-8") as file:
                rows = json.load(file)
            lexicon_id = self.create_lexicon(lexicon_name, "built-in")
            for item in rows:
                row = qwerty_item_to_word(item, lexicon_name)
                if not row:
                    continue
                self.conn.execute(
                    """
                    INSERT OR IGNORE INTO words
                    (lexicon_id, word, phonetic, meaning, example, next_review_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (lexicon_id, row["word"], row["phonetic"], row["meaning"], row["example"], today),
                )
        self.conn.commit()

    def create_lexicon(self, name: str, source: str = "custom") -> int:
        cursor = self.conn.execute("INSERT OR IGNORE INTO lexicons (name, source) VALUES (?, ?)", (name, source))
        self.conn.commit()
        if cursor.lastrowid:
            return cursor.lastrowid
        return self.conn.execute("SELECT id FROM lexicons WHERE name = ?", (name,)).fetchone()["id"]

    def import_words(self, file_path: str) -> tuple[int, str]:
        path = Path(file_path)
        lexicon_id = self.create_lexicon(path.stem, "import")
        rows = self.parse_word_file(path)
        today = date.today().isoformat()
        imported = 0
        for row in rows:
            word = row.get("word", "").strip()
            meaning = row.get("meaning", "").strip()
            if not word or not meaning:
                continue
            self.conn.execute(
                """
                INSERT OR IGNORE INTO words
                (lexicon_id, word, phonetic, meaning, example, next_review_date)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (lexicon_id, word, row.get("phonetic", "").strip(), meaning, row.get("example", "").strip(), today),
            )
            imported += 1
        self.conn.commit()
        return imported, path.stem

    @staticmethod
    def parse_word_file(path: Path) -> list[dict]:
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

    def lexicons(self):
        return self.conn.execute(
            """
            SELECT l.*,
              COUNT(w.id) AS total,
              SUM(CASE WHEN w.status = 'mastered' THEN 1 ELSE 0 END) AS mastered
            FROM lexicons l
            LEFT JOIN words w ON w.lexicon_id = l.id
            GROUP BY l.id
            ORDER BY l.created_at
            """
        ).fetchall()

    def plan(self):
        return self.conn.execute("SELECT * FROM plans WHERE id = 1").fetchone()

    def save_plan(self, lexicon_id: int, daily_new: int, target_date: str, alpha: float, font_size: int, bg_color: str, widget_size: str):
        current_plan = self.plan()
        current_word_id = current_plan["current_word_id"] if "current_word_id" in current_plan.keys() else None
        if current_plan["lexicon_id"] != lexicon_id:
            current_word_id = None
        self.conn.execute(
            """
            UPDATE plans
            SET lexicon_id = ?, daily_new = ?, target_date = ?, float_alpha = ?,
                font_size = ?, bg_color = ?, widget_size = ?, current_word_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (lexicon_id, daily_new, target_date, alpha, font_size, bg_color, widget_size, current_word_id),
        )
        self.conn.commit()

    def save_float_style(self, alpha: float, font_size: int, bg_color: str, widget_size: str):
        self.conn.execute(
            """
            UPDATE plans
            SET float_alpha = ?, font_size = ?, bg_color = ?, widget_size = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (alpha, font_size, bg_color, widget_size),
        )
        self.conn.commit()

    def next_card(self) -> WordCard | None:
        plan = self.plan()
        lexicon_id = plan["lexicon_id"]
        if not lexicon_id:
            return None
        current_word_id = plan["current_word_id"] if "current_word_id" in plan.keys() else None
        if current_word_id:
            current_card = self.conn.execute(
                """
                SELECT w.*, l.name AS lexicon_name
                FROM words w JOIN lexicons l ON l.id = w.lexicon_id
                WHERE w.id = ? AND w.lexicon_id = ? AND w.status != 'mastered'
                """,
                (current_word_id, lexicon_id),
            ).fetchone()
            if current_card:
                return row_to_card(current_card)
            self.conn.execute("UPDATE plans SET current_word_id = NULL WHERE id = 1")
            self.conn.commit()
        today = date.today().isoformat()
        card = self.conn.execute(
            """
            SELECT w.*, l.name AS lexicon_name
            FROM words w JOIN lexicons l ON l.id = w.lexicon_id
            WHERE w.lexicon_id = ?
              AND w.status != 'mastered'
            ORDER BY
              CASE WHEN w.next_review_date <= ? THEN 0 ELSE 1 END,
              CASE WHEN w.repetitions = 0 THEN 1 ELSE 0 END,
              w.next_review_date,
              w.seen_count,
              w.id
            LIMIT 1
            """,
            (lexicon_id, today),
        ).fetchone()
        if card:
            self.conn.execute("UPDATE plans SET current_word_id = ? WHERE id = 1", (card["id"],))
            self.conn.commit()
        return row_to_card(card) if card else None

    def review(self, word_id: int, rating: int):
        row = self.conn.execute("SELECT * FROM words WHERE id = ?", (word_id,)).fetchone()
        if not row:
            return
        old_interval = row["interval_days"]
        next_state = calculate_srs(row, rating)
        status = STATUS_MASTERED if rating >= 4 and next_state["repetitions"] >= 3 else STATUS_FUZZY if rating >= 3 else STATUS_NEW
        self.conn.execute(
            """
            UPDATE words
            SET status = ?, next_review_date = ?, interval_days = ?, repetitions = ?,
                ease_factor = ?, seen_count = seen_count + 1,
                correct_count = correct_count + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                status,
                next_state["next_review_date"],
                next_state["interval_days"],
                next_state["repetitions"],
                next_state["ease_factor"],
                1 if rating >= 3 else 0,
                word_id,
            ),
        )
        self.conn.execute(
            "INSERT INTO reviews (word_id, rating, old_interval_days, new_interval_days) VALUES (?, ?, ?, ?)",
            (word_id, rating, old_interval, next_state["interval_days"]),
        )
        today = date.today().isoformat()
        self.conn.execute(
            """
            INSERT INTO daily_stats (day, reviewed, known, unknown, new_seen)
            VALUES (?, 1, ?, ?, ?)
            ON CONFLICT(day) DO UPDATE SET
              reviewed = reviewed + 1,
              known = known + excluded.known,
              unknown = unknown + excluded.unknown,
              new_seen = new_seen + excluded.new_seen
            """,
            (today, 1 if rating >= 3 else 0, 1 if rating < 3 else 0, 1 if row["seen_count"] == 0 else 0),
        )
        self.conn.execute("UPDATE plans SET current_word_id = NULL WHERE id = 1 AND current_word_id = ?", (word_id,))
        self.conn.commit()

    def stats(self):
        plan = self.plan()
        lexicon_id = plan["lexicon_id"]
        if not lexicon_id:
            return {}
        summary = self.conn.execute(
            """
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN status = 'mastered' THEN 1 ELSE 0 END) AS mastered,
              SUM(CASE WHEN status = 'fuzzy' THEN 1 ELSE 0 END) AS fuzzy,
              SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) AS fresh,
              SUM(CASE WHEN next_review_date <= date('now', 'localtime') AND status != 'mastered' THEN 1 ELSE 0 END) AS due
            FROM words
            WHERE lexicon_id = ?
            """,
            (lexicon_id,),
        ).fetchone()
        days = self.conn.execute(
            "SELECT * FROM daily_stats WHERE day >= ? ORDER BY day",
            ((date.today() - timedelta(days=29)).isoformat(),),
        ).fetchall()
        return {"summary": summary, "days": days}

    def missing_examples_count(self, lexicon_id: int | None = None) -> int:
        if lexicon_id:
            row = self.conn.execute(
                "SELECT COUNT(*) AS total FROM words WHERE lexicon_id = ? AND (example IS NULL OR TRIM(example) = '')",
                (lexicon_id,),
            ).fetchone()
        else:
            row = self.conn.execute("SELECT COUNT(*) AS total FROM words WHERE example IS NULL OR TRIM(example) = ''").fetchone()
        return int(row["total"] or 0)


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

        self.panel_frame = tk.Frame(self, padx=16, pady=14, bd=0, relief="flat")
        self.panel_frame.pack(fill="both", expand=True)
        self.panel_frame.columnconfigure(0, weight=1)
        self.panel_frame.rowconfigure(1, weight=1)

        self.card_header = tk.Label(self.panel_frame, text="FloatVocab", anchor="w")
        self.card_header.grid(row=0, column=0, sticky="ew")

        self.content_frame = tk.Frame(self.panel_frame, bd=0, relief="flat")
        self.content_frame.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1, minsize=40)
        self.word_label = tk.Label(self.content_frame, text="", font=("Segoe UI", 28, "bold"), wraplength=320, justify="center")
        self.word_label.grid(row=0, column=0, sticky="nsew")
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
            text="Alt+Space 翻面  ·  Alt+Left 不认识  ·  Alt+Right 认识",
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
        for widget in [self.panel_frame, self.content_frame, self.word_label, self.detail_label, self.drag_bar, self.hint_label]:
            widget.bind("<ButtonPress-1>", self.start_move)
            widget.bind("<B1-Motion>", self.move)
        self.resize_grip.bind("<ButtonPress-1>", self.start_resize)
        self.resize_grip.bind("<B1-Motion>", self.resize)

    def apply_style(self):
        plan = self.app.db.plan()
        bg = plan["bg_color"]
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
        for widget in [self.panel_frame, self.content_frame, self.action_frame]:
            widget.configure(bg=bg)
        self.drag_bar.configure(bg=THEME["accent_soft"])
        self.card_header.configure(bg=bg, fg=THEME["muted"], font=("Segoe UI", 10, "bold"))
        self.word_label.configure(bg=bg, fg=THEME["text"])
        self.detail_label.configure(bg=bg, fg=THEME["muted"])
        self.hint_label.configure(bg=bg, fg=THEME["muted"])
        self.resize_grip.configure(bg=bg, fg=THEME["muted"])
        self.unknown_button.configure(
            bg="#FFF2F2",
            fg=THEME["danger"],
            activebackground="#FFE4E4",
            activeforeground=THEME["danger"],
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
        )
        self.flip_button.configure(
            bg=THEME["accent_soft"],
            fg=THEME["accent_active"],
            activebackground="#CBE2FF",
            activeforeground=THEME["accent_active"],
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
        )
        self.known_button.configure(
            bg="#EAF8F1",
            fg=THEME["success"],
            activebackground="#D8F2E4",
            activeforeground=THEME["success"],
            relief="flat",
            bd=0,
            padx=14,
            pady=6,
        )
        self.update_wraplength(wraplength)
        self.word_label.configure(font=("Segoe UI", word_font_size, "bold"))
        self.detail_label.configure(font=("Segoe UI", detail_font_size))

    def show_next(self):
        self.card = self.app.db.next_card()
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
        if not self.card:
            self.word_label.configure(text="今天没有待复习单词")
            self.detail_label.configure(text="可以回到主界面导入词库，或者明天再来继续学习。")
            return
        if self.flipped:
            if self.should_use_compact_flipped_layout():
                self.word_label.configure(font=("Segoe UI", self.word_font_size, "bold"))
                self.word_label.configure(text=self.card.word)
                self.detail_label.configure(text=self.build_flipped_detail(include_example=False))
            else:
                meaning_font_size = max(self.detail_font_size, min(self.word_font_size, 18))
                self.word_label.configure(font=("Segoe UI", meaning_font_size, "bold"))
                self.word_label.configure(text=self.card.meaning)
                self.detail_label.configure(text=self.build_flipped_detail(include_example=True, include_meaning=False))
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

    def mark_known(self):
        if self.card:
            self.app.db.review(self.card.id, 4)
        self.app.refresh_all()
        self.show_next()

    def mark_unknown(self):
        if self.card:
            self.app.db.review(self.card.id, 2)
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
        self.header = tk.Frame(self.container, bg=THEME["hero"], height=44)
        self.header.pack(fill="x")
        self.title_label = tk.Label(self.header, text="日报内容", anchor="w", bg=THEME["hero"], fg=THEME["text"], font=("Segoe UI", 12, "bold"))
        self.title_label.pack(side="left", fill="x", expand=True, padx=16, pady=10)
        self.hide_label = tk.Label(self.header, text="收起", anchor="e", bg=THEME["hero"], fg=THEME["muted"], cursor="hand2", font=("Segoe UI", 10, "bold"))
        self.hide_label.pack(side="right", padx=16)

        self.meta_label = tk.Label(
            self.container,
            text="",
            anchor="w",
            justify="left",
            bg=THEME["panel"],
            fg=THEME["muted"],
            padx=16,
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
            padx=16,
            pady=12,
            relief="flat",
            highlightthickness=0,
            font=("Segoe UI", 11),
            spacing1=3,
            spacing2=3,
            spacing3=6,
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
    def __init__(self):
        self.db = FloatVocabDB(DB_PATH)
        self.root = tk.Tk()
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
        self.root.after(120, self.poll_hotkeys)

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
        ttk.Label(panel, text=title, style="PanelTitle.TLabel").pack(anchor="w")
        if subtitle:
            ttk.Label(panel, text=subtitle, style="Muted.TLabel", wraplength=460, justify="left").pack(anchor="w", pady=(4, 14))
        return panel

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
        ttk.Label(hero, text="FloatVocab", style="HeroTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            hero,
            text="把每日计划、悬浮背词和英语日报放到一个更清晰的学习工作台里。",
            style="HeroBody.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(6, 0))
        hero_actions = ttk.Frame(hero, style="Hero.TFrame")
        hero_actions.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Button(hero_actions, text="显示悬浮窗", style="Primary.TButton", command=self.float_window.show_next).pack(side="left", padx=(0, 10))
        ttk.Button(hero_actions, text="刷新日报", style="Secondary.TButton", command=self.refresh_daily_briefs).pack(side="left")

        self.content_notebook = ttk.Notebook(shell)
        self.content_notebook.grid(row=1, column=0, sticky="nsew", pady=(18, 0))

        dashboard_tab = ttk.Frame(self.content_notebook, style="App.TFrame", padding=8)
        dashboard_tab.columnconfigure(0, weight=1)
        dashboard_tab.columnconfigure(1, weight=1)
        dashboard_tab.rowconfigure(2, weight=1)
        self.content_notebook.add(dashboard_tab, text="学习台")

        plan_box = self.create_panel(dashboard_tab, "学习计划", "先确定词库和每日目标，再进入今天的背词节奏。")
        plan_box.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.lexicon_var = tk.StringVar()
        plan_form = ttk.Frame(plan_box, style="Panel.TFrame")
        plan_form.pack(fill="x")
        plan_form.columnconfigure(0, weight=1)
        plan_form.columnconfigure(1, weight=1)
        ttk.Label(plan_form, text="当前词库", style="SectionLabel.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Label(plan_form, text="目标日期", style="SectionLabel.TLabel").grid(row=0, column=1, sticky="w", padx=(12, 0), pady=(0, 6))
        self.lexicon_combo = ttk.Combobox(plan_form, textvariable=self.lexicon_var, state="readonly")
        self.lexicon_combo.grid(row=1, column=0, sticky="ew", padx=(0, 6))
        self.target_date_var = tk.StringVar()
        ttk.Entry(plan_form, textvariable=self.target_date_var).grid(row=1, column=1, sticky="ew", padx=(6, 0))
        ttk.Label(plan_form, text="每日新词", style="SectionLabel.TLabel").grid(row=2, column=0, sticky="w", pady=(14, 6))
        ttk.Label(plan_form, text="状态", style="SectionLabel.TLabel").grid(row=2, column=1, sticky="w", padx=(12, 0), pady=(14, 6))
        self.daily_new_var = tk.IntVar(value=20)
        ttk.Spinbox(plan_form, from_=1, to=300, textvariable=self.daily_new_var).grid(row=3, column=0, sticky="ew", padx=(0, 6))
        self.example_status_label = ttk.Label(plan_form, text="", style="Muted.TLabel")
        self.example_status_label.grid(row=3, column=1, sticky="w", padx=(12, 0))
        plan_actions = ttk.Frame(plan_box, style="Panel.TFrame")
        plan_actions.pack(fill="x", pady=(16, 0))
        ttk.Button(plan_actions, text="保存计划", style="Secondary.TButton", command=self.save_plan).pack(side="left")
        ttk.Button(plan_actions, text="导入 TXT / CSV 词库", style="Quiet.TButton", command=self.import_words).pack(side="left", padx=(10, 0))
        ttk.Button(plan_actions, text="补全缺失例句", style="Quiet.TButton", command=self.enrich_examples).pack(side="left", padx=(10, 0))

        style_box = self.create_panel(dashboard_tab, "悬浮窗样式", "调整透明度、字号和背景，让桌面复习卡片更顺眼。")
        style_box.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
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
        ttk.Label(style_actions, text="调整后会自动同步到悬浮窗。", style="Muted.TLabel").pack(side="left", padx=(12, 0))
        ttk.Label(style_box, text="全局快捷键：Alt+Space 翻面，Alt+Left 不认识，Alt+Right 认识", style="Muted.TLabel", wraplength=420, justify="left").pack(anchor="w", pady=(12, 0))
        for variable in [self.alpha_var, self.font_size_var, self.bg_color_var, self.widget_size_var]:
            variable.trace_add("write", self.schedule_float_style_save)

        stats_box = self.create_panel(dashboard_tab, "任务统计", "今天的复习完成度和最近 30 天的节奏集中显示在这里。")
        stats_box.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(18, 0))
        self.progress_label = ttk.Label(stats_box, text="", style="Summary.TLabel")
        self.progress_label.pack(anchor="w")
        self.progress = ttk.Progressbar(stats_box, maximum=100, style="App.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(12, 12))
        self.heatmap_frame = tk.Frame(stats_box, bg=THEME["panel"])
        self.heatmap_frame.pack(fill="x")

        words_tab = ttk.Frame(self.content_notebook, style="Panel.TFrame", padding=8)
        words_tab.columnconfigure(0, weight=1)
        words_tab.rowconfigure(1, weight=1)
        self.content_notebook.add(words_tab, text="词库概览")

        ttk.Label(words_tab, text="最近更新的词条会显示在这里，便于快速浏览当前学习内容。", style="Muted.TLabel", wraplength=880, justify="left").grid(row=0, column=0, sticky="w", pady=(0, 10))
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

        news_actions = ttk.Frame(news_tab, style="Panel.TFrame")
        news_actions.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        news_actions.columnconfigure(0, weight=1)
        ttk.Button(news_actions, text="刷新最新 10 篇", style="Quiet.TButton", command=self.refresh_daily_briefs).grid(row=0, column=0, sticky="w")
        ttk.Button(news_actions, text="收藏并翻译", style="Secondary.TButton", command=self.save_selected_brief).grid(row=0, column=1, sticky="e")

        news_content = ttk.Frame(news_tab, style="Panel.TFrame")
        news_content.grid(row=1, column=0, sticky="nsew")
        news_content.columnconfigure(0, weight=1)
        news_content.columnconfigure(1, weight=1)
        news_content.rowconfigure(0, weight=1)

        latest_frame = ttk.Frame(news_content, style="Panel.TFrame")
        latest_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        latest_frame.columnconfigure(0, weight=1)
        latest_frame.rowconfigure(1, weight=1)
        ttk.Label(latest_frame, text="最新日报", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
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
        self.brief_summary = tk.Text(
            latest_frame,
            height=5,
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
        self.brief_summary.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        self.brief_summary.configure(state="disabled")

        favorite_frame = ttk.Frame(news_content, style="Panel.TFrame")
        favorite_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        favorite_frame.columnconfigure(0, weight=1)
        favorite_frame.rowconfigure(1, weight=1)
        ttk.Label(favorite_frame, text="个人收藏", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 8))
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
        self.refresh_stats()
        self.refresh_words()
        self.refresh_brief_list()
        self.refresh_favorite_list()
        self.refresh_example_status()

    def refresh_lexicons(self):
        self.lexicons = self.db.lexicons()
        values = [f"{row['id']} · {row['name']} ({row['mastered'] or 0}/{row['total'] or 0})" for row in self.lexicons]
        self.lexicon_combo["values"] = values
        plan = self.db.plan()
        self.loading_plan = True
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

    def selected_lexicon_id(self):
        value = self.lexicon_var.get()
        return int(value.split(" · ", 1)[0]) if value else None

    def save_plan(self):
        lexicon_id = self.selected_lexicon_id()
        if not lexicon_id:
            messagebox.showwarning(APP_NAME, "请先选择词库。")
            return
        target_date = self.target_date_var.get().strip()
        try:
            datetime.strptime(target_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning(APP_NAME, "目标日期格式应为 YYYY-MM-DD。")
            return
        self.db.save_plan(
            lexicon_id,
            int(self.daily_new_var.get()),
            target_date,
            float(self.alpha_var.get()),
            int(self.font_size_var.get()),
            self.bg_color_var.get().strip() or "#F7FAF5",
            self.widget_size_var.get(),
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
        self.db.save_float_style(
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
            filetypes=[("Word list", "*.txt *.csv"), ("All files", "*.*")],
        )
        if not file_path:
            return
        try:
            count, name = self.db.import_words(file_path)
        except UnicodeDecodeError:
            messagebox.showerror(APP_NAME, "导入失败：请使用 UTF-8 编码保存词库。")
            return
        messagebox.showinfo(APP_NAME, f"已导入 {name}：{count} 个单词。")
        self.refresh_all()

    def refresh_example_status(self):
        lexicon_id = self.selected_lexicon_id() or self.db.plan()["lexicon_id"]
        missing = self.db.missing_examples_count(lexicon_id)
        self.example_status_label.configure(text=f"当前词库还缺 {missing} 条例句")

    def enrich_examples(self):
        lexicon_id = self.selected_lexicon_id() or self.db.plan()["lexicon_id"]
        self.example_status_label.configure(text="正在补全例句...")

        def worker():
            try:
                result = enrich_database(DB_PATH, limit=200, refresh=False, lexicon_id=lexicon_id)
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
        stats = self.db.stats()
        if not stats:
            return
        summary = stats["summary"]
        total = summary["total"] or 0
        mastered = summary["mastered"] or 0
        percent = round((mastered / total) * 100) if total else 0
        self.progress["value"] = percent
        self.progress_label.configure(
            text=f"完成度 {percent}% · 已掌握 {mastered}/{total} · 模糊 {summary['fuzzy'] or 0} · 今日待复习 {summary['due'] or 0}"
        )
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
        lexicon_id = self.selected_lexicon_id() or self.db.plan()["lexicon_id"]
        if not lexicon_id:
            return
        rows = self.db.conn.execute(
            "SELECT word, meaning, status FROM words WHERE lexicon_id = ? ORDER BY updated_at DESC, id",
            (lexicon_id,),
        ).fetchall()
        for row in rows:
            self.words_tree.insert("", "end", values=(row["word"], row["meaning"], status_text(row["status"])))

    def refresh_daily_briefs(self):
        threading.Thread(target=self._refresh_daily_briefs_worker, daemon=True).start()

    def _refresh_daily_briefs_worker(self):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                news_digest.refresh_latest_briefs(conn, limit=10)
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
        rows = news_digest.latest_briefs(self.db.conn, limit=10)
        for row in rows:
            published = (row["published_at"] or "")[:16].replace("T", " ")
            saved_tag = " 已收藏" if row["saved"] else ""
            self.brief_tree.insert("", "end", iid=str(row["id"]), values=(row["source_name"], published, row["title"] + saved_tag))
        self.update_text_widget(self.brief_summary, "")

    def selected_brief_id(self) -> int | None:
        selection = self.brief_tree.selection()
        return int(selection[0]) if selection else None

    def show_selected_brief(self):
        brief_id = self.selected_brief_id()
        if not brief_id:
            self.update_text_widget(self.brief_summary, "")
            return
        row = self.db.conn.execute("SELECT * FROM daily_briefs WHERE id = ?", (brief_id,)).fetchone()
        if not row:
            self.update_text_widget(self.brief_summary, "")
            return
        saved = "已收藏" if row["saved"] else "点击“收藏并翻译”后保存全文"
        content = f"{row['title']}\n{row['summary']}\n\n{saved}\n{row['url']}"
        self.update_text_widget(self.brief_summary, content)

    def save_selected_brief(self):
        brief_id = self.selected_brief_id()
        if not brief_id:
            messagebox.showinfo(APP_NAME, "请先选择一篇日报。")
            return
        threading.Thread(target=self._save_selected_brief_worker, args=(brief_id,), daemon=True).start()

    def _save_selected_brief_worker(self, brief_id: int):
        try:
            with sqlite3.connect(DB_PATH) as conn:
                conn.row_factory = sqlite3.Row
                news_digest.save_brief_to_favorites(conn, brief_id)
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
        rows = news_digest.favorite_articles(self.db.conn)
        for row in rows:
            saved = (row["saved_at"] or "")[:16].replace("T", " ")
            self.favorite_tree.insert("", "end", iid=str(row["id"]), values=(row["source_name"], saved, row["title"]))

    def show_selected_favorite(self):
        selection = self.favorite_tree.selection()
        if not selection:
            return
        article = news_digest.favorite_article_by_id(self.db.conn, int(selection[0]))
        if article:
            self.article_window.show_article(article)

    def update_text_widget(self, widget: tk.Text, content: str):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        if content:
            widget.insert("1.0", content)
        widget.configure(state="disabled")

    def poll_hotkeys(self):
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
        self.root.after(120, self.poll_hotkeys)

    def run(self):
        self.root.mainloop()


def status_text(status: str) -> str:
    return {
        STATUS_NEW: "生词",
        STATUS_FUZZY: "模糊",
        STATUS_MASTERED: "已掌握",
    }.get(status, status)


def main():
    app = FloatVocabApp()
    app.run()


if __name__ == "__main__":
    main()
