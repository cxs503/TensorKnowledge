# KF-RESULT wp-11243-04

tags: kf-wp:wp-11243-04, DEM, coarse-graining, independent-review, red-team

## ① 本工序做了什么

对 report_id=**11243**（DEM Coarse-Graining Scaling Law & Fine-Coarse Cross-Validation）的上游工作包 **wp-11243-01**（资产登记，task_type `01-asset-registration`）做**独立审核**（task_type `04-independent-review`，lane C，reviewer_role=red-team-reviewer）。

审核对象：wp-11243-01 的全部产物（result.json、asset_manifest.json、validation.json、selfcheck.json、tests/test_kf_wp_11243_01.py、source_report_11243.md 快照）。

审核结论：**request_changes**（2 项 blocking + 2 项 non-blocking）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **独立取源**：只读 `knowledge/kf/wp-11243-01/source_report_11243.md`（2701 字符，sha256 与契约一致）。
2. **独立哈希重算**：`sha256(utf-8 bytes) = d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598` ✓
3. **定位器逐条回验**：对 asset_manifest.json 中 8 个 markdown 定位器（A01, A07-A13）独立验证 char_span 切片相等、子串存在、出现次数=1、行号一致。
4. **Schema 独立校验**：用 `jsonschema.validate()` 对 result.json 和 asset_manifest.json 分别按 `kf_result.v1.schema.json` 和 `asset_manifest.v1.wp-11243-01.schema.json` 校验。
5. **测试套件复跑**：`pytest -q tests/test_kf_wp_11243_01.py` → 2 failed, 8 passed。
6. **物理推导独立验证**：从 t_c = π·√(m/k_n) 和 c = √(k_n/m)·L_char 出发，独立推导两种口径的全部 13 个量的标度关系，与报告表逐项比对。
7. **负控验证**：独立推导两个负控场景的破坏因子。
8. **失效边界验证**：独立检查 f=1,2,4,8 的边界判定与标度关系的一致性。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `knowledge/kf/wp-11243-04/review_report.json` | 主产物：4 项发现（2 blocking + 2 non-blocking）、语义保真度评估、acceptance 逐项判定 |

## ④ 证据定位表

| 发现 | 类别 | 原文/产物定位 | 证据 |
|---|---|---|---|
| F1 (blocking) | schema_violation | result.json top-level keys | `claims` 不在 schema properties 中；provenance 中 `producer/emitted_at/notes` 不在 schema 允许列表中 |
| F2 (blocking) | missing_artifact | knowledge/kf/wp-11243-01/figures/ | 目录不存在；test_ids_unique_and_figures_carried_with_hashes 报 FileNotFoundError |
| F3 (non-blocking) | counting_inconsistency | asset_manifest.json counts.assets | counts.assets=15 但 len(assets)=13；2 项在 unresolved_references 中 |
| F4 (non-blocking) | verification_gap | publish_verification.json | figure_bytes=74649 不匹配任何 platform figure（56766-131699） |

## ⑤ 注意点与局限

- **未运行 TensorDEM 测试**：报告摘要声称 "56 pytest items pass"，但 markdown 正文中无 pytest 出现（0 次）。上游包正确将此标为 referenced_unresolved。本审核不运行外部测试套件。
- **图文件缺失**：5 张图的 PNG 字节未落盘到本地 figures/ 目录，导致离线完整性检查无法完成。这可能是注册脚本的 bug 或环境清理所致。
- **Schema 版本**：本审核使用工作树内的 `schemas/kf_result.v1.schema.json`。若平台侧 schema 有更新，结论可能变化。
- **物理内容无缺陷**：源报告的技术内容（标度律推导、负控、失效边界）经独立验证全部内部一致。缺陷集中在元数据/包装层。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✓ | review_report.json 可被 json.loads 解析 |
| schema_pass | ✓ | review_report.json 通过 kf_result.v1 schema 校验 |
| reviewer_independent | ✓ | 审核未参考生产者解释；所有发现从原始产物独立推导 |
| upstream_packages_completed | ✓ | wp-11243-01 产物存在（尽管有缺陷） |

失败项：无（本审核产物自身通过所有 acceptance 检查）。

repro_cmd：

```bash
cd <worktree> && python3 -c "
import json, jsonschema
schema = json.load(open('schemas/kf_result.v1.schema.json'))
review = json.load(open('knowledge/kf/wp-11243-04/review_report.json'))
jsonschema.validate(review, schema)
print('PASS')
"
```

## 结果信封（唯一 json 块）

```json
{
  "package_id": "wp-11243-04",
  "task_type": "04-independent-review",
  "report_id": "11243",
  "contract_version": "1.0",
  "provenance": {
    "source_uri": "tensor://reports/11243",
    "source_field": "markdown",
    "source_hash": "sha256:d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598",
    "source_hash_matches": true,
    "title": "DEM Coarse-Graining Scaling Law & Fine-Coarse Cross-Validation",
    "scenario_key": "tensordem-cg-upscaling",
    "chars": 2701
  },
  "outputs": {
    "review_report.json": {
      "review_target": "wp-11243-01",
      "reviewer_role": "red-team-reviewer",
      "review_date": "2026-11-12",
      "disposition": "request_changes",
      "findings": [
        {
          "id": "F1",
          "severity": "blocking",
          "category": "schema_violation",
          "title": "result.json fails kf_result.v1 schema validation",
          "description": "The upstream result.json contains top-level field 'claims' (value []) which is not in the kf_result.v1 schema's allowed properties (additionalProperties: false). Additionally, the provenance object contains fields 'producer', 'emitted_at', 'notes' which are not in the schema's provenance properties. The upstream validation.json claims 'kf_result.v1: pass' but independent re-validation fails with: 'Additional properties are not allowed (claims was unexpected)' and 'Additional properties are not allowed (emitted_at, notes, producer were unexpected)'.",
          "evidence": {
            "result_json_keys": ["package_id", "task_type", "report_id", "provenance", "outputs", "claims"],
            "schema_allowed_top_level": ["package_id", "task_type", "contract_version", "report_id", "provenance", "outputs"],
            "provenance_extra_fields": ["producer", "emitted_at", "notes"],
            "schema_provenance_allowed": ["source_uri", "source_field", "source_hash", "source_hash_matches", "title", "scenario_key", "chars"],
            "validation_command": "python3 -c \"import json,jsonschema; jsonschema.validate(json.load(open('knowledge/kf/wp-11243-01/result.json')), json.load(open('schemas/kf_result.v1.schema.json')))\"",
            "validation_result": "ValidationError: Additional properties are not allowed ('claims' was unexpected)"
          },
          "affected_scope": "result.json envelope integrity; schema_pass acceptance item is incorrectly marked true",
          "remediation": "Remove 'claims' from top level of result.json; move 'producer', 'emitted_at', 'notes' out of provenance or add them to the schema. Re-run validation."
        },
        {
          "id": "F2",
          "severity": "blocking",
          "category": "missing_artifact",
          "title": "Figure PNG files missing from local filesystem",
          "description": "The asset_manifest.json declares 5 figure attachments (A02-A06) with saved_path values pointing to knowledge/kf/wp-11243-01/figures/fig*.png. The test test_ids_unique_and_figures_carried_with_hashes attempts to read these files and verify their sha256 hashes, but the figures/ directory does not exist. This causes the test to fail with FileNotFoundError. The manifest claims resolution_check bytes for each figure (e.g., fig1_scaling_laws: 131699 bytes) but the actual files are absent.",
          "evidence": {
            "expected_path": "knowledge/kf/wp-11243-01/figures/fig1_scaling_laws.png",
            "actual_status": "FileNotFoundError: [Errno 2] No such file or directory",
            "test_failure": "tests/test_kf_wp_11243_01.py::test_ids_unique_and_figures_carried_with_hashes FAILED",
            "manifest_figure_count": 5,
            "files_on_disk": 0
          },
          "affected_scope": "Figure asset integrity cannot be verified offline; test suite fails",
          "remediation": "Ensure figure PNG files are saved to the declared paths during registration, or update the manifest to reflect that figures are only available via platform API (not local disk)."
        },
        {
          "id": "F3",
          "severity": "non-blocking",
          "category": "counting_inconsistency",
          "title": "counts.assets (15) != len(assets) (13)",
          "description": "The manifest's counts.assets field is 15, but the assets array contains only 13 items. The remaining 2 items (U01: test_suite_evidence, U02: quantitative_result_statement) are in the unresolved_references array. The by_class counts (sum=15) include classes from both arrays. This is a design ambiguity: counts.assets appears to mean 'total registered items' rather than 'items in the assets array'.",
          "evidence": {
            "counts_assets": 15,
            "len_assets_array": 13,
            "len_unresolved_references": 2,
            "by_class_sum": 15,
            "by_class_includes_unresolved": true
          },
          "affected_scope": "Semantic clarity of counts; not a schema violation",
          "remediation": "Consider renaming counts.assets to counts.total_items or adding a separate counts.unresolved field for clarity."
        },
        {
          "id": "F4",
          "severity": "non-blocking",
          "category": "verification_gap",
          "title": "publish_verification.json figure does not match any platform figure",
          "description": "The publish_verification.json reports figure_bytes=74649 and figure_sha256=eb8221656adf769b... This does not match any of the 5 platform figures declared in the manifest (bytes range: 56766-131699). The report_id in publish_verification is 14790 (the platform report where the result was published), not 11243. This suggests the figure being verified is a report preview/attachment figure, not one of the source report's figures.",
          "evidence": {
            "publish_verification_figure_bytes": 74649,
            "publish_verification_figure_sha256": "eb8221656adf769b368a76986061eaab143b8edba0c92c4a9a399861cf79204c",
            "platform_figure_bytes_range": [56766, 131699],
            "publish_verification_report_id": 14790,
            "source_report_id": 11243
          },
          "affected_scope": "Clarity of what figure is being verified in publish_verification",
          "remediation": "Clarify whether publish_verification should verify source report figures or the published result report's figures."
        }
      ],
      "semantic_fidelity_assessment": {
        "physics_derivations": "PASS - Both scaling approaches (A: k_n∝f³, B: k_n∝f) are correctly derived from their invariance conditions. All 13 quantities in the scaling table are internally consistent.",
        "negative_controls": "PASS - Both negative controls (mass-only scaling breaks t_c by f^(3/2); wrong k_n scaling breaks c by f) are correctly derived.",
        "failure_boundaries": "PASS - The f=1,2,4,8 boundary table is consistent with the scaling derivations.",
        "applicability_domains": "PASS - Recommendations (f≤4 for both approaches) are consistent with the failure mode analysis.",
        "record_summary_claims": "UNRESOLVED - The record summary claims '56 pytest items pass' and '0% deviation' for shear/repose/E_eff, but these numbers do not appear in the markdown body (pytest: 0 occurrences, 56: 0, 0%: 0). The upstream package correctly flagged these as referenced_unresolved.",
        "overall": "The source report's technical content is internally consistent and physically sound. The defects are in the packaging/metadata layer, not in the scientific content."
      },
      "acceptance_review": {
        "valid_json": {
          "status": "PASS",
          "note": "result.json and asset_manifest.json are valid JSON"
        },
        "schema_pass": {
          "status": "FAIL",
          "note": "result.json does NOT pass kf_result.v1 schema validation (extra fields: claims, producer, emitted_at, notes). The upstream validation.json incorrectly claims pass."
        },
        "source_locator_resolvable": {
          "status": "PASS",
          "note": "All 8 markdown locators verified independently (char span, substring, uniqueness, line number). 2 record-field locators verified as substrings of carried summary."
        },
        "source_hash_matches": {
          "status": "PASS",
          "note": "Independent hash computation matches contract: sha256:d278a86d919c8f9093f0b1786fcbf15409897d999f6e960716334727d3117598"
        },
        "no_duplicate_ids": {
          "status": "PASS",
          "note": "15 IDs (A01-A13, U01-U02) are all unique"
        },
        "all_claims_have_evidence_or_explicit_unresolved_status": {
          "status": "PASS",
          "note": "claims=[] (empty, correct for task_type 01). No claims were fabricated."
        },
        "tests_pass": {
          "status": "FAIL",
          "note": "2 of 10 tests fail: test_ids_unique_and_figures_carried_with_hashes (missing figure files), test_envelope_validates_against_platform_schema (schema violation)"
        }
      },
      "independence_statement": "This review was conducted independently from the upstream package producer. The reviewer did not consult the producer's explanation, scripts, or internal reasoning. All findings are derived from: (1) the source report markdown, (2) the upstream package artifacts on disk, (3) the platform schemas, and (4) independent physics derivation checks.",
      "checks_not_run": [
        "Figure content verification (PNG files missing from disk)",
        "TensorDEM pytest suite execution (out of scope for task_type 01)",
        "Platform API live verification (API access blocked in this environment)",
        "Cross-report contamination check (only report_id=11243 was examined)"
      ],
      "disposition_rationale": "Two blocking issues (schema violation in result.json, missing figure files) prevent this package from passing the acceptance gate. The scientific content of the source report is sound, but the packaging layer has defects that must be fixed before the package can be considered complete."
    }
  }
}
```
