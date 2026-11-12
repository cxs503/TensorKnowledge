"""wp-615-01（01-asset-registration）交付物回归测试。

全部离线：以 artifacts/kf/wp-615-01/source_snapshot/report_615.json 为唯一源，
不需要网络或 token。断言的是**不变量**（哈希一致、引文逐字可定位、ID 互异、
缺口必须带理由、信封结构合法、报告正文唯一 JSON 块与信封逐字节一致），
而不是"脚本跑通"。
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-615-01"
OUT = ROOT / "artifacts" / "kf" / PKG
DOCS = ROOT / "docs" / "kf" / f"KF-RESULT-{PKG}.md"

CONTRACT_SOURCE_HASH = "sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75"
CONTRACT_CHARS = 2125
CONTRACT_TITLE = "SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework"
CONTRACT_SCENARIO = "SIR-PC2|F06"


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return json.loads((OUT / "source_snapshot" / "report_615.json").read_text())


@pytest.fixture(scope="module")
def md(snapshot: dict) -> str:
    return snapshot["markdown"]


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((OUT / "asset_manifest.json").read_text())


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((OUT / "kf_result.json").read_text())


def test_only_report_615_is_touched(snapshot: dict) -> None:
    assert str(snapshot["id"]) == "615"
    assert snapshot["title"] == CONTRACT_TITLE


def test_source_hash_and_chars_match_contract(snapshot: dict, md: str) -> None:
    raw = md.encode("utf-8")
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == CONTRACT_SOURCE_HASH
    assert len(md) == CONTRACT_CHARS
    assert snapshot["scenario_key"] == CONTRACT_SCENARIO


def test_manifest_source_block_matches_snapshot(snapshot: dict, manifest: dict, md: str) -> None:
    src = manifest["source"]
    assert src["report_id"] == "615"
    assert src["source_field"] == "markdown"
    assert src["source_hash"] == CONTRACT_SOURCE_HASH
    assert src["hash_match"] is True
    assert src["chars"] == len(md) == src["contract_chars"]
    assert src["bytes"] == len(md.encode("utf-8"))
    assert src["record_fields"]["title"] == snapshot["title"]
    assert src["record_fields"]["title_matches_markdown_h1"] is True


def test_every_asset_quote_is_verbatim_and_offset_consistent(manifest: dict, md: str) -> None:
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q, off = loc["quote"], loc["offset_chars"]
        if not q or q not in md:
            bad.append((a["asset_id"], "substring"))
        elif off is None or md[off:off + len(q)] != q:
            bad.append((a["asset_id"], "offset"))
        assert loc["quote_verified"] is True, a["asset_id"]
    assert bad == [], bad


def test_locator_checks_block_agrees_with_markdown(manifest: dict, md: str) -> None:
    for key, chk in manifest["locator_checks"].items():
        assert chk["resolvable_in_markdown"] is True, key
        assert md.count(chk["quote"]) == chk["count_occurrences"] >= 1, key


def test_asset_ids_unique_and_gaps_accounted(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    unresolved_ids = {u["asset_id"] for u in manifest["unresolved"]}
    assert len(unresolved_ids) == len(manifest["unresolved"])
    for a in manifest["assets"]:
        if a["status"] != "resolved":
            assert a["asset_id"] in unresolved_ids
    for u in manifest["unresolved"]:
        assert len(u["reason"]) >= 10 and u["kind"]


def test_manifest_and_envelope_pass_json_schema(manifest: dict, envelope: dict) -> None:
    mschema = json.loads((ROOT / "schemas" / "asset_manifest.v1.schema.json").read_text())
    eschema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    jsonschema.Draft202012Validator(mschema).validate(manifest)
    jsonschema.Draft202012Validator(eschema).validate(envelope)


def test_envelope_pins_provenance_and_no_extraction(manifest: dict, envelope: dict) -> None:
    assert envelope["package_id"] == PKG
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == "615"
    assert envelope["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH == manifest["source"]["source_hash"]
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    assert envelope["claims"] == []  # 工序 01 不产 claim，也不得为填指标造 claim
    assert manifest["scope"]["extraction_performed"] is False
    assert manifest["scope"]["claims_emitted"] == 0


def test_no_claim_is_marked_verified(manifest: dict, envelope: dict) -> None:
    blob = json.dumps({"m": manifest, "e": envelope}, ensure_ascii=False).lower()
    assert "verified\": true" not in blob.replace(" ", "")
    assert '"status": "verified"' not in blob.replace(" ", "")


def test_checks_json_all_green() -> None:
    checks = json.loads((OUT / "checks.json").read_text())
    for key in ("all_pass", "source_hash_matches", "chars_match_contract", "source_locator_resolvable",
                "no_duplicate_ids", "schema_pass", "kf_result_schema_pass",
                "unresolved_assets_have_reason", "statuses_accounted"):
        assert checks[key] is True, key
    assert checks["bad_quotes"] == [] and checks["offset_mismatch"] == []
    assert checks["source_hash_recomputed"] == CONTRACT_SOURCE_HASH


def test_delivery_report_has_exactly_one_json_block_equal_to_envelope(envelope: dict) -> None:
    text = DOCS.read_text()
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
    assert len(blocks) == 1, f"expected exactly 1 json block, got {len(blocks)}"
    embedded = json.loads(blocks[0])
    assert embedded == envelope  # 原样提交，不得改动字段名/结构
    assert text.startswith(f"# KF-RESULT {PKG}")
    for section in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert section in text


def test_report_numbers_are_traceable_to_source(md: str) -> None:
    """零手抄：正文 ① 里由源报告派生的那一段，其数字必须逐个出现在源 markdown 中。"""
    text = DOCS.read_text()
    line = next(ln for ln in text.split("\n") if ln.startswith("逐字定位见 ④）"))
    nums = set(re.findall(r"\d+(?:[.,]\d+)*(?:×10⁻³)?", line))
    missing = sorted(n for n in nums if n not in md)
    assert missing == [], f"numbers not traceable to report 615 markdown: {missing}"


def test_figure_registered_as_unresolvable_not_fabricated(manifest: dict) -> None:
    figs = [a for a in manifest["assets"] if a["kind"] == "figure"]
    assert len(figs) == 1
    fig = figs[0]
    assert fig["status"] == "declared_unresolvable"
    assert fig["bytes"] == 0 and fig["sha256"] is None
    assert fig["retrieval"]["http_status"] == 404
    assert "png_base64" not in fig["fields"]["figure_record_keys"]


def test_version_controlled_mirror_is_byte_identical() -> None:
    """artifacts/ 被 .gitignore 忽略；knowledge/kf/<pkg>/ 是随分支交付的镜像，两者必须逐字节一致。"""
    mirror = ROOT / "knowledge" / "kf" / PKG
    for name in ("asset_manifest.json", "kf_result.json", "checks.json"):
        assert (mirror / name).read_bytes() == (OUT / name).read_bytes(), name
    assert (mirror / "report_615.md").read_bytes() == (OUT / "source_snapshot" / "report_615.md").read_bytes()
    assert (mirror / "figures" / "wp61501_asset_registry.png").read_bytes() == \
        (OUT / "figures" / "wp61501_asset_registry.png").read_bytes()
    assert (mirror / "KF-RESULT.md").read_text() == DOCS.read_text()


def test_report_payload_is_structured_for_platform() -> None:
    payload = json.loads((OUT / "report_payload.json").read_text())
    assert payload["title"] == f"KF-RESULT {PKG}"
    assert f"kf-wp:{PKG}" in payload["tags"]
    assert payload["scenario_key"] == CONTRACT_SCENARIO
    assert payload["markdown"].count("```json") == 1
    assert payload["figures"] and len(payload["figures"][0]["png_base64"]) > 1000