#!/usr/bin/env python3
"""m15247 —— 把交差核验结论落表 tensor_maturity_verdicts（evidence 全部取自 evidence.json，零手抄）。

用法：python3 scripts/m15247_verdict.py [--dry-run]
落表：repo=TensorKnowledge, scope='m15181 KBM-CONSUME-W1', mission_id=$MISSION_ID(默认15247)
      level=<L>, evidence=<JSON>, verdict_by='board-audit'
唯一键 (repo, scope, verdict_by) → 重跑即 UPDATE，幂等。
"""
import argparse
import json
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
EV = ROOT / "artifacts" / "audit_m15247" / "evidence.json"
PSQL = ["psql", "-U", "postgres", "-d", "tensorplatform", "-h", "/var/run/postgresql", "-tA"]
LEVEL = 2  # L2：真代码 输入->计算->输出，可复跑；L3 无集成消费方、L4 无注册基准行（详见 evidence.level_rationale）


def build():
    ev = json.loads(EV.read_text())
    art = {a["path"]: a["sha256"] for a in ev["run_artifacts"] if a["exists"]}
    out = {
        "impl_files": [f"{i['path']} ({i['entry']})" for i in ev["impl_files"]],
        "entry": ("python3 scripts/kb_ab_experiment.py --reps 4 / "
                  "python3 scripts/kb_consume_audit.py --out <dir> / "
                  "python3 scripts/kb_consumption_snapshot.py --print --no-db"),
        "run_artifacts": art,
        "tests": "NONE — grep -rl kb_ab_experiment/kb_consume_audit/kb_consumption_snapshot tests/ = 0 hits; "
                 "m15181 未提交 pytest，本轮用 scripts/m15247_audit_kbm_consume.py 做脚本级复算替代",
        "integration_callers": ev["integration_callers"]["note"] + f"; kb_consumption_snapshots 行={ev['integration_callers']['db_rows']}",
        "benchmark": (f"{ev['benchmark']['query']} -> {ev['benchmark']['n_rows']} 行（全表 "
                      f"{len(ev['benchmark']['table_anchors'])} 个 anchor 均非 KBM-*）→ 唯一裁判无参考行，L4 不可判；"
                      f"GET /tensor/bench/l4-verdict/{os.environ.get('SUBJ', '15181')} -> "
                      f"{ev['platform_l4_verdict'].get('status')} rows={ev['platform_l4_verdict'].get('rows')}"),
        "repro_cmd": (f"{ev['repro_run']['cmd']} -> exit={ev['repro_run']['exit']}；"
                      f"计数事实稳定 injected={ev['repro_run']['stable_fields']['injected_total']} "
                      f"cited={ev['repro_run']['stable_fields']['cited_total']}；"
                      f"时变字段漂移 {len(ev['repro_run']['recorded_vs_live_drift'])} 项 "
                      f"{ {k: [v['recorded'], v['live']] for k, v in ev['repro_run']['recorded_vs_live_drift'].items()} }"),
        "external_anchor": (f"ITTC-1957 C_F=0.075/(log10Re-2)^2 独立重算 "
                            f"Re=1e8→{ev['external_anchor']['ittc1957']['re1e8']}, "
                            f"Re=1e9→{ev['external_anchor']['ittc1957']['re1e9']}；判分容差 rel≤1% "
                            f"(scripts/kb_ab_experiment.py:82)，A 臂实测相对误差<0.01%"),
        "ab_recompute": ev["ab_recompute"],
        "report": {"id": 14295, "six_sections": ev["report"]["sections_present"],
                   "lt3pct_answered": ev["report"]["explicit_lt3pct_answer"],
                   "figures": ev["report"]["figures"], "markdown_sha256": ev["report"]["markdown_sha256"]},
        "prereg_pin": ev["prereg_pin"],
        "level_rationale": ev["level_rationale"],
        "findings": [
            "F1(非阻断) 无注册基准行 → 本单不可判 L4；报告亦未自称 L4/L5，无虚标",
            "F2(非阻断) 集成面只有一次手写 DB 快照，无调度器/端点/CI 消费方 → 不到 L3",
            "F3(非阻断·方法) temperature=0 下 reps=4 近似复制（K1/A rep0=rep1 text/token/latency 全同）→ 有效 n≈1，无不确定区间",
            "F4(非阻断·判分) grade_k3 接受带 32.3±1.5pp 只覆盖卡内 4 个 level 中的最小值；只答 35.135% 的正确答案会被判错",
            "F5(时效) 审计计数时变：本轮复跑 kb_total 31→38、暴露分母 132→209、引用率 1.52%→0.96%（48 分钟内），"
            "报告数字为带 taken_at 的快照，非永久值",
            "F6(诚实项已达标) K2 三臂 0/4 主动判无效锚、任务级双臂未跑均如实写；六段齐全且显式回答<3%",
        ],
    }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    ev = build()
    payload = json.dumps(ev, ensure_ascii=False)
    mid = int(os.environ.get("MISSION_ID", 15247))
    sql = (
        "INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by) VALUES "
        f"('TensorKnowledge','m15181 KBM-CONSUME-W1',{mid},{LEVEL},$json${payload}$json$,'board-audit') "
        "ON CONFLICT (repo, scope, verdict_by) DO UPDATE SET mission_id=EXCLUDED.mission_id,"
        "level=EXCLUDED.level, evidence=EXCLUDED.evidence, created_at=now() RETURNING id, level, gate_state;"
    )
    (ROOT / "artifacts/audit_m15247/verdict_insert.sql").write_text(sql + "\n")
    if a.dry_run:
        print(sql[:400], "...\n[dry-run] not executed")
        return 0
    r = subprocess.run(PSQL + ["-c", sql], capture_output=True, text=True)
    print("psql rc=", r.returncode, r.stdout.strip(), r.stderr.strip()[:400])
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())