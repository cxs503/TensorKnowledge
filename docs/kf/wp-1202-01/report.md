# KF-RESULT wp-1202-01

## ① 本工序做了什么

对 `report_id=1202`（标题：EX1-P2 prereg v1: KVLCC2 满载阻力盲预测（Holtrop-1984 主链，md5 冻结））执行 **01-asset-registration** 工序：确认源报告 markdown 的字节哈希与契约声明一致，列出报告中可解析的附件/工件元数据，不做知识抽取（claims 为空数组）。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取源报告**：通过 `GET /api/v1/tensor/reports/1202`（Bearer token 认证）获取完整报告 JSON，提取 `markdown` 字段。
2. **独立重算哈希**：对 markdown 字符串做 UTF-8 编码后计算 SHA-256，结果 `sha256:8af11b1cd48728e4d579eb6dccea1a7f7111a41baaf2fd68a045064cafaad1c1`，与契约声明的 `source_hash` 逐字节一致。
3. **字符数校验**：markdown 长度 3914 字符（UTF-8 编码 6053 字节），与契约 `chars: 3914` 一致。
4. **资产识别**：扫描报告正文，识别出 9 项资产——1 项源文本（已注册）、3 项结果图（元数据已声明）、5 项代码/数据文件（路径与 md5 在正文中声明）。
5. **生成 asset_manifest.json**：按 `kf_result.v1.schema.json` 结构组织，每个资产赋予唯一 `asset_id`，标注 `status`（registered / declared_metadata_only / declared_only）与 `locator`（原文行号与引文片段）。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-1202-01/kf_result.json` | KF-RESULT 信封，含 asset_manifest.json（9 项资产登记） |

资产登记汇总：
- **registered**（1 项）：源文本 markdown（含完整 SHA-256 哈希）
- **declared_metadata_only**（3 项）：fig1_rt_components_vs_fn.png、fig2_ct_and_wave_share.png、fig3_rt_loglog.png（有名称与 caption，无 PNG 字节）
- **declared_only**（5 项）：holtrop1984.py、ex1_kvlcc2_predict.py、predictions.csv、inputs.json、EX1_KVLCC2_prereg_v1.md（有路径与 md5 声明，文件本体不在报告内）

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 行号 |
|---|---|---|
| source_hash | `sha256:8af11b1cd48728e4d579eb6dccea1a7f7111a41baaf2fd68a045064cafaad1c1` | 契约声明 |
| holtrop1984.py | `backend/api/holtrop1984.py`：逐项转录 Holtrop (1984) 原文 | L10 |
| ex1_kvlcc2_predict.py | `tools/prereg/ex1_kvlcc2_predict.py`：Fn 0.10–0.20 步长 0.02 | L11 |
| predictions.csv md5 | `b070cddeab0f93a448f886bf0ea75420` | L12 |
| inputs.json md5 | `7a774bc3174c7c8bbe62213dfb76de65` | L12 |
| 图1 | 总阻力与分量 vs Fn | L32 |
| 图2 | Ct 与波阻占比 vs Fn | L33 |
| 图3 | Rt–Fn 双对数 | L34 |

## ⑤ 注意点与局限

- **本工序不做知识抽取**：claims 数组为空，符合 01-asset-registration 契约（"claims 允许为空数组"）。
- **图文件无 PNG 字节**：3 张结果图仅有名称与 caption 元数据，PNG 本体未随报告传输，status 标记为 `declared_metadata_only`。
- **代码/数据文件未下载**：5 项代码/数据资产仅有路径与 md5 声明，文件本体在 ship-performance-platform 仓库中，本工序不跨仓拉取，status 标记为 `declared_only`。
- **零手抄**：所有数字/引文均从报告 markdown 原文逐字定位，未凭记忆重述。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结果 |
|---|---|
| valid_json | ✅ kf_result.json 通过 json.load() 解析 |
| schema_pass | ✅ 所有必填字段（package_id/task_type/report_id/provenance/outputs）存在且类型正确 |
| source_locator_resolvable | ✅ source_uri=tensor://reports/1202 可通过 API GET 解析 |
| source_hash_matches | ✅ 独立重算 SHA-256 与契约声明一致 |
| no_duplicate_ids | ✅ 9 个 asset_id 全部唯一 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ claims 为空数组（合法完整结果） |

**repro_cmd**: `python3 -c "import urllib.request,json,hashlib; token=json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8010/api/v1/auth/login',json.dumps({'username':'eco_admin','password':'EcoTest!2026pass'}).encode(),headers={'Content-Type':'application/json'})).read())['access_token']; md=json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/1202',headers={'Authorization':f'Bearer {token}'})).read())['markdown']; print('sha256:'+hashlib.sha256(md.encode()).hexdigest())"`
