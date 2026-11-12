#!/usr/bin/env python3
"""KF-RESULT wp-2506-01 · 工序 01-asset-registration（report_id=2506，硬锁）。

只登记 report 2506 的资产与指纹：
- 确认 report_id 与 markdown 的 UTF-8 字节 sha256（与契约 source_hash 对齐）；
- 枚举可解析的附件/工件（逐字引文 + 字符偏移 + 回读校验）；
- 拿不到字节的工件（图件 / pytest 日志 / 代码级绑定）如实登记 declared_unresolvable；
- 不抽取知识（claims=[]）、不标 verified、不重跑上游算例、不读写其它 report_id。

用法：
  python3 scripts/kf/wp_2506_01_register_assets.py                      # 在线取源
  python3 scripts/kf/wp_2506_01_register_assets.py --record-file P.json # 离线重建
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from register_assets_lib import (  # noqa: E402
    Md,
    fetch_report,
    get_token,
    locate_all,
    probe,
    sha256_of,
)

REPORT_ID = "2506"
PACKAGE_ID = "wp-2506-01"
TASK_TYPE = "01-asset-registration"
LANE = "C"
SOURCE_URI = "tensor://reports/2506"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = "sha256:c62850b3dacd416bd9d535fec206f6e8427fb10121f439c7b865b2165e5138b0"
CONTRACT_CHARS = 3382
CONTRACT_TITLE = (
    "TensorFVM 粘性算子耗散性定因：非正交修正被证伪 + "
    "能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）"
)
CONTRACT_SCENARIO = "tensorfvm/verification/compatible-viscous-dissipativity"
PRODUCER = "kf-worker/tp-native-1"

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "artifacts" / "kf" / PACKAGE_ID
MIRROR = ROOT / "knowledge" / "kf" / PACKAGE_ID

# ---------------------------------------------------------------- 资产规格
# 选择器语法见 scripts/kf/register_assets_lib.py:Md.locate
SPEC: list[dict] = [
    dict(id="01-report-markdown", kind="report_markdown", sel="h1",
         section="H1", note="markdown 首行 H1，全文指纹载体"),
    dict(id="02-report-record", kind="report_record_metadata", sel="token:__TITLE__",
         status="declared_unresolvable", section="record.title",
         unresolved_reason=(
             "记录 title（=契约 title）未在 markdown 中逐字出现：markdown H1 措辞为"
             "「TensorFVM 粘性算子耗散性定因与能量相容装配（native compatible viscous operator）」，"
             "与记录 title「…定因：非正交修正被证伪 + 能量相容(Galerkin)装配 PSD 证书（41 几何扫掠）」不同。"
             "按零手抄纪律不改写、不强行匹配，登记为记录级元数据不可在正文定位（title_matches_markdown_h1=False）。"),
         note="记录级元数据：title/scenario_key/mission_id 见 source.record_fields；正文无同形串"),
    dict(id="03-section-case-defect", kind="section_prose", sel="after:## ①:1",
         section="① 案例介绍 / 悬案缺陷", note="§1 首行：strict xfail 开放缺陷"),
    dict(id="04-section-geometry-family", kind="section_prose", sel="after:## ①:2",
         section="① 案例介绍 / 几何族", note="§1 次行：two_tetrahedra(skew) 几何族与规模"),
    dict(id="05-parameter-sweep-grid", kind="parameter_statement", sel="after:## ①:3",
         section="① 案例介绍 / 扫掠参数", note="§1 第三行：边界条件、μ=ρ=1、41 点扫掠与合法域上界"),
    dict(id="06-criterion-statement", kind="criterion_statement", sel="after:## ①:4",
         section="① 案例介绍 / 判据", note="§1 末行：E=uᵀAu 与对称部分特征值判据"),
    dict(id="07-method-damping-sweep", kind="method_steps", sel="token:NativeViscous3D",
         section="② 方法 / 步骤1", note="§2 步骤1：correction_damping 扫掠用于检验既有归因"),
    dict(id="08-equation-galerkin-assembly", kind="equation", sel="token:K = Σ_c 2 μ_c V_c",
         section="② 方法 / Galerkin 装配式", note="§2 步骤2：能量（Galerkin）装配的平方和形式"),
    dict(id="09-method-psd-by-construction", kind="method_steps", sel="token:平方和",
         section="② 方法 / 半正定由构造保证", note="§2 步骤2：PSD 由平方和构造保证"),
    dict(id="10-toolchain-list", kind="toolchain_list",
         sel="token:audit_compatible_viscous_dissipativity",
         section="② 方法 / 工具链", note="§2 步骤3：审计脚本 + pytest + matplotlib 工具链"),
    dict(id="11-table-sweep-result", kind="result_table", sel="table:| skew |",
         section="③ 计算结果 / 41 点扫掠表", note="§3 表头行；数据行数由 stats.data_rows 程序化统计"),
    dict(id="12-table-sweep-row0", kind="result_table_row", sel="table_row:| skew |:0",
         section="③ 计算结果 / 首行数据", note="§3 表首个数据行（skew=0.000 代表行）"),
    dict(id="13-summary-legacy-default", kind="result_summary_bullet", sel="bullet:## ③:2 个几何",
         section="③ 扫描汇总 / legacy 默认装配", note="§3 汇总第1条：默认装配造能几何数"),
    dict(id="14-summary-alpha0", kind="result_summary_bullet", sel="bullet:## ③:纯两点通量",
         section="③ 扫描汇总 / α=0 反证", note="§3 汇总第2条：α=0 反而造能（归因被证伪）"),
    dict(id="15-summary-compatible-extrema", kind="result_summary_bullet", sel="bullet:## ③:E 的最小值",
         section="③ 扫描汇总 / 相容装配极值", note="§3 汇总第3条：相容装配 E 与 λmin 极值"),
    dict(id="16-figure-dissipativity-sweep", kind="figure", sel="token:![sweep]",
         status="declared_unresolvable", section="④ 图 / dissipativity-sweep.png",
         unresolved_reason=(
             "记录 figures 仅 name/caption（figure_payload_present=False），图件端点 "
             "GET /tensor/reports/2506/figures/dissipativity-sweep(.png) 返回 HTTP 404；"
             "本工序不重绘、不代上游补图，保留未解析（正文引用行仍可逐字定位）。"),
         note="§4 图引用行：正文以 markdown 图片语法指向该 png"),
    dict(id="17-limitation-attribution", kind="limitations_list", sel="bullet:## ⑤:归因修正",
         section="⑤ 局限 / 归因修正", note="§5 第1条：主因改判为 sum-by-parts 不成立"),
    dict(id="18-limitation-default-path", kind="limitations_list", sel="bullet:## ⑤:默认路径未改",
         section="⑤ 局限 / 默认路径未改", note="§5 第2条：默认路径逐位不变、strict xfail 保留"),
    dict(id="19-limitation-dissipativity-only", kind="limitations_list", sel="bullet:## ⑤:只认证耗散性",
         section="⑤ 局限 / 只认证耗散性", note="§5 第3条：标度/一致性未认证，如实留白"),
    dict(id="20-limitation-sparsity", kind="limitations_list", sel="bullet:## ⑤:两跳",
         section="⑤ 局限 / 稀疏度", note="§5 第4条：两跳模板的稀疏度/带宽需评估"),
    dict(id="21-error-basis", kind="error_judgement", sel="token:符号/特征值证书",
         section="⑥ 误差判定 / 判据性质", note="§6 显式声明不适用 <3% 条款及原因"),
    dict(id="22-error-energy-bound", kind="error_judgement", sel="bullet:## ⑥:相容装配 E ≤ 0",
         section="⑥ 误差判定 / E 证书", note="§6：41/41 点 E≤0 与最坏值"),
    dict(id="23-error-lambda-min", kind="error_judgement", sel="bullet:## ⑥:相容装配 λmin(K) > 0",
         section="⑥ 误差判定 / λmin 证书", note="§6：41/41 点 λmin>0 与最小值"),
    dict(id="24-test-evidence-summary", kind="test_evidence_summary",
         sel="token:audit_compatible_viscous_dissipativity",
         section="② 工具链 / pytest 用例数",
         note="§2 唯一给出用例数的一行（6 条用例）；与 asset-10 同源行，如实登记为文字自述"),
    dict(id="25-run-artifact-pytest-log", kind="run_artifact", sel="bullet:## ⑤:默认路径未改",
         status="declared_unresolvable", section="⑤ 局限 / 回归用例",
         unresolved_reason=(
             "报告仅以文字提及「有回归用例」与 pytest 6 条用例，未附原始 pytest 日志/trace/"
             "运行记录，工件字节不可得；工序 01 不重跑上游算例，故保留未解析。"),
         note="§5 第2条同一行（回归用例文字断言）：只登记可定位性，不作通过证据"),
    dict(id="26-codebase-pointer", kind="codebase_pointer",
         sel="token:audit_compatible_viscous_dissipativity",
         status="declared_unresolvable", section="② 工具链 / 代码路径",
         unresolved_reason=(
             "正文给出仓库内相对路径（src/tensorfvm/native_compatible_viscous3d.py、"
             "scripts/audit_compatible_viscous_dissipativity.py、"
             "tests/test_native_compatible_viscous3d.py）但无分支/提交号，字节不可经报告信道取得，"
             "亦无法绑定到具体 commit；仅由记录 mission_id=2488 探到 mission 记录 repo=TensorFVM，"
             "属记录级间接线索，不认定为工件绑定。"),
         note="代码指针：路径文本可定位，字节与 commit 不可得"),
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--record-file", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    args = ap.parse_args()

    out_dir = args.out or ART
    out_dir.mkdir(parents=True, exist_ok=True)

    rec = fetch_report(REPORT_ID, args.record_file)
    md_text = rec["markdown"]
    md = Md(md_text)
    sha = sha256_of(md_text)
    data = md_text.encode("utf-8")
    h1 = md.lines[0][1] if md.lines and md.lines[0][1].startswith("# ") else None
    title = rec.get("title") or ""

    token = get_token() if args.record_file is None else None
    fig_probes = [
        probe("/tensor/reports/2506/figures/dissipativity-sweep", token),
        probe("/tensor/reports/2506/figures/dissipativity-sweep.png", token),
    ]
    mission_probe: dict = {"endpoint": "/tensor/missions/2488", "http_status": None}
    if token:
        import urllib.request
        from register_assets_lib import api_base

        try:
            r = urllib.request.urlopen(
                urllib.request.Request(
                    api_base() + "/tensor/missions/2488",
                    headers={"Authorization": "Bearer " + token},
                ),
                timeout=30,
            )
            m = json.load(r)
            mission_probe = {
                "endpoint": "/tensor/missions/2488",
                "http_status": 200,
                "mission_repo": m.get("repo"),
                "mission_status": m.get("status"),
                "mission_campaign_id": m.get("campaign_id"),
            }
        except Exception as e:  # noqa: BLE001
            mission_probe["note"] = repr(e)

    assets, locator_checks = locate_all(md, SPEC, title, REPORT_ID)

    figs = rec.get("figures") or []
    figure_payload_present = any(
        isinstance(f, dict) and (f.get("png_base64") or f.get("base64")) for f in figs
    )
    ids = [a["asset_id"] for a in assets]
    unresolved = [a for a in assets if a["status"] != "resolved"]
    dist: dict = {}
    for a in assets:
        dist[a["status"]] = dist.get(a["status"], 0) + 1

    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "producer": PRODUCER,
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": sha,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_algo": "sha256",
            "hash_scope": "UTF-8 bytes of tensor_reports.markdown",
            "hash_match": sha == CONTRACT_SOURCE_HASH,
            "chars": len(md_text),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(md_text) == CONTRACT_CHARS,
            "bytes": len(data),
            "lines": len(md.lines),
            "fetched_via": rec.get("_retrieved_via", "unknown"),
            "record_fields": {
                "title": title,
                "scenario_key": rec.get("scenario_key"),
                "mission_id": rec.get("mission_id"),
                "status": rec.get("status"),
                "created_at": rec.get("created_at"),
                "tags": rec.get("tags") or [],
                "contract_title": CONTRACT_TITLE,
                "contract_scenario_key": CONTRACT_SCENARIO,
                "title_matches_contract": title == CONTRACT_TITLE,
                "scenario_matches_contract": rec.get("scenario_key") == CONTRACT_SCENARIO,
                "title_matches_markdown_h1": bool(h1 and title and title in h1),
            },
        },
        "assets": assets,
        "unresolved": [
            dict(asset_id=a["asset_id"], kind=a["kind"], reason=a["unresolved_reason"])
            for a in unresolved
        ],
        "locator_checks": locator_checks,
        "identity_facts": {
            "markdown_h1": h1,
            "record_title": title,
            "title_consistent": bool(h1 and title and title in h1),
            "scenario_key": rec.get("scenario_key"),
            "mission_id": rec.get("mission_id"),
            "mission_probe": mission_probe,
            "figures_declared": len(figs),
            "figure_payload_present": figure_payload_present,
            "figure_endpoint_probes": fig_probes,
            "markdown_sha256": sha,
            "chars": len(md_text),
            "bytes_utf8": len(data),
            "lines": len(md.lines),
            "asset_count": len(assets),
            "asset_status_distribution": dist,
        },
        "scope": {
            "extraction_performed": False,
            "claims_emitted": 0,
            "verification_performed": False,
            "note": ("工序 01 只登记资产与指纹：不抽取知识、不判定 verified、不重跑上游算例；"
                     "claims 允许为空数组，本单为空。"),
        },
        "limitations": [
            "图件字节不可得：记录 figures 仅 name/caption（figure_payload_present=False），"
            "端点探针 404；未重绘、未代上游补图。",
            "pytest 6 条用例为报告文字自述，无原始日志/trace 工件；本工序不重跑上游，只登记可定位性。",
            "正文给出仓库内相对路径但无分支/提交号，代码级绑定不可解析；"
            "仅记录级 mission_id=2488 → repo=TensorFVM 间接线索。",
            "本清单不评价报告结论真伪（含 α=0 反证与 PSD 证书）；数值裁决权在平台验证门与下游工序。",
            "引文口径=整行原文，不裁不改；跨行段落取其中代表行，不做字符串拼接（避免二次转录误差）。",
        ],
    }

    # ---- 机读自检
    def chk(name, passed, detail):
        return dict(name=name, passed=bool(passed), detail=detail)

    bad_quotes = [k for k, v in locator_checks.items() if not v["resolvable_in_markdown"]]
    offset_mismatch = [k for k, v in locator_checks.items() if not v["back_read_ok"]]
    missing_reason = [
        a["asset_id"] for a in unresolved if len(str(a.get("unresolved_reason", "")).strip()) < 10
    ]
    rf = manifest["source"]["record_fields"]
    checks = [
        chk("source_hash_matches", manifest["source"]["hash_match"],
            {"contract": CONTRACT_SOURCE_HASH, "recomputed": sha}),
        chk("chars_match_contract", manifest["source"]["chars_match_contract"],
            {"contract": CONTRACT_CHARS, "measured": len(md_text)}),
        chk("report_id_locked", str(rec.get("id")) == REPORT_ID, {"report_id": rec.get("id")}),
        chk("source_locator_resolvable", not bad_quotes and not offset_mismatch,
            {"assets": len(locator_checks), "bad_quotes": bad_quotes,
             "offset_mismatch": offset_mismatch}),
        chk("no_duplicate_ids", len(ids) == len(set(ids)),
            {"assets": len(ids), "unique": len(set(ids))}),
        chk("unresolved_have_reasons", not missing_reason, missing_reason),
        chk("all_claims_have_evidence_or_explicit_unresolved_status", True,
            {"claims": 0, "unresolved": len(unresolved),
             "note": "claims 为空数组（契约允许）；%d 条不可得工件均带 reason" % len(unresolved)}),
        chk("title_scenario_match_contract",
            rf["title_matches_contract"] and rf["scenario_matches_contract"],
            {"title_matches": rf["title_matches_contract"],
             "scenario_matches": rf["scenario_matches_contract"]}),
        chk("no_extraction_no_verification",
            manifest["scope"]["extraction_performed"] is False
            and manifest["scope"]["verification_performed"] is False,
            manifest["scope"]),
    ]

    import jsonschema  # noqa: PLC0415

    schema_dir = ROOT / "schemas"
    m_schema = json.loads((schema_dir / "asset_manifest.v1.schema.json").read_text(encoding="utf-8"))
    e_schema = json.loads((schema_dir / "kf_result.v1.schema.json").read_text(encoding="utf-8"))

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_hash": sha,
            "source_field": SOURCE_FIELD,
            "producer": PRODUCER,
            "emitted_at": manifest["generated_at"],
            "notes": ("asset_manifest.json 见 outputs；引文均由脚本从 markdown 按整行取子串，"
                      "逐条做 quote in markdown + 偏移回读确认；未抽取 claims，未标 verified。"),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    m_err = sorted(jsonschema.Draft202012Validator(m_schema).iter_errors(manifest), key=str)
    e_err = sorted(jsonschema.Draft202012Validator(e_schema).iter_errors(envelope), key=str)
    checks.append(chk("schema_pass", not m_err and not e_err,
                      {"manifest_errors": [e.message for e in m_err][:5],
                       "kf_result_errors": [e.message for e in e_err][:5],
                       "schema": ["schemas/asset_manifest.v1.schema.json",
                                  "schemas/kf_result.v1.schema.json"],
                       "validator": "jsonschema Draft2020-12"}))
    # ---- 落盘：先写清单/信封，再用 json.loads 真回读证明 valid_json
    (out_dir / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "kf_result.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    reload_errors = []
    for rel in ["asset_manifest.json", "kf_result.json"]:
        try:
            json.loads((out_dir / rel).read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            reload_errors.append({"file": rel, "error": repr(e)})
    checks.append(chk("valid_json", not reload_errors,
                      {"files": ["asset_manifest.json", "kf_result.json"],
                       "reloaded": True, "reload_errors": reload_errors}))

    result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "generated_at": manifest["generated_at"],
        "all_pass": all(c["passed"] for c in checks),
        "checks": checks,
        "acceptance": {c["name"]: c["passed"] for c in checks},
    }

    (out_dir / "checks.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    snap = out_dir / "source_snapshot" / ("report_%s.json" % REPORT_ID)
    snap.parent.mkdir(parents=True, exist_ok=True)
    snapshot = dict(rec)
    snap.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    # ---- 交付镜像（artifacts/ 被 .gitignore 忽略，随分支交付的是 knowledge/kf/<pkg>/）
    if out_dir == ART:
        MIRROR.mkdir(parents=True, exist_ok=True)
        for rel in ["asset_manifest.json", "kf_result.json", "checks.json",
                    "source_snapshot/report_%s.json" % REPORT_ID]:
            dst = MIRROR / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(out_dir / rel, dst)

    print(json.dumps({
        "package_id": PACKAGE_ID,
        "asset_count": len(assets),
        "status_distribution": dist,
        "all_pass": result["all_pass"],
        "failed": [c["name"] for c in checks if not c["passed"]],
        "sha": sha,
        "chars": len(md_text),
        "out": str(out_dir),
    }, ensure_ascii=False, indent=2))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())