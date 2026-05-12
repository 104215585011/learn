# FloatVocab — Codex 角色路由

这个项目里你有两个可能的角色：**Codex1（开发）** 或 **Codex2（测试）**。

## 每次会话开始

1. 读 `task-board.md`，找出当前哪个角色有任务在等待
2. 用户会告诉你本次扮演哪个角色，或者你可以问一句
3. 确认角色后，读对应文件：
   - Codex1(开发) → `agents/codex1-developer.md`
   - Codex2(测试) → `agents/codex2-tester.md`
4. 读完后按文件里的规则工作

## 如果没有明确说明

默认检查 `task-board.md`：
- 有 `TEST_IN_PROGRESS` 状态的 ticket → 你是 **Codex2**
- 有 `DEV_TODO` 或 `DEV_IN_PROGRESS` 状态的 ticket → 你是 **Codex1**
