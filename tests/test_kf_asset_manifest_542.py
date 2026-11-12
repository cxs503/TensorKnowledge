"""Acceptance invariants for work package wp-542-01 (report 542 asset manifest).

Offline checks always run. The live check (re-fetch the report and re-resolve every
locator against the real markdown bytes) runs when TENSOR_API_BASE is available.
"""
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "docs" / "kf" / "wp-542-01" / "asset_manifest.json"
EXPECTED_HASH = "a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_manifest_json_and_envelope(manifest):
    for key in ("manifest_version", "package_id", "task_type", "report_id", "provenance", "assets", "claims"):
        assert key in manifest, key
    assert manifest["package_id"] == "wp-542-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "542"


def test_scope_is_single_report(manifest):
    """This work package must not register or reference any other report id."""
    assert manifest["provenance"]["source_uri"] == "tensor://reports/542"
    assert manifest["report_id"] == "542"


def test_declared_hash_matches_contract(manifest):
    assert manifest["provenance"]["source_hash"] == "sha256:" + EXPECTED_HASH


def test_asset_ids_unique_and_locators_wellformed(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids and len(ids) == len(set(ids))
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["scheme"] in {"markdown_line", "report_field"}
        if loc["scheme"] == "markdown_line":
            assert isinstance(loc["line"], int) and loc["line"] >= 1
            assert isinstance(loc["quote"], str) and loc["quote"].strip()
        assert "status" in a["resolution"]
        assert a["resolution"]["status"] in {"resolved", "unresolved", "metadata_only"}


def test_no_claim_is_marked_verified(manifest):
    assert all(c.get("status") != "verified" for c in manifest["claims"])


def test_claims_empty_or_evidenced(manifest):
    for c in manifest["claims"]:
        assert c.get("evidence") or c.get("status") == "unresolved"


def test_summary_is_consistent_with_assets(manifest):
    s = manifest["summary"]
    assert s["asset_count"] == len(manifest["assets"])
    assert s["claims"] == len(manifest["claims"])
    counted = sum(v for k, v in s["by_kind"].items())
    assert counted == s["asset_count"]


@pytest.mark.skipif(not os.environ.get("TENSOR_API_BASE"), reason="platform API not configured")
def test_live_source_hash_and_every_locator_resolves(manifest):
    sys.path.insert(0, str(REPO / "scripts" / "kf"))
    import build_asset_manifest as b  # noqa: PLC0415

    _meta, md = b.fetch_report(b.login())
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
    lines = md.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["scheme"] == "markdown_line":
            assert loc["quote"] in md, a["asset_id"]
            assert lines[loc["line"] - 1] == loc["quote"], a["asset_id"]
        elif loc["field"] == "markdown":
            assert md, a["asset_id"]
        else:
            figs = _meta.get("figures") or []
            assert 0 <= loc["index"] < len(figs), a["asset_id"]
            assert figs[loc["index"]].get("name") == a["name"], a["asset_id"]