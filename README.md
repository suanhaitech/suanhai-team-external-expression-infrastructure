# Suanhai 团队对外表达基础设施

这是 `suanhaitech` 组织下的共享工程仓库，为 Suanhai 团队的科研小组和项目小组提供可复用的对外表达能力。

当前提供可发现的任务循环、任务状态工具、长页 HTML 项目汇报和多页 HTML 演示稿模板、语义组件包、响应式布局包和离线页面运行时包，以及按 Manifest 能力 ID 将它们安全复制到消费端任务目录的物料化工具。演示稿模板提供底部翻页、键盘导航、比例选择、讲者备注和逐页打印；默认运行时包随页面复制 KaTeX、字体和工具栏脚本，提供公式渲染、显示模式切换、全屏和浏览器保存 PDF 入口。仓库还提供小组资产仓库模板，以及多条消费端工作流：HTML 网页制作、小组初始化、从公共模板建仓并初始化、既有仓库首次接入基础设施、已接入 submodule 的受控更新。工作流集中在 `workflows/`，全部可复用模板、工具和领域资源集中在 `infrastructure/<领域>/`；office 文档和演示文稿等非 HTML 形式尚未实现。小组模板支持零到多个项目上下文；初始化工具只铺设空白骨架并拒绝覆盖，Agent 需通过访谈与负责人核对上下文。多视口检查和确定性 PDF 导出已提供，但依赖消费端本机浏览器运行时；完整自动化无障碍检查仍未实现。

本仓库另外提供可直接转发的一次性启动提示词：一类用于从 GitHub 公共模板建仓、递归克隆并初始化；另一类用于将基础设施首次接入既有仓库并安装消费端 Harness。前者适合新仓，后者适合保留既有结构的仓库；两者完成后，日常能力路由均依靠消费端根规则和固定 submodule Manifest。

本仓库自身由根 `AGENTS.md` 约束；对消费端提供的工作流以 Capability 形式注册在 `manifest.yml` 中。工作流是面向一个完整目标的复合能力，其 `ENTRYPOINT.md` 约束 Agent 如何执行；工作流调用的模板、工具、运行资源、技能和检查协议按领域放在 `infrastructure/<领域>/`。目录分组不代表需要继续拆成子工作流。

表达任务的场景画像位于 [`scenarios/catalog.json`](scenarios/catalog.json)，目前包括“课程学习”和“面向合作方的项目进展沟通”。场景决定受众变化目标、内容组织和验收重点；HTML、PDF、长页和逐页演示属于交付形式或阅读容器，不是场景能力。

项目进展场景支持项目经理统一主讲：先给总体判断和周期变化，再用可重复主线页解释证据与限制，最后说明跨线影响、协作请求和下周期结果。总览、主线更新、跨线协作三种正文页与既有封面/行动/来源页自由组合，详见 [项目总汇报设计与试用](docs/project-progress-report-design.md)。

CI 采用快速与完整两档：普通 develop PR 快速反馈，功能提交集成后双平台全量；说明文档与发布候选按各自范围验证。消费端切换已固定版本不重跑基础设施全量，升级检查已有提交验证与自身接入。规则和本地命令见 [CI 与消费端验证](docs/ci-validation.md)。

## 仓库职责

本仓库承载可以被多个小组复用的实践方法与工程能力。它回答“怎样帮助一个小组理解实践、组织表达并检查交付”，不替任何小组保存或确认具体认知：

- Agent 使用的技能说明；
- `workflows/` 中面向完整目标的工作流及其执行协议；
- `infrastructure/` 中按领域组织的可复用页面资产、运行时和专用工具；
- `infrastructure/<领域>/` 中的可复用资产、工具、技能和检查协议；
- 各工作流入口中约束 Agent 输入、工作目录、检查点和输出的 Harness；
- 能被父仓库以 Git submodule 固定版本引用的文件协议。

小组资产仓是该小组的实践记忆和工作现场，负责保存小组与项目事实、来源、已形成的认识与表达边界、任务过程、作品、评审和授权。小组可以把本组反复使用的概念说明、问答或方法总结保存到自己的 `topics/`；“在本组可复用”不等于“适合进入共享基础设施”。

一项内容只有在从具体项目和小组事实中抽象出来、适用范围与限制说得清楚，并且能独立服务多个小组时，才考虑沉淀到本仓库。沉淀的是通用模式、协议或能力，不是原始项目材料或小组结论；基础设施仓不得成为事实的权威来源，也不得替消费端确认事实、专业判断或发布授权。

归属判断可看维护责任：错误或过期时应由某个小组/项目负责人修正的内容，放在该小组资产仓；需要由基础设施维护者维护、且修改能服务多个小组的通用方法或能力，放在本仓库。两边可以分别保留具体实例和抽象模式，但不应复制同一份事实并形成双重维护。

## Agent 发现入口

Agent 从仓库根目录的 `manifest.yml` 发现已实现能力：

| ID | 类型 | 作用 |
| --- | --- | --- |
| `expression.task-loop` | workflow | 由消费端 Agent 执行的任务协作循环，使用任务记录工具 |
| `expression.task-record` | tool | Python 标准库工具，管理任务文件、状态及产出摘要 |
| `html.project-report-v1` | template | 网页形式下，离线项目概览、阶段进展和对外汇报 HTML/CSS 页面模板 |
| `html.presentation-deck-v1` | template | 网页形式下，离线多页演示稿模板，带底部翻页、比例选择、讲者备注和逐页打印 |
| `html.container.presentation-deck-v1` | template | 逐页演示稿容器；可按顺序组合 `html.single-page.*` 页面 |
| `html.semantic-components-v1` | template | 离线设计令牌、基础排版布局和已登记的语义 HTML 组件契约 |
| `html.runtime-kit-v1` | template | 网页形式下，离线 KaTeX 公式、显示模式切换、全屏和浏览器保存 PDF 运行时包 |
| `html.materialize` | tool | 复制完整页面预设，或按容器和有序单页能力组合页面；记录来源 commit 与文件哈希 |
| `html.responsive-layout-v1` | template | 网页内部可复用的响应式布局、长宽比、方向、打印和安全溢出 CSS 规则 |
| `html.viewport-check` | tool | 检查本地资源、viewport 元标签和多视口水平溢出，可选生成截图 |
| `html.pdf-export` | tool | 使用本机 Chrome、Edge 或 Chromium 将自包含 HTML 导出为 PDF，并记录环境和哈希 |
| `expression.html-production` | workflow | 跨消费端组织任务、来源、页面模板组件、迭代和人工收口的 HTML 网页制作流程 |
| `consumer.submodule-preflight` | tool | 只读核对消费端 submodule 的固定 gitlink、工作区和远端稳定分支快照 |
| `consumer.group-asset-bootstrap` | tool | 在已固定 submodule 的消费端安全铺设小组资产仓模板 |
| `consumer.group-asset-onboarding` | workflow | 引导负责人确认小组身份、多项目上下文、来源和边界 |
| `consumer.group-asset-create-and-initialize` | workflow | 可转发启动提示词：从 GitHub 模版创建、递归克隆、核验固定依赖，再转交仓内初始化 |
| `consumer.submodule-update` | workflow | 在用户确认和短期分支中受控更新消费端 submodule gitlink |
| `consumer.infrastructure-adoption` | workflow | 为不采用公共模板的既有仓库接入固定版本 submodule，并增补消费端根 Agent Harness |
| `consumer.infrastructure-adoption-harness` | tool | 预览并幂等安装消费端根 `AGENTS.md` Harness；默认只读，接入工作流授权后显式应用 |

目录中标记为 `planned / not implemented` 的能力不能被当作可调用入口。新增能力前必须先实现入口、补充说明、通过检查，再更新 Manifest。`workflow` 能力的 `uses` 字段列出它依赖的其他已声明能力；Manifest 校验会拒绝未声明的依赖。

## 消费端 Harness

通过 submodule 使用本仓库的小组资产仓库，应把自己的 `AGENTS.md`、`context/group/`、`context/projects/`、`tasks/`、`topics/`、`reports/`、`series/`、`courses/`、`books/`、`tools/` 和 `reviews/` 作为工作入口，把本仓库的 `manifest.yml` 作为共享能力入口。小组模板默认用 `reports/` 承载报告类任务产物；未迁移的消费端 `works/` 仍被任务工具兼容。消费端 Agent 的启动接入、初始化访谈、读取顺序、任务路线、停止条件和冒烟测试见：

- [消费端 Agent Bootstrap 协议](docs/consumer-repository-bootstrap.md)
- [消费端对外表达 Harness v0.1](docs/consumer-repository-harness-v0.1.md)
- [消费端 submodule 版本协议](docs/submodule-consumer-versioning.md)
- [来源与作品原始字节保护](infrastructure/repository-management/tools/asset-bytes/README.md)
- [消费端 Agent 冒烟测试](docs/consumer-repository-smoke-test.md)
- [任务循环入口](workflows/task-loop/ENTRYPOINT.md)
- [HTML 网页制作工作流入口](workflows/html/production/ENTRYPOINT.md)
- [HTML 网页制作工作流协议](workflows/html/production/WORKFLOW.md)
- [HTML 可复用基础设施框架](docs/html-framework.md)
- [HTML 模板资产层级](infrastructure/html/templates/README.md)
- [多页 HTML 演示稿设计与样例提炼](docs/html-presentation-deck-design.md)
- [多页 HTML 演示稿模板](infrastructure/html/templates/presets/presentation-deck-v1/README.md)
- [HTML 语义组件核心包 v1](infrastructure/html/components/core-v1/README.md)
- [HTML 模板与组件物料化工具](infrastructure/html/tools/materialize/README.md)
- [HTML 响应式布局包](infrastructure/html/styles/responsive-v1/README.md)
- [HTML 多视口检查工具](infrastructure/html/tools/viewport-check/README.md)
- [HTML PDF 导出工具](infrastructure/html/tools/pdf-export/README.md)
- [HTML 消费端端到端测试流程](docs/html-e2e-consumer-test.md)
- [可直接转发的 HTML 端到端测试提示词](docs/html-e2e-consumer-test-prompt.md)
- [可直接转发的 HTML 制作启动提示词](workflows/html/production/START_HTML_PRODUCTION.md)
- [HTML 基础设施稳定发布与消费端迁移说明](docs/html-infrastructure-stable-release.md)
- [小组资产仓初始化工作流](workflows/group-asset-repository-onboarding/ENTRYPOINT.md)
- [小组资产仓模板源](infrastructure/group-asset-repository/templates/group-asset-repository-v1/README.md)
- [小组资产仓模板铺设工具](infrastructure/group-asset-repository/tools/bootstrap/README.md)

## 工作流与可转发启动提示词

- [小组资产仓创建与初始化提示词](workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md)：从公共模板创建新仓，随后调用消费端初始化流程；
- [既有仓库接入基础设施提示词](workflows/infrastructure-adoption/ADOPT_EXISTING_REPOSITORY.md)：为现有仓库固定接入 submodule 并安装消费端根 Harness；
- [既有仓库接入工作流入口](workflows/infrastructure-adoption/ENTRYPOINT.md)；
- [小组资产仓从 GitHub 模板到新机器初始化](docs/group-asset-repository-bootstrap.md)
- [小组资产仓代建与初始化流程](docs/group-asset-repository-create-and-initialize.md)
- [小组资产仓模板验证与发布记录](docs/group-asset-template-validation.md)
- [任务循环验证与换 Agent 续作](docs/task-loop-validation.md)
- [Capability、Workflow 与 Harness 分层协议](docs/capability-and-harness-model.md)
- [submodule 更新工作流](workflows/submodule-update/ENTRYPOINT.md)

公共模板用于全新小组仓；已有仓库不需要迁移目录结构，可直接使用既有仓库接入提示词。接入工作流调用 `consumer.infrastructure-adoption-harness` 预览消费端根 `AGENTS.md` 的增补内容，预览、校验后直接安装。接入后，消费端根 AGENTS.md 承担长期 Harness，父仓 gitlink 固定共享基础设施版本；只要 submodule 已初始化且 Agent 客户端读取该文件，用户日常工作就不再重复发送初次提示词。客户端不读取时需要从它支持的指令入口显式引用；这不是后台自动执行。

Bootstrap 必须由消费端显式写入根 `AGENTS.md` 才会生效；文档存在于 submodule 中不会自动改变 Agent 行为。Agent 按消费端固定提交中的 Manifest 发现 workflow 和局部工具、模板等能力，再读取依赖入口并遵守用户授权；这些能力不是后台执行器或权限沙箱。

## 开发和版本

- `main`：稳定、可被 submodule 固定引用的版本；
- `develop`：日常集成分支；
- `codex/*`：从 `develop` 创建的短期开发分支，任务合入并通过最终检查后应按仓库 Harness 清理本次分支及安全可移除的 worktree；不顺手批量删除无关历史分支。

当前仓库由 Chaos 全权维护。开发过程中不自动提交、推送、部署或发布；GitHub Actions 校验 Manifest，并在 Windows 与 Linux 运行任务循环、submodule 预检和模板铺设行为测试。

## 本地检查

需要 Ruby 3.3 或更高版本：

```text
ruby scripts/validate_manifest.rb
```

校验脚本只使用 Ruby 标准库，不需要安装仓库级依赖。完整 CI 由 `.github/workflows/validate-manifest.yml` 执行。

任务循环需要 Python 3.10+，仅使用标准库：

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

## 当前阶段边界

HTML 网页制作工作流、语义组件包、响应式样式包、离线运行时包、模板/组件安全物料化工具、多视口检查和 PDF 导出目前为 `implemented / experimental`：它们分别提供页面制作编排、语义结构、可复用布局、页面内公式/显示/全屏/浏览器保存 PDF 能力、资产复制、静态/可选浏览器检查和本地 PDF 输出。浏览器检查和 PDF 导出依赖消费端本机运行时；运行时包缺少浏览器时不能声称交互或视觉检查通过，完整自动化无障碍检查仍未实现。

桌面演示稿使用全屏时会保留进入前的页面比例并整体放大；底部工具栏默认收起，指针移至下沿或键盘焦点进入后显示，并为工具栏预留安全间距。消费端已物料化的旧页面需重新选择最新模板/容器并生成新版本，submodule 更新不会自动改写复制出来的 CSS/JavaScript。

## 课程实践沉淀的新资产

开发版新增7种单页、5个语义组件、公共页框与可选暖白主题、原图阅读器；既有目录/过渡/方法页增强。HTML物料化支持完整页面清单、稳定ID、具名组件插槽、多布局/运行时与受控局部修订。整稿检查支持本机CDP、逐页交互、截图联系表和版本并排；素材登记与字节保护分别提供独立工具。课程画像、HTML主流程、启动和接入提示词同步维护。

全部30项的归属和边界见 [课程资产提炼](docs/course-reusable-assets.md)，实际选择以固定提交的Manifest为准。新资源是开发版可复用工程资产，教学有效性、专业内容和发布仍需消费端评审；现有消费端不会自动升级。

新 HTML 任务默认采用分页组合（`html.container.presentation-deck-v1` + `page-plan.json` + `html.single-page.*`），服务现场逐页讲解。用户明确要求连续阅读、传阅或查阅时采用长页；既有长页保持兼容。容器选择与空白模板/完整报告是独立维度；Agent 主动推荐资产，记录候选与选用资产、定制理由和验收信号。

交互组件现已统一控制栏与原图缩放体验，新任务默认配齐。参见 [交互组件与验收边界](docs/html-interaction-components.md)，或打开 [交互体验页](infrastructure/html/runtime-kits/preview/index.html)。

## 周期汇报展开资产

新增状态面板、研究主题与进展、当前结论与证据、下周期计划4种单页，及进度/证据/计划3种组件展示与可选浅绿主题。场景负责内容选择，HTML工作流负责制作与核验，页数和周期由消费端任务决定。固定设计画布仍未在本次正式化。可调用入口、匿名预览和填写边界见[周期汇报可复用资产](docs/project-report-reusable-assets.md)。
