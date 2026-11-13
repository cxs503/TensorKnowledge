"""KO Schema v1 一致性语料（benchmark 的 ref 侧）。

纪律：**ref 是规格，不是实测**。每条 case 的期望结论直接抄自
``docs/rci/schema-v1.md`` 的规则条款（条款号写在 ``ref_rule``），
``got`` 由 :func:`run_benchmark.evaluate` 现场用 ``scripts/validate_ko_v1.py`` 跑出来。
两侧不共享代码，才有对照意义。
"""
from __future__ import annotations

import copy
import json

REPORT_MD = """# 报告

## ① 案例介绍
圆柱绕流，Re=100，D=1，U=1。

## ② 怎么做的
LBM D2Q9，格子 512x256，时间步 20000。

## ③ 计算结果
St = 0.1645（程序化注入）。

## ④ 结果图
![vort](fig1.png)

## ⑤ 注意点
入口段需足够长。

## ⑥ 误差判定
St 相对文献 0.165 误差 0.30%，<3%。
"""

#: 平台报告只读导出（与 interface-spec §4 同形）
REPORTS = {"900001": {"markdown": REPORT_MD, "figures": [{"name": "fig1.png"}]}}

CARD = {
    "id": "tkc:tensorkbm:lbm-d2q9",
    "card_type": "method",
    "problem": {"description": "圆柱绕流非定常分离"},
    "method": {"name": "LBM D2Q9 BGK", "description": "单松弛格子玻尔兹曼", "family": "LBM"},
    "equations": [{"formula": "f_i(x+c_i dt, t+dt) = f_i - (f_i-f_i^eq)/tau", "source": "Chen & Doolen 1998"}],
    "applicable_domain": {"domain": "incompressible flow", "limitations": ["低 Mach 数"]},
    "created_at": "2026-11-12T00:00:00Z",
    "version": "1.0.0",
}


def _evidence(**over) -> dict:
    ev = {
        "report_id": 900001,
        "section": {"heading": "③ 计算结果"},
        "evidence_type": "simulation",
        "relation": "quantifies",
        "artifact_ref": {"kind": "report_figure", "ref": "fig1.png"},
    }
    ev.update(over)
    return ev


def base_ko(**over) -> dict:
    doc = {
        "schema_version": "ko/v1",
        "knowledge_id": "ko:tensorkbm:lbm-d2q9-strouhal",
        "version": 1,
        "type": "method_card",
        "domain": "tensorkbm",
        "subject": "LBM D2Q9 圆柱绕流",
        "claim": "D2Q9 BGK 在 Re=100 圆柱绕流下给出 St=0.1645，与文献 0.165 相差 0.30%",
        "conditions": {"description": "二维不可压，Re=100，格子 512x256",
                       "assumptions": ["低 Mach 数近似"],
                       "validity_range": {"Re": "50-200"}},
        "evidence": [_evidence()],
        "confidence": {"level": "high", "score": 0.9, "basis": "benchmark_tolerance"},
        "verification_status": "report_claimed",
        "limitations": ["未验证三维效应"],
        "relations": [],
        "next_actions": [{"action": "request_platform_verification", "anchor": "KBM-RCI-S2-SCHEMA"}],
        "provenance": {"producer": "agent/m15858", "producer_role": "agent", "mission_id": 15858,
                       "created_at": "2026-11-12T00:00:00Z", "storage_level": "L1"},
        "payload": copy.deepcopy(CARD),
        "data_references": [],
    }
    doc.update(over)
    return doc


def _mut(fn):
    doc = base_ko()
    fn(doc)
    return doc


MISSING_CLAIM = lambda d: d.pop("claim")                                    # noqa: E731
BAD_ID = lambda d: d.update(knowledge_id="KBM-D2Q9")                        # noqa: E731
BAD_TYPE = lambda d: d.update(type="blog_post")                             # noqa: E731
BAD_STATUS = lambda d: d.update(verification_status="verified")             # noqa: E731
BAD_KIND = lambda d: d["evidence"][0]["artifact_ref"].update(kind="s3_bucket")  # noqa: E731
L2_NO_REL = lambda d: d["provenance"].update(storage_level="L2")            # noqa: E731
NO_CONF_LEVEL = lambda d: d["confidence"].pop("level")                      # noqa: E731
NO_COND_DESC = lambda d: d["conditions"].pop("description")                 # noqa: E731
L3_NO_TICKET = lambda d: (d.update(verification_status="platform_verified"),
                          d["provenance"].update(storage_level="L3"))       # noqa: E731
BAD_CARD = lambda d: d["payload"].update(card_type="mystery")               # noqa: E731


#: (case_id, 期望 accept?, 期望错误串（None=只要被拒即可）, 规格条款, 构造器)
DOC_CASES = [
    ("doc.valid.report_claimed", True, None, "schema-v1 §2 必填 13 键", base_ko),
    ("doc.missing.claim", False, "claim", "schema-v1 §2 claim required", _mut_missing := (lambda: _mut(MISSING_CLAIM))),
    ("doc.bad.knowledge_id", False, "knowledge_id", "schema-v1 §2 knowledge_id pattern", lambda: _mut(BAD_ID)),
    ("doc.bad.type", False, "type", "schema-v1 §2 type 词表", lambda: _mut(BAD_TYPE)),
    ("doc.bad.verification_status", False, "verification_status", "schema-v1 §3 三态", lambda: _mut(BAD_STATUS)),
    ("doc.bad.artifact_kind", False, "artifact_ref", "schema-v1 §4 工件地址类型", lambda: _mut(BAD_KIND)),
    ("doc.l2_without_relations", False, "relations", "schema-v1 §3 L2 需关联边", lambda: _mut(L2_NO_REL)),
    ("doc.confidence_no_level", False, "confidence", "schema-v1 §2 confidence.level", lambda: _mut(NO_CONF_LEVEL)),
    ("doc.conditions_no_description", False, "conditions", "schema-v1 §2 conditions.description", lambda: _mut(NO_COND_DESC)),
    ("doc.l3_without_ticket", False, "verification", "schema-v1 §3 L3 唯一通道=平台验证单", lambda: _mut(L3_NO_TICKET)),
    ("doc.card.payload_invalid", False, "payload", "schema-v1 §2 五类卡 payload 过专属 schema", lambda: _mut(BAD_CARD)),
]


def _transition_case(prev_status: str, doc: dict, actor: str, ticket: dict | None) -> dict:
    return {"prev": {"verification_status": prev_status, "claim": doc.get("claim")},
            "actor_role": actor, "ticket": ticket}


#: (case_id, 期望 accept?, 规格条款, 构造)
TRANS_CASES = [
    ("trans.agent.report_claimed", True, "schema-v1 §3 agent 可把 unverified 升到 report_claimed",
     lambda: _transition_case("unverified", base_ko(), "agent", None)),
    ("trans.agent.to_l3_refused", False, "schema-v1 §3 Agent 不得自宣布 L3（owner 铁则）",
     lambda: _transition_case("report_claimed", _l3_doc(), "agent", _ticket())),
    ("trans.platform.to_l3_ok", True, "schema-v1 §3 平台验证单+confirmed 才可 L3",
     lambda: _transition_case("report_claimed", _l3_doc(), "platform", _ticket())),
    ("trans.skip_to_l3_refused", False, "schema-v1 §3 禁止 unverified→platform_verified 越级",
     lambda: _transition_case("unverified", _l3_doc(), "platform", _ticket())),
    ("trans.reopen_ok", True, "schema-v1 §3 reopen 反向一格",
     lambda: _transition_case("platform_verified", base_ko(verification_status="report_claimed"), "platform", None)),
    ("trans.back_to_unverified_refused", False, "schema-v1 §3 只能反向一格",
     lambda: _transition_case("platform_verified", base_ko(verification_status="unverified"), "platform", None)),
]


def _ticket() -> dict:
    return {"ticket_id": "mv:15858:ko:tensorkbm:lbm-d2q9-strouhal", "source": "maturity_gate",
            "gate_state": "confirmed", "gate_level": 3, "verdict_by": "gate/maturity",
            "verdict_at": "2026-11-12T01:00:00Z", "maturity_verdict_id": 286, "mission_id": 15858}


def _l3_doc() -> dict:
    doc = base_ko()
    doc["verification_status"] = "platform_verified"
    doc["provenance"]["storage_level"] = "L3"
    doc["verification"] = _ticket()
    doc["evidence"][0]["resolution"] = {
        "report_resolved": True, "section_resolved": True, "artifact_resolved": True,
        "resolver_version": "ko-v1/resolver/1.0.0", "resolved_at": "2026-11-12T00:30:00Z"}
    return doc


# ---------------------------------------------------------------- E-TR ref
def etr_cases() -> list[dict]:
    """三条 E-TR 解析语料：ref 为闭式解析值（写在 ref 里，非实测）。"""
    green = _evidence()
    missing_report = _evidence(report_id=999999)
    missing_artifact = _evidence(artifact_ref={"kind": "repo_path", "ref": "does/not/exist.py"})
    doc_only = _evidence(evidence_type="documentation", artifact_ref={"kind": "none", "ref": "none"})
    return [
        {"case_id": "etr.all_green", "evidence": [green],
         "ref": {"e_tr": 1.0, "r1": 1.0, "r2": 1.0, "r3": 1.0},
         "rule": "三闸全绿 → E-TR=1"},
        {"case_id": "etr.mixed_1of3", "evidence": [green, missing_report, missing_artifact],
         "ref": {"e_tr": round(1 / 3, 4), "r1": round(2 / 3, 4), "r2": round(2 / 3, 4), "r3": round(1 / 3, 4)},
         "rule": "报告闸缺→整条不可追溯；工件缺→整条不可追溯"},
        {"case_id": "etr.doc_only_none_artifact", "evidence": [doc_only],
         "ref": {"e_tr": 1.0, "r1": 1.0, "r2": 1.0, "r3": 1.0},
         "rule": "artifact_kind=none 时以小节锚点+切片 sha 代址，视为通过"},
    ]


if __name__ == "__main__":  # 语料自检（无断言，仅打印规模）
    print(json.dumps({"doc_cases": len(DOC_CASES), "trans_cases": len(TRANS_CASES),
                      "etr_cases": len(etr_cases())}, ensure_ascii=False))