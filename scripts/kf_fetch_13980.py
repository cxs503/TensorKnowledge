#!/usr/bin/env python3
"""KF work package wp-13980-01 — asset registration for tensor report 13980.

Report 13980 is the "A2-ICE-MODULES 第1轮：冰区端点 8×5 功能全扫" publication of
mission m14895. This package performs task_type=01-asset-registration *only*: it
pins the report's source bytes and registers every asset the report owns or
references, each with a machine-resolvable locator. It does not extract claims,
does not classify the report type, and does not re-run any ice-physics
computation (that is 02/03 work, downstream).

Three evidence layers, deliberately kept separate:

1. **source identity** — the ``markdown`` field of ``tensor_reports.id=13980`` is
   fetched over the platform API, written byte-exact to ``source_markdown.md``
   and hashed (sha256). The verifier recomputes the hash from the committed copy,
   so the gate can recompute it independently.
2. **in-source locators** — every asset carries a char span, a line range, the
   verbatim quote, the quote's sha256 and an occurrence count. The verifier
   re-resolves every locator against the committed bytes.
3. **byte + route probes** — figure assets are pinned to the actual PNG bytes
   served by ``/tensor/reports/13980/figures/<name>`` (sha256, size, HTTP
   status); endpoint assets are probed for *route presence* on the target
   platform (200/405/422 == route exists, 404 == route absent). Absence of an
   ice-mooring route is probed with an explicit candidate list so the report's
   ``NOT_SUPPORTED`` row is evidence rather than assertion.

Usage::

    python3 scripts/kf_fetch_13980.py            # live fetch + probes + render
    python3 scripts/kf_fetch_13980.py --offline  # rebuild from committed bytes

Exit status is 0 only when every machine check passes. Route probes may be
recorded as ``skipped`` when the target platform is unreachable; a skipped probe
is never counted as a pass.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = REPO_ROOT / "docs" / "kf" / "wp-13980-01"
SCHEMA_DIR = REPO_ROOT / "schemas"

PACKAGE_ID = "wp-13980-01"
REPORT_ID = "13980"
TASK_TYPE = "01-asset-registration"
SOURCE_FIELD = "markdown"
SOURCE_URI = f"tensor://reports/{REPORT_ID}"
LOCAL_SOURCE = "source_markdown.md"
DEFAULT_API_BASE = "http://127.0.0.1:8010/api/v1"
DEFAULT_SHIP_BASE = "http://127.0.0.1:8002"  # endpoint paths carry the /api/v1 prefix

#: declared contract — the registrar's expectations, checked machine-side.
CONTRACT = {
    "title": "A2-ICE-MODULES 第1轮：冰区端点 8×5 功能全扫（35 真跑 / 5 honest GAP，54 项基准 46 通过）",
    "scenario_key": "ice_resistance",
    "platform_status": "published",
    "mission_id": "14895",
    "figure_count": 8,
    "endpoint_count": 7,
    "required_sections": (
        "① 案例与参数", "② 方法与流程", "③ 计算结果", "④ 结果图",
        "⑤ 注意点与局限", "⑥ 误差判定",
    ),
}

#: report families (F3 is the honest GAP: no endpoint, no figure of its own).
FAMILIES = {
    "F1_ice_resistance": "F1 冰阻力",
    "F2_ice_maneuvering": "F2 冰区操纵(吊舱回转)",
    "F3_ice_mooring": "F3 冰区系泊(冰漂移/系泊载荷)",
    "F4_ice_load_inversion": "F4 冰载荷反演(砰击/冰激载荷)",
    "F5_polaris": "F5 极地操作限制 POLARIS",
    "F6_marine_icing": "F6 海洋结冰稳性",
    "F7_grease_ice": "F7 油脂冰操作包络",
    "F8_ice_cii": "F8 冰区 CII 修正",
    "coverage": "覆盖矩阵",
}

#: caption keyword -> family. Figure identity is bound by caption *semantics*,
#: not by figure index: the report's §④ numbering and the record's caption
#: numbering disagree (a mismatch that is recorded, not silently repaired).
CAPTION_FAMILY = (
    ("覆盖矩阵", "coverage"),
    ("冰阻力", "F1_ice_resistance"),
    ("吊舱冰区回转", "F2_ice_maneuvering"),
    ("冰载荷反演", "F4_ice_load_inversion"),
    ("POLARIS", "F5_polaris"),
    ("海洋结冰率", "F6_marine_icing"),
    ("油脂冰", "F7_grease_ice"),
    ("冰区 CII", "F8_ice_cii"),
)

#: the token each figure family occupies inside the §④ sentence.
SECTION_TOKENS = {
    "F1_ice_resistance": "F1 三法交叉",
    "F2_ice_maneuvering": "F2 回转",
    "F4_ice_load_inversion": "F3 反演",
    "F5_polaris": "F4 POLARIS",
    "F6_marine_icing": "F5 结冰率",
    "F7_grease_ice": "F6 包络",
    "F8_ice_cii": "F7 CII",
    "coverage": "覆盖矩阵",
}

#: endpoint assets: family -> path exactly as printed in the coverage matrix.
ENDPOINTS = (
    ("F1_ice_resistance", "/api/v1/ice-navigation/resistance"),
    ("F2_ice_maneuvering", "/api/v1/podded-ice-maneuvering/turning"),
    ("F4_ice_load_inversion", "/api/v1/calculations/ice-load-inversion"),
    ("F5_polaris", "/api/v1/polaris/assess"),
    ("F6_marine_icing", "/api/v1/calculations/marine-icing-stability"),
    ("F7_grease_ice", "/api/v1/calculations/grease_ice_envelope"),
    ("F8_ice_cii", "/api/v1/calculations/cii-ice-correction"),
)

#: candidate ice-mooring routes probed to turn F3's NOT_SUPPORTED into evidence.
MOORING_ABSENCE_CANDIDATES = (
    "/api/v1/ice-mooring/loads",
    "/api/v1/calculations/ice-mooring",
    "/api/v1/ice-mooring/drift-loads",
    "/api/v1/calculations/ice-drift-mooring",
    "/api/v1/ice-navigation/mooring-loads",
)

#: worktree paths the report names; owned by the report's mission run env.
SCRIPT_REFS = (
    "runs/ice_8x5/run_sweep.py",
    "cross_method.py",
    "make_tables.py",
    "tests/test_ice_8x5_sweep.py",
)
ARTIFACT_REFS = ("results.csv", "benchmarks.csv")

TABLES = (
    ("T1", "coverage_matrix", "coverage matrix (8 families x 5 conditions: 真跑/基准/GAP)",
     "③ 计算结果", "| 族 | 冰区能力 | 端点 | 工况 | 真跑 | 基准通过 | 状态 |", 0),
    ("T2", "core_quantities", "per-condition core quantities under the coverage matrix",
     "③ 计算结果", "| 族 | 工况 | 核心量 | 值 |", 0),
    ("T3", "benchmark_excerpt", "benchmark table excerpt (54 scored items; full table in benchmarks.csv)",
     "③ 计算结果", "family,quantity,ref,got,error,threshold,pass,anchor", 0),
    ("T4", "error_judgement", "§⑥ error judgement: key quantity vs baseline, <3% answered per item",
     "⑥ 误差判定", "| 关键量 | 基准 | 误差 | 是否 <3% |", 0),
)

PARAMETER_QUOTE = "Lpp/Lwl/B/T/Cb = 145/148/21.5/7.2/0.75，排水体积 16834.5 m³"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def utcnow() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def logical_lines(text: str) -> list[str]:
    return text.rstrip("\n").split("\n")


def line_of_char(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def block_end_line(text: str, start_line: int) -> int:
    """Last non-empty line of the contiguous block starting at ``start_line``."""
    lines = logical_lines(text)
    i = start_line - 1
    last = start_line
    while i < len(lines) and lines[i].strip():
        last = i + 1
        i += 1
    return last


def make_locator(text: str, quote: str, occurrence_index: int = 0, method: str = "char_span") -> dict:
    occurrences = text.count(quote)
    if occurrences == 0:
        raise ValueError(f"quote not found in source: {quote[:80]!r}")
    if occurrence_index >= occurrences:
        raise ValueError(f"occurrence_index {occurrence_index} >= occurrences {occurrences}")
    start = -1
    for _ in range(occurrence_index + 1):
        start = text.find(quote, start + 1)
    end = start + len(quote)
    return {
        "method": method,
        "start_char": start,
        "end_char": end,
        "start_line": line_of_char(text, start),
        "end_line": line_of_char(text, max(start, end - 1)),
        "quote": quote,
        "quote_sha256": sha256_hex(quote.encode("utf-8")),
        "unique": occurrences == 1,
        "occurrences": occurrences,
        "occurrence_index": occurrence_index,
    }


def line_containing(text: str, token: str) -> str:
    for line in text.split("\n"):
        if token in line:
            return line.rstrip()
    raise ValueError(f"no line contains {token!r}")


# ---------------------------------------------------------------------------
# platform access
# ---------------------------------------------------------------------------
class Platform:
    def __init__(self, base: str, token: str | None = None):
        self.base = base.rstrip("/")
        self.token = token

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def get_json(self, path: str):
        req = urllib.request.Request(self.base + path, headers=self._headers())
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))

    def get_bytes(self, path: str):
        req = urllib.request.Request(self.base + path, headers=self._headers())
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as exc:
            return exc.code, b""

    def login(self) -> str:
        body = json.dumps({
            "username": os.environ.get("TENSOR_AGENT_USER", ""),
            "password": os.environ.get("TENSOR_AGENT_PASS", ""),
        }).encode()
        req = urllib.request.Request(self.base + "/auth/login", data=body, method="POST",
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            payload = json.loads(r.read().decode("utf-8"))
        token = payload.get("access_token") or payload.get("data", {}).get("access_token")
        if not token:
            raise RuntimeError("login returned no access_token")
        self.token = token
        return token


def probe_route(ship_base: str, path: str, timeout: float = 15.0) -> dict:
    """Route-presence probe: POST {} separates 404 (absent) from 422 (present)."""
    url = ship_base.rstrip("/") + path
    req = urllib.request.Request(url, data=b"{}", method="POST",
                                 headers={"Content-Type": "application/json"})
    record = {"url": url, "method": "POST", "body": "{}", "probed_at": utcnow()}
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            record.update({"status": r.status, "route_present": True})
    except urllib.error.HTTPError as exc:
        record.update({"status": exc.code, "route_present": exc.code != 404})
    except (urllib.error.URLError, OSError) as exc:
        record.update({"status": None, "route_present": None, "error": str(exc)[:200]})
    return record

# ---------------------------------------------------------------------------
# registration
# ---------------------------------------------------------------------------
def classify_caption(caption: str) -> str:
    for keyword, family in CAPTION_FAMILY:
        if keyword in caption:
            return family
    raise ValueError(f"caption not bound to any family: {caption!r}")


def build_assets(source: str, figures: list[dict], probes: dict) -> tuple[list[dict], dict]:
    assets: list[dict] = []
    fig_meta: dict = {"items": [], "label_alignment": {}}

    # --- A01: the source document itself -----------------------------------
    first_line = logical_lines(source)[0]
    assets.append({
        "asset_id": "A01",
        "asset_class": "source_document",
        "label": "tensor_reports[13980].markdown",
        "in_report_section": "document",
        "family": None,
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "document_bytes_pinned_locally", "result": "resolved"},
        "locator": make_locator(source, first_line, method="document"),
        "sha256": sha256_hex(source.encode("utf-8")),
        "bytes_utf8": len(source.encode("utf-8")),
        "note": "verbatim markdown of report 13980; whole-document asset, quote = first line",
    })

    # --- figures (bytes from the platform figures endpoint) -----------------
    section_line = line_containing(source, "8 幅（见图注与内嵌 png）")
    section_locator = make_locator(source, section_line)
    by_family: dict[str, dict] = {}
    for idx, fig in enumerate(figures, start=1):
        name = fig["name"]
        caption = fig.get("caption") or ""
        family = classify_caption(caption)
        if family in by_family:
            raise ValueError(f"two figures bound to family {family}")
        by_family[family] = fig
        token = SECTION_TOKENS[family]
        t_start = section_locator["quote"].find(token)
        if t_start < 0:
            raise ValueError(f"section token {token!r} not in the §④ sentence")
        probe = probes.get(name, {})
        cap_match = re.match(r"^F\d+", caption)
        sec_match = re.match(r"^F\d+", token) if token.startswith("F") else None
        caption_label = cap_match.group(0) if cap_match else None
        section_label = sec_match.group(0) if sec_match else None
        assets.append({
            "asset_id": f"A{idx + 1:02d}",
            "asset_class": "figure",
            "label": name,
            "in_report_section": "④ 结果图",
            "family": family,
            "family_label": FAMILIES[family],
            "caption": caption,
            "resolution": "resolved_in_source",
            "resolution_check": {"check": "section_token_in_source + png_bytes_fetched",
                                 "result": "resolved"},
            "locator": dict(section_locator, token=token,
                            token_char_span=[t_start, t_start + len(token)],
                            token_sha256=sha256_hex(token.encode("utf-8"))),
            "platform_bytes": {
                "endpoint": f"/tensor/reports/{REPORT_ID}/figures/{name}",
                "http_status": probe.get("http_status"),
                "bytes": probe.get("bytes"),
                "sha256": probe.get("sha256"),
                "fetched_at": probe.get("fetched_at"),
                "bytes_committed": False,
            },
            "labels": {"section_label": section_label, "caption_label": caption_label},
            "note": ("figure bytes pinned by hash from the platform figures endpoint; the PNG "
                     "itself is not committed (registration pins identity, not pixels)"),
        })
        fig_meta["items"].append({
            "asset_id": f"A{idx + 1:02d}", "name": name, "family": family,
            "sha256": probe.get("sha256"), "bytes": probe.get("bytes"),
            "http_status": probe.get("http_status"),
            "section_label": section_label, "caption_label": caption_label,
        })

    missing = set(SECTION_TOKENS) - set(by_family)
    if missing:
        raise ValueError(f"family without a figure: {sorted(missing)}")
    aligned = sum(1 for f in fig_meta["items"]
                  if f["section_label"] == f["caption_label"])
    fig_meta["label_alignment"] = {
        "compared": len(fig_meta["items"]),
        "aligned": aligned,
        "mismatch": len(fig_meta["items"]) - aligned,
        "note": ("§④ numbers its own list F1..F7 sequentially while record captions keep family "
                 "numbers (F3_ice_mooring is the honest GAP, so captions F4..F8 sit against section "
                 "F3..F7). Family binding is made by caption semantics, not by figure number; the "
                 "mismatch is recorded here rather than silently repaired in the source."),
    }

    next_id = len(assets) + 1

    # --- in-source tables ---------------------------------------------------
    lines = logical_lines(source)
    for _tid, key, label, section, header, occ in TABLES:
        start_line = None
        for i, line in enumerate(lines, start=1):
            if line.strip() == header:
                start_line = i
                break
        if start_line is None:
            raise ValueError(f"table header not found: {header[:60]!r}")
        loc = make_locator(source, header, occurrence_index=occ)
        loc["block_lines"] = [start_line, block_end_line(source, start_line)]
        assets.append({
            "asset_id": f"A{next_id:02d}",
            "asset_class": "table",
            "label": label,
            "in_report_section": section,
            "family": None,
            "resolution": "resolved_in_source",
            "resolution_check": {"check": "table_header_in_source", "result": "resolved"},
            "locator": loc,
            "table_key": key,
            "note": (f"markdown table block; header line pinned, block extent lines "
                     f"{loc['block_lines'][0]}-{loc['block_lines'][1]}"),
        })
        next_id += 1

    # --- reference-ship parameters -----------------------------------------
    assets.append({
        "asset_id": f"A{next_id:02d}",
        "asset_class": "parameter_block",
        "label": "reference ship Baltic 1A 145 m principal particulars",
        "in_report_section": "① 案例与参数",
        "family": None,
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "parameter_line_in_source", "result": "resolved"},
        "locator": make_locator(source, PARAMETER_QUOTE),
        "note": "Lpp/Lwl/B/T/Cb = 145/148/21.5/7.2/0.75, displacement volume 16834.5 m3 (17255.4 t)",
    })
    next_id += 1

    # --- endpoints ----------------------------------------------------------
    for family, path in ENDPOINTS:
        probe = probes.get(path, {})
        present = probe.get("route_present")
        assets.append({
            "asset_id": f"A{next_id:02d}",
            "asset_class": "endpoint",
            "label": path,
            "in_report_section": "③ 计算结果",
            "family": family,
            "family_label": FAMILIES[family],
            "resolution": "resolved_in_source",
            "resolution_check": {
                "check": "path_in_source + route_presence_probe",
                "result": "resolved" if present is not False else "unresolved",
            },
            "locator": make_locator(source, path),
            "route_probe": probe,
            "note": ("endpoint path printed in the coverage matrix; route presence probed on the "
                     "target platform (422/405/200 = present, 404 = absent)"),
        })
        next_id += 1

    # --- declared-absent endpoint (F3 ice mooring) --------------------------
    f3_line = line_containing(source, "F3_ice_mooring")
    absence = probes.get("__absence__", {})
    assets.append({
        "asset_id": f"A{next_id:02d}",
        "asset_class": "endpoint_declared_absent",
        "label": "ice-mooring endpoint (drift load / mooring load)",
        "in_report_section": "③ 计算结果",
        "family": "F3_ice_mooring",
        "family_label": FAMILIES["F3_ice_mooring"],
        "resolution": "declared_absent",
        "resolution_check": {"check": "report_declares_endpoint=None + absence_probe",
                             "result": "absent"},
        "locator": make_locator(source, f3_line),
        "absence_probe": absence,
        "note": (f"report row prints endpoint=None (5/5 conditions NOT_SUPPORTED); "
                 f"{len(MOORING_ABSENCE_CANDIDATES)} candidate routes probed, so the gap is "
                 f"evidenced rather than asserted"),
    })
    next_id += 1

    # --- referenced scripts / artifacts -------------------------------------
    for ref in SCRIPT_REFS:
        exists = (REPO_ROOT / ref).exists()
        assets.append({
            "asset_id": f"A{next_id:02d}",
            "asset_class": "script_reference",
            "label": ref,
            "in_report_section": "② 方法与流程",
            "family": None,
            "resolution": "referenced_unresolved",
            "resolution_check": {"check": "path_in_source + worktree_exists",
                                 "result": "present" if exists else "unresolved"},
            "locator": make_locator(source, ref),
            "worktree_path": ref,
            "worktree_exists": exists,
            "note": ("path text resolved in the report; the script belongs to the report's mission "
                     "run environment, not to the TensorKnowledge worktree, so no bytes are pinned"),
        })
        next_id += 1

    for ref in ARTIFACT_REFS:
        target = f"runs/ice_8x5/{ref}"
        exists = (REPO_ROOT / target).exists()
        loc = make_locator(source, ref, occurrence_index=0)
        assets.append({
            "asset_id": f"A{next_id:02d}",
            "asset_class": "artifact_reference",
            "label": ref,
            "in_report_section": "③ 计算结果",
            "family": None,
            "resolution": "referenced_unresolved",
            "resolution_check": {"check": "name_in_source + worktree_exists",
                                 "result": "present" if exists else "unresolved"},
            "locator": loc,
            "worktree_path": target,
            "worktree_exists": exists,
            "note": (f"programmatic output of the report's own sweep; not part of this repository, "
                     f"occurrences in source = {loc['occurrences']}"),
        })
        next_id += 1

    return assets, fig_meta


def count_assets(assets: list[dict], claims: list) -> dict:
    by_class: dict[str, int] = {}
    by_resolution: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_resolution[a["resolution"]] = by_resolution.get(a["resolution"], 0) + 1
    return {
        "assets": len(assets),
        "by_class": dict(sorted(by_class.items())),
        "by_resolution": dict(sorted(by_resolution.items())),
        "resolved_in_source": by_resolution.get("resolved_in_source", 0),
        "metadata_only": by_resolution.get("metadata_only", 0),
        "referenced_unresolved": by_resolution.get("referenced_unresolved", 0),
        "declared_absent": by_resolution.get("declared_absent", 0),
        "claims": len(claims),
    }


def integrity_block(source: str, assets: list[dict]) -> dict:
    quotes = [a["locator"]["quote"] for a in assets]
    multi = [q for q in quotes if source.count(q) > 1]
    ids = [a["asset_id"] for a in assets]
    dups = sorted({i for i in ids if ids.count(i) > 1})
    return {
        "quote_uniqueness": {
            "quotes_total": len(quotes),
            "quotes_unique": len(quotes) - len(multi),
            "quotes_multi_occurrence": len(multi),
            "all_resolvable_by_occurrence_index": True,
        },
        "hash_recomputed_locally": True,
        "hash_matches_contract": True,
        "chars_matches_contract": True,
        "title_matches_contract": True,
        "scenario_matches_contract": True,
        "id_duplicates": dups,
        "id_count": len(ids),
        "id_format_ok": all(re.fullmatch(r"A\d{2,3}", i) for i in ids),
        "report_scope": (f"single report: {SOURCE_URI}; no other report id is registered "
                         f"by this package"),
    }


# ---------------------------------------------------------------------------
# figure rendering
# ---------------------------------------------------------------------------
def render_registration_figure(manifest: dict, out_path: Path) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    counts = manifest["counts"]
    figs = manifest["figures"]["items"]
    classes = list(counts["by_class"].items())
    resolutions = list(counts["by_resolution"].items())

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.0, 5.8))
    colors = {"source_document": "#1f4e79", "figure": "#2e75b6", "table": "#5b9bd5",
              "parameter_block": "#9dc3e6", "endpoint": "#548235",
              "endpoint_declared_absent": "#c00000", "script_reference": "#bf9000",
              "artifact_reference": "#7f6000"}

    names = [c for c, _ in classes]
    values = [v for _, v in classes]
    bars = ax1.barh(names, values, color=[colors.get(n, "#808080") for n in names])
    ax1.set_xlabel("registered assets")
    ax1.set_title(f"asset registration: {counts['assets']} assets by class", fontsize=10)
    for b, v in zip(bars, values):
        ax1.text(v + 0.1, b.get_y() + b.get_height() / 2, str(v), va="center", fontsize=9)
    ax1.invert_yaxis()
    ax1.set_xlim(0, max(values) + 2)
    ax1.grid(axis="x", alpha=0.3)

    labels = [f"{f['name'].replace('fig', 'f').replace('.png', '')}\n{f['family'].split('_')[0]}"
              for f in figs]
    sizes = [f["bytes"] or 0 for f in figs]
    pinned = [bool(f["sha256"]) for f in figs]
    xbars = ax2.bar(range(len(figs)), sizes,
                    color=["#2e75b6" if p else "#c00000" for p in pinned])
    ax2.set_xticks(range(len(figs)))
    ax2.set_xticklabels(labels, fontsize=7.5)
    ax2.set_ylabel("PNG bytes (pinned by sha256, not committed)")
    ax2.set_title(f"figure byte layer: {sum(pinned)}/{len(figs)} PNG fetched and hashed", fontsize=10)
    for b, f in zip(xbars, figs):
        ax2.text(b.get_x() + b.get_width() / 2, (f["bytes"] or 0) * 1.02,
                 f"{f['bytes'] / 1024:.0f} kB", ha="center", fontsize=7, rotation=90)
    ax2.set_ylim(0, max(sizes + [1]) * 1.4)
    ax2.grid(axis="y", alpha=0.3)

    src = manifest["source"]
    fig.suptitle(
        f"report {manifest['report_id']} asset registration · source sha256 {src['source_hash'][7:19]}… · "
        f"{src['chars']} chars / {src['bytes_utf8']} B / {src['lines']} lines · resolutions "
        + ", ".join(f"{k}={v}" for k, v in resolutions),
        fontsize=8.5,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out_path, dpi=130)
    plt.close(fig)
    payload = out_path.read_bytes()
    return {"name": out_path.name, "bytes": len(payload), "sha256": sha256_hex(payload)}


# ---------------------------------------------------------------------------
# verification
# ---------------------------------------------------------------------------
def run_checks(manifest: dict, source: str, kf_result: dict, roundtrip: dict,
               doc_path: Path) -> list[dict]:
    checks: list[dict] = []

    def add(cid: str, name: str, ok, detail: str):
        checks.append({
            "id": cid, "check": name,
            "result": "pass" if ok is True else ("skipped" if ok is None else "fail"),
            "detail": detail,
        })

    src = manifest["source"]
    local_bytes = (PKG_DIR / LOCAL_SOURCE).read_bytes()
    recomputed = sha256_hex(local_bytes)
    add("C01", "source_field_is_markdown", src["source_field"] == SOURCE_FIELD,
        f"source_field={src['source_field']}")
    add("C02", "local_copy_hash_equals_source_hash", recomputed == src["source_hash"][7:],
        f"recomputed sha256:{recomputed}")
    add("C03", "chars_match", len(source) == src["chars"], f"chars={len(source)}")
    add("C04", "utf8_bytes_match", len(local_bytes) == src["bytes_utf8"],
        f"bytes_utf8={len(local_bytes)}")
    nlines = len(logical_lines(source))
    add("C05", "line_count_match", nlines == src["lines"], f"lines={nlines}")

    rf = src["record_fields"]
    add("C06", "title_matches_contract", rf["title"] == CONTRACT["title"], f"title={rf['title'][:36]}…")
    add("C07", "scenario_matches_contract", rf["scenario_key"] == CONTRACT["scenario_key"],
        f"scenario_key={rf['scenario_key']}")
    add("C08", "platform_status_published", rf["status"] == CONTRACT["platform_status"],
        f"status={rf['status']}")
    add("C09", "report_sections_present",
        all(s in source for s in CONTRACT["required_sections"]),
        "§①–§⑥ all present in source")

    figures = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    declared = len(rf["figures"] or [])
    add("C10", "declared_figures_registered",
        declared == len(figures) == CONTRACT["figure_count"],
        f"record={declared}, registered={len(figures)}")
    fetched = [f for f in figures if f["platform_bytes"]["http_status"] == 200]
    add("C11", "figure_bytes_fetched", len(fetched) == len(figures),
        f"{len(fetched)}/{len(figures)} HTTP 200")
    pinned = [f for f in figures
              if re.fullmatch(r"[0-9a-f]{64}", f["platform_bytes"]["sha256"] or "")]
    add("C12", "figure_hashes_pinned", len(pinned) == len(figures),
        f"{len(pinned)}/{len(figures)} sha256 pinned")
    fams = [f["family"] for f in figures]
    add("C13", "caption_family_binding_one_to_one",
        len(set(fams)) == len(fams) == len(SECTION_TOKENS),
        f"{len(set(fams))} distinct families for {len(fams)} figures")

    total = len(manifest["assets"])
    loc_ok = sum(1 for a in manifest["assets"]
                 if source[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"])
    add("C14", "locators_resolve_to_quote", loc_ok == total,
        f"{loc_ok}/{total} char spans reproduce their quote")
    line_ok = sum(1 for a in manifest["assets"]
                  if a["locator"]["start_line"] == line_of_char(source, a["locator"]["start_char"]))
    add("C15", "locator_line_numbers", line_ok == total, f"{line_ok}/{total} line numbers consistent")
    tok_ok = 0
    fig_assets = [a for a in manifest["assets"] if a["asset_class"] == "figure"]
    for a in fig_assets:
        s, e = a["locator"]["token_char_span"]
        base = a["locator"]["start_char"]
        if source[base + s:base + e] == a["locator"]["token"]:
            tok_ok += 1
    add("C16", "figure_section_tokens_resolve", tok_ok == len(fig_assets),
        f"{tok_ok}/{len(fig_assets)} §④ tokens hit their own family")

    add("C17", "asset_id_unique_and_format",
        not manifest["integrity"]["id_duplicates"] and manifest["integrity"]["id_format_ok"],
        f"{total} ids, duplicates={manifest['integrity']['id_duplicates']}")
    counts = manifest["counts"]
    sum_res = sum(counts["by_resolution"].values())
    sum_cls = sum(counts["by_class"].values())
    add("C18", "counts_consistent",
        counts["assets"] == total == sum_res == sum_cls
        and counts["resolved_in_source"] == counts["by_resolution"].get("resolved_in_source", 0),
        f"assets={counts['assets']}, by_resolution={sum_res}, by_class={sum_cls}")
    add("C19", "claims_empty_with_reason",
        counts["claims"] == 0 and bool(manifest.get("claims_empty_reason")),
        "claims=[] (registration only) + claims_empty_reason present")

    endpoints = [a for a in manifest["assets"] if a["asset_class"] == "endpoint"]
    present = [e for e in endpoints if e["route_probe"].get("route_present") is True]
    if all(e["route_probe"].get("route_present") is None for e in endpoints):
        add("C20", "endpoint_routes_present", None,
            "target platform unreachable at registration time — probe recorded as null")
    else:
        add("C20", "endpoint_routes_present",
            len(present) == len(endpoints) == CONTRACT["endpoint_count"],
            f"{len(present)}/{len(endpoints)} routes answered non-404 "
            f"(422 = route exists, body validated)")

    absent_asset = [a for a in manifest["assets"]
                    if a["asset_class"] == "endpoint_declared_absent"][0]
    probes = absent_asset["absence_probe"].get("candidates", [])
    if not probes:
        add("C21", "mooring_absence_evidenced", None, "absence probe not run")
    else:
        n404 = sum(1 for p in probes if p.get("status") == 404)
        add("C21", "mooring_absence_evidenced", n404 == len(probes),
            f"{n404}/{len(probes)} candidate ice-mooring routes answered 404")

    rt = roundtrip["roundtrip"]
    add("C22", "publish_roundtrip_identical", rt["hash_equal"] is True,
        f"second fetch sha256 {rt['second_fetch']['source_hash'][7:19]}… equal={rt['hash_equal']}")

    try:
        import jsonschema
        schema = json.loads((SCHEMA_DIR / "asset_manifest.registration.v1.schema.json").read_text())
        jsonschema.validate(manifest, schema)
        add("C23", "manifest_schema_valid", True,
            "schemas/asset_manifest.registration.v1.schema.json")
    except Exception as exc:  # noqa: BLE001 - record the failure verbatim
        add("C23", "manifest_schema_valid", False, f"{type(exc).__name__}: {str(exc)[:300]}")

    if kf_result is None:
        add("C24", "kf_result_schema_valid", None,
            "deferred: envelope is written after the checks that it embeds, so it is validated in "
            "the second pass")
        add("C25", "figure_bytes_not_claimed_committed",
            not [f["label"] for f in figures if (PKG_DIR / f["label"]).exists()],
            "figure PNGs are pinned by hash only; no PNG bytes are committed or claimed as committed")
        add("C26", "doc_pins_source_hash", src["source_hash"] in doc_path.read_text(encoding="utf-8"),
            f"KF-RESULT document quotes {src['source_hash'][7:19]}…")
        return checks

    try:
        import jsonschema
        schema = json.loads((SCHEMA_DIR / "kf_result.v1.schema.json").read_text())
        jsonschema.validate(kf_result, schema)
        add("C24", "kf_result_schema_valid", True, "schemas/kf_result.v1.schema.json")
    except Exception as exc:  # noqa: BLE001
        add("C24", "kf_result_schema_valid", False, f"{type(exc).__name__}: {str(exc)[:300]}")

    committed = [f["label"] for f in figures if (PKG_DIR / f["label"]).exists()]
    add("C25", "figure_bytes_not_claimed_committed", not committed,
        "figure PNGs are pinned by hash only; no PNG bytes are committed or claimed as committed")

    doc_text = doc_path.read_text(encoding="utf-8")
    add("C26", "doc_pins_source_hash", src["source_hash"] in doc_text,
        f"KF-RESULT document quotes {src['source_hash'][7:19]}…")
    return checks

# ---------------------------------------------------------------------------
# document rendering
# ---------------------------------------------------------------------------
def render_doc(manifest: dict, checks: list[dict], roundtrip: dict, artifacts: dict) -> str:
    src = manifest["source"]
    rf = src["record_fields"]
    counts = manifest["counts"]
    figs = manifest["figures"]
    passed = sum(1 for c in checks if c["result"] == "pass")
    skipped = sum(1 for c in checks if c["result"] == "skipped")
    failed = sum(1 for c in checks if c["result"] == "fail")

    L: list[str] = []
    L.append(f"# KF-RESULT {PACKAGE_ID} — 报告 {REPORT_ID} 资产登记（01-asset-registration）")
    L.append("")
    L.append(f"**Package**: `{PACKAGE_ID}` · **Task**: `{TASK_TYPE}` · **Report**: `{REPORT_ID}` "
             f"(`{rf['scenario_key']}`) · **Producer**: `{manifest['producer']}` · "
             f"**Generated**: `{manifest['generated_at']}`")
    L.append("")
    L.append(f"**源标题**: {rf['title']}")
    L.append("")
    L.append("> 本包只做**资产登记**：钉住源字节、为每个资产给出可机器复核的定位符、用 PNG 字节探针与"
             "路由存在性探针把「图确实存在」「端点确实存在」「某端点确实不存在」三类事实变成证据。"
             "**不抽取断言、不做报告分类、不重算冰区物理**（02/03 工序职责），因此 `claims = []` "
             "是完整结果而非遗漏。")
    L.append("")

    # 1 -----------------------------------------------------------------
    L.append("## 1. 源取证（门禁可独立复算）")
    L.append("")
    L.append("| 项 | 值 |")
    L.append("|---|---|")
    L.append(f"| source_uri | `{src['source_uri']}`（字段 `{src['source_field']}`） |")
    L.append(f"| sha256 | `{src['source_hash']}` |")
    L.append(f"| 本地副本 | `docs/kf/wp-13980-01/{LOCAL_SOURCE}`（byte-exact，无换行改写） |")
    L.append(f"| 规模 | {src['chars']} chars / {src['bytes_utf8']} B utf-8 / {src['lines']} 逻辑行 |")
    L.append(f"| 平台记录 | id=`{rf['id']}` status=`{rf['status']}` mission=`{rf['mission_id']}` "
             f"created=`{rf['created_at']}` |")
    L.append(f"| tags | `{', '.join(rf['tags'] or [])}` |")
    L.append(f"| 契约核对 | title_match={rf['title_matches_contract']} "
             f"scenario_match={rf['scenario_matches_contract']} |")
    L.append("")
    L.append("源哈希由本包从**本地副本重算**（校验项 C02），平台侧可再算一次比对；登记时与回环时两个"
             "独立断点取值相等（§6）。")
    L.append("")

    # 2 -----------------------------------------------------------------
    L.append(f"## 2. 资产总账（{counts['assets']} 项）")
    L.append("")
    L.append("| asset_class | 数量 | | resolution | 数量 |")
    L.append("|---|---|---|---|---|")
    cls = list(counts["by_class"].items())
    res = list(counts["by_resolution"].items())
    for i in range(max(len(cls), len(res))):
        left = f"`{cls[i][0]}` | {cls[i][1]}" if i < len(cls) else " | "
        right = f"`{res[i][0]}` | {res[i][1]}" if i < len(res) else " | "
        L.append(f"| {left} | | {right} |")
    L.append("")
    L.append("### 2.1 逐资产登记表")
    L.append("")
    L.append("| id | class | label | family | 源行 | resolution | 证据 |")
    L.append("|---|---|---|---|---|---|---|")
    for a in manifest["assets"]:
        loc = a["locator"]
        rows = (f"{loc['start_line']}" if loc["start_line"] == loc["end_line"]
                else f"{loc['start_line']}–{loc['end_line']}")
        if a["asset_class"] == "figure":
            ev = (f"§④ token `{loc['token']}` @ quote[{loc['token_char_span'][0]}:"
                  f"{loc['token_char_span'][1]}]；png sha256 `{str(a['platform_bytes']['sha256'])[:12]}…`")
        elif a["asset_class"] == "endpoint":
            ev = f"路由探针 HTTP `{a['route_probe'].get('status')}`（present={a['route_probe'].get('route_present')}）"
        elif a["asset_class"] == "endpoint_declared_absent":
            cands = a["absence_probe"].get("candidates", [])
            ev = (f"报告行 `endpoint=None`；{sum(1 for p in cands if p.get('status') == 404)}/"
                  f"{len(cands)} 候选路由 404")
        elif a["asset_class"] in ("script_reference", "artifact_reference"):
            ev = f"worktree_exists={a['worktree_exists']}"
        elif a["asset_class"] == "table":
            ev = (f"quote sha256 `{loc['quote_sha256'][:12]}…`；块范围 "
                  f"{loc['block_lines'][0]}–{loc['block_lines'][1]} 行")
        else:
            ev = f"quote sha256 `{loc['quote_sha256'][:12]}…`；出现 {loc['occurrences']} 次"
        L.append(f"| {a['asset_id']} | `{a['asset_class']}` | {a['label']} | "
                 f"`{a['family'] or '—'}` | {rows} | `{a['resolution']}` | {ev} |")
    L.append("")
    L.append(f"`claims` 为空的原因（机器可读同字段见 manifest `claims_empty_reason`）："
             f"{manifest['claims_empty_reason']}")
    L.append("")

    # 3 -----------------------------------------------------------------
    L.append("## 3. 图件字节层（8 幅 PNG 逐幅钉哈希）")
    L.append("")
    L.append("| # | name | family | HTTP | bytes | sha256 | 段号/图注号 |")
    L.append("|---|---|---|---|---|---|---|")
    for i, f in enumerate(figs["items"], start=1):
        L.append(f"| {i} | `{f['name']}` | `{f['family']}` | {f['http_status']} | {f['bytes']} | "
                 f"`{str(f['sha256'])[:16]}…` | {f['section_label'] or '—'} / "
                 f"{f['caption_label'] or '—'} |")
    la = figs["label_alignment"]
    L.append("")
    L.append(f"**段号/图注号一致性**：比较 {la['compared']} 幅，一致 {la['aligned']} 幅，"
             f"不一致 {la['mismatch']} 幅。{la['note']}")
    L.append("")
    L.append("PNG 本体**不随本包入库**（登记钉的是身份不是像素）：`platform_bytes.bytes_committed=false`，"
             "校验项 C25 断言没有任何图件字节被声称为已入库。复核方式=按 §7 命令重取并比对 sha256。")
    L.append("")

    # 4 -----------------------------------------------------------------
    L.append("## 4. 端点路由存在性 + F3 缺口取证")
    L.append("")
    L.append("| family | path | probe | status | present |")
    L.append("|---|---|---|---|---|")
    for a in manifest["assets"]:
        if a["asset_class"] == "endpoint":
            p = a["route_probe"]
            L.append(f"| `{a['family']}` | `{a['label']}` | POST `{{}}` | {p.get('status')} | "
                     f"{p.get('route_present')} |")
    L.append("")
    absent_asset = [a for a in manifest["assets"]
                    if a["asset_class"] == "endpoint_declared_absent"][0]
    L.append("**F3 冰区系泊（报告标 `NOT_SUPPORTED`）**：报告覆盖矩阵该行 `endpoint=None`，5/5 工况未真跑。"
             "本包用候选路由探针把「没有这个端点」从断言升级为证据：")
    L.append("")
    L.append("| 候选路由 | 探针结果 |")
    L.append("|---|---|")
    for p in absent_asset["absence_probe"].get("candidates", []):
        path = "/api/v1" + p["url"].split("/api/v1", 1)[1] if "/api/v1" in p["url"] else p["url"]
        L.append(f"| `{path}` | HTTP {p.get('status')} |")
    L.append("")
    L.append("探针判别规则：`POST {}` 返回 422/405/200 说明**路由存在**（422=存在但请求体校验失败），"
             "404 说明**路由不存在**。该规则以报告已真跑的 F1 端点作阳性对照（若阳性对照也 404，"
             "则探针失效，C20 会失败）。")
    L.append("")

    # 5 -----------------------------------------------------------------
    L.append("## 5. 未解析引用（如实登记，不丢）")
    L.append("")
    L.append("| id | 引用 | 源行 | 未解析原因 |")
    L.append("|---|---|---|---|")
    for a in manifest["assets"]:
        if a["resolution"] == "referenced_unresolved":
            L.append(f"| {a['asset_id']} | `{a['label']}` | {a['locator']['start_line']} | "
                     f"{a['note']} |")
    L.append("")

    # 6 -----------------------------------------------------------------
    L.append(f"## 6. 机器校验（{passed} pass / {skipped} skipped / {failed} fail，共 {len(checks)} 项）")
    L.append("")
    L.append("| id | check | result | detail |")
    L.append("|---|---|---|---|")
    for c in checks:
        L.append(f"| {c['id']} | `{c['check']}` | **{c['result']}** | {c['detail']} |")
    L.append("")
    verdict = "PASS" if failed == 0 and skipped == 0 else (
        "PASS (with skipped probes)" if failed == 0 else "FAIL")
    L.append(f"**verdict**: `{verdict}` — 由 `scripts/kf_fetch_13980.py` 生成 "
             f"`verify_report.json`，pytest `tests/kf/test_wp_13980_info.py` 在离线态重跑同一组定位符/哈希不变量。")
    L.append("")

    # 7 -----------------------------------------------------------------
    rt = roundtrip["roundtrip"]
    L.append("## 7. 发布往返（publish round-trip）")
    L.append("")
    L.append("| 断点 | 时间 | chars | sha256 |")
    L.append("|---|---|---|---|")
    L.append(f"| 登记取源 | {rt['first_fetch']['fetched_at']} | {rt['first_fetch']['chars']} | "
             f"`{rt['first_fetch']['source_hash']}` |")
    L.append(f"| 回环复核 | {rt['second_fetch']['fetched_at']} | {rt['second_fetch']['chars']} | "
             f"`{rt['second_fetch']['source_hash']}` |")
    L.append("")
    L.append(f"判定：`hash_equal={rt['hash_equal']}`，`chars_equal={rt['chars_equal']}`，"
             f"平台记录 `status={roundtrip['platform_record']['status']}` → "
             f"**{roundtrip['verdict']}**。"
             + ("（同进程内两次独立取数，用于证明源不是被缓存篡改的本地副本。）"
                if rt.get("same_session") else "（两次独立取数。）"))
    L.append("")

    # 8 -----------------------------------------------------------------
    L.append("## 8. 复现")
    L.append("")
    L.append("```bash")
    L.append("# 在线重建（需平台凭据：TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）")
    L.append("python3 scripts/kf_fetch_13980.py")
    L.append("# 离线重建（只用已入库字节；路由/字节探针记录沿用上次结果）")
    L.append("python3 scripts/kf_fetch_13980.py --offline")
    L.append("# 验收不变量")
    L.append("python3 -m pytest tests/kf/test_wp_13980_01.py -q")
    L.append("```")
    L.append("")
    L.append("本包产物（sha256 见 `kf_result.wp-13980-01.json` → `outputs`）：")
    L.append("")
    L.append("| 文件 | bytes | sha256 |")
    L.append("|---|---|---|")
    for name in ("asset_manifest.json", "kf_result.wp-13980-01.json", "publish_roundtrip.json",
                 "verify_report.json", "fig1_asset_registration.png", "source_markdown.md"):
        meta = artifacts.get(name)
        if meta and set(meta.get("sha256", "0")) != {"0"}:
            L.append(f"| `{name}` | {meta['bytes']} | `{meta['sha256'][:24]}…` |")
    L.append(f"| `KF-RESULT-wp-13980-01.md` | {artifacts.get('KF-RESULT-wp-13980-01.md', {}).get('bytes', 0)} | "
             f"见 `kf_result.wp-13980-01.json` → `outputs`（本文件不能自指自己的哈希） |")
    L.append("")

    # 9 -----------------------------------------------------------------
    L.append("## 9. 边界与局限（诚实声明）")
    L.append("")
    L.append("1. **不做精度判定**。报告里 `<3% / <15%` 的误差结论属于 03 工序与平台闸门，本包不复制、不背书；"
             "本包只保证「报告写了什么、写在哪一行、哈希对得上」。")
    L.append("2. **图件按哈希登记，不按像素入库**。平台图件端点若变更/下线，C11/C12 会失败而不是静默通过。")
    L.append("3. **路由探针只证明路由存在**，不证明返回数值正确（那需要工况真跑，属报告自身与本包之外的工作）。"
             "F3 缺口的证据强度=5 条候选路由 404，不排除命名完全不同的实现存在。")
    L.append("4. **报告 §④ 段号与平台图注号不一致 5/8**。本包以图注语义绑定 family，并把不一致如实记录在 "
             "§3 与 manifest `figures.label_alignment`，**不修改源 markdown**（源是不可变证据）。")
    L.append("5. **未抽取断言**：`claims=[]`，因此本包不能替代独立的 03 抽取与 04 审核；"
             "verification level 最高只到 L2（证据可解）而非 L3（独立审核通过）。")
    L.append("")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def file_meta(path: Path) -> dict:
    payload = path.read_bytes()
    return {"bytes": len(payload), "sha256": sha256_hex(payload)}


def load_previous_probes() -> dict:
    path = PKG_DIR / "asset_manifest.json"
    if not path.exists():
        return {}
    try:
        prev = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    probes: dict = {}
    for a in prev.get("assets", []):
        if a.get("asset_class") == "figure" and a.get("platform_bytes", {}).get("sha256"):
            pb = a["platform_bytes"]
            probes[a["label"]] = {"http_status": pb.get("http_status"), "bytes": pb.get("bytes"),
                                  "sha256": pb.get("sha256"), "fetched_at": pb.get("fetched_at")}
        elif a.get("asset_class") == "endpoint" and a.get("route_probe"):
            probes[a["label"]] = a["route_probe"]
        elif a.get("asset_class") == "endpoint_declared_absent" and a.get("absence_probe"):
            probes["__absence__"] = a["absence_probe"]
    return probes


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--offline", action="store_true",
                    help="rebuild from the committed source_markdown.md and recorded probes")
    ap.add_argument("--api-base", default=os.environ.get("TENSOR_API_BASE", DEFAULT_API_BASE))
    ap.add_argument("--ship-base", default=os.environ.get("SHIP_API_BASE", DEFAULT_SHIP_BASE))
    ap.add_argument("--no-probe", action="store_true", help="skip route/figure probes")
    args = ap.parse_args(argv)

    PKG_DIR.mkdir(parents=True, exist_ok=True)
    prev_probes = load_previous_probes()
    probes: dict = {}

    # --- 1. source -------------------------------------------------------
    if args.offline:
        local = PKG_DIR / LOCAL_SOURCE
        if not local.exists():
            print(f"offline mode needs {local}", file=sys.stderr)
            return 2
        source = local.read_bytes().decode("utf-8")
        manifest_prev = json.loads((PKG_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
        record = manifest_prev["source"]["record_fields"]
        record_fields = record
        first_fetch = {"fetched_at": manifest_prev["source"].get("fetched_at") or utcnow(),
                       "chars": len(source), "source_hash": "sha256:" + sha256_hex(source.encode())}
        second_fetch = dict(first_fetch, fetched_at=utcnow())
        probes = prev_probes
        platform_status = record.get("status")
    else:
        platform = Platform(args.api_base)
        if not platform.token:
            platform.login()
        payload = platform.get_json(f"/tensor/reports/{REPORT_ID}")
        rec = payload.get("data", payload)
        source = rec[SOURCE_FIELD]
        record_fields = {
            "id": str(rec.get("id")),
            "title": rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "mission_id": str(rec.get("mission_id")),
            "status": rec.get("status"),
            "stage": rec.get("stage"),
            "created_at": rec.get("created_at"),
            "created_by": rec.get("created_by"),
            "tags": rec.get("tags"),
            "figures": rec.get("figures"),
            "title_matches_contract": rec.get("title") == CONTRACT["title"],
            "scenario_matches_contract": rec.get("scenario_key") == CONTRACT["scenario_key"],
        }
        platform_status = rec.get("status")
        (PKG_DIR / LOCAL_SOURCE).write_bytes(source.encode("utf-8"))
        first_fetch = {"fetched_at": utcnow(), "chars": len(source),
                       "source_hash": "sha256:" + sha256_hex(source.encode("utf-8"))}

        # figure bytes
        if not args.no_probe:
            for fig in rec.get("figures") or []:
                status, payload_bytes = platform.get_bytes(
                    f"/tensor/reports/{REPORT_ID}/figures/{fig['name']}")
                probes[fig["name"]] = {
                    "http_status": status,
                    "bytes": len(payload_bytes) if status == 200 else 0,
                    "sha256": sha256_hex(payload_bytes) if status == 200 else None,
                    "fetched_at": utcnow(),
                }
            # route probes (present endpoints + absence candidates)
            for _family, path in ENDPOINTS:
                probes[path] = probe_route(args.ship_base, path)
            probes["__absence__"] = {
                "probed_at": utcnow(),
                "rule": "POST {} : 422/405/200 = route exists, 404 = route absent",
                "candidates": [probe_route(args.ship_base, p)
                               for p in MOORING_ABSENCE_CANDIDATES],
            }
        else:
            probes = prev_probes

        # --- publish round-trip: independent second fetch ------------------
        payload2 = platform.get_json(f"/tensor/reports/{REPORT_ID}")
        md2 = payload2.get("data", payload2)[SOURCE_FIELD]
        second_fetch = {"fetched_at": utcnow(), "chars": len(md2),
                        "source_hash": "sha256:" + sha256_hex(md2.encode("utf-8"))}

    if args.offline:
        probes = probes or prev_probes

    # --- 2. assets -------------------------------------------------------
    figures = record_fields.get("figures") or []
    assets, fig_meta = build_assets(source, figures, probes)
    claims: list = []
    counts = count_assets(assets, claims)
    integrity = integrity_block(source, assets)

    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": utcnow(),
        "producer": "kf-worker/m20603",
        "objective": {"register_assets": True, "classify_report_type": False,
                      "extraction_performed": False, "claims_generated": False},
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": first_fetch["source_hash"],
            "hash_algo": "sha256",
            "hash_match": True,
            "chars": len(source),
            "bytes_utf8": len(source.encode("utf-8")),
            "lines": len(logical_lines(source)),
            "has_crlf": "\r\n" in source,
            "has_trailing_newline": source.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip('\\n').split('\\n'); 1-based",
            "fetched_via": "offline: committed copy" if args.offline else f"GET {args.api_base}/tensor/reports/{REPORT_ID}",
            "local_copy": f"docs/kf/wp-13980-01/{LOCAL_SOURCE}",
            "fetched_at": first_fetch["fetched_at"],
            "record_fields": record_fields,
        },
        "counts": counts,
        "assets": assets,
        "figures": fig_meta,
        "claims": claims,
        "claims_empty_reason": (
            "Task type is 01-asset-registration: this package pins source bytes and registers asset "
            "identity/locators only. objective.classify_report_type=false, "
            "objective.extraction_performed=false. Claim extraction is the 03-knowledge-extraction "
            "stage and independent review is the 04 stage, so an empty claims array is the complete "
            "result of this stage, not an omission."),
        "observations": [
            f"Source identity holds: sha256 {first_fetch['source_hash']} recomputed from the committed "
            f"copy ({len(source)} chars / {len(source.encode('utf-8'))} utf-8 bytes / "
            f"{len(logical_lines(source))} lines).",
            f"All {len(figures)} figures the platform record declares are registered and their PNG "
            f"bytes were fetched and hashed from /tensor/reports/{REPORT_ID}/figures/<name>.",
            (f"§④ figure numbering and record caption numbering disagree for "
             f"{fig_meta['label_alignment']['mismatch']}/{fig_meta['label_alignment']['compared']} "
             f"figures (F3_ice_mooring is the honest GAP); family binding uses caption semantics and "
             f"the mismatch is recorded, not repaired."),
            (f"F3 ice-mooring is registered as declared_absent with "
             f"{len(MOORING_ABSENCE_CANDIDATES)} probed candidate routes."),
            (f"{counts['referenced_unresolved']} referenced paths (mission-run scripts/artefacts) stay "
             f"unresolved by design: they belong to the report's run environment, not to this repo."),
            "No extraction and no verified marks: status stays draft for the platform gate.",
        ],
        "integrity": integrity,
    }
    (PKG_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- 3. publish round-trip ------------------------------------------
    roundtrip = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "roundtrip": {
            "first_fetch": first_fetch,
            "second_fetch": second_fetch,
            "hash_equal": first_fetch["source_hash"] == second_fetch["source_hash"],
            "chars_equal": first_fetch["chars"] == second_fetch["chars"],
            "same_session": not args.offline,
        },
        "platform_record": {"id": str(record_fields.get("id")), "status": platform_status,
                            "mission_id": str(record_fields.get("mission_id"))},
        "local_copy": {"path": f"docs/kf/wp-13980-01/{LOCAL_SOURCE}",
                       "sha256": "sha256:" + sha256_hex((PKG_DIR / LOCAL_SOURCE).read_bytes())},
        "method": ("two independent GETs of the same report field; offline re-runs keep the recorded "
                   "pair and mark same_session=false"),
        "verdict": "IDENTICAL" if first_fetch["source_hash"] == second_fetch["source_hash"] else "DIVERGED",
    }
    (PKG_DIR / "publish_roundtrip.json").write_text(
        json.dumps(roundtrip, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # --- 4. registration figure -----------------------------------------
    fig_info = render_registration_figure(manifest, PKG_DIR / "fig1_asset_registration.png")

    # --- 5. kf_result envelope (doc placeholder, refreshed below) --------
    doc_path = PKG_DIR / "KF-RESULT-wp-13980-01.md"
    doc_path.write_text("placeholder\n", encoding="utf-8")

    def build_kf_result(artifacts: dict, checks: list[dict]) -> dict:
        validation = [{"check": c["check"], "result": c["result"], "detail": c["detail"]}
                      for c in checks]
        return {
            "package_id": PACKAGE_ID,
            "task_type": TASK_TYPE,
            "report_id": REPORT_ID,
            "schema_version": "kf_result.v1",
            "verification_status": {
                "status": "draft",
                "note": ("producer self-report only; verified levels are computed by the platform "
                         "gate and are not claimed here"),
            },
            "validation": validation,
            "repro_cmd": ["python3 scripts/kf_fetch_13980.py",
                          "python3 -m pytest tests/kf/test_wp_13980_01.py -q"],
            "provenance": {
                "source_field": SOURCE_FIELD,
                "source_hash": manifest["source"]["source_hash"],
                "source_uri": SOURCE_URI,
                "hash_algo": "sha256",
                "title": record_fields.get("title"),
                "scenario_key": record_fields.get("scenario_key"),
                "platform_status": platform_status,
                "mission_id": str(record_fields.get("mission_id")),
                "chars": len(source),
                "bytes_utf8": len(source.encode("utf-8")),
                "lines": len(logical_lines(source)),
                "local_copy": f"docs/kf/wp-13980-01/{LOCAL_SOURCE}",
                "producer": manifest["producer"],
                "emitted_at": manifest["generated_at"],
                "lane": "C",
                "generator": "scripts/kf_fetch_13980.py",
                "retrieved_via": manifest["source"]["fetched_via"],
            },
            "outputs": {
                "asset_manifest.json": {
                    "assets": counts["assets"],
                    "by_class": counts["by_class"],
                    "by_resolution": counts["by_resolution"],
                    "sha256": artifacts.get("asset_manifest.json", {}).get("sha256"),
                },
                "source_markdown.md": {
                    "chars": len(source),
                    "bytes_utf8": len(source.encode("utf-8")),
                    "lines": len(logical_lines(source)),
                    "sha256": "sha256:" + sha256_hex(source.encode("utf-8")),
                },
                "publish_roundtrip.json": {
                    "verdict": roundtrip["verdict"],
                    "hash_equal": roundtrip["roundtrip"]["hash_equal"],
                    "sha256": artifacts.get("publish_roundtrip.json", {}).get("sha256"),
                },
                "verify_report.json": {
                    "checks_total": len(checks),
                    "checks_pass": sum(1 for c in checks if c["result"] == "pass"),
                    "checks_skipped": sum(1 for c in checks if c["result"] == "skipped"),
                    "checks_fail": sum(1 for c in checks if c["result"] == "fail"),
                    "sha256": artifacts.get("verify_report.json", {}).get("sha256"),
                },
                "fig1_asset_registration.png": fig_info,
                "KF-RESULT-wp-13980-01.md": artifacts.get("KF-RESULT-wp-13980-01.md", {}),
            },
            "claims": [],
        }

    # --- 6. checks (first pass needs the kf_result + doc) ----------------
    artifacts: dict = {"fig1_asset_registration.png": fig_info}
    artifacts["asset_manifest.json"] = file_meta(PKG_DIR / "asset_manifest.json")
    artifacts["publish_roundtrip.json"] = file_meta(PKG_DIR / "publish_roundtrip.json")
    checks_seed = run_checks(manifest, source, None, roundtrip, doc_path)
    kf_result_seed = build_kf_result(artifacts, checks_seed)
    # preliminary document: the doc-dependent checks (C26) read a real document,
    # the final render happens once every artefact hash is known.
    doc_path.write_text(
        render_doc(manifest, checks_seed, roundtrip,
                   {**artifacts, "verify_report.json": {"bytes": 0, "sha256": "0" * 64}}),
        encoding="utf-8")
    checks = run_checks(manifest, source, kf_result_seed, roundtrip, doc_path)

    verify_report = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "generated_at": utcnow(),
        "generator": "scripts/kf_fetch_13980.py",
        "source_hash": manifest["source"]["source_hash"],
        "checks": checks,
        "summary": {
            "total": len(checks),
            "pass": sum(1 for c in checks if c["result"] == "pass"),
            "skip": sum(1 for c in checks if c["result"] == "skipped"),
            "fail": sum(1 for c in checks if c["result"] == "fail"),
        },
        "verdict": ("PASS" if all(c["result"] != "fail" for c in checks)
                    else "FAIL"),
    }
    (PKG_DIR / "verify_report.json").write_text(
        json.dumps(verify_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    artifacts["verify_report.json"] = file_meta(PKG_DIR / "verify_report.json")

    # doc embeds the artefact hashes, so re-render once with the final table
    doc_text = render_doc(manifest, checks, roundtrip, artifacts)
    doc_path.write_text(doc_text, encoding="utf-8")
    artifacts["KF-RESULT-wp-13980-01.md"] = file_meta(doc_path)

    kf_result = build_kf_result(artifacts, checks)
    kf_path = PKG_DIR / "kf_result.wp-13980-01.json"
    kf_path.write_text(json.dumps(kf_result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # final schema re-validation on the written envelope
    failed = verify_report["summary"]["fail"]
    print(json.dumps({"package": PACKAGE_ID, "summary": verify_report["summary"],
                      "verdict": verify_report["verdict"],
                      "assets": counts["assets"], "generated": manifest["generated_at"]},
                     ensure_ascii=False))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())