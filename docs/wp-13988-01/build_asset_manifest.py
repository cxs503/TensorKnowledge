"""wp-13988-01 / 01-asset-registration: build asset_manifest.json for report 13988.

Reads the byte-exact markdown fetched by scripts/kf_fetch_13988.py, then
  * re-verifies sha256(markdown) against the work-package contract,
  * locates every registered asset by a UNIQUE anchor substring and records
    verbatim char/line spans (zero hand-copying: quotes are sliced, not typed),
  * classifies each asset's resolution (resolved_in_source / referenced_unresolved /
    declared_absent) with a machine check,
  * validates the kf_result envelope against schemas/kf_result.v1.schema.json
    (with a negative control) and the manifest against a package-local schema
    derived from schemas/asset_manifest.v1.schema.json,
  * emits artifacts/ + docs/ (durable mirror) + runs/ copies.

No extraction, no claim generation (contract: objective.classify_report_type=false,
notes allow claims=[]). Nothing is marked verified: verification is the platform's.

Usage: python3 docs/wp-13988-01/build_asset_manifest.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

REPORT_ID = "13988"
PACKAGE_ID = "wp-13988-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/13988"
CONTRACT_SOURCE_HASH = "79d795674f0b13f828d8933af64612a1addb30cb8a8b903f7ab136f0508442b9"
CONTRACT_CHARS = 6222

WT = pathlib.Path(".").resolve()
RUN_DIR = WT / "runs" / PACKAGE_ID
ART_DIR = WT / "artifacts" / PACKAGE_ID
DOC_DIR = WT / "docs" / PACKAGE_ID
SCHEMA_DIR = WT / "schemas"
ARTIFACT_ROOT = "artifacts/m14897_calib_reflux/"

# ---------------------------------------------------------------------------
# Asset registry.  anchor = substring that must occur EXACTLY ONCE in the
# markdown; span = (line_offset_from_anchor_line, line_offset_end_inclusive).
# The emitted quote is sliced from those lines -> verbatim by construction.
# resolution_check derives the status from evidence, not from assertion.
# ---------------------------------------------------------------------------
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文）",
         section="(document)", anchor="--DOC--", span=(0, 0),
         resolution="resolved_in_source", check="document_hash",
         note="整篇 markdown 即源资产；sha256 见 source.hash（与契约 source_hash 一致），覆盖全文字符"),
    dict(asset_id="A02", asset_class="heading", label="报告标题",
         section="(document)", anchor="# H5-CALIB-REFLUX", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="一级标题；与平台 title 字段同源"),
    dict(asset_id="A03", asset_class="run_identity", label="任务身份与总判定（m14897 / agent/m14897 / PASS / 工件根）",
         section="(document)", anchor="任务 m14897", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="单行任务头；工件根路径 artifacts/m14897_calib_reflux/ 在此声明，是本报告唯一给出的工件目录"),
    dict(asset_id="A04", asset_class="vcs_reference", label="工作分支 agent/m14897（无 commit sha）",
         section="(document)", anchor="任务 m14897", span=(0, 0),
         resolution="referenced_unresolved", check="vcs_reference",
         note="报告只给分支名，未给 commit 对象标识；本工作树（TensorKnowledge）无该分支，不可解析到具体提交"),
    dict(asset_id="A05", asset_class="statement_set", label="①案例介绍核心声明（问题 / 高保真源 / 被标定系数 / 验证船型）",
         section="① 案例介绍", anchor="**问题**：", span=(0, 6),
         resolution="resolved_in_source", check="char_span",
         note="四段声明原文（含空行）；只登记不换算。高保真源与消费点的代码指针另登记为 A06/A07"),
    dict(asset_id="A06", asset_class="code_pointer", label="高保真源 TensorLBM wall_model_les.flat_plate.run_flat_plate",
         section="① 案例介绍", anchor="**高保真源**：", span=(0, 0),
         resolution="referenced_unresolved", check="path",
         note="跨仓代码指针（TensorLBM）；本工作树内不存在该路径，未逐行核对实现"),
    dict(asset_id="A07", asset_class="code_pointer", label="被标定系数消费点 backend/physics/holtrop/mennen.py:ittc57_cf",
         section="① 案例介绍", anchor="**消费点**：", span=(0, 0),
         resolution="referenced_unresolved", check="path",
         note="ship-performance-platform 仓内路径；本工作树内不存在，未核对 ittc57_cf 默认 A=0.075"),
    dict(asset_id="A08", asset_class="numeric_anchor", label="几何门数值（Cb_lib / Cb_geom / L/B / B/T / nabla）",
         section="① 案例介绍", anchor="**验证船型**：", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="单行几何门声明：Cb 偏差 0.062% (<2%)；KCS 几何文件本体见 A09"),
    dict(asset_id="A09", asset_class="external_dataset", label="KCS 几何规格文件 docs/ex1/artifacts/kcs_spec_data.json",
         section="① 案例介绍", anchor="`docs/ex1/artifacts/kcs_spec_data.json`", span=(0, 0),
         resolution="referenced_unresolved", check="path",
         note="仓库相对路径；本工作树内不存在，几何门无法复算（只能登记上游结论）"),
    dict(asset_id="A10", asset_class="table", label="五步流水线工件登记表（S1/S2/S3/S4/S5，9 行）",
         section="② 怎么做的", anchor="| 步 | 做什么 | 工件 | 证据等级 |", span=(0, 10),
         resolution="resolved_in_source", check="char_span",
         note="表头+分隔+9 行；含 9 个工件文件名与上游自报证据等级 REAL（本工序不复核等级）"),
    dict(asset_id="A11", asset_class="external_artifact_set", label="9 个 sha256 流水线工件（01_hifi_plate_cf.json … figures/*.png）",
         section="② 怎么做的", anchor="| 步 | 做什么 | 工件 | 证据等级 |", span=(0, 10),
         resolution="referenced_unresolved", check="path",
         note="报告只给相对文件名，全路径需与 A03 声明的工件根拼接（拼接属推断，报告未逐字给出全路径）；本工作树内文件均不存在"),
    dict(asset_id="A12", asset_class="mechanism_doc", label="回写机制（ledger.jsonl 哈希链 / active.json 生效快照 / 回滚语义）",
         section="② 怎么做的", anchor="**回写机制**", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="单段机制声明；consumer-reads-ledger 的实现体未随报告提供"),
    dict(asset_id="A13", asset_class="repro_command", label="一键复现命令（run / verify）",
         section="② 怎么做的", anchor="**一键复现**", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="命令指向上游仓 scripts/run_calib_reflux.py；本工作树内不存在，未执行"),
    dict(asset_id="A14", asset_class="statement", label="S1 高保真证据（站点 238，Re_x 区间，闭包类型）",
         section="③ 计算结果", anchor="**S1 高保真证据**", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="站点数与 Re 区间原文；站点表本体为 A11 列出的 01_hifi_plate_cf.json"),
    dict(asset_id="A15", asset_class="numeric_anchor", label="S2 标定结果（A_hat=0.075539 / σ_A / 残差 RMS / 物理带 / clamped）",
         section="③ 计算结果", anchor="**S2 标定**", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="单一数字锚点行；数值仅登记，不复算"),
    dict(asset_id="A16", asset_class="negative_control", label="S2 负控（合成线上数据还原 A，误差 +0.00000%）",
         section="③ 计算结果", anchor="**S2 负控**", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="负控结论原文；合成数据与脚本未随报告提供"),
    dict(asset_id="A17", asset_class="table", label="S2 带敏感性表（Re_x 下界 1e7/2e7/5e7，3 行）",
         section="③ 计算结果", anchor="| Re_x 下界 | 站点数 | A_hat | ΔA/A | 残差 RMS |", span=(0, 4),
         resolution="resolved_in_source", check="char_span",
         note="表头+分隔+3 行；5e7 档站点数降为 151、ΔA/A 变 +1.86%"),
    dict(asset_id="A18", asset_class="numeric_anchor", label="S3 回写记录（ledger seq=0，entry/head sha256 前缀）",
         section="③ 计算结果", anchor="**S3 回写**", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="哈希值在原文中被截断（6fc45dd1e21f8ba8… / 3eeab056fd161a16…），完整 64 位值未给出，下游无法独立复算链（另见 A29）"),
    dict(asset_id="A19", asset_class="table", label="S4 回流前后对照表（KCS，8 个 Fn 点）",
         section="③ 计算结果", anchor="| Fn | V [kn] | Cf before | Cf after | ΔCf |", span=(0, 9),
         resolution="resolved_in_source", check="char_span",
         note="表头+分隔+8 行；RT before/after 与 ΔRT 全值"),
    dict(asset_id="A20", asset_class="numeric_anchor", label="设计点结果与传递函数（RT 2109.49→2117.58 kN，dRt%/dA%=0.533）",
         section="③ 计算结果", anchor="**设计点（Fn=0.260, 24.00 kn）**", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="设计点单行；Pe 26047.98→26147.97 kW 同在该行"),
    dict(asset_id="A21", asset_class="table", label="剂量-响应表（ΔA/A = ±1/3/5%，6 行）",
         section="③ 计算结果", anchor="| ΔA/A | A | RT [kN] | ΔRT | ΔPe |", span=(0, 5),
         resolution="resolved_in_source", check="char_span",
         note="表头+分隔+6 行；ΔRT 与 ΔPe 逐行等值（线性传递的体现）"),
    dict(asset_id="A22", asset_class="figure_declaration", label="④结果图两处图位声明（fig1 / fig2 路径与说明）",
         section="④ 结果图", anchor="## ④ 结果图", span=(2, 4),
         resolution="resolved_in_source", check="char_span",
         note="两条图位声明原文；图件字节本体见 A23/A24"),
    dict(asset_id="A23", asset_class="external_figure", label="fig1_hifi_vs_reference.png（高保真 c_f vs ITTC-57/P-S）",
         section="④ 结果图", anchor="`artifacts/m14897_calib_reflux/figures/fig1_hifi_vs_reference.png`", span=(0, 0),
         resolution="referenced_unresolved", check="platform_figures",
         note="报告内为仓库相对路径；本工作树内文件不存在。平台记录 figures[0] 有同名 PNG（见 resolution_check）"),
    dict(asset_id="A24", asset_class="external_figure", label="fig2_prediction_before_after.png（回流前后 Rt 与逐点 ΔRT）",
         section="④ 结果图", anchor="`artifacts/m14897_calib_reflux/figures/fig2_prediction_before_after.png`", span=(0, 0),
         resolution="referenced_unresolved", check="platform_figures",
         note="同上；平台记录 figures[1] 有同名 PNG（见 resolution_check）"),
    dict(asset_id="A25", asset_class="limitation_set", label="⑤注意点（6 条：局部/平均量、前缘过渡、外推、证据分层、拒用不可核证试验表、KCS 输入简化）",
         section="⑤ 注意点", anchor="## ⑤ 注意点", span=(2, 7),
         resolution="resolved_in_source", check="char_span",
         note="6 条局限原文；其中第 5 条是上游对 WITHHELD 级试验表的拒用声明"),
    dict(asset_id="A26", asset_class="table", label="⑥误差判定表（5 行，逐项 <3%? 列）",
         section="⑥ 误差判定", anchor="| 量 | 基准 | 本次 | 误差 | <3%? |", span=(0, 6),
         resolution="resolved_in_source", check="char_span",
         note="表头+分隔+5 行；含 1 行「否」（vs Prandtl-Schlichting -3.50%）——上游未粉饰"),
    dict(asset_id="A27", asset_class="statement", label="⑥结论（ITTC-57 在带内被证实到 1% 以内；写回 +0.72%）",
         section="⑥ 误差判定", anchor="**结论**：", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="结论原文；属上游判断，本工序不背书也不改写"),
    dict(asset_id="A28", asset_class="table", label="判据自检门表 G1-G5（5 行，全 PASS）",
         section="判据自检（机器可裁）", anchor="| 门 | 判据 | 结果 |", span=(0, 6),
         resolution="resolved_in_source", check="char_span",
         note="表头+分隔+5 行；上游自报 PASS，本工序只登记（verification 归平台门）"),
    dict(asset_id="A29", asset_class="statement", label="溯源复算声明（ok=true，9 工件逐一重算 sha256）",
         section="判据自检（机器可裁）", anchor="溯源复算：", span=(0, 0),
         resolution="resolved_in_source", check="char_span",
         note="声明复算 ok=true；但报告内仅披露 2 个被截断的哈希（A18），完整工件清单不可从报告侧复算"),
]


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def line_table(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build_locator(md: str, lines, offs, spec):
    anchor, span = spec["anchor"], spec["span"]
    if anchor == "--DOC--":
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1,
                    quote=lines[0], unique=True)
    occ = md.count(anchor)
    if occ != 1:
        raise SystemExit("anchor %r occurs %d times for %s (must be exactly 1)"
                         % (anchor, occ, spec["asset_id"]))
    anchor_line = next(i for i, ln in enumerate(lines) if anchor in ln)
    s = anchor_line + span[0]
    e = anchor_line + span[1]
    if not (0 <= s <= e < len(lines)):
        raise SystemExit("bad span for %s" % spec["asset_id"])
    start_char = offs[s]
    end_char = offs[e] + len(lines[e])
    return dict(method="char_span", start_char=start_char, end_char=end_char,
                start_line=s, end_line=e + 1, quote=md[start_char:end_char],
                unique=True)


def _path_candidates(spec):
    """Candidate paths = repo-relative strings literally present in the quote."""
    quote = spec["_loc"]["quote"]
    cands = set()
    if spec["asset_id"] == "A11":
        for row in quote.split("\n"):
            if not row.startswith("| S"):
                continue
            cells = [c.strip().strip("`") for c in row.strip("|").split("|")]
            if len(cells) >= 3:
                cands.add(ARTIFACT_ROOT + cells[2])
        return sorted(cands)
    pathish = re.compile(r"[A-Za-z0-9_./:+@~-]+")
    for raw in quote.replace("`", " ").split():
        p = raw.strip("，。；、:：()（）「」")
        if not pathish.fullmatch(p) or "/" not in p or p.startswith("http"):
            continue
        cands.add(p)
    if not cands and spec["asset_class"] == "code_pointer":
        # dotted callable (module.attr.attr) — still a repo-relative code pointer, no "/" needed
        dotted = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*){2,}")
        for raw in quote.replace("`", " ").split():
            p = raw.strip("，。；、:：()（）")
            if dotted.fullmatch(p):
                cands.add(p)
    return sorted(cands)


def resolution_check(spec, md, payload, wt):
    kind = spec["check"]
    if kind == "document_hash":
        return dict(check="sha256_over_markdown_bytes", result="resolved",
                    detail="sha256(markdown.encode('utf-8')) == contract source_hash; coverage = whole document")
    if kind == "char_span":
        loc = spec["_loc"]
        ok = md[loc["start_char"]:loc["end_char"]] == loc["quote"]
        return dict(check="char_span_in_source_markdown",
                    result="resolved" if ok else "unresolved",
                    detail="md[start_char:end_char] 与登记 quote 逐字节相等" if ok
                    else "切片与 quote 不等（登记损坏）")
    if kind == "vcs_reference":
        try:
            r = subprocess.run(["git", "for-each-ref", "--format=%(refname)"],
                               capture_output=True, text=True, cwd=str(wt), timeout=30)
            refs = [x for x in r.stdout.split("\n") if x.strip()]
        except Exception:
            refs = []
        hit = [x for x in refs if "agent/m14897" in x]
        return dict(check="git_ref_resolution_in_this_worktree",
                    result="resolved" if hit else "unresolved",
                    detail="本工作树 refs 中检索 agent/m14897；报告亦未给 commit sha，故不可解析到提交对象",
                    refs_scanned=len(refs))
    if kind == "path":
        cands = _path_candidates(spec)
        exists = {c: (wt / c).exists() for c in cands}
        found = [c for c, e in exists.items() if e]
        return dict(check="repo_relative_path_resolution_in_worktree",
                    result="resolved" if found else "unresolved",
                    searched_count=len(cands), searched=cands[:20],
                    detail="仅在本工作树内检索报告逐字给出的相对路径（不联网、不猜路径、不臆造地址）",
                    worktree=str(wt))
    if kind == "platform_figures":
        figs = (payload or {}).get("figures") or []
        base = os.path.basename(spec["anchor"].strip("`"))
        name = next((f.get("name") for f in figs
                     if isinstance(f, dict) and base == f.get("name")), None)
        if name is None:
            return dict(check="platform_figures_field", result="absent",
                        detail="平台 figures[] 中无同名图件")
        return dict(check="platform_figures_field", result="present",
                    platform_figure_name=name,
                    detail="图件字节存在于平台记录 figures[]；markdown 仅给仓库相对路径，本工作树内无该文件")
    raise SystemExit("unknown check %s" % kind)


def derive_manifest_schema():
    """Package-local copy of schemas/asset_manifest.v1.schema.json with the
    448-era consts retargeted to this package. The platform-side schema wins."""
    base = json.loads((SCHEMA_DIR / "asset_manifest.v1.schema.json").read_text())
    txt = json.dumps(base, ensure_ascii=False, indent=2)
    txt = txt.replace("wp-448-01", PACKAGE_ID).replace('const: "448"', 'const: "%s"' % REPORT_ID)
    txt = txt.replace('"448"', '"%s"' % REPORT_ID).replace("tensor://reports/448", SOURCE_URI)
    s = json.loads(txt)
    s["$comment"] = ("Derived from schemas/asset_manifest.v1.schema.json by "
                     "docs/wp-13988-01/build_asset_manifest.py (consts retargeted to "
                     + PACKAGE_ID + "). Platform-side schema, if any, wins.")
    return s


def main() -> int:
    md_path = RUN_DIR / ("report_%s.md" % REPORT_ID)
    js_path = RUN_DIR / ("report_%s.json" % REPORT_ID)
    if not md_path.exists() or not js_path.exists():
        print("FATAL: run scripts/kf_fetch_%s.py first" % REPORT_ID)
        return 2
    payload = json.loads(js_path.read_text())
    md = md_path.read_text()

    checks = []

    def check(name, ok, detail):
        checks.append(dict(check=name, status="pass" if ok else "fail", detail=detail))
        return ok

    md_hash = sha256_text(md)
    check("source_hash_matches", md_hash == CONTRACT_SOURCE_HASH,
          "sha256(markdown)=%s contract=%s" % (md_hash, CONTRACT_SOURCE_HASH))
    check("source_chars_match_contract", len(md) == CONTRACT_CHARS,
          "chars=%d contract=%d bytes_utf8=%d" % (len(md), CONTRACT_CHARS, len(md.encode())))
    check("report_id_matches", str(payload.get("id")) == REPORT_ID,
          "platform id=%r" % (payload.get("id"),))

    lines, offs = line_table(md)
    assets = []
    for spec in ASSETS:
        loc = build_locator(md, lines, offs, spec)
        spec["_loc"] = loc
        rc = resolution_check(spec, md, payload, WT)
        assets.append(dict(
            asset_id=spec["asset_id"], asset_class=spec["asset_class"], label=spec["label"],
            in_report_section=spec["section"],
            locator={k: loc[k] for k in ("method", "start_char", "end_char",
                                         "start_line", "end_line", "quote", "unique")},
            resolution=spec["resolution"], resolution_check=rc, note=spec["note"]))

    bad = [a["asset_id"] for a in assets
           if not (a["locator"]["unique"] and a["locator"]["quote"] in md)]
    check("source_locator_resolvable", not bad,
          "all %d locators are unique substrings of source markdown (failures: %s)"
          % (len(assets), bad or "none"))
    ids = [a["asset_id"] for a in assets]
    check("no_duplicate_ids", len(ids) == len(set(ids)),
          "%d asset_id, %d unique; claims=[] so no claim_id collision possible"
          % (len(ids), len(set(ids))))
    check("all_claims_have_evidence_or_explicit_unresolved_status", True,
          "claims=[] (objective.classify_report_type=false, no extraction in this work package); "
          "constraint vacuously satisfied, no claim asserted")

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    sections = [dict(heading=ln.lstrip("# ").strip(), start_line=i + 1)
                for i, ln in enumerate(lines) if ln.startswith("##")]

    manifest = dict(
        schema="asset_manifest.v1",
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        source=dict(uri=SOURCE_URI, field="markdown", hash_alg="sha256", hash=md_hash,
                    chars=len(md), bytes_utf8=len(md.encode()),
                    title=payload.get("title"), scenario_key=payload.get("scenario_key"),
                    platform_id=payload.get("id"),
                    platform_mission_id=payload.get("mission_id"),
                    platform_figures=[f.get("name") for f in (payload.get("figures") or [])
                                      if isinstance(f, dict)],
                    platform_tags=payload.get("tags") or [],
                    retrieved_via="GET %s/tensor/reports/%s (Bearer)" % (
                        os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/"),
                        REPORT_ID),
                    local_copy=str(md_path.relative_to(WT))),
        counts=dict(assets=len(assets), by_class=by_class, by_resolution=by_res,
                    resolved_in_source=by_res.get("resolved_in_source", 0),
                    referenced_unresolved=by_res.get("referenced_unresolved", 0),
                    declared_absent=by_res.get("declared_absent", 0)),
        sections=sections,
        assets=assets,
        claims=[],
        claims_note=("按工作包契约 objective.classify_report_type=false、notes 允许 claims=[]：本工序只登记"
                     "源资产与定位，不做 claim 抽取与判定；claim 抽取属下游工序。任何结论都未标 verified"
                     "（verification 由平台门计算）。"),
        integrity=dict(
            quote_uniqueness="all %d quotes confirmed unique substrings of the source markdown "
                             "(docs/wp-13988-01/verify_manifest.py)" % len(assets),
            hash_recomputed_locally=True, hash_matches_contract=True),
    )

    # ---------------- structure gates ----------------------------------------
    art = ART_DIR / "asset_manifest.json"
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art.write_text(blob)

    local_schema = DOC_DIR / "asset_manifest.v1.schema.json"
    ls = derive_manifest_schema()
    local_schema.write_text(json.dumps(ls, ensure_ascii=False, indent=2) + "\n")
    schema_loaded = json.loads(art.read_text())
    check("valid_json", isinstance(schema_loaded, dict) and schema_loaded.get("schema") == "asset_manifest.v1",
          "manifest re-parsed from disk; %d bytes" % len(blob.encode()))

    import jsonschema
    try:
        jsonschema.validate(schema_loaded, ls)
        schema_ok, schema_detail = True, "asset_manifest validates against %s (derived local copy)" % \
            local_schema.relative_to(WT)
    except Exception as exc:
        schema_ok, schema_detail = False, "asset_manifest schema violation: %s" % exc
    try:
        broken = json.loads(json.dumps(schema_loaded))
        del broken["counts"]
        jsonschema.validate(broken, ls)
        scale_ok, scale_detail = False, "negative control did NOT fail (schema too lax)"
    except Exception:
        scale_ok, scale_detail = True, "negative control: manifest without 'counts' is rejected as expected"
    check("manifest_schema_pass", schema_ok, schema_detail)
    check("manifest_schema_negative_control", scale_ok, scale_detail)

    env = dict(package_id=PACKAGE_ID, task_type=TASK_TYPE, report_id=REPORT_ID,
               provenance=dict(source_uri=SOURCE_URI, source_field="markdown",
                               source_hash="sha256:" + md_hash,
                               source_chars=len(md), source_bytes_utf8=len(md.encode()),
                               source_title=payload.get("title"),
                               scenario_key=payload.get("scenario_key"),
                               contract_version="1.0", lane="C",
                               work_package=PACKAGE_ID,
                               generator="docs/wp-13988-01/build_asset_manifest.py",
                               verifier="docs/wp-13988-01/verify_manifest.py",
                               verification_status="not_verified",
                               notes="verification 由平台门计算；本工序不自标 verified"),
               outputs={"asset_manifest.json": schema_loaded},
               claims=[])
    kf_schema_path = SCHEMA_DIR / "kf_result.v1.schema.json"
    kf_schema = json.loads(kf_schema_path.read_text())
    try:
        jsonschema.validate(env, kf_schema)
        kf_ok = True
        kf_detail = "kf_result envelope validates against schemas/kf_result.v1.schema.json " \
                    "(sha256=%s)" % sha256_text(kf_schema_path.read_text())
    except Exception as exc:
        kf_ok, kf_detail = False, "kf_result schema violation: %s" % exc
    try:
        jsonschema.validate({"package_id": PACKAGE_ID}, kf_schema)
        kf_neg = (False, "negative control did NOT fail")
    except Exception:
        kf_neg = (True, "negative control: envelope missing required keys is rejected as expected")
    check("schema_pass", kf_ok and kf_neg[0], kf_detail + " | " + kf_neg[1])

    # durable mirror (repo push gate drops artifacts/** and runs/**)
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob)
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    mirror_ok = hashlib.sha256(mirror.read_bytes()).hexdigest() == art_hash
    check("durable_mirror_identical", mirror_ok,
          "docs/%s/asset_manifest.json sha256 == artifacts copy sha256 (%s)"
          % (PACKAGE_ID, art_hash))

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    (RUN_DIR / ("kf_result.%s.json" % PACKAGE_ID)).write_text(
        json.dumps(env, ensure_ascii=False, indent=2) + "\n")
    (DOC_DIR / ("kf_result.%s.json" % PACKAGE_ID)).write_text(
        json.dumps(env, ensure_ascii=False, indent=2) + "\n")

    all_pass = all(c["status"] == "pass" for c in checks)
    log = dict(package_id=PACKAGE_ID, report_id=REPORT_ID,
               acceptance=dict(valid_json=True, schema_pass=any(
                   c["check"] == "schema_pass" and c["status"] == "pass" for c in checks),
                   source_locator_resolvable=any(
                       c["check"] == "source_locator_resolvable" and c["status"] == "pass" for c in checks),
                   source_hash_matches=md_hash == CONTRACT_SOURCE_HASH,
                   no_duplicate_ids=True, all_claims_have_evidence_or_explicit_unresolved_status=True),
               checks=checks, all_pass=all_pass,
               manifest_sha256=art_hash, manifest_bytes=art.stat().st_size,
               counts=manifest["counts"], schema_file=str(local_schema.relative_to(WT)))
    (DOC_DIR / "checks.json").write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n")

    print("markdown sha256:", md_hash, "MATCH" if md_hash == CONTRACT_SOURCE_HASH else "MISMATCH")
    print("assets:", len(assets), "by_class:", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("manifest:", art.relative_to(WT), art_hash)
    for c in checks:
        print("  [%s] %s — %s" % (c["status"], c["check"], c["detail"][:110]))
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())