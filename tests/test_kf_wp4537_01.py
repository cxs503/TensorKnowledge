"""wp-4537-01 (01-asset-registration, report 4537) — gate-facing self checks.

Every assertion here is an *invariant* rather than "the code ran":
  * the pinned source hash is recomputed from the fetched markdown bytes;
  * every locator/quote in the manifest is re-resolved against that source
    (span slice must equal the quote, snippet sha256 must match);
  * the result envelope validates against schemas/kf_result.v1.schema.json;
  * no duplicate asset ids, zero claims, nothing marked verified;
  * the builder is deterministic (same input -> same manifest modulo timestamp).

The source snapshot is tracked as docs/kf/wp-4537-01/source_report_4537.md, so
the hash / span / determinism / reproduction invariants hold in a clean checkout
without network. The legacy runs/m15537_wp4537_01/ cache and the live API remain
as fallbacks; when none is available the test skips with a reason instead of
pretending to pass.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "docs" / "kf" / "wp-4537-01" / "asset_manifest.json"
ENVELOPE_PATH = ROOT / "docs" / "kf" / "wp-4537-01" / "kf_result.json"
SCHEMA_PATH = ROOT / "schemas" / "kf_result.v1.schema.json"
# Tracked snapshot (in-repo, hash-pinned) — primary source for a clean checkout.
TRACKED_MD = ROOT / "docs" / "kf" / "wp-4537-01" / "source_report_4537.md"
TRACKED_RECORD = ROOT / "docs" / "kf" / "wp-4537-01" / "report_record_4537.json"
# Legacy run cache (git-ignored); kept as a fallback for old worktrees.
CACHE_MD = ROOT / "runs" / "m15537_wp4537_01" / "source_report_4537.md"
CACHE_RECORD = ROOT / "runs" / "m15537_wp4537_01" / "report_record_4537.json"

CONTRACT_SOURCE_HASH = "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08"
CONTRACT_CHARS = 7931


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert MANIFEST_PATH.exists(), f"missing deliverable {MANIFEST_PATH}"
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source_md() -> str:
    for snapshot in (TRACKED_MD, CACHE_MD):
        if snapshot.exists():
            return snapshot.read_text(encoding="utf-8")
    base = os.environ.get("TENSOR_API_BASE")
    if not base or not os.environ.get("TENSOR_AGENT_USER"):
        pytest.skip("no cached source and no TENSOR_API_BASE/TENSOR_AGENT_USER to refetch")
    import urllib.request

    def _post(url, body):
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    token = _post(
        f"{base}/auth/login",
        {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]},
    )["access_token"]
    req = urllib.request.Request(
        f"{base}/tensor/reports/4537", headers={"Authorization": f"Bearer {token}"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["markdown"]


def test_source_hash_matches_contract(manifest, source_md):
    assert _sha256(source_md) == CONTRACT_SOURCE_HASH[7:]
    assert len(source_md) == CONTRACT_CHARS
    src = manifest["source"]
    assert src["sha256"] == CONTRACT_SOURCE_HASH
    assert src["source_hash_matches"] is True
    assert src["chars"] == CONTRACT_CHARS and src["chars_match"] is True
    assert src["report_id"] == "4537"


def test_envelope_validates_against_vendored_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    envelope = json.loads(ENVELOPE_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["package_id"] == "wp-4537-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "4537"
    assert envelope["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert set(envelope["outputs"]) == {"asset_manifest.json"}
    # outputs value is the manifest content itself, not a path string
    assert envelope["outputs"]["asset_manifest.json"]["package_id"] == "wp-4537-01"


def test_every_locator_resolves_in_source(manifest, source_md):
    resolved = 0
    for asset in manifest["assets"]:
        loc = asset["locator"]
        occs = (
            loc.get("occurrences", [])
            + loc.get("markdown_caption_spans", [])
            + loc.get("markdown_head_spans", [])
            + loc.get("markdown_quote_spans", [])
        )
        for occ in occs:
            start, end = occ["span"]
            assert source_md[start:end] == occ["quote"], (
                f"{asset['asset_id']} span {occ['span']} drifted"
            )
            assert "sha256:" + _sha256(occ["quote"]) == occ["snippet_sha256"]
            resolved += 1
        # the authoritative markdown asset carries the whole-body span
        if asset["kind"] == "report_markdown":
            start, end = loc["span"]
            assert (start, end) == (0, len(source_md))
            assert source_md[start : start + len(loc["quote"])] == loc["quote"]
            resolved += 1
    assert resolved >= len(manifest["assets"]), "fewer locators resolved than assets registered"


def test_inline_code_index_spans_resolve(manifest, source_md):
    items = manifest["inline_code_index"]["items"]
    assert manifest["inline_code_index"]["count"] == len(items)
    for it in items:
        start, end = it["span"]
        assert source_md[start:end] == it["token"]
        assert "sha256:" + _sha256(it["token"]) == it["snippet_sha256"]


def test_ids_unique_and_no_verified_marking(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    for a in manifest["assets"]:
        assert a["status"] in {
            "resolved",
            "declared_only",
            "declared_shorthand",
            "declared_metadata_only",
            "declared_metadata_only",
            "unresolved",
        }
        assert "verified" not in json.dumps(a["status"])
        assert a["locator"].get("source_field") in {"markdown", "record"}


def test_claims_are_empty_and_nothing_forced(manifest):
    assert manifest["claims"] == []
    assert manifest["objective"]["extraction_performed"] is False
    assert manifest["objective"]["register_assets"] is True
    assert manifest["objective"]["classify_report_type"] is False


def test_unresolved_items_are_enumerated(manifest):
    non_resolved = [a["asset_id"] for a in manifest["assets"] if a["status"] != "resolved"]
    listed = [u["asset_id"] for u in manifest["unresolved"]]
    assert listed == non_resolved
    assert manifest["asset_counts"]["unresolved"] == len(non_resolved)
    for u in manifest["unresolved"]:
        assert u["reason"] and len(u["reason"]) > 5
    fig = [a for a in manifest["assets"] if a["kind"] == "report_figure"]
    if fig:  # figure bytes are not returned by the read endpoint -> must stay unresolved
        assert fig[0]["payload"]["present"] is False
        assert fig[0]["payload"]["reason"]


def test_declared_paths_are_not_fabricated_as_present(manifest):
    """Files of another repo must not be claimed as available here."""
    for a in manifest["assets"]:
        if a["kind"] in {"path_file", "path_directory"}:
            assert a["payload"]["present"] is False
            assert a["payload"]["sha256"] is None
            assert a["status"] in {"declared_only", "declared_shorthand"}


def test_builder_is_deterministic(manifest):
    spec = importlib.util.spec_from_file_location(
        "reg4537", ROOT / "scripts" / "kf" / "register_4537_assets.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    md_path = TRACKED_MD if TRACKED_MD.exists() else CACHE_MD
    record_path = TRACKED_RECORD if TRACKED_RECORD.exists() else CACHE_RECORD
    assert md_path.exists() and record_path.exists(), "pinned snapshot/record missing"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    a = mod.build(md_path.read_text(encoding="utf-8"), record)
    b = mod.build(md_path.read_text(encoding="utf-8"), record)
    a.pop("generated_at")
    b.pop("generated_at")
    assert json.dumps(a, sort_keys=True, ensure_ascii=False) == json.dumps(
        b, sort_keys=True, ensure_ascii=False
    )


def test_manifest_matches_source_report_only(manifest):
    assert manifest["package_id"] == "wp-4537-01"
    assert manifest["source"]["report_id"] == "4537"
    assert manifest["source"]["record"]["id"] == 4537
    blob = json.dumps(manifest, ensure_ascii=False)
    # regression guard: no other report id leaked into the register
    for other in re.findall(r"tensor://reports/(\d+)", blob):
        assert other == "4537"


def _builder_module():
    spec = importlib.util.spec_from_file_location(
        "reg4537_repro", ROOT / "scripts" / "kf" / "register_4537_assets.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_manifest_reproduces_offline_from_tracked_snapshot(manifest):
    """A clean checkout must rebuild the committed manifest from in-repo bytes only."""
    assert TRACKED_MD.exists(), f"tracked source snapshot missing: {TRACKED_MD}"
    assert TRACKED_RECORD.exists(), f"tracked record snapshot missing: {TRACKED_RECORD}"
    md = TRACKED_MD.read_text(encoding="utf-8")
    assert _sha256(md) == CONTRACT_SOURCE_HASH[7:]
    record = json.loads(TRACKED_RECORD.read_text(encoding="utf-8"))

    rebuilt = _builder_module().build(md, record)
    rebuilt.pop("generated_at", None)
    committed = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    committed.pop("generated_at", None)
    # full-field equality: spans, quotes, hashes, counts, unresolved reasons, checks
    assert json.dumps(rebuilt, sort_keys=True, ensure_ascii=False) == json.dumps(
        committed, sort_keys=True, ensure_ascii=False
    ), "rebuilding from the tracked snapshot no longer reproduces the committed manifest"

    # the asset-level retrieval provenance still records the original m15537 run
    # cache, while the authoritative bytes live in the tracked (hash-identical) copy
    markdown_asset = next(a for a in committed["assets"] if a["kind"] == "report_markdown")
    assert markdown_asset["retrieval"]["cache"] == "runs/m15537_wp4537_01/source_report_4537.md"
    assert markdown_asset["payload"]["sha256"] == CONTRACT_SOURCE_HASH
    src = committed["source"]
    assert src["sha256"] == CONTRACT_SOURCE_HASH
    assert src["chars"] == CONTRACT_CHARS


def test_snapshot_resolver_rejects_drifted_bytes(tmp_path, monkeypatch):
    """The resolver must fail loudly on a drifted snapshot, never refresh silently."""
    spec = importlib.util.spec_from_file_location(
        "kf4537_source", ROOT / "scripts" / "kf" / "kf4537_source.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    good = TRACKED_MD.read_text(encoding="utf-8")
    assert mod.sha256_text(good) == CONTRACT_SOURCE_HASH
    assert mod.load_markdown() == good  # tracked copy resolves and hash-checks

    drifted = tmp_path / "source_report_4537.md"
    drifted.write_text(good + "\n<!-- tampered -->", encoding="utf-8")
    monkeypatch.setattr(mod, "TRACKED_MD", drifted)
    with pytest.raises(ValueError, match="drifted from the pinned contract"):
        mod.load_markdown()
