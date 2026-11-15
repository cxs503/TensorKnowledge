"""TensorKnowledge — held-out 评测切分约定（防训练/评测泄漏）。

锚点 FEAT-SIM-DATAHOUSE（子件4·训练出口闸门，评测集切分）。

约定
----
* 名单文件 ``benchmarks/heldout/heldout_cases_v1.json`` 明确列出 held-out 案
  （≥15 案，``schema = tk-heldout/1``）。
* **任何产物**（数据集版本、训练集 builder、导出的 JSONL）都必须排除名单里的案；
  排除动作发生在 ``ke.dataset_builder.build_dataset()`` 入库存行之前，并在
  manifest 的 ``held_out`` 块里声明名单 id / 名单 sha256 / 被排除案号。
* 判定依据（任一命中即排除）：
  1. 行内 ``case_id`` / ``benchmark_id`` / ``benchmark_name`` / ``source_case``
     属于名单；
  2. 行内 ``split`` 显式为 ``held-out`` / ``held_out`` / ``test``。
* 名单本身按内容 sha256 钉住：名单被改动而 manifest 未升版本 → 可对账发现。

为什么不「按比例随机切分」：随机切分不可复现且无法证明被排除；此处用显式
名单 + 入库前强制过滤 + manifest 声明，三者都可审计。
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO = Path(__file__).resolve().parents[1]
DEFAULT_PATH = REPO / "benchmarks" / "heldout" / "heldout_cases_v1.json"
REGISTRY_SCHEMA = "tk-heldout/1"
#: 名单下限（评审要求：≥15 案）
MIN_CASES = 15
#: 行内可用于比对的案号字段
CASE_KEYS = ("case_id", "benchmark_id", "benchmark_name", "source_case")
#: 行内 split 值命中即排除
HELD_OUT_SPLITS = ("held-out", "held_out", "heldout", "test")


@dataclass(frozen=True)
class HeldOutRegistry:
    list_id: str
    list_version: str
    path: Path
    sha256: str
    cases: tuple[dict[str, Any], ...]

    @property
    def case_ids(self) -> frozenset[str]:
        return frozenset(str(c["case_id"]) for c in self.cases)

    def __len__(self) -> int:
        return len(self.cases)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_held_out(path: str | Path | None = None) -> HeldOutRegistry:
    """载入并校验 held-out 名单（案数下限、案号唯一、必填字段）。"""
    p = Path(path) if path is not None else DEFAULT_PATH
    if not p.is_file():
        raise FileNotFoundError(f"held-out registry not found: {p}")
    doc = json.loads(p.read_text(encoding="utf-8"))
    if doc.get("schema") != REGISTRY_SCHEMA:
        raise ValueError(f"{p}: schema must be {REGISTRY_SCHEMA!r}, got {doc.get('schema')!r}")
    cases = doc.get("cases") or []
    if not isinstance(cases, list) or len(cases) < MIN_CASES:
        raise ValueError(f"{p}: held-out list must declare >= {MIN_CASES} cases, got {len(cases)}")
    seen: set[str] = set()
    for c in cases:
        cid = str(c.get("case_id", "")).strip()
        if not cid:
            raise ValueError(f"{p}: case with empty case_id: {c!r}")
        if cid in seen:
            raise ValueError(f"{p}: duplicate held-out case_id {cid!r}")
        seen.add(cid)
        if not str(c.get("domain", "")).strip():
            raise ValueError(f"{p}: case {cid!r} missing domain")
    return HeldOutRegistry(
        list_id=str(doc.get("list_id") or p.stem),
        list_version=str(doc.get("list_version") or ""),
        path=p,
        sha256=_sha256_file(p),
        cases=tuple(cases),
    )


def row_case_id(row: dict[str, Any]) -> str | None:
    """取行内案号（按 CASE_KEYS 顺序取第一个非空值）。"""
    for k in CASE_KEYS:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    source = row.get("source")
    if isinstance(source, dict):
        for k in CASE_KEYS:
            v = source.get(k)
            if isinstance(v, str) and v.strip():
                return v.strip()
    return None


def filter_training_rows(
    rows: Iterable[dict[str, Any]],
    registry: HeldOutRegistry,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """把 held-out 案从训练行里剔除。

    返回 ``(kept, excluded)``；``excluded`` 每项带 ``id``/``case_id``/``reason``。
    """
    ids = registry.case_ids
    kept: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    for row in rows:
        cid = row_case_id(row)
        split = str(row.get("split", "")).strip().lower().replace("_", "-")
        reason = None
        if cid is not None and cid in ids:
            reason = "held_out_case_id"
        elif split in HELD_OUT_SPLITS:
            reason = "held_out_split_flag"
        if reason:
            excluded.append({
                "id": row.get("id"),
                "case_id": cid,
                "reason": reason,
            })
        else:
            kept.append(row)
    return kept, excluded


def declaration(
    registry: HeldOutRegistry,
    kept: list[dict[str, Any]],
    excluded: list[dict[str, Any]],
    total_rows: int,
) -> dict[str, Any]:
    """manifest 里的 held_out 声明块（可对账：名单 id + sha256 + 排除清单）。"""
    return {
        "policy": "held-out cases never enter training rows",
        "list_id": registry.list_id,
        "list_version": registry.list_version,
        "list_path": str(registry.path.relative_to(REPO)) if registry.path.is_relative_to(REPO) else str(registry.path),
        "list_sha256": registry.sha256,
        "case_count": len(registry),
        "source_rows": total_rows,
        "training_rows": len(kept),
        "excluded_count": len(excluded),
        "excluded": sorted(
            (e["case_id"] or e["id"] or "?") for e in excluded
        ),
        "enforced_by": "ke.dataset_builder.build_dataset",
    }


def verify_no_leak(rows: Iterable[dict[str, Any]], registry: HeldOutRegistry) -> None:
    """入库后置断言：库内行不得含 held-out 案号（泄漏即抛 AssertionError）。"""
    ids = registry.case_ids
    hits = [row_case_id(r) for r in rows if row_case_id(r) in ids]
    if hits:
        raise AssertionError(f"held-out leak: {sorted(set(hits))} present in dataset rows")