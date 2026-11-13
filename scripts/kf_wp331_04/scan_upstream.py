"""Scan platform reports client-side for a work-package tag (server ignores tag filter)."""
import json
import os
import urllib.request

base = os.environ["TENSOR_API_BASE"].rstrip("/")


def login():
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    for ep in ("/tensor/login", "/auth/login"):
        try:
            r = urllib.request.Request(base + ep, data=body, method="POST",
                                       headers={"Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(r, timeout=20))
            t = d.get("token") or d.get("access_token")
            if t:
                return t
        except Exception:
            pass
    raise SystemExit("no token")


tok = login()
needle = "wp-331"
seen, hits = 0, []
for offset in range(0, 40000, 2000):
    url = f"{base}/tensor/reports?limit=2000&offset={offset}"
    try:
        r = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
        d = json.load(urllib.request.urlopen(r, timeout=120))
    except Exception as exc:
        print("page fail", offset, exc)
        break
    items = d.get("items") or d
    if not items:
        break
    for it in items:
        seen += 1
        blob = " ".join(str(x) for x in (it.get("tags") or [])) + " " + str(it.get("title"))
        if needle in blob:
            hits.append((it.get("id"), it.get("title"), it.get("tags")))
    print("offset", offset, "seen", seen, "hits", len(hits))
    if len(items) < 2000:
        break
print("TOTAL seen", seen)
for h in hits:
    print(h)
json.dump(hits, open("/root/tp-agent/work/m15788/runs/wp-331-04/tag_hits.json", "w"), ensure_ascii=False)