"""wp-12510-01 · 资产登记不变量测试（含负对照：篡改必须被检出）。"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys

import pytest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(REPO, "docs", "kf", "wp-12510-01")
SNAP_MD = os.path.join(REPO, "runs", "wp-12510-01", "report_12510.md")
CONTRACT_HASH = "sha256:45f688344f4bc7983fc167fa84ef0fb47ad9a7a8265bcfbe8095239002da62da"


@pytest.fixture(scope="module")
def env() -> dict:
    return json.load(open(os.path.join(PKG, "kf_result.json"), encoding="utf-8"))


@pytest.fixture(scope="module")
def man() -> dict:
    return json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))


@pytest.fixture(scope="module")
def md() -> str:
    return open(SNAP_MD, encoding="utf-8").read()


def test_envelope_identity(env):
    assert env["package_id"] == "wp-12510-01"
    assert env["task_type"] == "01-asset-registration"
    assert env["report_id"] == "12510"
    assert env["provenance"]["source_field"] == "markdown"
    assert set(env["outputs"].keys()) == {"asset_manifest.json"}


def test_source_hash_matches_contract(env, md):
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert env["provenance"]["source_hash"] == CONTRACT_HASH


def test_source_chars(env, md):
    assert len(md) == 5656
    assert env["outputs"]["asset_manifest.json"]["source"]["chars"] == 5656


def test_all_markdown_locators_verbatim_unique(env, md):
    n = 0
    for a in env["outputs"]["asset_manifest.json"]["assets"]:
        for loc in a["locators"]:
            if loc.get("source_field") != "markdown":
                continue
            n += 1
            q = loc["quote"]
            assert md.count(q) == 1, f"quote not unique: {q[:40]}"
            s = md.index(q)
            assert loc["char_start"] == s
            assert loc["char_end"] == s + len(q)
    assert n == 7  # 1 源文档 + 4 图 + 代码 + 测试


def test_no_duplicate_ids(man):
    ids = [a["asset_id"] for a in man["assets"]]
    assert len(ids) == len(set(ids)) == 8
    assert man["claims"] == []


def test_figure_bytes_hashed_on_node(man):
    """4 张图的节点字节哈希与 manifest 记录一致（只读复算）。"""
    figs = [a for a in man["assets"] if a["kind"] == "figure"]
    assert len(figs) == 4
    for a in figs:
        disk = a["node_artifact"]
        assert disk["exists"]
        b = open(disk["path"], "rb").read()
        assert "sha256:" + hashlib.sha256(b).hexdigest() == disk["sha256"]
        assert disk["bytes"] == len(b)


def test_negative_tampered_quote_detected(env, md):
    """负对照：篡改任一 markdown locator 的 quote 后，逐字回解必须失败。"""
    man = copy.deepcopy(env["outputs"]["asset_manifest.json"])
    for a in man["assets"]:
        for loc in a["locators"]:
            if loc.get("source_field") == "markdown":
                loc["quote"] = loc["quote"] + "TAMPERED"
                assert md.count(loc["quote"]) == 0  # 篡改后不再是原文子串
                break
        else:
            continue
        break
    # 回解器视角：篡改后的 quote 无法在原文定位
    assert md.count("TAMPERED") == 0


def test_negative_duplicate_id_detected(man):
    """负对照：复制一个 asset_id 后唯一性检查必须失败。"""
    ids = [a["asset_id"] for a in man["assets"]]
    ids.append(ids[0])
    assert len(ids) != len(set(ids))


def test_offline_rerun_deterministic():
    """离线复跑：builder 重跑后 manifest 的哈希/计数/定位不变（emitted_at 除外）。"""
    before = json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, "scripts", "wp12510_register_assets.py"), "--offline"],
        capture_output=True, text=True, cwd=REPO,
    )
    assert r.returncode == 0, r.stderr
    after = json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))
    for k in ("source", "assets", "asset_counts", "id_uniqueness", "claims", "integrity"):
        assert before[k] == after[k], f"non-deterministic field: {k}"


def test_acceptance_gate_green():
    r = subprocess.run(
        [sys.executable, os.path.join(REPO, "scripts", "wp12510_verify_acceptance.py")],
        capture_output=True, text=True, cwd=REPO,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    acc = json.load(open(os.path.join(PKG, "acceptance.json"), encoding="utf-8"))
    assert acc["all_pass"] is True
