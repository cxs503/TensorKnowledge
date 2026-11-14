"""KPI-KB-VERIFY-RATE 的**冻结口径**（改口径 = 改本文件 = 必须版本升级）。

总账锚点：``feature_ledger#164`` ``KPI-KB-VERIFY-RATE``（state=open）
    分子 = L3 候选中「经平台验证单 + gate confirmed 通过」的 KO 数
    分母 = 进入验证流程的 KO 数
    目标 = 由 RCI-F1 试点评估定标（定标前只报现值，不消账）

数据面（只读，两个库）：
  * ``ke_service``  —— KO 权威存储 ``ko_compiler_v1``（DDL: schemas/sql/knowledge_object_v1.sql）
      - ``ko_object``       KO 主体：``storage_level`` / ``verification_status`` / ``producer``
      - ``ko_verification`` L3 唯一验证通道（验证单）：``gate_state`` / ``gate_level``
      - ``ko_evidence``     证据：``artifact_kind`` / ``artifact_resolved``
      - ``ko_state_event``  状态机事件：``to_status``
  * ``tensorplatform`` —— 平台侧交叉核对
      - ``tensor_maturity_verdicts``（gate verdict）
      - ``tensor_benchmark_cases``（机器裁判登记）
      - ``feature_ledger``（锚点原文：验收判据的唯一来源）

冻结原则（本文件即 spec，``spec_sha256`` 随结果落盘）：
  1. 分母主口径 = ``verification_status IN ('report_claimed','platform_verified')``
     —— 即「已进入 v1 状态机验证流程」的 KO；未进入流程的 ``unverified`` 不计。
  2. 分子主口径 = ``storage_level='L3' AND verification_status='platform_verified'
     AND 存在验证单 gate_state='confirmed' AND gate_level>=2``（DDL 约定 gate_level>=2 = confirmed）。
  3. 分母=0 → **未定义（null）**，不写 0（0/0 不是 0%）。
  4. 目标值未定标 → ``target=null`` + ``target_status='NOT_CALIBRATED'``，**禁止编造目标**。
  5. 另报三条灵敏度口径（分母/分子不同解释下的现值），但 headline 只引用主口径。
"""
from __future__ import annotations

import hashlib
import json

SPEC_VERSION = "kpi-kb-verify-rate/spec@1"

ANCHOR = {
    "feature_ledger_id": 164,
    "slug": "KPI-KB-VERIFY-RATE",
    "title": "KPI-KB-VERIFY-RATE",
    "definition": (
        "分子=L3候选中经平台验证单+gate confirmed 通过数，"
        "分母=进入验证流程的KO数；目标值由 RCI-F1 试点评估定标"
    ),
}

# 目标定标来源：RCI-F1 试点评估。未结算 => NOT_CALIBRATED（只报现值）。
TARGET_SOURCE = "docs/rci-f1-abc/REPORT.md（RCI-F1 试点评估，未结算前不定标）"

# 主口径
DENOMINATOR_SCOPE = "ko_compiler_v1.ko_object.verification_status IN ('report_claimed','platform_verified')"
NUMERATOR_SCOPE = (
    "ko_object.storage_level='L3' AND ko_object.verification_status='platform_verified' "
    "AND EXISTS(ko_verification.gate_state='confirmed' AND gate_level>=2)"
)

# ---------------------------------------------------------------------------
# 查询登记表：id -> {db, sql, kind, table, role}
#   kind: "scalar" 单值 | "map" 两列 label,value | "row" 单行多列 | "rows" 多行
#   role: "denominator" | "numerator" | "diagnostic" | "crosscheck" | "meta"
# 全部为单条 SELECT（无 ; 分隔的多语句），由 backend 以只读 GUC 执行。
# ---------------------------------------------------------------------------
QUERIES: dict[str, dict] = {
    # ---------------- 分母侧 ----------------
    "ko_total": dict(
        db="ke_service", table="ko_compiler_v1.ko_object", kind="scalar", role="diagnostic",
        sql="SELECT count(*) FROM ko_compiler_v1.ko_object",
    ),
    "ko_enter_flow": dict(
        db="ke_service", table="ko_compiler_v1.ko_object", kind="scalar", role="denominator",
        sql=("SELECT count(*) FROM ko_compiler_v1.ko_object "
             "WHERE verification_status IN ('report_claimed','platform_verified')"),
    ),
    "ko_enter_flow_events": dict(
        db="ke_service", table="ko_compiler_v1.ko_state_event", kind="scalar", role="diagnostic",
        sql=("SELECT count(DISTINCT knowledge_id) FROM ko_compiler_v1.ko_state_event "
             "WHERE to_status IN ('report_claimed','platform_verified')"),
    ),
    "ko_by_status": dict(
        db="ke_service", table="ko_compiler_v1.ko_object", kind="map", role="diagnostic",
        sql=("SELECT verification_status, count(*) FROM ko_compiler_v1.ko_object "
             "GROUP BY 1 ORDER BY 2 DESC"),
    ),
    "ko_by_level": dict(
        db="ke_service", table="ko_compiler_v1.ko_object", kind="map", role="diagnostic",
        sql=("SELECT storage_level, count(*) FROM ko_compiler_v1.ko_object "
             "GROUP BY 1 ORDER BY 2 DESC"),
    ),
    # ---------------- 分子侧 ----------------
    "ko_l3_candidates": dict(
        db="ke_service", table="ko_compiler_v1.ko_object", kind="scalar", role="diagnostic",
        sql="SELECT count(*) FROM ko_compiler_v1.ko_object WHERE storage_level = 'L3'",
    ),
    "ko_platform_verified": dict(
        db="ke_service", table="ko_compiler_v1.ko_object", kind="scalar", role="diagnostic",
        sql=("SELECT count(*) FROM ko_compiler_v1.ko_object "
             "WHERE verification_status = 'platform_verified'"),
    ),
    "num_l3_gate_confirmed": dict(
        db="ke_service", table="ko_compiler_v1.ko_object+ko_verification", kind="scalar", role="numerator",
        sql=("SELECT count(DISTINCT o.knowledge_id) FROM ko_compiler_v1.ko_object o "
             "JOIN ko_compiler_v1.ko_verification v ON v.knowledge_id = o.knowledge_id "
             "WHERE o.storage_level = 'L3' AND o.verification_status = 'platform_verified' "
             "AND v.gate_state = 'confirmed' AND v.gate_level >= 2"),
    ),
    # ---------------- 验证单通道 ----------------
    "verification_tickets": dict(
        db="ke_service", table="ko_compiler_v1.ko_verification", kind="scalar", role="diagnostic",
        sql="SELECT count(*) FROM ko_compiler_v1.ko_verification",
    ),
    "verification_tickets_confirmed": dict(
        db="ke_service", table="ko_compiler_v1.ko_verification", kind="scalar", role="diagnostic",
        sql="SELECT count(*) FROM ko_compiler_v1.ko_verification WHERE gate_state = 'confirmed'",
    ),
    "verification_ko_distinct": dict(
        db="ke_service", table="ko_compiler_v1.ko_verification", kind="scalar", role="diagnostic",
        sql="SELECT count(DISTINCT knowledge_id) FROM ko_compiler_v1.ko_verification",
    ),
    "num_confirmed_any_level": dict(
        db="ke_service", table="ko_compiler_v1.ko_verification", kind="scalar", role="diagnostic",
        sql=("SELECT count(DISTINCT knowledge_id) FROM ko_compiler_v1.ko_verification "
             "WHERE gate_state = 'confirmed' AND gate_level >= 2"),
    ),
    # ---------------- 证据门 ----------------
    "evidence_total": dict(
        db="ke_service", table="ko_compiler_v1.ko_evidence", kind="scalar", role="diagnostic",
        sql="SELECT count(*) FROM ko_compiler_v1.ko_evidence",
    ),
    "evidence_artifact_none": dict(
        db="ke_service", table="ko_compiler_v1.ko_evidence", kind="scalar", role="diagnostic",
        sql="SELECT count(*) FROM ko_compiler_v1.ko_evidence WHERE artifact_kind = 'none'",
    ),
    "ko_with_artifact_evidence": dict(
        db="ke_service", table="ko_compiler_v1.ko_evidence", kind="scalar", role="diagnostic",
        sql=("SELECT count(DISTINCT knowledge_id) FROM ko_compiler_v1.ko_evidence "
             "WHERE artifact_kind <> 'none'"),
    ),
    "ko_with_verified_artifact": dict(
        db="ke_service", table="ko_compiler_v1.ko_evidence", kind="scalar", role="diagnostic",
        sql=("SELECT count(DISTINCT knowledge_id) FROM ko_compiler_v1.ko_evidence "
             "WHERE artifact_kind <> 'none' AND artifact_resolved IS TRUE"),
    ),
    "evidence_kinds": dict(
        db="ke_service", table="ko_compiler_v1.ko_evidence", kind="map", role="diagnostic",
        sql=("SELECT artifact_kind, count(*) FROM ko_compiler_v1.ko_evidence "
             "GROUP BY 1 ORDER BY 2 DESC"),
    ),
    "ko_state_events": dict(
        db="ke_service", table="ko_compiler_v1.ko_state_event", kind="scalar", role="diagnostic",
        sql="SELECT count(*) FROM ko_compiler_v1.ko_state_event",
    ),
    # ---------------- 分母质量画像 ----------------
    "ko_producer_profile": dict(
        db="ke_service", table="ko_compiler_v1.ko_object", kind="json", role="diagnostic",
        sql=("SELECT json_build_object("
             "'producers', count(DISTINCT producer), "
             "'domains', count(DISTINCT domain), "
             "'n', count(*), "
             "'span_seconds', coalesce(round(extract(epoch FROM (max(created_at) - min(created_at)))::numeric, 1), 0), "
             "'first_at', min(created_at)::text, 'last_at', max(created_at)::text)::text "
             "FROM ko_compiler_v1.ko_object"),
    ),
    # ---------------- 平台侧交叉核对 ----------------
    "verdicts_total": dict(
        db="tensorplatform", table="tensor_maturity_verdicts", kind="scalar", role="crosscheck",
        sql="SELECT count(*) FROM tensor_maturity_verdicts",
    ),
    "verdicts_confirmed": dict(
        db="tensorplatform", table="tensor_maturity_verdicts", kind="scalar", role="crosscheck",
        sql="SELECT count(*) FROM tensor_maturity_verdicts WHERE gate_state = 'confirmed'",
    ),
    "verdicts_ko_scope": dict(
        db="tensorplatform", table="tensor_maturity_verdicts", kind="scalar", role="crosscheck",
        sql="SELECT count(*) FROM tensor_maturity_verdicts WHERE scope LIKE '%ko:%'",
    ),
    "verdicts_knowledge_scope_confirmed": dict(
        db="tensorplatform", table="tensor_maturity_verdicts", kind="scalar", role="crosscheck",
        sql=("SELECT count(*) FROM tensor_maturity_verdicts "
             "WHERE scope LIKE '%knowled%' AND gate_state = 'confirmed'"),
    ),
    "verdict_gate_states": dict(
        db="tensorplatform", table="tensor_maturity_verdicts", kind="map", role="crosscheck",
        sql=("SELECT gate_state, count(*) FROM tensor_maturity_verdicts "
             "GROUP BY 1 ORDER BY 2 DESC"),
    ),
    "benchmark_cases_for_anchor": dict(
        db="tensorplatform", table="tensor_benchmark_cases", kind="scalar", role="crosscheck",
        sql=("SELECT count(*) FROM tensor_benchmark_cases "
             "WHERE anchor_slug = 'KPI-KB-VERIFY-RATE'"),
    ),
    "feature_ledger_anchor": dict(
        db="tensorplatform", table="feature_ledger", kind="rows", role="meta",
        sql=("SELECT id, slug, status, "
             "coalesce(nullif(evidence,''), '(empty)') AS evidence, "
             "coalesce(mission_id::text,'(null)') AS mission_id "
             "FROM feature_ledger WHERE id = 164"),
    ),
}


def spec_dict() -> dict:
    """可哈希（canonical）的 spec 摘要，用于把口径绑到结果上。"""
    return {
        "version": SPEC_VERSION,
        "anchor": ANCHOR,
        "denominator_scope": DENOMINATOR_SCOPE,
        "numerator_scope": NUMERATOR_SCOPE,
        "target_source": TARGET_SOURCE,
        "queries": {k: {"db": v["db"], "sql": v["sql"], "table": v["table"],
                        "kind": v["kind"], "role": v["role"]}
                    for k, v in sorted(QUERIES.items())},
    }


def spec_sha256() -> str:
    blob = json.dumps(spec_dict(), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


SPEC_SHA256 = spec_sha256()