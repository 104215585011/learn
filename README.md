# FloatVocab 浮窗背词

轻量级 Windows 桌面背单词工具。当前版本使用 Python 标准库实现，无需联网、无需安装第三方依赖。

## 运行

```powershell
python app.py
```

## 功能

- 内置 50 个考研核心词作为测试词库
- 支持导入 TXT / CSV 单词表
- SQLite 本地保存词库、计划、掌握状态、复习记录
- 主窗口选择词库、设置每日新词和目标日期
- 桌面悬浮窗置顶显示，点击翻面
- 快捷键：
  - `Right` / `Alt + Right`：认识，进入下一词
  - `Left` / `Alt + Left`：不认识，进入下一词
  - `Space` / `Alt + Space`：翻面
  - `Esc`：隐藏悬浮窗
- 支持调节透明度、字体大小、背景颜色
- 进度统计和 30 天打卡热力图

## 导入格式

TXT 每行一个单词：

```text
abandon\t/əˈbændən/\t放弃\tNever abandon your plan.
```

CSV 支持列名：`word, phonetic, meaning, example`。没有表头时按这个顺序解析。
