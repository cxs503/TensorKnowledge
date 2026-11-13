"""Publish the wp-331-04 delivery markdown as a platform report (single result channel).

POST $TENSOR_API_BASE/tensor/reports with title/summary/scenario_key/mission_id/tags/
markdown/figures. The markdown is the rendered KF-RESULT file, which carries exactly one
```json block = the kf_result envelope. Run after build_review.py + render_result.py.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "kf" / "wp-331-04"


def main() -> int:
    dry = "--dry-run" in sys.argv
    md = (OUT / "KF-RESULT-wp-331-04.md").read_text(encoding="utf-8")
    figs = json.loads((OUT / "figures" / "figures.json").read_text(encoding="utf-8"))
    for f in figs:  # binaries live next to the metadata; embed at post time
        png = OUT / "figures" / f["file"]
        assert hashlib.sha256(png.read_bytes()).hexdigest() == f["sha256"], f["file"]
        f["png_base64"] = base64.b64encode(png.read_bytes()).decode("ascii")
    rev = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))

    payload = {
        "title": "KF-RESULT wp-331-04",
        "summary": (
            "wp-331-04 (04-independent-review, report 331): needs-fix; supersedes probe 14902. Source sha256 "
            "byte-equal to contract (1371 chars), 29/29 verbatim quotes. Blocker: upstream wp-331-01 unreachable on "
            "4 channels -> upstream_packages_completed=FALSE, fidelity unauditable. 5 majors: Hertz fit at delta/R=0.5 "
            "outside validity; 'lattice cannot do Hertz' confounded; sole PASS (beam 0.0125%) unverifiable; 58.6% energy "
            "drift; schema artifact missing. Honest-FAILs arithmetic-consistent; nothing verified."),
        "scenario_key": "dem_fem_coupling_hertz_cpu",
        "mission_id": 15788,
        "tags": ["kf-wp:wp-331-04", "04-independent-review", "report:331", "lane:C", "in-review",
                 "kf-stage-04", "verdict:needs-fix"],
        "markdown": md,
        "figures": [{"name": f["name"], "caption": f["caption"], "png_base64": f["png_base64"]}
                    for f in figs],
    }
    assert len(payload["summary"]) <= 500, len(payload["summary"])  # API limit, learned the hard way
    body = json.dumps(payload).encode()
    print("payload bytes:", len(body), "figures:", len(payload["figures"]),
          "verdict:", rev["verdict"])
    if dry:
        print("dry-run: not posted")
        return 0

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
    if not tok:
        raise SystemExit("login failed")
    req = urllib.request.Request(base + "/tensor/reports", data=body, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    d = json.load(urllib.request.urlopen(req, timeout=180))
    print("posted:", json.dumps({k: d.get(k) for k in ("id", "title", "status", "stage", "scenario_key")},
                                ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())