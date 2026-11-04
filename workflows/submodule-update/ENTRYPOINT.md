# `consumer.submodule-update` 工作流 Harness

这是消费端 Agent 执行 submodule 更新工作流的入口。它只指导 Agent 在用户确认范围内完成版本升级，不自动漂移、不自动发布，也不替用户判断“最新”是否等于“稳定”。

## 入口前提

先确认当前工作目录是消费端父仓根目录，并按消费端总 Harness 读取：

1. 根 `README.md` 和 `AGENTS.md`；
2. `.gitmodules` 和当前父仓 gitlink；
3. submodule 当前 `manifest.yml`；
4. `docs/submodule-consumer-versioning.md`；
5. 本目录的 `WORKFLOW.md`。

用户只要求“检查版本”时，只执行只读预检，不修改任何文件、引用或分支。用户要求“更新 submodule”时，也必须先完成只读预检并展示计划，再等待确认。若本工作流是 Agent 刚根据同一顶层调用前的 `update-available` 结果路由到的，直接复用该预检快照，不为更新流程再次预检；独立的新更新请求则先预检一次。

## 阶段 1：只读核对

运行当前固定 submodule 中声明的 `consumer.submodule-preflight` 工具。默认命令为：

```powershell
python vendor/suanhai-team-external-expression-infrastructure/infrastructure/repository-management/tools/submodule-preflight/submodule_preflight.py `
  --root . `
  --path vendor/suanhai-team-external-expression-infrastructure
```

记录：父仓 HEAD、父仓 gitlink、submodule HEAD、父仓和 submodule 工作区、远端稳定 ref、Manifest 版本和当前能力列表，并保留触发本工作流的预检结果。远端 `main` 与当前 gitlink 不同只表示指针不同；没有获取提交历史、Manifest 差异与验收记录前，不得断言它是快进提交、包含功能升级或已验收版本。此阶段不执行 checkout。

以下任一项本地检查失败，停止写入并报告：父仓或 submodule 脏、submodule 未初始化、gitlink 与 HEAD 不一致、固定对象缺失、来源 URL 不符合预期、Manifest 无法读取。远端查询失败时报告远端未知；不能把远端未知写成一致，也不能把本地检查失败当成网络问题忽略。若完整预检已由触发本工作流的 Harness 执行，本阶段复用其本地和远端快照，避免递归调用预检。

## 阶段 2：确认候选

目标必须是基础设施仓已验收或由负责人明确选定的完整 40 位小写 commit SHA。Agent 需要展示当前 gitlink 与候选 SHA、候选 commit 的验收来源、Manifest 能力变化、测试计划、将要修改的父仓路径，以及是否要提交、推送和创建 PR。若候选仅来自远端 `main` 指针，先验证其提交关系、能力差异和验收状态；不能把 `update-available` 本身当作更新批准或稳定性证明。

如果用户只说“拉最新”，不能直接执行。先询问稳定分支、明确 SHA 和授权范围。没有用户确认，不 checkout、不更新 index、不提交、不推送。

候选验证默认复用目标完整 SHA 已有的基础设施完整回归成功记录，不能只看 PR/普通说明的快速检查或 Manifest；缺少完整记录时可选已有完整记录的版本，或在基础设施仓手动运行目标版本的完整 CI。消费端不重新运行基础设施全量测试。本地 checkout/fetch 不触发远端 CI；只恢复另一父仓分支已固定的版本时，执行版本一致性预检即可。未完成 CI 的试验提交应说明状态，由负责人明确选择试用并检查受影响能力。详见 [CI 验证边界](../../docs/ci-validation.md)。

## 阶段 3：受控更新

获得确认后，按消费端总 Harness 从集成分支创建短期分支；若消费端没有 `develop`，从默认分支创建短期分支，不直接修改默认分支。然后在 submodule 内获取目标对象并执行 `git checkout --detach <完整SHA>`。此时父仓 `HEAD` 仍记录旧 gitlink，预检工具会正确报告新旧不一致，因此不要在父仓提交前将完整 preflight 当作通过标准。

只暂存 submodule 路径，用 `git diff --cached --submodule=log` 确认父仓记录的是 gitlink。再检查 submodule 的 `HEAD` 等于候选 SHA、submodule 自身工作区干净、父仓 index 中该路径为 `160000` 且指向候选 SHA；运行目标 Manifest 校验、消费端冒烟测试和必要真实任务试用，并记录旧 SHA、新 SHA、测试结果和兼容性风险。提交后父仓 `HEAD` 与 submodule HEAD 一致、父仓工作区干净时，再运行完整 preflight；消费端已配置 CI 时，已推送的 PR 还应等待其对新 gitlink 的递归 clone 检查通过；未配置则记录本地接入与冒烟结果。若用户未授权提交，保留本地更新和验证证据并暂停，不重启触发本次更新的原能力；获得提交授权并通过更新后 preflight 后，才从新 SHA 重新开始。

提交、推送和创建 PR 仍是独立副作用，只有用户明确授权相应动作时才执行。

## 阶段 4：失败与回退

发生脏工作区、目标对象不可用、Manifest 校验失败、测试失败、冲突或用户撤回授权时，停止并保留现场。不要使用 `reset --hard`、`git clean`、强推或删除分支清理现场。未提交更新在确认没有其他操作者修改后才可 checkout 已记录的旧 SHA；已提交更新优先通过消费端 `git revert` 回退。

## 收口报告

报告当前和目标 SHA、父仓分支、gitlink 与 submodule HEAD 是否一致、Manifest 和测试结果、修改文件、是否提交/推送/创建 PR、仍需谁确认的事项。更新完成不代表基础设施能力稳定、项目事实正确或获得发布授权。
