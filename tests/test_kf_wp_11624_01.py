#!/usr/bin/env python3
"""Tests for KF work package wp-11624-01 (01-asset-registration).

Positive tests prove the emitted manifests satisfy the six acceptance items.
Negative tests are the important half: they tamper with a *copy* of the manifest
(quote drift, hash drift, duplicated id, unevidenced claim, verified stamp) and
assert the verifier rejects each one — i.e. the checks assert invariants instead
of merely executing code.

Run: python3 -m pytest tests/test_kf_wp_11624_01.py -q
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-11624-01"
OUT = ROOT / "knowledge" / "kf" / PKG


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


verify = _load("kf_verify_11624", "scripts/kf_wp_11624_01_verify.py")

MD = (OUT / "source_report_11624.md").read_text(encoding="utf-8")
MAN_BYTES = (OUT / "asset_manifest.json").read_bytes()
MAN = json.loads(MAN_BYTES)
REC = json.loads((OUT / "source_record.json").read_text(encoding="utf-8"))
RES = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


def run(man=None, res=None, md=None, rec=None, man_bytes=None):
    m = MAN if man is None else man
    return verify.evaluate(
        MD if md is None else md,
        REC if rec is None else rec,
        m,
        RES if res is None else res,
        MAN_BYTES if man_bytes is None else man_bytes,
    )


# --------------------------------------------------------------------- positive
def test_source_hash_matches_contract():
    c = run()["source_hash_matches"]
    assert c["pass"], c
    assert c["snapshot_sha256"] == (
        "a5a0885e7f86a7d7e46ba9e66dcd748d1607075c640484785fce58868aaedd33")
    assert c["chars"] == 4253


def test_every_locator_resolves_and_is_unique():
    c = run()["source_locator_resolvable"]
    assert c["pass"], c["bad"]
    assert c["assets_checked"] >= 25
    md_spans = [d for d in c["detail"] if "occurrences" in d]
    assert all(d["occurrences"] == 1 for d in md_spans)


def test_all_checks_pass_on_committed_artifacts():
    checks = run()
    assert all(v["pass"] for v in checks.values()), {
        k: v for k, v in checks.items() if not v["pass"]}


def test_no_duplicate_ids():
    assert run()["no_duplicate_ids"]["pass"]


def test_claims_empty_by_contract_and_nothing_verified():
    c = run()["claims_have_evidence_or_unresolved_status"]
    assert c["pass"] and c["claims"] == 0
    assert RES["provenance"]["verification_status"] == "not_verified"
    # every asset is either sourced or explicitly marked unresolved/absent
    for a in MAN["assets"]:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved",
                                  "declared_absent"}


def test_figure_declarations_have_no_bytes_and_no_body_anchor():
    figs = [a for a in MAN["assets"] if a["kind"] == "figure_declaration"]
    assert len(figs) == 4
    for f in figs:
        rc = f["resolution_check"]
        assert rc["result"] == "absent"
        assert rc["bytes_present"] is False
        assert rc["body_tokens_found"] == []
        assert f["resolution"] == "declared_absent"


def test_repro_is_offline_stable():
    """Re-running the verifier's evaluate() twice yields identical results (no hidden state)."""
    assert run() == run()


# --------------------------------------------------------------------- negative
def test_detects_quote_drift():
    man = copy.deepcopy(MAN)
    man["assets"][5]["locator"]["quote"] = man["assets"][5]["locator"]["quote"] + "（篡改）"
    c = run(man=man)["source_locator_resolvable"]
    assert not c["pass"]
    assert man["assets"][5]["asset_id"] in c["bad"]


def test_detects_char_span_shift():
    man = copy.deepcopy(MAN)
    man["assets"][3]["locator"]["start_char"] += 1  # span no longer equals quote
    c = run(man=man)["source_locator_resolvable"]
    assert not c["pass"]
    assert man["assets"][3]["asset_id"] in c["bad"]


def test_detects_non_unique_quote():
    man = copy.deepcopy(MAN)
    man["assets"][1]["locator"]["quote"] = "---"  # appears more than once in the source
    c = run(man=man)["source_locator_resolvable"]
    assert not c["pass"]
    assert man["assets"][1]["asset_id"] in c["bad"]


def test_detects_source_hash_drift():
    md_tampered = MD + "\n"  # one extra byte
    c = run(md=md_tampered)["source_hash_matches"]
    assert not c["pass"]


def test_detects_manifest_hash_drift():
    man = copy.deepcopy(MAN)
    man["source"]["hash"] = "0" * 64
    c = run(man=man)["source_hash_matches"]
    assert not c["pass"] and c["snapshot_matches_contract"] is True


def test_detects_duplicate_asset_id():
    man = copy.deepcopy(MAN)
    man["assets"].append(copy.deepcopy(man["assets"][1]))
    c = run(man=man)["no_duplicate_ids"]
    assert not c["pass"] and c["duplicates"]


def test_detects_unevidenced_claim():
    man = copy.deepcopy(MAN)
    man["claims"] = [{"claim_id": "C-U-1", "text": "无出处断言"}]
    c = run(man=man)["claims_have_evidence_or_unresolved_status"]
    assert not c["pass"] and c["claim_violations"] == ["C-U-1"]


def test_detects_verified_stamp():
    res = copy.deepcopy(RES)
    res["provenance"]["verification_status"] = "verified"
    c = run(res=res)["claims_have_evidence_or_unresolved_status"]
    assert not c["pass"]


def test_detects_schema_violation():
    man = copy.deepcopy(MAN)
    man["package_id"] = "wp-9999-01"
    assert not run(man=man)["schema_pass"]["pass"]


def test_detects_broken_record_pointer():
    man = copy.deepcopy(MAN)
    fig = next(a for a in man["assets"] if a["locator"]["source_field"] == "record")
    fig["locator"]["pointer"] = "/figures/99"
    c = run(man=man)["source_locator_resolvable"]
    assert not c["pass"] and fig["asset_id"] in c["bad"]


def test_detects_foreign_report_reference():
    man = copy.deepcopy(MAN)
    man["source"]["uri"] = "tensor://reports/99999"
    c = run(man=man)["single_report_scope"]
    assert not c["pass"] and c["foreign_report_refs"]