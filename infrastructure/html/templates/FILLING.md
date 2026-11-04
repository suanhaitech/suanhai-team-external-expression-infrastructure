# 模板填写与复用协议

分页/长页决定阅读方式，`template`/`report` 决定内容完成度。空白模板可以保留明确的内容占位，但仍须具有合法结构、状态与可用导航。完整报告需要来源核验并清理占位；两种交付均不自动取得发布授权。

## 填写顺序

1. 读取所选单页的 `template.yml`、组件 `component.yml` 与 JSON 契约，保留稳定页面 ID 和已声明插槽；按语义职责选资产，不能仅凭视觉相似选卡片。
2. 填写 `data-slot` / `data-field` 正文与标题。属性用于定位，不会自动替换嵌套内容；替换父槽时不能误删子槽、单位或状态标签。纯文本计划不接受任意 HTML。
3. 对带状态的组件，同时设置 `data-state` 和可见状态标签。属性只能取组件契约的一个枚举值，不能填写候选列表。默认 `unverified`（待核验）或 `proposed`（拟议）不代表业务事实已经确认；不能只改颜色或只改可见文字。
4. 复制或删除整个重复单元（完整 article、表格行、主线页等），同步其唯一 ID、来源映射和页面计划；工具不自动推断真实主线数量。删除后重查目录、页码与交叉引用。
5. 作者操作说明、候选枚举、复制提示放在版本 README 或独立填写说明中。正文只保留读者需要的信息。探索期间可用 `data-author-hint` 标记提示，进入完整报告前清理；隐藏备注也随文件交付。

## 复用记录

分页用 `page-plan.json` 记录 `artifact_kind`、页面职责（`objective`）、核心信息、来源 ID、`candidate_assets`、实际 `template_id/components`、`customization_reason`、`acceptance_signals`。没有定制时写明直接复用；有缺口时说明为什么现有资产不足、局部补充什么以及验证方法，不另起一套公共排版或导航。

长页可在人读内容计划记录同样信息，不伪造逐页 ID。`materialization.json` 保存初始共享资产来源，后续编辑不回写初始哈希；检查结果中的 `static.resources` 与 `resources_sha256` 才描述检查时实际显式引用的资源集。它不覆盖 JS 动态依赖、来源内容或整个作品目录。

## 空白模板的填写验证

交付 README 至少说明槽位、状态/标签对应、重复单元、来源登记与检查命令。在仓外临时目录复制产物，使用明确标为合成的中性内容填写一个完整单元，并覆盖状态变化及重复单元增删，运行 `--artifact-kind report --backend none`；随后检查可用浏览器中的布局。合成数据仅在隔离目录使用，不进入消费端业务来源或正式版本。

`html.viewport-check --artifact-kind template` 允许正文占位，但拒绝非法组件状态；`--artifact-kind report` 另外拒绝方括号候选占位与 `data-author-hint`。这是启发式检测，文献编号或数学表达也可能匹配，须人工核对；它不自动证明填写完整、状态文字与属性语义一致或事实正确。默认值为 `template` 兼容历史调用，新任务必须显式指定。

演示稿检查使用 `--all-pages --interactions --full-page --fail-on-overflow`；长页使用 `--interactions --full-page --fail-on-overflow`。没有对应交互或浏览器不可用时保留 `not-run`，不能把空问题列表当作已经覆盖。全长截图与打印媒体均不能证明真实 PDF 分页正确。
