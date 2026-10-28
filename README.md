# Suanhai 团队对外表达基础设施

这是 `suanhaitech` 组织下的共享工程仓库，为 Suanhai 团队的科研小组和项目小组提供可复用的对外表达能力。

当前提供可发现的任务循环、任务状态工具和一套实验性的离线项目汇报模板，支持任务草案、共识对齐、反馈迭代、暂停恢复和按编号续作。模板只提供结构和样式，不自动生成内容；预览和 HTML 检查器仍未实现。

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
| `expression.task-loop` | harness | 由消费端 Agent 执行的任务协作循环 |
| `expression.task-record` | tool | Python 标准库工具，管理任务文件、状态及产出摘要 |
| `html.project-report-v1` | template | 离线项目概览、阶段进展和对外汇报 HTML/CSS 模板 |

目录中标记为 `planned / not implemented` 的能力不能被当作可调用入口。新增能力前必须先实现入口、补充说明、通过检查，再更新 Manifest。

## 消费端 Harness

通过 submodule 使用本仓库的小组资产仓库，应把自己的 `AGENTS.md`、`context/`、`tasks/`、`works/` 和 `reviews/` 作为项目工作入口，把本仓库的 `manifest.yml` 作为共享能力入口。消费端 Agent 的启动接入、读取顺序、任务路线、停止条件和首个 HTML 冒烟测试见：

- [消费端 Agent Bootstrap 协议](docs/consumer-repository-bootstrap.md)
- [消费端对外表达 Harness v0.1](docs/consumer-repository-harness-v0.1.md)
- [消费端 Agent 冒烟测试](docs/consumer-repository-smoke-test.md)
- [任务循环入口](harness/task-loop/ENTRYPOINT.md)
- [任务循环验证与换 Agent 续作](docs/task-loop-validation.md)

Bootstrap 必须由消费端显式写入根 `AGENTS.md` 才会生效；文档存在于 submodule 中不会自动改变 Agent 行为。根 Manifest 声明了当前任务循环、配套工具和项目汇报模板，Agent 需读取入口后按用户授权执行；它们不是后台执行器或权限沙箱。

## 开发和版本

- `main`：稳定、可被 submodule 固定引用的版本；
- `develop`：日常集成分支；
- `codex/*`：从 `develop` 创建的短期开发分支。

当前仓库由 Chaos 全权维护。开发过程中不自动提交、推送、部署或发布；GitHub Actions 只做确定性的 Manifest 校验。

## 本地检查

需要 Ruby 3.3 或更高版本：

```text
ruby scripts/validate_manifest.rb
```

校验脚本只使用 Ruby 标准库，不需要安装仓库级依赖。完整 CI 由 `.github/workflows/validate-manifest.yml` 执行。

任务循环需要 Python 3.10+，仅使用标准库：

```text
python -m unittest discover -s tests -p "test_task_loop.py" -v
```

## 当前阶段边界

本阶段先验证任务循环、跨会话恢复和一套离线 HTML 模板，不接入数据库、云端 API 或部署流程。模板不等于自动 HTML 生成器，消费端仍需由 Agent 按任务上下文填充并评审内容。
