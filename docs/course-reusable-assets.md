# 从课程制作沉淀可复用资产

本轮把一次课程网页制作中出现的通用需求沉淀为页面、样式、组件、工具和既有工作流规则。这里只记录可复用能力与验收方式，不保存原课程的标题、讲述事实、案例图片、人员信息或用户确认。

场景仍在 `scenarios/`，主工作流仍是 `expression.html-production`，工作流消费 `infrastructure/html/`。不是每一条经验都需要新的能力 ID，更不需要为每个检查点新建子工作流。模板表达页面职责，组件表达局部语义对象，样式统一视觉，运行时提供读者交互，工具负责确定性装配和检查；受众、来源与内容始终来自消费端。

## 30 项沉淀与验收映射

下表是本轮候选的实现归属和验证要求。表中路径指向代码或规则，不表示已经发布到 `main`，也不表示每项已做浏览器视觉验收。实际命令、环境、通过数及 `not-run` 必须记录在本轮开发结果中，不能仅凭这张表宣称通过。

| 编号 | 通用需求 | 沉淀形式与位置 | 验收关注点 |
| --- | --- | --- | --- |
| 1 | 插图式技术封面 | `templates/single-page/cover/technical-editorial-v1/` | 标题、说明、插图职责分开；无真实项目素材；窄屏仍可读 |
| 2 | 目录与章节路线 | 增强 `templates/single-page/agenda/route-v1/` | 章节与页码来自完整页面清单，插页后目录可重新派生 |
| 3 | 章节过渡页 | 增强 `templates/single-page/transition/statement-v1/` | 章节标题与本章要回答的问题突出，不堆叠整章正文 |
| 4 | 阶段演进页 | `templates/single-page/content/stages-v1/` | 演进顺序明确，阶段说明不暗含未经支持的因果关系 |
| 5 | 数字与观察页 | `templates/single-page/content/observation-v1/` | 数字、观察与解释分层，必要统计条件保持可见 |
| 6 | 定义与问题映射 | `templates/single-page/content/definition-mapping-v1/` | 精确定义独立突出，问题与回应一一可读 |
| 7 | 两栏对照 | `templates/single-page/content/comparison-v1/` | 比较维度一致，左右内容和阅读顺序清楚 |
| 8 | 原图与分析 | `templates/single-page/content/figure-analysis-v1/` | 原图、图注和讲者分析有边界，支持侧排或下排 |
| 9 | 短流程讲解 | 增强 `templates/single-page/content/method-v1/` | 单页表达少量连贯步骤，未声明通用图编辑器 |
| 10 | 关键词矩阵 | `templates/single-page/content/keyword-grid-v1/` | 关键词和解释有层级，不把视觉格子当作独立事实 |
| 11 | 暖白编辑主题 | `components/core-v1/themes/editorial-warm.css` | 主题控制颜色和视觉令牌，不改变项目内容或语义 |
| 12 | 公共页框 | `styles/presentation-v1/` | 共用边距、页眉和页脚节奏，页面模板保留职责差异 |
| 13 | 中文及混排字阶 | `styles/presentation-v1/` | 中文、英文、数字、长标题和副标题层级清楚，无固定项目标题 |
| 14 | 跨屏与安全溢出 | `styles/presentation-v1/` 及既有 `styles/responsive-v1/` | 窄屏不横向溢出，长内容可滚动或续页，不以裁剪伪装适配 |
| 15 | 完整原图阅读 | `runtime-kits/image-viewer-v1/` | 本地原图可完整展示、滚动与关闭，焦点/键盘行为可检查；无编辑或缩放按钮 |
| 16 | 整稿清单与目录页码同步 | `schemas/page-plan.schema.json`、`tools/materialize/` | 稳定页面 ID 唯一、来源引用闭合、页序派生；漏页和坏引用拒绝 |
| 17 | 安全派生版本与局部修订 | `tools/materialize/` 的基线与目标页参数 | 基线只读，新版本生成；非目标页保持，目标冲突先预览再处理 |
| 18 | 整稿逐页检查 | `tools/viewport-check/` | 遍历全部逻辑页；单次截图不能代替整稿；缺浏览器记 `not-run` |
| 19 | 截图联系表与版本并排 | `tools/viewport-check/` 的图册/对比输出 | 页面截图可定位和并排审阅；不宣称自动审美评分或内容等价 |
| 20 | 素材登记 | `tools/source-assets/` | 记录本地哈希、尺寸、来源及原始/衍生关系；URL登记不等于授权下载 |
| 21 | 统一 QA 证据 | `schemas/check-result.schema.json` 与 `checks/html/` | 状态和证据路径一致；无产物摘要只允许 `not-run` |
| 22 | 来源与作品原始字节保护 | `infrastructure/repository-management/tools/asset-bytes/`、小组模板 `.gitattributes` | 规则按目录阻止 Git 换行转换；预览与应用摘要一致，既有规则和历史文件不重写；摘要相同不等于内容正确 |
| 23 | 页面组件插槽 | 单页 `template.yml`、`components/core-v1/` 与 `tools/materialize/` | 只插入已声明位置和组件；错误插槽拒绝，不拼接任意输入为代码 |
| 24 | 正文、备注和附录分层 | [课程画像](../scenarios/course-learning-v1/README.md)、[主流程](../workflows/html/production/WORKFLOW.md) | 不强制每页来源小字；必要条件可见；备注不成为保密区 |
| 25 | 定义、判断与解释的语言层级 | 课程画像的内容表达规则 | 核心表述准确，辅助解释自然；讲者归纳不冒充来源原话 |
| 26 | 问题提出与结尾回应 | 课程画像、逐页计划 `responds_to` | 先提出再回扣，稳定 ID 关联；不要求每页建立复杂关系图 |
| 27 | 受众基础、理解深度和时间预算 | 主流程简报与 [brief.json](../infrastructure/html/examples/records/brief.json) | 对齐讲解深度和范围，不统一限制每页字数与总页数 |
| 28 | 逐页反馈与认可范围保护 | 主流程修订规则与 [revision.json](../infrastructure/html/examples/records/revision.json) | 记录真实反馈出处；认可一页不升级为整课验收；差异检查不代替认可 |
| 29 | 分阶段制作、占位与暂停续作 | 主流程、任务循环及 [handoff.md](../infrastructure/html/examples/records/handoff.md) | 区分已制作/占位/已讨论未制作；只复用现有 pause/resume 和状态真源 |
| 30 | 逐页来源与判断边界 | [source-map.json](../infrastructure/html/examples/records/source-map.json) 与课程画像 | 定义、观察、教学构造和归纳可区分；文件闭合不被当作事实验收 |

除第 22 项已经写明的跨领域完整路径外，表中 `templates/`、`styles/`、`components/`、`runtime-kits/`、`tools/` 和 `schemas/` 路径均相对于 `infrastructure/html/`。资产字节保护属于仓库管理领域，可读取 [consumer.asset-bytes](../infrastructure/repository-management/tools/asset-bytes/README.md)；不应从目录或候选编号猜能力 ID，调用前读取固定提交的 Manifest 和资产入口。

## 消费端如何复用

Agent 先读任务与来源，识别课程场景并对齐受众和时间，再形成完整页面计划。新稿使用 `--container-id` 和 `--page-plan` 组合已实现模板，按需要选样式、组件与运行时。局部改动在新修订中使用同一任务的基线版本和目标页面 ID，继承非目标内容。所有写入仍遵守 dry-run、摘要核对和显式应用。

`--page-plan` 与重复的 `--page-id` 不能同时提供；前者用于带稳定 ID 和内容的完整清单，后者保留为简单选型接口。页面组件在页面计划的 `components` 中指向已声明的插槽；完整预设原有的顶层 `--component-id` 不能直接套给单页组合。

课程组织规则增强已有主工作流，不替代场景判断，也不提供自动教学效果评估。中性记录样例见 [records/README.md](../infrastructure/html/examples/records/README.md)，实际文件应留在消费端。新旧两类消费仓都以自己的根规则、目录和固定 submodule 为边界，不要求迁移到标准模板布局。

## 验证口径与当前限制

文件与引用检查可以证明接口闭合，字节摘要可以证明被保护内容未变，浏览器检查可以观察具体环境下的布局和交互。它们都不能证明事实、教学策略或审美已被负责人认可。缺少浏览器、没有真实产物或未实际执行的检查一律保留 `not-run`；样例文件不能作为通过证据。

本轮不把某篇课程的具体知识、四个目标、案例原图或固定章节顺序沉淀为通用资产。学习目标、概念地图、专用交互练习等不因出现相关文字就成为已实现能力；只有真实入口、契约和检查具备后才能登记。尚未制作的课程章节和尚未核对的页面必须在消费端交接中保留。

合入前需要完成相关 Python 回归、Manifest 官方校验和改动审查。发布前再按仓库分支协议验收与晋级；本文件本身不提供提交、推送或发布授权。
