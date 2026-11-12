"""Acceptance invariants for work package wp-5716-01 (report 5716 asset manifest).

Offline checks always run against the pinned local copy of the report markdown
(runs/wp-5716-01/report_5716.md) so locators and the source hash are re-checked without
network access. The live check (re-fetch the report from the platform API and re-resolve
every locator against live bytes) runs only when TENSOR_API_BASE is set.
"""
import hashlib
import json
import os
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = "wp-5716-01"
REPORT_ID = "5716"
OUT = REPO / "docs" / "kf" / PKG
MANIFEST = OUT / "asset_manifest.json"
RESULT = OUT / "kf_result.json"
LOCAL_COPY = REPO / "runs" / PKG / ("report_%s.md" % REPORT_ID)
CONTRACT_HASH = "4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source_md():
    return LOCAL_COPY.read_bytes().decode("utf-8")


def test_envelope_and_scope(manifest):
    for key in ("manifest_version", "package_id", "task_type", "report_id", "provenance", "assets", "claims"):
        assert key in manifest, key
    assert manifest["package_id"] == PKG
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == REPORT_ID
    assert manifest["provenance"]["source_uri"] == "tensor://reports/%s" % REPORT_ID
    assert manifest["provenance"]["source_field"] == "markdown"


def test_local_copy_hash_matches_contract(manifest, source_md):
    """The registered bytes hash to the contract value; nothing drifted."""
    actual = hashlib.sha256(source_md.encode("utf-8")).hexdigest()
    assert actual == CONTRACT_HASH
    assert manifest["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert manifest["provenance"]["source_chars"] == len(source_md)
    assert manifest["provenance"]["source_bytes_utf8"] == len(source_md.encode("utf-8"))


def test_asset_ids_unique_and_locators_wellformed(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids and len(ids) == len(set(ids))
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["scheme"] in {"markdown_line", "report_field"}, a["asset_id"]
        assert a["resolution"]["status"] in {"resolved", "unresolved", "metadata_only"}, a["asset_id"]


def test_every_markdown_locator_resolves_verbatim(manifest, source_md):
    """quote must be the exact text of that 1-based line, and a substring of the source."""
    lines = source_md.split("\n")
    checked = 0
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["scheme"] != "markdown_line":
            continue
        ln, quote = loc["line"], loc["quote"]
        assert isinstance(ln, int) and 1 <= ln <= len(lines), a["asset_id"]
        assert lines[ln - 1] == quote, a["asset_id"]
        assert quote in source_md, a["asset_id"]
        checked += 1
    assert checked >= 10, "expected the report's path-like references to be registered"


def test_platform_figure_locators_within_bounds(manifest):
    figs = manifest["provenance"].get("report_tags") is not None  # metadata present
    assert figs
    n_figures = sum(1 for a in manifest["assets"] if a["locator"]["scheme"] == "report_field" and a["locator"]["field"] == "figures")
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["scheme"] == "report_field" and loc["field"] == "figures":
            assert isinstance(loc["index"], int) and loc["index"] < n_figures


def test_claims_empty_and_nothing_verified(manifest, source_md):
    assert manifest["claims"] == []
    for a in manifest["assets"]:
        assert a["resolution"]["status"] != "verified"
    for o in manifest.get("inventory_observations", []):
        assert o["status"] != "verified"
        assert o["evidence"], o["observation_id"]
        for ev in o["evidence"]:
            assert source_md.split("\n")[ev["line"] - 1] == ev["quote"], o["observation_id"]


def test_summary_and_provenance_consistency(manifest):
    assets = manifest["assets"]
    summary = manifest["summary"]
    assert summary["asset_count"] == len(assets)
    assert summary["resolved"] == sum(1 for a in assets if a["resolution"]["status"] == "resolved")
    assert summary["unresolved"] == sum(1 for a in assets if a["resolution"]["status"] == "unresolved")
    assert summary["metadata_only"] == sum(1 for a in assets if a["resolution"]["status"] == "metadata_only")
    assert summary["resolved"] + summary["unresolved"] + summary["metadata_only"] == len(assets)
    assert summary["claims"] == 0
    assert sum(summary["by_kind"].values()) == len(assets)


def test_result_envelope_binds_manifest_digest(manifest):
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert result["package_id"] == PKG and result["report_id"] == REPORT_ID
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    out = result["outputs"]["asset_manifest.json"]
    assert out["path"] == str(MANIFEST.relative_to(REPO))
    assert out["sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert out["asset_count"] == manifest["summary"]["asset_count"]


@pytest.mark.skipif(not os.environ.get("TENSOR_API_BASE"), reason="platform API not configured")
def test_live_source_hash_and_locators(manifest):
    """Re-fetch the report and re-resolve locators against live bytes."""
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    }).encode("utf-8")
    req = urllib.request.Request(base + "/auth/login", data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as resp:
        tok = json.loads(resp.read().decode("utf-8"))
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(base + "/tensor/reports/" + REPORT_ID)
    req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as resp:
        rec = json.loads(resp.read().decode("utf-8"))
    rec = rec.get("data") or rec
    assert str(rec["id"]) == REPORT_ID
    live_md = rec["markdown"]
    assert hashlib.sha256(live_md.encode("utf-8")).hexdigest() == manifest["provenance"]["source_hash"].split("sha256:")[-1]
    lines = live_md.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["scheme"] == "markdown_line":
            assert lines[loc["line"] - 1] == loc["quote"], a["asset_id"]