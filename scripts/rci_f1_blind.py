#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 盲审协议工件生成器（QR 式独立裁 + 人工≥30 交叉验证）。

做三件事（全部确定性、可复算）：
  1. prepare  : 从三臂知识对象工件生成**去臂标识**的盲审包（sample_id 哈希化、
                抹除 lane/package_id/model/生产者解释），把冻结快照落盘作证据基准；
                映射写入 blind_key.json 并按预注册记录其 sha256（评分齐全后才解封对账）。
  2. human30  : 按臂产量比例分层抽 ≥30 条进人工复核表（交叉验证盲审可靠性）。
  3. ingest   : 收评审回执（sample_id→四字段判定），写 scored.json；缺字段/越界即拒。

盲审只隐藏「臂」，不隐藏「仓/路径」——三臂同批同文档，仓路径不泄露臂归属，
但保留它才能让审核者反查 locator（证据门要求真实可达）。

用法:
  python scripts/rci_f1_blind.py prepare --dir artifacts/rci-f1-abc \
      --objects artifacts/rci-f1-abc/objects --corpus /root/tp-agent/work/m15462/knowledge/rci-pilot200/corpus
  python scripts/rci_f1_blind.py human30 --dir artifacts/rci-f1-abc --n 30
  python scripts/rci_f1_blind.py ingest --dir artifacts/rci-f1-abc --scores /tmp/review_A.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil

ARMS = ["A", "B", "C"]
FIELDS = ["claim_faithful", "locator_resolvable", "conditions_not_invented", "type_fit"]
SEED = "rci-f1-abc-blind-v1"
FORBIDDEN_KEYS = {"lane", "arm", "package_id", "agent_slot", "agent_session_id",
                  "model", "producer_note", "reasoning", "worker_id"}
LEAK_PATTERNS = [r"\blane\b", r"\bpackage_id\b", r"\bagent_slot\b", r"\bko_id\b"]


def h(*parts: str) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def sample_id_for(ko_id: str) -> str:
    return "bs-" + h(SEED, ko_id)[:12]


def load_objects(objects_dir: str) -> list[dict]:
    """objects/<LANE>/<package_id>.jsonl（或 objects.jsonl），每行一个 KO。"""
    out: list[dict] = []
    if not os.path.isdir(objects_dir):
        return out
    for lane in ARMS:
        d = os.path.join(objects_dir, lane)
        if not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            if not name.endswith(".jsonl"):
                continue
            pkg = name[:-6]
            for line in open(os.path.join(d, name), encoding="utf-8"):
                line = line.strip()
                if not line:
                    continue
                ko = json.loads(line)
                ko["_lane"] = lane
                ko["_package_id"] = pkg
                out.append(ko)
    return out


def redact(ko: dict) -> dict:
    """只留审核所需字段；臂/包/模型/解释一律剔除。"""
    src = ko.get("source", {})
    return {
        "ko_type": ko.get("ko_type"),
        "claim": {k: (ko.get("claim") or {}).get(k)
                  for k in ("statement", "claim_form")},
        "evidence": [
            {k: e.get(k) for k in ("path", "lines", "span", "sha256", "quote")}
            for e in (ko.get("evidence") or [])
        ],
        "conditions": {
            "stated_in_source": (ko.get("conditions") or {}).get("stated_in_source"),
            "scope": (ko.get("conditions") or {}).get("scope"),
            "text": (ko.get("conditions") or {}).get("text"),
        },
        "source": {"doc_id": src.get("doc_id") or src.get("path"),
                   "repo": src.get("repo"), "path": src.get("path"),
                   "sha256": src.get("sha256"), "content_type": src.get("content_type")},
    }


def _walk_keys(obj) -> set[str]:
    keys: set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            keys.add(k)
            keys |= _walk_keys(v)
    elif isinstance(obj, list):
        for v in obj:
            keys |= _walk_keys(v)
    return keys


def check_no_leak(item: dict) -> None:
    """结构级去标识检查：禁出现臂/包/模型字段，正文不得出现 lane/package_id 等字样。"""
    bad = _walk_keys(item) & FORBIDDEN_KEYS
    if bad:
        raise AssertionError(f"blind pack leak: forbidden keys {sorted(bad)}")
    blob = json.dumps({k: v for k, v in item.items() if k != "sample_id"}, ensure_ascii=False)
    for pat in LEAK_PATTERNS:
        if re.search(pat, blob):
            raise AssertionError(f"blind pack leak: pattern {pat!r} matched")


def prepare(dir_: str, objects_dir: str, corpus: str | None, seed: str = SEED) -> dict:
    batch = json.load(open(os.path.join(dir_, "batch60.json"), encoding="utf-8"))
    objs = load_objects(objects_dir)
    blind = os.path.join(dir_, "blind")
    os.makedirs(blind, exist_ok=True)

    items, key = [], {}
    for ko in objs:
        sid = sample_id_for(ko["id"])
        it = {"sample_id": sid, **redact(ko)}
        check_no_leak(it)
        items.append(it)
        key[sid] = {"lane": ko["_lane"], "ko_id": ko["id"],
                    "package_id": ko["_package_id"], "_order": h(seed, sid)}
    items.sort(key=lambda x: h(seed, x["sample_id"]))
    for i, it in enumerate(items, 1):
        it["order"] = i

    with open(os.path.join(blind, "pack.json"), "w", encoding="utf-8") as f:
        json.dump({"seed": seed, "n_items": len(items),
                   "batch_digest": batch["digest"], "items": items}, f,
                  ensure_ascii=False, indent=1)
    key_blob = json.dumps({"seed": seed, "key": key}, ensure_ascii=False,
                          sort_keys=True).encode()
    with open(os.path.join(blind, "blind_key.json"), "wb") as f:
        f.write(key_blob)
    key_sha = hashlib.sha256(key_blob).hexdigest()

    # 冻结快照：只拷批次内 60 篇，作为 locator 反查基准
    copied = 0
    if corpus and os.path.isdir(corpus):
        for d in batch["documents"]:
            src = os.path.join(corpus, d["repo"], d["path"])
            dst = os.path.join(blind, "corpus", d["repo"], d["path"])
            if os.path.isfile(src):
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copy2(src, dst)
                got = hashlib.sha256(open(dst, "rb").read()).hexdigest()
                if got != d["sha256"]:
                    raise AssertionError(f"snapshot sha mismatch {d['repo']}/{d['path']}")
                copied += 1

    info = {"n_items": len(items), "n_objects": len(objs), "key_sha256": key_sha,
            "corpus_copied": copied, "seed": seed}
    with open(os.path.join(blind, "prepare_info.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)
    return info


def human30(dir_: str, n: int = 30) -> dict:
    blind = os.path.join(dir_, "blind")
    pack = json.load(open(os.path.join(blind, "pack.json"), encoding="utf-8"))
    key = json.load(open(os.path.join(blind, "blind_key.json"), encoding="utf-8"))["key"]
    by_lane: dict[str, list[str]] = {a: [] for a in ARMS}
    for sid in sorted(key, key=lambda s: h(SEED, "human", s)):
        by_lane.setdefault(key[sid]["lane"], []).append(sid)
    total = sum(len(v) for v in by_lane.values()) or 1
    picked: list[str] = []
    for lane, ids in by_lane.items():
        if not ids or lane not in ARMS:
            continue
        k = max(1, round(n * len(ids) / total))
        picked.extend(ids[:k])
    picked = picked[:n] if len(picked) >= n else picked
    sheet_items = []
    for s in picked:
        row = {"sample_id": s}
        row.update({"human_" + f: None for f in FIELDS})
        sheet_items.append(row)
    sheet = {"n": len(picked), "fields": FIELDS, "items": sheet_items}
    with open(os.path.join(blind, "human30.json"), "w", encoding="utf-8") as f:
        json.dump(sheet, f, ensure_ascii=False, indent=1)
    # 人工复核表（可打印）：盲标识 + 顺序号，不带臂
    order = {it["sample_id"]: it["order"] for it in pack["items"]}
    lines = ["# RCI-F1 人工交叉验证表（≥30 条，逐字段二值判定）", "",
             "对每条：claim 是否忠实原文？locator 是否可达且片段匹配？conditions 是否臆造？KO 类型是否适配？",
             "1=通过，0=不通过。只依据 blind/corpus 冻结快照，不看生产者解释。", "",
             "| order | sample_id | claim_faithful | locator_resolvable | conditions_not_invented | type_fit |",
             "|---|---|---|---|---|---|"]
    for it in sorted(sheet["items"], key=lambda x: order.get(x["sample_id"], 0)):
        lines.append(f"| {order.get(it['sample_id'], '')} | {it['sample_id']} | | | | |")
    with open(os.path.join(blind, "human30_sheet.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    return {"n": len(picked)}


def ingest(dir_: str, scores_path: str, reviewer: str = "blind-reviewer") -> dict:
    blind = os.path.join(dir_, "blind")
    pack_ids = {it["sample_id"] for it in
                json.load(open(os.path.join(blind, "pack.json"), encoding="utf-8"))["items"]}
    payload = json.load(open(scores_path, encoding="utf-8"))
    rows = payload.get("items", payload if isinstance(payload, list) else [])
    out_path = os.path.join(blind, "scored.json")
    prev = {"items": []}
    if os.path.isfile(out_path):
        prev = json.load(open(out_path, encoding="utf-8"))
    by_sid = {r["sample_id"]: r for r in prev.get("items", [])}
    added = 0
    for r in rows:
        sid = r.get("sample_id")
        if sid not in pack_ids:
            raise ValueError(f"unknown sample_id {sid!r}")
        for f in FIELDS:
            v = r.get(f)
            if v not in (0, 1, True, False, None):
                raise ValueError(f"{sid}:{f} must be 0/1, got {v!r}")
        merged = {k: v for k, v in r.items() if k.startswith("human_")}
        row = by_sid.get(sid, {"sample_id": sid})
        row.update({f: (None if r.get(f) is None else int(bool(r.get(f)))) for f in FIELDS})
        row["reviewer"] = r.get("reviewer", reviewer)
        if merged:
            row.update(merged)
        by_sid[sid] = row
        added += 1
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"items": sorted(by_sid.values(), key=lambda x: x["sample_id"])}, f,
                  ensure_ascii=False, indent=1)
    return {"ingested": added, "total_scored": len(by_sid)}


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--dir", required=True)
    p.add_argument("--objects", required=True)
    p.add_argument("--corpus")
    h30 = sub.add_parser("human30")
    h30.add_argument("--dir", required=True)
    h30.add_argument("--n", type=int, default=30)
    ing = sub.add_parser("ingest")
    ing.add_argument("--dir", required=True)
    ing.add_argument("--scores", required=True)
    ing.add_argument("--reviewer", default="blind-reviewer")
    args = ap.parse_args()
    if args.cmd == "prepare":
        print(json.dumps(prepare(args.dir, args.objects, args.corpus), ensure_ascii=False, indent=1))
    elif args.cmd == "human30":
        print(json.dumps(human30(args.dir, args.n), ensure_ascii=False, indent=1))
    else:
        print(json.dumps(ingest(args.dir, args.scores, args.reviewer), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()