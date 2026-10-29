# 通用小组资产仓：从空仓到首次任务

本流程适用于项目小组、科研小组等小组。模板提供相同的起点；身份、项目上下文和实际作品由各组维护。新模板不创建 `works/`，报告产物进入 `reports/`；系列、课程和书籍分别进入对应目录，`topics/` 保存可复用内容。

## 1. 建立空 Git 仓并固定基础设施

前提：安装 Git 与 Python 3.10+，已有用户授权创建本地小组仓，目标目录为空；远程小组仓可后续按授权建立。不要在已有项目或大工仓运行以下新仓步骤。

以下 PowerShell 在准备放置各组仓库的父目录执行。先把 `your-group-expression-assets` 换成实际仓库目录名，把 `<完整40位已验收commit>` 换成包含本模板与铺设能力的完整提交。不要用浮动分支名代替实际固定版本。

```powershell
$groupAssetsDirectory = Join-Path (Get-Location) 'your-group-expression-assets'
$expressionInfraCommit = '<完整40位已验收commit>'

if ($expressionInfraCommit -notmatch '^[0-9a-fA-F]{40}$') { throw '请先填写基础设施的完整 commit' }
if (Test-Path -LiteralPath $groupAssetsDirectory) { throw '目标目录已经存在，请选择新的空目录' }
New-Item -ItemType Directory -Path $groupAssetsDirectory | Out-Null
Set-Location -LiteralPath $groupAssetsDirectory
git init -b main
if ($LASTEXITCODE -ne 0) { throw 'Git 初始化失败' }
git submodule add https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git vendor/suanhai-team-external-expression-infrastructure
if ($LASTEXITCODE -ne 0) { throw '基础设施 submodule 添加失败；保留现场后检查原因' }
git -C vendor/suanhai-team-external-expression-infrastructure checkout --detach $expressionInfraCommit
if ($LASTEXITCODE -ne 0) { throw '目标基础设施 commit 不可用；停止后续铺设' }
git add -- .gitmodules vendor/suanhai-team-external-expression-infrastructure
if ($LASTEXITCODE -ne 0) { throw 'gitlink 暂存失败' }
git submodule status --recursive
```

暂存 gitlink 只建立本地版本关系，不创建提交或推送。模板铺设工具支持此时尚无首次提交的空父仓；日常版本预检则以已有父仓提交为基准，首次提交前用下面的铺设预检核对 index 与 submodule HEAD。

## 2. 发现能力并铺设

先读取固定 submodule 的 `manifest.yml`，确认声明了 `consumer.group-asset-bootstrap` 和 `consumer.group-asset-onboarding`，再读取其入口。若旧版本未声明，停止本次能力调用并选择包含本能力的提交，不能把占位目录当可用能力。

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/tools/group-asset-bootstrap/materialize_template.py --root . --dry-run
if ($LASTEXITCODE -ne 0) { throw '铺设预检未通过' }
py -3 vendor/suanhai-team-external-expression-infrastructure/tools/group-asset-bootstrap/materialize_template.py --root . --apply
if ($LASTEXITCODE -ne 0) { throw '铺设未完成；根据工具输出检查现场' }
git diff --check
git status --short
```

铺设工具只创建缺失的模板文件，相同文件保持不变，存在不同内容时整次拒绝。它不添加或升级 submodule、不填事实、不建立任务、不提交或推送。普通写入异常会尝试清理本次文件和空目录；清理失败会明确报告残留。强制终止、断电和并发修改不具备事务保证，重试前核对现场。

## 3. 由 Agent 引导初始化

在小组仓根目录启动 Agent，输入：

> 请读取本仓 README.md、AGENTS.md 和固定 submodule 的 Manifest。按小组资产仓初始化入口引导我完成身份、工作边界、零到多个项目上下文的初始化；已提供的信息直接复用，未知事实保留待确认。分轮讨论，不创建虚构任务或作品，不提交、推送。

Agent 应区分当前使用者与小组身份，按 `context/initialization.md` 保存进度。小组上下文位于 `context/group/`，项目索引位于 `context/projects/README.md`；每个项目从 `_template/` 复制独立上下文。可以暂时没有项目，不必等所有事实补齐才开始工作。

初始化确认后，由负责人审阅本地差异，按实际授权提交明确文件清单，建立 `develop` 集成分支并配置小组远程；工具和 Harness 不自动代办这些 Git 动作。不要在此文档或 README 维护第二份版本锁，父仓 gitlink 承载版本事实。

## 4. 日常任务与新机器

- 已建立的仓库：`git clone --recurse-submodules <小组仓库URL>`；不要从模板重新建一份。
- 已有 clone 缺 submodule：`git submodule update --init --recursive`，恢复父仓记录的版本。
- 新需求：直接告诉 Agent 受众、目的和期望产出，Agent 先登记任务、讨论关键事项，再制作。
- 续作：告诉 Agent “继续任务 EXPR-…”，先读取已有任务与历史产物，不重建任务。
- 新版本：只读检查并报告更新；升级和回退按 `docs/submodule-consumer-versioning.md` 执行。

模板铺设不是旧仓迁移工具。大工仓等已有仓库应另开迁移任务，先保留历史任务、产物路径和摘要，再按目录职责迁移；不能直接用 `--apply` 覆盖现有 README、AGENTS 或上下文。
