"""End-to-end integration test for the dataset service (m8813).

Starts a live HTTP server, registers datasets, and verifies:
  1. Download stream + SHA256 header
  2. Diff between versions
  3. Eval loader consumption
  4. Epistemic leak prevention (draft=403)

Run: python -m pytest tests/test_datasets_e2e.py -v
"""
from __future__ import annotations

import json
import socket
import threading
import time

import pytest

from ke.datasets import DatasetStore
from ke.dataset_server import make_server, DatasetHandler
from ke.tk_eval_loader import TKDataset, _load_jsonl


@pytest.fixture
def e2e_server():
    """Start a server with pre-populated test data."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    server = make_server(":memory:", port, "127.0.0.1")
    store = DatasetHandler.store

    # Register published dataset v1.0
    store.register(
        "e2e-test", "v1.0",
        [
            {"id": "e2e-001", "text": "Hello world", "domain": "test", "task_type": "sft",
             "epistemic_status": "published", "created_at": "2026-11-09T10:00:00Z"},
            {"id": "e2e-002", "text": "Second sample", "domain": "test", "task_type": "sft",
             "epistemic_status": "published", "created_at": "2026-11-09T10:01:00Z"},
        ],
        status="published",
    )

    # Register published dataset v1.1 (with 2 more rows)
    store.register(
        "e2e-test", "v1.1",
        [
            {"id": "e2e-001", "text": "Hello world", "domain": "test", "task_type": "sft",
             "epistemic_status": "published", "created_at": "2026-11-09T10:00:00Z"},
            {"id": "e2e-002", "text": "Second sample", "domain": "test", "task_type": "sft",
             "epistemic_status": "published", "created_at": "2026-11-09T10:01:00Z"},
            {"id": "e2e-003", "text": "New row 1", "domain": "test", "task_type": "sft",
             "epistemic_status": "published", "created_at": "2026-11-09T10:02:00Z"},
            {"id": "e2e-004", "text": "New row 2", "domain": "test", "task_type": "sft",
             "epistemic_status": "published", "created_at": "2026-11-09T10:03:00Z"},
        ],
        status="published",
    )

    # Register draft dataset
    store.register(
        "e2e-test", "v2.0-draft",
        [
            {"id": "e2e-draft-001", "text": "Draft content", "domain": "test", "task_type": "sft",
             "epistemic_status": "draft", "created_at": "2026-11-09T11:00:00Z"},
        ],
        status="draft",
    )

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    time.sleep(0.3)
    yield port, store
    server.shutdown()


class TestE2E:
    """End-to-end integration tests."""

    def test_download_sha256_verification(self, e2e_server):
        """Download stream must include correct SHA256 header."""
        port, store = e2e_server
        base_url = f"http://127.0.0.1:{port}"
        url = f"{base_url}/datasets/e2e-test/v1.0/download"

        rows, sha_header = _load_jsonl(url)
        assert len(rows) == 2
        assert sha_header is not None
        assert len(sha_header) == 64  # SHA256 hex length

        # Verify SHA256 matches server-side computation
        manifest = store.get_manifest("e2e-test", "v1.0")
        assert sha_header == manifest["sha256"]

    def test_eval_loader_consumption(self, e2e_server):
        """Eval loader must successfully load and iterate samples."""
        port, _ = e2e_server
        base_url = f"http://127.0.0.1:{port}"

        ds = TKDataset("e2e-test", "v1.0", base_url)
        assert len(ds) == 2
        assert ds[0]["id"] == "e2e-001"
        assert ds[1]["id"] == "e2e-002"

        # Iterate all
        ids = [row["id"] for row in ds]
        assert ids == ["e2e-001", "e2e-002"]

    def test_diff_incremental(self, e2e_server):
        """Diff must return only new rows between versions."""
        port, store = e2e_server
        base_url = f"http://127.0.0.1:{port}"

        # Use the store directly for diff
        diff = store.diff("e2e-test", "v1.1", since="v1.0")
        assert len(diff) == 2
        assert diff[0]["id"] == "e2e-003"
        assert diff[1]["id"] == "e2e-004"

    def test_draft_403(self, e2e_server):
        """Draft dataset must return 403."""
        port, _ = e2e_server
        base_url = f"http://127.0.0.1:{port}"

        with pytest.raises(Exception):  # urllib.error.HTTPError
            _load_jsonl(f"{base_url}/datasets/e2e-test/v2.0-draft/download")

    def test_version_lock_discipline(self, e2e_server):
        """Version lock: name + version + sha256 must be consistent."""
        port, store = e2e_server
        base_url = f"http://127.0.0.1:{port}"

        # Get manifest
        manifest = store.get_manifest("e2e-test", "v1.0")
        name = manifest["name"]
        version = manifest["version"]
        sha256 = manifest["sha256"]

        # Download and verify
        rows, sha_header = _load_jsonl(f"{base_url}/datasets/{name}/{version}/download")
        assert sha_header == sha256

        # Version lock triplet
        version_lock = f"{name}:{version}:{sha256}"
        assert version_lock == "e2e-test:v1.0:" + sha256
