"""训练出口闸门 HTTP 面：``/api/v1/knowledge/train-gate``。

锚点 FEAT-SIM-DATAHOUSE（子件4·训练出口闸门）。

被 ``ke/api.py`` 以 ``app.include_router(...)`` 挂载；也可独立运行::

    KE_TRAIN_GATE_DB=/var/tk/train_gate.db KE_API_TOKEN=... \
        python -m uvicorn ke.train_gate_api:standalone_app --port 8022

端点
----
GET  /api/v1/knowledge/train-gate
    闸门表（可按 dataset_id / version / level / visible 过滤），附审级计数、
    held-out 名单声明与审计对账告警。
GET  /api/v1/knowledge/train-gate/audit
    审计行（append-only，按 audit_id 升序）。
POST /api/v1/knowledge/train-gate
    登记（to_level='none' 且行不存在）或推进审级（none→reviewed→published，
    需审定人 + 证据链 + 非产出方）；返回 gate 行与新增审计行。
GET  /api/v1/knowledge/held-out
    held-out 评测保留名单（id / sha256 / 案表）。

写面在 ``KE_API_TOKEN`` 未配置时返回 503（不开放匿名写）；与 KE 其余写面同源。
"""
from __future__ import annotations

import hmac
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body, FastAPI, Header, HTTPException, Query

from . import held_out as HO
from .train_gate import LEVELS, TrainGateStore

REPO = Path(__file__).resolve().parents[1]
DEFAULT_GATE_DB = REPO / "var" / "tk_train_gate.db"

router = APIRouter(prefix="/api/v1/knowledge", tags=["train-gate"])

_store: TrainGateStore | None = None
_store_dsn: str | None = None


def gate_dsn() -> str:
    return os.environ.get("KE_TRAIN_GATE_DB") or str(DEFAULT_GATE_DB)


def get_gate() -> TrainGateStore:
    """进程内单例闸门存储（DSN 变化时重建，便于测试/演示切换库）。"""
    global _store, _store_dsn
    dsn = gate_dsn()
    if _store is None or _store_dsn != dsn:
        if dsn != ":memory:":
            Path(dsn).parent.mkdir(parents=True, exist_ok=True)
        _store = TrainGateStore(dsn)
        _store_dsn = dsn
    return _store


def reset_gate() -> None:
    """丢弃单例（测试用）。"""
    global _store, _store_dsn
    if _store is not None and _store_dsn and _store_dsn != ":memory:":
        _store.close()
    _store = None
    _store_dsn = None


def _auth(authorization: str | None) -> str:
    expected = os.environ.get("KE_API_TOKEN") or ""
    if not expected:
        raise HTTPException(status_code=503,
                            detail="train-gate write surface disabled (KE_API_TOKEN unset)")
    token = (authorization or "").replace("Bearer ", "", 1).strip()
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid token")
    return token


def _public(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "dataset_id": row["dataset_id"],
        "version": row["version"],
        "review_level": row["review_level"],
        "reviewer": row["reviewer"],
        "evidence_chain": row["evidence_chain"],
        "admitted_at": row["admitted_at"],
        "producer": row["producer"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "train_visible": row["review_level"] in ("reviewed", "published"),
    }


@router.get("/train-gate")
def list_train_gate(
    dataset_id: str | None = Query(default=None),
    version: str | None = Query(default=None),
    level: str | None = Query(default=None, description="none|reviewed|published"),
    visible: bool | None = Query(default=None, description="只看训练侧可见/不可见"),
) -> dict[str, Any]:
    """闸门表读取面（训练侧调度器/审计方用）。"""
    gate = get_gate()
    try:
        rows = gate.list_rows(dataset_id=dataset_id, level=level,
                              visible_only=bool(visible))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if version:
        rows = [r for r in rows if r["version"] == version]
    if visible is False:
        rows = [r for r in rows if r["review_level"] == "none"]
    return {
        "items": [_public(r) for r in rows],
        "count": len(rows),
        "counts": gate.grade_counts(),
        "alerts": gate.integrity_alerts(),
        "levels": list(LEVELS),
        "policy": "only review_level in ('reviewed','published') may enter the training set",
    }


@router.get("/train-gate/audit")
def train_gate_audit(
    dataset_id: str | None = Query(default=None),
    version: str | None = Query(default=None),
) -> dict[str, Any]:
    gate = get_gate()
    rows = gate.audit(dataset_id=dataset_id, version=version)
    return {"items": rows, "count": len(rows)}


@router.get("/held-out")
def held_out_list() -> dict[str, Any]:
    """held-out 评测保留名单（永不进训练集）。"""
    reg = HO.load_held_out()
    return {
        "list_id": reg.list_id,
        "list_version": reg.list_version,
        "sha256": reg.sha256,
        "case_count": len(reg),
        "cases": list(reg.cases),
        "policy": "held-out cases never enter training rows; enforced by ke.dataset_builder",
    }


@router.post("/train-gate")
def post_train_gate(
    payload: dict = Body(...),
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """登记 / 推进审级。

    body 例（推进）::

        {"dataset_id":"FEAT-SIM-DATAHOUSE","version":"v1.0","to_level":"reviewed",
         "reviewer":"rev-zhang","evidence_chain":["tkc:...","tke:..."],
         "actor":"rev-zhang","note":"仿真成果数据楼 v1.0 审阅通过"}

    登记（新版本，初始审级 none）: ``{"dataset_id":..., "version":..., "to_level":"none",
    "producer":...}``。
    """
    _auth(authorization)
    gate = get_gate()
    for key in ("dataset_id", "version"):
        if not str(payload.get(key, "")).strip():
            raise HTTPException(status_code=422, detail=f"missing field: {key}")
    dataset_id = str(payload["dataset_id"]).strip()
    version = str(payload["version"]).strip()
    to_level = str(payload.get("to_level", "")).strip()
    if to_level not in LEVELS:
        raise HTTPException(status_code=422, detail=f"to_level must be one of {list(LEVELS)}")

    exists = gate.get(dataset_id, version) is not None
    try:
        if to_level == "none" and not exists:
            row = gate.register(
                dataset_id, version,
                producer=payload.get("producer"),
                actor=payload.get("actor") or payload.get("producer"),
                note=str(payload.get("note") or "registered via train-gate API"),
            )
            action = "register"
        elif to_level == "none":
            row = gate.revoke(dataset_id, version,
                              actor=str(payload.get("actor") or ""),
                              note=str(payload.get("note") or ""))
            action = "revoke"
        else:
            row = gate.transition(
                dataset_id, version, to_level,
                reviewer=str(payload.get("reviewer") or ""),
                evidence_chain=payload.get("evidence_chain"),
                actor=str(payload.get("actor") or payload.get("reviewer") or ""),
                note=str(payload.get("note") or ""),
            )
            action = "transition"
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    audit_rows = gate.audit(dataset_id, version)
    return {"action": action, "item": _public(row), "audit": audit_rows[-1] if audit_rows else None}


# 独立进程入口（无 KE 主服务时也能开闸门面）
standalone_app = FastAPI(
    title="TensorKnowledge train-gate API",
    version="1.0.0",
    description="FEAT-SIM-DATAHOUSE training-exit gate (/api/v1/knowledge/train-gate)",
)
standalone_app.include_router(router)