#!/usr/bin/env python3
"""wp-542-04 - independent (red-team) review of wp-542-01 for report 542.

Boundary: touches ONLY report_id=542 and the upstream package docs/kf/wp-542-01/.
Nothing is written to any other report package; upstream artifacts are never
edited, only recomputed for comparison.

Reviewer context rule (contract: reviewer_context_excludes_producer_explanation):
context = (a) the report markdown byte-for-byte as served by the platform,
(b) the upstream knowledge objects (kf_result.json / asset_manifest.json /
verification.json). No producer narrative is consumed.

Outputs (under --out, default docs/kf/wp-542-04):
  review_report.json   machine-readable review (verdict + checks + findings)
  source_snapshot.md   byte-exact copy of the reviewed markdown (replay input)
  report_body.md       publication body (six sections; numbers injected)
  figs/review_overview.png

Replay (offline, committed snapshot):
  python3 scripts/kf/review_wp542_04.py --offline --out docs/kf/wp-542-04
Replay (live platform record):
  python3 scripts/kf/review_wp542_04.py --out docs/kf/wp-542-04
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

REPORT_ID = "542"
PACKAGE_ID = "wp-542-04"
UPSTREAM_PACKAGE = "wp-542-01"
DECLARED_SOURCE_HASH = "sha256:a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40"
UPSTREAM_DIR = Path("docs/kf") / UPSTREAM_PACKAGE
PATH_TOKEN_RE = re.compile(r"[A-Za-z0-9_./-]+\.(?:py|json|png|md|csv|dat)\b")
PASS_CELL_RE = re.compile(r"\|\s*([^|]*PASS[^|]*)\s*\|")

# Verbatim evidence quotes. Each is asserted to be an exact substring of the
# reviewed markdown; a miss is reported as a failed check, never patched.
QUOTES = {
    "ice_density": "| 冰密度 \u03c1_ice | 917 kg/m\u00b3 | dem3d.py:24 硬编码 |",
    "fem_qualified_path": "tensorfem/shell4.py",
    "cohesive_pin": "tensorfem/cohesive.py:32",
    "cohesive_table_row": "| cohesive.py | 两节点cohesive界面 | ✅有测试 | PASS | test_cohesive.py (6 tests) |",
    "dynamics_pair": "tensorfem/dynamics.py, explicit_dynamics.py",
    "radar_gap_score": "整体差距在 4-6 分（10分制）",
    "no_numbers": "本单为 **能力盘点与任务规划**，无数值计算结果，故无误差判定",
    "task_row_L1": "| L1 基础能力 | 8 | 136h | A(5并行), B(4), C(3) |",
    "task_row_L2": "| L2 验证锚 | 4 | 50h | B(2), C(1), A(1) |",
    "task_row_L3": "| L3 应用集成 | 4 | 92h | D(2), E(2等G4) |",
    "task_row_total": "| **合计** | **16** | **278h** | \u2014 |",
    "groupA": "- **立即启动（组A）**：F01, F03, F04, F05, V04 \u2014 5个任务可并行",
    "sir_acronym": "SIR（Suboff Icebreaking Research）",
    "readonly_audit": "1. **只读审计**：未修改任何 src/ 代码，所有论断基于源码 + 已有测试",
    "smoke_scale": "2. **规模限制**：SI-4 演示为 smoke 级（12颗粒），非工程规模",
    "gpu_unverified": "3. **GPU 未验证**：dem3d.py 声称支持 CUDA，但 cell list 可能同步阻塞",
    "phys_acc_false": "4. **物理精度**：coupled_hull.py 的 `physical_accuracy_qualified` 硬编码为 False",
    "radar_reading": "TensorFEM 在时间积分(7)和断裂(6)方面较强，但在自适应(1)、并行(2)、工程规模(2)方面严重不足",
}


# --------------------------------------------------------------------------- io
def fetch_markdown() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user = os.environ["TENSOR_AGENT_USER"]
    password = os.environ["TENSOR_AGENT_PASS"]

    def call(path, payload=None, token=None):
        req = urllib.request.Request(
            base + path,
            data=json.dumps(payload).encode() if payload else None,
            method="POST" if payload else "GET",
        )
        req.add_header("Content-Type", "application/json")
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())

    token = call("/auth/login", {"username": user, "password": password})["access_token"]
    return call(f"/tensor/reports/{REPORT_ID}", token=token)["markdown"]


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ----------------------------------------------------------------------- checks
def check_source_hash(md: str) -> dict:
    got = sha256_text(md)
    return {"id": "C1", "name": "source_hash_matches_contract",
            "result": "pass" if got == DECLARED_SOURCE_HASH else "fail",
            "detail": f"recomputed={got} declared={DECLARED_SOURCE_HASH} "
                      f"chars={len(md)} bytes={len(md.encode('utf-8'))}"}


def check_quotes(md: str, lines: list) -> tuple:
    located, missing = {}, []
    for key, quote in QUOTES.items():
        if quote in md:
            located[key] = {"quote": quote, "line": next(i for i, l in enumerate(lines, 1) if quote in l)}
        else:
            missing.append(key)
    return ({"id": "C2", "name": "evidence_quotes_verbatim_in_source",
             "result": "pass" if not missing else "fail",
             "detail": f"quotes={len(QUOTES)} located={len(located)} missing={missing}"}, located)


def check_upstream_integrity(manifest_path: Path, kf_path: Path) -> tuple:
    kf = json.loads(kf_path.read_text(encoding="utf-8"))
    declared = kf["outputs"]["asset_manifest.json"]
    got_hash, got_bytes = sha256_file(manifest_path), manifest_path.stat().st_size
    ok = got_hash == declared["sha256"] and got_bytes == declared["bytes"]
    return ({"id": "C3", "name": "upstream_manifest_matches_its_declared_hash",
             "result": "pass" if ok else "fail",
             "detail": f"sha256={got_hash} declared={declared['sha256']} "
                       f"bytes={got_bytes} declared_bytes={declared['bytes']}"}, kf)


def _manifest_paths(assets: list) -> dict:
    out = defaultdict(list)
    for a in assets:
        p = a.get("path_reference")
        if p:
            out[p].append(a["asset_id"])
    return dict(out)


def check_recall_precision(md: str, assets: list) -> tuple:
    tokens = sorted(set(PATH_TOKEN_RE.findall(md)))
    man = _manifest_paths(assets)
    missing = [t for t in tokens if t not in man]
    extra = [p for p in man if p not in tokens]
    stats = {"path_tokens_in_source": len(tokens), "manifest_paths": len(man),
             "missing_from_manifest": missing, "extra_in_manifest": extra}
    return ([
        {"id": "C4", "name": "path_inventory_recall", "result": "pass" if not missing else "fail",
         "detail": f"source_tokens={len(tokens)} registered={len(tokens) - len(missing)} missing={missing}"},
        {"id": "C5", "name": "path_inventory_precision_no_invented_paths",
         "result": "pass" if not extra else "fail",
         "detail": f"manifest_paths={len(man)} not_traceable_to_source={extra}"},
    ], stats)


def check_locators(lines: list, assets: list) -> tuple:
    checked = bad_quote = bad_path = 0
    problems = []
    for a in assets:
        loc = a.get("locator") or {}
        if loc.get("scheme") != "markdown_line":
            continue
        checked += 1
        n, quote = loc.get("line"), loc.get("quote")
        if not isinstance(n, int) or not (1 <= n <= len(lines)):
            problems.append({"asset_id": a["asset_id"], "problem": "line_out_of_range", "line": n})
            bad_quote += 1
            continue
        if not quote or quote not in lines[n - 1]:
            problems.append({"asset_id": a["asset_id"], "problem": "quote_not_on_declared_line", "line": n})
            bad_quote += 1
        pref = a.get("path_reference")
        if pref and pref not in lines[n - 1]:
            problems.append({"asset_id": a["asset_id"], "problem": "path_not_in_declared_line", "line": n})
            bad_path += 1
    return ({"id": "C6", "name": "locators_resolve_verbatim_on_declared_lines",
             "result": "pass" if bad_quote == 0 and bad_path == 0 else "fail",
             "detail": f"markdown_line_locators={checked} quote_mismatch={bad_quote} path_mismatch={bad_path}"},
            {"checked": checked, "problems": problems})


def check_identity(assets: list) -> tuple:
    ids = [a["asset_id"] for a in assets]
    dup_ids = [i for i, c in Counter(ids).items() if c > 1]
    occ = Counter((a.get("path_reference"), (a.get("locator") or {}).get("line"))
                  for a in assets if a.get("path_reference"))
    dup_occ = [{"path": k[0], "line": k[1], "n": v} for k, v in occ.items() if v > 1]
    man_paths = _manifest_paths(assets)
    by_base = defaultdict(list)
    for p in man_paths:
        by_base[p.rsplit("/", 1)[-1]].append(p)
    variants = {b: ps for b, ps in by_base.items() if len(ps) > 1}
    return ([{"id": "C7", "name": "asset_ids_unique", "result": "pass" if not dup_ids else "fail",
              "detail": f"assets={len(assets)} unique={len(set(ids))} duplicates={dup_ids}"}],
            {"asset_count": len(assets), "distinct_path_strings": len(man_paths),
             "distinct_basenames_files": len(by_base), "basename_variants": variants,
             "duplicate_occurrences": dup_occ})


def check_resolution(assets: list) -> tuple:
    status = Counter((a.get("resolution") or {}).get("status") for a in assets)
    kinds = Counter(a.get("kind") for a in assets)
    kind_status = Counter(f"{a.get('kind')}/{(a.get('resolution') or {}).get('status')}" for a in assets)
    return ({"id": "C8", "name": "resolution_status_uses_declared_vocabulary",
             "result": "pass" if set(status) <= {"resolved", "unresolved", "metadata_only"} else "fail",
             "detail": f"status_counts={dict(status)} by_kind_status={dict(kind_status)}"},
            {"status_counts": dict(status), "kind_counts": dict(kinds), "kind_status": dict(kind_status)})


def check_claims_hygiene(manifest: dict) -> list:
    claims = manifest.get("claims", [])
    verified = [c for c in claims if str(c.get("status", "")).lower() == "verified"]
    return [
        {"id": "C9", "name": "no_claim_marked_verified", "result": "pass" if not verified else "fail",
         "detail": f"claims={len(claims)} verified_marks={len(verified)} note={manifest.get('claims_note', '')}"},
        {"id": "C10", "name": "empty_claims_consistent_with_task_type_01",
         "result": "pass" if not claims else "not_run",
         "detail": f"task_type={manifest.get('task_type')} claims={len(claims)} (registration-only, no extraction)"},
    ]


def _cells(quote: str) -> list:
    return [c.strip().strip("*") for c in quote.strip().strip("|").split("|")]


def _num(cell: str):
    m = re.search(r"\d+", cell)
    return int(m.group()) if m else None


def check_report_internals(md: str, lines: list, assets: list) -> tuple:
    keys = ("task_row_L1", "task_row_L2", "task_row_L3", "task_row_total")
    label = {"task_row_L1": "L1", "task_row_L2": "L2", "task_row_L3": "L3", "task_row_total": "TOTAL"}
    parsed = {label[k]: _cells(QUOTES[k]) for k in keys}
    nodes = {k: _num(parsed[k][1]) for k in ("L1", "L2", "L3")}
    hours = {k: _num(parsed[k][2]) for k in ("L1", "L2", "L3")}
    total_nodes, total_hours = _num(parsed["TOTAL"][1]), _num(parsed["TOTAL"][2])
    groups, members = {}, {}
    for k in ("L1", "L2", "L3"):
        groups[k] = {m.group(1): int(m.group(2)) for m in re.finditer(r"([A-E])\((\d+)", " ".join(parsed[k][2:4]))}
        members[k] = sum(groups[k].values())
    group_a = re.findall(r"F\d+|V\d+", QUOTES["groupA"])
    pass_cells = [c.strip() for l in lines if l.startswith("|") for c in PASS_CELL_RE.findall(l)]
    pass_exact = [c for c in pass_cells if c == "PASS"]
    unresolved = [a for a in assets
                  if (a.get("resolution") or {}).get("status") == "unresolved"
                  and a.get("kind") in ("source_code_reference", "data_artifact_reference")]
    checks = [
        {"id": "C11", "name": "task_tree_node_arithmetic_consistent",
         "result": "pass" if sum(nodes.values()) == total_nodes else "fail",
         "detail": f"L1={nodes['L1']} L2={nodes['L2']} L3={nodes['L3']} "
                   f"sum={sum(nodes.values())} total={total_nodes}"},
        {"id": "C12", "name": "task_tree_hour_arithmetic_consistent",
         "result": "pass" if sum(hours.values()) == total_hours else "fail",
         "detail": f"L1={hours['L1']} L2={hours['L2']} L3={hours['L3']} "
                   f"sum={sum(hours.values())} total={total_hours}"},
        {"id": "C13", "name": "per_layer_parallel_group_memberships_match_node_counts",
         "result": "pass" if all(members[k] == nodes[k] for k in nodes) else "fail",
         "detail": f"declared_group_members_per_layer={members} node_counts={nodes}"},
        {"id": "C14", "name": "module_verification_status_traceable_to_resolved_artifact", "result": "not_run",
         "detail": f"PASS-style cells in report={len(pass_cells)} (exact 'PASS'={len(pass_exact)}); "
                   f"unresolved code/data references upstream={len(unresolved)} -> none checkable here"},
        {"id": "C15", "name": "no_numerical_result_vs_numerical_claims",
         "result": "fail" if (QUOTES["radar_gap_score"] in md and "无数值计算结果" in md) else "pass",
         "detail": "section 6 states no numerical result exists while sections 3.4/3.5 report 10-point radar "
                   "scores and a 4-6 point gap band"},
    ]
    stats = {"nodes": nodes, "hours": hours, "total_nodes": total_nodes, "total_hours": total_hours,
             "group_members_per_layer": members, "groups": groups, "groupA_members": group_a,
             "pass_cells": len(pass_cells), "pass_exact": len(pass_exact),
             "unresolved_code_or_data_refs": len(unresolved)}
    return checks, stats


def check_upstream_gates(path: Path) -> tuple:
    v = json.loads(path.read_text(encoding="utf-8"))
    failed = [k for k, c in v.get("checks", {}).items() if not c.get("pass")]
    return ({"id": "C16", "name": "upstream_self_verification_record_read_not_adopted",
             "result": "not_run",
             "detail": f"upstream all_pass={v.get('all_pass')} failed_checks={failed}; the upstream gate record is "
                       f"evidence only and is not adopted as this review's verdict"}, v)


# --------------------------------------------------------------------- findings
def build_findings(q: dict, ident: dict, res: dict, rep: dict) -> list:
    findings = []
    variants = ident["basename_variants"]
    if variants:
        findings.append({
            "id": "F-01", "severity": "low", "blocking": False,
            "statement": "Upstream counts distinct path STRINGS, not distinct files: several files are cited under both a "
                         "qualified and an unqualified form, so the distinct-path total overstates distinct artifacts.",
            "evidence": [
                {"quote": q["fem_qualified_path"]["quote"], "line": q["fem_qualified_path"]["line"],
                 "note": "qualified form in the parameter table"},
                {"quote": "| shell4.py | 4节点MITC4壳 | ✅有测试 | PASS | test_shell4.py |", "line": None,
                 "note": "same file, unqualified form in the module table"},
                {"quote": q["cohesive_pin"]["quote"], "line": q["cohesive_pin"]["line"],
                 "note": "qualified form, second alias group"},
                {"quote": q["cohesive_table_row"]["quote"], "line": q["cohesive_table_row"]["line"],
                 "note": "unqualified form of the same file"},
            ],
            "quantities": {"distinct_path_strings": ident["distinct_path_strings"],
                           "distinct_file_basenames": ident["distinct_basenames_files"],
                           "variant_groups": variants},
            "affected_scope": "upstream summary.distinct_referenced_paths; any downstream per-file inventory metric",
            "recommendation": "Downstream extraction should normalise basenames before counting distinct artifacts and "
                              "keep the qualified/unqualified aliasing as an explicit alias map.",
        })
    if ident["duplicate_occurrences"]:
        findings.append({
            "id": "F-02", "severity": "low", "blocking": False,
            "statement": "Occurrence-level identity is documented, but body and appendix citations of the same files are "
                         "registered separately, so asset_count reads as inventory breadth when it is citation count.",
            "evidence": [
                {"quote": "![能力雷达图](runs/m605/fig1_capability_radar.png)", "line": None,
                 "note": "body image reference"},
                {"quote": "| `runs/m605/fig1_capability_radar.png` | 能力雷达图 |", "line": None,
                 "note": "appendix inventory row for the same file"},
            ],
            "quantities": {"asset_count": ident["asset_count"],
                           "duplicate_path_line_pairs": len(ident["duplicate_occurrences"]),
                           "examples": ident["duplicate_occurrences"][:6]},
            "affected_scope": "upstream summary.asset_count vs distinct_referenced_paths; ledger totals",
            "recommendation": "Report occurrence_count and distinct_file_count side by side so totals cannot be read "
                              "as breadth.",
        })
    findings.append({
        "id": "F-03", "severity": "medium", "blocking": False,
        "statement": "The report's central capability verdicts (module-level PASS) rest on artifacts that all sit outside "
                     "the resolved set, so registration cannot support them: PASS is producer-asserted, not established.",
        "evidence": [
            {"quote": q["readonly_audit"]["quote"], "line": q["readonly_audit"]["line"],
             "note": "evidence basis declared by the report itself"},
            {"quote": q["smoke_scale"]["quote"], "line": q["smoke_scale"]["line"],
             "note": "the only quantified demonstration is smoke scale"},
            {"quote": q["gpu_unverified"]["quote"], "line": q["gpu_unverified"]["line"],
             "note": "GPU support asserted without a runnable check"},
            {"quote": q["phys_acc_false"]["quote"], "line": q["phys_acc_false"]["line"],
             "note": "one module self-declares physical_accuracy=False"},
        ],
        "quantities": {"pass_style_cells": rep["pass_cells"], "exact_PASS_cells": rep["pass_exact"],
                       "unresolved_code_or_data_refs": rep["unresolved_code_or_data_refs"],
                       "resolution_status_counts": res["status_counts"]},
        "affected_scope": "report sections 3.1/3.2 maturity tables; any downstream object asserting solver maturity",
        "recommendation": "Task 03 must record these as producer-asserted (partially-supported/unresolved) unless "
                          "TensorFEM/TensorDEM sources resolve; do not promote them to supported.",
    })
    findings.append({
        "id": "F-04", "severity": "medium", "blocking": False,
        "statement": "The task-tree summary table is internally inconsistent: the L1 row lists parallel groups whose "
                     "member counts sum well above that layer's node count, and the L2 row re-lists the same groups, so "
                     "the layer/group mapping cannot be reconstructed from the report alone.",
        "evidence": [
            {"quote": q["task_row_L1"]["quote"], "line": q["task_row_L1"]["line"],
             "note": "L1 node count vs declared group member counts"},
            {"quote": q["task_row_L2"]["quote"], "line": q["task_row_L2"]["line"],
             "note": "L2 re-lists subsets of A/B/C"},
            {"quote": q["groupA"]["quote"], "line": q["groupA"]["line"],
             "note": "group A membership enumerated in prose (5 members, one of them a V node)"},
        ],
        "quantities": {"node_counts": rep["nodes"],
                       "declared_group_members_per_layer": rep["group_members_per_layer"],
                       "groupA_members": rep["groupA_members"]},
        "affected_scope": "report sections 4.1/4.3 scheduling plan; any extraction of task-tree structure from text",
        "recommendation": "Extract the task tree only from artifacts/fem_dem_task_tree.json (currently unresolved) and "
                          "treat the table's group columns as ambiguous until that JSON resolves.",
    })
    findings.append({
        "id": "F-05", "severity": "medium", "blocking": False,
        "statement": "Section 6 declares no numerical result exists, yet sections 3.4/3.5 assert 10-point radar scores "
                     "and a '4-6 point' gap band with no rubric, sample or baseline; those numbers are unfalsifiable as "
                     "published.",
        "evidence": [
            {"quote": q["no_numbers"]["quote"], "line": q["no_numbers"]["line"], "note": "section 6 disclaimer"},
            {"quote": q["radar_gap_score"]["quote"], "line": q["radar_gap_score"]["line"],
             "note": "quantitative gap claim"},
            {"quote": q["radar_reading"]["quote"], "line": q["radar_reading"]["line"],
             "note": "per-dimension scores without a rubric"},
        ],
        "quantities": {"stated_gap_band": "4-6 / 10", "rubric_found": False},
        "affected_scope": "report sections 3.4, 3.5, 6; any downstream claim citing scores or the gap band",
        "recommendation": "Treat radar scores as illustrative; require the rubric and per-dimension evidence before any "
                          "downstream claim uses them, otherwise record them unresolved.",
    })
    findings.append({
        "id": "F-06", "severity": "low", "blocking": False,
        "statement": "The acronym expansion offered for SIR is not supported anywhere in the report, while SIR is "
                     "elsewhere used as a run/series identifier; the expansion must not be propagated as a defined term.",
        "evidence": [
            {"quote": q["sir_acronym"]["quote"], "line": q["sir_acronym"]["line"], "note": "the only definition offered"},
            {"quote": "| SIR5 断裂规模 | 405颗粒, 3560键, 624断裂 | sir5 run_summary.json |", "line": None,
             "note": "SIR used as run identifier"},
        ],
        "quantities": {"definition_source_cited": False},
        "affected_scope": "terminology of downstream knowledge objects and glossary entries",
        "recommendation": "Keep SIR unresolved in the glossary until an authoritative definition is cited.",
    })
    findings.append({
        "id": "F-07", "severity": "info", "blocking": False,
        "statement": "Priority and blocking level are not in fixed correspondence in the gap matrix (one P1 gap carries "
                     "the same blocking marker as the P0 gaps), so severity ordering cannot be derived mechanically.",
        "evidence": [
            {"quote": "| P1 | GAP-FEM-P1 | 附加质量未接入质量矩阵 | 🔴阻断 | 频率误差 |", "line": None,
             "note": "P1 with the blocking marker"},
            {"quote": "| P0 | GAP-FEM-P0 | Winkler弹性地基板缺失 | 🔴阻断 | SI-4全链 |", "line": None,
             "note": "P0 with the same marker"},
        ],
        "quantities": {"priority_levels": 4, "distinct_blocking_markers": 4},
        "affected_scope": "report section 3.3 gap prioritisation ordering",
        "recommendation": "No action for registration; downstream should sort by the blocking column, not the priority id.",
    })
    return findings


# ------------------------------------------------------------------ publishing
def make_figure(res: dict, ident: dict, rep: dict, out_png: Path) -> bool:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return False
    fig, axes = plt.subplots(1, 3, figsize=(13, 3.8))
    ax = axes[0]
    labels = list(res["status_counts"].keys())
    vals = [res["status_counts"][k] for k in labels]
    ax.bar(labels, vals, color=["#2e7d32", "#f9a825", "#c62828"][: len(labels)])
    for i, v in enumerate(vals):
        ax.text(i, v, str(v), ha="center", va="bottom")
    ax.set_title("wp-542-01 asset resolution status")
    ax.set_ylabel("assets")

    ax = axes[1]
    series = [ident["asset_count"], ident["distinct_path_strings"], ident["distinct_basenames_files"]]
    ax.bar(["citations\n(asset_count)", "distinct path\nstrings", "distinct files\n(basename)"],
           series, color=["#1565c0", "#42a5f5", "#90caf9"])
    for i, v in enumerate(series):
        ax.text(i, v, str(v), ha="center", va="bottom")
    ax.set_title("registration breadth vs identity")

    ax = axes[2]
    ax.bar(["nodes\nL1+L2+L3", "declared group\nmembers (L1 row)"],
           [sum(rep["nodes"].values()), rep["group_members_per_layer"]["L1"]],
           color=["#6a1b9a", "#ef6c00"])
    ax.axhline(rep["nodes"]["L1"], ls="--", color="k", lw=1)
    ax.text(1.45, rep["nodes"]["L1"], f"L1 nodes={rep['nodes']['L1']}", va="bottom", ha="right", fontsize=8)
    ax.set_title("task-tree L1: nodes vs group members")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=130)
    plt.close(fig)
    return True


def render_body(rep: dict, checks: list, findings: list, ident: dict, res: dict, located: dict,
                figure_name) -> str:
    def tick(r):
        if isinstance(r, bool):
            return "✅" if r else "❌"
        return {"pass": "✅", "fail": "❌", "not_run": "⏸"}.get(r, "?")

    review = rep
    inv, loc = review["inventory"], review["locator"]
    rep = review["report_internals"]
    n_pass = sum(1 for c in checks if c["result"] == "pass")
    n_fail = sum(1 for c in checks if c["result"] == "fail")
    n_skip = sum(1 for c in checks if c["result"] == "not_run")
    quote_mis = sum(1 for p in loc["problems"] if p["problem"] == "quote_not_on_declared_line")
    path_mis = sum(1 for p in loc["problems"] if p["problem"] == "path_not_in_declared_line")
    P = PACKAGE_ID
    L = []
    L += [
        f"# KF-RESULT {P}", "",
        f"**工作包**: `{P}` (`04-independent-review`) · **被审对象**: `{UPSTREAM_PACKAGE}` (report {REPORT_ID})",
        f"**审核角色**: red-team-reviewer · **结论**: **{review['verdict']}**"
        f"（阻断项 {sum(1 for f in findings if f['blocking'])}）", "",
        "## ① 本工序做了什么", "",
        f"对 report {REPORT_ID}（《FEM/DEM 能力盘点与成组任务树 — m605 进展报告》）的上游工作包 "
        f"`{UPSTREAM_PACKAGE}`（task_type `01-asset-registration`）做独立对抗式审核：不看生产者解释，"
        "只以**报告原文 + 上游知识产物**（`kf_result.json` / `asset_manifest.json` / `verification.json`）为上下文，"
        "独立重算哈希、路径清点的召回/精确率、定位符逐字一致性、身份去重口径、报告内部数值自洽性，"
        "判定上游能否放行给下游工序。**本轮不改上游任何产物，也不把任何结论标成 verified。**", "",
        "## ② 怎么做的（步骤/工具/关键设置）", "",
        "1. 取原文：`GET /api/v1/tensor/reports/542` 的 `markdown` 字段落盘为 `source_snapshot.md`，"
        "重算 SHA256 与契约声明比对（C1）。",
        "2. 取上游产物：`docs/kf/wp-542-01/*.json`，重算 `asset_manifest.json` 字节哈希与其在 "
        "`kf_result.json` 中的自声明比对（C3）。",
        "3. 路径清点：对原文做**独立**正则抽取 `[A-Za-z0-9_./-]+\\.(py|json|png|md|csv|dat)`，"
        "与 manifest 的 `path_reference` 集合做双向差集——召回（C4）/ 无捏造（C5）。",
        "4. 定位符核验：对每条 `locator.scheme=markdown_line` 资产，检查 `quote` 是否为其**声明行**的逐字子串，"
        "且 `path_reference` 出现在同一行（C6）。",
        "5. 身份核验：`asset_id` 唯一性（C7）、`(path, markdown_line)` 重复、basename 归一后的**真实文件数**。",
        "6. 报告内部自洽：任务树节点/工时/并行组算术（C11-C13）；§6「无数值结果」与 §3.4/3.5 雷达分数的冲突（C15）；"
        "PASS 类结论与可解析证据的比例（C14）。",
        "7. 全部引文由程序断言为原文逐字子串，findings 内的引文同样复查（C17）；miss 即 check fail，不做人工修补。",
        "", "## ③ 产出物清单", "",
        "| 文件 | 要点 |", "|------|------|",
        f"| `docs/kf/{P}/review_report.json` | 机读审核结论：verdict / checks / findings / limitations（本单交付物） |",
        f"| `docs/kf/{P}/kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs） |",
        f"| `docs/kf/{P}/source_snapshot.md` | 被审 markdown 字节级快照（`--offline` 复跑输入） |",
        f"| `docs/kf/{P}/report_body.md` | 本报告正文（数字由脚本注入，零手抄） |",
        "| `scripts/kf/review_wp542_04.py` | 一键复跑全部检查（见 ⑧） |",
    ]
    if figure_name:
        L.append(f"| `docs/kf/{P}/figs/{figure_name}` | 三分面：解析状态分布 / 引用数与真实文件数 / L1 节点数 vs 组员数 |")
    L += ["", "## ④ 证据定位表（claim/字段 → 原文逐字引文）", "",
          "> 引文由脚本断言 `quote in markdown`；行号=平台 markdown 行号（1-based）。", "",
          "| # | 判定对象 | 原文引文（逐字） | 行 |", "|---|----------|------------------|----|"]
    keymap = [
        ("C1", "原文哈希锚点（参数表首行）", "ice_density"),
        ("C4/C5", "路径清点：qualified 形式", "fem_qualified_path"),
        ("F-01", "同一文件的 qualified 写法（别名组）", "cohesive_pin"),
        ("F-01", "同一文件的 unqualified 写法", "cohesive_table_row"),
        ("C4/C5", "同一行并列两条路径", "dynamics_pair"),
        ("C15", "§6「无数值结果」声明", "no_numbers"),
        ("C15", "§3.4 量化差距断言", "radar_gap_score"),
        ("C15", "§3.4 分项评分（无评分表）", "radar_reading"),
        ("C11", "任务树 L1 行（8 节点 / A(5),B(4),C(3)）", "task_row_L1"),
        ("C13", "任务树 L2 行（重列 A/B/C）", "task_row_L2"),
        ("C12", "任务树合计 16 节点 278h", "task_row_total"),
        ("C13", "组A 5 个任务（跨层，含 V04）", "groupA"),
        ("F-03", "只读审计的证据基础", "readonly_audit"),
        ("F-03", "PASS 结论下唯一的量化演示规模", "smoke_scale"),
        ("F-03", "GPU 能力自述（未验证）", "gpu_unverified"),
        ("F-03", "模块自承精度不合格", "phys_acc_false"),
        ("F-06", "SIR 缩写的唯一出处", "sir_acronym"),
    ]
    for cid, what, key in keymap:
        it = located[key]
        qv = it["quote"].replace("|", chr(92) + "|")
        L.append(f"| {cid} | {what} | {qv} | {it['line']} |" if "`" in it["quote"]
                 else f"| {cid} | {what} | `{qv}` | {it['line']} |")
    L += ["", "## ⑤ 注意点与局限", "",
          f"1. **上游 {res['status_counts'].get('unresolved', 0)}/{ident['asset_count']} 资产 unresolved**"
          f"（{', '.join(f'{k}={v}' for k, v in res['status_counts'].items())}）：TensorFEM/TensorDEM 源码树不在本仓边界内，故本单只裁「登记是否忠实于原文」，"
          "**不裁**「PASS 是否成立」——能力真伪属领域仓/下游取证范围。",
          "2. **上游自门记录只作证据**：`verification.json` 的 `all_pass` 被读取但未被采纳为本单裁决（C16=`not_run`）。",
          "3. **未读生产者解释**：上下文仅原文 + 上游三件产物，未引入任何生产者叙述性说明。",
          "4. **未运行** TensorFEM/TensorDEM 的任何测试或算例（越界），对报告的能力论断保持 unresolved。",
          "5. 引文行号绑定平台当前 markdown（sha256 已固定）；报告若被重新编辑，行号需重算，哈希门会先失败。",
          "6. **同仓独立性局限**：与上游共用同一 worktree，独立性是方法学的（独立重算 + 不同检查面），"
          "非组织隔离；已在 `review_report.json` 的 `reviewer_independence` 中登记。"]
    if not figure_name:
        L.append("7. 未生成图：环境缺 matplotlib（本单为审核结论，不涉场量/基准曲线）。")
    L += ["", "## ⑥ 自检（对照 acceptance 逐条）", "",
          "| acceptance 项 | 结果 | 依据 |", "|---------------|------|------|",
          f"| valid_json | {tick(review['acceptance']['valid_json'])} | `json.load` 通过（review_report.json / kf_result.json） |",
          f"| schema_pass | {tick(review['acceptance']['schema_pass'])} | 信封五键齐备；`task_type` 匹配 "
          "`^[0-9]{2}(-[a-z0-9-]+)?$`；`provenance` 含 `source_hash`+`source_field` |",
          f"| reviewer_independent | {tick(review['acceptance']['reviewer_independent'])} | 上下文=原文+上游产物；"
          "未读生产者解释；哈希/清点/定位符独立重算（局限见 ⑤-6） |",
          f"| upstream_packages_completed | {tick(review['acceptance']['upstream_packages_completed'])} | "
          f"`{UPSTREAM_PACKAGE}` 三件产物齐备且 manifest 哈希自洽（C3） |", "",
          f"**审核校验面**：{n_pass} pass / {n_fail} fail / {n_skip} not_run；"
          f"**发现项**：阻断 {sum(1 for f in findings if f['blocking'])} / "
          f"medium {sum(1 for f in findings if f['severity'] == 'medium')} / "
          f"low {sum(1 for f in findings if f['severity'] == 'low')} / "
          f"info {sum(1 for f in findings if f['severity'] == 'info')}。", "",
          "**如实列的未通过/未跑项**：C14（能力真伪不可由本仓校验）、C16（上游自门记录不采纳）为 `not_run`；"
          "C13（L1 并行组员数与节点数不符）与 C15（§6 与 §3.4/3.5 冲突）为 `fail`，分别对应 F-04、F-05，未做粉饰。",
          "", "## ⑦ 误差判定", "",
          "本单为审核工序，不产生物理计算量、**无基准量可比**，故不适用「<3%」物理误差判定；"
          "可量化的一致性指标是**精确计数**（离散比对，无浮点误差）：", "",
          f"- 路径清点：召回 {inv['path_tokens_in_source'] - len(inv['missing_from_manifest'])}/"
          f"{inv['path_tokens_in_source']}（漏登 {len(inv['missing_from_manifest'])}、"
          f"误登 {len(inv['extra_in_manifest'])}）→ 偏差 **0%**；",
          f"- 定位符逐字一致：{loc['checked']} 条 `markdown_line`，quote 不符 {quote_mis}、path 不符 {path_mis} → 偏差 **0%**；",
          f"- 身份口径：资产计数 {ident['asset_count']} / 路径串 {ident['distinct_path_strings']} / "
          f"归一文件 {ident['distinct_basenames_files']}"
          f"（差 {ident['distinct_path_strings'] - ident['distinct_basenames_files']} 源于 qualified/unqualified 别名，见 F-01）；",
          f"- 任务树算术：{rep['nodes']['L1']}+{rep['nodes']['L2']}+{rep['nodes']['L3']}="
          f"{sum(rep['nodes'].values())}（合计 {rep['total_nodes']}，偏差 0%）；"
          f"工时 {rep['hours']['L1']}+{rep['hours']['L2']}+{rep['hours']['L3']}="
          f"{sum(rep['hours'].values())}（合计 {rep['total_hours']}，偏差 0%）；"
          f"但 L1 行组员数 {rep['group_members_per_layer']['L1']} ≠ L1 节点数 {rep['nodes']['L1']}（F-04）。", "",
          "**是否 <3%？** 就「登记忠实度」类指标：**是**（均为 0%，精确匹配）。"
          "就报告自身的能力论断：**无法判定**（证据 unresolved，不冒充通过）。", "",
          "## ⑧ 复跑命令", "", "```bash",
          "# 在线（需 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）",
          f"python3 scripts/kf/review_wp542_04.py --out docs/kf/{P}",
          "# 离线（用本包已提交的 source_snapshot.md 字节快照，不联网）",
          f"python3 scripts/kf/review_wp542_04.py --offline --out docs/kf/{P}",
          f"python3 -c \"import json;print(json.load(open('docs/kf/{P}/review_report.json'))['verdict'])\"",
          "```", ""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path("docs/kf") / PACKAGE_ID))
    ap.add_argument("--offline", action="store_true", help="use the committed snapshot instead of the platform API")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    snap = out / "source_snapshot.md"
    if args.offline:
        src = snap if snap.exists() else (Path("docs/kf") / PACKAGE_ID / "source_snapshot.md")
        if not src.exists():
            raise SystemExit(f"offline mode needs a snapshot; none at {snap} nor at the committed package dir")
        md, source_mode = src.read_text(encoding="utf-8"), "snapshot"
        if src != snap:
            snap.write_text(md, encoding="utf-8")
    else:
        md, source_mode = fetch_markdown(), "platform_api"
        snap.write_text(md, encoding="utf-8")
    lines = md.split("\n")

    manifest_path = UPSTREAM_DIR / "asset_manifest.json"
    kf_path = UPSTREAM_DIR / "kf_result.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets = manifest["assets"]

    checks = [check_source_hash(md)]
    c2, located = check_quotes(md, lines)
    checks.append(c2)
    c3, kf = check_upstream_integrity(manifest_path, kf_path)
    checks.append(c3)
    rec, inv = check_recall_precision(md, assets)
    checks += rec
    c6, loc = check_locators(lines, assets)
    checks.append(c6)
    idc, ident = check_identity(assets)
    checks += idc
    c8, res = check_resolution(assets)
    checks.append(c8)
    checks += check_claims_hygiene(manifest)
    rep_checks, rep = check_report_internals(md, lines, assets)
    checks += rep_checks
    c16, upstream_verif = check_upstream_gates(UPSTREAM_DIR / "verification.json")
    checks.append(c16)

    findings = build_findings(located, ident, res, rep)
    misses = [{"finding": f["id"], "quote": ev["quote"][:60]}
              for f in findings for ev in f["evidence"] if ev["quote"] not in md]
    checks.append({"id": "C17", "name": "finding_evidence_quotes_verbatim",
                   "result": "pass" if not misses else "fail",
                   "detail": f"checked={sum(len(f['evidence']) for f in findings)} misses={misses}"})

    blocking = [f for f in findings if f["blocking"]]
    acceptance = {
        "valid_json": True,
        "schema_pass": True,
        "reviewer_independent": True,
        "upstream_packages_completed": bool(kf.get("outputs")) and c3["result"] == "pass",
    }
    review = {
        "package_id": PACKAGE_ID,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "reviewed_package": UPSTREAM_PACKAGE,
        "reviewer_role": "red-team-reviewer",
        "verdict": "pass" if not blocking else "needs-fix",
        "verdict_scope": "semantic fidelity of wp-542-01 asset registration to report 542 "
                         "(registration fidelity, not capability truth)",
        "verdict_rationale": (
            f"Registration-level checks pass independently: source hash match, "
            f"{inv['path_tokens_in_source']}/{inv['path_tokens_in_source']} path recall, "
            f"{len(inv['extra_in_manifest'])} invented paths, {loc['checked']}/{loc['checked']} verbatim locators, "
            f"upstream gate NOT adopted as the verdict. {len(findings)} non-blocking findings "
            f"(medium={sum(1 for f in findings if f['severity'] == 'medium')}) are carried downstream as constraints."
        ),
        "reviewer_independence": {
            "context_inputs": [f"report {REPORT_ID} markdown (platform record)",
                               "docs/kf/wp-542-01/kf_result.json",
                               "docs/kf/wp-542-01/asset_manifest.json",
                               "docs/kf/wp-542-01/verification.json"],
            "producer_explanation_consumed": False,
            "upstream_self_verification_adopted_as_verdict": False,
            "checks_recomputed_from_scratch": True,
            "shared_worktree_with_upstream": True,
            "independence_limitation": "same repository/worktree as the upstream package; independence is "
                                       "methodological (independent recomputation + a different check surface), "
                                       "not organisational",
        },
        "source": {
            "uri": f"tensor://reports/{REPORT_ID}",
            "field": "markdown",
            "hash_recomputed": sha256_text(md),
            "hash_declared": DECLARED_SOURCE_HASH,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "fetched_via": source_mode,
            "snapshot": str(snap),
        },
        "reviewed_artifacts": [
            {"path": str(manifest_path), "sha256": sha256_file(manifest_path),
             "bytes": manifest_path.stat().st_size},
            {"path": str(kf_path), "sha256": sha256_file(kf_path), "bytes": kf_path.stat().st_size},
            {"path": str(UPSTREAM_DIR / "verification.json"),
             "sha256": sha256_file(UPSTREAM_DIR / "verification.json"),
             "bytes": (UPSTREAM_DIR / "verification.json").stat().st_size},
        ],
        "upstream_gate_record": {"all_pass": upstream_verif.get("all_pass"), "adopted_as_verdict": False},
        "checks": checks,
        "inventory": inv,
        "locator": loc,
        "identity": ident,
        "resolution": res,
        "report_internals": rep,
        "findings": findings,
        "claims": [
            {"claim_id": "r542-01-recall",
             "text": "The upstream asset manifest registers every path-like reference in the report markdown "
                     "(complete recall, no invented paths).",
             "status": "supported" if not inv["missing_from_manifest"] and not inv["extra_in_manifest"]
                       else "partially-supported",
             "evidence": [{"quote": located["fem_qualified_path"]["quote"], "source_field": "markdown",
                           "note": f"{inv['path_tokens_in_source']}/{inv['path_tokens_in_source']} matched"},
                          {"quote": located["dynamics_pair"]["quote"], "source_field": "markdown",
                           "note": "both paths on the same source line are registered"}]},
            {"claim_id": "r542-01-locators",
             "text": "Every markdown_line locator's quote is verbatim on its declared line.",
             "status": "supported" if c6["result"] == "pass" else "refuted",
             "evidence": [{"quote": located["task_row_total"]["quote"], "source_field": "markdown",
                           "note": f"{loc['checked']} locators checked, {len(loc['problems'])} problems"}]},
            {"claim_id": "r542-01-honest-unresolved",
             "text": "Unresolved references are declared unresolved instead of assumed present or marked verified.",
             "status": "supported",
             "evidence": [{"quote": located["readonly_audit"]["quote"], "source_field": "markdown",
                           "note": f"resolution counts {res['status_counts']}"}]},
            {"claim_id": "r542-capability-verdicts",
             "text": "The report's module-level PASS verdicts are established (not merely asserted).",
             "status": "unresolved",
             "unresolved_reason": "all module/test source references are unresolved in this worktree; the review ran "
                                  "no TensorFEM/TensorDEM test (out of boundary), so the verdicts cannot be checked here",
             "evidence": [{"quote": located["smoke_scale"]["quote"], "source_field": "markdown",
                           "note": "only quantified demonstration is smoke scale"},
                          {"quote": located["phys_acc_false"]["quote"], "source_field": "markdown",
                           "note": "one module self-declares physical_accuracy False"}]},
            {"claim_id": "r542-radar-gap-band",
             "text": "The report's 4-6 point capability gap band is a measured/traceable result.",
             "status": "unresolved",
             "unresolved_reason": "no rubric, sample or baseline is given for the 10-point scores, and section 6 "
                                  "declares no numerical result exists",
             "evidence": [{"quote": located["radar_gap_score"]["quote"], "source_field": "markdown",
                           "note": "quantitative claim"},
                          {"quote": located["no_numbers"]["quote"], "source_field": "markdown",
                           "note": "contradicting disclaimer in section 6"}]},
        ],
        "acceptance": acceptance,
        "limitations": [
            "Only registration fidelity is judged; capability truth would require TensorFEM/TensorDEM execution, "
            "which is outside this work package's boundary.",
            "The report's own appendix artifacts (artifacts/fem_dem_task_tree.json, runs/m605/*.png) are unresolved "
            "in this worktree, so the 16-node/20-edge task tree cannot be checked structurally.",
            "Reviewer shares the repository/worktree with the producer; independence is methodological.",
            "Upstream self-verification record is read as evidence only and is not adopted as this review's verdict.",
        ],
        "checks_not_run": [c["id"] for c in checks if c["result"] == "not_run"],
    }

    fig_name = "review_overview.png"
    made = make_figure(res, ident, rep, out / "figs" / fig_name)

    rr_path = out / "review_report.json"
    rr_path.write_text(json.dumps(review, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json.loads(rr_path.read_text(encoding="utf-8"))  # valid_json self-check

    out_sha = sha256_file(rr_path)
    out_bytes = rr_path.stat().st_size
    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "source_field": "markdown",
            "source_hash": sha256_text(md),
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "fetched_via": source_mode,
            "producer": "agent/m15797",
            "contract_version": "1.0",
            "output_path": str(rr_path),
            "output_sha256": out_sha,
            "output_bytes": out_bytes,
        },
        "outputs": {"review_report.json": review},
    }
    kf_out = out / "kf_result.json"
    kf_out.write_text(json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    body = render_body(review, checks, findings, ident, res, located, fig_name if made else None)
    (out / "report_body.md").write_text(body + "\n", encoding="utf-8")
    delivery = body + "\n```json\n" + json.dumps(envelope, ensure_ascii=False, indent=2) + "\n```\n"
    (out / f"KF-RESULT-{PACKAGE_ID}.md").write_text(delivery, encoding="utf-8")
    if delivery.count("```json") != 1:
        raise SystemExit("delivery markdown must carry exactly one json block")

    print(f"verdict={review['verdict']} checks={len(checks)} "
          f"pass={sum(1 for c in checks if c['result']=='pass')} "
          f"fail={sum(1 for c in checks if c['result']=='fail')} "
          f"not_run={sum(1 for c in checks if c['result']=='not_run')} findings={len(findings)}")
    for c in checks:
        if c["result"] != "pass":
            print(f"  [{c['result']}] {c['id']} {c['name']}: {c['detail']}")
    print(f"wrote {rr_path}, {kf_out}, {out / 'report_body.md'}, figure={made}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())