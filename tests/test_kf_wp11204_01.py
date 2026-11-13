#!/usr/bin/env python3
"""Offline invariant tests for KF work package wp-11204-01 (report 11204).

These assert invariants, not "the script ran": every markdown locator is still a
verbatim substring of the frozen snapshot, spans/line numbers still agree with the
snapshot, ids stay unique, counts stay self-consistent, the figure bytes on disk
still hash to the values recorded in the manifest, the resolution vocabulary stays
three-valued with a basis for every non-resolved asset, and the delivered report
markdown keeps exactly one machine-readable JSON block whose numbers agree with the
manifest (anti-hand-copy gate).

No network: the builder/validator own the live re-fetch; these tests must stay green
offline so that a drifted hand edit is caught even without the platform.
"""
import hashlib
import json
import os
import re

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "kf", "wp-11204-01")
WORK = os.path.join(ROOT, "work", "wp-11204-01")
CONTRACT_HASH = "d22a30cc692b82f2acf6ea669fd898a330143436344e4091c4a39c06a5292f86"
CONTRACT_CHARS = 5999
SCAN_RE = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_./\-]*\.(?:py|json|png|md)|"
    r"src/[A-Za-z0-9_./\-]+|"
    r"ASTM E[0-9]+[A-Za-z0-9]*"
)


@pytest.fixture(scope="module")
def md():
    return open(os.path.join(WORK, "source_markdown.md"), encoding="utf-8").read()


@pytest.fixture(scope="module")
def man():
    return json.load(open(os.path.join(OUT, "asset_manifest.json"), encoding="utf-8"))


@pytest.fixture(scope="module")
def kf():
    return json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))


def test_source_hash_is_the_contract_hash(md, man):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    assert man["source"]["hash"] == CONTRACT_HASH
    assert man["source"]["chars"] == CONTRACT_CHARS
    assert man["source"]["bytes_utf8"] == len(md.encode("utf-8"))


def test_kf_provenance_hash_points_at_the_same_bytes(kf):
    assert kf["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert kf["provenance"]["source_field"] == "markdown"
    assert kf["report_id"] == "11204"
    assert kf["package_id"] == "wp-11204-01"
    assert kf["task_type"] == "01-asset-registration"


def test_every_markdown_locator_is_verbatim_with_consistent_spans(md, man):
    checked = 0
    for e in man["assets"]:
        for loc in e["locators"]:
            if loc["kind"] != "markdown_char_span":
                continue
            q = loc["quote"]
            assert md.count(q) == loc["occurrences"], (e["asset_id"], q)
            assert md[loc["start_char"]:loc["end_char"]] == q, (e["asset_id"], q)
            assert loc["start_line"] == md.count("\n", 0, loc["start_char"]) + 1
            assert len(loc["all_spans"]) == loc["occurrences"]
            for sp in loc["all_spans"]:
                assert md[sp["start_char"]:sp["end_char"]] == q
            # strictly inside the document, never an invented span
            assert 0 <= loc["start_char"] < loc["end_char"] <= len(md)
            checked += 1
    assert checked >= 25


def test_record_locators_point_at_fields_that_exist(man):
    rec = json.load(open(os.path.join(WORK, "record.json"), encoding="utf-8"))

    def resolve(path):
        cur = rec
        for m in re.finditer(r"([A-Za-z0-9_]+)|\[([0-9]+)\]", path.replace("record.", "")):
            key, idx = m.group(1), m.group(2)
            if key is not None:
                if not isinstance(cur, dict) or key not in cur:
                    return False
                cur = cur[key]
            else:
                cur = cur[int(idx)]
        return True

    n = 0
    for e in man["assets"]:
        for loc in e["locators"]:
            if loc["kind"] == "record_field":
                assert loc["present"] is True
                assert resolve(loc["record_path"]), (e["asset_id"], loc["record_path"])
                n += 1
    assert n >= 5


def test_asset_ids_unique_and_counts_recounted(man):
    ids = [e["asset_id"] for e in man["assets"]]
    assert len(ids) == len(set(ids)) == man["counts"]["assets"]
    by_class, by_res = {}, {}
    for e in man["assets"]:
        by_class[e["asset_class"]] = by_class.get(e["asset_class"], 0) + 1
        by_res[e["resolution"]] = by_res.get(e["resolution"], 0) + 1
    assert by_class == man["counts"]["by_class"]
    assert by_res == man["counts"]["by_resolution"]
    assert man["counts"]["resolved_in_source"] + man["counts"]["referenced_unresolved"] \
        + man["counts"]["declared_absent"] == len(ids)


def test_resolution_vocabulary_is_three_valued_and_unresolved_state_a_basis(man):
    allowed = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
    for e in man["assets"]:
        assert e["resolution"] in allowed
        assert e["resolution_basis"].strip()
        if e["resolution"] != "resolved_in_source":
            # an unresolved asset must not smuggle in byte-level evidence
            assert "figure_bytes" not in e or e["figure_bytes"].get("sha256") is None
    # the two artefacts that carry every number of the report must stay unresolved
    for aid in ("A18", "A19"):
        e = next(x for x in man["assets"] if x["asset_id"] == aid)
        assert e["resolution"] == "referenced_unresolved"


def test_claims_are_empty_and_nothing_is_marked_verified(man, kf):
    assert man["claims"] == []
    assert kf.get("claims") == []
    assert man["claims_policy"]["claims"] == []
    blob = json.dumps([man, kf], ensure_ascii=False)
    assert not re.search(r'"(?:status|verification)"\s*:\s*"(?:verified|confirmed)"', blob)
    assert "verified" not in {a.get("status") for a in man["assets"]}


def test_figure_bytes_on_disk_hash_to_the_manifest_values(man):
    figs = [e for e in man["assets"] if "figure_bytes" in e]
    assert len(figs) == 3
    for e in figs:
        fb = e["figure_bytes"]
        path = os.path.join(WORK, "figures", e["figure_bytes"]["url_path"].rsplit("/", 1)[-1] + ".png")
        raw = open(path, "rb").read()
        assert hashlib.sha256(raw).hexdigest() == fb["sha256"]
        assert len(raw) == fb["bytes"]
        assert raw[:8] == b"\x89PNG\r\n\x1a\n"
        assert fb["hash_stable_across_2_fetches"] is True
        assert fb["extension_form_probe"]["http_status"] == 404


def test_completeness_scanner_finds_no_unregistered_path_token(md, man):
    tokens = sorted(set(SCAN_RE.findall(md)))
    quoted = " \x00 ".join(loc["quote"] for e in man["assets"] for loc in e["locators"]
                           if loc["kind"] == "markdown_char_span")
    uncovered = [t for t in tokens if t not in quoted]
    assert uncovered == []
    assert len(tokens) == man["integrity"]["completeness_scanner_tokens"]


def test_schemas_validate(man, kf):
    env = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"), encoding="utf-8"))
    pkg = json.load(open(os.path.join(OUT, "asset_manifest.schema.json"), encoding="utf-8"))
    jsonschema.validate(kf, env)
    jsonschema.validate(man, pkg)
    assert kf["outputs"]["asset_manifest.json"] == man


def test_delivered_report_markdown_has_exactly_one_json_block_consistent_with_manifest(man):
    report = open(os.path.join(OUT, "KF-RESULT-wp-11204-01.md"), encoding="utf-8").read()
    blocks = re.findall(r"```json\n(.*?)\n```", report, re.S)
    assert len(blocks) == 1, "exactly one json block is the machine-readable delivery channel"
    assert report.count("```json") == 1
    payload = json.loads(blocks[0])
    assert payload["package_id"] == "wp-11204-01"
    assert payload["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert "kf-wp:wp-11204-01" in report
    # anti-hand-copy: every 64-hex digest printed in the report exists in the manifest
    known = set(re.findall(r"[0-9a-f]{64}", json.dumps(man)))
    for h in re.findall(r"[0-9a-f]{64}", report):
        assert h in known, "report prints a digest that is not in the manifest: " + h
    # and the headline counts printed in the report match
    assert str(man["counts"]["assets"]) in report
    assert "resolved_in_source" in report

def test_provenance_stamp_and_producer_are_well_formed(kf):
    import datetime as _dt

    prov = kf["provenance"]
    assert prov["producer"] == "agent/m15693"
    # a re-run must reuse the first-emission stamp (idempotent pipeline), so it has to
    # be a real ISO-8601 instant and stay stable while the source hash is unchanged
    _dt.datetime.fromisoformat(prov["emitted_at"])
    assert prov["source_chars"] == CONTRACT_CHARS
    assert prov["source_bytes_utf8"] == len(
        open(os.path.join(WORK, "source_markdown.md"), encoding="utf-8").read().encode("utf-8"))
