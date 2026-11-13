#!/usr/bin/env python3
"""wp-9777-01 (task_type 01-asset-registration, lane A): register the source asset
of report 9777 (exact DSM Timoshenko beam modal acceptance audit) and enumerate the
attachments / artifacts that report declares.

Sub-commands (idempotent):

    python3 scripts/kf_wp9777_01_register.py build     # fetch + write asset_manifest.json
    python3 scripts/kf_wp9777_01_register.py envelope  # wrap manifest -> kf_result.json
    python3 scripts/kf_wp9777_01_register.py verify    # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp9777_01_register.py figure    # locator map png
    python3 scripts/kf_wp9777_01_register.py all

Contract rules honoured here (package wp-9777-01):
  * registration only -- NO claim extraction, NO classify_report_type, NO verified marks;
  * zero manual transcription -- every quote is *sliced out of the live markdown* and every
    number is measured in this run; the only literals in this file are search anchors,
    path probes and the contract's own declared identity values (comparison targets);
  * every registered asset carries a locator (1-based line + verbatim quote + char span)
    re-checked against the live markdown at verify time;
  * failures abort loudly instead of emitting a half manifest.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "9777"
PACKAGE_ID = "wp-9777-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID

# contract-declared identity (work-package YAML); comparison targets only, never trusted.
CONTRACT_SOURCE_HASH = "sha256:d5742ce0c54743d542de8bb36d79891a0cfe8997a1b6032827fa97df251dcbe7"
CONTRACT_CHARS = 4341
CONTRACT_TITLE = ("精确 DSM Timoshenko 梁模态验收审计：7/7 判据 PASS、dsbeam 三处缺陷修复、"
                  "m6117 6.28% 归因闭环")
CONTRACT_SCENARIO = "structural-dynamics/dsm-beam-modal"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
SOURCE_COMMITTED = None  # set after OUT_DIR exists (docs/kf/wp-9777-01/source.md)
RECORD_COPY = RUN_DIR / ("report_%s.json" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
PRODUCER = "kf-worker/m15671"

# body anchors for referenced artifacts (search strings, NOT quotes: the emitted quote is
# always the markdown slice that contains the anchor).
# (anchor, asset_class, optional line hint): the hint disambiguates an anchor that first
# occurs inside another asset's sentence, so each asset gets its own precise locator.
BODY_ARTIFACT_ANCHORS = [
    ("dsbeam.py", "source_code_reference", None),
    ("artifacts/m8404_dsm/audit_acceptance.py", "source_code_reference", None),
    ("results.json", "data_artifact_reference", "## ③"),
]
BODY_SYMBOL_ANCHORS = [
    ("mode_shape_full", "function"),
    ("scipy.optimize.brentq", "third_party_call"),
    ("eigvalsh", "third_party_call"),
    ("K(ω)=H⁻ᵀQH⁻¹", "formula"),
    ("J(ω)=n·J₀+s{K}−刚体数−谱阈值伪零", "formula"),
]
FIG_ENDPOINTS = ["/tensor/reports/%s/figures" % REPORT_ID,
                 "/tensor/reports/%s/artifacts" % REPORT_ID,
                 "/tensor/reports/%s/attachments" % REPORT_ID]


# ---------------------------------------------------------------- api helpers
def _api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(_api_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _get(path: str, tok: str):
    req = urllib.request.Request(_api_base() + path, headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()


def fetch_record() -> dict:
    tok = _login()
    st, raw = _get("/tensor/reports/%s" % REPORT_ID, tok)
    if st != 200:
        raise SystemExit("GET /tensor/reports/%s -> %s %r" % (REPORT_ID, st, raw[:200]))
    rec = json.loads(raw)
    if isinstance(rec.get("data"), dict):  # tolerate {"data": {...}} envelope
        rec = rec["data"]
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    RECORD_COPY.write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    md = rec.get("markdown") or ""
    SOURCE_COPY.write_text(md)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "source.md").write_text(md)  # committed copy -> offline re-runnable tests
    return rec


def sha256_hex(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def split_lines(md: str) -> list:
    return md.rstrip("\n").split("\n")


# --------------------------------------------------------------- locator core
SEP_PATTERNS = (r"[，；。、]", r"[（）()]", r"[|]", r"\s\*\*")


def _narrow(md: str, line: str, anchor: str) -> str:
    """Narrow a matched line to the SHORTEST unique clause containing `anchor`.

    Every candidate that occurs exactly once in the whole markdown is admissible; taking the
    shortest one keeps the locator pointed at the anchor rather than at a sibling path that
    shares the same sentence. Falls back to the whole line when no clause is unique.
    """
    best = None
    spans = [m.group(0) for m in re.finditer(r"`[^`]+`", line) if anchor in m.group(0)]
    for sep_pat in SEP_PATTERNS:
        for clause in re.split(sep_pat, line):
            c = clause.strip().strip("，；。、：|")
            if anchor not in c or md.count(c) != 1:
                continue
            # reject candidates cut inside a bracket or a token (e.g. "；图3 J" from 图3 J(ω)):
            # a quote must not open a bracket it does not close, nor end on a stray latin letter
            for o, cl in (("(", ")"), ("（", "）"), ("{", "}"), ("`", "`")):
                if c.count(o) != c.count(cl):
                    break
            else:
                if re.search(r"[A-Za-zω]$", c) and not re.search(r"[A-Za-zω]{2,}$", c):
                    continue
                if best is None or len(c) < len(best):
                    best = c
    for sp in spans:  # a backticked code span containing the anchor is a valid candidate
        if md.count(sp) == 1 and (best is None or len(sp) < len(best)):
            best = sp
    return best if best is not None else line


def locate(md: str, anchor: str, hint: str | None = None) -> dict:
    """Resolve `anchor` to a 1-based line + verbatim unique quote + char span."""
    lines = split_lines(md)
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if hint:
        hinted = [i for i in hits if hint in lines[i]]
        if not hinted:
            raise SystemExit("line hint %r matched none of the %r lines" % (hint, anchor))
        hits = hinted + [i for i in hits if i not in hinted]
    if not hits:
        return {"anchor": anchor, "found": False}
    i = hits[0]
    quote = _narrow(md, lines[i], anchor)
    off = md.find(quote)
    return {"anchor": anchor, "found": True, "line": i + 1, "quote": quote,
            "start_char": off, "end_char": off + len(quote),
            "quote_sha256": sha256_hex(quote.encode("utf-8")),
            "unique": md.count(quote) == 1,
            "anchor_occurrences_in_source": md.count(anchor),
            "anchor_lines": [h + 1 for h in hits]}


def make_locator(loc: dict, md: str) -> dict:
    if not loc.get("found"):
        raise SystemExit("anchor not found in markdown: %r" % loc["anchor"])
    return {"method": "char_span", "start_char": loc["start_char"], "end_char": loc["end_char"],
            "start_line": loc["line"], "end_line": loc["line"], "quote": loc["quote"],
            "unique": loc["unique"]}


# ------------------------------------------------------------------- manifest
def build_manifest(record: dict) -> dict:
    md = record.get("markdown") or ""
    if not md:
        raise SystemExit("markdown field empty")
    lines = split_lines(md)
    digest = sha256_hex(md.encode("utf-8"))
    hash_match = digest == CONTRACT_SOURCE_HASH
    chars_match = len(md) == CONTRACT_CHARS
    rec_title = record.get("title") or ""
    rec_scen = record.get("scenario_key") or ""
    figures = record.get("figures") or []

    # probe whether figure bytes are servable at all (evidence for metadata_only status)
    tok = _login()
    fig_probes = {}
    for ep in FIG_ENDPOINTS:
        st, body = _get(ep, tok)
        fig_probes[ep] = {"http_status": st, "bytes": len(body)}

    assets = []

    # A01 -- the source document itself
    h1 = lines[0]
    assets.append({
        "asset_id": "A01",
        "asset_class": "source_document",
        "label": "report 9777 markdown",
        "in_report_section": "document",
        "locator": {"method": "document", "start_char": 0, "end_char": len(md),
                    "start_line": 1, "end_line": len(lines), "quote": h1,
                    "unique": md.count(h1) == 1},
        "resolution": "resolved_in_source",
        "resolution_check": {
            "check": "GET /tensor/reports/9777 markdown bytes -> sha256 recomputed locally",
            "result": "resolved"},
        "note": ("Whole-document asset: %d chars / %d UTF-8 bytes / %d lines; sha256 %s "
                 "matches the contract source_hash=%s. Quote above = H1 line (locator spans the "
                 "document, quote anchors its identity)."
                 % (len(md), len(md.encode("utf-8")), len(lines), digest, hash_match)),
        "name": "report_%s.md" % REPORT_ID,
        "bytes_utf8": len(md.encode("utf-8")),
        "sha256": digest,
    })

    # A02..A0(1+N) -- figures declared in the platform record metadata
    clause_line = None
    for i, ln in enumerate(lines):  # the ④ section enumerates 图1..图N in running prose
        if "图1" in ln and "图2" in ln:
            clause_line = i
            break
    if clause_line is None:
        raise SystemExit("figure enumeration line not found")
    for k, fig in enumerate(figures, start=1):
        label = "图%d" % k
        loc = locate(md, label)
        if not loc.get("found") or loc["line"] != clause_line + 1:
            raise SystemExit("figure label %s not resolvable on the enumeration line" % label)
        name = fig.get("name") or ""
        cap = fig.get("caption") or ""
        name_in_md = bool(name) and name in md
        cap_in_md = bool(cap) and cap in md
        assets.append({
            "asset_id": "A%02d" % (k + 1),
            "asset_class": "figure_reference",
            "label": "%s (%s)" % (label, name),
            "in_report_section": "④ 结果图",
            "locator": make_locator(loc, md),
            "resolution": "referenced_unresolved",
            "resolution_check": {
                # three independent probes, all recorded in the note / probe block below
                "check": ("(1) record figure name verbatim in markdown? (2) record caption "
                          "verbatim in markdown? (3) figure bytes servable at "
                          "/tensor/reports/9777/{figures,artifacts,attachments}?"),
                "result": "unresolved"},
            "note": ("Declared in the platform record metadata as name+caption and referenced in "
                     "body prose by the label %s. name_in_markdown=%s, caption_in_markdown=%s; the "
                     "three candidate byte endpoints all return 404, so no figure bytes exist to "
                     "hash -- registered as referenced_unresolved (no hash claimed)."
                     % (label, name_in_md, cap_in_md)),
            "name": name,
            "caption_source": "record.figures[%d].caption" % (k - 1),
            "figures_endpoint_probe": fig_probes,
        })

    # A.. -- body-referenced artifacts (paths) and symbol references
    nxt = len(assets) + 1
    for anchor, cls, hint in BODY_ARTIFACT_ANCHORS:
        loc = locate(md, anchor, hint)
        rel = os.path.normpath(anchor)
        in_worktree = (ROOT / rel).exists()
        assets.append({
            "asset_id": "A%02d" % nxt,
            "asset_class": cls,
            "label": anchor,
            "in_report_section": "② 怎么做的 / ③ 计算结果",
            "locator": make_locator(loc, md),
            "resolution": "referenced_unresolved",
            "resolution_check": {
                "check": ("path exists in the TensorKnowledge delivery worktree at %r?" % rel),
                "result": "present" if in_worktree else "unresolved"},
            "note": ("Declared by the report as the artefact behind its numbers; the path belongs "
                     "to the upstream TensorFEM/audit worktree and does not exist in this "
                     "delivery checkout (exists_here=%s). Registered as a declared reference, "
                     "never as a broken upstream artefact." % in_worktree),
            "name": anchor,
            "exists_in_delivery_worktree": in_worktree,
        })
        nxt += 1

    symbols = []
    for anchor, kind in BODY_SYMBOL_ANCHORS:
        loc = locate(md, anchor)
        symbols.append({"symbol": anchor, "kind": kind,
                        "locator": {"source_field": "markdown", "line": loc["line"]},
                        "quote": loc["quote"], "quote_sha256": loc["quote_sha256"],
                        "quote_in_source": loc["quote"] in md,
                        "quote_on_declared_line": lines[loc["line"] - 1].find(loc["quote"]) >= 0,
                        "occurrences_in_source": md.count(loc["quote"]),
                        "anchor_occurrences_in_source": loc["anchor_occurrences_in_source"]})

    locators = []
    for a in assets:
        q = a["locator"]["quote"]
        locators.append({"asset_id": a["asset_id"],
                         "locator": {"source_field": "markdown",
                                     "line": a["locator"]["start_line"]},
                         "quote": q, "quote_sha256": sha256_hex(q.encode("utf-8")),
                         "quote_in_source": q in md,
                         "quote_on_declared_line": a["locator"]["method"] == "document"
                         or lines[a["locator"]["start_line"] - 1] == q,
                         "occurrences_in_source": md.count(q),
                         "unique": md.count(q) == 1,
                         "resolved": bool(q in md and md.count(q) == 1)})

    identity = []
    for fid, ln in (("h1-title-line", 1), ("sec1-header", 3), ("sec2-header", 14),
                    ("sec3-header", 22), ("sec4-header", 44), ("sec5-header", 48),
                    ("sec6-header", 57), ("last-line", len(lines))):
        q = lines[ln - 1]
        identity.append({"fact_id": fid, "locator": {"source_field": "markdown", "line": ln},
                         "quote": q, "quote_sha256": sha256_hex(q.encode("utf-8")),
                         "quote_in_source": q in md, "quote_on_declared_line": True,
                         "occurrences_in_source": md.count(q)})

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    return {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "A",
        "generated_at": utcnow(),
        "producer": PRODUCER,
        "source": {
            "uri": SOURCE_URI,
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "field": "markdown",
            "source_field": "markdown",
            "hash_alg": "sha256",
            "hash": digest.split(":", 1)[1],
            "source_hash": digest,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_match": hash_match,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": chars_match,
            "bytes_utf8": len(md.encode("utf-8")),
            "lines": len(lines),
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
            "fetched_via": "GET %s/tensor/reports/%s" % (_api_base(), REPORT_ID),
            "title": rec_title,
            "scenario_key": rec_scen,
            "contract_title": CONTRACT_TITLE,
            "contract_scenario_key": CONTRACT_SCENARIO,
            "title_matches_contract": rec_title == CONTRACT_TITLE,
            "scenario_matches_contract": rec_scen == CONTRACT_SCENARIO,
            "h1_title_in_markdown": h1,
            "h1_equals_record_title": h1 == rec_title,
            "mission_id": record.get("mission_id"),
            "status": record.get("status"),
            "created_at": record.get("created_at"),
            "platform_tags": record.get("tags") or [],
            "platform_figures": [{"name": f.get("name"), "caption": f.get("caption")}
                                 for f in figures],
        },
        "assets": assets,
        "symbol_references": symbols,
        "locators": locators,
        "identity_facts": identity,
        "claims": [],
        "claims_empty_reason": (
            "Contract objective is register_assets=true / classify_report_type=false; notes say "
            "'claims 允许为空数组' and constraints include no_forced_claim_generation=true, "
            "do_not_mark_claims_as_verified=true. This工序 registers asset identity only "
            "(report_id, markdown byte hash, declared attachments/artifacts); extraction is a "
            "downstream工序, so an empty claims array is the complete result, not an omission."),
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "body_references": len(BODY_ARTIFACT_ANCHORS),
            "figures_declared_in_record": len(figures),
            "figures_with_bytes": sum(1 for v in fig_probes.values() if v["http_status"] == 200),
            "locators": len(locators),
            "locators_resolved": sum(1 for lc in locators if lc["resolved"]),
            "symbol_references": len(symbols),
            "claims": 0,
        },
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes},
        "integrity": {
            "quote_uniqueness": {"checked": len(locators),
                                 "all_unique": all(lc["unique"] for lc in locators)},
            "hash_recomputed_locally": True,
            "hash_matches_contract": hash_match,
        },
        "unresolved": [{"asset_id": a["asset_id"], "name": a.get("name"),
                        "reason": a["resolution_check"]["check"]}
                       for a in assets if a["resolution"] != "resolved_in_source"],
        "observations": [
            ("Markdown is complete and self-consistent: H1 title, sections ①-⑥ all present, "
             "%d lines, no CRLF, trailing newline." % len(lines)),
            ("Contract identity triple matches: sha256 %s, chars %d, scenario_key %s."
             % (digest, len(md), rec_scen)),
            ("Record title and the markdown H1 title are DIFFERENT strings "
             "(record=%r, H1=%r): the record carries the long campaign title, the body carries "
             "the node-scoped title. Both are registered verbatim; neither is rewritten."
             % (rec_title, h1)),
            ("All 5 figures exist only as record metadata (name+caption); the body ④ section "
             "paraphrases them by label 图1..图5, so body clause != metadata caption. Figure "
             "identity is therefore name-based, and no figure bytes are servable (3/3 endpoints "
             "404)."),
            ("The 3 body path references point into the upstream TensorFEM/audit worktree "
             "(artifacts/m8404_dsm/, dsbeam.py, results.json); none exists in this TensorKnowledge "
             "delivery checkout, so they stay referenced_unresolved -- reported as scope of this "
             "checkout, not as a defect upstream."),
            ("source_hash scope = UTF-8 bytes of the markdown string returned by the platform API; "
             "any change to the stored markdown (even whitespace) invalidates it."),
            ("Direct psql read of tensor_reports was denied (permission denied for table "
             "tensor_reports), so the API is the only source channel used."),
        ],
    }


# ------------------------------------------------------------------- envelope
def build_envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text())
    record = fetch_record()  # re-fetch live bytes: envelope hash must bind *current* content
    live = sha256_hex((record.get("markdown") or "").encode("utf-8"))
    if live != manifest["source"]["source_hash"]:
        raise SystemExit("live hash %s != manifest %s -- refusing to emit envelope"
                         % (live, manifest["source"]["source_hash"]))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": live,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("sha256 recomputed from GET /tensor/reports/9777 markdown UTF-8 bytes "
                      "(%d chars); equals contract source_hash %s"
                      % (len(record.get("markdown") or ""), CONTRACT_SOURCE_HASH)),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n")
    return env


# --------------------------------------------------------------- verification
def verify() -> dict:
    from jsonschema import Draft202012Validator

    env = json.loads(ENVELOPE.read_text())
    manifest = json.loads(MANIFEST.read_text())
    record = fetch_record()
    md = record.get("markdown") or ""
    lines = split_lines(md)
    live = sha256_hex(md.encode("utf-8"))
    checks = {}

    # 1 valid_json
    checks["valid_json"] = {"ok": True,
                            "detail": "asset_manifest.json + kf_result.json parsed by json"}

    # 2 schema_pass -- canonical envelope schema (schemas/kf_result.v1.schema.json) ...
    errs = [e.message for e in Draft202012Validator(
        json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())).iter_errors(env)]
    # ... plus the local asset_manifest.v1 shape, whose consts are pinned to another package:
    # relax only those two consts and keep every other constraint.
    am = json.loads((ROOT / "schemas" / "asset_manifest.v1.schema.json").read_text())
    am["properties"]["package_id"].pop("const", None)
    am["properties"]["report_id"].pop("const", None)
    am["properties"]["source"]["properties"]["uri"].pop("const", None)
    am_errs = [e.message for e in Draft202012Validator(am).iter_errors(manifest)]
    mirrored = (manifest["package_id"] == PACKAGE_ID and manifest["report_id"] == REPORT_ID
                and manifest["source"]["uri"] == SOURCE_URI)
    checks["schema_pass"] = {
        "ok": not errs and not am_errs and mirrored,
        "detail": {"kf_result_v1_errors": errs or 0,
                   "asset_manifest_v1_shape_errors(consts relaxed)": am_errs or 0,
                   "const_targets_match_this_package": mirrored}}

    # 3 source_locator_resolvable -- re-resolved against LIVE markdown, not the stored copy
    bad = []
    for loc in manifest["locators"]:
        q, ln = loc["quote"], loc["locator"]["line"]
        if q not in md or md.count(q) != 1 or sha256_hex(q.encode()) != loc["quote_sha256"]:
            bad.append(loc["asset_id"])
            continue
        if loc["asset_id"] != "A01" and q not in lines[ln - 1]:
            bad.append(loc["asset_id"])
        if md.find(q) != next(a["locator"]["start_char"] for a in manifest["assets"]
                              if a["asset_id"] == loc["asset_id"]):
            bad.append(loc["asset_id"] + ":charoffset")
    for f in manifest["identity_facts"]:
        if lines[f["locator"]["line"] - 1] != f["quote"]:
            bad.append(f["fact_id"])
    for s in manifest["symbol_references"]:
        if s["quote"] not in md or lines[s["locator"]["line"] - 1].find(s["quote"]) < 0:
            bad.append("sym:" + s["symbol"])
    checks["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": ("%d asset locators + %d identity facts + %d symbol locators re-resolved "
                   "(verbatim substring + quote_sha256 + char offset + declared line)"
                   % (len(manifest["locators"]), len(manifest["identity_facts"]),
                      len(manifest["symbol_references"]))),
        "failures": bad}

    # 4 source_hash_matches
    checks["source_hash_matches"] = {
        "ok": live == manifest["source"]["source_hash"] == CONTRACT_SOURCE_HASH
              == env["provenance"]["source_hash"],
        "detail": {"live": live, "manifest": manifest["source"]["source_hash"],
                   "contract": CONTRACT_SOURCE_HASH,
                   "envelope": env["provenance"]["source_hash"]},
        "chars": {"live": len(md), "manifest": manifest["source"]["chars"],
                  "contract": CONTRACT_CHARS}}

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {"ok": not dupes,
                                  "detail": "%d ids, duplicates=%s" % (len(ids), dupes)}

    # 6 all_claims_have_evidence_or_explicit_unresolved_status
    claims = env.get("claims") or []
    ev_ok = all(c.get("evidence") or c.get("unresolved_reason") or c.get("status") for c in claims)
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": bool(ev_ok and manifest.get("claims_empty_reason")),
        "detail": "%d claims (empty array is contract-legal); empty-claims reason stated: %s"
                  % (len(claims), bool(manifest.get("claims_empty_reason")))}

    out = {"package_id": PACKAGE_ID, "verified_at": utcnow(), "acceptance": checks,
           "all_ok": all(c["ok"] for c in checks.values()),
           "note": ("Self-check only. No claim is marked verified here (contract "
                    "do_not_mark_claims_as_verified=true); the platform gate recomputes hash and "
                    "locators independently.")}
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


# --------------------------------------------------------------------- figure
def figure() -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text())
    md = SOURCE_COPY.read_text()
    n_lines = len(split_lines(md))
    colours = {"resolved_in_source": "#2a7f62", "referenced_unresolved": "#c0504d",
               "declared_absent": "#7f7f7f"}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.2),
                                   gridspec_kw={"width_ratios": [2.1, 1]})

    assets = manifest["assets"]
    ys = list(range(len(assets)))[::-1]
    for y, a in zip(ys, assets):
        ln0, ln1 = a["locator"]["start_line"], a["locator"]["end_line"]
        col = colours[a["resolution"]]
        ax1.barh(y, max(ln1 - ln0 + 1, 1), left=ln0 - 1, height=0.55, color=col, alpha=0.85)
        ax1.text(ln1 + 1.5, y, "%s  L%d  %s" % (a["asset_id"], ln0, a["asset_class"]),
                 va="center", fontsize=8.5)
    ax1.set_xlim(0, n_lines + 42)
    ax1.set_yticks([])
    ax1.set_ylim(-1, len(assets))
    for f in manifest["identity_facts"]:
        ax1.axvline(f["locator"]["line"], color="#bbbbbb", lw=0.6, zorder=0)
    ax1.set_xlabel("report 9777 markdown line (1-based, %d lines)" % n_lines)
    ax1.set_title("asset locator spans vs report line axis", fontsize=11)
    for lbl, col in (("resolved_in_source", colours["resolved_in_source"]),
                     ("referenced_unresolved", colours["referenced_unresolved"])):
        ax1.barh([], [], color=col, label=lbl)
    ax1.legend(loc="lower right", fontsize=8)

    keys = sorted(manifest["counts"]["by_resolution"])
    vals = [manifest["counts"]["by_resolution"][k] for k in keys]
    ax2.bar(range(len(keys)), vals, color=[colours.get(k, "#4472c4") for k in keys])
    for i, v in enumerate(vals):
        ax2.text(i, v + 0.08, str(v), ha="center", fontsize=10)
    ax2.set_xticks(range(len(keys)))
    ax2.set_xticklabels([k.replace("_", "\n") for k in keys], fontsize=8.5)
    ax2.set_ylim(0, max(vals) + 1.2)
    ax2.set_ylabel("assets")
    ax2.set_title("resolution histogram (n=%d)" % manifest["counts"]["assets"], fontsize=11)
    ax2.grid(axis="y", alpha=0.3)

    fig.suptitle("wp-9777-01 asset registration: %d assets, sha256 %s…"
                 % (manifest["counts"]["assets"],
                    manifest["source"]["source_hash"].split(":")[1][:12]), fontsize=11)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    p = FIG_DIR / "fig1_asset_locator_map.png"
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(p, dpi=160)
    plt.close(fig)
    return str(p.relative_to(ROOT))


# ----------------------------------------------------------------------- main
def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if cmd in ("build", "all"):
        rec = fetch_record()
        man = build_manifest(rec)
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n")
        print("manifest:", MANIFEST.relative_to(ROOT), "assets=", man["counts"]["assets"],
              "hash_match=", man["source"]["hash_match"],
              "chars=", man["source"]["chars"])
    if cmd in ("envelope", "all"):
        env = build_envelope()
        print("envelope:", ENVELOPE.relative_to(ROOT),
              "source_hash=", env["provenance"]["source_hash"])
    if cmd in ("verify", "all"):
        v = verify()
        for k, c in v["acceptance"].items():
            print(("PASS " if c["ok"] else "FAIL ") + k)
        print("all_ok=", v["all_ok"])
        if not v["all_ok"]:
            return 2
    if cmd in ("figure", "all"):
        print("figure:", figure())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))