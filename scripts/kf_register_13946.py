"""Register the source assets of report 13946 (work package wp-13946-01, task_type 01-asset-registration).

Design rules enforced here (mirrors docs/kf/wp-*> precedent, e.g. scripts/kf_register_448.py):
  * No hand transcription. Every ``quote`` in the manifest is sliced out of the report markdown at
    run time from a programmatic line anchor (line-index span); the script re-checks that each
    quote is a *unique* substring of the markdown before writing anything. Character spans and
    line numbers are computed from the same slice, so locator and quote cannot drift apart.
  * Registration only. No claim extraction (contract: objective.register_assets=true,
    objective.classify_report_type=false, "claims 允许为空数组"). Items that cannot be resolved
    from the worktree/platform are recorded as ``referenced_unresolved`` / ``declared_absent``
    with a reason -- never silently dropped and never given an invented address.
  * Nothing is marked verified. ``resolution`` describes locator resolvability only.
  * Only report_id=13946 is read.

Input: runs/wp-13946-01/report_13946.md  (produced by scripts/kf_fetch_13946.py, hash-gated)
Outputs:
  artifacts/wp-13946-01/asset_manifest.json        (primary)
  runs/wp-13946-01/kf_result.wp-13946-01.json      (result envelope, kf_result.v1 shape)
  docs/wp-13946-01/*.json                          (durable mirror: .gitignore drops artifacts/)

Usage: python3 scripts/kf_register_13946.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

REPORT_ID = "13946"
PACKAGE_ID = "wp-13946-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/13946"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072"
EXPECTED_CHARS = 5534

RUN_DIR = pathlib.Path("runs") / PACKAGE_ID
ART_DIR = pathlib.Path("artifacts") / PACKAGE_ID
DOC_DIR = pathlib.Path("docs") / "wp-13946-01"

# asset_id, asset_class, label, (start_line, end_line) inclusive, resolution, note
# Line indices are 0-based into the report markdown; the emitted quote is the verbatim slice.
ASSETS = [
    ("A01", "document", "报告正文（markdown 全文，源资产本体）", (0, -1), "resolved_in_source",
     "整篇 markdown 即源资产；sha256/字符数见 source 字段，可由 scripts/kf_fetch_13946.py 复算"),
    ("A02", "heading", "报告标题（与 API title 字段同源）", (0, 0), "resolved_in_source",
     "一级标题单行；内容与平台 title 字段一致（见 ④ 证据定位表）"),
    ("A03", "provenance_header", "锚点/任务/方法三行溯源声明", (2, 5), "resolved_in_source",
     "声明 GAP-DEM-FRICTION 锚点、m14840 任务号、被审对象仓库与文件、方法=adversarial-review"),
    ("A04", "table", "结论表 F1/F2/F3（表头+分隔+3 条结论）", (9, 13), "resolved_in_source",
     "3 条结论级登记：F1/F2 缺陷已修、F3 结论不成立(honest 未修)；仅登记不改写、不判 verified"),
    ("A05", "parameter_set", "装置与案例参数表（颗粒/盒体/接触/伺服/协议/应力级，6 行）", (17, 24),
     "resolved_in_source",
     "参数原文逐字登记（r/ρ/n/盒体尺寸/kn/kt/e/dt/M_plate/τ_damp/γ/σ_n/seed），不做换算与补全"),
    ("A06", "procedure", "方法步骤清单（6 步：路径重建→解析预测→bedref 修正→速率记账→稳态门→A/B 矩阵）",
     (28, 33), "resolved_in_source",
     "6 条方法步骤原文；步骤内引用的脚本路径分别登记为 A17-A19"),
    ("A07", "table", "伺服模式相对误差对照表（drag vs bedref × 三级 σ_n）", (39, 42),
     "resolved_in_source",
     "表头+两行数据；数值仅登记，误差判定见 A13"),
    ("A08", "figure_reference", "图 1 内联引用（servo audit png 相对路径）", (47, 47),
     "referenced_unresolved",
     "markdown 图片链接指向 ../figures/shear_cell_m14840_servo.png；本工作树无 figures/ 目录，"
     "二进制不可解析；平台 reports.figures 元数据声明同名图（见 source.platform_figures），"
     "但本工序只登记链接，不校验图件内容"),
    ("A09", "figure_caption", "图 1 说明（A 面板载荷误差 / B 面板 τ 四等分均值）", (49, 49),
     "resolved_in_source",
     "图注原文；与平台 figures[0].caption 语义一致"),
    ("A10", "table", "表 1：应力保持逐级明细（drag/bedref σ_n 与 μ）", (76, 80),
     "resolved_in_source",
     "表头+3 行数据；含 drag/bedref 两侧 μ 值（本工序未对 μ 做任何结论）"),
    ("A11", "table", "表 2：拖曳伺服载荷偏置机理检验（v_z / ΔN 实测 / ΔN 解析预测）", (84, 90),
     "resolved_in_source",
     "含 F1 解析式原文行（稳态解 dN = M_p v_z (1-e^{-dt/tau})/dt）+ 表头 + 3 行数据"),
    ("A12", "table", "表 3：剪切率/惯性数记账（名义 vs 实测床高、τ 四等分均值、窗口漂移）", (94, 99),
     "resolved_in_source",
     "含 F2/F3 的关键数字（床高 0.0296-0.0299 m、实际 γ̇ 1.67-1.69 1/s、I_actual、drift）；仅登记"),
    ("A13", "error_judgement", "§6 误差判定表（含『不能声称』honest-FAIL 行）", (61, 67),
     "resolved_in_source",
     "5 行判定：逐项显式回答是否 <3%；末行 μ vs 实验=不可判定/不能声称"),
    ("A14", "repro_command", "复现命令行（pytest 8 passed / run_matrix / make_figures）", (69, 70),
     "resolved_in_source",
     "两条原文命令；标签 <tag>/<mode>/<strain> 为占位符，报告未给出具体取值——登记时不实例化"),
    ("A15", "limitation_set", "注意点与局限（5 条：判据/协议口径/旧记账/量级/适用范围）", (53, 57),
     "resolved_in_source",
     "5 条局限原文，preserve_uncertainty：原文措辞原样保留，不弱化也不强化"),
    ("A16", "code_artifact", "被审代码 src/tensordem/shear_cell.py（m14721 合并版）", (3, 3),
     "referenced_unresolved",
     "TensorDEM 仓内路径，本工作树（TensorKnowledge）无该文件，无 commit SHA/URL，故不可解析"),
    ("A17", "code_artifact", "诊断脚本 scripts/m14840/probe_servo_offset.py", (11, 11),
     "referenced_unresolved",
     "F1 证据来源脚本；跨仓相对路径，无 commit/URL，本工作树不可解析"),
    ("A18", "code_artifact", "证据矩阵脚本 scripts/m14840/run_matrix.py", (33, 33),
     "referenced_unresolved",
     "A/B 矩阵生成器；跨仓相对路径，不可解析"),
    ("A19", "code_artifact", "图表生成脚本 scripts/m14840/make_figures.py", (69, 70),
     "referenced_unresolved",
     "声明图表程序化注入（零手抄）；与 A18 同行引用，跨仓不可解析"),
    ("A20", "derived_document", "表 1/2/3 的脚本文档 docs/SHEAR_CELL_SERVO_AUDIT_M14840_tables.md",
     (37, 37), "referenced_unresolved",
     "报告称『表 1/2/3 见』该文件；跨仓路径，本工作树不存在，不可解析"),
    ("A21", "result_dataset", "证据矩阵结果集 artifacts/shear_cell_m14840/*.json", (33, 33),
     "referenced_unresolved",
     "通配路径，未列出具体文件名/哈希；跨仓，不可解析（不臆造文件名）"),
    ("A22", "test_artifact", "审计测试 tests/test_shear_cell_servo_audit_m14840.py（报告称 8 passed）",
     (69, 69), "referenced_unresolved",
     "跨仓测试文件；报告只给『8 passed（5 s）』这一观察，本工序未复跑（无该仓检出），不作独立性判定"),
    ("A23", "declared_absent", "μ vs 实验所需的实验/文献数据集", (67, 67), "declared_absent",
     "报告显式声明『无实验/文献数据集（仓内无直剪实验数据；F3 未稳态）』——按声明登记为缺失，不补造"),
]

# Optional tighter locators: for assets that the report mentions in a single dense line, the emitted
# quote is narrowed to the exact referenced token (still a verbatim slice, still required unique).
# Without this, A18/A19/A21 would share one line and the locators would not be individually checkable.
SUB_ANCHORS = {
    "A16": "`src/tensordem/shear_cell.py`",
    "A17": "scripts/m14840/probe_servo_offset.py",
    "A18": "`scripts/m14840/run_matrix.py`",
    "A19": "图/表 `scripts/m14840/make_figures.py`",
    "A20": "docs/SHEAR_CELL_SERVO_AUDIT_M14840_tables.md",
    "A21": "artifacts/shear_cell_m14840/*.json",
    "A22": "tests/test_shear_cell_servo_audit_m14840.py",
    "A23": "**无实验/文献数据集**（仓内无直剪实验数据；F3 未稳态）",
}


def read_source() -> tuple[str, dict]:
    md_path = RUN_DIR / "report_13946.md"
    if not md_path.exists():
        sys.exit("missing %s -- run scripts/kf_fetch_13946.py first" % md_path)
    md = md_path.read_text()
    meta = json.loads((RUN_DIR / "report_13946.json").read_text())
    return md, meta


def line_offsets(md: str) -> tuple[list[str], list[int]]:
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build(md: str, meta: dict) -> dict:
    digest = hashlib.sha256(md.encode()).hexdigest()
    assert digest == EXPECTED_HASH, "source hash drift: %s != %s" % (digest, EXPECTED_HASH)
    assert len(md) == EXPECTED_CHARS, "source char count drift: %d != %d" % (len(md), EXPECTED_CHARS)

    lines, offs = line_offsets(md)
    n = len(lines)

    def span(start: int, end: int):
        s = 0 if start == 0 and end == -1 else start
        e = (n - 1) if end == -1 else end
        return s, e

    assets, seen_ids, quotes = [], set(), []
    for aid, cls, label, (ls, le), resolution, note in ASSETS:
        if aid in seen_ids:
            sys.exit("duplicate asset_id %s" % aid)
        seen_ids.add(aid)
        s, e = span(ls, le)
        if aid in SUB_ANCHORS:
            tok = SUB_ANCHORS[aid]
            block = "\n".join(lines[s:e + 1])
            assert tok in block, "%s: sub anchor not inside lines %d-%d" % (aid, s, e)
            start_char = offs[s] + block.index(tok)
            end_char = start_char + len(tok)
            quote = tok
            s = md.count("\n", 0, start_char)
            e = md.count("\n", 0, end_char - 1)
        else:
            quote = "\n".join(lines[s:e + 1])
            start_char = offs[s]
            end_char = offs[e] + len(lines[e])
        assert quote, "%s: empty quote" % aid
        hit = md.count(quote)
        if hit != 1:
            sys.exit("%s: quote occurs %d times (must be unique): %r" % (aid, hit, quote[:80]))
        assert md[start_char:end_char] == quote, "%s: char span mismatch" % aid
        quotes.append(quote)
        assets.append({
            "asset_id": aid,
            "asset_class": cls,
            "label": label,
            "in_report_section": _section_of(lines, s),
            "locator": {
                "method": "document" if (s, e) == (0, n - 1) else "char_span",
                "start_char": start_char,
                "end_char": end_char,
                "start_line": s,
                "end_line": e,
                "quote": quote,
                "unique": True,
            },
            "resolution": resolution,
            "resolution_check": {
                "check": _check_of(resolution),
                "result": {"resolved_in_source": "resolved",
                           "referenced_unresolved": "unresolved",
                           "declared_absent": "absent"}[resolution],
            },
            "note": note,
        })

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(md.encode()),
            "title": meta.get("title", ""),
            "scenario_key": meta.get("scenario_key", ""),
            "platform_figures": meta.get("figures") or [],
            "platform_tags": meta.get("tags") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "claims_note": ("claims 有意为空：本工序 objective.register_assets=true / "
                        "classify_report_type=false，只登记资产不做抽取（契约允许空数组，"
                        "禁为填指标造知识）；报告内的 F1-F3 结论原样留在 A04 等资产里，未升级为 claim。"),
        "integrity": {
            "quote_uniqueness": "each quote asserted md.count(quote)==1 at build time",
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "char_count_matches_contract": len(md) == EXPECTED_CHARS,
            "char_span_recheck": "md[start_char:end_char] == quote for every asset (asserted)",
            "verified_by_platform_gate": False,
        },
    }
    return manifest


def _section_of(lines: list[str], idx: int) -> str:
    """Name the enclosing section; front-matter (only the document title above) is labelled."""
    for j in range(idx, -1, -1):
        if lines[j].startswith("## "):
            return lines[j][:60]
        if lines[j].startswith("### "):
            return lines[j][:60]
    return "front-matter (before section 1)"


def _check_of(resolution: str) -> str:
    return {
        "resolved_in_source": "verbatim slice of report markdown at char_span, unique in document",
        "referenced_unresolved": "referenced by relative path/env in report; not present in this "
                                 "worktree and no commit/URL/DOI given in the report",
        "declared_absent": "report explicitly states the item is absent/unavailable",
    }[resolution]


def main() -> int:
    md, meta = read_source()
    manifest = build(md, meta)

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_field": SOURCE_FIELD,
            "producer": "scripts/kf_register_13946.py (agent/m15769)",
            "emitted_at": "deterministic; see report created_at / git commit",
            "notes": ("asset registration only; no extraction, no verification claim. "
                      "source_hash = sha256(markdown bytes of report 13946)."),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    for d in (ART_DIR, RUN_DIR, DOC_DIR):
        d.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    etxt = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    (ART_DIR / "asset_manifest.json").write_text(text)
    (DOC_DIR / "asset_manifest.json").write_text(text)
    (RUN_DIR / "kf_result.wp-13946-01.json").write_text(etxt)
    (DOC_DIR / "kf_result.json").write_text(etxt)
    (RUN_DIR / "kf_result_block.wp-13946-01.json").write_text(etxt)

    print("assets:", manifest["counts"]["assets"])
    print("by_resolution:", manifest["counts"]["by_resolution"])
    print("source sha256:", manifest["source"]["hash"])
    print("wrote:", ART_DIR / "asset_manifest.json", DOC_DIR / "asset_manifest.json",
          RUN_DIR / "kf_result.wp-13946-01.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())