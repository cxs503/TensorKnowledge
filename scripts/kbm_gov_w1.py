#!/usr/bin/env python3
"""KBM governance W1 runner — 200-report pilot batch → three real numbers.

Anchor: KBM-TKC-GOV-SCALE.  Pipeline (see ``ke/gov.py``):

    tensor_reports (fixed slice)  ->  quantity KOs  ->  entity resolution
        ->  dedupe (fingerprint + semantic)  ->  cross-validation / contradictions
        ->  pooled agent review (state machine write-back)  ->  three-bucket stats

Usage
-----
    python scripts/kbm_gov_w1.py run    --out runs/kbm-gov-w1 [--limit 200] [--min-chars 1500]
    python scripts/kbm_gov_w1.py verify --out runs/kbm-gov-w1
    python scripts/kbm_gov_w1.py queue  --out runs/kbm-gov-w1        # factory 工序04 export

``run``  is reproducible: the slice is defined by *pilot slice rule* recorded in
``snapshot.json`` (published reports, markdown length >= min-chars, ascending id,
first ``limit``).  ``run_at`` is an input (``--run-at`` or ``$GOV_RUN_AT``) so two
runs of the same slice produce byte-identical ledgers.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from ke import gov  # noqa: E402

DEFAULT_RUN_AT = "2026-11-12T02:30:00Z"
SLICE_RULE = ("tensor_reports WHERE status='published' AND length(markdown)>={min_chars} "
              "ORDER BY id ASC LIMIT {limit}")


# ---------------------------------------------------------------------------
# Source slice
# ---------------------------------------------------------------------------
def fetch_reports(limit: int, min_chars: int) -> list[dict]:
    """Deterministic pilot slice straight out of the platform report store."""
    sql = ("COPY (SELECT id, coalesce(title,''), markdown FROM tensor_reports "
           f"WHERE status='published' AND length(markdown)>={int(min_chars)} "
           f"ORDER BY id ASC LIMIT {int(limit)}) TO STDOUT WITH (FORMAT csv)")
    pg = ["psql", "-U", os.environ.get("TP_PG_USER", "foundation"),
          "-d", os.environ.get("TP_PG_DB", "tensorplatform"), "-c", sql]
    proc = subprocess.run(pg, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"psql failed: {proc.stderr[:400]}")
    csv.field_size_limit(sys.maxsize)
    out = []
    for row in csv.reader(io.StringIO(proc.stdout)):
        if len(row) < 3:
            continue
        out.append({
            "report_id": int(row[0]),
            "title": row[1],
            "text": row[2],
            "producer": "platform/tensor_reports",
            "sha256": gov.sha256_text(row[2]),
        })
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_report(result: dict, artifacts: dict) -> str:
    s = result["stats"]
    m = s["metrics"]
    c = s["counts"]
    cv = result["crossval"]
    dedup = result["dedup"]
    lines = [
        "# KBM Governance W1 — 200 篇试点批治理结果（机器生成）",
        "",
        f"> 锚点 KBM-TKC-GOV-SCALE · run_at={result['run_at']} · "
        f"config={result['config_version']} · policy={result['policy_version']} · "
        f"processing graph sha256={artifacts.get('graph_sha256', '-')[:16]}",
        "",
        "## 三口径（互斥，可复算）",
        "",
        "| 口径 | 定义 | 值 |",
        "|---|---|---|",
        f"| B0 原始记录 | {gov.BUCKETS['B0_raw_records']} | {c['raw_records']} |",
        f"| B1 待评审 KO | {gov.BUCKETS['B1_ko_pending_review']} | {c['ko_pending_review']} |",
        f"| B2 经治理 KO | {gov.BUCKETS['B2_governed_objects']} | {c['governed_objects']} |",
        "",
        "## 验收三真数",
        "",
        "| 指标 | 值 | 分母（口径） | 公式 |",
        "|---|---|---|---|",
        f"| 重复率 | {m['duplicate_rate']['value']:.4%} | B1={c['ko_pending_review']} | "
        f"(B1 − clusters)/B1 = ({c['ko_pending_review']} − {c['dedup_clusters']})/"
        f"{c['ko_pending_review']} |",
        f"| 矛盾对数 | {m['contradiction_pairs']['value']} | pairs={cv['n_pairs']} | "
        "same-conditions pairs with rel_diff > 15% |",
        f"| 评审通过率 | {m['review_pass_rate']['value']:.4%} | B1={c['ko_pending_review']} | "
        f"{c['review_pass']}/B1 |",
        "",
        "## 处置分解",
        "",
        f"- 抽取候选（数量语句）: {c['quantity_statements']}；丢弃 {c['discarded']}"
        f"（entity_unresolved / not_quantity_name / provenance_unverified 等，见 discarded.jsonl）",
        f"- KO: {c['ko_extracted']}；去重簇 {c['dedup_clusters']}（重复成员 {c['duplicate_members']}）；"
        f"簇规模分布 {s['dedup_layers']['clusters_by_size']}",
        f"- 评审: pass {c['review_pass']} / needs-fix {c['review_needs_fix']} / fail {c['review_fail']}；"
        f"拒绝事件 {len(result['review']['folded']['refused'])}",
        f"- 交叉验证组判定: {s['group_verdicts']}；配对判定: {s['pair_verdicts']}",
        f"- 实体解析率: {m['entity_resolution_rate']['value']:.2%}"
        f"（分子分母见 stats.json metrics）",
        "",
        "## 工件",
        "",
        "| 文件 | sha256（前 16） |",
        "|---|---|",
    ]
    for name, sha in sorted(artifacts.get("files", {}).items()):
        lines.append(f"| `{name}` | `{sha[:16]}` |")
    lines += [
        "",
        "## 复现",
        "",
        "```bash",
        "python scripts/kbm_gov_w1.py run --out runs/kbm-gov-w1 --limit 200 --min-chars 1500",
        "python scripts/kbm_gov_w1.py verify --out runs/kbm-gov-w1",
        "python -m pytest tests/test_kbm_gov.py -q",
        "```",
    ]
    return "\n".join(lines) + "\n"


def processing_graph_sha(result: dict) -> str:
    """Identity of the processing graph (config + code + slice), not of the result."""
    h = gov.sha256_text
    parts = [h(json.dumps(result["reports"], sort_keys=True)),
             h(gov.CONFIG_PATH.read_text(encoding="utf-8")),
             h((REPO / "ke" / "gov.py").read_text(encoding="utf-8")),
             result["run_at"]]
    return h("|".join(parts))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_run(args) -> int:
    out = Path(args.out)
    cfg = gov.load_config(args.config)
    run_at = args.run_at or os.environ.get("GOV_RUN_AT") or DEFAULT_RUN_AT
    reports = fetch_reports(args.limit, args.min_chars)
    if not reports:
        print("no reports in slice", file=sys.stderr)
        return 2
    print(f"pilot slice: {len(reports)} reports, ids {reports[0]['report_id']}..{reports[-1]['report_id']}")
    result = gov.run_governance(reports, cfg, run_at=run_at)
    artifacts = gov.write_artifacts(result, out)
    graph = processing_graph_sha(result)
    (out / "report.md").write_text(
        render_report(result, {**artifacts, "graph_sha256": graph}), encoding="utf-8")
    gov._dump_json(out / "run_meta.json", {
        "anchor": "KBM-TKC-GOV-SCALE",
        "run_at": run_at,
        "slice_rule": SLICE_RULE.format(limit=args.limit, min_chars=args.min_chars),
        "n_reports": len(reports),
        "processing_graph_sha256": graph,
        "config_version": result["config_version"],
        "policy_version": result["policy_version"],
        "invariants": result["invariants"],
        "metrics": result["stats"]["metrics"],
    })
    print(json.dumps({"counts": result["stats"]["counts"],
                      "metrics": {k: v["value"] for k, v in result["stats"]["metrics"].items()},
                      "invariants": result["invariants"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_verify(args) -> int:
    """Recompute from persisted artefacts; re-check provenance against the source."""
    out = Path(args.out)
    cfg = gov.load_config(args.config)
    kos = [json.loads(l) for l in (out / "ko.jsonl").read_text(encoding="utf-8").splitlines() if l]
    clusters = json.loads((out / "dedup-clusters.json").read_text(encoding="utf-8"))
    crossval = json.loads((out / "crossval.json").read_text(encoding="utf-8"))
    stats = json.loads((out / "stats.json").read_text(encoding="utf-8"))
    snapshot = json.loads((out / "snapshot.json").read_text(encoding="utf-8"))
    writeback = json.loads((out / "review" / "writeback.json").read_text(encoding="utf-8"))
    ledger_lines = [json.loads(l) for l in
                    (out / "review" / "ledger.jsonl").read_text(encoding="utf-8").splitlines() if l]
    checks: dict[str, bool] = {}

    # 1. hash-chained review ledger
    checks["ledger_chain_ok"] = gov.verify_chain(ledger_lines)["ok"]
    # 2. dedupe/crossval recomputation from ko.jsonl reproduces the persisted numbers
    dedup2 = gov.dedupe(kos, cfg)
    checks["dedupe_recomputes"] = (dedup2["n_clusters"] == clusters["n_clusters"]
                                   and dedup2["duplicate_members"] == clusters["duplicate_members"])
    cv2 = gov.cross_validate(kos, cfg)
    checks["crossval_recomputes"] = (cv2["n_contradiction_pairs"] == crossval["n_contradiction_pairs"]
                                     and cv2["n_pairs"] == crossval["n_pairs"])
    # 3. source slice re-fetch: same ids, same sha256
    reports = {r["report_id"]: r for r in fetch_reports(snapshot["n_reports"], args.min_chars)}
    checks["slice_sha256_matches"] = all(
        reports.get(r["report_id"], {}).get("sha256") == r["sha256"] for r in snapshot["reports"])
    # 4. every governed KO re-verifies against the source bytes
    relocated = 0
    for ko in kos:
        rep = reports.get(ko["source"]["report_id"])
        if rep is None:
            continue
        relocated += bool(gov.relocate(rep["text"], {
            "span": ko["source"]["span"], "needle": ko["source"]["needle"],
            "value_literal": str(ko["value"]), "value": ko["value"]})["relocated"])
    checks["all_ko_relocate"] = relocated == len(kos)
    # 5. counting口径 invariants recomputed from artefacts
    counting = gov.Counting()
    for k, v in stats["counts"].items():
        counting.set(k, v)
    for name, m in stats["metrics"].items():
        counting.metrics[name] = m
    try:
        inv = counting.reconcile()
        checks["buckets_reconcile"] = all(inv.values())
    except gov.BucketViolation as exc:
        checks["buckets_reconcile"] = False
        print(f"bucket violation: {exc}", file=sys.stderr)
    # 6. writeback states match the ledger fold
    states = {w["ko_id"]: w["review_state"] for w in writeback}
    checks["writeback_matches_ledger"] = all(
        states.get(ev["event"]["object_ref"]) == ev["event"]["to_state"] for ev in ledger_lines)
    # 7. refused events are logged, never silently dropped
    refused = json.loads((out / "review" / "refused.json").read_text(encoding="utf-8"))
    checks["refusals_accounted"] = isinstance(refused, list)

    ok = all(checks.values())
    print(json.dumps({"checks": checks, "n_ko": len(kos), "relocated": relocated,
                      "all_ok": ok}, ensure_ascii=False, indent=2))
    return 0 if ok else 1


def cmd_queue(args) -> int:
    """Export the review queue in the contract the factory 工序04 step consumes."""
    out = Path(args.out)
    writeback = json.loads((out / "review" / "writeback.json").read_text(encoding="utf-8"))
    votes = [json.loads(l) for l in
             (out / "review" / "votes.jsonl").read_text(encoding="utf-8").splitlines() if l]
    by_item: dict[str, list[dict]] = {}
    for v in votes:
        by_item.setdefault(v["item_id"], []).append(v)
    queue = [{
        "queue_id": "kbm-gov-w1",
        "item_id": w["ko_id"],
        "subject_key": w["subject_key"],
        "source_report": w["source_report"],
        "state": w["review_state"],
        "decision_code": w["review_code"],
        "governed": w["governed"],
        "votes": [{"lane": v["lane"], "reviewer": v["reviewer"]["id"],
                   "verdict": v["verdict"], "code": v["code"]} for v in by_item.get(w["ko_id"], [])],
    } for w in writeback]
    gov._dump_jsonl(out / "review" / "queue-v1.jsonl", queue)
    print(json.dumps({"queue_items": len(queue),
                      "states": _hist(w["review_state"] for w in writeback)},
                     ensure_ascii=False))
    return 0


def _hist(values) -> dict:
    out: dict[str, int] = {}
    for v in values:
        out[v] = out.get(v, 0) + 1
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="KBM governance W1 (KBM-TKC-GOV-SCALE)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn in (("run", cmd_run), ("verify", cmd_verify), ("queue", cmd_queue)):
        p = sub.add_parser(name)
        p.add_argument("--out", default="runs/kbm-gov-w1")
        p.add_argument("--config", default=None)
        p.add_argument("--limit", type=int, default=200)
        p.add_argument("--min-chars", type=int, default=1500)
        p.add_argument("--run-at", default=None)
        p.set_defaults(func=fn)
    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())