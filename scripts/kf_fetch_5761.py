#!/usr/bin/env python3
"""Fetch tensor report 5761 markdown through the platform API and pin its byte hash.

Work package: wp-5761-01 (task_type=01-asset-registration).
Writes:
  runs/wp-5761-01/report_5761.markdown   verbatim markdown (source of truth for locators)
  runs/wp-5761-01/report_5761.meta.json  platform record fields + local hash recomputation

No judgement is made here (no classification, no extraction) per PRODUCTION-LINE-v1 §2.1.
Credentials come from the environment only; nothing is persisted.
"""
import hashlib
import json
import os
import sys
import urllib.request

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
RID = "5761"
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "runs", "wp-5761-01")


def _post_json(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _get_json(url, token):
    req = urllib.request.Request(url)
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    last = None
    for path in ("/tensor/auth/login", "/auth/login", "/tensor/login"):
        try:
            d = _post_json(BASE + path, {"username": USER, "password": PASS})
        except Exception as e:  # noqa: BLE001
            last = e
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
        last = RuntimeError("no token field in %s: %s" % (path, list(d)[:8]))
    raise SystemExit("login failed: %s" % last)


def main():
    tok = login()
    rec = _get_json("%s/tensor/reports/%s" % (BASE, RID), tok)
    rec = rec.get("data", rec) if isinstance(rec, dict) else rec
    md = rec["markdown"]
    raw = md.encode("utf-8")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "report_5761.markdown"), "w", encoding="utf-8") as f:
        f.write(md)
    meta = {
        "report_id": rec.get("id"),
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "status": rec.get("status"),
        "created_at": rec.get("created_at"),
        "updated_at": rec.get("updated_at"),
        "tags": rec.get("tags"),
        "mission_id": rec.get("mission_id"),
        "source_field": "markdown",
        "chars": len(md),
        "bytes_utf8": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "figures": rec.get("figures"),
        "fields_present": sorted(rec.keys()),
    }
    with open(os.path.join(OUT, "report_5761.meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(json.dumps({k: meta[k] for k in ("report_id", "chars", "bytes_utf8", "sha256")},
                     ensure_ascii=False))


if __name__ == "__main__":
    sys.exit(main())