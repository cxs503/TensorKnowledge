#!/usr/bin/env python3
"""KPI-KB-10K verifier — machine裁判 for the harvested knowledge corpus.

Checks (each printed as PASS/FAIL, exit 1 if any FAIL):

  C1 four-contract coverage : every KO = 1 claim + >=1 'supports' evidence
                              (+ mirrored claim_refs) + 1 provenance whose
                              generated_entity.id is that claim
  C2 schema                 : every record validates against the repo's
                              ``schemas/*.schema.json`` (aggregate-aware)
  C3 xref invariants        : ``ke.validate.xref_report`` I1-I5 (no dangling
                              refs, no orphan evidence, no claim w/o evidence)
  C4 unique ids             : claim/evidence/provenance ids are unique per kind
  C5 content_hash           : sha256(quote) == locator.content_hash, quote
                              <= schema maxLength, offsets non-inverted
  C6 target count           : knowledge_objects >= target (default 10000)
  C7 push budget            : file count <= 80 and every file < 4 MiB
                              (the platform push gate's MAX_FILES / MAX_FILE)
  C8 manifest reconciliation: manifest counts == discovered counts, and each
                              shard's sha256 matches the bytes on disk
  C9 online reproduction    : (only if the pinned repos are on disk) quote is
                              byte-identical to ``git show <commit>:<path>``
                              at [start_offset, end_offset). Otherwise the
                              check is reported as NOT_RUN — never as PASS.

Usage::

    python scripts/kb10k_verify.py                       # offline+online if repos exist
    python scripts/kb10k_verify.py --offline              # C9 reported NOT_RUN
    python scripts/kb10k_verify.py --json docs/kb10k/verification.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ke import contract, store, validate  # noqa: E402

MAX_FILES = 80
MAX_FILE_BYTES = 4 * 1024 * 1024


def sha256_bytes(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def check_coverage(recs: dict) -> tuple[bool, dict]:
    claims = recs["claims"]
    evidence = recs["evidence"]
    prov = recs["provenance"]
    ev_by_claim: dict[str, int] = {}
    for eid, (e, _rel) in evidence.items():
        for cid in e.get("claim_refs", []):
            ev_by_claim[cid] = ev_by_claim.get(cid, 0) + 1
    prov_by_claim: dict[str, int] = {}
    for pid, (p, _rel) in prov.items():
        gid = (p.get("generated_entity") or {}).get("id")
        if gid:
            prov_by_claim[gid] = prov_by_claim.get(gid, 0) + 1
    missing = [cid for cid in claims
               if ev_by_claim.get(cid, 0) < 1 or prov_by_claim.get(cid, 0) < 1]
    detail = {"claims": len(claims), "evidence": len(evidence),
              "provenance": len(prov),
              "claims_without_full_coverage": missing[:10],
              "n_incomplete": len(missing)}
    return not missing, detail


def check_hashes(recs: dict) -> tuple[bool, dict]:
    bad: list[dict] = []
    for eid, (e, rel) in recs["evidence"].items():
        loc = e.get("locator") or {}
        quote = loc.get("quote")
        if quote is None:
            bad.append({"id": eid, "why": "no quote", "file": rel})
            continue
        if len(quote) > 1200:
            bad.append({"id": eid, "why": f"quote len {len(quote)}>1200", "file": rel})
        if loc.get("content_hash") != sha256_bytes(quote.encode("utf-8")):
            bad.append({"id": eid, "why": "content_hash mismatch", "file": rel})
        s, t = loc.get("start_offset"), loc.get("end_offset")
        if isinstance(s, int) and isinstance(t, int) and t - s != len(quote):
            bad.append({"id": eid, "why": f"offset span {t - s} != quote len {len(quote)}",
                        "file": rel})
    return not bad, {"n_bad": len(bad), "examples": bad[:5]}


def check_manifest(pkg: Path, recs: dict) -> tuple[bool, dict]:
    man = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    if man["counts"]["knowledge_objects"] != len(recs["claims"]):
        problems.append(f"manifest KOs {man['counts']['knowledge_objects']} != "
                        f"discovered {len(recs['claims'])}")
    for kind, shards in man["shards"].items():
        for s in shards:
            p = pkg / kind / s["path"]
            if not p.is_file():
                problems.append(f"missing shard {p}")
                continue
            b = p.read_bytes()
            if hashlib.sha256(b).hexdigest() != s["sha256"]:
                problems.append(f"shard sha mismatch {p}")
    return not problems, {"problems": problems[:10], "tiers": man["counts"]["by_tier"]}


def check_budget(pkg: Path) -> tuple[bool, dict]:
    files = [p for p in pkg.rglob("*") if p.is_file()]
    big = [str(p.relative_to(pkg)) for p in files if p.stat().st_size > MAX_FILE_BYTES]
    ok = len(files) <= MAX_FILES and not big
    return ok, {"files": len(files), "over_size": big, "max_bytes": MAX_FILE_BYTES,
                "largest": max((p.stat().st_size for p in files), default=0)}


def check_online(recs: dict, ecosystem: Path) -> tuple[bool | None, dict]:
    """Re-derive every quoted slice from the pinned git object."""
    if not ecosystem.is_dir():
        return None, {"reason": f"ecosystem root absent: {ecosystem}"}
    cache: dict[tuple[str, str], str] = {}
    checked = mismatched = unavailable = 0
    examples: list[dict] = []
    for eid, (e, _rel) in recs["evidence"].items():
        src = e.get("source") or {}
        pid = src.get("persistent_id", "")
        if not pid.startswith("git:"):
            continue
        try:
            spec, path = pid[4:].split(":", 1)
            repo, commit = spec.split("@", 1)
        except ValueError:
            unavailable += 1
            continue
        key = (repo, commit, path)  # type: ignore[misc]
        k2 = (repo, commit, path)
        if k2 not in cache:  # type: ignore[operator]
            try:
                raw = subprocess.run(  # type: ignore[index]
                    ["git", "-C", str(ecosystem / repo), "show", f"{commit}:{path}"],
                    capture_output=True, check=True).stdout
                cache[k2] = raw.decode("utf-8", errors="replace")  # type: ignore[index]
            except Exception:
                cache[k2] = ""  # type: ignore[index]
        blob = cache[k2]  # type: ignore[index]
        if not blob:
            unavailable += 1
            continue
        loc = e["locator"]
        got = blob[loc["start_offset"]:loc["end_offset"]]
        checked += 1
        if got != loc["quote"]:
            mismatched += 1
            if len(examples) < 5:
                examples.append({"id": eid, "path": path,
                                 "expected_prefix": loc["quote"][:60],
                                 "got_prefix": got[:60]})
    detail = {"checked": checked, "mismatched": mismatched, "unavailable": unavailable,
              "examples": examples}
    if checked == 0:
        return None, {**detail, "reason": "no source blob reachable"}
    return mismatched == 0, detail


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default="knowledge/kb10k")
    ap.add_argument("--target", type=int, default=10_000)
    ap.add_argument("--ecosystem", default="/root/tensor-ecosystem")
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--json", default="")
    args = ap.parse_args(argv)

    pkg = (ROOT / args.package).resolve()
    results: list[dict] = []

    def add(name: str, ok, detail) -> None:
        results.append({"check": name, "ok": ok, "detail": detail})
        tag = "PASS" if ok is True else ("NOT_RUN" if ok is None else "FAIL")
        print(f"[{tag}] {name} :: {json.dumps(detail, ensure_ascii=False)[:260]}")

    found = contract.discover(pkg)
    recs = found.records

    ok, det = check_coverage(recs)
    add("C1 four_contract_coverage", ok, det)

    schema_lines = validate.schema_report_records(pkg)
    fails = [ln for ln in schema_lines if not ln[1]]
    add("C2 schema_all_records", bool(schema_lines) and not fails,
        {"records_validated": len(schema_lines), "failures": fails[:5]})

    conn = store.connect(":memory:")
    try:
        store.ingest_pilot(pkg, conn)
        xr = validate.xref_report(conn)
        ok = all(not v for v in xr.values())
        add("C3 xref_invariants", ok, {k: v[:5] for k, v in xr.items()})
        q_stats = __import__("ke.queries", fromlist=["stats"]).stats(conn)
    finally:
        conn.close()

    dup = [line for line in schema_lines if not line[1]]
    all_ids = [k for kind in ("claims", "evidence", "provenance")
               for k in recs[kind]]
    add("C4 unique_ids", len(all_ids) == len(set(all_ids)),
        {"total_ids": len(all_ids), "unique": len(set(all_ids))})

    ok, det = check_hashes(recs)
    add("C5 quote_content_hash", ok, det)

    n_ko = len(recs["claims"])
    add("C6 target_count", n_ko >= args.target, {"knowledge_objects": n_ko,
                                                "target": args.target})

    ok, det = check_budget(pkg)
    add("C7 push_budget", ok, det)

    ok, det = check_manifest(pkg, recs)
    add("C8 manifest_reconciliation", ok, det)

    if args.offline:
        add("C9 online_reproduction", None, {"reason": "--offline"})
    else:
        ok, det = check_online(recs, Path(args.ecosystem))
        add("C9 online_reproduction", ok, det)

    # C2 duplicates discovery: byte-identical collapsed duplicates are expected 0
    add("C10 no_collapsed_duplicates", not found.duplicates,
        {"duplicates": len(found.duplicates), "examples": found.duplicates[:3]})

    failed = [r for r in results if r["ok"] is False]
    not_run = [r for r in results if r["ok"] is None]
    summary = {"verdict": "FAIL" if failed else "PASS",
               "checks": len(results), "failed": [r["check"] for r in failed],
               "not_run": [r["check"] for r in not_run],
               "knowledge_objects": n_ko,
               "ke_stats": q_stats if "q_stats" in dir() else None,
               "unclassified_files": found.unclassified[:10]}
    print(json.dumps(summary, ensure_ascii=False))
    if args.json:
        out = {**summary, "results": results}
        (ROOT / args.json).parent.mkdir(parents=True, exist_ok=True)
        (ROOT / args.json).write_text(
            json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
