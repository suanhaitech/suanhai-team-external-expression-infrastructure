# 本地来源素材登记与核验

`html.source-assets` 使用 Python 标准库，登记消费端已经取得的原图、图表、原文和衍生素材。**不下载 URL，不推定内容授权，不修改原始文件。**

准备规格 JSON，例如：

```json
{"assets":[
  {"id":"original-diagram","path":"assets/original.svg","role":"original","source":"负责人提供的原始结构图","usage_rights":"负责人确认可在本次材料使用"},
  {"id":"annotated-diagram","path":"assets/annotated.svg","role":"derived","source":"原图添加讲解标记","derived_from":"original-diagram","transformation":"添加编号；完整原图另行保留"}
]}
```

来源也可登记 `source_url`（无凭据 HTTP(S) 地址，只保存不访问）、`caption`、`usage_rights`。原始素材的 `transformation` 固定 `none`；衍生素材必须声明操作并引用登记中的素材。衍生链不能循环。

```powershell
python infrastructure/html/tools/source-assets/source_assets.py register --root '<产物目录>' --input '<规格.json>'
python infrastructure/html/tools/source-assets/source_assets.py register --root '<产物目录>' --input '<规格.json>' --apply --expect-plan-sha256 '<预览摘要>'
python infrastructure/html/tools/source-assets/source_assets.py validate --root '<产物目录>' --input '<产物目录>/source-assets.json'
```

默认仅预览；应用绑定同一预览摘要，独占创建登记文件、拒绝覆盖。核验检查安全相对路径、符号链接越界、ID/路径唯一、衍生关系、字节数、SHA-256、类型及尺寸，修改素材会使旧登记失败。JSON Schema 见 `../../schemas/source-assets.schema.json`，不能代替工具的跨字段与文件检查。

当前尺寸读取支持 PNG/GIF/JPEG/SVG；其他格式登记尺寸为 null，不宣称图像已解码或可读。来源与权利字段由负责人提供，工具无法验证授权真伪。登记记录只含产物内相对路径，不写本机临时目录或凭据。
