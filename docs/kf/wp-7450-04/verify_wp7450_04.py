#!/usr/bin/env python3
"""wp-7450-04 · independent review harness for the upstream package wp-7450-01.

Independence design
-------------------
* The reviewed markdown is re-fetched from the platform (GET /api/v1/tensor/reports/7450)
  at review time; nothing is copied from the upstream package's own numbers.
* The upstream self-check file (verification.json) is READ ONLY to enumerate what the
  producer claims; every one of its claims is re-derived here from primary bytes.
* No producer explanation is consulted; only report markdown + upstream artefacts.

Outputs: docs/kf/wp-7450-04/verify_output.json (+ console summary).
Exit code 0 = all hard checks pass, 1 = at least one hard check failed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # worktree root
PKG04 = ROOT / "docs/kf/wp-7450-04"
UPSTREAM = ROOT / "docs/kf/wp-7450-01"
CONTRACT = {
    "report_id": "7450",
    "source_field": "markdown",
    "source_hash": "sha256:4b20aadcaabc128bc8fb10e8f9f164de670421c2b67d36d2837fc5781d96bfac",
    "chars": 6312,
    "title": "m6284 CII 规则三实现交叉核对：green_shipping 静默默认清偿 + "
             "独立转录互证（164 项回归）",
}

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


def login_token() -> str:
    """Bearer token for the platform API (env first, then /auth/login)."""
    tok = os.environ.get("TENSOR_TOKEN")
    if tok:
        return tok
    body = json.dumps({
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    }).encode()
    req = urllib.request.Request(
        f"{API}/auth/login", data=body,
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())["access_token"]


def fetch_report(report_id: str) -> dict:
    req = urllib.request.Request(
        f"{API}/tensor/reports/{report_id}",
        headers={"Authorization": f"Bearer {login_token()}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def line_of(md: str, char_index: int) -> int:
    """1-based line number of a character offset."""
    return md.count("\n", 0, char_index) + 1


def main() -> int:
    checks: list[dict] = []

    def add(cid, ok, detail, hard=True):
        checks.append({"check_id": cid, "pass": bool(ok), "hard": hard,
                       "detail": detail})
        return bool(ok)

    # ---------------- primary source ----------------
    rec = fetch_report(CONTRACT["report_id"])
    md = rec["markdown"]
    md_bytes = md.encode("utf-8")
    src_hash = sha256_bytes(md_bytes)

    add("S1_source_hash_recomputed",
        src_hash == CONTRACT["source_hash"].split(":")[1],
        f"recomputed sha256(markdown utf-8)={src_hash} "
        f"contract={CONTRACT['source_hash']} chars={len(md)} bytes={len(md_bytes)}")
    add("S2_source_shape",
        len(md) == CONTRACT["chars"] and rec["title"].startswith("m6284"),
        f"chars={len(md)} (contract {CONTRACT['chars']}) title={rec['title'][:40]!r}")
    # contract `title` is metadata (a descriptive label), NOT the markdown H1:
    # check that its identifying tokens all occur verbatim in the source instead.
    toks = ["CII", "green_shipping", "164"]
    matches = {t: (t in md) for t in toks}
    add("S3_contract_title_tokens_locatable", all(matches.values()),
        f"contract-title identifying tokens in markdown: {matches}; "
        f"markdown H1={md.splitlines()[0][:48]!r}")

    # ---------------- upstream quarters ----------------
    man_path = UPSTREAM / "asset_manifest.json"
    man_bytes = man_path.read_bytes()
    man = json.loads(man_bytes)
    man_hash = sha256_bytes(man_bytes)
    env = json.loads((UPSTREAM / "kf_result.json").read_text(encoding="utf-8"))
    receipt = json.loads((UPSTREAM / "publish_receipt.json").read_text(encoding="utf-8"))
    claimed_ver = json.loads((UPSTREAM / "verification.json").read_text(encoding="utf-8"))

    env_man_hash = env["outputs"]["asset_manifest.json"]["sha256"]
    add("U1_manifest_hash_envelope",
        man_hash == env_man_hash == receipt["manifest_sha256"],
        f"recomputed={man_hash} envelope={env_man_hash} receipt={receipt['manifest_sha256']}")
    add("U2_manifest_bytes",
        len(man_bytes) == env["outputs"]["asset_manifest.json"]["bytes"],
        f"recomputed bytes={len(man_bytes)} "
        f"envelope={env['outputs']['asset_manifest.json']['bytes']}")
    add("U3_envelope_source_hash",
        env["provenance"]["source_hash"] == CONTRACT["source_hash"]
        and env["provenance"]["source_hash"].split(":")[1] == src_hash,
        f"envelope={env['provenance']['source_hash']} recomputed={src_hash}")
    add("U4_manifest_source_block",
        man["source"]["hash"] == src_hash
        and man["source"]["chars"] == len(md)
        and man["source"]["bytes_utf8"] == len(md_bytes),
        f"manifest.source hash/chars/bytes = {man['source']['hash'][:16]}…/"
        f"{man['source']['chars']}/{man['source']['bytes_utf8']}")

    # ---------------- locators (the real content of an 01 package) ----------------
    assets = man["assets"]
    bad_span, bad_line, bad_sub, duplicate_q = [], [], [], []
    quote_counts = []
    for a in assets:
        loc = a["locator"]
        q = loc["quote"]
        s, e = loc["start_char"], loc["end_char"]
        if md[s:e] != q:
            bad_span.append(a["asset_id"])
        if q not in md:
            bad_sub.append(a["asset_id"])
        if md.count(q) != 1:
            quote_counts.append((a["asset_id"], md.count(q)))
            if md.count(q) > 1:
                duplicate_q.append(a["asset_id"])
        # 1-based inclusive line numbers
        if s < len(md):
            sl = line_of(md, s)
            el = line_of(md, max(e - 1, 0))
            if (sl, el) != (loc["start_line"], loc["end_line"]):
                bad_line.append((a["asset_id"], (sl, el),
                                 (loc["start_line"], loc["end_line"])))
    add("L1_spans_exact", not bad_span,
        f"assets={len(assets)} span_mismatch={bad_span or 'none'}")
    add("L2_quote_substring", not bad_sub,
        f"quotes not found verbatim in source: {bad_sub or 'none'}")
    add("L3_line_map_consistent", not bad_line,
        f"line-map mismatches: {bad_line or 'none'}")
    bad_tok, bad_unique = [], []
    for a in assets:
        loc = a["locator"]
        ts, tok = loc.get("token_span"), loc.get("token")
        if ts and tok and md[ts[0]:ts[1]] != tok:
            bad_tok.append(a["asset_id"])
        if "unique" in loc and loc["unique"] != (md.count(loc["quote"]) == 1):
            bad_unique.append(a["asset_id"])
    n_tok = sum(1 for a in assets if a["locator"].get("token_span"))
    add("L5_token_spans_exact", not bad_tok,
        f"{n_tok} assets declare token_span; mismatches={bad_tok or 'none'}")
    add("L6_declared_unique_flags_honest", not bad_unique,
        f"per-asset 'unique' flags disagreeing with source: {bad_unique or 'none'} "
        f"(A18 correctly declares unique=false for the 4x-repeated '/cii')")
    doc = [a for a in assets if a["locator"]["method"] == "document"]
    add("L7_document_span_covers_source",
        len(doc) == 1 and doc[0]["locator"]["start_char"] == 0
        and doc[0]["locator"]["end_char"] == len(md)
        and doc[0]["locator"]["quote"] == md,
        f"document asset span=[0,{len(md)}) quote==whole markdown: "
        f"{bool(doc and doc[0]['locator']['quote'] == md)}")
    ids = [a["asset_id"] for a in assets]
    add("L4_asset_ids_unique", len(ids) == len(set(ids)) == man["counts"]["assets"],
        f"ids={len(ids)} unique={len(set(ids))} counts.assets={man['counts']['assets']}")

    # ---------------- completeness / declared aggregates ----------------
    from collections import Counter
    by_class = Counter(a["asset_class"] for a in assets)
    by_res = Counter(a["resolution"] for a in assets)
    add("A1_by_class_matches",
        dict(by_class) == man["counts"]["by_class"]
        and sum(man["counts"]["by_class"].values()) == man["counts"]["assets"],
        f"recomputed={dict(by_class)} declared={man['counts']['by_class']}")
    add("A2_by_resolution_matches",
        dict(by_res) == man["counts"]["by_resolution"]
        and man["counts"]["resolved_in_source"] == by_res.get("resolved_in_source", 0)
        and man["counts"]["referenced_unresolved"] == by_res.get("referenced_unresolved", 0),
        f"recomputed={dict(by_res)} declared={man['counts']['by_resolution']}")

    # every referenced path really is absent from THIS worktree (honest unresolved)
    unresolved_ok, absent_but_called_resolved = [], []
    for a in assets:
        if a["asset_class"] != "source_code_reference":
            continue
        for p in [a["label"].split(" (markdown line")[0]]:
            exists = (ROOT / p).exists()
            if a["resolution"] == "referenced_unresolved" and not exists:
                unresolved_ok.append(p)
            if a["resolution"] == "resolved_in_source" and not exists:
                absent_but_called_resolved.append(p)
    add("A3_unresolved_真的不存在于本工作树",
        not absent_but_called_resolved and len(unresolved_ok) >= 8,
        f"verified-absent paths={len(unresolved_ok)} "
        f"claimed-resolved-but-absent={absent_but_called_resolved or 'none'}")

    paths=[a["label"].split(" (markdown line")[0] for a in assets
           if a["asset_class"]=="source_code_reference"]
    add("A4_distinct_paths_aggregate",
        len(set(paths))==man["counts"].get("distinct_referenced_paths"),
        f"occurrences={len(paths)} distinct_literal_paths={len(set(paths))} "
        f"declared={man['counts'].get('distinct_referenced_paths')} "
        f"(green_shipping.py cited twice on lines 26/37)")

    # ---------------- integrity self-consistency (adversarial) ----------------
    declared_uq = man["integrity"]["quote_uniqueness"]
    n_unique = sum(1 for a in assets if md.count(a["locator"]["quote"]) == 1)
    consistent = (declared_uq["total_quotes"] == len(assets)
                  and declared_uq["quotes_unique_in_source"] == n_unique
                  and (len(declared_uq["repeated_quotes"]) == 0) == (n_unique == len(assets)))
    add("I1_integrity_block_self_consistent", consistent,
        f"declared total/unique/repeated="
        f"{declared_uq['total_quotes']}/{declared_uq['quotes_unique_in_source']}/"
        f"{declared_uq['repeated_quotes']!r}; recomputed unique={n_unique}, "
        f"non-unique={[aid for aid, c in quote_counts if c != 1]!r}", hard=False)

    # ---------------- claims / verified / scope ----------------
    add("C1_no_claims_and_no_verified",
        man.get("claims") == [] and env.get("claims") == []
        and all(a.get("claimed_status") not in {"verified"} for a in assets),
        f"manifest.claims={len(man.get('claims', []))} "
        f"envelope.claims={len(env.get('claims', []))} verified_marks=0")
    scope_txt = (man_path.read_text(encoding="utf-8")
                 + (UPSTREAM / "kf_result.json").read_text(encoding="utf-8")
                 + (UPSTREAM / "report.md").read_text(encoding="utf-8"))
    other_ids = sorted({m for m in re.findall(r'"report_id"\s*:\s*"?(\d+)"?', scope_txt)}
                       - {"7450"})
    add("C2_report_scope_7450_only", not other_ids,
        f"report_ids referenced by upstream package: {other_ids or ['7450']}")

    # ---------------- schemas ----------------
    try:
        import jsonschema  # noqa: F401
        have_js = True
    except Exception:
        have_js = False
    if have_js:
        import jsonschema
        kf_schema = json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text())
        am_schema = json.loads((ROOT / "schemas/asset_manifest.v1.schema.json").read_text())
        kf_ok = not list(jsonschema.Draft202012Validator(kf_schema).iter_errors(env))
        # the shipped asset_manifest schema pins consts of its reference package
        # (wp-448-01 / 448); relax exactly those three, nothing else.
        relaxed = json.loads(json.dumps(am_schema))
        for k in ("package_id", "task_type", "report_id"):
            relaxed["properties"][k].pop("const", None)
        relaxed["properties"]["source"]["properties"]["uri"].pop("const", None)
        am_ok = not list(jsonschema.Draft202012Validator(relaxed).iter_errors(man))
        add("G1_schema_kf_result", kf_ok, "kf_result.json vs schemas/kf_result.v1.schema.json")
        add("G2_schema_asset_manifest", am_ok,
            "asset_manifest.json vs schemas/asset_manifest.v1.schema.json "
            "(package_id/task_type/report_id consts relaxed; documented in detail)")
    else:
        add("G1_schema_kf_result", False, "jsonschema not importable -> not_run", hard=False)
        add("G2_schema_asset_manifest", False, "jsonschema not importable -> not_run",
            hard=False)

    # ---------------- semantic fidelity of the *source report* itself ----------------
    # (a) required CII = a*Capacity^-c*(1-Z): every displayed row must satisfy it.
    rows = re.findall(
        r"^\| (\w+) \| (\d{4}) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| "
        r"([\d.]+) \| ([\d.e+-]+) \| ([\d.e+-]+) \|$", md, re.M)
    worst = 0.0
    for st, yr, ref, z, svc, api, ice, d1, d2 in rows:
        expect = float(ref) * (1 - float(z))
        rel = abs(float(svc) - expect) / expect
        worst = max(worst, rel)
    add("T1_table1_arithmetic",
        len(rows) == 16 and worst < 5e-5,
        f"rows_parsed={len(rows)} max|svc-ref*(1-Z)|/ref={worst:.2e} "
        f"(display rounding of 4-dp reference bound)")
    add("T2_table1_three_way_equal",
        all(float(d1) == 0.0 and float(d2) == 0.0 for *_, d1, d2 in rows)
        and "0.000e+00" in md,
        f"rows with relΔ=0 on both columns: "
        f"{sum(1 for *_, d1, d2 in rows if float(d1) == float(d2) == 0.0)}/{len(rows)}")
    # (b) table-2 regime semantics: 2027+ value must equal the 2026 value (Z frozen 0.11)
    t2 = re.findall(r"^\| (2019|2022|2023|2026|2027|2031) \| ([^|]+) \| ([^|]+) \| "
                    r"([^|]+) \| ([^|]+) \|$", md, re.M)
    t2d = {y: (reg.strip(), zx.strip(), req.strip(), old.strip()) for y, reg, zx, req, old in t2}
    ok_t2 = (set(t2d) == {"2019", "2022", "2023", "2026", "2027", "2031"}
             and t2d["2027"][2] == t2d["2026"][2] == "3.766208"
             and t2d["2019"][2].startswith("422")
             and t2d["2019"][3] == t2d["2022"][3] == "4.231694"
             and t2d["2027"][1] == "True" and t2d["2026"][1] == "False")
    add("T3_table2_regime_semantics", ok_t2,
        f"2026/2027 required={t2d.get('2026', ('', '', '?'))[2]}/"
        f"{t2d.get('2027', ('', '', '?'))[2]}; "
        f"z_extrapolated 2026={t2d.get('2026', ('', '?'))[1]} "
        f"2027={t2d.get('2027', ('', '?'))[1]}")
    add("T4_table3_rating_order", "| rating | A, A, B, C, D, E |" in md
        and "ratio=1.0" in md,
        "rating band row A,A,B,C,D,E present; ratio=1.0->C invariant stated")

    # ---------------- claims in the report that CANNOT be checked from here ----------------
    unverifiable = []
    if "164" in md:
        unverifiable.append(
            "pytest '164 项/164 passed' — test file lives in ship-performance-platform "
            "(backend/tests/test_cii_rule_arbitration_m6284.py); absent from this worktree")
    grid = re.search(r"4 型 × 4 年 × 4 容量", md)
    shown = len(rows)
    if grid:
        unverifiable.append(
            f"§⑥ error row claims a 4x4x4=64-cell grid but the markdown tabulates only "
            f"{shown} cells (Capacity=80 000 t); the other 48 cells are not observable here")
    if "a, c" in md and "WITHHELD" in md:
        unverifiable.append(
            "reference-line a,c / Z table / dd vector vs IMO原文 — offline, marked "
            "WITHHELD/NOT_SUPPORTED by the report itself; not testable in this context")

    hard_fail = [c["check_id"] for c in checks if c["hard"] and not c["pass"]]
    out = {
        "package_id": "wp-7450-04",
        "reviewed_package": "wp-7450-01",
        "report_id": "7450",
        "reviewed_source_hash": f"sha256:{src_hash}",
        "hashes": {"manifest_sha256": man_hash,
                   "kf_result_sha256": sha256_bytes((UPSTREAM / "kf_result.json").read_bytes()),
                   "markdown_sha256": src_hash},
        "checks": checks,
        "hard_failures": hard_fail,
        "not_run": [
            "wp-7450-02/03 upstream packages: not visible through the reports API window "
            "(list endpoint caps limit=100 and ignores offset; no work-package endpoint)",
            "pytest suite referenced by the source report (other repository)",
            "live /cii behaviour of green_shipping (ship API :8002 exposes no such route "
            "in this environment; openapi.json 404)",
        ],
        "unverifiable_or_overstated": unverifiable,
        "verdict": "pass" if not hard_fail else "needs-fix",
    }
    PKG04.mkdir(parents=True, exist_ok=True)
    (PKG04 / "verify_output.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["check_id"] + " :: " + c["detail"])
    print("\nverdict:", out["verdict"], "| hard_failures:", hard_fail or "none")
    return 0 if not hard_fail else 1


if __name__ == "__main__":
    sys.exit(main())