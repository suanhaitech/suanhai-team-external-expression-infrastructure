# 工作主线进展 v1

能力 ID：`html.single-page.content.workstream-update-v1`。

一页聚焦一条工作主线，以“本期承诺、实际结果、证据条件、结论限制、项目影响、下周期结果”组织输入，支持项目经理用同一口径讲述不同主线。结果和证据是事实层，结论与项目影响是解释层，两层需要分别核验。

- 插槽：`eyebrow`、`title`、`summary`、`owner`、`status`、`commitment`、`result`、`evidence`、`conditions`、`conclusion`、`limitation`、`project-impact`、`next-result`、`next-check`、`source`。
- `evidence` 可填已登记且获准交付的相对附件链接；长方法、实验数据和详细日志留在附件，不把本页变成技术资料目录。
- 每条主线均保留负责人、数据截止时间和核验状态；未收到更新时显式标明，不推断为无进展，也不照抄上期内容充当本期结果。
- `next-result` 写可核对的交付或验收证据，`next-check` 写负责人、时间、完成标准和依赖。
- 样式支持窄视口、容器宽度变化和打印，长内容自然增长；内容过长时按“结果与证据”“限制与下一步”拆页并检查打印，不以裁剪或缩小字号压进画布。

本页面为原创结构，仅含中性占位符；专业结论由主线负责人核验，项目经理结合多条主线组织整体影响。需通过 `html.materialize` 组合到已登记的 `paged-deck` 容器；可以多次选择同一页面 ID，为各主线分别生成实例。
