#!/usr/bin/env python3
"""Domain-semantics boundary audit (KBM-TKC-DOC-SYNC §④).

VISION 零领域语义硬编码原则的机器检查：

* 知识资产目录（``knowledge/oss-lbm`` / ``knowledge/sediment`` /
  ``knowledge-map/ship-ocean-domain``）里的 **JSON/Markdown 数据** 保留领域内容是
  OK 的 —— 那是知识资产本身。
* **代码**（``ke/`` 核心引擎、``scripts/`` 通用脚本、``tests/``）不得把领域词表
  写死。领域词必须以数据形式（包内 JSON、配置、参数）注入。

审计粒度=逐文件。输出 ``docs/ke/boundary-audit.json`` + ``docs/ke/boundary-audit.md``。
用法::

    python scripts/tk_boundary_audit.py           # 生成工件
    python scripts/tk_boundary_audit.py --check   # 仅核心代码有违规时 exit 1
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSET_DIRS = [ROOT / "knowledge" / "oss-lbm", ROOT / "knowledge" / "sediment",
              ROOT / "knowledge-map" / "ship-ocean-domain"]
CORE_DIRS = [ROOT / "ke", ROOT / "scripts", ROOT / "tests"]
OUT_JSON = ROOT / "docs" / "ke" / "boundary-audit.json"
OUT_MD = ROOT / "docs" / "ke" / "boundary-audit.md"

#: 领域词表（只存在于审计器里，用于检出；不注入被测代码）
TERMS_RAW = ["lattice-boltzmann", "lattice boltzmann", "lbm", "d2q9", "d3q19", "d3q27",
         "shan-chen", "kruger", "lbmpy", "taylor-green", "sediment", "sloshing",
         "ice", "ship", "hydrodynamic"]
CODE_SUFFIXES = {".py", ".sh", ".js", ".ts"}
#: 词边界匹配（避免 service/device 命中 ice、relationship 命中 ship）
TERMS = [re.compile(r"\b" + re.escape(t) + r"\b") for t in TERMS_RAW]


def hits_of(txt: str) -> list[str]:
    low = txt.lower()
    return [rx.pattern.strip("\\b") for rx in TERMS if rx.search(low)]
#: 允许携带领域词的数据/夹具路径（知识资产、试点夹具、抽取工具）
ALLOW = re.compile(r"(^knowledge/|^knowledge-map/|^platform-test/|^tests/fixtures/|"
                   r"^docs/|^artifacts/|^runs/|scripts/(ke_smoke|figures_sediment|"
                   r"build_sediment|generate_m5490|kf_|kb10k|extract))")


def audit() -> dict:
    findings, per_file = [], []
    for base in ASSET_DIRS:
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(ROOT))
            if p.suffix in CODE_SUFFIXES:
                hits = hits_of(p.read_text(errors="ignore"))
                verdict = "NOT_OK" if hits else "OK"
                if hits:
                    findings.append({"path": rel, "kind": "code_in_asset_dir", "terms": hits})
            else:
                verdict = "OK(asset)"
            per_file.append({"path": rel, "verdict": verdict})
    core = []
    for base in CORE_DIRS:
        for p in sorted(base.rglob("*.py")):
            rel = str(p.relative_to(ROOT))
            if ALLOW.search(rel):
                continue
            txt = p.read_text(errors="ignore").lower()
            hits = sorted(hits_of(txt))
            if hits:
                core.append({"path": rel, "terms": hits})
                findings.append({"path": rel, "kind": "core_code_hardcode", "terms": hits})
    return {"schema": "tk-boundary-audit/1",
            "rule": "知识资产数据保留领域内容 OK；核心代码硬编码领域词 NOT OK",
            "asset_files": len(per_file), "asset_code_files": sum(
                1 for f in per_file if f["verdict"] in ("OK", "NOT_OK")),
            "core_files_scanned": sum(1 for b in CORE_DIRS for _ in b.rglob("*.py")),
            "core_violations": core, "findings": findings,
            "verdict": "PASS" if not core else "FAIL"}


def render_md(rep: dict) -> str:
    lines = ["# 领域语义边界审计（机器生成）", "",
             f"- 规则：{rep['rule']}",
             f"- 知识资产目录文件：{rep['asset_files']}（代码文件 {rep['asset_code_files']}）",
             f"- 核心代码扫描文件：{rep['core_files_scanned']}",
             f"- 核心代码违规：{len(rep['core_violations'])}",
             f"- 判定：**{rep['verdict']}**", "",
             "## A. 核心引擎硬编码（NOT OK，须迁移）", "",
             "| 文件 | 命中词 | 迁移方案 |", "|---|---|---|"]
    critical = [v for v in rep["core_violations"]
                if Path(v["path"]).name in ("export.py", "contract.py", "migrate.py", "ingest_client.py")]
    adapters = [v for v in rep["core_violations"] if v not in critical]
    for v in critical:
        lines.append(f"| {v['path']} | {', '.join(v['terms'])} | 词表/算例移入 `knowledge/**` JSON 或 CLI 参数，代码只读数据 |")
    if not critical:
        lines.append("| （无） | — | — |")
    lines += ["", "## B. 领域抽取/发布适配器（可接受，需参数化）", "",
              "| 文件 | 命中词 | 处置 |", "|---|---|---|"]
    for v in adapters:
        lines.append(f"| {v['path']} | {', '.join(v['terms'])} | 领域词作为抽取目标合法；建议目标词表走 `--terms-file` |")
    if not adapters:
        lines.append("| （无） | — | — |")
    lines += ["", "## 判读口径", "",
              "- `knowledge/**`、`knowledge-map/**` 的 JSON/MD 是知识资产，领域内容属数据，判 OK。",
              "- 资产目录内若出现 `.py` 且写死领域词，判 NOT_OK（代码而非数据）。",
              "- `ke/` 核心引擎与通用 `scripts/` 出现领域词即违规，需改为数据注入。", ""]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    rep = audit()
    if args.check:
        print(f"BOUNDARY {rep['verdict']} core_violations={len(rep['core_violations'])}")
        return 0 if rep["verdict"] == "PASS" else 1
    OUT_JSON.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n")
    OUT_MD.write_text(render_md(rep))
    print(f"BOUNDARY {rep['verdict']} -> {OUT_MD.relative_to(ROOT)}")
    return 0 if rep["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())