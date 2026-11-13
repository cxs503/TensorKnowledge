"""KE 服务的 KO Schema v1 写入面（平台侧真调用方）。

被 ``ke/api.py`` 以 ``app.include_router(...)`` 挂载；端点直接调用
:mod:`ke.ko_ingest`（校验→三闸解析→落库→票据晋级），没有任何本地复制的规则。
写面在 ``KE_API_TOKEN`` 未配置时关闭（503），不开放匿名写。

可选依赖 fastapi：导入失败不影响 ``ke.ko_ingest`` 的 CLI 路径。
"""
from __future__ import annotations

import hmac
import os
from pathlib import Path

from fastapi import APIRouter, Body, Header, HTTPException, Query

from . import ko_ingest

REPO = Path(__file__).resolve().parents[1]
router = APIRouter(tags=["ko-v1"])


def _auth(authorization: str | None) -> None:
    expected = os.environ.get("KE_API_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="KO v1 write surface disabled (KE_API_TOKEN unset)")
    token = (authorization or "").replace("Bearer ", "", 1).strip()
    if not token or not hmac.compare_digest(token, expected):
        raise HTTPException(status_code=401, detail="invalid token")


@router.post("/ko/v1/ingest", status_code=201)
def ingest_ko_v1(payload: dict = Body(...), authorization: str | None = Header(default=None),
                 schema: str = Query(default="ko_v1")) -> dict:
    """Schema v1 知识对象入库（L1 结构化记录）。body = 知识对象，或 {"doc":…, "reports":…}。"""
    _auth(authorization)
    doc = payload.get("doc", payload)
    conn = ko_ingest.connect()
    try:
        ko_ingest.ensure_schema(conn, schema)
        return ko_ingest.ingest(conn, doc, schema=schema, reports=payload.get("reports"),
                                repo_roots=[REPO], on_conflict="skip")
    except Exception as exc:  # 校验/重复/哈希不符：422 而不是 500
        raise HTTPException(status_code=422, detail=f"{type(exc).__name__}: {str(exc)[:400]}")
    finally:
        conn.close()


@router.get("/ko/v1/{knowledge_id}/traceability")
def traceability_ko_v1(knowledge_id: str, schema: str = Query(default="ko_v1")) -> dict:
    """证据可追溯率 E-TR：从库内三闸事实列复算。"""
    conn = ko_ingest.connect()
    try:
        ko_ingest.ensure_schema(conn, schema)
        return {"knowledge_id": knowledge_id, "traceability": ko_ingest.traceability(
            conn, knowledge_id, schema=schema)}
    finally:
        conn.close()


@router.post("/ko/v1/{knowledge_id}/promote", status_code=200)
def promote_ko_v1(knowledge_id: str, payload: dict = Body(default={}),
                  authorization: str | None = Header(default=None),
                  schema: str = Query(default="ko_v1")) -> dict:
    """report_claimed → platform_verified。只有平台角色 + 已写验证单才可能成功。"""
    _auth(authorization)
    conn = ko_ingest.connect()
    try:
        ko_ingest.ensure_schema(conn, schema)
        if payload.get("ticket_id"):
            ko_ingest.add_ticket(conn, knowledge_id, str(payload["ticket_id"]), schema=schema,
                                 gate_level=int(payload.get("gate_level", 3)))
        return ko_ingest.promote(conn, knowledge_id, schema=schema)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"{type(exc).__name__}: {str(exc)[:400]}")
    finally:
        conn.close()