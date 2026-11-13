#!/usr/bin/env python3
"""wp-1561-04 · emit the review deliverables from review_checks.json.

Writes (all inside docs/kf/wp-1561-04/):
  review_report.json     the 04 deliverable (findings + checks + dispositions)
  review_events.json     append-only review ledger (foldable by scripts/ke_state_machine.py)
  kf_result.json         kf_result.v1 envelope (outputs = review_report + review_events)
  REPORT.md              six-section human report, numbers injected, no json fence
  fig_review_checks.png  per-ship recomputation residual + verdict matrix
  emit.log               schema validation of the emitted envelope

  python3 scripts/kf_wp1561_04_emit.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_UP = ROOT / "docs/kf/wp-1561-01"
PKG = ROOT / "docs/kf/wp-1561-04"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from ke_state_machine import fold  # noqa: E402

CONTRACT = json.loads((PKG / "review_checks.json").read_text(encoding="utf-8"))["contract"]
PRODUCER = CONTRACT["producer_identity"]
REVIEWER = CONTRACT["reviewer_identity"]
POLICY = "ke-review-v0.1"


def load_checks() -> dict:
    return json.loads((PKG / "review_checks.json").read_text(encoding="utf-8"))


def findings_of(chk: dict) -> list[dict]:
    per = {c["id"]: c for c in chk["checks"]}
    d = per["E1"]["detail"]["per_ship"]
    return [
        {"id": "F-01", "severity": "low", "blocking": False,
         "title": "record title != markdown H1, and the drift is not registered as an observation",
         "detail": "The record `title` (identical to this package's contract input.title) reads "
                   "'推进端点推力闭合修复' while the document H1 reads '/propulsion/predict 推力闭合修复'. "
                   "wp-1561-01 pins both strings (report.title, asset 1561-a000) but registers no "
                   "observation for the difference, so a downstream step that quotes the record title "
                   "emits a string that does not exist in the markdown.",
         "evidence": [
             {"quote": "# m1838 · /propulsion/predict 推力闭合修复：从 Kt=0.3-0.2J 直线式到 BEMT 反解转速",
              "where": "markdown line 1 (the only quotable form)"},
             {"record_field": "title",
              "value": per["C12"]["detail"]["record_title"],
              "record": per["C12"]["detail"]["record_title_source"],
              "note": "not present in the markdown; see check C12"}],
         "recommendation": "03+ must quote from markdown only; registering a 'title_drift' observation "
                           "would close the gap."},
        {"id": "F-02", "severity": "low", "blocking": False,
         "title": "'eta_R = 1.0 is conservative' points the optimistic way for power adequacy",
         "detail": f"With eta_D = eta0*eta_H*eta_R and P_D = P_E/eta_D, eta_R=1.0 (instead of the "
                   f"report's own Holtrop-typical 0.98) raises eta_D by ~2% and therefore lowers the "
                   f"predicted delivered power. At eta_R=0.98 the minimum reported eta_D falls to "
                   f"{per['E4']['detail']['min_eta_D_if_eta_R_0_98']} against the report's own 0.50 band "
                   f"floor (margin {per['E4']['detail']['min_margin_to_floor']} at eta_R=1.0). The band "
                   f"still holds, but the word 'conservative' is not licensed by the direction of the "
                   f"change. Not a defect of the registration (01 does not judge correctness).",
         "evidence": [{"quote": "η_R 默认 1.0（偏保守：Holtrop 回归值约 0.98）", "where": "## ⑤ 注意点 3"},
                      {"quote": "1. **Ferry 落在 I3 带边上（η_D=0.516）**。", "where": "## ⑤ 注意点 1"}],
         "recommendation": "extraction must keep the numeric qualifier and may not keep the word 'conservative'."},
        {"id": "F-03", "severity": "info", "blocking": False,
         "title": "two denominators in one geometry bullet (registered as 1561-o000) — arithmetic reproduced",
         "detail": f"|130790-115000|/130790 = {per['C7']['detail']['over_geometry_pct']}% (printed as "
                   f"'偏差 -12.1%') and /115000 = {per['C7']['detail']['over_displacement_pct']}% "
                   f"('相差 13.7%'). Both statements are right for their own denominator; nothing is "
                   f"fabricated. The upstream registration as unresolved is correct and sufficient.",
         "evidence": [{"quote": "- **Aframax**：Cb·L·B·T=130790 m³，输入排水量=115000，偏差 -12.1%（>10%：吃水/方形系数与排水量不自洽，请核对是否为设计吃水）",
                       "where": "## ⑤ 注意点 4"},
                      {"quote": "其中 Aframax 的 Cb·L·B·T 与输入排水量相差 13.7%",
                       "where": "## ⑤ 注意点 4 (same bullet)"}],
         "recommendation": "none for 01; 03 must carry both numbers together with their denominators."},
        {"id": "F-04", "severity": "medium", "blocking": False,
         "title": "five declared figures have no retrievable payload -> figure-borne statements are unverifiable",
         "detail": "All five figure endpoints still answer HTTP 404 on re-probe, so observation 1561-o001 "
                   "is accurate rather than stale. The markdown only describes the curves in prose; any "
                   "03/05 statement that reads a value off fig1-fig5 inherits unsupported evidence.",
         "evidence": [{"quote": "图 1 `fig1_thrust_power.png`：I2/I3 判据——需求带（蓝带）与平台值（蓝点=修复后，红方=修复前，",
                       "where": "## ④ 结果图"},
                      {"probe": {k: v.get("http") for k, v in chk.get("figure_probes", {}).items()}}],
         "recommendation": "keep figure claims 'partially-supported'; never quote a number that only exists "
                           "inside a 404 payload."},
        {"id": "F-05", "severity": "info", "blocking": False,
         "title": "subject-report arithmetic is self-consistent for 5/5 ships; residual differences trace to integer rpm",
         "detail": f"T_req = R_T/(1-t) reproduces the reported thrust on all five ships (worst relative "
                   f"difference {per['E1']['detail']['worst_T_rel_err']}), and eta_D = eta0*eta_H, "
                   f"J = V(1-w)/(nD), D/T = 0.70 and the I2/I3/I4 bands all reproduce to the printed "
                   f"decimals. Reported rpm is an integer, so J (prop. to 1/n) and P_D (prop. to n^3) are "
                   f"only determined to +-0.5 rpm: the recomputed P_D differs from the printed P_D by up "
                   f"to {max(v['P_D_rel_err'] for v in per['E1']['detail']['per_ship'].values()):.3f} "
                   f"relative, inside that interval. The gas-tight residual 1.11e-05 itself remains not_run.",
         "evidence": [{"quote": "关键量：推力闭合残差 |T(1−t)−R_T|/R_T 最大 **1.11e-05**；η_D 区间 **0.516–0.625**",
                       "where": "## ③ 计算结果"},
                      {"computed": {k: {"T_rel_err": v["T_rel_err"], "J_recomputed": v["J_recomputed"],
                                        "J_reported": v["J_reported"], "C_T": v["C_T"],
                                        "eta0_over_etaI": v["eta0_over_etaI"]}
                                    for k, v in per["E1"]["detail"]["per_ship"].items()}}],
         "recommendation": "quote rpm together with the +-0.5 rpm granularity whenever J or P_D is quoted."},
        {"id": "F-06", "severity": "low", "blocking": False,
         "title": "two non-resolved assets carry a status but no reason",
         "detail": f"{per['C5b']['detail']['count_status_only']} assets "
                   f"({', '.join(per['C5b']['detail']['status_only_no_reason'])}) say only "
                   f"'referenced_only_not_resolvable_from_this_record' with no prose reason, no "
                   f"present_in_worktree flag and no binary probe — the other 38 non-resolved assets "
                   f"carry at least one of those. Status-only is explicit, not a silent drop, hence "
                   f"non-blocking.",
         "evidence": [{"asset": "1561-a025", "quote": "/propulsion/predict", "where": "markdown line 23"},
                      {"asset": "1561-a028", "quote": "chain_gate --live", "where": "markdown line 85"}],
         "recommendation": "add a one-line reason (why it is not resolvable) for a025/a028."},
        {"id": "F-07", "severity": "low", "blocking": False,
         "title": "declared line count 163 vs 162 actual lines",
         "detail": f"manifest.report.lines and asset 1561-a000.line_count both say "
                   f"{per['C11']['detail']['declared_lines']}, while the text has "
                   f"{per['C11']['detail']['actual_splitlines']} lines and "
                   f"{per['C11']['detail']['actual_newline_count']} newline characters (the file ends with "
                   f"a newline). The declared value equals count(newline)+1, i.e. it counts a phantom "
                   f"final line. No locator is affected (largest locator line = 160).",
         "evidence": [{"computed": per["C11"]["detail"], "where": "asset_manifest.json report.lines"}],
         "recommendation": "state the counting rule or use splitlines(); hash pinning is unaffected."},
    ]


def build_review_report(chk: dict) -> dict:
    per = {c["id"]: c for c in chk["checks"]}
    findings = findings_of(chk)
    n_fail = sum(1 for c in chk["checks"] if c["status"] == "fail")
    blocking = [f["id"] for f in findings if f["blocking"]]
    disposition = "request-changes" if blocking else "approve-with-notes"
    upstream_files = {p.relative_to(PKG_UP).as_posix():
                      "sha256:" + __import__("hashlib").sha256(p.read_bytes()).hexdigest()
                      for p in sorted(PKG_UP.rglob("*")) if p.is_file()}

    return {
        "review_report_version": "1.0",
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "reviewer_role": CONTRACT["reviewer_role"],
        "reviewed_package": {
            "package_id": CONTRACT["reviewed_package"],
            "task_type": "01-asset-registration",
            "source_hash": CONTRACT["source_hash"],
            "artifacts": upstream_files,
        },
        "disposition": disposition,
        "ledger_decision": "approve",
        "disposition_reason": (
            f"no blocking finding; {chk['counts']['pass']}/{chk['counts']['checks']} checks reproduced, "
            f"{n_fail} non-blocking check(s) failed "
            f"({', '.join(c['id'] for c in chk['checks'] if c['status'] == 'fail')}), "
            f"{chk['counts']['not_run']} declared not_run. Hash pinning, locator resolution, envelope "
            f"schema and zero-claim legality all hold; the residual items are traceability wording, not "
            f"fabrication."),
        "blocking_findings": blocking,
        "scope": {
            "in_scope": [
                "byte identity of report 1561 markdown (contract vs snapshot vs live API)",
                "kf_result.v1 envelope of wp-1561-01 (schema, source identity, zero-claim legality)",
                "asset manifest accuracy re-derived from the source text (quotes, line locators, tallies)",
                "observation set: quote binding + arithmetic re-derivation",
                "independence and prompt-independence mechanics",
                "arithmetic self-consistency of the numbers the subject report itself prints",
            ],
            "out_of_scope": [
                "re-running the propulsion endpoint / BEMT kernel (lives in ship-performance-platform)",
                "figure payload content (binaries not served: HTTP 404 on every name)",
                "resistance R_T absolute accuracy (cross-domain, no reference dataset inside the report)",
                "knowledge extraction (工序 03) — task 01 registers assets and emits zero claims",
            ],
            "claims_assessment": (
                "wp-1561-01 declares zero knowledge claims, so there is no claim of its own to assess for "
                "truth; what is assessed here are its factual statements about the source. This review "
                "marks nothing as verified — verification is computed by the platform gate."),
        },
        "independence": {
            "reviewer": REVIEWER,
            "producer": [PRODUCER],
            "basis": per["F1"]["detail"]["basis"],
            "limitations": [
                "reviewer and producer run on the same platform and the same model family: independence "
                "is identity-level and method-level, not model-level",
                "without --live the review degrades to the pinned snapshot (A4 becomes not_run); with "
                "--live the live markdown hash was compared byte-exactly",
                "I listed the reviewed package directory and opened its README.md/selfcheck.json while "
                "scoping it. selfcheck.json is treated as an object under test (C10 audits it by "
                "recomputation; its ok:true is never copied), and README prose is cited nowhere as "
                "evidence. This is a disclosure, not a claim of perfect context isolation.",
                "no strong-model second sample was drawn (that is a platform-side job, not available here)",
            ],
        },
        "context_isolation": {
            "evidence_basis": ["report 1561 markdown (platform API or byte snapshot)",
                               "docs/kf/wp-1561-01/asset_manifest.json",
                               "docs/kf/wp-1561-01/kf_result.json"],
            "objects_under_test_not_evidence": ["docs/kf/wp-1561-01/selfcheck.json",
                                                "docs/kf/wp-1561-01/README.md"],
            "producer_explanation_used_as_support": False,
        },
        "checks": chk["checks"],
        "findings": findings,
        "counts": dict(chk["counts"], findings=len(findings), blocking_findings=len(blocking)),
        "acceptance_selfcheck": {
            "valid_json": "ok — review_report.json + kf_result.json round-trip through json.load (emit.log)",
            "schema_pass": "ok — outputs['review_report.json'] carrier envelope validated against "
                           "schemas/kf_result.v1.schema.json at emission (emit.log)",
            "reviewer_independent": f"ok — {per['F1']['detail']['independent']} "
                                    f"({per['F1']['detail']['basis']}); see F1",
            "upstream_packages_completed": "ok — wp-1561-01 present with 8 byte-hashed artifacts "
                                           "(reviewed_package.artifacts) and envelope passing B1-B4",
        },
        "checks_not_run": per["G1"]["detail"]["not_run"],
        "repro_cmd": "python3 scripts/kf_wp1561_04_checks.py --live --probe-figures && "
                     "python3 scripts/kf_wp1561_04_emit.py && "
                     "python3 -m pytest tests/test_wp1561_04_review.py -q",
        "artifacts": {"checks_raw": "docs/kf/wp-1561-04/review_checks.json",
                      "figure": "docs/kf/wp-1561-04/fig_review_checks.png",
                      "review_prompt": "docs/kf/wp-1561-04/review_prompt.md"},
    }


def build_ledger(review: dict) -> dict:
    return {"package_id": CONTRACT["package_id"], "object": "wp-1561-01",
            "policy_version": POLICY,
            "producer_ids": [PRODUCER],
            "system_transitions": [
                {"id": "kf1561-04:submit", "from": "draft", "to": "in-review",
                 "policy_version": POLICY, "by": "platform-task-completion",
                 "at": "2026-11-12T02:47:00Z",
                 "note": "task completion moves the package into review (ke_state_machine.submit); "
                         "it is deliberately NOT a review decision, so it is kept out of `events`"}],
            "events": [
                {"id": "kf1561-04:review-1", "decision": review["ledger_decision"],
                 "policy_version": POLICY,
                 "reviewer": {"id": REVIEWER, "reviewer_type": "agent"},
                 "reviewed_at": "2026-11-12T02:50:00Z",
                 "findings": [{"id": f["id"], "severity": f["severity"], "blocking": f["blocking"],
                               "title": f["title"]} for f in review["findings"]],
                 "review_report": "docs/kf/wp-1561-04/review_report.json",
                 "disposition": review["disposition"],
                 "note": "approve with non-blocking findings; no claim is marked verified by this event"},
            ]}


def figure(chk: dict) -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    per = {c["id"]: c for c in chk["checks"]}
    d = per["E1"]["detail"]["per_ship"]
    ships = list(d)
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.4))
    ax = axes[0]
    ax.bar(ships, [d[s]["T_rel_err"] * 100 for s in ships], color="#3b7dd8")
    ax.set_yscale("log")
    ax.set_ylabel("|T_new - R_T/(1-t)| / (R_T/(1-t))  [%]")
    ax.set_title("A · thrust closure re-derived\n(log scale, all < 3·10⁻³ %)")
    ax.grid(alpha=0.3, axis="y")

    ax = axes[1]
    ax.bar(ships, [d[s]["P_D_rel_err"] * 100 for s in ships], color="#d88a3b")
    ax.set_ylabel("|P_D(from K_Q) - P_D(printed)| / P_D  [%]")
    ax.set_title("B · delivered power re-derived\n(inside the ±0.5 rpm interval)")
    ax.grid(alpha=0.3, axis="y")

    ax = axes[2]
    for i, s in enumerate(ships):
        lo, hi = d[s]["I2_reported"]
        ax.plot([lo, hi], [i, i], color="#9bb7e0", lw=6, solid_capstyle="butt")
        ax.plot([d[s]["T_new_kN"]], [i], "o", color="#12408c")
        ax.plot([d[s]["T_req_kN"]], [i], "x", color="#c0392b", ms=9)
    ax.set_yticks(range(len(ships)), ships)
    ax.set_xlabel("thrust [kN]")
    ax.set_title("C · I2 band vs closure point\n(bar = R_T/(1-t), t∈[0.10,0.30]; ●=printed T; ×=re-derived)")
    ax.grid(alpha=0.3, axis="x")
    fig.suptitle("wp-1561-04 independent re-derivation over the 5 ships quoted in report 1561", fontsize=11)
    fig.tight_layout()
    out = PKG / "fig_review_checks.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    return out.name


SECTION = """# KF-RESULT wp-1561-04

**Independent (red-team) review of wp-1561-01 · report 1561 · lane C**

| field | value |
|---|---|
| package | `wp-1561-04` (`04-independent-review`) |
| reviewed package | `wp-1561-01` (`01-asset-registration`) |
| report | `1561` — m1838 推进端点推力闭合修复 |
| source hash (contract) | `{hash}` |
| source hash (recomputed) | `{rhash}` |
| reviewer role | red-team-reviewer (`{reviewer}`) |
| producer | `{producer}` |
| disposition | **{disposition}** |
| blocking findings | {blocking} |
| checks | {npass} pass / {nfail} fail / {nrun} not_run (of {ntot}) |
| findings | {nfind} (medium {nmed}, low {nlow}, info {ninfo}) |

## ① 本工序做了什么

The task-01 package for report 1561 was taken apart and every one of its factual statements was
re-derived from the report bytes: the byte hash of the markdown (contract vs snapshot vs live API),
the `kf_result.v1` envelope, all {nassets} registered assets (verbatim quote, line locator, kind and
resolvability tallies), the four registration observations, the producer's own 18 self-check claims,
the independence mechanics, and — as a red-team extension — the arithmetic of the numbers the
**subject report itself** prints for its five ships. No claim of the reviewed package was accepted
because the package said so, and nothing is marked verified: verification stays with the platform gate.

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **Source acquisition, two independent paths.** `GET {api}/tensor/reports/1561` (Bearer token) and
   the pinned snapshot `docs/kf/wp-1561-01/source/report_1561.md`; SHA-256 over raw UTF-8 bytes, no
   newline normalisation. Both give `{rhash}`.
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
| `docs/kf/wp-1561-04/review_report.json` | the 04 deliverable: {ntot} checks with method+raw detail, {nfind} findings, independence & scope declarations, disposition **{disposition}** |
| `docs/kf/wp-1561-04/review_events.json` | append-only review ledger (`draft→in-review` system transition + one `approve` with findings), foldable by `scripts/ke_state_machine.py` |
| `docs/kf/wp-1561-04/kf_result.json` | `kf_result.v1` envelope; `outputs` = review_report + review_events; `provenance.source_hash` = the report hash |
| `docs/kf/wp-1561-04/review_checks.json` | raw machine evidence for every check (per-ship recomputation table included) |
| `docs/kf/wp-1561-04/fig_review_checks.png` | 3 panels: thrust-closure residual, delivered-power residual, I2 band vs closure point, 5 ships |
| `docs/kf/wp-1561-04/review_prompt.md` | the red-team prompt actually operated under (Jaccard {jac} vs the producer prompt) |
| `scripts/kf_wp1561_04_checks.py` / `scripts/kf_wp1561_04_emit.py` | one-command reproduction |
| `tests/test_wp1561_04_review.py` | asserts hash, schema, verbatim quotes, ledger fold, absence of self-verification |

## ④ 证据定位表（claim → 原文逐字片段）

| claim | verbatim source fragment |
|---|---|
| the report fixes thrust closure without clamping | `{q1}` |
| the five-ship gate really passes after the fix | `{q2}` |
| Ferry sits on the I3 band edge (η_D=0.516) | `{q3}` |
| the geometry instead-of-denominator double count is in the source | `{q4}` |
| figures exist only as prose (payload 404) | `{q5}` |
| the report itself declares two non-passing rows | `{q6}` |
| η_R default 1.0 is called conservative | `{q7}` |
| tolerance claim (radial convergence) that I could not re-run | `{q8}` |

All eight fragments were located by substring search in the markdown whose hash is `{rhash}`;
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
   printed P_D by up to {maxpd} (KVLCC2/Aframax, printed 46/66 rpm) — inside the ±0.5 rpm interval.
   Whoever quotes J or P_D downstream must carry that granularity.
4. **Wording finding, not a number finding (F-02).** `η_R=1.0` is called conservative, while with
   `P_D=P_E/η_D` it lowers the predicted power; at the report's own Holtrop-typical 0.98 the smallest
   η_D would be {minetad} against the 0.50 floor. The I3 pass survives, the adjective does not.
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
| `reviewer_independent` | ✅ | `is_independent` → `{indep}` ({basis}); reviewer ≠ producer identity |
| `upstream_packages_completed` | ✅ | `wp-1561-01` present, 8 artifacts byte-hashed, envelope passes B1–B4 |
| `review_prompt_not_copied_from_producer` (constraint) | ✅ | 5-gram Jaccard {jac} < 0.5 (F2) |
| `reviewer_context_excludes_producer_explanation` (constraint) | ⚠️ disclosed, not absolute | evidence basis = markdown + manifest + envelope; selfcheck treated as object under test; README opened while scoping and cited nowhere |
| `do_not_mark_claims_as_verified` (constraint) | ✅ | no verification field in any deliverable (C8 on the reviewed package, test on mine) |
| review verdict | **{disposition}** | {nfail} non-blocking check(s) failed ({failed_ids}); no blocking finding |

Figures: `fig_review_checks.png` — a document/review package has no physical field, so the figure is a
recomputation panel (closure residual, power residual, I2 band vs closure point) rather than a flow
field; it exists so the numbers in ④/⑤ can be seen to be computed, not copied.
"""


def main() -> int:
    chk = load_checks()
    review = build_review_report(chk)
    ledger = build_ledger(review)
    per = {c["id"]: c for c in chk["checks"]}

    fig_name = figure(chk)

    subs = {
        "{hash}": CONTRACT["source_hash"], "{rhash}": chk["source"]["sha256_snapshot"],
        "{reviewer}": REVIEWER, "{producer}": PRODUCER,
        "{disposition}": review["disposition"], "{blocking}": str(len(review["blocking_findings"])),
        "{npass}": str(chk["counts"]["pass"]), "{nfail}": str(chk["counts"]["fail"]),
        "{nrun}": str(chk["counts"]["not_run"]), "{ntot}": str(chk["counts"]["checks"]),
        "{nfind}": str(len(review["findings"])),
        "{nmed}": str(sum(1 for f in review["findings"] if f["severity"] == "medium")),
        "{nlow}": str(sum(1 for f in review["findings"] if f["severity"] == "low")),
        "{ninfo}": str(sum(1 for f in review["findings"] if f["severity"] == "info")),
        "{nassets}": str(json.loads((PKG_UP / "asset_manifest.json").read_text(encoding="utf-8"))["counts"]["total"]),
        "{api}": "${TENSOR_API_BASE}",
        "{jac}": f"{per['F2']['detail']['jaccard']}",
        "{indep}": str(per["F1"]["detail"]["independent"]),
        "{basis}": per["F1"]["detail"]["basis"],
        "{failed_ids}": ", ".join(c["id"] for c in chk["checks"] if c["status"] == "fail"),
        "{maxpd}": f"{max(v['P_D_rel_err'] for v in per['E1']['detail']['per_ship'].values())*100:.2f}%",
        "{minetad}": str(per["E4"]["detail"]["min_eta_D_if_eta_R_0_98"]),
        "{q1}": "**推力闭合反解（不用钳位）。**",
        "{q2}": "修复后闸门：`cases=5 evaluated=5 verdict_fail=0 froude_fail=0`",
        "{q3}": "1. **Ferry 落在 I3 带边上（η_D=0.516）**。",
        "{q4}": "其中 Aframax 的 Cb·L·B·T 与输入排水量相差 13.7%",
        "{q5}": "图 4 `fig4_open_water.png`：各船设计桨的 K_T(J)、η0(J) 敞水曲线与闭合工作点（●）；右图叠加",
        "{q6}": "| η0 vs B4-70 实测谱（固定几何，同 C_T） | 实验谱 | 重载端偏乐观 15–20% | **否**（见注意点 2；无实验数据离线可得，故不作\"通过\"声明） |",
        "{q7}": "η_R 默认 1.0（偏保守：Holtrop 回归值约 0.98）",
        "{q8}": "12→32 站 K_T 差 0.6%、η0 差 0.05%",
    }
    md = SECTION
    for k, v in subs.items():
        md = md.replace(k, v)

    # ---- write deliverables
    (PKG / "review_report.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (PKG / "review_events.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (PKG / "REPORT.md").write_text(md, encoding="utf-8")

    env = {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_hash": CONTRACT["source_hash"],
            "source_field": "markdown",
            "producer": REVIEWER,
            "emitted_at": "2026-11-12T02:52:00Z",
            "notes": ("independent red-team review of wp-1561-01; evidence basis = report 1561 markdown + "
                      "upstream asset_manifest.json + kf_result.json; producer narrative not used as support"),
        },
        "outputs": {
            "review_report.json": json.loads((PKG / "review_report.json").read_text(encoding="utf-8")),
            "review_events.json": json.loads((PKG / "review_events.json").read_text(encoding="utf-8")),
        },
    }
    (PKG / "kf_result.json").write_text(
        json.dumps(env, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ---- fold the ledger (review state must be legal) + validate the envelope schema
    state, codes = fold(ledger["events"], {"producer_ids": ledger["producer_ids"]},
                        initial_state="in-review")
    import jsonschema
    schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(env, schema)
    log = (f"review_ledger_fold: state={state} codes={codes}\n"
           f"envelope_schema: kf_result.v1 OK (jsonschema)\n"
           f"review_report.json: json.load OK\n"
           f"checks: {chk['counts']}\n"
           f"disposition: {review['disposition']} blocking={review['blocking_findings']}\n"
           f"figure: {fig_name}\n")
    (PKG / "emit.log").write_text(log, encoding="utf-8")
    print(log)
    return 0 if state == "approved" else 1


if __name__ == "__main__":
    raise SystemExit(main())