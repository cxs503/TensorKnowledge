#!/usr/bin/env python3
"""Documentation-implementation drift gate (KBM-TKC-DOC-SYNC).

每条文档状态声明绑定一个机器谓词（文件存在/端点存在/生成统计数字），
并同时核对文档措辞是否与实现一致（文档说 planned 但实现已存在 = 漂移，
文档说 done 但实现缺失 = 虚报）。清单是数据：docs/ke/doc-sync-manifest.json。

    python scripts/tk_doc_sync.py            # 评估 + 写 docs/ke/doc-sync-report.{json,md}
    python scripts/tk_doc_sync.py --check    # 全绿 exit 0，否则 1
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs" / "ke" / "doc-sync-manifest.json"
OUT_JSON = ROOT / "docs" / "ke" / "doc-sync-report.json"
OUT_MD = ROOT / "docs" / "ke" / "doc-sync-report.md"


def _exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def _endpoint_present(path: str) -> bool:
    txt = (ROOT / "ke" / "api.py").read_text(encoding="utf-8")
    return f'"{path}"' in txt or f"'{path}'" in txt


def _test_collected(node: str) -> bool:
    r = subprocess.run([sys.executable, "-m", "pytest", node, "--collect-only", "-q"],
                       cwd=ROOT, capture_output=True, text=True)
    return r.returncode == 0 and "no tests ran" not in r.stdout


def _stats(expr: str) -> int:
    p = ROOT / "docs" / "ke" / "stats.json"
    if not p.exists():
        return -1
    scope, key = expr.split(".")
    return int(json.loads(p.read_text())["scopes"][scope].get(key, -1))


IMPL = {"file_exists": _exists, "endpoint_present": _endpoint_present,
        "test_collected": _test_collected, "stats": _stats}


def evaluate(manifest: dict) -> dict:
    rows = []
    for c in manifest["claims"]:
        doc_path = ROOT / c["doc"]
        doc_txt = doc_path.read_text(encoding="utf-8") if doc_path.exists() else ""
        present = c["text"] in doc_txt
        # 文档状态：同一行出现 [x] 或 "done" 记为声明实现
        line = next((ln for ln in doc_txt.splitlines() if c["text"] in ln), "")
        is_checkbox = line.lstrip().startswith("- [")
        doc_done = ("[x]" in line) if is_checkbox else bool(line)
        pred, arg = c["impl"]
        try:
            impl_val = IMPL[pred](arg)
        except Exception as exc:  # noqa: BLE001
            impl_val = f"ERROR:{exc}"
        if pred == "stats":
            impl_ok = impl_val == c.get("expect", 1)
        else:
            impl_ok = impl_val is True
        ok = bool(present) and (doc_done == c["done"]) and (impl_ok == c["done"] if c["done"] else True)
        rows.append({**c, "doc_present": present, "doc_says_done": doc_done,
                     "impl_val": impl_val, "ok": ok})
    return {"schema": "tk-doc-sync/1", "total": len(rows),
            "passed": sum(r["ok"] for r in rows),
            "failed": sum(not r["ok"] for r in rows), "rows": rows}


def render_md(rep: dict) -> str:
    lines = ["# 文档-实现状态对齐核对（机器生成，勿手改）", "",
             f"共 {rep['total']} 条状态声明：通过 {rep['passed']}，失败 {rep['failed']}。", "",
             "| 文档 | 声明 | 文档说已实现 | 实现谓词 | 实测 | 结果 |", "|---|---|---|---|---|---|"]
    for r in rep["rows"]:
        lines.append(f"| {r['doc']} | {r['text']} | {r['doc_says_done']} | "
                     f"`{r['impl'][0]}({r['impl'][1]})` | {r['impl_val']} | "
                     f"{'PASS' if r['ok'] else 'FAIL'} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    rep = evaluate(json.loads(MANIFEST.read_text(encoding="utf-8")))
    if args.check:
        print(f"DOC-SYNC {rep['passed']}/{rep['total']} pass")
        for r in rep["rows"]:
            if not r["ok"]:
                print(f"  FAIL {r['doc']}: {r['text']} doc_done={r['doc_says_done']} impl={r['impl_val']}")
        return 0 if rep["failed"] == 0 else 1
    OUT_JSON.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n")
    OUT_MD.write_text(render_md(rep))
    print(f"DOC-SYNC {rep['passed']}/{rep['total']} -> {OUT_MD.relative_to(ROOT)}")
    return 0 if rep["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
