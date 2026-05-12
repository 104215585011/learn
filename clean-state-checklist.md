# FloatVocab 收尾检查清单

每次会话结束前逐项确认。所有条目必须通过才能算干净收尾。

---

## 基础状态

- [ ] `python -m pytest tests/ -v` 全部通过（无 FAILED、无 ERROR）
- [ ] `python app.py` 能正常启动，无报错崩溃
- [ ] `cd electron && npm run dev` 能正常启动（如本轮涉及 Electron 改动）

## 功能清单

- [ ] `feature_list.json` 中本轮操作的功能 `status` 已更新（不能留在 `in_progress`）
- [ ] 标记为 `passing` 的功能 `evidence` 字段已填写具体验证记录
- [ ] 没有功能被错误标记为 `passing`（即：evidence 为空但 status 是 passing）
- [ ] 同一时间只有 0 或 1 个功能处于 `in_progress`

## 进度文档

- [ ] `claude-progress.md` 已追加本轮会话记录（目标 / 已完成 / 验证 / 证据 / 风险 / 下一步）
- [ ] `session-handoff.md` 已更新，下一轮 agent 可以只读这一个文件就知道从哪继续

## 代码质量

- [ ] 无半成品代码（如 `TODO: implement this`、`pass` 占位、空函数体）留在功能路径上
- [ ] 无未使用的 import 或临时调试代码（`print`、`breakpoint()`）被提交
- [ ] 涉及 `floatvocab/db.py` schema 变更时，`initialize_database()` 已同步更新

## 交接准备

- [ ] 下一轮 agent 不需要任何口头说明就能继续工作
- [ ] 已知的未解决问题已记录在 `claude-progress.md`「已知风险」和 `feature_list.json`「notes」中
- [ ] `clean-state-checklist.md` 本身未被修改（除非流程本身需要调整）
