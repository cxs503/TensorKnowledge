#!/usr/bin/env python3
"""RCI 阶段 2b：200 对象试点（真实语料 → ko/v1 映射）与 Schema v1.1 修订证据。

锚点 **KBM-RCI-S2B-PILOT**。三件事，全部机器可裁、可复现（种子固定、零手抄数字）：

1. ``build_frame`` —— 抽样框：仓内真实语料的去重 claim 全集，按 (facet × claim_type) 分层。
2. ``sample``     —— 确定性抽样：每层保底 ``MIN_PER_STRATUM``，余量按层规模比例，
                     层内按 ``sha256(f"{SEED}:{claim_id}")`` 排序取前 n（同输入 → 同 200 条）。
3. ``measure``    —— 三套口径同时给出：
       · strict v1       现状 Schema 直接验（预期大面积失败，失败按修订条款归类）
       · projected v1.1  按 ``docs/rci-s2b-schema-revisions.md`` 的 R1/R2/R4 在内存里打补丁后验证
       · RQS             公开权重的诊断合成分（五维，逐维均值也输出，读结论不必依赖权重）

产物：
    docs/rci-s2b-pilot200/metrics.json          全部数字（报告表格由此渲染，禁止手抄）
    docs/rci-s2b-pilot200/full_frame_rates.json 全样本精确率（§6 误差基准，--full-frame）
    docs/rci-s2b-pilot200/sample_manifest.json  200 条样本清单（id/层/权重/order_key）
    docs/rci-s2b-pilot200/{report-tables,error-table}.md 报告数字块（报告内嵌同一份）
    docs/assets/rci/ko_quality_by_type.png
    docs/assets/rci/review_field_accuracy.png
    docs/assets/rci/rqs_distribution.png

用法：
    python3 scripts/rci_s2b_pilot.py                  # 抽样 → 度量 → 出图 → 写工件
    python3 scripts/rci_s2b_pilot.py --no-figures
    python3 scripts/rci_s2b_pilot.py --render-tables  # 只把报告表格块打印到 stdout

纪律：本脚本**不改** ``schemas/`` 的权威 Schema，也不改 ``scripts/validate_ko_v1.py``；
v1.1 修订以「内存投影」形式度量（可回滚、可对照），落地留给评审。
"""
from __future__ import annotations

import argparse
import copy
import glob
import hashlib
import importlib.util
import json
import math
import re
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO = Path(__file__).resolve().parents[1]
OUT_ART = REPO / "docs" / "rci-s2b-pilot200"  # 不放 artifacts/：推送门禁会丢弃 artifacts/**
OUT_FIG = REPO / "docs" / "assets" / "rci"

ANCHOR = "KBM-RCI-S2B-PILOT"
PILOT_N = 200
MIN_PER_STRATUM = 3
SEED = 20261113  # 固定种子：层内顺序 = sha256(f"{SEED}:{id}")，只作记录与审计
SAMPLE_VERSION = "rci-s2b/sample/1.0.0"
METRIC_VERSION = "rci-s2b/metrics/1.0.0"

#: 语料面（facet → claim 文件 glob）。只收仓内已存在的真实语料。
CORPORA: dict[str, str] = {
    "kb10k": "knowledge/kb10k/claims/part-*.json",
    "oss-lbm": "knowledge/oss-lbm/claims/*.json",
    "sediment": "knowledge/sediment/**/claims/*.json",
    "kbm-demo": "knowledge/kbm/demo-sample/extract/claims/*.json",
}
#: 对应 evidence glob（按 id 建索引，用于证据可追溯与 review 字段派生）。
EVIDENCE_GLOBS: dict[str, str] = {
    "kb10k": "knowledge/kb10k/evidence/part-*.json",
    "oss-lbm": "knowledge/oss-lbm/evidence/*.json",
    "sediment": "knowledge/sediment/**/evidence/*.json",
    "kbm-demo": "knowledge/kbm/demo-sample/extract/evidence/*.json",
}

#: 源词表 → v1 type。``None`` = 无诚实映射（不硬凑，计入 unmapped 并进修订清单）。
SOURCE_TYPE_MAP: dict[str, str | None] = {
    "definition": "definition",
    "descriptive": "capability_claim",
    "methodological": "method_card",
    "mathematical": "method_card",
    "predictive": "benchmark_card",
    "interpretive": None,
    "hypothesis": None,
}
#: 有 payload 必填的卡类 v1 type（payload 缺失即 schema 失败，单列一类原因）。
CARD_TYPES = {
    "method_card",
    "parameter_card",
    "failure_card",
    "benchmark_card",
    "code_pointer_card",
}

#: epistemic_status → confidence.level（派生规则，逐条可审计）。
LEVEL_MAP = {
    "established": "medium",
    "supported": "medium",
    "provisional": "low",
    "draft": "low",
    "unassessed": "low",
    "unknown": "low",
}
#: evidence locator_type → v1.0 confidence.basis。v1.0 词表缺 code/dataset 档 → 派生失败。
BASIS_MAP_V10 = {
    "analytic-derivation": "analytic_reference",
    "experimental-data": "experimental_reference",
    "benchmark-run": "benchmark_tolerance",
    "literature-quote": "literature",
}
#: R2 拟新增词：代码位置/数据集位置（现网语料 100% 是这两类）。
BASIS_MAP_V11 = {**BASIS_MAP_V10, "code-location": "code_inspection", "dataset": "dataset_locator"}

#: RQS 公开权重（诊断合成分；逐维均值同时输出，读结论不必依赖权重）。
RQS_WEIGHTS = {
    "schema_conformance": 0.30,
    "evidence_traceability": 0.25,
    "field_completeness": 0.20,
    "review_derivability": 0.15,
    "id_stability": 0.10,
}
V1_REQUIRED_FIELDS = (
    "schema_version",
    "knowledge_id",
    "type",
    "domain",
    "subject",
    "claim",
    "conditions",
    "evidence",
    "confidence",
    "verification_status",
    "limitations",
    "provenance",
    "version",
)
REVIEW_FIELDS = (
    "confidence.level",
    "confidence.basis",
    "verification_status",
    "limitations",
    "provenance.storage_level",
)

_ID_BAD = re.compile(r"[^a-z0-9._-]+")
_ANCHOR_BAD = re.compile(r"[^a-z0-9\u4e00-\u9fff-]+")


# --------------------------------------------------------------------- loading
def _load_validator():
    """按路径装载权威校验器（不复制其逻辑，避免第二真相源）。"""
    path = REPO / "scripts" / "validate_ko_v1.py"
    spec = importlib.util.spec_from_file_location("validate_ko_v1", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _iter_records(pattern: str) -> Iterable[dict[str, Any]]:
    for path in sorted(glob.glob(str(REPO / pattern), recursive=True)):
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict):
            rows = data.get("claims") or data.get("evidence") or [data]
        else:
            continue
        for row in rows:
            if isinstance(row, dict):
                yield row


def build_frame() -> dict[str, Any]:
    """去重后的 claim 全集 + evidence 索引（同 id 只取首次出现，顺序确定）。"""
    claims: dict[str, dict[str, Any]] = {}
    claim_facet: dict[str, str] = {}
    for facet, pattern in CORPORA.items():
        for row in _iter_records(pattern):
            cid = str(row.get("id") or "")
            if not cid or "statement" not in row or cid in claims:
                continue
            claims[cid] = row
            claim_facet[cid] = facet
    evidence: dict[str, dict[str, Any]] = {}
    for _facet, pattern in EVIDENCE_GLOBS.items():
        for row in _iter_records(pattern):
            eid = str(row.get("id") or "")
            if eid and eid not in evidence:
                evidence[eid] = row
    strata: dict[tuple[str, str], list[str]] = {}
    for cid, row in claims.items():
        strata.setdefault((claim_facet[cid], str(row.get("claim_type") or "missing")), []).append(cid)
    return {"claims": claims, "facet": claim_facet, "evidence": evidence, "strata": strata}


def _key(cid: str) -> str:
    return hashlib.sha256(f"{SEED}:{cid}".encode("utf-8")).hexdigest()


def sample(frame: Mapping[str, Any], n: int = PILOT_N, minimum: int = MIN_PER_STRATUM) -> dict[str, Any]:
    """分层抽样：每层保底 ``minimum``（不足则全取），余量按层规模比例（最大余数法）。

    确定性：层内顺序 = ``sha256(f"{SEED}:{claim_id}")``，同输入必得同一样本。
    """
    strata: dict[tuple[str, str], list[str]] = frame["strata"]
    total = sum(len(v) for v in strata.values())
    keys = sorted(strata)
    picked: dict[tuple[str, str], int] = {k: 0 for k in keys}
    budget = n
    for k in keys:  # 第一轮：保底
        take = min(minimum, len(strata[k]), budget)
        picked[k] = take
        budget -= take
    if budget > 0:  # 第二轮：按剩余层规模比例（最大余数法，平局按层名定序）
        remaining = {k: len(strata[k]) - picked[k] for k in keys}
        pool = sum(remaining.values())
        if pool:
            quotas = {k: budget * remaining[k] / pool for k in keys}
            for k in keys:
                extra = min(int(math.floor(quotas[k])), remaining[k])
                picked[k] += extra
                budget -= extra
            for k in sorted(keys, key=lambda k: (-(quotas[k] - math.floor(quotas[k])), k)):
                if budget <= 0:
                    break
                if picked[k] < len(strata[k]):
                    picked[k] += 1
                    budget -= 1
    rows = []
    for k in keys:
        ids = sorted(strata[k], key=_key)
        take = picked[k]
        for cid in ids[:take]:
            rows.append(
                {
                    "claim_id": cid,
                    "facet": k[0],
                    "source_claim_type": k[1],
                    "stratum_size": len(strata[k]),
                    "weight": round(len(strata[k]) / take, 6) if take else 0.0,
                    "order_key": _key(cid),
                }
            )
    rows.sort(key=lambda r: (r["facet"], r["source_claim_type"], r["order_key"]))
    return {
        "n": len(rows),
        "population": total,
        "seed": SEED,
        "sample_version": SAMPLE_VERSION,
        "rows": rows,
    }


# --------------------------------------------------------------------- mapping
def _slug(text: str) -> str:
    out = _ID_BAD.sub("-", str(text).strip().lower())
    out = re.sub(r"-{2,}", "-", out).strip("-")
    return out or "x"


def _anchor(text: str) -> str:
    """section.anchor：只留 [a-z0-9 CJK -]，与 schema 的 ANCHOR_RE 对齐。"""
    out = _ANCHOR_BAD.sub("-", str(text).strip().lower())
    out = re.sub(r"-{2,}", "-", out).strip("-")
    return out or "locator"


def to_knowledge_id(claim_id: str, facet: str) -> str:
    """``tkc:<facet>:<slug>`` → ``ko:<facet>:<slug>``（保 facet 语义，slug 只做字符规范化）。"""
    body = claim_id.split(":", 2)[2] if claim_id.count(":") >= 2 else claim_id
    return f"ko:{_slug(facet)}:{_slug(body)}"


def _evidence_type(locator_type: Any) -> str:
    mapping = {
        "code-location": "code",
        "dataset": "dataset",
        "analytic-derivation": "analytic",
        "experimental-data": "measurement",
        "benchmark-run": "test",
        "literature-quote": "literature",
    }
    return mapping.get(str(locator_type or ""), "documentation")


def _hex64(value: Any) -> str:
    """规整 ``sha256:<hex>`` / ``<hex>`` → 64 位 hex；不合规返回空串（不伪造）。"""
    text = str(value or "").strip().lower()
    if text.startswith("sha256:"):
        text = text[len("sha256:"):]
    return text if re.fullmatch(r"[0-9a-f]{64}", text) else ""


def _artifact_ref(
    citation: str, persistent: str, digest: str, locator: Mapping[str, Any]
) -> dict[str, Any]:
    """源证据 → v1 ArtifactRef。仓内路径可解析则 repo_path；仅有 git 钉扎则 repo_path+repo/commit；否则 none。

    ``sha256`` 只在 ``content_hash`` 是 64 位 hex 时填（否则置 null，不伪造哈希）。
    """
    ref = citation if citation and (REPO / citation).exists() else ""
    out: dict[str, Any] = {"kind": "repo_path" if (ref or persistent.startswith("git:")) else "none"}
    if persistent.startswith("git:") and "@" in persistent:
        repo_part, _, commit = persistent[3:].partition("@")
        out.update({"ref": ref or persistent, "repo": repo_part or "unknown", "commit": commit[:40]})
    else:
        out["ref"] = ref or str(locator.get("value") or "unreferenced")
    out["sha256"] = _hex64(digest) or None
    return out


def _evidence_entries(
    claim: Mapping[str, Any], frame: Mapping[str, Any], *, projected: bool = False
) -> tuple[list[dict[str, Any]], list[str]]:
    """源 claim 的 evidence_refs → v1 EvidenceRef（不臆造 report_id）。"""
    out: list[dict[str, Any]] = []
    unresolved: list[str] = []
    for ref in claim.get("evidence_refs") or []:
        rec = frame["evidence"].get(str(ref))
        if not rec:
            unresolved.append(str(ref))
            continue
        locator = rec.get("locator") or {}
        source = rec.get("source") or {}
        citation = str(source.get("citation") or "")
        persistent = str(source.get("persistent_id") or "")
        digest = str(locator.get("content_hash") or "")
        entry: dict[str, Any] = {
            "evidence_id": "ev:" + hashlib.sha256(str(ref).encode("utf-8")).hexdigest()[:16],
            "evidence_type": _evidence_type(locator.get("locator_type")),
            "relation": rec.get("relation")
            if rec.get("relation") in {"supports", "refutes", "quantifies", "limits", "reproduces"}
            else "supports",
            "artifact_ref": _artifact_ref(citation, persistent, digest, locator),
            "section": {
                "heading": str(locator.get("value") or citation or ""),
                "anchor": _anchor(str(locator.get("value") or "locator")),
            },
            "locator": {
                "locator_kind": str(locator.get("locator_type") or "unknown"),
                "value": str(locator.get("value") or ""),
                "content_sha256": _hex64(locator.get("content_hash"))
                or (
                    # R5：外部源无文件级哈希时，摄取期对引文切片自算哈希（钉引用而非钉文件）
                    hashlib.sha256(" ".join(str(locator.get("quote") or "").split()).encode("utf-8")).hexdigest()
                    if projected and len(str(locator.get("quote") or "").strip()) >= 15
                    else ""
                ),
                "content_sha256_kind": "source_file"
                if _hex64(locator.get("content_hash"))
                else (
                    "quote_span"
                    if projected and len(str(locator.get("quote") or "").strip()) >= 15
                    else "none"
                ),
                "quote": str(locator.get("quote") or "")[:280],
                "citation": str(source.get("citation") or ""),
                "persistent_id": str(source.get("persistent_id") or ""),
            },
            "source_evidence_ref": str(ref),
        }
        out.append(entry)
    return out, unresolved


def _payload(claim: Mapping[str, Any], v1_type: str | None) -> dict[str, Any] | None:
    """卡类 payload：只从源记录已有字段搬运（无源字段就不合成，宁可失败也不编造）。"""
    if v1_type not in CARD_TYPES:
        return None
    method = claim.get("method") if isinstance(claim.get("method"), dict) else None
    if v1_type == "method_card" and method:
        return {
            "name": str(method.get("name") or claim.get("id")),
            "description": str(method.get("description") or claim.get("statement") or ""),
            "equations": [
                str(e.get("formula") if isinstance(e, dict) else e) for e in claim.get("equations") or []
            ],
            "applicable_domain": str((claim.get("scope") or {}).get("domain") or "unspecified"),
        }
    if v1_type == "benchmark_card":
        case = claim.get("benchmark_case") if isinstance(claim.get("benchmark_case"), dict) else None
        if case:
            return {
                "case": str(case.get("name") or case.get("id") or claim.get("id")),
                "reference_value": case.get("reference_value"),
                "tolerance": case.get("tolerance"),
                "source": str(case.get("source") or ""),
            }
    return None


def map_claim(
    claim: Mapping[str, Any], row: Mapping[str, Any], frame: Mapping[str, Any], *, projected: bool
) -> dict[str, Any]:
    """单条源 claim → ko/v1 文档 + 派生审计（哪些 review 字段可派生 / 为何不可）。"""
    v1_type = SOURCE_TYPE_MAP.get(row["source_claim_type"])
    evidence, unresolved = _evidence_entries(claim, frame, projected=projected)
    scope = claim.get("scope") or {}
    conditions = scope.get("conditions") or []
    epistemic = str(claim.get("epistemic_status") or "unknown")
    level = LEVEL_MAP.get(epistemic, "low")
    basis_map = BASIS_MAP_V11 if projected else BASIS_MAP_V10
    basis_candidates = {basis_map.get(ev["locator"]["locator_kind"]) for ev in evidence}
    basis_candidates.discard(None)
    basis = sorted(basis_candidates)[0] if basis_candidates else "unassessed"
    limitations = [f"source epistemic_status={epistemic}; no platform gate verdict in source corpus"]
    if unresolved:
        limitations.append(f"{len(unresolved)} evidence_ref(s) unresolved in repo corpus")
    refs = claim.get("evidence_refs") or []
    if refs and all(
        str((frame["evidence"].get(str(r)) or {}).get("assessment_status") or "") == "unassessed" for r in refs
    ):
        limitations.append("all evidence assessment_status=unassessed (not reviewed)")
    payload = _payload(claim, v1_type)
    subject = str(scope.get("system") or (str(claim.get("id")).split(":")[1] if claim.get("id") else row["facet"]))
    doc: dict[str, Any] = {
        "schema_version": "ko/v1",
        "knowledge_id": to_knowledge_id(str(claim["id"]), row["facet"]),
        "version": 1,
        "type": v1_type or "definition",  # 无映射时挂 definition，仅为让 schema 报出真正原因
        "domain": str(scope.get("domain") or row["facet"]),
        "subject": subject,
        "claim": str(claim.get("statement") or "").strip(),
        "conditions": {
            "description": "; ".join(str(c) for c in conditions) or str(scope.get("domain") or row["facet"]),
            **({"assumptions": [str(c) for c in conditions]} if conditions else {}),
        },
        "evidence": evidence,
        "confidence": {
            "level": level,
            "score": {"high": 0.8, "medium": 0.6, "low": 0.3}[level],
            "basis": basis,
            "note": f"derived from epistemic_status={epistemic}; basis from evidence locator kind",
        },
        "verification_status": "unverified",  # 无平台验证单 → 不许自晋级
        "limitations": limitations,
        "provenance": {
            "producer": str(claim.get("created_by") or "unknown"),
            "producer_role": "agent",
            "mission_id": None,
            "node_id": None,
            "created_at": str(claim.get("created_at") or "1970-01-01T00:00:00Z"),
            "pipeline": f"rci-s2b-pilot/{SAMPLE_VERSION}",
            "generator_version": METRIC_VERSION,
            "derived_from": [str(claim["id"])],
            "storage_level": "L1",
        },
    }
    if payload is not None:
        doc["payload"] = payload
    audit = {
        "source_claim_type": row["source_claim_type"],
        "type_mapped": v1_type is not None,
        "unresolved_evidence": unresolved,
        "payload_present": payload is not None,
        "basis_candidates": sorted(basis_candidates),
        "review": {
            "confidence.level": {"derivable": epistemic in LEVEL_MAP, "value": level},
            "confidence.basis": {
                "derivable": bool(basis_candidates),
                "value": basis,
                "reason": None
                if basis_candidates
                else "v1.0 basis enum has no slot for the locator kinds present",
            },
            "verification_status": {"derivable": True, "value": "unverified"},
            "limitations": {"derivable": True, "value": limitations},
            "provenance.storage_level": {"derivable": True, "value": "L1"},
        },
    }
    return {"doc": doc, "audit": audit}


# --------------------------------------------------------------------- validators
def projected_schema(v1: Mapping[str, Any]) -> dict[str, Any]:
    """v1.1 内存投影（R1 证据定位符 / R2 basis 词表）。权威文件不动。"""
    schema = copy.deepcopy(v1)
    ev = schema["$defs"]["EvidenceRef"]
    ev["properties"]["locator"] = {
        "type": "object",
        "description": "R1: 非报告证据的定位符（code/dataset/analytic），与 report_id 二选一。",
        "properties": {
            "locator_kind": {"type": "string", "minLength": 1},
            "value": {"type": "string", "minLength": 1},
            "content_sha256": {"type": "string"},
            "quote": {"type": "string"},
            "citation": {"type": "string"},
            "persistent_id": {"type": "string"},
        },
        "required": ["locator_kind", "value"],
    }
    ev["properties"]["source_evidence_ref"] = {"type": "string"}
    ev["required"] = ["evidence_type", "artifact_ref"]
    ev["anyOf"] = [{"required": ["report_id"]}, {"required": ["locator"]}]
    ev["properties"]["report_id"] = {"type": ["integer", "null"], "minimum": 1}
    basis = schema["properties"]["confidence"]["properties"]["basis"]["enum"]
    for extra in ("code_inspection", "dataset_locator"):
        if extra not in basis:
            basis.append(extra)
    return schema


def validate_strict(doc: Mapping[str, Any], validator) -> list[str]:
    try:
        validator.validate_document(doc)
        return []
    except validator.KOError as exc:
        return list(exc.errors)


def validate_projected(doc: Mapping[str, Any], schema: Mapping[str, Any], validator) -> list[str]:
    errors = list(validator._jsonschema_errors(doc, schema))
    # R4：非报告证据用 locator 定位；报告证据仍要 section.heading（不放松报告侧）
    for i, ev in enumerate(doc.get("evidence") or []):
        if not isinstance(ev, dict):
            continue
        has_report = isinstance(ev.get("report_id"), int)
        locator = ev.get("locator") if isinstance(ev.get("locator"), dict) else None
        if has_report:
            if not str(((ev.get("section") or {}).get("heading")) or "").strip():
                errors.append(f"evidence/{i}: pattern 'evidence/.*section' report evidence requires heading")
        elif locator:
            if not str(locator.get("value") or "").strip():
                errors.append(f"evidence/{i}: locator.value is required")
            if not str(locator.get("content_sha256") or "").strip():
                errors.append(f"evidence/{i}: locator needs content_sha256 (content-addressed proof)")
        else:
            errors.append(f"evidence/{i}: report_id missing and locator missing")
    if doc.get("verification_status") == "platform_verified":
        errors.append("verification_status platform_verified: L3 channel not relaxed by projection")
    if doc.get("verification_status") == "report_claimed":
        if not any(isinstance(ev.get("report_id"), int) for ev in doc.get("evidence") or []):
            errors.append("report_id missing: report_claimed requires >=1 report-linked evidence")
    return errors


def categorize(errors: Sequence[str]) -> list[str]:
    """错误 → 修订条款归类（R1 证据定位符 / R2 basis 词表 / payload / field / status / other）。"""
    cats = set()
    for err in errors:
        if err.startswith("R3:"):
            cats.add("R3_type_bridge")
        elif "basis" in err:
            cats.add("R2_basis_vocabulary")
        elif "report_id" in err or "section" in err or err.startswith(("schema: evidence", "evidence/")):
            cats.add("R1_evidence_locator")
        elif "payload" in err:
            cats.add("payload_card_body")
        elif err.startswith(("knowledge_id", "type", "domain", "subject", "claim", "conditions", "evidence")):
            cats.add("field_contract")
        elif "verification" in err or "storage_level" in err or err.startswith("stage:"):
            cats.add("status_machine")
        else:
            cats.add("other")
    return sorted(cats)


# --------------------------------------------------------------------- metrics
def _review_accuracy(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """review 字段口径：可派生 ∧ 与独立不变量一致 → 记为准确（conflict 单列）。"""
    out = []
    for field in REVIEW_FIELDS:
        derivable = consistent = conflicts = derivable_v10 = 0
        for it in items:
            audit = it["audit"]["review"][field]
            doc = it["doc"]
            ok = bool(audit["derivable"])
            derivable += int(ok)
            consistent += int(ok)
            derivable_v10 += int(bool(it["audit_strict"]["review"][field]["derivable"]))
            conflict = False
            if field == "confidence.level":
                if doc["confidence"]["level"] == "high" and not it.get("_reviewed_evidence"):
                    conflict = True
            elif field == "confidence.basis":
                if doc["confidence"]["basis"] != "unassessed" and not all(
                    bool((ev.get("locator") or {}).get("value")) for ev in doc["evidence"]
                ):
                    conflict = True
            elif field == "verification_status":
                if doc["verification_status"] == "platform_verified" and not doc.get("verification"):
                    conflict = True
            elif field == "limitations":
                if not doc["limitations"]:
                    conflict = True
            elif field == "provenance.storage_level":
                if doc["provenance"]["storage_level"] == "L3" and doc["verification_status"] != "platform_verified":
                    conflict = True
            if conflict:
                conflicts += 1
                consistent -= 1
        n = len(items)
        out.append(
            {
                "field": field,
                "n": n,
                "derivable_v10": derivable_v10,
                "derivable_v10_rate": _rate(derivable_v10, n),
                "derivable": derivable,
                "derivable_rate": _rate(derivable, n),
                "invariant_consistent": consistent,
                "accuracy": _rate(consistent, n),
                "conflicts": conflicts,
            }
        )
    return out


def _rqs(
    doc: Mapping[str, Any], *, projected_ok: bool, trace_rate: float, review_rate: float, id_ok: bool
) -> dict[str, float]:
    completeness = sum(1 for f in V1_REQUIRED_FIELDS if doc.get(f) not in (None, "", [], {})) / len(V1_REQUIRED_FIELDS)
    dims = {
        "schema_conformance": 1.0 if projected_ok else 0.0,
        "evidence_traceability": trace_rate,
        "field_completeness": completeness,
        "review_derivability": review_rate,
        "id_stability": 1.0 if id_ok else 0.0,
    }
    dims["RQS"] = round(sum(RQS_WEIGHTS[k] * v for k, v in dims.items()), 4)
    return dims


def _rate(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def measure(frame: Mapping[str, Any], samp: Mapping[str, Any]) -> dict[str, Any]:
    validator = _load_validator()
    v1_schema = validator._load_schema(validator.SCHEMA_V1)
    p_schema = projected_schema(v1_schema)
    items: list[dict[str, Any]] = []
    seen_ids: dict[str, int] = {}
    for row in samp["rows"]:
        claim = frame["claims"][row["claim_id"]]
        strict_item = map_claim(claim, row, frame, projected=False)
        proj_item = map_claim(claim, row, frame, projected=True)
        doc = proj_item["doc"]
        doc["provenance"]["content_sha256"] = validator.content_sha256(doc)
        strict_doc = copy.deepcopy(strict_item["doc"])
        strict_doc["provenance"]["content_sha256"] = validator.content_sha256(strict_doc)
        strict_errs = validate_strict(strict_doc, validator)
        proj_errs = validate_projected(doc, p_schema, validator)
        if not proj_item["audit"]["type_mapped"]:
            proj_errs.append(
                "R3: source claim_type has no v1 type mapping (needs versioned bridge registry)"
            )
        ev_total = len(doc["evidence"])
        ev_ok = 0
        has_reviewed = False
        gates = {
            "content_addressed": 0,
            "quote_present": 0,
            "addressable_local": 0,
            "addressable_pinned": 0,
            "addressable_external_pin": 0,
            "quote_span_hashed": 0,
        }
        for ev in doc["evidence"]:
            loc = ev.get("locator") or {}
            art = ev.get("artifact_ref") or {}
            citation = str(loc.get("citation") or "")
            content_addressed = bool(_hex64(loc.get("content_sha256")))
            quoted = len(str(loc.get("quote") or "").strip()) >= 15
            local = bool(citation) and (REPO / citation).exists()
            pinned = str(art.get("commit") or "") != ""
            if content_addressed:
                gates["content_addressed"] += 1
            if loc.get("content_sha256_kind") == "quote_span":
                gates["quote_span_hashed"] += 1
            if quoted:
                gates["quote_present"] += 1
            if local:
                gates["addressable_local"] += 1
            if pinned:
                gates["addressable_pinned"] += 1
            value_pin = bool(re.search(r"@[0-9a-f]{7,40}\b", str(loc.get("value") or "")))
            if value_pin:
                gates["addressable_external_pin"] += 1
            if content_addressed and quoted and (local or pinned or value_pin):
                ev_ok += 1
            rec = frame["evidence"].get(str(ev.get("source_evidence_ref"))) or {}
            if str(rec.get("assessment_status") or "") not in ("", "unassessed"):
                has_reviewed = True
        trace_rate = ev_ok / ev_total if ev_total else 0.0
        kid = doc["knowledge_id"]
        id_ok = bool(re.fullmatch(r"ko:[a-z0-9][a-z0-9._-]*:[a-z0-9][a-z0-9._-]*", kid)) and kid not in seen_ids
        seen_ids[kid] = seen_ids.get(kid, 0) + 1
        review_rate = sum(1 for f in REVIEW_FIELDS if proj_item["audit"]["review"][f]["derivable"]) / len(REVIEW_FIELDS)
        basis_unrepresentable = not strict_item["audit"]["review"]["confidence.basis"]["derivable"] and bool(
            proj_item["audit"]["review"]["confidence.basis"]["derivable"]
        )
        rqs = _rqs(doc, projected_ok=not proj_errs, trace_rate=trace_rate, review_rate=review_rate, id_ok=id_ok)
        items.append(
            {
                "row": row,
                "doc": doc,
                "audit": proj_item["audit"],
                "audit_strict": strict_item["audit"],
                "strict_errors": strict_errs,
                "strict_categories": categorize(strict_errs),
                "projected_errors": proj_errs,
                "projected_categories": categorize(proj_errs),
                "evidence": {
                    "total": ev_total,
                    "traceable": ev_ok,
                    "trace_rate": trace_rate,
                    "gates": gates,
                },
                "rqs": rqs,
                "_reviewed_evidence": has_reviewed,
                "_basis_unrepresentable_v10": basis_unrepresentable,
            }
        )
    return {"items": items, "validator_version": validator.RESOLVER_VERSION}


def summarize(frame: Mapping[str, Any], samp: Mapping[str, Any], meas: Mapping[str, Any]) -> dict[str, Any]:
    items = meas["items"]
    n = len(items)
    strict_pass = sum(1 for it in items if not it["strict_errors"])
    proj_pass = sum(1 for it in items if not it["projected_errors"])
    blockers: dict[str, int] = {}
    proj_blockers: dict[str, int] = {}
    for it in items:
        for c in it["strict_categories"]:
            blockers[c] = blockers.get(c, 0) + 1
        for c in it["projected_categories"]:
            proj_blockers[c] = proj_blockers.get(c, 0) + 1

    def weighted(flag) -> float | None:
        num = sum(it["row"]["weight"] * (1.0 if flag(it) else 0.0) for it in items)
        den = sum(it["row"]["weight"] for it in items)
        return round(num / den, 4) if den else None

    by_type: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        key = it["doc"]["type"] if it["audit"]["type_mapped"] else "unmapped"
        by_type.setdefault(key, []).append(it)
    type_rows = []
    for key in sorted(by_type):
        group = by_type[key]
        sp = sum(1 for g in group if not g["strict_errors"])
        pp = sum(1 for g in group if not g["projected_errors"])
        type_rows.append(
            {
                "type": key,
                "n": len(group),
                "strict_pass": sp,
                "strict_pass_rate": _rate(sp, len(group)),
                "projected_pass": pp,
                "projected_pass_rate": _rate(pp, len(group)),
                "mean_rqs": round(statistics.fmean(g["rqs"]["RQS"] for g in group), 4),
                "mean_trace_rate": round(statistics.fmean(g["evidence"]["trace_rate"] for g in group), 4),
            }
        )
    by_facet: dict[str, list[dict[str, Any]]] = {}
    for it in items:
        by_facet.setdefault(it["row"]["facet"], []).append(it)
    facet_rows = []
    for key in sorted(by_facet):
        group = by_facet[key]
        pp = sum(1 for g in group if not g["projected_errors"])
        facet_rows.append(
            {
                "facet": key,
                "n": len(group),
                "projected_pass": pp,
                "projected_pass_rate": _rate(pp, len(group)),
                "mean_trace_rate": round(statistics.fmean(g["evidence"]["trace_rate"] for g in group), 4),
                "mean_rqs": round(statistics.fmean(g["rqs"]["RQS"] for g in group), 4),
            }
        )
    rqs_values = [it["rqs"]["RQS"] for it in items]
    hist_edges = [round(i / 10, 1) for i in range(11)]
    hist_counts = [0] * (len(hist_edges) - 1)
    for v in rqs_values:
        hist_counts[min(int(v * 10), len(hist_counts) - 1)] += 1
    dim_means = {
        k: round(statistics.fmean(it["rqs"][k] for it in items), 4) for k in (*RQS_WEIGHTS.keys(), "RQS")
    }
    evidence_tot = sum(it["evidence"]["total"] for it in items)
    evidence_ok = sum(it["evidence"]["traceable"] for it in items)
    metrics: dict[str, Any] = {
        "anchor": ANCHOR,
        "metric_version": METRIC_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "validator_version": meas["validator_version"],
        "frame": {
            "population": samp["population"],
            "corpora": {
                f: sum(len(v) for k, v in frame["strata"].items() if k[0] == f) for f in sorted(CORPORA)
            },
            "strata": [
                {"facet": k[0], "claim_type": k[1], "size": len(v)} for k, v in sorted(frame["strata"].items())
            ],
            "source_type_vocabulary": sorted({k[1] for k in frame["strata"]}),
        },
        "sample": {
            "n": samp["n"],
            "seed": samp["seed"],
            "sampling_version": samp["sample_version"],
            "min_per_stratum": MIN_PER_STRATUM,
            "stratified_by": "facet × source claim_type",
            "by_stratum": [
                {
                    "facet": k[0],
                    "claim_type": k[1],
                    "sampled": sum(1 for r in samp["rows"] if (r["facet"], r["source_claim_type"]) == k),
                    "stratum_size": len(v),
                }
                for k, v in sorted(frame["strata"].items())
            ],
        },
        "strict_v1": {
            "pass": strict_pass,
            "n": n,
            "rate": _rate(strict_pass, n),
            "weighted_rate": weighted(lambda it: not it["strict_errors"]),
            "blockers": dict(sorted(blockers.items())),
        },
        "projected_v1_1": {
            "pass": proj_pass,
            "n": n,
            "rate": _rate(proj_pass, n),
            "weighted_rate": weighted(lambda it: not it["projected_errors"]),
            "blockers": dict(sorted(proj_blockers.items())),
            "revisions": [
                "R1_evidence_locator",
                "R2_basis_vocabulary",
                "R3_type_bridge",
                "R4_locator_section_split",
                "R5_quote_span_hash",
                "R6_external_pin",
            ],
        },
        "by_type": type_rows,
        "by_facet": facet_rows,
        "review_fields": _review_accuracy(items),
        "rqs": {
            "weights": RQS_WEIGHTS,
            "dimension_means": dim_means,
            "mean": round(statistics.fmean(rqs_values), 4),
            "median": round(statistics.median(rqs_values), 4),
            "min": round(min(rqs_values), 4),
            "max": round(max(rqs_values), 4),
            "histogram": {"edges": hist_edges, "counts": hist_counts},
        },
        "evidence": {
            "gates": {
                k: sum(it["evidence"]["gates"][k] for it in items)
                for k in (
                    "content_addressed",
                    "quote_present",
                    "addressable_local",
                    "addressable_pinned",
                    "addressable_external_pin",
                    "quote_span_hashed",
                )
            },
            "evidence_total": evidence_tot,
            "evidence_traceable": evidence_ok,
            "trace_rate": _rate(evidence_ok, evidence_tot),
            "weighted_trace_rate": weighted(lambda it: it["evidence"]["trace_rate"]),
            "per_object_trace_rate": [round(it["evidence"]["trace_rate"], 4) for it in items],
            "unresolved_refs": sum(len(it["audit"]["unresolved_evidence"]) for it in items),
        },
        "mapping": {
            "type_unmapped": sum(1 for it in items if not it["audit"]["type_mapped"]),
            "type_unmapped_share": _rate(sum(1 for it in items if not it["audit"]["type_mapped"]), n),
            "type_unmapped_weighted": weighted(lambda it: not it["audit"]["type_mapped"]),
            "payload_missing": sum(
                1
                for it in items
                if it["audit"]["type_mapped"]
                and it["doc"]["type"] in CARD_TYPES
                and not it["audit"]["payload_present"]
            ),
            "basis_unrepresentable_v10": sum(1 for it in items if it["_basis_unrepresentable_v10"]),
            "basis_unrepresentable_v10_share": _rate(
                sum(1 for it in items if it["_basis_unrepresentable_v10"]), n
            ),
            "basis_unrepresentable_v10_weighted": weighted(lambda it: it["_basis_unrepresentable_v10"]),
            "report_linked_evidence": 0,
            "report_linked_note": "仓内语料 0 条证据带 TP report_id（全为 locator 型）",
        },
    }
    metrics["reproducibility"] = {
        "metrics_sha256": _stable_digest(metrics),
        "note": "排除 generated_at 后的规范 JSON sha256；同一语料重跑必须一致",
    }
    return metrics


def _stable_digest(metrics: Mapping[str, Any]) -> str:
    body = copy.deepcopy(dict(metrics))
    body.pop("generated_at", None)
    body.pop("reproducibility", None)
    return hashlib.sha256(
        json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

def full_frame_rates(frame: Mapping[str, Any]) -> dict[str, Any]:
    """全样本（非抽样）精确率：作为 §6 误差判定的基准（总体值，不是估计量）。

    流式计数，不保留对象（10^4 量级不驻留内存）。
    """
    validator = _load_validator()
    v1_schema = validator._load_schema(validator.SCHEMA_V1)
    p_schema = projected_schema(v1_schema)
    n = 0
    strict_pass = proj_pass = 0
    ev_total = ev_ok = 0
    type_unmapped = basis_unrep = 0
    for cid in sorted(frame["claims"]):
        row = {"claim_id": cid, "facet": frame["facet"][cid],
               "source_claim_type": str(frame["claims"][cid].get("claim_type") or "missing")}
        claim = frame["claims"][cid]
        strict_item = map_claim(claim, row, frame, projected=False)
        proj_item = map_claim(claim, row, frame, projected=True)
        doc = proj_item["doc"]
        doc["provenance"]["content_sha256"] = validator.content_sha256(doc)
        sd = copy.deepcopy(strict_item["doc"])
        sd["provenance"]["content_sha256"] = validator.content_sha256(sd)
        strict_pass += int(not validate_strict(sd, validator))
        errs = validate_projected(doc, p_schema, validator)
        if not proj_item["audit"]["type_mapped"]:
            errs.append("R3: unmapped")
        proj_pass += int(not errs)
        type_unmapped += int(not proj_item["audit"]["type_mapped"])
        basis_unrep += int(
            proj_item["audit"]["review"]["confidence.basis"]["derivable"]
            and not strict_item["audit"]["review"]["confidence.basis"]["derivable"]
        )
        for ev in doc["evidence"]:
            loc = ev.get("locator") or {}
            art = ev.get("artifact_ref") or {}
            ev_total += 1
            ok = bool(_hex64(loc.get("content_sha256"))) and len(str(loc.get("quote") or "").strip()) >= 15 and (
                (bool(loc.get("citation")) and (REPO / str(loc.get("citation"))).exists())
                or bool(art.get("commit"))
                or bool(re.search(r"@[0-9a-f]{7,40}\b", str(loc.get("value") or "")))
            )
            ev_ok += int(ok)
        n += 1
    return {
        "anchor": ANCHOR,
        "scope": "full frame (population, not sample)",
        "population": n,
        "strict_v1_pass": strict_pass,
        "strict_v1_rate": _rate(strict_pass, n),
        "projected_v1_1_pass": proj_pass,
        "projected_v1_1_rate": _rate(proj_pass, n),
        "error_rate_pp": {
            "strict_v1": round(abs(_rate(strict_pass, n) * 100 - 0.0), 4),
            "projected_v1_1": None,  # 由报告脚本按样本值填入
        },
        "evidence_total": ev_total,
        "evidence_traceable": ev_ok,
        "evidence_trace_rate": _rate(ev_ok, ev_total),
        "type_unmapped": type_unmapped,
        "basis_unrepresentable_v10": basis_unrep,
        "basis_unrepresentable_v10_share": _rate(basis_unrep, n),
    }


# --------------------------------------------------------------------- figures
def _matplotlib():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def figure_quality_by_type(metrics: Mapping[str, Any], out: Path) -> Path:
    plt = _matplotlib()
    rows = metrics["by_type"]
    labels = [f"{r['type']} (n={r['n']})" for r in rows]
    y = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(9.6, 0.62 * len(rows) + 2.2))
    ax.barh([i + 0.2 for i in y], [r["strict_pass_rate"] or 0 for r in rows], height=0.38,
            color="#c0392b", label="strict v1 pass rate")
    ax.barh([i - 0.2 for i in y], [r["projected_pass_rate"] or 0 for r in rows], height=0.38,
            color="#1f77b4", label="projected v1.1 pass rate")
    for i, r in enumerate(rows):
        ax.text(max(r["strict_pass_rate"] or 0, r["projected_pass_rate"] or 0) + 0.02, i,
                f"RQS {r['mean_rqs']:.2f} · E-TR {r['mean_trace_rate']:.2f}", va="center", fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, 1.32)
    ax.set_xlabel(f"pass rate under schema (n={metrics['sample']['n']} objects, stratified sample)")
    ax.set_title(f"KO quality by v1 type — RCI S2b pilot (anchor {metrics['anchor']})", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def figure_review_accuracy(metrics: Mapping[str, Any], out: Path) -> Path:
    plt = _matplotlib()
    rows = metrics["review_fields"]
    labels = [r["field"] for r in rows]
    x = list(range(len(rows)))
    fig, ax = plt.subplots(figsize=(9.8, 4.4))
    ax.bar([i - 0.18 for i in x], [r["derivable_v10_rate"] or 0 for r in rows], width=0.36,
           color="#c0392b", label="derivable under v1.0 (current schema)")
    ax.bar([i + 0.18 for i in x], [r["accuracy"] or 0 for r in rows], width=0.36,
           color="#27ae60", label="accurate under projected v1.1 (derivable AND invariant-consistent)")
    for i, r in enumerate(rows):
        ax.text(i, max(r["derivable_v10_rate"] or 0, r["accuracy"] or 0) + 0.02,
                f"{r['derivable_v10_rate']:.2f}→{r['accuracy']:.2f}\nconflict {r['conflicts']}",
                ha="center", fontsize=8)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=8, rotation=12)
    ax.set_ylim(0, 1.18)
    ax.set_ylabel(f"rate over n={metrics['sample']['n']} objects")
    ax.set_title("Review-field accuracy after source→ko/v1 mapping (RCI S2b pilot)", fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def figure_rqs(metrics: Mapping[str, Any], out: Path) -> Path:
    plt = _matplotlib()
    hist = metrics["rqs"]["histogram"]
    edges, counts = hist["edges"], hist["counts"]
    centers = [(edges[i] + edges[i + 1]) / 2 for i in range(len(counts))]
    fig, axes = plt.subplots(1, 3, figsize=(13.6, 4.0), gridspec_kw={"width_ratios": [1.3, 1.3, 1]})
    axes[0].bar(centers, counts, width=0.085, color="#2980b9", edgecolor="white")
    for c, v in zip(centers, counts):
        if v:
            axes[0].text(c, v + max(counts) * 0.01, str(v), ha="center", fontsize=7)
    axes[0].axvline(metrics["rqs"]["mean"], color="#c0392b", linestyle="--", linewidth=1,
                    label=f"mean {metrics['rqs']['mean']:.3f}")
    axes[0].axvline(metrics["rqs"]["median"], color="#27ae60", linestyle=":", linewidth=1,
                    label=f"median {metrics['rqs']['median']:.3f}")
    axes[0].set_xlabel("RQS (weights published in metrics.json)")
    axes[0].set_ylabel("objects")
    axes[0].set_title(f"RQS distribution (n={metrics['sample']['n']}, "
                      f"min {metrics['rqs']['min']:.2f} / max {metrics['rqs']['max']:.2f})", fontsize=9)
    axes[0].legend(fontsize=7)
    axes[0].grid(axis="y", alpha=0.3)
    e_edges = [round(i / 5, 1) for i in range(6)]
    e_counts = [0] * (len(e_edges) - 1)
    for rate in metrics["evidence"]["per_object_trace_rate"]:
        e_counts[min(int(rate * 5), len(e_counts) - 1)] += 1
    axes[1].bar([(e_edges[i] + e_edges[i + 1]) / 2 for i in range(len(e_counts))], e_counts,
                width=0.16, color="#16a085", edgecolor="white")
    for i, v in enumerate(e_counts):
        if v:
            axes[1].text((e_edges[i] + e_edges[i + 1]) / 2, v + 1, str(v), ha="center", fontsize=7)
    axes[1].set_xticks(e_edges)
    axes[1].set_xlabel("per-object evidence traceability (E-TR)")
    axes[1].set_ylabel("objects")
    axes[1].set_title(f"E-TR distribution (pooled {metrics['evidence']['trace_rate']:.1%}, "
                      f"{metrics['evidence']['evidence_total']} evidence rows)", fontsize=9)
    axes[1].grid(axis="y", alpha=0.3)
    dims = metrics["rqs"]["dimension_means"]
    keys = list(metrics["rqs"]["weights"].keys())
    axes[2].barh(keys[::-1], [dims[k] for k in keys[::-1]], color="#8e44ad", height=0.55)
    for i, k in enumerate(keys[::-1]):
        axes[2].text(dims[k] + 0.02, i, f"{dims[k]:.3f}", va="center", fontsize=8)
    axes[2].set_xlim(0, 1.18)
    axes[2].set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    axes[2].set_title("per-dimension mean (unweighted)", fontsize=9)
    axes[2].grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# ---------------------------------------------------------------- table rendering
def render_tables(metrics: Mapping[str, Any]) -> str:
    """报告数字块：由 metrics.json 渲染，禁止手抄（测试逐字符比对）。"""
    s, st, pj, ev = metrics["sample"], metrics["strict_v1"], metrics["projected_v1_1"], metrics["evidence"]
    lines = ["<!-- BEGIN GENERATED: scripts/rci_s2b_pilot.py --render-tables -->"]
    lines.append("| 指标 | 数值 |")
    lines.append("|---|---|")
    lines.append(f"| 抽样框（去重 claim 全集） | {metrics['frame']['population']} |")
    lines.append(f"| 试点样本量 | {s['n']} |")
    lines.append(f"| 分层方式 | {s['stratified_by']}（每层保底 {s['min_per_stratum']}，余量按层规模比例） |")
    lines.append(f"| strict v1 通过 | {st['pass']}/{st['n']} = **{st['rate']:.1%}** |")
    lines.append(f"| strict v1 加权估计（总体） | {st['weighted_rate']:.1%} |")
    lines.append(f"| projected v1.1 通过 | {pj['pass']}/{pj['n']} = **{pj['rate']:.1%}** |")
    lines.append(f"| projected v1.1 加权估计（总体） | {pj['weighted_rate']:.1%} |")
    lines.append(f"| 证据条数（样本内） | {ev['evidence_total']} |")
    lines.append(
        "| 可追溯证据（内容哈希 ∧ 引文 ∧ 定位可解析[仓内或 git 钉扎]） | "
        f"{ev['evidence_traceable']}/{ev['evidence_total']} = {ev['trace_rate']:.1%} |"
    )
    lines.append(f"| 未解析 evidence_ref | {ev['unresolved_refs']} |")
    lines.append(f"| 类型无诚实映射对象 | {metrics['mapping']['type_unmapped']}（{metrics['mapping']['type_unmapped_share']:.1%}） |")
    lines.append(f"| 卡类 payload 缺失 | {metrics['mapping']['payload_missing']} |")
    lines.append(
        "| R2 影响：v1.0 basis 词表无档、被迫写 unassessed | "
        f"{metrics['mapping']['basis_unrepresentable_v10']}（{metrics['mapping']['basis_unrepresentable_v10_share']:.1%}） |"
    )
    g = ev["gates"]
    lines.append(
        "| 证据闸（内容哈希 / 引文 / 可解析-仓内 / 可解析-git钉扎 / 可解析-外部@pin） | "
        f"{g['content_addressed']} / {g['quote_present']} / {g['addressable_local']} / "
        f"{g['addressable_pinned']} / {g['addressable_external_pin']} 条 |"
    )
    lines.append(f"| R5 影响：摄取期引文切片自算哈希（quote_span） | {g['quote_span_hashed']} 条 |")
    lines.append(f"| RQS 均值 / 中位 / 最小 / 最大 | {metrics['rqs']['mean']:.3f} / {metrics['rqs']['median']:.3f} / {metrics['rqs']['min']:.3f} / {metrics['rqs']['max']:.3f} |")
    lines.append(f"| metrics 稳定摘要 sha256 | `{metrics['reproducibility']['metrics_sha256'][:16]}…` |")
    lines.append("")
    lines.append("**失败原因归类（严格 v1，按对象计数，可多因）**")
    lines.append("")
    lines.append("| 归类 | 条款 | 对象数 |")
    lines.append("|---|---|---|")
    clause = {
        "R1_evidence_locator": "R1 证据定位符（report_id 必填）",
        "R3_type_bridge": "R3 源类型词表→v1 type 桥接缺失",
        "R2_basis_vocabulary": "R2 basis 词表缺 code/dataset 档",
        "payload_card_body": "卡类 payload 必填",
        "field_contract": "字段契约",
        "status_machine": "状态机",
        "other": "其他",
    }
    for k, v in st["blockers"].items():
        lines.append(f"| `{k}` | {clause.get(k, '-')} | {v} |")
    lines.append("")
    lines.append("**分类型质量（v1 type，n = 样本内条数）**")
    lines.append("")
    lines.append("| v1 type | n | strict 通过 | projected 通过 | 平均 RQS | 平均 E-TR |")
    lines.append("|---|---|---|---|---|---|")
    for r in metrics["by_type"]:
        lines.append(
            f"| `{r['type']}` | {r['n']} | {r['strict_pass']}/{r['n']} ({r['strict_pass_rate']:.0%}) "
            f"| {r['projected_pass']}/{r['n']} ({r['projected_pass_rate']:.0%}) "
            f"| {r['mean_rqs']:.3f} | {r['mean_trace_rate']:.3f} |"
        )
    lines.append("")
    lines.append("**分语料面质量（facet）**")
    lines.append("")
    lines.append("| facet | n | projected 通过 | 平均 E-TR | 平均 RQS |")
    lines.append("|---|---|---|---|---|")
    for r in metrics["by_facet"]:
        lines.append(
            f"| `{r['facet']}` | {r['n']} | {r['projected_pass']}/{r['n']} ({r['projected_pass_rate']:.0%}) "
            f"| {r['mean_trace_rate']:.3f} | {r['mean_rqs']:.3f} |"
        )
    lines.append("")
    lines.append("**review 字段准确率（可派生 ∧ 不变量一致）**")
    lines.append("")
    lines.append("| 字段 | v1.0 可派生 | v1.1 可派生 | 准确（v1.1 ∧ 不变量） | 冲突 |")
    lines.append("|---|---|---|---|---|")
    for r in metrics["review_fields"]:
        lines.append(
            f"| `{r['field']}` | {r['derivable_v10']}/{r['n']} ({r['derivable_v10_rate']:.0%}) "
            f"| {r['derivable']}/{r['n']} ({r['derivable_rate']:.0%}) "
            f"| {r['invariant_consistent']}/{r['n']} ({r['accuracy']:.0%}) | {r['conflicts']} |"
        )
    lines.append("")
    lines.append("**RQS 逐维均值（权重见上表口径，逐维可直接读）**")
    lines.append("")
    lines.append("| 维度 | 权重 | 均值 |")
    lines.append("|---|---|---|")
    for k, w in metrics["rqs"]["weights"].items():
        lines.append(f"| `{k}` | {w:.2f} | {metrics['rqs']['dimension_means'][k]:.3f} |")
    lines.append("| **RQS** | 1.00 | **{:.3f}** |".format(metrics["rqs"]["dimension_means"]["RQS"]))
    lines.append("")
    lines.append("**RQS 直方图（0.1 分箱，count）**")
    lines.append("")
    lines.append("| 区间 | " + " | ".join(
        f"{metrics['rqs']['histogram']['edges'][i]:.1f}–{metrics['rqs']['histogram']['edges'][i + 1]:.1f}"
        for i in range(len(metrics["rqs"]["histogram"]["counts"]))
    ) + " |")
    lines.append("|---" * (len(metrics["rqs"]["histogram"]["counts"]) + 1) + "|")
    lines.append("| count | " + " | ".join(str(c) for c in metrics["rqs"]["histogram"]["counts"]) + " |")
    lines.append("<!-- END GENERATED -->")
    return "\n".join(lines)


def render_error_table(metrics: Mapping[str, Any], rates: Mapping[str, Any]) -> str:
    """§6 误差判定表：样本值 / 加权估计 / 全样本真值 / 误差(pp) / 是否 <3 pp。"""
    def pp(a: float, b: float) -> str:
        return f"{abs(a - b) * 100:.2f} pp"

    def verdict(*errs: float) -> str:
        return " / ".join("✅" if e * 100 < 3 else "❌" for e in errs)

    ev, mp, st, pj = metrics["evidence"], metrics["mapping"], metrics["strict_v1"], metrics["projected_v1_1"]
    rows = [
        (
            "strict v1 通过率",
            st["rate"],
            st["weighted_rate"],
            rates["strict_v1_rate"],
        ),
        (
            "projected v1.1 通过率",
            pj["rate"],
            pj["weighted_rate"],
            rates["projected_v1_1_rate"],
        ),
        (
            "证据可追溯率 E-TR",
            ev["trace_rate"],
            ev["weighted_trace_rate"],
            rates["evidence_trace_rate"],
        ),
        (
            "R2 影响面（basis 被迫 unassessed）",
            mp["basis_unrepresentable_v10_share"],
            mp["basis_unrepresentable_v10_weighted"],
            rates["basis_unrepresentable_v10_share"],
        ),
        (
            "类型无映射对象占比",
            mp["type_unmapped_share"],
            mp["type_unmapped_weighted"],
            rates["type_unmapped"] / rates["population"],
        ),
    ]
    lines = ["<!-- BEGIN GENERATED: error table -->"]
    lines.append(
        f"| 关键量 | 样本值（n={metrics['sample']['n']}，不加权） | 加权估计 | 全样本真值"
        f"（n={rates['population']}） | 误差（pp，不加权 / 加权） | <3 pp?（不加权 / 加权） |"
    )
    lines.append("|---|---|---|---|---|---|")
    for name, sample, weighted, pop in rows:
        lines.append(
            f"| {name} | {sample:.2%} | {weighted:.2%} | {pop:.2%} | {pp(sample, pop)} / {pp(weighted, pop)} "
            f"| {verdict(abs(sample - pop), abs(weighted - pop))} |"
        )
    lines.append("<!-- END GENERATED -->")
    return "\n".join(lines)


# --------------------------------------------------------------------- pipeline
def run(out_art: Path = OUT_ART, out_fig: Path = OUT_FIG, *, figures: bool = True) -> dict[str, Any]:
    frame = build_frame()
    samp = sample(frame)
    meas = measure(frame, samp)
    metrics = summarize(frame, samp, meas)
    out_art.mkdir(parents=True, exist_ok=True)
    (out_art / "metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    (out_art / "sample_manifest.json").write_text(
        json.dumps(
            {
                "anchor": ANCHOR,
                "sample_version": SAMPLE_VERSION,
                "seed": SEED,
                "n": samp["n"],
                "population": samp["population"],
                "rows": samp["rows"],
            },
            ensure_ascii=False,
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    if figures:
        out_fig.mkdir(parents=True, exist_ok=True)
        figure_quality_by_type(metrics, out_fig / "ko_quality_by_type.png")
        figure_review_accuracy(metrics, out_fig / "review_field_accuracy.png")
        figure_rqs(metrics, out_fig / "rqs_distribution.png")
    return metrics


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="RCI S2b 200-object pilot (anchor KBM-RCI-S2B-PILOT)")
    ap.add_argument("--no-figures", action="store_true", help="只写工件，不出图")
    ap.add_argument("--render-tables", action="store_true", help="打印报告数字块（从 metrics.json 读）")
    ap.add_argument("--full-frame", action="store_true", help="跑全样本精确率（§6 误差基准，慢）")
    args = ap.parse_args(argv)
    if args.render_tables:
        path = OUT_ART / "metrics.json"
        if not path.exists():
            print(f"missing {path}; run without --render-tables first", file=sys.stderr)
            return 2
        metrics_obj = json.loads(path.read_text(encoding="utf-8"))
        print(render_tables(metrics_obj))
        rates_path = OUT_ART / "full_frame_rates.json"
        if rates_path.exists():
            print()
            print(render_error_table(metrics_obj, json.loads(rates_path.read_text(encoding="utf-8"))))
        return 0
    if args.full_frame:
        rates = full_frame_rates(build_frame())
        OUT_ART.mkdir(parents=True, exist_ok=True)
        (OUT_ART / "full_frame_rates.json").write_text(
            json.dumps(rates, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps(rates, ensure_ascii=False, indent=1))
        return 0
    metrics = run(figures=not args.no_figures)
    print(json.dumps(
        {
            "anchor": metrics["anchor"],
            "population": metrics["frame"]["population"],
            "n": metrics["sample"]["n"],
            "strict_v1_rate": metrics["strict_v1"]["rate"],
            "projected_v1_1_rate": metrics["projected_v1_1"]["rate"],
            "rqs_mean": metrics["rqs"]["mean"],
            "metrics_sha256": metrics["reproducibility"]["metrics_sha256"][:16],
        },
        ensure_ascii=False,
        indent=1,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
