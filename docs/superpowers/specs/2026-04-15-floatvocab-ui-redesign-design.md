# FloatVocab UI Redesign Design

**Date:** 2026-04-15
**Project:** FloatVocab desktop app
**Scope:** Visual and layout redesign of the existing `tkinter` application without changing product behavior, data model, or learning workflow

## Goal

Refresh the current desktop UI so it feels like a modern study product instead of a default desktop form. The redesign should improve hierarchy, spacing, readability, and perceived quality while preserving the existing features, shortcuts, database behavior, and review actions.

## Product Constraints

- Keep the application as a pure Python `tkinter` / `ttk` desktop app.
- Do not change database schema or review logic for the UI redesign.
- Do not remove existing core functions:
  - lexicon selection and plan saving
  - floating review window
  - import TXT / CSV
  - example enrichment
  - progress and heatmap visibility
  - current lexicon overview table
  - daily news list, favorites, and article reading
- Prefer re-layout and restyling over introducing new behavior.

## Chosen Visual Direction

The interface will follow a study-product aesthetic with a bright, modern palette. The surface stays light and calm, while blue-cyan accents provide energy and clearer action emphasis. The app should feel clean and capable, not ornamental.

### Visual Thesis

Bright learning workspace: white and mist-blue surfaces, soft contrast, clear section boundaries, and restrained accent color for action and progress.

### Content Plan

- Hero/workbench header: app identity, concise orientation, primary actions
- Study controls: lexicon, daily target, target date, save/show/import actions
- Performance strip: progress, review summary, heatmap
- Knowledge workspace: lexicon table plus daily news/favorites
- Auxiliary windows: floating flashcard and article reader aligned with the same visual system

### Interaction Thesis

- Stronger action hierarchy through primary vs secondary button styling
- Clearer scanning with grouped sections and lighter table framing
- Floating review card uses more deliberate typography and spacing to feel like a study card, not a utility popup

## Information Architecture

The main window will be reorganized into a balanced dashboard instead of a vertical stack of label frames.

### Main Window

1. Top header band
   - Product title
   - One-sentence orientation copy
   - Quick actions for opening the floating review card and refreshing content

2. Upper content row
   - Left: study plan panel with lexicon picker and plan controls
   - Right: floating window appearance panel with sliders, font size, background color, and widget size

3. Middle strip
   - Progress summary
   - Completion meter
   - Heatmap embedded inside a cleaner summary block

4. Lower workspace
   - Lexicon overview table
   - Daily news split view: latest items on the left, favorites on the right, summaries below each area or in an integrated detail panel

This preserves all current content while improving eye flow: act first, monitor second, browse content third.

## Component Design

### Styling System

Create a consistent theme layer for:

- page background
- panel surface background
- subtle border colors
- primary accent
- success / warning / neutral state text
- heading, label, helper, and table typography
- button variants

The goal is to avoid ad hoc widget styling and instead make the app feel intentionally designed.

### Panels

Replace the current heavy `LabelFrame` look with flatter grouped panels:

- softer surface blocks
- more whitespace between controls
- stronger section titles
- less visible boxing around everything

The layout should still read as a desktop productivity tool, but with lighter chrome.

### Tables

Treeviews should feel cleaner and easier to scan:

- clearer headings
- alternating row background or subtle selected-state polish if feasible within ttk styling
- narrower visual noise around frames and padding
- more balanced widths for the word list and news list

### Floating Review Window

The floating card should keep its workflow intact but present content more clearly:

- bigger word area with better vertical rhythm
- supporting detail area separated visually
- cleaner action buttons for known / flip / unknown
- calmer hint row
- improved background and contrast defaults

The card should feel like a focused study surface rather than a generic popup.

### Daily Article Window

The article reader should look closer to a lightweight reading pane:

- clearer title bar
- quieter metadata treatment
- better body text spacing
- panel padding that supports long-form reading

## Layout and Responsiveness

The app only needs desktop responsiveness, but it should resize gracefully.

- Main window minimum width should still support side-by-side plan/style panels.
- Lower workspace should expand with the window and give tables more room.
- Text areas and tables should grow when the user enlarges the window.
- The floating card should retain minimum usable dimensions and preserve current drag / resize behavior.

## Copy Adjustments

Copy can be cleaned up for readability where necessary, but no feature semantics should change. Labels should be shorter, clearer, and grouped with helper text where useful.

## Implementation Boundaries

Allowed:

- UI layout reorganization inside `build_ui`
- new helper methods for theme and panel construction
- ttk style configuration
- restyling `tk` widgets used in floating and article windows
- small text changes to improve clarity

Not in scope:

- new learning features
- changed review scheduling logic
- changed database behavior
- new dependencies
- migration away from `tkinter`

## Verification Expectations

The redesign is complete when:

- all existing user flows still work
- the app launches without errors
- the main window layout is visually cleaner and more structured
- the floating review card looks polished and remains draggable/resizable
- the article reader matches the new visual system
- no feature behavior regresses during manual smoke testing
