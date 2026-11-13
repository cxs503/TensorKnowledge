#!/usr/bin/env python3
"""wp-331-01 门干跑（dry-run）：用**平台自己的门代码**校验本工序结果块。

不是替代平台门——平台会独立再重算一次哈希与定位；这里只是让工作树内的产物在
提交前就能被同一份门代码扫一遍，把「结构/身份/哈希/定位/去重」的失败挡在推送前。

依赖：平台 knowledge_factory 门模块（默认取工作树路径，可用 --kf-ops 覆盖）。
找不到门代码时不伪造结论：直接以 exit 3 退出并打印 degraded 理由。

用法：
  python3 scripts/kf_wp331_01_gate_dryrun.py \
      --kf-ops /root/tp-agent/work/m15495/ops \
      --out artifacts/kf/wp-331-01/gate_dryrun.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "331"
DEFAULT_KF_OPS = "/root/tp-agent/work/m15495/ops"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kf-ops", default=os.environ.get("KF_OPS_DIR", DEFAULT_KF_OPS))
    ap.add_argument("--manifest", default=str(ROOT / "docs/kf/wp-331-01/asset_manifest.json"))
    ap.add_argument("--snapshot", default=str(
        ROOT / f"docs/kf/wp-331-01/source_snapshot/report_{REPORT_ID}.markdown"))
    ap.add_argument("--envelope", default="/tmp/kf_env331.json")
    ap.add_argument("--report-md", default=str(
        ROOT / "docs/kf/wp-331-01-asset-registration.md"))
    ap.add_argument("--out", default=str(ROOT / "docs/kf/wp-331-01/gate_dryrun.json"))
    a = ap.parse_args(argv)

    if not Path(a.kf_ops, "knowledge_factory", "gates.py").is_file():
        print(f"degraded: knowledge_factory gates not found under {a.kf_ops}", file=sys.stderr)
        Path(a.out).write_text(json.dumps({
            "status": "degraded", "reason": f"gates module not found under {a.kf_ops}",
            "run_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 3

    sys.path.insert(0, a.kf_ops)
    from knowledge_factory import contract as kc, gates  # noqa: E402

    cfg = kc.load_config()
    contracts = kc.load_contracts(cfg)
    md = Path(a.snapshot).read_text(encoding="utf-8")
    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    doc = Path(a.report_md).read_text(encoding="utf-8")

    pkg = kc.build_package(
        {"id": int(REPORT_ID), "title": manifest["source"]["title_record"],
         "scenario_key": manifest["source"]["scenario_key"], "markdown": md},
        "01", "C", cfg, contracts)

    obj, err = gates.extract_payload(doc)
    env_file = json.loads(Path(a.envelope).read_text(encoding="utf-8")) if Path(
        a.envelope).is_file() else None

    sg, sok = gates.structure_gate(obj, gates.load_schema(), pkg)
    eg, eok, stats = gates.evidence_gate(obj, md, set(), cfg["gates"]["min_quote_chars"],
                                         expected_report_id=REPORT_ID)
    all_gates = sg + eg
    rec = {
        "status": "ok",
        "run_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "kf_ops": a.kf_ops,
        "gate_code_sha256": hashlib.sha256(
            Path(a.kf_ops, "knowledge_factory", "gates.py").read_bytes()).hexdigest(),
        "schema_sha256": hashlib.sha256(
            Path(a.kf_ops, "..", "schemas", "kf_result.v1.schema.json")
            .resolve().read_bytes()).hexdigest(),
        "package": {k: pkg[k] for k in ("package_id", "task_type", "lane")},
        "contract_hash_matches_source": pkg["input"]["source_hash"] == gates.sha256_text(md),
        "extract_payload_error": err,
        "payload_equals_envelope_file": (obj == env_file) if env_file is not None else None,
        "gates": all_gates,
        "gates_ok": sok and eok,
        "stats": stats,
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for g in all_gates:
        print(("PASS " if g["ok"] else "FAIL "), g["gate"],
              {k: v for k, v in g.items() if k not in ("gate", "ok")})
    print(f"GATES_OK={rec['gates_ok']}  written={a.out}")
    return 0 if rec["gates_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())