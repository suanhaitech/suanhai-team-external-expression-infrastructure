# 小组对外表达资产仓库 Agent 规则

Agent 工作目录为本仓库根目录。开始工作前必须按以下顺序读取；下列基础设施路径均位于 `vendor/suanhai-team-external-expression-infrastructure/`：

1. 根 `README.md` 与本文件；
2. 基础设施 `manifest.yml`；
3. 基础设施 `docs/consumer-repository-bootstrap.md`；
4. 基础设施 `docs/consumer-repository-harness-v0.1.md`；
5. 基础设施 `docs/submodule-consumer-versioning.md`，以及 Manifest 声明的预检能力入口；
6. 本仓库 `context/README.md`、`context/initialization.md`、`context/group/` 和 `context/projects/README.md`；
7. 按下述分流读取初始化入口，或当前任务记录、所属项目上下文与登记的直接来源。

初始化或任务资料不存在时，说明缺失，不把不存在的路径当作已读取资料。不要将 `context/projects/_template/` 当成真实项目。

## 启动分流

- 小组身份或上下文初始化尚未完成：读取 Manifest 中 `consumer.group-asset-onboarding` 的入口，按其引导完成候选信息访谈与核对。只读请求下仅报告初始化状态，不填写事实；已获授权的初始化直接按现有授权推进。
- 用户给出已有任务编号：读取 `expression.task-loop` 入口，通过 `expression.task-record` 的 `show` 读取当前记录，核对状态、历史与产出，再读取该任务所属项目上下文；不要新建同一任务。
- 用户提出新的真实需求：读取任务循环入口，登记未对齐草案并逐步讨论；明确是否属于某个已登记项目，或属于小组级工作。不要默认选择项目、把一个项目的事实用于其他项目，或为填字段虚构项目。
- 用户仅要求调查：只读上下文、任务和共享能力，不创建业务任务或作品。

## Submodule 预检与版本

每次启动时，Manifest 声明 `consumer.submodule-preflight` 的情况下，读取入口并从本仓库根目录执行只读预检：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/tools/submodule-preflight/submodule_preflight.py --root . --path vendor/suanhai-team-external-expression-infrastructure
```

新空仓尚无父仓首次提交时，预检工具不能读取不存在的父仓 HEAD；按建立流程运行 `consumer.group-asset-bootstrap` 的 dry-run，核对 index gitlink 与 submodule HEAD。可以先完成初始化访谈，不为通过预检擅自提交。首次提交后的日常启动使用上面的预检。

预检核对父仓固定 gitlink、submodule HEAD、工作区和远端稳定分支快照。远端存在更新只需报告，不执行 fetch、checkout、`submodule update --remote` 或静默升级。远端网络不可用时，保留失败结果，并用同一命令追加 `--skip-remote` 检查本地；本地固定版本一致且工作区干净时可继续使用该版本，明确报告远端状态未知。不能把其他本地错误当成网络问题忽略。升级与回退沿用版本协议和当前用户授权。

## 入口和对象

- `context/group/` 描述小组自身；`context/projects/` 可以为空，也可以登记多个项目。不要假设一个小组只有一个项目。
- 用户提出真实工作需求后，先在 `tasks/` 登记并对齐任务，再按任务类别选择承载目录。
- 报告类任务的版本产物放入 `reports/<task-id>/v001/`；系列、课程、书籍仍分别放入自己的归档位置。
- `topics/` 只放来源明确、状态可追溯且适合复用的内部内容资产。
- 评审与发布授权记录放入 `reviews/`；生成文件或通过工程检查不等于真人确认或发布授权。

## 共享能力

基础设施 submodule 默认只读。仅将 `manifest.yml` 中显式列出的能力视为可调用；目录存在或 README 写有计划，不代表能力已经实现。每次任务记录实际使用的能力 ID 与 submodule commit。

## 事实与授权

初始化材料默认为候选。未知信息标注“待确认”，记录来源和待核对责任人；只有负责人明确核对后才能标记为已确认。不得编造小组身份、成员职责、项目事实、来源许可、评审结论或发布授权。不得把秘密、凭据或无关个人信息写入资产仓。

提交、推送、部署、对外发送和发布必须有相应用户授权；已有授权在其范围内继续有效，不重复请求。用户确认任务产物不自动代表专业验收或对外发布授权。

详细启动协议见 `vendor/suanhai-team-external-expression-infrastructure/docs/consumer-repository-bootstrap.md`；新仓初始化访谈见 `vendor/suanhai-team-external-expression-infrastructure/harness/group-asset-repository/ENTRYPOINT.md`。
