# 资产字节保护

`consumer.asset-bytes` 为消费端预览或增补带标记的 `.gitattributes`，避免 Windows 换行转换改变已登记来源和作品的 SHA-256。它不执行 Git 暂存、归一化、提交或推送，不回写已登记文件。

```text
python protect_asset_bytes.py --root .
python protect_asset_bytes.py --root . --apply --expect-plan-sha256 <预览摘要>
```

默认保护 reports、courses、series、books、tasks。自定义输出目录时用重复的 `--output-root` 给出完整目录列表，并包含需要保护的任务记录目录。工具保留现有规则原文；标记内有不同内容时拒绝覆盖。应用后针对实际文件运行 `git check-attr text -- <文件>`，遇到嵌套规则或仓库级配置冲突由维护者明确合并。规则只影响今后的 Git 转换；历史摘要不因规则存在自动恢复。
