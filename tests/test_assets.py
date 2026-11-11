"""Knowledge asset management tests — one contract, both backends.

Every test that touches the store is parameterized over ``sqlite`` and ``pg``
through the shared :mod:`tests.conftest` fixtures (``new_conn`` / ``backend``),
so "the asset registry behaves identically on both backends" is machine-checks,
not a promise.

Covered contract points (see ``ke/assets.py`` + ``docs/ASSET-MANAGEMENT.md``):

* schema is created by ``ke.store.connect`` on both backends;
* KO versions are immutable, semver-ordered, with explicit lineage;
* the life-cycle state machine rejects illegal transitions;
* ``review_events`` is the only way into ``published`` and is append-only;
* dataset assets are sha256-pinned (idempotent re-registration only);
* the quality ledger's evidence roll-up is a *domain-scoped* count (documented
  coarse granularity) computed by an exact join, never a substring match;
* ``asset-index-v1`` export is deterministic;
* ``ke assets ...`` CLI and ``scripts/register_assets.py`` (incl. ``--verify``
  drift detection) work end to end.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import assets, contract, store  # noqa: E402

PILOT = REPO / "tests" / "fixtures" / "ke-pilot"
PILOT_DOMAIN = "research data stewardship principles"


@pytest.fixture
def ac(new_conn):
    """Isolated asset registry on the backend under test."""
    return new_conn()


def _seed_claims(conn) -> None:
    """Ingest the KE fixture package so the ledger has real claims/evidence."""
    store.ingest_pilot(PILOT, conn)


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------
def test_schema_created_by_connect(ac):
    assert assets.present_tables(ac) == list(assets.ASSET_TABLES)
    for table in assets.ASSET_TABLES:
        assert ac.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0


def test_ensure_schema_is_idempotent(ac):
    assets.ensure_schema(ac)
    assets.ensure_schema(ac)
    assert assets.present_tables(ac) == list(assets.ASSET_TABLES)


# ---------------------------------------------------------------------------
# KO versions
# ---------------------------------------------------------------------------
def test_register_ko_version_roundtrip(ac):
    vid = assets.register_ko_version(
        ac, "tko:demo:alpha", "1.0.0", title="Alpha", object_type="claim",
        summary="first", content={"domains": ["demo"]}, created_by="tester",
    )
    assert vid == "tko:demo:alpha:v1.0.0"
    latest = assets.get_ko_latest(ac, "tko:demo:alpha")
    assert latest["id"] == vid
    assert latest["state"] == "draft"
    assert latest["content"] == {"domains": ["demo"]}
    assert latest["created_by"] == "tester"


def test_register_same_version_twice_is_rejected(ac):
    assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0")
    with pytest.raises(ValueError, match="already registered"):
        assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", title="rewrite")


def test_register_rejects_bad_input(ac):
    with pytest.raises(ValueError):
        assets.register_ko_version(ac, "", "1.0.0")
    with pytest.raises(ValueError):
        assets.register_ko_version(ac, "tko:demo:alpha", "")
    with pytest.raises(ValueError):
        assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="nonsense")
    with pytest.raises(ValueError, match="born deprecated"):
        assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="deprecated")


def test_lineage_is_semver_ordered_not_textual(ac):
    for version in ("1.9.2", "1.10.0", "1.2.0"):
        assets.register_ko_version(ac, "tko:demo:alpha", version)
    lineage = assets.get_ko_lineage(ac, "tko:demo:alpha")
    assert [v["version"] for v in lineage] == ["1.2.0", "1.9.2", "1.10.0"]
    assert assets.get_ko_latest(ac, "tko:demo:alpha")["version"] == "1.10.0"
    assert assets.version_key("1.10.0") > assets.version_key("1.9.2")


def test_state_machine(ac):
    assets.check_transition("draft", "in_review")
    assets.check_transition("in_review", "published")
    assets.check_transition("published", "in_review")
    assets.check_transition("published", "deprecated")
    for current, target in (("draft", "published"), ("deprecated", "draft"),
                            ("deprecated", "published")):
        with pytest.raises(ValueError, match="illegal state transition"):
            assets.check_transition(current, target)


def test_supersede_lineage(ac):
    old = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="published")
    new = assets.register_ko_version(ac, "tko:demo:alpha", "1.1.0")
    assets.supersede_ko(ac, old, new)
    old_row = assets.get_ko_version(ac, old)
    assert old_row["superseded_by"] == new
    assert old_row["state"] == "deprecated"
    assert assets.get_ko_version(ac, new)["superseded_by"] is None


def test_supersede_rejects_forking_and_regression(ac):
    a = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="published")
    b = assets.register_ko_version(ac, "tko:demo:alpha", "1.1.0")
    c = assets.register_ko_version(ac, "tko:demo:alpha", "1.2.0")
    other = assets.register_ko_version(ac, "tko:demo:beta", "9.0.0")
    with pytest.raises(ValueError, match="cannot supersede itself"):
        assets.supersede_ko(ac, a, a)
    with pytest.raises(ValueError, match="lineage must stay within one KO"):
        assets.supersede_ko(ac, a, other)
    with pytest.raises(ValueError, match="must be greater"):
        assets.supersede_ko(ac, b, a)
    assets.supersede_ko(ac, a, b)
    with pytest.raises(ValueError, match="already superseded"):
        assets.supersede_ko(ac, a, c)


# ---------------------------------------------------------------------------
# review gate
# ---------------------------------------------------------------------------
def test_approve_promotes_to_published(ac):
    vid = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="in_review")
    event_id = assets.record_review(
        ac, vid, "approve", reviewer={"kind": "agent", "id": "reviewer-1"},
        rationale="evidence complete", findings=["4 claims / 8 evidence"],
    )
    assert event_id.startswith("trev:")
    assert assets.get_ko_version(ac, vid)["state"] == "published"
    events = assets.get_review_events(ac, vid)
    assert len(events) == 1
    assert events[0]["decision"] == "approve"
    assert events[0]["reviewer"] == {"kind": "agent", "id": "reviewer-1"}
    assert events[0]["findings"] == ["4 claims / 8 evidence"]
    assert events[0]["policy_version"] == "review-policy-v1"


def test_review_by_ko_id_targets_latest_version(ac):
    assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="published")
    latest = assets.register_ko_version(ac, "tko:demo:alpha", "2.0.0", state="in_review")
    assets.record_review(ac, "tko:demo:alpha", "approve")
    assert assets.get_ko_version(ac, latest)["state"] == "published"


def test_reject_and_revoke_effects(ac):
    a = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="in_review")
    assets.record_review(ac, a, "reject", rationale="claim not supported")
    assert assets.get_ko_version(ac, a)["state"] == "draft"
    b = assets.register_ko_version(ac, "tko:demo:beta", "1.0.0", state="published")
    assets.record_review(ac, b, "revoke", rationale="retracted upstream")
    assert assets.get_ko_version(ac, b)["state"] == "deprecated"


def test_change_request_keeps_version_in_review(ac):
    vid = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="in_review")
    assets.record_review(ac, vid, "request-changes", rationale="missing provenance")
    assert assets.get_ko_version(ac, vid)["state"] == "in_review"


def test_review_rejects_unknown_target_and_decision(ac):
    with pytest.raises(ValueError, match="no KO version or KO registered"):
        assets.record_review(ac, "tko:demo:ghost", "approve")
    vid = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="in_review")
    with pytest.raises(ValueError, match="unknown decision"):
        assets.record_review(ac, vid, "rubber-stamp")
    with pytest.raises(ValueError, match="supersedes_event not found"):
        assets.record_review(ac, vid, "approve", supersedes_event="trev:missing")


def test_review_events_are_append_only_and_ordered(ac):
    vid = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="in_review")
    first = assets.record_review(ac, vid, "request-changes", rationale="v1")
    second = assets.record_review(ac, vid, "approve", rationale="v2",
                                  supersedes_event=first)
    events = assets.get_review_events(ac, vid)
    assert [e["id"] for e in events] == [first, second]
    assert events[1]["supersedes_event"] == first
    assert len({e["id"] for e in events}) == 2


def test_deprecate_ko_records_review(ac):
    vid = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="published")
    event_id = assets.deprecate_ko(ac, vid, reviewer={"kind": "org", "id": "board"},
                                   rationale="superseded by policy v2")
    assert assets.get_ko_version(ac, vid)["state"] == "deprecated"
    assert assets.get_review_events(ac, vid)[-1]["id"] == event_id


# ---------------------------------------------------------------------------
# dataset assets
# ---------------------------------------------------------------------------
SHA_A = "a" * 64
SHA_B = "b" * 64


def test_dataset_asset_idempotent_and_immutable(ac):
    assets.register_dataset_asset(ac, "tka:demo:sft:v1.0.0", "sft", "1.0.0", 42, SHA_A,
                                  status_dist={"train": 42}, upstream_commit="deadbee",
                                  created_by="exporter")
    # same digest -> idempotent
    assets.register_dataset_asset(ac, "tka:demo:sft:v1.0.0", "sft", "1.0.0", 42, SHA_A)
    # different digest -> hard failure
    with pytest.raises(ValueError, match="immutability violation"):
        assets.register_dataset_asset(ac, "tka:demo:sft:v1.0.0", "sft", "1.0.0", 43, SHA_B)
    rows = assets.list_dataset_assets(ac)
    assert len(rows) == 1
    assert rows[0]["sha256"] == SHA_A
    assert rows[0]["status_dist"] == {"train": 42}
    assert rows[0]["record_count"] == 42


def test_dataset_asset_validates_input(ac):
    with pytest.raises(ValueError, match="64-char hex"):
        assets.register_dataset_asset(ac, "tka:demo:sft:v1", "sft", "1.0.0", 1, "short")
    with pytest.raises(ValueError, match="record_count"):
        assets.register_dataset_asset(ac, "tka:demo:sft:v1", "sft", "1.0.0", -1, SHA_A)
    with pytest.raises(ValueError, match="non-empty"):
        assets.register_dataset_asset(ac, "", "sft", "1.0.0", 1, SHA_A)


# ---------------------------------------------------------------------------
# quality ledger
# ---------------------------------------------------------------------------
def test_ledger_evidence_rollup_is_domain_scoped(ac):
    _seed_claims(ac)
    stats = {k: v for k, v in zip(
        ("claims", "evidence", "provenance", "gaps"),
        [ac.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
         for t in ("claims", "evidence", "provenance", "gap_anchors")],
    )}
    assert stats["claims"] == 4 and stats["evidence"] == 8

    # KO declaring the fixture's claim domain gets the domain roll-up
    assets.register_ko_version(ac, "tko:fixture", "1.0.0", state="published",
                               content={"domains": [PILOT_DOMAIN]})
    # KO declaring nothing falls back to exact ko_id matching -> no evidence
    assets.register_ko_version(ac, "tko:unrelated", "1.0.0", state="published")

    ledger = {e["ko_id"]: e for e in assets.compute_quality_ledger(ac)}
    linked = ac.execute(
        """SELECT COUNT(DISTINCT ce.evidence_id) FROM claim_evidence ce
           JOIN claims c ON c.id = ce.claim_id WHERE c.domain = ?""",
        (PILOT_DOMAIN,),
    ).fetchone()[0]
    assert ledger["tko:fixture"]["evidence_count"] == linked > 0
    assert ledger["tko:unrelated"]["evidence_count"] == 0


def test_ledger_counts_citations_and_falsifications(ac):
    a = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="in_review")
    assets.register_ko_version(ac, "tko:demo:beta", "1.0.0", state="published",
                               content={"cites": "tko:demo:alpha"})
    assets.record_review(ac, a, "reject", rationale="unsupported")
    assets.record_review(ac, a, "request-changes", rationale="revise")
    ledger = {e["ko_id"]: e for e in assets.compute_quality_ledger(ac)}
    assert ledger["tko:demo:alpha"]["citation_count"] == 1
    assert ledger["tko:demo:alpha"]["falsified_count"] == 1
    assert ledger["tko:demo:alpha"]["last_review_decision"] == "request-changes"
    assert ledger["tko:demo:beta"]["citation_count"] == 0


def test_ledger_staleness_uses_injected_now(ac):
    now = datetime(2026, 11, 11, 9, 0, tzinfo=timezone.utc)
    fresh = assets.register_ko_version(ac, "tko:demo:fresh", "1.0.0", state="in_review")
    stale = assets.register_ko_version(ac, "tko:demo:stale", "1.0.0", state="in_review")
    never = assets.register_ko_version(ac, "tko:demo:never", "1.0.0", state="published")
    assets.record_review(ac, fresh, "approve", now=now - timedelta(days=1))
    assets.record_review(ac, stale, "approve", now=now - timedelta(days=45))
    ledger = {e["ko_id"]: e for e in assets.compute_quality_ledger(ac, stale_days=30, now=now)}
    assert ledger["tko:demo:fresh"]["is_stale"] is False
    assert ledger["tko:demo:stale"]["is_stale"] is True
    assert ledger["tko:demo:never"]["is_stale"] is True  # published, never reviewed
    assert never  # registered for clarity


def test_quality_report_summary(ac):
    assets.register_ko_version(ac, "tko:demo:pub", "1.0.0", state="published")
    assets.register_ko_version(ac, "tko:demo:draft", "1.0.0", state="draft")
    assets.register_ko_version(ac, "tko:demo:dead", "1.0.0", state="published")
    assets.deprecate_ko(ac, "tko:demo:dead", rationale="retired")
    report = assets.get_quality_report(ac)
    assert report["summary"]["total_kos"] == 3
    assert report["summary"]["published"] == 1
    assert report["summary"]["deprecated"] == 1
    assert report["summary"]["draft_or_review"] == 1
    assert report["summary"]["stale"] == 1  # published + never reviewed
    assert len(report["ledger"]) == 3
    # materialized: the ledger table holds exactly one row per KO
    assert ac.execute("SELECT COUNT(*) FROM quality_ledger").fetchone()[0] == 3


# ---------------------------------------------------------------------------
# asset index export
# ---------------------------------------------------------------------------
def test_asset_index_export_is_deterministic(ac):
    old = assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="published",
                                     content={"domains": ["demo"]})
    new = assets.register_ko_version(ac, "tko:demo:alpha", "1.1.0", state="in_review")
    assets.supersede_ko(ac, old, new)
    assets.register_dataset_asset(ac, "tka:demo:sft:v1.0.0", "sft", "1.0.0", 10, SHA_A)

    first = assets.export_asset_index_obj(ac, generated_at=datetime(2026, 11, 11, tzinfo=timezone.utc))
    second = assets.export_asset_index_obj(ac, generated_at=datetime(2026, 11, 11, tzinfo=timezone.utc))
    assert first == second
    assert first["format"] == "asset-index-v1"
    assert first["total_entries"] == 3
    assert first["index_sha256"] == assets.sha256_json(first["entries"])

    kos = {e["asset_id"]: e for e in first["entries"] if e["asset_type"] == "knowledge_object"}
    assert kos[old]["state"] == "deprecated"
    assert kos[old]["lineage"] == [new]
    assert kos[old]["metadata"]["content_sha256"] is None
    assert kos[old]["metadata"]["content_keys"] == ["domains"]
    assert kos[new]["metadata"]["content_keys"] == []
    ds = [e for e in first["entries"] if e["asset_type"] == "dataset_sft"]
    assert len(ds) == 1 and ds[0]["sha256"] == SHA_A and ds[0]["state"] == "published"

    text = assets.export_asset_index_json(ac, generated_at=datetime(2026, 11, 11, tzinfo=timezone.utc))
    assert json.loads(text)["total_entries"] == 3


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _run_cli(*args: str, cwd: Path = REPO) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "ke.cli", *args], cwd=str(cwd),
                          capture_output=True, text=True, check=False)


def test_cli_assets_roundtrip(tmp_path):
    db = tmp_path / "ke.db"
    r = _run_cli("assets", "register-ko", "tko:cli:demo", "--version", "1.0.0",
                 "--title", "CLI demo", "--state", "in_review",
                 "--content", json.dumps({"domains": ["cli"]}), "--db", str(db))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["registered"] == "tko:cli:demo:v1.0.0"

    r = _run_cli("assets", "review", "tko:cli:demo", "--decision", "approve",
                 "--rationale", "ok", "--db", str(db))
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["decision"] == "approve"

    r = _run_cli("assets", "list", "--db", str(db))
    payload = json.loads(r.stdout)
    assert payload["total"] == 1 and payload["ko_versions"][0]["state"] == "published"

    r = _run_cli("assets", "show", "tko:cli:demo", "--lineage", "--db", str(db))
    assert [v["version"] for v in json.loads(r.stdout)["lineage"]] == ["1.0.0"]

    r = _run_cli("assets", "register-dataset", "--asset-id", "tka:cli:sft:v1.0.0",
                 "--type", "sft", "--version", "1.0.0", "--count", "7",
                 "--sha256", SHA_B, "--db", str(db))
    assert r.returncode == 0, r.stderr

    r = _run_cli("assets", "report", "--db", str(db))
    assert json.loads(r.stdout)["summary"]["published"] == 1

    out = tmp_path / "index.json"
    r = _run_cli("assets", "export-index", "--output", str(out), "--db", str(db))
    assert r.returncode == 0, r.stderr
    assert json.loads(out.read_text())["total_entries"] == 2

    # duplicate registration is a clean CLI failure, not a traceback
    r = _run_cli("assets", "register-ko", "tko:cli:demo", "--version", "1.0.0",
                 "--db", str(db))
    assert r.returncode == 1 and r.stdout == "" and "already registered" in r.stderr


# ---------------------------------------------------------------------------
# scripts/register_assets.py (registration + drift verification)
# ---------------------------------------------------------------------------
@pytest.fixture
def registry_tree(tmp_path):
    root = tmp_path / "knowledge"
    shutil.copytree(PILOT, root / "alpha")
    db = tmp_path / "assets.db"
    conn = store.connect(str(db))
    store.ingest_pilot(root / "alpha", conn)  # claims/evidence for the ledger
    conn.commit()
    conn.close()
    return {"root": root, "db": db, "index": tmp_path / "asset-index.json",
            "report": tmp_path / "health-report.json", "pkg": root / "alpha"}


def _run_script(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(REPO / "scripts" / "register_assets.py"), *args],
                          cwd=str(REPO), capture_output=True, text=True, check=False)


def test_register_assets_script_and_verify(registry_tree):
    t = registry_tree
    args = ["--root", str(t["root"]), "--db", str(t["db"]),
            "--index", str(t["index"]), "--report", str(t["report"])]
    r = _run_script(*args)
    assert r.returncode == 0, r.stderr
    summary = json.loads(r.stdout)
    assert summary["packages"] == 1
    assert summary["health"]["total_kos"] == 1
    assert summary["health"]["evidence_total"] > 0, "ledger must reach the pilot's evidence"

    doc = json.loads(t["index"].read_text())
    assert doc["format"] == "asset-index-v1"
    entry = doc["entries"][0]
    assert entry["asset_id"].startswith("tko:alpha:v")
    assert entry["metadata"]["content_sha256"]
    assert entry["state"] == "in_review"
    report = json.loads(t["report"].read_text())
    assert report["summary"]["total_kos"] == 1

    # re-running is a no-op (content unchanged)
    r = _run_script(*args)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["actions"] == {"unchanged": 1}

    # --verify: pinned digests match live bytes
    r = _run_script("--root", str(t["root"]), "--verify", "--index", str(t["index"]))
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout)["ok"] is True

    # tamper with one record file -> drift must be detected (exit 1)
    claim_file = sorted((t["pkg"] / "claims").glob("*.json"))[0]
    doc = json.loads(claim_file.read_text())
    target = doc if isinstance(doc, dict) else doc[0]
    target["statement"] = target.get("statement", "") + " TAMPERED"
    claim_file.write_text(json.dumps(doc, ensure_ascii=False, indent=2))

    r = _run_script("--root", str(t["root"]), "--verify", "--index", str(t["index"]))
    assert r.returncode == 1
    result = json.loads(r.stdout)
    assert result["ok"] is False
    assert result["drifted"] and result["drifted"][0]["ko_id"] == "tko:alpha"
    assert result["drifted"][0]["pinned"] != result["drifted"][0]["current"]


def test_register_assets_script_requires_existing_root(tmp_path):
    r = _run_script("--root", str(tmp_path / "nope"), "--db", str(tmp_path / "x.db"),
                    "--index", str(tmp_path / "i.json"), "--report", str(tmp_path / "r.json"))
    assert r.returncode == 2
    assert "root not found" in r.stderr


def test_contract_tables_untouched_by_asset_schema(ac):
    """The asset layer must not perturb the record contract's own tables."""
    before = contract.digests(ac)
    assets.register_ko_version(ac, "tko:demo:alpha", "1.0.0", state="in_review")
    assets.record_review(ac, "tko:demo:alpha", "approve")
    after = contract.digests(ac)
    assert before == after