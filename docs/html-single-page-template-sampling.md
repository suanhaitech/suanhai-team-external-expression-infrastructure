# HTML 单页模板采样与筛选

状态：设计采样记录与已登记页面资产清单。十个页面均为基础设施仓原创模板，不是第三方模板的复制品；页面现已登记为 Manifest 能力，可由 `html.materialize` 与逐页容器组合。

## 页面角色

单页按表达职责分为六类：封面、目录、章节过渡、正文、结尾、附录。指标、证据、对比、架构、方法和公式属于正文的版式变体；长页滚动和逐页演示属于容器。这个划分让制作方能按内容挑页面，再交给容器决定连续阅读还是逐页讲解。

## 公开样例

| 参考 | 观察重点 | 筛选结论 |
| --- | --- | --- |
| [Bootstrap Cover](https://getbootstrap.com/docs/5.3/examples/cover/) | 标题、主张和次要行动的层级 | 只参考内容主次；不引入 Bootstrap 依赖 |
| [Bootstrap Blog](https://getbootstrap.com/docs/5.3/examples/blog/) | 长内容的标题层级、元信息和留白 | 适合借鉴编辑式排版；不照搬博客导航和站点外壳 |
| [Bootstrap Dashboard](https://getbootstrap.com/docs/5.3/examples/dashboard/) | 指标、表格和状态的对齐方式 | 只借鉴信息分组；避免把对外页面做成密集后台面板 |
| [Bootstrap Features](https://getbootstrap.com/docs/5.3/examples/features/) | 多个论点/能力的扫描顺序 | 参考重复信息的节奏，不复制图标或示例文案 |
| [HTML5 UP Editorial](https://html5up.net/editorial) | 出版物式标题、分区和正文阅读 | 只参考编辑层级；该站主题按 CC BY 3.0 发布，原代码和素材不纳入本仓 |
| [HTML5 UP Hyperspace](https://html5up.net/hyperspace) | 章节切分与重点内容的变化 | 只借鉴章节节奏，不采用其滚动导航或视觉资产 |
| [Reveal.js](https://github.com/hakimel/reveal.js) | 逐页讲解与页面导航模型 | 既有演示容器已经提供底部页码和前后页控件；不复制其运行时代码 |

Bootstrap 示例遵循 Bootstrap 项目的 MIT 许可；Reveal.js 使用 MIT 许可。外部页面只作为设计研究来源，本轮没有复制第三方 HTML、CSS、脚本、图片、字体、图标或文案。复现的视觉与组件代码由本仓重新编写。

## 筛选标准

1. 页面角色清楚，读者能迅速知道这一页承担什么表达任务。
2. 内容插槽有边界，能容纳消费端的真实文字、数据、来源和待确认状态。
3. 版式在宽屏、窄屏和打印中都能读；内容变长时允许自然增高或拆页，不隐藏、缩小或裁切。
4. 页面离线工作，不依赖 CDN、远程字体、远程图片或服务端脚本。
5. 样式有变体命名空间，未来可以与其他页面和基础组件组合。

## 本轮复现

| 页面角色 | 模板 | 采用的表达结构 |
| --- | --- | --- |
| 封面 | `cover/editorial-v1` | 主题、场景、摘要、读者和核心判断 |
| 目录 | `agenda/route-v1` | 静态阅读路线；不承担翻页或点击导航 |
| 章节过渡 | `transition/statement-v1` | 章节编号、主题和关键问题 |
| 正文 | `content/evidence-v1` | 判断、证据、口径和表达边界 |
| 正文 | `content/method-v1` | 问题、方法、检查和判断步骤 |
| 正文 | `content/project-overview-v1` | 项目总体判断、上期基线、本期变化和里程碑影响 |
| 正文 | `content/workstream-update-v1` | 单条主线的目标、结果、证据条件、限制和下周期结果 |
| 正文 | `content/dependencies-v1` | 跨主线输入输出、就绪条件、项目影响和协作请求 |
| 结尾 | `closing/action-v1` | 收束结论和可执行后续动作 |
| 附录 | `appendix/source-register-v1` | 来源名称、版本定位和授权引用范围 |

这些页面已可被物料化工具调用。三种项目正文页基于周期汇报的通用结构重新设计，仅提炼总体叙事、证据分层和跨线关系，没有复制来源项目的页面、图片、数据或文案；职责与取舍见 [项目总汇报设计](project-progress-report-design.md)。后续是否新增指标、对比、架构/流程或公式变体，以真实消费端反馈为依据。

## 调用方式

页面以 `html.single-page.<role>.<variant>-v1` 登记；逐页容器以 `html.container.presentation-deck-v1` 登记。组合调用示例：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/infrastructure/html/tools/materialize/materialize_html.py `
  --root . `
  --task-id EXPR-20261031-1234abcd `
  --container-id html.container.presentation-deck-v1 `
  --page-id html.single-page.cover.editorial-v1 `
  --page-id html.single-page.agenda.route-v1 `
  --page-id html.single-page.content.evidence-v1 `
  --page-id html.single-page.closing.action-v1
```

重复 `--page-id` 的顺序就是页面顺序。当前组合器要求页面兼容 `paged-deck`，会复制单页样式、生成页码并记录每页的能力 ID、角色、变体和来源。单页组合目前不接受 `--component-id`；页面尚无通用语义组件插槽，避免把选中的组件静默放入不合适的页面。需要结构化语义组件时，使用仍兼容的完整预设路径，或在消费端按页面语义编排后另行登记评审。
