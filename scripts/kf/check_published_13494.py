"""Post-publication check for work package wp-13494-01.

Re-reads the *published* report from the platform (not the local files) and replays the checks the
platform gate is expected to run, so a pass here is evidence about the delivered artifact rather than
about the working copy:

  1. title / tags carry the package identity (KF-RESULT wp-13494-01, kf-wp:wp-13494-01)
  2. the markdown holds exactly one ```json block and it parses
  3. that envelope's package_id / task_type / report_id / provenance.source_hash are the contract values
  4. provenance.source_hash equals sha256 of the live markdown of report 13494 (recomputed now)
  5. every asset quote in the embedded manifest is a verbatim substring of report 13494's markdown,
     and its recorded char span still slices back to the same bytes
  6. no duplicate asset ids; zero claims (registration only, nothing marked verified)

Usage: python3 scripts/kf/check_published_13494.py [published_report_id]
Writes: docs/kf/wp-13494-01/published_check.json
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PKG = "wp-13494-01"
REPORT_ID = "13494"
EXPECTED_HASH = "ad61f9e0bc3dbe8c8f4ae40ce90056f06c98477c9a33302193f8297756783abe"
OUT = pathlib.Path("docs/kf") / PKG / "published_check.json"


def _login() -> str:
    cred = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=cred,
                                headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return d.get("access_token") or d.get("token")


def _get(path: str, token: str):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    return d["data"] if isinstance(d, dict) and isinstance(d.get("data"), dict) else d


def main() -> int:
    pub_id = sys.argv[1] if len(sys.argv) > 1 else None
    token = _login()
    src = _get("/tensor/reports/" + REPORT_ID, token)
    src_md = src["markdown"]
    src_hash = hashlib.sha256(src_md.encode("utf-8")).hexdigest()

    pub = None
    if pub_id:
        pub = _get("/tensor/reports/" + pub_id, token)
    else:  # find the published KF-RESULT report for this package
        listing = _get("/tensor/reports?limit=200", token)
        rows = listing.get("items") or listing.get("reports") or listing or []
        for r in rows:
            if r.get("title") == "KF-RESULT " + PKG:
                pub = _get("/tensor/reports/%s" % r["id"], token)
                break
    checks = {}
    if pub is None:
        checks["published_report_found"] = {"pass": False, "detail": "no report titled KF-RESULT %s" % PKG}
        verdict = {"package_id": PKG, "checks": checks, "all_pass": False}
        OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(verdict, ensure_ascii=False, indent=1))
        return 1

    md = pub.get("markdown") or ""
    tags = pub.get("tags") or []
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    envelope = json.loads(blocks[0]) if len(blocks) == 1 else None

    checks["published_report_found"] = {"pass": True,
                                        "detail": "id=%s title=%r tags=%s" % (pub.get("id"), pub.get("title"), tags)}
    checks["title_and_tag"] = {
        "pass": pub.get("title") == "KF-RESULT " + PKG and ("kf-wp:" + PKG) in tags,
        "detail": "title=%r has_tag=%s" % (pub.get("title"), ("kf-wp:" + PKG) in tags)}
    checks["single_json_block_parses"] = {
        "pass": len(blocks) == 1 and isinstance(envelope, dict),
        "detail": "json fences in published markdown=%d" % len(blocks)}
    checks["envelope_identity"] = {
        "pass": bool(envelope) and envelope.get("package_id") == PKG
        and envelope.get("task_type") == "01-asset-registration"
        and envelope.get("report_id") == REPORT_ID,
        "detail": None if not envelope else {k: envelope.get(k) for k in ("package_id", "task_type", "report_id")}}
    checks["envelope_hash_is_live_source_hash"] = {
        "pass": bool(envelope) and envelope.get("provenance", {}).get("source_hash") == "sha256:" + src_hash
        == "sha256:" + EXPECTED_HASH,
        "detail": "recomputed=%s envelope=%s contract=%s" % (
            src_hash, (envelope or {}).get("provenance", {}).get("source_hash"), EXPECTED_HASH)}

    # The envelope carries a summary of the produced file, so the delivered manifest is loaded from
    # its declared path and pinned to the envelope hash before it is used as the evidence base.
    out_entry = ((envelope or {}).get("outputs") or {}).get("asset_manifest.json") or {}
    mpath = pathlib.Path(out_entry.get("path") or (OUT.parent / "asset_manifest.json"))
    mbytes = mpath.read_bytes() if mpath.is_file() else b""
    manifest = json.loads(mbytes) if mbytes else {}
    assets = manifest.get("assets") or []
    checks["delivered_manifest_matches_envelope"] = {
        "pass": bool(mbytes) and hashlib.sha256(mbytes).hexdigest() == out_entry.get("sha256"),
        "detail": "path=%s recomputed=%s envelope=%s" % (
            mpath, hashlib.sha256(mbytes).hexdigest() if mbytes else None, out_entry.get("sha256"))}
    bad = []
    for a in assets:
        loc = a.get("locator", {})
        s, e, q = loc.get("start_char"), loc.get("end_char"), loc.get("quote")
        if not isinstance(s, int) or not isinstance(e, int) or not q:
            bad.append([a.get("asset_id"), "missing_locator"])
        elif q not in src_md or src_md[s:e] != q:
            bad.append([a.get("asset_id"), "quote_or_span"])
    ids = [a.get("asset_id") for a in assets]
    claims = (envelope or {}).get("claims") or []
    mclaims = manifest.get("claims") or []
    checks["quotes_verbatim_in_live_source"] = {
        "pass": bool(assets) and not bad,
        "detail": "assets=%d bad=%s" % (len(assets), bad[:5])}
    checks["no_duplicate_ids"] = {"pass": len(ids) == len(set(ids)) and all(ids),
                                  "detail": "assets=%d unique=%d" % (len(ids), len(set(ids)))}
    checks["claims_zero_and_none_verified"] = {
        "pass": claims == [] and mclaims == [],
        "detail": "envelope claims=%d manifest claims=%d (registration package: extraction is a "
                  "downstream work package)" % (len(claims), len(mclaims))}

    verdict = {"package_id": PKG, "published_report_id": pub.get("id"),
               "source_report_id": REPORT_ID, "source_hash": src_hash,
               "checks": checks, "all_pass": all(c["pass"] for c in checks.values()),
               "scope_note": "post-publication replay of the acceptance checks against the platform copy; "
                             "the platform gate remains authoritative."}
    OUT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    return 0 if verdict["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())