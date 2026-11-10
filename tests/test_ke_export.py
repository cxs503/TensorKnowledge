"""KE export — tests for the three-piece export pipeline.

Tests cover:
  * SFT export: epistemic hard gate (no draft/contested leakage), messages format
  * Eval export: ≥30 entries, tolerance + source present
  * Triples export: subject-predicate-object structure, provenance hash
  * Manifest: counts, distributions, upstream commit
  * CLI: export subcommand

Run: python -m pytest tests/test_ke_export.py -q
"""
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
OSS_LBM = REPO / "knowledge" / "oss-lbm"

sys.path.insert(0, str(REPO))
from ke import store, queries as q  # noqa: E402
from ke import export as exp  # noqa: E402


# ---------------------------------------------------------------- fixtures
@pytest.fixture(scope="module")
def conn():
    """In-memory DB with oss-lbm data."""
    c = store.connect(":memory:")
    exp._ingest_pilot_flexible(OSS_LBM, c)
    yield c
    c.close()


@pytest.fixture(scope="module")
def all_claims(conn):
    return q.all_claims(conn)


# ---------------------------------------------------------------- SFT tests
class TestSFTExport:
    def test_sft_export_returns_manifest(self, conn, tmp_path):
        manifest = exp.export_sft(conn, OSS_LBM, tmp_path)
        assert manifest["export_type"] == "sft"
        assert manifest["included"] > 0
        assert "generated_at" in manifest
        assert "upstream_commit" in manifest

    def test_sft_output_file_exists(self, conn, tmp_path):
        exp.export_sft(conn, OSS_LBM, tmp_path)
        assert (tmp_path / "sft.jsonl").exists()
        assert (tmp_path / "sft_manifest.json").exists()

    def test_sft_messages_format(self, conn, tmp_path):
        exp.export_sft(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "sft.jsonl").read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert "messages" in entry
            assert len(entry["messages"]) == 3
            roles = [m["role"] for m in entry["messages"]]
            assert roles == ["system", "user", "assistant"]

    def test_sft_epistemic_hard_gate_no_draft(self, conn, tmp_path):
        """Hard gate: no draft/contested/not-assessed entries in SFT output."""
        exp.export_sft(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "sft.jsonl").read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert entry["epistemic_status"] in exp.PUBLISHED_STATUSES, \
                f"Draft leakage: {entry['claim_id']} has status {entry['epistemic_status']}"

    def test_sft_no_draft_leakage_sample_10(self, conn, tmp_path):
        """Sample 10 entries: all must have published/reviewed status."""
        exp.export_sft(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "sft.jsonl").read_text(encoding="utf-8").strip().split("\n")
        sample = lines[:10]
        for line in sample:
            entry = json.loads(line)
            assert entry["epistemic_status"] in exp.PUBLISHED_STATUSES

    def test_sft_provenance_sha256(self, conn, tmp_path):
        """Every entry must have a provenance SHA256 hash."""
        exp.export_sft(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "sft.jsonl").read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert "provenance_sha256" in entry
            assert len(entry["provenance_sha256"]) == 64  # SHA256 hex length

    def test_sft_manifest_counts(self, conn, tmp_path):
        manifest = exp.export_sft(conn, OSS_LBM, tmp_path)
        assert manifest["total_claims"] == manifest["included"] + manifest["excluded"]
        assert manifest["included"] > 0

    def test_sft_manifest_domain_distribution(self, conn, tmp_path):
        manifest = exp.export_sft(conn, OSS_LBM, tmp_path)
        assert manifest["domain_distribution"]
        total = sum(manifest["domain_distribution"].values())
        assert total == manifest["included"]


# ---------------------------------------------------------------- Eval tests
class TestEvalExport:
    def test_eval_export_returns_manifest(self, conn, tmp_path):
        manifest = exp.export_eval(conn, OSS_LBM, tmp_path)
        assert manifest["export_type"] == "eval"
        assert manifest["included"] >= 30, f"Need ≥30 eval entries, got {manifest['included']}"

    def test_eval_output_file_exists(self, conn, tmp_path):
        exp.export_eval(conn, OSS_LBM, tmp_path)
        assert (tmp_path / "eval.jsonl").exists()
        assert (tmp_path / "eval_manifest.json").exists()

    def test_eval_has_tolerance(self, conn, tmp_path):
        """Every eval entry must have tolerance."""
        exp.export_eval(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "eval.jsonl").read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert "tolerance" in entry
            assert isinstance(entry["tolerance"], (int, float))
            assert 0 < entry["tolerance"] <= 1.0

    def test_eval_has_source_claim_id(self, conn, tmp_path):
        """Every eval entry must have source_claim_id."""
        exp.export_eval(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "eval.jsonl").read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert "source_claim_id" in entry
            assert entry["source_claim_id"]

    def test_eval_has_input_and_expected(self, conn, tmp_path):
        """Every eval entry must have input and expected fields."""
        exp.export_eval(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "eval.jsonl").read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert "input" in entry
            assert "expected" in entry

    def test_eval_benchmark_entries(self, conn, tmp_path):
        """Eval must include standard LBM benchmark entries."""
        exp.export_eval(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "eval.jsonl").read_text(encoding="utf-8").strip().split("\n")
        benchmark_names = set()
        for line in lines:
            entry = json.loads(line)
            if "benchmark_name" in entry:
                benchmark_names.add(entry["benchmark_name"])
        # Check that at least some benchmark entries are present
        assert len(benchmark_names) >= 3, f"Expected ≥3 benchmark types, got {benchmark_names}"

    def test_eval_manifest_counts(self, conn, tmp_path):
        manifest = exp.export_eval(conn, OSS_LBM, tmp_path)
        assert manifest["included"] >= 30


# ---------------------------------------------------------------- Triples tests
class TestTriplesExport:
    def test_triples_export_returns_manifest(self, conn, tmp_path):
        manifest = exp.export_triples(conn, OSS_LBM, tmp_path)
        assert manifest["export_type"] == "triples"
        assert manifest["total_triples"] > 0

    def test_triples_output_file_exists(self, conn, tmp_path):
        exp.export_triples(conn, OSS_LBM, tmp_path)
        assert (tmp_path / "triples.jsonl").exists()
        assert (tmp_path / "triples_manifest.json").exists()

    def test_triples_structure(self, conn, tmp_path):
        """Every triple must have subject, predicate, object."""
        exp.export_triples(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "triples.jsonl").read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert "subject" in entry
            assert "predicate" in entry
            assert "object" in entry
            assert entry["subject"].startswith("tkc:")
            assert entry["object"].startswith("tke:")

    def test_triples_provenance_sha256(self, conn, tmp_path):
        """Every triple must have a provenance SHA256 hash."""
        exp.export_triples(conn, OSS_LBM, tmp_path)
        lines = (tmp_path / "triples.jsonl").read_text(encoding="utf-8").strip().split("\n")
        for line in lines:
            entry = json.loads(line)
            assert "provenance_sha256" in entry
            assert len(entry["provenance_sha256"]) == 64

    def test_triples_relation_distribution(self, conn, tmp_path):
        manifest = exp.export_triples(conn, OSS_LBM, tmp_path)
        assert manifest["relation_distribution"]
        total = sum(manifest["relation_distribution"].values())
        assert total == manifest["total_triples"]


# ---------------------------------------------------------------- Unified export tests
class TestUnifiedExport:
    def test_export_sft(self, tmp_path):
        manifest = exp.export("sft", OSS_LBM, out_dir=tmp_path)
        assert manifest["export_type"] == "sft"
        assert (tmp_path / "sft.jsonl").exists()

    def test_export_eval(self, tmp_path):
        manifest = exp.export("eval", OSS_LBM, out_dir=tmp_path)
        assert manifest["export_type"] == "eval"
        assert manifest["included"] >= 30

    def test_export_triples(self, tmp_path):
        manifest = exp.export("triples", OSS_LBM, out_dir=tmp_path)
        assert manifest["export_type"] == "triples"
        assert manifest["total_triples"] > 0

    def test_export_invalid_kind(self, tmp_path):
        with pytest.raises(ValueError, match="Unknown export kind"):
            exp.export("invalid", OSS_LBM, out_dir=tmp_path)


# ---------------------------------------------------------------- CLI tests
class TestCLIExport:
    def test_cli_export_sft(self, tmp_path):
        r = subprocess.run(
            [sys.executable, "-m", "ke.cli", "export", str(OSS_LBM),
             "--kind", "sft", "--out", str(tmp_path)],
            capture_output=True, text=True, cwd=REPO,
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads(r.stdout)
        assert manifest["export_type"] == "sft"
        assert (tmp_path / "sft.jsonl").exists()

    def test_cli_export_eval(self, tmp_path):
        r = subprocess.run(
            [sys.executable, "-m", "ke.cli", "export", str(OSS_LBM),
             "--kind", "eval", "--out", str(tmp_path)],
            capture_output=True, text=True, cwd=REPO,
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads(r.stdout)
        assert manifest["included"] >= 30

    def test_cli_export_triples(self, tmp_path):
        r = subprocess.run(
            [sys.executable, "-m", "ke.cli", "export", str(OSS_LBM),
             "--kind", "triples", "--out", str(tmp_path)],
            capture_output=True, text=True, cwd=REPO,
        )
        assert r.returncode == 0, r.stderr
        manifest = json.loads(r.stdout)
        assert manifest["export_type"] == "triples"

    def test_cli_export_invalid_kind(self, tmp_path):
        r = subprocess.run(
            [sys.executable, "-m", "ke.cli", "export", str(OSS_LBM),
             "--kind", "invalid", "--out", str(tmp_path)],
            capture_output=True, text=True, cwd=REPO,
        )
        assert r.returncode != 0


# ---------------------------------------------------------------- Helper tests
class TestHelpers:
    def test_get_scope_from_db_row(self, conn):
        claim = q.all_claims(conn)[0]
        scope = exp._get_scope(claim, conn)
        assert "domain" in scope
        assert scope["domain"] == "lattice-Boltzmann-method"

    def test_get_scope_fallback(self):
        claim = {"domain": "test-domain"}
        scope = exp._get_scope(claim)
        assert scope == {}

    def test_sha256_deterministic(self):
        a = exp._sha256("test")
        b = exp._sha256("test")
        assert a == b
        assert len(a) == 64

    def test_sha256_different_inputs(self):
        a = exp._sha256("test1")
        b = exp._sha256("test2")
        assert a != b
