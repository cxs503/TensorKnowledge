"""wp-11478-01 · 01-asset-registration for report 11478.

Registers the source assets referenced by the report markdown (no extraction, no verification
of upstream numbers). Every registered asset carries a byte-exact locator into the report
markdown plus a machine-checked `resolution_check` backing its declared resolution status.

Inputs (produced by scripts/kf_fetch_11478.py):
  runs/wp-11478-01/report_11478.json   raw platform record
  runs/wp-11478-01/report_11478.md     markdown field (source of all locators)

Outputs:
  artifacts/wp-11478-01/asset_manifest.json
  runs/wp-11478-01/register_11478.json   build log (hash gate, per-asset check results)

Design notes:
  * locators are literal-substring spans, so "resolvable" is a decidable predicate:
    quote in markdown, count == 1, char/line offsets recomputed from the substring index.
  * absence of external paths is *recorded*, never invented: the report is a TensorPlatform
    artifact, so its `docs/m9713/...` and `tools/abm/...` paths cannot exist in this
    TensorKnowledge worktree; the check reports them as unresolved, honestly.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys

REPORT_ID = "11478"
PKG = "wp-11478-01"
EXPECTED_HASH = "b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258"
RUN_DIR = pathlib.Path("runs") / PKG
DOC_DIR = pathlib.Path("docs") / PKG   # docs/ is tracked; artifacts/ is gitignored (see .gitignore)

# External paths the report names; checked against this worktree only (no network guessing).
WT_PATHS = {
    "A01": ["tools/abm/six_dim_power.py"],
    "A02": ["tools/abm/acceptance.py"],
    "A06": ["ops/taskplane/tp_pusher.py"],
    "A08": ["docs/m9713/build_six_dim_power_validation.py"],
    "A09": ["docs/m9713/six_dim_power_validation.json"],
    "A11": ["tests/abm/test_m8716_provenance.py"],
}


def _a(asset_id, asset_class, label, quote, resolution, note, check="span"):
    return dict(asset_id=asset_id, asset_class=asset_class, label=label, quote=quote,
                resolution=resolution, note=note, check=check)


def _lines(md, a, b):
    """1-based inclusive line slice of the source markdown (contiguous span)."""
    lines = md.split("\n")
    return "\n".join(lines[a - 1:b])


def asset_defs(md):
    return [
        _a("A01", "code_module", "六维功效门模块 tools/abm/six_dim_power.py",
           "`tools/abm/six_dim_power.py`", "referenced_unresolved",
           "报告只声明模块位置与设计（纯 stdlib、零领域语义、参数由调用方注入）；"
           "文件不在本工作树（属 TensorPlatform 仓）", check="worktree_path"),
        _a("A02", "acceptance_criterion", "可选 E 环判据 E1_six_dim_advantage_statistical",
           "`tools/abm/acceptance.py` 的可选 E 环判据 `E1_six_dim_advantage_statistical`",
           "referenced_unresolved",
           "判据名与所在文件可定位；acceptance.py 本体不在本工作树", check="worktree_path"),
        _a("A03", "parameter_table", "输入参数表（本次复核所用固定设计，9 行）",
           _lines(md, 9, 19), "resolved_in_source",
           "维数/判决规则/置换分辨率/算例规模/seed 全在表内，是本工序可核的唯一定义面"),
        _a("A04", "numeric_anchor", "置换分辨率下限 min_perm_for_holm(0.05,6)=119",
           "min_perm_for_holm(0.05,6)=119", "resolved_in_source",
           "单值锚点；报告 §⑤ 另以「B≥119」复述同一约束"),
        _a("A05", "pipeline_gate_pattern", "推送门禁排除正则 _EXCLUDE=^(artifacts?/|runs/|results-/)",
           "`_EXCLUDE=^(artifacts?/|runs/|results-/)`", "resolved_in_source",
           "根因声明：证据目录被整目录滤除（§⑤ 第 1 条同义复述）；本工序不复核门禁实现"),
        _a("A06", "code_module", "推送脚本 ops/taskplane/tp_pusher.py",
           "`ops/taskplane/tp_pusher.py`", "referenced_unresolved",
           "报告称 _EXCLUDE/_EXCLUDE2 位于此文件；文件不在本工作树", check="worktree_path"),
        _a("A07", "vcs_commit", "历史提交 48f78f87（取回构建脚本的来源）",
           "历史提交 48f78f87", "referenced_unresolved",
           "外部仓库提交号；本仓对象库无此对象（git cat-file 失败）", check="git_object"),
        _a("A08", "script", "构建脚本与其复现命令 docs/m9713/build_six_dim_power_validation.py",
           "`python docs/m9713/build_six_dim_power_validation.py`", "referenced_unresolved",
           "复现命令原文；脚本不在本工作树，命令无法在本仓执行", check="worktree_path"),
        _a("A09", "artifact", "证据工件 docs/m9713/six_dim_power_validation.json",
           "生成 `docs/m9713/six_dim_power_validation.json`", "referenced_unresolved",
           "报告 §③ 声明全部数值取自该工件；工件不在本工作树，故数值溯源链在本工序未闭合",
           check="worktree_path"),
        _a("A10", "figure_product", "构建脚本附带产出的「两联图」",
           "与两联图；模拟侧结果与历史 seed 逐位一致", "referenced_unresolved",
           "图件本体未随报告提交，平台 figures 仅 1 张（A15）；此为脚本副产物声明",
           check="figure_asset"),
        _a("A11", "test_module", "溯源守卫测试 tests/abm/test_m8716_provenance.py（38 条）",
           "新增 `tests/abm/test_m8716_provenance.py`（38 条）", "referenced_unresolved",
           "测试文件不在本工作树；「38 条」「161 passed」属上游自报，本工序未运行", check="worktree_path"),
        _a("A12", "table", "③ 计算结果表（12 行·量/实测/比较基准/判定）",
           _lines(md, 37, 50), "resolved_in_source",
           "12 个数值行可在原文逐字定位；数值正确性属上游，本工序只登记"),
        _a("A13", "table", "⑥ 误差判定表（7 行·关键量/基准/误差/<3%？）",
           _lines(md, 71, 79), "resolved_in_source",
           "含 3 行显式「否」判定，是报告诚实申报面"),
        _a("A14", "figure_declaration", "无场量云图声明（统计方法任务无空间场）",
           "无物理场（无空间网格、无场量分布），故「场量云图」不适用", "declared_absent",
           "场量云图声明为不适用；平台 figures 字段非空（替代图见 A15）", check="figure_absent"),
        _a("A15", "figure", "三面板比较/校准图（平台 figures: six_dim_power_evidence.png）",
           "三面板，全部由工件 JSON 程序化生成", "resolved_in_platform_record",
           "图件不在 markdown 内，但平台记录 figures[0] 存在（1 条），故登记为平台记录内可解析",
           check="platform_figures"),
        _a("A16", "limitation_set", "§⑤ 注意点与适用边界（6 条）",
           _lines(md, 60, 67), "resolved_in_source",
           "门禁根因/解析漂移/seed 纪律/MC 噪声/适用边界/统计≠物理，六条原文"),
        _a("A17", "numeric_series", "族判决功效 vs n 数列（8 点）",
           "0.142/0.242/0.458/0.617/0.825/0.975/0.967/1.000", "resolved_in_source",
           "单行 8 值；点数与 n 网格 {9,12,16,20,26,32,40,60} 对齐（本工序只登记不复算）"),
        _a("A18", "toolchain", "工具链声明（Python 3.11 + stdlib + matplotlib + pytest）",
           "工具链：Python 3.11 + stdlib（random/math/statistics）+ matplotlib（仅作图）+ pytest。",
           "resolved_in_source", "本工序自有工具链于 runs 内记录，不复用上游声明"),
        _a("A19", "numeric_anchor", "功效正控 ρ=0.7 检出率 0.880 与 CP CI [0.844, 0.910]",
           "0.880（CP CI [0.844, 0.910]）", "resolved_in_source",
           "与 §⑥ 解析基准 0.8765 配对的点估计；§⑥ 自报误差 0.40%"),
        _a("A20", "upstream_change_reference", "上游 m8719 精度修复：t 分位 Cornish-Fisher→精确分位",
           "m8719 把 t 分位从 Cornish-Fisher 展开改为精确分位", "resolved_in_source",
           "解释「解析参照列漂移 ≤0.4%」的因果声明；属上游变更记录，本工序不复核"),
        _a("A21", "provenance_discipline", "34 个文档印值↔工件重算值逐项钉死",
           "34 个文档印值 ↔ 工件重算值逐项钉死", "resolved_in_source",
           "零手抄机制的声明面；对应测试体 A11（未在本工作树）"),
    ]


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def build_locator(md: str, quote: str) -> dict:
    n = md.count(quote)
    if n != 1:
        raise SystemExit(f"FATAL: quote not unique/found ({n} hits): {quote[:60]!r}")
    start = md.index(quote)
    end = start + len(quote)
    start_line = md.count("\n", 0, start)
    end_line = start_line + quote.count("\n")
    return dict(method="char_span", start_char=start, end_char=end,
                start_line=start_line, end_line=end_line, quote=quote, unique=True)


def section_map(md: str):
    """line index -> enclosing heading text (①-⑥ sections of the report)."""
    out, cur = [], "(preamble)"
    for ln in md.split("\n"):
        if ln.startswith("#"):
            cur = ln.strip()
        out.append(cur)
    return out


def run_check(asset, worktree: pathlib.Path, payload: dict, md: str) -> dict:
    aid, kind = asset["asset_id"], asset["check"]
    if kind == "worktree_path":
        paths = WT_PATHS[aid]
        missing = [p for p in paths if not (worktree / p).exists()]
        return dict(check="worktree_path_exists", paths=paths, missing=missing,
                    result="unresolved" if missing else "resolved",
                    detail="报告属 TensorPlatform 仓，路径在本（TensorKnowledge）工作树预期缺失")
    if kind == "git_object":
        sha = re.search(r"[0-9a-f]{7,40}", asset["quote"]).group(0)
        try:
            r = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], cwd=str(worktree),
                               capture_output=True, timeout=30)
            ok = r.returncode == 0
            return dict(check="git_cat_file", object=sha, exit_code=r.returncode,
                        result="resolved" if ok else "unresolved")
        except Exception as exc:  # pragma: no cover - environment dependent
            return dict(check="git_cat_file", object=sha, result="unresolved", error=str(exc))
    if kind == "platform_figures":
        figs = payload.get("figures") or []
        return dict(check="platform_figures_field", platform_figures_count=len(figs),
                    figures=[f.get("name") for f in figs if isinstance(f, dict)],
                    result="present" if figs else "absent")
    if kind == "figure_absent":
        # The asset is specifically a FIELD-CONTOUR figure; the platform figures field may still
        # hold comparative plots. Scan the figure names/captions for field-plot vocabulary instead
        # of using "figures is empty" as a proxy (that proxy would be wrong here).
        figs = [f for f in (payload.get("figures") or []) if isinstance(f, dict)]
        terms = ("云图", "contour", "field plot", "场量")
        hits = [f.get("name") for f in figs
                if any(t in ((f.get("name") or "") + " " + (f.get("caption") or "")) for t in terms)]
        return dict(check="platform_figures_field_scan", terms=list(terms),
                    platform_figures_count=len(figs),
                    figures=[f.get("name") for f in figs], field_plot_hits=hits,
                    result="absent" if not hits else "present",
                    detail="本资产指「场量云图」；平台 figures 内为替代比较/校准图（见 A15），"
                           "名称与图注均无场量云图词汇")
    if kind == "figure_asset":
        return dict(check="figure_reference_in_source", result="unresolved",
                    detail="原文仅声明脚本产出两联图，未给文件名/路径")
    # default: the locator itself is the verification
    loc = asset["locator"]
    ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"] and loc["unique"]
    return dict(check="char_span_in_source_markdown", result="resolved" if ok else "unresolved",
                span_roundtrip=ok)


def main() -> int:
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / f"report_{REPORT_ID}.json").read_text())
    md = (RUN_DIR / f"report_{REPORT_ID}.md").read_text()

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {EXPECTED_HASH}")
        return 2

    worktree = pathlib.Path(".").resolve()
    sections = section_map(md)
    assets, log = [], []
    for d in asset_defs(md):
        loc = build_locator(md, d["quote"])
        asset = dict(asset_id=d["asset_id"], asset_class=d["asset_class"], label=d["label"],
                     in_report_section=sections[loc["start_line"]],
                     locator=loc, resolution=d["resolution"], note=d["note"])
        asset["resolution_check"] = run_check(dict(asset, quote=d["quote"], check=d["check"]), worktree, payload, md)
        assets.append(asset)
        log.append(dict(asset_id=asset["asset_id"], resolution=asset["resolution"],
                        check=asset["resolution_check"]["check"],
                        check_result=asset["resolution_check"]["result"],
                        start_char=loc["start_char"], end_char=loc["end_char"]))

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("FATAL: duplicate asset_id")
    quotes = [a["locator"]["quote"] for a in assets]
    non_unique = [q[:40] for q in quotes if md.count(q) != 1]
    if non_unique:
        raise SystemExit(f"FATAL: non-unique quotes: {non_unique}")

    out_path = DOC_DIR / "asset_manifest.json"
    ignored = subprocess.run(["git", "check-ignore", "-q", str(out_path)], cwd=str(worktree),
                             capture_output=True).returncode == 0
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v2",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "source": {
            "uri": f"tensor://reports/{REPORT_ID}",
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": md_hash,
            "chars": len(md),
            "bytes_utf8": len(md.encode()),
            "title": payload.get("title"),
            "scenario_key": payload.get("scenario_key"),
            "platform_figures": [f.get("name") for f in (payload.get("figures") or [])
                                 if isinstance(f, dict)],
            "platform_tags": payload.get("tags") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "resolved_in_platform_record": by_res.get("resolved_in_platform_record", 0),
        },
        "assets": assets,
        "claims": json.loads((RUN_DIR / "claims_11478.json").read_text())
        if (RUN_DIR / "claims_11478.json").exists() else [],
        "integrity": {
            "quote_uniqueness": "all_pass",
            "hash_recomputed_locally": md_hash,
            "hash_matches_contract": md_hash == EXPECTED_HASH,
            "locator_roundtrip": "all_pass",
            "no_duplicate_ids": len(ids) == len(set(ids)),
            "verification_status": "not_verified_by_platform_gate",
            "upstream_numbers_recomputed": False,
            "output_path": str(out_path),
            "output_path_gitignored": ignored,
        },
    }
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (RUN_DIR / "register_11478.json").write_text(json.dumps(
        dict(package_id=PKG, source_hash="sha256:" + md_hash, counts=manifest["counts"],
             output_path=str(out_path), output_gitignored=ignored, assets=log),
        ensure_ascii=False, indent=2))
    print(json.dumps(dict(assets=len(assets), counts=manifest["counts"]), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())