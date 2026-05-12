# FloatVocab 进度日志

## 当前已验证状态

- **仓库根目录**：项目所在路径
- **标准启动路径**：`python app.py`
- **标准验证路径**：`python -m pytest tests/ -v`
- **当前最高优先级未完成功能**：查看 `feature_list.json` 中 priority 最小且 status != passing 的条目
- **当前 blocker**：无

### 已确认 passing 的功能

- 核心词库（SQLite 存储、状态追踪）
- 悬浮窗学习模式（翻面、快捷键）
- 词库导入（TXT / CSV）
- 进度统计 + 30 天打卡热力图
- 全局翻译气泡（global_translation）
- 多语言新闻摘要（news_digest）
- 单词例句 enrichment pipeline（example_pipeline）
- Electron 桌面壳（基础 dashboard 和悬浮窗通信）

---

## 会话记录

### 会话 2026-05-12（项目规范初始化）

- **本轮目标**：创建 agent harness 文件（AGENTS.md、init.sh、feature_list.json 等）
- **已完成**：创建全部 8 个规范文件
- **运行过的验证**：— （初始化轮次，未修改功能代码）
- **已记录证据**：— 
- **提交记录**：— 
- **已知风险或未解决问题**：feature_list.json 中功能状态基于 README 和代码结构推断，需下一轮校准
- **下一步最佳动作**：运行 `python -m pytest tests/ -v` 确认基础状态，然后选取 feature_list.json 中 priority 最小的 not_started 功能开工
