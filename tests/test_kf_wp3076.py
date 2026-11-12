"""Tests for KF work package wp-3076-01 (asset registration of report 3076).

Positive: the shipped manifest passes every offline acceptance check.
Negative controls: each structural guarantee is broken on a copy and MUST be detected
(tampered quote, shifted span, duplicated id, drifted source, self-verified claim,
upgraded figure payload, foreign report_id).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kf_verify_3076 as verify  # noqa: E402

DOCS = ROOT / "docs" / "wp-3076-01"
FILES = [
    "source.md",
    "source_meta.json",
    "asset_manifest.json",
    "kf_result.wp-3076-01.json",
    "kf_result.v1.schema.json",
    "asset_manifest.v1.schema.json",
]


@pytest.fixture()
def workdir(tmp_path: Path) -> Path:
    for name in FILES:
        shutil.copy(DOCS / name, tmp_path / name)
    return tmp_path


def load(workdir: Path) -> tuple[dict, dict]:
    manifest = json.loads((workdir / "asset_manifest.json").read_text(encoding="utf-8"))
    envelope = json.loads((workdir / "kf_result.wp-3076-01.json").read_text(encoding="utf-8"))
    return manifest, envelope


def dump(workdir: Path, manifest: dict, envelope: dict) -> None:
    (workdir / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (workdir / "kf_result.wp-3076-01.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")


def result_of(report: dict, item: str) -> dict:
    return next(c for c in report["checks"] if c["acceptance_item"] == item)


# ----------------------------- positive -----------------------------
def test_offline_verification_all_executed_pass(workdir: Path) -> None:
    report = verify.run_checks(workdir, online=False)
    assert report["acceptance_all_pass"] is True
    executed = [c for c in report["checks"] if c["result"] != "NOT_RUN"]
    assert executed and all(c["result"] == "PASS" for c in executed)
    # network-only probe must never be reported as PASS without running
    assert result_of(report, "platform_figure_payload_status_current")["result"] == "NOT_RUN"
    assert report["verified_label_written"] is False


def test_counts_are_derived_not_declared(workdir: Path) -> None:
    manifest, _ = load(workdir)
    counts = manifest["counts"]
    assert counts["assets"] == len(manifest["assets"]) == 19
    assert sum(counts["by_class"].values()) == counts["assets"]
    assert sum(counts["by_payload_status"].values()) == counts["assets"]
    registry = next(a for a in manifest["assets"] if a["asset_id"] == "A07")
    assert counts["check_id_count"] == len([t for t in registry["locator"]["quote"].split(" / ") if t.strip()]) == 11


def test_no_extraction_claims_empty(workdir: Path) -> None:
    manifest, envelope = load(workdir)
    assert manifest["claims"] == [] and envelope["claims"] == []
    assert manifest["objective"] == {"register_assets": True, "classify_report_type": False}
    assert manifest["boundaries"]["claims_marked_verified"] == 0


def test_every_quote_is_a_unique_verbatim_substring(workdir: Path) -> None:
    manifest, _ = load(workdir)
    source = (workdir / "source.md").read_text(encoding="utf-8")
    for asset in manifest["assets"]:
        quote = asset["locator"]["quote"]
        assert quote in source, asset["asset_id"]
        assert source.count(quote) == 1, asset["asset_id"]


def test_source_hash_is_pinned_to_contract(workdir: Path) -> None:
    manifest, envelope = load(workdir)
    assert manifest["source"]["hash"] == verify.CONTRACT_HASH
    assert envelope["provenance"]["source_hash"] == "sha256:" + verify.CONTRACT_HASH
    assert manifest["source"]["chars"] == verify.CONTRACT_CHARS == 3712


def test_envelope_shape(workdir: Path) -> None:
    _, envelope = load(workdir)
    assert envelope["package_id"] == "wp-3076-01"
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "3076"
    assert "asset_manifest.json" in envelope["outputs"]


# ----------------------------- negative controls -----------------------------
def test_negative_tampered_quote_is_detected(workdir: Path) -> None:
    manifest, envelope = load(workdir)
    manifest["assets"][3]["locator"]["quote"] += "X"
    dump(workdir, manifest, envelope)
    report = verify.run_checks(workdir, online=False)
    assert result_of(report, "source_locator_resolvable")["result"] == "FAIL"
    # a tampered quote stays schema-legal (shape unchanged) -> schema_pass must NOT be used as the guard
    assert result_of(report, "schema_pass")["result"] == "PASS"


def test_negative_shifted_span_is_detected(workdir: Path) -> None:
    manifest, envelope = load(workdir)
    manifest["assets"][5]["locator"]["start_char"] += 1
    dump(workdir, manifest, envelope)
    report = verify.run_checks(workdir, online=False)
    assert result_of(report, "source_locator_resolvable")["result"] == "FAIL"


def test_negative_duplicate_asset_id_is_detected(workdir: Path) -> None:
    manifest, envelope = load(workdir)
    manifest["assets"][1]["asset_id"] = manifest["assets"][0]["asset_id"]
    dump(workdir, manifest, envelope)
    report = verify.run_checks(workdir, online=False)
    assert result_of(report, "no_duplicate_ids")["result"] == "FAIL"


def test_negative_source_drift_is_detected(workdir: Path) -> None:
    pinned = (workdir / "source.md").read_text(encoding="utf-8")
    (workdir / "source.md").write_text(pinned + "\n", encoding="utf-8")
    manifest, envelope = load(workdir)
    dump(workdir, manifest, envelope)
    report = verify.run_checks(workdir, online=False)
    assert result_of(report, "source_hash_matches")["result"] == "FAIL"


def test_negative_self_verified_claim_is_detected(workdir: Path) -> None:
    manifest, envelope = load(workdir)
    manifest["claims"] = [{"claim_id": "c1", "text": "x", "status": "verified"}]
    dump(workdir, manifest, envelope)
    report = verify.run_checks(workdir, online=False)
    assert result_of(report, "all_claims_have_evidence_or_explicit_unresolved_status")["result"] == "FAIL"
    assert result_of(report, "boundaries_and_no_self_verified")["result"] == "FAIL"


def test_negative_figure_payload_upgraded_is_detected(workdir: Path) -> None:
    manifest, envelope = load(workdir)
    fig = next(a for a in manifest["assets"] if a["asset_id"] == "A17")
    fig["payload"]["status"] = "in_report_record"
    dump(workdir, manifest, envelope)
    report = verify.run_checks(workdir, online=False)
    assert result_of(report, "all_claims_have_evidence_or_explicit_unresolved_status")["result"] == "FAIL"


def test_negative_foreign_report_id_is_detected(workdir: Path) -> None:
    manifest, envelope = load(workdir)
    envelope["report_id"] = "999"
    dump(workdir, manifest, envelope)
    report = verify.run_checks(workdir, online=False)
    assert result_of(report, "boundaries_and_no_self_verified")["result"] == "FAIL"
    # report_id pattern is ^[0-9]+$, so a foreign id is schema-legal: only the boundary check catches it
    assert result_of(report, "schema_pass")["result"] == "PASS"