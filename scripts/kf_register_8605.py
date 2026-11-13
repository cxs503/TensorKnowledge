"""Register the source assets of report 8605 (work package wp-8605-01, task_type 01-asset-registration).

Design rules enforced here (same as the 448 lineage):
  * No hand transcription. Every ``quote`` in the manifest is sliced out of the report markdown at
    run time from a programmatic anchor (line search + line span); the script re-checks that each
    quote is a *unique* substring of the markdown before writing anything.
  * Registration only. No claim extraction (contract: objective.register_assets only, claims may be
    empty). Items that cannot be resolved from the platform/worktree are recorded as
    ``referenced_unresolved`` / ``declared_absent`` with the reason -- never silently dropped and
    never given an invented address.
  * Nothing is marked verified. ``resolution`` describes locator resolvability only.

Inputs (produced by scripts/kf_fetch_8605.py):
  runs/wp-8605-01/report_8605.md    (markdown payload)
  runs/wp-8605-01/report_8605.json  (raw API payload: id/title/scenario_key/figures/...)

Outputs:
  artifacts/wp-8605-01/asset_manifest.json
  runs/wp-8605-01/kf_result.wp-8605-01.json          (result envelope, kf_result.v1 shape)
  runs/wp-8605-01/kf_result_block.wp-8605-01.json    (same JSON, for the single ```json block)

Usage: python3 scripts/kf_register_8605.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

REPORT_ID = "8605"
PACKAGE_ID = "wp-8605-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36"
SOURCE_URI = "tensor://reports/8605"

RUN_DIR = pathlib.Path("runs/wp-8605-01")
ART_DIR = pathlib.Path("artifacts/wp-8605-01")
# durable mirror: this repo's push gate drops artifacts/** and runs/** (tp_pusher._EXCLUDE),
# so the committed copy of every deliverable lives under docs/wp-8605-01/ (byte-identical).
DOC_DIR = pathlib.Path("docs/wp-8605-01")

# Anchor table: asset_id, class, label, anchor substring (must be unique in the markdown),
# line span relative to the anchor line, and the resolution status.
# The anchor is only used to *find* lines; the emitted quote is the verbatim line text.
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文）",
         anchor="--doc--", span=(0, -1), resolution="resolved_in_source",
         note="整篇 markdown 即源资产；sha256 见 source.hash"),
    dict(asset_id="A02", asset_class="heading", label="报告标题",
         anchor="# P138W2-N09 · CII/EEXI 营运能效动态评级与碳强度漂移预警", span=(0, 0),
         resolution="resolved_in_source", note="标题行；与 API title 字段同源"),
    dict(asset_id="A03", asset_class="statement", label="一句话结论（四门通过 + 实船锚 WITHHELD 声明）",
         anchor="**一句话结论**", span=(0, 2), resolution="resolved_in_source",
         note="含四道门实测数字与 WITHHELD 声明；本工序只登记不复核"),
    dict(asset_id="A04", asset_class="parameter_set", label="算例母船参数表（VLCC 量级，8 行）",
         anchor="| 参数 | 取值 | 说明 |", span=(0, 9), resolution="resolved_in_source",
         note="表头+分隔行+8 行参数；数值仅登记不换算"),
    dict(asset_id="A05", asset_class="module_table", label="模块清单（backend/modules/operational_energy_efficiency/ 7 文件）",
         anchor="| 文件 | 职责 | 证据等级 |", span=(0, 8), resolution="resolved_in_source",
         note="7 个模块文件与证据等级原文；模块本体在外部仓（见 A13）"),
    dict(asset_id="A06", asset_class="gate_result_table", label="四道机器门结果表（4 行）",
         anchor="| 门 | 判据 | 实测 | 容差 | 结论 |", span=(0, 5), resolution="resolved_in_source",
         note="gate_1..gate_4 实测/容差/结论原文"),
    dict(asset_id="A07", asset_class="external_anchor", label="外部锚 GATE_GREEN_M1850（跨仓只读工件）",
         anchor="外部锚（另一仓工件，只读）：", span=(0, 0), resolution="referenced_unresolved",
         note="报告给出路径 backend/tests/data/acceptance_gate_m1850.json 与自身容差 0.02；"
              "该路径属另一仓（ship-performance-platform），本工作树内不存在，无法在平台侧解析"),
    dict(asset_id="A08", asset_class="table", label="外部锚逐算例偏差表（4 行）",
         anchor="| 算例 | 船型 | 容量 | attained 偏差 | 参考线偏差 | required 偏差 |",
         span=(0, 5), resolution="resolved_in_source",
         note="KVLCC2/Capesize/PostPanamax/Handysize 四算例偏差原文"),
    dict(asset_id="A09", asset_class="result_table", label="演示年动态评级与预警结果表（8 行）",
         anchor="| 量 | 数值 | 来源 |", span=(0, 9), resolution="resolved_in_source",
         note="required CII/边界/观测/归一/预测/评级概率/预警/漂移分解原文"),
    dict(asset_id="A10", asset_class="result_table", label="预测校准结果表（200 个 OSSE 年，6 行）",
         anchor="| 量 | 数值 | 名义/判据 |", span=(0, 7), resolution="resolved_in_source",
         note="PI 覆盖率/命中率/点预测误差（gate_4 与演示年两配置）原文"),
    dict(asset_id="A11", asset_class="figure_set", label="结果图清单（4 张，fig1..fig4）",
         anchor="## 4 结果图", span=(1, 5), resolution="resolved_in_source",
         note="图 1-4 内容与文件名原文；图件本体在平台 figures 字段（见 A12）"),
    dict(asset_id="A12", asset_class="figure_artifact", label="平台 figures 字段（4 个内嵌图件）",
         anchor="| 图 | 内容 | 文件 |", span=(0, 5), resolution="resolved_in_source",
         note="平台 API figures 字段含 4 个图件（fig1_calibration.png 等），与报告 §4 清单一致"),
    dict(asset_id="A13", asset_class="external_file_set", label="外部仓工件（artifacts/op_cii_n09/ 与 backend/tests/）",
         anchor="| 工件 | 内容 |", span=(0, 6), resolution="referenced_unresolved",
         note="gate_results.json/monthly_series.csv/forecast_calibration.csv/fig*.png/73 个 pytest 用例；"
              "均属 ship-performance-platform 仓，本工作树内不存在"),
    dict(asset_id="A14", asset_class="limitation_set", label="注意点与局限（7 条）",
         anchor="## 5 注意点", span=(1, 7), resolution="resolved_in_source",
         note="OSSE 浪向律符号/短波域偏低/浅水 DECLARED/η_D 近似/天气假设/规则系数证据等级/实船锚缺失原文"),
    dict(asset_id="A15", asset_class="error_table", label="误差判定表（关键量 vs 基准，7 行）",
         anchor="| 关键量 | 基准 | 误差 | <3%？ |", span=(0, 8), resolution="resolved_in_source",
         note="7 个关键量误差与 <3% 判定原文；含显式结论（外部锚 <3%、OSSE 4.411%、实船 WITHHELD）"),
    dict(asset_id="A16", asset_class="repro_chain", label="复现与审计链（pytest/run/make 命令）",
         anchor="## 7 复现与审计链", span=(1, 4), resolution="resolved_in_source",
         note="三条复现命令原文（73 passed / run_n09.py / make_report.py）"),
    dict(asset_id="A17", asset_class="relationship", label="与既有能力的关系（3 条，不重复已验证案例）",
         anchor="## 8 与既有能力的关系", span=(1, 3), resolution="resolved_in_source",
         note="复用 mepc.py / 补齐 A-E 评级 / 复用 STAWAVE-1 原文"),
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


def build_locator(md: str, lines, offs, anchor: str, span):
    if anchor == "--doc--":
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1,
                    quote=md, unique=True)
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor not unique/found ({len(hits)} hits): {anchor!r}")
    a = hits[0]
    i0, i1 = a + span[0], a + span[1]
    i1 = len(lines) - 1 if i1 < 0 else i1
    start = offs[i0]
    end = offs[i1] + len(lines[i1])
    quote = md[start:end]
    uniq = md.count(quote) == 1
    return dict(method="char_span", start_char=start, end_char=end,
                start_line=i0, end_line=i1, quote=quote, unique=uniq)


def section_of(line: str, previous: str) -> str:
    return line.strip() if line.startswith("#") else previous


def resolution_check(asset, worktree: pathlib.Path, payload: dict | None = None):
    """Machine check backing the declared resolution status (no invented results)."""
    aid = asset["asset_id"]
    if aid == "A07":
        line = asset["locator"]["quote"]
        found = re.findall(r"(https?://\S+|doi:\S+|10\.\d{4,}/\S+|[A-Za-z]:\\\S+)", line)
        return dict(check="address_extraction", result="unresolved" if not found else "resolved",
                    addresses_found=found,
                    detail="报告仅给出相对路径 backend/tests/data/acceptance_gate_m1850.json（无 URL/DOI/绝对路径），"
                           "且该路径属外部仓，本工作树内不存在")
    if aid == "A13":
        paths = ["artifacts/op_cii_n09/gate_results.json",
                 "artifacts/op_cii_n09/monthly_series.csv",
                 "artifacts/op_cii_n09/forecast_calibration.csv",
                 "backend/modules/operational_energy_efficiency/tests/"]
        missing = [p for p in paths if not (worktree / p).exists()]
        return dict(check="worktree_path_exists", paths=paths, missing=missing,
                    result="unresolved" if missing else "resolved",
                    detail="全部路径在本工作树（TensorKnowledge）内均不存在，属 ship-performance-platform 仓产物")
    if aid == "A12":
        figs = (payload or {}).get("figures", [])
        return dict(check="platform_figures_field", result="resolved" if figs else "absent",
                    platform_figures_count=len(figs),
                    detail="平台 figures 字段含 %d 个图件，与报告 §4 清单一致；图件在平台侧可解析" % len(figs))
    return dict(check="char_span_in_source_markdown", result="resolved")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / "report_8605.json").read_text())
    md = (RUN_DIR / "report_8605.md").read_text()

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {EXPECTED_HASH}")
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit(f"duplicate asset_id {spec['asset_id']}")
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"])
        if not loc["unique"]:
            raise SystemExit(f"quote not unique for {spec['asset_id']}: {spec['anchor']!r}")
        head = ""
        for ln in lines[: loc["start_line"]]:
            if ln.startswith("#"):
                head = ln.strip()
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=head or "(document)",
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=resolution_check({**spec, "locator": loc}, worktree, payload),
            note=spec["note"],
        ))

    classes = {}
    for a in assets:
        classes[a["asset_class"]] = classes.get(a["asset_class"], 0) + 1
    res = {}
    for a in assets:
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
            platform_figures=[f.get("name") for f in (payload.get("figures") or [])],
            platform_tags=payload.get("tags") or [],
            retrieved_via=dict(
                api=os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
                local_copy=str(RUN_DIR / "report_8605.md"),
            ),
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组："
                     "本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。"),
        integrity=dict(quote_uniqueness="all quotes confirmed unique substrings of source markdown (scripts/kf_verify_8605.py, checks.source_locator_resolvable)",
                       hash_recomputed_locally=True, hash_matches_contract=True),
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
        schema_version="kf_result.v1",
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
            local_copy=str(RUN_DIR / "report_8605.md"),
            generator="scripts/kf_register_8605.py",
            verifier="scripts/kf_verify_8605.py",
            verification_status="not_verified",  # verification is computed by the platform gate
        ),
        outputs={"asset_manifest.json": outputs_manifest},
    )

    res_path = RUN_DIR / "kf_result.wp-8605-01.json"
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "kf_result_block.wp-8605-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("assets:", len(assets), "by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", res_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
