#!/usr/bin/env python3
"""KF work package wp-11415-01 (task_type=01-asset-registration) generator.

Registers the *source assets* of tensor://reports/11415 (markdown field) WITHOUT
extracting knowledge: every registered asset carries a char-span locator into the
report markdown, and a machine-checkable resolution status.

Boundary: touches report 11415 only; refuses to run if the fetched markdown hash
differs from the work-package contract source_hash.

Outputs (all inside the worktree):
  docs/kf/wp-11415-01/asset_manifest.json        canonical artifact (tracked: artifacts/ is gitignored)
  artifacts/wp-11415-01/asset_manifest.json      byte-identical convenience mirror
  runs/wp-11415-01/kf_result.wp-11415-01.json    KF result envelope (kf_result.v1)

Run:  python3 scripts/kf_register_11415.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

PACKAGE_ID = "wp-11415-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "11415"
SOURCE_URI = "tensor://reports/11415"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "d8bc42883f1fa1d274a3ca4808586d2a8773e9d0f464b554c944f5090b0c8c50"
EXPECTED_CHARS = 7903
EXPECTED_TITLE = "IS Code 2008 §2.3 天气衡准完整链：φ1 查表 + 面积判据验证（m9667 / p176w1-n10）"
EXPECTED_SCENARIO = "ship-performance/stability/weather-criterion-imo-2008"

RUN_DIR = pathlib.Path("runs/wp-11415-01")
ART_DIR = pathlib.Path("docs/kf/wp-11415-01")      # canonical, tracked by git
DOC_DIR = pathlib.Path("artifacts/wp-11415-01")    # gitignored convenience mirror (see .gitignore)

# anchor        : unique substring of exactly one source line
# span          : (first_line_offset, last_line_offset) relative to the anchor line
ASSETS = [
    dict(asset_id="A01", asset_class="source_document", label="报告全文 markdown（本工序的唯一上游）",
         anchor="--doc--", span=(0, 0), resolution="resolved_in_source",
         note="method=document：覆盖全文 0..len(markdown)；sha256 与契约 source_hash 一致"),
    dict(asset_id="A02", asset_class="document_header", label="报告标题（含节点号 m9667 / p176w1-n10）",
         anchor="# IMO IS Code 2008 §2.3 天气衡准完整链", span=(0, 0),
         resolution="resolved_in_source", note="标题与平台 title 字段逐字一致"),
    dict(asset_id="A03", asset_class="external_standard", label="IS Code 2008 (MSC.267(85)) Part A §2.3 天气衡准条款",
         anchor="**规范**：IS Code 2008 (MSC.267(85))", span=(0, 0),
         resolution="referenced_unresolved",
         note="规范标识可按号人工检索，但报告内无 URL/DOI/本地副本，平台侧不可解析"),
    dict(asset_id="A04", asset_class="code_pointer", label="实现模块 backend/services/weather_criterion_iso.py（纯函数）",
         anchor="`backend/services/weather_criterion_iso.py`（纯函数）＋", span=(0, 0),
         resolution="referenced_unresolved",
         note="属 ship-performance-platform 仓的代码路径，本工作树（TensorKnowledge）内不存在"),
    dict(asset_id="A05", asset_class="api_endpoint", label="API 端点 POST /api/v1/weather-criterion-iso/check（backend/api/weather_criterion_iso.py）",
         anchor="`backend/api/weather_criterion_iso.py`（`POST /api/v1/weather-criterion-iso/check`）", span=(0, 0),
         resolution="referenced_unresolved",
         note="仅路由声明；本工序不调用该端点、不复核其响应"),
    dict(asset_id="A06", asset_class="evidence_artifact", label="证据工件 artifacts/weather_criterion_imo_2008_m9667/results.json（表值指纹截断）",
         anchor="**证据工件**：`artifacts/weather_criterion_imo_2008_m9667/results.json`", span=(0, 1),
         resolution="referenced_unresolved",
         note="指纹仅给出前 16 位十六进制 + 省略号，无法与任何完整 sha256 比对；工件本体不在本工作树"),
    dict(asset_id="A07", asset_class="test_pointer", label="规范测试 tests/test_weather_criterion_imo_m9667.py（22 例全绿）",
         anchor="**pytest**：`tests/test_weather_criterion_imo_m9667.py`（22 例全绿）", span=(0, 0),
         resolution="referenced_unresolved",
         note="测试本体在外部仓；本工序只登记声明，不复跑该测试"),
    dict(asset_id="A08", asset_class="table", label="船型参数表（6 船；Δ/GM/A/A-Z 输入 + lw/θ/a/b/b-a 结果）",
         anchor="| 算例 | Δ [t] | GM [m] | A/Δ [m²/t] | lw1 [m] |", span=(0, 7),
         resolution="resolved_in_source", note="表头+分隔+6 数据行共 8 行；数值零手抄改动"),
    dict(asset_id="A09", asset_class="method_description", label="完整链六步（lw / φ1 查表 / GZ / 角度 / 面积 / 判定）",
         anchor="1. **lw**：`wind_heeling_lever(P,A,Z,Δ)`", span=(0, 13),
         resolution="resolved_in_source", note="步骤 1–6 原文；含插值双档与端点钳制口径"),
    dict(asset_id="A10", asset_class="validation_design", label="交叉验证设计 + 结构恒等式 b−a 分解",
         anchor="**交叉验证设计**：被测模块（Simpson+二分）", span=(0, 2),
         resolution="resolved_in_source", note="quad+brentq 独立路径与 θc 相消恒等式的文字声明"),
    dict(asset_id="A11", asset_class="spec_table_set", label="三张规范表 2.3.1-1/2/3 的数字化转录（TABLE_PROVENANCE.verified = False）",
         anchor="**表值转录保真度未复核**", span=(0, 3),
         resolution="declared_absent",
         note="报告自述本环境无规范原件逐格复核 → 规范表数值本体不可得，不登记为已验证资产"),
    dict(asset_id="A12", asset_class="repro_script", label="一键复现脚本 tests/m9667_weather_criterion_verify.py",
         anchor="`python3 tests/m9667_weather_criterion_verify.py` 一键复现", span=(0, 0),
         resolution="referenced_unresolved", note="脚本不在本工作树；跨仓复现需外部检出"),
    dict(asset_id="A13", asset_class="table", label="C1 风倾力臂 vs 手算表（6 行，阈值 <1%）",
         anchor="| 算例 | lw1 手算 [m] | lw1 模块 [m] |", span=(0, 7),
         resolution="resolved_in_source", note="上游自报相对误差 0.00e+00；本工序只登记不复核"),
    dict(asset_id="A14", asset_class="scan_result", label="C2 φ1 插值误差扫描（7056 组表节点中点）",
         anchor="扫描 7056 组**表节点中点**", span=(0, 8),
         resolution="resolved_in_source", note="含 linear/pchip 双档与假绿陷阱的原始误差数字"),
    dict(asset_id="A15", asset_class="verdict_set", label="C3 面积比判据与 3 合规 / 3 不合规分类",
         anchor="### C3 面积比判据与分类（3 合规 / 3 不合规，准确率 100%）", span=(1, 7),
         resolution="resolved_in_source", note="分类准确率 100%、b/a 偏差 3.57e-14 等自报数字"),
    dict(asset_id="A16", asset_class="table", label="C4 负控表（GM 2 → 1e-06，6 行）",
         anchor="| GM [m] | θ1 [°] | b/a | 判定 |", span=(0, 7),
         resolution="resolved_in_source", note="θ1 饱和 16.22° 与 b/a→0.0694 的原文数字"),
    dict(asset_id="A17", asset_class="negative_control", label="C4 负控说明（零风压极限 / GM→0 / 无穿越）",
         anchor="* **零风压**（P=0）", span=(0, 7),
         resolution="resolved_in_source", note="零风压合规分支与非单调性的显式入账"),
    dict(asset_id="A18", asset_class="table", label="C5 与共享内核 GZ 积分自洽表（6 行，阈值 1%）",
         anchor="| 算例 | 模块 GZ 积分 [m·rad] | 内核梯形积分 [m·rad] |", span=(0, 7),
         resolution="resolved_in_source", note="max 相对误差 1.32e-07；曲线/解析式注入口径并列"),
    dict(asset_id="A19", asset_class="test_evidence", label="C6 pytest 计数（22 例，阈值 15）",
         anchor="`tests/test_weather_criterion_imo_m9667.py` 共 **22 例**（阈值 15），", span=(0, 1),
         resolution="resolved_in_source", note="仅计数声明；用例清单与运行日志未随报告给出"),
    dict(asset_id="A20", asset_class="figure", label="fig1_gz_areas.png（GZ+lw2 与 a/b 面积着色）",
         anchor="* **fig1_gz_areas.png**", span=(0, 1),
         resolution="resolved_in_source", note="图件本体经 GET /tensor/reports/11415/figures/<name> 取回并留 sha256（见 resolution_check）"),
    dict(asset_id="A21", asset_class="figure", label="fig2_ratio_verdicts.png（6 船 b/a 条形图）",
         anchor="* **fig2_ratio_verdicts.png**", span=(0, 0),
         resolution="resolved_in_source", note="图件本体经 GET /tensor/reports/11415/figures/<name> 取回并留 sha256（见 resolution_check）"),
    dict(asset_id="A22", asset_class="figure", label="fig3_theta1_phi1_chain.png（φ1 查表链与 θ1(GM)）",
         anchor="* **fig3_theta1_phi1_chain.png**", span=(0, 1),
         resolution="resolved_in_source", note="图件本体经 GET /tensor/reports/11415/figures/<name> 取回并留 sha256（见 resolution_check）"),
    dict(asset_id="A23", asset_class="figure", label="fig4_interp_error.png（C2 插值误差分布）",
         anchor="* **fig4_interp_error.png**", span=(0, 0),
         resolution="resolved_in_source", note="图件本体经 GET /tensor/reports/11415/figures/<name> 取回并留 sha256（见 resolution_check）"),
    dict(asset_id="A24", asset_class="table", label="§6 误差判定表（6 关键量 vs 基准，是否 <3%）",
         anchor="| 关键量 | 基准 | 误差 | 是否 <3% |", span=(0, 7),
         resolution="resolved_in_source", note="逐项“是”；θ1 项附 0.5° 门限与角量级换算"),
    dict(asset_id="A25", asset_class="uncertainty_flag", label="结论 + 规范表转录保真度 WITHHELD 声明",
         anchor="**结论**：C1–C6 六条机器判据全部 PASS", span=(0, 3),
         resolution="resolved_in_source", note="报告自标 WITHHELD；本工序不把该不确定性降级或升级"),
    dict(asset_id="A26", asset_class="deviation_declaration", label="面积口径偏差与理由（方法自主权申报）",
         anchor="> 偏差与理由（方法自主权申报）", span=(0, 4),
         resolution="resolved_in_source", note="风侧分支 a=∫_{−θ1}^{θc} 的口径偏差与并列字段说明"),
    dict(asset_id="A27", asset_class="algorithm_guard", label="几何自检守卫（Cb∈[0.30,1.00]、D>T、Δ 往返为 0）",
         anchor="Cb/L/B/Δ 自检（`ship_geometry`", span=(0, 0),
         resolution="resolved_in_source", note="几何先验证原则在报告内的落点；实现本体在外部仓"),
    dict(asset_id="A28", asset_class="model_formula", label="GZ 生成口径：共享内核 stability_core 壁舷式 GZ = sinφ(GM + ½BM tan²φ)",
         anchor="**船型参数表**（6 条完整船型；GZ 曲线由平台共享内核", span=(0, 1),
         resolution="resolved_in_source", note="曲线来源与解析式；KN 曲线接入为报告自述局限"),
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


def build_locator(md, lines, offs, anchor, span):
    if anchor == "--doc--":
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1, quote=md, unique=True)
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor not unique/found ({len(hits)} hits): {anchor!r}")
    a = hits[0]
    i0, i1 = a + span[0], a + span[1]
    i1 = len(lines) - 1 if i1 < 0 else i1
    start, end = offs[i0], offs[i1] + len(lines[i1])
    quote = md[start:end]
    return dict(method="char_span", start_char=start, end_char=end,
                start_line=i0, end_line=i1, quote=quote, unique=md.count(quote) == 1)


def resolution_check(spec, loc, worktree, payload, md):
    """Machine evidence for the declared resolution (never hand-asserted)."""
    aid = spec["asset_id"]
    q = loc["quote"]
    if aid == "A01":
        return dict(check="sha256_of_markdown_vs_contract", result="resolved",
                    recomputed="sha256:" + sha256_text(md), contract="sha256:" + EXPECTED_HASH,
                    chars=len(md), bytes_utf8=len(md.encode()))
    if aid == "A03":
        found = re.findall(r"(https?://\S+|doi:\S+|10\.\d{4,}/\S+)", q)
        return dict(check="address_extraction", result="resolved" if found else "unresolved",
                    addresses_found=found,
                    detail="仅在报告文本内检索 URL/DOI（不联网、不猜测地址）；规范号本身可由人工检索")
    if aid in ("A04", "A05", "A06", "A07", "A12"):
        paths = {
            "A04": ["backend/services/weather_criterion_iso.py"],
            "A05": ["backend/api/weather_criterion_iso.py"],
            "A06": ["artifacts/weather_criterion_imo_2008_m9667/results.json"],
            "A07": ["tests/test_weather_criterion_imo_m9667.py"],
            "A12": ["tests/m9667_weather_criterion_verify.py"],
        }[aid]
        missing = [p for p in paths if not (worktree / p).exists()]
        chk = dict(check="worktree_path_exists", paths=paths, missing=missing,
                   result="unresolved" if missing else "resolved",
                   detail="路径属 ship-performance-platform 仓；本工作树为 TensorKnowledge，缺文件=不可解析")
        if aid == "A06":
            m = re.search(r"sha256=`([0-9a-f]+)…`", q)
            prefix = m.group(1) if m else ""
            chk.update(fingerprint_prefix=prefix, fingerprint_hex_len=len(prefix),
                       fingerprint_full_sha256=False,
                       detail=chk["detail"] + "；且报告只给截断指纹（16/64 位），无法比对完整 sha256")
        return chk
    if aid in ("A20", "A21", "A22", "A23"):
        name = re.search(r"(fig[0-9]_[A-Za-z0-9_]+\.png)", q).group(1)
        local = RUN_DIR / "figures" / name
        fetched = {}
        fm = RUN_DIR / "figures_manifest.json"
        if fm.exists():
            fetched = {f["name"]: f for f in json.loads(fm.read_text())["figures"]}
        rec = dict(figure_name=name, url=fetched.get(name, {}).get("url"),
                   http_status=fetched.get(name, {}).get("http_status"))
        if not local.exists():
            rec.update(check="platform_figure_binary_fetch", result="unresolved", local_copy=str(local),
                       detail="GET /tensor/reports/11415/figures/<name> 未取回图件本体")
            return rec
        raw = local.read_bytes()
        is_png = raw[:8] == b"\x89PNG\r\n\x1a\n"
        rec.update(check="platform_figure_binary_fetch", result="present" if is_png else "unresolved",
                   png_magic=is_png, png_bytes=len(raw),
                   png_sha256="sha256:" + hashlib.sha256(raw).hexdigest(),
                   local_copy=str(local),
                   caption=str(fetched.get(name, {}).get("caption", ""))[:80])
        return rec
    if aid == "A11":
        flag = "TABLE_PROVENANCE.verified = False" in q
        return dict(check="spec_original_copy_in_source", result="absent",
                    state_flag_found=flag, flag="TABLE_PROVENANCE.verified = False",
                    detail="报告自述无规范原件逐格复核 → 规范表本体不在源内，且无外部可解析地址")
    return dict(check="char_span_in_source_markdown", result="resolved")


def heading_before(lines, idx):
    for ln in reversed(lines[:idx]):
        if ln.startswith("#"):
            return ln.strip()
    return "(preamble)"


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / "report_11415.json").read_text())
    md = (RUN_DIR / "report_11415.md").read_text()
    worktree = pathlib.Path(".").resolve()

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract {EXPECTED_HASH}")
        return 2
    if len(md) != EXPECTED_CHARS:
        print(f"FATAL: chars {len(md)} != contract chars {EXPECTED_CHARS}")
        return 2
    if payload.get("id") != int(REPORT_ID):
        print(f"FATAL: payload id {payload.get('id')} != {REPORT_ID}")
        return 2

    lines, offs = line_offsets(md)
    assets, seen, classes, res = [], set(), {}, {}
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit(f"duplicate asset_id {spec['asset_id']}")
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"])
        if not loc["unique"]:
            raise SystemExit(f"quote not unique for {spec['asset_id']}: {spec['anchor']!r}")
        rcheck = resolution_check(spec, loc, worktree, payload, md)
        res_value = spec["resolution"]
        if spec["asset_class"] == "figure" and rcheck["result"] != "present":
            # declared-in-report but binary unavailable -> cannot be resolved in source
            res_value = "referenced_unresolved"
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=heading_before(lines, loc["start_line"]),
            locator=loc,
            resolution=res_value,
            resolution_check=rcheck,
            note=spec["note"],
        ))
        classes[spec["asset_class"]] = classes.get(spec["asset_class"], 0) + 1
        res[res_value] = res.get(res_value, 0) + 1

    manifest = dict(
        schema="asset_manifest.v1",
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
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_status=payload.get("status"),
            platform_figures=[f.get("name") for f in (payload.get("figures") or [])],
            platform_tags=payload.get("tags") or [],
            retrieved_via="GET %s/tensor/reports/11415 (Bearer TENSOR_AGENT_USER token)" % (
                __import__("os").environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")),
            local_copy=str(RUN_DIR / "report_11415.md"),
            contract_source_hash="sha256:" + EXPECTED_HASH,
            contract_chars=EXPECTED_CHARS,
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("本工作包 objective 仅为 register_assets（classify_report_type=false），"
                     "契约 notes 明确 claims 允许为空数组；本工序不做 claim 抽取、不生成任何结论，"
                     "抽取交下游工作包。空数组=无 claim，而非“claim 无法取证”的省略。"),
        integrity=dict(
            quote_uniqueness="每个 locator.quote 经 md.count(quote)==1 与 char-span 切片等值双检（scripts/kf_verify_11415.py）",
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            no_duplicate_ids=True,
            verification_status="not_verified",
            verification_note="verification 由平台门计算；本工序不自行标 verified",
        ),
    )

    art = ART_DIR / "asset_manifest.json"
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art.write_text(blob)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    if mirror.read_bytes() != art.read_bytes():
        print("FATAL: durable mirror differs from artifact")
        return 3
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()

    # outputs.asset_manifest.json carries the manifest itself (no bookkeeping keys,
    # so it validates strictly against schemas/asset_manifest.v1.wp-11415-01.schema.json);
    # artifact bookkeeping lives in provenance (additionalProperties=true).
    out = manifest
    result = dict(
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
            local_copy=str(RUN_DIR / "report_11415.md"),
            artifact_path=str(art),
            artifact_sha256=art_hash,
            artifact_bytes=art.stat().st_size,
            artifact_durable_mirror=str(mirror),
            generator="scripts/kf_register_11415.py",
            verifier="scripts/kf_verify_11415.py",
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": out},
        claims=[],
    )
    (RUN_DIR / "kf_result.wp-11415-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("chars:", len(md), "assets:", len(assets))
    print("by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    return 0


if __name__ == "__main__":
    sys.exit(main())