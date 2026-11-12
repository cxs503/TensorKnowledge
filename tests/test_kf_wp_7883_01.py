"""Work package wp-7883-01 (01-asset-registration) — offline regression on the shipped manifest.

The online leg (re-fetch + re-hash + locator re-resolution) lives in
``scripts/kf/wp_7883_01.py verify``; these tests guard what can be checked with
no network: envelope schema conformance, manifest invariants, and the
acceptance items that do not need the source bytes.

Run: pytest -q tests/test_kf_wp_7883_01.py
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-7883-01"
MANIFEST_PATH = PKG_DIR / "asset_manifest.json"
RESULT_PATH = PKG_DIR / "kf_result.json"
VERDICT_PATH = PKG_DIR / "verification.json"
SCHEMA_PATH = REPO / "schemas" / "kf_result.v1.schema.json"

EXPECTED_HASH = "fc4d21ec4e30740b8596ea5b2892c877444ab58e274d5d301638322ae5fd77f5"
EXPECTED_CHARS = 7585


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.is_file(), "asset_manifest.json missing"
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result() -> dict:
    assert RESULT_PATH.is_file(), "kf_result.json missing"
    return json.loads(RESULT_PATH.read_text(encoding="utf-8"))


def test_paths_exist_and_manifest_is_json(manifest: dict) -> None:
    assert MANIFEST_PATH.read_bytes().endswith(b"\n")
    assert isinstance(manifest, dict) and manifest["assets"]


def test_envelope_matches_shipped_schema(result: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(result, json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_envelope_binds_source_hash_and_ids(result: dict) -> None:
    assert result["package_id"] == "wp-7883-01"
    assert result["report_id"] == "7883"
    assert result["task_type"].startswith("01")
    prov = result["provenance"]
    assert prov["source_field"] == "markdown"
    assert prov["source_hash"] == "sha256:" + EXPECTED_HASH
    assert prov["source_chars"] == EXPECTED_CHARS
    assert re.match(r"^sha256:[0-9a-f]{64}$", prov["source_hash"])


def test_outputs_echo_the_declared_file(result: dict) -> None:
    """Contract: outputs[name] is the content object of the declared output file."""
    disk = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert result["outputs"]["asset_manifest.json"] == disk
    bind = result["provenance"]["outputs_binding"]["asset_manifest.json"]
    assert bind["sha256"] == hashlib.sha256(MANIFEST_PATH.read_bytes()).hexdigest()
    assert bind["bytes"] == MANIFEST_PATH.stat().st_size


def test_no_duplicate_asset_ids_and_unique_locator_identity(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert all(ids)
    assert len(ids) == len(set(ids))


def test_every_asset_has_resolvable_locator_shape(manifest: dict) -> None:
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["scheme"] in {"report_field", "markdown_line", "markdown_line_range"}, a["asset_id"]
        if loc["scheme"] == "report_field":
            assert loc["field"] in {"markdown", "summary", "record", "figures"}
        else:
            assert isinstance(loc.get("quote"), str) and loc["quote"], a["asset_id"]
            assert loc["scheme"] != "markdown_line" or isinstance(loc["line"], int)


def test_multiline_table_quotes_are_stored_verbatim(manifest: dict) -> None:
    tables = [a for a in manifest["assets"] if a["kind"] == "markdown_table"]
    assert len(tables) == 6
    for t in tables:
        q = t["locator"]["quote"]
        assert "\n" in q and q.strip().startswith("|")
        assert hashlib.sha256(q.encode("utf-8")).hexdigest() == t["quote_sha256"]
        assert t["locator"]["line_end"] - t["locator"]["line_start"] + 1 == q.count("\n") + 1


def test_resolution_statuses_are_in_vocabulary(manifest: dict) -> None:
    allowed = set(manifest["resolution_status_vocabulary"])
    for a in manifest["assets"]:
        assert a["resolution"]["status"] in allowed, a["asset_id"]
        if a["resolution"]["status"] in {"unresolved", "metadata_only"}:
            assert a["resolution"].get("reason"), "unresolved assets must state why: " + a["asset_id"]


def test_resolved_assets_carry_hashes_where_bytes_exist(manifest: dict) -> None:
    for a in manifest["assets"]:
        if a["kind"] == "report_markdown":
            assert a["sha256"] == EXPECTED_HASH and a["chars"] == EXPECTED_CHARS
        if a["resolution"]["status"] == "resolved" and a["resolution"].get("scope") == "delivery_worktree":
            assert re.match(r"^[0-9a-f]{64}$", a["resolution"]["sha256"])


def test_claims_empty_and_nothing_marked_verified(manifest: dict) -> None:
    assert manifest["claims"] == []
    assert manifest["summary"]["claims"] == 0
    blob = json.dumps(manifest, ensure_ascii=False)
    assert '"verified"' not in blob


def test_scope_is_single_report(manifest: dict, result: dict) -> None:
    refs = set(re.findall(r"reports/(\d+)", json.dumps([manifest, result], ensure_ascii=False)))
    assert refs == {"7883"}


def test_verification_recorded_and_all_pass() -> None:
    assert VERDICT_PATH.is_file(), "verification.json missing (run wp_7883_01.py verify)"
    v = json.loads(VERDICT_PATH.read_text(encoding="utf-8"))
    failing = sorted(k for k, c in v["checks"].items() if not c["pass"])
    assert not failing, "failing acceptance checks: %s" % failing
    for name in ("valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
                 "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"):
        assert name in v["checks"]
    assert v["checks"]["source_hash_matches"]["detail"].count(EXPECTED_HASH) == 4