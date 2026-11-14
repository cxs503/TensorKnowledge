#!/usr/bin/env python3
"""Independent re-verification of wp-5624-01 (registration package) against report 5624.

The reviewer does not reuse the producer's self-check: every clause below is
recomputed from a hash-pinned snapshot of the source markdown
(``source/report_5624.md``) and from the artefacts the producer actually shipped
under ``docs/kf/wp-5624-01/``.  When platform credentials are present the live
record is fetched as well and compared byte-for-byte with the snapshot; without
credentials the snapshot stays authoritative and the live clause is recorded as
``not_run`` rather than assumed to pass.

Output: ``upstream_recheck.json`` (consumed by ``make_review_report.py``).
Run:    python3 docs/kf/wp-5624-04/verify_upstream.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
UP = ROOT / "docs" / "kf" / "wp-5624-01"
CONTRACT = HERE / "work-package.json"
SNAPSHOT = HERE / "source" / "report_5624.md"
OUT = HERE / "upstream_recheck.json"
REPORT_ID = "5624"

#: GATE-RULES S9 vocabulary: a 03/04 product may not carry these field names.
FORBIDDEN_FIELDS = ("verified", "verification_status", "verification_level",
                    "is_verified", "gate_confirmed")

#: Findings are attached to failing checks here, so the review report never
#: hand-transcribes a number or a quote: both come from the check detail.
FINDINGS = {
    "F5.body_inventory_counts_self_consistent": {
        "id": "F-01",
        "attributed_to": "report-5624",
        "severity": "major",
        "scope": "report 5624 body (lines 7-8) vs Fig.1 caption; non-blocking for this registration",
        "blocking_for": "any downstream claim that inventories '102 files / 6.45 MB'",
        "statement": (
            "The report body states 0 files for each of the two artefact roots (line 7) "
            "and then 102 files / 6.45 MB for the same two roots (line 8), while the "
            "Fig.1 caption gives the split 94 + 8 = 102. Two of the three statements "
            "cannot both be true. The manifest registered this as unresolved observation "
            "5624-obs-01 instead of choosing a number, which is the correct 01 behaviour, "
            "so the registration passes and only downstream inventory claims are blocked."
        ),
    },
    "F2.obs01_third_count_locator": {
        "id": "F-02",
        "attributed_to": "wp-5624-01",
        "severity": "minor",
        "scope": "wp-5624-01 asset_manifest.json observations[0]",
        "blocking_for": "nothing; characterisation of the observed inconsistency only",
        "statement": (
            "observations[0] presents 'three count calibers' in conflict, but the third "
            "one (116 index entries, line 29) is the arithmetic closure 102 + 14 mission "
            "artefacts, i.e. not a conflicting count; and its locator "
            "other_file_count_lines points at line 43, which states a sample size "
            "(20 files), not an inventory count. The observation is substantiated for the "
            "0-vs-102 pair, overstated otherwise, and its third locator is mis-attributed."
        ),
    },
    "D3.locator_quotes_distinct": {
        "id": "F-03",
        "attributed_to": "wp-5624-01",
        "severity": "minor",
        "scope": "wp-5624-01 locator_check",
        "blocking_for": "nothing; reported coverage figure only",
        "statement": (
            "locator_check reports 9/9 resolved, but two of the nine items "
            "(5624-ref-01 and 5624-ref-02) quote the same sentence, so distinct "
            "locator evidence is 8, not 9. Resolution is real for every item."
        ),
    },
    "D5.occurrence_counts": {
        "id": "F-04",
        "attributed_to": "wp-5624-01",
        "severity": "minor",
        "scope": "wp-5624-01 content_digests[1].occurrences",
        "blocking_for": "nothing; registration bookkeeping only",
        "statement": (
            "content_digests[1].occurrences is declared 1, but its 16-hex raw text is "
            "also a substring of the full 64-hex digest on line 25, so it occurs twice "
            "in the source. The declared prefix_of/prefix_consistent relation is correct."
        ),
    },
    "H3.no_self_verification": {
        "id": "F-05",
        "attributed_to": "wp-5624-01",
        "severity": "minor",
        "scope": "wp-5624-01 boundary.verification_status",
        "blocking_for": "nothing today; blocks a 03 product that reuses this envelope",
        "statement": (
            "boundary carries a field literally named verification_status (value "
            "'none — 由平台门独立计算，本包不标 verified'). No verification is "
            "asserted, but the field name is exactly the one GATE-RULES S9 forbids in "
            "03/04 products, so the envelope cannot be promoted into a 03 package "
            "unchanged."
        ),
    },
    "G5.shipped_png_bound_to_registered_figure": {
        "id": "F-06",
        "attributed_to": "wp-5624-01",
        "severity": "informational",
        "scope": "wp-5624-01 package contents",
        "blocking_for": "nothing; figure content is out of review scope",
        "statement": (
            "The package ships fig_acceptance.png while the record registers "
            "fig1_inventory/fig2_sizes/fig3_acceptance with no per-image digest, so the "
            "shipped PNG cannot be bound to any registered figure name or content."
        ),
    },
}

NOT_RUN = {
    "artifact_inventory_existence": (
        "the 102-file inventory lives in the m4963 TensorPlatform worktree; this "
        "worktree only touches report 5624 and does not cross-read it"),
    "content_digest_recomputation": (
        "the indexed artefact whose sha256 the report quotes is not in this worktree"),
    "pytest_10_cases": (
        "tools/artifact_indexer and its test suite are not in this worktree, so the "
        "'10 passed' clause cannot be executed here"),
    "index_byte_idempotency": (
        "the index JSON referenced by the report is not shipped; 'byte-identical on "
        "rebuild' is not reproducible from this worktree"),
    "figure_payload": (
        "the platform stores figure metadata only (no payload field), so no image can "
        "be decoded and compared"),
}


class Ledger:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def check(self, cid: str, ok: bool | None, detail) -> bool:
        """``ok is None`` records a not_run clause (unknown, never 'passed')."""
        self.items.append({"id": cid, "status": "pass" if ok else ("not_run" if ok is None
                                                                  else "fail"),
                           "ok": bool(ok), "detail": detail})
        return bool(ok)

    def failed(self) -> list[dict]:
        return [i for i in self.items if i["status"] == "fail"]

    def summary(self) -> dict:
        out = {"total": len(self.items), "passed": 0, "failed": 0, "not_run": 0}
        for i in self.items:
            out[{"pass": "passed", "fail": "failed", "not_run": "not_run"}[i["status"]]] += 1
        return out


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def sha256_file(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def fetch_live() -> dict:
    """Live record of report 5624, or a not_run marker (never a silent pass)."""
    base = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
    user, pw = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not base or not user or not pw:
        return {"status": "not_run", "reason": "no TENSOR_API_BASE/AGENT credentials"}
    try:
        body = json.dumps({"username": user, "password": pw}).encode()
        req = urllib.request.Request(base + "/auth/login", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        tok = json.loads(urllib.request.urlopen(req, timeout=30).read())
        tok = tok.get("access_token") or tok.get("token")
        req = urllib.request.Request(f"{base}/tensor/reports/{REPORT_ID}",
                                     headers={"Authorization": "Bearer " + tok})
        rec = json.loads(urllib.request.urlopen(req, timeout=60).read())
        return {"status": "ok", "record": rec}
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:  # pragma: no cover
        return {"status": "not_run", "reason": f"{type(exc).__name__}: {exc}"[:200]}


def _occurrence_lines(text: str, needle: str) -> list[int]:
    lines = text.split("\n")
    return [i for i, ln in enumerate(lines, 1) if needle in ln]


def main() -> int:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    manifest = json.loads((UP / "asset_manifest.json").read_text(encoding="utf-8"))
    kf = json.loads((UP / "kf_result.json").read_text(encoding="utf-8"))
    md = SNAPSHOT.read_text(encoding="utf-8")
    live = fetch_live()
    rec = live.get("record") or {}
    led = Ledger()

    # ---------------- A. source identity (independent recomputation) --------
    snap_hash = sha256_text(md)
    led.check("A1.snapshot_sha256_vs_contract", snap_hash == contract["input"]["source_hash"][7:],
              f"snapshot=sha256:{snap_hash} contract={contract['input']['source_hash']}")
    size = manifest["source_asset"]["size"]
    live_size = {"chars": len(md), "bytes": len(md.encode("utf-8")),
                 "lines": len(md.rstrip("\n").split("\n"))}
    led.check("A2.size_vs_manifest",
              (size["chars"], size["bytes_utf8"], size["lines"]) ==
              (live_size["chars"], live_size["bytes"], live_size["lines"]),
              f"recomputed={live_size} declared="
              f"{ {k: size[k] for k in ('chars', 'bytes_utf8', 'lines')} }")
    led.check("A3.snapshot_sha256_vs_manifest",
              ("sha256:" + snap_hash) == manifest["source_asset"]["hash"]["value"],
              f"manifest={manifest['source_asset']['hash']['value']}")
    led.check("A4.snapshot_sha256_vs_kf_result",
              ("sha256:" + snap_hash) == kf["provenance"]["source_hash"],
              f"kf_result={kf['provenance']['source_hash']}")
    if live["status"] == "ok":
        led.check("A5.live_markdown_equals_snapshot", rec.get("markdown") == md,
                  f"live_chars={len(rec.get('markdown') or '')} snapshot_chars={len(md)}")
    else:
        led.check("A5.live_markdown_equals_snapshot", None, live["reason"])

    # ---------------- B. record metadata registered faithfully ---------------
    meta = manifest["source_asset"]["record_metadata"]
    if live["status"] == "ok":
        fields = {"title": rec.get("title"), "scenario_key": rec.get("scenario_key"),
                  "mission_id": rec.get("mission_id"), "tags": rec.get("tags"),
                  "status": rec.get("status")}
        declared = {k: meta.get(k) for k in fields}
        led.check("B1.metadata_core_fields", fields == declared,
                  f"live={ {k: fields[k] for k in ('scenario_key', 'mission_id', 'status')} } "
                  f"declared={ {k: declared[k] for k in ('scenario_key', 'mission_id', 'status')} }")
    else:
        led.check("B1.metadata_core_fields", None, live["reason"])
    hint = meta.get("contract_layer_hint") or \
        manifest["source_asset"].get("contract_layer_hint") or {}
    scoped = [t for t in (meta.get("tags") or []) if t]
    tokens = (hint.get("value") or "").split("|")
    led.check("B2.contract_layer_hint_consistent",
              len(tokens) >= 2 and tokens[1] == meta.get("scenario_key")
              and tokens[0] in scoped and hint.get("interpreted") is False,
              f"hint={hint.get('value')} scenario_key={meta.get('scenario_key')} "
              f"interpreted={hint.get('interpreted')}")

    # ---------------- C. section segmentation --------------------------------
    sections = manifest["sections"]
    lines = md.split("\n")
    bad_head, bad_chars, bad_sha = [], [], []
    for s in sections:
        seg = "\n".join(lines[s["line_start"] - 1:s["line_end"]])
        if not lines[s["line_start"] - 1].startswith("#" * s["level"] + " ") or \
                s["heading"] not in lines[s["line_start"] - 1]:
            bad_head.append(s["ordinal"])
        if len(seg) != s["chars"]:
            bad_chars.append((s["ordinal"], len(seg), s["chars"]))
        if sha256_text(seg) != s["sha256"][7:]:
            bad_sha.append(s["ordinal"])
    led.check("C1.section_headings_at_declared_lines",
              not bad_head and [s["ordinal"] for s in sections] == list(range(1, len(sections) + 1)),
              f"n={len(sections)} bad_ordinals={bad_head}")
    led.check("C2.section_chars", not bad_chars, f"mismatch(ordinal,recomputed,declared)={bad_chars}")
    led.check("C3.section_sha256", not bad_sha, f"mismatch_ordinals={bad_sha}")
    spans = [(s["line_start"], s["line_end"]) for s in sections]
    led.check("C4.section_spans_ordered",
              all(a <= b for a, b in spans) and
              all(spans[i][1] < spans[i + 1][0] for i in range(len(spans) - 1)),
              f"spans={spans}")

    # ---------------- D. locators -------------------------------------------
    lc = manifest["locator_check"]
    quotes = [it["quote"] for it in lc["items"]]
    # attachments are located against the record's figures field, not the body text
    caption_pool = "\n".join(i["caption"] for i in manifest["attachments"]["items"])
    if live["status"] == "ok":
        caption_pool = "\n".join((f.get("caption") or "") for f in (rec.get("figures") or []))
    unresolved = [it["id"] for it in lc["items"]
                  if it["quote"] not in (caption_pool if it.get("source_field") == "figures" else md)]
    led.check("D1.locator_check_declared_total", lc["total"] == len(lc["items"]),
              f"declared_total={lc['total']} items={len(lc['items'])}")
    led.check("D2.locators_resolve_independently",
              not unresolved and all(it["resolvable"] for it in lc["items"]),
              f"unresolved={unresolved} declared_resolved={lc['resolved']}/{lc['total']} "
              f"pools=markdown|figures(captions={caption_pool.count(chr(10)) + 1})")
    distinct = len(set(quotes))
    led.check("D3.locator_quotes_distinct", distinct == len(quotes),
              f"distinct={distinct} items={len(quotes)} "
              f"duplicate_quotes={ {q: quotes.count(q) for q in set(quotes) if quotes.count(q) > 1} }")
    attribution = []
    for ref in manifest["referenced_artifacts"]:
        got = _occurrence_lines(md, ref["locator_quote"])
        if got and ref["first_line"] not in got:
            attribution.append({"id": ref["ref_id"], "declared": ref["first_line"], "found": got})
    led.check("D4.quote_line_attribution", not attribution, f"mismatches={attribution}")
    occ_bad = []
    for item in list(manifest["referenced_artifacts"]) + list(manifest["content_digests"]):
        got = md.count(item["raw_text"]) if item.get("raw_text") else None
        if got != item.get("occurrences"):
            occ_bad.append({"id": item.get("ref_id") or item.get("digest_id"),
                            "declared": item.get("occurrences"), "recomputed": got})
    led.check("D5.occurrence_counts", not occ_bad, f"mismatches={occ_bad}")

    # ---------------- E. content digests ------------------------------------
    dig = manifest["content_digests"]
    full = [d for d in dig if d["digits"] == 64][0]
    trunc = [d for d in dig if d["digits"] == 16][0]
    led.check("E1.digest_64hex_located",
              full["raw_text"] in md and full["first_line"] in _occurrence_lines(md, full["raw_text"]),
              f"lines={_occurrence_lines(md, full['raw_text'])} declared={full['first_line']}")
    led.check("E2.digest_prefix_located",
              trunc["raw_text"] in md and trunc["first_line"] in _occurrence_lines(md, trunc["raw_text"]),
              f"lines={_occurrence_lines(md, trunc['raw_text'])} declared={trunc['first_line']}")
    led.check("E3.digest_prefix_consistent_with_full",
              full["raw_text"].startswith(trunc["raw_text"]) and
              trunc.get("prefix_consistent") is True and
              trunc.get("prefix_of") == [full["digest_id"]],
              f"prefix_of={trunc.get('prefix_of')} full={full['digest_id'][:12]}")

    # ---------------- F. the registered internal inconsistency --------------
    obs = manifest["observations"][0]
    loc = obs["locators"]
    zero_ok = all(q in md and any(q in md.split("\n")[ln - 1] for ln in loc["zero_file_lines"])
                  for q in obs["quotes"][:1])
    total_ok = obs["quotes"][1] in md.split("\n")[loc["total_count_line"] - 1]
    led.check("F1.obs01_zero_and_total_quotes_at_declared_lines", zero_ok and total_ok,
              f"zero_lines={loc['zero_file_lines']} total_line={loc['total_count_line']}")
    third = loc["other_file_count_lines"]
    third_text = [md.split("\n")[ln - 1] for ln in third]
    third_is_count = [bool(re.search(r"(共|总|合计)\s*\**\s*\d+\s*(文件|条)", t)) for t in third_text]
    led.check("F2.obs01_third_count_locator", all(third_is_count),
              f"declared_lines={third} texts={third_text} inventory_count_statement={third_is_count}")
    counts = {"line7_zero_per_root": bool(re.search(r"（0 文件）", lines[6])),
              "line8_total": (re.search(r"共 \*\*(\d+) 文件", lines[7]) or [None, None])[1],
              "fig1_caption": (re.search(r"artifacts/ (\d+) \+ runs/ (\d+) = (\d+)",
                                         (manifest["attachments"]["items"][0]["caption"])) or [None] * 4)[3]}
    led.check("F3.obs01_zero_vs_total_conflict_confirmed",
              counts["line7_zero_per_root"] and counts["line8_total"] and
              counts["fig1_caption"] and counts["fig1_caption"] == counts["line8_total"],
              f"recomputed={counts}")
    body_zero = re.findall(r"`(?:artifacts|runs)/`（0 文件）", lines[6])
    body_total = re.search(r"共 \*\*(\d+) 文件 / ([\d.]+) MB\*\*", lines[7])
    led.check("F5.body_inventory_counts_self_consistent",
              not (len(body_zero) == 2 and body_total and int(body_total.group(1)) > 0),
              f"line7_zero_roots={len(body_zero)} line8_total_files="
              f"{body_total.group(1) if body_total else None} "
              f"line8_size_MB={body_total.group(2) if body_total else None}")
    led.check("F4.obs01_left_unresolved",
              obs["status"] == "unresolved" and obs["kind"] == "internal_inconsistency"
              and any(u["item"].endswith("which_count_is_authoritative") and u["status"] == "unresolved"
                      for u in manifest["unresolved"]),
              f"status={obs['status']} kind={obs['kind']}")

    # ---------------- G. attachments / figures ------------------------------
    att = manifest["attachments"]
    if live["status"] == "ok":
        figs = rec.get("figures") or []
        led.check("G1.attachment_count_vs_live_figures",
                  att["count"] == len(figs) == len(att["items"]),
                  f"live={len(figs)} declared={att['count']} items={len(att['items'])}")
        pairs = [(f.get("name"), f.get("caption")) for f in figs]
        decl = [(i["name"], i["caption"]) for i in att["items"]]
        led.check("G2.attachment_names_captions_vs_live", pairs == decl,
                  f"live_names={[p[0] for p in pairs]} declared_names={[p[0] for p in decl]}")
    else:
        led.check("G1.attachment_count_vs_live_figures", None, live["reason"])
        led.check("G2.attachment_names_captions_vs_live", None, live["reason"])
    no_payload = all(i.get("payload_field_present") is False and i.get("png_base64_len") == 0
                     for i in att["items"])
    no_inline = ("data:image" not in md) and not re.search(r"!\[[^\]]*\]\([^)]+\)", md)
    led.check("G3.attachment_payload_absent", no_payload and no_inline,
              f"items_no_payload={no_payload} markdown_has_no_image={no_inline} "
              f"scan={att['scan']}")
    led.check("G4.attachment_digests_absent",
              all("sha256" not in i for i in att["items"]),
              "no per-image digest registered, so figure content is out of scope (recorded, not failed)")
    shipped_pngs = sorted(p.name for p in UP.glob("*.png"))
    bound = [n for n in shipped_pngs if any(n == i["name"] for i in att["items"])]
    led.check("G5.shipped_png_bound_to_registered_figure", bool(bound),
              f"shipped_pngs={shipped_pngs} registered_names="
              f"{[i['name'] for i in att['items']]} bound={bound}")

    # ---------------- H. package integrity / no self-verification -----------
    led.check("H1.kf_result_outputs_equal_shipped_manifest",
              kf["outputs"].get("asset_manifest.json") == manifest,
              f"output_keys={sorted(kf['outputs'])}")
    led.check("H2.claims_empty_and_boundary_stated",
              kf["claims"] == [] and manifest["boundary"]["claims_generated"] == 0,
              f"claims={len(kf['claims'])} boundary_claims_generated="
              f"{manifest['boundary']['claims_generated']}")
    hits = []

    def scan(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in FORBIDDEN_FIELDS:
                    hits.append({"path": path + "/" + k,
                                 "value": v if isinstance(v, str) else type(v).__name__})
                scan(v, path + "/" + k)
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                scan(v, f"{path}[{i}]")

    scan(manifest)
    asserting = [h for h in hits if h["value"] not in ("none", "") and
                 "none" not in str(h["value"])[:8]]
    led.check("H3.no_self_verification", not hits,
              f"forbidden_field_names={hits} asserting_verification={asserting}")
    led.check("H4.boundary_single_report",
              manifest["boundary"]["report_ids_read"] == [REPORT_ID] and
              manifest["boundary"]["report_ids_written"] == [REPORT_ID],
              f"read={manifest['boundary']['report_ids_read']} "
              f"written={manifest['boundary']['report_ids_written']}")
    other_refs = sorted({r for r in re.findall(r"reports/(\d+)", json.dumps(manifest)) if r != REPORT_ID})
    led.check("H5.no_other_report_referenced", not other_refs, f"other_report_ids={other_refs}")

    # ---------------- J. the report's own arithmetic, re-derived ------------
    def cell(line_no: int) -> str:
        row = lines[line_no - 1]
        return row.split("|")[2].strip() if row.count("|") >= 3 else row

    cold = [int(x) for x in re.findall(r"\d+", cell(23))]
    warm = [int(x) for x in re.findall(r"\d+", cell(24))]
    sample = [int(x) for x in re.findall(r"\d+", cell(26))]
    verify = [int(x) for x in re.findall(r"\d+", cell(27))]
    led.check("J1.cold_build_arithmetic",
              cold[0] == cold[1] + cold[2] and cold[3] == cold[0] and cold[2] == 0,
              f"scanned/hashed/skipped/added={cold}")
    led.check("J2.second_build_arithmetic",
              warm[0] == warm[1] + warm[2] and warm[1] == 0 and "False" in cell(24),
              f"scanned/hashed/skipped/changed={warm} changed_flag={'False' in cell(24)}")
    led.check("J3.sample_arithmetic", sample[0] == sample[1] + sample[2] and sample[2] == 0,
              f"sampled={sample}")
    led.check("J4.verify_arithmetic", verify[0] == verify[1] + verify[2] and verify[2] == 0,
              f"total/passed/failed={verify}")
    pct = []
    for ln, total in ((43, sample[1] + sample[2]), (44, verify[1] + verify[2])):
        m = re.search(r"mismatch\s+(\d+)/(\d+)", lines[ln - 1])
        m2 = re.search(r"([\d.]+)% < ([\d.]+)%", lines[ln - 1])
        pct.append({"line": ln, "mismatch": int(m.group(1)), "n": int(m.group(2)),
                    "recomputed_pct": round(100.0 * int(m.group(1)) / int(m.group(2)), 1),
                    "stated_pct": float(m2.group(1)), "threshold": float(m2.group(2))})
    led.check("J5.error_percentages_recomputed",
              all(p["recomputed_pct"] == p["stated_pct"] and p["recomputed_pct"] < p["threshold"]
                  for p in pct) and pct[0]["n"] == sample[0] and pct[1]["n"] == verify[0],
              f"items={pct}")
    entries = int(re.search(r"(\d+) 条", lines[28]).group(1))
    own = int(re.search(r"含本单 (\d+) 个工件", lines[28]).group(1))
    declared_total = int(re.search(r"共 \*\*(\d+) 文件", lines[7]).group(1))
    led.check("J6.index_growth_arithmetic_closure",
              entries == declared_total + own,
              f"index_entries_line29={entries} declared_total_files_line8={declared_total} "
              f"own_artefacts_line29={own} closure={declared_total}+{own}={declared_total + own}")
    led.check("J7.pytest_clause_executable", None,
              NOT_RUN["pytest_10_cases"] + f" (report states {len(re.findall(r'10', cell(28)))} clause "
              f"'{cell(28)}')")

    # ---------------- K. independence of this review ------------------------
    producer_ids = {kf["provenance"]["producer"], (manifest.get("generator") or "").split("/")[-1]}
    reviewer = "m20805"
    led.check("K1.reviewer_independent_of_producer", reviewer not in producer_ids,
              f"producer_ids={sorted(producer_ids)} reviewer={reviewer}")
    led.check("K2.no_producer_review_material",
              not any((UP / n).exists() for n in
                      ("review_events.json", "verification_ticket.json", "review_report.json")),
              f"upstream_files={sorted(p.name for p in UP.iterdir())}")

    # ---------------- assemble --------------------------------------------
    findings = []
    for item in led.failed():
        spec = FINDINGS.get(item["id"])
        if spec:
            findings.append({**spec, "check_id": item["id"], "evidence": item["detail"]})
    result = {
        "recheck_version": "wp5624-04-recheck-1",
        "package_id": contract["package_id"],
        "reviewed_package": {
            "package_id": "wp-5624-01",
            "task_type": manifest["task_type"],
            "path": "docs/kf/wp-5624-01",
            "artifacts": [{"name": p.name, "sha256": sha256_file(p)}
                          for p in sorted(UP.iterdir()) if p.is_file()],
        },
        "source": {
            "report_id": REPORT_ID,
            "snapshot": "docs/kf/wp-5624-04/source/report_5624.md",
            "sha256": "sha256:" + snap_hash,
            "chars": live_size["chars"], "bytes": live_size["bytes"],
            "lines": live_size["lines"],
            "live_check": {"status": live["status"], **({} if live["status"] == "ok"
                                                       else {"reason": live.get("reason")})},
        },
        "checks": led.items,
        "summary": led.summary(),
        "findings": findings,
        "not_run": NOT_RUN,
        "recomputed": {"sections": [
            {"ordinal": s["ordinal"], "line_start": s["line_start"], "line_end": s["line_end"],
             "chars": s["chars"], "sha256_ok": s["ordinal"] not in bad_sha} for s in sections],
            "report_table": {"cold_build": cold, "second_build": warm, "sample": sample,
                             "verify": verify, "index_entries": entries, "own_artefacts": own,
                             "declared_total_files": declared_total, "percentages": pct},
            "locator_items": len(lc["items"]),
            "locator_unresolved": len(unresolved),
            "locator_distinct_quotes": distinct,
            "forbidden_fields": hits},
    }
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"checks={result['summary']}")
    for f in findings:
        print(f"  {f['id']} [{f['severity']}] {f['check_id']}: {f['evidence']}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0 if not any(f["severity"] == "blocking" for f in findings) else 1


if __name__ == "__main__":
    raise SystemExit(main())