#!/usr/bin/env python3
"""KF work package 01-asset-registration: register a report's source asset set.

Generic tool (no per-report constants): the same code registers any report that is
handed to the KF lane, so the artefact shape cannot drift between packages.

Design goals
------------
* zero hand-copying -- every locator, quote and count is derived from the report
  record returned by ``GET /tensor/reports/<id>`` (or from a byte-identical local
  snapshot via ``--record``);
* no invented information -- a reference the record cannot resolve is emitted as
  ``referenced_unresolved`` / ``declared_absent`` instead of being guessed;
* deterministic output -- no wall-clock timestamps, identical inputs give identical
  bytes, so the manifest can itself be hash-pinned and re-derived by the gate.

Resolution semantics (pinned here so the manifest is self-describing)
---------------------------------------------------------------------
``resolved_in_source``   bytes/text resolved: the markdown field itself, a referenced
                         file that is found in the checked worktree, or a figure whose
                         png payload is present in the record.
``referenced_unresolved``referenced by the report, but the content cannot be resolved
                         from the record (figure name+caption without png payload).
``declared_absent``      declared by the report, expected in another repository/scope,
                         not present in the checked worktree.

Outputs (into ``--out-dir``): ``asset_manifest.json`` (schemas/asset_manifest.v1.schema.json)
and ``kf_result.json`` (schemas/kf_result.v1.schema.json).

Usage
-----
    python3 scripts/kf/register_assets.py \
        --report-id 7920 --package-id wp-7920-01 \
        --out-dir docs/kf/wp-7920-01 --record-out docs/kf/wp-7920-01/source_7920.json

Credentials come from $TENSOR_API_BASE / $TENSOR_AGENT_USER / $TENSOR_AGENT_PASS.
``--record PATH`` reads an already captured report JSON instead of the API.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

TASK_TYPE = "01-asset-registration"
MANIFEST_SCHEMA = "asset_manifest.v1"
CONTRACT_VERSION = "1.0"
PRODUCER = "scripts/kf/register_assets.py"

# Path-like reference: keeps the en-dash used by figure ranges ("fig1–3.png").
_REF_RE = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_./\u2013-]*\.(?:py|json|csv|png|md|txt|ya?ml|toml|sh)\b"
)
_HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")

_CLASS_BY_SUFFIX = {
    ".py": "source_code",
    ".sh": "script",
    ".json": "data",
    ".csv": "dataset",
    ".png": "figure",
    ".md": "doc",
    ".txt": "doc",
    ".yaml": "data",
    ".yml": "data",
    ".toml": "config",
}


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
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
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
# source-text helpers
# --------------------------------------------------------------------------- #
def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def line_index(md: str) -> list[tuple[int, int, int]]:
    """[(line_no 1-based, start_offset, end_offset)] for ``md.split('\\n')``."""
    out, offset = [], 0
    for i, line in enumerate(md.split("\n"), 1):
        out.append((i, offset, offset + len(line)))
        offset += len(line) + 1
    return out


def line_of(index: list[tuple[int, int, int]], offset: int) -> int:
    for line_no, start, end in index:
        if start <= offset <= end:
            return line_no
    return index[-1][0]


def section_of(md: str, offset: int) -> str:
    """Nearest preceding markdown heading ('' when the text precedes any heading)."""
    section = ""
    for line in md[:offset].split("\n"):
        m = _HEADING_RE.match(line)
        if m:
            section = m.group(2).strip()
    return section or "document"


def occurrences(md: str, token: str) -> list[int]:
    starts, i = [], md.find(token)
    while i >= 0:
        starts.append(i)
        i = md.find(token, i + 1)
    return starts


def collect_references(md: str) -> list[dict]:
    """Referenced path-like tokens, canonicalised (bare basename <-> dotted path)."""
    seen: dict[str, int] = {}
    order: list[str] = []
    for m in _REF_RE.finditer(md):
        token = m.group(0)
        if token.startswith(("http", "www")):
            continue
        if token not in seen:
            seen[token] = m.start()
            order.append(token)
    order.sort(key=lambda t: seen[t])

    groups: list[dict] = []
    for token in order:
        placed = False
        for g in groups:
            other = g["label"]
            if token == other:
                placed = True
                break
            if token.endswith("/" + other) or other.endswith("/" + token):
                if len(token) > len(other):
                    g["label"] = token
                g["tokens"].append(token)
                placed = True
                break
        if not placed:
            groups.append({"label": token, "tokens": [token]})
    for g in groups:
        g["tokens"] = sorted(set(g["tokens"]), key=lambda t: md.find(t))
        g["occurrences"] = sorted(
            {start for token in g["tokens"] for start in occurrences(md, token)}
        )
    return groups


def _asset_class(label: str) -> str:
    return _CLASS_BY_SUFFIX.get(Path(label).suffix.lower(), "artifact")


# --------------------------------------------------------------------------- #
# manifest construction
# --------------------------------------------------------------------------- #
def build_manifest(
    record: dict,
    *,
    package_id: str,
    expect_sha256: str | None = None,
    expect_chars: int | None = None,
    repo_root: Path,
    lane: str = "C",
) -> dict:
    md = record.get("markdown") or ""
    digest = sha256_hex(md.encode("utf-8"))
    index = line_index(md)
    lines = md.split("\n")
    assets: list[dict] = []

    def add(asset_class: str, label: str, *, token: str | None, offset: int | None,
            resolution: str, check: str, result: str, note: str,
            extra_locator: dict | None = None) -> None:
        asset_id = f"A{len(assets) + 1:02d}"
        if offset is None:  # document-level locator
            locator = {
                "method": "document",
                "start_char": 0,
                "end_char": len(md),
                "start_line": 1,
                "end_line": len(lines),
                "quote": md.strip().split("\n")[0],
                "quote_sha256": sha256_hex(md.strip().split("\n")[0].encode()),
                "unique": True,
                "occurrences": 1,
            }
            section = "document"
        else:
            hits = occurrences(md, token or "")
            line_no = line_of(index, offset)
            locator = {
                "method": "char_span",
                "start_char": offset,
                "end_char": offset + len(token or ""),
                "start_line": line_no,
                "end_line": line_no,
                "quote": md[offset: offset + len(token or "")],
                "quote_sha256": sha256_hex(md[offset: offset + len(token or "")].encode()),
                "unique": len(hits) == 1,
                "occurrences": len(hits),
            }
            section = section_of(md, offset)
        locator.update(extra_locator or {})
        assets.append(
            {
                "asset_id": asset_id,
                "asset_class": asset_class,
                "label": label,
                "token": token,
                "in_report_section": section or "document",
                "locator": locator,
                "resolution": resolution,
                "resolution_check": {"check": check, "result": result},
                "note": note,
            }
        )

    # A01 -- the source text itself: the only asset whose bytes are in the record
    add(
        "report_markdown",
        f"reports/{record['id']}#markdown",
        token=None,
        offset=None,
        resolution="resolved_in_source",
        check="sha256(utf-8 markdown bytes) == manifest.source.hash",
        result="resolved",
        note=f"{len(md)} chars / {len(md.encode('utf-8'))} bytes, "
        "quoted locators below are slices of these bytes",
    )

    figures = record.get("figures") or []
    fig_by_name = {str(f.get("name") or ""): (i, f) for i, f in enumerate(figures)}
    fig_seen: set[str] = set()

    for group in collect_references(md):
        label = group["label"]
        offset = group["occurrences"][0]
        asset_class = _asset_class(label)
        name = Path(label).name

        if asset_class == "figure":
            fig_seen.add(name)
            entry = fig_by_name.get(name) or fig_by_name.get(label)
            hits = len(group["occurrences"])
            if entry and entry[1].get("png_base64"):
                payload = entry[1]["png_base64"]
                add(
                    "figure", label, token=label, offset=offset,
                    resolution="resolved_in_source",
                    check=f"record.figures[{entry[0]}].png_base64 present",
                    result="resolved",
                    note=f"png payload present in record ({len(payload)} b64 chars); "
                    "bytes hashable from the record",
                )
            elif entry:
                add(
                    "figure", label, token=label, offset=offset,
                    resolution="referenced_unresolved",
                    check=f"record.figures[{entry[0]}].png_base64 / "
                    f"GET /tensor/reports/{record['id']}/figures/{name}",
                    result="unresolved",
                    note="record carries name+caption only (no png payload; figure "
                    "endpoint absent), so no image bytes are hashed here",
                )
            else:
                add(
                    "figure", label, token=label, offset=offset,
                    resolution="referenced_unresolved",
                    check="record.figures[] name match",
                    result="unresolved",
                    note=f"referenced {hits}x in markdown but not declared in record.figures",
                )
            continue

        present = (repo_root / label).exists() or (repo_root / name).exists()
        add(
            asset_class, label, token=label, offset=offset,
            resolution="resolved_in_source" if present else "declared_absent",
            check=f"worktree existence: {label}",
            result="present" if present else "absent",
            note=(
                f"referenced {len(group['occurrences'])}x in markdown; found in the checked "
                "TensorKnowledge worktree"
                if present
                else f"referenced {len(group['occurrences'])}x in markdown; declared artefact "
                "lives outside this repository (checked scope = TensorKnowledge worktree)"
            ),
        )

    # figures declared by the record but never cited in the text are still assets
    for i, fig in enumerate(figures):
        name = str(fig.get("name") or f"figure[{i}]")
        if name in fig_seen:
            continue
        add(
            "figure", name, token=None, offset=None,
            resolution="referenced_unresolved",
            check=f"record.figures[{i}].png_base64",
            result="unresolved",
            note="declared in record.figures but not cited in the markdown; "
            + ("payload present" if fig.get("png_base64") else "no payload"),
        )

    by_class: dict[str, int] = {}
    by_resolution: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_resolution[a["resolution"]] = by_resolution.get(a["resolution"], 0) + 1

    pinned = (expect_sha256 or "").replace("sha256:", "").lower()
    contract_origin = "contract_declared"
    if not pinned:
        pinned = digest
        contract_origin = (
            "self_pinned_at_registration: no platform work-package contract endpoint is "
            "available to this lane; the registration-time measurement is pinned and "
            "re-derived independently by the verification step"
        )

    return {
        "schema": MANIFEST_SCHEMA,
        "package_id": package_id,
        "task_type": TASK_TYPE,
        "report_id": str(record["id"]),
        "lane": lane,
        "producer": PRODUCER,
        "generator_inputs": {
            "report_id": str(record["id"]),
            "package_id": package_id,
            "expect_sha256": ("sha256:" + pinned),
            "expect_chars": expect_chars,
            "record_path_or_api": "GET /tensor/reports/" + str(record["id"]),
        },
        "source": {
            "uri": f"tensor://reports/{record['id']}",
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "contract_source_hash": "sha256:" + pinned,
            "contract_origin": contract_origin,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "lines": len(lines),
            "title": record.get("title") or "",
            "scenario_key": record.get("scenario_key") or "",
            "platform_figures": [str(f.get("name") or "") for f in figures],
            "platform_tags": record.get("tags") or [],
            "chars_match_contract": (len(md) == expect_chars) if expect_chars else None,
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_resolution,
            "resolved_in_source": by_resolution.get("resolved_in_source", 0),
            "referenced_unresolved": by_resolution.get("referenced_unresolved", 0),
            "declared_absent": by_resolution.get("declared_absent", 0),
            "markdown_locators": sum(
                1 for a in assets if a["locator"]["method"] == "char_span"
            ),
        },
        "assets": assets,
        "claims": [],
        "claims_note": "registration only: no extraction, no classification, no verification; "
        "empty claims list is the contract for task_type=01-asset-registration",
        "resolution_semantics": {
            "resolved_in_source": "bytes/text resolved (markdown itself, file present in the "
            "checked worktree, or figure payload present in the record)",
            "referenced_unresolved": "referenced by the report but not resolvable from the "
            "record (figure metadata only)",
            "declared_absent": "declared by the report, expected outside the checked worktree",
            "checked_scope": "TensorKnowledge worktree",
        },
        "integrity": {
            "quote_uniqueness": {
                "unique": sum(1 for a in assets if a["locator"]["unique"]),
                "non_unique": sum(1 for a in assets if not a["locator"]["unique"]),
            },
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == pinned,
            "verified_logic": "no asset is marked verified here; the platform gate re-hashes "
            "the markdown and re-resolves every locator",
        },
    }


def build_result(manifest: dict, record: dict) -> dict:
    return {
        "package_id": manifest["package_id"],
        "task_type": manifest["task_type"],
        "contract_version": CONTRACT_VERSION,
        "report_id": str(record["id"]),
        "provenance": {
            "source_uri": f"tensor://reports/{record['id']}",
            "source_field": "markdown",
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_hash_matches": bool(manifest["integrity"]["hash_matches_contract"]),
            "title": record.get("title") or "",
            "scenario_key": record.get("scenario_key") or "",
            "chars": manifest["source"]["chars"],
        },
        "outputs": {"asset_manifest.json": manifest},
    }


def write_outputs(manifest: dict, result: dict, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (out_dir / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--report-id", required=True)
    ap.add_argument("--package-id", required=True)
    ap.add_argument("--expect-sha256", default=None)
    ap.add_argument("--expect-chars", type=int, default=None)
    ap.add_argument("--record", default=None, help="local report JSON instead of the API")
    ap.add_argument("--record-out", default=None, help="write the fetched record here")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--lane", default="C")
    args = ap.parse_args(argv)

    record = load_record(args.report_id, args.record)
    if str(record.get("id")) != str(args.report_id):
        raise SystemExit(f"record id {record.get('id')} != requested {args.report_id}")

    if args.record_out:
        Path(args.record_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.record_out).write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    manifest = build_manifest(
        record,
        package_id=args.package_id,
        expect_sha256=args.expect_sha256,
        expect_chars=args.expect_chars,
        repo_root=Path(args.repo_root),
        lane=args.lane,
    )
    result = build_result(manifest, record)
    write_outputs(manifest, result, Path(args.out_dir))

    print(f"report_id={manifest['report_id']} package_id={manifest['package_id']}")
    print(f"sha256={manifest['source']['hash']} "
          f"contract_match={manifest['integrity']['hash_matches_contract']}")
    print(f"chars={manifest['source']['chars']} bytes={manifest['source']['bytes_utf8']}")
    print(f"counts={json.dumps(manifest['counts'], ensure_ascii=False)}")
    return 0 if manifest["integrity"]["hash_matches_contract"] else 2


if __name__ == "__main__":
    sys.exit(main())