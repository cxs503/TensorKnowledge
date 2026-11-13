"""KF work package wp-9091-01 (01-asset-registration) — delivered-artifact invariants.

Self-contained: the package ships a byte-exact copy of the source markdown
(`docs/wp-9091-01/report_9091.md`), so every locator, the source hash and the whole manifest can be
re-derived offline — no platform access, no network.

Run:  python3 -m pytest tests/test_kf_wp9091_01_asset_manifest.py -q
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib
import re

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "wp-9091-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.wp-9091-01.json"
VERIFICATION = PKG / "verification.json"
SOURCE_MD = PKG / "report_9091.md"
KF_RESULT_MD = PKG / "KF-RESULT-wp9091-01.md"
FIGURE = PKG / "fig_asset_inventory.png"
SCHEMA_GENERIC = ROOT / "schemas" / "asset_manifest.v1.generic.schema.json"
BUILDER = PKG / "build_manifest.py"

REPORT_ID = "9091"
PACKAGE_ID = "wp-9091-01"
# pinned by the work-package contract (sha256 over the utf-8 bytes of payload.markdown)
CONTRACT_HASH = "89c2a8f978e2915cb079337441118458e78017bcb4a177c38d8c8a00cc8c6f17"
CONTRACT_CHARS = 10060
CONTRACT_BYTES = 10955


def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest():
    return load(MANIFEST)


@pytest.fixture(scope="module")
def envelope():
    return load(ENVELOPE)


@pytest.fixture(scope="module")
def md():
    return SOURCE_MD.read_text(encoding="utf-8")


# ---------------------------------------------------------------- package shape
def test_package_files_present():
    for p in (MANIFEST, ENVELOPE, VERIFICATION, SOURCE_MD, KF_RESULT_MD, FIGURE, BUILDER):
        assert p.exists(), "missing deliverable: %s" % p.relative_to(ROOT)
    assert len(list(PKG.glob("*.pyc"))) == 0, "no bytecode may be committed"


def test_no_repo_wide_or_foreign_paths_touched():
    """The package must stay inside docs/wp-9091-01/ (+ this test file)."""
    allowed = {PKG.relative_to(ROOT).as_posix()}
    for p in PKG.rglob("*"):
        if p.is_file():
            assert p.relative_to(ROOT).as_posix().startswith(list(allowed)[0])
    assert pathlib.Path(__file__).resolve().as_posix().endswith(
        "tests/test_kf_wp9091_01_asset_manifest.py")


# ---------------------------------------------------------------- source identity
def test_source_hash_matches_contract(manifest, md):
    raw = SOURCE_MD.read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    assert h == CONTRACT_HASH == manifest["source"]["hash"]
    assert len(raw) == CONTRACT_BYTES == manifest["source"]["bytes_utf8"]
    assert len(md) == CONTRACT_CHARS == manifest["source"]["chars"]
    assert manifest["source"]["chars_match_contract"] is True
    assert manifest["source"]["uri"] == "tensor://reports/" + REPORT_ID
    assert manifest["source"]["field"] == "markdown"
    assert manifest["source"]["hash_alg"] == "sha256"


def test_envelope_provenance(manifest, envelope):
    assert envelope["schema_version"] == "kf_result.v1"
    assert envelope["package_id"] == PACKAGE_ID
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == REPORT_ID
    prov = envelope["provenance"]
    assert prov["source_hash"] == "sha256:" + manifest["source"]["hash"]
    assert prov["source_chars"] == manifest["source"]["chars"]
    assert prov["verification_status"] == "not_verified"
    assert prov["lane"] == "C"
    assert prov["work_package"] == PACKAGE_ID
    inner = envelope["outputs"]["asset_manifest.json"]
    assert inner["artifact_sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert inner["artifact_bytes"] == MANIFEST.stat().st_size


# ---------------------------------------------------------------- schema
def test_manifest_matches_generic_schema(manifest):
    jsonschema.validate(manifest, load(SCHEMA_GENERIC))


def test_v1_schema_regression_not_broken():
    """The generic schema is additive: wp-448-01's manifest still validates against v1."""
    v1 = ROOT / "schemas" / "asset_manifest.v1.schema.json"
    m448 = ROOT / "docs" / "wp-448-01" / "asset_manifest.json"
    if not (v1.exists() and m448.exists()):
        pytest.skip("v1 schema or wp-448-01 manifest not present in this checkout")
    jsonschema.validate(load(m448), load(v1))


# ---------------------------------------------------------------- locators
def test_every_locator_reproduces_quote_verbatim(manifest, md):
    assets = manifest["assets"]
    assert len(assets) == 29
    for a in assets:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        assert 0 <= s < e <= len(md), a["asset_id"]
        assert md[s:e] == q, "%s: char span does not reproduce the quote" % a["asset_id"]
        assert md.count(q) == 1, "%s: quote is not unique (%d hits)" % (a["asset_id"], md.count(q))
        assert loc["unique"] is True


def test_locator_line_spans_agree_with_char_spans(manifest, md):
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        assert md.count("\n", 0, s) == loc["start_line"], a["asset_id"]
        assert md.count("\n", 0, e - 1) == loc["end_line"], a["asset_id"]
        if loc["method"] == "document":
            assert (s, e) == (0, len(md))


def test_exactly_one_document_locator(manifest, md):
    docs = [a for a in manifest["assets"] if a["locator"]["method"] == "document"]
    assert len(docs) == 1
    assert docs[0]["locator"]["quote"] == md


def test_scope_isolation(manifest, md):
    assert manifest["report_id"] == REPORT_ID
    assert manifest["package_id"] == PACKAGE_ID
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["schema"] == "asset_manifest.v1"
    for a in manifest["assets"]:
        assert a["locator"]["end_char"] <= len(md)


def test_no_duplicate_asset_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)


# ---------------------------------------------------------------- resolution & counts
def test_resolution_split(manifest):
    res = {}
    cls = {}
    for a in manifest["assets"]:
        res[a["resolution"]] = res.get(a["resolution"], 0) + 1
        cls[a["asset_class"]] = cls.get(a["asset_class"], 0) + 1
    assert res == {"resolved_in_source": 24, "referenced_unresolved": 4, "declared_absent": 1}
    counts = manifest["counts"]
    assert counts["assets"] == 29
    assert counts["by_resolution"] == res
    assert counts["by_class"] == cls
    assert counts["resolved_in_source"] == 24
    assert counts["referenced_unresolved"] == 4
    assert counts["declared_absent"] == 1


def test_every_asset_declares_a_resolution_check(manifest):
    for a in manifest["assets"]:
        chk = a["resolution_check"]
        assert chk["check"] and chk["result"], a["asset_id"]
        if a["resolution"] == "resolved_in_source":
            assert chk["result"] == "resolved", a["asset_id"]
        else:
            # unresolved by construction: the check must say so, not claim success
            assert chk["result"] in ("unresolved", "present", "absent"), a["asset_id"]
        assert a["note"].strip()
        assert a["in_report_section"]


def test_unresolved_assets_are_the_known_four_plus_one(manifest):
    unresolved = {a["asset_id"] for a in manifest["assets"]
                  if a["resolution"] == "referenced_unresolved"}
    absent = {a["asset_id"] for a in manifest["assets"] if a["resolution"] == "declared_absent"}
    assert unresolved == {"A06", "A17", "A18", "A19"}
    assert absent == {"A27"}
    a19 = [a for a in manifest["assets"] if a["asset_id"] == "A19"][0]
    assert a19["resolution_check"]["check"].startswith("platform_api_figures_field")
    assert a19["resolution_check"]["platform_figures_count"] == 3
    a27 = [a for a in manifest["assets"] if a["asset_id"] == "A27"][0]
    assert a27["resolution_check"]["matches_found"] == []


# ---------------------------------------------------------------- scope discipline
def test_claims_empty_and_nothing_verified(manifest, envelope):
    assert manifest["claims"] == []
    assert manifest["integrity"]["verification_status"] == "not_verified"
    assert envelope["provenance"]["verification_status"] == "not_verified"
    assert manifest["integrity"]["external_reference_scan"]["matches"] == []


def test_no_source_numbers_recomputed(manifest, md):
    """Registration only: no asset may carry a field asserting a verified claim."""
    for a in manifest["assets"]:
        assert "verified" not in json.dumps(a.get("resolution_check", {})).lower()
    assert "verified" not in json.dumps(manifest["claims"]).lower()


# ---------------------------------------------------------------- delivered evidence
def test_verification_record_is_current(manifest):
    ver = load(VERIFICATION)
    assert ver["all_pass"] is True
    assert ver["manifest_sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest(), \
        "verification.json is stale relative to asset_manifest.json — re-run the verify stage"
    assert ver["source_sha256"] == CONTRACT_HASH
    names = {c["name"] for c in ver["checks"]}
    assert names == {"valid_json", "schema_pass_generic", "schema_pass_regression_v1",
                     "source_locator_resolvable", "source_hash_matches", "no_duplicate_ids",
                     "claims_evidence_or_status", "scope_isolation"}
    assert all(c["ok"] for c in ver["checks"])
    assert ver["acceptance"]["source_locator_resolvable"] is True
    assert ver["acceptance"]["all_claims_have_evidence_or_explicit_unresolved_status"] is True
    assert ver["verification_status"] == "not_verified"


def test_kf_result_markdown_has_single_envelope_block(envelope):
    text = KF_RESULT_MD.read_text(encoding="utf-8")
    # the outer fence is four backticks: the envelope embeds verbatim quotes that themselves
    # contain a three-backtick ```bash fence (assets A01/A28)
    blocks = re.findall(r"(`{3,})json\n(.*?)\n\1", text, re.S)
    assert len(blocks) == 1, "expected exactly one fenced json block"
    assert len(blocks[0][0]) == 4, "outer fence must outrun the three-backtick fences inside"
    assert json.loads(blocks[0][1]) == envelope
    # a naive three-backtick extractor must NOT be able to mis-close the block
    assert text.count("\n````json\n") == 1 and text.count("\n````\n") == 1
    for heading in ("## 1.", "## 2.", "## 3.", "## 4.", "## 5.", "## 6.", "## 7."):
        assert heading in text
    assert CONTRACT_HASH in text
    assert "fig_asset_inventory.png" in text


def test_figure_is_a_real_png():
    raw = FIGURE.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(raw) > 20000


# ---------------------------------------------------------------- regenerability
def test_regenerator_reproduces_the_committed_manifest(tmp_path, manifest):
    """Re-derive the whole manifest from the archived markdown + the recorded platform fields,
    offline, into a scratch tree; every locator and count must come out identical."""
    src = manifest["source"]
    docs = tmp_path / "docs" / PACKAGE_ID
    runs = tmp_path / "runs" / PACKAGE_ID
    docs.mkdir(parents=True)
    runs.mkdir(parents=True)
    (docs / "report_9091.md").write_bytes(SOURCE_MD.read_bytes())
    (runs / "report_9091.json").write_text(json.dumps({
        "id": src["platform_id"], "title": src["title"], "scenario_key": src["scenario_key"],
        "mission_id": src["platform_mission_id"], "status": src["platform_status"],
        "figures": src["platform_figures"], "tags": src["platform_tags"]},
        ensure_ascii=False), encoding="utf-8")

    spec = importlib.util.spec_from_file_location("build_manifest_wp9091_01", BUILDER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.ROOT = tmp_path
    mod.DOC_DIR = docs
    mod.RUN_DIR = runs
    assert mod.build() == 0
    rebuilt = load(docs / "asset_manifest.json")
    assert rebuilt["assets"] == manifest["assets"]
    assert rebuilt["counts"] == manifest["counts"]
    assert rebuilt["source"]["hash"] == manifest["source"]["hash"]
    assert rebuilt == manifest, "regeneration is not byte-stable"