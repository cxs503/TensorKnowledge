#!/usr/bin/env python3
"""wp-9840-01 / 01-asset-registration — register the source assets of report 9840.

Scope (contract): confirm report_id + markdown byte hash, enumerate the resolvable
attachments/artifacts, and freeze a machine-checkable manifest. No claim extraction
(claims=[] is legitimate per contract), no verification (the platform gate computes it).

Zero hand-copying: every quote emitted in the manifest is sliced out of the source
markdown at build time (char span + line span recorded), never retyped.
"""
import hashlib
import json
import os
import pathlib
import sys

PACKAGE_ID = "wp-9840-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "9840"
EXPECTED_HASH = "159d4a1419890fe82d46b49037d00273376244d1f24a6503e386c6243d882524"
SOURCE_URI = "tensor://reports/9840"

RUN_DIR = pathlib.Path("runs/wp-9840-01")
ART_DIR = pathlib.Path("artifacts/wp-9840-01")
# durable mirror: the repo push gate drops artifacts/** and runs/**, so the committed
# copy of every deliverable lives under docs/wp-9840-01/ (byte-identical).
DOC_DIR = pathlib.Path("docs/wp-9840-01")

# Anchor table. mode:
#   "document" -> whole markdown
#   "table"    -> anchor line + following contiguous '|' lines (header..last data row)
#   "block"    -> anchor line + n following lines
#   "para"     -> anchor line + following contiguous non-empty, non-heading lines
#   "section"  -> anchor line(s) up to (excluding) the next heading of level <= anchor level
# Span is resolved against the frozen local copy; the emitted quote is a verbatim slice.
ASSETS = [
    # NOTE: no document-level asset (A01) on purpose. Registering the full markdown as a quote
    # would inject the source's own ```bash fences into the result envelope, making the report's
    # single ```json block ambiguous for fence parsers. The whole document is registered by
    # source.hash (sha256 over the exact bytes) instead — see integrity/document_registration.
    dict(asset_id="A02", asset_class="heading", label="报告标题（H1）",
         anchor="# IN65-N04 — DG 对流–扩散验证面", mode="block", n=0,
         resolution="resolved_in_source", note="与 API title 字段同源。"),
    dict(asset_id="A03", asset_class="metadata", label="节点/战役/仓/模块/机器门/分层声明",
         anchor="**节点** IN65-N04", mode="para", resolution="resolved_in_source",
         note="定位源仓与模块路径；模块本体见 A27/A28（本工作树内不可解析）。"),
    dict(asset_id="A04", asset_class="problem_statement", label="从上节点继承的四个未解问题（①②③④）",
         anchor="① 变系数旋转对流中 P2 误差地板", mode="para",
         resolution="resolved_in_source", note="本节点要逐条打开的四个开放问题的原文表述。"),
    dict(asset_id="A05", asset_class="criteria_table", label="模型问题与判据表 F1–F7（7 行）",
         anchor="| # | 方程 | 区域 / 精确解 | 判据 |", mode="table",
         resolution="resolved_in_source", note="七个算例的方程/区域/精确解/判据；数值仅登记不换算。"),
    dict(asset_id="A06", asset_class="method_setup", label="离散设置（节点型 DG / Gauss–Lobatto / SSP-RK3 / CFL / 求积）",
         anchor="**离散**：节点型 DG", mode="para",
         resolution="resolved_in_source", note="方法学声明；实现体见 A27（未解析）。"),
    dict(asset_id="A07", asset_class="code_declaration", label="新增工具声明：hllc.py（HLLC + Zhang–Shu）与 frontier.py",
         anchor="* `hllc.py`：Toro HLLC 通量", mode="block", n=1,
         resolution="resolved_in_source", note="两条工具声明的原文；代码本体见 A27（未解析）。"),
    dict(asset_id="A08", asset_class="toolchain", label="流程①–⑤（运行→出图→判决→报告生成器）",
         anchor="**流程**：① 参数化基准", mode="para",
         resolution="resolved_in_source", note="含集群节点 n315/n330 与 9 分片陈述，算力出处见 A31。"),
    dict(asset_id="A09", asset_class="table", label="F1 收敛数据表（锥/丘/宽高斯/窄高斯 × P1–P3，29 行数据）",
         anchor="| 初场 | 阶 | N | L2 | L2(kink带) | L2(光滑区) | 误差占比(kink带) | 质量漂移 |",
         mode="table", resolution="resolved_in_source",
         note="原始 L2/分带误差/质量漂移；本工序只登记，不复核数值。"),
    dict(asset_id="A10", asset_class="table", label="F1 最小二乘收敛阶表（9 行）",
         anchor="| 初场 | 阶 | L2 order | kink 带 order | 光滑区 order | 理论 p+1 |", mode="table",
         resolution="resolved_in_source", note="阶数与理论 p+1 并列的判读面。"),
    dict(asset_id="A11", asset_class="table", label="F2 一维 kink vs 光滑阶数表（6 行）",
         anchor="| 初场 | 阶 | L2 order | L1 order | 光滑理论 p+1 | H^{3/2} 上界 |", mode="table",
         resolution="resolved_in_source", note="正则性决定阶的对照面（kink L2 1.145–1.313 vs smooth 2.204–3.755）。"),
    dict(asset_id="A12", asset_class="table", label="F3 制造解 L2(u)/L2(q) 表（8 行）",
         anchor="| 阶 | N | L2(u) | L2(q) | 步数 |", mode="table",
         resolution="resolved_in_source", note="含步数，可反推时间步设置。"),
    dict(asset_id="A13", asset_class="table", label="F3 阶与理论偏差表（P1/P2）",
         anchor="| 阶 | L2(u) order | L2(q) order | 理论 | 偏差 |", mode="table",
         resolution="resolved_in_source", note="偏差 0.017/0.005 与 §6 判定表互指。"),
    dict(asset_id="A14", asset_class="table", label="F4 理想气体 Sod 主表（hllc/rusanov × P1/P2 × N=100–400，12 行）",
         anchor="| 通量 | 阶 | N | 激波位置误差% | 密度定位器误差% | 激波强度误差% | 接触宽度(格) | 接触位置误差(格) | L1(ρ) |",
         mode="table", resolution="resolved_in_source",
         note="含密度定位器伪影列（rusanov P2 N=100 行 132.811%/132.646%）。"),
    dict(asset_id="A15", asset_class="table", label="F4 TVB 放宽（M=50）对照表（12 行）",
         anchor="| 通量 | 阶 | N | 激波位置误差% | 激波强度误差% | 接触宽度(格) | L1(ρ) |", mode="table",
         resolution="resolved_in_source", note="限制器阈值放宽前后对照；$M$ 量纲为 dx^2（见 A22-3）。"),
    dict(asset_id="A16", asset_class="table", label="F5 等温 Sod 三方互裁表（LBM/DG P1/DG P2 × t=100/200/400）",
         anchor="| 求解器 | t | 激波位置 | 位置误差% | 激波厚度(格) | 平台密度 ρ* | L2/跳跃 |", mode="table",
         resolution="resolved_in_source", note="DG ⇄ LBM ⇄ 解析的三方互裁数字表。"),
    dict(asset_id="A17", asset_class="numeric_anchor", label="等温解析参考锚点（ρ*=0.4966, u*=0.4041, W=0.8137）",
         anchor="解析参考（等温）", mode="para",
         resolution="resolved_in_source", note="解析基准值；报告未给外部文献地址（自算解析解）。"),
    dict(asset_id="A18", asset_class="table", label="F6 方波 TV/过冲表（limited/unlimited × P1/P2 × N=64–256 × 周期 1/4，24 行）",
         anchor="| 限制器 | 阶 | N | 周期 | TV 比 | 过冲% | 欠冲% | L1 |", mode="table",
         resolution="resolved_in_source", note="TVD 账本原始行；过冲门 =0。"),
    dict(asset_id="A19", asset_class="table", label="F6 单模态耗散/色散表（幅值比 + 相位误差 + L2，12 行）",
         anchor="| 限制器 | 阶 | N | 幅值比 | 相位误差(rad) | L2 |", mode="table",
         resolution="resolved_in_source", note="耗散=幅值比、色散=相位误差的标量量化面。"),
    dict(asset_id="A20", asset_class="table", label="F7 守恒性表（质量/动量/能量漂移 + θ_min，4 行）",
         anchor="| 通量 | 阶 | N | 质量漂移 | 动量漂移(÷∫ρ) | 能量漂移 | θ_min |", mode="table",
         resolution="resolved_in_source", note="守恒账本；θ_min=0.928（rusanov P1）为限制器激活证据。"),
    dict(asset_id="A21", asset_class="numeric_anchor", label="旋转锥一周期质量漂移最大值 2.81e-13",
         anchor="旋转锥（二维、一周期）质量漂移最大值", mode="para",
         resolution="resolved_in_source", note="与 A09 锥 C0 P2 N=64 行同值，可交叉核对。"),
    dict(asset_id="A22", asset_class="figure_section", label="§4 结果图（markdown 侧正文为空）",
         anchor="## 4. 结果图", mode="section", resolution="declared_absent",
         note="markdown 该节无图件/无占位；图件实际存在于平台记录 figures 字段（6 张，见 source.platform_figures），"
              "故图件本体在本工作树内不可解析，只登记该节缺内容这一事实。"),
    dict(asset_id="A23", asset_class="limitation_set", label="注意点 8 条（含周期激波管污染、定位器陷阱、kink 基准构造）",
         anchor="## 5. 注意点（踩过的坑 / 局限 / 适用范围）", mode="section",
         resolution="resolved_in_source", note="八条踩坑/局限原文；第 7 条给出适用范围边界。"),
    dict(asset_id="A24", asset_class="table", label="§6 误差判定表（关键量 vs 基准 vs 阈值，12 行）",
         anchor="| 量 | 实测 | 基准 | 阈值 | 判定 |", mode="table",
         resolution="resolved_in_source", note="含 6 项 honest FAIL 与 6 项 PASS 的自报判定。"),
    dict(asset_id="A25", asset_class="statement", label="质量守恒结论文本（Euler 周期 1.13e-13 / 能量 1.08e-13 / 旋转锥 2.81e-13 vs 门 1e-10）",
         anchor="**质量守恒**：Euler 周期最差质量漂移", mode="para",
         resolution="resolved_in_source", note="正文复述 A20/A21 的数字，量级判读为浮点舍入。"),
    dict(asset_id="A26", asset_class="unevaluated_claims", label="「关键量是否 <3%」逐项回答（3 条）",
         anchor="**“关键量是否 <3%？”逐项回答**", mode="block", n=3,
         resolution="resolved_in_source", note="含 kink 上界“否，且不可能”的否证性论述；属报告自述，本工序不判真伪。"),
    dict(asset_id="A27", asset_class="verdict_summary", label="判决汇总（8/14 通过 + 6 项 honest FAIL 列表）",
         anchor="**判决汇总**", mode="para",
         resolution="resolved_in_source", note="FAIL 项名称清单；本工序只登记，不把任何项标成 verified。"),
    dict(asset_id="A28", asset_class="repro_block", label="复现命令（5 条，代码围栏内正文 + 19 项测试）",
         anchor="PYTHONPATH=src python -m pytest tests/test_dg_frontier_in65.py -q", mode="block", n=4,
         resolution="resolved_in_source",
         note="定位到 bash 代码围栏内的 5 条命令（不含围栏符，避免引文里携带三反引号）；"
              "执行体在 TensorLBM 仓，本工作树不可运行。"),
    dict(asset_id="A29", asset_class="external_module", label="源模块 src/tensorlbm/dg_verification/{hllc.py,frontier.py}",
         anchor="**节点** IN65-N04", mode="para", resolution="referenced_unresolved",
         note="属 TensorLBM 仓；本工作树（TensorKnowledge）内不存在，无 URL/commit 可解析。"),
    dict(asset_id="A30", asset_class="external_test", label="回归测试 test_periodic_tube_is_contaminated_reproduction（周期管污染钉死）",
         anchor="test_periodic_tube_is_contaminated_reproduction", mode="block", n=0,
         resolution="referenced_unresolved",
         note="属 TensorLBM 仓 tests/；本工作树不存在。整条注意点原文（A23）亦在此行内。"),
    dict(asset_id="A31", asset_class="external_script_set", label="出图脚本 scripts/plot_dg_frontier_in65.py（→ artifacts/IN65_N04/figures）",
         anchor="PYTHONPATH=src python scripts/plot_dg_frontier_in65.py", mode="block", n=0,
         resolution="referenced_unresolved", note="TensorLBM 仓 scripts/；本工作树内不存在。"),
    dict(asset_id="A32", asset_class="external_artifact", label="判决产物 VERDICT.json（scripts/verdict_dg_frontier_in65.py 产出）",
         anchor="PYTHONPATH=src python scripts/verdict_dg_frontier_in65.py", mode="block", n=0,
         resolution="referenced_unresolved",
         note="TensorLBM 仓 scripts/ 与 VERDICT.json；本工作树内不存在。"),
    dict(asset_id="A33", asset_class="compute_provenance", label="算力出处：集群 n315/n330 loong64 9 分片",
         anchor="**流程**：① 参数化基准", mode="para", resolution="referenced_unresolved",
         note="仅给节点名与分片数，无作业号/日志地址，平台侧无法解析。"),
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


def heading_level(ln: str) -> int:
    n = 0
    while n < len(ln) and ln[n] == "#":
        n += 1
    return n if n and (n >= len(ln) or ln[n] == " ") else 0


def resolve_span(md: str, lines, anchor: str, mode: str, n: int = 0):
    if mode == "document":
        return 0, len(lines) - 1
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit("anchor not unique/found (%d hits): %r" % (len(hits), anchor))
    a = hits[0]
    if mode == "block":
        b = a + n
    elif mode == "para":
        b = a
        while b + 1 < len(lines) and lines[b + 1].strip() and not heading_level(lines[b + 1]):
            b += 1
    elif mode == "table":
        b = a
        while b + 1 < len(lines) and lines[b + 1].startswith("|"):
            b += 1
        if b == a:
            raise SystemExit("anchor is not a table header: %r" % anchor)
    elif mode == "section":
        lvl = heading_level(lines[a])
        b = a
        j = a + 1
        while j < len(lines):
            hl = heading_level(lines[j])
            if hl and hl <= lvl:
                break
            b = j
            j += 1
    else:
        raise SystemExit("unknown mode " + mode)
    return a, min(b, len(lines) - 1)


def build_locator(md: str, lines, offs, spec):
    a, b = resolve_span(md, lines, spec["anchor"], spec["mode"], spec.get("n", 0))
    if spec["mode"] == "document":
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1, quote=md, unique=True)
    sc = offs[a]
    ec = offs[b] + len(lines[b])
    quote = md[sc:ec]
    if not quote.strip():
        raise SystemExit("empty quote for %s" % spec["asset_id"])
    unique = md.count(quote) == 1
    return dict(method="char_span", start_char=sc, end_char=ec, start_line=a, end_line=b,
                quote=quote, unique=unique)


def worktree_paths(md: str):
    import re
    return sorted(set(re.findall(r"(?:scripts|src|tests)/[A-Za-z0-9_./{},]+", md)))


def resolution_check(spec, loc, worktree: pathlib.Path, payload):
    """Every check must be an operation that can be re-run; no assertions from memory."""
    if spec["resolution"] == "declared_absent":
        figs = payload.get("figures") or []
        return dict(check="markdown_section_body_has_content", result="absent",
                    section_lines=loc["end_line"] - loc["start_line"] + 1,
                    body_chars=(len(loc["quote"].strip().split("\n", 1)[1])
                                if "\n" in loc["quote"].strip() else 0),
                    platform_figures_count=len(figs),
                    platform_figure_names=[f.get("name") for f in figs],
                    detail="§4 标题在 markdown 中无正文；图件仅在平台 figures 元数据字段中（本工序不下载图件字节）")
    if spec["resolution"] == "referenced_unresolved":
        # only文字引用 → check whether the referenced path resolves inside this worktree
        import re
        cands = re.findall(r"(?:scripts|src|tests)/[A-Za-z0-9_/.\-]+\.py", spec.get("_ref") or loc["quote"])
        found = [c for c in cands if (worktree / c).exists()]
        return dict(check="referenced_path_exists_in_worktree", result="unresolved" if not found else "present",
                    referenced_candidates=cands, found_in_worktree=found,
                    detail="报告指向 TensorLBM 仓的代码/产物路径；本工作树为 TensorKnowledge，解析不到（不联网猜地址）")
    # resolved_in_source
    return dict(check="char_span_re_slice_and_uniqueness", result="resolved",
                unique=loc["unique"], quote_chars=len(loc["quote"]),
                detail="在冻结 markdown 副本上按 [start_char,end_char) 重新切片与原文逐字相等，且全串唯一")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / ("report_%s.json" % REPORT_ID)).read_text())
    md = (RUN_DIR / ("report_%s.md" % REPORT_ID)).read_text()

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print("FATAL: markdown sha256 %s != contract source_hash %s" % (md_hash, EXPECTED_HASH))
        return 2
    if str(payload.get("id")) != REPORT_ID:
        print("FATAL: API payload id %r != %s" % (payload.get("id"), REPORT_ID))
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen_ids, seen_quotes = [], set(), {}
    for spec in ASSETS:
        if spec["asset_id"] in seen_ids:
            raise SystemExit("duplicate asset_id " + spec["asset_id"])
        seen_ids.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec)
        if not loc["unique"]:
            raise SystemExit("quote not unique for " + spec["asset_id"])
        if loc["method"] == "char_span":
            if loc["quote"] in seen_quotes:
                # two assets may legitimately read the SAME source line (e.g. one line declares both
                # the repo module paths and the machine gate). The sharing is recorded, not hidden.
                loc["shared_span_with"] = seen_quotes[loc["quote"]]
            else:
                seen_quotes[loc["quote"]] = spec["asset_id"]
        head = "(document)"
        for ln in lines[: loc["start_line"] + 1]:
            if heading_level(ln) and heading_level(ln) <= 3:
                head = ln.strip()
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=head or "(document)",
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=resolution_check({**spec, "_ref": spec.get("anchor")}, loc, worktree, payload),
            note=spec["note"],
        ))

    classes, res = {}, {}
    for a in assets:
        classes[a["asset_class"]] = classes.get(a["asset_class"], 0) + 1
        res[a["resolution"]] = res.get(a["resolution"], 0) + 1

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
            platform_figures=[dict(name=f.get("name"), caption=f.get("caption")) for f in (payload.get("figures") or [])],
            platform_tags=payload.get("tags", []),
            retrieved_via="GET %s/tensor/reports/%s" % (
                os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"), REPORT_ID),
            local_copy=str(RUN_DIR / ("report_%s.md" % REPORT_ID)),
            fetch_script="scripts/kf_fetch_9840.py",
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("工作包契约 objective.classify_report_type=false、notes 允许 claims 空数组："
                     "本工序只登记资产定位，不做 claim 抽取，也不把任何结论标成 verified。"),
        integrity=dict(
            quote_uniqueness="每条 char_span 引文在冻结 markdown 中出现的次数必须为 1（构建期强制，verify 期重算）",
            quotes_sliced_not_retyped=True,
            document_registration="整篇 markdown 由 source.hash（sha256 over exact bytes）登记，"
                                  "不重复登记为 document 级资产：全文引文会把源报告自己的代码围栏带进结果信封，"
                                  "使报告里唯一的 json 代码块对围栏解析器产生歧义。",
            hash_recomputed_locally=True,
            hash_matches_contract=True,
        ),
    )

    art = ART_DIR / "asset_manifest.json"
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art.write_text(blob)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != art_hash:
        print("FATAL: durable mirror differs from artifact")
        return 3

    outputs_manifest = dict(artifact_path=str(art), artifact_sha256=art_hash,
                            artifact_bytes=art.stat().st_size)
    outputs_manifest.update({k: v for k, v in manifest.items()})

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
            local_copy=manifest["source"]["local_copy"],
            generator="scripts/kf_register_9840.py",
            verifier="scripts/kf_verify_9840.py",
            verification_status="not_verified",  # verification is computed by the platform gate
            repro_cmd=("python3 scripts/kf_fetch_9840.py && python3 scripts/kf_register_9840.py && "
                       "python3 scripts/kf_verify_9840.py && python3 scripts/kf_9840_negative_control.py && "
                       "python3 scripts/kf_figures_9840.py"),
        ),
        outputs={"asset_manifest.json": outputs_manifest},
        claims=[],
    )

    res_path = RUN_DIR / ("kf_result.%s.json" % PACKAGE_ID)
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / ("kf_result_block.%s.json" % PACKAGE_ID)).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("assets:", len(assets), "by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", res_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())