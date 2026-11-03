# 图像与分析

能力 ID：`html.single-page.content.figure-analysis-v1`。原图与分析共用结构，可用 data-analysis-layout="side" 或 "below" 控制左右/上下布局。分析标签由消费端按案例、架构或实验目的填写。

内容槽：`eyebrow`, `title`, `summary`, `figure`, `analysis`, `boundary`。标题、来源、限定条件由消费端填充。示例文字和 SVG 仅演示结构，不表示项目事实。共享页框由 `shared_styles` 声明，颜色可选 `editorial-warm`。

支持可选 `supporting` 组件槽，由 page-plan 为本页绑定组件；不要求每页都插入组件。

手机自动单列、标题自然换行、长内容允许增高；桌面与打印应以真实内容重新检查。详细溯源可以放讲者备注，必要的事实限定、数据口径及图片来源仍须随内容保留。

本地示例图通过 `a[href][data-source-image]` 提供原图入口；选择 `html.image-viewer-v1` 时在完整原图阅读器中打开，未选择运行时或脚本不可用时按普通链接打开。更换图片时同步 `href`、`data-source-image`、图像`src`、caption与alt。
