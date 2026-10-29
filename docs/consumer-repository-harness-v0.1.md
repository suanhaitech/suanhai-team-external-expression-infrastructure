# 消费端对外表达 Harness v0.1

> **状态**：基础工作协议；可运行的任务循环与状态工具由当前 Manifest 声明，入口见 [任务循环](../harness/task-loop/ENTRYPOINT.md)
> **适用对象**：通过 Git submodule 使用本仓库的小组对外表达资产仓库
> **版本**：v0.1

## 1. 目标

当成员在一个小组对外表达资产仓库的根目录启动 Agent 时，Agent 应能够在一次任务开始前建立三个判断：

1. **我在哪个小组、为哪个项目或小组级工作服务**：从消费端 `context/group/` 理解小组身份与边界，从 `context/projects/README.md` 定位零到多个项目，再读取本次工作涉及的项目目标、场景、协作结构、工作主线、当前状态、来源和表达边界；
2. **这次要完成什么表达任务**：从消费端 `tasks/` 读取受众、目的、范围、输入、完成条件、输出位置和责任信息；
3. **我能调用哪些共享能力**：从 submodule 的 `manifest.yml` 发现已实现能力，并把未列出的目录视为不可调用。

满足这三个判断后，Agent 才能沿着项目约定的路线工作，形成可追溯的任务产出，进入评审，并在真人确认后交付。这里的启动规则必须由消费端根目录的 `AGENTS.md` 显式接入，具体见 [Bootstrap 协议](consumer-repository-bootstrap.md)。

这里的“成为项目对外资产表达专家”是工作目标的简写，实际指 Agent 获得项目上下文、任务路线、共享能力发现协议和停止条件的辅助支持。它不代表 Agent 自动拥有专业判断权、项目责任、客户验收权或发布授权。

## 2. 适用边界

本协议由共享基础设施仓库提供，但项目事实仍由消费端资产仓库和其登记的专业来源承载。

| 层级 | 主要职责 | 事实主位 |
| --- | --- | --- |
| 消费端资产仓库 | 项目上下文、任务、来源、作品、评审和责任记录 | 项目事实和表达资产 |
| 本共享基础设施仓库 | 通用技能、模板、工具、Harness、检查协议和发现规则 | 可复用工程能力 |
| 专业研发仓库或受控来源 | 源码、实验、测试、原始数据和专业技术材料 | 专业证据 |
| SuanhaiOS | 团队任务环境、能力入口和协作支持 | 不替代项目事实主位 |

本协议不创建项目、成员、客户、合同、验收或发布授权数据，也不把消费端的项目资料回流到共享基础设施仓库。

## 3. 消费端必须具备的最小结构

新小组模板采用以下结构；项目索引可以为空，任务和产物目录在有真实需求后才出现具体记录：

```text
consumer-repository/
├── AGENTS.md
├── README.md
├── vendor/<infrastructure>/
│   └── manifest.yml
├── context/
│   ├── README.md
│   ├── initialization.md
│   ├── group/
│   │   ├── identity.md
│   │   ├── sources.md
│   │   └── expression-boundary.md
│   └── projects/
│       ├── README.md
│       ├── _template/
│       └── <project-id>/
│           ├── project-overview.md
│           ├── current-status.md
│           ├── workstreams.md
│           ├── sources.md
│           └── expression-boundary.md
├── topics/
├── tasks/
│   └── <task-slug>/task.md
├── reports/
│   └── <task-id>/v001/
└── reviews/
    └── <work-slug>/review.md
```

其中目录可以由小组调整，但消费端 `AGENTS.md` 必须说明实际映射，并显式接入 [Bootstrap 协议](consumer-repository-bootstrap.md)。`projects/_template/` 是空白表单，不是项目。尚未迁移的单项目消费端可以继续使用 `context/project-overview.md`、`context/current-status.md` 等根路径，并由自己的 `AGENTS.md` 或 `context/README.md` 声明映射；不要求为了兼容读取创建第二份事实。目录存在不表示其中已经有事实、作品或授权记录。仅仅把基础设施作为 submodule 克隆下来，不会自动改变 Agent 的启动行为。

## 4. Agent 激活协议

消费端 Agent 的工作目录必须是资产仓库根目录。消费端根 `AGENTS.md` 需要接入 [Bootstrap 协议](consumer-repository-bootstrap.md)。启动任务时按以下顺序读取：

```text
1. 根 README.md
2. 根 AGENTS.md
3. vendor/<infrastructure>/manifest.yml
4. vendor/<infrastructure>/docs/consumer-repository-bootstrap.md
5. vendor/<infrastructure>/docs/consumer-repository-harness-v0.1.md
6. vendor/<infrastructure>/docs/submodule-consumer-versioning.md 与预检能力入口
7. context/README.md、context/initialization.md 与 context/group/
8. context/projects/README.md（项目索引）
9. 当前 tasks/<任务编号>/task.json（通过 show 读取）及生成的 task.md
10. 任务所属的 context/projects/<project-id>/ 项目上下文
11. task 中登记的直接来源
```

根规则接入后，先运行 Manifest 声明的只读 submodule 预检；不得因为远端有更新而自动切换版本。仅远端网络不可用时，可报告远端未知并通过 `--skip-remote` 复核本地固定版本，本地检查通过后继续；gitlink 漂移、submodule 脏工作区或缺失等错误不能忽略。具体命令和升级、回退路线见 [版本协议](submodule-consumer-versioning.md)。

新空仓尚无首次父仓提交时，按 [新仓建立流程](group-asset-repository-bootstrap.md) 使用模板铺设工具的 dry-run 核对 index gitlink 与 submodule HEAD，然后完成初始化；不为通过日常预检而自动提交。旧仓不存在 `initialization.md` 时遵循自己的初始化映射，不补造历史确认记录。

小组身份或上下文尚未初始化时，先从 Manifest 读取初始化 Harness 入口，按用户已授权范围访谈与核对；不要求此时已有项目或业务任务。已有任务号先 show，再按任务选择相关项目。新需求先登记草案并明确所属项目；小组级任务可以不属于项目。多个项目下不得自行选一个代替用户意图；没有项目时不得补造项目。旧消费端按其映射读取根 `context/` 文件；`project-structured-understanding.md` 如果存在且与当前项目有关，也应读取，但不是新模板必需文件。

读取后，Agent 必须先形成一份工作判断：当前小组、相关项目或小组级工作、任务目标、受众、允许使用的来源、拟输出路径、已发现的共享能力、缺失信息和需要真人确认的事项。它可以保留任务工作记录，不要求提交内部思考全文。

如果消费端没有明确 `task-slug`，只读启动时应报告缺少任务，并停止作品生成，不自行创建任务。用户已经提出真实任务并授权写入时，Agent 可以先登记任务说明；不能根据路线图或测试需要自行补造任务。

## 5. Manifest 能力发现协议

submodule 的 `manifest.yml` 是共享能力的唯一发现入口。

Agent 必须：

1. 读取 `schema_version` 和 `repository`；
2. 确认父仓库 submodule gitlink 是固定 commit；
3. 只把 `capabilities` 中显式列出的能力视为可调用；
4. 校验能力的 `kind`、`path` 和 `entrypoint`；
5. 读取能力入口说明，确认输入、输出、副作用和边界；
6. 在任务或评审记录中保留实际使用的能力 ID 和 submodule commit；如果清单为空，则记录“无可用共享能力”和 submodule commit，不虚构能力 ID。

历史 v0.1 骨架的 `capabilities` 为空。当前版本已注册任务循环、记录工具和 `html.project-report-v1` 离线模板；实际可用项始终以消费端固定提交的 Manifest 为准，不能把占位目录当作 HTML 自动生成、预览或检查器能力。

Manifest 是发现协议，不提供访问控制或执行隔离。消费端必须依赖 Agent 客户端和本机的工具授权边界；运行已声明能力前，仍要阅读其依赖和副作用说明。

## 6. 任务路由

所有对外表达任务都经过同一条主路线：

```text
任务登记
  → 项目上下文装配
  → 受众、目的和授权来源核对
  → 任务分解与表达结构
  → 形成作品初稿
  → 工程检查与事实核对
  → 真人评审
  → 修订
  → 真人确认内容、受众、用途和发布授权
  → 记录交付状态与遗留问题
```

### 6.1 任务登记

任务至少记录：任务名称、所属项目（使用项目索引中的标识；小组级任务注明不适用）、场景、受众、目的、范围、来源、输出位置、完成条件、执行与核对责任、截止时间和限制。任务工具尚无专门字段的信息写入相应记录，不额外编造字段或手改工具事实源。

使用任务循环时，任务目录采用工具产生的编号，`task.json` 是唯一状态事实源，`task.md` 是生成视图；未知项可以先留待澄清。正式制作前对齐关键目标，细节和责任信息逐步记录，不为填齐表格而补造事实。

任务说明不应把“做得好看”作为唯一完成条件，也不应把未确认的技术结论写成已确定内容。

### 6.2 项目上下文装配

Agent 先用 `context/group/identity.md`、`sources.md` 和 `expression-boundary.md` 理解小组定位、通用来源与表达边界，再从项目索引定位任务所属的 `context/projects/<project-id>/`。在该项目目录中，用 `project-overview.md` 理解目标与边界，用 `current-status.md` 理解日期限定的状态，用 `workstreams.md` 判断主线，用 `sources.md` 定位直接事实来源，用 `expression-boundary.md` 判断受众、用途和公开边界。项目额外维护 `project-structured-understanding.md` 时可用于理解对象和关系；旧单项目仓按已声明的根路径映射读取。

小组级任务不强制装配项目上下文。跨项目任务应明确列出相关项目并分别核对来源，不把某个项目的事实提升为全组事实。

上下文摘要帮助定位事实，不能代替直接来源。来源冲突、版本过期、授权缺失或事实状态不足时，Agent 必须降低表达强度或停止等待确认。

### 6.3 作品输出

报告类任务产物按新小组模板进入 `reports/`；系列、课程和书籍仍分别进入 `series/`、`courses/`、`books/`。尚未迁移的旧消费端可以继续使用 `works/`。每个产物应保留任务路径、来源版本、事实状态、适用条件、生成日期、作品状态和待评审问题。作品不是专业事实源，不得复制受限源码、原始数据、受限附件或未经授权的客户资料。

## 7. HTML 任务的首个验证切片

第一个真实消费端验证任务为“大工项目概览与当前进展”HTML。它只验证路线，不预设技术结论或发布授权。

检查点：

1. 任务文件明确外部受众、项目概览和当前进展范围；
2. Agent 能按项目索引或旧仓路径映射，从 `context/` 找到该项目身份、三条主线、当前状态和来源限制；
3. Agent 能识别当前 Manifest 中真实能力，不能调用计划中的 HTML 能力；
4. Agent 能形成 HTML 信息结构草稿，并记录来源和待核对事项；
5. 没有真实模板和预览工具时，Agent 停在待实现或人工生成状态，不伪造执行结果；
6. 报告作品进入 `reports/`（旧消费端可进入 `works/`），评审记录进入 `reviews/`；
7. 真人确认内容和发布授权后，作品才可标记为可交付。

## 8. 停止条件

遇到下列任一情况，Agent 必须停止相关动作，记录原因，并请求真人判断：

- 任务没有受众、目的、输出或完成条件；
- 事实来源不存在、冲突、过期或无法定位；
- 来源没有明确允许当前受众和用途使用；
- Manifest 中没有对应能力，或能力是计划、占位或不可用状态：停止相应共享能力调用，仍可继续只读上下文梳理、缺失分析和人工路线建议；
- 需要复制受限源码、原始数据、凭据、个人信息或内部网络信息；
- 技术观察需要被写成正式验收、客户承诺或普遍结论；
- 提交、推送、部署、发布或发送外部消息缺少相应授权；已有用户授权在其范围内继续有效，不因进入后续阶段而重复请求；
- 任务范围、责任主体或项目目标存在未解决冲突。

停止不是失败状态。停止记录应包含已完成的读取、缺少的输入、影响范围和下一步需要谁确认。

## 9. 评审和收口

评审至少分为三类：

| 评审类型 | 判断内容 | 不能替代 |
| --- | --- | --- |
| 工程检查 | 文件结构、链接、资源、渲染和可复现命令 | 内容事实正确性和发布授权 |
| 专业事实评审 | 技术主张、来源、适用条件和限制 | 对外发布许可 |
| 表达与发布评审 | 受众理解、表达质量、披露范围和用途授权 | 专业技术验收 |

评审记录进入消费端 `reviews/<work-slug>/`，至少记录版本、意见、处理结果、未解决问题、核对人和授权状态。Agent 可以生成清单、发现证据缺口和执行修订，但不能填写虚假的真人确认。

## 10. 版本和升级

消费端 submodule gitlink 是实际使用版本的唯一事实来源。启动时只读预检版本关系，远端更新只作提示。升级时按 [消费端 submodule 版本协议](submodule-consumer-versioning.md) 从消费端 `develop` 创建短期分支，更新到明确 commit，运行 Manifest 校验和冒烟测试，用真实任务试用，记录兼容性问题，再决定是否合并消费端的 `develop` 或 `main`。已有用户授权在其范围内继续有效。

共享基础设施变更也必须经过短期分支、Manifest 校验和消费端验证。消费端不能自动跟随 submodule 浮动分支。

## 11. v0.1 验收口径

在一个全新 clone 的消费端完成以下事项，即通过消费端协议验收：

1. 初始化 submodule，并确认 gitlink commit；
2. Agent 按规定顺序读取根规则、Manifest、项目上下文和任务说明；
3. Agent 输出项目、任务、受众、来源和边界的工作判断；
4. Agent 列出当前固定提交的 Manifest 能力，不把计划目录当作已实现能力；
5. Agent 拒绝调用计划中的 HTML 工具并说明原因；
6. Agent 生成 HTML 作品结构草稿或待实现说明；
7. Agent 把作品、来源和评审记录放到消费端规定目录；
8. Agent 指出需要真人确认的技术判断和发布授权；
9. Git 检查不包含凭据、缓存、构建产物或 submodule 内容复制。

这套验收证明消费端发现协议和项目工作路线可执行，不证明 HTML 工具、模板、预览器或检查器已经实现。

## 12. 后续实现顺序

1. 用本协议执行大工项目真实任务，记录 Agent 是否按路线工作；
2. 提取跨项目通用的任务字段和停止条件；
3. 实现 `html.external-expression` 技能的真实入口；
4. 实现 HTML 模板、预览工具和确定性检查器；
5. 通过 Manifest 暴露已经验证的能力；
6. 在消费端固定新的 submodule commit，再重复端到端验证。

本文件不是后台执行器。只有真实入口、说明、验证和 Manifest 同步完成后，Agent 才能把具体能力视为可用；当前任务循环的验收与旧骨架启动测试分开记录。
