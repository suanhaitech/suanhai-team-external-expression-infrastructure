# 小组资产仓模板铺设工具

状态：`implemented`

本工具把基础设施仓中固定版本的小组资产仓模板复制到已经初始化 submodule 的消费端仓库。它只铺设空结构和待填写说明，不生成成员身份、项目事实、任务、作品或授权记录。

## 使用

先按照 [新仓建立流程](../../docs/group-asset-repository-bootstrap.md) 创建消费端并固定基础设施 submodule。再从消费端根目录运行：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/tools/group-asset-bootstrap/materialize_template.py --root . --dry-run
py -3 vendor/suanhai-team-external-expression-infrastructure/tools/group-asset-bootstrap/materialize_template.py --root . --apply
```

不带 `--apply` 时工具只预览。正式写入前会检查当前仓库 gitlink 与 submodule `HEAD` 完全一致，并预检所有目标路径；已有相同文件会保留，任何内容不同的冲突会让整次操作在写入前失败。工具不会覆盖文件、安装 submodule、创建提交或推送。

模板铺设成功后，Agent 还需按初始化 Harness 与负责人逐项核对身份和项目上下文。当前工具不负责访谈，也不把推断内容写成已确认事实。

工具核对固定版本、URL 与入口位置，不解析或替代完整 Manifest Schema 校验；能力可用性仍以 Manifest 和基础设施 CI 为准。所有待写内容先准备在 staging 目录，再独占创建目标文件，避免覆盖预检后新出现的文件。普通写入失败会回滚本次创建的文件和空目录；清理失败会报告具体残留。断电、强制终止和并发修改不具备事务保证，重试前应核对现场。
