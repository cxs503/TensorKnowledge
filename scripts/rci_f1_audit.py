#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 预注册顺序审计：prereg 报告时间戳必须早于三臂 mission 创建时刻。

预注册的全部意义在于「先声明后执行」。本脚本从平台读取事实并落盘
artifacts/rci-f1-abc/prereg_ordering_audit.json，作为可复核证据（不是自述）。

用法: python scripts/rci_f1_audit.py --dir artifacts/rci-f1-abc [--mission 15496]
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


def get(path: str) -> dict:
    tok = os.environ.get("TP_TOKEN") or open("/tmp/tok_m15496").read().strip()
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + tok})
    return json.loads(urllib.request.urlopen(req, timeout=30).read())


def audit(dir_: str, mission: int) -> dict:
    disp = json.load(open(os.path.normpath(os.path.join(dir_, "../../runs/rci-f1-abc/dispatch.json")),
                          encoding="utf-8"))
    reps = get(f"/tensor/reports?mission_id={mission}")
    items = reps.get("items", reps if isinstance(reps, list) else [])
    prereg = [r for r in items if "prereg" in (r.get("tags") or [])]
    arms = []
    for d in disp.get("dispatch", []):
        mid = d.get("mission_id")
        if not mid:
            continue
        m = get(f"/tensor/missions/{mid}")
        arms.append({"lane": d["lane"], "mission_id": mid, "model": d.get("model"),
                     "status": m.get("status"), "created_at": m.get("created_at"),
                     "claimed_by": m.get("claimed_by"),
                     "goal_sha256": d.get("goal_sha256")})
    prereg_at = max(r["created_at"] for r in prereg) if prereg else None
    ok = bool(prereg_at) and all(a["created_at"] and a["created_at"] > prereg_at for a in arms)
    result = {"anchor": "KBM-RCI-F1-ABC", "prereg_report": {
        "ids": [r["id"] for r in prereg], "latest_created_at": prereg_at},
        "arms": arms, "prereg_precedes_all_arms": ok,
        "dispatch_generated_at": disp.get("generated_at"),
        "note": "prereg 报告先于臂创建 = 指标/阈值确实在执行前冻结；时间戳来自平台，不自述"}
    with open(os.path.join(dir_, "prereg_ordering_audit.json"), "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/rci-f1-abc")
    ap.add_argument("--mission", type=int, default=15496)
    args = ap.parse_args()
    r = audit(args.dir, args.mission)
    print(json.dumps({"prereg_at": r["prereg_report"]["latest_created_at"],
                      "arms": [(a["lane"], a["mission_id"], a["created_at"], a["status"]) for a in r["arms"]],
                      "ordering_ok": r["prereg_precedes_all_arms"]}, ensure_ascii=False, indent=1))
    raise SystemExit(0 if r["prereg_precedes_all_arms"] else 3)


if __name__ == "__main__":
    main()