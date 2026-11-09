"""KE prototype — reproducibility & consistency tests (m8620).

Ground truth = the m8554 epistemic pilot package
(platform-test/epistemic-benchmark/pilots/m8554/). Every expected value
below is pinned from the pilot records themselves; the tests prove the
SQLite-backed query layer reproduces them exactly, and that the KE's
xref invariants match the semantics of pilots/m8554/validate_pilot.py.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PILOT = REPO / "platform-test" / "epistemic-benchmark" / "pilots" / "m8554"

sys.path.insert(0, str(REPO))
from ke import queries as q  # noqa: E402
from ke import store, validate  # noqa: E402


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def conn(tmp_path_factory):
    db = tmp_path_factory.mktemp("ke") / "ke.db"
    c = store.connect(db)
    store.ingest_pilot(PILOT, c)
    yield c
    c.close()


# ------------------------------------------------------------------ ingest
def test_ingest_counts(conn):
    s = q.stats(conn)
    assert s["claims"] == 4
    assert s["evidence"] == 8
    assert s["provenance"] == 3
    assert s["claim_evidence_edges"] == 8
    assert s["evidence_claims_edges"] == 8


def test_raw_record_traceability(conn):
    """raw_json must round-trip to the exact source document (zero hand-copy)."""
    src = json.loads(
        (PILOT / "claims" / "tkc-fair-requires-open-access.json").read_text(encoding="utf-8")
    )
    assert q.raw_record(conn, "claims", "tkc:fair:requires-open-access") == src


# ------------------------------------------------- Q1: by epistemic_status
def test_q1_claims_by_status(conn):
    expected = {
        "established": ["tkc:prov-o:wasattributedto-signature"],
        "well-supported": ["tkc:fair:a1-protocol-conditions"],
        "contested": ["tkc:fair:requires-open-access"],
        "not-assessed": ["tkc:tkrepo:rocrate-export-production"],
    }
    for status, ids in expected.items():
        got = [c["id"] for c in q.claims_by_status(conn, status)]
        assert got == ids, status
    assert q.claims_by_status(conn, "speculative") == []


# --------------------------------------------- Q2: by evidence relation
def test_q2_evidence_by_relation(conn):
    expected = {
        "supports": ["tke:fair:a1-block", "tke:prov-o:entry6-wasattributedto"],
        "refutes": ["tke:fair:a1-2-auth-protocol"],
        "qualifies": ["tke:fair:r1-1-license"],
        "contextualizes": [
            "tke:fair:preamble-machine-actionability",
            "tke:prov-o:section31-agent-responsibility",
            "tke:ro-crate:root-data-entity-must",
        ],
        "mentions": ["tke:tkrepo:standards-mapping-p0"],
    }
    for rel, ids in expected.items():
        got = [e["id"] for e in q.evidence_by_relation(conn, rel)]
        assert got == ids, rel
    assert q.evidence_by_relation(conn, "derived-from") == []


# ------------------------------------- Q3: provenance chain claim->ev->src
def test_q3_provenance_chain_scientific(conn):
    chain = q.provenance_chain(conn, "tkc:prov-o:wasattributedto-signature")
    assert chain["claim"]["epistemic_status"] == "established"
    assert [l["evidence_id"] for l in chain["links"]] == [
        "tke:prov-o:entry6-wasattributedto",
        "tke:prov-o:section31-agent-responsibility",
    ]
    assert chain["links"][0]["relation"] == "supports"
    assert chain["links"][1]["relation"] == "contextualizes"
    for l in chain["links"]:
        assert l["source"]["url"] == "https://www.w3.org/TR/prov-o/"
        assert l["source"]["persistent_id"] == "http://www.w3.org/TR/2013/REC-prov-o-20130430/"
        assert l["locator"]["quote"]  # non-empty direct quotation
    # chain must agree with the claim's own evidence_refs
    refs = json.loads(
        conn.execute(
            "SELECT evidence_refs_json FROM claims WHERE id=?",
            ("tkc:prov-o:wasattributedto-signature",),
        ).fetchone()[0]
    )
    assert sorted(l["evidence_id"] for l in chain["links"]) == sorted(refs)


def test_q3_provenance_chain_contested(conn):
    chain = q.provenance_chain(conn, "tkc:fair:requires-open-access")
    rels = {l["evidence_id"]: l["relation"] for l in chain["links"]}
    assert rels == {
        "tke:fair:a1-2-auth-protocol": "refutes",
        "tke:fair:preamble-machine-actionability": "contextualizes",
        "tke:fair:r1-1-license": "qualifies",
    }
    with pytest.raises(KeyError):
        q.provenance_chain(conn, "tkc:does-not-exist")


# ------------------------------------------------------- Q4: by domain
def test_q4_claims_by_domain(conn):
    fair = [c["id"] for c in q.claims_by_domain(conn, "research data stewardship principles")]
    assert fair == [
        "tkc:fair:a1-protocol-conditions",
        "tkc:fair:requires-open-access",
    ]
    prov = [
        c["id"]
        for c in q.claims_by_domain(conn, "provenance standards / ontology specification text")
    ]
    assert prov == ["tkc:prov-o:wasattributedto-signature"]
    assert q.claims_by_domain(conn, "no-such-domain") == []
    # substring mode finds the same FAIR pair
    sub = [c["id"] for c in q.claims_by_domain(conn, "stewardship", exact=False)]
    assert sub == fair


# ------------------------------------------------- Q5: evidence for claim
def test_q5_evidence_for_claim(conn):
    ev = q.evidence_for_claim(conn, "tkc:fair:requires-open-access")
    assert {e["id"]: e["relation"] for e in ev} == {
        "tke:fair:a1-2-auth-protocol": "refutes",
        "tke:fair:preamble-machine-actionability": "contextualizes",
        "tke:fair:r1-1-license": "qualifies",
    }


# ------------------------------------------------------------------- stats
def test_q6_stats_distributions(conn):
    s = q.stats(conn)
    assert s["claims_by_status"] == {
        "contested": 1,
        "established": 1,
        "not-assessed": 1,
        "well-supported": 1,
    }
    assert s["evidence_by_relation"] == {
        "contextualizes": 3,
        "mentions": 1,
        "qualifies": 1,
        "refutes": 1,
        "supports": 2,
    }
    assert s["evidence_by_assessment"] == {"insufficient": 2, "unassessed": 6}


# ------------------------- consistency: KE xref vs validate_pilot.py
def _file_xref(pilot: Path):
    """Independent recomputation of the xref invariants from raw JSON files
    (same rules as validate_pilot.py section 2)."""
    claims = {
        json.loads(p.read_text(encoding="utf-8"))["id"]: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((pilot / "claims").glob("*.json"))
    }
    evidence = {
        json.loads(p.read_text(encoding="utf-8"))["id"]: json.loads(p.read_text(encoding="utf-8"))
        for p in sorted((pilot / "evidence").glob("*.json"))
    }
    ev_ids, cl_ids = set(evidence), set(claims)
    unresolved_claim_refs = sorted(
        (cid, r) for cid, c in claims.items() for r in c.get("evidence_refs", []) if r not in ev_ids
    )
    unresolved_evidence_refs = sorted(
        (eid, r) for eid, e in evidence.items() for r in e.get("claim_refs", []) if r not in cl_ids
    )
    refd_ev = {r for c in claims.values() for r in c.get("evidence_refs", [])}
    refd_cl = {r for e in evidence.values() for r in e.get("claim_refs", [])}
    return {
        "unresolved_claim_refs": unresolved_claim_refs,
        "unresolved_evidence_refs": unresolved_evidence_refs,
        "orphan_evidence": sorted(ev_ids - refd_ev),
        "claims_without_evidence": sorted(cl_ids - refd_cl),
    }


def test_xref_invariants_match_file_recomputation(conn):
    db_rep = validate.xref_report(conn)
    file_rep = _file_xref(PILOT)
    assert db_rep["unresolved_claim_refs"] == file_rep["unresolved_claim_refs"] == []
    assert db_rep["unresolved_evidence_refs"] == file_rep["unresolved_evidence_refs"] == []
    assert db_rep["orphan_evidence"] == file_rep["orphan_evidence"] == []
    assert db_rep["claims_without_evidence"] == file_rep["claims_without_evidence"] == []


def test_ke_validation_all_pass(conn):
    lines = validate.validate_package(PILOT, conn)
    assert lines, "empty report"
    fails = [(n, d) for n, ok, d in lines if not ok]
    assert not fails, fails
    names = [n for n, _, _ in lines]
    assert any(n.startswith("schema:claim:") for n in names)
    assert any(n.startswith("xref:") for n in names)


def test_reference_validator_passes():
    """The pilot's own reference validator must pass (ties KE semantics to it)."""
    r = subprocess.run(
        [sys.executable, str(PILOT / "validate_pilot.py")],
        capture_output=True,
        text=True,
        cwd=PILOT,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ALL PASS" in r.stdout


# ------------------------------------------------------------- reproducibility
def test_reproducible_double_ingest(tmp_path):
    db1, db2 = tmp_path / "a.db", tmp_path / "b.db"
    c1, c2 = store.connect(db1), store.connect(db2)
    store.ingest_pilot(PILOT, c1)
    store.ingest_pilot(PILOT, c2)
    snap = lambda c: json.dumps(  # noqa: E731
        {
            "status": {st: q.claims_by_status(c, st) for st in
                       ("established", "well-supported", "contested", "not-assessed")},
            "relation": {r: q.evidence_by_relation(c, r) for r in
                         ("supports", "refutes", "qualifies", "contextualizes", "mentions")},
            "domain": q.claims_by_domain(c, "research data stewardship principles"),
            "chain": q.provenance_chain(c, "tkc:prov-o:wasattributedto-signature"),
            "stats": q.stats(c),
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    assert snap(c1) == snap(c2)
    c1.close()
    c2.close()


def test_ingest_idempotent(conn):
    before = q.stats(conn)
    store.ingest_pilot(PILOT, conn)
    assert q.stats(conn) == before


# ------------------------------------------------------- negative control
def test_negative_corrupted_package_detected(tmp_path):
    """Injected violations must be caught: proves invariants are not vacuous."""
    bad = tmp_path / "bad-pilot"
    shutil.copytree(PILOT, bad)
    # (a) orphan evidence: not referenced by any claim
    orphan = {
        "id": "tke:orphan:test",
        "claim_refs": [],
        "source": {"source_type": "website", "citation": "x", "url": "https://x",
                   "accessed_at": "2026-11-09"},
        "relation": "supports",
        "locator": {"locator_type": "section", "value": "x", "quote": "x",
                    "quote_language": "en"},
        "extraction_method": "direct-quotation",
        "captured_at": "2026-11-09T12:10:00Z",
        "captured_by": "test",
        "assessment_status": "unassessed",
        "version": "1.0.0",
    }
    (bad / "evidence" / "tke-orphan-test.json").write_text(
        json.dumps(orphan, ensure_ascii=False), encoding="utf-8"
    )
    # (b) unresolvable evidence_ref inside a claim
    cf = bad / "claims" / "tkc-fair-a1-protocol-conditions.json"
    rec = json.loads(cf.read_text(encoding="utf-8"))
    rec["evidence_refs"].append("tke:ghost:missing")
    cf.write_text(json.dumps(rec, ensure_ascii=False), encoding="utf-8")

    conn = store.connect(":memory:")
    store.ingest_pilot(bad, conn)
    rep = validate.xref_report(conn)
    assert rep["unresolved_claim_refs"] == [("tkc:fair:a1-protocol-conditions", "tke:ghost:missing")]
    assert rep["orphan_evidence"] == ["tke:orphan:test"]
    assert rep["unresolved_evidence_refs"] == []
    assert rep["claims_without_evidence"] == []
    lines = validate.validate_package(bad, conn)
    failed = [n for n, ok, _ in lines if not ok]
    assert "xref:all_evidence_refs_resolve" in failed
    assert "xref:no_orphan_evidence" in failed
    conn.close()
