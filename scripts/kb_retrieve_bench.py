#!/usr/bin/env python3
"""kb_retrieve_bench —— KB 读路径基准（ref vs got，m15255 / KBM-CONSUME-W1 ③④）

问题：现网 `knowledge_base` 没有可用的读面，最接近「检索」的行为是注入器的通用词重叠
（`knowledge_injections.match_terms` 那套：空白分词、全库不过滤、命中词数排序）。
本轮把读路径实做成 `ke/consume.py`，就必须回答：**它真的比旧行为强吗？强多少？**

对照（题集 prereg 冻结在 benchmarks/kb_retrieval_gold_v1.json，sha256 入 bench.json）：
  ref       = ke.consume.naive_overlap   旧行为：空白分词 + 全库无过滤 + 命中词数
  got       = ke.consume.rank            新读路径：中文 bigram + 三面加权 + 域过滤
  got_domain= rank + 调用方已知 domain（只对题面自带仓名的题，单独报，不混进主指标）

指标：precision@1 / recall@5 / MRR@5（阈值 prereg 写定，未达标 = honest FAIL）
负例题（n02 组）只做诊断观测，不设阈值 —— 词面检索的假阳性是已知局限。

用法：
  python3 scripts/kb_retrieve_bench.py                       # 现网 PG（psycopg:///tensorplatform）
  python3 scripts/kb_retrieve_bench.py --cards <snapshot>    # 离线复算（用落盘卡快照）
产出：artifacts/kb_retrieval/{cards_snapshot.json,bench.json,bench.md}
退出码：0=全部指标达标；1=有指标未达标（honest FAIL，工件仍写全）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from ke import consume as C  # noqa: E402

DEFAULT_DSN = os.environ.get("KB_PG_DSN", "postgresql:///tensorplatform")
GOLD = ROOT / "benchmarks" / "kb_retrieval_gold_v1.json"


def load_cards(dsn: str):
    """直连 DSN 取卡；被拒（现网 agent 角色无 GRANT）时显式降到 psql 兜底并记录原因。"""
    try:
        conn = C.connect(dsn)
        try:
            return C.fetch_cards(conn, status="active"), "pg-direct", None
        finally:
            conn.close()
    except Exception as e:
        err = f"{type(e).__name__}: {e}"[:200]
        return C.fetch_cards_psql(), "psql-fallback", err


def topk(arm: str, q: str, cards, domain=None, limit=5):
    if arm == "ref":
        return C.naive_overlap(q, cards, limit=limit)
    return C.rank(q, cards, domain=domain, limit=limit)


def evaluate(queries, cards, arm: str):
    p1 = r5 = rr = 0.0
    rows = []
    for item in queries:
        gold = set(item["gold"])
        hits = topk(arm, item["q"], cards, domain=item.get("domain"))
        keys = [h["kb_key"] for h in hits]
        hit1 = bool(keys) and keys[0] in gold
        rec = len(gold & set(keys[:5])) / len(gold) if gold else 0.0
        rank_pos = next((i + 1 for i, k in enumerate(keys) if k in gold), None)
        p1 += hit1
        r5 += rec
        rr += 1.0 / rank_pos if rank_pos else 0.0
        rows.append({"id": item["id"], "q": item["q"], "gold": sorted(gold), "domain": item.get("domain"),
                     "top1": keys[0] if keys else None, "top1_score": hits[0]["score"] if hits else None,
                     "gold_rank": rank_pos, "hit1": hit1, "recall5": round(rec, 3),
                     "miss_reason": None if hit1 else ("no_result" if not keys else "wrong_card")})
    n = max(len(queries), 1)
    return {"n": len(queries), "precision_at_1": round(p1 / n, 4), "recall_at_5": round(r5 / n, 4),
            "mrr_at_5": round(rr / n, 4), "rows": rows}


def evaluate_negatives(negs, cards, arm: str):
    out = []
    for item in negs:
        hits = topk(arm, item["q"], cards, limit=3)
        out.append({"id": item["id"], "q": item["q"],
                    "returned": [{"kb_key": h["kb_key"], "score": h["score"]} for h in hits]})
    return out


def md_table(bench: dict) -> str:
    t = bench["thresholds"]
    lines = ["| 指标 | ref（旧行为） | got（ke.consume.rank） | Δ | 阈值 | 判定 |", "|---|---|---|---|---|---|"]
    for k in ("precision_at_1", "recall_at_5", "mrr_at_5"):
        r, g, th = bench["ref"][k], bench["got"][k], t[k]
        verdict = "PASS" if g >= th else "**FAIL**"
        lines.append(f"| {k} | {r} | {g} | {round(g - r, 4):+} | ≥{th} | {verdict} |")
    lines.append(f"\n题集 n={bench['got']['n']}；prereg sha256=`{bench['prereg_sha256']}`；"
                 f"cards n={bench['cards_n']}（snapshot sha256 `{bench['cards_sha256']}`）")
    lines.append("\n| 题 | 题面 | gold 卡 | ref top1 | got top1 | got rank |")
    lines.append("|---|---|---|---|---|---|")
    ref_rows = {r["id"]: r for r in bench["ref"]["rows"]}
    for r in bench["got"]["rows"]:
        rr = ref_rows.get(r["id"], {})
        lines.append(f"| {r['id']} | {r['q'][:34]} | `{(r['gold'] or [''])[0]}` | "
                     f"{'✓' if rr.get('hit1') else '✗'} | {'✓' if r.get('hit1') else '✗'} | "
                     f"{r.get('gold_rank')} |")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=str(GOLD))
    ap.add_argument("--cards", default=None, help="卡快照 JSON（离线复算用）")
    ap.add_argument("--dsn", default=DEFAULT_DSN)
    ap.add_argument("--out", default="artifacts/kb_retrieval")
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    gold_raw = pathlib.Path(a.gold).read_bytes()
    prereg = json.loads(gold_raw)
    prereg_sha = hashlib.sha256(gold_raw).hexdigest()

    cards_source, dsn_error = "snapshot", None
    if a.cards:
        cards = json.loads(pathlib.Path(a.cards).read_text())["cards"]
    else:
        cards, cards_source, dsn_error = load_cards(a.dsn)
        snap = json.dumps({"cards": cards}, ensure_ascii=False, sort_keys=True, indent=1)
        (out / "cards_snapshot.json").write_text(snap)
    cards_sha = hashlib.sha256(json.dumps(cards, ensure_ascii=False, sort_keys=True).encode()).hexdigest()

    ref = evaluate(prereg["queries"], cards, "ref")
    got = evaluate(prereg["queries"], cards, "got")
    dom_q = [q for q in prereg["queries"] if q.get("domain")]
    got_dom = evaluate(dom_q, cards, "got") if dom_q else {"n": 0, "rows": [],
                                                          "precision_at_1": None,
                                                          "recall_at_5": None, "mrr_at_5": None}
    negatives = {"ref": evaluate_negatives(prereg["negatives"], cards, "ref"),
                 "got": evaluate_negatives(prereg["negatives"], cards, "got")}

    th = prereg["thresholds"]
    verdicts = {k: ("PASS" if got[k] >= th[k] else "FAIL") for k in
                ("precision_at_1", "recall_at_5", "mrr_at_5")}
    bench = {"schema": "kb-retrieval-bench/1", "prereg_sha256": prereg_sha,
             "cards_n": len(cards), "cards_sha256": cards_sha,
             "dsn": None if a.cards else a.dsn, "cards_source": cards_source,
             "dsn_error": dsn_error, "thresholds": th, "verdicts": verdicts,
             "verdict": "PASS" if all(v == "PASS" for v in verdicts.values()) else "FAIL",
             "ref": ref, "got": got, "got_domain": got_dom, "negatives": negatives}
    (out / "bench.json").write_text(json.dumps(bench, ensure_ascii=False, indent=1))
    table = md_table(bench)
    (out / "bench.md").write_text(f"# KB 读路径基准（{bench['verdict']}）\n\n{table}\n")
    print(table)
    print("\nnegatives(ref/got):",
          json.dumps({k: [x["returned"][:1] for x in v] for k, v in negatives.items()},
                     ensure_ascii=False))
    return 0 if bench["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())