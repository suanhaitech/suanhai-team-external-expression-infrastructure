# HTML 页面容器

容器定义整个 HTML 的阅读方式和运行边界：长页容器负责连续滚动，演示稿容器负责逻辑分页、底部页码、上一页/下一页、键盘操作和逐页打印。容器不拥有项目内容，也不决定每一页使用哪种页面变体。

逐页演示稿容器已登记为 `html.container.presentation-deck-v1`。工作流通过 `html.materialize --container-id ... --page-id ...` 组合这里的容器与 `single-page/` 页面包；`--page-id` 顺序决定展示顺序。完整预设继续保留，供旧调用与快速起稿使用。
