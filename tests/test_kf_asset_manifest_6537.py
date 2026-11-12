"""Acceptance invariants for work package wp-6537-01 (report 6537 asset registration).

Offline checks always run (against the byte-exact snapshot committed with the manifest).
The live check runs only when the platform API is reachable, and it asserts the *same* hash.
"""
import hashlib
import json
import os
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-6537-01"
MANIFEST = PKG_DIR / "asset_manifest.json"
SNAPSHOT = PKG_DIR / "source_6537.md"
RESULT = PKG_DIR / "kf_result.json"
EXPECTED_HASH = "aaf27418db0e671d671f7cafa2aecf6d68e235f593384832f3fb46cf152d1f71"
EXPECTED_CHARS = 10530


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source():
    return SNAPSHOT.read_text(encoding="utf-8")


def test_manifest_top_level_identity(manifest):
    for key in ("schema", "package_id", "task_type", "report_id", "provenance",
                "counts", "assets", "claims", "integrity"):
        assert key in manifest, key
    assert manifest["package_id"] == "wp-6537-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "6537"


def test_scope_is_single_report(manifest):
    """Hard boundary: this package registers report 6537 only."""
    assert manifest["provenance"]["source_uri"] == "tensor://reports/6537"
    assert manifest["provenance"]["source_field"] == "markdown"
    assert "no other report id" in manifest["integrity"]["report_scope"]


def test_declared_hash_matches_contract(manifest):
    assert manifest["provenance"]["source_hash"] == "sha256:" + EXPECTED_HASH
    assert manifest["provenance"]["hash_matches_contract"] is True
    assert manifest["provenance"]["source_chars"] == EXPECTED_CHARS


def test_snapshot_bytes_rehash_to_contract_hash():
    raw = SNAPSHOT.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == EXPECTED_HASH
    assert len(raw.decode("utf-8")) == EXPECTED_CHARS


def test_every_locator_resolves_inside_the_source(manifest, source):
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["scheme"] == "report_field" and loc.get("field") == "figures":
            assert isinstance(loc["index"], int)
            continue
        q, s, e = loc["quote"], loc["start_char"], loc["end_char"]
        if loc.get("method") == "document":  # whole-document locator (the source asset itself)
            assert q in source and (s, e) == (0, len(source))
            continue
        if source[s:e] != q or source.count(q) != 1:
            bad.append(a["asset_id"])
        if (loc.get("start_line"), loc.get("end_line")) != (
            0, 0
        ):  # markdown-derived locators carry real line spans
            assert loc["start_line"] >= 1
            assert loc["start_line"] <= loc["end_line"]
    assert not bad, bad


def test_no_duplicate_asset_ids_and_counts_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    c = manifest["counts"]
    assert c["assets"] == len(ids)
    assert sum(c["by_class"].values()) == len(ids)
    assert sum(c["by_resolution"].values()) == len(ids)
    assert c["tables"] == c["by_class"].get("markdown_table", 0)
    assert c["code_blocks"] == c["by_class"].get("code_block", 0)
    assert c["platform_figures"] == c["by_class"].get("figure_platform_metadata", 0)


def test_resolution_vocabulary_is_bounded(manifest):
    allowed = {"resolved", "metadata_only", "unresolved", "declared_unavailable"}
    for a in manifest["assets"]:
        assert a["resolution"]["status"] in allowed, a["asset_id"]
        # no asset may claim verification: that is the platform gate's output, not ours
        assert "verified" not in json_dump_lower(a["resolution"])


def json_dump_lower(obj):
    return json.dumps(obj, ensure_ascii=False)


def test_claims_empty_and_never_verified(manifest):
    assert manifest["claims"] == []
    assert manifest["integrity"]["no_verified_marks"] is True
    assert manifest["integrity"]["claims_empty_is_intentional"] is True


def test_resolved_path_references_point_at_real_files(manifest):
    """If we ever claim a referenced file is resolved, it must exist AND its sha256 must match."""
    for a in manifest["assets"]:
        if a["asset_class"] != "path_reference":
            continue
        chk = a["resolution"]["local_check"]
        if a["resolution"]["status"] == "resolved":
            target = REPO / chk["resolved_path"]
            assert target.exists() or "files" in chk
            if "sha256" in chk:
                assert hashlib.sha256(target.read_bytes()).hexdigest() == chk["sha256"]
        else:
            assert chk["status"] == "unresolved"
            assert "reason" in chk


def test_unresolved_assets_declare_a_reason(manifest):
    for a in manifest["assets"]:
        if a["resolution"]["status"] in {"unresolved", "declared_unavailable"}:
            assert a["resolution"].get("reason") or a["resolution"].get("local_check", {}).get(
                "reason"
            ), a["asset_id"]


def test_figure_metadata_matches_report_record(manifest):
    metas = [a for a in manifest["assets"] if a["asset_class"] == "figure_platform_metadata"]
    body = [a for a in manifest["assets"] if a["asset_class"] == "figure_body_reference"]
    assert len(metas) == 5 and len(body) == 5
    names_meta = sorted(a["label"] for a in metas)
    names_body = sorted(Path(a["label"]).name for a in body)
    assert names_meta == names_body  # same five figures, cited both in record and in §4
    # probes are recorded verbatim, never assumed
    assert len(manifest["figure_probes"]) == 5
    for p in manifest["figure_probes"]:
        assert "status" in p


def test_result_envelope(manifest):
    res = json.loads(RESULT.read_text(encoding="utf-8"))
    assert res["package_id"] == "wp-6537-01"
    assert res["task_type"] == "01-asset-registration"
    assert res["report_id"] == "6537"
    assert res["provenance"]["source_field"] == "markdown"
    assert res["provenance"]["source_hash"] == "sha256:" + EXPECTED_HASH
    assert set(res["outputs"]) == {"asset_manifest.json"}
    embedded = res["outputs"]["asset_manifest.json"]
    assert embedded["package_id"] == manifest["package_id"]
    assert embedded["provenance"]["source_hash"] == manifest["provenance"]["source_hash"]
    assert len(embedded["assets"]) == len(manifest["assets"])


def test_live_source_hash_still_matches_contract():
    """Live platform check: re-fetch the report and re-hash the real markdown bytes."""
    base = os.environ.get("TENSOR_API_BASE")
    user, pw = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pw):
        pytest.skip("platform API env not configured")
    try:
        req = urllib.request.Request(
            base.rstrip("/") + "/auth/login",
            data=json.dumps({"username": user, "password": pw}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        tok = json.loads(urllib.request.urlopen(req, timeout=15).read())["access_token"]
        req = urllib.request.Request(
            base.rstrip("/") + "/tensor/reports/6537",
            headers={"Authorization": "Bearer " + tok},
        )
        md = json.loads(urllib.request.urlopen(req, timeout=15).read())["markdown"]
    except Exception as e:  # noqa: BLE001 - unreachable API is a skip, not a pass
        pytest.skip("platform API unreachable: %r" % (e,))
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
    assert len(md) == EXPECTED_CHARS
    assert md == SNAPSHOT.read_text(encoding="utf-8")