#!/usr/bin/env python3
"""Knowledge Object Schema v1 validator + evidence traceability meter.

锚点 KBM-RCI-S2-SCHEMA。三件事，全部可机器裁：

1. ``validate_document``   —— JSON Schema v1 + 语义附加检查（五类卡 payload、L 级一致性）。
   缺失即错误，不做静默降级。
2. ``check_transition``    —— verification_status 状态机（unverified -> report_claimed ->
   platform_verified，reopen 反向一格）。L3 唯一通道 = 平台验证单（gate_state=confirmed 且
   gate_level>=2）+ 至少一条三闸全绿证据；Agent 角色自宣布 L3 一律拒绝（owner 铁则）。
3. ``evidence_traceability`` —— 证据可追溯率可计算口径：
      单条证据可追溯 := 报告闸 ∧ 小节闸 ∧ 工件闸
      （artifact_kind='none' 时工件闸以“小节锚点 + 切片 sha256”代替地址，视为通过）
      E-TR := 三闸全绿证据条数 / 证据总条数
   同时输出三道单闸通过率（R1/R2/R3），便于定位是“报告丢了”还是“小节锚错了”。

CLI
---
    python scripts/validate_ko_v1.py --doc ko.json
    python scripts/validate_ko_v1.py --doc ko.json --transition-from unverified --actor-role agent
    python scripts/validate_ko_v1.py --doc ko.json --trace --reports reports.json --repo-root .
    python scripts/validate_ko_v1.py --markdown report.md            # 列出可引用小节锚

``--reports`` 形如 ``{"14521": {"markdown": "...", "figures": [{"name": "fig1.png"}]}}``；
该文件可由 TensorPlatform ``tensor_reports`` 只读导出（见 docs/rci/interface-spec.md §4）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
SCHEMAS = REPO / "schemas"
SCHEMA_V1 = SCHEMAS / "knowledge-object-v1.schema.json"

RESOLVER_VERSION = "ko-v1/resolver/1.0.0"

#: 五类卡（在飞 KBM-SCHEMA-W1）→ 专属 schema；payload 必须通过对应 schema。
CARD_SCHEMAS: dict[str, str] = {
    "method_card": "method-card.schema.json",
    "parameter_card": "parameter-card.schema.json",
    "failure_card": "failure-card.schema.json",
    "benchmark_card": "benchmark-card.schema.json",
    "code_pointer_card": "code-pointer-card.schema.json",
}

#: 状态机合法边。其余组合一律非法（含 unverified -> platform_verified 越级）。
TRANSITIONS: set[tuple[str, str]] = {
    ("unverified", "report_claimed"),
    ("report_claimed", "platform_verified"),
    ("platform_verified", "report_claimed"),  # reopen：平台验证单 gate_state=reopened
}

STATUSES = ("unverified", "report_claimed", "platform_verified")

ANCHOR_RE = re.compile(r"^[a-z0-9\u4e00-\u9fff][a-z0-9\u4e00-\u9fff-]*$")
HEADING_RE = re.compile(r"(?m)^(#{1,6})[ \t]+(.+?)[ \t]*$")
#: 中文序号/emoji 等标题前缀噪声，锚点里剥掉（heading 原文永远保留）。
_LEAD_NOISE = re.compile(r"^[\s\u2460-\u24ff\u2776-\u2793#*\-\d.、:：)）]+")


class KOError(Exception):
    """校验失败（结构化原因列表，便于 CI 直读）。"""

    def __init__(self, errors: Sequence[str]):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors))


# --------------------------------------------------------------------- helpers
def canonical_json(doc: Mapping[str, Any]) -> str:
    """排序键、紧凑分隔的规范 JSON（哈希与字节比较的唯一口径）。"""
    return json.dumps(doc, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def content_sha256(doc: Mapping[str, Any]) -> str:
    """对象内容哈希：排除 ``provenance.content_sha256`` 自身（避免自指）。"""
    body = json.loads(json.dumps(doc))
    prov = body.get("provenance")
    if isinstance(prov, dict):
        prov.pop("content_sha256", None)
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def slugify(heading: str) -> str:
    """标题 → 锚点 slug。保留 CJK，去序号/符号，空白折叠为 '-'。"""
    text = _LEAD_NOISE.sub("", heading.strip()).lower()
    text = re.sub(r"[^\w\u4e00-\u9fff]+", "-", text, flags=re.UNICODE)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "section"


def iter_sections(markdown: str) -> list[dict[str, Any]]:
    """切分 markdown 小节：level / heading / anchor / span(start,end) / section_sha256。"""
    heads = [(m.start(), len(m.group(1)), m.group(2).strip()) for m in HEADING_RE.finditer(markdown)]
    out: list[dict[str, Any]] = []
    for i, (start, level, heading) in enumerate(heads):
        end = len(markdown)
        for nstart, nlevel, _ in heads[i + 1:]:
            if nlevel <= level:
                end = nstart
                break
        body = markdown[start:end]
        out.append(
            {
                "level": level,
                "heading": heading,
                "anchor": slugify(heading),
                "span": [start, end],
                "section_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
            }
        )
    return out


def locate_section(markdown: str, section: Mapping[str, Any]) -> dict[str, Any] | None:
    """按 heading 原文定位；heading 不命中则退回 anchor；再退回 span 校验。"""
    sections = iter_sections(markdown)
    want = str(section.get("heading", "")).strip()
    cand = [s for s in sections if s["heading"] == want]
    if not cand and section.get("anchor"):
        cand = [s for s in sections if s["anchor"] == section["anchor"]]
    if not cand:
        return None
    hit = cand[0]
    span = section.get("span")
    if isinstance(span, list) and len(span) == 2:
        # 声明了偏移就必须落在同一段切片上，否则视为漂移
        if [hit["span"][0], hit["span"][1]] != [int(span[0]), int(span[1])]:
            if not (int(span[0]) <= hit["span"][0] < int(span[1])):
                return None
    declared = section.get("section_sha256")
    if declared and declared != hit["section_sha256"]:
        return None
    return hit


# ------------------------------------------------------------------ validation
def _load_schema(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonschema_errors(doc: Mapping[str, Any], schema: Mapping[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover - jsonschema is a test/runtime dep
        raise KOError(["jsonschema is not installed; cannot validate schema v1"])
    validator = jsonschema.Draft202012Validator(schema)
    out: list[str] = []
    for e in sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in e.absolute_path) or "<root>"
        out.append(f"schema: {loc}: {e.message}")
    return out


def validate_document(doc: Mapping[str, Any], *, schema: Mapping[str, Any] | None = None) -> None:
    """Schema v1 + 语义检查。通过返回 None，失败抛 :class:`KOError`（原因全量列出）。"""
    errors = _jsonschema_errors(doc, schema or _load_schema(SCHEMA_V1))

    # 五类卡：payload 必须过专属 schema（词表并入，但不允许只挂名不填正文）
    card = CARD_SCHEMAS.get(str(doc.get("type")))
    if card:
        payload = doc.get("payload")
        if not isinstance(payload, dict):
            errors.append(f"payload: type={doc['type']} requires the card body, got none")
        else:
            card_schema = _load_schema(SCHEMAS / card)
            errors.extend(
                f"payload({card}): {e}" for e in _jsonschema_errors(payload, card_schema)
            )

    # 证据可追溯结构：report_id 与 section 必须同时在场（不得只写“见报告”）
    for i, ev in enumerate(doc.get("evidence") or []):
        if not isinstance(ev, dict):
            continue
        section = ev.get("section") if isinstance(ev.get("section"), dict) else {}
        if not str(section.get("heading") or "").strip():
            errors.append(f"evidence/{i}: section.heading is required to anchor the claim")
        anchor = section.get("anchor")
        if anchor and not ANCHOR_RE.match(str(anchor)):
            errors.append(f"evidence/{i}: section.anchor {anchor!r} is not a valid slug")

    # L 级一致性（schema 已表达，这里给出人话 + 兜住 schema 漏网）
    status = doc.get("verification_status")
    level = (doc.get("provenance") or {}).get("storage_level")
    if status == "platform_verified" and level != "L3":
        errors.append("stage: platform_verified must be storage_level L3")
    if level == "L3" and status != "platform_verified":
        errors.append("stage: storage_level L3 requires verification_status platform_verified")
    if status in ("unverified", "report_claimed") and level == "L3":
        errors.append("stage: unverified/report_claimed cannot claim L3 storage")

    # 内容哈希自洽
    declared = (doc.get("provenance") or {}).get("content_sha256")
    if declared and declared != content_sha256(doc):
        errors.append(
            f"provenance.content_sha256 mismatch: declared {declared[:12]}… "
            f"!= recomputed {content_sha256(doc)[:12]}…"
        )

    if errors:
        raise KOError(errors)


def _ticket_ok(doc: Mapping[str, Any]) -> str | None:
    """返回平台验证单问题描述；None = 合格。"""
    ver = doc.get("verification")
    if not isinstance(ver, dict):
        return "verification ticket missing"
    if ver.get("gate_state") != "confirmed":
        return f"verification.gate_state={ver.get('gate_state')!r} is not 'confirmed'"
    try:
        level = int(ver.get("gate_level"))
    except (TypeError, ValueError):
        return "verification.gate_level missing"
    if level < 2:
        return f"verification.gate_level={level} < 2 (L0/L1 verdict is not a verification)"
    if not str(ver.get("verdict_by") or "").strip():
        return "verification.verdict_by missing (verdicts need an accountable reviewer)"
    return None


def check_transition(
    prev: Mapping[str, Any] | None,
    new: Mapping[str, Any],
    *,
    actor_role: str = "agent",
) -> None:
    """状态机 + L3 通道检查。``prev=None`` 表示新建对象。"""
    errors: list[str] = []
    new_status = str(new.get("verification_status"))
    if new_status not in STATUSES:
        errors.append(f"verification_status {new_status!r} not in {STATUSES}")

    if prev is None:
        prev_status = None
    else:
        prev_status = str(prev.get("verification_status"))
        if prev_status != new_status and (prev_status, new_status) not in TRANSITIONS:
            errors.append(f"illegal transition {prev_status} -> {new_status}")
        if prev_status == "platform_verified" and new_status == "platform_verified":
            if prev.get("claim") != new.get("claim"):
                errors.append("L3 object claim is immutable; publish a new version + supersedes edge")

    if new_status == "platform_verified":
        if actor_role != "platform":
            errors.append(
                "L3 promotion is platform-only: agents cannot self-declare platform_verified"
            )
        problem = _ticket_ok(new)
        if problem:
            errors.append(f"L3 channel: {problem}")
        traceable = [
            ev for ev in (new.get("evidence") or []) if _evidence_is_traceable(ev)
        ]
        if not traceable:
            errors.append(
                "L3 channel: no fully traceable evidence (report+section+artifact gates)"
            )
    elif new_status == "report_claimed":
        if not (new.get("evidence") or []):
            errors.append("report_claimed requires at least one evidence entry")
        if prev_status == "platform_verified" and actor_role != "platform":
            errors.append("demotion from platform_verified is platform-only (reopen ticket)")
        ver = new.get("verification")
        if prev_status == "platform_verified" and isinstance(ver, dict) and ver.get("gate_state") not in (
            None,
            "reopened",
        ):
            errors.append("demotion must be recorded with verification.gate_state='reopened'")

    if errors:
        raise KOError(errors)


# ---------------------------------------------------------------- traceability
def _evidence_is_traceable(ev: Mapping[str, Any]) -> bool:
    res = ev.get("resolution") or {}
    kind = str((ev.get("artifact_ref") or {}).get("kind", "none"))
    artifact_ok = res.get("artifact_resolved")
    if artifact_ok is None:
        artifact_ok = kind == "none"
    return bool(res.get("report_resolved")) and bool(res.get("section_resolved")) and bool(artifact_ok)


def evidence_traceability(evidences: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """可追溯率口径实现：E-TR = 三闸全绿 / 总数，附三道单闸通过率。"""
    rows = [ev for ev in evidences if isinstance(ev, Mapping)]
    total = len(rows)
    report_n = sum(1 for ev in rows if (ev.get("resolution") or {}).get("report_resolved"))
    section_n = sum(1 for ev in rows if (ev.get("resolution") or {}).get("section_resolved"))
    artifact_n = 0
    for ev in rows:
        res = ev.get("resolution") or {}
        kind = str((ev.get("artifact_ref") or {}).get("kind", "none"))
        ok = res.get("artifact_resolved")
        artifact_n += 1 if (ok if ok is not None else kind == "none") else 0
    full_n = sum(1 for ev in rows if _evidence_is_traceable(ev))

    def rate(n: int) -> float | None:
        return None if not total else round(n / total, 4)

    return {
        "evidence_total": total,
        "report_resolved_n": report_n,
        "section_resolved_n": section_n,
        "artifact_resolved_n": artifact_n,
        "fully_traceable_n": full_n,
        "r1_report_resolvable": rate(report_n),
        "r2_section_resolvable": rate(section_n),
        "r3_artifact_resolvable": rate(artifact_n),
        "e_tr": rate(full_n),
        "denominator": total,
    }


def resolve_evidence(
    ev: Mapping[str, Any],
    *,
    reports: Mapping[str, Mapping[str, Any]] | None = None,
    repo_roots: Sequence[Path] | None = None,
    artifact_probe: Callable[[Mapping[str, Any]], bool | None] | None = None,
) -> dict[str, Any]:
    """解析单条证据的三闸，返回带 ``resolution`` 的证据副本（不修改入参）。"""
    out = json.loads(json.dumps(ev))
    report_id = str(out.get("report_id"))
    report = (reports or {}).get(report_id)
    res: dict[str, Any] = {
        "report_resolved": False,
        "section_resolved": False,
        "artifact_resolved": None,
        "resolver_version": RESOLVER_VERSION,
        "resolved_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }

    markdown = None
    figures: list[Mapping[str, Any]] = []
    if isinstance(report, Mapping):
        markdown = report.get("markdown")
        figures = list(report.get("figures") or [])
        res["report_resolved"] = isinstance(markdown, str) and bool(markdown.strip())

    if markdown:
        hit = locate_section(markdown, out.get("section") or {})
        if hit:
            res["section_resolved"] = True
            # 回填规范化锚点与切片哈希（摄取期事实，非人工填）
            out.setdefault("section", {})
            out["section"].setdefault("anchor", hit["anchor"])
            out["section"].setdefault("span", hit["span"])
            out["section"].setdefault("section_sha256", hit["section_sha256"])

    art = out.get("artifact_ref") or {}
    kind = str(art.get("kind", "none"))
    if kind == "none":
        res["artifact_resolved"] = None  # 由口径按“不设址”处理
    elif artifact_probe is not None:
        res["artifact_resolved"] = artifact_probe(art)
    elif kind == "report_figure":
        res["artifact_resolved"] = any(str(f.get("name")) == str(art.get("ref")) for f in figures)
    elif kind == "repo_path":
        rel = str(art.get("ref") or "").lstrip("./")
        res["artifact_resolved"] = any((root / rel).exists() for root in (repo_roots or []))
    elif kind == "tensor_data_artifact":
        res["artifact_resolved"] = bool(art.get("sha256"))  # 本地可核的部分：内容寻址在位
    elif kind == "report_section":
        res["artifact_resolved"] = res["section_resolved"]
    else:  # url / 未识别：离线不可核，诚实置 NULL（不计入分子）
        res["artifact_resolved"] = None

    out["resolution"] = res
    return out


# ------------------------------------------------------------------------ CLI
def _dump(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True))


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Knowledge Object Schema v1 validator / traceability meter")
    ap.add_argument("--doc", help="knowledge object JSON file")
    ap.add_argument("--transition-from", choices=STATUSES, help="previous verification_status")
    ap.add_argument("--actor-role", default="agent", choices=("agent", "human", "platform"))
    ap.add_argument("--trace", action="store_true", help="resolve evidence + print E-TR")
    ap.add_argument("--reports", help='JSON map {"<report_id>": {"markdown": ..., "figures": [...]}}')
    ap.add_argument("--repo-root", action="append", default=[], help="repo root(s) for repo_path refs")
    ap.add_argument("--markdown", help="report markdown file: list citable section anchors")
    args = ap.parse_args(argv)

    if args.markdown:
        sections = iter_sections(Path(args.markdown).read_text(encoding="utf-8"))
        _dump([{k: s[k] for k in ("level", "heading", "anchor", "span", "section_sha256")} for s in sections])
        return 0

    if not args.doc:
        ap.error("--doc is required (or use --markdown)")

    doc = json.loads(Path(args.doc).read_text(encoding="utf-8"))
    try:
        validate_document(doc)
        prev = None
        if args.transition_from:
            prev = {"verification_status": args.transition_from, "claim": doc.get("claim")}
        check_transition(prev, doc, actor_role=args.actor_role)
    except KOError as exc:
        _dump({"ok": False, "errors": exc.errors})
        return 1

    result: dict[str, Any] = {"ok": True, "knowledge_id": doc.get("knowledge_id")}
    if args.trace:
        reports = {}
        if args.reports:
            raw = json.loads(Path(args.reports).read_text(encoding="utf-8"))
            reports = {str(k): v for k, v in raw.items()}
        roots = [Path(p) for p in (args.repo_root or [str(REPO)])]
        resolved = [resolve_evidence(ev, reports=reports, repo_roots=roots) for ev in doc.get("evidence", [])]
        result["traceability"] = evidence_traceability(resolved)
        result["evidence"] = [
            {"report_id": ev.get("report_id"), "section": (ev.get("section") or {}).get("heading"),
             "resolution": ev.get("resolution")}
            for ev in resolved
        ]
    _dump(result)
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())