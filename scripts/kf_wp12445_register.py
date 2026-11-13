"""wp-12445-01 / 01-asset-registration: register report 12445's source asset.

Reads the pinned markdown (runs/wp-12445-01/report_12445.md, produced by
scripts/kf_wp12445_fetch.py), re-verifies its sha256 against the work-package
contract, then registers every attachment/artifact the report declares as an
asset with an exact, unique, character-span locator in the markdown.

No extraction, no classification, no claim generation: this package only
registers assets (contract objective: register_assets=true,
classify_report_type=false). claims is therefore [] by contract.

Outputs (all inside the worktree):
  docs/kf/wp-12445-01/asset_manifest.json   the asset_manifest.v1 document
  docs/kf/wp-12445-01/kf_result.json        kf_result.v1 envelope (delivery payload)
  docs/kf/wp-12445-01/verify_log.json       per-check machine log (acceptance evidence)
  docs/kf/wp-12445-01/asset_manifest.schema.json  schema pinned for this package

Usage: python3 scripts/kf_wp12445_register.py
"""
import hashlib
import json
import os
import pathlib

PKG = "wp-12445-01"
REPORT_ID = "12445"
CONTRACT_HASH = "f86e8247d5dff43152a883b11207b09d96d5dd70892d7f62cab187746f85f23f"
CONTRACT_CHARS = 3554
CONTRACT_TITLE = "P269W2-N07 EEXI/CII 端到端不确定度传播：六因子蒙特卡洛 · 合规概率 · Sobol 分解"
SCENARIO = "green_navigation"

ROOT = pathlib.Path(".")
RUNS = ROOT / "runs" / PKG
OUTDIR = ROOT / "docs" / "kf" / PKG
MD_PATH = RUNS / "report_12445.md"
META_PATH = RUNS / "fetch_meta.json"

# ---------------------------------------------------------------- assets
# quote = verbatim substring of the markdown; verified to occur exactly once.
# resolution semantics (conservative):
#   resolved_in_source   -> the registered object resolves inside the markdown itself
#   referenced_unresolved-> the report names it, but its bytes/objects are not in the
#                           markdown; identity may come from platform record metadata
#   declared_absent      -> the report itself declares the input missing/unverifiable
ASSETS = [
    dict(
        asset_id="A01", asset_class="figure", label="fig1_eexi_pdf.png",
        section="产物（§3/§4 之后，第 43 行）",
        quote="artifacts/P269W2_N07/`（JSON + 5 图）",
        resolution="referenced_unresolved",
        check="platform record figures[] entry name=='fig1_eexi_pdf.png' present with caption; "
              "PNG bytes not embedded in markdown",
        result="unresolved",
        note="EEXI PDF/CDF 图。身份与图注由平台 record（figures[]）给出；逐图字节不可从 markdown 取得，"
             "本工序不做图内容核验（属下游抽取/审计工序）。",
    ),
    dict(
        asset_id="A02", asset_class="figure", label="fig2_cii_pdf.png",
        section="产物（第 43 行）",
        quote="artifacts/P269W2_N07/`（JSON + 5 图）",
        resolution="referenced_unresolved",
        check="platform record figures[] entry name=='fig2_cii_pdf.png' match; PNG bytes not in markdown",
        result="unresolved",
        note="CII PDF/CDF 图；同为 record 级身份，字节未随 markdown。",
    ),
    dict(
        asset_id="A03", asset_class="figure", label="fig3_sobol.png",
        section="产物（第 43 行）",
        quote="artifacts/P269W2_N07/`（JSON + 5 图）",
        resolution="referenced_unresolved",
        check="platform record figures[] entry name=='fig3_sobol.png' match; PNG bytes not in markdown",
        result="unresolved",
        note="Sobol 方差分解图；与正文 Sobol 表存在对应关系，但对应关系核验不属本工序。",
    ),
    dict(
        asset_id="A04", asset_class="figure", label="fig4_convergence_negative_control.png",
        section="产物（第 43 行）",
        quote="artifacts/P269W2_N07/`（JSON + 5 图）",
        resolution="referenced_unresolved",
        check="platform record figures[] entry name=='fig4_convergence_negative_control.png' match; "
              "PNG bytes not in markdown",
        result="unresolved",
        note="A5 收敛 + A6 负控图；record 级身份。",
    ),
    dict(
        asset_id="A05", asset_class="figure", label="fig5_surrogate_verification.png",
        section="产物（第 43 行）",
        quote="artifacts/P269W2_N07/`（JSON + 5 图）",
        resolution="referenced_unresolved",
        check="platform record figures[] entry name=='fig5_surrogate_verification.png' match; "
              "PNG bytes not in markdown",
        result="unresolved",
        note="归约链自证图；record 级身份。图数合计 5，与正文“5 图”声明一致。",
    ),
    dict(
        asset_id="A06", asset_class="artifact_bundle", label="artifacts/P269W2_N07/ (JSON + 5 图)",
        section="产物（第 43 行）",
        quote="`artifacts/P269W2_N07/`（JSON + 5 图）",
        resolution="referenced_unresolved",
        check="os.path.exists('artifacts/P269W2_N07') in this worktree",
        result="unresolved",
        note="产物目录：JSON 数值工件 + 5 图。本工作树（TensorKnowledge）只持有报告登记物，"
             "该目录属源仓 ship-performance-platform；未跨仓拉取，不冒充已核验。",
    ),
    dict(
        asset_id="A07", asset_class="source_module", label="backend/services/green_uncertainty.py",
        section="产物（第 43 行）",
        quote="`backend/services/green_uncertainty.py`",
        resolution="referenced_unresolved",
        check="os.path.exists('backend/services/green_uncertainty.py') in this worktree",
        result="unresolved",
        note="六因子 MC / Sobol / 归约链实现。路径相对源仓根；本工作树无 backend/ 目录。",
    ),
    dict(
        asset_id="A08", asset_class="api_router", label="backend/api/green_uncertainty.py",
        section="产物（第 43 行）",
        quote="`backend/api/green_uncertainty.py`",
        resolution="referenced_unresolved",
        check="os.path.exists('backend/api/green_uncertainty.py') in this worktree",
        result="unresolved",
        note="绿色航行不确定度 API 路由。",
    ),
    dict(
        asset_id="A09", asset_class="test_module", label="backend/tests/test_green_uncertainty.py",
        section="产物（第 43 行）；§3 判据 A7",
        quote="`backend/tests/test_green_uncertainty.py`",
        resolution="referenced_unresolved",
        check="os.path.exists('backend/tests/test_green_uncertainty.py') in this worktree",
        result="unresolved",
        note="37 例 pytest 的载体（A7 判据）；本工序未执行该测试（跨仓），不得视为已复现。",
    ),
    dict(
        asset_id="A10", asset_class="repro_script", label="scripts/run_green_uncertainty_p269w2_n07.py",
        section="产物（第 43 行）",
        quote="`scripts/run_green_uncertainty_p269w2_n07.py`",
        resolution="referenced_unresolved",
        check="os.path.exists('scripts/run_green_uncertainty_p269w2_n07.py') in this worktree",
        result="unresolved",
        note="一键复现脚本（重计算入口）。",
    ),
    dict(
        asset_id="A11", asset_class="documentation", label="docs/green_navigation/P269W2_N07_uncertainty_propagation.md",
        section="产物（第 43 行）",
        quote="`docs/green_navigation/P269W2_N07_uncertainty_propagation.md`",
        resolution="referenced_unresolved",
        check="os.path.exists('docs/green_navigation/P269W2_N07_uncertainty_propagation.md') "
              "in this worktree",
        result="unresolved",
        note="长文报告（本 markdown 为其摘要版）。",
    ),
    dict(
        asset_id="A12", asset_class="provenance_pointer", label="branch agent/m10831 @ commit 98efbb418",
        section="产物（第 43 行）",
        quote="分支 agent/m10831，commit 98efbb418",
        resolution="resolved_in_source",
        check="pointer string present verbatim and unique in markdown "
              "(commit object itself is in the source repo, not resolvable here)",
        result="resolved",
        note="仅登记指针文本本身可解（逐字定位命中）。commit 对象未在本仓拉取，"
             "故其内容与 40 位全哈希不在本工序核验范围（报告只给 9 位短哈希）。",
    ),
    dict(
        asset_id="A13", asset_class="code_pointer", label="api/green_shipping._gn_attained_index",
        section="§4 顺带修掉的真缺陷",
        quote="`api/green_shipping._gn_attained_index`",
        resolution="referenced_unresolved",
        check="os.path.exists('backend/api/green_shipping.py') in this worktree",
        result="unresolved",
        note="被点名的分母量纲缺陷函数（报告称已改为 kn 口径并加回归守卫）。本工序不评判该修复，"
             "只登记指针与定位。",
    ),
    dict(
        asset_id="A14", asset_class="withheld_dependency",
        label="规则要求值层（EEXI_required / CII_required 的规则依据）",
        section="§5 注意点 / 局限（末句）",
        quote="**要求值层与合规概率按 WITHHELD 处理**（规则系数离线转录不可复核）",
        resolution="declared_absent",
        check="report text declares the requirement-value layer WITHHELD; no rule document/coefficient "
              "table is attached in markdown",
        result="absent",
        note="报告自陈：规则系数离线转录不可复核。按 preserve_uncertainty 如实登记为缺失依赖，"
             "不补齐、不推断。",
    ),
]

# anchors = fields of the report body pinned to exact quotes (evidence table for the
# work-package report). Ordinal bookkeeping only; no statement is asserted as verified.
ANCHORS = [
    ("report_title", "报告标题", "P269W2-N07 EEXI/CII 端到端不确定度传播成熟化"),
    ("design_point", "算例几何/参数", "Lpp×B×T = 180×32×11.5 m，Cb=0.82，Capacity=35000 DWT"),
    ("eexi_required", "EEXI 要求值", "EEXI_required = 5.2318 gCO2/(t·nm)"),
    ("cii_required", "CII 要求值(2025)", "CII_required(2025) = 6.4397 gCO2/(t·nm)"),
    ("mc_settings", "MC 规模与种子", "MC N=20000（seed=20261110）"),
    ("reduction_chain", "归约链自证口径", "归约误差对**全 Holtrop+二分**逐样本复算实测"),
    ("figure_count", "图数声明", "（JSON + 5 图）"),
    ("deliverable_list", "产物清单起始", "产物：`backend/services/green_uncertainty.py`"),
    ("withheld_scope", "WITHHELD 范围", "**要求值层与合规概率按 WITHHELD 处理**"),
    ("provenance", "来源分支/commit", "分支 agent/m10831，commit 98efbb418"),
]


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    md = MD_PATH.read_text(encoding="utf-8")
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    log = {"package_id": PKG, "report_id": REPORT_ID, "checks": {}}

    log["checks"]["hash_recomputed_locally"] = {
        "sha256": digest, "pass": digest == CONTRACT_HASH}
    log["checks"]["chars_match"] = {
        "chars": len(md), "expected": CONTRACT_CHARS, "pass": len(md) == CONTRACT_CHARS}
    log["checks"]["bytes_utf8"] = {"bytes_utf8": len(raw), "pass": len(raw) == meta["bytes_utf8"]}
    log["checks"]["fetch_meta_hash_agree"] = {
        "fetch_meta_sha256": meta["sha256"], "pass": meta["sha256"] == digest}
    assert digest == CONTRACT_HASH, "FATAL: markdown sha256 != contract source_hash"
    assert len(md) == CONTRACT_CHARS, "FATAL: markdown char count != contract chars"

    # ---- locators: exact char span, unique in document
    assets = []
    for a in ASSETS:
        q = a["quote"]
        n = md.count(q)
        assert n == 1, "FATAL: quote not unique for %s (occurrences=%d): %r" % (a["asset_id"], n, q)
        s = md.index(q)
        e = s + len(q)
        exists = pathlib.Path(a["label"].strip("`")).exists() if a["asset_class"] not in (
            "figure", "provenance_pointer", "withheld_dependency", "artifact_bundle") else None
        if a["asset_class"] == "artifact_bundle":
            exists = pathlib.Path("artifacts/P269W2_N07").exists()
        assets.append({
            "asset_id": a["asset_id"],
            "asset_class": a["asset_class"],
            "label": a["label"],
            "in_report_section": a["section"],
            "resolution": a["resolution"],
            "resolution_check": {"check": a["check"], "result": a["result"]},
            "locator": {
                "method": "char_span",
                "start_char": s,
                "end_char": e,
                "start_line": line_of(md, s),
                "end_line": line_of(md, e - 1),
                "quote": q,
                "unique": True,
            },
            "note": a["note"],
        })
        if exists is not None:
            log.setdefault("local_path_checks", {})[a["asset_id"]] = bool(exists)
    log["checks"]["locators_unique"] = {"all_unique": True, "count": len(assets)}

    anchors = []
    for key, desc, q in ANCHORS:
        n = md.count(q)
        assert n == 1, "FATAL: anchor %s quote not unique (%d)" % (key, n)
        s = md.index(q)
        anchors.append({
            "anchor_id": key, "field": desc, "quote": q,
            "start_char": s, "end_char": s + len(q),
            "start_line": line_of(md, s), "unique": True,
        })
    log["checks"]["anchors_unique"] = {"all_unique": True, "count": len(anchors)}

    by_class = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
    by_res = {}
    for a in assets:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    # cross-check: figures declared in the report ("5 图") vs platform record figures[]
    plat_figs = meta.get("platform_figures") or []
    fig_assets = [a for a in assets if a["asset_class"] == "figure"]
    log["checks"]["figure_count_consistency"] = {
        "markdown_declared": 5,
        "registered_from_record": len(plat_figs),
        "registered_as_assets": len(fig_assets),
        "pass": len(plat_figs) == 5 == len(fig_assets),
    }
    assert fig_assets and len(plat_figs) == len(fig_assets) == 5

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "source": {
            "uri": "tensor://reports/" + REPORT_ID,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": CONTRACT_TITLE,
            "platform_title": meta.get("platform_title"),
            "title_matches_contract": meta.get("platform_title") == CONTRACT_TITLE,
            "scenario_key": SCENARIO,
            "platform_scenario_key": meta.get("platform_scenario_key"),
            "platform_figures": plat_figs,
            "platform_tags": meta.get("platform_tags") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "anchors": len(anchors),
        },
        "assets": assets,
        "anchors": anchors,
        "claims": [],
        "claims_note": "任务类型 01 只登记资产，不做抽取与分类（objective.classify_report_type=false）；"
                       "按 no_forced_claim_generation，claims=[] 为合法完整结果。",
        "integrity": {
            "quote_uniqueness": True,
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "locator_method": "char_span over utf-8 decoded markdown; uniqueness = exact match count == 1",
            "no_cross_report_access": True,
        },
    }
    log["checks"]["title_matches_contract"] = {"pass": manifest["source"]["title_matches_contract"]}
    log["checks"]["scenario_key_matches_contract"] = {
        "platform": manifest["source"]["platform_scenario_key"], "contract": SCENARIO,
        "pass": manifest["source"]["platform_scenario_key"] == SCENARIO,
    }

    # ---- acceptance gates (contract.acceptance)
    acc = {}
    acc["valid_json"] = True
    acc["source_hash_matches"] = digest == CONTRACT_HASH
    acc["source_locator_resolvable"] = all(
        md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"]
        and md.count(a["locator"]["quote"]) == 1 for a in assets)
    ids = [a["asset_id"] for a in assets]
    acc["no_duplicate_ids"] = len(ids) == len(set(ids))
    acc["all_claims_have_evidence_or_explicit_unresolved_status"] = all(
        ("evidence_locator" in c) or ("status" in c) for c in manifest["claims"]) and True
    log["acceptance"] = acc
    assert acc["source_hash_matches"] and acc["source_locator_resolvable"] and acc["no_duplicate_ids"]

    (OUTDIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    envelope = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + digest,
            "source_field": "markdown",
            "producer": "TENSOR_AGENT_USER via scripts/kf_wp12445_fetch.py + "
                        "scripts/kf_wp12445_register.py",
            "emitted_at": "2026-11-12",
            "notes": "按 char_span 逐字定位；claims=[] 为契约允许（本工序不抽取、不分类）。",
        },
        "outputs": {"asset_manifest.json": manifest},
    }
    (OUTDIR / "kf_result.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- schema validation
    from jsonschema import Draft202012Validator
    env_schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    errs = sorted(Draft202012Validator(env_schema).iter_errors(envelope), key=lambda e: e.path)
    log["checks"]["kf_result_schema"] = {
        "pass": not errs, "errors": [e.message for e in errs][:5]}

    man_schema = json.loads((OUTDIR / "asset_manifest.schema.json").read_text(encoding="utf-8"))
    errs2 = sorted(Draft202012Validator(man_schema).iter_errors(manifest), key=lambda e: e.path)
    log["checks"]["asset_manifest_schema"] = {
        "pass": not errs2, "errors": [e.message for e in errs2][:5]}
    log["acceptance"]["schema_pass"] = not errs and not errs2

    (OUTDIR / "verify_log.json").write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": manifest["counts"], "acceptance": log["acceptance"],
                      "kf_result_schema_pass": log["checks"]["kf_result_schema"]["pass"],
                      "manifest_schema_pass": log["checks"]["asset_manifest_schema"]["pass"],
                      "sha256": digest}, ensure_ascii=False, indent=2))
    if errs or errs2:
        raise SystemExit("FATAL: schema validation failed")


if __name__ == "__main__":
    main()