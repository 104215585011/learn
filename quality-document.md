# FloatVocab 质量快照

跟踪代码库随时间变强还是变弱。会话结束后更新，对比不同时间点快照。

评分说明：★★★ 好 / ★★☆ 可用但有缺口 / ★☆☆ 脆弱 / ☆☆☆ 未知或损坏

---

## 快照历史

| 日期 | 总体健康度 | 变化摘要 |
|------|------------|----------|
| 2026-05-12 | — | 初始快照，基于代码结构推断，未经实际运行验证 |

---

## 产品领域

### 学习核心（study）

| 指标 | 评级 | 说明 |
|------|------|------|
| 验证状态 | ★★☆ | test_study_state.py 存在，实际通过情况待确认 |
| Agent 可读性 | ★★☆ | floatvocab/services/study_service.py 结构清晰，但 app.py 中仍有直接 DB 调用 |
| 测试稳定性 | ★★☆ | 测试文件存在，覆盖率未知 |
| 关键缺口 | 悬浮窗外观调节（透明度/字号/背景色）持久化状态未确认 |

### 词库导入（import）

| 指标 | 评级 | 说明 |
|------|------|------|
| 验证状态 | ★★☆ | test_services.py 覆盖部分场景 |
| Agent 可读性 | ★★★ | LexiconRepository 职责清晰 |
| 测试稳定性 | ★★☆ | 边界情况（格式错误、重复导入）覆盖未知 |
| 关键缺口 | 内置考试词库（data/vocab_sources/）文件是否完整待确认 |

### 全局翻译（translation）

| 指标 | 评级 | 说明 |
|------|------|------|
| 验证状态 | ★★☆ | test_global_translation.py 存在 |
| Agent 可读性 | ★★☆ | global_translation.py 较长，逻辑集中 |
| 测试稳定性 | ★☆☆ | 依赖 Windows API，CI 环境可能无法运行 |
| 关键缺口 | Windows 独占功能，跨平台测试策略缺失 |

### 新闻摘要（news）

| 指标 | 评级 | 说明 |
|------|------|------|
| 验证状态 | ★★☆ | test_news_digest_resilience.py 和 test_multilingual_* 存在 |
| Agent 可读性 | ★★★ | NewsService / NewsRepository 分离良好 |
| 测试稳定性 | ★★☆ | resilience 测试专门覆盖网络不可用场景 |
| 关键缺口 | 每日摘要更新脚本（scripts/update_daily_briefs.py）的定时机制未集成 |

### Enrichment Pipeline（enrichment）

| 指标 | 评级 | 说明 |
|------|------|------|
| 验证状态 | ★★☆ | data/example_cache/ 有大量缓存，说明曾正常运行 |
| Agent 可读性 | ★★☆ | example_pipeline.py 顶层脚本，逻辑可追踪 |
| 测试稳定性 | ★☆☆ | 无专门测试文件 |
| 关键缺口 | API 依赖（如有），离线行为未测试 |

### Electron 桌面壳（electron）

| 指标 | 评级 | 说明 |
|------|------|------|
| 验证状态 | ★★☆ | 基于 commit 历史推断可用 |
| Agent 可读性 | ★★☆ | electron/src/api.js 统一 API 调用，结构合理 |
| 测试稳定性 | ☆☆☆ | 无前端测试 |
| 关键缺口 | Python 进程与 Electron 之间 IPC 通信的错误恢复未测试 |

---

## 架构层

### Main Process（app.py）

| 指标 | 评级 | 说明 |
|------|------|------|
| 边界执行 | ★☆☆ | app.py 仍有直接 DB 调用，未完全走 repository 层 |
| Agent 可读性 | ★★☆ | 文件很长，但 THEME 和常量定义集中在顶部，结构可辨 |

### 数据层（floatvocab/db.py + repositories/）

| 指标 | 评级 | 说明 |
|------|------|------|
| 边界执行 | ★★★ | Repository 类职责清晰，schema 集中在 initialize_database() |
| Agent 可读性 | ★★★ | 四个 repository 各自独立，依赖注入清晰 |

### 服务层（floatvocab/services/）

| 指标 | 评级 | 说明 |
|------|------|------|
| 边界执行 | ★★★ | StudyService / NewsService / EnrichmentService / SettingsService 分工明确 |
| Agent 可读性 | ★★★ | 每个 service 只依赖自己的 repository |

### Electron Renderer（electron/src/）

| 指标 | 评级 | 说明 |
|------|------|------|
| 边界执行 | ★★☆ | api.js 统一出口，但部分组件可能直接调用 IPC |
| Agent 可读性 | ★★☆ | 组件数量少，结构简单 |

---

## 已知技术债

| 位置 | 描述 | 优先级 |
|------|------|--------|
| app.py | 直接执行 SQLite 查询，绕过 repository 层 | 中 |
| global_translation.py | 文件过长，多个职责混在一起 | 低 |
| electron/ | 无前端测试 | 中 |
| scripts/ | 无测试，脚本可靠性未知 | 低 |

---

## 更新说明

> 每次重要会话后更新本文件。更新时：
> 1. 在「快照历史」中添加一行
> 2. 修改变化的评级（不要删旧评级，用 ~~划掉~~ 标记降级，直接改标记升级）
> 3. 更新「关键缺口」和「技术债」
