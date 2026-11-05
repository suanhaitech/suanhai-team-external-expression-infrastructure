# 周期汇报：状态面板与主线展开资产

状态：implemented / experimental。本次接入4种单页、3种组件展示、浅绿主题及场景填写规则。匿名示例不代表真实项目、负责人确认或业务验收。

## 可调用资产

| 能力ID | 页面责任 | 与既有资产的关系 |
| --- | --- | --- |
| html.single-page.content.project-status-v1 | 当前阶段、周期计划、带口径进度和总体判断 | 补充project-overview-v1，保留其上期基线/周期变化用途 |
| html.single-page.content.workstream-research-v1 | 工作对象、本期结果、回答了哪些问题 | 将紧凑workstream-update-v1的部分责任展开 |
| html.single-page.content.conclusion-evidence-v1 | 逐条判断、证据入口和限制 | 证据页的展开变体；已有evidence-v1仍保留 |
| html.single-page.content.workstream-plan-v1 | 任务、交付、如何核对及责任前提 | 与会议结尾action-v1用途分开，可独立组合 |

四页均位于`infrastructure/html/templates/single-page/content/`，通过现有容器与html.materialize物料化。每页有supporting可选组件槽；没有填充时不占版面。

核心包1.2.0在index.yml中登记以下展示组件，不增加独立Manifest能力：

| 组件ID | 语义和填写要求 |
| --- | --- |
| status.progress | 沿用status.metric；周期、定义、来源、评估时间明确后才填0至100数值；未知保留文字并隐藏progress |
| evidence.claim-source | 组合claim/source；每项判断有可核对位置与可见限制，核验状态不因链接存在而自动确认 |
| action.plan-table | 沿用next-step；任务、交付与核对方式逐项对应，补责任、期限、前提及确认状态 |

页面内预置相同组件结构并使用data-field标识编辑字段；这些字段不是page-plan的自动填值接口。列表/表格/链接由Agent在物料化后按真实材料编辑，新增条目不受默认数量限制。page-plan.slots继续只接受纯文本，不能把未审阅HTML当作槽值。

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

[匿名填充预览](../infrastructure/html/examples/project-progress/index.html)提供四种新页面的虚构内容，与[页面计划](../infrastructure/html/examples/project-progress/page-plan.json)、[合成来源](../infrastructure/html/examples/project-progress/source.md)配套。它是内容和版式示例，不是物料化器替代品，也不提供新的导航运行时。单页总目录可选[浅绿预览](../infrastructure/html/templates/single-page/preview/index.html?theme=editorial-green)或[暖黄预览](../infrastructure/html/templates/single-page/preview/index.html?theme=editorial-warm)。预览通过本地HTTP服务打开。

物料化继续先dry-run，再按同一计划摘要apply；普通任务需要固定依赖、已对齐任务和完整页面计划。可参考：

```text
py -3 <固定基础设施>/infrastructure/html/tools/materialize/materialize_html.py --root . --task-id <任务号> --container-id html.container.presentation-deck-v1 --page-plan tasks/<任务号>/page-plan.json --theme editorial-green --scenario-id expression.scenario.project-progress-communication-v1
```

示例计划artifact_kind为template，结构列表保留模板占位以供继续填写；它不声称自动生成完整报告。实际完整报告应按填写协议清理占位并复核来源。

## 版式与验收

- 标题与核心进展同等层级时使用一致字号、字重与左线；章节/工作线标识应便于翻页辨认。
- 列表数量变动时重新检查布局，不强制三栏三行或三条工作线；没有语义对应关系时不暗示逐行对应。
- 桌面演示出现滚动时先减少冗余、调整结构或拆页，不能裁切必要内容；手机可滚动阅读仍需验证末尾可达、无遮挡。保留现有严格检查的真实结果。
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
