#!/usr/bin/env python3
"""kb_consumption_entry —— KB 消费研究一键复算入口（m15255 / KBM-CONSUME-W1）

一条命令把「诊断 → 检索基准 → 消费快照 → 单测 → 图」全跑一遍，并把每一步的
命令/退出码/耗时/日志/工件 sha256 写进 ``runs/kb_consumption_<utc>/manifest.json``。
判据：任一步非零退出 → manifest.verdict=FAIL（honest FAIL，工件照样写全）。

LLM 的 A/B 实验默认不跑（要花钱/时间），用 ``--with-ab [--reps N]`` 显式开启；
已跑过的 A/B 目录会作为「最近一次 A/B 工件」被 manifest 收录（sha256 一起进账）。

用法：
  python3 scripts/kb_consumption_entry.py                  # 全离线可跑（DB 不可达时 audit 降级）
  python3 scripts/kb_consumption_entry.py --with-ab --reps 4
  python3 scripts/kb_consumption_entry.py --no-db --no-figures
产出：
  runs/kb_consumption_<utc>/{manifest.json,logs/*.log}
  artifacts/kb_consumption/{audit.json,summary.json,snapshots.jsonl}
  artifacts/kb_retrieval/{bench.json,bench.md,cards_snapshot.json,holdout/*}
  artifacts/kb_consumption/kb_consumption.png
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
PY = sys.executable


def sha256(path: pathlib.Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def git_head() -> str:
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() or "unknown"


def latest_ab() -> dict | None:
    dirs = sorted((ROOT / "runs").glob("kb_ab_*"), key=lambda p: p.name)
    if not dirs:
        return None
    d = dirs[-1]
    summary = d / "summary.json"
    if not summary.exists():
        return None
    body = json.loads(summary.read_text())
    return {"run_dir": str(d.relative_to(ROOT)), "prereg_sha256": body.get("prereg_sha256"),
            "arms": body.get("arms"), "cells": body.get("cells"),
            "retrieval": body.get("retrieval"),
            "sha256": {f.name: sha256(f) for f in sorted(d.iterdir()) if f.is_file()}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--with-ab", action="store_true", help="跑 LLM A/B（默认跳过）")
    ap.add_argument("--reps", type=int, default=4)
    ap.add_argument("--no-db", action="store_true", help="消费快照不写 Postgres")
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--skip-pytest", action="store_true")
    a = ap.parse_args()

    utc = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    run = ROOT / "runs" / f"kb_consumption_{utc}"
    (run / "logs").mkdir(parents=True, exist_ok=True)

    steps = []

    def step(name: str, cmd: list[str], outputs: list[str], expect_ok: bool = True):
        t0 = time.time()
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=3600)
        dur = round(time.time() - t0, 1)
        log = run / "logs" / f"{name}.log"
        log.write_text(f"$ {' '.join(cmd)}\n\n[stdout]\n{proc.stdout}\n[stderr]\n{proc.stderr}")
        rec = {"step": name, "cmd": " ".join(cmd), "exit": proc.returncode, "duration_s": dur,
               "log": str(log.relative_to(ROOT)),
               "outputs": {o: sha256(ROOT / o) for o in outputs},
               "ok": (proc.returncode == 0) if expect_ok else True}
        steps.append(rec)
        print(f"[{name}] exit={proc.returncode} {dur}s -> {rec['log']}")
        return rec

    step("audit", [PY, "scripts/kb_consume_audit.py", "--out", "artifacts/kb_consumption"],
         ["artifacts/kb_consumption/audit.json", "artifacts/kb_consumption/summary.json"])
    step("bench_v1", [PY, "scripts/kb_retrieve_bench.py"],
         ["artifacts/kb_retrieval/bench.json", "artifacts/kb_retrieval/bench.md",
          "artifacts/kb_retrieval/cards_snapshot.json"])
    step("bench_holdout", [PY, "scripts/kb_retrieve_bench.py",
                           "--gold", "benchmarks/kb_retrieval_holdout_v1.json",
                           "--cards", "artifacts/kb_retrieval/cards_snapshot.json",
                           "--out", "artifacts/kb_retrieval/holdout"],
         ["artifacts/kb_retrieval/holdout/bench.json", "artifacts/kb_retrieval/holdout/bench.md"])
    if a.with_ab:
        step("ab", [PY, "scripts/kb_ab_experiment.py", "--reps", str(a.reps)], [])
    step("snapshot", [PY, "scripts/kb_consumption_snapshot.py"] + (["--no-db"] if a.no_db else []),
         ["artifacts/kb_consumption/snapshots.jsonl"])
    if not a.skip_pytest:
        step("pytest", [PY, "-m", "pytest", "tests/test_kb_consume.py",
                        "tests/test_kb_consumption_scripts.py", "-q"], [])
    if not a.no_figures:
        step("figures", [PY, "scripts/kb_consumption_figures.py"],
             ["artifacts/kb_consumption/kb_consumption.png"])

    # 交付工件副本：artifacts/ 被 .gitignore + 推送门禁丢弃，故关键工件必须在 runs/ 留一份
    # （否则达标复核只看到脚本、看不到"真跑过的数字"）。
    copies = {}
    for rel in ("artifacts/kb_consumption/audit.json", "artifacts/kb_consumption/summary.json",
                "artifacts/kb_consumption/snapshots.jsonl", "artifacts/kb_consumption/kb_consumption.png",
                "artifacts/kb_retrieval/bench.json", "artifacts/kb_retrieval/bench.md",
                "artifacts/kb_retrieval/cards_snapshot.json",
                "artifacts/kb_retrieval/holdout/bench.json", "artifacts/kb_retrieval/holdout/bench.md"):
        src = ROOT / rel
        if src.exists():
            # 不能放 "copies/artifacts/..."：.gitignore 的 `artifacts/` 在任何层级都生效，
            # 会被连同推送门禁一起丢掉（本轮踩过）。改扁平命名 evidence/ 下。
            dst = run / "evidence" / rel.replace("artifacts/", "").replace("/", "__")
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copies[rel] = {"worktree_path": rel, "path": str(dst.relative_to(ROOT)),
                           "sha256": sha256(dst)}

    failed = [s["step"] for s in steps if not s["ok"]]
    bench = {}
    for tag, path in (("v1", "artifacts/kb_retrieval/bench.json"),
                      ("holdout", "artifacts/kb_retrieval/holdout/bench.json")):
        p = ROOT / path
        if p.exists():
            b = json.loads(p.read_text())
            bench[tag] = {k: b.get(k) for k in ("verdict", "verdicts", "prereg_sha256",
                                                "cards_n", "cards_source", "dsn_error")} | {
                "ref": {k: b["ref"][k] for k in ("precision_at_1", "recall_at_5", "mrr_at_5")},
                "got": {k: b["got"][k] for k in ("precision_at_1", "recall_at_5", "mrr_at_5")}}
    audit_summary = ROOT / "artifacts/kb_consumption/summary.json"
    manifest = {
        "schema": "kb-consumption-run/1",
        "mission": 15255, "anchor": "KBM-CONSUME-W1",
        "git_head": git_head(), "utc": utc, "python": sys.version.split()[0],
        "verdict": "PASS" if not failed else "FAIL",
        "failed_steps": failed,
        "steps": steps,
        "artifact_copies": copies,
        "bench": bench,
        "audit": json.loads(audit_summary.read_text()) if audit_summary.exists() else None,
        "ab_latest": latest_ab(),
        "repro_cmd": ("python3 scripts/kb_consumption_entry.py"
                      + (" --with-ab --reps " + str(a.reps) if a.with_ab else "")),
    }
    (run / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    print(json.dumps({k: manifest[k] for k in ("verdict", "failed_steps", "bench")},
                     ensure_ascii=False, indent=1))
    print("manifest:", (run / "manifest.json").relative_to(ROOT))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())