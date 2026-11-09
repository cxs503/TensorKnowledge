"""POST /tensor/reports with fallback payload shapes; prints the server's error body.

Used because the report schema on the server is not self-documenting from the
client side: if the first shape is rejected (422) we try the documented subset,
then a shape without figures, and print every response body so the failure is
diagnosable instead of guessed.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def call(path: str, body: dict, tok: str | None = None, timeout: int = 90):
    h = {"Content-Type": "application/json"}
    if tok:
        h["Authorization"] = f"Bearer {tok}"
    req = urllib.request.Request(API + path, data=json.dumps(body).encode(), headers=h)
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read().decode()[:400]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:600]
    except Exception as e:  # noqa: BLE001
        return -1, repr(e)[:200]


def main() -> None:
    status, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                        "password": os.environ["TENSOR_AGENT_PASS"]})
    assert status == 200, (status, body)
    tok = json.loads(body if len(body) < 400 else "{}").get("access_token")
    if not tok:  # body was truncated for display; re-request untruncated
        req = urllib.request.Request(
            API + "/auth/login",
            data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                             "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
            headers={"Content-Type": "application/json"})
        tok = json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]

    p = json.load(open("/tmp/report_8618.json"))
    variants = [
        ("full", p),
        ("no_figures", {k: v for k, v in p.items() if k != "figures"}),
        ("minimal", {k: p[k] for k in ("title", "summary", "scenario_key", "mission_id",
                                       "markdown")}),
        ("mission_str", {**p, "mission_id": str(p["mission_id"])}),
    ]
    for name, body in variants:
        st, resp = call("/tensor/reports", body, tok)
        print(f"[{name}] {st} {resp[:300]}")
        if st in (200, 201):
            print("posted variant:", name)
            return


if __name__ == "__main__":
    main()