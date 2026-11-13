"""Fetch the published report back and prove the delivery channel is intact.

Checks: title, tags contain kf-wp:wp-331-04, scenario_key, mission_id, markdown sha256 equals
the local rendered file, exactly one ```json block in the published body, and that block parses
to the local kf_result envelope; figures count and their sha256 match the local PNGs.
Writes runs/wp-331-04/published.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "kf" / "wp-331-04"
RUNS = ROOT / "runs" / "wp-331-04"


def main() -> int:
    rid = sys.argv[1] if len(sys.argv) > 1 else None
    if not rid:
        raise SystemExit("usage: verify_published.py <report_id>")
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    cred = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    tok = None
    for ep in ("/auth/login", "/tensor/login"):
        try:
            req = urllib.request.Request(base + ep, data=cred, method="POST",
                                         headers={"Content-Type": "application/json"})
            d = json.load(urllib.request.urlopen(req, timeout=30))
            tok = d.get("access_token") or d.get("token")
            if tok:
                break
        except Exception:
            continue
    req = urllib.request.Request(f"{base}/tensor/reports/{rid}",
                                 headers={"Authorization": "Bearer " + tok})
    rec = json.load(urllib.request.urlopen(req, timeout=60))

    local_md = (OUT / "KF-RESULT-wp-331-04.md").read_text(encoding="utf-8")
    env = json.loads((OUT / "kf_result.wp-331-04.json").read_text(encoding="utf-8"))
    figs = json.loads((OUT / "figures" / "figures.json").read_text(encoding="utf-8"))
    md = rec["markdown"]

    def figure_bytes(name: str) -> bytes:
        """Figure binaries are not in the record JSON; they are served one by one."""
        url = f"{base}/tensor/reports/{rid}/figures/{name}"
        return urllib.request.urlopen(
            urllib.request.Request(url, headers={"Authorization": "Bearer " + tok}), timeout=60).read()

    checks = {
        "title": rec.get("title") == "KF-RESULT wp-331-04",
        "tag": "kf-wp:wp-331-04" in (rec.get("tags") or []),
        "scenario_key": rec.get("scenario_key") == "dem_fem_coupling_hertz_cpu",
        "mission_id": str(rec.get("mission_id")) == "15788",
        "markdown_sha256": hashlib.sha256(md.encode()).hexdigest()
        == hashlib.sha256(local_md.encode()).hexdigest(),
        "single_json_block": md.count("```json") == 1,
        "envelope_roundtrip": json.loads(md.split("```json", 1)[1].split("```", 1)[0]) == env,
        "figures_count": len(rec.get("figures") or []) == len(figs),
        "figure_names": [f.get("name") for f in (rec.get("figures") or [])]
        == [f["name"] for f in figs],
        "figure_sha256": [hashlib.sha256(figure_bytes(f["name"])).hexdigest()
                          for f in (rec.get("figures") or [])] == [f["sha256"] for f in figs],
    }
    for k, v in checks.items():
        print(f"{k:<20} {'PASS' if v else 'FAIL'}")
    RUNS.mkdir(parents=True, exist_ok=True)
    (RUNS / "published.json").write_text(json.dumps({
        "report_id": rec.get("id"), "title": rec.get("title"), "status": rec.get("status"),
        "tags": rec.get("tags"), "scenario_key": rec.get("scenario_key"),
        "mission_id": rec.get("mission_id"), "summary_chars": len(rec.get("summary") or ""),
        "markdown_chars": len(md), "markdown_sha256": hashlib.sha256(md.encode()).hexdigest(),
        "figures": [{"name": f.get("name"), "caption": f.get("caption"),
                     "sha256": hashlib.sha256(figure_bytes(f["name"])).hexdigest()}
                    for f in (rec.get("figures") or [])],
        "checks": checks,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())