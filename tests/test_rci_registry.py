"""RCI-S1 registry (``ke.rci_registry``) — unit, end-to-end and artifact tests.

Three layers, so "the registry is correct" is not just "the script ran":

1. **unit** — fingerprints, the typing cascade, the per-report feature record;
2. **end-to-end** — a synthetic 6-report corpus driven through
   shard -> merge -> aggregate -> verify, including a tamper test that proves
   the verifier actually fails when the ledger and the summary disagree;
3. **artifact** — the frozen 9446-report snapshot (``KBM-RCI-S1-REGISTRY``):
   partitions sum to the row count, every aggregate is recomputable from the
   row-level ledger, the two independent implementations (pure-Python vs. the
   SQL recomputation) agree, the gate sweep is monotone, and the registry doc
   quotes live numbers (no hand-copied values, no dead figure links).
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ke import rci_registry as rr  # noqa: E402

ART = os.path.join(ROOT, "audit", "refs", "rci-s1-registry", "out")
DOC = os.path.join(ROOT, "docs", "rci-s1-registry.md")
FIGDIR = os.path.join(ROOT, "docs", "figures", "rci-s1")
SNAP = "m15810@2026-11-11T20:00:31Z"
TYPES = ("info", "research", "analysis", "creative")


# ---------------------------------------------------------------- fixtures

def _artifact(name):
    p = os.path.join(ART, name)
    if not os.path.exists(p):
        pytest.skip(f"frozen registry artifact not present: {p}")
    if name.endswith(".gz"):
        return rr.read_rows(p)
    return json.load(open(p, encoding="utf-8"))


@pytest.fixture(scope="module")
def rows():
    return _artifact("registry_rows.jsonl.gz")


@pytest.fixture(scope="module")
def summary():
    return _artifact("summary.json")


@pytest.fixture(scope="module")
def sensitivity():
    return _artifact("sensitivity.json")


@pytest.fixture(scope="module")
def extras():
    return _artifact("db_extras.json")


# ------------------------------------------------------- 1. unit: fingerprints

BODY = "阻力系数 0.5 与试验结果对照，重复段落用于构造重复簇。" * 8


def test_identical_bodies_have_identical_fingerprints():
    a, b = rr.nfc(BODY), rr.nfc(BODY)
    assert rr.sha256_bytes(a.encode()) == rr.sha256_bytes(b.encode())
    assert rr.gram_hashes(a) == rr.gram_hashes(b)
    assert rr.minhash_sig(rr.gram_hashes(a)) == rr.minhash_sig(rr.gram_hashes(b))


def test_disjoint_bodies_have_disjoint_minhash():
    x = rr.minhash_sig(rr.gram_hashes("alpha beta gamma delta 1 2 3"))
    y = rr.minhash_sig(rr.gram_hashes("完全不同的中文正文 阻力 推进 耐波 操纵 稳性"))
    same = sum(1 for p, q in zip(x, y) if p == q)
    assert same <= 8, f"MinHash-128 agrees on {same}/128 positions for disjoint sets"


def test_number_masked_skeleton_links_rephrased_copies():
    a = "解析解 0.7 与 0.9 对齐"
    b = "解析解 0.8 与 0.9 对齐"
    skel = lambda s: rr.sha256_bytes(rr.MASK_RE.sub("#", s).encode())  # noqa: E731
    assert skel(a) == skel(b), "number-masked skeleton must ignore numeric edits"
    assert rr.sha256_bytes(a.encode()) != rr.sha256_bytes(b.encode())


def test_tail_window_is_a_documented_blind_spot():
    """The 50k-char tail window is a stated limitation: heads are not compared."""
    filler = "丙" * (rr.MD_WINDOW + 10)
    head_a = "甲" * 200 + filler + BODY
    head_b = "乙" * 200 + filler + BODY
    assert rr.gram_hashes(head_a) == rr.gram_hashes(head_b)


# ------------------------------------------------------------ 2. unit: typing

@pytest.mark.parametrize("title,goal,md,clean_code,has_table,n_numbers,want", [
    ("新增阻力模块", "", "", "", False, 0, ("creative", "R1_title_creative")),
    ("模型校核报告", "", "", "", False, 0, ("research", "R2_title_research")),
    ("资产盘点", "", "", "", False, 0, ("analysis", "R3_title_analysis")),
    ("状态进展记录", "", "", "", False, 0, ("info", "R4_title_info")),
    ("case", "开发新模块", "", "", False, 0, ("creative", "R5_goal_creative")),
    ("case", "验证收敛", "", "", False, 0, ("research", "R6_goal_research")),
    ("case", "审计复算", "", "", False, 0, ("analysis", "R7_goal_analysis")),
    ("case", "补报纪要", "", "", False, 0, ("info", "R8_goal_info")),
    ("case", "", "与解析解对照", "", False, 0, ("research", "R9_bench_ref")),
    ("case", "", "|a|b|\n|1|2|\n|3|4|\n|5|6|\n|7|8|\n|9|0|\n|1|2|", "", True, 4,
     ("analysis", "R10_table_numbers")),
    ("case", "", "只有数字 41", "", False, 1, ("analysis", "R11_numbers")),
    ("case", "", "纯文字", "", False, 0, ("info", "R12_fallback")),
])
def test_typing_cascade_rules(title, goal, md, clean_code, has_table, n_numbers, want):
    assert rr.classify(title, goal, md, clean_code, has_table, n_numbers) == want


def test_every_rule_id_is_declared_and_clean_exclusion_wins():
    got = rr.classify("新增模块", "开发", "数字 1", "X06_process_log", True, 1)
    assert got == ("info", "R0_clean_excluded"), "clean hard-exclusion must outrank the cascade"
    assert got[1] in rr.TYPING_RULES
    assert set(rr.TYPING_RULES) >= {"R0_clean_excluded", "R12_fallback"}
    assert len(set(rr.TYPING_RULES)) == len(rr.TYPING_RULES), "rule ids must be unique"


# ------------------------------------------------ 3. end-to-end synthetic corpus

def _report(rid, title, md, mission_id=None, figures=None):
    return {"id": str(rid), "title": title, "markdown": md,
            "mission_id": "" if mission_id is None else str(mission_id),
            "scenario_key": f"k{rid}", "tags": json.dumps(["t"]),
            "figures": json.dumps(figures or []),
            "created_at": "2026-11-01 00:00:00+00"}


MISSIONS = {
    102: {"id": "102", "goal": "", "repo": "TensorLBM", "status": "succeeded",
          "model": "m", "claimed_by": "a", "created_at": "", "finished_at": "",
          "result": json.dumps({"cf": 0.5})},
    103: {"id": "103", "goal": "", "repo": "TensorFEM", "status": "succeeded",
          "model": "m", "claimed_by": "b", "created_at": "", "finished_at": "",
          "result": json.dumps({"cf": 0.5})},
    105: {"id": "105", "goal": "", "repo": "TensorBEM", "status": "failed",
          "model": "m", "claimed_by": "c", "created_at": "", "finished_at": "",
          "result": ""},
    106: {"id": "106", "goal": "", "repo": "TensorBEM", "status": "succeeded",
          "model": "m", "claimed_by": "c", "created_at": "", "finished_at": "",
          "result": json.dumps({"x": 0.7})},
}
LEDGER = {4: {"key": "report:4", "decision": "repaired",
              "repairs": ["p1", "p2"], "reason": None}}
TRIPLE = {"102": {"wt_exists": True, "wt_artifacts": True, "wt_repro": False,
                  "triple_ok": False}}


def corpus():
    return [
        _report(1, "新增阻力模块A", BODY, 102),
        _report(2, "新增阻力模块A", BODY, 102),                     # exact duplicate
        _report(3, "资产盘点", "阻力系数 0.5 复核 1.5 与 2.5", 103),
        _report(4, "状态进展记录", "无数字的一段说明文字"),           # no numbers
        _report(5, "case-alpha", "解析解 0.7 与 0.9 对齐", 105),
        _report(6, "case-beta", "解析解 0.8 与 0.9 对齐", 106),      # skeleton dup
    ]


@pytest.fixture(scope="module")
def e2e():
    reports = corpus()
    feats = rr.shard_features(reports, MISSIONS, LEDGER, TRIPLE, shard=0, n=1)
    rows = rr.merge_features(feats, snapshot="synthetic@t0")
    return feats, rows, rr.aggregate(rows)


def test_feature_record_flags_are_typed(e2e):
    feats, _, _ = e2e
    by_id = {f["id"]: f for f in feats}
    assert by_id[1]["real_exec_flag"] == "verified"          # 0.5 in result
    assert by_id[1]["real_exec_overlap"] == pytest.approx(1.0)
    assert by_id[3]["real_exec_flag"] == "partial"           # 1 of 3 numbers
    assert by_id[4]["real_exec_flag"] == "no_mission"
    assert by_id[5]["real_exec_flag"] == "no_result"
    assert by_id[6]["real_exec_flag"] == "zero_overlap"
    assert by_id[4]["failed_empty_codes"] == ["no_numbers", "no_artifact"]
    assert by_id[1]["triple_ok"] is False and by_id[1]["wt_exists"] is True
    assert by_id[4]["clean_decision"] == "repaired"
    for f in feats:
        assert f["type_rule"] in rr.TYPING_RULES
        assert f["asset_type"] in rr.ASSET_TYPES


def test_merge_partitions_and_clusters(e2e):
    _, rows, s = e2e
    assert len(rows) == s["rows"] == 6
    assert sum(s["by_type"].values()) == 6
    assert sum(s["by_clean"].values()) == 6
    assert sum(s["by_real_exec"].values()) == 6
    assert sum(s["by_type_rule"].values()) == 6
    assert "R12_fallback" not in s["by_type_rule"], "synthetic corpus matches a rule"
    assert s["by_type"] == {"creative": 2, "analysis": 1, "info": 1, "research": 2}

    assert s["dup_clusters"] == 2
    assert s["dup_reports_in_clusters"] == 4
    assert s["dup_excess_reports"] == 2
    by_rid = {r["report_id"]: r for r in rows}
    assert by_rid[1]["dup_cluster_id"] == by_rid[2]["dup_cluster_id"] == 1
    assert {"exact", "title", "skeleton"} <= set(by_rid[1]["dup_kind"].split(","))
    assert by_rid[5]["dup_cluster_id"] == by_rid[6]["dup_cluster_id"] == 5
    assert "skeleton" in by_rid[5]["dup_kind"]
    assert by_rid[3]["dup_cluster_id"] is None and by_rid[3]["dup_cluster_size"] == 1
    assert {r["snapshot_id"] for r in rows} == {"synthetic@t0"}


def test_quality_dimensions_are_explicit(e2e):
    _, rows, s = e2e
    by_rid = {r["report_id"]: r for r in rows}
    assert s["q_dims_pending"] == ["q_accuracy", "q_freshness", "q_reusability"]
    assert by_rid[4]["q_consistency"] == 0.5, "two repairs -> consistency penalty"
    assert by_rid[3]["q_consistency"] == 1.0
    # mission yes, worktree-triple no, clean ledger "not_in_w1" -> 1/3
    assert by_rid[1]["q_traceability"] == round(1 / 3, 3), "quality dims are rounded to 3dp"


def test_verify_accepts_consistent_and_rejects_tampered(e2e):
    _, rows, s = e2e
    assert rr.summary_mismatches(rows, s) == []
    rr.assert_summary_matches(rows, s)

    tampered = json.loads(json.dumps(s))
    tampered["md_chars_total"] += 1
    bad = rr.summary_mismatches(rows, tampered)
    assert [b[0] for b in bad] == ["md_chars_total"]
    with pytest.raises(AssertionError):
        rr.assert_summary_matches(rows, tampered)


def test_shard_count_does_not_change_the_ledger():
    reports = corpus()
    merged = []
    for n in (1, 3):
        feats = []
        for shard in range(n):
            feats.extend(rr.shard_features(reports, MISSIONS, LEDGER, TRIPLE,
                                           shard=shard, n=n))
        merged.append(rr.aggregate(rr.merge_features(feats, snapshot="synthetic@t0")))
    assert merged[0] == merged[1]


def test_sensitivity_sweep_is_monotone_and_gate_independent_links_hold(e2e):
    feats, _, s = e2e
    sweep = rr.sensitivity(feats, gates=(0.4, 0.5, 0.7))["sweep"]
    clustered = [x["dup_clusters"] for x in sweep]
    assert clustered == sorted(clustered, reverse=True), "looser gate never removes clusters"
    assert sweep[-1]["gate"] == 0.0
    # structural links are gate independent: exact dups survive the strictest gate
    assert sweep[2]["dup_reports"] >= 2


def test_cli_reproduces_the_documented_path(tmp_path):
    """shard -> merge -> verify -> sensitivity, exactly as the doc spells it."""
    data = tmp_path / "data"
    shards = tmp_path / "shards"
    out = tmp_path / "out"
    for d in (data, shards, out):
        d.mkdir()
    cols = ["id", "title", "markdown", "mission_id", "scenario_key", "tags",
            "figures", "created_at"]
    with open(data / "reports.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in corpus():
            w.writerow({k: r[k] for k in cols})
    mcols = ["id", "goal", "repo", "status", "model", "claimed_by", "created_at",
             "finished_at", "result"]
    with open(data / "missions.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=mcols)
        w.writeheader()
        for m in MISSIONS.values():
            w.writerow({k: m.get(k, "") for k in mcols})
    with open(data / "clean_ledger.jsonl", "w", encoding="utf-8") as f:
        for r in LEDGER.values():
            f.write(json.dumps(r) + "\n")
    json.dump(TRIPLE, open(data / "worktree_triple.json", "w", encoding="utf-8"))

    env = dict(os.environ, PYTHONPATH=ROOT)

    def run(*a):
        p = subprocess.run([sys.executable, "-m", "ke.rci_registry", *a], cwd=ROOT,
                           capture_output=True, text=True, env=env)
        assert p.returncode == 0, p.stdout + p.stderr
        return p.stdout

    for shard in range(2):
        run("shard", "--shard", str(shard), "--n", "2", "--data", str(data),
            "--out", str(shards))
    assert len(list(shards.glob("shard_*.jsonl"))) == 2
    run("merge", "--data", str(data), "--shards", str(shards), "--out", str(out),
        "--snapshot", "synthetic@t0")
    assert "VERIFY OK" in run("verify", "--out", str(out))
    run("sensitivity", "--shards", str(shards), "--out", str(out / "sensitivity.json"))
    s = json.load(open(out / "summary.json", encoding="utf-8"))
    assert s["rows"] == 6 and s["snapshot_id"] == "synthetic@t0"
    assert s["shards"] == 2 and s["dup_clusters"] == 2
    assert json.load(open(out / "sensitivity.json", encoding="utf-8"))["n_reports"] == 6


# ------------------------------------------------- 4. artifact-level snapshot

def test_snapshot_is_pinned_and_ids_are_unique(rows, summary):
    assert summary["snapshot_id"] == SNAP
    assert {r["snapshot_id"] for r in rows} == {SNAP}
    assert len(rows) == summary["rows"] == 9446
    assert len({r["report_id"] for r in rows}) == len(rows), "report_id is the PK"


def test_partitions_are_complete_and_typed(rows, summary):
    for key in ("by_type", "by_real_exec", "by_clean", "by_type_rule"):
        assert sum(summary[key].values()) == len(rows), f"{key} must partition the ledger"
    assert "R12_fallback" not in summary["by_type_rule"], "every report matched a rule"
    assert set(summary["by_type"]) <= set(rr.ASSET_TYPES)
    assert set(summary["by_real_exec"]) <= set(rr.REAL_EXEC_FLAGS)


def test_aggregates_recomputable_from_rows(rows, summary):
    bad = rr.summary_mismatches(rows, summary)
    assert bad == [], f"summary disagrees with the ledger: {bad}"


def test_typed_relations_hold_on_the_whole_snapshot(rows):
    for r in rows:
        if r["mission_id"] is None:
            assert r["real_exec_flag"] == "no_mission"
        if r["wt_exists"] is False:
            assert r["triple_ok"] is False, "triple_ok requires the worktree to exist"
        if r["real_exec_overlap"] is not None:
            assert 0.0 <= float(r["real_exec_overlap"]) <= 1.0
        if r["dup_cluster_id"] is not None:
            assert r["dup_cluster_size"] >= 2
        if r["type_rule"] == "R0_clean_excluded":
            assert r["asset_type"] == "info"


def test_two_independent_implementations_agree(rows, summary, extras):
    """Pure-Python aggregate vs. the SQL-side recomputation in db_extras.json."""
    from collections import Counter
    st = Counter(r["mission_status"] or "<none>" for r in rows)
    assert {k: st.get(k, 0) for k in extras["mission_status"]} == extras["mission_status"]
    repo = Counter(r["repo"] or "<none>" for r in rows)
    assert {k: repo.get(k, 0) for k in extras["by_repo"]} == extras["by_repo"]
    dk = Counter(r["dup_kind"] for r in rows if r["dup_kind"])
    assert {k: dk.get(k, 0) for k in extras["dup_kind"]} == extras["dup_kind"]
    tc = Counter((r["asset_type"], r["clean_decision"]) for r in rows)
    assert {(t, c): tc.get((t, c), 0) for t, c, _ in extras["type_x_clean"]} == \
        {(t, c): int(v) for t, c, v in extras["type_x_clean"]}
    ov = [float(r["real_exec_overlap"]) for r in rows if r["real_exec_overlap"] is not None]
    assert f"{sum(ov) / len(ov):.4f}" == extras["overlap_stats"]["mean"]


def test_sensitivity_monotone_in_gate(summary, sensitivity):
    sweep = {round(x["gate"], 3): x for x in sensitivity["sweep"]}
    assert {0.4, 0.5, 0.7, 0.0} <= set(sweep)
    assert sweep[0.4]["dup_clusters"] >= sweep[0.5]["dup_clusters"] >= sweep[0.7]["dup_clusters"]
    assert sweep[0.5]["dup_clusters"] == summary["dup_clusters"]
    assert sweep[0.5]["dup_reports"] == summary["dup_reports_in_clusters"]
    assert sensitivity["params"]["JACCARD_GATE"] == rr.JACCARD_GATE


def test_registry_doc_quotes_live_numbers(summary):
    if not os.path.exists(DOC):
        pytest.skip("registry doc not present")
    text = open(DOC, encoding="utf-8").read()

    def counts(d, order):
        return ", ".join(f"{k}={d[k]}" for k in order if d.get(k))

    assert f"| asset_type | {counts(summary['by_type'], TYPES)} |" in text
    assert f"clusters={summary['dup_clusters']}" in text
    assert f"reports_in_clusters={summary['dup_reports_in_clusters']}" in text
    assert f"excess={summary['dup_excess_reports']}" in text
    assert f"**{summary['rows']}**" in text or f"**{summary['rows']} " in text
    assert f"triple_ok={summary['triple_ok']}" in text
    for name in ("fig1_typing_clean.png", "fig2_real_exec.png", "fig3_duplicates.png",
                 "fig4_traceability_length.png", "fig5_crosscheck_parity.png"):
        assert f"figures/rci-s1/{name}" in text, f"doc must reference {name}"
        assert os.path.exists(os.path.join(FIGDIR, name)), f"missing figure {name}"
    for r in summary["by_type_rule"].values():
        assert str(r) in text