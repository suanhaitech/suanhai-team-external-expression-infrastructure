# 小组对外表达资产仓库 Agent 规则

Agent 工作目录为本仓库根目录。先读取根 `README.md` 与本文件，完成下面的首次启动检查，再读取基础设施文件；不能在 submodule 尚未初始化时声称已经读取 Manifest。下列基础设施路径均位于 `vendor/suanhai-team-external-expression-infrastructure/`。

## 首次启动：先恢复已经配置的固定依赖

本仓应由公开 GitHub 模板仓 `suanhaitech/suanhai-team-group-asset-template` 创建，模板已包含 `.gitmodules` 和固定 gitlink。成员不需要单独克隆基础设施仓，也不需要重新添加 submodule。

1. 用 Git 查询确认当前目录是父仓根目录，检查 `.gitmodules` 中预期路径与基础设施 HTTPS URL，并检查父仓 gitlink 是 `160000` 模式的固定 commit。
2. 如果 Manifest 不存在但路径已登记、gitlink 有效，判断用户请求：只读调查只报告“submodule 尚未初始化”和恢复命令；用户要求“初始化小组资产仓”或“项目初始化”时，恢复固定依赖属于该初始化请求的授权范围，可以执行：

   ```text
   git submodule update --init --recursive -- vendor/suanhai-team-external-expression-infrastructure
   ```

3. 只恢复父仓已经记录的版本，不执行 `git submodule add`、`update --remote`、随意 checkout、配置改写、提交或推送。已存在的 submodule 有修改或 HEAD 漂移时，保留现场并报告，不用恢复命令覆盖已有工作。
4. 如果 `.gitmodules`、预期 URL 或 gitlink 缺失/冲突，说明模板接入异常并停止该能力调用，不猜一个版本自动补建。网络或权限失败时保留结果，不声称已恢复。
5. 恢复后重新核对 submodule HEAD 与父仓 gitlink 一致，再读取 Manifest。Python 工具需要 Python 3.10+；Windows 使用 `py -3`，Linux/macOS 使用 `python3`，不为通过初始化静默安装或改变本机环境。

当前 Manifest 为 schema v2 时，若用户要求“检查或更新基础设施 submodule”，先读取 `consumer.submodule-update` 的 `workflows/submodule-update/ENTRYPOINT.md`；只检查时保持只读，更新时必须展示明确 commit 和变更计划并等待用户确认。不得使用 `git submodule update --remote` 自动跟随远端，也不得直接修改 `main`。

## 固定依赖可用后的读取顺序

1. 根 `README.md` 与本文件；
2. 基础设施 `manifest.yml`；
3. 基础设施 `docs/consumer-repository-bootstrap.md`；
4. 基础设施 `docs/consumer-repository-harness-v0.1.md`；
5. 基础设施 `docs/submodule-consumer-versioning.md`，以及 Manifest 声明的预检能力入口；
6. 本仓库 `context/README.md`、`context/initialization.md`、`context/group/` 和 `context/projects/README.md`；
7. 按下述分流读取初始化入口，或当前任务记录、所属项目上下文与登记的直接来源。

初始化或任务资料不存在时，说明缺失，不把不存在的路径当作已读取资料。不要将 `context/projects/_template/` 当成真实项目。

## 启动分流

- 用户问“你是谁”“你在本仓库扮演什么角色”或“这个仓库是什么”时，先依据本文件说明 Agent 在本仓库中的工作职责与边界，并读取根 `README.md` 说明仓库定位。区分运行环境提供的模型/客户端身份、Agent 的仓库工作角色、小组身份和项目身份；只有用户进一步询问小组或项目时，才读取对应 `context/group/` 或 `context/projects/<project-id>/`。只问身份不创建任务、不扫描全部项目资料；未核实的身份和事实明确标注为未知或待确认，不从仓库路径、Git 作者或当前操作者推断。
- 用户说“初始化小组资产仓”：先读取 `context/initialization.md`，通过 Manifest 中 `consumer.group-asset-onboarding` 入口继续候选信息访谈与核对。初始化已满足当前工作需要时说明现状，询问本次要完善的对象，不重置已确认信息。
- 用户说“进行项目初始化”或“初始化项目”：作为初始化入口别名，先判断是在完成小组首启，还是在已有小组中新增/完善具体项目。已有项目不重建，多个项目时不自行选择。只读请求下仅报告状态；已获授权的初始化直接按现有授权推进。
- 用户给出已有任务编号：读取 `expression.task-loop` 入口，通过 `expression.task-record` 的 `show` 读取当前记录，核对状态、历史与产出，再读取该任务所属项目上下文；不要新建同一任务。
- 用户提出新的真实需求：读取任务循环入口，登记未对齐草案并逐步讨论；明确是否属于某个已登记项目，或属于小组级工作。不要默认选择项目、把一个项目的事实用于其他项目，或为填字段虚构项目。
- 用户要求制作 HTML 页面：按上述任务登记规则，通过 Manifest 中的 `expression.html-production` 读取 HTML 制作工作流；确认是否需要公式、显示模式、全屏和保存 PDF，再按需选择 `html.runtime-kit-v1`，不宣称所有页面会自动包含运行时按钮。
- 用户仅要求调查：只读上下文、任务和共享能力，不创建业务任务或作品。
- 用户要求检查或更新 submodule：路由到 Manifest 中显式声明的 `consumer.submodule-update`，遵守其确认、短期分支、验证和回退规则；没有该能力时只按版本协议报告，不自行补造工作流。

## 每次独立共享能力调用前的预检

每次准备调用一个独立的顶层共享能力时，先从当前固定 Manifest 确认 `consumer.submodule-preflight` 已声明并读取其入口，再从本仓库根目录执行只读预检。读取 Manifest 和预检工具入口是发现/启动检查，不视为调用业务能力；预检工具自身也不递归触发预检。

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/infrastructure/repository-management/tools/submodule-preflight/submodule_preflight.py --root . --path vendor/suanhai-team-external-expression-infrastructure
```

新空仓尚无父仓首次提交时，预检工具不能读取不存在的父仓 HEAD；按建立流程运行 `consumer.group-asset-bootstrap` 的 dry-run，核对 index gitlink 与 submodule HEAD。可以先完成初始化访谈，不为通过预检擅自提交。首次提交后，每个独立的顶层能力调用各自执行一次上面的预检。

一个顶层工作流开始后固定使用预检得到的完整 SHA；它通过 `uses` 调用的工具、模板、样式、技能或检查均沿用该 SHA，不重复查询。同一会话中开始另一个独立任务/报告、调用另一个顶层能力，或在新会话恢复任务时，重新预检；仅继续当前尚未中断的工作流时复用快照。预检工具输出应保留在本次任务记录或 Agent 的工作上下文中，至少记录 `observed_at`、父仓 gitlink SHA、submodule HEAD 和远端 `main` SHA/状态。

- `status=locked`：本地状态一致，远端 `main` 与固定 gitlink 相同；锁定并使用该完整 SHA。
- `status=update-available` 且本地检查通过：向用户报告当前 gitlink SHA 与远端 `main` SHA，并说明 SHA 不同只表示远端指针发生变化，不能据此断言候选是快进提交、包含新能力或已验收。若用户本轮已明确要求更新，按其要求进入 `consumer.submodule-update` 并展示计划、等待更新确认；否则暂停该顶层能力，请用户选择暂缓更新、继续当前固定 SHA，或立即进入该受控更新流程。
- 用户选择立即更新：先由更新工作流展示候选、差异、验证和回退计划并取得确认；它复用触发更新的这次预检快照，避免递归预检。只有用户已授权提交、更新后的 gitlink 已进入父仓 `HEAD`、父仓工作区干净且完整预检通过后，才能从新固定 SHA 重新开始原能力；提交尚未获授权时保留现场并暂停原能力。
- 远端查询失败：明确报告远端状态未知；若所有本地检查通过，可继续使用当前固定 SHA，但不得声称与远端同步。若本地任一检查失败（gitlink 与 HEAD 不一致、父仓路径或 submodule 脏、固定对象或能力入口缺失等），停止相关能力调用并保留现场。

远端快照使用只读 `ls-remote`，不执行 fetch、checkout、`git submodule update --remote` 或静默升级。版本更新和回退沿用版本协议与当前用户授权；远端变化或用户选择不能导致正在进行的工作流中途切换 SHA。

上面的预检命令在 Windows 使用 `py -3`；Linux/macOS 将解释器替换为 `python3`。首次恢复固定依赖可以为下载该固定 commit 访问远端，但不等于升级或远端追随。

## 入口和对象

- `context/group/` 描述小组自身；`context/projects/` 可以为空，也可以登记多个项目。不要假设一个小组只有一个项目。
- 用户提出真实工作需求后，先在 `tasks/` 登记并对齐任务，再按任务类别选择承载目录。
- 报告类任务的版本产物放入 `reports/<task-id>/v001/`；系列、课程、书籍仍分别放入自己的归档位置。
- `topics/` 保存来源明确、状态可追溯、适合本小组重复使用且由本小组负责核实和更新的内容资产。可在本组复用不等于适合共享给其他组；只有脱离具体项目事实、适用边界清楚并能服务多个小组的抽象模式，才考虑提炼到基础设施仓。
- 评审与发布授权记录放入 `reviews/`；生成文件或通过工程检查不等于真人确认或发布授权。

## 共享能力

基础设施 submodule 默认只读。它提供跨小组可复用的方法与执行能力，不是本小组事实或结论的权威副本。仅将 `manifest.yml` 中显式列出的能力视为可调用；目录存在或 README 写有计划，不代表能力已经实现。每次任务记录实际使用的能力 ID 与 submodule commit。

## 事实与授权

初始化材料默认为候选。未知信息标注“待确认”，记录来源和待核对责任人；只有负责人明确核对后才能标记为已确认。不得编造小组身份、成员职责、项目事实、来源许可、评审结论或发布授权。不得把秘密、凭据或无关个人信息写入资产仓。

不同机器、成员或会话启动时，先读取共享初始化进度。当前使用者角色与共享小组身份分开，不能把本次操作者覆盖为小组身份、仓库负责人或项目负责人。只追问缺项、变化和本轮要处理的对象，保留已有确认依据。

提交、推送、部署、对外发送和发布必须有相应用户授权；已有授权在其范围内继续有效，不重复请求。用户确认任务产物不自动代表专业验收或对外发布授权。

详细启动协议见 `vendor/suanhai-team-external-expression-infrastructure/docs/consumer-repository-bootstrap.md`；新仓初始化访谈见 `vendor/suanhai-team-external-expression-infrastructure/workflows/group-asset-repository-onboarding/ENTRYPOINT.md`。
