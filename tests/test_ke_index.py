"""Tests for the four-dimension retrieval projection + consumption meter.

Covers KBM-TKC-INDEX-API deliverables ①②③:

* ① ``ke.facets.project_doc`` derivation rules (concept/problem/method/evidence)
* ② ``/by-concept`` … ``/facets`` endpoints + optional read auth
* ③ inject/cite ledger feeding KPI-KB-REUSE-RATE (idempotent cités)
"""
from __future__ import annotations

import os
import socket
import threading
import time

import httpx
import pytest
import uvicorn

TOKEN = "test-token-index"


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _claim(cid="tkc:idx:alpha", **over):
    rec = {
        "id": cid,
        "statement": "Plane Poiseuille flow has a parabolic velocity profile.",
        "claim_type": "descriptive",
        "scope": {"domain": "lattice-Boltzmann-method", "system": "unit-test"},
        "epistemic_status": "established",
        "evidence_refs": ["tke:idx:alpha-src"],
        "created_at": "2026-11-12T00:00:00Z",
        "created_by": "agent-index",
        "version": "1.0.0",
        "notes": ["TensorLBM service: verify the magic relaxation time before reuse."],
    }
    rec.update(over)
    return rec


def _evidence(eid="tke:idx:alpha-src", **over):
    rec = {
        "id": eid,
        "claim_refs": ["tkc:idx:alpha"],
        "source": {"source_type": "code", "citation": "analysis/poiseuille.py"},
        "relation": "supports",
        "locator": {"locator_type": "code-location", "value": "poiseuille.py:24"},
        "extraction_method": "direct-quotation",
        "captured_at": "2026-11-12T00:00:00Z",
        "assessment_status": "reviewed-supports",
        "version": "1.0.0",
    }
    rec.update(over)
    return rec


@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    dsn = "sqlite:" + str(tmp_path_factory.mktemp("keidx") / "ke.db")
    os.environ["KE_DSN"] = dsn
    os.environ["KE_API_TOKEN"] = TOKEN

    from ke import api as api_mod
    from ke import apistore as S

    S.Store(dsn).ensure_schema()
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(api_mod.app, host="127.0.0.1", port=port,
                                           log_level="warning"))
    th = threading.Thread(target=server.run, daemon=True)
    th.start()
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
    th.join(timeout=10)


@pytest.fixture()
def clean(base_url):
    from ke import apistore as S

    store = S.Store(os.environ["KE_DSN"])
    with store.connect(write=True) as conn:
        for table in ("ke_usage", "ke_facet", "ke_edge", "ke_review", "ke_ko"):
            conn.execute(f"DELETE FROM {table}")
    return base_url


@pytest.fixture()
def client(clean):
    with httpx.Client(base_url=clean, timeout=10) as c:
        yield c


def _seed(client):
    h = {"Authorization": f"Bearer {TOKEN}"}
    assert client.post("/ko", json={"kind": "claim", "producer": "agent-index",
                                    "doc": _claim()}, headers=h).status_code == 201
    assert client.post("/ko", json={"kind": "evidence", "producer": "agent-index",
                                    "doc": _evidence()}, headers=h).status_code == 201


# ---------------------------------------------------------------- projection
def test_project_doc_four_dimensions():
    from ke import facets

    rows = facets.project_doc("claim", _claim())
    got = {(r["dim"], r["value"]) for r in rows}
    assert ("concept", "lattice-boltzmann-method") in got          # scope.domain
    assert ("concept", "unit-test") in got                         # scope.system
    assert ("evidence", "tke:idx:alpha-src") in got                # evidence_refs
    assert any(d == "problem" and "magic" in v for d, v in got)  # notes token
    # statement tokens reach concept at lower weight
    w = {(r["dim"], r["value"]): r["weight"] for r in rows}
    assert w[("concept", "lattice-boltzmann-method")] > w[("concept", "poiseuille")]

    ev = facets.project_doc("evidence", _evidence())
    got_ev = {(r["dim"], r["value"]) for r in ev}
    assert ("method", "direct-quotation") in got_ev
    assert ("method", "code") in got_ev
    assert ("evidence", "supports") in got_ev
    assert ("evidence", "reviewed-supports") in got_ev


def test_hypothesis_statement_feeds_problem_dimension():
    from ke import facets

    doc = _claim(claim_type="hypothesis",
                 statement="Exactness of the bounce-back solution is width dependent.")
    rows = {(r["dim"], r["value"]) for r in facets.project_doc("claim", doc)}
    assert ("problem", "unresolved:hypothesis") in rows
    assert ("problem", "exactness") in rows


def test_explicit_facets_override_weight():
    from ke import facets

    doc = _claim(facets={"concept": ["magic-tau"], "problem": ["wall-offset"]})
    rows = {(r["dim"], r["value"]): r["weight"] for r in facets.project_doc("claim", doc)}
    assert rows[("concept", "magic-tau")] == facets.WEIGHTS["explicit"]
    assert rows[("problem", "wall-offset")] == facets.WEIGHTS["explicit"]


# ------------------------------------------------------------------ endpoints
def test_by_concept_returns_matched_facets(client):
    _seed(client)
    r = client.get("/by-concept", params={"concept": "poiseuille"})
    assert r.status_code == 200
    body = r.json()
    assert body["dim"] == "concept" and body["total"] == 1
    item = body["items"][0]
    assert item["id"] == "tkc:idx:alpha"
    assert any("poiseuille" in m["value"] for m in item["matched"])
    assert item["statement"].startswith("Plane Poiseuille")


def test_by_problem_reads_notes(client):
    _seed(client)
    r = client.get("/by-problem", params={"problem": "magic relaxation"})
    body = r.json()
    assert body["total"] == 1 and body["items"][0]["id"] == "tkc:idx:alpha"


def test_by_evidence_exact_id_and_relation(client):
    _seed(client)
    # claim found from the evidence id it cites
    r = client.get("/by-evidence", params={"evidence": "tke:idx:alpha-src"})
    assert {it["id"] for it in r.json()["items"]} >= {"tkc:idx:alpha"}
    # evidence object found by relation facet
    r = client.get("/by-evidence", params={"evidence": "supports", "kind": "evidence"})
    assert r.json()["items"][0]["id"] == "tke:idx:alpha-src"


def test_by_method_follows_claim_evidence_edge(client):
    _seed(client)
    r = client.get("/by-method", params={"method": "direct-quotation", "kind": "claim"})
    body = r.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "tkc:idx:alpha"   # via evidence edge
    assert any(m["field"] == "extraction_method" for m in body["items"][0]["matched"])


def test_facets_browse_counts(client):
    _seed(client)
    r = client.get("/facets", params={"dim": "concept", "q": "lattice"})
    body = r.json()
    assert body["count"] >= 1
    row = next(v for v in body["values"] if v["value"] == "lattice-boltzmann-method")
    assert row["objects"] == 1


def test_index_rebuild_is_idempotent(client):
    _seed(client)
    h = {"Authorization": f"Bearer {TOKEN}"}
    before = client.get("/by-concept", params={"concept": "poiseuille"}).json()["total"]
    assert client.post("/index/rebuild", headers=h).status_code == 200
    after = client.get("/by-concept", params={"concept": "poiseuille"}).json()["total"]
    assert before == after == 1


# --------------------------------------------------------- consumption meter
def test_injection_then_citation_reuse_kpi(client):
    _seed(client)
    r = client.get("/by-concept", params={"concept": "poiseuille", "log": "true",
                                          "mission_id": 15722, "consumer": "agent-test"})
    assert r.json()["injection"]["n"] == 1
    # injected only -> rate 0
    stats = client.get("/usage/stats").json()
    assert stats["injected_objects"] == 1 and stats["cited_objects"] == 0
    assert stats["kpi_kb_reuse_rate"] == 0.0

    h = {"Authorization": f"Bearer {TOKEN}", "X-KE-Agent": "agent-test"}
    body = {"mission_id": 15722, "artifact": "runs/m15722/case1.json"}
    c = client.post("/ko/tkc:idx:alpha/cite", json=body, headers=h)
    assert c.status_code == 200 and c.json()["duplicate"] is False
    # idempotent per (ko, mission, artifact)
    c2 = client.post("/ko/tkc:idx:alpha/cite", json=body, headers=h)
    assert c2.json()["duplicate"] is True

    stats = client.get("/usage/stats").json()
    assert stats["cited_objects"] == 1
    assert stats["kpi_kb_reuse_rate"] == 1.0
    assert stats["missions"][0]["mission_id"] == 15722

    usage = client.get("/ko/tkc:idx:alpha/usage").json()
    assert usage["injected"] == 1 and usage["cited"] == 1
    assert usage["distinct_artifacts"] == 1
    assert any(e["artifact"] == "runs/m15722/case1.json" for e in usage["events"])


def test_cite_unknown_object_is_404(client):
    h = {"Authorization": f"Bearer {TOKEN}"}
    r = client.post("/ko/tkc:none:missing/cite", json={}, headers=h)
    assert r.status_code == 404


def test_read_auth_can_be_enabled(clean, monkeypatch):
    monkeypatch.setenv("KE_REQUIRE_READ_AUTH", "1")
    monkeypatch.setenv("KE_READ_TOKEN", "read-secret")
    with httpx.Client(base_url=clean, timeout=10) as c:
        assert c.get("/by-concept", params={"concept": "x"}).status_code == 401
        ok = c.get("/by-concept", params={"concept": "x"},
                   headers={"Authorization": "Bearer read-secret"})
        assert ok.status_code == 200
    monkeypatch.delenv("KE_REQUIRE_READ_AUTH")
    monkeypatch.delenv("KE_READ_TOKEN")