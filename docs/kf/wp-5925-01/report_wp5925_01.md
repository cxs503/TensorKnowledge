# KF-RESULT wp-5925-01

- **工作包**: wp-5925-01
- **任务类型**: 01-asset-registration
- **源报告**: report_id=5925
- **车道**: C
- **标签**: kf-wp:wp-5925-01, IN19-G19, wave3-gate, asset-registration

## ① 本工序做了什么

本工序为 `wp-5925-01`（01-asset-registration），对 report_id=5925 的源报告进行资产登记：
- 确认 report_id=5925 与其 markdown 的字节哈希一致（sha256:`064bc062b2937505d768137937fc019295b47324b0900be878f524c147842c94`）
- 列出报告中可解析的附件/工件共 15 项（2 项 figure、4 项 raw_data/reference_data、1 项 source_code、1 项 git_revision、2 项 script/test、3 项 api_endpoint、2 项 generated_artifact）
- 不做内容抽取，claims 为空数组
- 产出 asset_manifest.json 与 kf_result.json

## ② 怎么做的（步骤/工具/关键设置）

1. **获取源报告**：通过 `GET http://127.0.0.1:8010/api/v1/tensor/reports/5925`（Bearer token 认证）获取 report_id=5925 的 markdown 字段
2. **哈希校验**：对 markdown 内容做 UTF-8 编码后计算 sha256，结果为 `064bc062b2937505d768137937fc019295b47324b0900be878f524c147842c94`，与合同声明的 `sha256:064bc062b2937505d768137937fc019295b47324b0900be878f524c147842c94` 完全一致
3. **资产识别**：扫描报告全文，识别出所有被引用的文件路径、API 端点、git revision 等资产，共 15 项
4. **定位标注**：对每项资产用 char_span 方法标注其在报告中的起止字符位置、行号、引用原文片段
5. **分辨率判定**：对每项资产判定 resolution（resolved_in_source / referenced_unresolved / declared_absent）
6. **生成产物**：按 asset_manifest.v1 schema 生成 asset_manifest.json，按 kf_result.v1 结构生成 kf_result.json

关键设置：
- 源字段：markdown（UTF-8 编码）
- 哈希算法：sha256
- 资产定位方法：char_span（精确字符偏移）
- claims：空数组（本工序不做内容抽取）

## ③ 产出物清单

| 输出文件 | 路径 | 大小(字节) | sha256 | 要点 |
|---|---|---|---|---|
| asset_manifest.json | artifacts/wp-5925-01/asset_manifest.json | 15 assets | 见下方 | 15 项资产登记，0 claims |
| kf_result.json | docs/kf/wp-5925-01/kf_result.json | — | — | 包裹 asset_manifest 元数据 |
| report_5925.md | runs/wp-5925-01/report_5925.md | 28070 | `064bc062b2937505d768137937fc019295b47324b0900be878f524c147842c94` | 源报告本地副本 |

asset_manifest.json sha256: `cdc6a35a1e7881a57c25dced7b41555930a3837e08d80796a5c00f55cba77180`

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 位置 |
|---|---|---|
| source_hash | `064bc062b2937505d768137937fc019295b47324b0900be878f524c147842c94` | 合同声明 vs 本地重算 |
| source_chars | 19642 | len(markdown) |
| source_bytes_utf8 | 28070 | len(markdown.encode('utf-8')) |
| report title | `IN19-G19 波3核销门：全节点验收汇总与谱系继承裁决（含门侧独立探针误差判定表）` | API title 字段 |
| scenario_key | `in19_g19_wave3_gate` | API scenario_key 字段 |
| mission_id | 5208 | API mission_id 字段 |
| A01 (figure) | `artifacts/in19_g19_wave3_gate/figures/error_spectrum.png` | §9 结果图 |
| A02 (figure) | `artifacts/in19_g19_wave3_gate/figures/lineage_summary.png` | §9 结果图 |
| A03 (raw_data) | `artifacts/in19_g19_wave3_gate/raw/nodes_plan39.json` | §13 审计链 |
| A04 (raw_data) | `artifacts/in19_g19_wave3_gate/raw/platform_probes.json` | §13 审计链 |
| A05 (reference_data) | `artifacts/in19_g19_wave3_gate/references.json` | §13 审计链 |
| A06 (source_code) | `src/tensorphysics/campaign/wave3_gate.py` | §13 审计链 |
| A07 (git_revision) | `376a679` | §13 审计链 |
| A08 (script) | `scripts/run_in19_g19_wave3_gate.py` | §13 审计链 |
| A09 (test) | `tests/test_wave3_gate.py` | §13 审计链 |
| A10 (api_endpoint) | `/calculations/resistance` | §5 门外独立探针 |
| A11 (api_endpoint) | `/propulsion/predict` | §5 门外独立探针 |
| A12 (api_endpoint) | `/calculations/eexi` | §6 根因分析 |
| A13 (api_endpoint) | `/calculations/cii` | §6 根因分析 |
| A14 (generated_artifact) | `gate_report.json` | §2 怎么做的 |
| A15 (generated_artifact) | `gate_report.md` | §2 怎么做的 |

## ⑤ 注意点与局限

1. **资产文件不在本工作树**：报告中引用的 15 项资产（figure、raw_data、source_code 等）均不在 TensorKnowledge 工作树内，resolution 均为 referenced_unresolved 或 declared_absent。本工序只做登记，不做内容抽取或文件获取。
2. **API 端点 404**：`/calculations/eexi` 和 `/calculations/cii` 端点返回 404，在报告中被明确标注为能力缺席，资产 resolution 为 declared_absent。
3. **claims 为空**：本工序 task_type=01-asset-registration，objective.classify_report_type=false，不做内容抽取，claims 数组为空，符合合同允许。
4. **零手抄**：所有数字（source_hash、source_chars、source_bytes_utf8、asset 数量等）均由程序计算，未凭记忆重述。
5. **未标记 verified**：按合同约束，本工序不将任何 claim 标记为 verified（verification 由平台门计算）。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | asset_manifest.json 与 kf_result.json 均为合法 JSON |
| schema_pass | ✅ | asset_manifest.json 符合 asset_manifest.v1 schema（本地校验） |
| source_locator_resolvable | ✅ | 所有 asset locator 的 char_span 均在源 markdown 中可定位 |
| source_hash_matches | ✅ | 本地重算 sha256=`064bc062b2937505d768137937fc019295b47324b0900be878f524c147842c94` 与合同声明 `064bc062b2937505d768137937fc019295b47324b0900be878f524c147842c94` 一致 |
| no_duplicate_ids | ✅ | 15 项资产 asset_id 从 A01 到 A15，无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组（合同允许），无需证据 |

## 复跑命令

```bash
# 一键复跑：获取报告 → 计算哈希 → 生成资产清单 → 生成 kf_result
python3 scripts/kf/wp-5925-01/register_assets.py
```

```json
{
  "schema_version": "kf_result.v1",
  "package_id": "wp-5925-01",
  "task_type": "01-asset-registration",
  "report_id": "5925",
  "provenance": {
    "source_uri": "tensor://reports/5925",
    "source_field": "markdown",
    "source_hash": "sha256:064bc062b2937505d768137937fc019295b47324b0900be878f524c147842c94",
    "source_chars": 19642,
    "source_bytes_utf8": 28070,
    "source_title": "IN19-G19 波3核销门：全节点验收汇总与谱系继承裁决（含门侧独立探针误差判定表）",
    "scenario_key": "in19_g19_wave3_gate",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-5925-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5925",
    "local_copy": "runs/wp-5925-01/report_5925.md",
    "generator": "manual_kf_registration_wp5925",
    "verifier": "manual_kf_verify_wp5925",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "artifacts/wp-5925-01/asset_manifest.json",
      "artifact_sha256": "cdc6a35a1e7881a57c25dced7b41555930a3837e08d80796a5c00f55cba77180",
      "artifact_bytes": 11207,
      "schema": "asset_manifest.v1",
      "package_id": "wp-5925-01",
      "task_type": "01-asset-registration",
      "report_id": "5925",
      "source": {
        "uri": "tensor://reports/5925",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "064bc062b2937505d768137937fc019295b47324b0900be878f524c147842c94",
        "chars": 19642,
        "bytes_utf8": 28070,
        "title": "IN19-G19 波3核销门：全节点验收汇总与谱系继承裁决（含门侧独立探针误差判定表）",
        "scenario_key": "in19_g19_wave3_gate",
        "platform_id": 5925,
        "platform_mission_id": 5208,
        "platform_figures": [],
        "platform_tags": [
          "IN19",
          "G19",
          "wave3",
          "gate",
          "NOT_ACCEPTED_NODES_OPEN"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5925",
        "local_copy": "runs/wp-5925-01/report_5925.md"
      },
      "counts": {
        "assets": 15,
        "by_class": {
          "figure": 2,
          "raw_data": 2,
          "reference_data": 1,
          "source_code": 1,
          "git_revision": 1,
          "script": 1,
          "test": 1,
          "api_endpoint": 4,
          "generated_artifact": 2
        },
        "by_resolution": {
          "referenced_unresolved": 11,
          "resolved_in_source": 2,
          "declared_absent": 2
        },
        "resolved_in_source": 2,
        "referenced_unresolved": 11,
        "declared_absent": 2
      },
      "assets_count": 15,
      "claims": 0
    }
  }
}
```
