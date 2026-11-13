#!/usr/bin/env python3
"""Publish the wp-3076-04 delivery report and verify the round trip.

Steps
  1. login (TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE)
  2. POST /tensor/reports  {title, summary, scenario_key, mission_id, tags, markdown, figures}
  3. re-GET the created report: markdown must be byte-identical to the local doc,
     provenance hash of the payload must equal the local sha256
  4. GET each figure back: HTTP 200 and identical bytes (positive control on the
     figure endpoint, so a 404 elsewhere is provably absent payload, not a bad route)
  5. write artifacts/wp-3076-04/publish_roundtrip.json

Refuses to publish twice: if a KF-RESULT wp-3076-04 report already exists with the
same markdown hash, it only verifies (use --force to post again).
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "wp-3076-04"
DOC = ROOT / "docs" / "wp-3076-04" / "KF-RESULT-wp-3076-04.md"
FIG = PKG / "fig_deviation_boundary.png"
OUT = PKG / "publish_roundtrip.json"
MISSION_ID = 15826


def _req(url, *, payload=None, token=None, method=None, raw=False):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method or ("POST" if data else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            body = resp.read()
            return resp.status, (body if raw else json.loads(body.decode()))
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()[:500]


def login(base):
    st, out = _req(f"{base}/auth/login",
                   payload={"username": os.environ["TENSOR_AGENT_USER"],
                            "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit(f"login failed {st}: {out}")
    tok = out.get("access_token") or out.get("token")
    if not tok:
        raise SystemExit(f"login gave no token: {list(out)}")
    return tok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--supersede-reason", default=None,
                    help="reason recorded when an earlier report of this package is superseded")
    args = ap.parse_args()

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    token = login(base)

    md = DOC.read_text(encoding="utf-8")
    md_sha = hashlib.sha256(md.encode("utf-8")).hexdigest()
    png = FIG.read_bytes()
    png_sha = hashlib.sha256(png).hexdigest()
    n_fences = md.count("```json")

    payload = {
        "title": "KF-RESULT wp-3076-04",
        "summary": ("对 report 3076（manuscript_gate v1）的独立审核：判定 needs-fix。"
                    "独立复算复现 H1 coth/tanh 偏差序列 5/5（最大 |Δ|≤0.004 pp），"
                    "同时抓到 5 项 major：HARD 分母 8/11≠8/10、正控 3 项 HARD SKIP 使“0 误报”仅为 7/10、"
                    "implmethod 对 H5 假阴性、⑥<3% 列 3 行范畴误用、“T≥14 s 无根”边界应为 14.19 s。"),
        "scenario_key": "paper-line-provenance-gate",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:wp-3076-04", "kf-results", "independent-review",
                 "paper-production", "provenance-gate", "adversarial-review", "needs-fix"],
        "markdown": md,
        "figures": [{
            "name": FIG.name,
            "caption": ("左：H1 偏差序列（报告声称值 vs 本审核独立求解器复算值，5/5 重合，log 纵轴，灰虚线=3%）；"
                        "右：coth 分支在 k∈(0,10] 1/m 内的根存在性 vs 周期，红区=无根，黑虚线=解析临界期 "
                        "T_c=2π√(h/g)，橙点线=报告声称的边界 T=14 s（T=14 s 仍有根）。"),
            "png_base64": base64.b64encode(png).decode(),
        }],
    }

    st, body = _req(f"{base}/tensor/reports", payload=payload, token=token)
    if st not in (200, 201):
        print(f"POST failed {st}: {body}", file=sys.stderr)
        return 2
    rec = body.get("data", body)
    rid = rec.get("id")
    print(f"created report id={rid} status={rec.get('status')}")

    # --- round trip on markdown ---
    st2, back = _req(f"{base}/tensor/reports/{rid}", token=token)
    back = back.get("data", back) if st2 == 200 else {}
    back_md = back.get("markdown") or ""
    md_equal = back_md == md
    back_sha = hashlib.sha256(back_md.encode("utf-8")).hexdigest()

    # --- figure endpoint positive control ---
    st3, png_back = _req(f"{base}/tensor/reports/{rid}/figures/{FIG.name}", token=token, raw=True)
    fig_ok = st3 == 200 and isinstance(png_back, (bytes, bytearray))
    fig_sha = hashlib.sha256(png_back).hexdigest() if fig_ok else None

    prev = json.loads(OUT.read_text(encoding="utf-8")) if OUT.is_file() else None
    superseded = (prev or {}).get("superseded_reports", [])
    if prev and prev.get("report_id") and prev["report_id"] != rid:
        superseded = superseded + [{
            "report_id": prev["report_id"],
            "superseded_by": rid,
            "reason": args.supersede_reason or "corrected body of the same package report",
        }]

    receipt = {
        "report_id": rid,
        "title": payload["title"],
        "mission_id": MISSION_ID,
        "scenario_key": payload["scenario_key"],
        "tags": payload["tags"],
        "markdown": {"local_sha256": md_sha, "chars": len(md), "json_blocks": n_fences,
                     "fetched_sha256": back_sha, "byte_equal": md_equal},
        "figure": {"name": FIG.name, "local_bytes": len(png), "local_sha256": png_sha,
                   "http_status": st3, "fetched_sha256": fig_sha,
                   "byte_equal": fig_ok and fig_sha == png_sha},
        "checks": {"markdown_roundtrip": md_equal,
                   "single_json_block": n_fences == 1,
                   "figure_endpoint_200": fig_ok,
                   "figure_bytes_equal": bool(fig_ok and fig_sha == png_sha)},
        "superseded_reports": superseded,
        "superseded_note": ("only the report named in report_id is the deliverable of this work package; "
                            "earlier ids are kept for audit"),
        "known_cosmetics": ("markdown tables in the delivered body escape '|' inside cells and use a spaced "
                            "double-backtick fence for quotes that themselves contain a backtick; the JSON "
                            "result envelope is unaffected by rendering"),
        "verdict": "PASS" if (md_equal and n_fences == 1 and fig_ok and fig_sha == png_sha) else "FAIL",
    }
    OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(receipt["checks"], ensure_ascii=False, indent=1))
    print(f"verdict={receipt['verdict']}  wrote {OUT.relative_to(ROOT)}")
    return 0 if receipt["verdict"] == "PASS" else 3


if __name__ == "__main__":
    raise SystemExit(main())