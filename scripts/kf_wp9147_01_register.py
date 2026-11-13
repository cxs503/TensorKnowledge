"""wp-9147-01 | task_type=01-asset-registration for report_id=9147 (read-only, single report).

What this script does (registration only, no extraction):
  * reads the byte-exact markdown fetched by scripts/kf_wp9147_01_fetch.py
  * re-derives every asset locator from a *programmatic anchor* (line search) and slices the
    emitted ``quote`` out of the markdown at run time -> zero hand transcription
  * asserts each quote is a unique substring of the markdown (quote_uniqueness integrity item)
  * classifies each asset's resolution: resolved_in_source / referenced_unresolved / declared_absent
  * emits asset_manifest.json + locator_check.json + source.md + sha256.txt under docs/kf/wp-9147-01/
    (durable: this repo's push gate drops artifacts/** and runs/**, so committed deliverables live
    under docs/, byte-identical to the run copies)

No claim is extracted and no claim is marked verified: objective.classify_report_type=false and the
contract explicitly allows ``claims: []``. Hash equality is a mechanical identity check; the
verification gate belongs to the platform.

Scope guard: only report_id=9147 is touched. No other report is read or written.

Usage: python3 scripts/kf_wp9147_01_register.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

REPORT_ID = "9147"
PACKAGE_ID = "wp-9147-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/9147"
EXPECTED_HASH = "754d613193b8da4880f56371095812b6865d4d376bdca5edb8ab4f4ceb6d0ff6"
CONTRACT_TITLE = "P77-N03: EEXI/CII Green Compliance Machine Judgment Gate Maturation"
CONTRACT_SCENARIO = "P77-N03"

RUN_DIR = pathlib.Path("runs/wp-9147-01")
OUT_DIR = pathlib.Path("docs/kf/wp-9147-01")

# Asset table: anchor substring (must be unique in markdown) -> line window relative to the anchor
# line. The quote is the verbatim slice of those lines, never typed by hand.
#   resolution: resolved_in_source      = the asset body is inside the markdown
#               referenced_unresolved   = only a path/label is in the markdown; payload is not
#                                         part of the report record (lives in the producing repo)
#               declared_absent         = report declares the slot but the record carries no payload
ASSETS = [
    dict(asset_id="A01", asset_class="document", label="报告 markdown 全文（源资产本体）",
         section="(document)", anchor=None, start=None, n_lines=None,
         resolution="resolved_in_source",
         note="整篇 markdown 即源资产；sha256 见 source.hash，字节数见 source.bytes_utf8"),
    dict(asset_id="A02", asset_class="heading", label="章节锚：Implementation Summary",
         section="L1", anchor="## Implementation Summary", start=0, n_lines=1,
         resolution="resolved_in_source", note="一级章节标题行；正文结构起点"),
    dict(asset_id="A03", asset_class="method_list", label="实施步骤清单（MEPC 条款映射 6 条）",
         section="L3-L9 (### What was done)", anchor="### What was done", start=1, n_lines=6,
         resolution="resolved_in_source",
         note="6 条方法陈述，逐条带 IMO 决议号（MEPC.335(76)/328(76)/353(78)/354(78)）；仅登记位置，不做抽取"),
    dict(asset_id="A04", asset_class="table", label="验收判据结果表（6 条判据 a-f）",
         section="L11-L19 (### Acceptance Criteria Results)", anchor="| Criterion | Result |",
         start=0, n_lines=8, resolution="resolved_in_source",
         note="表头+分隔行+6 行判据；数值仅登记不换算、不复核（复核不属本工序）"),
    dict(asset_id="A05", asset_class="numeric_anchor_list", label="关键数值清单（KVLCC2 EEXI/CII 5 项）",
         section="L21-L26 (### Key Numbers)", anchor="### Key Numbers", start=1, n_lines=5,
         resolution="resolved_in_source",
         note="5 个数值锚点（Attained/Required EEXI、ratio、CII 等级、dd 边界）；本工序只登记，不判定真伪"),
    dict(asset_id="A06", asset_class="evidence_grade_list", label="证据分级清单（3 条）",
         section="L28-L31 (### Evidence Grades)", anchor="### Evidence Grades", start=1, n_lines=3,
         resolution="resolved_in_source",
         note="报告自陈的证据等级：REAL×2 + WITHHELD×1（Required 系数未离线复核）；平台未复核，保持原样"),
    dict(asset_id="A07", asset_class="code_path", label="backend/services/green_compliance.py（~500 行）",
         section="L33-L38 (### Files)", anchor="- backend/services/green_compliance.py", start=0,
         n_lines=1, resolution="referenced_unresolved",
         note="仅路径文本在 markdown 内；代码不在报告记录内，本工序不读取生产仓，登记为未解析"),
    dict(asset_id="A08", asset_class="test_path", label="backend/tests/test_green_compliance_m7776.py（47 tests）",
         section="L33-L38 (### Files)", anchor="- backend/tests/test_green_compliance_m7776.py",
         start=0, n_lines=1, resolution="referenced_unresolved",
         note="仅路径文本在 markdown 内；用例数 47 为报告自陈，未在本工序复跑"),
    dict(asset_id="A09", asset_class="artifact_json", label="artifacts/m7776/compliance_report.json",
         section="L33-L38 (### Files)", anchor="- artifacts/m7776/compliance_report.json", start=0,
         n_lines=1, resolution="referenced_unresolved",
         note="年度报告工件路径；payload 未挂在报告记录上，未解析"),
    dict(asset_id="A10", asset_class="artifact_figure", label="artifacts/m7776/fig_eexi_cii_analysis.png",
         section="L33-L38 (### Files)", anchor="- artifacts/m7776/fig_eexi_cii_analysis.png", start=0,
         n_lines=1, resolution="referenced_unresolved",
         note="图件路径文本在 markdown 内，但平台记录 figures=[]，PNG 本体不可从本报告解析"),
    dict(asset_id="A11", asset_class="doc_path", label="docs/m7776/P77_N03_green_compliance.md",
         section="L33-L38 (### Files)", anchor="- docs/m7776/P77_N03_green_compliance.md", start=0,
         n_lines=1, resolution="referenced_unresolved",
         note="说明文档路径文本；文档本体不在报告记录内，未解析"),
    dict(asset_id="A12", asset_class="figure_attachment_slot", label="记录级图件附件槽（record.figures）",
         section="L33-L38 (### Files)", anchor="### Files", start=0, n_lines=1,
         resolution="declared_absent",
         note="报告在 Files 节声明 1 张 PNG，但 GET /api/v1/tensor/reports/9147 的 figures 为空数组："
              "记录级附件槽为空（absence 是登记事实，不是失败）"),
]


def _find_unique_line(lines: list[str], anchor: str) -> int:
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit(f"anchor not unique ({len(hits)} hits): {anchor!r}")
    return hits[0]


def build_asset(spec: dict, md: str, lines: list[str]) -> dict:
    if spec["anchor"] is None:  # whole document
        quote = md
        start_line, end_line = 0, len(lines) - 1
        method = "document"
    else:
        base = _find_unique_line(lines, spec["anchor"])
        start_line = base + spec["start"]
        end_line = start_line + spec["n_lines"] - 1
        if start_line < 0 or end_line >= len(lines):
            raise SystemExit(f"line window out of range for {spec['asset_id']}")
        quote = "\n".join(lines[start_line:end_line + 1])
        if not quote.strip():
            raise SystemExit(f"empty quote for {spec['asset_id']}")
        method = "char_span"
    # offsets are measured on the real string, not computed cumulatively
    pos = md.find(quote)
    if pos < 0:
        raise SystemExit(f"quote not a substring of markdown: {spec['asset_id']}")
    unique = md.count(quote) == 1
    if not unique:
        raise SystemExit(f"quote not unique in markdown: {spec['asset_id']}")
    present_in_window = md[pos:pos + len(quote)] == quote
    if not present_in_window:
        raise SystemExit(f"offset check failed: {spec['asset_id']}")
    return {
        "asset_id": spec["asset_id"],
        "asset_class": spec["asset_class"],
        "label": spec["label"],
        "in_report_section": spec["section"],
        "locator": {
            "method": method,
            "start_char": pos,
            "end_char": pos + len(quote),
            "start_line": start_line,
            "end_line": end_line,
            "quote": quote,
            "unique": unique,
        },
        "resolution": spec["resolution"],
        "resolution_check": {
            "check": (
                "quote found verbatim in markdown at declared [start_char,end_char) and unique"
                if spec["resolution"] == "resolved_in_source"
                else ("path text found verbatim in markdown; payload not carried by the report record"
                      if spec["resolution"] == "referenced_unresolved"
                      else "GET /api/v1/tensor/reports/9147 -> figures == [] (no attachment payload)")
            ),
            "result": ("resolved" if spec["resolution"] == "resolved_in_source"
                       else "unresolved" if spec["resolution"] == "referenced_unresolved" else "absent"),
        },
        "note": spec["note"],
    }


def main() -> None:
    md_bytes = (RUN_DIR / "report_9147.md").read_bytes()
    md = md_bytes.decode("utf-8")
    rec = json.loads((RUN_DIR / "report_9147.json").read_text())
    meta = json.loads((RUN_DIR / "report_9147.meta.json").read_text())
    digest = hashlib.sha256(md_bytes).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit(f"SOURCE HASH MISMATCH: {digest} != {EXPECTED_HASH}")
    lines = md.splitlines()

    assets = [build_asset(spec, md, lines) for spec in ASSETS]
    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate asset_id")

    by_class: dict[str, int] = {}
    by_resolution: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_resolution[a["resolution"]] = by_resolution.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "hash_scope": "sha256 over the UTF-8 bytes of the markdown field",
            "hash_matches_contract": digest == EXPECTED_HASH,
            "chars": len(md),
            "bytes_utf8": len(md_bytes),
            "title": rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "title_matches_contract": rec.get("title") == CONTRACT_TITLE,
            "scenario_matches_contract": rec.get("scenario_key") == CONTRACT_SCENARIO,
            "source_record_mission_id": rec.get("mission_id"),
            "source_record_status": rec.get("status"),
            "source_record_created_at": rec.get("created_at"),
            "line_count": len(lines),
            "platform_figures": rec.get("figures") or [],
            "platform_tags": rec.get("tags") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_resolution,
            "resolved_in_source": by_resolution.get("resolved_in_source", 0),
            "referenced_unresolved": by_resolution.get("referenced_unresolved", 0),
            "declared_absent": by_resolution.get("declared_absent", 0),
        },
        "assets": assets,
        "claims": [],
        "claims_note": (
            "claims 故意为空数组：契约 objective.register_assets=true / classify_report_type=false，"
            "notes 明示 claims 允许为空；本工序只做资产登记与定位，不做抽取，不造 claim，"
            "也不把任何结论标为 verified。"
        ),
        "integrity": {
            "quote_uniqueness": "all quotes asserted unique substrings at registration time "
                                "(scripts/kf_wp9147_01_register.py, build_asset) and re-checked by "
                                "scripts/kf_wp9147_01_check.py",
            "hash_recomputed_locally": digest == EXPECTED_HASH,
            "hash_matches_contract": digest == EXPECTED_HASH,
        },
    }

    locator_check = {
        "report_id": REPORT_ID,
        "source_hash": f"sha256:{digest}",
        "source_hash_expected": f"sha256:{EXPECTED_HASH}",
        "source_hash_matches": digest == EXPECTED_HASH,
        "checks": [
            {
                "asset_id": a["asset_id"],
                "method": a["locator"]["method"],
                "start_char": a["locator"]["start_char"],
                "end_char": a["locator"]["end_char"],
                "start_line": a["locator"]["start_line"],
                "end_line": a["locator"]["end_line"],
                "quote_len": len(a["locator"]["quote"]),
                "slice_matches": md[a["locator"]["start_char"]:a["locator"]["end_char"]]
                                  == a["locator"]["quote"],
                "occurrences": md.count(a["locator"]["quote"]),
                "resolution": a["resolution"],
            }
            for a in assets
        ],
    }
    locator_check["all_slice_matches"] = all(c["slice_matches"] for c in locator_check["checks"])
    locator_check["all_unique"] = all(c["occurrences"] == 1 for c in locator_check["checks"])

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "locator_check.json").write_text(
        json.dumps(locator_check, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (OUT_DIR / "source.md").write_bytes(md_bytes)
    (OUT_DIR / "sha256.txt").write_text(f"sha256:{digest}\n", encoding="utf-8")

    print(f"report {REPORT_ID}: chars={len(md)} bytes={len(md_bytes)} lines={len(lines)}")
    print(f"sha256={digest} match={digest == EXPECTED_HASH}")
    print(f"assets={len(assets)} by_resolution={by_resolution}")
    print(f"locators: slice_matches={locator_check['all_slice_matches']} "
          f"unique={locator_check['all_unique']}")
    print(f"wrote {OUT_DIR}/asset_manifest.json")


if __name__ == "__main__":
    sys.exit(main())