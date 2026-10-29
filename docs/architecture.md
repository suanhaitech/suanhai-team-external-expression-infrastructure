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

- **项目工作入口**：消费端自己的 `AGENTS.md`、`context/`、`tasks/`、`topics/`、`reports/`、`series/`、`courses/`、`books/`、`tools/` 和 `reviews/`，解释小组与项目事实、任务、来源、报告资产和评审；旧消费端的 `works/` 仍由任务工具兼容；
- **共享能力入口**：本仓库 submodule 中的 `manifest.yml`，只声明已经实现、可验证和可调用的能力。

消费端 Harness 把两类入口连接成任务路线，但不把项目事实复制到共享仓库，也不把计划目录提升成能力。消费端必须在根 `AGENTS.md` 显式接入 [Bootstrap 协议](consumer-repository-bootstrap.md)，否则 submodule 中的文档不会自动改变 Agent 行为。完整协议和冒烟测试见 [消费端对外表达 Harness v0.1](consumer-repository-harness-v0.1.md) 和 [消费端 Agent 冒烟测试](consumer-repository-smoke-test.md)。

新组通过公开的 GitHub 模板仓 `suanhaitech/suanhai-team-group-asset-template` 创建独立资产仓，再递归克隆。发布的模板仓已配置基础设施 submodule 和固定 gitlink；成员不需要先克隆基础设施或手工铺设文件。具体操作见 [新机器初始化流程](group-asset-repository-bootstrap.md)。

如果组长希望 Agent 代办建仓和本地克隆，使用自包含的 [创建与初始化提示词](../harness/group-asset-repository/CREATE_AND_INITIALIZE.md)。该启动文本在 submodule 尚不存在时即可单独分享；建仓、递归克隆和固定依赖核验后，才把控制交给消费端已固定版本中的初始化 Harness。创建目标仓、初始化本地上下文、负责人确认和远程推送是不同边界，不能把前一步授权延伸成后续全部授权。

模板源文件保存在本仓 `templates/group-asset-repository-v1/`，源目录本身不嵌套自身 submodule；维护者将其发布到独立模板仓时配置依赖。铺设工具是维护者从空仓建模版和工具回归的备用入口，只复制空结构，不承担现有仓库自动迁移。初始化 Harness 引导当前使用者区分小组身份与项目事实、保留来源与确认依据。小组上下文位于 `context/group/`，零到多个项目位于 `context/projects/`；初始化进度保存在 `context/initialization.md`。

## 任务循环与恢复

当前 [任务循环入口](../harness/task-loop/ENTRYPOINT.md) 由 Manifest 发现，配套 Python 工具以消费端 `tasks/<编号>/task.json` 为唯一任务事实源，生成 `task.md` 阅读视图。状态、共识记录、反馈、产出摘要和下一步留在消费端；共享仓只维护通用协议与工具。

用户协作循环负责目标和版本确认，Agent 内部循环负责授权范围内的制作与检查。状态工具不运行 Agent、不提供 HTML 生成或浏览器预览，也无法证明用户身份或发布权限。跨设备恢复依赖父仓文件同步与准确 submodule gitlink，不由任务编号自动完成。

## 责任边界

基础设施仓库提供“如何工作”的共享能力。小组资产仓库提供“正在表达什么”的事实、来源、任务上下文、评审和责任记录。Agent 可以执行工具，但不因此成为专业判断或对外发布的责任主体。

## 首版不做的事情

- 远程插件市场和动态能力注册；
- 多 Agent 编排平台；
- 自动 Git 提交、推送、部署或发布；
- 统一审批状态机；
- 项目、科研、客户和成员数据存储；
- 对小组资产仓库的强制模板和内容同步。
