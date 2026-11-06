# 周期汇报：状态面板与主线展开资产

状态：implemented / experimental。已有4种周期汇报单页、3种组件展示、可选浅绿主题及场景填写规则，配合通用图像分析、依赖、行动和来源页使用。匿名示例不代表真实项目、负责人确认或业务验收。

## 可调用资产

| 能力ID | 页面责任 | 与既有资产的关系 |
| --- | --- | --- |
| html.single-page.content.project-status-v1 | 当前阶段、周期计划、带口径进度和总体判断 | 补充project-overview-v1，保留其上期基线/周期变化用途 |
| html.single-page.content.workstream-research-v1 | 工作对象、本期结果、回答了哪些问题 | 将紧凑workstream-update-v1的部分责任展开 |
| html.single-page.content.conclusion-evidence-v1 | 一个主判断、互补证据入口和限制 | 证据页的展开变体；已有evidence-v1仍保留 |
| html.single-page.content.workstream-plan-v1 | 任务、交付、如何核对及责任前提 | 与会议结尾action-v1用途分开，可独立组合 |

四页均位于`infrastructure/html/templates/single-page/content/`，通过现有容器与html.materialize物料化。每页有supporting可选组件槽；没有填充时不占版面。

核心包1.2.0在index.yml中登记以下展示组件，不增加独立Manifest能力：

| 组件ID | 语义和填写要求 |
| --- | --- |
| status.progress | 沿用status.metric；周期、定义、来源、评估时间明确后才填0至100数值；未知保留文字并隐藏progress |
| evidence.claim-source | 组合claim/source；每项判断有可核对位置与可见限制，核验状态不因链接存在而自动确认 |
| action.plan-table | 沿用next-step；任务、交付与核对方式逐项对应，补责任、期限、前提及确认状态 |

页面内预置相同组件结构并使用data-field标识编辑字段；这些字段不是page-plan的自动填值接口。列表/表格/链接由Agent在物料化后按真实材料编辑，新增条目不受默认数量限制。page-plan.slots继续只接受纯文本，不能把未审阅HTML当作槽值。

## 页面语义与资产落点

| 页面责任 | 已有单页（`html.single-page.` 后缀） | 可配合的组件 |
| --- | --- | --- |
| 封面与阅读路线 | `cover.editorial-v1`、`agenda.route-v1` | `content.summary` |
| 阶段/周期状态或上期变化 | `content.project-status-v1` 或 `content.project-overview-v1` | `status.phase`、`status.metric`、`status.progress` |
| 工作对象、本期结果与回答的问题 | `content.workstream-research-v1`；简短更新用 `content.workstream-update-v1` | `content.summary`、`evidence.observation` |
| 一个判断与多项文字、数字或表格证据 | `content.conclusion-evidence-v1` | `evidence.claim-source`、`evidence.observation`、`evidence.source` |
| 一张图承担主要证明任务 | `content.figure-analysis-v1` | `evidence.figure-analysis`；原图交互复用 image-viewer |
| 任务、交付与核对方式 | `content.workstream-plan-v1` | `action.plan-table`、`action.next-step` |
| 输入输出、跨线影响与协作 | `content.dependencies-v1` | `content.mapping`、`action.next-step` |
| 待确认事项、收尾与下周期结果 | `closing.action-v1` | `action.next-step` |
| 材料版本和使用边界 | `appendix.source-register-v1` | `evidence.source` |

这些是已有资产的选型映射，不是新的固定组合预设。主题与结构分离，不能将某个项目的工作线数量、每线五页、四张证据卡或私有 CSS 固化为全局规则。

## 单结论证据页的填写

证据页按“判断 → 证据 → 解释 → 适用边界 → 下一步影响”组织，标题直接表达可被追问的判断，写清对象和条件。同一个判断可以由多项互补证据支持，不同独立判断应拆页，不为填满卡片凑证据。数字写测量对象、单位、样本/次数、统计方式、比较基线和必要条件；未知口径标明未知，不补造。

`evidence.claim-source` 的一个 article 表示一个判断。物料化后，可在其 `ex-claim-source__evidence` 区内使用原生 `ul/li` 或多个证据段落，每项保留来源 ID、版本、具体定位与支持关系。保留现有首条 `source/locator` 字段，新增条目不要重复声明同名可填槽；内部文本可用 `data-field` 就地编辑。大表或图像优先使用现有表格结构/图像分析页，不把复杂 HTML 塞入 `page-plan.slots`。这复用已有组件，不新增列表字段或状态机。

必要的边界应在正文可见，说明证据允许推出什么、尚未证明什么。来源原文与汇报人的解释分开，建议用以下中性模式核对：

| 合理的阶段判断 | 对应证据与边界 |
| --- | --- |
| 已形成可进入接口评审的设计 | 设计文档包含模块职责、输入输出和异常路径；评审记录仍需核对，不能据此声称已实现或性能达标 |
| 风险触发条件已具体明确 | 在并发更新同一对象时可能产生状态覆盖；依据追踪记录列触发条件、后果、检查步骤及尚未覆盖情形 |
| 构造样例达到程序终止条件，质量仍待独立核对 | 停止日志证明终止条件成立；独立质量报告才支持验收结论，两种指标不能自动等同 |

“设计基线”“单算例实测”“跨模型实测”“待实现验证”“待负责人确认”“建议稿”是内容词汇，不能直接替换组件 `data-state` 的合法枚举。来源状态、判断核验和发布授权分别记录，链接存在或素材哈希正确都不证明结论正确。

## 图像主证据的选型与可读性

多项数字、文字或表格共同支撑判断时优先用 `conclusion-evidence-v1`；一张架构图、曲线、流程图或原图承担主要证明任务时优先用 `figure-analysis-v1`。图像分析页应解释图中事实、汇报人的判断、适用边界和下一步影响；图注写对象、来源版本及原图/摘录/转换方式，衍生图保留原图入口。

主证据图片在默认页面应占主要视觉区域，保持原始比例，能辨认结论所依赖的标注、坐标、图例和数据。放大入口供读细节，不能作为默认小图的唯一补救。依据画布可用高度、图注和边界选择侧排或下排；拥挤时减少冗余、换图或拆页，不裁关键内容，不持续缩字，不套用某一项目的固定像素预算。

完整比例和无溢出只是几何检查。密集竖图在短窗口、横图在分析过长的下排布局中仍可能难读，应人工检查结论依赖的文字；必要时拆页或制作标明来源/转换的重点摘录并保留完整原图，不能将合成尺寸测试写成任意素材的可读性保证。

## 页面计划、备注与来源记录

沿用现有页面计划字段：`core_message` 写主判断/问题，`source_ids` 列本页来源，`notes` 写串场句、关键数字、可能追问及答复来源，`acceptance_signals` 写结构/来源/证据如何核对。必要条件留正文；备注随 HTML 交付并可能投屏可见，不能放机密。模板槽位仍是纯文本，复杂结构在物料化后填写。

三种记录各司其职：来源清单记录材料版本与使用范围；`source-map.json` 按页面/判断记录来源定位及解释性质；`html.source-assets` 登记素材字节、尺寸和衍生关系。source-map 目前是人工流程约定与示例，尚无独立 Schema 或专用自动校验器。不同版本并列登记，不静默合并；转录值和自行计算值写明转换与计算来源。

## 从场景到HTML的选择

场景负责内容责任；HTML工作流负责收集、计划、物料化、检查与反馈；模板和组件提供结构。无需新建平行项目汇报工作流或完整固定套稿。

- 重点为上期对照和里程碑变化：选project-overview-v1。
- 重点为当前阶段、周期计划及完成口径：可选project-status-v1。阶段是项目级归纳，不能与负责人机械一一对应。
- 简短主线更新：保留workstream-update-v1。
- 复杂主线：按“研究主题与进展 → 结论与证据 → 下周期计划”展开，也可合页或拆页。
- 已在各线说明计划且无统筹需求：不再复制整章计划。
- 跨线依赖真实存在且影响目标：继续用dependencies-v1，不能因为删去独立页而丢失重要关系。

周期、工作线数量、问题数、证据条数和总页数由任务决定。主报告即使不打开附件，也应让合作方理解项目状态、重要成果、问题和下一步；细节在获准原件中就近链接，必要限制留在主稿。

## 来源提取表

先读取项目目标、上次会议要求与负责人本期原件，再填写内容计划。建议在消费端任务中复制以下骨架：

| 输入类型 | 需要提取 | 不可混淆的边界 |
| --- | --- | --- |
| 上期会议要求 | 目标、提出方、日期、待回答问题 | 历史要求不等于本期已完成 |
| 本期原件 | 产物、实验条件、结果、定位、版本 | 详细设计不等于实现；个案不等于普遍规律 |
| 补充说明 | 说话人、时间、适用范围、确认状态 | 自评进度不等于技术成熟度 |
| 项目级判断 | 共同目标、阶段归纳、影响及依据 | 判断由主汇报人负责，不自动成为专业核验 |
| 下周期安排 | 任务、交付、核对条件、责任、期限、依赖 | 建议不等于负责人承诺 |

缺失、冲突和过期信息保留待确认与核对人。百分比说明周期、定义、来源、评估人和日期，不由任务数自动推导，不把各线平均成没有依据的项目完成率。

## 主题与兼容

选择`--theme editorial-green`得到浅绿，`--theme editorial-warm`得到暖黄。使用同一结构切换主题；旧模板的硬编码颜色改为主题token并保留原色fallback，未加载颜色令牌时保留原色fallback。语义状态仍有文字，颜色不能代替状态；完整无障碍需独立核验。

[匿名填充预览](../infrastructure/html/examples/project-progress/index.html)提供四种周期汇报页及通用图像证据页，与[四页模板起点计划](../infrastructure/html/examples/project-progress/page-plan.json)、[合成来源](../infrastructure/html/examples/project-progress/source.md)、[人工来源映射示例](../infrastructure/html/examples/project-progress/source-map.json)配套。预览额外图像页用于比较证据形态，不声称源计划直接生成这份已填 HTML；复杂结构需物料化后填写。它不是物料化器替代品，不提供新的导航运行时。单页总目录可选[浅绿预览](../infrastructure/html/templates/single-page/preview/index.html?theme=editorial-green)或[暖黄预览](../infrastructure/html/templates/single-page/preview/index.html?theme=editorial-warm)。预览通过本地HTTP服务打开。

物料化继续先dry-run，再按同一计划摘要apply；普通任务需要固定依赖、已对齐任务和完整页面计划。可参考：

```text
py -3 <固定基础设施>/infrastructure/html/tools/materialize/materialize_html.py --root . --task-id <任务号> --container-id html.container.presentation-deck-v1 --page-plan tasks/<任务号>/page-plan.json --theme editorial-green --scenario-id expression.scenario.project-progress-communication-v1
```

示例计划artifact_kind为template，结构列表保留模板占位以供继续填写；它不声称自动生成完整报告。实际完整报告应按填写协议清理占位并复核来源。

## 版式与验收

- 标题与核心进展同等层级时使用一致字号、字重与左线；章节/工作线标识应便于翻页辨认。
- 列表数量变动时重新检查布局，不强制三栏三行或三条工作线；没有语义对应关系时不暗示逐行对应。
- 桌面演示出现滚动时先减少冗余、调整结构或拆页，不能裁切必要内容；手机可滚动阅读仍需验证末尾可达、无遮挡。保留现有严格检查的真实结果。
- 默认页面中的主图须能读出结论依赖的内容，逐项核对主判断、证据、来源与边界；自动几何检查不能替代视觉或专业核验。
- 全屏期间底部控制栏持续隐藏且不可聚焦，鼠标/触摸下沿不能唤出，画布比例不变，Esc退出后恢复。复用现有容器，不另加全局指针拦截；按[安全区测试](html-presentation-safe-area-test.md)验收。
- 增删重排同步目录、导航、页码、页面计划与来源；检查结果注明当前HTML和有效CSS/JS摘要，旧证据保留历史属性。初次materialization记录不回写为后续定制记录。
- 事实、叙事、审美、几何/交互、手机阅读、打印/PDF和用途授权分别验收；未知/未运行如实记录。

本次不修改共享容器的固定设计画布、不放宽viewport-check门禁，也不自动同步后续手改文件的摘要。封面居中、大编号过渡等其他候选仍留待后续接入。项目专属数据、原始附件及撤回比较页不进入共享资产。

## 实现验证

新增回归用合成内容检查真实组合物料化、重复页面ID隔离、组件契约与包目录、主题对比度及默认未知进度。浏览器可用时检查320/390/768/1366宽度、长标题和1/3/5项，以及打印自然流。工具缺失应报告not-run，不能把静态结果当成视觉或专业验收。

仓库本地受影响测试命令：

```text
py -3 -m unittest discover -s tests -p test_project_report_assets.py -v
```

Manifest由官方Ruby校验和CI核验；PR按现有快速档，集成develop后执行双平台完整回归。最终验证结果以对应提交CI和本次测试输出为准，本文不预写通过结论。

## 后续沉淀的验证门槛

本轮固化规则、已有资产选型、匿名多证据示例及图像可用空间适配，未新增 Schema、Manifest 能力或固定套稿。原有全屏隐藏行为继续由容器及交互回归维护。

后续应在两个不同消费端分别试用“图像主证据”和“多项数据/文字证据”路径，记录固定 SHA、页面计划、素材与来源映射、当前版本检查结果、专业核验/项目叙事评审和重复缺口；合成回归不等于第二个真实消费端。只有两个消费端均证明现有结构无法表达同一需求时，才评估 source-map Schema/校验器、页面计划新字段、新组件或项目经理组合预设。实现入口和旧格式兼容测试完成后才能注册 Manifest。
