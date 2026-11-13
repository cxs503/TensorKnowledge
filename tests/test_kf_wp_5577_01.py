#!/usr/bin/env python3
"""Invariants for work package wp-5577-01 (KF 工序 01 · asset-registration of report 5577).

Every fact is re-derived from the artifacts on disk (no constant copied from the
package's own JSON), and the builder's pure functions are re-run offline to prove
the committed manifest was produced by the code, not hand-edited. Mutation tests
show the instrument actually detects tampering.
"""

from __future__ import annotations

import bisect
import hashlib
import importlib.util
import json
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-5577-01"
SRC = PKG / "source"
BUILDER = ROOT / "scripts" / "wp5577_build_report.py"
SCHEMAS = ROOT / "schemas"


def _load_builder():
    spec = importlib.util.spec_from_file_location("wp5577_build_report", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def builder():
    return _load_builder()


@pytest.fixture(scope="module")
def md() -> str:
    return (SRC / "report_5577.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def record() -> dict:
    return json.loads((SRC / "report_5577.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf_result() -> dict:
    return json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def acceptance() -> dict:
    return json.loads((PKG / "acceptance.json").read_text(encoding="utf-8"))


def _starts(text: str):
    lines = text.rstrip("\n").split("\n")
    out, pos = [], 0
    for ln in lines:
        out.append(pos)
        pos += len(ln) + 1
    return lines, out


# ---------------------------------------------------------------------------
# 源载荷与哈希钉子
# ---------------------------------------------------------------------------
def test_source_payload_pinned_to_hash(md, manifest):
    raw = (SRC / "report_5577.md").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    pinned = (SRC / "markdown.sha256").read_text(encoding="utf-8").strip()
    assert pinned == "sha256:" + digest
    assert manifest["source"]["hash"] == digest
    assert manifest["source"]["hash_alg"] == "sha256"
    assert manifest["source"]["field"] == "markdown"
    assert manifest["source"]["uri"] == "tensor://reports/5577"


def test_source_sizes_are_self_consistent(md, manifest):
    assert manifest["source"]["chars"] == len(md)
    assert manifest["source"]["bytes_utf8"] == len(md.encode("utf-8"))
    assert manifest["source"]["lines"] == len(md.rstrip("\n").split("\n"))


def test_source_matches_committed_platform_record(md, record):
    """提交的 platform 响应与入包 markdown 必须是同一份载荷（防止各自漂移）。"""
    assert record["markdown"] == md
    assert record["id"] == 5577
    assert manifest_scenario(record) == "campaign/bp-demo-in12p8"


def manifest_scenario(record: dict) -> str:
    return record["scenario_key"]


# ---------------------------------------------------------------------------
# schema 门
# ---------------------------------------------------------------------------
def test_asset_manifest_passes_schema(manifest):
    schema = json.loads((SCHEMAS / "asset_manifest.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)


def test_kf_result_passes_schema(kf_result):
    schema = json.loads((SCHEMAS / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
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
def test_locator_quotes_are_exact_slices(md, manifest):
    body = md.rstrip("\n")
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["quote"] == body[loc["start_char"]:loc["end_char"]], a["asset_id"]
        assert 0 <= loc["start_char"] < loc["end_char"] <= len(body)
        assert loc["method"] in ("char_span", "document")


def test_locator_quotes_are_unique(md, manifest):
    for a in manifest["assets"]:
        assert md.count(a["locator"]["quote"]) == 1, a["asset_id"]
        assert a["locator"]["unique"] is True


def test_line_numbers_recompute_from_offsets(md, manifest):
    body = md.rstrip("\n")
    lines, starts = _starts(md)
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            assert loc["start_char"] == 0 and loc["end_char"] == len(body)
            assert (loc["start_line"], loc["end_line"]) == (1, len(lines))
            continue
        assert bisect.bisect_right(starts, loc["start_char"]) == loc["start_line"]
        assert bisect.bisect_right(starts, loc["end_char"] - 1) == loc["end_line"]
        assert loc["start_line"] <= loc["end_line"]


def test_locate_expands_to_unique_when_needle_ambiguous(builder, md):
    """短 needle 命中多处时必须扩行到唯一，且仍满足 quote == md[start:end]。"""
    needle = "Holtrop"
    assert md.count(needle) > 1
    loc = builder.locate(md, needle)
    assert loc["unique"] is True
    assert md.count(loc["quote"]) == 1
    assert loc["quote"] == md[loc["start_char"]:loc["end_char"]]


def test_locate_raises_on_absent_needle(builder, md):
    with pytest.raises(SystemExit):
        builder.locate(md, "此串在源报告中不存在-5577")


# ---------------------------------------------------------------------------
# 清单结构与计数
# ---------------------------------------------------------------------------
def test_asset_ids_are_contiguous_and_unique(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids == ["A%02d" % i for i in range(1, len(ids) + 1)]


def test_counts_reconcile(manifest):
    counts = manifest["counts"]
    assets = manifest["assets"]
    assert counts["assets"] == len(assets)
    assert sum(counts["by_class"].values()) == len(assets)
    assert sum(counts["by_resolution"].values()) == len(assets)
    recomputed: dict = {}
    for a in assets:
        recomputed[a["resolution"]] = recomputed.get(a["resolution"], 0) + 1
    assert counts["by_resolution"]["resolved_in_source"] == recomputed.get("resolved_in_source", 0)
    assert counts["by_resolution"]["referenced_unresolved"] == recomputed.get("referenced_unresolved", 0)
    assert counts["by_resolution"]["declared_absent"] == recomputed.get("declared_absent", 0)
    for key in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        assert counts[key] == counts["by_resolution"][key]


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
            assert a["note"], a["asset_id"]


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
        if check["bytes"]:
            assert a["resolution"] == "resolved_in_source" or check["http_status"] == 200
        else:
            assert a["resolution"] == "referenced_unresolved"
            assert check["http_status"] == 404


def test_package_figure_is_a_real_png_with_recorded_hash(acceptance):
    fig = PKG / "fig1_asset_resolution.png"
    blob = fig.read_bytes()
    assert blob[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(blob) > 10_000
    assert acceptance["figure"]["sha256"] == hashlib.sha256(blob).hexdigest()
    assert acceptance["figure"]["bytes"] == len(blob)


# ---------------------------------------------------------------------------
# 伪造与污染守卫
# ---------------------------------------------------------------------------
def test_no_bytecode_or_pycache_in_package():
    """原 PR#152 把 ke/__pycache__/*.pyc 混进了提交；本包必须结构性禁止。"""
    junk = [str(p.relative_to(ROOT)) for p in PKG.rglob("*")
            if p.suffix == ".pyc" or "__pycache__" in p.parts]
    assert junk == []


def test_cross_repo_references_are_not_fabricated(manifest):
    for a in manifest["assets"]:
        probe = a.get("probe") or {}
        if a["resolution"] != "referenced_unresolved" or probe.get("kind") != "repo_path":
            continue
        path = probe["path"]
        if path.startswith("symbol:"):
            continue
        assert not (ROOT / path.rstrip("/")).exists(), path
        assert a["resolution_check"]["exists_in_this_worktree"] is False


def test_claims_empty_but_justified(manifest):
    assert manifest["claims"] == []
    assert len(manifest["claims_empty_reason"]) > 20


# ---------------------------------------------------------------------------
# 验收项 + 构建器可复现（防手改）
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


def test_builder_reproduces_committed_manifest(builder, md, record, manifest):
    """离线重放 plan()：产物必须逐字段等于提交的 manifest —— 证明它不是手写的。"""
    probes = {}
    for a in manifest["assets"]:
        probe = a.get("probe")
        if not probe:
            continue
        kind = probe.get("kind")
        if kind == "platform_figure":
            probes[a["asset_id"]] = {
                "http_status": probe.get("http_status"),
                "bytes": probe.get("bytes", 0),
            }
        elif kind == "repo_path":
            probes[a["asset_id"]] = {
                "exists_in_this_worktree": bool(probe.get("exists_in_this_worktree", False)),
            }
    replayed = builder.plan(md, record, probes)
    assert replayed["manifest"] == manifest
    assert replayed["digest"] == manifest["source"]["hash"]


def test_builder_detects_tampered_manifest(builder, md, record, manifest):
    """变异测试：改一个 quote / 一个计数，检验器必须报错。"""
    tampered = json.loads(json.dumps(manifest))
    tampered["assets"][1]["locator"]["quote"] = tampered["assets"][1]["locator"]["quote"] + "X"
    body = md.rstrip("\n")
    loc = tampered["assets"][1]["locator"]
    assert loc["quote"] != body[loc["start_char"]:loc["end_char"]]

    tampered2 = json.loads(json.dumps(manifest))
    tampered2["counts"]["assets"] += 1
    assert sum(tampered2["counts"]["by_resolution"].values()) != tampered2["counts"]["assets"]

    schema = json.loads((SCHEMAS / "asset_manifest.v1.schema.json").read_text(encoding="utf-8"))
    tampered3 = json.loads(json.dumps(manifest))
    tampered3["task_type"] = "03-knowledge-extraction"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(tampered3, schema)

# ---------------------------------------------------------------------------
# 图字节探活工件（404 的归因必须可复算，而不是散文断言）
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def probe_artifact() -> dict:
    return json.loads((SRC / "figure_probe.json").read_text(encoding="utf-8"))


def test_probe_artifact_covers_declared_figures(record, probe_artifact):
    declared = [f["name"] for f in record["figures"]]
    assert probe_artifact["report_id"] == "5577"
    assert sorted(probe_artifact["target_figures"]) == sorted(declared)
    assert sorted(t["name"] for t in probe_artifact["targets"]) == sorted(declared)
    for t in probe_artifact["targets"]:
        assert isinstance(t["http_status"], int)
        assert t["payload_bytes"] >= 0 and t["body_bytes"] >= 0


def test_probe_artifact_has_a_working_positive_control(probe_artifact):
    """正对照取自同路由的另一份报告：必须 200 且载荷非空、带 sha256。"""
    ctl = probe_artifact["controls"][0]
    assert ctl["report_id"] != probe_artifact["report_id"]
    assert ctl["http_status"] == 200
    assert ctl["payload_bytes"] > 0
    assert len(ctl["payload_sha256"]) == 64
    assert probe_artifact["control_used"]["name"] == ctl["name"]
    assert probe_artifact["control_ok"] is True
    assert probe_artifact["probe_valid"] is True


def test_probe_artifact_verdict_is_recomputed_not_declared(builder, probe_artifact):
    """把工件里的 targets/controls 重新喂给纯函数 evaluate_probe，判定必须逐字段复现。"""
    recomputed = builder.evaluate_probe(probe_artifact["targets"], probe_artifact["controls"])
    for key in ("all_targets_404", "control_ok", "probe_valid", "conclusion"):
        assert recomputed[key] == probe_artifact[key], key
    assert recomputed["control_used"] == probe_artifact["control_used"]


def test_probe_artifact_status_agrees_with_manifest(manifest, probe_artifact):
    status = {t["name"]: t["http_status"] for t in probe_artifact["targets"]}
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    assert figs
    for a in figs:
        name = a["probe"]["name"]
        assert a["resolution_check"]["http_status"] == status[name]
        assert a["probe"]["http_status"] == status[name]
        assert a["resolution"] == "referenced_unresolved"


def test_evaluate_probe_rejects_an_invalid_control(builder, probe_artifact):
    """变异测试：正对照失效（404）时，404 归因必须被判为无效 —— 不许两边甩锅。"""
    bad = json.loads(json.dumps(probe_artifact))
    bad["controls"][0].update({"http_status": 404, "payload_bytes": 0, "payload_sha256": None})
    verdict = builder.evaluate_probe(bad["targets"], bad["controls"])
    assert verdict["control_ok"] is False
    assert verdict["probe_valid"] is False
    assert "无效" in verdict["conclusion"]
    # 目标图其实可达时，同样不许判「报告侧缺图」
    reachable = json.loads(json.dumps(probe_artifact))
    reachable["targets"][1].update({"http_status": 200, "payload_bytes": 1234,
                                    "payload_sha256": "0" * 64})
    verdict2 = builder.evaluate_probe(reachable["targets"], reachable["controls"])
    assert verdict2["all_targets_404"] is False
    assert verdict2["probe_valid"] is False


def test_probe_figure_bytes_short_circuits_on_first_good_control(builder):
    """探活顺序固定：第一个可用正对照命中即停；首个候选失败则落到下一个。"""
    calls = []

    def fake_fetch(path):
        calls.append(path)
        if "/reports/5577/figures/" in path:
            return {"http_status": 404, "payload_bytes": 0, "body_bytes": 29, "payload_sha256": None}
        if "/reports/11621/" in path:
            return {"http_status": 500, "payload_bytes": 0, "body_bytes": 5, "payload_sha256": None}
        return {"http_status": 200, "payload_bytes": 70557, "body_bytes": 70557,
                "payload_sha256": "9" * 64}

    art = builder.probe_figure_bytes(["a.png", "b.png"], token="t",
                                     candidates=(("11621", "x.png"), ("14965", "y.png")),
                                     fetch=fake_fetch)
    assert art["probe_valid"] is True
    assert art["control_used"] == {"report_id": "14965", "name": "y.png"}
    assert len(art["controls"]) == 2
    assert len(art["targets"]) == 2
    assert sum(1 for c in calls if "/reports/5577/" in c) == 2
