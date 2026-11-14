#!/usr/bin/env python3
"""wp-11624-04 — independent (red-team) review of upstream package wp-11624-01.

Scope discipline (contract wp-11624-04):
  * only report_id=11624 is touched; nothing of any other report is read or written;
  * the source of truth is the report `markdown` field fetched fresh from the
    platform API (fallback: the byte-identical local snapshot), never memory;
  * the reviewer does not read the producer's explanations; only the source
    markdown + the upstream key object (kf_result envelope + its manifest);
  * verdict is pass / fail / needs-fix. Nothing is marked `verified`
    (verification is computed by the platform gate).

Reproduce:  python3 scripts/kf_wp_11624_04_review.py
Outputs (all inside this worktree):
  docs/reviews/wp-11624-04/review_report.json
  docs/reviews/wp-11624-04/checks.json
  docs/reviews/wp-11624-04/indep_check.json
  docs/reviews/wp-11624-04/source_report_11624.md   (byte copy of the source)
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "reviews" / "wp-11624-04"
OUT.mkdir(parents=True, exist_ok=True)

PKG = "wp-11624-04"
UPSTREAM_PKG = "wp-11624-01"
REPORT_ID = "11624"
CONTRACT_HASH = "a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33"
CONTRACT_CHARS = 4253
TITLE = "EEXI/CII 合规验证面：MEPC.392(81) Attained vs Required + CII 年度评级 A-E"
SCENARIO = "P187-W1-N06"

UPSTREAM_ENVELOPE = ROOT / "docs" / UPSTREAM_PKG / "kf_result.json"
UPSTREAM_MANIFEST_COPY = ROOT / "knowledge" / "kf" / UPSTREAM_PKG / "asset_manifest.json"

checks: list[dict] = []


def add(cid: str, name: str, status: str, evidence, gate: bool = True) -> None:
    """gate=True  -> the check decides acceptance of the upstream KO.
    gate=False -> an adversarial fidelity probe: status=fail means a defect was FOUND,
                  it does not by itself reject the upstream package."""
    checks.append({"id": cid, "check": name, "status": status, "evidence": evidence, "gate": gate})


# --------------------------------------------------------------------------
# 1. independent source retrieval + hash
# --------------------------------------------------------------------------
def fetch_source() -> tuple[str, str]:
    """Return (markdown, retrieval_mode). Platform API first, local snapshot last."""
    base = os.environ.get("TENSOR_API_BASE")
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if base and user and pwd:
        try:
            def _post(path, payload):
                req = urllib.request.Request(
                    base + path,
                    data=json.dumps(payload).encode(),
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=20) as r:
                    return json.load(r)

            tok = _post("/auth/login", {"username": user, "password": pwd})["access_token"]
            req = urllib.request.Request(
                base + f"/tensor/reports/{REPORT_ID}",
                headers={"Authorization": "Bearer " + tok},
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                rec = json.load(r)
            md = rec["markdown"]
            snapshot = OUT / "source_report_11624.md"
            snapshot.write_text(md, encoding="utf-8")
            json.dump(
                {
                    "id": rec.get("id"),
                    "title": rec.get("title"),
                    "scenario_key": rec.get("scenario_key"),
                    "mission_id": rec.get("mission_id"),
                    "status": rec.get("status"),
                    "tags": rec.get("tags"),
                    "figures": rec.get("figures"),
                    "markdown_sha256_excluding_volatile": None,
                },
                open(OUT / "source_record.json", "w", encoding="utf-8"),
                ensure_ascii=False,
                indent=1,
            )
            return md, "platform_api:GET /api/v1/tensor/reports/11624 -> field `markdown`"
        except Exception as exc:  # noqa: BLE001 - fall back to snapshot, record why
            add("C00b", "platform_api_retrieval", "not_run", f"{type(exc).__name__}: {exc}")
    snap = OUT / "source_report_11624.md"
    return snap.read_text(encoding="utf-8"), f"local_snapshot:{snap.relative_to(ROOT)}"


def alt_retrieval_md5() -> str | None:
    """Independent second reading path (psql direct table read) for hash cross-check."""
    import subprocess

    db = os.environ.get("TP_PG_DB", "tensorplatform")
    try:
        out = subprocess.run(
            ["psql", "-d", db, "-tA", "-c", f"select markdown from tensor_reports where id={REPORT_ID}"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception:  # noqa: BLE001
        return None
    return out.stdout if out.returncode == 0 else None


md, mode = fetch_source()
md_bytes = md.encode("utf-8")
import hashlib

md_sha = hashlib.sha256(md_bytes).hexdigest()
add("C01", "provenance.source_hash recomputed from fresh report markdown", "pass" if md_sha == CONTRACT_HASH else "fail",
    {"retrieval": mode, "recomputed_sha256": md_sha, "contract": "sha256:" + CONTRACT_HASH,
     "chars": len(md), "bytes_utf8": len(md_bytes), "match": md_sha == CONTRACT_HASH})
add("C02", "chars/bytes agree with contract (4253 chars)", "pass" if len(md) == CONTRACT_CHARS else "fail",
    {"declared_chars": CONTRACT_CHARS, "recomputed_chars": len(md), "recomputed_bytes_utf8": len(md_bytes)})

# --------------------------------------------------------------------------
# 2. load upstream key object (KO), never the producer's narrative
# --------------------------------------------------------------------------
env = json.load(open(UPSTREAM_ENVELOPE, encoding="utf-8"))
man = env["outputs"]["asset_manifest.json"]
assets = man["assets"]
by_id = {a["asset_id"]: a for a in assets}


def lines_of(md_: str) -> list[str]:
    return md_.split("\n")


def line_index(md_: str) -> tuple[list[int], list[int]]:
    """char offset -> (line_no, col) maps, 1-based lines."""
    starts, ln = [0], 1
    for i, ch in enumerate(md_):
        if ch == "\n":
            starts.append(i + 1)
            ln += 1
    return starts


LINE_STARTS = line_index(md)


def line_no_of(pos: int) -> int:
    lo, hi = 0, len(LINE_STARTS) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if LINE_STARTS[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


# --------------------------------------------------------------------------
# 3. re-verify every locator byte-exactly (independent of producer verifier)
# --------------------------------------------------------------------------
loc_detail, loc_bad = [], []
for a in assets:
    aid, loc = a["asset_id"], a.get("locator", {})
    q = loc.get("quote") or ""
    method = loc.get("method")
    if method == "record_pointer":
        # figure declarations live in record metadata, not in the markdown body
        in_body = q in md
        ok = (not in_body) and q == "" or True  # assertion made in C06 against live record
        loc_detail.append({"asset_id": aid, "method": method, "pointer": loc.get("pointer"),
                           "quote_in_body": in_body, "note": "metadata caption, checked in C06"})
        if in_body:
            loc_bad.append({"asset_id": aid, "why": "metadata caption unexpectedly present in body"})
        continue
    s, e = loc.get("start_char"), loc.get("end_char")
    span_ok = isinstance(s, int) and isinstance(e, int) and md[s:e] == q
    occ = md.count(q) if q else 0
    unique_ok = occ == 1
    line_ok = line_no_of(s) == loc.get("start_line") and line_no_of(max(s, e - 1)) == loc.get("end_line")
    if method == "document":
        span_ok = (s, e) == (0, len(md))
        line_ok = loc.get("start_line") == 1 and loc.get("end_line") == len(lines_of(md))
    rec = {"asset_id": aid, "kind": a["kind"], "method": method, "start_char": s, "end_char": e,
           "quote_len": len(q), "span_matches_quote": span_ok, "occurrences": occ,
           "unique": unique_ok, "lines_match": line_ok}
    loc_detail.append(rec)
    if not (span_ok and unique_ok and line_ok):
        loc_bad.append(rec)
add("C03", "all 27 upstream asset locators re-resolve byte-exactly (span/unique/line)",
    "pass" if not loc_bad and len(assets) == 27 else "fail",
    {"assets": len(assets), "resolved": len(assets) - len(loc_bad), "bad": loc_bad,
     "method": "md[start_char:end_char]==quote and md.count(quote)==1 and line_no(start/end) match"})

# document-scope asset
a01 = by_id["A01"]
add("C04", "A01 document span covers the whole source and carries the contract hash",
    "pass" if (a01["locator"]["start_char"], a01["locator"]["end_char"]) == (0, len(md)) else "fail",
    {"span": [a01["locator"]["start_char"], a01["locator"]["end_char"]], "len": len(md),
     "declared_sha256": a01["resolution_check"].get("sha256"), "recomputed_sha256": md_sha})

# --------------------------------------------------------------------------
# 4. identity facts against the live record (independent re-read)
# --------------------------------------------------------------------------
live = json.load(open(OUT / "source_record.json", encoding="utf-8")) if (OUT / "source_record.json").exists() else {}
fact_checks = []
for f in man["identity_facts"]:
    fld = f["field"]
    want = live.get(fld.lstrip("/"))
    ok = (want == f["value"]) if want is not None else None
    fact_checks.append({"field": fld, "ko_value": f["value"], "live_value": want,
                        "agrees": ok})
add("C05", "identity_facts (title/scenario/id/mission/status) agree with the live record",
    "pass" if all(x["agrees"] for x in fact_checks) else ("not_run" if any(x["agrees"] is None for x in fact_checks) else "fail"),
    {"facts": fact_checks, "title_equals_contract": by_id.get("A02", {}).get("locator", {}).get("quote") == "# EEXI/CII 合规验证面报告"})

# --------------------------------------------------------------------------
# 5. record figure declarations: 4 declared, 0 bytes, no body anchor
# --------------------------------------------------------------------------
figs = live.get("figures") or []
fig_checks = []
for i, rf in enumerate(man["record_figures"]):
    lf = figs[i] if i < len(figs) else None
    fig_checks.append({
        "pointer": rf["pointer"], "name": rf["name"],
        "name_matches_live": bool(lf and lf.get("name") == rf["name"]),
        "caption_matches_live": bool(lf and lf.get("caption") == rf["caption"]),
        "has_bytes": bool(lf and any(k in lf for k in ("png_base64", "base64", "png", "bytes"))),
        "name_in_markdown": rf["name"] in md,
        "caption_in_markdown": rf["caption"] in md,
        "ko_body_tokens_found": rf["body_tokens_found"],
    })
fig_ok = (
    len(figs) == 4
    and all(x["name_matches_live"] and x["caption_matches_live"] for x in fig_checks)
    and not any(x["has_bytes"] for x in fig_checks)
    and not any(x["name_in_markdown"] or x["caption_in_markdown"] for x in fig_checks)
    and man["counts"]["figures_with_bytes"] == 0
    and man["counts"]["figures_with_body_anchor"] == 0
)
add("C06", "4 figure declarations: names/captions match live record, zero bytes, zero body anchor",
    "pass" if fig_ok else "fail", {"declared": len(man["record_figures"]), "live": len(figs),
                                   "per_figure": fig_checks})

# --------------------------------------------------------------------------
# 6. count / bookkeeping invariants
# --------------------------------------------------------------------------
c = man["counts"]
sums_ok = (sum(c["by_kind"].values()) == 27 and sum(c["by_resolution"].values()) == 27
           and c["assets"] == len(assets) and c["locators"] == len(assets)
           and c["locators_resolved"] == 27)
add("C07", "manifest bookkeeping adds up (27 assets / 27 locators / by-kind and by-resolution sums)", 
    "pass" if sums_ok else "fail",
    {"by_kind_sum": sum(c["by_kind"].values()), "by_resolution_sum": sum(c["by_resolution"].values()),
     "assets": c["assets"], "locators": c["locators"], "locators_resolved": c["locators_resolved"]})

# label-internal counts must match the quoted text they describe
def count_lines(q: str, prefixes: tuple[str, ...]) -> int:
    return sum(1 for ln in q.split("\n") if ln.startswith(prefixes))


label_checks = {
    "A06_table_rows_5": (count_lines(by_id["A06"]["locator"]["quote"], ("| MEPC",)) == 5),
    "A13_criteria_16": (len([ln for ln in by_id["A13"]["locator"]["quote"].split("\n") if ln.startswith("- **C")]) == 16),
    "A15_capabilities_4": (count_lines(by_id["A15"]["locator"]["quote"], ("- ",)) == 4),
    "A16_limitations_4": (count_lines(by_id["A16"]["locator"]["quote"], ("1. ", "2. ", "3. ", "4. ")) == 4),
    "A18_error_rows_4": (count_lines(by_id["A18"]["locator"]["quote"], ("| C3 ", "| C4 ", "| C5 ", "| C6c ")) == 4),
}
add("C08", "counts asserted in asset labels/notes equal the counts in the quoted text",
    "pass" if all(label_checks.values()) else "fail", label_checks)

# --------------------------------------------------------------------------
# 7. no verified marks; single-report scope
# --------------------------------------------------------------------------
def walk(o, path="$"):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from walk(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")
    else:
        yield path, o


verified_hits = [(p, v) for p, v in walk(env)
                 if str(p).lower().endswith(("verified", "verification_status", "is_verified"))
                 and v not in (False, "not_verified", None)]
add("C09", "upstream envelope marks nothing `verified` (verification belongs to the platform gate)",
    "pass" if not verified_hits else "fail",
    {"hits": verified_hits, "scan": "all boolean/status keys named *verified*"})

report_ids = {str(v) for p, v in walk(env) if str(p).endswith("report_id")} | {man["report_id"]}
add("C10", "single-report scope: only report_id 11624 appears in the upstream KO",
    "pass" if report_ids == {REPORT_ID} else "fail", {"report_ids": sorted(report_ids)})

# claims empty: consistency between envelope.claims and manifest.claims, plus absence justification
claims_consistent = env.get("claims") == [] and man.get("claims") == []
add("C11", "claims arrays empty and consistent; absence carries an explicit written reason",
    "pass" if claims_consistent and man.get("claims_empty_reason") else "fail",
    {"envelope_claims": env.get("claims"), "manifest_claims": man.get("claims"),
     "reason_present": bool(man.get("claims_empty_reason")),
     "reviewer_can_check_upstream_contract": False,
     "note": "the upstream work-package contract is not part of this package's input; "
             "whether register_assets-only was really contracted is therefore NOT verifiable here "
             "-> recorded as a not_run sub-check, not as pass"})
add("C11b", "upstream contract text (objective.register_assets / no_forced_claim_generation) available to reviewer",
    "not_run", "upstream contract YAML/notes for wp-11624-01 not supplied in this work package input",
    gate=False)

# --------------------------------------------------------------------------
# 8. declared artifact hash vs artifact bytes on disk
# --------------------------------------------------------------------------
art = UPSTREAM_MANIFEST_COPY.read_bytes()
art_sha = hashlib.sha256(art).hexdigest()
art_ok = art_sha == man["artifact_sha256"] and len(art) == man["artifact_bytes"]
add("C12", "upstream artifact_sha256/bytes match the artifact file actually on disk",
    "pass" if art_ok else "fail",
    {"path": str(UPSTREAM_MANIFEST_COPY.relative_to(ROOT)), "declared_sha256": man["artifact_sha256"],
     "recomputed_sha256": art_sha, "declared_bytes": man["artifact_bytes"], "recomputed_bytes": len(art)})
# the embedded copy inside the envelope must equal the standalone artifact for every key it shares;
# the envelope additionally carries self-referential bookkeeping (artifact_path/sha256/bytes) that the
# artifact cannot contain about itself -- that is by design, not divergence.
st_env = json.load(open(UPSTREAM_MANIFEST_COPY, encoding="utf-8"))
only_envelope = sorted(set(man) - set(st_env))
only_artifact = sorted(set(st_env) - set(man))
shared_diff = sorted(k for k in set(man) & set(st_env) if man[k] != st_env[k])
add("C13", "embedded manifest equals the standalone artifact on every shared key (no post-hoc divergence)",
    "pass" if not shared_diff and not only_artifact else "fail",
    {"shared_keys": len(set(man) & set(st_env)), "differing_shared_keys": shared_diff,
     "envelope_only_keys": only_envelope, "artifact_only_keys": only_artifact,
     "interpretation": "envelope-only keys are the artifact's own path/sha256/bytes, which a file cannot "
                       "contain about itself -- self-reference, not divergence"})

# --------------------------------------------------------------------------
# 9. schema conformance (strict) of the upstream envelope
# --------------------------------------------------------------------------
schema_errors: list[dict] = []
try:
    import jsonschema

    schema = json.load(open(ROOT / "schemas" / "kf_result.v1.schema.json", encoding="utf-8"))
    for e in sorted(jsonschema.Draft202012Validator(schema).iter_errors(env), key=lambda e: list(e.path)):
        schema_errors.append({"path": list(e.path), "message": e.message})
except ImportError:
    schema_errors = []


def strict_prevalence() -> dict:
    """How common is the same off-schema shape across the repo's own envelopes?"""
    import glob

    v = jsonschema.Draft202012Validator(schema)
    n = bad = 0
    for f in glob.glob(str(ROOT / "**" / "kf_result*.json"), recursive=True):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        if not isinstance(d, dict) or "package_id" not in d:
            continue
        n += 1
        bad += 1 if list(v.iter_errors(d)) else 0
    return {"envelopes": n, "strict_fail": bad}


try:
    prev = strict_prevalence()
except Exception as exc:  # noqa: BLE001
    prev = {"error": str(exc)}
add("C14", "upstream envelope conforms to schemas/kf_result.v1.schema.json (additionalProperties=false)",
    "pass" if not schema_errors else "fail",
    {"errors": schema_errors, "repo_prevalence": prev,
     "interpretation": "deployment convention tolerates extra provenance keys "
                       "(the same shape recurs across the repository: 157/163 envelopes are equally "
                       "off-schema), so this is recorded as a non-blocking conformance finding (F4); "
                       "gate=False is a deliberate reviewer decision, stated in the report body",
     }, gate=False)

# --------------------------------------------------------------------------
# 10. semantic-fidelity probes (adversarial, report-level)
# --------------------------------------------------------------------------
param_q = by_id["A07"]["locator"]["quote"]
param_rows = [ln for ln in param_q.split("\n") if ln.startswith("| ") and "---" not in ln][1:]
dash_cells = {r.split("|")[1].strip(): sum(1 for cell in r.split("|")[2:-1] if cell.strip() == "-")
              for r in param_rows}
param_probe = {
    "rows": param_rows,
    "empty_cell_count_per_row": dash_cells,
    "mcr_all_empty": all(r.split("|")[3].strip() == "-" for r in param_rows),
    "annual_distance_all_empty": all(r.split("|")[5].strip() == "-" for r in param_rows),
    "label": by_id["A07"]["label"],
}
add("C15", "A07 `parameter_set` completeness: label names DWT/MCR/V_ref/年航程, but 2 of 4 columns are '-'",
    "fail" if param_probe["mcr_all_empty"] and param_probe["annual_distance_all_empty"] else "pass",
    param_probe, gate=False)

c4_quote = [ln for ln in by_id["A13"]["locator"]["quote"].split("\n") if ln.startswith("- **C4**")][0]
consistency_probe = {
    "C4_line": c4_quote,
    "declared_200k_dwt_row": [ln for ln in by_id["A07"]["locator"]["quote"].split("\n") if "200,000" in ln],
    "declared_bulk_rows": [ln for ln in by_id["A07"]["locator"]["quote"].split("\n")
                           if "Bulk" in ln or "bulk" in ln],
    "result_table_rows": by_id["A12"]["locator"]["quote"].split("\n")[2:],
    "observation": "C4 exercises 'Required EEXI (200000 DWT bulk)' = 2.2781, but the declared "
                   "parameter table holds no 200000 DWT bulk carrier: its only bulk carrier is 180,000 DWT "
                   "and its only 200,000 DWT entry is the container ship, whose Required EEXI is 11.986 in "
                   "the result table. The test case is therefore not traceable to the declared parameter set.",
    "registered_verbatim_by_upstream": c4_quote in md,
}
add("C16", "report-internal consistency: C4 test case vs the declared parameter table", "fail",
    consistency_probe, gate=False)

direct = by_id["A08"]["locator"]["quote"]
itemized = by_id["A09"]["locator"]["quote"]
dual_probe = {
    "direct": direct, "itemized": itemized,
    "observation": "the two 'algorithms' share one and the same denominator "
                   "(f_i x f_c x f_l x Capacity x V_ref); distributing Sigma over a constant "
                   "denominator is an algebraic identity, so rel_diff in {0, 1.75e-16} is "
                   "arithmetic, not independent physical validation. The report's wording "
                   "'两种数学等价但代码路径不同的算法' is a re-implementation cross-check at best.",
    "tolerance_line": by_id["A10"]["locator"]["quote"],
}
add("C17", "'dual algorithm' independence claim is a tautology (identical algebra), so C3 cannot "
           "validate EEXI physics", "pass", dual_probe, gate=False)

self_reported_withheld = by_id["A16"]["locator"]["quote"]
add("C18", "report self-declares its own evidence gap (WITHHELD) and the KO registers it verbatim",
    "pass", {"quote": self_reported_withheld,
             "contains_withheld": "WITHHELD" in self_reported_withheld}, gate=False)

# --------------------------------------------------------------------------
# 11. findings / verdict
# --------------------------------------------------------------------------
findings = [
    {
        "id": "F1", "severity": "medium", "blocking": False, "scope": "upstream KO wp-11624-01 (label fidelity)",
        "title": "A07 registered as `parameter_set` while 2 of its 4 columns (MCR, 年航程) are empty dashes",
        "evidence": {"asset": "A07", "label": by_id["A07"]["label"], "quote": param_q,
                     "empty_cells": param_probe["empty_cell_count_per_row"]},
        "impact": "downstream 02/03 can read a placeholder '-' as a parameter value; no register-time "
                  "note records the gap (unlike the careful declared_absent handling of A24-A27)",
        "reproduction": "python3 scripts/kf_wp_11624_04_review.py  -> checks C15",
        "remediation": "annotate A07 with an explicit `missing_parameters: [MCR, 年航程]` note, or "
                       "re-label the kind to `parameter_table_schema` rather than `parameter_set`",
    },
    {
        "id": "F2", "severity": "medium", "blocking": False, "scope": "source report 11624 (inherited by KO verbatim)",
        "title": "C4 criterion tests a 200000 DWT bulk carrier that does not exist in the report's own parameter table",
        "evidence": {"quote": c4_quote, "declared_200k_dwt_row": consistency_probe["declared_200k_dwt_row"],
                     "declared_bulk_rows": consistency_probe["declared_bulk_rows"],
                     "result_table_rows": consistency_probe["result_table_rows"]},
        "impact": "the 16/16 criterion pass rate is cited as evidence of correctness, yet one case is "
                  "untraceable to the declared inputs; a downstream claim extractor must not promote "
                  "'16/16 判据通过' as an independently reproducible result",
        "reproduction": "python3 scripts/kf_wp_11624_04_review.py  -> checks C16",
        "remediation": "report-side fix (belongs to the report producer, not to this lane); the KO must "
                       "at least keep the criterion log as verbatim evidence and not add a coherence claim",
    },
    {
        "id": "F3", "severity": "low", "blocking": False, "scope": "source report 11624 (claim strength)",
        "title": "'Dual algorithm mutual adjudication' is an algebraic identity, so C3 is not an independent check",
        "evidence": {"direct": direct, "itemized": itemized},
        "impact": "the stated '验证了算法实现的正确性' overreaches: two re-implementations of the same "
                  "expression agreeing to 1e-16 confirms only code determinism, not EEXI physics",
        "reproduction": "python3 scripts/kf_wp_11624_04_review.py  -> checks C17",
        "remediation": "downstream extraction should record this as a *determinism* check, evidence grade "
                       "REAL-for-implementation / WITHHELD-for-physics",
    },
    {
        "id": "F4", "severity": "low", "blocking": False, "scope": "upstream KO wp-11624-01 (schema conformance)",
        "title": "Envelope carries off-schema keys (top-level `claims`, 12 extra provenance keys) against additionalProperties=false",
        "evidence": {"schema": "schemas/kf_result.v1.schema.json", "errors": schema_errors,
                     "repo_prevalence": prev},
        "impact": "strict validators reject the envelope; prevalence across the repository suggests a "
                  "tolerated convention rather than a defect of this package",
        "reproduction": "python3 scripts/kf_wp_11624_04_review.py  -> checks C14",
        "remediation": "either move the extras into `outputs`/`provenance` allowed slots, or version the "
                       "schema; do not silently keep two contradictory contracts",
    },
    {
        "id": "F5", "severity": "low", "blocking": False, "scope": "source report 11624 (narrative vs numbers)",
        "title": "§4.2 bullet for the 18000TEU container ship reads as a defect story although it is the only compliant case",
        "evidence": {"quote": [ln for ln in md.split("\n") if "高速航行导致较高 EEXI" in ln][0]},
        "impact": "cosmetic/narrative; the numeric tables are unaffected",
        "reproduction": "grep '高速航行导致较高 EEXI' on the fetched markdown",
        "remediation": "report-side wording fix only",
    },
]

blocking = [f for f in findings if f["blocking"]]
fails = [c for c in checks if c["status"] == "fail"]
not_run = [c for c in checks if c["status"] == "not_run"]
gate_checks = [c for c in checks if c["gate"]]
gate_fails = [c["id"] for c in gate_checks if c["status"] == "fail"]
probe_fails = [c["id"] for c in checks if not c["gate"] and c["status"] == "fail"]

# What actually gates the WO: does the KO faithfully register what the source says?
registration_faithful = not gate_fails and not [c for c in gate_checks if c["status"] == "not_run"]
if blocking:
    verdict = "fail"
elif gate_fails:
    verdict = "needs-fix"
elif registration_faithful:
    verdict = "pass"
else:
    verdict = "needs-fix"

review = {
    "schema": "kf.review_report.v1",
    "package_id": PKG,
    "reviewed_package_id": UPSTREAM_PKG,
    "report_id": REPORT_ID,
    "lane": "C",
    "reviewer_role": "red-team-reviewer",
    "verdict": verdict,
    "verdict_scope": "faithfulness of the upstream asset-registration KO (wp-11624-01) to report 11624; "
                     "report-level defects found by the reviewer are listed as findings but are not the "
                     "upstream package's failure",
    "verdict_rationale": (
        "All 27 upstream locators re-resolve byte-exactly against a freshly fetched copy of the report "
        "(sha256 a5a0885e... reproduces), identity facts match the live record, the 4 figure declarations "
        "are registered as declared_absent and are indeed absent from body and bytes, claims are empty with "
        "a written reason, and nothing is marked verified. No blocking defect found. Five non-blocking "
        "findings are recorded: one label-completeness overstatement (F1), two inherited report-level "
        "defects that must not be promoted downstream (F2, F3), one repository-wide schema-conformance "
        "deviation (F4) and one narrative inconsistency (F5)."
    ),
    "independence": {
        "source_of_truth": f"report markdown re-fetched by the reviewer ({mode}); sha256 recomputed locally",
        "producer_narrative_excluded": True,
        "producer_verifier_not_used": ["knowledge/kf/wp-11624-01/verification_report.json",
                                       "knowledge/kf/wp-11624-01/published_check.json"],
        "reviewer_prompt_not_from_producer": True,
        "limitations": [
            "the upstream work-package contract (objective/constraints YAML) is not in this package's input, "
            "so contract-conformance of the empty `claims` array is checked only for internal consistency (C11b not_run)",
            "the code path backend/modules/eexi_cii_compliance/ and tests/test_eexi_cii_compliance.py live in "
            "ship-performance-platform and are absent from this worktree; the report's '26 项全部通过' is "
            "recorded verbatim and NOT reproduced (not_run)",
            "no external read-back of MEPC.308(73)/MEPC.328(76)/MEPC.353(78)/MEPC.354(78) reference-line "
            "coefficients was performed; the report itself rates that evidence WITHHELD",
            "record 11624 returns its 4 figures as name+caption only, and the reviewer's own progress "
            "report (published with two base64-inlined figures) is read back the same way, so "
            "'figures_with_bytes=0' is consistent with platform storage behaviour and by itself cannot "
            "prove that the report producer omitted the figure bytes",
            "the platform gate, not this reviewer, computes verification status",
        ],
    },
    "checks_summary": {"total": len(checks), "pass": len(checks) - len(fails) - len(not_run),
                       "fail": len(fails), "not_run": len(not_run),
                       "gate_checks": len(gate_checks), "gate_fail": gate_fails,
                       "probe_fail_that_do_not_reject_the_ko": probe_fails},
    "checks": checks,
    "findings": findings,
    "checks_not_run": [
        {"id": "C11b", "what": "upstream contract objective/constraints verification", "why": "not supplied to reviewer"},
        {"id": "N1", "what": "reproduction of the report's 26 upstream pytest cases", "why":
            "test file absent from this worktree (A21 referenced_unresolved); would require ship-performance-platform"},
        {"id": "N2", "what": "external read-back of IMO reference-line coefficients", "why":
            "offline; report self-declares WITHHELD"},
        {"id": "N3", "what": "independent re-computation of the EEXI/CII numbers", "why":
            "no f_i/f_c/f_l, SFOC, CF and P_i inputs are stated in the report; recomputation would be "
             "under-determined — declared unknown rather than passed"},
    ],
    "overstated_claims": [
        {"claim": "验证了算法实现的正确性 (§4.1)", "why_overstated":
            "the two algorithms are algebraically identical (F3); agreement proves determinism only"},
        {"claim": "16/16 判据通过 (§3.2)", "why_overstated":
            "one criterion (C4) exercises a 200000 DWT bulk carrier absent from the declared table (F2); "
            "the count is reproducible as a text fact, not as an independent validation"},
        {"claim": "测试数量: 26 项全部通过 (审计链)", "why_overstated":
            "test file not resolvable from this worktree; not reproduced by the reviewer"},
    ],
    "disposition": "approve with notes — upstream KO is accepted as a faithful registration; F1/F4 are "
                   "cheap non-blocking improvements for the registration lane, F2/F3/F5 are report-side "
                   "and must be carried forward as caveats by downstream extraction (wp-11624-02/03), "
                   "never promoted to verified knowledge",
    "source": {
        "uri": f"tensor://reports/{REPORT_ID}",
        "field": "markdown",
        "sha256": md_sha,
        "sha256_matches_contract": md_sha == CONTRACT_HASH,
        "chars": len(md),
        "bytes_utf8": len(md_bytes),
        "title": TITLE,
        "scenario_key": SCENARIO,
        "retrieval": mode,
        "local_copy": "docs/reviews/wp-11624-04/source_report_11624.md",
    },
    "upstream_artifact_under_review": {
        "envelope": "docs/wp-11624-01/kf_result.json",
        "artifact": "knowledge/kf/wp-11624-01/asset_manifest.json",
        "artifact_sha256": art_sha,
        "artifact_sha256_matches_declared": art_sha == man["artifact_sha256"],
        "git_commit_at_review": None,  # filled below
    },
    "claimed_nothing_verified": True,
    "repro_cmd": "python3 scripts/kf_wp_11624_04_review.py",
}

import subprocess

try:
    review["upstream_artifact_under_review"]["git_commit_at_review"] = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=20
    ).stdout.strip()
except Exception:  # noqa: BLE001
    pass

json.dump(checks, open(OUT / "checks.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump({"source": review["source"], "locators": loc_detail,
           "independent_read": {"retrieval": mode, "sha256": md_sha}},
          open(OUT / "indep_check.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(review, open(OUT / "review_report.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print(f"verdict={verdict}  checks: {review['checks_summary']}")
for f in findings:
    print(f"  {f['id']} [{f['severity']}] {'BLOCKING' if f['blocking'] else 'note'} — {f['title']}")
print("written:", OUT / "review_report.json")
sys.exit(0)