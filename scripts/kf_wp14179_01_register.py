#!/usr/bin/env python3
"""KF work package wp-14179-01 (task_type=01-asset-registration) for report_id=14179.

Registers the source asset (report markdown bytes) and every resolvable
attachment / artifact reference / in-body block of that ONE report.
No extraction, no classification, no claim generation, nothing marked verified.

Inputs (fetched, never hand-copied):
  GET $TENSOR_API_BASE/tensor/reports/14179   (Bearer = login from TENSOR_AGENT_USER/PASS)

Outputs:
  artifacts/wp-14179-01/asset_manifest.json                 contract output
  docs/kf/wp-14179-01/asset_manifest.json                   durable mirror (pushed; artifacts/** is dropped by the push gate)
  docs/kf/wp-14179-01/{kf_result.json,locator_check.json,source.md,sha256.txt}
  docs/kf/wp-14179-01/{figure1_asset_coverage.png,report_body.md}
  runs/wp-14179-01/{report_14179.json,report_14179.md,kf_result.wp-14179-01.json}

Usage: python3 scripts/kf_wp14179_01_register.py [--no-publish]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

REPORT_ID = "14179"
PACKAGE_ID = "wp-14179-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_VERSION = "1.0"
LANE = "B"
MISSION_ID = 15783
SOURCE_URI = "tensor://reports/" + REPORT_ID
EXPECTED_HASH = "2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315"
EXPECTED_CHARS = 5506
EXPECTED_TITLE = ("交差审计 m14897 H5-CALIB-REFLUX：三件套重跑通过、A_hat 0.075539(+0.72%)"
                  "/RT +0.384% → verdict L5")
EXPECTED_SCENARIO = "calib_reflux_audit"

RUN_DIR = pathlib.Path("runs/wp-14179-01")
ART_DIR = pathlib.Path("artifacts/wp-14179-01")
DOC_DIR = pathlib.Path("docs/kf/wp-14179-01")

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

# ---------------------------------------------------------------------------
# Asset anchor table.
#   anchor = substring that must occur EXACTLY ONCE in the source markdown
#            (the machinery fails loudly otherwise -> no hand counting);
#   span   = (first_line_offset, last_line_offset) relative to the anchor line;
#   probe  = what the machine-checkable resolution_check does.
# ---------------------------------------------------------------------------
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告 markdown 全文（源资产本体）",
         anchor="--doc--", span=(0, -1), resolution="resolved_in_source", probe="document",
         note="整篇 markdown 即源资产；sha256 见 source.hash（与契约 source_hash 逐字节比对）"),
    dict(asset_id="A02", asset_class="heading", label="报告一级标题",
         anchor="# 交差审计：m14897 H5-CALIB-REFLUX", span=(0, 0),
         resolution="resolved_in_source", probe="span",
         note="标题行；与记录 title 字段同源（见 provenance.title_matches_contract）"),
    dict(asset_id="A03", asset_class="vcs_reference",
         label="上游 mission/commit/PR 三元组（m14897 / 2eb994ce1 / PR #935）",
         anchor="PR **#935** merged", span=(-1, 1), resolution="referenced_unresolved",
         probe="git_object", git_object="2eb994ce1",
         note="上游仓库提交号；TensorKnowledge 对象库中不存在，本工序不推断其内容"),
    dict(asset_id="A04", asset_class="code_pointer", label="被审计消费点 mennen.py:ittc57_cf",
         anchor="`backend/physics/holtrop/mennen.py:ittc57_cf`", span=(-1, 0),
         resolution="referenced_unresolved", probe="paths",
         paths=["backend/physics/holtrop/mennen.py"], repo="ship-performance-platform",
         note="代码指针（仓库+文件+符号）；本工作树无该仓库"),
    dict(asset_id="A05", asset_class="numeric_anchor",
         label="被标定系数 ITTC57_A = 0.075 与其覆盖入口 Holtrop1984Input.cf_line_A",
         anchor="**被标定系数**", span=(0, 1), resolution="resolved_in_source", probe="span",
         note="系数声明 + 消费入口原文；数值只登记不换算"),
    dict(asset_id="A06", asset_class="code_pointer",
         label="高保真源 TensorLBM wall_model_les.flat_plate.run_flat_plate",
         anchor="**高保真源**", span=(0, 2), resolution="referenced_unresolved", probe="paths",
         paths=["wall_model_les/flat_plate.py", "TensorLBM/wall_model_les/flat_plate.py"],
         repo="TensorLBM",
         note="外部仓模块路径；报告以点路径给出，非本仓可解析地址"),
    dict(asset_id="A07", asset_class="geometry_declaration",
         label="KCS 几何前置门数值（Cb_lib/nabla/L/B/T 比值）",
         anchor="**验证船型**", span=(0, 1), resolution="resolved_in_source", probe="span",
         note="几何门数值原文；本工序不复核"),
    dict(asset_id="A08", asset_class="artifact_set",
         label="上游 run_artifacts 9 工件清单（artifacts/m14897_calib_reflux/）",
         anchor="**run_artifacts 复核**", span=(0, 3), resolution="referenced_unresolved",
         probe="paths", paths=["artifacts/m14897_calib_reflux/"],
         repo="ship-performance-platform",
         note="工件目录与 9 个文件名清单；本工作树内不存在"),
    dict(asset_id="A09", asset_class="measurement_record",
         label="重跑实测数字块（A_hat=0.07553932521 / RT 2109.49→2117.58 kN / 传递函数 0.533 / 负控 +0.00000%）",
         anchor="**benchmark ref vs got 复核**", span=(0, 3),
         resolution="resolved_in_source", probe="span",
         note="上游自报实测值；只登记原文，不做独立复算（本工序无上游代码）"),
    dict(asset_id="A10", asset_class="command", label="repro_cmd 与其执行证据（run + verify）",
         anchor="**repro_cmd 可执行**", span=(0, 1), resolution="referenced_unresolved",
         probe="paths", paths=["scripts/run_calib_reflux.py"],
         repo="ship-performance-platform",
         note="复现命令可执行性来自上游报告；脚本本体不在本工作树，未执行"),
    dict(asset_id="A11", asset_class="test_suite",
         label="单测文件 backend/tests/test_calib_reflux.py 与 17 passed",
         anchor="**单测重跑**", span=(0, 1), resolution="referenced_unresolved", probe="paths",
         paths=["backend/tests/test_calib_reflux.py"], repo="ship-performance-platform",
         note="测试文件不在本工作树；本工序未重跑该测试（避免以未跑宣称通过）"),
    dict(asset_id="A12", asset_class="gate_check",
         label="maturity_gate.judge 自检（claimed L5 → 7 键全过）",
         anchor="**判级+网关自检**", span=(0, 1), resolution="referenced_unresolved",
         probe="paths", paths=["maturity_gate.py"], repo="ship-performance-platform",
         note="网关实现体与运行结果均为上游产物；本工序只登记声明"),
    dict(asset_id="A13", asset_class="dataset_stats",
         label="S1 高保真证据统计（站点数 238、Re_x 区间）",
         anchor="**S1 高保真证据**", span=(0, 0), resolution="resolved_in_source", probe="span",
         note="数据集统计摘要；数据本体为 A08 工件，未在本仓"),
    dict(asset_id="A14", asset_class="parameter_set",
         label="S2 标定结果（A_hat、σ_A、残差 RMS/max、物理带、clamped、带敏感性）",
         anchor="**S2 标定**", span=(0, 2), resolution="resolved_in_source", probe="span",
         note="标定参数与不确定度原文；数值仅登记"),
    dict(asset_id="A15", asset_class="ledger_record",
         label="S3 回写账本记录（seq=0、entry_sha256、生效快照 head_sha256）",
         anchor="**S3 回写**", span=(0, 1), resolution="resolved_in_source", probe="span",
         note="账本哈希为截断展示（…）；登记原文，不补全"),
    dict(asset_id="A16", asset_class="table",
         label="S4 回流前后对照表（表头 8 列 + 8 个 Fn 数据行）",
         anchor="**S4 回流前后对照**", span=(0, 11), resolution="resolved_in_source", probe="span",
         note="只登记表结构（含引文全文），不抽取数值到知识对象"),
    dict(asset_id="A17", asset_class="numeric_anchor",
         label="设计点结论数字（Fn=0.260 RT/Pe 变化量、传递函数 dRt%/dA%）",
         anchor="**设计点（Fn=0.260, 24.00 kn）**", span=(0, 1),
         resolution="resolved_in_source", probe="span",
         note="设计点派生数字原文；与 A16 表格同源"),
    dict(asset_id="A18", asset_class="figure", label="图1 fig1_hifi_vs_reference.png（高保真局部摩阻 vs 参考线）",
         anchor="figures/fig1_hifi_vs_reference.png", span=(0, 1),
         resolution="resolved_in_source", probe="figure",
         figure_name="fig1_hifi_vs_reference.png",
         note="记录 figures[] 内含同名 png 元数据（name+caption），正文给出路径"),
    dict(asset_id="A19", asset_class="figure", label="图2 fig2_prediction_before_after.png（回流前后 KCS 总阻力曲线）",
         anchor="figures/fig2_prediction_before_after.png", span=(0, 1),
         resolution="resolved_in_source", probe="figure",
         figure_name="fig2_prediction_before_after.png",
         note="记录 figures[] 内含同名 png 元数据（name+caption），正文给出路径"),
    dict(asset_id="A20", asset_class="limitation_set",
         label="注意点 1–6（局部/平均恒等式、前缘过渡段、外推、证据分层、WITHHELD 拒用、审计侧记账）",
         anchor="## ⑤ 注意点", span=(2, 16), resolution="resolved_in_source", probe="span",
         note="六条坑/局限原文；含 WITHHELD 级外部试验表被拒用的判据"),
    dict(asset_id="A21", asset_class="table", label="误差判定表（5 行，含显式 <3%? 回答）",
         anchor="| 量 | 基准 | 本次 | 误差 | <3%? |", span=(0, 6),
         resolution="resolved_in_source", probe="span",
         note="上游误差表原文；本工序不复核其结论"),
    dict(asset_id="A22", asset_class="statement", label="结论段（机制证明 + 1% 以内一致性）",
         anchor="**结论**：高保真数值解与 ITTC-57", span=(0, 3),
         resolution="resolved_in_source", probe="span",
         note="上游结论原文，按约束保持为未验证陈述"),
    dict(asset_id="A23", asset_class="statement", label="L0–L5 判级依据清单",
         anchor="## 判级（L0–L5 功能实质）", span=(2, 10),
         resolution="resolved_in_source", probe="span", note="六档判级的逐条依据原文"),
    dict(asset_id="A24", asset_class="verdict", label="verdict = L5 与其诚实注记",
         anchor="**verdict = L5**", span=(0, 1), resolution="resolved_in_source", probe="span",
         note="上游 verdict；本工序不背书、不改写、不标 verified"),
    dict(asset_id="A25", asset_class="deliverable_set",
         label="本单工件三路径（docs/m15056_audit_m14897.md、artifacts 目录、reports 证据 json）",
         anchor="**工件**：`docs/m15056_audit_m14897.md`", span=(0, 2),
         resolution="referenced_unresolved", probe="paths",
         paths=["docs/m15056_audit_m14897.md", "artifacts/m15056_audit_m14897/",
                "reports/m15056_verdict_evidence.json"],
         repo="ship-performance-platform",
         note="相对路径；本工作树（TensorKnowledge）内不存在，属上游仓产物"),
    dict(asset_id="A26", asset_class="external_worktree",
         label="审计侧记账：m14897 / m15056 两个 worktree 绝对路径与 ECO 主 checkout 陈旧声明",
         anchor="6. **审计侧记账**", span=(0, 2), resolution="referenced_unresolved",
         probe="abs_paths",
         abs_paths=["/root/tp-agent/work/m14897",
                    "/root/tp-agent/work/m15056/artifacts/m15056_audit_m14897/"],
         note="宿主机绝对路径；host 探针结果仅作信息位，跨机器不可复现"),
    dict(asset_id="A27", asset_class="code_pointer",
         label="回流管线脚本 scripts/run_calib_reflux.py（run/verify 入口）",
         anchor="**repro_cmd 可执行**：`python scripts/run_calib_reflux.py run`", span=(0, 0),
         resolution="referenced_unresolved", probe="paths",
         paths=["scripts/run_calib_reflux.py"], repo="ship-performance-platform",
         note="命令引用的脚本本体；本工作树无此文件"),
]


# --------------------------------------------------------------------------- io
def _req(url: str, body=None, token=None, timeout=90):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


def login():
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        raise SystemExit("FATAL: TENSOR_AGENT_USER / TENSOR_AGENT_PASS not set")
    _, d = _req(BASE + "/auth/login", {"username": user, "password": pwd})
    tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
    if not tok:
        raise SystemExit("FATAL: no access_token in login response")
    return tok


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def line_offsets(md: str):
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build_locator(md, lines, offs, anchor, span):
    if anchor == "--doc--":
        return dict(method="document", start_char=0, end_char=len(md), start_line=0,
                    end_line=len(lines) - 1, quote=md, unique=True, occurrences=1)
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"FATAL anchor {anchor!r}: {len(hits)} hits (need exactly 1)")
    a = hits[0]
    i0 = a + span[0]
    i1 = a + span[1]
    i1 = len(lines) - 1 if i1 < 0 else i1
    if i0 < 0 or i1 >= len(lines) or i1 < i0:
        raise SystemExit(f"FATAL span out of range for anchor {anchor!r}: {(i0, i1)}")
    start = offs[i0]
    end = offs[i1] + len(lines[i1])
    quote = md[start:end]
    return dict(method="char_span", start_char=start, end_char=end, start_line=i0,
                end_line=i1, quote=quote, unique=md.count(quote) == 1,
                occurrences=md.count(quote))


def section_of(lines, idx):
    head = "(document)"
    for ln in lines[: idx + 1]:
        if ln.startswith("#"):
            head = ln.strip()
    return head


# ------------------------------------------------------------------ resolution
def resolution_check(spec, loc, record):
    """Machine-checkable backing for the declared resolution status."""
    probe = spec["probe"]
    worktree = pathlib.Path(".").resolve()
    if probe == "document":
        return dict(check="char_span_covers_whole_markdown", result="resolved",
                    detail=f"start_char=0, end_char=len(markdown)={loc['end_char']}")
    if probe == "span":
        ok = md_slice_identity_ok(loc)
        return dict(check="quote_is_unique_substring_of_markdown", result="resolved" if ok else "unresolved",
                    detail="md[start_char:end_char]==quote 且 quote 在全文唯一出现",
                    quote_in_source=ok)
    if probe == "figure":
        names = [f.get("name") for f in (record.get("figures") or [])]
        present = spec["figure_name"] in names
        return dict(check="record_figures_name_lookup", result="present" if present else "absent",
                    figure_name=spec["figure_name"], record_figure_names=names,
                    payload_downloaded=False,
                    detail="只按记录 figures[].name 对齐，PNG 本体未下载/未入库")
    if probe == "git_object":
        try:
            r = subprocess.run(["git", "cat-file", "-e", spec["git_object"] + "^{commit}"],
                               cwd=str(worktree), capture_output=True, timeout=30)
            ok = r.returncode == 0
            return dict(check="git_cat_file_in_this_worktree", object=spec["git_object"],
                        result="resolved" if ok else "unresolved", exit_code=r.returncode,
                        detail="对象存在于本仓对象库才算 resolved；上游仓提交号在本仓不存在")
        except Exception as exc:  # pragma: no cover
            return dict(check="git_cat_file_in_this_worktree", object=spec["git_object"],
                        result="unresolved", error=str(exc))
    if probe == "paths":
        paths = spec["paths"]
        present = [p for p in paths if (worktree / p).exists()]
        missing = [p for p in paths if p not in present]
        return dict(check="worktree_relative_path_exists", result="unresolved" if missing else "resolved",
                    repo_declared=spec.get("repo"), paths=paths, present=present, missing=missing,
                    detail="按 TensorKnowledge 工作树根判定；报告引用的上游仓不在本工作树内")
    if probe == "abs_paths":
        probe_host = []
        for p in spec["abs_paths"]:
            probe_host.append(dict(path=p, exists_on_host=pathlib.Path(p).exists()))
        return dict(check="host_absolute_path_probe_informational", result="unresolved",
                    probes=probe_host,
                    detail=("绝对路径不属于 source_uri 可解析面；host 存在性仅作信息位，"
                            "换机即不可复现，故仍登记 referenced_unresolved"))
    raise SystemExit("FATAL unknown probe " + probe)


_CURRENT_MD = {"md": ""}


def md_slice_identity_ok(loc):
    md = _CURRENT_MD["md"]
    return md[loc["start_char"]:loc["end_char"]] == loc["quote"] and md.count(loc["quote"]) == 1


# ----------------------------------------------------------------------- figure
def make_coverage_figure(manifest) -> pathlib.Path:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    assets = manifest["assets"]
    colors = {"resolved_in_source": "#2b8a3e", "referenced_unresolved": "#c92a2a",
              "declared_absent": "#868e96"}
    fig, ax = plt.subplots(figsize=(11, 8.2))
    for i, a in enumerate(assets):
        loc = a["locator"]
        if loc["method"] == "document":
            ax.barh(i, loc["end_char"], left=0, height=0.72,
                    color=colors[a["resolution"]], alpha=0.25)
            ax.text(loc["end_char"] * 0.5, i, "A01 whole markdown (0..%d)" % loc["end_char"],
                    va="center", ha="center", fontsize=7.5, color="#333")
        else:
            w = max(loc["end_char"] - loc["start_char"], 1)
            ax.barh(i, w, left=loc["start_char"], height=0.72,
                    color=colors[a["resolution"]], alpha=0.9)
            ax.text(loc["end_char"] + 60, i, "L%d-%d" % (loc["start_line"] + 1, loc["end_line"] + 1),
                    va="center", fontsize=7, color="#495057")
    ax.set_yticks(range(len(assets)))
    ax.set_yticklabels(["%s %s" % (a["asset_id"], a["asset_class"]) for a in assets], fontsize=7.5)
    ax.invert_yaxis()
    ax.set_xlabel("character offset in source markdown (chars=%d)" % manifest["source"]["chars"])
    ax.set_title("wp-14179-01 asset registration coverage — report 14179 markdown\n"
                 "green = resolved_in_source, red = referenced_unresolved (external repo path)",
                 fontsize=10)
    ax.grid(axis="x", linestyle=":", alpha=0.5)
    ax.set_xlim(-200, manifest["source"]["chars"] * 1.08)
    fig.tight_layout()
    out = DOC_DIR / "figure1_asset_coverage.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


# ------------------------------------------------------------------------- main
def main() -> int:
    for d in (RUN_DIR, ART_DIR, DOC_DIR):
        d.mkdir(parents=True, exist_ok=True)

    tok = login()
    _, rec = _req(BASE + "/tensor/reports/" + REPORT_ID, token=tok)
    if isinstance(rec, dict) and isinstance(rec.get("data"), dict):
        rec = rec["data"]
    (RUN_DIR / f"report_{REPORT_ID}.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = rec["markdown"]
    _CURRENT_MD["md"] = md
    (RUN_DIR / f"report_{REPORT_ID}.md").write_text(md, encoding="utf-8")
    (DOC_DIR / "source.md").write_text(md, encoding="utf-8")

    md_hash = sha256_text(md)
    if md_hash != EXPECTED_HASH:
        raise SystemExit(f"FATAL markdown sha256 {md_hash} != contract {EXPECTED_HASH}")
    if len(md) != EXPECTED_CHARS:
        raise SystemExit(f"FATAL chars {len(md)} != contract {EXPECTED_CHARS}")
    title_matches = rec.get("title") == EXPECTED_TITLE
    scenario_matches = rec.get("scenario_key") == EXPECTED_SCENARIO

    lines, offs = line_offsets(md)

    assets, seen = [], set()
    for spec in ASSETS:
        aid = spec["asset_id"]
        if aid in seen:
            raise SystemExit(f"FATAL duplicate asset_id {aid}")
        seen.add(aid)
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"])
        if not loc["unique"]:
            raise SystemExit(f"FATAL quote not unique for {aid}: {spec['anchor']!r}")
        chk = resolution_check(spec, loc, rec)
        assets.append(dict(
            asset_id=aid,
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=section_of(lines, loc["start_line"]),
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=chk,
            note=spec["note"],
        ))

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    # structural block registry, computed from the registered quotes (no typed row counts)
    by_id = {a["asset_id"]: a for a in assets}
    pipe_tables = []
    for aid, name in (("A16", "S4 回流前后对照表"), ("A21", "误差判定表")):
        q_lines = by_id[aid]["locator"]["quote"].split("\n")
        tbl = [(i, ln) for i, ln in enumerate(q_lines) if ln.strip().startswith("|")]
        pipe_tables.append(dict(name=name, anchor_asset=aid,
                                header_cells=len(tbl[0][1].split("|")[1:-1]),
                                data_rows=len(tbl) - 2,   # minus header, minus |---| separator
                                start_line=by_id[aid]["locator"]["start_line"] + tbl[0][0],
                                registered_as="structure_only"))
    blocks = dict(pipe_tables=pipe_tables, fenced_code_blocks_none=True)

    manifest = dict(
        schema="asset_manifest.v1",
        blocks=blocks,
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        contract_version=CONTRACT_VERSION,
        report_id=REPORT_ID,
        lane=LANE,
        generator="scripts/kf_wp14179_01_register.py",
        source=dict(
            uri=SOURCE_URI,
            field="markdown",
            hash_alg="sha256",
            hash=md_hash,
            hash_expected=EXPECTED_HASH,
            hash_matches_contract=True,
            chars=len(md),
            chars_expected=EXPECTED_CHARS,
            chars_matches=True,
            chars_semantics="契约 chars = python str 长度（码点）；UTF-8 字节数另记（CJK 正文两者不同）",
            bytes_utf8=len(md.encode("utf-8")),
            title=rec.get("title"),
            scenario_key=rec.get("scenario_key"),
            platform_id=rec.get("id"),
            platform_mission_id=rec.get("mission_id"),
            platform_status=rec.get("status"),
            platform_created_at=rec.get("created_at"),
            platform_tags=rec.get("tags", []),
            platform_figures=[f.get("name") for f in (rec.get("figures") or [])],
            retrieved_via=f"GET {BASE}/tensor/reports/{REPORT_ID} (Bearer)",
            local_copy=str(RUN_DIR / f"report_{REPORT_ID}.md"),
        ),
        counts=dict(assets=len(assets), by_class=by_class, by_resolution=by_res,
                    resolved_in_source=by_res.get("resolved_in_source", 0),
                    referenced_unresolved=by_res.get("referenced_unresolved", 0),
                    declared_absent=by_res.get("declared_absent", 0)),
        assets=assets,
        claims=[],
        claims_note=("契约 objective.classify_report_type=false 且 notes 明确 claims 允许空数组："
                     "本工序只做资产登记与定位，不做 claim 抽取、不做类型分类、不标 verified"
                     "（verification 由平台门计算）；因此 claims 为空是合法完整结果，"
                     "acceptance 项 all_claims_have_evidence_or_explicit_unresolved_status 空真成立。"),
        boundary=dict(
            only_report_id=REPORT_ID,
            read_other_reports=False,
            modified_upstream_artifacts=False,
            marked_verified=False,
            extraction_done=False,
            classification_done=False,
        ),
    )

    art = ART_DIR / "asset_manifest.json"
    blob = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    art.write_text(blob, encoding="utf-8")
    mirror = DOC_DIR / "asset_manifest.json"
    mirror.write_text(blob, encoding="utf-8")
    art_hash = hashlib.sha256(art.read_bytes()).hexdigest()
    if hashlib.sha256(mirror.read_bytes()).hexdigest() != art_hash:
        raise SystemExit("FATAL durable mirror differs from artifact")

    locator_check = dict(
        package_id=PACKAGE_ID, report_id=REPORT_ID, source_hash="sha256:" + md_hash,
        markdown_chars=len(md),
        check="每条形如 md[start_char:end_char] == quote 且 md.count(quote) == 1",
        total=len(assets),
        passed=sum(1 for a in assets if md.count(a["locator"]["quote"]) == 1
                   and md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]),
        assets=[dict(asset_id=a["asset_id"], start_char=a["locator"]["start_char"],
                     end_char=a["locator"]["end_char"], start_line=a["locator"]["start_line"],
                     end_line=a["locator"]["end_line"], occurrences=a["locator"]["occurrences"])
                for a in assets],
    )
    (DOC_DIR / "locator_check.json").write_text(
        json.dumps(locator_check, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DOC_DIR / "sha256.txt").write_text(
        f"source markdown sha256: {md_hash}\n"
        f"source chars: {len(md)}  bytes_utf8: {len(md.encode('utf-8'))}\n"
        f"asset_manifest.json sha256: {art_hash}\n", encoding="utf-8")

    result = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        provenance=dict(
            source_uri=SOURCE_URI,
            source_field="markdown",
            source_hash="sha256:" + md_hash,
            source_chars=len(md),
            source_bytes_utf8=len(md.encode("utf-8")),
            source_title=rec.get("title"),
            title_matches_contract=title_matches,
            scenario_key=rec.get("scenario_key"),
            scenario_key_matches_contract=scenario_matches,
            contract_version=CONTRACT_VERSION,
            lane=LANE,
            producer="agent/m15783",
            generator="scripts/kf_wp14179_01_register.py",
            verifier="scripts/kf_wp14179_01_verify.py",
            retrieved_via=f"GET {BASE}/tensor/reports/{REPORT_ID} (Bearer)",
            notes=("source_hash 由 hashlib.sha256 over UTF-8 bytes of the markdown field 独立重算，"
                   "与契约 source_hash 逐字节一致；合约 chars=5506 与 len(markdown) 相同。"
                   "哈希相等仅为机械身份校验，本包不含任何 verified 结论——verification 由平台门计算。"),
            verification_status="not_verified",
        ),
        outputs={"asset_manifest.json": manifest},
        claims=[],
    )
    (RUN_DIR / f"kf_result.{PACKAGE_ID}.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (DOC_DIR / "kf_result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    fig_path = None
    try:
        fig_path = make_coverage_figure(manifest)
    except Exception as exc:  # keep going; report will state the reason
        print("figure skipped:", exc)

    print(json.dumps(dict(source_hash=md_hash, chars=len(md), assets=len(assets),
                          by_resolution=by_res, by_class=by_class,
                          manifest_sha256=art_hash,
                          locator_passed=locator_check["passed"],
                          figure=str(fig_path) if fig_path else None),
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())