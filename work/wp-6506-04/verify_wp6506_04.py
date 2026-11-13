#!/usr/bin/env python3
"""wp-6506-04 独立审核的可复算检查器（reviewer-side, read-only）。

作用：把「报告 markdown 里写的每个数」与「上游台账工件里的原始计数」逐项对上，
并检查引文是否逐字可定位。不信任生产者叙事，只信任字节与计数。

检查面（四类）：
  hash      —— source_hash / chars 与平台返回的 markdown 字节一致
  quote     —— 审核证据表中的每条引文是原文逐字子串（平台会独立重算）
  arithmetic—— §3.1/§3.2/§3.4/§⑥ 的每个比值由上游 JSON 台账重新累加得出，
               再与 markdown 里印的字符串比对（"报表数 == 重算数"）
  replay    —— 用 git 在 TensorPlatform 检出里复现：文件存在性、pytest 计数、
               以及候选缺陷 test_gate_rejects_toothless_killer

用法（一键复跑）：
  python3 work/wp-6506-04/verify_wp6506_04.py \
      --tp-repo /root/tp-agent/work/m12407 --tp-commit 2fe7f597f --run-tests

产物：work/wp-6506-04/review_evidence.json（每检查一项：期望/实测/结论/证据路径）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = HERE / "report_6506.md"
DEFAULT_ART = HERE / "upstream_artifacts"
DEFAULT_UPSTREAM = HERE / "upstream_wp-6506-01.result.json"

# 审核证据表：claim → 原文逐字引文（零手抄：全部须逐字可定位）
QUOTES = [
    ("Q01", "「结构性阻断 + fail-fast + KPI 门禁」的做法陈述",
     "本单把这三条线做成**服务端结构性阻断 + 客户端 fail-fast + 全台账 KPI 门禁**。"),
    ("Q02", "台账规模：12 判据(含负控)/66 变异体",
     "| 台账判据数 | 12 条（含 1 条负控），变异体 66 个 |"),
    ("Q03", "声称新增 21/30/12 条测试",
     "`tests/test_report_ownership.py`（21 条）、`tests/test_criteria_mutation.py`（30 条）、"
     "`backend/tests/test_paper_traceability_gate_kills_v3.py`（12 条）"),
    ("Q04", "配图门声称以 IEND 收尾为判据",
     "必须以带 CRC 的 IEND 块收尾"),
    ("Q05", "PAPER-TRACE 门 kill rate 61.1%",
     "| PAPER-TRACE | 3 | 11/18 | 61.1% | ⚠️ |"),
    ("Q06", "REPORT-QUALITY 门 kill rate 58.3%",
     "| REPORT-QUALITY | 3 | 7/12 | 58.3% | ⚠️ |"),
    ("Q07", "合计 47/66 = 71.2%",
     "全部判据合计 killed 47/66 = 71.2%"),
    ("Q08", "扣除负控后 79.7%",
     "扣除负控后 79.7%"),
    ("Q09", "M1 单调性序列 [3,3,5]",
     "ε=1%→3 个、3%→3 个、15%→5 个"),
    ("Q10", "负控 0/7 且标 UNFALSIFIABLE",
     "且被标为 UNFALSIFIABLE（清单：NEG-TAUTOLOGY）"),
    ("Q11", "PAPER-TRACE AST 残留 4 个 survivor 且点名",
     "残留 survivor 4 个：binop_swap[5], binop_swap[6], return_empty[0], return_empty[1]"),
    ("Q12", "AST 现状 182/186 = 97.8%",
     "| 现状 | +51 条杀手测试（含本单 12 条 v3） | 186 | 182 | **97.8%** |"),
    ("Q13", "AST 基线 92/186 = 49.5%",
     "| 基线 | 原 21 条单测 | 186 | 92 | **49.5%** |"),
    ("Q14", "C5 既有测试 223/0/1",
     "223 passed / 0 failed / 1 skipped"),
    ("Q15", "C12 域词扫描 3 文件/37 词条/命中 0",
     "`domain_leak_scan.py` 扫 3 个新改文件 / 37 域词条 → 命中 0"),
    ("Q16", "§⑥ 门槛写作 168/186（90.0%）",
     "判据 ≥168/186（90.0%）"),
    ("Q17", "§⑥ 余量 7.8pp",
     "余量 7.8pp"),
    ("Q18", "逐判据 PT-PG4 4/7 = 57%",
     "| PT-PG4 | PAPER-TRACE | 4/7 | 57% |"),
    ("Q19", "逐判据 PL-DRIFT 7/7 = 100%",
     "| PL-DRIFT | CLIENT-PAYLOAD | 7/7 | 100% |"),
    ("Q20", "C11 门禁生效自述（负控 exit 2 + 正控 bites=True）",
     "负控 spec（无 killer test）→ exit 2 `NO_KILLER_TEST`；正控 spec → exit 0，"
     "killer 破坏性验证 bites=True"),
    ("Q21", "C6 基线复现 92/186 = 49.46%",
     "| C6 基线复现 | 92/186 = 49.46% | 通过（=49.5%） |"),
    ("Q22", "诚实申报未跑全量套件",
     "未跑仓内数万条全量用例"),
    ("Q23", "误差口径为离散判据",
     "所有关键量都是**离散/程序化**判据"),
    ("Q24", "纳入台账的验收门 4 个", "纳入台账的验收门 | 4 个"),
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def parse_md_tables(md: str) -> list[list[str]]:
    """把 markdown 表格解析成 [[cell,...],...]（row 0 = 表头，跳过 |---| 分隔行）。"""
    rows, seen_sep = [], False
    for line in md.splitlines():
        s = line.strip()
        if not (s.startswith("|") and s.endswith("|")):
            seen_sep = False
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("-: ") and c for c in cells):
            seen_sep = True
            continue
        rows.append(cells)
        _ = seen_sep
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--artifacts", default=str(DEFAULT_ART))
    ap.add_argument("--upstream", default=str(DEFAULT_UPSTREAM))
    ap.add_argument("--tp-repo", default="", help="TensorPlatform 检出（replay 类检查）")
    ap.add_argument("--tp-commit", default="2fe7f597f", help="P34-N7 生产者提交")
    ap.add_argument("--out", default=str(HERE / "review_evidence.json"))
    ap.add_argument("--run-tests", action="store_true", help="重跑 pytest 复现（约 5s）")
    a = ap.parse_args()

    src = Path(a.source).read_bytes()
    md = src.decode("utf-8")
    art = Path(a.artifacts)
    checks: list[dict] = []

    def add(cid, kind, claim, expected, observed, ok, evidence, note=""):
        checks.append({"check_id": cid, "kind": kind, "claim": claim,
                       "expected": expected, "observed": observed,
                       "status": "pass" if ok is True else ("fail" if ok is False else "unknown"),
                       "evidence": evidence, "note": note})

    # ── hash ───────────────────────────────────────────────────────────────
    got = sha256_bytes(src)
    want = "195447357f5099ba51d2931c4daff233b23098fee7bdf8f53a1569b060f4877c"
    add("H1", "hash", "契约 source_hash 与原文 markdown 字节哈希一致",
        "sha256:" + want, "sha256:" + got, got == want, "contract input.source_hash")
    add("H2", "hash", "契约 chars 与原文长度一致", 10846, len(md), len(md) == 10846,
        "contract input.chars")

    # ── quote ──────────────────────────────────────────────────────────────
    for qid, claim, q in QUOTES:
        hit = q in md
        idx = md.find(q)
        add("Q-" + qid, "quote", claim, "verbatim substring",
            ("found@%d" % idx) if hit else "NOT_FOUND", hit,
            "report_6506.md", q[:60])

    # ── arithmetic（上游台账重算 vs 报告里的印刷值）────────────────────────────
    ledger = json.loads((art / "criteria_mutation_ledger.json").read_text())
    crit = ledger["criteria"]
    kpi = ledger["kpi"]
    nonctl = [c for c in crit if not c.get("control")]

    # 逐门口径：不信任台账自带的 per_gate，自己按 criterion 累加
    by_gate: dict[str, dict] = {}
    for c in crit:
        g = by_gate.setdefault(c["gate"], {"n": 0, "mutants": 0, "killed": 0})
        g["n"] += 1
        g["mutants"] += int(c["total"])
        g["killed"] += int(c["killed"])
    add("A1", "arithmetic", "台账判据条数 12（含 1 条负控）", 12, len(crit),
        len(crit) == 12, "criteria_mutation_ledger.json#criteria")
    add("A1b", "arithmetic", "负控条数 1", 1, len(crit) - len(nonctl),
        len(crit) - len(nonctl) == 1, "criteria_mutation_ledger.json#criteria")
    tot_m = sum(int(c["total"]) for c in crit)
    tot_k = sum(int(c["killed"]) for c in crit)
    add("A2", "arithmetic", "变异体总数 66", 66, tot_m, tot_m == 66,
        "sum(criteria[].total)")
    add("A3", "arithmetic", "全部判据合计 killed 47/66", "47/66",
        "%d/%d" % (tot_k, tot_m), (tot_k, tot_m) == (47, 66), "sum(criteria[].killed)")
    rate_all = tot_k / tot_m
    add("A3b", "arithmetic", "合计 kill rate 71.2%", "71.2%", "%.1f%%" % (100 * rate_all),
        abs(rate_all - 0.7121) < 5e-4, "47/66")
    ctl_m = sum(int(c["total"]) for c in crit if c.get("control"))
    rate_acc = tot_k / (tot_m - ctl_m)
    add("A4", "arithmetic", "扣除负控后 79.7%", "79.7%", "%.1f%%" % (100 * rate_acc),
        abs(rate_acc - 0.7966) < 5e-4, "47/(66-7)")

    # §3.1 逐门表
    gate_rows = {"PAPER-TRACE": (3, 11, 18, "61.1%"),
                 "REPORT-QUALITY": (3, 7, 12, "58.3%"),
                 "REPORT-OWNERSHIP": (3, 15, 15, "100.0%"),
                 "CLIENT-PAYLOAD": (2, 14, 14, "100.0%"),
                 "NEGATIVE-CONTROL": (1, 0, 7, "0.0%")}
    for gname, (n, k, m, printed) in gate_rows.items():
        obs = by_gate.get(gname, {"n": 0, "killed": 0, "mutants": 0})
        ok = (obs["n"], obs["killed"], obs["mutants"]) == (n, k, m)
        add("A5-" + gname, "arithmetic", "§3.1 逐门 %s 行 = (%d 判据, %d/%d)" % (gname, n, k, m),
            [n, k, m], [obs["n"], obs["killed"], obs["mutants"]], ok, "ledger#criteria")
        if obs["mutants"]:
            r = "%.1f%%" % (100 * obs["killed"] / obs["mutants"])
            add("A5r-" + gname, "arithmetic", "§3.1 %s kill rate 印刷值" % gname,
                printed, r, r == printed, "killed/mutants")

    # §3.2 逐判据表
    per_crit = {"PT-PG4": (4, 7, "57%"), "PT-PG5": (3, 7, "43%"), "PT-PG7": (4, 4, "100%"),
                "RQ-PHYSICS": (2, 4, "50%"), "RQ-VALIDATION": (2, 4, "50%"),
                "RQ-FIGURES": (3, 4, "75%"), "RO-MISSION": (7, 7, "100%"),
                "RO-PNG-MAGIC": (4, 4, "100%"), "RO-PNG-IEND": (4, 4, "100%"),
                "PL-NAME": (7, 7, "100%"), "PL-DRIFT": (7, 7, "100%"),
                "NEG-TAUTOLOGY": (0, 7, "0%")}
    cmap = {c["cid"]: c for c in crit}
    for cid, (k, m, printed) in per_crit.items():
        c = cmap[cid]
        ok = (int(c["killed"]), int(c["total"])) == (k, m)
        add("A6-" + cid, "arithmetic", "§3.2 %s = %d/%d（印刷 %s）" % (cid, k, m, printed),
            [k, m], [int(c["killed"]), int(c["total"])], ok, "ledger#criteria[%s]" % cid)
        r = "%d%%" % round(100 * int(c["killed"]) / int(c["total"]))
        add("A6r-" + cid, "arithmetic", "§3.2 %s kill rate 印刷值" % cid, printed, r,
            r == printed, "killed/total")

    # 可实例化率 / 门数
    inst = [c for c in crit if c.get("instantiable")]
    add("A7", "arithmetic", "判据可实例化率 12/12 = 100%", "12/12",
        "%d/%d" % (len(inst), len(crit)), len(inst) == 12, "criteria[].instantiable")
    add("A8", "arithmetic", "纳入台账的验收门 4 个（负控不计门）", 4,
        len([g for g, v in by_gate.items() if g != "NEGATIVE-CONTROL"]),
        len([g for g, v in by_gate.items() if g != "NEGATIVE-CONTROL"]) == 4, "set(gate)")

    # M1 单调性：按 eps 统计被杀的 M1 变异体
    eps_kills: dict[float, int] = {}
    for c in crit:
        for mu in c.get("mutants") or []:
            if mu.get("class") != "M1":
                continue
            e = mu.get("eps")
            eps_kills[e] = eps_kills.get(e, 0) + (1 if mu.get("killed") else 0)
    grid = sorted(eps_kills)
    seq = [eps_kills[e] for e in grid]
    viol = sum(1 for i in range(1, len(seq)) if seq[i] < seq[i - 1])
    add("A9", "arithmetic", "§3.1 M1 单调性序列 ε=1%/3%/15% → [3,3,5]", [3, 3, 5], seq,
        seq == [3, 3, 5], "criteria[].mutants[class=M1]")
    add("A10", "arithmetic", "M1 单调性违例 0", 0, viol, viol == 0, "eps-grid pairwise")

    # 负控
    for c in crit:
        if not c.get("control"):
            continue
        add("A11", "arithmetic", "负控 %s killed 0/7" % c["cid"], [0, 7],
            [int(c["killed"]), int(c["total"])],
            (int(c["killed"]), int(c["total"])) == (0, 7), "ledger#criteria[control]")
        add("A11c", "arithmetic", "负控 killed 类 0/5", [0, 5],
            [int(c["killed_classes"]), int(c["classes_total"])],
            (int(c["killed_classes"]), int(c["classes_total"])) == (0, 5),
            "ledger#criteria[control].killed_classes")

    # §3.3 最弱 mutant 清单：逐条核 label（报告点名的变异体必须真在 survivor 里）
    weak = [("PT-PG4", "M1@1%"), ("PT-PG4", "M1@3%"), ("PT-PG4", "M4"),
            ("PT-PG5", "M1@1%"), ("PT-PG5", "M1@3%"), ("PT-PG5", "M2"), ("PT-PG5", "M4"),
            ("RQ-FIGURES", "M3"), ("RQ-PHYSICS", "M2"), ("RQ-PHYSICS", "M5"),
            ("RQ-VALIDATION", "M2"), ("RQ-VALIDATION", "M5")]
    bad = []
    for cid, label in weak:
        surv = {s.get("label") for s in (cmap[cid].get("survivors") or [])}
        if label not in surv:
            bad.append("%s:%s" % (cid, label))
    add("A12", "arithmetic", "§3.3 点名 12 个最弱 mutant 全部真在 survivor 集里", [],
        bad, not bad, "criteria[].survivors[].label")
    n_surv_nonctl = sum(int(c["total"]) - int(c["killed"]) for c in nonctl)
    add("A13", "arithmetic", "§3.3 清单完备性：非负控 survivor 共 12 个 == 清单行数",
        12, n_surv_nonctl, n_surv_nonctl == 12, "sum(total-killed) 非负控")

    # §3.4 AST 审计
    c6 = json.loads((art / "audit_c6_baseline.json").read_text())
    c7 = json.loads((art / "audit_c7_v3.json").read_text())
    add("A14", "arithmetic", "§3.4 基线 92/186 = 49.46%", [92, 186],
        [int(c6["killed"]), int(c6["total"])],
        (int(c6["killed"]), int(c6["total"])) == (92, 186), "audit_c6_baseline.json")
    add("A14r", "arithmetic", "基线 kill rate 49.5%（印刷）", "49.5%",
        "%.1f%%" % (100 * c6["killed"] / c6["total"]),
        "%.1f%%" % (100 * c6["killed"] / c6["total"]) == "49.5%", "92/186")
    add("A15", "arithmetic", "§3.4 现状 182/186 = 97.8%", [182, 186],
        [int(c7["killed"]), int(c7["total"])],
        (int(c7["killed"]), int(c7["total"])) == (182, 186), "audit_c7_v3.json")
    surv_names = [s.get("name") for s in (c7.get("survivors") or [])]
    cited = ["binop_swap[5]", "binop_swap[6]", "return_empty[0]", "return_empty[1]"]
    add("A16", "arithmetic", "§3.4 残留 4 个 survivor 且点名一致", cited, surv_names,
        surv_names == cited, "audit_c7_v3.json#survivors")
    add("A16b", "arithmetic", "现状 ≥168/186 门槛", "182>=168", 182 >= 168,
        182 >= 168, "audit_c7_v3.json")

    # §⑥ 门槛算术（此条是审核发现的算术瑕疵）
    add("A17", "arithmetic", "§⑥ 门槛印刷为「168/186（90.0%）」——真值 90.32%",
        "168/186 = 90.0%", "168/186 = %.2f%%" % (100 * 168 / 186),
        abs(100 * 168 / 186 - 90.0) < 0.05, "168/186",
        "印刷 90.0% 与 90.32% 差 0.32pp；§⑥ 同表余量按 90.0% 算得 7.8pp，按 168/186 应为 7.53pp")
    add("A17b", "arithmetic", "§⑥ 余量 14/186 = 7.53pp，报告写 7.8pp",
        "7.8pp", "%.2fpp" % (100 * (182 - 168) / 186),
        abs(100 * (182 - 168) / 186 - 7.8) < 0.05, "(182-168)/186",
        "两个基准混用：7.85pp 是 97.85-90.0，7.53pp 是 (182-168)/186")

    # 测试批次 / 域词 / C11 台账
    tr = json.loads((art / "test_runs.json").read_text())
    add("A18", "arithmetic", "C5 223 passed / 0 failed / 1 skipped",
        [223, 0, 1], [tr["total_passed"], tr["total_failed"], tr["total_skipped"]],
        (tr["total_passed"], tr["total_failed"], tr["total_skipped"]) == (223, 0, 1),
        "test_runs.json")
    add("A18b", "arithmetic", "批次可加性：51 + 172 = 223",
        223, tr["runs"][0]["passed"] + tr["runs"][1]["passed"],
        tr["runs"][0]["passed"] + tr["runs"][1]["passed"] == 223, "test_runs.json#runs")
    leak = json.loads((art / "domain_leak_scan.json").read_text())
    add("A19", "arithmetic", "C12 域词扫描 3 文件 / 37 词条 / 命中 0",
        [3, 37, 0], [len(leak["files_scanned"]), leak["word_count"], leak["hit_count"]],
        (len(leak["files_scanned"]), leak["word_count"], leak["hit_count"]) == (3, 37, 0),
        "domain_leak_scan.json")
    neg = json.loads((art / "gate_c11_negative.json").read_text())
    add("A20", "arithmetic", "C11 负控 exit 2 / NO_KILLER_TEST", [2, "NO_KILLER_TEST"],
        [neg["exit_code"], neg["rejected"][0]["reason"]],
        neg["exit_code"] == 2 and neg["rejected"][0]["reason"] == "NO_KILLER_TEST",
        "gate_c11_negative.json")
    pos = json.loads((art / "gate_c11_positive.json").read_text())
    add("A21", "arithmetic", "C11 正控 exit 0 且 bites=True", [0, True],
        [pos["exit_code"], all(k["bites"] for k in pos["killer_checks"])],
        pos["exit_code"] == 0 and all(k["bites"] for k in pos["killer_checks"]),
        "gate_c11_positive.json")
    add("A22", "arithmetic", "C11 正控 killer_checks 的 exit 必须是 1（真红），不能是 4（收集错误）",
        [1], sorted({k["exit"] for k in pos["killer_checks"]}),
        {k["exit"] for k in pos["killer_checks"]} == {1}, "gate_c11_positive.json",
        "台账里是 1=failed，符合；但 gate 代码把任意非 0 当 bites，见 R4")

    # 上游 01 包：资产清单完备性
    up = json.loads(Path(a.upstream).read_text())
    blk = up["blocks"][0]
    man = blk["outputs"]["asset_manifest.json"]
    add("U1", "replay", "上游 wp-6506-01 已发布（report 14673，01-asset-registration）",
        "01-asset-registration", blk["task_type"], blk["task_type"] == "01-asset-registration",
        "report 14673 kf_result block")
    add("U2", "replay", "上游 provenance.source_hash 与本单一致", "sha256:" + want,
        man["source_hash"], man["source_hash"] == "sha256:" + want, "upstream asset_manifest")
    add("U3", "replay", "上游 asset_manifest 含 assets[] 逐项（locator/类型/sha256）",
        "assets[] with locator+hash", "keys=" + ",".join(sorted(man)), False,
        "upstream asset_manifest.json",
        "只有计数与类型直方图，没有任何 asset 条目、locator 或 sha256 → 无法挂证据")
    add("U4", "replay", "上游 asset_count=17 与原文可枚举路径记号的关系（信息项）",
        "17", "见 observed", None, "asset_manifest.json#artifact_count",
        "信息项：报告正文出现 %d 个互不相同的路径样式记号（含 4 张图、CI yml、tests 文件），"
        "17 与之相容但清单未列出条目故不可逐条核对" % 0)

    # 原文里的路径样式记号（供 U4 参考）
    tokens = sorted({t for t in re.findall(r"`([^`\s]+?\.(?:py|json|yml|png|md))`", md)})
    checks[-1]["observed"] = "%d 个互不相同的路径记号：%s" % (len(tokens), ", ".join(tokens))
    checks[-1]["status"] = "unknown"

    # ── replay（git / pytest）──────────────────────────────────────────────
    tp = a.tp_repo
    if not tp:
        add("R0", "replay", "TensorPlatform 检出未提供 → replay 类检查 not_run", "run",
            "not_run", None, "--tp-repo 未给")
    else:
        def git(*args):
            p = subprocess.run(["git", *args], cwd=tp, capture_output=True, text=True)
            return p.returncode, p.stdout

        commit = a.tp_commit
        rc, out = git("ls-tree", "-r", "--name-only", commit)
        tracked = set(out.split())
        add("R1", "replay", "生产者提交里 tests/test_report_ownership.py 存在",
            True, "tests/test_report_ownership.py" in tracked,
            "tests/test_report_ownership.py" in tracked, "git ls-tree %s" % commit)
        n_art = len([x for x in tracked if x.startswith("artifacts/m5496/")])
        add("R2", "replay", "生产者提交里 artifacts/m5496 台账入库（12 个）", 12, n_art,
            n_art == 12, "git ls-tree %s | grep artifacts/m5496" % commit)
        rc, out = git("show", "%s:tests/test_report_ownership.py" % commit)
        n_def = len(re.findall(r"def test_", out))
        add("R3", "replay", "「21 条」需要参数化展开才成立：该提交 def test_ 18 个",
            "18 defs (+3 参数化)", "%d defs" % n_def, None,
            "git show %s:tests/test_report_ownership.py" % commit,
            "def 计数 18 ≠ 21；21 只能由 parametrize 展开得到（未在本次审核中复跑该文件）")
        rc, out = git("ls-tree", "-r", "--name-only", "HEAD")
        head_tracked = set(out.split())
        add("R4", "replay", "当前 main HEAD 上 tests/test_report_ownership.py 仍存在（报告引用它）",
            True, "tests/test_report_ownership.py" in head_tracked,
            "tests/test_report_ownership.py" in head_tracked, "git ls-tree HEAD",
            "HEAD 上不存在；同时 artifacts/m5496 在 HEAD 上 %d 个文件 → 报告里的复算入口在 main 上不可解析"
            % len([x for x in head_tracked if x.startswith("artifacts/m5496/")]))
        rc, out = git("rev-parse", "HEAD")
        checks[-1]["note"] += "（HEAD=%s）" % out.strip()[:9]

        if a.run_tests:
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            p = subprocess.run([sys.executable, "-m", "pytest", "tests/test_criteria_mutation.py",
                                "-q", "-p", "no:cacheprovider"],
                               cwd=tp, capture_output=True, text=True, env=env, timeout=600)
            tail = (p.stdout or "").strip().splitlines()[-1:]
            add("R5", "replay", "tests/test_criteria_mutation.py 30 条全绿（报告 C5/C11 的前提）",
                "30 passed", tail[0] if tail else "(no output)", p.returncode == 0,
                "pytest tests/test_criteria_mutation.py -q (cwd=TensorPlatform worktree)",
                "复现：1 failed, 29 passed —— 失败用例 test_gate_rejects_toothless_killer")
            fails = [l for l in (p.stdout or "").splitlines() if l.startswith("FAILED")]
            add("R6", "replay", "失败用例定位", "none", fails[0] if fails else "none",
                not fails, "pytest stdout")
            p2 = subprocess.run([sys.executable, "-m", "pytest", "tests/test_criteria_mutation.py",
                                 "-q", "--noconftest", "-p", "no:cacheprovider"],
                                cwd=tp, capture_output=True, text=True, env=env, timeout=600)
            add("R7", "replay", "报告附录/CI 命令 `pytest tests/test_criteria_mutation.py -q --noconftest` 可收集",
                "exit 0", "exit %d" % p2.returncode, p2.returncode == 0,
                "pytest -q --noconftest", "收集错误：ModuleNotFoundError: No module named 'tools.audit'")
            p3 = subprocess.run([sys.executable, "-m", "pytest",
                                 "backend/tests/test_paper_traceability_gate_kills_v3.py",
                                 "-q", "-p", "no:cacheprovider"],
                                cwd=tp, capture_output=True, text=True, env=env, timeout=900)
            add("R8", "replay", "v3 killer 测试 12 条全绿（报告 C7 的测试侧）", "12 passed",
                (p3.stdout or "").strip().splitlines()[-1:][0] if p3.stdout.strip() else "",
                p3.returncode == 0, "pytest backend/tests/test_paper_traceability_gate_kills_v3.py")
    if not a.run_tests:
        add("R5", "replay", "pytest 复现未跑（未给 --run-tests）", "run", "not_run", None, "")

    # ── 结论聚合 ───────────────────────────────────────────────────────────
    n_pass = sum(1 for c in checks if c["status"] == "pass")
    n_fail = sum(1 for c in checks if c["status"] == "fail")
    n_unk = sum(1 for c in checks if c["status"] == "unknown")
    by_kind: dict[str, dict[str, int]] = {}
    for c in checks:
        d = by_kind.setdefault(c["kind"], {"pass": 0, "fail": 0, "unknown": 0})
        d[c["status"]] += 1
    evidence = {
        "reviewer": "wp-6506-04 reviewer (agent, mission 15845)",
        "reviewed_package": "wp-6506-01",
        "source": {"path": a.source, "chars": len(md), "sha256": got},
        "upstream_artifacts": {
            "dir": str(art),
            "origin": "TensorPlatform@%s:artifacts/m5496/*.json" % a.tp_commit,
            "sha256": {f.name: sha256_bytes(f.read_bytes())
                       for f in sorted(art.glob("*.json"))},
        },
        "counts": {"total": len(checks), "pass": n_pass, "fail": n_fail, "unknown": n_unk,
                   "by_kind": by_kind},
        "checks": checks,
    }
    Path(a.out).write_text(json.dumps(evidence, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(evidence["counts"], ensure_ascii=False))
    print("-> %s" % a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())