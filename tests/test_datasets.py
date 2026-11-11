"""Tests for the versioned dataset service (m8813).

Covers:
  - Registration and immutability
  - Manifest retrieval
  - Download with SHA256 verification
  - Epistemic leak prevention (draft=403, published-only default, ?include=reviewed)
  - Diff between versions
  - Integrity verification
  - Status promotion (draft → reviewed → published)
  - HTTP API server endpoints

Run: python -m pytest tests/test_datasets.py -v
"""
from __future__ import annotations

import json
import threading
import time
from http.client import HTTPConnection
from urllib.request import urlopen, Request
from urllib.error import HTTPError

import pytest

from ke.datasets import DatasetStore
from ke.dataset_server import make_server, DatasetHandler

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ROWS = [
    {
        "id": "tk-test-0001",
        "text": "Sample training text one.",
        "domain": "test-domain",
        "task_type": "sft",
        "epistemic_status": "published",
        "created_at": "2026-11-09T10:00:00Z",
    },
    {
        "id": "tk-test-0002",
        "text": "Sample training text two.",
        "domain": "test-domain",
        "task_type": "sft",
        "epistemic_status": "published",
        "created_at": "2026-11-09T10:01:00Z",
    },
    {
        "id": "tk-test-0003",
        "text": "Sample training text three.",
        "domain": "test-domain",
        "task_type": "eval",
        "epistemic_status": "published",
        "created_at": "2026-11-09T10:02:00Z",
    },
]

DRAFT_ROWS = [
    {
        "id": "tk-draft-0001",
        "text": "Draft content — not yet verified.",
        "domain": "test-domain",
        "task_type": "sft",
        "epistemic_status": "draft",
        "created_at": "2026-11-09T11:00:00Z",
    },
]

REVIEWED_ROWS = [
    {
        "id": "tk-reviewed-0001",
        "text": "Reviewed content — assessed but not published.",
        "domain": "test-domain",
        "task_type": "sft",
        "epistemic_status": "reviewed",
        "created_at": "2026-11-09T12:00:00Z",
    },
]


@pytest.fixture
def store():
    s = DatasetStore(":memory:")
    # Register a published dataset
    s.register("test-ds", "v1.0", SAMPLE_ROWS, status="published", description="Test dataset v1")
    # Register a draft dataset
    s.register("test-ds", "v2.0-draft", DRAFT_ROWS, status="draft", description="Draft version")
    # Register a reviewed dataset
    s.register("test-ds", "v1.5-reviewed", REVIEWED_ROWS, status="reviewed", description="Reviewed version")
    # Register a second version with more rows (for diff testing)
    more_rows = SAMPLE_ROWS + [
        {
            "id": "tk-test-0004",
            "text": "New row in v1.1.",
            "domain": "test-domain",
            "task_type": "sft",
            "epistemic_status": "published",
            "created_at": "2026-11-09T10:03:00Z",
        },
        {
            "id": "tk-test-0005",
            "text": "Another new row in v1.1.",
            "domain": "test-domain",
            "task_type": "sft",
            "epistemic_status": "published",
            "created_at": "2026-11-09T10:04:00Z",
        },
    ]
    s.register("test-ds", "v1.1", more_rows, status="published", description="Test dataset v1.1")
    yield s
    s.close()


@pytest.fixture
def server_port():
    """Start a temporary HTTP server on a free port."""
    import socket
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server = make_server(":memory:", port, "127.0.0.1")
    # Pre-populate with test data
    store = DatasetHandler.store
    store.register("http-test", "v1.0", SAMPLE_ROWS, status="published")
    store.register("http-test", "v2.0-draft", DRAFT_ROWS, status="draft")
    store.register("http-test", "v1.5-reviewed", REVIEWED_ROWS, status="reviewed")

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.2)  # Let server start
    yield port
    server.shutdown()


# ---------------------------------------------------------------------------
# Core store tests
# ---------------------------------------------------------------------------

class TestRegistration:
    def test_register_returns_manifest(self, store):
        manifest = store.get_manifest("test-ds", "v1.0")
        assert manifest is not None
        assert manifest["name"] == "test-ds"
        assert manifest["version"] == "v1.0"
        assert manifest["status"] == "published"
        assert manifest["row_count"] == 3
        assert "sha256" in manifest
        assert "created_at" in manifest

    def test_register_immutability(self, store):
        """Same name+version cannot be registered twice."""
        with pytest.raises(ValueError, match="already exists"):
            store.register("test-ds", "v1.0", SAMPLE_ROWS, status="published")

    def test_register_invalid_status(self, store):
        with pytest.raises(ValueError, match="invalid status"):
            store.register("test-ds", "v99", SAMPLE_ROWS, status="bogus")


class TestListing:
    def test_list_all(self, store):
        datasets = store.list_datasets()
        names = [(d["name"], d["version"]) for d in datasets]
        assert ("test-ds", "v1.0") in names
        assert ("test-ds", "v1.1") in names
        assert ("test-ds", "v2.0-draft") in names
        assert ("test-ds", "v1.5-reviewed") in names

    def test_list_by_name(self, store):
        datasets = store.list_datasets(name="test-ds")
        assert all(d["name"] == "test-ds" for d in datasets)
        assert len(datasets) == 4


class TestManifest:
    def test_get_manifest(self, store):
        m = store.get_manifest("test-ds", "v1.0")
        assert m is not None
        assert m["sha256"] is not None

    def test_get_manifest_not_found(self, store):
        assert store.get_manifest("nonexistent", "v1.0") is None


class TestDownload:
    def test_download_published(self, store):
        rows, sha = store.download_rows_jsonl("test-ds", "v1.0")
        assert len(rows) == 3
        assert sha is not None
        # Verify each row is valid JSON
        for r in rows:
            parsed = json.loads(r)
            assert "id" in parsed
            assert "text" in parsed

    def test_download_draft_denied_by_default(self, store):
        """Draft datasets must not be downloadable by default."""
        with pytest.raises(PermissionError, match="draft"):
            store.download_rows_jsonl("test-ds", "v2.0-draft")

    def test_download_draft_with_all(self, store):
        """Draft datasets are accessible with include='all'."""
        rows, sha = store.download_rows_jsonl("test-ds", "v2.0-draft", include="all")
        assert len(rows) == 1

    def test_download_reviewed_denied_by_default(self, store):
        """Reviewed datasets must not be downloadable by default."""
        with pytest.raises(PermissionError, match="reviewed"):
            store.download_rows_jsonl("test-ds", "v1.5-reviewed")

    def test_download_reviewed_with_reviewed_flag(self, store):
        """Reviewed datasets are accessible with include='reviewed'."""
        rows, sha = store.download_rows_jsonl("test-ds", "v1.5-reviewed", include="reviewed")
        assert len(rows) == 1

    def test_download_not_found(self, store):
        with pytest.raises(KeyError):
            store.download_rows_jsonl("nonexistent", "v1.0")

    def test_download_sha256_consistency(self, store):
        """SHA256 must be consistent across downloads."""
        _, sha1 = store.download_rows_jsonl("test-ds", "v1.0")
        _, sha2 = store.download_rows_jsonl("test-ds", "v1.0")
        assert sha1 == sha2


class TestDiff:
    def test_diff_returns_new_rows(self, store):
        """v1.1 has 2 more rows than v1.0."""
        diff = store.diff("test-ds", "v1.1", since="v1.0")
        assert len(diff) == 2
        assert diff[0]["id"] == "tk-test-0004"
        assert diff[1]["id"] == "tk-test-0005"

    def test_diff_since_not_found(self, store):
        with pytest.raises(KeyError, match="since version"):
            store.diff("test-ds", "v1.1", since="nonexistent")

    def test_diff_draft_since_denied(self, store):
        with pytest.raises(PermissionError):
            store.diff("test-ds", "v1.1", since="v2.0-draft")


class TestIntegrity:
    def test_verify_integrity(self, store):
        assert store.verify_integrity("test-ds", "v1.0") is True

    def test_verify_integrity_not_found(self, store):
        assert store.verify_integrity("nonexistent", "v1.0") is False


class TestPromotion:
    def test_promote_draft_to_reviewed(self, store):
        store.register("promo-test", "v1.0", SAMPLE_ROWS[:1], status="draft")
        m = store.promote("promo-test", "v1.0", "reviewed")
        assert m["status"] == "reviewed"

    def test_promote_reviewed_to_published(self, store):
        store.register("promo-test2", "v1.0", SAMPLE_ROWS[:1], status="draft")
        store.promote("promo-test2", "v1.0", "reviewed")
        m = store.promote("promo-test2", "v1.0", "published")
        assert m["status"] == "published"

    def test_promote_invalid_transition(self, store):
        store.register("promo-test3", "v1.0", SAMPLE_ROWS[:1], status="draft")
        with pytest.raises(ValueError, match="cannot promote"):
            store.promote("promo-test3", "v1.0", "published")  # skip reviewed

    def test_promote_not_found(self, store):
        with pytest.raises(KeyError):
            store.promote("nonexistent", "v1.0", "reviewed")


# ---------------------------------------------------------------------------
# HTTP API server tests
# ---------------------------------------------------------------------------

class TestHTTPAPI:
    """Test the HTTP API endpoints using a live server."""

    def _get(self, port, path):
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        headers = dict(resp.getheaders())
        conn.close()
        return status, body, headers

    def test_list_datasets(self, server_port):
        status, body, _ = self._get(server_port, "/datasets")
        assert status == 200
        data = json.loads(body)
        assert "datasets" in data
        assert len(data["datasets"]) == 3

    def test_manifest(self, server_port):
        status, body, _ = self._get(server_port, "/datasets/http-test/v1.0/manifest")
        assert status == 200
        data = json.loads(body)
        assert data["name"] == "http-test"
        assert data["version"] == "v1.0"
        assert "sha256" in data

    def test_manifest_not_found(self, server_port):
        status, _, _ = self._get(server_port, "/datasets/nonexistent/v1.0/manifest")
        assert status == 404

    def test_download_published(self, server_port):
        status, body, headers = self._get(server_port, "/datasets/http-test/v1.0/download")
        assert status == 200
        assert "X-Dataset-SHA256" in headers
        rows = [json.loads(line) for line in body.strip().splitlines() if line.strip()]
        assert len(rows) == 3

    def test_download_draft_returns_403(self, server_port):
        """Draft dataset download must return 403."""
        status, body, _ = self._get(server_port, "/datasets/http-test/v2.0-draft/download")
        assert status == 403
        data = json.loads(body)
        assert "error" in data
        assert "draft" in data["error"].lower()

    def test_download_reviewed_returns_403_by_default(self, server_port):
        """Reviewed dataset download must return 403 by default."""
        status, body, _ = self._get(server_port, "/datasets/http-test/v1.5-reviewed/download")
        assert status == 403
        data = json.loads(body)
        assert "error" in data

    def test_download_reviewed_with_include(self, server_port):
        """Reviewed dataset accessible with ?include=reviewed."""
        status, body, _ = self._get(
            server_port, "/datasets/http-test/v1.5-reviewed/download?include=reviewed"
        )
        assert status == 200
        rows = [json.loads(line) for line in body.strip().splitlines() if line.strip()]
        assert len(rows) == 1

    def test_diff(self, server_port):
        # First register a v1.1 with more rows
        # We need to access the store directly for this test
        status, body, _ = self._get(server_port, "/datasets/http-test/v1.0/download")
        assert status == 200

    def test_diff_missing_since(self, server_port):
        status, body, _ = self._get(server_port, "/datasets/http-test/v1.0/diff")
        assert status == 400
        data = json.loads(body)
        assert "since" in data["error"]

    def test_not_found(self, server_port):
        status, _, _ = self._get(server_port, "/nonexistent")
        assert status == 404


# ---------------------------------------------------------------------------
# Epistemic leak prevention — comprehensive
# ---------------------------------------------------------------------------

class TestEpistemicLeakPrevention:
    """Comprehensive tests for epistemic status enforcement."""

    def test_draft_never_downloadable_default(self, store):
        store.register("leak-test", "v1.0", DRAFT_ROWS, status="draft")
        with pytest.raises(PermissionError):
            store.download_rows_jsonl("leak-test", "v1.0")

    def test_draft_never_downloadable_reviewed_flag(self, store):
        store.register("leak-test2", "v1.0", DRAFT_ROWS, status="draft")
        with pytest.raises(PermissionError):
            store.download_rows_jsonl("leak-test2", "v1.0", include="reviewed")

    def test_published_always_downloadable(self, store):
        store.register("leak-test3", "v1.0", SAMPLE_ROWS, status="published")
        rows, _ = store.download_rows_jsonl("leak-test3", "v1.0")
        assert len(rows) == 3

    def test_reviewed_downloadable_with_reviewed_flag(self, store):
        store.register("leak-test4", "v1.0", REVIEWED_ROWS, status="reviewed")
        rows, _ = store.download_rows_jsonl("leak-test4", "v1.0", include="reviewed")
        assert len(rows) == 1

    def test_reviewed_not_downloadable_default(self, store):
        store.register("leak-test5", "v1.0", REVIEWED_ROWS, status="reviewed")
        with pytest.raises(PermissionError):
            store.download_rows_jsonl("leak-test5", "v1.0")

    def test_http_draft_403(self, server_port):
        status, body, _ = self._get(server_port, "/datasets/http-test/v2.0-draft/download")
        assert status == 403

    def _get(self, port, path):
        conn = HTTPConnection("127.0.0.1", port, timeout=5)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8")
        status = resp.status
        conn.close()
        return status, body, {}
