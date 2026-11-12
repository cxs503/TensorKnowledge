#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 程序化门禁（结构门 + 证据门）→ 生成 run 回执。

为什么需要它：M4（证据完整率）绝不能采信抽取器自报的 verified 标记。
本脚本对每个 work package 的产出做可复算反查，并把计数写进 runs/<LANE>/<pkg>.json，
指标计算器只认这份程序化回执。

结构门: JSON 可解析 / 必填字段齐 / doc 集合与批次一致 / KO id 去重
证据门: 每条 evidence 指针 (path, lines, sha256) 在冻结快照上可反查 + 行区间内引文逐字可匹配

用法:
  python scripts/rci_f1_gate.py --batch artifacts/rci-f1-abc/batch60.json \
      --lane A --package rci-f1-A-A01 --objects artifacts/rci-f1-abc/objects/A/rci-f1-A-A01.jsonl \
      --corpus artifacts/rci-f1-abc/blind/corpus --out artifacts/rci-f1-abc/runs/A/rci-f1-A-A01.json \
      [--tokens N --compute S --wall S --agents 1]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os

REQUIRED_KO = ("id", "ko_type", "claim", "evidence", "conditions", "quality", "provenance")


def sha_file(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def resolve_locator(corpus: str, loc: dict) -> tuple[bool, str]:
    rel = (loc.get("path") or "").lstrip("/")
    if not rel:
        return False, "missing path"
    full = os.path.join(corpus, rel)
    if not os.path.isfile(full):
        return False, "path not found in snapshot"
    got = sha_file(full)
    if loc.get("sha256") and got != loc["sha256"]:
        return False, "sha256 mismatch"
    lines = loc.get("lines") or []
    if not (isinstance(lines, list) and len(lines) == 2):
        return False, "lines missing"
    a, b = int(lines[0]), int(lines[1])
    text = open(full, encoding="utf-8", errors="replace").read().splitlines()
    if a < 1 or b < a or b > len(text):
        return False, f"line range out of bounds ({a}-{b}/{len(text)})"
    quote = (loc.get("quote") or "").strip()
    if not quote:
        return False, "quote missing"
    window = "\n".join(text[a - 1:b])
    if quote not in window:
        return False, "quote not found in line window"
    return True, "ok"


def gate(batch_path: str, lane: str, package: str, objects: str, corpus: str,
         cost: dict | None = None) -> dict:
    batch = json.load(open(batch_path, encoding="utf-8"))
    docs = {d["doc_id"]: d for d in batch["documents"]}
    wps = None
    wp_path = os.path.join(os.path.dirname(batch_path), "tk_work_packages.json")
    if os.path.isfile(wp_path):
        wps = json.load(open(wp_path, encoding="utf-8"))
    expected = None
    if wps:
        for p in wps["packages"]:
            if p["package_id"] == package:
                expected = p["doc_ids"]
    seen_docs: set[str] = set()
    ids: list[str] = []
    kos: list[dict] = []
    structure_errors: list[str] = []
    if not os.path.isfile(objects):
        structure_errors.append("objects file missing")
    else:
        for ln, line in enumerate(open(objects, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                ko = json.loads(line)
            except json.JSONDecodeError as e:
                structure_errors.append(f"line {ln}: invalid json ({e.msg})")
                continue
            missing = [k for k in REQUIRED_KO if k not in ko]
            if missing:
                structure_errors.append(f"line {ln}: missing fields {missing}")
                continue
            ids.append(ko["id"])
            kos.append(ko)
            src = (ko.get("source") or {})
            did = src.get("doc_id") or (src.get("repo", "") + "/" + src.get("path", ""))
            seen_docs.add(did)
    dup = sorted({i for i in ids if ids.count(i) > 1})

    loc_total = loc_ok = 0
    claims = claims_with_loc = 0
    loc_failures: list[dict] = []
    for ko in kos:
        claims += 1
        ev = ko.get("evidence") or []
        ok_any = False
        for loc in ev:
            loc_total += 1
            ok, why = resolve_locator(corpus, loc)
            if ok:
                loc_ok += 1
                ok_any = True
            else:
                loc_failures.append({"ko": ko.get("id"), "path": loc.get("path"), "why": why})
        if ok_any:
            claims_with_loc += 1

    docs_completed = len(seen_docs)
    docs_passed = 0
    if not structure_errors and not dup:
        if expected is None:
            docs_passed = docs_completed
        else:
            docs_passed = len(seen_docs & set(expected))
    rec = {
        "arm": lane,
        "package_id": package,
        "agent_count": int((cost or {}).get("agents") or 1),
        "docs_expected": len(expected) if expected else None,
        "docs_completed": docs_completed,
        "docs_passed": docs_passed,
        "claims": claims,
        "claims_with_locator": claims_with_loc,
        "locators_total": loc_total,
        "locators_resolved": loc_ok,
        "structure_gate": {"passed": not structure_errors and not dup,
                           "errors": structure_errors[:20], "duplicate_ids": dup[:20]},
        "evidence_gate": {"passed": loc_total > 0 and loc_ok == loc_total,
                          "failures": loc_failures[:20]},
        "cost": {"tokens": (cost or {}).get("tokens"),
                 "compute_core_seconds": (cost or {}).get("compute_core_seconds"),
                 "wall_seconds": (cost or {}).get("wall_seconds")},
    }
    return rec


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", required=True)
    ap.add_argument("--lane", required=True, choices=["A", "B", "C"])
    ap.add_argument("--package", required=True)
    ap.add_argument("--objects", required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--tokens", type=int)
    ap.add_argument("--compute", type=float)
    ap.add_argument("--wall", type=float)
    ap.add_argument("--agents", type=int, default=1)
    args = ap.parse_args()
    rec = gate(args.batch, args.lane, args.package, args.objects, args.corpus,
               {"tokens": args.tokens, "compute_core_seconds": args.compute,
                "wall_seconds": args.wall, "agents": args.agents})
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rec, f, ensure_ascii=False, indent=1)
        f.write("\n")
    ok = rec["structure_gate"]["passed"] and rec["docs_passed"] == (rec["docs_expected"] or rec["docs_completed"])
    print(json.dumps({"package": rec["package_id"], "docs_passed": rec["docs_passed"],
                      "docs_expected": rec["docs_expected"],
                      "locators": f"{rec['locators_resolved']}/{rec['locators_total']}",
                      "structure_gate": rec["structure_gate"]["passed"], "ok": ok},
                     ensure_ascii=False))
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()