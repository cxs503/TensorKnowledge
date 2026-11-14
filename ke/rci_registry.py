"""RCI-S1 · Research Asset Registry (anchor ``KBM-RCI-S1-REGISTRY``).

Turns the platform's published reports into a *verifiable asset ledger*: one row
per report, four-way asset typing with a recorded rule id, duplicate clusters,
a real-execution overlap flag against the mission result, and six quality
dimensions.  Every number in ``docs/rci-s1-registry.md`` is produced by this
module — never hand-copied — and ``aggregate`` is the single source of
aggregation truth shared by the merge phase and the verifier, so a summary that
disagrees with the row-level ledger is a hard failure.

Phases (each a pure function, so tests can drive them on a synthetic corpus)::

    features = shard_features(reports, missions, ledger, triple, shard=0, n=1)
    rows     = merge_features(features, snapshot="m15810@2026-11-11T20:00:31Z")
    summary  = aggregate(rows)
    assert_summary_matches(rows, summary)        # zero-hand-copy guarantee
    sweep    = sensitivity(features, gates=(0.4, 0.5, 0.7))

CLI (the reproduction path of the registry doc)::

    python3 -m ke.rci_registry shard --shard 0 --n 24 --data DIR --out DIR
    python3 -m ke.rci_registry merge --data DIR --shards DIR --out DIR --snapshot S
    python3 -m ke.rci_registry verify --out DIR
    python3 -m ke.rci_registry sensitivity --shards DIR --out DIR/sensitivity.json

``DIR`` for ``shard``/``merge`` is the CSV dump produced by
``audit/refs/rci-s1-registry/build_data.py`` (``reports.csv``, ``missions.csv``,
``clean_ledger.jsonl``, ``worktree_triple.json``) — the dump itself is a pinned
window over the platform DB, so this module never talks to the DB directly.

Design constraints kept from the original pipeline: pure stdlib (``psycopg2`` is
a stub on loong64), deterministic (no wall clock, sha256 digests only),
shard-count invariant (every aggregate is recomputed from rows, not from shard
partial sums).
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter, defaultdict

csv.field_size_limit(sys.maxsize)

# --- frozen parameters (recorded in summary["params"]; changing one is a new
# --- snapshot, not a tuning knob) ------------------------------------------
N_PERM = 128
BANDS, ROWS = 16, 8
JACCARD_GATE = 0.5
GRAM = 5
MD_WINDOW = 50_000
REAL_EXEC_VERIFIED = 0.5          # number overlap -> "verified"
TYPING_RULES = (
    "R0_clean_excluded", "R1_title_creative", "R2_title_research",
    "R3_title_analysis", "R4_title_info", "R5_goal_creative",
    "R6_goal_research", "R7_goal_analysis", "R8_goal_info", "R9_bench_ref",
    "R10_table_numbers", "R11_numbers", "R12_fallback",
)
ASSET_TYPES = ("info", "analysis", "research", "creative")
REAL_EXEC_FLAGS = ("verified", "partial", "zero_overlap", "no_numbers",
                   "no_mission", "no_result")

PARAMS = {"N_PERM": N_PERM, "BANDS": BANDS, "ROWS": ROWS, "GRAM": GRAM,
          "MD_WINDOW": MD_WINDOW, "JACCARD_GATE": JACCARD_GATE,
          "real_exec_verified": REAL_EXEC_VERIFIED,
          "dup_link": "exact_sha|title_norm|skeleton(number-masked)|minhash_lsh(J>=0.5)"}

NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
TITLE_KEEP_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")
MASK_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")
KW_CREATIVE = re.compile(r"新增|新建|实现|开发|重构|接入|移植|升级|支持|构建|搭建|扩展|补齐|打通|落地|成熟化|回填|修复|回修|补全")
KW_RESEARCH = re.compile(r"验证|对标|收敛|守恒|误差|解析|基准|复现|研究|推导|标定|求解|校核|核算|清算|清偿")
KW_ANALYSIS = re.compile(r"审计|核查|复算|对比|分析|盘点|评估|审查|抽检|复核|诊断|排查|归因|对拍|挖矿|判读")
KW_INFO = re.compile(r"补报|纪要|提案|通知|状态|进展|记录|备忘|登记|归档|汇报|周报|例会|probe|探针|情报")
BENCH_REF_RE = re.compile(r"解析解|解析值|文献|实验值|参考值|基准值|benchmark|守恒|收敛阶")
CLEAN_HARD_CODES = ("X02_empty_or_stub", "X06_process_log")

M64 = (1 << 64) - 1


def _perm_constants():
    """Deterministic (a, b) pairs for the 128 MinHash permutations."""
    out = []
    seed = 0x9E3779B97F4A7C15
    for p in range(N_PERM):
        seed = (seed * 6364136223846793005 + 1442695040888963407) % (1 << 64)
        a = (seed ^ (p * 0x9E3779B97F4A7C15)) | 1
        b = (seed >> 32) | ((p + 1) << 56)
        out.append((a, b))
    return out


PERMS = _perm_constants()


# --- normalisation / fingerprinting --------------------------------------

def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s or "")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def title_norm(t: str) -> str:
    """Case/punctuation-insensitive title key (CJK kept verbatim)."""
    return "".join(TITLE_KEEP_RE.sub("", (t or "").lower()))


def norm_num(s: str) -> str:
    return s.rstrip("0").rstrip(".") if "." in s else s


def numbers_of(md: str) -> set:
    out = set()
    for t in NUM_RE.findall(md or ""):
        t = norm_num(t)
        if t not in ("", "-", "+"):
            out.add(t)
    return out


def flatten_numbers(obj, acc: set) -> set:
    """Collect every numeric literal inside a JSON value (mission.result)."""
    if isinstance(obj, bool):
        return acc
    if isinstance(obj, (int, float)):
        v = int(obj) if isinstance(obj, float) and obj.is_integer() else obj
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
    return acc


def gram_hashes(md: str) -> list:
    """Deterministic 5-gram 64-bit hashes over the tail window, sorted."""
    if len(md) <= GRAM:
        return []
    window = md[-MD_WINDOW:] if len(md) > MD_WINDOW else md
    seen = set()
    for i in range(len(window) - GRAM + 1):
        g = window[i:i + GRAM]
        seen.add(int.from_bytes(hashlib.md5(g.encode("utf-8")).digest()[:8], "big"))
    return sorted(seen)


def minhash_sig(gh: list) -> list:
    """MinHash-128 signature; an empty sketch hashes to all zeros."""
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


def jaccard(sa: set, sb: set) -> float:
    if not sa or not sb:
        return 0.0
    inter = len(sa & sb)
    return inter / (len(sa) + len(sb) - inter)


def classify(title: str, goal: str, md: str, clean_code: str,
             has_table: bool, n_numbers: int):
    """Deterministic 4-way typing cascade; returns ``(asset_type, rule_id)``.

    Cascade order is title -> mission goal -> body signal, so the rule id that
    fires *is* the provenance of the type.  ``R12_fallback`` means "no signal
    matched" and is asserted to be 0 on the registry snapshot.
    """
    if clean_code in CLEAN_HARD_CODES:
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


# --- phase 1: per-report features ----------------------------------------

def _as_json(raw, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return default


def feature_record(report: dict, mission: dict | None = None,
                   clean: dict | None = None, triple: dict | None = None) -> dict:
    """Per-report feature record (the shard artefact).

    ``report``/``mission`` are CSV-dump rows (strings), ``clean`` a KBM-CLEAN-W1
    ledger row, ``triple`` the worktree probe for the report's mission.
    """
    rid = int(report["id"])
    md = nfc(report.get("markdown") or "")
    title = report.get("title") or ""
    mid = int(report["mission_id"]) if report.get("mission_id") else None
    goal = (mission.get("goal") or "") if mission else ""
    repo = mission["repo"] if mission else None
    tags = _as_json(report.get("tags"), [])
    figs = _as_json(report.get("figures"), [])

    gh = gram_hashes(md)
    nums = numbers_of(md)
    has_table = md.count("|") > 10

    clean_decision = clean["decision"] if clean else "not_in_w1"
    clean_code = clean["reason"] if (clean and clean["decision"] == "excluded") else None
    n_repairs = len(clean["repairs"]) if clean else 0
    atype, rule = classify(title, goal, md, clean_code or "", has_table, len(nums))

    flag, overlap = "no_mission", None
    if mission is not None:
        resj = _as_json(mission.get("result"), {})
        if not resj:
            flag = "no_result"
        elif not nums:
            flag = "no_numbers"
        else:
            resnums = flatten_numbers(resj, set())
            inter = len(nums & resnums)
            overlap = inter / len(nums)
            flag = ("verified" if overlap >= REAL_EXEC_VERIFIED
                    else ("partial" if inter > 0 else "zero_overlap"))

    t = triple or {}
    fec = []
    if not nums:
        fec.append("no_numbers")
    if not (t.get("wt_artifacts") or figs):
        fec.append("no_artifact")
    if clean_code in ("X02_empty_or_stub", "X05_pure_template", "X06_process_log"):
        fec.append("clean_" + clean_code)

    return {
        "id": rid,
        "title": title,
        "scenario_key": report.get("scenario_key"),
        "repo": repo,
        "mission_id": mid,
        "mission_status": mission.get("status") if mission else None,
        "mission_model": mission.get("model") if mission else None,
        "mission_claimed_by": mission.get("claimed_by") if mission else None,
        "mission_created_at": mission.get("created_at") if mission else None,
        "mission_finished_at": mission.get("finished_at") if mission else None,
        "md_chars": len(md),
        "n_figures": len(figs),
        "n_tags": len(tags),
        "has_table": has_table,
        "n_numbers": len(nums),
        "md_sha256": sha256_bytes(md.encode("utf-8")),
        "title_norm": title_norm(title),
        "skeleton_sha256": sha256_bytes(MASK_RE.sub("#", md).encode("utf-8")),
        "minhash": minhash_sig(gh),
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
        "created_at": report.get("created_at"),
    }


def shard_features(reports, missions: dict, ledger: dict, triple: dict,
                   shard: int = 0, n: int = 1) -> list:
    """Features for ``id % n == shard``; shard count never affects aggregates."""
    out = []
    for row in reports:
        rid = int(row["id"])
        if rid % n != shard:
            continue
        mid = int(row["mission_id"]) if row.get("mission_id") else None
        out.append(feature_record(
            row,
            missions.get(mid) if mid else None,
            ledger.get(rid),
            triple.get(str(mid)) if mid else None,
        ))
    return out


def load_ledger(path: str) -> dict:
    """KBM-CLEAN-W1 ledger (``key = report:<id>``) keyed by report id."""
    out = {}
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            out[int(str(r["key"]).split(":")[1])] = r
    return out


def load_csv(path: str) -> list:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --- phase 2: merge / duplicate clustering --------------------------------

class DSU:
    """Union-find with the smaller id as root (stable cluster ids)."""

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


def lsh_pairs(feats: list) -> list:
    """Candidate pairs from 16x8 banded MinHash signatures (conservative)."""
    cand = set()
    for b in range(BANDS):
        buckets = defaultdict(list)
        for r in feats:
            buckets[tuple(r["minhash"][b * ROWS:(b + 1) * ROWS])].append(r["id"])
        for grp in buckets.values():
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    x, y = grp[i], grp[j]
                    cand.add((x, y) if x < y else (y, x))
    return sorted(cand)


def structural_groups(feats: list) -> dict:
    """Gate-independent exact links: md sha256, normalised title, masked skeleton."""
    groups = defaultdict(list)
    for key in ("md_sha256", "title_norm", "skeleton_sha256"):
        g = defaultdict(list)
        for r in feats:
            if r.get(key):
                g[r[key]].append(r["id"])
        for members in g.values():
            for x in members[1:]:
                groups[(key, members[0])].append(x)
    return groups


def _quality(r: dict) -> dict:
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
    return {"q_completeness": round(q_comp, 3),
            "q_accuracy": None,
            "q_traceability": round(q_trace, 3),
            "q_reusability": None,
            "q_freshness": None,
            "q_consistency": q_cons}


def merge_features(feats: list, snapshot: str = "",
                   jaccard_gate: float = JACCARD_GATE) -> list:
    """Cluster duplicates and emit the registry rows (one per report)."""
    feats = sorted(feats, key=lambda r: r["id"])
    by_id = {r["id"]: r for r in feats}
    dsu = DSU()
    pair_kinds = defaultdict(set)

    def link(a, b, kind):
        dsu.union(a, b)
        pair_kinds[(min(a, b), max(a, b))].add(kind)

    for kind, key in (("exact", "md_sha256"), ("title", "title_norm"),
                      ("skeleton", "skeleton_sha256")):
        g = defaultdict(list)
        for r in feats:
            if r.get(key):
                g[r[key]].append(r["id"])
        for members in g.values():
            for x in members[1:]:
                link(members[0], x, kind)

    pairs = lsh_pairs(feats)
    for a, b in pairs:
        jac = jaccard(set(by_id[a]["gram_hashes"]), set(by_id[b]["gram_hashes"]))
        if jac >= jaccard_gate:
            link(a, b, "minhash")

    comp = defaultdict(list)
    for r in feats:
        comp[dsu.find(r["id"])].append(r["id"])

    rows = []
    for root, members in comp.items():
        members = sorted(members)
        if len(members) >= 2:
            cid, csize = min(members), len(members)
            kinds = set()
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    kinds |= pair_kinds.get((members[i], members[j]), set())
            ckind = ",".join(sorted(kinds))
        else:
            cid, csize, ckind = None, 1, None
        for x in members:
            r = by_id[x]
            row = {
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
            }
            row.update(_quality(r))
            row.update({
                "dup_cluster_id": cid,
                "dup_cluster_size": csize,
                "dup_kind": ckind,
                "real_exec_flag": r["real_exec_flag"],
                "real_exec_overlap": (round(r["real_exec_overlap"], 4)
                                      if r["real_exec_overlap"] is not None else None),
                "clean_decision": r["clean_decision"],
                "clean_primary_code": r["clean_primary_code"],
                "failed_empty": bool(r["failed_empty_codes"]),
                "failed_empty_codes": list(r["failed_empty_codes"]),
                "created_at": r["created_at"],
                "snapshot_id": snapshot,
            })
            rows.append(row)
    rows.sort(key=lambda r: r["report_id"])
    return rows


# --- phase 3: aggregation + verification ---------------------------------

AGGREGATE_KEYS = (
    "rows", "by_type", "by_type_rule", "by_real_exec", "by_clean",
    "dup_clusters", "dup_reports_in_clusters", "dup_excess_reports",
    "dup_cluster_size_hist", "dup_kind", "failed_empty", "failed_empty_codes",
    "triple_ok", "wt_exists", "with_mission", "distinct_missions",
    "distinct_repos", "distinct_scenarios", "md_chars_total", "md_chars_p50",
    "n_figures_total", "reports_with_figures", "q_dims_pending",
)


def aggregate(rows: list) -> dict:
    """The single source of aggregation truth (used by merge *and* verify)."""
    clusters = Counter(r["dup_cluster_id"] for r in rows if r.get("dup_cluster_id"))
    in_clusters = sum(1 for r in rows if r.get("dup_cluster_id"))
    chars = sorted(r["md_chars"] for r in rows)
    return {
        "rows": len(rows),
        "by_type": dict(Counter(r["asset_type"] for r in rows)),
        "by_type_rule": dict(Counter(r["type_rule"] for r in rows)),
        "by_real_exec": dict(Counter(r["real_exec_flag"] for r in rows)),
        "by_clean": dict(Counter(r["clean_decision"] for r in rows)),
        "dup_clusters": len(clusters),
        "dup_reports_in_clusters": in_clusters,
        "dup_excess_reports": in_clusters - len(clusters),
        "dup_cluster_size_hist": {str(k): v for k, v in Counter(clusters.values()).items()},
        "dup_kind": dict(Counter(r["dup_kind"] for r in rows if r.get("dup_kind"))),
        "failed_empty": sum(1 for r in rows if r.get("failed_empty")),
        "failed_empty_codes": dict(Counter(c for r in rows
                                           for c in r.get("failed_empty_codes") or [])),
        "triple_ok": sum(1 for r in rows if r.get("triple_ok")),
        "wt_exists": sum(1 for r in rows if r.get("wt_exists")),
        "with_mission": sum(1 for r in rows if r.get("mission_id")),
        "distinct_missions": len({r["mission_id"] for r in rows if r.get("mission_id")}),
        "distinct_repos": len({r["repo"] for r in rows if r.get("repo")}),
        "distinct_scenarios": len({r["scenario_key"] for r in rows
                                   if r.get("scenario_key")}),
        "md_chars_total": sum(chars),
        "md_chars_p50": chars[len(chars) // 2] if chars else 0,
        "n_figures_total": sum(r["n_figures"] for r in rows),
        "reports_with_figures": sum(1 for r in rows if r["n_figures"] > 0),
        "q_dims_pending": sorted({k for r in rows for k, v in r.items()
                                  if k.startswith("q_") and v is None}),
    }


def summary_mismatches(rows: list, summary: dict) -> list:
    """Recompute every aggregate from rows; return ``[(key, in_summary, recomputed)]``."""
    expect = aggregate(rows)
    return [(k, summary.get(k), expect[k]) for k in AGGREGATE_KEYS
            if summary.get(k) != expect[k]]


def assert_summary_matches(rows: list, summary: dict) -> None:
    bad = summary_mismatches(rows, summary)
    if bad:
        raise AssertionError(
            "summary disagrees with the row-level ledger: "
            + json.dumps(bad, ensure_ascii=False))


# --- sensitivity: move only the Jaccard gate ------------------------------

def sensitivity(feats: list, gates=(0.4, 0.5, 0.7), include_lsh_only=True) -> dict:
    """Duplicate-cluster counts as the exact-Jaccard gate moves.

    Structural links (exact sha / title / masked skeleton) are gate-independent,
    so only the MinHash-verified links can change: more clusters at a looser
    gate, never fewer — the monotonicity the registry doc claims.
    """
    pairs = lsh_pairs(feats)
    by_id = {r["id"]: r for r in feats}

    def sweep_one(gate: float) -> dict:
        dsu = DSU()
        for kind, key in (("exact", "md_sha256"), ("title", "title_norm"),
                          ("skeleton", "skeleton_sha256")):
            g = defaultdict(list)
            for r in feats:
                if r.get(key):
                    g[r[key]].append(r["id"])
            for members in g.values():
                for x in members[1:]:
                    dsu.union(members[0], x)
        used = 0
        for a, b in pairs:
            jac = jaccard(set(by_id[a]["gram_hashes"]), set(by_id[b]["gram_hashes"]))
            if jac <= 0.0:
                continue
            if gate == 0 or jac >= gate:
                dsu.union(a, b)
                used += 1
        comp = defaultdict(list)
        for r in feats:
            comp[dsu.find(r["id"])].append(r["id"])
        multi = {k: v for k, v in comp.items() if len(v) >= 2}
        in_clusters = sum(len(v) for v in multi.values())
        return {"gate": gate, "lsh_pairs": len(pairs), "pairs_accepted": used,
                "dup_clusters": len(multi), "dup_reports": in_clusters,
                "dup_excess": in_clusters - len(multi),
                "largest_cluster": max((len(v) for v in multi.values()), default=0)}

    out = [sweep_one(float(g)) for g in gates]
    if include_lsh_only:
        out.append(sweep_one(0.0))
    return {"n_reports": len(feats), "params": PARAMS,
            "note": "gate=0.0 == LSH-band-only upper bound (no exact Jaccard pruning)",
            "sweep": out}


# --- IO helpers -----------------------------------------------------------

def write_rows(rows: list, path: str) -> None:
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_rows(path: str) -> list:
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


# --- CLI ------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ke.rci_registry")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("shard", help="per-report features for id %% n == shard")
    p.add_argument("--shard", type=int, required=True)
    p.add_argument("--n", type=int, required=True)
    p.add_argument("--data", required=True)
    p.add_argument("--out", required=True)
    p = sub.add_parser("merge", help="cluster + emit registry rows/summary")
    p.add_argument("--data", required=True)
    p.add_argument("--shards", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--snapshot", default="")
    p = sub.add_parser("verify", help="recompute every aggregate from the rows")
    p.add_argument("--out", required=True)
    p = sub.add_parser("sensitivity", help="Jaccard-gate sweep from frozen shards")
    p.add_argument("--shards", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--gates", default="0.4,0.5,0.7")
    a = ap.parse_args(argv)

    if a.cmd == "shard":
        reports = load_csv(os.path.join(a.data, "reports.csv"))
        missions = {int(m["id"]): m for m in load_csv(os.path.join(a.data, "missions.csv"))}
        ledger = load_ledger(os.path.join(a.data, "clean_ledger.jsonl"))
        tp = os.path.join(a.data, "worktree_triple.json")
        triple = json.load(open(tp, encoding="utf-8")) if os.path.exists(tp) else {}
        feats = shard_features(reports, missions, ledger, triple, a.shard, a.n)
        os.makedirs(a.out, exist_ok=True)
        write_rows(feats, os.path.join(a.out, f"shard_{a.shard:03d}.jsonl"))
        print(f"shard {a.shard}/{a.n}: {len(feats)} reports")
        return 0

    if a.cmd == "merge":
        feats = []
        for fn in sorted(os.listdir(a.shards)):
            if fn.startswith("shard_") and fn.endswith(".jsonl"):
                feats.extend(read_rows(os.path.join(a.shards, fn)))
        rows = merge_features(feats, snapshot=a.snapshot)
        os.makedirs(a.out, exist_ok=True)
        write_rows(rows, os.path.join(a.out, "registry_rows.jsonl"))
        s = aggregate(rows)
        s["snapshot_id"] = a.snapshot
        s["params"] = PARAMS
        s["lsh_candidate_pairs"] = len(lsh_pairs(feats))
        s["shards"] = len([f for f in os.listdir(a.shards) if f.endswith(".jsonl")])
        with open(os.path.join(a.out, "summary.json"), "w", encoding="utf-8") as f:
            json.dump(s, f, ensure_ascii=False, indent=1)
        print(json.dumps({k: s[k] for k in ("rows", "dup_clusters", "dup_excess_reports")},
                         ensure_ascii=False))
        return 0

    if a.cmd == "verify":
        rows = read_rows(os.path.join(a.out, "registry_rows.jsonl"))
        summary = json.load(open(os.path.join(a.out, "summary.json"), encoding="utf-8"))
        bad = summary_mismatches(rows, summary)
        if bad:
            print("VERIFY FAIL: " + json.dumps(bad, ensure_ascii=False))
            return 1
        print(f"VERIFY OK: all {len(AGGREGATE_KEYS)} aggregates recomputed equal "
              f"over {len(rows)} rows")
        return 0

    feats = []
    for fn in sorted(os.listdir(a.shards)):
        if fn.startswith("shard_") and fn.endswith(".jsonl"):
            feats.extend(read_rows(os.path.join(a.shards, fn)))
    out = sensitivity(feats, [float(g) for g in a.gates.split(",")])
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps(out["sweep"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())