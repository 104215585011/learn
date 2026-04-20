# FloatVocab Brand Workbench Refresh Design

**Date:** 2026-04-20
**Project:** FloatVocab desktop app
**Scope:** Mature-brand refresh of the existing `tkinter` desktop interface, focused on overall comfort, visual quality, and smoother study workspace flow without changing learning behavior or database logic

## Goal

Upgrade FloatVocab from a capable desktop utility into a calmer, more mature study product. The redesign should make the app feel more comfortable to use day to day, reduce visual noise, improve action hierarchy, and give the main window, floating card, and reader surfaces a shared premium identity.

## Product Intent

The target feel is not energetic or gamified. The product should feel like a high-quality reading and study workspace:

- restrained and premium rather than flashy
- spacious rather than dense
- calm and trustworthy rather than stimulating
- cold white / gray-blue rather than warm or playful

This visual personality should guide every layout and styling choice in the refresh.

## Product Constraints

- Keep the application as a pure Python `tkinter` / `ttk` desktop app.
- Do not change database schema, review scheduling, translation behavior, or article fetching logic as part of this redesign.
- Preserve all current core capabilities:
  - language and lexicon selection
  - plan saving
  - floating review card
  - TXT / CSV import
  - example enrichment
  - progress summary and heatmap
  - lexicon overview table
  - daily news list, favorites, and article reading
- Prefer re-layout, restyling, copy cleanup, and stronger defaults over introducing new features.

## Chosen Design Direction

FloatVocab will move toward a brand-led workbench design instead of a control-heavy desktop form. The home screen should feel like a focused study dashboard where the user immediately understands what today’s work is, what state learning is in, and where to continue.

### Visual Thesis

Quiet premium study workspace: cold white surfaces, gray-blue structure, restrained accent color, generous spacing, and strong typography hierarchy doing more work than borders or saturated fills.

### Interaction Thesis

- Primary actions should be few, obvious, and calm.
- Secondary actions should remain easy to find without competing for attention.
- Settings should support the study flow, not dominate first glance.
- Reading and review surfaces should feel more immersive and less like utility popups.

## Information Architecture

The main window should be reorganized into three large zones that clarify attention order.

### 1. Brand Header

The top band should establish identity and orientation without crowding the page.

Contents:

- product title and concise positioning copy
- current language / lexicon context
- one or two primary actions only, such as showing the floating card and refreshing briefs

The header should create confidence and polish, not serve as a control dump.

### 2. Today Workbench

This is the main operational area and should answer:

- what am I studying now
- what is my daily plan
- how far along am I
- what should I do next

Contents:

- language and lexicon context
- daily target and target date controls
- progress summary and review state
- floating card appearance controls, presented as supporting preferences rather than the dominant task

The workbench should prioritize today’s learning state before configuration detail.

### 3. Content Space

The lower area should behave like a calm content workspace instead of multiple management boxes.

Contents:

- lexicon overview as a clean browsing table
- daily news and favorites as reading-oriented content panes
- improved transitions between selecting, previewing, saving, and reopening content

The reading side should feel closer to a high-quality reader than an admin panel.

## Visual System

### Color

Use a restrained palette built around:

- cold white main background
- soft gray-blue panel surfaces
- darker slate text for primary content
- muted gray-blue for helper text
- one disciplined accent family for actions, progress emphasis, and selected states

Avoid loud contrast, warm branding, or decorative gradients. Accent usage should be sparse and intentional.

### Typography

Typography should create most of the hierarchy.

- stronger title treatment in the brand header
- clear section titles with quieter subtitles
- slightly larger, more breathable body copy where reading comfort matters
- helper copy that is visible but not noisy

Text density should decrease compared with the current version. Labels should be shortened where needed to support a calmer experience.

### Surfaces and Borders

Panels should read as refined surfaces, not boxed widgets.

- reduce heavy frame feeling
- prefer spacing and subtle tonal contrast over obvious borders
- keep corners and padding consistent across panels
- use separators sparingly

The interface should feel assembled from a small set of reusable, disciplined surface types.

## Main Window Component Changes

### Header

- Strengthen brand identity with a more intentional title block.
- Simplify action area so only key actions remain visually prominent.
- Add concise contextual copy that helps the user understand the current study setup at a glance.

### Study Plan Panel

- Make plan controls easier to scan by grouping context first and dates/targets second.
- Present system feedback more elegantly, with clearer spacing around status text.
- Reduce the “form” feeling so the panel reads as a study setup card, not a settings dialog.

### Floating Card Preferences Panel

- Keep the current controls, but visually demote them beneath learning state.
- Clarify that these controls are personalization options, not the main job of the page.
- Use calmer helper copy and better alignment so sliders and selectors feel less mechanical.

### Progress / Summary Panel

- Make progress information more legible and more product-like.
- Treat the heatmap as part of a composed performance surface rather than an embedded utility fragment.
- Improve spacing so summary data can breathe.

### Lexicon Overview

- Keep the table, but make it feel cleaner and less crowded.
- Improve heading hierarchy, surrounding whitespace, and table framing.
- Preserve efficient scanning while reducing visual noise.

### Daily News and Favorites

- Reframe the area as a reading workspace.
- Give latest briefs and favorites clearer structure without making them look like separate tools.
- Improve balance between list selection and summary/detail reading.
- Empty and low-content states should feel intentional rather than unfinished.

## Floating Review Window

The floating card should become a refined study surface.

- stronger word hierarchy
- calmer detail area
- clearer separation between answer content and actions
- more premium spacing and default proportions
- controls that remain visible and stable even with long meanings or examples

It should feel like a focused reading card with actions, not a generic popup with buttons.

## Article Reader Window

The article reader should align with the same quiet visual system.

- cleaner title and metadata rhythm
- more comfortable body spacing for longer reading
- restrained chrome around supporting controls
- stronger sense of a reading pane rather than a utility modal

## Copy Direction

Copy should support the mature tone:

- shorter labels
- fewer exclamation-style cues
- neutral, calm helper text
- clearer status wording when content is missing or unavailable

The tone should feel composed and confident.

## Responsiveness and Desktop Behavior

The app only needs desktop responsiveness, but it should resize gracefully.

- main sections should keep their hierarchy at larger sizes
- content panes and tables should expand naturally
- no panel should feel cramped at typical laptop widths
- floating card and reader should retain sensible minimum proportions

## Implementation Boundaries

Allowed:

- reorganizing layout inside the current UI-building flow
- adjusting panel composition and grouping
- expanding the existing theme/styling layer
- restyling `ttk` widgets and relevant `tk` widgets
- refining labels, helper copy, and default visual settings
- improving empty-state presentation where existing data can be absent

Not in scope:

- new learning mechanics
- database or schema changes
- changing review scoring behavior
- changing translation or news-fetch logic
- adding external UI dependencies
- migrating away from `tkinter`

## Verification Expectations

The refresh is complete when:

- the app still launches cleanly
- current study, import, review, and reading flows still work
- the home screen clearly reads as a mature study workbench
- the main window feels more spacious and less control-heavy
- the floating card and article reader visibly share the same brand language
- tables and reading panes are easier and calmer to use
- no existing UI behavior regressions appear in automated or manual smoke checks
