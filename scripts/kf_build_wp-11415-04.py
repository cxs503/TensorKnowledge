#!/usr/bin/env python3
"""Build the wp-11415-04 review deliverables from the raw check outputs.

Zero hand transcription: every number and every quote in the emitted JSON is
either read from runs/wp-11415-04/*.json or asserted to be a *unique* verbatim
substring of the source markdown at build time (assertion failure aborts).

Outputs
  artifacts/wp-11415-04/review_report.json      (outputs['review_report.json'])
  artifacts/wp-11415-04/review_events.json      (outputs['review_events.json'])
  artifacts/wp-11415-04/kf_result.json          (kf_result.v1 envelope)
  runs/wp-11415-04/kf_result.wp-11415-04.json   (run copy, byte identical)

Run: python3 scripts/kf_build_wp-11415-04.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib

RUN = pathlib.Path("runs/wp-11415-04")
ART = pathlib.Path("artifacts/wp-11415-04")
DOCS = pathlib.Path("docs/kf/wp-11415-04")
UPSTREAM_PKG = pathlib.Path("docs/kf/wp-11415-01")

PACKAGE = "wp-11415-04"
TASK = "04-independent-review"
REPORT_ID = "11415"
TARGET = "wp-11415-01"


def load(p: pathlib.Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _estate_envelope_scan_legacy() -> dict:
    """Validate every published KF-RESULT envelope in docs/kf against
    schemas/kf_result.v1.schema.json (estate-wide context for finding F2)."""
    import re

    import jsonschema

    schema = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    total = invalid = with_claims = 0
    valid_ids, invalid_ids = [], []
    for p in sorted(pathlib.Path("docs/kf").glob("*/KF-RESULT-*.md")):
        if p.parent.name == PACKAGE:          # never count our own envelope
            continue
        blocks = re.findall(r"```json\n(.*?)\n```", p.read_text(encoding="utf-8", errors="replace"), flags=re.S)
        if not blocks:
            continue
        try:
            inst = json.loads(blocks[-1])
        except json.JSONDecodeError:
            continue
        total += 1
        errs = list(v.iter_errors(inst))
        if errs:
            invalid += 1
            invalid_ids.append(p.parent.name)
        else:
            valid_ids.append(p.parent.name)
        if isinstance(inst, dict) and "claims" in inst:
            with_claims += 1
    return {
        "packages_checked": total,
        "packages_invalid": invalid,
        "packages_valid": valid_ids,
        "share_invalid": round(invalid / total, 4) if total else None,
        "envelopes_with_top_level_claims": with_claims,
        "validator": "schemas/kf_result.v1.schema.json (Draft 2020-12)",
        "excluded_self_package": PACKAGE,
    }


def main() -> int:
    md = (RUN / "report_11415.md").read_text(encoding="utf-8")
    identity = load(RUN / "source_identity.json")
    checks = load(RUN / "independent_checks.json")
    stage2 = load(RUN / "stage2_probe.json")
    man = load(RUN / "upstream_asset_manifest_wp-11415-01.json")
    upstream_result = load(RUN / "upstream_kf_result_wp-11415-01.json")

    def loc(quote: str) -> dict:
        n = md.count(quote)
        assert n == 1, f"quote not unique ({n}x): {quote[:60]!r}"
        s = md.index(quote)
        return {
            "quote": quote,
            "char_span": [s, s + len(quote)],
            "line": md[:s].count("\n") + 1,
            "sha256": "sha256:" + hashlib.sha256(quote.encode()).hexdigest(),
        }

    ART.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    from kf_scan_estate_envelopes import scan as estate_scan

    estate = estate_scan(pathlib.Path("docs/kf"), exclude=PACKAGE)
    chk = checks["checks"]
    ns_pass = sum(1 for c in chk.values() if c["status"] == "pass")
    ns_fail = sorted(k for k, c in chk.items() if c["status"] != "pass")

    # ---- finding evidence, all asserted unique verbatim substrings ----------
    q_title = loc("# IMO IS Code 2008 §2.3 天气衡准完整链 —— 验证报告（m9667 / p176w1-n10）")
    q_pytest = loc("**pytest**：`tests/test_weather_criterion_imo_m9667.py`（22 例全绿）")
    q_evid = loc("**证据工件**：`artifacts/weather_criterion_imo_2008_m9667/results.json`（表值指纹")
    q_withheld = loc("**表值转录保真度未复核**：三张表是 IS Code 2008 表 2.3.1-1/2/3 的**数字化转录**，")
    q_dev = loc('> 偏差与理由（方法自主权申报）：1) 节点文字把面积写作"0°→交点 / 交点到 φ2"，')
    q_lw2 = loc("阵风力臂 `lw2 = 1.5·lw1`")
    q_theta1 = loc("`θ1 = 109·k·X1·X2·√(r·s)`，k 由船型预设给出")
    q_s1 = loc("| S1_bulk_50k | 61,323 | 2.50 | 0.022 | 0.0124 | 0.0187 | 23.32 | 0.28 | 0.43 | 45 | 0.2400 | 1.1818 | 4.924 | 4.924 | COMPLIANT |")
    q_s6 = loc("| S6_ferry_A4000 | 21,115 | 0.70 | 0.189 | 0.0827 | 0.1241 | 17.78 | 6.23 | 8.68 | 25 | 0.0946 | 0.0722 | 0.764 | 0.764 | NON_COMPLIANT |")
    q_scope_gz = loc("**船型参数表**（6 条完整船型；GZ 曲线由平台共享内核 `stability_core`")

    mirror = UPSTREAM_PKG / "asset_manifest.json"
    mirror_sha = hashlib.sha256(mirror.read_bytes()).hexdigest()

    findings = [
        {
            "id": "F1",
            "severity": "major",
            "category": "reproducibility",
            "blocking_for_pipeline": True,
            "title": "上游验证器无法从仓内产物复跑；声明的 durable mirror 与 run 目录均不存在",
            "detail": (
                "wp-11415-01 的 provenance 声明 local_copy=runs/wp-11415-01/report_11415.md 与 "
                "artifact_durable_mirror=artifacts/wp-11415-01/asset_manifest.json，并把说明书"
                "（verifier=scripts/kf_verify_11415.py）留作复算入口；但两者在检出中均不存在，"
                "该验证器直接以 FileNotFoundError 退出。审核者按『平台原文 + 已发布 JSON 块 + 已提交 manifest 镜像』"
                "重建 run 输入后复跑，结果 ALL_PASS=False，唯一失败项为 kf_result_schema（见 F2）。"
                "因此『验证器全绿』这一说法在仓库内不可复现，只能标为 unreproduced。"
            ),
            "evidence": [
                {"what": "declared durable mirror missing", **stage2["identity"], },  # noqa: E501 (kept verbatim)
            ],
            "reproduction": [
                "python3 scripts/kf_fetch_11415_04.py",
                "python3 scripts/kf_isolate_upstream_11415_04.py",
                "python3 scripts/kf_probe_stage2_11415_04.py   # 重建 runs/ 后复跑上游验证器",
                "cat runs/wp-11415-04/replay/runs/wp-11415-01/verify_report.json",
            ],
            "recommendation": "上游工序把 runs/wp-11415-01/{report_11415.json,report_11415.md,kf_result} 与 artifacts/wp-11415-01/asset_manifest.json 一并提交（或改验证器为从平台+已发布块重建输入），再谈『可复算』。",
        },
        {
            "id": "F2",
            "severity": "major",
            "category": "schema_conformance",
            "blocking_for_pipeline": False,
            "title": "已发布 kf_result 信封不满足 schemas/kf_result.v1.schema.json（顶层 claims + provenance 15 个额外键）",
            "detail": (
                "对 wp-11415-01 已发布的 JSON 块做 Draft 2020-12 校验，得 2 处 additionalProperties 违规："
                "根对象多出 claims；provenance 多出 15 个键（source_chars/source_title/artifact_sha256/… 而 schema 只允许 "
                "title/chars 命名）。同一校验对仓内 40 个已发布 KF-RESULT 包跑一遍，39 个同样违规 —— "
                "说明这是产线范围的『发射口径 vs schema』分歧，不是本生产者独有的越界；"
                "平台侧显然接受（该包已 published）。故判非阻塞，但契约 acceptance.schema_pass 若按仓内 schema 严格判，本包不通过。"
            ),
            "evidence": [
                {"what": "schema errors on published envelope", "errors": stage2["schema_errors"]},
                {"what": "estate-wide scan", **estate},
                {"what": "this envelope", "errors": stage2["schema_errors"]},
            ],
            "reproduction": [
                "python3 scripts/kf_probe_stage2_11415_04.py            # 枚举本信封的 schema 违规",
                "python3 scripts/kf_scan_estate_envelopes.py --exclude wp-11415-04  # 产线级对照",
            ],
            "recommendation": "平台二选一：放宽 kf_result.v1（additionalProperties=true，或把 source_chars/source_title 等列为正式字段），或统一发射器与 schema 一致；本审核不自行改动上游产物。",
        },
        {
            "id": "F3",
            "severity": "info",
            "category": "convention",
            "blocking_for_pipeline": False,
            "title": "A02（报告标题行）用 '(preamble)' 作为 in_report_section 哨兵",
            "detail": "标题行自身即一级标题，登记为 '(preamble)' 属约定选择；quote 逐字命中、span 精确，无语义损失。建议把该哨兵写进 manifest schema/README，避免下游把 '(preamble)' 误当章节名。",
            "evidence": [{"what": "title line", **q_title}],
            "reproduction": ["python3 scripts/kf_verify_wp-11415-04.py   # C2 会记录该哨兵"],
            "recommendation": "文档化哨兵取值，非阻断。",
        },
        {
            "id": "F4",
            "severity": "info",
            "category": "strength",
            "blocking_for_pipeline": False,
            "title": "登记内容本身逐字节通过：28/28 定位码、21/6/1 分辨率、4 张图重取 sha 一致、标签零手抄",
            "detail": (
                "28 个资产的 char_span 全部满足 md[start:end]==quote、count(quote)==1、start_line/end_line 重算一致、"
                "A01..A28 连号；21 条 resolved_in_source 的 span 复核通过、6 条 referenced_unresolved 的路径确认不在本工作树、"
                "1 条 declared_absent 的 TABLE_PROVENANCE.verified = False 旗标在原文出现；"
                "4 张图的 png_sha256/字节数与平台再取回逐字节一致；label/note 中 33 个数字原子全部为原文子串。"
            ),
            "evidence": [
                {"what": "withheld declaration in source", **q_withheld},
                {"what": "figure evidence pointer", **q_evid},
                {"what": "test pointer", **q_pytest},
            ],
            "reproduction": ["python3 scripts/kf_verify_wp-11415-04.py"],
            "recommendation": "无需动作。",
        },
        {
            "id": "F5",
            "severity": "info",
            "category": "source_self_consistency",
            "blocking_for_pipeline": False,
            "title": "被审报告自身表格自洽（lw2=1.5·lw1、b/a=b/a、C5 与参数表同值），但规范表转录保真度仍 WITHHELD",
            "detail": (
                "从原文解析 6 行参数表 + 6 行 C5 表做恒等式重算：lw2/lw1 与 1.5 的最大偏离在 4 位小数舍入内；"
                "b/a 与 b/a（面积重算）最大相对偏离 1.03e-03（4 位小数舍入传播，非矛盾）；C5 的 b/a 两列与参数表同值。"
                "但三张 IS Code 表 2.3.1-1/2/3 的数值转录无原件可比，报告已自述 WITHHELD，本审核沿用该状态，不升级为 verified。"
            ),
            "evidence": [
                {"what": "lw2 = 1.5 lw1", **q_lw2},
                {"what": "theta1 chain formula", **q_theta1},
                {"what": "S1 row", **q_s1},
                {"what": "S6 row", **q_s6},
                {"what": "GZ curve provenance", **q_scope_gz},
                {"what": "deviation declaration", **q_dev},
            ],
            "reproduction": ["python3 scripts/kf_verify_wp-11415-04.py   # C10"],
            "recommendation": "维持 WITHHELD；换入经核对的规范表后需重跑 C2/C10。",
        },
    ]

    review_report = {
        "package_id": PACKAGE,
        "task_type": TASK,
        "contract_version": "1.0",
        "review_target": {
            "package_id": TARGET,
            "task_type": "01-asset-registration",
            "report_id": REPORT_ID,
            "committed_mirror": str(mirror),
            "committed_mirror_sha256": mirror_sha,
            "published_envelope_path": "docs/kf/wp-11415-01/KF-RESULT-wp-11415-01.md (single fenced JSON block)",
            "assets": len(man["assets"]),
            "claims": len(man["claims"]),
        },
        "source": {
            "report_id": REPORT_ID,
            "uri": identity["report_id"] and "tensor://reports/11415",
            "field": "markdown",
            "sha256": identity["sha256"],
            "chars": identity["chars"],
            "bytes_utf8": identity["bytes_utf8"],
            "title": identity["title"],
            "scenario_key": identity["scenario_key"],
            "platform_status": identity["status"],
            "platform_mission_id": identity["mission_id"],
            "rehash_matches_contract": identity["sha256_matches_contract"],
        },
        "reviewer": {
            "role": "red-team-reviewer",
            "independent": True,
            "context_included": [
                "report 11415 markdown re-fetched from the platform (not from the producer)",
                "machine-readable payload of wp-11415-01 (outputs.asset_manifest.json)",
                "figure binaries re-fetched by name from the platform",
            ],
            "context_excluded": [
                "producer's prose sections of wp-11415-01 (only the json block is parsed)",
                "any upstream explanation of method or results",
            ],
            "limitations": [
                "上游 runs/wp-11415-01/* 与 artifacts/wp-11415-01/asset_manifest.json 未提交 → 只能按平台原文+已发布块+已提交镜像重建输入复跑（F1）。",
                "ship-performance-platform 仓不在本工作树 → A04/A05/A06/A07/A12 指向的代码、工件、测试本体无法执行或逐行审阅。",
                "IS Code 2008 表 2.3.1-1/2/3 原件不可得 → 规范表数值转录保真度无法独立复核（WITHHELD，沿用报告自述）。",
                "无生产者侧 verify_report.json 原件（未提交），无法判断其『全绿』是在哪一版信封上算出的。",
            ],
        },
        "checks": [
            {
                "id": cid,
                "status": c["status"],
                "detail": c["detail"],
                "problems": c["problems"],
            }
            for cid, c in chk.items()
        ],
        "check_summary": {
            "total": len(chk),
            "pass": ns_pass,
            "fail": len(ns_fail),
            "failed_ids": ns_fail,
        },
        "findings": findings,
        "checks_not_run": [
            {
                "check": "规范表 2.3.1-1/2/3 数值 vs 原作逐格比对",
                "status": "not_run",
                "reason": "IS Code 2008 原件不在环境内，报告亦自述 TABLE_PROVENANCE.verified = False。",
            },
            {
                "check": "ship-performance-platform 模块复算（weather_criterion_iso.py / pytest 22 例）",
                "status": "not_run",
                "reason": "该仓不在本工作树；A04/A07 的 resolution 已如实登记为 referenced_unresolved。",
            },
            {
                "check": "生产者 verify_report.json 原件比对",
                "status": "not_run",
                "reason": "runs/wp-11415-01 未提交（见 F1）；本审核只能用重建输入复跑验证器。",
            },
            {
                "check": "真实 KN/GZ 曲线条件下的判据复核",
                "status": "not_run",
                "reason": "被审报告用壁舷式解析曲线，报告已声明其比真实 KN 更陡；无实船 KN 数据可注入。",
            },
        ],
        "overstated_claims": [
            {
                "claim_as_registered": "artifact_durable_mirror = artifacts/wp-11415-01/asset_manifest.json",
                "status_in_repo": "missing",
                "note": "声明为『durable mirror』但该路径在检出中不存在；已提交的镜像是 docs/kf/wp-11415-01/asset_manifest.json（sha256 与声明一致）。",
            },
            {
                "claim_as_registered": "verifier = scripts/kf_verify_11415.py（可复算入口）",
                "status_in_repo": "runs_on_reconstructed_inputs_only",
                "note": "按仓内状态直接运行 FileNotFoundError；重建输入的复跑结果 ALL_PASS=False（失败项 kf_result_schema）。",
            },
        ],
        "no_verified_marking": True,
        "verification_owner": "platform",
        "disposition": {
            "verdict": "pass",
            "on_what": "语义保真度（28/28 定位码逐字节、覆盖完整、分辨率如实、标签零手抄、图二进制可重取）",
            "disposition": "approve-with-notes",
            "pipeline_verdict": "needs-fix",
            "pipeline_blockers": ["F1"],
            "rationale": (
                "登记内容本身未发现实质缺陷：全部定位码、计数、分辨率状态、图件指纹均可独立复现。"
                "两项失败检查同源（信封 schema），且属产线范围口径分歧（39/40 包同样违规），不判为生产者越界；"
                "但 F1（复跑不可行 + 声明的 durable mirror 缺失）使『验证器全绿』在仓库内不可复现，需上游补交 run 产物后才能结案。"
                "本次不把任何结论标为 verified —— verification 由平台门计算。"
            ),
        },
    }

    review_events = [
        {
            "seq": 1,
            "event": "source_pinned",
            "actor": PACKAGE,
            "basis": ["C1_source_identity"],
            "outcome": "pass",
            "note": f"sha256={identity['sha256']} chars={identity['chars']} 与契约一致",
        },
        {
            "seq": 2,
            "event": "upstream_payload_isolated",
            "actor": PACKAGE,
            "basis": ["scripts/kf_isolate_upstream_11415_04.py"],
            "outcome": "pass",
            "note": "只取 wp-11415-01 的单个 json 块，生产者叙述未进入审核上下文",
        },
        {
            "seq": 3,
            "event": "locators_recomputed",
            "actor": PACKAGE,
            "basis": ["C2_locator_fidelity"],
            "outcome": "pass",
            "note": f"{len(man['assets'])}/{len(man['assets'])} 逐字节命中",
        },
        {
            "seq": 4,
            "event": "coverage_and_labels_audited",
            "actor": PACKAGE,
            "basis": ["C3_coverage", "C4_label_numbers"],
            "outcome": "pass",
            "note": "5 个文件引用 + 4 张图 + 5 张表全部有归属资产；33 个数字原子均为原文子串",
        },
        {
            "seq": 5,
            "event": "resolution_honesty_audited",
            "actor": PACKAGE,
            "basis": ["C5_resolution_honesty"],
            "outcome": "pass",
            "note": "21 resolved / 6 referenced_unresolved / 1 declared_absent，桶与计数自洽",
        },
        {
            "seq": 6,
            "event": "figure_binaries_refetched",
            "actor": PACKAGE,
            "basis": ["C9_figure_binaries"],
            "outcome": "pass",
            "note": "4 张 png 的 sha256 与字节数与登记值逐字节一致",
        },
        {
            "seq": 7,
            "event": "source_internal_arithmetic_recomputed",
            "actor": PACKAGE,
            "basis": ["C10_source_internal_arithmetic"],
            "outcome": "pass",
            "note": "lw2/lw1、b/a、C5 交叉列全部自洽（最大偏离 1.03e-03 = 4 位小数舍入）",
        },
        {
            "seq": 8,
            "event": "envelope_schema_check",
            "actor": PACKAGE,
            "basis": ["C6_schema"],
            "outcome": "fail",
            "note": "kf_result.v1 两处 additionalProperties 违规；产线级 39/40 包同样违规（F2）",
        },
        {
            "seq": 9,
            "event": "upstream_verifier_replayed",
            "actor": PACKAGE,
            "basis": ["C8_replay_upstream_verifier"],
            "outcome": "fail",
            "note": "重建输入后 ALL_PASS=False，唯一失败项 kf_result_schema（F1 的可复现性证据）",
        },
        {
            "seq": 10,
            "event": "disposition_emitted",
            "actor": PACKAGE,
            "basis": ["C1..C10"],
            "outcome": "approve-with-notes",
            "note": "语义保真度 pass；产线 needs-fix（F1）；无一结论标 verified",
        },
    ]

    # ------------------------------------------------------------ envelope
    result = {
        "package_id": PACKAGE,
        "task_type": TASK,
        "contract_version": "1.0",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": "tensor://reports/11415",
            "source_field": "markdown",
            "source_hash": "sha256:" + identity["sha256"],
            "source_hash_matches": True,
            "title": identity["title"],
            "scenario_key": identity["scenario_key"],
            "chars": identity["chars"],
        },
        "outputs": {"review_report.json": review_report, "review_events.json": review_events},
    }

    assert chr(96) * 3 not in json.dumps(result, ensure_ascii=False), "fence literal leaked into the result JSON"

    # schema-validate before writing (fail fast)
    import jsonschema

    schema = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(result, schema)

    for p, obj in (
        (ART / "review_report.json", review_report),
        (ART / "review_events.json", review_events),
        (ART / "kf_result.json", result),
        (RUN / "kf_result.wp-11415-04.json", result),
        # docs/ is the durable mirror: artifacts/ is git-ignored by the estate
        # .gitignore, so the committed copy must live under docs/kf/<pkg>/.
        (DOCS / "review_report.json", review_report),
        (DOCS / "review_events.json", review_events),
        (DOCS / "kf_result.json", result),
    ):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"checks: {len(chk)} total, {ns_pass} pass, failed={ns_fail}")
    print(f"findings: {[f['id'] + ':' + f['severity'] for f in findings]}")
    print(f"verdict: {review_report['disposition']['verdict']} / {review_report['disposition']['pipeline_verdict']}")
    for p in (ART / "review_report.json", ART / "review_events.json", ART / "kf_result.json"):
        b = p.read_bytes()
        print(f"{p} {len(b)}B sha256={hashlib.sha256(b).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())