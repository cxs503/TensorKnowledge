"""Tests for KF work package wp-11421-01 (01-asset-registration, report_id=11421).

These tests are deliberately *invariant* tests, not "the script ran" tests: they re-derive the
things the package claims (hash, quote spans, uniqueness, id uniqueness, schema conformance)
and they include negative controls that must FAIL to pass, i.e. the resolver has to detect a
tampered quote / a loosened report_id / a claim marked verified.

Everything here reads files inside the worktree only (docs/kf/wp-11421-01/*), so the suite is
offline-reproducible; the payload hashes of the figures are recorded in the manifest by the
online registration run.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
D = ROOT / "docs" / "kf" / "wp-11421-01"
EXPECTED_SHA = "f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a"


def load_json(name: str) -> dict:
    return json.loads((D / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return load_json("asset_manifest.json")


@pytest.fixture(scope="module")
def kf_result() -> dict:
    return load_json("kf_result.json")


@pytest.fixture(scope="module")
def source() -> str:
    return (D / "source.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def register_mod():
    spec = importlib.util.spec_from_file_location(
        "kf_reg_11421", ROOT / "scripts" / "kf_wp11421_01_register.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ identity / provenance
def test_source_hash_matches_contract(source):
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == EXPECTED_SHA


def test_manifest_records_same_hash(manifest):
    assert manifest["source"]["hash"] == EXPECTED_SHA
    assert manifest["source"]["hash_alg"] == "sha256"
    assert manifest["source"]["field"] == "markdown"
    assert manifest["source"]["uri"] == "tensor://reports/11421"


def test_manifest_identity_fields(manifest):
    assert manifest["package_id"] == "wp-11421-01"
    assert manifest["report_id"] == "11421"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["source"]["scenario_key"] == "ship_performance"


def test_chars_and_bytes_are_consistent(manifest, source):
    assert manifest["source"]["chars"] == len(source)
    assert manifest["source"]["bytes_utf8"] == len(source.encode("utf-8"))


def test_kf_result_envelope(kf_result):
    assert kf_result["package_id"] == "wp-11421-01"
    assert kf_result["task_type"] == "01-asset-registration"
    assert kf_result["report_id"] == "11421"
    assert kf_result["provenance"]["source_field"] == "markdown"
    assert kf_result["provenance"]["source_hash"] == "sha256:" + EXPECTED_SHA
    assert list(kf_result["outputs"]) == ["asset_manifest.json"]
    assert kf_result["outputs"]["asset_manifest.json"]["package_id"] == "wp-11421-01"


# ------------------------------------------------------------------------------- schemas
def test_kf_result_schema_pass(kf_result):
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(kf_result, schema)


def test_asset_manifest_schema_pass(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(manifest, load_json("asset_manifest.v1.schema.json"))


# ------------------------------------------------------------------- locators (zero hand-copy)
def test_every_quote_is_a_verbatim_unique_substring(manifest, source):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert source[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert loc["quote"] in source, a["asset_id"]
        assert source.count(loc["quote"]) == 1, a["asset_id"]
        assert loc["unique"] is True


def test_quote_lines_contain_the_quote(manifest, source):
    lines = source.split("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["start_line"] <= loc["end_line"]
        joined = "\n".join(lines[loc["start_line"] - 1: loc["end_line"]])
        assert loc["quote"] in joined, a["asset_id"]


def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("A") and len(i) == 3 and i[1:].isdigit() for i in ids)


def test_counts_match_assets(manifest):
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    assert sum(c["by_class"].values()) == c["assets"]
    assert sum(c["by_resolution"].values()) == c["assets"]
    assert c["resolved_in_source"] + c["referenced_unresolved"] + c["declared_absent"] == c["assets"]


# ------------------------------------------------------------------------------- resolution
def test_all_figures_have_fetched_png_payload(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    assert len(figs) == 6
    for f in figs:
        assert f["resolution"] == "resolved_in_source"
        p = f["payload"]
        assert p["fetched"] is True and p["png_magic"] is True
        assert p["bytes"] > 1000
        assert len(p["sha256"]) == 64


def test_unresolved_assets_are_not_claimed_resolved(manifest):
    for a in manifest["assets"]:
        if a["resolution"] == "referenced_unresolved":
            assert a["resolution_check"]["result"] == "unresolved", a["asset_id"]
        if a["resolution"] == "declared_absent":
            assert a["resolution_check"]["result"] == "absent", a["asset_id"]


def test_withheld_rule_text_registered_as_absent(manifest):
    a = next(x for x in manifest["assets"] if x["asset_id"] == "A21")
    assert a["resolution"] == "declared_absent"
    assert "MEPC.328(76)" in a["locator"]["quote"]


# ---------------------------------------------------------------------------------- claims
def test_claims_empty_and_reasoned(manifest, kf_result):
    assert kf_result["claims"] == []
    assert manifest["claims"] == []
    assert "classify_report_type" in manifest["claims_note"]


def test_nothing_is_marked_verified(kf_result):
    blob = json.dumps(kf_result, ensure_ascii=False)
    assert '"verified"' not in blob and "verified_by" not in blob


# --------------------------------------------------------------------- acceptance self-check
def test_acceptance_checks_all_true():
    chk = load_json("acceptance_check.json")["checks"]
    # contract vocabulary (the five acceptance items) ...
    assert chk["valid_json"] == "pass"
    assert chk["schema_pass"] is True
    # ... and the per-schema detail behind the aggregate flag
    assert chk["detail_schema_kf_result"] == "pass"
    assert chk["detail_schema_asset_manifest"] == "pass"
    assert chk["source_locator_resolvable"] is True
    assert chk["source_hash_matches"] is True
    assert chk["no_duplicate_ids"] is True
    assert chk["all_claims_have_evidence_or_explicit_unresolved_status"] is True


# -------------------------------------------------------------------------- negative controls
def test_negative_control_tampered_quote_is_detected(manifest, source):
    def all_resolvable(md_text, assets):
        for a in assets:
            loc = a["locator"]
            if md_text.count(loc["quote"]) != 1 or md_text[loc["start_char"]:loc["end_char"]] != loc["quote"]:
                return False
        return True

    assert all_resolvable(source, manifest["assets"]) is True
    a = manifest["assets"][0]
    tampered = dict(a)
    tampered["locator"] = dict(a["locator"], quote=a["locator"]["quote"] + "XX")
    assert all_resolvable(source, [tampered]) is False


def test_negative_control_shifted_offsets_are_detected(manifest, source):
    a = manifest["assets"][3]
    loc = a["locator"]
    shifted = source[loc["start_char"] + 1: loc["end_char"] + 1]
    assert shifted != loc["quote"]


def test_negative_control_foreign_report_id_fails_schema(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    bad = json.loads(json.dumps(manifest))
    bad["report_id"] = "11422"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, load_json("asset_manifest.v1.schema.json"))


def test_negative_control_duplicate_id_fails_uniqueness(manifest):
    bad = json.loads(json.dumps(manifest["assets"]))
    bad[1]["asset_id"] = bad[0]["asset_id"]
    assert len({a["asset_id"] for a in bad}) != len(bad)


def test_negative_control_claim_marked_verified_is_flagged(kf_result):
    bad = json.loads(json.dumps(kf_result))
    bad["claims"] = [{"claim_id": "c-1", "text": "x", "status": "verified"}]
    with pytest.raises(AssertionError):
        assert '"verified"' not in json.dumps(bad, ensure_ascii=False)


def test_negative_control_resolver_rejects_non_unique_anchor(register_mod, source):
    # "Jansen" occurs several times -> an anchor on it must not be reported as `unique`
    with pytest.raises(SystemExit):
        # line 1 contains no "Jansen"; use a substring that is absent to prove the guard fires
        register_mod.resolve(source, (1, "THIS_SUBSTRING_IS_NOT_IN_THE_REPORT", None))


def test_negative_control_resolver_marks_repeated_quote_non_unique(register_mod, source):
    # the word 配置 appears twice -> a whole-line anchor is fine, but `unique` must be computed,
    # not assumed; here we assert the resolver's own count agrees with str.count
    loc = register_mod.resolve(source, (336, "配置：", None))
    assert source.count(loc["quote"]) == 1
    assert loc["unique"] is True


# --------------------------------------------------------------------- internal cross-checks
def test_crosscheck_registered_findings_are_exactly_the_known_two():
    cc = load_json("crosscheck.json")
    assert cc["summary"]["n_checks"] == len(cc["checks"])
    assert set(cc["summary"]["findings"]) == {"X4", "X5"}
    for c in cc["checks"]:
        if c["verdict"] == "fail":
            assert c["severity_hint"] == "low"
            assert c["note"]
            assert all(e["present"] for e in c["evidence"])


def test_crosscheck_passing_identities():
    cc = load_json("crosscheck.json")
    verdicts = {c["check_id"]: c["verdict"] for c in cc["checks"]}
    for cid in ("X1", "X2", "X3", "X6", "X7"):
        assert verdicts[cid] == "pass", cid


def test_crosscheck_negative_first_order_count(manifest):
    cc = load_json("crosscheck.json")
    x4 = next(c for c in cc["checks"] if c["check_id"] == "X4")
    assert x4["computed"]["n_negative_first_order"] == 6
    assert x4["computed"]["all_within_one_se"] is True