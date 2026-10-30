# 可直接转发给 Agent 的提示词：接入既有仓库

请在**当前已存在的 Git 仓库根目录**执行一次“接入 Suanhai 团队对外表达基础设施”的工作流。本仓库没有采用 Suanhai 公共小组资产模板。你的目标是将基础设施作为固定版本的 Git submodule 接入，并在本仓根 `AGENTS.md` 安装消费端总 Harness，使之后在本仓工作的 Agent 能从本仓规则发现和路由基础设施能力。

这是一段一次性接入提示词：它授权你在限定本地范围内完成首次接线。接入后，日常任务由本仓根 `AGENTS.md` 和父仓固定的 submodule Manifest 路由，不需要重复发送本提示词。这里的“自动”指 Agent 客户端启动时会读取根 `AGENTS.md` 且 submodule 已初始化；若客户端不读取该文件，需要使用客户端支持的指令入口显式引用它，这不是后台自动执行。升级基础设施版本时走本仓已接入的 `consumer.submodule-update` 工作流。

## 固定来源

- 基础设施仓库：`https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git`
- 稳定 ref：`refs/heads/main`
- 默认 submodule 路径：`vendor/suanhai-team-external-expression-infrastructure`
- 接入前工作流入口：`https://raw.githubusercontent.com/suanhaitech/suanhai-team-external-expression-infrastructure/<已核对的完整commit>/workflows/infrastructure-adoption/ENTRYPOINT.md`
- 接入前工作流说明：`https://raw.githubusercontent.com/suanhaitech/suanhai-team-external-expression-infrastructure/<已核对的完整commit>/workflows/infrastructure-adoption/WORKFLOW.md`

从网络读取入口时，先从稳定分支解析完整 commit SHA，再将它填入以上 URL 的版本位置，读取该不可变版本的入口；确认主机、组织和仓库路径与上面一致。长期版本必须锁定同一个完整 40 位 commit。若该工作流还未发布到稳定分支，说明来源版本未发布并停止；不得暗中改用未知分支或短 SHA。

仅当此工作流已进入基础设施仓库稳定 `main`，且该固定版本的 Manifest 已注册 `consumer.infrastructure-adoption` 后，才将本提示词转发给小组负责人。`develop` 或短期分支上的内容仍是待验证版本，不作为组长的通用接入入口。

## 授权范围

发送本提示词并允许你修改当前工作区，即授权你在本流程内添加基础设施 submodule、更新 `.gitmodules` 和父仓 gitlink、在根 `AGENTS.md` 增补共享 Harness。先审计并报告计划，然后可直接执行，无须为相同范围再次询问。除非我另行明确授权，不得：

- 删除、覆盖、重排现有规则或将本仓迁移成公共模板结构；
- 修改项目事实、来源、任务、报告、评审、CI 以外文件或 submodule 内文件；
- 使用 `git submodule update --remote` 或自动跟随远端；
- commit、push、创建 PR、合并、部署或发布；
- 读取、输出或保存凭据、token、私钥或本机敏感信息。

## 执行步骤

1. 确认当前目录就是父仓根目录。读取根 `README.md`、`AGENTS.md`（不存在则记录），运行：

   ```powershell
   git status --short --branch
   git branch --show-current
   git remote  # 只列出远端名称，不读取 URL
   git rev-parse --show-toplevel
   ```

   工作区脏、存在未解决合并或不是仓库根时停止，不清理现场。

2. 检查默认目标路径、`.gitmodules` 和已有 submodule。路径冲突或同一路径配置了不同 URL 时停止。若基础设施已经以正确 URL 和 gitlink 接入，不重复新增，但继续核对其是否已初始化、HEAD 是否等于 gitlink、工作区是否干净，并继续第 5 步确保根 Harness 已安装；缺少 Harness 时按本提示词授权完成预览与安装。若父仓已记录 gitlink、但本机尚未初始化 submodule，在目标路径无冲突且工作区干净时运行 `git submodule update --init --recursive -- <实际路径>`，然后核对实际 HEAD 与父仓 gitlink 一致；这只恢复仓库锁定版本，不升级版本。

3. 运行以下只读命令获取稳定候选：

   ```powershell
   git ls-remote https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git refs/heads/main
   ```

   验证返回唯一完整 40 位 SHA，将它记为“工作流来源 SHA”。向我报告该 SHA、URL、路径、当前分支、计划修改的 `.gitmodules`/gitlink/`AGENTS.md` 和检查计划；本提示词已授权这些限定本地变更，无须等待第二次确认。网络失败、结果为空/不唯一或 SHA 无效时停止，不猜测版本。使用工作流来源 SHA 读取不可变版本的 `manifest.yml`，确认它登记了 `consumer.infrastructure-adoption` 且入口路径正确，再读取同一 SHA 下的工作流入口和说明；任一文件缺失或 Manifest 未登记该能力，停止。若本仓尚无正确 gitlink，工作流来源 SHA 同时用作新 submodule 的固定 SHA；若已有正确 gitlink，则保留原 SHA，绝不把工作流来源 SHA 当成升级目标，后续 Manifest 和 Harness 工具都从现有固定版本读取。

4. 遵从本仓分支治理。已有规则时按规则操作；没有分支规则且当前在稳定分支时，自动创建本地短期分支：先执行 `git switch -c codex/chore-infrastructure-adoption`；若名称已占用，改用 `codex/chore-infrastructure-adoption-YYYYMMDD`，仍冲突则追加递增序号。不直接改稳定分支。**仅在尚未接入 submodule 时**，接入参数通过只读检查后运行：

   ```powershell
   git submodule add https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure.git "<实际路径>"
   git -C "<实际路径>" cat-file -e "<已解析的完整SHA>^{commit}"
   git -C "<实际路径>" checkout --detach <已解析的完整SHA>
   git add -- "<实际路径>"
   ```

   若目标对象在本地不存在，只可从已核验的预期远端获取该确切 SHA 并验证后继续；获取失败则停止并报告。若 `git submodule add` 已留下部分 .gitmodules、目录或 index 变化，保留并报告这些状态，不擅自删除或回滚。`git add` 只暂存父仓 gitlink，不提交。

5. 从当前固定的 submodule Manifest 确认 `consumer.infrastructure-adoption-harness` 已注册，且类型和入口正确。若本轮新接入的稳定版本未注册该工具，停止说明该基础设施版本尚不兼容。若仓库原本已有的固定版本缺少此工具，停止并报告；不要自动升级 gitlink 或从远端复制工具，负责人需另行授权 `consumer.submodule-update` 后再恢复本流程。不得手工复制 Harness 替代工具。

   先做只读预览：

   ```powershell
   # Windows PowerShell
   py -3 "<实际路径>/tools/infrastructure-adoption-harness/install_harness.py" --root . --submodule-path "<实际路径>" --dry-run

   # Linux/macOS
   python3 "<实际路径>/tools/infrastructure-adoption-harness/install_harness.py" --root . --submodule-path "<实际路径>" --dry-run
   ```

   向我展示 JSON 中的 `planned_harness` 完整内容、`planned_diff`、`plan_sha256`、`agents_action`、固定 SHA 和将修改的文件。以本提示词授予的本地修改权限，立即以相同参数运行并添加 `--apply --expect-plan-sha256 <本次预览的 plan_sha256>`，不用等待第二次确认。工具会重新计算计划摘要；若原文件、路径或 gitlink 在审阅后发生变化就拒绝写入。工具只会在本仓根创建或增补 `AGENTS.md`，不覆盖已有规则，不修改其他项目文件，不暂存、提交、推送或改动 submodule。

   若标记已成对存在且内容一致，工具报告 `unchanged`；若标记重复、残缺、顺序错误或内容不同，工具会拒绝修改。不得绕过工具手工合并。Agent 客户端不读取根 `AGENTS.md` 时如实报告；只有负责人同意且客户端存在明确指令入口时，才添加最小指针，不复制完整 Harness。

6. 读取固定 submodule 内的 `manifest.yml`、`docs/consumer-repository-bootstrap.md`、`docs/submodule-consumer-versioning.md` 和接入工作流入口。检查所有能力入口与 `uses` 引用；只按 Manifest 路由。

7. 提交前执行本地核对：
   - `git ls-files --stage -- <实际路径>` 显示 `160000` 和本轮解析的 SHA；
   - submodule HEAD 等于父仓 index 中 gitlink，submodule 自身干净；
   - `.gitmodules` 只有正确路径和 HTTPS URL；
   - 原 `AGENTS.md` 内容保留，新标记只出现一次；
   - `git diff --check` 通过，改动限于预期接入文件。

   新 gitlink 尚未进入父仓 HEAD 时，完整 preflight 会因 HEAD 没有 gitlink 而失败，这是提交前的预期状态。不得为了通过它而擅自提交。可运行 Manifest 校验器；环境缺 Ruby 时报告未执行。

8. 只有我单独授权 commit 且父仓提交已包含 gitlink 后，才运行完整 `consumer.submodule-preflight`。网络明确不可用时可增加 `--skip-remote` 并注明远端未知；不能跳过本地 gitlink、HEAD、对象或工作区错误。commit、push、PR、合并和发布分别授权。

9. 收口报告父仓路径和分支、URL、固定 SHA、变更文件、Manifest 和检查结果、尚待处理事项及未执行的外部动作。不要把本地接线成功说成项目事实验收或发布授权。

完成后，只要 submodule 已初始化且 Agent 客户端会读取本仓根 `AGENTS.md`，我就可以直接在本仓提出任务，由本仓 Harness 按固定 Manifest 路由共享能力；新 clone 时按父仓 gitlink 恢复固定版本。以后发现远端新版本只作为候选，升级走 `consumer.submodule-update`，不再运行初次接入提示词。
