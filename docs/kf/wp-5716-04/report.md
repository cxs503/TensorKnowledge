## ① 本工序做了什么

目标：对 report_id=5716（IN10-G1 冰区航行全流程总攻验收门）的产出做**独立红队审核**（审核对象 wp-5716-01），只判语义保真：报告里的数量、判据、结论是否自洽、可复算、可定位。本单不改报告任何字节、不写其它 report_id、不给出 verified 标记（verification 由平台门计算）。

结论（disposition）：**needs-fix**。诚实基调可信（4 项披露项如实标不通过、外部锚点未粉饰、结构结论自认不通过），但存在 2 条阻断级事务性缺陷：同一物理量在报告内出现两个不同数值（C3 总时长 63.3 h vs 68.2 h），以及"7 项披露"与报告里实际可定位的 4 个披露 ID 不可调和。物理结论不必推翻，修复成本=编辑性订正 + 新增 1 条断言。

审核面统计：findings 10 条（high 3 / medium 3 / low 4），其中阻断 2 条；独立复算后**被证实自洽**的量 7 条（列在 ④ 下半表，避免只报负面）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文并钉哈希**：`scripts/kf/fetch_report_5716.py` 走 `GET $TENSOR_API_BASE/tensor/reports/5716`，把 `markdown` 原样落盘到 `docs/kf/wp-5716-04/source_5716.md`，重算 sha256 = `sha256:4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377`，与契约 source_hash 逐字相等（平台可独立重算，本单已自算一次）。
2. **零手抄机制（不是口号，是断言）**：`scripts/kf/review_wp_5716_04.py` 把审核要引用的 24 段引文登记在常量表 `Q` 里，运行时对每段做 `in markdown` 断言；任一段漂移即 `SystemExit`，不产出结果。④ 全部引文均由此断言担保。
3. **独立复算（reviewer 自己算，不采信自报）**：几何先验 Cb、B2 板格 β 修正后的 20 年利用率、D1/C3 平均航速与冰段速度反演、能量尺度、以及跨章节同量冲突扫描，全部由 Python 现算并写入 `docs/kf/wp-5716-04/recompute.json`（本报告数字全部来自该文件或引文，无手抄）。
4. **披露集合枚举**：对 markdown 做 `D0[0-9]-[A-Z0-9-]+` 正则，数出实际可定位的披露 ID。
5. **上下文隔离**：只读 `markdown` 字段（+ 仅用于溯源钉点的 id/title/tags/created_at）；**未使用**生产者的 summary/解释，**未接触**生产者代码与 `artifacts/campaign_ice_nav/*`（不在本工作树可及面）。
6. **出图**：`scripts/kf/fig_wp_5716_04.py` 从 markdown 的 ⑥ 表**直接解析**百分比行出图（数值不手抄），另从 recompute.json 出时间/速度闭合图（本机无 CJK 字体，图内标签为 reviewer 英译，已在图题声明）。
7. **自检门**：`scripts/kf/validate_wp_5716_04.py` 做 schema 校验 + 现场重取原文重算哈希 + 引文逐段复核 + 报告内 ```json 块唯一性与等价性。

一键复跑（工作树根执行，幂等；缺网可全部加 --offline 走 runs/ 快照）：

```text
python3 scripts/kf/fetch_report_5716.py --out docs/kf/wp-5716-04/source_5716.md && \
python3 scripts/kf/review_wp_5716_04.py --offline && \
python3 scripts/kf/fig_wp_5716_04.py && \
python3 scripts/kf/assemble_wp_5716_04.py --offline && \
python3 scripts/kf/validate_wp_5716_04.py && \
python3 -m pytest tests/test_wp_5716_04_review.py -q && \
python3 scripts/kf/verify_published_5716_04.py --report-id <published_id>
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-5716-04/review_report.json` | **契约声明的输出**：findings（含 severity/blocking/复现方法/影响/修复建议）+ corroborated_claims + checks_not_run + disposition |
| `docs/kf/wp-5716-04/recompute.json` | 全部复算中间量（输入、Cb 两口径、β 修正谱、速度/时间/能量闭合、冲突扫描、枚举计数），报告数字的唯一来源 |
| `docs/kf/wp-5716-04/figures/fig_review_errors.png` | ⑥ 表 10 个百分比项 vs 3% 验收线 / 25% 预登记筛选线（对数轴，值由 markdown 解析） |
| `docs/kf/wp-5716-04/figures/fig_review_closure.png` | 由报告总量反演的冰段平均速度 vs 报出的 4.50 kn 设计点 |
| `docs/kf/wp-5716-04/source_5716.md` (+`.meta.json`) | 原文快照与哈希钉点（provenance 可复算） |
| `scripts/kf/{fetch_report_5716,review_wp_5716_04,fig_wp_5716_04,validate_wp_5716_04}.py` | 一键复跑工具链 |
| `docs/kf/wp-5716-04/kf_result.json` | 结果信封（给机器门），与本报告唯一 json 块逐字一致 |

## ④ 证据定位表（claim/字段 → 原文引文片段，逐字）

阻断与主要缺陷：

| # | 审核判断 | 原文引文（逐字，脚本断言在文） |
|---|---|---|
| F1 | C3 总时长两处不同值 | 「C3：总航程 684.1 nm / 63.3 h / 203388 kWh；冰区占比 27.0%，设计点 4.50 kn, R_ice 464.7 kN」 ／ 「航线时间 54.4 h vs 剖面 68.2 h」 |
| F2 | 声称 7 项披露、实可定位 4 个 ID | 「16 项门断言 + 7 项披露」 ／ 「但有 4 项披露项如实不通过，不覆盖」 |
| F3 | 16 项断言无一闭合时间/能量；D1↔C3 未对账 | 「门判据 **16/16 通过**（要求 ≥8）」 ／ 「D1：主航线 684.1 nm / 54.5 h，no-go 0 nm」 ／ 「- A2→D1：冰量守恒 2.6e-14，方向探针 5.3e-05，覆盖 20.4%。」 |
| F4 | 墙钟两值（50.7 s vs 约 41.5 s） | 「墙钟 50.7 s」 ／ 「总链墙钟约 41.5 s（单核 CPU，无 GPU）」 |
| F5 | G01 的 Cb 公式缺密度步，字面代入自破其 2% 容差 | 「几何先验门：由独立排水量（DWT/0.8167）反算 Cb=0.82007 vs 声明 0.82（相对差 8.5e-5）」 ／ 「（L_pp=190 m, B=30 m, T=11.5 m, Cb=0.82, 主机 18 MW, 服务航速 13 kn」 |
| F6 | ⑥ 漏项（GM 0.09%）与无基线技能值 | 「GM 0.09%」 ／ 「A2：72 h 技能（vs 持续性）0.505，同化 RMSE 0.1145 m（冰图 0.1444 m），质量误差 0.0e+00，航窗可作业 10/12 lead。」 |
| F7 | 跨库 REAL 行 vs 未挂载降级条件 | 「| TensorFEM Mindlin Q4 vs 闭式 Mindlin | 0.211% | tensorfem.plate 闭式解 | 是 |」 ／ 「plan-12 外部仓库（TensorFEM/TensorDEM/TensorPhysics）若未挂载，对账项自动降级为 WITHHELD，不默认通过。」 |
| F8 | 质量误差恒零未给范数 | 「A2：72 h 技能（vs 持续性）0.505，同化 RMSE 0.1145 m（冰图 0.1444 m），质量误差 0.0e+00，航窗可作业 10/12 lead。」 |
| F9 | 测试计数无工件身份 | 「pytest `backend/tests/test_campaign_ice_nav.py` 13 passed；上游四套测试（ICE_DA 69、route 14、speed_profile 14、ice_belt 19）仍全绿。」 ／ 「`artifacts/campaign_ice_nav/campaign_acceptance.json`（含全链 sha256 清单）」 |
| F10 | 门阈 8/16 且 16 项均为自洽性；外部锚全数不通过 | 「门判据 **16/16 通过**（要求 ≥8）」 ／ 「| D1 vs C3 冰中航速（独立实现） | 65.6% | 两套生产模型互比 | 否 |」 ／ 「| B2 板格系数 vs 简支板理论 β | 75.8% | Navier 级数 0.2874 | 否 |」 |

独立复算**通过**的量（避免只报负面；也说明本次审核没有制造伪缺陷）：

| # | reviewer 复算 | 结果 | 结论 |
|---|---|---|---|
| V1 | Cb 两口径 | 字面（无密度）Cb=0.840577，相对差 2.5093%（>2% 容差，故 F5）；补 ρ=1.025 t/m³ 后 Cb=0.820075 | 报出 0.82007 可复现，缺陷仅在"未声明密度步" |
| V2 | 几何比 | L/B=6.3333、B/T=2.6087 | 与「6.333 / 2.609」一致 |
| V3 | β 修正后利用率 | β_B2≈0.5052，按 S-N 斜率 m=3 得 12.44 | 与原文「12.4」一致（m=3 与方向性未在文中声明，故只列 low 提示） |
| V4 | D07 65.6% | 4.50×(1+0.656)=7.452 kn | 与"同 (h,C) 下 ≈7.45 kn"自洽 |
| V5 | 平均航速 | D1 12.55 kn、C3(63.3h) 10.81 kn、C3(68.2h) 10.03 kn | 与 13 kn 服务航速量级自洽 |
| V6 | 能量尺度 | 203388 kWh / 63.3 h = 3213.1 kW（占 18 MW 的 17.9%），297.3 kWh/nm | 量级合理，无独立性冲突 |
| V7 | A2 同化增益 | (0.1444−0.1145)/0.1444 = 20.71% | 与"同化优于冰图"一致 |

## ⑤ 注意点与局限

1. **不可复跑的部分明确标 not_run（不标 pass）**：`modules.campaign_ice_nav.run_campaign` 的代码与 `artifacts/campaign_ice_nav/campaign_acceptance.json` sha256 台账都不在本工作树可及面，故 G13「台账可复算」、pytest 13 passed、上游 116 项测试、TensorFEM Q4 0.211% 均**未运行**，只登记为证据未绑定（F9/F7），不判真假。
2. **upstream_packages_completed 无法从平台 API 核验**：探测 `/tensor/reports/5716/packages`、`/tensor/work_packages?report_id=5716`、`/kf/packages?report_id=5716` 全部 404，`/tensor/reports?tags=...` 的 tags 过滤被服务端忽略（返回 total=100 与 limit 相同）。故该项在 ⑥ 标 `?`（unknown），不冒充 PASS。
3. **单审核人、无第二意见**，且审核面只有 markdown：报告引用的图（4 张在 figures 字段）本单未逐图核验数值一致性。
4. **F3 的"2.55×"是反演量不是断言错误**：由报告自身总量（684.1 nm、冰区 27.0%、开阔水 13 kn）反演冰段均速；若设计点 4.50 kn 仅代表最不利单个 lead，则反演值高于设计点属正常。报告缺逐段表，故该条只作为"门覆盖缺口"提，不作为"报告算错"。
5. **F5 的严重度按"可复算性"定，不按"结果错"定**：插入 ρ 后数值完全复现，所以这不是算错，而是断言文本不自足——但按报告自己的 2% 容差，字面代入是 FAIL，故必须写清 formula。
6. **未把任何结论标 verified**：本单只给 pass/fail/needs-fix 与证据，`verification_status` 字段显式写 `NOT_VERIFIED_BY_REVIEWER`。
7. 图内标签为英译（宿主无 CJK 字体），数值全部程序化解析，未手抄。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 判定 | 依据 |
|---|---|---|
| valid_json | 是 | `docs/kf/wp-5716-04/kf_result.json` 与报告唯一 json 块均由 json.load 解析通过（validate 脚本） |
| schema_pass | 是 | 对 `schemas/kf_result.v1.schema.json` 做 jsonschema 校验通过（必填 5 字段、additionalProperties=false、source_hash 正则 `^sha256:[0-9a-f]{64}$`） |
| reviewer_independent | 是 | 上下文仅 markdown + 自算；未用 producer summary/解释；未读其它 report_id。隔离声明写入 review_report.json 的 reviewer_independence 段 |
| upstream_packages_completed | ? unknown（不冒充 PASS） | 平台无 packages 端点（3 个候选路径 404，tags 过滤被忽略）；可达的唯一上游证据是 report 5716 本体（哈希相符）。见 ⑤.2 |
| constraints.review_prompt_not_copied_from_producer | 是 | 审核提示由本单契约文本给出，未从生产者产物反向取用；findings 全部为 reviewer 自算/自定位 |
| constraints.reviewer_context_excludes_producer_explanation | 是 | 只用 `markdown` 字段；summary 字段仅在 meta.json 中留档未被引用（findings 每条引文均可在 markdown 逐字定位） |
| constraints.do_not_mark_claims_as_verified | 是 | 全报告无 verified 标记；`verification_status=NOT_VERIFIED_BY_REVIEWER`；信封不含任何 verified 字段 |
| output.review_report.json | 是 | `docs/kf/wp-5716-04/review_report.json`（信封 outputs 键名一致） |

honest-FAIL 记录（不粉饰）：`upstream_packages_completed` 无法核验 → 标 unknown；本单**未运行**被测系统、**未复核**报告 4 张图、**未获**第二审核人意见。这三项都是真实的审核盲区，不能算通过。

```json
{
  "package_id": "wp-5716-04",
  "task_type": "04-independent-review",
  "report_id": "5716",
  "provenance": {
    "source_hash": "sha256:4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377",
    "source_field": "markdown",
    "producer": "m15839/agent/m15839",
    "emitted_at": "2026-11-12T02:53:01Z",
    "notes": "Independent red-team review of wp-5716-01. Context = report 5716 markdown + own arithmetic recomputation only; producer explanation excluded. No claim is marked verified."
  },
  "outputs": {
    "review_report.json": {
      "package_id": "wp-5716-04",
      "task_type": "04-independent-review",
      "reviewed_package": "wp-5716-01",
      "report_id": "5716",
      "reviewer_role": "red-team-reviewer",
      "reviewer_independence": {
        "context_used": [
          "report markdown (source_field=markdown)",
          "own arithmetic recomputation"
        ],
        "context_excluded": [
          "producer explanation / summary / chat",
          "producer code and artifacts under artifacts/campaign_ice_nav (not reachable from this worktree)",
          "any report_id other than 5716"
        ],
        "note": "The platform record snapshot at docs/kf/wp-5716-04/source_5716.md.meta.json was written only to pin provenance (id/title/tags/created_at) and its `summary` field was NOT used as review evidence; every finding below cites a verbatim substring of the markdown."
      },
      "scope": {
        "checks_performed": [
          "source hash recomputed from bytes and compared with the contract value",
          "verbatim-substring verification of every quoted fragment",
          "first-order arithmetic closure of Cb, beta correction, speeds, time, energy",
          "cross-section duplicate-quantity conflict scan (time, wall clock)",
          "disclosure-ID enumeration vs declared count",
          "assertion-table and error-table census"
        ],
        "checks_not_run": [
          "re-execution of modules.campaign_ice_nav.run_campaign (code lives in the ship-owners' backend repo, not in this worktree)",
          "verification of artifacts/campaign_ice_nav/campaign_acceptance.json sha256 ledger (not in reviewable surface; G13 not re-derivable)",
          "pytest backend/tests/test_campaign_ice_nav.py (13 claimed) and 116 upstream tests",
          "upstream package completion registry (no packages endpoint on the platform API: /tensor/reports/5716/packages, /tensor/work_packages, /kf/packages all 404)",
          "A2 OSSE skill re-computation (no observation source in the markdown)",
          "TensorFEM Q4 Mindlin 0.211% re-computation (cross-repo mount status unstated)"
        ],
        "unknown_not_passed": [
          "upstream_packages_completed",
          "G13 ledger recomputability",
          "test counts"
        ]
      },
      "provenance": {
        "source_uri": "tensor://reports/5716",
        "source_field": "markdown",
        "source_hash_recomputed": "sha256:4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377",
        "source_hash_matches_contract": true,
        "chars": 4790,
        "evidence_quotes_verified": 24,
        "recompute_artifact": "docs/kf/wp-5716-04/recompute.json"
      },
      "findings": [
        {
          "id": "F1-C3-TOTAL-TIME",
          "severity": "high",
          "blocking": true,
          "class": "internal numeric contradiction",
          "title": "C3 total voyage time is reported twice with different values (63.3 h vs 68.2 h)",
          "quote_keys": [
            "c3_totals",
            "d1_vs_c3_time",
            "d07_row"
          ],
          "measurements": {
            "t_hours_in_section3": 63.3,
            "t_hours_in_conclusion": 68.2,
            "rel_gap_pct": 7.7
          },
          "reproduction": "grep -o '63\\.3 h' / '68\\.2 h' on the fetched markdown; the two strings coexist and no caveat distinguishes them. Reconstruct mean speed: 684.1/63.3=10.81 kn vs 684.1/68.2=10.03 kn.",
          "impact": "every downstream consumer of C3 duration/energy-per-hour picks a different value depending on which section it reads; D07's '40–66%' divergence band is stated against an ambiguous basis",
          "remediation": "state one authoritative C3 duration (plus the alternative's definition, e.g. profile-with-acceleration vs delivered-legs), and add an assertion closing C3 total time and kWh against its own per-bin speeds"
        },
        {
          "id": "F2-DISCLOSURE-SET",
          "severity": "high",
          "blocking": true,
          "class": "unsupported claim / non-auditable disclosure set",
          "title": "Report declares '7 项披露' but enumerates only 4 disclosure IDs",
          "quote_keys": [
            "disclosure_count",
            "disclosure_four",
            "d01"
          ],
          "measurements": {
            "claimed_n": 7,
            "named_D_ids": [
              "D01-UIKKU-ANCHOR",
              "D02-PLATE-MINDLIN",
              "D06-STRUCTURAL-VERDICT",
              "D07-SPEED-MODEL-DIVERGENCE"
            ],
            "named_n": 4,
            "gap": 3
          },
          "reproduction": "regex `D0[0-9]-[A-Z0-9-]+` over the markdown yields exactly 4 IDs (D06, D01, D02, D07) against a declared 7",
          "impact": "the reviewable surface is smaller than claimed: 3 of 7 disclosures cannot be located, quoted or graded by any downstream consumer",
          "remediation": "list all 7 IDs with their predeclared criteria, or correct the count to 4"
        },
        {
          "id": "F3-NO-TIME-ENERGY-CLOSURE-ASSERTION",
          "severity": "high",
          "blocking": false,
          "class": "gate coverage gap (missing assertion)",
          "title": "none of the 16 assertions closes route time / energy against the per-leg speeds, and none reconciles D1 time with C3 time",
          "quote_keys": [
            "c3_totals",
            "d1_route",
            "regrid",
            "gate_threshold"
          ],
          "measurements": {
            "assumption": "ice share 27.0% of 684.1 nm, open-water at the stated 13 kn service speed",
            "ice_nm": 184.7,
            "open_water_nm": 499.4,
            "open_water_h": 38.41,
            "implied_mean_ice_kn": {
              "D1@54.5h": 11.48,
              "C3@63.3h": 7.42,
              "C3@68.2h": 6.2
            },
            "reported_design_point_kn": 4.5,
            "ratio_vs_design_point": {
              "D1@54.5h": 2.55,
              "C3@63.3h": 1.65
            },
            "verdict": "first-order closure is NOT satisfied at 11.48 kn (D1) / 7.42 kn (C3) vs the reported 4.50 kn design point; the report carries no per-leg table, so this cannot be resolved from the markdown"
          },
          "reproduction": "back-out the ice-segment speed from the report's own totals (684.1 nm, 27.0% ice, 13 kn open water): D1 -> 11.48 kn, C3 -> 7.42 kn, against a reported design point of 4.50 kn",
          "impact": "G12 re-computes length only and G10 checks units only, so a time/energy closure error would pass the gate silently; the 2.55x gap between the reconstructed D1 ice speed and the 4.50 kn design point is exactly the inconsistency class the gate does not cover",
          "remediation": "add G17-TIME-ENERGY-CLOSURE (sum of leg times == total time, sum of leg kWh == reported kWh, both <=1e-9 relative) and a per-leg table (leg, h_ice, v_kn, t_h, kWh)"
        },
        {
          "id": "F4-WALLCLOCK-CONFLICT",
          "severity": "medium",
          "blocking": false,
          "class": "internal numeric contradiction",
          "title": "End-to-end wall clock stated as 50.7 s in ② and ~41.5 s in ⑤ note 9",
          "quote_keys": [
            "wallclock_2",
            "wallclock_9"
          ],
          "measurements": {
            "s_section2": 50.7,
            "s_note9": 41.5,
            "rel_gap_pct": 18.1
          },
          "reproduction": "both literals present in the markdown; 18.1% apart",
          "impact": "a reproducibility claim is the cheapest thing to keep exact; an 18% self-disagreement weakens the sha256-ledger credibility",
          "remediation": "report one measured value with host/cores and the run id"
        },
        {
          "id": "F5-G01-CB-FORMULA-UNDERSPECIFIED",
          "severity": "medium",
          "blocking": false,
          "class": "assertion not reproducible from report text",
          "title": "G01's Cb formula (Cb = nabla/(L*B*T) from DWT/0.8167) omits the seawater-density step; applied literally it gives 2.51% and fails G01's own 2% tolerance",
          "quote_keys": [
            "geom_cb",
            "geom_cb_row",
            "geom_params"
          ],
          "measurements": {
            "literal": {
              "cb": 0.840577,
              "reported_cb": 0.82007,
              "rel_diff_pct_vs_0.82": 2.5093,
              "g01_own_tolerance_pct": 2.0,
              "verdict": "FAIL of G01's own 2% tolerance if the formula is applied literally (no density step)"
            },
            "with_rho_1.025": {
              "cb": 0.820075,
              "reported_cb": 0.82007,
              "rel_diff_pct_vs_0.82": 0.00911,
              "reported_rel_diff": 8.5e-05,
              "verdict": "reported value reproduces to display precision only when an unstated rho=1.025 t/m3 conversion is inserted"
            }
          },
          "reproduction": "45000/0.8167=55099.79 t -> /(190*30*11.5)=0.840577 (2.51% off 0.82); inserting rho=1.025 t/m3 gives 0.820075, which matches the reported 0.82007 to display precision",
          "impact": "the geometry prior gate is auditable only by a reader who guesses the unstated density; the report's own formula, taken literally, contradicts its PASS",
          "remediation": "write Cb = (DWT/0.8167/1.025)/(L*B*T) and state rho and its source in contracts.py"
        },
        {
          "id": "F6-ERROR-TABLE-SELECTION",
          "severity": "medium",
          "blocking": false,
          "class": "incomplete answer to the mandated 'is it <3%?' question",
          "title": "⑥ omits quantities stated elsewhere (E1 GM 0.09%) and gives no baseline value for A2 skill 0.505, so the '<3%' answer set is not complete or auditable",
          "quote_keys": [
            "e1_gm",
            "a2_line",
            "b2_beta_row"
          ],
          "measurements": {
            "rows": 13,
            "yes": 7,
            "no": 6
          },
          "reproduction": "count rows in ⑥: 13 rows, 7 是 / 6 否; GM 0.09% appears only in ③ and never in ⑥; '0.505' has no persistence-baseline number",
          "impact": "omissions here are conservative (GM would pass), but a reader cannot reconstruct which quantities the author considered key, and skill without a baseline number is not interpretable",
          "remediation": "make ⑥ a complete table over every headline quantity in ③, incl. GM and both skill/baseline"
        },
        {
          "id": "F7-FEM-REAL-VS-WITHHELD",
          "severity": "low",
          "blocking": false,
          "class": "evidence-grade ambiguity",
          "title": "TensorFEM Q4 0.211% is reported as a passing REAL row while note 8 says cross-repo checks auto-downgrade to WITHHELD when the repo is unmounted; the report never states which branch ran",
          "quote_keys": [
            "fem_row",
            "withheld_cond"
          ],
          "measurements": {
            "reported_rel_err_pct": 0.211
          },
          "reproduction": "both statements coexist; no mount status / repo ref is given",
          "impact": "the only cross-repo numeric binding is not traceable to a code identity",
          "remediation": "state mount status + repo commit for the TensorFEM check, or mark the row WITHHELD"
        },
        {
          "id": "F8-EXACT-ZERO-MASS-ERROR",
          "severity": "low",
          "blocking": false,
          "class": "unqualified exact-zero claim",
          "title": "A2 mass error is reported as exactly 0.0e+00 without norm definition",
          "quote_keys": [
            "a2_line"
          ],
          "measurements": {
            "reported": 0.0
          },
          "reproduction": "literal present; no L1/L2/relative definition, no ulp scale",
          "impact": "an exact zero in floating point is a strong claim; it is only credible for a conservation-by-construction scheme, which should be said explicitly",
          "remediation": "state the norm, the domain, and whether conservation is by construction"
        },
        {
          "id": "F9-TEST-EVIDENCE-UNBOUND",
          "severity": "low",
          "blocking": false,
          "class": "claim without artifact identity",
          "title": "13 pytest passes plus 116 upstream tests are cited without a log/commit/hash pointer",
          "quote_keys": [
            "tests",
            "artifacts"
          ],
          "measurements": {
            "campaign_tests": 13,
            "upstream_tests": 116
          },
          "reproduction": "numbers present; no artifact path or hash accompanies them",
          "impact": "G13 claims a sha256 ledger, but the cited JSON is outside the reviewable surface, so the ledger itself cannot be recomputed here",
          "remediation": "inline the ledger (stage -> sha256) and the pytest summary line, or attach a run id"
        },
        {
          "id": "F10-GATE-BAR-AND-SCOPE",
          "severity": "low",
          "blocking": false,
          "class": "overstated scope of the headline verdict",
          "title": "gate threshold is 8/16, and all 16 assertions are self-consistency: the only external anchors (D01, D02, D07) all fail, so 'gate PASS' must not be read as physics accuracy",
          "quote_keys": [
            "gate_threshold",
            "d07_row",
            "b2_beta_row",
            "d01",
            "honest_fail_scope"
          ],
          "measurements": {
            "pass_cells": 16,
            "rows_declared": 16,
            "gate_threshold": 8
          },
          "reproduction": "16 declared rows, 16 PASS cells; threshold ≥8; 3 external anchors fail",
          "impact": "a 50%-threshold consistency gate plus a 67.6 utilization FAIL in the same report means bare 'acceptance gate passed' is misleading",
          "remediation": "state in the verdict line that the gate certifies plumbing/consistency, not physics accuracy"
        }
      ],
      "corroborated_claims": [
        {
          "id": "V1-CB-REPRODUCES",
          "quote_keys": [
            "geom_cb"
          ],
          "measurements": {
            "cb": 0.820075,
            "reported_cb": 0.82007,
            "rel_diff_pct_vs_0.82": 0.00911,
            "reported_rel_diff": 8.5e-05,
            "verdict": "reported value reproduces to display precision only when an unstated rho=1.025 t/m3 conversion is inserted"
          },
          "note": "not a defect; the defect (F5) is the unstated density step"
        },
        {
          "id": "V2-GEOM-RATIOS",
          "quote_keys": [
            "geom_cb"
          ],
          "measurements": {
            "LB": 6.3333,
            "BT": 2.6087,
            "reported": {
              "LB": 6.333,
              "BT": 2.609
            },
            "verdict": "consistent"
          }
        },
        {
          "id": "V3-B2-12.4-REPRODUCES",
          "quote_keys": [
            "b2_correction",
            "b2_beta_row"
          ],
          "measurements": {
            "beta_theory": 0.2874,
            "reported_rel_diff": 0.758,
            "beta_implied_B2": 0.5052,
            "utilization_20y": 67.58,
            "utilization_after_correction": {
              "SN_slope_m=3": 12.44,
              "SN_slope_m=3.5": 9.38,
              "SN_slope_m=4": 7.08,
              "SN_slope_m=5": 4.02
            },
            "reported_after_correction": 12.4,
            "verdict": "12.4 reproduces exactly for S-N slope m=3 and beta_B2 > beta_theory; neither assumption is stated in the markdown"
          },
          "note": "reproduces exactly at S-N slope m=3"
        },
        {
          "id": "V4-D07-65.6PCT-REPRODUCES",
          "quote_keys": [
            "d07_row"
          ],
          "measurements": {
            "design_point_kn": 4.5,
            "reported_rel_divergence": 0.656,
            "implied_peer_speed_kn": 7.452,
            "verdict": "65.6% is consistent with a peer model at ~7.45 kn under the same (h,C)"
          }
        },
        {
          "id": "V5-MEAN-SPEEDS-PLAUSIBLE",
          "quote_keys": [
            "d1_route",
            "c3_totals"
          ],
          "measurements": {
            "D1_mean_kn_54.5h": 12.55,
            "C3_mean_kn_63.3h": 10.81,
            "C3_mean_kn_68.2h": 10.03
          }
        },
        {
          "id": "V6-ENERGY-SCALE-PLAUSIBLE",
          "quote_keys": [
            "c3_totals"
          ],
          "measurements": {
            "avg_power_kW": 3213.1,
            "energy_per_nm_kWh": 297.3,
            "main_engine_MW": 18.0,
            "avg_load_pct": 17.9
          }
        },
        {
          "id": "V7-A2-ASSIMILATION-GAIN",
          "quote_keys": [
            "a2_line"
          ],
          "measurements": {
            "gain_vs_ice_chart_pct": 20.71
          }
        }
      ],
      "overstated_claims": [
        "Report declares '7 项披露' but enumerates only 4 disclosure IDs",
        "⑥ omits quantities stated elsewhere (E1 GM 0.09%) and gives no baseline value for A2 skill 0.505, so the '<3%' answer set is not complete or auditable",
        "gate threshold is 8/16, and all 16 assertions are self-consistency: the only external anchors (D01, D02, D07) all fail, so 'gate PASS' must not be read as physics accuracy"
      ],
      "blocking_findings": [
        "F1-C3-TOTAL-TIME",
        "F2-DISCLOSURE-SET"
      ],
      "disposition": "needs-fix",
      "disposition_rationale": "The honesty posture is sound: 4 disclosures are stated as failing, external anchors are not dressed up, and the structural verdict is declared 不通过. The numbers I could recompute independently reproduce (Cb with rho, B2 12.4 at m=3, D07 65.6%, mean speeds, energy scale). Blocking defects are transactional rather than physical: the same quantity carries two values (C3 total time 63.3 vs 68.2 h; wall clock 50.7 vs 41.5 s), and the declared disclosure count (7) cannot be reconciled with the 4 IDs actually named. No assertion in the 16-item gate closes time/energy or reconciles D1 vs C3, so the reconstructed 11.48 kn D1 mean ice speed against the 4.50 kn design point is a coverage hole, not a proven error. Fix cost is editorial + one assertion; the physics conclusions do not need to change.",
      "verification_status": "NOT_VERIFIED_BY_REVIEWER -- verification is computed by the platform gate, not asserted here"
    }
  }
}
```