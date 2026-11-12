#!/usr/bin/env python3
"""wp-2506-01（工序 01-asset-registration，report 2506）回归测试。

断言的是**不变量**而不是"脚本跑过了"：
- 指纹：markdown 字节哈希 == 契约 source_hash，chars == 契约 chars；
- 可定位性：每条 quote 必须能在快照 markdown 里逐字命中，且 offset 回读一致（防"存了但指不到"）；
- 互不覆盖：清单/快照只涉及 report_id=2506；
- 口径：不抽取（claims=[]）、不标 verified；
- 缺口：declared_unresolvable 必须带理由，不允许静默丢资产；
- 结构：两份 schema（Draft 2020-12）零错误；
- 交付：knowledge/kf/wp-2506-01 镜像与 artifacts 逐字节一致；正文只有一个 json 块且与信封一致；
- 可重建：离线用快照重跑，除 generated_at 外与仓库产物逐字节一致。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-2506-01"
ART = ROOT / "artifacts" / "kf" / PKG
MIRROR = ROOT / "knowledge" / "kf" / PKG
# artifacts/ 被 .gitignore 忽略；干净检出（CI/自动推送分支）下只有 knowledge/ 镜像，
# 故产物根目录回退到镜像——两者逐字节一致由 test_mirror_is_byte_identical 保证。
if not ART.exists():
    ART = MIRROR
SNAP = ART / "source_snapshot" / "report_2506.json"
DOC = ROOT / "docs" / "kf" / "KF-RESULT-wp-2506-01.md"
CONTRACT_HASH = "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0"
CONTRACT_CHARS = 3382


@pytest.fixture(scope="module")
def man() -> dict:
    return json.loads((ART / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def env() -> dict:
    return json.loads((ART / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def checks() -> dict:
    return json.loads((ART / "checks.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def snapshot() -> dict:
    return json.loads(SNAP.read_text(encoding="utf-8"))


def test_source_fingerprint_matches_contract(man, snapshot):
    assert man["source"]["source_hash"] == CONTRACT_HASH
    assert man["source"]["contract_source_hash"] == CONTRACT_HASH
    assert man["source"]["hash_match"] is True
    assert man["source"]["chars"] == CONTRACT_CHARS
    assert man["source"]["chars_match_contract"] is True
    # 快照自洽：sha256 取自快照里的 markdown 本身
    import hashlib

    md = snapshot["markdown"]
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert man["identity_facts"]["markdown_sha256"] == CONTRACT_HASH


def test_report_id_is_locked_to_2506(man, snapshot):
    assert man["report_id"] == "2506"
    assert man["source"]["report_id"] == "2506"
    assert man["source"]["source_uri"] == "tensor://reports/2506"
    assert str(snapshot["id"]) == "2506"
    # 清单里出现的 report 引用只能是 2506（互不覆盖的机器检查）
    blob = json.dumps(man, ensure_ascii=False)
    refs = set(re.findall(r"tensor://reports/(\d+)", blob)) | set(
        re.findall(r"/tensor/reports/(\d+)", blob)
    )
    assert refs == {"2506"}, refs


def test_every_locator_resolves_in_snapshot(man, snapshot):
    md = snapshot["markdown"]
    bad = []
    for a in man["assets"]:
        loc = a.get("locator")
        if not loc:
            continue
        q, off = loc["quote"], loc["offset_chars"]
        assert q, a["asset_id"]
        if q not in md:
            bad.append((a["asset_id"], "not_substring"))
        if md[off:off + len(q)] != q:
            bad.append((a["asset_id"], "offset_mismatch"))
        if loc["quote_verified"] is not True:
            bad.append((a["asset_id"], "quote_verified_flag"))
        assert loc["count_occurrences"] >= 1, a["asset_id"]
    assert bad == []


def test_locator_checks_cover_all_located_assets(man):
    located = {a["asset_id"] for a in man["assets"] if a.get("locator")}
    assert located == set(man["locator_checks"])
    for aid, v in man["locator_checks"].items():
        assert v["resolvable_in_markdown"] and v["back_read_ok"], aid


def test_no_duplicate_asset_ids(man):
    ids = [a["asset_id"] for a in man["assets"]]
    assert len(ids) == len(set(ids))
    for aid in ids:
        assert re.match(r"^asset-2506-\d{2}-[a-z0-9-]+$", aid), aid


def test_unresolvable_assets_have_explicit_reason(man):
    gaps = [a for a in man["assets"] if a["status"] != "resolved"]
    assert gaps, "本单至少应有图件字节不可得这一条缺口"
    for a in gaps:
        reason = str(a.get("unresolved_reason", "")).strip()
        assert len(reason) >= 10, a["asset_id"]
    # unresolved 摘要与资产列表一致
    assert {u["asset_id"] for u in man["unresolved"]} == {a["asset_id"] for a in gaps}
    for u in man["unresolved"]:
        assert len(u["reason"].strip()) >= 10


def test_scope_no_extraction_no_verification(man, env):
    assert man["scope"]["extraction_performed"] is False
    assert man["scope"]["verification_performed"] is False
    assert man["scope"]["claims_emitted"] == 0
    assert env["claims"] == []
    assert env["task_type"] == "01-asset-registration"
    assert env["package_id"] == PKG
    assert env["report_id"] == "2506"
    blob = json.dumps(env, ensure_ascii=False).lower()
    assert '"verified": true' not in blob
    assert '"status": "verified"' not in blob


def test_package_envelope_matches_manifest(env, man):
    inner = env["outputs"]["asset_manifest.json"]
    assert inner == man
    assert env["provenance"]["source_hash"] == man["source"]["source_hash"] == CONTRACT_HASH
    assert env["provenance"]["source_field"] == "markdown"
    assert env["provenance"]["source_uri"] == "tensor://reports/2506"


@pytest.mark.parametrize("schema_name,target", [
    ("asset_manifest.v1.schema.json", "manifest"),
    ("kf_result.v1.schema.json", "envelope"),
])
def test_schema_pass(schema_name, target, man, env):
    schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
    doc = man if target == "manifest" else env
    errs = sorted(jsonschema.Draft202012Validator(schema).iter_errors(doc), key=str)
    assert [e.message for e in errs] == []


def test_all_checks_pass(checks):
    assert checks["all_pass"] is True
    assert [c["name"] for c in checks["checks"] if not c["passed"]] == []
    names = {c["name"] for c in checks["checks"]}
    for required in ["valid_json", "schema_pass", "source_locator_resolvable",
                     "source_hash_matches", "no_duplicate_ids",
                     "all_claims_have_evidence_or_explicit_unresolved_status"]:
        assert required in names, required
    assert checks["acceptance"]["valid_json"] is True


def test_report_doc_has_single_json_block_equal_to_envelope(env):
    text = DOC.read_text(encoding="utf-8")
    assert text.splitlines()[0].strip() == "# KF-RESULT wp-2506-01"
    assert text.count("```json") == 1
    block = text.split("```json", 1)[1].split("```", 1)[0]
    assert json.loads(block) == env
    assert "kf-wp:wp-2506-01" not in text  # tags 走 API，不塞正文
    # 六段齐全
    for sec in ["①", "②", "③", "④", "⑤", "⑥"]:
        assert sec in text


def test_mirror_is_byte_identical():
    for rel in ["asset_manifest.json", "kf_result.json", "checks.json",
                "source_snapshot/report_2506.json", "figures/wp2506_01_asset_registry.png",
                "delivery_verification.json"]:
        a, b = ART / rel, MIRROR / rel
        assert a.exists() and b.exists(), rel
        assert a.read_bytes() == b.read_bytes(), rel


def test_figure_is_real_png():
    head = (ART / "figures" / "wp2506_01_asset_registry.png").read_bytes()[:8]
    assert head == b"\x89PNG\r\n\x1a\n"


def test_offline_rebuild_reproduces_manifest(tmp_path):
    """离线用快照重跑，除 generated_at/路径相关探针外应与仓库产物一致。"""
    cmd = [sys.executable, str(ROOT / "scripts" / "kf" / "wp_2506_01_register_assets.py"),
           "--record-file", str(SNAP), "--out", str(tmp_path)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    fresh = json.loads((tmp_path / "asset_manifest.json").read_text(encoding="utf-8"))
    committed = json.loads((ART / "asset_manifest.json").read_text(encoding="utf-8"))
    for d in (fresh, committed):
        d.pop("generated_at")
        d["source"].pop("fetched_via")          # 取源信道不同（在线 GET vs 快照），属登记内容而非资产事实
        d["identity_facts"].pop("figure_endpoint_probes", None)
        d["identity_facts"].pop("mission_probe", None)
    assert fresh == committed

def test_delivery_verification_if_present():
    """交付自验（发布后回读）记录：若存在必须全绿，且哈希口径与契约一致。"""
    p = ART / "delivery_verification.json"
    if not p.exists():
        pytest.skip("未跑交付自验（离线环境）")
    d = json.loads(p.read_text(encoding="utf-8"))
    assert d["all_pass"] is True
    assert d["recomputed_source_sha256"] == CONTRACT_HASH
    assert d["checks"]["json_block_equals_local_envelope"] is True
    assert d["checks"]["tags_contain_package_tag"] is True
    assert d["checks"]["upstream_2506_figure_still_unreachable"] is True
    assert d["package_id"] == PKG
