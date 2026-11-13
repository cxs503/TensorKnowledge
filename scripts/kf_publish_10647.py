"""Publish the wp-10647-01 progress report to the platform (/tensor/reports).

Payload is /tmp/report_10647_publish.json, produced by scripts/kf_report_10647.py (report markdown
contains exactly one ```json block = the result envelope, byte-identical to
runs/wp-10647-01/kf_result.wp-10647-01.json).

Auth: TENSOR_AGENT_USER / TENSOR_AGENT_PASS against $TENSOR_API_BASE (default :8010/api/v1).
The response is stored as runs/wp-10647-01/publish_response.json and re-read from the API to confirm
round-trip (report id, tags, figure count).

Usage: python3 scripts/kf_publish_10647.py
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PAYLOAD = pathlib.Path("/tmp/report_10647_publish.json")
OUT = pathlib.Path("runs/wp-10647-01/publish_response.json")


def request(path: str, data: dict | None, token: str | None = None) -> dict:
    body = json.dumps(data).encode() if data is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(BASE + path, data=body, headers=headers,
                                 method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def login() -> str:
    user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = request(path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    raise SystemExit("login failed")


def main() -> int:
    token = login()
    payload = json.loads(PAYLOAD.read_text(encoding="utf-8"))
    resp = request("/tensor/reports", payload, token)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(resp, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rid = resp.get("id")
    print("created report id:", rid, "status:", resp.get("status"),
          "mission:", resp.get("mission_id"))
    print("tags:", resp.get("tags"))
    print("figures:", [(f.get("name"), len(f.get("png_base64") or "")) for f in (resp.get("figures") or [])])
    print("markdown chars:", len(resp.get("markdown") or ""))

    # round-trip verification: read the report back and check the single ```json block
    back = request("/tensor/reports/%s" % rid, None, token)
    if isinstance(back.get("data"), dict):
        back = back["data"]
    md = back.get("markdown") or ""
    ok_single = (md.count("```json") == 1)
    print("round-trip id match:", back.get("id") == rid)
    print("single json block:", ok_single, "| md chars:", len(md))
    return 0 if ok_single and back.get("id") == rid else 1


if __name__ == "__main__":
    sys.exit(main())