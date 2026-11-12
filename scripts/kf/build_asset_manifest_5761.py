#!/usr/bin/env python3
"""Work package wp-5761-01 — asset registration for tensor report 5761 (task_type=01-asset-registration).

Scope guard: touches ONLY report_id=5761. No classification, no claim extraction, no verification marks
(PRODUCTION-LINE-v1 §2.1). Every locator quote is sliced out of the fetched markdown bytes by the
anchor search below — nothing is retyped, so quotes are literal substrings of the source.

Products (all under docs/ because tp_pusher._EXCLUDE drops artifacts/ and runs/):
  docs/kf/wp-5761-01/report_5761.markdown              verbatim source copy (byte-identical)
  docs/kf/wp-5761-01/asset_manifest.json               main product (schema asset_manifest.v1.wp-5761-01)
  docs/kf/wp-5761-01/schema/asset_manifest.v1.wp-5761-01.schema.json
  docs/kf/wp-5761-01/schema_binding.json               parent schema sha256 + mechanical substitutions
  docs/kf/wp-5761-01/kf_result.json                    envelope (package_id/task_type/report_id/provenance/outputs)
  docs/kf/wp-5761-01/fig_asset_inventory.png           figure 1 (counts by class/resolution)
  docs/kf/wp-5761-01/fig_locator_map.png               figure 2 (locator spans over source position)

Operations, keyed by anchor+mode; mode = line | block | raw | document.
  line  : whole line containing the anchor
  block : whole paragraph (lines from the anchor line until a blank line or EOF)
  raw   : exactly the anchor text (used where a sub-line span matters)
  item  : one list item (from the anchor line up to the next item marker / blank line / EOF)
  document: whole markdown (locator.method="document", quote = H1 line)

Usage: python3 scripts/kf/build_asset_manifest_5761.py
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

PKG = "wp-5761-01"
REPORT_ID = "5761"
SOURCE_URI = "tensor://reports/5761"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "06f7e6a9d2164c64a916d4f11cc0e117af97766de133438d10fc884a35c2c4d7"
EXPECTED_CHARS = 4141

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / PKG
PARENT_SCHEMA = REPO / "schemas" / "asset_manifest.v1.schema.json"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]


# ------------------------------------------------------------------ platform I/O
def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    body = json.dumps({"username": USER, "password": PASS}).encode()
    for path in ("/tensor/auth/login", "/auth/login"):
        try:
            d = _req(BASE + path, data=body)
        except Exception:  # noqa: BLE001 - try next shape
            continue
        tok = d.get("access_token") or d.get("token")
        if tok:
            return tok
    form = urllib.parse.urlencode({"username": USER, "password": PASS}).encode()
    d = _req(BASE + "/auth/login", data=form, ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token")
    return tok


def fetch(token):
    d = _req("%s/tensor/reports/%s" % (BASE, REPORT_ID), token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown" % REPORT_ID)
    return d, md


# ------------------------------------------------------------------ asset table
# (asset_id, asset_class, label, section, anchor, mode, resolution, note)
SPEC = [
    ("A01", "document", "报告 markdown 全文（源资产本体）", "全文", None, "document",
     "resolved_in_source", "整份 markdown 即源资产；locator.method=document 表全文级，quote 取 H1 行作可核验锚点"),
    ("A02", "statement", "结论段：PASS + 64 项测试 / 51 负例 / 90.21% 分支覆盖 / 回归锁 MATCH", "结论",
     "**结论**：PASS。", "block", "resolved_in_source", "只登记位置与原文，不抽取 claim；数字以本段逐字为准"),
    ("A03", "method_scope_declaration", "作用域声明：航线优化层 modules.green_navigation_ice.route 的求解链", "① 案例介绍",
     "对象是船舶绿色航行-冰区域求解链上的", "block", "resolved_in_source",
     "给出 A2 冰情场→阻力推进→POLARIS/B2→GO/CAUTION/NO-GO→A* 的链路声明"),
    ("A04", "cost_function_definition", "三目标加权代价函数 J", "① 案例介绍",
     "$$J = w_E", "line", "resolved_in_source", "公式为原文 LaTeX，未改写"),
    ("A05", "case_declaration", "基准冰场几何（57×31 格，9.61×10.07 nm）+ 起终点 + 船型 arctic_bulker_45",
     "① 案例介绍", "NO-GO/LAND 是硬约束", "block", "resolved_in_source",
     "几何/起终点/船型同段给出；Cb 几何自校验结论在原文中为 PASS"),
    ("A06", "scope_statement", "节点作用域=测试面（只补测试不改算法）", "① 案例介绍",
     "本节点的作用域是**测试面**", "line", "resolved_in_source", "该句是「零数值改动」主张的原文边界"),
    ("A07", "method_step", "步骤1 纳入既有实现：astar/optimize/risk/field/speed/api 六模块", "② 怎么做的",
     "**纳入既有实现**", "item", "resolved_in_source", "六模块名逐一出现在 quote 内"),
    ("A08", "source_code_reference", "第二刀测试文件 route/tests/test_route_second_cut.py（64 项）", "② 怎么做的",
     "`route/tests/test_route_second_cut.py`", "line", "referenced_unresolved",
     "报告给出路径但该文件不在本交付工作树内，也无内联内容，无法核验哈希"),
    ("A09", "boundary_case_set", "边界工况集（全冰封/单通道走廊/无缺口墙/起点 NO-GO/扩展上限 120）", "② 怎么做的",
     "边界工况用**确定性构造小冰场**", "item", "resolved_in_source", "明确「无随机项」=确定性构造"),
    ("A10", "negative_case_set", "负例集（冰况谱越界/负风险/退化权重/C3-B2 契约/REST 非法请求）", "② 怎么做的",
     "* 负例：冰况谱越界", "item", "resolved_in_source", "负例口径=拒收（非法输入必须失败）"),
    ("A11", "source_code_reference", "回归锁生成脚本 make_route_lock.py", "② 怎么做的",
     "`make_route_lock.py`", "raw", "referenced_unresolved", "脚本不在本工作树，仅路径可定位"),
    ("A12", "data_artifact_reference", "回归锁文件 artifacts/ice_route_second_cut/route_lock.json", "② 怎么做的",
     "`artifacts/ice_route_second_cut/route_lock.json`", "raw", "referenced_unresolved",
     "锁文件路径被引用但未随报告提供；哈希只能核验其存在性主张，不能核验内容"),
    ("A13", "method_step", "步骤3 输入闸门（field/risk/optimize/REST，唯一代码改动）", "② 怎么做的",
     "3. **输入闸门", "item", "resolved_in_source", "原文声明闸门为「拒收」而非「裁剪」"),
    ("A14", "toolchain_declaration", "步骤4 工具链（pytest junitxml / coverage --branch / matplotlib）", "② 怎么做的",
     "4. **工具链**", "item", "resolved_in_source", "工具链声明；具体版本号原文未给（不补）"),
    ("A15", "source_code_reference", "第二刀运行脚本 run_second_cut.py", "② 怎么做的",
     "`run_second_cut.py`", "raw", "referenced_unresolved", "脚本不在本工作树"),
    ("A16", "data_artifact_reference", "判据汇总工件 summary.json", "② 怎么做的",
     "`summary.json`", "raw", "referenced_unresolved", "工件被引用但未提供内容；报告称数字由其产出"),
    ("A17", "table", "判据表（5 项判据 / 目标 / 实测 / 结论）", "③ 计算结果",
     "| 判据 | 目标 | 实测 | 结论 |", "block", "resolved_in_source", "5 行判据全在 quote 内，未抄写任何数字到别处"),
    ("A18", "table", "逐模块分支覆盖表（6 模块 + 合计）", "③ 计算结果",
     "| 模块 | 语句 | 分支 | 分支覆盖 | 语句覆盖 |", "block", "resolved_in_source",
     "合计行 847/194/90.21%/96.93% 在 quote 内"),
    ("A19", "table", "边界工况实测表（4 工况）", "③ 计算结果",
     "| 工况 | 结果 | 关键数字 |", "block", "resolved_in_source", "含 FAILED 如实计数"),
    ("A20", "table", "回归锁航线表（4 条航线长度/油耗/航时/sha256 前缀）", "③ 计算结果",
     "| 航线 | 长度 nm | 油耗 t | 航时 h |", "block", "resolved_in_source",
     "sha256 仅给前 16 位（原文如此），登记为前缀截断，不作全量哈希主张"),
    ("A21", "figure_declaration", "图1 边界工况（全冰封判决 / 单通道走廊穿越）", "④ 结果图",
     "图1 边界工况", "line", "referenced_unresolved",
     "④ 仅给图题文字；平台 figures[] 同索引条目也只有 name+caption，无 png_base64 载荷，故无字节可哈希"),
    ("A22", "figure_declaration", "图2 逐模块分支覆盖 vs 80% 判据线", "④ 结果图",
     "图2 route/ 求解核心逐模块分支覆盖", "line", "referenced_unresolved",
     "同上：图题存在、二进制载荷缺失"),
    ("A23", "figure_declaration", "图3 基准冰场 4 条已知航线（回归锁对象）", "④ 结果图",
     "图3 基准冰场 4 条已知航线", "line", "referenced_unresolved", "同上：图题存在、二进制载荷缺失"),
    ("A24", "limitation", "注意点1：零和权重使最小代价退化为任意可行路径", "⑤ 注意点",
     "不是无害输入", "item", "resolved_in_source", "含 0·inf=nan 的机制解释"),
    ("A25", "limitation", "注意点2：NaN 绕过范围检查", "⑤ 注意点",
     "NaN 能绕过范围检查", "item", "resolved_in_source", "闸门改用 isfinite + 上下界两段判据"),
    ("A26", "limitation", "注意点3：闸门是拒收不是裁剪（边界值必须放行）", "⑤ 注意点",
     "闸门是拒收不是裁剪", "item", "resolved_in_source", "防过度拒收的专门测试在原文被提及"),
    ("A27", "limitation", "注意点4：局限（理想化冰场/玩具网格/覆盖口径不含脚本层）", "⑤ 注意点",
     "**局限**：基准冰场是理想化构造", "item", "resolved_in_source",
     "适用范围声明：不构成真实冰区绝对正确性主张"),
    ("A28", "external_dataset", "A2 观测冰情产品（被声明未使用）", "⑤ 注意点",
     "非 A2 观测产品", "raw", "declared_absent",
     "报告显式声明基准冰场为理想化构造、非 A2 观测产品；该外部数据集在源内被声明为不存在"
     "（子片段，落在 A27 段内）"),
    ("A29", "limitation", "注意点5：D1 边界（不引入新算法，闸门可机械重放）", "⑤ 注意点",
     "5. **D1 边界**", "item", "resolved_in_source", "给出合入主干后的可重放条件"),
    ("A30", "table", "误差判定表（4 项，逐项问「是否 <3%」）", "⑥ 误差判定",
     "| 关键量 | 基准 | 误差 | 是否 <3% |", "block", "resolved_in_source",
     "含一项答案为「否」的显式声明"),
    ("A31", "error_judgment_statement", "对「走廊长度 8.620% 误差」的显式说明（网格离散度量而非模型误差）",
     "⑥ 误差判定", "对最后一项的显式说明", "block", "resolved_in_source",
     "原文把判据改为「≥下界且 ≤下界+15%」，未宣称满足 3%"),
]

RES_CHECK = {
    "resolved_in_source": {"check": "char_span_in_source_markdown", "result": "resolved"},
    "referenced_unresolved": {"check": "worktree_file_lookup", "result": "unresolved"},
    "declared_absent": {"check": "source_declaration_search", "result": "absent"},
}


# ------------------------------------------------------------------ locators
def locate(md, anchor, mode):
    """Slice a verbatim span out of md. Returns locator dict; raises if the anchor is absent."""
    if mode == "document":
        first_nl = md.find("\n")
        quote = md[: first_nl if first_nl > 0 else len(md)]
        return {
            "method": "document",
            "start_char": 0,
            "end_char": len(md),
            "start_line": 1,
            "end_line": md.count("\n") + (0 if md.endswith("\n") else 1),
            "quote": quote,
            "unique": md.count(quote) == 1,
        }
    hits = md.count(anchor)
    if hits < 1:
        raise SystemExit("ANCHOR NOT FOUND: %r" % anchor)
    idx = md.find(anchor)
    if mode == "raw":
        start, end = idx, idx + len(anchor)
    else:
        start = md.rfind("\n", 0, idx) + 1
        if mode == "line":
            end = md.find("\n", idx)
            end = len(md) if end < 0 else end
        elif mode == "item":
            end = len(md)
            pos = md.find("\n", idx)
            while pos >= 0:
                nxt = md.find("\n", pos + 1)
                line = md[pos + 1: nxt if nxt >= 0 else len(md)]
                if line.strip() == "" or re.match(r"^\s*(\d+\.\s|\*\s)", line):
                    end = pos
                    break
                pos = nxt
        else:  # block: extend to a blank line / EOF
            end = len(md)
            pos = md.find("\n", idx)
            while pos >= 0:
                nxt = md.find("\n", pos + 1)
                line = md[pos + 1: nxt if nxt >= 0 else len(md)]
                if line.strip() == "":
                    end = pos
                    break
                pos = nxt
    quote = md[start:end]
    if md.count(quote) != 1:
        raise SystemExit("QUOTE NOT UNIQUE for %r (count=%d)" % (anchor, md.count(quote)))
    if md[start:end] != quote:
        raise SystemExit("SPAN MISMATCH for %r" % anchor)
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": md.count("\n", 0, start) + 1,
        "end_line": md.count("\n", 0, end) + 1,
        "quote": quote,
        "unique": True,
    }


# ------------------------------------------------------------------ schema
def specialize_schema():
    """Mechanically re-pin the delivered asset_manifest.v1 schema to this package (no hand editing)."""
    parent = PARENT_SCHEMA.read_text(encoding="utf-8")
    subs = [
        ("wp-448-01", PKG),
        ("448", REPORT_ID),
        ("tensor://reports/448", SOURCE_URI),
    ]
    text = parent
    applied = []
    for old, new in subs:
        old_s, new_s = json.dumps(old, ensure_ascii=False), json.dumps(new, ensure_ascii=False)
        n = text.count(old_s)
        if n < 1:
            raise SystemExit("schema substitution target missing: %s" % old_s)
        text = text.replace(old_s, new_s)
        applied.append({"from": old, "to": new, "occurrences": n})
    sch = json.loads(text)
    sch["$id"] = "https://tensorplatform.local/schemas/asset_manifest.v1.wp-5761-01.schema.json"
    sch["title"] = "asset_manifest.v1 (pinned to wp-5761-01 / report 5761)"
    sch["description"] = (
        "Mechanical specialization of schemas/asset_manifest.v1.schema.json (sha256 recorded in "
        "schema_binding.json): only the four report/package pins were re-bound, every structural "
        "constraint (required keys, asset_id pattern, resolution enum, locator fields) is inherited "
        "unchanged. Written by scripts/kf/build_asset_manifest_5761.py; if the platform-side canonical "
        "schema differs, the platform gate wins and this artifact must be revised."
    )
    out = OUT / "schema" / ("asset_manifest.v1.%s.schema.json" % PKG)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    binding = {
        "package_id": PKG,
        "parent_schema": str(PARENT_SCHEMA.relative_to(REPO)),
        "parent_schema_sha256": hashlib.sha256(PARENT_SCHEMA.read_bytes()).hexdigest(),
        "specialized_schema": str(out.relative_to(REPO)),
        "specialized_schema_sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "substitutions": applied,
        "note": "Only report/package identity pins were substituted; structure inherited verbatim. "
                "The canonical schemas/kf_result.v1.schema.json named by the contract is absent from "
                "this worktree, so result-envelope shape follows the accepted wp-448-01 / wp-542-01 precedent.",
    }
    (OUT / "schema_binding.json").write_text(
        json.dumps(binding, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out, binding


# ------------------------------------------------------------------ figures
def figures(manifest):
    import base64
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    assets = manifest["assets"]
    classes, by_res = [], {}
    for a in assets:
        if a["asset_class"] not in classes:
            classes.append(a["asset_class"])
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    figs = []

    # figure 1: inventory by class, split by resolution
    fig, ax = plt.subplots(figsize=(9, 4.6))
    counts = {c: [0, 0, 0] for c in classes}
    order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    for a in assets:
        counts[a["asset_class"]][order.index(a["resolution"])] += 1
    bottom = [0] * len(classes)
    colors = {"resolved_in_source": "#2b7a3d", "referenced_unresolved": "#c47f00",
              "declared_absent": "#8c2f39"}
    for i, res in enumerate(order):
        vals = [counts[c][i] for c in classes]
        ax.bar(range(len(classes)), vals, bottom=bottom, label="%s (%d)" % (res, by_res.get(res, 0)),
               color=colors[res])
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_xticks(range(len(classes)))
    ax.set_xticklabels(classes, rotation=60, ha="right", fontsize=8)
    ax.set_ylabel("assets")
    ax.set_title("wp-5761-01 asset inventory: %d assets in %d classes (report 5761)" % (len(assets), len(classes)))
    ax.legend(fontsize=8)
    fig.tight_layout()
    p1 = OUT / "fig_asset_inventory.png"
    fig.savefig(p1, dpi=130)
    plt.close(fig)
    figs.append({"name": p1.name,
                 "caption": "wp-5761-01 资产清单：按 asset_class 统计、按 resolution 分层（resolved_in_source / "
                            "referenced_unresolved / declared_absent），计数直接由 asset_manifest.json 渲染。"})

    # figure 2: locator map over source position
    fig, ax = plt.subplots(figsize=(9, 5))
    mdlen = manifest["source"]["chars"]
    for k, a in enumerate(assets):
        loc = a["locator"]
        ax.barh(k, max(loc["end_char"] - loc["start_char"], 8), left=loc["start_char"],
                height=0.7, color=colors[a["resolution"]])
    ax.set_yticks(range(len(assets)))
    ax.set_yticklabels([a["asset_id"] for a in assets], fontsize=7)
    ax.set_xlabel("character offset in report 5761 markdown (total %d chars)" % mdlen)
    ax.set_xlim(0, mdlen)
    ax.invert_yaxis()
    ax.set_title("wp-5761-01 locator spans: every char_span re-slices to its quote")
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    fig.tight_layout()
    p2 = OUT / "fig_locator_map.png"
    fig.savefig(p2, dpi=130)
    plt.close(fig)
    figs.append({"name": p2.name,
                 "caption": "wp-5761-01 定位覆盖图：每条资产 locator 的 [start_char,end_char) 在 4141 字符源文中的位置，"
                            "颜色=resolution 状态（A01 为全文 document 级，覆盖 0..4141）。"})

    return [{"name": f["name"], "caption": f["caption"],
             "png_base64": base64.b64encode((OUT / f["name"]).read_bytes()).decode()} for f in figs]


# ------------------------------------------------------------------ build
def build():
    token = login()
    meta, md = fetch(token)
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit("SOURCE HASH MISMATCH: contract=%s actual=%s" % (EXPECTED_HASH, digest))
    if len(md) != EXPECTED_CHARS:
        raise SystemExit("SOURCE CHAR MISMATCH: contract=%d actual=%d" % (EXPECTED_CHARS, len(md)))

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report_5761.markdown").write_bytes(raw)  # byte-identical copy, no newline normalisation

    assets, seen = [], set()
    for aid, cls, label, section, anchor, mode, res, note in SPEC:
        if aid in seen:
            raise SystemExit("duplicate asset_id %s" % aid)
        seen.add(aid)
        loc = locate(md, anchor, mode)
        asset = {
            "asset_id": aid,
            "asset_class": cls,
            "label": label,
            "in_report_section": section,
            "locator": loc,
            "resolution": res,
            "resolution_check": dict(RES_CHECK[res]),
            "note": note,
        }
        if mode == "document":
            asset["note"] = ("%s；end_char=%d == source chars，start_line=1，end_line=%d"
                            % (note, loc["end_char"], loc["end_line"]))
        assets.append(asset)

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
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
        "claims_note": ("契约 objective.register_assets=true 且 objective.classify_report_type=false：本工序只登记资产"
                        "定位，不抽取 claim。claims 允许为空数组，claim 抽取由下游 03 工序包负责；"
                        "本包不对任何结论定性，也不写 verified 标记。"),
        "integrity": {
            "quote_uniqueness": "every quote re-sliced from the same bytes and counted exactly once "
                                "(scripts/kf/verify_5761.py, check source_locator_resolvable)",
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == EXPECTED_HASH,
        },
        "observations": [
            {"id": "O1", "kind": "title_mismatch",
             "detail": "平台报告 title 与 markdown H1 不同文：platform=%r / H1=%r。"
                       "本包 source.title 登记平台权威字段，H1 作为 A01 locator 原文并保留差异，不合并改写。"
                       % (meta.get("title"), md.split("\n", 1)[0].lstrip("# ").strip())},
            {"id": "O2", "kind": "figure_payload_absent",
             "detail": "平台 figures[] 三条仅含 name+caption，无 png_base64；④ 仅给图题。图1–图3 登记为 "
                       "referenced_unresolved，未以零字节冒充已解析。"},
            {"id": "O3", "kind": "hash_prefix_only",
             "detail": "回归锁航线表只给 sha256 前 16 位（原文 8c3d6e38fe4a1a7f… 等），本包按前缀登记，"
                       "不作全量哈希主张。"},
            {"id": "O4", "kind": "code_paths_not_in_worktree",
             "detail": "route/ 包、route/tests/test_route_second_cut.py、make_route_lock.py、run_second_cut.py、"
                       "artifacts/ice_route_second_cut/route_lock.json、summary.json 均不在 TensorKnowledge 交付"
                       "工作树内，按 referenced_unresolved 挂账，不猜路径、不臆造哈希。"},
        ],
    }

    mpath = OUT / "asset_manifest.json"
    mpath.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sch_path, binding = specialize_schema()

    # schema validation (proves the product, not just "we wrote a file")
    import jsonschema
    jsonschema.validate(manifest, json.loads(sch_path.read_text(encoding="utf-8")))

    figs = figures(manifest)

    mraw = mpath.read_bytes()
    result = {
        "schema_version": "kf_result.v1",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + digest,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(raw),
            "source_title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "contract_version": "1.0",
            "lane": "C",
            "work_package": PKG,
            "retrieved_via": "GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
            "local_copy": str((OUT / "report_5761.markdown").relative_to(REPO)),
            "generator": "scripts/kf/build_asset_manifest_5761.py",
            "verifier": "scripts/kf/verify_5761.py",
            "verification_note": "not_verified: verification is computed by the platform gate only; "
                                 "the producer does not certify its own products",
        },
        "outputs": {
            "asset_manifest.json": {
                "artifact_path": str(mpath.relative_to(REPO)),
                "artifact_sha256": hashlib.sha256(mraw).hexdigest(),
                "artifact_bytes": len(mraw),
                "schema": "asset_manifest.v1",
                "schema_path": str(sch_path.relative_to(REPO)),
                "schema_sha256": binding["specialized_schema_sha256"],
                "package_id": PKG,
                "task_type": "01-asset-registration",
                "report_id": REPORT_ID,
                "counts": manifest["counts"],
                "assets": manifest["assets"],
                "claims": manifest["claims"],
                "integrity": manifest["integrity"],
                "observations": manifest["observations"],
            }
        },
    }
    rpath = OUT / "kf_result.json"
    rpath.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "figures.json").write_text(
        json.dumps([{"name": f["name"], "caption": f["caption"]} for f in figs], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps({"assets": len(assets), "counts": manifest["counts"], "manifest_sha256":
                      hashlib.sha256(mraw).hexdigest(), "result": str(rpath.relative_to(REPO))},
                     ensure_ascii=False))
    return manifest, result


if __name__ == "__main__":
    build()
    sys.exit(0)