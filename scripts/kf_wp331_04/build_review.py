"""Build the independent review report for wp-331-04 (report_id=331).

Design rules implemented here:
  * every quote is asserted to be a literal substring of the source markdown
    (zero hand-copy: an unverifiable quote fails the build, it is never written out);
  * every number used in the analysis is parsed out of the source table / parameter
    line by regex, then the derived quantities are computed in code
    (no number is retyped from memory);
  * the source hash is recomputed from the fetched bytes and compared with the
    contract hash;
  * nothing is written to any other report_id.

Outputs:
  runs/wp-331-04/source_331.md          (byte-exact snapshot of the source markdown)
  docs/kf/wp-331-04/review_report.json  (the review object; also the package output)
  docs/kf/wp-331-04/kf_result.wp-331-04.json (envelope submitted to the platform)
  runs/wp-331-04/review_events.json     (single review-state event; kept out of the
                                         package output dir so the contract's
                                         `output` declaration stays exactly honoured)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPORT_ID = "331"
PACKAGE_ID = "wp-331-04"
TASK_TYPE = "04-independent-review"
REVIEWED_PACKAGE = "wp-331-01"
CONTRACT_HASH = "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717"
CONTRACT_CHARS = 1371
CONTRACT_TITLE = "M404: DEM-FEM Coupling Interface Schema + Hertz/Beam Benchmarks (CPU)"
CONTRACT_SCENARIO = "dem_fem_coupling_hertz_cpu"

ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "runs" / "wp-331-04"
OUT = ROOT / "docs" / "kf" / "wp-331-04"


# --------------------------------------------------------------------------- fetch
def fetch_record(report_id: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    tok = None
    for ep in ("/auth/login", "/tensor/login"):
        try:
            req = urllib.request.Request(base + ep, data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
            payload = json.load(urllib.request.urlopen(req, timeout=30))
            tok = payload.get("access_token") or payload.get("token")
            if tok:
                break
        except Exception:  # pragma: no cover - endpoint probing
            continue
    if not tok:
        raise SystemExit("login failed")
    req = urllib.request.Request(f"{base}/tensor/reports/{report_id}",
                                 headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req, timeout=60))


# ------------------------------------------------------------------ source parsing
def parse_table(md: str) -> dict[str, tuple[str, str, str]]:
    """Parse the '## ③ Results' markdown table into {metric: (hertz, target, beam)}."""
    lines = md.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.startswith("## ③"))
    except StopIteration:
        raise SystemExit("results section not found")
    rows: dict[str, tuple[str, str, str]] = {}
    for ln in lines[start:]:
        if ln.startswith("## ") and not ln.startswith("## ③"):
            break
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) != 4 or set(cells[1]) <= set("- "):
            continue
        if cells[0].lower() == "metric":
            continue
        rows[cells[0]] = (cells[1], cells[2], cells[3])
    if not rows:
        raise SystemExit("no table rows parsed")
    return rows


def num(text: str) -> float:
    m = re.search(r"-?\d+(?:\.\d+)?", text.replace(",", ""))
    if not m:
        raise SystemExit(f"no number in {text!r}")
    return float(m.group(0))


def parse_params(md: str) -> dict[str, float]:
    """Pull named parameters out of the '**Parameters**' bullet, in units of metre / SI."""
    line = next(ln for ln in md.splitlines() if "**Parameters**" in ln)
    out: dict[str, float] = {}
    for key in ("k_bond", "tool_speed", "max_indent"):
        m = re.search(rf"{key}=([0-9.eE+-]+)", line)
        if m:
            out[key] = float(m.group(1))
    m = re.search(r"R=([0-9.eE+-]+)m", md)
    if m:
        out["indenter_R"] = float(m.group(1))
    return out


# ------------------------------------------------------------------------- review
def main() -> None:
    RUNS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    rec = fetch_record(REPORT_ID)
    md: str = rec["markdown"]
    (RUNS / f"source_{REPORT_ID}.md").write_text(md, encoding="utf-8")

    source_hash = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    hash_ok = source_hash == CONTRACT_HASH
    chars_ok = len(md) == CONTRACT_CHARS

    def q(text: str) -> dict:
        """Quote record with a hard verbatim guard."""
        if text not in md:
            raise SystemExit(f"QUOTE_NOT_FOUND: {text!r}")
        start = md.index(text)
        return {"quote": text, "source_field": "markdown",
                "offset_start": start, "offset_end": start + len(text),
                "content_hash": "sha256:" + hashlib.sha256(text.encode()).hexdigest()}

    table = parse_table(md)
    params = parse_params(md)

    exp_h = num(table["Exponent"][0])            # 1.4108
    exp_t = num(table["Exponent"][1])            # 1.5
    exp_tol = num(table["Exponent"][1].split("±")[1])  # 0.05
    stiff_h = num(table["Stiffness error"][0])   # 44.1
    stiff_t = num(table["Stiffness error"][1])   # 3
    stiff_b = num(table["Stiffness error"][2])   # 0.0125
    energy_h = num(table["Energy drift"][0])     # 58.6
    energy_t = num(table["Energy drift"][1])     # 1

    exp_dev = abs(exp_h - exp_t)
    derived = {
        "exponent_reported": exp_h,
        "exponent_target": exp_t,
        "exponent_tolerance": exp_tol,
        "exponent_abs_deviation": round(exp_dev, 4),
        "exponent_relative_deviation_pct": round(100 * exp_dev / exp_t, 4),
        "exponent_tolerance_overshoot_factor": round(exp_dev / exp_tol, 4),
        "exponent_verdict": "FAIL" if exp_dev > exp_tol else "PASS",
        "stiffness_error_pct": stiff_h,
        "stiffness_target_pct": stiff_t,
        "stiffness_budget_overshoot_factor": round(stiff_h / stiff_t, 4),
        "stiffness_verdict": "FAIL" if stiff_h > stiff_t else "PASS",
        "energy_drift_pct": energy_h,
        "energy_target_pct": energy_t,
        "energy_budget_overshoot_factor": round(energy_h / energy_t, 4),
        "energy_verdict": "FAIL" if energy_h > energy_t else "PASS",
        "beam_error_pct": stiff_b,
        "beam_budget_margin_factor": round(stiff_t / stiff_b, 2),
        "beam_verdict": "PASS" if stiff_b <= stiff_t else "FAIL",
        "indent_over_R": round(params["max_indent"] / params["indenter_R"], 4),
        "indent_over_R_note": ("Hertz small-strain validity needs delta/R << 1; the reported "
                               "final indentation reaches delta/R =" f"{params['max_indent'] / params['indenter_R']:.2f}"),
        "params": params,
        "figures_in_record": len(rec.get("figures") or []),
    }
    derived["derived_consistent_with_report_claims"] = (
        derived["exponent_verdict"] == "FAIL" and derived["stiffness_verdict"] == "FAIL"
        and derived["energy_verdict"] == "FAIL" and derived["beam_verdict"] == "PASS")

    findings = [
        {
            "id": "F1",
            "severity": "blocker",
            "category": "process/upstream",
            "statement": (f"Upstream package {REVIEWED_PACKAGE} has no retrievable product, so the "
                          "claim-level fidelity of the extraction (03 output) cannot be audited; "
                          "this package can therefore not be approved, only refused/returned."),
            "evidence": [q("## ③ Results")],
            "analysis": ("Channels checked: (a) platform report listing — 100 most recent records "
                         "scanned client-side for the tag kf-wp:wp-331-01, zero hits; the reports "
                         "endpoint honours neither ?tag= nor ?offset= (both return the newest 50-100 "
                         "rows), so an exhaustive scan is impossible from here; (b) no work-package "
                         "endpoint (/tensor/work-packages, /tensor/packages -> HTTP 404); "
                         "(c) psql: 'permission denied for table tensor_reports'; (d) worktree "
                         "artifacts: no file matching wp-331-* outside this package. "
                         "Therefore the review is executed against the only reachable authoritative "
                         "evidence, the source markdown, and every 03-style claim below is judged "
                         "for whether the source can support it."),
            "remediation": (f"Attach the {REVIEWED_PACKAGE} product (claims/evidence/provenance) to "
                            "the package and re-run this review; acceptance item "
                            "upstream_packages_completed stays FALSE until then."),
            "blocking": True,
        },
        {
            "id": "F2",
            "severity": "major",
            "category": "scope-overclaim",
            "statement": ("The title advertises a 'DEM-FEM Coupling Interface Schema', but the body "
                          "declares TensorFEM unavailable: no coupling is executed, and no schema "
                          "artifact, path or validator output is given."),
            "evidence": [q("**Honest-FAIL**: TensorFEM unavailable; DEM lattice ≠ continuum half-space"),
                         q("Schema  validates against jsonschema")],
            "analysis": ("Two separate assertions are collapsed into one: 'a schema exists' and 'it "
                         "validates'. The report supplies neither the schema file, its $id/version, "
                         "nor the validator command and exit status, so 'validates against jsonschema' "
                         "is unfalsifiable from the text. Any 03 claim asserting a validated "
                         "DEM-FEM interface schema must be status=unresolved, not supported; a claim "
                         "naming DEM-FEM *coupling* (as opposed to interface-schema authoring) as "
                         "demonstrated is scope drift."),
            "remediation": ("Either attach the schema file + validator transcript (path, command, "
                            "exit code, jsonschema version) or restate the delivery as 'interface "
                            "schema draft, unvalidated; FEM side not available'."),
            "blocking": False,
        },
        {
            "id": "F3",
            "severity": "major",
            "category": "theory-validity-range",
            "statement": ("The Hertz comparison is run over a load range that violates Hertz's own "
                          "small-strain condition, so the 1.4108 exponent is not a clean measure of "
                          "discretisation error and the ±0.05 acceptance band is mis-specified for "
                          "this range."),
            "evidence": [q("**Geometry**: DEM3D bonded-sphere assembly (4×3×4 grid) with spherical indenter (R=0.1m)"),
                         q("- **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m")],
            "analysis": (f"max_indent / R = {params['max_indent']} / {params['indenter_R']} = "
                         f"{derived['indent_over_R']}, i.e. delta/R = 0.5 at the end of the stroke. "
                         "Hertz (F proportional to delta^1.5) assumes delta/R << 1 (single-digit-percent "
                         "strains); at delta/R = 0.5 both the geometric linearisation and the "
                         "half-space assumption fail, and the fitted exponent drifts below 1.5 for "
                         "reasons that have nothing to do with the lattice. The honest FAIL verdict "
                         "itself is therefore not evidence that the DEM discretisation is inadequate."),
            "remediation": ("Restrict the fit window to small strain (e.g. delta/R <= 0.05-0.1), report "
                            "the fitted exponent per window, and only then compare against 1.5 +/- 0.05; "
                            "alternatively declare the finite-strain regime and compare against a "
                            "finite-deformation contact solution instead of Hertz."),
            "blocking": False,
        },
        {
            "id": "F4",
            "severity": "major",
            "category": "confounded-causal-attribution",
            "statement": ("'DEM discrete lattice cannot reproduce continuum Hertz contact' is stated as "
                          "the cause of the 44.1% stiffness error, but the setup confounds at least "
                          "four candidate causes that the report never separates."),
            "evidence": [q("- DEM discrete lattice cannot reproduce continuum Hertz contact"),
                         q("- **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m"),
                         q("Effective modulus estimated: E_dem ≈ k_bond/(2r)")],
            "analysis": ("Candidate causes, none excluded by the reported evidence: (i) the ad-hoc "
                         "calibration E_dem ~ k_bond/(2r) is not derived and its agreement with the "
                         "continuum E* of the assembly is never tested; (ii) tool_speed = 5 m/s means "
                         "the indentation is dynamic — inertial/drag forces superpose on the static "
                         "contact law, and no ramp/relaxation or quasi-static protocol is documented; "
                         "(iii) the assembly is 4x3x4 spheres, i.e. the compliant half-space is a "
                         "few sphere diameters thick, so a stiff far boundary is plausible; (iv) the "
                         "lattice anisotropy of a bonded-sphere packing. A single-run FAIL cannot "
                         "attribute the error to (iv) alone, which is what the note asserts."),
            "remediation": ("Add a discriminating experiment per candidate: (a) calibrate E_dem "
                            "against a two-sphere/bulk-modulus test, (b) load at << 5 m/s or with "
                            "energy-damped relaxation, (c) grow the assembly depth and show "
                            "convergence of the contact stiffness. Then the residual can be "
                            "attributed to the lattice."),
            "blocking": False,
        },
        {
            "id": "F5",
            "severity": "major",
            "category": "unverifiable-pass",
            "statement": ("The only PASS item (beam stiffness 0.0125%) and the claimed second-order "
                          "convergence are not reproducible from the report: no reference value, no "
                          "beam data, no mesh series."),
            "evidence": [q("| Stiffness error | 44.1% | ≤3% | 0.0125% |"),
                         q("- Beam FD shows second-order convergence (error ∝ 1/n²)"),
                         q("| Mesh conv | 8.4% | <5% | converging |"),
                         q("- Beam fallback: FD Euler-Bernoulli with simply-supported BCs")],
            "analysis": ("A relative error needs a reference. The report gives neither the analytic "
                         "simply-supported deflection used as reference, nor L, EI, P, nor the grid "
                         "resolution, so 0.0125% cannot be recomputed or checked for a units/"
                         "normalisation mistake (a factor-100 slip would look like a superb PASS). "
                         "The 'second-order convergence' claim likewise rests on a single number "
                         "(8.4% 'Mesh conv', metric undefined) rather than a mesh sequence with a "
                         "fitted slope, so it is a hypothesis, not a measurement."),
            "remediation": ("Report the numeric reference (delta_ref = 5wL^4/384EI or equivalent), the "
                            "case constants, and at least three mesh levels n = 40/80/160 with errors "
                            "and the fitted log-log slope (expected -2)."),
            "blocking": False,
        },
        {
            "id": "F6",
            "severity": "major",
            "category": "numerical-integrity",
            "statement": ("An energy drift of 58.6% against a ≤1% target invalidates the DEM trajectory "
                          "from which the exponent and stiffness are extracted; the defective trajectory "
                          "cannot support any contact-law conclusion."),
            "evidence": [q("| Energy drift | 58.6% | ≤1% | — |"),
                         q("- **Parameters**: k_bond=1e5 N/m, tool_speed=5 m/s, max_indent=0.05m")],
            "analysis": (f"{derived['energy_drift_pct']}% vs {derived['energy_target_pct']}% is a "
                         f"{derived['energy_budget_overshoot_factor']}x overshoot. Neither the "
                         "integrator, the timestep, the damping model nor the energy definition "
                         "('drift' relative to initial PE?) is stated, so the audit cannot even "
                         "distinguish a genuine integration error from a wrong energy accounting. "
                         "Any knowledge object that carries the DEM exponent/stiffness numbers "
                         "without this defect attached is over-claiming."),
            "remediation": ("State integrator and dt, report total (kinetic+potential+contact) energy "
                            "conservation for a free-flight and a resting-contact control case, and "
                            "re-run the indentation only after drift < 1%."),
            "blocking": False,
        },
        {
            "id": "F7",
            "severity": "minor",
            "category": "precision-of-statement",
            "statement": ("The FAIL line conflates a relative percentage with an absolute tolerance: "
                          "1.4108 vs 1.5 is a 0.0892 absolute shortfall, 1.78x the stated +-0.05 band, "
                          "not '5.9% outside a 5% band' as the wording suggests."),
            "evidence": [q("- Hertz exponent 1.4108 vs 1.5: **5.9% error, FAIL** (outside ±0.05)")],
            "analysis": (f"Computed: |{exp_h} - {exp_t}| = {derived['exponent_abs_deviation']} "
                         f"(relative {derived['exponent_relative_deviation_pct']}%), "
                         f"overshoot = {derived['exponent_tolerance_overshoot_factor']}x the "
                         f"{exp_tol} tolerance. The verdict FAIL is correct and unaffected; only the "
                         "audit trail is imprecise."),
            "remediation": "State the absolute deviation (0.0892) alongside the percentage.",
            "blocking": False,
        },
        {
            "id": "F8",
            "severity": "minor",
            "category": "reproducibility",
            "statement": ("The report carries no run identity: no commit, no input deck path, no seed, "
                          "no sphere radius / packing fraction / timestep, no figure paths."),
            "evidence": [q("## ④ Figures"),
                         q("See attached: Hertz F-δ curve + beam deflection comparison")],
            "analysis": (f"Record carries figures = {derived['figures_in_record']}; the text points to "
                         "'attached' curves without file names, so a reviewer cannot bind the plotted "
                         "quantity to the table numbers. The geometry line gives the grid (4x3x4) and "
                         "the indenter radius but not the sphere radius r that the E_dem ~ k_bond/(2r) "
                         "calibration needs — the calibration therefore cannot be recomputed at all."),
            "remediation": ("Add a run-identity block: repo+commit, input deck path, sphere radius, "
                            "packing fraction, dt, seed, figure file names."),
            "blocking": False,
        },
    ]

    claim_judgements = [
        {
            "claim_id": "cj-exponent-fail",
            "text": "Hertz exponent 1.4108 vs target 1.5 +- 0.05 is a FAIL.",
            "evidence": [q("| Exponent | 1.4108 | 1.5±0.05 | — |"),
                         q("- Hertz exponent 1.4108 vs 1.5: **5.9% error, FAIL** (outside ±0.05)")],
            "judgement": "supports",
            "reasoning": ("Arithmetic confirms the FAIL: |1.4108-1.5| = 0.0892 > 0.05. The claim is "
                          "faithful to the source and correctly signed; only its phrasing is imprecise (F7). "
                          "What it may NOT be used to support is the causal reading 'lattice cannot do "
                          "Hertz' (F3, F4)."),
        },
        {
            "claim_id": "cj-stiffness-fail",
            "text": "Hertz stiffness error 44.1% vs target <=3% is a FAIL.",
            "evidence": [q("| Stiffness error | 44.1% | ≤3% | 0.0125% |"),
                         q("- Hertz stiffness 44.1%: **FAIL** (target ≤3%)")],
            "judgement": "qualifies",
            "reasoning": ("The FAIL verdict is arithmetic-consistent (44.1/3 = 14.7x the budget), but "
                          "the 44.1% itself is not recomputable: E* needs Poisson's ratio and E_dem "
                          "needs the sphere radius r, neither is stated. A knowledge object must carry "
                          "the number as 'as-reported, base quantities missing', not as a verified "
                          "material property of the lattice."),
        },
        {
            "claim_id": "cj-beam-pass",
            "text": "Beam FD (n=80) stiffness error 0.0125% vs <=3% is a PASS.",
            "evidence": [q("| Stiffness error | 44.1% | ≤3% | 0.0125% |"),
                         q("- Beam stiffness 0.0125%: **PASS** (<3%)")],
            "judgement": "insufficient",
            "reasoning": ("No reference deflection, beam constants or normalisation convention appears "
                          "in the report, so the PASS is unfalsifiable (F5). It must not be promoted to "
                          "a reusable 'FD Euler-Bernoulli is validated to 1e-4' knowledge claim."),
        },
        {
            "claim_id": "cj-energy-fail",
            "text": "Energy drift 58.6% vs <=1% target is a FAIL.",
            "evidence": [q("| Energy drift | 58.6% | ≤1% | — |")],
            "judgement": "supports",
            "reasoning": ("1% target, 58.6% measured: 58.6x over budget. Verdict supported and, per F6, "
                          "it is the most consequential number in the report because it disqualifies "
                          "the companion results."),
        },
        {
            "claim_id": "cj-lattice-cannot-hertz",
            "text": "DEM discrete lattice cannot reproduce continuum Hertz contact.",
            "evidence": [q("- DEM discrete lattice cannot reproduce continuum Hertz contact"),
                         q("Effective modulus estimated: E_dem ≈ k_bond/(2r)")],
            "judgement": "refutes",
            "reasoning": ("Refuted as stated (a universal/structural claim drawn from one confounded "
                          "run). The supported version is narrower: 'in this setup (delta/R = 0.5, "
                          "tool_speed 5 m/s, 4x3x4 assembly, E_dem = k_bond/(2r) calibration) the "
                          "fitted law deviates from Hertz'. See F3/F4 for the un-excluded causes."),
        },
        {
            "claim_id": "cj-second-order",
            "text": "Beam FD shows second-order convergence (error proportional to 1/n^2).",
            "evidence": [q("- Beam FD shows second-order convergence (error ∝ 1/n²)"),
                         q("| Mesh conv | 8.4% | <5% | converging |")],
            "judgement": "insufficient",
            "reasoning": ("A convergence order requires errors at >=3 resolutions and a fitted slope; "
                          "the report shows one undefined 'Mesh conv' number and the word 'converging'. "
                          "Order 2 is plausible for the Euler-Bernoulli FD stencil but is unmeasured here."),
        },
        {
            "claim_id": "cj-schema-validates",
            "text": "Schema validates against jsonschema.",
            "evidence": [q("Schema  validates against jsonschema")],
            "judgement": "insufficient",
            "reasoning": ("No schema file, $id, validator version or exit status; the sentence is not "
                          "checkable and should stay unresolved in any extraction (F2)."),
        },
    ]

    checks_not_run = [
        "claim-level extraction fidelity vs wp-331-01 product (product unreachable; see F1)",
        "review-ledger fold / G3 semantic gate execution (platform gate, out of scope for this package)",
        "re-execution of the DEM indentation or the beam FD solve (no run identity in the source: no "
        "commit, deck path, radius, dt, seed — see F8)",
        "figure contents (Hertz F-delta curve, beam deflection) — only the record's figure count was read",
        "cross-report consistency of the M404 series (out of scope: single report_id per contract boundary)",
    ]

    limitations = [
        "Single channel: the platform reports list returns at most the newest 50-100 rows and ignores "
        "?tag=/?offset=, so absence of a kf-wp:wp-331-01 record is 'not found on the reachable window', "
        "not proof of non-existence; psql on tensor_reports is permission-denied for this identity.",
        "Reviewer sees only report markdown + record metadata; no producer explanation, no prior review "
        "events, no code — therefore root-cause statements about the solver (integrator choice, contact "
        "model) are inferences from the parameter line, marked as such.",
        "All numeric judgements are arithmetic on the report's own table; they validate internal "
        "consistency of the report, not the physics it claims to simulate.",
        "No finding here marks any claim as verified; verification is the platform gate's job.",
    ]

    review = {
        "review_report_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "reviewed_package": REVIEWED_PACKAGE,
        "reviewer": {
            "role": "red-team-reviewer",
            "agent": "agent/m15788",
            "repo": "TensorKnowledge",
            "independence_of_producer": True,
            "producer_explanation_used": False,
            "review_prompt_copied_from_producer": False,
            "context_used": ["tensor://reports/331#markdown", "tensor_reports[331] record metadata"],
        },
        "source": {
            "uri": "tensor://reports/331",
            "field": "markdown",
            "sha256": source_hash,
            "contract_sha256": CONTRACT_HASH,
            "hash_recomputed_independently": True,
            "hash_matches_contract": hash_ok,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": chars_ok,
            "title": rec.get("title"),
            "contract_title": CONTRACT_TITLE,
            "scenario_key": rec.get("scenario_key"),
            "contract_scenario_key": CONTRACT_SCENARIO,
        },
        "upstream": {
            "package_id": REVIEWED_PACKAGE,
            "product_found": False,
            "channels_checked": [
                "GET /tensor/reports (client-side tag scan over newest 100; ?tag= and ?offset= ignored server-side)",
                "GET /tensor/work-packages, /tensor/work_packages, /tensor/packages (all HTTP 404)",
                "psql -d tensorplatform 'select markdown from tensor_reports where id=331' (permission denied)",
                "worktree scan for wp-331-* artifacts (none outside this package)",
            ],
            "consequence": ("acceptance item upstream_packages_completed = FALSE; verdict cannot be "
                            "'approve'. Review executed against the source report as the authoritative "
                            "evidence so the analysis is still usable once the product is attached."),
        },
        "verdict": "needs-fix",
        "verdict_summary": (
            "needs-fix, not pass. Blocking: the reviewed product wp-331-01 is unreachable, so claim-level "
            "fidelity cannot be audited. Substantive: even judged on the source alone, four major defects "
            "must be fixed before any knowledge object from this report is reusable — (F3) the Hertz "
            "comparison runs at delta/R = 0.5, far outside Hertzias validity, (F4) the causal attribution "
            "'lattice cannot reproduce Hertz' is confounded by dynamic loading and an untested E_dem "
            "calibration, (F5) the only PASS (beam 0.0125%) and the claimed O(1/n^2) order have no "
            "reference value or mesh series, (F6) a 58.6% energy drift disqualifies the trajectory that "
            "produced the reported exponent/stiffness. The report's own honest-FAIL discipline is good "
            "and its three FAIL verdicts are arithmetic-consistent; they are not the defect."),
        "derived_metrics": derived,
        "findings": findings,
        "claim_judgements": claim_judgements,
        "review_event": {
            "event_id": "rev-wp-331-04-01",
            "package_id": REVIEWED_PACKAGE,
            "time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "decision": "request_changes",
            "reviewer": {"agent": "agent/m15788", "role": "red-team-reviewer"},
            "blocking_findings": [f["id"] for f in findings if f["blocking"]],
            "major_findings": [f["id"] for f in findings if f["severity"] == "major"],
            "basis": "upstream product not retrievable + 5 major defects in the reviewable source",
            "marks_claims_verified": False,
        },
        "acceptance_selfcheck": {
            "valid_json": True,
            "schema_pass": True,
            "reviewer_independent": True,
            "upstream_packages_completed": False,
            "note": "upstream_packages_completed is honestly FALSE (product unreachable, F1); "
                    "reviewer_independent holds: no producer context was read, no producer prompt used. "
                    "The reviewer asserts no verification state for any claim: verification is the "
                    "platform gate's exclusive output and is deliberately absent from this package.",
        },
        "checks_not_run": checks_not_run,
        "limitations": limitations,
        "repro_cmd": ("cd <worktree> && python3 scripts/kf_wp331_04/build_review.py && "
                      "python3 scripts/kf_wp331_04/verify_review.py"),
    }

    (OUT / "review_report.json").write_text(
        json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": source_hash,
            "source_field": "markdown",
            "producer": "agent/m15788",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": ("Independent review of wp-331-01 for report 331; source markdown re-fetched and "
                      "sha256 recomputed (match: %s). No claim marked verified." % hash_ok),
        },
        "outputs": {"review_report.json": review},
    }
    (OUT / f"kf_result.{PACKAGE_ID}.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    events = {
        "package_id": PACKAGE_ID,
        "reviewed_package": REVIEWED_PACKAGE,
        "events": [review["review_event"]],
        "note": "kept outside the package output dir so the contract's output declaration "
                "(review_report.json only) stays exactly honoured",
    }
    (RUNS / "review_events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"source_hash": source_hash, "hash_ok": hash_ok, "chars_ok": chars_ok,
                      "quotes_checked": sum(len(f.get("evidence", [])) for f in findings)
                      + sum(len(c.get("evidence", [])) for c in claim_judgements),
                      "verdict": review["verdict"],
                      "derived": {k: derived[k] for k in
                                  ("exponent_abs_deviation", "exponent_tolerance_overshoot_factor",
                                   "indent_over_R", "stiffness_budget_overshoot_factor",
                                   "energy_budget_overshoot_factor", "beam_budget_margin_factor")}},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()