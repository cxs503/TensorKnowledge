#!/usr/bin/env python3
"""把派单结果与臂执行状态写进可变的 status 台账（保持预注册的 tk_work_packages.json 不可变）。

为什么分开：预注册里记录了 tk_work_packages.json 的 sha256；执行期状态必须可变，
所以台账只读、状态另存（workpackage_status.json）。

用法:
  python scripts/rci_f1_status.py --dir artifacts/rci-f1-abc            # 从 dispatch.json 初始化/刷新
  python scripts/rci_f1_status.py --dir artifacts/rci-f1-abc --refresh   # 读 runs/ 与 mission 状态刷新
"""
from __future__ import annotations

import argparse
import glob
import json
import os
from datetime import datetime, timezone


def load(path: str, default):
    if os.path.isfile(path):
        return json.load(open(path, encoding="utf-8"))
    return default


def refresh(dir_: str, do_network: bool = False) -> dict:
    wps = json.load(open(os.path.join(dir_, "tk_work_packages.json"), encoding="utf-8"))
    dpath = os.path.normpath(os.path.join(dir_, "../../runs/rci-f1-abc/dispatch.json"))
    disp = load(dpath, {"dispatch": []})
    lane_mission = {d["lane"]: d.get("mission_id") for d in disp.get("dispatch", [])}
    lane_model = {d["lane"]: d.get("model") for d in disp.get("dispatch", [])}

    status = {"anchor": "KBM-RCI-F1-ABC",
              "updated_at": datetime.now(timezone.utc).isoformat(),
              "lanes": {}, "packages": {}}
    for lane, mid in lane_mission.items():
        status["lanes"][lane] = {"mission_id": mid, "model": lane_model.get(lane),
                                 "recorded_packages": 0, "docs_completed": 0,
                                 "docs_passed": 0}

    for p in wps["packages"]:
        pid, lane = p["package_id"], p["lane"]
        recs = glob.glob(os.path.join(dir_, "runs", lane, pid + ".json"))
        entry = {"lane": lane, "n_docs": p["n_docs"], "mission_id": lane_mission.get(lane),
                 "model": lane_model.get(lane), "status": "dispatched" if lane_mission.get(lane) else "defined"}
        if recs:
            r = json.load(open(recs[0], encoding="utf-8"))
            entry.update({"status": "recorded",
                          "docs_completed": r.get("docs_completed"),
                          "docs_passed": r.get("docs_passed"),
                          "structure_gate": (r.get("structure_gate") or {}).get("passed"),
                          "evidence_gate": (r.get("evidence_gate") or {}).get("passed"),
                          "locators": [r.get("locators_resolved"), r.get("locators_total")]})
            status["lanes"][lane]["recorded_packages"] += 1
            status["lanes"][lane]["docs_completed"] += int(r.get("docs_completed") or 0)
            status["lanes"][lane]["docs_passed"] += int(r.get("docs_passed") or 0)
        status["packages"][pid] = entry

    out = os.path.join(dir_, "workpackage_status.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=1)
        f.write("\n")
    return status


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/rci-f1-abc")
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    st = refresh(args.dir)
    print(json.dumps({"lanes": st["lanes"],
                      "recorded": sum(1 for p in st["packages"].values() if p["status"] == "recorded")},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()