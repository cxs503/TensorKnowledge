#!/usr/bin/env python3
"""wp-13272-01 · 01-asset-registration for report_id=13272 (only that report).

Registers the source report as an asset (byte-pinned markdown), its record metadata,
its one declared figure, and every artifact/symbol/standard reference the report text
names — WITHOUT extracting claims (contract objective: register_assets only).

Zero hand-copy: every quote registered here is a verbatim substring of the fetched
markdown located at run time; every record value is read from the API record.
If a needle is not found verbatim, the script exits non-zero (refuse to invent).

Usage:
  python3 scripts/wp13272_register_assets.py            # live: fetch report 13272
  python3 scripts/wp13272_register_assets.py --offline  # reuse work/wp-13272-01/source/
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
REPORT_ID = "13272"
PACKAGE_ID = "wp-13272-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/13272"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = "sha256:75ed781cefac9fee890f493c256dec8aea2e70795eca9d7a8bbfef1af1bcce90"
CONTRACT_CHARS = 4537
CONTRACT_TITLE = "CII 规则内核三副本单源化与 regime 语义修复（m13764）"
CONTRACT_SCENARIO = "green_navigation"

WT = pathlib.Path(__file__).resolve().parent.parent
SRC_DIR = WT / "work" / "wp-13272-01" / "source"
OUT_DIR = WT / "docs" / "kf" / PACKAGE_ID

# (suffix, kind, role, name, markdown_needle, extra)
# markdown_needle=None → record-only asset (no markdown locator).
REFERENCE_TABLE = [
    ("10", "source_code", "referenced_external_artifact",
     "backend/services/cii_required_value.py", "backend/services/cii_required_value.py",
     {"note": "implementation A — 权威口径（显式 regime，m1829 建）"}),
    ("11", "source_code", "referenced_external_artifact",
     "backend/api/green_shipping.py", "backend/api/green_shipping.py",
     {"note": "implementation B — 主 API 副本"}),
    ("12", "source_code", "referenced_external_artifact",
     "backend/modules/green_navigation_ice/mepc.py", "backend/modules/green_navigation_ice/mepc.py",
     {"note": "implementation C — 冰区链副本"}),
    ("13", "source_code", "referenced_external_artifact",
     "green_navigation_ice/api.py", "green_navigation_ice/api.py",
     {"note": "ice module API surface (compliance / model_audit 回显)"}),
    ("14", "tool", "referenced_external_artifact",
     "tools/cii_consistency_scan.py", "tools/cii_consistency_scan.py",
     {"note": "机器对账工具（年份 2019–2030 × 三实现）"}),
    ("15", "result_data", "referenced_external_artifact",
     "artifacts/cii_consistency_scan_*.json", "artifacts/cii_consistency_scan_*.json",
     {"note": "glob reference in section ③ heading; concrete instances = before/after"}),
    ("16", "result_data", "referenced_external_artifact",
     "artifacts/cii_consistency_scan_before.json", "artifacts/cii_consistency_scan_before.json",
     {"note": "基线：12/12 年份不一致"}),
    ("17", "result_data", "referenced_external_artifact",
     "artifacts/cii_consistency_scan_after.json", "artifacts/cii_consistency_scan_after.json",
     {"note": "修复后：0/12"}),
    ("18", "figure_file", "referenced_external_artifact",
     "artifacts/m13764_cii_consistency.png", "artifacts/m13764_cii_consistency.png",
     {"note": "section ④ 声明图；与 record.figures[0] 同名；同一图的字节副本经平台存储可达（见 ast-13272-03），repo 路径本身不可回解"}),
    ("19", "test_file", "referenced_external_artifact",
     "tests/test_cii_single_source_consistency.py", "tests/test_cii_single_source_consistency.py",
     {"note": "153 passed"}),
    ("20", "test_dir", "referenced_external_artifact",
     "backend/modules/green_navigation_ice/tests", "backend/modules/green_navigation_ice/tests",
     {"note": "47 passed"}),
    ("21", "test_file", "referenced_external_artifact",
     "backend/tests/test_green_shipping.py", "backend/tests/test_green_shipping.py", {}),
    ("22", "test_file", "referenced_external_artifact",
     "backend/tests/test_green_efficiency_m1895.py", "backend/tests/test_green_efficiency_m1895.py",
     {"note": "与 test_green_shipping.py 合计 37 passed"}),
    ("23", "test_file", "referenced_external_artifact",
     "tests/test_cii_regime_m1829.py", "tests/test_cii_regime_m1829.py",
     {"note": "70 passed"}),
    ("30", "symbol_reference", "referenced_external_artifact",
     "mepc.z_factor", "mepc.z_factor",
     {"note": "C1 根因：Z_FACTORS.get(year, 11.0) 一次性兜底"}),
    ("31", "symbol_reference", "referenced_external_artifact",
     "Z_FACTORS.get(year, 11.0)", "Z_FACTORS.get(year, 11.0)", {}),
    ("32", "symbol_reference", "referenced_external_artifact",
     "Z_FACTORS = 100·A.CII_Z_FACTOR", "Z_FACTORS = 100·A.CII_Z_FACTOR",
     {"note": "修复：Z 表由 A 派生（单源化）"}),
    ("33", "symbol_reference", "referenced_external_artifact",
     "z_regime() / z_extrapolated() / required_cii_meta()",
     "z_regime() / z_extrapolated() / required_cii_meta()",
     {"note": "mepc.py 新增函数"}),
    ("34", "symbol_reference", "referenced_external_artifact",
     "z_factor()", "z_factor()",
     {"note": "对 <2023 返回 0.0（参考线口径）"}),
    ("35", "symbol_reference", "referenced_external_artifact",
     "_gn_required_cii()", "_gn_required_cii()",
     {"note": "green_shipping.py：委派 A 的 required_cii()"}),
    ("36", "symbol_reference", "referenced_external_artifact",
     "required_cii()", "required_cii()",
     {"note": "A 的权威入口"}),
    ("37", "key_reference", "referenced_external_artifact",
     "regime / z_extrapolated / required_value_is_reference / regime_note",
     "regime / z_extrapolated / required_value_is_reference / regime_note",
     {"note": "green_shipping 返回体新增键"}),
    ("38", "key_reference", "referenced_external_artifact",
     "z_factor", "z_factor` 仍为分数",
     {"note": "保留原键（分数口径）"}),
    ("39", "key_reference", "referenced_external_artifact",
     "dd_vector_basis", "dd_vector_basis",
     {"note": "compliance / model_audit 回显"}),
    ("40", "symbol_reference", "referenced_external_artifact",
     "dd_vector", "dd_vector` 只有一档通用值",
     {"note": "通用单档 (0.86, 0.94, 1.06, 1.18)；未做船型×容量档转录"}),
    ("41", "symbol_reference", "referenced_external_artifact",
     "DD_VECTOR_BASIS", "DD_VECTOR_BASIS",
     {"note": "与 /reference、model_audit 均显式回显该局限"}),
    ("42", "symbol_reference", "referenced_external_artifact",
     "mepc.required_cii(ref, 2019)", "mepc.required_cii(ref, 2019)",
     {"note": "行为变更：3.7662 → 4.2317"}),
    ("43", "key_reference", "referenced_external_artifact",
     "z_extrapolated=True", "z_extrapolated=True",
     {"note": "2027+ 外推值必须带标记"}),
    ("44", "key_reference", "referenced_external_artifact",
     "divergent_years", "divergent_years",
     {"note": "对账结论键：12/12 → 0/12"}),
    ("45", "formula", "referenced_external_artifact",
     "a·Cap^(−c)", "a·Cap^(−c)",
     {"note": "2019 参考线公式（基准 4.2317）"}),
    ("46", "key_reference", "referenced_external_artifact",
     "z/required_value/regime", "z/required_value/regime",
     {"note": "建议总账条目的逐点比对量"}),
    ("47", "key_reference", "referenced_external_artifact",
     "divergent_years == 0", "divergent_years == 0",
     {"note": "建议总账条目验收判据"}),
    ("48", "data_value", "referenced_external_artifact",
     "(0.86, 0.94, 1.06, 1.18)", "(0.86, 0.94, 1.06, 1.18)",
     {"note": "dd_vector 通用单档值"}),
    ("50", "standard_document", "referenced_external_artifact",
     "MEPC.353(78)", "MEPC.353(78)",
     {"note": "参考线"}),
    ("51", "standard_document", "referenced_external_artifact",
     "MEPC.338(76)", "MEPC.338(76)",
     {"note": "年度折减率 Z"}),
    ("52", "standard_document", "referenced_external_artifact",
     "MEPC.354(78)", "MEPC.354(78)",
     {"note": "评级"}),
    ("53", "standard_document", "referenced_external_artifact",
     "MEPC.354(78) G4", "MEPC.354(78) G4",
     {"note": "船型×容量档 dd 向量（未转录）"}),
    ("60", "ledger_slug", "referenced_external_artifact",
     "KPI-QC-RECHECK", "KPI-QC-RECHECK",
     {"note": "锚点：已合并功能独立复核的子项"}),
    ("61", "ledger_slug", "referenced_external_artifact",
     "DEF-CII-SINGLE-SOURCE", "DEF-CII-SINGLE-SOURCE",
     {"note": "建议新总账条目（域：绿色航行 ship-performance-platform）"}),
    ("70", "api_endpoint", "referenced_external_artifact",
     "compliance", "compliance",
     {"note": "ice 模块端点，回显 regime 标记"}),
    ("71", "api_endpoint", "referenced_external_artifact",
     "model_audit", "model_audit",
     {"note": "ice 模块端点，回显 regime 标记"}),
    ("72", "api_endpoint", "referenced_external_artifact",
     "/reference", "/reference",
     {"note": "显式回显 DD_VECTOR_BASIS 局限"}),
]

UNRESOLVED_FILE_REASON = (
    "no byte copy attached to the report record; platform store endpoints probed "
    "(see probe_evidence); local /root/ship-performance-platform checkout is not a git "
    "work tree and the path is absent there — registration stops at the reference level, "
    "ownership stays with the producing repo (ship-performance-platform)"
)
UNRESOLVED_SYMBOL_REASON = (
    "symbol/key-level reference named in the report text; no byte copy exists in the "
    "report record or the platform store — resolvable only inside the producing repo"
)
UNRESOLVED_STANDARD_REASON = (
    "external IMO/MEPC instrument; offline environment, rule text not re-read "
    "(report itself marks the coefficient layer WITHHELD)"
)
UNRESOLVED_SLUG_REASON = (
    "ledger slug in the platform knowledge ledger; not part of the report record"
)
UNRESOLVED_ENDPOINT_REASON = (
    "API surface of the producing repo; not a stored artifact of this report"
)


def load_probes() -> list:
    pf = SRC_DIR / "probes.json"
    return json.loads(pf.read_text()) if pf.exists() else []


def fetch_record() -> dict:
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps(
            {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    tok = json.load(urllib.request.urlopen(req))["access_token"]
    req2 = urllib.request.Request(
        BASE + f"/tensor/reports/{REPORT_ID}", headers={"Authorization": "Bearer " + tok}
    )
    d = json.load(urllib.request.urlopen(req2))
    if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict):
        d = d["data"]
    return d


def md_locator(md: str, needle: str, note: str | None = None) -> dict:
    i = md.find(needle)
    if i < 0:
        raise SystemExit(f"needle not found verbatim in markdown: {needle!r} — refusing to invent")
    loc = {
        "source_uri": SOURCE_URI,
        "source_field": SOURCE_FIELD,
        "char_start": i,
        "char_end": i + len(needle),
        "quote": needle,
    }
    if note:
        loc["note"] = note
    return loc


def record_locator(field: str, value) -> dict:
    return {
        "source_uri": SOURCE_URI,
        "source_field": "record",
        "field": field,
        "value": value,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    if args.offline:
        d = json.loads((SRC_DIR / "report_13272_record.json").read_text())
        md = (SRC_DIR / "report_13272.md").read_text()
    else:
        d = fetch_record()
        md = d["markdown"]
        SRC_DIR.mkdir(parents=True, exist_ok=True)
        (SRC_DIR / "report_13272_record.json").write_text(json.dumps(d, ensure_ascii=False, indent=1))
        (SRC_DIR / "report_13272.md").write_text(md)

    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    h1 = md.splitlines()[0]
    if digest != CONTRACT_SOURCE_HASH:
        raise SystemExit(f"hash mismatch: {digest} != {CONTRACT_SOURCE_HASH}")
    if len(md) != CONTRACT_CHARS:
        raise SystemExit(f"chars mismatch: {len(md)} != {CONTRACT_CHARS}")

    # ---- asset 01: source document -------------------------------------------
    assets = [
        {
            "asset_id": "ast-13272-01",
            "kind": "source_document",
            "role": "primary_source",
            "name": "report_13272_markdown",
            "locators": [md_locator(md, h1, "H1 line; whole-document span recorded in content_ref")],
            "content_ref": {
                "source_uri": SOURCE_URI,
                "source_field": SOURCE_FIELD,
                "chars": len(md),
                "byte_length_utf8": len(md.encode("utf-8")),
                "sha256": digest,
            },
            "resolvable": True,
            "resolution": "fetched_via_tensor_api",
            "status": "resolved",
        },
        # ---- asset 02: record metadata ---------------------------------------
        {
            "asset_id": "ast-13272-02",
            "kind": "record_metadata",
            "role": "identification",
            "name": "report_13272_record",
            "locators": [
                record_locator("id", d["id"]),
                record_locator("title", d["title"]),
                record_locator("scenario_key", d["scenario_key"]),
                record_locator("mission_id", d["mission_id"]),
                record_locator("status", d["status"]),
                record_locator("created_at", d["created_at"]),
                record_locator("tags", d["tags"]),
                record_locator("summary", d["summary"]),
            ],
            "resolvable": True,
            "resolution": "fetched_via_tensor_api",
            "status": "resolved",
        },
    ]

    # ---- asset 03: declared figure (record) ----------------------------------
    fig_asset = {
        "asset_id": "ast-13272-03",
        "kind": "figure",
        "role": "declared_figure",
        "name": d["figures"][0]["name"],
        "locators": [
            record_locator("figures[0].name", d["figures"][0]["name"]),
            record_locator("figures[0].caption", d["figures"][0]["caption"]),
            md_locator(md, "artifacts/m13764_cii_consistency.png",
                         "same figure named in section ④ with repo-relative path"),
        ],
    }
    fig_probe = next(
        (p for p in load_probes()
         if p.get("endpoint") == f"/tensor/reports/{REPORT_ID}/figures/{d['figures'][0]['name']}"),
        None,
    )
    if fig_probe and fig_probe.get("ok") and fig_probe.get("png_magic_ok"):
        fig_asset.update(
            {
                "resolvable": True,
                "resolution": "fetched_via_tensor_api_store",
                "status": "resolved",
                "content_ref": {
                    "endpoint": fig_probe["endpoint"],
                    "content_type": fig_probe.get("content_type"),
                    "bytes": fig_probe.get("bytes"),
                    "sha256": fig_probe.get("sha256"),
                },
            }
        )
    else:
        fig_asset.update(
            {
                "resolvable": False,
                "resolution": "record_declares_name_and_caption_only_no_png_base64",
                "status": "unresolved",
                "unresolved_reason": (
                    "record carries name+caption only (no png_base64); platform store "
                    "endpoints probed, see probe_evidence"
                ),
            }
        )
    assets.append(fig_asset)

    # ---- referenced artifacts / symbols / standards ---------------------------
    for suffix, kind, role, name, needle, extra in REFERENCE_TABLE:
        reason_map = {
            "standard_document": UNRESOLVED_STANDARD_REASON,
            "ledger_slug": UNRESOLVED_SLUG_REASON,
            "api_endpoint": UNRESOLVED_ENDPOINT_REASON,
        }
        loc = md_locator(md, needle, extra.get("note"))
        assets.append(
            {
                "asset_id": f"ast-13272-{suffix}",
                "kind": kind,
                "role": role,
                "name": name,
                "locators": [loc],
                "resolvable": False,
                "resolution": "reference_only_no_byte_copy",
                "status": "unresolved",
                "unresolved_reason": reason_map.get(kind, UNRESOLVED_SYMBOL_REASON
                                                                      if kind in ("symbol_reference", "key_reference", "formula")
                                                                      else UNRESOLVED_FILE_REASON),
            }
        )

    # ---- manifest -------------------------------------------------------------
    n_resolved = sum(1 for a in assets if a["status"] == "resolved")
    n_unresolved = len(assets) - n_resolved
    n_locators = sum(len(a["locators"]) for a in assets)
    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "scope": {
            "report_id": REPORT_ID,
            "reports_touched": [REPORT_ID],
            "registers_assets_only": True,
            "extracts_claims": False,
            "classifies_report_type": False,
            "writes_outside_worktree": False,
        },
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "title": d["title"],
            "markdown_h1": h1,
            "title_matches_contract": d["title"] == CONTRACT_TITLE,
            "title_equals_markdown_h1": d["title"] == h1,
            "title_equals_markdown_h1_stripped": d["title"] == h1.lstrip("# ").strip(),
            "scenario_key": d["scenario_key"],
            "chars": len(md),
            "byte_length_utf8": len(md.encode("utf-8")),
            "sha256": digest,
            "hash_check": {
                "expected": CONTRACT_SOURCE_HASH,
                "recomputed": digest,
                "match": digest == CONTRACT_SOURCE_HASH,
            },
            "chars_check": {
                "expected": CONTRACT_CHARS,
                "observed": len(md),
                "match": len(md) == CONTRACT_CHARS,
            },
        },
        "assets": assets,
        "counts": {
            "assets": len(assets),
            "locators": n_locators,
            "resolved": n_resolved,
            "unresolved": n_unresolved,
        },
        "invariants": {
            "asset_ids_unique": len({a["asset_id"] for a in assets}) == len(assets),
            "all_quotes_are_verbatim_substrings": all(
                loc["quote"] in md
                for a in assets
                for loc in a["locators"]
                if loc.get("source_field") == SOURCE_FIELD
            ),
            "no_verified_marks": not any(
                "verified" in json.dumps(a, ensure_ascii=False).lower()
                for a in assets
            ),
            "single_report_touched": True,
        },
        "probe_evidence": json.loads((SRC_DIR / "probes.json").read_text())
        if (SRC_DIR / "probes.json").exists()
        else [],
        "observations": [
            "record.mission_id=13764 while the work-package contract says mission_id: null — "
            "recorded as observed, not adjudicated by this package",
            "record.title == contract title, and the markdown H1 equals the title once the "
            "'# ' marker is stripped (title_equals_markdown_h1 is False only because of the marker)",
            "local /root/ship-performance-platform checkout is not a git work tree and the 12 "
            "exact repo paths checked there are all absent — bounded observation only; "
            "resolvable=false rests on 'no byte copy in the report record + platform store "
            "endpoints 404'",
            "the declared figure IS byte-reachable through the platform store "
            "(GET /tensor/reports/13272/figures/m13764_cii_consistency.png → 200, image/png, "
            "79031 bytes, sha256:2b908afb7afc5b700b6a19d6e22dc765fb7227ecc45c61705cbd2465f2a6c71c); "
            "the other three probed endpoints returned 404",
            "claims=[] is by design: contract notes allow an empty claims array and "
            "no_forced_claim_generation forbids inventing knowledge objects at this stage",
            "this package registers references; it does NOT verify any number in the report "
            "(correctness of the report's figures is the job of stages 03/04 and independent review)",
        ],
        "claims_policy": {
            "claims": [],
            "reason": (
                "contract objective is register_assets only; notes state 'claims 允许为空数组'; "
                "constraints forbid forced claim generation and marking claims verified — "
                "verification is computed by the platform gate"
            ),
        },
    }

    # ---- result envelope -------------------------------------------------------
    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": digest,
            "source_field": SOURCE_FIELD,
            "producer": "agent/m15756",
            "emitted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "notes": (
                "source_hash recomputed from the report-13272 markdown bytes fetched over the "
                "TensorPlatform API; equals the contract-declared hash "
                "sha256:75ed781cefac9fee890f493c256dec8aea2e70795eca9d7a8bbfef1af1bcce90"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "asset_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (OUT_DIR / "kf_result.json").write_text(json.dumps(envelope, ensure_ascii=False, indent=2))
    print(f"assets={len(assets)} locators={n_locators} resolved={n_resolved} unresolved={n_unresolved}")
    print(f"wrote {OUT_DIR / 'asset_manifest.json'} and {OUT_DIR / 'kf_result.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
