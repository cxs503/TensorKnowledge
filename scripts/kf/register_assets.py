#!/usr/bin/env python3
"""KF work-package 01-asset-registration: register a report's source asset set.

Design goals
------------
* zero hand-copying: every locator/quote is extracted programmatically from the
  report record fetched from the platform API (or a byte-identical local record);
* no invented information: anything the source does not contain is emitted as an
  explicit ``unresolved`` entry instead of being guessed;
* deterministic output: no wall-clock timestamps, identical inputs -> identical
  bytes, so the manifest itself can be hash-pinned.

The manifest is intentionally *registration only*: it does not extract claims
(work package 03's job) and never marks anything as verified (the platform gate
computes verification).

Usage
-----
    python3 scripts/kf/register_assets.py \
        --report-id 459 \
        --expect-sha256 333ea7e4c7b908bc9701a34c72960d0e0e8ed728798758fd68f830a75507f6b9 \
        --expect-chars 7586 \
        --package-id wp-459-01 \
        --out-dir docs/kf/wp-459-01

Credentials come from $TENSOR_API_BASE / $TENSOR_AGENT_USER / $TENSOR_AGENT_PASS.
``--record PATH`` reads an already captured report JSON instead of the API.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

PACKAGE_ID = "wp-459-01"
TASK_TYPE = "01-asset-registration"

# A path-like reference: keeps the en-dash used by the source ("fig1–3.png").
_REF_RE = re.compile(r"[A-Za-z0-9_./\u2013-]+\.(?:py|json|md|png)")
_COMMIT_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
_QUOTE_WINDOW = 80


# --------------------------------------------------------------------------- #
# fetching
# --------------------------------------------------------------------------- #
def _login(base: str, user: str, password: str) -> str:
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": user, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    payload = json.load(urllib.request.urlopen(req, timeout=30))
    token = payload.get("access_token") or payload.get("token")
    if not token:
        raise RuntimeError("login returned no token")
    return token


def fetch_record(report_id: str) -> dict:
    base = os.environ["TENSOR_API_BASE"]
    token = _login(base, os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"])
    req = urllib.request.Request(
        f"{base}/tensor/reports/{report_id}", headers={"Authorization": "Bearer " + token}
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def load_record(report_id: str, record_path: str | None) -> dict:
    if record_path:
        return json.loads(Path(record_path).read_text(encoding="utf-8"))
    return fetch_record(report_id)


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _line_index(md: str) -> list[tuple[int, int, str]]:
    """[(line_no, start_offset, line_text)] with 1-based line numbers."""
    out, offset = [], 0
    for i, line in enumerate(md.split("\n"), 1):
        out.append((i, offset, line))
        offset += len(line) + 1
    return out


def _quote_for(line: str, match_start: int, match_end: int) -> str:
    """A verbatim slice of ``line`` around the reference (substring of markdown)."""
    if len(line) <= 2 * _QUOTE_WINDOW + (match_end - match_start):
        return line
    lo = max(0, match_start - _QUOTE_WINDOW)
    hi = min(len(line), match_end + _QUOTE_WINDOW)
    return line[lo:hi]


def find_locators(md: str, needle: str) -> list[dict]:
    """All occurrences of ``needle`` in ``md`` as resolvable locator dicts."""
    locs = []
    for line_no, _start, line in _line_index(md):
        for m in re.finditer(re.escape(needle), line):
            quote = _quote_for(line, m.start(), m.end())
            locs.append(
                {
                    "source_field": "markdown",
                    "line": line_no,
                    "quote": quote,
                    "char_offset": md.index(line) + m.start(),
                }
            )
            break  # one locator per line is enough for resolvability
    return locs


def canonicalise(refs: list[tuple[str, int]]) -> list[dict]:
    """Merge bare basenames with their dotted-path variants (same logical file)."""
    groups: list[dict] = []
    for name, line in refs:
        placed = False
        for g in groups:
            if name == g["name"]:
                g["occurrences"].append({"name": name, "line": line})
                placed = True
                break
            if name.endswith("/" + g["name"]) or g["name"].endswith("/" + name):
                g["occurrences"].append({"name": name, "line": line})
                g["name"] = name if len(name) > len(g["name"]) else g["name"]
                placed = True
                break
        if not placed:
            groups.append({"name": name, "occurrences": [{"name": name, "line": line}]})
    return groups


# --------------------------------------------------------------------------- #
# manifest construction
# --------------------------------------------------------------------------- #
def build_manifest(
    record: dict,
    *,
    package_id: str,
    expect_sha256: str,
    expect_chars: int | None,
    repo_root: Path,
) -> dict:
    md = record.get("markdown") or ""
    digest = sha256_hex(md)
    assets: list[dict] = []
    unresolved: list[dict] = []

    def add_asset(**kw) -> None:
        kw["asset_id"] = f"asset-459-{len(assets) + 1:04d}"
        assets.append(kw)

    # 1) the source text itself -- the only byte-resolvable asset in the record
    add_asset(
        kind="source_text",
        name="markdown",
        logical_name=f"tensor://reports/{record['id']}#markdown",
        media_type="text/markdown; charset=utf-8",
        payload={
            "present": bool(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "chars": len(md),
            "sha256": digest,
        },
        locator={"source_field": "markdown", "offset": 0, "length": len(md)},
        resolvable=True,
        status="registered",
    )

    # 2) figures: metadata may exist without payload -> register honestly
    figures = record.get("figures") or []
    md_fig_line = None
    for line_no, _s, line in _line_index(md):
        if "图 1" in line and ("附件" in line or "fig" in line.lower()):
            md_fig_line = (line_no, line)
            break
    for idx, fig in enumerate(figures):
        raw_b64 = fig.get("png_base64") or ""
        payload_bytes = b""
        if raw_b64:
            try:
                payload_bytes = base64.b64decode(raw_b64, validate=True)
            except Exception:  # noqa: BLE001 - corrupt payload is an asset-level finding
                payload_bytes = b""
        present = bool(payload_bytes)
        fig_asset = {
            "kind": "figure",
            "name": fig.get("name") or f"figure[{idx}]",
            "logical_name": f"tensor://reports/{record['id']}#/figures/{idx}",
            "media_type": "image/png",
            "declared_metadata": {"caption": fig.get("caption", "")},
            "record_pointer": f"/figures/{idx}",
            "payload": {
                "present": present,
                "bytes": len(payload_bytes),
                "sha256": hashlib.sha256(payload_bytes).hexdigest() if present else None,
            },
            "resolvable": present,
            "status": "registered" if present else "declared_metadata_only",
        }
        if md_fig_line:
            fig_asset["locator"] = {
                "source_field": "markdown",
                "line": md_fig_line[0],
                "quote": md_fig_line[1],
            }
        add_asset(**fig_asset)
        if not present:
            unresolved.append(
                {
                    "item": f"/figures/{idx}:{fig.get('name')}",
                    "issue": "figure entry carries name+caption but no png payload",
                    "observed": {"png_base64_chars": len(raw_b64), "bytes": 0},
                    "impact": "binary image bytes cannot be hashed/registered from this source",
                    "status": "unresolved",
                }
            )

    # 3) declared artifacts referenced by the text (paths + commit prefix)
    refs: list[tuple[str, int]] = []
    for line_no, _start, line in _line_index(md):
        for m in _REF_RE.finditer(line):
            refs.append((m.group(0), line_no))
    for group in canonicalise(refs):
        name = group["name"]
        locators: list[dict] = []
        seen_loc: set[tuple[int, str]] = set()
        for variant in sorted({o["name"] for o in group["occurrences"]}):
            for loc in find_locators(md, variant):
                key = (loc["line"], loc["quote"])
                if key not in seen_loc:
                    seen_loc.add(key)
                    locators.append(loc)
        locators.sort(key=lambda loc: (loc["line"], loc["char_offset"]))
        asset = {
            "kind": "declared_artifact",
            "name": name,
            "name_variants": sorted({o["name"] for o in group["occurrences"]}),
            "media_type": _guess_media(name),
            "declared_in_lines": sorted({o["line"] for o in group["occurrences"]}),
            "locator": locators[0] if locators else None,
            "locators": locators,
            "payload": {"present": False, "bytes": None, "sha256": None},
            "resolvable": False,
            "status": "declared_only",
        }
        if "\u2013" in name:
            asset["status"] = "declared_shorthand"
            asset["notes"] = (
                "en-dash range in the source, not a literal filename; "
                "expands to the per-figure files listed in the same package"
            )
        add_asset(**asset)

    commit_locators: dict[str, list[dict]] = {}
    for line_no, _start, line in _line_index(md):
        for m in _COMMIT_RE.finditer(line):
            tok = m.group(0)
            if not any(c.isdigit() for c in tok) or len(tok) < 7:
                continue
            commit_locators.setdefault(tok, []).append(
                {
                    "source_field": "markdown",
                    "line": line_no,
                    "quote": _quote_for(line, m.start(), m.end()),
                }
            )
    for tok, locators in commit_locators.items():
        add_asset(
            kind="declared_commit",
            name=tok,
            abbreviated=len(tok) < 40,
            locator=locators[0],
            locators=locators,
            resolvable=False,
            status="declared_only",
            payload={"present": False, "bytes": None, "sha256": None},
        )
        if len(tok) < 40:
            unresolved.append(
                {
                    "item": f"commit:{tok}",
                    "issue": "only an abbreviated commit id appears in the source",
                    "observed": {"hex_chars": len(tok), "occurrences": len(locators)},
                    "impact": "git object identity / prereg binding cannot be re-resolved from this report alone",
                    "status": "unresolved",
                }
            )

    # 4) artifact-existence check inside this delivery checkout (honest scope note)
    root = Path(repo_root)
    for asset in assets:
        if asset["kind"] != "declared_artifact" or "\u2013" in asset["name"]:
            continue
        for cand in asset.get("name_variants", [asset["name"]]):
            asset.setdefault("existence_check", []).append(
                {"path": cand, "checked_in": "TensorKnowledge worktree", "exists": (root / cand).exists()}
            )
        asset["existence_check_all_absent"] = all(
            not e["exists"] for e in asset["existence_check"]
        )

    # 5) seals/hashes promised by the text but not present in it
    if "sha256" in md and not re.search(r"\bsha256:[0-9a-f]{64}\b", md):
        unresolved.append(
            {
                "item": "prereg_v2.seal.json#sha256",
                "issue": "text refers to a content hash seal but no 64-hex sha256 literal is present",
                "observed": {"sha256_literals_in_markdown": 0},
                "impact": "prereg_v2.json integrity cannot be re-derived from the report alone; "
                "requires artifacts/prereg_v2.seal.json (not part of this record)",
                "status": "unresolved",
            }
        )

    return {
        "manifest_version": "1.0",
        "package_id": package_id,
        "task_type": TASK_TYPE,
        "generated_by": "scripts/kf/register_assets.py",
        "generator_inputs": {
            "report_id": str(record["id"]),
            "expect_sha256": expect_sha256,
            "expect_chars": expect_chars,
        },
        "source": {
            "report_id": str(record["id"]),
            "source_uri": f"tensor://reports/{record['id']}",
            "source_field": "markdown",
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "status": record.get("status"),
            "tags": record.get("tags") or [],
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "sha256": digest,
            "hash_independently_recomputed": True,
            "contract_declared_source_hash": expect_sha256,
            "source_hash_matches": digest == expect_sha256,
            "contract_declared_chars": expect_chars,
            "chars_match": (len(md) == expect_chars) if expect_chars is not None else None,
            "figures_entries": len(figures),
        },
        "asset_counts": {
            "total": len(assets),
            "registered_with_bytes": sum(
                1 for a in assets if a.get("resolvable") and a["payload"].get("present")
            ),
            "by_status": {
                st: sum(1 for a in assets if a["status"] == st)
                for st in sorted({a["status"] for a in assets})
            },
            "unresolved_items": len(unresolved),
        },
        "assets": assets,
        "claims": [],
        "unresolved": unresolved,
        "notes": [
            "registration only: no extraction, no classification, no verification",
            "every locator quote is a verbatim substring of the source markdown",
            "figure entries carry metadata only; png payload is absent in the report record",
            "declared artifacts live outside this repository (TensorKnowledge); "
            "existence_check records that scope limitation",
        ],
    }


def _guess_media(name: str) -> str:
    return {
        ".py": "text/x-python",
        ".json": "application/json",
        ".md": "text/markdown",
        ".png": "image/png",
    }.get(Path(name).suffix, "application/octet-stream")


def build_result(manifest: dict, record: dict) -> dict:
    return {
        "package_id": manifest["package_id"],
        "task_type": manifest["task_type"],
        "report_id": str(record["id"]),
        "provenance": {
            "source_hash": "sha256:" + manifest["source"]["sha256"],
            "source_field": "markdown",
            "producer": "scripts/kf/register_assets.py",
            "notes": (
                "hash recomputed from GET /tensor/reports/459 markdown; "
                "report-markdown bytes only (figures metadata excluded)"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report-id", default="459")
    ap.add_argument("--package-id", default=PACKAGE_ID)
    ap.add_argument("--expect-sha256", required=True)
    ap.add_argument("--expect-chars", type=int, default=None)
    ap.add_argument("--record", default=None, help="local report JSON instead of API")
    ap.add_argument("--out-dir", default="docs/kf/wp-459-01")
    ap.add_argument("--repo-root", default=".")
    args = ap.parse_args(argv)

    record = load_record(args.report_id, args.record)
    if str(record.get("id")) != str(args.report_id):
        raise SystemExit(f"record id {record.get('id')} != requested {args.report_id}")

    manifest = build_manifest(
        record,
        package_id=args.package_id,
        expect_sha256=args.expect_sha256,
        expect_chars=args.expect_chars,
        repo_root=Path(args.repo_root),
    )
    result = build_result(manifest, record)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(f"report_id={manifest['source']['report_id']}")
    print(f"sha256={manifest['source']['sha256']} match={manifest['source']['source_hash_matches']}")
    print(f"chars={manifest['source']['chars']} match={manifest['source']['chars_match']}")
    print(f"assets={manifest['asset_counts']}")
    return 0 if manifest["source"]["source_hash_matches"] else 2


if __name__ == "__main__":
    sys.exit(main())