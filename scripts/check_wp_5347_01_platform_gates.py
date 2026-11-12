#!/usr/bin/env python3
"""Optional cross-check: run the *platform* gate module against this package.

The authoritative judgement belongs to the platform (``kf/ops/knowledge_factory/
gates.py``: structure gate + evidence gate).  This script imports that module
read-only when it is present (``$KF_OPS_DIR``, default
``/root/tp-agent/kf/ops``) and replays its checks on the artefacts emitted here,
so a local green is the platform's own definition of green rather than mine.

Exit 0 iff every platform gate returns ok (or the module is absent -> "not_run",
exit 0 with an explicit note; absence is not a pass).

Usage: python3 scripts/check_wp_5347_01_platform_gates.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "artifacts" / "wp-5347-01"
if not PKG.is_dir():  # committed snapshot: artifacts/** is git-ignored
    PKG = REPO / "docs" / "production" / "wp-5347-01"
OPS = Path(os.environ.get("KF_OPS_DIR", "/root/tp-agent/kf/ops"))

CONTRACT = {
    "package_id": "wp-5347-01",
    "report_id": "5347",
    "task_type": "01-asset-registration",
}


def main() -> int:
    out_path = PKG / "platform_gate.json"
    if not (OPS / "knowledge_factory" / "gates.py").is_file():
        doc = {"ok": None, "status": "not_run",
               "reason": f"platform gate module not present under {OPS}"}
        out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n",
                            encoding="utf-8")
        print(json.dumps(doc, ensure_ascii=False))
        return 0

    sys.path.insert(0, str(OPS))
    from knowledge_factory import gates  # noqa: E402  (read-only reuse)

    payload, err = gates.extract_payload((PKG / "KF-RESULT-wp-5347-01.md").read_text(
        encoding="utf-8"))
    if err:
        print(json.dumps({"ok": False, "extract_error": err}, ensure_ascii=False))
        return 1
    source_md = (PKG / "report_5347.md").read_text(encoding="utf-8")

    struct, struct_ok = gates.structure_gate(payload, pkg=CONTRACT)
    ev, ev_ok, stats = gates.evidence_gate(payload, source_md, expected_report_id="5347")
    doc = {
        "ok": bool(struct_ok and ev_ok),
        "platform_gate_module": str(OPS / "knowledge_factory" / "gates.py"),
        "structure": struct,
        "structure_ok": struct_ok,
        "evidence": ev,
        "evidence_ok": ev_ok,
        "evidence_stats": stats,
        "note": ("claims=0 时 g5/g5b/g6 为空真：stats.locator_rate=None 表示无可定位 claim，"
                 "平台按“零 claim 合法”处理，不得读作定位率 100%"),
    }
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["ok"], "structure_ok": struct_ok, "evidence_ok": ev_ok,
                      "stats": stats}, ensure_ascii=False))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())