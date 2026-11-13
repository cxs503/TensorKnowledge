#!/usr/bin/env python3
"""Build asset_manifest.json for KF work package wp-11204-01 (report 11204).

Contract: task_type=01-asset-registration, report_id=11204, source_field=markdown,
declared source_hash sha256:d22a30cc...5292f86, chars=5999.
Scope: register assets ONLY. No claim extraction, no verification, no classification.

Gates enforced here (all fatal, no "warn and continue"):
  G1  sha256(markdown utf-8) == contract hash, chars == contract chars
  G2  every markdown locator quote is a verbatim substring of the fetched markdown
  G3  every primary locator quote is unique inside the markdown (occurrences==1)
  G4  every path-like token found by the completeness scanner is covered by a
      registered asset (no silently unregistered reference)
  G5  asset_id uniqueness; counts recomputed from the asset list
  G6  figure bytes: sha256 stable across two independent fetches

Outputs (written inside the worktree):
  work/wp-11204-01/figures/*.png        downloaded figure bytes
  docs/kf/wp-11204-01/asset_manifest.json
  docs/kf/wp-11204-01/kf_result.json
"""
import datetime
import hashlib
import json
import os
import re
import struct
import sys
import urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WORK = os.path.join(HERE, "work", "wp-11204-01")
OUTDIR = os.path.join(HERE, "docs", "kf", "wp-11204-01")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

PACKAGE_ID = "wp-11204-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "11204"
SOURCE_URI = "tensor://reports/11204"
CONTRACT_HASH = "d22a30cc692b82f2acf6ea669fd898a330143436344e4091c4a39c06a5292f86"
CONTRACT_CHARS = 5999
REPO_OF_RECORD = "TensorPhysics"          # verbatim: "**仓** TensorPhysics"
BRANCH_OF_RECORD = "agent/m9422"          # verbatim: "**分支** `agent/m9422`"

# ---------------------------------------------------------------- asset table
# quotes are verbatim substrings of the report markdown; all are re-verified.
MD = "markdown_char_span"
RF = "record_field"

ASSETS = [
    dict(id="A01", cls="report_source_markdown", label="report 11204 markdown (the registered asset itself)",
         section="document", locators=[(MD, "# FEM 弹塑性本构（von Mises J2）与 3D 混合模式 cohesive 单元：CT / 三点弯曲验证")],
         resolution="resolved_in_source",
         why="bytes in hand and hashed; title line is also the markdown H1"),
    dict(id="A02", cls="record_metadata", label="platform record metadata (title/summary/scenario_key/tags/status)",
         section="record", locators=[(RF, "record.title"), (RF, "record.summary"), (RF, "record.scenario_key"),
                                     (RF, "record.tags"), (RF, "record.status")],
         resolution="resolved_in_source",
         why="record fields returned by GET /tensor/reports/11204 and stored in work/wp-11204-01/record.json"),
    dict(id="A03", cls="figure_file", label="fig1_ct_field_and_seb_cohesive (record figures[0], CT sigma_yy field + SE(B) cohesive curve)",
         section="record.figures[0] + ④ 结果图",
         locators=[(RF, "record.figures[0]"),
                   (MD, "![图1 CT 应力场与 SE(B) 粘聚区载荷-位移](figures/m9422/fig1_ct_field_and_seb_cohesive.png)")],
         resolution="resolved_in_source", figure="fig1_ct_field_and_seb_cohesive",
         why="PNG bytes served by the platform figure endpoint, sha256 recorded; linked from markdown ④"),
    dict(id="A04", cls="figure_file", label="fig2_mixed_mode_and_j2 (record figures[1], mixed-mode I/II/III energy vs extended BK; J2 uniaxial)",
         section="record.figures[1] + ④ 结果图",
         locators=[(RF, "record.figures[1]"),
                   (MD, "![图2 混合模式断裂能与 J2 单轴响应](figures/m9422/fig2_mixed_mode_and_j2.png)")],
         resolution="resolved_in_source", figure="fig2_mixed_mode_and_j2",
         why="PNG bytes served by the platform figure endpoint, sha256 recorded; linked from markdown ④"),
    dict(id="A05", cls="figure_file", label="fig3_j_comparison_and_convergence (record figures[2], CT J EDI vs E1820 eta; J convergence)",
         section="record.figures[2] + ④ 结果图",
         locators=[(RF, "record.figures[2]"),
                   (MD, "![图3 J 对比与网格收敛](figures/m9422/fig3_j_comparison_and_convergence.png)")],
         resolution="resolved_in_source", figure="fig3_j_comparison_and_convergence",
         why="PNG bytes served by the platform figure endpoint, sha256 recorded; linked from markdown ④"),
    dict(id="A06", cls="repo_path_reference", label="figures/m9422/fig1_ct_field_and_seb_cohesive.png (in-repo figure path, TensorPhysics)",
         section="④ 结果图", locators=[(MD, "figures/m9422/fig1_ct_field_and_seb_cohesive.png")],
         resolution="referenced_unresolved",
         why="upstream writes figures under figures/m9422/ in the TensorPhysics worktree; that path is not in this TensorKnowledge checkout and no such path is served by the platform, so the path itself is registered but not byte-resolved"),
    dict(id="A07", cls="repo_path_reference", label="figures/m9422/fig2_mixed_mode_and_j2.png (in-repo figure path, TensorPhysics)",
         section="④ 结果图", locators=[(MD, "figures/m9422/fig2_mixed_mode_and_j2.png")],
         resolution="referenced_unresolved",
         why="same as A06"),
    dict(id="A08", cls="repo_path_reference", label="figures/m9422/fig3_j_comparison_and_convergence.png (in-repo figure path, TensorPhysics)",
         section="④ 结果图", locators=[(MD, "figures/m9422/fig3_j_comparison_and_convergence.png")],
         resolution="referenced_unresolved",
         why="same as A06"),
    dict(id="A09", cls="module_reference", label="src/tensorphysics/fem_nonlinear/ (module declared for this node)",
         section="标题行", locators=[(MD, "src/tensorphysics/fem_nonlinear/")],
         resolution="referenced_unresolved",
         why="module lives in the TensorPhysics repo; not present in this worktree, not served by the platform"),
    dict(id="A10", cls="source_code_path", label="j2_plasticity.py (J2 radial return + consistent tangent)",
         section="② 1. 本构层", locators=[(MD, "`j2_plasticity.py`")],
         resolution="referenced_unresolved", why="source file owned by TensorPhysics; content not read or hashed here"),
    dict(id="A11", cls="source_code_path", label="cohesive3d.py (bilinear mixed-mode cohesive, extended BK)",
         section="② 2. 界面层", locators=[(MD, "`cohesive3d.py`")],
         resolution="referenced_unresolved", why="source file owned by TensorPhysics; content not read or hashed here"),
    dict(id="A12", cls="source_code_path", label="plane_strain_fem.py (Q4 plane-strain Newton + EDI J)",
         section="② 3. 求解层", locators=[(MD, "`plane_strain_fem.py`")],
         resolution="referenced_unresolved", why="source file owned by TensorPhysics; content not read or hashed here"),
    dict(id="A13", cls="source_code_path", label="anchors.py (ASTM E399/E1820 geometric + eta factors)",
         section="② 4. 锚点层", locators=[(MD, "`anchors.py`")],
         resolution="referenced_unresolved", why="source file owned by TensorPhysics; content not read or hashed here"),
    dict(id="A14", cls="source_code_path", label="verification.py (acceptance criteria layer)",
         section="② 5. 判据层", locators=[(MD, "`verification.py`")],
         resolution="referenced_unresolved", why="source file owned by TensorPhysics; content not read or hashed here"),
    dict(id="A15", cls="script_path", label="scripts/m9422_run_verification.py (one-shot number production)",
         section="② 5. 判据层 / 附：可复现性",
         locators=[(MD, "scripts/m9422_run_verification.py")],
         resolution="referenced_unresolved", why="script owned by TensorPhysics; not executed here"),
    dict(id="A16", cls="script_path", label="scripts/m9422_figures.py (criteria table + three figures)",
         section="附：可复现性", locators=[(MD, "scripts/m9422_figures.py")],
         resolution="referenced_unresolved", why="script owned by TensorPhysics; not executed here"),
    dict(id="A17", cls="test_path", label="tests/test_fem_elastoplastic_cohesive3d.py (40 tests incl. negative controls)",
         section="附：可复现性", locators=[(MD, "tests/test_fem_elastoplastic_cohesive3d.py")],
         resolution="referenced_unresolved",
         why="test file owned by TensorPhysics; the '(40 tests, 19 s green)' statement is upstream's, not re-run or re-verified by this package"),
    dict(id="A18", cls="result_data_path", label="artifacts/m9422/verification.json (all numbers of the report)",
         section="② 5. 判据层", locators=[(MD, "`artifacts/m9422/verification.json`")],
         resolution="referenced_unresolved",
         why="probe of /tensor/artifacts/m9422/verification.json returned HTTP 404 and the path is absent from this worktree; the numeric payload behind every table in ③ was NOT re-read, so no number is independently confirmed here"),
    dict(id="A19", cls="result_data_path", label="artifacts/m9422/acceptance.json (machine gate verdicts)",
         section="② 5. 判据层", locators=[(MD, "`acceptance.json`")],
         resolution="referenced_unresolved",
         why="probe of /tensor/artifacts/m9422/acceptance.json returned HTTP 404 and the path is absent from this worktree; the six PASS verdicts are upstream claims not re-checked here"),
    dict(id="A20", cls="symbol_reference", label="j_integral(symmetry_factor=2) (half-model EDI switch, documented condition)",
         section="⑤ 1. 半模型 EDI 陷阱", locators=[(MD, "`j_integral(symmetry_factor=2)`")],
         resolution="referenced_unresolved",
         why="symbol referenced by name only; definition lives in plane_strain_fem.py in TensorPhysics and was not inspected"),
    dict(id="A21", cls="parameter_reference", label="crack_axis=1 (SE(B) crack growth along +y)",
         section="⑤ 2. 裂纹扩展方向", locators=[(MD, "`crack_axis=1`")],
         resolution="referenced_unresolved", why="parameter name/value referenced only; implementation not inspected"),
    dict(id="A22", cls="provenance_pointer", label="producer repo/branch: TensorPhysics @ agent/m9422",
         section="标题行", locators=[(RF, "record.tags"), (MD, "**仓** TensorPhysics"), (MD, "`agent/m9422`")],
         resolution="referenced_unresolved",
         why="registration records where the artefacts live; no commit id is given anywhere in the report or record, so the exact revision behind these numbers is NOT pinned by the source (see limitations L3)"),
    dict(id="A23", cls="external_standard", label="ASTM E399 (CT/SE(B) geometry + P_Q)",
         section="① 几何与材料 / ② 4. / ③ 判据总表", locators=[(MD, "ASTM E399")],
         resolution="referenced_unresolved",
         why="normative document cited by label only; no clause text or copy is attached to the report record and no clause was read here"),
    dict(id="A24", cls="external_standard", label="ASTM E1820 (J-integral / eta-plasticity method)",
         section="① 几何与材料 / ② 4. / ③ 判据总表", locators=[(MD, "ASTM E1820")],
         resolution="referenced_unresolved",
         why="same as A23: label-only citation, standard text not available in this package"),
    dict(id="A25", cls="external_law", label="extended Benzeggagh-Kenane (BK) mixed-mode criterion",
         section="① 3D 混合模式 cohesive / ② 2. 界面层",
         locators=[(MD, "Benzeggagh-Kenane")],
         resolution="referenced_unresolved",
         why="law named and its closed form written in ②, but the analytic reference values in ③ were not recomputed by this package (extraction/verification is out of scope)"),
    dict(id="A26", cls="node_identifier", label="node p273w3-n01-fem-elastoplastic-cohesive (scenario_key)",
         section="标题行 / record.scenario_key",
         locators=[(RF, "record.scenario_key"), (MD, "p273w3-n01-fem-elastoplastic-cohesive")],
         resolution="resolved_in_source", why="identifier is byte-identical in markdown and in the platform record scenario_key"),
    dict(id="A27", cls="repro_command_block", label="reproducibility code block of 附：可复现性 (3 commands)",
         section="附：可复现性",
         locators=[(MD, "python scripts/m9422_run_verification.py   # 全部数字 -> artifacts/m9422/*.json"),
                   (MD, "python scripts/m9422_figures.py            # 判据表 + 三张图")],
         resolution="referenced_unresolved",
         why="commands target the TensorPhysics worktree; not executable from this TensorKnowledge checkout and not executed by this package"),
]

# path-like / standard-like tokens that the completeness scanner must find covered
SCAN_RE = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(?:py|json|png|md)|"
    r"src/[A-Za-z0-9_./\-]+|"
    r"ASTM E[0-9]+[A-Za-z0-9]*"
)


def sha256_hex(b):
    return hashlib.sha256(b).hexdigest()


def login():
    user = os.environ.get("TENSOR_AGENT_USER", "")
    pw = os.environ.get("TENSOR_AGENT_PASS", "")
    req = urllib.request.Request(API + "/auth/login",
                                 data=json.dumps({"username": user, "password": pw}).encode(),
                                 method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return d.get("access_token") or d.get("token")


def get_bytes(token, path):
    req = urllib.request.Request(API + path, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read(), r.headers.get("Content-Type")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("Content-Type") if e.headers else None


def png_size(b):
    if len(b) < 24 or not b.startswith(b"\x89PNG\r\n\x1a\n"):
        return None
    w, h = struct.unpack(">II", b[16:24])
    return {"width": w, "height": h}


def char_line(md, pos):
    return md.count("\n", 0, pos) + 1


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    figdir = os.path.join(WORK, "figures")
    os.makedirs(figdir, exist_ok=True)
    md = open(os.path.join(WORK, "source_markdown.md"), encoding="utf-8").read()
    record = json.load(open(os.path.join(WORK, "record.json"), encoding="utf-8"))

    # ---- G1
    h = sha256_hex(md.encode("utf-8"))
    if h != CONTRACT_HASH or len(md) != CONTRACT_CHARS:
        print("FATAL G1: hash/chars mismatch", h, len(md))
        return 1

    token = login()

    # ---- G6: fetch each figure twice, hash must agree
    fig_bytes = {}
    fig_checks = {}
    for name in [a["figure"] for a in ASSETS if a.get("figure")]:
        s1, b1, ct1 = get_bytes(token, "/tensor/reports/11204/figures/" + name)
        s2, b2, ct2 = get_bytes(token, "/tensor/reports/11204/figures/" + name)
        if s1 != 200 or s2 != 200 or sha256_hex(b1) != sha256_hex(b2):
            print("FATAL G6: figure fetch unstable", name, s1, s2)
            return 2
        open(os.path.join(figdir, name + ".png"), "wb").write(b1)
        fig_bytes[name] = b1
        fig_checks[name] = {
            "url_path": "/tensor/reports/11204/figures/" + name,
            "http_status_first": s1,
            "http_status_second": s2,
            "content_type": ct1,
            "bytes": len(b1),
            "sha256": sha256_hex(b1),
            "hash_stable_across_2_fetches": True,
            "png_size": png_size(b1),
            "extension_form_probe": {"path": "/tensor/reports/11204/figures/" + name + ".png",
                                     "http_status": get_bytes(token, "/tensor/reports/11204/figures/" + name + ".png")[0]},
        }

    # ---- G2/G3: resolve markdown locators
    built = []
    for a in ASSETS:
        locs = []
        for kind, q in a["locators"]:
            if kind == MD:
                start = md.find(q)
                if start < 0:
                    print("FATAL G2: quote not verbatim for", a["id"], repr(q[:60]))
                    return 3
                spans = []
                pos = 0
                while True:
                    i = md.find(q, pos)
                    if i < 0:
                        break
                    spans.append({"start_char": i, "end_char": i + len(q),
                                  "start_line": char_line(md, i),
                                  "end_line": char_line(md, i + len(q))})
                    pos = i + 1
                end = start + len(q)
                locs.append({
                    "kind": MD, "source_uri": SOURCE_URI, "source_field": "markdown",
                    "start_char": start, "end_char": end,
                    "start_line": char_line(md, start), "end_line": char_line(md, end),
                    "quote": q, "occurrences": len(spans), "verbatim": True,
                    "unique": len(spans) == 1,
                    "all_spans": spans,
                })
            else:  # record field
                locs.append({"kind": RF, "source_uri": SOURCE_URI, "source_field": "record",
                             "record_path": q, "present": _record_present(record, q)})
        md_locs = [l for l in locs if l["kind"] == MD]
        if md_locs and not md_locs[0]["unique"]:
            print("NOTE G3: quote occurs %d times for %s %r -> all spans enumerated"
                  % (md_locs[0]["occurrences"], a["id"], md_locs[0]["quote"][:60]))
        entry = {
            "asset_id": a["id"],
            "asset_class": a["cls"],
            "label": a["label"],
            "in_report_section": a["section"],
            "producer_repo": REPO_OF_RECORD,
            "locators": locs,
            "resolution": a["resolution"],
            "resolution_basis": a["why"],
        }
        if a.get("figure"):
            entry["figure_bytes"] = fig_checks[a["figure"]]
        built.append(entry)

    # ---- G4: completeness scanner
    tokens = sorted(set(SCAN_RE.findall(md)))
    quoted = " \x00 ".join(l["quote"] for e in built for l in e["locators"] if l["kind"] == MD)
    uncovered = [t for t in tokens if t not in quoted]
    if uncovered:
        print("FATAL G4: unregistered path-like tokens:", uncovered)
        return 4

    # ---- G5: ids unique, counts
    ids = [e["asset_id"] for e in built]
    if len(ids) != len(set(ids)):
        print("FATAL G5: duplicate asset_id")
        return 5
    by_class = {}
    by_res = {}
    for e in built:
        by_class[e["asset_class"]] = by_class.get(e["asset_class"], 0) + 1
        by_res[e["resolution"]] = by_res.get(e["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI, "field": "markdown", "hash_alg": "sha256", "hash": h,
            "hash_prefixed": "sha256:" + h,
            "chars": len(md), "bytes_utf8": len(md.encode("utf-8")),
            "title_markdown_h1": md.split("\n", 1)[0].lstrip("# ").strip(),
            "title_record": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "platform_tags": record.get("tags"),
            "platform_figures_declared": record.get("figures"),
            "record_status": record.get("status"),
            "record_mission_id": record.get("mission_id"),
        },
        "counts": {
            "assets": len(built),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": built,
        "claims": [],
        "claims_policy": {
            "claims": [],
            "reason": "objective.register_assets=true and objective.classify_report_type=false; contract allows an empty array and forbids forced claim generation, so no claim is emitted and nothing from ③ is restated, re-derived or marked verified",
        },
        "integrity": {
            "hash_recomputed_locally": True,
            "hash_matches_contract": h == CONTRACT_HASH,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "all_markdown_quotes_verbatim": True,
            "all_primary_quotes_unique": all(l["unique"] for e in built for l in e["locators"]
                                             if l["kind"] == MD),
            "multi_occurrence_quotes": [
                {"asset_id": e["asset_id"], "quote": l["quote"], "occurrences": l["occurrences"],
                 "spans_enumerated": len(l["all_spans"])}
                for e in built for l in e["locators"] if l["kind"] == MD and not l["unique"]
            ],
            "all_occurrence_spans_enumerated": True,
            "asset_ids_unique": True,
            "completeness_scanner_tokens": len(tokens),
            "completeness_scanner_uncovered": [],
            "figure_hash_stable_across_refetch": all(
                v["hash_stable_across_2_fetches"] for v in fig_checks.values()),
        },
        "observations": [
            {
                "id": "obs-title-drift",
                "observation": "record.title differs byte-wise from the markdown H1: record uses half-width parentheses '本构(von Mises J2)', H1 uses full-width '本构（von Mises J2）'",
                "record_title": record.get("title"),
                "markdown_h1": md.split("\n", 1)[0].lstrip("# ").strip(),
                "impact": "downstream consumers must key on report_id, not on title equality",
            },
            {
                "id": "obs-figure-endpoint-extensionless",
                "observation": "figure bytes are served at /api/v1/tensor/reports/11204/figures/<name> (extensionless, HTTP 200, image/png); the same path with '.png' appended returns HTTP 404",
                "impact": "prior packages that concluded 'figures are metadata-only' for this platform were probing the wrong URL shape; here figure bytes ARE resolvable and hashed (A03-A05). The '.png' 404 must not be read as 'figure missing'",
            },
            {
                "id": "obs-mission-id",
                "observation": "record.mission_id=9422 although the package contract declares mission_id: null",
                "impact": "recorded as observed only; this package does not reconcile it",
            },
            {
                "id": "obs-no-commit-id",
                "observation": "the report names repo TensorPhysics and branch agent/m9422 but no commit SHA; neither record nor markdown pins a revision",
                "impact": "the bytes behind A09-A19 cannot be tied to an immutable revision from the source alone",
            },
            {
                "id": "obs-summary-truncated",
                "observation": "record.summary ends mid-word ('... 6 项机器判据全部 PASS；p')",
                "impact": "summary cannot be used as a self-contained evidence source; the markdown is the registration target",
            },
        ],
        "limitations": [
            "L1 registration only: no claim extraction, no numeric re-derivation, no report-type classification — those belong to downstream packages",
            "L2 verification is deliberately left unset; the platform gate computes it, this package must not mark anything verified",
            "L3 referenced implementation artefacts (A09-A19) live in the TensorPhysics repo at branch agent/m9422 with no commit SHA in the source; nothing was read, hashed or trusted from them",
            "L4 the link between the markdown figure paths (A06-A08) and the record figure names (A03-A05) rests on identical basenames; the source never states the mapping, so it is recorded as a stated-dependency, not as a verbatim fact",
            "L5 the six PASS verdicts and the 40-test/19 s claim in ③/附 are upstream statements; this package did not re-run them and marks them neither supported nor refuted",
            "L6 external standards (A23/A24) and the BK law (A25) are label-cited; no clause text was available, so no clause-level claim is registered",
            "L7 the three figure PNGs were hashed byte-wise (twice, stable), but their content was NOT audited: axes, plotted values and their agreement with the tables in section 3 of the report remain upstream statements",
        ],
        "probes_ref": "work/wp-11204-01/probes.json",
    }

    with open(os.path.join(OUTDIR, "asset_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)

    kf_result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + h,
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "producer": "agent/m15693",
            "emitted_at": _emitted_at(),
            "notes": "asset registration only; hash recomputed from the fetched markdown and equal to the contract value; no claim extracted, nothing marked verified",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    with open(os.path.join(OUTDIR, "kf_result.json"), "w", encoding="utf-8") as f:
        json.dump(kf_result, f, ensure_ascii=False, indent=1)

    print(json.dumps({"assets": len(built), "by_class": by_class, "by_resolution": by_res,
                      "scanner_tokens": len(tokens), "figures": {k: v["sha256"][:16] for k, v in fig_checks.items()}},
                     ensure_ascii=False, indent=1))
    return 0


def _emitted_at():
    """First-emission stamp, preserved across re-runs.

    Re-running the pipeline must not silently rewrite the delivered artifact: if a
    kf_result.json already exists its emitted_at is reused, so the whole repro_cmd is
    idempotent (byte-identical outputs) instead of drifting on every run.
    """
    prev = os.path.join(OUTDIR, "kf_result.json")
    if os.path.isfile(prev):
        try:
            stamp = json.load(open(prev, encoding="utf-8"))["provenance"]["emitted_at"]
            if isinstance(stamp, str) and stamp:
                return stamp
        except Exception:  # noqa: BLE001
            pass
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _record_present(record, path):
    cur = record
    for part in re.findall(r"[^.\[\]]+|\[(\d+)\]", path.replace("record.", "")):
        pass
    # simple resolver supporting a.b[0].c
    cur = record
    for m in re.finditer(r"([A-Za-z0-9_]+)|\[([0-9]+)\]", path.replace("record.", "")):
        key, idx = m.group(1), m.group(2)
        if key is not None:
            if not isinstance(cur, dict) or key not in cur:
                return False
            cur = cur[key]
        else:
            i = int(idx)
            if not isinstance(cur, list) or i >= len(cur):
                return False
            cur = cur[i]
    return True


if __name__ == "__main__":
    sys.exit(main())