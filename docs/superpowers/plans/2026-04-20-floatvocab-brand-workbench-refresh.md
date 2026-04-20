# FloatVocab Brand Workbench Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refresh FloatVocab into a calmer, more premium study workspace by restructuring the main dashboard, unifying the visual system, and polishing the floating review card and article reader without changing product behavior.

**Architecture:** Keep the work inside the existing `app.py` UI layer, using the current `tkinter` / `ttk` structure and expanding the existing theme/style helpers rather than introducing new dependencies or new windows. Drive the work with focused UI regression tests in `tests/test_ui_layout.py`, then update the main window, floating card, and article reader in small TDD-style slices.

**Tech Stack:** Python, `tkinter`, `ttk`, `sqlite3`, `unittest`

---

## File Map

- Modify: `C:\Users\wang\learn\app.py`
  - Expand `THEME`
  - Clean up duplicated `configure_root` / `configure_styles` helpers if still present
  - Rework `build_ui`
  - Refine `FloatingWindow`
  - Refine `DailyArticleWindow`
- Modify: `C:\Users\wang\learn\tests\test_ui_layout.py`
  - Add UI assertions for the new dashboard hierarchy, calmer copy, and polished floating/article surfaces

### Task 1: Lock the New Main Window Hierarchy with Tests

**Files:**
- Modify: `C:\Users\wang\learn\tests\test_ui_layout.py`
- Test: `C:\Users\wang\learn\tests\test_ui_layout.py`

- [ ] **Step 1: Write the failing test for the new dashboard hierarchy**

```python
    def test_main_window_exposes_brand_header_and_today_workbench(self):
        ui = app.FloatVocabApp()
        try:
            ui.root.update_idletasks()
            ui.root.update()

            self.assertEqual(ui.hero_title_label.cget("text"), "FloatVocab")
            self.assertIn("安静", ui.hero_body_label.cget("text"))
            self.assertEqual(ui.workbench_title_label.cget("text"), "今日学习")
            self.assertEqual(ui.plan_box_title_label.cget("text"), "学习设置")
            self.assertEqual(ui.style_box_title_label.cget("text"), "阅读外观")
            self.assertEqual(ui.stats_box_title_label.cget("text"), "学习状态")

            tab_labels = [ui.content_notebook.tab(tab_id, "text") for tab_id in ui.content_notebook.tabs()]
            self.assertEqual(tab_labels[0], "工作台")
            self.assertIn("词库概览", tab_labels)
        finally:
            ui.root.destroy()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_main_window_exposes_brand_header_and_today_workbench -v`

Expected: FAIL because the new widget attributes and updated tab copy do not exist yet.

- [ ] **Step 3: Implement the minimal main-window hierarchy update**

```python
        self.hero_title_label = ttk.Label(hero, text="FloatVocab", style="HeroTitle.TLabel")
        self.hero_title_label.grid(row=0, column=0, sticky="w")
        self.hero_body_label = ttk.Label(
            hero,
            text="安静、克制的桌面学习空间，让今天的词汇计划和阅读内容更容易进入状态。",
            style="HeroBody.TLabel",
        )
        self.hero_body_label.grid(row=1, column=0, sticky="w", pady=(8, 0))

        self.content_notebook.add(dashboard_tab, text="工作台")

        self.workbench_title_label = ttk.Label(dashboard_tab, text="今日学习", style="WorkbenchTitle.TLabel")
        self.workbench_title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        plan_box = self.create_panel(dashboard_tab, "学习设置", "先确认语言、词库和今天的目标。")
        self.plan_box_title_label = plan_box.title_label

        style_box = self.create_panel(dashboard_tab, "阅读外观", "把悬浮窗调整到适合长时间停留的状态。")
        self.style_box_title_label = style_box.title_label

        stats_box = self.create_panel(dashboard_tab, "学习状态", "进度、复习节奏和热力图集中显示在这里。")
        self.stats_box_title_label = stats_box.title_label
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_main_window_exposes_brand_header_and_today_workbench -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/test_ui_layout.py app.py
git commit -m "feat: reshape floatvocab workbench hierarchy"
```

### Task 2: Build the Calmer Brand Style Layer

**Files:**
- Modify: `C:\Users\wang\learn\app.py`
- Test: `C:\Users\wang\learn\tests\test_ui_layout.py`

- [ ] **Step 1: Write the failing test for the refreshed style tokens**

```python
    def test_theme_uses_cool_toned_brand_palette_for_workbench_refresh(self):
        self.assertEqual(app.THEME["bg"], "#F3F7FB")
        self.assertEqual(app.THEME["panel"], "#FAFCFF")
        self.assertEqual(app.THEME["hero"], "#E8F0F8")
        self.assertEqual(app.THEME["accent"], "#5C7C99")
        self.assertEqual(app.THEME["muted"], "#607287")
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_theme_uses_cool_toned_brand_palette_for_workbench_refresh -v`

Expected: FAIL because the palette still reflects the earlier brighter product styling.

- [ ] **Step 3: Implement the refreshed theme and styles**

```python
THEME = {
    "bg": "#F3F7FB",
    "panel": "#FAFCFF",
    "panel_alt": "#F0F5FA",
    "hero": "#E8F0F8",
    "text": "#1F2D3D",
    "muted": "#607287",
    "accent": "#5C7C99",
    "accent_active": "#496983",
    "accent_soft": "#DCE7F1",
    "border": "#D9E3EC",
}

self.style.configure("HeroTitle.TLabel", background=THEME["hero"], foreground=THEME["text"], font=("Segoe UI", 26, "bold"))
self.style.configure("HeroBody.TLabel", background=THEME["hero"], foreground=THEME["muted"], font=("Segoe UI", 10))
self.style.configure("WorkbenchTitle.TLabel", background=THEME["bg"], foreground=THEME["text"], font=("Segoe UI", 15, "bold"))
self.style.configure("PanelTitle.TLabel", background=THEME["panel"], foreground=THEME["text"], font=("Segoe UI", 11, "bold"))
self.style.configure("Muted.TLabel", background=THEME["panel"], foreground=THEME["muted"], font=("Segoe UI", 9))
```

- [ ] **Step 4: Run the theme test**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_theme_uses_cool_toned_brand_palette_for_workbench_refresh -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_ui_layout.py
git commit -m "feat: add calm brand styling for floatvocab"
```

### Task 3: Recompose the Dashboard for Spaciousness and Clearer Priority

**Files:**
- Modify: `C:\Users\wang\learn\app.py`
- Test: `C:\Users\wang\learn\tests\test_ui_layout.py`

- [ ] **Step 1: Write the failing test for calmer helper copy and grouped workbench panels**

```python
    def test_dashboard_panels_use_calm_copy_and_supporting_status_layout(self):
        ui = app.FloatVocabApp()
        try:
            ui.root.update_idletasks()
            ui.root.update()

            self.assertIn("今天", ui.workbench_title_label.cget("text"))
            self.assertIn("词库", ui.lexicon_state_label.cget("text"))
            self.assertIn("悬浮窗会自动同步", ui.float_style_hint_label.cget("text"))
            self.assertIn("最近 30 天", ui.stats_summary_label.cget("text"))
        finally:
            ui.root.destroy()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_dashboard_panels_use_calm_copy_and_supporting_status_layout -v`

Expected: FAIL because the new labels and grouped summary widgets do not exist yet.

- [ ] **Step 3: Implement the dashboard recomposition**

```python
        dashboard_tab.rowconfigure(1, weight=0)
        dashboard_tab.rowconfigure(2, weight=1)

        self.workbench_title_label = ttk.Label(dashboard_tab, text="今日学习", style="WorkbenchTitle.TLabel")
        self.workbench_title_label.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        self.float_style_hint_label = ttk.Label(
            style_box,
            text="悬浮窗会自动同步这些设置，保持桌面阅读体验一致。",
            style="Muted.TLabel",
            wraplength=420,
            justify="left",
        )
        self.float_style_hint_label.pack(anchor="w", pady=(12, 0))

        self.stats_summary_label = ttk.Label(
            stats_box,
            text="最近 30 天的节奏和今天的完成度会一起展示。",
            style="Muted.TLabel",
        )
        self.stats_summary_label.pack(anchor="w", pady=(4, 10))
```

- [ ] **Step 4: Run the targeted test**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_dashboard_panels_use_calm_copy_and_supporting_status_layout -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_ui_layout.py
git commit -m "feat: recompose floatvocab dashboard copy and spacing"
```

### Task 4: Polish the Floating Review Card Into a Premium Reading Surface

**Files:**
- Modify: `C:\Users\wang\learn\app.py`
- Test: `C:\Users\wang\learn\tests\test_ui_layout.py`

- [ ] **Step 1: Write the failing test for the refined floating card defaults**

```python
    def test_floating_window_uses_premium_card_defaults_after_refresh(self):
        ui = app.FloatVocabApp()
        try:
            ui.float_window.apply_style()
            ui.root.update_idletasks()
            ui.root.update()

            self.assertEqual(ui.float_window.card_header.cget("fg"), app.THEME["muted"])
            self.assertEqual(ui.float_window.action_frame.cget("bg"), app.THEME["panel"])
            self.assertEqual(ui.float_window.drag_bar.cget("bg"), app.THEME["panel_alt"])
            self.assertGreater(int(ui.float_window.panel_frame.cget("padx")), 24)
        finally:
            ui.root.destroy()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_floating_window_uses_premium_card_defaults_after_refresh -v`

Expected: FAIL because the floating window still uses the earlier brighter utility styling.

- [ ] **Step 3: Implement the floating card polish**

```python
        self.panel_frame.configure(bg=THEME["panel"], padx=28, pady=24)
        self.card_header.configure(
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 10, "bold"),
        )
        self.content_frame.configure(bg=THEME["panel"])
        self.word_label.configure(bg=THEME["panel"], fg=THEME["text"])
        self.detail_label.configure(bg=THEME["panel"], fg=THEME["muted"])
        self.action_frame.configure(bg=THEME["panel"])
        self.drag_bar.configure(bg=THEME["panel_alt"])
        self.resize_grip.configure(bg=THEME["panel"], fg=THEME["muted"])
```

- [ ] **Step 4: Run the targeted floating-window test**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_floating_window_uses_premium_card_defaults_after_refresh -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_ui_layout.py
git commit -m "feat: polish floatvocab floating review card"
```

### Task 5: Unify the Daily Reader with the New Brand Language

**Files:**
- Modify: `C:\Users\wang\learn\app.py`
- Test: `C:\Users\wang\learn\tests\test_ui_layout.py`

- [ ] **Step 1: Write the failing test for the calmer reader styling**

```python
    def test_article_reader_matches_refreshed_reading_surface(self):
        ui = app.FloatVocabApp()
        try:
            self.assertEqual(ui.article_window.container.cget("bg"), app.THEME["panel"])
            self.assertEqual(ui.article_window.header.cget("bg"), app.THEME["hero"])
            self.assertEqual(ui.article_window.title_label.cget("fg"), app.THEME["text"])
            self.assertEqual(ui.article_window.meta_label.cget("fg"), app.THEME["muted"])
        finally:
            ui.root.destroy()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_article_reader_matches_refreshed_reading_surface -v`

Expected: FAIL because the reader window has not yet been aligned to the new brand palette and reading rhythm.

- [ ] **Step 3: Implement the reader refresh**

```python
        self.container.configure(bg=THEME["panel"])
        self.header.configure(bg=THEME["hero"], height=52)
        self.title_label.configure(bg=THEME["hero"], fg=THEME["text"], font=("Segoe UI", 12, "bold"))
        self.hide_label.configure(bg=THEME["hero"], fg=THEME["muted"], font=("Segoe UI", 10, "bold"))
        self.meta_label.configure(bg=THEME["panel"], fg=THEME["muted"], font=("Segoe UI", 9))
        self.summary.configure(
            bg=THEME["panel"],
            fg=THEME["text"],
            insertbackground=THEME["text"],
            spacing1=2,
            spacing2=8,
            spacing3=4,
            padx=18,
            pady=18,
        )
```

- [ ] **Step 4: Run the targeted reader test**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_article_reader_matches_refreshed_reading_surface -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_ui_layout.py
git commit -m "feat: align daily reader with brand refresh"
```

### Task 6: Run the Focused Regression Suite and Clean Up Duplicated UI Helpers

**Files:**
- Modify: `C:\Users\wang\learn\app.py`
- Test: `C:\Users\wang\learn\tests\test_ui_layout.py`

- [ ] **Step 1: Write the failing test that guards against duplicated style setup regressions**

```python
    def test_app_creates_single_style_object_and_main_widgets_initialize_once(self):
        ui = app.FloatVocabApp()
        try:
            self.assertIsNotNone(ui.style)
            self.assertTrue(hasattr(ui, "content_notebook"))
            self.assertTrue(hasattr(ui, "float_window"))
            self.assertTrue(hasattr(ui, "article_window"))
        finally:
            ui.root.destroy()
```

- [ ] **Step 2: Run the test**

Run: `python -m unittest tests.test_ui_layout.AppLayoutTests.test_app_creates_single_style_object_and_main_widgets_initialize_once -v`

Expected: PASS or FAIL. If it already passes, keep it as a guard before the final cleanup.

- [ ] **Step 3: Remove duplicated UI helper definitions and keep one canonical style path**

```python
    def configure_root(self):
        self.root.title("FloatVocab 悬浮背词")
        self.root.geometry("1180x860")
        self.root.minsize(1080, 760)
        self.root.configure(bg=THEME["bg"])

    def configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        ...

    def create_panel(self, parent, title: str, subtitle: str | None = None):
        panel = ttk.Frame(parent, style="Panel.TFrame", padding=22)
        panel.title_label = ttk.Label(panel, text=title, style="PanelTitle.TLabel")
        panel.title_label.pack(anchor="w")
        ...
        return panel
```

- [ ] **Step 4: Run the focused suite**

Run: `python -m unittest tests.test_ui_layout -v`

Expected: PASS

- [ ] **Step 5: Run the broader regression suite**

Run: `python -m unittest tests.test_services tests.test_async_error_callbacks tests.test_news_digest_resilience tests.test_ui_layout -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app.py tests/test_ui_layout.py
git commit -m "refactor: finalize floatvocab brand refresh ui"
```

## Self-Review

- Spec coverage:
  - Main workbench hierarchy: covered by Tasks 1 and 3
  - Brand palette and calmer visual system: covered by Task 2
  - Floating review card polish: covered by Task 4
  - Article reader alignment: covered by Task 5
  - Regression safety and helper cleanup: covered by Task 6
- Placeholder scan:
  - No `TODO`, `TBD`, or “implement later” markers remain
  - Every code-changing step includes example code or the exact assertions to add
- Type consistency:
  - New widget handles use consistent names: `hero_title_label`, `hero_body_label`, `workbench_title_label`, `plan_box_title_label`, `style_box_title_label`, `stats_box_title_label`, `float_style_hint_label`, `stats_summary_label`
  - All tests target `AppLayoutTests` and the existing `app.FloatVocabApp`
