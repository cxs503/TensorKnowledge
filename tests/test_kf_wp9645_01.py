#!/usr/bin/env python3
"""Offline invariant tests for work package wp-9645-01 (task_type=01-asset-registration).

Everything below runs without platform credentials: the source of record is cached verbatim as
docs/kf/wp-9645-01/source.md, so the whole registration can be re-derived locally.

    pytest tests/test_kf_wp9645_01.py -q

What is asserted (invariants, not "the script ran"):
  * the cached source is byte-identical to the pinned contract hash, and the manifest's claimed
    source hash/chars are that same byte string;
  * every locator quote is an exact slice of the source at the declared span, and the declared
    line numbers agree with the character offsets;
  * the manifest is reproducible offline from (source.md, platform_record) alone -- i.e. no
    artifact depends on hidden build state;
  * the registered-value audit is green *and* every quarantined quantity carries a reason;
  * assets unresolved or declared absent never carry an invented hash, and all carry a note;
  * the kf_result.v1 envelope is schema-valid, embeds the manifest byte-for-byte, and its
    provenance hash equals the pinned source hash;
  * claims stay empty with a reason, and nothing is marked `verified`;
  * sha256.txt covers exactly the seven deliverables with matching digests;
  * the report body carries the numbers it claims to inject from the JSON artifacts;
  * the scope guard holds: the package registers report 9645 and nothing else.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-9645-01"
SOURCE = PKG / "source.md"
MANIFEST = PKG / "asset_manifest.json"
SCHEMA = PKG / "asset_manifest.schema.json"
ENVELOPE = PKG / "kf_result.json"
LEDGER = PKG / "locator_check.json"
BODY = PKG / "report_body.md"
SHA = PKG / "sha256.txt"
FIGURE = PKG / "asset_coverage.png"
SHARED_SCHEMA = ROOT / "schemas" / "asset_manifest.v1.schema.json"
KF_SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
SCRIPT = ROOT / "scripts" / "kf" / "wp_9645_01_register.py"

REPORT_ID = "9645"
PACKAGE_ID = "wp-9645-01"
CONTRACT_HASH = "sha256:a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00"
CONTRACT_CHARS = 11824


def _load_register():
    spec = importlib.util.spec_from_file_location("wp_9645_01_register", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def reg():
    return _load_register()


@pytest.fixture(scope="module")
def source() -> str:
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


# --------------------------------------------------------------------- source integrity
def test_cached_source_matches_pinned_contract(source):
    raw = source.encode("utf-8")
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert len(source) == CONTRACT_CHARS
    assert len(source.split("\n")) == 196


def test_manifest_source_block_is_the_same_bytes(source, manifest):
    src = manifest["source"]
    assert src["hash"] == hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert src["chars"] == len(source)
    assert src["bytes_utf8"] == len(source.encode("utf-8"))
    assert src["contract_hash"] == CONTRACT_HASH
    assert src["hash_matches_contract"] is True
    assert src["chars_matches_contract"] is True
    assert src["title_matches_contract"] is True
    assert src["scenario_matches_contract"] is True


def test_scope_guard_is_report_9645_only():
    text = SCRIPT.read_text(encoding="utf-8")
    assert 'REPORT_ID = "9645"' in text
    # every report id literal in the script (endpoint, provenance URI, docstrings) is 9645
    assert set(re.findall(r"reports/(\d+)", text)) == {REPORT_ID}
    assert text.count("%s/tensor/reports/%s") == 1  # exactly one endpoint call
    assert text.count("tensor_reports") == 0


# --------------------------------------------------------------------- locators
def test_every_locator_is_a_verbatim_slice(source, manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert source[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert source.count("\n", 0, loc["start_char"]) + 1 == loc["start_line"], a["asset_id"]


def test_every_table_and_section_locator_slices_correctly(source, manifest):
    for t in manifest["tables"]:
        loc = t["locator"]
        assert source[loc["start_char"]:loc["end_char"]] == loc["quote"], t["table_id"]
        assert t["header"] in source
        # the locator covers the whole table block, which begins with the header + separator
        assert loc["quote"].startswith(t["header_quote"]), t["table_id"]
        assert t["header_quote"] == t["header"] + "\n" + loc["quote"].split("\n")[1]
        assert len(loc["quote"].split("\n")) == t["n_rows"] + 2, t["table_id"]
    for s in manifest["outline"]["sections"]:
        assert source[s["start_char"]:s["end_char"]] == s["heading"], s["section_id"]


def test_locator_ledger_is_independently_reproducible_and_clean(reg, source, manifest, ledger):
    recomputed = reg.locator_check(source, manifest)
    assert recomputed == ledger
    assert ledger["all_ok"] is True
    assert ledger["mismatches"] == []
    assert ledger["counts"]["assets_ok"] == ledger["counts"]["assets"] == len(manifest["assets"])
    assert ledger["counts"]["tables_ok"] == ledger["counts"]["tables"]
    assert ledger["counts"]["sections_ok"] == ledger["counts"]["sections"]


# --------------------------------------------------------------------- reproducibility
def test_manifest_is_reproducible_offline(reg, source, manifest):
    rebuilt = reg.build_manifest(source, manifest["source"]["platform_record"])
    assert rebuilt == manifest, "manifest is not reproducible from source.md alone"


def test_registered_value_audit_is_green(manifest):
    audit = manifest["number_audit"]
    assert audit["summary"]["all_passed"] is True
    assert audit["summary"]["failed"] == 0
    assert audit["summary"]["checks"] == len(audit["checks"]) >= 80
    assert {c["verdict"] for c in audit["checks"]} == {"PASS"}
    for c in audit["checks"]:
        assert c["error"] <= c["tolerance"], c["check_id"]


def test_audit_covers_the_expected_families_and_quarantines_with_reasons(manifest):
    audit = manifest["number_audit"]
    fams = set(audit["families"])
    for expected in ("F1_kappa_product", "F2_kappa_vs_ratio", "F3_phi", "F4_iso_table",
                     "F5_nonconservative", "F6_negative_control", "F7_derivative",
                     "F8_form_table", "F9_adjoint_table", "F10_inverse_consistency",
                     "F11_criteria_summary", "F12_cross_section"):
        assert expected in fams, expected
    assert audit["not_audited"], "a report with solver outputs must quarantine something"
    for na in audit["not_audited"]:
        assert na["reason"].strip(), na
        assert len(na["reason"]) > 15


def test_audit_recomputes_phi_without_scipy(reg):
    # P_f = Phi(-4) = 3.1671e-05 is the report's own target; the package uses math.erfc only
    assert abs(reg.phi(-4.0) - 3.167124183e-05) / 3.167124183e-05 < 1e-9


# --------------------------------------------------------------------- honesty rules
def test_unresolved_assets_never_carry_invented_hashes(manifest):
    for a in manifest["assets"]:
        assert a["note"].strip(), a["asset_id"]
        if a["resolution"] != "resolved_in_source":
            assert not re.search(r"\bsha256:[0-9a-f]{8,}", json.dumps(a)), a["asset_id"]
            assert a["resolution_check"]["result"] in ("unresolved", "absent")


def test_resolution_vocabulary_and_counts_agree(manifest):
    assets = manifest["assets"]
    assert all(a["resolution"] in ("resolved_in_source", "referenced_unresolved",
                                  "declared_absent") for a in assets)
    counts = manifest["counts"]
    assert counts["assets"] == len(assets)
    derived = {}
    for a in assets:
        derived[a["resolution"]] = derived.get(a["resolution"], 0) + 1
    assert counts["by_resolution"] == derived
    assert counts["resolved_in_source"] == derived.get("resolved_in_source", 0)
    assert counts["referenced_unresolved"] == derived.get("referenced_unresolved", 0)
    assert counts["declared_absent"] == derived.get("declared_absent", 0)
    assert sum(counts["by_class"].values()) == len(assets)


def test_asset_ids_are_unique_and_well_formed(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids == ["A%02d" % (i + 1) for i in range(len(ids))]
    assert len(set(ids)) == len(ids)


def test_claims_empty_and_nothing_is_verified(manifest):
    assert manifest["claims"] == []
    assert manifest["claims_empty_reason"].strip()

    def walk(obj):
        if isinstance(obj, dict):
            assert "verified" not in obj
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
        elif isinstance(obj, str):
            assert obj.strip().lower() != "verified"

    walk(manifest)


def test_figures_are_registered_from_platform_metadata_only(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure_reference"]
    assert len(figs) == 6
    names = {a["reference"]["platform_figure_name"] for a in figs}
    assert names == {f["name"] for f in manifest["source"]["platform_record"]["figures"]}
    assert all(a["resolution"] == "referenced_unresolved" for a in figs)
    assert all(f["has_payload"] is False
               for f in manifest["source"]["platform_record"]["figures"])


def test_normative_table_is_declared_absent_with_the_report_own_authority(manifest, source):
    absent = [a for a in manifest["assets"] if a["resolution"] == "declared_absent"]
    assert len(absent) == 1
    assert "ISO 19906" in absent[0]["label"]
    assert absent[0]["locator"]["quote"] in source
    assert "primary_source_verified" in absent[0]["note"]


# --------------------------------------------------------------------- schema / envelope
def test_manifest_validates_against_local_schema(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(manifest, json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_local_schema_is_a_redirect_of_the_shared_schema():
    local = json.loads(SCHEMA.read_text(encoding="utf-8"))
    shared = json.loads(SHARED_SCHEMA.read_text(encoding="utf-8"))
    assert local["properties"]["assets"] == shared["properties"]["assets"], \
        "asset shape must not diverge from the shared contract"
    assert local["properties"]["counts"] == shared["properties"]["counts"]
    assert local["properties"]["integrity"] == shared["properties"]["integrity"]
    assert local["properties"]["package_id"]["const"] == PACKAGE_ID
    assert local["properties"]["report_id"]["const"] == REPORT_ID
    # only the three identity consts may differ
    assert shared["properties"]["package_id"]["const"] != PACKAGE_ID
    assert shared["properties"]["assets"]["items"]["properties"].keys() == \
        local["properties"]["assets"]["items"]["properties"].keys()


def test_envelope_is_valid_and_consistent(envelope, manifest):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(envelope, json.loads(KF_SCHEMA.read_text(encoding="utf-8")))
    assert envelope["package_id"] == PACKAGE_ID
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == REPORT_ID
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_hash_matches"] is True
    assert envelope["outputs"]["asset_manifest.json"] == manifest


# --------------------------------------------------------------------- digests / report / figure
def test_sha256_txt_covers_all_deliverables():
    rows = {}
    for line in SHA.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, path = line.split("  ", 1)
        rows[path] = digest
    expected = {
        "docs/kf/wp-9645-01/source.md",
        "docs/kf/wp-9645-01/asset_manifest.json",
        "docs/kf/wp-9645-01/asset_manifest.schema.json",
        "docs/kf/wp-9645-01/kf_result.json",
        "docs/kf/wp-9645-01/locator_check.json",
        "docs/kf/wp-9645-01/report_body.md",
        "docs/kf/wp-9645-01/asset_coverage.png",
    }
    assert set(rows) == expected
    for path, digest in rows.items():
        actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
        assert actual == digest, path


def test_report_body_carries_the_injected_numbers(manifest, ledger):
    body = BODY.read_text(encoding="utf-8")
    audit = manifest["number_audit"]["summary"]
    for needle in (manifest["source"]["hash"],
                   str(manifest["counts"]["assets"]),
                   str(audit["checks"]),
                   str(audit["passed"]),
                   "%d/%d" % (ledger["counts"]["assets_ok"], ledger["counts"]["assets"]),
                   manifest["assets"][-1]["asset_id"]):
        assert needle in body, needle
    for heading in ("① 案例介绍", "② 怎么做的", "③ 计算结果", "④ 结果图", "⑤ 注意点", "⑥ 误差判定"):
        assert heading in body, heading
    assert "<3 %" in body and "显式回答" in body
    assert "![asset coverage](asset_coverage.png)" in body


def test_report_body_has_no_stale_values(manifest):
    """The report must not claim numbers that the JSON artifacts do not contain."""
    body = BODY.read_text(encoding="utf-8")
    n_assets = manifest["counts"]["assets"]
    for m in re.finditer(r"(\d+) 个资产", body):
        assert int(m.group(1)) == n_assets
    assert "75/75" not in body or manifest["number_audit"]["summary"]["checks"] == 75


def test_coverage_figure_is_a_real_png():
    head = FIGURE.read_bytes()[:8]
    assert head == b"\x89PNG\r\n\x1a\n"
    assert FIGURE.stat().st_size > 20000


def test_no_bytecode_or_cache_is_shipped():
    assert not list(PKG.rglob("__pycache__"))
    assert not list(PKG.rglob("*.pyc"))