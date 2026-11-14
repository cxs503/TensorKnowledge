"""Acceptance invariants for work package wp-13980-01 (report 13980 asset registration).

Every check here is offline: it runs against the bytes committed with the package,
so a reviewer can re-verify without platform credentials. The single live piece of
evidence (figure PNG bytes, endpoint route probes) is pinned in the manifest with
its sha256 / HTTP status, and this module asserts the pin is well formed rather
than trusting the prose in KF-RESULT.

Division of labour:

* ``scripts/kf_fetch_13980.py`` *produces* the package (fetch + probe + render).
* this module *re-verifies* it from the committed artefacts, independently of the
  producer's own ``verify_report.json`` verdict.
"""

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "docs" / "kf" / "wp-13980-01"
MANIFEST_PATH = PKG / "asset_manifest.json"
SOURCE_PATH = PKG / "source_markdown.md"
KF_RESULT_PATH = PKG / "kf_result.wp-13980-01.json"
ROUNDTRIP_PATH = PKG / "publish_roundtrip.json"
VERIFY_PATH = PKG / "verify_report.json"
DOC_PATH = PKG / "KF-RESULT-wp-13980-01.md"
FIGURE_PATH = PKG / "fig1_asset_registration.png"

#: source identity pinned at registration time (report 13980, mission m14895)
EXPECTED_SOURCE_SHA256 = "2e506d3c8285306a34dd397de133f8c48f6f02a604629adbc0c79eb81ce83ce6"
EXPECTED_CHARS = 8267
EXPECTED_BYTES = 11213
EXPECTED_LINES = 120
EXPECTED_REPORT_ID = "13980"
EXPECTED_FIGURES = 8
EXPECTED_ENDPOINTS = 7
EXPECTED_ASSETS = 28


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return SOURCE_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest():
    return _load(MANIFEST_PATH)


@pytest.fixture(scope="module")
def kf_result():
    return _load(KF_RESULT_PATH)


@pytest.fixture(scope="module")
def assets(manifest):
    return manifest["assets"]


# ---------------------------------------------------------------------------
# package presence
# ---------------------------------------------------------------------------
def test_package_files_exist():
    for path in (MANIFEST_PATH, SOURCE_PATH, KF_RESULT_PATH, ROUNDTRIP_PATH,
                 VERIFY_PATH, DOC_PATH, FIGURE_PATH):
        assert path.is_file(), path
        assert path.stat().st_size > 0, path


def test_manifest_identity(manifest):
    assert manifest["schema"] == "asset_manifest.v1"
    assert manifest["package_id"] == "wp-13980-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == EXPECTED_REPORT_ID
    assert manifest["source"]["source_uri"] == f"tensor://reports/{EXPECTED_REPORT_ID}"
    assert manifest["source"]["source_field"] == "markdown"


def test_manifest_schema_valid(manifest):
    jsonschema = pytest.importorskip("jsonschema")
    schema = _load(REPO / "schemas" / "asset_manifest.registration.v1.schema.json")
    jsonschema.validate(manifest, schema)


# ---------------------------------------------------------------------------
# source identity (recomputed here, not read from verify_report)
# ---------------------------------------------------------------------------
def test_source_bytes_match_pinned_identity(source):
    payload = source.encode("utf-8")
    assert hashlib.sha256(payload).hexdigest() == EXPECTED_SOURCE_SHA256
    assert len(source) == EXPECTED_CHARS
    assert len(payload) == EXPECTED_BYTES
    assert len(source.rstrip("\n").split("\n")) == EXPECTED_LINES


def test_manifest_source_hash_equals_local_copy(manifest, source):
    src = manifest["source"]
    assert src["source_hash"] == "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert src["chars"] == len(source)
    assert src["bytes_utf8"] == len(source.encode("utf-8"))
    assert src["lines"] == len(source.rstrip("\n").split("\n"))
    assert src["hash_match"] is True


def test_record_fields_are_declared_honestly(manifest):
    rf = manifest["source"]["record_fields"]
    assert rf["id"] == EXPECTED_REPORT_ID
    assert rf["status"] == "published"
    assert rf["mission_id"] == "14895"
    assert rf["scenario_key"] == "ice_resistance"
    assert rf["title_matches_contract"] is True
    assert rf["scenario_matches_contract"] is True
    assert rf["title"].startswith("A2-ICE-MODULES")


# ---------------------------------------------------------------------------
# locators: the core evidence layer, re-resolved from the committed bytes
# ---------------------------------------------------------------------------
def test_every_locator_resolves_to_its_quote(manifest, source, assets):
    assert len(assets) == EXPECTED_ASSETS == manifest["counts"]["assets"]
    for a in assets:
        loc = a["locator"]
        assert source[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert hashlib.sha256(loc["quote"].encode("utf-8")).hexdigest() == loc["quote_sha256"], a["asset_id"]
        assert loc["end_char"] - loc["start_char"] == len(loc["quote"]), a["asset_id"]


def test_locator_line_numbers_and_occurrences(manifest, source, assets):
    for a in assets:
        loc = a["locator"]
        expected_line = source.count("\n", 0, loc["start_char"]) + 1
        assert loc["start_line"] == expected_line, a["asset_id"]
        assert loc["occurrences"] == source.count(loc["quote"]), a["asset_id"]
        assert loc["unique"] == (loc["occurrences"] == 1), a["asset_id"]
        assert a["locator"]["method"] in ("char_span", "document")


def test_quotes_are_locatable_by_occurrence_index(source, assets):
    for a in assets:
        loc = a["locator"]
        idx, seen = -1, -1
        while True:
            idx = source.find(loc["quote"], idx + 1)
            if idx < 0:
                break
            seen += 1
            if seen == loc["occurrence_index"]:
                break
        assert idx == loc["start_char"], a["asset_id"]


def test_asset_ids_unique_sequential_and_formatted(assets):
    ids = [a["asset_id"] for a in assets]
    assert len(set(ids)) == len(ids)
    assert ids == [f"A{i:02d}" for i in range(1, len(ids) + 1)]
    assert all(re.fullmatch(r"A\d{2,3}", i) for i in ids)
    assert manifest_dups_free(assets)


def manifest_dups_free(assets) -> bool:
    ids = [a["asset_id"] for a in assets]
    return not {i for i in ids if ids.count(i) > 1}


# ---------------------------------------------------------------------------
# counts / classes / resolutions
# ---------------------------------------------------------------------------
def test_counts_consistent_with_assets(manifest, assets):
    counts = manifest["counts"]
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert counts["by_class"] == dict(sorted(by_class.items()))
    assert counts["by_resolution"] == dict(sorted(by_res.items()))
    assert counts["assets"] == len(assets) == sum(by_res.values()) == sum(by_class.values())
    for key in ("resolved_in_source", "metadata_only", "referenced_unresolved", "declared_absent"):
        assert counts[key] == by_res.get(key, 0), key


def test_resolution_enum_and_check_pairs(assets):
    allowed = {"resolved_in_source", "metadata_only", "referenced_unresolved", "declared_absent"}
    for a in assets:
        assert a["resolution"] in allowed, a["asset_id"]
        assert a["resolution_check"]["check"], a["asset_id"]
        assert a["resolution_check"]["result"] in ("resolved", "unresolved", "absent", "present")


def test_claims_empty_with_honest_reason(manifest):
    assert manifest["claims"] == []
    assert manifest["counts"]["claims"] == 0
    reason = manifest["claims_empty_reason"]
    assert "01" in reason and "extraction" in reason.lower()


# ---------------------------------------------------------------------------
# figure byte layer
# ---------------------------------------------------------------------------
def test_figures_registered_and_byte_pinned(manifest, assets):
    figs = [a for a in assets if a["asset_class"] == "figure"]
    assert len(figs) == EXPECTED_FIGURES
    declared = manifest["source"]["record_fields"]["figures"]
    assert [f["name"] for f in declared] == [f["label"] for f in figs]
    for f in figs:
        pb = f["platform_bytes"]
        assert pb["endpoint"].endswith(f"/figures/{f['label']}")
        assert pb["http_status"] == 200, f["asset_id"]
        assert re.fullmatch(r"[0-9a-f]{64}", pb["sha256"]), f["asset_id"]
        assert pb["bytes"] > 1000, f["asset_id"]
        assert pb["bytes_committed"] is False
        assert not (PKG / f["label"]).exists(), "figure bytes must not be committed"


def test_figure_families_bound_one_to_one_and_tokens_resolve(manifest, source, assets):
    figs = [a for a in assets if a["asset_class"] == "figure"]
    families = [f["family"] for f in figs]
    assert len(set(families)) == len(families) == EXPECTED_FIGURES
    for f in figs:
        loc = f["locator"]
        s, e = loc["token_char_span"]
        base = loc["start_char"]
        assert source[base + s:base + e] == loc["token"], f["asset_id"]
        assert hashlib.sha256(loc["token"].encode("utf-8")).hexdigest() == loc["token_sha256"]


def test_figure_label_mismatch_is_recorded_not_hidden(manifest):
    la = manifest["figures"]["label_alignment"]
    assert la["compared"] == EXPECTED_FIGURES
    assert la["aligned"] + la["mismatch"] == la["compared"]
    assert la["mismatch"] == 5  # §④ renumbers F1..F7 after the F3 GAP
    note = la["note"].lower()
    assert "recorded" in note and "silently repaired" in note


# ---------------------------------------------------------------------------
# endpoint route evidence + the F3 gap
# ---------------------------------------------------------------------------
def test_endpoint_routes_pinned(assets):
    eps = [a for a in assets if a["asset_class"] == "endpoint"]
    assert len(eps) == EXPECTED_ENDPOINTS
    assert len({e["label"] for e in eps}) == EXPECTED_ENDPOINTS
    for e in eps:
        probe = e["route_probe"]
        assert probe["method"] == "POST" and probe["body"] == "{}"
        assert probe["route_present"] is True, e["label"]
        assert probe["status"] in (200, 201, 405, 422), (e["label"], probe["status"])
        assert e["resolution_check"]["result"] == "resolved"


def test_ice_mooring_gap_is_evidenced(assets, source):
    gap = [a for a in assets if a["asset_class"] == "endpoint_declared_absent"]
    assert len(gap) == 1
    gap = gap[0]
    assert gap["family"] == "F3_ice_mooring"
    assert gap["resolution"] == "declared_absent"
    assert "F3_ice_mooring" in gap["locator"]["quote"]
    assert "`None`" in gap["locator"]["quote"]
    candidates = gap["absence_probe"]["candidates"]
    assert len(candidates) == 5
    assert all(c["status"] == 404 for c in candidates)
    assert all("api/v1" in c["url"] for c in candidates)


def test_referenced_paths_stay_unresolved_with_reason(assets):
    refs = [a for a in assets if a["resolution"] == "referenced_unresolved"]
    assert len(refs) == 6
    for a in refs:
        assert a["asset_class"] in ("script_reference", "artifact_reference")
        assert a["worktree_exists"] is False, a["label"]
        assert a["note"]


# ---------------------------------------------------------------------------
# envelope / round-trip / verify report coherence
# ---------------------------------------------------------------------------
def test_kf_result_envelope(manifest, kf_result):
    jsonschema = pytest.importorskip("jsonschema")
    jsonschema.validate(kf_result, _load(REPO / "schemas" / "kf_result.v1.schema.json"))
    assert kf_result["package_id"] == manifest["package_id"]
    assert kf_result["task_type"] == "01-asset-registration"
    assert kf_result["report_id"] == EXPECTED_REPORT_ID
    prov = kf_result["provenance"]
    assert prov["source_field"] == "markdown"
    assert prov["source_hash"] == manifest["source"]["source_hash"]
    assert prov["chars"] == EXPECTED_CHARS
    assert prov["local_copy"].endswith("source_markdown.md")
    assert kf_result["claims"] == []
    assert kf_result["verification_status"]["status"] == "draft"  # L3 is the platform's call


def test_kf_result_outputs_point_at_real_artefacts(kf_result):
    outputs = kf_result["outputs"]
    for name in ("asset_manifest.json", "source_markdown.md", "publish_roundtrip.json",
                 "verify_report.json", "fig1_asset_registration.png", "KF-RESULT-wp-13980-01.md"):
        assert name in outputs, name
        assert (PKG / name).is_file(), name
    for name, meta in outputs.items():
        if not isinstance(meta, dict):
            continue
        digest = meta.get("sha256")
        if not digest or set(digest) == {"0"}:
            continue
        actual = hashlib.sha256((PKG / name).read_bytes()).hexdigest()
        assert digest.replace("sha256:", "") == actual, name


def test_publish_roundtrip_identity(manifest, source, kf_result):
    rt = _load(ROUNDTRIP_PATH)
    assert rt["roundtrip"]["hash_equal"] is True
    assert rt["roundtrip"]["chars_equal"] is True
    assert rt["verdict"] == "IDENTICAL"
    assert rt["roundtrip"]["first_fetch"]["source_hash"] == manifest["source"]["source_hash"]
    assert rt["roundtrip"]["second_fetch"]["source_hash"] == manifest["source"]["source_hash"]
    assert rt["local_copy"]["sha256"] == "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert rt["report_id"] == EXPECTED_REPORT_ID


def test_verify_report_is_green_and_complete():
    vr = _load(VERIFY_PATH)
    assert vr["verdict"] == "PASS"
    assert vr["summary"]["fail"] == 0
    assert vr["summary"]["total"] == len(vr["checks"])
    assert vr["summary"]["pass"] + vr["summary"]["skip"] == vr["summary"]["total"]
    ids = [c["id"] for c in vr["checks"]]
    assert len(set(ids)) == len(ids)
    assert all(c["result"] in ("pass", "fail", "skipped") for c in vr["checks"])
    assert vr["source_hash"] == "sha256:" + EXPECTED_SOURCE_SHA256


def test_verify_report_agrees_with_independent_recheck(manifest):
    """The producer's verdict must not disagree with this module's own findings."""
    vr = _load(VERIFY_PATH)
    by_id = {c["id"]: c for c in vr["checks"]}
    # C02 = local copy hash, recomputed here independently
    assert by_id["C02"]["result"] == "pass"
    # C14 = locators resolve, recomputed in test_every_locator_resolves_to_its_quote
    assert by_id["C14"]["result"] == "pass"
    # C20 = routes present, must match the pinned probe evidence
    eps = [a for a in manifest["assets"] if a["asset_class"] == "endpoint"]
    assert by_id["C20"]["result"] == ("pass" if all(
        e["route_probe"]["route_present"] for e in eps) else "fail")


# ---------------------------------------------------------------------------
# document + rendered figure
# ---------------------------------------------------------------------------
def test_document_pins_the_evidence(source):
    doc = DOC_PATH.read_text(encoding="utf-8")
    assert "wp-13980-01" in doc
    assert EXPECTED_SOURCE_SHA256 in doc
    for section in ("①", "②", "③", "④", "⑤", "⑥"):
        assert section in source
    for heading in ("## 1. 源取证", "## 2. 资产总账", "## 3. 图件字节层",
                    "## 4. 端点路由存在性", "## 5. 未解析引用", "## 6. 机器校验",
                    "## 7. 发布往返", "## 8. 复现", "## 9. 边界与局限"):
        assert heading in doc, heading
    assert "claims = []" in doc or "claims=[]" in doc
    assert "L2" in doc  # verification ceiling is stated, not implied


def test_registration_figure_is_a_real_png():
    payload = FIGURE_PATH.read_bytes()
    assert payload[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(payload) > 20000
    assert b"matplotlib" in payload.lower() or b"IHDR" in payload


# ---------------------------------------------------------------------------
# producer helpers (regression guard for the locator maths)
# ---------------------------------------------------------------------------
def test_registrar_helpers_locator_math():
    spec = importlib.util.spec_from_file_location(
        "kf_fetch_13980", REPO / "scripts" / "kf_fetch_13980.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    text = "line one\nline two\nline one\n"
    loc = mod.make_locator(text, "line one", occurrence_index=1)
    assert text[loc["start_char"]:loc["end_char"]] == "line one"
    assert loc["start_line"] == 3
    assert loc["occurrences"] == 2
    assert loc["unique"] is False
    with pytest.raises(ValueError):
        mod.make_locator(text, "absent quote")
    with pytest.raises(ValueError):
        mod.make_locator(text, "line one", occurrence_index=5)
    assert mod.block_end_line(text, 1) == 3  # three contiguous non-empty lines
    assert mod.block_end_line(text, 2) == 3
    assert mod.block_end_line("a\nb\n\nc\n", 1) == 2
    assert mod.line_of_char(text, text.index("line two")) == 2