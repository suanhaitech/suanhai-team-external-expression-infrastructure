# 对外表达任务循环

这是由消费端 Agent 执行的工作协议，配套工具只管理任务文件和校验状态，不调用模型、生成 HTML、调度 Agent 或实施权限隔离。运行依赖为 Python 3.10+ 标准库。任务、反馈和产出保存在消费端，基础设施 submodule 默认只读。

## 入口选择

- 用户只要求调查：只读项目上下文、Manifest 和现有任务，不创建任务或修复环境。
- 用户要求开始制作：先建立任务草案，可保存尚未明确的问题，不必等所有字段齐全才登记。
- 用户给出任务编号：先读取该任务，再决定续作、评审、暂停恢复或开启新一轮。

先核对消费端根规则，再使用本入口。安装依赖、修复权限、清理文件、提交、推送、部署等副作用须符合实际用户授权；`--test` 和工具参数不产生额外授权。

## 两层循环

**用户协作循环**：需求草案 → 关键问题澄清 → 记录共识 → 展示可评审产出 → 收集反馈 → 修订 → 用户确认本轮版本。优先询问影响方向的问题，不为了格式完整而一次抛出所有字段。

**内部制作循环**：读取本任务的已确认目标和来源 → 从 Manifest 选择实际可用能力 → 制作 → 检查 → 修复 → 记录检查证据。已对齐范围内的小改动可以连续执行；受众、范围、事实边界或完成标准发生变化时回到澄清。检查连续两轮没有进展时，记录失败命令、影响和下一步，停止重复尝试，不自动修复环境。

没有已实现的 HTML 能力时，仍可澄清任务、组织内容和记录待办；停止相应共享能力调用。若用户选择由 Agent 自身编程能力制作，需明确这是另一路线，不能把结果当成基础设施 HTML 能力测试通过。

## 持久化约定

```text
tasks/<任务编号>/
├── task.json   # 任务状态、简报、历史、产出引用的唯一事实源
└── task.md     # 由工具生成的阅读视图，不手工维护第二份状态
reports/<任务编号>/v001/<产出文件>
reports/<任务编号>/v002/<产出文件>
```

报告类任务默认使用 `reports/`；系列、课程和书籍按消费端约定放在 `series/`、`courses/` 或 `books/`。旧消费端的 `works/` 仍受兼容支持，不自动迁移历史产物。自建仓可通过 `.suanhai/expression.json` 声明自己的额外顶层产出目录；不能把产出放进 `vendor/`、`.git/`、`context/` 或 `tasks/`。任务号形如 `EXPR-20261028-a1b2c3d4`，在当前仓库内定位，不是跨仓全局任务编号。

`task.json` 记录用户请求、简报、状态、当前轮次、操作版本、历史、下一步和产出路径/摘要。产物可以是单个文件或包含 HTML、CSS 和本地资源的自包含目录；目录 SHA-256 覆盖相对路径及所有文件内容。用户原话用于记录对齐或完成的依据，不能由 Agent 编造；工具只检查记录是否存在，无法判断发言身份或授予发布权限。`mode: test` 是测试标识，不能变成真实业务或真人确认。

## 工具命令

从消费端仓库根目录执行下列命令，`ID` 替换成实际任务号，`N` 替换成刚刚 `show` 返回的 `version`。所有已有任务的写入都要求 `--expect-version N`；版本冲突时先重新读取并保留另一操作者的变更，不重试覆盖。

```powershell
python vendor/suanhai-team-external-expression-infrastructure/harness/task-loop/scripts/task_loop.py --root . create --title "用户给出的任务名" --request "用户提出的实际需求"
python vendor/suanhai-team-external-expression-infrastructure/harness/task-loop/scripts/task_loop.py --root . list
python vendor/suanhai-team-external-expression-infrastructure/harness/task-loop/scripts/task_loop.py --root . show ID
```

登记共识草案（未知字段保持待澄清；正式对齐前补齐关键项）：

```powershell
python vendor/suanhai-team-external-expression-infrastructure/harness/task-loop/scripts/task_loop.py --root . brief ID --expect-version N --audience "受众" --purpose "用途" --scope "范围" --output "reports/ID" --acceptance "完成标准" --source "context/projects/PROJECT/project-overview.md"
```

记录真实的用户对齐意见后，进入执行：

```powershell
python vendor/suanhai-team-external-expression-infrastructure/harness/task-loop/scripts/task_loop.py --root . event ID --expect-version N --type align --note "关键目标已对齐" --user-quote "实际用户原话"
python vendor/suanhai-team-external-expression-infrastructure/harness/task-loop/scripts/task_loop.py --root . event ID --expect-version N --type start --note "开始已授权范围内的制作" --next-action "完成首版内容结构"
```

每条状态写入都会增加 `version`；上面的 `N` 不能重复使用，先读取最新任务再执行下一条。`render` 只重建阅读视图，不改变状态或版本。

## 状态及反馈

| 事件 | 结果 | 使用条件 |
| --- | --- | --- |
| `align` | clarifying → ready | 关键简报齐备，记录实际用户对齐原话 |
| `start` | ready → working | 开始已确认范围内的制作 |
| `checkpoint` | 保持状态 | 保存做了什么、检查结果、问题和下一步 |
| `review` | working → review | 单文件或自包含目录真实存在，记录内容及资源路径的 SHA-256 |
| `feedback --scope minor` | ready/working/review → 新轮次 | 局部调整，目标共识保持有效；ready保持ready，其余进入working |
| `feedback --scope scope` | ready/working/review → clarifying，新轮次 | 受众、目标或范围变化，需要重新对齐，无需等到首个产出才可记录 |
| `pause` / `resume` | 保存并恢复原状态 | 记录暂停原因及恢复后的下一步 |
| `complete` | review → completed | 用户确认本轮，产出摘要未改变 |
| `reopen` | completed → working 或 clarifying | 保留完成记录，按反馈类型开启新轮次 |

反馈原话、检查命令及结果、未解决事项应进入事件 `--note`，下一步进入 `--next-action`。这份记录应足以让新 Agent 接着做，不要求保存聊天全文或内部推理。

```powershell
python vendor/suanhai-team-external-expression-infrastructure/harness/task-loop/scripts/task_loop.py --root . event ID --expect-version N --type review --note "结构草稿完成，等待用户意见；HTML尚未生成" --artifact "reports/ID/v001/outline.md" --next-action "请用户评审结构"
python vendor/suanhai-team-external-expression-infrastructure/harness/task-loop/scripts/task_loop.py --root . event ID --expect-version N --type feedback --scope minor --note "实际用户反馈；记录相应调整" --next-action "生成v002并检查"
```

每轮使用新的产出路径，不能覆盖以前的评审版本或已确认版本。工具记录文件或目录摘要并拒绝复用历史产出路径，无法阻止其他程序直接改文件；本机制不是文件访问控制。

## 暂停、完成与恢复

暂停前记录：当前版本、已做工作、检查结果、未解决问题和下一步。新会话拿到编号后先 `show`，核对当前仓库/submodule 和产出是否仍存在，再复述任务目标与当前进度。状态为 paused 时按用户续作要求 `resume`；completed 时按新需求 `reopen`。

如果来源缺失、旧摘要不符、用户决定相互冲突，先说明差异，不根据旧聊天猜测或补造。`show` 对结构合法记录返回摘要及只读 `_diagnostics`，`list` 逐项显示损坏记录的错误，不因一条坏记录隐藏其他任务；这些诊断不写回 JSON。读取和诊断不改变状态；来源/产出缺失或已确认历史产物被改写时，写入会拒绝。待评审产物被外部改动时仍可登记反馈，但不能沿用旧摘要完成本轮。JSON 本身损坏时可只读查看原文件，不据此重新创建同一任务。

`validate ID` 严格检查记录与历史产出；`render ID --expect-version N` 只用于在用户授权下重建阅读视图，不能清理其他文件或改写事实。简报的 output 可用作品目录作为稳定目标位置，具体每轮文件以 artifacts 中记录的路径为准。

只有实际用户认可才能记录 `complete --user-quote`。完成意味着本轮内容达到约定，不等于专业技术验收或发布授权。收口时告知用户：任务号、产出路径、当前轮次、仍存限制，以及“以后可通过此任务号继续讨论”。

跨设备续作还要求消费端任务与产出文件已经按用户授权同步；编号本身不会自动传输文件。Git 操作仍遵守用户授权，不能因要恢复任务而自行提交或推送。

## 故障处理与验证

JSON 使用版本冲突检查、写锁和原子替换，生成阅读视图失败时应报告 JSON 与视图各自的状态。不要删除不明锁文件或自动回滚用户文件；保留错误并说明人工恢复方式。多个文件、多个仓库的写入不构成分布式事务。

通用工具回归与跨会话验证见 [任务循环验证流程](../../docs/task-loop-validation.md)。测试数据只放隔离临时仓库，并明确 `mode: test`，不进入真实任务列表或项目事实。
