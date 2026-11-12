#!/usr/bin/env python3
"""Probe whether report 1226's declared figures / referenced artifacts are byte-resolvable.

Every probe is a plain HTTP GET against the platform; the observed status code is the
evidence registered in the asset manifest.  No writes, no other report_id touched.
"""
import json
import os
import urllib.error
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


def login():
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": USER, "password": PASS}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    return d.get("access_token") or d.get("token")


def probe(path, token):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            return {"path": path, "http_status": r.status, "bytes": len(body),
                    "content_type": r.headers.get("Content-Type")}
    except urllib.error.HTTPError as e:
        return {"path": path, "http_status": e.code, "bytes": 0, "content_type": None}
    except Exception as e:  # noqa: BLE001 - transport failure is itself evidence
        return {"path": path, "http_status": None, "error": type(e).__name__, "bytes": 0}


CANDIDATES = [
    "/tensor/reports/1226/figures/fig1_cii_reference_lines.png",
    "/tensor/reports/1226/figures",
    "/tensor/artifacts/cii_m1643/cii_reference_verification.json",
    "/tensor/reports/1226/attachments",
]


def main():
    tok = login()
    out = [probe(p, tok) for p in CANDIDATES]
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()