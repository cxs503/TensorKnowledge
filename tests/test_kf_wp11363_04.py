"""Invariant tests for the wp-11363-04 review package.

These assert properties of the delivered artefacts (not merely that code runs):
  * the envelope satisfies the canonical KF-RESULT schema — the very item the
    reviewed package wp-11363-01 fails (finding F3);
  * provenance.source_hash equals a fresh sha256 of the fetched markdown;
  * every reviewed-package locator and every review evidence locator resolves
    byte-exactly (slice == quote, line, occurrence count);
  * the verdict is consistent with the blocking/non-blocking finding split;
  * no claim is marked verified and no other report_id leaks in.

Mutation cases prove the locator check can actually go red.
"""
import hashlib
import json
import os
import re
import sys

import jsonschema
import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "kf", "wp-11363-04")
PKG01 = os.path.join(ROOT, "docs", "kf", "wp-11363-01")
SNAPSHOT = os.path.join(ROOT, "runs", "m19810", "source_11363.md")
CONTRACT_HASH = "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23"


def load(name, base=OUT):
    with open(os.path.join(base, name), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def src():
    with open(SNAPSHOT, "rb") as fh:
        raw = fh.read()
    return raw.decode("utf-8"), raw


@pytest.fixture(scope="module")
def envelope():
    return load("kf_result.json")


@pytest.fixture(scope="module")
def review(envelope):
    return envelope["outputs"]["review_report.json"]


def test_envelope_validates_against_canonical_schema(envelope):
    schema = load("kf_result.v1.schema.json", os.path.join(ROOT, "schemas"))
    jsonschema.validate(envelope, schema)
    assert set(envelope) <= {"package_id", "task_type", "contract_version", "report_id",
                             "provenance", "outputs"}, "no additional root properties allowed"


def test_reviewed_package_still_fails_that_schema():
    """The blocking finding F3 must be reproducible, not asserted."""
    schema = load("kf_result.v1.schema.json", os.path.join(ROOT, "schemas"))
    with pytest.raises(jsonschema.ValidationError) as exc:
        jsonschema.validate(load("kf_result.json", PKG01), schema)
    assert "claims" in str(exc.value)


def test_source_hash_and_size(src, envelope):
    md, raw = src
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    prov = envelope["provenance"]
    assert prov["source_hash"] == CONTRACT_HASH
    assert prov["source_hash_matches"] is True
    assert prov["chars"] == len(md) == 6902
    assert len(md.splitlines()) == 124


def test_review_evidence_locators_resolve(src, review):
    md, _raw = src
    rows = review["evidence_locators"]
    assert len(rows) >= 8
    for row in rows:
        s, e = row["char_span"]
        assert md[s:e] == row["quote"], row["claim_id"]
        assert md.count(row["quote"]) == row["occurrences_in_source"], row["claim_id"]
        assert md.count("\n", 0, s) + 1 == row["line"], row["claim_id"]
        assert row["byte_exact"] is True


def test_reviewed_package_locators_resolve(src):
    """Independent re-resolution of all 25 locators of wp-11363-01."""
    md, _raw = src
    manifest = load("asset_manifest.json", PKG01)
    assert len(manifest["assets"]) == 25
    for asset in manifest["assets"]:
        loc = asset["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], asset["asset_id"]
        assert md.count("\n", 0, loc["start_char"]) + 1 == loc["line"], asset["asset_id"]
        assert md.count(loc["quote"]) == loc["count_occurrences"], asset["asset_id"]


def test_locator_check_can_go_red(src):
    """Mutation: a shifted span or an edited quote must be detected."""
    md, _raw = src
    manifest = load("asset_manifest.json", PKG01)
    a = manifest["assets"][1]["locator"]
    shifted = (a["start_char"] + 1, a["end_char"] + 1)
    assert md[shifted[0]:shifted[1]] != a["quote"]
    edited = a["quote"][:-1] + ("X" if a["quote"][-1] != "X" else "Y")
    assert md.find(edited) < 0


def test_verdict_matches_findings(review):
    findings = review["findings"]
    blocking = [f["id"] for f in findings if f["blocking"]]
    non_blocking = [f["id"] for f in findings if not f["blocking"]]
    assert review["blocking_findings"] == blocking
    assert review["non_blocking_findings"] == non_blocking
    if blocking:
        assert review["verdict"] in ("needs-fix", "fail")
    else:
        assert review["verdict"] in ("pass", "pass_with_notes")
    for f in findings:
        assert f["evidence"] and f["reproduction"] and f["affected_scope"]
    assert {"high", "medium"} >= {f["severity"] for f in findings if f["blocking"]}


def test_checks_are_the_ledger(review):
    """The published check table must be the recomputed ledger, not a retyped copy."""
    ledger = review["check_ledger"]["checks"]
    assert {k: v["status"] for k, v in ledger.items()} == \
           {k: v["status"] for k, v in review["checks"].items()}
    assert all(v["detail"] for v in review["checks"].values())


def test_acceptance_items_are_explicit(review):
    acc = review["acceptance"]
    assert set(acc) == {"valid_json", "schema_pass", "reviewer_independent",
                        "upstream_packages_completed"}
    assert acc["schema_pass"]["status"] == "fail", "F3 must stay visible in the acceptance table"
    assert acc["upstream_packages_completed"]["status"] == "unknown_not_run"


def test_no_verified_marks_and_single_report_id(envelope, review):
    assert review["verified_marks"]["count"] == 0
    blob = json.dumps(envelope, ensure_ascii=False)
    assert '"verified": true' not in blob
    for m in re.finditer(r'"report_id": "([^"]+)"', blob):
        assert m.group(1) == "11363"


def test_figure_probe_ledger_is_self_consistent(review):
    ledger = review["check_ledger"]["checks"]["C7_figure_probe_recheck"]["reprobe"]
    figures = [k for k in ledger if k != "figures_endpoint"]
    assert len(figures) == 4
    for k in figures:
        d, r = ledger[k]["declared"], ledger[k]["recomputed"]
        assert d["http_status"] == r["http_status"] == 200, k
        assert d["bytes"] == r["bytes"], k
        assert d["payload_sha256"] == r["sha256"], k
        assert r["png_magic_ok"] is True, k
    assert sum(ledger[k]["recomputed"]["bytes"] for k in figures) == 373525


def test_observation_contradiction_still_recorded(review):
    """F1 must stay reproducible from the artefact pair it cites."""
    f1 = [f for f in review["findings"] if f["id"] == "F1"][0]
    probes = f1["evidence"]["probes"]
    assert probes and all(p["http_status"] == 200 and p["payload_sha256"] for p in probes.values())
    assert "404" in f1["evidence"]["observation_text"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))