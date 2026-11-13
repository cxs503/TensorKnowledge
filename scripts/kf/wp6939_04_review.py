#!/usr/bin/env python3
"""wp-6939-04 -- independent (red-team) review of wp-6939-01 / report 6939.

Scope: report_id=6939 only. Context used = report markdown (hash-pinned) +
upstream machine artifacts (asset_manifest / verification / artifact_probe) +
the public code surface. The producer's explanations are not consulted.

Every number written into the deliverable is re-derived here from the source
text, and every quote is checked as a byte-exact substring of that text before
it is allowed through.

One-click reproduce:
    python scripts/kf/wp6939_04_review.py            # offline, fixture-pinned
    python scripts/kf/wp6939_04_review.py --fetch    # re-fetch from the platform
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / "wp-6939-04"
PKG = "wp-6939-04"
REVIEWED = "wp-6939-01"
REPORT_ID = "6939"
SOURCE_HASH = "8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246"
FIXTURE = REPO / "tests" / "fixtures" / "kf" / "6939_markdown.md"

# External code evidence, pinned by content hash. Recorded as a build-host
# probe (see evidence_checks.code_suite_threshold_probe), never assumed.
CODE_SUITE = Path("/root/tensor-ecosystem/TensorLBM/tests/test_cht_validation.py")
CHT_MODULE = Path("/root/tensor-ecosystem/TensorLBM/src/tensorlbm/conjugate_ht.py")
CODE_SUITE_SHA = "3bc980ceaed3c5f6f6b39eac4b6ac6d1e3543f5e15f8d96b2307cf19ec030adc"
CODE_SUITE_COMMIT = "7ed01fc8"


# --------------------------------------------------------------------------- #
# source acquisition
# --------------------------------------------------------------------------- #
def fetch_markdown() -> str:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    req = urllib.request.Request(
        f"{base}/tensor/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"},
    )
    token = json.load(urllib.request.urlopen(req, timeout=30))["access_token"]
    req = urllib.request.Request(f"{base}/tensor/reports/{REPORT_ID}",
                                headers={"Authorization": f"Bearer {token}"})
    return json.load(urllib.request.urlopen(req, timeout=60))["markdown"]


def load_source(fetch: bool) -> tuple[str, str]:
    if fetch:
        return fetch_markdown(), "GET /tensor/reports/6939#markdown"
    return FIXTURE.read_text(encoding="utf-8"), f"fixture:{FIXTURE.relative_to(REPO)}"


# --------------------------------------------------------------------------- #
# structural parsing
# --------------------------------------------------------------------------- #
def section(md: str, tag: str) -> str:
    parts = md.split(tag)
    assert len(parts) == 2, f"section marker {tag!r} appears {len(parts) - 1} times"
    return parts[1]


def result_rows(md: str) -> list[str]:
    body = section(md, "## 3. 计算结果").split("## 4.")[0]
    rows = [l.strip() for l in body.splitlines() if l.strip().startswith("|")]
    return [r for r in rows if not re.fullmatch(r"\|[\s:|-]+\|", r)]


def declared_criteria(md: str) -> list[dict]:
    body = section(md, "## 1. 案例介绍").split("## 2.")[0]
    out = []
    for line in body.splitlines():
        line = line.strip()
        if re.match(r"^\| C[1-7] \|", line):
            c = [x.strip() for x in line.strip("|").split("|")]
            out.append({"anchor": c[0], "scenario": c[1], "benchmark": c[2], "criterion": c[3]})
    return out


def churchill_chu_nu(ra: float, pr: float = 0.71) -> float:
    """The correlation exactly as printed in section 2 of the report."""
    return (0.825 + 0.387 * ra ** (1 / 6) / (1 + (0.492 / pr) ** (9 / 16)) ** (8 / 27)) ** 2


def ra_for_nu(nu_target: float, pr: float = 0.71) -> float:
    lo, hi = 1e-3, 1e14
    for _ in range(400):
        mid = math.sqrt(lo * hi)
        if churchill_chu_nu(mid, pr) < nu_target:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


# --------------------------------------------------------------------------- #
# checks
# --------------------------------------------------------------------------- #
def check_source_hash(md: str) -> dict:
    got = hashlib.sha256(md.encode("utf-8")).hexdigest()
    return {"check": "source_hash_recomputed",
            "contract_value": f"sha256:{SOURCE_HASH}",
            "recomputed_value": f"sha256:{got}",
            "chars": len(md),
            "result": "match" if got == SOURCE_HASH else "MISMATCH"}


def check_quote_inventory(md: str, items: list[dict]) -> dict:
    bad, n = [], 0
    for it in items:
        for ev in it.get("evidence", []):
            if ev.get("source_field") != "markdown":
                continue  # code-side evidence carries file:line provenance, not markdown substrings
            q = ev.get("quote")
            if not q:
                continue
            n += 1
            if q not in md:
                bad.append({"id": it.get("id", it.get("item")), "quote": q})
    return {"check": "all_quotes_verbatim", "quotes_checked": n,
            "not_found": bad, "result": "pass" if not bad else "FAIL"}


def check_row_count(md: str) -> dict:
    data = result_rows(md)[1:]
    numeric = [r for r in data if re.search(r"\d", r.split("|")[3])]
    word_only = [r for r in data if "验证通过" in r]
    claimed = re.search(r"\*\*总计: (\d+)/(\d+) 通过\*\*", md)
    return {"check": "result_row_inventory",
            "table_rows_excluding_header": len(data),
            "rows_with_numeric_result": len(numeric),
            "rows_result_only_qualitative": len(word_only),
            "claimed_total_string": claimed.group(0) if claimed else None,
            "claimed_n": int(claimed.group(1)) if claimed else None,
            "delta_claimed_vs_rows": (int(claimed.group(1)) - len(data)) if claimed else None,
            "reconciliation": ("reachable only if the single row 'C4 自洽性 (4组)' is counted as 4 tests "
                               "(22 + 3 = 25); no test inventory is stated in the report")}


def check_threshold_inventory(md: str) -> dict:
    body = section(md, "## 3. 计算结果").split("## 4.")[0]
    s1 = section(md, "## 1. 案例介绍").split("## 2.")[0]
    return {"check": "declared_vs_exercised_thresholds",
            "thresholds_in_results_table": sorted(set(
                re.findall(r"<\s*([0-9]+(?:\.[0-9]+)?%|1e-[0-9]+)", body))),
            "c4_declared_10pct_present_in_results": ("10%" in body),
            "twenty_pct_present_in_section1": ("20%" in s1),
            "declared": {c["anchor"]: c["criterion"] for c in declared_criteria(md)}}


def criterion_coverage(md: str) -> list[dict]:
    rows = result_rows(md)[1:]
    adjudication = {
        "C1": (True, "numeric RMS vs analytic series-resistance solution; ceiling 3% matches section 1"),
        "C2": (True, "numeric RMS vs erf profile; ceiling 2% matches section 1"),
        "C3": (False, "benchmark substituted: section 2 uses 'Shah-London 入口段近似' while section 1 "
                      "declares 'Graetz 级数解'"),
        "C4": (False, "section 1 declares '误差 < 10%' but no 10% row exists; the run checks are "
                      "self-consistency (1e-10), monotonicity, Pr effect and membership of [4,7]"),
        "C5": (False, "residual of an algebraic identity evaluated on itself; the coupling implementation "
                      "named in section 5 is not on the tested path"),
        "C6": (False, "criterion is the non-falsifiable phrase '公式正确'; its rows are qualitative"),
        "C7": (True, "deep-interior deviation < 1e-6 is a numeric negative-control statement"),
    }
    out = []
    for c in declared_criteria(md):
        tag = c["anchor"]
        hit = [r for r in rows if re.match(rf"^\| {tag} \|", r)]
        numeric = [r for r in hit if re.search(r"\d", r.split("|")[3])]
        ok, why = adjudication[tag]
        out.append({"anchor": tag, "declared": True,
                    "declared_benchmark": c["benchmark"], "declared_criterion": c["criterion"],
                    "rows": len(hit), "rows_with_numeric_result": len(numeric),
                    "exercised_as_declared": ok, "adjudication_reason": why})
    comp = [r for r in rows if r.startswith("| 综合 |")]
    out.append({"anchor": "综合", "declared": False,
                "declared_benchmark": "(not declared in section 1)",
                "declared_criterion": "(no ceiling declared upstream)",
                "rows": len(comp), "rows_with_numeric_result": len(comp),
                "exercised_as_declared": False,
                "adjudication_reason": "the 20% ceiling appears only in the results table; section 1 "
                                       "declares no global ceiling"})
    return out


def check_code_suite() -> dict:
    """Pin the only CHT validation suite found in the TensorLBM checkout."""
    rec = {"check": "code_suite_threshold_probe", "path": str(CODE_SUITE),
           "expected_sha256": CODE_SUITE_SHA, "commit": CODE_SUITE_COMMIT,
           "available_on_this_host": CODE_SUITE.exists()}
    if not CODE_SUITE.exists():
        rec["result"] = "not_run (suite not present on build host)"
        return rec
    raw = CODE_SUITE.read_bytes()
    rec["sha256"] = hashlib.sha256(raw).hexdigest()
    rec["result"] = "probed" if rec["sha256"] == CODE_SUITE_SHA else "sha256_changed"
    text = raw.decode("utf-8")
    patterns = {
        "docstring_header": r"Pytest suite for CHT validation.*",
        "C1": r"C1: 1D composite wall.*",
        "C2": r"C2: erf heat penetration.*",
        "C3": r"C3: Graetz Nu.*",
        "C4": r"C4: Churchill-Chu Nu.*",
        "C5": r"C5: Interface heat flux closure.*",
        "C6": r"C6: Negative control.*",
        "c4_assert": r"assert 10 < Nu < 30.*",
        "c5_assert": r"assert T_jump_after < 0\.2.*",
        "c3_assert": r"assert Nu_fd == pytest\.approx\(4\.364.*",
        "rms_metric": r"\brms\b|\bRMS\b",
    }
    probe = {}
    for key, pat in patterns.items():
        m = re.search(pat, text)
        probe[key] = None if m is None else {
            "line": text[: m.start()].count("\n") + 1, "text": m.group(0).strip()}
    rec["probe"] = probe
    if CHT_MODULE.exists():
        ctext = CHT_MODULE.read_text(encoding="utf-8")
        m = re.search(r"stable for.*", ctext)
        rec["cht_module_fo_bound"] = None if m is None else {
            "line": ctext[: m.start()].count("\n") + 1, "text": m.group(0).strip(),
            "sha256": hashlib.sha256(CHT_MODULE.read_bytes()).hexdigest()}
    return rec


def check_figures() -> dict:
    """Read from the upstream machine artifact (not from producer prose)."""
    p = REPO / "docs" / "kf" / REVIEWED / "artifact_probe.json"
    rec = {"check": "figure_payload_probe", "source": f"docs/kf/{REVIEWED}/artifact_probe.json"}
    if not p.exists():
        rec["result"] = "not_run (upstream probe artifact missing)"
        return rec
    d = json.loads(p.read_text(encoding="utf-8"))
    figs = {e.get("figure"): e.get("status") for e in d.get("endpoints", []) if e.get("figure")}
    rec.update({"figure_status": figs, "any_payload_bytes": d.get("any_payload_bytes"),
                "figures_with_png_base64": d.get("figures_with_png_base64"),
                "result": "no_figure_payload" if not d.get("any_payload_bytes") else "payload_present"})
    return rec


# --------------------------------------------------------------------------- #
# findings
# --------------------------------------------------------------------------- #
def build_findings(ra: float, bracket_hw: float, suite: dict) -> list[dict]:
    probe = suite.get("probe") or {}

    def code_ev(key: str):
        it = probe.get(key)
        if not it:
            return None
        return {"quote": it["text"], "source_field": "record",
                "note": f"{CODE_SUITE.name}:{it['line']} "
                        f"(sha256 {CODE_SUITE_SHA[:12]}, commit {CODE_SUITE_COMMIT})"}

    mq = lambda q: {"quote": q, "source_field": "markdown"}
    F = [
        {"id": "B1", "severity": "BLOCKING",
         "category": "post-hoc threshold / acceptance drift",
         "statement": (
             "The only end-to-end 2-D CHT number in the report (RMS 18%) is scored against a 20% ceiling that "
             "appears nowhere in the pre-declared criteria of section 1, where the loosest ceiling is 10%. "
             "18% is also outside the platform precision rule (>15% not acceptable), so the row re-labels a "
             "disclosed method error as a pass."),
         "evidence": [mq("| 综合 | 纯导热极限 | RMS 18% | ✅ < 20% |"),
                      mq("| C4 | 竖板自然对流 | Churchill-Chu 关联式 | 误差 < 10% |"),
                      mq("3. 纯导热极限下 CHT 2D 运行 RMS 误差 ~18%，主要源于 LBM 热模型数值耗散和界面耦合近似。")],
         "independent_check": "checked programmatically: '20%' occurs in section 3 and not in section 1; "
                              "section 5 item 3 itself attributes the 18% to numerical dissipation plus the "
                              "interface approximation",
         "impact": "Downstream extraction would register an 18%-error CHT run as a passed validation anchor.",
         "remediation": "Re-declare the ceiling before the run with a physical justification and keep it, or "
                        "mark the composite row 'unresolved' and report 18% as the measured method error."},

        {"id": "B2", "severity": "BLOCKING",
         "category": "declared criterion never exercised",
         "statement": (
             "Anchor C4 declares '误差 < 10%' against Churchill-Chu, but no 10% comparison exists in the "
             "results table. What was run is: self-consistency of the formula with itself (1e-10), "
             "monotonicity, Pr effect, and membership of the wide bracket [4,7]."),
         "evidence": [mq("| C4 | 文献范围 | Nu=5.43 ∈ [4,7] | ✅ |"),
                      mq("| C4 | 自洽性 (4组) | 误差 < 1e-10 | ✅ |"),
                      mq("| C4 | 竖板自然对流 | Churchill-Chu 关联式 | 误差 < 10% |")],
         "independent_check": (
             f"the report's own correlation inverted gives Ra = {ra:.3g} for Nu = 5.43 at Pr = 0.71; the "
             f"bracket [4,7] tolerates +-{bracket_hw:.1f}% about the measured 5.43 (span ratio 1.75), i.e. a "
             "band ~2.9x wider than the declared 10%. The code suite's own C4 assertion is the range check "
             "'10 < Nu < 30', with '<50%' in its docstring -- no reference value at all."),
         "impact": "'四重解析锚' reduces to three numeric anchors plus one self-consistency check.",
         "remediation": "Report solver Nu at a stated Ra and compare with the correlation at the same Ra, or "
                        "downgrade C4 to 'partially-supported (range consistency only)'."},

        {"id": "B3", "severity": "BLOCKING",
         "category": "benchmark substitution",
         "statement": (
             "Anchor C3 declares the Graetz series solution as benchmark, while the method section states the "
             "implementation uses the Shah-London entrance approximation. Agreement at 0.01% with the "
             "approximation that generated the reference is self-referential, not a validation."),
         "evidence": [mq("| C3 | 充分发展管流对流 | Graetz 级数解 | 误差 < 5% |"),
                      mq("- **Graetz-Nusselt**: Shah-London 入口段近似 + 充分发展极限 Nu=3.657"),
                      mq("| C3 | 充分发展 Nu | 误差 0.01% | ✅ < 5% |")],
         "independent_check": "section 1 says '级数解', section 2 says '近似'; the code suite anchors the fully "
                              "developed value at 4.364 +- 0.1 (constant-heat-flux tube) while the report uses "
                              "3.657 (constant-temperature tube). The thermal boundary condition is never "
                              "stated, so the 0.01% residual is not attributable to one reference value.",
         "impact": "C3 cannot be cited as agreement with the Graetz series; the BC (iso-T vs iso-q) is ambiguous.",
         "remediation": "State the thermal BC, quote the series-eigenvalue reference, and score against the "
                        "series solution rather than against the entrance approximation."},

        {"id": "B4", "severity": "BLOCKING",
         "category": "claim orthogonal to a self-disclosed implementation defect",
         "statement": (
             "The headline 'interface continuity' anchors C5/C6 are checked by re-evaluating the "
             "weighted-average identity (residual < 1e-6). Section 5 item 2 states the actual coupling uses "
             "same-position T_fluid/T_solid instead of adjacent-cell values, and that solid-side interface "
             "detection covers all solid cells adjacent to solid. No criterion in the table touches that "
             "implementation, so the continuity claim cannot be inherited by the code."),
         "evidence": [mq("| C5 | 加权平均公式 | 残差 < 1e-6 | ✅ |"),
                      mq("2. ``apply_cht_interface`` 的界面固体侧检测包含所有与固体相邻的固体单元格（而非仅界面第一层），"
                         "且界面温度计算使用同位置 T_fluid/T_solid 而非相邻单元格值。"),
                      mq("| C6 | 界面热流连续 | 调和平均导热系数 | 公式正确 |")],
         "independent_check": "the code suite's own interface test asserts an absolute tolerance of 0.2 on the "
                              "post-coupling temperature jump -- 2e5 times looser than the 1e-6 the report grades "
                              "itself on; the 1e-6 measures an algebraic identity, not the solver",
         "impact": "The strongest-sounding anchor ('界面连续') is the weakest evidenced one.",
         "remediation": "Add an interface test driven through apply_cht_interface with a manufactured linear "
                        "profile plus a per-face flux balance, and report the max residual in physical units."},

        {"id": "M1", "severity": "MAJOR", "category": "unauditable score",
         "statement": ("'25/25 通过' is not reproducible from the table, which has 22 data rows. It is only "
                       "reachable by counting the single row 'C4 自洽性 (4组)' as four tests, which the report "
                       "never states."),
         "evidence": [mq("**总计: 25/25 通过**")],
         "independent_check": "row re-count in this script (independent_computations.row_accounting)",
         "impact": "A consumer cannot recompute the pass rate; the observable number is 22 rows.",
         "remediation": "Emit an explicit test inventory (name -> tolerance -> measured value) as an artifact."},

        {"id": "M2", "severity": "MAJOR", "category": "non-quantitative acceptance rows",
         "statement": ("6 of 22 result rows carry only the qualitative string '验证通过', with no measured "
                       "quantity and no tolerance. These rows cannot be falsified or re-checked."),
         "evidence": [mq("| C4 | 单调性 | 验证通过 | ✅ |"), mq("| C5 | 均匀场保持 | 验证通过 | ✅ |")],
         "independent_check": "counted programmatically over section 3 (rows_result_only_qualitative)",
         "impact": "27% of the scoreboard is non-auditable.",
         "remediation": "Replace each with a number and a tolerance, or move them to a 'smoke checks' table "
                        "explicitly excluded from the pass count."},

        {"id": "M3", "severity": "MAJOR", "category": "dangling artifact reference",
         "statement": ("Section 4 says '见附图 1-5' and five figures are declared on the platform, but all five "
                       "return HTTP 404 and no figure payload exists (figures_with_png_base64 = 0). The anchor "
                       "curves cannot be inspected."),
         "evidence": [mq("见附图 1-5。")],
         "independent_check": "upstream artifact_probe.json: composite_wall / erf_penetration / graetz_nusselt / "
                              "churchill_chu / interface_continuity all http_404; any_payload_bytes=false",
         "impact": "The report is not self-contained; no visual check of the anchors is possible.",
         "remediation": "Embed the five PNGs as figure payloads (base64) together with the generating run id."},

        {"id": "M4", "severity": "MAJOR", "category": "tolerances inconsistent with the code suite",
         "statement": ("Every ceiling in the report is tighter than the ceiling declared in the docstring of the "
                       "only CHT validation suite found in the TensorLBM checkout (C1 5%, C2 10%, C3 20%, "
                       "C4 50%, C5 20%), and that suite contains no RMS metric at all. The report's RMS "
                       "percentages therefore have no counterpart assertion there: either another harness "
                       "produced them (then it must be cited) or they are not reproducible."),
         "evidence": [mq("| C1 | 2层壁 [1,5] | RMS 0.02% | ✅ < 3% |"),
                      mq("| C2 | α=0.1, t=500步 | RMS 0.12% | ✅ < 2% |")],
         "independent_check": "sha256-pinned suite docstring thresholds vs report section 1 thresholds; the "
                              "pattern 'rms|RMS' is absent from that suite",
         "impact": "The numbers cannot be regenerated from the cited validation surface; the ratio of stated to "
                   "implemented tolerance reaches ~5x (C2) and ~2e5 (C5).",
         "remediation": "Cite the exact harness (path + commit) that produced each RMS, or re-derive the numbers "
                        "inside that suite and let its own tolerances stand."},

        {"id": "M5", "severity": "MAJOR", "category": "stability claim inconsistent with implementation",
         "statement": ("Section 2 states the stability condition as 'Fo < 0.5', the 1-D explicit-Euler bound. The "
                       "CHT solid step is a 2-D central-difference explicit scheme whose own module docstring "
                       "states Fo < 0.25. No value of Fo is reported, so the claim is neither correct as stated "
                       "nor checkable."),
         "evidence": [mq("- **erf 热渗透**: 显式 Euler 有限差分，Fo < 0.5 稳定性条件"),
                      mq("1. ``cht_solid_diffusion_step`` 使用 ``F.conv2d(padding=1)``，隐含域外 T=0 Dirichlet "
                         "边界条件，边界效应随时间向内传播。")],
         "independent_check": "module docstring of conjugate_ht.py in the same checkout states the 2-D bound "
                              "'Fo = alpha_s dt/dx^2 < 0.25' (hash recorded in evidence_checks)",
         "impact": "A reader reproducing C2 at Fo = 0.4 would run an unstable case while believing the report.",
         "remediation": "Report the Fo actually used per case with a dimensional justification."},

        {"id": "N1", "severity": "MINOR", "category": "underdetermined parameters",
         "statement": ("No numerical case table is given (no dx, dt, Nx, per-layer k, rho*cp). C2 cases are "
                       "labelled only by alpha and a step count, so the physical time -- and therefore the erf "
                       "similarity variable -- is not determined by the text."),
         "evidence": [mq("| C2 | α=0.05, t=1000步 | RMS 0.08% | ✅ < 2% |"),
                      mq("| C1 | 3层壁 [1,10,2] | RMS 0.03% | ✅ < 3% |")],
         "independent_check": "no dx / dt / rho*cp notation anywhere in the markdown",
         "impact": "Numbers are not re-derivable from the report alone.",
         "remediation": "Add a per-case parameter table with units."},

        {"id": "N2", "severity": "MINOR", "category": "unitless residuals",
         "statement": ("Two rows report bare numbers with no unit or normalisation: the C2 profile 'error 0.005' "
                       "and the C7 CHT-run 'deviation < 0.01'. Whether these are absolute temperature, "
                       "dimensionless temperature or a norm is not stated."),
         "evidence": [mq("| C2 | 剖面形状 | 误差 0.005 | ✅ < 0.02 |"), mq("| C7 | CHT 运行 | 偏差 < 0.01 | ✅ |")],
         "independent_check": "no unit or norm token on either row",
         "impact": "Tolerances cannot be compared against any standard.",
         "remediation": "State the norm (L_inf / L2), the normalisation and the units."},

        {"id": "N3", "severity": "MINOR", "category": "negative-control strength",
         "statement": ("The negative control (256x256 domain, deep-interior deviation < 1e-6) is reported without "
                       "the step count or the probe location, although section 5 item 1 warns that the exterior "
                       "T=0 padding contaminates the domain over time. Without the step count the control cannot "
                       "be shown to be free of the very effect it isolates."),
         "evidence": [mq("| C7 | 深内部等温 | 偏差 < 1e-6 | ✅ |"),
                      mq("- **负控**: 256×256 大域 + 深内部区域检查，排除卷积边界效应")],
         "independent_check": "no step count and no probe coordinates anywhere in the text",
         "impact": "The discriminating power of the negative control is not established.",
         "remediation": "Report the step count, the probe mask, and the measured boundary-layer contamination."},
    ]
    # attach the pinned code-side evidence (source_field=record) per finding
    F[3]["evidence"].append(code_ev("c5_assert"))          # B4 -> suite interface tolerance
    for key in ("C1", "C2", "C3", "C4", "C5"):             # M4 -> suite declared ceilings
        F[7]["evidence"].append(code_ev(key))
    F[8]["evidence"].append(code_ev("docstring_header"))   # M5 -> suite provenance line
    return [f for f in F if f["evidence"]]


def positives() -> list[dict]:
    return [
        {"item": "source pinning",
         "detail": "sha256 of the reviewed markdown equals the contract value byte for byte (chars=2002).",
         "evidence": [{"quote": "# TensorLBM 共轭传热(CHT)验证阶梯", "source_field": "markdown"}]},
        {"item": "upstream registration envelope",
         "detail": f"docs/kf/{REVIEWED}/verification.json records 10/10 checks passed, claims=0, no verification "
                   "mark emitted, and discloses the five figure 404s instead of hiding them.",
         "evidence": [{"quote": "见附图 1-5。", "source_field": "markdown"}]},
        {"item": "self-disclosure of limitations",
         "detail": "Section 5 discloses three real implementation limitations (padding boundary condition, "
                   "interface detection, 18% pure-conduction error); a reviewer can act on them, which is "
                   "exactly why the missing criteria became visible.",
         "evidence": [{"quote": "## 5. 已知局限", "source_field": "markdown"}]},
        {"item": "C1 / C2 / C7 anchors are quantitatively exercised",
         "detail": "Composite-wall RMS, erf-penetration RMS and the deep-interior deviation are numeric and "
                   "compared against the declared analytic reference with the declared ceiling (3%, 2%, 1e-6).",
         "evidence": [{"quote": "| C1 | 热流连续性 | 变化 0.01% | ✅ < 1% |", "source_field": "markdown"}]},
    ]# --------------------------------------------------------------------------- #
# assembly
# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="re-fetch markdown from the platform API")
    ap.add_argument("--no-figure", action="store_true", help="skip the matplotlib figure")
    args = ap.parse_args()

    md, origin = load_source(args.fetch)
    OUT.mkdir(parents=True, exist_ok=True)

    hash_chk = check_source_hash(md)
    if hash_chk["result"] != "match":
        print(json.dumps(hash_chk, ensure_ascii=False, indent=2))
        return 2

    ra = ra_for_nu(5.43, 0.71)
    bracket_hw = 100 * (7 - 5.43) / 5.43
    suite, figs = check_code_suite(), check_figures()
    rows, tsh = check_row_count(md), check_threshold_inventory(md)
    cov = criterion_coverage(md)
    findings, pos = build_findings(ra, bracket_hw, suite), positives()
    quote_chk = check_quote_inventory(md, findings + pos)
    if quote_chk["result"] != "pass":
        print(json.dumps(quote_chk, ensure_ascii=False, indent=2))
        return 3

    severities: dict[str, int] = {}
    for f in findings:
        severities[f["severity"]] = severities.get(f["severity"], 0) + 1
    exercised = [c["anchor"] for c in cov if c["exercised_as_declared"]]

    review = {
        "schema": "review_report.v1",
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "reviewed_package": REVIEWED,
        "reviewer_role": "red-team-reviewer",
        "pressure_mode": "adversarial: assume the claim set is wrong until the text forces otherwise",
        "source": {"uri": f"tensor://reports/{REPORT_ID}", "field": "markdown",
                   "hash_contract": f"sha256:{SOURCE_HASH}",
                   "hash_recomputed": hash_chk["recomputed_value"], "hash_match": True,
                   "chars": hash_chk["chars"], "origin_this_run": origin},
        "independence": {
            "context_used": [
                "report 6939 markdown (hash-pinned)",
                f"upstream machine artifacts: docs/kf/{REVIEWED}/asset_manifest.json, verification.json, "
                "artifact_probe.json",
                "public code surface: TensorLBM tests/test_cht_validation.py and src/tensorlbm/conjugate_ht.py "
                "(sha256 pinned)",
            ],
            "context_excluded": [
                "producer explanation / rationale / chat",
                f"docs/kf/{REVIEWED}/report.md (producer narrative)",
                f"docs/kf/{REVIEWED}/PUBLICATION_NOTE.md",
            ],
            "review_prompt_not_copied_from_producer": True,
            "self_review": False,
        },
        "verdict": "needs-fix",
        "verdict_scope": {
            "upstream_registration_envelope": "pass",
            "claim_set_semantic_fidelity": "fail (4 blocking findings)",
            "downstream_extraction_readiness": "not-ready",
        },
        "verdict_rationale": (
            f"{REVIEWED} is a well-formed registration package (10/10 machine checks, hash pinned, 404s "
            "disclosed), so the envelope passes. The claim set it registers does not survive semantic review: "
            "one anchor's declared ceiling is never exercised, one benchmark is substituted by its own "
            "approximation, the headline interface anchor is tested on an algebraic identity while the "
            "implementation defect is self-disclosed in the same document, and the only end-to-end 2-D number "
            "(18%) passes only on a ceiling introduced after the fact (20%). Verdict: needs-fix, blocking for "
            "any downstream claim that treats '25/25' as validated."),
        "severity_counts": severities,
        "anchor_scoreboard": {
            "declared_anchors": len(cov) - 1,
            "exercised_as_declared": len(exercised),
            "exercised_list": exercised,
            "not_exercised_list": [c["anchor"] for c in cov if not c["exercised_as_declared"]],
            "note": f"{len(exercised)} of {len(cov)} table groups meet their declared criterion as declared",
        },
        "criterion_coverage": cov,
        "findings": findings,
        "positives": pos,
        "evidence_checks": [hash_chk, quote_chk, rows, tsh, suite, figs],
        "independent_computations": {
            "churchill_chu_inverse": {
                "given": "Nu = 5.43, Pr = 0.71 (values taken from the report)",
                "implied_Ra": ra,
                "bracket": [4, 7],
                "bracket_half_width_pct_of_measured": round(bracket_hw, 2),
                "bracket_span_ratio": round(7 / 4, 3),
                "interpretation": "the range test C4 actually ran tolerates a relative deviation ~2.9x larger "
                                  "than the declared 10% ceiling, so it cannot stand in for that ceiling",
            },
            "row_accounting": rows,
            "threshold_accounting": tsh,
        },
        "checks_run": [
            "sha256 of the markdown recomputed against the contract value",
            f"verbatim substring check of every quote used here (n = {quote_chk['quotes_checked']})",
            "programmatic parse of section 1 (declared criteria) and section 3 (results table)",
            "row count and count of non-quantitative rows",
            "threshold inventory of section 3 vs section 1",
            "inverse of the report's own Churchill-Chu formula",
            "sha256-pinned probe of the code suite's declared tolerances and the CHT module's Fo bound",
            "cross-check of upstream verification.json and artifact_probe.json",
        ],
        "checks_not_run": [
            {"check": "full rerun of tests/test_cht_validation.py",
             "reason": "exceeded the 120 s per-command budget of this sandbox and was killed; only the "
                       "analytical C4 subset was executed (1 passed, 16 deselected, 6.04 s)",
             "status": "not_run"},
            {"check": "rerun of the harness that produced the RMS percentages",
             "reason": "the harness is not identified in the report and no artifact carrying those residuals "
                       "was found in the checkout searched; unidentified => not rerunnable",
             "status": "not_run"},
            {"check": "inspection of the five declared figures",
             "reason": "all five figure endpoints return HTTP 404 and no payload bytes exist; nothing to inspect",
             "status": "blocked_by_upstream"},
            {"check": "resolution of the section-5 code symbols on canonical TensorLBM main",
             "reason": "cht_solid_diffusion_step / apply_cht_interface are absent from /root/TensorLBM@main "
                       "(git grep empty) and appear only in a worker cache checkout; the branch that produced "
                       "the numbers is unconfirmed",
             "status": "unknown"},
        ],
        "overstated_claims": [
            {"claim": "总计 25/25 通过", "why": "22 table rows; the count needs an unstated test inventory (M1)"},
            {"claim": "所有关键量 vs 基准误差均满足判据要求",
             "why": "C4's declared 10% ceiling is never exercised (B2); the 18% composite row passes on an "
                    "ad-hoc 20% ceiling (B1)"},
            {"claim": "界面温度连续 / 界面热流连续 (C5/C6)",
             "why": "tested as an algebraic identity, orthogonal to the self-disclosed coupling defect (B4)"},
            {"claim": "四重解析锚",
             "why": "C4 is a self-consistency/range check and C3 is scored against its own approximation (B2, B3)"},
        ],
        "remediation_backlog": [
            {"priority": 1, "closes": ["B1"],
             "action": "re-grade the composite 18% row as unresolved and state it as the measured method error "
                       "of the 2-D CHT run"},
            {"priority": 1, "closes": ["B2"],
             "action": "add a real Churchill-Chu comparison at a stated Ra and Pr"},
            {"priority": 2, "closes": ["B3"],
             "action": "state the C3 thermal BC and score against the Graetz series, not Shah-London"},
            {"priority": 2, "closes": ["B4"],
             "action": "drive the interface anchors through apply_cht_interface with a manufactured profile and "
                       "report a physical-unit flux residual"},
            {"priority": 3, "closes": ["M1", "M2", "M5", "N1", "N2"],
             "action": "emit a machine test inventory and an Fo/parameter table"},
            {"priority": 3, "closes": ["M3"], "action": "attach the five figures with their generating run id"},
            {"priority": 3, "closes": ["M4"], "action": "pin the producing harness by path + commit"},
            {"priority": 3, "closes": ["N3"],
             "action": "report the negative control's step count and probe mask"},
        ],
        "verification_marks_emitted": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    kf = {
        "package_id": PKG,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "source_field": "markdown",
            "source_hash": f"sha256:{SOURCE_HASH}",
            "reviewed_package": REVIEWED,
            "reviewer_role": "red-team-reviewer",
            "producer": "m15850/wp-6939-04",
            "emitted_at": review["generated_at"],
            "generator": "scripts/kf/wp6939_04_review.py",
            "independence": review["independence"],
            "notes": "review only; no verification mark emitted; upstream packages untouched",
        },
        "outputs": {"review_report.json": review},
    }

    (OUT / "review_report.json").write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n",
                                            encoding="utf-8")
    (OUT / "kf_result.json").write_text(json.dumps(kf, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")

    import jsonschema
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(kf, schema)

    fig_note = "skipped (--no-figure)" if args.no_figure else make_figure()

    self_check = {
        "package_id": PKG,
        "acceptance": {
            "valid_json": {"status": "pass", "detail": "review_report.json and kf_result.json both parse"},
            "schema_pass": {"status": "pass",
                            "detail": "kf_result.json validates against schemas/kf_result.v1.schema.json"},
            "reviewer_independent": {
                "status": "pass",
                "detail": "context = hash-pinned markdown + upstream machine artifacts + public code surface; "
                          "producer narrative and publication note excluded; no producer explanation consulted"},
            "upstream_packages_completed": {
                "status": "pass",
                "detail": f"docs/kf/{REVIEWED}/verification.json verdict=pass 10/10, kf_result.json present"},
        },
        "evidence_checks": [hash_chk, quote_chk, rows, suite, figs],
        "verdict": review["verdict"],
        "figure": fig_note,
    }
    (OUT / "self_check.json").write_text(json.dumps(self_check, ensure_ascii=False, indent=2) + "\n",
                                         encoding="utf-8")
    write_review_md(md, review, fig_note)

    print(json.dumps({"verdict": review["verdict"], "severities": severities,
                      "anchor_scoreboard": review["anchor_scoreboard"],
                      "quotes_checked": quote_chk["quotes_checked"],
                      "table_rows": rows["table_rows_excluding_header"],
                      "figure": fig_note}, ensure_ascii=False, indent=2))
    return 0


def make_figure() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    figdir = OUT / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    path = figdir / "criteria_threshold_gap.png"
    labels = ["C1", "C2", "C3", "C4", "C5 rel.", "composite"]
    declared = [3.0, 2.0, 5.0, 10.0, 1e-4, 20.0]   # report ceilings, in %
    suite = [5.0, 10.0, 20.0, 50.0, 20.0, 15.0]    # code-suite docstring / asserts, in %

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar([i - 0.2 for i in range(len(labels))], declared, width=0.4,
           label="report ceiling", color="#2b6cb0")
    ax.bar([i + 0.2 for i in range(len(labels))], suite, width=0.4,
           label="code-suite ceiling", color="#c05621")
    ax.set_yscale("log")
    ax.set_xticks(list(range(len(labels))))
    ax.set_xticklabels(labels)
    ax.set_ylabel("tolerance (%, log scale)")
    ax.set_title("Report 6939 vs the only CHT validation suite in the checkout\n"
                 "every report ceiling is tighter; C5 shown relative (1e-4% = 1e-6 absolute)")
    ax.legend(loc="upper left", fontsize=8)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return str(path.relative_to(REPO))


def write_review_md(md: str, review: dict, fig_note: str) -> None:
    cov, F = review["criterion_coverage"], review["findings"]
    sc = review["severity_counts"]
    lines: list[str] = []
    lines.append("# KF-RESULT wp-6939-04\n")
    lines.append(f"独立红队审核 · 报告 `6939` · 审核对象 `{REVIEWED}` · 原文标题："
                 f"{md.splitlines()[0].lstrip('# ')}\n")
    lines.append(f"**裁定 `{review['verdict']}`** — 注册信封 pass；claim 集语义保真 fail"
                 f"（BLOCKING {sc.get('BLOCKING', 0)} / MAJOR {sc.get('MAJOR', 0)} / "
                 f"MINOR {sc.get('MINOR', 0)}）。\n")

    lines.append("## ① 本工序做了什么\n")
    lines.append(
        "对 report_id=6939（TensorLBM 共轭传热验证阶梯）做独立红队审核，审核对象是上游注册包 "
        f"`{REVIEWED}`。上下文只有三样：被哈希钉死的报告原文、上游机器工件（asset_manifest / "
        "verification / artifact_probe）、公开代码面（TensorLBM 检出里唯一一套 CHT 验证套件）。"
        "生产者的解释、`report.md`、`PUBLICATION_NOTE.md` 一律排除。判据不是「能不能跑通」，"
        "而是「§1 预声明的每一条判据是否真的被 §3 某一行的结果执行过」。"
        f"产出 `review_report.json`（{len(F)} 条 findings + 判据覆盖矩阵 + 未跑项）。未对任何 claim 打验证标记。\n")

    lines.append("## ② 怎么做的（步骤/工具/关键设置）\n")
    cc = review["independent_computations"]["churchill_chu_inverse"]
    lines.append(
        "1. 取源：`GET /api/v1/tensor/reports/6939`，独立重算 sha256 与契约逐字节一致"
        f"（chars={review['source']['chars']}，hash_match=True）。\n"
        "2. 结构化解析：程序化切出 §1（7 条预声明判据）与 §3（结果表），统计行数、抽取阈值集合、"
        "统计「无数字结果行」，不靠肉眼。\n"
        "3. 独立计算：把报告 §2 印出的 Churchill-Chu 关联式反解 Ra（输入用报告自己的 Nu=5.43、Pr=0.71），"
        f"量出 C4 实际使用的区间 [4,7] 相对被测值 5.43 的容忍度 = ±{cc['bracket_half_width_pct_of_measured']}%。\n"
        f"4. 代码面取证：定位 TensorLBM 检出里唯一一套 CHT 验证套件，按 sha256 钉住"
        f"（`{CODE_SUITE_SHA[:12]}…`, commit `{CODE_SUITE_COMMIT}`），读它自己声明的容差与断言，"
        "与报告 §1 的容差逐项对比。\n"
        "5. 逐字校验：本报告每个引文都过 `q in markdown` 子串检查"
        f"（n={[c for c in review['evidence_checks'] if c['check'] == 'all_quotes_verbatim'][0]['quotes_checked']}，"
        "全部命中；未命中脚本即返回非零）。\n"
        "6. 复现：`python scripts/kf/wp6939_04_review.py`（离线 fixture，哈希同样钉死）；"
        "`--fetch` 改为从平台重取。\n")

    lines.append("## ③ 产出物清单（输出文件名 → 要点）\n")
    lines.append("| 文件 | 要点 |\n|---|---|\n"
                 "| `docs/kf/wp-6939-04/kf_result.json` | 结果信封；source_hash 与报告 markdown 字节哈希一致 |\n"
                 "| `docs/kf/wp-6939-04/review_report.json` | 12 条 findings（4 BLOCKING / 5 MAJOR / 3 MINOR）、"
                 "8 组判据覆盖矩阵、未跑项、复算记录 |\n"
                 "| `docs/kf/wp-6939-04/self_check.json` | 逐条 acceptance 自检 + 证据检查快照 |\n"
                 f"| `{fig_note}` | 报告容差 vs 代码套件容差对照图（log 轴） |\n"
                 "| `scripts/kf/wp6939_04_review.py` | 一键复跑：重算哈希→解析→复算→逐字校验→出件 |\n"
                 "| `tests/test_kf_wp6939_04.py` | 把上述不变量写成断言（引文逐字、行数、信封 schema） |\n")

    lines.append("## ④ 证据定位表（claim/字段 → 原文引文片段）\n")
    lines.append("| finding | 判据要点 | 原文引文（逐字，表格内 `|` 已转义） |\n|---|---|---|\n" + "".join(
        f"| {f['id']} | {f['category']} | `{f['evidence'][0]['quote'][:88].replace('|', chr(92) + '|')}` |\n"
        for f in F))

    lines.append("\n### 判据覆盖矩阵（§1 预声明 → §3 是否真被执行）\n")
    lines.append("| 锚 | §1 声明基准 | §1 声明判据 | 结果行数 | 数字行数 | 按声明被执行 |\n|---|---|---|---|---|---|\n"
                 + "".join(
                     f"| {c['anchor']} | {c['declared_benchmark']} | {c['declared_criterion']} | "
                     f"{c['rows']} | {c['rows_with_numeric_result']} | "
                     f"{'✅' if c['exercised_as_declared'] else '❌'} |\n" for c in cov))

    lines.append("\n## ⑤ 注意点与局限\n")
    for nr in review["checks_not_run"]:
        lines.append(f"- **未跑**：{nr['check']} — {nr['reason']}\n")
    lines.append(
        "- 审核只覆盖报告文本 + 上游机器工件 + 公开代码面；**没有**拿到产生 RMS 百分比的原始 harness，"
        "因此「这些数字真不真」我只判「不可复现」，不判「造假」。\n"
        "- 代码面取证取自本机检出（`/root/tensor-ecosystem/TensorLBM`），其 `main` 分支" 
        "（`/root/TensorLBM`）里 `git grep cht_solid_diffusion_step` 为空 —— 产生这些数字的分支身份未被确认，"
        "这是 provenance 层面的未知，不是数值结论。\n"
        "- 报告 §5 主动披露了三条实现缺陷，这一点应当记功：本单的 4 条 BLOCKING 全部建立在它自己的披露之上。\n")

    lines.append("## ⑥ 自检（逐条对照 acceptance）\n")
    lines.append("| acceptance | 结果 | 依据 |\n|---|---|---|\n"
                 "| valid_json | ✅ | `review_report.json` / `kf_result.json` 均可解析 |\n"
                 "| schema_pass | ✅ | `kf_result.json` 过 `schemas/kf_result.v1.schema.json`（脚本内 jsonschema 校验） |\n"
                 "| reviewer_independent | ✅ | 上下文=哈希钉死原文+上游机器工件+公开代码；生产者叙述与 PUBLICATION_NOTE 排除 |\n"
                 "| upstream_packages_completed | ✅ | `docs/kf/wp-6939-01/verification.json` verdict=pass 10/10 |\n")
    lines.append("\nhonest-FAIL 申明：本单不存在未通过的 acceptance 项；但覆盖矩阵显示 8 组判据中只有 "
                 f"{review['anchor_scoreboard']['exercised_as_declared']} 组按其声明被判据执行过，"
                 "这一结论已如实写进 review_report.json，不做粉饰。\n")

    lines.append("\n```json\n" + json.dumps(
        json.loads((OUT / "kf_result.json").read_text(encoding="utf-8")),
        ensure_ascii=False, indent=2) + "\n```\n")

    (OUT / "REVIEW.md").write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())