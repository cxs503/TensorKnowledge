#!/usr/bin/env python3
"""wp-10542-01: fetch report 10542 markdown from the platform API and pin its sha256.

No secrets on the command line: credentials come from the environment
(TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE).
"""
import hashlib
import json
import os
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
RID = "10542"
OUT = "/tmp/kf10542/report.json"


def post(path, body):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def get(path, token):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def main():
    for path in ("/tensor/auth/login", "/auth/login"):
        try:
            tok = post(path, {"username": USER, "password": PASS})
            break
        except Exception as e:  # noqa: BLE001
            last = e
    else:
        raise SystemExit(f"login failed: {last}")
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise SystemExit(f"no token in login response keys={list(tok)}")
    rec = get(f"/tensor/reports/{RID}", token)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    md = rec["markdown"]
    h = hashlib.sha256(md.encode("utf-8")).hexdigest()
    meta = {
        "report_id": RID,
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "tags": rec.get("tags"),
        "figures": rec.get("figures"),
        "chars": len(md),
        "bytes_utf8": len(md.encode("utf-8")),
        "sha256": h,
        "record_keys": sorted(rec.keys()),
    }
    json.dump({"meta": meta, "markdown": md}, open(OUT, "w"), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()