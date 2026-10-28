# 消费端 Agent Bootstrap 协议

> **状态**：可复制到消费端 `AGENTS.md` 的启动协议；具体任务循环与工具由 Manifest 声明，本文件不是自动执行器。
> **适用对象**：通过 `vendor/suanhai-team-external-expression-infrastructure` 使用本仓库的小组资产仓库。

## 为什么需要这段协议

Agent 不会因为 submodule 中存在文档，就自动发现并执行其中的工作规则。消费端必须在自己的根 `AGENTS.md` 中显式接入本协议，才能让新 clone 的仓库按照一致的顺序装配项目上下文、发现共享能力并执行停止条件。

本协议只提供可复用的启动约束。项目事实、任务责任、来源授权和发布决定仍以消费端仓库为准；本仓库不能替代消费端的权限规则。

“任何成员 clone 后即可使用”需要满足几个明确条件：submodule 已初始化、Agent 从消费端仓库根目录启动、Agent 客户端会加载根 `AGENTS.md`（否则每次启动时要显式要求它遵循该文件）、消费端上下文与任务资料已准备好。仓库文件无法强制所有 Agent 客户端采用相同的启动行为，也无法替代用户本机和远端系统的访问权限。

## 接入方式

将下面的规则复制到消费端根 `AGENTS.md`，并把其中的 submodule 路径替换为实际路径（默认是 `vendor/suanhai-team-external-expression-infrastructure`）。消费端原有的项目规则、权限边界和更严格的限制优先于本协议。

```markdown
## 共享对外表达基础设施启动规则

Agent 的工作目录必须是本仓库根目录。开始任何对外表达任务前，按以下顺序读取：

1. `README.md`
2. `AGENTS.md`
3. `vendor/suanhai-team-external-expression-infrastructure/manifest.yml`
4. `vendor/suanhai-team-external-expression-infrastructure/docs/consumer-repository-bootstrap.md`
5. `vendor/suanhai-team-external-expression-infrastructure/docs/consumer-repository-harness-v0.1.md`
6. `context/README.md` 及其中与当前任务相关的项目上下文
7. `tasks/<task-slug>/task.md`
8. 任务说明中登记的直接来源

读取后，先输出当前项目、任务目标、受众、允许使用的来源、计划输出路径、Manifest 能力、缺失信息和需要真人确认的事项。只读请求下没有任务时不创建任务或作品；获授权的制作请求可以先创建未对齐的任务草案。

当前 Manifest 包含 `expression.task-loop` 时，读取其 entrypoint，并通过 `expression.task-record` 管理任务。用户给出任务号时先 show 读取，恢复前只核对状态；不要根据旧聊天或旧测试报告推断本轮事实。

共享能力只能从 submodule 的 `manifest.yml` 发现。只有 `capabilities` 中显式列出的能力才可调用；计划目录、占位 README 和未列出的路径都不可调用。当前 Manifest 可能为空，此时记录“无可用共享能力”和 submodule commit，并按 Harness 文档的停止条件工作。

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
