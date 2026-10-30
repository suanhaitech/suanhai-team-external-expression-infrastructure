# 消费端 submodule 版本协议

本协议用于通过 Git submodule 使用共享基础设施的消费端。它把“实际使用哪个版本”和“远端当前指向哪里”分开处理：父仓库提交中的 `160000` gitlink 是复现事实，远端 `main` 只用于只读比较，不能成为自动跟随的版本来源。

当消费端更新到 Manifest schema v2 后，`consumer.submodule-update` 是受控更新工作流，入口见 [`workflows/submodule-update/ENTRYPOINT.md`](../workflows/submodule-update/ENTRYPOINT.md)；旧版本消费端仍只能按本协议手工执行显式升级，不能因为远端出现新提交而自动漂移。

## 预检工具

Manifest 中的 `consumer.submodule-preflight` 指向 `tools/submodule-preflight/submodule_preflight.py`。工具只使用 Python 标准库和 Git CLI，所有 Git 命令均为查询操作。在消费端父仓库根目录执行：

```powershell
python vendor/suanhai-team-external-expression-infrastructure/tools/submodule-preflight/submodule_preflight.py --root . --path vendor/suanhai-team-external-expression-infrastructure
```

不传 `--path` 时，工具从父仓库 `.gitmodules` 读取全部 submodule。多个 `--path` 可重复使用。升级候选必须显式传入完整 40 位 commit：

```powershell
python vendor/suanhai-team-external-expression-infrastructure/tools/submodule-preflight/submodule_preflight.py `
  --root . `
  --path vendor/suanhai-team-external-expression-infrastructure `
  --candidate <candidate-commit> `
  --require-remote-head
```

输入约束如下：

- `--root` 必须是父仓库根目录；`--path` 必须是仓库相对 POSIX 路径；
- 默认只读远端 `origin` 的 `refs/heads/main`，可用 `--remote-name` 和 `--remote-ref` 指定；
- `--candidate` 只验证对象是否存在以及与远端指针的关系，不会 checkout；
- `--skip-remote` 只适用于无网络的离线检查，结果会明确标记为 `skip`；
- 每个 Git 查询受 `--timeout` 限制。远端查询可能触发 Git 的凭据助手，但工具不打印凭据、不写入凭据、不执行 fetch。

JSON 输出的顶层版本为 `submodule-preflight.v1`（由 `schema_version: 1` 和 `tool` 标识），每个 submodule 包含：

- `gitlink_committed`：父仓库 `HEAD` 中的固定 commit；
- `gitlink_index`、`parent_head`：用于发现已暂存但尚未提交的 gitlink 变化；
- `submodule_head`、`initialized`、`submodule_clean`：本地检出和工作树状态；
- `remote_url`、`remote_ref`、`remote_sha`：脱敏后的远端只读快照；
- `candidate`、`checks`、`ok`：显式候选和逐项结果。

每个 submodule 还提供 `status`：`locked` 表示本地 gitlink、检出提交和工作树一致且远端比较符合要求；`dirty` 表示父仓或 submodule 工作树有未提交变化；`missing` 表示 submodule 未初始化或固定对象不可读取；`update-available` 表示显式候选或远端 ref 与当前固定版本不同；`unknown` 表示无法获得远端快照。`update-available` 只是待审查信号，不会触发升级。

退出码为 `0`（所有必需检查通过）、`1`（检查失败或发现漂移）和 `2`（参数、Git 环境或查询错误）。`remote_sha` 与固定 gitlink 不同本身只表示远端发生了变化；只有传入 `--require-remote-head` 时才把这种差异视为失败。远端分支可能移动，工具不在没有 fetch 的情况下声称两个 commit 存在祖先关系。

预检不会写工作树、index、refs、submodule 配置或父仓库文件，也不会生成锁文件。它不能替代权限系统、Manifest 校验、真实任务试用或真人评审。

## 显式升级

升级必须是消费端的一个可审查任务，按消费端总 Harness 从集成分支创建短期分支；如果消费端没有 `develop`，从默认分支创建短期分支，但不直接修改默认分支：

1. 记录父仓库 commit、旧 gitlink、submodule `HEAD` 和工作树状态，并运行一次预检；
2. 在基础设施仓库选择已验收的不可变 commit，记录其来源和兼容性说明；不要使用 `git submodule update --remote`；
3. 由操作者显式在隔离工作树中 checkout 候选 commit，然后运行预检、基础设施 Manifest 校验、消费端冒烟测试和必要的真实任务试用；
4. 只暂存 submodule 路径，核对 `git diff --cached --submodule`，在消费端记录旧 SHA、新 SHA、测试结果、兼容性风险和评审结论；
5. 按消费端既有流程提交、审查并合入集成分支；若没有 `develop`，按其默认分支治理规则合入。稳定版本再按消费端发布流程进入稳定分支。

预检工具不执行第 2 至第 5 步。这样每个消费端可以保留自己的审批人、测试矩阵和发布记录，同时共享相同的事实核对格式。

## 失败回退

升级未提交时，确认没有其他操作者的工作后，显式 checkout 已记录的旧 SHA，重新运行预检，再暂存 gitlink。升级已经提交时，优先在消费端创建 `git revert <升级提交>`，保留完整审计链。旧对象不在本地时，只能在明确授权下按旧 SHA 获取；禁止用 `reset --hard`、`clean` 或强制推送覆盖未知修改。

回退记录至少包括：升级父仓提交、旧/新 gitlink SHA、失败证据、回退提交、预检输出和恢复后的验证结果。脏工作树、旧对象缺失、合并冲突或远端访问失败时，工具只报告问题并停止，交由操作者判断。

## 两仓职责

基础设施仓维护本协议、预检工具、稳定的 JSON 输出约定和不依赖网络的临时 Git 回归测试。消费端维护实际 submodule 路径和远端配置、升级与回退任务、测试/审批记录及项目事实。协议不把消费端内容复制回基础设施仓，也不保存第二份版本锁。
