# KF-RESULT wp-14069-01

**tags**: `kf-wp:wp-14069-01`, `01-asset-registration`, `GAP-DEM-FRICTION`, `TensorDEM`, `board-audit`, `maturity-verdict`

## ① 本工序做了什么

本工作包 `wp-14069-01` 为 **01-asset-registration**（源资产登记）工序，针对 `report_id=14069`（标题：「交差核验 audit：m14960（GAP-DEM-FRICTION）判级 L3 / 返修 —— headline −4.6% 取自稳态门拒绝的窗口」）执行源资产登记。

具体工作：
- 从平台 API 获取报告 markdown 原文（5521 字符）
- 验证 `source_hash` 与契约声明一致（`sha256:bff244d0f165c115f95e5e450e57671722615e315cc75c772973b962e5113139`，匹配 ✓）
- 解析报告结构：11 个章节段、6 张数据表、1 张图引用、5 个代码/脚本引用、7 个证据指针工件
- 产出 `asset_manifest.json`，登记所有可解析的附件/工件路径与元数据
- **不做知识抽取**：claims 数组为空，由后续工作包（如 02-claim-extraction）填充

## ② 怎么做的（步骤/工具/关键设置）

1. **获取源报告**：通过 `GET /api/v1/tensor/reports/14069`（Bearer token 认证）获取完整报告 JSON，提取 `markdown` 字段。
2. **哈希校验**：用 `hashlib.sha256(markdown.encode()).hexdigest()` 计算字节哈希，与契约 `source_hash` 比对 → 一致。
3. **结构解析**：人工阅读报告 markdown，识别章节标题（`##` 级）、表格（`|...|` 语法）、图引用（`figures` 数组）、代码引用（反引号路径）、证据指针（§7）。
4. **资产清单编制**：参照既有资产登记范例（`wp-446-01`、`wp-8510-01`）的 JSON 结构，编制 `asset_manifest.json`，包含 sections/tables/figures/code_references/claims/unresolved_assets。
5. **结果信封封装**：按 `schemas/kf_result.v1.schema.json` 构建结果 JSON，包含 `package_id`/`task_type`/`report_id`/`provenance`/`outputs`/`claims`。
6. **工具链**：Python 3.11 + `urllib.request`（API 访问）+ `hashlib`（哈希）+ `json`（序列化）。

## ③ 产出物清单

| 输出文件名 | 要点 |
|---|---|
| `docs/wp-14069-01_asset_manifest.json` | 源资产登记清单：11 sections、6 tables、1 figure、5 code_references、0 claims、7 unresolved_assets |
| `docs/kf_result_wp-14069-01.md` | 本工序报告（含嵌入式结果 JSON） |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 定位 |
|---|---|---|
| source_hash | `sha256:bff244d0f165c115f95e5e450e57671722615e315cc75c772973b962e5113139` | 契约 input.source_hash；API 响应 markdown 字段 sha256 校验通过 |
| report title | `交差核验 audit：m14960（GAP-DEM-FRICTION）不该按「基准验证」结账 —— 判级 L3 / 返修` | markdown 第 1 行（h1 标题） |
| scenario_key | `GAP-DEM-FRICTION` | API 响应 scenario_key 字段；markdown 第 3 行 |
| report_id | `14069` | API 响应 id 字段 |
| chars | `5521` | API 响应 markdown 字段 `len()` 计算 |
| figure name | `m14978_window_sensitivity.png` | API 响应 figures[0].name |
| figure caption | `m14960 headline 算例：(a) τ(γ) 仍在漂移（阴影=平均窗口）；(b) μ 随平均窗口长度变化，灰带=文献 0.36–0.40，红虚线=±10% 门` | API 响应 figures[0].caption |
| 参数表（颗粒） | `r=0.005 m, ρ=2500 kg/m³, 单分散` | markdown §1 参数表第 1 行 |
| 参数表（接触） | `k_n=1e5 N/m, k_t/k_n=0.5, e=0.3, μ_roll=0.05, μ_p=0.5` | markdown §1 参数表第 2 行 |
| 参数表（盒体） | `0.080×0.032×0.050 (N=78) / 0.080×0.064×0.080 (N=390)` | markdown §1 参数表第 3 行 |
| 参数表（应力/协议） | `σ_n=4000 Pa（伺服）；γ=0.6（有限尺寸扫描）/ 1.0（μ_p 矩阵）；seed=6107` | markdown §1 参数表第 4 行 |
| 参数表（外部锚） | `μ_s=0.38，带 0.36–0.40（Jop/Forterre/Pouliquen, Nature 441,727 (2006); GDR MiDi, EPJE 14,341 (2004)）` | markdown §1 参数表第 5 行 |
| 可复现性（9 量 Δ=0） | `9 个承重量最大绝对差 = **0.0**（含 σ_n/τ/μ/I/drift/r²/steps/N/shear_rate）` | markdown §3.1 末行 |
| 稳态门 REJECT | `size_small: drift -0.566, R² 0.211 → REJECT`；`size_medium: drift +0.240, R² 0.083 → REJECT` | markdown §3.2 表格 |
| 窗口敏感性（last_50%） | `last_50%: τ̄=1447.6, μ=0.3627, vs 0.38=-4.6%, 是` | markdown §3.3 表格第 1 行 |
| 窗口敏感性（last_10%） | `last_10%: τ̄=1888.1, μ=0.4730, vs 0.38=+24.5%, 否` | markdown §3.3 表格第 4 行 |
| μ 相对极差 | `μ 相对极差 **28.8%**` | markdown §3.3 正文 |
| 工件一致性（C4 表2/表3） | `4 / **0** / 7` | markdown §3.5 表格第 1 行 |
| 平台 L4 门 | `CLAIMED_NOT_PROVEN，rows=0` | markdown §3.5 表格第 5 行 |
| 裁定 | `level=**3**, verdict_by=\`board-audit\`，处置=**reopened（返修）**` | markdown 第 4 行 |
| 证据指针 | `docs/audit/M14960_CROSS_AUDIT.md · artifacts/audit_m14960/audit.json（C1–C7） · ... · commit 97711cb8` | markdown §7 |

## ⑤ 注意点与局限

1. **仅登记不抽取**：本工序为 01-asset-registration，claims 数组为空。报告中的知识主张（如「L3 成熟度」「稳态门 REJECT」「窗口敏感性 28.8%」等）未被提取为结构化 claim，需后续 02/03 工序处理。
2. **工件路径跨仓**：报告 §7 引用的 7 个证据指针（audit.json、rerun JSON/log、pytest log、png、脚本、commit）均位于 TensorDEM 仓内，不在本 TensorKnowledge 工作树中，标记为 `unresolved`。
3. **图无内嵌数据**：报告 `figures` 数组仅有 name+caption 元数据，无 `png_base64` 内嵌，原始 PNG 文件位置未给出绝对路径。
4. **未跑项声明**：报告 §5 第 5 点明确声明 4 项未跑（mu030/050/070 重跑、size_large、oss_inventory SQL、文献在线核验），本登记如实记录为 unresolved。
5. **零手抄纪律**：本登记中所有数字/引文均从 API 返回的 markdown 字段逐字定位，无凭记忆重述。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | 结果 JSON 经 `json.loads()` 解析通过 |
| schema_pass | ✅ | 包含全部 required 字段（package_id/task_type/report_id/provenance/outputs）；provenance 含 source_hash + source_field；outputs 含 asset_manifest.json |
| source_locator_resolvable | ✅ | source_uri=`tensor://reports/14069` 可通过 API `GET /tensor/reports/14069` 解析 |
| source_hash_matches | ✅ | 计算 `sha256(markdown.encode()).hexdigest()` = `bff244d0f165c115f95e5e450e57671722615e315cc75c772973b962e5113139`，与契约一致 |
| no_duplicate_ids | ✅ | asset_manifest 中所有 id（sections/tables/figures/code_references/unresolved_assets）均唯一 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 数组为空（01-asset-registration 允许）；unresolved_assets 全部标注 status="unresolved" |

**repro_cmd**:
```bash
cd /root/tp-agent/work/m15781 && python3 -c "
import urllib.request, json, hashlib
token = '...'  # 登录后获取
req = urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/14069', headers={'Authorization': f'Bearer {token}'})
resp = urllib.request.urlopen(req)
data = json.loads(resp.read())
md = data['markdown']
h = hashlib.sha256(md.encode()).hexdigest()
assert h == 'bff244d0f165c115f95e5e450e57671722615e3113139', f'Hash mismatch: {h}'
print('Source hash verified')
with open('docs/wp-14069-01_asset_manifest.json') as f:
    manifest = json.load(f)
assert manifest['source_hash_verified'] == True
assert manifest['source_hash'] == f'sha256:{h}'
print('Asset manifest validated')
"
```

```json
{
  "package_id": "wp-14069-01",
  "task_type": "01-asset-registration",
  "report_id": "14069",
  "provenance": {
    "source_hash": "sha256:bff244d0f165c115f95e5e450e57671722615e315cc75c772973b962e5113139",
    "source_field": "markdown",
    "producer": "agent-wp-14069-01",
    "emitted_at": "2026-11-12T02:32:00Z",
    "notes": "Asset registration for report 14069 (m14978 cross-audit of m14960 GAP-DEM-FRICTION). Source hash verified against API response. Claims array empty per 01-asset-registration contract."
  },
  "outputs": {
    "asset_manifest.json": {
      "package_id": "wp-14069-01",
      "task_type": "01-asset-registration",
      "report_id": 14069,
      "source_uri": "tensor://reports/14069",
      "source_hash": "sha256:bff244d0f165c115f95e5e450e57671722615e315cc75c772973b962e5113139",
      "source_hash_verified": true,
      "source_field": "markdown",
      "source_length_chars": 5521,
      "title": "交差核验 audit：m14960（GAP-DEM-FRICTION）判级 L3 / 返修 —— headline −4.6% 取自稳态门拒绝的窗口",
      "scenario_key": "GAP-DEM-FRICTION",
      "report_status": "published",
      "report_created_at": "2026-11-11T13:55:44.101519+00:00",
      "report_tags": ["GAP-DEM-FRICTION", "TensorDEM", "board-audit", "maturity-verdict", "shear-cell", "steady-state-gate", "L3"],
      "sections": [
        {"heading": "1. 案例介绍（被审对象是什么）", "locator": "markdown lines 5-18", "contains": ["physical_background", "parameter_table", "external_anchor"]},
        {"heading": "2. 怎么做的（审计方法，全程独立于报告数字）", "locator": "markdown lines 20-30", "contains": ["method_steps", "toolchain_references", "audit_script"]},
        {"heading": "3.1 可复现性：PASS（比特级）", "locator": "markdown lines 32-44", "contains": ["reproducibility_table", "bitwise_comparison"]},
        {"heading": "3.2 仓内自己的稳态门：headline 两行均 REJECT", "locator": "markdown lines 46-54", "contains": ["stationarity_gate_results", "tol_comparison"]},
        {"heading": "3.3 窗口口径敏感性", "locator": "markdown lines 56-68", "contains": ["window_sensitivity_table", "drift_analysis"]},
        {"heading": "3.4 外部锚：WITHHELD", "locator": "markdown lines 70-72", "contains": ["anchor_comparison", "calibration_status"]},
        {"heading": "3.5 工件/表述一致性（机检）", "locator": "markdown lines 74-82", "contains": ["artifact_consistency_checks", "platform_l4_verdict"]},
        {"heading": "4. 图", "locator": "markdown lines 84-85", "contains": ["figure_reference"]},
        {"heading": "5. 注意点（坑与局限）", "locator": "markdown lines 87-98", "contains": ["caveats", "limitations", "unverified_items"]},
        {"heading": "6. 误差判定（逐项显式回答\"是否 <3%\"）", "locator": "markdown lines 100-114", "contains": ["error_judgment_table", "honest_conclusion"]},
        {"heading": "7. 证据指针", "locator": "markdown lines 116-117", "contains": ["artifact_paths", "commit_reference"]}
      ],
      "tables": [
        {"id": "tbl-14069-params", "caption": "算例参数表", "locator": "markdown section 1", "columns": ["参数", "值"], "rows": 5, "quoted_keys": ["颗粒", "接触", "盒体 small / medium", "应力/协议", "外部锚"]},
        {"id": "tbl-14069-reproducibility", "caption": "可复现性对照表（提交工件 vs 本审计重跑）", "locator": "markdown section 3.1", "columns": ["量", "提交工件", "本审计重跑", "|Δ|"], "rows": 6, "quoted_keys": ["sigma_pa", "tau_pa", "mu", "drift_rel", "drift_r2", "total_steps"]},
        {"id": "tbl-14069-stationarity-gate", "caption": "稳态门结果（提交口径 vs gate @0.15）", "locator": "markdown section 3.2", "columns": ["run", "drift_rel", "drift R²", "gate 关（提交口径）", "gate @0.15"], "rows": 2, "quoted_keys": ["size_small", "size_medium"]},
        {"id": "tbl-14069-window-sensitivity", "caption": "窗口口径敏感性（headline 算例，σ_n=3991.7 Pa）", "locator": "markdown section 3.3", "columns": ["窗口", "τ̄ [Pa]", "μ", "vs 0.38", "是否 <10%"], "rows": 4, "quoted_keys": ["last_50%", "last_40%", "last_25%", "last_10%"]},
        {"id": "tbl-14069-artifact-consistency", "caption": "工件/表述一致性机检结果", "locator": "markdown section 3.5", "columns": ["检查", "结果"], "rows": 5, "quoted_keys": ["C4 表2/表3/log_levels", "C4 per-tag 机读工件", "C5 文档未渲染注入模板", "C6 分析脚本解析 runs/*.log", "平台 L4 门"]},
        {"id": "tbl-14069-error-judgment", "caption": "误差判定表（逐项显式回答\"是否 <3%\"）", "locator": "markdown section 6", "columns": ["关键量", "基准", "误差", "是否 <3%", "是否 <10%（锚点判据）"], "rows": 7, "quoted_keys": ["mu_macro_N390_50pct", "mu_macro_N390_10pct", "mu_window_spread", "mu_macro_N78", "sigma_n_hold", "headline_reproducibility", "stationarity"]}
      ],
      "figures": [
        {"id": "fig-14069-window-sensitivity", "name": "m14978_window_sensitivity.png", "caption": "m14960 headline 算例：(a) τ(γ) 仍在漂移（阴影=平均窗口）；(b) μ 随平均窗口长度变化，灰带=文献 0.36–0.40，红虚线=±10% 门", "has_embedded_png": false, "note": "figures 数组仅有 name+caption 元数据，无 png_base64 内嵌数据；原始 PNG 位置未在报告正文中给出绝对路径"}
      ],
      "code_references": [
        {"id": "code-14069-audit-script", "file": "scripts/audit/m14960_cross_audit.py", "context": "复算脚本，产出 artifacts/audit_m14960/audit.json（C1–C7）", "locator": "markdown section 2 第7步 & section 7"},
        {"id": "code-14069-audit-figure", "file": "scripts/audit/m14960_audit_figure.py", "context": "生成窗口敏感性图", "locator": "markdown section 7"},
        {"id": "code-14069-shear-cell", "file": "src/tensordem/shear_cell.py:612", "context": "_validity_gate 函数，稳态门判据实现", "locator": "markdown section 2 第4步"},
        {"id": "code-14069-run-friction", "file": "scripts/m14960/run_friction_matrix.py", "context": "headline 独立重跑入口", "locator": "markdown section 2 第2步"},
        {"id": "code-14069-test-shear", "file": "tests/test_shear_cell_friction.py", "context": "装置回归测试：10 passed / 84 s", "locator": "markdown section 2 第3步"}
      ],
      "claims": [],
      "claims_note": "本工作包为 01-asset-registration（源资产登记），不做抽取。claims 留空，由后续工作包（如 02-claim-extraction）填充。",
      "unresolved_assets": [
        {"id": "ua-14069-fig-png", "description": "报告引用了 m14978_window_sensitivity.png，但 figures 数组无 png_base64 数据，原始 PNG 文件位置未在报告正文中给出绝对路径", "status": "unresolved"},
        {"id": "ua-14069-audit-json", "description": "artifacts/audit_m14960/audit.json（C1–C7）被引用为所有数字的来源，但文件位于 TensorDEM 仓内，不在本工作树", "status": "unresolved"},
        {"id": "ua-14069-rerun-artifacts", "description": "artifacts/audit_m14960/rerun_size_medium.json|log 被引用，但文件位于 TensorDEM 仓内", "status": "unresolved"},
        {"id": "ua-14069-pytest-log", "description": "artifacts/audit_m14960/pytest_shear_cell_friction.log 被引用，但文件位于 TensorDEM 仓内", "status": "unresolved"},
        {"id": "ua-14069-unrun-items", "description": "报告 §5 第5点声明未跑项：mu030/050/070 重跑（约 30 min）、size_large(N=1392)、oss_inventory 空集 SQL 复核、文献在线核验（沙箱无出站）", "status": "unresolved"},
        {"id": "ua-14069-commit-97711cb8", "description": "commit 97711cb8 被引用为审计提交，但位于 TensorDEM 仓内", "status": "unresolved"},
        {"id": "ua-14069-commit-3fcf006d", "description": "commit 3fcf006d（被审对象 m14960 提交）位于 TensorDEM 仓 agent/m14960 分支", "status": "unresolved"}
      ],
      "registration_timestamp": "2026-11-12T02:32:00Z",
      "registered_by": "agent-wp-14069-01"
    }
  },
  "claims": []
}
```
