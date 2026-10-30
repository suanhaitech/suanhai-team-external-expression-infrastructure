# 工作流能力

这里存放面向消费端仓库的复合工作流及其 Agent 执行 Harness。

- `WORKFLOW.md` 说明目标、阶段、输入、输出、状态和确认点；
- `ENTRYPOINT.md` 是消费端 Agent 实际读取的执行协议；
- 具体动作优先调用 `tools/`、`templates/`、`skills/` 和 `checks/` 中已在 Manifest 注册的能力；
- 工作流不承载消费端的项目事实、来源文件或最终作品。

工作流通过根 `manifest.yml` 的 `kind: workflow` 注册，并用 `uses` 声明依赖。能力发现不等于用户授权；工作流仍须遵守消费端总 Harness 和实际权限边界。
