# Codex Branch Workflow

- 新功能或高风险改动优先在新的 `codex/*` 分支上进行，避免直接和当前 `codex/floatvocab` 工作区冲突。
- 分支上的改动完成后，先由 Codex 跑相关验证，再向用户确认结果和影响范围。
- 只有在用户确认无误后，才把改动并回本地 `codex/floatvocab`。
- 并回 `codex/floatvocab` 后，删除已经完成使命的冗余本地分支。
- 如果远端主线有更新，先确认本地工作区干净，再对 `codex/floatvocab` 执行拉取。
