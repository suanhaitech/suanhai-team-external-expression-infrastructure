# HTML Viewport Check

`html.viewport-check` 对消费端自包含 HTML 做确定性的资源和响应式检查，并在本机存在 Playwright 浏览器运行时的情况下执行真实多视口溢出检查。

## 使用

```powershell
py -3 tools/html-viewport-check/viewport_check.py `
  --html reports/EXPR-.../v001/index.html `
  --output reports/EXPR-.../v001/viewport-check.json
```

默认检查：390x844、768x1024、1366x768、1920x1080 和 794x1123（A4 近似像素尺寸）。可以通过重复 `--viewport name=widthxheight` 指定自己的矩阵。

工具始终执行静态检查：viewport meta、HTML/CSS 外部运行时资源、相对资源存在性和 HTML 引用边界。若 Python 环境有 `playwright` 且浏览器可启动，工具会启动只绑定 `127.0.0.1` 的临时静态服务器，在每个视口测量 `scrollWidth` 与 `innerWidth`，可选保存截图。没有浏览器时浏览器部分为 `not-run`，退出码仍只反映静态检查；不能将 `not-run` 解读为视觉通过。

`--fail-on-overflow` 可以把已执行视口中的水平溢出转换为失败退出码。工具不修改 HTML，不安装浏览器，不访问远程运行时资源；报告会记录页面 SHA-256、检查配置、浏览器检查状态和各视口指标。
