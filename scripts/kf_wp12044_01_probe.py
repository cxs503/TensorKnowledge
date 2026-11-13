#!/usr/bin/env python3
"""Probe auxiliary platform endpoints for report 12044 (figure resolution evidence).

Records raw responses so the asset_manifest resolution_check rows are backed by an
actually-executed probe rather than an assumption. Credentials: environment only.
"""
from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-12044-01"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def login() -> str:
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.loads(r.read().decode())
    if isinstance(d.get("data"), dict):
        d = d["data"]
    return d.get("access_token") or d.get("token")


def get(path: str, token: str):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            try:
                return {"status": r.status, "body": json.loads(body.decode())}
            except Exception:
                return {"status": r.status, "body": "<non-json %d bytes>" % len(body)}
    except urllib.error.HTTPError as e:
        return {"status": e.code, "body": e.read().decode(errors="replace")[:400]}
    except Exception as e:  # pragma: no cover
        return {"status": None, "error": str(e)}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    tok = login()
    paths = [
        "/tensor/reports/12044/figures",
        "/tensor/reports/12044/assets",
        "/tensor/reports/12044/attachments",
    ]
    out = {"base": BASE, "probes": {}}
    for p in paths:
        out["probes"][p] = get(p, tok)
    (OUT / "platform_probe.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(out, ensure_ascii=False, indent=2)[:2500])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())