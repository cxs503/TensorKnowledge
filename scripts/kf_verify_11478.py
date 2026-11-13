"""wp-11478-01 · independent verification of the asset manifest.

Re-derives every acceptance item from raw inputs instead of trusting the builder. The pure
check functions take (markdown, manifest) so they can be unit-tested, including with tampered
copies (see tests/test_kf_wp11478.py) — a check that cannot fail proves nothing.

Acceptance items mapped to checks:
  valid_json                -> json.load of the manifest (done by caller/main)
  schema_pass               -> jsonschema against schemas/asset_manifest.v2.schema.json
  source_locator_resolvable -> for every asset locator AND claim evidence quote:
                               quote == md[start_char:end_char] and md.count(quote) == 1
  source_hash_matches       -> sha256(freshly fetched markdown) == manifest.source.hash
                               == contract source_hash
  no_duplicate_ids          -> asset_id / claim_id unique
  claims_evidence           -> supported|refuted need evidence; unresolved|partially-supported
                               need unresolved_reason; nobody may self-mark verified
Extra consistency: counts vs recount, in_report_section must be a real heading.

CLI: python3 scripts/kf_verify_11478.py  -> runs/wp-11478-01/verify_11478.json ; exit 0 iff pass
"""
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

PKG = "wp-11478-01"
REPORT_ID = "11478"
CONTRACT_HASH = "b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258"
RUN_DIR = pathlib.Path("runs") / PKG
MANIFEST = pathlib.Path("docs") / PKG / "asset_manifest.json"
SCHEMA = pathlib.Path("schemas/asset_manifest.v2.schema.json")
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def check_locators(md: str, manifest: dict):
    """Return [(asset_id, reason)] for every locator that does not re-resolve uniquely."""
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        if md.count(quote) != 1:
            bad.append((a["asset_id"], "quote_not_unique"))
            continue
        if md[loc["start_char"]:loc["end_char"]] != quote:
            bad.append((a["asset_id"], "slice_mismatch"))
            continue
        if md.count("\n", 0, loc["start_char"]) != loc["start_line"]:
            bad.append((a["asset_id"], "line_offset_mismatch"))
    return bad


def check_claim_locators(md: str, manifest: dict):
    bad = []
    for c in manifest["claims"]:
        for e in c.get("evidence") or []:
            loc = e.get("locator") or {}
            if md.count(e["quote"]) != 1:
                bad.append((c["claim_id"], "quote_not_unique"))
            elif md[loc.get("start_char", -1):loc.get("end_char", -1)] != e["quote"]:
                bad.append((c["claim_id"], "slice_mismatch"))
    return bad


def check_duplicate_ids(manifest: dict):
    bad = []
    aids = [a["asset_id"] for a in manifest["assets"]]
    cids = [c["claim_id"] for c in manifest["claims"]]
    bad += [("asset_id", i) for i in set(aids) if aids.count(i) > 1]
    bad += [("claim_id", i) for i in set(cids) if cids.count(i) > 1]
    return bad


def check_claim_status(manifest: dict):
    """Claims must be evidenced or explicitly unresolved; nobody may mark a claim verified."""
    bad = []
    for c in manifest["claims"]:
        st = c["status"]
        if st in ("supported", "refuted") and not c.get("evidence"):
            bad.append((c["claim_id"], "missing_evidence"))
        if st in ("unresolved", "partially-supported") and not c.get("unresolved_reason"):
            bad.append((c["claim_id"], "missing_unresolved_reason"))
        if c.get("verified") is True:
            bad.append((c["claim_id"], "self_marked_verified"))
    return bad


def check_counts(manifest: dict):
    bad = []
    by_class, by_res = {}, {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    if c["assets"] != len(manifest["assets"]):
        bad.append(("counts.assets", c["assets"], len(manifest["assets"])))
    if c["by_class"] != by_class:
        bad.append(("counts.by_class", c["by_class"], by_class))
    if c["by_resolution"] != by_res:
        bad.append(("counts.by_resolution", c["by_resolution"], by_res))
    if sum(c["by_resolution"].values()) != c["assets"]:
        bad.append(("counts.by_resolution.sum", sum(c["by_resolution"].values()), c["assets"]))
    for key in ("resolved_in_source", "referenced_unresolved", "declared_absent",
                "resolved_in_platform_record"):
        if key in c and c[key] != by_res.get(key, 0):
            bad.append((f"counts.{key}", c[key], by_res.get(key, 0)))
    return bad


def check_sections(md: str, manifest: dict):
    headings = {ln.strip() for ln in md.split("\n") if ln.startswith("#")}
    return [(a["asset_id"], a["in_report_section"]) for a in manifest["assets"]
            if a["in_report_section"] not in headings]


def verify(md: str, manifest: dict, schema: dict) -> dict:
    import jsonschema
    checks, blocking = [], []

    try:
        jsonschema.validate(manifest, schema)
        checks.append(dict(id="schema_pass", ok=True, detail="schemas/asset_manifest.v2.schema.json"))
    except Exception as exc:
        checks.append(dict(id="schema_pass", ok=False, detail=str(exc)[:400]))
        blocking.append("schema_pass")

    live = hashlib.sha256(md.encode()).hexdigest()
    mh = manifest["source"]["hash"]
    ok = live == mh == CONTRACT_HASH
    checks.append(dict(id="source_hash_matches", ok=ok,
                       detail=dict(live_sha256=live, manifest_sha256=mh,
                                   contract_sha256=CONTRACT_HASH, chars=len(md))))
    if not ok:
        blocking.append("source_hash_matches")

    bad_loc = check_locators(md, manifest) + check_claim_locators(md, manifest)
    checks.append(dict(id="source_locator_resolvable", ok=not bad_loc,
                       detail=dict(assets_checked=len(manifest["assets"]),
                                   claim_quotes_checked=sum(len(c.get("evidence") or [])
                                                            for c in manifest["claims"]),
                                   failures=bad_loc,
                                   method="quote == md[start_char:end_char] and md.count(quote)==1")))
    if bad_loc:
        blocking.append("source_locator_resolvable")

    dup = check_duplicate_ids(manifest)
    checks.append(dict(id="no_duplicate_ids", ok=not dup, detail=dict(failures=dup,
                       assets=len(manifest["assets"]), claims=len(manifest["claims"]))))
    if dup:
        blocking.append("no_duplicate_ids")

    cbad = check_claim_status(manifest)
    checks.append(dict(id="all_claims_have_evidence_or_explicit_unresolved_status", ok=not cbad,
                       detail=dict(failures=cbad,
                                   by_status={s: sum(1 for c in manifest["claims"] if c["status"] == s)
                                              for s in sorted({c["status"] for c in manifest["claims"]})})))
    if cbad:
        blocking.append("all_claims_have_evidence_or_explicit_unresolved_status")

    cnt = check_counts(manifest)
    checks.append(dict(id="counts_consistent", ok=not cnt, detail=dict(failures=cnt)))
    if cnt:
        blocking.append("counts_consistent")

    sec = check_sections(md, manifest)
    checks.append(dict(id="sections_exist_in_source", ok=not sec, detail=dict(failures=sec)))
    if sec:
        blocking.append("sections_exist_in_source")

    return dict(package_id=PKG, report_id=REPORT_ID, status="pass" if not blocking else "fail",
                blocking_failures=blocking, checks=checks,
                verified_by="scripts/kf_verify_11478.py (local); platform gate is authoritative")


def fetch_markdown():
    """Fresh fetch (no local cache) so locator/hash checks are independent of the builder."""
    token = None
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if user and pwd:
        req = urllib.request.Request(BASE + "/auth/login",
                                     data=json.dumps({"username": user, "password": pwd}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        token = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
    req = urllib.request.Request(f"{BASE}/tensor/reports/{REPORT_ID}")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    if isinstance(payload.get("data"), dict):
        payload = payload["data"]
    return payload.get("markdown") or ""


def main() -> int:
    manifest = json.loads(MANIFEST.read_text())
    schema = json.loads(SCHEMA.read_text())
    md = fetch_markdown()
    verdict = verify(md, manifest, schema)
    verdict["checks"].insert(0, dict(id="valid_json", ok=True, detail=str(MANIFEST)))
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / "verify_11478.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2))
    print(json.dumps(dict(status=verdict["status"], blocking=verdict["blocking_failures"],
                          checks={c["id"]: c["ok"] for c in verdict["checks"]}), ensure_ascii=False))
    return 0 if verdict["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())