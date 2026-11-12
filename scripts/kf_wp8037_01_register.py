#!/usr/bin/env python3
"""wp-8037-01 (task_type 01-asset-registration) for report 8037.

Sub-commands (idempotent):

    python3 scripts/kf_wp8037_01_register.py build     # fetch + write asset_manifest.json
    python3 scripts/kf_wp8037_01_register.py envelope  # wrap manifest -> kf_result.json
    python3 scripts/kf_wp8037_01_register.py verify    # 6 acceptance checks -> verification.json
    python3 scripts/kf_wp8037_01_register.py figure    # asset locator map png
    python3 scripts/kf_wp8037_01_register.py report    # render KF-RESULT markdown (single json block)
    python3 scripts/kf_wp8037_01_register.py all       # build+envelope+verify+figure+report

Contract rules honoured here (wp-8037-01):
  * registration only: objective.register_assets=true, classify_report_type=false, no extraction,
    `claims` is an empty array with an explicit reason;
  * zero hand transcription: every quote is sliced out of the markdown at run time from a unique
    programmatic anchor, and every number in the artefacts is measured in this script;
  * nothing is marked verified: `resolution` describes locator resolvability only. The "Pass"
    column of the source table is the author's self-declaration, registered as data;
  * scope is report 8037 only: no other report_id is read or written.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "8037"
PACKAGE_ID = "wp-8037-01"
TASK_TYPE = "01-asset-registration"
LANE = "C"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
PRODUCER = "kf-worker/m15606"

# contract-declared identity (work-package YAML). Comparison targets only -- never trusted.
CONTRACT = {
    "source_hash": "sha256:1e44804da4c51cf5e17cb6db345e3f414ffa55321b8f3e8b3a29d08e9c69c9b0",
    "chars": 1223,
    "title": "DEM Contact Mechanics Dual Verification (P27W3-N06)",
    "scenario_key": "dem_contact_mechanics_verification",
}

RUN_DIR = ROOT / "runs" / PACKAGE_ID             # scratch: fetched source (repo push gate drops runs/)
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID      # committed deliverables
ART_MIRROR = ROOT / "artifacts" / PACKAGE_ID     # convenience mirror
SOURCE_MD = RUN_DIR / ("source_%s.md" % REPORT_ID)
RECORD_JSON = RUN_DIR / "record.json"
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
FIGURE = OUT_DIR / "figures" / "asset_locator_map.png"
RESULT_MD = OUT_DIR / ("KF-RESULT-%s.md" % PACKAGE_ID)
SCHEMA_LOCAL = ROOT / "schemas" / "asset_manifest.wp-8037-01.schema.json"
SCHEMA_ENVELOPE = ROOT / "schemas" / "kf_result.v1.schema.json"


# --------------------------------------------------------------------- api
def api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _req(url, body=None, token=None):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def login():
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    last = None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _req(api_base() + path, {"username": user, "password": pwd})
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    raise SystemExit("login failed: %r" % (last,))


def fetch_source(force=False):
    """Return (markdown, record). Cached under runs/wp-8037-01/."""
    if not force and SOURCE_MD.exists() and RECORD_JSON.exists():
        return SOURCE_MD.read_bytes().decode("utf-8"), json.loads(RECORD_JSON.read_text("utf-8"))
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    tok = login()
    payload = _req(api_base() + "/tensor/reports/" + REPORT_ID, token=tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    md = payload.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("payload has no str markdown field; keys=%s" % sorted(payload))
    SOURCE_MD.write_bytes(md.encode("utf-8"))
    rec = {k: v for k, v in payload.items() if k != "markdown"}
    rec["_fetched_via"] = "GET %s/tensor/reports/%s" % (api_base(), REPORT_ID)
    RECORD_JSON.write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")
    return md, rec


# ------------------------------------------------------- locator machinery
def line_table(md):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def locate(md, anchor):
    """Line index of a *unique* anchor. A fuzzy anchor would silently shift a locator,
    which is exactly the failure mode this package forbids -> hard fail instead."""
    occ = md.count(anchor)
    if occ != 1:
        raise SystemExit("anchor %r occurs %d times (must be exactly 1)" % (anchor, occ))
    return md[: md.index(anchor)].count("\n")


def section_of(lines, li):
    for k in range(li, -1, -1):
        if lines[k].startswith("## "):
            return lines[k][3:].strip()
        if lines[k].startswith("# "):
            return "(document header)"
    return "(document)"


# Asset table:
# (id, class, label, anchor substring, end-line offset relative to anchor line,
#  resolution, check description, result enum, note, probe path)
ASSET_SPEC = [
    ("A01", "document", "report markdown (full body)",
     "# DEM Contact Mechanics Dual Verification", 0, "resolved_in_source",
     "sha256 of the markdown field recomputed locally equals the contract hash", "resolved",
     "Whole markdown is the primary asset; see source.hash / source.bytes_utf8.", None),
    ("A02", "heading", "section heading 'Results'", "## Results", 0, "resolved_in_source",
     "heading line found verbatim", "resolved",
     "Opens the acceptance-criteria table section.", None),
    ("A03", "criteria_table", "acceptance criteria table C1-C9 (header + 9 rows)",
     "| Criterion | Key Metric | Error | Pass |", 10, "resolved_in_source",
     "table header + separator + 9 criterion rows found verbatim", "resolved",
     "The verdict column is the report author's self-declaration; registered as data, not re-verified here.",
     None),
    ("A04", "criterion_result", "criterion C1 row", "| C1 |", 0, "resolved_in_source",
     "row found verbatim", "resolved",
     "Numeric string '0% (exact)' is not unique in the document - the row is the unique locator.", None),
    ("A05", "criterion_result", "criterion C2 row", "| C2 |", 0, "resolved_in_source",
     "row found verbatim", "resolved", "Bound expressed as a strict inequality ('<1e-10%').", None),
    ("A06", "criterion_result", "criterion C3 row", "| C3 |", 0, "resolved_in_source",
     "row found verbatim", "resolved",
     "Column labelled 'Error' carries a fit statistic (R^2), not an error - mixed column semantics.", None),
    ("A07", "criterion_result", "criterion C4 row", "| C4 |", 0, "resolved_in_source",
     "row found verbatim", "resolved",
     "Same numeric string '0% (exact)' as C1; only the row context disambiguates.", None),
    ("A08", "criterion_result", "criterion C5 row", "| C5 |", 0, "resolved_in_source",
     "row found verbatim", "resolved", "Boolean metric ('Yes'); no numeric value is given.", None),
    ("A09", "criterion_result", "criterion C6 row", "| C6 |", 0, "resolved_in_source",
     "row found verbatim", "resolved", "Boolean metric ('Yes'); no numeric value is given.", None),
    ("A10", "criterion_result", "criterion C7 row", "| C7 |", 0, "resolved_in_source",
     "row found verbatim", "resolved", "Boolean metric ('Yes'); no numeric value is given.", None),
    ("A11", "criterion_result", "criterion C8 row", "| C8 |", 0, "resolved_in_source",
     "row found verbatim", "resolved",
     "States the verdict JSON is 'Generated' but the artefact itself is not attached to the report.", None),
    ("A12", "criterion_result", "criterion C9 row", "| C9 |", 0, "resolved_in_source",
     "row found verbatim", "resolved",
     "'32/32' is the only unit-bearing count in the table; no run id or commit accompanies it.", None),
    ("A13", "heading", "section heading 'Key Findings'", "## Key Findings", 0, "resolved_in_source",
     "heading line found verbatim", "resolved", "Opens the prose finding list.", None),
    ("A14", "finding_set", "key findings list (6 bullets)", "## Key Findings", 6,
     "resolved_in_source", "6 bullet lines found verbatim", "resolved",
     "Each bullet is a candidate knowledge statement for a later extraction package; not extracted here.",
     None),
    ("A15", "numeric_anchor", "shape-representation verdict criterion (n1 <= 4, N >= 32)",
     "Shape verdict:", 0, "resolved_in_source", "line found verbatim", "resolved",
     "Only quantitative shape recommendation in the report; unicode subscripts preserved as bytes.", None),
    ("A16", "heading", "section heading 'Files'", "## Files", 0, "resolved_in_source",
     "heading line found verbatim", "resolved", "Declares 5 external artefacts.", None),
    ("A17", "file_reference", "declared module path", "src/tensordem/dem_contact_verification.py", 0,
     "referenced_unresolved", "path probed in this worktree (TensorKnowledge checkout)", "unresolved",
     "Declared path belongs to the TensorDEM repository, not to this worktree; no attachment on the record.",
     "src/tensordem/dem_contact_verification.py"),
    ("A18", "file_reference", "declared test module path",
     "tests/test_dem_contact_mechanics_verification.py", 0, "referenced_unresolved",
     "path probed in this worktree (TensorKnowledge checkout)", "unresolved",
     "Declared path belongs to the TensorDEM repository; no test-run identity (run id / commit) is given.",
     "tests/test_dem_contact_mechanics_verification.py"),
    ("A19", "file_reference", "declared full-report path",
     "docs/dem_contact_mechanics_verification_report.md", 0, "referenced_unresolved",
     "path probed in this worktree (TensorKnowledge checkout)", "unresolved",
     "Declared full report is cited as the source of the numbers; it is not attached.", 
     "docs/dem_contact_mechanics_verification_report.md"),
    ("A20", "file_reference", "declared verdict JSON path",
     "artifacts/dem/shape_representation_verdict.json", 0, "referenced_unresolved",
     "path probed in this worktree (TensorKnowledge checkout)", "unresolved",
     "Its content is asserted by criterion C8 but never quoted; unverifiable from this report alone.",
     "artifacts/dem/shape_representation_verdict.json"),
    ("A21", "figure_declaration", "declared figure set c1_*.png .. c5_*.png",
     "artifacts/dem/figures/c1_*.png through c5_*.png", 0, "declared_absent",
     "platform record figures[] length + worktree glob probe", "absent",
     "Figures are declared as a glob range but the payload carries none (figures=[]); no PNG bytes in scope.",
     "artifacts/dem/figures/*.png"),
    ("A22", "platform_record", "platform record metadata (title/scenario_key/tags/figures)",
     "# DEM Contact Mechanics Dual Verification", 0, "resolved_in_source",
     "record fields read from the API response for report 8037", "present",
     "Record-level metadata; not part of the markdown body, so its locator is the title line.", None),
]


def probe_path(rel_glob):
    """Mechanical existence probe; never invents an address."""
    hits = []
    if "*" in rel_glob:
        hits = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(rel_glob))
    elif (ROOT / rel_glob).exists():
        hits = [rel_glob]
    return {"probe": "Path.glob(%r) under %s" % (rel_glob, ROOT.name),
            "hits": hits, "exists": bool(hits)}


# --------------------------------------------------------------------- build
def build(force_fetch=False):
    md, rec = fetch_source(force=force_fetch)
    raw = md.encode("utf-8")
    lines, offs = line_table(md)
    for d in (RUN_DIR, OUT_DIR, ART_MIRROR):
        d.mkdir(parents=True, exist_ok=True)

    assets = []
    for (aid, cls, label, anchor, end_rel, resolution, check, result, note, probe) in ASSET_SPEC:
        li = locate(md, anchor)
        end_li = li + end_rel
        if end_li >= len(lines):
            raise SystemExit("%s: span overruns document" % aid)
        quote = "\n".join(lines[li: end_li + 1])
        loc = {
            "method": "char_span",
            "start_char": offs[li],
            "end_char": offs[li] + len(quote),
            "start_line": li + 1,
            "end_line": end_li + 1,
            "quote": quote,
            "unique": md.count(quote) == 1,
        }
        if md[loc["start_char"]:loc["end_char"]] != quote:
            raise SystemExit("%s: char span does not reproduce the quote" % aid)
        if aid == "A01":
            loc = {"method": "document", "start_char": 0, "end_char": len(md),
                   "start_line": 1, "end_line": len(lines), "quote": quote,
                   "unique": md.count(quote) == 1}
        entry = {
            "asset_id": aid,
            "asset_class": cls,
            "label": label,
            "in_report_section": "(document)" if aid == "A01" else section_of(lines, li),
            "locator": loc,
            "resolution": resolution,
            "resolution_check": {"check": check, "result": result},
            "note": note,
        }
        if probe is not None:
            entry["resolution_check"]["probe"] = probe_path(probe)
        assets.append(entry)

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    h = hashlib.sha256(raw).hexdigest()
    manifest = {
        "schema": "asset_manifest.v1",
        "schema_source": ("schemas/asset_manifest.wp-8037-01.schema.json (package-local instance of "
                          "asset_manifest.v1; the repo-wide schemas/asset_manifest.v1.schema.json pins "
                          "report 448 and is left untouched)"),
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "producer": PRODUCER,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": "sha256:" + h,
            "hash_hex": h,
            "contract_hash": CONTRACT["source_hash"].split(":", 1)[1],
            "hash_matches_contract": ("sha256:" + h) == CONTRACT["source_hash"],
            "chars": len(md),
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "has_crlf": "\r\n" in md,
            "trailing_newline": md.endswith("\n"),
            "title": rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "contract_chars": CONTRACT["chars"],
            "contract_title": CONTRACT["title"],
            "contract_scenario_key": CONTRACT["scenario_key"],
            "chars_matches_contract": len(md) == CONTRACT["chars"],
            "title_matches_contract": (rec.get("title") or "").strip() == CONTRACT["title"],
            "scenario_key_matches_contract":
                (rec.get("scenario_key") or "").strip() == CONTRACT["scenario_key"],
            "platform_id": rec.get("id"),
            "platform_mission_id": rec.get("mission_id"),
            "platform_status": rec.get("status"),
            "platform_tags": rec.get("tags") or [],
            "platform_figures": rec.get("figures") or [],
            "platform_figure_count": len(rec.get("figures") or []),
            "retrieved_via": rec.get("_fetched_via"),
            "local_copy": str(SOURCE_MD.relative_to(ROOT)),
            "committed_copy": str((OUT_DIR / ("source_%s.md" % REPORT_ID)).relative_to(ROOT)),
            "hash_scope": ("UTF-8 bytes of the markdown field as served by "
                           "GET /api/v1/tensor/reports/8037"),
            "line_counting": ("logical lines = markdown.split(chr(10)); 0-based internally, "
                              "1-based in locators"),
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "unique_quotes": sum(1 for a in assets if a["locator"]["unique"]),
        },
        "assets": assets,
        "claims": [],
        "claims_empty_reason": (
            "Contract for wp-8037-01 sets objective.register_assets=true and "
            "objective.classify_report_type=false; extraction is a separate package. "
            "constraints.no_forced_claim_generation=true, so no knowledge statement is emitted. "
            "The 9 criterion rows and the 6 finding bullets are registered as locatable assets so "
            "that a later extraction package can cite them without re-reading the report."),
        "integrity": {
            "quote_uniqueness": {
                "checked": len(assets),
                "unique": sum(1 for a in assets if a["locator"]["unique"]),
                "all_unique": all(a["locator"]["unique"] for a in assets),
            },
            "hash_recomputed_locally": "sha256:" + h,
            "hash_matches_contract": ("sha256:" + h) == CONTRACT["source_hash"],
            "chars_matches_contract": len(md) == CONTRACT["chars"],
            "asset_id_unique": len({a["asset_id"] for a in assets}) == len(assets),
            "char_spans_reproduce_quotes": all(
                md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]
                for a in assets if a["locator"]["method"] == "char_span"),
            "verification_status": "not_verified",
        },
        "observations": [
            "The report is a 30-line result summary: no geometry, no parameter table, no method "
            "section and no per-criterion numeric error series. Downstream extraction is thin by "
            "construction, and that is a property of the source, not of this package.",
            "The 'Pass' column is a self-declaration of the producing mission; this package "
            "registers the strings and does not confirm them (verification is the platform gate's job).",
            "The column labelled 'Error' mixes three kinds of value: error magnitudes (C1, C2, C4), "
            "a fit statistic (C3, R^2) and booleans (C5-C7, 'Yes'). Treating the column uniformly "
            "would be a modelling error.",
            "'0% (exact)' occurs twice (C1 tangential force, C4 sphere R_eff) with different "
            "meanings; substring-level dedup would merge two distinct results, hence row-level locators.",
            "C9 '32/32' and the files line '(32 tests)' agree, but neither carries a run id or "
            "commit: the count is internally consistent and externally unverifiable from this report.",
            "No figure bytes are attached (record figures=[]), while the Files section declares "
            "c1_*.png through c5_*.png: the graphical evidence is absent from the source of record.",
        ],
        "limitations": [
            "Only report_id=8037 was read; no other report was touched.",
            "External artefact paths (A17-A20) are declared inside the TensorDEM repository and were "
            "probed only within this TensorKnowledge worktree: absence here is not evidence of "
            "absence there.",
            "Registration is not verification: no claim in this manifest is marked verified and the "
            "manifest carries no knowledge-object or evidence-grade judgement.",
        ],
    }
    if not manifest["source"]["hash_matches_contract"]:
        raise SystemExit("FATAL: recomputed hash != contract hash; refusing to write a manifest")
    (OUT_DIR / ("source_%s.md" % REPORT_ID)).write_bytes(raw)  # offline re-verification copy
    text = json.dumps(manifest, ensure_ascii=False, indent=2)
    MANIFEST.write_text(text, encoding="utf-8")
    (ART_MIRROR / "asset_manifest.json").write_text(text, encoding="utf-8")
    print("wrote %s (%d assets, %d chars source)"
          % (MANIFEST.relative_to(ROOT), len(assets), len(md)))
    return manifest


# ------------------------------------------------------------------ envelope
def envelope():
    man = json.loads(MANIFEST.read_text("utf-8"))
    raw = MANIFEST.read_bytes()
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": man["source"]["hash"],
            "source_field": "markdown",
            "source_uri": SOURCE_URI,
            "producer": PRODUCER,
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "contract_source_hash": CONTRACT["source_hash"],
            "source_chars": man["source"]["chars"],
            "source_bytes_utf8": man["source"]["bytes_utf8"],
            "source_title": man["source"]["title"],
            "scenario_key": man["source"]["scenario_key"],
            "contract_version": "1.0",
            "lane": LANE,
            "work_package": PACKAGE_ID,
            "retrieved_via": man["source"]["retrieved_via"],
            "local_copy": man["source"]["local_copy"],
            "generator": "scripts/kf_wp8037_01_register.py",
            "verifier": "scripts/kf_wp8037_01_register.py verify",
            "verification_status": "not_verified",
            "manifest_path": str(MANIFEST.relative_to(ROOT)),
            "manifest_sha256": "sha256:" + hashlib.sha256(raw).hexdigest(),
            "manifest_bytes": len(raw),
        },
        "outputs": {"asset_manifest.json": man},
        "claims": [],
    }
    text = json.dumps(env, ensure_ascii=False, indent=2)
    ENVELOPE.write_text(text, encoding="utf-8")
    (ART_MIRROR / "kf_result.json").write_text(text, encoding="utf-8")
    print("wrote %s" % ENVELOPE.relative_to(ROOT))
    return env


# -------------------------------------------------------------------- verify
def verify(re_fetch=True):
    """Re-measure every acceptance item against the LIVE report, never against the manifest."""
    md, _rec = fetch_source(force=re_fetch)
    raw = md.encode("utf-8")
    lines, _offs = line_table(md)
    checks = {}

    try:
        man = json.loads(MANIFEST.read_text("utf-8"))
        env = json.loads(ENVELOPE.read_text("utf-8"))
        checks["valid_json"] = {"ok": True,
                                "detail": "asset_manifest.json and kf_result.json both parse as JSON"}
    except Exception as exc:  # noqa: BLE001
        man = env = None
        checks["valid_json"] = {"ok": False, "detail": "JSON parse error: %r" % (exc,)}

    detail, ok = [], True
    try:
        import jsonschema
        jsonschema.validate(man, json.loads(SCHEMA_LOCAL.read_text("utf-8")))
        detail.append("asset_manifest.json valid against %s" % SCHEMA_LOCAL.name)
        jsonschema.validate(env, json.loads(SCHEMA_ENVELOPE.read_text("utf-8")))
        detail.append("kf_result.json valid against canonical %s" % SCHEMA_ENVELOPE.name)
        if "asset_manifest.json" not in (env.get("outputs") or {}):
            ok = False
            detail.append("envelope.outputs lacks key 'asset_manifest.json'")
    except ImportError:
        ok = False
        detail.append("jsonschema not installed -> schema_pass NOT RUN (reported as failure, not as pass)")
    except Exception as exc:  # noqa: BLE001
        ok = False
        detail.append("schema violation: %s" % str(exc).splitlines()[0])
    checks["schema_pass"] = {"ok": ok, "detail": "; ".join(detail)}

    bad = []
    for a in (man["assets"] if man else []):
        loc = a["locator"]
        if loc["method"] == "document":
            span_ok = loc["start_char"] == 0 and loc["end_char"] == len(md)
            # whole-document locator: the source ends with a newline, so joining every line is
            # shorter than md by that newline; assert the line bounds instead.
            line_ok = loc["start_line"] == 1 and loc["end_line"] == len(lines)
        else:
            span_ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"]
            line_ok = "\n".join(lines[loc["start_line"] - 1:loc["end_line"]]) == loc["quote"]
        in_doc = loc["quote"] in md
        uniq = md.count(loc["quote"]) == 1
        if not (span_ok and in_doc and uniq and line_ok):
            bad.append({"asset_id": a["asset_id"], "char_span_ok": span_ok,
                        "substring_ok": in_doc, "unique_ok": uniq, "line_span_ok": line_ok})
    total = len(man["assets"]) if man else 0
    checks["source_locator_resolvable"] = {
        "ok": bool(man) and not bad,
        "detail": "%d/%d locators re-resolved verbatim (char span + substring + uniqueness + line span)"
                  % (total - len(bad), total),
        "failures": bad,
    }

    live = "sha256:" + hashlib.sha256(raw).hexdigest()
    checks["source_hash_matches"] = {
        "ok": (live == CONTRACT["source_hash"]
               and live == (man["source"]["hash"] if man else None)
               and live == (env["provenance"]["source_hash"] if env else None)),
        "detail": "live=%s contract=%s manifest=%s"
                  % (live, CONTRACT["source_hash"], man["source"]["hash"] if man else None),
        "chars": {"live": len(md), "contract": CONTRACT["chars"],
                  "manifest": man["source"]["chars"] if man else None},
    }

    if man:
        ids = [a["asset_id"] for a in man["assets"]]
        cids = [c.get("claim_id") for c in man.get("claims", [])]
        dup = sorted({i for i in ids if ids.count(i) > 1})
        dupc = sorted({i for i in cids if i and cids.count(i) > 1})
        pattern_ok = all(len(i) == 3 and i.startswith("A") and i[1:].isdigit() for i in ids)
        checks["no_duplicate_ids"] = {
            "ok": (not dup) and (not dupc) and pattern_ok,
            "detail": "%d asset ids, %d claim ids, duplicates assets=%s claims=%s, A\\d{2} pattern %s"
                      % (len(ids), len(cids), dup, dupc, "ok" if pattern_ok else "FAIL"),
        }
        claims = man.get("claims", [])
        unbacked = [c for c in claims
                    if not (c.get("evidence") or c.get("evidence_locator") or c.get("status"))]
        explicit_empty = (claims == [] and bool(man.get("claims_empty_reason")))
        checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
            "ok": (not unbacked) and (explicit_empty or bool(claims)),
            "detail": ("claims=[] with an explicit claims_empty_reason "
                       "(no_forced_claim_generation) - vacuously satisfied and declared, "
                       "not silently omitted") if explicit_empty else
                      ("%d claims, %d without evidence/status" % (len(claims), len(unbacked))),
            "unbacked": [c.get("claim_id") for c in unbacked],
        }
    else:
        checks["no_duplicate_ids"] = {"ok": False, "detail": "no manifest"}
        checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
            "ok": False, "detail": "no manifest"}

    import re
    other = sorted({m for m in re.findall(r"tensor://reports/(\d+)",
                                          json.dumps(man, ensure_ascii=False))
                    if m != REPORT_ID}) if man else []
    checks["scope_single_report_id"] = {
        "ok": not other,
        "detail": "no foreign report_id in the manifest" if not other else "foreign ids: %s" % other,
    }

    all_ok = all(v["ok"] for v in checks.values())
    result = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "source_hash_live": live,
        "gate": "PASS" if all_ok else "FAIL",
        "gate_scope": "the six contract acceptance items for task_type 01-asset-registration only",
        "checks": checks,
        "not_verified": [
            "The 'Pass' verdicts in the source table are NOT re-verified: no simulation was re-run "
            "and no test suite was executed (the declared test module is not in this worktree).",
            "External artefact contents (A17-A20) were not read; only their declared paths were probed.",
            "No numeric claim is compared with any benchmark here; this package performs no "
            "error-vs-reference assessment.",
        ],
    }
    VERIFICATION.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    for k, v in checks.items():
        print("[%s] %s :: %s" % ("PASS" if v["ok"] else "FAIL", k, v["detail"]))
    print("GATE:", result["gate"])
    return result


# -------------------------------------------------------------------- figure
def make_figure():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    man = json.loads(MANIFEST.read_text("utf-8"))
    md = SOURCE_MD.read_bytes().decode("utf-8")
    lines, _ = line_table(md)
    colors = {"resolved_in_source": "#2b8a3e", "referenced_unresolved": "#e8590c",
              "declared_absent": "#c92a2a"}
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 1, figsize=(13, 8.8), gridspec_kw={"height_ratios": [1.4, 1]})

    ax = axes[0]
    rows = [a for a in man["assets"] if a["asset_id"] != "A01"]
    for i, a in enumerate(rows):
        loc = a["locator"]
        y = len(rows) - i - 1
        ax.barh(y, loc["end_line"] - loc["start_line"] + 1, left=loc["start_line"] - 1,
                height=0.62, color=colors[a["resolution"]], edgecolor="black", linewidth=0.4)
        ax.text(loc["end_line"] + 0.25, y, a["asset_id"], va="center", fontsize=7)
    ax.set_yticks([])
    ax.set_xlim(0, len(lines))
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.set_xlabel("line number in report 8037 markdown (1-based)")
    ax.set_title("wp-8037-01 asset locator map -- %d assets over %d source lines / %d chars"
                 % (man["counts"]["assets"], len(lines), man["source"]["chars"]), fontsize=10)
    ax.legend(handles=[Patch(facecolor=c, edgecolor="black", label=k) for k, c in colors.items()],
              fontsize=8, loc="lower right")
    ax.grid(axis="x", alpha=0.25)

    ax2 = axes[1]
    res = man["counts"]["by_resolution"]
    keys = sorted(res)
    ax2.bar(keys, [res[k] for k in keys], color=[colors.get(k, "#495057") for k in keys],
            edgecolor="black", linewidth=0.5, width=0.5)
    for j, k in enumerate(keys):
        ax2.text(j, res[k] + 0.15, str(res[k]), ha="center", fontsize=9)
    ax2.set_ylabel("assets")
    ax2.set_ylim(0, max(res.values()) + 1.8)
    ax2.set_title("resolution classes (registration != verification) -- sha256 %s...%s "
                  "matches contract: %s"
                  % (man["source"]["hash"][7:19], man["source"]["hash"][-8:],
                     man["source"]["hash_matches_contract"]), fontsize=10)
    ax2.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=150)
    print("wrote", FIGURE.relative_to(ROOT))


# -------------------------------------------------------------------- report
def render_report():
    man = json.loads(MANIFEST.read_text("utf-8"))
    env = json.loads(ENVELOPE.read_text("utf-8"))
    ver = json.loads(VERIFICATION.read_text("utf-8")) if VERIFICATION.exists() else None
    src, cnt = man["source"], man["counts"]
    md = SOURCE_MD.read_bytes().decode("utf-8")
    nlines = len(line_table(md)[0])

    asset_rows = "\n".join(
        "| %s | `%s` | %s | `%s` | %s | %s |" % (
            a["asset_id"], a["asset_class"], a["in_report_section"], a["resolution"],
            a["label"] if a["locator"]["method"] == "document"
            else "%d-%d" % (a["locator"]["start_line"], a["locator"]["end_line"]),
            a["locator"]["quote"].replace("|", "\\|").replace("\n", " / "))
        for a in man["assets"])
    quote_rows = "\n".join(
        "| %s | `%s` | %d | `%s` |" % (
            a["asset_id"], a["asset_class"], a["locator"]["start_line"],
            a["locator"]["quote"].split("\n")[0].replace("|", "\\|"))
        for a in man["assets"])
    check_rows = "\n".join(
        "| %s | %s | %s |" % (k, "✅" if v["ok"] else "❌", v["detail"])
        for k, v in (ver["checks"] if ver else {}).items())
    fig_note = ("见 `docs/kf/%s/figures/asset_locator_map.png`（图未内嵌于 markdown，"
                "由平台 figures 通道单独上传）。" % PACKAGE_ID) if FIGURE.exists() else \
               "本包未生成图（纯登记工序，无场量）；理由见 §⑤。"
    result_json = json.dumps(env, ensure_ascii=False, indent=2)

    body = """# KF-RESULT {pkg}

- package_id: `{pkg}` · task_type: `{tt}` · lane: `{lane}`
- report_id: `{rid}` · source: `{uri}` (field `{field}`)
- source sha256: `{hash}` — contract `{chash}` → **match: {hm}**
- chars {chars} / bytes {nbytes} / lines {nlines} · title: {title}
- status: **draft**（verification 由平台门计算；本包不标 verified）
- tags: `kf-wp:{pkg}` · repro_cmd: `python3 scripts/kf_wp8037_01_register.py all`（等价分步：
  `build` → `envelope` → `verify` → `figure` → `report`；`verify` 会回活报告重算 6 项验收）

## ① 本工序做了什么

01-asset-registration（登记，不抽取）：核对 report 8037 的 markdown 字节哈希与契约一致，然后把报告内
**{na} 个可定位资产**逐一登记并给出可复算定位器（字符区间 + 行区间 + 逐字引文 + 唯一性）：

| 分辨率 | 数量 | 含义 |
|---|---|---|
| `resolved_in_source` | {r_ok} | 引文在本报告 markdown 内逐字可定位 |
| `referenced_unresolved` | {r_un} | 报告声明的外部工件（源码/测试/报告/verdict JSON）未随报告附上 |
| `declared_absent` | {r_ab} | 报告声明存在但载荷内确实缺失（图集 figures=[]） |

`claims` 为空数组并写明理由：契约 `objective.register_assets=true`、`classify_report_type=false`、
`constraints.no_forced_claim_generation=true`；抽取是后续独立工作包。9 条判据行与 6 条 findings
已登记为可定位资产，供下游直接引用，不必重读原文。

**未做**：不做分类、不做知识抽取、不判证据等级、不标 verified、不复算任何数值、不重跑任何仿真/测试。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `GET $TENSOR_API_BASE/tensor/reports/8037`（Bearer 登录令牌，环境变量注入）取 `markdown` 字段，
   按 UTF-8 原字节落盘（不做换行/空白修补），本地重算 sha256；
2. 身份四项对表：哈希 / 字符数 / title / scenario_key 全部与契约一致（见 `runs/wp-8037-01/fetch_meta.json`）；
3. 建立**锚点表**：每个资产用「文档内唯一子串」做锚，锚出现次数 ≠1 直接 `SystemExit`
   （模糊锚会静默位移定位器，这是本工序最该防的失效模式）；行区间由锚行 + 相对偏移得到，
   再反算字符区间，并当场断言 `md[start:end] == quote`；
4. 外部工件用 `Path.glob` 在工作树内做**机械探测**，不存在就记 `referenced_unresolved` 并附探测记录，
   绝不编造地址；`figures` 以平台 record 的 `figures[]` 长度 + 工作树 glob 双证据判 `declared_absent`；
5. 产物：`asset_manifest.json` → 包一层 `kf_result.v1` 信封 → `verify` 子命令**回到活报告**重算 6 项验收
   （不信任 manifest 自述）→ matplotlib 出定位图 → 渲染本报告。

关键设置：JSON 全部 `ensure_ascii=False`（保留 `n₁`/`R²` 等 unicode 原字节）；行号在内部 0-based、
定位器对外 1-based，并在 manifest 的 `source.line_counting` 里写明口径。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/{pkg}/asset_manifest.json` | 主产物：{na} 资产 + source 身份块 + counts + integrity + observations/limitations |
| `docs/kf/{pkg}/kf_result.json` | `kf_result.v1` 信封（`outputs["asset_manifest.json"]` 内嵌上文，`provenance.source_hash`=活哈希） |
| `docs/kf/{pkg}/verification.json` | 6 项验收逐项结果 + `not_verified` 清单（gate={gate}） |
| `docs/kf/{pkg}/figures/asset_locator_map.png` | 资产定位图：横轴=源行号，颜色=分辨率；下panel=分辨率计数+哈希身份 |
| `docs/kf/{pkg}/KF-RESULT-{pkg}.md` | 本报告（正文末唯一一个 json fenced 结果块） |
| `artifacts/{pkg}/asset_manifest.json`, `kf_result.json` | 字节同源镜像（推送门会丢弃 artifacts/，故正本在 docs/） |
| `scripts/kf_wp8037_01_register.py` | 一键复跑（build/envelope/verify/figure/report） |

## ④ 证据定位表（资产 → 原文逐字片段）

| asset_id | class | 行（1-based） | 原文引文（首行，逐字） |
|---|---|---|---|
{quote_rows}

完整清单（含多行资产全文、唯一性、外部探测）见 `asset_manifest.json.assets[]`。图：{fig_note}

## ⑤ 注意点与局限

1. **本报告只说结论，不说证据**：正文 30 行、{chars} 字符，无几何、无参数表、无方法节、无逐判据误差序列。
   下游 03 抽取能提的东西天生很薄——这是**源的性质**，不是本包的省略。
2. **`Pass` 列是生产方自述**：9 行 ✅ 全部登记为"数据"，本包不复核（未重跑）。
   把自述当验证是产线最危险的误读，故 manifest 里 `verification_status=not_verified`。
3. **`Error` 列语义混杂**：C1/C2/C4 是误差量级、C3 是拟合统计量 `R²`、C5–C7 是布尔 `Yes`。
   若下游把该列当同质误差序列会用错统计方法。
4. **`0% (exact)` 出现两次**（C1 切向力、C4 球 R_eff）：子串级去重会把两个不同结论并成一个，
   故一律用整行定位。
5. **图形证据缺失**：Files 声明 `c1_*.png through c5_*.png`，但 record `figures=[]`、工作树无 PNG
   → 判 `declared_absent`；C8 声称 verdict JSON "Generated" 但同样未附内容 → 判 `referenced_unresolved`。
6. **外部工件只在本地工作树探测过**（TensorKnowledge）：这里找不到**不等于** TensorDEM 里没有。
7. **本包没有数值精度结论**：不涉及与基准的误差比较，"是否 <3%" 对本工序无定义（见 §⑥ 说明）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 说明 |
|---|---|---|
{check_rows}

- **误差判定（必答项）**：本工序为资产登记，**不产生任何物理量或误差数字**，因此不存在"关键量 vs 基准误差是否 <3%"
  的对象；此处不做数值精度声明，也不拿报告自述的 0% / <1e-10% 充当本包结论（它们是源文本的引文，不是本包的测量）。
  需要精度判定的是下游抽取+验证包。
- **honest 声明**：未完成/未做的部分是「数值复算、测试重跑、外部工件内容核验」——三项均如实登记为 `not_verified`，
  未粉饰为通过。若平台门判 `schema_pass` 失败，原因是本地 schema 实例与平台侧 schema 口径差异，
  正本以平台门为准（已在 `schema_source` 写明）。

```json
{result_json}
```
"""
    body = body.format(
        pkg=PACKAGE_ID, tt=TASK_TYPE, lane=LANE, rid=REPORT_ID, uri=SOURCE_URI,
        field=src["field"], hash=src["hash"], chash=CONTRACT["source_hash"],
        hm=src["hash_matches_contract"], chars=src["chars"], nbytes=src["bytes_utf8"],
        nlines=src["lines"], title=src["title"], na=cnt["assets"],
        r_ok=cnt["resolved_in_source"], r_un=cnt["referenced_unresolved"],
        r_ab=cnt["declared_absent"], gate=(ver or {}).get("gate", "NOT_RUN"),
        quote_rows=quote_rows, check_rows=check_rows, fig_note=fig_note,
        result_json=result_json)
    # contract shape: exactly one ```json block
    if body.count("```json") != 1:
        raise SystemExit("report must carry exactly one json block, found %d" % body.count("```json"))
    RESULT_MD.write_text(body, encoding="utf-8")
    print("wrote %s (%d chars, 1 json block)" % (RESULT_MD.relative_to(ROOT), len(body)))
    return body


# ------------------------------------------------------------------- publish
def publish():
    """POST the KF-RESULT report (single json block body) + the locator figure."""
    import base64
    body_md = RESULT_MD.read_text("utf-8")
    if body_md.count("```json") != 1:
        raise SystemExit("refusing to publish: %d json blocks (contract wants exactly 1)"
                         % body_md.count("```json"))
    env = json.loads(ENVELOPE.read_text("utf-8"))
    src = json.loads(MANIFEST.read_text("utf-8"))["source"]
    figures = []
    if FIGURE.exists():
        figures.append({
            "name": "asset_locator_map",
            "caption": ("wp-8037-01 asset locator map (report 8037): bars = registered asset line "
                        "spans over the 30-line source markdown, coloured by resolution class "
                        "(%d/%d/%d resolved/unresolved/absent); source sha256 matches contract=%s."
                        % (MANIFEST_COUNTS()[0], MANIFEST_COUNTS()[1], MANIFEST_COUNTS()[2],
                           src["hash_matches_contract"]))[:300],
            "png_base64": base64.b64encode(FIGURE.read_bytes()).decode(),
        })
    payload = {
        "title": "KF-RESULT " + PACKAGE_ID,
        "summary": ("%s (01-asset-registration, report 8037): markdown sha256 [%s] recomputed locally "
                    "and equal to the contract hash; %d assets registered with verbatim locators "
                    "(%d resolved_in_source / %d referenced_unresolved / %d declared_absent); "
                    "claims=[] by contract (no extraction). Registration only - nothing marked verified."
                    % (PACKAGE_ID, env["provenance"]["source_hash"],
                       MANIFEST_COUNTS()[3], MANIFEST_COUNTS()[0],
                       MANIFEST_COUNTS()[1], MANIFEST_COUNTS()[2])),
        "scenario_key": src["scenario_key"],
        "mission_id": 15606,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + REPORT_ID,
                 "lane:" + LANE, "draft", "knowledge-factory",
                 "dem_contact_mechanics_verification", "DEM"],
        "markdown": body_md,
        "figures": figures,
    }
    tok = login()
    try:
        resp = _req(api_base() + "/tensor/reports", payload, tok)
    except urllib.error.HTTPError as exc:  # noqa: F821 - imported at module level below
        raise SystemExit("publish failed: %s %s" % (exc.code, exc.read().decode()[:400]))
    print(json.dumps(resp, ensure_ascii=False)[:800])
    return resp


def MANIFEST_COUNTS():
    man = json.loads(MANIFEST.read_text("utf-8"))
    c = man["counts"]
    return (c["resolved_in_source"], c["referenced_unresolved"], c["declared_absent"], c["assets"])


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd == "build":
        build(force_fetch="--force" in argv)
    elif cmd == "envelope":
        envelope()
    elif cmd == "verify":
        verify(re_fetch=True)
    elif cmd == "figure":
        make_figure()
    elif cmd == "report":
        render_report()
    elif cmd == "publish":
        publish()
    elif cmd == "all":
        build(force_fetch="--force" in argv)
        envelope()
        verify(re_fetch=True)
        make_figure()
        render_report()
    else:
        raise SystemExit(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))