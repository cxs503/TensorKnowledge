"""Register the source assets of report 448 (work package wp-448-01, task_type 01-asset-registration).

Design rules enforced here:
  * No hand transcription. Every ``quote`` in the manifest is sliced out of the report markdown at
    run time from a programmatic anchor (line search + line span); the script re-checks that each
    quote is a *unique* substring of the markdown before writing anything.
  * Registration only. No claim extraction (contract: objective.register_assets only, claims may be
    empty). Items that cannot be resolved from the platform/worktree are recorded as
    ``referenced_unresolved`` / ``declared_absent`` with the reason -- never silently dropped and
    never given an invented address.
  * Nothing is marked verified. ``resolution`` describes locator resolvability only.

Inputs (produced by scripts/kf_fetch_448.py):
  runs/wp-448-01/report_448.md    (markdown payload)
  runs/wp-448-01/report_448.json  (raw API payload: id/title/scenario_key/figures/...)

Outputs:
  artifacts/wp-448-01/asset_manifest.json
  runs/wp-448-01/kf_result.wp-448-01.json          (result envelope, kf_result.v1 shape)
  runs/wp-448-01/kf_result_block.wp-448-01.json    (same JSON, for the single ```json block)

Usage: python3 scripts/kf_register_448.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

REPORT_ID = "448"
PACKAGE_ID = "wp-448-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "a3e7910fbcbe3624805a875ebd9a033c54036a1950cdc2885a6fc739dbcabea8"
SOURCE_URI = "tensor://reports/448"

RUN_DIR = pathlib.Path("runs/wp-448-01")
ART_DIR = pathlib.Path("artifacts/wp-448-01")
# durable mirror: this repo's push gate drops artifacts/** and runs/** (tp_pusher._EXCLUDE),
# so the committed copy of every deliverable lives under docs/wp-448-01/ (byte-identical).
DOC_DIR = pathlib.Path("docs/wp-448-01")

# Anchor table: asset_id, class, label, anchor substring (must be unique in the markdown),
# line span relative to the anchor line, and the resolution status.
# The anchor is only used to *find* lines; the emitted quote is the verbatim line text.
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文）",
         anchor="--doc--", span=(0, -1), resolution="resolved_in_source",
         note="整篇 markdown 即源资产；sha256 见 source.hash"),
    dict(asset_id="A02", asset_class="heading", label="报告标题",
         anchor="# EX-1 水池锚定", span=(0, 0), resolution="resolved_in_source",
         note="标题行；与 API title 字段同源"),
    dict(asset_id="A03", asset_class="table", label="基线几何参数表（7 行）",
         anchor="| 参数 | 符号 | 值 | 来源 |", span=(0, 8), resolution="resolved_in_source",
         note="表头+分隔行+7 行数据；数值仅登记不换算"),
    dict(asset_id="A04", asset_class="geometry_declaration", label="几何锁定状态（STL/点云/主尺度）",
         anchor="### 几何锁定状态", span=(1, 3), resolution="resolved_in_source",
         note="三条声明的原文；资产本体（STL/点云文件）见 A17/A18"),
    dict(asset_id="A05", asset_class="statement", label="优化目标 min C_T(Fr=0.28)",
         anchor="**目标**: min C_T(Fr=0.28)", span=(0, 0), resolution="resolved_in_source",
         note="单行目标声明"),
    dict(asset_id="A06", asset_class="design_space", label="设计变量定义（8 DOF，x1-x8）",
         anchor="**设计变量**: 8 DOF", span=(0, 3), resolution="resolved_in_source",
         note="含 8 DOF 声明行 + 3 条分组说明"),
    dict(asset_id="A07", asset_class="constraint_set", label="约束 C1-C7（可执行断言）",
         anchor="**约束** (可执行断言 C1-C7):", span=(0, 7), resolution="resolved_in_source",
         note="7 条约束原文；可执行实现体在 A19 引用的 test_constraints.py（未解析）"),
    dict(asset_id="A08", asset_class="parameter_set", label="速度矩阵（5 个 Fr 点 + 设计点权重）",
         anchor="**速度矩阵**: 5 个 Fr 点 (0.14/0.21/0.28/0.35/0.41)", span=(0, 0), resolution="resolved_in_source",
         note="Fr 点与权重原文"),
    dict(asset_id="A09", asset_class="measurement_plan", label="三层评估方案（经验公式/CFD/水池）",
         anchor="### 三层评估方案", span=(1, 3), resolution="resolved_in_source",
         note="各层样本量与不确定度原文"),
    dict(asset_id="A10", asset_class="prereg_lock", label="预注册锁定条目（4 条）",
         anchor="### 预注册锁定", span=(1, 4), resolution="resolved_in_source",
         note="append-only 与判定规则原文；基线 C_T 单独登记为 A12"),
    dict(asset_id="A11", asset_class="prediction", label="预测改善区间（保守/乐观/最可能）",
         anchor="### 预测改善区间", span=(1, 3), resolution="resolved_in_source",
         note="三条预测原文；属预测值非实测"),
    dict(asset_id="A12", asset_class="numeric_anchor", label="基线 C_T 参考值 2.40e-3（IIHR+CFDWS 均值）",
         anchor="- 基线 C_T 参考值: 2.40e-3", span=(0, 0), resolution="resolved_in_source",
         note="单一数字锚点；外部出处为文献均值，报告未给可解析地址"),
    dict(asset_id="A13", asset_class="table", label="约束断言测试结果表（11 行）",
         anchor="| 测试用例 | 结果 | 说明 |", span=(0, 12), resolution="resolved_in_source",
         note="11 个用例的通过标记；测试代码本体在 A19 引用（未解析）"),
    dict(asset_id="A14", asset_class="figure_declaration", label="无图声明与待出图清单",
         anchor="本任务为纯文档/规格定义，无计算场量或对比曲线", span=(0, 4),
         resolution="declared_absent", note="报告声明本阶段无图；API figures 字段为空数组"),
    dict(asset_id="A15", asset_class="figure_slot", label="已声明待产图件（3 项）",
         anchor="- **无图理由**:", span=(1, 3), resolution="declared_absent",
         note="计划中图件，尚未产出；不登记为现存资产"),
    dict(asset_id="A16", asset_class="limitation_set", label="局限与风险（4 条）",
         anchor="### 局限与风险", span=(1, 4), resolution="resolved_in_source",
         note="精度/不确定度/成本/预期偏离原文"),
    dict(asset_id="A17", asset_class="external_dataset", label="精确 STL 几何（164926 面，7.9 MB）",
         anchor="- 精确 STL:", span=(0, 0), resolution="referenced_unresolved",
         note="报告未给出可解析地址（无路径/URL/DOI），仅声明规模与门禁结果"),
    dict(asset_id="A18", asset_class="external_dataset", label="官方点云（2250 点，Zenodo 源）",
         anchor="- 官方点云:", span=(0, 0), resolution="referenced_unresolved",
         note="仅标注来源为 Zenodo，无 record id/DOI，无法在平台侧解析"),
    dict(asset_id="A19", asset_class="external_file_set", label="交付物清单（docs/ex1/ 5 个文件）",
         anchor="**交付物**:", span=(1, 5), resolution="referenced_unresolved",
         note="仓库相对路径；本工作树（TensorKnowledge）内不存在，属外部仓库产物"),
    dict(asset_id="A20", asset_class="vcs_reference", label="Git Commit 78ed109（agent/m541 分支）",
         anchor="**Git Commit**:", span=(0, 0), resolution="referenced_unresolved",
         note="外部仓库提交号；本仓 git 对象库无法解析"),
    dict(asset_id="A21", asset_class="table", label="关键量 vs 基准误差表（6 行）",
         anchor="| 指标 | 本任务值 | 基准值 | 误差 | <3%? |", span=(0, 7),
         resolution="resolved_in_source", note="上游自报 0% 误差；本工序只登记不复核"),
    dict(asset_id="A22", asset_class="external_note", label="图件补充要求（RPT-REWORK m583 治理标记）",
         anchor="## 图件补充 (RPT-REWORK m583)", span=(0, 4), resolution="resolved_in_source",
         note="治理标记：报告曾因缺图被要求补图；标记不含图件本体"),
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
    if aid == "A19":
        paths = ["docs/ex1/problem_spec.md", "docs/ex1/prereg.md", "docs/ex1/evaluation_plan.md",
                 "docs/ex1/data_anchors.md", "docs/ex1/test_constraints.py"]
        missing = [p for p in paths if not (worktree / p).exists()]
        return dict(check="worktree_path_exists", paths=paths, missing=missing,
                    result="unresolved" if missing else "resolved")
    if aid == "A20":
        try:
            r = subprocess.run(["git", "cat-file", "-e", "78ed109^{commit}"],
                               cwd=str(worktree), capture_output=True, timeout=30)
            ok = r.returncode == 0
            return dict(check="git_cat_file", object="78ed109", result="resolved" if ok else "unresolved",
                        exit_code=r.returncode)
        except Exception as exc:  # pragma: no cover - environment dependent
            return dict(check="git_cat_file", object="78ed109", result="unresolved", error=str(exc))
    if aid in ("A17", "A18"):
        line = asset["locator"]["quote"]
        found = re.findall(r"(https?://\S+|doi:\S+|10\.\d{4,}/\S+|[A-Za-z]:\\\S+)", line)
        return dict(check="address_extraction", result="unresolved" if not found else "resolved",
                    addresses_found=found,
                    detail="仅在报告文本内检索 URL/DOI/绝对路径（不联网猜测地址）")
    if aid in ("A14", "A15"):
        figs = (payload or {}).get("figures", [])
        return dict(check="platform_figures_field", result="absent" if not figs else "present",
                    platform_figures_count=len(figs),
                    detail="报告声明本阶段无图，且平台 figures 字段为空")
    return dict(check="char_span_in_source_markdown", result="resolved")


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    payload = json.loads((RUN_DIR / "report_448.json").read_text())
    md = (RUN_DIR / "report_448.md").read_text()

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
            retrieved_via="GET %s/tensor/reports/448" % os.environ.get(
                "TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
            local_copy=str(RUN_DIR / "report_448.md"),
        ),
        counts=dict(assets=len(assets), by_class=classes, by_resolution=res,
                    resolved_in_source=res.get("resolved_in_source", 0),
                    referenced_unresolved=res.get("referenced_unresolved", 0),
                    declared_absent=res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组："
                     "本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。"),
        integrity=dict(quote_uniqueness="all quotes confirmed unique substrings of source markdown (scripts/kf_verify_448.py, checks.source_locator_resolvable)",
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
            local_copy=str(RUN_DIR / "report_448.md"),
            generator="scripts/kf_register_448.py",
            verifier="scripts/kf_verify_448.py",
            verification_status="not_verified",  # verification is computed by the platform gate
        ),
        outputs={"asset_manifest.json": outputs_manifest},
    )

    res_path = RUN_DIR / "kf_result.wp-448-01.json"
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "kf_result_block.wp-448-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == EXPECTED_HASH else "MISMATCH")
    print("assets:", len(assets), "by_class:", json.dumps(classes, ensure_ascii=False))
    print("by_resolution:", json.dumps(res, ensure_ascii=False))
    print("manifest:", art, art_hash)
    print("result:", res_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())