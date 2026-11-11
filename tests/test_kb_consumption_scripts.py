"""脚本级单测：A/B 判分器 + 检索基准的指标/判定逻辑（离线，无 LLM/无 DB）。

为什么这条测试重要（负账教训）：m15181 交付的三个脚本**没有任何 pytest 覆盖**，
达标复核只能跑脚本当证据；脚本一改，判分口径就可能悄悄漂移。这里把「判分口径」
和「阈值判定」钉成断言。
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

CARDS = [
    {"kb_key": "KB-DEMO-A", "ktype": "fact", "domain": "demo-a",
     "title": "平板摩擦系数公式", "content": "0.075/(log10 Re-2)^2", "status": "active"},
    {"kb_key": "KB-DEMO-B", "ktype": "pattern", "domain": "demo-b",
     "title": "递交集群作业", "content": "长任务不要压控制面。", "status": "active"},
]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, REPO / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ A/B 判分器

def test_grade_k1_accepts_truth_and_rejects_noise():
    ab = _load("kb_ab", "scripts/kb_ab_experiment.py")
    good = ab.grade_k1("Re=1e8: 0.002083; Re=1e9: 0.001531")
    assert good["pass"] is True
    assert good["detail"] == {"re1e8": True, "re1e9": True}
    assert ab.grade_k1("Re=1e8: 0.0025; Re=1e9: 0.0012")["pass"] is False
    assert ab.grade_k1("不知道")["pass"] is False


def test_grade_k2_requires_all_three_elements():
    ab = _load("kb_ab", "scripts/kb_ab_experiment.py")
    ok = ab.grade_k2("1) 递交集群 job（cj123）；2) 不在 99 控制面压重算；3) loong64 与 x86 分架构判读")
    assert ok["pass"] is True
    partial = ab.grade_k2("1) 递交集群 job；2) 本地跑；3) loong64 与 x86")
    assert partial["pass"] is False and partial["detail"]["not_on_99"] is False


def test_grade_k3_needs_both_numbers():
    ab = _load("kb_ab", "scripts/kb_ab_experiment.py")
    assert ab.grade_k3('{"convergence_rate": 0.07, "force_err_pct": 32.3, "level": 2}')["pass"] is True
    assert ab.grade_k3('{"convergence_rate": 0.07, "force_err_pct": 40.0}')["pass"] is False


def test_render_cards_verbatim_and_digest_truncates():
    ab = _load("kb_ab", "scripts/kb_ab_experiment.py")
    rows = {c["kb_key"]: c for c in CARDS}
    full = ab.render_cards(rows, ["KB-DEMO-A", "KB-DEMO-MISSING"])
    assert "[KB-DEMO-A] (fact/demo-a)" in full and CARDS[0]["content"] in full
    assert "KB-DEMO-MISSING" not in full
    short = ab.digest(rows, ["KB-DEMO-A"], n=5)
    assert CARDS[0]["content"][:5] in short and CARDS[0]["content"] not in short
    assert short.endswith("…")


# ------------------------------------------------------------------ 基准脚本

def test_bench_evaluate_metrics_and_miss_reasons():
    bench = _load("kb_bench", "scripts/kb_retrieve_bench.py")
    queries = [{"id": "t1", "q": "平板摩擦系数", "gold": ["KB-DEMO-A"]},
               {"id": "t2", "q": "zzz 完全不存在", "gold": ["KB-DEMO-B"]}]
    got = bench.evaluate(queries, CARDS, "got")
    assert got["n"] == 2
    assert got["precision_at_1"] == 0.5
    assert got["rows"][0]["hit1"] is True and got["rows"][0]["gold_rank"] == 1
    assert got["rows"][1]["miss_reason"] == "no_result"
    # ref 语义锁死：按空白分词后做**子串**匹配。空格分开的词能中，连写整句（词序不同）中不了。
    ref = bench.evaluate([{"id": "r1", "q": "平板 摩擦 系数", "gold": ["KB-DEMO-A"]},
                          {"id": "r2", "q": "摩擦系数平板", "gold": ["KB-DEMO-A"]}], CARDS, "ref")
    assert ref["rows"][0]["hit1"] is True          # "平板"/"摩擦"/"系数" 都是 title 子串
    assert ref["rows"][1]["hit1"] is False         # 整句连写不是任何字段的子串 → 零命中
    assert ref["precision_at_1"] == 0.5


def test_bench_verdict_is_threshold_driven_not_self_declared():
    bench = _load("kb_bench", "scripts/kb_retrieve_bench.py")
    b = {"thresholds": {"precision_at_1": 0.8, "recall_at_5": 0.9, "mrr_at_5": 0.7},
         "prereg_sha256": "deadbeef", "cards_n": 2, "cards_sha256": "cafe",
         "ref": {"precision_at_1": 0.65, "recall_at_5": 0.7, "mrr_at_5": 0.675, "n": 20, "rows": []},
         "got": {"precision_at_1": 0.85, "recall_at_5": 0.9, "mrr_at_5": 0.86, "n": 20,
                 "rows": [{"id": "t1", "q": "q", "gold": ["KB-DEMO-A"], "hit1": True, "gold_rank": 1}]}}
    table = bench.md_table(b)
    assert "PASS" in table and "85.0" not in table
    b["got"]["precision_at_1"] = 0.75
    assert "**FAIL**" in bench.md_table(b)


def test_bench_prereg_files_are_frozen_and_wellformed():
    for name in ("kb_retrieval_gold_v1.json", "kb_retrieval_holdout_v1.json"):
        g = json.loads((REPO / "benchmarks" / name).read_text())
        assert g["schema"] == "kb-retrieval-gold/1"
        assert g["queries"] and all(q["gold"] for q in g["queries"])
        thr = g["thresholds"]
        assert 0 < thr["precision_at_1"] <= 1 and 0 < thr["recall_at_5"] <= 1
        ids = [q["id"] for q in g["queries"]]
        assert len(ids) == len(set(ids))