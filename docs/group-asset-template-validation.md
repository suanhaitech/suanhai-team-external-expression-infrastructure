# 小组资产仓模板 v1：本地验收记录

日期：2026-10-29。开发分支：`codex/feat-group-asset-template`，基线 `2797d8349b313b2f4dd17a8106c74ee03583475f`。本文记录尚未提交的开发实现验证，不声称该版本已经可从远程获取。

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

跨平台最终记录：Windows Python 3.12 共运行 48 项，45 项通过、3 项因符号链接权限跳过；Linux Python 3.12 共运行 48 项，47 项通过、1 项 Windows junction 专项跳过。Linux 覆盖了 Windows 无权限执行的符号链接测试；Windows junction 测试实际通过。模板专项包含 17 项，覆盖无首次父仓提交和任务循环衔接。

Manifest 使用 WSL Ubuntu 24.04 临时解包的 Ruby 3.2.3 验证：当前 6 项能力通过，2 个有效 fixture 通过，5 个非法 fixture 均按预期拒绝。临时运行时未安装到系统、未修改 PATH。远端 CI 仍使用 Ruby 3.3，须在后续授权推送后运行；本地结果不代替远端 CI。

## 尚需真实 Agent 试用

脚本测试能证明文件与版本关系，不能证明所有 Agent 客户端会自动读取规则，也不能证明真人访谈体验。下一步按 [冒烟测试第 7 节](consumer-repository-smoke-test.md#7-新小组模板首启和初始化访谈) 在隔离小组仓试用：

1. 在根目录启动全新会话，先只读识别未初始化状态和 Manifest 能力；
2. 输入真实使用者角色、小组定位与边界，观察 Agent 是否分轮提问并持久化进度；
3. 分别验证零项目、多个项目与切换会话后的续接，不把项目空白模板当事实；
4. 初始化满足当前工作需要后，提出真实需求，确认任务编号和报告输出进入 `reports/`；
5. 记录客户端、实际命令、固定 commit、通过项与偏差，再决定迁移大工仓。

本轮未迁移大工仓、未创建其他真实小组仓、未实现新的 HTML 渲染或检查工具。模板铺设没有断电、强制终止或并发修改事务保证；失败清理不能完成时会报告残留。
