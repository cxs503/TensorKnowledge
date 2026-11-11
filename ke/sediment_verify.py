#!/usr/bin/env python3
"""Verify a generated sediment package against its source pin and its own spec.

Each check is machine-evaluable and independent of the producer's claims about
itself.  A verifier that only re-reads the JSON it is given would prove nothing,
so the load-bearing checks re-open the pinned git blobs (quotes, offsets,
content hashes) and recompute the benchmark table from the source artifacts.

Checks
------
V1 package-present      claims / evidence / provenance / benchmarks.json / INDEX.md
V2 schema               every record validates against schemas/*.schema.json
V3 cross-reference      claim<->evidence links complete in both directions,
                        one provenance record per claim with matching task_key
V4 quote-at-pin         `quote == blob[start:end]`, quote occurs exactly once,
                        locator.content_hash == sha256(blob)
V5 producer-contract    claims draft, evidence unassessed, no review event written
V6 index-consistency    every claim/benchmark/evidence id and the pinned sha in INDEX.md
V7 benchmark-rederive    stored ref/got/rel_error reproduce from the source JSON
V8 run-artifacts        run manifest lists the package files with matching sha256

Exit codes: 0 all executed checks pass, 1 a check failed, 3 source checkout (or
pinned commit) unavailable so the source-dependent checks were NOT run.

Usage::

    python3 -m ke.sediment_verify --package knowledge/sediment/tk-sediment-m5054 \
        --spec knowledge/sediment/tk-sediment-m5054/spec.json \
        --source-repo /root/tensor-ecosystem/TensorSPH \
        --run-dir docs/sediment/tk-sediment-m5054/runs/extract \
        --report docs/sediment/tk-sediment-m5054/runs/validate/validate_report.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from ke.sediment_extract import (GitPin, SourceUnavailable, build_benchmarks,
                                 QuoteNotFound)

ROOT = Path(__file__).resolve().parents[1]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


class Report:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, check: str, ok: bool | None, detail: str = "") -> None:
        status = "SKIP" if ok is None else ("PASS" if ok else "FAIL")
        self.rows.append({"check": check, "status": status, "detail": detail})
        print(f"{status} {check}{(' :: ' + detail) if detail else ''}")

    @property
    def failed(self) -> list[dict]:
        return [r for r in self.rows if r["status"] == "FAIL"]

    @property
    def skipped(self) -> list[dict]:
        return [r for r in self.rows if r["status"] == "SKIP"]

    @property
    def passed(self) -> list[dict]:
        return [r for r in self.rows if r["status"] == "PASS"]


def verify(package: Path, spec_path: Path, schemas: Path, source_repo: str | None,
           run_dir: Path | None) -> Report:
    rep = Report()
    spec = load(spec_path)
    pkg = Path(package)

    claims = sorted((pkg / "claims").glob("*.json")) if (pkg / "claims").is_dir() else []
    evidence = sorted((pkg / "evidence").glob("*.json")) if (pkg / "evidence").is_dir() else []
    prov = sorted((pkg / "provenance").glob("*.json")) if (pkg / "provenance").is_dir() else []
    bench_path = pkg / "benchmarks.json"
    index_path = pkg / "INDEX.md"

    # ---- V1 ---------------------------------------------------------------- #
    present = bool(claims and evidence and prov and bench_path.is_file()
                   and index_path.is_file())
    rep.add("V1 package-present", present,
            f"claims={len(claims)} evidence={len(evidence)} provenance={len(prov)} "
            f"benchmarks={bench_path.is_file()} index={index_path.is_file()}")
    if not present:
        return rep

    claim_recs = [load(p) for p in claims]
    ev_recs = [load(p) for p in evidence]
    prov_recs = [load(p) for p in prov]

    # ---- V2 ---------------------------------------------------------------- #
    try:
        from jsonschema import Draft202012Validator
    except ImportError:  # pragma: no cover
        rep.add("V2 schema", None, "jsonschema not installed")
    else:
        for name, recs in (("claim-record", claim_recs),
                           ("evidence-record", ev_recs),
                           ("provenance-record", prov_recs)):
            validator = Draft202012Validator(load(schemas / f"{name}.schema.json"))
            bad = []
            for rec in recs:
                errors = sorted(validator.iter_errors(rec),
                                key=lambda e: list(e.absolute_path))
                if errors:
                    bad.append(f"{rec.get('id')}: "
                               f"{errors[0].message.splitlines()[0][:160]}")
            rep.add(f"V2 schema:{name}", not bad,
                    f"{len(recs)} records" + (f"; {len(bad)} invalid: {bad[:3]}" if bad else ""))

    # ---- V3 ---------------------------------------------------------------- #
    claim_ids = {c["id"] for c in claim_recs}
    ev_ids = {e["id"] for e in ev_recs}
    problems = []
    for claim in claim_recs:
        for ref in claim.get("evidence_refs", []):
            if ref not in ev_ids:
                problems.append(f"{claim['id']} references missing {ref}")
    seen_pairs = set()
    for ev in ev_recs:
        for ref in ev.get("claim_refs", []):
            if ref not in claim_ids:
                problems.append(f"{ev['id']} references missing {ref}")
            seen_pairs.add((ref, ev["id"]))
    for claim in claim_recs:
        for ref in claim.get("evidence_refs", []):
            if (claim["id"], ref) not in seen_pairs:
                problems.append(f"{ref} does not point back at {claim['id']}")
    prov_claims = {p["generated_entity"]["id"]: p for p in prov_recs}
    for cid in sorted(claim_ids):
        if cid not in prov_claims:
            problems.append(f"no provenance record for {cid}")
    for pid, prov_rec in prov_claims.items():
        if pid not in claim_ids:
            problems.append(f"provenance {prov_rec['id']} generated unknown claim {pid}")
        params = prov_rec["activity"].get("parameters", {})
        if params.get("task_key") != spec["task_key"]:
            problems.append(f"{prov_rec['id']} task_key {params.get('task_key')!r} "
                            f"!= {spec['task_key']!r}")
    rep.add("V3 cross-reference", not problems,
            f"{len(seen_pairs)} claim-evidence links, {len(prov_recs)} provenance"
            + (f"; {problems[:4]}" if problems else ""))

    # ---- V5 (independent of the source repo) -------------------------------- #
    leaks = []
    for claim in claim_recs:
        if claim.get("epistemic_status") != "draft":
            leaks.append(f"{claim['id']} status={claim.get('epistemic_status')}")
    for ev in ev_recs:
        if ev.get("assessment_status") != "unassessed":
            leaks.append(f"{ev['id']} assessment={ev.get('assessment_status')}")
    review_files = [str(p.relative_to(pkg)) for p in pkg.rglob("*review*")]
    if review_files:
        leaks.append(f"review artefacts present: {review_files}")
    rep.add("V5 producer-contract", not leaks,
            f"claims draft + evidence unassessed, {len(ev_recs)} records"
            + (f"; {leaks[:4]}" if leaks else ""))

    # ---- V6 ---------------------------------------------------------------- #
    index_text = index_path.read_text(encoding="utf-8")
    bench = load(bench_path)
    missing = [cid for cid in sorted(claim_ids) if cid not in index_text]
    missing += [e["id"] for e in ev_recs if e["id"] not in index_text]
    missing += [r["id"] for r in bench["rows"] if r["id"] not in index_text]
    if spec["source"]["sha"] not in index_text:
        missing.append(spec["source"]["sha"])
    if spec["task_key"] not in index_text:
        missing.append(spec["task_key"])
    rep.add("V6 index-consistency", not missing,
            f"{len(claim_ids) + len(ev_recs) + len(bench['rows'])} identifiers"
            + (f"; missing {missing[:4]}" if missing else ""))

    # ---- V4 + V7: need the pinned commit ------------------------------------ #
    repo = source_repo or spec["source"].get("default_path")
    try:
        pin = GitPin(repo, spec["source"]["sha"])
    except (SourceUnavailable, TypeError) as exc:
        rep.add("V4 quote-at-pin", None, f"source checkout unavailable ({exc})")
        rep.add("V7 benchmark-rederive", None, "needs the pinned commit")
        return rep

    quote_problems = []
    for ev in ev_recs:
        value = ev["locator"]["value"]
        path = value.split("#")[0].split(":")[-1]
        try:
            text = pin.blob(path)
        except SourceUnavailable as exc:
            quote_problems.append(f"{ev['id']}: {exc}")
            continue
        quote = ev["locator"]["quote"]
        start, end = ev["locator"]["start_offset"], ev["locator"]["end_offset"]
        if text[start:end] != quote:
            quote_problems.append(f"{ev['id']}: blob[start:end] != quote")
        if text.count(quote) != 1:
            quote_problems.append(f"{ev['id']}: quote not unique")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != ev["locator"]["content_hash"]:
            quote_problems.append(f"{ev['id']}: content_hash mismatch")
    rep.add("V4 quote-at-pin", not quote_problems,
            f"{len(ev_recs)} quotes at {pin.short}" + (f"; {quote_problems[:4]}" if quote_problems else ""))

    # ---- V7 ---------------------------------------------------------------- #
    rederived = build_benchmarks(spec, pin)
    drift = []
    for stored, fresh in zip(bench["rows"], rederived["rows"]):
        for key in ("ref", "got", "rel_error"):
            a, b = stored.get(key), fresh.get(key)
            if a is None or b is None:
                if a != b:
                    drift.append(f"{stored['id']}.{key}: stored {a!r} != fresh {b!r}")
                continue
            if abs(a - b) > 1e-12 * max(1.0, abs(a), abs(b)):
                drift.append(f"{stored['id']}.{key}: stored {a!r} != fresh {b!r}")
        for key in ("id", "ref_expr", "source"):
            if stored[key] != fresh[key]:
                drift.append(f"{stored['id']}.{key}: stored {stored[key]!r} != fresh {fresh[key]!r}")
    if len(bench["rows"]) != len(rederived["rows"]):
        drift.append(f"row count {len(bench['rows'])} != {len(rederived['rows'])}")
    rep.add("V7 benchmark-rederive", not drift,
            f"{len(rederived['rows'])} rows recomputed from {len(rederived['rows'])} source "
            f"artifacts" + (f"; {drift[:4]}" if drift else ""))

    # ---- V8 ---------------------------------------------------------------- #
    manifest_path = (Path(run_dir) if run_dir else Path(spec["package"]["run_dir"])) / "run_manifest.json"
    if not manifest_path.is_file():
        rep.add("V8 run-artifacts", False, f"missing {manifest_path}")
    else:
        manifest = load(manifest_path)
        bad = []
        for entry in manifest.get("files", []):
            path = Path(entry["path"])
            if not path.is_file():
                bad.append(f"missing {path}")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != entry["sha256"]:
                bad.append(f"{path.name} sha256 drift")
        if manifest.get("spec_sha256") != hashlib.sha256(spec_path.read_bytes()).hexdigest():
            bad.append("manifest spec_sha256 != spec on disk (spec changed after build)")
        if manifest.get("source", {}).get("sha") != spec["source"]["sha"]:
            bad.append("manifest source sha mismatch")
        rep.add("V8 run-artifacts", not bad,
                f"{len(manifest.get('files', []))} files attested"
                + (f"; {bad[:4]}" if bad else ""))
    return rep


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--package", default="knowledge/sediment/tk-sediment-m5054")
    parser.add_argument("--spec", default="knowledge/sediment/tk-sediment-m5054/spec.json")
    parser.add_argument("--schemas", default="schemas")
    parser.add_argument("--source-repo", default=None)
    parser.add_argument("--run-dir", default=None)
    parser.add_argument("--report", default=None, help="write the JSON report here")
    args = parser.parse_args(argv)

    package = Path(args.package)
    if not package.is_absolute():
        package = ROOT / package
    spec_path = Path(args.spec)
    if not spec_path.is_absolute():
        spec_path = ROOT / spec_path
    schemas = Path(args.schemas)
    if not schemas.is_absolute():
        schemas = ROOT / schemas
    run_dir = Path(args.run_dir) if args.run_dir else None
    if run_dir is not None and not run_dir.is_absolute():
        run_dir = ROOT / run_dir

    rep = verify(package, spec_path, schemas, args.source_repo, run_dir)
    payload = {
        "package": str(package),
        "spec": str(spec_path),
        "source_sha": json.loads(spec_path.read_text(encoding="utf-8"))["source"]["sha"],
        "checks": rep.rows,
        "passed": len(rep.passed),
        "failed": len(rep.failed),
        "skipped": len(rep.skipped),
    }
    if args.report:
        report = Path(args.report)
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
        print(f"report: {report}")

    if rep.failed:
        print(f"{len(rep.failed)} checks FAILED, {len(rep.passed)} passed, "
              f"{len(rep.skipped)} skipped")
        return 1
    if rep.skipped:
        print(f"checks passed ({len(rep.passed)}) with {len(rep.skipped)} skipped "
              f"(source-dependent checks NOT run)")
        return 3
    print(f"checks passed ({len(rep.passed)})")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())