"""List platform reports filtered by tag/substring, to locate upstream package products.

Usage: python3 scripts/kf_wp331_04/list_reports.py --tag kf-wp:wp-331 --limit 50
"""
import argparse
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
        except Exception:
            continue
    raise SystemExit("no token")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--raw", action="store_true")
    a = ap.parse_args()
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    tok = login(base, os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"])
    url = f"{base}/tensor/reports?limit={a.limit}"
    if a.tag:
        url += "&tag=" + urllib.parse.quote(a.tag)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    rows = d if isinstance(d, list) else (d.get("items") or d.get("reports") or d.get("data") or [])
    if a.raw:
        print(json.dumps(d, ensure_ascii=False)[:3000])
        return
    print("n =", len(rows))
    for r in rows:
        tags = r.get("tags") or []
        hit = (not a.tag) or any(a.tag in str(t) for t in tags)
        if hit:
            print(r.get("id"), "|", " ".join(map(str, tags))[:90], "|", str(r.get("title"))[:80])


if __name__ == "__main__":
    import urllib.parse
    main()