# FloatVocab UI Iteration Design

**Date:** 2026-04-19
**Project:** FloatVocab desktop app
**Scope:** Iterative UI upgrade of the existing `tkinter` desktop application, focusing on the main dashboard, daily news workspace, floating review card, and visual consistency.

## Goal

Improve the current desktop UI so the product feels more intentional, easier to scan, and more task-focused in daily use. The redesign should preserve the current data model, review behavior, and feature set while making the app better at guiding the user toward the next useful action.

This iteration builds on the existing redesign foundation and refines the product around three confirmed priorities:

1. A mixed-mode dashboard that balances action-first study flow with access to configuration.
2. A daily news workspace that reads like a study reading area rather than a management table.
3. A floating review card that feels like a dedicated learning surface instead of a utility popup.

## Product Constraints

- Keep the app as a pure Python `tkinter` / `ttk` desktop application.
- Do not change the database schema, spaced repetition behavior, or news persistence behavior as part of this UI work.
- Preserve all current major actions and bindings:
  - select language and lexicon
  - save study plan
  - import TXT / CSV lexicons
  - rename and delete lexicons
  - enrich missing examples
  - open and use the floating review card
  - refresh, preview, favorite, open, and delete daily news entries
- Avoid new dependencies unless absolutely necessary. Prefer restructuring, styling, and copy improvements within the existing stack.

## Confirmed Direction

The design direction is a **mixed-mode study workspace**.

That means the app should:

- foreground the user's immediate learning task
- keep configuration nearby, but visually secondary
- preserve the feeling of a capable workbench
- reduce equal-weight controls that currently compete for attention

The app should not become either:

- a pure landing page that hides management features, or
- a flat control dashboard where every section feels equally important

## Design Principles

### 1. Action Before Administration

The UI should make it obvious what the user can do next, especially when opening the app for a normal study session. Primary actions should appear before setup or maintenance actions.

### 2. Clear Visual Hierarchy

Important information should be scannable without reading long helper text. Titles, summaries, status, and actions should each have distinct visual weight.

### 3. Focused Reading Surfaces

The floating card and article reader should feel calm and content-led. They should minimize chrome and emphasize the main learning material.

### 4. Preserve Familiarity

Existing flows should still feel recognizable. This is a refinement, not a product rewrite.

## Information Architecture

## Main Dashboard

The main dashboard keeps the current tab structure, but the first tab becomes more task-oriented.

### Hero / Task Entry

The top hero section becomes a task entry point rather than a product introduction banner.

It should contain:

- the product title
- a short one-line status summary, such as today's due count and current mastery level
- one primary action: continue review
- one secondary action: refresh daily news

The hero should answer: "What should I do now?" within the first glance.

### Primary Control Row

The next row remains two columns:

- left: study plan
- right: floating window style

However, the study plan column should carry more visual weight than the style panel.

#### Study Plan Panel

The study plan panel should prioritize:

- language
- current lexicon
- target date
- daily new-word goal
- key status summaries

The primary action in this panel is saving the plan.

Utility actions should be de-emphasized:

- import lexicon remains visible
- rename, delete, and enrich should become quieter actions, grouped more carefully so they do not compete with the main save path

#### Floating Style Panel

The style panel remains available, but visually secondary. It should feel like a tuning panel, not a co-equal task driver.

It should still expose:

- transparency
- font size
- background color
- widget size

The explanatory copy should be shorter and more supportive.

### Stats Strip

The current stats section should evolve from a single long summary sentence into a clearer progress area.

It should include:

- a concise overall progress summary
- small metric groupings for key signals such as due count, mastered count, or current completion
- the existing progress bar
- the existing 30-day heatmap with clearer spacing and optional legend treatment if feasible

The purpose of this strip is not only to show numbers, but to communicate momentum.

### Content Layer

Content-heavy areas should sit below the task and progress layers.

This layer includes:

- lexicon overview
- daily news workspace

These remain important, but should no longer visually compete with the top-level study task.

## Daily News Workspace

The daily news area should shift from a symmetric management layout to a reading-first split workspace.

### Layout

The workspace should become:

- a primary left column for latest news and preview
- a secondary right column for saved favorites

This keeps the latest content as the main exploration area and makes favorites feel like a personal archive.

### Latest News Column

The left column should contain:

- the latest items list
- a structured preview card below the list

The preview card should present:

- title
- source
- publication time
- save state
- summary text
- a lightweight prompt about opening or saving the full article

The preview should feel like a content card, not a raw text dump.

### Favorites Column

The right column should continue to show saved articles, but in a quieter role.

The header should communicate archive intent, such as "personal collection" or equivalent Chinese copy. The delete action remains accessible but visually subdued.

### Action Bar

The top action bar should better match user intent:

- refresh remains a list-level action
- favorite-and-translate remains a context action tied to the current selection

The layout should reinforce that users first select, then act.

### Reader Window Relationship

The main news tab is for scanning and previewing.
The detached article reader remains the full reading surface.

That means the main news tab does not need to behave like a full document reader. It only needs to make the handoff to the article window feel obvious and smooth.

## Floating Review Card

The floating review card should feel like a compact study product.

### Structure

The card keeps a three-part structure:

- header
- content
- action area

### Header

The header should no longer be a plain product label only.

It should include:

- product or mode identity
- lightweight session status, such as remaining cards, if the current services expose that cleanly

If remaining-card data is not easily available without behavioral changes, the header should still become a more deliberate drag surface with clearer visual affordance.

### Content Hierarchy

The main word should remain the strongest visual element on the front face.

Supporting information should be quieter:

- phonetic
- example sentence

On the flipped face, meaning becomes the main content, with supporting details still visible but clearly secondary.

The current compact flipped layout logic should be preserved if it already supports better readability. The goal is visual improvement, not workflow change.

### Action Row

The three actions remain:

- unknown
- flip
- known

But the hierarchy should be improved:

- flip reads as the stable neutral action
- known and unknown read as confident outcome actions
- spacing and alignment should make the row feel like a purpose-built control bar

### Helper Copy

Shortcut hints remain, but should be quieter so they do not compete with the card content.

### Drag / Resize

Current drag, resize, and keyboard behavior must remain intact.
If possible, the drag affordance should feel integrated into the card header rather than relying on a visually isolated thin bar.

## Daily Article Reader

The article reader should visually align with the updated floating card and dashboard.

It should remain:

- borderless
- lightweight
- focused on reading

Improvements should target:

- title hierarchy
- metadata calmness
- text spacing and long-form readability
- consistency with the product's updated surface colors and typography

The current focus-loss auto-hide behavior remains in scope unless it becomes clearly incompatible with the refined layout.

## Styling System

This iteration should consolidate styling rather than continue ad hoc updates.

### Theme Needs

The app should use a more explicit theme layer covering:

- app background
- panel surfaces
- alt surfaces
- borders
- text
- muted text
- accent
- success / warning / danger roles

### Typography Needs

Typography should establish a clearer hierarchy across:

- hero title
- panel titles
- section labels
- body copy
- helper copy
- table headings

The current visual gap between levels is too small, so text blocks often feel equally weighted.

### Reuse And Cleanup

The implementation should remove or consolidate duplicate style and helper definitions where possible so future UI changes remain predictable.

## Non-Goals

This iteration does not include:

- new learning features
- new data fields
- changes to review scoring or review scheduling
- changes to the article fetching pipeline
- migration away from `tkinter`
- a full responsive redesign for mobile or tablet

## Verification Expectations

The UI iteration is complete when:

- the dashboard clearly foregrounds the user's next study action
- the study plan and style sections are visually differentiated by priority
- the stats section is easier to scan than the current long summary sentence
- the daily news tab feels reading-first, with latest content clearly prioritized over favorites
- the floating card feels more polished and task-focused
- the article reader visually matches the rest of the app
- all existing callbacks and workflows continue working
- the app still launches cleanly and supports manual smoke testing of core flows
