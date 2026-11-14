"""CLI 入口：``python -m tools.kpi_kb_verify_rate <command>``。

退出码约定（机器可判）：
  0 = 命令成功且（若有判据）判定通过
  1 = 判定不通过（verify 不一致 / bench 有 FAIL）
  2 = 输入或环境问题（快照口径不匹配、库不可达、用法错误）
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import bench as bench_mod
from . import collect as collect_mod
from . import compute, oracle, report, spec
from .backend import BackendUnavailable


def _load_snapshot(path: str | Path) -> dict:
    snap = json.loads(Path(path).read_text(encoding="utf-8"))
    if snap.get("spec_sha256") != spec.SPEC_SHA256:
        print(f"[exit2] 快照口径与当前 spec 不一致：{snap.get('spec_sha256')} != {spec.SPEC_SHA256}；"
              "口径变了必须重新 collect", file=sys.stderr)
        raise SystemExit(2)
    if snap.get("snapshot_sha256") != compute.snapshot_fingerprint(snap):
        print("[exit2] 快照指纹自校验失败（文件被改过）", file=sys.stderr)
        raise SystemExit(2)
    return snap


def cmd_collect(args) -> int:
    snap = collect_mod.collect(user=args.user)
    p = collect_mod.write_snapshot(snap, args.out)
    tsv = collect_mod.write_tsv_dumps(snap, args.out)
    print(json.dumps({"snapshot": str(p), "snapshot_sha256": snap["snapshot_sha256"],
                      "n_queries": len(spec.QUERIES), "tsv": [str(t) for t in tsv]},
                     ensure_ascii=False))
    return 0


def cmd_measure(args) -> int:
    snap = _load_snapshot(args.snapshot)
    result = compute.build_result(snap)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "result.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"current": result["current"], "numerator": result["numerator"],
                      "denominator": result["denominator"], "target": result["target"],
                      "target_status": result["target_status"],
                      "result_sha256": compute.result_fingerprint(result)}, ensure_ascii=False))
    return 0


def cmd_report(args) -> int:
    snap = _load_snapshot(args.snapshot)
    result = compute.build_result(snap)
    bench_rep = bench_mod.run(snapshot=snap, user=args.user) if args.with_bench else None
    arts = report.write_artifacts(snap, result, args.out, bench=bench_rep)
    print(json.dumps({"current": result["current"], "numerator": result["numerator"],
                      "denominator": result["denominator"],
                      "result_sha256": arts["result_sha256"],
                      "files": [str(p) for p in
                                [arts["result"], arts["markdown"], *arts["figures"]]]},
                     ensure_ascii=False))
    return 0


def cmd_verify(args) -> int:
    snap = _load_snapshot(args.snapshot)
    result = compute.build_result(snap)
    checks = []

    # 1) 与落盘 result.json 逐字段一致（同一快照必须同结果）
    out = Path(args.snapshot).parent
    prev_path = out / "result.json"
    if prev_path.exists():
        prev = json.loads(prev_path.read_text(encoding="utf-8"))
        same = compute.result_fingerprint(prev) == compute.result_fingerprint(result)
        checks.append({"check": "result == 落盘 result.json", "pass": same,
                       "detail": "result_fingerprint 比对"})
    else:
        checks.append({"check": "result == 落盘 result.json", "pass": None,
                       "detail": "未找到 result.json（not_run）"})

    # 2) 独立 oracle 复算（活库）
    if not args.no_oracle:
        oc = oracle.oracle_counts(user=args.user)
        if oc is None:
            checks.append({"check": "oracle 双路径复算", "pass": None,
                           "detail": "psql/PG 不可达（not_run，不是 pass）"})
        else:
            same = (oc["numerator"] == result["numerator"]
                    and oc["denominator"] == result["denominator"])
            checks.append({"check": "oracle 双路径复算", "pass": same,
                           "detail": {"oracle": {"numerator": oc["numerator"],
                                                 "denominator": oc["denominator"]},
                                      "primary": {"numerator": result["numerator"],
                                                  "denominator": result["denominator"]},
                                      "denominator_ids_equal_primary":
                                          oc.get("denominator_ids_equal_primary")}})

    # 3) 语义不变量
    inv = (result["current"] is None) == (result["denominator"] == 0)
    checks.append({"check": "0/0 -> null 语义", "pass": inv,
                   "detail": {"current": result["current"],
                              "denominator": result["denominator"]}})
    tgt = result["target"] is None and result["target_status"] == "NOT_CALIBRATED"
    checks.append({"check": "目标未定标则不编造 target", "pass": tgt,
                   "detail": {"target": result["target"],
                              "target_status": result["target_status"]}})

    ran = [c for c in checks if c["pass"] is not None]
    ok = all(c["pass"] for c in ran)
    print(json.dumps({"current": result["current"], "checks": checks,
                      "all_run_checks_pass": ok,
                      "not_run": [c["check"] for c in checks if c["pass"] is None]},
                     ensure_ascii=False, indent=2))
    return 0 if ok else 1


def cmd_bench(args) -> int:
    snap = None
    if args.snapshot:
        snap = _load_snapshot(args.snapshot)
    rep = bench_mod.run(snapshot=snap, cases_path=args.cases, user=args.user, out_dir=args.out)
    print(json.dumps(rep["summary"], ensure_ascii=False, indent=2))
    return 0 if rep["summary"]["all_run_checks_pass"] else 1


def cmd_selftest(args) -> int:
    """离线自检：只验语义与指纹，不连库。"""
    fails: list[dict] = []

    def check(name, cond, detail=None):
        if not cond:
            fails.append({"check": name, "detail": detail})

    check("3/10 = 0.3", compute.verify_rate(3, 10) == 0.3)
    check("0/0 -> None", compute.verify_rate(0, 0) is None)
    check("0/5338 -> 0.0", compute.verify_rate(0, 5338) == 0.0)
    check("10/10 -> 1.0", compute.verify_rate(10, 10) == 1.0)
    for bad in ((4, 3), (-1, 5), (1, -5)):
        try:
            compute.verify_rate(*bad)
            check(f"reject {bad}", False)
        except compute.SemanticsError:
            pass
    ci0 = compute.wilson_interval(0, 5338)
    check("Wilson(0,5338).high > 0", ci0 is not None and ci0["high"] > 0, ci0)
    check("Wilson(0,0) -> None", compute.wilson_interval(0, 0) is None)
    check("spec_sha256 stable", spec.spec_sha256() == spec.SPEC_SHA256)
    fam = {"schema": "x", "spec_sha256": spec.SPEC_SHA256, "raw": {"ko_total": 1},
           "collected_at_utc": "t1"}
    fam2 = dict(fam, collected_at_utc="t2")
    check("指纹与采集时刻无关",
          compute.snapshot_fingerprint(fam) == compute.snapshot_fingerprint(fam2))
    # 口径不一致必须拒
    try:
        compute.build_result({"spec_sha256": "deadbeef", "raw": {}})
        check("拒收口径不一致快照", False)
    except compute.SemanticsError:
        pass
    print(json.dumps({"fails": fails, "n_fail": len(fails)}, ensure_ascii=False, indent=2))
    return 0 if not fails else 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="python -m tools.kpi_kb_verify_rate",
        description="KPI-KB-VERIFY-RATE 只读计量器（feature_ledger#164）")
    ap.add_argument("--user", default=None, help="PG 角色（默认 env KPI_PG_USER 或 postgres）")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("collect", help="连库采集快照（只读）")
    p.add_argument("--out", required=True, help="输出目录（如 runs/kpi_kb_verify_rate）")
    p.set_defaults(func=cmd_collect)

    p = sub.add_parser("measure", help="由快照算 result.json（不连库）")
    p.add_argument("--snapshot", required=True)
    p.add_argument("--out", default=None, help="默认与 snapshot 同目录")
    p.set_defaults(func=cmd_measure)

    p = sub.add_parser("report", help="生成 result + 六要素 Markdown + 图件")
    p.add_argument("--snapshot", required=True)
    p.add_argument("--out", default=None)
    p.add_argument("--with-bench", action="store_true", help="同时跑 ref-vs-got 基准并写进报告⑥")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("verify", help="复核：落盘结果一致 + 独立 oracle + 语义不变量")
    p.add_argument("--snapshot", required=True)
    p.add_argument("--no-oracle", action="store_true")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("bench", help="ref-vs-got 基准（三层）")
    p.add_argument("--snapshot", default=None)
    p.add_argument("--cases", default=None)
    p.add_argument("--out", default="benchmarks/kpi_kb_verify_rate")
    p.set_defaults(func=cmd_bench)

    p = sub.add_parser("selftest", help="离线语义自检")
    p.set_defaults(func=cmd_selftest)
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)
    if getattr(args, "out", None) is None and args.cmd in ("measure", "report"):
        args.out = str(Path(args.snapshot).parent)
    try:
        return args.func(args)
    except BackendUnavailable as exc:
        print(f"[exit2] 数据库不可达：{exc}", file=sys.stderr)
        return 2
    except collect_mod.CollectionError as exc:
        print(f"[exit2] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())