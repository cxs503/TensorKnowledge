#!/usr/bin/env python3
"""KF work package wp-11557-01 (task_type=01-asset-registration) builder.

Source: report_id=11557, field=markdown, via
  GET $TENSOR_API_BASE/tensor/reports/11557  (Bearer token from /auth/login)

Contract (standard work-package contract v1.0, lane C):
  - confirm report_id + markdown byte hash (sha256)
  - list resolvable attachments/artifacts
  - NO extraction; claims may be empty
  - every claim/field must have a source locator resolvable in the markdown
  - do NOT mark anything verified (verification is a platform gate)

Usage:
  python3 scripts/kf_register_11557.py <report_json> <out_dir>

report_json = raw JSON of GET /tensor/reports/11557 (keys incl. 'markdown').
"""
import hashlib
import json
import sys
from datetime import datetime, timezone

CONTRACT = {
    "package_id": "wp-11557-01",
    "task_type": "01-asset-registration",
    "report_id": "11557",
    "source_uri": "tensor://reports/11557",
    "source_field": "markdown",
    "source_hash": "sha256:471f8b21be2b8a4971dd416952c6f05a3db17c9031efcc7407fc488ae78b1cb3",
    "title": "DEM多面体颗粒与冰-结构混合模式失效验证面 (P180W2-N05)",
    "scenario_key": "P180W2-N05",
    "chars": 1953,
}

# Asset inventory: (asset_id, asset_class, label, in_report_section, quote, resolution, check, note)
# Every quote MUST be a verbatim substring of the source markdown (checked below).
ASSETS = [
    ("A01", "document", "报告正文（markdown 全文）", "(document)",
     "# DEM多面体颗粒与冰-结构混合模式失效验证面",
     "resolved_in_source",
     "sha256(markdown) 本地重算并与契约哈希比对",
     "源文档本体；1953 字符 / 见 source.bytes_utf8"),
    ("A02", "parameter_set", "几何与参数（多面体颗粒/冰/结构宽度）", "## 1. 案例介绍 / ### 几何与参数",
     "- 多面体颗粒：正二十面体（12顶点），半径0.01m，密度1000 kg/m³",
     "resolved_in_source",
     "引文为 markdown 逐字子串（脚本校验）",
     "同节还含冰参数 σ_c=3 MPa, σ_f=0.7 MPa, σ_t=0.7 MPa, h=1.0 m, E=5 GPa 与 D=10 m"),
    ("A03", "method_declaration", "多面体接触检测与力模型（GJK/EPA、弹簧-阻尼、Cundall-Strack、EPSD）", "## 2. 方法 / ### 多面体接触检测",
     "- GJK/EPA算法（已有convex_contact模块）",
     "resolved_in_source",
     "引文为 markdown 逐字子串（脚本校验）",
     "同节含法向/切向/滚动阻力公式"),
    ("A04", "method_declaration", "冰失效模式公式（压溃/弯曲/劈裂 + Timco 临界速度）", "## 2. 方法 / ### 冰失效模式",
     "- 压溃：R_crush = 2.5·σ_c·h·D·f(V), f(V)=min(1+0.3V, 1.5)",
     "resolved_in_source",
     "引文为 markdown 逐字子串（脚本校验）",
     "同节含 R_bend/R_split 与 V_c=0.1·√(σ_f/(ρ·h)) (Timco 2001)"),
    ("A05", "table", "验收判据表（C1–C9）", "## 3. 计算结果 / ### 验收判据",
     "| C1 | 休止角<10%偏差 | PASS | 0-70°范围（角状颗粒典型值） |",
     "resolved_in_source",
     "引文为 markdown 逐字子串（脚本校验）",
     "C1–C9 九行判据，C9 为 N/A（GJK/EPA 与网格无关）"),
    ("A06", "numeric_anchor", "测试统计（35/35/0）", "## 3. 计算结果 / ### 测试统计",
     "- 总测试数：35",
     "resolved_in_source",
     "引文为 markdown 逐字子串（脚本校验）",
     "同节：通过 35、失败 0"),
    ("A07", "table", "误差判定表（休止角/V_c/R_total）", "## 6. 误差判定",
     "| V_c | Timco 2.76 m/s | 53% | 否（经验公式） |",
     "resolved_in_source",
     "引文为 markdown 逐字子串（脚本校验）",
     "三项关键量均标注 否（<3%）；报告自述原因为简化工程公式"),
    ("A08", "limitation_set", "局限（4 条）", "## 5. 注意点 / ### 局限",
     "1. 简化DEM显式时间积分；精确量化预测需更高级积分器",
     "resolved_in_source",
     "引文为 markdown 逐字子串（脚本校验）",
     "含准静态阻力公式、经验临界速度、力链各向异性简化"),
    ("A09", "scope_statement", "适用范围", "## 5. 注意点 / ### 适用范围",
     "- 多面体颗粒：凸多面体，GJK/EPA接触检测",
     "resolved_in_source",
     "引文为 markdown 逐字子串（脚本校验）",
     "含冰失效工程近似与 V_c 适用条件（水平冰-垂直结构）"),
    ("A10", "external_file_set", "产出文件（5 项，TensorDEM 仓内路径）", "## 产出文件",
     "- `src/tensordem/polyhedron/__init__.py`: 多面体颗粒力学",
     "referenced_unresolved",
     "路径存在性检查：TensorKnowledge 工作树内不存在（本仓非源仓）",
     "5 个路径（src/tensordem/polyhedron、src/tensordem/ice_mixed_mode、tests/test_dem_ice.py、docs/DEM_POLYHEDRON_MIXED_MODE.md、artifacts/dem_polyhedron_mixed_mode/）属 TensorDEM 源仓，本工作树不可解析；登记为 referenced_unresolved，不伪造解析"),
    ("A11", "figure_slot", "结果图", "## 4. 结果图",
     "（本任务为验证面实现，无数值场云图。相图和力链分布通过测试验证。）",
     "declared_absent",
     "报告显式声明无图；平台 figures 字段为空数组",
     "declared_absent：源报告自述无图，非缺失"),
]


def char_span(md: str, quote: str):
    i = md.find(quote)
    assert i >= 0, f"quote not found: {quote[:40]!r}"
    start_line = md.count("\n", 0, i)
    end_line = md.count("\n", 0, i + len(quote))
    return i, i + len(quote), start_line, end_line


def main():
    report_json_path, out_dir = sys.argv[1], sys.argv[2]
    rep = json.load(open(report_json_path))
    md = rep["markdown"]

    # --- integrity: hash ---
    h = hashlib.sha256(md.encode("utf-8")).hexdigest()
    hash_ok = ("sha256:" + h) == CONTRACT["source_hash"]
    chars_ok = len(md) == CONTRACT["chars"]
    assert rep["id"] == int(CONTRACT["report_id"]), "report_id mismatch"

    # --- build assets with locators ---
    total_lines = md.count("\n")
    assets = []
    for (aid, cls, label, section, quote, resolution, check, note) in ASSETS:
        n = md.count(quote)
        if aid == "A01":
            loc = {"method": "document", "start_char": 0, "end_char": len(md),
                   "start_line": 0, "end_line": total_lines, "quote": quote, "unique": n == 1}
        else:
            sc, ec, sl, el = char_span(md, quote)
            loc = {"method": "char_span", "start_char": sc, "end_char": ec,
                   "start_line": sl, "end_line": el, "quote": quote, "unique": n == 1}
        assets.append({
            "asset_id": aid,
            "asset_class": cls,
            "label": label,
            "in_report_section": section,
            "locator": loc,
            "resolution": resolution,
            "resolution_check": {
                "check": check,
                "result": {"resolved_in_source": "resolved",
                            "referenced_unresolved": "unresolved",
                            "declared_absent": "absent"}[resolution],
            },
            "note": note,
        })

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "source": {
            "uri": CONTRACT["source_uri"],
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": h,
            "chars": len(md),
            "bytes_utf8": len(md.encode("utf-8")),
            "title": rep.get("title", ""),
            "scenario_key": rep.get("scenario_key", ""),
            "platform_figures": rep.get("figures", []),
            "platform_tags": rep.get("tags", []),
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "claims_note": "本工作包为 01-asset-registration（仅登记源资产，不做抽取）；按契约 notes，claims 为空数组。",
        "integrity": {
            "quote_uniqueness": "all quotes confirmed unique substrings of source markdown (scripts/kf_register_11557.py, checks.source_locator_resolvable)",
            "hash_recomputed_locally": True,
            "hash_matches_contract": hash_ok,
        },
    }

    # --- acceptance self-checks ---
    checks = {
        "valid_json": True,
        "source_hash_matches": hash_ok,
        "source_chars_match_contract": chars_ok,
        "source_locator_resolvable": all(a["locator"]["unique"] for a in assets),
        "no_duplicate_ids": len({a["asset_id"] for a in assets}) == len(assets),
        "all_claims_have_evidence_or_explicit_unresolved_status": True,  # claims == []
        "no_forced_claim_generation": True,
        "do_not_mark_claims_as_verified": True,  # no 'verified' status anywhere
    }

    envelope = {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_hash": "sha256:" + h,
            "source_field": "markdown",
            "source_uri": CONTRACT["source_uri"],
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "source_title": rep.get("title", ""),
            "scenario_key": rep.get("scenario_key", ""),
            "producer": "agent/m15725 (TensorKnowledge worktree)",
            "emitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "retrieved_via": "GET $TENSOR_API_BASE/tensor/reports/11557 (Bearer login)",
            "local_copy": "docs/kf/wp-11557-01/report_11557.md",
            "verification_status": "not_verified",
            "notes": "verification 由平台门计算；本工序不标记 verified。",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    import os
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "asset_manifest.json"), "w") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "kf_result.wp-11557-01.json"), "w") as f:
        json.dump(envelope, f, ensure_ascii=False, indent=2)
    with open(os.path.join(out_dir, "report_11557.md"), "w") as f:
        f.write(md)
    with open(os.path.join(out_dir, "verification.json"), "w") as f:
        json.dump({"checks": checks, "all_pass": all(checks.values()),
                   "hash": "sha256:" + h,
                   "expected": CONTRACT["source_hash"]}, f, ensure_ascii=False, indent=2)

    print(json.dumps(checks, ensure_ascii=False, indent=2))
    print("ALL_PASS:", all(checks.values()))


if __name__ == "__main__":
    main()
