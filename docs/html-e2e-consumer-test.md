# HTML 能力消费端端到端测试

状态：`implemented / experimental` 的测试流程文档

本流程用于验证一个真实的消费端小组资产仓库，能否在固定的基础设施 submodule 上完成一次最小 HTML 任务。它验证的是“消费端 Agent 能发现、物料化、修改、检查并记录 HTML 产物”，不代表页面已经通过专业事实验收、发布授权或生产部署验收。

## 测试边界

测试必须在消费端仓库的隔离测试分支进行。测试 Agent 可以修改测试分支中的任务、来源和报告文件；不得修改基础设施 submodule 内的文件，不得提交或推送基础设施仓库，不得部署或发布页面。

本轮只使用合成测试内容，不使用大工项目事实、客户资料、受限源码或未经授权的图片。测试任务使用 `mode: test`，页面只用于验证模板、组件、任务循环和离线资源路径。

必须使用一个明确的基础设施 commit。不能使用 `git submodule update --remote`，不能把远端 `develop` 或 `main` 的移动指针当作版本锁。基础设施当前工作区中的未提交修改不能被消费端 submodule 引用；必须先在基础设施仓库形成一个可获取的 commit，并把准确 SHA 提供给测试 Agent。

## 测试前提

测试开始前准备以下信息：

| 名称 | 含义 |
| --- | --- |
| `INFRA_COMMIT` | 基础设施仓库本轮测试使用的完整 40 位 commit SHA |
| `CONSUMER_ROOT` | 测试机上的小组资产仓库根目录 |
| `SUBMODULE_PATH` | 消费端 `.gitmodules` 中基础设施的相对路径，公共模板通常是 `vendor/suanhai-team-external-expression-infrastructure` |
| `TEST_BRANCH` | 只用于本轮测试的消费端分支，例如 `codex/e2e-html-production-20261031` |

如果 `INFRA_COMMIT` 尚未发布到基础设施远程仓库，先停止测试。不能让测试 Agent 使用另一台机器上的未提交文件，也不能用“远端最新提交”猜测 SHA。

父仓库必须把 submodule gitlink 提交到 `INFRA_COMMIT`。这是工具的安全前提：父仓 `HEAD`、index 和 submodule `HEAD` 必须指向同一个 commit。若测试消费端还固定在旧 commit，应在隔离测试分支中只更新这个 gitlink，并形成一个本地测试提交；该提交不需要推送，但必须保留以便复现测试结果。

## 推荐执行方式

在测试机上启动你平常使用的 Agent，把下面的“测试机 Agent 提示词”全文发送给它。提示词可以从任意起始工作目录运行，会先在 `D:\Works\Suanhaitech\Repos` 创建唯一的公共模板 clone 和隔离测试分支，再自动发现 submodule 路径。提示词中的 `INFRA_COMMIT` 已固定为本轮候选 SHA，无需手工替换。Agent 会在创建本地 gitlink 测试提交和执行 `html.materialize apply` 前分别停下，等待你确认。

## 测试机 Agent 提示词

```text
你现在在一个小组对外表达资产仓库的隔离测试分支中，执行“HTML 基础设施消费端端到端测试”。本次只验证共享基础设施的发现、任务循环、模板/组件物料化、离线资源和审计记录，不制作真实项目页面，不发布，不部署。

本次固定输入：
- 基础设施仓库：suanhaitech/suanhai-team-external-expression-infrastructure
- 基础设施测试 commit：INFRA_COMMIT
- 期望 submodule 路径：SUBMODULE_PATH
- 测试分支：TEST_BRANCH

请严格按以下协议执行。所有路径使用当前仓库根目录的相对路径；所有写入仅限当前消费端测试分支。不要修改基础设施 submodule 内的文件，不要执行 `git submodule update --remote`，不要推送，不要部署，不要发布。

## 0. 工作区和权限预检

1. 读取当前仓库根目录的 `README.md`、`AGENTS.md`，再读取 `.gitmodules`、submodule 的 `manifest.yml`、`workflows/html-production/WORKFLOW.md`、`tools/html-materialize/README.md` 和任务循环入口。
2. 执行并保存输出：

   ```powershell
   git status --short --branch
   git rev-parse HEAD
   git config --file .gitmodules --get-regexp "^submodule\..*\.(path|url)$"
   git submodule status --recursive
   ```

3. 如果父仓库有未说明的修改、submodule 工作区脏、`.gitmodules` 缺失，或当前目录不是消费端根目录，立即停止并报告；不要 stash、reset、clean 或删除文件。
4. 检查当前分支是否为 `TEST_BRANCH`。若当前在其他分支，只有确认这是专用测试 clone 且工作区干净时才创建并切换到 `TEST_BRANCH`；如果这是日常工作 clone 或无法确认隔离性，停止并请测试者提供专用 clone。
5. 从 `.gitmodules` 读取实际 submodule 路径。如果它不是 `SUBMODULE_PATH`，以实际路径为准，并在结果中报告；调用物料化工具时必须传 `--submodule-path "<实际路径>"`。
6. 检查父仓 `HEAD` 的 gitlink、index gitlink 和 submodule `HEAD`。如果三者不是 `INFRA_COMMIT`：
   - 先确认当前分支是 `TEST_BRANCH`，且工作区干净；
   - 在 submodule 中 checkout `INFRA_COMMIT`，只暂存 submodule gitlink；
   - 展示 `git diff --cached --submodule`；
   - 在用户确认后，或用户已经明确授权本次测试分支可创建本地测试提交时，提交唯一的 gitlink 变更；
   - 不推送该消费端测试分支；
   - 如果 commit 对象无法获取，停止并报告，不改用远端最新分支。
7. 重新执行 `git submodule status --recursive`、`git -C "<实际路径>" rev-parse HEAD` 和 `git -C "<实际路径>" status --porcelain`，确认 submodule 正好是 `INFRA_COMMIT` 且干净。

## 1. 只读发现和基础设施预检

1. 解析 `manifest.yml`，确认 `schema_version`、`repository` 正确，并确认以下能力实际存在且入口文件存在：
   - `expression.task-loop`
   - `expression.task-record`
   - `html.project-report-v1`
   - `html.semantic-components-v1`
   - `html.materialize`
   - `expression.html-production`
2. 运行 Manifest 官方校验器（如果测试机安装了 Ruby）：

   ```powershell
   ruby "<实际路径>/scripts/validate_manifest.rb"
   ```

   如果没有 Ruby，标记为“未执行”，不能写成“通过”。
3. 运行消费端 submodule 预检工具。公共模板路径示例：

   ```powershell
   py -3 "<实际路径>/tools/submodule-preflight/submodule_preflight.py" `
     --root . `
     --path "<实际路径>"
   ```

   自定义路径必须替换 `<实际路径>`。预检失败时停止，不自行修复版本关系。

## 2. 创建合成来源和测试任务

1. 使用任务循环工具先创建 `mode: test` 任务，取得唯一的 `<TASK_ID>`。再创建 `context/e2e-html-test/<TASK_ID>/source.md`，避免重测覆盖旧记录；如果消费端规则要求固定路径，必须先确认目标文件不存在。内容可以是：

   ```markdown
   # HTML E2E synthetic source

   This file is synthetic test input only. It is not a project fact and must not be published.
   ```

   不要把真实项目资料复制进来。
2. 用 `brief` 登记：
   - 受众：内部测试者；
   - 用途：验证 HTML 模板、语义组件和任务记录；
   - 范围：项目无关的 HTML 结构和最小合成内容；
   - 输出：`reports/<task-id>`（稳定输出根，不要手写 `v001`）；
   - 来源：刚创建的合成来源文件；
   - 完成标准：页面离线可打开、选中组件已装配、资源路径闭合、task-loop review/validate 通过。
3. 记录实际用户确认原话后执行 `align`，再执行 `start`。每次已有任务写入前都必须先 `show`，并携带最新的 `--expect-version`。
4. 把创建后的任务编号、任务记录版本、任务中记录的 `infrastructure_commit` 输出出来。若任务记录的基础设施 commit 不是 `INFRA_COMMIT`，停止；不要手改 `task.json`。

先执行 `create` 取得任务编号，再创建唯一来源文件；之后每个任务写入命令前都执行 `show`，使用刚返回的最新版本。下面 `N0`、`N1`、`N2` 分别是各自操作前刚查询到的版本，不能复用旧版本号：

```powershell
   py -3 "<实际路径>/harness/task-loop/scripts/task_loop.py" --root . create --test `
  --title "HTML 基础设施端到端合成测试" `
  --request "验证模板、语义组件、任务循环和离线资源，不代表真实项目页面"

# 读取 create 返回的任务编号后，设置唯一合成来源路径并创建来源文件。
$sourcePath = "context/e2e-html-test/<TASK_ID>/source.md"
if (Test-Path -LiteralPath $sourcePath) { throw "合成来源已存在；停止以免覆盖：$sourcePath" }
New-Item -ItemType Directory -Force (Split-Path $sourcePath) | Out-Null
Set-Content -LiteralPath $sourcePath -Encoding utf8 -Value @"
# HTML E2E synthetic source

This file is synthetic test input only. It is not a project fact and must not be published.
"@

py -3 "<实际路径>/harness/task-loop/scripts/task_loop.py" --root . brief <TASK_ID> `
  --expect-version <N0> `
  --audience "内部测试者" `
  --purpose "验证 HTML 基础设施消费端流程" `
  --scope "只做项目无关的合成 HTML 页面和资源检查" `
  --output "reports/<TASK_ID>" `
  --acceptance "页面离线可打开、组件已装配、资源路径闭合、review 和 validate 通过" `
  --source $sourcePath

py -3 "<实际路径>/harness/task-loop/scripts/task_loop.py" --root . event <TASK_ID> `
  --expect-version <N1> --type align `
  --note "合成测试目标、来源、输出根和完成标准已由测试者确认" `
  --user-quote "<测试者实际确认原话；不得由 Agent 编造>"

py -3 "<实际路径>/harness/task-loop/scripts/task_loop.py" --root . event <TASK_ID> `
  --expect-version <N2> --type start `
  --note "开始执行已确认范围内的 HTML 消费端测试" `
  --next-action "完成物料化、页面检查并等待评审"
```

## 3. 物料化 dry-run 和人工确认

从当前固定 submodule 的工具入口执行 dry-run。组件包和语义组件 ID 不要混淆：

```powershell
   py -3 "<实际路径>/tools/html-materialize/materialize_html.py" `
  --root . `
  --submodule-path "<实际路径>" `
  --task-id <TASK_ID> `
  --template-id html.project-report-v1 `
  --component-package-id html.semantic-components-v1 `
  --component-id content.summary `
  --component-id status.phase `
  --component-id status.metric `
  --component-id evidence.claim `
  --component-id action.next-step `
  --source-id synthetic-html-e2e
```

保存完整 JSON 输出，并核对：

- `mode` 是 `dry-run`，没有写入文件；
- `output` 是 `reports/<TASK_ID>/v001`；
- `infrastructure_commit` 等于 `INFRA_COMMIT`；
- `would_write` 只包含任务版本目录中的页面、组件包、模板说明/元数据、许可证文件、`report.yml` 和 `materialization.json`；以工具返回的完整清单为准，不凭文件名列表猜测；
- `plan_sha256` 和 `task_record_version` 已记录；
- 没有目标冲突。

把 dry-run 摘要展示给用户，等待用户明确确认。没有确认前不要加 `--apply`。

## 4. apply 和页面内容填充

用户确认 dry-run 后，使用完全相同的参数，额外加上：

```powershell
py -3 "<实际路径>/tools/html-materialize/materialize_html.py" `
  --root . `
  --submodule-path "<实际路径>" `
  --task-id <TASK_ID> `
  --template-id html.project-report-v1 `
  --component-package-id html.semantic-components-v1 `
  --component-id content.summary `
  --component-id status.phase `
  --component-id status.metric `
  --component-id evidence.claim `
  --component-id action.next-step `
  --source-id synthetic-html-e2e `
  --apply `
  --expect-plan-sha256 <dry-run 的 plan_sha256> `
  --expect-task-version <dry-run 的 task_record_version>
```

1. apply 成功后，检查 `reports/<TASK_ID>/v001/`：

   ```text
   index.html
   styles.css
   report.css
   report.yml
   materialization.json
   README.md
   template.yml
   LICENSE
   NOTICE
   assets/html-semantic-components-v1/
   ```

2. 在编辑页面前，根据 `materialization.json` 的 `files` 清单计算并核对所有物料化文件 SHA-256。模板包的 README、元数据和许可证文件也会随包复制；以完整的 dry-run `would_write` 清单为准。
3. 用最小合成内容替换页面占位符，只写入与测试任务对应的内容。例如把页面标题改为“HTML 基础设施端到端测试”，把状态、指标、证据和下一步组件填入合成文本。不要把占位符保留成看似真实的项目事实。
4. 创建 `reports/<TASK_ID>/v001/sources.yml`，登记 `id: synthetic-html-e2e`，引用 `context/e2e-html-test/source.md`，并说明它是 synthetic、仅内部测试、不具备发布授权。
5. 更新模板包带来的 `README.md`，说明该目录是 `mode: test` 产物、使用的基础设施 commit、模板 ID、组件包 ID 和语义组件 ID。
6. 修改页面后，不要再次运行同一 apply 覆盖用户内容。若需要重新物料化，先保留 v001，按任务反馈创建新修订和 v002。`materialization.json` 的哈希是首次物料化基线；填充页面后 `index.html` 哈希变化是预期的，未编辑资源应保持匹配。

## 5. 离线资源和页面检查

执行下列检查并保留输出：

```powershell
Get-ChildItem -Recurse -File reports/<TASK_ID>/v001
$externalRefs = rg -n -g "*.html" -g "*.css" 'href=["'']https?://|src=["'']https?://|url\(\s*["'']?https?://|//cdn' reports/<TASK_ID>/v001
$rgExit = $LASTEXITCODE
if ($rgExit -eq 0) { $externalRefs; throw "发现远程运行时资源，停止并报告" }
if ($rgExit -gt 1) { throw "rg 检查器执行失败，退出码：$rgExit" }
git diff --check
```

确认：

- `index.html` 中存在本次选择的 `data-component`：`content.summary`、`status.phase`、`status.metric`、`evidence.claim`、`action.next-step`；
- HTML 引用的 CSS 都是相对路径，引用的本地文件真实存在；
- 页面、CSS、组件包不依赖 CDN、远程字体、远程图片或运行时网络；相对路径的本地 `@import` 可以保留，需核对其目标文件存在；
- PowerShell 中 `rg` 退出码 0 表示发现匹配、1 表示没有匹配（符合预期）、大于 1 表示检查器错误；
- 编辑页面前，`materialization.json` 的文件 SHA-256 与实际文件一致；编辑后，未编辑资源仍匹配，`index.html` 哈希变化应被解释为消费端内容填充；
- `report.yml` 记录模板、组件包、语义组件、来源和 pending 授权状态；
- 页面占位符已替换为合成测试内容。

浏览器检查必须区分“已实际检查”和“未执行”：

- 用本地浏览器打开 `reports/<TASK_ID>/v001/index.html`，检查桌面视图；
- 将窗口缩窄到手机宽度，检查导航、文本、组件和表格是否溢出；
- 使用打印预览检查 A4 页面；
- 如测试机能生成截图，保存到仓库外的临时目录，不要把截图或缓存作为测试资产提交。

当前基础设施没有自动浏览器预览、截图、公式渲染或自动无障碍检查器。没有实际打开浏览器时，必须明确写“浏览器检查未执行”，不能把静态测试当作视觉验收。

## 6. 任务 review 和 validate

页面和资源检查通过后，使用当前任务循环记录自包含目录：

```powershell
py -3 "<实际路径>/harness/task-loop/scripts/task_loop.py" `
  --root . event <TASK_ID> `
  --expect-version <最新 version> `
  --type review `
  --note "HTML E2E 合成页面已物料化；记录静态资源、离线路径和浏览器检查结果" `
  --artifact "reports/<TASK_ID>/v001" `
  --next-action "等待测试负责人评审，不执行发布"

py -3 "<实际路径>/harness/task-loop/scripts/task_loop.py" `
  --root . validate <TASK_ID>
```

`review` 前再次 `show` 获取最新 version。`validate` 通过后，不要自动执行 `complete`；本轮测试只需停在 `review`，由测试负责人决定是否记录测试完成。

## 7. 可选的恢复测试

如果要同时验证任务可恢复性：

1. 关闭当前会话，启动新的 Agent；
2. 只发送“继续任务 `<TASK_ID>`，先只读核对状态和产物，不修改文件”；
3. 新 Agent 必须恢复任务状态、版本、submodule commit、产物 SHA-256 和未解决事项；
4. 不要让它自动 `resume`、`complete`、提交或推送。

如果要验证局部反馈：使用 `feedback --scope minor` 进入新修订，生成 `v002`，不得覆盖 v001；再重复页面检查和 `review`。范围变化必须回到澄清阶段，不要直接生成新版页面。

## 8. 结果回传格式

测试 Agent 最终必须用以下结构回传，不要只说“测试成功”：

```text
HTML E2E 测试结果

测试机：<设备或系统版本>
Agent/模型：<实际使用的 Agent 和模型；未知则写未知>
消费端根目录：<绝对路径>
消费端分支：<分支名>
父仓 HEAD：<SHA>
submodule 路径：<实际路径>
submodule gitlink/HEAD：<完整 SHA>
基础设施 commit：<INFRA_COMMIT>
任务编号：<TASK_ID>
任务状态：<working/review/paused；不要擅自声称 completed>

通过项：
- Manifest 能力发现：<pass/fail>
- submodule 预检：<pass/fail/warn，附原因>
- 任务 create/brief/align/start：<pass/fail>
- materialize dry-run：<pass/fail，plan_sha256>
- materialize apply：<pass/fail，写入文件数>
- 语义组件插入：<pass/fail，列出组件 ID>
- 本地资源路径：<pass/fail>
- 离线依赖检查：<pass/fail>
- report.yml/materialization.json：<pass/fail>
- 浏览器桌面检查：<pass/fail/not-run>
- 手机视图检查：<pass/fail/not-run>
- 打印视图检查：<pass/fail/not-run>
- task-loop review：<pass/fail>
- task-loop validate：<pass/fail>

实际执行的关键命令：<列出命令，不省略参数>
生成目录：<相对路径>
工作区状态：<git status --short --branch 和 submodule status 摘要>
未解决问题和限制：<逐项列出>
是否提交/推送：必须明确写“未推送”；如创建了本地测试提交，列出 SHA 和内容
```

只有在上述结果、关键命令和工作区状态都返回后，本轮才算完成测试数据收集。测试结果仍需由维护者审核，不能把 Agent 的自报结果视为自动发布授权。
