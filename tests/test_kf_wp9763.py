"""Invariant tests for work package wp-9763-01 (asset registration of report 9763).

Positive assertions pin the delivered artifacts; the negative-control tests mutate an in-memory copy
and require the check kernel to go RED, so a green suite means the checks are live rather than merely
executed.

Run: pytest tests/test_kf_wp9763.py -q
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import kf_verify_9763 as kv  # noqa: E402

MAN_PATH = ROOT / "artifacts/wp-9763-01/asset_manifest.json"
ENV_PATH = ROOT / "runs/wp-9763-01/kf_result.wp-9763-01.json"
MD_PATH = ROOT / "runs/wp-9763-01/report_9763.md"
CONTRACT_HASH = "ca29ba6f428001ddc1546e10c82b71ad1a18dcbf1c2bd09a1abd96e9760b1df3"


@pytest.fixture(scope="module")
def man():
    return json.loads(MAN_PATH.read_text())


@pytest.fixture(scope="module")
def env():
    return json.loads(ENV_PATH.read_text())


@pytest.fixture(scope="module")
def md():
    return MD_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------- positive invariants

def test_source_hash_matches_contract_and_manifest(man, md):
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert man["source"]["hash"] == CONTRACT_HASH
    assert man["source"]["chars"] == len(md) == 3884
    assert man["source"]["bytes_utf8"] == len(md.encode())


def test_every_quote_reslices_exactly(man, md):
    assert kv.locator_failures(md, man["assets"]) == []


def test_quotes_are_unique_substrings(man, md):
    for a in man["assets"]:
        assert md.count(a["locator"]["quote"]) == 1, a["asset_id"]


def test_no_duplicate_asset_ids(man):
    assert kv.duplicate_ids(man["assets"]) == []
    assert len({a["asset_id"] for a in man["assets"]}) == man["counts"]["assets"] == len(man["assets"])


def test_schema_pass(man, env):
    jsonschema.validate(man, json.loads((ROOT / "schemas/asset_manifest.v1.wp-9763-01.schema.json").read_text()))
    jsonschema.validate(env, json.loads((ROOT / "schemas/kf_result.v1.schema.json").read_text()))


def test_envelope_carries_manifest_verbatim(man, env):
    assert env["outputs"]["asset_manifest.json"] == man
    assert kv.embedded_sha(env) == hashlib.sha256(MAN_PATH.read_bytes()).hexdigest()
    assert env["provenance"]["artifact_sha256"] == hashlib.sha256(MAN_PATH.read_bytes()).hexdigest()


def test_durable_mirror_is_byte_identical(man):
    assert (ROOT / "docs/kf/wp-9763-01/asset_manifest.json").read_bytes() == MAN_PATH.read_bytes()


def test_nothing_marked_verified(man, env):
    assert kv.verified_markers(man) == []
    assert kv.verified_markers(env) == []
    assert env["provenance"]["verification_status"] == "not_verified"


def test_scope_is_single_report(man, env):
    assert man["scope_boundary"]["report_ids_touched"] == ["9763"]
    assert man["report_id"] == env["report_id"] == "9763"
    assert man["scope_boundary"]["upstream_artifacts_modified"] is False


def test_claims_allowed_empty_but_policy_holds(man):
    assert man["claims"] == []
    assert kv.unbacked_claims(man) == []
    assert "claims_note" in man


def test_resolution_counts_consistent(man):
    c = man["counts"]
    actual = {}
    for a in man["assets"]:
        actual[a["resolution"]] = actual.get(a["resolution"], 0) + 1
    assert c["by_resolution"] == actual
    assert c["resolved_in_source"] == actual.get("resolved_in_source", 0)
    assert c["referenced_unresolved"] == actual.get("referenced_unresolved", 0)
    assert c["declared_absent"] == 0
    assert sum(c["by_class"].values()) == c["assets"]


def test_unresolved_assets_carry_the_failed_probe(man):
    for a in man["assets"]:
        if a["resolution"] == "referenced_unresolved":
            assert a["resolution_check"]["result"] in ("unresolved", "absent"), a["asset_id"]
    ids = [a["asset_id"] for a in man["assets"] if a["resolution"] == "referenced_unresolved"]
    assert ids == ["A25", "A30", "A31", "A32"]


def test_cross_checks_quotes_locate(man, md):
    for c in man["cross_checks"]:
        for ev in c.get("evidence", []):
            assert md.count(ev["quote"]) == 1, (c["check_id"], ev["quote"][:30])
            assert md.split("\n")[ev["line"]] == ev["quote"]


def test_key_cross_check_findings_present(man):
    results = {c["check_id"]: c["result"] for c in man["cross_checks"]}
    assert results["C3_pytest_count_conflict"] == "inconsistent"
    assert results["C4_metric_naming_drift"] == "inconsistent"
    assert results["C5_arith_reproduction"] == "consistent"
    assert results["C6_reference_column_circularity"] == "unresolved"  # handed to downstream, not adjudicated


def test_verification_report_overall_pass():
    v = json.loads((ROOT / "artifacts/wp-9763-01/verification.json").read_text())
    assert v["overall"] == "PASS"
    fails = [c["check"] for c in v["checks"] if c["result"] != "pass"]
    assert fails == []


# ---------------------------------------------------------------- negative controls

def test_negative_tampered_quote_is_caught(man, md):
    bad = copy.deepcopy(man["assets"])
    target = next(a for a in bad if a["asset_id"] == "A13")
    target["locator"]["quote"] = target["locator"]["quote"].replace("4.4721", "4.4722")
    failures = kv.locator_failures(md, bad)
    assert any(f["asset_id"] == "A13" and f["why"] == "quote != md[start:end]" for f in failures)


def test_negative_shifted_span_is_caught(man, md):
    bad = copy.deepcopy(man["assets"])
    target = next(a for a in bad if a["asset_id"] == "A14")
    target["locator"]["start_char"] += 1
    assert any(f["asset_id"] == "A14" for f in kv.locator_failures(md, bad))


def test_negative_line_span_drift_is_caught(man, md):
    bad = copy.deepcopy(man["assets"])
    target = next(a for a in bad if a["asset_id"] == "A05")
    target["locator"]["start_line"] += 1
    failures = kv.locator_failures(md, bad)
    assert any(f["asset_id"] == "A05" and "line numbers" in f["why"] for f in failures)


def test_negative_duplicate_id_is_caught(man):
    bad = copy.deepcopy(man["assets"])
    bad[3]["asset_id"] = bad[2]["asset_id"]
    assert kv.duplicate_ids(bad) == [bad[2]["asset_id"]]


def test_negative_claim_without_evidence_is_caught(man):
    bad = copy.deepcopy(man)
    bad["claims"] = [{"claim_id": "c1", "text": "U_cr 精确匹配 Theodorsen 解"}]
    assert len(kv.unbacked_claims(bad)) == 1


def test_negative_verified_marker_is_caught(man, env):
    bad = copy.deepcopy(env)
    bad["provenance"]["verification"] = "verified"
    assert kv.verified_markers(bad) != []
    bad2 = copy.deepcopy(man)
    bad2["assets"][0]["verified"] = True
    assert kv.verified_markers(bad2) != []


def test_negative_envelope_mismatch_is_caught(man, env):
    bad = copy.deepcopy(env)
    bad["outputs"]["asset_manifest.json"]["counts"]["assets"] += 1
    assert kv.embedded_sha(bad) != hashlib.sha256(MAN_PATH.read_bytes()).hexdigest()


def test_negative_schema_violation_is_caught(man):
    schema = json.loads((ROOT / "schemas/asset_manifest.v1.wp-9763-01.schema.json").read_text())
    bad = copy.deepcopy(man)
    del bad["integrity"]
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)


def test_negative_resolution_enum_is_caught(man):
    schema = json.loads((ROOT / "schemas/asset_manifest.v1.wp-9763-01.schema.json").read_text())
    bad = copy.deepcopy(man)
    bad["assets"][0]["resolution"] = "resolved_external_ok"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, schema)