#!/usr/bin/env python3
"""wp-444-04 · independent verification of the upstream wp-444-01 registration.

What this script is:  a *re-derivation* pass over the upstream package
`wp-444-01` (01-asset-registration of tensor report 444) and over the source
text it registers.  What it is not: an authority.  It writes status per check
and never writes a `verified` field — verification is a platform-gate output,
not a reviewer output.

Evidence read (never trusted, always re-derived):
  * live record ``GET $TENSOR_API_BASE/tensor/reports/444`` (``--live``, default)
  * pinned byte snapshot ``docs/kf/wp-444-04/source/report_444.md`` (``--snapshot``)
  * upstream committed result document ``docs/kf_result_wp-444-01.md``

Emitted (no hand-copied number, every value comes from the two sources above):
  * ``--out`` JSON used by ``work/build_review_report.py``

Usage:
  python3 work/verify_wp444_01.py                       # live, write --out
  python3 work/verify_wp444_01.py --snapshot            # offline, pinned bytes
  python3 work/verify_wp444_01.py --write-snapshot      # re-pin the snapshot
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "docs/kf/wp-444-04/source/report_444.md"
UPSTREAM_DOC = ROOT / "docs/kf_result_wp-444-01.md"
DEFAULT_OUT = Path("/tmp/wp-444-04/verify.json")
REPORT_ID = "444"

# A span of this shape is a schema/field placeholder ("png_base64", "{name, caption}"),
# not a quotation of the source text.
PLACEHOLDER = re.compile(r"^\{.*\}$|^\w+$")


# --------------------------------------------------------------------------- api
def _token(base: str) -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    tok = payload.get("access_token") or payload.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(payload))
    return tok


def fetch_record() -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(f"{base}/tensor/reports/{REPORT_ID}",
                                 headers={"Authorization": "Bearer " + _token(base)})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def snapshot_bytes() -> bytes:
    return SNAPSHOT.read_bytes()


# ------------------------------------------------------------------ extraction
def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_tables(lines: list[str]) -> list[dict]:
    """GFM tables: a header row immediately followed by a delimiter row."""
    out = []
    for i, line in enumerate(lines):
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-|: ]+\|$", lines[i + 1]):
            rows, j = [], i + 2
            while j < len(lines) and lines[j].startswith("|"):
                rows.append(lines[j])
                j += 1
            out.append({"start_line": i + 1, "end_line": j, "header": line, "data_rows": len(rows)})
    return out


def structure(md: str) -> dict:
    lines = md.split("\n")
    lvl2 = [ln for ln in lines if ln.startswith("## ")]
    lvl3 = [ln for ln in lines if ln.startswith("### ")]
    return {
        "chars": len(md),
        "lines": len(lines),
        "level2_headings": lvl2,
        "level3_headings": lvl3,
        "level2_count": len(lvl2),
        "level3_count": len(lvl3),
        "heading_count_all_levels": len([ln for ln in lines if re.match(r"^#{1,6} ", ln)]),
        "tables": count_tables(lines),
        "tables_count": len(count_tables(lines)),
        "fenced_code_blocks": md.count("```") // 2,
        "inline_code_spans": len(re.findall(r"`[^`\n]+`", md)),
    }


def upstream_document() -> dict:
    """Parse the upstream package's committed result document (never trusted, quoted)."""
    doc = UPSTREAM_DOC.read_text(encoding="utf-8")
    hashes = sorted(set(re.findall(r"\b[0-9a-f]{64}\b", doc)))
    tally = re.search(
        r"识别\s*(\d+)\s*个章节标题、\s*(\d+)\s*张表格、\s*(\d+)\s*个\s*figures\s*条目、"
        r"\s*(\d+)\s*个代码文件引用", doc)
    unresolved = re.search(r"unresolved_assets_count[\"'\s:]+(\d+)", doc)
    claims = re.search(r"claims_count[\"'\s:]+(\d+)", doc)
    return {
        "path": str(UPSTREAM_DOC.relative_to(ROOT)),
        "sha256": sha256_text(doc),
        "declared_source_hash": ("sha256:" + hashes[0]) if hashes else None,
        "declared_hash_occurrences": len(hashes),
        "declared_tallies": {
            "level_headings": int(tally.group(1)),
            "tables": int(tally.group(2)),
            "figures": int(tally.group(3)),
            "code_references": int(tally.group(4)),
        } if tally else None,
        "declared_unresolved_count": int(unresolved.group(1)) if unresolved else None,
        "declared_claims_count": int(claims.group(1)) if claims else None,
        "declared_some_artifact_locator_verified_statement": (
            "source_locator_resolvable" in doc),
    }


def evidence_rows(doc_text: str) -> list[dict]:
    """Rows of the upstream ④ 证据定位表: (field, quote spans, location)."""
    rows, in_table = [], False
    for line in doc_text.split("\n"):
        if line.startswith("| 字段/声明 |"):
            in_table = True
            continue
        if in_table and line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3 or set(cells[0]) <= set("-: "):
                continue
            rows.append({"field": cells[0], "quote_cell": cells[1], "location": cells[2]})
        elif in_table and rows:
            break
    return rows


def classify_locator(row: dict) -> list[dict]:
    """Turn one evidence row into quote bindings with a declared locator kind."""
    quotes = re.findall(r"`([^`]+)`", row["quote_cell"])
    if not quotes:                       # a computed statement, not a quotation
        return [{"field": row["field"], "quote": row["quote_cell"], "kind": "computed",
                 "location": row["location"]}]
    loc = row["location"]
    if "程序计算" in loc:
        kind = "computed"
    elif "API" in loc:
        kind = "record"
    elif re.search(r"(markdown|section|line)", loc, re.I):
        kind = "markdown"
    else:
        kind = "unbound"
    if kind == "computed":             # a digest the upstream recomputed; we re-recompute it
        return [{"field": row["field"], "quote": quotes[0], "kind": "computed",
                 "location": loc}]
    out = []
    for q in quotes:
        if PLACEHOLDER.match(q.strip()):
            out.append({"field": row["field"], "quote": q, "kind": "placeholder",
                        "location": loc})
            continue
        span = re.search(r"lines?\s*(\d+)\s*(?:[-–]\s*(\d+))?", loc)
        out.append({
            "field": row["field"], "quote": q, "kind": kind, "location": loc,
            "declared_line_span": [int(span.group(1)), int(span.group(2) or span.group(1))]
            if span else None,
        })
    return out


def bind(binding: dict, md: str, record: dict) -> dict:
    """Resolve a quote against its declared locator kind."""
    q = binding["quote"]
    if binding["kind"] == "markdown":
        binding["verbatim"] = q in md
        pos = md.find(q)
        binding["found_char"] = pos if pos >= 0 else None
        binding["found_line"] = md[:pos].count("\n") + 1 if pos >= 0 else None
        span = binding.get("declared_line_span")
        if span:
            block = "\n".join(md.split("\n")[span[0] - 1:span[1]])
            binding["span_text_contains_head"] = block.strip()[:40] in block
            binding["span_lines"] = [span[0], span[1]]
    elif binding["kind"] == "record":
        flat = json.dumps(record, ensure_ascii=False)
        binding["verbatim"] = q in flat
        binding["found_in_record_field"] = next(
            (k for k, v in record.items() if isinstance(v, str) and q in v), None)
    else:
        binding["verbatim"] = None
    return binding


# ------------------------------------------------------------------------ main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", action="store_true", help="use pinned bytes, no network")
    ap.add_argument("--write-snapshot", action="store_true", help="re-pin the snapshot from live")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    live_used = not args.snapshot
    if live_used:
        record = fetch_record()
        md = record["markdown"]
        if args.write_snapshot:
            SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
            SNAPSHOT.write_text(md, encoding="utf-8")
            print("pinned snapshot ->", SNAPSHOT.relative_to(ROOT), flush=True)
    else:
        md = snapshot_bytes().decode("utf-8")
        record = {}   # record-level fields are unavailable offline, and that is reported

    up = upstream_document()
    doc_text = UPSTREAM_DOC.read_text(encoding="utf-8")
    st = structure(md)
    digest = sha256_text(md)

    tallies = {
        "level2_headings": st["level2_count"],
        "tables": st["tables_count"],
        "figures": len(record.get("figures") or []),
    }
    claimed = up["declared_tallies"] or {}

    bindings = [bind(b, md, record)
                for row in evidence_rows(doc_text) for b in classify_locator(row)]

    out = {
        "package_id": "wp-444-04", "object": "wp-444-01", "report_id": REPORT_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": "live" if live_used else "snapshot",
        "endpoint": f"{os.environ.get('TENSOR_API_BASE', '')}/tensor/reports/{REPORT_ID}",
        "source": {
            "sha256": digest, "chars": len(md),
            "snapshot_path": str(SNAPSHOT.relative_to(ROOT)),
            "snapshot_sha256": sha256_text(snapshot_bytes().decode("utf-8"))
            if SNAPSHOT.is_file() else None,
            "declared_hash": up["declared_source_hash"],
            "hash_matches_upstream": digest == up["declared_source_hash"],
            "hash_matches_snapshot": SNAPSHOT.is_file()
            and digest == sha256_text(snapshot_bytes().decode("utf-8")),
        },
        "record": {
            "available": live_used,
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "status": record.get("status"),
            "fields": sorted(k for k in record if k != "markdown"),
            "figures": [{"name": f.get("name"), "has_png_base64": "png_base64" in f,
                         "keys": sorted(f)} for f in (record.get("figures") or [])],
        },
        "structure": st,
        "upstream": up,
        "upstream_tallies_match": {
            "headings": claimed.get("level_headings") == tallies["level2_headings"],
            "tables": claimed.get("tables") == tallies["tables"],
            "figures": claimed.get("figures") == tallies["figures"] if live_used else None,
            "code_references": claimed.get("code_references") == st["fenced_code_blocks"],
        },
        "locator_bindings": bindings,
        "locator_summary": {
            "total": len(bindings),
            "markdown_quotes": sum(1 for b in bindings if b["kind"] == "markdown"),
            "markdown_verbatim": sum(1 for b in bindings
                                     if b["kind"] == "markdown" and b.get("verbatim")),
            "record_quotes": sum(1 for b in bindings if b["kind"] == "record"),
            "record_verbatim": sum(1 for b in bindings
                                   if b["kind"] == "record" and b.get("verbatim")),
            "unbound_or_placeholder": sum(1 for b in bindings
                                          if b["kind"] in {"placeholder", "unbound"}),
        },
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in
                      ("mode", "source", "upstream_tallies_match", "locator_summary")},
                     ensure_ascii=False, indent=1))
    print("->", out_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())