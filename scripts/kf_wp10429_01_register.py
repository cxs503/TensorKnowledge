#!/usr/bin/env python3
"""wp-10429-01 (task_type=01-asset-registration) — register the assets of report 10429.

Scope discipline
  * only report_id=10429 is touched (single-record pipeline stage);
  * no extraction: objective.classify_report_type=false and the contract notes allow
    claims=[] -> we register locators, we do not mint knowledge claims;
  * zero hand-copying: every quote in the manifest is *cut* from the fetched markdown by
    line/char arithmetic (build_locator), never retyped;
  * nothing is marked verified: provenance.verification_status = "not_verified"
    (the platform gate computes verification).

Inputs (fetch step, scripts/kf_fetch_10429.py or the fetch block below)
  runs/wp-10429-01/report_10429.json   raw API payload
  runs/wp-10429-01/report_10429.md     markdown payload

Outputs
  artifacts/wp-10429-01/asset_manifest.json           (contract output)
  docs/kf/wp-10429-01/asset_manifest.json             (durable mirror, byte-identical)
  runs/wp-10429-01/kf_result.wp-10429-01.json         (kf_result.v1 envelope)
  runs/wp-10429-01/kf_result_block.wp-10429-01.json   (identical, for the single ```json block)
  docs/kf/wp-10429-01/kf_result.json                  (durable mirror of the envelope)

Usage: python3 scripts/kf_wp10429_01_register.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "10429"
PACKAGE_ID = "wp-10429-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_VERSION = "1.0"
EXPECTED_HASH = "6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d"
SOURCE_URI = "tensor://reports/10429"
SCENARIO_KEY = "fsi_lbm_strong_coupling"
EXPECTED_TITLE = ("P153W2-N03 TensorFEM x TensorLBM strong-coupling FSI: Turek-Hron 2D-2 anchor "
                  "+ FSI-2 honest-FAIL + energy ledger")
EXPECTED_CHARS = 7442

RUN_DIR = pathlib.Path("runs/wp-10429-01")
ART_DIR = pathlib.Path("artifacts/wp-10429-01")
DOC_DIR = pathlib.Path("docs/kf/wp-10429-01")

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

# ---------------------------------------------------------------------------
# Asset table.  anchor = a substring that occurs on exactly ONE source line
# (the script fails loudly otherwise); span = (first_line_offset, last_line_offset)
# relative to that line; the emitted quote is the verbatim text of those lines.
# resolution is a *structural* judgement, re-checked by kf_wp10429_01_verify.py:
#   resolved_in_source   -> the quoted text exists at the recorded char span
#   referenced_unresolved-> the report points at something not resolvable from this
#                          worktree / without a resolvable address (no invented address)
#   declared_absent      -> the report itself declares the artefact absent
# ---------------------------------------------------------------------------
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，源资产本体）",
         anchor="__DOCUMENT__", span=None, resolution="resolved_in_source",
         note="整篇 markdown 即源资产；sha256 与 chars 见 source.hash/chars"),
    dict(asset_id="A02", asset_class="heading", label="报告标题行（含 P153W2-N03 编号与主题）",
         anchor="# P153W2-N03 — LBM x FE partitioned strong coupling", span=(0, 0),
         resolution="resolved_in_source", note="标题行；与平台 title 字段同源"),
    dict(asset_id="A03", asset_class="vcs_reference", label="产出来源三元组：Repo TensorFEM / branch agent/m8136 / mission 8136",
         anchor="**Repo** TensorFEM · **branch** `agent/m8136` · **mission** 8136", span=(0, 0),
         resolution="resolved_in_source",
         note="分支名可登记，但报告未给 commit sha，故无 git 对象可解析（见 resolution_check.detail）"),
    dict(asset_id="A04", asset_class="case_geometry", label="Turek-Hron 2D-2 几何与工况声明（渠道/圆柱/梁尺寸）",
         anchor="Turek & Hron (2006) laminar channel 2.5 x 0.41 m, rigid cylinder D = 0.1 m at",
         span=(0, 1), resolution="resolved_in_source",
         note="几何以文字声明，未附网格文件或 STL；D/L/h 三个尺度是该 FSI 基准的定义量"),
    dict(asset_id="A05", asset_class="parameter_set", label="物理参数集（rho/nu/U_mean/Re/E/rho_s）",
         anchor="Physical parameters: rho = 1000 kg/m^3", span=(0, 1),
         resolution="resolved_in_source", note="数值原样登记，不做单位换算"),
    dict(asset_id="A06", asset_class="table", label="两个锚定算例定义表 + 外部参考量（CD/CL/St）",
         anchor="| case | what it isolates | external reference |", span=(0, 4),
         resolution="resolved_in_source",
         note="外部参考以区间给出（CD=3.22-3.24, St=0.295-0.305）；参考来源见 A18 参考文献集"),
    dict(asset_id="A07", asset_class="code_pointer", label="流体求解器 src/tensorfem/lbm_channel2d.py（外部仓文件）",
         anchor="* **Fluid** `src/tensorfem/lbm_channel2d.py`", span=(0, 2),
         resolution="referenced_unresolved",
         note="TensorFEM 仓相对路径；本工作树（TensorKnowledge）内不存在该文件，无法解析到具体版本"),
    dict(asset_id="A08", asset_class="code_pointer", label="结构求解器符号 CantileverBeamFE / ModalCantileverBeam",
         anchor="* **Structure** `CantileverBeamFE` / `ModalCantileverBeam`", span=(0, 4),
         resolution="referenced_unresolved",
         note="仅给符号名，未给文件路径或 commit；本工作树内无同名符号"),
    dict(asset_id="A09", asset_class="code_pointer", label="耦合模块符号 StrongCouplingFSI2（Aitken 动态松弛）",
         anchor="* **Coupling** `StrongCouplingFSI2`", span=(0, 5),
         resolution="referenced_unresolved",
         note="符号名 + 方法描述；实现体在外部仓，本工作树不可解析"),
    dict(asset_id="A10", asset_class="method_declaration", label="能量账本构成的五项定义",
         anchor="* **Energy ledger**: fluid kinetic energy", span=(0, 2),
         resolution="resolved_in_source", note="账本项定义原文；账本数值本体见 A13/A15"),
    dict(asset_id="A11", asset_class="table", label="流体锚定结果表（3 组 cells/D × dt，含相对误差）",
         anchor="| cells/D | dt [s] | CD | CL amplitude | St |", span=(0, 5),
         resolution="resolved_in_source",
         note="上游自报相对误差；本工序只登记不复核（复核属下游/门）"),
    dict(asset_id="A12", asset_class="validation_statement", label="网格收敛性结论（CD 1.81% / St 0.35%）",
         anchor="Grid refinement (D=12 -> 20): CD changes 1.81%,", span=(0, 3),
         resolution="resolved_in_source",
         note="结论同时给出主导偏差来源（零梯度出口反射声波）"),
    dict(asset_id="A13", asset_class="table", label="结构与界面验证表（f1 / Newmark 能量漂移 / 静挠度 / 界面合力守恒）",
         anchor="| check | result | criterion |", span=(0, 5),
         resolution="resolved_in_source", note="4 项自检结果与其判据并列给出"),
    dict(asset_id="A14", asset_class="table", label="耦合 FSI-2 运行清单（步数/子迭代/FFT 峰/幅值/阻力/账本残差）",
         anchor="| quantity | value | note |", span=(0, 7),
         resolution="resolved_in_source",
         note="运行配置（cells/D=20, u_lat=0.05, dt=2.50e-04, 1200 steps, 5 modes, zeta=2%）在表前一行"),
    dict(asset_id="A15", asset_class="table", label="验收判据表 C1-C8（computed 值与 verdict）",
         anchor="| id | criterion | computed | verdict |", span=(0, 9),
         resolution="resolved_in_source",
         note="含 FAIL/WITHHELD/PASS 三种判定；本工序不改变其状态、不标 verified"),
    dict(asset_id="A16", asset_class="statement", label="总体判定陈述（2/8 定量判据通过，honest FAIL）",
         anchor="**Verdict: C6 and C7 and C8 pass;", span=(0, 1),
         resolution="resolved_in_source", note="判定陈述原文；数值依据见 A15"),
    dict(asset_id="A17", asset_class="root_cause_set", label="C8 根因分析 6 条（瞬态/算力/无幅值饱和/出口反射/参考转写/旧 PASS 被证伪）",
         anchor="## 5. Root causes of the FAIL (C8)", span=(1, 20),
         end_anchor="be downgraded to MOCK in the ledger.",
         resolution="resolved_in_source",
         note="第 6 条含对既有能力 fsi_turek_hron / fsi_flutter 的证伪结论，见 A19 单列"),
    dict(asset_id="A18", asset_class="statement", label="新增且已验证内容清单（4 项）",
         anchor="## 6. What is genuinely new and verified", span=(1, 9),
         end_anchor="FSI modules are MOCK.",
         resolution="resolved_in_source", note="上游自述『verified』；本工序原样登记，不改写为平台 verified"),
    dict(asset_id="A19", asset_class="falsification_statement", label="证伪结论：fsi_turek_hron（调参+Re=30 当 100）与 fsi_flutter（2sqrt(mu) 同义反复）应降级 MOCK",
         anchor="6. **Previously reported PASS is falsified.**", span=(0, 3),
         resolution="resolved_in_source",
         note="负面结论（capability downgrade 建议）；不由本工序执行降级，仅登记"),
    dict(asset_id="A20", asset_class="figure_declaration", label="图件声明 4 项（artifacts/fsi_strong_coupling/*.png）",
         anchor="## 7. Figures", span=(1, 5),
         resolution="resolved_in_source",
         note="路径为 TensorFEM 仓相对路径；平台 record.figures 里 4 个同名图件已存在（名称逐一对应）"),
    dict(asset_id="A21", asset_class="reference_set", label="参考文献集 4 条（Turek-Hron 2006 / Kuettler-Wall 2008 / Guo 2002 / Newmark 1959）",
         anchor="## 8. References", span=(1, 10),
         end_anchor="   J. Eng. Mech. Div. 85, 67.",
         resolution="resolved_in_source",
         note="书目条目在源文内可定位；条目未给 DOI/URL，故外部全文不可由本工序解析"),
    dict(asset_id="A22", asset_class="numeric_anchor", label="关键数值锚点：账本残差 6.693557969802016（669%）触发 C5 FAIL",
         anchor="| C5 | energy ledger residual (<= 5%) |", span=(0, 0),
         resolution="resolved_in_source",
         note="单一数字锚；同一量在 A14 以 669% 形式出现（百分比与小数两处一致，仅登记不做换算校验）"),
]

# Declared external artefact paths (from A07-A09/A20 regions); existence is *checked*,
# never assumed.  Missing -> referenced_unresolved with the searched candidates listed.
EXTERNAL_PATH_CANDIDATES = {
    "A07": ["src/tensorfem/lbm_channel2d.py", "tensorfem/lbm_channel2d.py"],
    "A08": ["src/tensorfem/beam_fe.py", "src/tensorfem/cantilever_beam.py"],
    "A09": ["src/tensorfem/strong_coupling_fsi2.py", "src/tensorfem/fsi_coupling2.py"],
    "A20": ["artifacts/fsi_strong_coupling/fig_cylinder_validation.png",
            "artifacts/fsi_strong_coupling/fig_fsi2_history.png",
            "artifacts/fsi_strong_coupling/fig_energy_ledger.png",
            "artifacts/fsi_strong_coupling/fig_summary.png"],
}


# ---------------------------------------------------------------------------
def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def find_line(lines, needle: str) -> int:
    hits = [i for i, ln in enumerate(lines) if needle in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor {needle!r} matched {len(hits)} lines (need exactly 1): {hits[:5]}")
    return hits[0]


def build_locator(md: str, lines, offs, anchor: str, span, end_anchor=None):
    if anchor == "__DOCUMENT__":
        # quote is a VERBATIM slice of the head of the document (not an elided display
        # string): a gate that resolves every quote by substring search must still pass.
        head = md[:200]
        return dict(method="document", start_char=0, end_char=len(md), start_line=0,
                    end_line=len(lines) - 1, quote=head,
                    unique=(md.count(head) == 1), span_chars=len(md))
    i0 = find_line(lines, anchor)
    a, b = span
    s, e = i0 + a, i0 + b
    if end_anchor is not None:
        e = find_line(lines, end_anchor)
        if e < s:
            raise SystemExit(f"end_anchor {end_anchor!r} (line {e}) precedes start {s}")
    if s < 0 or e >= len(lines) or e < s:
        raise SystemExit(f"bad span {span} for anchor {anchor!r} (line {i0}, n_lines={len(lines)})")
    quote = "\n".join(lines[s:e + 1])
    return dict(method="char_span", start_char=offs[s], end_char=offs[e] + len(lines[e]),
                start_line=s, end_line=e, quote=quote,
                unique=(md.count(quote) == 1), span_chars=len(quote))


def section_head(lines, line_no: int) -> str:
    head = "(document)"
    for ln in lines[:line_no]:
        if ln.startswith("#"):
            head = ln.strip()
    return head


def resolution_check(spec: dict, md: str, manifest_quote: str, payload: dict) -> dict:
    aid = spec["asset_id"]
    if aid == "A01":
        ok = sha256_text(md) == EXPECTED_HASH
        return dict(check="document_sha256_matches_contract",
                    result="resolved" if ok else "unresolved",
                    detail="整篇 markdown sha256 与契约 source_hash %s" % ("一致" if ok else "不一致"))
    if spec["resolution"] == "resolved_in_source":
        if aid == "A20":
            figs = payload.get("figures") or []
            names = [f.get("name") for f in figs if isinstance(f, dict)]
            declared = [ln.strip("- *`") for ln in manifest_quote.split("\n") if ".png" in ln]
            declared_stems = [d.rsplit("/", 1)[-1][:-4] for d in declared]
            matched = [s for s in declared_stems if s in names]
            return dict(check="platform_figures_name_match",
                        result="present" if matched else "absent",
                        detail=f"declared png 声明 {len(declared_stems)} 个，平台 record.figures 同名 {len(matched)} 个",
                        declared=declared_stems, platform_figure_names=names)
        pos = md.find(manifest_quote)
        return dict(check="substring_at_char_span", result="resolved" if pos >= 0 else "unresolved",
                    detail="quote 在源 markdown 中逐字命中" if pos >= 0 else "quote 未命中",
                    found_at_char=pos)
    if spec["resolution"] == "referenced_unresolved":
        cands = EXTERNAL_PATH_CANDIDATES.get(aid, [])
        found = [c for c in cands if pathlib.Path(c).exists()]
        return dict(check="worktree_path_lookup", result="resolved" if found else "unresolved",
                    detail=("命中:" + ",".join(found)) if found else
                           "候选中本工作树均不存在（外部仓 TensorFEM 产物）；报告未给 URL/DOI/commit，故不猜地址",
                    searched=cands)
    return dict(check="report_declared_absent", result="absent")


def fetch(via: str = "api") -> tuple[dict, str]:
    """Fetch report 10429 (API) or reuse the local copy; env holds the credentials."""
    jpath, mpath = RUN_DIR / "report_10429.json", RUN_DIR / "report_10429.md"
    if via == "local" and jpath.exists() and mpath.exists():
        return json.loads(jpath.read_text()), mpath.read_text()
    creds = {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    req = urllib.request.Request(API + "/auth/login", data=json.dumps(creds).encode(),
                                 headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req, timeout=60))["access_token"]
    req = urllib.request.Request(f"{API}/tensor/reports/{REPORT_ID}",
                                 headers={"Authorization": "Bearer " + tok})
    payload = json.load(urllib.request.urlopen(req, timeout=120))
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    jpath.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    rec = payload.get("data", payload)
    md = rec["markdown"]
    mpath.write_text(md)
    return payload, md


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    payload, md = fetch("local" if (RUN_DIR / "report_10429.md").exists() else "api")
    rec = payload.get("data", payload)

    md_hash = sha256_text(md)
    problems = []
    if md_hash != EXPECTED_HASH:
        problems.append(f"sha256 {md_hash} != contract {EXPECTED_HASH}")
    if len(md) != EXPECTED_CHARS:
        problems.append(f"chars {len(md)} != contract {EXPECTED_CHARS}")
    if rec.get("title") != EXPECTED_TITLE:
        problems.append(f"title mismatch: {rec.get('title')!r}")
    if problems:
        print("FATAL: " + "; ".join(problems))
        return 2

    lines, offs = line_offsets(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit(f"duplicate asset_id {spec['asset_id']}")
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"], spec.get("end_anchor"))
        if loc["method"] == "char_span" and not loc["unique"]:
            raise SystemExit(f"quote not unique for {spec['asset_id']}: {spec['anchor']!r}")
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=section_head(lines, loc["start_line"]),
            resolution=spec["resolution"],
            resolution_check=resolution_check(spec, md, loc["quote"], rec),
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
            chars=len(md), bytes_utf8=len(md.encode()), title=rec.get("title"),
            scenario_key=rec.get("scenario_key"), platform_id=rec.get("id"),
            platform_mission_id=rec.get("mission_id"),
            platform_figures=[f.get("name") for f in (rec.get("figures") or []) if isinstance(f, dict)],
            platform_tags=rec.get("tags", []),
            contract_hash="sha256:" + EXPECTED_HASH,
            contract_chars=EXPECTED_CHARS,
            retrieved_via=f"GET {API}/tensor/reports/{REPORT_ID}",
            local_copy=str(RUN_DIR / "report_10429.md"),
            worktree=str(worktree),
        ),
        counts=dict(assets=len(assets), by_class=by_class, by_resolution=by_res,
                    resolved_in_source=by_res.get("resolved_in_source", 0),
                    referenced_unresolved=by_res.get("referenced_unresolved", 0),
                    declared_absent=by_res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("工作包契约 objective.classify_report_type=false / notes『不做抽取，claims 允许为空数组』："
                     "本工序只登记资产与定位，不生成 claim；claim 抽取留给下游工序。"),
        integrity=dict(
            quote_uniqueness=("全部 char_span quote 均由 build_locator 从源 markdown 按行/字符偏移切出，"
                              "并逐一断言 md.count(quote)==1（见 scripts/kf_wp10429_01_register.py）"),
            zero_hand_copy="数字/引文无手工键入，全部来自 fetched markdown 的切片",
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            contract_hash_echoed="sha256:" + EXPECTED_HASH,
            verification_status="not_verified",
            verification_note="verification 由平台门计算；本文件不置 verified 标记",
        ),
    )

    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art = ART_DIR / "asset_manifest.json"
    art.write_text(blob)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
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
            source_title=rec.get("title"),
            scenario_key=rec.get("scenario_key"),
            contract_version=CONTRACT_VERSION,
            lane="C",
            work_package=PACKAGE_ID,
            retrieved_via=manifest["source"]["retrieved_via"],
            local_copy=str(RUN_DIR / "report_10429.md"),
            generator="scripts/kf_wp10429_01_register.py",
            verifier="scripts/kf_wp10429_01_verify.py",
            artifact_path=str(art),
            artifact_sha256=art_hash,
            artifact_bytes=art.stat().st_size,
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": json.loads(blob)},
        claims=[],
    )

    res_path = RUN_DIR / "kf_result.wp-10429-01.json"
    res_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (RUN_DIR / "kf_result_block.wp-10429-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    (DOC_DIR / "kf_result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH")
    print("chars:", len(md), "bytes:", len(md.encode()))
    print("assets:", len(assets), "by_class:", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("manifest:", art, art_hash, art.stat().st_size, "bytes")
    print("result:", res_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())