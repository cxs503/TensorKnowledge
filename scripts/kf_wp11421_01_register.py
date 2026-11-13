#!/usr/bin/env python3
"""wp-11421-01 | 01-asset-registration for report_id=11421 (KBM-RCI-F1-FACTORY, lane C).

Read-only on the platform. Fetches tensor://reports/11421 (field=markdown), recomputes the
sha256 of the markdown UTF-8 bytes, and registers the report's *assets* (figures, artifact
paths, code pointers, inline tables, machine-criteria block, declared-absent rule text).

No extraction is performed: objective.classify_report_type=false, so `claims` stays empty.
No claim is marked verified anywhere in this package: hash equality is a mechanical
identity check, verification status belongs to the platform gate.

Zero-hand-copy discipline: every quote in the manifest is *sliced out of the fetched
markdown* at emit time (anchor = line number + sub-string selector), then re-checked to
occur exactly once in the source. Nothing is retyped from memory.

Scope guard: only report_id=11421 is read. No other report is touched.

Outputs (all inside the worktree):
    docs/kf/wp-11421-01/asset_manifest.json   asset registry (the package's output)
    docs/kf/wp-11421-01/kf_result.json        kf_result.v1 envelope (platform-facing)
    docs/kf/wp-11421-01/locator_check.json    quote -> char/line span resolution report
    docs/kf/wp-11421-01/source.md             verbatim copy of the source markdown
    docs/kf/wp-11421-01/sha256.txt            recomputed digest

Usage:
    python3 scripts/kf_wp11421_01_register.py                # fetch from platform
    python3 scripts/kf_wp11421_01_register.py --source-file docs/kf/wp-11421-01/source.md
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request

REPORT_ID = "11421"
SOURCE_URI = "tensor://reports/11421"
SOURCE_FIELD = "markdown"
# contract-declared digest (source_hash in the work-package contract) — recomputed, never trusted
EXPECTED_SHA256 = "f85c29fe650365140152064807d90b2accdf43382f2222956470f3521e0a280a"
EXPECTED_CHARS = 18542
EXPECTED_TITLE = "P270W1-N07 端到端不确定度传播：几何→阻力→推进→EEXI/CII 六因子分解（蒙特卡洛 + Sobol）"
EXPECTED_SCENARIO = "ship_performance"
PKG = "wp-11421-01"
OUT = "docs/kf/wp-11421-01"  # must live under docs/: the push gate drops artifacts/**

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


# --------------------------------------------------------------------------- anchors
# Every entry: (asset_id, asset_class, label, section, resolution, anchor, note, check)
# anchor = (line_no_1based, start_substr|None, end_substr|None)
#   None/None      -> whole line (trailing newline stripped)
#   start only     -> from start_substr to end of line
#   both           -> inclusive slice start_substr..end_substr
# The quote is SLICED FROM THE FETCHED MARKDOWN, so it is verbatim by construction.
ASSETS = [
    ("A01", "figure", "fig1_eexi_pdf.png — EEXI 达到值 PDF + 要求值竖线 + 5–95% 带 + 合规概率",
     "§3.5 图", "resolved_in_source",
     (260, "`fig1_eexi_pdf.png`", None),
     "platform record figures[0]; name matched against figures[] of the report payload",
     "figure name present in platform record figures[] (exact name match)"),
    ("A02", "figure", "fig2_cii_pdf.png — CII 同上（PDF/要求值/5–95% 带/合规概率）",
     "§3.5 图", "resolved_in_source",
     (261, "`fig2_cii_pdf.png`", None),
     "platform record figures[1]; name match", "figure name present in platform record figures[] (exact name match)"),
    ("A03", "figure", "fig3_sobol_groups.png — 六因子组一阶/总效应 Sobol（EEXI、CII 双面板，带标准误）",
     "§3.5 图", "resolved_in_source",
     (262, "`fig3_sobol_groups.png`", None),
     "platform record figures[2]; name match", "figure name present in platform record figures[] (exact name match)"),
    ("A04", "figure", "fig4_convergence.png — 样本量收敛：σ 与合规概率 vs N",
     "§3.5 图", "resolved_in_source",
     (263, "`fig4_convergence.png`", None),
     "platform record figures[3]; name match", "figure name present in platform record figures[] (exact name match)"),
    ("A05", "figure", "fig5_sigma_control.png — σ→0 负控：σ 比 vs ε + 概率阶跃",
     "§3.5 图", "resolved_in_source",
     (264, "`fig5_sigma_control.png`", None),
     "platform record figures[4]; name match", "figure name present in platform record figures[] (exact name match)"),
    ("A06", "figure", "fig6_sensitivity.png — 灵敏度结构：解析 δ 法 vs 有限差分 vs MC Sobol 三对照",
     "§3.5 图", "resolved_in_source",
     (265, "`fig6_sensitivity.png`", None),
     "platform record figures[5]; name match", "figure name present in platform record figures[] (exact name match)"),
    ("A07", "artifact_path", "artifacts/P270W1-N07/{results.json, tables.md, fig1..fig6} — 生产者工件目录",
     "§preamble 工件", "referenced_unresolved",
     (5, "`artifacts/P270W1-N07/{results.json, tables.md, fig1..fig6}`", None),
     "path declared in report; the files live in ship-performance-platform (producing repo), "
     "not in this report record -> not resolvable from tensor://reports/11421",
     "declared path resolvable inside the report payload (markdown/figures/record)? -> no"),
    ("A08", "data_table", "附录 A · 数字表（声明为 artifacts/P270W1-N07/tables.md 原文）",
     "附录 A", "referenced_unresolved",
     (331, "## 附录 A · 数字表", None),
     "appendix says it reproduces tables.md verbatim; the 8 tables ARE inline (see A16) but "
     "byte-identity with the外部 tables.md cannot be checked from this record -> unresolved",
     "byte-identity check between appendix A and external tables.md possible? -> no"),
    ("A09", "source_code", "scripts/p270w1_n07_uncertainty.py — 生成全部数字的执行脚本",
     "§preamble 执行脚本", "referenced_unresolved",
     (4, "**执行脚本**", None),
     "code pointer into ship-performance-platform; file not attached to the report record",
     "file attached/resolvable from record? -> no"),
    ("A10", "module", "backend/modules/green_uq/ — UQ 模块（mc/sobol/spec）",
     "§preamble 模块", "referenced_unresolved",
     (4, "`backend/modules/green_uq/`", "`backend/modules/green_uq/`"),
     "module pointer; source not attached to the record",
     "module sources attached/resolvable from record? -> no"),
    ("A11", "module", "backend/physics/holtrop — Holtrop-Mennen 唯一实现（R_T 求解器）",
     "§2.1 确定性链", "referenced_unresolved",
     (74, "Holtrop-Mennen 唯一实现", None),
     "Holtrop implementation pointer; the regression coefficients themselves are not in the record",
     "solver source attached/resolvable from record? -> no"),
    ("A12", "api_function", "api/green_shipping: _gn_attained_index / _gn_attained_cii / _PowerChain / _gn_required_*",
     "§2.1 纪律 1", "referenced_unresolved",
     (92, "`api/green_shipping` 的 `_gn_attained_index`", None),
     "rule-formula single source reused by this node (判据 C1 证明同输入相对差 < 1e-9); "
     "function bodies not in the record",
     "function bodies attached/resolvable from record? -> no"),
    ("A13", "test", "test_chain.py::test_attained_index_unit_1852_fix — 1852 量纲回归测试",
     "§2.3 缺陷修复", "referenced_unresolved",
     (125, "`test_chain.py::test_attained_index_unit_1852_fix`", None),
     "regression test for the 1852 factor defect; test file not in the record",
     "test file attached/resolvable from record? -> no"),
    ("A14", "test", "test_green_shipping.py — 原有 18 条断言（只断言 idx > 0）",
     "§2.3 缺陷修复", "referenced_unresolved",
     (127, "原有 18 条 `test_green_shipping.py` 断言", None),
     "pre-existing test suite quoted by count only; file not in the record",
     "test file attached/resolvable from record? -> no"),
    ("A15", "config", "green_uq spec.py — 13 成员六因子不确定度谱 + 逐因子 provenance",
     "§1.3 不确定度谱", "referenced_unresolved",
     (45, "出处（`spec.py` 逐条）", None),
     "the 13-member spectrum table itself is inline (see A17); the spec.py provenance strings are not",
     "spec.py attached/resolvable from record? -> no"),
    ("A16", "data_table", "附录 A 表1–表8 数字表（程序化生成，勿手改）",
     "附录 A", "resolved_in_source",
     (333, "# P270W1-N07 数字表", None),
     "8 tables rendered inline in the appendix; each row is quotable from the markdown",
     "table block present verbatim in markdown? -> yes"),
    ("A17", "data_table", "§1.3 六因子不确定度谱（13 个成员，分布/1σ/作用位置）",
     "§1.3", "resolved_in_source",
     (43, "### 1.3 六因子不确定度谱", None),
     "inline Markdown table; 13 rows of (group, member, distribution, 1σ, action site)",
     "table present verbatim in markdown? -> yes"),
    ("A18", "machine_criteria", "results.json -> criteria C1–C10 与 all_pass 判据块",
     "§preamble 机器判据 / 附录 A 表8", "resolved_in_source",
     (6, "**机器判据**", None),
     "criteria block is reproduced inline as 表8 with all_pass = True; the producer-side "
     "results.json remains referenced_unresolved (A07)",
     "criteria block present verbatim in markdown? -> yes"),
    ("A19", "run_config", "运行配置（n_mc / n_sobol / n_anchor / n_convergence / seed / workers）",
     "附录 A 表头", "resolved_in_source",
     (336, "配置：", None),
     "seed and sample sizes are in the markdown -> the statistical results are re-runnable "
     "if the producer script (A09) is available",
     "config line present verbatim in markdown? -> yes"),
    ("A20", "result_field", "results.json.monte_carlo.numerics.out_of_holtrop_domain — Holtrop 域外推比例",
     "§4 注意点 5", "referenced_unresolved",
     (285, "`monte_carlo.numerics.out_of_holtrop_domain`", None),
     "only the field name is given; the numeric share is instead quoted in §3.2 (76999/200000)",
     "field value resolvable from record? -> no (field name only)"),
    ("A21", "rule_reference", "MEPC.328(76) / MEPC.353(78) 规则系数原文（要求值来源）",
     "§1.2 要求值", "declared_absent",
     (41, "（`WITHHELD`：系数转录自 MEPC.328(76)/MEPC.353(78)", None),
     "report itself declares WITHHELD: no offline copy of the rule text; consequently the "
     "required values cannot be independently recomputed from this record",
     "rule text attached/resolvable from record? -> no (declared WITHHELD)"),
    ("A22", "data_table", "§1.2 设计案例参数表（Kamsarmax 散货船 80 000 dwt）",
     "§1.2", "resolved_in_source",
     (26, "### 1.2 设计案例", None),
     "inline parameter table (L,B,T,Cb,Cm,Cp,displacement,DWT,MCR,SFOC,C_F,efficiencies,service speed)",
     "table present verbatim in markdown? -> yes"),
]


def fetch_markdown() -> tuple[str, dict]:
    user = os.environ["TENSOR_AGENT_USER"]
    pwd = os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req))
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise SystemExit("login returned no token")
    req = urllib.request.Request(
        f"{BASE}/tensor/reports/{REPORT_ID}", headers={"Authorization": "Bearer " + token}
    )
    payload = json.load(urllib.request.urlopen(req))
    return payload.get(SOURCE_FIELD) or "", payload


def _token() -> str:
    user = os.environ["TENSOR_AGENT_USER"]
    pwd = os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req))
    return tok.get("access_token") or tok.get("token")


def probe_figure(name: str, token: str) -> dict:
    """Fetch the figure payload from the report record. Never assume it exists."""
    url = f"{BASE}/tensor/reports/{REPORT_ID}/figures/{name}"
    try:
        req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
        resp = urllib.request.urlopen(req)
        body = resp.read()
        return {
            "probe": "GET /tensor/reports/<id>/figures/<name>",
            "http_status": resp.status,
            "bytes": len(body),
            "content_type": resp.headers.get("Content-Type", ""),
            "sha256": hashlib.sha256(body).hexdigest(),
            "png_magic": body[:8] == b"\x89PNG\r\n\x1a\n",
            "fetched": True,
        }
    except urllib.error.HTTPError as e:  # noqa: PERF203
        return {"probe": url, "http_status": e.code, "fetched": False,
                "error": e.read()[:200].decode("utf-8", "replace")}
    except Exception as e:  # pragma: no cover - network
        return {"probe": url, "fetched": False, "error": f"{type(e).__name__}: {e}"}


def line_offsets(md: str) -> list[int]:
    offs, pos = [0], 0
    for ln in md.split("\n"):
        pos += len(ln) + 1
        offs.append(pos)
    return offs


def resolve(md: str, anchor) -> dict:
    line_no, start_s, end_s = anchor
    lines = md.split("\n")
    if not (1 <= line_no <= len(lines)):
        raise SystemExit(f"anchor line {line_no} out of range")
    raw = lines[line_no - 1]
    if start_s is None:
        quote = raw.rstrip()
        col0, col1 = 0, len(quote)
    else:
        i = raw.find(start_s)
        if i < 0:
            raise SystemExit(f"anchor start {start_s!r} not found on line {line_no}: {raw!r}")
        if end_s is None:
            quote = raw[i:].rstrip()
            col0, col1 = i, i + len(quote)
        else:
            j = raw.find(end_s, i)
            if j < 0:
                raise SystemExit(f"anchor end {end_s!r} not found on line {line_no}")
            quote = raw[i : j + len(end_s)]
            col0, col1 = i, i + len(quote)
    offs = line_offsets(md)
    start_char = offs[line_no - 1] + col0
    end_char = offs[line_no - 1] + col1
    if md[start_char:end_char] != quote:
        raise SystemExit(f"offset mismatch on line {line_no}")
    occurrences = md.count(quote)
    return {
        "method": "char_span",
        "start_char": start_char,
        "end_char": end_char,
        "start_line": line_no,
        "end_line": line_no,
        "quote": quote,
        "unique": occurrences == 1,
        "_occurrences": occurrences,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-file", help="use a local verbatim copy instead of the platform API")
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--skip-schema", action="store_true")
    args = ap.parse_args()

    if args.source_file:
        md = open(args.source_file, encoding="utf-8").read()
        payload = {"id": int(REPORT_ID), "title": EXPECTED_TITLE,
                   "scenario_key": EXPECTED_SCENARIO, "figures": [], "tags": []}
        offline = True
    else:
        md, payload = fetch_markdown()
        offline = False

    data = md.encode("utf-8")
    digest = hashlib.sha256(data).hexdigest()
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "source.md"), "w", encoding="utf-8") as fh:
        fh.write(md)
    with open(os.path.join(args.out, "sha256.txt"), "w", encoding="utf-8") as fh:
        fh.write(f"sha256:{digest}\nchars={len(md)}\nbytes_utf8={len(data)}\n")

    checks = {
        "report_id_matches": str(payload.get("id")) == REPORT_ID,
        "hash_matches_contract": digest == EXPECTED_SHA256,
        "chars_matches_contract": len(md) == EXPECTED_CHARS,
        "title_matches_contract": payload.get("title") == EXPECTED_TITLE,
        "scenario_key_matches_contract": payload.get("scenario_key") == EXPECTED_SCENARIO,
    }
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    if not checks["hash_matches_contract"]:
        print("FATAL: source hash differs from the work-package contract", file=sys.stderr)
        return 2

    plat_figs = payload.get("figures") or []
    plat_names = [f.get("name") if isinstance(f, dict) else None for f in plat_figs]
    if offline:
        plat_names = ["(offline: figures[] unavailable)"] * 0  # do not fake a match offline

    token = None if offline else _token()
    assets, checks_out = [], []
    for aid, aclass, label, section, resolution, anchor, note, check in ASSETS:
        loc = resolve(md, anchor)
        occ = loc.pop("_occurrences")
        expected_result = {
            "resolved_in_source": "resolved",
            "referenced_unresolved": "unresolved",
            "declared_absent": "absent",
        }[resolution]
        # figure assets: resolution is decided by the platform record, not by the quote
        payload_info = None
        if aclass == "figure":
            fname = label.split(" ")[0]
            listed = fname in plat_names
            if offline:
                result = "unresolved"
                check = (f"figure {fname!r} payload probe + figures[] name match "
                         f"NOT RUN (offline replay)")
                note += " | offline replay: payload not verified"
            else:
                payload_info = probe_figure(fname, token)
                ok = bool(payload_info.get("fetched")) and payload_info.get("png_magic", False)
                result = "resolved" if (listed and ok) else "unresolved"
                check = (f"figures[] name match={listed}; GET figures/{fname} -> "
                         f"HTTP {payload_info.get('http_status')}, "
                         f"{payload_info.get('bytes')} B, PNG magic="
                         f"{payload_info.get('png_magic')}")
                if not ok:
                    note += " | WARNING: payload not retrievable as PNG"
        else:
            result = expected_result
        entry = {
            "asset_id": aid,
            "asset_class": aclass,
            "label": label,
            "in_report_section": section,
            "locator": loc,
            "resolution": resolution,
            "resolution_check": {"check": check, "result": result},
            "note": note,
        }
        if payload_info is not None:
            entry["payload"] = payload_info
        assets.append(entry)
        checks_out.append({
            "asset_id": aid,
            "asset_class": aclass,
            "resolution": resolution,
            "resolution_result": result,
            "occurrences_in_source": occ,
            "unique": loc["unique"],
            "locator_resolvable": md[loc["start_char"]:loc["end_char"]] == loc["quote"],
            "quote_chars": len(loc["quote"]),
        })

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    dup_ids = len({a["asset_id"] for a in assets}) != len(assets)
    bad_quotes = [c["asset_id"] for c in checks_out if not (c["unique"] and c["locator_resolvable"])]

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(data),
            "title": payload.get("title", ""),
            "scenario_key": payload.get("scenario_key", ""),
            "platform_figures": plat_names,
            "platform_tags": payload.get("tags") or [],
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
        "claims_note": "Empty by contract: objective.classify_report_type=false and objective.extract_claims "
                       "is not declared. No claim was generated to fill a quota; no claim is marked verified.",
        "integrity": {
            "quote_uniqueness": all(c["unique"] for c in checks_out),
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == EXPECTED_SHA256,
            "duplicate_asset_ids": dup_ids,
            "locators_all_resolvable": not bad_quotes,
        },
        "limits": [
            "Registration only. No numbers were re-derived; no statistic was recomputed from the producer "
            "artifacts (they are not in this record — see A07).",
            "Figures are resolved by NAME against the platform record's figures[]; the PNG bytes were not "
            "inspected, so figure content is not attested.",
            "Required values (EEXI_req / CII_req) depend on rule coefficients the report itself marks "
            "WITHHELD (A21); they are registered as declared_absent, not as verified inputs.",
            "Appendix A claims to be tables.md verbatim; byte-identity to the外部 file cannot be checked "
            "from this record and is left unresolved (A08).",
        ],
    }

    with open(os.path.join(args.out, "asset_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    result = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": f"sha256:{digest}",
            "source_field": SOURCE_FIELD,
            "producer": "scripts/kf_wp11421_01_register.py",
            "emitted_at": payload.get("created_at") or "",
            "notes": "asset registration only; no extraction, no claim verification; "
                     "hash recomputed from the fetched markdown UTF-8 bytes",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    with open(os.path.join(args.out, "kf_result.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    locator_check = {
        "report_id": REPORT_ID,
        "source_hash": f"sha256:{digest}",
        "checks": checks,
        "n_assets": len(assets),
        "assets": checks_out,
        "summary": {
            "quotes_unique": sum(1 for c in checks_out if c["unique"]),
            "quotes_total": len(checks_out),
            "locators_resolvable": sum(1 for c in checks_out if c["locator_resolvable"]),
            "bad": bad_quotes,
        },
    }
    with open(os.path.join(args.out, "locator_check.json"), "w", encoding="utf-8") as fh:
        json.dump(locator_check, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    # ---------------------------------------------------------------- schema gate
    gate = {
        "kf_result_v1": "not_run",
        "asset_manifest_v1": "not_run",
        "valid_json": "pass",
    }
    if not args.skip_schema:
        try:
            import jsonschema
        except ImportError:
            gate["kf_result_v1"] = "skipped(no jsonschema)"
        else:
            with open("schemas/kf_result.v1.schema.json", encoding="utf-8") as fh:
                jsonschema.validate(result, json.load(fh))
            gate["kf_result_v1"] = "pass"
            local = os.path.join(args.out, "asset_manifest.v1.schema.json")
            if os.path.exists(local):
                with open(local, encoding="utf-8") as fh:
                    jsonschema.validate(manifest, json.load(fh))
                gate["asset_manifest_v1"] = "pass"
            path_gate = {
                # contract vocabulary first (the five acceptance items of the work package)
                "valid_json": gate["valid_json"],
                "schema_pass": gate["kf_result_v1"] == "pass" and gate["asset_manifest_v1"] == "pass",
                "source_locator_resolvable": not bad_quotes,
                "source_hash_matches": digest == EXPECTED_SHA256,
                "no_duplicate_ids": not dup_ids,
                "all_claims_have_evidence_or_explicit_unresolved_status": True,
                # detail behind the aggregate flags
                "detail_schema_kf_result": gate["kf_result_v1"],
                "detail_schema_asset_manifest": gate["asset_manifest_v1"],
                "_unused": None,
            }
            path_gate.pop("_unused", None)
            with open(os.path.join(args.out, "acceptance_check.json"), "w", encoding="utf-8") as fh:
                json.dump({"package_id": PKG, "checks": path_gate,
                           "detail": {"bad_quotes": bad_quotes, "n_assets": len(assets)}},
                          fh, ensure_ascii=False, indent=2)
                fh.write("\n")
            print(json.dumps(path_gate, ensure_ascii=False, indent=2))

    print(f"[ok] {len(assets)} assets -> {args.out}/asset_manifest.json")
    print(f"[ok] sha256:{digest}")
    return 0 if (not bad_quotes and not dup_ids) else 1


if __name__ == "__main__":
    raise SystemExit(main())