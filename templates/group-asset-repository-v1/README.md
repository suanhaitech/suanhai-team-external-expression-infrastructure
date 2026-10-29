# 小组对外表达资产仓库

初始化状态：待负责人确认；见 `context/initialization.md`。

本仓库承载小组的对外表达上下文、可复用内容、任务、报告与其他表达资产。初始文件来自基础设施的小组资产仓模板 v1，尚未填写小组身份、项目事实、任务或评审结论。基础设施作为 `vendor/suanhai-team-external-expression-infrastructure` submodule 固定引入；项目内容保存在本仓库。

## 结构

- `context/group/`：小组身份、职责边界、表达边界和通用来源规则；
- `context/projects/`：零个或多个项目的索引与独立上下文；
- `topics/`：经来源和状态管理、可在小组内部复用的内容资产；
- `tasks/`：一次具体表达工作的目标、受众、来源、责任与状态；
- `reports/`：报告类任务各轮次的产物；不承载系列、课程或书籍；
- `series/`、`courses/`、`books/`：分别归档系列、课程和书籍型资产；
- `tools/`：小组专属辅助工具；通用工具优先由基础设施提供；
- `reviews/`：事实评审、表达评审、修订和发布授权记录。

目录存在只说明预留了承载位置，不代表已经有真实对象或完成授权。`context/projects/_template/` 是复制用空白模板，不是一个已登记项目。

## 初始化

新仓采用“空 Git 仓库 → 添加基础设施 submodule → 固定明确 commit 并暂存 gitlink → 铺设模板 → 初始化访谈”的顺序。具体命令见基础设施的 `docs/group-asset-repository-bootstrap.md`。模板本身不嵌套 submodule，铺设工具也不代为添加或升级 submodule。

推荐在消费端从已初始化的 submodule 运行只读预览，再执行铺设：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/tools/group-asset-bootstrap/materialize_template.py --root . --dry-run
py -3 vendor/suanhai-team-external-expression-infrastructure/tools/group-asset-bootstrap/materialize_template.py --root . --apply
```

随后按照 submodule 中的 `harness/group-asset-repository/ENTRYPOINT.md` 完成真人访谈和待确认上下文核对。工具和 Agent 均不得编造项目资料或替负责人授权。

## 日常使用

新机器克隆已建立的小组仓库时使用 `git clone --recurse-submodules <本小组仓库URL>`，已有 clone 则运行 `git submodule update --init --recursive` 还原父仓固定版本。不要重复铺设模板。

在本仓库根目录启动 Agent：首次说明“请引导我初始化小组资产仓”；日常直接提出真实工作需求；续作时说明“继续任务 EXPR-…”。Agent 应先读取根规则和 Manifest，再选择初始化或任务循环。对没有自动加载 `AGENTS.md` 的客户端，需要显式要求它先读取本文件和 `AGENTS.md`。
