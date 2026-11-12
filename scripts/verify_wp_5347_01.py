#!/usr/bin/env python3
"""Verifier for work package wp-5347-01 (process 01, report 5347).

Runs the acceptance checks of the owner contract *against the artefacts on
disk* and writes ``artifacts/wp-5347-01/checks.json``.  Exit code 0 iff every
check is ``passed`` (a ``vacuous`` check is reported as vacuous, never as
passed — the zero-claim case must stay visible).

Checks
------
A1 valid_json            both emitted JSON files parse
A2 schema_pass           kf_result validates against schemas/kf_result.v1.schema.json
A3 source_hash_matches   recomputed sha256(markdown bytes) == contract == manifest
A4 source_locator_resolvable  every char-span locator quote is the exact substring
                              at its recorded offsets and cites its own path token
A5 no_duplicate_ids      asset ids unique (claims: none by contract)
A6 claims_have_evidence_or_unresolved  vacuous here (0 claims) — reported as such
A7 envelope_integrity    package_id/task_type/report_id agree across envelope,
                         manifest and report; outputs == the declared file only
A8 no_self_verification  no producer-written verification/gate markers anywhere
A9 report_channel        the KF-RESULT markdown carries exactly one ```json block
                         and it is byte-identical in content to kf_result.json
A10 figure_honesty       figures registered metadata_only iff record has no bytes

Usage: python3 scripts/verify_wp_5347_01.py [--quiet]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "artifacts" / "wp-5347-01"
if not OUT.is_dir():  # committed snapshot: artifacts/** is git-ignored
    OUT = REPO / "docs" / "production" / "wp-5347-01"
SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"

PACKAGE_ID = "wp-5347-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "5347"
#: byte-for-byte from the owner contract (package_id wp-5347-01, input.source_hash)
CONTRACT_SOURCE_HASH = ("sha256:bdd7bb0e76c120366d71fe0470570563"
                        "33cf83cfef6e0a2ca1ca125082a9d2e1")
CONTRACT_CHARS = 4206
MIN_QUOTE_CHARS = 12
VERIFIED_MARKERS = ("verified", "verification_status", "verification_level",
                    "is_verified", "gate_confirmed")

JSON_BLOCK = re.compile(r"```json\s*\n(.*?)```", re.S)


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _walk_keys(node, path="") -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    if isinstance(node, dict):
        for k, v in node.items():
            out.append((path + "/" + str(k), str(k)))
            out += _walk_keys(v, path + "/" + str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += _walk_keys(v, f"{path}[{i}]")
    return out


def run_checks(out: Path = OUT) -> dict:
    checks: list[dict] = []

    def add(name: str, status: str, **evidence) -> None:
        checks.append({"check": name, "status": status, "evidence": evidence})

    src_path = out / "report_5347.md"
    meta_path = out / "report_5347.md.meta.json"
    manifest_path = out / "asset_manifest.json"
    result_path = out / "kf_result.json"
    report_path = out / f"KF-RESULT-{PACKAGE_ID}.md"
    missing = [p.name for p in (src_path, meta_path, manifest_path, result_path, report_path)
               if not p.is_file()]
    if missing:
        add("A0.files_present", "failed", missing=missing)
        return {"ok": False, "checks": checks}

    text = src_path.read_bytes().decode("utf-8")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    # ---- A1 valid_json
    parsed, errors = {}, []
    for path in (manifest_path, result_path):
        try:
            parsed[path.name] = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name}: {exc.msg} @{exc.pos}")
    add("A1.valid_json", "failed" if errors else "passed", errors=errors)
    manifest = parsed.get("asset_manifest.json") or {}
    result = parsed.get("kf_result.json") or {}

    # ---- A2 schema_pass
    try:
        import jsonschema
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        errs = sorted(validator.iter_errors(result), key=lambda e: list(e.path))
        add("A2.schema_pass",
            "passed" if not errs else "failed",
            schema=str(SCHEMA.relative_to(REPO)),
            schema_sha256=sha256_bytes(SCHEMA.read_bytes()),
            errors=[f"{'/'.join(str(p) for p in e.path)}: {e.message[:120]}"
                    for e in errs[:3]])
    except FileNotFoundError:
        add("A2.schema_pass", "not_run", reason=f"schema absent: {SCHEMA}")

    # ---- A3 source_hash_matches (three-way)
    actual = sha256_bytes(text.encode("utf-8"))
    claimed = (result.get("provenance") or {}).get("source_hash")
    in_manifest = (manifest.get("source") or {}).get("source_hash")
    add("A3.source_hash_matches",
        "passed" if actual == claimed == in_manifest == CONTRACT_SOURCE_HASH else "failed",
        contract=CONTRACT_SOURCE_HASH, recomputed=actual,
        envelope=claimed, manifest=in_manifest,
        chars={"contract": CONTRACT_CHARS, "actual": len(text),
               "manifest": (manifest.get("source") or {}).get("chars")})

    # ---- A4 source_locator_resolvable
    bad_span, bad_token, checked = [], [], 0
    for asset in manifest.get("assets") or []:
        loc = asset.get("locator") or {}
        if loc.get("locator_type") != "char_span":
            continue
        checked += 1
        start, end, quote = loc.get("start_offset"), loc.get("end_offset"), loc.get("quote", "")
        if text[start:end] != quote:
            bad_span.append({"asset_id": asset.get("asset_id"),
                             "expected": quote[:40], "got": (text[start:end] or "")[:40]})
            continue
        if quote not in text or len(quote) < MIN_QUOTE_CHARS:
            bad_span.append({"asset_id": asset.get("asset_id"), "reason": "quote not in text"})
            continue
        if asset.get("path") and asset["path"] not in quote:
            bad_token.append({"asset_id": asset.get("asset_id"), "path": asset.get("path")})
        if loc.get("quote_sha256") and loc["quote_sha256"] != sha256_bytes(quote.encode()):
            bad_span.append({"asset_id": asset.get("asset_id"), "reason": "quote hash mismatch"})
    add("A4.source_locator_resolvable",
        "failed" if (bad_span or bad_token) else "passed",
        char_span_locators=checked, span_mismatches=bad_span[:5],
        path_not_in_quote=bad_token[:5],
        min_quote_chars=MIN_QUOTE_CHARS)

    # ---- A5 no_duplicate_ids
    ids = [a.get("asset_id") for a in manifest.get("assets") or []]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    claim_ids = [c.get("claim_id") for c in result.get("claims") or []]
    claim_dupes = sorted({i for i in claim_ids if claim_ids.count(i) > 1})
    add("A5.no_duplicate_ids",
        "passed" if not dupes and not claim_dupes and all(ids) else "failed",
        n_assets=len(ids), duplicate_assets=dupes[:5], n_claims=len(claim_ids),
        duplicate_claims=claim_dupes[:5])

    # ---- A6 claims_have_evidence_or_unresolved (vacuous when no claims)
    claims = result.get("claims") or []
    offenders = [c.get("claim_id") for c in claims
                 if not (c.get("evidence") or []) and not (
                     c.get("status") == "unresolved" and str(c.get("unresolved_reason", "")).strip())]
    if not claims:
        add("A6.claims_have_evidence_or_unresolved", "vacuous",
            reason="process 01 extracts no claims (objective.register_assets only); "
                   "empty claim set is contract-legal, so this acceptance line is "
                   "vacuously satisfied — NOT evidence that anything was verified",
            n_claims=0)
    else:
        add("A6.claims_have_evidence_or_unresolved",
            "failed" if offenders else "passed", offenders=offenders[:5], n_claims=len(claims))

    # ---- A7 envelope_integrity
    problems = []
    if result.get("package_id") != PACKAGE_ID:
        problems.append(f"package_id={result.get('package_id')!r}")
    if str(result.get("task_type", "")).split("-")[0] != TASK_TYPE.split("-")[0]:
        problems.append(f"task_type={result.get('task_type')!r}")
    if str(result.get("report_id")) != REPORT_ID:
        problems.append(f"report_id={result.get('report_id')!r}")
    if manifest.get("package_id") != PACKAGE_ID or str(manifest.get("report_id")) != REPORT_ID:
        problems.append("manifest identity mismatch")
    if list((result.get("outputs") or {}).keys()) != ["asset_manifest.json"]:
        problems.append(f"outputs keys={(result.get('outputs') or {}).keys()}")
    if (result.get("outputs") or {}).get("asset_manifest.json") != manifest:
        problems.append("embedded manifest != asset_manifest.json on disk")
    if (result.get("provenance") or {}).get("source_field") != "markdown":
        problems.append("source_field != markdown")
    add("A7.envelope_integrity", "failed" if problems else "passed", problems=problems)

    # ---- A8 no_self_verification
    hits = [(p, k) for p, k in _walk_keys(result)
            if k in VERIFIED_MARKERS or k.lower() in VERIFIED_MARKERS]
    add("A8.no_self_verification", "failed" if hits else "passed", offenders=hits[:5])

    # ---- A9 report_channel
    md = report_path.read_text(encoding="utf-8")
    blocks = JSON_BLOCK.findall(md)
    issues = []
    if len(blocks) != 1:
        issues.append(f"json_blocks={len(blocks)}")
    else:
        try:
            if json.loads(blocks[0]) != result:
                issues.append("payload != kf_result.json")
        except json.JSONDecodeError as exc:
            issues.append(f"payload decode: {exc.msg}")
    if not md.lstrip().startswith(f"# KF-RESULT {PACKAGE_ID}"):
        issues.append("title line is not '# KF-RESULT wp-5347-01'")
    add("A9.report_channel", "failed" if issues else "passed",
        json_blocks=len(blocks), issues=issues,
        report=report_path.name, chars=len(md))

    # ---- A10 figure_honesty
    figs = meta.get("figures") or []
    have_bytes = [f.get("name") for f in figs if f.get("png_base64")]
    fig_assets = [a for a in manifest.get("assets") or [] if a.get("kind") == "figure"]
    bad = []
    if have_bytes:
        bad.append(f"record now carries bytes for {have_bytes}: metadata_only is stale")
    if len(fig_assets) != len(figs):
        bad.append(f"figure assets {len(fig_assets)} != record figures {len(figs)}")
    add("A10.figure_honesty", "failed" if bad else "passed",
        record_figures=len(figs), metadata_only=len(fig_assets), problems=bad)

    ok = all(c["status"] in ("passed", "vacuous") for c in checks)
    return {"ok": ok, "checks": checks,
            "counts": {"passed": sum(c["status"] == "passed" for c in checks),
                       "vacuous": sum(c["status"] == "vacuous" for c in checks),
                       "failed": sum(c["status"] == "failed" for c in checks),
                       "not_run": sum(c["status"] == "not_run" for c in checks)}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="verify wp-5347-01 artefacts")
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--dir", default=str(OUT), help="package directory to verify")
    args = ap.parse_args(argv)
    report = run_checks(Path(args.dir))
    (Path(args.dir) / "checks.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.quiet:
        print(json.dumps(report["counts"], ensure_ascii=False))
        for c in report["checks"]:
            print(f"  {c['status']:8s} {c['check']}")
            if c["status"] == "failed":
                print("           ", json.dumps(c["evidence"], ensure_ascii=False)[:300])
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())