"""Post-publish probe for wp-13946-01: are the delivered figure bytes retrievable and identical?

The platform JSON record for a report keeps figures as name+caption only (png_base64 comes back
empty), but the bytes are served at /tensor/reports/<id>/figures/<name>. This script fetches them
for the published KF-RESULT report and compares sha256 against the local committed png, so the
figure in the delivery is evidence, not an assertion.

Inputs : docs/wp-13946-01/published.json (report id written by kf_publish_13946.py)
         docs/wp-13946-01/fig1_asset_coverage.png
Outputs: artifacts/wp-13946-01/figure_probe.json, docs/wp-13946-01/figure_probe.json
Exit   : 0 match, 1 mismatch, 2 cannot verify
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

DOC = pathlib.Path("docs/wp-13946-01")
ART = pathlib.Path("artifacts/wp-13946-01")
PNG = DOC / "fig1_asset_coverage.png"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _open(url, payload=None, tok=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"} if data else {})
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    return urllib.request.urlopen(req, timeout=60)


def login() -> str | None:
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (user and pwd):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = json.loads(_open(BASE + path, {"username": user, "password": pwd}).read())
        except Exception:  # noqa: BLE001
            continue
        tok = d.get("access_token") or d.get("token")
        if tok:
            return tok
    return None


def main() -> int:
    pub = json.loads((DOC / "published.json").read_text())
    rid = pub["response"]["id"]
    tok = login()
    local = PNG.read_bytes()
    rec = json.loads(_open(BASE + "/tensor/reports/%s" % rid, tok=tok).read())
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    name = (rec.get("figures") or [{}])[0].get("name")
    try:
        r = _open(BASE + "/tensor/reports/%s/figures/%s" % (rid, name), tok=tok)
        remote = r.read()
        status = r.status
    except urllib.error.HTTPError as exc:
        print("figure not retrievable:", exc.code, exc.read()[:120])
        return 2
    out = {
        "report_id": rid,
        "report_title": rec.get("title"),
        "figure_name": name,
        "png_base64_in_record_chars": len((rec.get("figures") or [{}])[0].get("png_base64") or ""),
        "http_status": status,
        "local_bytes": len(local),
        "remote_bytes": len(remote),
        "local_sha256": hashlib.sha256(local).hexdigest(),
        "remote_sha256": hashlib.sha256(remote).hexdigest(),
        "bytes_identical": remote == local,
        "note": ("Platform keeps figures as name+caption in the report record (png_base64 empty) but "
                 "serves the uploaded bytes at /tensor/reports/<id>/figures/<name>; identity is "
                 "checked by sha256 here."),
    }
    for d in (ART, DOC):
        d.mkdir(parents=True, exist_ok=True)
        (d / "figure_probe.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: out[k] for k in ("report_id", "figure_name", "bytes_identical",
                                          "local_bytes", "remote_bytes")}, ensure_ascii=False))
    return 0 if out["bytes_identical"] else 1


if __name__ == "__main__":
    sys.exit(main())