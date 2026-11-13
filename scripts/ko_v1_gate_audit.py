#!/usr/bin/env python3
"""KBM-RCI-S2-SCHEMA 第 2 轮 —— 真实语料上的三闸/六要素实测（零手抄）。

目的：把 ``docs/rci/schema-v1.md`` §3.2 里「现网基线」的两个数字（55.2% 报告引用
artifacts/runs 路径、46.9% 六要素齐全）从**声明**变成**可复算**，并给出两个分辨率
（N=25 / N=100）下的稳定性，供报告 ④对照表 ⑤收敛性 使用。

口径（与 schema-v1 §3.2 一致，纯程序判定）：
  R1 报告闸  := 报告 GET 成功 且 markdown 非空 且 mission_id 存在
  R2 小节闸  := 报告内可解析出至少 1 个 markdown 标题锚（heading→anchor）
  F  要素覆盖 := 六要素 facet 命中数与命中清单（facet 由标题关键词判定，**启发式**，
               声明在报告里，不作论文级结论）
  R3 工件闸  := markdown 内含 artifacts/ 或 runs/ 路径（结构判定；跨工作树不存在
               故不核文件系统，与基线口径一致，不强于基线）
  E-TR 上界 := (R1 ∧ R2 ∧ R3 ∧ 六要素全覆盖) 的报告占比 —— 注意这是**报告级上界**，
               不是对象级可追溯率；对象级 E-TR 由 validate_ko_v1.evidence_traceability 计算。

用法:
    python scripts/ko_v1_gate_audit.py --samples 25 100 --out runs/rci/audit_gate
"""
from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")

HEADING_RE = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.M)
ARTIFACT_RE = re.compile(r"\b(?:artifacts|runs)/[\w./\-]+")

# 六要素 facet 判定（顺序即优先级；命中一个 facet 后不再重复计入）
FACETS: list[tuple[str, tuple[str, ...]]] = [
    ("case", ("案例", "介绍", "背景", "问题设定", "introduction", "case")),
    ("method", ("方法", "流程", "实现", "做法", "method", "approach", "implementation")),
    ("result", ("结果", "计算结果", "result")),
    ("figure", ("图", "figure", "云图", "曲线")),
    ("note", ("注意", "局限", "踩坑", "讨论", "note", "limitation", "caveat")),
    ("error", ("误差", "判定", "error", "accuracy", "verification")),
]


def slugify(heading: str) -> str:
    s = heading.strip().lower()
    s = re.sub(r"^[\s\d\.\)\(\]。、①-⑳:：\-]+", "", s)
    s = re.sub(r"[^\w\u4e00-\u9fff]+", "-", s, flags=re.UNICODE)
    return re.sub(r"-{2,}", "-", s).strip("-")


def _request(url: str, token: str | None = None, body: dict | None = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def login(base: str) -> str:
    user = os.environ["TENSOR_AGENT_USER"]
    pwd = os.environ["TENSOR_AGENT_PASS"]
    tok = _request(base + "/auth/login", body={"username": user, "password": pwd})
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise SystemExit("login failed: no access_token")
    return token


def facets_of(headings: list[str]) -> dict[str, list[str]]:
    hit: dict[str, list[str]] = {}
    for h in headings:
        low = h.lower()
        for facet, keys in FACETS:
            if facet in hit:
                continue
            if any(k in low for k in keys):
                hit[facet] = hit.get(facet, []) + [h]
                break
    return hit


def measure_report(rep: dict[str, Any]) -> dict[str, Any]:
    md = rep.get("markdown") or ""
    headings = [m.group(1) for m in HEADING_RE.finditer(md)]
    anchors = [slugify(h) for h in headings]
    facets = facets_of(headings)
    art_paths = ARTIFACT_RE.findall(md)
    r1 = bool(md.strip()) and rep.get("mission_id") is not None
    r2 = len(anchors) > 0
    r3 = len(art_paths) > 0
    six = len(facets) == len(FACETS)
    return {
        "report_id": rep.get("id"),
        "mission_id": rep.get("mission_id"),
        "md_chars": len(md),
        "n_headings": len(headings),
        "n_anchors": len(set(a for a in anchors if a)),
        "facets_hit": sorted(facets),
        "n_facets": len(facets),
        "n_artifact_paths": len(art_paths),
        "R1_report": r1,
        "R2_section": r2,
        "R3_artifact": r3,
        "six_element": six,
        "etr_upper": bool(r1 and r2 and r3 and six),
        "sample_headings": headings[:8],
    }


def aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    def rate(key: str) -> float:
        return round(sum(1 for r in rows if r[key]) / n, 4) if n else 0.0
    facet_counts = {f: sum(1 for r in rows if f in r["facets_hit"]) for f, _ in FACETS}
    return {
        "n": n,
        "R1_report_rate": rate("R1_report"),
        "R2_section_rate": rate("R2_section"),
        "R3_artifact_rate": rate("R3_artifact"),
        "six_element_rate": rate("six_element"),
        "etr_upper_rate": rate("etr_upper"),
        "facet_rates": {k: round(v / n, 4) for k, v in facet_counts.items()} if n else {},
        "median_md_chars": int(statistics.median([r["md_chars"] for r in rows])) if n else 0,
        "median_headings": int(statistics.median([r["n_headings"] for r in rows])) if n else 0,
    }


def run_sample(base: str, token: str, n: int) -> list[dict[str, Any]]:
    listing = _request(base + f"/tensor/reports?limit={n}", token=token)
    items = listing.get("items") or listing.get("reports") or []
    rows: list[dict[str, Any]] = []
    for it in items[:n]:
        rid = it.get("id")
        try:
            rep = _request(base + f"/tensor/reports/{rid}", token=token)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            rows.append({"report_id": rid, "fetch_error": f"{type(exc).__name__}: {exc}",
                         "R1_report": False, "R2_section": False, "R3_artifact": False,
                         "six_element": False, "etr_upper": False, "facets_hit": [],
                         "md_chars": 0, "n_headings": 0, "n_anchors": 0,
                         "n_artifact_paths": 0, "n_facets": 0, "sample_headings": []})
            continue
        if isinstance(rep, dict) and "report" in rep and isinstance(rep["report"], dict):
            rep = rep["report"]
        rows.append(measure_report(rep))
        time.sleep(0.01)
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=DEFAULT_BASE)
    ap.add_argument("--samples", nargs="+", type=int, default=[25, 100])
    ap.add_argument("--out", default=str(ROOT / "runs" / "rci" / "audit_gate"))
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    token = login(args.base)

    summary: dict[str, Any] = {"base": args.base, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                               "samples": {}}
    for n in sorted(args.samples):
        rows = run_sample(args.base, token, n)
        agg = aggregate(rows)
        (out / f"reports_n{n}.json").write_text(
            json.dumps({"aggregate": agg, "rows": rows}, ensure_ascii=False, indent=1))
        summary["samples"][str(n)] = agg
        print(f"N={n}: {json.dumps(agg, ensure_ascii=False)}")

    (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
    print(f"wrote {out/'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())