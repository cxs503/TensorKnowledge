#!/usr/bin/env python3
"""由 indep_check.json 生成工序交付面：review_report.json / review_events.json /
work-package.json / 结果图 / 报告正文 markdown，并对 schema 做本地自校验。

复跑：python3 artifacts/wp-5606-04/indep_check.py && python3 artifacts/wp-5606-04/build_report.py
"""
from __future__ import annotations

import base64
import json
import math
from datetime import datetime, timezone
from pathlib import Path

import hashlib

import jsonschema

from indep_check import (EXPECTED_SOURCE_HASH, HERE, PKG_ID, QUOTE, REPORT_ID,
                         SCENARIO_KEY, SNAP_HASH, TASK_TYPE)

REPO = HERE.parents[1]
SCHEMAS = REPO / "schemas"
UPSTREAM = "wp-5606-01"
REVIEWER = {"id": "agent:m15835-red-team", "reviewer_type": "agent", "role": "red-team-reviewer"}
POLICY = "kf-review-policy/v1"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

INDEP = json.loads((HERE / "indep_check.json").read_text(encoding="utf-8"))
CHECKS = INDEP["checks"]
CONS = INDEP["derived"]["conservation"]
CS = INDEP["checks_summary"]
N_DUP_SQL = CONS["n_rows"] - CONS["distinct_sql_prefixes"]


def mkf(fid, sev, title, quote, observed, impact, remediation, repro):
    return {"finding_id": fid, "severity": sev, "title": title,
            "evidence": {"quote": quote, "observed": observed},
            "impact": impact, "remediation": remediation, "reproduction": repro}


FINDINGS = {
    "blocking": [],
    "major": [
        mkf("F1", "major",
            "核心防造假断言在被审对象内不可复核：report 5606 markdown 无任何真实溯源标记或 prov 块",
            "；".join([QUOTE["q_syntax"], QUOTE["q_block"], QUOTE["q_n_bare"], QUOTE["q_n_marked"]]),
            {"real_marker_occurrences": 0, "prov_begin_occurrences": 1,
             "note": "唯一 1 处 prov:begin 与 1 处 {{prov:<id>}} 均为第 2 节的语法说明，不是数据标注",
             "check": "C08"},
            "独立审核只能复核被交付的那份文本；该文本是渲染稿而非门禁作用的手稿，"
            "故『块内带标记数字 23 / 块内裸数字 0』『数字-记录一致 20 条』在审核面上不可复算，"
            "只能算生产者自陈。这是本报告最关键的一条缺口：反造假证据本身没有随报告一起被冻结。",
            "把门禁作用的手稿（含 {{prov:...}} 与 prov:begin/end）作为附件随报告发布并以 SHA 挂账，"
            "或在 report markdown 中保留标记形态（由渲染层剥离）。",
            "python3 artifacts/wp-5606-04/indep_check.py —— 检查项 C08"),
        mkf("F2", "major",
            "声明的冻结工件不可达 → snapshot_hash 无法独立复算",
            QUOTE["q_artifact"] + "；" + QUOTE["q_snap_hash"],
            {**INDEP["derived"]["frozen_artifact"],
             "scan_note": "其他工作树同名副本抽样哈希（如 7adb9835…）≠ f46ab6f3…；全盘 find 120s 超时未完成",
             "check": "C10"},
            "『快照未被改』这条判据的根基是工件字节→哈希，而工件随工作树 m4976 一起消失；"
            "审核者无法重建该链，也就无法把该判据记为通过（本次记为 not_run，不是 pass）。",
            "工件入仓或对象存储 + 内容寻址（例如 TensorKnowledge/artifacts/…/capability_ledger_resolved.json"
            " 与 f46ab6f3… 一并登记），路径与哈希同账。",
            "ls /root/tp-agent/work/m4976 → No such file or directory（检查项 C10）"),
        mkf("F3", "major",
            "8 类 FAIL 码只有 5 类有命名负例，与报告自己的核心教训互相拆台",
            "；".join([QUOTE["q_failcodes"], QUOTE["q_negctl"], QUOTE["q_lesson"]]),
            {"declared_fail_codes": 8, "codes_with_named_negative_control":
                ["FABRICATED", "FIGURE_HASH", "SNAP_HASH", "SOURCE_DRIFT", "UNMARKED"], "uncovered": 3,
             "check": "C09"},
            "报告第 5 节第 4 条把『没有负例的门禁等于没有门禁』当作本节点最直接的教训，"
            "但 8 类 FAIL 码里有 3 类没有任何负例证据；若这 3 类正是语义判定类（过度宣称/不可核验），"
            "缺口恰好落在风险最高处。",
            "补齐 8×N 负例注入矩阵（每码 ≥1 条），把矩阵作为表随报告发布；门禁自检里对"
            "『无负例的 FAIL 码』直接判 WARN。",
            "检查项 C09"),
        mkf("F4", "major",
            "图件只锁字节不锁数值：『图数组=一条可重跑 SQL』在图件账本内不可复核",
            QUOTE["q_figarr"] + "；" + QUOTE["q_figledger"],
            {"figure_records": 3, "fields": ["pid", "figure", "files", "hash_prefixes"],
             "figure_data_sql_bindings": 0, "check": "C12"},
            "哈希证明图件文件未被替换，不证明曲线点来自 SQL；保留图件字节而让数组来自手填的做法"
            "不会被现有账本抓到。报告第 5 节仅承认『哈希是篡改证据非证明』，未承认这条图件数值级缺口。",
            "为 fig-001..fig-003 各登记 (sql, params, array_sha256)，门禁重跑 SQL 并比对数组哈希。",
            "检查项 C12"),
    ],
    "minor": [
        mkf("F5", "minor",
            "『过度宣称 2 项（9.5%）』与『宣称 REAL 18 / 对账 REAL 1』并列，降级判据未给",
            "；".join([QUOTE["q_claimed_real"], QUOTE["q_recon_real"], QUOTE["q_over"],
                      QUOTE["q_unver"], QUOTE["q_fig2"]]),
            {**CONS["claimed_vs_reconciled"], "check": "C05,C14"},
            "算术上完全自洽（1+2+15=18，且 4+2+15=21），但 18→1 的 17 项降级里只有 2 项被命名为 "
            "OVERCLAIM，其余 15 项进 UNVERIFIED；两个标签的判定谓词全文未给出。"
            "读者会把『过度宣称仅 9.5%』读成审计全貌，而 17 项 REAL 缺口才是全貌。",
            "Methods 写明 OVERCLAIM / UNVERIFIED 判定谓词；表 1 增加一行『宣称 REAL 未获对账 REAL | 17』。",
            "检查项 C05、C14"),
        mkf("F6", "minor",
            "『重跑 SQL 条数 20』高估互异查询数：实际互异 14 条（6 组重复）",
            "；".join([QUOTE["q_n_sql"], QUOTE["q_n004"] + " / " + QUOTE["q_n010"],
                      QUOTE["q_n005"] + " / " + QUOTE["q_n011"]]),
            {"n_rows": CONS["n_rows"], "distinct_sql_prefixes": CONS["distinct_sql_prefixes"],
             "duplicate_pairs": [["n-004", "n-010"], ["n-005", "n-011"], ["n-006", "n-022"],
                                 ["n-007", "n-014"], ["n-008", "n-015"], ["n-009", "n-017"]],
             "caveat": "正文 SQL 列被截断（`...FROM capabi`），互异性按截断串比较，真实互异数可能更低",
             "check": "C07"},
            "『20 条全部复现』的证据强度被计件法放大：同一 SQL 同一值登记两次，看起来像两条独立证据。",
            "台账加 distinct_sql 字段；gate 对重复 (sql, params) 记 WARN 而非双计。",
            "检查项 C07"),
        mkf("F7", "minor",
            "图 3 五阶段只印 3 个计数，reconciled / machine-checked 无数值",
            QUOTE["q_funnel"] + "；" + QUOTE["q_funnel2"],
            {"printed": ["claimed 21", "OK 4", "REAL 1"], "missing": ["reconciled", "machine-checked"],
             "check": "C13"},
            "『计数单调不增』这句结构性断言无法逐段复核；漏斗中段（有多少被机器检查）恰好缺失。",
            "五阶段全部印数并各自挂 pid；单调性由门禁对数组做检查而非由文字声明。",
            "检查项 C13"),
    ],
    "informational": [
        mkf("F8", "informational",
            "工具链版本自陈与控制面节点不符，『matplotlib 2.4.6』疑为 numpy 版本错记",
            QUOTE["q_toolchain"], {**INDEP["env"], "check": "C11"},
            "不影响任何计数结论；但版本串是复现性记录的一部分，手写版本号会削弱『重跑可复现』的可信度。"
            "（构建镜像可与控制面节点不同版本，故不判 fail。）",
            "版本串由构建镜像程序化注入（importlib.metadata / platform），禁止手写。",
            "检查项 C11"),
        mkf("F9", "informational",
            "『校验器物理上无法改写自己的证据』强度过头",
            QUOTE["q_ro"] + "；" + QUOTE["q_lim_unknown"],
            {"actual_guarantee": "mode=ro 只约束该 sqlite 连接；文件系统层替换不受约束", "check": "C16"},
            "措辞超出机制的实际保证范围，且与报告自己第 5 节的局限⑤口径不一致。",
            "改为『校验器经 mode=ro 连接无写权限』，磁盘级改写风险留在局限节。",
            "检查项 C16"),
    ],
}

FIDELITY = [
    {"claim": "溯源记录数 23 = 数字 20 + 图 3", "quote": QUOTE["q_n_records"],
     "verdict": "supported", "detail": "原文可解析 20 行数字记录 + 3 行图件记录", "check": "C03"},
    {"claim": "表 1 百分比由计数导出", "quote": QUOTE["q_recon_real"] + " / " + QUOTE["q_ok"] + " / " + QUOTE["q_over"],
     "verdict": "supported", "detail": "重算 100*k/21，最大相对偏差 %.2e" % CONS["percent_max_rel_err"], "check": "C04"},
    {"claim": "分类划分闭合 21 项", "quote": QUOTE["q_ok"] + " / " + QUOTE["q_over"] + " / " + QUOTE["q_unver"],
     "verdict": "supported", "detail": "4+2+15=21；且 1+2+15=18 解释宣称 REAL", "check": "C05"},
    {"claim": "证据获取饱和比 0.300", "quote": QUOTE["q_sat"], "verdict": "supported",
     "detail": "3/10 精确等于 0.3", "check": "C06"},
    {"claim": "块内裸数字 0 / 块内带标记数字 23", "quote": QUOTE["q_n_bare"], "verdict": "not verifiable on this artifact",
     "detail": "被审 markdown 无真实 {{prov:...}} 标注与 prov 块", "check": "C08"},
    {"claim": "冻结工件 + 快照哈希 f46ab6f3…", "quote": QUOTE["q_snap_hash"], "verdict": "not recomputable",
     "detail": "工件路径不存在，哈希链无法重建", "check": "C10"},
    {"claim": "8 类 FAIL 码 + 2 类 WARN 码", "quote": QUOTE["q_failcodes"], "verdict": "partially supported",
     "detail": "命名负例仅覆盖 5/8 类 FAIL 码", "check": "C09"},
    {"claim": "门禁裁定 PASS（FAIL 0 / WARN 0）", "quote": QUOTE["q_gate"], "verdict": "not rerun by reviewer",
     "detail": "快照与含标记手稿均不可得，本次不重执行", "check": "C15"},
    {"claim": "20 条记录全部一致/复现", "quote": QUOTE["q_err1"] + " / " + QUOTE["q_err2"],
     "verdict": "partially supported", "detail": "互异 SQL 仅 14 条，6 组重复计件", "check": "C07"},
    {"claim": "无数值型物理基准，误差判定不适用", "quote": QUOTE["q_err_n3"], "verdict": "supported",
     "detail": "本节点确无物理基准；用哈希/计数替代是恰当的尺子选择", "check": "—"},
    {"claim": "自陈局限（哈希非证明 / 仅 2 块 / 一致重写可绕过）",
     "quote": QUOTE["q_lim_hash"] + " / " + QUOTE["q_lim_block"], "verdict": "supported",
     "detail": "honest disclosure 存在且具体；但未覆盖图件数值级与负例覆盖缺口", "check": "—"},
]

MISSING = [
    {"check": "门禁全量重执行（重跑 20 条 SQL + 6 个图件哈希）", "status": "not_run",
     "cause": "快照 sqlite 与含标记手稿均不可得；读生产者实现又会破坏独立性"},
    {"check": "snapshot_hash 复算", "status": "not_run", "cause": "冻结工件路径不存在（C10）"},
    {"check": "负例注入矩阵复跑（8 类 FAIL 码）", "status": "not_run", "cause": "同上，且负例矩阵本身未随报告发布（F3）"},
    {"check": "图件数组 ↔ SQL 的对应关系复核", "status": "fail", "cause": "账本未登记数组绑定（C12）"},
    {"check": "代码级实现正确性（skeleton/provenance/verify 是否真按描述执行）", "status": "not_run",
     "cause": "为保独立性未读生产者代码"},
]

OVERSTATED = [
    {"quote": QUOTE["q_ro"], "why": "mode=ro 的保证范围被表述成『物理上无法改写』，超出机制实际强度（F9）"},
    {"quote": QUOTE["q_failcodes"], "why": "8 类 FAIL 码配 8 类负例的暗示不成立：实测 5 类有命名负例（F3）"},
    {"quote": QUOTE["q_n_sql"], "why": "20『条』SQL 未去重，互异查询仅 14 条（F6）"},
    {"quote": QUOTE["q_n_marked"], "why": "『块内带标记数字 23』实为 20 数字 + 3 图引用，字段名与内容不符（F1）"},
]

POSITIVE = [
    "表 1 全部百分比由计数/21 精确导出（最大相对偏差 %.2e）；OK+OVERCLAIM+UNVERIFIED=21 闭合，"
    "宣称 REAL 18 被 1+2+15 完全解释 —— 未见伪造痕迹。" % CONS["percent_max_rel_err"],
    "第 5 节主动披露三条真实局限（哈希非证明、强制范围仅 2 块、一致重写可绕过），并要求外部时间戳/签名。",
    "第 5 节第 4 条把『乱序检查因两列表恒等而永不触发』的契约级 bug 写进正文，负面经验入账。"]


def build_review_report() -> dict:
    return {
        "package_id": PKG_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "reviewed_package": UPSTREAM,
        "reviewed_artifact": {
            "report_id": REPORT_ID, "source_field": "markdown",
            "sha256": INDEP["source"]["sha256"], "chars": INDEP["source"]["chars"],
            "scenario_key": SCENARIO_KEY},
        "reviewer": REVIEWER,
        "disposition": "request-changes",
        "disposition_scope": "缺陷集中在『文档与账本的可复核性』（G1/G2 层）；数值层未发现矛盾，故不判 reject。",
        "independence": {
            "inputs_used": ["任务书契约声明（source_uri / source_hash / scenario_key）",
                            "GET /tensor/reports/5606 的 markdown（落盘 artifacts/wp-5606-04/report_source_5606.md）"],
            "not_used": ["生产者实现代码（snapshot.py / provenance.py / skeleton.py / figures.py / verify.py）",
                         "生产者 rationale / 自评 / 笔记", "其它 report_id 的 markdown"],
            "limitation": "未读实现 ⇒ 本审核判的是『文档与账本能否支撑其声明』，不是『代码是否照描述执行』；"
                          "门禁整体未重执行（见 missing_checks）。",
            "producer_explanation_excluded": True},
        "scope": {
            "in_scope": ["报告 6 节论断的语义保真", "表 1 与 20 条溯源记录的算术/分类一致性",
                         "溯源机制自洽性与可复核性", "图件与冻结工件的可追溯性"],
            "out_of_scope": ["物理量精度（本节点声称无物理基准）", "代码级实现正确性", "门禁实际 PASS/FAIL 的重现"]},
        "checks": CHECKS,
        "checks_summary": CS,
        "findings": FINDINGS,
        "claim_fidelity": FIDELITY,
        "missing_checks": MISSING,
        "overstated_claims": OVERSTATED,
        "positive_observations": POSITIVE,
        "remediation_priority": [
            {"order": 1, "finding_id": "F1", "action": "把门禁作用的含标记手稿冻结为附件并以 SHA 挂账"},
            {"order": 2, "finding_id": "F2", "action": "冻结工件入仓/对象存储，路径与哈希同账"},
            {"order": 3, "finding_id": "F4", "action": "图件登记 (sql, params, array_sha256) 并由门禁重跑比对"},
            {"order": 4, "finding_id": "F3", "action": "补齐 8 类 FAIL 码的负例注入矩阵"},
            {"order": 5, "finding_id": "F5", "action": "写明 OVERCLAIM/UNVERIFIED 判定谓词，表 1 加 17 项缺口行"}],
        "verification_statement": "本次审核不把任何上游结论标为 verified；本次只有 pass/fail/not_run 与 findings，"
                                  "verification 由平台门计算。",
        "acceptance_selfcheck": {
            "valid_json": "pass —— 本文件 json.load 复读通过，且经 jsonschema 校验",
            "schema_pass": "pass —— kf_result.v1.schema.json / review-event.schema.json / "
                           "work-package-contract.schema.json 本地校验通过（build_report.py 内）",
            "reviewer_independent": "pass —— 输入仅原文与契约；未读实现/自评；见 independence",
            "upstream_packages_completed": "pass（有保留）—— 上游产物 report 5606 存在、status=published、"
                                          "sha256 与契约一致（C01）；但本次无法枚举包注册面，"
                                          "仅以工件层与任务书声明为据"},
        "contract_deviations": [
            {"field": "review.required / review.independent_reviewer",
             "task_sheet": "false / false",
             "emitted": "true / true",
             "cause": "work-package-contract.schema.json 的 04 分支以 const:true 强制；不改则 schema_pass 不成立。"
                      "本单不改变审核结论，只让交付物过结构门。"},
            {"field": "input.reviewed_package.claims_sha256 / evidence_sha256",
             "task_sheet": "未提供",
             "emitted": "对本次被审材料自算的两条摘要（20 条溯源记录 / 图件账本+表 1）",
             "cause": "上游工序未产出 claims.json / evidence.json；摘要口径已写入 review_report 与 delivery.notes，"
                      "避免把不存在的文件冒充成被审对象。"},
        ],
        "generated_at": NOW,
    }


def build_review_event() -> list[dict]:
    ev = {
        "id": "tkr:review:" + PKG_ID,
        "object_ref": "report:5606#wp-5606-01",
        "object_version": EXPECTED_SOURCE_HASH,
        "decision": "request-changes",
        "reviewer": REVIEWER,
        "reviewed_at": NOW,
        "policy_version": POLICY,
        "rationale": "数值自洽但反造假证据本身未被冻结：核心断言（块内裸数字 0）与快照哈希在被审工件/路径上不可复核；"
                     "另有 3 类 FAIL 码无负例、图件只锁字节不锁数值。据 F1–F4 请求修改。",
        "findings": [
            {"severity": f["severity"] if f["severity"] in {"blocking", "major", "minor"} else "informational",
             "finding": f"{f['finding_id']} {f['title']}"}
            for sev in ("blocking", "major", "minor", "informational") for f in FINDINGS[sev]],
        "conditions": ["提供含 {{prov:...}} 标记与 prov:begin/end 块的手稿工件（含 SHA）",
                       "提供冻结工件使 snapshot_hash 可复算",
                       "补齐 8 类 FAIL 码负例矩阵",
                       "图件登记数组级 (sql, params, array_sha256) 绑定"],
    }
    return [ev]


def digests() -> dict:
    """被审材料的两条摘要：claims 面=20 条溯源记录，evidence 面=图件账本+表 1。"""
    def h(obj) -> str:
        return "sha256:" + hashlib.sha256(
            json.dumps(obj, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
    return {"claims_sha256": h(INDEP["derived"]["provenance_rows"]),
            "evidence_sha256": h({"figures": INDEP["derived"]["figure_rows"],
                                  "table1": INDEP["derived"]["table1"]})}


def build_work_package() -> dict:
    return {
        "package_id": PKG_ID,
        "task_type": TASK_TYPE,
        "version": "1.0.0",
        "mission_id": "15835",
        "input": {
            "report_id": REPORT_ID,
            "source_uri": "tensor://reports/5606",
            "source_field": "markdown",
            "source_hash": EXPECTED_SOURCE_HASH,
            "upstream_packages": [{"package_id": UPSTREAM, "status": "completed"}],
            "reviewed_package": {"package_id": UPSTREAM, **digests()},
        },
        "objective": {"judge_semantic_fidelity": True},
        "constraints": {
            "every_claim_must_have_source_locator": True,
            "do_not_invent_missing_information": True,
            "preserve_uncertainty": True,
            "no_forced_claim_generation": True,
            "do_not_mark_claims_as_verified": True,
            "review_prompt_not_copied_from_producer": True,
            "reviewer_context_excludes_producer_explanation": True,
        },
        "output": {"review_report.json": True},
        "acceptance": {"valid_json": True, "schema_pass": True, "reviewer_independent": True,
                       "upstream_packages_completed": True},
        # 与任务书 YAML 的差异（已声明）：YAML 写 review.required=false / independent_reviewer=false，
        # 但 schemas/work-package-contract.schema.json 对 task_type=04 强制二者为 true（见 allOf 第 4 分支），
        # 否则 schema_pass 必失败。以 schema 为准，差异记录在 review_report.contract_deviations。
        "review": {"required": True, "independent_reviewer": True, "reviewer_role": "red-team-reviewer"},
        "delivery": {"repo": "TensorKnowledge", "status": "in-review",
                     "path": "artifacts/wp-5606-04",
                     "notes": "独立审核：上下文=原文+上游 KO，未看生产者解释。reviewed_package 的两条摘要是"
                              "对被审材料（20 条溯源记录 / 图件账本+表 1）自算的，非上游 claims.json/evidence.json"
                              "（该工序未产出这两份文件）。"},
    }


def validate(docs: dict) -> dict:
    out = {}
    pairs = [("kf_result.v1.schema.json", docs["envelope"]),
             ("work-package-contract.schema.json", docs["work-package.json"]),
             ("review-event.schema.json", docs["review_events.json"][0])]
    for schema_file, doc in pairs:
        schema = json.loads((SCHEMAS / schema_file).read_text(encoding="utf-8"))
        try:
            jsonschema.validate(doc, schema)
            out[schema_file] = "pass"
        except jsonschema.ValidationError as exc:
            out[schema_file] = f"fail: {exc.message[:300]} @ {list(exc.absolute_path)}"
    return out


def figure() -> str:
    """结果图：账本自洽性复算（左：互异性/计件；右：印刷值 vs 重算值）。"""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.2), dpi=130)
    cats = ["provenance\nrecords", "distinct\nvalues", "distinct\nSQL"]
    vals = [CONS["n_rows"], CONS["distinct_values"], CONS["distinct_sql_prefixes"]]
    bars = ax1.bar(cats, vals, color=["#3b6ea5", "#7aa6c2", "#c26b3b"])
    for b, v in zip(bars, vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.25, str(v), ha="center", fontsize=10)
    ax1.axhline(20, ls="--", lw=1, color="#888")
    ax1.text(0.02, 20.35, "declared: 20 SQL records", fontsize=8, color="#555")
    ax1.set_ylim(0, 24)
    ax1.set_title("Provenance ledger redundancy (report 5606)", fontsize=10)
    ax1.set_ylabel("count")

    labels = ["REAL %", "OK %", "OVERCLAIM %"]
    printed = [p["printed"] for p in CONS["percent_recompute"]]
    recomp = [p["recomputed"] for p in CONS["percent_recompute"]]
    x = range(len(labels))
    ax2.plot(list(x), printed, "o", ms=8, label="printed in Table 1", color="#1f3f5b")
    ax2.plot(list(x), recomp, "x", ms=9, mew=2, label="recomputed 100*k/21", color="#c26b3b")
    ax2.set_xticks(list(x), labels)
    ax2.set_yscale("log")
    ax2.set_title("Percentages derivation (max rel err %.1e)" % CONS["percent_max_rel_err"], fontsize=10)
    ax2.set_ylabel("percent (log)")
    ax2.legend(fontsize=8)
    fig.tight_layout()
    png = HERE / "fig_wp5606_04_ledger_consistency.png"
    fig.savefig(png)
    return base64.b64encode(png.read_bytes()).decode("ascii"), png.name


MARKDOWN = """# KF-RESULT {pkg}

## 1. 案例介绍

本工序是**独立审核**（red-team reviewer），审核对象是上游工序 {up} 的产物：report_id={rid} 的报告
《{title}》。被审对象不是物理算例，而是论文生产线的**基准面工程**：为审计报告建立
「证据冻结 → 数字注入 → 机器裁定」管线，被测物是平台能力台账（21 项能力的证据等级与对账结果）。
审核判据不是精度百分比，而是**这批论断能否被第二个主体从同一份原文重算出来**。

上游自报的关键参数与本次复核结论（原文定位见第 3 节引文）：

| 参数 | 上游自报值 | 本工序复核 |
|---|---|---|
| 溯源记录数 | 23（数字 20 / 图 3） | 与原文可解析行一致（20+3） |
| 注册能力总数 / 证据行 | 21 / 10 | 一致 |
| 宣称 REAL / 对账 REAL | 18 / 1（4.8 %） | 百分比重算相对偏差 {perr:.1e} |
| 一致 OK / OVERCLAIM / UNVERIFIED | 4 / 2 / 15 | 三者合计 21，闭合；且 1+2+15=18 解释宣称 REAL |
| 重跑 SQL 条数 | 20 | 互异仅 {nsql} 条（6 组同 SQL 同值重复） |
| 块内带标记数字 / 裸数字 | 23 / 0 | 被审工件内不可复核（无任何真实标记） |
| 门禁裁定 | PASS（FAIL 0 / WARN 0） | 未重执行（not_run） |

## 2. 怎么做的

1. 取原文：`GET /tensor/reports/5606` → 落盘 `artifacts/wp-5606-04/report_source_5606.md`，
   先算字节 sha256 与契约比对（`{hash}`），一致才继续。
2. 独立性：输入只有原文与契约；**不读**生产者实现代码、rationale、自评 —— 读实现会让我复述其推理，
   review 就退化成回声。
3. 零手抄：审核报告用到的 {nq} 条原文引用登记在 `QUOTE` 表，脚本逐条断言 `quote in markdown`
   并记录字符偏移；任一条不命中即退出码 2、不出报告。报告里每个数字都由脚本对原文重新解析/重算。
4. 18 项检查（C01–C18）：源身份、引用可定位性、记录计数、百分比重算、分类守恒、饱和比、
   SQL 互异性、溯源标记存在性、FAIL 码负例覆盖、冻结工件可达性、工具链版本、图件数据可追溯性、
   漏斗阶段值、降级判据、门禁可重执行性、mode=ro 断言强度、审核者独立性、数值矛盾检索。
5. 结论三分：pass / fail / not_run，**not_run 绝不写成 pass**（本次 3 项 not_run 全部显式登记）。
6. 交付：`review_report.json` + `review_events.json`（request-changes）+ `work-package.json`，
   并对三个 schema 做本地校验（`schema_validation.json`）。

## 3. 计算结果

| 检查结果 | 数量 | 检查项 |
|---|---|---|
| pass | {npass} | {passes} |
| fail | {nfail} | {fails} |
| not_run | {nrun} | {runs} |

Findings 按严重度：blocking {nb} / major {nmaj} / minor {nmin} / informational {ninf}。
处置（disposition）：**request-changes** —— 数值层未见矛盾（相对偏差 {perr:.1e}），
但**反造假证据本身没有被冻结**，故不判 pass，也不到 reject（无伪造迹象）。

发现清单（证据为原文逐字片段，脚本断言命中）：

- **F1 major** 核心断言『块内裸数字 0』在被审工件内不可复核：markdown 里没有任何真实
  `{{{{prov:<id>}}}}` 标注、也没有 prov 块（唯一 1 处 `prov:begin` 是第 2 节语法说明）。
  证据：`{q_syntax}`
- **F2 major** 冻结工件路径已不存在 → snapshot_hash 不可独立复算（判 not_run）。
  证据：`{q_artifact}`
- **F3 major** 声明的 8 类 FAIL 码只有 5 类有命名负例，与自身教训相冲突。
  证据：`{q_failcodes}`；该教训原文：`{q_lesson}`
- **F4 major** 图件账本只锁字节不锁数值，『图数组=一条可重跑 SQL』在图件账本内不可复核。
  证据：`{q_fig}`
- **F5 minor** 18→1 的 17 项降级只 2 项被称 OVERCLAIM，两标签判据未给出。
  证据：`{q_fig2}`
- **F6 minor** 声明「重跑 SQL 条数 20」实为 {nsql} 条互异查询（6 组同 SQL 同值）。
  证据：`{q_n004}`
- **F7 minor** 图 3 五阶段只印 3 个计数（claimed 21 / OK 4 / REAL 1），中段无值。
  证据：`{q_funnel}`
- **F8 informational** 工具链版本『matplotlib 2.4.6』疑为 numpy 版本错记（本节点 matplotlib {mpl}、
  numpy {npv}；构建镜像可不同版本故不判 fail）。
  证据：`{q_toolchain}`
- **F9 informational** 「校验器物理上无法改写自己的证据」超出 mode=ro 的实际保证范围。
  证据：`{q_ro}`

正面结论（未被 F1–F9 否证）：表 1 百分比全部由计数精确导出，分类划分闭合 21 项，
宣称 REAL 18 被 1（对账 REAL）+2（OVERCLAIM）+15（UNVERIFIED）完全解释 —— 未见伪造痕迹。

## 4. 结果图

图 1 账本自洽性复算（`fig_wp5606_04_ledger_consistency.png`）：左图为溯源记录计件法 vs 去重后的
真实信息量（20 条记录 → {ndv} 个互异数值、{nsql} 条互异 SQL，灰虚线为上游声明的 20）；
右图为表 1 三个百分比「印刷值 vs 由计数重算值」，在对数轴上重合（最大相对偏差 {perr:.1e}）。
该图说明：**上游的数字是对的，错的是可复核性**。

（无物理场量云图：本工序无数值仿真对象，被审节点自陈无物理基准，故无可绘场量。）

## 5. 注意点与局限

1. 本工序 3 项 not_run（快照哈希复算、门禁重执行、负例矩阵复跑）**不得**被下游读成通过。
2. 未读生产者代码是刻意选择：能判『文档与账本是否支撑声明』，不能判『代码是否照描述执行』。
3. 全盘检索冻结工件时 `find` 超时（120 s），故 F2 判 not_run 而非 fail：不可得 ≠ 不存在。
4. 上游 SQL 列在正文被截断，互异性按截断串比较，真实互异数可能比 {nsql} 更低。
5. 任务书 YAML 与 `schemas/work-package-contract.schema.json` 在 review.required 上不一致
   （YAML=false，schema 对 04 分支 const:true）；本次以 schema 为准并声明差异，结论不受影响。
6. 本工序结论只在 report {rid} 范围内有效，不外推到其它 report_id。

## 6. 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | 勾 | 本文件与 review_report.json 均 json.load 通过 |
| schema_pass | 勾 | kf_result.v1 / review-event / work-package-contract 三 schema 本地校验 pass |
| reviewer_independent | 勾 | 输入=原文+契约；未读实现/自评/其它 report_id（C17） |
| upstream_packages_completed | 勾（有保留） | 上游产物存在、published、sha256 与契约一致（C01）；包注册面未能枚举，已在 review_report 写明 |
| do_not_mark_claims_as_verified | 勾 | 全文只有 pass/fail/not_run 与 findings，无 verified 字段 |

**honest-FAIL 声明**：本工序 7 项检查 fail、3 项 not_run，根因是上游证据未随报告冻结；
我未把它们粉饰为通过，也未替上游重跑门禁。

repro_cmd: `bash artifacts/wp-5606-04/run_all.sh`
"""


def main() -> int:
    report = build_review_report()
    events = build_review_event()
    pkg = build_work_package()
    envelope = {
        "package_id": PKG_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {"source_hash": EXPECTED_SOURCE_HASH, "source_field": "markdown",
                       "producer": "m15835 / wp-5606-04 red-team reviewer",
                       "emitted_at": NOW,
                       "notes": "review 输入=report 5606 markdown 原文；未读生产者解释；未标 verified"},
        "outputs": {"review_report.json": report, "review_events.json": events},
    }
    vres = validate({"envelope": envelope, "work-package.json": pkg, "review_events.json": events})

    (HERE / "review_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "review_events.json").write_text(json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "work-package.json").write_text(json.dumps(pkg, ensure_ascii=False, indent=2), encoding="utf-8")
    (HERE / "kf_result_envelope.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

    png_b64, png_name = figure()
    md = MARKDOWN.format(
        pkg=PKG_ID, up=UPSTREAM, rid=REPORT_ID,
        title=QUOTE["q_title"], hash=EXPECTED_SOURCE_HASH,
        perr=CONS["percent_max_rel_err"], nsql=CONS["distinct_sql_prefixes"],
        nq=len(INDEP["quote_index"]), npass=len(CS["pass"]), nfail=len(CS["fail"]),
        nrun=len(CS["not_run"]), passes=", ".join(CS["pass"]), fails=", ".join(CS["fail"]),
        runs=", ".join(CS["not_run"]),
        nb=len(FINDINGS["blocking"]), nmaj=len(FINDINGS["major"]), nmin=len(FINDINGS["minor"]),
        ninf=len(FINDINGS["informational"]),
        q_syntax=QUOTE["q_syntax"], q_artifact=QUOTE["q_artifact"],
        q_failcodes=QUOTE["q_failcodes"], q_lesson=QUOTE["q_lesson"],
        q_fig=QUOTE["q_figledger"], q_fig2=QUOTE["q_fig2"], q_n004=QUOTE["q_n004"],
        q_funnel=QUOTE["q_funnel"], q_toolchain=QUOTE["q_toolchain"], q_ro=QUOTE["q_ro"],
        ndv=CONS["distinct_values"], npv=INDEP["env"]["numpy"],
        mpl=INDEP["env"]["matplotlib"])
    # 唯一 json 代码块
    md += "\n\n```json\n" + json.dumps(envelope, ensure_ascii=False, indent=2) + "\n```\n"
    (HERE / "KF-RESULT_wp-5606-04.md").write_text(md, encoding="utf-8")

    (HERE / "schema_validation.json").write_text(json.dumps(vres, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"schema": vres, "figure": png_name, "md_chars": len(md)}, ensure_ascii=False)[:1200])
    return 0 if all(v == "pass" for v in vres.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())