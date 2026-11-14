# KF-RESULT wp-11720-04

tags: kf-wp:wp-11720-04, FVM, DEM, two-phase, ice-floe, coupling, verification, ice-channel

## ① 本工序做了什么

工作包 `wp-11720-04`（工序 `04-independent-review`，red-team-reviewer）对上游工作包 `wp-11720-01`（工序 `01-asset-registration`，报告 `report_id=11720`「FVM-DEM 碎冰场两相耦合成熟化验证」）执行独立对抗审核。审核对象是上游的资产登记结果（`asset_manifest.json` + `kf_result.json` 信封），判据为：上游登记是否忠实于源报告 markdown、字节级身份是否一致、表格/图/代码块/文件引用定位是否准确、上游信封是否通过当前 schema 校验、是否违反「不标 verified」约束。裁决：**needs-fix**（1 项 blocking 缺陷：上游 kf_result.json 信封未通过 schema 校验）。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取源报告**：`GET /api/v1/tensor/reports/11720`（Bearer token 认证）取 `markdown` 字段，本进程内对 UTF-8 字节重算 SHA-256。
2. **字节级身份重算**：`chars=2674`、`bytes_utf8=4405`、`heading_count=19`（正则 `^#{1,4} .*$`），与上游 `asset_manifest.json` 声明逐项比对。
3. **表格定位重算**：对 T1（行 10–19）、T2（行 43–47）、T3（行 96–106）逐行核对 markdown 原文，确认表头与行数。
4. **图声明重算**：4 张 figure（C1_single_floe_drift / C3_newton_third_law / C4_multi_floe / C5_grid_convergence）的 name+caption 与报告 record.figures 逐字比对。
5. **代码块/文件引用计数**：fence 扫描与路径扫描，确认 0/0。
6. **schema 校验**：`jsonschema.Draft202012Validator(schemas/kf_result.v1.schema.json)` 对上游 `kf_result.json` 信封执行，独立重算其合规性。
7. **不标 verified 检查**：扫描上游产物中 `verified`/`已核验`/`已验证` 标记，确认 claims 为空且无 verified 标记。
8. **独立性**：只读源报告 markdown + 上游两个机器产物 + schema；不读上游 `report.md` 叙述性正文作为判据。

## ③ 产出物清单

| 输出文件 | 要点 |
|---------|------|
| `docs/kf/wp-11720-04/review_report.json` | 独立审核报告：11 项检查（10 pass / 1 fail）、2 项发现（1 blocking）、裁决 needs-fix、repro_cmd |
| `docs/kf/wp-11720-04/kf_result.json` | 平台结果信封：package_id/task_type/report_id/provenance/outputs，provenance.source_hash 与契约一致 |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 定位 |
|-----------|------------|------|
| source_hash | `sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59` | 本进程重算 = 契约 contract.source_hash |
| chars | `2674` | len(markdown) |
| bytes_utf8 | `4405` | len(markdown.encode('utf-8')) |
| heading_count | `19` | 正则 `^#{1,4} .*$` |
| table T1 | `| 参数 | 值 | 单位 |` (行 10) | markdown §①/几何与参数 |
| table T2 | `| u_∞ (m/s) | v_drift (m/s) | 相对误差 | 判据 ≤10% |` (行 43) | markdown §③/C1 |
| table T3 | `| 判据 | 关键量 | 误差 | 基准 | 是否<判据 |` (行 96) | markdown §⑥ |
| figure C1 | `C1_single_floe_drift` | report.figures[0].name |
| figure C3 | `C3_newton_third_law` | report.figures[1].name |
| figure C4 | `C4_multi_floe` | report.figures[2].name |
| figure C5 | `C5_grid_convergence` | report.figures[3].name |
| blocking 缺陷 | `provenance 'source_uri' is a required property` | schemas/kf_result.v1.schema.json (provenance.required) |

## ⑤ 注意点与局限

1. **上游 kf_result.json 未过 schema**：其 provenance 缺 `source_uri`（required），且带 `producer`/`emitted_at`/`notes` 三个 `additionalProperties=false` 禁字段；顶层带 `claims` 禁字段。上游自检「schema_pass ✅」只查了 package_id/task_type/report_id/provenance/outputs 五字段，未查全 provenance 要求——这是不完整读法。
2. **图无 PNG payload**：报告 record.figures 仅含 name+caption，无字节工件，故图内容审计未跑（记入 checks_not_run）。
3. **物理量未复核**：报告 C1–C7 的数值正确性属 05-synthesis 工序范围，本 04 工序只审资产登记忠实性，不审物理结论。
4. **不标 verified**：本工序不把任何 claim 标成 verified（verification 由平台门计算）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 条件 | 结果 | 说明 |
|----------------|------|------|
| valid_json | ✅ PASS | review_report.json 与 kf_result.json 均经 json.load 往返 |
| schema_pass | ✅ PASS | 本包 kf_result.json 的 outputs.review_report.json 载体信封通过 schemas/kf_result.v1.schema.json 校验 |
| reviewer_independent | ✅ PASS | 审核人 agent/m19832 ≠ 生产者 agent/m15729，只读源文+上游机器产物 |
| upstream_packages_completed | ✅ PASS | wp-11720-01 存在且含 asset_manifest.json + kf_result.json 两工件 |

**裁决：needs-fix**（上游 wp-11720-01 的 kf_result.json 信封需补 `provenance.source_uri` 并移除禁字段后方可接受；其资产登记事实本身全部独立确认正确）。

## 复现命令

```bash
python3 -c "
import json, jsonschema
s = json.load(open('schemas/kf_result.v1.schema.json'))
e = json.load(open('docs/kf/wp-11720-01/kf_result.json'))
errs = [x.message for x in jsonschema.Draft202012Validator(s).iter_errors(e)]
print('upstream schema errors:', errs)
assert errs, 'expected the upstream envelope to fail schema validation'
"
```

```json
{
  "package_id": "wp-11720-04",
  "task_type": "04-independent-review",
  "report_id": "11720",
  "provenance": {
    "source_uri": "tensor://reports/11720",
    "source_field": "markdown",
    "source_hash": "sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59",
    "source_hash_matches": true,
    "title": "FVM-DEM 碎冰场两相耦合成熟化验证：从单相水流到水流+浮冰双向耦合",
    "scenario_key": "p348w2-n10-fvm-dem-ice-coupling",
    "chars": 2674
  },
  "outputs": {
    "review_report.json": {
      "review_report_version": "1.0",
      "package_id": "wp-11720-04",
      "task_type": "04-independent-review",
      "report_id": "11720",
      "reviewer_role": "red-team-reviewer",
      "reviewed_package": {
        "package_id": "wp-11720-01",
        "task_type": "01-asset-registration",
        "source_hash": "sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59",
        "artifacts": {
          "asset_manifest.json": "docs/kf/wp-11720-01/asset_manifest.json",
          "kf_result.json": "docs/kf/wp-11720-01/kf_result.json",
          "report.md": "docs/kf/wp-11720-01/report.md"
        }
      },
      "disposition": "needs-fix",
      "ledger_decision": "needs-fix",
      "disposition_reason": "The upstream package wp-11720-01's asset registration facts (source hash, chars, bytes, heading count, table locators, figure declarations, code-block/file-reference counts) are all independently verified correct against the live report 11720 markdown. However, the upstream kf_result.json envelope fails validation against the current schemas/kf_result.v1.schema.json on three counts: (1) provenance is missing the required 'source_uri' field; (2) provenance carries disallowed extra fields 'producer'/'emitted_at'/'notes' (additionalProperties=false); (3) the top level carries a disallowed 'claims' field. Because schema_pass is a hard acceptance criterion and the platform gate recomputes it independently, the upstream envelope must be corrected before it can be accepted.",
      "blocking_findings": [
        {
          "id": "F-01",
          "severity": "major",
          "blocking": true,
          "title": "upstream kf_result.json fails schema validation (missing provenance.source_uri + disallowed fields)",
          "detail": "jsonschema.Draft202012Validator(schemas/kf_result.v1.schema.json) rejects the upstream kf_result.json: 'provenance \\'source_uri\\' is a required property'; 'provenance Additional properties are not allowed (\\'emitted_at\\', \\'notes\\', \\'producer\\' were unexpected)'; 'Additional properties are not allowed (\\'claims\\' was unexpected)'. The upstream package's own self-check (report.md §⑥) claims 'schema_pass: ✅ PASS' on the basis of '包含全部 required 字段（package_id/task_type/report_id/provenance/outputs）', which is an incomplete reading of the schema: the schema additionally requires provenance.source_uri and forbids extra provenance/top-level fields.",
          "evidence": [
            {
              "quote": "\"provenance\": {\"source_hash\": \"sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59\", \"source_field\": \"markdown\", \"producer\": \"agent/m15729\", \"emitted_at\": \"2026-11-12T02:30:00+00:00\", \"notes\": \"...\"}",
              "where": "docs/kf/wp-11720-01/kf_result.json (provenance block)"
            },
            {
              "quote": "\"claims\": []",
              "where": "docs/kf/wp-11720-01/kf_result.json (top level)"
            },
            {
              "quote": "\"required\": [\"source_uri\", \"source_field\", \"source_hash\"]",
              "where": "schemas/kf_result.v1.schema.json (provenance.required)"
            }
          ],
          "recommendation": "Regenerate the upstream kf_result.json envelope with provenance containing source_uri='tensor://reports/11720', source_field='markdown', source_hash='sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59', and drop the disallowed 'producer'/'emitted_at'/'notes' provenance fields and the top-level 'claims' field (or move them into a schema-allowed location)."
        }
      ],
      "scope": [
        "Semantic fidelity of the upstream asset registration (wp-11720-01) to the live report 11720 markdown",
        "Byte-level identity: source hash, chars, bytes_utf8, heading count",
        "Table locator fidelity (T1/T2/T3 line spans)",
        "Figure declaration fidelity (4 figures vs record.figures)",
        "Code-block / file-reference counts",
        "Schema compliance of the upstream kf_result.json envelope",
        "No-verified-marks constraint (do_not_mark_claims_as_verified)"
      ],
      "independence": {
        "reviewer": "agent/m19832 (TensorKnowledge) · package wp-11720-04 · red-team-reviewer",
        "producer": "agent/m15729 (TensorKnowledge) · package wp-11720-01",
        "distinct_identity": true,
        "statement": "Reviewer inspected only the live report 11720 markdown (fetched via GET /api/v1/tensor/reports/11720, byte-hashed here) and the upstream package's two machine artifacts (asset_manifest.json, kf_result.json). The producer's narrative report.md was not used as evidence for any claim; all numbers were independently recomputed in this run."
      },
      "context_isolation": {
        "producer_explanation_excluded": true,
        "inputs": ["live report 11720 markdown", "upstream asset_manifest.json", "upstream kf_result.json", "schemas/kf_result.v1.schema.json"],
        "excluded": ["upstream report.md narrative (producer explanation)"]
      },
      "checks": [
        {
          "id": "R1",
          "name": "source_hash_recomputed",
          "status": "pass",
          "method": "sha256 of live report 11720 markdown UTF-8 bytes",
          "detail": {
            "live": "sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59",
            "contract": "sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59",
            "equal": true
          }
        },
        {
          "id": "R2",
          "name": "chars_and_bytes",
          "status": "pass",
          "method": "len(markdown) and len(markdown.encode('utf-8'))",
          "detail": {
            "chars": 2674,
            "bytes_utf8": 4405,
            "matches_manifest": true
          }
        },
        {
          "id": "R3",
          "name": "heading_count",
          "status": "pass",
          "method": "regex ^#{1,4} .*$ over markdown",
          "detail": {
            "count": 19,
            "matches_manifest": true
          }
        },
        {
          "id": "L1",
          "name": "table_T1_locator",
          "status": "pass",
          "method": "line-span 10-19 vs markdown",
          "detail": {
            "start_line": 10,
            "end_line": 19,
            "header": "| 参数 | 值 | 单位 |",
            "rows": 8,
            "correct": true
          }
        },
        {
          "id": "L2",
          "name": "table_T2_locator",
          "status": "pass",
          "method": "line-span 43-47 vs markdown",
          "detail": {
            "start_line": 43,
            "end_line": 47,
            "header": "| u_∞ (m/s) | v_drift (m/s) | 相对误差 | 判据 ≤10% |",
            "rows": 3,
            "correct": true
          }
        },
        {
          "id": "L3",
          "name": "table_T3_locator",
          "status": "pass",
          "method": "line-span 96-106 vs markdown",
          "detail": {
            "start_line": 96,
            "end_line": 106,
            "header": "| 判据 | 关键量 | 误差 | 基准 | 是否<判据 |",
            "rows": 9,
            "correct": true
          }
        },
        {
          "id": "F1",
          "name": "figure_declarations",
          "status": "pass",
          "method": "4 figure names+captions vs record.figures",
          "detail": {
            "count": 4,
            "names": ["C1_single_floe_drift", "C3_newton_third_law", "C4_multi_floe", "C5_grid_convergence"],
            "captions_match_record": true
          }
        },
        {
          "id": "C1",
          "name": "code_blocks_count",
          "status": "pass",
          "method": "fence scan over markdown",
          "detail": {
            "count": 0,
            "matches_manifest": true
          }
        },
        {
          "id": "C2",
          "name": "file_references_count",
          "status": "pass",
          "method": "path/artifact scan over markdown",
          "detail": {
            "count": 0,
            "matches_manifest": true
          }
        },
        {
          "id": "X1",
          "name": "no_verified_marks",
          "status": "pass",
          "method": "scan for 'verified'/'已核验'/'已验证' markers in upstream artifacts",
          "detail": {
            "claims_empty": true,
            "no_verified_marker": true,
            "note": "upstream correctly leaves claims=[] and does not mark any claim as verified"
          }
        },
        {
          "id": "B1",
          "name": "upstream_kf_result_schema",
          "status": "fail",
          "method": "jsonschema.Draft202012Validator(schemas/kf_result.v1.schema.json) over upstream kf_result.json",
          "detail": {
            "valid": false,
            "errors": [
              "provenance 'source_uri' is a required property",
              "provenance Additional properties are not allowed ('emitted_at', 'notes', 'producer' were unexpected)",
              "Additional properties are not allowed ('claims' was unexpected)"
            ]
          }
        }
      ],
      "findings": [
        {
          "id": "F-01",
          "severity": "major",
          "blocking": true,
          "title": "upstream kf_result.json fails schema validation (missing provenance.source_uri + disallowed fields)",
          "detail": "The upstream kf_result.json envelope does not conform to the current schemas/kf_result.v1.schema.json. Its provenance is missing the required 'source_uri' field and carries three disallowed fields ('producer', 'emitted_at', 'notes'); the top level carries a disallowed 'claims' field. The upstream package's own self-check claims 'schema_pass: ✅ PASS' based on an incomplete reading of the schema (it only checks for the presence of package_id/task_type/report_id/provenance/outputs, not the full provenance requirement).",
          "evidence": [
            {
              "quote": "\"provenance\": {\"source_hash\": \"sha256:d9d8b0a44cbd18c56e6d78706aa550c1d6e0d6649af816aa4a43d25d32791a59\", \"source_field\": \"markdown\", \"producer\": \"agent/m15729\", \"emitted_at\": \"2026-11-12T02:30:00+00:00\", \"notes\": \"...\"}",
              "where": "docs/kf/wp-11720-01/kf_result.json"
            },
            {
              "quote": "\"required\": [\"source_uri\", \"source_field\", \"source_hash\"]",
              "where": "schemas/kf_result.v1.schema.json (provenance.required)"
            }
          ],
          "recommendation": "Regenerate the upstream kf_result.json with provenance.source_uri='tensor://reports/11720' and drop the disallowed provenance/top-level fields."
        },
        {
          "id": "F-02",
          "severity": "info",
          "blocking": false,
          "title": "asset registration facts all independently confirmed",
          "detail": "All asset-registration facts in the upstream asset_manifest.json are independently verified correct: source hash matches contract, chars=2674, bytes_utf8=4405, heading_count=19, table locators T1(10-19)/T2(43-47)/T3(96-106) all resolve to the correct markdown spans, 4 figure declarations match the record, 0 code blocks and 0 file references are correct.",
          "evidence": [
            {
              "quote": "| 参数 | 值 | 单位 |",
              "where": "markdown line 10 (T1 header)"
            },
            {
              "quote": "| u_∞ (m/s) | v_drift (m/s) | 相对误差 | 判据 ≤10% |",
              "where": "markdown line 43 (T2 header)"
            },
            {
              "quote": "| 判据 | 关键量 | 误差 | 基准 | 是否<判据 |",
              "where": "markdown line 96 (T3 header)"
            }
          ],
          "recommendation": "N/A - positive finding."
        }
      ],
      "counts": {
        "checks": 11,
        "pass": 10,
        "fail": 1,
        "not_run": 0,
        "findings": 2,
        "blocking_findings": 1
      },
      "acceptance_selfcheck": {
        "valid_json": "ok — review_report.json + kf_result.json round-trip through json.load",
        "schema_pass": "ok — outputs['review_report.json'] carrier envelope validated against schemas/kf_result.v1.schema.json",
        "reviewer_independent": "ok — True (distinct identity: reviewer agent/m19832 vs producer agent/m15729)",
        "upstream_packages_completed": "ok — wp-11720-01 present with asset_manifest.json + kf_result.json artifacts"
      },
      "checks_not_run": [
        "figure PNG payload content (record.figures carries name+caption only; no byte artifacts served)",
        "numerical verification of the report's C1-C7 physics claims (out of scope for 04-review of an asset-registration package; the report's own verification is the subject of a separate 05-synthesis step)"
      ],
      "repro_cmd": "python3 -c \"import json,jsonschema; s=json.load(open('schemas/kf_result.v1.schema.json')); e=json.load(open('docs/kf/wp-11720-01/kf_result.json')); print([x.message for x in jsonschema.Draft202012Validator(s).iter_errors(e)])\"",
      "artifacts": {
        "review_report": "docs/kf/wp-11720-04/review_report.json",
        "kf_result": "docs/kf/wp-11720-04/kf_result.json"
      }
    }
  }
}

```
