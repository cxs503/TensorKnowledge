"""Post-hoc check of the published KF-RESULT report for wp-12690-01.

The server-side copy must contain exactly one fenced ```json block, that block must parse back to the
shipped envelope byte-for-byte (as parsed), and its provenance hash must equal the markdown hash the
platform itself holds for report 12690 -- i.e. the hash is recomputed from the platform's copy of the
source report, not trusted from the envelope.

Usage: python3 scripts/kf_check_published_12690.py [published_report_id]
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
SOURCE_REPORT = "12690"
PKG = "wp-12690-01"
DEFAULT_PUBLISHED = "14863"


def token() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            req = urllib.request.Request(
                BASE + path, data=json.dumps({"username": u, "password": p}).encode(),
                headers={"Content-Type": "application/json"})
            d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
            t = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
            if t:
                return t
        except Exception:
            continue
    return None


def get(path: str, tok: str | None) -> dict:
    req = urllib.request.Request(BASE + path)
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    return d["data"] if isinstance(d, dict) and isinstance(d.get("data"), dict) else d


def main() -> int:
    rid = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PUBLISHED
    tok = token()
    pub = get(f"/tensor/reports/{rid}", tok)
    src = get(f"/tensor/reports/{SOURCE_REPORT}", tok)

    md = pub.get("markdown") or ""
    blocks = re.findall(r"```(\w*)\n(.*?)```", md, re.S)
    jblocks = [b for b in blocks if b[0] == "json"]
    ok = True

    def chk(name: str, cond: bool, detail: str) -> None:
        nonlocal ok
        ok = ok and cond
        print(("PASS " if cond else "FAIL ") + name + " :: " + detail)

    chk("single_json_block", len(jblocks) == 1, f"json fences={len(jblocks)}, all fences={len(blocks)}")
    got = json.loads(jblocks[0][1]) if jblocks else {}
    local = json.loads(pathlib.Path(f"runs/{PKG}/kf_result.{PKG}.json").read_text())
    chk("block_equals_shipped_envelope", got == local, f"package_id={got.get('package_id')}")

    h_plat = hashlib.sha256((src.get("markdown") or "").encode()).hexdigest()
    prov = (got.get("provenance") or {}).get("source_hash", "")
    chk("platform_recomputed_hash_matches",
        prov == "sha256:" + h_plat,
        f"platform(12690)={h_plat[:16]}… envelope={prov[:23]}…")

    man = (got.get("outputs") or {}).get("asset_manifest.json") or {}
    chk("manifest_hash_field_matches", man.get("source", {}).get("hash") == h_plat,
        f"manifest.source.hash={str(man.get('source', {}).get('hash'))[:16]}…")
    chk("claims_empty", got.get("claims") == [] and man.get("claims") == [],
        "registration-only package: both claim arrays empty")
    chk("no_verified_label",
        not [a for a in man.get("assets", []) if str(a.get("resolution")) == "verified"],
        f"assets={len(man.get('assets', []))}")
    chk("tag_present", f"kf-wp:{PKG}" in (pub.get("tags") or []), f"tags={pub.get('tags')}")
    chk("title", pub.get("title") == f"KF-RESULT {PKG}", f"title={pub.get('title')!r}")

    print("ALL_PASS:", ok)
    out = json.dumps(dict(published_report_id=rid, source_report=SOURCE_REPORT,
                          platform_hash=h_plat, all_pass=ok), ensure_ascii=False, indent=2)
    for d in (pathlib.Path(f"runs/{PKG}"), pathlib.Path(f"docs/{PKG}")):
        d.mkdir(parents=True, exist_ok=True)
        (d / "published_check.json").write_text(out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())