"""Register the source assets of report 9763 (work package wp-9763-01, task_type 01-asset-registration).

Design rules enforced here (same discipline as scripts/kf_register_448.py):
  * No hand transcription. Every ``quote`` is sliced out of the report markdown at run time from a
    programmatic anchor (unique line search + inclusive line span); each emitted quote is re-checked
    to be a *unique* substring of the markdown before anything is written.
  * Registration only. No claim extraction, no report-type classification (contract:
    objective.register_assets=true, classify_report_type=false, claims may be an empty array).
  * Nothing is marked verified. ``resolution`` describes locator/asset resolvability only;
    ``verification`` is computed by the platform gate, never by this script.
  * Unresolvable references are recorded as ``referenced_unresolved`` with the probe that failed --
    never dropped, never given an invented address.

Resolution semantics used here (declared, so the field is reproducible rather than asserted):
  resolved_in_source    the asset body *is* text inside the report markdown (quote == body)
  referenced_unresolved the asset body lives outside the markdown and is not reachable inside this
                        worktree; the locator is the report line that points at it
  declared_absent       the report itself declares the asset does not exist

Inputs:  runs/wp-9763-01/report_9763.md, runs/wp-9763-01/report_9763.json  (scripts/kf_fetch_9763.py)
Outputs: artifacts/wp-9763-01/asset_manifest.json
         docs/kf/wp-9763-01/asset_manifest.json           (durable mirror, byte-identical)
         runs/wp-9763-01/kf_result.wp-9763-01.json        (result envelope, kf_result.v1 shape)
         docs/kf/wp-9763-01/kf_result.json                (durable mirror of the envelope)

Usage: python3 scripts/kf_register_9763.py
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import pathlib
import sys

REPORT_ID = "9763"
PACKAGE_ID = "wp-9763-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_HASH = "ca29ba6f428001ddc1546e10c82b71ad1a18dcbf1c2bd09a1abd96e9760b1df3"
CONTRACT_CHARS = 3884
SOURCE_URI = "tensor://reports/9763"
FEM_ROOT = os.environ.get("KF_TENSORFEM_ROOT", "/root/tensor-ecosystem/TensorFEM")

RUN_DIR = pathlib.Path("runs/wp-9763-01")
ART_DIR = pathlib.Path("artifacts/wp-9763-01")
DOC_DIR = pathlib.Path("docs/kf/wp-9763-01")

# asset_id, asset_class, label, start anchor (unique line substring), end anchor, resolution, note
ASSETS = [
    ("A01", "document", "报告正文（markdown 全文）", None, None, "resolved_in_source",
     "整篇 markdown 即源资产本体；sha256 见 source.hash，与契约 source_hash 一致"),
    ("A02", "heading", "报告标题（H1）", "# TensorFEM 流固耦合（FSI）验证面", None, "resolved_in_source",
     "标题行；与平台 title 字段同源（逐字一致）"),
    ("A03", "provenance_lineage", "任务谱系行（P87W2-N05 / Mission 8461）",
     "## P87W2-N05 | Mission 8461", None, "resolved_in_source",
     "报告内声明的节点号与 mission 号；仅登记，不与平台 mission 表交叉断言"),
    ("A04", "narrative", "物理背景（颤振现象 + Theodorsen 1935 / Dowell 1995 出处）",
     "颤振是飞行器/桥梁/涡轮叶片等柔性结构", None, "resolved_in_source",
     "文献锚点以文字引用形式出现，报告未给出 DOI/页码"),
    ("A05", "parameter_table", "几何与参数表（9 行：L/b/h/E/ρ_s/ν/ρ_f/μ/U）",
     "| 参数 | 符号 | 值 | 单位 |", "| 流速范围 | U | [5, 50] | m/s |", "resolved_in_source",
     "表头+分隔行+9 行数据；数值仅登记不换算、不校验物理一致性"),
    ("A06", "parameter_set", "典型截面无量纲参数（μ/σ/r_α/x_α）",
     "### 典型截面参数（无量纲）", "- 静不平衡 x_α = 0（对称截面）", "resolved_in_source",
     "4 条无量纲参数定义原文；质量比 μ 定义式 m/(πρ_f b²) 在本资产内"),
    ("A07", "method_statement", "耦合策略（分区弱耦合，3 条）",
     "### 耦合策略", "3. **时间推进**：Staggered 格式", "resolved_in_source",
     "气动力/结构/时间推进三项原文；含 Theodorsen 函数 C(k) 表达式与 Δt=0.01"),
    ("A08", "method_statement", "颤振判据（4×4 状态空间特征值）",
     "### 颤振判据", "特征值分析：求解 4×4 状态空间特征值问题", "resolved_in_source",
     "判据定义原文：最大实部 > 0 判颤振失稳"),
    ("A09", "formula", "关键公式①：Theodorsen 颤振速度 U_cr/(bω_α) = 2√μ",
     "- Theodorsen 颤振速度：U_cr/(bω_α) = 2√μ", None, "resolved_in_source",
     "canonical case 解析式；第 3(a) 节对标列同式，详见 cross_checks.circularity_note"),
    ("A10", "formula", "关键公式②：颤振频率 ω_fl/ω_α ≈ √σ ≈ 0.4472",
     "- 颤振频率：ω_fl/ω_α ≈ √σ = √0.2 ≈ 0.4472", None, "resolved_in_source",
     "解析近似式；4 个 μ 共用同一值，与 μ 无关（见 cross_checks）"),
    ("A11", "formula", "关键公式③：增长率 σ 超/亚临界线性式",
     "- 增长率：σ ≈ 0.3(U/U_cr - 1)", None, "resolved_in_source",
     "超临界 0.3(U/U_cr-1) 与亚临界 -0.1(1-U/U_cr) 两条近似式"),
    ("A12", "code_pointer", "工具链声明（theodorsen.py / fsi_flutter.py / NumPy-SciPy / Matplotlib）",
     "### 工具链", "- Matplotlib：论文级图表", "resolved_in_source",
     "仅 basename，无仓库路径；对应模块在 TensorFEM 检出中可达（见 resolution_check.pointer_probe）"),
    ("A13", "results_table", "结果表 (a)：U_cr vs μ（4 行）",
     "| μ | U_cr (TensorFEM) | U_cr (Theodorsen 2√μ) | 误差 |", "| 50 | 14.1421 | 14.1421 | 0.0000% |",
     "resolved_in_source", "数值表原文；数值仅登记，算术复算见 cross_checks.arith_reproduction"),
    ("A14", "acceptance_criterion", "验收判据 (a)：U_cr 误差 < 5%",
     "**判据 (a)：误差 < 5% → ✅ PASS（最大误差 0.00%）**", None, "resolved_in_source",
     "报告自报 PASS；本工序不采信、不改判（verified 由平台门计算）"),
    ("A15", "results_table", "结果表 (b)：ω_fl/ω_α vs μ（4 行）",
     "| μ | ω_fl/ω_α (TensorFEM) | ω_fl/ω_α (Theodorsen √σ) | 误差 |", "| 50 | 0.4472 | 0.4472 | 0.0000% |",
     "resolved_in_source", "数值表原文"),
    ("A16", "acceptance_criterion", "验收判据 (b)：ω_fl 误差 < 3%",
     "**判据 (b)：误差 < 3% → ✅ PASS（最大误差 0.00%）**", None, "resolved_in_source",
     "报告自报 PASS；本工序不采信"),
    ("A17", "results_table", "结果表 (c)：超临界增长率 σ vs U/U_cr（4 行）",
     "| U/U_cr | σ (TensorFEM) | σ (Dowell 线性) | 误差 |", "| 1.5 | 0.150000 | 0.150000 | 0.00% |",
     "resolved_in_source", "数值表原文；对照列标注 Dowell 线性"),
    ("A18", "acceptance_criterion", "验收判据 (c)：σ 误差 < 10%",
     "**判据 (c)：误差 < 10% → ✅ PASS（最大误差 0.00%）**", None, "resolved_in_source",
     "报告自报 PASS；本工序不采信"),
    ("A19", "results_table", "结果表 (d)：亚临界 σ（3 行）",
     "| U/U_cr | σ | 稳定性 |", "| 0.9 | -0.010000 | ✅ 衰减 |", "resolved_in_source",
     "数值表原文"),
    ("A20", "acceptance_criterion", "验收判据 (d)：亚临界 σ < 0",
     "**判据 (d)：σ < 0 → ✅ PASS**", None, "resolved_in_source", "报告自报 PASS；本工序不采信"),
    ("A21", "numeric_anchor", "结果 (e)：质量比标度指数 0.500000（理论 0.5）",
     "### (e) 质量比标度律", "**判据 (e)：指数误差 < 2% → ✅ PASS**", "resolved_in_source",
     "拟合区间 μ ∈ [1, 100]、指数 0.500000、误差 0.0000% 原文"),
    ("A22", "convergence_statement", "结果 (f)：时间步收敛性（Δt 0.05→0.002）",
     "### (f) 时间步收敛性", "**判据 (f)：→ ✅ PASS**", "resolved_in_source",
     "章节名为「时间步收敛性」，第 6 节表内写作「网格收敛」，用词不一致见 cross_checks"),
    ("A23", "negative_control", "结果 (g)：负控 μ=10⁶ → U_cr=2000.0",
     "### (g) 负控", "**判据 (g)：→ ✅ PASS**", "resolved_in_source",
     "负控定义与结果原文"),
    ("A24", "figure_declaration", "图件声明：见内嵌 figures（7 张）",
     "见内嵌 figures（7 张论文级图表）。", None, "resolved_in_source",
     "正文仅给数量与「内嵌」声明，未给文件名/图注；文件名证据在 A25"),
    ("A25", "figure_set", "图件集 7 张（平台 figures 元数据 + fig[1-7] 命名）",
     "- 图表：`artifacts/fsi_flutter/fig[1-7]_*.png`", None, "referenced_unresolved",
     "平台 figures 字段有 7 条 name+caption，但无 png 字节；本工作树与 TensorFEM 检出均无该 png 文件"),
    ("A26", "limitation_set", "局限性与适用范围（5 条）",
     "### 局限性与适用范围", "5. **经验近似**：增长率公式", "resolved_in_source",
     "5 条限制原文；其中第 5 条直接限定 A11 增长率公式为临界点近邻近似"),
    ("A27", "pitfall_set", "踩过的坑（3 条）",
     "### 踩过的坑", "3. FFT 频率提取", "resolved_in_source", "3 条工程经验原文"),
    ("A28", "roadmap", "后续改进方向（4 条）",
     "### 后续改进方向", "4. 强耦合 FSI 实现", "resolved_in_source",
     "4 条计划原文；第 1 条声明当前气动力为 Theodorsen 代理而非全场求解"),
    ("A29", "criteria_table", "误差判定总表（8 行判据 a-h）",
     "| 判据 | 要求 | 实际 | 结果 |", "**全部 8 项判据通过。**", "resolved_in_source",
     "8 行判据原文含 (h) pytest 覆盖行；该行与审计链的测试计数不一致，见 cross_checks"),
    ("A30", "code_pointer", "审计链·代码指针（src/tensorfem/theodorsen.py, fsi_flutter.py）",
     "- 代码：`src/tensorfem/theodorsen.py`", None, "referenced_unresolved",
     "相对 TensorFEM 仓库根；本工作树不可达，TensorFEM 检出可达（见 resolution_check.pointer_probe）"),
    ("A31", "test_pointer", "审计链·测试指针（tests/test_fsi_*.py 4 个文件）",
     "- 测试：`tests/test_fsi_flutter_critical_speed.py`", None, "referenced_unresolved",
     "4 个测试文件名；本工作树不可达，TensorFEM 检出可达（未执行，超出本工序范围）"),
    ("A32", "run_command", "审计链·测试运行记录（pytest → 104 passed）",
     "- 测试运行：`pytest tests/test_fsi_*.py -v` → 104 passed", None, "referenced_unresolved",
     "运行记录不可在本工作树复现（无该测试集）；与判据 (h) 的 60 tests 数值冲突见 cross_checks"),
]

MD_FILES = {  # pointer assets: relative path(s) probed inside the TensorFEM checkout
    "A30": ["src/tensorfem/theodorsen.py", "src/tensorfem/fsi_flutter.py"],
    "A31": ["tests/test_fsi_flutter_critical_speed.py", "tests/test_fsi_flutter_frequency.py",
            "tests/test_fsi_amplitude_growth.py", "tests/test_fsi_mass_ratio_scaling.py"],
}


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def line_index(lines, anchor: str) -> int:
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor {anchor!r} matched {len(hits)} lines (need exactly 1): {hits}")
    return hits[0]


def offsets(lines):
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return offs


def build_locator(md: str, lines, offs, start_anchor, end_anchor):
    if start_anchor is None:  # whole document
        return dict(method="document", start_char=0, end_char=len(md), start_line=0,
                    end_line=len(lines) - 1, quote=md, unique=True)
    i = line_index(lines, start_anchor)
    j = i if end_anchor is None else line_index(lines, end_anchor)
    if end_anchor is not None and j < i:
        raise SystemExit(f"end anchor before start anchor for {start_anchor!r}")
    start = offs[i]
    end = offs[j] + len(lines[j])
    quote = md[start:end]
    unique = md.count(quote) == 1
    if not unique:
        raise SystemExit(f"quote not unique for {start_anchor!r}: {quote[:60]!r}")
    return dict(method="char_span", start_char=start, end_char=end, start_line=i, end_line=j,
                quote=quote, unique=True)


def section_of(lines, start_line: int) -> str:
    head = "(document)"
    for ln in lines[: start_line + 1]:
        if ln.startswith("#"):
            head = ln.strip()
    return head


def probe_paths(paths):
    out = {}
    for p in paths:
        wt = pathlib.Path(p)
        ext = pathlib.Path(FEM_ROOT) / p if FEM_ROOT else pathlib.Path("/nonexistent") / p
        out[p] = dict(worktree=wt.is_file(),
                      external_checkout=dict(root=FEM_ROOT, exists=ext.is_file(),
                                             bytes=ext.stat().st_size if ext.is_file() else None))
    return out


def resolution_check(asset_id, cls, loc, payload):
    if cls in ("code_pointer", "test_pointer", "run_command"):
        if asset_id in MD_FILES:
            probes = probe_paths(MD_FILES[asset_id])
            hit = all(v["external_checkout"]["exists"] for v in probes.values())
            return dict(check="pointer_target_probe(worktree, external_checkout)",
                        result="unresolved" if not any(v["worktree"] for v in probes.values()) else "resolved",
                        worktree_reachable=False, external_checkout_reachable=hit,
                        paths=probes,
                        detail="resolution 判据=本工作树内能否拿到资产本体；跨仓检出命中仅为信息性证据，不计入 resolved")
        # A12 toolchain: basenames only, no repo-relative path declared
        base = ["theodorsen.py", "fsi_flutter.py"]
        found = {b: bool(glob.glob(os.path.join(FEM_ROOT, "src", "**", b), recursive=True)) if FEM_ROOT else False
                 for b in base}
        return dict(check="basename_probe(external_checkout)",
                    result="unresolved",
                    basenames_resolved=found,
                    detail="报告仅给 basename（无目录），无法形成唯一地址；本资产本体为文本，resolution 按文本判 resolved_in_source")
    if asset_id == "A25":
        figs = payload.get("figures") or []
        png_hits = []
        for root in (".", FEM_ROOT):
            if root and os.path.isdir(root):
                png_hits += glob.glob(os.path.join(root, "artifacts", "fsi_flutter", "fig*.png"))
        return dict(check="figure_pointer_resolution(platform figures field + disk glob)",
                    result="unresolved",
                    platform_figure_count=len(figs),
                    platform_figure_names=[f.get("name") for f in figs if isinstance(f, dict)],
                    png_bytes_in_payload=any(isinstance(f, dict) and f.get("png_base64") for f in figs),
                    png_files_found_on_disk=len(png_hits),
                    detail="图件元数据可得（7 条 name+caption），图件本体（png 字节/文件）在平台 payload 与本机均不可得")
    return dict(check="char_span_in_source_markdown", result="resolved",
                unique_occurrence=loc["unique"])


def cross_checks(md, lines, payload):
    import math
    checks = []

    def add(cid, what, result, evidence_lines, detail):
        checks.append(dict(check_id=cid, what=what, result=result,
                           evidence=[dict(quote=lines[i], line=i) for i in evidence_lines],
                           detail=detail))

    # 1) contract-vs-source identity
    add("C1_contract_source_identity",
        "契约 source_hash / chars 与实测 markdown 一致",
        "consistent" if (sha256_text(md) == CONTRACT_HASH and len(md) == CONTRACT_CHARS) else "inconsistent",
        [], dict(measured_sha256=sha256_text(md), contract_sha256=CONTRACT_HASH,
                 measured_chars=len(md), contract_chars=CONTRACT_CHARS))

    # 2) figure count declared in three places
    figs = payload.get("figures") or []
    add("C2_figure_count_agreement",
        "A24 正文声明 7 张 vs 平台 figures 字段条数 vs A25 fig[1-7] 命名",
        "consistent" if (len(figs) == 7 and "7 张" in lines[118] and "fig[1-7]" in lines[159]) else "inconsistent",
        [118, 159], dict(markdown_claim="7 张论文级图表", platform_figures=len(figs),
                         audit_glob="fig[1-7]"))

    # 3) pytest count conflict inside the source (no correction performed)
    add("C3_pytest_count_conflict",
        "判据 (h) 与审计链的 pytest 计数互相矛盾（60 vs 104）",
        "inconsistent",
        [151, 160],
        dict(criterion_row="60 tests PASS", audit_chain="104 passed",
             summary_field=("104 项 pytest 全 PASS" if "104" in (payload.get("summary") or "") else None),
             action="仅登记矛盾，不做取舍、不改写上游"))

    # 4) metric naming drift for (f)
    add("C4_metric_naming_drift",
        "第 (f) 节标题「时间步收敛性」与第 6 节表行「网格收敛」用词不一致",
        "inconsistent", [104, 149],
        dict(section_title="时间步收敛性", table_row="网格收敛", action="仅登记，不做判读"))

    # 5) arithmetic reproduction of the numbers the report itself quotes
    a_rows = [(5, 4.4721), (10, 6.3246), (20, 8.9443), (50, 14.1421)]
    a_err = max(abs(round(2 * math.sqrt(mu), 4) - v) for mu, v in a_rows)
    c_rows = [(1.1, 0.030000), (1.2, 0.060000), (1.3, 0.090000), (1.5, 0.150000)]
    c_err = max(abs(round(0.3 * (r - 1.0), 6) - v) for r, v in c_rows)
    d_rows = [(0.5, -0.050000), (0.7, -0.030000), (0.9, -0.010000)]
    d_err = max(abs(round(-0.1 * (1.0 - r), 6) - v) for r, v in d_rows)
    add("C5_arith_reproduction",
        "表 (a)(b)(c)(d)(g) 数值 vs 报告自述公式的算术复算（4-6 位小数内）",
        "consistent" if max(a_err, c_err, d_err) <= 5e-7 and abs(round(2 * math.sqrt(1e6), 1) - 2000.0) <= 0.05
        else "inconsistent",
        [40, 42, 56, 112],
        dict(max_abs_dev_a=a_err, max_abs_dev_c=c_err, max_abs_dev_d=d_err,
             sqrt_sigma_0p2=round(math.sqrt(0.2), 4), negative_control_2sqrt_1e6=2 * math.sqrt(1e6),
             scope="只复算报告自己写的公式，不独立验证物理/方法"))

    # 6) circularity observation (not adjudicated here)
    add("C6_reference_column_circularity",
        "表 (a)(b) 的「解析解/Theodorsen」列与报告关键公式① ② 同式，数值逐位相同：0.0000% 误差可能来自公式自比较而非独立求解",
        "unresolved",
        [40, 41, 56, 67],
        dict(why="本工序只做资产登记，判读归下游工序；此处仅保留可定位证据",
             observed="TensorFEM 列与解析列在 4 位小数上逐项相等",
             downstream="抽取/核验工序需查 TensorFEM 侧是否独立求解或直接调用同一公式"))
    return checks


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    payload = json.loads((RUN_DIR / "report_9763.json").read_text())
    md = (RUN_DIR / "report_9763.md").read_text(encoding="utf-8")
    md_hash = sha256_text(md)
    if md_hash != CONTRACT_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {CONTRACT_HASH}")
        return 2
    if len(md) != CONTRACT_CHARS:
        print(f"FATAL: chars {len(md)} != contract chars {CONTRACT_CHARS}")
        return 2

    lines = md.split("\n")
    offs = offsets(lines)

    assets, seen = [], set()
    for aid, cls, label, sa, ea, resolution, note in ASSETS:
        if aid in seen:
            raise SystemExit(f"duplicate asset_id {aid}")
        seen.add(aid)
        loc = build_locator(md, lines, offs, sa, ea)
        assets.append(dict(
            asset_id=aid, asset_class=cls, label=label,
            in_report_section=section_of(lines, loc["start_line"]),
            locator=loc, resolution=resolution,
            resolution_check=resolution_check(aid, cls, loc, payload),
            note=note,
        ))

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI, field="markdown", hash_alg="sha256", hash=md_hash,
            chars=len(md), bytes_utf8=len(md.encode()),
            title=payload.get("title"), scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"), platform_mission_id=payload.get("mission_id"),
            platform_status=payload.get("status"), platform_tags=payload.get("tags", []),
            platform_figures=payload.get("figures", []),
            contract_hash_match=True, contract_chars_match=True,
            retrieved_via="GET %s/tensor/reports/9763" % os.environ.get(
                "TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
            local_copy=str(RUN_DIR / "report_9763.md"),
        ),
        counts=dict(assets=len(assets), by_class=by_class, by_resolution=by_res,
                    resolved_in_source=by_res.get("resolved_in_source", 0),
                    referenced_unresolved=by_res.get("referenced_unresolved", 0),
                    declared_absent=by_res.get("declared_absent", 0)),
        assets=assets,
        cross_checks=cross_checks(md, lines, payload),
        claims=[],
        claims_note=("按工作包契约 objective.classify_report_type=false 且 notes 明确允许 claims 为空数组："
                     "本工序只做资产定位登记，不抽取知识 claim；claim 抽取与判读归下游工序。"
                     "cross_checks 中 result=unresolved 的条目是留给下游的证据包，不是结论。"),
        integrity=dict(
            quote_uniqueness="每条 quote 已在脚本内断言为 markdown 的唯一子串（md.count(q)==1），复核见 scripts/kf_verify_9763.py",
            hash_recomputed_locally=True, hash_matches_contract=True,
            nothing_marked_verified="manifest 中无 verified 字段；verification 由平台门计算",
            no_hand_transcription="quote 全部由 char span 从原文切片，脚本不接受手写引文",
        ),
        scope_boundary=dict(
            report_ids_touched=[REPORT_ID],
            upstream_artifacts_modified=False,
            verification_performed_by="platform gate",
        ),
    )

    art = ART_DIR / "asset_manifest.json"
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art.write_text(blob)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != art_hash:
        print("FATAL: durable mirror differs from artifact")
        return 3

    # The envelope carries the manifest object verbatim: re-serialising outputs["asset_manifest.json"]
    # with the same formatting must reproduce the artifact file byte for byte (checked by the verifier).
    outputs_manifest = manifest

    result = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI, source_field="markdown", source_hash="sha256:" + md_hash,
            source_chars=len(md), source_bytes_utf8=len(md.encode()),
            source_title=payload.get("title"), scenario_key=payload.get("scenario_key"),
            contract_version="1.0", lane="A", work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(RUN_DIR / "report_9763.md"),
            generator="scripts/kf_register_9763.py", verifier="scripts/kf_verify_9763.py",
            verification_status="not_verified",
            artifact_path=str(art), artifact_sha256=art_hash, artifact_bytes=art.stat().st_size,
            notes="asset registration only; no claim extraction, nothing marked verified",
        ),
        outputs={"asset_manifest.json": outputs_manifest},
    )
    res_path = RUN_DIR / "kf_result.wp-9763-01.json"
    res_blob = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    res_path.write_text(res_blob)
    (DOC_DIR / "kf_result.json").write_text(res_blob)

    print("markdown sha256:", md_hash, "MATCH")
    print("chars:", len(md), "bytes:", len(md.encode()))
    print("assets:", len(assets))
    print("by_class:", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("cross_checks:", json.dumps([(c["check_id"], c["result"]) for c in manifest["cross_checks"]], ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", res_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())