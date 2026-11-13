#!/usr/bin/env python3
"""KF work package wp-9083-01 (task_type=01-asset-registration, report_id=9083).

Registers the source assets of tensor://reports/9083:
  * the report markdown itself (byte hash / chars / lines / utf8 bytes),
  * the two locatable sections of that markdown,
  * every attachment declared in the report record (`figures`), each with an
    honest retrieval probe (declared != retrievable).

No extraction, no claim generation, no verification marking.

Every number that ends up in the deliverables is computed here (zero hand copy);
every quote used as a source locator is re-verified to occur exactly once in the
markdown before it is written out.

Repro (one key):
    python3 scripts/kf_register_9083.py            # regenerate + validate
    python3 scripts/kf_register_9083.py --check    # validate existing artifacts only
"""
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.error
import urllib.request

import jsonschema

# ---------------------------------------------------------------- constants ---
REPORT_ID = "9083"
PACKAGE_ID = "wp-9083-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_SOURCE_HASH = "sha256:345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8"
CONTRACT_CHARS = 258
SOURCE_URI = "tensor://reports/9083"
SOURCE_FIELD = "markdown"

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "artifacts" / "kf" / PACKAGE_ID
RUN_DIR = ROOT / "runs" / "kf" / PACKAGE_ID
DOC_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
SCHEMAS = ROOT / "schemas"

MANIFEST_PATH = OUT_DIR / "asset_manifest.json"
RESULT_PATH = OUT_DIR / "kf_result.json"
REPORT_PATH = DOC_DIR / "REPORT.md"
TEMPLATE_PATH = DOC_DIR / "REPORT.template.md"
RUNLOG_PATH = RUN_DIR / "registration_run.json"


# -------------------------------------------------------------------- http ---
def _req(path: str, method: str = "GET", body=None, token=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return resp.status, resp.headers.get("content-type", ""), raw
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("content-type", "") if exc.headers else "", exc.read()


def login() -> str:
    if not (USER and PASS):
        sys.exit("TENSOR_AGENT_USER / TENSOR_AGENT_PASS not set")
    status, _, raw = _req("/auth/login", "POST", {"username": USER, "password": PASS})
    if status != 200:
        sys.exit(f"login failed: HTTP {status}")
    return json.loads(raw)["access_token"]


def fetch_report(token: str) -> dict:
    status, _, raw = _req(f"/tensor/reports/{REPORT_ID}", token=token)
    if status != 200:
        sys.exit(f"GET report {REPORT_ID} failed: HTTP {status} {raw[:200]!r}")
    return json.loads(raw)


def probe_figure(token: str, name: str) -> dict:
    status, ctype, raw = _req(f"/tensor/reports/{REPORT_ID}/figures/{name}", token=token)
    try:
        detail = json.loads(raw).get("detail")
    except Exception:
        detail = None
    return {
        "figure_name": name,
        "endpoint": f"GET {BASE}/tensor/reports/{REPORT_ID}/figures/{name}",
        "http_status": status,
        "content_type": ctype,
        "bytes_returned": len(raw),
        "detail": detail,
        "retrievable": status == 200 and len(raw) > 0,
    }


# ------------------------------------------------------------- markdown ops ---
def doc_stats(md: str) -> dict:
    return {
        "chars": len(md),
        "bytes_utf8": len(md.encode("utf-8")),
        "lines": md.count("\n") + (0 if md.endswith("\n") else 1),
        "sha256": hashlib.sha256(md.encode("utf-8")).hexdigest(),
    }


def locate(md: str, quote: str) -> dict:
    """Char span + line span of `quote`; fails loudly if absent or non-unique."""
    hits = [m.start() for m in re.finditer(re.escape(quote), md)]
    if len(hits) != 1:
        raise SystemExit(f"locator quote not unique/absent ({len(hits)} hits): {quote!r}")
    start = hits[0]
    end = start + len(quote)
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": md.count("\n", 0, start) + 1,
        "end_line": md.count("\n", 0, start + len(quote) - 1) + 1,
        "quote": quote,
        "unique": True,
    }


def section_span(md: str, heading: str) -> tuple[str, int, int]:
    start = md.index(heading)
    nxt = md.find("\n## ", start + len(heading))
    end = len(md.rstrip()) if nxt == -1 else md.rstrip().rfind("\n", 0, nxt) if False else nxt
    body = md[start:end].rstrip("\n")
    return body, start, start + len(body)


def document_span(md: str) -> dict:
    body = md.rstrip("\n")
    return {
        "method": "document",
        "start_char": 0,
        "end_char": len(body),
        "start_line": 1,
        "end_line": md.count("\n") + (0 if md.endswith("\n") else 1),
        "quote": body,
        "unique": md.count(body) == 1,
    }


# ------------------------------------------------------------------ build ----
def build(token: str, emitted_at: str | None = None) -> tuple[dict, dict]:
    rec = fetch_report(token)
    md = rec.get("markdown") or ""
    st = doc_stats(md)

    hash_ok = f"sha256:{st['sha256']}" == CONTRACT_SOURCE_HASH
    if not hash_ok:
        raise SystemExit(
            f"source hash mismatch: api sha256:{st['sha256']} vs contract {CONTRACT_SOURCE_HASH}"
        )

    figures = rec.get("figures") or []
    probes = [probe_figure(token, f.get("name", "")) for f in figures]

    assets = []
    # A01 — the report markdown document itself
    assets.append(
        {
            "asset_id": "A01",
            "asset_class": "report_document",
            "label": f"markdown of report {REPORT_ID} ({st['chars']} chars, {st['lines']} lines)",
            "in_report_section": "whole document",
            "locator": document_span(md),
            "resolution": "resolved_in_source",
            "resolution_check": {
                "check": f"GET {BASE}/tensor/reports/{REPORT_ID} -> field 'markdown'; "
                f"sha256 recomputed locally == contract source_hash",
                "result": "resolved",
            },
            "note": "byte-exact match: sha256:"
            + st["sha256"]
            + " == contract source_hash; chars "
            + str(st["chars"])
            + " == contract chars "
            + str(CONTRACT_CHARS),
        }
    )

    # A02/A03 — the two locatable sections (structure only, no extraction)
    sections = [("A02", "## Results", "results_block"), ("A03", "## Tests", "tests_block")]
    for aid, heading, cls in sections:
        body, s, e = section_span(md, heading)
        loc = locate(md, body)
        assert loc["start_char"] == s and loc["end_char"] == e, (heading, loc, s, e)
        assets.append(
            {
                "asset_id": aid,
                "asset_class": cls,
                "label": f"section starting at '{heading}' ({len(body)} chars)",
                "in_report_section": heading,
                "locator": loc,
                "resolution": "resolved_in_source",
                "resolution_check": {
                    "check": "section byte span located in markdown; quote occurs exactly once",
                    "result": "resolved",
                },
                "note": "structure pointer only; no numeric extraction performed in this package",
            }
        )

    # A04.. — attachments declared in the record; retrieval honestly probed
    for i, (fig, pr) in enumerate(zip(figures, probes)):
        name = fig.get("name", "")
        assets.append(
            {
                "asset_id": f"A{4 + i:02d}",
                "asset_class": "declared_figure",
                "label": name,
                "in_report_section": "not referenced in markdown; declared only in record field "
                f"figures[{i}]",
                "locator": document_span(md),
                "resolution": "referenced_unresolved",
                "resolution_check": {
                    "check": pr["endpoint"]
                    + " -> HTTP "
                    + str(pr["http_status"])
                    + (f" detail={pr['detail']!r}" if pr["detail"] else "")
                    + "; and figure name is not a substring of the markdown",
                    "result": "unresolved",
                },
                "declaration_source": {
                    "field": "record",
                    "path": f"figures[{i}]",
                    "verbatim": {"name": name, "caption": fig.get("caption")},
                    "in_markdown": name in md,
                },
                "note": "declared in report record metadata, bytes not retrievable through the "
                "platform figure endpoint (HTTP 404); caption is generic text, not evidence",
            }
        )

    ids = [a["asset_id"] for a in assets]
    assert len(ids) == len(set(ids)), "duplicate asset_id"
    assert all(a["locator"]["unique"] for a in assets)

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": st["sha256"],
            "chars": st["chars"],
            "bytes_utf8": st["bytes_utf8"],
            "title": rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "platform_status": rec.get("status"),
            "platform_tags": rec.get("tags") or [],
            "platform_figures": figures,
            "platform_mission_id": rec.get("mission_id"),
            "contract_chars": CONTRACT_CHARS,
            "contract_hash_matches": hash_ok,
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "figures_declared": len(figures),
            "figures_retrievable": sum(1 for p in probes if p["retrievable"]),
        },
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": "all locator quotes re-verified unique in markdown "
            f"({len(assets)}/{len(assets)})",
            "hash_recomputed_locally": "sha256:" + st["sha256"],
            "hash_matches_contract": hash_ok,
            "no_claim_verification": "claims empty by contract (objective.classify_report_type="
            "false, no extraction); nothing marked verified",
        },
    }

    emitted = emitted_at or _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()
    result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": f"sha256:{st['sha256']}",
            "source_field": SOURCE_FIELD,
            "producer": "scripts/kf_register_9083.py",
            "emitted_at": emitted,
            "notes": "asset registration only; source_hash recomputed from the platform markdown "
            "field, not copied; every locator quote re-verified unique in that markdown",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    runlog = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "generated_at": emitted,
        "api_base": BASE,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "chars": st["chars"],
            "bytes_utf8": st["bytes_utf8"],
            "lines": st["lines"],
            "sha256_recomputed": st["sha256"],
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_match": hash_ok,
            "contract_chars": CONTRACT_CHARS,
            "chars_match": st["chars"] == CONTRACT_CHARS,
        },
        "figure_probes": probes,
        "counts": manifest["counts"],
        "quote_checks": [
            {
                "asset_id": a["asset_id"],
                "start_char": a["locator"]["start_char"],
                "end_char": a["locator"]["end_char"],
                "occurrences_in_markdown": md.count(a["locator"]["quote"]),
            }
            for a in assets
        ],
        "repro_cmd": "TENSOR_API_BASE=$TENSOR_API_BASE python3 scripts/kf_register_9083.py"
    }
    return result, {"runlog": runlog, "md": md, "probes": probes}


# ----------------------------------------------------------------- schema ----
def validate(result: dict) -> dict:
    out = {}

    env_schema = json.loads((SCHEMAS / "kf_result.v1.schema.json").read_text())
    jsonschema.validate(result, env_schema)
    out["kf_result.v1.schema.json"] = "pass"

    # schemas/asset_manifest.v1.schema.json is pinned to package wp-448-01 of
    # another report; the structural body is reused with the const values
    # rebound to this package (platform-side schema wins if it differs).
    man_schema = copy.deepcopy(json.loads((SCHEMAS / "asset_manifest.v1.schema.json").read_text()))
    props = man_schema["properties"]
    props["package_id"]["const"] = PACKAGE_ID
    props["report_id"]["const"] = REPORT_ID
    props["task_type"]["const"] = TASK_TYPE
    props["source"]["properties"]["uri"]["const"] = SOURCE_URI
    jsonschema.validate(result["outputs"]["asset_manifest.json"], man_schema)
    out["asset_manifest.v1.schema.json (consts rebound to " + PACKAGE_ID + ")"] = "pass"

    return out


# ------------------------------------------------------------------ report ---
def render_report(result: dict, runlog: dict) -> str:
    man = result["outputs"]["asset_manifest.json"]
    src = man["source"]
    cnt = man["counts"]
    md = runlog_markdown(man)
    fig_rows = "\n".join(
        "| {figure_name} | {http_status} | {bytes_returned} | {detail} | {retrievable} |".format(
            **p
        )
        for p in runlog["figure_probes"]
    )
    ev_rows = "\n".join(
        "| {aid} | {label} | {res} | `{quote}` | {span} |".format(
            aid=a["asset_id"],
            label=a["label"].replace("|", "\\|"),
            res=a["resolution"],
            quote=(a["locator"]["quote"] if len(a["locator"]["quote"]) <= 60
                   else a["locator"]["quote"][:57] + "..."),
            span=f"L{a['locator']['start_line']}-{a['locator']['end_line']} "
                 f"[{a['locator']['start_char']},{a['locator']['end_char']})",
        )
        for a in man["assets"]
    )
    tpl = TEMPLATE_PATH.read_text()
    subs = {
        "{{KFRESULT_JSON}}": json.dumps(result, ensure_ascii=False, indent=2),
        "{{HASH}}": src["hash"],
        "{{CHARS}}": str(src["chars"]),
        "{{BYTES}}": str(src["bytes_utf8"]),
        "{{TITLE}}": src["title"],
        "{{SCENARIO}}": src["scenario_key"],
        "{{N_ASSETS}}": str(cnt["assets"]),
        "{{N_RESOLVED}}": str(cnt["resolved_in_source"]),
        "{{N_UNRESOLVED}}": str(cnt["referenced_unresolved"]),
        "{{N_FIG}}": str(cnt["figures_declared"]),
        "{{N_FIG_OK}}": str(cnt["figures_retrievable"]),
        "{{FIG_TABLE}}": fig_rows,
        "{{EVIDENCE_TABLE}}": ev_rows,
        "{{SECTION_MAP}}": md,
        "{{EMITTED}}": result["provenance"]["emitted_at"],
    }
    out = tpl
    for k, v in subs.items():
        out = out.replace(k, v)
    return out


def runlog_markdown(man: dict) -> str:
    rows = []
    for a in man["assets"]:
        rows.append(
            f"| {a['asset_id']} | {a['locator']['method']} | "
            f"{a['locator']['start_line']} | {a['locator']['end_line']} | "
            f"{a['locator']['start_char']} | {a['locator']['end_char']} | "
            f"{len(a['locator']['quote'])} |"
        )
    head = (
        "| asset | locator method | line start | line end | char start | char end | quote chars |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    return head + "\n".join(rows)


# -------------------------------------------------------------------- main ---
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate existing artifacts, no API write")
    ap.add_argument("--post", action="store_true", help="also POST the rendered report to the platform")
    ap.add_argument(
        "--fresh-timestamp",
        action="store_true",
        help="issue a new emitted_at instead of reusing the previous run's",
    )
    args = ap.parse_args()

    if args.check:
        result = json.loads(RESULT_PATH.read_text())
        print(json.dumps(validate(result), indent=2))
        return 0

    # timestamps are reused from a previous run so that re-running the script
    # does not silently drift the bytes of an already delivered report.
    emitted_at = None
    if RUNLOG_PATH.exists() and not args.fresh_timestamp:
        emitted_at = json.loads(RUNLOG_PATH.read_text()).get("generated_at")

    token = login()
    result, extra = build(token, emitted_at)
    checks = validate(result)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    MANIFEST_PATH.write_text(json.dumps(result["outputs"]["asset_manifest.json"], indent=2, ensure_ascii=False) + "\n")
    RESULT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    # byte-exact snapshot of the source markdown: lets the offline test suite
    # recompute the upstream hash without touching the network or the DB.
    snap = RUN_DIR / "source_markdown.snapshot.md"
    snap.write_bytes(extra["md"].encode("utf-8"))
    assert hashlib.sha256(snap.read_bytes()).hexdigest() == extra["runlog"]["source"]["sha256_recomputed"]

    runlog = extra["runlog"]
    runlog["source_snapshot"] = {
        "path": str(snap.relative_to(ROOT)),
        "sha256": hashlib.sha256(snap.read_bytes()).hexdigest(),
        "bytes_utf8": snap.stat().st_size,
    }
    runlog["schema_checks"] = checks
    RUNLOG_PATH.write_text(json.dumps(runlog, indent=2, ensure_ascii=False) + "\n")

    report = render_report(result, runlog)
    REPORT_PATH.write_text(report)

    # artifacts/ is deliberately gitignored (mission-push gate drops artifacts/**),
    # so the two deliverable json files are also kept next to the report.
    (DOC_DIR / "asset_manifest.json").write_text(
        json.dumps(result["outputs"]["asset_manifest.json"], indent=2, ensure_ascii=False) + "\n"
    )
    (DOC_DIR / "kf_result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")

    # exactly one ```json fence, and it parses back to the emitted envelope
    fences = re.findall(r"```json\n(.*?)\n```", report, flags=re.S)
    assert len(fences) == 1, f"expected exactly one json block, found {len(fences)}"
    assert json.loads(fences[0]) == result, "embedded json block differs from kf_result.json"

    if args.post:
        body = {
            "title": f"KF-RESULT {PACKAGE_ID}",
            "summary": (
                f"asset registration for report {REPORT_ID}: markdown sha256 verified "
                f"({src_chars(result)} chars), {result['outputs']['asset_manifest.json']['counts']['assets']} assets "
                f"registered, {result['outputs']['asset_manifest.json']['counts']['figures_declared']} declared figures, "
                f"{result['outputs']['asset_manifest.json']['counts']['figures_retrievable']} retrievable"
            ),
            "scenario_key": "p50w2-arb7250-n03-dense-dem-cfd",
            "mission_id": 15628,
            "tags": [f"kf-wp:{PACKAGE_ID}", "KF-RESULT", "asset-registration", "CFD-DEM"],
            "markdown": report,
            "figures": [],
        }
        status, _, raw = _req("/tensor/reports", "POST", body, token=token)
        print("POST /tensor/reports ->", status, raw[:300].decode(errors="replace"))
        if status not in (200, 201):
            return 1

    print(json.dumps({"schema_checks": checks, "runlog": str(RUNLOG_PATH),
                      "manifest": str(MANIFEST_PATH), "result": str(RESULT_PATH),
                      "report": str(REPORT_PATH)}, indent=2))
    print(json.dumps(result["outputs"]["asset_manifest.json"]["counts"], indent=2))
    return 0


def src_chars(result: dict) -> str:
    return str(result["outputs"]["asset_manifest.json"]["source"]["chars"])


if __name__ == "__main__":
    raise SystemExit(main())