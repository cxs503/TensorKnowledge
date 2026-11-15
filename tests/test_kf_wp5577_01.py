#!/usr/bin/env python3
"""wp-5577-01 (01-asset-registration) — independent re-checks of the committed artifacts.

No network: everything is recomputed from the byte-exact local copy of the source
markdown (docs/kf/wp-5577-01/source/report_5577.md) and the committed JSON artifacts.

Run: python3 -m pytest tests/test_kf_wp5577_01.py -q
"""
from __future__ import annotations

import bisect
import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-5577-01"
SRC = PKG / "source"
SOURCE_MD = SRC / "report_5577.md"
SOURCE_JSON = SRC / "report_5577.json"
MANIFEST = PKG / "asset_manifest.json"
RESULT = PKG / "kf_result.json"
ACCEPTANCE = PKG / "acceptance.json"
FIGURE_PROBE = SRC / "figure_probe.json"
FIGURE_PNG = PKG / "fig1_asset_resolution.png"
REPORT_MD = PKG / "REPORT.md"
ENVELOPE_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"
MANIFEST_SCHEMA = REPO / "schemas" / "asset_manifest.v1.schema.json"
BUILDER_SCRIPT = REPO / "scripts" / "wp5577_build_report.py"
KF_REPORT_SCRIPT = REPO / "scripts" / "kf" / "wp5577_build_report.py"

CONTRACT_HASH = "60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8"
CONTRACT_CHARS = 3702
CONTRACT_BYTES = 5707


def _load_builder():
    spec = importlib.util.spec_from_file_location("wp5577_build_report", BUILDER_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_kf_report():
    spec = importlib.util.spec_from_file_location("kf_wp5577_build_report", KF_REPORT_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def md() -> str:
    return SOURCE_MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def record() -> dict:
    return json.loads(SOURCE_JSON.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf_result() -> dict:
    return json.loads(RESULT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def acceptance() -> dict:
    return json.loads(ACCEPTANCE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def probe() -> dict:
    return json.loads(FIGURE_PROBE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def builder():
    return _load_builder()


@pytest.fixture(scope="module")
def kf_report():
    return _load_kf_report()


# ---------------------------------------------------------------------------
# 源载荷与哈希钉子
# ---------------------------------------------------------------------------
def test_source_copy_is_byte_exact(md):
    raw = SOURCE_MD.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert raw == md.encode("utf-8")
    assert len(md) == CONTRACT_CHARS
    assert len(md.encode("utf-8")) == CONTRACT_BYTES


def test_source_hash_pinned_to_file(md):
    pinned = (SRC / "markdown.sha256").read_text(encoding="utf-8").strip()
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert pinned == "sha256:" + digest


def test_manifest_declares_the_same_source(manifest, md):
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["hash_alg"] == "sha256"
    assert manifest["source"]["field"] == "markdown"
    assert manifest["source"]["uri"] == "tensor://reports/5577"
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert manifest["source"]["bytes_utf8"] == CONTRACT_BYTES
    assert manifest["source"]["lines"] == len(md.rstrip("\n").split("\n"))


def test_source_matches_committed_platform_record(md, record):
    assert record["markdown"] == md
    assert record["id"] == 5577
    assert record["scenario_key"] == "campaign/bp-demo-in12p8"


def test_source_sizes_are_self_consistent(md, manifest):
    assert manifest["source"]["chars"] == len(md)
    assert manifest["source"]["bytes_utf8"] == len(md.encode("utf-8"))
    assert manifest["source"]["lines"] == len(md.rstrip("\n").split("\n"))


# ---------------------------------------------------------------------------
# schema 门
# ---------------------------------------------------------------------------
def test_asset_manifest_passes_schema(manifest):
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_kf_result_passes_schema(kf_result):
    schema = json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(kf_result, schema)


def test_kf_result_provenance_matches_manifest(manifest, kf_result):
    assert kf_result["report_id"] == manifest["report_id"]
    assert kf_result["package_id"] == manifest["package_id"]
    prov = kf_result["provenance"]
    assert prov["source_hash"] == "sha256:" + manifest["source"]["hash"]
    assert prov["source_uri"] == manifest["source"]["uri"]
    assert prov["chars"] == manifest["source"]["chars"]
    out = kf_result["outputs"]["asset_manifest.json"]
    assert out["path"] == "docs/kf/wp-5577-01/asset_manifest.json"
    assert out["counts"]["assets"] == manifest["counts"]["assets"]


# ---------------------------------------------------------------------------
# locator：切片自洽 / 唯一 / 行号可反算
# ---------------------------------------------------------------------------
def test_every_locator_quote_is_reproducible_from_the_source(manifest, md):
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            assert (loc["start_char"], loc["end_char"]) == (0, len(md.rstrip("\n"))), a["asset_id"]
            assert loc["quote"] in md, a["asset_id"]
        else:
            assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
        assert loc["quote"].strip(), a["asset_id"]


def test_locator_quotes_are_unique(manifest, md):
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            continue
        assert md.count(loc["quote"]) == 1, a["asset_id"]
        assert loc["unique"] is True, a["asset_id"]


def test_line_numbers_agree_with_char_spans(manifest, md):
    body = md.rstrip("\n")
    lines = body.split("\n")
    starts = []
    pos = 0
    for ln in lines:
        starts.append(pos)
        pos += len(ln) + 1
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            assert loc["start_line"] == 1
            assert loc["end_line"] == len(lines)
            continue
        assert bisect.bisect_right(starts, loc["start_char"]) == loc["start_line"], a["asset_id"]
        assert bisect.bisect_right(starts, loc["end_char"] - 1) == loc["end_line"], a["asset_id"]
        assert loc["start_line"] <= loc["end_line"]


def test_locate_expands_to_unique_when_needle_ambiguous(builder, md):
    needle = "Holtrop"
    assert md.count(needle) > 1
    loc = builder.locate(md, needle)
    assert loc["unique"] is True
    assert md.count(loc["quote"]) == 1
    assert loc["quote"] == md[loc["start_char"]:loc["end_char"]]


def test_locate_raises_on_absent_needle(builder, md):
    with pytest.raises(SystemExit):
        builder.locate(md, "此串在源报告中不存在-5577-test")


# ---------------------------------------------------------------------------
# 清单结构与计数
# ---------------------------------------------------------------------------
def test_no_duplicate_or_malformed_ids(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == ["A%02d" % i for i in range(1, len(ids) + 1)]


def test_counts_match_assets(manifest):
    c = manifest["counts"]
    assert c["assets"] == len(manifest["assets"])
    assert sum(c["by_class"].values()) == c["assets"]
    assert sum(c["by_resolution"].values()) == c["assets"]
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert c[res] == c["by_resolution"].get(res, 0)


def test_resolution_states_are_consistent(manifest):
    pairs = {
        "resolved_in_source": {"resolved"},
        "referenced_unresolved": {"unresolved"},
        "declared_absent": {"absent"},
    }
    for a in manifest["assets"]:
        assert a["resolution"] in pairs, a["asset_id"]
        assert a["resolution_check"]["result"] in pairs[a["resolution"]], a["asset_id"]


def test_every_asset_carries_resolution_check(manifest, md):
    for a in manifest["assets"]:
        check = a["resolution_check"]
        assert check["check"] and check["result"]
        if a["resolution"] == "resolved_in_source":
            assert check["result"] == "resolved"
        elif a["resolution"] == "declared_absent":
            assert check["result"] == "absent"
        else:
            assert check["result"] == "unresolved"
            assert a.get("note"), a["asset_id"]


def test_declared_absent_assets_are_explicit_in_source(md, manifest):
    absent = [a for a in manifest["assets"] if a["resolution"] == "declared_absent"]
    assert absent, "源报告至少有一处显式声明不可得（KCS EFD / 七维指标）"
    for a in absent:
        assert "未取得" in a["locator"]["quote"] or "证据" in a["locator"]["quote"]


# ---------------------------------------------------------------------------
# 图：登记完整、字节 honest、本包图可校验
# ---------------------------------------------------------------------------
def test_all_platform_figures_are_registered(record, manifest):
    declared = [f["name"] for f in record["figures"]]
    registered = [a["probe"]["name"] for a in manifest["assets"]
                  if a["asset_class"] == "embedded_figure"]
    assert sorted(declared) == sorted(registered)


def test_unresolved_figures_record_http_evidence(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    for a in figs:
        check = a["resolution_check"]
        assert "http_status" in check
        if check.get("bytes", 0):
            assert a["resolution"] == "resolved_in_source" or check["http_status"] == 200
        else:
            assert a["resolution"] == "referenced_unresolved"
            assert check["http_status"] == 404


def test_package_figure_is_a_real_png_with_recorded_hash(acceptance):
    blob = FIGURE_PNG.read_bytes()
    assert blob[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(blob) > 10_000
    assert acceptance["figure"]["sha256"] == hashlib.sha256(blob).hexdigest()
    assert acceptance["figure"]["bytes"] == len(blob)


def test_figure_probe_conclusion(probe):
    assert probe["all_targets_404"] is True
    assert probe["control_ok"] is True
    assert probe["probe_valid"] is True


# ---------------------------------------------------------------------------
# 伪造与污染守卫
# ---------------------------------------------------------------------------
def test_no_bytecode_or_pycache_in_package():
    """原 PR#152 把 ke/__pycache__/*.pyc 混进了提交；本包必须结构性禁止。"""
    junk = [str(p.relative_to(REPO)) for p in PKG.rglob("*")
            if p.suffix == ".pyc" or "__pycache__" in p.parts]
    assert junk == []


def test_cross_repo_references_are_not_fabricated(manifest):
    for a in manifest["assets"]:
        probe_info = a.get("probe") or {}
        if a["resolution"] != "referenced_unresolved" or probe_info.get("kind") != "repo_path":
            continue
        path = probe_info["path"]
        if path.startswith("symbol:"):
            continue
        assert not (REPO / path.rstrip("/")).exists(), path
        assert a["resolution_check"]["exists_in_this_worktree"] is False


def test_claims_empty_but_justified(manifest):
    assert manifest["claims"] == []
    assert len(manifest["claims_empty_reason"]) > 20


# ---------------------------------------------------------------------------
# 验收项
# ---------------------------------------------------------------------------
def test_acceptance_all_pass(acceptance):
    assert acceptance["items_total"] == len(acceptance["items"])
    assert acceptance["items_pass"] == acceptance["items_total"]
    assert acceptance["verdict"] == "PASS"
    ids = [i["id"] for i in acceptance["items"]]
    assert len(ids) == len(set(ids))
    required = {"AC%02d" % i for i in range(1, 17)}
    assert required.issubset(set(ids))
    for item in acceptance["items"]:
        assert item["pass"] is True, item


# ---------------------------------------------------------------------------
# 构建器可复现（防手改）
# ---------------------------------------------------------------------------
def test_builder_reproduces_committed_manifest(builder, md, record, manifest):
    """离线重放 plan()：产物必须逐字段等于提交的 manifest —— 证明它不是手写的。"""
    probes = {}
    for a in manifest["assets"]:
        probe_info = a.get("probe")
        if not probe_info:
            continue
        kind = probe_info.get("kind")
        if kind == "platform_figure":
            probes[a["asset_id"]] = {
                "http_status": probe_info.get("http_status"),
                "bytes": probe_info.get("bytes", 0),
            }
        elif kind == "repo_path":
            probes[a["asset_id"]] = {
                "exists_in_this_worktree": bool(probe_info.get("exists_in_this_worktree", False)),
            }
    replayed = builder.plan(md, record, probes)
    assert replayed["manifest"] == manifest
    assert replayed["digest"] == manifest["source"]["hash"]


def test_builder_detects_tampered_manifest(builder, md, record, manifest):
    """变异测试：改一个 quote，重放必须不等。"""
    probes = {}
    for a in manifest["assets"]:
        probe_info = a.get("probe")
        if not probe_info:
            continue
        kind = probe_info.get("kind")
        if kind == "platform_figure":
            probes[a["asset_id"]] = {
                "http_status": probe_info.get("http_status"),
                "bytes": probe_info.get("bytes", 0),
            }
        elif kind == "repo_path":
            probes[a["asset_id"]] = {
                "exists_in_this_worktree": bool(probe_info.get("exists_in_this_worktree", False)),
            }
    replayed = builder.plan(md, record, probes)
    tampered = json.loads(json.dumps(manifest))
    tampered["assets"][1]["locator"]["quote"] = tampered["assets"][1]["locator"]["quote"][:-1] + "X"
    assert replayed["manifest"] != tampered


# ---------------------------------------------------------------------------
# KF 报告脚本守卫
# ---------------------------------------------------------------------------
def test_kf_report_script_exists():
    assert KF_REPORT_SCRIPT.exists()


def test_kf_report_verbatim_function(kf_report, md):
    """KF 报告脚本的 verbatim() 必须能定位所有 EVIDENCE 标记。"""
    for field, marker, note in kf_report.EVIDENCE:
        line_no, line, start = kf_report.verbatim(md, marker)
        assert line_no > 0
        assert 0 <= start < len(md)
        assert marker in line


def test_kf_report_contract_hash_matches(kf_report):
    assert kf_report.CONTRACT_HASH == CONTRACT_HASH
    assert kf_report.CONTRACT_CHARS == CONTRACT_CHARS


def test_kf_report_render_produces_report(kf_report):
    """render() 必须产出 REPORT.md 且内容含六要素标题。"""
    report_path = kf_report.render()
    assert report_path.exists()
    text = report_path.read_text(encoding="utf-8")
    for section in ("① 案例介绍", "② 怎么做的", "③ 计算结果", "④ 证据定位表", "⑤ 注意点", "⑥ 误差判定"):
        assert section in text, f"missing section: {section}"
    assert CONTRACT_HASH[:16] in text
    assert "wp-5577-01" in text


def test_kf_report_render_evidence_table_complete(kf_report):
    """渲染的报告必须包含所有 EVIDENCE 字段。"""
    report_path = kf_report.render()
    text = report_path.read_text(encoding="utf-8")
    for field, marker, note in kf_report.EVIDENCE:
        assert "`%s`" % field in text, f"missing evidence field: {field}"


def test_kf_report_render_acceptance_table_complete(kf_report, acceptance):
    """渲染的报告必须包含所有验收项。"""
    report_path = kf_report.render()
    text = report_path.read_text(encoding="utf-8")
    for item in acceptance["items"]:
        assert item["id"] in text, f"missing acceptance item: {item['id']}"


def test_kf_report_render_error_judgment_table(kf_report):
    """渲染的报告必须包含误差判定表。"""
    report_path = kf_report.render()
    text = report_path.read_text(encoding="utf-8")
    assert "E1" in text
    assert "E5" in text
    assert "HONEST-FAIL" in text


def test_kf_report_no_verified_marks(kf_report):
    """纪律：报告不得出现 verified=true 标记。"""
    report_path = kf_report.render()
    text = report_path.read_text(encoding="utf-8")
    assert "verified=true" not in text.lower()
    assert '"verified"' not in text


# ---------------------------------------------------------------------------
# 结果信封守卫
# ---------------------------------------------------------------------------
def test_result_carries_no_verified_marks():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    assert all(c.get("status") != "verified" for c in result.get("claims", []))
    blob = json.dumps(result["outputs"]["asset_manifest.json"])
    assert blob.count('"verified"') == 0


def test_scope_guard_only_report_5577_is_referenced():
    manifest_data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    blob = json.dumps(manifest_data)
    for other in ("tensor://reports/542", "tensor://reports/623", "tensor://reports/1610",
                  "tensor://reports/448", "tensor://reports/8288"):
        assert other not in blob


def test_result_envelope_validates_against_platform_schema():
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    schema = json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.validate(result, schema)
    assert result["package_id"] == "wp-5577-01"
    assert result["task_type"] == "01-asset-registration"
    assert result["report_id"] == "5577"
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert result["provenance"]["source_field"] == "markdown"
    assert "asset_manifest.json" in result["outputs"]
