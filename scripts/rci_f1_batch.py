#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 批次构建（预注册用，先于执行）。

从 m15462 的 200 份分层试点样本（repo x content_type x tier，131 层）里，
按**预先声明**的规则抽取 60 份分层子集，并把同一批次写成三臂共用的
工作包台账（lane=A/B/C）。

规则（写死在本文，改动必须新版本号）:
  S1 分层键 = content_type x tier（12 个非空单元）。
  S2 分配 = Hamilton 最大余数法，按 200 样本各单元占比分配 N=60，每单元保底 1 席。
  S3 层内排序 = sha256("rci-f1-abc-v1|<repo>|<path>") 升序（与路径/时间/大小无关）。
  S4 层内选样 = 按该层 repo 轮转（round-robin）取前 k 席 → 确定性提高仓覆盖面。
  S5 工作包 = A 臂 1 包(60 份)；B/C 臂各 20 包(每包 3 份)，B 与 C 的 doc→package
     映射完全相同（配对设计，降低批次噪声）。

用法:
  python scripts/rci_f1_batch.py build --source artifacts/rci-f1-abc/source/pilot200_sample.json \
      --out-dir artifacts/rci-f1-abc --n 60
  python scripts/rci_f1_batch.py verify --out-dir artifacts/rci-f1-abc
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict

SEED = "rci-f1-abc-v1"
PACKAGE_CONTRACT_VERSION = "rci-f1-wp/1.0"
AGENTS_PER_LANE = {"B": 20, "C": 20}


def h(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def doc_id(doc: dict) -> str:
    return "doc:" + h(doc["repo"], doc["path"], doc["sha256"])[:16]


def load_docs(source: str) -> list[dict]:
    payload = json.load(open(source, encoding="utf-8"))
    docs = payload["documents"] if isinstance(payload, dict) else payload
    if len(docs) < 60:
        raise SystemExit(f"source sample too small: {len(docs)}")
    return docs


def hamilton(cell_sizes: dict[str, int], n: int) -> dict[str, int]:
    """最大余数法分配，每非空单元保底 1 席。"""
    cells = {k: v for k, v in cell_sizes.items() if v > 0}
    quota = {k: n * v / sum(cells.values()) for k, v in cells.items()}
    alloc = {k: max(1, int(q)) for k, q in quota.items()}
    # 保底 1 席可能已超额，先把超出部分按小数余数从小到大回收
    while sum(alloc.values()) > n:
        k = min((k for k in alloc if alloc[k] > 1), key=lambda k: (quota[k] - alloc[k], k))
        alloc[k] -= 1
    remainders = sorted(
        ((quota[k] - alloc[k], k) for k in alloc), key=lambda t: (-t[0], t[1])
    )
    i = 0
    while sum(alloc.values()) < n:
        alloc[remainders[i % len(remainders)][1]] += 1
        i += 1
    return alloc


def select_within_stratum(docs: list[dict], k: int) -> list[dict]:
    """S3+S4: 哈希排序后按 repo 轮转取前 k 席。"""
    ordered = sorted(docs, key=lambda d: h(SEED, d["repo"], d["path"]))
    buckets: dict[str, list[dict]] = defaultdict(list)
    for d in ordered:
        buckets[d["repo"]].append(d)
    repo_order = sorted(buckets, key=lambda r: (h(SEED, "repo", r), r))
    picked: list[dict] = []
    while len(picked) < k:
        progressed = False
        for repo in repo_order:
            if not buckets[repo]:
                continue
            picked.append(buckets[repo].pop(0))
            progressed = True
            if len(picked) == k:
                break
        if not progressed:
            break
    return picked


def build(source: str, out_dir: str, n: int = 60) -> dict:
    docs = load_docs(source)
    cells: dict[str, list[dict]] = defaultdict(list)
    for d in docs:
        cells[f"{d['content_type']}|{d['tier']}"].append(d)
    alloc = hamilton({k: len(v) for k, v in cells.items()}, n)

    selected: list[dict] = []
    for cell in sorted(cells):
        for d in select_within_stratum(cells[cell], alloc[cell]):
            selected.append(
                {
                    "doc_id": doc_id(d),
                    "repo": d["repo"],
                    "path": d["path"],
                    "sha256": d["sha256"],
                    "chars": d["chars"],
                    "content_type": d["content_type"],
                    "tier": d["tier"],
                    "stratum": cell,
                    "select_key": h(SEED, d["repo"], d["path"])[:16],
                }
            )
    selected.sort(key=lambda d: (d["stratum"], d["select_key"]))
    if len(selected) != n:
        raise SystemExit(f"selected {len(selected)} != {n}")

    batch_digest = h(*[f"{d['doc_id']}:{d['sha256']}" for d in selected])
    batch = {
        "anchor": "KBM-RCI-F1-ABC",
        "version": SEED,
        "n": n,
        "source": {
            "path": os.path.relpath(source, out_dir + "/.."),
            "sha256": h_open(source),
            "upstream_mission": 15462,
            "upstream_sample": "knowledge/rci-pilot200/sample.json",
        },
        "design": {
            "stratification": "content_type x tier (Hamilton largest remainder, min 1/stratum)",
            "within_stratum": "sha256(seed|repo|path) asc, repo round-robin",
            "pairing": "B and C share identical doc->package mapping",
        },
        "allocation": alloc,
        "observed": {
            "by_type": count(selected, "content_type"),
            "by_tier": count(selected, "tier"),
            "by_repo": count(selected, "repo"),
            "cells_covered": len({d["stratum"] for d in selected}),
            "repos_covered": len({d["repo"] for d in selected}),
        },
        "digest": batch_digest,
        "documents": selected,
    }

    packages = build_packages(selected)
    os.makedirs(out_dir, exist_ok=True)
    write_json(os.path.join(out_dir, "batch60.json"), batch)
    write_json(
        os.path.join(out_dir, "tk_work_packages.json"),
        {
            "anchor": "KBM-RCI-F1-ABC",
            "contract_version": PACKAGE_CONTRACT_VERSION,
            "batch_digest": batch_digest,
            "n_documents": n,
            "lanes": {"A": 1, "B": AGENTS_PER_LANE["B"], "C": AGENTS_PER_LANE["C"]},
            "packages": packages,
        },
    )
    return {"batch": batch, "packages": packages}


def build_packages(docs: list[dict]) -> list[dict]:
    """A=1x60；B/C=20x3，B 与 C 映射一致（配对）。"""
    ordered = sorted(docs, key=lambda d: d["doc_id"])
    pkgs: list[dict] = []

    pkgs.append(
        pkg_row("A", 1, "A01", [d["doc_id"] for d in ordered], docs, review="none", skills="none")
    )
    for slot in range(1, AGENTS_PER_LANE["B"] + 1):
        # 轮转分配：包内尽量跨分层（stratum 交错）
        chunk = [d for i, d in enumerate(ordered) if i % AGENTS_PER_LANE["B"] == slot - 1]
        ids = [d["doc_id"] for d in chunk]
        pid = f"B{slot:02d}"
        pkgs.append(pkg_row("B", slot, pid, ids, docs, review="none", skills="none"))
        pkgs.append(
            pkg_row("C", slot, f"C{slot:02d}", ids, docs, review="independent+skills", skills="v1")
        )
    return pkgs


def pkg_row(lane, slot, pid, ids, docs, review, skills) -> dict:
    by_doc = {d["doc_id"]: d for d in docs}
    return {
        "package_id": f"rci-f1-{lane}-{pid}",
        "lane": lane,
        "agent_slot": slot,
        "task_type": "01-05",  # 登记/解析/抽取/审核/综合（按 SPEC 工序号）
        "doc_ids": ids,
        "n_docs": len(ids),
        "strata": sorted({by_doc[i]["stratum"] for i in ids}),
        "contract_version": PACKAGE_CONTRACT_VERSION,
        "independent_review": review,
        "skills": skills,
        "status": "defined",
        "gates": {
            "structure": "pending",
            "evidence": "pending",
            "semantic": "pending" if review != "none" else "not_required_by_design",
        },
        "cost": {"tokens": None, "compute_core_seconds": None, "wall_seconds": None},
        "mission_id": None,
    }


def count(rows: list[dict], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        out[r[key]] = out.get(r[key], 0) + 1
    return dict(sorted(out.items()))


def h_open(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def write_json(path: str, obj) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")


def verify(out_dir: str) -> dict:
    """机器校验：覆盖/配对/一致性。返回检查结果；任一失败抛 AssertionError。"""
    batch = json.load(open(os.path.join(out_dir, "batch60.json"), encoding="utf-8"))
    wps = json.load(open(os.path.join(out_dir, "tk_work_packages.json"), encoding="utf-8"))
    docs = batch["documents"]
    ids = {d["doc_id"] for d in docs}
    checks = {}

    checks["n_docs_60"] = len(docs) == 60
    checks["doc_ids_unique"] = len(ids) == len(docs)
    checks["digest_matches"] = batch["digest"] == h(
        *[f"{d['doc_id']}:{d['sha256']}" for d in docs]
    )
    checks["cells_covered_12"] = batch["observed"]["cells_covered"] == 12
    checks["repos_covered_15"] = batch["observed"]["repos_covered"] == 15

    lanes = defaultdict(list)
    for p in wps["packages"]:
        lanes[p["lane"]].extend(p["doc_ids"])
    for lane, expect in (("A", 1), ("B", 20), ("C", 20)):
        checks[f"lane_{lane}_packages_{expect}"] = (
            len([p for p in wps["packages"] if p["lane"] == lane]) == expect
        )
        checks[f"lane_{lane}_covers_batch_once"] = sorted(lanes[lane]) == sorted(ids)

    bmap = {p["agent_slot"]: p["doc_ids"] for p in wps["packages"] if p["lane"] == "B"}
    cmap = {p["agent_slot"]: p["doc_ids"] for p in wps["packages"] if p["lane"] == "C"}
    checks["bc_pairing_identical"] = bmap == cmap
    checks["bc_pkg_sizes_3"] = all(len(v) == 3 for v in bmap.values())
    checks["wp_batch_digest_matches"] = wps["batch_digest"] == batch["digest"]
    failed = [k for k, v in checks.items() if not v]
    result = {"checks": checks, "passed": not failed, "failed": failed,
              "batch_digest": batch["digest"]}
    if failed:
        raise AssertionError(json.dumps(result, ensure_ascii=False))
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--source", required=True)
    b.add_argument("--out-dir", required=True)
    b.add_argument("--n", type=int, default=60)
    v = sub.add_parser("verify")
    v.add_argument("--out-dir", required=True)
    args = ap.parse_args()
    if args.cmd == "build":
        out = build(args.source, args.out_dir, args.n)
        print(json.dumps({"batch_digest": out["batch"]["digest"],
                          "observed": out["batch"]["observed"],
                          "packages": len(out["packages"])}, ensure_ascii=False, indent=1))
        print(json.dumps(verify(args.out_dir), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(verify(args.out_dir), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()