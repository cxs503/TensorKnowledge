#!/usr/bin/env python3
"""Regenerate the m15913 evidence bundle for the production-line runner.

Every number in ``docs/production/run-artifacts/`` and in the report figure is
written by a program from a real run; nothing is typed by hand.

    python scripts/wp_line_artifacts.py --out docs/production/run-artifacts
    python scripts/wp_line_artifacts.py --out docs/production/run-artifacts \
        --online --reports 15050,15048,15047,15045,15044

What it produces:

=============== ==========================================================
file            produced by
=============== ==========================================================
line_report.json          ``ke.wp_line.run_line`` over ``tests/fixtures/extraction``
synthesis_input.json      ``assemble_synthesis_input`` over the *clearing* subset
line_report_ok_subset.json the same subset run (only packages that can clear)
benchmark.json            ``run_benchmark`` (reference table in GATE-RULES.md
                          vs computed verdicts + mutation matrix)
asset_registration.json   process 01 against the live platform (``--online``)
                         or the offline fixture sources (default)
figures/wp_line_benchmark.png  matplotlib, from ``benchmark.json`` only
=============== ==========================================================
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ke import wp_gate, wp_line  # noqa: E402

FIXTURES = wp_line.FIXTURES
OK_SUBSET = ("ok-basic", "ok-verified", "ok-zero-claim")
DEFAULT_REPORTS = "15050,15048,15047,15045,15044"


def _dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    print(f"wrote {path}")


def _ok_subset_root(dest: Path) -> Path:
    """Copy only the fixtures that are *designed* to clear their exit gate."""
    root = dest / "extraction"
    root.mkdir(parents=True, exist_ok=True)
    for name in OK_SUBSET:
        shutil.copytree(FIXTURES / name, root / name)
    for sub in ("sources", "ledgers", "tickets"):
        shutil.copytree(FIXTURES / sub, root / sub)
    return root


def make_figure(bench: dict, dest: Path) -> Path:
    """Two panels, all values read from ``benchmark.json``."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 4.4),
                                   gridspec_kw={"width_ratios": [1.15, 1]})
    metrics = bench["metrics"]
    names = list(metrics)
    values = [metrics[n] * 100 for n in names]
    ax1.bar(range(len(names)), values, color="#2f6f9f")
    ax1.set_xticks(range(len(names)))
    ax1.set_xticklabels([n.replace("_", "\n") for n in names], fontsize=8)
    ax1.set_ylim(0, 110)
    ax1.set_ylabel("agreement / coverage [%]")
    for i, v in enumerate(values):
        ax1.text(i, v + 2, f"{v:.1f}", ha="center", fontsize=8)
    ax1.set_title(f"declared vs computed (n={bench['n_fixtures']} fixtures, "
                  f"{bench['n_mutations']} mutations)", fontsize=9)

    rules = sorted({r for row in bench["mutations"] for r in row["got_rules"]}
                   | {r for row in bench["fixtures"].values() for r in row["got_rules"]})
    counts = [sum(1 for row in bench["mutations"] if r in row["got_rules"])
              for r in rules]
    ax2.barh(range(len(rules)), counts, color="#9f5d2f")
    ax2.set_yticks(range(len(rules)))
    ax2.set_yticklabels(rules, fontsize=7)
    ax2.invert_yaxis()
    ax2.set_xlabel("mutants that reddened the rule")
    ax2.set_title("rule sensitivity (mutation matrix)", fontsize=9)
    ax2.set_xlim(0, max(counts) + 1 if counts else 1)
    fig.tight_layout()
    dest.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(dest, dpi=160)
    plt.close(fig)
    print(f"wrote {dest}")
    return dest


def _table(headers, rows) -> list[str]:
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return out


def write_results_doc(out: Path, bench: dict, line: dict, ok_line: dict,
                      bundle: dict, asset: dict | None) -> Path:
    """Render RESULTS.md from the JSON artefacts only (no hand-typed numbers)."""
    lines = ["# Production-line runner — results (generated)", "",
             "Every number below is read from the JSON files in this directory;",
             "regenerate with `python scripts/wp_line_artifacts.py`.", ""]

    lines += ["## Five processes (declared in code, spec: PRODUCTION-LINE-v1 §2)", ""]
    lines += _table(
        ["process", "difficulty", "parallelism", "agent tier", "depends on", "exit gate"],
        [[p, spec["difficulty"], spec["parallelism"], spec["agent_tier"],
          ", ".join(spec["depends_on"]) or "—", spec["exit_gate"]]
         for p, spec in wp_line.PROCESSES.items()])
    lines.append("")

    lines += ["## Fixture matrix: reference (GATE-RULES.md) vs computed", ""]
    lines += _table(
        ["fixture", "ref verdict", "got verdict", "ref rules", "got rules",
         "ref level", "got level", "verdict/rule/level"],
        [[name, row["ref_verdict"], row["got_verdict"],
          ", ".join(row["ref_rules"]) or "—", ", ".join(row["got_rules"]) or "—",
          row["ref_level"], row["got_level"],
          "/".join("ok" if row[k] else "DIFF"
                   for k in ("verdict_match", "rules_match", "level_match"))]
         for name, row in sorted(bench["fixtures"].items())])
    lines.append("")

    lines += ["## Benchmark metrics vs predeclared thresholds", ""]
    lines += _table(["metric", "threshold", "got", "pass"],
                    [[k, bench["thresholds"][k], f"{bench['metrics'][k]:.4f}",
                      "yes" if bench["metrics"][k] >= bench["thresholds"][k] else "NO"]
                     for k in bench["thresholds"]])
    lines.append("")
    lines.append(f"Rule coverage: {bench['rules']['n_exercised']}/"
                 f"{bench['rules']['n_implemented']} implemented rules reddened "
                 f"(uncovered: {bench['rules']['uncovered'] or 'none'}).")
    lines.append("")

    lines += ["## Mutation matrix (one invariant reddened at a time)", ""]
    lines += _table(["mutant", "invariant broken", "expected rule", "rules that fired",
                     "gate verdict", "detected"],
                    [[m["name"], m["breaks"], m["expect_rule"],
                      ", ".join(m["got_rules"]) or "—", m["got_verdict"],
                      "yes" if m["detected"] else "NO"]
                     for m in bench["mutations"]])
    lines.append("")

    lines += ["## Line run over the fixture root", ""]
    lines += _table(["process", "packages", "cleared", "failed", "blocked upstream"],
                    [[p["task_type"], p["n_packages"], p["n_cleared"], p["n_failed"],
                      p["n_blocked_upstream"]] for p in line["processes"]])
    lines.append("")
    lines.append(f"base_processing_complete={line['base_processing_complete']}, "
                 f"synthesis_unblocked={line['synthesis_unblocked']} "
                 f"(a failing upstream package blocks 05 by design).")
    lines.append("")

    lines += ["## 05 synthesis input over the clearing subset", ""]
    lines += _table(["package", "report", "level", "claims"],
                    [[p["package_id"], p["report_id"], p["level"], p["n_claims"]]
                     for p in bundle["eligible_packages"]])
    lines.append("")
    lines += _table(["refused package", "code", "detail"],
                    [[r["package_id"], r["code"], r["detail"]] for r in bundle["refusals"]])
    lines.append("")
    lines.append(f"ready={bundle['ready']}, claims={bundle['n_claims']}, "
                 f"duplicate candidates={bundle['n_duplicate_candidates']}, "
                 f"ok-subset cleared={sum(p['n_cleared'] for p in ok_line['processes'])}.")
    lines.append("")

    if asset:
        lines += [f"## Process 01 — asset registration ({asset.get('mode', '?')})", ""]
        lines += _table(["report id", "reachable", "source hash (sha256)", "chars"],
                        [[r["report_id"], r["reachable"], r.get("source_hash") or "—",
                          r.get("length_chars") or "—"] for r in asset["reports"]])
        lines.append("")
    dest = out / "RESULTS.md"
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {dest}")
    return dest


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(ROOT / "docs" / "production" / "run-artifacts"))
    ap.add_argument("--figures", default=str(ROOT / "docs" / "production" / "figures"))
    ap.add_argument("--online", action="store_true",
                    help="process 01 reads the live platform ($TENSOR_API_BASE)")
    ap.add_argument("--reports", default=DEFAULT_REPORTS)
    ap.add_argument("--skip-live", action="store_true", help="keep the previous asset run")
    args = ap.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    log: list[str] = ["# Production-line runner — run log (generated)\n"]

    # 1. the whole fixture matrix (five processes, 8 extraction packages)
    report = wp_line.run_line(
        FIXTURES, resolver=wp_gate.DirSourceResolver(FIXTURES / "sources"),
        review_ledger_dir=FIXTURES / "ledgers", tickets_dir=FIXTURES / "tickets",
        prompts_dir=wp_line.PROMPTS_DIR)
    _dump(out / "line_report.json", report)
    ext = next(p for p in report["processes"]
               if p["task_type"] == "03-knowledge-extraction")
    log.append(f"- fixture matrix: {ext['n_packages']} extraction packages, "
               f"{ext['n_cleared']} cleared, {ext['n_failed']} failed, "
               f"{ext['n_blocked_upstream']} blocked upstream; "
               f"base_processing_complete={report['base_processing_complete']}")

    # 2. the clearing subset + the 05 input bundle it produces
    with tempfile.TemporaryDirectory(prefix="wp-line-ok-") as tmp:
        ok_root = _ok_subset_root(Path(tmp))
        ok_report = wp_line.run_line(
            ok_root, resolver=wp_gate.DirSourceResolver(ok_root / "sources"),
            review_ledger_dir=ok_root / "ledgers", tickets_dir=ok_root / "tickets",
            prompts_dir=wp_line.PROMPTS_DIR)
        _dump(out / "line_report_ok_subset.json", ok_report)
        bundle = wp_line.assemble_synthesis_input(ok_root, ok_report)
        _dump(out / "synthesis_input.json", bundle)
        log.append(f"- clearing subset: {len(OK_SUBSET)} packages, "
                   f"synthesis ready={bundle['ready']}, "
                   f"eligible={bundle['n_eligible_packages']}, "
                   f"refused={bundle['n_refused_packages']}, "
                   f"claims={bundle['n_claims']}, "
                   f"duplicate_candidates={bundle['n_duplicate_candidates']}")
        for refusal in bundle["refusals"]:
            log.append(f"  - refused {refusal['package_id']}: {refusal['code']} "
                       f"({refusal['detail']})")

    # 3. benchmark against the pre-existing reference table + mutation matrix
    bench = wp_line.run_benchmark(FIXTURES)
    _dump(out / "benchmark.json", bench)
    for name, value in bench["metrics"].items():
        log.append(f"- benchmark {name}: {value:.4f} "
                   f"(threshold {bench['thresholds'][name]})")
    make_figure(bench, Path(args.figures) / "wp_line_benchmark.png")
    log.append(f"- rule coverage: {bench['rules']['n_exercised']}/"
               f"{bench['rules']['n_implemented']} implemented rules reddened by at "
               f"least one mutant or fixture; uncovered={bench['rules']['uncovered']}")

    # 4. process 01 against the live platform (real reports, real hashes)
    if not args.skip_live:
        ids = [r.strip() for r in args.reports.split(",") if r.strip()]
        if args.online:
            resolver = wp_gate.ApiSourceResolver()
            mode = "live platform"
        else:
            resolver = wp_gate.DirSourceResolver(FIXTURES / "sources")
            mode = "offline fixture sources"
        live = wp_line.register_assets(ids, resolver, out / "packages-01",
                                      mission_id="15913")
        live["mode"] = mode
        live["report_ids"] = ids
        _dump(out / "asset_registration.json", live)
        log.append(f"- process 01 ({mode}): {live['n_reachable']}/{live['n_reports']} "
                   f"reachable, {live['n_unreachable']} unreachable")
        for row in live["reports"]:
            log.append(f"  - {row['report_id']}: reachable={row['reachable']} "
                       f"hash={row.get('source_hash')} chars={row.get('length_chars')}")

    write_results_doc(out, bench, report, ok_report, bundle,
                      json.loads((out / "asset_registration.json").read_text())
                      if (out / "asset_registration.json").is_file() else None)
    log.append("")
    log.append("Regenerate with: python scripts/wp_line_artifacts.py --out "
               f"{args.out}" + (" --online" if args.online else "") + "\n")
    (out / "RUN-LOG.md").write_text("\n".join(log), encoding="utf-8")
    print(f"wrote {out/'RUN-LOG.md'}")
    return 0 if bench["pass"] else 3


if __name__ == "__main__":
    raise SystemExit(main())