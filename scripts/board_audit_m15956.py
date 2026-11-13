#!/usr/bin/env python3
"""Board cross-audit of m15956 (KBM-TKC-DOC-SYNC round 2) — receipt check.

非重做：只核验被审单交付物的三件套（run_artifacts / 数值对照 / repro_cmd）
是否真存在、可复现，并把每一条结论绑到原始工件。

    python scripts/board_audit_m15956.py                 # 生成 artifacts/board-audit/m15956/
    python scripts/board_audit_m15956.py --audited DIR   # 指定被审工作树

输出（audit_summary.json 的每项都带 command/exit/stdout 原文，可逐条复核）：
  * repro：4 条复现命令（doc-sync / stats / boundary / pytest）
  * artifacts：工件存在性 + sha256
  * structure：doc-sync 谓词分布（含自指条数）、stats 三口径、boundary 违规数
  * claims：被审单 headline 的每条数字声明 vs 本次实测
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "artifacts" / "board-audit" / "m15956"
DEFAULT_AUDITED = Path("/root/tp-agent/work/m15956")
AUDIT_MISSION = 15963
ANCHOR = "KBM-TKC-DOC-SYNC"

#: 被审单 headline 的数字声明（原文摘录，逐条与实测对账）
CLAIMED = [
    {"key": "doc_sync_pass", "claim": "文档-实现漂移门 9/9 PASS", "expect": "9/9"},
    {"key": "stats_raw", "claim": "原始记录 30443", "expect": 30443},
    {"key": "stats_pending", "claim": "待评审 KO 10166", "expect": 10166},
    {"key": "stats_governed", "claim": "经治理 KO 0", "expect": 0},
    {"key": "boundary_violations", "claim": "61 处核心违规", "expect": 61},
    {"key": "boundary_critical", "claim": "A级 6 处", "expect": 6},
    {"key": "pytest_passed", "claim": "test_ke_proto+test_ke_api 55 passed", "expect": 55},
]


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run(cmd: list[str], cwd: Path, timeout: int = 600) -> dict:
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return {"cmd": " ".join(cmd), "cwd": str(cwd), "exit": r.returncode,
                "stdout_tail": "\n".join(r.stdout.strip().splitlines()[-12:]),
                "stderr_tail": "\n".join(r.stderr.strip().splitlines()[-6:])}
    except subprocess.TimeoutExpired:
        return {"cmd": " ".join(cmd), "cwd": str(cwd), "exit": "timeout", "stdout_tail": "", "stderr_tail": ""}


def artefacts(aud: Path) -> dict:
    rels = ["docs/ke/doc-sync-report.json", "docs/ke/doc-sync-report.md",
            "docs/ke/stats.json", "docs/ke/stats.md",
            "docs/ke/boundary-audit.json", "docs/ke/boundary-audit.md",
            "docs/ke/figures/doc-sync-stats.png",
            "docs/ke/m8802-acceptance.md", "scripts/tk_doc_sync.py",
            "scripts/tk_stats.py", "scripts/tk_boundary_audit.py"]
    out = {}
    for rel in rels:
        p = aud / rel
        out[rel] = {"exists": p.is_file(), "bytes": p.stat().st_size if p.is_file() else 0,
                    "sha256": sha256(p) if p.is_file() else None}
    return out


def structure(aud: Path) -> dict:
    man = json.loads((aud / "docs/ke/doc-sync-manifest.json").read_text())
    preds: dict[str, int] = {}
    self_ref = []
    for c in man["claims"]:
        kind, arg = c["impl"]
        preds[kind] = preds.get(kind, 0) + 1
        if kind == "file_exists" and arg.startswith("docs/"):
            self_ref.append({"doc": c["doc"], "claim": c["text"], "predicate": f"{kind}({arg})"})
    stats = json.loads((aud / "docs/ke/stats.json").read_text())
    bnd = json.loads((aud / "docs/ke/boundary-audit.json").read_text())
    critical_names = {"export.py", "contract.py", "migrate.py", "ingest_client.py"}
    crit = [v for v in bnd["core_violations"] if Path(v["path"]).name in critical_names]
    return {
        "doc_sync": {"claims": len(man["claims"]), "predicates": preds,
                     "self_referential": self_ref,
                     "note": "自指=文档声明某能力已实现、谓词只查该文档/其产物自身是否存在，"
                             "不构成文档-实现一致性证据"},
        "stats": {"total": stats["total"], "digest": stats["digest"]},
        "boundary": {"core_files_scanned": bnd["core_files_scanned"],
                     "core_violations": len(bnd["core_violations"]),
                     "critical_files": len(crit),
                     "critical_term_hits": sum(len(v["terms"]) for v in crit),
                     "verdict": bnd["verdict"]},
    }


def parse_stdout(runs: dict) -> dict:
    import re
    doc = re.search(r"DOC-SYNC (\d+)/(\d+)", runs["doc_sync"].get("stdout_tail", ""))
    bnd = re.search(r"core_violations=(\d+)", runs["boundary"].get("stdout_tail", ""))
    pt = re.search(r"(\d+) passed", runs["pytest_core"].get("stdout_tail", "") + runs["pytest_core"].get("stderr_tail", ""))
    mig = re.search(r"(\d+) failed", runs["pytest_migrate"].get("stdout_tail", "") + runs["pytest_migrate"].get("stderr_tail", ""))
    return {
        "doc_sync_pass": f"{doc.group(1)}/{doc.group(2)}" if doc else None,
        "stats_digest_match": "PASS" if "STATS PASS" in runs["stats"].get("stdout_tail", "") else "FAIL",
        "boundary_violations": int(bnd.group(1)) if bnd else None,
        "boundary_check_exit": runs["boundary"]["exit"],
        "pytest_passed": int(pt.group(1)) if pt else None,
        "migrate_failed": int(mig.group(1)) if mig else None,
    }


def reconcile(measured: dict, struct: dict) -> list[dict]:
    got = {
        "doc_sync_pass": measured["doc_sync_pass"],
        "stats_raw": struct["stats"]["total"]["raw_records"],
        "stats_pending": struct["stats"]["total"]["pending_ko"],
        "stats_governed": struct["stats"]["total"]["governed_ko"],
        "boundary_violations": struct["boundary"]["core_violations"],
        "boundary_critical": struct["boundary"]["critical_files"],
        "pytest_passed": measured["pytest_passed"],
    }
    rows = []
    for c in CLAIMED:
        g = got.get(c["key"])
        rows.append({**c, "got": g, "match": str(g) == str(c["expect"])})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audited", default=str(DEFAULT_AUDITED))
    args = ap.parse_args()
    aud = Path(args.audited).resolve()
    if not (aud / "scripts/tk_doc_sync.py").is_file():
        print(f"NOT FOUND: {aud}/scripts/tk_doc_sync.py", file=sys.stderr)
        return 2

    py = sys.executable
    runs = {
        "doc_sync": run([py, "scripts/tk_doc_sync.py", "--check"], aud, 180),
        "stats": run([py, "scripts/tk_stats.py", "--check"], aud, 180),
        "boundary": run([py, "scripts/tk_boundary_audit.py", "--check"], aud, 300),
        "pytest_core": run([py, "-m", "pytest", "tests/test_ke_proto.py", "tests/test_ke_api.py", "-q"], aud, 900),
        "pytest_migrate": run([py, "-m", "pytest", "tests/test_ke_migrate.py", "-q"], aud, 900),
    }
    art = artefacts(aud)
    struct = structure(aud)
    measured = parse_stdout(runs)
    summary = {
        "schema": "board-audit/1",
        "audit_mission": AUDIT_MISSION,
        "audited_worktree": str(aud),
        "anchor_slug": ANCHOR,
        "note": "基准裁判=tensor_benchmark_cases(anchor_slug)；本次查询 0 行 → 本单无登记基准，"
                "级别上限受限于此（L4 需 ref vs got + 误差）",
        "runs": runs,
        "measured": measured,
        "artifacts": art,
        "structure": struct,
        "claims_vs_measured": reconcile(measured, struct),
    }
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / "audit_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n")
    mism = [r for r in summary["claims_vs_measured"] if not r["match"]]
    print("BOARD-AUDIT m15956")
    print(" doc_sync:", measured["doc_sync_pass"], "| stats:", measured["stats_digest_match"],
          "| boundary:", measured["boundary_violations"], "violations (exit",
          measured["boundary_check_exit"], ")")
    print(" pytest core:", measured["pytest_passed"], "passed | migrate:", measured["migrate_failed"], "failed")
    print(" claims match:", len(summary["claims_vs_measured"]) - len(mism), "/", len(summary["claims_vs_measured"]),
          "| mismatches:", [m["claim"] + f" (got {m['got']})" for m in mism])
    print(" ->", (OUTDIR / "audit_summary.json").relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())