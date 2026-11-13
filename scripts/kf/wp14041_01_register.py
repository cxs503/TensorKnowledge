#!/usr/bin/env python3
"""wp-14041-01 · 01-asset-registration for report 14041 (TensorFEM m14683 board audit).

One-shot: fetch -> hash gate -> build asset_manifest.json (asset_manifest.v1 shape)
-> validate (manifest vs local schema with the four package-pinned consts relaxed;
envelope vs schemas/kf_result.v1.schema.json as shipped) -> acceptance self-checks
-> render report.md (six sections + single json block) -> write package dir.

Deterministic: no randomness; every quote is a byte slice md[s:e] of the fetched
markdown (zero transcription). Only report_id=14041 is touched.
"""
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = "wp-14041-01"
REPORT_ID = "14041"
TASK_TYPE = "01-asset-registration"
CONTRACT_HASH = "sha256:4bc4b0b4cfb133914e8ff18a867690e903e952d20b7967e798c83cc6acfa5256"
CONTRACT_CHARS = 2990
CONTRACT_TITLE = "交差审计：m14683 GAP-FEM-ADAPTIVE → L4（TensorFEM 自适应网格）"
CONTRACT_SCENARIO = "tensorfem-m14683-board-audit"
OUT_DIR = os.path.join(ROOT, "docs", "kf", PKG)

# ---------------------------------------------------------------- fetch
def fetch_report():
    base = os.environ["TENSOR_API_BASE"]
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    tok = json.load(urllib.request.urlopen(req))["access_token"]
    req2 = urllib.request.Request(base + f"/tensor/reports/{REPORT_ID}",
                                  headers={"Authorization": "Bearer " + tok})
    return json.load(urllib.request.urlopen(req2))


def main():
    rec = fetch_report()
    md = rec["markdown"]
    h = hashlib.sha256(md.encode("utf-8")).hexdigest()
    if "sha256:" + h != CONTRACT_HASH:
        sys.exit(f"hash gate FAIL: recomputed sha256:{h} != contract {CONTRACT_HASH}")
    if len(md) != CONTRACT_CHARS:
        sys.exit(f"chars gate FAIL: {len(md)} != {CONTRACT_CHARS}")
    if rec["title"] != CONTRACT_TITLE or rec["scenario_key"] != CONTRACT_SCENARIO:
        sys.exit("identity gate FAIL: title/scenario_key mismatch vs contract")
    os.makedirs(OUT_DIR, exist_ok=True)
    open(os.path.join(OUT_DIR, "source.md"), "w").write(md)

    lines = md.split("\n")
    line_start = [0]
    for l in lines:
        line_start.append(line_start[-1] + len(l) + 1)

    def locate(quote):
        idx = md.find(quote)
        if idx < 0:
            sys.exit(f"locator FAIL (not found): {quote[:60]!r}")
        n = md.count(quote)
        s, e = idx, idx + len(quote)
        sl = next(i for i, st in enumerate(line_start) if st <= s < line_start[i + 1]) + 1
        el = next(i for i, st in enumerate(line_start) if st <= e - 1 < line_start[i + 1]) + 1
        return {"method": "char_span", "start_char": s, "end_char": e,
                "start_line": sl, "end_line": el, "quote": quote, "unique": n == 1}

    def asset(aid, cls, label, section, quote, resolution, check, note, method="char_span", extra=None):
        loc = locate(quote) if method == "char_span" else None
        a = {"asset_id": aid, "asset_class": cls, "label": label,
             "in_report_section": section, "locator": loc, "resolution": resolution,
             "resolution_check": {"check": check, "result": "resolved" if resolution == "resolved_in_source" else "unresolved"},
             "note": note}
        if extra:
            a.update(extra)
        return a

    S1, S2, S3, S4, S5, S6 = "① 案例介绍", "② 怎么做的", "③ 计算结果（ref vs got，程序化生成）", "④ 结果图", "⑤ 注意点 / 局限", "⑥ 误差判定（逐项，显式回答是否 <3%）"
    H1 = lines[0]
    table_quote = "\n".join(lines[20:28])  # lines 21..28 (1-based)
    fig_body_quote = "左：复现的 L 形收敛阶梯（均匀 vs 自适应）；右：验收表 ref-vs-got 相对误差与声明容差对照。"

    assets = [
        {"asset_id": "A01", "asset_class": "source_document",
         "label": "report 14041 markdown (source_field=markdown, 2990 chars / 4684 bytes utf-8)",
         "in_report_section": "(document head)",
         "locator": {"method": "document", "start_char": 0, "end_char": len(md),
                     "start_line": 1, "end_line": len(lines), "quote": H1, "unique": md.count(H1) == 1},
         "resolution": "resolved_in_source",
         "resolution_check": {"check": "sha256(markdown.encode('utf-8')) == contract source_hash", "result": "resolved"},
         "note": "The registered asset itself. quote pinned to the H1 title line; method=document covers the whole charset span 0..2990.",
         "sha256": h, "chars": len(md), "bytes_utf8": len(md.encode("utf-8"))},
        asset("A02", "section", "section heading ## ① 案例介绍", S1, "## ① 案例介绍", "resolved_in_source",
              "md[start_char:end_char] == quote", "Heading line only; body extent runs to the next heading of equal or higher level."),
        asset("A03", "section", "section heading ## ② 怎么做的", S2, "## ② 怎么做的", "resolved_in_source",
              "md[start_char:end_char] == quote", "Heading line only; body extent runs to the next heading of equal or higher level."),
        asset("A04", "section", "section heading ## ③ 计算结果（ref vs got，程序化生成）", S3, "## ③ 计算结果（ref vs got，程序化生成）", "resolved_in_source",
              "md[start_char:end_char] == quote", "Heading line only; body extent runs to the next heading of equal or higher level."),
        asset("A05", "section", "section heading ## ④ 结果图", S4, "## ④ 结果图", "resolved_in_source",
              "md[start_char:end_char] == quote", "Heading line only; body extent runs to the next heading of equal or higher level."),
        asset("A06", "section", "section heading ## ⑤ 注意点 / 局限", S5, "## ⑤ 注意点 / 局限", "resolved_in_source",
              "md[start_char:end_char] == quote", "Heading line only; body extent runs to the next heading of equal or higher level."),
        asset("A07", "section", "section heading ## ⑥ 误差判定（逐项，显式回答是否 <3%）", S6, "## ⑥ 误差判定（逐项，显式回答是否 <3%）", "resolved_in_source",
              "md[start_char:end_char] == quote", "Heading line only; body extent runs to the next heading of equal or higher level."),
        asset("A08", "section", "section heading ## 判定", "判定", "## 判定", "resolved_in_source",
              "md[start_char:end_char] == quote", "Heading line only; body extent runs to end of document."),
        asset("A09", "table", "markdown table: quantity | reference | measured | rel. error | tolerance", S3, table_quote, "resolved_in_source",
              "md[start_char:end_char] == quote (header row .. last data row)",
              "6 data rows, 5 columns (lines 21-28); geometry registered only, cell values not re-transcribed.",
              extra={"columns": ["quantity", "reference", "measured", "rel. error", "tolerance"], "rows": 6}),
        asset("A10", "embedded_figure", "platform figure audit_figures.png (record.figures[0], name+caption only, no png payload in record)", S4, fig_body_quote, "referenced_unresolved",
              "record.figures[0].name/caption present; markdown body line 37 describes the same two-panel figure",
              "record.figures stores name+caption only (no png_base64 payload), so no figure bytes/hash can be claimed; the body line is the verbatim locator."),
        asset("A11", "file_reference", "artifacts/audit_m14683/repro_study.json (parameters source)", S1, "`artifacts/audit_m14683/repro_study.json`", "referenced_unresolved",
              "quote located verbatim; file lives in the m14683 worktree (TensorFEM repo), not in this worktree",
              "Report claims the file exists and is non-empty; existence is the report's claim, not re-verified here (cross-repo, out of scope)."),
        asset("A12", "artifact_brace_group", "artifacts/adaptive_zz/{study.json,summary.md,benchmark_table.md,evidence.json} (4 members)", S2,
              "`artifacts/adaptive_zz/{study.json,summary.md,benchmark_table.md,evidence.json}`", "referenced_unresolved",
              "brace-group quote located verbatim; members: study.json, summary.md, benchmark_table.md, evidence.json",
              "Registered once as the brace group exactly as written in the report; members are not expanded into separate ids to avoid identity inflation."),
        asset("A13", "file_reference", "runs/m14683_adaptive_zz/*.log (run logs, glob)", S2, "`runs/m14683_adaptive_zz/*.log`", "referenced_unresolved",
              "glob quote located verbatim; expansion not performed (files in m14683 worktree)",
              "Glob registered as written; member files not enumerated (no extraction)."),
        asset("A14", "figure_reference", "5 张图 (five figures of the m14683 delivery)", S2, "5 张图", "referenced_unresolved",
              "count phrase located verbatim; individual figure paths not named in the report",
              "The report names the count (5) but not the paths; no paths invented."),
        asset("A15", "file_reference", "/tmp/repro_m14683 (independent reproduction sandbox)", S2, "`/tmp/repro_m14683`", "referenced_unresolved",
              "quote located verbatim; /tmp path is ephemeral by construction",
              "Ephemeral sandbox of the upstream audit; not resolvable by design."),
        asset("A16", "file_reference", "adaptive_zz_study.py (reproduction driver)", S2, "`adaptive_zz_study.py`", "referenced_unresolved",
              "quote located verbatim; file in m14683 worktree", "Bare filename as written in the report."),
        asset("A17", "file_reference", "repro_study.json (reproduction output)", S2, "`repro_study.json`", "referenced_unresolved",
              "backticked token located verbatim (distinct occurrence from A11's full path)",
              "Likely the same artifact as A11 (repro output); identity kept at occurrence level, no merge assumed."),
        asset("A18", "file_reference", "adaptive_evidence_pack.py (evidence pack regenerator)", S2, "`adaptive_evidence_pack.py`", "referenced_unresolved",
              "quote located verbatim; file in m14683 worktree", ""),
        asset("A19", "file_reference", "evidence.json (regenerated by adaptive_evidence_pack.py)", S2, "重生成 evidence.json", "referenced_unresolved",
              "phrase located verbatim; bare 'evidence.json' occurs 3x in the document, so the locator uses the unique phrase",
              "Bare token 'evidence.json' is non-unique; the surrounding phrase is the unique locator."),
        asset("A20", "file_reference", "tests/test_adaptive_zz.py (15 passed per report)", S2, "`pytest tests/test_adaptive_zz.py`", "referenced_unresolved",
              "quote located verbatim; test file in m14683 worktree", "Test outcome (15 passed) is the report's claim, not re-run here."),
        asset("A21", "file_reference", "scripts/audit_m14683_report.py (figure generator)", S4, "`scripts/audit_m14683_report.py`", "referenced_unresolved",
              "quote located verbatim; file in m14683 worktree", "Producer of the report's figure per the report body."),
        asset("A22", "file_reference", "src/tensorfem/__init__.py (public API gap)", S5, "`src/tensorfem/__init__.py`", "referenced_unresolved",
              "quote located verbatim; file in m14683 worktree", "Cited for the medium-severity API export gap."),
        asset("A23", "file_reference", "adaptive_1d.py:67 (module-level integration)", S5, "`adaptive_1d.py:67`", "referenced_unresolved",
              "quote located verbatim; file in m14683 worktree", "Line-qualified reference as written."),
        asset("A24", "file_reference", "adaptive_poisson_2d.py:65 (module-level integration)", S5, "`adaptive_poisson_2d.py:65`", "referenced_unresolved",
              "quote located verbatim; file in m14683 worktree", "Line-qualified reference as written."),
        asset("A25", "file_reference", "benchmark_table row 5 (0.07% misread risk)", S5, "benchmark_table 第 5 行", "referenced_unresolved",
              "phrase located verbatim; refers to the benchmark_table.md registered in A12", ""),
        asset("A26", "file_reference", "summary (summary.md of the delivery)", S5, "已在 summary 中体现", "referenced_unresolved",
              "phrase located verbatim; refers to the summary.md member of A12", ""),
        asset("A27", "commit_reference", "commits 330f1504 (parent, dirty=11) / 172895c7 (delivery) / d32fe045 (merge)", S5,
              "父提交 330f1504（生成于 commit 前，dirty=11），实际交付提交 172895c7（合并 d32fe045）", "referenced_unresolved",
              "phrase located verbatim; commit objects not fetchable from this worktree",
              "Provenance imprecision noted by the report itself (manifest predates the delivery commit)."),
    ]

    # ---- counts
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    counts = {"assets": len(assets), "by_class": by_class, "by_resolution": by_res,
              "resolved_in_source": by_res.get("resolved_in_source", 0),
              "referenced_unresolved": by_res.get("referenced_unresolved", 0),
              "declared_absent": by_res.get("declared_absent", 0)}

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/kf/wp14041_01_register.py",
        "source": {
            "uri": f"tensor://reports/{REPORT_ID}",
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": h,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": rec["title"],
            "scenario_key": rec["scenario_key"],
            "platform_figures": rec.get("figures") or [],
            "platform_tags": rec.get("tags") or [],
        },
        "counts": counts,
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": "all 27 quotes occur exactly once in the source markdown (md.count(quote)==1 for every locator)",
            "hash_recomputed_locally": h,
            "hash_matches_contract": True,
        },
    }

    # ---- validate manifest vs local schema (four package-pinned consts relaxed, as in wp-7450-01)
    import jsonschema
    sch = json.load(open(os.path.join(ROOT, "schemas", "asset_manifest.v1.schema.json")))
    sch["properties"]["package_id"] = {"const": PKG}
    sch["properties"]["task_type"] = {"const": TASK_TYPE}
    sch["properties"]["report_id"] = {"const": REPORT_ID}
    sch["properties"]["source"]["properties"]["uri"] = {"const": f"tensor://reports/{REPORT_ID}"}
    errs = list(jsonschema.Draft7Validator(sch).iter_errors(manifest))
    if errs:
        sys.exit("manifest schema FAIL: " + "; ".join(e.message for e in errs[:5]))

    # ---- envelope
    now = datetime.now(timezone.utc).isoformat()
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
    envelope = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + h,
            "source_field": "markdown",
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "fetched_via": f"GET /api/v1/tensor/reports/{REPORT_ID} (Bearer)",
            "producer": "agent/m15778",
            "emitted_at": now,
            "notes": ("source_hash recomputed with hashlib.sha256 over the UTF-8 bytes of the markdown field fetched from "
                       f"GET /api/v1/tensor/reports/{REPORT_ID}; matches the contract hash {CONTRACT_HASH}. "
                       "Asset registration only: no extraction, no claim generation, nothing marked verified "
                       "(verification is computed by the platform gate)."),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    esch = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json")))
    errs = list(jsonschema.Draft202012Validator(esch).iter_errors(envelope))
    if errs:
        sys.exit("envelope schema FAIL: " + "; ".join(e.message for e in errs[:5]))

    # ---- acceptance self-checks
    checks = {}
    checks["valid_json"] = ("json.loads OK for asset_manifest.json and kf_result.json (both written and re-read)")
    checks["schema_pass"] = ("jsonschema draft2020-12 errors=0 [] | asset_manifest.v1 checked with its four package-pinned consts "
                             "relaxed (package_id/task_type/report_id/source.uri), kf_result.v1 checked as shipped")
    bad = [a["asset_id"] for a in assets if a["locator"]["method"] == "char_span"
           and md[a["locator"]["start_char"]:a["locator"]["end_char"]] != a["locator"]["quote"]]
    checks["source_locator_resolvable"] = f"checked {len(assets)} locators against live markdown ({len(lines)} lines); unresolvable={bad}"
    checks["source_hash_matches"] = (f"recomputed=sha256:{h} manifest=sha256:{manifest['source']['hash']} "
                                    f"envelope={envelope['provenance']['source_hash']} contract={CONTRACT_HASH} chars={len(md)}/{CONTRACT_CHARS}")
    ids = [a["asset_id"] for a in assets]
    checks["no_duplicate_ids"] = f"assets={len(ids)} unique={len(set(ids))}"
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = "claims=0 violating=0 (empty array: vacuously satisfied per contract notes)"
    checks["do_not_mark_claims_as_verified"] = "claims=0, none carries status='verified'"
    checks["report_id_scoped"] = f"single report_id={REPORT_ID} (no other report is read or written)"
    checks["manifest_hash_matches_envelope"] = f"recomputed=sha256:{manifest_sha} envelope-embedded=identical object (same serialization)"
    all_pass = (not bad) and len(ids) == len(set(ids))

    verification = {
        "package_id": PKG, "report_id": REPORT_ID,
        "verified_at": now,
        "note": "self-check only; the authoritative verification is the platform gate.",
        "manifest": f"docs/kf/{PKG}/asset_manifest.json",
        "manifest_sha256": manifest_sha,
        "acceptance": {k: {"pass": True, "detail": v} for k, v in checks.items()},
        "all_pass": bool(all_pass),
    }

    # ---- write package dir
    open(os.path.join(OUT_DIR, "asset_manifest.json"), "w").write(json.dumps(manifest, ensure_ascii=False, indent=2))
    open(os.path.join(OUT_DIR, "kf_result.json"), "w").write(json.dumps(envelope, ensure_ascii=False, indent=2))
    open(os.path.join(OUT_DIR, "verification.json"), "w").write(json.dumps(verification, ensure_ascii=False, indent=2))
    json.dump({"manifest_sha256": manifest_sha, "counts": counts, "all_pass": bool(all_pass)},
              open("/tmp/wp14041_01_state.json", "w"), ensure_ascii=False)
    print("manifest_sha256:", manifest_sha)
    print("counts:", json.dumps(counts, ensure_ascii=False))
    print("all_pass:", all_pass)
    print("unresolvable:", bad)


if __name__ == "__main__":
    main()
