# HTML PDF 导出工具

状态：`implemented / experimental`

`export_pdf.py` 将消费端任务版本目录中的自包含 HTML 页面，通过本机 Chrome、Edge 或 Chromium 的 headless DevTools Protocol 打印成 PDF。工具只使用 Python 标准库，不自动安装浏览器、不访问远程运行时资源，并将输出哈希和打印环境写入同目录的 `pdf-export.json`。

## 命令

在消费端任务产物目录执行：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/infrastructure/html/tools/pdf-export/export_pdf.py `
  --root reports/EXPR-YYYYMMDD-xxxxxxxx/v001 `
  --input index.html `
  --output report.pdf `
  --metadata pdf-export.json `
  --paper a4
```

工具先在 `127.0.0.1` 上启动临时 HTTP 服务，再通过浏览器 DevTools 的 `Page.printToPDF` 输出。`--landscape` 可切换横向，`--margin-mm` 设置统一页边距，`--scale` 设置 0.1 到 2.0 的缩放比例，`--no-background` 关闭背景打印。默认由 `--paper` 决定纸张；只有显式传入 `--prefer-css-page-size` 时，HTML 内的 `@page { size: ... }` 才覆盖命令行纸张设置。

输出成功时返回 `status: completed`，并生成 PDF 和元数据；找不到浏览器时返回 `status: not-run`，仍写入元数据说明原因。输入、输出和元数据都必须是产物目录内的安全相对路径，工具拒绝路径越界、符号链接逃逸和覆盖已有文件。

PDF 的字体、分页和二进制内容可能随本机浏览器、字体和操作系统变化；工具只等待页面加载事件和字体加载，不保证异步脚本或懒加载图片已完成。`pdf-export.json` 记录浏览器版本、纸张、页边距、缩放、CSS 纸张优先级、字节数和 SHA-256，浏览器绝对路径只描述本机环境。不能把“生成成功”当作版式、事实或发布授权评审。
