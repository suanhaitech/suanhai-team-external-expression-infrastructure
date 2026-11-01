# HTML 基础设施稳定发布与消费端迁移说明

本次将已通过集成检查和消费端试用的目录重构及 HTML 能力发布到稳定 `main`，再同步公共小组资产仓模板。`develop` 继续集成下一轮改动；能力的 `implemented / experimental` 标记保持不变。稳定分支提供可复现的发布基线，不代表所有浏览器、设备或内容都已完成验收。

## 发布范围

- 完整工作流放在 `workflows/`，可复用模板、组件、样式、运行时、Schema 和工具放在 `infrastructure/<领域>/`；不强制拆分子工作流。
- Manifest schema v2 声明 17 项能力，包括 HTML 制作、物料化、响应式布局、离线公式和工具栏、多视口检查及本地 PDF 导出。
- HTML 启动提示词明确按需选择 `html.runtime-kit-v1`，记录运行时选择并检查实际交互；运行时仍为可选项，旧页面不会自动获得按钮。
- 公共模板同步根 Agent 规则、使用说明、初始化进度和 CI 中的新路径，并固定基础设施稳定 `main` 的完整 commit。新仓继承固定 gitlink，已有仓不会自动升级。

父仓 gitlink 是消费端实际使用版本的唯一事实源。本文中的验收提交仅为历史证据，不是需要同步维护的第二份版本锁。

## 验证依据与限制

集成基线 `55469ab2aa6aa97b0c7a73e60a097deaf37b4f10` 的 [CI 41330210244](https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure/actions/runs/41330210244) 通过 Ruby Manifest 校验和 Windows、Ubuntu Python 回归。本次提示词及文档修订另由发布候选 PR 的同一套 CI 检查，只有全部通过的提交才能进入稳定分支。

消费端本地隔离试用记录显示：任务循环走到 `review`，物料化 117 个文件，未编辑的 116 项共享文件哈希保持一致；五类语义组件装配成功，公式实际渲染，本地 PDF 导出完成。这些结果证明共享资产可复用，不构成项目事实确认、页面发布授权或时间/token 节省的量化结论。

仍需明确报告的限制：

- 本地试用没有执行官方 Ruby 校验；官方结果来自上述 CI。
- Playwright 视口检查未执行，独立 headless 检查最小实际宽度为 504px，不能当作真实 390px 手机视口通过。
- 全屏、显示模式和浏览器打印按钮的逐项点击，以及 PDF 打印版式仍需针对交付页面检查。
- 浏览器检查与 PDF 导出依赖本机运行时；不可用时保留 `not-run`，不自动安装或伪造通过。

## 两仓发布顺序

1. 提示词和文档修订先在从 `develop` 创建的短期分支提交，通过 Manifest、Windows 与 Ubuntu CI。
2. 将同一验收提交快进到基础设施 `develop` 和 `main`；不强推、不移动标签。
3. 公共模板从其 `main` 创建短期分支，同步模板源文件，并将 gitlink 固定到刚发布的基础设施 commit。
4. 核验模板源一致、gitlink 模式为 `160000`、递归 clone 可用、预检和初始化入口有效；通过 Windows、Linux、macOS 模板 CI 后快进公共模板 `main`。
5. 核对两仓本地与远端发布分支一致，并保留实际 CI 链接和完整提交供维护者追溯。

公共模板自身不嵌入消费端任务、项目事实或测试产物。本次发布不修改已有小组仓，也不重新生成历史页面。

## 既有小组仓升级

在该小组仓根目录向平常使用的 Agent 说明“按 `consumer.submodule-update` 更新到基础设施稳定 `main` 的已验收提交”。Agent 先预检，解析并展示完整 SHA、能力变化、旧路径兼容性和测试计划，按现有授权推进；不使用 `git submodule update --remote`。

本次路径迁移至少需要核对以下活跃入口：

| 旧入口 | 新入口 |
| --- | --- |
| `harness/task-loop/ENTRYPOINT.md` | `workflows/task-loop/ENTRYPOINT.md` |
| `harness/task-loop/scripts/task_loop.py` | `infrastructure/task-loop/tools/task-record/task_loop.py` |
| `harness/group-asset-repository/ENTRYPOINT.md` | `workflows/group-asset-repository-onboarding/ENTRYPOINT.md` |
| `workflows/group-asset-repository/CREATE_AND_INITIALIZE.md` | `workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md` |
| `tools/submodule-preflight/submodule_preflight.py` | `infrastructure/repository-management/tools/submodule-preflight/submodule_preflight.py` |
| `templates/html-report/project-report-v1/` | `infrastructure/html/page-templates/project-report-v1/` |

保留小组自有规则与已确认上下文，只修正仍在使用的引用，不为迁移重写历史评审证据。按 Manifest 的能力 ID 发现入口，避免长期硬编码工具路径。新 gitlink 未提交前完整 preflight 会发现父仓 HEAD 与 index 不同，此时使用更新工作流规定的提交前核对；不要为了让预检通过擅自提交。

## 当前对外提示词入口

- [没有小组仓：创建并初始化](../workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md)
- [已有仓：接入基础设施](../workflows/infrastructure-adoption/ADOPT_EXISTING_REPOSITORY.md)
- [制作 HTML 页面](../workflows/html/production/START_HTML_PRODUCTION.md)
- [隔离消费端 HTML 端到端测试](html-e2e-consumer-test-prompt.md)

分享时使用稳定 `main` URL；实际执行仍以消费端固定 commit 的 Manifest 和入口为准。创建或接入提示词只负责首次接线，后续升级使用独立更新工作流。
