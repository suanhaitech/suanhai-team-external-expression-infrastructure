# HTML 模板与组件物料化工具

能力 ID：`html.materialize`

工具将已登记的页面模板和组件包复制到消费端已对齐任务的版本目录，形成可继续编辑的本地页面骨架。它不生成项目事实，不修改基础设施 submodule，不提交或推送。

## 前置条件

- 从消费端仓库内固定的基础设施 submodule 运行；默认从当前脚本位置推导路径，自建仓也可用 `--submodule-path` 显式指定；
- 父仓 HEAD 与 index 中的 submodule gitlink 一致，submodule 干净；
- `tasks/<任务编号>/task.json` 已进入 `working`，且任务当前修订固定的基础设施 commit 与当前 gitlink 一致（创建时或授权换版 feedback 后记录）；
- `brief.output` 已明确为稳定的 `<输出根>/<任务编号>`；工具按当前任务修订生成 `vNNN` 目录，也兼容旧记录中已经写入的 `<输出根>/<任务编号>/vNNN`；
- 页面模板、可选响应式布局包和组件包均已在当前 Manifest 注册。
- 默认运行时 `html.runtime-kit-v1` 与 `html.image-viewer-v1` 必须在 Manifest 注册；工具自动复制完整交互与本地 KaTeX。显式 `--runtime-kit-id` 是增量，重复 ID 去重；不扫描目录自动启用未知包。

## 两阶段操作

先预览计划：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/infrastructure/html/tools/materialize/materialize_html.py `
  --root . `
  --task-id EXPR-20261031-1234abcd `
  --template-id html.project-report-v1 `
  --layout-id html.responsive-layout-v1 `
  --runtime-kit-id html.runtime-kit-v1 `
  --component-package-id html.semantic-components-v1 `
  --component-id status.phase `
  --component-id action.next-step
```

核对输出路径、submodule commit、模板/组件版本和 `plan_sha256` 后，显式应用同一计划：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/infrastructure/html/tools/materialize/materialize_html.py `
  --root . `
  --task-id EXPR-20261031-1234abcd `
  --template-id html.project-report-v1 `
  --layout-id html.responsive-layout-v1 `
  --runtime-kit-id html.runtime-kit-v1 `
  --component-package-id html.semantic-components-v1 `
  --component-id status.phase `
  --component-id action.next-step `
  --apply `
  --expect-plan-sha256 <预览返回的SHA256> `
  --expect-task-version <预览返回的任务记录版本>
```

任务编号示例必须替换为真实任务编号。工具默认 `reports/`；自建仓可使用 task brief 中已对齐的输出根，但该根必须是任务工具默认允许目录或 `.suanhai/expression.json` 显式声明的目录。

任务匹配已登记场景时，可以显式传入场景画像 ID：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/infrastructure/html/tools/materialize/materialize_html.py `
  --root . `
  --task-id EXPR-20261031-1234abcd `
  --scenario-id expression.scenario.course-learning-v1 `
  --container-id html.container.presentation-deck-v1 `
  --page-id html.single-page.cover.editorial-v1 `
  --page-id html.single-page.agenda.route-v1 `
  --page-id html.single-page.content.method-v1
```

当前登记的场景画像位于基础设施根目录 `scenarios/catalog.json`。工具拒绝未知或未实现的场景，并把 `id`、版本和画像路径写入 `report.yml`、`materialization.json` 与 dry-run 结果。场景只记录任务分类，不会替任务简报选择输出根；输出位置仍以已对齐的 `brief.output` 为准。未传 `--scenario-id` 的旧调用保持原格式。

逐页讲解有两种兼容路径：旧任务继续使用 `--template-id html.presentation-deck-v1`；新任务可以使用容器和有序单页模板组合：

```powershell
py -3 vendor/suanhai-team-external-expression-infrastructure/infrastructure/html/tools/materialize/materialize_html.py `
  --root . `
  --task-id EXPR-20261031-1234abcd `
  --container-id html.container.presentation-deck-v1 `
  --page-id html.single-page.cover.editorial-v1 `
  --page-id html.single-page.agenda.route-v1 `
  --page-id html.single-page.content.evidence-v1 `
  --page-id html.single-page.closing.action-v1
```

重复 `--page-id` 的出现顺序就是展示顺序；同一个页面变体可以安全重复使用。组合器复制单页样式和本地素材，替换容器示例页，生成唯一页码和 ID，并记录页面角色、变体、版本和来源。仅使用 `--page-id` 的旧调用保持兼容；新任务建议使用下面的完整页面计划。

## 完整页面计划与可选资产

`--page-plan tasks/<任务号>/page-plan.json` 取代重复的 `--page-id`，必须与容器搭配使用。协议见 `infrastructure/html/schemas/page-plan.schema.json`，中性样例见 `infrastructure/html/examples/records/page-plan.json`。每页保留稳定 ID、模板 ID、标题、职责、核心信息、来源 ID、回应关系、纯文本内容槽和默认隐藏备注。HTML 页面、目录与显示页码从同一清单生成，改变显示顺序不需要手改页面 ID。

```text
python materialize_html.py --root . --task-id <任务号> --container-id html.container.presentation-deck-v1 --page-plan tasks/<任务号>/page-plan.json --theme editorial-warm --layout-id html.responsive-layout-v1 --layout-id html.presentation-foundation-v1 --runtime-kit-id html.runtime-kit-v1 --runtime-kit-id html.image-viewer-v1
```

以上仍为预览，应用必须追加匹配的 `--apply --expect-plan-sha256 ... --expect-task-version ...`。主题为组件包中的可选令牌覆盖；布局包和运行时包可重复选择。原图阅读器与工具栏保持独立实现，默认同时装配；默认集合也写入预览、报告与物料化来源记录。底层 `inject_runtime_kit(None)` 保留兼容语义，不能代表新任务的默认策略。

单页 `template.yml` 可声明 `component_slots: [supporting]`（YAML列表写法）及 `<!-- SUANHAI_COMPONENTS:supporting -->` 插槽。页面计划使用 `components: [{"slot":"supporting","id":"content.definition"}]` 把包内已登记组件放入指定页。工具拒绝未声明插槽、未登记组件和不兼容白名单；不会猜测任意 HTML 的插入位置。组合模式不接受缺少目标页面的 `--component-id`。

`slots` 值是纯文本，自动转义。复杂表格、列表和图示应保留模板结构，在物料化的新版本里填充，不能把未审阅 HTML 作为字符串注入。填写结构插槽后需要检查语义是否仍适合原标签。共享样式使用 `shared_styles` 相对 `infrastructure/html` 声明；第一版共享CSS只接受无外部依赖的文件，其他包继续遵守原有显式资源协议。

## 安全局部修订

先通过任务循环反馈并进入下一轮 `working`，用完整新计划预览：

```text
python materialize_html.py --root . --task-id <任务号> --container-id html.container.presentation-deck-v1 --page-plan tasks/<任务号>/page-plan.json --baseline-version v001 --replace-page page-explanation
```

其余主题、布局、运行时和场景参数必须与基线保持一致。工具从同任务旧版本只读继承，新版本只替换指定页面；基线需有完整页面清单和物料化记录，非目标页逐字保留，并记录基线摘要及替换范围。检查目录、已识别的旧检查JSON和旧PDF导出结果不继承为本轮证据；原始来源PDF保留。自定义、未登记的旧导出不能自动辨识，需在修订计划中清理或迁移，并重新检查和导出。

第一版要求固定基础设施提交、容器、场景、主题、布局、运行时、全稿来源定义及简报设置、页面 ID 和顺序一致。插页、重排、升级公共资源或更换全局配置时使用完整装配，再做整稿检查。局部修订不能自动理解用户已在 HTML 中手改的目标页；完整页面计划需先表达该页要保留的内容，复杂手工结构应在新版本继续调整，不回写旧版本。

## 输出

工具把页面模板文件复制到 `brief.output` 对应的 `vNNN` 版本目录，将响应式布局包复制到 `assets/<布局ID转目录名>/`，将运行时包复制到 `assets/<运行时ID转目录名>/`，将组件包复制到 `assets/<组件包ID转目录名>/`，并把 `--component-id` 选择的语义 HTML 片段插入模板声明的组件插槽，同时在模板声明的样式、运行时脚本和工具栏插槽中加入相对资源引用。选择 `html.runtime-kit-v1` 时，页面获得 `data-math` 公式渲染、自动/窄屏/平板/桌面显示模式、全屏和浏览器保存 PDF 入口；运行时包不访问 CDN。`report.yml` 初始化任务元数据、模板/布局/运行时/组件选择和待确认授权状态；`materialization.json` 记录任务/修订、基础设施 commit、模板、布局、运行时、组件版本以及复制文件的 SHA-256。项目事实、来源清单和最终授权状态仍由 Agent 按工作流填充；工具只交付结构起点。

默认只预览，不写文件。应用时必须提供最近一次预览的计划摘要和任务记录版本。工具预检全部目标、拒绝覆盖不同内容、拒绝符号链接及越界路径；重复应用相同计划是幂等的，内容发生变化则停止，不覆盖用户修改。

工具只使用 Python 标准库。Manifest YAML 由仓库 Ruby CI 校验器做完整解析与 Schema 校验；本工具只读取本仓 schema v2 中固定格式的能力标量字段，遇到不支持的结构会失败关闭。
