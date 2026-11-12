"""Machine gate for work package wp-5347-01 (process 01, report 5347).

Positive path: the emitted artefacts satisfy every acceptance line of the
contract.  Negative path (mutation tests): the verifier is *not* vacuous — each
acceptance line is shown to fail when the corresponding evidence is tampered
with.  A verifier that only ever says "passed" would be worthless, so these
mutations are the real content of this file.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "artifacts" / "wp-5347-01"
sys.path.insert(0, str(REPO / "scripts"))

import verify_wp_5347_01 as V  # noqa: E402
import wp_5347_01_register_assets as B  # noqa: E402

PKG = V.OUT


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _status(report: dict, name: str) -> str:
    for c in report["checks"]:
        if c["check"] == name:
            return c["status"]
    raise AssertionError(f"check {name} not reported; got {[c['check'] for c in report['checks']]}")


@pytest.fixture()
def pkg_copy(tmp_path: Path) -> Path:
    dst = tmp_path / "wp-5347-01"
    shutil.copytree(PKG, dst)
    return dst


def _rewrite_result(dst: Path, mutate) -> None:
    """Mutate kf_result.json, the on-disk manifest and the report block together."""
    res_p = dst / "kf_result.json"
    man_p = dst / "asset_manifest.json"
    rep_p = dst / f"KF-RESULT-{V.PACKAGE_ID}.md"
    res = json.loads(res_p.read_text(encoding="utf-8"))
    man = json.loads(man_p.read_text(encoding="utf-8"))
    mutate(man, res)
    res["outputs"]["asset_manifest.json"] = man
    man_p.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    res_p.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = rep_p.read_text(encoding="utf-8")
    head, _, _tail = md.partition("```json")
    rep_p.write_text(head + "```json\n" + json.dumps(res, ensure_ascii=False, indent=2) + "\n```\n",
                     encoding="utf-8")


# ---------------------------------------------------------------------------
# positive
# ---------------------------------------------------------------------------
def test_all_acceptance_lines_pass():
    report = V.run_checks(PKG)
    assert report["ok"] is True, json.dumps(
        [c for c in report["checks"] if c["status"] == "failed"], ensure_ascii=False)[:800]
    assert report["counts"]["failed"] == 0
    assert report["counts"]["not_run"] == 0


def test_zero_claim_case_is_reported_vacuous_not_passed():
    report = V.run_checks(PKG)
    assert _status(report, "A6.claims_have_evidence_or_unresolved") == "vacuous"


def test_source_snapshot_matches_contract_hash():
    """The snapshot is the provenance base; its bytes must still be the contract's."""
    data = (PKG / "report_5347.md").read_bytes()
    assert V.sha256_bytes(data) == V.CONTRACT_SOURCE_HASH
    assert len(data.decode("utf-8")) == V.CONTRACT_CHARS


def test_every_locator_is_verbatim_and_cites_its_own_path():
    text = (PKG / "report_5347.md").read_text(encoding="utf-8")
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    spans = [a for a in manifest["assets"] if a["locator"]["locator_type"] == "char_span"]
    assert spans, "expected char-span locators for every path asset"
    for a in spans:
        loc = a["locator"]
        quote = text[loc["start_offset"]:loc["end_offset"]]
        assert quote == loc["quote"]
        assert a["path"] in quote
        assert len(quote) >= V.MIN_QUOTE_CHARS


def test_no_asset_is_claimed_resolved_without_bytes():
    """Process 01 must not overstate reachability: nothing here ships bytes."""
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"]["resolved"] == 0
    assert manifest["counts"]["unresolved"] == manifest["counts"]["assets"]
    assert len(manifest["unresolved"]) == manifest["counts"]["assets"]
    for a in manifest["assets"]:
        assert a["reachability"] in B.REACHABILITY and a["resolution_note"]


def test_extraction_and_classification_were_not_performed():
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    reg = manifest["registration"]
    assert reg["extraction_performed"] is False
    assert reg["classification_performed"] is False
    assert reg["claims_extracted"] == 0
    result = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    assert result["claims"] == []


def test_report_markdown_has_exactly_one_json_block_and_six_sections():
    md = (PKG / f"KF-RESULT-{V.PACKAGE_ID}.md").read_text(encoding="utf-8")
    assert md.count("```json") == 1
    assert md.lstrip().startswith(f"# KF-RESULT {V.PACKAGE_ID}")
    for marker in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert marker in md, marker
    assert "repro_cmd" in md


# ---------------------------------------------------------------------------
# negative (mutation) — proves each acceptance line can actually fail
# ---------------------------------------------------------------------------
def test_tampered_source_bytes_fail_hash_check(pkg_copy: Path):
    src = pkg_copy / "report_5347.md"
    src.write_bytes(src.read_bytes() + b"\n<!-- injected -->\n")
    assert _status(V.run_checks(pkg_copy), "A3.source_hash_matches") == "failed"


def test_tampered_quote_offset_fails_locator_check(pkg_copy: Path):
    def mutate(man, _res):
        man["assets"][0]["locator"]["start_offset"] += 1
    _rewrite_result(pkg_copy, mutate)
    assert _status(V.run_checks(pkg_copy), "A4.source_locator_resolvable") == "failed"


def test_duplicate_asset_id_fails(pkg_copy: Path):
    def mutate(man, _res):
        man["assets"][1]["asset_id"] = man["assets"][0]["asset_id"]
    _rewrite_result(pkg_copy, mutate)
    assert _status(V.run_checks(pkg_copy), "A5.no_duplicate_ids") == "failed"


def test_injected_claim_without_evidence_fails(pkg_copy: Path):
    res_p = pkg_copy / "kf_result.json"
    res = json.loads(res_p.read_text(encoding="utf-8"))
    res["claims"] = [{"claim_id": "5347-c1", "text": "injected", "status": "supported"}]
    res_p.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    assert _status(V.run_checks(pkg_copy), "A6.claims_have_evidence_or_unresolved") == "failed"


def test_producer_written_verification_marker_fails(pkg_copy: Path):
    res_p = pkg_copy / "kf_result.json"
    res = json.loads(res_p.read_text(encoding="utf-8"))
    res["provenance"]["verification_status"] = "confirmed"
    res_p.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    assert _status(V.run_checks(pkg_copy), "A8.no_self_verification") == "failed"


def test_second_json_block_breaks_the_result_channel(pkg_copy: Path):
    rep = pkg_copy / f"KF-RESULT-{V.PACKAGE_ID}.md"
    rep.write_text(rep.read_text(encoding="utf-8") + "\n```json\n{}\n```\n", encoding="utf-8")
    assert _status(V.run_checks(pkg_copy), "A9.report_channel") == "failed"


def test_figure_registered_resolved_without_bytes_fails(pkg_copy: Path):
    """If a figure were promoted to a resolvable asset the honesty check must fire."""
    meta = json.loads((pkg_copy / "report_5347.md.meta.json").read_text(encoding="utf-8"))
    meta["figures"][0]["png_base64"] = "AAAA"
    (pkg_copy / "report_5347.md.meta.json").write_text(json.dumps(meta, ensure_ascii=False),
                                                       encoding="utf-8")
    assert _status(V.run_checks(pkg_copy), "A10.figure_honesty") == "failed"