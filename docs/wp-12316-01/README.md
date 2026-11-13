# wp-12316-01 · 资产登记：report 12316

工作包 `wp-12316-01`（task_type `01-asset-registration`，lane C）。**只登记，不抽取**；claims 为空数组是
契约允许的完整结果（`objective.register_assets: true` / `classify_report_type: false`）。

源：`tensor://reports/12316`，字段 `markdown`，
`sha256 = a38be5c7ec3bc9250f3d1a53fb75491d66489da695b121134a761e93bdba7f87`（9610 chars / 14664 bytes，
与工作包契约 `input.source_hash` / `chars` 逐字节相等）。

## 产物

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 交付物：48 条资产（23 落在源 markdown 内 / 24 指向报告外工件 / 1 条报告显式声明的不存在），每条带字符区间+行区间+逐字引文，以及外部工件的 bytes/sha256 |
| `asset_manifest.v1.schema.json` | 从 `schemas/asset_manifest.v1.schema.json` 打补丁 pin 到本包/本报告的副本（`schema_pass` 因此可机器复算） |
| `verification.json` | 独立验证器输出：6 项 acceptance + 9 条检查（含**重新联网取一次原文**后重算哈希/重切片） |
| `fig1_registration_map.png` | 图 1：资产分类×解析状态 + 外部引用解析到哪个工作树根 + 完整性摘要 |
| `report.md` | 发布到平台的报告正文（唯一一个 json 代码块 = 结果信封） |

`artifacts/wp-12316-01/`（本地生成）与上面的 `asset_manifest.json` / schema / 图逐字节相同——推送门排除
`artifacts/**`，所以耐久副本放在这里。

## 一键复跑

```bash
python3 scripts/kf_register_12316.py    # 取原文 + 钉哈希 + 锚点切片 + 只读探测外部地址
python3 scripts/kf_verify_12316.py      # 独立再取一次原文，重切片全部引文，schema 校验，6 项 acceptance
python3 scripts/kf_publish_12316.py     # 生成图与本报告（数字全部程序化注入，零手抄）
python3 -m pytest tests/test_kf_wp_12316_manifest.py -q    # 8 passed（离线不变量；无缓存原文时 skip 而非假绿）
```

需要 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`（取原文用）。

## 登记的边界

- 只碰 report_id=12316；未读写其它 report。
- 外部工件只做**只读**存在性/sha256 探测（工作树根从报告自己的表格解析），不复制、不改写、不猜地址。
- 不标 verified：`integrity.verification_status = "not_verified"`，verification 由平台门计算。
- 报告里的数字（1.0 检出率、41.396 s、1371 条声明……）一律只登记不换算。