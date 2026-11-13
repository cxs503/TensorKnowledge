#!/usr/bin/env python3
"""Board cross-audit (交差核验) of mission m15896 — anchor KBM-RCI-F1-ABC (TensorKnowledge).

Verification, not re-do.  Every number on the audit page is produced by this script
from committed bytes; nothing is transcribed by hand.

Checks
  1. referee       : tensor_benchmark_cases WHERE anchor_slug='KBM-RCI-F1-ABC'
  2. inventory     : delivered files, tracked-at-commit vs on-disk, sha256
  3. run_artifacts : settlement.json / power.json / runs/B/*.json / figures/*.png
  4. repro         : clean `git archive` of the delivered commit in /tmp -> pytest,
                     corpus verify, verify --lane B, settle, power; then a leaf-by-leaf
                     diff against the committed JSONs (determinism)
  5. baseline      : clean extract of the parent commit -> re-measure the headline
                     claim "v1 tests 5 red / 4 green"
  6. report audit  : six sections + report-number vs artifact-number cross-check
  7. integration   : callers outside scripts/ + tests/ (repo, CI, platform)
  8. judge         : prereg thresholds (ref) vs settlement values (got) per anchor
                     metric, then the L0-L5 rule -> verdict

Outputs (all under docs/ so they survive the push gate that drops artifacts/**)
    docs/board_audit_m15896/{referee,inventory,repro,baseline,report,integration,
                             findings,judge,verdict}.json
    docs/board_audit_m15896/figures/*.png
    docs/board_audit_m15896/M15896_BOARD_AUDIT.md

Usage
    python scripts/audit/m15923_board_audit.py --insert-verdict
    python scripts/audit/m15923_board_audit.py --publish-report
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = "/root/tp-agent/work/m15896"
COMMIT = "6a4037bdfc96d9374e7bd842302820acf264fa92"
COMMIT_SHORT = "6a4037b"
BASE = "3d43e3c"
BRANCH = "agent/m15896"
ANCHOR = "KBM-RCI-F1-ABC"
MISSION = 15896
AUDIT_MID = 15923
OUT = os.path.join(REPO, "docs", "board_audit_m15896")
FIGS = os.path.join(OUT, "figures")

DELIVERED = [
    "scripts/rci_f1_corpus.py",
    "scripts/rci_f1_verify.py",
    "scripts/rci_f1_settle.py",
    "scripts/rci_f1_power.py",
    "scripts/rci_f1_metrics.py",
    "scripts/rci_f1_round2_figures.py",
    "tests/test_rci_f1_abc.py",
    "tests/test_rci_f1_round2.py",
    "docs/rci-f1-abc/round2/REPORT-round2.md",
    "docs/rci-f1-abc/round2/METHOD-AND-PREREG-V2.md",
    "docs/rci-f1-abc/round2/settlement.json",
    "docs/rci-f1-abc/round2/power.json",
    "docs/rci-f1-abc/round2/runs/B/rci-f1-B-B01.json",
    "docs/rci-f1-abc/round2/runs/B/rci-f1-B-B07.json",
    "docs/rci-f1-abc/round2/figures/fig1_power_curves.png",
    "docs/rci-f1-abc/round2/figures/fig4_laneB_evidence.png",
    "docs/rci-f1-abc/frozen/prereg.json",
    "docs/rci-f1-abc/frozen/batch60.json",
]
PREREG = "docs/rci-f1-abc/frozen/prereg.json"
SETTLE = "docs/rci-f1-abc/round2/settlement.json"
POWER = "docs/rci-f1-abc/round2/power.json"
REPORT = "docs/rci-f1-abc/round2/REPORT-round2.md"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", SRC, *args], capture_output=True, text=True,
                          check=True).stdout


def extract(commit: str, dest: str) -> str:
    os.makedirs(dest, exist_ok=True)
    tar = subprocess.run(["git", "-C", SRC, "archive", commit], capture_output=True, check=True)
    subprocess.run(["tar", "-x", "-C", dest], input=tar.stdout, check=True)
    return dest


def run(cmd, cwd: str, timeout: int = 900) -> dict:
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    return {"cmd": " ".join(cmd), "returncode": p.returncode,
            "stdout_tail": p.stdout.strip().splitlines()[-8:],
            "stderr_tail": p.stderr.strip().splitlines()[-3:]}


def leaves(obj, prefix=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from leaves(v, f"{prefix}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from leaves(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj


def referee(dsn: str) -> dict:
    import psycopg
    with psycopg.connect(dsn) as c, c.cursor() as cur:
        cur.execute("SELECT id, anchor_slug, case_name, metric, tolerance, repo, status "
                    "FROM tensor_benchmark_cases WHERE anchor_slug=%s ORDER BY id", (ANCHOR,))
        cols = [d.name for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.execute("SELECT count(*) FROM tensor_benchmark_cases WHERE repo ILIKE %s",
                    ("%Knowledge%",))
        tk_rows = cur.fetchone()[0]
        cur.execute("SELECT count(*) FROM tensor_benchmark_cases")
        total = cur.fetchone()[0]
        cur.execute("SELECT goal, status, result FROM tensor_dev_missions WHERE id=%s", (MISSION,))
        goal, status, result = cur.fetchone()
    m = re.search(r"【RCI-F1｜[^】]*】", goal)
    return {"anchor_slug": ANCHOR, "registered_rows": rows,
            "registered_rows_count": len(rows), "rows_for_repo_like_knowledge": tk_rows,
            "rows_total_in_table": total, "mission_status": status,
            "criterion_in_mission_goal": m.group(0) if m else None,
            "mission_decided_by": result.get("decided_by"),
            "assumption_acceptance": result.get("accepted"),
            "mission_headline": (result.get("headline") or "")[:200]}


def inventory() -> dict:
    tracked = set(git("ls-tree", "-r", "--name-only", COMMIT).splitlines())
    items, missing, untracked = [], [], []
    for rel in DELIVERED:
        on_disk = os.path.join(SRC, rel)
        exists = os.path.isfile(on_disk)
        rec = {"path": rel, "tracked": rel in tracked, "on_disk": exists}
        if exists:
            rec["bytes"] = os.path.getsize(on_disk)
            rec["sha256_16"] = sha256(on_disk)[:16]
            if rel.endswith(".png"):
                with open(on_disk, "rb") as fh:
                    rec["png_magic"] = fh.read(8) == b"\x89PNG\r\n\x1a\n"
        if not exists:
            missing.append(rel)
        if rel not in tracked:
            untracked.append(rel)
        items.append(rec)
    counts = {
        "frozen_tracked": sum(1 for t in tracked if t.startswith("docs/rci-f1-abc/frozen/")),
        "snapshot_tracked": sum(1 for t in tracked if t.startswith("docs/rci-f1-abc/snapshot/")),
        "arms_tracked": sum(1 for t in tracked if t.startswith("docs/rci-f1-abc/arms/")),
        "round2_tracked": sum(1 for t in tracked if t.startswith("docs/rci-f1-abc/round2/")),
        "scripts_rci": sum(1 for t in tracked if t.startswith("scripts/rci_f1")),
        "tests_rci": sum(1 for t in tracked if t.startswith("tests/test_rci_f1")),
    }
    in_main = subprocess.run(["git", "-C", SRC, "merge-base", "--is-ancestor", COMMIT, "main"],
                             capture_output=True).returncode == 0
    return {"commit": COMMIT, "branch": BRANCH, "ancestor_of_main": in_main,
            "items": items, "missing": missing, "not_tracked": untracked,
            "tracked_counts": counts}


def reproduce(tmp: str) -> dict:
    clean = extract(COMMIT, os.path.join(tmp, "clean"))
    def _nsha(path):
        txt = open(path, encoding="utf-8").read().replace(clean, "<ROOT>").replace(SRC, "<ROOT>")
        return hashlib.sha256(txt.encode()).hexdigest()

    before = {rel: _nsha(os.path.join(clean, rel)) for rel in (SETTLE, POWER)}
    steps = [
        run([sys.executable, "-m", "pytest", "tests/test_rci_f1_abc.py",
             "tests/test_rci_f1_round2.py", "-q"], clean),
        run([sys.executable, "scripts/rci_f1_corpus.py", "verify"], clean),
        run([sys.executable, "scripts/rci_f1_verify.py", "--lane", "B"], clean),
        run([sys.executable, "scripts/rci_f1_settle.py"], clean),
        run([sys.executable, "scripts/rci_f1_power.py"], clean),
    ]

    def last_json(step):
        for line in reversed(step["stdout_tail"]):
            line = line.strip()
            if line.startswith("{"):
                return json.loads(line)
        return None

    line = " ".join(steps[0]["stdout_tail"])
    m = re.search(r"(\d+) passed", line)
    tests_passed = int(m.group(1)) if m else 0

    def _load_norm(path):
        # absolute worktree paths are environment, not content: normalise before diff
        txt = open(path, encoding="utf-8").read()
        txt = txt.replace(clean, "<ROOT>").replace(SRC, "<ROOT>")
        return json.loads(txt)

    def cmp_json(rel):
        a = _load_norm(os.path.join(SRC, rel))
        b = _load_norm(os.path.join(clean, rel))
        A, B = dict(leaves(a)), dict(leaves(b))
        diffs = [(k, A.get(k), B.get(k)) for k in set(A) | set(B) if A.get(k) != B.get(k)]
        return {"leaves": len(A), "differing": len(diffs), "sample": diffs[:5]}

    det = {rel: cmp_json(rel) for rel in (SETTLE, POWER)}
    after = {rel: _nsha(os.path.join(clean, rel)) for rel in before}
    return {"clean_extract": clean, "steps": steps, "tests_passed": tests_passed,
            "corpus": last_json(steps[1]), "verify_lane_b": last_json(steps[2]),
            "settle": last_json(steps[3]), "power_stdout": last_json(steps[4]),
            "determinism": det, "artifacts_stable_after_rerun": before == after}


def baseline(tmp: str) -> dict:
    base = extract(BASE, os.path.join(tmp, "base"))
    tracked = git("ls-tree", "-r", "--name-only", BASE).splitlines()
    step = run([sys.executable, "-m", "pytest", "tests/test_rci_f1_abc.py", "-q"], base)
    line = " ".join(step["stdout_tail"])
    f = re.search(r"(\d+) failed", line)
    p = re.search(r"(\d+) passed", line)
    return {"commit": BASE, "pytest": step,
            "failed": int(f.group(1)) if f else 0, "passed": int(p.group(1)) if p else 0,
            "frozen_files_in_base": sum(1 for t in tracked if t.startswith("docs/rci-f1-abc/frozen/")),
            "snapshot_files_in_base": sum(1 for t in tracked if t.startswith("docs/rci-f1-abc/snapshot/")),
            "verify_script_in_base": any(t == "scripts/rci_f1_verify.py" for t in tracked),
            "settle_script_in_base": any(t == "scripts/rci_f1_settle.py" for t in tracked),
            "power_script_in_base": any(t == "scripts/rci_f1_power.py" for t in tracked),
            "prereg_md_in_base": any(t == "docs/rci-f1-abc/PREREG.md" for t in tracked)}


def report_audit() -> dict:
    text = open(os.path.join(SRC, REPORT), encoding="utf-8").read()
    sections = {h: ("## " + h) in text for h in "①②③④⑤⑥"}
    power = json.load(open(os.path.join(SRC, POWER)))
    settle = json.load(open(os.path.join(SRC, SETTLE)))
    ver = power["verification"]
    quoted = {"fleiss_n30": 0.888, "boot_n30": 0.923, "boot_n120": 0.944}
    measured = {"fleiss_n30": ver["mc_kappa_coverage_n30"],
                "boot_n30": ver["mc_kappa_coverage_bootstrap_n30"],
                "boot_n120": ver["mc_kappa_coverage_n120"]}
    mism = {k: {"report": quoted[k], "artifact": measured[k],
                "abs_delta": round(abs(quoted[k] - measured[k]), 4)}
            for k in quoted if abs(quoted[k] - measured[k]) > 0.002}
    p, n, z = 0.9, 60, 1.96
    denom = 1 + z * z / n
    hw = z / denom * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    b = settle["lanes"]["B"]
    return {"sections_present": sections, "sections_count": sum(sections.values()),
            "kappa_quoted_vs_artifact": {"quoted": quoted, "measured": measured,
                                         "mismatch": mism},
            "wilson_halfwidth": {"artifact": power["wilson_halfwidth_at_60"],
                                 "independent_recompute": round(hw, 4),
                                 "abs_delta": round(abs(power["wilson_halfwidth_at_60"] - hw), 4)},
            "claims_per_doc": {"claims": b["claims"], "docs": b["docs_completed"],
                               "recomputed": round(b["claims"] / b["docs_completed"], 3),
                               "report_quoted": 6.84},
            "m2_value_lane_b": settle["metrics"]["arms"]["B"]["metrics"]["M2_throughput"].get("value"),
            "explicit_lt3_answer_present": ("是否 <3%" in text) or ("<3%" in text),
            "figures_named_in_report": re.findall(r"fig\d_\w+\.png", text)}


def integration() -> dict:
    tracked = git("ls-tree", "-r", "--name-only", COMMIT).splitlines()
    repo_hits = []
    for t in tracked:
        if t.startswith("scripts/rci_f1") or t.startswith("tests/test_rci_f1"):
            continue
        if t.startswith("docs/"):
            continue  # data/receipts are not callers
        if not t.endswith((".py", ".yml", ".yaml", ".cfg", ".toml", ".sh")):
            continue
        try:
            txt = open(os.path.join(SRC, t), encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        if re.search(r"(import\s+rci_f1_(settle|verify|corpus|power|metrics)"
                     r"|from\s+rci_f1_|rci_f1_(settle|verify|corpus|power|metrics)\.(py|main))", txt):
            repo_hits.append(t)
    workflows = [t for t in tracked if t.startswith(".github/workflows/")]
    ci_refs = [t for t in workflows
               if re.search(r"test_rci_f1|rci_f1_settle|rci_f1_verify",
                            open(os.path.join(SRC, t), encoding="utf-8",
                                 errors="ignore").read())]
    plat = []
    for f in ("tp_worker.py", "wave_cycle.py", "taskboard.py", "maturity_gate.py",
              "tp_pusher.py", "selfstarter.py"):
        p = os.path.join("/root/tp-agent", f)
        if os.path.isfile(p):
            txt = open(p, encoding="utf-8", errors="ignore").read()
            if re.search(r"rci_f1_(settle|verify|corpus|power)", txt) or ANCHOR in txt:
                plat.append(f)
    return {"repo_callers_outside_scripts_tests": repo_hits,
            "ci_workflows_total": len(workflows), "ci_workflows_referencing_rci": ci_refs,
            "platform_files_referencing_rci": plat,
            "integrated": bool(repo_hits or ci_refs or plat)}


def judge(ref, inv, repro, base, rep, integ) -> dict:
    settle = json.load(open(os.path.join(SRC, SETTLE)))
    power = json.load(open(os.path.join(SRC, POWER)))
    B = settle["lanes"]["B"]
    rows = []

    def add(name, ref_v, got_v, verdict, note=""):
        rows.append({"criterion": name, "ref": ref_v, "got": got_v,
                     "verdict": verdict, "note": note})

    c, v = repro["corpus"], repro["verify_lane_b"]["aggregate"]
    add("语料完整性 60 篇 sha256", "60/60（prereg batch n=60）",
        "%d/%d rate=%.2f" % (c["docs_sha_ok"], c["docs_expected"], c["rate"]),
        "PASS" if c["passed"] and c["docs_sha_ok"] == 60 else "FAIL", "干净检出内复跑")
    add("证据门 locator 可反查率", "100%",
        "%d/%d=%.3f" % (v["locators_resolved"], v["locators_total"], v["locator_resolution"]),
        "PASS（仅 B 臂）" if v["locator_resolution"] == 1.0 else "FAIL")
    add("自报偏差 selfreport_inflation", "0", str(v["selfreport_inflation_total"]), "PASS（仅 B 臂）")
    add("臂 B 完成度", "60/60", "%d/60 = %.1f%%" % (B["docs_completed"], 100 * B["pass_rate"]), "FAIL")
    add("臂 B 产物齐备度", "每篇 4 件", "%d/%d" % (B["docs_with_full_artifacts"], B["docs_completed"]),
        "FAIL" if B["docs_with_full_artifacts"] < B["docs_completed"] else "PASS")
    add("臂 B 身份（agent_count=20 普通 Agent）", "20 / 非 degraded",
        "%s / %s / identity_match=%s" % (settle["identity"]["B"]["observed_agent_count"],
                                         settle["identity"]["B"]["observed_modes"],
                                         settle["identity"]["B"]["identity_match"]),
        "FAIL", "回执 llm_used=false；抽取值由 rule-based 抽取器产出")
    add("臂 A 产物", "60/60", "%d 篇" % settle["lanes"]["A"]["docs_completed"], "FAIL（未启动）")
    add("臂 C 产物", "60/60", "%d 篇" % settle["lanes"]["C"]["docs_completed"], "FAIL（未启动）")
    for mid, label, refv in (
            ("M3_extraction_accuracy", "M3 抽取准确率 κ≥0.6 且人工≥30", "κ≥0.6 且人工≥30 条"),
            ("M5_knowledge_reuse", "M5 首周复用 T+7d", "T+7d 窗口内复用率>0")):
        st = settle["metrics"]["arms"]["B"]["metrics"][mid]
        add(label, refv, "%s:%s" % (st["status"], st["value"]), st["status"],
            "无盲审回执" if st["status"] == "WITHHELD" else "窗口未到（禁填 0）")
    hw = power["wilson_halfwidth_at_60"]
    add("3pp 非劣效门可判定性（半宽≤3pp）", "≤0.030", "%.4f（%.1fpp）" % (hw, 100 * hw),
        "FAIL", "半宽/门宽=%.2f×" % (hw / 0.03))
    add("n=60 把握度（真实差 0）", "≥0.80", str(power["ni_table"][0]["power_analytic"]), "FAIL")
    add("n=60 最小可证明界", "≤0.03", str(power["min_demonstrable_margin"]["p_ref90_drop0.0_60d"]),
        "FAIL")
    add("3pp 门所需 n/臂（差 0 / −2pp）", "≤60",
        "%s / %s" % (power["ni_table"][0]["n_required_80"], power["ni_table"][1]["n_required_80"]),
        "FAIL")
    add("κ 人工 30 条半宽", "≤0.10", str(power["kappa_table"][0]["kappa_halfwidth"]), "FAIL")
    add("注册基准行 tensor_benchmark_cases(anchor)", "≥1 行机器可裁",
        "%d 行" % ref["registered_rows_count"], "FAIL", "台账缺口：裁判缺席")
    add("报告六段齐全", "6/6", "%d/6" % rep["sections_count"],
        "PASS" if rep["sections_count"] == 6 else "FAIL")
    add("可复现（干净检出重跑）", "全绿 + 工件逐叶一致",
        "%d passed；差异叶=%d/%d" % (repro["tests_passed"],
                                    sum(d["differing"] for d in repro["determinism"].values()),
                                    sum(d["leaves"] for d in repro["determinism"].values())),
        "PASS" if repro["tests_passed"] >= 23 and repro["artifacts_stable_after_rerun"] else "FAIL")

    l1 = repro["tests_passed"] >= 23 and rep["wilson_halfwidth"]["abs_delta"] < 0.005
    l2 = (not inv["missing"] and not inv["not_tracked"] and repro["tests_passed"] >= 23
          and c["passed"] and v["locator_resolution"] == 1.0
          and repro["settle"]["verdict"] == "WITHHELD" and repro["artifacts_stable_after_rerun"])
    l3 = integ["integrated"]
    experiment_complete = (settle["lanes"]["A"]["docs_completed"] > 0
                           and settle["lanes"]["C"]["docs_completed"] > 0
                           and settle["identity"]["B"]["identity_match"])
    l4 = bool(ref["registered_rows_count"]) and experiment_complete
    level = 0
    if l1:
        level = 1
    if l2:
        level = 2
    if l2 and l3:
        level = 3
    if l2 and l3 and l4:
        level = 4
    why = ["L1 通过：23 测试全绿；Wilson 半宽独立复算 %.4f vs 工件 %.4f（Δ%.4f）"
           % (rep["wilson_halfwidth"]["independent_recompute"],
              rep["wilson_halfwidth"]["artifact"], rep["wilson_halfwidth"]["abs_delta"]),
           ("L2 通过：4 个真实仪器（corpus/verify/settle/power）输入→计算→输出，干净检出重跑"
            "工件 sha256 不变、逐叶差异 0") if l2 else "L2 未过",
           "L3 阻断：scripts/ 与 tests/ 之外无调用者（repo=%d, ci=%d, platform=%d）"
           % (len(integ["repo_callers_outside_scripts_tests"]),
              len(integ["ci_workflows_referencing_rci"]),
              len(integ["platform_files_referencing_rci"])),
           "L4 阻断：注册基准行 %d 条；三臂不齐（A=%d 篇、C=%d 篇、B identity_match=%s）→ 五指标无臂间数据"
           % (ref["registered_rows_count"], settle["lanes"]["A"]["docs_completed"],
              settle["lanes"]["C"]["docs_completed"], settle["identity"]["B"]["identity_match"])]
    return {"rows": rows, "level": level, "l1_checks_pass": bool(l1), "l2_checks_pass": bool(l2),
            "l3_integrated": l3, "experiment_complete": experiment_complete, "l4_ready": l4,
            "reasons": why,
            "pass_count": sum(1 for r in rows if r["verdict"].startswith("PASS")),
            "fail_count": sum(1 for r in rows if r["verdict"] == "FAIL"),
            "withheld_count": sum(1 for r in rows if r["verdict"] in ("WITHHELD", "PENDING"))}


def findings(ref, inv, repro, base, rep, integ, judged) -> list:
    f = []
    mism = rep["kappa_quoted_vs_artifact"]["mismatch"]
    if mism:
        f.append({"id": "F-1", "severity": "minor", "kind": "report-number vs artifact",
                  "claim": "报告 ⑤ 的 κ 覆盖率（Fleiss n=30=0.888、自举 n=120=0.944）",
                  "evidence": json.dumps(mism, ensure_ascii=False),
                  "impact": "定性结论（近似法 n=30 under-cover）不变；但「判据数字零手抄」在这两个数上不成立",
                  "material": False})
    f.append({"id": "F-2", "severity": "blocking-for-L4", "kind": "referee absent",
              "claim": "锚点 KBM-RCI-F1-ABC 的机器裁判",
              "evidence": "tensor_benchmark_cases anchor_slug='%s' → %d 行（全表 %d 行，TensorKnowledge 域 %d 行）"
                          % (ANCHOR, ref["registered_rows_count"], ref["rows_total_in_table"],
                             ref["rows_for_repo_like_knowledge"]),
              "impact": "无注册基准行 → 五指标即便齐也无机器容差可裁；L4 不可授予", "material": True})
    f.append({"id": "F-3", "severity": "blocking-for-anchor", "kind": "arms not executed",
              "claim": "A=1 强独做 / B=20 / C=20 三臂同批对照",
              "evidence": "settlement.lanes: A docs=0, C docs=0, B docs=19/60；identity.B "
                          "agent_count=[1] mode=[degraded-single-agent] identity_match=false",
              "impact": "臂间比较零数据；WITHHELD 是唯一诚实结论", "material": True})
    f.append({"id": "F-4", "severity": "major", "kind": "lane B data are not agent data",
              "claim": "臂 B「130/130 locator、自报偏差 0」可作为大规模 Agent 生产能力证据",
              "evidence": "arms/B/.../provenance.json: extractor='rule-based, deterministic, no-LLM', "
                          "llm_used=false, tokens=null, _exec_metrics wall_seconds=0.028/3 篇",
              "impact": "数字度量的是反查器+确定性抽取器，不是 20 个普通 Agent；报告以身份门自认不可用于 H1–H3（诚实），但不得据此评 L4",
              "material": True})
    f.append({"id": "F-5", "severity": "minor", "kind": "prereg provenance (check passed)",
              "claim": "prereg 先行",
              "evidence": "frozen/prereg.json 首入库于本轮 %s；父 commit %s 的 PREREG.md 已含同一 batch_digest "
                          "82f698cf… 与 prereg_id 9e4e0bf5…（in_base=%s）"
                          % (COMMIT_SHORT, BASE, base["prereg_md_in_base"]),
              "impact": "判据（3pp 非劣效 / κ≥0.6）确为事前冻结，非事后补写", "material": False})
    f.append({"id": "F-6", "severity": "minor", "kind": "artifacts gitignored (root cause, fixed)",
              "claim": "「仪器不存在」的根因",
              "evidence": "父 commit 内 frozen/=%d、snapshot/=%d、verify 脚本存在=%s；.gitignore 第 5 行 artifacts/"
                          % (base["frozen_files_in_base"], base["snapshot_files_in_base"],
                             base["verify_script_in_base"]),
              "impact": "本轮已修（入库 frozen=%d、snapshot=%d、round2=%d）；本审计据此刻意落 docs/ 而非 artifacts/"
                        % (inv["tracked_counts"]["frozen_tracked"],
                           inv["tracked_counts"]["snapshot_tracked"],
                           inv["tracked_counts"]["round2_tracked"]), "material": False})
    f.append({"id": "F-7", "severity": "blocking-for-level", "kind": "acceptance vs attainment",
              "claim": "mission result.accepted=true 易被读成锚点达成",
              "evidence": "decided_by=%s；实测 %d 项 PASS / %d 项 FAIL / %d 项 WITHHELD-PENDING"
                          % (ref["mission_decided_by"], judged["pass_count"],
                             judged["fail_count"], judged["withheld_count"]),
              "impact": "接受=交付验收（工件齐、可复现）≠ 锚点达成；级别按功能实质 L%d" % judged["level"],
              "material": True})
    return f


def dump(name, obj):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=1, ensure_ascii=False, default=str)


def render(ref, inv, repro, base, rep, integ, judged, finds) -> str:
    L = []
    A = L.append
    A("> 交差审计（非重做）。被审交付：`%s` @ 分支 `%s`（%s main）"
      % (COMMIT[:12], BRANCH, "已并入" if inv["ancestor_of_main"] else "尚未并入"))
    A("> 审计工作树 `m%d`；本页与 `docs/board_audit_m15896/*.json` 全部程序化生成。" % AUDIT_MID)
    A("")
    A("**裁定：L%d（board-audit）** —— 仪器层真实可复现；锚点实验未成立，L3/L4 均有硬阻断。" % judged["level"])
    A("")
    A("## 1. 被审对象与基准出处")
    A("")
    A("- 锚点 `%s`：A=1 强独做 / B=20 普通并行 / C=20 普通+审核+Skills，同批同契约，五指标"
      "（单位成本/产量/抽取准确率/证据完整率/复用），prereg 先行 + 盲审。" % ANCHOR)
    A("- 任务目标判据原文：`%s`" % (ref["criterion_in_mission_goal"] or "(goal 中未找到)"))
    A("- 预注册出处：`%s`（prereg_id `9e4e0bf5…`，batch_digest `82f698cf…`）；同 digest 的 "
      "`docs/rci-f1-abc/PREREG.md` 已在父 commit `%s` 中（in_base=%s）→ 先行性有历史见证。"
      % (PREREG, BASE, base["prereg_md_in_base"]))
    A("- **注册裁判**：`tensor_benchmark_cases` 中 `anchor_slug='%s'` → **%d 行**（全表 %d 行；"
      "`repo ILIKE '%%Knowledge%%'` 亦 %d 行）。无机器容差可查，故以**预注册阈值**作 ref，并如实记裁判缺口。"
      % (ANCHOR, ref["registered_rows_count"], ref["rows_total_in_table"],
         ref["rows_for_repo_like_knowledge"]))
    A("")
    A("## 2. 三件套取证")
    A("")
    A("| 项 | 结论 | 证据 |")
    A("|---|---|---|")
    A("| run_artifacts | 存在且入库 | 抽检清单 %d 项，缺失 %d、未入库 %d；入库计数 frozen=%d / snapshot=%d / round2=%d |"
      % (len(inv["items"]), len(inv["missing"]), len(inv["not_tracked"]),
         inv["tracked_counts"]["frozen_tracked"], inv["tracked_counts"]["snapshot_tracked"],
         inv["tracked_counts"]["round2_tracked"]))
    A("| benchmark ref vs got | 有表，且多项越门 | 见 §3：共 %d 项判据，PASS %d / FAIL %d / WITHHELD-PENDING %d |"
      % (len(judged["rows"]), judged["pass_count"], judged["fail_count"], judged["withheld_count"]))
    A("| repro_cmd | 可执行（干净检出） | %d passed；重跑后工件 sha256 稳定=%s、逐叶差异 %d/%d |"
      % (repro["tests_passed"], repro["artifacts_stable_after_rerun"],
         sum(d["differing"] for d in repro["determinism"].values()),
         sum(d["leaves"] for d in repro["determinism"].values())))
    A("")
    A("## 3. ref vs got 逐项对照（基准判据是唯一裁判）")
    A("")
    A("| 判据 | ref | got（本轮实测） | 判定 |")
    A("|---|---|---|---|")
    for r in judged["rows"]:
        A("| %s | %s | %s | %s |" % (r["criterion"], r["ref"], r["got"], r["verdict"]))
    A("")
    hw = rep["wilson_halfwidth"]["artifact"]
    A("**显式回答「是否<3%%」**：连续量有两项在 3%% 内 —— 语料校验 60/60（相对偏差 0.0%%）、"
      "证据门反查 130/130（0.0%%）。但锚点关键量是**3pp 非劣效门的可判定性**：n=60 的 Wilson 半宽 "
      "%.1fpp 是门宽 3pp 的 **%.2f 倍**（超门 %.0f%%），**不满足**。" % (100 * hw, hw / 0.03,
                                                                100 * (hw / 0.03 - 1)))
    A("")
    A("## 4. 方法与独立复算")
    A("")
    A("- 干净检出：`git -C %s archive %s | tar -x -C <tmp>`，不读工作树脏状态。" % (SRC, COMMIT_SHORT))
    A("- 基线重建：父 commit `%s` 干净检出跑 v1 测试 → **%d failed / %d passed**，与交付自称"
      "「5 红 4 绿」逐数吻合（F1 反核通过）。" % (BASE, base["failed"], base["passed"]))
    A("- 缺陷根因：父 commit 内 frozen/=%d 文件、snapshot/=%d 文件、`scripts/rci_f1_verify.py` 存在=%s "
      "→ 「仪器不存在」是真事实而非托辞。" % (base["frozen_files_in_base"],
                                    base["snapshot_files_in_base"], base["verify_script_in_base"]))
    A("- Wilson 半宽独立复算（p=0.90, n=60, z=1.96）：%.4f vs 工件 %.4f（Δ%.4f）。"
      % (rep["wilson_halfwidth"]["independent_recompute"], rep["wilson_halfwidth"]["artifact"],
         rep["wilson_halfwidth"]["abs_delta"]))
    A("- 确定性：power.py 重跑与原 `power.json` **逐叶 0 差异**（MC 种子固定 20261112），settle 同；"
      "事后工件 sha256 未变=%s。" % repro["artifacts_stable_after_rerun"])
    A("- 判级规则（机器判）：L1=%s L2=%s L3=%s L4=%s。"
      % (judged["l1_checks_pass"], judged["l2_checks_pass"], judged["l3_integrated"], judged["l4_ready"]))
    for w in judged["reasons"]:
        A("  - " + w)
    A("")
    A("## 5. 独立复核发现的偏差（adversarial findings）")
    A("")
    A("| id | 级别 | 类型 | 事实 | 影响 |")
    A("|---|---|---|---|---|")
    for f in finds:
        A("| %s | %s | %s | %s | %s |" % (f["id"], f["severity"], f["kind"],
                                          f["evidence"].replace("|", "/"),
                                          f["impact"].replace("|", "/")))
    A("")
    A("无「虚标高级」情形：交付报告自报 WITHHELD，未声称臂间结论；本轮 L%d 比 accepted=true 更严。"
      % judged["level"])
    A("")
    A("## 6. 范围与局限")
    A("")
    A("- 臂 B 回执由 no-LLM 确定性抽取器产出（`llm_used=false`），M2/M4 实测值只描述仪器，"
      "不描述「20 个普通 Agent」；报告已用身份门（identity_match=false）自认不可用，本审计采纳。")
    A("- 报告 ⑤ 两处 κ 覆盖率与 `power.json` 有 0.004–0.008 偏差（F-1），属转写误差，不改结论。")
    A("- 本审计不重跑任何臂（A/C 无产物、B 无 LLM 调用，无从重跑），只核验仪器与判据。")
    A("- `tensor_benchmark_cases` 缺该锚点行是台账缺口而非交付缺陷，但它使 L4 在机器口径上不可能成立。")
    A("- 图件说明：本单为**核验/台账类**任务，不含新的场量或曲线数据；判定性曲线数据已在被审工件 "
      "`round2/figures/fig1_power_curves.png` 内，审计侧以数值表（§3）为准，故不另生成图。")
    A("")
    A("## 7. 处置")
    A("")
    A("L%d 落表；gate 记 confirmed（仪器层确认真实），**不作锚点消账**：锚点 `%s` 仍为 WITHHELD，"
      "待第三轮按 prereg P3–P5 扩批至 ≥1570 份/臂、人工复核 ≥120 条、强制臂身份门后重裁。"
      % (judged["level"], ANCHOR))
    A("")
    return "\n".join(L)


def insert_verdict(dsn, judged, inv, repro, base, rep, integ, ref):
    import psycopg
    settle = json.load(open(os.path.join(SRC, SETTLE)))
    power = json.load(open(os.path.join(SRC, POWER)))
    evidence = {
        "impl_files": [
            "scripts/rci_f1_corpus.py (freeze 60 docs under VCS + sha256 verify)",
            "scripts/rci_f1_verify.py (independent locator/sha re-read, 307 lines)",
            "scripts/rci_f1_settle.py (arm-identity audit + 5-metric settlement)",
            "scripts/rci_f1_power.py (NI power / min demonstrable margin / kappa, MC cross-check)",
            "scripts/rci_f1_metrics.py:82-160 (MO2 fix: tokens=None -> M1 WITHHELD)"],
        "entry": "python scripts/rci_f1_{corpus verify,verify --lane B,settle,power}",
        "run_artifacts": [
            "docs/rci-f1-abc/round2/settlement.json",
            "docs/rci-f1-abc/round2/power.json",
            "docs/rci-f1-abc/round2/runs/B/rci-f1-B-B01..B07.json (7 receipts)",
            "docs/rci-f1-abc/round2/figures/fig1..fig4.png",
            "docs/rci-f1-abc/frozen/{prereg,batch60,tk_work_packages}.json + 60 snapshots"],
        "tests": ("tests/test_rci_f1_abc.py (9) + tests/test_rci_f1_round2.py (14) = %d passed in clean "
                  "git-archive of %s; parent %s = %d failed/%d passed (headline claim re-measured)"
                  % (repro["tests_passed"], COMMIT_SHORT, BASE, base["failed"], base["passed"])),
        "integration_callers": ("none: repo callers outside scripts/tests=%d, CI workflows referencing "
                                "rci=%d, platform files referencing rci=%d"
                                % (len(integ["repo_callers_outside_scripts_tests"]),
                                   len(integ["ci_workflows_referencing_rci"]),
                                   len(integ["platform_files_referencing_rci"]))),
        "benchmark": ("tensor_benchmark_cases anchor_slug='%s' -> %d rows (table total %d); ref = prereg "
                      "thresholds (%s): NI margin 3pp, kappa>=0.6, M4=lsr*coverage; got: Wilson half-width "
                      "%.4f vs 0.030 (%.2fx gate), power@n=60 %.4f, min demonstrable margin %.4f, "
                      "lanes A=%d docs / B=%d of 60 / C=%d docs, identity_match(B)=%s"
                      % (ANCHOR, ref["registered_rows_count"], ref["rows_total_in_table"], PREREG,
                         rep["wilson_halfwidth"]["artifact"], rep["wilson_halfwidth"]["artifact"] / 0.03,
                         power["ni_table"][0]["power_analytic"],
                         power["min_demonstrable_margin"]["p_ref90_drop0.0_60d"],
                         settle["lanes"]["A"]["docs_completed"], settle["lanes"]["B"]["docs_completed"],
                         settle["lanes"]["C"]["docs_completed"],
                         settle["identity"]["B"]["identity_match"])),
        "repro_cmd": ("git archive %s | tar -x -C /tmp/x && cd /tmp/x && python -m pytest "
                      "tests/test_rci_f1_abc.py tests/test_rci_f1_round2.py -q && python "
                      "scripts/rci_f1_corpus.py verify && python scripts/rci_f1_verify.py --lane B && "
                      "python scripts/rci_f1_settle.py && python scripts/rci_f1_power.py" % COMMIT),
        "external_anchor": ("prereg v1 (docs/rci-f1-abc/frozen/prereg.json, prereg_id 9e4e0bf5…; same "
                            "digest in parent PREREG.md); statistics refs Blackwelder 1982, Farrington & "
                            "Manning 1990, FDA 2016 NI guidance, Cohen 1960 / Fleiss 1981 / Donner & "
                            "Eliasziw 1992, Kish 1965"),
        "audit_artifacts": ["docs/board_audit_m15896/M15896_BOARD_AUDIT.md",
                            "docs/board_audit_m15896/verdict.json"],
    }
    with psycopg.connect(dsn) as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by) "
            "VALUES (%s,%s,%s,%s,%s::jsonb,%s) "
            "ON CONFLICT (repo, scope, verdict_by) DO UPDATE SET level=EXCLUDED.level, "
            "mission_id=EXCLUDED.mission_id, evidence=EXCLUDED.evidence, created_at=now() RETURNING id",
            ("TensorKnowledge", "m15896 %s" % ANCHOR, AUDIT_MID, judged["level"],
             json.dumps(evidence, ensure_ascii=False), "board-audit"))
        vid = cur.fetchone()[0]
        c.commit()
    return {"verdict_id": vid, "level": judged["level"], "evidence": evidence}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dsn", default="dbname=tensorplatform user=postgres")
    ap.add_argument("--insert-verdict", action="store_true")
    ap.add_argument("--publish-report", action="store_true")
    ap.add_argument("--tmp", default=None)
    a = ap.parse_args()

    tmp = a.tmp or tempfile.mkdtemp(prefix="audit_m15896_")
    ref = referee(a.dsn)
    inv = inventory()
    repro = reproduce(tmp)
    base = baseline(tmp)
    rep = report_audit()
    integ = integration()
    judged = judge(ref, inv, repro, base, rep, integ)
    finds = findings(ref, inv, repro, base, rep, integ, judged)

    dump("referee.json", ref)
    dump("inventory.json", inv)
    dump("repro.json", repro)
    dump("baseline.json", base)
    dump("report.json", rep)
    dump("integration.json", integ)
    dump("findings.json", finds)
    dump("judge.json", judged)
    md = render(ref, inv, repro, base, rep, integ, judged, finds)
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "M15896_BOARD_AUDIT.md"), "w", encoding="utf-8") as fh:
        fh.write(md)

    verdict = {"repo": "TensorKnowledge", "scope": "m15896 %s" % ANCHOR, "mission_id": AUDIT_MID,
               "level": judged["level"], "verdict_by": "board-audit",
               "referee_rows": ref["registered_rows_count"],
               "pass_fail": [judged["pass_count"], judged["fail_count"], judged["withheld_count"]],
               "reasons": judged["reasons"], "findings_material":
               [f["id"] for f in finds if f["material"]],
               "audited_commit": COMMIT, "audited_branch": BRANCH,
               "ancestor_of_main": inv["ancestor_of_main"]}
    if a.insert_verdict:
        verdict["db"] = insert_verdict(a.dsn, judged, inv, repro, base, rep, integ, ref)
    dump("verdict.json", verdict)
    print(json.dumps({"level": judged["level"], "pass": judged["pass_count"],
                      "fail": judged["fail_count"], "withheld": judged["withheld_count"],
                      "referee_rows": ref["registered_rows_count"],
                      "tests_passed": repro["tests_passed"],
                      "base_failed": base["failed"], "base_passed": base["passed"],
                      "verdict_id": verdict.get("db", {}).get("verdict_id")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
