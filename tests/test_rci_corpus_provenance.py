"""RCI pilot200 语料快照溯源的回归测试（anchor KBM-RCI-S2B-PILOT）。

守的不是「脚本能跑」，而是四条不变量：

1. **字节级溯源**：`knowledge/rci-pilot200/corpus/` 下每个文件的 sha256 等于
   2026-11-12 冻结清单的值，且清单钉扎 == 扫描上游时的钉扎
   （能发现「文件在、内容被换」这种 PR#184 式的假交付）。
2. **第二副本互证**：每份文档与本仓第二条独立链路
   `docs/rci-f1-abc/snapshot/doc_*/` 里同 sha256 的副本逐字节相同——
   两次独立落盘互相印证，排除「只有一处手写、另一个路径抄过去」。
3. **清单 ↔ 磁盘互为完备**：不许有未登记文件，不许清单数与条目数不符。
4. **负控**（证明闸门会红）：改一个字节 / 截断 / 塞未登记文件 / 钉扎互相矛盾，
   校验器必须各自报出对应错误码。永远绿的闸门不算闸门。
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO / "knowledge" / "rci-pilot200" / "PROVENANCE.json"


def _load():
    path = REPO / "scripts" / "rci_corpus_provenance.py"
    spec = importlib.util.spec_from_file_location("rci_corpus_provenance", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("rci_corpus_provenance", mod)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def prov():
    return _load()


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


# ------------------------------------------------------------ 1. 清单自洽与字节溯源
def test_manifest_scope_is_an_explicit_subset(manifest):
    """清单必须自报「子集」，不能让人误以为是 200 份全量快照。"""
    assert manifest["anchor"] == "KBM-RCI-S2B-PILOT"
    assert manifest["scope"] == "subset"
    assert manifest["documents_in_pilot"] == 200
    assert manifest["documents_in_repo"] == len(manifest["documents"]) < manifest["documents_in_pilot"]
    assert manifest["upstream_mission"] == 15462
    assert "其余 198 份不复制入库" in manifest["scope_note"]


def test_every_snapshot_matches_frozen_sha256(prov, manifest):
    """仓内字节 == 冻结清单钉扎 == 扫描期钉扎；路径必须符合 locator 规则。"""
    issues = prov.check_documents(manifest, REPO)
    assert issues == [], issues
    for doc in manifest["documents"]:
        assert doc["sha256"] == doc["inventory_sha256"]
        assert doc["snapshot_path"] == prov.expected_snapshot_path(manifest, doc)
        assert (REPO / doc["snapshot_path"]).is_file()


def test_corpus_bytes_are_the_upstream_document_not_a_placeholder(manifest):
    """PR#184 第一轮的问题就是清单有文件、磁盘上其实是 `+0/-0` 的空占位。"""
    for doc in manifest["documents"]:
        blob = (REPO / doc["snapshot_path"]).read_bytes()
        assert len(blob) == doc["bytes"] > 1024
        assert b"\x00" not in blob, "疑似二进制占位"
        text = blob.decode("utf-8")
        assert text.startswith("#"), "上游文档应以一级标题开头"
        assert text.count("\n") + 1 == doc["line_count"]


def test_second_copy_in_f1_snapshot_is_byte_identical(prov, manifest):
    """第二链路独立副本互证：不是「一处手写、另一处照抄」。"""
    checked = 0
    for doc in manifest["documents"]:
        f1_path = REPO / doc["f1_snapshot_path"]
        if not f1_path.is_file():
            continue
        assert prov.sha256_file(f1_path) == doc["sha256"], doc["f1_snapshot_path"]
        assert f1_path.read_bytes() == (REPO / doc["snapshot_path"]).read_bytes()
        checked += 1
    assert checked == len(manifest["documents"]), "第二链路副本应覆盖全部快照文档"


def test_snapshot_documents_are_consumed_by_f1_abc_batch(manifest):
    """这些路径不是自娱自乐：它们必须真在 F1-ABC 批的 60 份文档里。"""
    batch = json.loads((REPO / "docs/rci-f1-abc/frozen/batch60.json").read_text(encoding="utf-8"))
    by_sha = {d["sha256"]: d for d in batch["documents"]}
    for doc in manifest["documents"]:
        hit = by_sha.get(doc["sha256"])
        assert hit is not None, doc["path"]
        assert hit["repo"] == doc["repo"] and hit["path"] == doc["path"]
        assert hit["doc_id"] == doc["f1_doc_id"]


def test_cli_reports_clean(prov, capsys):
    assert prov.main([]) == 0
    assert "0 issue(s)" in capsys.readouterr().err


# ------------------------------------------------------------------ 2. 负控（闸门会红）
def test_negative_control_detects_single_byte_edit(prov, manifest):
    target = REPO / manifest["documents"][0]["snapshot_path"]

    def tampering_reader(path: Path) -> bytes:
        blob = path.read_bytes()
        return b"X" + blob[1:] if path == target else blob

    codes = {i["code"] for i in prov.check_documents(manifest, REPO, reader=tampering_reader)}
    assert "E_SHA256_MISMATCH" in codes


def test_negative_control_detects_truncation(prov, manifest):
    target = REPO / manifest["documents"][0]["snapshot_path"]

    def truncating_reader(path: Path) -> bytes:
        blob = path.read_bytes()
        return blob[:-1] if path == target else blob

    codes = {i["code"] for i in prov.check_documents(manifest, REPO, reader=truncating_reader)}
    assert "E_BYTES_MISMATCH" in codes


def test_negative_control_detects_missing_snapshot(prov, manifest):
    hollow = dict(manifest, documents=[dict(manifest["documents"][0], snapshot_path="knowledge/rci-pilot200/corpus/nope.md")])
    codes = {i["code"] for i in prov.check_documents(hollow, REPO)}
    assert "E_SNAPSHOT_MISSING" in codes


def test_negative_control_detects_unlisted_file(prov, tmp_path):
    """往 corpus/ 里塞一个未登记文件，必须报 E_UNLISTED_FILE。"""
    fake = {"corpus_root": "corpus", "documents_in_repo": 0, "documents": []}
    (tmp_path / "corpus" / "TensorBEM").mkdir(parents=True)
    (tmp_path / "corpus" / "TensorBEM" / "smuggled.md").write_text("# not traced\n", encoding="utf-8")
    codes = {i["code"] for i in prov.check_coverage(fake, tmp_path)}
    assert "E_UNLISTED_FILE" in codes


def test_negative_control_detects_pin_disagreement(prov, manifest):
    """快照钉扎 != 扫描期钉扎 ⇒ 扫描后文件漂移，不是原件。"""
    drifted = dict(
        manifest,
        documents=[dict(manifest["documents"][0], inventory_sha256="0" * 64)],
    )
    codes = {i["code"] for i in prov.check_documents(drifted, REPO)}
    assert "E_INVENTORY_PIN_DISAGREE" in codes


# ------------------------------------------------------ 3. 交付卫生（PR#184 的教训）
def test_no_bytecode_or_cache_files_are_tracked():
    """PR#184 的文件清单里混着 `ke/__pycache__/*.pyc (+0/-0)`：空占位不能算交付。"""
    try:
        out = subprocess.run(
            ["git", "ls-files", "--", "*.pyc", "__pycache__/*"],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):  # pragma: no cover - 无 git 环境
        pytest.skip("git 不可用")
    assert out.strip() == "", f"不应跟踪的字节码/缓存文件: {out.split()}"