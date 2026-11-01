# 语义组件

每个组件目录都包含：

- `component.yml`：机器可读契约；
- `template.html`：最小可复制结构；
- 组件包的 `semantic.css`：共享展示实现。

Agent 应先读取组件包根目录的 `package.yml` 和 `index.yml`，再按组件 ID 读取这里的 `component.yml` 与 `template.html`。不要扫描 CSS 类名猜测组件用途，也不要把未在 `index.yml` 登记的目录当作能力。
