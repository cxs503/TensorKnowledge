"""Register the source assets of report 9706 (work package wp-9706-01, task_type 01-asset-registration).

Design rules enforced here (contract wp-9706-01 constraints):
  * Zero hand transcription. Every ``quote`` is *sliced out of the report markdown at run time*
    from a programmatic anchor (line search + block rule), then re-checked to be a **unique**
    substring of the markdown before anything is written. Char spans are re-derived from the
    markdown itself, never typed.
  * Registration only, no extraction. ``objective.classify_report_type=false`` and the contract
    notes allow ``claims: []`` -> claims stays empty and says why (no forced claim generation).
  * Nothing is marked verified. ``resolution`` describes **locator resolvability** only;
    provenance.verification_status stays ``not_verified`` (the platform gate computes verification).
  * Unresolvable items are recorded as ``referenced_unresolved`` / ``declared_absent`` together
    with the machine check that backs the status -- never dropped, never given an invented address.
  * Only report_id=9706 is read. No other report is opened or written.

Inputs : runs/wp-9706-01/report_9706.md    (markdown payload, sha256-checked against the contract)
         runs/wp-9706-01/report_9706.json  (raw API payload: title/scenario_key/figures/tags)
Outputs: artifacts/wp-9706-01/asset_manifest.json       (machine artifact)
         docs/wp-9706-01/asset_manifest.json            (byte-identical durable mirror)
         runs/wp-9706-01/kf_result.wp-9706-01.json      (result envelope, kf_result.v1 shape)
         runs/wp-9706-01/kf_result_block.wp-9706-01.json (same JSON, for the single ```json block)

Usage: python3 scripts/kf_register_9706.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys

REPORT_ID = "9706"
PACKAGE_ID = "wp-9706-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_VERSION = "1.0"
LANE = "B"
SOURCE_URI = "tensor://reports/9706"
EXPECTED_HASH = "7d0e024b8630cd3390f5efc0c3f5abfb467e85a869c78126bbb210a1a2d13534"
EXPECTED_CHARS = 12546
CONTRACT_TITLE = "IN145-N04 DP 系统能力评估：凸推力分配 × 环境力平衡 × 操作包线（PSV-6450，判据全过）"
CONTRACT_SCENARIO = "dp_capability"

RUN_DIR = pathlib.Path("runs") / PACKAGE_ID
ART_DIR = pathlib.Path("artifacts") / PACKAGE_ID
DOC_DIR = pathlib.Path("docs") / PACKAGE_ID

# Paths whose existence is probed for cross-repo pointers. They belong to the *upstream* repo
# (ship-performance-platform); this worktree is TensorKnowledge, so absent == "not resolvable here".
UPSTREAM_REPO = "ship-performance-platform"


def _a(aid, cls, label, block, resolution, check, note):
    return dict(asset_id=aid, asset_class=cls, label=label, block=block,
                resolution=resolution, check=check, note=note)


ASSETS = [
    # ---- source-level ----------------------------------------------------------------
    _a("A01", "document", "报告 markdown 全文（源资产本体）",
       dict(kind="doc"), "resolved_in_source", dict(kind="document_covers_source"),
       "整篇 markdown 即本源资产；字节哈希见 source.hash（平台独立重算）。"),
    _a("A02", "heading", "报告正文标题行",
       dict(kind="line", anchor="IN145-N04 动力定位（DP）系统能力评估：推力分配优化", off0=0, off1=0),
       "resolved_in_source", dict(kind="title_matches_platform"),
       "正文标题与平台 title 同源；合同 title 是摘要式命名（更短），差异如实登记不复写。"),
    _a("A03", "provenance_header", "产出仓/分支/节点/物理内核/工件/测试声明（4 行）",
       dict(kind="line", anchor="**仓**：`ship-performance-platform`", off0=0, off1=3),
       "resolved_in_source", dict(kind="char_span"),
       "声明上游仓 ship-performance-platform、分支 agent/m8390、节点 IN145-N04；本工作树无法校验该分支内容，只登记原文。"),
    _a("A04", "section", "摘要（三物理环节 + 一处如实偏差登记）",
       dict(kind="until_marker", anchor="## 摘要", marker="---"),
       "resolved_in_source", dict(kind="char_span"),
       "含结论数字（QP 迭代 3、降级 19%/26%、最差扇区 ≈59 kn）；本工序只登记位置，不复核数值。"),
    # ---- method / parameter tables ---------------------------------------------------
    _a("A05", "table", "环境力模型与证据分级表（风/流/波浪漂移/推力折减）",
       dict(kind="table", anchor="| 要素 | 模型 | 分级 | 不确定度（声明） |"),
       "resolved_in_source", dict(kind="char_span"),
       "上游自报证据分级（REAL/参数化假设）与不确定度带；属报告声明，本工序未复核。"),
    _a("A06", "statement", "几何先校验声明（Δ 相对偏差 2.2e-5、L/B、B/T、Cb 在带内）",
       dict(kind="line", anchor="几何先校验后计算（平台纪律：先证 Cb/L/B）", off0=0, off1=2),
       "resolved_in_source", dict(kind="char_span"),
       "平台几何纪律（先证 Cb/L/B）的落实声明；数值只登记不换算。"),
    _a("A07", "table", "表 1 参考船主尺度与几何一致性校验",
       dict(kind="table", anchor="### 表 1 参考船主尺度与几何一致性校验"),
       "resolved_in_source", dict(kind="char_span"),
       "Lpp/B/T、Δ、Cb、A_F/A_L、A_uv、总系柱推力；参数化参考船（非实船图纸）。"),
    _a("A08", "table", "表 2 推力器布置（5 台：2 尾全回转 + 1 首伸缩 + 2 首隧道）",
       dict(kind="table", anchor="### 表 2 推力器布置"),
       "resolved_in_source", dict(kind="char_span"),
       "含系柱推力与折减后可用推力；DP-2 冗余配置声明。"),
    _a("A09", "figure_diagram", "§2 计算流程图（环境力 → τ_req → SOCP 分配 → 二分包线）",
       dict(kind="fence", anchor="**流程**（`physics/dp_capability/envelope.py`）"),
       "resolved_in_source", dict(kind="char_span"),
       "ASCII 流程图（代码围栏），不是位图；位图资产见 A21–A24。"),
    _a("A10", "method_spec", "§2 关键设置（推力器模型/分配模式/包线判据/工具链）",
       dict(kind="until_blank", anchor="**关键设置**"),
       "resolved_in_source", dict(kind="char_span"),
       "含可行判据（相对残差 ≤1e-4）与二分容差（0.10 kn）等可复现设置。"),
    # ---- result tables ---------------------------------------------------------------
    _a("A11", "table", "表 3 判据②：10 工况点环境力-推力平衡",
       dict(kind="table", anchor="### 表 3 判据②"),
       "resolved_in_source", dict(kind="char_span"),
       "10 行工况 + 残差列；残差数值仅登记，未复核。"),
    _a("A12", "table", "表 4 判据①：随机 24 工况分配器核查",
       dict(kind="table", anchor="### 表 4 判据①"),
       "resolved_in_source", dict(kind="char_span"),
       "QP 迭代 / 推力利用率 / 最大广义力残差。"),
    _a("A13", "table", "表 5 判据③：操作包线（24 航向可抗最大风速）",
       dict(kind="table", anchor="### 表 5 判据③"),
       "resolved_in_source", dict(kind="char_span"),
       "包线主数据集：最差扇区 59.41 kn @75°，最优 120.0 kn @0°，形状比 2.02。"),
    _a("A14", "table", "表 6 判据④：单推力器失效降级（5 个失效工况）",
       dict(kind="table", anchor="### 表 6 判据④"),
       "resolved_in_source", dict(kind="char_span"),
       "三口径（平均/最差航向/包线面积）并列；AZ3 失效包线面积口径 30.38% 略超 30%，正文已如实登记。"),
    _a("A15", "table", "表 7 风-流边界（4 航向 × 7 流速）",
       dict(kind="table", anchor="### 表 7 风-流边界"),
       "resolved_in_source", dict(kind="char_span"),
       "'*' = 超过 120 kn 搜索上限（截断标记，不是真实上限）。"),
    _a("A16", "table", "表 8 关键假设敏感性（7 变体）",
       dict(kind="table", anchor="### 表 8 关键假设敏感性"),
       "resolved_in_source", dict(kind="char_span"),
       "baseline 最差扇区 61.88 kn 与表 5 的 59.41 kn 口径不同（航向取样差异），差异保留不调和。"),
    _a("A17", "table", "表 9 典型工况分配结果（审计用，mode=min_power）",
       dict(kind="table", anchor="### 表 9 典型工况的分配结果"),
       "resolved_in_source", dict(kind="char_span"),
       "逐推力器推力/方位明细，可用于分配结果审计。"),
    _a("A18", "table", "表 10 工件与审计链（字节数 + sha256 前 16 位）",
       dict(kind="table", anchor="### 表 10 工件与审计链（sha256）"),
       "resolved_in_source", dict(kind="char_span"),
       "6 个工件的引用行；全量 sha256 与文件本体不在源内（逐项见 A21–A26）。"),
    _a("A19", "provenance_marker", "表格程序化注入标记 + 生成器声明（TABLES:BEGIN）",
       dict(kind="line", anchor="<!-- TABLES:BEGIN -->", off0=0, off1=2),
       "resolved_in_source", dict(kind="char_span"),
       "TABLES:BEGIN/END 成对标记（END 在表 10 之后）；声明表格由 scripts/gen_dp_capability_doc.py 从 artifacts JSON 程序化注入，是防手抄机制的证据。"),
    # ---- figures ---------------------------------------------------------------------
    _a("A20", "figure_block", "§4 结果图说明块（4 图：极坐标包线/风-流边界/失效降级/分配画像）",
       dict(kind="until_marker", anchor="图件由 `scripts/gen_dp_capability_artifacts.py` 生成", marker="---"),
       "resolved_in_source", dict(kind="char_span"),
       "含出图脚本指针与每图读法；图件字节本体不在源文本内（见 A21–A24）。"),
    _a("A21", "figure_artifact", "dp_capability_polar.png（极坐标操作包线）",
       dict(kind="line", anchor="| `artifacts/dp_capability/dp_capability_polar.png` |", off0=0, off1=0),
       "resolved_in_source", dict(kind="hash_prefix_row", platform_figure="dp_capability_polar"),
       "源内 179017 字节 + 哈希前缀 `08120e114f59dd10…`；全量 sha256 与 PNG 字节不在源内，故只能校验前缀。"),
    _a("A22", "figure_artifact", "dp_wind_current_boundary.png（风-流边界）",
       dict(kind="line", anchor="| `artifacts/dp_capability/dp_wind_current_boundary.png` |", off0=0, off1=0),
       "resolved_in_source", dict(kind="hash_prefix_row", platform_figure="dp_wind_current_boundary"),
       "源内 74891 字节 + 哈希前缀 `98656762fb0dcc7f…`；全量 sha256 与字节不在源内。"),
    _a("A23", "figure_artifact", "dp_failure_degradation.png（失效降级柱状图）",
       dict(kind="line", anchor="| `artifacts/dp_capability/dp_failure_degradation.png` |", off0=0, off1=0),
       "resolved_in_source", dict(kind="hash_prefix_row", platform_figure="dp_failure_degradation"),
       "源内 40985 字节 + 哈希前缀 `f4b3798724649bfc…`；全量 sha256 与字节不在源内。"),
    _a("A24", "figure_artifact", "dp_allocation_profile.png（典型工况推力器利用率）",
       dict(kind="line", anchor="| `artifacts/dp_capability/dp_allocation_profile.png` |", off0=0, off1=0),
       "resolved_in_source", dict(kind="hash_prefix_row", platform_figure="dp_allocation_profile"),
       "源内 30488 字节 + 哈希前缀 `79fc5909c58dbab5…`；全量 sha256 与字节不在源内。"),
    # ---- non-figure artifacts --------------------------------------------------------
    _a("A25", "json_artifact", "dp_capability_report.json（逐点原始数据）",
       dict(kind="line", anchor="| `artifacts/dp_capability/dp_capability_report.json` |", off0=0, off1=0),
       "resolved_in_source", dict(kind="hash_prefix_row"),
       "源内 36254 字节 + 哈希前缀 `11f58960a7503108…`；JSON 本体不在源内，内容未登记。"),
    _a("A26", "json_artifact", "sensitivity.json（敏感性原始结果）",
       dict(kind="line", anchor="| `artifacts/dp_capability/sensitivity.json` |", off0=0, off1=0),
       "resolved_in_source", dict(kind="hash_prefix_row"),
       "源内 1658 字节 + 哈希前缀 `1194cc19f3407fcb…`；JSON 本体不在源内。"),
    _a("A27", "json_artifact", "acceptance.json（逐条判据 ①–⑥ 落 pass 标记）",
       dict(kind="line", anchor="**审计链**：表 10 给出每个工件的 sha256", off0=0, off1=1),
       "referenced_unresolved", dict(kind="artifact_row_absent", name="acceptance.json"),
       "只在 §7 审计链段被提及；表 10 无该文件行（无字节数、无哈希），故不可解析到可校验地址。"),
    # ---- repro / traps / limits ------------------------------------------------------
    _a("A28", "command_block", "§7 复现/验收命令（pytest + 两个生成脚本 + 端点 curl）",
       dict(kind="fence", anchor="## 7 复现 / 验收命令"),
       "resolved_in_source", dict(kind="char_span"),
       "repro 命令块；仓库路径属 ship-performance-platform，本工作树不可执行（见 A39/A40）。"),
    _a("A29", "trap_record", "踩坑 1：方向启发式 + QP 非凸 → 可行工况被误判不可行（SOCP 修正）",
       dict(kind="until_blank", anchor="**踩坑 1（方法学，最重要）**"),
       "resolved_in_source", dict(kind="char_span"),
       "方法学结论；旧实现差异只在 git 历史里，本工序无法校验该历史。"),
    _a("A30", "trap_record", "踩坑 2：可行/不可行边界的对偶渐近平台与停滞退出",
       dict(kind="until_blank", anchor="**踩坑 2**"),
       "resolved_in_source", dict(kind="char_span"),
       "迭代退出策略（全钳制即停 + 残差 4 次不降即停）；最大迭代 40 → 10 量级。"),
    _a("A31", "limitation", "局限 1：绝对幅值偏乐观（59 kn vs 公开 15–30 kn 带）+ 敏感性诊断",
       dict(kind="until_blank", anchor="**局限 1（绝对幅值偏乐观）**"),
       "resolved_in_source", dict(kind="char_span"),
       "报告自认的超差项及工程折减建议；下游不得改写为「判据通过」或抹去。"),
    _a("A32", "limitation", "局限 2：定性判据不是定量基准（拒绝编基准）",
       dict(kind="until_blank", anchor="**局限 2（定性判据不是定量基准）**"),
       "resolved_in_source", dict(kind="char_span"),
       "明确声明不做「与 DNV 图误差 < x%」的断言；抽取时须保留该不确定性。"),
    _a("A33", "limitation", "局限 3：漂移力近似与风系数经验族（无 RAO / 二阶传递函数）",
       dict(kind="until_blank", anchor="**局限 3（漂移力与风系数是近似）**"),
       "resolved_in_source", dict(kind="char_span"),
       "横风艏摇系数 ≈0.108 的不确定度声明。"),
    _a("A34", "limitation", "局限 4：推进器水动力未建模（尾流/方向依赖/吃水纵倾）",
       dict(kind="until_blank", anchor="**局限 4（推进器水动力未建模）**"),
       "resolved_in_source", dict(kind="char_span"),
       "适用边界声明。"),
    _a("A35", "scope_declaration", "适用范围（准静态能力评估）",
       dict(kind="line", anchor="**适用范围**：准静态能力评估", off0=0, off1=1),
       "resolved_in_source", dict(kind="char_span"),
       "准静态口径声明；不含项清单单独登记为 A36（declared_absent）。"),
    _a("A36", "capability_absence", "未纳入能力清单（DP 控制器动力学/波浪瞬时推力波动/锚泊拖轮/冰区）",
       dict(kind="line", anchor="**适用范围**：准静态能力评估", off0=0, off1=1),
       "declared_absent", dict(kind="negation_markers", markers=["不含", "未接入"]),
       "报告以「不含…不含…不含冰区（冰载荷未接入）」显式声明缺席；本工序按缺席登记，不推断其数值。"),
    # ---- error adjudication section ---------------------------------------------------
    _a("A37", "table", "§6 误差判定表（关键量 vs 基准，逐项回答是否 < 3%）",
       dict(kind="table", anchor="| 关键量 | 基准（clean-room / 解析） | 本次结果 | 相对偏差 | 是否 < 3% |"),
       "resolved_in_source", dict(kind="char_span"),
       "12 行逐项判定，含 1 行「不适用（无单值基准）」与 1 行「否——如实登记」；本工序只登记不复判。"),
    _a("A38", "statement", "§6 结论：有解析基准的量全部 < 3%，唯一超差项无定量基准",
       dict(kind="line", anchor="**结论**：凡有**解析/clean-room 基准**的量", off0=0, off1=2),
       "resolved_in_source", dict(kind="char_span"),
       "上游 honest-FAIL 纪律声明；是否成立由下游/平台门判，本工序不背书。"),
    # ---- cross-repo code pointers -----------------------------------------------------
    _a("A39", "code_pointer", "物理内核包 backend/physics/dp_capability/ + 端点 backend/api/dynamic_positioning.py",
       dict(kind="line", anchor="**物理内核**：`backend/physics/dp_capability/`", off0=0, off1=0),
       "referenced_unresolved",
       dict(kind="cross_repo_path", paths=["backend/physics/dp_capability",
                                           "backend/api/dynamic_positioning.py"]),
       "指针属上游仓 ship-performance-platform；本工作树（TensorKnowledge）内不存在，按未解析登记，不猜地址。"),
    _a("A40", "code_pointer", "谱核指针 physics.wave_spectrum_core（平台单源谱核）",
       dict(kind="line", anchor="谱型用平台**单源谱核** `physics.wave_spectrum_core`", off0=0, off1=0),
       "referenced_unresolved", dict(kind="cross_repo_path", paths=["physics/wave_spectrum_core"]),
       "跨仓模块指针；本工作树无法解析，按未解析登记。"),
]

# -------------------------------------------------------------------------------------------
# engine
# -------------------------------------------------------------------------------------------
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def _trim_trailing_blank(lines, i0, i1):
    while i1 > i0 and lines[i1].strip() == "":
        i1 -= 1
    return i1


def resolve_span(lines, block):
    """Return (i0, i1) line indices (0-based, inclusive) for a block spec."""
    kind = block["kind"]
    if kind == "doc":
        return 0, len(lines) - 1
    anchor = block["anchor"]
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor not unique/found ({len(hits)} hits): {anchor!r}")
    a = hits[0]
    if kind == "line":
        return a + block.get("off0", 0), a + block.get("off1", 0)
    if kind == "table":
        if lines[a].lstrip().startswith("|"):
            i0 = a
        else:
            j = a + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            i0 = j
        j = i0
        while j < len(lines) and lines[j].lstrip().startswith("|"):
            j += 1
        i1 = j - 1
        if i1 < i0:
            raise SystemExit(f"empty table block for anchor {anchor!r}")
        return i0, _trim_trailing_blank(lines, i0, i1)
    if kind == "until_blank":
        # skip blank lines right after the anchor (a heading/marker line), then read the block
        j = a + 1
        while j < len(lines) and lines[j].strip() == "":
            j += 1
        while j < len(lines) and lines[j].strip() != "":
            j += 1
        return a, _trim_trailing_blank(lines, a, j - 1)
    if kind == "until_marker":
        j = a + 1
        while j < len(lines) and lines[j].strip() != block["marker"]:
            j += 1
        if j >= len(lines):
            raise SystemExit(f"end marker {block['marker']!r} not found after {anchor!r}")
        return a, _trim_trailing_blank(lines, a, j - 1)
    if kind == "fence":
        j = a + 1
        while j < len(lines) and not lines[j].lstrip().startswith("```"):
            j += 1
        if j >= len(lines):
            raise SystemExit(f"opening fence not found after {anchor!r}")
        i0 = j
        j2 = i0 + 1
        while j2 < len(lines) and not lines[j2].lstrip().startswith("```"):
            j2 += 1
        if j2 >= len(lines):
            raise SystemExit(f"closing fence not found after {anchor!r}")
        return i0, j2
    raise SystemExit(f"unknown block kind {kind!r}")


def build_locator(md: str, lines, offs, block) -> dict:
    i0, i1 = resolve_span(lines, block)
    if block["kind"] == "doc":
        quote = md
        start, end = 0, len(md)
    else:
        start = offs[i0]
        end = offs[i1] + len(lines[i1])
        quote = md[start:end]
    unique = md.count(quote) == 1
    return dict(method="document" if block["kind"] == "doc" else "char_span",
                start_char=start, end_char=end, start_line=i0 + 1, end_line=i1 + 1,
                quote=quote, unique=unique)


def section_of(lines, i0: int) -> str:
    head = "(document)"
    for ln in lines[:i0]:
        if ln.startswith("#"):
            head = ln.strip()
    return head


def resolution_check(spec, loc, md, payload, worktree):
    """Machine check backing the declared resolution status. Never invents a result."""
    chk = spec["check"]
    kind = chk["kind"]
    quote = loc["quote"]
    if kind == "char_span":
        ok = md[loc["start_char"]:loc["end_char"]] == quote and loc["unique"]
        return dict(check="char_span_roundtrip_and_uniqueness", result="resolved" if ok else "unresolved",
                    quote_occurrences=md.count(quote), char_span_len=loc["end_char"] - loc["start_char"])
    if kind == "document_covers_source":
        ok = loc["start_char"] == 0 and loc["end_char"] == len(md) and quote == md
        return dict(check="document_span_equals_whole_markdown", result="resolved" if ok else "unresolved",
                    chars=len(md), sha256=sha256_text(md))
    if kind == "title_matches_platform":
        title = payload.get("title") or ""
        head = quote.lstrip("# ").strip()
        return dict(check="platform_title_vs_heading_line", result="resolved" if title else "unresolved",
                    platform_title=title, heading_line=head,
                    identical=head == title,
                    detail="合同 title 为摘要式命名；正文标题行与平台 title 的异同在此如实记录")
    if kind == "hash_prefix_row":
        m = re.search(r"\|\s*(\d+)\s*\|\s*`([0-9a-f]{16})…`", quote)
        row = dict(check="artifact_row_size_and_hash_prefix_present",
                   result="resolved" if m else "unresolved")
        if m:
            row.update(bytes_declared=int(m.group(1)), sha256_prefix_declared=m.group(2),
                       full_sha256_available=False,
                       detail="源内只有 16 位前缀与字节数；文件本体/全量哈希不在源内，未做字节校验")
        fig_name = chk.get("platform_figure")
        if fig_name:
            names = [f.get("name") for f in (payload.get("figures") or [])]
            row["platform_figure_declared"] = fig_name in names
            row["platform_figures"] = names
        return row
    if kind == "artifact_row_absent":
        name = chk["name"]
        has_row = bool(re.search(r"\|\s*`[^`]*" + re.escape(name) + r"`\s*\|\s*\d+\s*\|", md))
        return dict(check="table10_artifact_row_lookup", result="unresolved" if not has_row else "resolved",
                    queried=name, artifact_row_in_table10=has_row,
                    detail="§7 提及但表 10 无该工件行（无字节数/无哈希）→ 不可解析")
    if kind == "negation_markers":
        found = {mk: (mk in md[loc["start_char"]:loc["end_char"]]) for mk in chk["markers"]}
        return dict(check="absent_capability_markers_in_quote",
                    result="absent" if all(found.values()) else "unresolved", markers=found,
                    detail="报告用否定句声明这些能力未纳入；登记为 declared_absent，不作数值推断")
    if kind == "cross_repo_path":
        paths = chk["paths"]
        present = [p for p in paths if (worktree / p).exists()]
        return dict(check="worktree_path_exists", result="resolved" if present else "unresolved",
                    repo=UPSTREAM_REPO, paths_checked=paths, paths_present_here=present,
                    detail="指针属上游仓；本工作树（TensorKnowledge）内不存在 → 未解析，不猜地址")
    raise SystemExit(f"unknown check kind {kind!r}")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / f"report_{REPORT_ID}.json").read_text(encoding="utf-8"))
    md = (RUN_DIR / f"report_{REPORT_ID}.md").read_text(encoding="utf-8")

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {EXPECTED_HASH}")
        return 2
    if len(md) != EXPECTED_CHARS:
        print(f"FATAL: chars {len(md)} != contract chars {EXPECTED_CHARS}")
        return 2
    if str(payload.get("id")) != REPORT_ID:
        print(f"FATAL: payload id {payload.get('id')!r} != {REPORT_ID!r} (wrong report touched?)")
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen = [], set()
    for spec in ASSETS:
        aid = spec["asset_id"]
        if aid in seen:
            raise SystemExit(f"duplicate asset_id {aid}")
        seen.add(aid)
        loc = build_locator(md, lines, offs, spec["block"])
        if not loc["unique"]:
            raise SystemExit(f"quote not unique for {aid}: {loc['quote'][:80]!r}")
        assets.append(dict(
            asset_id=aid,
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=section_of(lines, loc["start_line"] - 1),
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=resolution_check(spec, loc, md, payload, worktree),
            note=spec["note"],
        ))

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        contract_version=CONTRACT_VERSION,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI,
            field="markdown",
            hash_alg="sha256",
            hash=md_hash,
            chars=len(md),
            bytes_utf8=len(md.encode("utf-8")),
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_title=CONTRACT_TITLE,
            contract_scenario_key=CONTRACT_SCENARIO,
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_figures=payload.get("figures", []),
            platform_tags=payload.get("tags", []),
            platform_created_at=payload.get("created_at"),
            retrieved_via="GET %s/tensor/reports/%s" % (
                os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"), REPORT_ID),
            local_copy=str(RUN_DIR / f"report_{REPORT_ID}.md"),
        ),
        conventions=dict(
            char_offsets="0-based character offsets into the decoded markdown string (str indices, not bytes)",
            line_numbers="1-based, inclusive",
            resolution_meaning=("resolved_in_source = the in-report reference/quote resolves to an exact, "
                                "unique substring of the source markdown; it does NOT mean the referenced "
                                "artifact bytes were obtained or verified"),
        ),
        counts=dict(
            assets=len(assets), by_class=by_class, by_resolution=by_res,
            resolved_in_source=by_res.get("resolved_in_source", 0),
            referenced_unresolved=by_res.get("referenced_unresolved", 0),
            declared_absent=by_res.get("declared_absent", 0),
        ),
        assets=assets,
        claims=[],
        claims_note=("contract objective.classify_report_type=false and notes allow claims: [] -> this package "
                     "registers asset locators only, no claim extraction, no forced claim generation. "
                     "Claim extraction belongs to a downstream work package."),
        integrity=dict(
            quote_uniqueness="every quote confirmed a unique substring of the source markdown "
                             "(scripts/kf_register_9706.py build_locator + scripts/kf_verify_9706.py)",
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            verification_status="not_verified",
            verification_note="verification is computed by the platform gate; nothing here is self-marked verified",
        ),
    )

    art = ART_DIR / "asset_manifest.json"
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art.write_text(blob, encoding="utf-8")
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob, encoding="utf-8")
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != art_hash:
        print("FATAL: durable mirror differs from artifact")
        return 3

    result = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI,
            source_field="markdown",
            source_hash="sha256:" + md_hash,
            source_chars=len(md),
            source_bytes_utf8=len(md.encode("utf-8")),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version=CONTRACT_VERSION,
            lane=LANE,
            mission_id=15665,
            work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(RUN_DIR / f"report_{REPORT_ID}.md"),
            generator="scripts/kf_register_9706.py",
            verifier="scripts/kf_verify_9706.py",
            manifest_path=str(art),
            manifest_sha256="sha256:" + art_hash,
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": manifest},
    )

    (RUN_DIR / f"kf_result.{PACKAGE_ID}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (RUN_DIR / f"kf_result_block.{PACKAGE_ID}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DOC_DIR / f"kf_result.{PACKAGE_ID}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("markdown sha256 :", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("chars/bytes     :", len(md), len(md.encode("utf-8")))
    print("assets          :", len(assets))
    print("by_class        :", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution   :", json.dumps(by_res, ensure_ascii=False))
    print("manifest        :", art, "sha256=" + art_hash)
    print("envelope        :", RUN_DIR / f"kf_result.{PACKAGE_ID}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
