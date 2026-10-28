# 消费端 Agent 冒烟测试

> **目标**：验证全新克隆的小组资产仓库能让 Agent 进入正确的项目上下文、发现共享能力并按任务路线工作
> **测试阶段**：历史 v0.1 空 Manifest 骨架的启动回归
> **版本适用性**：下文“能力为空”仅适用于旧骨架；当前任务循环验证使用 [任务循环验证流程](task-loop-validation.md)，以实际 Manifest 为准。HTML 工具仍未实现。

## 测试模式和前提

**立即可运行的只读协议测试**需要：

- 一个消费端资产仓库 clone；
- 已初始化的基础设施 submodule；
- 至少一份项目上下文；
- 可以在资产仓库根目录启动的 Agent。

这一步可以通过明确提示 Agent 读取 Bootstrap 和 Harness 文档来运行，不要求先有任务记录，也不证明 Agent 客户端会自动读取 submodule 文档。

**自动启动测试**还要求消费端根 `AGENTS.md` 已接入 [Bootstrap 协议](consumer-repository-bootstrap.md)。仅仅初始化 submodule、让文档出现在 `vendor/` 下，不视为完成接入。

**完整任务路线和作品测试**还需要一份明确受众、目的、范围、授权来源和输出的任务说明。如果暂时没有任务，Agent 应报告缺少任务并停止生成作品；这是有效的只读测试结果，不需要伪造任务。

## 1. 验证版本和结构

在消费端根目录执行：

```powershell
git submodule update --init --recursive
git submodule status --recursive
Test-Path vendor/suanhai-team-external-expression-infrastructure/manifest.yml
git -C vendor/suanhai-team-external-expression-infrastructure rev-parse HEAD
```

记录父仓库 commit、submodule gitlink commit、Manifest 是否存在以及 submodule 工作区状态。

## 2. 立即运行：只读上下文和能力发现

在消费端根目录启动 Agent，输入：

```text
请先不要制作页面，也不要修改文件。临时按消费端对外表达基础设施的 Bootstrap 和 Harness 协议工作。读取 README.md、AGENTS.md、vendor/suanhai-team-external-expression-infrastructure/manifest.yml、vendor/suanhai-team-external-expression-infrastructure/docs/consumer-repository-bootstrap.md、vendor/suanhai-team-external-expression-infrastructure/docs/consumer-repository-harness-v0.1.md、context/ 和 tasks/。输出当前项目、当前是否存在任务、允许使用的来源、计划输出位置、Manifest 中发现的共享能力、缺失信息和需要真人确认的事项。如果没有任务文件，明确说明并停止作品生成。
```

通过条件：

- Agent 识别消费端仓库根目录为工作目录；
- Agent 按照提示读取 Bootstrap 和 Harness 协议；
- Agent 识别项目身份，并准确说明当前是否存在任务；
- Agent 引用项目上下文和来源登记；
- Agent 说明 `capabilities: []`；
- Agent 在记录中写明“无可用共享能力”和实际 submodule commit，而不是虚构能力 ID；
- Agent 不把计划目录说成已实现能力；
- Agent 不生成项目事实或虚构授权；
- 如果没有任务文件，Agent 停止作品生成。

此项通过只能证明协议可按明确指令执行，不能证明 clone 后会自动激活。

## 3. 验证自动启动接入

仅在消费端根 `AGENTS.md` 已复制 Bootstrap 规则后运行。重新从该仓库根目录启动 Agent，只输入：

```text
请梳理当前仓库中对外表达工作的启动条件、当前任务和可用共享能力；先不要修改文件。
```

通过条件：

- Agent 无需用户再次指定基础设施文档路径，也能报告其遵循的 Bootstrap 和 Harness 规则；
- Agent 能从消费端上下文和 Manifest 得出项目背景与能力清单；
- 若没有任务，Agent 明确停止作品生成；
- 如果 Agent 客户端不自动读取 `AGENTS.md`，记录该客户端需要显式启动提示的限制，不把手动读取结果记为自动启动通过。

## 4. 验证任务路由

输入：

```text
请基于当前任务说明，给出本次对外表达任务的执行路线。只写任务阶段、每阶段的输入和输出、停止条件、评审节点以及最终文件位置。不要执行提交、推送、部署或发布。
```

通过条件：

- 路线包含任务登记、上下文装配、来源核对、作品、工程检查、评审和真人确认；
- 路线区分专业事实评审和发布授权；
- 路线指出没有 HTML 能力时的停止位置；
- 输出路径位于消费端，不写入 submodule。

如果当前没有 `tasks/<task-slug>/task.md`，本节不执行，记录为“等待首个任务登记”；不得根据项目计划自行补造任务。

## 5. 验证能力边界

输入：

```text
请列出当前 submodule Manifest 中可以调用的能力，并说明哪些计划目录不能调用。对于当前任务，如果缺少 HTML 模板、预览工具或检查器，请给出停止或人工接管说明，不要模拟执行结果。
```

通过条件：

- 能力清单为空；
- Agent 说明能力目录存在不等于能力已实现；
- Agent 不调用不存在的命令；
- Agent 给出人工接管或后续实现建议。

## 6. 验证作品和评审承载

在确认任务允许生成草稿后，输入：

```text
请只生成本次 HTML 对外表达作品的信息结构草稿，并说明每个主张对应的来源、事实状态和限制。把待评审问题列成清单，标出需要真人确认的内容和发布授权。不要声称 HTML 已渲染或已发布。
```

通过条件：

- 草稿关联任务和来源；
- 未把阶段性证据写成正式验收；
- 明确待核对内容；
- 没有复制私有来源正文或敏感材料；
- 草稿按消费端约定进入 `works/` 或明确说明待创建路径；
- 评审事项可以进入 `reviews/`。

本节仅在已登记任务、来源授权明确且真人允许生成草稿时执行；否则只记录停止原因，不创建作品。

## 测试记录

每次测试至少记录：

| 字段 | 内容 |
| --- | --- |
| 消费端仓库 commit | 父仓库实际测试版本 |
| submodule commit | 实际使用的基础设施 commit |
| Agent 和运行方式 | 模型、客户端或本地启动方式 |
| 任务路径 | `tasks/<task-slug>/task.md` |
| 测试日期 | `YYYY-MM-DD` |
| 通过项 | 对应步骤和观察结果 |
| 失败项 | 触发输入、实际行为和影响 |
| 人工接管 | 哪些判断需要真人处理 |
| 后续动作 | 修复、补充上下文或实现能力 |

## 判定规则

- 读取顺序错误、Manifest 能力误报、越权读取或虚构授权：测试失败；
- 任务路线完整但工具尚未实现：协议测试通过，能力实现测试未开始；
- 作品结构合理但专业事实或发布授权待确认：允许进入评审，不得标记为可交付；
- 测试失败必须保留记录，不通过删除断言或降低验收要求来修复。
