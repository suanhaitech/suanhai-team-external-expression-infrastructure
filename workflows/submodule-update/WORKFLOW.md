# 消费端 submodule 更新工作流

状态：`implemented / experimental`

## 目标

在小组资产仓中，将基础设施 submodule 从当前父仓 gitlink 更新到一个已经验收、可复现的完整 commit，同时留下可审阅的版本差异和验证证据。

## 输入

- 消费端父仓根目录；
- submodule 相对路径，通常为 `vendor/suanhai-team-external-expression-infrastructure`；
- 目标基础设施仓、稳定 ref 和完整 40 位候选 commit；
- 候选 commit 的验收来源、兼容性说明和试用范围；
- 用户对更新、提交、推送或创建 PR 的明确授权边界。

## 输出

- 更新前的父仓 commit、旧 gitlink、submodule HEAD 和预检快照；
- 目标 commit、Manifest 能力清单和兼容性核对结果；
- 父仓中只包含 submodule gitlink 的可审阅差异；
- 更新后的 preflight、Manifest 校验、消费端冒烟测试和必要真实任务试用结果；
- 提交或 PR 建议。提交、推送和合并是否执行，以用户明确授权为准。

## 阶段

1. 读取消费端 `README.md`、`AGENTS.md`、`.gitmodules`、当前 Manifest 和版本协议；
2. 检查父仓和 submodule 工作区干净、gitlink 与 HEAD 一致，并运行 `consumer.submodule-preflight`；
3. 核对目标 commit 是完整 SHA、对象可获取、来源仓库正确，并读取目标 Manifest；
4. 展示旧 SHA、新 SHA、能力变化、兼容性风险和将要修改的路径，等待用户确认；
5. 按消费端总 Harness 选择集成基线：配置了 `develop` 时从最新 `develop` 创建短期分支；没有 `develop` 时从默认分支创建短期分支，不直接修改默认分支；明确 checkout 目标 commit；
6. 更新父仓 gitlink，只暂存 submodule 路径；
7. 在父仓提交前，核验 submodule HEAD、父仓 index 中 `160000` gitlink 和目标 SHA 一致，确认 submodule 自身干净，并运行可在当前环境执行的目标 Manifest 校验与消费端冒烟测试；
8. 记录版本、测试和待解决问题；按用户授权提交、推送和创建 PR；
9. 在父仓提交完成且工作区干净后，再运行完整 `consumer.submodule-preflight`；CI 也应对包含新 gitlink 的提交执行新 clone 检查；
10. 报告最终 gitlink、测试证据和未执行的外部动作。

## 禁止事项

- 不使用 `git submodule update --remote` 自动跟随远端；
- 不把远端最新提交直接当成稳定版本；
- 不在脏工作区上更新或覆盖他人修改；
- 不直接修改消费端 `main`，不强推、不 reset、不 clean；
- 不把 submodule 文件复制成父仓普通文件；
- 不把更新成功等同于项目事实验收或发布授权。
