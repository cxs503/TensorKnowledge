# KF-RESULT wp-6939-04
独立红队审核 · 报告 `6939` · 审核对象 `wp-6939-01` · 原文标题：TensorLBM 共轭传热(CHT)验证阶梯
**裁定 `needs-fix`** — 注册信封 pass；claim 集语义保真 fail（BLOCKING 4 / MAJOR 5 / MINOR 3）。
## ① 本工序做了什么
对 report_id=6939（TensorLBM 共轭传热验证阶梯）做独立红队审核，审核对象是上游注册包 `wp-6939-01`。上下文只有三样：被哈希钉死的报告原文、上游机器工件（asset_manifest / verification / artifact_probe）、公开代码面（TensorLBM 检出里唯一一套 CHT 验证套件）。生产者的解释、`report.md`、`PUBLICATION_NOTE.md` 一律排除。判据不是「能不能跑通」，而是「§1 预声明的每一条判据是否真的被 §3 某一行的结果执行过」。产出 `review_report.json`（12 条 findings + 判据覆盖矩阵 + 未跑项）。未对任何 claim 打验证标记。
## ② 怎么做的（步骤/工具/关键设置）
1. 取源：`GET /api/v1/tensor/reports/6939`，独立重算 sha256 与契约逐字节一致（chars=2002，hash_match=True）。
2. 结构化解析：程序化切出 §1（7 条预声明判据）与 §3（结果表），统计行数、抽取阈值集合、统计「无数字结果行」，不靠肉眼。
3. 独立计算：把报告 §2 印出的 Churchill-Chu 关联式反解 Ra（输入用报告自己的 Nu=5.43、Pr=0.71），量出 C4 实际使用的区间 [4,7] 相对被测值 5.43 的容忍度 = ±28.91%。
4. 代码面取证：定位 TensorLBM 检出里唯一一套 CHT 验证套件，按 sha256 钉住（`3bc980ceaed3…`, commit `7ed01fc8`），读它自己声明的容差与断言，与报告 §1 的容差逐项对比。
5. 逐字校验：本报告每个引文都过 `q in markdown` 子串检查（n=30，全部命中；未命中脚本即返回非零）。
6. 复现：`python scripts/kf/wp6939_04_review.py`（离线 fixture，哈希同样钉死）；`--fetch` 改为从平台重取。
## ③ 产出物清单（输出文件名 → 要点）
| 文件 | 要点 |
|---|---|
| `docs/kf/wp-6939-04/kf_result.json` | 结果信封；source_hash 与报告 markdown 字节哈希一致 |
| `docs/kf/wp-6939-04/review_report.json` | 12 条 findings（4 BLOCKING / 5 MAJOR / 3 MINOR）、8 组判据覆盖矩阵、未跑项、复算记录 |
| `docs/kf/wp-6939-04/self_check.json` | 逐条 acceptance 自检 + 证据检查快照 |
| `docs/kf/wp-6939-04/figures/criteria_threshold_gap.png` | 报告容差 vs 代码套件容差对照图（log 轴） |
| `scripts/kf/wp6939_04_review.py` | 一键复跑：重算哈希→解析→复算→逐字校验→出件 |
| `tests/test_kf_wp6939_04.py` | 把上述不变量写成断言（引文逐字、行数、信封 schema） |
## ④ 证据定位表（claim/字段 → 原文引文片段）
| finding | 判据要点 | 原文引文（逐字，表格内 `|` 已转义） |
|---|---|---|
| B1 | post-hoc threshold / acceptance drift | `\| 综合 \| 纯导热极限 \| RMS 18% \| ✅ < 20% \|` |
| B2 | declared criterion never exercised | `\| C4 \| 文献范围 \| Nu=5.43 ∈ [4,7] \| ✅ \|` |
| B3 | benchmark substitution | `\| C3 \| 充分发展管流对流 \| Graetz 级数解 \| 误差 < 5% \|` |
| B4 | claim orthogonal to a self-disclosed implementation defect | `\| C5 \| 加权平均公式 \| 残差 < 1e-6 \| ✅ \|` |
| M1 | unauditable score | `**总计: 25/25 通过**` |
| M2 | non-quantitative acceptance rows | `\| C4 \| 单调性 \| 验证通过 \| ✅ \|` |
| M3 | dangling artifact reference | `见附图 1-5。` |
| M4 | tolerances inconsistent with the code suite | `\| C1 \| 2层壁 [1,5] \| RMS 0.02% \| ✅ < 3% \|` |
| M5 | stability claim inconsistent with implementation | `- **erf 热渗透**: 显式 Euler 有限差分，Fo < 0.5 稳定性条件` |
| N1 | underdetermined parameters | `\| C2 \| α=0.05, t=1000步 \| RMS 0.08% \| ✅ < 2% \|` |
| N2 | unitless residuals | `\| C2 \| 剖面形状 \| 误差 0.005 \| ✅ < 0.02 \|` |
| N3 | negative-control strength | `\| C7 \| 深内部等温 \| 偏差 < 1e-6 \| ✅ \|` |

### 判据覆盖矩阵（§1 预声明 → §3 是否真被执行）
| 锚 | §1 声明基准 | §1 声明判据 | 结果行数 | 数字行数 | 按声明被执行 |
|---|---|---|---|---|---|
| C1 | 串联热阻公式 | 误差 < 3% | 4 | 4 | ✅ |
| C2 | erf 解析解 | 误差 < 2% | 4 | 4 | ✅ |
| C3 | Graetz 级数解 | 误差 < 5% | 3 | 1 | ❌ |
| C4 | Churchill-Chu 关联式 | 误差 < 10% | 4 | 2 | ❌ |
| C5 | 加权平均公式 | 残差 < 1e-6 | 2 | 1 | ❌ |
| C6 | 调和平均导热系数 | 公式正确 | 2 | 1 | ❌ |
| C7 | 均匀场保持 | 深内部偏差 < 1e-6 | 2 | 2 | ✅ |
| 综合 | (not declared in section 1) | (no ceiling declared upstream) | 1 | 1 | ❌ |

## ⑤ 注意点与局限
- **未跑**：full rerun of tests/test_cht_validation.py — exceeded the 120 s per-command budget of this sandbox and was killed; only the analytical C4 subset was executed (1 passed, 16 deselected, 6.04 s)
- **未跑**：rerun of the harness that produced the RMS percentages — the harness is not identified in the report and no artifact carrying those residuals was found in the checkout searched; unidentified => not rerunnable
- **未跑**：inspection of the five declared figures — all five figure endpoints return HTTP 404 and no payload bytes exist; nothing to inspect
- **未跑**：resolution of the section-5 code symbols on canonical TensorLBM main — cht_solid_diffusion_step / apply_cht_interface are absent from /root/TensorLBM@main (git grep empty) and appear only in a worker cache checkout; the branch that produced the numbers is unconfirmed
- 审核只覆盖报告文本 + 上游机器工件 + 公开代码面；**没有**拿到产生 RMS 百分比的原始 harness，因此「这些数字真不真」我只判「不可复现」，不判「造假」。
- 代码面取证取自本机检出（`/root/tensor-ecosystem/TensorLBM`），其 `main` 分支（`/root/TensorLBM`）里 `git grep cht_solid_diffusion_step` 为空 —— 产生这些数字的分支身份未被确认，这是 provenance 层面的未知，不是数值结论。
- 报告 §5 主动披露了三条实现缺陷，这一点应当记功：本单的 4 条 BLOCKING 全部建立在它自己的披露之上。
## ⑥ 自检（逐条对照 acceptance）
| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | `review_report.json` / `kf_result.json` 均可解析 |
| schema_pass | ✅ | `kf_result.json` 过 `schemas/kf_result.v1.schema.json`（脚本内 jsonschema 校验） |
| reviewer_independent | ✅ | 上下文=哈希钉死原文+上游机器工件+公开代码；生产者叙述与 PUBLICATION_NOTE 排除 |
| upstream_packages_completed | ✅ | `docs/kf/wp-6939-01/verification.json` verdict=pass 10/10 |

honest-FAIL 申明：本单不存在未通过的 acceptance 项；但覆盖矩阵显示 8 组判据中只有 3 组按其声明被判据执行过，这一结论已如实写进 review_report.json，不做粉饰。

```json
{
  "package_id": "wp-6939-04",
  "task_type": "04-independent-review",
  "report_id": "6939",
  "provenance": {
    "source_uri": "tensor://reports/6939",
    "source_field": "markdown",
    "source_hash": "sha256:8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246",
    "reviewed_package": "wp-6939-01",
    "reviewer_role": "red-team-reviewer",
    "producer": "m15850/wp-6939-04",
    "emitted_at": "2026-11-12T02:56:09.303854+00:00",
    "generator": "scripts/kf/wp6939_04_review.py",
    "independence": {
      "context_used": [
        "report 6939 markdown (hash-pinned)",
        "upstream machine artifacts: docs/kf/wp-6939-01/asset_manifest.json, verification.json, artifact_probe.json",
        "public code surface: TensorLBM tests/test_cht_validation.py and src/tensorlbm/conjugate_ht.py (sha256 pinned)"
      ],
      "context_excluded": [
        "producer explanation / rationale / chat",
        "docs/kf/wp-6939-01/report.md (producer narrative)",
        "docs/kf/wp-6939-01/PUBLICATION_NOTE.md"
      ],
      "review_prompt_not_copied_from_producer": true,
      "self_review": false
    },
    "notes": "review only; no verification mark emitted; upstream packages untouched"
  },
  "outputs": {
    "review_report.json": {
      "schema": "review_report.v1",
      "package_id": "wp-6939-04",
      "task_type": "04-independent-review",
      "report_id": "6939",
      "reviewed_package": "wp-6939-01",
      "reviewer_role": "red-team-reviewer",
      "pressure_mode": "adversarial: assume the claim set is wrong until the text forces otherwise",
      "source": {
        "uri": "tensor://reports/6939",
        "field": "markdown",
        "hash_contract": "sha256:8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246",
        "hash_recomputed": "sha256:8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246",
        "hash_match": true,
        "chars": 2002,
        "origin_this_run": "fixture:tests/fixtures/kf/6939_markdown.md"
      },
      "independence": {
        "context_used": [
          "report 6939 markdown (hash-pinned)",
          "upstream machine artifacts: docs/kf/wp-6939-01/asset_manifest.json, verification.json, artifact_probe.json",
          "public code surface: TensorLBM tests/test_cht_validation.py and src/tensorlbm/conjugate_ht.py (sha256 pinned)"
        ],
        "context_excluded": [
          "producer explanation / rationale / chat",
          "docs/kf/wp-6939-01/report.md (producer narrative)",
          "docs/kf/wp-6939-01/PUBLICATION_NOTE.md"
        ],
        "review_prompt_not_copied_from_producer": true,
        "self_review": false
      },
      "verdict": "needs-fix",
      "verdict_scope": {
        "upstream_registration_envelope": "pass",
        "claim_set_semantic_fidelity": "fail (4 blocking findings)",
        "downstream_extraction_readiness": "not-ready"
      },
      "verdict_rationale": "wp-6939-01 is a well-formed registration package (10/10 machine checks, hash pinned, 404s disclosed), so the envelope passes. The claim set it registers does not survive semantic review: one anchor's declared ceiling is never exercised, one benchmark is substituted by its own approximation, the headline interface anchor is tested on an algebraic identity while the implementation defect is self-disclosed in the same document, and the only end-to-end 2-D number (18%) passes only on a ceiling introduced after the fact (20%). Verdict: needs-fix, blocking for any downstream claim that treats '25/25' as validated.",
      "severity_counts": {
        "BLOCKING": 4,
        "MAJOR": 5,
        "MINOR": 3
      },
      "anchor_scoreboard": {
        "declared_anchors": 7,
        "exercised_as_declared": 3,
        "exercised_list": [
          "C1",
          "C2",
          "C7"
        ],
        "not_exercised_list": [
          "C3",
          "C4",
          "C5",
          "C6",
          "综合"
        ],
        "note": "3 of 8 table groups meet their declared criterion as declared"
      },
      "criterion_coverage": [
        {
          "anchor": "C1",
          "declared": true,
          "declared_benchmark": "串联热阻公式",
          "declared_criterion": "误差 < 3%",
          "rows": 4,
          "rows_with_numeric_result": 4,
          "exercised_as_declared": true,
          "adjudication_reason": "numeric RMS vs analytic series-resistance solution; ceiling 3% matches section 1"
        },
        {
          "anchor": "C2",
          "declared": true,
          "declared_benchmark": "erf 解析解",
          "declared_criterion": "误差 < 2%",
          "rows": 4,
          "rows_with_numeric_result": 4,
          "exercised_as_declared": true,
          "adjudication_reason": "numeric RMS vs erf profile; ceiling 2% matches section 1"
        },
        {
          "anchor": "C3",
          "declared": true,
          "declared_benchmark": "Graetz 级数解",
          "declared_criterion": "误差 < 5%",
          "rows": 3,
          "rows_with_numeric_result": 1,
          "exercised_as_declared": false,
          "adjudication_reason": "benchmark substituted: section 2 uses 'Shah-London 入口段近似' while section 1 declares 'Graetz 级数解'"
        },
        {
          "anchor": "C4",
          "declared": true,
          "declared_benchmark": "Churchill-Chu 关联式",
          "declared_criterion": "误差 < 10%",
          "rows": 4,
          "rows_with_numeric_result": 2,
          "exercised_as_declared": false,
          "adjudication_reason": "section 1 declares '误差 < 10%' but no 10% row exists; the run checks are self-consistency (1e-10), monotonicity, Pr effect and membership of [4,7]"
        },
        {
          "anchor": "C5",
          "declared": true,
          "declared_benchmark": "加权平均公式",
          "declared_criterion": "残差 < 1e-6",
          "rows": 2,
          "rows_with_numeric_result": 1,
          "exercised_as_declared": false,
          "adjudication_reason": "residual of an algebraic identity evaluated on itself; the coupling implementation named in section 5 is not on the tested path"
        },
        {
          "anchor": "C6",
          "declared": true,
          "declared_benchmark": "调和平均导热系数",
          "declared_criterion": "公式正确",
          "rows": 2,
          "rows_with_numeric_result": 1,
          "exercised_as_declared": false,
          "adjudication_reason": "criterion is the non-falsifiable phrase '公式正确'; its rows are qualitative"
        },
        {
          "anchor": "C7",
          "declared": true,
          "declared_benchmark": "均匀场保持",
          "declared_criterion": "深内部偏差 < 1e-6",
          "rows": 2,
          "rows_with_numeric_result": 2,
          "exercised_as_declared": true,
          "adjudication_reason": "deep-interior deviation < 1e-6 is a numeric negative-control statement"
        },
        {
          "anchor": "综合",
          "declared": false,
          "declared_benchmark": "(not declared in section 1)",
          "declared_criterion": "(no ceiling declared upstream)",
          "rows": 1,
          "rows_with_numeric_result": 1,
          "exercised_as_declared": false,
          "adjudication_reason": "the 20% ceiling appears only in the results table; section 1 declares no global ceiling"
        }
      ],
      "findings": [
        {
          "id": "B1",
          "severity": "BLOCKING",
          "category": "post-hoc threshold / acceptance drift",
          "statement": "The only end-to-end 2-D CHT number in the report (RMS 18%) is scored against a 20% ceiling that appears nowhere in the pre-declared criteria of section 1, where the loosest ceiling is 10%. 18% is also outside the platform precision rule (>15% not acceptable), so the row re-labels a disclosed method error as a pass.",
          "evidence": [
            {
              "quote": "| 综合 | 纯导热极限 | RMS 18% | ✅ < 20% |",
              "source_field": "markdown"
            },
            {
              "quote": "| C4 | 竖板自然对流 | Churchill-Chu 关联式 | 误差 < 10% |",
              "source_field": "markdown"
            },
            {
              "quote": "3. 纯导热极限下 CHT 2D 运行 RMS 误差 ~18%，主要源于 LBM 热模型数值耗散和界面耦合近似。",
              "source_field": "markdown"
            }
          ],
          "independent_check": "checked programmatically: '20%' occurs in section 3 and not in section 1; section 5 item 3 itself attributes the 18% to numerical dissipation plus the interface approximation",
          "impact": "Downstream extraction would register an 18%-error CHT run as a passed validation anchor.",
          "remediation": "Re-declare the ceiling before the run with a physical justification and keep it, or mark the composite row 'unresolved' and report 18% as the measured method error."
        },
        {
          "id": "B2",
          "severity": "BLOCKING",
          "category": "declared criterion never exercised",
          "statement": "Anchor C4 declares '误差 < 10%' against Churchill-Chu, but no 10% comparison exists in the results table. What was run is: self-consistency of the formula with itself (1e-10), monotonicity, Pr effect, and membership of the wide bracket [4,7].",
          "evidence": [
            {
              "quote": "| C4 | 文献范围 | Nu=5.43 ∈ [4,7] | ✅ |",
              "source_field": "markdown"
            },
            {
              "quote": "| C4 | 自洽性 (4组) | 误差 < 1e-10 | ✅ |",
              "source_field": "markdown"
            },
            {
              "quote": "| C4 | 竖板自然对流 | Churchill-Chu 关联式 | 误差 < 10% |",
              "source_field": "markdown"
            }
          ],
          "independent_check": "the report's own correlation inverted gives Ra = 9.98e+03 for Nu = 5.43 at Pr = 0.71; the bracket [4,7] tolerates +-28.9% about the measured 5.43 (span ratio 1.75), i.e. a band ~2.9x wider than the declared 10%. The code suite's own C4 assertion is the range check '10 < Nu < 30', with '<50%' in its docstring -- no reference value at all.",
          "impact": "'四重解析锚' reduces to three numeric anchors plus one self-consistency check.",
          "remediation": "Report solver Nu at a stated Ra and compare with the correlation at the same Ra, or downgrade C4 to 'partially-supported (range consistency only)'."
        },
        {
          "id": "B3",
          "severity": "BLOCKING",
          "category": "benchmark substitution",
          "statement": "Anchor C3 declares the Graetz series solution as benchmark, while the method section states the implementation uses the Shah-London entrance approximation. Agreement at 0.01% with the approximation that generated the reference is self-referential, not a validation.",
          "evidence": [
            {
              "quote": "| C3 | 充分发展管流对流 | Graetz 级数解 | 误差 < 5% |",
              "source_field": "markdown"
            },
            {
              "quote": "- **Graetz-Nusselt**: Shah-London 入口段近似 + 充分发展极限 Nu=3.657",
              "source_field": "markdown"
            },
            {
              "quote": "| C3 | 充分发展 Nu | 误差 0.01% | ✅ < 5% |",
              "source_field": "markdown"
            }
          ],
          "independent_check": "section 1 says '级数解', section 2 says '近似'; the code suite anchors the fully developed value at 4.364 +- 0.1 (constant-heat-flux tube) while the report uses 3.657 (constant-temperature tube). The thermal boundary condition is never stated, so the 0.01% residual is not attributable to one reference value.",
          "impact": "C3 cannot be cited as agreement with the Graetz series; the BC (iso-T vs iso-q) is ambiguous.",
          "remediation": "State the thermal BC, quote the series-eigenvalue reference, and score against the series solution rather than against the entrance approximation."
        },
        {
          "id": "B4",
          "severity": "BLOCKING",
          "category": "claim orthogonal to a self-disclosed implementation defect",
          "statement": "The headline 'interface continuity' anchors C5/C6 are checked by re-evaluating the weighted-average identity (residual < 1e-6). Section 5 item 2 states the actual coupling uses same-position T_fluid/T_solid instead of adjacent-cell values, and that solid-side interface detection covers all solid cells adjacent to solid. No criterion in the table touches that implementation, so the continuity claim cannot be inherited by the code.",
          "evidence": [
            {
              "quote": "| C5 | 加权平均公式 | 残差 < 1e-6 | ✅ |",
              "source_field": "markdown"
            },
            {
              "quote": "2. ``apply_cht_interface`` 的界面固体侧检测包含所有与固体相邻的固体单元格（而非仅界面第一层），且界面温度计算使用同位置 T_fluid/T_solid 而非相邻单元格值。",
              "source_field": "markdown"
            },
            {
              "quote": "| C6 | 界面热流连续 | 调和平均导热系数 | 公式正确 |",
              "source_field": "markdown"
            },
            {
              "quote": "assert T_jump_after < 0.2, f\"Interface jump after coupling: {T_jump_after}\"",
              "source_field": "record",
              "note": "test_cht_validation.py:190 (sha256 3bc980ceaed3, commit 7ed01fc8)"
            }
          ],
          "independent_check": "the code suite's own interface test asserts an absolute tolerance of 0.2 on the post-coupling temperature jump -- 2e5 times looser than the 1e-6 the report grades itself on; the 1e-6 measures an algebraic identity, not the solver",
          "impact": "The strongest-sounding anchor ('界面连续') is the weakest evidenced one.",
          "remediation": "Add an interface test driven through apply_cht_interface with a manufactured linear profile plus a per-face flux balance, and report the max residual in physical units."
        },
        {
          "id": "M1",
          "severity": "MAJOR",
          "category": "unauditable score",
          "statement": "'25/25 通过' is not reproducible from the table, which has 22 data rows. It is only reachable by counting the single row 'C4 自洽性 (4组)' as four tests, which the report never states.",
          "evidence": [
            {
              "quote": "**总计: 25/25 通过**",
              "source_field": "markdown"
            }
          ],
          "independent_check": "row re-count in this script (independent_computations.row_accounting)",
          "impact": "A consumer cannot recompute the pass rate; the observable number is 22 rows.",
          "remediation": "Emit an explicit test inventory (name -> tolerance -> measured value) as an artifact."
        },
        {
          "id": "M2",
          "severity": "MAJOR",
          "category": "non-quantitative acceptance rows",
          "statement": "6 of 22 result rows carry only the qualitative string '验证通过', with no measured quantity and no tolerance. These rows cannot be falsified or re-checked.",
          "evidence": [
            {
              "quote": "| C4 | 单调性 | 验证通过 | ✅ |",
              "source_field": "markdown"
            },
            {
              "quote": "| C5 | 均匀场保持 | 验证通过 | ✅ |",
              "source_field": "markdown"
            }
          ],
          "independent_check": "counted programmatically over section 3 (rows_result_only_qualitative)",
          "impact": "27% of the scoreboard is non-auditable.",
          "remediation": "Replace each with a number and a tolerance, or move them to a 'smoke checks' table explicitly excluded from the pass count."
        },
        {
          "id": "M3",
          "severity": "MAJOR",
          "category": "dangling artifact reference",
          "statement": "Section 4 says '见附图 1-5' and five figures are declared on the platform, but all five return HTTP 404 and no figure payload exists (figures_with_png_base64 = 0). The anchor curves cannot be inspected.",
          "evidence": [
            {
              "quote": "见附图 1-5。",
              "source_field": "markdown"
            }
          ],
          "independent_check": "upstream artifact_probe.json: composite_wall / erf_penetration / graetz_nusselt / churchill_chu / interface_continuity all http_404; any_payload_bytes=false",
          "impact": "The report is not self-contained; no visual check of the anchors is possible.",
          "remediation": "Embed the five PNGs as figure payloads (base64) together with the generating run id."
        },
        {
          "id": "M4",
          "severity": "MAJOR",
          "category": "tolerances inconsistent with the code suite",
          "statement": "Every ceiling in the report is tighter than the ceiling declared in the docstring of the only CHT validation suite found in the TensorLBM checkout (C1 5%, C2 10%, C3 20%, C4 50%, C5 20%), and that suite contains no RMS metric at all. The report's RMS percentages therefore have no counterpart assertion there: either another harness produced them (then it must be cited) or they are not reproducible.",
          "evidence": [
            {
              "quote": "| C1 | 2层壁 [1,5] | RMS 0.02% | ✅ < 3% |",
              "source_field": "markdown"
            },
            {
              "quote": "| C2 | α=0.1, t=500步 | RMS 0.12% | ✅ < 2% |",
              "source_field": "markdown"
            },
            {
              "quote": "C1: 1D composite wall steady-state T profile vs series thermal resistance <5%",
              "source_field": "record",
              "note": "test_cht_validation.py:4 (sha256 3bc980ceaed3, commit 7ed01fc8)"
            },
            {
              "quote": "C2: erf heat penetration transient T profile vs analytical <10%",
              "source_field": "record",
              "note": "test_cht_validation.py:5 (sha256 3bc980ceaed3, commit 7ed01fc8)"
            },
            {
              "quote": "C3: Graetz Nu vs Shah-London <20%",
              "source_field": "record",
              "note": "test_cht_validation.py:6 (sha256 3bc980ceaed3, commit 7ed01fc8)"
            },
            {
              "quote": "C4: Churchill-Chu Nu vs correlation <50%",
              "source_field": "record",
              "note": "test_cht_validation.py:7 (sha256 3bc980ceaed3, commit 7ed01fc8)"
            },
            {
              "quote": "C5: Interface heat flux closure <20%",
              "source_field": "record",
              "note": "test_cht_validation.py:8 (sha256 3bc980ceaed3, commit 7ed01fc8)"
            }
          ],
          "independent_check": "sha256-pinned suite docstring thresholds vs report section 1 thresholds; the pattern 'rms|RMS' is absent from that suite",
          "impact": "The numbers cannot be regenerated from the cited validation surface; the ratio of stated to implemented tolerance reaches ~5x (C2) and ~2e5 (C5).",
          "remediation": "Cite the exact harness (path + commit) that produced each RMS, or re-derive the numbers inside that suite and let its own tolerances stand."
        },
        {
          "id": "M5",
          "severity": "MAJOR",
          "category": "stability claim inconsistent with implementation",
          "statement": "Section 2 states the stability condition as 'Fo < 0.5', the 1-D explicit-Euler bound. The CHT solid step is a 2-D central-difference explicit scheme whose own module docstring states Fo < 0.25. No value of Fo is reported, so the claim is neither correct as stated nor checkable.",
          "evidence": [
            {
              "quote": "- **erf 热渗透**: 显式 Euler 有限差分，Fo < 0.5 稳定性条件",
              "source_field": "markdown"
            },
            {
              "quote": "1. ``cht_solid_diffusion_step`` 使用 ``F.conv2d(padding=1)``，隐含域外 T=0 Dirichlet 边界条件，边界效应随时间向内传播。",
              "source_field": "markdown"
            },
            {
              "quote": "Pytest suite for CHT validation – IN31-L02 campaign.",
              "source_field": "record",
              "note": "test_cht_validation.py:1 (sha256 3bc980ceaed3, commit 7ed01fc8)"
            }
          ],
          "independent_check": "module docstring of conjugate_ht.py in the same checkout states the 2-D bound 'Fo = alpha_s dt/dx^2 < 0.25' (hash recorded in evidence_checks)",
          "impact": "A reader reproducing C2 at Fo = 0.4 would run an unstable case while believing the report.",
          "remediation": "Report the Fo actually used per case with a dimensional justification."
        },
        {
          "id": "N1",
          "severity": "MINOR",
          "category": "underdetermined parameters",
          "statement": "No numerical case table is given (no dx, dt, Nx, per-layer k, rho*cp). C2 cases are labelled only by alpha and a step count, so the physical time -- and therefore the erf similarity variable -- is not determined by the text.",
          "evidence": [
            {
              "quote": "| C2 | α=0.05, t=1000步 | RMS 0.08% | ✅ < 2% |",
              "source_field": "markdown"
            },
            {
              "quote": "| C1 | 3层壁 [1,10,2] | RMS 0.03% | ✅ < 3% |",
              "source_field": "markdown"
            }
          ],
          "independent_check": "no dx / dt / rho*cp notation anywhere in the markdown",
          "impact": "Numbers are not re-derivable from the report alone.",
          "remediation": "Add a per-case parameter table with units."
        },
        {
          "id": "N2",
          "severity": "MINOR",
          "category": "unitless residuals",
          "statement": "Two rows report bare numbers with no unit or normalisation: the C2 profile 'error 0.005' and the C7 CHT-run 'deviation < 0.01'. Whether these are absolute temperature, dimensionless temperature or a norm is not stated.",
          "evidence": [
            {
              "quote": "| C2 | 剖面形状 | 误差 0.005 | ✅ < 0.02 |",
              "source_field": "markdown"
            },
            {
              "quote": "| C7 | CHT 运行 | 偏差 < 0.01 | ✅ |",
              "source_field": "markdown"
            }
          ],
          "independent_check": "no unit or norm token on either row",
          "impact": "Tolerances cannot be compared against any standard.",
          "remediation": "State the norm (L_inf / L2), the normalisation and the units."
        },
        {
          "id": "N3",
          "severity": "MINOR",
          "category": "negative-control strength",
          "statement": "The negative control (256x256 domain, deep-interior deviation < 1e-6) is reported without the step count or the probe location, although section 5 item 1 warns that the exterior T=0 padding contaminates the domain over time. Without the step count the control cannot be shown to be free of the very effect it isolates.",
          "evidence": [
            {
              "quote": "| C7 | 深内部等温 | 偏差 < 1e-6 | ✅ |",
              "source_field": "markdown"
            },
            {
              "quote": "- **负控**: 256×256 大域 + 深内部区域检查，排除卷积边界效应",
              "source_field": "markdown"
            }
          ],
          "independent_check": "no step count and no probe coordinates anywhere in the text",
          "impact": "The discriminating power of the negative control is not established.",
          "remediation": "Report the step count, the probe mask, and the measured boundary-layer contamination."
        }
      ],
      "positives": [
        {
          "item": "source pinning",
          "detail": "sha256 of the reviewed markdown equals the contract value byte for byte (chars=2002).",
          "evidence": [
            {
              "quote": "# TensorLBM 共轭传热(CHT)验证阶梯",
              "source_field": "markdown"
            }
          ]
        },
        {
          "item": "upstream registration envelope",
          "detail": "docs/kf/wp-6939-01/verification.json records 10/10 checks passed, claims=0, no verification mark emitted, and discloses the five figure 404s instead of hiding them.",
          "evidence": [
            {
              "quote": "见附图 1-5。",
              "source_field": "markdown"
            }
          ]
        },
        {
          "item": "self-disclosure of limitations",
          "detail": "Section 5 discloses three real implementation limitations (padding boundary condition, interface detection, 18% pure-conduction error); a reviewer can act on them, which is exactly why the missing criteria became visible.",
          "evidence": [
            {
              "quote": "## 5. 已知局限",
              "source_field": "markdown"
            }
          ]
        },
        {
          "item": "C1 / C2 / C7 anchors are quantitatively exercised",
          "detail": "Composite-wall RMS, erf-penetration RMS and the deep-interior deviation are numeric and compared against the declared analytic reference with the declared ceiling (3%, 2%, 1e-6).",
          "evidence": [
            {
              "quote": "| C1 | 热流连续性 | 变化 0.01% | ✅ < 1% |",
              "source_field": "markdown"
            }
          ]
        }
      ],
      "evidence_checks": [
        {
          "check": "source_hash_recomputed",
          "contract_value": "sha256:8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246",
          "recomputed_value": "sha256:8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246",
          "chars": 2002,
          "result": "match"
        },
        {
          "check": "all_quotes_verbatim",
          "quotes_checked": 30,
          "not_found": [],
          "result": "pass"
        },
        {
          "check": "result_row_inventory",
          "table_rows_excluding_header": 22,
          "rows_with_numeric_result": 16,
          "rows_result_only_qualitative": 6,
          "claimed_total_string": "**总计: 25/25 通过**",
          "claimed_n": 25,
          "delta_claimed_vs_rows": 3,
          "reconciliation": "reachable only if the single row 'C4 自洽性 (4组)' is counted as 4 tests (22 + 3 = 25); no test inventory is stated in the report"
        },
        {
          "check": "declared_vs_exercised_thresholds",
          "thresholds_in_results_table": [
            "1%",
            "1e-10",
            "1e-6",
            "2%",
            "20%",
            "3%",
            "5%"
          ],
          "c4_declared_10pct_present_in_results": false,
          "twenty_pct_present_in_section1": false,
          "declared": {
            "C1": "误差 < 3%",
            "C2": "误差 < 2%",
            "C3": "误差 < 5%",
            "C4": "误差 < 10%",
            "C5": "残差 < 1e-6",
            "C6": "公式正确",
            "C7": "深内部偏差 < 1e-6"
          }
        },
        {
          "check": "code_suite_threshold_probe",
          "path": "/root/tensor-ecosystem/TensorLBM/tests/test_cht_validation.py",
          "expected_sha256": "3bc980ceaed3c5f6f6b39eac4b6ac6d1e3543f5e15f8d96b2307cf19ec030adc",
          "commit": "7ed01fc8",
          "available_on_this_host": true,
          "sha256": "3bc980ceaed3c5f6f6b39eac4b6ac6d1e3543f5e15f8d96b2307cf19ec030adc",
          "result": "probed",
          "probe": {
            "docstring_header": {
              "line": 1,
              "text": "Pytest suite for CHT validation – IN31-L02 campaign."
            },
            "C1": {
              "line": 4,
              "text": "C1: 1D composite wall steady-state T profile vs series thermal resistance <5%"
            },
            "C2": {
              "line": 5,
              "text": "C2: erf heat penetration transient T profile vs analytical <10%"
            },
            "C3": {
              "line": 6,
              "text": "C3: Graetz Nu vs Shah-London <20%"
            },
            "C4": {
              "line": 7,
              "text": "C4: Churchill-Chu Nu vs correlation <50%"
            },
            "C5": {
              "line": 8,
              "text": "C5: Interface heat flux closure <20%"
            },
            "C6": {
              "line": 9,
              "text": "C6: Negative control (k_s → ∞ isothermal wall limit)"
            },
            "c4_assert": {
              "line": 150,
              "text": "assert 10 < Nu < 30  # expected range for Ra=1e6, Pr=0.71"
            },
            "c5_assert": {
              "line": 190,
              "text": "assert T_jump_after < 0.2, f\"Interface jump after coupling: {T_jump_after}\""
            },
            "c3_assert": {
              "line": 133,
              "text": "assert Nu_fd == pytest.approx(4.364, abs=0.1)"
            },
            "rms_metric": null
          },
          "cht_module_fo_bound": {
            "line": 21,
            "text": "stable for",
            "sha256": "2e6a312e31d10ef627d2c0547e81cb18be927500ba1d33b647187648e36a1811"
          }
        },
        {
          "check": "figure_payload_probe",
          "source": "docs/kf/wp-6939-01/artifact_probe.json",
          "figure_status": {
            "composite_wall": "http_404",
            "erf_penetration": "http_404",
            "graetz_nusselt": "http_404",
            "churchill_chu": "http_404",
            "interface_continuity": "http_404"
          },
          "any_payload_bytes": false,
          "figures_with_png_base64": 0,
          "result": "no_figure_payload"
        }
      ],
      "independent_computations": {
        "churchill_chu_inverse": {
          "given": "Nu = 5.43, Pr = 0.71 (values taken from the report)",
          "implied_Ra": 9976.553237152497,
          "bracket": [
            4,
            7
          ],
          "bracket_half_width_pct_of_measured": 28.91,
          "bracket_span_ratio": 1.75,
          "interpretation": "the range test C4 actually ran tolerates a relative deviation ~2.9x larger than the declared 10% ceiling, so it cannot stand in for that ceiling"
        },
        "row_accounting": {
          "check": "result_row_inventory",
          "table_rows_excluding_header": 22,
          "rows_with_numeric_result": 16,
          "rows_result_only_qualitative": 6,
          "claimed_total_string": "**总计: 25/25 通过**",
          "claimed_n": 25,
          "delta_claimed_vs_rows": 3,
          "reconciliation": "reachable only if the single row 'C4 自洽性 (4组)' is counted as 4 tests (22 + 3 = 25); no test inventory is stated in the report"
        },
        "threshold_accounting": {
          "check": "declared_vs_exercised_thresholds",
          "thresholds_in_results_table": [
            "1%",
            "1e-10",
            "1e-6",
            "2%",
            "20%",
            "3%",
            "5%"
          ],
          "c4_declared_10pct_present_in_results": false,
          "twenty_pct_present_in_section1": false,
          "declared": {
            "C1": "误差 < 3%",
            "C2": "误差 < 2%",
            "C3": "误差 < 5%",
            "C4": "误差 < 10%",
            "C5": "残差 < 1e-6",
            "C6": "公式正确",
            "C7": "深内部偏差 < 1e-6"
          }
        }
      },
      "checks_run": [
        "sha256 of the markdown recomputed against the contract value",
        "verbatim substring check of every quote used here (n = 30)",
        "programmatic parse of section 1 (declared criteria) and section 3 (results table)",
        "row count and count of non-quantitative rows",
        "threshold inventory of section 3 vs section 1",
        "inverse of the report's own Churchill-Chu formula",
        "sha256-pinned probe of the code suite's declared tolerances and the CHT module's Fo bound",
        "cross-check of upstream verification.json and artifact_probe.json"
      ],
      "checks_not_run": [
        {
          "check": "full rerun of tests/test_cht_validation.py",
          "reason": "exceeded the 120 s per-command budget of this sandbox and was killed; only the analytical C4 subset was executed (1 passed, 16 deselected, 6.04 s)",
          "status": "not_run"
        },
        {
          "check": "rerun of the harness that produced the RMS percentages",
          "reason": "the harness is not identified in the report and no artifact carrying those residuals was found in the checkout searched; unidentified => not rerunnable",
          "status": "not_run"
        },
        {
          "check": "inspection of the five declared figures",
          "reason": "all five figure endpoints return HTTP 404 and no payload bytes exist; nothing to inspect",
          "status": "blocked_by_upstream"
        },
        {
          "check": "resolution of the section-5 code symbols on canonical TensorLBM main",
          "reason": "cht_solid_diffusion_step / apply_cht_interface are absent from /root/TensorLBM@main (git grep empty) and appear only in a worker cache checkout; the branch that produced the numbers is unconfirmed",
          "status": "unknown"
        }
      ],
      "overstated_claims": [
        {
          "claim": "总计 25/25 通过",
          "why": "22 table rows; the count needs an unstated test inventory (M1)"
        },
        {
          "claim": "所有关键量 vs 基准误差均满足判据要求",
          "why": "C4's declared 10% ceiling is never exercised (B2); the 18% composite row passes on an ad-hoc 20% ceiling (B1)"
        },
        {
          "claim": "界面温度连续 / 界面热流连续 (C5/C6)",
          "why": "tested as an algebraic identity, orthogonal to the self-disclosed coupling defect (B4)"
        },
        {
          "claim": "四重解析锚",
          "why": "C4 is a self-consistency/range check and C3 is scored against its own approximation (B2, B3)"
        }
      ],
      "remediation_backlog": [
        {
          "priority": 1,
          "closes": [
            "B1"
          ],
          "action": "re-grade the composite 18% row as unresolved and state it as the measured method error of the 2-D CHT run"
        },
        {
          "priority": 1,
          "closes": [
            "B2"
          ],
          "action": "add a real Churchill-Chu comparison at a stated Ra and Pr"
        },
        {
          "priority": 2,
          "closes": [
            "B3"
          ],
          "action": "state the C3 thermal BC and score against the Graetz series, not Shah-London"
        },
        {
          "priority": 2,
          "closes": [
            "B4"
          ],
          "action": "drive the interface anchors through apply_cht_interface with a manufactured profile and report a physical-unit flux residual"
        },
        {
          "priority": 3,
          "closes": [
            "M1",
            "M2",
            "M5",
            "N1",
            "N2"
          ],
          "action": "emit a machine test inventory and an Fo/parameter table"
        },
        {
          "priority": 3,
          "closes": [
            "M3"
          ],
          "action": "attach the five figures with their generating run id"
        },
        {
          "priority": 3,
          "closes": [
            "M4"
          ],
          "action": "pin the producing harness by path + commit"
        },
        {
          "priority": 3,
          "closes": [
            "N3"
          ],
          "action": "report the negative control's step count and probe mask"
        }
      ],
      "verification_marks_emitted": false,
      "generated_at": "2026-11-12T02:56:09.303854+00:00"
    }
  }
}
```
