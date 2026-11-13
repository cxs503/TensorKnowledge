"""Fetch the source report for wp-331-04 (report_id=331) from the platform API.

Usage:  python3 scripts/kf_wp331_04/fetch_report.py --out /tmp/r331.md
Env:    TENSOR_API_BASE, TENSOR_AGENT_USER, TENSOR_AGENT_PASS
"""
import argparse
import hashlib
import json
import os
import urllib.request


def login(base, user, pw):
    body = json.dumps({"username": user, "password": pw}).encode()
    for ep in ("/tensor/login", "/auth/login", "/login"):
        try:
            req = urllib.request.Request(base + ep, data=body, method="POST",
                                         headers={"Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=30))
            tok = d.get("token") or d.get("access_token") or (d.get("data") or {}).get("token")
            if tok:
                return tok
        except Exception as exc:  # pragma: no cover - endpoint probing
            print(f"login fail {ep}: {exc}")
    raise SystemExit("could not obtain token")


def fetch(base, tok, report_id):
    for ep in (f"/tensor/reports/{report_id}", f"/reports/{report_id}"):
        try:
            req = urllib.request.Request(base + ep, headers={"Authorization": "Bearer " + tok})
            d = json.load(urllib.request.urlopen(req, timeout=60))
            md = d.get("markdown") or (d.get("data") or {}).get("markdown")
            if md:
                return md, d
        except Exception as exc:  # pragma: no cover - endpoint probing
            print(f"fetch fail {ep}: {exc}")
    raise SystemExit("could not fetch markdown")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/r331.md")
    ap.add_argument("--report-id", default="331")
    a = ap.parse_args()
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = login(base, os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"])
    md, record = fetch(base, tok, a.report_id)
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(md)
    print("chars:", len(md))
    print("sha256:", hashlib.sha256(md.encode("utf-8")).hexdigest())
    print("record keys:", sorted(record.keys()))
    print("title:", record.get("title"))
    print("scenario_key:", record.get("scenario_key"))


if __name__ == "__main__":
    main()