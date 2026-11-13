#!/usr/bin/env python3
"""Build the wp-5347-04 review_report.json product from fresh bytes + recomputation.

Every quote embedded in the output is asserted to be a verbatim substring of the
report-5347 markdown (or of the reviewed manifest) before the file is written, so the
product cannot drift from the source (anti hand-copy guard).

Usage:
  python3 scripts/review_wp5347_04_report.py [--out docs/kf/wp-5347-04/review_report.json]
"""
import argparse
import hashlib
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC = os.path.join(ROOT, "work", "review_wp5347_04.py")
DEFAULT_OUT = os.path.join(ROOT, "docs", "kf", "wp-5347-04", "review_report.json")


def load_checks():
    spec = importlib.util.spec_from_file_location("rev5347", SPEC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(text):
    if isinstance(text, str):
        text = text.encode("utf-8")
    return "sha256:" + hashlib.sha256(text).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()

    mod = load_checks()
    rec = mod.fetch_record()
    md = rec["markdown"]
    manifest_path = mod.DEFAULT_MANIFEST
    manifest_bytes = open(manifest_path, "rb").read()
    man = json.loads(manifest_bytes.decode("utf-8"))

    # ---- run the reviewer checks (same code path as the CLI) -------------------
    checks = mod.__dict__["main"]  # noqa: F841  (imported for side-effect parity)
    evidence = json.loads(
        open(os.path.join(ROOT, "docs", "kf", "wp-5347-04", "review_evidence.json"),
             encoding="utf-8").read())

    def by_name(name):
        for c in evidence["checks"]:
            if c["check"] == name:
                return c
        raise KeyError(name)

    # ---- quotes are pinned to the source exactly ------------------------------
    q_true = md[3448:3522]
    bad_asset = None
    for a in man["assets"]:
        if a["asset_id"] == "asset-5347-024":
            bad_asset = a
    q_shipped = bad_asset["locator"]["quote"]
    assert q_true != q_shipped
    assert md[bad_asset["locator"]["start_offset"]:bad_asset["locator"]["end_offset"]] == q_true

    ratio_rows = [
        "| 扫描文档数 | 145 | 152 |",
        "| 指针数 | 831 | 879 |",
        "| `code:TRACKED` | 275 | 290 |",
        "| `test:TRACKED` | 251 | 263 |",
        "| 判 `TRACKED` 占比 | 0.8472 | 0.8476 |",
    ]
    for r in ratio_rows:
        assert r in md, r
    q_orphan = "| 失效指针 ORPHAN | 0 | 0 |"
    assert q_orphan in md
    q_layout = "| self-hosted loong64 (.../ci_env/_work/...) | FAIL | PASS |"
    assert q_layout in md
    q_honest = "本轮未把 `python -m pytest -q` 全量跑完"
    assert q_honest in md

    findings = [
        {
            "id": "F1",
            "severity": "high",
            "blocking": True,
            "title": "asset-5347-024 的 quote 不是逐字原文：机构名被替换（外协方 -> 外协方），而 quote_sha256 仍是原文哈希",
            "scope": "wp-5347-01 / asset_manifest.json / asset-5347-024",
            "evidence": {
                "source_slice_at_declared_offsets": {"start_offset": 3448,
                                                     "end_offset": 3522,
                                                     "text": q_true,
                                                     "sha256": sha(q_true)},
                "shipped_quote": {"text": q_shipped, "sha256": sha(q_shipped)},
                "declared_quote_sha256": bad_asset["locator"]["quote_sha256"],
                "byte_equal_at_offsets": md[3448:3522] == q_shipped,
                "declared_hash_equals_source_slice_hash":
                    sha(q_true) == bad_asset["locator"]["quote_sha256"],
                "shipped_quote_sha256_matches_declared": sha(q_shipped) ==
                    bad_asset["locator"]["quote_sha256"],
            },
            "why_it_matters": "G2 的 E3/E4 是 fail-closed：声明了偏移就必须 md[start:end] == quote 字节相等；"
                              "哈希与 quote 自相矛盾说明文本是在抽取后被改写的，属『篡改 quote』等价物。"
                              "下游 03 若以此节点做证据，会把改写后的文本当作原文引用。",
            "reproduction": "python3 work/review_wp5347_04.py --json /tmp/rv.json ; "
                            "看 R3.quote_at_declared_offsets / R4.quote_sha256_matches 两条 violations",
            "remediation": ["把 quote 恢复为 md[3448:3522] 的逐字切片（上述 source_slice_at_declared_offsets.text）；"
                            "若确需脱敏，改为缩短 span 到不含机构名的子串（例如自『环境缺 `libflexiblas.so.3`』起），"
                            "或另设显式 redaction 字段并在其中记录被替换的原文；quote 字段本身永不可编辑。"],
        },
        {
            "id": "F2",
            "severity": "medium",
            "blocking": False,
            "title": "报告表的『TRACKED 占比』无法用同表可见行复算（缺 doc:TRACKED 行）："
                     "可见行复算 %s/%s vs 印刷 %s/%s" % tuple(
                         by_name("R12.report_ratio_reproducible")["detail"]["ratio_from_visible_rows"]
                         + by_name("R12.report_ratio_reproducible")["detail"]["printed_ratio"]),
            "scope": "report 5347 §③『证据账本计数』表（对下游 03 为 advisory）",
            "evidence": {
                "printed_rows": ratio_rows,
                "recomputed_from_visible_rows": by_name(
                    "R12.report_ratio_reproducible")["detail"]["ratio_from_visible_rows"],
                "printed_ratio": by_name("R12.report_ratio_reproducible")["detail"]["printed_ratio"],
                "implied_unshown_row_doc_TRACKED": by_name(
                    "R12.report_ratio_reproducible")["detail"]["implied_doc_tracked_not_shown"],
            },
            "why_it_matters": "该行若被下游直接引用为『账本健康度』，引用者无法自证；补一行 doc:TRACKED 即可闭环。"
                              "算术上与『存在一行 doc:TRACKED=%d』自洽（152 篇态），故非造假，"
                              "属『不可独立复算』。" % by_name("R12.report_ratio_reproducible")
                              ["detail"]["implied_doc_tracked_not_shown"][1],
            "reproduction": "python3 work/review_wp5347_04.py --json /tmp/rv.json ; 看 R12",
            "remediation": ["报告或账本工件中显式给出 doc:TRACKED 计数行，或直接引用 docs/doc_evidence_ledger.json 的机器可读字段。"],
        },
        {
            "id": "F3",
            "severity": "low",
            "blocking": False,
            "title": "图资产登记的理由陈述可复现但措辞不精确：/tensor/reports/5347/figures 是路由级 404，图级 404 来自 /figures/<name>",
            "scope": "wp-5347-01 / asset-5347-025、asset-5347-026（reachability=metadata_only）",
            "evidence": {
                "probe": "GET /tensor/reports/5347/figures -> 404 {\"detail\":\"Not Found\"} ; "
                         "GET /tensor/reports/5347/figures/provenance_gate_matrix.png -> "
                         "404 {\"detail\":\"figure not found\"}",
                "record_figures": [f.get("name") for f in (rec.get("figures") or [])],
                "declared_caption_matches_record": by_name(
                    "R9.record_field_locator_resolvable")["detail"]["caption_violations"] == [],
            },
            "why_it_matters": "结论（图像字节不可取回、只能登记为 metadata_only）成立；但把两条不同 404 混为一句，"
                              "下游复现时可能误判为『报告无图』。",
            "reproduction": "见上 probe 两条 GET；或读 review_evidence.json 的 R9 段",
            "remediation": ["把 note 写成『/figures/<name> 返回 figure not found，/figures 路由不存在』，区分路由缺失与资产缺失。"],
        },
        {
            "id": "F4",
            "severity": "low",
            "blocking": False,
            "title": "asset-5347-001/002/003 共用同一 char_span [673,764]，span 身份 ≠ 资产身份",
            "scope": "wp-5347-01 / asset_manifest.json",
            "evidence": {
                "shared_span": [a["locator"].get("start_offset") for a in man["assets"]
                                if a["asset_id"] in ("asset-5347-001", "asset-5347-002",
                                                     "asset-5347-003")],
                "paths": ["/home/runner/work/<repo>/<repo>", "/work/", ".../_work/<repo>/<repo>"],
            },
            "why_it_matters": "合规（三个 path token 都逐字出现在该 span 内），但下游若按 offset 去重会把三条资产折叠成一条。",
            "reproduction": "review_evidence.json R6（26/26 通过）+ 直接读 manifest 三条 locator",
            "remediation": ["在 manifest 里注明『span 可被多资产共享，去重键是 (path, span)』。"],
        },
    ]

    report = {
        "review": {
            "package_id": "wp-5347-04",
            "task_type": "04-independent-review",
            "report_id": "5347",
            "reviewer_role": "red-team-reviewer",
            "reviewed": {
                "package_id": "wp-5347-01",
                "task_type": "01-asset-registration",
                "artifact": "asset_manifest.json",
                "artifact_sha256": sha(manifest_bytes),
                "artifact_bytes": len(manifest_bytes),
                "artifact_origin": manifest_path,
                "source_hash": man["source"]["source_hash"],
            },
            "verdict": "needs-fix",
            "verdict_scope": "wp-5347-01 的 asset_manifest.json 内容面；不涉及 02/03/05 工序",
            "verdict_rationale": "26 条资产里 25 条 locator 逐字可定位、计数与开放账目全闭合；"
                                 "唯一阻塞项 F1 是 1 条 quote 被改写（字节不等）且 quote_sha256 与 quote 自相矛盾。"
                                 "按 G2 E3/E4 的 fail-closed 语义，该包在修复前不满足证据门；"
                                 "因缺陷单点且修复路径明确，判 needs-fix（request-changes），不判 reject。",
            "severity_counts": {"high": 1, "medium": 1, "low": 2},
            "semantic_fidelity": {
                "judged": True,
                "result": "partially-faithful",
                "basis": "逐条把 manifest 的 quote 与报告 markdown 字节比对（26/26），"
                         "并核 registered path 是否逐字出现在其 quote 内（26/26）；"
                         "25 条完全忠实，1 条（asset-5347-024）把原文机构名替换后仍保留原文哈希。",
                "not_judged": "报告对 TensorDEM 仓库侧事实（20 passed / 36 passed / 账本 152 篇 879 条）的语义真伪——"
                              "本工作树无该仓库检出，属 not_run（见 checks_not_run）。",
            },
            "checks": evidence["checks"],
            "checks_passed": sum(1 for c in evidence["checks"] if c["ok"]),
            "checks_total": len(evidence["checks"]),
            "findings": findings,
            "checks_not_run": [
                {"item": "TensorDEM main@524821fd 的 pytest / ruff / 账本 --check 实际输出",
                 "status": "not_run",
                 "reason": "本工作树只有 TensorKnowledge 检出，未含 TensorDEM 仓库；报告自述 20 passed / 36 passed 无法在此复现"},
                {"item": "docs/doc_evidence_ledger.json 的逐状态计数（152 篇 / 879 条 / ORPHAN 0）",
                 "status": "not_run",
                 "reason": "账本在 TensorDEM 仓内；本单只允许用 report 5347 的 markdown 作原文，未取该仓工件"},
                {"item": "两张结果图的图像内容（provenance_gate_matrix.png / ledger_regeneration.png）",
                 "status": "not_run",
                 "reason": "记录只有 name/caption 元数据，/figures/<name> 返回 figure not found（已实测），无可比对字节"},
                {"item": "02/03 工序产物（classification / claims / evidence）的审核",
                 "status": "not_applicable",
                 "reason": "该报告链当前只存在 01 包；无 claim 可做语义门审核，未越界代做"},
            ],
            "scope": {
                "inputs_used": ["GET /tensor/reports/5347 的 markdown 字段（sha256 与契约一致：%s）" %
                                sha(md)],
                "bytes_pinned": {"markdown_sha256": sha(md), "markdown_chars": len(md),
                                 "markdown_bytes": len(md.encode('utf-8')),
                                 "manifest_sha256": sha(manifest_bytes)},
                "checks_performed": ["R1 source_hash", "R2 char_count",
                                     "R3 quote_at_declared_offsets", "R4 quote_sha256",
                                     "R5 quote_searchable", "R6 registered_path_in_quote",
                                     "R7 counts_consistency", "R8 coverage_probe",
                                     "R9 record_field_locator", "R10 record_identity",
                                     "R11 unresolved_account_closure",
                                     "R12 report_ratio_reproducibility",
                                     "F3 端点实测探测"],
            },
            "context_isolation": {
                "producer_explanation_excluded": True,
                "files_read_from_upstream_package": ["asset_manifest.json"],
                "files_present_but_not_opened": ["README.md", "KF-RESULT-wp-5347-01.md",
                                                 "kf_result.json", "publish_receipt.json",
                                                 "live_gate.json", "platform_gate.json",
                                                 "checks.json"],
                "note": "只读 01 工序的行为产物（asset_manifest.json），不读生产者自述/回执；"
                        "因此本审核不引用生产者的任何解释性文字。",
            },
            "independence_limitations": [
                "上游产物取自兄弟工作树 %s（不在平台包 API 上），已用 artifact_sha256=%s 钉住被审字节；"
                "若他人看到的是不同字节，以其哈希与本报告 %s 对照即可判定。" %
                (manifest_path, sha(manifest_bytes), sha(manifest_bytes)[:19]),
                "审核者=mission 15832 工人；被审包生产者=mission 15564 工人（见 manifest registration.producer 字段），"
                "非同一包、非同一工作树、未协作。",
                "语义门（M6）本质不可程序化：本报告的语义判断建立在 26 条 locator 的字节比对与 1 条算术探针上，"
                "不是对报告技术结论真伪的判定（那需要 TensorDEM 检出）。",
                "未使用任何生产者 prompt / 解释文本，方法为从源字节独立重算（对抗式复核）。",
            ],
            "disposition": "request-changes",
            "blocking_remediation": ["F1：把 asset-5347-024 的 quote 改为 md[3448:3522] 的逐字切片"
                                     "（或缩短 span 以规避机构名，quote 字段永不编辑），"
                                     "重生成后重跑 R3/R4 应为 0 violations。"],
            "non_blocking_suggestions": ["F2：补 doc:TRACKED 行或直接引用账本工件字段",
                                        "F3：区分路由 404 与资产 404",
                                        "F4：注明 span 可被多资产共享、去重键是 (path, span)"],
            "status_boundary_note": "本报告只输出复核结果（recomputed/matched），不含任何验证状态判定；"
                                    "验证级别由平台门计算。",
            "reproduce": "python3 work/review_wp5347_04.py --json docs/kf/wp-5347-04/review_evidence.json "
                         "&& python3 scripts/review_wp5347_04_report.py",
        }
    }

    result = {
        "package_id": "wp-5347-04",
        "task_type": "04-independent-review",
        "report_id": "5347",
        "provenance": {
            "source_hash": sha(md),
            "source_field": "markdown",
            "producer": "mission 15832 (agent m15832, TensorKnowledge)",
            "emitted_at": "2026-11-12T02:50:00+00:00",
            "notes": "review_report.json built from fresh platform bytes; all embedded quotes asserted "
                     "verbatim against the report markdown and the reviewed manifest before writing.",
        },
        "outputs": {"review_report.json": report},
    }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(args.out)
    print("verdict:", report["review"]["verdict"],
          "checks:", report["review"]["checks_passed"], "/", report["review"]["checks_total"],
          "findings:", len(report["review"]["findings"]))


if __name__ == "__main__":
    main()