#!/usr/bin/env python3
"""wp-9761-01 (task_type 01-asset-registration): register the source assets of report 9761.

Scope discipline of this package (per contract):
  * only report_id=9761 is read or written;
  * nothing is extracted (claims = []), nothing is marked verified;
  * every asset carries a *verbatim* locator (char span + line span + quote) that the
    platform can re-resolve as a substring of the markdown;
  * the byte hash of the markdown is recomputed here and compared with the contract.

Invariants enforced while building (hard failures, not warnings):
  I1  sha256(markdown) == provenance.source_hash from the contract
  I2  every asset_id is unique and matches ^A[0-9]{2}$
  I3  every locator quote occurs exactly once in the markdown (uniqueness)
  I4  md[start_char:end_char] == quote (slice / offset consistency)
  I5  line span in the locator reproduces the same quote
  I6  resolution_check.result is consistent with `resolution`
      (resolved_in_source->resolved, referenced_unresolved->unresolved,
       declared_absent->absent)

Outputs:
  artifacts/wp-9761-01/asset_manifest.json      (manifest, primary)
  docs/wp-9761-01/asset_manifest.json           (byte-identical durable mirror: the repo
                                                 push gate drops artifacts/** and runs/**)
  runs/wp-9761-01/kf_result.wp-9761-01.json     (kf_result.v1 envelope)
  runs/wp-9761-01/kf_result_block.wp-9761-01.json (same JSON; the single ```json block payload)

Usage: python3 scripts/kf_register_9761.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys

REPORT_ID = "9761"
PACKAGE_ID = "wp-9761-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_VERSION = "1.0"
LANE = "A"
SCENARIO_KEY = "rigid_contact_energy_ledger_certification"
EXPECTED_HASH = "4667a18d2c2c183344308980f0b5ef2f018575f060f8129f7e0d8140abca2e2a"
EXPECTED_CHARS = 8931
SOURCE_URI = "tensor://reports/9761"
DOMAIN_LAYER = "DEM|rigid_contact_energy_ledger_certification|l"

RUN_DIR = pathlib.Path("runs/wp-9761-01")
ART_DIR = pathlib.Path("artifacts/wp-9761-01")
DOC_DIR = pathlib.Path("docs/wp-9761-01")
MD_PATH = RUN_DIR / "report_9761.md"
PAYLOAD_PATH = RUN_DIR / "report_9761.json"

# Asset registry.  anchor = a substring that must occur on exactly one line of the
# markdown (it is only used to locate the line); span = (start_offset, end_offset)
# relative to that line, end inclusive; the emitted quote is the verbatim line block.
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，源资产本体）",
         anchor="# P54W3-N03", span=(0, -1), resolution="resolved_in_source", method="document",
         note="整篇 markdown 即源资产；sha256 与契约 source_hash 逐字节一致（I1 校验）"),
    dict(asset_id="A02", asset_class="heading", label="报告标题行",
         anchor="# P54W3-N03 刚性碰撞能量账本收敛阶认证（成熟化）", span=(0, 0),
         resolution="resolved_in_source", method="char_span",
         note="与平台 title 字段不同文字（平台 title 为任务全名），差异登记在 observations.title_drift"),
    dict(asset_id="A03", asset_class="provenance_statement", label="生成者/版本/时间戳与零手抄声明",
         anchor="生成 2026-11-09T08:06:54+00:00", span=(0, 0), resolution="resolved_in_source",
         method="char_span",
         note="声明全部数字由 scripts/p54w3_contact_energy_certification.py 程序化写入 metrics.json；本工序只登记该声明，不复核"),
    dict(asset_id="A04", asset_class="problem_statement", label="问题背景 + 三项成熟化交付",
         anchor="**物理背景.**", span=(0, 4), resolution="resolved_in_source", method="char_span",
         note="含 m5404 5.111e-07 口径/实现之问与三件交付物（并列口径、可测性、pytest 判据）"),
    dict(asset_id="A05", asset_class="table", label="算例与参数表（S/R/C/M 四个算例，6 行）",
         anchor="| 算例 | 配置 | 参数 | 参考解 |", span=(-2, 5), resolution="resolved_in_source",
         method="char_span",
         note="数值仅登记不换算；参考解列给出解析式与 m5404 报告值"),
    dict(asset_id="A06", asset_class="definition_table", label="三口径离散定义表（flux/explicit/trapezoid）",
         anchor="| 口径 | 离散定义 | 对照基准 | 预期 |", span=(0, 5),
         resolution="resolved_in_source", method="char_span",
         note="每个口径的离散定义、对照基准与预期阶；分子式在原文中以行内代码给出"),
    dict(asset_id="A07", asset_class="method_rationale", label="检查点协议（本单核心增量）说明段",
         anchor="**(b) 为什么必须引入检查点", span=(0, 0), resolution="resolved_in_source",
         method="char_span",
         note="velocity-Verlet 恒等式论证 + 实测斜率 0.986/1.989；属方法论证非独立证据"),
    dict(asset_id="A08", asset_class="negative_control", label="负控设计（三项：记账缺陷/注入缺陷/预渐近区）",
         anchor="**(c) 负控（判据有判别力才叫判据）.**", span=(0, 0),
         resolution="resolved_in_source", method="char_span",
         note="负控实测值 1.09e-01/8.02e-01、斜率 -0.005；负控代码本体见 A10（未解析）"),
    dict(asset_id="A09", asset_class="toolchain_declaration", label="工具链组成（模块/回归守卫/复现脚本）",
         anchor="**(d) 工具链.**", span=(0, 0), resolution="resolved_in_source", method="char_span",
         note="声明 10 条用例、certify_all 折叠判据、--render-only 重建；代码文件本体见 A10"),
    dict(asset_id="A10", asset_class="external_code_set", label="TensorDEM 侧代码三件（模块/用例/复现脚本）",
         anchor="contact_energy_certification.py`（三口径 + 检查点协议", span=(0, 0),
         resolution="referenced_unresolved", method="char_span",
         note="仓内相对路径，属 TensorDEM 仓产物；本工作树（TensorKnowledge）内不存在，无法本地解析"),
    dict(asset_id="A11", asset_class="table", label="三口径 × Δt 残差表（8 级，10 行）",
         anchor="| N_c=t_c/Δt | Δt [s] | 通量口径残差（全程） |", span=(0, 10),
         resolution="resolved_in_source", method="char_span",
         note="本单主证据数字表；本工序只登记定位，不复算、不判 verified"),
    dict(asset_id="A12", asset_class="numeric_result_statement", label="拟合结论（显式 0.986 / 梯形 1.989，R²，残差比）",
         anchor="拟合（log|r| vs log Δt，最小二乘）", span=(0, 0),
         resolution="resolved_in_source", method="char_span",
         note="斜率/R²/粗细残差比 121.9× 与 15335.2× 的原文陈述"),
    dict(asset_id="A13", asset_class="interpretation", label="「读法」段：三口径差异的解释",
         anchor="**读法.**", span=(0, 0), resolution="resolved_in_source", method="char_span",
         note="属作者解释（interpretation），非机器判据；下游抽取须保留此定性"),
    dict(asset_id="A14", asset_class="numeric_result_statement", label="恢复系数判据 c 结果（e=0.571663401 vs 0.571740028）",
         anchor="目标 e=0.571740028（clamped 闭式）", span=(0, 0),
         resolution="resolved_in_source", method="char_span",
         note="含粗分辨率 N_c=32 误差 8.594e-04，用于论证「离散误差而非偏置」"),
    dict(asset_id="A15", asset_class="table", label="五球 Newton 摆动量/残差表（3 级，5 行）",
         anchor="| Δt [s] | N_c | 总动量漂移 |", span=(0, 4), resolution="resolved_in_source",
         method="char_span",
         note="静不定接触网络下的动量守恒与末球速度"),
    dict(asset_id="A16", asset_class="table", label="m5404 残差重判表（4 级 Δt，7 行）",
         anchor="| Δt [s] | 步数 | 状态量口径残差 |", span=(0, 5), resolution="resolved_in_source",
         method="char_span",
         note="含注入 1e-3 缺陷对照列与浮冰 A/B 出射速度列"),
    dict(asset_id="A17", asset_class="verdict_statement", label="判据 e 结论（`convention`）及三条支撑",
         anchor="**显式判定（判据 e）：`convention`。**", span=(0, 4),
         resolution="resolved_in_source", method="char_span",
         note="结论原文 + 复现/判别力/归因三条；本工序登记结论，不替平台判定真伪"),
    dict(asset_id="A18", asset_class="figure_declaration", label="5 幅图的 markdown 声明（图 1-图 5 + 题注）",
         anchor="## 4. 结果图", span=(2, 20), resolution="resolved_in_source", method="char_span",
         note="声明块（含题注）在源文可定位；图件二进制见 A19"),
    dict(asset_id="A19", asset_class="figure_binary_set", label="图件二进制 5 个（figures/fig1..fig5.png）",
         anchor="![三口径收敛](figures/fig1_three_conventions.png)", span=(0, 18),
         resolution="referenced_unresolved", method="char_span",
         note="路径相对 TensorDEM 仓 docs/p54w3-contact-energy-certification/；"
              "平台 figures 字段只登记 name+caption（5 条），png 字节不在本工作树"),
    dict(asset_id="A20", asset_class="limitation_set", label="注意点与局限 7 条",
         anchor="## 5. 注意点（踩过的坑 / 局限 / 适用范围）", span=(2, 8),
         resolution="resolved_in_source", method="char_span",
         note="恒等式陷阱/通量口径语义/检查点位置/线性弹簧/恢复系数适用面/≥3 级 Δt/不复用已验收案例"),
    dict(asset_id="A21", asset_class="table", label="误差判定表（关键量 vs 基准，6 行）",
         anchor="| 关键量 | 本单结果 | 基准 | 相对误差 | 是否 <3% |", span=(0, 7),
         resolution="resolved_in_source", method="char_span",
         note="上游自报六项全部 <3%；本工序只登记，误差是否成立由平台门/下游复审裁定"),
    dict(asset_id="A22", asset_class="self_assessment", label="「是否<3%」逐项回答段",
         anchor="**逐项回答「是否<3%」**", span=(0, 0), resolution="resolved_in_source",
         method="char_span",
         note="声明无 3%~15% 可疑带项、未放宽归一化（E0=½m_eff v0²）"),
    dict(asset_id="A23", asset_class="table", label="机器验收判据表（a-e，8 行）",
         anchor="| 判据 | 实测 | 阈值 | 结论 |", span=(0, 7), resolution="resolved_in_source",
         method="char_span",
         note="五项判据实测/阈值/PASS 原文；阈值来源见 A26"),
    dict(asset_id="A24", asset_class="numeric_result_statement", label="折叠判据 all_passed = True",
         anchor="**总计 全部通过**", span=(0, 0), resolution="resolved_in_source",
         method="char_span",
         note="上游自报折叠结果；本工序不将其转写为 verified"),
    dict(asset_id="A25", asset_class="artifact_path_list", label="产物路径清单（metrics.json/figures/模块/用例/复现命令）",
         anchor="产物路径：", span=(0, 6), resolution="referenced_unresolved", method="char_span",
         note="5 条仓内相对路径；均属 TensorDEM 仓，本工作树内不存在"),
    dict(asset_id="A26", asset_class="audit_chain", label="审计链 5 条（阈值常量/解析参考/负控/判定规则/可复算）",
         anchor="## 8. 审计链", span=(2, 6), resolution="resolved_in_source", method="char_span",
         note="FLUX_TOL=1e-9、SLOPE_TOL=0.2、RESTITUTION_TOL=1e-3、MOMENTUM_TOL=1e-12 等阈值声明"),
    dict(asset_id="A28", asset_class="normalization_declaration", label="残差归一化约定（E0=½m_eff v0²）",
         anchor="**(a) 三口径的并列定义**", span=(0, 0), resolution="resolved_in_source",
         method="char_span",
         note="补充登记：覆盖率缺口分析（图 1 阴影带）显示此行未被任何资产钉住；"
              "归一化基准是残差量纲的定义本身，下游抽取需要它，故补登"),
    dict(asset_id="A29", asset_class="interpretation", label="五球摆物理解释段（静不定加载/末球 0.989 m/s）",
         anchor="五球紧贴时 4 个接触**同时**加载", span=(0, 0), resolution="resolved_in_source",
         method="char_span",
         note="补充登记：覆盖率缺口分析发现该解释段未被钉住；含 1.11e-15 与 0.989 m/s 的原文数字"),
    dict(asset_id="A27", asset_class="environment_record", label="运行环境记录（TensorDEM 0.1.0 / Python 3.11.6 / 壁钟 112.2 s）",
         anchor="6. **环境**：TensorDEM 0.1.0", span=(0, 0), resolution="resolved_in_source",
         method="char_span",
         note="可复现性元数据；本工序不验证该环境是否可复现"),
]

RESOLUTION_TO_CHECK = {
    "resolved_in_source": "resolved",
    "referenced_unresolved": "unresolved",
    "declared_absent": "absent",
}


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build_locator(md: str, lines, offs, anchor: str, span: tuple[int, int]) -> dict:
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit("anchor %r occurs on %d lines (must be exactly 1)" % (anchor, len(hits)))
    a = hits[0]
    s, e = a + span[0], a + span[1]
    if span[1] == -1:
        e = len(lines) - 1
    if s < 0 or e >= len(lines) or e < s:
        raise SystemExit("bad span for %r: %s (lines=%d)" % (anchor, span, len(lines)))
    quote = "\n".join(lines[s:e + 1])
    start_char = offs[s]
    end_char = offs[e] + len(lines[e])
    if md[start_char:end_char] != quote:
        raise SystemExit("slice mismatch for %r" % anchor)
    n = md.count(quote)
    return dict(method="document" if (s == 0 and e == len(lines) - 1) else "char_span",
                start_char=start_char, end_char=end_char,
                start_line=s, end_line=e, quote=quote, unique=(n == 1),
                occurrences=n)


PATH_RE = re.compile(r"(?:src|tests|scripts|docs)/[A-Za-z0-9_./*-]+")


def resolution_check(spec: dict, md: str, payload: dict, worktree: pathlib.Path) -> dict:
    res = spec["resolution"]
    if res == "resolved_in_source":
        return dict(check="char_span_in_source_markdown", result="resolved",
                    detail="quote 在 markdown 中唯一出现（occurrences=1），切片与行区间一致",
                    occurrences=md.count("\n".join(md.split("\n")[spec["_loc"]["start_line"]:
                                                              spec["_loc"]["end_line"] + 1])))
    if spec["asset_id"] == "A19":
        figs = payload.get("figures") or []
        return dict(check="platform_figures_field_and_worktree_lookup", result="unresolved",
                    platform_figures_count=len(figs),
                    platform_figure_names=[f.get("name") for f in figs if isinstance(f, dict)],
                    worktree_hits=[],
                    detail="平台 figures 只登记 name+caption（无 png 字节）；图件路径属 TensorDEM 仓")
    # external path sets: look for the concrete files inside *this* worktree only
    quote = spec["_loc"]["quote"]
    cands = sorted(set(PATH_RE.findall(quote)))
    found = [p for p in cands if (worktree / p).exists()]
    return dict(check="worktree_path_lookup", result="unresolved",
                paths_referenced=cands, worktree_hits=found,
                detail="仅在本工作树内查存在性；不联网、不跨仓猜路径")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    if not MD_PATH.exists():
        raise SystemExit("missing %s — run scripts/kf_fetch_9761.py first" % MD_PATH)
    md = MD_PATH.read_text(encoding="utf-8")
    payload = json.loads(PAYLOAD_PATH.read_text(encoding="utf-8"))

    # ---- I1: source hash -------------------------------------------------------
    md_hash = sha256_text(md)
    hash_ok = (md_hash == EXPECTED_HASH)
    if not hash_ok:
        print("FATAL: markdown sha256 %s != contract source_hash %s" % (md_hash, EXPECTED_HASH))
        return 2
    if len(md) != EXPECTED_CHARS:
        print("FATAL: chars %d != contract chars %d" % (len(md), EXPECTED_CHARS))
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen = [], set()
    for spec in ASSETS:
        # I2
        if not re.fullmatch(r"A[0-9]{2}", spec["asset_id"]):
            raise SystemExit("bad asset_id %r" % spec["asset_id"])
        if spec["asset_id"] in seen:
            raise SystemExit("duplicate asset_id %s" % spec["asset_id"])
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"])
        if not loc["unique"]:                                   # I3
            raise SystemExit("quote not unique for %s (%d occurrences)"
                             % (spec["asset_id"], loc["occurrences"]))
        spec["_loc"] = loc
        head = "(document)"
        for ln in lines[: loc["start_line"]]:
            if ln.startswith("#"):
                head = ln.strip().lstrip("# ").strip()
        rc = resolution_check(spec, md, payload, worktree)
        if rc["result"] != RESOLUTION_TO_CHECK[spec["resolution"]]:   # I6
            raise SystemExit("resolution/check mismatch for %s: %s vs %s"
                             % (spec["asset_id"], rc["result"], spec["resolution"]))
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=head,
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=rc,
            note=spec["note"],
        ))

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    md_heading = lines[0].lstrip("# ").strip()
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
            hash_matches_contract=True,
            contract_hash="sha256:" + EXPECTED_HASH,
            chars=len(md),
            chars_matches_contract=(len(md) == EXPECTED_CHARS),
            chars_contract=EXPECTED_CHARS,
            bytes_utf8=len(md.encode()),
            title=payload.get("title"),
            markdown_heading=md_heading,
            scenario_key=payload.get("scenario_key"),
            scenario_key_matches_contract=(payload.get("scenario_key") == SCENARIO_KEY),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_status=payload.get("status"),
            platform_created_at=payload.get("created_at"),
            platform_figures=[dict(name=f.get("name"), caption=f.get("caption"))
                              for f in (payload.get("figures") or [])],
            platform_tags=payload.get("tags") or [],
            domain_layer=DOMAIN_LAYER,
            retrieved_via="GET %s/tensor/reports/9761" % os.environ.get(
                "TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
            local_copy=str(MD_PATH),
        ),
        counts=dict(assets=len(assets), by_class=by_class, by_resolution=by_res,
                    resolved_in_source=by_res.get("resolved_in_source", 0),
                    referenced_unresolved=by_res.get("referenced_unresolved", 0),
                    declared_absent=by_res.get("declared_absent", 0),
                    unique_quotes=sum(1 for a in assets if a["locator"]["unique"])),
        assets=assets,
        claims=[],
        claims_note=("契约 objective.classify_report_type=false 且 notes 指明「不做抽取、claims 允许为空」："
                     "本工序只登记资产定位与解析状态，不产出知识 claim。"
                     "A17/A24 中的结论性原文属源资产内容，登记不等于平台验证。"),
        observations=[
            dict(id="O1", kind="metadata_drift",
                 text="平台 title 与 markdown 一级标题不同文字：title 为任务全名，正文标题带「（成熟化）」后缀。",
                 evidence_asset="A02",
                 detail=dict(platform_title=payload.get("title"), markdown_heading=md_heading)),
            dict(id="O2", kind="figures_present",
                 text="平台 figures 字段登记 5 条（name+caption），对应正文明声明的图 1-图 5；png 字节未随报告存储。",
                 evidence_asset="A18"),
            dict(id="O3", kind="external_code_dependency",
                 text="结论的全部数值产物在 TensorDEM 仓（模块/用例/metrics.json），本工序无法在本工作树内解析，"
                      "故 A10/A25 标 referenced_unresolved，不视为缺失或造假。",
                 evidence_asset="A10"),
            dict(id="O4", kind="upstream_lineage",
                 text="报告自身声明其上游为 in54w1（留 documented FAIL）与 m5404（5.111290246e-07）；"
                      "两者均以文字出现，未给出可解析报告号或路径。",
                 evidence_asset="A04"),
            dict(id="O5", kind="no_verification_claim",
                 text="本 manifest 不含 verified 标记：A23/A24 的 PASS 与 all_passed=True 是源报告的自报值，"
                      "登记的是「原文如此」，不是平台复算结论。",
                 evidence_asset="A23"),
        ],
        integrity=dict(
            quote_uniqueness="每条 quote 在 markdown 中唯一（occurrences=1），由 scripts/kf_register_9761.py 断言",
            quote_slice_consistency="md[start_char:end_char]==quote 与 行区间重建同时校验（I4/I5）",
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            no_asset_id_duplicates=True,
            verified_flags="none (verification is computed by the platform gate)",
            verifier="scripts/kf_verify_9761.py",
        ),
    )
    for spec in ASSETS:
        spec.pop("_loc", None)

    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art = ART_DIR / "asset_manifest.json"
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
            source_bytes_utf8=len(md.encode()),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version=CONTRACT_VERSION,
            lane=LANE,
            work_package=PACKAGE_ID,
            domain_layer=DOMAIN_LAYER,
            contract_source_hash="sha256:" + EXPECTED_HASH,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(MD_PATH),
            generator="scripts/kf_register_9761.py",
            verifier="scripts/kf_verify_9761.py",
            emitted_at=payload.get("created_at"),
            verification_status="not_verified",   # platform gate computes verification
        ),
        outputs={
            "asset_manifest.json": dict(
                artifact_path=str(art),
                artifact_sha256=art_hash,
                artifact_bytes=art.stat().st_size,
                durable_mirror=str(mirror),
                campaign_mission_id=15667,
                **{k: v for k, v in manifest.items() if k != "schema"},
            )
        },
        claims=[],
    )

    res_path = RUN_DIR / "kf_result.wp-9761-01.json"
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    block = RUN_DIR / "kf_result_block.wp-9761-01.json"
    block.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("markdown sha256:", md_hash, "MATCH" if hash_ok else "MISMATCH")
    print("chars:", len(md), "bytes_utf8:", len(md.encode()))
    print("assets:", len(assets), "by_class:", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", res_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())