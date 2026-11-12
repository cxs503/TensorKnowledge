"""Post-hoc check of the published mission report: the server-side copy must still contain exactly one
fenced json block, that block must parse, and its provenance hash must equal report 448's markdown hash.

Usage: python3 scripts/kf_check_published.py <report_id>
"""
import hashlib
import json
import os
import re
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
EXPECTED = "a3e7910fbcbe3624805a875ebd9a033c54036a1950cdc2885a6fc739dbcabea8"


def token():
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            req = urllib.request.Request(BASE + path, data=json.dumps({"username": u, "password": p}).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
            t = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
            if t:
                return t
        except Exception:
            continue
    return None


def get(path, tok):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def main():
    rid = sys.argv[1]
    tok = token()
    rep = get("/tensor/reports/%s" % rid, tok)
    if "data" in rep and isinstance(rep["data"], dict):
        rep = rep["data"]
    md = rep["markdown"]
    blocks = re.findall(r"```(\w*)\n(.*?)```", md, re.S)
    jblocks = [b for b in blocks if b[0] == "json"]
    result = json.loads(jblocks[0][1]) if jblocks else None
    src = get("/tensor/reports/448", tok)["markdown"]
    src = src if isinstance(src, str) else src
    h = hashlib.sha256(src.encode()).hexdigest()
    print("published report id:", rep["id"], "| title:", rep["title"])
    print("tags:", rep.get("tags"))
    print("figures:", [f.get("name") for f in rep.get("figures", [])])
    print("fenced blocks:", [(b[0], len(b[1])) for b in blocks])
    print("json blocks:", len(jblocks))
    print("embedded package_id/task_type/report_id:", result and (result["package_id"], result["task_type"], result["report_id"]))
    print("embedded provenance.source_hash:", result and result["provenance"]["source_hash"])
    print("report 448 markdown sha256 (recomputed now):", h)
    print("MATCH:", bool(result) and result["provenance"]["source_hash"] == "sha256:" + h == "sha256:" + EXPECTED)
    print("asset count embedded:", result and len(result["outputs"]["asset_manifest.json"]["assets"]))
    return 0 if (len(jblocks) == 1 and result and h == EXPECTED) else 1


if __name__ == "__main__":
    sys.exit(main())