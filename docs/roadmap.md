# 首版路线图

## 当前阶段：骨架和协议

目标是让未来的消费端能够可靠发现共享能力，同时明确尚未实现的边界。

- 建立仓库目录和中文维护说明；
- 固定 `manifest.yml` 和 Manifest Schema；
- 提供 Ruby 标准库校验脚本与 GitHub Actions；
- 保留 HTML 技能、模板、Harness、预览和检查目录的计划说明；
- 只有已完成许可登记、离线核验和消费端试用的能力才写入 `capabilities`。
- 复合工作流以 `kind: workflow` 注册，工作流 Harness 通过 `uses` 声明已注册的依赖；工具、模板、技能和检查器保持各自的能力边界。

本阶段新增的消费端 Harness 协议，先以文档和人工冒烟测试验证。消费端必须显式接入 Bootstrap 规则，才能让 Agent 读取这套协议；它约束 Agent 的读取顺序、任务路由、来源边界、停止条件和评审收口，但不声明 HTML 工具已经实现。

## 当前增量：可恢复的任务循环

实现 `expression.task-loop` 与 `expression.task-record`，并接入 `html.project-report-v1` 模板，提供草案、对齐、反馈、暂停、完成和按编号恢复。模板验证先使用隔离测试任务，不把测试标识当作真实项目或确认。详见 [任务循环验证](task-loop-validation.md)。

## 下一阶段：HTML 能力切片

当前已新增通用小组资产仓模板、只创建缺失文件的铺设工具、初始化访谈 Harness、组长可直接转发的建仓初始化提示词，以及既有仓库首次接入基础设施工作流。新模板采用 `topics/` 与 `reports/`，支持零到多个项目并保留旧仓 `works/` 兼容；既有仓接入流程不迁移其目录结构，由一次性提示词授权 Agent 固定 submodule 并安装消费端根 Harness；已有正确 submodule 时仍会补装缺失的 Harness。接入后的日常能力路由依赖该根文件和 Agent 客户端的加载行为。入口见[小组仓建立流程](group-asset-repository-bootstrap.md)、[小组仓代建与初始化流程](group-asset-repository-create-and-initialize.md)和[既有仓库接入工作流](../workflows/infrastructure-adoption/ENTRYPOINT.md)。

下一步实现 `html.external-expression` 的最小纵向能力：读取任务说明和获准来源，使用已登记模板形成 HTML，在本地预览并完成确定性检查。内容判断、专业准确性和对外授权仍由真人负责。

## 再下一阶段：真实消费端验证

创建大工项目对外表达资产仓库，将本仓库作为 submodule 固定一个可获取的 commit，用“大工项目概览与当前进展”HTML 汇报页验证端到端流程。

## 回流原则

真实任务中发现的通用改进，先去除项目私有事实，再作为独立变更回流本仓库。项目专属页面、客户资料和未经确认的判断不回流。
