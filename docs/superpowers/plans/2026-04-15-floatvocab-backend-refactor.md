# FloatVocab Backend Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the desktop app's internal backend into repository and service layers while preserving current behavior and data compatibility.

**Architecture:** Introduce a new `floatvocab` package that owns models, database bootstrap, repositories, and services. Keep `news_digest.py`, `example_pipeline.py`, and the Tk UI behavior intact at first, then route the UI through service interfaces so `app.py` becomes a composition entry point instead of the main business-logic container.

**Tech Stack:** Python, tkinter, sqlite3, unittest

---

## File Structure

- Create: `C:\Users\wang\learn\floatvocab\__init__.py`
  - package marker and compatibility exports used by `app.py`
- Create: `C:\Users\wang\learn\floatvocab\models.py`
  - data classes and row-to-model helpers shared across layers
- Create: `C:\Users\wang\learn\floatvocab\db.py`
  - connection factory and schema/bootstrap logic for the local SQLite database
- Create: `C:\Users\wang\learn\floatvocab\repositories\__init__.py`
  - repository package exports
- Create: `C:\Users\wang\learn\floatvocab\repositories\lexicon_repository.py`
  - lexicon import, parse, and recent-word queries
- Create: `C:\Users\wang\learn\floatvocab\repositories\plan_repository.py`
  - read/save plan and floating-style persistence
- Create: `C:\Users\wang\learn\floatvocab\repositories\study_repository.py`
  - review queue selection, review persistence, and stats queries
- Create: `C:\Users\wang\learn\floatvocab\repositories\news_repository.py`
  - latest briefs, favorites, and brief/article fetches from SQLite
- Create: `C:\Users\wang\learn\floatvocab\services\__init__.py`
  - service package exports
- Create: `C:\Users\wang\learn\floatvocab\services\settings_service.py`
  - plan validation and settings save/load APIs
- Create: `C:\Users\wang\learn\floatvocab\services\study_service.py`
  - card selection, review submission, words list, and stats APIs
- Create: `C:\Users\wang\learn\floatvocab\services\news_service.py`
  - news refresh, preview, favorites, and save-to-favorites APIs
- Create: `C:\Users\wang\learn\floatvocab\services\enrichment_service.py`
  - example enrichment APIs and result forwarding
- Modify: `C:\Users\wang\learn\app.py`
  - replace embedded backend logic with imports from the new package
  - keep UI/window behavior compatible while routing through services
- Modify: `C:\Users\wang\learn\tests\test_study_state.py`
  - keep regression test aligned with the exported compatibility API
- Modify: `C:\Users\wang\learn\tests\test_async_error_callbacks.py`
  - keep async error callback regression aligned with app wiring
- Modify: `C:\Users\wang\learn\tests\test_news_digest_resilience.py`
  - extend coverage to the service boundary
- Create: `C:\Users\wang\learn\tests\test_services.py`
  - service-level regression tests for study/settings/news/enrichment boundaries
- Read during implementation:
  - `C:\Users\wang\learn\docs\superpowers\specs\2026-04-15-floatvocab-backend-refactor-design.md`
  - `C:\Users\wang\learn\news_digest.py`
  - `C:\Users\wang\learn\example_pipeline.py`

### Task 1: Lock In Service Boundary Tests First

**Files:**
- Modify: `C:\Users\wang\learn\tests\test_news_digest_resilience.py`
- Create: `C:\Users\wang\learn\tests\test_services.py`
- Read: `C:\Users\wang\learn\tests\test_study_state.py`

- [ ] **Step 1: Add a failing test for study review flow through a future service boundary**

```python
def test_study_service_next_card_and_review_updates_resume_state():
    db = app.FloatVocabDB(TEST_DB_PATH)
    service = app.StudyService(db)

    first = service.get_next_card()
    assert first is not None
    assert db.plan()["current_word_id"] == first.id

    service.submit_review(first.id, 4)

    assert db.plan()["current_word_id"] is None
```

- [ ] **Step 2: Add a failing test for settings validation through a future service boundary**

```python
def test_settings_service_rejects_invalid_target_date():
    db = app.FloatVocabDB(TEST_DB_PATH)
    service = app.SettingsService(db)

    with pytest.raises(ValueError):
        service.save_plan(
            lexicon_id=1,
            daily_new=20,
            target_date="2026/04/15",
            alpha=0.88,
            font_size=26,
            bg_color="#FFFFFF",
            widget_size="medium",
        )
```

- [ ] **Step 3: Add a failing test for news save through a future service boundary**

```python
def test_news_service_save_brief_to_favorites_delegates_to_news_digest():
    service = app.NewsService(TEST_DB_PATH)

    with mock.patch.object(app.news_digest, "save_brief_to_favorites") as save_mock:
        service.save_brief_to_favorites(brief_id=1)

    assert save_mock.called
```

- [ ] **Step 4: Run the focused tests to verify they fail for the expected missing service symbols**

Run: `python -m unittest tests.test_services -v`
Expected: FAIL with import or attribute errors for `StudyService`, `SettingsService`, or `NewsService`

- [ ] **Step 5: Commit**

```bash
git add tests/test_services.py tests/test_news_digest_resilience.py
git commit -m "test: add backend service boundary regressions"
```

### Task 2: Extract Models And Database Bootstrap

**Files:**
- Create: `C:\Users\wang\learn\floatvocab\__init__.py`
- Create: `C:\Users\wang\learn\floatvocab\models.py`
- Create: `C:\Users\wang\learn\floatvocab\db.py`
- Modify: `C:\Users\wang\learn\app.py`

- [ ] **Step 1: Create the package root and move shared data objects into `models.py`**

```python
from dataclasses import dataclass


@dataclass
class WordCard:
    id: int
    word: str
    phonetic: str
    meaning: str
    example: str
    status: str
    lexicon_name: str
```

- [ ] **Step 2: Create a database bootstrap module that owns connection setup and schema initialization**

```python
def open_connection(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(conn: sqlite3.Connection) -> None:
    init_learning_schema(conn)
    news_digest.ensure_schema(conn)
    ensure_plan_columns(conn)
    ensure_word_columns(conn)
    seed_builtin_lexicons(conn)
```

- [ ] **Step 3: Update `FloatVocabDB` to delegate bootstrap responsibilities**

```python
class FloatVocabDB:
    def __init__(self, db_path: Path):
        self.conn = open_connection(db_path)
        initialize_database(self.conn)
```

- [ ] **Step 4: Run the study-state regression to verify schema compatibility still works**

Run: `python -m unittest tests.test_study_state -v`
Expected: PASS and `current_word_id` behavior remains unchanged

- [ ] **Step 5: Commit**

```bash
git add floatvocab/__init__.py floatvocab/models.py floatvocab/db.py app.py tests/test_study_state.py
git commit -m "refactor: extract database bootstrap and shared models"
```

### Task 3: Extract Repository Layer Behind Existing Logic

**Files:**
- Create: `C:\Users\wang\learn\floatvocab\repositories\__init__.py`
- Create: `C:\Users\wang\learn\floatvocab\repositories\lexicon_repository.py`
- Create: `C:\Users\wang\learn\floatvocab\repositories\plan_repository.py`
- Create: `C:\Users\wang\learn\floatvocab\repositories\study_repository.py`
- Create: `C:\Users\wang\learn\floatvocab\repositories\news_repository.py`
- Modify: `C:\Users\wang\learn\app.py`

- [ ] **Step 1: Write repository wrappers that own the SQL currently embedded in `FloatVocabDB`**

```python
class PlanRepository:
    def __init__(self, conn):
        self.conn = conn

    def fetch_plan(self):
        return self.conn.execute("SELECT * FROM plans WHERE id = 1").fetchone()

    def save_plan(self, lexicon_id, daily_new, target_date, alpha, font_size, bg_color, widget_size, current_word_id):
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
```

- [ ] **Step 2: Route `FloatVocabDB` methods through repositories without changing its public API**

```python
class FloatVocabDB:
    def __init__(self, db_path: Path):
        self.conn = open_connection(db_path)
        initialize_database(self.conn)
        self.lexicons_repo = LexiconRepository(self.conn)
        self.plan_repo = PlanRepository(self.conn)
        self.study_repo = StudyRepository(self.conn)
        self.news_repo = NewsRepository(self.conn)
```

- [ ] **Step 3: Keep helper functions like `calculate_srs` and row mapping stable for now**

```python
def calculate_srs(row, rating: int):
    ...
```

- [ ] **Step 4: Run service-boundary tests plus existing study tests**

Run: `python -m unittest tests.test_study_state tests.test_services -v`
Expected: study regressions stay green while service tests still fail only for missing service classes

- [ ] **Step 5: Commit**

```bash
git add floatvocab/repositories floatvocab/models.py app.py tests/test_services.py tests/test_study_state.py
git commit -m "refactor: move backend SQL into repositories"
```

### Task 4: Introduce Settings And Study Services

**Files:**
- Create: `C:\Users\wang\learn\floatvocab\services\__init__.py`
- Create: `C:\Users\wang\learn\floatvocab\services\settings_service.py`
- Create: `C:\Users\wang\learn\floatvocab\services\study_service.py`
- Modify: `C:\Users\wang\learn\app.py`
- Modify: `C:\Users\wang\learn\tests\test_services.py`

- [ ] **Step 1: Implement `SettingsService` with validation and pass-through persistence**

```python
class SettingsService:
    def __init__(self, db):
        self.db = db

    def save_plan(self, lexicon_id, daily_new, target_date, alpha, font_size, bg_color, widget_size):
        datetime.strptime(target_date, "%Y-%m-%d")
        self.db.save_plan(lexicon_id, daily_new, target_date, alpha, font_size, bg_color, widget_size)
```

- [ ] **Step 2: Implement `StudyService` with next-card, review, stats, and recent-words methods**

```python
class StudyService:
    def __init__(self, db):
        self.db = db

    def get_next_card(self):
        return self.db.next_card()

    def submit_review(self, word_id: int, rating: int):
        self.db.review(word_id, rating)
```

- [ ] **Step 3: Export the new service classes from both `floatvocab` and `app.py` compatibility imports**

```python
from floatvocab.services import SettingsService, StudyService
```

- [ ] **Step 4: Run the service tests to verify the new study/settings APIs pass**

Run: `python -m unittest tests.test_services -v`
Expected: PASS for study and settings service coverage, any remaining failures isolated to news/enrichment services

- [ ] **Step 5: Commit**

```bash
git add floatvocab/services/__init__.py floatvocab/services/settings_service.py floatvocab/services/study_service.py app.py tests/test_services.py
git commit -m "refactor: add study and settings services"
```

### Task 5: Introduce News And Enrichment Services

**Files:**
- Create: `C:\Users\wang\learn\floatvocab\services\news_service.py`
- Create: `C:\Users\wang\learn\floatvocab\services\enrichment_service.py`
- Modify: `C:\Users\wang\learn\tests\test_news_digest_resilience.py`
- Modify: `C:\Users\wang\learn\tests\test_services.py`
- Modify: `C:\Users\wang\learn\app.py`

- [ ] **Step 1: Implement `NewsService` as the only application-layer caller of `news_digest`**

```python
class NewsService:
    def __init__(self, db_path: Path, connection_factory=open_connection):
        self.db_path = db_path
        self.connection_factory = connection_factory

    def save_brief_to_favorites(self, brief_id: int):
        with self.connection_factory(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            return news_digest.save_brief_to_favorites(conn, brief_id)
```

- [ ] **Step 2: Implement `EnrichmentService` as a thin wrapper over `enrich_database(...)`**

```python
class EnrichmentService:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def enrich_examples(self, lexicon_id=None, limit=200, refresh=False):
        return enrich_database(self.db_path, limit=limit, refresh=refresh, lexicon_id=lexicon_id)
```

- [ ] **Step 3: Update tests to assert service-level fallback and delegation behavior**

```python
def test_enrichment_service_forwards_result_shape():
    service = app.EnrichmentService(TEST_DB_PATH)
    with mock.patch.object(app, "enrich_database", return_value={"processed": 1, "updated": 1, "skipped": 0, "failures": []}):
        result = service.enrich_examples()
    assert result["updated"] == 1
```

- [ ] **Step 4: Run the service and news regression suite**

Run: `python -m unittest tests.test_services tests.test_news_digest_resilience -v`
Expected: PASS with existing fallback behavior preserved

- [ ] **Step 5: Commit**

```bash
git add floatvocab/services/news_service.py floatvocab/services/enrichment_service.py app.py tests/test_services.py tests/test_news_digest_resilience.py
git commit -m "refactor: add news and enrichment services"
```

### Task 6: Route Tk UI Methods Through Services And Remove Direct SQL

**Files:**
- Modify: `C:\Users\wang\learn\app.py`
- Modify: `C:\Users\wang\learn\tests\test_async_error_callbacks.py`
- Modify: `C:\Users\wang\learn\tests\test_ui_layout.py`

- [ ] **Step 1: Inject services into `FloatVocabApp` during initialization**

```python
class FloatVocabApp:
    def __init__(self):
        self.db = FloatVocabDB(DB_PATH)
        self.settings_service = SettingsService(self.db)
        self.study_service = StudyService(self.db)
        self.news_service = NewsService(DB_PATH)
        self.enrichment_service = EnrichmentService(DB_PATH)
```

- [ ] **Step 2: Replace direct database reads in UI refresh methods with service calls**

```python
def refresh_words(self):
    rows = self.study_service.get_recent_words(self.selected_lexicon_id() or self.db.plan()["lexicon_id"], limit=80)
```

- [ ] **Step 3: Replace direct `news_digest` calls in worker methods with `NewsService`**

```python
def _save_selected_brief_worker(self, brief_id: int):
    try:
        self.news_service.save_brief_to_favorites(brief_id)
    except Exception as exc:
        ...
```

- [ ] **Step 4: Run the UI-facing regression tests**

Run: `python -m unittest tests.test_async_error_callbacks tests.test_ui_layout -v`
Expected: PASS with callback behavior and tab layout unchanged

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_async_error_callbacks.py tests/test_ui_layout.py
git commit -m "refactor: route desktop UI through backend services"
```

### Task 7: Reduce `app.py` To Composition And Run Full Verification

**Files:**
- Modify: `C:\Users\wang\learn\app.py`
- Modify: `C:\Users\wang\learn\floatvocab\__init__.py`
- Modify: `C:\Users\wang\learn\docs\superpowers\plans\2026-04-15-floatvocab-backend-refactor.md`

- [ ] **Step 1: Keep compatibility exports in `app.py` while removing duplicated backend implementations**

```python
from floatvocab.models import WordCard
from floatvocab.services import SettingsService, StudyService, NewsService, EnrichmentService
from floatvocab.db import FloatVocabDB
```

- [ ] **Step 2: Ensure top-level helper names used by tests still exist or are intentionally re-exported**

```python
__all__ = [
    "FloatVocabDB",
    "FloatVocabApp",
    "StudyService",
    "SettingsService",
    "NewsService",
    "EnrichmentService",
    "WordCard",
]
```

- [ ] **Step 3: Run the full regression suite**

Run: `python -m unittest discover -s tests -v`
Expected: PASS with 0 failures and 0 errors

- [ ] **Step 4: Launch the app for a final manual smoke check**

Run: `python app.py`
Expected: main window opens, floating review still works, news actions still respond, no import-time errors after the refactor

- [ ] **Step 5: Commit**

```bash
git add app.py floatvocab docs/superpowers/plans/2026-04-15-floatvocab-backend-refactor.md tests
git commit -m "refactor: separate FloatVocab backend layers"
```
