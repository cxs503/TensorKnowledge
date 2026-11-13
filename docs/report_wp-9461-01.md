# KF-RESULT wp-9461-01

tags: kf-wp:wp-9461-01, lane:B, 01-asset-registration, green-navigation.eeoi_cii

## ① 本工序做了什么

工作包 `wp-9461-01`（工序 01-asset-registration）对 `report_id=9461` 执行源资产登记：
- 从平台 API 获取报告 markdown 全文（10571 字符）
- 计算并验证字节 SHA-256 哈希，与契约值 `sha256:c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1` 一致
- 扫描报告正文，提取所有可解析的附件/工件引用路径（共 10 项）
- 生成 `asset_manifest.json` 作为登记产物
- **不做知识抽取**：claims 数组为空，符合工序 01 契约

## ② 怎么做的（步骤/工具/关键设置）

1. **登录平台**：`POST /api/v1/auth/login` 以 `eco_admin` 获取 Bearer token
2. **获取报告**：`GET /api/v1/tensor/reports/9461`，取 `markdown` 字段
3. **哈希校验**：`hashlib.sha256(md.encode('utf-8')).hexdigest()` → 与契约 `c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1` 逐位比对，匹配
4. **工件扫描**：正则/文本扫描 markdown 中的路径引用（`artifacts/`、`tests/`、`backend/` 前缀），去重后按类型分类
5. **Schema 校验**：用 `jsonschema.validate()` 对 `kf_result.v1.schema.json` 校验输出信封，PASS
6. **产物写入**：`artifacts/asset_manifest.json` + `artifacts/kf_result_wp-9461-01.json`

关键设置：零手抄——所有路径/描述逐字来自报告原文 markdown。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `artifacts/asset_manifest.json` | 源资产登记清单：report_id、source_hash（已验证）、10 项工件引用（probe 脚本×1、results JSON×1、PNG 图×4、测试套件×1、模块×3）、claims=[] |
| `artifacts/kf_result_wp-9461-01.json` | kf_result v1 信封：package_id/wp-9461-01、task_type/01-asset-registration、report_id/9461、provenance（source_hash 匹配）、outputs（含 asset_manifest.json） |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 位置 |
|---|---|---|
| source_hash | `sha256:c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1` | 工作包契约 input.source_hash |
| title | `EEOI 与 CII 营运指标闭环验证（节点 p48w3-n09-eeoi-cii · m8189）` | 报告 markdown 第 1 行 |
| chars | `10571` | 工作包契约 input.chars；API 返回 markdown 长度 |
| probe_eeoi_cii_m8189.py | `artifacts/eeoi_cii_m8189/probe_eeoi_cii_m8189.py`（工件哈希 `d0d1b41a506f4635…`） | 报告 § 头部 |
| test_eeoi_cii_m8189.py | `tests/test_eeoi_cii_m8189.py`（24 项，全绿） | 报告 § 头部 |
| eeoi_cii.py | `backend/modules/green_navigation/eeoi_cii.py` | 报告 § 头部 |
| fig1–fig4 | `artifacts/eeoi_cii_m8189/fig{1,2,3,4}_*.png` | 报告 §3.6 |
| results.json | `artifacts/eeoi_cii_m8189/results.json` | 报告 §2.2 |
| cii_required_value | `backend/services/cii_required_value.required_cii` | 报告 §2.1 步骤(f) |
| green_shipping.py | `backend/api/green_shipping.py` 的 `_gn_cii_rating_status()` | 报告 §5.3 第 5 条 |

## ⑤ 注意点与局限

- **工序 01 不做抽取**：claims 为空数组是契约允许的完整结果，不代表报告无知识可抽（后续工序 03 可接手）
- **工件哈希不完整**：报告中 probe 脚本哈希仅给前缀 `d0d1b41a506f4635…`，无法做完整校验——登记时保留原文截断形式
- **未验证工件存在性**：仅登记报告中引用的路径，未检查这些文件在仓内是否实际存在（属后续工序职责）
- **零手抄纪律**：所有路径/描述逐字来自 markdown，未做任何推断或补全

## ⑥ 自检（acceptance 逐条对照）

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✓ | `json.loads()` 无异常 |
| schema_pass | ✓ | `jsonschema.validate()` 通过 kf_result.v1 |
| source_locator_resolvable | ✓ | report_id=9461 可从 API 获取，markdown 字段存在 |
| source_hash_matches | ✓ | 计算哈希 `c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1` 与契约一致 |
| no_duplicate_ids | ✓ | artifacts 数组 10 项路径互异 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims=[]（空数组，无需证据） |

**结论：全部 acceptance 项通过，无 honest-FAIL。**

## 复跑命令

```bash
# 一键复跑：登录→取报告→验哈希→生成产物→校验 schema
python3 -c "
import urllib.request, json, hashlib, jsonschema
token = json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8010/api/v1/auth/login', data=json.dumps({'username':'eco_admin','password':'EcoTest!2026pass'}).encode(), headers={'Content-Type':'application/json'})).read())['access_token']
md = json.loads(urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/9461', headers={'Authorization': f'Bearer {token}'})).read())['markdown']
h = hashlib.sha256(md.encode('utf-8')).hexdigest()
assert h == 'c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1', f'Hash mismatch: {h}'
with open('schemas/kf_result.v1.schema.json') as f: schema = json.load(f)
with open('artifacts/kf_result_wp-9461-01.json') as f: result = json.load(f)
jsonschema.validate(result, schema)
print('All checks PASS')
"
```

```json
{
  "package_id": "wp-9461-01",
  "task_type": "01-asset-registration",
  "report_id": "9461",
  "provenance": {
    "source_hash": "sha256:c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1",
    "source_field": "markdown",
    "producer": "agent/m15642",
    "emitted_at": "2026-11-12T01:32:44Z",
    "notes": "工序 01 资产登记：确认 report_id=9461 的 markdown 字节哈希与契约一致，列出报告中可解析的附件/工件引用。claims 为空数组（本工序不做抽取）。"
  },
  "outputs": {
    "asset_manifest.json": {
      "report_id": "9461",
      "source_uri": "tensor://reports/9461",
      "source_field": "markdown",
      "source_hash": "sha256:c839141234f9b547f153399b3e09784457d55832f3449d16c7b5b21a278a92b1",
      "title": "EEOI 与 CII 营运指标闭环验证（节点 p48w3-n09-eeoi-cii · m8189）",
      "scenario_key": "green-navigation.eeoi_cii",
      "chars": 10571,
      "hash_verified": true,
      "artifacts": [
        {"path": "artifacts/eeoi_cii_m8189/probe_eeoi_cii_m8189.py", "type": "probe_script", "hash_prefix": "d0d1b41a506f4635", "description": "金标探针脚本，生成 results.json + 金标 CSV + 4 张图"},
        {"path": "artifacts/eeoi_cii_m8189/results.json", "type": "results_data", "description": "计算结果 JSON（含 annual.by_year、rating_boundaries 等）"},
        {"path": "artifacts/eeoi_cii_m8189/fig1_voyage_closure.png", "type": "figure", "description": "KVLCC2 满载航次的功率时程、累计燃油与累计 CO₂"},
        {"path": "artifacts/eeoi_cii_m8189/fig2_speed_sensitivity.png", "type": "figure", "description": "航速对 EEOI/AER 的影响（k=3.0/3.2/3.5 三档进距律）与 2023 要求值线"},
        {"path": "artifacts/eeoi_cii_m8189/fig3_cii_rating_bands.png", "type": "figure", "description": "2023–2026 年油轮 required CII 与 A–E 分区（d1–d4）"},
        {"path": "artifacts/eeoi_cii_m8189/fig4_integration_convergence.png", "type": "figure", "description": "梯形积分对解析积分的相对误差随采样数收敛"},
        {"path": "tests/test_eeoi_cii_m8189.py", "type": "test_suite", "description": "24 项 pytest 测试，全绿"},
        {"path": "backend/modules/green_navigation/eeoi_cii.py", "type": "module", "description": "被测模块：EEOI/CII 计算纯函数实现"},
        {"path": "backend/services/cii_required_value.py", "type": "module", "description": "被调用服务：required_cii 参考线与 Z 因子计算"},
        {"path": "backend/api/green_shipping.py", "type": "module", "description": "API 层：_gn_cii_rating_status() 返回 NOT_SUPPORTED"}
      ],
      "claims": [],
      "notes": "工序 01 仅做资产登记，不做知识抽取。claims 为空数组符合契约。"
    }
  },
  "claims": []
}
```
