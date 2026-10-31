# HTML 页面模板

状态：`implemented / experimental`

职责：提供由 HTML 基础层、布局和语义组件组合而成的可复用页面起点。

当前提供 `project-report-v1/`，已加入根目录 `manifest.yml`。页面模板只在固定 submodule commit 中可用；消费端应复制到自己的作品版本目录，不要修改 submodule 内的文件。模板可以组合 `../components/` 中的通用组件，但交付页面必须复制为自包含产物。

新小组模板的报告类任务默认使用 `reports/<任务编号>/v001/`；旧消费端仍可使用 `works/`。系列、课程和书籍保持各自归档，不统一移入 `reports/`。
