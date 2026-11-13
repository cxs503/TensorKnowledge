#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""wp-174-01 平台门复算：用**平台仓原版** ops/knowledge_factory/gates.py（只读引用）跑一遍
structure_gate + evidence_gate，验证「报告 markdown → 唯一 json 块 → 门」端到端可用。

与 scripts/kf/wp_174_01_verify.py 的分工：
  * verify.py = 本包自检（独立实现在先，防止门本身有 bug 时自欺）；
  * 本脚本 = 与平台门对表（防止自检实现与平台口径漂移）。

用法：
  python3 scripts/kf/wp_174_01_gate_replica.py [--gates <path/to/gates.py>]
默认 gates 路径取 $TENSOR_KF_GATES 或平台检出 ../m15495/ops/knowledge_factory/gates.py（只读）。
产物：artifacts/kf/wp-174-01/gate_replica.json
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-174-01")
REPORT_MD = os.path.join(ROOT, "reports", "kf-results", "wp-174-01.md")
DEFAULT_GATES = os.environ.get(
    "TENSOR_KF_GATES",
    "/root/tp-agent/work/m15495/ops/knowledge_factory/gates.py",
)


def api(path, body=None, token=None):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(
        base + path, data=None if body is None else json.dumps(body).encode(), headers=headers
    )
    return json.load(urllib.request.urlopen(req))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gates", default=DEFAULT_GATES)
    args = ap.parse_args()
    if not os.path.exists(args.gates):
        print("gates.py 不存在（平台检出缺失）：%s —— 如实记 not_run" % args.gates)
        out = {"not_run": True, "reason": "gates.py not found: %s" % args.gates,
               "note": "自检 scripts/kf/wp_174_01_verify.py 仍独立可跑；平台门最终裁决"}
        json.dump(out, open(os.path.join(PKG, "gate_replica.json"), "w"),
                  ensure_ascii=False, indent=2)
        return 0

    spec = importlib.util.spec_from_file_location("kf_gates", args.gates)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)

    md_report = open(REPORT_MD, encoding="utf-8").read()
    obj, err = g.extract_payload(md_report)

    tok = api("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                              "password": os.environ["TENSOR_AGENT_PASS"]})
    tok = tok.get("access_token") or tok.get("token")
    src_md = api("/tensor/reports/174", token=tok)["markdown"]

    pkg = {"package_id": "wp-174-01", "report_id": "174", "task_type": "01"}
    sg, sok = g.structure_gate(obj, pkg=pkg)
    eg, eok, stats = g.evidence_gate(obj, src_md, seen_claim_ids=set(),
                                     min_quote_chars=12, expected_report_id="174")
    envelope = json.load(open(os.path.join(PKG, "kf_result.json"), encoding="utf-8"))
    out = {
        "package_id": "wp-174-01",
        "run_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "gate_source": args.gates,
        "gate_source_note": "平台仓原版代码只读引用，未修改",
        "extract_payload_error": err,
        "envelope_equals_kf_result_json": obj == envelope,
        "structure_gate": {"ok": sok, "gates": sg},
        "evidence_gate": {"ok": eok, "gates": eg, "stats": stats},
        "vacuous_g5_note": ("claims=[] ⇒ g5 checked=0 属空洞通过；本包以报告定位表 + "
                            "asset_manifest.locator_quote 提供非空洞证据密度"),
        "ok": bool(err is None and sok and eok and obj == envelope),
    }
    with open(os.path.join(PKG, "gate_replica.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("end2end ok =", out["ok"], "| structure", sok, "| evidence", eok, "| stats", stats)
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())