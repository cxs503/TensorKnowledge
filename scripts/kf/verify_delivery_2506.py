#!/usr/bin/env python3
"""交付自验（post-delivery）：把我方发布的本工作包报告读回来，独立复核门口径。

复核项（全部机器判定，不手填）：
1. 已发布报告的 markdown 里**只有一个** ```json 块，且该块与本地产物 kf_result.json 完全相等；
2. tags 含 `kf-wp:wp-2506-01`，title == `KF-RESULT wp-2506-01`，mission_id 正确；
3. provenance.source_hash 与源快照 markdown 的 UTF-8 字节 sha256 逐字节一致（平台会独立重算）；
4. 图件路由对照：对**本工序自己发布的报告**探 `GET /tensor/reports/<id>/figures/<name>.png`；
   同时对 report 2506 的同形路由再探一次并记录状态码——用于区分「路由形状不对」与
   「report 2506 的图件载荷在平台侧确实不存在」（后者才是缺口登记的理由）。

用法：python3 scripts/kf/verify_delivery_2506.py --report-id 14613
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = "wp-2506-01"
ART = ROOT / "artifacts" / "kf" / PKG
MIRROR = ROOT / "knowledge" / "kf" / PKG
PKG_TAG = "kf-wp:%s" % PKG


def api_base() -> str:
    return os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


def token() -> str:
    cred = json.dumps(
        {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    ).encode()
    d = json.load(urllib.request.urlopen(
        urllib.request.Request(api_base() + "/auth/login", data=cred,
                              headers={"Content-Type": "application/json"}), timeout=30))
    return d.get("access_token") or d.get("token")


def get_json(tok: str, path: str) -> dict:
    return json.load(urllib.request.urlopen(
        urllib.request.Request(api_base() + path, headers={"Authorization": "Bearer " + tok}),
        timeout=60))


def probe(tok: str, path: str) -> dict:
    try:
        r = urllib.request.urlopen(urllib.request.Request(
            api_base() + path, headers={"Authorization": "Bearer " + tok}), timeout=60)
        return {"endpoint": path, "http_status": r.status, "bytes": len(r.read())}
    except urllib.error.HTTPError as e:
        return {"endpoint": path, "http_status": e.code, "bytes": 0}
    except Exception as e:  # noqa: BLE001
        return {"endpoint": path, "http_status": None, "note": repr(e)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-id", required=True)
    args = ap.parse_args()

    env = json.loads((ART / "kf_result.json").read_text(encoding="utf-8"))
    snap = json.loads((ART / "source_snapshot" / "report_2506.json").read_text(encoding="utf-8"))
    src_md = snap["markdown"]
    recomputed = "sha256:" + hashlib.sha256(src_md.encode("utf-8")).hexdigest()

    tok = token()
    rec = get_json(tok, "/tensor/reports/" + args.report_id)
    md = rec.get("markdown") or ""
    blocks = md.split("```json")
    block = blocks[1].split("```", 1)[0] if len(blocks) > 1 else ""
    posted_env = json.loads(block) if block.strip() else None

    fig_name = (rec.get("figures") or [{}])[0].get("name") if rec.get("figures") else None
    our_fig = probe(tok, "/tensor/reports/%s/figures/%s" % (args.report_id, fig_name)) if fig_name else None
    upstream_fig = probe(tok, "/tensor/reports/2506/figures/dissipativity-sweep.png")

    def strip_ts(doc):
        """比对时剔除发射时间戳（generated_at / provenance.emitted_at）：重跑必然刷新，但不属内容。"""
        if doc is None:
            return None
        d = json.loads(json.dumps(doc))
        d.pop("generated_at", None)
        d.get("provenance", {}).pop("emitted_at", None)
        d.get("outputs", {}).get("asset_manifest.json", {}).pop("generated_at", None)
        return d

    checks = {
        "single_json_block": md.count("```json") == 1,
        "json_block_equals_local_envelope": strip_ts(posted_env) == strip_ts(env),
        "tags_contain_package_tag": PKG_TAG in (rec.get("tags") or []),
        "title_ok": rec.get("title") == "KF-RESULT " + PKG,
        "mission_id_ok": rec.get("mission_id") == 15532,
        "provenance_hash_matches_source_snapshot": (
            (posted_env or {}).get("provenance", {}).get("source_hash") == recomputed
        ),
        "provenance_hash_equals_contract": (
            (posted_env or {}).get("provenance", {}).get("source_hash")
            == env["provenance"]["source_hash"]
        ),
        "figure_route_shape_valid_control": bool(our_fig and our_fig.get("http_status") == 200),
        "upstream_2506_figure_still_unreachable": bool(
            upstream_fig and upstream_fig.get("http_status") == 404
        ),
    }
    out = {
        "package_id": PKG,
        "published_report_id": args.report_id,
        "verified_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "recomputed_source_sha256": recomputed,
        "checks": checks,
        "all_pass": all(checks.values()),
        "figure_probes": {"own_report": our_fig, "upstream_2506": upstream_fig},
        "note": ("post-delivery 自验：把发布后的报告读回来独立复核唯一 json 块、tags、mission_id、"
                 "provenance 哈希；图件路由以本工序自己发布的报告作对照（200），"
                 "据此判定 report 2506 图件 404 属上游载荷缺失而非路由形状问题。"),
    }
    (ART / "delivery_verification.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if (ART / "delivery_verification.json").exists():
        MIRROR.mkdir(parents=True, exist_ok=True)
        (MIRROR / "delivery_verification.json").write_text(
            (ART / "delivery_verification.json").read_text(encoding="utf-8"), encoding="utf-8")
    print(json.dumps({"all_pass": out["all_pass"],
                      "failed": [k for k, v in checks.items() if not v]}, ensure_ascii=False))
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())