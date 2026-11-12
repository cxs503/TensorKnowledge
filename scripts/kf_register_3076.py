#!/usr/bin/env python3
"""Register the source assets of report 3076 (KF wp-3076-01, task_type=01-asset-registration).

No extraction: claims are intentionally an empty array. Every registered asset carries
(a) a locator whose quote is recomputed out of the pinned markdown (char span + line span + uniqueness),
(b) an explicit payload status (present / external / 404 / out-of-scope-by-boundary),
so unresolved items stay visibly unresolved instead of being upgraded to "verified".

Inputs : docs/wp-3076-01/source.md, docs/wp-3076-01/source_meta.json (written by scripts/kf_fetch_3076.py)
Outputs: docs/wp-3076-01/asset_manifest.json, docs/wp-3076-01/kf_result.wp-3076-01.json
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "wp-3076-01"
PACKAGE_ID = "wp-3076-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "3076"
SOURCE_URI = "tensor://reports/3076"
CONTRACT_HASH = "9b7bb2427af8a1b4a7f229971492c52fc691737a7742b4b703ce4e41cea464c1"

# (asset_id, asset_class, label, section, anchor, payload, note)
#   anchor   = verbatim substring of the pinned markdown, asserted to occur exactly once
#   payload  = dict(status, checked_how[, evidence])
PLAN = [
    (
        "A01", "source_document", "tensor://reports/3076 markdown（本包登记的唯一原文）", "document",
        "## ① 案例介绍",
        {"status": "in_report_record",
         "checked_how": "GET /tensor/reports/3076 → field markdown; sha256 + char count recomputed and compared with the work-package contract",
         "evidence": {"sha256": CONTRACT_HASH, "chars": 3712}},
        "Whole-document locator: span covers the entire pinned markdown; the envelope provenance.source_hash is this asset's hash.",
    ),
    (
        "A02", "negative_control_manuscript", "封存稿 manuscript.md（246 行、6 图）", "① 对象表 / ② 步骤1",
        "papers/_sealed/ice-wave-mechanics-r2/manuscript.md",
        {"status": "external_not_in_record",
         "checked_how": "path text is quoted verbatim from the markdown; the file itself lives in the paper-line repo (papers/), which is outside this report record — not fetched by this package"},
        "Negative control (known FAIL). 6 embedded figures of that manuscript are not enumerated here: the report does not name them, and inventing names is forbidden.",
    ),
    (
        "A03", "evidence_base_report", "证据基 Report #823", "① 对象表",
        "证据基 Report #823",
        {"status": "cross_report_out_of_scope",
         "checked_how": "referenced by id only; work-package boundary forbids reading any report_id other than 3076, so its contents/hash are NOT checked here"},
        "Deliberately unresolved: resolving it requires a separate cross-report work package.",
    ),
    (
        "A04", "review_report", "异族确认评审 Report #961（判 FAIL）", "① 背景",
        "Report #961",
        {"status": "cross_report_out_of_scope",
         "checked_how": "same boundary as A03 — id cited in text, record not read"},
        "The report explicitly states its coth/tanh numbers do not match #961 (74.19%/37.5%); that divergence is a property of the source, not resolved by this package.",
    ),
    (
        "A05", "defect_seal", "SEAL.md（H1–H8 硬伤清单）", "① 背景 / ② 步骤1",
        "SEAL.md 列了 H1–H8 八类硬伤",
        {"status": "external_not_in_record",
         "checked_how": "quoted path text only; SEAL.md lives in the paper-line repo, not in the report record"},
        "Upstream input of the gate; registering it does not validate its content.",
    ),
    (
        "A06", "gate_implementation", "papers/tools/manuscript_gate.py（11 项 checks 实现）", "② 步骤2",
        "`papers/tools/manuscript_gate.py`：统一数字规范化",
        {"status": "external_not_in_record",
         "checked_how": "quoted path text only; source file lives in the paper-line repo"},
        "The claim 'only reads the audited manuscript' (mtime assertion test) is a statement of the source and is NOT re-verified here.",
    ),
    (
        "A07", "check_registry", "11 项 check 标识符（struct…arith）", "② 步骤1",
        "struct / figref / figdata / numtrace / formula / overclaim / statdof / implmethod / repro / placeholder / arith",
        {"status": "in_report_record",
         "checked_how": "the identifier list is enumerated verbatim inside the located span; count recomputed from the span (see check_id_count)"},
        "Registered as a symbol list only — no semantics, thresholds or per-check verdicts are extracted here.",
    ),
    (
        "A08", "positive_control_tree", "正控目录 papers/data/gate-2026-11-03/control/", "① 对象表 / ② 步骤3",
        "`papers/data/gate-2026-11-03/control/`",
        {"status": "external_not_in_record",
         "checked_how": "quoted path text only; the tree is created in the paper-line repo and is not part of this report record"},
        "Positive control (must PASS, 0 HARD). Its internal files are registered individually as A09–A14.",
    ),
    (
        "A09", "solver_code", "control/solver.py（tanh 边界条件二分法参考解）", "② 步骤3",
        "`solver.py`（tanh 边界条件）",
        {"status": "external_not_in_record", "checked_how": "quoted path text only; body not in the record"},
        "Numeric correctness of the solver is a claim of the source report, not re-run by this package.",
    ),
    (
        "A10", "evidence_base", "control/evidence.json（正控证据基）", "② 步骤3",
        "`evidence.json`",
        {"status": "external_not_in_record", "checked_how": "quoted path text only; body not in the record"},
        "Same name as the sealed-tree evidence base (Report #823); the two are distinct files — this package registers the positive-control one only.",
    ),
    (
        "A11", "figure_builder", "control/make_figures.py（图件生成脚本）", "② 步骤3",
        "`make_figures.py`",
        {"status": "external_not_in_record", "checked_how": "quoted path text only; body not in the record"},
        "",
    ),
    (
        "A12", "data_tables", "control/data/*.csv（图件数值源，glob 引用）", "② 步骤3",
        "`data/*.csv`",
        {"status": "external_not_in_record",
         "checked_how": "glob pattern, not a file list; the report does not enumerate the individual CSV names"},
        "Glob reference registered as-is. Individual CSV files are unresolved (count unknown) — no names invented.",
    ),
    (
        "A13", "figure_payloads", "control/figures/*.png（正控图件，glob 引用）", "② 步骤3",
        "`figures/*.png`",
        {"status": "external_not_in_record",
         "checked_how": "glob pattern; individual PNG names not enumerated by the report"},
        "Distinct from the platform record figures A17–A19: those are the report's own three figures.",
    ),
    (
        "A14", "figure_metadata", "control/figures_metadata.json（内嵌数值数组）", "② 步骤3",
        "`figures_metadata.json`",
        {"status": "external_not_in_record", "checked_how": "quoted path text only; body not in the record"},
        "",
    ),
    (
        "A15", "recompute_artifact", "coth_tanh_impact.json（H1 独立复算产物）", "② 步骤4",
        "`coth_tanh_impact.json`",
        {"status": "external_not_in_record", "checked_how": "quoted path text only; body not in the record"},
        "The percentages 0.37%→25.02% quoted in ③/⑥ are the source's numbers; they are not recomputed by this registration package.",
    ),
    (
        "A16", "dev_toolchain", "Python 3.11 + pytest 19 passed + matplotlib", "② 步骤5",
        "Python 3.11 + pytest 19 passed + matplotlib",
        {"status": "declared_in_source_only",
         "checked_how": "declared in text; this package does not re-run the paper-line test suite (different repo, different toolchain)"},
        "19 passed is an unverified declaration from the source, carried forward as such.",
    ),
    (
        "A17", "platform_figure", "gate_state_matrix.png（图1：11 checks × 2 稿状态矩阵）", "④ 结果图",
        "状态矩阵（11 checks × 2 稿）",
        {"status": "declared_payload_missing",
         "checked_how": "record.figures[0] gives name+caption; GET /tensor/reports/3076/figures/gate_state_matrix.png returned HTTP 404 'figure not found'",
         "evidence": {"record_name": "gate_state_matrix.png", "http_status": 404}},
        "Registered from the platform record (name + caption verbatim). PNG bytes are NOT stored in this report record — explicitly unresolved, not assumed present.",
    ),
    (
        "A18", "platform_figure", "gate_numtrace_dev.png（图2：数值溯源偏差分布）", "④ 结果图",
        "数值溯源偏差分布（tol=5e-3 线）",
        {"status": "declared_payload_missing",
         "checked_how": "record.figures[1] gives name+caption; figure payload endpoint probed for A17 returned 404, so the same endpoint was recorded as unusable rather than assumed to work per-figure",
         "evidence": {"record_name": "gate_numtrace_dev.png", "http_status": 404}},
        "See A17 for the payload-endpoint evidence; no per-figure 200 was observed.",
    ),
    (
        "A19", "platform_figure", "gate_coth_tanh.png（图3：coth/tanh 误式代价曲线）", "④ 结果图",
        "coth/tanh 误式代价曲线",
        {"status": "declared_payload_missing",
         "checked_how": "record.figures[2] gives name+caption; payload endpoint returned 404 for the checked figure name",
         "evidence": {"record_name": "gate_coth_tanh.png", "http_status": 404}},
        "Caption says '含 3%/15% 线' — that is the source's caption text, registered verbatim, not verified against an image.",
    ),
]


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build() -> tuple[dict, dict]:
    source = (OUT / "source.md").read_text(encoding="utf-8")
    meta = json.loads((OUT / "source_meta.json").read_text(encoding="utf-8"))
    record = meta["record"]
    if sha256_hex(source) != CONTRACT_HASH:
        raise SystemExit("pinned source.md does not match the contract hash — refusing to register")

    assets = []
    for asset_id, asset_class, label, section, anchor, payload, note in PLAN:
        hits = source.count(anchor)
        if hits != 1:
            raise SystemExit(f"{asset_id}: anchor occurs {hits} times (must be exactly 1): {anchor!r}")
        start = source.index(anchor)
        end = start + len(anchor)
        if asset_id == "A01":
            start, end = 0, len(source)
            quote = source[: len(anchor)]
            method = "document"
        else:
            quote = anchor
            method = "char_span"
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

    check_id_span = next(a for a in assets if a["asset_id"] == "A07")["locator"]["quote"]
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
            "contract_chars": 3712,
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
            "check_id_count": len([t for t in check_id_span.split(" / ") if t.strip()]),
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
            "hash_matches_contract": True,
            "chars_match_contract": len(source) == 3712,
            "all_locators_unique_quotes": all(a["locator"]["unique"] for a in assets),
            "verified_by": "scripts/kf_verify_3076.py (re-fetches the report independently)",
            "no_file_outside_worktree_written": True,
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
            "producer": "kf-wp3076-01 asset registration (scripts/kf_register_3076.py)",
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
    (OUT / "kf_result.wp-3076-01.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"assets={manifest['counts']['assets']} by_payload={manifest['counts']['by_payload_status']}")
    print(f"check_ids={manifest['counts']['check_id_count']} claims=0")
    print("wrote asset_manifest.json + kf_result.wp-3076-01.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())