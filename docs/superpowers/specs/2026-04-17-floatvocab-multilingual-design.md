# FloatVocab Multilingual Learning Design

**Date:** 2026-04-17
**Project:** FloatVocab desktop app
**Scope:** Add first-class support for multiple target learning languages across lexicons, study selection, imports, and daily briefs

## Goal

Extend the current English-only learning experience into a multilingual structure that supports the project's initial market languages: English, Spanish, French, Korean, Japanese, Italian, Indonesian, Russian, Arabic, and Portuguese.

The product should keep a simple daily flow:

1. Choose the current learning language.
2. Choose a lexicon within that language.
3. Study words and browse daily briefs for that language.

The design must avoid overwhelming the user when many lexicons exist and must prevent naming collisions across languages.

## Product Decisions

### Primary User Entry

The homepage primary selector is **current learning language**, not current lexicon.

After the user changes language:

- the lexicon selector only shows lexicons for that language
- the study plan remains tied to the chosen lexicon within that language
- the daily briefs area changes to the active language context
- imports default to the active language

This keeps the user focused on one language at a time and prevents mixed-language clutter in the main learning flow.

### Lexicon Model

Lexicons are still first-class entities, but each lexicon belongs to exactly one language.

- A user may keep multiple lexicons for the same language.
- Different languages may reuse the same lexicon name.
- Duplicate lexicon names are only forbidden within the same language.

Examples:

- `English / Core 3000` and `Japanese / Core 3000` are valid together.
- Two separate `English / Core 3000` lexicons are not allowed.

### Language Scope

The first supported languages are:

- `en` English
- `es` Spanish
- `fr` French
- `ko` Korean
- `ja` Japanese
- `it` Italian
- `id` Indonesian
- `ru` Russian
- `ar` Arabic
- `pt` Portuguese

These language codes act as stable internal identifiers across database rows, source folders, settings, and future integrations.

## Architecture

The multilingual feature is implemented as a new language context that flows through four layers:

1. **Persistence layer** stores the active language and each lexicon's language.
2. **Repository/service layer** filters lexicons and briefs by language.
3. **UI layer** makes language selection the top-level interaction.
4. **Content ingestion layer** imports lexicons and briefs into the correct language bucket.

This is an additive change. Existing study scheduling and word review behavior should remain unchanged.

## Data Model Changes

### `lexicons`

Add a required `language_code TEXT NOT NULL DEFAULT 'en'`.

Change uniqueness from:

- `name` unique globally

to:

- `(language_code, name)` unique together

This enables the same display name to exist across different languages without ambiguity.

### `plans`

Add a required `current_language_code TEXT NOT NULL DEFAULT 'en'`.

The `plans` table remains the single place for app-level study context. The stored plan now represents:

- current language
- current lexicon
- current daily target
- current visual settings

When the user switches language, the app updates `current_language_code` and then selects an appropriate lexicon for that language.

### `daily_briefs`

Add a required `language_code TEXT NOT NULL DEFAULT 'en'`.

The same article URL may legitimately appear in separate language feeds over time, so the uniqueness rule should become language-aware if necessary. The preferred uniqueness is:

- `(language_code, url)` unique together

This keeps briefs partitioned by language without cross-language collisions.

### `favorite_articles`

Add `language_code TEXT NOT NULL DEFAULT 'en'`.

Saved articles must remain attributable to their source language so the favorites pane stays aligned with the active language.

### Migration Strategy

Existing data should migrate as follows:

- all existing lexicons become `language_code = 'en'`
- the existing plan becomes `current_language_code = 'en'`
- all existing briefs and favorite articles become `language_code = 'en'`

This preserves current users without requiring manual cleanup.

## Repository and Service Design

### Lexicon Repository

The lexicon repository should gain language-aware operations:

- list all supported languages for UI display
- list lexicons by language
- create lexicon with `name + language_code + source`
- import words into a lexicon already scoped to a language

The main lexicon query used by the homepage should default to:

- list lexicons for the current language only

An optional management view may later list all lexicons across languages, but it should not drive the default study workflow.

### Settings Service

The settings service should manage:

- reading the current language from the plan
- updating the current language
- updating the selected lexicon inside the current language

Language switching behavior:

1. Save the chosen `current_language_code`.
2. Load lexicons for that language.
3. If the current `lexicon_id` belongs to that language, keep it.
4. Otherwise choose the first available lexicon for that language.
5. If none exist, clear `lexicon_id` and show an empty-state prompt to import a lexicon.

### News Service

The news service should become language-aware:

- refresh latest briefs for one language
- list latest briefs for one language
- list favorite articles for one language
- save article favorites while preserving `language_code`

The active language must be passed explicitly through service boundaries rather than inferred from hard-coded English assumptions.

## UI Design

### Homepage Control Flow

The homepage study area should adopt this order:

1. **Current learning language**
2. **Current lexicon**
3. **Daily plan settings**
4. **Import and enrichment actions**

The current language control is visually above the lexicon selector to reinforce the mental model:

- choose the language first
- then choose the lexicon inside it

### Lexicon Selector

The lexicon selector only shows lexicons for the current learning language.

If no lexicons exist for the active language:

- disable the lexicon selector
- show helper text such as "No lexicon exists for this language yet. Import a word pack first."
- keep the import action visible and obvious

### Lexicon Naming in UI

Default daily screens should avoid showing cross-language clutter.

In the main study area:

- show only the lexicon names for the active language

In any future all-lexicon management view:

- show `Language name · Lexicon name`
- optionally add a source tag such as `built-in` or `imported`

Examples:

- `English · CET4`
- `Japanese · N5`
- `Spanish · DELE A1`

### Daily Briefs Area

The current hard-coded English presentation should become language-aware.

Examples:

- `English Daily Briefs`
- `Spanish Daily Briefs`
- `French Daily Briefs`

The refresh action only fetches briefs for the active language. The favorites pane also only shows saved articles for the active language.

### Empty States

The app needs clear empty states for newly added languages.

If a language has:

- no lexicons: prompt for lexicon import
- no briefs configured: show "Daily briefs are not configured for this language yet." or equivalent fallback copy
- no saved favorites: keep the panel empty but not broken

This avoids requiring all 10 languages to be fully populated on day one.

## Import Design

### Import Rule

Every imported lexicon must belong to a language.

The import flow should support two sources of truth:

1. the currently selected language in the UI
2. an optional `language_code` embedded in the imported file metadata

The precedence rule should be:

- if the file explicitly declares `language_code`, use it
- otherwise use the current learning language

### Supported File Shape

Imported rows may continue to use the current fields:

- `word`
- `meaning`
- `phonetic`
- `example`

Optional future metadata may include:

- `language_code`
- `source`
- `level`

The importer should ignore unsupported fields rather than fail.

### Built-In Source Layout

Built-in lexicon sources should move toward a language-partitioned directory structure:

- `data/vocab_sources/en/...`
- `data/vocab_sources/es/...`
- `data/vocab_sources/fr/...`
- `data/vocab_sources/ko/...`
- `data/vocab_sources/ja/...`
- `data/vocab_sources/it/...`
- `data/vocab_sources/id/...`
- `data/vocab_sources/ru/...`
- `data/vocab_sources/ar/...`
- `data/vocab_sources/pt/...`

This keeps seed data organized and makes future expansion predictable.

### Duplicate Handling

Duplicate protection should remain at the word level within a lexicon:

- words stay unique by `(lexicon_id, word)`

Importing into different lexicons remains allowed, even within the same language.

## Daily Brief Design

### Language-Specific Feeds

Daily brief sources should be configured per language instead of globally.

The system should treat feeds as a language map, for example:

- `en`: BBC World, Reuters World
- `es`: BBC Mundo, El Pais
- `fr`: France 24, Le Monde
- `ja`: NHK News Web

The exact source list can be expanded gradually. The important design rule is that feed configuration belongs to a language code, not to the app globally.

### Translation Behavior

The current article pipeline assumes English source content and Chinese translation output. That behavior can remain the first shipped default.

Initial multilingual brief behavior should therefore be:

- fetch content in the selected learning language
- store the original article text
- continue translating article text into Simplified Chinese for reading support

This means the product supports multilingual learning languages without immediately needing multilingual UI localization or many translation targets.

### Rollout Boundary

For the first implementation, it is acceptable if:

- English has full briefs support
- a subset of the new languages has configured feeds
- unsupported languages show an explicit empty state

This allows the data model and UI to be correct from day one while the content network grows progressively.

## Initialization and Seeding

Database initialization should seed built-in lexicons with explicit `language_code`.

The existing built-in English datasets should be seeded as English.

Future built-in datasets for other languages can be added incrementally without altering the database design.

When the app starts:

1. Load `current_language_code`.
2. Load lexicons for that language.
3. Resolve the active lexicon.
4. Render study widgets and briefs in that language context.

## Error Handling

### Language With No Lexicons

The app should not error when the current language has no lexicons. It should:

- clear the active lexicon
- keep the page usable
- prompt the user to import a lexicon

### Language With No Brief Sources

Refreshing briefs for a language without configured sources should not raise a fatal error. It should:

- return an empty result
- display a clear status message in the UI

### Invalid Import Metadata

If a file declares an unknown `language_code`, the app should reject it with a user-facing validation message instead of importing into an undefined bucket.

## Testing Strategy

### Migration Tests

Add coverage for:

- adding `language_code` to existing lexicons and news rows
- adding `current_language_code` to plans
- preserving existing English data after migration

### Repository and Service Tests

Add coverage for:

- creating lexicons with language codes
- allowing same lexicon name across different languages
- rejecting duplicate lexicon names within the same language
- filtering lexicons by active language
- switching current language and selecting a matching lexicon
- listing briefs and favorites by language

### UI Tests

Add coverage for:

- rendering the language selector
- updating the lexicon selector when language changes
- showing empty state when no lexicon exists for a language
- using language-aware daily brief labels

### Manual Verification

Smoke test the following flows:

1. Start with migrated English-only data and confirm it still works.
2. Switch to a language with no lexicons and confirm the empty state is clear.
3. Import a lexicon into Spanish and confirm it only appears under Spanish.
4. Create another lexicon named the same under Japanese and confirm it is allowed.
5. Refresh briefs for English and confirm no regression.
6. Refresh briefs for an unsupported language and confirm graceful empty behavior.

## Non-Goals

This design does not include:

- full UI translation/localization into each target language
- simultaneous multi-language study on the same main screen
- automatic acquisition of all 10 languages' lexicon datasets
- guaranteed day-one news feeds for every language
- changes to spaced repetition scheduling logic

## Recommendation

Ship the multilingual feature in two phases.

### Phase 1

- add language-aware schema and migrations
- add current language selector to the homepage
- filter lexicons by language
- make imports language-aware
- make daily brief storage and UI language-aware
- keep English as the only fully configured brief source if needed

### Phase 2

- add more built-in lexicons by language
- configure additional news feeds
- add an all-lexicon management view if user demand emerges

This phased rollout gives the product the correct foundation without forcing all content operations to be solved at once.
