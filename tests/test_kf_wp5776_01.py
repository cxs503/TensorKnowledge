"""Offline acceptance tests for work package wp-5776-01 (asset registration, report 5776).

No network, no database: every assertion runs against the artifacts committed with this
work package plus the local markdown copy in runs/wp-5776-01/.

Run: python3 -m pytest tests/test_kf_wp5776_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re

import jsonschema
import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-5776-01"
MANIFEST_P = PKG_DIR / "asset_manifest.json"
RESULT_P = PKG_DIR / "kf_result.wp-5776-01.json"
SCHEMA_MANIFEST = PKG_DIR / "asset_manifest.v1_5776.schema.json"
SCHEMA_KF = PKG_DIR / "kf_result.v1.schema.json"
MD_P = REPO / "runs" / "wp-5776-01" / "report_5776.md"
CONSIST_P = REPO / "runs" / "wp-5776-01" / "consistency_check.json"

CONTRACT_HASH = "49089e9b193af49f9ffcf4f35b8a82b6f4deec5da07edc8e654fc7902385c04f"
CONTRACT_CHARS = 4950


@pytest.fixture(scope="module")
def md() -> str:
    return MD_P.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_P.read_text(encoding="utf-8"))


def _line_offsets(md: str):
    offs, pos = [], 0
    for i, ln in enumerate(md.split("\n"), start=1):
        offs.append((i, pos, pos + len(ln)))
        pos += len(ln) + 1
    return offs


def test_source_hash_and_chars_match_contract(md):
    raw = md.encode("utf-8")
    assert hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_report_identity_is_5776_only(manifest):
    assert manifest["report_id"] == "5776"
    assert manifest["package_id"] == "wp-5776-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["provenance"]["source_uri"] == "tensor://reports/5776"
    assert manifest["provenance"]["source_field"] == "markdown"


def test_provenance_hash_matches_local_copy(manifest, md):
    declared = manifest["provenance"]["source_hash"].split("sha256:")[-1]
    assert declared == hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH


def test_manifest_schema(manifest):
    jsonschema.validate(manifest, json.loads(SCHEMA_MANIFEST.read_text(encoding="utf-8")))


def test_result_envelope_schema_and_hash(result=None):
    res = json.loads(RESULT_P.read_text(encoding="utf-8"))
    jsonschema.validate(res, json.loads(SCHEMA_KF.read_text(encoding="utf-8")))
    md_raw = MD_P.read_bytes()
    assert res["provenance"]["source_hash"] == "sha256:" + hashlib.sha256(md_raw).hexdigest()
    assert res["provenance"]["source_hash"].split("sha256:")[-1] == CONTRACT_HASH
    assert res["report_id"] == "5776" and res["package_id"] == "wp-5776-01"
    assert set(res) <= {"package_id", "task_type", "report_id", "provenance", "outputs", "claims"}


def test_outputs_carry_the_manifest_verbatim():
    res = json.loads(RESULT_P.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_P.read_text(encoding="utf-8"))
    assert "asset_manifest.json" in res["outputs"]
    assert res["outputs"]["asset_manifest.json"] == manifest


def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 1
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)
    assert manifest["counts"]["assets"] == len(ids)


def test_every_locator_resolves_byte_exactly(manifest, md):
    offs = _line_offsets(md)
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["method"] == "char_span", a["asset_id"]
        s, e = loc["start_char"], loc["end_char"]
        assert 0 <= s < e <= len(md), a["asset_id"]
        assert md[s:e] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) == 1, a["asset_id"]
        assert (offs[loc["start_line"] - 1][1], offs[loc["end_line"] - 1][2]) == (s, e), a["asset_id"]


def test_resolution_status_is_consistent_with_check(manifest):
    for a in manifest["assets"]:
        if a["resolution"] == "resolved_in_source":
            assert a["resolution_check"] == {"check": "char_span_in_source_markdown", "result": "resolved"}
        elif a["resolution"] == "referenced_unresolved":
            assert a["resolution_check"]["result"] == "unresolved"
        else:
            assert a["resolution"] == "declared_absent"


def test_figure_assets_claim_no_bytes(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure_attachment"]
    assert len(figs) == 3
    for a in figs:
        assert a["resolution"] == "referenced_unresolved"
        assert a["platform_metadata"]["bytes_available"] is False
        assert "attachment:" in a["locator"]["quote"]
        # the name in the attachment URI must be the platform-recorded figure name
        name = re.search(r"attachment:([^)]+)", a["locator"]["quote"]).group(1)
        assert name == a["platform_metadata"]["name"]


def test_claims_empty_and_never_verified(manifest):
    assert manifest["claims"] == []
    assert manifest["provenance"]["verification_status"] == "not_verified"
    for c in manifest["claims"]:
        assert "verified" not in json.dumps(c)


def test_counts_agree_with_assets(manifest):
    assets = manifest["assets"]
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert manifest["counts"]["by_class"] == by_class
    assert manifest["counts"]["by_resolution"] == by_res
    assert manifest["counts"]["assets"] == sum(by_class.values())


def test_consistency_check_recomputes():
    """The audit numbers must be reproducible from the source with no hand-typed values."""
    c = json.loads(CONSIST_P.read_text(encoding="utf-8"))
    md = MD_P.read_text(encoding="utf-8")
    rho_w = float(re.search(r"ρ_w=([0-9.]+) kg/m³", md).group(1))
    rho_i = float(re.search(r"ρ_i=([0-9.]+) kg/m³", md).group(1))
    factor = math.sqrt(rho_w / rho_i)
    assert c["factor"] == pytest.approx(factor, rel=1e-12)
    assert c["inputs_parsed_from_source"]["rho_w"] == rho_w
    assert c["inputs_parsed_from_source"]["rho_i"] == rho_i
    assert len(c["rows"]) == 9
    for r in c["rows"]:
        assert r["U_analytical_table"] == pytest.approx(r["U_current"] * factor, rel=1e-3)
        assert r["dev_analytical_rel"] < 0.03
        assert r["dev_sim_rel"] < 0.03
    assert c["summary"]["analytical_column_within_3pct"] is True
    assert c["summary"]["sim_column_within_3pct"] is True
    # honesty guard: the audit must not present itself as platform verification
    assert "NOT platform verification" in c["scope"]


def test_work_package_does_not_reach_other_reports(manifest):
    blob = json.dumps(manifest, ensure_ascii=False)
    assert "tensor://reports/5776" in blob
    assert not re.search(r"wp-(?!5776-01)\d+-\d{2}", blob)
    assert manifest["provenance"]["source_uri"].count("5776") == 1

def test_delivery_markdown_embeds_result_as_single_json_block():
    text = (PKG_DIR / "KF-RESULT-wp-5776-01.md").read_text(encoding="utf-8")
    assert text.startswith("# KF-RESULT wp-5776-01")
    # quotes inside the embedded manifest contain fenced blocks (```bash), so the envelope fence is
    # matched with real newlines on both sides rather than by naive "```json".split()
    found = re.findall(r"\n```json\n(.*?)\n```\n", text, flags=re.S)
    assert len(found) == 1
    assert json.loads(found[0]) == json.loads(RESULT_P.read_text(encoding="utf-8"))
