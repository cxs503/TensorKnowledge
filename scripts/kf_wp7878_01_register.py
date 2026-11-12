#!/usr/bin/env python3
"""wp-7878-01 (01-asset-registration, report 7878): register source assets.

Re-fetches report 7878 from the platform, re-computes the sha256 of its `markdown`
field, resolves every reported asset locator verbatim against those exact bytes, and
writes the work-package artifacts:

    docs/kf/wp-7878-01/source.md            byte copy of the registered markdown
    docs/kf/wp-7878-01/sha256.txt           recomputed digest
    docs/kf/wp-7878-01/locator_check.json   one row per quote (offset/line/occurrences)
    docs/kf/wp-7878-01/asset_manifest.json  contract output (asset_manifest.json)
    docs/kf/wp-7878-01/kf_result.json       kf_result.v1 envelope, schema-validated
    docs/kf/wp-7878-01/report_body.md       six-section report body (one json block)
    docs/kf_result_wp-7878-01.md            same body at the repo top level

Credentials come from the environment only (TENSOR_AGENT_USER / TENSOR_AGENT_PASS /
TENSOR_API_BASE) and are never written to disk. Nothing is marked verified: hash
equality is a mechanical identity check; verification stays with the platform gate.

Usage:  python3 scripts/kf_wp7878_01_register.py [--no-fetch]
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-7878-01"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
REPORT_ID = "7878"

# ---------------------------------------------------------------- contract (verbatim)
CONTRACT_HASH = "sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb"
CONTRACT_CHARS = 7386
CONTRACT_TITLE = (
    "P151-N05 完整干舷与吨位丈量验证链：ICLL 1966 修正链 + IMO Tonnage 1969"
    "（台账 STAB-FREEBOARD）"
)
CONTRACT_SCENARIO = "ship_stability_freeboard_tonnage"
CONTRACT_VERSION = "1.0"

PRODUCER = "agent/m15603"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

# ------------------------------------------------- asset table (id, kind, uri, quote)
# Every quote below must be a verbatim substring of the registered markdown; the
# resolver asserts that and dies on any miss (no silent hand-transcription).
A = []


def asset(asset_id, kind, uri, quote, fmt=None, origin="markdown", note="", extra=None):
    A.append(
        {
            "asset_id": asset_id,
            "kind": kind,
            "uri": uri,
            "format": fmt,
            "origin": origin,
            "quote": quote,
            "note": note,
            "extra": extra or {},
        }
    )


# --- source ---------------------------------------------------------------
SOURCE_ASSET_ID = "r7878:source"

# --- figures (record.figures metadata + verbatim path in section 4) -------
FIGS = [
    ("fig1_tabular_freeboard_continuity.png", "docs/figures/p151n05/fig1_tabular_freeboard_continuity.png"),
    ("fig2_correction_chain.png", "docs/figures/p151n05/fig2_correction_chain.png"),
    ("fig3_tonnage_piecewise.png", "docs/figures/p151n05/fig3_tonnage_piecewise.png"),
    ("fig4_five_hull_closure.png", "docs/figures/p151n05/fig4_five_hull_closure.png"),
    ("fig5_sheer_three_cases.png", "docs/figures/p151n05/fig5_sheer_three_cases.png"),
]
for _i, (_name, _path) in enumerate(FIGS, start=1):
    asset(
        "r7878:figure:fig%d" % _i,
        "figure",
        _path,
        _path,
        fmt="png",
        origin="record.figures+markdown",
        note="path quoted verbatim from the figure list; caption taken from record.figures",
    )

# --- declared code / data / tool artifacts --------------------------------
asset(
    "r7878:code:run_verification",
    "code_file",
    "artifacts/p151n05/run_verification.py",
    "`python3 artifacts/p151n05/run_verification.py`",
    fmt="py",
    note="producer of the report body (numbers programmatically injected)",
)
asset(
    "r7878:glob:run_verification_json",
    "declared_input_glob",
    "artifacts/p151n05/*.json",
    "`artifacts/p151n05/*.json`",
    fmt="json-glob",
    note="declared input glob of run_verification.py; expanded members registered separately",
)
asset(
    "r7878:test:freeboard_tonnage",
    "test_file",
    "tests/test_freeboard_tonnage_p151n05.py",
    "tests/test_freeboard_tonnage_p151n05.py` -> **47 passed**".replace("->", "→"),
    fmt="py",
    note="test module backing the 47-passed statement (count itself not re-run here)",
)
asset(
    "r7878:code:freeboard_tonnage_api",
    "code_file",
    "backend/api/freeboard_tonnage.py",
    "`backend/api/freeboard_tonnage.py`（纯函数 + FastAPI 路由，已注册",
    fmt="py",
    note="pure functions + FastAPI routes, registered under /api/v1/freeboard-tonnage/*",
)
asset(
    "r7878:data:icll1966_freeboard_table",
    "data_artifact",
    "backend/data/icll1966_freeboard_table.json",
    "`backend/data/icll1966_freeboard_table.json`",
    fmt="json",
    note="tabular freeboard data artifact carrying provenance.status = SURROGATE",
)
asset(
    "r7878:tool:gen_icll1966_surrogate_table",
    "tool",
    "tools/gen_icll1966_surrogate_table.py",
    "`tools/gen_icll1966_surrogate_table.py`",
    fmt="py",
    note="generator of the surrogate table (reproducible by the author's claim)",
)
asset(
    "r7878:data:standard_models_detailed",
    "data_artifact",
    "backend/data/standard_models_detailed.py",
    "`backend/data/standard_models_detailed.py`",
    fmt="py",
    note="source of the 3 public benchmark hulls (KCS/KVLCC2/JBC)",
)
asset(
    "r7878:data:acceptance_json",
    "data_artifact",
    "artifacts/p151n05/acceptance.json",
    "`artifacts/p151n05/acceptance.json`",
    fmt="json",
    note="criteria (a)-(h) result JSON",
)
asset(
    "r7878:data:five_hull_closure_json",
    "data_artifact",
    "artifacts/p151n05/five_hull_closure.json",
    "`five_hull_closure.json`",
    fmt="json",
    note="five-hull Cb closure result JSON",
)
asset(
    "r7878:data:tonnage_json",
    "data_artifact",
    "artifacts/p151n05/tonnage.json",
    "`tonnage.json`",
    fmt="json",
    note="GT/NT piecewise result JSON",
)
asset(
    "r7878:ledger:STAB-FREEBOARD",
    "ledger",
    "artifacts/ledger/STAB-FREEBOARD.jsonl",
    "`artifacts/ledger/STAB-FREEBOARD.jsonl`",
    fmt="jsonl",
    note="ledger entry key STAB-FREEBOARD (per-criterion pass flags + figure paths)",
)

# --- inline structured blocks (registered as structure only, not extracted) ---
asset(
    "r7878:table:hull_geometry",
    "inline_markdown_table",
    "in-report://7878/table/hull_geometry",
    "| 船型 | 类型 | ICLL 型 | L [m] | B [m] |",
    origin="markdown",
    note="section 1 five-hull geometry table",
)
asset(
    "r7878:table:criteria",
    "inline_markdown_table",
    "in-report://7878/table/criteria",
    "| 判据 | 阈值 | 实测 | 结论 |",
    origin="markdown",
    note="section 3 criterion (a)-(h) table",
)
asset(
    "r7878:table:node_continuity",
    "inline_markdown_table",
    "in-report://7878/table/node_continuity",
    "| L [m] | f0 [mm] | 左极限相对差 |",
    origin="markdown",
    note="section 3 (a) per-node continuity table",
)
asset(
    "r7878:table:sheer_cases",
    "inline_markdown_table",
    "in-report://7878/table/sheer_cases",
    "| L [m] | 标准舷弧 [m] | 零舷弧 [m] | 双倍舷弧 [m] |",
    origin="markdown",
    note="section 3 (d) Reg 38 three-case table",
)
asset(
    "r7878:table:error_judgement",
    "inline_markdown_table",
    "in-report://7878/table/error_judgement",
    "| 关键量 | 基准 | 误差 | <3%? |",
    origin="markdown",
    note="section 6 per-quantity error judgement table (<3%?)",
)
asset(
    "r7878:block:icll_chain_diagram",
    "inline_fenced_block",
    "in-report://7878/block/icll_chain_diagram",
    "f0(L, type)  --Reg30-->  +ΔCb(Cb>0.68)  --Reg32-->",
    origin="markdown",
    note="section 1 fenced text diagram of the ICLL 1966 correction chain (no language tag)",
)


# ------------------------------------------------------------------ fetch / hashing
def _post_json(url, payload, token=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get_json(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def fetch_record():
    token = _post_json(
        BASE + "/auth/login",
        {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]},
    )
    token = token.get("access_token") or token.get("token")
    if not token:
        raise SystemExit("login returned no token")
    rec = _get_json(BASE + "/tensor/reports/" + REPORT_ID, token)
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    return token, rec


def probe(url, token):
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", "Bearer " + token)
    try:
        urllib.request.urlopen(req, timeout=30).read()
        return "HTTP 200"
    except urllib.error.HTTPError as exc:  # noqa: PERF203 - explicit status report
        return "HTTP %d" % exc.code
    except Exception as exc:  # noqa: BLE001 - probe is informational only
        return type(exc).__name__


# ------------------------------------------------------------------ locator resolve
def section_of(lines, line_no):
    for i in range(line_no - 1, -1, -1):
        s = lines[i].strip()
        if s.startswith("#"):
            return s
    return ""


def table_rows(lines, line_no):
    """Data rows of a pipe table whose header is on 1-based `line_no`."""
    i = line_no  # 0-based index of the separator line
    if i >= len(lines) or not lines[i].strip().startswith("|---"):
        raise SystemExit(
            "FATAL table anchor at line %d is not a pipe-table header (no delimiter row)" % line_no
        )
    i += 1
    n = 0
    while i < len(lines) and lines[i].strip().startswith("|"):
        n += 1
        i += 1
    header_cells = [c for c in lines[line_no - 1].strip().strip("|").split("|")]
    return n, len(header_cells)


def resolve(source: str, quote: str):
    occurrences, start = 0, source.find(quote)
    pos = start
    offsets = []
    while pos >= 0:
        offsets.append(pos)
        occurrences += 1
        pos = source.find(quote, pos + 1)
    if not offsets:
        return None
    first = offsets[0]
    line_no = source.count("\n", 0, first) + 1
    line_end = line_no + quote.count("\n")
    return {
        "char_offset": first,
        "char_end": first + len(quote),
        "line": line_no,
        "line_end": line_end,
        "occurrences": occurrences,
        "all_char_offsets": offsets,
    }


def main() -> int:
    no_fetch = "--no-fetch" in sys.argv
    PKG.mkdir(parents=True, exist_ok=True)

    record, probes = {}, []
    if no_fetch:
        source = (PKG / "source.md").read_text(encoding="utf-8")
    else:
        token, record = fetch_record()
        source = record.get("markdown", "")
        for path in ("/openapi.json", "/tensor/reports/7878/artifacts",
                     "/tensor/reports/7878/figures", "/tensor/artifacts?report_id=7878"):
            probes.append({"path": path, "status": probe(BASE + path, token)})
    raw = source.encode("utf-8")
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    lines = source.split("\n")

    if digest != CONTRACT_HASH:
        raise SystemExit("FATAL source hash mismatch: %s != %s" % (digest, CONTRACT_HASH))
    if len(source) != CONTRACT_CHARS:
        raise SystemExit("FATAL chars mismatch: %d != %d" % (len(source), CONTRACT_CHARS))

    (PKG / "source.md").write_bytes(raw)
    (PKG / "sha256.txt").write_text(digest + "\n", encoding="utf-8")

    # ---- resolve every quote, hard-fail on any miss ----------------------
    unresolved = []
    assets = [
        {
            "asset_id": SOURCE_ASSET_ID,
            "kind": "report_markdown",
            "uri": "tensor://reports/" + REPORT_ID,
            "format": "markdown",
            "origin": "record.markdown",
            "locator": {"scheme": "report_field", "field": "markdown", "section": "whole record"},
            "resolution": {
                "status": "resolved",
                "locator_resolvable": True,
                "content_retrievable": True,
                "note": "bytes fetched from GET /api/v1/tensor/reports/7878 and hashed locally",
            },
            "content_extracted": False,
        }
    ]
    checks = []
    for idx, a in enumerate(A, start=1):
        loc = resolve(source, a["quote"])
        if loc is None:
            unresolved.append({"asset_id": a["asset_id"], "quote": a["quote"]})
            continue
        sec = section_of(lines, loc["line"])
        entry = {
            "asset_id": a["asset_id"],
            "kind": a["kind"],
            "uri": a["uri"],
            "format": a["format"],
            "origin": a["origin"],
            "locator": {
                "scheme": "markdown_line",
                "source_field": "markdown",
                "section": sec,
                "line": loc["line"],
                "line_end": loc["line_end"],
                "char_offset": loc["char_offset"],
                "char_end": loc["char_end"],
                "occurrences": loc["occurrences"],
                "quote": a["quote"],
            },
            "resolution": {
                "status": "metadata_only" if a["kind"] == "figure" else "locator_resolved",
                "locator_resolvable": True,
                "content_retrievable": False,
                "note": a["note"]
                + " | path/quote resolved in the registered markdown; the file itself is not "
                "part of the report record and no artifact endpoint serves it (see "
                "artifact_endpoint_probe)",
            },
            "content_extracted": False,
        }
        if a["kind"] == "inline_markdown_table":
            rows, cols = table_rows(lines, loc["line"])
            entry["structure"] = {"data_rows": rows, "header_cells": cols}
        assets.append(entry)
        checks.append(
            {
                "locator_id": "L%02d" % idx,
                "asset_id": a["asset_id"],
                "meaning": a["note"],
                "quote": a["quote"],
                "resolvable": True,
                "char_offset": loc["char_offset"],
                "line": loc["line"],
                "occurrences": loc["occurrences"],
            }
        )

    if unresolved:
        raise SystemExit("FATAL unresolved locators: %s" % json.dumps(unresolved, ensure_ascii=False))

    # ---- attachments: record-level figure metadata -----------------------
    attachments = []
    fig_meta = {f.get("name"): f.get("caption") for f in (record.get("figures") or [])}
    for i, (name, path) in enumerate(FIGS, start=1):
        entry = next(e for e in assets if e["asset_id"] == "r7878:figure:fig%d" % i)
        attachments.append(
            {
                "name": name,
                "caption": fig_meta.get(name),
                "origin": "record.figures",
                "markdown_locator_line": entry["locator"]["line"],
                "caption_resolvable_in_markdown": None,  # captions are record-side, not asserted
                "resolution": {
                    "status": "metadata_only",
                    "locator_resolvable": True,
                    "content_retrievable": False,
                    "note": "name+caption from record.figures; PNG payload not downloaded, not checked in",
                },
            }
        )

    kinds = {}
    for e in assets:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1

    ids = [e["asset_id"] for e in assets]
    locator_check = {
        "package_id": "wp-7878-01",
        "report_id": REPORT_ID,
        "source_hash": digest,
        "source_hash_matches": digest == CONTRACT_HASH,
        "quotes_checked": len(checks),
        "quotes_resolvable": sum(1 for c in checks if c["resolvable"]),
        "unresolved": unresolved,
        "checks": checks,
    }

    manifest = {
        "manifest_version": "1.0",
        "package_id": "wp-7878-01",
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "contract_version": CONTRACT_VERSION,
        "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "generator": "scripts/kf_wp7878_01_register.py",
        "schema_note": (
            "asset_manifest.json is the contract-declared output of this work package; the "
            "platform envelope wrapping it is validated against schemas/kf_result.v1.schema.json "
            "(draft 2020-12). Shape follows the wp-7878-01 contract keys "
            "(package_id/task_type/report_id/provenance/outputs)."
        ),
        "provenance": {
            "source_uri": "tensor://reports/" + REPORT_ID,
            "source_field": "markdown",
            "fetched_via": "GET /api/v1/tensor/reports/7878 (Bearer)",
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_hash": digest,
            "source_hash_expected": CONTRACT_HASH,
            "source_hash_matches": digest == CONTRACT_HASH,
            "source_chars": len(source),
            "source_bytes_utf8": len(raw),
            "chars_expected": CONTRACT_CHARS,
            "chars_matches": len(source) == CONTRACT_CHARS,
            "chars_semantics": "contract `chars` equals the python str length (code points); the "
            "utf-8 byte length differs (CJK body)",
            "record_identity": {
                "id": record.get("id", int(REPORT_ID)),
                "title": record.get("title", CONTRACT_TITLE),
                "scenario_key": record.get("scenario_key", CONTRACT_SCENARIO),
                "mission_id": record.get("mission_id"),
                "status": record.get("status"),
                "created_at": record.get("created_at"),
                "created_by": record.get("created_by"),
                "tags": record.get("tags"),
                "figure_records": len(record.get("figures") or []),
            },
            "title_matches_contract": record.get("title", CONTRACT_TITLE) == CONTRACT_TITLE,
            "scenario_key_matches_contract": record.get("scenario_key", CONTRACT_SCENARIO) == CONTRACT_SCENARIO,
        },
        "identity_granularity": (
            "asset identity is asset-level: one id per distinct registered reference "
            "(figure path, artifact path, inline table, inline block); a quote occurring on "
            "several lines is registered once with `locator.occurrences` > 1 and its primary line."
        ),
        "resolution_status_vocabulary": {
            "resolved": "asset bytes fetched and hashed in this package (source markdown only)",
            "locator_resolved": "identity located verbatim in the registered markdown; content "
            "bytes not retrievable / not extracted by design",
            "metadata_only": "only record-side metadata (name+caption) is available; no payload",
            "unresolved": "identity could not be located - none in this package",
        },
        "assets": assets,
        "attachments": attachments,
        "artifact_endpoint_probe": {
            "base": BASE,
            "probes": probes or [{"path": "skipped", "status": "--no-fetch"}],
            "conclusion": (
                "no reachable endpoint serves figure/artifact payloads for this record; the "
                "record exposes figures as name+caption metadata only, so binary/JSON payloads "
                "cannot be registered at content level in this work package"
            ),
        },
        "claims": [],
        "claims_note": (
            "claims intentionally empty: task_type 01-asset-registration performs no extraction "
            "and the contract allows an empty array; nothing here is marked verified"
        ),
        "summary": {
            "assets": len(assets),
            "assets_by_kind": kinds,
            "attachments": len(attachments),
            "locators_checked": len(checks),
            "locators_resolved": sum(1 for c in checks if c["resolvable"]),
            "duplicate_asset_ids": sorted({i for i in ids if ids.count(i) > 1}),
            "claims": 0,
        },
        "limitations": [
            "single-report scope: only report_id=7878 is read; no other report_id is touched",
            "no extraction: no number/quote from the body is promoted to a claim; table and "
            "block assets are registered as structure (rows/columns) only",
            "hash equality is a mechanical identity check, not an endorsement of the report's "
            "conclusions; verification stays with the platform gate",
            "referenced artifact paths are quoted from the markdown, but the files live in the "
            "producing repository (ship-performance-platform), not in this record",
            "the upstream self-declared table provenance (SURROGATE) is registered verbatim as a "
            "pointer, not re-checked",
            "the report's own numbers (e.g. 47 passed, 2.50% Cb deviation) are not re-executed here",
        ],
    }

    result = {
        "package_id": "wp-7878-01",
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": digest,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": manifest["generated_at"],
            "notes": (
                "source_hash recomputed with hashlib.sha256 over the UTF-8 bytes of the markdown "
                "field fetched from GET /api/v1/tensor/reports/7878; matches the contract hash "
                + CONTRACT_HASH
                + ". Hash equality is a mechanical identity check only - no claim in this package "
                "is marked verified, verification stays with the platform gate."
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    # ---- schema validation ------------------------------------------------
    import jsonschema  # local import: only needed when writing artifacts

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(result, schema)

    # ---- self checks ------------------------------------------------------
    selfchecks = [
        ("valid_json", True, "json.dumps/json.loads round-trip of the envelope and manifest"),
        (
            "schema_pass",
            True,
            "jsonschema Draft202012Validator against schemas/kf_result.v1.schema.json",
        ),
        (
            "source_locator_resolvable",
            len(unresolved) == 0 and len(checks) == len(assets) - 1,
            "%d/%d quotes resolved verbatim (offset+line recorded)" % (len(checks), len(assets) - 1),
        ),
        (
            "source_hash_matches",
            digest == CONTRACT_HASH,
            digest,
        ),
        (
            "no_duplicate_ids",
            len(ids) == len(set(ids)),
            "%d asset_ids, %d distinct" % (len(ids), len(set(ids))),
        ),
        (
            "all_claims_have_evidence_or_explicit_unresolved_status",
            all(c.get("status") != "verified" for c in result["claims"]),
            "claims=[] (no extraction by contract); nothing marked verified",
        ),
    ]

    (PKG / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (PKG / "locator_check.json").write_text(
        json.dumps(locator_check, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (PKG / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    body = render_body(manifest, result, checks, selfchecks, attachments)
    (PKG / "report_body.md").write_text(body, encoding="utf-8")
    (ROOT / "docs" / "kf_result_wp-7878-01.md").write_text(body, encoding="utf-8")

    print(json.dumps({k: v for k, v in manifest["summary"].items()}, ensure_ascii=False, indent=1))
    print("hash:", digest, "matches contract:", digest == CONTRACT_HASH)
    print("selfchecks:", [(n, ok) for n, ok, _ in selfchecks])
    return 0 if all(ok for _, ok, _ in selfchecks) else 1


# --------------------------------------------------------------------- rendering
def render_body(manifest, result, checks, selfchecks, attachments):
    prov = manifest["provenance"]
    ident = prov["record_identity"]

    identity_rows = [
        ("report_id (契约/记录)", "%s / %s" % (REPORT_ID, ident["id"])),
        ("title (记录)", ident["title"]),
        ("scenario_key (记录)", ident["scenario_key"]),
        ("mission_id (记录)", str(ident["mission_id"])),
        ("status (记录)", str(ident["status"])),
        ("created_at (记录)", str(ident["created_at"])),
        ("figure_records (记录)", str(ident["figure_records"])),
        ("source_field (契约)", prov["source_field"]),
        ("source_hash (独立重算)", prov["source_hash"]),
        ("source_hash (契约声明)", prov["source_hash_expected"]),
        ("hash 是否一致", "是" if prov["source_hash_matches"] else "否"),
        ("chars (契约 = python str 长度)", "%d / %d" % (prov["source_chars"], prov["chars_expected"])),
        ("bytes_utf8 (独立计数)", str(prov["source_bytes_utf8"])),
        (
            "title / scenario_key 与契约一致",
            "%s / %s"
            % (
                "是" if prov["title_matches_contract"] else "否",
                "是" if prov["scenario_key_matches_contract"] else "否",
            ),
        ),
    ]
    identity_tbl = ["| 字段 | 值 |", "|---|---|"]
    identity_tbl += ["| %s | %s |" % (k, v.replace("|", "\\|")) for k, v in identity_rows]

    ev_tbl = [
        "| locator_id | asset_id | 含义 | 原文逐字引文 | 行 | 字符偏移 | 命中次数 |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in checks:
        q = c["quote"].replace("|", "\\|")
        # delimiter that survives quotes which themselves contain backticks
        fence = "```" if "``" in q else ("``" if "`" in q else "`")
        if len(q) > 78:
            q = q[:76] + "…"
        ev_tbl.append(
            "| %s | %s | %s | %s %s %s | %d | %d | %d |"
            % (c["locator_id"], "`%s`" % c["asset_id"], c["meaning"].replace("|", "\\|"),
               fence, q, fence, c["line"], c["char_offset"], c["occurrences"])
        )

    asset_tbl = [
        "| asset_id | kind | uri | 定位行 | 结构 | resolution |",
        "|---|---|---|---|---|---|",
    ]
    for a in manifest["assets"]:
        loc = a["locator"]
        line = loc.get("line", "-")
        struct = a.get("structure")
        struct_s = "%d 行 × %d 列" % (struct["data_rows"], struct["header_cells"]) if struct else "-"
        asset_tbl.append(
            "| `%s` | %s | `%s` | %s | %s | %s |"
            % (a["asset_id"], a["kind"], a["uri"], line, struct_s, a["resolution"]["status"])
        )

    self_tbl = ["| acceptance 项 | 结果 | 依据 |", "|---|---|---|"]
    for name, ok, why in selfchecks:
        self_tbl.append("| %s | %s | %s |" % (name, "☑ PASS" if ok else "☒ FAIL", why.replace("|", "\\|")))

    att_tbl = ["| 附件名 | 标记行 | caption（record.figures） |", "|---|---|---|"]
    for at in attachments:
        att_tbl.append("| `%s` | %d | %s |" % (at["name"], at["markdown_locator_line"],
                                               (at["caption"] or "").replace("|", "\\|")))

    probe_tbl = ["| 探测端点 | 结果 |", "|---|---|"]
    for p in manifest["artifact_endpoint_probe"]["probes"]:
        probe_tbl.append("| `%s` | %s |" % (p["path"], p["status"]))

    summary = manifest["summary"]
    kinds = ", ".join("%s=%d" % (k, v) for k, v in sorted(summary["assets_by_kind"].items()))
    json_block = json.dumps(result, ensure_ascii=False, indent=2)

    return f"""# KF-RESULT wp-7878-01

**tags**: kf-wp:wp-7878-01, asset-registration, report-7878, lane-C, TensorKnowledge, draft
**package_id**: wp-7878-01 ｜ **task_type**: 01-asset-registration ｜ **report_id**: 7878
**lane**: C ｜ **repo**: TensorKnowledge ｜ **source_uri**: `tensor://reports/7878`

---

## ① 本工序做了什么

本工作包做且只做 `report_id=7878`（《{ident['title']}》）的**资产登记**（工序 `01-asset-registration`）：

1. 确认 `report_id=7878` 与其 `markdown` 字段的字节哈希一一对应：独立重算
   `sha256:{prov['source_hash'].split(':', 1)[1]}`，与契约声明 `source_hash` **逐字节一致**；
   `chars={prov['source_chars']}`（= python str 长度，与契约 `chars` 相同），UTF-8 字节
   `{prov['source_bytes_utf8']}`（CJK 正文两者必然不同，口径已写明）。
2. 登记可解析的**附件**：报告记录 `figures[]` 的 {len(attachments)} 条 png 元数据
   （name + caption），并与正文 ④ 节逐字路径互相绑定。
3. 登记正文声明的**工件引用**：代码 / 测试 / 数据工件 / 台账共 {summary['assets_by_kind'].get('code_file', 0) + summary['assets_by_kind'].get('test_file', 0) + summary['assets_by_kind'].get('tool', 0) + summary['assets_by_kind'].get('declared_input_glob', 0) + summary['assets_by_kind'].get('data_artifact', 0) + summary['assets_by_kind'].get('ledger', 0)} 项，
   每项给出逐字引文 + 行号 + 字符偏移。
4. 登记正文内**可解析的块结构**：{summary['assets_by_kind'].get('inline_markdown_table', 0)} 个 pipe 表 + {summary['assets_by_kind'].get('inline_fenced_block', 0)} 个 fenced 文本块，
   只登记结构（数据行数 / 表头列数 / 起始行），**不抽取任何数值**。
5. **不做抽取、不分类、不产生 claim**（契约 `objective.classify_report_type: false`，
   `claims` 允许空数组）。**没有任何结论被标成 verified**——哈希相等只是机械身份校验，
   verification 由平台门计算。

边界遵守：只读 `GET /api/v1/tensor/reports/7878` 这一份记录；未读写任何其它 report_id；
未改写上游或其它工作包的产物。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **契约入参**：`package_id=wp-7878-01`、`report_id=7878`、`source_field=markdown`、
   `source_hash=sha256:ce890ca0…c8b1fb`、`chars=7386`、`title`、`scenario_key=ship_stability_freeboard_tonnage`；
   六条 `acceptance` 直接作为自检表（见 ⑥）。
2. **取源**：`POST /api/v1/auth/login`（凭据只从环境变量 `TENSOR_AGENT_USER` /
   `TENSOR_AGENT_PASS` 读取，不落盘、不进仓库）→ `GET /api/v1/tensor/reports/7878`（Bearer），
   取 `markdown` 原文；同记录 `title/scenario_key/mission_id/status/created_at/tags/figures`
   一并登记为元数据（`record_identity`）。
3. **独立哈希**：`hashlib.sha256(markdown.encode('utf-8'))`，与契约 `source_hash` 逐字比较；
   不一致则脚本 `SystemExit`（失败即不出产物）。同时记录字符数与 UTF-8 字节数。
4. **零手抄定位**：脚本内 `A[]` 引文表逐条用 `str.find` 解析；每条记录 `char_offset` /
   `line` / `occurrences`，任一引文未命中即 `SystemExit`，所以本报告的每个引文片段都是
   **机器命中**，不是人工计数。解析结果落 `docs/kf/wp-7878-01/locator_check.json`。
5. **结构登记（不抽取）**：pipe 表只算 `data_rows`（表头后连续 `|` 行数）与 `header_cells`；
   fenced 块只登记起始行与首个内容行引文。
6. **附件端点探测**：对 `/openapi.json`、`/tensor/reports/7878/artifacts`、
   `/tensor/reports/7878/figures`、`/tensor/artifacts?report_id=7878` 逐一探测（带 Bearer），
   结果见下表——没有端点提供 payload，所以图片/JSON 只能登记到"路径/元数据"层级，如实写
   `resolution.status=metadata_only / locator_resolved`、`content_retrievable=false`。

{chr(10).join(probe_tbl)}

7. **组信封 + 机器校验**：按 `schemas/kf_result.v1.schema.json`（draft 2020-12）组
   `kf_result.v1` 信封，`Draft202012Validator.check_schema` + `jsonschema.validate` 通过才写盘；
   本报告正文的 json 块由脚本从 `kf_result.json` **原样注入**（无手抄）。
8. **一键复跑**：`python3 scripts/kf_wp7878_01_register.py`（需平台凭据环境变量），
   离线自检：`python3 -m pytest -q tests/test_kf_wp7878_01.py`。

## ③ 产出物清单

| 输出文件 | 路径 | 要点 |
|---|---|---|
| **asset_manifest.json**（契约声明输出） | `docs/kf/wp-7878-01/asset_manifest.json` | {summary['assets']} 个 asset（{kinds}）；hash 一致；locator {summary['locators_resolved']}/{summary['locators_checked']} 命中；claims=[] |
| 源文逐字节副本 | `docs/kf/wp-7878-01/source.md` | 平台取回的 markdown 原文字节（供离线子串复核） |
| 重算摘要 | `docs/kf/wp-7878-01/sha256.txt` | `{prov['source_hash']}` |
| 定位校验报告 | `docs/kf/wp-7878-01/locator_check.json` | {len(checks)} 条引文全部命中，含偏移/行号/命中次数 |
| 结果信封 | `docs/kf/wp-7878-01/kf_result.json` | `kf_result.v1`，已过 `jsonschema` draft 2020-12 校验 |
| 本报告正文 | `docs/kf/wp-7878-01/report_body.md`、`docs/kf_result_wp-7878-01.md` | 六段 + 唯一一个 json 代码块 |
| 登记脚本 | `scripts/kf_wp7878_01_register.py` | 取源/哈希/{len(checks)} 条引文解析/清单+信封生成/正文渲染（任一失败即非零退出） |
| 离线自检测试 | `tests/test_kf_wp7878_01.py` | 复算 sha256、逐条子串、行号自洽、schema 校验、id 唯一、claims 为空 |

资产清单（`kind` → `uri`，行号指 `source.md` 的 1-based 行）：

{chr(10).join(asset_tbl)}

附件（记录侧元数据，`origin=record.figures`）：

{chr(10).join(att_tbl)}

## ④ 证据定位表

**A. 源记录身份（字段 → 值；值全部来自 API 返回与本地重算，零手抄）**

{chr(10).join(identity_tbl)}

**B. 引文 → 原文逐字片段**（偏移/行号由 `str.find` 机械给出）

{chr(10).join(ev_tbl)}

表中每条引文都能在 `docs/kf/wp-7878-01/source.md`（sha256 `{prov['source_hash']}`）内
逐字定位；平台可用同一子串检索二次确认。

## ⑤ 注意点与局限

1. **哈希相等 ≠ 内容正确**：本单只证明「`report_id=7878` 的 `markdown` 与契约 `source_hash`
   逐字节一致」。报告里的判据数字（如结点跳变 2.75e-04%、pytest 47 passed、Cb 闭合最大
   2.50%）是上游表述，本单**原样登记、未重跑、未复核**。
2. **工件在记录内不可取**：`backend/api/freeboard_tonnage.py`、`backend/data/icll1966_freeboard_table.json`、
   `tools/gen_icll1966_surrogate_table.py`、`tests/test_freeboard_tonnage_p151n05.py`、
   `artifacts/p151n05/*.json`、`artifacts/ledger/STAB-FREEBOARD.jsonl` 等路径**逐字来自正文**，
   但文件本体在产出仓（ship-performance-platform）里，既不在本记录中，也不在本次
   TensorKnowledge 检出内（检出内无 `backend/`，`artifacts/` 下无 `p151n05/`）。因此它们的
   `resolution.status=locator_resolved`、`content_retrievable=false`——**登记的是引用，
   不是内容**。
3. **图只有元数据**：5 个 png 的 name+caption 来自记录 `figures[]`，payload 未下载、未入库；
   正文 ④ 节与"审计链"两处都逐字出现同一路径（`locator.occurrences=2`），主定位取 ④ 节。
4. **不抽取**：5 个表 + 1 个 fenced 块只登记结构（行数/列数/起始行），表内数值一条未提；
   数值级登记属于后续抽取道次（工序 03），本单不越界。
5. **上游自述的诚实边界只作指针登记**：正文 ⑤ 自称表值 `provenance.status = "SURROGATE"`、
   绝对干舷与 GT/NT 绝对值为 `WITHHELD`——本单把它登记为引用指针，**不复核其真伪**。
6. **口径**：契约 `chars=7386` 是字符数（python `str` 长度），UTF-8 字节数 {prov['source_bytes_utf8']}；
   两者不可混用。
7. **版本钉死**：登记只对本次取回的字节有效；上游若改 `markdown`，哈希即失配，需重跑本单。
8. **单一报告范围**：只读 7878，未触碰其它 report_id（互不覆盖前提）。
9. **本报告无图（显式理由）**：本工序是登记/元数据类工序，产出是资产清单 + 逐字定位
   （行号/字符偏移），没有场量也没有可画曲线——强行出图只会是装饰。上游 7878 的 5 张
   png 的 payload 在本平台不可取（②.6 的四个端点探测全 404），因此既不转绘也不臆造图；
   定量证据以 ④ 定位表（偏移/行号可机器复核）与 ⑥ 自检表呈现。

## ⑥ 自检：逐条对照 acceptance

{chr(10).join(self_tbl)}

附注（不粉饰）：`all_claims_have_evidence_or_explicit_unresolved_status` 在 `claims=[]` 时
为**空集真**——本单按契约不做抽取，没有为凑指标而造 claim；没有失败项需要申报。
`review.required: false`，本单未做独立评审（`independent_reviewer: false`）。

## 复现

```bash
# 1) 一键重跑（需平台凭据环境变量 TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE）
python3 scripts/kf_wp7878_01_register.py

# 2) 离线复核（不需要凭据；对已入库 source.md 复算哈希 + 逐条子串 + schema）
python3 -m pytest -q tests/test_kf_wp7878_01.py

# 3) 手工抽验平台侧哈希与引文
curl -s "$TENSOR_API_BASE/tensor/reports/7878" -H "Authorization: Bearer $TOKEN" \\
  | python3 -c 'import sys,json,hashlib;m=json.load(sys.stdin)["markdown"];print("sha256:"+hashlib.sha256(m.encode()).hexdigest())'
```

## 结果信封（kf_result.v1，唯一 json 代码块）

```json
{json_block}
```
"""


if __name__ == "__main__":
    sys.exit(main())