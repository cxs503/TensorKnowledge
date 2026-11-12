#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 五指标计算器（预注册指标的唯一计算入口，报告数字由此注入）。

输入（全部为工件，不手抄）:
  <dir>/runs/<LANE>/<package_id>.json   每 work package 的执行回执（成本/产量/证据门计数）
  <dir>/blind/scored.json               盲审评分回执 [{sample_id, claim_faithful, locator_resolvable,
                                        conditions_not_invented, type_fit, reviewer, human_*?}]
  <dir>/blind/blind_key.json            封存映射 {sample_id: {lane, ko_id}}（评分齐全后解封）
  <dir>/batch60.json                    批次（N 分母与 doc 清单）
输出:
  <dir>/metrics.json                    五指标×三臂 + 判定 + 数据可得性
  <dir>/metrics.md                      论文用表（报告直接引用）

缺失数据纪律（预注册 MO1-MO5）: 不可得 → status=WITHHELD/PENDING + null，禁填 0。
"""
from __future__ import annotations

import argparse
import json
import math
import os

METRIC_KEYS = ["M1_unit_cost", "M2_throughput", "M3_extraction_accuracy",
               "M4_evidence_completeness", "M5_knowledge_reuse"]
ARMS = ["A", "B", "C"]
FIELDS = ["claim_faithful", "locator_resolvable", "conditions_not_invented", "type_fit"]
KAPPA_MIN = 0.6
MIN_PASS_RATE = 0.8


def wilson(k: int, n: int, z: float = 1.96) -> list[float] | None:
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    hw = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return [round((c - hw) / d, 4), round((c + hw) / d, 4)]


def load_runs(runs_dir: str) -> dict[str, list[dict]]:
    runs: dict[str, list[dict]] = {a: [] for a in ARMS}
    if not os.path.isdir(runs_dir):
        return runs
    for lane in ARMS:
        d = os.path.join(runs_dir, lane)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".json"):
                continue
            rec = json.load(open(os.path.join(d, name), encoding="utf-8"))
            rec.setdefault("arm", lane)
            rec["_file"] = name
            runs[lane].append(rec)
    return runs


def load_blind(blind_dir: str) -> tuple[list[dict], dict]:
    scored = key = None
    p = os.path.join(blind_dir, "scored.json")
    if os.path.isfile(p):
        scored = json.load(open(p, encoding="utf-8")).get("items", [])
    p = os.path.join(blind_dir, "blind_key.json")
    if os.path.isfile(p):
        key = json.load(open(p, encoding="utf-8")).get("key", {})
    return scored or [], key or {}


def cohen_kappa(a: list[int], b: list[int]) -> float | None:
    if not a or len(a) != len(b):
        return None
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    if pe >= 1.0:
        return None
    return round((po - pe) / (1 - pe), 4)


def _arm_cost(recs: list[dict]) -> dict:
    tot = {"tokens": 0, "compute": 0.0, "wall": 0.0, "docs": 0, "passed": 0, "agents": 0,
           "loc_total": 0, "loc_ok": 0, "claims": 0, "claims_with_loc": 0}
    for r in recs:
        c = r.get("cost", r)
        tot["tokens"] += int(c.get("tokens") or 0)
        tot["compute"] += float(c.get("compute_core_seconds") or 0.0)
        tot["wall"] += float(c.get("wall_seconds") or 0.0)
        tot["docs"] += int(r.get("docs_completed") or 0)
        tot["passed"] += int(r.get("docs_passed") or 0)
        tot["agents"] = max(tot["agents"], int(r.get("agent_count") or 0))
        tot["loc_total"] += int(r.get("locators_total") or 0)
        tot["loc_ok"] += int(r.get("locators_resolved") or 0)
        tot["claims"] += int(r.get("claims") or 0)
        tot["claims_with_loc"] += int(r.get("claims_with_locator") or 0)
    return tot


def compute(batch: dict, runs: dict[str, list[dict]], blind_dir: str) -> dict:
    n_batch = batch.get("n", 0)
    scored, key = load_blind(blind_dir)
    out = {"anchor": "KBM-RCI-F1-ABC", "batch_digest": batch.get("digest"),
           "n_batch": n_batch, "arms": {}, "verdict": None, "blind": {}}

    # ---- 盲审可靠性（先算，决定 M3 可用性）----
    human_pairs = {"claim_faithful": [], "locator_resolvable": [],
                   "conditions_not_invented": [], "type_fit": []}
    for it in scored:
        for f in FIELDS:
            hv = it.get("human_" + f)
            if hv is not None:
                human_pairs[f].append((int(bool(it.get(f))), int(bool(hv))))
    kappas = {f: cohen_kappa([p[0] for p in v], [p[1] for p in v])
              for f, v in human_pairs.items() if v}
    n_human = sum(1 for it in scored if it.get("human_claim_faithful") is not None)
    kappa_ok = bool(kappas) and all(v is not None and v >= KAPPA_MIN for v in kappas.values())
    out["blind"] = {"n_scored": len(scored), "n_human": n_human, "kappa": kappas,
                    "kappa_ok": kappa_ok, "kappa_min": KAPPA_MIN,
                    "human_required": 30,
                    "human_enough": n_human >= 30}

    for arm in ARMS:
        recs = runs.get(arm, [])
        a = {"n_packages_recorded": len(recs), "metrics": {}}
        if not recs:
            for k in METRIC_KEYS:
                a["metrics"][k] = {"status": "NOT_STARTED", "value": None,
                                   "reason": "臂未启动/无执行回执（MO3）"}
            out["arms"][arm] = a
            continue
        t = _arm_cost(recs)
        n_done = t["docs"] or 0
        pass_rate = (t["passed"] / n_done) if n_done else None
        a["totals"] = {"tokens": t["tokens"], "compute_core_seconds": round(t["compute"], 1),
                       "wall_seconds": round(t["wall"], 1), "agents": t["agents"],
                       "docs_completed": n_done, "docs_passed": t["passed"],
                       "pass_rate": None if pass_rate is None else round(pass_rate, 4)}
        # M1 单位成本
        if n_done:
            per_doc = {"tokens": round(t["tokens"] / n_done, 1),
                       "compute_core_seconds": round(t["compute"] / n_done, 2),
                       "agent_hours": round(t["wall"] / 3600 * t["agents"] / n_done, 4)}
            u = (per_doc["tokens"] / 1000 + per_doc["compute_core_seconds"] / 60
                 + per_doc["agent_hours"])
            a["metrics"]["M1_unit_cost"] = {"status": "REAL", "value": round(u, 4),
                                            "components": per_doc}
        else:
            a["metrics"]["M1_unit_cost"] = {"status": "WITHHELD", "value": None,
                                            "reason": "无完成文档（MO1/MO5）"}
        # M2 单位时间产量
        if pass_rate is not None and t["wall"] > 0 and pass_rate >= MIN_PASS_RATE:
            a["metrics"]["M2_throughput"] = {"status": "REAL",
                                             "value": round(t["passed"] / (t["wall"] / 3600), 3),
                                             "components": {"docs_passed": t["passed"],
                                                            "wall_hours": round(t["wall"] / 3600, 3)}}
        elif pass_rate is not None and pass_rate < MIN_PASS_RATE:
            a["metrics"]["M2_throughput"] = {"status": "WITHHELD", "value": None,
                                             "reason": f"pass_rate {pass_rate:.2f} < {MIN_PASS_RATE}（停止规则3）"}
        else:
            a["metrics"]["M2_throughput"] = {"status": "WITHHELD", "value": None,
                                             "reason": "缺挂钟或完成数据"}
        # M3 抽取准确率（盲审）
        items = [it for it in scored if key.get(it["sample_id"], {}).get("lane") == arm]
        if items and kappa_ok and out["blind"]["human_enough"]:
            ok = sum(sum(int(bool(it.get(f))) for f in FIELDS) for it in items)
            tot = len(items) * len(FIELDS)
            a["metrics"]["M3_extraction_accuracy"] = {
                "status": "REAL", "value": round(ok / tot, 4),
                "components": {"items": len(items), "passed_fields": ok, "fields": tot,
                               "wilson95": wilson(ok, tot),
                               "by_field": {f: round(sum(int(bool(it.get(f))) for it in items) / len(items), 3)
                                            for f in FIELDS}}}
        else:
            reason = ("无盲审回执" if not items else
                      ("κ 不达标/人工复核不足 → M3 WITHHELD（预注册盲审可靠性条款）"
                       if not (kappa_ok and out["blind"]["human_enough"]) else "缺数据"))
            a["metrics"]["M3_extraction_accuracy"] = {"status": "WITHHELD", "value": None,
                                                      "reason": reason}
        # M4 证据完整率
        if t["loc_total"] and t["claims"]:
            lsr = t["loc_ok"] / t["loc_total"]
            cov = t["claims_with_loc"] / t["claims"]
            a["metrics"]["M4_evidence_completeness"] = {
                "status": "REAL", "value": round(lsr * cov, 4),
                "components": {"locator_success_rate": round(lsr, 4),
                               "evidence_coverage": round(cov, 4),
                               "locators": t["loc_total"], "claims": t["claims"]}}
        else:
            a["metrics"]["M4_evidence_completeness"] = {"status": "WITHHELD", "value": None,
                                                        "reason": "证据门未回执（无 locator/claim 计数）"}
        # M5 首周复用（长线，T+7d）
        reuse = sum(int(r.get("reuse_citations") or 0) for r in recs if r.get("reuse_window_closed"))
        closed = [r for r in recs if r.get("reuse_window_closed")]
        if closed:
            a["metrics"]["M5_knowledge_reuse"] = {
                "status": "REAL", "value": round(reuse / max(1, len(closed)), 3),
                "components": {"ko_citations": reuse, "packages_settled": len(closed)}}
        else:
            a["metrics"]["M5_knowledge_reuse"] = {"status": "PENDING", "value": None,
                                                  "reason": "首周窗口未结算（T+7d，MO2 禁填 0）"}
        out["arms"][arm] = a

    out["verdict"] = judge(out)
    return out


def _val(m: dict, arm: str, key: str):
    cell = (m.get("arms", {}).get(arm) or {}).get("metrics", {}).get(key) or {}
    return cell.get("value") if cell.get("status") == "REAL" else None


def judge(m: dict) -> dict:
    A = {k: _val(m, "A", k) for k in METRIC_KEYS}
    C = {k: _val(m, "C", k) for k in METRIC_KEYS}
    B = {k: _val(m, "B", k) for k in METRIC_KEYS}
    out = {"inputs": {"A": A, "B": B, "C": C}, "hypotheses": {}, "verdict": "WITHHELD",
           "reason": "", "conditions": []}
    if A["M3_extraction_accuracy"] is None or C["M3_extraction_accuracy"] is None \
            or A["M4_evidence_completeness"] is None or C["M4_evidence_completeness"] is None:
        out["reason"] = "关键质量指标不可得（A/C 的 M3/M4 未结算）→ WITHHELD，不判成立与否"
        return out
    th = {"pp": 0.03, "tp": 3.0, "cost": 1.0}
    h1 = (C["M3_extraction_accuracy"] >= A["M3_extraction_accuracy"] - th["pp"]
          and C["M4_evidence_completeness"] >= A["M4_evidence_completeness"] - th["pp"])
    h2 = (C["M2_throughput"] is not None and A["M2_throughput"] is not None
          and C["M2_throughput"] >= th["tp"] * A["M2_throughput"])
    h3 = (C["M1_unit_cost"] is not None and A["M1_unit_cost"] is not None
          and C["M1_unit_cost"] <= th["cost"] * A["M1_unit_cost"])
    out["hypotheses"] = {"H1_quality_non_inferior": h1, "H2_throughput_3x": h2,
                         "H3_cost_not_worse": h3}
    if not h1:
        out["verdict"] = "NOT_SCALABLE"
        out["reason"] = "H1 不成立：C 的抽取准确率或证据完整率落后 A 超过 3pp"
    elif h2 and h3:
        out["verdict"] = "SCALABLE"
        out["reason"] = "H1∧H2∧H3 成立：普通 Agent 标准产线在质量非劣前提下吞吐≥3×、单位成本≤A"
    else:
        out["verdict"] = "CONDITIONAL"
        reasons = []
        if not h2:
            reasons.append("吞吐未达 3×A（并发/审核工序开销）")
        if not h3:
            reasons.append("单位成本未优于 A（审核与 Skill 开销）")
        out["reason"] = "H1 成立但 " + "；".join(reasons)
        out["conditions"] = reasons
    return out


def to_markdown(m: dict) -> str:
    lines = ["| 指标 | A（1 强 Agent） | B（20 普通） | C（20 普通+审核+Skill） |",
             "|---|---|---|---|"]
    for k in METRIC_KEYS:
        cells = []
        for a in ARMS:
            c = (m["arms"].get(a) or {}).get("metrics", {}).get(k) or {}
            v = c.get("value")
            s = c.get("status", "NA")
            cells.append("—" if v is None else f"{v}")
            if v is None:
                cells[-1] = f"*{s}*"
        lines.append(f"| {k} | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append(f"判定：**{m['verdict']['verdict']}** — {m['verdict']['reason']}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/rci-f1-abc")
    args = ap.parse_args()
    batch = json.load(open(os.path.join(args.dir, "batch60.json"), encoding="utf-8"))
    runs = load_runs(os.path.join(args.dir, "runs"))
    m = compute(batch, runs, os.path.join(args.dir, "blind"))
    with open(os.path.join(args.dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
        f.write("\n")
    md = to_markdown(m)
    with open(os.path.join(args.dir, "metrics.md"), "w", encoding="utf-8") as f:
        f.write(md + "\n")
    print(md)


if __name__ == "__main__":
    main()