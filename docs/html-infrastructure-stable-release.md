# HTML 基础设施稳定发布与消费端迁移说明

本轮将 develop 已集成的 HTML 组合、场景、交互与项目汇报改进提升到稳定 `main`。发布候选及稳定提交的验证以各自 GitHub Actions 结果为准，不用历史绿灯替代当前检查。`develop` 继续集成下一轮改动；能力的 `implemented / experimental` 标记保持不变。稳定分支提供可复现的发布基线，不代表所有浏览器、设备或内容都已完成验收。

## 发布范围

- 完整工作流放在 `workflows/`，可复用模板、组件、样式、运行时、Schema 和工具放在 `infrastructure/<领域>/`；不强制拆分子工作流。
- Manifest schema v2 按固定提交登记真实能力，包括单页组合、页面计划与局部修订、原图阅读器、素材登记及已有 HTML 制作/检查工具；不从目录数推断可用能力。
- 新物料化默认配齐工具栏/公式与原图阅读器；增量参数继续兼容。演示稿全屏底栏持续隐藏且不可聚焦，下沿指针/触摸不唤出，Esc退出后恢复。旧作品不会因更新 gitlink 自动改写。
- 项目汇报固化一页一个主判断、互补证据/来源/边界、图片主视图可读、讲者备注及计划核对规则；已有单页/组件复用，未新增 source-map Schema、专用校验器或固定项目经理套稿。

父仓 gitlink 是消费端实际使用版本的唯一事实源。本文中的验收提交仅为历史证据，不是需要同步维护的第二份版本锁。

## 验证依据与限制

本轮先合入 develop，等待该集成提交双平台全量与 Manifest 门槛通过，再由 develop 向 main 发 PR，提前执行双平台全量；合入 main 后核对稳定提交的完整检查。以下目录迁移及早期消费端记录为历史证据，不代表本轮真实消费端试用已完成。当前工程回归使用中性合成素材，两个不同真实消费端的试用仍按[项目汇报验证门槛](project-report-reusable-assets.md)推进。

集成基线 `55469ab2aa6aa97b0c7a73e60a097deaf37b4f10` 的 [CI 41330210244](https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure/actions/runs/41330210244) 通过 Ruby Manifest 校验和 Windows、Ubuntu Python 回归。本次提示词及文档修订另由发布候选 PR 的同一套 CI 检查，只有全部通过的提交才能进入稳定分支。

消费端本地隔离试用记录显示：任务循环走到 `review`，物料化 117 个文件，未编辑的 116 项共享文件哈希保持一致；五类语义组件装配成功，公式实际渲染，本地 PDF 导出完成。这些结果证明共享资产可复用，不构成项目事实确认、页面发布授权或时间/token 节省的量化结论。

仍需明确报告的限制：

- 本地试用没有执行官方 Ruby 校验；官方结果来自上述 CI。
- Playwright 视口检查未执行，独立 headless 检查最小实际宽度为 504px，不能当作真实 390px 手机视口通过。
- 全屏、显示模式和浏览器打印按钮的逐项点击，以及 PDF 打印版式仍需针对交付页面检查。
- 浏览器检查与 PDF 导出依赖本机运行时；不可用时保留 `not-run`，不自动安装或伪造通过。

## 本仓发布与消费端升级顺序

1. 从 `develop` 建短期分支实现，通过受影响检查并提交 PR 到 develop。
2. PR 快速档通过后合入 develop，等待集成 SHA 的 Windows/Ubuntu 全量回归与 Manifest 门槛通过。
3. 创建 develop → main 发布 PR，检查完整差异并等待发布 PR 双平台全量和 Manifest 通过后合并。
4. 核对 main 稳定提交的 CI、本地/远端指针及工作区，清理本任务短期分支；不移动旧标签，不强推。
5. 消费端按更新工作流固定该完整 SHA，复用基础设施的完整回归记录，执行自身接入与实际能力冒烟。已有 HTML 需从新固定版本物料化到新版本目录，保留历史字节与证据。

本轮仅发布基础设施，不自动修改外部公共模板仓或已有小组仓的 gitlink。建仓、接入、HTML 制作和更新入口仍按 Manifest 路由；启动/接入提示词负责首次接线，日常执行读取固定版本工作流，不能靠复制旧提示词获得新能力。

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
| `templates/html-report/project-report-v1/` | `infrastructure/html/page-templates/project-report-v1/` → `infrastructure/html/templates/presets/project-report-v1/` |

保留小组自有规则与已确认上下文，只修正仍在使用的引用，不为迁移重写历史评审证据。按 Manifest 的能力 ID 发现入口，避免长期硬编码工具路径。新 gitlink 未提交前完整 preflight 会发现父仓 HEAD 与 index 不同，此时使用更新工作流规定的提交前核对；不要为了让预检通过擅自提交。

## 当前对外提示词入口

- [没有小组仓：创建并初始化](../workflows/group-asset-repository-create-and-initialize/CREATE_AND_INITIALIZE.md)
- [已有仓：接入基础设施](../workflows/infrastructure-adoption/ADOPT_EXISTING_REPOSITORY.md)
- [制作 HTML 页面](../workflows/html/production/START_HTML_PRODUCTION.md)
- [隔离消费端 HTML 端到端测试](html-e2e-consumer-test-prompt.md)

分享时使用稳定 `main` URL；实际执行仍以消费端固定 commit 的 Manifest 和入口为准。创建或接入提示词只负责首次接线，后续升级使用独立更新工作流。
