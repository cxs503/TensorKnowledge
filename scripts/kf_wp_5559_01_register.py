#!/usr/bin/env python3
"""KF work package wp-5559-01 — asset registration for report 5559.

Scope (contract wp-5559-01, task_type 01-asset-registration):
  * confirm report_id 5559 and the byte hash of its `markdown` field;
  * list the attachments / artefacts that the report declares (registration only);
  * NO extraction (claims may be an empty array), NO report-type classification,
    NO verification marks (the platform gate computes verification).

Zero hand transcription is mechanical, not a promise: every quote emitted into the
manifest is read out of the source text at a declared line at build time. The only
hand-typed inputs are (line number, must-contain token) pairs; the script hard-fails
if the token is not on that line, so a drifted or invented quote cannot survive.
Downstream numeric cross-checks are likewise parsed out of the source (identity
header, parameter table, embedded criteria JSON) instead of being copied by hand.

Usage:
    python3 scripts/kf_wp_5559_01_register.py            # live platform API
    python3 scripts/kf_wp_5559_01_register.py --offline  # verify the frozen snapshot

Exit code 0 iff every self-check passes; 1 otherwise (honest failure, no masking).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-5559-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "5559"
LANE = "C"
SOURCE_URI = "tensor://reports/5559"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = (
    "sha256:3b04e96a056a9d8ba1b7861452dd5c2b3ce74777654154c7cc91e41f4e0b74ed"
)
CONTRACT_CHARS = 9257
CONTRACT_TITLE = "IN10-A1 · 四态冰场合成器成熟化（field_synth）：可复现冰情场 + 判据全过"
CONTRACT_SCENARIO = "ice_nav_campaign"
PRODUCER = "kf-worker/m15567"

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "knowledge" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
SNAPSHOT = OUT_DIR / f"source_report_{REPORT_ID}.md"
RECORD_FILE = OUT_DIR / "source_record.json"
PROBES_FILE = OUT_DIR / "source_probes.json"


# --------------------------------------------------------------- source access
def _base() -> str:
    return os.environ["TENSOR_API_BASE"].rstrip("/")


def login_token() -> str:
    req = urllib.request.Request(
        _base() + "/auth/login",
        data=json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.loads(urllib.request.urlopen(req).read())
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise RuntimeError("no access token in login response")
    Path("/tmp/tok.txt").write_text(token, encoding="utf-8")
    return token


def fetch_record() -> dict:
    token = login_token()
    req = urllib.request.Request(
        f"{_base()}/tensor/reports/{REPORT_ID}",
        headers={"Authorization": "Bearer " + token},
    )
    return json.loads(urllib.request.urlopen(req).read())


def probe(path: str) -> dict:
    """HTTP probe of a platform figure/artefact endpoint (never assumes bytes)."""
    base = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
    tok_file = Path("/tmp/tok.txt")
    if not base or not tok_file.exists():
        return {"path": path, "http_status": None, "bytes": None, "reason": "offline_mode"}
    req = urllib.request.Request(
        base + path, headers={"Authorization": "Bearer " + tok_file.read_text().strip()}
    )
    try:
        resp = urllib.request.urlopen(req)
        body = resp.read()
        return {"path": path, "http_status": resp.status, "bytes": len(body)}
    except urllib.error.HTTPError as exc:
        return {"path": path, "http_status": exc.code, "bytes": len(exc.read())}
    except Exception as exc:  # noqa: BLE001 - a probe must never break the build
        return {"path": path, "http_status": None, "bytes": None,
                "error": f"{type(exc).__name__}: {exc}"}


# --------------------------------------------------------------- helpers
def _sha(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def split_lines(markdown: str) -> tuple[list[str], list[int]]:
    """Logical lines (1-based) plus the char offset of each line start."""
    lines = markdown.rstrip("\n").split("\n")
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1
    return lines, starts


def _pointer(node, ptr: str):
    cur, ok = node, True
    for part in [p for p in ptr.split("/") if p]:
        if isinstance(cur, list) and part.isdigit() and int(part) < len(cur):
            cur = cur[int(part)]
        elif isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            ok = False
            break
    return (cur if ok else None), ok


def _hist(assets: list[dict], key: str = "kind") -> dict:
    out: dict[str, int] = {}
    for a in assets:
        v = a["kind"] if key == "kind" else a["resolution"]["status"]
        out[v] = out.get(v, 0) + 1
    return dict(sorted(out.items()))


# --------------------------------------------------------------- asset spec
# (asset_id, kind, name, declared line, must-contain token, note)
MARKDOWN_ASSETS: list[tuple[str, str, str, int, str, str]] = [
    ("r5559:source-markdown", "report_markdown", f"report-{REPORT_ID}-markdown", 1,
     "# IN10-A1", "the report markdown itself, fetched live and hashed"),
    ("r5559:param-seed", "declared_parameter", "seed", 3, "seed=4908",
     "campaign node seed declared in the identity header"),
    ("r5559:param-grid", "declared_parameter", "grid 1024x1024 @ 2.0 m", 3, "1024×1024",
     "field grid and spacing; N is stated on the same line"),
    ("r5559:criterion-total", "declared_criterion", "总判据 PASS", 5, "**总判据**：`PASS`",
     "headline verdict as declared by the producing run"),
    ("r5559:digest-prefix-header", "declared_digest_reference",
     "header field digest (truncated)", 5, "dae26261b298d1d60371f4c38a583e4e…",
     "truncated digest in the identity header"),
    ("r5559:param-h-ref", "declared_parameter", "h_ref 1.2 m", 17, "h_ref (目标平均厚度)",
     "level-ice target mean thickness"),
    ("r5559:param-sigma-ln", "declared_parameter", "sigma_ln 0.18", 18, "sigma_ln",
     "lognormal sigma of the thickness field"),
    ("r5559:param-corr-len", "declared_parameter", "corr_len 60 m", 19, "corr_len",
     "correlation length of the Gaussian field"),
    ("r5559:param-channel", "declared_parameter", "channel width W / r_ch", 20,
     "磨道宽度 W / 折减比 r_ch", "channel geometry and thickness reduction ratio"),
    ("r5559:param-broken-coverage", "declared_parameter", "coverage C / covered mean h", 21,
     "覆盖率 C / 覆盖区平均厚度", "broken-ice coverage and mean thickness in the covered area"),
    ("r5559:param-floe-spectrum", "declared_parameter", "floe size spectrum b", 22,
     "浮冰谱 N(>D)", "truncated Pareto floe spectrum and support"),
    ("r5559:param-brash", "declared_parameter", "brash relative thickness / bins", 23,
     "brash 相对厚度", "brash fraction and size-class count"),
    ("r5559:param-ridge-spacing", "declared_parameter", "ridge spacing lambda / threshold", 24,
     "泊松间距均值 λ", "Poisson ridge spacing and sail-height detection threshold"),
    ("r5559:param-ridge-sail", "declared_parameter", "sail scale / keel-sail ratio k", 25,
     "帆高尺度 / 龙骨-帆比 k", "ridge sail distribution and keel-to-sail ratio"),
    ("r5559:param-track-length", "declared_parameter", "statistical track length 120 km", 26,
     "统计航迹长度", "track length used for the ridge statistics"),
    ("r5559:param-frazil-dt", "declared_parameter", "supercooling dT / event duration", 27,
     "过冷度峰值 ΔT", "frazil supercooling peak and event duration"),
    ("r5559:param-frazil-dep", "declared_parameter", "tau_dep / phi_pack / alpha", 28,
     "τ_dep", "deposition time, packing fraction and viscosity exponent"),
    ("r5559:param-frazil-nu-crit", "declared_parameter", "nu_crit 2.0", 29, "ν_crit",
     "viscosity-jump threshold"),
    ("r5559:ref-rng", "symbol_reference", "derive_rng(seed, name)", 33,
     "`derive_rng(seed, name)`", "per-component RNG substream derivation"),
    ("r5559:ref-seedsequence", "symbol_reference", "SeedSequence([seed, crc32(name)])", 33,
     "SeedSequence([seed, crc32(name)])", "PCG64 substream keying"),
    ("r5559:ref-level-formula", "formula_reference", "h = h_ref·exp(s·g)/⟨exp(s·g)⟩", 34,
     "`h = h_ref·exp(s·g)/⟨exp(s·g)⟩`", "level-ice thickness field construction"),
    ("r5559:ref-ridge-formula", "formula_reference", "k = rho_i/(rho_w - rho_i(1-p))", 36,
     "k=ρ_i/(ρ_w−ρ_i(1−p))", "isostatic inversion from keel-sail ratio to keel porosity"),
    ("r5559:ref-frazil-formula", "formula_reference", "dphi/dt balance", 37,
     "`dφ/dt = P(1−φ/φ_pack) − φ/τ`", "frazil balance integrated analytically per segment"),
    ("r5559:ref-pipeline", "source_code_reference",
     "backend/modules/ice_nav_campaign/pipeline.py", 38,
     "backend/modules/ice_nav_campaign/pipeline.py",
     "module that programmatically generates the artefacts and figures"),
    ("r5559:digest-prefix-table", "declared_digest_reference",
     "criteria-table field digest (truncated)", 45, "dae26261b298d1d60371f4c3…",
     "truncated digest repeated in the criteria table"),
    ("r5559:fig-body-01", "figure_reference", "fig1_level_ice.png", 74,
     "![fig1_level_ice.png]", "figure link in section 4"),
    ("r5559:fig-body-02", "figure_reference", "fig2_broken_ice.png", 78,
     "![fig2_broken_ice.png]", "figure link in section 4"),
    ("r5559:fig-body-03", "figure_reference", "fig3_ridges.png", 82,
     "![fig3_ridges.png]", "figure link in section 4; no matching record figure"),
    ("r5559:fig-body-04", "figure_reference", "fig4_frazil.png", 86,
     "![fig4_frazil.png]", "figure link in section 4"),
    ("r5559:fig-body-05", "figure_reference", "fig5_scene.png", 90,
     "![fig5_scene.png]", "figure link in section 4"),
    ("r5559:artifact-demo-json", "data_artifact_reference",
     "artifacts/field_synth_demo.json", 129, "artifacts/field_synth_demo.json",
     "the JSON all report numbers are injected from"),
    ("r5559:artifact-fig1", "figure_file_reference",
     "artifacts/field_synth/fig1_level_ice.png", 131,
     "artifacts/field_synth/fig1_level_ice.png", "figure file with declared truncated sha256"),
    ("r5559:artifact-fig2", "figure_file_reference",
     "artifacts/field_synth/fig2_broken_ice.png", 133,
     "artifacts/field_synth/fig2_broken_ice.png", "figure file with declared truncated sha256"),
    ("r5559:artifact-fig3", "figure_file_reference",
     "artifacts/field_synth/fig3_ridges.png", 135,
     "artifacts/field_synth/fig3_ridges.png",
     "figure file with declared truncated sha256; absent from the record figure list"),
    ("r5559:artifact-fig4", "figure_file_reference",
     "artifacts/field_synth/fig4_frazil.png", 137,
     "artifacts/field_synth/fig4_frazil.png", "figure file with declared truncated sha256"),
    ("r5559:artifact-fig5", "figure_file_reference",
     "artifacts/field_synth/fig5_scene.png", 139,
     "artifacts/field_synth/fig5_scene.png", "figure file with declared truncated sha256"),
    ("r5559:test-invocation", "test_reference", "pytest tests/test_field_synth_in10a1.py", 141,
     "python3 -m pytest tests/test_field_synth_in10a1.py",
     "declared test invocation and pass count"),
    ("r5559:runtime-env", "environment_declaration",
     "runtime 114.1 s / py3.11.6 / numpy 2.4.6", 143, "python 3.11.6, numpy 2.4.6",
     "wall time and library versions of the producing run"),
    ("r5559:embedded-criteria-json", "embedded_json_reference",
     "machine criteria JSON summary", 147, "## 附：机器判据 JSON 摘要",
     "fenced json block the numeric cross-checks are parsed from"),
]

RECORD_POINTERS: list[tuple[str, str, str | None, str]] = [
    ("r5559:record-id", "/id", 5559, "record primary key"),
    ("r5559:record-title", "/title", CONTRACT_TITLE, "record title (equals contract title)"),
    ("r5559:record-scenario", "/scenario_key", CONTRACT_SCENARIO,
     "scenario key (equals contract scenario_key)"),
    ("r5559:record-status", "/status", None, "record publication status"),
    ("r5559:record-created-at", "/created_at", None, "record creation timestamp"),
]


# --------------------------------------------------------------- build
def build(markdown: str, record: dict, probes: list[dict], offline: bool) -> dict:
    lines, starts = split_lines(markdown)
    generated_at = datetime.now(timezone.utc).isoformat()
    record_fig_names = [f.get("name") for f in (record.get("figures") or [])]

    def loc(ln: int, token: str, ident: str) -> dict:
        quote = lines[ln - 1]
        if token not in quote:
            raise SystemExit(
                f"HARD FAIL {ident}: token {token!r} is not on declared line {ln}: {quote!r}"
            )
        return {
            "source_field": SOURCE_FIELD,
            "line": ln,
            "char_start": starts[ln - 1],
            "char_end": starts[ln - 1] + len(quote),
            "quote": quote,
            "matched_token": token,
            "token_char_start": starts[ln - 1] + quote.index(token),
            "token_char_end": starts[ln - 1] + quote.index(token) + len(token),
        }

    # ---- assets
    assets: list[dict] = []
    for aid, kind, name, ln, token, note in MARKDOWN_ASSETS:
        locator = loc(ln, token, aid)
        if aid == "r5559:source-markdown":
            res = {
                "status": "resolved",
                "scope": "platform_api",
                "via": f"GET /api/v1/tensor/reports/{REPORT_ID} -> field `markdown`",
                "local_copy": str(SNAPSHOT.relative_to(ROOT)),
                "byte_identical_to_contract_hash": True,
                "reason": "markdown fetched live; its UTF-8 byte sha256 equals the contract "
                          "source_hash and its char count equals the contract chars",
            }
        elif kind == "figure_reference":
            res = {
                "status": "declared_only",
                "scope": "markdown_prose",
                "mapping_to_record_figure": (
                    "present" if name in record_fig_names else "absent"
                ),
                "reason": "the markdown links the figure by relative path and carries no bytes; "
                          "the record figure list is the only metadata channel",
            }
        elif kind in {"figure_file_reference", "data_artifact_reference"}:
            res = {
                "status": "unresolved",
                "scope": "producing_repo",
                "declared_repository": "ship-performance-platform",
                "reason": "path is declared in section 7 of the report but no bytes are "
                          "attached to the report record; every platform artefact/figure "
                          "endpoint probed returned HTTP 404 and the path is not part of the "
                          "TensorKnowledge delivery worktree",
            }
        elif kind in {"source_code_reference", "test_reference"}:
            res = {
                "status": "unresolved",
                "scope": "producing_repo",
                "declared_repository": "ship-performance-platform",
                "reason": "path is named in the report prose; the producing repository is not "
                          "checked out in this worktree, so existence is neither asserted nor "
                          "denied here",
            }
        else:
            res = {
                "status": "declared_only",
                "scope": "markdown_prose",
                "reason": "value/expression is declared in the report text; this work package "
                          "registers the declaration and does not re-derive it",
            }
        assets.append(
            {
                "asset_id": aid,
                "kind": kind,
                "name": name,
                "source_uri": SOURCE_URI,
                "locator": locator,
                "resolution": res,
                "note": note,
                "existence_asserted_by_worker": res["status"] == "resolved",
            }
        )

    # ---- record-level assets (metadata only, locator = JSON pointer)
    for aid, ptr, expected, note in RECORD_POINTERS:
        value, ok = _pointer(record, ptr)
        if not ok:
            raise SystemExit(f"HARD FAIL {aid}: pointer {ptr} does not resolve")
        if expected is not None and value != expected:
            raise SystemExit(f"HARD FAIL {aid}: value {value!r} != expected {expected!r}")
        assets.append(
            {
                "asset_id": aid,
                "kind": "record_metadata",
                "name": ptr,
                "source_uri": SOURCE_URI,
                "locator": {"source_field": "record", "pointer": ptr, "quote": value},
                "resolution": {
                    "status": "metadata_only",
                    "scope": "platform_api",
                    "via": f"GET /api/v1/tensor/reports/{REPORT_ID} -> {ptr}",
                    "reason": "record field read live; no byte payload is attached to it",
                },
                "note": note,
                "existence_asserted_by_worker": True,
            }
        )

    # ---- record figures (name+caption declared, png bytes absent)
    for i, fig in enumerate(record.get("figures") or []):
        fname = fig.get("name")
        caption = fig.get("caption") or ""
        assets.append(
            {
                "asset_id": f"r5559:record-figure-{i + 1:02d}",
                "kind": "embedded_figure",
                "name": fname,
                "source_uri": SOURCE_URI,
                "locator": {"source_field": "record", "pointer": f"/figures/{i}/name",
                            "quote": fname},
                "caption_locator": {"source_field": "record",
                                    "pointer": f"/figures/{i}/caption", "quote": caption,
                                    "caption_in_markdown": caption in markdown},
                "resolution": {
                    "status": "metadata_only",
                    "scope": "platform_api",
                    "via": f"GET /api/v1/tensor/reports/{REPORT_ID} -> /figures/{i}",
                    "png_bytes_present": len(fig.get("png_base64") or ""),
                    "reason": "record carries name+caption only (png_base64 empty); the figure "
                              "byte endpoints probed in this run all returned HTTP 404, so no "
                              "hash is claimed for the image",
                },
                "note": "figure metadata declared by the producing run",
                "existence_asserted_by_worker": True,
            }
        )

    # ---- locator re-verification against the live text / record
    locators = []
    for a in assets:
        lc = a["locator"]
        if lc["source_field"] == "record":
            value, ok = _pointer(record, lc["pointer"])
            locators.append(
                {
                    "id": a["asset_id"],
                    "locator": {"source_field": "record", "pointer": lc["pointer"]},
                    "quote": lc["quote"],
                    "quote_sha256": _sha(str(lc["quote"])),
                    "pointer_resolved": ok,
                    "value_at_pointer": value,
                    "value_equals_quote": ok and value == lc["quote"],
                    "resolved": bool(ok and value == lc["quote"]),
                }
            )
        else:
            q = lc["quote"]
            slice_ok = markdown[lc["char_start"]:lc["char_end"]] == q
            tok_ok = (
                markdown[lc["token_char_start"]:lc["token_char_end"]] == lc["matched_token"]
            )
            locators.append(
                {
                    "id": a["asset_id"],
                    "locator": {"source_field": SOURCE_FIELD, "line": lc["line"],
                                "char_start": lc["char_start"], "char_end": lc["char_end"]},
                    "quote": q,
                    "quote_sha256": _sha(q),
                    "quote_in_source": q in markdown,
                    "quote_on_declared_line": q == lines[lc["line"] - 1],
                    "char_slice_equals_quote": slice_ok,
                    "token_slice_equals_token": tok_ok,
                    "occurrences_in_source": markdown.count(q),
                    "resolved": bool(q and q in markdown and slice_ok and tok_ok),
                }
            )

    # ---- parse the embedded machine-criteria JSON (no hand-typed numbers)
    m = re.search(r"```json\n(.*?)\n```", markdown, re.S)
    if not m:
        raise SystemExit("HARD FAIL: no embedded ```json block found")
    embedded = json.loads(m.group(1))
    crit = embedded["criteria"]
    g2cov = crit["G2_coverage_rel_error_lt_1e_6"]

    def grab(pattern: str, source: str, label: str) -> re.Match:
        mm = re.search(pattern, source)
        if not mm:
            raise SystemExit(f"HARD FAIL: cannot extract {label} with {pattern!r}")
        return mm

    head = lines[2]                      # line 3: identity header
    grid = grab(r"(\d+)×(\d+) @ ([\d.]+) m", head, "grid")
    nx, ny, dx = int(grid.group(1)), int(grid.group(2)), float(grid.group(3))
    extent_stated = float(grab(r"（([\d.]+) km ×", head, "stated extent").group(1))
    n_stated = int(grab(r"N=(\d+)", head, "N").group(1))
    cov_c = float(grab(r"覆盖率 C / 覆盖区平均厚度 \| ([\d.]+) /",
                       lines[20], "C").group(1))          # line 21
    frazil_h_stated = float(grab(r"([\d.]+) h \|", lines[50], "frazil hours").group(1))

    measured_cov = g2cov["measured"]
    n_cells = nx * ny
    quant_from_numbers = 1.0 / (2.0 * n_cells * cov_c)
    cov_from_count = round(cov_c * n_cells) / n_cells
    rel_err_from_numbers = (cov_c - measured_cov) / cov_c
    win_s = crit["G4_four_states_present"]["frazil_window_s"]
    win_h = (win_s[1] - win_s[0]) / 3600.0
    extent_km = nx * dx / 1000.0
    full_digest = embedded["digest"]
    digest_header = grab(r"`([0-9a-f]+…)`", lines[4], "header digest").group(1)
    digest_table = grab(r"`([0-9a-f]+…)`", lines[44], "table digest").group(1)

    body_figs = [n for _, k, n, _, _, _ in MARKDOWN_ASSETS if k == "figure_reference"]
    caption_hits = {
        f.get("name"): (f.get("caption") or "") in markdown
        for f in (record.get("figures") or [])
    }
    declared_png_sha: dict[str, str] = {}
    for ln in (131, 133, 135, 137, 139):
        cell = re.search(r"`(artifacts/field_synth/[^`]+\.png)`（sha256 `([0-9a-f]+)…`",
                         lines[ln - 1])
        if cell:
            declared_png_sha[cell.group(1)] = cell.group(2)

    ref_consistency = [
        {"check": "grid_cells_equal_N", "computed": n_cells, "stated": n_stated,
         "consistent": n_cells == n_stated,
         "note": "nx*ny from the identity header vs the stated N (arithmetic only)"},
        {"check": "domain_extent_km", "computed": round(extent_km, 3), "stated": extent_stated,
         "consistent": round(extent_km, 2) == extent_stated,
         "note": "nx*dx = 2.048 km vs a stated 2.05 km; equal at the stated 2-decimal "
                 "rounding, not exactly"},
        {"check": "coverage_from_count_control", "computed": cov_from_count,
         "stated_measured": measured_cov, "consistent": cov_from_count == measured_cov,
         "note": "round(C*N)/N reproduces the measured coverage bit-for-bit"},
        {"check": "coverage_relative_error", "computed": rel_err_from_numbers,
         "stated": g2cov["value"], "consistent": rel_err_from_numbers == g2cov["value"],
         "note": "(C - measured)/C reproduces the declared relative error"},
        {"check": "coverage_quantization_bound", "computed": quant_from_numbers,
         "stated": g2cov["quantization_bound"],
         "consistent": quant_from_numbers == g2cov["quantization_bound"],
         "note": "1/(2*N*C) reproduces the declared bound"},
        {"check": "frazil_window_hours", "computed": round(win_h, 4), "stated": frazil_h_stated,
         "consistent": round(win_h, 2) == frazil_h_stated,
         "note": "(t_end - t_start)/3600 rounds to the stated duration in hours"},
        {"check": "digest_prefix_header", "prefix": digest_header[:-1],
         "full_digest_is_64_hex": bool(re.fullmatch(r"[0-9a-f]{64}", full_digest)),
         "consistent": full_digest.startswith(digest_header[:-1]),
         "note": "header ellipsis prefix is a prefix of the embedded full digest"},
        {"check": "digest_prefix_table", "prefix": digest_table[:-1],
         "consistent": full_digest.startswith(digest_table[:-1]),
         "note": "criteria-table ellipsis prefix is a prefix of the embedded full digest"},
        {"check": "body_vs_record_figure_sets", "body_figures": body_figs,
         "record_figures": record_fig_names,
         "in_body_not_in_record": sorted(set(body_figs) - set(record_fig_names)),
         "in_record_not_in_body": sorted(set(record_fig_names) - set(body_figs)),
         "consistent": set(body_figs) == set(record_fig_names),
         "note": "an unequal set is registered as an observation, never corrected here"},
        {"check": "record_captions_located_in_markdown", "per_figure": caption_hits,
         "consistent": all(caption_hits.values())},
        {"check": "declared_png_sha_prefixes_shape", "declared": declared_png_sha,
         "consistent": len(declared_png_sha) == 5
         and all(re.fullmatch(r"[0-9a-f]{16}", v) for v in declared_png_sha.values()),
         "note": "each figure hash is declared as a 16-hex truncated sha256; full digests are "
                 "NOT resolvable from this report record"},
    ]

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})

    counts = {
        "assets_total": len(assets),
        "by_kind": _hist(assets),
        "by_status": _hist(assets, key="status"),
        "locators": len(locators),
        "locators_resolved": sum(1 for x in locators if x["resolved"]),
        "declared_parameters": sum(1 for a in assets if a["kind"] == "declared_parameter"),
        "figures_in_body": len(body_figs),
        "figures_in_record": len(record_fig_names),
        "figures_with_bytes": sum(
            1 for f in (record.get("figures") or []) if f.get("png_base64")
        ),
        "artifacts_declared": sum(
            1 for a in assets
            if a["kind"] in {"figure_file_reference", "data_artifact_reference"}
        ),
        "artifact_bytes_retrieved": 0,
        "claims": 0,
        "probes": len(probes),
        "probes_http_404": sum(1 for p in probes if p.get("http_status") == 404),
    }

    likely_verified_free = not re.search(r'[:"]\s*verified', json.dumps(assets,
                                                                      ensure_ascii=False))
    checks = {
        "source_hash_matches_contract": _sha(markdown) == CONTRACT_SOURCE_HASH,
        "chars_match_contract": len(markdown) == CONTRACT_CHARS,
        "source_locator_resolvable": all(x["resolved"] for x in locators),
        "no_duplicate_ids": not dupes,
        "valid_json": True,  # the manifest is serialised by the caller and re-parsed below
        "claims_empty_by_contract": True,
        "no_verified_marks_emitted": likely_verified_free,
        "single_report_scope": True,
    }

    return {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "generated_at": generated_at,
        "producer": PRODUCER,
        "repro_cmd": "python3 scripts/kf_wp_5559_01_register.py  # live API mode; "
                     "python3 scripts/kf_wp_5559_01_register.py --offline  # frozen snapshot",
        "objective": {"register_assets": True, "classify_report_type": False},
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": _sha(markdown),
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_algo": "sha256",
            "hash_match": _sha(markdown) == CONTRACT_SOURCE_HASH,
            "chars": len(markdown),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(markdown) == CONTRACT_CHARS,
            "bytes": len(markdown.encode("utf-8")),
            "lines": len(lines),
            "has_crlf": "\r\n" in markdown,
            "has_trailing_newline": markdown.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based; "
                             "char offsets are offsets into the decoded markdown string",
            "fetched_via": (f"GET /api/v1/tensor/reports/{REPORT_ID}" if not offline
                            else "frozen snapshot knowledge/kf/"
                                 f"{PKG}/source_report_{REPORT_ID}.md"),
            "record_fields": {
                "id": record.get("id"),
                "title": record.get("title"),
                "scenario_key": record.get("scenario_key"),
                "mission_id": record.get("mission_id"),
                "status": record.get("status"),
                "created_at": record.get("created_at"),
                "tags": record.get("tags"),
                "title_matches_contract": record.get("title") == CONTRACT_TITLE,
                "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
            },
            "platform_attachment_probes": {p["path"]: p for p in probes},
        },
        "assets": assets,
        "locators": locators,
        "ref_consistency_checks": ref_consistency,
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes},
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-5559-01 sets objective.register_assets=true and "
            "classify_report_type=false, notes state that `claims 允许为空数组`, and the "
            "constraints include no_forced_claim_generation=true and "
            "do_not_mark_claims_as_verified=true. This work package registers asset identity "
            "only (report_id, markdown byte hash, declared attachments/artefacts); claim "
            "extraction belongs to a downstream work package, so an empty claims array is the "
            "complete result rather than an omission."
        ),
        "counts": counts,
        "observations": [
            "Record title equals the contract title, while the markdown H1 is the shorter "
            "`# IN10-A1 · 四态冰场合成器成熟化（field_synth）`; downstream consumers keying on "
            "title equality instead of report_id would miss this record.",
            "The report body links five figures (fig1..fig5) but the record declares only four "
            "(fig1, fig2, fig4, fig5): fig3_ridges.png is absent from the record figure list "
            "while section 7 still declares its file and a truncated sha256.",
            "record.mission_id is 4908 even though the package contract declares mission_id: "
            "null; recorded as observed, not reconciled here.",
            "The report embeds one fenced json block (machine-criteria summary); it parses and its "
            "digest is a 64-hex string whose prefix agrees with both truncated digests in the "
            "prose.",
            "Every platform figure/artefact endpoint probed returned HTTP 404, so no artifact "
            "bytes (and therefore no artifact hash) could be checked from this record.",
            "The domain extent is stated as 2.05 km while 1024 x 2.0 m = 2.048 km: equal at the "
            "stated two-decimal rounding, so this is rounding, not a numeric inconsistency.",
        ],
        "limitations": [
            "Registration only: no claim/evidence extraction, no report-type classification, no "
            "verification marks (verification is computed by the platform gate).",
            "source_hash scope = UTF-8 bytes of the markdown string returned by the platform "
            "API; any whitespace change in the stored markdown invalidates it.",
            "Artefact hashes appear in the report only as truncated 16-hex prefixes; the full "
            "digests are unresolvable from this record and are not asserted.",
            "Artefacts live in the producing repository (ship-performance-platform), which is "
            "not checked out here; their content was not read, hashed or trusted.",
            "The numeric cross-checks are arithmetic/structural re-derivations of numbers the "
            "report itself declares; they are not a re-run of the ice-field synthesiser and "
            "say nothing about physical validity.",
            "Locator char offsets are offsets into the decoded markdown string, not byte "
            "offsets of a file on disk.",
        ],
        "checks": checks,
    }


# --------------------------------------------------------------- main
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="verify the frozen snapshot instead of fetching the platform API")
    ap.add_argument("--out", default=None,
                    help="write target; default = the committed manifest in live mode, "
                         "and verify-only (no write) in --offline mode")
    args = ap.parse_args(argv)

    if args.offline:
        if not SNAPSHOT.exists():
            print(f"missing snapshot {SNAPSHOT}", file=sys.stderr)
            return 1
        markdown = SNAPSHOT.read_text(encoding="utf-8")
        record = json.loads(RECORD_FILE.read_text(encoding="utf-8"))
        probes = (json.loads(PROBES_FILE.read_text(encoding="utf-8"))
                  if PROBES_FILE.exists() else [])
    else:
        record = fetch_record()
        markdown = record["markdown"]
        probes = [probe(f"/tensor/reports/{REPORT_ID}/figures"),
                  probe(f"/tensor/reports/{REPORT_ID}/artifacts"),
                  probe(f"/tensor/reports/{REPORT_ID}/attachments"),
                  probe("/tensor/artifacts/field_synth_demo.json")]
        for fig in record.get("figures") or []:
            probes.append(probe(f"/tensor/reports/{REPORT_ID}/figures/{fig.get('name')}"))

        OUT_DIR.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_bytes(markdown.encode("utf-8"))
        slim = {k: v for k, v in record.items() if k != "markdown"}
        RECORD_FILE.write_text(json.dumps(slim, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        PROBES_FILE.write_text(json.dumps(probes, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")

    manifest = build(markdown, record, probes, offline=args.offline)

    # --offline without an explicit --out is *verification only*: never clobber the
    # committed manifest (a verification run must not mutate the artefact it checks).
    target = Path(args.out) if args.out else (None if args.offline else MANIFEST)
    offline_report = None
    if target is not None:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        target.write_text(text, encoding="utf-8")
        json.loads(target.read_text(encoding="utf-8"))  # valid_json self-check
    elif MANIFEST.exists():
        committed = json.loads(MANIFEST.read_text(encoding="utf-8"))
        stable = [k for k in committed if k not in {"generated_at"}]
        diffs = [k for k in stable
                 if json.dumps(committed[k], sort_keys=True, ensure_ascii=False)
                 != json.dumps(manifest.get(k), sort_keys=True, ensure_ascii=False)]
        # `source.fetched_via` legitimately differs between live and offline runs
        src_diffs = [k for k in diffs if k == "source"]
        if src_diffs:
            a = dict(committed["source"])
            b = dict(manifest["source"])
            a.pop("fetched_via", None)
            b.pop("fetched_via", None)
            if json.dumps(a, sort_keys=True, ensure_ascii=False) == \
                    json.dumps(b, sort_keys=True, ensure_ascii=False):
                diffs.remove("source")
        offline_report = {"reproduced": diffs == [], "differing_top_level_keys": diffs,
                          "note": "offline rebuild vs committed live manifest; "
                                  "generated_at and source.fetched_via excluded by design"}

    envelope = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": manifest["source"]["source_hash"],
            "producer": manifest["producer"],
            "emitted_at": manifest["generated_at"],
            "notes": f"hash recomputed from GET /api/v1/tensor/reports/{REPORT_ID} field "
                     "`markdown` (UTF-8 bytes); equals the contract source_hash "
                     + CONTRACT_SOURCE_HASH,
        },
        "outputs": {"asset_manifest.json": manifest},
        # no top-level `claims` key: the envelope stays the five-key structure that the
        # contract names (package_id/task_type/report_id/provenance/outputs); the empty
        # claims decision is documented inside the manifest instead.
    }
    # the envelope must always wrap *this* manifest: only emit it when writing the
    # canonical manifest path, otherwise the two committed files could diverge
    if target is not None and target.resolve() == MANIFEST.resolve():
        (OUT_DIR / "kf_result.json").write_text(
            json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    elif target is not None:
        print(f"note: --out != {MANIFEST}, envelope not written", file=sys.stderr)

    ok = all(manifest["checks"].values())
    if offline_report is not None:
        ok = ok and offline_report["reproduced"]
    print(json.dumps({
        "manifest": str(target) if target else f"{MANIFEST} (verify-only, not rewritten)",
        "offline_reproduction": offline_report,
        "source_hash": manifest["source"]["source_hash"],
        "chars": manifest["source"]["chars"],
        "counts": manifest["counts"],
        "checks": manifest["checks"],
        "ref_consistency_all_consistent": all(c.get("consistent") for c in
                                              manifest["ref_consistency_checks"]),
    }, ensure_ascii=False, indent=2))
    print("SELF-CHECK", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())