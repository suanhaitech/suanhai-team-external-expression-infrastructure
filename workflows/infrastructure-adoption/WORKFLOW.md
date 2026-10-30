# 既有仓库接入基础设施工作流

状态：implemented / experimental

能力 ID：consumer.infrastructure-adoption

## 目标

让一个已经存在、没有采用 Suanhai 公共小组资产模板的 Git 仓库，在不丢失原有规则和文件的前提下，接入 Suanhai 团队对外表达基础设施，并获得可以长期生效的消费端 Agent Harness。

这条工作流只负责首次接入，不负责创建远程仓库、迁移项目资料、重构为公共模板目录，也不替负责人完成项目上下文或业务任务初始化。

## 适用场景

- 仓库已经存在，负责人希望保留现有目录、CI、分支和根 AGENTS.md；
- 仓库尚无基础设施 submodule，或已正确固定兼容版本但根 Harness 尚未安装；
- 使用者已通过本提示词授权 Agent 添加 .gitmodules 配置、submodule gitlink 和最小 Harness 接入段；
- 基础设施仓库可通过公开 HTTPS URL 获取，目标 commit 可复现。

若已有固定版本未声明 `consumer.infrastructure-adoption-harness` 或缺少其入口，本流程不自动升级该 gitlink，也不从远端复制工具；先单独通过 `consumer.submodule-update` 更新到兼容版本，再恢复本流程。该限制适用于已有旧 gitlink；新接入的版本直接固定到此次从稳定 `main` 解析的 commit。

从公共模板创建新仓库继续使用 consumer.group-asset-create-and-initialize；已存在 submodule 的版本升级继续使用 consumer.submodule-update。本工作流不替代二者。

## 输入

- 既有仓库根目录和当前分支；
- submodule 相对路径：优先沿用既有仓库清晰约定；无约定且默认路径空闲时使用 vendor/suanhai-team-external-expression-infrastructure；
- 基础设施仓库 HTTPS URL；
- 稳定分支 refs/heads/main 上可获取的完整 40 位 commit SHA；
- 既有仓库的分支治理、权限约定及根 AGENTS.md、README、CI 和 Git 状态。

默认路径不是强制模板。若既有仓库已有明确的 vendor、infrastructure 或其他目录约定，沿用该约定；若路径已有用途但不能确定是否可用，停止并询问负责人，不覆盖或移动既有内容。

## 输出

- 父仓 .gitmodules 中的 HTTPS URL 和相对路径；
- 指向明确完整 commit 的 160000 submodule gitlink；
- 父仓根 AGENTS.md 中一段通过已声明工具预览、校验后安装的共享基础设施 Harness；
- Manifest、gitlink、工作区及适用预检的核对结果；
- 未解决的路径冲突、规则冲突和后续升级事项。

## 执行阶段

### 1. 只读审计

确认当前目录是父仓根目录，读取 README、AGENTS.md、.gitmodules（如存在）、分支约定和相关 CI，再检查：

~~~
git status --short --branch
git branch --show-current
git remote
git rev-parse --show-toplevel
~~~

工作区脏、存在未解决合并、目标路径被占用、URL/路径冲突、已有错误配置或当前目录不是仓库根时，停止并报告。不得用 reset、clean 或覆盖写入整理现场。

### 2. 对齐接入参数

本提示词本身授权 Agent 在当前仓库按本工作流修改 `.gitmodules`、submodule gitlink 和根 `AGENTS.md`；不需要再为同一范围逐项等待确认。采用清楚的既有路径；否则使用默认路径。启动提示词从稳定 `main` 解析完整 SHA，以它读取不可变的工作流入口；若此前未接入 submodule，该 SHA 同时作为新 gitlink 的固定版本。若已有正确 gitlink，则保留原固定 SHA，不以 `main` 候选替换它，并从该固定版本读取能力 Manifest 和安装工具。向负责人报告工作流来源 SHA、实际固定 SHA、URL、路径、修改文件和验证计划后继续。若路径、来源、分支策略或授权范围存在实质歧义，仍须停下询问；已有固定版本缺少安装工具时另行授权升级。不能把“main 当前最新”写成已有仓库的版本锁；父仓 gitlink 才是长期使用版本的唯一事实来源。

接入授权不包括 commit、push、PR、合并、部署或发布。每种外部副作用需要分别授权。

### 3. 添加并固定 submodule

遵循父仓既有分支治理。若尚未接入，确认工作区干净、路径可用且本提示词的授权范围匹配后执行：

~~~
git submodule add https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git <path>
git -C <path> cat-file -e <完整SHA>^{commit}
git -C <path> checkout --detach <完整SHA>
git add -- <path>
~~~

如果 submodule 已通过正确 URL 和 gitlink 接入，不要重复运行 `git submodule add`，也不要切换其 commit；只核对路径、URL、gitlink、初始化状态与工作区。若尚未接入，若目标对象不在本地对象库，从预期远端获取已解析的完整 SHA；获取失败时停止并报告。checkout 后必须 git add -- <path> 更新父仓 index 中的 gitlink。核对模式为 160000，SHA 为本轮解析并固定的完整值；.gitmodules 仅记录 URL 和路径。不得复制 submodule 文件或使用 git submodule update --remote。暂存不等于提交授权。

### 4. 通过确定性工具安装消费端 Harness

在固定 submodule 的 Manifest 确认 `consumer.infrastructure-adoption-harness` 已注册，核对其 `kind`、`path` 和 `entrypoint`。若已存在的固定版本未注册该工具或入口不存在，停止报告；不要自动升级 gitlink，也不得手工复制 Harness 代替。由负责人另行授权 `consumer.submodule-update` 后再继续。

先预览并向负责人报告准确计划；本提示词已经授权限定范围内的本地接入，因此无需第二次人工确认：

~~~
Windows PowerShell: py -3 "<实际路径>/tools/infrastructure-adoption-harness/install_harness.py" --root . --submodule-path "<实际路径>" --dry-run
Linux/macOS: python3 "<实际路径>/tools/infrastructure-adoption-harness/install_harness.py" --root . --submodule-path "<实际路径>" --dry-run
~~~

工具校验父仓 `.gitmodules` 的 HTTPS URL、index gitlink、submodule HEAD、工作区状态和固定 Manifest 工具登记；默认只读。Agent 展示返回的完整 `planned_harness`、`planned_diff`、`plan_sha256`、目标文件状态和固定 SHA 后，立即用本次 dry-run 返回的摘要执行 `--apply --expect-plan-sha256 <plan_sha256>`。摘要是防止预览后文件变化的并发保护，不是额外的人为审批；任何计划不一致仍拒绝写入。工具只增补父仓根 `AGENTS.md`，不触碰其他项目文件，不修改 submodule、不暂存、不提交或推送。

工具只操作父仓根 `AGENTS.md`：保留原有规则和顺序；已有相同标记段时保持不变；标记冲突、残缺或重复时拒绝写入。工具不改其他文件、不修改 submodule、不暂存、不提交或推送。冲突时停止，不以手工编辑绕过。

生成的 Harness 让后续 Agent 沿用父仓任务、上下文、作品和评审约定，从固定 Manifest 按 `uses` 路由已声明能力，按需调用共享 workflow、tool、template、skill 或 check；共享能力使用前运行适用的只读预检，更新走 `consumer.submodule-update`。它不是权限沙箱，也不代表专业确认或发布授权。

后续自动路由依赖 submodule 已初始化、Agent 从父仓根工作，且客户端会加载根 `AGENTS.md`。客户端不自动加载时，向负责人报告并按其客户端指令入口选择加入最小指针；不得声称后台自动运行。

没有根 AGENTS.md 时可以创建最小文件并说明其职责。有文件时只追加标记段，不得覆盖、重排或删除原规则。标记已成对存在且内容相同时保持不变；标记重复、残缺或内容冲突时停止交负责人，不自动合并。若当前 Agent 客户端不会自动读取 AGENTS.md，如实报告；只有在客户端现有指令入口可安全引用时才添加最小指针，不复制多份完整 Harness。

### 5. 验证和留痕

接入后读取固定版本 Manifest，校验仓库标识、能力入口和 uses 依赖。运行可用的 Manifest 校验器；环境无 Ruby 时报告未执行。

新 gitlink 在提交前通常只存在于父仓 index。完整 consumer.submodule-preflight 从父仓 HEAD 读取 gitlink，此时运行会因 HEAD 尚无该 gitlink 而失败。这是工具输入前提，不应误报接入失败，也不能为通过检查而擅自提交。

提交前做本地核对：

- git ls-files --stage -- <path> 显示模式 160000 和确认的 SHA；
- submodule HEAD 与父仓 index gitlink 一致，submodule 工作区干净；
- .gitmodules 中路径和 URL 正确；
- AGENTS.md 原内容保留，Harness 标记只出现一次；
- git diff --check 通过，改动仅限预期接入文件；
- 未写入凭据、缓存、本机绝对路径或项目私密材料。

只有父仓提交已经包含此次 gitlink 后，才运行完整 consumer.submodule-preflight。未获提交授权时保留可审阅改动，并如实说明完整预检尚未适用。

### 6. 收口

报告父仓路径和分支、基础设施 URL、固定 SHA、修改文件、Manifest 与本地核对结果、适用的预检结果，以及没有执行的 commit/push/PR。接入完成只表示工程接线完成，不代表项目上下文已确认、专业事实已验收或内容获得发布授权。

## 长期使用规则

接入后的 Agent 从父仓根 AGENTS.md 启动，按本仓规则读取固定 submodule 的 Manifest 并路由已声明能力。新 clone 如果已经有父仓 gitlink、但 submodule 尚未初始化，可在无路径冲突、无本地修改且遵循本仓规则时运行 git submodule update --init --recursive -- <path> 恢复父仓固定版本；这不是升级，也不改变 gitlink。

日常工作不再依赖初次提示词。远端 main 前进只形成候选信号；升级必须另行使用 consumer.submodule-update，在短期分支中验证并由负责人审阅。

## 停止条件

脏工作区、未解决合并、路径或 URL 冲突、无法获得明确 SHA、目标对象不可获取、既有 AGENTS.md 标记冲突、Manifest/入口缺失、用户撤回授权或 Git 命令失败时，停止写入并报告。禁止删除、覆盖或回退未知内容。
