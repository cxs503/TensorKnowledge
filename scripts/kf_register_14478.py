#!/usr/bin/env python3
"""Register the source assets of report 14478 (KF wp-14478-01, task_type=01-asset-registration).

No extraction: claims are intentionally an empty array (the contract says claims may be empty and
classify_report_type=false). Every registered asset carries
(a) a locator whose quote is re-sliced out of the pinned markdown (char span + line span + uniqueness),
(b) an explicit payload status (in record / external URL / external repo path / missing payload),
so unresolved items stay visibly unresolved instead of being upgraded to "present".

Inputs : docs/wp-14478-01/source.md, docs/wp-14478-01/source_meta.json (written by scripts/kf_fetch_14478.py)
Outputs: docs/wp-14478-01/asset_manifest.json, docs/wp-14478-01/kf_result.wp-14478-01.json
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wp-14478-01"
PACKAGE_ID = "wp-14478-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "14478"
SOURCE_URI = "tensor://reports/14478"
CONTRACT_HASH = "8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0"
CONTRACT_CHARS = 6156
CONTRACT_TITLE = "CASE-CYLINDER-DRAG-FVM: TensorFVM DFG 2D-1 cylinder drag case (per-quantity <5% verdict)"
CONTRACT_SCENARIO = "case-cylinder-drag-fvm"

# (asset_id, asset_class, label, section, anchor, payload, note)
#   anchor  = verbatim substring of the pinned markdown, asserted to occur exactly once
#   payload = dict(status, checked_how[, declared][, evidence])
PLAN = [
    (
        "A01", "source_document", "tensor://reports/14478 markdown（本包登记的唯一原文）", "全文（document locator）",
        "## ① 问题与参考值出处",
        {"status": "in_report_record",
         "checked_how": "GET /tensor/reports/14478 → field markdown; sha256 + char count recomputed and compared with the work-package contract",
         "evidence": {"sha256": CONTRACT_HASH, "chars": CONTRACT_CHARS, "bytes_utf8": 9430}},
        "Whole-document locator: span covers the entire pinned markdown; the envelope provenance.source_hash is this asset's hash.",
    ),
    (
        "A02", "reference_authority_page", "Turek 组 FeatFlow DFG 2D-1 官网页（Re=20 参考值来源）", "① 参考值出处",
        "https://wwwold.mathematik.tu-dortmund.de/~featflow/en/benchmarks/cfdbenchmarking/flow/dfg_benchmark1_re20.html",
        {"status": "external_url_declared",
         "checked_how": "URL quoted verbatim from the markdown; not fetched by this package (external network, and the source itself reports fetch restrictions in ‘生态摩擦’ item 4)",
         "declared": {"used_for": "C_D=5.57953523384 / C_L=0.010618948146 / p_diff=0.11752016697 Pa (§③ 参考值表)"}},
        "Payload bytes are NOT registered here: the archived copy is A03.",
    ),
    (
        "A03", "reference_page_archive", "归档页 featflow_re20.html（Re=20 官网页原文）", "⑥ 失败模式与工件",
        "featflow_re20.html",
        {"status": "external_repo_path_declared",
         "checked_how": "path quoted verbatim; the file lives in the TensorFVM repo worktree (artifacts/case-cylinder-drag-fvm/reference/), which is outside this report record and this TensorKnowledge worktree — no bytes fetched or hashed by this package"},
        "Registered as a path+role only; its sha256 is said to be recorded in fetch_manifest.json (A05), not re-derived here.",
    ),
    (
        "A04", "reference_page_archive", "归档页 featflow_re100.html（Re=100 同族页，本算例未用其数值）", "⑥ 失败模式与工件",
        "featflow_re100.html",
        {"status": "external_repo_path_declared",
         "checked_how": "same boundary as A03 — path quoted verbatim, bytes not fetched"},
        "The report does not state that any Re=100 value enters the verdict; it is listed only among archived pages.",
    ),
    (
        "A05", "provenance_manifest", "fetch_manifest.json（URL + sha256 归档清单）", "⑥ 失败模式与工件",
        "`fetch_manifest.json`（URL + sha256）",
        {"status": "external_repo_path_declared",
         "checked_how": "path and declared content (‘URL + sha256’) quoted verbatim; file not read by this package"},
        "The per-URL sha256 values are NOT reproduced here — reading them would require the TensorFVM worktree.",
    ),
    (
        "A06", "reference_data", "reference.json（正则解析结果 + 匹配位置）", "⑥ 失败模式与工件",
        "`reference.json`（解析结果 + 匹配位置）",
        {"status": "external_repo_path_declared",
         "checked_how": "path quoted verbatim; file not read by this package"},
        "The three reference numbers are registered as quoted report text (source_document quotes in the delivery report), not from this JSON.",
    ),
    (
        "A07", "reference_parser", "fetch_reference.py（抓取→正则→reference.json，含 drift 比对）", "① 参考值出处",
        "`artifacts/case-cylinder-drag-fvm/reference/fetch_reference.py`（抓取→正则→`reference.json`",
        {"status": "external_repo_path_declared",
         "checked_how": "path quoted verbatim; script not executed by this package"},
        "零手抄 mechanism claimed by the source; this package does not re-run it (out of boundary).",
    ),
    (
        "A08", "case_harness", "scripts/case_cylinder_drag_fvm.py（solve / analyze / report 三入口）", "② 方法与实现",
        "本单新增算例级 harness `scripts/case_cylinder_drag_fvm.py`（三个入口）",
        {"status": "external_repo_path_declared",
         "checked_how": "path quoted verbatim; harness not executed by this package (its runs/ output is absent, A11)"},
        "Only the declared接口面 (3 entry points) is registered; no behaviour is asserted.",
    ),
    (
        "A09", "contract_test", "tests/test_case_cylinder_drag_fvm.py（合成数据契约测试）", "⑥ 失败模式与工件",
        "`tests/test_case_cylinder_drag_fvm.py`：合成数据契约测试",
        {"status": "external_repo_path_declared",
         "checked_how": "path quoted verbatim; the file is not in this worktree and was not run",
         "declared": {"claimed_result": "pytest tests/test_case_cylinder_drag_fvm.py → 1 passed"}},
        "The claim ‘1 passed’ is the source's own statement (declared_in_source_only), NOT re-executed here.",
    ),
    (
        "A10", "report_tool", "artifacts/case-cylinder-drag-fvm/tools/post_report.py（报告投递工具）", "⑥ 失败模式与工件",
        "`artifacts/case-cylinder-drag-fvm/tools/post_report.py`：报告投递工具",
        {"status": "external_repo_path_declared",
         "checked_how": "path quoted verbatim; file not read by this package"},
        "No payload bytes registered.",
    ),
    (
        "A11", "solver_run_output", "artifacts/case-cylinder-drag-fvm/runs/（集群三档网格结果）", "⑥ 失败模式与工件",
        "`artifacts/case-cylinder-drag-fvm/runs/`（集群结果）",
        {"status": "declared_payload_missing",
         "checked_how": "the markdown itself states this path is missing (‘缺’, ‘本单未产出’); nothing to fetch, and inventing content is forbidden",
         "declared": {"missing_because": "§④ FAIL：三作业排队 9.6 min 未派发，本单预算内未取回任何 result.json"}},
        "Unresolved by design: the deliverable is the missing-payload record, not the numbers.",
    ),
    (
        "A12", "analysis_output", "artifacts/case-cylinder-drag-fvm/analysis/（判据/收敛/分项/图件）", "⑥ 失败模式与工件",
        "`analysis/`（图件）",
        {"status": "declared_payload_missing",
         "checked_how": "same line as A11 declares runs/ and analysis/ both absent; not synthesised here",
         "declared": {"missing_because": "analysis requires runs/, which was never retrieved"}},
        "Unresolved by design.",
    ),
    (
        "A13", "native_solver_outputs", "包内原生求解产物：result.json / fields.npz / history.json", "② 方法与实现",
        "（`result.json` / `fields.npz` / `history.json`）",
        {"status": "declared_payload_missing",
         "checked_how": "output filenames quoted verbatim as the declared native format; no instance exists (runs/ absent, A11)"},
        "Format declaration only — zero instances registered.",
    ),
    (
        "A14", "repo_doc", "docs/benchmarks-index.md（仓内基准索引，含 64×24 历史误差 13.36%）", "⑥ 失败模式与工件",
        "`docs/benchmarks-index.md` 记录 64×24 曾出现",
        {"status": "external_repo_path_declared",
         "checked_how": "path quoted verbatim; the TensorFVM repo doc is not present in this worktree and was not read",
         "declared": {"quoted_number": "C_D 误差 ≈13.36%（源文自述的历史记录，本包未复核）"}},
        "The 13.36% figure is registered as the source's own statement, not verified.",
    ),
    (
        "A15", "report_document", "docs/case-cylinder-drag-fvm/report.md（report 入口的生成目标）", "② 方法与实现",
        "--out docs/case-cylinder-drag-fvm/report.md",
        {"status": "declared_in_source_only",
         "checked_how": "path appears only inside the repro command block of the markdown; no bytes of it are in the record, so its existence is unconfirmed here"},
        "Self-referential generator target of the registered report itself; not resolved by this package.",
    ),
    (
        "A16", "solver_code", "tensorfvm.verification.dfg 包（贴体网格 + SIMPLE/Rhie–Chow + 壁面牵引/压力重构）", "② 方法与实现",
        "`tensorfvm.verification.dfg` 提供贴体网格 + SIMPLE/Rhie–Chow",
        {"status": "external_repo_path_declared",
         "checked_how": "module path quoted verbatim; TensorFVM package not installed/checked out in this worktree — capability claims (REAL vs MOCK) are NOT assessed by this package"},
        "Evidence-level grading of the solver is out of scope for task_type=01.",
    ),
    (
        "A17", "reference_constant", "包内常量 tensorfvm.verification.dfg.REFERENCE（与 reference.json 漂移比对，drift=无）", "① 参考值出处",
        "`tensorfvm.verification.dfg.REFERENCE`",
        {"status": "external_repo_path_declared",
         "checked_how": "symbol quoted verbatim; not readable in this worktree",
         "declared": {"drift": "无（源文自述）"}},
        "‘drift = 无’ is the source's assertion; this package neither recomputes nor upgrades it.",
    ),
    (
        "A18", "cluster_job", "集群作业三连（/tmp/m15406_dfg_*，各档独立作业）", "② 方法与实现",
        "PYTHONPATH=src python -m tensorfvm.verification.dfg --output /tmp/m15406_dfg_64x24",
        {"status": "declared_payload_missing",
         "checked_how": "command quoted verbatim; the three /tmp outputs were never retrieved (§④) and /tmp is not part of any repo — nothing registered",
         "declared": {"jobs": ["m15406_dfg_64x24", "m15406_dfg_128x48", "m15406_dfg_256x96"], "state_at_write": "queued"}},
        "Only the 64x24 command line is the locator anchor; the other two are named in declared.jobs because each /tmp token is quoted in the source.",
    ),
    (
        "A19", "figure_set", "analyze 生成的 7 张图（运行点/场量/收敛等）", "⑥ 失败模式与工件",
        "阻力分项与 7 张图",
        {"status": "declared_payload_missing",
         "checked_how": "the count ‘7 张图’ is quoted verbatim; analysis/ is absent (A12) and the markdown names no figure filenames",
         "declared": {"figure_count": 7}},
        "Individual figure names are NOT registered: the source does not name them, and inventing names is forbidden.",
    ),
    (
        "A20", "solver_config", "包内配置项 SolverConfig.tolerance（收敛判据 1e-6）", "③ 参数表",
        "`SolverConfig.tolerance`",
        {"status": "external_repo_path_declared",
         "checked_how": "symbol quoted verbatim; source tree not present in this worktree"},
        "Parameter table value (1e-6) is content of the source, not re-measured.",
    ),
]


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(out_dir: Path = OUT) -> tuple[dict, dict]:
    source = (out_dir / "source.md").read_text(encoding="utf-8")
    meta = json.loads((out_dir / "source_meta.json").read_text(encoding="utf-8"))
    record = meta["record"]
    if sha256_hex(source) != CONTRACT_HASH:
        raise SystemExit("pinned source.md does not match the contract hash — refusing to register")
    if len(source) != CONTRACT_CHARS:
        raise SystemExit("pinned source.md does not match the contract char count — refusing to register")
    if record.get("title") != CONTRACT_TITLE or record.get("scenario_key") != CONTRACT_SCENARIO:
        raise SystemExit("platform record title/scenario_key drifted from the contract — refusing to register")

    assets = []
    for asset_id, asset_class, label, section, anchor, payload, note in PLAN:
        hits = source.count(anchor)
        if hits != 1:
            raise SystemExit(f"{asset_id}: anchor occurs {hits} times (must be exactly 1): {anchor!r}")
        start = source.index(anchor)
        end = start + len(anchor)
        if asset_id == "A01":
            quote, method = source[:200], "document"
            start, end = 0, len(source)
        else:
            quote, method = anchor, "char_span"
        assets.append(
            {
                "asset_id": asset_id,
                "asset_class": asset_class,
                "label": label,
                "in_report_section": section,
                "locator": {
                    "method": method,
                    "source_field": "markdown",
                    "start_char": start,
                    "end_char": end,
                    "start_line": source.count("\n", 0, start) + 1,
                    "end_line": source.count("\n", 0, max(end - 1, start)) + 1,
                    "quote": quote,
                    "unique": source.count(quote) == 1,
                },
                "payload": payload,
                "note": note,
            }
        )

    by_class: dict[str, int] = {}
    by_payload: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_payload[a["payload"]["status"]] = by_payload.get(a["payload"]["status"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "objective": {"register_assets": True, "classify_report_type": False},
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": CONTRACT_HASH,
            "chars": len(source),
            "bytes_utf8": len(source.encode("utf-8")),
            "contract_chars": CONTRACT_CHARS,
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "platform_mission_id": record.get("mission_id"),
            "platform_status": record.get("status"),
            "platform_created_at": record.get("created_at"),
            "platform_tags": record.get("tags", []),
            "platform_figures": record.get("figures", []),
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_payload_status": by_payload,
            "reference_values_quoted": 3,
            "claims": 0,
        },
        "assets": assets,
        "claims": [],
        "claims_note": (
            "claims intentionally empty: contract objective is asset registration only "
            "(classify_report_type=false, no extraction). Filling claims here would fabricate knowledge "
            "objects that belong to task_type 03."
        ),
        "integrity": {
            "hash_recomputed_locally": True,
            "hash_matches_contract": sha256_hex(source) == CONTRACT_HASH,
            "chars_match_contract": len(source) == CONTRACT_CHARS,
            "all_locators_unique_quotes": all(a["locator"]["unique"] for a in assets),
            "verified_by": "scripts/kf_verify_14478.py (re-fetches the report independently)",
            "no_file_outside_worktree_written": True,
            "other_report_ids_touched": 0,
        },
        "boundaries": {
            "only_report_id": REPORT_ID,
            "other_reports_read": False,
            "upstream_artifacts_rewritten": False,
            "claims_marked_verified": 0,
        },
    }
    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + CONTRACT_HASH,
            "producer": "kf-wp14478-01 asset registration (scripts/kf_register_14478.py)",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": "hash = sha256 of the exact UTF-8 bytes of the report markdown field; recomputed from the platform on every verify run",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    return manifest, envelope


def main() -> int:
    manifest, envelope = build()
    (OUT / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT / "kf_result.wp-14478-01.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"assets={manifest['counts']['assets']} by_payload={manifest['counts']['by_payload_status']}")
    print(f"claims=0 classes={len(manifest['counts']['by_class'])}")
    print("wrote asset_manifest.json + kf_result.wp-14478-01.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())