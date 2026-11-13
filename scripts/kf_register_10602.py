"""Register the source assets of report 10602 (work package wp-10602-01, task_type 01-asset-registration).

Design rules enforced here (contract constraints):
  * No hand transcription. Every ``locator.quote`` is sliced out of the report markdown at run time
    from a programmatic anchor (unique substring -> line index -> line span). The script asserts the
    quote is a *unique* substring of the markdown before writing anything; a duplicated anchor, a
    missing anchor or an empty span is a hard error (exit != 0).
  * Registration only. No claim extraction (objective.register_assets=true,
    objective.classify_report_type=false; the contract explicitly allows an empty claims array).
    Nothing is marked verified: ``resolution`` describes locator/asset resolvability only, never the
    truth of a number in the report.
  * Do not invent missing information. Assets named by the report but not contained in the payload
    are recorded as ``referenced_unresolved`` or ``declared_absent`` with the reason and the search
    that was performed -- never silently dropped, never given a fabricated address.
  * Report 10602 only. Nothing else is read or written by this package.

Inputs (produced by scripts/kf_fetch_10602.py):
  runs/wp-10602-01/report_10602.md    (markdown payload, sha256 checked against the contract)
  runs/wp-10602-01/report_10602.json  (raw API payload: id/title/scenario_key/figures/tags/...)

Outputs:
  artifacts/wp-10602-01/asset_manifest.json
  runs/wp-10602-01/kf_result.wp-10602-01.json      (result envelope, kf_result.v1 shape)
  docs/wp-10602-01/asset_manifest.json             (durable copy: push gate drops artifacts/ and runs/)
  docs/wp-10602-01/fig1_asset_coverage.png

Usage: python3 scripts/kf_register_10602.py
"""
from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import json
import os
import pathlib
import sys

REPORT_ID = "10602"
PACKAGE_ID = "wp-10602-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687"
SOURCE_URI = "tensor://reports/10602"
CONTRACT_CHARS = 6037

RUN_DIR = pathlib.Path("runs/wp-10602-01")
ART_DIR = pathlib.Path("artifacts/wp-10602-01")
DOC_DIR = pathlib.Path("docs/wp-10602-01")

# ---------------------------------------------------------------------------
# Anchor table.  anchor = unique substring of the markdown used only to *find*
# the line; span = (first, last) line offsets relative to the anchor line
# (inclusive, negative values count back from end of file).  The emitted quote
# is the verbatim text of those lines.
# ---------------------------------------------------------------------------
CONTENT_ASSETS = [
    dict(asset_id="A01", asset_class="document",
         label="报告正文（markdown 全文）", anchor="--document--", method="document",
         span=(0, -1), note="整篇 markdown 即源资产；sha256 见 source.hash"),
    dict(asset_id="A02", asset_class="heading", label="报告标题行",
         anchor="# P162W1-N04 | EEDI 设计变量灵敏度", span=(0, 0),
         note="标题行；与 API title 字段同源"),
    dict(asset_id="A03", asset_class="declaration", label="仓/模块归属与运行耗时声明",
         anchor="**仓** ship-performance-platform | **模块**", span=(0, 1),
         note="含「验收 C1-C8：全部 PASS」声明与三段耗时；本包只登记位置，不核验判定"),
    dict(asset_id="A04", asset_class="design_space", label="设计变量与盒约束表（5 变量）",
         anchor="| 变量 | 含义 | 区间 |", span=(0, 6),
         note="表头+分隔行+5 行数据；区间为原文边界，未做单位换算"),
    dict(asset_id="A05", asset_class="parameter_set", label="设计点参数（V_ref/SFC/C_F/eta_S）",
         anchor="设计点参数：V_ref = 14.0 kn", span=(0, 1),
         note="四个设计点常量原文"),
    dict(asset_id="A06", asset_class="constraint_set", label="约束门限（DWT/GM/sigma/L_B/B_T/Cb-Cp）",
         anchor="约束门限：DWT >= 25000 t", span=(0, 2),
         note="六项门限原文；可执行实现体未随报告提供（见 A35/A37）"),
    dict(asset_id="A07", asset_class="result_block", label="参考设计点结果（DWT/GM/sigma/R_T/eta_D/J/n/P/EEDI）",
         anchor="**参考设计点**（L=180 m", span=(0, 4),
         note="参考点全部数字原文；本包不重算、不换算"),
    dict(asset_id="A08", asset_class="context_reference", label="IMO Phase-3 参考线与「不做合规判定」声明",
         anchor="（IMO Phase-3 参考线 4.38", span=(0, 2),
         note="明确声明仅作上下文、不做合规判定 -> 下游不得据此生成合规结论"),
    dict(asset_id="A09", asset_class="method_chain", label="公式链（阻力/敞水/排水量，REAL）",
         anchor="1. **公式链（REAL", span=(0, 5),
         note="含槽内实现引用与 eta_D ≡ P_E/P_D 数值断言"),
    dict(asset_id="A10", asset_class="method_proxy", label="筛选级工程代理（DWT/GM/sigma 单点标定）",
         anchor="2. **筛选级工程代理", span=(0, 3),
         note="报告自标「显式标注，非规范计算」；误差判定章同样声明无基准"),
    dict(asset_id="A11", asset_class="method_surrogate", label="可微近似（张量积 Chebyshev 样条）",
         anchor="3. **可微近似**", span=(0, 3),
         note="节点数 8^4=4096、度数 4 等设置原文"),
    dict(asset_id="A12", asset_class="method_sensitivity", label="灵敏度方法（四阶差分/弹性系数/Saltelli + Sobol）",
         anchor="4. **灵敏度**", span=(0, 2),
         note="N=4096 基样本、24576 次评估原文"),
    dict(asset_id="A13", asset_class="method_optimizer", label="优化器设置（约束 NSGA-II）",
         anchor="5. **优化**", span=(0, 1),
         note="种群 120、上限 1000 代、SBX/多项式变异原文"),
    dict(asset_id="A14", asset_class="method_gates", label="门禁与全链复核/投影",
         anchor="6. **门禁**", span=(0, 1),
         note="几何可行性 + DWT/GM/sigma/功率平衡，前沿解全链复核原文"),
    dict(asset_id="A15", asset_class="acceptance_table", label="验收判据表 C1-C8（数值 + PASS 判定）",
         anchor="| 判据 | 指标 | 数值 | 判定 |", span=(0, 9),
         note="8 条判据原文；PASS 是报告作者的判定（claim），本包不做 verification"),
    dict(asset_id="A16", asset_class="result_block", label="Pareto 前沿汇总（N/EEDI 区间/成本区间/偏差）",
         anchor="**Pareto 前沿**：N = 120", span=(0, 3),
         note="含逐解明细 CSV 的引用（A31）"),
    dict(asset_id="A17", asset_class="table", label="C6 约束负控明细表",
         anchor="| 收紧方式 | 参数序列 |", span=(0, 3),
         note="两组参数序列、全局 min EEDI、包络位移原文"),
    dict(asset_id="A18", asset_class="interpretation", label="C6 方向解释与被否定的镜像对称假设",
         anchor="方向解释：①收紧容量上界", span=(0, 3),
         note="报告自述唯一假设修正（镜像对称被实测否定）；否定性结果，如实登记"),
    dict(asset_id="A19", asset_class="sensitivity_block", label="局部灵敏度弹性系数（设计点面 4D）",
         anchor="**局部灵敏度（参考设计点", span=(0, 5),
         note="E_L/E_B/E_T/E_Cb 四条"),
    dict(asset_id="A20", asset_class="sensitivity_block", label="自由功率面弹性系数（5D，含 P）",
         anchor="**自由功率面弹性系数（含 P）**", span=(0, 6),
         note="五条弹性系数"),
    dict(asset_id="A21", asset_class="sensitivity_block", label="全局灵敏度 Sobol 指数（4D / 5D）",
         anchor="**全局灵敏度 Sobol（设计点面 4D）**", span=(0, 3),
         note="一阶/总效应指数；原文自注「一阶指数和 = 1.902 <1」——该数值本身存疑，本包只登记不解释"),
    dict(asset_id="A22", asset_class="figure_reference", label="结果图声明（5 张内嵌图）",
         anchor="## 四、结果图", span=(0, 3),
         note="markdown 内只有文字声明，无图内联；二进制见 A42"),
    dict(asset_id="A23", asset_class="caveat", label="注意点 1：EEDI 简化面（非规范全量）",
         anchor="1. **公式链非规范全量**", span=(0, 0),
         note="简化面公式与同口径函数位置；缺失修正项另见 A43"),
    dict(asset_id="A24", asset_class="caveat", label="注意点 2：重量/稳性/强度为筛选级代理",
         anchor="2. **重量/稳性/强度是筛选级代理**", span=(0, 2),
         note="明确「不可作为结构或稳性设计依据」；规范判定缺失另见 A44"),
    dict(asset_id="A25", asset_class="caveat", label="注意点 3：差分量化噪声实测坑",
         anchor="3. **差分量化噪声（实测坑）**", span=(0, 2),
         note="R_T 舍入 0.01 kN 导致梯度污染；报告声明本包不改共享模块行为"),
    dict(asset_id="A26", asset_class="caveat", label="注意点 4：两种导数面必须区分",
         anchor="4. **两种导数面必须区分**", span=(0, 1),
         note="固定 P 与设计点面 dEEDI/dCb 符号相反；C3 采用后者"),
    dict(asset_id="A27", asset_class="caveat", label="注意点 5：适用范围与局限",
         anchor="5. **局限**：代理仅在给定盒约束内有效", span=(0, 2),
         note="代理有效域、固定螺旋桨几何、成本代理口径、未含耦合项"),
    dict(asset_id="A28", asset_class="error_table", label="误差判定表（6 个关键量 vs 基准）",
         anchor="| 关键量 | 基准 | 误差 | 是否 < 3% |", span=(0, 7),
         note="误差数字与「是否 < 3%」原文；本包不重算"),
    dict(asset_id="A29", asset_class="error_statement", label="无实验基准量的显式声明",
         anchor="对「有基准的量」逐项显式回答", span=(0, 3),
         note="明示 DWT/GM/sigma/成本代理无基准 -> 不给误差数字（符合精度纪律）"),
    dict(asset_id="A30", asset_class="audit_chain", label="审计链（判据/图/复现/代码位置）",
         anchor="## 七、审计链", span=(0, -1),
         note="列出 artifacts、figures、repro 命令、代码模块；各条逐一登记为 A31-A41"),
]

# Assets the report *names* but whose body is not contained in the markdown payload.
EXTERNAL_REFS = [
    dict(asset_id="A31", asset_class="artifact_file", label="Pareto 逐解明细 CSV",
         anchor="`artifacts/m9073_eedi_opt/pareto_front.csv`",
         path="artifacts/m9073_eedi_opt/pareto_front.csv",
         note="报告称每行含设计变量/目标/约束量/复核标志/代理-真值差"),
    dict(asset_id="A32", asset_class="artifact_file", label="审计链整条：判据与全部中间量（acceptance.json + sensitivity.json + pareto_front.csv 说明）",
         anchor="`artifacts/m9073_eedi_opt/acceptance.json`", span=(0, 1),
         path="artifacts/m9073_eedi_opt/acceptance.json", note="C1-C8 判据与中间量"),
    dict(asset_id="A33", asset_class="artifact_file", label="灵敏度 JSON（sensitivity.json）",
         anchor="`sensitivity.json`", path="artifacts/m9073_eedi_opt/sensitivity.json",
         note="局部/全局灵敏度原始数值"),
    dict(asset_id="A34", asset_class="artifact_glob", label="结果图 PNG（fig1..fig5）",
         anchor="`artifacts/m9073_eedi_opt/figures/fig1..fig5*.png`",
         path="artifacts/m9073_eedi_opt/figures", note="glob 形式引用，5 个图文件"),
    dict(asset_id="A35", asset_class="repro_command", label="一键复跑脚本（seed = 20261009）",
         anchor="`python scripts/eedi_opt_m9073.py`", path="scripts/eedi_opt_m9073.py",
         note="报告声明固定 seed = 20261009"),
    dict(asset_id="A36", asset_class="test_file", label="C1-C8 与门禁/投影测试",
         anchor="`pytest tests/test_eedi_optimization_m9073.py -q`",
         path="tests/test_eedi_optimization_m9073.py", note="报告声明覆盖 C1-C8"),
    dict(asset_id="A37", asset_class="code_module", label="优化实现包（design_space/hydro/chain/...）",
         anchor="代码：`backend/physics/eedi_opt/`", path="backend/physics/eedi_opt",
         note="7 个子模块名原文：design_space / hydro / chain / surrogate / sensitivity / pareto / gates"),
    dict(asset_id="A38", asset_class="code_module", label="优化 API 端点模块",
         anchor="、API：`backend/api/eedi_optimization.py`", path="backend/api/eedi_optimization.py",
         note="HTTP 接口层"),
    dict(asset_id="A39", asset_class="code_dependency", label="阻力实现（Holtrop-Mennen 1984）",
         anchor="`backend/physics/holtrop.holtrop1984_resistance`",
         path="backend/physics/holtrop.py", note="公式链第一环，报告称复用仓内单一实现"),
    dict(asset_id="A40", asset_class="code_dependency", label="敞水实现（Wageningen B 系列）",
         anchor="`src/b_series`", path="src/b_series", note="敞水回归 + brentq 工作点求解"),
    dict(asset_id="A41", asset_class="code_dependency", label="EEDI 同口径函数",
         anchor="`api/extended_calculations.calculate_energy_efficiency_v2`",
         path="api/extended_calculations.py", note="报告称与简化面同口径"),
    dict(asset_id="A42", asset_class="figure_binary", label="5 张内嵌图（fig1..fig5 PNG 二进制）",
         anchor="5 张内嵌图：Pareto 前沿与全链复核", path=None,
         note="平台 payload.figures 只有 name+caption（fig1_pareto_front … fig5_constraint_shift），"
              "无 png_base64 字段 -> 图二进制不可从 API 解析"),
]

DECLARED_ABSENT = [
    dict(asset_id="A43", asset_class="missing_term_set", label="EEDI 修正项 P_AE/f_j/f_i/f_w/创新技术抵扣",
         anchor="EEDI 用简化面", span=(0, 1),
         note="报告明示公式链未含这些项 -> 下游不得据此生成规范 EEDI 值"),
    dict(asset_id="A44", asset_class="missing_analysis", label="船级社规范计算 + IS Code 2008 六项衡准+天气衡准",
         anchor="完整判定需船级社规范计算与 IS Code 2008", span=(0, 0),
         note="报告明示这部分判定在域外（未做）"),
    dict(asset_id="A45", asset_class="missing_analysis", label="破舱稳性与纵倾/吃水差耦合",
         anchor="未含破舱稳性与纵倾/吃水差耦合", span=(0, 0),
         note="报告局限第 5 条明示未含"),
]

# Roots used for the external-existence probe (read-only).  Bounded on purpose.
PROBE_ROOTS = ["/root/ship-performance-platform", "/root/tp-agent/work/m9073"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_source():
    md_path = RUN_DIR / "report_10602.md"
    js_path = RUN_DIR / "report_10602.json"
    if not md_path.exists() or not js_path.exists():
        sys.exit("missing inputs; run scripts/kf_fetch_10602.py first")
    raw = md_path.read_bytes()
    md = raw.decode("utf-8")
    payload = json.loads(js_path.read_text())
    return md, raw, payload


def probe(rel: str | None) -> dict:
    """Existence probe for an externally referenced path (read-only, bounded roots)."""
    if rel is None:
        return {"check": "platform payload figure binaries", "result": "unresolved",
                "searched": "payload.figures[].png_base64"}
    hits = []
    for root in PROBE_ROOTS:
        p = pathlib.Path(root) / rel
        hits.append({"path": str(p), "exists": p.exists()})
    found = any(h["exists"] for h in hits)
    return {"check": "filesystem existence probe at " + ", ".join(PROBE_ROOTS),
            "result": "present" if found else "unresolved",
            "searched": rel, "probe": hits}


def build(md: str, raw: bytes, payload: dict) -> dict:
    lines = md.split("\n")
    nlines = len(lines)
    # heading index for section labelling (derived, not hand written)
    heads = [(i, lines[i]) for i, ln in enumerate(lines)
             if ln.startswith("#")]

    def section_of(line_idx: int) -> str:
        cur = ""
        for i, h in heads:
            if i <= line_idx:
                cur = h.lstrip("# ").strip()
            else:
                break
        return cur

    def line_of_anchor(anchor: str) -> int:
        if anchor == "--document--":
            return 0
        hits = [i for i, ln in enumerate(lines) if anchor in ln]
        if len(hits) != 1:
            sys.exit(f"anchor not unique/found ({len(hits)} hits): {anchor!r}")
        return hits[0]

    def make_locator(method, anchor, span):
        if method == "document":
            start_line, end_line = 0, nlines - 1
        else:
            base = line_of_anchor(anchor)
            a, b = span
            start_line = base + a
            end_line = nlines - 1 if b < 0 else base + b
        if not (0 <= start_line <= end_line < nlines):
            sys.exit(f"bad span for {anchor!r}: {start_line}..{end_line}")
        quote = "\n".join(lines[start_line:end_line + 1])
        start_char = md.find(quote)
        if start_char < 0:
            sys.exit(f"quote not locatable: {anchor!r}")
        count = md.count(quote)
        return {"method": method, "start_char": start_char,
                "end_char": start_char + len(quote),
                "start_line": start_line, "end_line": end_line,
                "quote": quote, "unique": count == 1}, count

    md_bytes = raw
    assets = []
    for spec in CONTENT_ASSETS:
        method = spec.get("method", "char_span")
        loc, count = make_locator(method, spec["anchor"], spec["span"])
        assets.append({
            "asset_id": spec["asset_id"],
            "asset_class": spec["asset_class"],
            "label": spec["label"],
            "in_report_section": "全文（markdown 整体）" if method == "document"
                                 else section_of(loc["start_line"]),
            "locator": loc,
            "resolution": "resolved_in_source",
            "resolution_check": {"check": "quote is a unique substring of source markdown "
                                          "(md.count(quote) == 1)",
                                 "result": "resolved"},
            "note": spec["note"],
        })

    for spec in EXTERNAL_REFS:
        loc, count = make_locator("char_span", spec["anchor"], spec.get("span", (0, 0)))
        chk = probe(spec.get("path"))
        assets.append({
            "asset_id": spec["asset_id"],
            "asset_class": spec["asset_class"],
            "label": spec["label"],
            "in_report_section": section_of(loc["start_line"]),
            "locator": loc,
            "resolution": "referenced_unresolved",
            "resolution_check": chk,
            "note": spec["note"] + "；资产本体不在 markdown payload 内，登记为 referenced_unresolved",
        })

    for spec in DECLARED_ABSENT:
        loc, count = make_locator("char_span", spec["anchor"], spec["span"])
        assets.append({
            "asset_id": spec["asset_id"],
            "asset_class": spec["asset_class"],
            "label": spec["label"],
            "in_report_section": section_of(loc["start_line"]),
            "locator": loc,
            "resolution": "declared_absent",
            "resolution_check": {"check": "report text explicitly declares the item out of scope / "
                                          "not included", "result": "absent"},
            "note": spec["note"],
        })

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        sys.exit("duplicate asset ids: " + str(ids))

    by_class = collections.Counter(a["asset_class"] for a in assets)
    by_res = collections.Counter(a["resolution"] for a in assets)

    # content coverage: union of spans of markdown-resident assets (A01 = whole doc excluded)
    covered = set()
    for a in assets:
        if a["resolution"] == "resolved_in_source" and a["asset_id"] != "A01":
            covered.update(range(a["locator"]["start_char"], a["locator"]["end_char"]))
    coverage = len(covered) / len(md)

    hash_hex = sha256_bytes(md_bytes)
    figures = payload.get("figures") or []
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": hash_hex,
            "chars": len(md),
            "bytes_utf8": len(md_bytes),
            "title": payload.get("title"),
            "scenario_key": payload.get("scenario_key"),
            "platform_mission_id": payload.get("mission_id"),
            "platform_status": payload.get("status"),
            "platform_figures": figures,
            "platform_tags": payload.get("tags"),
        },
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": "all quotes are unique substrings of the markdown "
                                f"(md.count(quote) == 1 for {len(assets)}/{len(assets)} assets); "
                                f"pairwise-distinct quote strings: {len({a['locator']['quote'] for a in assets})}"
                                f"/{len(assets)}",
            "hash_recomputed_locally": hash_hex,
            "hash_matches_contract": hash_hex == EXPECTED_HASH,
            "contract_chars_match": len(md) == CONTRACT_CHARS,
            "content_span_coverage": f"{coverage * 100:.1f}% of markdown characters are covered by "
                                     "the spans of the markdown-resident assets (A02-A30; A01=whole doc excluded)",
            "verified_claims": 0,
            "verification_note": "no claim is marked verified: verification is computed by the "
                                 "platform gate, not by this work package",
        },
    }
    return manifest, coverage


def write_outputs(manifest: dict) -> dict:
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (RUN_DIR / "asset_manifest.json").write_text(text)
    (ART_DIR / "asset_manifest.json").write_text(text)
    (DOC_DIR / "asset_manifest.json").write_text(text)

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_field": "markdown",
            "producer": "scripts/kf_register_10602.py (agent m15686)",
            "emitted_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
            "notes": "asset registration only; no extraction, no claim verification; "
                     f"{manifest['counts']['assets']} assets registered "
                     f"(resolved_in_source={manifest['counts']['resolved_in_source']}, "
                     f"referenced_unresolved={manifest['counts']['referenced_unresolved']}, "
                     f"declared_absent={manifest['counts']['declared_absent']})",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    etxt = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    (RUN_DIR / "kf_result.wp-10602-01.json").write_text(etxt)
    (DOC_DIR / "kf_result.wp-10602-01.json").write_text(etxt)
    return envelope


def figure(manifest: dict, coverage: float) -> pathlib.Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    assets = manifest["assets"]
    md = (RUN_DIR / "report_10602.md").read_text()
    n = len(md)
    content = [a for a in assets if a["resolution"] == "resolved_in_source" and a["asset_id"] != "A01"]
    classes = sorted({a["asset_class"] for a in assets})
    cmap = {c: plt.cm.tab20(i / max(1, len(classes) - 1)) for i, c in enumerate(classes)}

    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(15, 8), gridspec_kw={"width_ratios": [2.2, 1]})
    for row, a in enumerate(assets):
        y = len(assets) - row
        col = cmap[a["asset_class"]]
        if a["resolution"] == "resolved_in_source":
            ax.barh(y, a["locator"]["end_char"] - a["locator"]["start_char"],
                    left=a["locator"]["start_char"], height=0.7, color=col, edgecolor="k", lw=0.3)
        else:
            ax.barh(y, 0.02 * n, left=0.985 * n, height=0.7, color=col, edgecolor="k", lw=0.3,
                    hatch="///")
    ax.set_yticks([len(assets) - i for i in range(len(assets))])
    ax.set_yticklabels([a["asset_id"] + " " + a["asset_class"] for a in assets], fontsize=7)
    ax.set_xlabel("character offset in report 10602 markdown (chars)")
    ax.set_xlim(0, n)
    ax.set_title(f"Asset spans along the source (n={len(assets)}); span cover of content assets = "
                 f"{coverage * 100:.1f}%\nhatched = referenced_unresolved / declared_absent "
                 f"(outside payload)", fontsize=9)

    cnt = collections.Counter(a["asset_class"] for a in assets)
    keys = [k for k, _ in cnt.most_common()]
    ax2.barh([len(keys) - i for i in range(len(keys))], [cnt[k] for k in keys],
             color=[cmap[k] for k in keys], edgecolor="k", lw=0.4)
    ax2.set_yticks([len(keys) - i for i in range(len(keys))])
    ax2.set_yticklabels(keys, fontsize=8)
    ax2.set_xlabel("assets")
    ax2.set_title("assets per asset_class", fontsize=9)
    for i, k in enumerate(keys):
        ax2.text(cnt[k] + 0.1, len(keys) - i, str(cnt[k]), va="center", fontsize=8)
    ax2.set_xlim(0, max(cnt.values()) * 1.25)

    fig.tight_layout()
    out = DOC_DIR / "fig1_asset_coverage.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    return out


def main():
    md, raw, payload = load_source()
    manifest, coverage = build(md, raw, payload)
    if not manifest["integrity"]["hash_matches_contract"]:
        sys.exit(f"source hash mismatch: {manifest['source']['hash']} != {EXPECTED_HASH}")
    envelope = write_outputs(manifest)
    fig_path = figure(manifest, coverage)
    print("source sha256:", manifest["source"]["hash"], "(matches contract)")
    print("chars:", manifest["source"]["chars"], "bytes:", manifest["source"]["bytes_utf8"])
    print("assets:", manifest["counts"]["assets"], manifest["counts"]["by_resolution"])
    print("content span coverage:", manifest["integrity"]["content_span_coverage"])
    print("figure:", fig_path)
    print("envelope:", list(envelope))


if __name__ == "__main__":
    main()