#!/usr/bin/env python3
"""wp-5757-04 · 独立审核（红队）复跑脚本。

只读：从平台 API 取 report 5757 的 markdown，独立复核上游 wp-5757-01 的
asset_manifest（出处可定位性/唯一性/召回）与报告正文内部算术一致性，
产出 checks.json；不修改任何上游产物，不读其它 report_id。

用法（在仓库检出根执行）：
  TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 \
  TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
  python3 docs/kf/wp-5757-04/verify_wp_5757_04.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request

PACKAGE_ID = "wp-5757-04"
REPORT_ID = "5757"
EXPECTED_HASH = "sha256:d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915"
EXPECTED_CHARS = 5061
UPSTREAM = "docs/kf/wp-5757-01/asset_manifest.json"
OUT_DIR = "docs/kf/wp-5757-04"


def _api(path: str, token: str | None = None, body: dict | None = None):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=data, headers=headers)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def login() -> str:
    r = _api(
        "/auth/login",
        body={
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        },
    )
    return r["access_token"]


def table_rows(md: str) -> list[list[str]]:
    """把 markdown 里所有表格数据行拆成 cell 列表（去掉表头/分隔行）。"""
    rows = []
    for line in md.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        if cells[0] in ("门 id", "判据", "关键量"):
            continue
        rows.append(cells)
    return rows


def main() -> int:
    tok = login()
    rec = _api(f"/tensor/reports/{REPORT_ID}", tok)
    md = rec["markdown"]

    checks: list[dict] = []

    def add(cid, name, ok, detail, severity="blocking"):
        checks.append(
            {
                "check_id": cid,
                "name": name,
                "result": "pass" if ok else "fail",
                "severity_if_fail": severity,
                "detail": detail,
            }
        )

    # ── C1 provenance：独立重算哈希/字符数 ────────────────────────────
    h = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    add("C1", "provenance 哈希与被审 markdown 一致",
        h == EXPECTED_HASH and len(md) == EXPECTED_CHARS,
        {"recomputed": h, "expected": EXPECTED_HASH,
         "chars": len(md), "bytes_utf8": len(md.encode())})

    man = json.load(open(UPSTREAM, encoding="utf-8"))
    add("C2", "上游 manifest 的 provenance 哈希/字符数与本报告一致",
        man["provenance"]["hash"] == h[7:] and man["provenance"]["chars"] == len(md),
        {"manifest_hash": man["provenance"]["hash"], "recomputed": h[7:],
         "manifest_chars": man["provenance"]["chars"], "actual_chars": len(md)})
    add("C3", "上游 manifest 声明的 asset_count 与 assets 数组一致",
        man["summary"]["total_assets"] == len(man["assets"]),
        {"total_assets": man["summary"]["total_assets"], "len": len(man["assets"])})
    add("C4", "asset 编号唯一且无空 locator",
        len({a["asset_id"] for a in man["assets"]}) == len(man["assets"])
        and all(a["locator"]["quote"] for a in man["assets"]),
        {"ids": [a["asset_id"] for a in man["assets"]]})

    # ── C5/C6 locator：span 逐字、行号、唯一性 ────────────────────────
    loc = []
    for a in man["assets"]:
        q, s, e = a["locator"]["quote"], a["locator"]["start_char"], a["locator"]["end_char"]
        loc.append(
            {
                "asset_id": a["asset_id"],
                "quote": q,
                "span_exact": md[s:e] == q,
                "line_ok": md[:s].count("\n") + 1 == a["locator"]["start_line"]
                and md[:e].count("\n") + 1 == a["locator"]["end_line"],
                "occurrences": md.count(q),
                "declared_unique": a["locator"]["unique"],
                "first_index": md.find(q),
                "first_index_equals_span": md.find(q) == s,
            }
        )
    add("C5", "15 个 locator 的 char_span 与行号逐字命中原文",
        all(r["span_exact"] and r["line_ok"] for r in loc),
        {"checked": len(loc), "failed": [r["asset_id"] for r in loc if not (r["span_exact"] and r["line_ok"])]})
    non_unique = [r["asset_id"] for r in loc if r["occurrences"] > 1]
    add("C6", "locator.unique=true 与实际出现次数相符（机器可读字段须为真）",
        not any(r["declared_unique"] and r["occurrences"] > 1 for r in loc),
        {"non_unique_quotes": non_unique,
         "mitigation": "md.find(quote) 与记录 start_char 全部一致，first-occurrence 解析不受影响",
         "reproducible_by_index": all(r["first_index_equals_span"] for r in loc)},
        severity="minor")

    # ── C7 召回：独立抽取候选资产 vs manifest 覆盖 ────────────────────
    cands = set()
    for m in re.finditer(r"[A-Za-z0-9_./\-]+\.(py|sh|yaml|yml|json|md|png)", md):
        cands.add(m.group(0))
    reg = {a["locator"]["quote"] for a in man["assets"]}
    uncovered_paths = sorted(c for c in cands if not any(c in r or r in c for r in reg))
    add("C7", "file/path 型资产召回无遗漏",
        not uncovered_paths,
        {"candidate_paths": sorted(cands), "registered": sorted(reg),
         "uncovered": uncovered_paths},
        severity="minor")
    add("C8", "报告引用的 pytest 覆盖套件是否登记为资产",
        "pytest" not in md.lower() or any("test" in r for r in reg),
        {"report_says": [ln.strip() for ln in md.splitlines() if "pytest" in ln],
         "registered_test_assets": [r for r in reg if "test" in r]},
        severity="minor")

    # ── C9 报告内部算术：生产只读矩阵 vs 自述动作计数 ────────────────
    rows = table_rows(md)
    prod = [r for r in rows if len(r) >= 6 and re.fullmatch(r"\d+", r[0])]
    prod_actions = [r[4].strip("`") for r in prod]
    # 正文『动作计数』一行在 markdown 里被硬换行折成两行，先按 " / " 续行合并再解析
    flat = re.sub(r"/\n\s+", "/ ", md)
    stated_line = [ln.strip() for ln in flat.splitlines() if "动作计数" in ln][0]
    stated_counts = dict(re.findall(r"(\w+)=(\d+)", stated_line))
    # 逐字引文：原文该行被硬换行折成两行，这里给未合并的首行 + 续行片段
    raw_line = [ln.strip() for ln in md.splitlines() if "动作计数" in ln][0]
    raw_cont = "hold_owner_only=1"
    counted = {k: prod_actions.count(k) for k in sorted(set(prod_actions))}
    add("C9", "生产 6 门矩阵的行动作计数与自述『动作计数』一致",
        all(int(stated_counts.get(k, -1)) == v for k, v in counted.items())
        and sum(int(v) for v in stated_counts.values()) == len(prod_actions),
        {"matrix_rows": len(prod_actions), "matrix_counts": counted,
         "stated": stated_counts,
         "quote": raw_line, "quote_continuation": raw_cont,
         "note": "该行在原文里被硬换行折成两行（首行以 '/' 结尾，续行为 hold_owner_only=1）；"
                 "计数按合并后文本解析"})

    # ── C10 沙箱段：动作计数、释放集合、配对 ─────────────────────────
    sbx_start = md.index("### 沙箱写入路径")
    sbx_end = md.index("### 生产审计链")
    sbx_rows = [r for r in rows if len(r) == 3 and re.fullmatch(r"\d+", r[0])
                and r[1].strip("`") in ("release", "wait", "hold_owner_only")]
    sbx_rows = [r for r in sbx_rows if f"| {r[0]} |" in md[sbx_start:sbx_end]]
    sbx_actions = [r[1].strip("`") for r in sbx_rows]
    released = [int(r[0]) for r in sbx_rows if r[1].strip("`") == "release"]
    audit_line = [ln.strip() for ln in md.splitlines() if "审计动作计数" in ln][0]
    audit_counts = {k: int(v) for k, v in re.findall(r"'(\w+)': (\d+)", audit_line)}
    add("C10", "沙箱表行动作计数 == 自述审计动作计数，且 release 集合一致",
        {k: v for k, v in audit_counts.items() if k in ("release", "wait", "hold_owner_only")}
        == {k: sbx_actions.count(k) for k in ("release", "wait", "hold_owner_only")}
        and sorted(released) == [129, 144, 153, 170],
        {"sandbox_counts": {k: sbx_actions.count(k) for k in sorted(set(sbx_actions))},
         "audit_counts": audit_counts, "released": sorted(released),
         "quote": audit_line})
    add("C11", "release↔rollback 配对自洽（4 放 / 4 回滚）",
        audit_counts.get("release") == audit_counts.get("rollback") == len(released),
        {"release": audit_counts.get("release"), "rollback": audit_counts.get("rollback"),
         "released_rows": len(released)})

    # ── C12 审计行数算术：6 门 + G21 等待 vs 7 行 ────────────────────
    gate_wait = prod_actions.count("wait")
    gate_hold = prod_actions.count("hold_owner_only")
    audit_para = [ln for ln in md.splitlines() if "gate_release_audit" in ln and "行" in ln]
    total7 = gate_wait + gate_hold + 1  # +plan21 G21 一个 wait
    add("C12", "生产首轮审计行数 7 = 6 门动作 + G21 一行的算术自洽",
        total7 == 7,
        {"six_gate_wait": gate_wait, "six_gate_hold": gate_hold,
         "g21_wait": 1, "derived_total": total7,
         "note": "总数自洽；但正文把 6 个 wait 行写成『六门 wait ×6』，而六门中 wait=5、hold=1，"
                 "第 6 个 wait 来自 plan 21 的 G21",
         "prose_quote": audit_para[0].strip()[:80] if audit_para else ""},
        severity="minor")

    # ── C13 治理门优先级：矩阵与判据表是否声明 C3 先于 C2 ────────────
    g185 = [r for r in prod if r[0] == "185"][0]
    crit_table = [r for r in rows if len(r) == 3 and r[0].startswith("C")]
    add("C13", "判据表显式声明 C3(治理门) 先于 C2(工件可解析) 的判定优先级",
        any("先" in " ".join(r) or "优先级" in " ".join(r) for r in crit_table),
        {"gate185_row": g185,
         "explanation": "185 行判据工件 not_found（C2 不满足）却给 hold_owner_only（C3），"
                        "说明实现让 C3 短路 C2；判据表只列 C1/C2/C3 未写优先级，"
                        "仅靠 C3 描述里的『永不自动放』隐含",
         "criteria_table": crit_table},
        severity="minor")

    # ── C14 证据可复算性：快照哈希是否给全 ───────────────────────────
    snap = [ln.strip() for ln in md.splitlines() if "快照" in ln and "before" in ln]
    truncated = bool(snap) and "…" in snap[0]
    add("C14", "生产快照哈希给全（可被独立重算/比对）",
        not truncated,
        {"quote": snap[0] if snap else "", "truncated": truncated,
         "impact": "production_untouched=True 只能采信程序结论，外部无法复算"},
        severity="minor")

    # ── C15 图件载荷是否随报告发布 ───────────────────────────────────
    figs = rec.get("figures") or []
    has_payload = bool(figs) and all(("png_base64" in f and f["png_base64"]) for f in figs)
    add("C15", "图件 A12 的 png 载荷随报告记录发布（下游可否验图）",
        has_payload,
        {"figures": [{k: (str(v)[:40] + "...") if k != "png_base64" else "MISSING"
                      for k, v in f.items()} for f in figs],
         "impact": "上游把 A12 记为 referenced_unresolved 是诚实的；但图内容对下游不可验"},
        severity="minor")

    # ── 汇总 ─────────────────────────────────────────────────────────
    fails = [c for c in checks if c["result"] == "fail"]
    blocking = [c for c in fails if c["severity_if_fail"] == "blocking"]
    out = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "reviewed_package": "wp-5757-01",
        "source_hash": h,
        "source_chars": len(md),
        "checks_total": len(checks),
        "checks_pass": len(checks) - len(fails),
        "checks_fail": len(fails),
        "blocking_failures": [c["check_id"] for c in blocking],
        "non_blocking_failures": [c["check_id"] for c in fails if c is not blocking],
        "checks": checks,
        "locator_matrix": loc,
    }
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(os.path.join(OUT_DIR, "checks.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)

    for c in checks:
        print(f"[{c['result'].upper():4}] {c['check_id']:4} {c['name']}")
    print(f"\nsummary: {out['checks_pass']}/{out['checks_total']} pass, "
          f"blocking failures={out['blocking_failures']}")
    print(f"wrote {OUT_DIR}/checks.json")
    return 0 if not blocking else 1


if __name__ == "__main__":
    sys.exit(main())