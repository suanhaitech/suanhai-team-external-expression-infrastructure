# HTML 模板资产

状态：`implemented / experimental`

这里统一放置 HTML 的容器、单页模板和完整组合预设。工作流通过 Manifest 能力 ID 选择资产，不能把目录路径当作稳定接口。

```text
templates/
├── containers/    长页报告、多页演示稿等整体阅读容器
├── single-page/   可自由组合的单页模板
│   ├── cover/
│   ├── agenda/
│   ├── transition/
│   ├── content/
│   ├── closing/
│   └── appendix/
└── presets/       为常见任务保留的完整组合预设
```

`presets/` 当前提供 `project-report-v1/` 和 `presentation-deck-v1/`。前者面向纵向连续阅读的长页报告；后者面向逐页讲解，翻页控件固定在底部，并带页码选择、上一页/下一页、键盘导航、可选讲者备注和逐页打印。它们是兼容性和快速上手入口，不限制未来的页面自由组合。

`single-page/` 的页面模板是可嵌入容器的单个逻辑页面，不是完整的 `<html>` 文档。每个页面包应包含 `template.yml`、`page.html`、专属 `styles.css`、`README.md`，并声明页面角色、版本、插槽和兼容容器。只有登记在 Manifest 中的页面 ID 可由 Agent 调用。

当前页面角色、能力 ID 和顺序组合示例见 [`single-page/README.md`](single-page/README.md)，采样来源、筛选依据与复现边界见 [`docs/html-single-page-template-sampling.md`](../../../docs/html-single-page-template-sampling.md)。

页面模板只在固定 submodule commit 中可用；消费端应复制到自己的作品版本目录，不要修改 submodule 内的文件。内容、来源、事实核对和发布授权仍由消费端维护。

新小组模板的报告类任务默认使用 `reports/<任务编号>/v001/`；旧消费端仍可使用 `works/`。系列、课程和书籍保持各自归档，不统一移入 `reports/`。

新 HTML 任务默认采用分页组合（`html.container.presentation-deck-v1` + `page-plan.json` + `html.single-page.*`），服务现场逐页讲解。用户明确要求连续阅读、传阅或查阅时采用长页；既有长页保持兼容。容器选择与空白模板/完整报告是独立维度；Agent 主动推荐资产，记录候选与选用资产、定制理由和验收信号。
