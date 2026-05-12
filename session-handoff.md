# FloatVocab 会话交接

## 当前已验证

- 所有核心功能基于 README 和代码结构推断为 passing（未经本地实际运行验证）
- 测试文件存在：`tests/test_study_state.py`、`tests/test_services.py`、`tests/test_ui_layout.py`、`tests/test_global_translation.py`、`tests/test_news_digest_resilience.py` 等
- `data/example_cache/` 包含大量缓存文件，enrichment pipeline 曾正常运行

**下一轮开工前必须运行**：
```powershell
python -m pytest tests/ -v
```

---

## 本轮改动

- 创建了项目 agent harness 文件（AGENTS.md、init.sh、claude-progress.md、feature_list.json、session-handoff.md、clean-state-checklist.md、evaluator-rubric.md、quality-document.md）
- 未修改任何功能代码

---

## 仍损坏或未验证

- `feature_list.json` 中所有功能状态均为推断，**未经实际运行验证**
- `transparency-font-color`（priority 10）和 `cloud-sync`（priority 11）状态为 `not_started`，需确认实现程度

---

## 下一步最佳动作

1. 运行 `python -m pytest tests/ -v`，确认全绿
2. 如有失败：记录到 `claude-progress.md`，修复后再继续
3. 实际运行 `python app.py`，逐一验证 `feature_list.json` 中 passing 功能的 `verification` 步骤
4. 对不符合的功能，将 status 从 `passing` 改回 `not_started` 或 `blocked`
5. 从 priority 最小的 `not_started` 功能开始新工作

**不要动的地方**：
- `floatvocab/db.py` — schema 敏感，改动会影响所有 repository
- `electron/main/index.js` — Electron 主进程，IPC 通道定义在此

---

## 命令参考

```powershell
# 验证
python -m pytest tests/ -v

# 启动 Python GUI
python app.py

# 启动 Electron
cd electron
npm install
npm run dev

# 运行 enrichment
python example_pipeline.py

# 更新新闻摘要
python scripts/update_daily_briefs.py
```
