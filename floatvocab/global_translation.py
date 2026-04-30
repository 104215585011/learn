from __future__ import annotations

import ctypes
import ctypes.wintypes
import json
import time
from dataclasses import dataclass
from urllib.parse import quote_plus

import news_digest


MAX_SELECTION_CHARS = 600
DEFAULT_BUBBLE_WIDTH = 340
DEFAULT_BUBBLE_HEIGHT = 180
MYMEMORY_TRANSLATE_ENDPOINT = "https://api.mymemory.translated.net/get?q={query}&langpair=en|zh-CN"
MYMEMORY_SOURCE_LANGUAGE_FALLBACKS = ["en", "es", "fr", "ja", "ko", "it", "pt", "ru", "ar", "id"]


def normalize_selection_text(text: str | None, max_chars: int = MAX_SELECTION_CHARS) -> str | None:
    normalized = " ".join(str(text or "").split())
    if not normalized or len(normalized) > max_chars:
        return None
    return normalized


def should_translate_clipboard_text(text: str | None, last_text: str | None = None) -> bool:
    normalized = normalize_selection_text(text)
    if not normalized:
        return False
    if normalized.startswith("__FLOATVOCAB_SELECTION_"):
        return False
    return normalized != normalize_selection_text(last_text)


def capture_window_expired(deadline: float | None, *, now: float | None = None) -> bool:
    if deadline is None:
        return True
    current_time = time.monotonic() if now is None else now
    return current_time >= deadline


def moved_enough_for_selection(start: tuple[int, int] | None, end: tuple[int, int], threshold: int = 6) -> bool:
    if start is None:
        return False
    return abs(end[0] - start[0]) >= threshold or abs(end[1] - start[1]) >= threshold


def calculate_bubble_position(
    pointer_x: int,
    pointer_y: int,
    bubble_width: int,
    bubble_height: int,
    screen_width: int,
    screen_height: int,
    *,
    offset: int = 18,
    margin: int = 12,
) -> tuple[int, int]:
    x = pointer_x + offset
    y = pointer_y + offset
    max_x = max(margin, screen_width - bubble_width - margin)
    max_y = max(margin, screen_height - bubble_height - margin)
    return max(margin, min(x, max_x)), max(margin, min(y, max_y))


def mymemory_language_candidates(source_language_code: str | None = None) -> list[str]:
    normalized = str(source_language_code or "").strip().casefold()
    candidates = []
    if normalized:
        candidates.append(normalized)
    for language_code in MYMEMORY_SOURCE_LANGUAGE_FALLBACKS:
        if language_code not in candidates:
            candidates.append(language_code)
    return candidates


def translate_to_chinese(text: str, source_language_code: str | None = None) -> str:
    for language_code in mymemory_language_candidates(source_language_code):
        try:
            translated = translate_with_mymemory(text, language_code)
        except Exception:  # noqa: BLE001
            translated = ""
        if translated and translated.casefold() != text.casefold():
            return translated
    return news_digest.translate_text(text)


def translate_with_mymemory(text: str, source_language_code: str = "en") -> str:
    endpoint = MYMEMORY_TRANSLATE_ENDPOINT.replace("langpair=en|zh-CN", f"langpair={source_language_code}|zh-CN")
    url = endpoint.format(query=quote_plus(text))
    payload = json.loads(news_digest.fetch_text(url))
    if int(payload.get("responseStatus") or 0) != 200:
        return ""
    response_data = payload.get("responseData") or {}
    return str(response_data.get("translatedText") or "").strip()


@dataclass(frozen=True)
class SelectionRequest:
    text: str
    x: int
    y: int


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG)),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("ki", _KEYBDINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", _INPUTUNION),
    ]


class _POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.wintypes.LONG), ("y", ctypes.wintypes.LONG)]


def current_cursor_position() -> tuple[int, int]:
    if not hasattr(ctypes, "windll") or ctypes.windll is None:
        return 0, 0
    point = _POINT()
    if not ctypes.windll.user32.GetCursorPos(ctypes.byref(point)):
        return 0, 0
    return int(point.x), int(point.y)


def left_mouse_button_down() -> bool:
    if not hasattr(ctypes, "windll") or ctypes.windll is None:
        return False
    return bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)


class WindowsSelectionReader:
    KEYEVENTF_KEYUP = 0x0002
    INPUT_KEYBOARD = 1
    VK_MENU = 0x12
    VK_CONTROL = 0x11
    VK_C = 0x43
    VK_INSERT = 0x2D

    def __init__(self, root, *, copy_delay: float = 0.16):
        self.root = root
        self.copy_delay = copy_delay

    def read_selection(self) -> str | None:
        before_sequence = self._clipboard_sequence_number()
        previous = self._get_clipboard_text()
        self._wait_until_key_released(self.VK_MENU)
        self._release_modifier_keys()
        self._send_ctrl_c()
        time.sleep(self.copy_delay)
        after_sequence = self._clipboard_sequence_number()
        copied = self._get_clipboard_text()
        if after_sequence == before_sequence:
            self._send_ctrl_insert()
            time.sleep(self.copy_delay)
            after_sequence = self._clipboard_sequence_number()
            copied = self._get_clipboard_text()
        if after_sequence == before_sequence:
            return None
        if previous is not None:
            self._set_clipboard_text(previous)
        return normalize_selection_text(copied)

    def _get_clipboard_text(self) -> str | None:
        try:
            return self.root.clipboard_get()
        except Exception:  # noqa: BLE001
            return None

    def _set_clipboard_text(self, text: str) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.root.update_idletasks()

    def _clear_clipboard(self) -> None:
        self.root.clipboard_clear()
        self.root.update_idletasks()

    def _clipboard_sequence_number(self) -> int:
        try:
            return int(ctypes.windll.user32.GetClipboardSequenceNumber())
        except Exception:  # noqa: BLE001
            return time.monotonic_ns()

    def _keyboard_input(self, vk: int, flags: int = 0):
        return _INPUT(
            type=self.INPUT_KEYBOARD,
            union=_INPUTUNION(ki=_KEYBDINPUT(vk, 0, flags, 0, None)),
        )

    def _wait_until_key_released(self, vk: int, timeout: float = 0.35) -> None:
        if not hasattr(ctypes, "windll") or ctypes.windll is None:
            return
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if not ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
                return
            time.sleep(0.01)

    def _release_modifier_keys(self) -> None:
        if not hasattr(ctypes, "windll") or ctypes.windll is None:
            return
        for vk in (self.VK_MENU, self.VK_CONTROL):
            if ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000:
                input_event = self._keyboard_input(vk, self.KEYEVENTF_KEYUP)
                ctypes.windll.user32.SendInput(1, ctypes.byref(input_event), ctypes.sizeof(_INPUT))

    def _send_ctrl_c(self) -> None:
        inputs = (_INPUT * 4)(
            self._keyboard_input(self.VK_CONTROL),
            self._keyboard_input(self.VK_C),
            self._keyboard_input(self.VK_C, self.KEYEVENTF_KEYUP),
            self._keyboard_input(self.VK_CONTROL, self.KEYEVENTF_KEYUP),
        )
        ctypes.windll.user32.SendInput(len(inputs), ctypes.byref(inputs), ctypes.sizeof(_INPUT))

    def _send_ctrl_insert(self) -> None:
        inputs = (_INPUT * 4)(
            self._keyboard_input(self.VK_CONTROL),
            self._keyboard_input(self.VK_INSERT),
            self._keyboard_input(self.VK_INSERT, self.KEYEVENTF_KEYUP),
            self._keyboard_input(self.VK_CONTROL, self.KEYEVENTF_KEYUP),
        )
        ctypes.windll.user32.SendInput(len(inputs), ctypes.byref(inputs), ctypes.sizeof(_INPUT))
