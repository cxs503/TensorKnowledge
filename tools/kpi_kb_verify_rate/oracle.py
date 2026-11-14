"""独立第二代码路径（oracle）：**换个写法**重算同一个 KPI，用来判主路是否算错。

刻意与 ``spec.QUERIES`` 主路不同：
  * 分母：主路数 ``ko_object.verification_status``；oracle 走 **状态机事件表**
    ``ko_state_event.to_status`` 的 distinct knowledge_id（另一张表、另一种语义来源）。
  * 分子：主路从 ``ko_object`` 出发 JOIN 验证单；oracle 从 ``ko_verification`` 出发用
    ``EXISTS`` 半连接回 ``ko_object``，并且**返回 id 集合**而不是只返回计数。
  * 判定：不只是计数相等，还比 **集合相等**（同 id 集合），避免"两个错数刚好相等"。

在活库上跑（需要 psql 可达）；离线/CI 上不可用时返回 ``None`` 并由调用方标 ``not_run``。
"""
from __future__ import annotations

from .backend import BackendUnavailable, PsqlBackend

DENOMINATOR_SQL = (
    "SELECT DISTINCT knowledge_id FROM ko_compiler_v1.ko_state_event "
    "WHERE to_status IN ('report_claimed','platform_verified')"
)

NUMERATOR_IDS_SQL = (
    "SELECT v.knowledge_id FROM ko_compiler_v1.ko_verification v "
    "WHERE v.gate_state = 'confirmed' AND v.gate_level >= 2 "
    "AND EXISTS (SELECT 1 FROM ko_compiler_v1.ko_object o "
    "WHERE o.knowledge_id = v.knowledge_id AND o.storage_level = 'L3' "
    "AND o.verification_status = 'platform_verified')"
)

PRIMARY_DENOMINATOR_IDS_SQL = (
    "SELECT knowledge_id FROM ko_compiler_v1.ko_object "
    "WHERE verification_status IN ('report_claimed','platform_verified')"
)


def oracle_counts(user: str | None = None, max_ids: int = 200000) -> dict | None:
    """返回 {numerator, denominator, numerator_ids, denominator_ids, set_equal_*}。"""
    be = PsqlBackend("ke_service", user=user)
    try:
        num_ids = sorted(r[0] for r in be.rows(NUMERATOR_IDS_SQL) if r and r[0])
        den_ids = sorted(r[0] for r in be.rows(DENOMINATOR_SQL) if r and r[0])
        primary_den_ids = sorted(r[0] for r in be.rows(PRIMARY_DENOMINATOR_IDS_SQL) if r and r[0])
    except BackendUnavailable:
        return None
    if len(num_ids) > max_ids or len(den_ids) > max_ids:
        return {"error": f"id 集合超过 {max_ids}，拒绝在内存里比集合相等"}
    return {
        "numerator": len(num_ids),
        "denominator": len(den_ids),
        "numerator_ids": num_ids,
        "denominator_ids_equal_primary": set(den_ids) == set(primary_den_ids),
        "denominator_distinct_primary": len(primary_den_ids),
        "numerator_ids_sample": num_ids[:10],
    }