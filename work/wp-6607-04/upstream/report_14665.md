# KF-RESULT wp-6607-01

tags: kf-wp:wp-6607-01

## 1. 本工序做了什么

完成 report_id=6607 的源资产登记（task_type=01-asset-registration）。确认报告 markdown 字节哈希与契约一致，解析出 9 个可定位附件/工件（1 artifact、1 doc、3 figure、3 script、1 test），全部在原文中以字面子串形式出现。未做知识抽取（claims 为空数组，符合契约 objective.classify_report_type=false）。

## 2. 怎么做的

1. 通过 TENSOR_API_BASE 登录获取 token，GET /tensor/reports/6607 取 markdown 字段
2. 本地重算 sha256，与契约 source_hash 比对（一致 ✓）
3. 子串搜索定位 9 个资产引用，记录 char_span / line / quote
4. 按 schemas/asset_manifest.v1.schema.json 与 schemas/kf_result.v1.schema.json 组装输出
5. 零手抄：所有 locator.quote 均为原文逐字子串

关键设置：
- hash_alg: sha256
- source_field: markdown
- claims: []（契约允许空数组）

## 3. 产出物清单

| 输出文件 | 要点 |
|---|---|
| asset_manifest.json | 9 个资产登记，含 char_span locator、resolution_check、integrity 校验 |
| kf_result.json | KF 结果信封，包裹 asset_manifest.json |

## 4. 证据定位表

| 资产 | 原文引文片段（逐字） | char_span |
|---|---|---|
| A01 jamming_protocol.json | `artifacts/jamming_protocol/jamming_protocol.json` | [3258, 3306] |
| A02 granular2d_jamming_energy_minimization.md | `docs/granular2d_jamming_energy_minimization.md` | [3535, 3581] |
| A03 pressure_vs_phi.png | `pressure_vs_phi.png` | [7195, 7214] |
| A04 phi_j_vs_N.png | `phi_j_vs_N.png` | [7238, 7252] |
| A05 residual_history.png | `residual_history.png` | [7273, 7293] |
| A06 jamming_protocol_ablation.py | `benchmarks/jamming_protocol_ablation.py` | [7332, 7371] |
| A07 jamming_double_periodic_verification.py | `benchmarks/jamming_double_periodic_verification.py` | [7477, 7527] |
| A08 jamming_protocol_report.py | `benchmarks/jamming_protocol_report.py` | [7535, 7572] |
| A09 test_granular2d_energy_minimization.py | `tests/test_granular2d_energy_minimization.py` | [7590, 7634] |

## 5. 注意点与局限

- 本工序仅做资产登记，不做知识抽取/claims 生成（契约明确 classify_report_type=false）
- 所有资产均为"在原文中被引用"（resolved_in_source），未验证其实际存在性或可访问性
- 无图：本工序为纯文档/后端任务，不涉及计算结果可视化

## 6. 自检（逐条对照 acceptance）

- [✓] valid_json: asset_manifest.json 与 kf_result.json 均为合法 JSON
- [✓] schema_pass: 按 schemas/asset_manifest.v1.schema.json 与 schemas/kf_result.v1.schema.json 组装
- [✓] source_locator_resolvable: 9 个 locator.quote 均为原文逐字子串（substring_search=resolved）
- [✓] source_hash_matches: sha256 本地重算 = b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1，与契约一致
- [✓] no_duplicate_ids: A01–A09 唯一
- [✓] all_claims_have_evidence_or_explicit_unresolved_status: claims 为空数组（契约允许）

## 复现命令

```bash
python3 << 'EOF'
import os, requests, hashlib, json
base = os.environ['TENSOR_API_BASE']
token = requests.post(f'{base}/auth/login', json={'username': os.environ['TENSOR_AGENT_USER'], 'password': os.environ['TENSOR_AGENT_PASS']}).json()['access_token']
md = requests.get(f'{base}/tensor/reports/6607', headers={'Authorization': f'Bearer {token}'}).json()['markdown']
print('sha256:' + hashlib.sha256(md.encode()).hexdigest())
print('chars:', len(md))
EOF
```

```json
{
  "package_id": "wp-6607-01",
  "task_type": "01-asset-registration",
  "report_id": "6607",
  "provenance": {
    "source_hash": "sha256:b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1",
    "source_field": "markdown",
    "producer": "agent/m15592",
    "emitted_at": "2026-11-12T01:27:56.227518Z",
    "notes": "Asset registration only; no claim extraction (per contract objective.classify_report_type=false)"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-6607-01",
      "task_type": "01-asset-registration",
      "report_id": "6607",
      "source": {
        "uri": "tensor://reports/6607",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "b228e4f68599218d82dcedc7ca4166e0cc5250f9fbe34f611e86bc651a6231c1",
        "chars": 7642,
        "bytes_utf8": 11166,
        "title": "jamming 体积分数重锁：FIRE/CG 能量极小 + 双周期 + 有限尺寸标度（IN32-N02）",
        "scenario_key": "dem-granular-jamming"
      },
      "counts": {
        "assets": 9,
        "by_class": {
          "artifact": 1,
          "doc": 1,
          "figure": 3,
          "script": 3,
          "test": 1
        },
        "by_resolution": {
          "resolved_in_source": 9,
          "referenced_unresolved": 0,
          "declared_absent": 0
        },
        "resolved_in_source": 9,
        "referenced_unresolved": 0,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "artifact",
          "label": "jamming_protocol.json",
          "in_report_section": "§4 判据逐项",
          "locator": {
            "method": "char_span",
            "start_char": 3258,
            "end_char": 3306,
            "start_line": 76,
            "end_line": 76,
            "quote": "artifacts/jamming_protocol/jamming_protocol.json",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search",
            "result": "resolved"
          },
          "note": "Machine-readable criterion results JSON"
        },
        {
          "asset_id": "A02",
          "asset_class": "doc",
          "label": "granular2d_jamming_energy_minimization.md",
          "in_report_section": "§4 criterion a_fire_convergence",
          "locator": {
            "method": "char_span",
            "start_char": 3535,
            "end_char": 3581,
            "start_line": 80,
            "end_line": 80,
            "quote": "docs/granular2d_jamming_energy_minimization.md",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search",
            "result": "resolved"
          },
          "note": "Design doc for FIRE/CG energy minimization"
        },
        {
          "asset_id": "A03",
          "asset_class": "figure",
          "label": "pressure_vs_phi.png",
          "in_report_section": "§7 图",
          "locator": {
            "method": "char_span",
            "start_char": 7195,
            "end_char": 7214,
            "start_line": 125,
            "end_line": 125,
            "quote": "pressure_vs_phi.png",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search",
            "result": "resolved"
          },
          "note": "Four-protocol P(φ) EOS + literature window"
        },
        {
          "asset_id": "A04",
          "asset_class": "figure",
          "label": "phi_j_vs_N.png",
          "in_report_section": "§7 图",
          "locator": {
            "method": "char_span",
            "start_char": 7238,
            "end_char": 7252,
            "start_line": 125,
            "end_line": 125,
            "quote": "phi_j_vs_N.png",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search",
            "result": "resolved"
          },
          "note": "φ_J(N) finite-size scaling fit"
        },
        {
          "asset_id": "A05",
          "asset_class": "figure",
          "label": "residual_history.png",
          "in_report_section": "§7 图",
          "locator": {
            "method": "char_span",
            "start_char": 7273,
            "end_char": 7293,
            "start_line": 126,
            "end_line": 126,
            "quote": "residual_history.png",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search",
            "result": "resolved"
          },
          "note": "FIRE residual history"
        },
        {
          "asset_id": "A06",
          "asset_class": "script",
          "label": "jamming_protocol_ablation.py",
          "in_report_section": "§8 复现",
          "locator": {
            "method": "char_span",
            "start_char": 7332,
            "end_char": 7371,
            "start_line": 131,
            "end_line": 131,
            "quote": "benchmarks/jamming_protocol_ablation.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search",
            "result": "resolved"
          },
          "note": "Main ablation benchmark script"
        },
        {
          "asset_id": "A07",
          "asset_class": "script",
          "label": "jamming_double_periodic_verification.py",
          "in_report_section": "§8 复现",
          "locator": {
            "method": "char_span",
            "start_char": 7477,
            "end_char": 7527,
            "start_line": 133,
            "end_line": 133,
            "quote": "benchmarks/jamming_double_periodic_verification.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search",
            "result": "resolved"
          },
          "note": "Double periodic verification script"
        },
        {
          "asset_id": "A08",
          "asset_class": "script",
          "label": "jamming_protocol_report.py",
          "in_report_section": "§8 复现",
          "locator": {
            "method": "char_span",
            "start_char": 7535,
            "end_char": 7572,
            "start_line": 134,
            "end_line": 134,
            "quote": "benchmarks/jamming_protocol_report.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search",
            "result": "resolved"
          },
          "note": "Protocol report generation script"
        },
        {
          "asset_id": "A09",
          "asset_class": "test",
          "label": "test_granular2d_energy_minimization.py",
          "in_report_section": "§8 复现",
          "locator": {
            "method": "char_span",
            "start_char": 7590,
            "end_char": 7634,
            "start_line": 135,
            "end_line": 135,
            "quote": "tests/test_granular2d_energy_minimization.py",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "substring_search",
            "result": "resolved"
          },
          "note": "Pytest test suite (29 cases, 5 negative controls)"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": true,
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
