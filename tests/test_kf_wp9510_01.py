#!/usr/bin/env python3
"""Offline regression tests for work package wp-9510-01 (01-asset-registration, report 9510).

No network: everything is checked against the committed source copy
(docs/kf/wp-9510-01/source_9510.md) and the committed artefacts under docs/kf/wp-9510-01/.

The contract constants below are pinned from the work-package contract YAML
(package wp-9510-01) so that the manifest's self-reported values are checked
against an independent copy, not against themselves.
"""
import hashlib
import json
import re
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-9510-01"
SOURCE = OUT / "source_9510.md"
MANIFEST = OUT / "asset_manifest.json"
ENVELOPE = OUT / "kf_result.json"
VERIFICATION = OUT / "verification.json"
REPORT_MD = OUT / "REPORT.md"

# --- pinned contract values (work-package contract YAML, wp-9510-01) ----------
CONTRACT_HASH = "cdc7db83dac16cc900d6a54d14b29f7c59e3288804041be61444d517921ee39c"
CONTRACT_CHARS = 8039
CONTRACT_REPORT_ID = "9510"
CONTRACT_PACKAGE_ID = "wp-9510-01"
CONTRACT_TASK_TYPE = "01-asset-registration"


@pytest.fixture(scope="module")
def source():
    return SOURCE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


def test_source_hash_and_chars_match_contract(source):
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH, "source copy drifted from the contract hash"
    assert len(source) == CONTRACT_CHARS


def test_package_identity(manifest, envelope):
    assert manifest["package_id"] == CONTRACT_PACKAGE_ID == envelope["package_id"]
    assert manifest["task_type"] == CONTRACT_TASK_TYPE == envelope["task_type"]
    assert manifest["report_id"] == CONTRACT_REPORT_ID == envelope["report_id"]
    assert manifest["source"]["hash_prefixed"] == "sha256:" + CONTRACT_HASH
    assert manifest["source"]["chars"] == CONTRACT_CHARS


def test_envelope_hash_binds_to_source(envelope, source):
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert hashlib.sha256(source.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert "asset_manifest.json" in envelope["outputs"]


def test_every_locator_resolves_offline(manifest, source):
    lines = source.rstrip("\n").split("\n")
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        ln = loc["start_line"]
        ok_line = 0 < ln <= len(lines) and lines[ln - 1] == loc["quote"]
        ok_sub = loc["quote"] in source
        if loc["method"] == "document":
            ok_span = (loc["start_char"] == 0 and loc["end_char"] == len(source)
                       and loc["start_line"] == 1 and loc["end_line"] == len(lines))
        else:
            ok_span = source[loc["start_char"]:loc["end_char"]] == loc["quote"]
        if not (ok_line and ok_span and ok_sub):
            bad.append(a["asset_id"])
    assert not bad, "locators not re-resolvable: %s" % bad


def test_locator_quotes_do_not_rewrite_source(manifest, source):
    """每资产引文必须是源文的一段逐字子串（零手抄的机器判据）。"""
    for a in manifest["assets"]:
        assert a["locator"]["quote"] in source, a["asset_id"]


def test_no_duplicate_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids[0] == "A01" and all(re.fullmatch(r"A\d{2}", i) for i in ids)


def test_counts_consistent_with_assets(manifest):
    assets = manifest["assets"]
    counts = manifest["counts"]
    assert counts["assets"] == len(assets)
    by_res = {}
    for a in assets:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert counts["by_resolution"] == by_res
    assert counts["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)


def test_claims_empty_with_stated_reason(manifest, envelope):
    assert envelope["outputs"]["claims.json"] == []
    assert "claims" not in envelope  # schema/kf_result.v1: additionalProperties=false
    assert manifest["claims"] == []
    assert manifest.get("claims_empty_reason")


def test_manifest_schema_pass(manifest):
    schema = json.loads((ROOT / "schemas" / "asset_manifest.v1.schema.json").read_text())
    cls = (jsonschema.Draft202012Validator if "2020-12" in schema.get("$schema", "")
           else jsonschema.Draft7Validator)
    errs = list(cls(schema).iter_errors(manifest))
    assert not errs, [e.message for e in errs[:5]]


def test_envelope_schema_pass(envelope):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    errs = list(jsonschema.Draft202012Validator(schema).iter_errors(envelope))
    assert not errs, [e.message for e in errs[:5]]


def test_manifest_schema_still_validates_earlier_package():
    """The schema was generalised (package_id/report_id/uri const -> pattern) for this
    package; wp-448-01 must still validate, i.e. the change is backward compatible."""
    schema = json.loads((ROOT / "schemas" / "asset_manifest.v1.schema.json").read_text())
    inst = json.loads((ROOT / "docs" / "wp-448-01" / "asset_manifest.json").read_text())
    errs = list(jsonschema.Draft7Validator(schema).iter_errors(inst))
    assert not errs, [e.message for e in errs[:5]]


def test_report_has_exactly_one_json_block_equal_to_envelope():
    text = REPORT_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
    assert len(blocks) == 1, "expected exactly one ```json block, got %d" % len(blocks)
    assert json.loads(blocks[0]) == json.loads(ENVELOPE.read_text(encoding="utf-8"))
    assert text.splitlines()[0].strip() == "# KF-RESULT wp-9510-01"


def test_report_quotes_are_verbatim_in_source(manifest, source):
    """The report never rewrites upstream text: each printed quote equals the manifest
    quote up to exactly two declared display transforms -- pipe -> "/" for table
    safety, and 96-char truncation with a trailing ellipsis."""
    lines = source.rstrip("\n").split("\n")
    text = REPORT_MD.read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if re.match(r"^\| A\d{2} \|", line)]
    assert len(rows) == len(manifest["assets"]), "evidence table row count mismatch"
    by_quote = {}
    for a in manifest["assets"]:
        q = a["locator"]["quote"].replace("|", "/")
        if len(q) > 96:
            q = q[:96] + "…"
        by_quote[a["asset_id"]] = q
    for row in rows:
        aid = row.split("|")[1].strip()
        assert by_quote[aid] in row, aid
        raw_line = [line for line in lines if line.replace("|", "/").startswith(
            by_quote[aid].rstrip("…"))]
        assert raw_line, "printed quote is not a verbatim prefix of any source line: %s" % aid


def test_no_foreign_report_touched():
    """Boundary check: this package may only reference report 9510."""
    blobs = [MANIFEST.read_text(encoding="utf-8"), ENVELOPE.read_text(encoding="utf-8")]
    for blob in blobs:
        ids = set(re.findall(r"/tensor/reports/(\d+)", blob)) | set(
            re.findall(r"tensor://reports/(\d+)", blob))
        assert ids <= {CONTRACT_REPORT_ID}, ids


def test_figures_are_not_overclaimed(manifest):
    """A figure whose bytes the platform does not serve must stay referenced_unresolved
    with no hash claim (no silent upgrade to 'present')."""
    probes = manifest["figure_probes"]
    for a in manifest["assets"]:
        name = a["label"].rstrip("/").rsplit("/", 1)[-1]
        if a["asset_class"] != "figure" or name not in probes:
            continue
        probe = probes[name]
        if probe["http_status"] != 200 or not probe["bytes"]:
            assert a["resolution"] == "referenced_unresolved", a["asset_id"]
            assert "no payload, no hash claimed" in a["note"], a["asset_id"]
        else:
            assert probe["sha256"], a["asset_id"]


def test_self_verification_all_ok():
    ver = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    assert ver["all_ok"] is True
    assert set(ver["acceptance"]) == {
        "valid_json", "schema_pass", "source_locator_resolvable",
        "source_hash_matches", "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status",
    }
    for name, check in ver["acceptance"].items():
        assert check["ok"], name

def test_report_has_error_judgement_section():
    """Section ⑥ must compare measured values with the contract baseline and answer the
    <3% question explicitly, including the dimension that has no baseline at all."""
    text = REPORT_MD.read_text(encoding="utf-8")
    assert "## ⑥ 误差判定" in text
    section = text.split("## ⑥ 误差判定", 1)[1].split("## ⑦", 1)[0]
    assert "是否 <3%" in section
    hash_row = [ln for ln in section.splitlines() if "源 markdown sha256" in ln]
    chars_row = [ln for ln in section.splitlines() if "源 markdown 字符数" in ln]
    fig_row = [ln for ln in section.splitlines() if "图件字节 sha256" in ln]
    assert hash_row and chars_row and fig_row, "error table rows missing"
    assert hash_row[0].rstrip().endswith("| 是 |"), hash_row[0]
    assert chars_row[0].rstrip().endswith("| 是 |"), chars_row[0]
    assert "不可判" in fig_row[0], "no-baseline dimension must declare itself unjudgeable"
    assert "不可判" in section  # prose statement, not only a table cell


def test_readback_audit_of_published_copy():
    """Post-publication audit: the copy the platform stores must hash to report 9510's
    markdown and carry exactly one kf_result json block. Skips when the audit was not
    run (offline checkout)."""
    path = OUT / "readback.json"
    if not path.exists():
        pytest.skip("readback.json not present (publish step not run)")
    rec = json.loads(path.read_text(encoding="utf-8"))
    assert rec["schema"] == "kf_readback.v1"
    assert rec["source_report_id"] == CONTRACT_REPORT_ID
    assert rec["all_ok"] is True, rec["checks"]
    checks = rec["checks"]
    assert checks["json_blocks"] == 1 and checks["block_parses"] is True
    assert checks["provenance_matches_live"] is True
    assert checks["matches_contract"] is True
    assert checks["tags_ok"] is True
    assert checks["env_package_id"] == CONTRACT_PACKAGE_ID
    assert checks["source_hash_live"] == "sha256:" + CONTRACT_HASH
    assert str(checks["mission_id"]) == "18569"
