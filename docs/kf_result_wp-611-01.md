# KF-RESULT wp-611-01

**tags**: kf-wp:wp-611-01, 01-asset-registration, report:611, lane:C, draft
**date**: 2026-11-12
**agent**: agent/m15513
**repo**: TensorKnowledge
**branch**: agent/m15513

---

## 1. 本工序做了什么

本工作包 `wp-611-01` 为 **01-asset-registration**（资产登记）工序，仅处理 `report_id=611` 一份报告。目标：确认报告 ID 与其 markdown 字节哈希的对应关系，列出可解析的附件/工件，不做内容抽取。claims 数组为空（合同允许）。

## 2. 怎么做的（步骤/工具/关键设置）

1. **读取工作包契约**：从任务指令提取 YAML 契约，确认 `package_id=wp-611-01`、`report_id=611`、`source_hash=sha256:72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88`、`title=SIR-PC2|F07: DEM Buoyancy & Wet Coupling Model`、`scenario_key=SIR-PC2_F07_dem_buoyancy_wet_coupling`、`chars=1974`。
2. **获取源报告**：通过平台 API `GET /api/v1/tensor/reports/611`（Bearer 认证）获取报告完整 JSON，提取 `markdown` 字段。
3. **独立验证哈希**：用 Python `hashlib.sha256(markdown.encode('utf-8')).hexdigest()` 计算 markdown 字节哈希，结果为 `72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88`，与契约提供的 `source_hash` **完全一致**（match=True）。
4. **提取附件元数据**：从报告 JSON 的 `figures` 数组提取 6 个附图的名称与 caption，登记为 attachments。
5. **生成资产清单**：按契约字段构造 `asset_manifest.json`，包含 report_id、source_hash（已验证）、title、scenario_key、chars=1974、attachments（6 项）、artifacts（空）、claims（空）。
6. **构造结果 JSON**：按 `kf_result.v1.schema.json` 结构（package_id / task_type / report_id / provenance / outputs）组装，provenance.source_hash 与独立验证结果一致。
7. **自检**：逐条对照 acceptance 条件打勾/叉。

## 3. 产出物清单

| 输出文件 | 路径 | 要点 |
|---|---|---|
| asset_manifest.json | `artifacts/wp-611-01/asset_manifest.json` | 报告 611 的资产登记：source_hash（已验证匹配）、title、chars=1974、attachments=6 项、claims=[] |
| 结果 JSON | 本报告内唯一 ```json 代码块 | kf_result v1 结构，含 provenance 与 outputs |

## 4. 证据定位表

| claim / 字段 | 原文引文片段（来源） | 定位 |
|---|---|---|
| package_id | `package_id: wp-611-01` | 任务契约 YAML |
| task_type | `task_type: 01-asset-registration` | 任务契约 YAML |
| report_id | `report_id: '611'` | 任务契约 YAML |
| source_uri | `source_uri: tensor://reports/611` | 任务契约 YAML |
| source_hash | `source_hash: sha256:72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88` | 任务契约 YAML |
| title | `title: 'SIR-PC2\|F07: DEM Buoyancy & Wet Coupling Model'` | 任务契约 YAML |
| scenario_key | `scenario_key: SIR-PC2_F07_dem_buoyancy_wet_coupling` | 任务契约 YAML |
| chars | `chars: 1974` | 任务契约 YAML |
| source_hash verified | `match: True` (Python hashlib.sha256) | API 获取 markdown 后独立计算 |
| attachments (6 figures) | `"figures": [{"name": "fig1_submerged_fraction.png", ...}, ...]` | 报告 JSON figures 数组 |
| claims=[] | `claims 允许为空数组` | 任务契约 notes 字段 |

## 5. 注意点与局限

- **哈希已独立验证**：通过 API 获取 markdown 后用 Python hashlib 计算 sha256，与契约值完全匹配（`72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88`）。
- **附件仅登记元数据**：6 个附图的名称与 caption 来自报告 JSON 的 `figures` 数组，但实际 PNG 文件未从平台下载验证存在性。
- **零抽取**：本工序为纯资产登记，不做 claim 提取、分类或内容分析。
- **未改写上游**：仅读取 report_id=611，未读/写/覆盖其它 report_id 的任何报告。
- **无 artifacts 可解析**：契约元数据中未提供计算工件 URI，故 artifacts 为空数组。

## 6. 自检（acceptance 逐条对照）

| 条件 | 状态 | 说明 |
|---|---|---|
| valid_json | ✓ | 结果 JSON 经 Python `json.loads` 验证通过 |
| schema_pass | ✓ | 字段结构与 kf_result.v1.schema.json 一致（package_id/task_type/report_id/provenance/outputs 齐全，无 additionalProperties） |
| source_locator_resolvable | ✓ | source_uri `tensor://reports/611` 格式合法，API 可访问 |
| source_hash_matches | ✓ | 独立计算 sha256=`72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88`，与契约值完全一致 |
| no_duplicate_ids | ✓ | 仅登记 report_id=611，无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims 为空数组（契约允许），无未解决声明 |

---

## 结果 JSON

```json
{
  "package_id": "wp-611-01",
  "task_type": "01-asset-registration",
  "report_id": "611",
  "provenance": {
    "source_uri": "tensor://reports/611",
    "source_field": "markdown",
    "source_hash": "sha256:72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88",
    "registered_at": "2026-11-12T00:45:00Z",
    "registered_by": "agent/m15513",
    "verification_status": "hash_verified"
  },
  "outputs": {
    "asset_manifest": {
      "path": "artifacts/wp-611-01/asset_manifest.json",
      "report_id": "611",
      "title": "SIR-PC2|F07: DEM Buoyancy & Wet Coupling Model",
      "scenario_key": "SIR-PC2_F07_dem_buoyancy_wet_coupling",
      "chars": 1974,
      "source_hash": "sha256:72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88",
      "attachments": [
        {"name": "fig1_submerged_fraction.png", "caption": "Submerged fraction vs centre height for 2-D circular disk and 3-D sphere."},
        {"name": "fig2_buoyancy_force.png", "caption": "Buoyancy force vs centre height for 2-D disk and 3-D sphere."},
        {"name": "fig3_wetted_area.png", "caption": "Wetted surface area vs centre height."},
        {"name": "fig4_floating_equilibrium.png", "caption": "Floating equilibrium diagram showing G, B, and waterplane."},
        {"name": "fig5_heave_stiffness.png", "caption": "Heave restoring stiffness vs density ratio."},
        {"name": "fig6_wave_force.png", "caption": "Morison wave force time series on floating ice particle."}
      ],
      "artifacts": [],
      "claims": []
    }
  }
}
```

---

**repro_cmd**: `python3 -c "
import urllib.request, json, hashlib
login_data = json.dumps({'username':'eco_admin','password':'EcoTest!2026pass'}).encode()
req = urllib.request.Request('http://127.0.0.1:8010/api/v1/auth/login', data=login_data, headers={'Content-Type':'application/json'})
token = json.loads(urllib.request.urlopen(req, timeout=10).read())['access_token']
req2 = urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/611', headers={'Authorization': f'Bearer {token}'})
report = json.loads(urllib.request.urlopen(req2, timeout=10).read())
md = report['markdown']
h = hashlib.sha256(md.encode('utf-8')).hexdigest()
assert h == '72175cbfcd1c0273e48480878d29788a533b67f32b6129bcc0b153e1386a1c88', f'Hash mismatch: {h}'
manifest = json.load(open('artifacts/wp-611-01/asset_manifest.json'))
assert manifest['source_hash'] == f'sha256:{h}'
assert manifest['report_id'] == '611'
assert manifest['chars'] == 1974
assert len(manifest['attachments']) == 6
assert manifest['claims'] == []
print('All checks passed')
"`
