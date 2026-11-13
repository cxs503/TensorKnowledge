"""Tests for KF work package wp-8240-01 (task_type=01-asset-registration).

These assert the *invariants* of the emitted manifest against the committed
snapshot of the source report, not merely that files exist. They read only the
durable `docs/wp-8240-01/` copies (the push gate drops artifacts/** and runs/**),
so they keep working on a fresh clone and in CI.

Run: python3 -m pytest tests/test_kf_wp_8240.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "wp-8240-01"
MD = DOC / "source_8240.md"
MANIFEST = DOC / "asset_manifest.json"
ENVELOPE = DOC / "kf_result.wp-8240-01.json"
PAYLOAD = DOC / "source_8240.json"

CONTRACT_HASH = "113b007338c90e984af4be66352aae382cd90f7e976725e819825a95bfa46e7d"
CONTRACT_CHARS = 9689
CONTRACT_TITLE = ("EEXI attained 闭合链路（P73W2-N02）：Holtrop 阻力→推进功率→轴系效率→"
                  "gCO₂/(t·nm)，99.9%→<3% 精度传递")
CONTRACT_SCENARIO = "green_eexi_attained_closure"

pytestmark = pytest.mark.skipif(not MANIFEST.exists(),
                                reason="wp-8240-01 artifacts not present in this checkout")


@pytest.fixture(scope="module")
def source() -> str:
    return MD.read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text())


def test_source_snapshot_matches_contract(source):
    assert hashlib.sha256(source.encode()).hexdigest() == CONTRACT_HASH
    assert len(source) == CONTRACT_CHARS


def test_source_is_report_8240_only():
    payload = json.loads(PAYLOAD.read_text())
    assert str(payload["id"]) == "8240"
    assert payload["title"] == CONTRACT_TITLE
    assert payload["scenario_key"] == CONTRACT_SCENARIO
    assert payload["markdown"] == MD.read_text()


def test_manifest_source_block(manifest, source):
    src = manifest["source"]
    assert src["uri"] == "tensor://reports/8240"
    assert src["field"] == "markdown"
    assert src["hash"] == CONTRACT_HASH
    assert src["chars"] == len(source) == CONTRACT_CHARS
    assert src["bytes_utf8"] == len(source.encode())
    assert src["title"] == CONTRACT_TITLE
    assert src["scenario_key"] == CONTRACT_SCENARIO


def test_manifest_and_envelope_schema(manifest, envelope):
    jsonschema.validate(
        manifest, json.loads((ROOT / "schemas/asset_manifest.v1.1.schema.json").read_text()))
    jsonschema.validate(
        envelope, json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text()))


@pytest.mark.parametrize("field", ["asset_id", "asset_class", "label", "in_report_section",
                                   "locator", "resolution", "resolution_check", "note"])
def test_every_asset_has_required_field(manifest, field):
    assert all(field in a for a in manifest["assets"])


def test_quotes_are_verbatim_unique_and_span_consistent(manifest, source):
    lines = source.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1

    def line_of(char: int) -> int:
        i = 0
        while i + 1 < len(offs) and offs[i + 1] <= char:
            i += 1
        return i

    problems = []
    for a in manifest["assets"]:
        loc, aid = a["locator"], a["asset_id"]
        q = loc["quote"]
        if not q or source.count(q) != 1:
            problems.append(f"{aid}: quote missing or not unique (count={source.count(q)})")
            continue
        if loc["method"] == "char_span":
            if source[loc["start_char"]:loc["end_char"]] != q:
                problems.append(f"{aid}: span does not reproduce quote")
            if (line_of(loc["start_char"]), line_of(loc["end_char"] - 1)) != (
                    loc["start_line"], loc["end_line"]):
                problems.append(f"{aid}: line span inconsistent with char span")
        else:
            assert (loc["start_char"], loc["end_char"]) == (0, len(source))
    assert not problems, problems


def test_asset_ids_unique_and_ascending(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert [int(i[1:]) for i in ids] == list(range(1, len(ids) + 1))


def test_counts_match_actual_assets(manifest):
    by_class, by_res = {}, {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"]) == len(manifest["assets"])
    assert c["by_class"] == by_class
    assert c["by_resolution"] == by_res
    assert c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
    assert c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
    assert c["declared_absent"] == by_res.get("declared_absent", 0)


def test_coverage_gate_non_heading_lines(manifest, source):
    lines = source.split("\n")
    covered = set()
    for a in manifest["assets"]:
        if a["locator"]["method"] == "document":
            continue
        covered.update(range(a["locator"]["start_line"], a["locator"]["end_line"] + 1))
    bare = [ln for i, ln in enumerate(lines) if i not in covered and ln.strip()]
    assert bare, "coverage gate would be vacuous"
    assert all(ln.lstrip().startswith("#") or ln.strip() == "```" for ln in bare)
    assert manifest["structural_lines_not_registered"]["count"] == len(bare)


def test_claims_rule(manifest):
    for cl in manifest["claims"]:
        assert cl.get("status") or cl.get("evidence") or cl.get("evidence_locator")
    assert manifest["claims"] == []  # no extraction in this work package


def test_envelope_outputs_and_provenance(manifest, envelope):
    assert envelope["package_id"] == manifest["package_id"] == "wp-8240-01"
    assert envelope["report_id"] == manifest["report_id"] == "8240"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["verification_status"] == "not_verified"
    assert envelope["outputs"]["asset_manifest.json"] == manifest


def test_no_claim_marked_verified(manifest, envelope):
    blob = json.dumps([manifest, envelope], ensure_ascii=False).lower()
    assert '"verified"' not in blob.replace('"not_verified"', "")


def test_unresolved_assets_declare_the_check_that_failed(manifest):
    for a in manifest["assets"]:
        rc = a["resolution_check"]
        if a["resolution"] == "resolved_in_source":
            assert rc["result"] in ("resolved", "present")
        else:
            assert rc["result"] in ("unresolved", "absent")
            assert rc.get("detail") or rc.get("worktree_hit")