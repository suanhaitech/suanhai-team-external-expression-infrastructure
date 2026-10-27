# Agent 协作约定

本仓库是 Suanhai 团队共享的对外表达基础设施工程仓库。它提供可复用的工具、技能、模板、Harness 和检查协议，不承载具体小组的项目事实或对外表达资产。

## 当前状态

- 仓库首版只完成骨架和 Agent 发现协议；
- `manifest.yml` 是能力发现的唯一入口；
- `capabilities` 为空表示当前没有可调用能力；
- `skills/`、`templates/`、`harness/`、`tools/`、`checks/` 下的占位目录均为 `planned / not implemented`；
- 不得因为目录存在，就把计划能力描述为已经可用。

## 开发边界

- Chaos 是当前仓库负责人和唯一开发者；
- 项目专属事实、客户资料、凭据、令牌和未经授权的数据不得进入本仓库；
- 不在这里实现项目任务、数据库、云端接口或部署流程；
- 不自动执行 Git commit、push、部署或正式发布；
- 工程检查通过不代表专业内容正确，也不代表对外发布已经获得授权。

## 分支约定

- `main` 是稳定版本，禁止强制推送和删除；
- `develop` 是集成分支；
- 日常修改从 `develop` 创建 `codex/feat-*`、`codex/fix-*` 或 `codex/chore-*` 短期分支；
- 合入 `main` 前必须通过 Manifest CI；当前不要求人工评审；
- 分支规则受 GitHub 仓库设置约束，文档约定不能替代服务端权限控制。

## 修改前检查

1. 确认当前分支和工作区状态；
2. 阅读 `README.md`、`docs/architecture.md` 和相关能力目录说明；
3. 判断改动是否属于共享、可复用的基础设施；
4. 更新 Manifest、Schema、说明和检查时保持一致；
5. 运行 `ruby scripts/validate_manifest.rb`，并检查最终 diff 不含凭据、缓存或构建产物。

新增能力时，先实现并验证真实入口，再把它加入 `manifest.yml`。不能把占位目录提前暴露给 Agent。
