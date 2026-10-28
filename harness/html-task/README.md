# HTML 任务 Harness

状态：`planned / not implemented`

计划职责：约束 HTML 任务的输入、允许读取的来源、工作目录、检查点、停止条件和输出路径。

当前没有执行器，也没有加入根目录 `manifest.yml`。

在执行器实现前，消费端必须先接入[Bootstrap 协议](../../docs/consumer-repository-bootstrap.md)，再使用[消费端对外表达 Harness v0.1](../../docs/consumer-repository-harness-v0.1.md)中的文档协议和[冒烟测试](../../docs/consumer-repository-smoke-test.md)验证任务路线。文档协议不能被当作本目录的可调用执行器。
