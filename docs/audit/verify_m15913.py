#!/usr/bin/env python3
"""m15922 交差核验：对 m15913（KBM-RCI-F1-SPEC）交付做独立复算。

核验面（全部机器可判，零手抄）：
  A1 基准复算：重跑 ke.wp_line.run_benchmark，与仓内工件 benchmark.json 逐字段比对
  A2 负对照（可证伪性）：篡改参考表一行，验证基准会掉分并以 exit=3 报错
  A3 门禁基准注册：tensor_benchmark_cases 中 anchor=KBM-RCI-F1-SPEC 的行数
  A4 运行工件：run_artifacts 各文件存在 + JSON 合法
  A5 真平台回环：process 01 登记的 5 份报告按 sha256 与平台 live markdown 复算
  A6 报告六段：tensor_reports id=15052 六要素齐全
用法： python docs/audit/verify_m15913.py [--out docs/audit/repro/verify_result.json]
只读 m15913 工作树；只写本工作树。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.error
import urllib.request

WT = pathlib.Path("/root/tp-agent/work/m15913")
ART = WT / "docs/production/run-artifacts"
SECTIONS = ("①", "②", "③", "④", "⑤", "⑥")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
PG = ["psql", "-h", "127.0.0.1", "-U", "foundation", "-d", "tensorplatform", "-tAc"]


def api(method: str, path: str, payload=None, token: str | None = None):
    req = urllib.request.Request(API + path, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    data = json.dumps(payload).encode() if payload is not None else None
    with urllib.request.urlopen(req, data, timeout=60) as r:
        return json.loads(r.read() or b"{}")


def psql(sql: str) -> str:
    env = {k: v for k, v in os.environ.items()}
    env.setdefault("PGPASSWORD", "")
    r = subprocess.run(PG + [sql], capture_output=True, text=True, env=env)
    return r.stdout.strip()


def a1_benchmark_rerun() -> dict:
    sys.path.insert(0, str(WT))
    from ke import wp_line  # noqa: E402  (delivered implementation, read-only import)

    got = wp_line.run_benchmark()
    stored = json.loads((ART / "benchmark.json").read_text())
    fields = ("metrics", "n_fixtures", "n_mutations", "n_mutations_detected",
              "below_threshold", "pass", "thresholds", "fixtures", "mutations")
    same = {f: got.get(f) == stored.get(f) for f in fields}
    return {"stored_metrics": stored["metrics"], "rerun_metrics": got["metrics"],
            "field_equal": same, "all_equal": all(same.values()),
            "n_fixtures": got["n_fixtures"], "n_mutations": got["n_mutations"],
            "n_mutations_detected": got["n_mutations_detected"]}


def a2_negative_control() -> dict:
    """参考表改一行 → 基准必须掉分 + 非零退出码（证明测的是判定而非硬编码）。"""
    ref = WT / "docs/production/GATE-RULES.md"
    tampered = pathlib.Path("/tmp/m15922_gate_rules_tampered.md")
    txt = ref.read_text()
    txt2 = txt.replace("| `bad-no-evidence` | `FAIL_STRUCTURAL`",
                       "| `bad-no-evidence` | `PASS_PROGRAMMATIC_PENDING_REVIEW`", 1)
    tampered.write_text(txt2)
    r = subprocess.run([sys.executable, "-m", "ke.wp_line", "bench",
                        "--ref-doc", str(tampered), "--json", "/tmp/m15922_neg_bench.json"],
                       cwd=WT, capture_output=True, text=True, timeout=600)
    neg = json.loads(pathlib.Path("/tmp/m15922_neg_bench.json").read_text())
    return {"tampered_row": "bad-no-evidence verdict FAIL_STRUCTURAL -> PASS_...",
            "exit_code": r.returncode, "metrics": neg["metrics"],
            "below_threshold": neg["below_threshold"],
            "detected_shift": neg["metrics"]["verdict_agreement"] < 1.0}


def a3_registered_benchmark() -> dict:
    out = psql("SELECT count(*) FROM tensor_benchmark_cases "
               "WHERE anchor_slug='KBM-RCI-F1-SPEC'")
    total = psql("SELECT count(*)||' anchors='||count(DISTINCT anchor_slug) "
                 "FROM tensor_benchmark_cases")
    return {"anchor": "KBM-RCI-F1-SPEC", "rows": int(out or 0 or 0),
            "table_totals": total,
            "ref_source_used": "docs/production/GATE-RULES.md 夹具矩阵（m15494 commit a1c0c76 先于实现 355218c）"}


def a4_run_artifacts() -> dict:
    names = ["benchmark.json", "line_report.json", "synthesis_input.json",
             "asset_registration.json", "RESULTS.md", "RUN-LOG.md"]
    rows = {}
    for n in names:
        p = ART / n
        ok = p.exists()
        valid = None
        if ok and p.suffix == ".json":
            try:
                json.loads(p.read_text())
                valid = True
            except Exception:
                valid = False
        rows[n] = {"exists": ok, "json_valid": valid,
                   "bytes": p.stat().st_size if ok else 0}
    return rows


def a5_live_hash_roundtrip() -> dict:
    tok = api("POST", "/auth/login", {
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    reg = json.loads((ART / "asset_registration.json").read_text())
    rows = []
    for r in reg["reports"]:
        rep = api("GET", "/tensor/reports/" + str(r["report_id"]), token=tok)
        md = rep.get("markdown", "")
        h = "sha256:" + hashlib.sha256(md.encode()).hexdigest()
        rows.append({"report_id": r["report_id"], "reachable": bool(md),
                     "declared": r["source_hash"], "recomputed": h,
                     "hash_match": h == r["source_hash"],
                     "len_match": len(md) == r["length_chars"]})
    return {"n": len(rows), "n_match": sum(1 for x in rows if x["hash_match"]),
            "rows": rows}


def a6_report_sections() -> dict:
    tok = api("POST", "/auth/login", {
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    rep = api("GET", "/tensor/reports/15052", token=tok)
    md = rep.get("markdown", "")
    return {"report_id": 15052, "chars": len(md),
            "sections_present": {s: s in md for s in SECTIONS},
            "all_six": all(s in md for s in SECTIONS),
            "n_figures": len(rep.get("figures") or []),
            "error_lt_3pct_stated": bool(re.search(r"<\s*3\s*%|是否\s*<\s*3%", md))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/audit/repro/verify_result.json")
    args = ap.parse_args()
    res = {"mission_audited": 15913, "audit_mission": 15922,
           "anchor": "KBM-RCI-F1-SPEC",
           "A1_benchmark_rerun": a1_benchmark_rerun(),
           "A2_negative_control": a2_negative_control(),
           "A3_registered_benchmark_cases": a3_registered_benchmark(),
           "A4_run_artifacts": a4_run_artifacts(),
           "A5_live_hash_roundtrip": a5_live_hash_roundtrip(),
           "A6_report_sections": a6_report_sections()}
    res["verdict"] = {
        "A1_reproducible": res["A1_benchmark_rerun"]["all_equal"],
        "A2_falsifiable": res["A2_negative_control"]["detected_shift"]
        and res["A2_negative_control"]["exit_code"] != 0,
        "A3_registered_case": res["A3_registered_benchmark_cases"]["rows"] > 0,
        "A5_live_loop_closed": res["A5_live_hash_roundtrip"]["n_match"]
        == res["A5_live_hash_roundtrip"]["n"],
        "A6_six_sections": res["A6_report_sections"]["all_six"],
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps({k: v for k, v in res["verdict"].items()}, ensure_ascii=False))
    print("metrics:", res["A1_benchmark_rerun"]["rerun_metrics"])
    print("negative control exit:", res["A2_negative_control"]["exit_code"],
          "verdict_agreement:", res["A2_negative_control"]["metrics"]["verdict_agreement"])
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())