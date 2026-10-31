# 首版路线图

## 当前阶段：骨架和协议

目标是让未来的消费端能够可靠发现共享能力，同时明确尚未实现的边界。

- 建立仓库目录和中文维护说明；
- 固定 `manifest.yml` 和 Manifest Schema；
- 提供 Ruby 标准库校验脚本与 GitHub Actions；
- 保留 HTML 技能、模板、Harness、预览和检查目录的计划说明；
- 只有已完成许可登记、离线核验和消费端试用的能力才写入 `capabilities`。
- 复合工作流以 `kind: workflow` 注册，工作流 Harness 通过 `uses` 声明已注册的依赖；工具、模板、技能和检查器保持各自的能力边界。

本阶段新增的消费端 Harness 协议，先以文档和人工冒烟测试验证。消费端必须显式接入 Bootstrap 规则，才能让 Agent 读取这套协议；它约束 Agent 的读取顺序、任务路由、来源边界、停止条件和评审收口。当前 HTML 页面模板、语义组件和物料化工具已通过 Manifest 暴露，其他 HTML 工程能力仍按下文边界处理。

## 当前增量：可恢复的任务循环

实现 `expression.task-loop` 与 `expression.task-record`，并接入 `html.project-report-v1` 模板，提供草案、对齐、反馈、暂停、完成和按编号恢复。模板验证先使用隔离测试任务，不把测试标识当作真实项目或确认。详见 [任务循环验证](task-loop-validation.md)。

## 下一阶段：HTML 能力切片

当前已新增通用小组资产仓模板、只创建缺失文件的铺设工具、初始化访谈 Harness、组长可直接转发的建仓初始化提示词，以及既有仓库首次接入基础设施工作流。新模板采用 `topics/` 与 `reports/`，支持零到多个项目并保留旧仓 `works/` 兼容；既有仓接入流程不迁移其目录结构，由一次性提示词授权 Agent 固定 submodule 并安装消费端根 Harness；已有正确 submodule 时仍会补装缺失的 Harness。接入后的日常能力路由依赖该根文件和 Agent 客户端的加载行为。入口见[小组仓建立流程](group-asset-repository-bootstrap.md)、[小组仓代建与初始化流程](group-asset-repository-create-and-initialize.md)和[既有仓库接入工作流](../workflows/infrastructure-adoption/ENTRYPOINT.md)。

已在开发线加入通用 HTML 制作工作流 `expression.html-production`、页面模板包和离线语义组件包 `html.semantic-components-v1`。呈现形式层使用 `formats/`：网页与未来的文档、演示文稿并列；网页的 HTML 实现位于 `formats/web/html/`，页面模板位于 `page-templates/`，组件位于同级的 `components/`。组件包以 `package.yml`、`index.yml`、foundation、layout、semantic、theme 和 examples 分层，Agent 可以先按机器可读目录选择组件，再读取单组件契约和模板。工作流规定任务登记、澄清、来源、内容结构、版本化产物、反馈和人工收口。两者适用于公共模板仓和保留自有目录的既有消费端。

已增加 `html.materialize`，可按 Manifest 能力 ID 将已登记页面模板和组件包安全复制到已对齐任务的版本目录，并记录来源 commit、能力版本和文件哈希。Agent 不再逐文件手工复制基础设施资产；它仍负责选择、填充项目内容和人工评审。

仍需实现的 HTML 工程能力包括：浏览器预览/截图、HTML 与资源检查、真实多视口和打印验收、无障碍检查、离线数学公式渲染。能力实现前不得通过工作流或目录描述暗示这些工具可调用。优先根据组件包和实际消费端任务反馈确定内容协议与检查器接口，再逐项将已实现入口加入 Manifest。内容判断、专业准确性和对外授权仍由真人负责。

## 再下一阶段：真实消费端验证

创建大工项目对外表达资产仓库，将本仓库作为 submodule 固定一个可获取的 commit，用“大工项目概览与当前进展”HTML 汇报页验证端到端流程。

## 回流原则

真实任务中发现的通用改进，先去除项目私有事实，再作为独立变更回流本仓库。项目专属页面、客户资料和未经确认的判断不回流。
