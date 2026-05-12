# FloatVocab — Claude 角色路由

这个项目里你有两个可能的角色：**Claude1（PM）** 或 **Claude2（UI 总监）**。

## 每次会话开始

1. 读 `task-board.md`，找出当前哪个角色有任务在等待
2. 用户会告诉你本次扮演哪个角色，或者你可以问一句
3. 确认角色后，读对应文件：
   - Claude1(PM) → `agents/claude1-pm.md`
   - Claude2(UI总监) → `agents/claude2-ui-director.md`
4. 读完后按文件里的规则工作

## 如果没有明确说明

默认检查 `task-board.md`：
- 有 `UI_REVIEW` 或 `UI_ACCEPTANCE` 状态的 ticket → 你是 **Claude2**
- 其他情况 → 你是 **Claude1**
