"""KE migration tests — SQLite staging -> PostgreSQL authoritative (m8800).

These tests pin the migration contract:

* the four record contracts of ``knowledge/oss-lbm/`` are fully ingested
  (nothing silently dropped, byte-identical re-publications collapsed);
* the SQLite and PostgreSQL stores hold *the same bytes* (per-table SHA-256 of
  the canonical row dump), not merely the same row counts;
* re-running the migration is idempotent;
* the reconciliation artefact (JSON + Markdown) is produced and its verdict is
  checked by the CLI exit code.
"""
from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "knowledge" / "oss-lbm"

sys.path.insert(0, str(REPO))
from ke import contract, migrate, queries as q, store, validate  # noqa: E402

#: pinned inventory of the source package (four contracts)
EXPECTED = {
    "claims": 102,
    "evidence": 142,
    "provenance": 7,
    "gap_anchors": 6,
    "claim_evidence": 150,
    "evidence_claims": 150,
    "gap_claims": 27,
}
#: byte-identical roll-up duplicates collapsed by the loader (claims/claims.json
#: re-publishes mflbm/claims.json)
EXPECTED_COLLAPSED = 10


@pytest.fixture(scope="module")
def src_store():
    """SQLite staging store with the whole oss-lbm package ingested."""
    st = store.connect(":memory:")
    contract.ingest_source(SOURCE, st)
    yield st
    st.close()


@pytest.fixture(scope="module")
def pg_store(pg_ok):
    """Authoritative PostgreSQL store holding the migrated package."""
    schema = f"ke_mig_{uuid.uuid4().hex[:8]}"
    st = store.connect(backend="pg", schema=schema, create_schema=True)
    yield st
    st.drop_schema()
    st.close()


@pytest.fixture(scope="module")
def migrated(src_store, pg_store):
    migrate.copy_all(src_store, pg_store)
    return pg_store


# ------------------------------------------------------------------ ingest
def test_source_inventory_pinned(src_store):
    got = {t: contract.table_digest(src_store, t)[0] for t in contract.TABLE_ORDER}
    for table, n in EXPECTED.items():
        assert got[table] == n, (table, got[table], n)


def test_rollup_duplicates_collapsed_not_dropped():
    found = contract.discover(SOURCE)
    assert len(found.duplicates) == EXPECTED_COLLAPSED
    assert {d["kind"] for d in found.duplicates} == {"claims"}
    assert all(d["kept"] == "claims/claims.json" for d in found.duplicates)
    assert all(d["collapsed"] == "mflbm/claims.json" for d in found.duplicates)


def test_conflicting_duplicate_record_is_rejected(tmp_path):
    """Same id + different content must abort (never silently pick one)."""
    for sub, payload in (
        ("a/claims", {"id": "tkc:x:dup", "statement": "one", "claim_type": "descriptive",
                      "epistemic_status": "established", "evidence_refs": [],
                      "created_at": "2026-11-09T00:00:00Z", "version": "1.0.0"}),
        ("b/claims", {"id": "tkc:x:dup", "statement": "two", "claim_type": "descriptive",
                      "epistemic_status": "established", "evidence_refs": [],
                      "created_at": "2026-11-09T00:00:00Z", "version": "1.0.0"}),
    ):
        d = tmp_path / sub
        d.mkdir(parents=True)
        (d / "rec.json").write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError, match="conflicting claims record id"):
        contract.discover(tmp_path)


# --------------------------------------------------------------- migration
def test_migration_preserves_every_byte(src_store, migrated):
    """SQLite and PostgreSQL must hold identical rows (digests, not counts)."""
    src_digests = contract.digests(src_store)
    dst_digests = contract.digests(migrated)
    assert {t: v["rows"] for t, v in src_digests.items()} == \
           {t: v["rows"] for t, v in dst_digests.items()}
    for table in contract.TABLE_ORDER:
        assert src_digests[table]["sha256"] == dst_digests[table]["sha256"], table


def test_reconcile_verdict_pass(src_store, migrated):
    rep = migrate.reconcile(src_store, migrated)
    assert rep["verdict"] == "PASS", [r for r in rep["rows"] if not r["rows_match"]]
    assert rep["totals"]["objects_source"] == rep["totals"]["objects_target"] == 257
    assert rep["totals"]["relations_source"] == rep["totals"]["relations_target"] == 327
    assert rep["assertions"]["match"] and rep["assertions"]["stats_match"]


def test_migration_is_idempotent(src_store, migrated):
    before = contract.digests(migrated)
    migrate.copy_all(src_store, migrated)
    migrate.copy_all(src_store, migrated)
    assert contract.digests(migrated) == before


def test_query_layer_parity_across_backends(src_store, migrated):
    """The six query classes return the same results on both backends."""
    def snap(conn):
        return json.dumps(
            {
                "stats": q.stats(conn),
                "status": {s: [c["id"] for c in q.claims_by_status(conn, s)]
                           for s in ("established", "well-supported", "contested",
                                     "not-assessed", "speculative")},
                "relation": {r: [e["id"] for e in q.evidence_by_relation(conn, r)]
                             for r in ("supports", "refutes", "qualifies",
                                       "contextualizes", "mentions")},
                "domains": {d: [c["id"] for c in q.claims_by_domain(conn, d)]
                            for d in ("lattice-Boltzmann-method", "no-such-domain")},
                "gaps": q.gap_anchors(conn),
                "gap_claims": {g["id"]: [c["id"] for c in q.claims_for_gap(conn, g["id"])]
                               for g in q.gap_anchors(conn)},
                "xref": validate.xref_report(conn),
            },
            ensure_ascii=False, sort_keys=True,
        )

    assert snap(src_store) == snap(migrated)


def test_gap_contract_and_known_data_gap(migrated):
    """Gap anchors are stored and queryable; the known dangling-anchor debt is
    reported identically on both backends (data finding, not a store bug)."""
    gaps = q.gap_anchors(migrated)
    assert len(gaps) == 6
    ids = {g["id"] for g in gaps}
    assert "GAP-LBM-MCMP-POISEUILLE" in ids
    assert q.claims_for_gap(migrated, "GAP-LBM-MCMP-POISEUILLE"), "gap must resolve to claims"
    rep = validate.xref_report(migrated)
    assert rep["unresolved_claim_refs"] == [] and rep["unresolved_evidence_refs"] == []
    # 10 mflbm claims are anchored to GAP-LBM-HPC-SCALING, which is not defined
    # inside this package -> storable (no FK) and visibly reported here.
    assert {g for g, _ in rep["unresolved_gap_refs"]} == {"GAP-LBM-HPC-SCALING"}
    assert len(rep["unresolved_gap_refs"]) == 10


# ------------------------------------------------------------------- CLI
def test_migrate_cli_writes_reconciliation(pg_ok, tmp_path):
    schema = f"ke_cli_{uuid.uuid4().hex[:8]}"
    out, md = tmp_path / "reconcile.json", tmp_path / "reconcile.md"
    env = {"KE_PG_DSN": store.default_pg_dsn(), "PATH": "/usr/local/bin:/usr/bin:/bin"}
    cmd = [sys.executable, "-m", "ke.migrate", "--source", str(SOURCE),
           "--pg-schema", schema, "--out", str(out), "--md", str(md)]
    r = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads(out.read_text(encoding="utf-8"))
    assert rep["verdict"] == "PASS"
    assert rep["totals"]["objects_source"] == rep["totals"]["objects_target"] == 257
    assert rep["totals"]["relations_source"] == rep["totals"]["relations_target"] == 327
    md_text = md.read_text(encoding="utf-8")
    assert "| object | claims (claim-record) | 102 | 102 |" in md_text
    # re-run in --check mode: read-only reconciliation must stay PASS
    r2 = subprocess.run(cmd + ["--check"], cwd=REPO, capture_output=True, text=True, env=env)
    assert r2.returncode == 0, r2.stdout + r2.stderr
    # cleanup the schema created by the CLI run
    st = store.connect(backend="pg", schema=schema)
    st.drop_schema()
    st.close()


def test_dsn_credentials_never_written(tmp_path):
    assert migrate.mask_dsn("postgresql://user:s3cret@h:5432/db") == \
           "postgresql://user:***@h:5432/db"
    assert "s3cret" not in migrate.mask_dsn("postgresql://u:s3cret@h/db")
    # the default DSN carries no credentials at all (peer auth over the socket)
    assert "@" not in store.default_pg_dsn()