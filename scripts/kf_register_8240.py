#!/usr/bin/env python3
"""KF work package wp-8240-01 (task_type=01-asset-registration, lane C, report_id=8240).

Registers the *assets* of report 8240 (structure/locators only, no extraction):
  * confirms report_id 8240 and the byte hash of its `markdown` field
  * enumerates every asset the markdown actually carries (sections, tables,
    formulas, the ASCII chain diagram, figure references, code/artifact/test
    pointers from the audit chain) with a verbatim, unique source locator
  * classifies each asset's resolvability in *this* worktree
    (resolved_in_source / referenced_unresolved / declared_absent)

No claim is extracted (objective.classify_report_type=false, and the package
notes explicitly allow claims to be an empty array). Nothing is marked
verified: verification is computed by the platform gate.

Inputs (cached by a previous run, or re-fetched with --refetch + TENSOR_TOKEN):
  runs/wp-8240-01/report_8240.md    (markdown payload)
  runs/wp-8240-01/report_8240.json  (raw API payload: id/title/scenario_key/figures/...)

Outputs:
  artifacts/wp-8240-01/asset_manifest.json
  docs/wp-8240-01/asset_manifest.json              (durable mirror, byte-identical)
  docs/wp-8240-01/kf_result.wp-8240-01.json        (result envelope, kf_result.v1)
  runs/wp-8240-01/kf_result.wp-8240-01.json        (same envelope, run copy)

Usage: python3 scripts/kf_register_8240.py [--refetch]
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "8240"
PACKAGE_ID = "wp-8240-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/8240"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "113b007338c90e984af4be66352aae382cd90f7e976725e819825a95bfa46e7d"
EXPECTED_CHARS = 9689
EXPECTED_TITLE = ("EEXI attained 闭合链路（P73W2-N02）：Holtrop 阻力→推进功率→轴系效率→"
                  "gCO₂/(t·nm)，99.9%→<3% 精度传递")
EXPECTED_SCENARIO = "green_eexi_attained_closure"

RUN_DIR = pathlib.Path("runs/wp-8240-01")
ART_DIR = pathlib.Path("artifacts/wp-8240-01")
DOC_DIR = pathlib.Path("docs/wp-8240-01")

# Figure references in the markdown: (asset_id, png filename)
FIGURES = [
    ("A15", "fig_eexi_power_chain.png"),
    ("A16", "fig_eexi_sensitivity.png"),
    ("A17", "fig_eexi_compliance_band.png"),
    ("A18", "fig_eexi_error_before_after.png"),
    ("A19", "fig_eexi_power_speed.png"),
]

# Audit-chain pointers (repo-relative paths in ship-performance-platform).
CODE_POINTERS = [
    ("A24", "code_module_ref", "backend/api/eexi_closure.py",
     "链路/不确定度/三态实现体；不在本工作树（TensorKnowledge）内", "code:"),
    ("A25", "code_module_ref", "backend/api/green_shipping.py",
     "量纲修复 + 路由挂载 + L5 证据层；不在本工作树内", "code:"),
    ("A26", "test_ref", "backend/tests/test_eexi_attained_closure.py",
     "报告声明 25 用例（含跨端点同源闸门与缺陷回归）；测试本体不可解析", "test:"),
    ("A27", "artifact_ref", "artifacts/eexi_attained_closure.json",
     "报告声明「本报告全部数字的来源」；该 JSON 不在本工作树内，故本工序无法交叉复算任何数字", "artifact:"),
    ("A28", "artifact_ref", "artifacts/capabilities.json",
     "GREEN-EEXI 升账记录；不在本工作树内", "artifact:"),
    ("A29", "script_ref", "scripts/gen_eexi_closure_artifact.py",
     "生成链第一段（JSON + 图）；不在本工作树内", "script:"),
    ("A30", "script_ref", "scripts/render_eexi_doc.py",
     "生成链第二段（出本报告）；不在本工作树内", "script:"),
]

# Anchor table: asset_id, class, label, anchor substring (must occur on exactly one
# line of the markdown), line span relative to the anchor line, resolution, note.
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，9,689 字符）",
         anchor=None, span=None, resolution="resolved_in_source",
         note="整篇 markdown 即源资产；sha256 见 source.hash（平台可独立重算）"),
    dict(asset_id="A02", asset_class="heading", label="报告标题（H1）",
         anchor="# EEXI attained 闭合链路：Holtrop 阻力", span=(0, 0),
         resolution="resolved_in_source", note="标题行；与 API title 同源但措辞不同（见 note_title_mismatch）"),
    dict(asset_id="A03", asset_class="metadata", label="任务/战役节点/生成时间/来源仓（行内元数据）",
         anchor="**任务**：m6882 / 战役节点 P73W2-N02", span=(0, 0),
         resolution="resolved_in_source",
         note="声明上游 mission=6882、节点 P73W2-N02、生成时间 2026-11-08T09:40:19.304877+00:00、来源仓 ship-performance-platform"),
    dict(asset_id="A04", asset_class="diagram_ascii", label="EEXI 链路 ASCII 流程图（代码块内容 5 行，不含围栏）",
         anchor="几何 (Lpp,B,T,Cb,Cm,Cwp,ABT,AT) ─┬─► Holtrop-Mennen ─► R_T ─┐",
         span=(0, 4), resolution="resolved_in_source",
         note="几何→阻力→有效功率→推进效率→轴功率→EEXI 的流程示意；纯文本，无外链图件。"
              "引文只取代码块内容（围栏行无载荷），故 manifest 内不含代码围栏字符"),
    dict(asset_id="A05", asset_class="formula", label="化简式 EEXI_attained = R_T(V_ref)·SFC·C_F/(η_D·η_S·η_G·Capacity)",
         anchor="> **EEXI_attained = R_T(V_ref)·SFC·C_F", span=(0, 0),
         resolution="resolved_in_source", note="报告核心解析式（V 与 V_ref 精确抵消后的形式）"),
    dict(asset_id="A06", asset_class="table", label="三参考船主尺度/功率参数表（表头+分隔+3 行）",
         anchor="| 船 | DWT [t] | Lpp×B×T [m] | Cb | MCR [kW] |", span=(0, 4),
         resolution="resolved_in_source",
         note="C56/C40/C35 三船的 DWT、Lpp×B×T、Cb、MCR、EPL、P_ME,EEXI、V_ref、SFC、燃料、C_F；只登记字面值，不做换算"),
    dict(asset_id="A07", asset_class="statement", label="数据来源与外部基准缺失声明（WITHHELD 判据）",
         anchor="> 数据来源声明：公开船舶参数量级", span=(0, 0),
         resolution="resolved_in_source",
         note="报告自陈非 GISIS 回读、外部实测比对判 WITHHELD——本工序只登记该声明，不复核其真实性"),
    dict(asset_id="A08", asset_class="table", label="3.1 三船 EEXI 全链路结果表（参考值/路径A/B/C/required/三态）",
         anchor="| 船 | 参考值（独立复算） | 路径 A 声明功率 |", span=(0, 4),
         resolution="resolved_in_source", note="本报告主结果表；数值仅登记"),
    dict(asset_id="A09", asset_class="table", label="3.2 功率链明细表（路径 B 计算点）",
         anchor="| 船 | V [kn] | Fn | R_T [kN] | P_E [kW] |", span=(0, 4),
         resolution="resolved_in_source", note="含 T(1−t)−R_T 残差列"),
    dict(asset_id="A10", asset_class="table", label="3.3 同源闸门表（判据 b/c）",
         anchor="| 船 | 内核级 \\|ΔR_T\\| [N] |", span=(0, 4),
         resolution="resolved_in_source", note="端点 vs 链路内核级差值；三船「通过=True」"),
    dict(asset_id="A11", asset_class="table", label="3.4 缺陷修复前后对照表（S2 基线）",
         anchor="| 船 | attained 修复前 | 与独立复算偏差 |", span=(0, 4),
         resolution="resolved_in_source", note="1852 倍量纲缺陷的前后对照；比值列恒等"),
    dict(asset_id="A12", asset_class="table", label="3.5 六因子不确定度分解表",
         anchor="| 因子 | 基值 | 指数 ∂lnEEXI/∂lnx |", span=(0, 7),
         resolution="resolved_in_source", note="R_T/eta_D/SFC/C_F/DWT/V_ref 的指数、份额、先验 σ、排序"),
    dict(asset_id="A13", asset_class="table", label="3.5 三船 Σ 份额与 σ_combined 表",
         anchor="| 船 | Σ 等权份额 [%] | σ_combined |", span=(0, 4),
         resolution="resolved_in_source", note="三船共用同一组份额（数值三行相同），仅登记"),
    dict(asset_id="A14", asset_class="table", label="3.6 合规三态判定表（判据 e）",
         anchor="| 船 | attained（链路） | required | 余量 |", span=(0, 4),
         resolution="resolved_in_source", note="C56=UNCERTAIN，C40/C35=COMPLIANT；判据列含灰区规则原文"),
    dict(asset_id="A20", asset_class="limitation_set", label="⑤ 注意点与局限（8 条）",
         anchor="1. 外部基准缺失：无 GISIS/船级社 EEXI 技术文件回读通道", span=(0, 7),
         resolution="resolved_in_source",
         note="含外部基准缺失、参考船量级、η_S/η_G 取值、Holtrop/BEMT 适用域、C_F 表值偏差 0.10%、容量 70% DWT 待办等"),
    dict(asset_id="A21", asset_class="table", label="⑥ 误差判定表（关键量 vs 基准，逐项是否 <3%）",
         anchor="| 关键量 | 基准 | 平台值 | 相对误差 | <3%？ |", span=(0, 10),
         resolution="resolved_in_source",
         note="9 行；含 C40/C35 路径 C 的「否（如实暴露）」行——本工序只登记，不改判"),
    dict(asset_id="A22", asset_class="statement", label="⑥ 结论段（<3% 是否满足的显式回答）",
         anchor="**结论**：公式+量纲层（路径 A）与独立复算一致到机器精度", span=(0, 0),
         resolution="resolved_in_source", note="结论行原文；引用即逐字定位"),
    dict(asset_id="A23", asset_class="table", label="验收判据自检表 (a)–(f)",
         anchor="| 判据 | 阈值 | 实测 | 通过 |", span=(0, 7),
         resolution="resolved_in_source", note="上游自报 6 条判据全 True；本工序不复核其计算"),
    dict(asset_id="A38", asset_class="derivation", label="V 与 V_ref 精确抵消的结构性质推导段",
         anchor="代入 P_ME 后有一个值得写下来的结构性质", span=(0, 6),
         resolution="resolved_in_source",
         note="解析推导叙述（V 精确抵消、阻力误差一比一进 EEXI、V_ref 只经阻力曲线斜率进入）；只登记原文"),
    dict(asset_id="A39", asset_class="statement", label="3.4 比值恒等声明（1851.998 = 1 nm / 0.99983 m）",
         anchor="修复前最大偏差 **99.9460%**", span=(0, 0),
         resolution="resolved_in_source",
         note="量纲缺陷修复的量级解释句；本工序只登记，不复算该恒等式"),
    dict(asset_id="A40", asset_class="paragraph", label="① 引入段：EEXI 只吃手输功率的问题陈述 + 1852 倍量纲缺陷",
         anchor="EEXI（能效现有船舶指数，MEPC.328(76)）", span=(0, 0),
         resolution="resolved_in_source",
         note="背景与动机段落原文；「有能力台账里 GREEN-EEXI 长期停在 WITHHELD（对要求值误差 99.9%）」等表述只登记不改判"),
    dict(asset_id="A41", asset_class="method_section", label="② 方法步骤（7 条编号步骤）",
         anchor="1. **同源闸门（不复制内核）**", span=(0, 9),
         resolution="resolved_in_source",
         note="同源闸门/功率链/量纲修正/三条路径/不确定度分解/合规三态/复现命令七步原文"),
    dict(asset_id="A42", asset_class="conclusion", label="3.1 路径 C 适用域边界结论段",
         anchor="路径 C 是「只给几何与主机功率", span=(0, 0),
         resolution="resolved_in_source",
         note="对 C56/C40/C35 路径 C 偏差的定性说明与几何-only 判 WITHHELD 的理由（Holtrop 回归域边缘）"),
    dict(asset_id="A43", asset_class="conclusion", label="3.5 不确定度要点段（改进优先级）",
         anchor="要点：等权 ±5% 扰动下", span=(0, 0),
         resolution="resolved_in_source",
         note="V_ref 指数≈2.1–2.3 与「R_T 独占约 2/3 方差」的叙述；只登记，不复算"),
    dict(asset_id="A31", asset_class="figure_binary_payload",
         label="图件二进制载荷（payload.figures[].png_base64）",
         anchor="## ④ 结果图", span=(0, 0), resolution="declared_absent",
         note="平台报告记录的 figures 字段只有 name/caption，4 条均无 png_base64（解码长度 0），"
              "故图件像素内容在源资产层不可得"),
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def line_index_of(offs, char: int) -> int:
    lo, hi = 0, len(offs) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offs[mid] <= char:
            lo = mid
        else:
            hi = mid - 1
    return lo


def find_anchor_line(md: str, anchor: str) -> int:
    idx = md.find(anchor)
    if idx < 0:
        raise SystemExit(f"anchor not found: {anchor!r}")
    if md.find(anchor, idx + 1) >= 0:
        raise SystemExit(f"anchor not unique: {anchor!r}")
    return idx


def build_locator(md: str, lines, offs, anchor, span) -> dict:
    if anchor is None:  # whole-document locator
        quote = lines[0]
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1, quote=quote,
                    unique=md.count(quote) == 1)
    a = find_anchor_line(md, anchor)
    a_line = line_index_of(offs, a)
    s, e = a_line + span[0], a_line + span[1]
    if s < 0 or e >= len(lines):
        raise SystemExit(f"span out of range for anchor {anchor!r}: {s}..{e}")
    start_char = offs[s]
    end_char = offs[e] + len(lines[e])
    quote = md[start_char:end_char]
    return dict(method="char_span", start_char=start_char, end_char=end_char,
                start_line=s, end_line=e, quote=quote, unique=md.count(quote) == 1)


def heading_above(lines, start_line: int) -> str:
    head = "(document)"
    for ln in lines[:start_line]:
        if ln.startswith("#"):
            head = ln.strip()
    return head


def worktree_lookup(worktree: pathlib.Path, rel: str) -> dict:
    """Does the referenced path (or a same-basename file) exist in THIS worktree?"""
    direct = (worktree / rel).exists()
    base = pathlib.PurePosixPath(rel).name
    same_name = [str(p.relative_to(worktree)) for p in worktree.rglob(base)
                 if ".git" not in p.parts][:5]
    return dict(direct=direct, same_basename=same_name)


def resolution_check(spec, loc, worktree, payload, md) -> dict:
    aid, cls = spec["asset_id"], spec["asset_class"]
    if aid == "A31":
        figs = payload.get("figures") or []
        n_bytes = sum(1 for f in figs if f.get("png_base64"))
        return dict(check="payload.figures[].png_base64_present", result="absent",
                    platform_figures_count=len(figs), figures_with_png_bytes=n_bytes,
                    detail="报告记录 figures 字段仅含 name/caption；无像素载荷可登记")
    if cls == "figure_ref":
        name = spec["png"]
        found = worktree_lookup(worktree, f"artifacts/eexi_attained_closure/{name}")
        names = [f.get("name") for f in (payload.get("figures") or [])]
        in_platform = name in names
        sha_decl = spec.get("sha_prefix")
        return dict(check="worktree_file_lookup + platform_figures_name_match",
                    result="unresolved" if not found["direct"] else "resolved",
                    worktree_path=f"artifacts/eexi_attained_closure/{name}",
                    worktree_hit=found, in_platform_figures_field=in_platform,
                    declared_sha256_prefix=sha_decl,
                    detail=("图件位于 ship-performance-platform 仓，本工作树内不存在；"
                            + ("平台 figures 字段有同名条目但无 png 载荷。"
                               if in_platform else
                               "平台 figures 字段无同名条目（仅 name/caption 元数据可对账）。")
                            + (f"报告只给截断 sha256 前缀 {sha_decl}（末尾省略号），不足以复算校验。"
                               if sha_decl else "报告未给该图 sha256 声明行。")
                    )
                    )
    if aid in ("A01", "A02"):
        return dict(check="recomputed_sha256_of_source_markdown", result="resolved",
                    sha256=sha256_bytes(md.encode()),
                    detail="整篇 markdown 哈希与本包契约 source_hash 一致（见 integrity）")
    if spec.get("rel_path"):
        found = worktree_lookup(worktree, spec["rel_path"])
        return dict(check="worktree_file_lookup", result="resolved" if found["direct"] else "unresolved",
                    worktree_path=spec["rel_path"], worktree_hit=found,
                    detail=("路径在本工作树内存在" if found["direct"] else
                            "路径不在本工作树（TensorKnowledge）内：属来源仓 ship-performance-platform 的产物，"
                            "本工序无该仓检出，故不可解析" + (
                                "；本工作树内也无同名文件" if not found["same_basename"] else
                                "；本工作树内有同名文件需人工比对：" + ", ".join(found["same_basename"]))))
    return dict(check="char_span_in_source_markdown", result="resolved",
                detail="quote 为 markdown 唯一子串（见 integrity.quote_uniqueness）")


def refetch(run_dir: pathlib.Path) -> None:
    token = os.environ.get("TENSOR_TOKEN")
    if not token:
        raise SystemExit("--refetch requires TENSOR_TOKEN")
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    req = urllib.request.Request(f"{base}/tensor/reports/{REPORT_ID}",
                                 headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / f"report_{REPORT_ID}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    (run_dir / f"report_{REPORT_ID}.md").write_text(payload.get("markdown") or "")
    print("refetched", payload.get("id"), "chars", len(payload.get("markdown") or ""))


def main() -> int:
    if "--refetch" in sys.argv:
        refetch(RUN_DIR)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    payload = json.loads((RUN_DIR / f"report_{REPORT_ID}.json").read_text())
    md = (RUN_DIR / f"report_{REPORT_ID}.md").read_text()

    md_hash = sha256_bytes(md.encode())
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {EXPECTED_HASH}")
        return 2
    if len(md) != EXPECTED_CHARS:
        print(f"FATAL: chars {len(md)} != contract chars {EXPECTED_CHARS}")
        return 2
    if payload.get("title") != EXPECTED_TITLE:
        print(f"FATAL: title mismatch: {payload.get('title')!r}")
        return 2
    if payload.get("scenario_key") != EXPECTED_SCENARIO:
        print(f"FATAL: scenario_key mismatch: {payload.get('scenario_key')!r}")
        return 2
    if str(payload.get("id")) != REPORT_ID:
        print(f"FATAL: payload id {payload.get('id')} != {REPORT_ID}")
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    specs = list(ASSETS)
    for aid, name in FIGURES:
        specs.append(dict(asset_id=aid, asset_class="figure_ref", label=f"结果图 {name}",
                          anchor=f"![{name}]", span=(0, 2), resolution="referenced_unresolved",
                          png=name, note="④ 结果图小节内的图片引用；图件本体不在本工作树"))
    for aid, cls, rel, note, _tag in CODE_POINTERS:
        specs.append(dict(asset_id=aid, asset_class=cls, label=f"审计链指针 {rel}",
                          anchor=f"`{rel}`", span=(0, 0), resolution="referenced_unresolved",
                          rel_path=rel, note=note))

    # figure sha256 prefix declarations live on the line after each image: attach them.
    sha_prefix = {}
    for spec in specs:
        if spec["asset_class"] == "figure_ref":
            i = find_anchor_line(md, spec["anchor"])
            ln = line_index_of(offs, i)
            nxt = lines[ln + 1] if ln + 1 < len(lines) else ""
            if "sha256=" in nxt:
                sha_prefix[spec["asset_id"]] = nxt.split("sha256=`", 1)[1].split("`")[0]
                spec["sha_prefix"] = sha_prefix[spec["asset_id"]]
                spec["note"] = ("④ 结果图小节内的图片引用；图件本体不在本工作树；"
                                f"报告只给截断 sha256 前缀 {spec['sha_prefix']}")

    assets, seen = [], set()
    for spec in specs:
        aid = spec["asset_id"]
        if aid in seen:
            raise SystemExit(f"duplicate asset_id {aid}")
        seen.add(aid)
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"])
        if not loc["unique"]:
            raise SystemExit(f"quote not unique for {aid}")
        if loc["method"] == "char_span" and md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            raise SystemExit(f"char span does not reproduce quote for {aid}")
        section = heading_above(lines, loc["start_line"])
        assets.append(dict(
            asset_id=aid,
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=section,
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=resolution_check(spec, loc, worktree, payload, md),
            note=spec["note"],
        ))

    # Asset ids follow document order (deterministic, ascending): sort by locator
    # position, then renumber. Specs above use provisional ids only for wiring.
    assets.sort(key=lambda a: (a["locator"]["start_line"], a["locator"]["start_char"]))
    for i, a in enumerate(assets, start=1):
        a["asset_id"] = f"A{i:02d}"

    # Coverage gate: every non-empty line must be inside some content asset, except pure
    # heading/caption lines (which carry no payload of their own). Fails loudly if not.
    covered = set()
    for a in assets:
        if a["asset_id"] == "A01":      # whole-document locator covers everything trivially
            continue
        covered.update(range(a["locator"]["start_line"], a["locator"]["end_line"] + 1))
    bare = [(i, lines[i]) for i in range(len(lines)) if i not in covered and lines[i].strip()]

    def kind_of(ln: str) -> str:
        if ln.lstrip().startswith("#"):
            return "heading"
        if ln.strip() == "```":
            return "code_fence"
        return "payload"

    if any(kind_of(ln) == "payload" for _, ln in bare):
        raise SystemExit("uncovered payload lines: "
                         + repr([ln[:60] for _, ln in bare if kind_of(ln) == "payload"]))
    # fence delimiters are recorded by position/kind only (their literal text would put a
    # code-fence sequence inside the result JSON and break naive fence scanners)
    structural_census = [dict(line=i, kind=kind_of(ln),
                              text="(code fence delimiter)" if kind_of(ln) == "code_fence"
                              else ln.strip()) for i, ln in bare]

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = dict(
        schema="asset_manifest.v1.1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI,
            field=SOURCE_FIELD,
            hash_alg="sha256",
            hash=md_hash,
            chars=len(md),
            bytes_utf8=len(md.encode()),
            lines=len(lines),
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_status=payload.get("status"),
            platform_figures=[dict(name=f.get("name"), caption=f.get("caption"),
                                   has_png_bytes=bool(f.get("png_base64")))
                              for f in (payload.get("figures") or [])],
            platform_tags=payload.get("tags", []),
            retrieved_via="GET %s/tensor/reports/%s" % (
                os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
                REPORT_ID),
            local_copy=str(RUN_DIR / f"report_{REPORT_ID}.md"),
            durable_copy=str(DOC_DIR / f"source_{REPORT_ID}.md"),
        ),
        counts=dict(assets=len(assets), by_class=by_class, by_resolution=by_res,
                    resolved_in_source=by_res.get("resolved_in_source", 0),
                    referenced_unresolved=by_res.get("referenced_unresolved", 0),
                    declared_absent=by_res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("本工序 objective.classify_report_type=false 且契约 notes 允许 claims 为空数组："
                     "只做资产登记与定位，不做 claim 抽取（claim 抽取/核验属下游工序，"
                     "且报告主数字的源 artifact eexi_attained_closure.json 不在本工作树内，"
                     "本工序无法交叉复算）。未把任何结论标为 verified。"),
        note_title_mismatch=("平台 title（含「（P73W2-N02）」「99.9%→<3% 精度传递」）与 markdown H1"
                             "（不含这两段）措辞不同；二者均属源字段，登记时并存，不做统一。"),
        note_figure_field_gap=("markdown ④ 小节引用 5 张 png；平台 figures 字段只声明 4 条"
                               "（缺 fig_eexi_power_speed.png），且 4 条均无 png_base64 载荷。"
                               "属登记层面的元数据缺口，本工序只记录不修复。"),
        structural_lines_not_registered=dict(
            count=len(structural_census), lines=structural_census,
            note=("只看结构、不看内容的行不单独立资产：章节标题/图题（heading，"
                  "图题内容由对应 figure_ref 的 note 与平台 figures.caption 对账）与代码块围栏"
                  "（code_fence，纯定界符无载荷）。覆盖闸门：其余全部非空行（kind=payload）"
                  "必须落在某条资产 locator 内，否则生成器拒不出包。"),
        ),
        id_convention="asset_id 按 locator 文档顺序升序编号（A01=文档首部），便于人工顺读与 diff 稳定",
        integrity=dict(
            quote_uniqueness="每条 locator.quote 均为源 markdown 的唯一子串（scripts/kf_verify_8240.py 复核 count==1）",
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            contract_chars_matched=True,
            report_id_isolated="仅读 report_id=8240，未访问其他 report_id",
            asset_coverage=(f"{len(assets)} 条资产覆盖 {len(lines)} 行中的 "
                            f"{len(lines) - len(bare)} 行；剩余 {len(bare)} 行全为标题/图题/围栏"),
        ),
    )

    # durable source snapshot: the push gate drops runs/**, so the committed copy of the
    # evidence base (markdown + payload) lives in docs/ and is byte-identical to runs/.
    doc_md = DOC_DIR / f"source_{REPORT_ID}.md"
    doc_payload = DOC_DIR / f"source_{REPORT_ID}.json"
    doc_md.write_bytes(md.encode())
    doc_payload.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    if sha256_bytes(doc_md.read_bytes()) != md_hash:
        print("FATAL: docs/ markdown snapshot differs from source")
        return 3

    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art = ART_DIR / "asset_manifest.json"
    art.write_text(blob)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    art_hash = sha256_bytes(art.read_bytes())
    if sha256_bytes(mirror.read_bytes()) != art_hash:
        print("FATAL: durable mirror differs from artifact")
        return 3

    envelope = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI,
            source_field=SOURCE_FIELD,
            source_hash="sha256:" + md_hash,
            source_chars=len(md),
            source_bytes_utf8=len(md.encode()),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version="1.0",
            lane="C",
            work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(RUN_DIR / f"report_{REPORT_ID}.md"),
            durable_copy=str(DOC_DIR / f"source_{REPORT_ID}.md"),
            artifact_sha256=art_hash,
            generator="scripts/kf_register_8240.py",
            verifier="scripts/kf_verify_8240.py",
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": {k: v for k, v in manifest.items()}},
        claims=[],
    )
    env_blob = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    (RUN_DIR / f"kf_result.{PACKAGE_ID}.json").write_text(env_blob)
    (DOC_DIR / f"kf_result.{PACKAGE_ID}.json").write_text(env_blob)

    print("markdown sha256:", md_hash, "MATCH")
    print("chars:", len(md), "bytes:", len(md.encode()), "lines:", len(lines))
    print("assets:", len(assets), "by_class:", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("envelope:", RUN_DIR / f"kf_result.{PACKAGE_ID}.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())