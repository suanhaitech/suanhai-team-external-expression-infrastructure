# 首版架构边界

## 仓库关系

本仓库是共享能力仓库。未来的小组对外表达资产仓库是父仓库，通过 Git submodule 固定本仓库的具体 commit：

```text
小组资产仓库
└── vendor/suanhai-team-external-expression-infrastructure
    └── 固定 commit 的共享能力
```

父仓库的 gitlink 是实际使用版本的唯一事实来源。分支名和标签只用于开发、识别和保留提交，不能替代 gitlink。

## 能力分层

- **skill**：告诉 Agent 如何理解表达任务、组织步骤和处理边界；
- **template**：提供 HTML 页面或组件的结构起点；
- **tool**：执行渲染、预览、转换、素材处理或确定性检查；
- **harness**：约束输入、工作目录、工具调用、停止条件和输出协议；
- **check**：验证结构、资源、链接或渲染结果。

Manifest 只列出已经实现并可被消费端使用的能力。计划能力写在路线文档和对应目录的 README 中，不进入清单。

## 消费端工作层

一个小组资产仓库同时使用两类入口：

- **项目工作入口**：消费端自己的 `AGENTS.md`、`context/`、`tasks/`、`works/` 和 `reviews/`，解释项目事实、任务、来源、作品和评审；
- **共享能力入口**：本仓库 submodule 中的 `manifest.yml`，只声明已经实现、可验证和可调用的能力。

消费端 Harness 把两类入口连接成任务路线，但不把项目事实复制到共享仓库，也不把计划目录提升成能力。消费端必须在根 `AGENTS.md` 显式接入 [Bootstrap 协议](consumer-repository-bootstrap.md)，否则 submodule 中的文档不会自动改变 Agent 行为。完整协议和冒烟测试见 [消费端对外表达 Harness v0.1](consumer-repository-harness-v0.1.md) 和 [消费端 Agent 冒烟测试](consumer-repository-smoke-test.md)。

## 责任边界

基础设施仓库提供“如何工作”的共享能力。小组资产仓库提供“正在表达什么”的事实、来源、任务上下文、评审和责任记录。Agent 可以执行工具，但不因此成为专业判断或对外发布的责任主体。

## 首版不做的事情

- 远程插件市场和动态能力注册；
- 多 Agent 编排平台；
- 自动 Git 提交、推送、部署或发布；
- 统一审批状态机；
- 项目、科研、客户和成员数据存储；
- 对小组资产仓库的强制模板和内容同步。
