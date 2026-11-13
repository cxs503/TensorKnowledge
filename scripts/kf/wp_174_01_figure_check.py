#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""图件回读校验：平台 JSON 只回显图名、不回显 png_base64（实测），因此必须独立回读字节，
否则「图件存在」就成了自述。本脚本：
  1) 用 package_id 找**最新**一条 KF-RESULT 报告（与平台 store.find_result_report 同口径：tags 含 kf-wp:<pkg>）；
  2) 取该报告 figures[].name，GET /tensor/reports/<id>/figures/<name> 取字节；
  3) 与工作树内本地 PNG 比 sha256；
  4) 落 artifacts/kf/wp-174-01/figure_check.json（供报告程序化注入，零手抄）。

用法：python3 scripts/kf/wp_174_01_figure_check.py
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-174-01")
LOCAL_FIG = os.path.join(PKG, "figures", "wp-174-01_section_index.png")
PACKAGE_ID = "wp-174-01"


def api(path, body=None, token=None):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        base + path, data=None if body is None else json.dumps(body).encode(), headers=headers
    )
    return json.load(urllib.request.urlopen(req))


def raw(path, token):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + token})
    return urllib.request.urlopen(req).read()


def main() -> int:
    tok = api("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                              "password": os.environ["TENSOR_AGENT_PASS"]})
    tok = tok.get("access_token") or tok.get("token")

    # 与平台 find_result_report 同口径：tag 精确匹配，取 id 最大的一条
    listing = api("/tensor/reports?q=" + PACKAGE_ID + "&limit=200", token=tok)
    candidates = [r for r in listing.get("items", [])
                  if ("kf-wp:" + PACKAGE_ID) in (r.get("tags") or [])]
    if not candidates:
        raise SystemExit("no KF-RESULT report found for %s" % PACKAGE_ID)
    latest = max(candidates, key=lambda r: int(r["id"]))
    rec = api("/tensor/reports/%d" % int(latest["id"]), token=tok)
    figs = rec.get("figures") or []
    local_bytes = open(LOCAL_FIG, "rb").read()
    local_sha = hashlib.sha256(local_bytes).hexdigest()

    items = []
    for f in figs:
        name = f.get("name")
        remote = raw("/tensor/reports/%d/figures/%s" % (int(latest["id"]), name), tok)
        items.append({
            "name": name,
            "png_base64_in_json": bool(f.get("png_base64")),
            "remote_bytes": len(remote),
            "remote_sha256": hashlib.sha256(remote).hexdigest(),
            "png_magic_ok": remote[:4] == b"\x89PNG",
        })
    out = {
        "checked_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "result_report_id_checked": int(latest["id"]),
        "figure_api_path_template": "/tensor/reports/<id>/figures/<name>",
        "platform_json_returns_png_base64": any(i["png_base64_in_json"] for i in items),
        "n_figures": len(items),
        "remote_items": items,
        "local_bytes": len(local_bytes),
        "local_sha256": local_sha,
        "bytes_identical_to_local": all(
            i["remote_sha256"] == local_sha and i["remote_bytes"] == len(local_bytes) for i in items
        ) and len(items) > 0,
        "note": "平台 JSON 不回显 png_base64，故图件存在性用回读字节 sha256 证明，而非自述",
    }
    with open(os.path.join(PKG, "figure_check.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({k: out[k] for k in ("result_report_id_checked", "n_figures",
                                          "bytes_identical_to_local",
                                          "platform_json_returns_png_base64")},
                     ensure_ascii=False))
    return 0 if out["bytes_identical_to_local"] else 1


if __name__ == "__main__":
    raise SystemExit(main())