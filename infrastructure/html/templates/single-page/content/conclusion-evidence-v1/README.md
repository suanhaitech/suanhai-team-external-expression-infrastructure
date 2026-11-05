# 当前结论与证据

能力ID：`html.single-page.content.conclusion-evidence-v1`。

逐条判断、证据入口及限制；适合工作主线的第二层讲述。

页面可独立使用或与其他单页自由组合，不限制工作主线数量、周期或总页数。数据列表由Agent在物料化后按真实内容增减；`page-plan.slots`仅允许纯文本，不通过HTML字符串注入复杂结构。

嵌入的组件展示沿用核心包契约；内部`data-field`只用于就地编辑，不是第二套可调用槽协议。需单独插入组件时使用supporting槽，避免与已有主体重复。

默认未知信息保留待确认，重要限制保持可见。主题可用editorial-green或editorial-warm，结构相同。桌面内容过多时拆页，不裁切或持续缩字；手机允许明确的滚动阅读，打印允许续页。

详见[填写与场景映射](../../../../../../docs/project-report-reusable-assets.md)。
