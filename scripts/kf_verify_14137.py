"""Independent acceptance verifier for wp-14137-01 (does not import the registering script).

Re-derives every acceptance item from raw bytes rather than trusting the manifest:
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

Usage: python3 scripts/kf_verify_14137.py [--offline]
Writes artifacts/wp-14137-01/acceptance.json
Exit code 0 = all PASS, 2 = at least one FAIL.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/wp-14137-01"
ART = ROOT / "artifacts/wp-14137-01"
MANIFEST = ART / "asset_manifest.json"
ENVELOPE = RUN / "kf_result.wp-14137-01.json"
SOURCE_MD = RUN / "report_14137.md"

PACKAGE_ID = "wp-14137-01"
REPORT_ID = "14137"
CONTRACT_HASH = "6f65040f0d3483ee5ca35f81c0fa4e5af147165e066e6c9c1cdb9a815faa8c30"
CONTRACT_CHARS = 7569
RESOLUTIONS = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
# gate parity is reported separately from the contract acceptance items, so the published
# 18-item acceptance table stays a faithful copy of this file's checks[]
PARITY: dict = {"ok": None, "detail": "not run (offline)"}


def fresh_markdown() -> tuple[str, str]:
    """Re-fetch from the platform (same computation the gate performs). Returns (markdown, note)."""
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (user and pwd):
        return "", "no credentials in env; online re-fetch skipped"
    try:
        req = urllib.request.Request(base + "/auth/login",
                                     data=json.dumps({"username": user, "password": pwd}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode())
        tok = tok.get("access_token") or tok.get("token") or (tok.get("data") or {}).get("access_token")
        req = urllib.request.Request(base + f"/tensor/reports/{REPORT_ID}",
                                     headers={"Authorization": "Bearer " + tok})
        with urllib.request.urlopen(req, timeout=60) as r:
            rec = json.loads(r.read().decode())
        if isinstance(rec.get("data"), dict):
            rec = rec["data"]
        return rec.get("markdown") or "", "re-fetched from platform API"
    except Exception as exc:  # pragma: no cover
        return "", f"online re-fetch failed: {exc}"


def api_url(path: str) -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/") + path


def _token() -> str:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    req = urllib.request.Request(base + "/auth/login",
                                 data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                  "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        d = json.loads(r.read().decode())
    return d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")


def line_of(text: str, pos: int) -> int:
    return text[:pos].count("\n")


def main() -> int:
    offline = "--offline" in sys.argv
    out = ART / "acceptance.json"
    if "--out" in sys.argv:
        out = pathlib.Path(sys.argv[sys.argv.index("--out") + 1])
    checks: list[dict] = []

    def add(item, ok, detail, evidence=None):
        checks.append(dict(item=item, result="PASS" if ok else "FAIL", detail=detail,
                           evidence=evidence or {}))

    # ---- load ----
    try:
        manifest = json.loads(MANIFEST.read_text())
        add("valid_json:asset_manifest", True, "artifacts/wp-14137-01/asset_manifest.json parses")
    except Exception as exc:
        add("valid_json:asset_manifest", False, str(exc))
        return report(checks, out)
    try:
        envelope = json.loads(ENVELOPE.read_text())
        add("valid_json:kf_result", True, "runs/wp-14137-01/kf_result.wp-14137-01.json parses")
    except Exception as exc:
        add("valid_json:kf_result", False, str(exc))
        return report(checks, out)

    md = SOURCE_MD.read_text()

    # ---- source_hash_matches (three independent ways) ----
    local_hash = hashlib.sha256(md.encode()).hexdigest()
    add("source_hash_matches:local_recompute", local_hash == CONTRACT_HASH,
        f"sha256(runs md)={local_hash}", {"contract": CONTRACT_HASH})
    add("source_hash_matches:manifest_field", manifest["source"]["hash"] == CONTRACT_HASH,
        "manifest.source.hash", {"value": manifest["source"]["hash"]})
    add("source_hash_matches:envelope_provenance",
        envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH,
        "envelope.provenance.source_hash", {"value": envelope["provenance"]["source_hash"]})
    if not offline:
        fresh, note = fresh_markdown()
        ok = bool(fresh) and hashlib.sha256(fresh.encode()).hexdigest() == CONTRACT_HASH
        add("source_hash_matches:platform_refetch", ok, note,
            {"fresh_sha256": hashlib.sha256(fresh.encode()).hexdigest() if fresh else None})
    add("source_chars_matches_contract", len(md) == CONTRACT_CHARS,
        f"len(markdown)={len(md)} contract={CONTRACT_CHARS}")

    # ---- gate parity: local envelope == the ```json block of the published report ----
    if not offline:
        rt = ROOT / "docs/wp-14137-01/publish_roundtrip.json"
        if rt.exists():
            rid = json.loads(rt.read_text()).get("published_report_id")
            try:
                tok = _token()
                req = urllib.request.Request(api_url(f"/tensor/reports/{rid}"),
                                             headers={"Authorization": "Bearer " + tok})
                with urllib.request.urlopen(req, timeout=60) as r:
                    rec = json.loads(r.read().decode())
                if isinstance(rec.get("data"), dict):
                    rec = rec["data"]
                md_pub = rec.get("markdown", "")
                start = md_pub.find("```json")
                block = json.loads(md_pub[start + 7:md_pub.rfind("\n```")])
                PARITY.update(report_id=rid, ok=block == envelope,
                              json_blocks=md_pub.count("```json"),
                              title=rec.get("title"),
                              tags_ok=f"kf-wp:{PACKAGE_ID}" in (rec.get("tags") or []),
                              detail=f"report {rid}: stored json block equals runs/.../kf_result.{PACKAGE_ID}.json")
            except Exception as exc:
                PARITY.update(report_id=rid, ok=False, detail=f"{type(exc).__name__}: {exc}")

    # ---- schema_pass ----
    try:
        import jsonschema
        schema = json.loads((ROOT / "schemas/asset_manifest.v1.schema.json").read_text())
        patched = copy.deepcopy(schema)
        patched["properties"]["package_id"] = {"const": PACKAGE_ID}
        patched["properties"]["report_id"] = {"const": REPORT_ID}
        patched["properties"]["source"]["properties"]["uri"] = {"const": f"tensor://reports/{REPORT_ID}"}
        jsonschema.validate(manifest, patched)
        jsonschema.validate(envelope, json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text()))
        add("schema_pass", True,
            "asset_manifest.v1 (identity consts substituted for this package) + kf_result.v1 both validate")
    except Exception as exc:
        add("schema_pass", False, f"{type(exc).__name__}: {str(exc)[:400]}")

    # ---- source_locator_resolvable ----
    bad = []
    non_unique = []
    line_mismatch = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        if md[s:e] != loc["quote"]:
            bad.append(a["asset_id"])
        if md.count(loc["quote"]) != 1:
            non_unique.append(a["asset_id"])
        if line_of(md, s) != loc["start_line"] or line_of(md, max(s, e - 1)) != loc["end_line"]:
            line_mismatch.append(a["asset_id"])
        if a["resolution"] not in RESOLUTIONS:
            bad.append(a["asset_id"] + ":bad_resolution")
    add("source_locator_resolvable:quote_slices", not bad,
        f"{len(manifest['assets'])} assets; md[start:end]==quote for all", {"failures": bad})
    add("source_locator_resolvable:quote_unique", not non_unique,
        "every quote is a unique substring of the markdown", {"failures": non_unique})
    add("source_locator_resolvable:line_numbers_consistent", not line_mismatch,
        "start_line/end_line recomputed from char offsets match", {"failures": line_mismatch})

    # ---- no_duplicate_ids ----
    ids = [a["asset_id"] for a in manifest["assets"]]
    add("no_duplicate_ids", len(ids) == len(set(ids)), f"{len(ids)} asset ids, {len(set(ids))} unique")

    # ---- claims ----
    claims = manifest.get("claims", [])
    claim_ok = all(("evidence_locator" in c) or c.get("status") in
                   {"supported", "partially-supported", "unresolved", "refuted"} for c in claims)
    add("all_claims_have_evidence_or_explicit_unresolved_status", claim_ok,
        f"claims={len(claims)} (empty array is legitimate here: no extraction in task_type 01)")

    env_claims = envelope.get("claims", [])
    env_ok = all(c.get("evidence") or c.get("status") in
                 {"unresolved", "refuted", "supported", "partially-supported"} for c in env_claims)
    add("kf_result_claims_constraint", env_ok, f"envelope claims={len(env_claims)}")

    # ---- envelope <-> manifest consistency ----
    add("envelope_outputs_equal_manifest", envelope["outputs"].get("asset_manifest.json") == manifest,
        "outputs['asset_manifest.json'] is byte-identical in content to the artifact file")
    add("envelope_identity", (envelope["package_id"], envelope["report_id"], envelope["task_type"])
        == (PACKAGE_ID, REPORT_ID, "01-asset-registration"),
        "package_id/report_id/task_type fields")
    add("not_marked_verified",
        "verified" not in json.dumps(manifest.get("assets", []), ensure_ascii=False).lower().replace("未标 verified", "")
        and manifest["integrity"].get("hash_matches_contract") is True,
        "no asset carries a 'verified' label; registration only")

    # ---- counts self-consistency ----
    by_res = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    add("counts_consistent", manifest["counts"]["by_resolution"] == by_res
        and manifest["counts"]["assets"] == len(manifest["assets"]),
        "counts.by_resolution / counts.assets recomputed", {"recomputed": by_res})

    return report(checks, out)


def report(checks: list[dict], dest: pathlib.Path) -> int:
    ART.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for c in checks if c["result"] == "PASS")
    payload = dict(package_id=PACKAGE_ID, report_id=REPORT_ID, total=len(checks), passed=passed,
                   failed=len(checks) - passed, checks=checks, gate_parity=PARITY)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    dest.write_text(text)
    mirror = ROOT / "docs/wp-14137-01/acceptance.json"
    if dest == ART / "acceptance.json":          # artifacts/ is gitignored -> keep a committed copy
        mirror.parent.mkdir(parents=True, exist_ok=True)
        mirror.write_text(text)
    for c in checks:
        print(f"{c['result']:<4} {c['item']:<58} {c['detail'][:90]}")
    print(f"gate_parity: {'PASS' if PARITY.get('ok') else ('SKIP' if PARITY.get('ok') is None else 'FAIL')}"
          f" — {PARITY.get('detail', '')}")
    print(f"\n{passed}/{len(checks)} PASS -> {dest}")
    return 0 if passed == len(checks) and PARITY.get("ok") is not False else 2


if __name__ == "__main__":
    raise SystemExit(main())