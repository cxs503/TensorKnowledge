"""wp-11924-01 asset registration (task_type=01-asset-registration, report_id=11924).

Zero hand-copy: every `quote` in the manifest is *sliced out of the freshly fetched markdown* by a
unique anchor string + a relative line span; the manifest is therefore reproducible byte-for-byte and
contains no re-typed numbers.

Inputs (produced by scripts/kf_fetch_11924.py):
  runs/wp-11924-01/report_11924.md    (markdown payload)
  runs/wp-11924-01/report_11924.json  (raw API payload: id/title/scenario_key/figures/...)

Outputs:
  artifacts/wp-11924-01/asset_manifest.json         (primary deliverable)
  docs/wp-11924-01/asset_manifest.json              (durable mirror, byte-identical)
  runs/wp-11924-01/kf_result.wp-11924-01.json       (kf_result.v1 envelope)
  runs/wp-11924-01/kf_result_block.wp-11924-01.json (same JSON; source of the single ```json block)

Usage: python3 scripts/kf_wp11924_01_register.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys

REPORT_ID = "11924"
PACKAGE_ID = "wp-11924-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "21d915c88bbf78f6f90384f52ce2001f1d7709306c373b159625154ab221bd73"
EXPECTED_CHARS = 13138
SOURCE_URI = "tensor://reports/11924"

RUN_DIR = pathlib.Path("runs/wp-11924-01")
ART_DIR = pathlib.Path("artifacts/wp-11924-01")
DOC_DIR = pathlib.Path("docs/wp-11924-01")

URL_RE = re.compile(r"(https?://[^\s)）`]+|doi:\s*10\.[^\s,;)]+|10\.[0-9]{4,}/[^\s,;)]+)")
PATH_RE = re.compile(r"((?:src|scripts|tests|runs|artifacts|figures)/[A-Za-z0-9_./{},\-]+)")

# Anchor table.  anchor = substring that must occur EXACTLY ONCE in the markdown;
# span = (first_line_offset, last_line_offset) relative to the anchor line.
# The emitted quote is the verbatim slice, never a retyped string.
ASSETS = [
    dict(asset_id="A01", asset_class="document", kind="doc",
         label="报告正文（markdown 全文，含摘要/图表/误差判定）",
         anchor="--doc--", span=(0, -1), resolution="resolved_in_source",
         note="整篇 markdown 即源资产；sha256 见 source.hash，字符数 13138、UTF-8 字节数 22299"),
    dict(asset_id="A02", asset_class="heading", kind="span",
         label="报告标题（与平台 title 字段同源）",
         anchor="# BPM 微观参数三目标联合标定：可行性判定与可辨识性审计", span=(0, 0),
         resolution="resolved_in_source", note="一级标题行"),
    dict(asset_id="A03", asset_class="provenance_header", kind="span",
         label="节点/仓库/分支 + 新增模块 + 原始数据与判据数字来源声明",
         anchor="**节点** P270W2C-N08（任务 m9756）", span=(0, 2),
         resolution="resolved_in_source",
         note="三行溯源声明；其中引用的外部路径分别登记为 A36/A39/A40"),
    dict(asset_id="A04", asset_class="acceptance_table", kind="span",
         label="结论速览表 AC1–AC8（判据 → 目标 → 实测 → 判定）",
         anchor="| 判据 | 目标 | 实测 | 判定 |", span=(0, 9),
         resolution="resolved_in_source",
         note="8 条判据的判定标记；本工序只登记，不重新裁定 PASS/FAIL"),
    dict(asset_id="A05", asset_class="statement", kind="span",
         label="核心问题与微观参数向量 θ 的定义",
         anchor="**同一个微观参数向量 θ = (k_b, ε_b, μ_s, μ_d, k_c, k_p) 能否同时满足", span=(0, 0),
         resolution="resolved_in_source", note="θ 六分量定义所在行"),
    dict(asset_id="A06", asset_class="table", kind="span",
         label="§1.2 几何与参数表（试件尺寸/点阵/加载协议/验收目标）",
         anchor="| 项 | 值 |", span=(0, 11),
         resolution="resolved_in_source",
         note="10 行数据；数值仅登记，不换算不复核"),
    dict(asset_id="A07", asset_class="parameter_box", kind="span",
         label="参数盒表（θ 六分量的含义/下界/上界/采样方式）",
         anchor="| θ 分量 | 含义 | 参数盒下界 | 上界 | 采样 |", span=(0, 7),
         resolution="resolved_in_source",
         note="原文界列全为 n/a：参数盒上下界在报告中缺失，如实登记缺失、不补造数值"),
    dict(asset_id="A08", asset_class="procedure", kind="span",
         label="§2 方法七步（响应面/Jacobian/可辨识性/NSGA-II/留出门/应力场/负控复现）",
         anchor="1. **响应面设计**", span=(0, 6),
         resolution="resolved_in_source", note="7 条方法步骤原文，含 33 点/747 任务/916 s 等规模数字"),
    dict(asset_id="A09", asset_class="identifiability_result", kind="span",
         label="AC2 判定：cond(J)=9.063 / rank 3 of 6 / structurally-underdetermined",
         anchor="- cond(J) = **9.063**", span=(0, 1),
         resolution="resolved_in_source", note="条件数行 + 判定行（含英文机器可读结论串）"),
    dict(asset_id="A10", asset_class="table", kind="span",
         label="量纲一化 Jacobian 表（3 响应 × 6 参数）",
         anchor="| UCS | +0.32 | +0.47 |", span=(-2, 2),
         resolution="resolved_in_source", note="表头 + 分隔行 + UCS/σ_t/m 三行"),
    dict(asset_id="A11", asset_class="table", kind="span",
         label="参数相关矩阵表（JᵀJ 归一化，6 × 6，恒零列记 —）",
         anchor="| k_b | +1.00 | -0.36 |", span=(-2, 5),
         resolution="resolved_in_source", note="表头 + 分隔行 + 6 个参数行"),
    dict(asset_id="A12", asset_class="statement_set", kind="span",
         label="结构不可观测参数声明（mu_s / mu_d 列范数 0.000）",
         anchor="**结构不可观测参数**", span=(0, 3),
         resolution="resolved_in_source", note="标题行 + 两个参数条目（含机器可读处置建议串）"),
    dict(asset_id="A13", asset_class="recommendation", kind="span",
         label="机器可读降维建议（k_c + k_p 合并，γ = 6.71）",
         anchor="机器可读降维建议：", span=(2, 2),
         resolution="resolved_in_source", note="建议段唯一一条条目"),
    dict(asset_id="A14", asset_class="table", kind="span",
         label="AC3 参考 θ 的三目标实测与满足性表",
         anchor="| UCS ∈ [5.0, 15.0] MPa | 1.010 MPa | 否 |", span=(-2, 2),
         resolution="resolved_in_source", note="表头 + 分隔行 + UCS / σc/σt / m CI 三行"),
    dict(asset_id="A15", asset_class="branch_verdict", kind="span",
         label="AC3 三分支判定：参考 θ 落分支 (c)（含英文机器可读串）",
         anchor="参考 θ 的判定：**分支 (c)**", span=(0, 0),
         resolution="resolved_in_source", note="单行判定；分支定义为 a/b/c 三档"),
    dict(asset_id="A16", asset_class="count_record", kind="span",
         label="全部设计点分支计数 a/b/c = 0/0/33 + NSGA-II 前沿规模 80",
         anchor="全部设计点分支计数", span=(0, 0),
         resolution="resolved_in_source", note="单行计数记录"),
    dict(asset_id="A17", asset_class="table", kind="span",
         label="代理（二次响应面）精度表：in-sample R² / LOO R² / LOO RMSE / 样本特征数",
         anchor="| ucs | 0.9965 | 0.9302 |", span=(-2, 2),
         resolution="resolved_in_source",
         note="含 m 的 LOO R² = 0.0904（精度低，原文已声明前沿结论按 LOO 解读）"),
    dict(asset_id="A18", asset_class="table", kind="span",
         label="前沿最小越界量个体（代理值 θ 与三个代理响应）",
         anchor="| k_b=2.59e+05", span=(-2, 0),
         resolution="resolved_in_source", note="单行参数/响应记录；原文声明未回代 DEM"),
    dict(asset_id="A19", asset_class="table", kind="span",
         label="AC4 留出厚度外推表（t=0.05 / 0.80 m）",
         anchor="| 0.05 | 0.397 | 0.376 |", span=(-2, 1),
         resolution="resolved_in_source", note="表头 + 分隔行 + 两个留出厚度行"),
    dict(asset_id="A20", asset_class="numeric_record", kind="span",
         label="幂律拟合参数：m = 262.976、bootstrap CI、σ_ref、端点局部 m 与方向一致性",
         anchor="拟合得到 m = 262.976", span=(0, 0),
         resolution="resolved_in_source", note="单行数字记录（CI 宽度 721.537）"),
    dict(asset_id="A21", asset_class="table", kind="span",
         label="§3.4b 协议细化收敛表（UCS 与 t=0.4 m 拉伸各 1×/2×/4×）",
         anchor="| conv_ucs_1x | 1× | 1.0098 |", span=(-2, 5),
         resolution="resolved_in_source",
         note="表头 + 分隔行 + 6 行；UCS 随加密持续下降（未收敛），属上游 honest 记录"),
    dict(asset_id="A22", asset_class="table", kind="span",
         label="AC5 巴西圆盘中心应力比表（3 分辨率 × 3 平均区 = 9 配置）",
         anchor="| 7 | 4 | 0.12 | 2 | -3.481 |", span=(-2, 8),
         resolution="resolved_in_source",
         note="含 3 个 nan/inf 配置（平均区 0.30）与跨配置偏差 10–788%"),
    dict(asset_id="A23", asset_class="verdict", kind="span",
         label="AC5 判定：中心区 PASS + 跨配置稳健性 FAIL 的如实记录",
         anchor="判定：PASS（容差 15%，按**中心区**读数判定）", span=(0, 0),
         resolution="resolved_in_source",
         note="同一行同时给出 PASS 与稳健性 FAIL，保留上游不确定性表述"),
    dict(asset_id="A24", asset_class="statement_set", kind="span",
         label="AC6 负控分位与 AC7 复现性/准静态门结果（含 FAIL 标记）",
         anchor="- **AC6**：200 组随机 θ 的 UCS 分位", span=(0, 1),
         resolution="resolved_in_source",
         note="两条 bullet：AC6 违反比例 83.5%（FAIL）、AC7 相对差 0.000 / KE 0.022（FAIL）"),
    dict(asset_id="A25", asset_class="figure_declaration", kind="span",
         label="§3.7 六张图件的 markdown 引用与图注（图 1–图 6）",
         anchor="### 3.7 图", span=(0, 24),
         resolution="resolved_in_source",
         note="图件声明在源内可解析；图件二进制本体见 A26（平台 payload 未内嵌 png）"),
    dict(asset_id="A26", asset_class="figure_binary_set", kind="figure_bin",
         label="六张 png 图件本体（figures/p270w2c_n08/*.png：响应面/Jacobian/Pareto/尺寸效应/巴西/UCS）",
         anchor="![response surface](figures/p270w2c_n08/fig_response_surface.png)", span=(0, 0),
         resolution="referenced_unresolved",
         note="报告只给仓库相对路径，平台 figures 字段有 name/caption 但无图件二进制，本工作树（TensorKnowledge）内不存在该路径 → 不可解析"),
    dict(asset_id="A27", asset_class="limitation_set", kind="span",
         label="§4 条 1 / 1b：宽矩阵条件数假象 + 运动学驱动瞬态撕裂（最大坑）",
         anchor="1. **宽矩阵的条件数是“假朋友”**", span=(0, 1),
         resolution="resolved_in_source",
         note="1b 记录首轮战役 t=0.4/0.8 m 强度全为 0、整轮作废，与自适应增量修正"),
    dict(asset_id="A28", asset_class="limitation_set", kind="span",
         label="§4 条 2–4：σ_t 观测面口径 / 尺寸效应 −1/m 与 legacy −2/m 偏差 / m 参照只能是键级输入",
         anchor="2. **σ_t 的观测面选择**", span=(0, 2),
         resolution="resolved_in_source", note="三条口径与偏差声明"),
    dict(asset_id="A29", asset_class="limitation_set", kind="span",
         label="§4 条 4b：UCS 对加载增量敏感（1.01 → 0.86 → 0.67 MPa 未收敛）",
         anchor="4b. **强度对加载增量敏感（UCS）**", span=(0, 0),
         resolution="resolved_in_source", note="单条局限；给出绝对强度不可用的适用范围"),
    dict(asset_id="A30", asset_class="limitation_set", kind="span",
         label="§4 条 5：Love–Weber 应力张量缺切向/摩擦接触力（virial 与 P/(Dt) 差 1.4–2.6 倍）",
         anchor="5. **应力张量缺切向/摩擦接触力**", span=(0, 0),
         resolution="resolved_in_source", note="单条局限"),
    dict(asset_id="A31", asset_class="limitation_set", kind="span",
         label="§4 条 5b：准静态门（KE/外功 ≤1e-3）在拉伸试件上不达标",
         anchor="5b. **准静态门（KE/外功 ≤1e-3）在拉伸试件上不达标**", span=(0, 0),
         resolution="resolved_in_source", note="单条局限；给出未实现的补强方向"),
    dict(asset_id="A32", asset_class="limitation_set", kind="span",
         label="§4 条 6–8：点阵各向异性 / Pareto 来自代理 / 适用范围声明",
         anchor="6. **简单立方点阵的各向异性**", span=(0, 2),
         resolution="resolved_in_source", note="三条局限与适用范围（-10 ℃ 淡水冰量级、ε̇ ≲ 1e-3 s⁻¹）"),
    dict(asset_id="A33", asset_class="table", kind="span",
         label="§5 误差判定表（7 个关键量 vs 基准，逐项 <3%?）",
         anchor="| 复现性 UCS | 同 θ 独立进程重跑 | 0.000 |", span=(-2, 6),
         resolution="resolved_in_source", note="表头 + 分隔行 + 7 个关键量行"),
    dict(asset_id="A34", asset_class="statement", kind="span",
         label="§5 「是否 <3%」显式回答（含 honest FAIL 声明）",
         anchor="**“是否 < 3%”的显式回答**", span=(0, 0),
         resolution="resolved_in_source",
         note="单段结论；明确巴西中心应力比不是 3% 量级问题而是定性不符"),
    dict(asset_id="A35", asset_class="test_record", kind="span",
         label="§6 测试与验收：42 项 pytest + 复现命令 + 审计链",
         anchor="- `tests/test_bpm_calibration_feasibility.py`（42 项，全绿）", span=(0, 3),
         resolution="resolved_in_source",
         note="测试计数与复现命令原文；测试代码本体为外部资产 A38"),
    dict(asset_id="A36", asset_class="code_reference", kind="inline",
         label="新增模块 src/tensordem/bpm_calibration_feasibility.py",
         anchor="**新增模块** `src/tensordem/bpm_calibration_feasibility.py`", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓内相对路径；本工作树（TensorKnowledge）不存在，报告未给 URL/DOI"),
    dict(asset_id="A37", asset_class="code_reference", kind="inline",
         label="战役脚本 scripts/p270w2c_n08_feasibility.py（sample/analyze）+ 图/报告渲染脚本",
         anchor="**战役脚本** `scripts/p270w2c_n08_feasibility.py`", span=(0, 0),
         resolution="referenced_unresolved",
         note="外部仓相对路径，本工作树不可解析"),
    dict(asset_id="A38", asset_class="code_reference", kind="path",
         label="测试文件 tests/test_bpm_calibration_feasibility.py（42 项）",
         anchor="- 运行：`PYTHONPATH=src python -m pytest tests/test_bpm_calibration_feasibility.py -q`",
         span=(0, 0),
         resolution="referenced_unresolved", note="外部仓相对路径，本工作树不可解析"),
    dict(asset_id="A39", asset_class="dataset", kind="inline",
         label="原始数据 runs/p270w2c_n08/records.jsonl（逐任务记录）",
         anchor="**原始数据** `runs/p270w2c_n08/records.jsonl`", span=(0, 0),
         resolution="referenced_unresolved", note="外部仓运行产物，本工作树不可解析"),
    dict(asset_id="A40", asset_class="dataset", kind="inline",
         label="判据数字 artifacts/p270w2c_n08/report.json（报告的唯一数字来源）",
         anchor="**判据数字** `artifacts/p270w2c_n08/report.json`", span=(0, 0),
         resolution="referenced_unresolved", note="外部仓工件，本工作树不可解析"),
    dict(asset_id="A41", asset_class="audit_archive", kind="path",
         label="runs/p270w2c_n08/v{1,2,3}_protocol_superseded/（三轮回炉记录）",
         anchor="`runs/p270w2c_n08/v{1,2,3}_protocol_superseded/`", span=(0, 0),
         resolution="referenced_unresolved", note="外部仓审计留档目录，本工作树不可解析"),
    dict(asset_id="A42", asset_class="code_reference", kind="inline",
         label="legacy 模块 bpm_calibration / bpm_identifiability（t^(−2/m) 口径）",
         anchor="legacy `bpm_calibration`/`bpm_identifiability`", span=(0, 0),
         resolution="referenced_unresolved", note="外部仓模块名，报告未给路径，本工作树不可解析"),
]


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def anchor_line(md: str, anchor: str) -> int:
    n = md.count(anchor)
    if n != 1:
        raise SystemExit("anchor %r occurs %d times (must be exactly 1)" % (anchor, n))
    return md.count("\n", 0, md.index(anchor))


def build_locator(md: str, lines, offs, spec: dict) -> dict:
    if spec["kind"] == "doc":
        return dict(method="document", start_char=0, end_char=len(md), start_line=0,
                    end_line=len(lines) - 1, quote=lines[0], unique=md.count(lines[0]) == 1)
    l0 = anchor_line(md, spec["anchor"])
    if spec["kind"] == "inline":
        start = md.index(spec["anchor"])
        quote = spec["anchor"]
        return dict(method="char_span", start_char=start, end_char=start + len(quote),
                    start_line=l0, end_line=l0, quote=quote, unique=md.count(quote) == 1)
    a, b = l0 + spec["span"][0], l0 + spec["span"][1]
    if not (0 <= a <= b < len(lines)):
        raise SystemExit("bad span for %s: %d..%d" % (spec["asset_id"], a, b))
    start, end = offs[a], offs[b] + len(lines[b])
    quote = md[start:end]
    return dict(method="char_span", start_char=start, end_char=end, start_line=a, end_line=b,
                quote=quote, unique=md.count(quote) == 1)


def scan_addresses(text: str) -> list[str]:
    """URL/DOI/relative-path candidates inside the quoted text (no network guessing)."""
    found = URL_RE.findall(text) + PATH_RE.findall(text)
    seen, out = set(), []
    for f in found:
        f = f.strip().rstrip("`")
        if f and f not in seen:
            seen.add(f)
            out.append(f)
    return sorted(out)


def resolution_check(spec: dict, loc: dict, payload: dict, worktree: pathlib.Path) -> dict:
    kind = spec["kind"]
    if kind == "doc":
        return dict(check="sha256_of_full_markdown_vs_contract", result="resolved",
                    chars=len(loc["quote"]) and loc["end_char"], detail="全文字节级重算；见 source.hash")
    if kind == "inline":
        addr = scan_addresses(loc["quote"])
        rels = [a for a in addr if PATH_RE.match(a)]
        urls = [a for a in addr if a.startswith("http") or a.startswith("10.") or a.startswith("doi:")]
        if rels or urls:
            return dict(check="worktree_path_exists + report_url_doi_scan", result="unresolved",
                        reported_paths=rels, worktree_path_exists={r: (worktree / r).exists() for r in rels},
                        external_addresses_found=urls,
                        detail="报告只给仓库相对路径，本工作树（TensorKnowledge）不存在，且无 URL/DOI")
        return dict(check="report_url_doi_path_scan", result="unresolved",
                    reported_paths=[], external_addresses_found=[],
                    detail="报告内无可解析路径/URL（仅模块名或引文），不猜测地址")
    if kind == "span":
        return dict(check="char_span_in_source_markdown", result="resolved",
                    detail="md[start_char:end_char] == quote 且该 quote 在全文唯一")
    if kind == "figure_bin":
        figs = (payload or {}).get("figures", []) or []
        names = [f.get("name") for f in figs if isinstance(f, dict)]
        has_b64 = any(isinstance(f, dict) and f.get("png_base64") for f in figs)
        rel = "figures/p270w2c_n08"
        return dict(check="platform_figures_field + worktree_path_exists",
                    result="unresolved",
                    platform_figures_declared=len(figs), declared_names=names,
                    png_base64_present=has_b64, worktree_path=rel,
                    worktree_path_exists=(worktree / rel).exists(),
                    detail="声明存在（name/caption）但二进制不可取；相对路径在本工作树不存在")
    if kind == "path":
        addr = scan_addresses(loc["quote"])
        rels = [a for a in addr if PATH_RE.match(a)]
        exists = {r: (worktree / r).exists() for r in rels}
        urls = [a for a in addr if a.startswith("http") or a.startswith("10.") or a.startswith("doi:")]
        return dict(check="worktree_path_exists + report_url_doi_scan", result="unresolved",
                    reported_paths=rels, worktree_path_exists=exists,
                    external_addresses_found=urls,
                    detail=("仅登记报告内给出的相对路径；本工作树不存在，报告无 URL/DOI 可解析"
                            if (rels or urls) else "报告未给出可解析路径/URL（仅模块名），不猜测地址"))
    raise SystemExit("unknown kind " + kind)


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / "report_11924.json").read_text())
    md = (RUN_DIR / "report_11924.md").read_text()

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print("FATAL: markdown sha256 %s != contract source_hash %s" % (md_hash, EXPECTED_HASH))
        return 2
    if len(md) != EXPECTED_CHARS:
        print("FATAL: chars %d != contract chars %d" % (len(md), EXPECTED_CHARS))
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit("duplicate asset_id " + spec["asset_id"])
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec)
        if not loc["unique"]:
            raise SystemExit("quote not unique for %s: %r" % (spec["asset_id"], spec["anchor"]))
        head = "(document)"
        if loc["method"] == "char_span":
            for ln in lines[: loc["start_line"]]:
                if ln.startswith("#"):
                    head = ln.strip()
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=head,
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=resolution_check(spec, loc, payload, worktree),
            note=spec["note"],
        ))

    classes, res = {}, {}
    covered = set()
    for a in assets:
        classes[a["asset_class"]] = classes.get(a["asset_class"], 0) + 1
        res[a["resolution"]] = res.get(a["resolution"], 0) + 1
        if a["locator"]["method"] == "char_span":
            covered |= set(range(a["locator"]["start_char"], a["locator"]["end_char"]))

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI,
            field="markdown",
            hash_alg="sha256",
            hash=md_hash,
            chars=len(md),
            bytes_utf8=len(md.encode()),
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_status=payload.get("status"),
            platform_figures=payload.get("figures", []),
            platform_tags=payload.get("tags", []),
            retrieved_via="GET %s/tensor/reports/%s" % (
                os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"), REPORT_ID),
            local_copy=str(RUN_DIR / "report_11924.md"),
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0),
                    chars_covered_by_char_spans=len(covered),
                    coverage_fraction=round(len(covered) / len(md), 4)),
        assets=assets,
        claims=[],
        claims_note=("按工作包契约 objective.classify_report_type=false 且 delivery.notes 允许 claims 为空数组："
                     "本工序只登记资产与定位，不做 claim 抽取、不作报告类型分类；"
                     "claim 抽取与 verification 由下游工序/平台门负责。"),
        integrity=dict(
            quote_uniqueness="每个 quote 在源 markdown 中出现次数 == 1（scripts/kf_wp11924_01_verify.py 复验）",
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            quotes_sliced_not_retyped=True,
            verification_status="not_verified",
        ),
    )

    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art = ART_DIR / "asset_manifest.json"
    art.write_text(blob)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != art_hash:
        print("FATAL: durable mirror differs from artifact")
        return 3

    out_manifest = dict(artifact_path=str(art), artifact_sha256=art_hash,
                        artifact_bytes=art.stat().st_size)
    out_manifest.update(manifest)

    result = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI,
            source_field="markdown",
            source_hash="sha256:" + md_hash,
            source_chars=len(md),
            source_bytes_utf8=len(md.encode()),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version="1.0",
            lane="C",
            work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(RUN_DIR / "report_11924.md"),
            generator="scripts/kf_wp11924_01_register.py",
            verifier="scripts/kf_wp11924_01_verify.py",
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": out_manifest},
        claims=[],
    )

    for name in ("kf_result.wp-11924-01.json", "kf_result_block.wp-11924-01.json"):
        (RUN_DIR / name).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("chars:", len(md), "bytes:", len(md.encode()))
    print("assets:", len(assets), "classes:", len(classes))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("coverage_fraction:", manifest["counts"]["coverage_fraction"])
    print("manifest:", art, art_hash, art.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())