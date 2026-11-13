#!/usr/bin/env python3
"""Probe platform for upstream work packages of a report_id (read-only).

Tries a few documented-looking endpoints and prints what resolves. Used to
establish the acceptance item `upstream_packages_completed` for wp-5716-04
without touching any report of another id.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def token(base):
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        j = json.loads(r.read().decode())
    return j.get("access_token") or j.get("token")


def get(base, tok, path):
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]
    except Exception as e:  # noqa: BLE001
        return -1, repr(e)


def main() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = token(base)
    report_id = sys.argv[1] if len(sys.argv) > 1 else "5716"
    for path in (
        f"/tensor/reports/{report_id}/packages",
        f"/tensor/work_packages?report_id={report_id}",
        f"/tensor/reports?report_id={report_id}",
        f"/tensor/reports?search=wp-{report_id}",
        f"/kf/packages?report_id={report_id}",
        "/tensor/reports?limit=3",
    ):
        st, js = get(base, tok, path)
        head = json.dumps(js, ensure_ascii=False)[:300] if not isinstance(js, str) else js
        print(f"{path} -> {st} :: {head}")
    return 0


if __name__ == "__main__":
    sys.exit(main())