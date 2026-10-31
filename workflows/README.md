# 工作流能力

这里存放面向消费端仓库的复合工作流及其 Agent 执行 Harness。

- `WORKFLOW.md` 说明目标、阶段、输入、输出、状态和确认点；
- `ENTRYPOINT.md` 是通过 Manifest 发现后由消费端 Agent 实际读取的执行协议；
- 需要在目标仓库尚不存在时启动的工作流，可以在同目录提供可转发的提示词；
- 具体动作优先调用 `tools/`、`templates/`、`skills/` 和 `checks/` 中已在 Manifest 注册的能力；
- 工作流不承载消费端的项目事实、来源文件或最终作品。

已有工作流包括任务循环、HTML 网页制作、小组资产仓初始化、从公共模板建仓并初始化、既有仓库接入基础设施，以及已接入 submodule 的受控版本更新。HTML 网页制作工作流是跨消费端目录的协议，先按消费端自身规则登记任务和产物，再使用固定 Manifest 中实际存在的页面模板与组件；当前不提供自动预览、公式引擎或浏览器检查器。面向首次使用者的两份一次性启动提示词也统一放在各自的工作流目录中：新仓提示词在 `group-asset-repository/CREATE_AND_INITIALIZE.md`，既有仓接入提示词在 `infrastructure-adoption/ADOPT_EXISTING_REPOSITORY.md`。`consumer.group-asset-create-and-initialize` 的 Manifest 入口为同目录 `ENTRYPOINT.md`；公共提示词在 submodule 不存在前独立唤起流程，建仓后转交消费端根 `AGENTS.md` 和 onboarding workflow。既有仓库接入会调用 `consumer.infrastructure-adoption-harness` 工具，先展示消费端根 Harness 的准确写入计划，再按提示词授权安装。新建空仓的模板铺设属于独立工具，不等同于既有仓库首次接入。

工作流通过根 `manifest.yml` 的 `kind: workflow` 注册，并用 `uses` 声明依赖。能力发现不等于用户授权；工作流仍须遵守消费端总 Harness 和实际权限边界。
