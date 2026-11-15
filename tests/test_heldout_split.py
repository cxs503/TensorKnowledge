"""held-out 评测切分测试（防训练/评测泄漏）。

覆盖：
  * 名单文件 ≥15 案、案号唯一、schema 校验；案数不足即拒绝
  * builder 在入库前剔除 held-out 行（case_id 命中 / split 标记命中两条路径）
  * 库内行复核：任何 held-out 案号都不在数据集里（verify_no_leak）
  * manifest 声明块：名单 id / sha256 / 排除清单 / 行数对账
  * 同一名单下 v1.0 与 v1.1 的声明可比对（名单改了 sha256 会变）

Run: python -m pytest tests/test_heldout_split.py -v
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from ke import held_out as HO
from ke.dataset_builder import build_dataset
from ke.datasets import DatasetStore
from ke.train_gate import TrainGateStore

REPO = Path(__file__).resolve().parents[1]
REG_PATH = REPO / "benchmarks" / "heldout" / "heldout_cases_v1.json"


@pytest.fixture()
def registry():
    return HO.load_held_out()


def test_registry_has_at_least_15_unique_cases(registry):
    assert len(registry) >= HO.MIN_CASES
    ids = [c["case_id"] for c in registry.cases]
    assert len(ids) == len(set(ids))
    assert all(c.get("domain") for c in registry.cases)
    # 覆盖九学科的多数：至少 5 个不同 domain
    assert len({c["domain"] for c in registry.cases}) >= 5
    assert len(registry.sha256) == 64


def test_registry_rejects_short_list(tmp_path):
    p = tmp_path / "short.json"
    p.write_text(json.dumps({
        "schema": HO.REGISTRY_SCHEMA,
        "list_id": "short",
        "cases": [{"case_id": f"HO-{i}", "domain": "resistance"} for i in range(5)],
    }), encoding="utf-8")
    with pytest.raises(ValueError, match=">= 15"):
        HO.load_held_out(p)


def test_registry_rejects_duplicate_case(tmp_path):
    cases = [{"case_id": "HO-DUP", "domain": "resistance"} for _ in range(15)]
    p = tmp_path / "dup.json"
    p.write_text(json.dumps({"schema": HO.REGISTRY_SCHEMA, "cases": cases}), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate"):
        HO.load_held_out(p)


def test_filter_by_case_id_and_split_flag(registry):
    held = next(iter(registry.case_ids))
    rows = [
        {"id": "a", "case_id": "SIM-RES-OK"},
        {"id": "b", "case_id": held},
        {"id": "c", "benchmark_name": held},
        {"id": "d", "split": "held-out"},
        {"id": "e", "split": "test"},
        {"id": "f", "split": "train"},
    ]
    kept, excluded = HO.filter_training_rows(rows, registry)
    assert [r["id"] for r in kept] == ["a", "f"]
    reasons = {e["id"]: e["reason"] for e in excluded}
    assert reasons == {"b": "held_out_case_id", "c": "held_out_case_id",
                       "d": "held_out_split_flag", "e": "held_out_split_flag"}


def test_builder_excludes_held_out_and_declares_in_manifest(registry, tmp_path):
    store = DatasetStore(tmp_path / "ds.sqlite")
    gate = TrainGateStore(conn=store.conn)
    store.attach_gate(gate)
    held = sorted(registry.case_ids)[:3]
    rows = [{"id": f"ok-{i}", "case_id": f"SIM-{i}", "text": f"row {i}"} for i in range(5)]
    rows += [{"id": f"leak-{i}", "case_id": cid, "text": "held-out"} for i, cid in enumerate(held)]
    rows += [{"id": "split-leak", "split": "held-out", "text": "held-out"}]

    built = build_dataset(store, "DS", "v1.0", rows, status="draft",
                          producer="builder-test", gate=gate)

    assert built["kept_rows"] == 5
    assert len(built["excluded"]) == 4
    manifest = built["manifest"]
    assert manifest["row_count"] == 5
    decl = manifest["held_out"]
    assert decl["list_id"] == registry.list_id
    assert decl["list_sha256"] == registry.sha256
    assert decl["case_count"] == len(registry)
    assert decl["source_rows"] == 9 and decl["training_rows"] == 5
    assert decl["excluded_count"] == 4
    assert set(held) <= set(decl["excluded"])

    # 库内实读：没有 held-out 案号
    stored = [json.loads(r["row_json"]) for r in store.conn.execute(
        "SELECT row_json FROM dataset_rows WHERE name='DS' AND version='v1.0' ORDER BY row_index")]
    assert len(stored) == 5
    assert not (registry.case_ids & {r.get("case_id") for r in stored})
    # 闸门初始 none
    assert gate.get("DS", "v1.0")["review_level"] == "none"


def test_manifest_keeps_held_out_declaration_after_promote(registry, tmp_path):
    store = DatasetStore(tmp_path / "ds.sqlite")
    build_dataset(store, "DS", "v1.0", [{"id": "a", "text": "t"}], status="draft")
    store.promote("DS", "v1.0", "reviewed")
    manifest = store.get_manifest("DS", "v1.0")
    assert manifest["status"] == "reviewed"
    assert manifest["held_out"]["list_id"] == registry.list_id
    assert manifest["held_out"]["list_sha256"] == registry.sha256


def test_verify_no_leak_detects_injected_row(registry, tmp_path):
    """绕过 builder 直接入库的行，复核函数必须报泄漏（builder 的后置闸）。"""
    store = DatasetStore(tmp_path / "ds.sqlite")
    held = sorted(registry.case_ids)[0]
    store.register("BYPASS", "v1.0", [{"id": "bad", "case_id": held, "text": "t"}],
                   status="draft")
    stored = [json.loads(r["row_json"]) for r in store.conn.execute(
        "SELECT row_json FROM dataset_rows WHERE name='BYPASS'")]
    with pytest.raises(AssertionError, match="held-out leak"):
        HO.verify_no_leak(stored, registry)
    assert HO.row_case_id({"source": {"case_id": held}}) == held


def test_sim_datahouse_source_exclusion_math(registry):
    """仓库内 FEAT-SIM-DATAHOUSE v1.0 源数据：held-out 行必须被全部剔除。"""
    rows = [json.loads(line) for line in
            (REPO / "data" / "sim_datahouse_v1_source.jsonl").read_text(
                encoding="utf-8").splitlines() if line.strip()]
    kept, excluded = HO.filter_training_rows(rows, registry)
    assert len(rows) == len(kept) + len(excluded)
    assert len(excluded) >= 6
    assert not (registry.case_ids & {HO.row_case_id(r) for r in kept})
    decl = HO.declaration(registry, kept, excluded, len(rows))
    assert decl["training_rows"] == len(kept) and decl["excluded_count"] == len(excluded)