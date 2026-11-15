"""TensorKnowledge — 数据集版本 builder（held-out 强制排除 + 闸门登记）。

锚点 FEAT-SIM-DATAHOUSE（子件4·训练出口闸门）。

任何数据集版本都必须经 :func:`build_dataset` 入库，它做三件事，顺序不可颠倒：

1. 载入 held-out 名单（默认 ``benchmarks/heldout/heldout_cases_v1.json``），
   **入库前**把名单内案行剔除（不存在「先入库后过滤」的窗口）；
2. 入库后在同一个 SQLite 事务之外复核：库内行不得含 held-out 案号（
   :func:`ke.held_out.verify_no_leak`）；
3. manifest 写入 ``held_out`` 声明块（名单 id / sha256 / 排除清单 / 行数对账），
   并在有闸门表时登记 ``train_gate`` 行，初始审级 = ``none``（训练侧不可见）。

builder 不接受 `skip_held_out=True` 之类开关：排除是义务，不是选项。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from . import held_out as HO
from .datasets import DatasetStore
from .train_gate import TrainGateStore


class HeldOutLeakError(AssertionError):
    """held-out 案号出现在待入库/已入库行里。"""


def build_dataset(
    store: DatasetStore,
    name: str,
    version: str,
    rows: Iterable[dict[str, Any]],
    description: str = "",
    status: str = "draft",
    producer: str | None = None,
    gate: TrainGateStore | None = None,
    held_out_path: str | Path | None = None,
    registry: HO.HeldOutRegistry | None = None,
    extra_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """构建并登记一个数据集版本，返回 {manifest, kept_rows, excluded, gate}。

    *status* 是数据集自身审级（draft/reviewed/published，见 :mod:`ke.datasets`）；
    训练可见性由 ``train_gate`` 单独把关，二者不可互相替代。
    """
    rows = list(rows)
    reg = registry or HO.load_held_out(held_out_path)

    kept, excluded = HO.filter_training_rows(rows, reg)
    decl = HO.declaration(reg, kept, excluded, total_rows=len(rows))
    if decl["excluded_count"] != len(excluded):  # pragma: no cover - 结构性自检
        raise AssertionError("held-out declaration mismatch")

    extra = {"held_out": decl}
    if extra_manifest:
        if "held_out" in extra_manifest:
            raise ValueError("extra_manifest must not override held_out declaration")
        extra.update(extra_manifest)

    gate_row = None
    if gate is not None:
        # 先确认闸门未被登记过，避免「数据集入库了但闸门登记失败」的半截状态
        if gate.get(name, version) is not None:
            raise ValueError(f"train_gate already has {name}/{version}")

    store.register(
        name, version, kept, status=status, description=description, extra_manifest=extra
    )

    if gate is not None:
        gate_row = gate.register(name, version, producer=producer or "dataset-builder",
                                 actor=producer or "dataset-builder",
                                 note=f"dataset version {name}/{version} built")

    # 入库后复核（防 builder 与 store 之间有别的路径塞行）
    stored = [r for r in _stored_rows(store, name, version)]
    try:
        HO.verify_no_leak(stored, reg)
    except AssertionError as exc:
        raise HeldOutLeakError(str(exc)) from exc
    if len(stored) != len(kept):
        raise AssertionError(
            f"row-count mismatch for {name}/{version}: store={len(stored)} builder={len(kept)}"
        )

    return {
        "manifest": store.get_manifest(name, version),
        "kept_rows": len(kept),
        "excluded": excluded,
        "held_out": decl,
        "gate": gate_row,
    }


def _stored_rows(store: DatasetStore, name: str, version: str) -> list[dict[str, Any]]:
    """直读库内行（不走 download 闸门：这是 builder 的自检，不是训练侧消费）。"""
    import json

    cur = store.conn.execute(
        "SELECT row_json FROM dataset_rows WHERE name=? AND version=? ORDER BY row_index",
        (name, version),
    )
    return [json.loads(r["row_json"]) for r in cur]