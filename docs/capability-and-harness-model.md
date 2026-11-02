# Capability、Workflow 与 Harness 分层协议

## 目的

本文件定义基础设施仓库对“能力、工作流、Harness、工具、模板、技能和检查器”的本地术语。它解决一个实际问题：Agent 进入小组资产仓库时，哪些规则约束它，哪些能力可以被调用，哪些程序只执行一个局部动作。

## 总体关系

```text
小组资产仓库总 Harness
        ↓
Agent 读取并路由用户意图
        ↓
Workflow Capability（工作流能力）
        ↓
Workflow Harness（工作流执行协议）
        ↓
Tool / Template / Skill / Check / Context
        ↓
任务状态、文件产出或仓库变更
```

## 术语定义

### 仓库总 Harness

仓库总 Harness 绑定一个具体仓库，约束所有进入该仓库工作的 Agent。它规定读取顺序、目录职责、写入范围、权限边界、确认点、停止条件和留痕规则。

小组资产仓库的总 Harness 位于消费端根目录，通常由 `AGENTS.md`、`README.md` 和消费端自己的任务/评审规则共同组成。基础设施 submodule 中的文档不会自动改变消费端 Agent 的行为，消费端必须显式接入这些规则。

基础设施仓库自己的根 `AGENTS.md` 也是一个总 Harness，但它只约束基础设施仓库自身的维护、验证和发布，不约束所有消费端的全部工作。

### Capability

Capability 是可以被 Agent 发现、选择和调用的能力单元。`manifest.yml` 是共享能力的唯一发现入口。一个 Capability 可以是工具、模板、技能、检查器或工作流。

Manifest 中的 `kind` 描述能力的主要形态：

| `kind` | 含义 | 示例 |
| --- | --- | --- |
| `workflow` | 面向完整目标的复合能力 | `consumer.submodule-update` |
| `tool` | 一个确定、可验证的局部动作 | `consumer.submodule-preflight` |
| `template` | 可复用的文件或页面起点 | `html.project-report-v1` |
| `skill` | 领域知识和操作指导 | HTML 表达技能 |
| `check` | 结果验证能力 | 结构或资源检查器 |
| `harness` | 旧版本兼容类型；新能力不再使用 | 既有消费端旧 Manifest |

能力被发现不等于获得权限。Agent 仍需遵守消费端总 Harness、用户授权和工具自身的副作用边界。

### Workflow

Workflow 是一个面向完整目标的执行单元。它可以组织多个步骤、状态、确认点和停止条件，并调用其他 Capability 完成目标。当前设计不要求人为拆分子工作流；只有在真实复用中出现稳定、独立且需要单独版本治理的阶段时，才考虑新增独立工作流能力。

例如，submodule 更新工作流包括：预检当前状态、选择已验收 commit、展示差异、等待用户确认、在短期分支更新父仓 gitlink、验证并形成可审阅变更。

### Workflow Harness

Workflow Harness 是工作流的 Agent 执行协议。它规定 Agent 每个阶段应该读取什么、询问什么、调用哪些能力、何时停止、如何记录结果以及哪些动作必须等待确认。

工作流与 Harness 的区别是：

```text
Workflow：要完成什么目标和过程
Harness：Agent 如何在边界内执行这个过程
```

`workflows/<workflow>/WORKFLOW.md` 适合描述目标、阶段、输入、输出和状态；`ENTRYPOINT.md` 是 Agent 实际读取的执行入口。简单工作流可以暂时合并为一个入口文件，但语义上仍然区分这两层。

### Tool、Template、Skill 和 Check

- **Tool** 执行确定动作，例如读取 gitlink、检查工作树或写入任务状态。工具不替代用户判断，也不自行决定是否发布。
- **Template** 提供文件或页面结构起点。模板不承载具体项目事实，不负责任务状态和发布授权。
- **Skill** 提供领域知识和操作指导，帮助 Agent 理解表达、材料或技术问题。
- **Check** 验证结果是否满足结构、资源、链接或可复现性要求。通过检查不等于事实正确或获得发布授权。

这些能力不需要各自再嵌套 Harness。只有当它们被组织成一个需要 Agent 按阶段推进的完整目标时，才由工作流 Harness 约束调用。

## 目录与注册约定

```text
AGENTS.md                 基础设施仓库自身总 Harness
manifest.yml              对外 Capability 注册和发现入口
workflows/                可独立触发的完整工作流及其执行入口
  html/production/        HTML 制作工作流
  task-loop/              任务循环工作流
  group-asset-repository-create-and-initialize/
                          创建并初始化小组资产仓工作流
  group-asset-repository-onboarding/
                          消费端身份和项目上下文初始化工作流
  infrastructure-adoption/
                          既有仓库接入基础设施工作流
  submodule-update/       消费端 submodule 受控更新工作流
infrastructure/           工作流消费的可复用资产和领域工具
  html/                   HTML 页面、组件、样式、运行时、Schema、技能和工具
  group-asset-repository/ 小组资产仓模板与初始化工具
  repository-management/  仓库接入和 submodule 管理工具
  task-loop/              任务记录工具
schemas/                  根仓库协议 Schema（当前仅保留 Manifest Schema）
顶层 templates/、skills/、checks/、tools/、harness/ 不再承载可调用能力
```

工作流 Capability 在 Manifest 中使用 `kind: workflow`，入口指向 `workflows/<workflow>/ENTRYPOINT.md`。可选 `uses` 字段列出它依赖的其他已声明 Capability ID；校验脚本会拒绝未声明的依赖。工作流目录的 `WORKFLOW.md` 和 `ENTRYPOINT.md` 可以引用这些依赖，但不会因此把工具或模板变成工作流。能力的真实位置以 Manifest 的 `path` 和 `entrypoint` 为准。

## 当前实例

| 能力 | 形态 | Harness/入口 | 依赖 |
| --- | --- | --- | --- |
| `consumer.group-asset-create-and-initialize` | Workflow Capability | `workflows/group-asset-repository-create-and-initialize/ENTRYPOINT.md` | 建仓并初始化工作流；可转发提示词位于同目录 |
| `consumer.group-asset-onboarding` | Workflow Capability | `workflows/group-asset-repository-onboarding/ENTRYPOINT.md` | 消费端上下文和负责人确认 |
| `expression.task-loop` | Workflow Capability | `workflows/task-loop/ENTRYPOINT.md` | `expression.task-record` |
| `expression.task-record` | Tool Capability | `infrastructure/task-loop/tools/task-record/task_loop.py` | Python 标准库 |
| `expression.html-production` | Workflow Capability | `workflows/html/production/ENTRYPOINT.md` | `expression.task-loop`, `expression.task-record`, HTML 页面模板、语义组件包和按需运行时包 |
| `html.materialize` | Tool Capability | `infrastructure/html/tools/materialize/materialize_html.py` | 固定 submodule、Manifest 中登记的完整预设或容器与有序单页 ID、可选布局/运行时/组件包、已对齐任务 |
| `consumer.submodule-preflight` | Tool Capability | `infrastructure/repository-management/tools/submodule-preflight/submodule_preflight.py` | Git CLI |
| `html.project-report-v1` | Template Capability | `infrastructure/html/templates/presets/project-report-v1/index.html` | 消费端已对齐任务和来源 |
| `html.semantic-components-v1` | Template Capability | `infrastructure/html/components/core-v1/README.md` | 离线样式令牌、布局与六种语义组件 |
| `html.responsive-layout-v1` | Template Capability | `infrastructure/html/styles/responsive-v1/README.md` | 离线响应式、长宽比、方向和打印布局规则 |
| `html.runtime-kit-v1` | Template Capability | `infrastructure/html/runtime-kits/runtime-kit-v1/README.md` | 离线 KaTeX 公式、显示模式、全屏和浏览器保存 PDF 入口 |
| `consumer.submodule-update` | Workflow Capability | `workflows/submodule-update/ENTRYPOINT.md` | `consumer.submodule-preflight` |
| `consumer.infrastructure-adoption` | Workflow Capability | `workflows/infrastructure-adoption/ENTRYPOINT.md` | `consumer.infrastructure-adoption-harness`, `consumer.submodule-preflight` |
| `consumer.infrastructure-adoption-harness` | Tool Capability | `infrastructure/repository-management/tools/infrastructure-adoption-harness/install_harness.py` | 在既有消费端根 `AGENTS.md` 中预览或安装共享长期 Harness |

## 权限和留痕

Harness 是行为协议，不是权限沙箱。关键边界还要由用户确认、Agent 客户端权限、Git 分支/CI 规则和可验证工具共同承担。工作流应遵守：先读后写、显式目标、幂等或拒绝覆盖、保留历史、短期分支、可审阅变更和明确停止原因。

工作流执行的任务记录、项目事实、来源、素材和最终作品留在消费端；基础设施仓只维护可复用协议和能力，不复制消费端业务事实。

## 初始化工作流迁移说明

此前“初始化资产仓库”的能力仍然存在，没有被删除。整体重构后：

- 创建仓库并完成首次初始化的完整工作流位于 `workflows/group-asset-repository-create-and-initialize/`；
- 已有仓库的身份、项目上下文和表达边界初始化工作流位于 `workflows/group-asset-repository-onboarding/`；
- 模板铺设工具位于 `infrastructure/group-asset-repository/tools/bootstrap/`；
- 既有仓库接入基础设施的工作流位于 `workflows/infrastructure-adoption/`；
- submodule 预检和 Harness 安装工具位于 `infrastructure/repository-management/tools/`。

消费端或旧文档如果仍引用迁移前的 `harness/`、顶层 `tools/`、`templates/`、`schemas/`、`skills/` 或 `checks/` 路径，应按 `manifest.yml` 的当前路径更新。不要复制旧目录形成第二套事实源。
