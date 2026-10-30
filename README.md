# Suanhai 团队对外表达基础设施

这是 `suanhaitech` 组织下的共享工程仓库，为 Suanhai 团队的科研小组和项目小组提供可复用的对外表达能力。

当前提供可发现的任务循环、任务状态工具、离线项目汇报模板、小组资产仓库模板，以及多条消费端工作流：小组初始化、从公共模板建仓并初始化、既有仓库首次接入基础设施、已接入 submodule 的受控更新。小组模板支持零到多个项目上下文；初始化工具只铺设空白骨架并拒绝覆盖，Agent 需通过访谈与负责人核对上下文。HTML 预览和检查器仍未实现。

本仓库另外提供可直接转发的一次性启动提示词：一类用于从 GitHub 公共模板建仓、递归克隆并初始化；另一类用于将基础设施首次接入既有仓库并安装消费端 Harness。前者适合新仓，后者适合保留既有结构的仓库；两者完成后，日常能力路由均依靠消费端根规则和固定 submodule Manifest。

本仓库自身由根 `AGENTS.md` 约束；对消费端提供的工作流以 Capability 形式注册在 `manifest.yml` 中。工作流是面向一个完整目标的复合能力，通常由工作流目录中的 Harness 约束 Agent 执行，并调用工具、模板、技能和检查器。

## 仓库职责

本仓库承载可以被多个小组复用的工程能力：

- Agent 使用的技能说明；
- HTML 和其他表达资产的模板；
- 本地预览、渲染和检查工具；
- 约束 Agent 输入、工作目录、检查点和输出的 Harness；
- 能被父仓库以 Git submodule 固定版本引用的文件协议。

项目事实、客户资料、科研材料、成员责任、任务来源和最终表达资产属于各小组自己的资产仓库，不应复制到本仓库。

## Agent 发现入口

Agent 从仓库根目录的 `manifest.yml` 发现已实现能力：

| ID | 类型 | 作用 |
| --- | --- | --- |
| `expression.task-loop` | workflow | 由消费端 Agent 执行的任务协作循环，使用任务记录工具 |
| `expression.task-record` | tool | Python 标准库工具，管理任务文件、状态及产出摘要 |
| `html.project-report-v1` | template | 离线项目概览、阶段进展和对外汇报 HTML/CSS 模板 |
| `consumer.submodule-preflight` | tool | 只读核对消费端 submodule 的固定 gitlink、工作区和远端稳定分支快照 |
| `consumer.group-asset-bootstrap` | tool | 在已固定 submodule 的消费端安全铺设小组资产仓模板 |
| `consumer.group-asset-onboarding` | workflow | 引导负责人确认小组身份、多项目上下文、来源和边界 |
| `consumer.group-asset-create-and-initialize` | workflow | 可转发启动提示词：从 GitHub 模版创建、递归克隆、核验固定依赖，再转交仓内初始化 |
| `consumer.submodule-update` | workflow | 在用户确认和短期分支中受控更新消费端 submodule gitlink |
| `consumer.infrastructure-adoption` | workflow | 为不采用公共模板的既有仓库接入固定版本 submodule，并增补消费端根 Agent Harness |
| `consumer.infrastructure-adoption-harness` | tool | 预览并幂等安装消费端根 `AGENTS.md` Harness；默认只读，接入工作流授权后显式应用 |

目录中标记为 `planned / not implemented` 的能力不能被当作可调用入口。新增能力前必须先实现入口、补充说明、通过检查，再更新 Manifest。`workflow` 能力的 `uses` 字段列出它依赖的其他已声明能力；Manifest 校验会拒绝未声明的依赖。

## 消费端 Harness

通过 submodule 使用本仓库的小组资产仓库，应把自己的 `AGENTS.md`、`context/group/`、`context/projects/`、`tasks/`、`topics/`、`reports/`、`series/`、`courses/`、`books/`、`tools/` 和 `reviews/` 作为工作入口，把本仓库的 `manifest.yml` 作为共享能力入口。小组模板默认用 `reports/` 承载报告类任务产物；未迁移的消费端 `works/` 仍被任务工具兼容。消费端 Agent 的启动接入、初始化访谈、读取顺序、任务路线、停止条件和冒烟测试见：

- [消费端 Agent Bootstrap 协议](docs/consumer-repository-bootstrap.md)
- [消费端对外表达 Harness v0.1](docs/consumer-repository-harness-v0.1.md)
- [消费端 submodule 版本协议](docs/submodule-consumer-versioning.md)
- [消费端 Agent 冒烟测试](docs/consumer-repository-smoke-test.md)
- [任务循环入口](harness/task-loop/ENTRYPOINT.md)
- [小组资产仓初始化 Harness](harness/group-asset-repository/ENTRYPOINT.md)
- [小组资产仓创建与初始化提示词](harness/group-asset-repository/CREATE_AND_INITIALIZE.md)
- [既有仓库接入基础设施提示词](workflows/infrastructure-adoption/ADOPT_EXISTING_REPOSITORY.md)
- [既有仓库接入工作流](workflows/infrastructure-adoption/ENTRYPOINT.md)
- [小组资产仓从 GitHub 模板到新机器初始化](docs/group-asset-repository-bootstrap.md)
- [小组资产仓代建与初始化流程](docs/group-asset-repository-create-and-initialize.md)
- [小组资产仓模板验证与发布记录](docs/group-asset-template-validation.md)
- [任务循环验证与换 Agent 续作](docs/task-loop-validation.md)
- [Capability、Workflow 与 Harness 分层协议](docs/capability-and-harness-model.md)
- [submodule 更新工作流](workflows/submodule-update/ENTRYPOINT.md)

公共模板用于全新小组仓；已有仓库不需要迁移目录结构，可直接使用既有仓库接入提示词。接入工作流调用 `consumer.infrastructure-adoption-harness` 预览消费端根 `AGENTS.md` 的增补内容，预览、校验后直接安装。接入后，消费端根 AGENTS.md 承担长期 Harness，父仓 gitlink 固定共享基础设施版本；只要 submodule 已初始化且 Agent 客户端读取该文件，用户日常工作就不再重复发送初次提示词。客户端不读取时需要从它支持的指令入口显式引用；这不是后台自动执行。

Bootstrap 必须由消费端显式写入根 `AGENTS.md` 才会生效；文档存在于 submodule 中不会自动改变 Agent 行为。Agent 按消费端固定提交中的 Manifest 发现 workflow 和局部工具、模板等能力，再读取依赖入口并遵守用户授权；这些能力不是后台执行器或权限沙箱。

## 开发和版本

- `main`：稳定、可被 submodule 固定引用的版本；
- `develop`：日常集成分支；
- `codex/*`：从 `develop` 创建的短期开发分支。

当前仓库由 Chaos 全权维护。开发过程中不自动提交、推送、部署或发布；GitHub Actions 校验 Manifest，并在 Windows 与 Linux 运行任务循环、submodule 预检和模板铺设行为测试。

## 本地检查

需要 Ruby 3.3 或更高版本：

```text
ruby scripts/validate_manifest.rb
```

校验脚本只使用 Ruby 标准库，不需要安装仓库级依赖。完整 CI 由 `.github/workflows/validate-manifest.yml` 执行。

任务循环需要 Python 3.10+，仅使用标准库：

```text
python -m unittest discover -s tests -p "test_*.py" -v
```

## 当前阶段边界

本阶段先验证任务循环、跨会话恢复和一套离线 HTML 模板，不接入数据库、云端 API 或部署流程。模板不等于自动 HTML 生成器，消费端仍需由 Agent 按任务上下文填充并评审内容。
