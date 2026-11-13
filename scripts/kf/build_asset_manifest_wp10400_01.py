#!/usr/bin/env python3
"""wp-10400-01 (task_type=01-asset-registration): register the source assets of report 10400.

Scope, per the work-package contract:
  * input  : report_id=10400, source_field=markdown, source_hash=sha256:7a5ad01...
  * output : asset_manifest.json (register + locate assets; NO extraction,
             objective.classify_report_type=false, claims may be [])
  * hard gate: the markdown bytes fetched live from the platform are hashed and
    compared with the contract constant *before* anything is written. There is
    no code path that emits a manifest for a hash-mismatched source.

Design notes
  * Every locator is a character span into the source markdown, derived from an
    anchor substring that is required to occur exactly once. The emitted `quote`
    is the verbatim line text of that span (never retyped by hand), so the
    platform's independent substring re-check is a tautology only if the source
    is unchanged -- which is exactly what the hash gate pins down.
  * Referenced-but-external artefacts (per-case JSON runtime directory, the spec
    file, the four PNGs) are registered with resolution=referenced_unresolved
    and an explicit probe result; nothing is invented or silently dropped.
  * This script does not write report bodies; runner script renders the report
    from the manifest (see render_report_wp10400_01.py).

Usage:
  python3 scripts/kf/build_asset_manifest_wp10400_01.py [--offline]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys

REPORT_ID = "10400"
PACKAGE_ID = "wp-10400-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/10400"
SOURCE_FIELD = "markdown"
CONTRACT_HASH = "7a5ad01426079811a40edd7d8a95f7f09e1119e8a78ecfc44782d3b85920ab54"
CONTRACT_TITLE = "TensorDEM 二元颗粒床尺寸偏析验证（真实运行数据）"
CONTRACT_SCENARIO = "P70-N03_segregation_dynamics"
CONTRACT_CHARS = 6118

RUN_DIR = pathlib.Path("runs/wp-10400-01")
ART_DIR = pathlib.Path("artifacts/wp-10400-01")
# durable mirror: the push gate drops artifacts/** and runs/**, so the committed
# copy of every deliverable has to live under docs/.
DOC_DIR = pathlib.Path("docs/kf/wp-10400-01")

SNAPSHOT_MD = RUN_DIR / "report_10400.md"
SNAPSHOT_JSON = RUN_DIR / "report_10400.json"

# asset_id, asset_class, label, anchor (must be unique), line span relative to the
# anchor line (inclusive), resolution, note, probe spec for external artefacts.
ASSETS: list[dict] = [
    dict(asset_id="A01", asset_class="document", label="报告正文（markdown 全文，6118 字符）",
         anchor="# TensorDEM 二元颗粒床尺寸偏析验证报告（真实运行数据）", span=(0, 0),
         resolution="resolved_in_source", locator_method="document",
         note="整篇 markdown 即源资产本体；sha256/字符数见 source 段。段落定位以本资产的字符域为界。"),
    dict(asset_id="A02", asset_class="heading", label="报告标题行",
         anchor="# TensorDEM 二元颗粒床尺寸偏析验证报告（真实运行数据）", span=(0, 0),
         resolution="resolved_in_source",
         note="标题行原文；与平台 title 字段一致（由 provenance 脚本逐字比对，非人工转录）。"),
    dict(asset_id="A03", asset_class="provenance_statement", label="程序化生成声明（13 个逐案例 JSON 记录 → 本报告）",
         anchor="> 本文件由 `segregation_validation_report.py`", span=(0, 0),
         resolution="resolved_in_source",
         note="报告自述零合成数据分支、每个数字可回溯到记录文件；本工序只登记声明，不复核生成链（不越界）。"),
    dict(asset_id="A04", asset_class="table", label="案例参数表（颗粒数/粒径比/驱动/接触模型等 9 行）",
         anchor="| 参数 | 取值 |", span=(0, 10),
         resolution="resolved_in_source",
         note="表头+分隔行+9 行数据；数值仅登记不换算、不复核。"),
    dict(asset_id="A05", asset_class="code_reference", label="源码 src/tensordem/segregation/campaign.py（RSA 布床 + 振动底板驱动）",
         anchor="`src/tensordem/segregation/campaign.py`", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓路径；本工作树是 TensorKnowledge，无法解析，属跨仓引用。",
         probe=dict(kind="path", paths=["src/tensordem/segregation/campaign.py",
                                        "tensordem/segregation/campaign.py"])),
    dict(asset_id="A06", asset_class="code_reference", label="源码 metrics.py（分层组分 / S_bn / v_up / 质量与一阶矩审计）",
         anchor="`metrics.py` 从粒子位置直接计算分层组分", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓路径（报告仅给文件名，未给完整路径），本工作树内不可解析。",
         probe=dict(kind="path", paths=["src/tensordem/segregation/metrics.py",
                                        "tensordem/segregation/metrics.py"])),
    dict(asset_id="A07", asset_class="code_reference", label="源码 analysis.py::evaluate_criteria（6 条验收判据机器判定）",
         anchor="`analysis.py::evaluate_criteria`", span=(0, 0),
         resolution="referenced_unresolved",
         note="判据实现体；本工序只登记引用，不评判判据口径（判据正确性属下游复核工序）。",
         probe=dict(kind="path", paths=["src/tensordem/segregation/analysis.py",
                                        "tensordem/segregation/analysis.py"])),
    dict(asset_id="A08", asset_class="code_reference", label="源码 transfer.py（二维切片 → 三维舱段 → ΔVCG/ΔTCG/ΔGM 闭式映射）",
         anchor="`transfer.py` 把二维切片分布", span=(0, 0),
         resolution="referenced_unresolved",
         note="稳性传递映射实现；本工作树内不可解析。",
         probe=dict(kind="path", paths=["src/tensordem/segregation/transfer.py",
                                        "tensordem/segregation/transfer.py"])),
    dict(asset_id="A09", asset_class="code_reference", label="运行载体 scripts/run_segregation_campaign.py（进程池，一案例一进程）",
         anchor="5. 运行载体：`scripts/run_segregation_campaign.py`", span=(0, 0),
         resolution="referenced_unresolved",
         note="TensorDEM 仓运行入口；本工序不执行它（登记不等于复跑）。",
         probe=dict(kind="path", paths=["scripts/run_segregation_campaign.py"])),
    dict(asset_id="A10", asset_class="dataset_reference", label="逐案例运行记录目录 .scratch/pilot_out（13 个 JSON 记录）",
         anchor="| 记录目录 | `.scratch/pilot_out` |", span=(0, 0),
         resolution="referenced_unresolved",
         note="运行时目录，报告第「附」节明示不随仓提交；本工作树内不存在，故全部数值的原始记录在本侧不可解析（保留为未解析，不臆造内容）。",
         probe=dict(kind="path", paths=[".scratch/pilot_out"])),
    dict(asset_id="A11", asset_class="dataset_reference", label="重建用算例规格 runs/segregation/pilot_specs.json",
         anchor="--spec runs/segregation/pilot_specs.json", span=(0, 0),
         resolution="referenced_unresolved",
         note="报告称规格文件随仓提交并可据此重建全部数字；本工作树（TensorKnowledge）内无此路径，跨仓不可解析。",
         probe=dict(kind="path", paths=["runs/segregation/pilot_specs.json"])),
    dict(asset_id="A12", asset_class="table", label="主结果表：粒径比 → mean S_bn / mean v_up / cases（4 行）",
         anchor="| $d_l/d_s$ | mean $S_{bn}$ | mean $v_{up}$ (m/s) | cases |", span=(0, 5),
         resolution="resolved_in_source",
         note="表头+分隔行+4 行数据；数字逐字登记，本工序不做算术复核，也不重算 S_bn。"),
    dict(asset_id="A13", asset_class="table", label="6 条验收判据判定表（a–f，7 行，含 sat 行）",
         anchor="| 判据 | 实测 | 限值 | 结论 |", span=(0, 8),
         resolution="resolved_in_source",
         note="7 行中 3 PASS / 3 FAIL / 1 无判定（—）；上游 honest-FAIL，本工序原样登记不改写。"),
    dict(asset_id="A14", asset_class="finding_statement", label="方向性发现：反向巴西坚果（reverse Brazil-nut）区间",
         anchor="**方向性发现**", span=(0, 0),
         resolution="resolved_in_source",
         note="报告据此声明判据 (b)/(d) 失去物理意义；属上游解释性结论，本工序不改标 verified。"),
    dict(asset_id="A15", asset_class="numeric_anchor", label="传递映射数值（ΔVCG / ΔTCG / 两个 ΔGM，最偏析案例 demo_ratio_R4.0_s0）",
         anchor="传递映射（最偏析案例 `demo_ratio_R4.0_s0`）", span=(0, 0),
         resolution="resolved_in_source",
         note="单行数值锚点：ΔVCG=1.76e-05 m、ΔTCG=0、ΔGM=-5.54e-11 m（两个界），逐字登记。"),
    dict(asset_id="A16", asset_class="numeric_anchor", label="底面载荷和审计最大相对误差 0.678（未收敛项）",
         anchor="底面载荷和审计（全部振动案例的最大相对误差）= 0.678", span=(0, 0),
         resolution="resolved_in_source",
         note="报告自承未收敛、不参与判据 (e)；登记为「已知缺陷量」而非通过项。"),
    dict(asset_id="A17", asset_class="figure", label="图 segregation_vs_ratio.png（S_bn vs d_l/d_s + 等径负对照 ±0.02 带）",
         anchor="![segregation_vs_ratio](artifacts/segregation_figures/segregation_vs_ratio.png)", span=(0, 2),
         resolution="referenced_unresolved",
         note="图引用+英文图注在源内可定位；PNG 二进制属 TensorDEM 仓 artifacts/，本工作树内不存在。平台 figures 字段含同名条目（见 resolution_check）。",
         probe=dict(kind="figure", name="segregation_vs_ratio",
                    paths=["artifacts/segregation_figures/segregation_vs_ratio.png"])),
    dict(asset_id="A18", asset_class="figure", label="图 rise_velocity_scaling.png（上升速度 vs 粒径比超额 + 幂律拟合 + 文献斜率 p=1）",
         anchor="![rise_velocity_scaling](artifacts/segregation_figures/rise_velocity_scaling.png)", span=(0, 2),
         resolution="referenced_unresolved",
         note="图引用+图注在源内可定位；PNG 二进制本工作树内不存在。",
         probe=dict(kind="figure", name="rise_velocity_scaling",
                    paths=["artifacts/segregation_figures/rise_velocity_scaling.png"])),
    dict(asset_id="A19", asset_class="figure", label="图 segregation_vs_gamma.png（S_bn vs 驱动 Γ + 拟合 Γ_c + 文献锚 Γ_c=1.2）",
         anchor="![segregation_vs_gamma](artifacts/segregation_figures/segregation_vs_gamma.png)", span=(0, 2),
         resolution="referenced_unresolved",
         note="图引用+图注在源内可定位；PNG 二进制本工作树内不存在（报告判据 (d) 自述拟合不可辨识，图内拟合线不构成阈值证据）。",
         probe=dict(kind="figure", name="segregation_vs_gamma",
                    paths=["artifacts/segregation_figures/segregation_vs_gamma.png"])),
    dict(asset_id="A20", asset_class="figure", label="图 stability_impact.png（货重矩 → 稳性闭式映射，ΔVCG/ΔTCG/两个 ΔGM 界）",
         anchor="![stability_impact](artifacts/segregation_figures/stability_impact.png)", span=(0, 2),
         resolution="referenced_unresolved",
         note="图引用+图注在源内可定位；PNG 二进制本工作树内不存在。",
         probe=dict(kind="figure", name="stability_impact",
                    paths=["artifacts/segregation_figures/stability_impact.png"])),
    dict(asset_id="A21", asset_class="table", label="敏感性表 4b：颗粒数/时间窗（N=600, 0.6 s）四案（4 行）",
         anchor="| 集合 | 案例 | N | run_time (s) | $S_{bn}$ | $S_{fine}$ | $v_{up}$ (m/s) |", span=(0, 5),
         resolution="resolved_in_source",
         note="表头+分隔行+4 行数据；该集合独立于主表（报告原文如此声明），登记时保持两个数据集分离。"),
    dict(asset_id="A22", asset_class="finding_statement", label="敏感性结论：S_bn 符号不稳定、R² 极低（信号受统计噪声主导）",
         anchor="敏感性说明：同一驱动位形下改变颗粒数与时间窗", span=(0, 0),
         resolution="resolved_in_source",
         note="报告据此声明指数/阈值结论不可靠；属上游自限性声明。"),
    dict(asset_id="A23", asset_class="limitation_set", label="局限与适用范围 8 条（二维切片/短时窗/案例数/尺度/自由液面/架构/扩样/报告卫生）",
         anchor="- **二维切片**", span=(0, 7),
         resolution="resolved_in_source",
         note="8 条局限原文；其中「扩样作业仍在排队」是时点性状态，后续报告可能过期，登记为快照事实。"),
    dict(asset_id="A24", asset_class="table", label="误差判定表 §6：关键量 vs 基准（6 行）",
         anchor="| 关键量 | 实测 | 基准 | 相对偏差 | 是否 < 3% |", span=(0, 7),
         resolution="resolved_in_source",
         note="表头+分隔行+6 行数据；上游对 p、Γ_c、底面载荷均给出「否」，本工序原样登记。"),
    dict(asset_id="A25", asset_class="verdict", label="总判定：6 条判据 3 条通过，all_pass=False",
         anchor="**总判定**：6 条判据中 3 条通过", span=(0, 0),
         resolution="resolved_in_source",
         note="honest-FAIL 结论原文；本工序不得改标 verified（verification 由平台门计算）。"),
    dict(asset_id="A26", asset_class="repro_script", label="附：可复现命令块（bash：主算例 + 敏感性探测 + 报告重生成）",
         anchor="```bash", span=(0, 24),
         resolution="resolved_in_source",
         note="三段命令原文（含内嵌 python 生成 probe_specs）；本工序不执行（不压控制面、不改上游产物）。"),
    dict(asset_id="A27", asset_class="finding_statement", label="误差结论段：闭式量 <3% 达成、两个物理标度量超 3% 不宣称达标",
         anchor="**结论**：质量守恒与传递映射是闭式/审计量", span=(0, 0),
         resolution="resolved_in_source",
         note="报告显式回答「是否<3%」并给出 否 的项；属上游误差判定，不重复计算。"),
]


def _api_call(path: str, body: dict | None = None, token: str | None = None) -> dict:
    from urllib.request import Request, urlopen

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(base + path, data=json.dumps(body).encode() if body else None,
                  headers=headers)
    with urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_source(offline: bool) -> tuple[str, dict]:
    if offline:
        return SNAPSHOT_MD.read_text(encoding="utf-8"), json.loads(
            SNAPSHOT_JSON.read_text(encoding="utf-8"))
    tok = _api_call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    payload = _api_call(f"/tensor/reports/{REPORT_ID}", token=tok)
    return payload["markdown"], payload


def sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def line_table(md: str) -> tuple[list[str], list[int]]:
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def build_locator(md: str, lines: list[str], offs: list[int], anchor: str,
                  span: tuple[int, int], method: str = "char_span") -> dict:
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"FATAL: anchor {anchor!r} occurs in {len(hits)} lines (need exactly 1)")
    a = hits[0]
    s, e = a + span[0], a + span[1]
    if e >= len(lines):
        raise SystemExit(f"FATAL: span {span} past end of document for anchor {anchor!r}")
    quote = "\n".join(lines[s:e + 1])
    if method == "document":
        return dict(method="document", start_char=0, end_char=len(md),
                    start_line=0, end_line=len(lines) - 1, quote=quote,
                    unique=md.count(quote) == 1)
    start_char = offs[s]
    end_char = offs[e] + len(lines[e])
    if md[start_char:end_char] != quote:
        raise SystemExit(f"FATAL: char span does not reproduce quote for {anchor!r}")
    return dict(method="char_span", start_char=start_char, end_char=end_char,
                start_line=s, end_line=e, quote=quote,
                unique=md.count(quote) == 1)


def probe_asset(spec: dict, md: str, payload: dict, worktree: pathlib.Path) -> dict:
    """Resolve an external artefact reference without inventing anything."""
    p = spec.get("probe") or {}
    if p.get("kind") == "path":
        hits = [x for x in p["paths"] if (worktree / x).exists()]
        return dict(check="worktree_path_probe", result="present" if hits else "unresolved",
                    candidate_paths=p["paths"], addresses_found=hits,
                    detail="probe = os.path.exists on the declared relative paths inside this "
                           "worktree only (no network, no cross-repo guess)")
    if p.get("kind") == "figure":
        figs = payload.get("figures") or []
        hit = [f for f in figs if f.get("name") == p["name"]]
        disk = [x for x in p["paths"] if (worktree / x).exists()]
        return dict(check="platform_figures_field+worktree_path_probe",
                    result="present" if hit else "unresolved",
                    platform_figure_name=p["name"],
                    platform_caption=(hit[0].get("caption") if hit else None),
                    caption_in_source=bool(hit and hit[0].get("caption")
                                           and hit[0]["caption"] in md),
                    binary_in_worktree=bool(disk), candidate_paths=p["paths"],
                    detail="figure identity resolved via platform figures metadata and the "
                           "verbatim caption present in the markdown; the PNG binary itself "
                           "lives in the TensorDEM repo and is absent from this worktree")
    return dict(check="char_span_in_source_markdown", result="resolved")


def section_of(lines: list[str], idx: int) -> str:
    head = "(document)"
    for ln in lines[: idx + 1]:
        if ln.startswith("#"):
            head = ln.strip()
    return head


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="use the local snapshot instead of the live API (hash gate still runs)")
    args = ap.parse_args()

    RUN_DIR.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    DOC_DIR.mkdir(parents=True, exist_ok=True)

    md, payload = fetch_source(args.offline)
    if not args.offline:
        SNAPSHOT_MD.write_text(md, encoding="utf-8")
        SNAPSHOT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                                 encoding="utf-8")

    # ---- hard hash gate (no manifest is ever written for a mismatched source) ----
    md_hash = sha256_text(md)
    if md_hash != CONTRACT_HASH:
        print(f"FATAL: markdown sha256 {md_hash} != contract source_hash {CONTRACT_HASH}")
        return 2
    if len(md) != CONTRACT_CHARS:
        print(f"FATAL: chars {len(md)} != contract chars {CONTRACT_CHARS}")
        return 2
    if payload.get("title") != CONTRACT_TITLE or payload.get("scenario_key") != CONTRACT_SCENARIO:
        print(f"FATAL: title/scenario mismatch: {payload.get('title')!r} "
              f"{payload.get('scenario_key')!r}")
        return 2

    lines, offs = line_table(md)
    worktree = pathlib.Path(".").resolve()

    assets, seen = [], set()
    for spec in ASSETS:
        if spec["asset_id"] in seen:
            raise SystemExit(f"FATAL: duplicate asset_id {spec['asset_id']}")
        seen.add(spec["asset_id"])
        loc = build_locator(md, lines, offs, spec["anchor"], spec["span"],
                           spec.get("locator_method", "char_span"))
        if not loc["unique"]:
            raise SystemExit(f"FATAL: quote not unique for {spec['asset_id']}")
        assets.append(dict(
            asset_id=spec["asset_id"],
            asset_class=spec["asset_class"],
            label=spec["label"],
            in_report_section=section_of(lines, loc["start_line"]),
            locator=loc,
            resolution=spec["resolution"],
            resolution_check=probe_asset(spec, md, payload, worktree),
            note=spec["note"],
        ))

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    img_refs = [ln for ln in lines if ln.startswith("![")]
    fig_names_md = [r.split("](")[0][2:] for r in img_refs]
    fig_names_platform = [f.get("name") for f in (payload.get("figures") or [])]
    caption_ok = all((f.get("caption") or "") in md for f in (payload.get("figures") or []))

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
            bytes_utf8=len(md.encode("utf-8")),
            title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            platform_id=payload.get("id"),
            platform_mission_id=payload.get("mission_id"),
            platform_status=payload.get("status"),
            platform_figures=payload.get("figures") or [],
            platform_tags=payload.get("tags") or [],
            retrieved_via=("local snapshot (--offline)" if args.offline else
                           f"GET {os.environ['TENSOR_API_BASE'].rstrip('/')}/tensor/reports/{REPORT_ID}"),
            local_copy=str(SNAPSHOT_MD),
        ),
        counts=dict(
            assets=len(assets), by_class=by_class, by_resolution=by_res,
            resolved_in_source=by_res.get("resolved_in_source", 0),
            referenced_unresolved=by_res.get("referenced_unresolved", 0),
            declared_absent=by_res.get("declared_absent", 0),
        ),
        assets=assets,
        claims=[],
        claims_note=("objective.classify_report_type=false 且 notes 允许 claims 为空数组：本工序只登记"
                     "资产定位，不做 claim 抽取；claim 抽取与复核由下游工作包负责。零条=合法完整结果，"
                     "不为填指标而造知识。"),
        integrity=dict(
            quote_uniqueness=("every asset quote confirmed as exactly one occurrence in the source "
                              "markdown (build_locator raises otherwise)"),
            hash_recomputed_locally=True,
            hash_matches_contract=True,
            contract_source_hash="sha256:" + CONTRACT_HASH,
            chars_matches_contract=len(md) == CONTRACT_CHARS,
            title_matches_contract=payload.get("title") == CONTRACT_TITLE,
            scenario_matches_contract=payload.get("scenario_key") == CONTRACT_SCENARIO,
            figure_refs_in_markdown=fig_names_md,
            figure_names_in_platform=fig_names_platform,
            figure_refs_consistent=(fig_names_md == fig_names_platform),
            platform_captions_verbatim_in_markdown=caption_ok,
            duplicate_asset_ids=len(seen) != len(assets),
            claims_status=("claims=[] by contract; no claim is marked verified by this package "
                           "(verification is computed by the platform gate)"),
        ),
    )

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
            source_field=SOURCE_FIELD,
            source_hash="sha256:" + md_hash,
            source_chars=len(md),
            source_bytes_utf8=len(md.encode("utf-8")),
            source_title=payload.get("title"),
            scenario_key=payload.get("scenario_key"),
            contract_version="1.0",
            lane="C",
            work_package=PACKAGE_ID,
            generator="scripts/kf/build_asset_manifest_wp10400_01.py",
            verifier="scripts/kf/validate_wp10400_01.py",
            verification_status="not_verified",
            verification_note="verification is computed by the platform gate; this package "
                              "asserts nothing about claim truth",
            artifact_sha256=art_hash,
        ),
        outputs={"asset_manifest.json": manifest},
    )
    (RUN_DIR / "kf_result.wp-10400-01.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("markdown sha256:", md_hash, "MATCH")
    print("assets:", len(assets))
    print("by_class:", json.dumps(by_class, ensure_ascii=False))
    print("by_resolution:", json.dumps(by_res, ensure_ascii=False))
    print("figure refs consistent:", fig_names_md == fig_names_platform)
    print("artifact:", art, art_hash)
    return 0


if __name__ == "__main__":
    sys.exit(main())