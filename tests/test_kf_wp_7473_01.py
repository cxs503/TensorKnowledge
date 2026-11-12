"""Acceptance invariants for work package wp-7473-01 (report 7473 asset registration).

Offline checks run always against the committed byte-identical snapshot of the source
markdown.  The live check (re-fetch report 7473 and re-resolve every locator) runs only
when the platform API is reachable and credentials are present.
"""
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-7473-01"
MANIFEST = PKG_DIR / "asset_manifest.json"
SNAPSHOT = PKG_DIR / "source_markdown.md"
SCHEMA = PKG_DIR / "asset_manifest_7473.schema.json"
RESULT = PKG_DIR / "kf_result.json"
EXPECTED_HASH = "c3b3d0954d289cf1f7849f83889e995c71c39bbc15122ddf9f823f5d698d0f6b"
EXPECTED_CHARS = 5942


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def markdown():
    return SNAPSHOT.read_text(encoding="utf-8")


def test_envelope(manifest):
    for key in ("manifest_version", "package_id", "task_type", "report_id", "source", "assets", "claims"):
        assert key in manifest, key
    assert manifest["package_id"] == "wp-7473-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "7473"


def test_scope_is_single_report(manifest):
    """This package must not register or reference any other report id."""
    src = manifest["source"]
    assert src["source_uri"] == "tensor://reports/7473"
    blob = json.dumps(manifest, ensure_ascii=False)
    for other in ("tensor://reports/542", "tensor://reports/623", "tensor://reports/448"):
        assert other not in blob


def test_source_hash_matches_contract_and_snapshot(manifest):
    declared = manifest["source"]["source_hash"]
    assert declared == "sha256:" + EXPECTED_HASH
    assert manifest["source"]["hash_match"] is True
    assert manifest["source"]["chars"] == EXPECTED_CHARS
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == EXPECTED_HASH


def test_manifest_matches_local_schema(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(manifest, json.loads(SCHEMA.read_text(encoding="utf-8")))
    # ... and the delivery envelope must satisfy the repository canonical kf_result schema
    jsonschema.validate(json.loads(RESULT.read_text(encoding="utf-8")),
                        json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8")))


def test_asset_ids_unique_and_locators_resolve_in_snapshot(manifest, markdown):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids and len(ids) == len(set(ids))
    lines = markdown.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["scheme"] == "markdown_line":
            ln = loc["line"]
            assert 1 <= ln <= len(lines), a["asset_id"]
            assert lines[ln - 1] == loc["quote"], a["asset_id"]
            assert markdown[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
            assert loc["unique"] == (markdown.count(loc["quote"]) == 1), a["asset_id"]
        elif loc["scheme"] == "markdown_document":
            assert loc["start_char"] == 0 and loc["end_char"] == len(markdown)
        elif loc["scheme"] == "report_field":
            assert loc["field"] == "figures" and loc["quote"]


def test_quotes_are_verbatim_slices(manifest, markdown):
    """BS4-free structural check: no locator quote may be hand-edited into a non-substring."""
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["scheme"] in {"markdown_line", "markdown_document"}:
            assert loc["quote"] in markdown, a["asset_id"]


def test_resolution_vocabulary_closed(manifest):
    allowed = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
    results = {"resolved": "resolved_in_source", "unresolved": "referenced_unresolved", "absent": "declared_absent"}
    n = {"resolved_in_source": 0, "referenced_unresolved": 0, "declared_absent": 0}
    for a in manifest["assets"]:
        status = a["resolution"]["status"]
        assert status in allowed, a["asset_id"]
        assert results[a["resolution"]["result"]] == status, a["asset_id"]
        n[status] += 1
    assert n == manifest["counts"]["by_resolution"]


def test_foreign_repo_paths_are_not_falsely_resolved(manifest):
    """Regression: TensorLBM paths must never be 'resolved' against TensorKnowledge's own tests/."""
    for a in manifest["assets"]:
        label = a["label"].rstrip("/")
        if label.startswith(("src/", "tests/", "benchmarks/", "artifacts/")):
            assert a["resolution"]["status"] == "referenced_unresolved", (a["asset_id"], label)


def test_no_claim_marked_verified(manifest):
    assert manifest["claims"] == []
    assert manifest["counts"].get("claims", 0) in (0, None)


def test_kf_result_envelope_matches_manifest(manifest):
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["package_id"] == "wp-7473-01"
    assert result["task_type"] == "01-asset-registration"
    assert result["report_id"] == "7473"
    assert result["provenance"]["source_hash"] == manifest["source"]["source_hash"]
    out = result["outputs"]["asset_manifest.json"]
    assert out["sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert out["bytes"] == len(MANIFEST.read_bytes())
    assert out["asset_count"] == manifest["counts"]["assets"]
    assert result["claims"] == []
    # every hashed output must still match disk: catches a stale envelope after a partial re-run
    for name, meta in result["outputs"].items():
        path = REPO / meta["path"]
        assert path.is_file(), name
        assert hashlib.sha256(path.read_bytes()).hexdigest() == meta["sha256"], name
        assert len(path.read_bytes()) == meta["bytes"], name


def test_live_report_still_identical():
    """Live re-fetch: the registered hash must still describe report 7473."""
    base = os.environ.get("TENSOR_API_BASE")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        pytest.skip("no platform credentials in environment")
    try:
        req = urllib.request.Request(
            base.rstrip("/") + "/auth/login",
            data=json.dumps({"username": user, "password": pwd}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            token = json.loads(r.read().decode())["access_token"]
        req = urllib.request.Request(
            base.rstrip("/") + "/tensor/reports/7473",
            headers={"Authorization": "Bearer " + token},
        )
        with urllib.request.urlopen(req, timeout=20) as r:
            md = json.loads(r.read().decode())["markdown"]
    except (urllib.error.URLError, KeyError, OSError) as e:  # pragma: no cover - env dependent
        pytest.skip("platform unreachable: %s" % type(e).__name__)
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
    assert len(md) == EXPECTED_CHARS
