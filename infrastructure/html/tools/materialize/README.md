# HTML 模板与组件物料化工具

能力 ID：`html.materialize`

工具将已登记的页面模板和组件包复制到消费端已对齐任务的版本目录，形成可继续编辑的本地页面骨架。它不生成项目事实，不修改基础设施 submodule，不提交或推送。

## 前置条件

- 从消费端仓库内固定的基础设施 submodule 运行；默认从当前脚本位置推导路径，自建仓也可用 `--submodule-path` 显式指定；
- 父仓 HEAD 与 index 中的 submodule gitlink 一致，submodule 干净；
- `tasks/<任务编号>/task.json` 已进入 `working`，且创建任务时记录的基础设施 commit 与当前 gitlink 一致；
- `brief.output` 已明确为稳定的 `<输出根>/<任务编号>`；工具按当前任务修订生成 `vNNN` 目录，也兼容旧记录中已经写入的 `<输出根>/<任务编号>/vNNN`；
- 页面模板、可选响应式布局包和组件包均已在当前 Manifest 注册。
- 如需页面内公式、显示模式、全屏和浏览器保存 PDF 入口，运行时包 `html.runtime-kit-v1` 也必须在当前 Manifest 注册；它会连同本地 KaTeX 资源一起复制。

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

重复 `--page-id` 的出现顺序就是展示顺序；同一个页面变体可以安全重复使用。组合器会复制每个页面的 `styles.css`、替换容器示例页、生成唯一页码和 ID；`report.yml` 与 `materialization.json` 都记录有序页面 ID，后者还保留角色、变体、版本和来源。组合模式目前不接受 `--component-id`，因为单页包尚未声明通用语义组件插槽；需要语义组件时使用完整预设路径，或先扩展单页契约并补充评审。

## 输出

工具把页面模板文件复制到 `brief.output` 对应的 `vNNN` 版本目录，将响应式布局包复制到 `assets/<布局ID转目录名>/`，将运行时包复制到 `assets/<运行时ID转目录名>/`，将组件包复制到 `assets/<组件包ID转目录名>/`，并把 `--component-id` 选择的语义 HTML 片段插入模板声明的组件插槽，同时在模板声明的样式、运行时脚本和工具栏插槽中加入相对资源引用。选择 `html.runtime-kit-v1` 时，页面获得 `data-math` 公式渲染、自动/窄屏/平板/桌面显示模式、全屏和浏览器保存 PDF 入口；运行时包不访问 CDN。`report.yml` 初始化任务元数据、模板/布局/运行时/组件选择和待确认授权状态；`materialization.json` 记录任务/修订、基础设施 commit、模板、布局、运行时、组件版本以及复制文件的 SHA-256。项目事实、来源清单和最终授权状态仍由 Agent 按工作流填充；工具只交付结构起点。

默认只预览，不写文件。应用时必须提供最近一次预览的计划摘要和任务记录版本。工具预检全部目标、拒绝覆盖不同内容、拒绝符号链接及越界路径；重复应用相同计划是幂等的，内容发生变化则停止，不覆盖用户修改。

工具只使用 Python 标准库。Manifest YAML 由仓库 Ruby CI 校验器做完整解析与 Schema 校验；本工具只读取本仓 schema v2 中固定格式的能力标量字段，遇到不支持的结构会失败关闭。
