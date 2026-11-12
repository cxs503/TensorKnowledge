"""wp-5624-01 验收回归：对已交付的 kf_result / asset_manifest 复算合同 acceptance 项。

设计：能连平台就独立重取 report 5624 的 markdown 做二次核验（哈希、逐字引文、确定性重建）；
无凭据/无网络时跳过联网用例，仅对已交付产物做结构自检（不得把未跑标成通过）。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
PKG = "wp-5624-01"
OUT = ROOT / "artifacts" / "kf" / PKG
CONTRACT_HASH = (
    "sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839"
)
CONTRACT_CHARS = 1833

needs_api = pytest.mark.skipif(
    not all(os.environ.get(k) for k in ("TENSOR_API_BASE", "TENSOR_AGENT_USER", "TENSOR_AGENT_PASS")),
    reason="无平台凭据，联网核验未执行（不是通过）",
)


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "register_assets_5624", ROOT / "scripts" / "kf" / PKG / "register_assets.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest(result: dict) -> dict:
    return result["outputs"]["asset_manifest.json"]


@pytest.fixture(scope="module")
def record() -> dict:
    return _load_module().fetch_record()


def test_valid_json_and_schema(result: dict) -> None:
    jsonschema.validate(
        result, json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    )
    assert result["package_id"] == PKG
    assert result["report_id"] == "5624"


def test_provenance_hash_matches_contract(manifest: dict) -> None:
    h = manifest["source_asset"]["hash"]
    assert h["value"] == CONTRACT_HASH
    assert h["matches_contract"] is True
    assert manifest["source_asset"]["size"]["chars"] == CONTRACT_CHARS


@needs_api
def test_hash_recomputed_from_platform(record: dict, manifest: dict) -> None:
    md = record["markdown"]
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert manifest["source_asset"]["hash"]["value"] == CONTRACT_HASH


def test_no_duplicate_ids(manifest: dict) -> None:
    ids = [r["ref_id"] for r in manifest["referenced_artifacts"]]
    ids += [d["digest_id"] for d in manifest["content_digests"]]
    ids += [o["id"] for o in manifest["observations"]]
    assert ids and len(ids) == len(set(ids))


def test_locators_resolvable_flags(manifest: dict) -> None:
    lc = manifest["locator_check"]
    assert lc["all_resolved"] is True
    assert lc["resolved"] == lc["total"] > 0
    assert lc["unresolved_items"] == []


@needs_api
def test_every_markdown_locator_is_verbatim_substring(record: dict, manifest: dict) -> None:
    md = record["markdown"]
    md_items = [i for i in manifest["locator_check"]["items"] if i["source_field"] == "markdown"]
    assert md_items
    for it in md_items:
        assert it["quote"] in md, it["id"]


@needs_api
def test_figure_captions_match_record(record: dict, manifest: dict) -> None:
    caps = {f.get("caption") for f in record.get("figures") or []}
    for it in manifest["locator_check"]["items"]:
        if it["source_field"] == "figures":
            assert it["quote"] in caps


def test_claims_policy(result: dict) -> None:
    """01 工序不做抽取：claims 允许为空；非空时每条必须有证据或显式未决状态。"""
    assert result["claims"] == [] or all(
        (c.get("evidence") or c.get("unresolved_reason")) for c in result["claims"]
    )
    assert result["outputs"]["asset_manifest.json"]["boundary"]["claims_generated"] == len(
        result["claims"]
    )


def test_boundary_single_report(manifest: dict) -> None:
    b = manifest["boundary"]
    assert b["report_ids_read"] == ["5624"]
    assert b["report_ids_written"] == ["5624"]
    assert not _exact_value(manifest, "verified")
    assert not _exact_value(manifest, "VERIFIED")


def _exact_value(obj, needle: str) -> bool:
    """递归找「恰好等于」needle 的标量（不误伤 'verification_status' 这类说明文字）。"""
    if isinstance(obj, dict):
        return any(_exact_value(v, needle) for v in obj.values())
    if isinstance(obj, list):
        return any(_exact_value(v, needle) for v in obj)
    return obj == needle


@needs_api
def test_deterministic_rebuild(record: dict, result: dict, tmp_path: Path) -> None:
    mod = _load_module()
    rebuilt, _ = mod.build_manifest(record)
    committed = json.loads(json.dumps(result["outputs"]["asset_manifest.json"]))
    rebuilt["generated_at"] = committed["generated_at"]
    assert rebuilt == committed


@needs_api
def test_referenced_paths_absent_in_this_worktree(manifest: dict) -> None:
    """诚实性：报告声明的工件根不由本仓产出，存在性必须如实标 not_checked。"""
    for r in manifest["referenced_artifacts"]:
        assert r["existence"] == "not_checked"
        assert r["locator_quote"]