#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 三臂派单（A=本单直接派发；B/C=交 KBM-RCI-F1-FACTORY 泳道）。

纪律：
  * goal 全文由 batch60.json / tk_work_packages.json 程序化生成（零手抄 60 条清单）；
  * 每条 goal 的 sha256 与 mission_id 一起落盘到 runs/rci-f1-abc/dispatch.json（可复算）；
  * 派单前必须已存在 prereg.json（预注册先于执行），否则拒绝派单。

用法:
  python scripts/rci_f1_dispatch.py --dir artifacts/rci-f1-abc --dry-run
  python scripts/rci_f1_dispatch.py --dir artifacts/rci-f1-abc --execute
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
STRONG_MODEL = "Qwen3.8-27B"      # fleet 强档（verifier/generalist 席位 22 个）
ORDINARY_MODEL = "deepseek-v4-flash"  # fleet 普通档（主体席位）

COMMON_CONTRACT = """工作包契约（RCI-F1 wp/1.0，工序 01-05）:
- 输入: 文档清单见下（doc_id / repo / path / sha256 前 12 位）；原文以冻结快照为证据基准。
- 输出(每份文档): {doc_id}/claims.json, evidence.json, provenance.json, extraction_summary.json
  字段骨架: claim{statement, claim_form, faithfulness{quote, span, lines, sha256}},
  evidence[{path, lines, span, sha256, quote}], conditions{stated_in_source, scope, text},
  quality(六维 0-5 整数 + rubric), provenance{extractor, ts, inputs_sha256}
- 硬约束: ①每条 claim 必带 source locator（path+行区间+sha256，抽取时当场核验，
  核不上即弃并记 drop 原因）；②不得臆造：conditions 只允许原文自述，无自述则
  stated_in_source=false 且 scope="not-stated-in-source"；③零 claim 合法（no_forced_claim_generation），
  不得为充数编造知识；④禁止把 KO 标成 verified（三状态分离：mission succeeded≠审核通过≠科学验证）。
- 每 work package 必须落一条执行回执 runs/<LANE>/<package_id>.json:
  {arm, package_id, doc_ids, agent_count, wall_seconds, tokens, compute_core_seconds,
   docs_completed, docs_passed, claims, claims_with_locator, locators_total, locators_resolved}
  其中 locators_total/resolved 必须是程序化反查结果（sha256+行区间可解析且片段匹配），不得自报。
- 交付路径: 本仓 docs/rci-f1-abc/arms/<LANE>/<package_id>/ 与 objects/<LANE>/<package_id>.jsonl。
"""


def h(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def doc_lines(batch: dict) -> str:
    return "\n".join(
        f"{i:02d} {d['doc_id']} {d['repo']} {d['path']} {d['sha256'][:12]} [{d['content_type']}/{d['tier']}]"
        for i, d in enumerate(batch["documents"], 1)
    )


def pkgs_text(wps: dict, lane: str) -> str:
    rows = [p for p in wps["packages"] if p["lane"] == lane]
    return "\n".join(f"{p['package_id']} slot={p['agent_slot']} docs={','.join(p['doc_ids'])}"
                     for p in rows)


def goal_A(batch: dict, wps: dict) -> str:
    return f"""【锚点=KBM-RCI-F1-ABC】【A 臂执行单·单强 Agent 整批】你=1 个 Agent 独立加工整批 60 份文档
（组织变量定义为「单个 Agent 独立完成」，禁止把包内文档再分派给子代理并行）。

{COMMON_CONTRACT}
本臂: lane=A, package_id=rci-f1-A-A01, 共 60 份（整批）。
执行回执落 runs/A/rci-f1-A-A01.json，其中 agent_count 必须填 1。

批次锚: KBM-RCI-F1-ABC batch_digest={batch['digest']}
预注册见 artifacts/rci-f1-abc/prereg.json（指标与阈值已冻结，勿改）。

60 份文档清单（doc_id repo path sha256前12 [type/tier]）:
{doc_lines(batch)}

验收: 60/60 有回执；结构门(JSON/Schema) + 证据门(locator 程序化反查) 通过率写入回执；
允许失败不许伪造：做不到的文档如实记 failed 并在 extraction_summary 写明原因。"""


def goal_lane(batch: dict, wps: dict, lane: str) -> str:
    if lane == "B":
        org = ("20 个普通 Agent 并行（**免独立审核、免成熟 Skill**：只给通用抽取指令，"
               "不给 Skill 模板库、不给独立审核工序）；每个 Agent 一个 work package（3 份）。")
        accept = ("验收: 20/20 包有回执；结构门 + 证据门程序化；本臂**不含语义门**（设计如此）。")
    else:
        org = ("20 个普通 Agent 并行 + **独立审核 Agent**（审核者只看原文+知识对象，"
               "不看生产者解释）+ **成熟 Skills**（RCI-F1 抽取 Skill v1 模板库）；每包 3 份。")
        accept = ("验收: 20/20 包有回执；结构门 + 证据门程序化 + 语义门由独立审核 Agent 出 review.json。")
    return f"""【锚点=KBM-RCI-F1-ABC】【{lane} 臂泳道执行单】本单交 KBM-RCI-F1-FACTORY(任务 15495) 泳道调度器
按 tk_work_packages.json 分片派发；若直接由单 Agent 执行=降级模式，须在回执里如实记 agent_count，
不得把单 Agent 顺序加工记为并行。

组织方式（本臂唯一变量）: {org}

{COMMON_CONTRACT}
本臂: lane={lane}, 20 个 work package（每包 3 份，B 与 C 的 doc->package 映射完全相同=配对设计）。
执行回执落 runs/{lane}/<package_id>.json，agent_count 填该包实际执行者数。

批次锚: KBM-RCI-F1-ABC batch_digest={batch['digest']}

20 个 work package:
{pkgs_text(wps, lane)}

60 份文档清单（doc_id repo path sha256前12 [type/tier]）:
{doc_lines(batch)}

{accept}"""


def goal_for(lane: str, batch: dict, wps: dict) -> str:
    if lane == "A":
        return goal_A(batch, wps)
    return goal_lane(batch, wps, lane)


def build_requests(dir_: str) -> list[dict]:
    batch = json.load(open(os.path.join(dir_, "batch60.json"), encoding="utf-8"))
    wps = json.load(open(os.path.join(dir_, "tk_work_packages.json"), encoding="utf-8"))
    prereg = json.load(open(os.path.join(dir_, "prereg.json"), encoding="utf-8"))
    reqs = []
    for lane, model, key, tokens, calls, wall in (
        ("A", STRONG_MODEL, "rci-f1-abc-lane-a", 2_400_000, 160, 7200),
        ("B", ORDINARY_MODEL, "rci-f1-abc-lane-b", 900_000, 120, 7200),
        ("C", ORDINARY_MODEL, "rci-f1-abc-lane-c", 1_600_000, 200, 7200),
    ):
        goal = goal_for(lane, batch, wps)
        reqs.append({
            "lane": lane,
            "goal": goal,
            "goal_sha256": h(goal),
            "goal_chars": len(goal),
            "body": {
                "goal": goal,
                "repo": "TensorKnowledge",
                "base_ref": "main",
                "runner": "native",
                "origin": "agent",
                "model": model,
                "claim_unassigned": True,
                "task_key": key,
                "budget": {"max_tokens": tokens, "max_tool_calls": calls, "max_wall_seconds": wall},
            },
            "prereg_id": prereg["prereg_id"],
            "batch_digest": batch["digest"],
        })
    return reqs


def post(body: dict) -> dict:
    tok = os.environ.get("TP_TOKEN") or open("/tmp/tok_m15496").read().strip()
    req = urllib.request.Request(BASE + "/tensor/missions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/rci-f1-abc")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    reqs = build_requests(args.dir)
    rec = {"anchor": "KBM-RCI-F1-ABC", "generated_at": datetime.now(timezone.utc).isoformat(),
           "models": {"A": STRONG_MODEL, "B": ORDINARY_MODEL, "C": ORDINARY_MODEL},
           "dispatch": []}
    for r in reqs:
        row = {"lane": r["lane"], "task_key": r["body"]["task_key"], "model": r["body"]["model"],
               "goal_chars": r["goal_chars"], "goal_sha256": r["goal_sha256"],
               "prereg_id": r["prereg_id"], "batch_digest": r["batch_digest"]}
        if args.execute:
            resp = post(r["body"])
            row["mission_id"] = resp.get("id")
            row["response_status"] = resp.get("status")
        rec["dispatch"].append(row)
    out = os.path.join(args.dir, "..", "..", "runs", "rci-f1-abc", "dispatch.json")
    out = os.path.normpath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if args.execute:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
    print(json.dumps(rec, ensure_ascii=False, indent=1))
    if not args.execute:
        print(f"(dry-run) goal chars: " + ", ".join(f"{r['lane']}={r['goal_chars']}" for r in reqs))


if __name__ == "__main__":
    main()