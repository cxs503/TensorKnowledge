# KF-RESULT wp-6184-04

**工序** 04 独立审核（red-team） · **报告** report_id=6184 · **审核对象** `wp-6184-01`（01-asset-registration）
**结论** `verdict = pass`（阻断性失败 0 项；非阻断失败 1 项；未执行 1 项）

## ① 本工序做了什么

对上游 `wp-6184-01`（report 6184 的资产登记包）做独立审核：不采信生产者叙述，只用**报告原文 2406 字符**与**上游产物字节**重算一遍，判其登记是否忠实、计数是否掺水、是否自封验证、零 claim 是否合法；顺带用报告自己的数字做算术闭合探针，把过强的证据表述标出来供下游 03 抽取时不被传染。共 10 个探针，8 过 1 未执行 1 非阻断失败。

## ② 怎么做的（步骤/工具/关键设置）

1. `GET /api/v1/tensor/reports/6184`（Bearer）取 `markdown`，本地重算 `sha256` 得 `sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c`，与工作包契约 `input.source_hash` 逐字节相等，字符数 2406 与契约 2406 相等（探针 R1）。原文快照落盘 `source_snapshot.md`，使离线可复验。
2. 遍历上游 manifest 的 10 个资产，对每个 locator 重算 `markdown[start_char:end_char] == quote`、quote 在原文中的出现次数、以及 1-based 行号（R3）。
3. 用资产列表反算 `counts.assets / by_class / resolved_in_source`，与 manifest 自述比对（R4）；扫描上游信封是否出现自封验证字段（R6）。
4. 从原文表格解析 EEXI/要求/裕度三列，用**发布列**重算裕度，并按两列各自 3 位小数打印的舍入包络做**区间检验**（不是点值比对，避免把打印舍入当误差）（R7）；数出"不装 EPL 达标"的船数（R8）。
5. 探针 R9：报告自称 `EEXI ∝ P_ME^(2/3)`，用它复算 82k 散货的 EPL 27.4% —— 主机理式给 24.9%，差 2.5 个百分点，方向与"辅机项未被限功率"一致，但要闭合必须有引擎源码，故记 **not_run**，不记通过。
6. 探针 R10（补全度）：扫原文中所有反引号路径 token（4 个），排除整篇文档资产后比对 manifest，暴露 1 个未登记路径 → 发现项 F1。
7. 工具链：Python 3.11 + `scripts/kf/wp6184_review.py`（确定性，可 `--no-api` 离线复跑）、`scripts/kf/wp6184_figure.py`（证据图）、`pytest`。审核 prompt 由本工作包契约+原文自拟，未复制生产 prompt；上下文不含生产者 `provenance.notes` / `integrity.notes` / 上游叙述 MD。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `review_report.json` | 审核结论信封内容：10 探针状态 + 4 项发现（F1 minor / F2 major / F3-F4 minor）+ 语义忠实判定 + 下游告诫 + not_run 清单 |
| `review_report.schema.json` | 本包自带 schema（仓内无 review_report 统一 schema，供 `schema_pass` 机器可判） |
| `kf_result.json` | kf_result.v1 交付信封，`outputs["review_report.json"]` 即上表首项，本文件 sha256=sha256:5e8956b02802031e89a44531ea2ae19afa86430f8f0c8645905cadda920a2b88 |
| `source_snapshot.md` | 报告 6184 原文逐字节快照（sha256 与契约相等），离线复验用 |
| `upstream_snapshot/kf_result.json` | 上游 `wp-6184-01` 交付只读副本（sha256=sha256:a6621fa0bec51ea73dde089d1e01c6b1357c9579413ba7c52658c9b15444576f），未改写 |
| `review_checks.json` | 10 探针原始结果 + 11 行裕度区间 + EPL 探针 + 补全度扫描 |
| `figures/review_6184_evidence.png` | 左：探针状态矩阵（含非阻断失败，不隐藏）；右：报告发布裕度 vs 重算值（恒等线+舍入带） |
| `scripts/kf/wp6184_review.py` / `wp6184_figure.py` / `tests/test_wp6184_04_review.py` | 审核器 / 出图 / 12 条验收测试 |

## ④ 证据定位表（claim → 原文逐字片段）

| 判定 | 原文引文（逐字，可 `str.find` 定位） |
|---|---|
| 上游 source_hash 正确 | `sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c` 本地重算相等，2406 字符相等 |
| 10/10 资产 locator 字节精确 | 逐资产 `md[start:end] == quote` 全为真；行号 `1..43` 全部复现（R3 明细见 `review_checks.json`） |
| 零 claim 合法 | `claims: []` 且 `task_type=01-asset-registration`；01 的职责是登记不是抽取 |
| 内容不含自封验证 | 扫描 `verified / verification_status / verification_level / is_verified / gate_confirmed` 命中 0（R6） |
| F1 未登记资产 | `` `backend/api/green_shipping.py` 集装箱船 EEXI 削减率未按吨位分档（一律 20%） `` |
| F2 证据强度 | `| 达到 EEXI（11 船） | 独立闭式手算 | 0.0e+00 | **是** |` |
| F3 年份窗口自相矛盾 | `CII：2023→2026 评级随 Z% 收紧单调下降（如 Post-Panamax 8500TEU：E→E，比值 1.35→1.44）` 对比 §4 `CII 评级矩阵 2023–2027` |
| F4 几何关数自相矛盾 | `` `fleet`（几何三关） `` 对比 §3 `几何：12/12 过 Cb/L·B·T、DWT/Δ 包络、L/B·B/T 包络、高 Cb+高 Fn 组合检查。` |
| R7 算术闭合 | 11/11 行的发布裕度落在 `EEXI`/`要求` 两列打印舍入可达区间内（最大偏离 −7.2508 vs 发布 −7.2，band [−7.3216,−7.1799]） |
| R8 达标数 | `不装 EPL 达标 **2/11**` ↔ 表内仅 `feeder_1700teu`(16.417≤20.161)、`lng_174k`(5.157≤7.960) 达标 |
| R9 未闭合 | `例：82k 散货 attained 4.219 vs required 3.486（−21.0%，需 EPL 27.4%）` 与 `EEXI ∝ P_ME^(2/3)`：主机理式 24.9% |

## ⑤ 注意点与局限

- **审核对象与观察对象分离**：verdict 只判 `wp-6184-01`（登记是否忠实合法）。F2/F3/F4 是**报告本身**的证据强度/自洽问题，不改上游包 verdict，但下游 03 不得把 §6 前四行当作"独立/外部精度验证"来引用（`下游告诫` 已写入 review_report）。
- **F2 是本单最该被看见的一条**：标题与 §6 的 `0.00%` 建立在"独立闭式手算/双实现互校"两个未发布基线上；11 船**恰好** 0.0e+00 更像同一代数式的等价重算（R7 证明它至少是自洽的），而不是外部精度。若下游成稿照抄"外部基准 0.00%"，会把自洽说成验证。
- **不可闭合项已如实记 not_run**：R9 需引擎源码（在 ship-performance-platform，本仓不可达）；上游 `artifacts/in28_i1/checks.json`（`15/15 通过` 的唯一凭据）同样不可达 → 本单**不复制**该结论。
- **报告图不可读**：平台 `/tensor/reports/6184/figures/in28i1_figures_1to4.png` 返回 404，四联图只能按声明处理，未目视核对。
- 独立性是**程序性**的：新工位、契约自制 prompt、上下文只含原文与上游产物；但同一 owner 舰队、同一套服务，非组织级独立，已在 `reviewer.independence_limitations` 写明。
- 边界遵守：只碰 report_id=6184；未改写上游产物（只做只读副本）；未给任何结论打 verified（结论由平台门计算）。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | `review_report.json` / `kf_result.json` 均 `json.loads` 通过；测试 `test_review_report_is_valid_json` |
| `schema_pass` | ✅ | 经本包 `review_report.schema.json` 校验通过（`test_review_report_schema_pass`） |
| `reviewer_independent` | ✅ | 审核 prompt 契约自拟未复制生产 prompt；上下文排除生产者叙述；identity=agent/m15844 ≠ 上游 producer=agent/m15587 |
| `upstream_packages_completed` | ✅ | 上游 `wp-6184-01` 产物齐全（kf_result/asset_manifest/asset_manifest.schema/source_snapshot/verification），source_hash 与契约一致，10 资产 locator 全可解析 |
| `constraints.review_prompt_not_copied_from_producer` | ✅ | 审核器 prompt 为探针清单（见 ②），与生产抽取 prompt 无共享文本 |
| `constraints.reviewer_context_excludes_producer_explanation` | ✅ | `reviewer.context_excluded` 列明排除三项，判定只用原文与产物字节 |
| `constraints.do_not_mark_claims_as_verified` | ✅ | 全文无自封验证类字段名（`test_no_self_attestation_fields_anywhere`）；verdict 用 pass/fail |
| `objective.judge_semantic_fidelity` | ✅ | `semantic_fidelity.overall = faithful`，含 basis 与 residual_risk（0 claim、10 资产、7/10 保守标 unresolved） |

**honest-FAIL 项（不粉饰）**：`R9.epl_law_probe` = not_run（缺引擎源码，27.4% 与主机理式 24.9% 的 2.5pp 差**未闭合**）；`N2` 外部基准确认未做（源报告自述离线不可得，`WITHHELD`）。这两条使本单**不能**支持"引擎精度已外部验证"的任何说法。

## 复跑

```bash
# 一键复跑（工作树根 = TensorKnowledge 检出）
python3 scripts/kf/wp6184_review.py            # 联网取原文并重算全部探针 → review_report.json
python3 scripts/kf/wp6184_review.py --no-api   # 只对提交的 source_snapshot.md 离线复验
python3 scripts/kf/wp6184_figure.py            # 证据图
python3 -m pytest tests/test_wp6184_04_review.py -q   # 12 passed
```

## 结果信封（唯一 json 块）

```json
{
  "package_id": "wp-6184-04",
  "task_type": "04-independent-review",
  "report_id": "6184",
  "provenance": {
    "source_hash": "sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c",
    "source_field": "markdown",
    "producer": "agent/m15844 · scripts/kf/wp6184_review.py",
    "emitted_at": "2026-11-12T02:54:54.252783+00:00",
    "notes": "reviewer context = source markdown of report 6184 + upstream wp-6184-01 package artifacts + this work-package contract; producer narrative excluded. Upstream kf_result.json sha256=sha256:a6621fa0bec51ea73dde089d1e01c6b1357c9579413ba7c52658c9b15444576f. Verdict applies to the reviewed package; source-report findings are observations, listed separately."
  },
  "outputs": {
    "review_report.json": {
      "review_report_version": "1.0",
      "review_id": "wp-6184-04",
      "report_id": "6184",
      "mission_id": 15844,
      "reviewed_package": {
        "package_id": "wp-6184-01",
        "task_type": "01-asset-registration",
        "source_hash": "sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c",
        "producer": "agent/m15587 · scripts/kf/wp6184_register_assets.py",
        "emitted_at": "2026-11-12T01:28:39.580812+00:00"
      },
      "reviewer": {
        "role": "red-team-reviewer",
        "identity": "agent/m15844",
        "prompt_origin": "derived from this work package's contract plus the source markdown; not copied from the producer prompt",
        "context_consulted": [
          "source markdown of report 6184",
          "upstream asset_manifest.json / kf_result.json (claims, provenance)",
          "work-package contract wp-6184-04"
        ],
        "context_excluded": [
          "producer provenance.notes",
          "upstream integrity.notes",
          "upstream narrative markdown KF-RESULT_wp-6184-01.md"
        ],
        "independence_limitations": [
          "same serving infrastructure and same owner fleet as the producer; independence is procedural (fresh worker, contract-only prompt, source-and-objects-only context), not organisational",
          "engine sources (ship-performance-platform) and the upstream checks.json artifact are not reachable from this repository, so engine-level numbers cannot be reproduced here"
        ]
      },
      "verdict": "pass",
      "verdict_scope": "pass/fail judged on the reviewed package (asset registration): source identity, locator fidelity, count truthfulness, zero-claim legality, no self-attestation. Source-report findings are recorded as observations and do not change the package verdict.",
      "checks": [
        {
          "id": "R1.source_hash_matches",
          "name": "recomputed sha256(markdown) equals contract source_hash",
          "status": "pass",
          "blocking": true,
          "detail": "computed=sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c chars=2406 via GET /tensor/reports/6184",
          "evidence": {
            "contract_hash": "sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c",
            "contract_chars": 2406
          }
        },
        {
          "id": "R2.upstream_identity",
          "name": "upstream package addresses the same report and source bytes",
          "status": "pass",
          "blocking": true,
          "detail": "package=wp-6184-01 task=01-asset-registration report=6184 hash=sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c",
          "evidence": {}
        },
        {
          "id": "R3.locators_byte_exact",
          "name": "every asset quote equals markdown[start:end], is unique, line spans match",
          "status": "pass",
          "blocking": true,
          "detail": "10 assets; span/quote fails=[]; start_line fails=[]; end_line fails=[]",
          "evidence": {
            "per_asset": {
              "A01": {
                "quote_chars": 2406,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 1,
                "end_line_recomputed": 43,
                "start_line_declared": 1,
                "end_line_declared": 43,
                "quote_sha256": "sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c",
                "content_hash_declared": null,
                "long_enough_min12": true
              },
              "A02": {
                "quote_chars": 30,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 2,
                "end_line_recomputed": 2,
                "start_line_declared": 2,
                "end_line_declared": 2,
                "quote_sha256": "sha256:b63db74e74ec5db3f8377ad7f59049f6ff88e721749849d5c85e9f2579a02289",
                "content_hash_declared": null,
                "long_enough_min12": true
              },
              "A03": {
                "quote_chars": 297,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 4,
                "end_line_recomputed": 4,
                "start_line_declared": 4,
                "end_line_declared": 4,
                "quote_sha256": "sha256:02532b3433af99476f1e899a95154460586c680b4c6ed8e1e19018d6b2eebed4",
                "content_hash_declared": null,
                "long_enough_min12": true
              },
              "A04": {
                "quote_chars": 53,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 6,
                "end_line_recomputed": 6,
                "start_line_declared": 6,
                "end_line_declared": 6,
                "quote_sha256": "sha256:0671178d6e581e1b53c1a4ad8f541cc14234b3335fd3e38202d85cfbf2d0e4f4",
                "content_hash_declared": null,
                "long_enough_min12": true
              },
              "A05": {
                "quote_chars": 646,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 9,
                "end_line_recomputed": 21,
                "start_line_declared": 9,
                "end_line_declared": 21,
                "quote_sha256": "sha256:aa03a497c65d0c423956c7bf3e5dca17560648725d8dca826ef547308d78c077",
                "content_hash_declared": null,
                "long_enough_min12": true
              },
              "A06": {
                "quote_chars": 329,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 33,
                "end_line_recomputed": 40,
                "start_line_declared": 33,
                "end_line_declared": 40,
                "quote_sha256": "sha256:d5b0f4610ccda986acf0aa9b5fd53ac3910464260bc97e52d669c38fb692caa3",
                "content_hash_declared": null,
                "long_enough_min12": true
              },
              "A07": {
                "quote_chars": 93,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 27,
                "end_line_recomputed": 27,
                "start_line_declared": 27,
                "end_line_declared": 27,
                "quote_sha256": "sha256:376f816d9e7e65b766b9688ee372fd4ba6ba3b819544a3d54ce6a56bfc5bb79a",
                "content_hash_declared": null,
                "long_enough_min12": true
              },
              "A08": {
                "quote_chars": 27,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 4,
                "end_line_recomputed": 4,
                "start_line_declared": 4,
                "end_line_declared": 4,
                "quote_sha256": "sha256:b98c1fbb86700496596f7a4d1c5cdfaf7231378f519148f51b2f8ca1dada63e3",
                "content_hash_declared": null,
                "long_enough_min12": true
              },
              "A09": {
                "quote_chars": 55,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 4,
                "end_line_recomputed": 4,
                "start_line_declared": 4,
                "end_line_declared": 4,
                "quote_sha256": "sha256:e2c4756663e1872d0c88da1d44fcfd962ee269de98bc13830fbbc593d1ee7ec1",
                "content_hash_declared": null,
                "long_enough_min12": true
              },
              "A10": {
                "quote_chars": 66,
                "at_declared_span": true,
                "occurrences_in_source": 1,
                "declared_unique_satisfied": true,
                "start_line_recomputed": 40,
                "end_line_recomputed": 40,
                "start_line_declared": 40,
                "end_line_declared": 40,
                "quote_sha256": "sha256:f41fb2ccccc7bdbb05ef94546b20bd3497470c126ce6bdbe22617e9edf384b3c",
                "content_hash_declared": null,
                "long_enough_min12": true
              }
            }
          }
        },
        {
          "id": "R4.counts_consistent",
          "name": "manifest counts and class histogram equal the recomputed ones",
          "status": "pass",
          "blocking": true,
          "detail": "assets=10 by_class={'source_document': 1, 'code_pointer': 1, 'code_module': 2, 'artifact_file': 1, 'embedded_data_table': 2, 'figure': 1, 'external_standard': 1, 'external_dataset': 1} resolved_in_source=3",
          "evidence": {}
        },
        {
          "id": "R5.zero_claim_legality",
          "name": "an asset-registration package that asserts no knowledge is a legal complete result",
          "status": "pass",
          "blocking": true,
          "detail": "task_type=01-asset-registration claims=0",
          "evidence": {}
        },
        {
          "id": "R6.no_self_attestation",
          "name": "upstream does not self-attest a passed gate",
          "status": "pass",
          "blocking": true,
          "detail": "self-attestation field names matched: 0 of 5 scanned",
          "evidence": {
            "scanned_field_names": 5,
            "matched": 0
          }
        },
        {
          "id": "R7.margin_arithmetic",
          "name": "published margin column is reachable from the published EEXI/required columns",
          "status": "pass",
          "blocking": true,
          "detail": "rows=11 inside_band=11/11",
          "evidence": {
            "rows": [
              {
                "ship": "handymax_56",
                "margin_reported": -24.3,
                "margin_recomputed_pointwise": -24.3243,
                "feasible_band_from_print_rounding": [
                  -24.4012,
                  -24.2475
                ],
                "inside_band": true,
                "compliant_attained_le_required": false
              },
              {
                "ship": "panamax_82",
                "margin_reported": -21.0,
                "margin_recomputed_pointwise": -21.027,
                "feasible_band_from_print_rounding": [
                  -21.1087,
                  -20.9453
                ],
                "inside_band": true,
                "compliant_attained_le_required": false
              },
              {
                "ship": "capesize_180",
                "margin_reported": -28.8,
                "margin_recomputed_pointwise": -28.7563,
                "feasible_band_from_print_rounding": [
                  -28.854,
                  -28.6585
                ],
                "inside_band": true,
                "compliant_attained_le_required": false
              },
              {
                "ship": "mr2_50",
                "margin_reported": -7.2,
                "margin_recomputed_pointwise": -7.2508,
                "feasible_band_from_print_rounding": [
                  -7.3216,
                  -7.1799
                ],
                "inside_band": true,
                "compliant_attained_le_required": false
              },
              {
                "ship": "aframax_110",
                "margin_reported": -13.0,
                "margin_recomputed_pointwise": -13.0216,
                "feasible_band_from_print_rounding": [
                  -13.1031,
                  -12.9401
                ],
                "inside_band": true,
                "compliant_attained_le_required": false
              },
              {
                "ship": "vlcc_320",
                "margin_reported": -19.4,
                "margin_recomputed_pointwise": -19.432,
                "feasible_band_from_print_rounding": [
                  -19.5367,
                  -19.3273
                ],
                "inside_band": true,
                "compliant_attained_le_required": false
              },
              {
                "ship": "feeder_1700teu",
                "margin_reported": 18.6,
                "margin_recomputed_pointwise": 18.5705,
                "feasible_band_from_print_rounding": [
                  18.516,
                  18.625
                ],
                "inside_band": true,
                "compliant_attained_le_required": true
              },
              {
                "ship": "subpanamax_3500teu",
                "margin_reported": -3.6,
                "margin_recomputed_pointwise": -3.6031,
                "feasible_band_from_print_rounding": [
                  -3.6588,
                  -3.5473
                ],
                "inside_band": true,
                "compliant_attained_le_required": false
              },
              {
                "ship": "panamax_4500teu",
                "margin_reported": -3.6,
                "margin_recomputed_pointwise": -3.6262,
                "feasible_band_from_print_rounding": [
                  -3.6822,
                  -3.5702
                ],
                "inside_band": true,
                "compliant_attained_le_required": false
              },
              {
                "ship": "postpanamax_8500teu",
                "margin_reported": -20.9,
                "margin_recomputed_pointwise": -20.8997,
                "feasible_band_from_print_rounding": [
                  -20.9581,
                  -20.8412
                ],
                "inside_band": true,
                "compliant_attained_le_required": false
              },
              {
                "ship": "lng_174k",
                "margin_reported": 35.2,
                "margin_recomputed_pointwise": 35.2136,
                "feasible_band_from_print_rounding": [
                  35.1532,
                  35.2739
                ],
                "inside_band": true,
                "compliant_attained_le_required": true
              }
            ]
          }
        },
        {
          "id": "R8.compliance_count",
          "name": "the source's '2 of 11 compliant without EPL' reproduces",
          "status": "pass",
          "blocking": true,
          "detail": "compliant rows=['feeder_1700teu', 'lng_174k']",
          "evidence": {}
        },
        {
          "id": "R9.epl_law_probe",
          "name": "EPL 27.4% is reconcilable with the 2/3 power law the source states",
          "status": "not_run",
          "blocking": null,
          "detail": "requires the compliance engine sources (ship-performance-platform) — not reachable here",
          "evidence": {
            "probe": {
              "ship": "panamax_82",
              "attained": 4.219,
              "required": 3.486,
              "ratio_required_over_attained": 0.826262,
              "epl_pct_stated": 27.400000000000002,
              "epl_pct_from_2_3_law_main_engine_only": 24.894,
              "delta_percentage_points": 2.506,
              "implied_exponent_if_single_power_term": 1.678,
              "reading": "stated EPL exceeds the main-engine-only 2/3-law figure, i.e. the sign matches a fixed (non-limited) auxiliary term still present in the numerator; the engine code needed to close this is not in this repository, so the exact value stays unresolved",
              "resolved": false
            }
          }
        },
        {
          "id": "R10.asset_completeness",
          "name": "every path-like token named in the source is registered as an asset",
          "status": "fail",
          "blocking": false,
          "detail": "tokens=['artifacts/in28_i1/checks.json', 'backend/api/green_shipping.py', 'backend/modules/eexi_cii_compliance', 'fleet.py'] unregistered=['backend/api/green_shipping.py']",
          "evidence": {
            "path_like_tokens_in_source": [
              "artifacts/in28_i1/checks.json",
              "backend/api/green_shipping.py",
              "backend/modules/eexi_cii_compliance",
              "fleet.py"
            ],
            "registered": [
              "artifacts/in28_i1/checks.json",
              "backend/modules/eexi_cii_compliance",
              "fleet.py"
            ],
            "unregistered": [
              "backend/api/green_shipping.py"
            ]
          }
        }
      ],
      "summary_counts": {
        "checks": 10,
        "pass": 8,
        "fail_blocking": 0,
        "fail_non_blocking": 1,
        "not_run": 1
      },
      "findings": [
        {
          "id": "F1",
          "severity": "minor",
          "blocking": false,
          "target": "wp-6184-01",
          "statement": "one path named verbatim in the source is not registered as an asset: `backend/api/green_shipping.py` (source char 2243, §7). The manifest registers the compliance package and `fleet.py` but not the API module the source itself flags as defective.",
          "source_quote": "`backend/api/green_shipping.py` 集装箱船 EEXI 削减率未按吨位分档（一律 20%）",
          "impact": "inventory incompleteness: a downstream extraction that trusts the manifest as the asset list would not know the module exists; no incorrect statement is produced, so nothing is fabricated",
          "remediation": "register the module in a follow-up registration package; packages are not reusable, so do not edit wp-6184-01",
          "evidence": {
            "probe": "R10",
            "unregistered": [
              "backend/api/green_shipping.py"
            ]
          }
        },
        {
          "id": "F2",
          "severity": "major",
          "blocking": false,
          "target": "report 6184 §6",
          "statement": "the title and §6 headline '0.00% error' rests on baselines named '独立闭式手算' and '双实现互校'; the report publishes neither the closed form nor the second implementation, and exact 0.0e+00 on 11 ships is what an algebraically identical recomputation gives. Read as external validation it would be overstated; read as arithmetic self-consistency it is supported (probe R7).",
          "source_quote": "| 达到 EEXI（11 船） | 独立闭式手算 | 0.0e+00 | **是** |",
          "impact": "downstream knowledge objects must not cite this row as an independent/external accuracy result",
          "remediation": "cite the self-consistency baseline and point at the artifact holding the closed form before any external-accuracy framing",
          "evidence": {
            "probe": "R7",
            "margin_rows_inside_band": 11
          }
        },
        {
          "id": "F3",
          "severity": "minor",
          "blocking": false,
          "target": "report 6184 §3 vs §4",
          "statement": "the CII window is stated inconsistently: §3 says 2023→2026 while the figure caption in §4 says 2023–2027. The CII example given for 'monotonic decline' is E→E, which shows floor saturation rather than a decline (the worsening ratio 1.35→1.44 is the part that carries the statement).",
          "source_quote": "CII：2023→2026 评级随 Z% 收紧单调下降（如 Post-Panamax 8500TEU：E→E，比值 1.35→1.44）",
          "impact": "a downstream claim copied verbatim would inherit the wrong year range",
          "remediation": "state one window and quote the ratio, not the saturated grade",
          "evidence": {
            "also_in_source": "CII 评级矩阵 2023–2027"
          }
        },
        {
          "id": "F4",
          "severity": "minor",
          "blocking": false,
          "target": "report 6184 §2 vs §3",
          "statement": "geometry gate count disagrees with itself: §2 says `fleet`（几何三关） while §3 enumerates four checks (Cb/L·B·T, DWT/Δ envelope, L/B·B/T envelope, high-Cb + high-Fn combination).",
          "source_quote": "`fleet`（几何三关）",
          "impact": "reader cannot tell whether 3 or 4 gates produced '12/12'",
          "remediation": "name the four gates once, consistently",
          "evidence": {
            "also_in_source": "几何：12/12 过 Cb/L·B·T、DWT/Δ 包络、L/B·B/T 包络、高 Cb+高 Fn 组合检查。"
          }
        }
      ],
      "semantic_fidelity": {
        "judged": true,
        "claims_reviewed": 0,
        "assets_reviewed": 10,
        "overall": "faithful",
        "basis": "no knowledge claim is asserted, so no claim can over-reach; all 10 registered assets are byte-exact spans of the source; 7 of 10 are declared referenced_unresolved rather than inflated to 'resolved'; the manifest neither adds nor drops resolution status",
        "residual_risk": "completeness (F1) and the source report's own evidence strength (F2) — both outside what 01 asserts"
      },
      "downstream_advisories": [
        "03 extraction: attach verbatim quotes; the EEXI/CII table and §6 rows are the only numeric surfaces, and §6 rows 1-4 are self-consistency, not external accuracy.",
        "03 extraction: '15/15 通过' and 'artifacts/in28_i1/checks.json' are unverifiable from this repository (WITHHELD) — do not restate them as evidence.",
        "03 extraction: the EPL range 5.5-34.2% and the per-ship EPL figure are engine-derived; the report does not publish the auxiliary term, so keep them as reported values.",
        "05 synthesis: report 6184 discloses an unfixed defect in backend/api/green_shipping.py (container-ship reduction rate flat 20%, required value low by 12.5%) — the library engine is compliant, the API path for container ships is not."
      ],
      "checks_not_run": [
        {
          "id": "R9",
          "why": "needs the compliance engine sources and fleet spec, which live in ship-performance-platform, not in this repository"
        },
        {
          "id": "N1",
          "why": "re-execution of the upstream registration script (m15587 scripts/kf/wp6184_register_assets.py) — not present here; fidelity was re-derived from bytes instead"
        },
        {
          "id": "N2",
          "why": "external benchmark agreement (GISIS/VeriFuel point values) — the source itself declares them offline-unavailable and WITHHELD"
        }
      ],
      "limitations": [
        "verdict is about the review object (wp-6184-01); the report-level findings F2-F4 are observations on report 6184 and are not a package defect",
        "no external literature or MEPC text was fetched for this review; regulatory numbers were checked only for internal consistency, because the source itself marks the coefficient layer WITHHELD",
        "the source report's figures could not be inspected: the platform returns 404 for the figure attachment, so the four-panel figure is taken as declared, not read"
      ],
      "provenance": {
        "source_uri": "tensor://reports/6184",
        "source_field": "markdown",
        "source_hash": "sha256:f13e86a0dd27242b2872083e00f50b1c4cd5e4248a30b17de565db49d0aa310c",
        "source_chars": 2406,
        "source_snapshot": "source_snapshot.md",
        "upstream_kf_result_sha256": "sha256:a6621fa0bec51ea73dde089d1e01c6b1357c9579413ba7c52658c9b15444576f",
        "tool": "scripts/kf/wp6184_review.py",
        "generated_at": "2026-11-12T02:54:54.145520+00:00"
      },
      "acceptance_selfcheck": {
        "valid_json": true,
        "schema_pass": true,
        "reviewer_independent": true,
        "upstream_packages_completed": true
      }
    }
  }
}
```
