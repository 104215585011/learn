# FloatVocab Backend Refactor Design

**Date:** 2026-04-15
**Project:** FloatVocab desktop app
**Scope:** Deep internal backend refactor for the existing desktop application while preserving current features, data compatibility, and user-visible behavior

## Goal

Reorganize the current backend logic so the desktop UI no longer talks directly to raw SQLite queries, background task wiring, or news-fetching functions. The result should be a clearer internal architecture with stable service interfaces, lower coupling, and better testability, without changing the product's current behavior.

## Current State

The project is functionally a desktop app with an embedded local backend:

- `app.py` contains UI construction, state management, database schema, persistence logic, review scheduling, and thread orchestration
- `news_digest.py` contains news schema setup, fetching, saving, translation, and article extraction
- `example_pipeline.py` is triggered directly from the UI for example enrichment
- parts of the UI still call `self.db.conn.execute(...)` or open standalone SQLite connections directly

This creates several problems:

- business rules and persistence are mixed together
- UI code knows table structure and SQL details
- background tasks are triggered in UI methods instead of service boundaries
- tests can only target the current structure indirectly
- `app.py` has become the composition root, business layer, repository, and UI at the same time

## Refactor Objectives

- Preserve existing SQLite schema and existing data
- Preserve current learning workflow, news workflow, example enrichment flow, and UI behavior
- Remove direct SQL access from the UI layer
- Introduce clear service interfaces for study, settings, news, and enrichment operations
- Separate repositories from business rules
- Make async task entry points easier to test by isolating work units from Tk callbacks
- Keep startup and packaging simple for the current desktop app

## Non-Goals

- No HTTP API
- No migration away from `tkinter`
- No product redesign or workflow redesign
- No semantic change to spaced repetition behavior
- No schema rewrite unless a tiny compatibility migration is required
- No new third-party runtime dependencies

## Recommended Approach

Use a layered in-process architecture:

- UI layer: Tk widgets, layout, event bindings, display formatting
- service layer: business use cases and operation boundaries
- repository layer: SQLite reads and writes
- integration layer: external or slow operations such as news fetch and example enrichment
- model layer: small data objects and typed result shapes used across layers

This is a deep internal refactor, but still optimized for compatibility. The application remains a desktop app with one local database file. We are only changing the internal calling structure.

## Target Module Structure

Suggested file layout:

```text
app.py
floatvocab/
  __init__.py
  models.py
  db.py
  repositories/
    __init__.py
    lexicon_repository.py
    study_repository.py
    plan_repository.py
    news_repository.py
  services/
    __init__.py
    study_service.py
    settings_service.py
    news_service.py
    enrichment_service.py
  ui/
    __init__.py
    main_window.py
    floating_window.py
    article_window.py
    hotkeys.py
```

The exact filenames can be adjusted during implementation, but the boundaries should remain the same.

## Layer Responsibilities

### Models

Purpose:

- define stable value objects passed between layers
- keep UI and repositories from sharing raw SQLite rows as their main contract

Expected contents:

- `WordCard`
- lightweight study summary/result objects
- lightweight news/favorite article objects
- operation result objects such as import counts or enrichment summaries

### Database Bootstrap

Purpose:

- centralize connection creation and schema initialization
- keep migration and compatibility logic out of UI classes

Expected responsibilities:

- open SQLite connection with `row_factory`
- run schema initialization for learning tables
- delegate news-related schema initialization
- run compatibility checks for optional columns like `current_word_id`

This replaces the current habit of creating ad hoc connections in multiple places.

### Repository Layer

Purpose:

- own all SQL
- present persistence operations in domain language

Expected repository split:

- `LexiconRepository`
  - list lexicons
  - create lexicon
  - import words
  - list recent words for a lexicon
- `PlanRepository`
  - read plan
  - save plan
  - save float style
  - manage `current_word_id`
- `StudyRepository`
  - fetch next review candidate
  - load word state for review
  - persist review result
  - load stats and streak/heatmap data
  - count missing examples
- `NewsRepository`
  - list latest briefs
  - get brief by id
  - mark brief saved
  - list favorites
  - get favorite article by id
  - save favorite article

Repository rules:

- repositories may share a connection provider
- repositories do not contain Tk logic
- repositories do not open threads
- repositories do not perform network operations

### Service Layer

Purpose:

- enforce business rules and expose clean use-case interfaces to the UI

#### Study Service

Owns:

- next card selection flow
- review submission flow
- study stats aggregation
- word list view data
- status text mapping if that remains domain-related

Representative interface:

- `get_dashboard_state()`
- `get_next_card()`
- `submit_review(word_id, rating)`
- `get_recent_words(lexicon_id, limit=80)`
- `get_study_stats()`

#### Settings Service

Owns:

- reading the active plan
- saving selected lexicon, daily target, target date
- saving floating-window appearance settings
- validating plan inputs before persistence

Representative interface:

- `get_plan_settings()`
- `save_plan(...)`
- `save_float_style(...)`

#### News Service

Owns:

- refresh latest briefs
- read latest briefs and favorites
- load detail text for selected brief/favorite
- save a brief to favorites
- hide `news_digest` implementation details from the UI

Representative interface:

- `refresh_latest_briefs(limit=10)`
- `list_latest_briefs(limit=10)`
- `get_brief_preview(brief_id)`
- `save_brief_to_favorites(brief_id)`
- `list_favorite_articles()`
- `get_favorite_article(article_id)`

This service will wrap both repository work and the integration work in `news_digest.py`.

#### Enrichment Service

Owns:

- example enrichment entry point
- reporting processed/updated/skipped/failures in a stable shape
- keeping the UI unaware of the implementation details in `example_pipeline.py`

Representative interface:

- `get_missing_examples_count(lexicon_id=None)`
- `enrich_examples(lexicon_id=None, limit=200, refresh=False)`

## Integration Boundaries

### `news_digest.py`

Keep it as an integration/helper module for now, but stop treating it as something the UI calls directly.

After refactor:

- `news_digest.py` remains responsible for feed fetch, article extraction, translation, and fallback generation
- `NewsService` becomes the only caller from the application layer
- SQLite persistence for news data should be mediated through `NewsRepository` where reasonable

This allows us to preserve the working logic while improving boundaries.

### `example_pipeline.py`

Treat this as an external enrichment engine.

After refactor:

- the UI calls `EnrichmentService`
- `EnrichmentService` calls `enrich_database(...)`
- callback-friendly result handling stays outside the core enrichment logic

## UI Changes Required

The UI should remain visually and behaviorally the same, but its responsibilities must shrink.

The UI should:

- read formatted state from services
- invoke service methods on button clicks
- keep Tk-specific input validation and display concerns only where presentation-specific
- keep background threading only as orchestration around service calls

The UI should stop doing:

- `self.db.conn.execute(...)`
- direct calls into `news_digest.*`
- direct use of raw SQLite rows for display decisions
- direct construction of standalone SQLite connections for business operations

## Threading Strategy

Current async actions include:

- refresh daily briefs
- save selected brief
- enrich examples

Target rule:

- UI owns Tk thread scheduling and callback dispatch
- services expose synchronous work methods
- worker threads call service methods
- completion/error callbacks in UI translate results into message boxes or view refreshes

This keeps thread ownership predictable while making the actual work testable outside Tk.

## Compatibility Strategy

Compatibility is the priority. The refactor should preserve:

- database file location
- existing table names and columns
- existing current-word resume behavior
- existing review scheduling results
- existing news favorite persistence behavior
- existing example enrichment entry point behavior
- existing global shortcut behavior

Where current behavior is awkward but user-visible, keep it unless it is clearly a bug that blocks the refactor.

## Testing Strategy

Existing tests already cover useful compatibility points:

- current word persistence across app restart
- async error callback behavior for brief saving
- resilience when translation or content fetching fails
- top-level UI tab structure

During refactor we should preserve or add tests around:

- repository schema bootstrap and compatibility columns
- service-level next card and review behavior
- service-level news save fallback behavior
- service-level example enrichment result forwarding
- UI methods calling service interfaces instead of raw SQL

Recommended test split:

- repository tests with in-memory SQLite
- service tests with real repositories or narrow mocks depending on the scenario
- minimal UI smoke tests to ensure window construction still works

## Incremental Delivery Plan

To reduce regression risk, implementation should be phased:

1. Extract models and database bootstrap
2. Extract repositories without changing behavior
3. Extract services and route existing app methods through them
4. Move Tk window classes into UI modules
5. Reduce `app.py` to composition and startup
6. Run tests and fix compatibility regressions

This sequencing allows behavior-preserving moves before more structural edits.

## Risks

### Risk 1: Hidden behavior changes from switching row types to models

Mitigation:

- keep model fields close to the current row shape
- only convert where boundaries matter
- verify current tests still pass

### Risk 2: SQLite connection behavior changes when centralizing connection creation

Mitigation:

- preserve `row_factory = sqlite3.Row`
- preserve WAL initialization
- keep worker-thread connections explicit where needed

### Risk 3: UI regressions from moving methods out of `FloatVocabApp`

Mitigation:

- keep method names or adapter methods stable during the transition
- refactor in phases rather than rewriting the whole UI shell at once

### Risk 4: News workflow regressions because persistence and fetch logic are currently intertwined

Mitigation:

- preserve fallback semantics exactly
- keep `news_digest.py` logic intact at first
- move boundaries before changing implementation details

## Success Criteria

The refactor is successful when:

- `app.py` is no longer the main home of SQL and business logic
- the UI no longer executes raw SQL directly
- news and enrichment operations are invoked through services
- existing user-visible behavior remains compatible
- the current tests still pass after updating imports and call sites
- the codebase has clear backend interfaces that make later changes safer

## Open Decisions Already Resolved

- We are not introducing HTTP APIs in this refactor
- We are aiming for deep internal cleanup, not a cosmetic shuffle
- We are optimizing for compatibility over behavior changes

## Implementation Recommendation

Proceed with the layered refactor using repositories and services as the main boundary. This gives the project a real backend architecture inside the desktop app while keeping risk under control and preserving the current product surface.
