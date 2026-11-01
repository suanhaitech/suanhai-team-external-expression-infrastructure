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

## 第一次使用

先打开公开模板仓 `https://github.com/suanhaitech/suanhai-team-group-asset-template`，点击 **Use this template → Create a new repository** 创建本小组自己的 GitHub 仓库，再克隆新建的小组仓。模板仓已经配置基础设施 submodule 和固定 gitlink；成员无需单独克隆基础设施仓，也无需手工添加 submodule 或再次铺设模板。

本机需要 Git、Python 3.10+ 和可在仓库目录工作的 Agent 客户端。Windows 可用 `py -3 --version` 检查 Python；Linux/macOS 使用 `python3 --version`。

```text
git clone --recurse-submodules <本小组仓库URL> <本地目录>
cd <本地目录>
```

在本小组资产仓根目录启动 Agent，输入：

> 初始化小组资产仓。

根 `AGENTS.md` 会让 Agent 核对固定基础设施版本，通过 Manifest 发现 `consumer.group-asset-onboarding`，分轮引导当前使用者、小组身份和零到多个项目的上下文初始化。说“进行项目初始化”也可以，Agent 会先区分本次是小组首启，还是给已有小组增加或完善一个项目。

如果客户端没有自动读取 `AGENTS.md`，输入：

> 请先读取本仓根目录 README.md 和 AGENTS.md，再引导我初始化小组资产仓。

初始化进度保存在 `context/initialization.md`。未知内容可以保留待确认，不为填齐字段编造事实；换机器或换成员不会重置小组共享身份。

## 日常使用

新机器克隆已建立的小组仓库时仍使用 `git clone --recurse-submodules <本小组仓库URL>`。普通 clone 漏掉 submodule 时，初始化请求下 Agent 可用下面的命令恢复父仓固定版本；只读请求只诊断，不恢复：

```text
git submodule update --init --recursive -- vendor/suanhai-team-external-expression-infrastructure
```

该命令还原 gitlink 记录的版本，不追随远程分支。不要重新运行 `git submodule add`、`update --remote` 或模板铺设工具来修复已有小组仓。

在本仓库根目录启动 Agent：首次说明“请引导我初始化小组资产仓”；日常直接提出真实工作需求；续作时说明“继续任务 EXPR-…”。Agent 应先读取根规则和 Manifest，再选择初始化或任务循环。对没有自动加载 `AGENTS.md` 的客户端，需要显式要求它先读取本文件和 `AGENTS.md`。

完整首启和新机器测试流程见基础设施 `docs/group-asset-repository-bootstrap.md`。模板结构更新与基础设施版本升级分别评审；父仓 gitlink 是实际基础设施版本的唯一事实来源。

如果需要检查或更新基础设施 submodule，在本仓根目录向 Agent 说明“检查基础设施版本”或“更新基础设施 submodule”。Agent 应从 Manifest 路由到 `consumer.submodule-update`，先运行只读预检，展示明确目标 commit 和影响，再按用户确认在短期分支中更新父仓 gitlink。不会因为远端出现新提交而自动升级。
