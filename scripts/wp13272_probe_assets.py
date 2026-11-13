#!/usr/bin/env python3
"""wp-13272-01 · probe platform storage endpoints for the report-13272 figure and
referenced artifacts. Records HTTP status codes (and content hash for 200s) as
evidence; no retries, no guessing.

The report record declares one figure (m13764_cii_consistency.png, name+caption only,
no png_base64) and the markdown names several artifacts/*.json|py|png paths. This probe
checks whether any byte copy is reachable through the platform store.

Writes work/wp-13272-01/source/probes.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
REPORT_ID = "13272"
FIGURE = "m13764_cii_consistency.png"

WT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = WT / "work" / "wp-13272-01" / "source"

ENDPOINTS = [
    f"/tensor/reports/{REPORT_ID}/figures/{FIGURE}",
    f"/tensor/reports/{REPORT_ID}/figures",
    f"/tensor/artifacts/{FIGURE}",
    f"/tensor/reports/{REPORT_ID}/attachments",
]


def probe(path: str, token: str) -> dict:
    url = BASE + path
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            body = r.read()
            out = {
                "endpoint": path,
                "http_status": r.status,
                "content_type": r.headers.get("Content-Type"),
                "bytes": len(body),
                "ok": True,
            }
            if r.status == 200 and body[:4] == b"\x89PNG":
                out["sha256"] = "sha256:" + hashlib.sha256(body).hexdigest()
                out["png_magic_ok"] = True
                if path.endswith(FIGURE):
                    (SRC_DIR / FIGURE).write_bytes(body)
            return out
    except urllib.error.HTTPError as e:
        return {"endpoint": path, "http_status": e.code, "ok": False}
    except Exception as e:  # noqa: BLE001
        return {"endpoint": path, "http_status": None, "error": type(e).__name__, "ok": False}


def main() -> int:
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps(
            {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    tok = json.load(urllib.request.urlopen(req))["access_token"]
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    results = [probe(p, tok) for p in ENDPOINTS]
    (SRC_DIR / "probes.json").write_text(json.dumps(results, ensure_ascii=False, indent=1))
    for r in results:
        print(r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
