# 小组资产仓模板 v1：验证与发布记录

日期：2026-10-29。开发分支：`codex/feat-group-asset-template`，基线 `2797d8349b313b2f4dd17a8106c74ee03583475f`。本文分别记录自动化检查、GitHub 模板分发和 Agent 交互试用，不以其中一项替代其他验收。

## 验证对象

- `consumer.group-asset-bootstrap`：核对固定 submodule 并铺设缺失的模板文件；
- `consumer.group-asset-onboarding`：引导使用者、小组身份、来源与零到多个项目的初始化访谈；
- 任务工具新增 `reports/` 支持，同时保留历史 `works/` 兼容；
- 新仓初始化、读取顺序、版本预检和日常任务入口的文档衔接。

## 自动化验证

基础命令：

```text
python -m unittest discover -s tests -p "test_*.py" -v
python -m unittest tests.test_group_asset_bootstrap -v
python -m py_compile tools/group-asset-bootstrap/materialize_template.py harness/task-loop/scripts/task_loop.py tests/test_group_asset_bootstrap.py
ruby scripts/validate_manifest.rb
git diff --check
```

所有测试仓库均在临时目录，以本地 Git 快照和真实 submodule 运行，不修改现有小组仓。模拟用户决定均标注为合成测试输入，任务使用 `mode: test`，不冒充真人确认。

已验证的行为：

- 新 clone 能初始化相同 gitlink，URL 和 submodule HEAD 均可核对；
- 没有父仓首次提交、gitlink 只在 index 中时仍可铺设；
- 默认和 `--dry-run` 不写文件，`--apply` 铺设后重复运行保持不变；
- 不同内容的既有文件、错误 URL、HEAD 漂移和脏 submodule 会被拒绝；
- 非法相对路径、越界符号链接和 Windows junction 会被拒绝；
- 普通文件阻挡父目录、半途复制失败和预检后出现文件时不覆盖用户内容，并回滚本次可清理文件；
- 模板仓可以通过任务工具完成测试草案、对齐、制作、`reports/` 产出登记、校验与合成测试确认，`task.json` 和 `task.md` 可读取；
- 上述流程保持 submodule 工作区干净，不替用户执行提交或推送。

初次本地记录：Windows Python 3.12 共运行 48 项，45 项通过、3 项因符号链接权限跳过；Linux Python 3.12 共运行 48 项，47 项通过、1 项 Windows junction 专项跳过。模板专项包含 17 项，覆盖无首次父仓提交和任务循环衔接。

第一次远端 CI 暴露两个 Windows 问题：TEMP 的 8.3 短路径和解析后的长路径比较导致误判越界，以及 CP1252 控制台不能输出中文 JSON。修复后，路径两端采用相同的解析边界，三个 Python CLI 在参数解析前统一 UTF-8 输出；新增短路径别名和 CP1252 子进程回归。

基础设施实现提交 `fa518eee92b728df84cc8019412ec68e3d7d5070` 的 [CI 40845365974](https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure/actions/runs/40845365974) 已通过；合入 `develop` 的集成提交 `524bcb059323c92d09401f44cfb8be65b4bcc4fe` 的 [CI 40847254371](https://github.com/suanhaitech/suanhai-team-external-expression-infrastructure/actions/runs/40847254371) 也已通过：

- Windows Python 3.12：54 项通过；
- Linux Python 3.12：54 项，53 项通过、1 项 Windows junction 专项跳过；
- Ruby 3.3 Manifest 检查：当前 6 项能力、有效 fixtures 和非法 fixtures 的预期拒绝均通过。

## GitHub 模板分发与新 clone

公开入口：[suanhaitech/suanhai-team-group-asset-template](https://github.com/suanhaitech/suanhai-team-group-asset-template)。仓库已设置 `is_template=true`，默认分支 `main`。

本次发布及测试固定值仅是验收快照，不是另一份版本锁：

| 对象 | 已核对的提交 |
| --- | --- |
| 独立模板仓 | `50b036e6ab0eb4631595ff8bf16a7e710aabe5cd` |
| 模板及生成仓的基础设施 gitlink | `524bcb059323c92d09401f44cfb8be65b4bcc4fe`（已合入基础设施 `develop`） |
| GitHub generate API 生成的隔离私有测试仓 | `suanhaitech/group-asset-template-e2e-v3-20261029`，`ad0958d52b40dca6cc1b7e4a4d47682034939ee6` |

实测结果：

- 模板源文件与独立模板仓对应文件一致，后者额外维护 `.gitmodules` 和真正的 `160000` gitlink，没有把基础设施复制为普通目录。
- GitHub generate API 保留了 `.gitmodules`、HTTPS URL、路径和固定 gitlink；生成仓的 `template_repository` 正确指向公开模板仓。不能只根据 GitHub 文档或目录存在推断这一点。
- Windows 全新 `git clone --recurse-submodules` 成功；父仓 gitlink 与基础设施 HEAD 一致，submodule 干净，本地预检 `ok: true`。
- 另一次普通 clone 的 submodule 初始为未初始化；执行 `git submodule update --init --recursive -- vendor/suanhai-team-external-expression-infrastructure` 后恢复相同固定提交，父仓无变化。此项验证 Git 恢复命令，不冒充 Agent 自动恢复的交互测试。
- 最终模板提交的 [CI 40848082367](https://github.com/suanhaitech/suanhai-team-group-asset-template/actions/runs/40848082367) 与 v3 隔离生成仓的 [CI 40848227080](https://github.com/suanhaitech/group-asset-template-e2e-v3-20261029/actions/runs/40848227080) 均在 Windows、Linux、macOS 通过递归 checkout、只读预检及初始化入口检查。CI 不执行用户访谈，也不证明所有 Agent 客户端都能自动加载规则。

## Agent 冷启动与续接

在 v3 GitHub 生成仓中，用两次互相独立、未传入历史聊天的 Agent 会话测试：

- 首次输入“初始化小组资产仓”，Agent 核对当前 `524bcb0` 固定 submodule，预检通过；把合成候选分别写入初始化进度、小组身份、边界、来源文件；保留零项目索引，不创建项目目录、任务和作品；不提交或推送。
- 第二次只读续接“继续初始化小组资产仓”，Agent 从共享文件恢复演练状态，区分本轮操作者与小组身份，准确指出候选信息、负责人待确认事项和项目数量为零；检查记录无冲突，没有依赖上一会话聊天。只读续接未写文件、提交、推送或改 submodule。

隔离工作区的候选记录明确标为合成演练，不能当成真实团队事实、负责人确认或发布授权。该试验覆盖从公开模板生成到固定 submodule、Agent 落盘和新会话读取的主链路，不代表所有 Agent 客户端均会自动加载 `AGENTS.md`。

另一次直接运行 Codex CLI 沙箱探针时，其子进程环境缺少 `py -3`、`basename` 和 `sed`，所以当次预检失败；本次正式 Agent 测试环境中这些依赖可用，预检通过。这说明需要检查 Agent 工具子进程自己的 PATH，不能只验证桌面终端。测试未安装软件或改变系统配置。

## 真人与其他客户端的后续试用

脚本测试和隔离演练不能证明所有 Agent 客户端会自动读取规则，也不能替代真人访谈体验。按 [新机器测试手册](group-asset-repository-bootstrap.md) 在本小组仓中继续试用：

1. 在根目录启动全新会话，先只读识别未初始化状态和 Manifest 能力；
2. 输入真实使用者角色、小组定位与边界，观察 Agent 是否分轮提问并持久化进度；
3. 分别验证零项目、多个项目与切换会话后的续接，不把项目空白模板当事实；
4. 初始化满足当前工作需要后，提出真实需求，确认任务编号和报告输出进入 `reports/`；
5. 记录客户端、实际命令、固定 commit、通过项与偏差，再决定迁移大工仓。

本轮未迁移大工仓、未创建其他真实小组仓、未实现新的 HTML 渲染或检查工具。隔离测试仓仅承载演练，未提交真实身份、项目事实或专业材料。新机器上的 Agent 沙箱仍须确认 Python 和 Git 子命令依赖可访问；不能把桌面终端可用误认为 Agent 子进程可用。模板铺设没有断电、强制终止或并发修改事务保证；失败清理不能完成时会报告残留。
