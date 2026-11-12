"""wp-7878-01 (01-asset-registration, report 7878) acceptance tests.

Offline: every check runs against the artifacts committed in this worktree, so the gate
can be re-run without platform credentials. Re-fetching the source (and therefore
re-proving that the artifacts came from the live record) is
`python3 scripts/kf_wp7878_01_register.py`; the live re-check below runs when
TENSOR_API_BASE + credentials are exported.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-7878-01"
SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"
EXPECTED_HASH = "sha256:ce890ca0df1440fe3339a7eece9a31f9b0fc767eb6cb43d9991b446f42c8b1fb"
EXPECTED_CHARS = 7386


def _load(name):
    return json.loads((PKG / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return (PKG / "source.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _load("asset_manifest.json")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return _load("kf_result.json")


@pytest.fixture(scope="module")
def locator_check() -> dict:
    return _load("locator_check.json")


@pytest.fixture(scope="module")
def body() -> str:
    return (PKG / "report_body.md").read_text(encoding="utf-8")


# --------------------------------------------------------------- source identity
def test_source_hash_matches_contract(source: str) -> None:
    digest = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == EXPECTED_HASH


def test_manifest_identity_fields(manifest: dict, source: str) -> None:
    prov = manifest["provenance"]
    assert manifest["package_id"] == "wp-7878-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "7878"
    assert prov["source_uri"] == "tensor://reports/7878"
    assert prov["source_field"] == "markdown"
    assert prov["source_hash"] == EXPECTED_HASH
    assert prov["source_hash_expected"] == EXPECTED_HASH
    assert prov["source_hash_matches"] is True
    assert prov["source_chars"] == len(source) == EXPECTED_CHARS
    assert prov["source_bytes_utf8"] == len(source.encode("utf-8"))
    assert prov["title_matches_contract"] is True
    assert prov["scenario_key_matches_contract"] is True
    assert (PKG / "sha256.txt").read_text(encoding="utf-8").strip() == EXPECTED_HASH


def test_scope_is_single_report(manifest: dict, envelope: dict, body: str) -> None:
    """Hard boundary of this work package: only report 7878 may be touched."""
    blob = json.dumps(manifest, ensure_ascii=False)
    ids = set(re.findall(r"tensor://reports/(\d+)", blob))
    assert ids <= {"7878"}
    assert "tensor://reports/7878" in body
    assert envelope["report_id"] == "7878"


# --------------------------------------------------------------- locators verbatim
def test_every_quote_resolves_verbatim_and_offsets_are_exact(manifest: dict, source: str) -> None:
    for asset in manifest["assets"]:
        loc = asset["locator"]
        if loc["scheme"] != "markdown_line":
            assert loc["scheme"] == "report_field"
            continue
        quote = loc["quote"]
        pos = source.find(quote, loc["char_offset"])
        assert pos == loc["char_offset"], asset["asset_id"]
        assert quote == source[loc["char_offset"]:loc["char_end"]], asset["asset_id"]
        assert source.count("\n", 0, pos) + 1 == loc["line"], asset["asset_id"]
        assert source.count("\n", 0, pos + len(quote)) + 1 == loc["line_end"], asset["asset_id"]
        assert source.count(quote) == loc["occurrences"], asset["asset_id"]
        assert asset["resolution"]["locator_resolvable"] is True
        assert asset["content_extracted"] is False


def test_locator_check_agrees_with_manifest(manifest: dict, locator_check: dict) -> None:
    assert locator_check["source_hash"] == EXPECTED_HASH
    assert locator_check["unresolved"] == []
    assert locator_check["quotes_checked"] == len(locator_check["checks"])
    checked = {c["asset_id"] for c in locator_check["checks"]}
    located = {a["asset_id"] for a in manifest["assets"] if a["locator"]["scheme"] == "markdown_line"}
    assert checked == located
    assert locator_check["quotes_resolvable"] == len(checked)


def test_asset_ids_unique(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["summary"]["duplicate_asset_ids"] == []


def test_resolution_status_in_documented_vocabulary(manifest: dict) -> None:
    vocab = set(manifest["resolution_status_vocabulary"])
    for asset in manifest["assets"]:
        assert asset["resolution"]["status"] in vocab, asset["asset_id"]
    for att in manifest["attachments"]:
        assert att["resolution"]["status"] in vocab


def test_table_structure_recounted_independently(manifest: dict, source: str) -> None:
    """`structure.data_rows` must equal an independent recount of the pipe table."""
    lines = source.split("\n")
    n_tables = 0
    for asset in manifest["assets"]:
        struct = asset.get("structure")
        if struct is None:
            continue
        n_tables += 1
        header = asset["locator"]["line"] - 1
        assert lines[header].strip().startswith("|")
        assert lines[header + 1].strip().startswith("|---")
        rows = 0
        i = header + 2
        while i < len(lines) and lines[i].strip().startswith("|"):
            rows += 1
            i += 1
        assert rows == struct["data_rows"], asset["asset_id"]
        assert len([c for c in lines[header].strip().strip("|").split("|")]) == struct["header_cells"]
    assert n_tables == 5


# --------------------------------------------------------------- no extraction
def test_manifest_registers_no_extraction(manifest: dict, envelope: dict) -> None:
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert manifest["summary"]["claims"] == 0
    assert all(a["content_extracted"] is False for a in manifest["assets"])


def test_nothing_marked_verified(manifest: dict, envelope: dict, body: str) -> None:
    blob = json.dumps([manifest, envelope], ensure_ascii=False)
    assert '"verified"' not in blob
    assert "status=verified" not in body


def test_figures_have_metadata_and_locators(manifest: dict) -> None:
    figs = [a for a in manifest["assets"] if a["kind"] == "figure"]
    assert len(figs) == 5
    assert len(manifest["attachments"]) == 5
    by_line = {a["uri"]: a["locator"]["line"] for a in figs}
    for att in manifest["attachments"]:
        assert att["name"] and att["caption"]
        assert att["origin"] == "record.figures"
        assert att["markdown_locator_line"] == by_line["docs/figures/p151n05/" + att["name"]]
        assert att["resolution"]["content_retrievable"] is False


# --------------------------------------------------------------- envelope / schema
def test_envelope_validates_against_schema(envelope: dict) -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(envelope, schema)
    assert envelope["provenance"]["source_hash"] == EXPECTED_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert set(envelope["outputs"]) == {"asset_manifest.json"}


def test_envelope_embeds_the_manifest_verbatim(envelope: dict, manifest: dict) -> None:
    assert envelope["outputs"]["asset_manifest.json"] == manifest


def test_report_body_has_exactly_one_json_block_equal_to_envelope(body: str, envelope: dict) -> None:
    blocks = re.findall(r"```json\n(.*?)```", body, flags=re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == envelope
    assert body.startswith("# KF-RESULT wp-7878-01")
    assert "kf-wp:wp-7878-01" in body
    # the six mandated sections are present
    for marker in ("① 本工序做了什么", "② 怎么做的", "③ 产出物清单", "④ 证据定位表",
                   "⑤ 注意点与局限", "⑥ 自检"):
        assert marker in body, marker


def test_repo_level_body_copy_matches(body: str) -> None:
    assert (REPO / "docs" / "kf_result_wp-7878-01.md").read_text(encoding="utf-8") == body


# --------------------------------------------------------------- live re-fetch (opt-in)
@pytest.mark.skipif(
    not (os.environ.get("TENSOR_AGENT_USER") and os.environ.get("TENSOR_AGENT_PASS")),
    reason="platform credentials not exported; live re-fetch is covered by the register script",
)
def test_live_record_still_hashes_to_contract(source: str) -> None:
    import urllib.request

    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps(
            {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
        ).encode(),
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    tok = json.loads(urllib.request.urlopen(req, timeout=60).read())
    tok = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(base + "/tensor/reports/7878")
    req.add_header("Authorization", "Bearer " + tok)
    rec = json.loads(urllib.request.urlopen(req, timeout=60).read())
    rec = rec.get("data", rec)
    live = rec["markdown"]
    assert live == source
    assert "sha256:" + hashlib.sha256(live.encode("utf-8")).hexdigest() == EXPECTED_HASH