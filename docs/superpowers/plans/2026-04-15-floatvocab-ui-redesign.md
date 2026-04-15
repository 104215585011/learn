# FloatVocab UI Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the existing Tkinter desktop UI so it feels like a modern study product while preserving all current behavior.

**Architecture:** Keep all business logic in `app.py`, but introduce a clearer theme layer and reorganize widget construction into a cleaner dashboard layout. Update the floating card and article reader to share the same visual language, then manually verify existing workflows still behave the same.

**Tech Stack:** Python, tkinter, ttk, sqlite3

---

## File Structure

- Modify: `C:\Users\wang\learn\app.py`
  - Add theme constants and ttk styling helpers
  - Rebuild the main window layout in `build_ui`
  - Refresh widget styling for treeviews, buttons, and text areas
  - Restyle `FloatingWindow`
  - Restyle `DailyArticleWindow`
- Read during implementation:
  - `C:\Users\wang\learn\docs\superpowers\specs\2026-04-15-floatvocab-ui-redesign-design.md`

### Task 1: Establish Theme Tokens And ttk Styles

**Files:**
- Modify: `C:\Users\wang\learn\app.py`

- [ ] **Step 1: Add centralized theme constants near the top-level app constants**

```python
THEME = {
    "bg": "#F4F8FC",
    "panel": "#FFFFFF",
    "panel_alt": "#EEF5FB",
    "border": "#D7E6F2",
    "text": "#16324A",
    "muted": "#5F7990",
    "accent": "#1F8CFF",
    "accent_soft": "#DCEEFF",
    "success": "#1FA971",
    "warning": "#F39C3D",
}
```

- [ ] **Step 2: Add a style configuration helper on `FloatVocabApp`**

```python
def configure_styles(self):
    self.style = ttk.Style()
    self.style.theme_use("clam")
    self.style.configure("App.TFrame", background=THEME["bg"])
    self.style.configure("Panel.TFrame", background=THEME["panel"])
    self.style.configure("PanelTitle.TLabel", background=THEME["panel"], foreground=THEME["text"], font=("Segoe UI", 12, "bold"))
    self.style.configure("Muted.TLabel", background=THEME["bg"], foreground=THEME["muted"], font=("Segoe UI", 10))
    self.style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"))
```

- [ ] **Step 3: Call the style helper before building widgets**

Run this shape in `__init__`:

```python
self.configure_root()
self.configure_styles()
self.build_ui()
```

- [ ] **Step 4: Run the app to verify it still launches**

Run: `python app.py`
Expected: main window opens without `ttk.Style` errors

- [ ] **Step 5: Commit**

```bash
git add app.py docs/superpowers/specs/2026-04-15-floatvocab-ui-redesign-design.md docs/superpowers/plans/2026-04-15-floatvocab-ui-redesign.md
git commit -m "design FloatVocab UI refresh"
```

### Task 2: Rebuild The Main Window Layout

**Files:**
- Modify: `C:\Users\wang\learn\app.py`

- [ ] **Step 1: Replace the current stacked `LabelFrame` composition with a dashboard layout**

Implement a structure equivalent to:

```python
shell = ttk.Frame(self.root, style="App.TFrame", padding=20)
shell.grid(row=0, column=0, sticky="nsew")
shell.columnconfigure(0, weight=1)

hero = ttk.Frame(shell, style="Panel.TFrame", padding=20)
controls = ttk.Frame(shell, style="App.TFrame")
workspace = ttk.Frame(shell, style="App.TFrame")
```

- [ ] **Step 2: Put study-plan and style controls into side-by-side panels**

Keep the same bound variables and commands, but move them into two visually balanced sections with internal spacing and helper copy.

- [ ] **Step 3: Promote key actions with clearer button hierarchy**

Use:
- primary styling for `显示悬浮窗`
- neutral secondary styling for `保存计划`
- utility styling for `导入 TXT / CSV 词库` and `补全缺失例句`

- [ ] **Step 4: Keep all original callbacks unchanged**

Confirm these commands remain wired exactly:

```python
command=self.save_plan
command=self.float_window.show_next
command=self.import_words
command=self.enrich_examples
command=self.choose_color
command=self.refresh_daily_briefs
command=self.save_selected_brief
```

- [ ] **Step 5: Run the app to verify the main dashboard renders**

Run: `python app.py`
Expected: the app opens with the new section order and all controls visible

### Task 3: Polish Progress, Tables, And News Workspace

**Files:**
- Modify: `C:\Users\wang\learn\app.py`

- [ ] **Step 1: Restyle the stats area as a lighter summary panel**

Keep:
- `self.progress_label`
- `self.progress`
- `self.heatmap_frame`

But place them in a cleaner summary block with more spacing and less heavy framing.

- [ ] **Step 2: Rebuild the lexicon overview section with a cleaner table container**

Retain:

```python
self.words_tree = ttk.Treeview(words_box, columns=("word", "meaning", "status"), show="headings", height=8)
```

but give the table its own polished container and consistent padding.

- [ ] **Step 3: Rebuild the daily news area into a balanced two-column workspace**

Retain both:

```python
self.brief_tree
self.favorite_tree
```

and the summary text box, while improving:
- spacing
- section labels
- top action bar alignment
- proportional widths

- [ ] **Step 4: Verify selection bindings still work**

Check that these remain present and active:

```python
self.brief_tree.bind("<<TreeviewSelect>>", lambda _event: self.show_selected_brief())
self.favorite_tree.bind("<<TreeviewSelect>>", lambda _event: self.show_selected_favorite())
```

- [ ] **Step 5: Run the app and manually click through tables**

Run: `python app.py`
Expected: tables render cleanly, selections still populate details, double-click behavior still opens/save items

### Task 4: Restyle The Floating Review Card

**Files:**
- Modify: `C:\Users\wang\learn\app.py`

- [ ] **Step 1: Update `FloatingWindow` base surfaces and typography**

Adjust the existing widgets so the hierarchy becomes:
- large word display
- quieter detail area
- clean action row
- subtle helper row

- [ ] **Step 2: Improve button visual roles without changing commands**

Keep:

```python
self.unknown_button = tk.Button(...)
self.flip_button = tk.Button(...)
self.known_button = tk.Button(...)
```

but style them so the center action reads neutral and the outer actions read clearly distinct.

- [ ] **Step 3: Keep current behavior for move, resize, flip, and review**

Do not change:
- keyboard shortcuts
- drag handling
- resize handling
- `mark_known`
- `mark_unknown`
- `flip`

- [ ] **Step 4: Run the app and open the floating card**

Run: `python app.py`
Expected: the card appears with improved spacing and all three actions still work

### Task 5: Restyle The Daily Article Reader And Final Smoke Test

**Files:**
- Modify: `C:\Users\wang\learn\app.py`

- [ ] **Step 1: Restyle `DailyArticleWindow` to match the new app language**

Keep the same structure but update:
- header surface
- title emphasis
- metadata contrast
- text area spacing and colors

- [ ] **Step 2: Ensure focus-loss hide behavior remains intact**

Keep:

```python
self.bind("<FocusOut>", lambda _event: self.after(120, self.hide_if_focus_lost))
```

- [ ] **Step 3: Perform a manual smoke test of the core flows**

Run: `python app.py`
Check:
- choose lexicon
- save plan
- open floating review window
- flip / known / unknown actions
- import dialog opens
- news list refresh button is visible and clickable
- selecting a news item updates preview
- opening a saved article still works

- [ ] **Step 4: Record any visual regressions and fix them inline**

If a widget loses contrast, spacing, or resizing behavior, adjust immediately in `app.py` before closing the task.

- [ ] **Step 5: Commit**

```bash
git add app.py
git commit -m "refresh FloatVocab desktop UI"
```
