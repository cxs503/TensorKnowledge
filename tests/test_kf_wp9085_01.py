"""Acceptance invariants for work package wp-9085-01 (report 9085 asset registration).

Offline checks always run against the committed artifacts + the committed byte copy of
the markdown. The live checks (re-fetch the report, re-derive every locator from the
served markdown) run when TENSOR_API_BASE/credentials are present, and are skipped
otherwise — a skip is reported as skipped, never as passed.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-9085-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
DERIVED_SCHEMA = PKG / "asset_manifest.schema.derived.json"
VERIFICATION = PKG / "verification.json"
REPORT_MD = PKG / "KF-RESULT-wp-9085-01.md"
SOURCE_COPY = REPO / "runs" / "wp-9085-01" / "source_9085.md"
SHARED_SCHEMA = REPO / "schemas" / "asset_manifest.v1.schema.json"
KF_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"

CONTRACT_HASH = "sha256:6d424777af46c0c47d01887a47e4de261416aa154a7bbb86d6f1a81502d61d0a"
CONTRACT_CHARS = 9761


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest():
    return load(MANIFEST)


@pytest.fixture(scope="module")
def source():
    return SOURCE_COPY.read_text(encoding="utf-8")


# ------------------------------------------------------------------ structure
def test_valid_json_and_envelope_shape(manifest):
    for key in ("schema", "package_id", "task_type", "report_id", "source",
                "counts", "assets", "claims", "integrity"):
        assert key in manifest, key
    assert manifest["schema"] == "asset_manifest.v1"
    assert manifest["package_id"] == "wp-9085-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "9085"


def test_manifest_schema_pass(manifest):
    import jsonschema

    derived = load(DERIVED_SCHEMA)
    errs = list(jsonschema.Draft7Validator(derived).iter_errors(manifest))
    assert not errs, [e.message for e in errs]


def test_shared_schema_differs_only_in_package_identity(manifest):
    """The shared schema pins wp-448-01; this package may differ only in identity."""
    import jsonschema

    shared = load(SHARED_SCHEMA)
    paths = {"/".join(str(p) for p in e.absolute_path)
             for e in jsonschema.Draft7Validator(shared).iter_errors(manifest)}
    assert paths <= {"package_id", "report_id", "source/uri"}, paths


def test_kf_result_envelope_validates(manifest):
    import jsonschema

    env = load(ENVELOPE)
    schema = load(KF_SCHEMA)
    errs = list(jsonschema.Draft202012Validator(schema).iter_errors(env))
    assert not errs, [e.message for e in errs]
    assert env["outputs"]["asset_manifest.json"] == manifest


def test_source_hash_matches_contract(manifest):
    raw = SOURCE_COPY.read_bytes()
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert manifest["source"]["hash_prefixed"] == CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH.split(":", 1)[1]
    assert manifest["source"]["chars"] == CONTRACT_CHARS == len(
        SOURCE_COPY.read_text(encoding="utf-8"))
    assert manifest["source"]["bytes_utf8"] == len(raw)
    assert manifest["integrity"]["hash_matches_contract"] is True
    assert load(ENVELOPE)["provenance"]["source_hash"] == CONTRACT_HASH


def test_single_report_scope(manifest):
    assert manifest["source"]["uri"] == "tensor://reports/9085"
    assert manifest["source"]["record_id"] == 9085
    blob = json.dumps(manifest["assets"], ensure_ascii=False)
    assert "reports/9085" in blob or True  # ids/uris are checked for other reports below
    other = [s for s in blob.split("reports/")[1:]]
    assert all(s.startswith("9085") for s in other), other


# ------------------------------------------------------------------- locators
def test_asset_ids_unique_and_wellformed(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids and len(ids) == len(set(ids))
    assert all(len(i) == 3 and i.startswith("A") and i[1:].isdigit() for i in ids)
    assert manifest["counts"]["duplicate_asset_ids"] == []


def test_primary_locators_resolve_in_source(manifest, source):
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        assert q in source, a["asset_id"]
        assert source.count(q) == 1, (a["asset_id"], source.count(q))
        if loc["method"] == "document":
            assert loc["start_char"] == 0 and loc["end_char"] == len(source)
        else:
            assert source[loc["start_char"]:loc["end_char"]] == q, a["asset_id"]
            assert source.count("\n", 0, loc["start_char"]) + 1 == loc["start_line"]
            assert source.count("\n", 0, max(loc["end_char"] - 1, 0)) + 1 == \
                loc["end_line"]
        assert loc["unique"] is True


def test_every_occurrence_resolves(manifest, source):
    for a in manifest["assets"]:
        for occ in a.get("occurrences") or []:
            assert source[occ["start_char"]:occ["end_char"]] == occ["quote"]
            assert source.count("\n", 0, occ["start_char"]) + 1 == occ["line"]


def test_every_asset_declares_resolution_and_check(manifest):
    for a in manifest["assets"]:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved",
                                   "declared_absent"}
        assert a["resolution_check"]["check"]
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent",
                                                   "present"}


def test_unresolved_assets_are_not_asserted(manifest):
    """Byte-less references must not be declared to exist; only the fetched source is."""
    for a in manifest["assets"]:
        if a["asset_class"] == "report_markdown":
            assert a["existence_asserted_by_worker"] is True
        else:
            assert a["existence_asserted_by_worker"] is False
            assert a["resolution"] == "referenced_unresolved"


def test_figures_are_one_to_one(manifest):
    chk = manifest["source"]["figure_link_check"]
    assert len(chk["record_figure_names"]) == 6
    assert chk["one_to_one"] is True, chk
    assert chk["record_only"] == [] and chk["markdown_only"] == []
    figs = [a for a in manifest["assets"] if a["asset_class"] == "figure_reference"]
    assert len(figs) == 6
    for f in figs:
        assert f["record_metadata"]["present_in_record_figures"] is True
        assert f["record_metadata"]["caption"]


def test_counts_recomputed(manifest):
    by_class, by_res = {}, {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert manifest["counts"]["assets"] == len(manifest["assets"])
    assert manifest["counts"]["by_class"] == by_class
    assert manifest["counts"]["by_resolution"] == by_res
    assert manifest["counts"]["excluded_tokens"] == \
        len(manifest["excluded_tokens"]["items"])


# --------------------------------------------------------------------- claims
def test_no_claims_and_nothing_verified(manifest):
    assert manifest["claims"] == []
    env = load(ENVELOPE)
    assert env.get("claims", []) == []
    for c in manifest["claims"]:
        assert c.get("status") != "verified"


# ------------------------------------------------------------------ self-check
def test_verification_report_is_clean():
    ver = load(VERIFICATION)
    assert ver["overall_ok"] is True, ver["failures"]
    assert ver["hash_matches_contract"] is True
    assert ver["locator_checks_passed"] == ver["locator_checks_total"]
    assert ver["occurrence_checks_passed"] == ver["occurrence_checks_total"]
    assert ver["recomputed_source_hash"] == CONTRACT_HASH


def test_report_markdown_has_exactly_one_json_block_equal_to_kf_result():
    text = REPORT_MD.read_text(encoding="utf-8")
    assert text.startswith("# KF-RESULT wp-9085-01")
    assert "kf-wp:wp-9085-01" in text
    blocks = text.split("```json")
    assert len(blocks) == 2, "expected exactly one ```json block"
    body = blocks[1].split("```", 1)[0].strip()
    assert json.loads(body) == load(ENVELOPE)


# ---------------------------------------------------------------- live re-check
live = pytest.mark.skipif(
    not (os.environ.get("TENSOR_API_BASE") and os.environ.get("TENSOR_AGENT_USER")),
    reason="platform API not configured in this environment",
)


@live
def test_live_markdown_still_matches(manifest):
    import sys

    sys.path.insert(0, str(REPO / "scripts"))
    import kf_wp9085_01_verify as verify

    md = verify.fetch_markdown()
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    rep = verify.verify({"markdown": md})
    assert rep["overall_ok"] is True, rep["failures"]