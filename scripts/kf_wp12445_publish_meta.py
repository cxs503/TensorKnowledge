"""Pin the published KF-RESULT report id for wp-12445-01 and record its live metadata.

Usage: python3 scripts/kf_wp12445_publish_meta.py 14846
"""
import json, os, pathlib, sys, urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _req(BASE + path, {"username": u, "password": p})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main():
    rid = int(sys.argv[1])
    d = _req(BASE + "/tensor/reports/" + str(rid), token=login())
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    meta = {"kf_result_report_id": d.get("id"), "title": d.get("title"),
            "mission_id": d.get("mission_id"), "tags": d.get("tags"),
            "markdown_chars": len(d.get("markdown") or ""),
            "figures": [f.get("name") for f in (d.get("figures") or [])]}
    out = pathlib.Path("runs/wp-12445-01/published.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(meta, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
