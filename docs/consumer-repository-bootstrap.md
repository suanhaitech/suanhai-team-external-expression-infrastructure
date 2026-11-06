# 消费端 Agent Bootstrap 协议

> **状态**：可复制到消费端 `AGENTS.md` 的启动协议；具体任务循环与工具由 Manifest 声明，本文件不是自动执行器。
> **适用对象**：通过 `vendor/suanhai-team-external-expression-infrastructure` 使用本仓库的小组资产仓库。

## 为什么需要这段协议

Agent 不会因为 submodule 中存在文档，就自动发现并执行其中的工作规则。消费端必须在自己的根 `AGENTS.md` 中显式接入本协议，才能让新 clone 的仓库按照一致的顺序装配项目上下文、发现共享能力并执行停止条件。

本协议只提供可复用的启动约束。项目事实、任务责任、来源授权和发布决定仍以消费端仓库为准；本仓库不能替代消费端的权限规则。

“任何成员 clone 后即可使用”需要满足几个明确条件：submodule 已初始化、Agent 从消费端仓库根目录启动、Agent 客户端会加载根 `AGENTS.md`（否则每次启动时要显式要求它遵循该文件）、消费端上下文与任务资料已准备好。仓库文件无法强制所有 Agent 客户端采用相同的启动行为，也无法替代用户本机和远端系统的访问权限。

## 接入方式

本文件描述消费端 Harness 的通用启动协议，不会因为 submodule 被克隆而自动生效。采用公共模板的新仓已经预置接入规则；既有仓库首次接入时，使用[既有仓库接入工作流](../workflows/infrastructure-adoption/ENTRYPOINT.md)和[可转发提示词](../workflows/infrastructure-adoption/ADOPT_EXISTING_REPOSITORY.md)。该一次性流程保留原仓库结构、固定 submodule 版本，并调用已声明工具预览及安装消费端根 `AGENTS.md` 规则。以后同一仓库中的 Agent 从根规则路由能力，不重复使用首次提示词。

公共模板已经把等价的启动规则放入消费端根 `AGENTS.md`。既有仓库不要直接手工复制下面的示例来绕过接入流程；应使用[既有仓库接入工作流](../workflows/infrastructure-adoption/ENTRYPOINT.md)调用 `consumer.infrastructure-adoption-harness`，提示词授权后由 Agent 预览校验并安装带标记的规则。下面的文本用于说明协议内容和模板实现，submodule 路径默认是 `vendor/suanhai-team-external-expression-infrastructure`；消费端原有的项目规则、权限边界和更严格的限制优先于本协议。

### 登记来源与作品前保护原始字节

跨设备 clone 可能因 Git 换行转换改变同一文件的 SHA-256，影响任务恢复和作品校验。新公共模板已经通过根 `.gitattributes` 对 `tasks/`、`reports/`、`courses/`、`series/`、`books/` 声明 `-text`；建仓后核对实际文件的 `git check-attr text -- <文件>` 结果为 `unset`。这里保护的是这些目录内的来源/作品及任务记录，不代表仓库任意位置的来源都已受保护。

既有仓库或使用自定义输出根的仓库，在首次登记来源/作品摘要前，从固定 Manifest 发现 [`consumer.asset-bytes`](../infrastructure/repository-management/tools/asset-bytes/README.md)。先运行工具的默认只读预览（没有 `--dry-run` 参数），核对 `planned_text`、影响目录和 `plan_sha256`；本轮已有相应本地接入修改授权时，以相同参数加 `--apply --expect-plan-sha256 <预览摘要>` 显式应用。仅追加带标记的 `.gitattributes`，原规则保持不变；冲突、标记差异、嵌套规则覆盖时停止报告。不得改写旧 Harness 标记段来引入这项路由。

工具默认保护上述五个目录。使用 `--output-root` 时应给出需要保护的完整安全顶层目录集合，包含任务记录目录及实际来源/作品目录，不能只给一个新增目录而遗漏已有目录；受保护的 `context/`、`vendor/` 不能通过此参数接管。来源在其他位置时先说明保护边界，不能声称已全部覆盖。

规则只影响今后的 Git 转换，不恢复历史字节。不得自动执行 `git add --renormalize`、批量重签摘要或重写已有来源/作品；已经发生的摘要差异应先找原文件并解释，另行确定迁移。固定旧版 Manifest 没有该能力时，报告保护缺口，通过受控更新另行解决，不从远端临时复制工具。

```markdown
## 共享对外表达基础设施启动规则

Agent 的工作目录必须是本仓库根目录。开始任何对外表达任务前，按以下顺序读取：

1. `README.md`
2. `AGENTS.md`
3. `vendor/suanhai-team-external-expression-infrastructure/manifest.yml`
4. `vendor/suanhai-team-external-expression-infrastructure/docs/consumer-repository-bootstrap.md`
5. `vendor/suanhai-team-external-expression-infrastructure/docs/consumer-repository-harness-v0.1.md`
6. 基础设施 `docs/submodule-consumer-versioning.md` 与已声明的预检能力入口
7. `context/README.md`、`context/initialization.md`、`context/group/` 和 `context/projects/README.md`（旧仓按本仓实际映射）
8. 已有任务的 `task.json`（通过 show）和生成的 `task.md`，再读取任务相关的项目上下文及登记的直接来源

读取后，先输出当前项目、任务目标、受众、允许使用的来源、计划输出路径、Manifest 能力、缺失信息和需要真人确认的事项。只读请求下没有任务时不创建任务或作品；获授权的制作请求可以先创建未对齐的任务草案。

用户询问“你是谁”“你在本仓库扮演什么角色”或“这个仓库是什么”时，将其视为仓库定向问题：根据根 `AGENTS.md` 说明 Agent 在消费端的工作角色和边界，根据根 `README.md` 说明仓库定位。运行模型/客户端身份以当前运行环境为准；小组与项目身份分别以对应上下文为准，只在问题需要时读取。只问身份不创建任务、不扫描全部项目资料；上下文未提供或尚未确认时明确说明未知，不从仓库路径、Git 作者或当前操作者推断。

当前 Manifest 包含 `expression.task-loop` 时，读取其 entrypoint，并通过 `expression.task-record` 管理任务。Manifest 的 `kind: workflow` 表示复合工作流能力；读取其入口后，还要按 `uses` 字段读取依赖能力。用户给出任务号时先 show 读取，恢复前只核对状态；不要根据旧聊天或旧测试报告推断本轮事实。

新仓初始化未完成时，从 Manifest 读取 `consumer.group-asset-onboarding` 入口，按用户已有授权继续分轮访谈。先区分当前使用者角色与共享的小组身份；小组可以有零到多个项目，不能默认选择项目。只读请求仅报告初始化状态，不填写事实。缺少旧单项目路径时不伪造文件，按本仓的实际上下文映射读取。

准备调用每个独立的顶层共享能力前，运行已声明的 `consumer.submodule-preflight` 做只读版本预检；一次顶层工作流中的依赖能力沿用同一完整 SHA，不重复查询。同一会话中开始另一个独立任务/能力，或在新会话恢复任务时，重新预检。若远端 `main` SHA 与父仓 gitlink 不同，报告两者并说明这只代表指针不同，不证明候选是快进提交、包含新能力或已验收。若用户本轮已明确要求更新，进入受控更新流程并展示计划、等待确认；否则暂停该顶层调用，让用户选择暂缓并继续使用当前固定 SHA，或进入受控更新流程。远端查询失败时标记为未知，本地检查通过时可继续固定 SHA，但不得声称已同步；任何本地检查失败都停止。新空仓尚无首次提交时，按新仓建立流程运行铺设工具 dry-run 核对 index gitlink 与 submodule HEAD，不能为了通过预检而擅自提交。

共享能力只能从 submodule 的 `manifest.yml` 发现。只有 `capabilities` 中显式列出的能力才可调用；计划目录、占位 README 和未列出的路径都不可调用。不同 gitlink 可能包含不同 Manifest 版本；例如 schema v2 增加了通过 `uses` 声明依赖的 workflow 能力。当前 HTML 网页制作工作流、语义组件包、响应式布局包、离线页面运行时包 `html.runtime-kit-v1`、`html.materialize`、`html.viewport-check` 和 `html.pdf-export` 已注册；完整无障碍检查只有在相应能力明确注册后才可调用。运行时包自身提供本地公式渲染和页面工具栏，但真实浏览器交互仍需在消费端执行检查。

项目事实、来源文件、作品、评审记录和发布授权写入本仓库；默认不修改 submodule。提交、推送、部署或发布须有相应用户授权；已有授权在其范围内继续有效。Agent 不能代替专业事实评审、责任主体确认或对外授权。
```

Manifest 是**发现清单**，不是权限系统或执行沙箱。它回答“基础设施声明了哪些能力”，不会检查用户是否有权访问本地文件、阻止工具产生副作用或隔离命令执行。消费端仍需遵守本地 Agent 的工具授权设置，并在运行能力前阅读其输入、输出、依赖、外部访问和副作用说明。

## 接入后的启动结果

完成接入后，新 clone 的消费端 Agent 可以立即验证以下行为：

1. 知道自己工作的项目和任务主位在哪里；
2. 能从 `manifest.yml` 得到确定的共享能力清单；
3. 能在相关能力缺失或来源不足时停止相关动作，不调用占位目录或虚构结果；
4. 能把草稿、来源关联和评审问题留在消费端仓库；
5. 能把需要真人判断的事项交还给责任主体。

这使 Agent 获得项目对外表达工作的上下文和受限工作流支持，但不使 Agent 自动拥有项目专业判断、客户验收权或发布权限。

若消费端尚无任务记录，Agent 应先说明缺少任务并停止作品生成；此时仍可完成只读的上下文和能力发现冒烟测试。没有任务时的停止行为本身就是可验证结果，不需要为了测试而伪造项目任务。

## 验证要求

消费端在提交 `AGENTS.md` 的接入改动前，应按 [消费端 Agent 冒烟测试](consumer-repository-smoke-test.md) 验证读取顺序、Manifest 能力发现、停止条件和作品承载位置。基础设施仓库只记录通用协议，不记录具体项目资料。
