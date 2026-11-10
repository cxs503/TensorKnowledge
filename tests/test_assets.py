"""Tests for knowledge asset management (m8811)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).parent
REPO_ROOT = HERE.parent

sys.path.insert(0, str(REPO_ROOT))

from ke import store, assets as asset_mgr


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """Fresh in-memory database with full schema."""
    c = store.connect(":memory:")
    yield c
    c.close()


@pytest.fixture
def conn_with_kos(conn):
    """Database with sample KO versions registered."""
    asset_mgr.register_ko_version(
        conn, ko_id="tko:test:alpha", version="1.0.0",
        title="Alpha claim", object_type="claim",
        summary="Test alpha", state="published",
        created_by="test-agent", raw_json='{"id":"tkc:test:alpha"}',
    )
    asset_mgr.register_ko_version(
        conn, ko_id="tko:test:alpha", version="1.1.0",
        title="Alpha claim v1.1", object_type="claim",
        summary="Test alpha refined", state="published",
        created_by="test-agent", raw_json='{"id":"tkc:test:alpha"}',
    )
    asset_mgr.register_ko_version(
        conn, ko_id="tko:test:beta", version="1.0.0",
        title="Beta claim", object_type="claim",
        summary="Test beta", state="draft",
        created_by="test-agent", raw_json='{"id":"tkc:test:beta"}',
    )
    yield conn


# ---------------------------------------------------------------------------
# KO version lifecycle tests
# ---------------------------------------------------------------------------

class TestKOVersionLifecycle:
    def test_register_ko_version(self, conn):
        vid = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:x", version="1.0.0",
            title="Test", object_type="claim", summary="Summary",
            state="draft", created_by="agent", raw_json="{}",
        )
        assert vid == "tko:test:x:v1.0.0"
        row = conn.execute("SELECT * FROM ko_versions WHERE id = ?", (vid,)).fetchone()
        assert row is not None
        assert row["state"] == "draft"

    def test_invalid_state_rejected(self, conn):
        with pytest.raises(ValueError, match="Invalid state"):
            asset_mgr.register_ko_version(
                conn, ko_id="tko:test:x", version="1.0.0",
                state="nonexistent", created_by="agent", raw_json="{}",
            )

    def test_state_transition_valid(self, conn):
        vid = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:x", version="1.0.0",
            state="draft", created_by="agent", raw_json="{}",
        )
        asset_mgr.transition_ko_state(conn, vid, "in_review")
        row = conn.execute("SELECT state FROM ko_versions WHERE id = ?", (vid,)).fetchone()
        assert row["state"] == "in_review"

    def test_state_transition_invalid(self, conn):
        vid = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:x", version="1.0.0",
            state="deprecated", created_by="agent", raw_json="{}",
        )
        with pytest.raises(ValueError, match="Invalid state transition"):
            asset_mgr.transition_ko_state(conn, vid, "published")

    def test_supersede_chain(self, conn):
        v1 = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:chain", version="1.0.0",
            state="published", created_by="agent", raw_json="{}",
        )
        v2 = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:chain", version="1.1.0",
            state="published", created_by="agent", raw_json="{}",
        )
        asset_mgr.supersede_ko(conn, v1, v2)

        row = conn.execute("SELECT superseded_by FROM ko_versions WHERE id = ?", (v1,)).fetchone()
        assert row["superseded_by"] == v2

    def test_get_ko_lineage(self, conn_with_kos):
        lineage = asset_mgr.get_ko_lineage(conn_with_kos, "tko:test:alpha")
        assert len(lineage) == 2
        assert lineage[0]["version"] == "1.0.0"
        assert lineage[1]["version"] == "1.1.0"

    def test_get_ko_latest(self, conn_with_kos):
        latest = asset_mgr.get_ko_latest(conn_with_kos, "tko:test:alpha")
        assert latest["version"] == "1.1.0"

    def test_get_ko_latest_not_found(self, conn):
        assert asset_mgr.get_ko_latest(conn, "tko:test:nonexistent") is None

    def test_deprecate_ko(self, conn):
        vid = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:dep", version="1.0.0",
            state="published", created_by="agent", raw_json="{}",
        )
        event_id = asset_mgr.deprecate_ko(conn, vid, reviewer="test-reviewer", rationale="test")
        assert "tkr:" in event_id

        row = conn.execute("SELECT state FROM ko_versions WHERE id = ?", (vid,)).fetchone()
        assert row["state"] == "deprecated"

        rev = conn.execute("SELECT * FROM review_events WHERE id = ?", (event_id,)).fetchone()
        assert rev is not None
        assert rev["decision"] == "deprecate"


# ---------------------------------------------------------------------------
# Dataset asset tests
# ---------------------------------------------------------------------------

class TestDatasetAssets:
    def test_register_dataset_asset(self, conn):
        sha = hashlib.sha256(b"test data").hexdigest()
        aid = asset_mgr.register_dataset_asset(
            conn, asset_id="tka:test:sft:v1.0.0",
            asset_type="sft", version="1.0.0",
            record_count=100, sha256=sha,
            created_by="agent", raw_json="{}",
        )
        assert aid == "tka:test:sft:v1.0.0"

    def test_immutability_enforced(self, conn):
        sha1 = hashlib.sha256(b"data v1").hexdigest()
        asset_mgr.register_dataset_asset(
            conn, asset_id="tka:test:imm:v1.0.0",
            asset_type="sft", version="1.0.0",
            record_count=100, sha256=sha1,
            created_by="agent", raw_json="{}",
        )

        # Same sha256 = idempotent (OK)
        aid = asset_mgr.register_dataset_asset(
            conn, asset_id="tka:test:imm:v1.0.0",
            asset_type="sft", version="1.0.0",
            record_count=100, sha256=sha1,
            created_by="agent", raw_json="{}",
        )
        assert aid == "tka:test:imm:v1.0.0"

        # Different sha256 = violation
        sha2 = hashlib.sha256(b"data v2").hexdigest()
        with pytest.raises(ValueError, match="Immutability violation"):
            asset_mgr.register_dataset_asset(
                conn, asset_id="tka:test:imm:v1.0.0",
                asset_type="sft", version="1.0.0",
                record_count=100, sha256=sha2,
                created_by="agent", raw_json="{}",
            )

    def test_list_dataset_assets(self, conn):
        sha = hashlib.sha256(b"test").hexdigest()
        asset_mgr.register_dataset_asset(
            conn, asset_id="tka:test:sft:v1.0.0",
            asset_type="sft", version="1.0.0",
            record_count=50, sha256=sha,
            created_by="agent", raw_json="{}",
        )
        assets = asset_mgr.list_dataset_assets(conn)
        assert len(assets) == 1
        assert assets[0]["asset_type"] == "sft"
        assert assets[0]["record_count"] == 50


# ---------------------------------------------------------------------------
# Quality ledger tests
# ---------------------------------------------------------------------------

class TestQualityLedger:
    def test_compute_quality_ledger(self, conn_with_kos):
        ledger = asset_mgr.compute_quality_ledger(conn_with_kos)
        assert len(ledger) == 2  # alpha and beta

        alpha = next(r for r in ledger if r["ko_id"] == "tko:test:alpha")
        assert alpha["state"] == "published"
        assert alpha["version"] == "1.1.0"

        beta = next(r for r in ledger if r["ko_id"] == "tko:test:beta")
        assert beta["state"] == "draft"

    def test_stale_detection(self, conn):
        # Register a published KO with old review date
        vid = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:stale", version="1.0.0",
            state="published", created_by="agent", raw_json="{}",
        )
        # Insert an old review event (60 days ago)
        from datetime import datetime, timezone, timedelta
        old_date = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
        conn.execute(
            """INSERT INTO review_events
               (id, object_ref, object_version, decision, reviewer_json,
                reviewed_at, policy_version, rationale, raw_json)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                "tkr:test:old-review", "tko:test:stale", "1.0.0",
                "approve",
                json.dumps({"id": "agent", "reviewer_type": "agent"}, sort_keys=True),
                old_date, "v1", "old review", "{}",
            ),
        )

        ledger = asset_mgr.compute_quality_ledger(conn, stale_days=30)
        stale_entry = next(r for r in ledger if r["ko_id"] == "tko:test:stale")
        assert stale_entry["is_stale"] is True

    def test_quality_report_summary(self, conn_with_kos):
        report = asset_mgr.get_quality_report(conn_with_kos)
        assert "summary" in report
        assert report["summary"]["total_kos"] == 2
        assert report["summary"]["published"] == 1  # alpha
        assert report["summary"]["draft_or_review"] == 1  # beta


# ---------------------------------------------------------------------------
# ASSET-INDEX export tests
# ---------------------------------------------------------------------------

class TestAssetIndexExport:
    def test_export_format(self, conn_with_kos):
        index = asset_mgr.export_asset_index(conn_with_kos)
        assert len(index) >= 2  # at least the two KOs

        entry = index[0]
        assert "asset_id" in entry
        assert "asset_type" in entry
        assert "version" in entry
        assert "state" in entry
        assert "sha256" in entry
        assert "lineage" in entry
        assert "metadata" in entry

    def test_export_json_structure(self, conn_with_kos):
        json_str = asset_mgr.export_asset_index_json(conn_with_kos)
        data = json.loads(json_str)
        assert data["format"] == "asset-index-v1"
        assert "generated_at" in data
        assert "total_entries" in data
        assert "entries" in data
        assert data["total_entries"] == len(data["entries"])

    def test_dataset_assets_in_export(self, conn):
        sha = hashlib.sha256(b"test").hexdigest()
        asset_mgr.register_dataset_asset(
            conn, asset_id="tka:test:sft:v1.0.0",
            asset_type="sft", version="1.0.0",
            record_count=100, sha256=sha,
            created_by="agent", raw_json="{}",
        )
        index = asset_mgr.export_asset_index(conn)
        ds_entries = [e for e in index if e["asset_type"].startswith("dataset_")]
        assert len(ds_entries) == 1
        assert ds_entries[0]["record_count"] == 100


# ---------------------------------------------------------------------------
# CLI integration tests
# ---------------------------------------------------------------------------

class TestCLIAssets:
    @pytest.fixture
    def db_path(self, tmp_path):
        return str(tmp_path / "test_assets.db")

    def _init_db(self, db_path):
        """Initialize DB with schema (creates empty tables)."""
        c = store.connect(db_path)
        c.close()

    def test_assets_list_empty(self, db_path):
        self._init_db(db_path)
        result = subprocess.run(
            [sys.executable, "-m", "ke.cli", "assets", "list", "--db", db_path],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert "No KO versions registered" in result.stdout

    def test_assets_list_with_data(self, db_path):
        conn = store.connect(db_path)
        asset_mgr.register_ko_version(
            conn, ko_id="tko:test:cli", version="1.0.0",
            title="CLI test", state="draft",
            created_by="agent", raw_json="{}",
        )
        conn.commit()
        conn.close()

        result = subprocess.run(
            [sys.executable, "-m", "ke.cli", "assets", "list", "--db", db_path],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["total"] == 1

    def test_assets_show_lineage(self, db_path):
        conn = store.connect(db_path)
        v1 = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:lineage", version="1.0.0",
            state="published", created_by="agent", raw_json="{}",
        )
        v2 = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:lineage", version="1.1.0",
            state="published", created_by="agent", raw_json="{}",
        )
        asset_mgr.supersede_ko(conn, v1, v2)
        conn.commit()
        conn.close()

        result = subprocess.run(
            [sys.executable, "-m", "ke.cli", "assets", "show",
             "tko:test:lineage", "--db", db_path, "--lineage"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert len(data["lineage"]) == 2

    def test_assets_report(self, db_path):
        conn = store.connect(db_path)
        asset_mgr.register_ko_version(
            conn, ko_id="tko:test:report", version="1.0.0",
            state="published", created_by="agent", raw_json="{}",
        )
        conn.commit()
        conn.close()

        result = subprocess.run(
            [sys.executable, "-m", "ke.cli", "assets", "report", "--db", db_path],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "summary" in data
        assert "ledger" in data

    def test_assets_export_index(self, db_path, tmp_path):
        conn = store.connect(db_path)
        asset_mgr.register_ko_version(
            conn, ko_id="tko:test:export", version="1.0.0",
            state="published", created_by="agent", raw_json="{}",
        )
        conn.commit()
        conn.close()

        output = tmp_path / "index.json"
        result = subprocess.run(
            [sys.executable, "-m", "ke.cli", "assets", "export-index",
             "--db", db_path, "--output", str(output)],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["format"] == "asset-index-v1"

    def test_assets_register_dataset(self, db_path):
        sha = hashlib.sha256(b"test").hexdigest()
        result = subprocess.run(
            [sys.executable, "-m", "ke.cli", "assets", "register-dataset",
             "--db", db_path,
             "--asset-id", "tka:test:sft:v1.0.0",
             "--type", "sft", "--version", "1.0.0",
             "--count", "100", "--sha256", sha],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert "registered" in data

    def test_assets_deprecate(self, db_path):
        conn = store.connect(db_path)
        vid = asset_mgr.register_ko_version(
            conn, ko_id="tko:test:deprecate", version="1.0.0",
            state="published", created_by="agent", raw_json="{}",
        )
        conn.commit()
        conn.close()

        result = subprocess.run(
            [sys.executable, "-m", "ke.cli", "assets", "deprecate",
             vid, "--db", db_path,
             "--reviewer", "test-agent", "--rationale", "test deprecation"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["deprecated"] == vid


# ---------------------------------------------------------------------------
# Full pipeline test (oss-lbm registration)
# ---------------------------------------------------------------------------

class TestFullPipeline:
    def test_register_oss_lbm_kos(self):
        """Test that all oss-lbm claims can be registered as KOs."""
        conn = store.connect(":memory:")
        from scripts.register_assets import register_oss_lbm_kos
        result = register_oss_lbm_kos(conn)
        assert len(result["kos"]) > 0

    def test_supersede_demo(self):
        """Test the supersede chain demo."""
        conn = store.connect(":memory:")
        from scripts.register_assets import create_supersede_demo
        result = create_supersede_demo(conn)
        assert len(result["chain"]) == 3
        lineage = asset_mgr.get_ko_lineage(conn, result["ko_id"])
        assert len(lineage) == 3

    def test_dataset_registration(self):
        """Test dataset asset registration."""
        conn = store.connect(":memory:")
        from scripts.register_assets import register_dataset_assets
        result = register_dataset_assets(conn)
        assert len(result) == 3  # sft, eval, triples

    def test_asset_index_export(self):
        """Test that asset index export is valid JSON with correct format."""
        conn = store.connect(":memory:")
        from scripts.register_assets import (
            register_oss_lbm_kos, create_supersede_demo, register_dataset_assets,
        )
        register_oss_lbm_kos(conn)
        create_supersede_demo(conn)
        register_dataset_assets(conn)

        json_str = asset_mgr.export_asset_index_json(conn)
        data = json.loads(json_str)
        assert data["format"] == "asset-index-v1"
        assert data["total_entries"] > 0
        assert len(data["entries"]) == data["total_entries"]

        # Verify all entries have required fields
        for entry in data["entries"]:
            assert "asset_id" in entry
            assert "asset_type" in entry
            assert "version" in entry
            assert "state" in entry
            assert "sha256" in entry
