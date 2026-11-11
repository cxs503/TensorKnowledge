"""KE service — HTTP API (FastAPI).

Run:  KE_API_TOKEN=... KE_DSN=postgresql://... python -m uvicorn ke.api:app --host 127.0.0.1 --port 8021

Endpoints (see docs/ke/api.md for the full contract + curl examples):

    GET    /healthz                     liveness + driver + DB reachability
    POST   /ko                          create a knowledge object (claim/evidence/
                                        provenance/review contract record)
    GET    /ko                          list (kind / axis+status / domain)
    GET    /ko/{id}                     read one object (exact ingested document)
    PATCH  /ko/{id}                     replace a *draft* document (producer only)
    DELETE /ko/{id}                     delete a *draft* (producer only)
    POST   /ko/{id}/submit              draft -> submitted (producer only)
    POST   /ko/{id}/review              append review event + move review state
                                        (server enforces reviewer != producer)
    POST   /ko/{id}/publish             private -> published (needs approved)
    GET    /ko/{id}/reviews             append-only review log for one object
    GET    /query/by-status             Q1
    GET    /query/by-evidence-relation  Q2
    GET    /query/chain                 Q3 provenance chain
    GET    /query/by-domain             Q4
    GET    /query/claim-evidence        Q5 claim -> evidence
    GET    /query/stats                 Q6 aggregate statistics
    GET    /search                      claim text + domain + status filtering

Auth: ``Authorization: Bearer $KE_API_TOKEN`` on every mutating call.  When
``KE_API_TOKEN`` is unset the write surface is *disabled* (503) rather than
open — an unconfigured deployment cannot be written to.
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import time
from pathlib import Path
from typing import Any, Literal

from fastapi import Body, Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from . import apistore as S

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"
SERVICE_VERSION = "1.0.0"

app = FastAPI(
    title="TensorKnowledge Engine API",
    version=SERVICE_VERSION,
    description="Knowledge-object service: CRUD, six query classes, review/publication "
                "state machine, search. Postgres transactions; SQLite supported for tests.",
)

_store: S.Store | None = None
_store_dsn: str | None = None


def get_store() -> S.Store:
    """One Store per DSN; rebuilt if KE_DSN changes (used by tests)."""
    global _store, _store_dsn
    dsn = S.default_dsn()
    if _store is None or _store_dsn != dsn:
        _store = S.Store(dsn)
        _store.ensure_schema()
        _store_dsn = dsn
    return _store


@app.exception_handler(S.NotFound)
async def _nf(_req: Request, exc: S.NotFound) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": f"not found: {exc}"})


@app.exception_handler(S.Conflict)
async def _cf(_req: Request, exc: S.Conflict) -> JSONResponse:
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(S.Forbidden)
async def _fb(_req: Request, exc: S.Forbidden) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": str(exc)})


@app.exception_handler(S.BadRequest)
async def _br(_req: Request, exc: S.BadRequest) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


# --------------------------------------------------------------------------
# auth
# --------------------------------------------------------------------------
def require_write_token(authorization: str | None = Header(default=None)) -> str:
    """Bearer check for the write surface.

    * KE_API_TOKEN unset  -> 503, writes disabled (never silently open)
    * header missing/bad  -> 401
    * match               -> returns the token (consumers ignore it)
    """
    expected = os.environ.get("KE_API_TOKEN", "")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="write API disabled: KE_API_TOKEN is not configured",
        )
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    presented = authorization.split(None, 1)[1].strip()
    if not hmac.compare_digest(presented, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return presented


def _identity(request: Request, body_producer: str | None = None) -> str:
    ident = request.headers.get("x-ke-agent") or body_producer
    if not ident:
        raise HTTPException(
            status_code=422,
            detail="producer identity required: send X-KE-Agent header or producer field",
        )
    return ident


# --------------------------------------------------------------------------
# request models
# --------------------------------------------------------------------------
class KOCreate(BaseModel):
    """POST /ko body: an explicit wrapper, or a bare contract record."""

    model_config = ConfigDict(extra="allow")

    kind: Literal["claim", "evidence", "provenance", "review"] | None = None
    producer: str | None = None
    domain: str | None = None
    doc: dict | None = None
    strict: bool | None = None


class KOPatch(BaseModel):
    model_config = ConfigDict(extra="allow")

    doc: dict
    producer: str | None = None


class Publisher(BaseModel):
    model_config = ConfigDict(extra="allow")

    producer: str | None = None


class ReviewIn(BaseModel):
    model_config = ConfigDict(extra="allow")

    decision: Literal["approve", "request-changes", "reject", "revoke", "deprecate"]
    reviewer: dict | str
    policy_version: str = "ke-review-policy/1.0.0"
    rationale: str | None = None
    findings: list[dict] | None = None
    reviewed_at: str | None = None
    id: str | None = None


def _reviewer_id(reviewer: dict | str) -> tuple[str, str]:
    if isinstance(reviewer, str):
        return reviewer, "agent"
    rid = reviewer.get("id")
    if not rid:
        raise S.BadRequest("reviewer.id is required")
    return str(rid), str(reviewer.get("reviewer_type") or "agent")


def _validate_record(kind: str, doc: dict, strict: bool) -> None:
    if not isinstance(doc, dict):
        raise S.BadRequest("record must be a JSON object")
    missing = [f for f in S.REQUIRED_FIELDS[kind] if f not in doc]
    if missing:
        raise S.BadRequest(f"{kind} record missing required fields: {missing}")
    inferred = S.infer_kind(doc)
    if inferred is not None and inferred != kind:
        raise S.BadRequest(
            f"id {doc['id']!r} has prefix for kind {inferred!r}, but kind={kind!r}"
        )
    if inferred is None:
        raise S.BadRequest(
            f"id {doc.get('id')!r} must start with {S.ID_PREFIX[kind]!r}"
        )
    if not strict:
        return
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover
        raise S.BadRequest("strict validation requested but jsonschema is missing") from exc
    schema_file = SCHEMAS_DIR / f"{kind}-record.schema.json"
    if not schema_file.is_file():  # pragma: no cover
        raise S.BadRequest(f"schema not found: {schema_file}")
    schema = json.loads(schema_file.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as exc:
        raise S.BadRequest(f"schema violation at {list(exc.path)}: {exc.message}") from exc


# --------------------------------------------------------------------------
# ops
# --------------------------------------------------------------------------
@app.get("/", include_in_schema=False)
def root() -> dict:
    return {
        "service": "TensorKnowledge Engine API",
        "version": SERVICE_VERSION,
        "docs": "/docs",
        "endpoints": sorted(
            {r.path for r in app.routes if getattr(r, "path", "").startswith(("/ko", "/query", "/search", "/healthz"))}
        ),
    }


@app.get("/healthz")
def healthz() -> dict:
    store = get_store()
    return {
        "status": "ok" if store.ping() else "degraded",
        "driver": store.driver,
        "reachable": store.ping(),
        "write_enabled": bool(os.environ.get("KE_API_TOKEN")),
        "version": SERVICE_VERSION,
        "time": S.now_iso(),
    }


# --------------------------------------------------------------------------
# KO CRUD
# --------------------------------------------------------------------------
@app.post("/ko", status_code=201, dependencies=[Depends(require_write_token)])
def create_ko(request: Request, body: KOCreate = Body(...)) -> dict:
    payload: dict[str, Any] = body.model_dump(exclude_none=True)
    doc = payload.pop("doc", None)
    if doc is None:
        # bare record form: strip wrapper keys, keep the record
        doc = {k: v for k, v in payload.items() if k not in ("kind", "producer", "domain", "strict")}
    kind = payload.get("kind") or S.infer_kind(doc)
    if kind not in S.KINDS:
        raise S.BadRequest(
            "cannot determine kind: pass kind=claim|evidence|provenance|review "
            "or use a tkc:/tke:/tkp:/tkr: id"
        )
    strict = bool(payload.get("strict") or os.environ.get("KE_SCHEMA_STRICT") == "1")
    _validate_record(kind, doc, strict)
    producer = _identity(request, payload.get("producer") or doc.get("created_by") or doc.get("captured_by"))
    store = get_store()
    obj = store.create_ko(kind, doc, producer, domain=payload.get("domain"))
    return obj


@app.get("/ko")
def list_ko(
    kind: Literal["claim", "evidence", "provenance", "review"] | None = None,
    axis: Literal["production", "evidence", "review", "publication"] | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    domain: str | None = None,
    limit: int = Query(default=200, ge=1, le=2000),
    offset: int = Query(default=0, ge=0),
    include_doc: bool = False,
) -> dict:
    if axis and not status_filter:
        raise HTTPException(422, "axis requires status")
    res = get_store().list_ko(kind=kind, axis=axis, status=status_filter, domain=domain,
                              limit=limit, offset=offset)
    if not include_doc:
        res["items"] = [{k: v for k, v in it.items() if k != "doc"} for it in res["items"]]
    return res


@app.get("/ko/{ko_id:path}/reviews")
def list_reviews(ko_id: str) -> dict:
    get_store().get_ko(ko_id)  # 404 if unknown
    return get_store().reviews_for(ko_id)


@app.get("/ko/{ko_id:path}")
def read_ko(ko_id: str) -> dict:
    return get_store().get_ko(ko_id)


@app.patch("/ko/{ko_id:path}", dependencies=[Depends(require_write_token)])
def patch_ko(ko_id: str, body: KOPatch, request: Request) -> dict:
    store = get_store()
    existing = store.get_ko(ko_id)
    _validate_record(existing["kind"], body.doc, os.environ.get("KE_SCHEMA_STRICT") == "1")
    return store.update_doc(ko_id, _identity(request, body.producer), body.doc)


@app.delete("/ko/{ko_id:path}", status_code=204, dependencies=[Depends(require_write_token)])
def delete_ko(ko_id: str, request: Request, body: Publisher | None = None) -> None:
    producer = body.producer if body else None
    get_store().delete_ko(ko_id, _identity(request, producer))


@app.post("/ko/{ko_id:path}/submit", dependencies=[Depends(require_write_token)])
def submit_ko(ko_id: str, request: Request, body: Publisher | None = None) -> dict:
    producer = body.producer if body else None
    return get_store().submit(ko_id, _identity(request, producer))


@app.post("/ko/{ko_id:path}/review", dependencies=[Depends(require_write_token)])
def review_ko(ko_id: str, body: ReviewIn, request: Request) -> dict:
    reviewer_id, reviewer_type = _reviewer_id(body.reviewer)
    reviewed_at = body.reviewed_at or S.now_iso()
    event_id = body.id or "tkr:ke:%d-%s" % (int(time.time() * 1000), secrets.token_hex(4))
    event = {
        "id": event_id,
        "object_ref": ko_id,
        "decision": body.decision,
        "reviewer": {"id": reviewer_id, "reviewer_type": reviewer_type},
        "reviewed_at": reviewed_at,
        "policy_version": body.policy_version,
        "rationale": body.rationale,
        "findings": body.findings,
    }
    event = {k: v for k, v in event.items() if v is not None}
    _validate_record("review", event, strict=os.environ.get("KE_SCHEMA_STRICT") == "1")
    applied = get_store().record_review(
        ko_id,
        {"id": event_id, "reviewer": reviewer_id, "decision": body.decision,
         "reviewed_at": reviewed_at, "doc": event},
    )
    return {"object": applied, "event": event}


@app.post("/ko/{ko_id:path}/publish", dependencies=[Depends(require_write_token)])
def publish_ko(ko_id: str) -> dict:
    """Publication is gated by an approved review, not by producer identity."""
    return get_store().publish(ko_id)


# --------------------------------------------------------------------------
# six query classes
# --------------------------------------------------------------------------
@app.get("/query/by-status")
def q_by_status(
    axis: Literal["production", "evidence", "review", "publication"],
    status_value: str = Query(alias="status"),
    kind: Literal["claim", "evidence", "provenance", "review"] | None = None,
) -> dict:
    return get_store().by_status(axis, status_value, kind)


@app.get("/query/by-evidence-relation")
def q_by_relation(
    relation: Literal["supports", "refutes", "qualifies", "contextualizes", "mentions", "derived-from"],
) -> dict:
    return get_store().by_evidence_relation(relation)


@app.get("/query/chain")
def q_chain(claim_id: str) -> dict:
    return get_store().provenance_chain(claim_id)


@app.get("/query/by-domain")
def q_by_domain(domain: str, exact: bool = False, kind: str = "claim") -> dict:
    return get_store().claims_by_domain(domain, exact=exact, kind=kind)


@app.get("/query/claim-evidence")
def q_claim_evidence(claim_id: str) -> dict:
    return get_store().evidence_for_claim(claim_id)


@app.get("/query/stats")
def q_stats() -> dict:
    return get_store().stats()


@app.get("/search")
def search(
    q: str = Query(min_length=1),
    kind: Literal["claim", "evidence", "provenance", "review"] | None = None,
    domain: str | None = None,
    axis: Literal["production", "evidence", "review", "publication"] | None = None,
    status_value: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
) -> dict:
    if axis and not status_value:
        raise HTTPException(422, "axis requires status")
    return get_store().search(q, kind=kind, domain=domain, axis=axis, status=status_value, limit=limit)