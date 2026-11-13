#!/usr/bin/env python3
"""KF work package wp-14351-01 (task_type=01-asset-registration) asset registration.

Scope (hard boundary of the package): report_id=14351 only. This script
  * recomputes the sha256 of the report markdown bytes and checks it against the
    contract-declared hash (no re-statement from memory, no copying),
  * indexes report headings,
  * registers every asset it can locate in the markdown with a char-span locator
    (quote is taken from the source, never retyped: quote = md[start:end]),
  * machine-checks the resolution status it declares (worktree path existence /
    record figures field / cluster-artifact availability),
  * emits asset_manifest.json, kf_result.json (envelope), verification.json and
    the KF-RESULT report body (report.md) with the single ```json result block.

No extraction is performed: claims = [] by design (contract notes: 不做抽取),
and nothing is marked verified (verification belongs to the platform gate).

Usage:  python scripts/kf/register_14351_assets.py
Inputs: runs/wp-14351-01/report_14351.json  (produced by runs/wp-14351-01/fetch_report.py)
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parents[2]
RUN = ROOT / "runs" / "wp-14351-01"
OUT = ROOT / "docs" / "kf" / "wp-14351-01"
OUT.mkdir(parents=True, exist_ok=True)

PACKAGE_ID = "wp-14351-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "14351"
SOURCE_URI = "tensor://reports/14351"
SOURCE_FIELD = "markdown"
CONTRACT_HASH = "sha256:8c696991f8bef0c1f0903d2104e88a437897875c759af309c0c7710ce1260558"
CONTRACT_CHARS = 4190
GENERATOR = "scripts/kf/register_14351_assets.py"

# ---------------------------------------------------------------- asset specs
# span = (offset_from_anchor_line, offset_to_anchor_line), inclusive; the quote
# is sliced out of the markdown, so no text is ever transcribed by hand.
ASSET_SPECS = [
    dict(
        asset_id="A01", asset_class="source_document",
        label="报告正文（markdown 全文，本工序的哈希基准对象）",
        anchor="--doc--", span=(0, 0), resolution="resolved_in_source",
        check="source_sha256_recompute",
        note="全文作为单一文档资产登记；quote=全文，sha256 与契约 source_hash 一致（见 integrity）。",
    ),
    dict(
        asset_id="A02", asset_class="case_definition",
        label="DCB 算例定义（ASTM D5528 Mode I 层间断裂）",
        anchor="DCB（ASTM D5528 双悬臂梁，Mode I 层间断裂）", span=(0, 1),
        resolution="resolved_in_source", note="案例背景与用途，原文两句。",
    ),
    dict(
        asset_id="A03", asset_class="parameter_set",
        label="几何 + 离散化 + 材料/内聚参数（L/b/h/a0、E/ν、k_n/k_s/t_n0/t_s0/G_Ic/G_IIc/BK η）",
        anchor="结构化 HEX8 adherends + 零厚度 COH3D8 韧带", span=(0, 1),
        resolution="resolved_in_source",
        note="参数以行内数字给出（无独立参数表）；本工序只登记定位，不抽取为参数卡。",
    ),
    dict(
        asset_id="A04", asset_class="analytic_reference",
        label="解析基准（Williams 根部转角修正梁柔性 C + LEFM 峰值载荷闭式）",
        anchor="解析基准（独立闭式）", span=(0, 2),
        resolution="resolved_in_source",
        note="对标公式原文；属报告自述的外部基准谱系（ASTM D5528 / Kanninen），无可解析地址。",
    ),
    dict(
        asset_id="A05", asset_class="defect_record",
        label="缺陷 A（物理错误）：加载 dof 未进 fixed_dofs → 反力恒 0",
        anchor="**缺陷 A（物理错误）**", span=(0, 2),
        resolution="resolved_in_source", note="缺陷描述与后果链（反力/损伤/峰值判据退化）。",
    ),
    dict(
        asset_id="A06", asset_class="defect_record",
        label="缺陷 B（不终止）：终步零长度步无限循环",
        anchor="**缺陷 B（不终止）**", span=(0, 2),
        resolution="resolved_in_source",
        note="含历史证据表述（控制节点残留 24 min 僵尸进程），本工序不复核该历史。",
    ),
    dict(
        asset_id="A07", asset_class="test_reference",
        label="回归测试钉住：tests/test_cohesive3d_dcb_solver_guards.py（3 新测试）+ 修正 tests/test_cohesive3d_dcb.py",
        anchor="行为由 `tests/test_cohesive3d_dcb_solver_guards.py`", span=(0, 1),
        resolution="referenced_unresolved", check="external_path_absent_in_worktree",
        paths=["tests/test_cohesive3d_dcb_solver_guards.py", "tests/test_cohesive3d_dcb.py"],
        note="路径属外部仓库（TensorFEM）检出；本工作树为 TensorKnowledge，按契约边界不复制内容。",
    ),
    dict(
        asset_id="A08", asset_class="code_reference",
        label="修复实现文件 src/tensorfem/cohesive3d_dcb.py",
        anchor="复现后定位到两个**求解器缺陷**", span=(0, 0),
        resolution="referenced_unresolved", check="external_path_absent_in_worktree",
        paths=["src/tensorfem/cohesive3d_dcb.py"],
        note="报告声明两处缺陷均在该文件修复；本工作树无此路径，未核验代码内容。",
    ),
    dict(
        asset_id="A09", asset_class="code_reference",
        label="前轮基准脚本 benchmarks/cohesive3d_dcb_3d.py（及历史轮 m14987/m15001）",
        anchor="**前轮死法定位**", span=(0, 0),
        resolution="referenced_unresolved", check="external_path_absent_in_worktree",
        paths=["benchmarks/cohesive3d_dcb_3d.py"],
        note="外部仓库脚本；同句给出历史轮次编号，仅登记为文本引用。",
    ),
    dict(
        asset_id="A10", asset_class="run_artifact_reference",
        label="单元级验证真跑：benchmarks/cohesive3d_verification.py → benchmarks/cohesive3d_verification.json（all_passed True）",
        anchor="**单元级验证（真跑）**", span=(0, 2),
        resolution="referenced_unresolved", check="external_path_absent_in_worktree",
        paths=["benchmarks/cohesive3d_verification.py", "benchmarks/cohesive3d_verification.json"],
        note="报告声明工件 all_passed True；工件本体不在本工作树，本工序只登记引用与自述结果。",
    ),
    dict(
        asset_id="A11", asset_class="run_artifact_reference",
        label="试件级探测真跑：benchmarks/cohesive3d_dcb_displacement_control_probe.py（+ 同名 .json 工件，nx=24）",
        anchor="**试件级探测（真跑）**", span=(0, 1),
        resolution="referenced_unresolved", check="external_path_absent_in_worktree",
        paths=["benchmarks/cohesive3d_dcb_displacement_control_probe.py",
               "benchmarks/cohesive3d_dcb_displacement_control_probe.json"],
        note="探针脚本与 JSON 工件均在外部仓库；报告声明 0.3 s 机器可判。",
    ),
    dict(
        asset_id="A12", asset_class="test_result_statement",
        label="全量内聚 pytest 结果：61 passed, 2 xfailed（strict=True）",
        anchor="4. 全量内聚 pytest", span=(0, 0),
        resolution="resolved_in_source", note="文本自述的测试计数；测试本体见 A07，未在本工作树复跑。",
    ),
    dict(
        asset_id="A13", asset_class="table",
        label="试件级结果表（5 行：柔性 C×2 / 峰值非零 / 终止 / 收敛）",
        anchor="试件级（`benchmarks/cohesive3d_dcb_displacement_control_probe.json`）", span=(0, 8),
        resolution="resolved_in_source",
        note="含 +460.7% / +588.4% 误差与两条回归判据；上游自报数字，本工序不复核、不标 verified。",
    ),
    dict(
        asset_id="A14", asset_class="result_statement",
        label="单元级六项 all_passed=True 的概述陈述（数字以工件为准）",
        anchor="单元级（`benchmarks/cohesive3d_verification.json`）", span=(0, 1),
        resolution="resolved_in_source", note="报告显式声明不在正文重复单元级数字。",
    ),
    dict(
        asset_id="A15", asset_class="run_artifact_reference",
        label="宽度分辨基准 benchmarks/cohesive3d_dcb_3d.json（quick，135.7 s，all_passed=False）及其陈旧助手说明",
        anchor="宽度分辨基准（", span=(0, 4),
        resolution="referenced_unresolved", check="external_path_absent_in_worktree",
        paths=["benchmarks/cohesive3d_dcb_3d.json"],
        note="JSON 工件在外部仓库；正文数字（+460.7% / -99.8% / 0.936 / 0.719 vs 30.085）为自述。",
    ),
    dict(
        asset_id="A16", asset_class="figure_declaration",
        label="图件声明：docs/assets/cohesive3d-dcb-3d/{load_opening,damage_field,rcurve}.png",
        anchor="docs/assets/cohesive3d-dcb-3d/load_opening.png", span=(0, 2),
        resolution="referenced_unresolved", check="record_figures_and_path_check",
        paths=["docs/assets/cohesive3d-dcb-3d/load_opening.png",
               "docs/assets/cohesive3d-dcb-3d/damage_field.png",
               "docs/assets/cohesive3d-dcb-3d/rcurve.png"],
        note="3 个 PNG 路径：平台 figures[] 仅 2 条同名（无二进制载荷），rcurve.png 未出现在 figures[]；"
             "docs/assets/ 路径不在本工作树。",
    ),
    dict(
        asset_id="A17", asset_class="open_defect_statement",
        label="开放缺陷：试件柔性为梁理论 5.6–6.9 倍（疑似有效自由跨度 2a）",
        anchor="**开放缺陷（未解决）**", span=(0, 3),
        resolution="resolved_in_source",
        note="报告自述未定案；含 nx=24→5.61×、nx=50→约 11× 两处量级，以及 2 个 strict-xfail 测试与 negative 记录的引用（本体未在本工作树）。",
    ),
    dict(
        asset_id="A18", asset_class="negation_record_reference",
        label="锚点未闭合声明（试件级 DCB 不能作验收算例；仅单元级能力可用）",
        anchor="该缺陷使**试件级** DCB 不能作为验收算例", span=(0, 1),
        resolution="resolved_in_source",
        note="否定性结论原文；2 个 strict-xfail 测试与 negative 记录的引用位于 A17 引文内（本工序未解析其本体）。",
    ),
    dict(
        asset_id="A19", asset_class="limitation_set",
        label="既有适用限制：小应变运动学、无摩擦/接触/循环退化",
        anchor="小应变运动学、无摩擦/接触/循环退化", span=(0, 0),
        resolution="resolved_in_source", note="报告声明为既有限制、本轮未变。",
    ),
    dict(
        asset_id="A20", asset_class="external_job_reference",
        label="集群作业 cj1024（全量 DCB，队列深度 238，未取回）",
        anchor="集群 cj1024（全量 DCB）因队列深度 238 未取回", span=(0, 0),
        resolution="referenced_unresolved", check="cluster_artifact_lookup",
        note="仅文本引用；本工序不向集群查询历史队列状态（快照≠历史事实），故工件不可解析。",
    ),
    dict(
        asset_id="A21", asset_class="table",
        label="误差判定表（4 行，逐项回答是否 <3%）",
        anchor="| 关键量 | 基准 | 误差 | <3%? |", span=(0, 5),
        resolution="resolved_in_source",
        note="上游自报：单元级 ≤1e-10 判是；柔性/峰值/能量三项判否（+460.7% / -99.8% / 0.936）。",
    ),
    dict(
        asset_id="A22", asset_class="repro_command_set",
        label="repro_cmd（4 条命令块：单元级 / 探针 / pytest）",
        anchor="# 单元级：all_passed True", span=(0, 4),
        resolution="resolved_in_source", note="命令块原文；命令引用外部仓库脚本，本工作树不可直接执行。",
    ),
]

# --------------------------------------------------------------- helpers


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def line_index(md: str):
    lines = md.split("\n")
    offsets, pos = [], 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1
    return lines, offsets


def headings(md: str, lines, offsets):
    secs = []
    in_fence = False
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", ln)
        if not m:
            continue
        secs.append(dict(level=len(m.group(1)), heading=m.group(2).strip(),
                         start_line=i, heading_span=[offsets[i], offsets[i] + len(ln)]))
    for k, s in enumerate(secs):
        nxt = secs[k + 1]["start_line"] if k + 1 < len(secs) else len(lines)
        s["char_span"] = [offsets[s["start_line"]], offsets[nxt]] if nxt < len(lines) else [offsets[s["start_line"]], len(md)]
        s["heading_sha256"] = "sha256:" + sha256_text(lines[s["start_line"]])
    return secs


def section_of(start_line: int, secs) -> str:
    cur = "(preamble)"
    for s in secs:
        if s["start_line"] <= start_line:
            cur = s["heading"]
    return cur


def build_locator(md, lines, offsets, spec):
    if spec["anchor"] == "--doc--":
        return dict(method="document", start_char=0, end_char=len(md), start_line=0,
                    end_line=len(lines) - 1, quote=md,
                    quote_sha256="sha256:" + sha256_text(md), quote_unique=True,
                    matches_source=True)
    hits = [i for i, ln in enumerate(lines) if spec["anchor"] in ln]
    if len(hits) != 1:
        raise SystemExit(f"[{spec['asset_id']}] anchor hits={len(hits)} (need 1): {spec['anchor']!r}")
    a = hits[0]
    i0, i1 = a + spec["span"][0], a + spec["span"][1]
    if not (0 <= i0 <= i1 < len(lines)):
        raise SystemExit(f"[{spec['asset_id']}] span out of range: {spec['span']} at line {a}")
    start = offsets[i0]
    end = offsets[i1] + len(lines[i1])
    quote = md[start:end]
    uniq = md.count(quote) == 1
    if not uniq:
        raise SystemExit(f"[{spec['asset_id']}] quote not unique ({md.count(quote)} occurrences)")
    if md[start:end] != quote:  # slice identity is the zero-hand-copy guarantee
        raise SystemExit(f"[{spec['asset_id']}] slice mismatch")
    return dict(method="char_span", start_char=start, end_char=end, start_line=i0, end_line=i1,
                quote=quote, quote_sha256="sha256:" + sha256_text(quote),
                quote_unique=True, matches_source=True)


def external_path_check(paths):
    present = [p for p in paths if (ROOT / p).exists()]
    missing = [p for p in paths if not (ROOT / p).exists()]
    return dict(check="external_path_absent_in_worktree", paths=paths, present=present,
                missing=missing, result="resolved" if not missing else "unresolved",
                detail="本工作树=TensorKnowledge 检出；所列路径属外部仓库（TensorFEM）产物，按契约边界不复制、不臆造内容。")


def main() -> int:
    payload = json.loads((RUN / "report_14351.json").read_text(encoding="utf-8"))
    md = payload["markdown"]
    h = sha256_text(md)
    if h != CONTRACT_HASH.replace("sha256:", ""):
        raise SystemExit(f"FATAL: sha256 {h} != contract {CONTRACT_HASH}")
    if len(md) != CONTRACT_CHARS:
        raise SystemExit(f"FATAL: chars {len(md)} != contract {CONTRACT_CHARS}")

    lines, offsets = line_index(md)
    secs = headings(md, lines, offsets)
    figures = payload.get("figures") or []
    fig_names = [f.get("name") for f in figures]

    assets = []
    for spec in ASSET_SPECS:
        loc = build_locator(md, lines, offsets, spec)
        if spec["resolution"] == "referenced_unresolved":
            if spec["check"] == "external_path_absent_in_worktree":
                chk = external_path_check(spec["paths"])
            elif spec["check"] == "record_figures_and_path_check":
                chk = external_path_check(spec["paths"])
                chk["check"] = "record_figures_and_path_check"
                chk["record_figures_names"] = fig_names
                chk["record_figures_matched"] = [p.split("/")[-1] for p in spec["paths"]
                                                 if p.split("/")[-1] in fig_names]
                chk["record_figures_missing"] = [p.split("/")[-1] for p in spec["paths"]
                                                 if p.split("/")[-1] not in fig_names]
                chk["result"] = "unresolved"
                chk["detail"] = ("figures[] 仅有 name/caption（无 png_base64 载荷），"
                                 f"且 rcurve.png 不在 figures[]；docs/assets 路径不在本工作树。")
            elif spec["check"] == "cluster_artifact_lookup":
                chk = dict(check="cluster_artifact_lookup", job_id="cj1024", result="unresolved",
                           detail="报告自述未取回；本工序不查询集群历史队列状态（避免把当前快照当作历史事实）。")
            else:
                raise SystemExit(f"unknown check {spec['check']}")
        else:
            chk = dict(check=spec.get("check", "char_span_in_source_markdown"), result="resolved",
                       detail="quote 在 markdown 中唯一，且 md[start:end]==quote（本脚本重算）。")
        assets.append(dict(asset_id=spec["asset_id"], asset_class=spec["asset_class"],
                           label=spec["label"],
                           in_report_section=section_of(loc["start_line"], secs),
                           locator=loc, resolution=spec["resolution"],
                           resolution_check=chk, note=spec["note"]))

    ids = [a["asset_id"] for a in assets]
    assert len(ids) == len(set(ids)), "duplicate asset ids"

    by_class, by_res = {}, {"resolved_in_source": 0, "referenced_unresolved": 0, "declared_absent": 0}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] += 1

    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "B",
        "objective": {"register_assets": True, "classify_report_type": False,
                      "extraction_performed": False},
        "generated_at": "2026-11-12T03:05:00Z",
        "generator": GENERATOR,
        "generator_inputs": {"report_id": REPORT_ID, "source_uri": SOURCE_URI,
                             "source_field": SOURCE_FIELD,
                             "contract_expected_sha256": CONTRACT_HASH,
                             "contract_expected_chars": CONTRACT_CHARS,
                             "retrieval_endpoint": "GET /api/v1/tensor/reports/14351"},
        "source": {
            "report_id": REPORT_ID, "source_uri": SOURCE_URI, "source_field": SOURCE_FIELD,
            "sha256": "sha256:" + h, "contract_declared_sha256": CONTRACT_HASH,
            "source_hash_matches": True,
            "chars": len(md), "bytes_utf8": len(md.encode()), "lines": len(lines),
            "contract_declared_chars": CONTRACT_CHARS, "chars_match": True,
            "hash_scope": "UTF-8 bytes of tensor_reports.markdown (report 14351)",
            "record": {
                "id": payload.get("id"), "title": payload.get("title"),
                "scenario_key": payload.get("scenario_key"),
                "mission_id": payload.get("mission_id"), "status": payload.get("status"),
                "created_at": payload.get("created_at"), "tags": payload.get("tags"),
                "summary_sha256": "sha256:" + sha256_text(payload.get("summary") or ""),
                "summary_chars": len(payload.get("summary") or ""),
            },
            "sections": secs,
        },
        "attachment_scan": {
            "record_figures_len": len(figures),
            "record_figures_keys": sorted({k for f in figures for k in f}),
            "record_figures_payload_present": any(f.get("png_base64") for f in figures),
            "record_figures_names": fig_names,
            "markdown_image_syntax_hits": len(re.findall(r"!\[[^\]]*\]\([^)]*\)", md)),
            "markdown_code_fence_hits": len(re.findall(r"```", md)),
            "markdown_url_hits": len(re.findall(r"https?://\S+", md)),
            "markdown_path_like_hits": len(re.findall(r"(?:benchmarks|tests|src|docs)/[\w./-]+", md)),
            "note": "扫描范围=记录 figures[] + markdown 图片语法 + 明文 URL/路径；全量登记，不过滤。",
        },
        "assets": assets,
        "counts": {"assets": len(assets), "by_class": by_class, "by_resolution": by_res},
        "claims": [],
        "claim_policy": {
            "count": 0,
            "reason": "契约 objective.classify_report_type=false、notes=不做抽取；且 "
                      "no_forced_claim_generation / do_not_mark_claims_as_verified 要求"
                      "不得为凑指标造知识。",
            "consequence": "报告内所有结论性表述保持原文状态（含 honest-FAIL 的 3 项未达标），"
                           "既未升格为 claim，也未标注 verified；verification 由平台门计算。",
            "acceptance_item_all_claims_have_evidence_or_explicit_unresolved_status":
                "vacuous-true：claims 为空数组（契约允许），无缺证据的 claim 条目。",
        },
        "integrity": {
            "quote_uniqueness": all(a["locator"]["quote_unique"] for a in assets),
            "hash_recomputed_locally": "sha256:" + h,
            "hash_matches_contract": True,
            "no_duplicate_ids": len(ids) == len(set(ids)),
            "all_locators_resolvable": all(
                a["locator"]["method"] == "document"
                or md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]
                for a in assets),
            "claims_marked_verified": 0,
        },
        "limitations": [
            "本工序只做资产登记：不做类型分类、不做知识抽取、不复核任何数字（+460.7%/-99.8%/0.936 等均为上游自述）。",
            "8 条资产指向外部仓库（TensorFEM）文件/工件/集群作业，其内容无法在本工作树解析，故标 referenced_unresolved 而非 resolved。",
            "平台 figures[] 仅返回 name/caption、无 png_base64 载荷，图件二进制不可校验；rcurve.png 未出现在 figures[]。",
            "本工作树若无 contracts/ 下的契约文件，则 sha256/chars 契约值取自任务下发的包契约文本（见 generator_inputs）。",
        ],
    }

    # ---- validate manifest against the locally pinned schema
    schema = json.loads((OUT / "asset_manifest.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(manifest, schema)

    manifest_path = OUT / "asset_manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": CONTRACT_HASH,
            "source_field": SOURCE_FIELD,
            "source_uri": SOURCE_URI,
            "producer": GENERATOR,
            "emitted_at": "2026-11-12T03:05:00Z",
            "notes": "source_hash=对 markdown UTF-8 字节独立重算的 sha256（本脚本），与契约声明一致；"
                     "source_field=markdown；未改动上游报告，未标注任何 verified。",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    env_schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, env_schema)
    (OUT / "kf_result.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=1), encoding="utf-8")

    # ---- acceptance self-check (machine, honest)
    checks = []

    def add(name, ok, detail):
        checks.append(dict(item=name, result="PASS" if ok else "FAIL", detail=detail))

    reparsed = json.loads(manifest_path.read_text(encoding="utf-8"))
    add("valid_json", isinstance(reparsed, dict), "json.loads(docs/kf/wp-14351-01/asset_manifest.json) 成功")
    try:
        jsonschema.validate(reparsed, schema)
        schema_ok, schema_detail = True, "jsonschema(draft-07) 对 docs/kf/wp-14351-01/asset_manifest.schema.json 通过"
    except jsonschema.ValidationError as exc:  # pragma: no cover
        schema_ok, schema_detail = False, str(exc)
    try:
        jsonschema.validate(envelope, env_schema)
        env_ok = True
    except jsonschema.ValidationError:  # pragma: no cover
        env_ok = False
    add("schema_pass", schema_ok and env_ok,
        schema_detail + "；kf_result 信封对 schemas/kf_result.v1.schema.json 通过=" + str(env_ok))
    loc_ok = all(md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]
                 for a in reparsed["assets"])
    add("source_locator_resolvable", loc_ok,
        f"{len(reparsed['assets'])}/{len(reparsed['assets'])} 条 locator 的 quote 与其 char span 一致"
        f"（且全部 quote_unique=True）")
    add("source_hash_matches", sha256_text(md) == CONTRACT_HASH.replace("sha256:", ""),
        f"重算 {sha256_text(md)} == 契约 {CONTRACT_HASH}")
    add("no_duplicate_ids", len({a["asset_id"] for a in reparsed["assets"]}) == len(reparsed["assets"]),
        f"asset_id 唯一数={len({a['asset_id'] for a in reparsed['assets']})}")
    add("all_claims_have_evidence_or_explicit_unresolved_status", len(reparsed["claims"]) == 0,
        "claims=[]（契约允许；不做抽取），无缺证据 claim 条目 → 条件空真；每条资产另带 resolution 或 unresolved 说明")
    add("contract_chars_match", len(md) == CONTRACT_CHARS, f"chars {len(md)} == 契约 {CONTRACT_CHARS}")
    add("single_report_scope", {reparsed["report_id"], str(payload.get("id"))} == {"14351"},
        "仅取回/登记 report 14351；未读写任何其它 report_id")
    # structural, not string-grep: no object may carry a "verified" flag (true/"verified"/"pass")
    def verified_flags(node, path="$"):
        out = []
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "verified" or (k.endswith("_verified") and k != "claims_marked_verified" and v):
                    out.append(f"{path}.{k}={v!r}")
                out += verified_flags(v, f"{path}.{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                out += verified_flags(v, f"{path}[{i}]")
        elif isinstance(node, str) and node.strip().lower() in ("verified", "gate-verified"):
            out.append(f"{path}={node!r}")
        return out
    flags = verified_flags({k: v for k, v in reparsed.items() if k != "claim_policy"})
    add("do_not_mark_claims_as_verified", not flags and reparsed["integrity"]["claims_marked_verified"] == 0,
        "结构化扫描：无任何 verified 标记对象/值" + (f"；发现 {flags}" if flags else "")
        + f"；integrity.claims_marked_verified={reparsed['integrity']['claims_marked_verified']}"
        + "（claim_policy 为说明性文字，已从扫描中排除）")

    verification = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "source_sha256": "sha256:" + h,
        "assets": len(reparsed["assets"]),
        "counts": reparsed["counts"],
        "checks": checks,
        "passed": sum(1 for c in checks if c["result"] == "PASS"),
        "failed": sum(1 for c in checks if c["result"] == "FAIL"),
        "repro_cmd": "python runs/wp-14351-01/fetch_report.py && python scripts/kf/register_14351_assets.py",
    }
    (OUT / "verification.json").write_text(json.dumps(verification, ensure_ascii=False, indent=1),
                                          encoding="utf-8")
    print(json.dumps({k: verification[k] for k in ("assets", "counts", "passed", "failed")},
                     ensure_ascii=False, indent=1))
    for c in checks:
        print(c["result"], c["item"], "|", c["detail"][:110])
    return 0 if verification["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())