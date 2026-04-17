# FloatVocab Multilingual Learning Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a language-first study flow so the app can switch the current learning language, filter lexicons by that language, import language-scoped word packs, and store daily briefs per language without breaking existing English users.

**Architecture:** Extend the SQLite schema with language fields, thread the active language through repositories and services, and make the `tkinter` homepage choose language before lexicon. Preserve the current review scheduling and article-reading flow; only partition data and UI context by language.

**Tech Stack:** Python, `sqlite3`, `tkinter`/`ttk`, `unittest`, `rg`, Git

---

## File Structure

- Modify: `floatvocab/db.py`
  Purpose: add schema migration hooks for `language_code` and `current_language_code`, seed built-in lexicons with explicit language metadata.
- Modify: `floatvocab/repositories/lexicon_repository.py`
  Purpose: create/list lexicons by language and enforce uniqueness within a language.
- Modify: `floatvocab/repositories/plan_repository.py`
  Purpose: read/write the current language and reset the active lexicon when a language change invalidates it.
- Modify: `floatvocab/repositories/news_repository.py`
  Purpose: list and fetch briefs/favorites within a language scope.
- Modify: `floatvocab/services/settings_service.py`
  Purpose: expose current language settings and language-aware plan updates.
- Modify: `floatvocab/services/news_service.py`
  Purpose: pass `language_code` into news refresh/list/save boundaries.
- Modify: `news_digest.py`
  Purpose: store briefs and favorites per language, filter feed refresh by language, and centralize language-specific feed config.
- Modify: `app.py`
  Purpose: add the current-language selector, filter lexicon choices, update import flow, and make the daily-brief UI labels/context language-aware.
- Modify: `tests/test_services.py`
  Purpose: verify language-aware settings and news service behavior.
- Modify: `tests/test_news_digest_resilience.py`
  Purpose: verify favorite saving and brief storage remain correct with `language_code`.
- Modify: `tests/test_ui_layout.py`
  Purpose: verify the language selector and daily-brief labels appear in the main UI.
- Create: `tests/test_multilingual_schema.py`
  Purpose: cover schema migration and repository uniqueness/filtering behavior.

### Task 1: Add Language-Aware Schema And Repository Foundations

**Files:**
- Create: `tests/test_multilingual_schema.py`
- Modify: `floatvocab/db.py`
- Modify: `floatvocab/repositories/lexicon_repository.py`
- Modify: `floatvocab/repositories/plan_repository.py`

- [ ] **Step 1: Write the failing schema and repository tests**

```python
import sqlite3
import unittest

from floatvocab.db import initialize_database, open_connection
from floatvocab.repositories import LexiconRepository, PlanRepository


class MultilingualSchemaTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

        def passthrough(item, _lexicon_name):
            return item

        initialize_database(
            self.conn,
            builtin_lexicon="data/kaoyan_50.json",
            vocab_source_dir="data/vocab_sources",
            exam_lexicons=[],
            qwerty_item_to_word=passthrough,
        )

    def tearDown(self):
        self.conn.close()

    def test_initialize_database_adds_language_columns_with_english_defaults(self):
        lexicon_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(lexicons)")}
        plan_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(plans)")}
        brief_columns = {row["name"] for row in self.conn.execute("PRAGMA table_info(daily_briefs)")}

        self.assertIn("language_code", lexicon_columns)
        self.assertIn("current_language_code", plan_columns)
        self.assertIn("language_code", brief_columns)
        self.assertEqual(self.conn.execute("SELECT current_language_code FROM plans WHERE id = 1").fetchone()[0], "en")

    def test_same_lexicon_name_is_allowed_across_languages_but_not_within_one_language(self):
        repo = LexiconRepository(self.conn)

        repo.create_lexicon("Core 3000", "en", "test")
        repo.create_lexicon("Core 3000", "ja", "test")

        with self.assertRaises(sqlite3.IntegrityError):
            repo.create_lexicon("Core 3000", "en", "test")

    def test_list_lexicons_filters_by_language(self):
        repo = LexiconRepository(self.conn)
        repo.create_lexicon("English Deck", "en", "test")
        repo.create_lexicon("Spanish Deck", "es", "test")

        english_names = [row["name"] for row in repo.list_lexicons(language_code="en")]
        spanish_names = [row["name"] for row in repo.list_lexicons(language_code="es")]

        self.assertIn("English Deck", english_names)
        self.assertNotIn("Spanish Deck", english_names)
        self.assertEqual(spanish_names, ["Spanish Deck"])

    def test_save_plan_persists_current_language_and_clears_lexicon_when_language_changes(self):
        lexicon_repo = LexiconRepository(self.conn)
        english_id = lexicon_repo.create_lexicon("English Deck", "en", "test")
        spanish_id = lexicon_repo.create_lexicon("Spanish Deck", "es", "test")
        plan_repo = PlanRepository(self.conn)

        plan_repo.save_plan(english_id, 20, "2026-07-01", 0.88, 26, "#F7FAF5", "medium", "en")
        plan_repo.save_plan(spanish_id, 20, "2026-07-01", 0.88, 26, "#F7FAF5", "medium", "es")

        row = plan_repo.fetch_plan()
        self.assertEqual(row["current_language_code"], "es")
        self.assertEqual(row["lexicon_id"], spanish_id)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_multilingual_schema -v`
Expected: FAIL with missing columns such as `language_code` / `current_language_code` and repository signature mismatches.

- [ ] **Step 3: Add language columns and migration helpers in `floatvocab/db.py`**

```python
def _init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS lexicons (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          language_code TEXT NOT NULL DEFAULT 'en',
          source TEXT NOT NULL DEFAULT 'built-in',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(language_code, name)
        );

        CREATE TABLE IF NOT EXISTS plans (
          id INTEGER PRIMARY KEY CHECK (id = 1),
          lexicon_id INTEGER,
          current_language_code TEXT NOT NULL DEFAULT 'en',
          daily_new INTEGER NOT NULL DEFAULT 20,
          target_date TEXT,
          float_alpha REAL NOT NULL DEFAULT 0.88,
          font_size INTEGER NOT NULL DEFAULT 26,
          bg_color TEXT NOT NULL DEFAULT '#F7FAF5',
          widget_size TEXT NOT NULL DEFAULT 'medium',
          updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (lexicon_id) REFERENCES lexicons(id) ON DELETE SET NULL
        );
        """
    )
    _ensure_plan_columns(conn)
    _ensure_lexicon_columns(conn)


def _ensure_lexicon_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(lexicons)").fetchall()}
    if "language_code" not in columns:
        conn.execute("ALTER TABLE lexicons ADD COLUMN language_code TEXT NOT NULL DEFAULT 'en'")


def _ensure_plan_columns(conn: sqlite3.Connection) -> None:
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(plans)").fetchall()}
    if "current_language_code" not in columns:
        conn.execute("ALTER TABLE plans ADD COLUMN current_language_code TEXT NOT NULL DEFAULT 'en'")
```

- [ ] **Step 4: Seed built-in lexicons as English**

```python
def _seed_builtin_lexicon(conn: sqlite3.Connection, builtin_lexicon: Path) -> None:
    if conn.execute(
        "SELECT 1 FROM lexicons WHERE name = ? AND language_code = ?",
        ("Kaoyan Core 50", "en"),
    ).fetchone():
        return
    lexicon_id = _create_lexicon(conn, "Kaoyan Core 50", "en", "built-in")


def _seed_exam_lexicons(...):
    ...
        if conn.execute(
            "SELECT 1 FROM lexicons WHERE name = ? AND language_code = ?",
            (lexicon_name, "en"),
        ).fetchone():
            continue
        lexicon_id = _create_lexicon(conn, lexicon_name, "en", "built-in")
```

- [ ] **Step 5: Make repository methods language-aware**

```python
class LexiconRepository:
    def create_lexicon(self, name: str, language_code: str, source: str = "custom") -> int:
        cursor = self.conn.execute(
            "INSERT INTO lexicons (name, language_code, source) VALUES (?, ?, ?)",
            (name, language_code, source),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def list_lexicons(self, language_code: str | None = None):
        if language_code is None:
            return self.conn.execute("SELECT * FROM lexicons ORDER BY language_code, created_at").fetchall()
        return self.conn.execute(
            """
            SELECT l.*, COUNT(w.id) AS total,
                   SUM(CASE WHEN w.status = 'mastered' THEN 1 ELSE 0 END) AS mastered
            FROM lexicons l
            LEFT JOIN words w ON w.lexicon_id = l.id
            WHERE l.language_code = ?
            GROUP BY l.id
            ORDER BY l.created_at
            """,
            (language_code,),
        ).fetchall()

    def import_word_rows(self, lexicon_name: str, language_code: str, rows: list[dict], source: str = "import") -> int:
        lexicon_id = self.create_lexicon(lexicon_name, language_code, source)
        ...
```

- [ ] **Step 6: Persist current language in `PlanRepository`**

```python
class PlanRepository:
    def save_plan(
        self,
        lexicon_id: int | None,
        daily_new: int,
        target_date: str,
        alpha: float,
        font_size: int,
        bg_color: str,
        widget_size: str,
        current_language_code: str,
    ) -> None:
        current_plan = self.fetch_plan()
        current_word_id = current_plan["current_word_id"] if "current_word_id" in current_plan.keys() else None
        if current_plan["current_language_code"] != current_language_code:
            current_word_id = None
        self.conn.execute(
            """
            UPDATE plans
            SET lexicon_id = ?, current_language_code = ?, daily_new = ?, target_date = ?,
                float_alpha = ?, font_size = ?, bg_color = ?, widget_size = ?,
                current_word_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            """,
            (lexicon_id, current_language_code, daily_new, target_date, alpha, font_size, bg_color, widget_size, current_word_id),
        )
        self.conn.commit()
```

- [ ] **Step 7: Run test to verify it passes**

Run: `python -m unittest tests.test_multilingual_schema -v`
Expected: PASS for all schema/repository migration tests.

- [ ] **Step 8: Commit**

```bash
git add tests/test_multilingual_schema.py floatvocab/db.py floatvocab/repositories/lexicon_repository.py floatvocab/repositories/plan_repository.py
git commit -m "feat: add multilingual schema foundations"
```

### Task 2: Make News And Settings Services Language-Aware

**Files:**
- Modify: `news_digest.py`
- Modify: `floatvocab/repositories/news_repository.py`
- Modify: `floatvocab/services/news_service.py`
- Modify: `floatvocab/services/settings_service.py`
- Modify: `tests/test_services.py`
- Modify: `tests/test_news_digest_resilience.py`

- [ ] **Step 1: Write the failing service and news-digest tests**

```python
def test_settings_service_switch_language_keeps_same_shape_and_passes_language_to_db(self):
    service = app.SettingsService(self.db)

    with mock.patch.object(self.db, "save_plan", return_value=None) as save_plan_mock:
        service.save_plan(
            lexicon_id=7,
            daily_new=18,
            target_date="2026-04-15",
            alpha=0.92,
            font_size=24,
            bg_color="#FAFAFA",
            widget_size="large",
            current_language_code="ja",
        )

    save_plan_mock.assert_called_once_with(7, 18, "2026-04-15", 0.92, 24, "#FAFAFA", "large", "ja")


def test_news_service_refresh_latest_briefs_passes_language_code(self):
    sentinel_conn = mock.Mock(spec=sqlite3.Connection)
    connection_context = mock.MagicMock()
    connection_context.__enter__.return_value = sentinel_conn
    connection_factory = mock.Mock(return_value=connection_context)

    with mock.patch.object(app.news_digest, "refresh_latest_briefs", return_value=[]) as refresh_mock:
        service = app.NewsService(self.db_path, connection_factory=connection_factory)
        service.refresh_latest_briefs(language_code="es", limit=10)

    refresh_mock.assert_called_once_with(sentinel_conn, language_code="es", limit=10)
```

```python
def test_latest_briefs_are_filtered_by_language(self):
    self.conn.execute(
        """
        INSERT INTO daily_briefs (id, language_code, source_key, source_name, title, summary, url, published_at, saved)
        VALUES (2, 'es', 'bbc_mundo', 'BBC Mundo', 'Titulo', 'Resumen', 'https://example.com/es', '2026-04-16T10:00:00', 0)
        """
    )
    self.conn.commit()

    english_rows = news_digest.latest_briefs(self.conn, language_code="en", limit=10)
    spanish_rows = news_digest.latest_briefs(self.conn, language_code="es", limit=10)

    self.assertEqual({row["language_code"] for row in english_rows}, {"en"})
    self.assertEqual({row["language_code"] for row in spanish_rows}, {"es"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_services tests.test_news_digest_resilience -v`
Expected: FAIL with unexpected keyword arguments such as `current_language_code` and `language_code`.

- [ ] **Step 3: Add language-aware schema and feed config in `news_digest.py`**

```python
LANGUAGE_FEEDS = {
    "en": [
        {"key": "bbc_world", "name": "BBC World", "feed": "https://feeds.bbci.co.uk/news/world/rss.xml"},
        {"key": "reuters_world", "name": "Reuters World", "feed": "https://feeds.reuters.com/Reuters/worldNews"},
    ],
    "es": [
        {"key": "bbc_mundo", "name": "BBC Mundo", "feed": "https://feeds.bbci.co.uk/mundo/rss.xml"},
    ],
}


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS daily_briefs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          language_code TEXT NOT NULL DEFAULT 'en',
          source_key TEXT NOT NULL,
          source_name TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          url TEXT NOT NULL,
          published_at TEXT NOT NULL DEFAULT '',
          fetched_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          saved INTEGER NOT NULL DEFAULT 0,
          UNIQUE(language_code, url)
        );

        CREATE TABLE IF NOT EXISTS favorite_articles (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          brief_id INTEGER NOT NULL UNIQUE,
          language_code TEXT NOT NULL DEFAULT 'en',
          source_key TEXT NOT NULL,
          source_name TEXT NOT NULL,
          title TEXT NOT NULL,
          summary TEXT NOT NULL DEFAULT '',
          url TEXT NOT NULL UNIQUE,
          published_at TEXT NOT NULL DEFAULT '',
          content_text TEXT NOT NULL DEFAULT '',
          bilingual_text TEXT NOT NULL DEFAULT '',
          metadata_json TEXT NOT NULL DEFAULT '{}',
          saved_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
```

- [ ] **Step 4: Filter refresh/list/save operations by language**

```python
def refresh_latest_briefs(conn: sqlite3.Connection, language_code: str, limit: int = 10) -> list[sqlite3.Row]:
    briefs = list(fetch_briefs(language_code, limit))
    for brief in briefs:
        conn.execute(
            """
            INSERT INTO daily_briefs (language_code, source_key, source_name, title, summary, url, published_at, fetched_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(language_code, url) DO UPDATE SET
              source_key = excluded.source_key,
              source_name = excluded.source_name,
              title = excluded.title,
              summary = excluded.summary,
              published_at = excluded.published_at,
              fetched_at = CURRENT_TIMESTAMP
            """,
            (language_code, brief.source_key, brief.source_name, brief.title, brief.summary, brief.url, brief.published_at),
        )
    conn.commit()
    return latest_briefs(conn, language_code=language_code, limit=limit)


def latest_briefs(conn: sqlite3.Connection, language_code: str, limit: int = 10) -> list[sqlite3.Row]:
    return conn.execute(
        """
        SELECT *
        FROM daily_briefs
        WHERE language_code = ?
        ORDER BY published_at DESC, fetched_at DESC, id DESC
        LIMIT ?
        """,
        (language_code, limit),
    ).fetchall()
```

- [ ] **Step 5: Update repository and service method signatures**

```python
class NewsRepository:
    def list_latest_briefs(self, language_code: str, limit: int = 10):
        return self.conn.execute(
            """
            SELECT *
            FROM daily_briefs
            WHERE language_code = ?
            ORDER BY published_at DESC, fetched_at DESC, id DESC
            LIMIT ?
            """,
            (language_code, limit),
        ).fetchall()


class NewsService:
    def refresh_latest_briefs(self, language_code: str, limit: int = 10):
        with self.connection_factory(self.db_path) as conn:
            if hasattr(conn, "row_factory"):
                conn.row_factory = sqlite3.Row
            return self.news_digest.refresh_latest_briefs(conn, language_code=language_code, limit=limit)

    def list_latest_briefs(self, language_code: str, limit: int = 10):
        ...

    def list_favorite_articles(self, language_code: str):
        ...

    def save_brief_to_favorites(self, brief_id: int, language_code: str):
        ...


class SettingsService:
    def save_plan(..., current_language_code: str):
        return self.db.save_plan(
            lexicon_id,
            daily_new,
            target_date,
            alpha,
            font_size,
            bg_color,
            widget_size,
            current_language_code,
        )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m unittest tests.test_services tests.test_news_digest_resilience -v`
Expected: PASS for all language-aware service and news-digest tests.

- [ ] **Step 7: Commit**

```bash
git add news_digest.py floatvocab/repositories/news_repository.py floatvocab/services/news_service.py floatvocab/services/settings_service.py tests/test_services.py tests/test_news_digest_resilience.py
git commit -m "feat: add multilingual news and settings services"
```

### Task 3: Add Language-First UI Flow And Language-Scoped Imports

**Files:**
- Modify: `app.py`
- Modify: `floatvocab/repositories/lexicon_repository.py`
- Modify: `tests/test_ui_layout.py`
- Modify: `tests/test_services.py`

- [ ] **Step 1: Write the failing UI tests**

```python
def test_build_ui_renders_current_language_selector(self):
    app_instance = app.FloatVocabApp(root=self.root, db=self.db, news_service=self.news_service)
    app_instance.build_ui()

    self.assertTrue(hasattr(app_instance, "language_var"))
    self.assertEqual(app_instance.language_combo.cget("state"), "readonly")


def test_refresh_words_uses_current_language_filtered_lexicons(self):
    english_id = self.db.create_lexicon("English Deck", "en", "test")
    self.db.create_lexicon("Spanish Deck", "es", "test")
    self.db.save_plan(english_id, 20, "2026-06-01", 0.88, 26, "#F7FAF5", "medium", "en")

    app_instance = app.FloatVocabApp(root=self.root, db=self.db, news_service=self.news_service)
    app_instance.build_ui()
    app_instance.refresh_plan_controls()

    combo_values = list(app_instance.lexicon_combo.cget("values"))
    self.assertIn("English Deck", combo_values)
    self.assertNotIn("Spanish Deck", combo_values)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_ui_layout -v`
Expected: FAIL with missing `language_var` / `language_combo` and stale lexicon filtering assumptions.

- [ ] **Step 3: Add supported-language metadata and language selector state in `app.py`**

```python
SUPPORTED_LANGUAGES = [
    ("en", "English"),
    ("es", "Spanish"),
    ("fr", "French"),
    ("ko", "Korean"),
    ("ja", "Japanese"),
    ("it", "Italian"),
    ("id", "Indonesian"),
    ("ru", "Russian"),
    ("ar", "Arabic"),
    ("pt", "Portuguese"),
]


class FloatVocabApp:
    def __init__(...):
        ...
        self.language_var = tk.StringVar()
        self.language_options = dict(SUPPORTED_LANGUAGES)
        self.lexicon_lookup: dict[str, int] = {}
```

- [ ] **Step 4: Put the language selector above the lexicon selector**

```python
ttk.Label(plan_form, text="Current Language", style="SectionLabel.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 6))
self.language_combo = ttk.Combobox(
    plan_form,
    textvariable=self.language_var,
    state="readonly",
    values=[label for _, label in SUPPORTED_LANGUAGES],
)
self.language_combo.grid(row=1, column=0, sticky="ew")
self.language_combo.bind("<<ComboboxSelected>>", lambda _event: self.on_language_changed())

ttk.Label(plan_form, text="Current Lexicon", style="SectionLabel.TLabel").grid(row=2, column=0, sticky="w", pady=(14, 6))
self.lexicon_combo = ttk.Combobox(plan_form, textvariable=self.lexicon_var, state="readonly")
self.lexicon_combo.grid(row=3, column=0, sticky="ew")
```

- [ ] **Step 5: Filter lexicons and daily-brief labels by the active language**

```python
def current_language_code(self) -> str:
    label = self.language_var.get()
    for code, name in SUPPORTED_LANGUAGES:
        if name == label:
            return code
    return "en"


def refresh_plan_controls(self):
    plan = self.settings_service.get_plan_settings()
    current_language_code = plan["current_language_code"] or "en"
    self.language_var.set(dict(SUPPORTED_LANGUAGES)[current_language_code])
    rows = self.db.list_lexicons(language_code=current_language_code)
    self.lexicon_lookup = {row["name"]: row["id"] for row in rows}
    self.lexicon_combo.configure(values=list(self.lexicon_lookup))


def refresh_daily_briefs(self):
    language_code = self.current_language_code()
    self.news_service.refresh_latest_briefs(language_code=language_code, limit=10)
    self.content_notebook.tab(self.news_tab, text=f"{self.language_options[language_code]} Daily Briefs")
```

- [ ] **Step 6: Make imports default to the active language**

```python
def import_words(self):
    file_path = filedialog.askopenfilename(...)
    if not file_path:
        return
    language_code = self.current_language_code()
    count, name = self.db.import_words(file_path, language_code=language_code)
    messagebox.showinfo(APP_NAME, f"Imported {count} words into {self.language_options[language_code]} / {name}.")


class FloatVocabDB:
    def import_words(self, file_path: str, language_code: str) -> tuple[int, str]:
        ...
        file_language_code = rows[0].get("language_code", "").strip() if rows else ""
        effective_language_code = file_language_code or language_code
        count = self.lexicon_repository.import_word_rows(name, effective_language_code, rows, source="import")
        return count, name
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `python -m unittest tests.test_ui_layout tests.test_services -v`
Expected: PASS, including new language selector and language-scoped import behavior.

- [ ] **Step 8: Commit**

```bash
git add app.py floatvocab/repositories/lexicon_repository.py tests/test_ui_layout.py tests/test_services.py
git commit -m "feat: add language-first app flow"
```

### Task 4: End-To-End Verification And Regression Cleanup

**Files:**
- Modify: `tests/test_services.py`
- Modify: `tests/test_news_digest_resilience.py`
- Modify: `tests/test_ui_layout.py`
- Modify: `tests/test_multilingual_schema.py`
- Modify: `app.py`
- Modify: `news_digest.py`

- [ ] **Step 1: Add one end-to-end regression test for empty-language handling**

```python
def test_switching_to_language_with_no_lexicons_clears_lexicon_selection(self):
    english_id = self.db.create_lexicon("English Deck", "en", "test")
    self.db.save_plan(english_id, 20, "2026-06-01", 0.88, 26, "#F7FAF5", "medium", "en")

    app_instance = app.FloatVocabApp(root=self.root, db=self.db, news_service=self.news_service)
    app_instance.build_ui()
    app_instance.language_var.set("French")
    app_instance.on_language_changed()

    self.assertEqual(app_instance.lexicon_var.get(), "")
    self.assertEqual(list(app_instance.lexicon_combo.cget("values")), [])
```

- [ ] **Step 2: Run the targeted multilingual suite**

Run: `python -m unittest tests.test_multilingual_schema tests.test_services tests.test_news_digest_resilience tests.test_ui_layout -v`
Expected: PASS for all multilingual tests and no legacy English regression failures.

- [ ] **Step 3: Run the broader existing regression suite**

Run: `python -m unittest tests.test_study_state tests.test_services tests.test_async_error_callbacks tests.test_news_digest_resilience tests.test_ui_layout -v`
Expected: PASS with the existing study-state and async callback tests still green.

- [ ] **Step 4: Smoke-check the app boots after schema migration**

Run: `python -m py_compile app.py floatvocab/db.py floatvocab/repositories/lexicon_repository.py floatvocab/repositories/plan_repository.py floatvocab/services/settings_service.py floatvocab/services/news_service.py news_digest.py`
Expected: no output and exit code 0.

- [ ] **Step 5: Commit**

```bash
git add tests/test_multilingual_schema.py tests/test_services.py tests/test_news_digest_resilience.py tests/test_ui_layout.py app.py news_digest.py
git commit -m "test: verify multilingual learning flow"
```

## Self-Review

### Spec Coverage

- Language-first entry flow: covered by Task 3.
- Lexicon language ownership and name-collision rules: covered by Task 1.
- Plan-level current language storage: covered by Task 1 and Task 2.
- Language-aware briefs/favorites: covered by Task 2.
- Language-scoped imports and empty states: covered by Task 3 and Task 4.
- Regression and rollout safety: covered by Task 4.

### Placeholder Scan

- No `TODO`, `TBD`, or deferred implementation markers remain.
- Each task includes concrete file paths, commands, and code snippets.

### Type Consistency

- `language_code` is the shared persistence/service/news field name throughout the plan.
- `current_language_code` is reserved for the app-level plan state.
- `save_plan(..., current_language_code)` is used consistently across repository, service, and UI tasks.
