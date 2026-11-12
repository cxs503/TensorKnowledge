#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 预注册/批次/盲审/门禁/指标的机器校验（S1 判据）。

覆盖：
  1. 批次可复现性与不变量（60 份 / 12 分层 / 15 仓 / 三臂全覆盖 / B=C 配对）
  2. 预注册冻结（五指标键、阈值项、prereg_id 对内容敏感、绑定批次 digest）
  3. 结构门+证据门（sha 不符 / 引文不匹配 / 行区间越界必须判死，不许自报通过）
  4. 盲审去标识（禁字段/禁字样、sample_id 确定性、封存映射、人工表 ≥30）
  5. 五指标算术（合成夹具，明确标注 SYNTHETIC，不作为实验证据）+ 判定分支
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import rci_f1_batch as B  # noqa: E402
import rci_f1_blind as BL  # noqa: E402
import rci_f1_gate as G  # noqa: E402
import rci_f1_metrics as M  # noqa: E402
import rci_f1_prereg as P  # noqa: E402

ART = os.path.join(ROOT, "artifacts", "rci-f1-abc")
SOURCE = os.path.join(ART, "source", "pilot200_sample.json")
BATCH = os.path.join(ART, "batch60.json")


def test_batch_deterministic_and_invariants(tmp_path):
    d1, d2 = str(tmp_path / "b1"), str(tmp_path / "b2")
    a = B.build(SOURCE, d1, 60)
    b = B.build(SOURCE, d2, 60)
    assert a["batch"]["digest"] == b["batch"]["digest"]
    v = B.verify(d1)
    assert v["passed"], v
    assert v["batch_digest"] == a["batch"]["digest"]
    obs = a["batch"]["observed"]
    assert a["batch"]["n"] == 60 and obs["cells_covered"] == 12 and obs["repos_covered"] == 15
    # B/C 配对：同一 slot 的 doc 集合完全一致
    pk = a["packages"]
    bmap = {p["agent_slot"]: p["doc_ids"] for p in pk if p["lane"] == "B"}
    cmap = {p["agent_slot"]: p["doc_ids"] for p in pk if p["lane"] == "C"}
    assert bmap == cmap and all(len(v) == 3 for v in bmap.values())


def test_committed_batch_matches_selector():
    """入库批次必须能由脚本复算出来（防手改清单）。"""
    committed = json.load(open(os.path.join(ART, "batch60.json"), encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        fresh = B.build(SOURCE, td, 60)["batch"]
    assert fresh["digest"] == committed["digest"]
    assert [d["doc_id"] for d in fresh["documents"]] == [d["doc_id"] for d in committed["documents"]]


def test_prereg_frozen_and_bound():
    pr = json.load(open(os.path.join(ART, "prereg.json"), encoding="utf-8"))
    batch = json.load(open(os.path.join(ART, "batch60.json"), encoding="utf-8"))
    assert pr["batch"]["digest"] == batch["digest"]
    assert list(pr["metrics"]) == M.METRIC_KEYS  # 五指标冻结，顺序一致
    assert len(pr["metrics"]) == 5
    for k in ("accuracy_non_inferiority_pp", "evidence_non_inferiority_pp",
              "throughput_advantage_min", "cost_advantage_max_ratio",
              "min_pass_rate_per_arm", "human_sample_min", "kappa_min_acceptable"):
        assert k in pr["thresholds"]
    assert pr["thresholds"]["human_sample_min"] >= 30
    assert len(pr["stopping_rules"]) >= 3
    assert set(pr["missing_data_rules"]) >= {"MO1", "MO2", "MO3"}
    # prereg_id 对内容敏感（改一个阈值即变）
    saved = P.METRICS["M1_unit_cost"]["definition"]
    try:
        base = P.build(ART)["prereg_id"]
        P.METRICS["M1_unit_cost"]["definition"] = saved + " "
        assert P.build(ART)["prereg_id"] != base
    finally:
        P.METRICS["M1_unit_cost"]["definition"] = saved


def _corpus(tmp_path, text="line1\nalpha beta\ngamma delta\nline4\n"):
    root = tmp_path / "corpus" / "Repo"
    root.mkdir(parents=True)
    f = root / "doc.md"
    f.write_text(text, encoding="utf-8")
    return str(tmp_path / "corpus"), "Repo/doc.md", hashlib.sha256(f.read_bytes()).hexdigest()


def _ko(rel, sha, quote="alpha beta", lines=(2, 2), ko_id="ko-1"):
    return {"id": ko_id, "ko_type": "simulation",
            "claim": {"statement": "s", "claim_form": "reported"},
            "evidence": [{"path": rel, "lines": list(lines), "quote": quote, "sha256": sha}],
            "conditions": {"stated_in_source": False, "scope": "not-stated-in-source", "text": None},
            "quality": {}, "provenance": {},
            "source": {"doc_id": "doc:x", "repo": "Repo", "path": rel, "sha256": sha}}


def test_gate_rejects_bad_evidence(tmp_path):
    corpus, rel, sha = _corpus(tmp_path)
    objs = tmp_path / "objects.jsonl"
    # 1) 正常
    objs.write_text(json.dumps(_ko(rel, sha)) + "\n", encoding="utf-8")
    ok = G.gate(BATCH, "A", "rci-f1-A-A01", str(objs), corpus)
    assert ok["evidence_gate"]["passed"] and ok["locators_resolved"] == 1
    # 2) sha 不符
    objs.write_text(json.dumps(_ko(rel, "0" * 64)) + "\n", encoding="utf-8")
    bad = G.gate(BATCH, "A", "rci-f1-A-A01", str(objs), corpus)
    assert bad["evidence_gate"]["passed"] is False and bad["locators_resolved"] == 0
    # 3) 引文不在行窗口
    objs.write_text(json.dumps(_ko(rel, sha, quote="NOT-THERE")) + "\n", encoding="utf-8")
    bad2 = G.gate(BATCH, "A", "rci-f1-A-A01", str(objs), corpus)
    assert bad2["locators_resolved"] == 0 and bad2["claims_with_locator"] == 0
    # 4) 行区间越界
    objs.write_text(json.dumps(_ko(rel, sha, lines=(99, 120))) + "\n", encoding="utf-8")
    bad3 = G.gate(BATCH, "A", "rci-f1-A-A01", str(objs), corpus)
    assert bad3["locators_resolved"] == 0
    # 5) 结构门：缺字段 + 重复 id
    objs.write_text(json.dumps({"id": "ko-1"}) + "\n", encoding="utf-8")
    bad4 = G.gate(BATCH, "A", "rci-f1-A-A01", str(objs), corpus)
    assert bad4["structure_gate"]["passed"] is False


def test_blind_blinding_and_sealing(tmp_path):
    corpus, rel, sha = _corpus(tmp_path)
    d = tmp_path / "art"
    d.mkdir()
    shutil.copy(os.path.join(ART, "batch60.json"), d / "batch60.json")
    objs = d / "objects"
    for lane, ko_id in (("A", "ko-a1"), ("B", "ko-b1"), ("C", "ko-c1")):
        (objs / lane).mkdir(parents=True)
        row = _ko(rel, sha, ko_id=ko_id)
        row["_lane"] = lane
        (objs / lane / f"pkg{lane}.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
    info = BL.prepare(str(d), str(objs), None)
    pack = json.load(open(d / "blind" / "pack.json", encoding="utf-8"))
    key = json.load(open(d / "blind" / "blind_key.json", encoding="utf-8"))["key"]
    assert info["n_items"] == 3 and len(key) == 3
    # 去标识：包里不得出现 lane 字段/字样，也不能出现包名
    for it in pack["items"]:
        assert "lane" not in json.dumps(it, ensure_ascii=False).lower()
        assert "pkga" not in json.dumps(it, ensure_ascii=False).lower()
    # sample_id 确定性
    assert BL.sample_id_for("ko-a1") == BL.sample_id_for("ko-a1") != BL.sample_id_for("ko-b1")
    # 封存映射 sha256 可复算
    blob = json.dumps({"seed": BL.SEED, "key": key}, ensure_ascii=False,
                      sort_keys=True).encode()
    assert hashlib.sha256(blob).hexdigest() == info["key_sha256"]
    # 人工表
    h = BL.human30(str(d), 3)
    assert h["n"] == 3
    sheet = json.load(open(d / "blind" / "human30.json", encoding="utf-8"))
    assert {i["sample_id"] for i in sheet["items"]} <= set(key)


def test_blind_ingest_validation(tmp_path):
    d = tmp_path / "art"
    (d / "blind").mkdir(parents=True)
    json.dump({"seed": BL.SEED, "n_items": 1,
               "items": [{"sample_id": "bs-1", "order": 1}]},
              open(d / "blind" / "pack.json", "w"))
    good = tmp_path / "good.json"
    json.dump({"items": [{"sample_id": "bs-1", "claim_faithful": 1,
                          "locator_resolvable": 1, "conditions_not_invented": 0,
                          "type_fit": 1}]}, open(good, "w"))
    res = BL.ingest(str(d), str(good), "synthetic")
    assert res["total_scored"] == 1
    bad = tmp_path / "bad.json"
    json.dump({"items": [{"sample_id": "bs-unknown", "claim_faithful": 1}]}, open(bad, "w"))
    with pytest.raises(ValueError):
        BL.ingest(str(d), str(bad))
    bad2 = tmp_path / "bad2.json"
    json.dump({"items": [{"sample_id": "bs-1", "claim_faithful": 7}]}, open(bad2, "w"))
    with pytest.raises(ValueError):
        BL.ingest(str(d), str(bad2))


# ---------- 指标算术（SYNTHETIC 夹具：只验公式，不作实验证据） ----------
def _run(arm, pid, docs, passed, tokens, compute, wall, agents,
         claims, claims_loc, loc_total, loc_ok):
    return {"arm": arm, "package_id": pid, "doc_ids": [], "agent_count": agents,
            "docs_completed": docs, "docs_passed": passed, "claims": claims,
            "claims_with_locator": claims_loc, "locators_total": loc_total,
            "locators_resolved": loc_ok,
            "cost": {"tokens": tokens, "compute_core_seconds": compute, "wall_seconds": wall}}


def test_metrics_arithmetic_synthetic(tmp_path):
    batch = {"n": 6, "digest": "synthetic"}
    runs = {"A": [_run("A", "A1", 6, 6, 6000, 600, 360, 1, 6, 6, 12, 12)],
            "B": [_run("B", "B1", 6, 5, 3000, 300, 180, 20, 6, 5, 12, 10)],
            "C": []}
    blind = tmp_path / "blind"
    blind.mkdir()
    # 30 条人工复核（合成，标签有方差以便 κ 可算；人工与盲审基本一致 → 高 κ）
    items, key = [], {}
    for i in range(30):
        lane = "A" if i % 2 == 0 else "B"
        sid = f"s{i}"
        vals = {"claim_faithful": 1 if i % 3 else 0,
                "locator_resolvable": 1 if i % 4 else 0,
                "conditions_not_invented": 0 if i % 5 else 1,
                "type_fit": 1 if i % 6 else 0}
        row = {"sample_id": sid, **vals}
        for f, v in vals.items():  # 人工与盲审一致率 28/30
            row["human_" + f] = v if i not in (3, 17) else 1 - v
        items.append(row)
        key[sid] = {"lane": lane, "ko_id": f"ko{i}"}
    json.dump({"items": items}, open(blind / "scored.json", "w"))
    json.dump({"key": key}, open(blind / "blind_key.json", "w"))
    exp_a = [sum(it[f] for f in M.FIELDS) for it in items if key[it["sample_id"]]["lane"] == "A"]
    m = M.compute(batch, runs, str(blind))
    a, b, c = m["arms"]["A"], m["arms"]["B"], m["arms"]["C"]
    # M1: A tokens/doc=1000 → 1000/1000=1；compute/doc=100 → /60；agent_hours=360/3600*1/6
    u = 1.0 + round(100 / 60, 4) + round(360 / 3600 * 1 / 6, 4)
    assert a["metrics"]["M1_unit_cost"]["value"] == pytest.approx(u, rel=1e-3)
    # M2: A 6 docs / 0.1h = 60 docs/h
    assert a["metrics"]["M2_throughput"]["value"] == pytest.approx(60.0, rel=1e-6)
    # M4: A lsr=1 cov=1 → 1.0；B lsr=10/12 cov=5/6
    assert a["metrics"]["M4_evidence_completeness"]["value"] == 1.0
    assert b["metrics"]["M4_evidence_completeness"]["value"] == pytest.approx(10 / 12 * 5 / 6, abs=1e-4)
    # M3: 由夹具独立复算 A 的字段通过率
    assert a["metrics"]["M3_extraction_accuracy"]["value"] == pytest.approx(
        sum(exp_a) / (len(exp_a) * 4), abs=1e-6)
    # C 未启动 → 全部 NOT_STARTED，判定 WITHHELD
    assert c["metrics"]["M1_unit_cost"]["status"] == "NOT_STARTED"
    assert m["verdict"]["verdict"] == "WITHHELD"


def test_metrics_m3_withheld_when_human_insufficient(tmp_path):
    batch = {"n": 2, "digest": "synthetic"}
    runs = {"A": [_run("A", "A1", 2, 2, 1000, 100, 60, 1, 2, 2, 4, 4)], "B": [], "C": []}
    blind = tmp_path / "blind"
    blind.mkdir()
    items = [{"sample_id": "s0", "claim_faithful": 1, "locator_resolvable": 1,
              "conditions_not_invented": 1, "type_fit": 1, "human_claim_faithful": 1}]
    json.dump({"items": items}, open(blind / "scored.json", "w"))
    json.dump({"key": {"s0": {"lane": "A", "ko_id": "k"}}}, open(blind / "blind_key.json", "w"))
    m = M.compute(batch, runs, str(blind))
    assert m["arms"]["A"]["metrics"]["M3_extraction_accuracy"]["status"] == "WITHHELD"
    assert m["blind"]["human_enough"] is False


def test_kappa_and_judge_branches():
    assert M.cohen_kappa([1, 1, 0, 0], [1, 1, 0, 0]) == 1.0
    assert M.cohen_kappa([1, 0], [1, 0]) in (1.0, None)
    full = {"blind": {"kappa_ok": True, "human_enough": True},
            "arms": {ar: {"metrics": {k: {"status": "REAL", "value": v}
                                     for k, v in zip(M.METRIC_KEYS, vals)}}
                     for ar, vals in {"A": (10, 1, 0.9, 0.9, 1),
                                      "B": (12, 6, 0.85, 0.82, 1),
                                      "C": (14, 6, 0.88, 0.89, 1)}.items()}}
    j = M.judge(full)
    assert j["hypotheses"] == {"H1_quality_non_inferior": True, "H2_throughput_3x": True,
                               "H3_cost_not_worse": False}
    assert j["verdict"] == "CONDITIONAL"
    full["arms"]["C"]["metrics"]["M3_extraction_accuracy"]["value"] = 0.5
    assert M.judge(full)["verdict"] == "NOT_SCALABLE"