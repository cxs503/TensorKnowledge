#!/usr/bin/env python3
"""Independent verification of the wp-14478-01 asset registration.

Nothing is taken from the generator: the report is re-fetched from the platform (online mode), the
hash is recomputed, every locator quote is re-sliced out of the fresh markdown, both JSON documents
are validated against their locally pinned schemas, and the work-package acceptance items become a
machine table. Offline mode (`online=False`) is used by the negative-control tests: it verifies the
pinned source.md instead of re-fetching and marks the network-only check NOT_RUN, never PASS.

Exit code 0 only if every executed acceptance item passes.
"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import jsonschema

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kf_fetch_14478 as fetch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wp-14478-01"
CONTRACT_HASH = "8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0"
CONTRACT_CHARS = 6156
CONTRACT_TITLE = "CASE-CYLINDER-DRAG-FVM: TensorFVM DFG 2D-1 cylinder drag case (per-quantity <5% verdict)"
CONTRACT_SCENARIO = "case-cylinder-drag-fvm"
RESERVED_SECTION_TITLES = {
    "①问题与参考值出处", "②方法与实现（已完成的真实部分）", "③参数表（无量纲数完整）",
    "④对照表（ref vs got + 逐项误差）—— **FAIL：无 got**", "⑤收敛性/参数敏感性 —— **FAIL：待计算**",
    "⑥失败模式与工件",
}


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_locators(source: str, assets: list[dict]) -> list[str]:
    """Every locator must slice back to its own quote, occur exactly once, and carry correct lines."""
    errors: list[str] = []
    for asset in assets:
        loc = asset.get("locator", {})
        quote, start, end = loc.get("quote"), loc.get("start_char"), loc.get("end_char")
        aid = asset.get("asset_id")
        if not isinstance(quote, str) or not quote:
            errors.append(f"{aid}: missing quote")
            continue
        if not (isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(source)):
            errors.append(f"{aid}: span {start}:{end} out of range")
            continue
        sliced = source[start:end]
        if loc.get("method") == "document":
            if not sliced.startswith(quote):
                errors.append(f"{aid}: document span does not start with the quote")
        elif sliced != quote:
            errors.append(f"{aid}: source[{start}:{end}] != quote")
        if source.count(quote) != 1 or not loc.get("unique"):
            errors.append(f"{aid}: quote occurs {source.count(quote)}x (unique={loc.get('unique')})")
        exp_start_line = source.count("\n", 0, start) + 1
        exp_end_line = source.count("\n", 0, max(end - 1, start)) + 1
        if (loc.get("start_line"), loc.get("end_line")) != (exp_start_line, exp_end_line):
            errors.append(
                f"{aid}: line span {loc.get('start_line')}-{loc.get('end_line')} "
                f"!= recomputed {exp_start_line}-{exp_end_line}"
            )
        if aid == "A01" and (start, end) != (0, len(source)):
            errors.append("A01: document locator does not cover the whole markdown")
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


def check_unique_ids(manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    ids = [a.get("asset_id") for a in manifest.get("assets", [])]
    if len(ids) != len(set(ids)):
        errors.append(f"duplicate asset_id: {sorted({i for i in ids if ids.count(i) > 1})}")
    if not all(isinstance(i, str) and i.startswith("A") for i in ids):
        errors.append("asset_id naming deviates from A00 pattern")
    claim_ids = [c.get("claim_id") for c in (manifest.get("claims") or []) + (envelope.get("claims") or [])]
    if len(claim_ids) != len(set(claim_ids)):
        errors.append("duplicate claim_id")
    if envelope.get("outputs", {}).get("asset_manifest.json") != manifest:
        errors.append("envelope outputs['asset_manifest.json'] is not byte-equal to asset_manifest.json")
    return errors


def check_claim_policy(manifest: dict, envelope: dict) -> list[str]:
    """Empty claims are legitimate for task_type 01; any claim must carry evidence or an explicit status."""
    errors: list[str] = []
    allowed = {"supported", "partially-supported", "unresolved", "refuted"}
    for claim in (manifest.get("claims") or []) + (envelope.get("claims") or []):
        cid = claim.get("claim_id")
        has_ev = bool(claim.get("evidence"))
        if not has_ev and claim.get("status") not in allowed:
            errors.append(f"{cid}: neither evidence nor an explicit allowed status")
        if claim.get("status") == "verified":
            errors.append(f"{cid}: status 'verified' is not allowed (platform gate owns verification)")
    blob = json.dumps([manifest, envelope], ensure_ascii=False)
    if '"verified"' in blob.replace('\\"', '"'):
        errors.append("the literal string \"verified\" appears as a status value somewhere in the documents")
    return errors


def check_boundaries(manifest: dict, envelope: dict) -> list[str]:
    errors: list[str] = []
    if manifest.get("report_id") != "14478" or envelope.get("report_id") != "14478":
        errors.append("report_id is not 14478")
    b = manifest.get("boundaries", {})
    if b.get("other_reports_read") is not False or b.get("upstream_artifacts_rewritten") is not False:
        errors.append(f"boundary flags are not all false: {b}")
    if any(len(str(a.get("asset_id"))) != 3 for a in manifest.get("assets", [])):
        errors.append("asset_id width deviates from A00")
    for asset in manifest.get("assets", []):
        status = asset.get("payload", {}).get("status")
        if status not in {"in_report_record", "external_url_declared", "external_repo_path_declared",
                          "declared_payload_missing", "declared_in_source_only"}:
            errors.append(f"{asset.get('asset_id')}: unknown payload status {status!r}")
    return errors


def check_record_metadata(manifest: dict, record: dict | None) -> list[str]:
    errors: list[str] = []
    if record is None:
        return ["platform record unavailable, metadata cannot be compared"]
    src = manifest.get("source", {})
    if record.get("title") != src.get("title") or record.get("title") != CONTRACT_TITLE:
        errors.append(f"title drift: record={record.get('title')!r} manifest={src.get('title')!r}")
    if record.get("scenario_key") != src.get("scenario_key") or record.get("scenario_key") != CONTRACT_SCENARIO:
        errors.append(f"scenario_key drift: record={record.get('scenario_key')!r} manifest={src.get('scenario_key')!r}")
    if record.get("tags") != src.get("platform_tags"):
        errors.append("platform tags drift between record and manifest")
    if (record.get("figures") or []) != (src.get("platform_figures") or []):
        errors.append("platform figures drift between record and manifest")
    return errors


def run_checks(out_dir: Path = OUT, online: bool = True) -> dict:
    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    envelope = json.loads((out_dir / "kf_result.wp-14478-01.json").read_text(encoding="utf-8"))
    pinned = (out_dir / "source.md").read_text(encoding="utf-8")

    record: dict | None = None
    source = pinned
    if online:
        source, record = fetch.fetch_markdown()

    checks: list[dict] = []

    def add(item: str, result: str, detail) -> None:
        checks.append({"acceptance_item": item, "result": result, "detail": detail})

    hash_ok = sha256_hex(source) == CONTRACT_HASH == manifest["source"]["hash"] == envelope["provenance"]["source_hash"].split(":", 1)[1]
    add("source_hash_matches", "PASS" if hash_ok else "FAIL",
        {"sha256": sha256_hex(source), "contract": CONTRACT_HASH,
         "provenance": envelope["provenance"]["source_hash"],
         "note": "recomputed from " + ("live platform re-fetch" if online else "pinned source.md")})
    add("chars_match_contract",
        "PASS" if len(source) == CONTRACT_CHARS == manifest["source"]["chars"] else "FAIL",
        {"chars": len(source), "bytes_utf8": len(source.encode("utf-8")), "contract_chars": CONTRACT_CHARS})

    parse_ok = True
    try:
        json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
        json.loads((out_dir / "kf_result.wp-14478-01.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:  # pragma: no cover - only on corrupted artifacts
        parse_ok = False
        add("valid_json", "FAIL", {"error": str(exc)})
    if parse_ok:
        add("valid_json", "PASS", {"files": ["asset_manifest.json", "kf_result.wp-14478-01.json"], "parse": "ok"})

    schema_errors = check_schemas(out_dir, manifest, envelope)
    add("schema_pass", "PASS" if not schema_errors else "FAIL",
        {"errors": schema_errors, "documents": 2,
         "schemas": ["kf_result.v1.schema.json (worktree canonical)",
                     "asset_manifest.v1.schema.json (pinned by this package)"]})

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

    meta_errors = check_record_metadata(manifest, record)
    add("record_metadata_verbatim", "PASS" if not meta_errors else "FAIL",
        {"source": "live platform record" if record is not None else "NOT_RUN (no network fetch in this mode)",
         "errors": meta_errors})

    figures = manifest["source"].get("platform_figures") or []
    if figures:
        token = fetch.login()
        probes = []
        for fig in figures:
            name = fig.get("name") if isinstance(fig, dict) else str(fig)
            import urllib.error
            import urllib.request
            url = fetch.api_base() + f"/tensor/reports/14478/figures/{name}"
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    body = resp.read()
                    probes.append({"name": name, "http_status": resp.status, "bytes": len(body),
                                   "sha256": hashlib.sha256(body).hexdigest()})
            except urllib.error.HTTPError as exc:
                probes.append({"name": name, "http_status": exc.code})
        add("platform_figure_payload_status_current", "PASS" if all(p.get("http_status") == 200 for p in probes) else "FAIL",
            {"probes": probes})
    else:
        add("platform_figure_payload_status_current", "PASS",
            {"platform_figures": 0,
             "note": "the platform record carries no figure entries, so no figure payload can be missing; "
                     "vacuous pass recorded explicitly rather than omitted"})

    executed = [c for c in checks if c["result"] != "NOT_RUN"]
    ok = all(c["result"] == "PASS" for c in executed)
    return {
        "package_id": manifest["package_id"],
        "report_id": manifest["report_id"],
        "mode": "online (platform re-fetch)" if online else "offline (pinned source.md)",
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {"uri": "tensor://reports/14478", "field": "markdown", "sha256": sha256_hex(source),
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