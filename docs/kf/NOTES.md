# KF 工序 01（asset-registration）工作笔记（append-only）

面向后续 wp-XX-01 工人。每条 ≤120 字，来源均为本仓实做包。

1. **源哈希先证后做**（wp-8288-01）：拉 `markdown` 后立刻比 sha256 与字符数，不符即 `SystemExit`；
   否则下游全部工件建立在漂移源上，平台重算哈希时整包作废。
2. **quote 只许切片**：`quote = md[start:end]`，不唯一就向上扩行到唯一；行号由字符偏移反算，
   这样 `start_line`/`char_span`/`quote` 三者自洽，平台子串校验必过。
3. **报告 json 块的反引号坑**（wp-8288-01 实测）：manifest 若逐字登记了代码围栏引文，块内会出现三反引号，
   用 `re.search(r"```json\n(.*?)\n```", md, re.S)` 这类懒匹配会提前截断 ⇒ JSON 解析失败。
   出报告时把信封里的反引号写成 U+0060 转义（JSON 等价），并在正文注明。
4. **schemas/asset_manifest.v1.schema.json 被别的包 pin 住**（const 写死 package_id/report_id）：
   不要改共享 schema；另存 `<包>/asset_manifest.schema.json` 只重定向 const，字段与枚举一律不动。
5. **跨仓路径一律 unresolved**：`src/tensordem/*` 这类属别的仓，登记「引用存在、内容未取」+ 原因，
   不要在本仓造同名文件，也不要猜内容填进 manifest。
6. **claims 可以空**：01 工序无抽取职责，空数组 + `claims_empty_reason` 是完整结果；
   造 claim 反而违反 `no_forced_claim_generation`。