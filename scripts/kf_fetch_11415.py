#!/usr/bin/env python3
"""Fetch report 11415 (markdown + metadata + figure binaries) from the report API.

Writes (all inside the worktree):
  runs/wp-11415-01/report_11415.json      raw report payload (markdown field included)
  runs/wp-11415-01/report_11415.md        markdown extracted from payload['markdown']
  runs/wp-11415-01/figures/<name>.png     figure binaries (GET /tensor/reports/11415/figures/<name>)
  runs/wp-11415-01/figures_manifest.json  per-figure fingerprint (bytes / sha256 / content-type)

No hashing decisions here; scripts/kf_register_11415.py recomputes the markdown hash
and refuses to run if it differs from the work-package contract source_hash.
Run:  python3 scripts/kf_fetch_11415.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

REPORT_ID = "11415"
RUN_DIR = pathlib.Path("runs/wp-11415-01")
FIG_DIR = RUN_DIR / "figures"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _post_json(url: str, payload: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login() -> str:
    user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    last: object = None
    for path in ("/auth/login", "/tensor/auth/login"):
        try:
            d = _post_json(API + path, {"username": user, "password": pwd})
        except Exception as exc:  # noqa: BLE001
            last = exc
            continue
        for k in ("access_token", "token", "accessToken"):
            if isinstance(d, dict) and d.get(k):
                return d[k]
        last = RuntimeError("no token field in login response")
    raise SystemExit(f"login failed: {last}")


def get(url: str, token: str):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.status, r.headers.get("content-type"), r.read()


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    token = login()

    status, ctype, raw = get(f"{API}/tensor/reports/{REPORT_ID}", token)
    payload = json.loads(raw.decode())
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        payload = payload["data"]
    if not isinstance(payload, dict) or "markdown" not in payload:
        print("FATAL: unexpected payload shape", file=sys.stderr)
        return 2
    (RUN_DIR / "report_11415.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n")
    md = payload["markdown"]
    (RUN_DIR / "report_11415.md").write_text(md)
    print("report_id:", payload.get("id"), "title:", payload.get("title"))
    print("scenario_key:", payload.get("scenario_key"))
    print("tags:", payload.get("tags"))
    print("markdown chars:", len(md), "bytes_utf8:", len(md.encode()))

    figs = []
    for f in payload.get("figures") or []:
        name = f.get("name")
        url = f"{API}/tensor/reports/{REPORT_ID}/figures/{name}"
        rec = dict(name=name, caption=f.get("caption", ""), url=url,
                   source="GET /tensor/reports/%s/figures/{name}" % REPORT_ID)
        try:
            st, ct, blob = get(url, token)
            path = FIG_DIR / name
            path.write_bytes(blob)
            rec.update(http_status=st, content_type=ct, bytes=len(blob),
                       sha256="sha256:" + hashlib.sha256(blob).hexdigest(),
                       png_magic=blob[:8] == PNG_MAGIC, local_copy=str(path))
        except urllib.error.HTTPError as exc:
            rec.update(http_status=exc.code, error="HTTPError")
        except Exception as exc:  # noqa: BLE001
            rec.update(error=type(exc).__name__)
        figs.append(rec)
        print("figure:", name, rec.get("http_status"), rec.get("bytes"), rec.get("sha256"))
    (RUN_DIR / "figures_manifest.json").write_text(
        json.dumps(dict(report_id=REPORT_ID, figures=figs), ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())