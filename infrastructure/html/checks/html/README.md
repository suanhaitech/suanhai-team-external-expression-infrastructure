# HTML 确定性检查

状态：`implemented / experimental`

实现入口为 [`html.viewport-check`](../../tools/viewport-check/README.md)：静态资源、整稿逐页多视口、导航遮挡、图片完整加载、重复 ID、可选成品交互检查。Playwright 或本机 CDP 后端只打开指定的离线产物，本机无浏览器时如实记录 `not-run`。

检查 JSON 使用 [`check-result.schema.json`](../../schemas/check-result.schema.json)，统一包含工具、时间、入口 HTML SHA-256、总体状态、逐项 `checks[]`、证据与限制。总状态规则：任一已运行失败为 fail；浏览器等必要项未运行时为 not-run；已选择的必要检查全通过才为 pass。可选组件未选择时可在其子项说明 not-run，不强迫安装所有组件。

默认 CLI 退出码为向后兼容只保证静态资源成功；自动验收请传 `--fail-on-overflow` 并读取 JSON，不能把退出 0 当作所有检查已执行。浏览器启动缺失为 not-run，已启动后页面脚本或检查异常为 fail。视口下的打印媒体不等于真实 PDF 分页、页数验收。

HTML 联系表和前后版本截图并排供人工评审，不自动判断美观。SHA 为 null 的未运行样例只能取 not-run，不得拿来登记任务检查通过。来源素材另用 [`html.source-assets`](../../tools/source-assets/README.md) 检查字节、尺寸与来源/衍生关系。

工程检查不替代专业判断、内容确认、图片可读性或对外发布授权。
