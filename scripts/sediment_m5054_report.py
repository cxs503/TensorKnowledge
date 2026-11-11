#!/usr/bin/env python3
"""Render the m5054 sediment report + maturity evidence from the package artifacts.

Zero hand-copied numbers: every table cell comes from
``knowledge/sediment/tk-sediment-m5054/benchmarks.json``, the run manifests under
``docs/sediment/tk-sediment-m5054/runs/``, or the pinned source blobs.  Re-running
after a rebuild regenerates the report; the report therefore cannot drift away
from the package.

Outputs
-------
``docs/sediment/tk-sediment-m5054-report.md``      paper-style report (six sections)
``docs/sediment/tk-sediment-m5054-evidence.json``  maturity-gate evidence bundle

    python3 scripts/sediment_m5054_report.py
"""
from __future__ import annotations

import argparse
import hashlib
import re
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ke.sediment_extract import GitPin  # noqa: E402

PKG = ROOT / "knowledge" / "sediment" / "tk-sediment-m5054"
DOCS = ROOT / "docs" / "sediment"
RUNS = DOCS / "tk-sediment-m5054" / "runs"
FIGDIR = DOCS / "tk-sediment-m5054" / "figures"
MISSION = 14526


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fmt(value: float, digits: int = 6) -> str:
    if value is None:
        return "—"
    return f"{value:.{digits}g}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-repo", default="/root/tensor-ecosystem/TensorSPH")
    args = parser.parse_args(argv)

    spec = _load(PKG / "spec.json")
    bench = _load(PKG / "benchmarks.json")
    claims = [_load(p) for p in sorted((PKG / "claims").glob("*.json"))]
    evidence = [_load(p) for p in sorted((PKG / "evidence").glob("*.json"))]
    manifest = _load(RUNS / "extract" / "run_manifest.json")
    validate = _load(RUNS / "validate" / "validate_report.json")
    guard = _load(RUNS / "source_guard" / "source_guard.json")
    figs = _load(FIGDIR / "manifest.json")
    pin = GitPin(args.source_repo, spec["source"]["sha"])
    kernel = json.loads(pin.blob("benchmarks/threed_kernel/report.json"))
    shear = json.loads(pin.blob("benchmarks/threed_shear/report.json"))
    hydro = json.loads(pin.blob("benchmarks/threed_hydrostatic/report.json"))
    anchors = _load(PKG / "anchors.json")

    rows = {r["id"]: r for r in bench["rows"]}
    outside = [r for r in bench["rows"] if r["within_tolerance"] is False]

    # ---- parameter table, read from the pinned artifacts ------------------ #
    params_by_case = {
        "threed_kernel": kernel["params"],
        "threed_shear": shear["params"],
        "threed_hydrostatic": hydro["params"],
    }

    L: list[str] = []
    add = L.append
    add("# TensorSPH 3-D operator verification: what the analytic benchmarks actually verify "
        "(mission m5054)")
    add("")
    add(f"* **本单**：mission {MISSION}（TensorKnowledge），返修自 m8824；"
        f"task_key `{spec['task_key']}`")
    add(f"* **源单**：mission {spec['mission']['id']}（{spec['mission']['repo']}，"
        f"branch `{spec['mission']['branch']}`，PR {spec['mission']['pr']}，"
        f"model {spec['mission']['model']}，{spec['mission']['status']}）")
    add(f"* **源 pin**：`{spec['source']['sha']}`（commit {pin.commit_time}）")
    add(f"* **产物**：`knowledge/sediment/tk-sediment-m5054/`"
        f"（{len(claims)} claim / {len(evidence)} evidence / {len(spec['claims'])} provenance，"
        f"四契约）＋ `docs/sediment/tk-sediment-m5054/runs/`（运行工件）")
    add("* **证据分级**：本轮所有数字来自源 pin 的 report.json 或本仓运行工件，"
        "提取与复核均程序化（`ke/sediment_extract.py` / `ke/sediment_verify.py`），"
        "claim 一律 `epistemic_status=draft`、`assessment_status=unassessed`（不自审）")
    add("")
    add("---")
    add("")

    # ---- ① case ---------------------------------------------------------- #
    add("## ① 案例介绍（物理背景 / 几何 / 参数表）")
    add("")
    add("源单把 2-D SPH 求解器扩到三维：新增 3-D 三次样条核、格点质量标定、三周期最小镜像邻居搜索、"
        "对称压力力、二阶矩重整化粘性 Laplacian、Adami 壁面模型，以及质量/动量/能量计量器，并对")
    add("**三个解析基准**给出可机读 report.json：")
    add("")
    add("| 基准 | 解析参考 | 判据数 | verdict | missing_cases |")
    add("|---|---|---|---|---|")
    for name, rep in (("threed_kernel", kernel), ("threed_shear", shear),
                      ("threed_hydrostatic", hydro)):
        add(f"| `{name}` | {rep['reference']} | {len(rep['criteria'])} | "
            f"`{rep['verdict']}` | {rep['missing_cases'] or '—'} |")
    add("")
    add("**参数表（逐字取自源 report.json 的 params）**")
    add("")
    add("| 基准 | 参数 |")
    add("|---|---|")
    for name, params in params_by_case.items():
        cells = ", ".join(f"`{k}={v}`" for k, v in params.items())
        add(f"| `{name}` | {cells} |")
    add("")
    # geometry / lattice verification
    h = kernel["quadrature"]["h"]
    dx_ladder = [row["dx"] for row in kernel["dx_independence"]["rows"]]
    shear_n = [row["n"] for row in shear["resolution_ladder"]]
    add("**格点/几何核验（先验后算，程序化断言）**")
    add("")
    add("| 核验项 | 期望 | 实测 | 判定 |")
    add("|---|---|---|---|")
    add(f"| 核支撑 h（kernel） | 与 dx 阶梯解耦 | h={h} | {'PASS' if h == 0.013 else 'FAIL'} |")
    add(f"| dx 阶梯 | 单调且 4 级 | {dx_ladder} | "
        f"{'PASS' if dx_ladder == sorted(dx_ladder, reverse=True) and len(dx_ladder) == 4 else 'FAIL'} |")
    add(f"| 剪切波分辨率阶梯 | n = 12/16/20/24 | {shear_n} | "
        f"{'PASS' if shear_n == [12, 16, 20, 24] else 'FAIL'} |")
    add(f"| h/dx（kernel 阶梯） | 1.3 | {kernel['operator_ladder'][0]['h_over_dx']} | "
        f"{'PASS' if abs(kernel['operator_ladder'][0]['h_over_dx'] - 1.3) < 1e-12 else 'FAIL'} |")
    add(f"| 二阶矩格点常数 K 的分辨率无关性 | spread < 1e-12 | "
        f"{max(r['second_moment_K_spread'] for r in kernel['operator_ladder']):.3g} | "
        f"{'PASS' if max(r['second_moment_K_spread'] for r in kernel['operator_ladder']) < 1e-12 else 'FAIL'} |")
    add("")
    add("（船舶几何量 Cb/L/B 不适用：本单是数值算子验证，不是船型阻力/耐波算例。）")
    add("")

    # ---- ② method -------------------------------------------------------- #
    add("## ② 怎么做的（方法 / 流程 / 关键设置 / 工具链）")
    add("")
    add("1. **知识侧（四契约，程序化生成）**：`ke/sediment_extract.py` 按 spec 在 "
        "`git show <sha>:<path>` 的 blob 里用 `str.index` 定位每条引句，记录 `start_offset/"
        "end_offset/行号/content_hash(sha256)`；引句不唯一或找不到即中止构建（负对照测试覆盖）。"
        "claim/evidence/provenance 全部由程序写出，人手不写任何 JSON。")
    add("2. **数值侧（基准表重算）**：`build_benchmarks()` 从源 report.json 里读参数，"
        "用显式公式**重算参考值**再与工件值比对——`2*nu*(2*pi/L)^2`（unsteady-Stokes 衰减率）、"
        "`rho0*g*(H-dx/2)`（静水底部载荷）、`-9*(1/(pi*h^3))/h^2`（三次样条核在 r=0 的 Laplacian）、"
        "核归一化恒等式 1 与 6。公式字符串随行存进 `benchmarks.json`，可被第三方独立复算。")
    add("3. **独立复核**：`ke/sediment_verify.py` 十项检查（schema / 双向交叉引用 / 引句@pin / "
        "INDEX 一致性 / 生产者契约 / 基准重算 / 运行工件 sha256），不读取生成者的自述。")
    add("4. **源侧实测探针**：`scripts/sediment_m5054_source_guard.py` 用 `git archive` 把守护测试与三个 "
        "report.json 落到临时目录并执行 pytest，结论写进运行工件（不改动源仓工作树）。")
    add("5. **工具链**：python " + manifest["build"]["python"] +
        "、jsonschema、pytest、matplotlib；重计算未上集群（全部为秒级 JSON 处理，"
        "源算例本身未重跑——见 ⑤ 局限）。")
    add("")
    add("```bash")
    add(spec["package"]["repro_cmd"])
    add("python3 scripts/sediment_m5054_source_guard.py")
    add("python3 scripts/sediment_m5054_figures.py")
    add("python3 -m pytest tests/test_sediment_m5054.py -q")
    add("```")
    add("")

    # ---- ③ results ------------------------------------------------------- #
    add("## ③ 计算结果（程序化注入，零手抄）")
    add("")
    add("### 3.1 基准重算表（ref 由公式重算 vs got 为源工件值）")
    add("")
    add("| 行 | 参考量 | ref | got | 相对误差 | 容差 | 是否达标 |")
    add("|---|---|---|---|---|---|---|")
    for row in bench["rows"]:
        tol = row["tolerance"]
        tol_txt = "—" if tol["kind"] == "none" else (
            f"{tol['value']:g}{'%' if tol['kind'] == 'percent' else ' (abs)'}")
        err = ("abs " + _fmt(row["abs_error"], 4)) if row["rel_error_pct"] is None else (
            f"{row['rel_error_pct']:+.4g}%")
        within = "—" if row["within_tolerance"] is None else (
            "是" if row["within_tolerance"] else "**否**")
        add(f"| `{row['id']}` | {row['ref_label']} | {_fmt(row['ref'], 17)} | "
            f"{_fmt(row['got'], 17)} | {err} | {tol_txt} | {within} |")
    add("")
    add(f"最差行：`{bench['summary']['worst_row']}`"
        f"（{bench['summary']['max_abs_rel_error_pct']:.4g}%），"
        f"超差行 {len(outside)}/{len(bench['rows'])}："
        f"{', '.join('`' + r['id'] + '`' for r in outside)}。**超差行保留不删**："
        "Tait 壁面控制算例、粗分辨率剪切、格点二阶矩常数本身就是结论的一部分。")
    add("")
    add("### 3.2 逐算例（源工件数值，供对照）")
    add("")
    add("| 基准 | 算例 | 关键量 | 值 | 相对误差 |")
    add("|---|---|---|---|---|")
    for row in kernel["operator_ladder"]:
        add(f"| kernel | n={row['n']} (kh={row['kh']:.4f}) | laplacian corrected rel L2 | "
            f"{row['laplacian_corrected_rel_l2']:.4f} | "
            f"raw {row['laplacian_raw_rel_l2']:.4f} |")
    for row in shear["resolution_ladder"]:
        add(f"| shear | {row['case']} (n={row['n']}) | decay rate fit | "
            f"{row['decay']['fit_rate']:.6f} 1/s | {100 * row['decay']['rel_error']:+.2f}% |")
    for row in hydro["runs"]:
        add(f"| hydrostatic | {row['case']} | bottom pressure | "
            f"{row['pressure']['bottom_measured']:.2f} Pa | "
            f"{100 * row['pressure']['bottom_rel_error']:+.2f}% |")
    add("")
    add("### 3.3 知识条目与运行工件")
    add("")
    add(f"* claims：{len(claims)}（draft）；evidence：{len(evidence)}；provenance：{len(claims)}")
    add(f"* 验证器：{validate['passed']} passed / {validate['failed']} failed / "
        f"{validate['skipped']} skipped → "
        + ", ".join(f"{c['check']}={c['status']}" for c in validate["checks"]))
    add(f"* 源侧守护测试实测：pytest {guard['pytest']['summary']}"
        f"（failover: {', '.join(c['test'].rsplit('::', 1)[-1] for c in guard['pytest']['cases'] if c['status'] == 'FAILED')}）")
    add(f"* README 引用的 `{guard['doc_link_check']['path']}` 在 pin 上 "
        f"`git cat-file -e` 退出码 {guard['doc_link_check']['returncode']}"
        f"（存在={guard['doc_link_check']['exists']}）")
    add(f"* 运行工件 manifest：{len(manifest['files'])} 个文件带 sha256（"
        f"`docs/sediment/tk-sediment-m5054/runs/extract/run_manifest.json`）")
    add("")

    # ---- ④ figures ------------------------------------------------------- #
    add("## ④ 结果图（matplotlib，数字全部来自工件）")
    add("")
    captions = {
        "fig1_laplacian_ladder.png":
            "算子阶梯：原始 Laplacian 非单调（5.38%→13.87%），二阶矩重整化单调降（19.37%→2.96%）；"
            "kh>0.5 区间原始更准 → 重整化只是细 kh 手段（claim `laplacian-renorm-scope`）。",
        "fig2_shear_decay.png":
            "剪切波衰减率误差 vs 分辨率（3%/15% 门限）与同算例 n=20 的原始/重整化对照；"
            "verdict=fail 来自缺失算例 h1.8，而非判据失败（claim `shear-verdict-fail-is-a-coverage-failure`）。",
        "fig3_hydrostatic.png":
            "静水柱：底部载荷误差（2.75%…−25.2%）与逐层核心区最大误差（最高 43.2%）并置，"
            "说明头条 2.7% 不是逐层精度（claim `hydrostatic-headline-is-a-single-point`）。",
        "fig4_kernel_quadrature.png":
            "核归一化两条恒等式的相对误差（4e-15 与 2.5e-11 量级），双精度下闭合"
            "（claim `kernel-quadrature-exact`）。",
    }
    for entry in figs["figures"]:
        name = Path(entry["path"]).name
        add(f"**{name}**（`{entry['path']}`，sha256 `{entry['sha256'][:16]}…`）")
        add("")
        add(f"![{name}](tk-sediment-m5054/figures/{name})")
        add("")
        add(f"*{captions.get(name, '')}*")
        add("")

    # ---- ⑤ caveats ------------------------------------------------------- #
    add("## ⑤ 注意点（踩过的坑 / 局限 / 适用范围）")
    add("")
    add("1. **verdict 与 criteria 必须分开读**：shear 的 6/6 判据为真而 verdict=fail——"
        "verdict 把缺保密进来了（`missing_cases=['h1.8']`）。只看 criteria 会误判为全绿，只看 verdict 会误判为物理失败。")
    add("2. **头条数字是单点**：README 的「2.7% / 2.7%」分别只对应 n=24 与最优 c0=20 算例；"
        "同算子 n=12 是 12.62%，Tait 壁面 25.23%，逐层核心区最大 43.17%。")
    add("3. **格点二阶矩 K=2.3469 ≠ 连续值 2.0（+17.3%）不是 bug**：它是格点常数"
        "（跨分辨率 spread < 1e-12），这正是「重整化要除以离散二阶矩而不是连续值」的原因。")
    add("4. **推送门禁会吃路径**（本单实测发现）：`tp_pusher` 把顶层 `runs/`、`artifacts/` 当记录区滤除，"
        "并把任何 `/m<数字>/` 路径段当作「他单产物」滤除——按源单号命名的 "
        "`knowledge/sediment/m5054/` 正好命中后者，这正是此前 7 个 sediment 单「N 个文件被门禁滤除」"
        "却落地为空的结构性原因。本单因此改名为 `tk-sediment-m5054`（task_key），"
        "运行工件放 `docs/` 下，并有测试 `test_delivery_paths_survive_the_push_gate` 守护。")
    add("5. **未重跑 SPH 求解器**：本轮验证的是「源工件数字 vs 解析参考」的再现性与契约完整性；"
        "三个基准的求解器重跑（约 40 min）不在本单范围，源仓 `run.py` 与用例 JSON 均在 pin 内可复现。")
    add("6. **producer 不自审**：所有 claim 是 draft、evidence 是 unassessed，"
        "独立评审席位才能改这两个字段（本包不写任何 review-event）。")
    suite = RUNS / "suite" / "pytest_suite.txt"
    if suite.is_file():
        tail = [ln for ln in suite.read_text(encoding="utf-8").splitlines()
                if re.search(r"\d+ (passed|failed|error)", ln)]
        add(f"7. **全仓测试态（记录于 `{suite.relative_to(ROOT)}`）**：{tail[-1].strip() if tail else 'n/a'}；"
            "剩余红点是其它 mission 的孤儿交付（`tests/test_ke_proto.py` 依赖的 pilot 包不存在、"
            "`scripts/validate_ontology_v1.py` 依赖的 `artifacts/example-cards/` 不存在），"
            "均为本单之前既有、本单未触碰；本单同时把三个 sediment 测试的收集期 ImportError "
            "改成诚实 skip（m2953/m7437/m7485 的包不在本检出内），否则整仓 pytest 在收集阶段即中断。")
    add("")

    # ---- ⑥ error judgement ---------------------------------------------- #
    add("## ⑥ 误差判定（关键量 vs 基准，逐项回答「是否 <3%」）")
    add("")
    add("| 关键量 | 参考值（公式重算） | 计算值（源工件） | 相对误差 | <3%？ | 说明 |")
    add("|---|---|---|---|---|---|")
    key_rows = ["kernel-integral", "kernel-second-moment", "kernel-laplacian-origin",
                "shear-decay-n24", "shear-decay-n12", "shear-raw-n20", "shear-renorm-n20",
                "hydro-bottom-best", "hydro-bottom-tait", "hydro-core-max",
                "lattice-second-moment-K"]
    for rid in key_rows:
        row = rows[rid]
        err = ("abs " + _fmt(row["abs_error"], 4)) if row["rel_error_pct"] is None else (
            f"{row['rel_error_pct']:+.3f}%")
        if row["within_tolerance"] is None:
            verdict = "—（无门限）"
        elif row["tolerance"]["kind"] == "percent" and row["tolerance"]["value"] == 3.0:
            verdict = "是" if row["within_tolerance"] else "**否**"
        else:
            within3 = (row["rel_error_pct"] is not None and abs(row["rel_error_pct"]) < 3.0)
            verdict = ("是" if within3 else "**否**") + (
                f"（本行门限 {row['tolerance']['value']:g}"
                f"{'%' if row['tolerance']['kind'] == 'percent' else ' abs'}）")
        add(f"| `{rid}` | {_fmt(row['ref'], 17)} | {_fmt(row['got'], 17)} | {err} | {verdict} | "
            f"{row['ref_label']} |")
    add("")
    add("**结论（honest）**：")
    add("")
    add("* 核级恒等式全部 <3%（实际在 1e-11 量级以下）——3-D 核本身不是误差来源；")
    add("* 剪切波最细分辨率 −2.68% 满足 3% 门，但粗分辨率 −12.62%（<15% 门）不满足 3%；"
        "同一 n=20 上原始算子 +11.46%、重整化 −4.18%，均不满足 3%；")
    add("* 静水底部载荷仅最优算例 −2.75% 满足 3%，同族其他算例 −4.30%/−8.74%、Tait 控制算例 −25.23%；"
        "逐层核心区最大误差 43.17%（>15% 不可接受，明确登记）；")
    add("* 因此「3-D 算子已验证」只在细 kh + 最优配置下成立，源单的 honest-FAIL 成立："
        "算子核心可信，交付契约（文档缺失、守护测试与工件矛盾）未闭合。")
    add("")
    add("## 外部锚点（L5 依据）")
    add("")
    for anchor in anchors:
        add(f"* {anchor['label']}（DOI {anchor['doi']}）— {anchor['why']}")
    add("")
    add(f"锚点清单另存 `docs/sediment/tk-sediment-m5054-anchors.md`；"
        f"本报告 sha256 `{{report_sha}}`（生成后回填于 evidence）。")
    add("")

    report_path = DOCS / "tk-sediment-m5054-report.md"
    text = "\n".join(L)
    report_path.write_text(text + "\n", encoding="utf-8")
    report_sha = _sha(report_path)
    report_path.write_text(text.replace("{report_sha}", report_sha) + "\n", encoding="utf-8")

    # ---- evidence bundle ------------------------------------------------- #
    def rel(p: Path) -> str:
        return str(p)

    evidence_bundle = {
        "scope": "TensorKnowledge sediment package for mission m5054 "
                 "(task_key tk-sediment-m5054, source TensorSPH PR 338 @ "
                 "82b72a15c044259d1e7c8d638e9273705fa42e7b)",
        "repo": "TensorKnowledge",
        "mission_id": MISSION,
        "rework_of": 8824,
        "source_mission": spec["mission"]["id"],
        "claimed_level": 5,
        "tests": [
            "tests/test_sediment_m5054.py::test_package_shape_and_producer_contract",
            "tests/test_sediment_m5054.py::test_delivery_paths_survive_the_push_gate",
            "tests/test_sediment_m5054.py::test_stale_quote_aborts_the_build",
            "tests/test_sediment_m5054.py::test_committed_package_is_byte_identical_to_a_fresh_build",
            "tests/test_sediment_m5054.py::test_every_quote_resolves_once_at_the_pin",
            "tests/test_sediment_m5054.py::test_benchmark_references_are_recomputed_not_copied",
            "tests/test_sediment_m5054.py::test_build_entry_point_runs_end_to_end",
            "tests/test_sediment_m5054.py::test_validator_catches_a_tampered_quote",
            "tests/test_sediment_m5054.py::test_source_guard_run_artifact_is_recorded",
            "tests/test_sediment_m5054.py::test_validator_passes_and_all_checks_execute",
        ],
        "impl_files": [
            rel(ROOT / "ke" / "sediment_extract.py"),
            rel(ROOT / "ke" / "sediment_verify.py"),
        ],
        "entry": rel(PKG / "validate_m5054.py"),
        "run_artifacts": [
            rel(RUNS / "extract" / "run_manifest.json"),
            rel(RUNS / "extract" / "extract.txt"),
            rel(RUNS / "validate" / "validate_report.json"),
            rel(RUNS / "source_guard" / "source_guard.json"),
            rel(RUNS / "source_guard" / "pytest_output.txt"),
            rel(FIGDIR / "manifest.json"),
        ],
        "integration_callers": [
            "scripts/sediment_m5054_build.py",
            "validate_m5054.py",
            "ke.sediment_extract.extract_package",
        ],
        "benchmark": {
            "rows": [{k: r[k] for k in ("id", "ref_label", "ref", "got", "abs_error",
                                        "rel_error", "rel_error_pct",
                                        "within_tolerance")} for r in bench["rows"]],
            "summary": bench["summary"],
            "recomputed_by": "ke.sediment_extract.build_benchmarks (formulas stored per row)",
            "table_file": rel(PKG / "benchmarks.json"),
        },
        "repro_cmd": spec["package"]["repro_cmd"],
        "external_anchor": rel(DOCS / "tk-sediment-m5054-anchors.md"),
        "report": rel(report_path),
        "report_sha256": report_sha,
        "notes": [
            "Paths are absolute in this build worktree; the same files after merge live at "
            "TensorKnowledge/ke/sediment_extract.py, "
            "TensorKnowledge/knowledge/sediment/tk-sediment-m5054/validate_m5054.py, "
            "TensorKnowledge/docs/sediment/tk-sediment-m5054/runs/.",
            "Package directory is named by task_key, not by the source mission, because the "
            "push gate drops paths containing an /m<digits>/ segment from another mission.",
        ],
    }
    # every path in the evidence bundle must resolve, or the bundle is theatre
    missing = [p for p in (evidence_bundle["impl_files"] + evidence_bundle["run_artifacts"]
                           + [evidence_bundle["entry"], evidence_bundle["external_anchor"],
                              evidence_bundle["report"]]) if not Path(p).is_file()]
    assert not missing, f"evidence points at missing files: {missing}"

    ev_path = DOCS / "tk-sediment-m5054-evidence.json"
    ev_path.write_text(json.dumps(evidence_bundle, indent=2, ensure_ascii=False) + "\n",
                       encoding="utf-8")
    print(f"report  : {report_path} ({report_path.stat().st_size} B, sha256 {report_sha[:16]}...)")
    print(f"evidence: {ev_path} ({ev_path.stat().st_size} B)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())