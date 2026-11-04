# 首版架构边界

## 仓库关系

本仓库是共享能力仓库。未来的小组对外表达资产仓库是父仓库，通过 Git submodule 固定本仓库的具体 commit：

```text
小组资产仓库
└── vendor/suanhai-team-external-expression-infrastructure
    └── 固定 commit 的共享能力
```

父仓库的 gitlink 是实际使用版本的唯一事实来源。分支名和标签只用于开发、识别和保留提交，不能替代 gitlink。

## 能力分层

- **skill**：告诉 Agent 如何理解表达任务、组织步骤和处理边界；
- **template**：提供 HTML 页面或组件的结构起点；
- **tool**：执行渲染、预览、转换、素材处理或确定性检查；
- **workflow**：面向一个完整目标的复合能力，组织多个阶段、状态和确认点；
- **harness**：约束 Agent 如何执行一个工作流，包括输入、工作目录、工具调用、停止条件和输出协议；它是工作流的执行机制，不是独立的业务目标；
- **check**：验证结构、资源、链接或渲染结果。

Manifest 只列出已经实现并可被消费端使用的能力。工作流用 `kind: workflow` 注册，并通过可选的 `uses` 列出依赖的能力 ID；新工作流入口通常是 `workflows/<workflow>/ENTRYPOINT.md`。为兼容既有消费端，`kind: harness` 仍被 Schema 接受，但新能力不再使用它。计划能力写在路线文档和对应目录的 README 中，不进入清单。

## 场景、工作流与基础设施

场景、工作流和基础设施是三个不同的设计维度：

- **场景**说明实践/认知对象、受众、希望受众发生的变化、内容路径和成功标准；它回答“为什么做、为谁做、结果如何才有价值”。
- **工作流**组织 Agent 为完成目标需要经历的步骤、确认点和停止条件；它回答“怎样把任务安全地做完”。
- **基础设施**提供可以被工作流复用的页面模板、组件、样式、运行时、工具和检查协议；它回答“执行时有哪些可复用资产”。

因此，场景可以复用同一工作流，一个工作流也可以承载多个场景；场景不会因位于一个目录就成为可执行能力，也不进入 `manifest.yml`。当前 HTML 场景画像位于 `scenarios/`，由 `expression.html-production` 显式读取；场景选择会记录在 HTML 作品的 `report.yml` 和 `materialization.json`，不改变用户事实所在的消费端边界。

## Harness 的绑定关系

本仓库存在两层 Harness：

1. 根 `AGENTS.md` 是基础设施仓库自身的总 Harness，约束维护 Agent 如何修改、验证和发布共享能力；
2. 工作流目录下的入口是消费端工作流 Harness，约束小组资产仓中的 Agent 如何执行某一个已发现的 Workflow Capability。当前工作流入口统一位于 `workflows/<workflow>/ENTRYPOINT.md`。

工作流不是 Harness 的同义词。工作流描述“要完成什么完整目标”，Harness 描述“Agent 如何在边界内完成它”；工作流再调用 `infrastructure/<领域>/` 中的工具、模板、技能和检查协议。能力发现通过 Manifest 完成，能力发现本身不授予 Git 或外部系统权限。

## 消费端工作层

一个小组资产仓库同时使用两类入口：

- **项目工作入口**：消费端自己的 `AGENTS.md`、`context/`、`tasks/`、`topics/`、`reports/`、`series/`、`courses/`、`books/`、`tools/` 和 `reviews/`，解释小组与项目事实、任务、来源、报告资产和评审；旧消费端的 `works/` 仍由任务工具兼容；
- **共享能力入口**：本仓库 submodule 中的 `manifest.yml`，只声明已经实现、可验证和可调用的能力。

消费端 Harness 把两类入口连接成任务路线，但不把项目事实复制到共享仓库，也不把计划目录提升成能力。消费端必须在根 `AGENTS.md` 显式接入 [Bootstrap 协议](consumer-repository-bootstrap.md)，否则 submodule 中的文档不会自动改变 Agent 行为。完整协议和冒烟测试见 [消费端对外表达 Harness v0.1](consumer-repository-harness-v0.1.md) 和 [消费端 Agent 冒烟测试](consumer-repository-smoke-test.md)。

新组通过公开的 GitHub 模板仓 `suanhaitech/suanhai-team-group-asset-template` 创建独立资产仓，再递归克隆。发布的模板仓已配置基础设施 submodule 和固定 gitlink；成员不需要先克隆基础设施或手工铺设文件。具体操作见 [新机器初始化流程](group-asset-repository-bootstrap.md)。共享能力分为三个相关部分：`scenarios/` 放任务画像，`workflows/` 放可独立触发的工作流，`infrastructure/<领域>/` 放工作流可复用的模板、工具、运行资源、Schema、技能和检查协议。HTML 页面资产位于 `infrastructure/html/templates/`，其中 `containers/` 保存阅读容器，`single-page/` 保存可组合单页，`presets/` 保存完整组合预设；小组资产仓库模板源位于 `infrastructure/group-asset-repository/templates/`。

如果组长希望 Agent 代办建仓和本地克隆，使用 `workflows/` 下自包含的[创建与初始化提示词](../workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md)。它是一次性工作流启动入口，不是消费端长期 Harness；在 submodule 尚不存在时即可单独分享。建仓、递归克隆和固定依赖核验后，Agent 再读取新仓根规则并调用消费端初始化工作流。创建目标仓、初始化本地上下文、负责人确认和远程推送是不同边界，不能把前一步授权延伸成后续全部授权。

已经有自己仓库、但不想采用公共模板的团队，可使用[既有仓库接入提示词](../workflows/infrastructure-adoption/ADOPT_EXISTING_REPOSITORY.md)。这是一段一次性的启动入口：它授权 Agent 审计仓库后接入固定 commit 的 submodule，并调用 Manifest 注册的 `consumer.infrastructure-adoption-harness` 预览校验后安装根 `AGENTS.md` 规则。提示词授权后无需二次确认；若 submodule 已正确接入，则不重复添加，但仍核对和补装缺失的根 Harness。工具只追加带标记的 Harness，不覆盖本仓规则，也不复制公共模板目录；遇到冲突时停止。接入完成后由消费端 Harness 持续路由固定 Manifest 能力；只要 Agent 客户端会读取根 `AGENTS.md` 且 submodule 已初始化，后续任务就不需重复这段提示词。升级仍通过独立的 submodule 更新工作流显式进行。

模板源文件保存在本仓 `infrastructure/group-asset-repository/templates/group-asset-repository-v1/`，源目录本身不嵌套自身 submodule；维护者将其发布到独立模板仓时配置依赖。铺设工具是维护者从空仓建模版和工具回归的备用入口，只复制空结构，不承担现有仓库自动迁移。小组初始化工作流引导当前使用者区分小组身份与项目事实、保留来源与确认依据。小组上下文位于 `context/group/`，零到多个项目位于 `context/projects/`；初始化进度保存在 `context/initialization.md`。

## 任务循环与恢复

当前 [任务循环入口](../workflows/task-loop/ENTRYPOINT.md) 由 Manifest 发现；配套 Python 工具位于 `infrastructure/task-loop/tools/task-record/`，以消费端 `tasks/<编号>/task.json` 为唯一任务事实源并生成 `task.md` 阅读视图。状态、共识记录、反馈、产出摘要和下一步留在消费端；共享仓只维护通用协议与工具。

HTML 网页制作由 [`expression.html-production`](../workflows/html/production/ENTRYPOINT.md) 组织需求澄清、来源登记、页面模板和组件选择、版本化产物、运行时装配、响应式检查、可选 PDF 导出、用户反馈及人工收口。Agent 可使用 [`html.materialize`](../infrastructure/html/tools/materialize/README.md) 将已登记资产安全复制到消费端已对齐任务目录，并记录固定 submodule commit 和文件哈希；工作流要求先预览计划，再应用同一摘要的计划。`html.runtime-kit-v1` 提供完全离线的 KaTeX 公式、显示模式、全屏和浏览器保存 PDF 入口；`html.viewport-check` 和 `html.pdf-export` 的浏览器部分仍依赖消费端本机运行时，完整自动化无障碍检查尚未实现。

HTML 主工作流当前读取 [`scenarios/`](../scenarios/README.md) 中的“课程学习”和“面向合作方的项目进展沟通”画像。课程通常归档到消费端 `courses/`，项目进展沟通通常归档到 `reports/`；HTML、PDF、长页与逐页演示是交付形式或容器，不是场景。

项目周期汇报在现有画像中组织项目经理的总体判断、主线证据与跨线影响；工作流负责来源和核验记录，页面通过项目总览、可重复主线更新、跨线依赖三个正文变体组合，不另设一套工作流或固定整套预设。项目事实与具体责任人仍留在消费端，设计依据见 [项目总汇报设计](project-progress-report-design.md)。

用户协作循环负责目标和版本确认，Agent 内部循环负责授权范围内的制作与检查。状态工具不运行 Agent、不提供 HTML 生成或浏览器预览，也无法证明用户身份或发布权限。跨设备恢复依赖父仓文件同步与准确 submodule gitlink，不由任务编号自动完成。

## 责任边界

### 小组资产仓：实践记忆与工作现场

小组资产仓由小组维护，记录其实际实践和责任关系，包括小组/项目上下文、来源、已形成的认识与表达边界、任务状态、作品、评审和授权。`topics/` 可以保存经过来源和状态管理、在本组多次使用的内容资产。它们即使可复用，也仍由本组对其事实、适用范围和更新负责。

### 基础设施仓：跨组可复用的方法与执行能力

基础设施仓由基础设施维护者维护，提供多个小组可采用的通用方法和执行能力，包括场景画像、工作流、数据协议、模板、工具、运行资源和检查规则。它可以保存从实践中提炼出的抽象模式，但必须说明适用范围与限制，且不能依赖或携带某个小组的未公开事实。基础设施仓不是小组认知的权威副本，也不负责确认具体项目事实、专业结论、来源许可或发布授权。

### 归属判定

遇到边界模糊的材料，依次判断：

1. 如果材料过时或有误，应该由谁负责核对和修正？小组/项目负责人负责的事实、结论、来源和口径留在消费端；基础设施维护者负责的通用协议和能力放在基础设施仓。
2. 复用范围是一个小组，还是多个小组？本组多次使用的内容进入消费端 `topics/`；跨组可复用的抽象模式才考虑进入基础设施仓。
3. 抽象后是否仍需读取某个具体项目的事实才能理解或执行？若是，说明它尚未成为独立的通用资产，应留在消费端，或先补充抽象边界后再评估。

具体作品和评审记录留在消费端；基础设施可以保留不含项目事实的通用样例、模板和验证协议。两边可以分别保存具体实例和抽象模式，但要避免复制同一份事实并形成双重维护。Agent 可以执行工具，但不因此成为专业判断或对外发布的责任主体。

消费端根 `AGENTS.md` 是本地治理规则，定义该仓事实来源、目录职责、责任人、权限和长期启动方式；基础设施的 workflow `ENTRYPOINT.md` 是某项通用能力的执行协议，定义该能力的步骤、输入输出和停止条件。两者约束范围不同：工作流不能覆盖消费端事实和治理规则，消费端 Harness 也不需要复制每个工作流的完整执行细节。

## 首版不做的事情

- 远程插件市场和动态能力注册；
- 多 Agent 编排平台；
- 自动 Git 提交、推送、部署或发布；
- 统一审批状态机；
- 项目、科研、客户和成员数据存储；
- 对小组资产仓库的强制模板和内容同步。

新 HTML 任务默认采用分页组合（`html.container.presentation-deck-v1` + `page-plan.json` + `html.single-page.*`），服务现场逐页讲解。用户明确要求连续阅读、传阅或查阅时采用长页；既有长页保持兼容。容器选择与空白模板/完整报告是独立维度；Agent 主动推荐资产，记录候选与选用资产、定制理由和验收信号。

HTML 交互组件与单页模板分别维护，物料化器默认装配工具栏/公式和原图阅读器；分页容器负责组合控件，运行时负责动作。默认集合是明确列举的已注册能力，新增组件必须先实现、验证再增量加入。详见 [交互组件边界](html-interaction-components.md)。
