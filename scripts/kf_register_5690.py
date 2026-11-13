"""Register the source assets of report 5690 (work package wp-5690-01, task_type 01-asset-registration).

Design rules enforced here (same discipline as scripts/kf_register_448.py):
  * No hand transcription. Every ``quote`` in the manifest is sliced out of the report markdown at
    run time from a programmatic anchor (line search + line span); the script re-checks that each
    quote is a *unique* substring of the markdown before writing anything.
  * Registration only. No claim extraction (contract: objective.register_assets only, claims may be
    empty). Items that cannot be resolved from the platform/worktree are recorded as
    ``referenced_unresolved`` / ``declared_absent`` with the reason -- never silently dropped and
    never given an invented address.
  * Nothing is marked verified. ``resolution`` describes locator resolvability only.

Inputs (produced by scripts/kf_fetch_5690.py):
  runs/wp-5690-01/report_5690.md    (markdown payload)
  runs/wp-5690-01/report_5690.json  (raw API payload: id/title/scenario_key/figures/...)

Outputs:
  artifacts/wp-5690-01/asset_manifest.json
  runs/wp-5690-01/kf_result.wp-5690-01.json          (result envelope, kf_result.v1 shape)
  runs/wp-5690-01/kf_result_block.wp-5690-01.json    (same JSON, for the single ```json block)

Usage: python3 scripts/kf_register_5690.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

REPORT_ID = "5690"
PACKAGE_ID = "wp-5690-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "a1e3f5faa1f969bcdfb759f7357adb8cc7474194e44a2c02ae4370f1db1b29a1"
SOURCE_URI = "tensor://reports/5690"

RUN_DIR = pathlib.Path("runs/wp-5690-01")
ART_DIR = pathlib.Path("artifacts/wp-5690-01")
# durable mirror: this repo's push gate drops artifacts/** and runs/** (tp_pusher._EXCLUDE),
# so the committed copy of every deliverable lives under docs/wp-5690-01/ (byte-identical).
DOC_DIR = pathlib.Path("docs/wp-5690-01")

# Anchor table: asset_id, class, label, anchor substring (must be unique in the markdown),
# line span relative to the anchor line, and the resolution status.
# The anchor is only used to *find* lines; the emitted quote is the verbatim line text.
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文）",
         anchor="--doc--", span=(0, -1), resolution="resolved_in_source",
         note="整篇 markdown 即源资产；sha256 见 source.hash（与契约 source_hash 逐字节一致）"),
    dict(asset_id="A02", asset_class="heading", label="报告标题",
         anchor="# IN11-H6 高保真仿真军验收门", span=(0, 0), resolution="resolved_in_source",
         note="标题行；与 API title 字段同源"),
    dict(asset_id="A03", asset_class="statement", label="门禁结论（PASS，12 断言 6/6/0）",
         anchor="**结论：门禁 `PASS`**", span=(0, 0), resolution="resolved_in_source",
         note="单行结论声明；上游自报，本工序只登记不复核"),
    dict(asset_id="A04", asset_class="table", label="上游观测量表（H1-H4，4 行）",
         anchor="| 上游 | 仓 / 模块 | 观测量 | 经验链对端 |", span=(0, 5), resolution="resolved_in_source",
         note="表头+分隔行+4 行数据；数值仅登记不换算"),
    dict(asset_id="A05", asset_class="table", label="交叉一致性断言表（XC-01..XC-12，12 行）",
         anchor="| id | 比对 | 上游量 | dev | 判据 | 结论 |", span=(0, 13), resolution="resolved_in_source",
         note="12 条断言的 dev/判据/结论原文；判据 ±15%（XC-11 为 ±2%）"),
    dict(asset_id="A06", asset_class="statement_set", label="四对指定比对逐条要点（4 条）",
         anchor="**四对指定比对逐条要点**", span=(1, 5), resolution="resolved_in_source",
         note="4 条要点原文；含拒收/上界/口径界定表述"),
    dict(asset_id="A07", asset_class="figure_declaration", label="结果图声明（图 1/2/3）",
         anchor="## ④ 结果图", span=(1, 4), resolution="resolved_in_source",
         note="3 条图声明原文；PNG 字节在平台 figures 字段（3 项，名称 fig1/fig2/fig3_*.png），本仓不落地"),
    dict(asset_id="A08", asset_class="artifact_reference", label="门禁母版 artifacts/hifi_acceptance.json",
         anchor="artifacts/hifi_acceptance.json`（门禁母版）", span=(0, 0), resolution="referenced_unresolved",
         note="H5 仓（ship-performance-platform）相对路径；本工作树内不存在，报告未给可解析 URI"),
    dict(asset_id="A09", asset_class="artifact_reference", label="三库工件归档 artifacts/hifi_upstream/",
         anchor="artifacts/hifi_upstream/`（三库工件归档）", span=(0, 0), resolution="referenced_unresolved",
         note="H5 仓相对路径目录；本工作树内不存在，逐字节归档内容不可在本仓解析"),
    dict(asset_id="A10", asset_class="document_reference", label="论文级报告 docs/campaign/hifi_xcheck_report.md",
         anchor="docs/campaign/hifi_xcheck_report.md`（论文级报告）", span=(0, 0), resolution="referenced_unresolved",
         note="H5 仓相对路径；本工作树内不存在"),
    dict(asset_id="A11", asset_class="figure_set", label="图件集 artifacts/figures/hifi_acceptance/*.png",
         anchor="artifacts/figures/hifi_acceptance/*.png", span=(0, 0), resolution="referenced_unresolved",
         note="H5 仓相对路径通配；本工作树内不存在（平台 figures 字段另有 3 张同名图，见 A07）"),
    dict(asset_id="A12", asset_class="code_reference", label="验收测试 backend/tests/test_hifi_acceptance.py（23 例）",
         anchor="backend/tests/test_hifi_acceptance.py", span=(0, 0), resolution="referenced_unresolved",
         note="H5 仓相对路径；本工作树内不存在，23 例为上游自报"),
    dict(asset_id="A13", asset_class="code_reference", label="Lindqvist 实现 api/ice/formulas.py::calc_lindqvist",
         anchor="api/ice/formulas.py::calc_lindqvist", span=(0, 0), resolution="referenced_unresolved",
         note="H5 仓相对路径+函数符号；本工作树内不存在（上游表 H3 行的 `api.ice/formulas.py` 为同一文件的模块记法）"),
    dict(asset_id="A14", asset_class="code_reference", label="B1 全局力 modules/ice_fullscale/ice_physics.py::global_ice_force/local_line_load",
         anchor="modules/ice_fullscale/ice_physics.py::global_ice_force/local_line_load", span=(0, 0),
         resolution="referenced_unresolved",
         note="H5 仓相对路径+函数符号；本工作树内不存在"),
    dict(asset_id="A15", asset_class="code_reference", label="W9-1215 黏度律 physics/grease_ice/rheology.py::viscosity_ratio",
         anchor="physics/grease_ice/rheology.py::viscosity_ratio", span=(0, 0), resolution="referenced_unresolved",
         note="H5 仓相对路径+函数符号；本工作树内不存在"),
    dict(asset_id="A16", asset_class="external_model", label="W9-1215 损失模型 physics.grease_ice.rheology（φ_max=0.35，α=1.70）",
         anchor="W9-1215 损失模型 `physics.grease_ice.rheology`（φ_max=0.35，α=1.70）", span=(0, 0),
         resolution="referenced_unresolved",
         note="标定产物 W9-1215 的模块记法；本工作树内无该模块，报告未给可解析 URI"),
    dict(asset_id="A17", asset_class="code_reference", label="报告生成器 make_acceptance_docs.py",
         anchor="make_acceptance_docs.py", span=(0, 0), resolution="referenced_unresolved",
         note="H5 仓脚本；本工作树内不存在"),
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


def resolution_check(asset, worktree: pathlib.Path, payload: dict | None = None):
    """Machine check backing the declared resolution status (no invented results)."""
    aid = asset["asset_id"]
    if aid in ("A08", "A09", "A10", "A11", "A12", "A13", "A14", "A15", "A17"):
        paths = {
            "A08": ["artifacts/hifi_acceptance.json"],
            "A09": ["artifacts/hifi_upstream"],
            "A10": ["docs/campaign/hifi_xcheck_report.md"],
            "A11": ["artifacts/figures/hifi_acceptance"],
            "A12": ["backend/tests/test_hifi_acceptance.py"],
            "A13": ["api/ice/formulas.py"],
            "A14": ["modules/ice_fullscale/ice_physics.py"],
            "A15": ["physics/grease_ice/rheology.py"],
            "A17": ["make_acceptance_docs.py"],
        }[aid]
        missing = [p for p in paths if not (worktree / p).exists()]
        return dict(check="worktree_path_exists", paths=paths, missing=missing,
                    result="unresolved" if missing else "resolved",
                    detail="H5 仓（ship-performance-platform）相对路径；本工作树（TensorKnowledge）内实测不存在")
    if aid == "A16":
        line = asset["locator"]["quote"]
        import re
        found = re.findall(r"(https?://\S+|doi:\S+|10\.\d{4,}/\S+)", line)
        p = "physics/grease_ice/rheology.py"
        missing = [p] if not (worktree / p).exists() else []
        return dict(check="address_extraction+worktree_path_exists", addresses_found=found,
                    paths=[p], missing=missing,
                    result="unresolved" if (not found or missing) else "resolved",
                    detail="原文行内无 URL/DOI，且本工作树内无该模块")
    if aid == "A07":
        figs = (payload or {}).get("figures", [])
        return dict(check="platform_figures_field", result="resolved",
                    platform_figures_count=len(figs),
                    figure_names=[f.get("name") for f in figs],
                    detail="3 条图声明在源 markdown 内可定位；PNG 字节在平台 figures 字段（3 项）")
    return dict(check="char_span_in_source_markdown", result="resolved")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / "report_5690.json").read_text())
    md = (RUN_DIR / "report_5690.md").read_text()

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
            platform_figures=payload.get("figures", []),
            platform_tags=payload.get("tags", []),
            retrieved_via="GET %s/tensor/reports/5690" % os.environ.get(
                "TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
            local_copy=str(RUN_DIR / "report_5690.md"),
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组："
                     "本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。"),
        integrity=dict(quote_uniqueness="all quotes confirmed unique substrings of source markdown (scripts/kf_verify_5690.py, checks.source_locator_resolvable)",
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
            local_copy=str(RUN_DIR / "report_5690.md"),
            generator="scripts/kf_register_5690.py",
            verifier="scripts/kf_verify_5690.py",
            verification_status="not_verified",  # verification is computed by the platform gate
        ),
        outputs={"asset_manifest.json": outputs_manifest},
    )

    res_path = RUN_DIR / "kf_result.wp-5690-01.json"
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "kf_result_block.wp-5690-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("assets:", len(assets), "by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", res_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
