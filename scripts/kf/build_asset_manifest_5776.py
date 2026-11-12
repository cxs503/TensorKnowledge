#!/usr/bin/env python3
"""Work package wp-5776-01 (01-asset-registration) — asset manifest builder + verifier.

Scope guard: touches ONLY report_id=5776. No extraction, no claims, no verification
marks (verification is computed by the platform gate, not here).

Zero hand-copying: every locator quote is sliced out of the fetched markdown by line
range (`"\n".join(lines[a-1:b])`), never retyped, so `quote` is verbatim by
construction. Offsets are the offsets of those bytes in the source string.

Usage:
  python3 scripts/kf/build_asset_manifest_5776.py build
  python3 scripts/kf/build_asset_manifest_5776.py verify
  python3 scripts/kf/build_asset_manifest_5776.py result
  python3 scripts/kf/build_asset_manifest_5776.py build verify result   # one-shot
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts" / "kf"))
from fetch_report_5776 import OUT as RUNS_DIR  # noqa: E402
from fetch_report_5776 import login  # noqa: E402
from fetch_report_5776 import _req  # noqa: E402

PKG = "wp-5776-01"
REPORT_ID = "5776"
SOURCE_URI = "tensor://reports/5776"
SOURCE_FIELD = "markdown"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "49089e9b193af49f9ffcf4f35b8a82b6f4deec5da07edc8e654fc7902385c04f"
EXPECTED_CHARS = 4950
EXPECTED_TITLE = (
    "Ice Floe Drift DEM-LBM Coupled Benchmark: Analytical Anchor for "
    "Two-Phase Coupling Verification"
)
EXPECTED_SCENARIO = "IN12-S7-ice-floe-drift-dem-lbm"

OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
VERDICT = OUT_DIR / "verification.json"
RESULT = OUT_DIR / "kf_result.wp-5776-01.json"
SCHEMA_ASSET = OUT_DIR / "asset_manifest.v1_5776.schema.json"
SCHEMA_KF = OUT_DIR / "kf_result.v1.schema.json"

# ---------------------------------------------------------------------------
# Asset registry: (asset_id, asset_class, label, section, kind, span|figure)
# `kind` explains *how* the asset is materialised:
#   figure_attachment  -> markdown image with attachment: URI (bytes not in repo)
#   file_reference     -> path cited in the report's audit trail
#   body_block         -> fenced block / parameter list / table inside markdown
# ---------------------------------------------------------------------------
REGISTRY = [
    ("A01", "figure_attachment", "Figure 1 — drift time series PNG", "## 4. Results Figures / ### Figure 1",
     "figure", {"line": 82, "index": 0}),
    ("A02", "figure_attachment", "Figure 2 — parameter sweep PNG", "## 4. Results Figures / ### Figure 2",
     "figure", {"line": 86, "index": 1}),
    ("A03", "figure_attachment", "Figure 3 — error distribution PNG", "## 4. Results Figures / ### Figure 3",
     "figure", {"line": 90, "index": 2}),
    ("A04", "source_code_reference", "DEM-LBM ice-floe-drift core module", "## 7. Audit Trail / Files created",
     "file", {"line": 122}),
    ("A05", "source_code_reference", "Test suite for the ice-floe-drift benchmark", "## 7. Audit Trail / Files created",
     "file", {"line": 123}),
    ("A06", "source_code_reference", "Benchmark runner", "## 7. Audit Trail / Files created",
     "file", {"line": 124}),
    ("A07", "document_reference", "Case documentation README", "## 7. Audit Trail / Files created",
     "file", {"line": 125}),
    ("A08", "data_artifact_reference", "Benchmark results JSON", "## 7. Audit Trail / Files created",
     "file", {"line": 126}),
    ("A09", "verification_record", "Test execution log (pytest)", "## 7. Audit Trail / Test execution",
     "block", {"lines": (130, 133)}),
    ("A10", "reproducibility_record", "Reproduction command block", "## 7. Audit Trail / Reproducibility",
     "block", {"lines": (136, 140)}),
    ("A11", "analytical_expression", "Closed-form drift-velocity anchor", "## 1. Case Introduction / Analytical solution",
     "block", {"lines": (13, 16)}),
    ("A12", "parameter_block", "Geometry and fluid parameters", "## 1. Case Introduction / Geometry",
     "block", {"lines": (7, 10)}),
    ("A13", "inline_table", "Baseline case result table", "## 3. Results / Baseline Case",
     "block", {"lines": (37, 40)}),
    ("A14", "inline_table", "9-case parameter sweep table", "## 3. Results / Parameter Sweep",
     "block", {"lines": (44, 54)}),
    ("A15", "inline_table", "Negative control table", "## 3. Results / Negative Control",
     "block", {"lines": (64, 66)}),
    ("A16", "inline_table", "Force balance table", "## 3. Results / Force Balance",
     "block", {"lines": (70, 76)}),
    ("A17", "inline_table", "Error assessment table", "## 6. Error Assessment",
     "block", {"lines": (110, 115)}),
]

FILE_PATH_RE_TMPL = r"`(?P<path>%s)`"


def fetch():
    """GET /tensor/reports/5776 with an env-credential bearer token; pin the bytes."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    tok = login()
    base = __import__("os").environ["TENSOR_API_BASE"].rstrip("/")
    d = _req(base + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    if not isinstance(d, dict) or not isinstance(d.get("markdown"), str):
        raise SystemExit("report %s: no markdown field (keys=%s)" % (REPORT_ID, sorted(d or [])))
    raw = d["markdown"].encode("utf-8")
    (RUNS_DIR / "report_5776.json").write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUNS_DIR / "report_5776.md").write_bytes(raw)
    return d, d["markdown"]


def line_offsets(md: str):
    """[(line_no, start_char, end_char_exclusive_of_newline)] for 1-based lines."""
    out, pos, lines = [], 0, md.split("\n")
    for i, ln in enumerate(lines, start=1):
        out.append((i, pos, pos + len(ln)))
        pos += len(ln) + 1
    return out, lines


def announce(msg):
    print("[build_asset_manifest_5776] " + msg)


# ---------------------------------------------------------------------------
def build():
    meta, md = fetch()
    raw = md.encode("utf-8")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != EXPECTED_HASH:
        raise SystemExit("source_hash mismatch: fetched=%s contract=%s" % (actual, EXPECTED_HASH))
    if len(md) != EXPECTED_CHARS:
        raise SystemExit("char count mismatch: fetched=%d contract=%d" % (len(md), EXPECTED_CHARS))
    offs, lines = line_offsets(md)
    figs = meta.get("figures") or []

    assets = []
    for aid, klass, label, section, kind, spec in REGISTRY:
        if kind == "figure":
            ln = spec["line"]
            start, end = offs[ln - 1][1], offs[ln - 1][2]
            quote = lines[ln - 1]
            idx = spec["index"]
            meta_fig = figs[idx] if 0 <= idx < len(figs) else None
            resolution = "referenced_unresolved"
            check = {"check": "attachment_uri_materialisation", "result": "unresolved"}
            note = ("Markdown image uses an `attachment:%s` URI; the platform reports `figures[%d]` "
                    "with name=%r and caption=%r but exposes no PNG bytes (GET /tensor/reports/%s/artifacts "
                    "and /tensor/artifacts?report_id=%s both return 404), and no such PNG exists in this "
                    "worktree — so the asset is registered by reference only, never assumed.") % (
                meta_fig["name"] if meta_fig else "?", idx,
                meta_fig["name"] if meta_fig else None, meta_fig["caption"] if meta_fig else None,
                REPORT_ID, REPORT_ID)
            platform_meta = {"figures_index": idx,
                             "name": (meta_fig or {}).get("name"),
                             "caption": (meta_fig or {}).get("caption"),
                             "bytes_available": False}
        elif kind == "file":
            ln = spec["line"]
            start, end = offs[ln - 1][1], offs[ln - 1][2]
            quote = lines[ln - 1]
            import re
            m = re.search(r"`([^`]+)`", quote)
            if not m:
                raise SystemExit("A%s: no backticked path on line %d" % (aid, ln))
            path = m.group(1)
            resolution = "referenced_unresolved"
            check = {"check": "path_exists_in_delivery_worktree", "result": "unresolved"}
            note = ("Cited at line %d as `%s`; the path lives in the report's own worktree "
                    "(/root/tp-agent/work/m5068 per the reproducibility block), not in this delivery "
                    "worktree, so its existence/content is NOT validated here." % (ln, path))
            platform_meta = None
        else:
            a, b = spec["lines"]
            start, end = offs[a - 1][1], offs[b - 1][2]
            quote = "\n".join(lines[a - 1:b])
            resolution = "resolved_in_source"
            check = {"check": "char_span_in_source_markdown", "result": "resolved"}
            note = "Body-resident block; span covers source lines %d-%d inclusive." % (a, b)
            platform_meta = None

        if md.count(quote) != 1:
            raise SystemExit("A%s: quote is not a unique substring (count=%d)" % (aid, md.count(quote)))
        if md[start:end] != quote:
            raise SystemExit("A%s: char span does not reproduce the quote" % aid)

        loc = {
            "method": "char_span",
            "start_char": start,
            "end_char": end,
            "start_line": spec.get("line", spec.get("lines", (None, None))[0]),
            "end_line": spec.get("line", spec.get("lines", (None, None))[1]),
            "quote": quote,
            "unique": True,
            "encoding": "utf-8",
        }
        asset = {
            "asset_id": aid,
            "asset_class": klass,
            "label": label,
            "in_report_section": section,
            "locator": loc,
            "resolution": resolution,
            "resolution_check": check,
            "note": note,
        }
        if kind == "file":
            asset["path_reference"] = path
            asset["path_reference_scope"] = "report_worktree_not_delivery_worktree"
        if platform_meta:
            asset["platform_metadata"] = platform_meta
        assets.append(asset)

    ids = [a["asset_id"] for a in assets]
    assert len(ids) == len(set(ids)), "duplicate asset ids"

    by_class, by_resolution = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_resolution[a["resolution"]] = by_resolution.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "source_hash": "sha256:" + actual,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "lane": "C",
            "contract_version": "1.0",
            "retrieved_via": "GET %s/tensor/reports/%s" % (
                __import__("os").environ.get("TENSOR_API_BASE", "").rstrip("/"), REPORT_ID),
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "local_copy": "runs/wp-5776-01/report_5776.md",
            "platform_figures": [
                {"index": i, "name": f.get("name"), "caption": f.get("caption"), "bytes_available": False}
                for i, f in enumerate(figs)
            ],
            "platform_tags": meta.get("tags") or [],
            "platform_status": meta.get("status"),
            "platform_mission_id": meta.get("mission_id"),
            "generator": "scripts/kf/build_asset_manifest_5776.py",
            "verifier": "scripts/kf/build_asset_manifest_5776.py verify",
            "verification_status": "not_verified",
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_resolution,
            "resolved_in_source": sum(1 for a in assets if a["resolution"] == "resolved_in_source"),
            "referenced_unresolved": sum(1 for a in assets if a["resolution"] == "referenced_unresolved"),
            "declared_absent": sum(1 for a in assets if a["resolution"] == "declared_absent"),
        },
        "assets": assets,
        "claims": [],
        "claims_note": (
            "objective.register_assets=true / classify_report_type=false and the package notes allow an "
            "empty claims array: this lane registers assets + locators only. No claim is extracted and no "
            "claim is marked verified; claim extraction belongs to a downstream work package and "
            "verification is computed by the platform gate."
        ),
        "integrity": {
            "quote_uniqueness": "every quote re-sliced from source lines and confirmed md.count(quote)==1, md[start:end]==quote",
            "hash_recomputed_locally": True,
            "hash_matches_contract": actual == EXPECTED_HASH,
            "chars_match_contract": len(md) == EXPECTED_CHARS,
            "duplicate_ids": False,
        },
        "limitations": [
            "Registration only: no text extraction, no claim generation, no verified marks.",
            "Figure assets are referenced, not materialised: the platform exposes figure name/caption but no PNG bytes and no artifact endpoint exists, so A01-A03 stay referenced_unresolved.",
            "A04-A08 are the report's own audit-trail paths; they live in the report's worktree (/root/tp-agent/work/m5068), outside this delivery worktree, so their existence is not validated here.",
            "Report self-reported numbers are registered as text spans, not re-derived here; the purely arithmetic consistency audit of the sweep table against the report's own closed form lives in runs/wp-5776-01/consistency_check.json (scripts/kf/consistency_check_5776.py) and is explicitly NOT a platform verification.",
            "The audit-trail line `- 3 PNG figures (time series, parameter sweep, error distribution)` (line 127) is a collective restatement of A01-A03 and is deliberately not registered as a separate asset.",
            "Schemas: this worktree has no schemas/kf_result.v1.schema.json, so a pinned copy (sha256=170dba8b0b5d54012490aaadc0b68647a9520ecb869e9d03f873afb99b74c076, taken from sibling worktree m15506) sits at docs/kf/wp-5776-01/kf_result.v1.schema.json and docs/kf/wp-5776-01/asset_manifest.v1_5776.schema.json pins the manifest shape; if the platform-side schema differs, the platform gate wins and this artifact must be revised.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    announce("wrote %s (%d assets: %s)" % (MANIFEST.relative_to(REPO), len(assets), by_class))
    return manifest


# ---------------------------------------------------------------------------
def verify():
    """Re-run every acceptance item from scratch (re-fetch the source, re-slice quotes)."""
    import jsonschema

    checks = {}
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "json.loads OK on %s" % MANIFEST.relative_to(REPO)}
    except Exception as e:  # noqa: BLE001
        checks["valid_json"] = {"pass": False, "detail": repr(e)}
        manifest = None

    meta, md = fetch()  # independent re-fetch for the locator/hash checks
    raw = md.encode("utf-8")
    offs, lines = line_offsets(md)

    if manifest is not None:
        errs = []
        try:
            schema = json.loads(SCHEMA_ASSET.read_text(encoding="utf-8"))
            jsonschema.validate(manifest, schema)
        except Exception as e:  # noqa: BLE001
            errs.append("asset_manifest schema: %s" % str(e).split("\n")[0][:300])
        checks["schema_pass"] = {
            "pass": not errs,
            "detail": ("validated against %s (pinned copy of asset_manifest.v1 with package consts for %s) plus "
                       "kf_result.v1 envelope check in 'result'; errors=%s") % (
                SCHEMA_ASSET.relative_to(REPO), PKG, errs),
        }

        bad, checked = [], 0
        for a in manifest["assets"]:
            loc = a["locator"]
            checked += 1
            ok = (
                loc["method"] == "char_span"
                and isinstance(loc["start_char"], int) and isinstance(loc["end_char"], int)
                and 0 <= loc["start_char"] < loc["end_char"] <= len(md)
                and md[loc["start_char"]:loc["end_char"]] == loc["quote"]
                and md.count(loc["quote"]) == 1
                and loc["quote"] in md
                and loc["start_line"] >= 1 and loc["end_line"] >= loc["start_line"]
            )
            # line numbers must agree with the char spans
            if ok:
                s_line = offs[loc["start_line"] - 1][1]
                e_line = offs[loc["end_line"] - 1][2]
                ok = (s_line, e_line) == (loc["start_char"], loc["end_char"])
            if not ok:
                bad.append(a["asset_id"])
        # every fenced/table block that a downstream lane may need must be inside some span? no:
        # only the registered set is asserted here.
        checks["source_locator_resolvable"] = {
            "pass": not bad,
            "detail": "checked %d char_span locators (span==quote, unique, line<->char agreement); failing=%s" % (
                checked, bad),
        }

        actual = hashlib.sha256(raw).hexdigest()
        declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
        checks["source_hash_matches"] = {
            "pass": actual == declared == EXPECTED_HASH,
            "detail": "recomputed=%s declared=%s contract=%s chars=%d/%d" % (
                actual, declared, EXPECTED_HASH, len(md), EXPECTED_CHARS),
        }

        ids = [a["asset_id"] for a in manifest["assets"]]
        checks["no_duplicate_ids"] = {
            "pass": len(ids) == len(set(ids)) and bool(ids) and all(ids),
            "detail": "assets=%d unique=%d first=%s last=%s" % (
                len(ids), len(set(ids)), ids[0] if ids else None, ids[-1] if ids else None),
        }

        claims = manifest.get("claims", [])
        bad_claims = [c for c in claims if not c.get("evidence") and c.get("status") != "unresolved"]
        checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
            "pass": not bad_claims,
            "detail": "claims=%d violating=%d (empty array is legal per contract notes: register_assets only)" % (
                len(claims), len(bad_claims)),
        }

    # envelope check for the kf_result artifact
    result_errs = []
    try:
        res = json.loads(RESULT.read_text(encoding="utf-8"))
        kfs = json.loads(SCHEMA_KF.read_text(encoding="utf-8"))
        jsonschema.validate(res, kfs)
        if res["provenance"]["source_hash"] != "sha256:" + hashlib.sha256(raw).hexdigest():
            result_errs.append("kf_result.provenance.source_hash != recomputed markdown hash")
        if "asset_manifest.json" not in res["outputs"]:
            result_errs.append("outputs missing asset_manifest.json")
    except Exception as e:  # noqa: BLE001
        result_errs.append("kf_result: %s" % str(e).split("\n")[0][:300])
    checks["kf_result_envelope_schema_pass"] = {
        "pass": not result_errs,
        "detail": "validated %s against %s; errors=%s" % (
            RESULT.relative_to(REPO) if RESULT.exists() else RESULT.name,
            SCHEMA_KF.relative_to(REPO), result_errs),
    }

    # the delivery markdown must embed exactly one ```json block equal to the envelope
    embed_errs = []
    try:
        md_report = (REPO / "docs" / "kf" / PKG / ("KF-RESULT-%s.md" % PKG)).read_text(encoding="utf-8")
        # NB: locator quotes legitimately contain fenced blocks (e.g. ```bash), so the fence must be
        # matched with REAL newlines on both sides; naive "```json".split() would cut inside a quote.
        found = re.findall(r"\n```json\n(.*?)\n```\n", md_report, flags=re.S)
        if len(found) != 1:
            embed_errs.append("expected exactly 1 fenced json block, found %d" % len(found))
        elif json.loads(found[0]) != json.loads(RESULT.read_text(encoding="utf-8")):
            embed_errs.append("embedded json differs from %s" % RESULT.name)
    except Exception as e:  # noqa: BLE001
        embed_errs.append("delivery markdown: %s" % str(e).split("\n")[0][:200])
    checks["result_block_embedded_once_in_delivery_markdown"] = {
        "pass": not embed_errs,
        "detail": "KF-RESULT-%s.md carries the kf_result JSON as its single fenced json block; errors=%s" % (PKG, embed_errs),
    }

    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "result": str(RESULT.relative_to(REPO)),
        "source_hash": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=2))
    return 0 if verdict["all_pass"] else 1


# ---------------------------------------------------------------------------
def emit_result():
    """Wrap the manifest in the kf_result.v1 envelope (the only result channel)."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = (RUNS_DIR / "report_5776.md").read_bytes()
    res = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + hashlib.sha256(md).hexdigest(),
            "source_field": SOURCE_FIELD,
            "source_uri": SOURCE_URI,
            "producer": "scripts/kf/build_asset_manifest_5776.py",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "notes": ("asset registration for report %s only: %d assets, claims=[] by contract "
                      "(register_assets only), nothing marked verified; verification is platform-gated."
                      % (REPORT_ID, len(manifest["assets"]))),
        },
        "outputs": {
            "asset_manifest.json": manifest,
        },
        "claims": [],
    }
    RESULT.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    announce("wrote %s" % RESULT.relative_to(REPO))
    return res


if __name__ == "__main__":
    acts = sys.argv[1:] or ["build", "verify", "result"]
    if "build" in acts:
        build()
    if "result" in acts:
        emit_result()
    if "verify" in acts:
        sys.exit(verify())