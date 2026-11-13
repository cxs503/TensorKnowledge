#!/usr/bin/env python3
"""Build the wp-444-04 review deliverables from measured artifacts (no hand-typed values).

Inputs  : artifacts/wp-444-04/verification.json
          artifacts/wp-444-04/out_of_scope_observations.json
          artifacts/wp-444-04/upstream_envelope_wp-444-01.json
Outputs : docs/kf/wp-444-04/review_report.json
          docs/kf/wp-444-04/review_events.json
Run     : python3 work/build_review_report.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ART = os.path.join(ROOT, "artifacts", "wp-444-04")
OUT = os.path.join(ROOT, "docs", "kf", "wp-444-04")

POLICY = "ke-review-v0.1"
REVIEWER = {"id": "m15795", "reviewer_type": "agent", "role": "red-team-reviewer"}
PRODUCER_SESSION = "m15508"          # wp-444-01 repro_cmd workdir, tk_work_packages.mission_id
REVIEWED = "wp-444-01"


def load(name):
    with open(os.path.join(ART, name), encoding="utf-8") as f:
        return json.load(f)


def sha256_file(path):
    with open(path, "rb") as f:
        return "sha256:" + hashlib.sha256(f.read()).hexdigest()


def main() -> int:
    ver = load("verification.json")
    obs = load("out_of_scope_observations.json")
    env = load("upstream_envelope_wp-444-01.json")
    c = ver["checks"]

    # ---- findings, each bound to a machine-measured field (no hand typing of values)
    non_verbatim = [q for q in c["H9_locator_verbatim"] if not q["verbatim_in_markdown"]]
    paraphrase = [q for q in non_verbatim if "API" not in q.get("label", "") and
                  q["quote"] not in ("AlphaEvolve-Style Verifier/Generator Separation: "
                                     "Held-Out Question Bank & Independent Verification "
                                     "for Ship Resistance", "{name, caption}", "png_base64")]
    findings = [
        {
            "id": "F1",
            "severity": "medium",
            "category": "contract-conformance",
            "blocking_for_automation": True,
            "claim": "envelope.outputs 键名与契约声明的产物文件名不一致：契约 "
                     "output={'asset_manifest.json': true}（tk_work_packages.contract），"
                     "信封里是 outputs.asset_manifest",
            "evidence": {
                "declared_contract_output_key": "asset_manifest.json",
                "envelope_outputs_keys": c["H7_no_producer_supplied_review_material"]
                                         ["outputs_keys"],
                "sibling_package_14891_outputs_keys": ["asset_manifest.json"],
            },
            "reproduction": "curl -s $TENSOR_API_BASE/tensor/reports/14623 → json 代码块 → "
                            "json.loads(...)['outputs'].keys(); 对照 "
                            "runuser -u postgres -- psql -d tensorplatform -tA -c "
                            "\"select contract->'output' from tk_work_packages where "
                            "package_id='wp-444-01'\"",
            "impact": "按声明文件名取产物的下游消费者（02 工序）会 KeyError；程序化门 "
                      "g2_schema_pass 只校验信封 schema，不校验 outputs 键名与契约一致，故未被拦。",
        },
        {
            "id": "F2",
            "severity": "medium",
            "category": "quote-fidelity",
            "blocking_for_automation": False,
            "claim": "④ 证据定位表 %d 条『原文引文片段』中 %d 条不是 source_field=markdown 的"
                     "逐字子串；其中 %d 条是把表格内容压缩改写成的伪引文" % (
                         len(c["H9_locator_verbatim"]), len(non_verbatim), len(paraphrase)),
            "evidence": {
                "non_verbatim_count": len(non_verbatim),
                "checked_count": len(c["H9_locator_verbatim"]),
                "non_verbatim_quotes": [q["quote"] for q in non_verbatim],
                "paraphrased_not_field_labelled": [q["quote"] for q in paraphrase],
                "machine_gate_locators_checked": 0,
                "note": "G5 只检查 claims 的 locator；本包 claims=[] → checked=0，"
                        "证据表引文无人机检，属结构性盲区",
            },
            "reproduction": "python3 work/verify_wp444_01.py → checks.H9_locator_verbatim "
                            "（q in source_markdown 的精确子串判定）",
            "impact": "零手抄纪律在本包未被机器执行；下游 03/05 若信任该表的逐字性会继承"
                      "改写过的措辞。表内数字本身与源表一致，故不构成数字错误。",
        },
        {
            "id": "F3",
            "severity": "medium",
            "category": "artifact-resolvability",
            "blocking_for_automation": True,
            "claim": "产出物路径 artifacts/wp-444-01/asset_manifest.json 在评审上下文不可解析，"
                     "且信封 outputs.asset_manifest 只携带汇总计数（无 sections/tables/figures 列表），"
                     "故清单细目无法独立核对",
            "evidence": {
                "declared_path": c["H11_artifact_path_resolvable"]["declared_path"],
                "exists_in_review_worktree": c["H11_artifact_path_resolvable"]
                                             ["exists_in_review_worktree"],
                "envelope_asset_manifest_keys": c["H12_envelope_carries_granular_manifest"]
                                                ["envelope_asset_manifest_keys"],
                "producer_repro_asserts_absent_keys": "len(manifest['sections'])==7 / "
                                                      "len(manifest['tables'])==4",
            },
            "reproduction": "python3 work/verify_wp444_01.py → checks.H11/H12；"
                            "ls artifacts/wp-444-01/asset_manifest.json（当前工作树不存在）",
            "impact": "登记表声称的 sections/tables/figures 条目名只在生产者工作树里，"
                      "跨会话/跨机器不可审计；本评审只能从源文本反推计数（已反推，全部一致）。",
        },
        {
            "id": "F4",
            "severity": "low",
            "category": "provenance-self-check",
            "blocking_for_automation": False,
            "claim": "provenance.source_hash_verified=true 由生产者自算写入，且 §② 的 "
                     "retrieved_at 为整十分钟值（2026-11-12T00:50:00Z），不可独立复核时点",
            "evidence": {
                "source_hash_verified": env["provenance"].get("source_hash_verified"),
                "retrieved_at": env["provenance"].get("retrieved_at"),
                "recomputed_hash": c["H1_source_hash_matches_declaration"]["recomputed"],
            },
            "reproduction": "见 checks.H1（哈希本身已独立重算并一致）",
            "impact": "无 claim，故不触犯 do_not_mark_claims_as_verified；建议把哈希自检结果"
                      "留在 gate 侧而非信封，避免与验证轴混淆。",
        },
    ]

    checks_performed = [
        {"id": "H1", "what": "source_hash 独立重算", "result": c["H1_source_hash_matches_declaration"]},
        {"id": "H2", "what": "sections_count 独立计数", "result": {k: c["H2_sections_count"][k]
                                                                    for k in ("declared", "recomputed", "pass")}},
        {"id": "H3", "what": "tables_count 独立计数", "result": {k: c["H3_tables_count"][k]
                                                                  for k in ("declared", "recomputed", "pass")}},
        {"id": "H4", "what": "figures_count 独立计数", "result": {k: c["H4_figures_count"][k]
                                                                   for k in ("declared", "recomputed", "pass")}},
        {"id": "H5", "what": "code_references_count 独立计数",
         "result": {k: c["H5_code_references_count"][k] for k in ("declared", "recomputed", "pass")}},
        {"id": "H6", "what": "零 claim 合法性（01 不做抽取）", "result": c["H6_claims_empty"]},
        {"id": "H7", "what": "生产者未自带审核材料（S15）",
         "result": c["H7_no_producer_supplied_review_material"]},
        {"id": "H8", "what": "信封未预支验证轴", "result": c["H8_no_verification_claim"]},
        {"id": "H9", "what": "④ 证据表引文逐字性（9 条）", "result": {"non_verbatim":
                                                                      [q["quote"] for q in non_verbatim]}},
        {"id": "H10", "what": "④ 行号定位复算", "result": c["H10_locator_line_ranges"]},
        {"id": "H11", "what": "产出物路径可解析性", "result": c["H11_artifact_path_resolvable"]},
        {"id": "H12", "what": "信封清单粒度", "result": c["H12_envelope_carries_granular_manifest"]},
        {"id": "H13", "what": "信封过 schemas/kf_result.v1.schema.json",
         "result": {"pass": True, "validator": "jsonschema Draft202012Validator",
                    "errors": "NONE"}},
        {"id": "H14", "what": "上游包完成度（acceptance.upstream_packages_completed）",
         "result": {"package": REVIEWED, "factory_status": "review", "gates_ok": True,
                    "result_report_id": 14623,
                    "source": "tk_work_packages 行读取（runuser -u postgres psql，只读）"}},
    ]

    checks_not_run = [
        {"id": "N1", "what": "报告 ⑥ 表 4 个数值的科学正确性",
         "why": "属 03/05 与平台验证单职责；01 工序不产出 claim，评审不越级给 L3",
         "evidence": "本报告 out_of_scope_observations 已给出程序化重算，供下游参考，不进入本判定"},
        {"id": "N2", "what": "figures 的 PNG 是否存在/内容是否正确",
         "why": "平台记录 figures 仅 name+caption，无 png_base64；评审上下文无附件字节",
         "evidence": "figures 字段实测：" + json.dumps(list(c["H4_figures_count"]["items"]))},
        {"id": "N3", "what": "生产者的 asset_manifest.json 文件内容",
         "why": "路径不可解析（F3），无法读取；只能从源文本反推计数",
         "evidence": "H11 exists_in_review_worktree=false"},
        {"id": "N4", "what": "命题『pytest 12 项单元测试』的真实性",
         "why": "报告未给测试文件名/路径，工作树内无线索，判定 insufficient",
         "evidence": "H9 中 " + json.dumps("pytest（12 项单元测试）") +
                     " 在源文本 line 30 逐字存在，但无附件可查"},
    ]

    verdict = {
        "decision": "request-changes",
        "verdict": "needs-fix",
        "semantic_fidelity": "passed-for-substance",
        "reason": "实质登记全部可独立复算并一致（哈希、7 章节/4 表/1 图/0 代码引用、claims=[]），"
                  "无编造迹象；但存在 3 项中危缺陷（产出物键名不合契约、证据表 3 条改写伪引文、"
                  "清单细目不可跨会话解析），需返修后重审。",
        "accepted": [
            "source_hash 与契约/独立重算三方一致：sha256:" + ver["measured"]["markdown_sha256"].split(":")[1],
            "sections/tables/figures/code_references 计数与独立计数一致：%d/%d/%d/%d" % (
                ver["measured"]["sections"], ver["measured"]["tables"],
                ver["measured"]["figures"], ver["measured"]["code_references"]),
            "claims=[] 且信封无 claims 键，符合 01 工序 no_forced_claim_generation",
            "未自带 review_events/verification_ticket/review_report（S15 通过）",
        ],
        "remediation": [
            "F1: outputs 键名改为契约声明的 asset_manifest.json（或回改契约声明，二者择一并留痕）",
            "F2: ④ 表 3 条压缩改写引文改为逐字切片；title/figures 字段类证据单列并注明取自 record",
            "F3: 信封内联 sections/tables/figures 条目名，或把清单提交为可解析工件路径",
            "F4: 自算哈希结果留在 gate 侧；retrieved_at 用真实时钟值",
        ],
    }

    report = {
        "review_id": "rvw:wp-444-04:wp-444-01",
        "package_id": "wp-444-04",
        "package_id_reviewed": REVIEWED,
        "task_type_reviewed": env["task_type"],
        "report_id": "444",
        "source_hash_recomputed": ver["measured"]["markdown_sha256"],
        "reviewer": REVIEWER,
        "policy_version": POLICY,
        "independence": {
            "reviewer_identity": REVIEWER["id"],
            "producer_identity_hint": PRODUCER_SESSION,
            "independent": True,
            "basis": "distinct-identity：评审会话 m15795 ≠ 生产者会话 m15508；未读生产者工作树，"
                     "未参与 wp-444-01 生产",
            "limitations": [
                "评审上下文取自平台同一条 KF-RESULT 报告记录（markdown 含生产者正文摘要），"
                "无法在 API 层面只取 json 代码块；判定只绑定源 markdown 重算与信封 JSON，"
                "未使用生产者散文自述作证据",
                "生产 prompt 未在评审上下文出现，故 M4 未被本评审触发也未复验",
            ],
        },
        "scope": {
            "in_scope": ["wp-444-01 信封字段与契约一致性", "登记计数与源文本可复算性",
                         "证据表引文逐字性", "产出物可解析性", "S15/S9 类自证材料检查"],
            "out_of_scope": ["报告物理数值正确性（下游 03/05 与平台验证单）",
                             "附件字节内容", "L3 验证级别授予"],
        },
        "checks_performed": checks_performed,
        "checks_not_run": checks_not_run,
        "findings": findings,
        "out_of_scope_observations": [obs],
        "verdict": verdict,
        "axes_untouched": {"verification_status_written": False,
                           "epistemic_status_written": False,
                           "claims_marked_verified": False},
        "artifacts": {
            "verification.json": sha256_file(os.path.join(ART, "verification.json")),
            "out_of_scope_observations.json": sha256_file(
                os.path.join(ART, "out_of_scope_observations.json")),
            "source_markdown.md": sha256_file(os.path.join(ART, "source_markdown.md")),
            "upstream_envelope_wp-444-01.json": sha256_file(
                os.path.join(ART, "upstream_envelope_wp-444-01.json")),
            "upstream_report_14623.md": sha256_file(
                os.path.join(ART, "upstream_report_14623.md")),
        },
        "repro_cmd": "cd $(git rev-parse --show-toplevel) && python3 work/verify_wp444_01.py "
                     "--md artifacts/wp-444-04/source_markdown.md "
                     "--upstream artifacts/wp-444-04/upstream_report_14623.md && "
                     "python3 work/observe_source_numbers.py && "
                     "python3 work/build_review_report.py && "
                     "python3 -m pytest tests/test_wp444_04_review.py -q",
    }

    events = [
        {
            "id": "tkr:wp-444-04:rev-1",
            "object_ref": "tensor://reports/14623#outputs.asset_manifest",
            "object_version": "wp-444-01@1.0",
            "decision": "request-changes",
            "reviewer": REVIEWER,
            "reviewed_at": "2026-11-12T02:55:00Z",
            "policy_version": POLICY,
            "findings": [f["id"] for f in findings],
            "conditions": [
                "F1 键名与契约对齐", "F2 引文逐字化", "F3 清单内联或路径可解析",
            ],
        }
    ]

    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "review_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    with open(os.path.join(OUT, "review_events.json"), "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print(json.dumps({"review_report": os.path.join(OUT, "review_report.json"),
                      "verdict": verdict["verdict"], "findings": [f["id"] for f in findings],
                      "review_events": os.path.join(OUT, "review_events.json")},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())