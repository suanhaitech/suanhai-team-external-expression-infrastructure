# 小组资产仓创建与初始化工作流

状态：`implemented / experimental`

能力 ID：`consumer.group-asset-create-and-initialize`

## 目标

从公开 GitHub 模板为一个小组创建独立资产仓，递归克隆到负责人指定的本地父目录，核验模板固定的基础设施 submodule，然后转交给新仓中的初始化 Harness。

## 入口

此流程的第一步发生在目标仓库和基础设施 submodule 尚不存在之前，因此组长可直接转发同目录的 [`CREATE_AND_INITIALIZE.md`](CREATE_AND_INITIALIZE.md) 作为一次性启动提示词。提示词自包含，不要求先克隆本基础设施仓。

已在基础设施或消费端工作区中的 Agent 可从 Manifest 发现本能力，读取 [`ENTRYPOINT.md`](ENTRYPOINT.md) 后执行工作流。新仓建立完成后，长期行为由新仓根 `AGENTS.md` 约束；小组身份和项目上下文由 `consumer.group-asset-onboarding` 引导确认。

## 输入

- 小组正式名称和目标仓库短名；
- 本地克隆父目录绝对路径；
- 预期 GitHub 账号及仓库可见性；
- 当前 Agent 环境中的 Git、GitHub CLI、Python 和网络访问能力；
- 后续初始化访谈所需的小组与项目信息，可在建仓后逐步提供。

## 结果

- 由公开模板生成的独立小组资产仓；
- 本地递归克隆，`origin` 指向新仓；
- `.gitmodules`、父仓 gitlink、submodule HEAD、远端稳定 `main` 快照和 Manifest 入口核验记录；
- 模板 `.gitattributes` 的有效字节保护范围，必要时通过已声明工具增补的本地保护段；
- 留在新仓工作区、供负责人审阅的初始化候选与待确认项。

## 阶段与边界

1. 收集并核对建仓参数和 Agent 工具环境；
2. 使用 GitHub Template Generate API 创建目标仓；
3. 使用 `git clone --recurse-submodules` 克隆新仓；
4. 初始化后运行一次只读 submodule 预检，确认本地状态，并把当前 SHA 作为本次顶层流程的版本快照；远端 `main` SHA 不同只视为候选变化，报告两者并等待用户选择暂缓并继续固定版，或结束流程、另行授权受控更新；
5. 核对模板已带的根 `.gitattributes`：tasks/reports/courses/series/books 的 `-text` 规则以 `git check-attr text -- <实际文件>` 验证为 `unset`。自定义目录存在保护缺口时，按固定 Manifest 的 [`consumer.asset-bytes`](../../infrastructure/repository-management/tools/asset-bytes/README.md) 默认只读预览，再在本地初始化授权范围内同参 `--apply --expect-plan-sha256 <摘要>` 显式应用；不覆盖原规则、不改旧 Harness、不运行 `git add --renormalize` 或重写历史文件。工具没有 `--dry-run` 参数；重复 `--output-root` 指定包含任务目录的完整安全目录集合，context/vendor 等未覆盖来源须如实说明。能力缺失或规则冲突时报告，不自动升级；
6. 复用阶段 4 的预检快照，从新仓根规则调用 `consumer.group-asset-onboarding`，逐项收集、标注并记录小组上下文；不在同一创建与初始化流程内重复查询。

建仓是持久的远程副作用。流程不得覆盖已有仓库或目录、修改组织权限、改动基础设施版本、提交或推送初始化材料，也不得把候选信息写成负责人已确认。具体授权、异常处理和端到端测试步骤以启动提示词及[代建流程说明](../../docs/group-asset-repository-create-and-initialize.md)为准。

## 依赖

- `consumer.group-asset-onboarding`
- `consumer.submodule-preflight`
