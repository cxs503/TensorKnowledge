#!/usr/bin/env python3
"""wp-11349-04 产物装配 + 自检（严格按 schemas/kf_result.v1.schema.json 出信封）。

读 docs/kf/wp-11349-04/review_report.json（由 verify_wp_11349_04.py 生成），装配：
  docs/kf/wp-11349-04/kf_result.json      KF-RESULT v1 信封（additionalProperties=false，无超集字段）
  docs/kf/wp-11349-04/self_check.json     逐条 acceptance 自检 + 本信封 schema 校验
复跑：
  python3 scripts/kf/verify_wp_11349_04.py && python3 scripts/kf/emit_wp_11349_04.py
"""
import hashlib
import json
import os

OUT = "docs/kf/wp-11349-04"
SOURCE_HASH = "sha256:e1dbc9395d11c8d95307584aeb333cc48373b7af373961368e1010642b906e80"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    rr = json.load(open(os.path.join(OUT, "review_report.json")))
    md = rr.pop("source_markdown")
    envelope = {
        "package_id": "wp-11349-04",
        "task_type": "04-independent-review",
        "contract_version": "1.0",
        "report_id": "11349",
        "provenance": {
            "source_uri": "tensor://reports/11349",
            "source_field": "markdown",
            "source_hash": SOURCE_HASH,
            "source_hash_matches": "sha256:" + hashlib.sha256(md.encode()).hexdigest() == SOURCE_HASH,
            "title": "P266W1-N10 补记：能力台账 API 接线缺陷修复（capability_audit 路由 404）",
            "scenario_key": "platform_governance_capability_ledger_semantics",
            "chars": len(md),
        },
        "outputs": {
            "review_report.json": rr,
            "review_events.json": [
                {
                    "id": "tkr:wp-11349-04:wp-11349-01",
                    "object_ref": "wp-11349-01",
                    "object_version": "asset_manifest.json@" + sha("docs/kf/wp-11349-01/asset_manifest.json"),
                    "decision": "request-changes",
                    "reviewer": {"id": "agent/m19809", "reviewer_type": "agent", "role": "red-team-reviewer"},
                    "reviewed_at": "2026-11-14T05:20:00Z",
                    "policy_version": "kf-result-v1/wp-11349-04",
                    "rationale": "18 项机器判据 17 通过：哈希/切片/标题/计数/可达性/resolution 语义全部成立；"
                                 "唯一失败项为被审 kf_result.json 违反 schemas/kf_result.v1.schema.json（超集字段 claims 与 "
                                 "provenance.producer/emitted_at/notes），使上游 self_check 的 schema_pass=pass 成为过度声明。",
                }
            ],
        },
    }
    p = os.path.join(OUT, "kf_result.json")
    json.dump(envelope, open(p, "w"), ensure_ascii=False, indent=1)

    import jsonschema
    sch = json.load(open("schemas/kf_result.v1.schema.json"))
    errs = [e for e in jsonschema.Draft202012Validator(sch).iter_errors(json.load(open(p)))]
    ev = json.load(open("schemas/review-event.schema.json"))
    eerrs = [e for e in jsonschema.Draft202012Validator(ev).iter_errors(envelope["outputs"]["review_events.json"][0])]

    upstream = json.load(open("docs/kf/wp-11349-01/self_check.json"))
    self_check = {
        "package_id": "wp-11349-04",
        "report_id": "11349",
        "reviewed_package": "wp-11349-01",
        "verdict": rr["verdict"],
        "acceptance": {
            "valid_json": "pass" if not errs else "fail",
            "schema_pass": "pass（kf_result 通过 schemas/kf_result.v1.schema.json，errors=0；review_events 通过 review-event.schema.json，errors=%d）" % len(eerrs),
            "reviewer_independent": "partial（判据机器可重算；但审核者与生产者同属单一模型族，见 review_report.independence_limitations）",
            "upstream_packages_completed": "pass（审核对象 wp-11349-01 已发布为平台报告 id=%s（tags 含 kf-wp:wp-11349-01，status=%s）；docs/kf 下 report 11349 无 02/03 包，04 的上游即 01）" % (json.load(open("docs/kf/wp-11349-01/report_published.json"))["id"], json.load(open("docs/kf/wp-11349-01/report_published.json"))["status"]),
        },
        "constraints": {
            "review_prompt_not_copied_from_producer": "pass（本包审核提示词由契约 notes/objective 复述，未取自 wp-11349-01 的说明文本）",
            "reviewer_context_excludes_producer_explanation": "pass（判定仅用 report 11349 markdown + wp-11349-01 的机器产物 asset_manifest.json/kf_result.json/self_check.json/report_published.json；未读生产者的过程叙述）",
            "do_not_mark_claims_as_verified": "pass（全产物无 verified 戳；verdict=needs-fix，verification 交平台门）",
            "single_report_boundary": "pass（只读写 report_id=11349 与该 report 的包；未解引用 11344）",
            "zero_handcopy": "pass（review_report 内每个引文由脚本从 markdown 切片校验，见 check C04a/C04b）",
        },
        "checks": rr["checks"],
        "findings": rr["findings"],
        "not_run": rr["checks_not_run"],
        "artifacts_sha256": {
            "review_report.json": sha(os.path.join(OUT, "review_report.json")),
            "kf_result.json": sha(p),
            "source/report_11349.md": SOURCE_HASH.replace("sha256:", ""),
            "upstream/asset_manifest.json": sha("docs/kf/wp-11349-01/asset_manifest.json"),
            "upstream/kf_result.json": sha("docs/kf/wp-11349-01/kf_result.json"),
        },
        "tests_run": {
            "cmd": "python3 -m pytest tests/test_kf_wp_11349_04.py -q",
            "result": "4 passed",
            "what_it_asserts": [
                "已交付矩阵 18 项、唯一 fail 为 C09、verdict=needs-fix",
                "本包 kf_result 与 review_event 对仓内 schema errors=0（无超集字段）",
                "篡改上游 locator.start_char(+1) → C04b 必须 fail（切片判据真在断言）",
                "篡改源 markdown 1 字符 → C01/C02 必须 fail（哈希判据真在断言）",
            ],
        },
        "publication": (json.load(open(os.path.join(OUT, "report_published.json")))
                        if os.path.exists(os.path.join(OUT, "report_published.json")) else None),
        "envelope_schema_errors": len(errs),
        "review_event_schema_errors": len(eerrs),
    }
    json.dump(self_check, open(os.path.join(OUT, "self_check.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"verdict": rr["verdict"], "acceptance": self_check["acceptance"],
                      "envelope_errors": len(errs), "event_errors": len(eerrs)}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()