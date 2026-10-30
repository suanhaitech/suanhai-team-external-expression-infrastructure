# 小组资产仓：从 GitHub 模板到新机器初始化

本流程适用于项目小组、科研小组等小组。成员的入口是公开模板仓 `https://github.com/suanhaitech/suanhai-team-group-asset-template`；基础设施是小组资产仓已经配置的固定 submodule。成员不用先克隆基础设施仓，不用手工添加 submodule，也不用再次铺设模板。

模板根目录提供标准文件和空白上下文，`.gitmodules` 提供基础设施 HTTPS URL 与路径，父仓 gitlink 固定实际使用的基础设施 commit。版本事实只在 gitlink 中维护，不在 README 或配置文件再保存一份版本锁。

## 一、组长的 Agent 代办入口

组长可将位于 `workflows/` 的[创建并初始化提示词](../workflows/group-asset-repository/CREATE_AND_INITIALIZE.md)全文发送给 Agent，在必要时补充小组名称、仓库短名和本机父目录。Agent 先检查 `gh` 登录和本机工具环境；组织建仓权限以 GitHub Template Generate API 的实际结果为准。成功后递归克隆、核验 gitlink，并按新仓根规则调用初始化 Harness。仓库默认为 private；初始化记录先留在本地给组长审阅，不自动提交或推送。

详细的授权边界、失败处理和新机器测试步骤见[小组资产仓代建与初始化流程](group-asset-repository-create-and-initialize.md)。Agent 无法访问目标目录、缺少工具或没有组织建仓权限时，应停止报告；组长可以改用下面的手工自助路径。

## 二、成员手工自助路径

### 1. 本机条件

- Git，可以从本机访问本小组 GitHub 仓库和公开基础设施仓；私有小组仓按 GitHub 的正常方式认证。
- Python 3.10+，Windows 可使用 `py -3`，Linux/macOS 使用 `python3`。只有 Git 已可用时不能声称 Python 工具也能运行。
- 一个能够在小组仓根目录读取文件、使用本地工具和保存上下文的 Agent 客户端。客户端若不自动读取 `AGENTS.md`，采用下面的兼容提示。

这些条件也必须在 Agent 的工具执行环境中成立。普通终端能运行 Python，不代表客户端沙箱中的解释器也可用；先在 Agent 环境核对版本。若工具环境缺少解释器，保留诊断并修复对应客户端的运行条件后再执行校验；不要把手工检查记成脚本通过，也不要为此静默安装软件或改系统配置。

Windows 检查：

```powershell
git --version
py -3 --version
```

Linux/macOS 检查：

```sh
git --version
python3 --version
```

### 2. 从模板创建自己的小组仓

打开模板仓，点击 **Use this template → Create a new repository**，选择有权限的 GitHub 所有者，填写小组资产仓名称并确认可见性。小组仓是独立仓库；小组事实、任务和产物都在这里维护。模板中不包含已确认的具体小组或项目事实。

基础设施维护者发布模板时已经设置好 submodule；不要为了使用模板先克隆基础设施主仓。模板仓未来的文件更新不会自动覆盖已经生成的小组仓。

### 3. 递归克隆小组仓

Windows PowerShell，替换本组仓库 URL 与本机目标目录：

```powershell
$groupAssetsUrl = '<本小组仓库URL>'
$groupAssetsDirectory = Join-Path (Get-Location) 'my-group-expression-assets'
if (Test-Path -LiteralPath $groupAssetsDirectory) { throw '目标目录已存在，请选择新目录' }
git clone --recurse-submodules $groupAssetsUrl $groupAssetsDirectory
if ($LASTEXITCODE -ne 0) { throw '克隆未完成；根据 Git 输出检查网络、权限或固定版本' }
Set-Location -LiteralPath $groupAssetsDirectory
```

Linux/macOS：

```sh
git clone --recurse-submodules '<本小组仓库URL>' ./my-group-expression-assets
cd ./my-group-expression-assets
```

确认 clone 成功后再进入 Agent。普通 clone 漏掉 submodule 时，不需要重新 clone 或重新 add；根 `AGENTS.md` 会先识别固定依赖缺失。只读调查只诊断，用户提出初始化请求后可恢复父仓已经配置的版本：

```text
git submodule update --init --recursive -- vendor/suanhai-team-external-expression-infrastructure
```

恢复命令可能下载固定对象，不使用 `--remote`，不会选择远端最新分支。父仓配置或 gitlink 缺失时属于接入异常，不用恢复命令猜测版本；已有 submodule 脏工作区或 HEAD 漂移时先报告并保留现场。

### 4. 在资产仓根目录启动 Agent

输入：

> 初始化小组资产仓。

如果客户端不自动加载根 `AGENTS.md`，使用兼容提示：

> 请先读取本仓根目录 README.md 和 AGENTS.md，再引导我初始化小组资产仓。

“进行项目初始化”也是可接受的自然用语。Agent 应先判断本次是小组首启，还是在已初始化的小组中新增/完善一个项目；不能默认小组只有一个项目，也不能把整个小组身份覆盖为某个项目。

Agent 先核对固定依赖，再从 Manifest 找到 `consumer.group-asset-onboarding` 的入口。完整流程保存在 `harness/group-asset-repository/ENTRYPOINT.md`，这里不维护另一套访谈规则。

## 三、新机器端到端测试手册

测试目标是证明：成员从 GitHub 模板创建自己的仓库，递归克隆后，Agent 能按根规则进入初始化访谈并保存可续接的进度。脚本文件存在或复制成功不能代替这个成员交互测试。

### A. 核对生成仓的结构与固定版本

在全新的测试仓 clone 根目录运行：

```text
git status --short --branch
git ls-tree HEAD vendor/suanhai-team-external-expression-infrastructure
git config --file .gitmodules --get-regexp "^submodule\..*\.(path|url)$"
git submodule status --recursive
git -C vendor/suanhai-team-external-expression-infrastructure rev-parse HEAD
git -C vendor/suanhai-team-external-expression-infrastructure status --porcelain
```

核对以下证据：

- 父仓 `ls-tree` 条目是 `160000 commit <SHA>`，而不是普通目录；
- `.gitmodules` 路径为 `vendor/suanhai-team-external-expression-infrastructure`，URL 指向公开基础设施仓的 HTTPS 地址；
- submodule `HEAD` 等于父仓 gitlink；记录完整 SHA，不把某次固定测试 SHA 写回模板文档；
- `submodule status` 没有 `-`（未初始化）、`+`（HEAD 漂移）或 `U`（冲突）前缀；
- submodule 工作区干净；Manifest 声明 `consumer.group-asset-onboarding` 和实际可调用入口；
- 具有根 `README.md`、`AGENTS.md`、`context/initialization.md`、`context/group/`、`context/projects/` 以及 `tasks/topics/reports/series/courses/books/tools/reviews`；没有新建 `works/`，没有伪造具体任务或作品。

在 Windows 用 `py -3`、Linux/macOS 用 `python3` 执行已声明的 `consumer.submodule-preflight`。远端更新仅作提示；网络失败可通过 `--skip-remote` 核对本地固定版本并明确远端未知。其他本地错误不能忽略。

### B. 验证只读首启

启动一个未继承旧会话的新 Agent，输入：

> 请只读检查这个小组资产仓的初始化状态、基础设施版本和可用初始化入口，不修改文件，不创建任务。

通过条件：Agent 能找到根规则、固定 Manifest、初始化 Harness 和进度文件；说明尚待初始化的信息；不把 `_template/` 当项目，不推断成员身份，不写文件。若客户端未自动加载规则，记录限制并使用兼容提示重试，不把后者记成自动加载通过。

另用一个普通 clone（不递归）覆盖恢复分支：只读请求应只报告缺少 submodule；随后明确说“初始化小组资产仓”，Agent 可执行固定版本恢复命令，再读取 Manifest。它不得执行 `submodule add` 或 `update --remote`。记录恢复前后 gitlink、submodule HEAD 和命令输出。

### C. 分轮访谈并保存初始化进度

输入“初始化小组资产仓”，提供当前使用者工作称呼与角色、小组名称、定位、仓库维护责任和适合记录的来源边界。观察 Agent 是否一次询问少量关键问题，复用已有答案，先形成候选稿，再根据真实回答逐项记录确认与待确认事项。

检查 `context/group/` 和 `context/initialization.md`：小组共享身份不等于本次操作者；未知内容保持未知；核对依据、日期和下一步可追溯。不要使用真实秘密或未经许可资料作为测试输入；使用演练数据时必须明确标为演练，不能把它提升为真实小组事实。

### D. 覆盖零项目与多项目

使用独立测试仓或明确分开的测试轮次，避免把演练场景混入真实上下文：

- 零项目：用户确认暂未登记项目时，Agent 保留空项目索引，仍可完成小组层面的初始化，不为通过流程虚构项目。
- 多项目：用户分别提供两个项目时，Agent 为它们建立不同 `context/projects/<project-id>/`，独立记录目标、状态、来源和边界；不把某一项目的事实写成全组事实。
- “项目初始化”别名：小组已经初始化后，说“初始化项目”应先定位要新增或完善的项目，不重置小组初始化。

初始化达到当前工作所需即可收口，不要求所有事实都已经确定。未确认项继续留在进度文件和具体上下文中。

### E. 新会话与另一台机器续接

关闭会话，在同一目录启动新 Agent，输入“继续初始化小组资产仓”。它应读取已有进度，只询问缺项、变化和本轮处理对象，不重问全部内容，不覆盖已确认身份。

经负责人审阅并按实际授权提交、推送父仓初始化记录后，在另一台机器再次递归克隆本小组仓。新 clone 应获得相同 gitlink、已同步上下文和初始化状态；重新确认当前操作者角色，但不把新操作者写成小组身份。未提交或未推送的文件不会凭空跨机器出现，任务号或初始化口令也不传输文件。

### F. 收口与后续真实任务

最后运行 `git diff --check`、`git status --short` 和 submodule 工作区检查，确认只有预期的父仓上下文改动。初始化不需要为了测试而生成业务任务；用户随后提出真实需求，才进入 Manifest 中的任务循环。报告类产物进入 `reports/<任务编号>/v001/`，系列、课程和书籍各自归档。

每次测试记录：日期、操作系统、Git/Python 版本、Agent 客户端及规则加载方式、模板仓提交、父仓提交、完整 gitlink、输入与实际行为、修改文件、通过/失败/未执行项、需要修复的问题。没有实际运行的客户端、平台或交互步骤必须标记“未执行”；不能因为某个自动化检查通过就声称整条真人交互已通过。

## 三、维护者备用路径：从空仓铺设

本节只服务模板发布、工具回归和经过确认的特殊建仓，不是普通成员主路径；已有仓迁移另设任务，不能覆盖现有 README、AGENTS 或上下文。

维护者在全新空 Git 父仓中添加公开基础设施 submodule，选择包含本能力的已验收完整 commit，显式 checkout 该 commit 并暂存 `.gitmodules` 与 submodule 路径。父仓 index 的 gitlink 必须与 submodule HEAD 一致。然后从固定 submodule 运行铺设工具：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/tools/group-asset-bootstrap/materialize_template.py --root . --dry-run
py -3 vendor/suanhai-team-external-expression-infrastructure/tools/group-asset-bootstrap/materialize_template.py --root . --apply
```

Linux/macOS 将解释器替换为 `python3`。工具默认只预览，`--apply` 只创建缺失文件，已有相同文件保持不变、不同内容整体拒绝；不添加/升级 submodule，不写小组事实，不提交/推送。普通写入异常会尝试清理本次文件和空目录，清理失败报告残留；断电、强制终止和并发修改不具备事务保证。

尚无父仓首次提交时，铺设工具可核对 index gitlink 与 submodule HEAD；日常版本预检不能读取不存在的父仓 HEAD，不为通过它擅自提交。GitHub 从独立模板创建的小组仓已有初始提交，采用正常首启流程即可。
