# KF-RESULT wp-1561-04

**Independent (red-team) review of wp-1561-01 · report 1561 · lane C**

| field | value |
|---|---|
| package | `wp-1561-04` (`04-independent-review`) |
| reviewed package | `wp-1561-01` (`01-asset-registration`) |
| report | `1561` — m1838 推进端点推力闭合修复 |
| source hash (contract) | `sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620` |
| source hash (recomputed) | `sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620` |
| reviewer role | red-team-reviewer (`agent/m15823 (TensorKnowledge) · package wp-1561-04 · red-team-reviewer`) |
| producer | `agent/m15529 (TensorKnowledge) · package wp-1561-01` |
| disposition | **approve-with-notes** |
| blocking findings | 0 |
| checks | 26 pass / 3 fail / 1 not_run (of 30) |
| findings | 7 (medium 1, low 4, info 2) |

## ① 本工序做了什么

The task-01 package for report 1561 was taken apart and every one of its factual statements was
re-derived from the report bytes: the byte hash of the markdown (contract vs snapshot vs live API),
the `kf_result.v1` envelope, all 57 registered assets (verbatim quote, line locator, kind and
resolvability tallies), the four registration observations, the producer's own 18 self-check claims,
the independence mechanics, and — as a red-team extension — the arithmetic of the numbers the
**subject report itself** prints for its five ships. No claim of the reviewed package was accepted
because the package said so, and nothing is marked verified: verification stays with the platform gate.

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **Source acquisition, two independent paths.** `GET ${TENSOR_API_BASE}/tensor/reports/1561` (Bearer token) and
   the pinned snapshot `docs/kf/wp-1561-01/source/report_1561.md`; SHA-256 over raw UTF-8 bytes, no
   newline normalisation. Both give `sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620`.
2. **Re-derivation, not reading.** `scripts/kf_wp1561_04_checks.py` recomputes each check from the
   text and from `asset_manifest.json` / `kf_result.json`. The producer's `selfcheck.json` is loaded
   only as an **object under test** (C10): its `ok:true` is audited by recomputation, never copied, and
   README prose is cited nowhere as evidence.
3. **Locator audit** (C2/C3): exact substring test of every asset quote plus "the quote's first line
   must sit on the line the locator names" (162-line text, 57 assets).
4. **Arithmetic audit** (E1–E4): per ship, `t=0.5Cb-0.12`, `w=0.5Cb-0.05`, `T_req=R_T/(1-t)`,
   `I2=[R_T/0.9, R_T/0.7]`, `P_E=R_T·V·0.514444`, `I3=[P_E/0.78, P_E/0.50]`, `η_D=η0·η_H`,
   `J=V(1-w)/(nD)`, `I4=T(1-t)/R_T`, `C_T=T/(½ρV_a²πD²/4)`, `η_I=2/(1+√(1+C_T))`, and `P_D` rebuilt
   from `K_Q=J·K_T/(2π·η0)`. Because the report prints **integer rpm**, J (∝1/n) and P_D (∝n³) are
   tested inside the ±0.5 rpm interval instead of against a point value with an invented tolerance.
   ρ=1025 kg/m³ is my assumption; the report prints only the symbol — corroborated by reproducing its
   quoted Ferry `C_T=4.37` to 0.00.
5. **Independence mechanics** (F1/F2): `ke_state_machine.is_independent(reviewer, producer)` and
   `ke.wp_gate.prompt_similarity(producer-v1.md, review_prompt.md)` (char 5-gram Jaccard, threshold 0.5).
6. **Live figure probe** (D1): `GET /tensor/reports/1561/figures/<name>` for all five names.
7. **Own deliverables re-checked** by `tests/test_wp1561_04_review.py` (schema, verbatim quotes, ledger
   fold, no verification markers).

## ③ 产出物清单（文件 → 要点）

| file | content |
|---|---|
| `docs/kf/wp-1561-04/review_report.json` | the 04 deliverable: 30 checks with method+raw detail, 7 findings, independence & scope declarations, disposition **approve-with-notes** |
| `docs/kf/wp-1561-04/review_events.json` | append-only review ledger (`draft→in-review` system transition + one `approve` with findings), foldable by `scripts/ke_state_machine.py` |
| `docs/kf/wp-1561-04/kf_result.json` | `kf_result.v1` envelope; `outputs` = review_report + review_events; `provenance.source_hash` = the report hash |
| `docs/kf/wp-1561-04/review_checks.json` | raw machine evidence for every check (per-ship recomputation table included) |
| `docs/kf/wp-1561-04/fig_review_checks.png` | 3 panels: thrust-closure residual, delivered-power residual, I2 band vs closure point, 5 ships |
| `docs/kf/wp-1561-04/review_prompt.md` | the red-team prompt actually operated under (Jaccard 0.0945 vs the producer prompt) |
| `scripts/kf_wp1561_04_checks.py` / `scripts/kf_wp1561_04_emit.py` | one-command reproduction |
| `tests/test_wp1561_04_review.py` | asserts hash, schema, verbatim quotes, ledger fold, absence of self-verification |

## ④ 证据定位表（claim → 原文逐字片段）

| claim | verbatim source fragment |
|---|---|
| the report fixes thrust closure without clamping | `**推力闭合反解（不用钳位）。**` |
| the five-ship gate really passes after the fix | `修复后闸门：`cases=5 evaluated=5 verdict_fail=0 froude_fail=0`` |
| Ferry sits on the I3 band edge (η_D=0.516) | `1. **Ferry 落在 I3 带边上（η_D=0.516）**。` |
| the geometry instead-of-denominator double count is in the source | `其中 Aframax 的 Cb·L·B·T 与输入排水量相差 13.7%` |
| figures exist only as prose (payload 404) | `图 4 `fig4_open_water.png`：各船设计桨的 K_T(J)、η0(J) 敞水曲线与闭合工作点（●）；右图叠加` |
| the report itself declares two non-passing rows | `| η0 vs B4-70 实测谱（固定几何，同 C_T） | 实验谱 | 重载端偏乐观 15–20% | **否**（见注意点 2；无实验数据离线可得，故不作"通过"声明） |` |
| η_R default 1.0 is called conservative | `η_R 默认 1.0（偏保守：Holtrop 回归值约 0.98）` |
| tolerance claim (radial convergence) that I could not re-run | `12→32 站 K_T 差 0.6%、η0 差 0.05%` |

All eight fragments were located by substring search in the markdown whose hash is `sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620`;
`tests/test_wp1561_04_review.py::test_report_quotes_are_verbatim` re-asserts that.

## ⑤ 注意点与局限

1. **Nothing re-run in the propulsion domain.** The closure residual `1.11e-05`, the 28 pytest items,
   the 12-vs-32-station convergence and the BEMT-vs-B4-70 optimism live in
   `ship-performance-platform`, which is not checked out here. They are declared `not_run`; I never
   converted them into a pass.
2. **Figures are unverifiable.** All five figure payloads answer HTTP 404 (re-probed live), so the
   registration observation stays accurate but any curve-borne statement can only be
   `partially-supported`.
3. **Residual differences trace to integer rpm, not to errors.** Recomputed P_D differs from the
   printed P_D by up to 1.61% (KVLCC2/Aframax, printed 46/66 rpm) — inside the ±0.5 rpm interval.
   Whoever quotes J or P_D downstream must carry that granularity.
4. **Wording finding, not a number finding (F-02).** `η_R=1.0` is called conservative, while with
   `P_D=P_E/η_D` it lowers the predicted power; at the report's own Holtrop-typical 0.98 the smallest
   η_D would be 0.5057 against the 0.50 floor. The I3 pass survives, the adjective does not.
5. **Two non-resolved assets carry a status but no reason** (1561-a025, 1561-a028); the other 38
   non-resolved assets carry a prose reason or `present_in_worktree`. Non-blocking.
6. **Declared line count is 163, actual is 162** (the file ends with a newline). No locator is affected
   (largest locator line = 160).
7. **Independence is identity-level + method-level, not model-level**: producer and reviewer are the
   same model family on the same platform. Also declared: I opened the package's README/selfcheck while
   scoping; selfcheck is audited as an object under test, README is cited nowhere.
8. **I did not mark anything verified**, per the contract's `do_not_mark_claims_as_verified`.

## ⑥ 自检（逐条对照 acceptance）

| acceptance | result | how |
|---|---|---|
| `valid_json` | ✅ | both JSON deliverables round-trip through `json.load`; asserted in the test |
| `schema_pass` | ✅ | envelope validated against `schemas/kf_result.v1.schema.json` at emission (B1, emit.log) |
| `reviewer_independent` | ✅ | `is_independent` → `True` (distinct-identity); reviewer ≠ producer identity |
| `upstream_packages_completed` | ✅ | `wp-1561-01` present, 8 artifacts byte-hashed, envelope passes B1–B4 |
| `review_prompt_not_copied_from_producer` (constraint) | ✅ | 5-gram Jaccard 0.0945 < 0.5 (F2) |
| `reviewer_context_excludes_producer_explanation` (constraint) | ⚠️ disclosed, not absolute | evidence basis = markdown + manifest + envelope; selfcheck treated as object under test; README opened while scoping and cited nowhere |
| `do_not_mark_claims_as_verified` (constraint) | ✅ | no verification field in any deliverable (C8 on the reviewed package, test on mine) |
| review verdict | **approve-with-notes** | 3 non-blocking check(s) failed (C5b, C12, C11); no blocking finding |

Figures: `fig_review_checks.png` — a document/review package has no physical field, so the figure is a
recomputation panel (closure residual, power residual, I2 band vs closure point) rather than a flow
field; it exists so the numbers in ④/⑤ can be seen to be computed, not copied.
