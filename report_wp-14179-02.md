# KF-RESULT wp-14179-02

tags: kf-wp:wp-14179-02, classification, audit, calib-reflux

## ① 本工序做了什么

本工作包 `wp-14179-02`（task_type=`02-classification-parse`）对报告 `report_id=14179` 进行类型分类与主题标签标注。报告标题为「交差审计 m14897 H5-CALIB-REFLUX：三件套重跑通过、A_hat 0.075539(+0.72%)/RT +0.384% → verdict L5」。

分类结论：
- **报告类型**：audit（交差审计）
- **学科域**：resistance（阻力）
- **子域**：calibration（标定/回流）
- **主题标签**：CALIB-REFLUX, calib_reflux_audit, holtrop, ittc57, friction_coefficient, kcs
- **船型**：KCS（KRISO 集装箱船）
- **判级**：L5
- **分层**：CALIB-REFLUX|calib_reflux_audit|m

本工序**不做抽取**（register_assets=false），仅打类型/主题标签并给出判定依据的原文片段定位。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取报告原文**：通过平台 API `GET /api/v1/tensor/reports/14179`（Bearer token 认证）获取 `markdown` 字段，共 5506 字符。
2. **哈希校验**：对 markdown 字节计算 SHA-256，结果为 `sha256:2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315`，与契约声明的 `source_hash` 一致。
3. **类型判定**：
   - 标题含「交差审计」→ report_type = `audit`
   - 内容涉及摩擦线常量 ITTC57_A 标定 → domain = `resistance`, subdomain = `calibration`
   - 验证船型为 KCS → ship_type = `KCS`
   - 判级段落明确 verdict = `L5`
4. **证据定位**：每个分类字段均绑定原文逐字引文片段（见④证据定位表）。
5. **JSON 产出**：按 `kf_result.v1.schema.json` 结构生成 `classification.json`，通过 schema 校验。

工具链：Python 3（urllib 获取 API、json 解析/校验、hashlib 计算 SHA-256）。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `classification.json` | 报告分类结果信封，含 package_id/task_type/report_id/provenance/outputs；outputs.classification.json 内含 report_type=audit, domain=resistance, subdomain=calibration, ship_type=KCS, verdict=L5, topic_tags 六项，layer=CALIB-REFLUX\|calib_reflux_audit\|m |

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 分类字段 | 判定值 | 原文引文（逐字） | 原文位置 |
|---|---|---|---|
| report_type | audit | `交差审计：m14897 H5-CALIB-REFLUX（ship-performance-platform）→ verdict **L5**` | 标题 |
| domain | resistance | `摩擦线常量 \`ITTC57_A = 0.075\`（\`backend/physics/holtrop/mennen.py:ittc57_cf\`）` | ① 案例介绍 |
| subdomain | calibration | `H5-CALIB-REFLUX · 高保真→经验系数回流` | ① 案例介绍 |
| ship_type | KCS | `**验证船型**：KCS（KRISO 集装箱船），几何先过门：Cb_lib=0.6509 vs` | ① 案例介绍 |
| verdict | L5 | `**verdict = L5**（完整、集成、可复现的科研工程机制；诚实注记：高保真源为 RANS 级、` | 判级（L0–L5 功能实质） |
| methods | Holtrop1984, TensorLBM, ITTC-57 | `**高保真源**：TensorLBM \`wall_model_les.flat_plate.run_flat_plate\`` | ① 案例介绍 |
| key_quantities | A_hat, RT, Cf | `A_hat=**0.075539**（ΔA/A=+0.72%）` / `RT **2109.49→2117.58 kN**（+0.384%）` | ③ 计算结果 |
| layer | CALIB-REFLUX\|calib_reflux_audit\|m | 契约 notes 指定 | 工作包契约 |

## ⑤ 注意点与局限

1. **仅分类不抽取**：本工序 contract 明确 `register_assets: false`，不做知识对象抽取（claims 数组为空是合法完整结果）。
2. **零手抄约束**：所有引文逐字来自报告 markdown，未凭记忆重述。
3. **不标 verified**：分类结果不标记为 verified（verification 由平台门计算）。
4. **单一报告边界**：仅处理 report_id=14179，未读/写/覆盖其它 report_id。
5. **分类主观性**：domain/subdomain 标签基于报告内容语义判定，不同分类体系可能有不同归类。

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | classification.json 通过 json.load() 解析 |
| schema_pass | ✅ | 所有 required 字段存在，pattern 校验通过（package_id/task_type/report_id/source_hash/source_field） |
| source_locator_resolvable | ✅ | 每个分类字段的 evidence_quote 均可在报告原文中逐字定位（6/6 通过） |
| source_hash_matches | ✅ | SHA-256 计算结果 `sha256:2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315` 与契约一致 |
| no_duplicate_ids | ✅ | 无 claim_id 重复（本工序无 claims 数组） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | 无 claims 需要处理；分类字段均有 evidence_quote 定位 |

**repro_cmd**：
```bash
cd /root/tp-agent/work/m19804 && python3 -c "
import json, hashlib, urllib.request
# 1. 获取报告
req = urllib.request.Request('http://127.0.0.1:8010/api/v1/auth/login',
    data=json.dumps({'username':'eco_admin','password':'EcoTest!2026pass'}).encode(),
    headers={'Content-Type':'application/json'})
token = json.loads(urllib.request.urlopen(req).read())['access_token']
req2 = urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/14179',
    headers={'Authorization': f'Bearer {token}'})
md = json.loads(urllib.request.urlopen(req2).read())['markdown']
# 2. 校验哈希
assert hashlib.sha256(md.encode()).hexdigest() == '2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315'
# 3. 加载并校验分类结果
with open('classification.json') as f:
    result = json.load(f)
assert result['package_id'] == 'wp-14179-02'
assert result['task_type'] == '02-classification-parse'
assert result['report_id'] == '14179'
assert 'classification.json' in result['outputs']
# 4. 校验所有 evidence_quote 在原文中可定位
rationale = result['outputs']['classification.json']['classification_rationale']
for field, info in rationale.items():
    assert info['evidence_quote'] in md, f'Quote not found for {field}'
print('ALL CHECKS PASSED')
"
```

```json
{
  "package_id": "wp-14179-02",
  "task_type": "02-classification-parse",
  "report_id": "14179",
  "provenance": {
    "source_hash": "sha256:2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315",
    "source_field": "markdown",
    "producer": "agent/m19804",
    "emitted_at": "2025-06-14T00:00:00Z",
    "notes": "Classification-only work package; no extraction performed per contract."
  },
  "outputs": {
    "classification.json": {
      "report_type": "audit",
      "report_subtype": "cross-audit",
      "domain": "resistance",
      "subdomain": "calibration",
      "topic_tags": [
        "CALIB-REFLUX",
        "calib_reflux_audit",
        "holtrop",
        "ittc57",
        "friction_coefficient",
        "kcs"
      ],
      "ship_type": "KCS",
      "ship_type_full": "KRISO Container Ship",
      "verdict": "L5",
      "methods": [
        "Holtrop1984",
        "TensorLBM",
        "ITTC-57"
      ],
      "key_quantities": [
        "A_hat",
        "RT",
        "Cf"
      ],
      "classification_rationale": {
        "report_type": {
          "value": "audit",
          "evidence_quote": "交差审计：m14897 H5-CALIB-REFLUX（ship-performance-platform）→ verdict **L5**",
          "source_section": "标题"
        },
        "domain": {
          "value": "resistance",
          "evidence_quote": "摩擦线常量 `ITTC57_A = 0.075`（`backend/physics/holtrop/mennen.py:ittc57_cf`）",
          "source_section": "① 案例介绍"
        },
        "subdomain": {
          "value": "calibration",
          "evidence_quote": "H5-CALIB-REFLUX · 高保真→经验系数回流",
          "source_section": "① 案例介绍"
        },
        "ship_type": {
          "value": "KCS",
          "evidence_quote": "**验证船型**：KCS（KRISO 集装箱船），几何先过门：Cb_lib=0.6509 vs",
          "source_section": "① 案例介绍"
        },
        "verdict": {
          "value": "L5",
          "evidence_quote": "**verdict = L5**（完整、集成、可复现的科研工程机制；诚实注记：高保真源为 RANS 级、",
          "source_section": "判级（L0–L5 功能实质）"
        },
        "methods": {
          "value": ["Holtrop1984", "TensorLBM", "ITTC-57"],
          "evidence_quote": "**高保真源**：TensorLBM `wall_model_les.flat_plate.run_flat_plate`",
          "source_section": "① 案例介绍"
        }
      },
      "layer": "CALIB-REFLUX|calib_reflux_audit|m"
    }
  }
}
```
