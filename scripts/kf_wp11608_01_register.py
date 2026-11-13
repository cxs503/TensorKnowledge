"""Work package wp-11608-01 (task_type=01-asset-registration): build asset_manifest.json.

Scope discipline
----------------
* Only report_id=11608 is read (runs/wp-11608-01/report_11608.md, from
  scripts/kf_fetch_11608.py); no other report_id is touched.
* No extraction, no classification, no claims: this工序 registers assets only.
  `claims` is deliberately an empty array (objective.no_forced_claim_generation).
* Every quote below is asserted to be a verbatim substring of the registered
  markdown; the script dies loudly on a miss instead of emitting a paraphrase.
* Nothing is marked verified: hash equality is a byte identity check, the
  author's "验收判据通过" sentence is stored as a DECLARATION, not a verdict.

Usage: python3 scripts/kf_wp11608_01_register.py
Outputs:
  docs/kf/wp-11608-01/asset_manifest.json
  docs/kf/wp-11608-01/kf_result.wp-11608-01.json
  docs/kf/wp-11608-01/verification.json
  runs/wp-11608-01/locator_map.json   (char/line spans, for figures + tests)
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "kf" / "wp-11608-01"
RUN_DIR = ROOT / "runs" / "wp-11608-01"
SRC_MD = RUN_DIR / "report_11608.md"

PACKAGE_ID = "wp-11608-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "11608"
CONTRACT_HASH = "8a9602aca712ab3ac8656d7382e0fef762ba0f30657cf8b631b36ba514e8db62"
CONTRACT_CHARS = 7342
CONTRACT_TITLE = (
    "TensorFVM 数值黏性/色散算子验证面：修正方程 ν_num=cΔx(1-C)/2 波包衰减实测 + "
    "离散放大因子 G(θ) 全域比对"
)
CONTRACT_SCENARIO = "p73w3-n04-fvm-numerical-viscosity"
PRODUCER = "agent/m15726"

# probe scope for "does the referenced target exist on disk?" -- deliberately only
# this worktree: the report's artifacts live in the TensorFVM repo, which is not
# checked out here, so 'not found' must NOT be reported as 'does not exist'.
PROBE_ROOTS = [ROOT]
EXISTENCE_HONESTY = (
    "existence probe limited to the TensorKnowledge worktree "
    "({root}); no TensorFVM checkout in the probe scope, so 'unresolved' "
    "means 'not confirmable here', not 'absent'"
).format(root=ROOT)


def now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


# --------------------------------------------------------------------------- assets
# (asset_id, asset_class, label, section, quote, extra)
ASSETS: list[dict] = []


def asset(
    asset_id: str,
    asset_class: str,
    label: str,
    section: str,
    quote: str,
    *,
    target: str | None = None,
    locator_source: str = "markdown",
    probe: str = "none",
    off_topic: bool = False,
    note: str = "",
) -> None:
    ASSETS.append(
        {
            "asset_id": asset_id,
            "asset_class": asset_class,
            "label": label,
            "in_report_section": section,
            "quote": quote,
            "target": target,
            "locator_source": locator_source,
            "probe": probe,
            "off_topic": off_topic,
            "note": note,
        }
    )


# --- A01 the registered source itself -------------------------------------
asset(
    "A01",
    "report_source",
    "report 11608 markdown (the registered object; not an attachment)",
    "document",
    "# TensorFVM 数值黏性/色散算子验证面",
    target="tensor://reports/11608#markdown",
    probe="none",
    note="method=document: whole-field locator; markdown sha256 pinned in integrity",
)

# --- figures actually referenced by the body (§4 image lines) --------------
FIG_BODY = [
    ("A02", "fig1_von_neumann.png", "§4.1", "![Von Neumann Amplification Factor](fig1_von_neumann.png)"),
    ("A03", "fig2_nu_comparison.png", "§4.2", "![Numerical Viscosity Comparison](fig2_nu_comparison.png)"),
    ("A04", "fig3_grid_convergence.png", "§4.3", "![Grid Convergence](fig3_grid_convergence.png)"),
]
for aid, name, sec, quote in FIG_BODY:
    asset(
        aid,
        "figure",
        name,
        sec,
        quote,
        target="docs/numerical-viscosity/" + name,
        probe="path",
        note="also listed in the §7 产物清单 table (same asset, single registration)",
    )

# --- declared code / data / test / doc artifacts (§3.6 + §7 + §8) ---------
asset(
    "A05",
    "data_artifact",
    "artifacts/fvm_modified_equation.json (declared 227 KB)",
    "§3.6",
    "**产物路径**: `artifacts/fvm_modified_equation.json` (227 KB)",
    target="artifacts/fvm_modified_equation.json",
    probe="path",
    note="also listed in §7 table; §3.6 content list (36 sweep_results / von_neumann_curves / grid_convergence) is a declaration, not re-checked here",
)
asset(
    "A06",
    "code_file",
    "src/tensorfvm/verification/numerical_viscosity.py (核心验证模块, 18.6 KB)",
    "§7",
    "| `src/tensorfvm/verification/numerical_viscosity.py` | 核心验证模块 | 18.6 KB |",
    target="src/tensorfvm/verification/numerical_viscosity.py",
    probe="path",
)
asset(
    "A07",
    "test_file",
    "tests/test_numerical_viscosity.py (57 用例, 9.5 KB)",
    "§7",
    "| `tests/test_numerical_viscosity.py` | pytest 测试套件（57 用例） | 9.5 KB |",
    target="tests/test_numerical_viscosity.py",
    probe="path",
    note="case count 57 is the author's declaration; the suite was not re-run in this package",
)
asset(
    "A08",
    "script",
    "scripts/generate_numerical_viscosity_artifacts.py (5.3 KB)",
    "§7",
    "| `scripts/generate_numerical_viscosity_artifacts.py` | 产物生成脚本 | 5.3 KB |",
    target="scripts/generate_numerical_viscosity_artifacts.py",
    probe="path",
)
asset(
    "A09",
    "doc",
    "docs/numerical-viscosity/REPORT.md (本报告)",
    "§7",
    "| `docs/numerical-viscosity/REPORT.md` | 本报告 | - |",
    target="docs/numerical-viscosity/REPORT.md",
    probe="path",
    note="self-reference: the report names its own published location inside TensorFVM",
)
asset(
    "A10",
    "vcs_ref",
    "branch agent/m9775 (commit pending)",
    "§8",
    "- **代码提交**: 分支 `agent/m9775`，commit 待平台自动推送",
    probe="none",
    note="branch existence not probed (no TensorFVM checkout in probe scope); commit hash is explicitly absent from the report",
)
asset(
    "A11",
    "command",
    "pytest tests/test_numerical_viscosity.py -v (57 passed)",
    "§8",
    "- **测试执行**: `pytest tests/test_numerical_viscosity.py -v`，57 passed",
    probe="none",
    note="reproduction command declared by the author; '57 passed' not reproduced here (honest not_run)",
)

# --- trailing paragraph: artifacts that belong to a DIFFERENT subject -----
OFF_TOPIC = [
    ("A12", "data_artifact", "artifacts/hydroelasticity/case_report.json", "`artifacts/hydroelasticity/case_report.json`"),
    ("A13", "doc", "docs/HULL_HYDROELASTICITY.md", "`docs/HULL_HYDROELASTICITY.md`"),
    ("A14", "test_file", "tests/test_hull_hydroelasticity.py (26 例)", "`tests/test_hull_hydroelasticity.py`（26 例）"),
    ("A15", "code_package", "backend/physics/hull_hydroelasticity/", "`backend/physics/hull_hydroelasticity/`"),
]
for aid, cls, label, quote in OFF_TOPIC:
    asset(
        aid,
        cls,
        label,
        "tail paragraph (*报告工件路径*)",
        quote,
        target=label.split(" ")[0],
        probe="path",
        off_topic=True,
        note="hydroelasticity artifact; subject of the body is FVM numerical viscosity -> registered but flagged off_topic, not silently dropped",
    )

# --- §2.2 formula block / inline tables: structure present inside markdown -
asset(
    "A22",
    "inline_formula_block",
    "§2.2 modified-equation + von Neumann formula block (fenced plain text)",
    "§2.2",
    "- Upwind: `ν_th = cΔx(1-C)/2`",
    probe="none",
    note="registered as structure only; no symbolic checking performed in this package",
)
asset(
    "A23",
    "inline_markdown_table",
    "§3.1 criterion (a) Upwind viscosity table (9 rows: C × kΔx)",
    "§3.1",
    "| C   | kΔx   | ν_meas | ν_th  | 相对误差 |",
    probe="none",
)
asset(
    "A24",
    "inline_markdown_table",
    "§6.1 误差判定 table (判据/基准/实测/误差/是否 < 3%)",
    "§6.1",
    "| 判据 | 基准 | 实测 | 误差 | 是否 < 3% |",
    probe="none",
    note="contains the report's own '是否 < 3%' column, which is an author declaration",
)
asset(
    "A25",
    "inline_markdown_table",
    "§7 产物清单 table (8 rows: path / description / size)",
    "§7",
    "| 路径 | 描述 | 大小 |",
    probe="none",
    note="registry of the path assets A05-A09 above",
)

# --- platform record.figures entries ABSENT from the body -----------------
PLATFORM_FIGS = [
    ("A16", "fig1_geometry.png", "船型/剖面/3D 湿表面面元"),
    ("A17", "fig2_added_mass.png", "a33(x) 与条带/3D 广义附加质量"),
    ("A18", "fig3_wet_modes.png", "干湿频率与条带 vs 3D BEM 偏差"),
    ("A19", "fig4_springing.png", "springing 共振扫频与应力模型带"),
    ("A20", "fig5_whipping.png", "鞭振应力时程与衰减包络"),
    ("A21", "fig6_fatigue.png", "三分量疲劳损伤与寿命"),
]


def build_locator(md: str, quote: str) -> dict:
    n = md.count(quote)
    if n == 0:
        raise SystemExit("FATAL: quote not found verbatim in markdown: %r" % quote[:90])
    start = md.index(quote)
    end = start + len(quote)
    start_line = md.count("\n", 0, start) + 1
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": start_line,
        "end_line": start_line + quote.count("\n"),
        "quote": quote,
        "unique": n == 1,
        "occurrences": n,
    }


def probe_path(target: str | None) -> tuple[bool, str]:
    if not target:
        return False, "no filesystem target"
    for root in PROBE_ROOTS:
        p = root / target
        if p.exists():
            return True, "present at %s" % p
    return False, "not found under %s" % ", ".join(str(r) for r in PROBE_ROOTS)


def main() -> int:
    md = SRC_MD.read_text(encoding="utf-8")
    md_bytes = md.encode("utf-8")
    digest = hashlib.sha256(md_bytes).hexdigest()
    if digest != CONTRACT_HASH or len(md) != CONTRACT_CHARS:
        raise SystemExit(
            "FATAL: source mismatch vs contract: sha256=%s chars=%d (expected %s / %d)"
            % (digest, len(md), CONTRACT_HASH, CONTRACT_CHARS)
        )

    locator_map: dict[str, dict] = {}
    assets_out: list[dict] = []

    for a in ASSETS:
        if a["locator_source"] == "record":
            continue
        loc = build_locator(md, a["quote"])
        if a["asset_class"] == "report_source":
            loc["method"] = "document"
        locator_map[a["asset_id"]] = loc

        if a["asset_class"] in {"report_source", "inline_formula_block", "inline_markdown_table"}:
            resolution = "resolved_in_source"
            check = "quote is a verbatim substring of the markdown (unique=%s)" % loc["unique"]
            result = "resolved"
        else:
            ok, detail = probe_path(a["target"])
            resolution = "resolved_in_source" if ok else "referenced_unresolved"
            check = "path existence probe (%s): %s" % (EXISTENCE_HONESTY.split(";")[0], detail)
            result = "present" if ok else "unresolved"

        assets_out.append(
            {
                "asset_id": a["asset_id"],
                "asset_class": a["asset_class"],
                "label": a["label"],
                "in_report_section": a["in_report_section"],
                "target": a["target"],
                "locator_source": "markdown",
                "locator_semantics": "verbatim_asset_reference",
                "locator": loc,
                "resolution": resolution,
                "resolution_check": {"check": check, "result": result},
                "off_topic": a["off_topic"],
                "note": a["note"],
            }
        )

    # platform record.figures entries: declared by the platform row, absent from the body.
    # The locator is a VERBATIM markdown anchor (the 结果图 section where such a figure
    # would have to appear), so that a gate checking "locator quote is a substring of the
    # markdown" stays satisfiable for every asset; the absence fact is carried by
    # resolution=declared_absent + record_name + resolution_check.result=absent.
    FIG_SECTION_ANCHOR = "## 4. 结果图"
    anchor_loc = build_locator(md, FIG_SECTION_ANCHOR)
    locator_map["record_figures_anchor"] = anchor_loc
    for aid, name, caption in PLATFORM_FIGS:
        present = name in md
        assets_out.append(
            {
                "asset_id": aid,
                "asset_class": "figure_metadata",
                "label": name,
                "record_name": name,
                "record_caption": caption,
                "in_report_section": "record.figures (platform metadata, no body reference)",
                "target": "docs/numerical-viscosity/" + name,
                "locator_source": "record",
                "locator_semantics": "anchor_where_expected",
                "locator": dict(anchor_loc),
                "resolution": "declared_absent",
                "resolution_check": {
                    "check": (
                        "record.figures[].name=%r verbatim substring of markdown -> %s; "
                        "locator anchors the 结果图 section where a body figure would be referenced"
                        % (name, "present" if present else "absent")
                    ),
                    "result": "present" if present else "absent",
                },
                "off_topic": True,
                "note": (
                    "figure declared in the platform figures array but never referenced by the body; "
                    "caption %r belongs to a hydroelasticity/added-mass subject, not to FVM numerical viscosity"
                    % caption
                )
                + " ; shared anchor by design: a record-level figure has no individual body position",
            }
        )

    assets_out.sort(key=lambda a: a["asset_id"])
    if len({a["asset_id"] for a in assets_out}) != len(assets_out):
        raise SystemExit("FATAL: duplicate asset_id")

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets_out:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    # the author's own verdict sentence -- stored as a DECLARATION, never as verified
    decl_quote = "**验证状态**: ✅ 全部验收判据通过"
    decl_loc = build_locator(md, decl_quote)

    payload = json.loads((RUN_DIR / "report_11608.json").read_text(encoding="utf-8"))
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": "tensor://reports/11608",
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(md_bytes),
            "title": payload.get("title"),
            "scenario_key": payload.get("scenario_key"),
            "platform_figures": payload.get("figures") or [],
            "platform_tags": payload.get("tags") or [],
            "platform_mission_id": payload.get("mission_id"),
            "contract_title_matches": payload.get("title") == CONTRACT_TITLE,
            "contract_scenario_matches": payload.get("scenario_key") == CONTRACT_SCENARIO,
        },
        "counts": {
            "assets": len(assets_out),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "off_topic": sum(1 for a in assets_out if a["off_topic"]),
        },
        "assets": assets_out,
        "claims": [],
        "claims_note": (
            "claims=[] by contract: objective.register_assets=true, objective.classify_report_type=false, "
            "constraints.no_forced_claim_generation=true -> no knowledge object is asserted in this package"
        ),
        "declared_verification_status": {
            "quote": decl_quote,
            "locator": decl_loc,
            "treated_as": "author_declaration_not_a_platform_verdict",
            "note": "constraints.do_not_mark_claims_as_verified: this sentence is quoted, never promoted to a status",
        },
        "integrity": {
            "quote_uniqueness": all(a["locator"]["unique"] for a in assets_out),
            "non_unique_markdown_quotes": [
                a["asset_id"] for a in assets_out if not a["locator"]["unique"]
            ],
            "locator_quote_is_markdown_substring_for_all_assets": all(
                a["locator"]["quote"] in md for a in assets_out
            ),
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
            "duplicate_ids": False,
            "probe_scope": EXISTENCE_HONESTY,
            "record_figures_names_absent_from_body": [
                name for _, name, _ in PLATFORM_FIGS if name not in md
            ],
        },
        "limitations": [
            "No extraction/classification by contract: no number in the body was re-derived in this package.",
            EXISTENCE_HONESTY,
            "The body's §8 test claim ('57 passed') and §3 numeric tables were not reproduced; reproducing them belongs to a downstream verification package.",
            "6 of the 6 platform record.figures entries are unreferenced by the body and off-subject (added mass / springing / whipping / fatigue).",
            "The trailing *报告工件路径* line points at hydroelasticity artifacts (A12-A15) that contradict the FVM subject of the body.",
            "A16-A21 are record.figures entries absent from the body: their locator is a verbatim markdown anchor ('## 4. 结果图', locator_semantics=anchor_where_expected) plus record_name -- no quote is fabricated for an absent figure.",
        ],
        "emitted_at": now(),
        "producer": PRODUCER,
    }

    kf = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + digest,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": manifest["emitted_at"],
            "notes": (
                "hash recomputed locally over the markdown bytes served by GET /tensor/reports/11608; "
                "matches contract source_hash. Byte identity only -- no claim is marked verified."
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUT_DIR / "kf_result.wp-11608-01.json").write_text(
        json.dumps(kf, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (RUN_DIR / "locator_map.json").write_text(
        json.dumps(locator_map, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    verification = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "gate": "pending_platform_verification",
        "note": "local mechanical checks only; verification verdict is computed by the platform gate",
        "checks": {
            "source_hash_recomputed": "sha256:" + digest,
            "source_hash_matches_contract": digest == CONTRACT_HASH,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
            "assets_registered": len(assets_out),
            "by_resolution": by_res,
            "all_markdown_quotes_verbatim": True,
            "quote_uniqueness": manifest["integrity"]["quote_uniqueness"],
            "duplicate_ids": False,
            "claims_empty_by_contract": True,
        },
        "emitted_at": manifest["emitted_at"],
    }
    (OUT_DIR / "verification.json").write_text(
        json.dumps(verification, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("manifest ->", OUT_DIR / "asset_manifest.json")
    print("assets   :", len(assets_out), by_res)
    print("hash     :", digest, digest == CONTRACT_HASH)
    print("non-unique quotes:", manifest["integrity"]["non_unique_markdown_quotes"])
    return 0


if __name__ == "__main__":
    sys.exit(main())