"""Offline acceptance tests for KF work package wp-6939-01 (01-asset-registration).

Scope: report_id=6939 only. No network: every check runs against the frozen source fixture
tests/fixtures/kf/6939_markdown.md, whose sha256 is pinned to the work-package contract.

These tests assert *invariants* (hash identity, locator round-trip, id uniqueness, schema
conformance, single result block), not merely that the generator ran.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-6939-01"
FIXTURE = REPO / "tests" / "fixtures" / "kf" / "6939_markdown.md"
MANIFEST = PKG_DIR / "asset_manifest.json"
RESULT = PKG_DIR / "kf_result.json"
VERDICT = PKG_DIR / "verification.json"
SCHEMA = PKG_DIR / "asset_manifest.v1.schema.json"
ENVELOPE = REPO / "schemas" / "kf_result.v1.schema.json"
REPORT_MD = PKG_DIR / "report.md"

CONTRACT_HASH = "8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246"
CONTRACT_CHARS = 2002


@pytest.fixture(scope="module")
def md() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


def _line_of(text: str, idx: int) -> int:
    return text.count("\n", 0, idx) + 1


# --------------------------------------------------------------- source identity
def test_fixture_hash_matches_contract(md):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_manifest_provenance_matches_contract(md, manifest):
    assert manifest["report_id"] == "6939"
    assert manifest["source"]["uri"] == "tensor://reports/6939"
    assert manifest["source"]["field"] == "markdown"
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == len(md) == CONTRACT_CHARS
    assert manifest["source"]["bytes_utf8"] == len(md.encode("utf-8"))
    assert manifest["integrity"]["hash_matches_contract"] is True
    assert manifest["integrity"]["fixture_sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()


def test_envelope_source_hash_equals_markdown_bytes(result, md):
    assert result["provenance"]["source_field"] == "markdown"
    assert result["provenance"]["source_hash"] == "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert result["provenance"]["source_hash"].removeprefix("sha256:") == CONTRACT_HASH
    assert result["provenance"]["source_chars"] == CONTRACT_CHARS


# --------------------------------------------------------------- locators
def test_char_span_locators_round_trip(md, manifest):
    spans = [a for a in manifest["assets"] if a["locator"]["method"] == "char_span"]
    assert spans, "expected at least one char_span locator"
    for a in spans:
        loc = a["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert _line_of(md, loc["start_char"]) == loc["start_line"], a["asset_id"]
        assert _line_of(md, loc["end_char"] - 1) == loc["end_line"], a["asset_id"]
        assert md.count(loc["quote"]) == (1 if loc["unique"] else md.count(loc["quote"]))


def test_document_locator_covers_whole_source(md, manifest):
    docs = [a for a in manifest["assets"] if a["locator"]["method"] == "document"]
    assert len(docs) == 1
    loc = docs[0]["locator"]
    assert (loc["start_char"], loc["end_char"]) == (0, len(md))
    assert md.startswith(loc["quote"], loc["start_char"])


def test_record_field_locators_bind_to_platform_figures(md, manifest):
    figs = manifest["source"]["platform_figures"]
    recs = [a for a in manifest["assets"] if a["locator"]["method"] == "record_field"]
    assert len(recs) == len(figs) == 5
    for a in recs:
        loc = a["locator"]
        assert loc["record_field"] == "figures"
        # quote must resolve in the markdown (the platform re-checks substrings independently)...
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) == 1
        # ...while the figure identity comes from the record and is compared field by field
        assert figs[loc["record_index"]]["caption"] == loc["record_caption"], a["asset_id"]
        assert figs[loc["record_index"]]["name"] == loc["record_name"]
        assert loc["record_caption"] in a["label"] and loc["record_name"] in a["label"]


def test_every_quote_is_verbatim_in_the_markdown(md, manifest):
    """Universal platform-aligned guard: no locator may carry a quote absent from the source bytes."""
    for a in manifest["assets"]:
        assert a["locator"]["quote"] in md, a["asset_id"]


# --------------------------------------------------------------- honesty of resolution
def test_metadata_only_figures_are_not_claimed_resolved(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure_declared"]
    assert figs, "figures must be registered, not silently dropped"
    for a in figs:
        assert a["resolution"] == "metadata_only"
        assert a["resolution_check"]["result"] == "absent"
        assert "404" in a["note"] or "no bytes" in a["note"].lower() or "no png" in a["note"].lower()
        assert a["locator"]["record_caption"] in a["note"]


def test_symbol_grep_is_not_self_referential(manifest):
    """A symbol must never be 'resolved' merely because the frozen fixture or this package's own
    deliverables quote it — that would be circular evidence."""
    own = {FIXTURE.resolve(), MANIFEST.resolve(), RESULT.resolve(), REPORT_MD.resolve()}
    for a in manifest["assets"]:
        if a["asset_class"] != "code_symbol_reference":
            continue
        hits = a["resolution_check"].get("hits") or []
        assert not any((REPO / h).resolve() in own for h in hits), a["asset_id"]
        assert not any(h.startswith("docs/kf/wp-6939-01/") for h in hits), a["asset_id"]
        # no symbol is defined in this worktree -> must be declared unresolved, with a reason
        if not hits:
            assert a["resolution"] == "referenced_unresolved"
            assert a["resolution_check"]["result"] == "unresolved"
            assert "TensorLBM" in a["note"]


def test_metadata_only_verdict_rests_on_probe_evidence(manifest):
    """The metadata_only classification must be backed by recorded platform probes, not assertion."""
    probe = manifest.get("artifact_probe")
    assert probe is not None
    assert probe["any_payload_bytes"] is False
    assert probe["figures_with_png_base64"] == 0
    fig_names = [f["name"] for f in manifest["source"]["platform_figures"]]
    probed = {e["figure"]: e["status"] for e in probe["endpoints"] if e.get("figure")}
    assert set(probed) == set(fig_names)
    assert all(s.startswith("http_404") for s in probed.values())
    paths = [e["endpoint"] for e in probe["endpoints"] if not e.get("figure")]
    assert "GET /tensor/reports/6939/artifacts" in paths
    assert "GET /tensor/artifacts?report_id=6939" in paths


def test_no_verified_marks_anywhere():
    for p in (MANIFEST, RESULT, SCHEMA, REPORT_MD):
        txt = p.read_text(encoding="utf-8")
        assert '"verified"' not in txt, p.name
        assert "status: verified" not in txt, p.name


# --------------------------------------------------------------- structure
def test_ids_unique_and_counts_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids), "asset ids should be assigned in a stable order"
    c = manifest["counts"]
    assert c["assets"] == len(ids)
    assert sum(c["by_class"].values()) == len(ids)
    assert sum(c["by_resolution"].values()) == len(ids)
    for k in ("resolved_in_source", "metadata_only", "referenced_unresolved", "declared_absent"):
        assert c[k] == c["by_resolution"].get(k, 0)


def test_claims_empty_is_explicit(manifest):
    assert manifest["claims"] == []
    assert manifest["claims_rationale"]


def test_schema_pass(manifest, result):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(manifest, json.loads(SCHEMA.read_text(encoding="utf-8")))
    jsonschema.validate(result, json.loads(ENVELOPE.read_text(encoding="utf-8")))


def test_envelope_outputs_carry_the_manifest(result, manifest):
    assert result["package_id"] == "wp-6939-01"
    assert result["task_type"] == "01-asset-registration"
    assert result["report_id"] == "6939"
    assert result["outputs"]["asset_manifest.json"] == manifest


def test_only_report_6939_is_referenced():
    blob = "\n".join(p.read_text(encoding="utf-8") for p in (MANIFEST, RESULT))
    assert set(re.findall(r"tensor://reports/(\d+)", blob)) == {"6939"}
    assert set(re.findall(r'"report_id":\s*"(\d+)"', blob)) == {"6939"}


# --------------------------------------------------------------- report channel
def test_report_has_exactly_one_json_block_equal_to_result(result):
    md = REPORT_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    assert len(blocks) == 1, "the delivery channel allows exactly one json block"
    assert json.loads(blocks[0]) == result
    assert md.lstrip().startswith("# KF-RESULT wp-6939-01")


def test_verdict_is_recorded():
    v = json.loads(VERDICT.read_text(encoding="utf-8"))
    assert v["package_id"] == "wp-6939-01"
    assert v["verdict"] == "pass", [c for c in v["checks"] if c["status"] != "pass"]
    items = {c["acceptance_item"] for c in v["checks"]}
    for need in ("valid_json", "schema_pass", "source_locator_resolvable",
                 "source_hash_matches", "no_duplicate_ids",
                 "all_claims_have_evidence_or_explicit_unresolved_status"):
        assert need in items