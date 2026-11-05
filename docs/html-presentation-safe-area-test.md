# 演示稿内容安全区：消费端测试

## 适用范围与变化

面向通过固定 submodule 使用 `html.container.presentation-deck-v1` 或兼容演示稿预设的资产仓。模板画布根据底部控制栏和展开备注的实测高度预留空间，超高内容可在当前页内访问；检查器用 `pageVerticalOverflow` 单独报告超出可视画布的内容，避免把“没有横向溢出”误报为“适合演示”。长页报告不适用演示单页的高度限制，打印保持完整内容可见。

升级 gitlink 不会改写已经物料化的作品。旧版本保留其原始资产、来源摘要和检查证据；测试必须在新的版本目录物料化本次固定版本，不能只更改旧 materialization.json 的来源 SHA。

## 准备

1. 读取消费端根规则、当前任务、固定 Manifest、HTML 主工作流与所选资产入口。
2. 核对父仓 HEAD gitlink、index 与 submodule HEAD 一致，submodule 干净；开发候选与稳定 main 的差异应如实记录，不自动降级。
3. 按消费端授权完成版本升级与必要的 gitlink 提交后再测试。已有用户改动只记录与保留，不顺手提交或覆盖。
4. 已有任务沿用原 ID，通过任务工具的版本重绑定与反馈协议记录新基础设施锚点，不能手改 task.json 绕过并发校验。

## 制作与检查

1. 保留原内容与事实边界，先在隔离目录或新作品版本定位哪些页面需要纵向滚动。
2. 对失败页面给出调整清单：优先减少同屏信息、调整图文比例、将扩展解释移至默认隐藏备注或附录，必要时拆页；保留来源、关键条件及问题—回应关系。不能用全局缩小字体或裁剪内容消除错误。
3. 按主工作流更新逐页计划，通过 html.materialize dry-run / apply 创建新版本，复用共享容器、主题、页框、运行时和原图阅读器。继承内容不等于继承旧版检查结果。
4. 在消费端根目录运行固定 submodule 中的检查工具：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/infrastructure/html/tools/viewport-check/viewport_check.py --html '<新版本>/index.html' --artifact-kind report --all-pages --interactions --full-page --backend auto --viewport desktop=1366x768 --viewport tablet=768x1024 --viewport phone=390x844 --viewport wide=1920x1080 --screenshot-dir '<新版本>/checks/screenshots' --contact-sheet '<新版本>/checks/contact-sheet.html' --output '<新版本>/checks/viewport-check.json' --fail-on-overflow
```

Linux/macOS 用 python3 替代 py -3。路径替换为消费端真实作品目录。无需为了检查安装 Playwright，工具也支持本机 Chrome/Edge/Chromium 的 CDP；后端均不可用时记录 not-run。

5. 检查原始 JSON 中每个视口、每一页的 pageVerticalOverflow、textOverflow、horizontalOverflow、navigationOverlap、brokenImages、duplicateIds；记录失败页 ID 和指标，不只看退出码。补测 `--viewport laptop-short=1280x650`、`--viewport split-window=1000x700`；普通窗口分别切页后，从短窗口进入全屏再次检查，不能只在大窗口进入全屏后验收。手机上保留滚动访问不等于投屏验收通过；无法同时满足时分视口报告限制，并提出独立阅读布局等方案。
6. 实际验证前后翻页、首尾禁用、页码选择、备注默认隐藏与展开后的正文可读性、显示模式、全屏和原图阅读器。查看截图确认标题层级、字号、留白和图文比例；自动几何检查不能代替人工视觉评审。
   组合单页还须核对：背景铺满画布且没有外层白纸/封面装饰；相同视口与比例下所有页画布等高、页码相对画布的基线一致；全屏的正文、插图和页码同比缩放；底栏隐藏/唤出及备注展开后，手机滚到正文末尾和页码均不被遮挡。移除消费端重复实现的页框、folio 和全屏覆盖，不通过裁剪正文或缩字获得通过。
7. PDF 按用户已确认的纸张、方向和页边距导出；缺少参数或未执行时记录 not-run。打印对话框与完整无障碍验收单独记录。

## 回传结果

提交任务 ID、新版本路径、固定基础设施完整 SHA、旧新内容对照、变更页 ID、完整检查 JSON、截图联系表、逐项通过/失败/未运行结果及遗留问题。任务停在 review 等待用户评审；测试提示词本身不授予提交、推送、合并或发布权限。

## 维护者验证基线

本轮 Windows 本地完整回归：218 项测试，5 项因符号链接权限等环境限制跳过，其余通过。包含演示稿控制栏/备注安全区、超高内容可访问、打印内容保留，以及检查器识别真实纵向溢出并在移除缺陷后通过的回归。官方 Manifest 和集成提交的双平台完整回归以对应 SHA 的 GitHub Actions 结果为准；消费端不重复运行基础设施全量。
