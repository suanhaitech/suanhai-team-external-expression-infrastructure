# 可直接转发的 HTML 端到端测试提示词

将下面“测试机 Agent 提示词”全文发送给测试机上你平常使用的 Agent。可以从 Agent 当前打开的任意工作目录发送；提示词会先在固定测试父目录创建一个全新 clone，再在其中完成测试。基础设施候选 commit 已固定，无需预先填写 submodule 路径或任务编号。该流程面向 Windows PowerShell，要求安装 Git 和 Python 3.10+；Ruby 只用于官方 Manifest 校验。

## 测试机 Agent 提示词

你现在可能位于任意工作目录。先按“0. 创建隔离测试 clone”在 `D:\Works\Suanhaitech\Repos` 下新建独立消费端仓库；后续所有读取、写入和 Git 命令都必须针对这个新 clone，不能操作启动时所在目录中的任何仓库。本轮只验证固定基础设施 submodule、任务循环、HTML 模板、语义组件、物料化、离线资源和审计记录。使用合成测试内容，不制作真实项目页面，不发布，不部署。

本轮唯一测试候选为基础设施 commit `149759f18edf54c83bdfbadf8326c3031c10bb4f`，来自远程短期分支 `codex/feat-html-production-workflow`。它不是稳定 `main` 发布版。全程按该 SHA 固定，不得改用浮动分支头。

总规则：
- 只修改当前消费端仓库的隔离测试分支；不得修改 submodule 内的文件。
- 不执行 git submodule update --remote，不根据远端 main/develop 自动选择版本。
- 不自动提交、推送、部署或发布。需要记录 gitlink 的本地测试提交前，先展示差异并等用户确认。
- 不 stash、reset --hard、clean、删除用户文件或覆盖已有作品。
- 每次已有任务写入前先 show，使用刚刚读取的最新 --expect-version；版本冲突就停止并重新读取。
- 不编造用户原话、项目事实、来源授权或浏览器检查结果。

## 0. 工作区和固定依赖预检

### 创建隔离测试 clone

以下 PowerShell 命令不依赖 Agent 启动时所在目录。测试仓统一创建在 `D:\Works\Suanhaitech\Repos` 下，每次使用时间戳目录和对应分支；目录已存在、父目录不可用、clone 失败或无法确认当前工作目录时立即停止，不删除、不覆盖任何内容。

    $testParent = 'D:\Works\Suanhaitech\Repos'
    if (-not (Test-Path -LiteralPath $testParent -PathType Container)) { throw "测试父目录不存在：$testParent" }
    $runId = Get-Date -Format 'yyyyMMdd-HHmmss'
    $testDir = "html-e2e-test-$runId"
    $consumerRoot = Join-Path $testParent $testDir
    $testBranch = "codex/e2e-html-production-$runId"
    if (Test-Path -LiteralPath $consumerRoot) { throw "测试目录已存在，停止以免覆盖：$consumerRoot" }
    Set-Location -LiteralPath $testParent
    git clone --recurse-submodules 'https://github.com/suanhaitech/suanhai-team-group-asset-template.git' $testDir
    if ($LASTEXITCODE -ne 0) { throw "模板仓库 clone 失败，退出码：$LASTEXITCODE" }
    Set-Location -LiteralPath $consumerRoot
    git switch -c $testBranch
    if ($LASTEXITCODE -ne 0) { throw "创建隔离测试分支失败，退出码：$LASTEXITCODE" }
    git status --short --branch
    git submodule status --recursive
    if ((git status --porcelain).Length -ne 0) { throw '新 clone 工作区不干净，停止测试' }

clone 完成后，必须把 Agent 的工作目录切换为 `$consumerRoot`。如果 Agent 客户端不能持久切换工作目录，后续每条命令都必须显式使用该根目录（例如 Git 使用 `git -C $consumerRoot`、任务工具使用 `--root $consumerRoot`）；不得退回启动时的工作目录。记录 `$consumerRoot` 和 `$testBranch`，后续报告使用其绝对路径。

先读取当前仓库根目录的 README.md、AGENTS.md、.gitmodules，再读取基础设施 submodule 中的 manifest.yml、HTML 工作流协议、HTML 物料化工具说明和任务循环入口。

执行并保存结果：
    git status --short --branch
    git rev-parse HEAD
    git config --file .gitmodules --get-regexp "^submodule\..*\.(path|url)$"
    git submodule status --recursive

如果刚创建的 clone 中 `.gitmodules` 缺失、父仓有未说明改动或 submodule 工作区不干净，停止并报告。不要 stash、reset、clean 或删除文件。将候选 SHA 保存为 `$expectedInfrastructureCommit`：
    $expectedInfrastructureCommit = "149759f18edf54c83bdfbadf8326c3031c10bb4f"

确认当前分支等于刚才创建的 `$testBranch`，并且当前路径位于 `$consumerRoot`。若不一致，停止；不得在 `main`、`develop`、启动时所在仓库或其他日常分支继续。

从 .gitmodules 解析基础设施 submodule 的实际相对路径，保存为 PowerShell 变量 $submodulePath；不要假设路径一定是 vendor/suanhai-team-external-expression-infrastructure。若 submodule 尚未初始化，只能在消费端工作区干净且已确认隔离后执行 `git submodule update --init --recursive -- $submodulePath`；禁止使用 `--remote`。执行：
    $infra = Join-Path (Get-Location) ($submodulePath -replace '/', '\')
    $gitlinkHead = (git ls-tree HEAD -- $submodulePath).Split()[2]
    $gitlinkIndex = (git ls-files --stage -- $submodulePath).Split()[1]
    $submoduleHead = (git -C $infra rev-parse HEAD).Trim()
    git -C $infra status --porcelain

父仓 HEAD gitlink、index gitlink 和 submodule HEAD 必须先互相一致，submodule 工作区必须干净。然后确认当前父仓分支是隔离测试分支；若不是且工作区干净，先请求用户同意创建 `codex/e2e-html-production-YYYYMMDD`，不要直接在 `main`、`develop` 或日常分支继续。

如果三者不一致，或当前 gitlink 不是 `$expectedInfrastructureCommit`，先在已确认的隔离测试分支执行受控候选更新：
    git -C $infra fetch origin codex/feat-html-production-workflow
    git -C $infra cat-file -e "$expectedInfrastructureCommit^{commit}"
    git -C $infra checkout --detach $expectedInfrastructureCommit
    git add -- $submodulePath
    git diff --cached --submodule

核对暂存区只有该 submodule gitlink 变更后，向用户展示旧 SHA、新 SHA 和 `git diff --cached --submodule`，等待用户明确确认再创建仅含 gitlink 的本地测试提交。拒绝确认则停止。测试父仓分支绝不推送。完成后父仓 HEAD gitlink、index gitlink、submodule HEAD 必须完全等于候选 SHA；若远程候选分支不能获取该完整 commit，则停止，不猜测或改用最新 `main/develop`。

## 1. 验证固定版本能力

从 $infra/manifest.yml 检查 repository、schema_version，并确认以下能力登记且入口存在：
- expression.task-loop
- expression.task-record
- html.project-report-v1
- html.semantic-components-v1
- html.materialize
- expression.html-production

确认页面模板 index.html 有样式和语义组件插槽，组件包有 package.yml、index.yml、组件契约及组件模板。

若任一能力不存在，说明候选版本不完整。停止并返回当前 submodule SHA 和缺少能力，不得绕过检查或修改候选 submodule 内容。

如果测试机有 Ruby，执行 ruby "$infra/scripts/validate_manifest.rb"；没有 Ruby 就记录 Manifest 官方校验未执行，不能写成通过。

执行消费端 submodule 预检：
    py -3 "$infra/tools/submodule-preflight/submodule_preflight.py" --root . --path $submodulePath
预检中除 `remote_matches_expected: warn` 之外任何失败都要停止，不绕过版本、URL 或工作区检查。若稳定 `origin/main` 尚未包含短期测试候选，记录这一个 drift warning；只有前述精确候选 SHA 已从指定短期分支成功获取且父仓 gitlink 三方一致时才继续。不能把该警告写成稳定发布或 main 已更新。

## 2. 创建合成来源和测试任务

确认 context、tasks、reports 目录存在；缺少时停止并报告，不自行迁移或创建目录。

保存任务工具路径并创建 mode: test 任务：
    $taskTool = "$infra/harness/task-loop/scripts/task_loop.py"
    $created = py -3 $taskTool --root . create --test --title "HTML 基础设施端到端合成测试" --request "验证模板、语义组件、任务循环和离线资源，不代表真实项目页面" | ConvertFrom-Json
    $taskId = $created.id

只在消费端创建唯一的合成测试来源，避免重复测试覆盖旧材料：
    $sourcePath = "context/e2e-html-test/$taskId/source.md"
    if (Test-Path -LiteralPath $sourcePath) { throw "合成来源已存在；停止以免覆盖：$sourcePath" }
    New-Item -ItemType Directory -Force (Split-Path $sourcePath) | Out-Null
    Set-Content -LiteralPath $sourcePath -Encoding utf8 -Value @"
# HTML E2E synthetic source

This file is synthetic test input only. It is not a project fact and must not be published.
"@

执行 show $taskId，取得当前 version 后保存为 $version，再 brief：
    $task = py -3 $taskTool --root . show $taskId | ConvertFrom-Json
    $version = $task.version
    py -3 $taskTool --root . brief $taskId --expect-version $version --audience "内部测试者" --purpose "验证 HTML 基础设施消费端流程" --scope "只做项目无关的合成 HTML 页面和资源检查" --output "reports/$taskId" --acceptance "页面离线可打开、选中组件已装配、资源路径闭合、review 和 validate 通过" --source $sourcePath

brief 后再次 show。向用户确认本次是内部合成测试、不使用真实项目事实、不对外发布。等待用户给出实际确认原话，不能自己编造或用示例代替。

收到用户确认后，再次 show 取得最新 version 并执行 align：
    $task = py -3 $taskTool --root . show $taskId | ConvertFrom-Json
    $version = $task.version
    py -3 $taskTool --root . event $taskId --expect-version $version --type align --note "合成测试目标、来源、输出根和完成标准已由测试者确认" --user-quote "用户刚刚实际给出的确认原话"

align 后再次 show，使用最新 version 执行 start：
    $task = py -3 $taskTool --root . show $taskId | ConvertFrom-Json
    $version = $task.version
    py -3 $taskTool --root . event $taskId --expect-version $version --type start --note "开始执行已确认范围内的 HTML 消费端测试" --next-action "完成物料化、页面检查并等待评审"

核对 tasks/$taskId/task.json 中 infrastructure_commit 等于 submodule SHA；不要手改 task.json。

## 3. 物料化 dry-run

组件包 ID 与语义组件 ID 不同。组件包使用 --component-package-id，语义组件使用重复的 --component-id。先运行 dry-run，不得加 --apply：
    $dryRun = py -3 "$infra/tools/html-materialize/materialize_html.py" --root . --submodule-path $submodulePath --task-id $taskId --template-id html.project-report-v1 --component-package-id html.semantic-components-v1 --component-id content.summary --component-id status.phase --component-id status.metric --component-id evidence.claim --component-id action.next-step --source-id synthetic-html-e2e | ConvertFrom-Json
    $dryRun | ConvertTo-Json -Depth 20

确认 mode 为 dry-run、没有写入，output 为 reports/$taskId/v001，commit 与 submodule SHA 一致，would_write 是完整清单，plan_sha256 和 task_record_version 存在，且无冲突。

把输出路径、基础设施 SHA、写入清单、plan_sha256 和 task_record_version 展示给用户，等用户明确确认后再 apply。

## 4. apply 和最小合成内容

用户确认后，使用同样参数运行 apply，并传入 --expect-plan-sha256 $dryRun.plan_sha256 和 --expect-task-version $dryRun.task_record_version。不要更改模板、组件、来源或 submodule 参数：
    py -3 "$infra/tools/html-materialize/materialize_html.py" --root . --submodule-path $submodulePath --task-id $taskId --template-id html.project-report-v1 --component-package-id html.semantic-components-v1 --component-id content.summary --component-id status.phase --component-id status.metric --component-id evidence.claim --component-id action.next-step --source-id synthetic-html-e2e --apply --expect-plan-sha256 $dryRun.plan_sha256 --expect-task-version $dryRun.task_record_version

按完整 would_write 清单检查输出；模板 README.md、template.yml、LICENSE、NOTICE 也可能被复制，不要擅自删除。

编辑前按 materialization.json 的 files 清单核对基线 SHA-256。然后将标题换成“HTML 基础设施端到端测试”，填入五个已选语义组件的合成文本，替换所有可能被误认为事实的占位内容。

创建 reports/$taskId/v001/sources.yml，登记 id synthetic-html-e2e，引用 `$sourcePath`，注明仅内部合成测试、无发布授权；更新该目录 README，记录 mode、基础设施 SHA、模板 ID、组件包 ID、语义组件 ID。

编辑后不得再次对同一目录 apply。若需修改，通过 task-loop feedback 创建新修订和 v002，不覆盖 v001。materialization.json 是初始物料化基线；编辑 index.html 后其哈希变化是预期的，未编辑共享 CSS、组件包和元数据应保持基线哈希。

## 5. 离线资源和人工页面检查

执行并保存：
    Get-ChildItem -Recurse -File "reports/$taskId/v001"
    $externalRefs = rg -n -g "*.html" -g "*.css" 'href=["'']https?://|src=["'']https?://|url\(\s*["'']?https?://|//cdn' "reports/$taskId/v001"
    $rgExit = $LASTEXITCODE
    if ($rgExit -eq 0) { $externalRefs; throw "发现远程运行时资源，停止并报告" }
    if ($rgExit -gt 1) { throw "rg 检查器执行失败，退出码：$rgExit" }
    git diff --check

只对 HTML/CSS 搜索运行时外链，README 和许可证中的普通链接不算页面资源；相对路径的本地 `@import` 可以保留，但目标文件必须存在。PowerShell 中 `rg` 退出码 0 表示发现匹配、1 表示没有匹配（符合预期）、大于 1 表示检查器错误。确认 index.html 有 content.summary、status.phase、status.metric、evidence.claim、action.next-step 五个 data-component；CSS 和资源都是相对路径且目标文件存在；无 CDN、远程字体、远程图片和运行时网络依赖。

本地浏览器打开 reports/$taskId/v001/index.html，检查桌面、手机和 A4 打印预览。没有浏览器或截图时明确记录 not-run / 浏览器检查未执行，不能把静态检查说成视觉验收。截图只能存放仓库外临时目录。

## 6. review 和 validate

页面检查后先 show 取得最新 version，再登记目录评审并验证：
    $task = py -3 $taskTool --root . show $taskId | ConvertFrom-Json
    $version = $task.version
    py -3 $taskTool --root . event $taskId --expect-version $version --type review --note "HTML E2E 合成页面已物料化；已记录静态资源、离线路径和浏览器检查结果" --artifact "reports/$taskId/v001" --next-action "等待测试负责人评审，不执行发布"
    py -3 $taskTool --root . validate $taskId

本轮停在 review，不自动 complete，不记录发布授权。

## 7. 最终回传

不能只说“成功”，请返回：
- 测试机系统、Agent/模型、消费端绝对路径和分支；
- 父仓 HEAD、submodule 路径、gitlink、submodule HEAD 和基础设施 SHA；
- TASK_ID、任务状态和生成目录；
- Manifest、submodule 预检、任务 create/brief/align/start、dry-run、apply、组件插入、离线资源、report.yml/materialization.json、review、validate 的逐项结果；
- 桌面、手机、打印检查分别为 pass、fail 或 not-run；
- 实际关键命令、plan_sha256、task_record_version；
- git status --short --branch 和 git submodule status --recursive 摘要；
- 未解决问题；
- 是否提交/推送。必须明确写“未推送”；若创建本地 gitlink 测试提交，列出 SHA 和内容。

测试结果返回后等待维护者审核，不把本次测试自动升级为发布授权。
