"""Invariant + negative-control tests for work package wp-11478-01 (asset registration of report 11478).

Every acceptance criterion is asserted on the real artifacts, and each check function is fed a
tampered copy to prove it can fail (a check that only ever returns "ok" proves nothing).

Run: pytest -q tests/test_kf_wp11478.py
Offline: reads runs/wp-11478-01/report_11478.md (byte-identical to the platform source, hash-pinned)
and artifacts/wp-11478-01/asset_manifest.json; no network needed.
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import re
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import kf_verify_11478 as kv  # noqa: E402

PKG = "wp-11478-01"
MANIFEST_PATH = ROOT / f"docs/{PKG}/asset_manifest.json"
SCHEMA_PATH = ROOT / "schemas/asset_manifest.v2.schema.json"
KF_SCHEMA_PATH = ROOT / "schemas/kf_result.v1.schema.json"
ENVELOPE_PATH = ROOT / f"docs/{PKG}/kf_result.{PKG}.json"
MD_PATH = ROOT / f"runs/{PKG}/report_11478.md"
DOC_PATH = ROOT / f"docs/{PKG}/KF-RESULT-{PKG}.md"
CONTRACT_HASH = "b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258"


@pytest.fixture(scope="module")
def md() -> str:
    return MD_PATH.read_text()


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text())


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE_PATH.read_text())


# ---------------------------------------------------------------- acceptance: hash
def test_source_hash_matches_contract(md, manifest):
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["integrity"]["hash_matches_contract"] is True
    assert manifest["source"]["chars"] == len(md) == 4710
    assert manifest["source"]["bytes_utf8"] == len(md.encode()) == 8163


# ---------------------------------------------------------------- acceptance: schemas
def test_manifest_validates_against_v2_schema(manifest):
    jsonschema.validate(manifest, json.loads(SCHEMA_PATH.read_text()))


def test_envelope_validates_against_kf_result_v1(envelope):
    jsonschema.validate(envelope, json.loads(KF_SCHEMA_PATH.read_text()))
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["package_id"] == PKG and envelope["report_id"] == "11478"
    assert envelope["task_type"] == "01-asset-registration"


def test_v2_schema_rejects_wrong_package_pattern(manifest):
    bad = copy.deepcopy(manifest)
    bad["package_id"] = "148-01"  # must be wp-<id>-01
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(bad, json.loads(SCHEMA_PATH.read_text()))


# ---------------------------------------------------------------- acceptance: locators
def test_every_locator_reresolves_uniquely(md, manifest):
    assert kv.check_locators(md, manifest) == []
    assert kv.check_claim_locators(md, manifest) == []
    for a in manifest["assets"]:
        loc = a["locator"]
        assert md[loc["start_char"]:loc["end_char"]] == loc["quote"]
        assert loc["end_char"] - loc["start_char"] == len(loc["quote"])


def test_locator_check_detects_tampered_quote(md, manifest):
    t = copy.deepcopy(manifest)
    t["assets"][5]["locator"]["quote"] = t["assets"][5]["locator"]["quote"] + "X"
    assert ("A06", "quote_not_unique") in kv.check_locators(md, t)


def test_locator_check_detects_shifted_span(md, manifest):
    t = copy.deepcopy(manifest)
    t["assets"][0]["locator"]["start_char"] += 1
    assert any(a == "A01" and why == "slice_mismatch" for a, why in kv.check_locators(md, t))


def test_locator_check_detects_line_drift(md, manifest):
    t = copy.deepcopy(manifest)
    t["assets"][10]["locator"]["start_line"] += 2
    assert any(a == "A11" and why == "line_offset_mismatch" for a, why in kv.check_locators(md, t))


def test_claim_locator_check_detects_edit(md, manifest):
    t = copy.deepcopy(manifest)
    t["claims"][1]["evidence"][0]["locator"]["start_char"] += 3
    assert ("C02-error-table-honest-no-cosmetic", "slice_mismatch") in kv.check_claim_locators(md, t)


# ---------------------------------------------------------------- acceptance: ids
def test_no_duplicate_ids(manifest):
    assert kv.check_duplicate_ids(manifest) == []


def test_duplicate_detector_works(manifest):
    t = copy.deepcopy(manifest)
    t["assets"].append(copy.deepcopy(t["assets"][0]))
    assert ("asset_id", "A01") in kv.check_duplicate_ids(t)


# ---------------------------------------------------------------- acceptance: claims
def test_no_claim_is_marked_verified(envelope, manifest):
    assert all(not c.get("verified") for c in manifest["claims"])
    assert all("verified" not in c for c in envelope["claims"])


def test_unresolved_claim_without_reason_is_rejected(manifest):
    t = copy.deepcopy(manifest)
    for c in t["claims"]:
        if c["status"] == "unresolved":
            c.pop("unresolved_reason", None)
            assert (c["claim_id"], "missing_unresolved_reason") in kv.check_claim_status(t)
            break


def test_self_marked_verified_is_rejected(manifest):
    t = copy.deepcopy(manifest)
    t["claims"][0]["verified"] = True
    assert any(why == "self_marked_verified" for _, why in kv.check_claim_status(t))


def test_supported_claim_without_evidence_is_rejected(manifest):
    t = copy.deepcopy(manifest)
    for c in t["claims"]:
        if c["status"] == "supported":
            c.pop("evidence")
            assert (c["claim_id"], "missing_evidence") in kv.check_claim_status(t)
            break


# ---------------------------------------------------------------- consistency
def test_counts_consistent_and_detects_drift(manifest):
    assert kv.check_counts(manifest) == []
    t = copy.deepcopy(manifest)
    t["counts"]["assets"] += 1
    assert any(f[0] == "counts.assets" for f in kv.check_counts(t))
    t2 = copy.deepcopy(manifest)
    t2["counts"]["resolved_in_source"] += 1
    assert any(f[0] == "counts.resolved_in_source" for f in kv.check_counts(t2))


def test_sections_exist_and_detects_fake_section(md, manifest):
    assert kv.check_sections(md, manifest) == []
    t = copy.deepcopy(manifest)
    t["assets"][0]["in_report_section"] = "## ⑦ 不存在的章节"
    assert ("A01", "## ⑦ 不存在的章节") in kv.check_sections(md, t)


def test_resolution_status_is_backed_by_its_check(manifest):
    """No wallpaper: a declared status must agree with the machine check it claims to rest on."""
    for a in manifest["assets"]:
        res, chk = a["resolution"], a["resolution_check"]["result"]
        if res == "referenced_unresolved":
            assert chk == "unresolved", a["asset_id"]
        elif res == "resolved_in_platform_record":
            assert chk == "present", a["asset_id"]
        elif res == "declared_absent":
            assert chk == "absent", a["asset_id"]
        elif res == "resolved_in_source":
            assert chk == "resolved", a["asset_id"]


def test_missing_external_paths_are_reported_not_hidden(manifest):
    """The 8 unresolved assets must be external-repo paths (structurally absent here), not typos."""
    wt = [a for a in manifest["assets"] if a["resolution_check"]["check"] == "worktree_path_exists"]
    assert len(wt) >= 5
    for a in wt:
        assert a["resolution_check"]["missing"], a["asset_id"]


# ---------------------------------------------------------------- end-to-end
def test_full_verify_passes_on_real_inputs(md, manifest):
    verdict = kv.verify(md, manifest, json.loads(SCHEMA_PATH.read_text()))
    assert verdict["status"] == "pass", verdict["blocking_failures"]
    assert {c["id"] for c in verdict["checks"]} >= {
        "schema_pass", "source_hash_matches", "source_locator_resolvable", "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status"}


def test_full_verify_fails_on_wrong_markdown(md, manifest):
    verdict = kv.verify(md.replace("0.880", "0.881"), manifest, json.loads(SCHEMA_PATH.read_text()))
    assert verdict["status"] == "fail"
    assert "source_hash_matches" in verdict["blocking_failures"]
    assert "source_locator_resolvable" in verdict["blocking_failures"]


def test_report_has_exactly_one_json_block_matching_envelope(envelope):
    doc = DOC_PATH.read_text()
    blocks = re.findall(r"```json\n(.*?)\n```", doc, flags=re.S)
    assert len(blocks) == 1, f"expected 1 json block, got {len(blocks)}"
    assert json.loads(blocks[0]) == envelope
    assert "KF-RESULT wp-11478-01" in doc.splitlines()[0]
    for section in ("①", "②", "③", "④", "⑤", "⑥"):
        assert section in doc


def test_outputs_key_is_the_declared_artifact(envelope, manifest):
    assert list(envelope["outputs"]) == ["asset_manifest.json"]
    assert envelope["outputs"]["asset_manifest.json"] == manifest

# ---------------------------------------------------------------- deliverable durability
def test_primary_artifact_is_trackable():
    """artifacts/ is gitignored in this repo; the manifest must NOT live there."""
    manifest = json.loads(MANIFEST_PATH.read_text())
    import subprocess
    rc = subprocess.run(["git", "check-ignore", "-q", str(MANIFEST_PATH.relative_to(ROOT))],
                        cwd=str(ROOT), capture_output=True).returncode
    assert rc != 0, "primary artifact is gitignored -> would be dropped by the push gate"
    assert manifest["integrity"]["output_path_gitignored"] is False
    assert manifest["integrity"]["output_path"].endswith("docs/wp-11478-01/asset_manifest.json")


def test_pipeline_rerun_is_byte_identical():
    """Idempotency: rebuild manifest/claims/register/verify/png and compare bytes (excl. timestamped doc)."""
    import subprocess
    targets = [MANIFEST_PATH,
               ROOT / f"runs/{PKG}/claims_11478.json",
               ROOT / f"runs/{PKG}/register_11478.json",
               ROOT / f"runs/{PKG}/verify_11478.json",
               ROOT / f"docs/{PKG}/asset_span_map.png"]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in targets}
    for script in ("kf_claims_11478.py", "kf_register_11478.py", "kf_figure_11478.py",
                   "kf_verify_11478.py"):
        r = subprocess.run([sys.executable, f"scripts/{script}"], cwd=str(ROOT),
                           capture_output=True, text=True)
        assert r.returncode == 0, (script, r.stdout[-300:], r.stderr[-300:])
    after = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in targets}
    assert before == after, {str(p): (before[p], after[p]) for p in targets if before[p] != after[p]}


def test_publish_record_and_roundtrip_verification():
    """The delivered report was published; its round-trip check must be green for the same id."""
    pub = json.loads((ROOT / f"runs/{PKG}/publish_11478.json").read_text())
    ver = json.loads((ROOT / f"runs/{PKG}/publish_verify_11478.json").read_text())
    assert pub["status"] == 200 and isinstance(pub["report_id"], int)
    assert ver["report_id"] == pub["report_id"], "publish_verify is stale vs publish record"
    assert ver["all_pass"] is True, ver["checks"]
