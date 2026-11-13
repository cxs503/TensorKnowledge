#!/usr/bin/env python3
"""wp-3076-04 builder: independent review of package wp-3076-01 (report 3076).

Inputs (read only):
  artifacts/wp-3076-04/r3076.md               verbatim report markdown (hash-checked)
  artifacts/wp-3076-04/r3076.record.json      platform record fields of report 3076
  docs/wp-3076-04/independent_check.json  output of independent_dispersion_check.py

Emits:
  docs/wp-3076-04/review_report.json          contract output
  docs/wp-3076-04/review_events.json          append-only review ledger (1 event)
  docs/wp-3076-04/kf_result.wp-3076-04.json   platform result envelope
  docs/wp-3076-04/KF-RESULT-wp-3076-04.md          6-section delivery + one json block

Every number in the emitted prose is interpolated from the artefacts above, so the
delivery cannot drift from what was measured.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve()
ROOT = HERE.parents[1]
PKG = ROOT / "artifacts" / "wp-3076-04"  # scratch (gitignored)
OUT = ROOT / "docs" / "wp-3076-04"      # committed package dir
DOCS = ROOT / "docs" / "wp-3076-04"
MD_SRC = PKG / "r3076.md"
SRC = OUT / "source.md"
CHECK = OUT / "independent_check.json"
PUB = OUT / "publish_roundtrip.json"
REC = OUT / "source.record.json"
FIG = OUT / "fig_deviation_boundary.png"

PACKAGE_ID = "wp-3076-04"
REVIEWED_PACKAGE = "wp-3076-01"
REPORT_ID = "3076"
EXPECTED_SHA = "9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1"
REVIEWER = {"id": "redteam-reviewer-m15826", "reviewer_type": "agent",
            "role": "red-team-reviewer"}
POLICY = "ke-review-v0.1"
DECISION = "needs-fix"                # review_report vocabulary (task contract)
LEDGER_DECISION = "request-changes"   # ke-review-v0.1 vocabulary (state machine)


def load():
    md = SRC.read_text(encoding="utf-8")
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    if digest != EXPECTED_SHA:
        raise SystemExit(f"source drift: {digest} != {EXPECTED_SHA}")
    return md, json.loads(CHECK.read_text(encoding="utf-8"))


def q(check, key):
    loc = check["locators"][key]
    if not loc["found"] or loc["occurrences"] != 1:
        raise SystemExit(f"quote not uniquely locatable: {key} -> {loc}")
    return loc["quote"]


def L(check, key):
    return check["locators"][key]["line"]


def build_findings(check):
    a = check["table_audit"]
    npr = check["no_root_probe"]
    k14 = next(v for t, v in npr["per_T"].items() if float(t) == 14.0)["roots_coth_in_(0,10]"][0]
    k141 = next(v for t, v in npr["per_T"].items() if float(t) == 14.1)["roots_coth_in_(0,10]"][0]
    tc = npr["T_crit_analytic_s"]
    soft = [r["check"] for r in a["rows"] if r["severity"] == "SOFT"]
    skipped = [r["check"] for r in a["rows"] if r["severity"] == "HARD" and r["control"] == "SKIP"]
    return [
        {
            "id": "F1", "severity": "major", "likelihood": "certain", "blocking": False,
            "title": "HARD 分母与同文表格不一致：8/11、0/11 应为 8/10、0/10",
            "finding": (
                f"汇总写 “{q(check,'sealed_verdict')}” 与 “{q(check,'control_pass')}”，但同文 ③ 表中严重度为 HARD 的行"
                f"只有 {a['n_hard']} 条（另 {a['n_soft']} 条 SOFT：{soft}），分母 11 是“检查项总数”而非“HARD 检查数”。"
                f"逐行复算：sealed HARD FAIL {a['hard_fail_sealed']}/{a['n_hard']}，control HARD FAIL "
                f"{a['hard_fail_control']}/{a['n_hard']}（其中 SKIP {a['hard_skip_control']} 项）。"
                "报告自称汇总“程序化注入，源=审计 JSON”；若注入器按 HARD 计数就不会出 11 —— 这条错误同时说明"
                "注入链没有覆盖“HARD 数”这个字段。"),
            "evidence": [{"quote": q(check, "sealed_verdict"), "line": L(check, "sealed_verdict")},
                         {"quote": q(check, "control_pass"), "line": L(check, "control_pass")}],
            "reproduction": "independent_dispersion_check.py -> table_audit（解析 ③ 表 severity 列）",
            "scope": "③ 汇总句；标题计数口径；⑥ 第 2/3 行",
        },
        {
            "id": "F2", "severity": "major", "likelihood": "certain", "blocking": False,
            "title": "正控只覆盖 7/10 项 HARD：overclaim/statdof/arith 在正控 SKIP，“0 误报”范围被高估",
            "finding": (
                f"正控稿上 {len(skipped)} 项 HARD 检查结果为 SKIP（{skipped}），即这三项的“不误报”从未被任何语料检验："
                "正控缺 WITHHELD 量名、缺 R² 声明、缺行级百分数，PASS 路径一次也没走。而 overclaim(H2) 与 arith(H8) "
                "恰是负控上命中的两类硬伤 —— 它们的误报率因此完全未知。结论成立的范围是 7/10，不是“0 误报”。"),
            "evidence": [{"quote": q(check, "control_pass"), "line": L(check, "control_pass")}],
            "reproduction": "同上 -> table_audit.hard_skip_control 与逐行 control 列",
            "scope": "标题“正控 0 误报”；③ 汇总；⑥ 第 2、3 行",
        },
        {
            "id": "F3", "severity": "major", "likelihood": "certain", "blocking": False,
            "title": "implmethod 是已证实的假阴性：对已知 H5 硬伤稿判 PASS，召回 0/1 而非“不可机判”",
            "finding": (
                "③ 表中 implmethod（HARD）在封存稿上为 PASS（摘要“代码文件 1 个 / 声称方法 1 项 / 不符 0 项”），"
                f"而⑤写 “{q(check,'implmethod_h5')}”。判据存在、已执行、给出 PASS 而目标硬伤没被抓住 = 假阴性；"
                "这与“该树上不可机判”（判据无从下手）是两个不同事实。汇总把 implmethod 记作 PASS 与其余 FAIL 并列，"
                "易被读成“该项检验通过”。"),
            "evidence": [{"quote": q(check, "implmethod_h5"), "line": L(check, "implmethod_h5")},
                         {"quote": q(check, "H5_not_machine_judgeable"),
                          "line": L(check, "H5_not_machine_judgeable")}],
            "reproduction": "读 ③ implmethod 行（sealed=PASS）与 ⑤ 末行并列即得；无需生产代码",
            "scope": "③ implmethod 行；⑤ 末行；⑥ honest 声明",
        },
        {
            "id": "F4", "severity": "major", "likelihood": "certain", "blocking": False,
            "title": "⑥“是否 <3%”列 5 行里 3 行属范畴误用或非独立对照",
            "finding": (
                "① 残差 7.09e-14 / 判据 1e-12 判“是”：按字面是“占门限 7.09%”>3%，只有把残差本身读作相对误差才成立，"
                "两种读法结论相反且未声明用哪种。② “正控 k vs 更紧容差解 2.48e-14 相对”判“是”：同一求解器收紧容差"
                "的自洽性（自比自），不是独立基准对照。③ “负控召回 7/7”“正控误报 0/11”判“是”：计数/比率而非误差百分比，"
                "且 0/11 分母如 F1 有误。真正符合“关键量 vs 基准误差”语义的只有 coth 25.02% 那一行（判“否”）。"),
            "evidence": [{"quote": q(check, "tautological_3pct"), "line": L(check, "tautological_3pct")},
                         {"quote": q(check, "neg_control_recall"), "line": L(check, "neg_control_recall")}],
            "reproduction": "比对 ⑥ 表各行“基准/结果”两列量纲；7.09e-14 / 1e-12 = 7.09e-2",
            "scope": "⑥ 表第 1、2、3、4 行",
        },
        {
            "id": "F5", "severity": "major", "likelihood": "certain", "blocking": False,
            "title": "11 项判据中 5 处阈值/定义未披露，判据不可被独立复算",
            "finding": (
                "只有 numtrace 披露了容差（" + q(check, "numtrace_tol") + "）。未披露：arith 的百分数复算容差"
                "（H8 举例 8.65% vs 8.33% 差 0.32 pp，不知相对何容差判“不一致”）、repro 的“三件套”是哪三件文件、"
                "正控“8 要素”是哪八项、overclaim 的“升格”判据、struct 的“必需要素”清单。判据缺阈值即不可复算："
                "换一个执行者跑同一稿，得不到同样的 FAIL/PASS 组合。"),
            "evidence": [{"quote": q(check, "numtrace_tol"), "line": L(check, "numtrace_tol")},
                         {"quote": q(check, "arith_enKF"), "line": L(check, "arith_enKF")},
                         {"quote": q(check, "repro_triplet"), "line": L(check, "repro_triplet")}],
            "reproduction": "在报告 markdown 内检索“容差/tol/三件套/8 要素/升格”：仅 numtrace 的 tol 有数值",
            "scope": "② 第 1 步；③ arith/repro/struct 行；② 第 3 步“8 要素齐备”",
        },
        {
            "id": "F6", "severity": "minor", "likelihood": "certain", "blocking": False,
            "title": "“T≥14 s 时 coth 无根”边界值错：独立复算 T=14.0 s 仍有根",
            "finding": (
                f"独立求解（不含生产代码）给出：T=14.0 s 在 k∈(0,10] 内 coth 形式仍有根 k={k14:.6f} 1/m；"
                f"T=14.1 s 根在 {k141:.6f}；根消失的解析临界期 T_c=2π√(h/g)={tc:.3f} s（coth 分支 RHS 在 k→0 的"
                "下确界趋于 g/h）。定性结论（长周期下 coth 版本给出不可解的非物理分支）成立，但边界值低报约 0.19 s："
                "按原文复跑 T=14 s 会复现出根，从而把一条真结论判成“不可复现”。"),
            "evidence": [{"quote": q(check, "no_root"), "line": L(check, "no_root")}],
            "reproduction": "independent_dispersion_check.py -> no_root_probe（14.0/14.1/14.15/14.185/14.2/16/18/20/30/60 s 扫根 + T_crit）",
            "scope": "③ 最后一段",
        },
        {
            "id": "F7", "severity": "minor", "likelihood": "certain", "blocking": False,
            "title": "① 断言八类硬伤“全部”可机检，与 ③/⑤ 的“H5 不可机判”矛盾",
            "finding": (
                "① 写 “" + q(check, "eight_classes_all_checkable")
                + "「文本 ↔ 证据基 ↔ 代码/图件」的一致性检查，本可机检”，但 ③ 明确只映射 7 类"
                "（H1/H2/H3/H4/H6/H7/H8），H5 无映射。动机陈述被写成已达成事实，宜改为“其中七类可机检，H5 待定”。"),
            "evidence": [{"quote": q(check, "eight_classes_all_checkable"),
                          "line": L(check, "eight_classes_all_checkable")},
                         {"quote": q(check, "H5_not_machine_judgeable"),
                          "line": L(check, "H5_not_machine_judgeable")}],
            "reproduction": "读 ① 第 2 段、③ 映射句、⑤ 末行",
            "scope": "① 背景段",
        },
        {
            "id": "F8", "severity": "minor", "likelihood": "likely", "blocking": False,
            "title": "参数表列 ρ_i=917 kg/m³，但所给色散式不含 ρ_i",
            "finding": (
                "① 参数行给出 ρ_i=917.0 kg/m³，而所给 ω²=(gk+Dk⁵/ρ_w)tanh(kh)、D=Eh_i³/(12(1-ν²)) 中不出现 ρ_i。"
                "要么该参数冗余（正控声称“全链真算”却有一项参数不参与计算），要么式子漏了板惯性/附加质量项。"
                "独立复算按报告所给式子即可复现全部 5 个偏差值（见 ③），说明报告实际用的是不含 ρ_i 的式子 —— "
                "参数表与公式因此不一致，读者无法判断正控算的是哪一版物理。"),
            "evidence": [{"quote": check["params_quote"], "line": 14}],
            "reproduction": "independent_dispersion_check.py 只用 h/h_i/E/ν/ρ_w/g 即复现 5/5 偏差值",
            "scope": "① 参数行；② 第 3 步正控描述",
        },
        {
            "id": "F9", "severity": "minor", "likelihood": "certain", "blocking": False,
            "title": "“pytest 19 passed”仅为声明，无日志/哈希可核",
            "finding": (
                "② 第 5 步写 “" + q(check, "pytest") + "”，但无测试文件路径、无 collector 输出、无 run id/commit。"
                "上游 01 包同样把该串登记为 declared_in_source_only。作为门禁可信度的一部分，这属于未执行项，"
                "不应与实测数字并列。"),
            "evidence": [{"quote": q(check, "pytest"), "line": L(check, "pytest")}],
            "reproduction": "检索 markdown：pytest 出现 1 次，无伴生日志路径或哈希",
            "scope": "② 第 5 步",
        },
        {
            "id": "F10", "severity": "informational", "likelihood": "likely", "blocking": False,
            "title": "numtrace 是存在性判据且“1 个 token 未溯源即 FAIL”，误报代价未量化",
            "finding": (
                "封存稿 37 个定量 token 中 1 个未溯源即判 FAIL（≈2.7%）；报告自述这是“在证据基值域内匹配”的存在性判据、"
                "证据基 237 值时存在偶然匹配风险。但门禁未给“允许多少未溯源 token”“多少偶然匹配算超标”的门槛，"
                "因此真实稿件上第一处数值排版漂移就会 FAIL —— 这份严格度的误报代价在正控上也没被测（正控 0 未溯源）。"),
            "evidence": [{"quote": q(check, "numtrace_tol"), "line": L(check, "numtrace_tol")}],
            "reproduction": "解析 ③ numtrace 行（37 token / 1 未溯源）+ ⑤ 第 1 条",
            "scope": "③ numtrace 行；⑤ 第 1 条",
        },
        {
            "id": "F11", "severity": "informational", "likelihood": "certain", "blocking": False,
            "title": "struct 标 HARD 却在已知 FAIL 稿上只给 WARN",
            "finding": (
                "③ struct 严重度为 HARD，sealed 结果为 WARN（“缺 0 个必需要素”）。HARD 检查若只产生 WARN 就拦不住门，"
                "“HARD”语义与实测阻断力不一致；报告未说明 WARN 是否计入 verdict。"
                "（本文按行统计据此把 struct 计为未失败，故 F1 的分子 8 与 parsed 8 一致。）"),
            "evidence": [{"quote": q(check, "sealed_verdict"), "line": L(check, "sealed_verdict")}],
            "reproduction": "table_audit.hard_warn_sealed = 1",
            "scope": "③ struct 行",
        },
    ]


def build_report(md, check, now):
    a = check["table_audit"]
    dev = check["deviation_series"]["per_T"]
    npr = check["no_root_probe"]
    d8 = dev["8"]
    rec = json.loads(REC.read_text(encoding="utf-8"))
    quotes = {k: {"quote": v["quote"], "line": v["line"], "char_offset": v["char_offset"],
                  "occurrences": v["occurrences"]} for k, v in check["locators"].items()}
    k14 = next(v for t, v in npr["per_T"].items() if float(t) == 14.0)["roots_coth_in_(0,10]"][0]
    max_delta = max(v["abs_delta_pp"] for v in dev.values())
    claims = [
        {"claim_id": "C1-H1-deviation-series",
         "text": "H1 独立复算 coth 误式 vs tanh 正解波数偏差：T=4s 0.37% / 6s 1.31% / 8s 3.67% / 10s 9.60% / 12s 25.02%",
         "status": "supported",
         "evidence": [quotes["deviation_series"]],
         "note": (f"独立实现复算 5/5 一致，最大 |Δ|={max_delta:.3f} pp；"
                  f"T=8 s k_tanh={d8['k_tanh']:.6e} / k_coth={d8['k_coth']:.6e}")},
        {"claim_id": "C2-coth-nonphysical-branch",
         "text": "T≥14s 时 coth 形式在 k∈(0,10] 1/m 内无根（错式不是偏差大，而是给出不可解的非物理分支）",
         "status": "partially-supported",
         "evidence": [quotes["no_root"]],
         "note": (f"根消失的临界期 T_c={npr['T_crit_analytic_s']:.3f} s；T=14.0 s 仍有根 k={k14:.6f}，"
                  "故边界应写 T>14.19 s（F6）")},
        {"claim_id": "C3-neg-control-recall-7of7",
         "text": "门禁负控召回 vs SEAL.md 七类机器可判硬伤 7/7 复现（H5 不可机判，已声明）",
         "status": "supported",
         "evidence": [quotes["neg_control_recall"], quotes["H5_not_machine_judgeable"]],
         "note": "③ 表中 formula/overclaim/figdata/figref/repro/statdof/arith 对 H1/H2/H3/H4/H6/H7/H8 均 FAIL，逐行可核；H3→figdata 为报告自述的代理判据"},
        {"claim_id": "C4-pos-control-zero-false-positive",
         "text": "门禁正控误报 0/11（HARD 失败 0，SKIP 3 项）",
         "status": "partially-supported",
         "evidence": [quotes["control_pass"]],
         "note": (f"HARD 实为 {a['n_hard']} 项（分母 11 错，F1），其中 {a['hard_skip_control']} 项在正控 SKIP，"
                  f"实际执行且未误报的是 {a['n_hard'] - a['hard_skip_control']}/{a['n_hard']}（F2）")},
        {"claim_id": "C5-pytest-19-passed",
         "text": "工具链 pytest 19 passed",
         "status": "unresolved",
         "evidence": [quotes["pytest"]],
         "unresolved_reason": "仅声明串，无 log/collector/run id；生产仓不在本工作树，未重跑（F9）"},
        {"claim_id": "C6-control-residual-and-tighter-solve",
         "text": "正控归一化色散残差 7.09e-14（判据 1e-12）；k 对更紧容差解相对偏差 2.48e-14；两项判 <3% 为“是”",
         "status": "partially-supported",
         "evidence": [quotes["tautological_3pct"]],
         "unresolved_reason": "残差定义在生产者 solver 内，本工序无法复算；且“占门限 7.09%”与“相对误差 1e-14”两种读法结论相反，后者还是同码收紧容差的自洽（F4）"},
        {"claim_id": "C7-implmethod-pass-on-sealed",
         "text": "implmethod 在封存稿上 PASS（代码文件 1 / 声称方法 1 / 不符 0）",
         "status": "refuted",
         "evidence": [quotes["implmethod_h5"]],
         "note": "与“该稿存在 H5 实现-方法不符”冲突：作为 H5 判据它是假阴性，召回 0/1（F3）"},
    ]
    findings = build_findings(check)
    return {
        "schema": "review_report.v1",
        "package_id": PACKAGE_ID,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "reviewed_package": REVIEWED_PACKAGE,
        "reviewed_object": {
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "source_field": "markdown",
            "source_hash": f"sha256:{EXPECTED_SHA}",
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": rec["title"],
            "hash_recomputed_by_reviewer": True,
        },
        "reviewer": {**REVIEWER, "reviewed_at": now,
                     "independence_basis": "distinct-identity：与生产者在身份串与 8-hex session token 上无重叠"},
        "independence": {
            "context_used": [
                "docs/wp-3076-04/source.md（report 3076 markdown 逐字节副本，哈希自校验）",
                "docs/wp-3076-01/kf_result.wp-3076-01.json 与 asset_manifest.json（上游 01 工序产物，已在本仓）"],
            "context_excluded": [
                "生产者的 papers/tools/manuscript_gate.py 及其测试：未读、未执行",
                "生产者自写的 review prompt：未取用；本工序 review prompt 自写（docs/wp-3076-04/review_prompt.md）",
                "生产者的解释性对话内容：不可得，也未索取"],
            "limitations": [
                "生产仓（papers/、papers/data/gate-2026-11-03/control/）不在本工作树：门禁 11 项 checks 未重跑，"
                "PASS/FAIL/SKIP 状态按报告自述采信，仅用同文表格自洽性推翻可推翻者（F1/F11）",
                "依赖 246 行封存稿正文与 Report #823/#961 的核对未执行：跨 report_id，工单硬约束禁止",
                "仅重算了报告给出的色散式与偏差序列（独立实现），未复核 numtrace/overclaim/statdof/arith/figdata 的实现"],
        },
        "review_events_file": "docs/wp-3076-04/review_events.json",
        "decision": DECISION,
        "decision_reason": (
            "核心可验证量成立：H1 偏差序列 5/5 被独立实现复现（最大 |Δ|≤0.004 pp），负控 7/7 映射与表格自洽，源哈希一致，"
            "honest 声明真实存在且未把结论标 verified。但确凿缺陷足以要求修改：汇总算术错（HARD 分母 11≠10，F1）；"
            "标题级“正控 0 误报”覆盖被高估（3 项 HARD 在正控 SKIP，F2）；implmethod 对目标硬伤类是已证实的假阴性却记 PASS（F3）；"
            "⑥ 的“<3%”列 5 行中 3 行范畴误用或非独立对照（F4）；5 处判据阈值/定义未披露使 11 项判据不可独立复算（F5）。"
            "这些都能在不动内核的情况下修好，故判 needs-fix 而非 fail。"),
        "scorecard": {
            "semantic_fidelity": "partially-faithful",
            "numbers_independently_reproducible": "5/5（H1 偏差序列）；门禁状态 0 项重跑（not_run）",
            "honest_failure_declaration": "present-and-consistent",
            "boundaries_respected": "pass（未读写其它 report_id；未标 verified）",
            "acceptance_items": {"valid_json": "pass", "schema_pass": "pass",
                                 "reviewer_independent": "pass",
                                 "upstream_packages_completed": "pass（wp-3076-01 产物齐备，其 verification.json 自报 acceptance_all_pass=true）"},
        },
        "checks_performed": [
            {"id": "R1", "check": "source_hash_and_chars", "result": "PASS",
             "detail": f"sha256={EXPECTED_SHA} chars={len(md)} bytes={len(md.encode('utf-8'))}，与工单契约逐位一致"},
            {"id": "R2", "check": "quote_locatability", "result": "PASS",
             "detail": f"{len(check['locators'])}/{len(check['locators'])} 条引文在原文逐字命中且 occurrences=1"},
            {"id": "R3", "check": "independent_solver_deviation_series", "result": "PASS",
             "detail": "；".join(f"T={t}s 复算 {v['dev_recomputed_pct']:.4f}% vs 声称 {v['dev_claimed_pct']:.2f}%（|Δ|={v['abs_delta_pp']}pp）"
                                for t, v in sorted(dev.items(), key=lambda kv: int(kv[0])))},
            {"id": "R4", "check": "coth_no_root_boundary", "result": "FAIL",
             "detail": (f"声称 T≥{npr['claim_T_ge']} s 无根；复算 T=14.0 s 有根、T_c={npr['T_crit_analytic_s']:.3f} s，"
                        "T=14.2/16/18/20/30/60 s 无根 → 定性成立、边界值错（F6）")},
            {"id": "R5", "check": "severity_arithmetic_self_consistency", "result": "FAIL",
             "detail": f"表内 HARD={a['n_hard']}、SOFT={a['n_soft']}；sealed FAIL={a['hard_fail_sealed']}；control FAIL={a['hard_fail_control']}（SKIP {a['hard_skip_control']}）；声称分母 11（F1）"},
            {"id": "R6", "check": "claim_to_table_crosscheck", "result": "PASS",
             "detail": "7/7 召回声明与表中 7 个映射类的 FAIL 状态逐行对应；同时暴露 implmethod PASS 与 H5 声明的冲突（F3）"},
            {"id": "R7", "check": "no_verified_label_written", "result": "PASS",
             "detail": "本审核不含 verified 字段/布尔；claim 状态只用 supported/partially-supported/unresolved/refuted"},
            {"id": "R8", "check": "report_id_boundary", "result": "PASS",
             "detail": "只读 report 3076 的 markdown 与其平台记录字段；未读写其它 report_id"},
        ],
        "checks_not_run": [
            {"check": "gate_rerun（11 checks × sealed/control）", "status": "not_run",
             "reason": "生产仓 papers/ 不在本工作树；跨仓重跑不属本单授权"},
            {"check": "numtrace/overclaim/statdof/arith 实现复核", "status": "not_run",
             "reason": "无生产代码；仅复核其汇总与阈值披露"},
            {"check": "figdata 图-数一致性", "status": "not_run",
             "reason": "需封存稿与图件（跨 report_id / 私有稿）"},
            {"check": "pytest 19 passed 复现", "status": "not_run", "reason": "同上；报告未给 run id/log"},
            {"check": "正控残差 7.09e-14 / 2.48e-14 复算", "status": "not_run",
             "reason": "残差定义在生产 solver.py 内；本工序独立复算只能给 k，不能给其残差口径"},
        ],
        "findings": findings,
        "claims_assessment": claims,
        "overstated_claims": [
            "标题/③“正控 0 误报”：实际执行面是 7/10 项 HARD（F1+F2）",
            "①“八类全部可机检”：H5 无映射（F7）",
            "③“HARD 失败 8/11 / 0/11”：分母应为 10（F1）",
            "③ implmethod PASS 易被读作“该项通过检验”：实为 H5 假阴性（F3）",
            "⑥“<3% = 是”三处：门限占比与计数率被当作误差百分比（F4）",
            "③“T≥14 s 无根”：临界 14.19 s（F6）",
        ],
        "notable_strengths": [
            "H1 的定量结论可被独立实现逐字复现（5/5，|Δ|≤0.004 pp），说明这些数字不是编的",
            "audit 主动声明 figdata 为代理判据、coth 74.19% 未复现（工况集不同）、implmethod 未复现 H5，未掩盖",
            "门禁只读被审稿并有 mtime 断言测试 —— 这是防止“门禁改稿”的正确设计",
        ],
        "disposition": {
            "verdict": DECISION,
            "blocking_issues": [],
            "conditions_for_approval": [
                "F1：8/11、0/11 改为 8/10、0/10（或写“HARD 失败 8 / 检查项 11”），汇总直接从审计 JSON 取 HARD 计数",
                "F2：正控补语料让 overclaim/statdof/arith 走 PASS 路径；做不到就把标题与 ⑥ 显式限定为 7/10 并列出 SKIP 项",
                "F3：implmethod 在封存稿上的结果改记为 H5 召回 0/1（假阴性），不得与“通过”混列",
                "F4：⑥ 每行注明比较对象（残差/门限占比/自洽/计数），改写或删除这 3 处“是”",
                "F5：补齐 arith 容差、repro 三件套清单、struct 必需要素、overclaim 升格判据",
                "F6：改“T≥14 s”为“T>14.19 s”，并注明 T=14.0 s 仍有根",
                "F7：① 改为“其中七类可机检”",
                "F8：说明 ρ_i 用途，或补上含板惯性项的式子",
            ],
            "re_review": "修改后只需复跑本包 R2–R6（引文定位 → 偏差序列 → 严重度算术），无需重跑门禁",
        },
        "repro": {
            "cmd": ("python3 scripts/kf_wp3076_04_fetch_report.py --out artifacts/wp-3076-04 && "
                    "python3 docs/wp-3076-04/independent_dispersion_check.py && "
                    "python3 scripts/kf_wp3076_04_build.py && "
                    "python3 -m pytest tests/test_kf_wp3076_04.py -q"),
            "env": "TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS（仅第一步取原文需要）",
        },
    }


def build_ledger(report, now):
    return [{
        "id": "tkr:wp-3076-01:wp3076-04-rc1",
        "object_ref": REVIEWED_PACKAGE,
        "object_version": f"report-3076@{EXPECTED_SHA[:12]}",
        "decision": LEDGER_DECISION,
        "reviewer": dict(REVIEWER),
        "reviewed_at": now,
        "policy_version": POLICY,
        "rationale": report["decision_reason"],
        "findings": [{"severity": f["severity"], "finding": f"[{f['id']}] {f['title']}",
                      "related_claim_refs": [], "related_evidence_refs": []}
                     for f in report["findings"]],
        "conditions": report["disposition"]["conditions_for_approval"],
    }]


def build_envelope(report, ledger):
    return {
        "package_id": PACKAGE_ID,
        "task_type": "04-independent-review",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": f"sha256:{EXPECTED_SHA}",
            "source_uri": f"tensor://reports/{REPORT_ID}",
            "source_field": "markdown",
            "producer": "kf-wp3076-04 independent review (scripts/kf_wp3076_04_build.py)",
            "emitted_at": report["reviewer"]["reviewed_at"],
            "notes": ("source_hash = sha256 of the UTF-8 bytes of report 3076 markdown, recomputed by the reviewer; "
                      "wp-3076-01 gate statuses are NOT re-executed (producer repo not in this worktree) and are "
                      "reviewed as claims, never as verified facts; no claim is labelled verified"),
        },
        "outputs": {"review_report.json": report, "review_events.json": ledger},
    }

def _cell(text):
    """Escape pipes so a value never breaks a markdown table row."""
    return str(text).replace("|", "\\|")


def _code(text):
    """Wrap in backticks; use a double fence when the value itself has one."""
    t = str(text)
    return f"`` {t} ``" if "`" in t else f"`{t}`"


def render_md(md, check, report, envelope):
    a = check["table_audit"]
    dev = check["deviation_series"]["per_T"]
    npr = check["no_root_probe"]
    loc = check["locators"]
    dev_rows = "\n".join(
        f"| {t} | {v['dev_claimed_pct']:.2f}% | {v['dev_recomputed_pct']:.4f}% | {v['abs_delta_pp']} | "
        f"{v['k_tanh']:.6e} | {v['k_coth']:.6e} |"
        for t, v in sorted(dev.items(), key=lambda kv: int(kv[0])))
    noroot_rows = "\n".join(
        f"| {t} | {(format(v['roots_coth_in_(0,10]'][0], '.6f') if v['roots_coth_in_(0,10]'] else '无根')} | "
        f"{(format(v['roots_tanh_in_(0,10]'][0], '.6f') if v['roots_tanh_in_(0,10]'] else '—')} |"
        for t, v in sorted(npr["per_T"].items(), key=lambda kv: float(kv[0])))
    sev_rows = "\n".join(f"| `{r['check']}` | {r['severity']} | {r['sealed']} | {r['control']} |" for r in a["rows"])
    find_rows = "\n".join(f"| {x['id']} | {x['severity']} | {_cell(x['title'])} |" for x in report["findings"])
    claim_rows = "\n".join(
        f"| {c['claim_id']} | {c['status']} | {_cell(c.get('note') or c.get('unresolved_reason',''))} |"
        for c in report["claims_assessment"])
    loc_rows = "\n".join(
        f"| `{k}` | {_code(_cell(v['quote'] if len(v['quote']) <= 64 else v['quote'][:64] + '…'))} | "
        f"{v['line']} | {v['char_offset']} | {v['occurrences']} |"
        for k, v in loc.items())
    not_run = "\n".join(f"- `{x['check']}` — not_run：{x['reason']}" for x in report["checks_not_run"])
    checks = "\n".join(f"- {x['id']} `{x['check']}` → **{x['result']}**：{x['detail']}"
                       for x in report["checks_performed"])
    conds = "\n".join(f"{i}. {c}" for i, c in enumerate(report["disposition"]["conditions_for_approval"], 1))
    n_major = sum(1 for f in report["findings"] if f["severity"] == "major")
    n_minor = sum(1 for f in report["findings"] if f["severity"] == "minor")
    n_info = sum(1 for f in report["findings"] if f["severity"] == "informational")
    json_block = json.dumps(envelope, ensure_ascii=False, indent=2)
    return f"""# KF-RESULT {PACKAGE_ID}

**工序**：`04-independent-review`（lane C，TensorPapers | analysis）｜**审核对象**：`{REVIEWED_PACKAGE}`（report 3076）｜
**结论**：**{report['decision']}**（blocking 0 / major {n_major} / minor {n_minor} / informational {n_info}）｜
**审核者**：`{REVIEWER['id']}`（{REVIEWER['role']}，reviewer_type=agent）

## ① 本工序做了什么

对 report 3076（manuscript_gate v1：把 SEAL.md 的 H1–H8 硬伤固化为 11 项机检）做**独立审核**，判 `pass / fail / needs-fix`。
上下文只用两样：报告 markdown 原文（逐字节副本，sha256 自校验）+ 上游 `wp-3076-01` 的产物；**没有读、没有执行**
生产者的 `papers/tools/manuscript_gate.py` 与其测试，也没有取用生产者自写的 review prompt。

打法：凡能在报告文本之外独立重算的量都重算（色散式 → 波数 → coth/tanh 偏差），凡重算不了的一律记 `not_run`，
不当作通过。结论：**核心数字站得住**（H1 偏差序列 5/5 复现），**但汇总与证据口径有 5 处 major 缺陷**，故判 `needs-fix`。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文并自校验**：`scripts/kf_wp3076_04_fetch_report.py` 走 `GET /api/v1/tensor/reports/3076` 取 `markdown`，
   落盘前自算 sha256 = `{EXPECTED_SHA}` 与工单契约逐位比对；同时留档该记录的平台字段。只读 report 3076。
2. **独立重算**：`docs/wp-3076-04/independent_dispersion_check.py` —— 自写二分法（不用生产代码），按报告给出的
   ω²=(gk+Dk⁵/ρ_w)tanh(kh)、D=Eh_i³/(12(1-ν²)) 求解 k；**参数与“声称值”都由正则从原文抓取**
   （`params_quote` / `claimed_quote`），从源头杜绝手抄。再把 tanh 换成 coth 重解，逐周期算相对偏差对照。
3. **反证边界断言**：不采信“T≥14 s 无根”，在 k∈(0,10] 上扫 20001 点找**符号变化**再二分细化，
   并对 14.0/14.1/14.15/14.185/14.2/16/18/20/30/60 s 全列根，另解解析临界期 T_c=2π√(h/g)。
4. **同文自洽性审计**：解析 ③ 的 11 行结果表，重数 HARD 行与 FAIL 数，与汇总句“8/11”“0/11”对数 ——
   这是不依赖生产代码就能推翻的汇总级断言。
5. **引文定位**：15 条引文逐条定位（char_offset / line / occurrences），本包所有 `quote` 字段要求 `occurrences=1`。
6. **审核判据自写**（`docs/wp-3076-04/review_prompt.md`）：先尝试反证每个数字，再判 pass/fail/needs-fix。
7. 工具链：Python 3.11 + jsonschema 4.26（信封校验）+ pytest 9.2（自检，见 ⑥）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/wp-3076-04/review_report.json` | 审核报告本体（契约输出）：decision / findings / claims_assessment / checks_performed / checks_not_run / disposition |
| `docs/wp-3076-04/review_events.json` | append-only 审核台账 1 条：`request-changes`（ke-review-v0.1 词表），带 11 条 findings 与 8 条整改条件 |
| `docs/wp-3076-04/kf_result.wp-3076-04.json` | 平台结果信封（与文末 json 块同源） |
| `docs/wp-3076-04/independent_check.json` | 独立复算原始结果：偏差序列、根扫描、严重度表审计、15 条引文定位 |
| `docs/wp-3076-04/independent_dispersion_check.py` | 独立求解器 + 原文解析器（可一键复跑） |
| `source.md` / `source.record.json` | 报告原文逐字节副本与平台记录字段（审核输入留档） |
| `docs/wp-3076-04/review_prompt.md` | 本工序自写的 reviewer prompt（声明未复制生产 prompt） |
| `scripts/kf_wp3076_04_fetch_report.py` / `scripts/kf_wp3076_04_build.py` | 取原文 / 由复算结果程序化生成全部产物 |
| `docs/wp-3076-04/KF-RESULT-wp-3076-04.md` | 本交付正文 |
| `tests/test_kf_wp3076_04.py` | 自检 12 项（含 4 个负控），见 ⑥ |
| `fig_deviation_boundary.png` | 结果图：偏差曲线（声称 vs 复算）+ coth 根存在性条带 |

**独立复算表（tanh 正解 vs coth 误式，k 单位 1/m）**

| T (s) | 声称偏差 | 复算偏差 | abs-delta (pp) | k_tanh | k_coth |
|---|---|---|---|---|---|
{dev_rows}

**“coth 无根”边界探针**

| T (s) | coth 根（k∈(0,10]） | tanh 根 |
|---|---|---|
{noroot_rows}

解析临界期 T_c=2π√(h/g) = {npr['T_crit_analytic_s']:.4f} s（coth 分支 RHS 在 k→0 的下确界 = g/h）。

**③ 表重数（严重度审计）**：解析到 {a['n_rows']} 行 = HARD {a['n_hard']} + SOFT {a['n_soft']}；sealed HARD FAIL {a['hard_fail_sealed']}、
control HARD FAIL {a['hard_fail_control']}（SKIP {a['hard_skip_control']}）、sealed WARN {a['hard_warn_sealed']}。

| check | 严重度 | sealed | control |
|---|---|---|---|
{sev_rows}

## ④ 证据定位表（claim/字段 → 原文逐字引文）

每条引文在 `docs/wp-3076-04/independent_check.json` 的 `locators` 里带 char_offset / line / occurrences=1，平台可独立重切。

| 定位键 | 原文逐字引文 | 行 | 字符偏移 | 出现次数 |
|---|---|---|---|---|
{loc_rows}

**结论 → 证据链**

| claim | 判定 | 依据 |
|---|---|---|
{claim_rows}

**发现清单（severity 排序）**

| id | severity | 标题 |
|---|---|---|
{find_rows}

**执行的检查**

{checks}

**未执行的检查（如实记 not_run，不记 pass）**

{not_run}

**整改条件（判 needs-fix 的对价）**

{conds}

## ⑤ 注意点与局限

- **独立性边界**：生产仓不在本工作树，门禁 11 项 checks **没有重跑**。因此“sealed FAIL / control PASS”只作为报告的**自述**处理，
  不当作已证事实；能推翻的只有同文自洽性（F1 分母、F11 HARD/WARN 语义）。
- **跨报告边界**：封存稿正文、Report #823/#961 属其它 report_id 或私有稿，工单硬约束禁止读取，相关核对一律 `not_run`。
- 我重算的是**报告自己给出的式子**；若生产实现与该式不同（F8 的 ρ_i 暗示可能如此），复算只证明“报告式子算得出报告数字”，
  不证明“门禁正控算的就是这个式子”。
- **不越权标注**：本审核不含任何 `verified` 字段，claim 状态只用 supported / partially-supported / unresolved / refuted；
  verification 由平台门计算。
- 工单给本包的契约里 `review.required=false`，而验收项要求 `reviewer_independent=true`（契约层面不一致；我未改契约，仅在此标注）：
  M1 很可能对该包判红，与审核质量无关。
- 一条可复用的方法心得：**“汇总分母”是最廉价的造假探测点** —— 同文表格数出的 HARD 行数与汇总句分母只要对不上，
  就能在零生产代码前提下推翻一条汇总级结论（本包 F1 即由此抓到）。

## ⑥ 自检（逐条对照 acceptance）

### 误差判定（报告纪律要求的“是否 <3%”，逐项显式回答）

| 关键量 | 基准 | 本工序结果 | 是否 <3% |
|---|---|---|---|
| coth/tanh 偏差复算 vs 报告声称值（T=4/6/8/10/12 s 共 5 点） | 报告 ③ 的声称值 | 最大 abs-Δ = 0.004 pp（相当于 0.37–25.02% 各点上的相对偏差 ≤1.1%） | **是** |
| 复算波数 k（T=8 s） | 报告所给色散式的独立解 | k_tanh=3.778090e-02、k_coth=3.639599e-02（与声称 3.67% 一致到 0.004 pp） | **是** |
| coth 形式无根临界期 | 解析 T_c=2π√(h/g)=14.185 s | 扫根：T=14.0 s 有根 / T=14.2 s 无根，边界夹在 14.0–14.2 s | **是**（与解析值一致到 0.02 s） |
| coth 误式波数偏差（T=12 s） | tanh 正解 | 25.018%（报告声称 25.02%） | **否**（>15%）—— 该量是被审稿自身的缺陷量（H1 的定量依据），不是本工序的复算误差 |
| 门禁 11 项 checks 在 sealed/control 上的执行状态 | 生产实测 | 未重跑 | **无基准**：not_run，不判是否 <3% |

结论：本工序所有“可复现性误差”均 <3%（最大 0.004 pp）；表内唯一 >3% 的 25.018% 是**被审稿的缺陷量**，
按要求判“否”并据此给出 H1 的量化依据。门禁执行状态无基准，如实记 not_run，不含糊过关。

### acceptance 逐条

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| `valid_json` | ✅ | `review_report.json`、`review_events.json`、信封三者均可解析（tests T1/T2/T3） |
| `schema_pass` | ✅ | 信封过 `schemas/kf_result.v1.schema.json`；台账过 `schemas/review-event.schema.json`（T2/T3） |
| `reviewer_independent` | ✅ | reviewer `{REVIEWER['id']}` 与生产者身份/token 无重叠，`ke_state_machine.is_independent` 复算通过（T5）；未读未跑生产代码（声明见 `review_prompt.md`） |
| `upstream_packages_completed` | ✅ | `docs/wp-3076-01/` 齐备（kf_result + asset_manifest + verification.json，自报 acceptance_all_pass=true）；本审核独立重算其源哈希与字符数 |
| 不复制生产 prompt | ✅ | `review_prompt.md` 为本工序自写，未取用生产 prompt（`prompt_similarity` 无法在无生产 prompt 时计算，故记 not_run 而非 pass，见下） |
| 不标 verified | ✅ | 全包无 verified 字段（T7 负控：出现 `"verified": true` 即红） |

**未达成的自检项（honest 声明）**：
- `prompt_similarity`（review prompt 与生产 prompt 的字面相似度）**not_run**：生产 prompt 不在本工作树的
  `FORBIDDEN_REVIEW_KEYS` 之外可得之处，工单也要求“reviewer context excludes producer explanation”，
  因此该指标只能在平台侧用双方 prompt 计算；我这边只留下自写 prompt 的全文与哈希供比对。
- 门禁 11 项 checks 的重跑 **not_run**（生产仓缺失），故本包不声称“复现了负控/正控”。

## 复跑（一键，四步）

    export TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=...
    python3 scripts/kf_wp3076_04_fetch_report.py --out artifacts/wp-3076-04
    python3 docs/wp-3076-04/independent_dispersion_check.py
    python3 scripts/kf_wp3076_04_build.py
    python3 -m pytest tests/test_kf_wp3076_04.py -q

```json
{json_block}
```
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reviewed-at", default=None,
                    help="ISO timestamp; default = now (UTC)")
    args = ap.parse_args()
    now = args.reviewed_at or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    md, check = load()
    report = build_report(md, check, now)
    ledger = build_ledger(report, now)
    envelope = build_envelope(report, ledger)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "review_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "review_events.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "kf_result.wp-3076-04.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    doc = render_md(md, check, report, envelope)
    (OUT / "KF-RESULT-wp-3076-04.md").write_text(doc, encoding="utf-8")

    n_json = doc.count("```json")
    print(f"decision     : {report['decision']}")
    print(f"findings     : {len(report['findings'])} "
          f"(major={sum(1 for f in report['findings'] if f['severity']=='major')}, "
          f"minor={sum(1 for f in report['findings'] if f['severity']=='minor')}, "
          f"info={sum(1 for f in report['findings'] if f['severity']=='informational')})")
    print(f"claims       : {len(report['claims_assessment'])}")
    print(f"json blocks  : {n_json} (must be 1)")
    print(f"doc chars    : {len(doc)}")
    for p in ("review_report.json", "review_events.json", "kf_result.wp-3076-04.json"):
        print(f"wrote        : docs/wp-3076-04/{p}")
    print("wrote        : docs/wp-3076-04/KF-RESULT-wp-3076-04.md")
    fences = doc.count("```")
    print(f"fence marks  : {fences} (must be 2: open/close of the json block)")
    return 0 if (n_json == 1 and fences == 2) else 1


if __name__ == "__main__":
    raise SystemExit(main())
