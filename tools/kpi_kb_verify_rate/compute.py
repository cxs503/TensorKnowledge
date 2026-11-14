"""纯函数算核：把一份 snapshot 变成 KPI 结果。**不连库、不读时钟、不写文件。**

这样同一份 snapshot 在任何机器（含无库节点 / CI）复算都得到同一份 result，
结果的可复算性由函数纯度保证，而不是由「跑过一遍现网」保证。

口径语义（与 spec.py 一致，机器可判）：
  * ``denominator == 0``  -> ``current = None``（未定义，**不是** 0.0）
  * ``0 <= numerator <= denominator``，越界即抛错（防止口径写反）
  * 目标未定标 -> ``target=None`` / ``target_status='NOT_CALIBRATED'`` / ``gap=None``
"""
from __future__ import annotations

import hashlib
import json
import math

from . import spec


class SemanticsError(ValueError):
    """计数关系违反口径（分子>分母、负值等）。"""


# ---------------------------------------------------------------------------
# 基础算术
# ---------------------------------------------------------------------------
def verify_rate(numerator: int, denominator: int) -> float | None:
    """KPI 现值。分母为 0 => None（未定义），绝不返回 0.0。"""
    numerator = int(numerator)
    denominator = int(denominator)
    if numerator < 0 or denominator < 0:
        raise SemanticsError(f"计数不得为负：num={numerator} den={denominator}")
    if numerator > denominator:
        raise SemanticsError(f"分子不得大于分母：num={numerator} den={denominator}")
    if denominator == 0:
        return None
    return numerator / denominator


def wilson_interval(k: int, n: int, z: float = 1.959963984540054) -> dict | None:
    """Wilson 95% 区间；n=0 -> None。分子=0 时上界仍 >0（诚实表达不确定性）。"""
    k, n = int(k), int(n)
    if n <= 0:
        return None
    if k < 0 or k > n:
        raise SemanticsError(f"Wilson 计数越界：k={k} n={n}")
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return {"method": "wilson", "level": 0.95, "low": max(0.0, centre - half),
            "high": min(1.0, centre + half)}


def _fmt(x: float) -> str:
    return f"{x:.4%}"


# ---------------------------------------------------------------------------
# 空心指标：由 snapshot 的原始计数**程序化**推导缺口（不手抄字符串）
# ---------------------------------------------------------------------------
def derive_top_gaps(raw: dict) -> list[dict]:
    """每个缺口都带「推导式」，任何人可以用 snapshot 复算。"""
    gaps: list[dict] = []
    total = int(raw.get("ko_total") or 0)
    tickets = int(raw.get("verification_tickets") or 0)
    confirmed = int(raw.get("verification_tickets_confirmed") or 0)
    with_art = int(raw.get("ko_with_artifact_evidence") or 0)
    l3 = int(raw.get("ko_l3_candidates") or 0)
    ev_total = int(raw.get("evidence_total") or 0)
    ev_none = int(raw.get("evidence_artifact_none") or 0)
    verdicts_ko = int(raw.get("verdicts_ko_scope") or 0)
    bench = int(raw.get("benchmark_cases_for_anchor") or 0)
    prof = raw.get("ko_producer_profile") or {}

    if tickets == 0:
        gaps.append({
            "id": "GAP-KO-VERIFY-TICKET-ZERO",
            "severity": "blocking",
            "finding": "验证单通道零投产：ko_verification 无任何单据，分子在结构上只能是 0",
            "derivation": f"verification_tickets({tickets}) == 0 -> num_l3_gate_confirmed == 0",
            "next_check": "ke/ko_ingest.py:add_ticket() 是否有调用方；有则查为何 0 行",
        })
    if ev_total and with_art == 0:
        gaps.append({
            "id": "GAP-KO-EVIDENCE-ARTIFACT-NONE",
            "severity": "blocking",
            "finding": "证据层全是占位证据：artifact_kind='none' 覆盖全部证据行，gate 无物可确认",
            "derivation": f"evidence_artifact_none({ev_none})/evidence_total({ev_total}) = "
                          f"{ev_none / ev_total:.4%}；ko_with_artifact_evidence={with_art}",
            "next_check": "ko_evidence 的产出侧（compiler）是否只写 none",
        })
    if l3 == 0 and total > 0:
        gaps.append({
            "id": "GAP-KO-L3-POOL-EMPTY",
            "severity": "blocking",
            "finding": "L3 候选池为空：全部 KO 停在 L2，分子定义域本身为空",
            "derivation": f"ko_l3_candidates({l3}) == 0（ko_total={total}）",
            "next_check": "storage_level 提升是否也需要验证单/证据门（同一张单子）",
        })
    producers = int(prof.get("producers") or 0)
    span = float(prof.get("span_seconds") or 0)
    if producers == 1 and total > 0 and span < 600:
        gaps.append({
            "id": "GAP-KO-DENOMINATOR-PROVENANCE",
            "severity": "major",
            "finding": "分母质量存疑：单一 producer 在极短窗口内批量灌入全部 KO，真实性未证",
            "derivation": f"producers({producers})==1 且 span_seconds({span})<600，n={total}",
            "next_check": "抽检 KO 正文/来源，判断是否为占位批量导入",
        })
    if bench == 0:
        gaps.append({
            "id": "GAP-KPI-BENCH-REFEREE",
            "severity": "major",
            "finding": "机器裁判缺位：tensor_benchmark_cases 对本锚点 0 行，KPI 型锚点无 ref-vs-got 基线可判",
            "derivation": f"benchmark_cases_for_anchor({bench}) == 0",
            "next_check": "登记 case：anchor_slug=KPI-KB-VERIFY-RATE, metric=current, tol=双路复算一致",
        })
    if verdicts_ko == 0:
        gaps.append({
            "id": "GAP-PLATFORM-KO-SCOPE-VERDICT",
            "severity": "minor",
            "finding": "平台 gate verdict 无 KO 作用域名，KPI 分子无法从平台侧交叉确认",
            "derivation": f"verdicts_ko_scope({verdicts_ko}) == 0",
            "next_check": "verdict scope 是否需要 ko:<knowledge_id> 形式的确认单",
        })
    if tickets > 0 and confirmed == 0:
        gaps.append({
            "id": "GAP-KO-GATE-NOT-CONFIRMED",
            "severity": "major",
            "finding": "验证单存在但无 gate confirmed（gate_level>=2 未达成）",
            "derivation": f"verification_tickets={tickets}, confirmed={confirmed}",
            "next_check": "查 gate_state 分布与 verdict 关联",
        })
    return gaps


def derive_proposed_anchors(raw: dict, gaps: list[dict]) -> list[dict]:
    """由缺口派生锚点建议（acceptance 里的数字全部来自 snapshot）。"""
    out: list[dict] = []
    gap_ids = {g["id"] for g in gaps}
    tickets = int(raw.get("verification_tickets") or 0)
    total = int(raw.get("ko_total") or 0)
    with_art = int(raw.get("ko_with_artifact_evidence") or 0)
    l3 = int(raw.get("ko_l3_candidates") or 0)
    if "GAP-KO-VERIFY-TICKET-ZERO" in gap_ids:
        out.append({
            "slug": "GAP-KO-VERIFY-TICKET-WIRE",
            "derived_from": f"verification_tickets={tickets}",
            "acceptance": ("ko_verification 出现 >=1 张由真实调用方（非测试夹具）写入的验证单，"
                           "且 ko_state_event 有对应 to_status 流转事件；"
                           "KPI 分子随之可非零"),
            "why_anchor": "分子为 0 的病因是通道未接线，不是 gate 判据太严；修通道才是可验证的下一步",
        })
    if "GAP-KO-EVIDENCE-ARTIFACT-NONE" in gap_ids:
        out.append({
            "slug": "GAP-KO-EVIDENCE-ARTIFACT",
            "derived_from": f"ko_with_artifact_evidence={with_art}/{total}",
            "acceptance": (f"artifact_kind<>'none' 的 KO 数从 {with_art} 提升到 >=1%·ko_total"
                           f"（即 >={max(1, total // 100)} 条）且抽查可解析"),
            "why_anchor": "gate confirmed 需要可解析工件，证据层占位则分子永远为 0",
        })
    if "GAP-KO-L3-POOL-EMPTY" in gap_ids:
        out.append({
            "slug": "GAP-KO-L3-PROMOTION-RULE",
            "derived_from": f"ko_l3_candidates={l3}",
            "acceptance": ("定义并落库 L2->L3 提升判据（验证单 + 工件证据 + gate_level>=2），"
                           "在 >=10 条 KO 上演练通过"),
            "why_anchor": "KPI 定义域为空时，任何分子改进都无法体现",
        })
    out.append({
        "slug": "CASE-KPI-KB-VERIFY-RATE-BENCH",
        "derived_from": f"benchmark_cases_for_anchor={int(raw.get('benchmark_cases_for_anchor') or 0)}",
        "acceptance": ("在 tensor_benchmark_cases 登记 anchor_slug='KPI-KB-VERIFY-RATE'，"
                       "metric='current+denominator'，tolerance='双路(SQL 主路 vs 独立 oracle)复算一致 0 偏差'；"
                       "CI 每次跑 tools/kpi_kb_verify_rate bench 判绿"),
        "why_anchor": "把人工替代判据机器化，否则该 KPI 永远只能靠人看报告",
    })
    return out


# ---------------------------------------------------------------------------
# 快照指纹 / 结果装配
# ---------------------------------------------------------------------------
_FINGERPRINT_DROP = {"collected_at_utc", "collected_at_utc_source", "host",
                     "psql_version", "snapshot_sha256"}


def snapshot_fingerprint(snapshot: dict) -> str:
    """对「值 + SQL 原文 + spec」做 canonical sha256；时间戳与主机名不入指纹。"""
    body = {k: v for k, v in snapshot.items() if k not in _FINGERPRINT_DROP}
    blob = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def sensitivity(raw: dict) -> list[dict]:
    """三条灵敏度口径（同分母不同分子解释 / 同分子不同分母解释）。"""
    total = int(raw.get("ko_total") or 0)
    enter = int(raw.get("ko_enter_flow") or 0)
    tickets_ko = int(raw.get("verification_ko_distinct") or 0)
    strict = int(raw.get("num_l3_gate_confirmed") or 0)
    any_level = int(raw.get("num_confirmed_any_level") or 0)
    confirmed_tickets = int(raw.get("verification_tickets_confirmed") or 0)
    rows = [
        {"scope": "PRIMARY: L3 ∧ platform_verified ∧ confirmed(>=2) / report_claimed∪platform_verified",
         "numerator": strict, "denominator": enter},
        {"scope": "MOLECULE-RELAXED: 任意 storage_level 的 confirmed(>=2) / 同分母",
         "numerator": any_level, "denominator": enter},
        {"scope": "TICKET-ONLY: confirmed 验证单数 / 分母=开过验证单的 KO 数（未开单则未定义）",
         "numerator": confirmed_tickets, "denominator": tickets_ko},
        {"scope": "ALL-KO: 同分子 / ko_total（把未进入流程的 KO 也算分母）",
         "numerator": strict, "denominator": total},
    ]
    for r in rows:
        r["current"] = verify_rate(r["numerator"], r["denominator"])
        r["current_display"] = "未定义(0/0)" if r["current"] is None else _fmt(r["current"])
    return rows


def build_result(snapshot: dict) -> dict:
    """snapshot -> result JSON（总账要求的 current/unit/target/gap/data_sources/top_gaps/proposed_anchors）。"""
    if snapshot.get("spec_sha256") not in (None, spec.SPEC_SHA256):
        raise SemanticsError(
            "snapshot 的口径与当前 spec 不一致："
            f"{snapshot.get('spec_sha256')} != {spec.SPEC_SHA256}（口径改了必须重采）")
    raw = snapshot["raw"]
    numerator = int(raw.get("num_l3_gate_confirmed") or 0)
    denominator = int(raw.get("ko_enter_flow") or 0)
    current = verify_rate(numerator, denominator)
    gaps = derive_top_gaps(raw)

    data_sources = []
    for qid, q in sorted(spec.QUERIES.items()):
        data_sources.append({
            "id": qid, "db": q["db"], "table": q["table"], "role": q["role"],
            "sql": q["sql"],
            "value": raw.get(qid),
        })

    return {
        "anchor": spec.ANCHOR,
        "kpi": "KPI-KB-VERIFY-RATE",
        "spec_version": spec.SPEC_VERSION,
        "spec_sha256": spec.SPEC_SHA256,
        "snapshot_sha256": snapshot.get("snapshot_sha256") or snapshot_fingerprint(snapshot),
        "collected_at_utc": snapshot.get("collected_at_utc"),
        "current": current,
        "current_display": "未定义(0/0)" if current is None else _fmt(current),
        "unit": "ratio (verified L3 KO / KO entering verification flow)",
        "numerator": numerator,
        "denominator": denominator,
        "denominator_scope": spec.DENOMINATOR_SCOPE,
        "numerator_scope": spec.NUMERATOR_SCOPE,
        "confidence_interval": wilson_interval(numerator, denominator),
        "target": None,
        "target_status": "NOT_CALIBRATED",
        "target_source": spec.TARGET_SOURCE,
        "gap": None,
        "gap_reason": ("目标值未定标（RCI-F1 试点未结算）：按总账口径只报现值、不消账，"
                       "不编造目标也不把 gap 写成 0"),
        "sensitivity": sensitivity(raw),
        "data_sources": data_sources,
        "top_gaps": gaps,
        "proposed_anchors": derive_proposed_anchors(raw, gaps),
        "repro_cmd": [
            "python -m tools.kpi_kb_verify_rate collect --out runs/kpi_kb_verify_rate",
            "python -m tools.kpi_kb_verify_rate measure --snapshot runs/kpi_kb_verify_rate/snapshot.json --out runs/kpi_kb_verify_rate",
            "python -m tools.kpi_kb_verify_rate verify --snapshot runs/kpi_kb_verify_rate/snapshot.json",
            "python -m tools.kpi_kb_verify_rate bench --out benchmarks/kpi_kb_verify_rate",
            "python -m pytest tests/test_kpi_kb_verify_rate.py -q",
        ],
    }


def result_fingerprint(result: dict) -> str:
    """结果的指纹：用于 verify 判「同一 snapshot 是否得到同一 result」。"""
    body = {k: v for k, v in result.items() if k not in {"collected_at_utc"}}
    blob = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()