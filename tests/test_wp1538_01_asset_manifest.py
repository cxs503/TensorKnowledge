"""wp-1538-01 资产登记产物不变量测试。

断言的是**不变量**（hash 绑定、零手抄引文逐字可定位、id 唯一、信封结构），
不是「跑一遍不报错」：

1. manifest 观测哈希 == 契约声明哈希 == 本地快照哈希；
2. 信封 provenance.source_hash 与快照逐位一致（平台会独立重算，此断言是本地预演）；
3. 每条 artifact locator 引文 / declared_path 都是源 markdown 的**逐字子串**（零手抄的机器判据）；
4. claims 为空（本工序禁止抽取），且 outputs 与 artifact_manifest.json 文件内容一致；
5. kf_result.v1 结构门（schema 存在时用 jsonschema，否则 skip 并如实标记）。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
# 本仓 .gitignore 丢弃 artifacts/**（mission-push gate），故被跟踪的正式副本在 docs/wp-1538-01/；
# 构建工作目录 artifacts/wp-1538-01/ 存在时优先用它（同内容，仅 generated_at 时间戳可能不同）。
_CANDIDATES = [ROOT / "docs" / "wp-1538-01", ROOT / "artifacts" / "wp-1538-01"]
WP = next((c for c in _CANDIDATES if (c / "asset_manifest.json").exists()), _CANDIDATES[0])
SNAPSHOT = ROOT / "runs" / "wp-1538-01" / "source_1538.md"
MANIFEST = WP / "asset_manifest.json"
ENVELOPE = WP / "kf_result_wp-1538-01.json"

CONTRACT_HASH = "sha256:9d7f968e4c888872eba25bfc190c3e6415e5c7a8f0f4b2733e665181e0d17c85"


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


def test_source_snapshot_hash_matches_contract() -> None:
    assert "sha256:" + hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == CONTRACT_HASH


def test_manifest_binds_report_id_to_contract_hash(manifest: dict) -> None:
    rep = manifest["report"]
    assert manifest["package_id"] == "wp-1538-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert rep["report_id"] == "1538"
    assert rep["source_field"] == "markdown"
    assert rep["source_hash_declared"] == CONTRACT_HASH
    assert rep["source_hash_observed"] == CONTRACT_HASH
    assert rep["hash_match"] is True
    assert rep["chars_observed"] == rep["chars_declared"]


def test_envelope_source_hash_matches_snapshot(envelope: dict) -> None:
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_hash"] == (
        "sha256:" + hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    )


def test_every_artifact_locator_is_verbatim_in_source(manifest: dict, source: str) -> None:
    assert manifest["artifacts"], "工件表不应为空（报告 §7 至少 1 行）"
    for art in manifest["artifacts"]:
        assert art["declared_path"] in source, art["declared_path"]
        quote = art["locator"]["quote"]
        assert quote in source, quote
        # 记录的行号必须真的指向该引文
        line = source.splitlines()[art["locator"]["table_row_line"] - 1]
        assert line == quote


def test_no_duplicate_ids(manifest: dict) -> None:
    artifact_ids = [a["artifact_id"] for a in manifest["artifacts"]]
    attachment_ids = [a["attachment_id"] for a in manifest["attachments"]]
    paths = [a["declared_path"] for a in manifest["artifacts"]]
    assert len(artifact_ids) == len(set(artifact_ids)), f"artifact_id 重复：{artifact_ids}"
    assert len(attachment_ids) == len(set(attachment_ids)), f"attachment_id 重复：{attachment_ids}"
    assert len(paths) == len(set(paths)), f"declared_path 重复：{paths}"
    # 跨类别 id 也不得撞
    assert not set(artifact_ids) & set(attachment_ids)


def test_attachments_are_metadata_only(manifest: dict) -> None:
    for att in manifest["attachments"]:
        assert att["binary_resolution"] == "metadata_only"
        assert att["caption"], "caption 不应为空"


def test_no_claims_extracted(manifest: dict, envelope: dict) -> None:
    assert manifest["claims"] == []
    assert envelope["claims"] == []
    assert "claims_note" in manifest


def test_outputs_match_manifest_file(manifest: dict, envelope: dict) -> None:
    assert envelope["outputs"]["asset_manifest.json"] == manifest
    # manifest 文件指纹必须与信封里登记的一致（防止 manifest 被就地改动而未重算信封）
    recorded = envelope["provenance"]["asset_manifest_sha256"]
    actual = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert recorded == actual, "manifest 指纹与信封登记值不一致，需重跑 build_report.py"


def test_envelope_passes_kf_result_schema(envelope: dict) -> None:
    schema_path = ROOT / "schemas" / "kf_result.v1.schema.json"
    if not schema_path.exists():
        pytest.skip("kf_result.v1.schema.json 不在本检出中（honest: not_run）")
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
