#!/usr/bin/env python3
"""Register knowledge packages as versioned assets; export the asset index.

What it does
------------
1. Scans one or more package roots (default ``knowledge/``) for KE packages —
   a directory is a package when it contains at least one of ``claims/``,
   ``evidence/``, ``provenance/``, ``gaps/``.
2. Derives a KO identifier per package from its path
   (``knowledge/oss-lbm`` -> ``tko:oss-lbm``) and computes a *content digest*:
   sha256 over ``(relative path, file sha256)`` of every ``*.json`` record
   file, sorted — so the digest is machine-independent and changes iff record
   bytes change.
3. Registers the KO version (``--version``, default derived from the digest
   prefix) and, when a previous version of the same KO is already registered,
   registers the new one and links it with ``supersede_ko`` (lineage, no
   deletes).
4. Registers a dataset-level asset for the produced index itself (so the
   asset index is an asset with a pinned digest), then writes
   ``--index``/``--report`` artefacts.

``--verify`` mode
-----------------
Re-scans the roots and compares the recomputed digests with the digests pinned
in an existing ``--index`` artefact.  Exit code 0 iff every pinned asset still
matches (drift detection: a drifted *record* file is a hard failure, it must
show up as a new version, not as a silent rewrite).

Usage::

    python scripts/register_assets.py --root knowledge --db /tmp/ke.db \\
        --index artifacts/asset-index.json --report artifacts/health-report.json
    python scripts/register_assets.py --root knowledge --verify \\
        --index artifacts/asset-index.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import assets, contract, store  # noqa: E402

RECORD_DIRS = ("claims", "evidence", "provenance", "gaps")


# ---------------------------------------------------------------------------
# package discovery + digests
# ---------------------------------------------------------------------------
def find_packages(root: Path) -> list[Path]:
    """Directories under ``root`` that carry at least one KE record directory."""
    found = []
    for path in sorted(root.rglob("*")):
        if path.is_dir() and any((path / d).is_dir() for d in RECORD_DIRS):
            found.append(path)
    return found


def package_facts(pkg: Path) -> tuple[dict, list[str]]:
    """Record counts and claim domains as the *contract* sees the package.

    Uses :func:`ke.contract.discover` — the same reader the ingest path uses —
    so a package can never be counted differently here than in the store.
    """
    try:
        found = contract.discover(pkg)
    except (FileNotFoundError, ValueError):
        return {k: 0 for k in contract.KINDS}, []
    counts = {kind: len(found.records[kind]) for kind in contract.KINDS}
    domains = set()
    for rec, _src in found.records["claims"].values():
        scope = rec.get("scope") or {}
        domain = scope.get("domain") or rec.get("domain")
        if domain:
            domains.add(domain)
    return counts, sorted(domains)


def package_digest(pkg: Path, root: Path) -> dict:
    """Content digest of one package (path-normalized, order-independent)."""
    files = sorted(p for p in pkg.rglob("*.json") if p.is_file())
    per_file = []
    for f in files:
        rel = f.relative_to(root).as_posix()
        per_file.append((rel, hashlib.sha256(f.read_bytes()).hexdigest()))
    blob = json.dumps(per_file, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    counts, domains = package_facts(pkg)
    return {
        "package": pkg.relative_to(root).as_posix(),
        "files": len(files),
        "counts": counts,
        "domains": domains,
        "sha256": hashlib.sha256(blob).hexdigest(),
    }


def ko_id_for(package: str, prefix: str = "tko") -> str:
    return f"{prefix}:{package.replace('/', ':')}"


def version_for(digest: str) -> str:
    """Deterministic content-addressed version: ``0.0.<n>`` from digest prefix."""
    return f"1.0.{int(digest[:8], 16)}"


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------
def register(roots: list[Path], db_path: str, *, created_by: str, prefix: str,
             state: str = "in_review") -> dict:
    conn = store.connect(db_path)
    summaries = []
    try:
        for root in roots:
            for pkg in find_packages(root):
                info = package_digest(pkg, root)
                ko_id = ko_id_for(info["package"], prefix)
                version = version_for(info["sha256"])
                previous = assets.get_ko_latest(conn, ko_id)
                same = previous is not None and previous["content"].get("sha256") == info["sha256"]
                if same:
                    vid = previous["id"]
                    action = "unchanged"
                else:
                    vid = assets.register_ko_version(
                        conn, ko_id, version,
                        title=info["package"],
                        object_type="knowledge_package",
                        summary=(f"{info['files']} record files: "
                                 + ", ".join(f"{k}={v}" for k, v in info["counts"].items() if v)),
                        content=info,
                        # the registry records *existence*; promotion to
                        # published is a separate, audited review decision
                        # (ke assets review --decision approve)
                        state=state,
                        created_by=created_by,
                        source_file=f"{info['package']}/",
                    )
                    action = "registered"
                    if previous is not None:
                        try:
                            assets.supersede_ko(conn, previous["id"], vid)
                            action = "registered+superseded"
                        except ValueError as exc:  # version not greater
                            action = f"registered(no-supersede: {exc})"
                summaries.append({
                    "ko_id": ko_id,
                    "version": version,
                    "version_id": vid,
                    "sha256": info["sha256"],
                    "action": action,
                    "counts": info["counts"],
                })
        conn.commit()
        report = assets.get_quality_report(conn, stale_days=30)
        index = assets.export_asset_index_obj(conn)
        conn.commit()
        return {"registered": summaries, "report": report, "index": index}
    finally:
        conn.close()


def verify(index_path: Path, roots: list[Path], *, prefix: str) -> dict:
    """Compare pinned package digests in ``index_path`` with the live record bytes."""
    doc = json.loads(index_path.read_text(encoding="utf-8"))
    pinned = {e["asset_id"]: e for e in doc.get("entries", [])
              if e.get("asset_type") == "knowledge_object"}
    current = {}
    for root in roots:
        for pkg in find_packages(root):
            info = package_digest(pkg, root)
            current[ko_id_for(info["package"], prefix)] = info["sha256"]

    matched, missing, drifted, unpinned = [], [], [], []
    for asset_id, entry in sorted(pinned.items()):
        ko_id = entry["metadata"]["ko_id"]
        pinned_digest = entry["metadata"].get("content_sha256")
        now_digest = current.get(ko_id)
        if now_digest is None:
            missing.append(ko_id)
        elif pinned_digest is None:
            unpinned.append(ko_id)
        elif now_digest != pinned_digest:
            drifted.append({"ko_id": ko_id, "pinned": pinned_digest, "current": now_digest})
        else:
            matched.append(ko_id)
    ok = not missing and not drifted and not unpinned
    return {
        "ok": ok,
        "matched": sorted(matched),
        "missing": sorted(missing),
        "drifted": drifted,
        "unpinned": sorted(unpinned),
        "pinned_entries": len(pinned),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", action="append", default=None,
                    help="package root (repeatable, default: knowledge)")
    ap.add_argument("--db", default=":memory:", help="KE store path/DSN")
    ap.add_argument("--index", default="artifacts/asset-index.json")
    ap.add_argument("--report", default="artifacts/health-report.json")
    ap.add_argument("--created-by", default="register_assets")
    ap.add_argument("--prefix", default="tko", help="KO id namespace prefix")
    ap.add_argument("--verify", action="store_true",
                    help="recompute digests and compare with the pinned index")
    ap.add_argument("--state", default="in_review",
                    choices=["draft", "in_review", "published"],
                    help="life-cycle state a newly registered version starts in")
    ap.add_argument("--json", action="store_true", help="machine-readable result")
    args = ap.parse_args(argv)

    roots = [Path(r) for r in (args.root or ["knowledge"])]
    for root in roots:
        if not root.is_dir():
            print(f"ERROR: root not found: {root}", file=sys.stderr)
            return 2

    if args.verify:
        index_path = Path(args.index)
        if not index_path.is_file():
            print(f"ERROR: index artefact not found: {index_path} "
                  f"(run the register step first to pin digests)", file=sys.stderr)
            return 2
        result = verify(index_path, roots, prefix=args.prefix)
        print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1

    result = register(roots, args.db, created_by=args.created_by,
                      prefix=args.prefix, state=args.state)
    index_path = Path(args.index)
    report_path = Path(args.report)
    index_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    doc = result["index"]
    doc["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    index_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                          encoding="utf-8")
    report_path.write_text(json.dumps(result["report"], ensure_ascii=False, indent=2,
                                      sort_keys=True) + "\n", encoding="utf-8")

    summary = {
        "packages": len(result["registered"]),
        "actions": {a: sum(1 for r in result["registered"] if r["action"] == a)
                    for a in sorted({r["action"] for r in result["registered"]})},
        "index_entries": doc["total_entries"],
        "index_sha256": doc["index_sha256"],
        "index": str(index_path),
        "report": str(report_path),
        "health": result["report"]["summary"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())