#!/usr/bin/env python3
"""wp-444-04 independent review: re-derive every wp-444-01 asset-registration claim
straight from the report markdown (zero copy-paste). Writes artifacts/wp-444-04/verification.json.

Run:  python3 work/verify_wp444_01.py
Env:  TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS (login), or
      --md /tmp/report444.md --upstream /tmp/report14623.md for offline replay.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "artifacts", "wp-444-04")
UPSTREAM_REPORT_ID = 14623  # wp-444-01 result report (tk_work_packages.result_report_id)
SOURCE_REPORT_ID = 444
DECLARED_SOURCE_HASH = ("sha256:"
                        "4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2")


# ---------------------------------------------------------------- fetch helpers
def _get(url, token=None):
    req = urllib.request.Request(url)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def fetch_live():
    base = os.environ["TENSOR_API_BASE"]
    tok = json.loads(
        urllib.request.urlopen(
            urllib.request.Request(
                base + "/auth/login",
                data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                 "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            ),
            timeout=60,
        ).read()
    )["access_token"]
    src = _get(f"{base}/tensor/reports/{SOURCE_REPORT_ID}", tok)
    up = _get(f"{base}/tensor/reports/{UPSTREAM_REPORT_ID}", tok)
    return src, up


def json_blocks(md: str):
    return [json.loads(b) for b in re.findall(r"```json\n(.*?)```", md, re.S)]


# ---------------------------------------------------------------- measurement
def count_sections(md: str) -> list[str]:
    return [ln.rstrip() for ln in md.splitlines() if ln.startswith("## ")]


def count_tables(md: str) -> list[dict]:
    """A markdown table = run of lines starting with '|' whose 2nd line is a separator."""
    lines = md.splitlines()
    tables, i = [], 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and \
                re.match(r"^\s*\|[\s:\-|]+\|\s*$", lines[i + 1]):
            start = i
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                i += 1
            rows = [l for l in lines[start:i] if l.lstrip().startswith("|")]
            tables.append({"start_line": start + 1, "end_line": i,
                           "header": rows[0], "data_rows": len(rows) - 2})
        else:
            i += 1
    return tables


CODE_PATH = re.compile(r"`[^`]*\.(py|cpp|hpp|c|cu|f90|jl|m|ipynb|sh|json|yaml|yml)`")


def count_code_refs(md: str) -> list[str]:
    return CODE_PATH.findall(md)


def locate(md: str, needle: str):
    """1-based line numbers where `needle` appears (exact substring)."""
    return [n for n, ln in enumerate(md.splitlines(), 1) if needle in ln]


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--md")
    ap.add_argument("--upstream")
    ap.add_argument("--out", default=os.path.join(OUT_DIR, "verification.json"))
    a = ap.parse_args()

    if a.md:
        src_md = open(a.md, encoding="utf-8").read()
        src_rec = {"id": SOURCE_REPORT_ID, "markdown": src_md,
                   "figures": json.load(open(os.path.join(HERE, "figures444.json")))
                   if os.path.exists(os.path.join(HERE, "figures444.json")) else None}
        up_md = open(a.upstream, encoding="utf-8").read()
        up_rec = {"id": UPSTREAM_REPORT_ID}
    else:
        src_rec, up_rec = fetch_live()
        src_md, up_md = src_rec["markdown"], up_rec["markdown"]

    blocks = json_blocks(up_md)
    assert len(blocks) == 1, f"expected exactly one ```json block, got {len(blocks)}"
    env = blocks[0]

    checks = {}

    # H1 source identity: recompute byte-exact sha256 of the markdown string
    h = hashlib.sha256(src_md.encode("utf-8")).hexdigest()
    checks["H1_source_hash_matches_declaration"] = {
        "recomputed": "sha256:" + h,
        "declared": env["provenance"]["source_hash"],
        "contract": DECLARED_SOURCE_HASH,
        "pass": "sha256:" + h == env["provenance"]["source_hash"] == DECLARED_SOURCE_HASH,
    }

    # H2..H5 structural counts, recomputed independently
    man = env["outputs"]["asset_manifest"]
    secs = count_sections(src_md)
    tbls = count_tables(src_md)
    figs = src_rec.get("figures") or []
    code_refs = count_code_refs(src_md)
    checks["H2_sections_count"] = {"declared": man["sections_count"], "recomputed": len(secs),
                                   "pass": man["sections_count"] == len(secs), "items": secs}
    checks["H3_tables_count"] = {"declared": man["tables_count"], "recomputed": len(tbls),
                                 "pass": man["tables_count"] == len(tbls),
                                 "items": [t["header"] for t in tbls]}
    checks["H4_figures_count"] = {"declared": man["figures_count"], "recomputed": len(figs),
                                  "pass": man["figures_count"] == len(figs),
                                  "items": [f.get("name") for f in figs]}
    checks["H5_code_references_count"] = {
        "declared": man["code_references_count"], "recomputed": len(code_refs),
        "pass": man["code_references_count"] == len(code_refs), "items": code_refs,
        "note": "counts backticked path-with-extension tokens; prose mentions of a test "
                "framework are not code references",
    }
    checks["H6_claims_empty"] = {"declared": man["claims_count"],
                                 "envelope_has_claims_key": "claims" in env,
                                 "pass": man["claims_count"] == 0 and "claims" not in env,
                                 "note": "01-asset-registration 不抽取；零 claim 合法"}
    checks["H7_no_producer_supplied_review_material"] = {
        "outputs_keys": sorted(env["outputs"]),
        "forbidden_present": [k for k in ("review_events.json", "verification_ticket.json",
                                          "review_report.json") if k in env["outputs"]],
        "pass": not any(k in env["outputs"] for k in ("review_events.json",
                                                      "verification_ticket.json",
                                                      "review_report.json")),
    }
    # H8 the envelope must not pre-empt the verification axis
    flat = json.dumps(env, ensure_ascii=False)
    banned = [w for w in ("\"verification_status\"", "\"verified\": true", "\"L3\"")
              if w in flat]
    checks["H8_no_verification_claim"] = {
        "banned_tokens_found": banned, "pass": not banned,
        "note": "provenance.source_hash_verified 是自算哈希自检（可程序化复现），不属 claim 验证",
    }

    # H9 locator fidelity: every ④ quote must be a verbatim substring of the markdown
    quotes = [
        "AlphaEvolve-Style Verifier/Generator Separation: Held-Out Question Bank & "
        "Independent Verification for Ship Resistance",
        "见 figures 附件：四面板图展示 ITTC-1957 摩擦线、平板边界层、逐公式通过率、逐题偏差",
        "本报告经治理升级，补充六要素章节（背景/方法/结果/图件/注意点/误差判定）",
        "ITTC-1957 / Blasius / P-S / Holtrop",
        "ITTC-1957 5/5 / Blasius 3/3 / P-S 4/4 / HM 3/3 / 合计 15/15",
        "ITTC-1957 Cf (Re=1e8) 0.0% / Blasius Cf 0.0% / P-S Cf 0.0% / HM 1+k 0.0%",
        "pytest（12 项单元测试）",
        "{name, caption}",
        "png_base64",
    ]
    checks["H9_locator_verbatim"] = [
        {"quote": q, "verbatim_in_markdown": q in src_md, "lines": locate(src_md, q)[:5],
         "in_upstream_prose": q in up_md}
        for q in quotes
    ]

    # H10 the producer's line-range locators, re-derived
    claimed = [
        ("参数表 4 行", "| 公式 | 输入 | 输出 | 参考值来源 |", "lines 11-17"),
        ("计算结果表 5 行", "| 题目类别 | 题数 | 通过 | 最大偏差 | 容差 |", "lines 35-41"),
        ("误差判定表 4 行", "| 关键量 | 基准 | 实际 | 偏差 | <3%? |", "lines 55-60"),
        ("图引用", "见 figures 附件", "line 45"),
        ("治理升级", "本报告经治理升级", "line 69"),
    ]
    checks["H10_locator_line_ranges"] = [
        {"label": lab, "claimed": cl, "anchor": anc, "actual_lines": locate(src_md, anc),
         "anchor_present": anc in src_md} for lab, anc, cl in claimed
    ]

    # H11 deliverable resolvability: declared artifact path must resolve for the reviewer
    p = man["path"]
    checks["H11_artifact_path_resolvable"] = {
        "declared_path": p,
        "exists_in_review_worktree": os.path.exists(os.path.join(ROOT, p)),
        "pass": os.path.exists(os.path.join(ROOT, p)),
        "note": "路径相对生产者工作树；评审上下文中不可解析 → 清单细目不可独立核对",
    }
    # H12 envelope granularity
    checks["H12_envelope_carries_granular_manifest"] = {
        "envelope_asset_manifest_keys": sorted(man),
        "has_sections_list": "sections" in man, "has_tables_list": "tables" in man,
        "has_figures_list": "figures" in man,
        "pass": all(k in man for k in ("sections", "tables", "figures")),
    }

    hard = [k for k, v in checks.items() if k.startswith("H") and isinstance(v, dict)
            and v.get("pass") is False]
    soft = [k for k, v in checks.items() if k.startswith("H") and isinstance(v, list)
            and any(i.get("verbatim_in_markdown") is False for i in v)]
    report = {
        "package_reviewed": env["package_id"],
        "task_type_reviewed": env["task_type"],
        "source_report_id": SOURCE_REPORT_ID,
        "upstream_result_report_id": UPSTREAM_REPORT_ID,
        "measured": {"sections": len(secs), "tables": len(tbls), "figures": len(figs),
                     "code_references": len(code_refs), "markdown_sha256": "sha256:" + h,
                     "markdown_chars": len(src_md)},
        "checks": checks,
        "hard_failures": hard,
        "locator_non_verbatim": soft,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({"out": a.out, "hard_failures": hard, "locator_non_verbatim": soft,
                      "measured": report["measured"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())