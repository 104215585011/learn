# FloatVocab Dynamic Review Design

**Date:** 2026-04-17
**Project:** FloatVocab desktop app
**Scope:** Replace the current simplified review loop with a dynamic memory-strength-driven review flow and a clearer today-task experience

## Goal

Make the floating vocabulary workflow feel more natural and more aligned with forgetting-curve-style review. The system should stop behaving like an endless generic card queue and instead act like a daily study engine that:

- automatically prioritizes the most urgent review items
- supports three memory-strength feedback levels
- retries forgotten words again the same day
- naturally introduces new words when review pressure is low
- clearly shows what remains in today’s workload

## User Intent Confirmed

The user wants:

- no explicit “resume from where you left off” concept in the UI
- dynamic next-review scheduling based on memory strength rather than a fixed daily new-word quota
- new words to be introduced automatically after urgent review work is handled
- three feedback levels on each word:
  - `忘了`
  - `模糊记得`
  - `很熟`
- `忘了` words to reappear later the same day and also be prioritized the next day
- a relatively aggressive spacing strategy when the user marks a word as `很熟`

## Current Problems

The current local implementation has three main mismatches with that intent:

1. `daily_new` is saved but not used to actually govern the card queue
2. `next_card()` chooses from all non-mastered words by a simple due-date-oriented ordering, not a proper today-task workflow
3. the dashboard shows overall progress, not meaningful daily workload metrics

The result is that the app does not answer the questions a learner naturally has:

- what should I review today?
- how many items are left?
- how many have I completed today?
- why did this word show up again?

## Design Direction

Use a dynamic review engine with a today-task view.

This does **not** mean implementing a full Anki clone or a complex research-grade memory model. The target is a pragmatic middle path:

- more dynamic than fixed intervals
- simpler than full SM-2 or FSRS
- easy to understand and tune in this desktop app

## Core Experience

### Learning Flow

At any moment, the next word should come from one of four queues, in priority order:

1. same-day retry words
2. due review words
3. near-due review words
4. unseen new words

The user should not need to manually choose between “review mode” and “new word mode.” The system should flow naturally through the highest-priority work first.

### Feedback Model

Replace the current effective two-level review behavior with three explicit review outcomes:

- `忘了`
- `模糊记得`
- `很熟`

These should map to different updates in memory strength and scheduling urgency.

## Data Model Changes

The current word table already stores review-related fields such as repetitions, interval, ease, and next review date. For the new model, add focused fields that better match the desired workflow.

### New Word-Level Fields

Add to `words`:

- `memory_strength REAL NOT NULL DEFAULT 0`
  - a lightweight representation of how stable this memory currently is
- `lapse_count INTEGER NOT NULL DEFAULT 0`
  - total times the word was forgotten
- `last_reviewed_at TEXT`
  - precise timestamp of the latest review action
- `next_review_at TEXT`
  - precise next review timestamp, replacing date-only logic for queueing
- `same_day_retry_at TEXT`
  - when a forgotten word should reappear later the same day
- `last_rating TEXT`
  - one of `forgot`, `fuzzy`, `solid`

### Existing Fields To Keep

Keep for compatibility and transition:

- `status`
- `seen_count`
- `correct_count`
- `updated_at`

The old interval/ease/repetition fields can remain during transition, but the new queueing logic should no longer depend on them as the source of truth.

## Task Queues

### 1. Same-Day Retry Queue

Words marked `忘了` should not disappear until tomorrow. They should come back again later the same day.

Rules:

- on `忘了`, set `same_day_retry_at` to a short future time
- same-day retry items always outrank ordinary due items
- once the same-day retry is served, clear or move that field as appropriate

This provides immediate reinforcement without forcing the word to repeat instantly in a frustrating loop.

### 2. Due Review Queue

Words whose `next_review_at <= now` are due.

Sorting within this queue should prioritize the most urgent items first. A reasonable ordering is:

- same-day retries excluded because they are handled earlier
- oldest overdue first
- lower memory strength first
- higher lapse count first
- oldest review timestamp first

This keeps fragile memories from being buried behind easier material.

### 3. Near-Due Queue

When there are few or no due items, the system may pull in words that are about to become due soon.

This queue should be conservative. It exists to keep the flow smooth, not to overwhelm the learner.

### 4. New Word Queue

Unseen words should appear automatically only when the more urgent queues are light enough.

This means the system is no longer driven by a hard daily new-word quota. Instead, new words are introduced opportunistically based on workload.

## Scheduling Rules

### `忘了`

Effects:

- strong drop in `memory_strength`
- increment `lapse_count`
- set `same_day_retry_at` for a later retry today
- set `next_review_at` to tomorrow or an early next-day review window
- mark `last_rating = 'forgot'`

Intent:

- the learner gets another chance the same day
- the word also returns early the next day

### `模糊记得`

Effects:

- small increase in `memory_strength`
- set `next_review_at` to a near future interval
- clear any same-day retry marker
- mark `last_rating = 'fuzzy'`

Intent:

- the system recognizes partial recall
- the interval grows, but cautiously

### `很熟`

Effects:

- strong increase in `memory_strength`
- set `next_review_at` to a significantly longer interval
- clear any same-day retry marker
- mark `last_rating = 'solid'`

Intent:

- the system rewards strong recall by spacing more aggressively
- but words with repeated lapses should still be moderated by their weaker history

## Dynamic Interval Strategy

Instead of a fixed table like `1/3/7/14/30`, use memory-strength-driven intervals.

### Inputs

Next review timing should be influenced by:

- current `memory_strength`
- latest rating (`forgot`, `fuzzy`, `solid`)
- `lapse_count`
- whether the word is still relatively new or already stable

### Behavioral Shape

- `forgot` sharply contracts the schedule
- `fuzzy` grows the schedule gently
- `solid` grows the schedule aggressively
- repeated forgetting caps how optimistic the algorithm can be

This gives the “forgetting curve feel” the user wants without introducing an opaque or over-engineered system.

## Status Model

Keep user-facing status lightweight.

Internally, the queueing logic should use the new scheduling fields. Externally, the UI can still show understandable states such as:

- `新词`
- `待复习`
- `当天回炉`
- `已掌握`

“已掌握” should be treated carefully. It should not mean the word permanently leaves the system unless the product explicitly wants retirement behavior. For now, a word can be considered effectively mastered when its memory strength is high and its interval is long, but it may still return if the algorithm calls for it.

## Dashboard Changes

Replace the current plan-centric progress emphasis with a today-task view.

### Show Prominently

- `今日待复习`
- `今日回炉`
- `今日已完成`
- `当前学习池`

### Secondary Metrics

- total words
- long-term mastered count or strong-memory count
- 30-day heatmap

### Remove As Primary Focus

- `每日新词` as the central planning concept
- overall mastery percentage as the main progress indicator

The current overall mastery view may remain, but it should not dominate the dashboard.

## Floating Window Changes

The floating review card should explain the current word’s role in today’s workflow.

### Show

- current card type:
  - `新词`
  - `到期复习`
  - `当天回炉`
- today progress summary:
  - completed
  - due remaining
  - retry remaining

### Actions

Replace the current review actions with:

- `忘了`
- `模糊记得`
- `很熟`

These labels should map directly to the new scheduling logic.

## Plan Settings Changes

The old `daily_new` field should no longer be treated as the main engine of progress.

Options:

- preserve it in storage for backward compatibility, but reduce its role in the UI
- later repurpose or remove it after migration is stable

`target_date` may also become secondary unless it is used to shape automatic pacing in a future iteration.

For this phase, the main product behavior should no longer depend on `daily_new`.

## Migration Strategy

This feature should be introduced without breaking existing local data.

### Schema Migration

Add the new columns through compatibility-safe migration code.

### Backfill

For existing words:

- initialize `memory_strength` from current review history heuristically
- set `next_review_at` from `next_review_date` when available
- initialize `lapse_count` conservatively

This does not need to be perfect. It only needs to provide a stable starting point.

## Testing Strategy

Add tests for:

- same-day retry behavior after `忘了`
- next-day priority after a lapse
- `模糊记得` producing shorter intervals than `很熟`
- due queue outranking new words
- new words appearing only when urgent queues are light
- dashboard stats exposing today-task counts correctly

The most important regression protection is around queue selection and scheduling transitions.

## Risks

### Risk 1: Overly aggressive spacing hides weak words too long

Mitigation:

- let `lapse_count` pull intervals back down
- tune `solid` growth conservatively at first, even if it feels aggressive

### Risk 2: Same-day retry feels repetitive

Mitigation:

- retry after a short delay rather than immediately
- ensure a forgotten word does not monopolize the queue

### Risk 3: UI becomes harder to understand

Mitigation:

- use plain labels like `今日待复习` and `当天回炉`
- avoid showing raw algorithm numbers

### Risk 4: Existing data migrates awkwardly

Mitigation:

- keep old review fields during transition
- backfill only what is needed for a smooth start

## Success Criteria

This redesign is successful when:

- the app no longer feels driven by a hidden daily-new-word setting
- the next card flow clearly prioritizes urgent review
- forgotten words come back the same day and again early the next day
- strong recall noticeably extends spacing
- the dashboard clearly shows today’s study workload
- the floating card labels and actions match the learner’s mental model

## Recommendation

Implement the dynamic review engine with a today-task UI, using memory strength and lapse history as the scheduling core. This delivers a more natural forgetting-curve experience without overcomplicating the current desktop app.
