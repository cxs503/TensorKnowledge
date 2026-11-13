#!/usr/bin/env python3
"""Work package wp-13980-01 (task_type 01-asset-registration) for report 13980.

Scope per contract: register the source assets only.  No claim extraction, no
classification, nothing marked verified.

Design rules enforced here (same discipline as scripts/kf_register_448.py):
  * Zero hand transcription.  Every emitted ``quote`` is sliced out of the report
    markdown at run time between programmatic line anchors; each quote is re-checked
    to be a *unique* substring of the markdown before anything is written, and each
    locator's (start_char,end_char) is re-sliced to confirm it reproduces the quote.
  * Hash gate first: the markdown sha256 must equal the contract source_hash
    (sha256:2e506d3c8285306a34dd397de133f8c48f6f02a604629adbc0c79eb81ce83ce6),
    otherwise the script refuses to write anything.
  * Unresolvable references are declared as ``referenced_unresolved`` /
    ``declared_absent`` with a machine check attached -- never silently dropped and
    never given an invented path/address.
  * ``claims`` stays empty: the contract sets objective.register_assets=true,
    objective.classify_report_type=false and notes explicititly allow an empty array.

Inputs : artifacts/wp-13980-01/source_markdown.md + source_meta.json
         (written by scripts/kf_fetch_13980.py from GET $TENSOR_API_BASE/tensor/reports/13980)
Outputs: artifacts/wp-13980-01/asset_manifest.json
         artifacts/wp-13980-01/resolution_checks.json
         runs/wp-13980-01/asset_manifest.json, kf_result.wp-13980-01.json
         runs/wp-13980-01/kf_result_block.wp-13980-01.json  (the single ```json block)
         docs/kf/wp-13980-01/asset_manifest.json             (durable mirror; push gate
                                                              drops artifacts/** and runs/**)

Usage: python3 scripts/kf_register_13980.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

REPORT_ID = "13980"
PACKAGE_ID = "wp-13980-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/13980"
EXPECTED_HASH = "2e506d3c8285306a34dd397de133f8c48f6f02a604629adbc0c79eb81ce83ce6"
EXPECTED_CHARS = 8267

ART_DIR = pathlib.Path("artifacts/wp-13980-01")
RUN_DIR = pathlib.Path("runs/wp-13980-01")
DOC_DIR = pathlib.Path("docs/kf/wp-13980-01")
SHIP_API = "http://127.0.0.1:8002/openapi.json"  # the API the report swept

# asset_id, asset_class, label, anchor substring (unique in markdown), 0-based
# line span relative to the anchor line, declared resolution, note.
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，源资产本体）",
         anchor="--doc--", span=(0, -1), resolution="resolved_in_source",
         note="整篇 markdown 即源资产；字节 sha256/字符数见 source 块，由 scripts/kf_verify_13980.py 重算"),
    dict(asset_id="A02", asset_class="case_parameter_set",
         label="参考船与工况规模声明（Baltic 1A 145 m 主尺度 + 排水体积 + 40 工况逐条落工件）",
         anchor="参考船=Baltic 1A 145 m", span=(0, 2), resolution="resolved_in_source",
         note="仅登记原文数值，不做换算/校验（几何 Cb/L/B 校验属船舶平台闸门，不在本工序）"),
    dict(asset_id="A03", asset_class="coverage_matrix",
         label="8 族 × 5 工况覆盖矩阵（端点路径 / 真跑数 / 基准通过数 / 状态）",
         anchor="| F1_ice_resistance | 冰阻力 |", span=(0, 7), resolution="resolved_in_source",
         note="表内 7 个 `...` 端点路径由本脚本正则抽出并逐个对照运行中 openapi 校验（见 resolution_checks）"),
    dict(asset_id="A04", asset_class="pipeline_script_ref",
         label="扫描流水线脚本引用（run_sweep.py / cross_method.py / make_tables.py）",
         anchor="`runs/ice_8x5/run_sweep.py`", span=(0, 1), resolution="referenced_unresolved",
         note="脚本本体位于产出仓（船舶总体性能平台），不在 TensorKnowledge 工作树内；本工序不跨仓取件"),
    dict(asset_id="A05", asset_class="test_program_ref",
         label="机器校验测试引用（pytest tests/test_ice_8x5_sweep.py，7 项）",
         anchor="pytest tests/test_ice_8x5_sweep.py", span=(0, 0), resolution="referenced_unresolved",
         note="测试文件不在本工作树；登记其被引用事实，不宣称已复跑"),
    dict(asset_id="A06", asset_class="benchmark_anchor_ref",
         label="外部基准锚集（Lindqvist 1989 / Riska 1997 / MT Uikku / IMO MSC.137(76) / MSC.1/Circ.1519 / IS Code 2008 6.35 mm/h / MEPC.353(78)）",
         anchor="基准锚：Lindqvist 1989", span=(0, 1), resolution="referenced_unresolved",
         note="报告只给文献名与条款号，未给 URL/DOI；按约束不联网猜地址，故登记为未解析"),
    dict(asset_id="A07", asset_class="results_table",
         label="逐工况核心量表（F1–F8 共 40 行）",
         anchor="| F1 冰阻力 | h=0.3 m |", span=(0, 39), resolution="resolved_in_source",
         note="核心量原文保留（含 F3 五条 NOT_SUPPORTED 状态行），不抽取、不改写"),
    dict(asset_id="A08", asset_class="benchmark_table",
         label="基准对照 CSV 节选（family,quantity,ref,got,error,threshold,pass,anchor）",
         anchor="family,quantity,ref,got,error,threshold,pass,anchor", span=(0, 19),
         resolution="resolved_in_source",
         note="报告声明全表 54 项已评分，此处为节选；完整 54 行未在 markdown 内出现，缺量如实登记"),
    dict(asset_id="A09", asset_class="data_file_ref",
         label="benchmarks.csv 完整基准表引用（54 项已评分）",
         anchor="全表见 benchmarks.csv", span=(0, 0), resolution="referenced_unresolved",
         note="文件本体不在工作树内；报告只给出相对文件名，未给出绝对路径"),
    dict(asset_id="A10", asset_class="figure_section",
         label="结果图章节声明（8 幅，含族-图对应关系）",
         anchor="## ④ 结果图", span=(0, 1), resolution="resolved_in_source",
         note="章节文本声明 8 幅存在；png 本体登记为 A11（平台 figures 字段）"),
    dict(asset_id="A11", asset_class="figure_asset",
         label="8 幅结果图 png（fig1_ice_resistance … fig8_coverage）",
         anchor="## ④ 结果图", span=(0, 1), resolution="resolved_in_source",
         note="分辨率=平台 figures 字段携带 8 个具名 png；本工作树内无二进制副本，不伪造本地地址"),
    dict(asset_id="A12", asset_class="limitations_section",
         label="注意点与局限（模型形式不确定度 / F3 GAP / F2 可达域 / F7 待查 / 包络越限）",
         anchor="## ⑤ 注意点与局限", span=(0, 7), resolution="resolved_in_source",
         note="保留不确定度原话，包括『公式级 15% 精度不可宣称』这类否定性声明"),
    dict(asset_id="A13", asset_class="error_table",
         label="误差判定表（关键量 vs 基准，逐项 + 是否 <3%）",
         anchor="| 关键量 | 基准 | 误差 | 是否 <3% |", span=(0, 10), resolution="resolved_in_source",
         note="表内『否』项按原文保留，不做粉饰；误差判定结论归平台门，本工序不重算"),
    dict(asset_id="A14", asset_class="absent_capability",
         label="F3 冰区系泊缺失声明（openapi 全扫 + backend grep 均无模型 → 5 工况 NOT_SUPPORTED）",
         anchor="| F3_ice_mooring | 冰区系泊(冰漂移/系泊载荷) |", span=(0, 0),
         resolution="declared_absent",
         note="机检：对运行中 openapi 做 ice∧mooring 关键词扫描，命中 0 条即与报告声明一致"),
    dict(asset_id="A16", asset_class="raw_run_artifact_ref",
         label="40 工况原始工件族声明（每工况的请求/响应/sha256/耗时逐条落工件）",
         anchor="全部 40 工况的请求", span=(0, 0), resolution="referenced_unresolved",
         note="族级登记：报告只声明该工件族存在，未列出文件名/路径；本工作树无 runs/ice_8x5 原始目录，"
              "故只登记引用与缺失机检。引文与 A02 重叠——A02 登记整段案例声明，A16 单列该工件族"),
    dict(asset_id="A15", asset_class="gate_report_ref",
         label="既有闸门报告引用（ice_resistance_gate_report.md，4 条文献基线）",
         anchor="平台既有闸门 ice_resistance_gate_report.md", span=(0, 0),
         resolution="referenced_unresolved",
         note="闸门报告不在本工作树；登记引用事实，不替其背书"),
]

REF_PATH_CHECKS = {
    "A04": ["runs/ice_8x5/run_sweep.py", "runs/ice_8x5/cross_method.py", "runs/ice_8x5/make_tables.py"],
    "A05": ["tests/test_ice_8x5_sweep.py"],
    "A09": ["benchmarks.csv"],
    "A15": ["ice_resistance_gate_report.md"],
    "A16": ["runs/ice_8x5"],
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


def build_locator(md: str, lines, offs, anchor: str, span):
    if anchor == "--doc--":
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1, quote=md, unique=True)
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor not unique/found ({len(hits)} hits): {anchor!r}")
    a = hits[0]
    i0 = a + span[0]
    i1 = (len(lines) - 1) if span[1] < 0 else a + span[1]
    start, end = offs[i0], offs[i1] + len(lines[i1])
    quote = md[start:end]
    return dict(method="char_span", start_char=start, end_char=end,
                start_line=i0, end_line=i1, quote=quote, unique=md.count(quote) == 1)


def section_of(lines, upto):
    head = "(document)"
    for ln in lines[: upto + 1]:
        if ln.startswith("#"):
            head = ln.strip()
    return head


def ship_openapi_paths():
    try:
        with urllib.request.urlopen(SHIP_API, timeout=10) as r:
            data = json.loads(r.read().decode())
        return sorted(data.get("paths", {})), None
    except Exception as exc:  # environment dependent, reported honestly
        return [], str(exc)


def main() -> int:
    ART_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    md = (ART_DIR / "source_markdown.md").read_text()
    meta = json.loads((ART_DIR / "source_meta.json").read_text())

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {EXPECTED_HASH}")
        return 2
    if len(md) != EXPECTED_CHARS:
        print(f"FATAL: markdown chars {len(md)} != contract chars {EXPECTED_CHARS}")
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()
    openapi_paths, openapi_err = ship_openapi_paths()

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit(f"duplicate asset_id {spec['asset_id']}")
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"])
        if not loc["unique"]:
            raise SystemExit(f"quote not unique for {spec['asset_id']}: {spec['anchor']!r}")
        if loc["method"] == "char_span":
            # independent re-slice: offsets must reproduce the quote exactly
            if md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
                raise SystemExit(f"locator offsets do not reproduce quote: {spec['asset_id']}")

        aid = spec["asset_id"]
        if aid in REF_PATH_CHECKS:
            paths = REF_PATH_CHECKS[aid]
            missing = [p for p in paths if not (worktree / p).exists()]
            check = dict(check="worktree_path_exists", paths=paths, missing=missing,
                         result="unresolved" if missing else "resolved",
                         detail="仅查本工作树；产出仓内的本体不跨仓取件")
        elif aid == "A03":
            eps = re.findall(r"`(/api/v1/[^`]+)`", loc["quote"])
            present = [p for p in eps if p in openapi_paths]
            absent = [p for p in eps if p not in openapi_paths]
            check = dict(check="ship_openapi_endpoint_exists", api=SHIP_API,
                         endpoints_declared=eps, endpoints_present=present,
                         endpoints_absent=absent, openapi_path_count=len(openapi_paths),
                         openapi_error=openapi_err,
                         result="resolved" if eps and not absent and not openapi_err else "unresolved")
        elif aid == "A14":
            moor = [p for p in openapi_paths if "moor" in p.lower()]
            ice_moor = [p for p in openapi_paths if "moor" in p.lower() and "ice" in p.lower()]
            check = dict(check="ship_openapi_ice_mooring_keyword_scan", api=SHIP_API,
                         openapi_path_count=len(openapi_paths), mooring_paths=moor,
                         ice_and_mooring_paths=ice_moor, openapi_error=openapi_err,
                         result="absent" if (not openapi_err and not ice_moor) else "present")
        elif aid == "A11":
            figs = meta.get("figure_names") or []
            named_in_quote = re.findall(r"fig\d+_[a-z_]+", loc["quote"])
            check = dict(check="platform_figures_field", platform_figures_count=len(figs),
                         platform_figure_names=figs,
                         named_in_figure_section=named_in_quote,
                         result="present" if figs else "absent",
                         detail="分辨率=平台 figures 字段非空；图为平台内嵌 png，工作树无二进制副本")
        else:
            check = dict(check="char_span_in_source_markdown", result="resolved",
                         detail="quote 在源 markdown 中唯一出现且偏移可复现")

        assets.append(dict(
            asset_id=aid,
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=section_of(lines, loc["start_line"]),
            resolution=spec["resolution"],
            resolution_check=check,
            locator=loc,
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
        report_id=REPORT_ID,
        source=dict(
            uri=SOURCE_URI, field="markdown", hash_alg="sha256", hash=md_hash,
            chars=len(md), bytes_utf8=len(md.encode()),
            title=meta.get("title"), scenario_key=meta.get("scenario_key"),
            platform_id=meta.get("report_id"), platform_mission_id=meta.get("mission_id"),
            platform_tags=meta.get("tags", []),
            platform_figures=meta.get("figure_names", []),
            retrieved_via="GET %s/tensor/reports/%s" % (
                os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
                REPORT_ID),
            local_copy=str(ART_DIR / "source_markdown.md"),
        ),
        counts=dict(assets=len(assets), by_class=by_class, by_resolution=by_res,
                    resolved_in_source=by_res.get("resolved_in_source", 0),
                    referenced_unresolved=by_res.get("referenced_unresolved", 0),
                    declared_absent=by_res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("契约 objective.classify_report_type=false 且 notes 明确 claims 允许为空数组："
                     "本工序只登记源资产定位，不抽取 claim；claim 抽取由下游工序负责。"
                     "本清单不得被读作 verified——verification 由平台门独立计算。"),
        integrity=dict(
            quote_uniqueness="全部 quote 均为源 markdown 的唯一子串，locator 偏移可复现（scripts/kf_verify_13980.py）",
            hash_recomputed_locally=True, hash_matches_contract=True,
            source_chars_match_contract=len(md) == EXPECTED_CHARS,
        ),
    )

    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art = ART_DIR / "asset_manifest.json"
    art.write_text(blob)
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()

    (ART_DIR / "resolution_checks.json").write_text(json.dumps(
        dict(package_id=PACKAGE_ID, ship_openapi=SHIP_API, openapi_error=openapi_err,
             openapi_path_count=len(openapi_paths),
             checks={a["asset_id"]: a["resolution_check"] for a in assets}),
        ensure_ascii=False, indent=2) + "\n")

    (RUN_DIR / "asset_manifest.json").write_text(blob)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
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
            source_title=meta.get("title"),
            scenario_key=meta.get("scenario_key"),
            contract_version="1.0",
            lane="C",
            work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(ART_DIR / "source_markdown.md"),
            generator="scripts/kf_register_13980.py",
            verifier="scripts/kf_verify_13980.py",
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": dict(
            artifact_path=str(art), artifact_sha256=art_hash,
            artifact_bytes=art.stat().st_size, **{k: v for k, v in manifest.items()})},
        claims=[],
    )

    (RUN_DIR / "kf_result.wp-13980-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "kf_result_block.wp-13980-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("chars:", len(md), "bytes:", len(md.encode()))
    print("assets:", len(assets), "by_class:", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("openapi paths:", len(openapi_paths), "err:", openapi_err)
    print("manifest:", art, art_hash)
    print("result:", RUN_DIR / "kf_result.wp-13980-01.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())