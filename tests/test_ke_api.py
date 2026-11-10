"""Endpoint tests for the KE HTTP service (``ke/api.py``).

The suite talks to a *real* uvicorn server (started in a thread on an ephemeral
port) over HTTP, so routing, auth, transaction and concurrency behaviour are
exercised end to end rather than through an in-process shortcut.

Backing store: a throw-away SQLite file by default (works anywhere), or any
DSN in ``KE_TEST_DSN`` — e.g.

    KE_TEST_DSN='postgresql:///ke_m8801?user=postgres' pytest tests/test_ke_api.py

so the same assertions cover the Postgres transaction path.
"""
from __future__ import annotations

import os
import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
import pytest
import uvicorn

TOKEN = "test-token-m8801"
PKG = Path(__file__).resolve().parents[1] / "knowledge" / "oss-lbm"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _claim(cid: str = "tkc:test:alpha", **over) -> dict:
    rec = {
        "id": cid,
        "statement": "LBM on a D2Q9 lattice reproduces the Navier-Stokes limit at second order.",
        "claim_type": "descriptive",
        "scope": {"domain": "lattice-Boltzmann-method", "system": "unit-test"},
        "modality": "asserted",
        "epistemic_status": "well-supported",
        "evidence_refs": ["tke:test:alpha-src"],
        "created_at": "2026-11-09T00:00:00Z",
        "created_by": "agent-producer",
        "version": "1.0.0",
        "notes": ["concurrency and auth probes"],
    }
    rec.update(over)
    return rec


def _evidence(eid: str = "tke:test:alpha-src", claim_refs: list[str] | None = None,
              relation: str = "supports") -> dict:
    return {
        "id": eid,
        "claim_refs": claim_refs if claim_refs is not None else ["tkc:test:alpha"],
        "source": {
            "source_type": "code",
            "citation": "lattice_boltzmann/kernel.py",
            "url": "https://example.invalid/repo",
        },
        "relation": relation,
        "locator": {"locator_type": "code-location", "value": "kernel.py:1-20"},
        "captured_at": "2026-11-09T00:00:00Z",
        "assessment_status": "reviewed-supports",
        "version": "1.0.0",
    }


@pytest.fixture(scope="session")
def base_url(tmp_path_factory) -> str:
    dsn = os.environ.get("KE_TEST_DSN") or (
        "sqlite:" + str(tmp_path_factory.mktemp("keapi") / "ke.db")
    )
    os.environ["KE_DSN"] = dsn
    os.environ["KE_API_TOKEN"] = TOKEN

    from ke import api as api_mod
    from ke import apistore as S

    store = S.Store(dsn)
    store.ensure_schema()

    port = _free_port()
    server = uvicorn.Server(
        uvicorn.Config(api_mod.app, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{port}"
    for _ in range(200):
        try:
            if httpx.get(f"{url}/healthz", timeout=0.5).status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.05)
    else:  # pragma: no cover
        raise RuntimeError("uvicorn did not start")
    yield url
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture()
def clean(base_url):
    """Empty every table before each test (server keeps running)."""
    from ke import apistore as S

    store = S.Store(os.environ["KE_DSN"])
    with store.connect(write=True) as conn:
        for table in ("ke_edge", "ke_review", "ke_ko"):
            conn.execute(f"DELETE FROM {table}")
    return base_url


@pytest.fixture()
def client(clean):
    with httpx.Client(base_url=clean, timeout=30.0) as c:
        c.headers["Authorization"] = f"Bearer {TOKEN}"
        c.headers["X-KE-Agent"] = "agent-producer"
        yield c


# ---------------------------------------------------------------- ops / auth
def test_healthz_is_open_and_reports_driver(base_url):
    res = httpx.get(f"{base_url}/healthz", timeout=5)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok" and body["reachable"] is True
    assert body["driver"] in ("postgres", "sqlite")
    assert body["write_enabled"] is True


def test_write_without_token_is_401(client):
    res = client.post("/ko", json={"kind": "claim", "doc": _claim()},
                      headers={"Authorization": ""})
    assert res.status_code == 401
    res = client.post("/ko", json={"kind": "claim", "doc": _claim()},
                      headers={"Authorization": "Bearer wrong-token"})
    assert res.status_code == 401
    assert client.get("/ko").json()["total"] == 0


def test_write_disabled_when_token_unset(client, monkeypatch):
    monkeypatch.delenv("KE_API_TOKEN")
    res = client.post("/ko", json={"kind": "claim", "doc": _claim()})
    assert res.status_code == 503
    assert "KE_API_TOKEN" in res.json()["detail"]


# ------------------------------------------------------------------- create
def test_create_and_read_claim_roundtrip(client):
    res = client.post("/ko", json={"kind": "claim", "producer": "agent-producer",
                                   "doc": _claim()})
    assert res.status_code == 201, res.text
    obj = res.json()
    assert obj["id"] == "tkc:test:alpha"
    assert obj["production_status"] == "draft"
    assert obj["review_status"] == "unreviewed"
    assert obj["publication_status"] == "private"
    assert obj["evidence_status"] == "well-supported"
    assert obj["domain"] == "lattice-Boltzmann-method"

    got = client.get("/ko/tkc:test:alpha")
    assert got.status_code == 200
    assert got.json()["doc"] == _claim()          # exact ingested bytes


def test_duplicate_create_is_409(client):
    assert client.post("/ko", json={"kind": "claim", "doc": _claim()}).status_code == 201
    res = client.post("/ko", json={"kind": "claim", "doc": _claim()})
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


def test_bare_record_body_is_accepted(client):
    res = client.post("/ko", json=_evidence())
    assert res.status_code == 201, res.text
    assert res.json()["kind"] == "evidence"


def test_invalid_record_is_422(client):
    bad = _claim()
    bad.pop("epistemic_status")
    assert client.post("/ko", json={"kind": "claim", "doc": bad}).status_code == 422
    wrong_prefix = _claim(cid="tke:test:not-a-claim")
    res = client.post("/ko", json={"kind": "claim", "doc": wrong_prefix})
    assert res.status_code == 422
    assert "prefix" in res.json()["detail"]


def test_missing_producer_identity_is_422(clean):
    with httpx.Client(base_url=clean, timeout=10) as c:
        c.headers["Authorization"] = f"Bearer {TOKEN}"
        doc = _claim()
        doc.pop("created_by")
        res = c.post("/ko", json={"kind": "claim", "doc": doc})
    assert res.status_code == 422
    assert "producer" in res.json()["detail"]


# ------------------------------------------------------- review / publication
def test_producer_cannot_review_own_object(client):
    client.post("/ko", json={"kind": "claim", "producer": "agent-producer", "doc": _claim()})
    res = client.post("/ko/tkc:test:alpha/review",
                      json={"decision": "approve",
                            "reviewer": {"id": "agent-producer", "reviewer_type": "agent"}})
    assert res.status_code == 403
    assert "may not review" in res.json()["detail"]
    obj = client.get("/ko/tkc:test:alpha").json()
    assert obj["review_status"] == "unreviewed"
    assert obj["publication_status"] == "private"
    assert client.get("/ko/tkc:test:alpha/reviews").json()["count"] == 0


def test_review_approve_then_publish(client):
    client.post("/ko", json={"kind": "claim", "doc": _claim()})
    res = client.post("/ko/tkc:test:alpha/review",
                      json={"decision": "approve",
                            "reviewer": {"id": "agent-reviewer", "reviewer_type": "agent"},
                            "rationale": "source inspected"})
    assert res.status_code == 200, res.text
    assert res.json()["object"]["review_status"] == "approved"
    assert res.json()["event"]["id"].startswith("tkr:ke:")

    # publishing is review-gated, not identity-gated: no X-KE-Agent needed
    pub = client.post("/ko/tkc:test:alpha/publish", headers={"X-KE-Agent": ""})
    assert pub.status_code == 200
    assert pub.json()["publication_status"] == "published"
    assert pub.json()["review_status"] == "approved"

    log = client.get("/ko/tkc:test:alpha/reviews").json()
    assert log["count"] == 1 and log["items"][0]["decision"] == "approve"


def test_publish_requires_approval(client):
    client.post("/ko", json={"kind": "claim", "doc": _claim()})
    res = client.post("/ko/tkc:test:alpha/publish")
    assert res.status_code == 409
    assert "need approved" in res.json()["detail"]


def test_revoke_retracts_published_object(client):
    client.post("/ko", json={"kind": "claim", "doc": _claim()})
    client.post("/ko/tkc:test:alpha/review",
                json={"decision": "approve", "reviewer": "agent-reviewer"})
    assert client.post("/ko/tkc:test:alpha/publish").json()["publication_status"] == "published"
    res = client.post("/ko/tkc:test:alpha/review",
                      json={"decision": "revoke", "reviewer": "agent-reviewer",
                            "rationale": "locator no longer resolves"})
    assert res.status_code == 200
    obj = res.json()["object"]
    assert obj["review_status"] == "revoked"
    assert obj["publication_status"] == "retracted"
    assert client.get("/ko").json()["items"][0]["review_status"] == "revoked"


def test_four_states_move_independently(client):
    """production != evidence != review != publication."""
    client.post("/ko", json={"kind": "claim", "doc": _claim()})
    sub = client.post("/ko/tkc:test:alpha/submit")
    assert sub.status_code == 200
    obj = sub.json()
    assert obj["production_status"] == "submitted"
    assert obj["review_status"] == "unreviewed"
    assert obj["evidence_status"] == "well-supported"
    assert obj["publication_status"] == "private"
    # submitted objects are frozen for editing
    assert client.patch("/ko/tkc:test:alpha", json={"doc": _claim()}).status_code == 409


def test_patch_frozen_after_review(client):
    """A producer must not edit an approved document and then publish it."""
    client.post("/ko", json={"kind": "claim", "doc": _claim()})
    assert client.post("/ko/tkc:test:alpha/review",
                       json={"decision": "approve", "reviewer": "agent-reviewer"}).status_code == 200
    res = client.patch("/ko/tkc:test:alpha", json={"doc": _claim(statement="post-review edit")})
    assert res.status_code == 409
    assert "reviewed objects are frozen" in res.json()["detail"]
    assert client.get("/ko/tkc:test:alpha").json()["doc"]["statement"] == _claim()["statement"]


def test_review_event_id_cannot_be_replayed(client):
    client.post("/ko", json={"kind": "claim", "doc": _claim()})
    body = {"decision": "approve", "reviewer": "agent-reviewer", "id": "tkr:test:evt-1"}
    assert client.post("/ko/tkc:test:alpha/review", json=body).status_code == 200
    replay = client.post("/ko/tkc:test:alpha/review", json={**body, "decision": "revoke"})
    assert replay.status_code == 409
    assert "already used" in replay.json()["detail"]
    obj = client.get("/ko/tkc:test:alpha").json()
    assert obj["review_status"] == "approved" and obj["publication_status"] == "private"
    assert client.get("/ko/tkc:test:alpha/reviews").json()["count"] == 1


def test_patch_and_delete_draft(client):
    client.post("/ko", json={"kind": "claim", "doc": _claim()})
    updated = _claim(statement="revised statement")
    res = client.patch("/ko/tkc:test:alpha", json={"doc": updated})
    assert res.status_code == 200
    assert client.get("/ko/tkc:test:alpha").json()["doc"]["statement"] == "revised statement"
    assert client.delete("/ko/tkc:test:alpha").status_code == 204
    assert client.get("/ko/tkc:test:alpha").status_code == 404


# ------------------------------------------------------------- query surface
@pytest.fixture()
def seeded(client):
    client.post("/ko", json={"kind": "claim", "doc": _claim()})
    client.post("/ko", json={"kind": "evidence", "doc": _evidence()})
    client.post("/ko", json={"kind": "evidence",
                             "doc": _evidence("tke:test:alpha-refutes",
                                              claim_refs=["tkc:test:alpha"],
                                              relation="refutes")})
    client.post("/ko", json={"kind": "claim",
                             "doc": _claim("tkc:test:beta",
                                           statement="Thermal LBM needs a separate field.",
                                           epistemic_status="provisional",
                                           scope={"domain": "thermal-lbm", "system": "unit-test"},
                                           evidence_refs=[])})
    client.post("/ko", json={"kind": "provenance", "doc": {
        "id": "tkp:test:ingest",
        "generated_entity": {"id": "knowledge/oss-lbm", "entity_type": "knowledge-object",
                             "version": "1.0.0"},
        "activity": {"id": "act-1", "activity_type": "extraction",
                     "started_at": "2026-11-09T00:00:00Z"},
        "agents": [{"id": "agent-producer", "agent_type": "software-agent"}],
        "derived_from": ["tkc:test:alpha"],
        "recorded_at": "2026-11-09T00:00:00Z",
        "version": "1.0.0",
    }})
    return client


def test_q1_by_status(seeded):
    res = seeded.get("/query/by-status", params={"axis": "evidence", "status": "provisional"})
    assert res.status_code == 200
    body = res.json()
    assert body["count"] == 1 and body["items"][0]["id"] == "tkc:test:beta"
    assert seeded.get("/query/by-status",
                      params={"axis": "review", "status": "unreviewed"}).json()["count"] == 5


def test_q2_by_evidence_relation(seeded):
    body = seeded.get("/query/by-evidence-relation", params={"relation": "refutes"}).json()
    assert body["count"] == 1
    assert body["items"][0]["evidence_id"] == "tke:test:alpha-refutes"
    assert body["items"][0]["claim_id"] == "tkc:test:alpha"
    sup = seeded.get("/query/by-evidence-relation", params={"relation": "supports"}).json()
    assert sup["count"] == 1 and sup["items"][0]["assessment_status"] == "reviewed-supports"


def test_q3_provenance_chain(seeded):
    body = seeded.get("/query/chain", params={"claim_id": "tkc:test:alpha"}).json()
    assert body["claim"]["id"] == "tkc:test:alpha"
    assert {l["evidence_id"] for l in body["links"]} == {
        "tke:test:alpha-src", "tke:test:alpha-refutes"}
    assert body["links"][0]["source"]["citation"]
    assert [p["provenance_id"] for p in body["provenance"]] == ["tkp:test:ingest"]
    assert body["complete"] is True
    assert seeded.get("/query/chain", params={"claim_id": "tkc:test:nope"}).status_code == 404


def test_q3_reports_package_level_provenance_separately(client):
    client.post("/ko", json={"kind": "claim", "doc": _claim("tkc:oss-lbm:pkg-claim",
                                                           evidence_refs=[])})
    client.post("/ko", json={"kind": "provenance", "doc": {
        "id": "tkp:oss-lbm:pkg-ingest",
        "generated_entity": {"id": "knowledge/oss-lbm", "entity_type": "knowledge-object",
                             "version": "1.0.0"},
        "activity": {"id": "act-2", "activity_type": "extraction",
                     "started_at": "2026-11-09T00:00:00Z"},
        "agents": [{"id": "agent-producer", "agent_type": "software-agent"}],
        "recorded_at": "2026-11-09T00:00:00Z",
        "version": "1.0.0",
    }})
    body = client.get("/query/chain", params={"claim_id": "tkc:oss-lbm:pkg-claim"}).json()
    # no per-claim provenance record exists -> chain provenance stays empty
    assert body["provenance"] == []
    # the package-level record is surfaced, clearly labelled
    assert [p["provenance_id"] for p in body["package_provenance"]] == ["tkp:oss-lbm:pkg-ingest"]
    assert body["package_provenance"][0]["match"] == "package-namespace"


def test_q4_by_domain(seeded):
    exact = seeded.get("/query/by-domain",
                       params={"domain": "lattice-Boltzmann-method", "exact": True}).json()
    assert exact["count"] == 1 and exact["items"][0]["id"] == "tkc:test:alpha"
    # substring (case-insensitive) matching, on either side of the hyphen
    boltz = seeded.get("/query/by-domain", params={"domain": "BOLTZMANN"}).json()
    assert boltz["count"] == 1 and boltz["items"][0]["id"] == "tkc:test:alpha"
    lbm = seeded.get("/query/by-domain", params={"domain": "lbm"}).json()
    assert lbm["count"] == 1 and lbm["items"][0]["id"] == "tkc:test:beta"


def test_q5_claim_evidence(seeded):
    body = seeded.get("/query/claim-evidence", params={"claim_id": "tkc:test:alpha"}).json()
    assert body["count"] == 2
    assert {i["relation"] for i in body["items"]} == {"supports", "refutes"}
    assert body["dangling_evidence_refs"] == []
    # a claim pointing at evidence that was never ingested stays visible
    body2 = seeded.get("/query/claim-evidence", params={"claim_id": "tkc:test:beta"}).json()
    assert body2["count"] == 0 and body2["items"] == []


def test_q6_stats(seeded):
    body = seeded.get("/query/stats").json()
    assert body["objects"] == 5
    assert body["by_kind"] == {"claim": 2, "evidence": 2, "provenance": 1}
    assert body["edges"] == 3
    assert body["review_events"] == 0
    assert body["publication_status"] == {"private": 5}
    assert body["evidence_status"]["provisional"] == 1


def test_search_text_domain_and_status_filters(seeded):
    all_hits = seeded.get("/search", params={"q": "lattice"}).json()
    assert all_hits["count"] >= 2
    narrowed = seeded.get("/search",
                          params={"q": "thermal", "domain": "thermal-lbm"}).json()
    assert narrowed["count"] == 1
    assert narrowed["items"][0]["id"] == "tkc:test:beta"
    # domain filter alone must exclude the other domain
    assert seeded.get("/search",
                      params={"q": "lattice", "domain": "thermal-lbm"}).json()["count"] == 0
    by_status = seeded.get("/search",
                           params={"q": "lattice", "axis": "evidence",
                                   "status": "well-supported"}).json()
    assert [i["id"] for i in by_status["items"]] == ["tkc:test:alpha"]
    assert "snippet" in by_status["items"][0]
    # case-insensitive on both engines
    assert seeded.get("/search", params={"q": "LATTICE"}).json()["count"] == all_hits["count"]


# ---------------------------------------------------------------- concurrency
def test_concurrent_distinct_writes(client):
    def create(i: int) -> int:
        with httpx.Client(base_url=str(client.base_url), timeout=30) as c:
            c.headers["Authorization"] = f"Bearer {TOKEN}"
            c.headers["X-KE-Agent"] = "agent-producer"
            return c.post("/ko", json={"kind": "claim",
                                       "doc": _claim(f"tkc:test:c{i:03d}")}).status_code

    with ThreadPoolExecutor(max_workers=12) as pool:
        codes = list(pool.map(create, range(24)))
    assert codes.count(201) == 24, codes
    stats = client.get("/query/stats").json()
    assert stats["objects"] == 24
    assert stats["by_kind"] == {"claim": 24}


def test_concurrent_same_id_has_one_winner(client):
    def create(_i: int) -> int:
        with httpx.Client(base_url=str(client.base_url), timeout=30) as c:
            c.headers["Authorization"] = f"Bearer {TOKEN}"
            c.headers["X-KE-Agent"] = "agent-producer"
            return c.post("/ko", json={"kind": "claim", "doc": _claim()}).status_code

    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(create, range(10)))
    assert codes.count(201) == 1, codes
    assert codes.count(409) == 9, codes
    assert client.get("/query/stats").json()["objects"] == 1


# --------------------------------------------------------------- real package
def test_smoke_real_oss_lbm_package(client):
    """Ingest the real knowledge/oss-lbm package and run all six queries."""
    from ke.ingest_client import ingest_package

    assert PKG.is_dir(), PKG
    out = ingest_package(str(client.base_url), TOKEN, PKG, "agent-m8801",
                         client=client)
    assert out["counts"]["failed"] == 0, out["failures"][:3]
    assert out["counts"]["created"] >= 50

    stats = client.get("/query/stats").json()
    assert stats["objects"] == out["counts"]["created"]
    assert stats["by_kind"]["claim"] >= 30 and stats["by_kind"]["evidence"] >= 30
    assert stats["edges"] > 50

    # Q1 by status, Q2 by relation, Q4 by domain, Q6 stats on real data
    established = client.get("/query/by-status",
                             params={"axis": "evidence", "status": "established"}).json()
    assert established["count"] >= 1
    supports = client.get("/query/by-evidence-relation", params={"relation": "supports"}).json()
    assert supports["count"] >= 1
    domain = client.get("/query/by-domain", params={"domain": "lattice-Boltzmann-method"}).json()
    assert domain["count"] >= 1

    # Q3 + Q5 on a claim that actually exists in the package
    claim_id = stats and client.get("/ko", params={"kind": "claim", "limit": 1}).json()["items"][0]["id"]
    chain = client.get("/query/chain", params={"claim_id": claim_id}).json()
    assert chain["claim"]["id"] == claim_id
    assert chain["links"], "expected at least one evidence link for %s" % claim_id
    ce = client.get("/query/claim-evidence", params={"claim_id": claim_id}).json()
    assert ce["count"] >= 1
    assert client.get("/search", params={"q": "lattice"}).json()["count"] >= 1