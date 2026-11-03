# HTML Viewport Check

`html.viewport-check` 对消费端自包含 HTML 做确定性的资源和响应式检查。浏览器后端可选 Playwright 或本机 Chrome/Edge/Chromium CDP，无需引用测试私有类。

## 使用

```powershell
py -3 infrastructure/html/tools/viewport-check/viewport_check.py `
  --html reports/EXPR-.../v001/index.html `
  --output reports/EXPR-.../v001/viewport-check.json
```

默认检查：390x844、768x1024、1366x768、1920x1080 和 794x1123（A4 近似像素尺寸）。可以通过重复 `--viewport name=widthxheight` 指定自己的矩阵。

工具始终执行静态检查：viewport meta、HTML/CSS 外部运行时资源、相对资源存在性和 HTML 引用边界。`--backend auto` 优先 Playwright，启动不可用时尝试本机 CDP；也可选 `playwright`、`cdp`、`none`，CDP 可传 `--browser`。本地服务器只暴露产物目录且绑定 127.0.0.1，不安装任何浏览器。静态失败时不打开页面。

默认检查首屏；`--all-pages` 遍历演示稿每一页，记录文档水平溢出、可见文字容器溢出、导航遮挡、未加载图片、重复 ID 与页数选项一致性。导航遮挡在滚动到底后测量，以免将手机上可通过滚动阅读的正文误认为永久被挡。自定义容器应使用标准 `data-deck-page`、`data-page-select` 标记。

`--interactions` 验证首尾禁用、前后翻页、备注默认隐藏及内容、原图阅读器打开/Escape关闭/焦点返回/方向键隔离。未选择的可选组件记为 `not-run`。不自动验收全屏、浏览器打印对话框或完整无障碍。

```powershell
python infrastructure/html/tools/viewport-check/viewport_check.py --html '<产物目录>/index.html' --all-pages --interactions --backend cdp --viewport desktop=1366x768 --viewport phone=390x844 --screenshot-dir '<产物目录>/checks/screenshots' --contact-sheet '<产物目录>/checks/contact-sheet.html' --output '<产物目录>/checks/viewport-check.json' --fail-on-overflow
```

`--contact-sheet` 生成离线 HTML 联系表，不依赖 Pillow。再传 `--compare-with '<上一版检查.json>'` 按视口和页序生成并排截图，供人工评审；它不自动声称视觉差异正确，增删页后应人工核对对应关系。截图保留实际控件，记录当前视口，长页可滚动区域需要人工补看。

报告含统一 `checks[]`、HTML SHA-256、环境、指标和限制，Schema 见 `../../schemas/check-result.schema.json`。静态通过但浏览器不可用时，总状态为 `not-run`；浏览器运行后出现页面异常为 `fail`。默认退出码兼容旧行为，静态失败返回 1；加 `--fail-on-overflow` 让所有浏览器布局/交互失败返回 1。`not-run` 返回 0 也不表示视觉验收通过。输出/截图目录应为本次新版本的专用目录，工具会写入这些明确指定的证据文件。
