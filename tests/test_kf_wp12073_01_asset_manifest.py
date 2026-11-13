"""Invariant tests for KF work package wp-12073-01 (01-asset-registration, report 12073).

These tests do not re-run the pipeline; they assert the *invariants* the committed
artifacts must satisfy, so a silent drift (edited manifest, hand-copied number, id
collision, locator that no longer resolves) fails here instead of passing review.

They are offline by construction: every check reads committed files only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "kf", "wp-12073-01")
SNAPSHOT = os.path.join(OUT, "source", "report_12073.md")
FIGDIR = os.path.join(OUT, "source", "figures")

CONTRACT_HASH = "sha256:362fbe90ba196e81f94aa4f6dd9d74bc5f69c729e7eb9f99a125fb9415bea850"
CONTRACT_CHARS = 3446


@pytest.fixture(scope="module")
def md() -> str:
    return open(SNAPSHOT, encoding="utf-8").read()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.load(open(os.path.join(OUT, "asset_manifest.json"), encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))


def test_source_hash_pinned(md: str, manifest: dict, envelope: dict) -> None:
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    assert manifest["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert manifest["provenance"]["source_chars"] == CONTRACT_CHARS


def test_envelope_shape_and_identity(envelope: dict) -> None:
    assert envelope["package_id"] == "wp-12073-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "12073"
    assert envelope["provenance"]["source_field"] == "markdown"
    # only the declared output file is emitted
    assert set(envelope["outputs"]) == {"asset_manifest.json"}
    assert envelope["outputs"]["asset_manifest.json"]["report_id"] == "12073"


def test_envelope_validates_against_repo_schema(envelope: dict) -> None:
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"),
                            encoding="utf-8"))
    jsonschema.validate(envelope, schema)


def test_every_locator_resolves_verbatim(md: str, manifest: dict) -> None:
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            assert loc["start_char"] == 0 and loc["end_char"] == len(md)
            assert loc["quote"] in md
            continue
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) >= 1
        assert loc["unique"] == (md.count(loc["quote"]) == 1), a["asset_id"]


def test_line_numbers_consistent(md: str, manifest: dict) -> None:
    for a in manifest["assets"]:
        loc = a["locator"]
        assert md.count("\n", 0, loc["start_char"]) + 1 == loc["start_line"], a["asset_id"]
        assert loc["start_line"] <= loc["end_line"]


def test_no_duplicate_asset_ids(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == [f"A{i:02d}" for i in range(1, len(ids) + 1)]  # contiguous, ordered


def test_claims_empty_and_well_formed(manifest: dict, envelope: dict) -> None:
    # contract: "claims 允许为空数组" — zero claims is a complete result, not a gap
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    for c in manifest["claims"]:
        assert c.get("evidence") or c.get("status")


def test_unresolved_assets_claim_no_payload_hash(manifest: dict) -> None:
    for a in manifest["assets"]:
        if a["resolution"] == "referenced_unresolved":
            assert not (a.get("payload") or {}).get("sha256"), a["asset_id"]
            assert a["resolution_check"]["result"] == "unresolved"


def test_figure_bytes_match_manifest(manifest: dict) -> None:
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    assert figs, "report 12073 declares 5 figures"
    for a in figs:
        path = os.path.join(FIGDIR, a["payload"]["name"])
        blob = open(path, "rb").read()
        assert len(blob) == a["payload"]["bytes"]
        assert "sha256:" + hashlib.sha256(blob).hexdigest() == a["payload"]["sha256"]
        assert a["locator"]["quote"] == a["payload"]["name"]


def test_counts_consistent_with_assets(manifest: dict) -> None:
    assets = manifest["assets"]
    counts = manifest["counts"]
    assert counts["assets"] == len(assets)
    assert sum(counts["by_class"].values()) == len(assets)
    assert sum(counts["by_resolution"].values()) == len(assets)
    for k in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert counts[k] == sum(1 for a in assets if a["resolution"] == k)


def test_quote_uniqueness_ledger_is_complete(manifest: dict) -> None:
    spans = [a for a in manifest["assets"] if a["locator"]["method"] == "char_span"]
    ledger = manifest["integrity"]["quote_uniqueness"]
    assert ledger["total"] == len(spans)
    assert ledger["unique"] == sum(1 for a in spans if a["locator"]["unique"])
    assert [x["asset_id"] for x in ledger["non_unique"]] == \
        [a["asset_id"] for a in spans if not a["locator"]["unique"]]
    assert ledger["unique"] + len(ledger["non_unique"]) == ledger["total"]


def test_report_markdown_carries_exactly_one_json_block() -> None:
    md = open(os.path.join(OUT, "KF-RESULT-wp-12073-01.md"), encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    assert len(blocks) == 1
    parsed = json.loads(blocks[0])
    committed = json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))
    assert parsed == committed  # the published block IS the committed envelope
    assert md.splitlines()[0] == "# KF-RESULT wp-12073-01"

def test_locators_also_resolve_under_ke_gate_semantics(md: str, manifest: dict) -> None:
    """Cross-check against the platform's own locator resolver (ke/wp_gate.py).

    ``ke.wp_gate.locator_matches`` declares ``start_offset``/``end_offset`` as the
    contract and otherwise searches the quote verbatim. Asserting both the
    ``char_span`` mapping and the search fallback keeps the manifest readable by the
    KE gate even though this package's schema names the fields ``start_char``/``end_char``.
    """
    from ke import wp_gate

    for a in manifest["assets"]:
        loc = a["locator"]
        ok, code, detail = wp_gate.locator_matches(md, {"quote": loc["quote"]})
        assert ok, (a["asset_id"], code, detail)
        if loc["method"] == "char_span":
            ok, code, detail = wp_gate.locator_matches(
                md, {"quote": loc["quote"], "start_offset": loc["start_char"],
                     "end_offset": loc["end_char"]})
            assert ok and code == "OK_OFFSETS", (a["asset_id"], code, detail)
