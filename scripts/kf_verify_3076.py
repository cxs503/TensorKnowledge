#!/usr/bin/env python3
"""Independent verification of the wp-3076-01 asset registration.

Nothing is taken from the generator: the report is re-fetched from the platform (online mode), the
hash is recomputed, every locator quote is re-sliced out of the fresh markdown, both JSON documents
are validated against their (locally pinned) schema, and the work-package acceptance items become a
machine table. Offline mode (`offline=True`) is used by the negative-control tests: it verifies the
pinned source.md instead of re-fetching and marks the network-only checks NOT_RUN instead of PASS.

Exit code 0 only if every executed acceptance item passes (NOT_RUN is tolerated only offline).
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

import kf_fetch_3076 as fetch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wp-3076-01"
CONTRACT_HASH = "9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1"
CONTRACT_CHARS = 3712
ALLOWED_CLAIM_STATUS = {"supported", "partially-supported", "unresolved", "refuted"}
PLATFORM_FIGURE_IDS = {"A17", "A18", "A19"}


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def probe_figure(name: str, token: str) -> dict:
    url = fetch.api_base() + f"/tensor/reports/{fetch.REPORT_ID}/figures/{name}"
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read()
            return {"name": name, "http_status": resp.status, "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest()}
    except urllib.error.HTTPError as exc:
        return {"name": name, "http_status": exc.code, "body": exc.read().decode("utf-8", "replace")[:120]}
    except Exception as exc:  # network/other
        return {"name": name, "http_status": None, "error": f"{type(exc).__name__}: {exc}"[:160]}


def check_locators(source: str, assets: list[dict]) -> list[str]:
    """Every locator must slice back to its own quote, occur exactly once, and carry correct lines."""
    errors: list[str] = []
    for asset in assets:
        loc = asset.get("locator", {})
        quote, start, end = loc.get("quote"), loc.get("start_char"), loc.get("end_char")
        if not isinstance(quote, str) or not quote:
            errors.append(f"{asset.get('asset_id')}: missing quote")
            continue
        if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(source)):
            errors.append(f"{asset.get('asset_id')}: span {start}:{end} out of range")
            continue
        sliced = source[start:end]
        if loc.get("method") == "document":
            if not sliced.startswith(quote):
                errors.append(f"{asset.get('asset_id')}: document span does not start with the quote")
        elif sliced != quote:
            errors.append(f"{asset.get('asset_id')}: source[{start}:{end}] != quote")
        if source.count(quote) != 1 or not loc.get("unique"):
            errors.append(f"{asset.get('asset_id')}: quote occurs {source.count(quote)}x (unique={loc.get('unique')})")
        exp_start_line = source.count("\n", 0, start) + 1
        exp_end_line = source.count("\n", 0, max(end - 1, start)) + 1
        if (loc.get("start_line"), loc.get("end_line")) != (exp_start_line, exp_end_line):
            errors.append(
                f"{asset.get('asset_id')}: line span {loc.get('start_line')}-{loc.get('end_line')} "
                f"!= recomputed {exp_start_line}-{exp_end_line}"
            )
        if asset.get("asset_id") == "A01" and (start, end) != (0, len(source)):
            errors.append("A01: document locator does not cover the whole markdown")
    return errors


def check_unique_ids(manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    ids = [a.get("asset_id") for a in manifest.get("assets", [])]
    if len(ids) != len(set(ids)):
        errors.append(f"duplicate asset_id in {len(ids) - len(set(ids))} place(s)")
    spans = [(a["locator"]["start_char"], a["locator"]["end_char"]) for a in manifest.get("assets", []) if "locator" in a]
    if len(spans) != len(set(spans)):
        errors.append(f"{len(spans) - len(set(spans))} asset(s) share an identical locator span")
    claim_ids = [c.get("claim_id") for c in manifest.get("claims", []) + envelope.get("claims", [])]
    claim_ids = [c for c in claim_ids if c is not None]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("duplicate claim_id")
    return errors


def check_claim_policy(manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    for claim in manifest.get("claims", []) + envelope.get("claims", []):
        if claim.get("status") not in ALLOWED_CLAIM_STATUS and not claim.get("evidence"):
            errors.append(f"{claim.get('claim_id')}: neither a legal status nor evidence")
        if claim.get("status") == "verified":
            errors.append(f"{claim.get('claim_id')}: 'verified' is not a legal status for this lane")
    for asset in manifest.get("assets", []):
        payload = asset.get("payload", {})
        if not payload.get("status") or len(payload.get("checked_how", "")) < 10:
            errors.append(f"{asset.get('asset_id')}: payload status/checked_how missing")
        if asset.get("asset_id") in PLATFORM_FIGURE_IDS and payload.get("status") != "declared_payload_missing":
            errors.append(f"{asset.get('asset_id')}: platform figure payload must stay unresolved (no bytes in record)")
    return errors


def check_boundaries(manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    if envelope.get("report_id") != "3076" or manifest.get("report_id") != "3076":
        errors.append("report_id is not 3076")
    bounds = manifest.get("boundaries", {})
    if bounds.get("other_reports_read") is not False:
        errors.append("boundary flag other_reports_read is not false")
    if bounds.get("upstream_artifacts_rewritten") is not False:
        errors.append("boundary flag upstream_artifacts_rewritten is not false")
    if bounds.get("claims_marked_verified") != 0:
        errors.append("claims_marked_verified is not 0")
    blob = json.dumps([manifest, envelope], ensure_ascii=False)
    for bad in ('"status": "verified"', '"verified": true', '"verification_status": "verified"'):
        if bad in blob:
            errors.append(f"forbidden self-verification marker {bad}")
    return errors


def check_sources(out_dir: Path, source: str, manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    digest = sha256_hex(source)
    if digest != CONTRACT_HASH:
        errors.append(f"source sha256 {digest} != contract {CONTRACT_HASH}")
    if manifest.get("source", {}).get("hash") != CONTRACT_HASH:
        errors.append("manifest.source.hash != contract hash")
    prov = envelope.get("provenance", {}).get("source_hash", "")
    if prov != "sha256:" + CONTRACT_HASH:
        errors.append("envelope.provenance.source_hash != contract hash")
    if len(source) != CONTRACT_CHARS or manifest.get("source", {}).get("chars") != CONTRACT_CHARS:
        errors.append(f"chars {len(source)} != contract {CONTRACT_CHARS}")
    pinned_path = out_dir / "source.md"
    if pinned_path.exists() and sha256_hex(pinned_path.read_text(encoding="utf-8")) != digest:
        errors.append("pinned source.md diverges from the source under verification")
    return errors


def check_record_metadata(manifest: dict, record: dict | None) -> list[str]:
    if record is None:
        return []
    errors: list[str] = []
    if manifest.get("source", {}).get("title") != record.get("title"):
        errors.append("title differs from the live record")
    if manifest.get("source", {}).get("scenario_key") != record.get("scenario_key"):
        errors.append("scenario_key differs from the live record")
    if [f.get("name") for f in manifest.get("source", {}).get("platform_figures", [])] != [
        f.get("name") for f in record.get("figures", [])
    ]:
        errors.append("figure names differ from the live record")
    return errors


def check_schemas(out_dir: Path, manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    for doc, schema_path in [
        (envelope, out_dir / "kf_result.v1.schema.json"),
        (manifest, out_dir / "asset_manifest.v1.schema.json"),
    ]:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
            errors.append(f"{schema_path.name}: {'/'.join(map(str, err.path))}: {err.message}")
    return errors


def run_checks(out_dir: Path = OUT, online: bool = True) -> dict:
    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    envelope = json.loads((out_dir / "kf_result.wp-3076-01.json").read_text(encoding="utf-8"))
    pinned = (out_dir / "source.md").read_text(encoding="utf-8")
    meta_path = out_dir / "source_meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}

    record: dict | None = None
    source = pinned
    if online:
        source, record = fetch.fetch_markdown()

    checks: list[dict] = []

    def add(item: str, result: str, detail) -> None:
        checks.append({"acceptance_item": item, "result": result, "detail": detail})

    src_errors = check_sources(out_dir, source, manifest, envelope)
    add("source_hash_matches", "PASS" if not src_errors else "FAIL",
        {"sha256": sha256_hex(source), "contract": CONTRACT_HASH, "errors": src_errors})
    add("chars_match_contract", "PASS" if len(source) == CONTRACT_CHARS == manifest["source"]["chars"] else "FAIL",
        {"chars": len(source), "bytes_utf8": len(source.encode("utf-8"))})
    add("valid_json", "PASS", {"files": ["asset_manifest.json", "kf_result.wp-3076-01.json"], "parse": "ok"})

    schema_errors = check_schemas(out_dir, manifest, envelope)
    add("schema_pass", "PASS" if not schema_errors else "FAIL",
        {"errors": schema_errors, "documents": 2,
         "schemas": ["kf_result.v1.schema.json (restored from commit 53c59cc)", "asset_manifest.v1.schema.json"]})

    loc_errors = check_locators(source, manifest["assets"])
    add("source_locator_resolvable", "PASS" if not loc_errors else "FAIL",
        {"assets_checked": len(manifest["assets"]), "errors": loc_errors})

    dup_errors = check_unique_ids(manifest, envelope)
    add("no_duplicate_ids", "PASS" if not dup_errors else "FAIL", {"errors": dup_errors})

    claim_errors = check_claim_policy(manifest, envelope)
    add("all_claims_have_evidence_or_explicit_unresolved_status", "PASS" if not claim_errors else "FAIL",
        {"claims": len(manifest.get("claims", [])) + len(envelope.get("claims", [])),
         "asset_payload_statuses": manifest["counts"]["by_payload_status"], "errors": claim_errors})

    boundary_errors = check_boundaries(manifest, envelope)
    add("boundaries_and_no_self_verified", "PASS" if not boundary_errors else "FAIL", {"errors": boundary_errors})

    meta_errors = check_record_metadata(manifest, record if record is not None else meta.get("record"))
    add("record_metadata_verbatim", "PASS" if not meta_errors else "FAIL",
        {"source": "live platform record" if record is not None else "pinned source_meta.json",
         "errors": meta_errors})

    if online:
        token = fetch.login()
        probes = [probe_figure(f["name"], token) for f in manifest["source"]["platform_figures"]]
        missing = all(p.get("http_status") == 404 for p in probes)
        add("platform_figure_payload_status_current", "PASS" if missing else "FAIL",
            {"probes": probes,
             "note": "404 for all three figures ⇒ 'declared_payload_missing' is current; if any turns 200 the manifest must be re-registered"})
    else:
        add("platform_figure_payload_status_current", "NOT_RUN",
            {"reason": "offline mode: figure payload endpoint not probed, so no PASS is claimed"})

    # positive control for the figure-payload route: after this package's own report is published,
    # the same endpoint must answer 200 for its figures -> proves 3076's 404 is absent bytes, not a bad route.
    roundtrip = out_dir / "publish_roundtrip.json"
    if roundtrip.exists():
        rt = json.loads(roundtrip.read_text(encoding="utf-8"))
        pc = rt.get("figure_endpoint_positive_control", {})
        add("figure_endpoint_positive_control", "PASS" if pc.get("http_status") == 200 else "FAIL",
            {"probe": pc,
             "implies": "endpoint behaviour is known-good, therefore the 404s recorded for report 3076 mean the payloads are absent"})
    else:
        add("figure_endpoint_positive_control", "NOT_RUN",
            {"reason": "publish_roundtrip.json absent: this package's own report not published yet"})

    executed = [c for c in checks if c["result"] != "NOT_RUN"]
    ok = all(c["result"] == "PASS" for c in executed)
    return {
        "package_id": manifest["package_id"],
        "report_id": manifest["report_id"],
        "mode": "online (platform re-fetch)" if online else "offline (pinned source.md)",
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"uri": "tensor://reports/3076", "field": "markdown", "sha256": sha256_hex(source),
                   "chars": len(source), "bytes_utf8": len(source.encode("utf-8"))},
        "checks": checks,
        "acceptance_all_pass": ok,
        "verified_label_written": False,
        "note": "对账=结构/哈希/定位/唯一性/边界；不评判报告结论真伪，也不把任何结论标为 verified（verification 由平台门计算）。",
    }


def main() -> int:
    report = run_checks(online=True)
    (OUT / "verification.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in report["checks"]:
        print(f"[{c['result']}] {c['acceptance_item']}")
    print(f"mode={report['mode']} all_pass={report['acceptance_all_pass']}")
    return 0 if report["acceptance_all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())