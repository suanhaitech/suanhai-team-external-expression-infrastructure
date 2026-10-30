# `consumer.infrastructure-adoption` 工作流 Harness

这是既有仓库首次接入 Suanhai 对外表达基础设施的消费端执行入口。目标是把基础设施固定为 submodule，并将必要的消费端总 Harness 安装到父仓库根目录，使未来会话可以从本仓规则发现和使用共享能力。

## 入口前提

你正在目标父仓库根目录工作。先读取根 `README.md`、`AGENTS.md`（如存在）、`.gitmodules`（如存在）、本仓分支与权限约定，并运行：

```powershell
git status --short --branch
git branch --show-current
git remote
git rev-parse --show-toplevel
```

读取本工作流 `WORKFLOW.md`。submodule 尚未接入时，不得声称已读取它内部的 Manifest 或文档。接入成功后，再读取固定版本的 `manifest.yml`、`docs/consumer-repository-bootstrap.md`、`docs/consumer-repository-harness-v0.1.md`、`docs/submodule-consumer-versioning.md` 及本入口。

## 阶段 1：只读审计

检查当前目录确为父仓库根目录，父仓及相关 submodule 工作区干净、没有未解决合并；确认接入路径没有被文件、目录或其他 submodule 占用，并检查 `.gitmodules` 是否已有同一 URL 或路径。只列出远端名称，不读取或输出可能包含凭据的 URL。

以下情况停止并报告，不做清理或覆盖：工作区脏、合并冲突、路径/URL 冲突、已有错误配置、当前目录不是仓库根、或用户没有授权本地文件修改。如果基础设施已通过正确 URL 和 gitlink 接入，则不重复添加：submodule 已初始化且父仓 HEAD 已记录 gitlink 时，只有固定版本 Manifest 确实注册 `consumer.submodule-preflight` 且入口存在，才运行该工具；若该旧版没有预检能力，改用只读 Git 查询核对 `.gitmodules`、index gitlink、submodule HEAD 与工作区，不调用不存在的能力。若父仓只有已暂存的 gitlink，则按阶段 5 做 index 核对；若父仓已有 gitlink 但 submodule 尚未初始化，按父仓规则恢复固定版本后再检查。版本变更另走 `consumer.submodule-update`。不论 submodule 是本轮新增还是已正确存在，都继续用阶段 4 工具核对根 Harness；若缺少则按本提示词授权预览并安装。固定版本若缺少 Harness 安装工具，阶段 4 会停止并说明需要另行更新。既有规则始终保留，不能假设已有 submodule 就表示 Harness 完整。

## 阶段 2：确认参数和版本

默认候选：

```text
URL: https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git
路径: vendor/suanhai-team-external-expression-infrastructure
稳定 ref: refs/heads/main
```

启动提示词从稳定 `main` 解析唯一完整 40 位 SHA，以该不可变版本读取本工作流。若尚未接入 submodule，该 SHA 是新 gitlink 的固定版本；若已有正确 gitlink，则保留其现有 SHA，从该版本读取能力 Manifest 和 Harness 安装工具。报告工作流来源 SHA 与实际固定 SHA，不把 `main` 候选用于升级。此工作流入口与提示词授权 Agent 在限定范围内完成本地接入，不需再次等待路径和 SHA 确认；路径或来源有歧义、或分支治理不允许当前操作时停止询问。分支名、“最新”或短 SHA 不能作为版本锁。遵守父仓既有分支治理；没有分支规则且当前处于稳定分支时，自动创建本地短期分支（优先 `codex/chore-infrastructure-adoption`，重名则附加日期），不直接修改受保护分支。

接入授权不包括提交、推送、PR、合并、部署或发布。每种外部副作用分别需要授权。

## 阶段 3：添加并固定 submodule

若尚未接入，确认工作区干净、路径可用且提示词授权范围匹配后执行：

```powershell
git submodule add https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git "<path>"
git -C "<path>" cat-file -e "<确认的40位SHA>^{commit}"
git -C "<path>" checkout --detach <确认的40位SHA>
git add -- "<path>"
```

如果基础设施已经通过正确 URL 和 gitlink 接入，不要重复运行 `git submodule add` 或改变其固定 commit。只核对路径、URL、gitlink、初始化状态和工作区，然后继续阶段 4。若尚未接入，目标对象不在本地时从指定远端获取已解析的 SHA；获取失败时停止。若 `git submodule add` 已创建部分配置或目录后操作失败，保留现场并报告每项变更，不自行删除或回滚。确认父仓 index 中的条目是 `160000 commit <SHA>`；`.gitmodules` 仅记录路径和 URL。不要复制 submodule 内容，不要使用 `git submodule update --remote`。`git add -- <path>` 只更新父仓 gitlink index，不等于提交授权。

## 阶段 4：用已声明工具预览并安装消费端总 Harness

先确认固定版本 Manifest 显式注册 `consumer.infrastructure-adoption-harness`，且其 `kind`、`path`、`entrypoint` 正确。未注册或入口不存在时停止；不要自动升级现有 gitlink，也不得从远端复制工具或手工复制规则。已有旧版本应另行使用 `consumer.submodule-update` 并经单独授权后，再恢复本流程。工具也会确认 Manifest schema、仓库标识和 Harness 必需的协议文件属于该固定版本。

按消费端实际路径先执行只读预览：

```powershell
# Windows PowerShell
py -3 "./<实际路径>/tools/infrastructure-adoption-harness/install_harness.py" --root . --submodule-path "<实际路径>" --dry-run

# Linux/macOS
python3 "./<实际路径>/tools/infrastructure-adoption-harness/install_harness.py" --root . --submodule-path "<实际路径>" --dry-run
```

向负责人展示工具返回的 `planned_harness` 完整文本、`planned_diff`、`plan_sha256`、目标文件状态、固定 SHA 和预期变更。以本提示词已授予的本地修改权限继续执行相同命令，添加 `--apply --expect-plan-sha256 <本次预览的 plan_sha256>`；工具会重新计算计划摘要；如果文件、submodule 路径或固定 SHA 与审阅时不一致，就拒绝写入。该工具只增补父仓根 `AGENTS.md`，不触碰其他项目文件，不修改 submodule、不暂存、不提交或推送。

工具返回冲突时停止并报告，不得绕过工具手工编辑。没有根 `AGENTS.md` 时工具会新建；有文件时只追加标记段，不得覆盖、重排或删除原规则。标记已成对存在且内容完全一致则保持不变；标记重复、残缺、顺序错误或内容不同则拒绝修改。若 Agent 客户端不自动加载 `AGENTS.md`，如实说明；仅在客户端已有指令入口允许时加入最小指针，不能复制多份完整 Harness。

## 阶段 5：验证接入

读取固定版本 Manifest，确认 schema、仓库名、能力入口和 `uses` 依赖有效。运行可用的 Manifest 校验器；若环境没有 Ruby，报告未执行。

新 gitlink 在父仓首次提交前通常只存在 index，完整 `consumer.submodule-preflight` 会因 HEAD 暂无 gitlink 而失败。此时不得将失败解释成接入错误，也不得为通过检查擅自提交。提交前使用本地核对：

- `git ls-files --stage -- <path>` 显示模式 `160000` 和确认的 SHA；
- submodule `HEAD` 与 index gitlink SHA 一致，submodule 工作区干净；
- `.gitmodules` 中 URL 和路径正确；
- `AGENTS.md` 原内容保留，标记仅出现一次；
- `git diff --check` 通过，改动仅限预期接入文件。

仅当父仓提交已包含 gitlink 后，才运行完整预检：

```powershell
python <实际路径>/tools/submodule-preflight/submodule_preflight.py --root . --path <实际路径>
```

只有明确网络不可用时才可增加 `--skip-remote` 并注明远端未知；不得掩盖本地状态错误。新 clone 中已有 gitlink 但未初始化时，可按父仓规则运行 `git submodule update --init --recursive -- <path>` 恢复固定版本；这不是升级。

## 阶段 6：收口与后续使用

报告父仓路径、分支、基础设施 URL 和固定 SHA、修改文件、Manifest/本地核对/预检结果、是否创建短期分支，以及未执行的 commit/push/PR。接入完成只表示工程接线完成，不代表项目事实已核实、业务上下文已初始化或材料获得发布授权。

接入后，Agent 在父仓根目录工作时由根 `AGENTS.md` 路由共享能力；这依赖 submodule 已初始化，且当前 Agent 客户端会自动读取根 `AGENTS.md`。若客户端不读取该文件，用户需通过客户端支持的入口显式要求遵循它；这不是后台自动执行。后续不再需要首次接入提示词。基础设施更新另走 `consumer.submodule-update`，不自动追随远端。
