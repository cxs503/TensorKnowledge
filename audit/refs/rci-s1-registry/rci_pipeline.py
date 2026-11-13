#!/usr/bin/env python3
"""RCI-S1 · Research Asset Registry pipeline (pure stdlib, loong64-safe).

Phases (designed for cluster sharding):

  shard  --shard i --n N --data DIR --out DIR
      Per-report features for report ids with id % N == i: format stats,
      fingerprints (exact sha / title / number-masked skeleton / MinHash),
      4-way type classification, real-execution overlap vs mission.result,
      clean-ledger + worktree-triple joins.

  merge  --data DIR --shards DIR --out DIR
      Union-find over (exact sha, title, skeleton, LSH candidates),
      cluster assignment, registry rows, deep-dive sample, summary.

  verify --out DIR
      Recompute every summary.json aggregate from registry_rows.jsonl;
      exit 1 on any mismatch (zero-hand-copy guarantee).

Determinism: no wall-clock in outputs; all digests sha256.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

csv.field_size_limit(sys.maxsize)

N_PERM = 128
BANDS, ROWS = 16, 8
JACCARD_GATE = 0.5
GRAM = 5
MD_WINDOW = 50_000
NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
TITLE_KEEP_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")
MASK_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
KW_CREATIVE = re.compile(r"新增|新建|实现|开发|重构|接入|移植|升级|支持|构建|搭建|扩展|补齐|打通|落地|成熟化|回填|修复|回修|补全")
KW_RESEARCH = re.compile(r"验证|对标|收敛|守恒|误差|解析|基准|复现|研究|推导|标定|求解|校核|核算|清算|清偿")
KW_ANALYSIS = re.compile(r"审计|核查|复算|对比|分析|盘点|评估|审查|抽检|复核|诊断|排查|归因|对拍|挖矿|判读")
KW_INFO = re.compile(r"补报|纪要|提案|通知|状态|进展|记录|备忘|登记|归档|汇报|周报|例会|probe|探针|情报")
BENCH_REF_RE = re.compile(r"解析解|解析值|文献|实验值|参考值|基准值|benchmark|守恒|收敛阶")


def _perm_constants():
    out = []
    seed = 0x9E3779B97F4A7C15
    for p in range(N_PERM):
        seed = (seed * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        a = (seed ^ (p * 0x9E3779B97F4A7C15)) | 1
        b = (seed >> 32) | ((p + 1) << 56)
        out.append((a, b))
    return out


PERMS = _perm_constants()
M64 = (1 << 64) - 1


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def title_norm(t: str) -> str:
    return "".join(TITLE_KEEP_RE.sub("", (t or "").lower()))


def norm_num(s: str) -> str:
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return s


def numbers_of(md: str) -> set:
    out = set()
    for t in NUM_RE.findall(md or ""):
        t = norm_num(t)
        if t not in ("", "-", "+"):
            out.add(t)
    return out


def flatten_numbers(obj, acc: set):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        v = obj
        if isinstance(v, float) and v.is_integer():
            v = int(v)
        s = norm_num(str(v))
        if s not in ("", "-", "+"):
            acc.add(s)
    elif isinstance(obj, str):
        for t in NUM_RE.findall(obj):
            t = norm_num(t)
            if t not in ("", "-", "+"):
                acc.add(t)
    elif isinstance(obj, dict):
        for v in obj.values():
            flatten_numbers(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            flatten_numbers(v, acc)


def gram_hashes(md: str) -> list:
    """Deterministic 5-gram hash list (tail window), deduped, sorted."""
    if len(md) <= GRAM:
        return []
    window = md[-MD_WINDOW:] if len(md) > MD_WINDOW else md
    seen = set()
    for i in range(len(window) - GRAM + 1):
        g = window[i:i + GRAM]
        h = int.from_bytes(hashlib.md5(g.encode("utf-8")).digest()[:8], "big")
        seen.add(h)
    return sorted(seen)


def minhash_sig(gh: list) -> list:
    if not gh:
        return [0] * N_PERM
    sig = []
    for a, b in PERMS:
        m = M64
        for h in gh:
            v = (a * h + b) & M64
            if v < m:
                m = v
        sig.append(m)
    return sig


def classify(title: str, goal: str, md: str, clean_code: str,
              has_table: bool, n_numbers: int):
    """Deterministic 4-way cascade; returns (type, rule)."""
    if clean_code in ("X02_empty_or_stub", "X06_process_log"):
        return "info", "R0_clean_excluded"
    if KW_CREATIVE.search(title):
        return "creative", "R1_title_creative"
    if KW_RESEARCH.search(title):
        return "research", "R2_title_research"
    if KW_ANALYSIS.search(title):
        return "analysis", "R3_title_analysis"
    if KW_INFO.search(title):
        return "info", "R4_title_info"
    if KW_CREATIVE.search(goal):
        return "creative", "R5_goal_creative"
    if KW_RESEARCH.search(goal):
        return "research", "R6_goal_research"
    if KW_ANALYSIS.search(goal):
        return "analysis", "R7_goal_analysis"
    if KW_INFO.search(goal):
        return "info", "R8_goal_info"
    if BENCH_REF_RE.search(md):
        return "research", "R9_bench_ref"
    if has_table and n_numbers > 0:
        return "analysis", "R10_table_numbers"
    if n_numbers > 0:
        return "analysis", "R11_numbers"
    return "info", "R12_fallback"


def load_missions(path):
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[int(row["id"])] = row
    return out


def run_shard(shard: int, n: int, data: str, out: str):
    reports = []
    with open(f"{data}/reports.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(row["id"]) % n == shard:
                reports.append(row)
    missions = load_missions(f"{data}/missions.csv")
    ledger = {}
    lp = f"{data}/clean_ledger.jsonl"
    if os.path.exists(lp):
        for line in open(lp, encoding="utf-8"):
            r = json.loads(line)
            ledger[int(r["key"].split(":")[1])] = r
    triple = json.load(open(f"{data}/worktree_triple.json"))

    os.makedirs(out, exist_ok=True)
    with open(f"{out}/shard_{shard:03d}.jsonl", "w", encoding="utf-8") as fo:
        for row in reports:
            rid = int(row["id"])
            md = nfc(row["markdown"] or "")
            title = row["title"] or ""
            mid = int(row["mission_id"]) if row["mission_id"] else None
            m = missions.get(mid) if mid else None
            goal = (m["goal"] or "") if m else ""
            repo = m["repo"] if m else None
            try:
                tags = json.loads(row["tags"] or "[]")
            except json.JSONDecodeError:
                tags = []
            try:
                figs = json.loads(row["figures"] or "[]")
            except json.JSONDecodeError:
                figs = []
            gh = gram_hashes(md)
            sig = minhash_sig(gh)
            nums = numbers_of(md)
            has_table = md.count("|") > 10
            lr = ledger.get(rid)
            clean_decision = lr["decision"] if lr else "not_in_w1"
            clean_code = lr["reason"] if (lr and lr["decision"] == "excluded") else None
            n_repairs = len(lr["repairs"]) if lr else 0
            atype, rule = classify(title, goal, md, clean_code or "", has_table, len(nums))
            flag, overlap = "no_mission", None
            if m:
                try:
                    resj = json.loads(m["result"]) if m["result"] else {}
                except json.JSONDecodeError:
                    resj = {}
                if not resj:
                    flag = "no_result"
                elif not nums:
                    flag = "no_numbers"
                else:
                    resnums = set()
                    flatten_numbers(resj, resnums)
                    inter = len(nums & resnums)
                    overlap = inter / len(nums)
                    flag = "verified" if overlap >= 0.5 else ("partial" if inter > 0 else "zero_overlap")
            t = triple.get(str(mid)) if mid else {}
            t = t or {}
            fec = []
            if not nums:
                fec.append("no_numbers")
            if not (t.get("wt_artifacts") or figs):
                fec.append("no_artifact")
            if clean_code in ("X02_empty_or_stub", "X05_pure_template", "X06_process_log"):
                fec.append("clean_" + clean_code)
            rec = {
                "id": rid,
                "title": title,
                "scenario_key": row["scenario_key"],
                "repo": repo,
                "mission_id": mid,
                "mission_status": m["status"] if m else None,
                "mission_model": m["model"] if m else None,
                "mission_claimed_by": m["claimed_by"] if m else None,
                "mission_created_at": m["created_at"] if m else None,
                "mission_finished_at": m["finished_at"] if m else None,
                "md_chars": len(md),
                "n_figures": len(figs),
                "n_tags": len(tags),
                "has_table": has_table,
                "n_numbers": len(nums),
                "md_sha256": sha256_bytes(md.encode("utf-8")),
                "title_norm": title_norm(title),
                "skeleton_sha256": sha256_bytes(MASK_RE.sub("#", md).encode("utf-8")),
                "minhash": sig,
                "gram_hashes": gh,
                "asset_type": atype,
                "type_rule": rule,
                "real_exec_flag": flag,
                "real_exec_overlap": overlap,
                "clean_decision": clean_decision,
                "clean_primary_code": clean_code,
                "n_clean_repairs": n_repairs,
                "wt_exists": t.get("wt_exists", False),
                "wt_artifacts": t.get("wt_artifacts", False),
                "wt_repro": t.get("wt_repro", False),
                "triple_ok": t.get("triple_ok", False),
                "failed_empty_codes": fec,
                "created_at": row["created_at"],
            }
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")


class DSU:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[max(ra, rb)] = min(ra, rb)


PARAMS = {"N_PERM": N_PERM, "BANDS": BANDS, "ROWS": ROWS, "GRAM": GRAM,
          "MD_WINDOW": MD_WINDOW, "JACCARD_GATE": JACCARD_GATE,
          "dup_link": "exact_sha|title_norm|skeleton(number-masked)|minhash_lsh(J>=0.5)"}


def _agg(rows):
    """Single source of aggregation truth: used by merge AND verify."""
    clusters = {}
    for x in rows:
        if x["dup_cluster_id"]:
            clusters.setdefault(x["dup_cluster_id"], 0)
            clusters[x["dup_cluster_id"]] += 1
    return {
        "rows": len(rows),
        "by_type": dict(Counter(x["asset_type"] for x in rows)),
        "by_type_rule": dict(Counter(x["type_rule"] for x in rows)),
        "by_real_exec": dict(Counter(x["real_exec_flag"] for x in rows)),
        "by_clean": dict(Counter(x["clean_decision"] for x in rows)),
        "dup_clusters": len(clusters),
        "dup_reports_in_clusters": sum(1 for x in rows if x["dup_cluster_id"]),
        "dup_excess_reports": sum(1 for x in rows if x["dup_cluster_id"]) - len(clusters),
        "dup_cluster_size_hist": {str(k): v for k, v in Counter(clusters.values()).items()},
        "dup_kind": dict(Counter(x["dup_kind"] for x in rows if x["dup_kind"])),
        "failed_empty": sum(1 for x in rows if x["failed_empty"]),
        "failed_empty_codes": dict(Counter(c for x in rows for c in x["failed_empty_codes"])),
        "triple_ok": sum(1 for x in rows if x["triple_ok"]),
        "wt_exists": sum(1 for x in rows if x["wt_exists"]),
        "with_mission": sum(1 for x in rows if x["mission_id"]),
        "distinct_missions": len({x["mission_id"] for x in rows if x["mission_id"]}),
        "distinct_repos": len({x["repo"] for x in rows if x["repo"]}),
        "distinct_scenarios": len({x["scenario_key"] for x in rows if x["scenario_key"]}),
        "md_chars_total": sum(x["md_chars"] for x in rows),
        "md_chars_p50": sorted(x["md_chars"] for x in rows)[len(rows) // 2],
        "n_figures_total": sum(x["n_figures"] for x in rows),
        "reports_with_figures": sum(1 for x in rows if x["n_figures"] > 0),
        "q_dims_pending": sorted({k for x in rows for k, v in x.items()
                                  if k.startswith("q_") and v is None}),
    }


def run_merge(data: str, shards: str, out: str, snapshot: str = ""):
    os.makedirs(out, exist_ok=True)
    feats = []
    for fn in sorted(os.listdir(shards)):
        if fn.startswith("shard_") and fn.endswith(".jsonl"):
            with open(f"{shards}/{fn}", encoding="utf-8") as f:
                feats.extend(json.loads(l) for l in f)
    feats.sort(key=lambda r: r["id"])
    by_id = {r["id"]: r for r in feats}

    dsu = DSU()
    pair_rel = defaultdict(set)

    def union(a, b, kind):
        dsu.union(a, b)
        pair_rel[(min(a, b), max(a, b))].add(kind)

    by_sha = defaultdict(list)
    for r in feats:
        by_sha[r["md_sha256"]].append(r["id"])
    for grp in by_sha.values():
        for x in grp[1:]:
            union(grp[0], x, "exact")
    by_title = defaultdict(list)
    for r in feats:
        if r["title_norm"]:
            by_title[r["title_norm"]].append(r["id"])
    for grp in by_title.values():
        for x in grp[1:]:
            union(grp[0], x, "title")
    by_skel = defaultdict(list)
    for r in feats:
        by_skel[r["skeleton_sha256"]].append(r["id"])
    for grp in by_skel.values():
        for x in grp[1:]:
            union(grp[0], x, "skeleton")

    cand = set()
    for b in range(BANDS):
        buckets = defaultdict(list)
        for r in feats:
            key = tuple(r["minhash"][b * ROWS:(b + 1) * ROWS])
            buckets[key].append(r["id"])
        for grp in buckets.values():
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    x, y = grp[i], grp[j]
                    cand.add((x, y) if x < y else (y, x))
    n_checked = 0
    for a, b in sorted(cand):
        sa, sb = set(by_id[a]["gram_hashes"]), set(by_id[b]["gram_hashes"])
        if not sa or not sb:
            continue
        inter = len(sa & sb)
        jac = inter / (len(sa) + len(sb) - inter)
        n_checked += 1
        if jac >= JACCARD_GATE:
            union(a, b, "minhash")

    comp = defaultdict(list)
    for r in feats:
        comp[dsu.find(r["id"])].append(r["id"])
    cluster_of = {}
    for root, members in comp.items():
        if len(members) >= 2:
            cid = min(members)
            kinds = set()
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    kinds |= pair_rel.get((min(members[i], members[j]), max(members[i], members[j])), set())
            for x in members:
                cluster_of[x] = (cid, len(members), ",".join(sorted(kinds)))
        else:
            for x in members:
                cluster_of[x] = (None, 1, None)

    rows = []
    for r in feats:
        cid, csize, ckind = cluster_of[r["id"]]
        q_comp = (
            (1 if r["title"] else 0)
            + (1 if r["md_chars"] > 120 else 0)
            + (1 if r["mission_id"] else 0)
            + (1 if r["n_figures"] > 0 or r["has_table"] else 0)
            + (1 if r["clean_decision"] in ("kept", "repaired") else 0)
        ) / 5.0
        q_trace = (
            (1 if r["mission_id"] else 0)
            + (1 if r["triple_ok"] else 0)
            + (1 if r["clean_decision"] in ("kept", "repaired") else 0)
        ) / 3.0
        q_cons = 1.0 if (r["n_clean_repairs"] or 0) == 0 else 0.5
        rows.append({
            "report_id": r["id"],
            "repo": r["repo"],
            "scenario_key": r["scenario_key"],
            "mission_id": r["mission_id"],
            "mission_status": r["mission_status"],
            "mission_model": r["mission_model"],
            "mission_claimed_by": r["mission_claimed_by"],
            "mission_created_at": r["mission_created_at"],
            "mission_finished_at": r["mission_finished_at"],
            "md_chars": r["md_chars"],
            "n_figures": r["n_figures"],
            "n_tags": r["n_tags"],
            "wt_exists": r["wt_exists"],
            "wt_artifacts": r["wt_artifacts"],
            "wt_repro": r["wt_repro"],
            "triple_ok": r["triple_ok"],
            "asset_type": r["asset_type"],
            "type_rule": r["type_rule"],
            "q_completeness": round(q_comp, 3),
            "q_accuracy": None,
            "q_traceability": round(q_trace, 3),
            "q_reusability": None,
            "q_freshness": None,
            "q_consistency": q_cons,
            "dup_cluster_id": cid,
            "dup_cluster_size": csize,
            "dup_kind": ckind,
            "real_exec_flag": r["real_exec_flag"],
            "real_exec_overlap": round(r["real_exec_overlap"], 4) if r["real_exec_overlap"] is not None else None,
            "clean_decision": r["clean_decision"],
            "clean_primary_code": r["clean_primary_code"],
            "failed_empty": bool(r["failed_empty_codes"]),
            "failed_empty_codes": r["failed_empty_codes"],
            "created_at": r["created_at"],
        })
    for row in rows:
        row["snapshot_id"] = snapshot
    with open(f"{out}/registry_rows.jsonl", "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    # deep-dive: stratified by real_exec_flag; recompute number overlap with
    # explicit per-number evidence (top 15 by (len desc, value)) from source.
    missions = load_missions(f"{data}/missions.csv")
    rep_md = {}
    with open(f"{data}/reports.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rep_md[int(row["id"])] = row
    strata = defaultdict(list)
    for r in feats:
        strata[r["real_exec_flag"]].append(r)
    deep = []
    for flag in sorted(strata):
        grp = sorted(strata[flag], key=lambda r: r["id"])
        k = min(12, len(grp))
        step = len(grp) / k
        for i in range(k):
            r = grp[int(i * step)]
            md = nfc(rep_md[r["id"]]["markdown"] or "")
            nums = numbers_of(md)
            top = sorted(nums, key=lambda s: (-len(s), s))[:15]
            resnums = set()
            m = missions.get(r["mission_id"]) if r["mission_id"] else None
            if m:
                try:
                    resj = json.loads(m["result"]) if m["result"] else {}
                except json.JSONDecodeError:
                    resj = {}
                flatten_numbers(resj, resnums)
            deep.append({
                "report_id": r["id"],
                "flag": r["real_exec_flag"],
                "mission_id": r["mission_id"],
                "n_report_numbers": len(nums),
                "top_numbers": top,
                "in_result": [x for x in top if x in resnums],
                "n_in_result": sum(1 for x in top if x in resnums),
            })
    with open(f"{out}/deep_dive.json", "w", encoding="utf-8") as f:
        json.dump({"strata_sizes": {k: len(v) for k, v in strata.items()},
                   "sampled": deep}, f, ensure_ascii=False, indent=1)

    s = _agg(rows)
    s["snapshot_id"] = snapshot
    s["params"] = PARAMS
    s["lsh_candidate_pairs"] = n_checked
    s["shards"] = len([f for f in os.listdir(shards) if f.endswith(".jsonl")])
    with open(f"{out}/summary.json", "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=1)
    print(json.dumps(s, ensure_ascii=False))


def run_verify(out: str):
    rows = [json.loads(l) for l in open(f"{out}/registry_rows.jsonl", encoding="utf-8")]
    s = json.load(open(f"{out}/summary.json", encoding="utf-8"))
    expect = _agg(rows)
    for k in ("snapshot_id", "params", "lsh_candidate_pairs", "shards"):
        expect[k] = s.get(k)
    bad = []
    for k, v in expect.items():
        if s.get(k) != v:
            bad.append((k, s.get(k), v))
    if bad:
        print("VERIFY FAIL:", json.dumps(bad, ensure_ascii=False))
        sys.exit(1)
    print("VERIFY OK: all", len(expect), "aggregates recomputed equal")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("shard")
    p1.add_argument("--shard", type=int, required=True)
    p1.add_argument("--n", type=int, required=True)
    p1.add_argument("--data", required=True)
    p1.add_argument("--out", required=True)
    p2 = sub.add_parser("merge")
    p2.add_argument("--data", required=True)
    p2.add_argument("--shards", required=True)
    p2.add_argument("--out", required=True)
    p2.add_argument("--snapshot", default="")
    p3 = sub.add_parser("verify")
    p3.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "shard":
        run_shard(a.shard, a.n, a.data, a.out)
    elif a.cmd == "merge":
        run_merge(a.data, a.shards, a.out, a.snapshot)
    else:
        run_verify(a.out)


if __name__ == "__main__":
    main()
