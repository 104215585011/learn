# FloatVocab UI Iteration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refine the FloatVocab desktop UI so the dashboard is more task-focused, the news area is reading-first, and the floating windows feel more polished without changing product behavior.

**Architecture:** Keep all behavior in the existing `app.py` structure, but tighten the UI around a clearer theme system and a more intentional layout hierarchy. Implement the work in small slices: first consolidate styling and dashboard hierarchy, then reshape the news workspace and reader presentation, then polish the floating review card and align the detached article window.

**Tech Stack:** Python, tkinter, ttk, sqlite3, pytest

---

## File Structure

- Modify: `C:\Users\10421\project\learn\app.py`
  - Consolidate duplicated style helpers and add clearer UI tokens.
  - Rework the dashboard hero, plan panel hierarchy, stats summary, and control emphasis.
  - Rebuild the news workspace around a primary latest-news column and a secondary favorites column.
  - Polish the floating review card and the article reader while preserving existing callbacks and behavior.
- Modify: `C:\Users\10421\project\learn\tests\test_ui_layout.py`
  - Add or update focused UI-structure tests that lock in the new copy and helper methods without requiring interactive desktop automation.
- Read during execution:
  - `C:\Users\10421\project\learn\docs\superpowers\specs\2026-04-19-floatvocab-ui-iteration-design.md`
  - `C:\Users\10421\project\learn\docs\superpowers\specs\2026-04-15-floatvocab-ui-redesign-design.md`

### Task 1: Consolidate Theme And Dashboard Entry Hierarchy

**Files:**
- Modify: `C:\Users\10421\project\learn\tests\test_ui_layout.py`
- Modify: `C:\Users\10421\project\learn\app.py`

- [ ] **Step 1: Write a failing test for the new task-entry copy and hierarchy helpers**

```python
def test_ui_copy_mentions_continue_review_and_dashboard_summary():
    from app import FloatVocabApp

    source = FloatVocabApp.build_ui.__code__.co_consts
    joined = "\n".join(str(item) for item in source if isinstance(item, str))

    assert "继续复习" in joined
    assert "今日待复习" in joined or "待复习" in joined
```

- [ ] **Step 2: Run the targeted test to verify it fails for the current UI copy**

Run: `pytest tests/test_ui_layout.py -k continue_review_and_dashboard_summary -v`
Expected: FAIL because the current hero copy does not yet expose the new task-entry wording.

- [ ] **Step 3: Remove duplicated style/helper definitions and implement the dashboard task-entry hierarchy**

```python
def build_dashboard_summary_text(self) -> str:
    stats = self.study_service.get_study_stats()
    if not stats:
        return "今天还没有学习记录，先开始一轮复习。"
    summary = stats["summary"]
    total = summary["total"] or 0
    mastered = summary["mastered"] or 0
    due = summary["due"] or 0
    percent = round((mastered / total) * 100) if total else 0
    return f"今日待复习 {due} 个，已掌握 {percent}%"
```

```python
ttk.Label(
    hero,
    text=self.build_dashboard_summary_text(),
    style="HeroBody.TLabel",
).grid(row=1, column=0, sticky="w", pady=(6, 0))

ttk.Button(
    hero_actions,
    text="继续复习",
    style="Primary.TButton",
    command=self.float_window.show_next,
).pack(side="left", padx=(0, 10))
```

- [ ] **Step 4: Run the targeted test again to verify it passes**

Run: `pytest tests/test_ui_layout.py -k continue_review_and_dashboard_summary -v`
Expected: PASS

- [ ] **Step 5: Commit the dashboard-entry slice**

```bash
git add app.py tests/test_ui_layout.py
git commit -m "refactor: sharpen dashboard task entry hierarchy"
```

### Task 2: Rebalance Study Plan, Style Panel, And Stats Strip

**Files:**
- Modify: `C:\Users\10421\project\learn\tests\test_ui_layout.py`
- Modify: `C:\Users\10421\project\learn\app.py`

- [ ] **Step 1: Write a failing test for new stats summary helpers and quieter utility actions**

```python
def test_ui_exposes_metric_summary_helpers():
    from app import FloatVocabApp

    assert hasattr(FloatVocabApp, "build_metric_items")
```

- [ ] **Step 2: Run the targeted test to verify it fails before helper extraction**

Run: `pytest tests/test_ui_layout.py -k metric_summary_helpers -v`
Expected: FAIL because `build_metric_items` does not exist yet.

- [ ] **Step 3: Add minimal helper methods and re-layout the panels without changing callbacks**

```python
def build_metric_items(self, stats: dict | None) -> list[tuple[str, str]]:
    if not stats:
        return [("今日待复习", "0"), ("已掌握", "0"), ("总词数", "0")]
    summary = stats["summary"]
    return [
        ("今日待复习", str(summary["due"] or 0)),
        ("已掌握", str(summary["mastered"] or 0)),
        ("总词数", str(summary["total"] or 0)),
    ]
```

```python
ttk.Button(plan_actions, text="保存计划", style="Primary.TButton", command=self.save_plan).pack(side="left")
ttk.Button(plan_actions, text="导入词库", style="Secondary.TButton", command=self.import_words).pack(side="left", padx=(10, 0))
ttk.Button(plan_actions, text="重命名", style="Quiet.TButton", command=self.edit_selected_lexicon).pack(side="left", padx=(18, 0))
ttk.Button(plan_actions, text="删除", style="Quiet.TButton", command=self.delete_selected_lexicon).pack(side="left", padx=(10, 0))
ttk.Button(plan_actions, text="补全例句", style="Quiet.TButton", command=self.enrich_examples).pack(side="left", padx=(10, 0))
```

- [ ] **Step 4: Run the targeted test and a broader layout smoke test**

Run: `pytest tests/test_ui_layout.py -k "metric_summary_helpers or ui_layout" -v`
Expected: PASS

- [ ] **Step 5: Commit the plan/style/stats slice**

```bash
git add app.py tests/test_ui_layout.py
git commit -m "feat: rebalance study controls and stats strip"
```

### Task 3: Rebuild The Daily News Workspace Around Reading

**Files:**
- Modify: `C:\Users\10421\project\learn\tests\test_ui_layout.py`
- Modify: `C:\Users\10421\project\learn\app.py`

- [ ] **Step 1: Write a failing test for structured preview text**

```python
def test_news_preview_helper_formats_structured_summary():
    from app import FloatVocabApp

    preview = FloatVocabApp.format_brief_preview(
        None,
        {
            "title": "Headline",
            "summary": "Summary body",
            "source_name": "Source",
            "published_at": "2026-04-19 08:00",
            "saved": 1,
            "url": "https://example.com",
        },
    )

    assert "Headline" in preview
    assert "Source" in preview
    assert "已收藏" in preview
```

- [ ] **Step 2: Run the targeted test to verify it fails before the helper exists**

Run: `pytest tests/test_ui_layout.py -k structured_summary -v`
Expected: FAIL because `format_brief_preview` does not exist yet.

- [ ] **Step 3: Add a preview formatter and rework the news layout around primary latest content and secondary favorites**

```python
def format_brief_preview(self, row: dict) -> str:
    saved = "已收藏" if row["saved"] else "可收藏并翻译"
    published = (row["published_at"] or "").replace("T", " ")[:16]
    return (
        f"{row['title']}\n"
        f"{row['source_name']} · {published}\n"
        f"{saved}\n\n"
        f"{row['summary']}\n\n"
        f"双击条目或收藏后可在阅读窗查看全文。\n{row['url']}"
    )
```

```python
content_shell = ttk.Frame(news_tab, style="Panel.TFrame")
content_shell.grid(row=2, column=0, sticky="nsew")
content_shell.columnconfigure(0, weight=3)
content_shell.columnconfigure(1, weight=2)
```

- [ ] **Step 4: Run the targeted test and the news-related UI tests**

Run: `pytest tests/test_ui_layout.py -k "structured_summary or news" -v`
Expected: PASS

- [ ] **Step 5: Commit the news-workspace slice**

```bash
git add app.py tests/test_ui_layout.py
git commit -m "feat: make news workspace reading-first"
```

### Task 4: Polish The Floating Review Card

**Files:**
- Modify: `C:\Users\10421\project\learn\tests\test_ui_layout.py`
- Modify: `C:\Users\10421\project\learn\app.py`

- [ ] **Step 1: Write a failing test for the floating card header helper**

```python
def test_floating_window_header_text_reflects_learning_state():
    from app import FloatingWindow

    class StubApp:
        class settings_service:
            @staticmethod
            def get_plan_settings():
                return {"bg_color": "#FFFFFF", "float_alpha": 1.0, "font_size": 24, "widget_size": "medium"}

    assert hasattr(FloatingWindow, "build_header_text")
```

- [ ] **Step 2: Run the targeted test to verify it fails before helper extraction**

Run: `pytest tests/test_ui_layout.py -k floating_window_header_text -v`
Expected: FAIL because `build_header_text` does not exist yet.

- [ ] **Step 3: Add a minimal header helper and restyle the card while preserving behavior**

```python
def build_header_text(self) -> str:
    if not self.card:
        return "FloatVocab · 准备开始"
    return "FloatVocab · 当前学习卡"
```

```python
self.card_header.configure(
    bg=bg,
    fg=THEME["muted"],
    font=("Segoe UI", 10, "bold"),
    padx=2,
    pady=2,
)
self.flip_button.configure(padx=18, pady=8)
```

- [ ] **Step 4: Run the targeted test and a focused UI smoke test**

Run: `pytest tests/test_ui_layout.py -k "floating_window_header_text or floating" -v`
Expected: PASS

- [ ] **Step 5: Commit the floating-card slice**

```bash
git add app.py tests/test_ui_layout.py
git commit -m "feat: polish floating review card presentation"
```

### Task 5: Align The Article Reader And Run Full Verification

**Files:**
- Modify: `C:\Users\10421\project\learn\tests\test_ui_layout.py`
- Modify: `C:\Users\10421\project\learn\app.py`

- [ ] **Step 1: Write a failing test for article preview/readability helper text**

```python
def test_article_window_still_mentions_reader_title():
    from app import DailyArticleWindow

    source = DailyArticleWindow.__init__.__code__.co_consts
    joined = "\n".join(str(item) for item in source if isinstance(item, str))

    assert "日报内容" in joined
    assert "收起" in joined
```

- [ ] **Step 2: Run the targeted test to verify the reader slice is covered**

Run: `pytest tests/test_ui_layout.py -k article_window_still_mentions_reader_title -v`
Expected: PASS or FAIL only if the constructor copy changes unexpectedly during restyling.

- [ ] **Step 3: Restyle the article window surfaces and spacing while preserving focus-loss behavior**

```python
self.header = tk.Frame(self.container, bg=THEME["hero"], height=48)
self.meta_label.configure(
    bg=THEME["panel"],
    fg=THEME["muted"],
    padx=18,
    pady=12,
    font=("Segoe UI", 10),
)
self.text.configure(
    bg=THEME["panel"],
    fg=THEME["text"],
    padx=18,
    pady=14,
    spacing1=4,
    spacing2=4,
    spacing3=8,
)
```

- [ ] **Step 4: Run the full targeted verification suite**

Run: `pytest tests/test_ui_layout.py -v`
Expected: PASS

Run: `python -m py_compile app.py`
Expected: no output

- [ ] **Step 5: Run manual smoke verification**

Run: `python app.py`
Check:
- hero shows task-oriented copy
- study plan actions still work
- stats section renders without overlap
- latest news selection updates preview
- favorites still open in the reader window
- floating window opens, flips, and records known/unknown reviews
- article reader still hides on focus loss

- [ ] **Step 6: Commit the final verification slice**

```bash
git add app.py tests/test_ui_layout.py docs/superpowers/specs/2026-04-19-floatvocab-ui-iteration-design.md docs/superpowers/plans/2026-04-19-floatvocab-ui-iteration.md
git commit -m "feat: iterate floatvocab desktop ui"
```
