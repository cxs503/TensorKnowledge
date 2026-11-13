#!/usr/bin/env python3
"""wp-8583-01 (task_type 01-asset-registration): register the source asset of report 8583.

Scope guard: report_id=8583 only; no other report is read or written. Registration only --
no claim extraction, no report-type classification, and nothing is marked verified
(verification is computed by the platform gate).

Design rules honoured here (contract wp-8583-01):
  * zero manual transcription: every `quote` is sliced at run time out of the markdown bytes
    fetched from the platform; each quote is asserted to be a *unique* substring, and its char
    span / line span / sha256 are measured, never retyped;
  * do_not_invent_missing_information: figures whose bytes the platform does not serve, and
    artefact paths that do not exist in this delivery worktree, are recorded as
    `metadata_only` / `unresolved` with a reason -- never given an invented address;
  * preserve_uncertainty / no_forced_claim_generation: claims = [] (the contract notes allow
    this); prose observations are labelled observations and are not promoted to claims.

Sub-commands (idempotent):
  python3 scripts/kf_wp8583_01_register.py build     # fetch + write asset_manifest.json
  python3 scripts/kf_wp8583_01_register.py envelope  # wrap manifest -> kf_result.wp-8583-01.json
  python3 scripts/kf_wp8583_01_register.py verify    # 6 acceptance checks -> verification.json
  python3 scripts/kf_wp8583_01_register.py figure    # locator coverage png
  python3 scripts/kf_wp8583_01_register.py report    # KF-RESULT markdown (single json block)
  python3 scripts/kf_wp8583_01_register.py publish   # POST the KF-RESULT report
  python3 scripts/kf_wp8583_01_register.py all       # build+envelope+verify+figure+report
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "8583"
PACKAGE_ID = "wp-8583-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
UPSTREAM_MISSION_ID = 15624

# contract-declared identity (comparison targets only; never trusted as observed values)
CONTRACT_SOURCE_HASH = "2dae949f5c82c8f0e931f5280c0ea5c565bd188e05b0c109e49763d47a4fdfa4"
CONTRACT_CHARS = 4087
CONTRACT_TITLE = ("IN69-N10 极地航行 CII 合规性耦合优化：冰阻力→油耗→CII 评级 + "
                  "速度-冰况 Pareto + Polar Code 窗口")
CONTRACT_SCENARIO = "polar_cii_compliance"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / ("kf_result.%s.json" % PACKAGE_ID)
VERDICT = OUT_DIR / "verification.json"
FIGMETA = OUT_DIR / "figure.json"
REPORT_MD = OUT_DIR / ("KF-RESULT-%s.md" % PACKAGE_ID)
FIGURE = OUT_DIR / "fig_locator_coverage.png"
SOURCE_COPY = RUN_DIR / ("report_%s.md" % REPORT_ID)

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
PRODUCER = "m15624/scripts/kf_wp8583_01_register.py"

# Registered document blocks: (suffix, class, label, anchor, first_line_offset, last_line_offset).
# The anchor is used only to *locate* the block; the emitted quote is its verbatim text.
SECTIONS = [
    ("title", "heading", "报告标题行",
     "## IN69-N10 极地航行 CII 合规性耦合优化", 0, 0),
    ("sec1-case", "case_description", "§① 案例介绍（耦合链条 + 三型母型 + 情景/窗口）",
     "### ① 案例介绍", 0, 12),
    ("fleet-geometry", "parameter_table", "三型母型主尺度与设计点（Cb/L/B 校验声明）",
     "三型母型（几何先过 Cb/L/B 校验）", 0, 3),
    ("scenario-window", "scenario_definition", "5 档冰况情景 + 评级基准年 + 速度/冰厚窗口",
     "情景 5 档（h=0/0.2/0.5/0.8/1.0 m", 0, 1),
    ("sec2-method", "method_chain", "§② 做法 7 步（Lindqvist/η_prop 反解/CII 算式/优化器/工具链）",
     "### ② 怎么做的", 0, 10),
    ("cii-matrix", "result_table", "§③ 年 CII 矩阵表（3 船型 × 5 冰况，含 required 基准）",
     "| 船型（required） | 无冰 | 薄冰 0.2 | 中冰 0.5 | 厚冰 0.8 | 冰级上限 1.0 |", 0, 4),
    ("cii-uplift", "result_statement", "中冰年 CII 抬高幅度结论行（三船型）",
     "中冰使年 CII 抬高 16.3%", 0, 0),
    ("vopt-table", "result_table", "CII 最优航速表（数学窗 / 工程窗 / 网格互校）",
     "**CII 最优航速（两套窗口并列）**", 0, 6),
    ("pareto-both", "result_statement", "速度-时长 Pareto + 速度-航线 Pareto 两段结论",
     "**速度-时长 Pareto（中冰，2500 nm）**", 0, 5),
    ("uncertainty", "result_statement", "不确定度段（n=20000，metrology/stress 双 σ 口径）",
     "**不确定度（中冰，服务航速，n=20000）**", 0, 4),
    ("sec4-figures", "figure_index", "§④ 结果图清单（6 张图的文字登记）",
     "### ④ 结果图（6 张", 0, 4),
    ("sec5-caveats", "caveat_list", "§⑤ 注意点 7 条（陷阱/判据性质/σ 敏感/适用域/法规系数离线）",
     "### ⑤ 注意点", 0, 10),
    ("sec6-errors", "acceptance_table", "§⑥ 误差判定表（判据 a–g：目标 / 实测 / <3%?）",
     "### ⑥ 误差判定（逐项显式回答）", 0, 10),
    ("provenance-footer", "provenance_statement", "honest 声明 + 产物路径 + commit 归属",
     "honest 声明：", 0, 2),
]

ALLOWED_RESOLUTION = ("resolved", "resolved_in_source", "resolved_in_worktree",
                      "referenced_unresolved", "unresolved", "declared_absent",
                      "metadata_only", "declared_only")
UNRESOLVED_LIKE = ("unresolved", "metadata_only")


# ------------------------------------------------------------------ platform IO
def _req(path, body=None, tok=None, timeout=120):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode()


def login():
    st, body = _req("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                    "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit("login failed: %s %s" % (st, body[:300]))
    return json.loads(body)["access_token"]


def fetch_record(tok=None):
    tok = tok or login()
    st, body = _req("/tensor/reports/" + REPORT_ID, tok=tok)
    if st != 200:
        raise SystemExit("GET report %s -> %s %s" % (REPORT_ID, st, body[:300]))
    rec = json.loads(body)
    if isinstance(rec, dict) and "markdown" not in rec and isinstance(rec.get("data"), dict):
        rec = rec["data"]
    return rec


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ------------------------------------------------------------------- manifest
def _line_of(lines, anchor):
    hits = [i for i, ln in enumerate(lines) if anchor in ln]
    if len(hits) != 1:
        raise SystemExit("anchor not unique (%d hits): %r" % (len(hits), anchor))
    return hits[0]


def _offset(lines, idx):
    return sum(len(ln) + 1 for ln in lines[:idx])


def _refs(md, lines):
    """Every backticked token in the markdown, classified; paths resolved in this worktree."""
    out, seen = [], set()
    for m in re.finditer(r"`([^`\n]+)`", md):
        tok = m.group(1).strip()
        if not tok or tok in seen:
            continue
        seen.add(tok)
        ln = md.count("\n", 0, m.start()) + 1
        if re.match(r"^(GET|POST|PUT|DELETE)\s+\S+", tok):
            kind = "api_reference"
            resolution = {"status": "declared_only", "scope": "report_prose",
                          "reason": "REST route asserted by the report; this package registers the "
                                    "declaration only and does not exercise the endpoint"}
        elif re.fullmatch(r"[\w./-]+\.(py|md|json|csv|png|ya?ml|toml|h|cpp)", tok) or tok.endswith("/"):
            kind = "path_reference"
            rel = tok.rstrip("/")
            exists = (ROOT / rel).exists()
            same = []
            if not exists:
                base = Path(rel).name
                if base:
                    same = sorted(str(p.relative_to(ROOT)) for p in ROOT.rglob(base)
                                  if ".git" not in p.parts)[:5]
            resolution = {
                "status": "resolved_in_worktree" if exists else "unresolved",
                "scope": "delivery_worktree=%s" % ROOT.name,
                "exists_here": exists,
                "same_basename_hits": same,
                "reason": None if exists else
                          "declared by the report as an artefact of the producing (solver) run; not "
                          "present in this TensorKnowledge delivery worktree -- existence neither "
                          "asserted nor denied",
            }
        else:
            kind = "symbol_or_expression"
            resolution = {"status": "declared_only", "scope": "report_prose",
                          "reason": "named in the report (symbol / formula / knob); registration only"}
        out.append({
            "asset_id": "r%s:ref:%02d" % (REPORT_ID, len(out) + 1),
            "kind": kind,
            "name": tok,
            "locator": {"source_field": "markdown", "line": ln,
                        "char_start": m.start(), "char_end": m.end(),
                        "quote": lines[ln - 1]},
            "quote_token": tok,
            "resolution": resolution,
        })
    return out


def _prose_refs(md, lines, already):
    """Artefacts declared in plain prose (not backticked): file names and git SHAs.

    The report names some artefacts only in running text (e.g. chain.py, summary.json,
    commit 7925bc0e); without this pass they would silently fall out of the inventory.
    """
    out = []
    pats = [(r"(?<![\w/`.-])([\w-]+\.(?:py|json|csv|png|md))(?![\w`])", "path_reference"),
            (r"commit\s+([0-9a-f]{7,40})", "git_commit")]
    for pat, kind in pats:
        for m in re.finditer(pat, md):
            tok = m.group(1)
            if tok in already:
                continue
            already.add(tok)
            ln = md.count("\n", 0, m.start(1)) + 1
            if kind == "path_reference":
                exists = (ROOT / tok).exists()
                hits = sorted(str(q.relative_to(ROOT)) for q in ROOT.rglob(tok)
                              if ".git" not in q.parts)[:5] if not exists else []
                resolution = {"status": "resolved_in_worktree" if exists else "unresolved",
                              "scope": "delivery_worktree=%s" % ROOT.name,
                              "exists_here": exists, "same_basename_hits": hits,
                              "reason": None if exists else
                                        "named in prose as an artefact of the producing run; absent "
                                        "from this delivery worktree -- existence neither asserted "
                                        "nor denied"}
            else:
                resolution = {"status": "declared_only", "scope": "report_prose",
                              "reason": "commit id cited by the report as the provenance of the run; "
                                        "that commit is not an object in this repository's history"}
            out.append({
                "asset_id": "r%s:prose:%02d" % (REPORT_ID, len(out) + 1),
                "kind": kind, "name": tok, "reference_form": "prose",
                "locator": {"source_field": "markdown", "line": ln,
                            "char_start": m.start(1), "char_end": m.end(1),
                            "quote": lines[ln - 1]},
                "quote_token": tok, "resolution": resolution})
    return out


def _regulations(md, lines):
    out, seen = [], set()
    for m in re.finditer(r"MEPC\.\d+(?:\(\d+\))?(?:/\d+)*", md):
        tok = m.group(0)
        if tok in seen:
            continue
        seen.add(tok)
        ln = md.count("\n", 0, m.start()) + 1
        out.append({
            "asset_id": "r%s:reg:%02d" % (REPORT_ID, len(out) + 1),
            "kind": "regulation_reference",
            "name": tok,
            "locator": {"source_field": "markdown", "line": ln,
                        "char_start": m.start(), "char_end": m.end(),
                        "quote": lines[ln - 1]},
            "resolution": {"status": "declared_only", "scope": "report_prose",
                           "reason": "regulation cited by the report; the report itself flags its "
                                     "coefficients as offline transcription (§⑤ item 7) and this "
                                     "package does not re-verify them"},
        })
    return out

def build_manifest(rec: dict) -> dict:
    md = rec.get("markdown") or ""
    raw = md.encode("utf-8")
    lines = md.rstrip("\n").split("\n")
    digest = sha256_hex(raw)
    if digest != CONTRACT_SOURCE_HASH:
        raise SystemExit("source hash mismatch: %s != contract %s" % (digest, CONTRACT_SOURCE_HASH))
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_bytes(raw)

    title_quote = lines[0]
    assets = [{
        "asset_id": "r%s:source-markdown" % REPORT_ID,
        "kind": "report_markdown",
        "name": "report-%s-markdown" % REPORT_ID,
        "locator": {"method": "document", "source_field": "markdown", "line": 1,
                    "char_start": 0, "char_end": len(md),
                    "quote": title_quote, "quote_unique": md.count(title_quote) == 1},
        "source_uri": SOURCE_URI,
        "media_type": "text/markdown",
        "bytes": len(raw), "chars": len(md), "lines": len(lines),
        "sha256": digest,
        "hash_scope": "sha256 over the UTF-8 bytes of the markdown field served by "
                      "GET /api/v1/tensor/reports/%s" % REPORT_ID,
        "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
        "resolution": {"status": "resolved_in_source", "scope": "platform_api",
                       "via": "GET /tensor/reports/%s" % REPORT_ID},
        "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
        "chars_matches_contract": len(md) == CONTRACT_CHARS,
    }]

    for n, (suffix, klass, label, anchor, lo, hi) in enumerate(SECTIONS, start=1):
        i = _line_of(lines, anchor)
        start_line, end_line = i + 1 + lo, i + 1 + hi          # 1-based, inclusive
        if end_line > len(lines) or start_line < 1:
            raise SystemExit("span out of range for %s" % suffix)
        quote = "\n".join(lines[start_line - 1:end_line])
        occ = md.count(quote)
        if occ != 1:
            raise SystemExit("quote not unique (%d) for %s" % (occ, suffix))
        cs = _offset(lines, start_line - 1)
        assets.append({
            "asset_id": "r%s:section:%02d" % (REPORT_ID, n),
            "asset_class": klass,
            "label": label,
            "anchor": anchor,
            "in_report_section": "L%d-L%d" % (start_line, end_line),
            "locator": {"method": "char_span", "source_field": "markdown",
                        "start_line": start_line, "end_line": end_line,
                        "char_start": cs, "char_end": cs + len(quote),
                        "quote": quote, "quote_unique": True,
                        "quote_sha256": sha256_hex(quote.encode("utf-8"))},
            "resolution": {"status": "resolved_in_source", "scope": "report_markdown"},
            "note": "block registered verbatim; its numbers are registered, not recomputed",
        })

    # figures declared in the report *record*; the platform exposes name/caption only
    tok = login()
    fig_probes = {}
    for idx, fig in enumerate(rec.get("figures") or []):
        name = fig.get("name") or ""
        st, body = _req("/tensor/reports/%s/figures/%s" % (REPORT_ID, name), tok=tok)
        fig_probes[name] = {"http_status": st, "bytes": len(body)}
        assets.append({
            "asset_id": "r%s:figure:%02d" % (REPORT_ID, idx + 1),
            "kind": "declared_figure",
            "name": name,
            "caption": fig.get("caption"),
            "locator": {"method": "document", "source_field": "record",
                        "pointer": "/figures/%d/name" % idx, "quote": name,
                        "quote_unique": md.count(name) > 0},
            "resolution": {"status": "metadata_only", "scope": "platform_api",
                           "via": "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, name),
                           "http_status": st,
                           "reason": "record exposes name/caption only and the figure-bytes route "
                                     "returned HTTP %d; no byte hash is claimed" % st},
        })

    refs = _refs(md, lines)
    regs = _regulations(md, lines)
    refs = refs + _prose_refs(md, lines, {r["name"] for r in refs} | {r["name"] for r in regs})

    locators = []
    for a in assets + refs + regs:
        loc = a["locator"]
        if loc.get("source_field") != "markdown" or "quote" not in loc:
            continue
        q = loc["quote"]
        ln = loc.get("line") or loc.get("start_line")
        if loc.get("method") == "char_span":
            s_, e_ = loc["start_line"], loc["end_line"]
            on_line = "\n".join(lines[s_ - 1:e_]) == q
        else:
            on_line = (lines[ln - 1] == q) if 0 < ln <= len(lines) else False
        locators.append({
            "asset_id": a["asset_id"], "line": ln,
            "line_range": [loc.get("start_line", ln), loc.get("end_line", ln)],
            "quote_sha256": sha256_hex(q.encode("utf-8")),
            "quote_in_source": q in md,
            "quote_on_declared_line": on_line,
            "occurrences_in_source": md.count(q),
            "resolved": bool(q in md and on_line),
        })

    all_ids = [a["asset_id"] for a in assets + refs + regs]
    dupes = sorted({i for i in all_ids if all_ids.count(i) > 1})
    statuses = [a["resolution"]["status"] for a in assets]
    kinds = {}
    for a in assets:
        key = "%s/%s" % (a.get("kind") or a.get("asset_class"), a["resolution"]["status"])
        kinds[key] = kinds.get(key, 0) + 1

    return {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "hash_alg": "sha256",
            "source_hash": "sha256:" + digest,
            "sha256": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "title": rec.get("title"),
            "scenario_key": rec.get("scenario_key"),
            "upstream_mission_id": rec.get("mission_id"),
            "platform_status": rec.get("status"),
            "platform_tags": rec.get("tags") or [],
            "platform_figures": [f.get("name") for f in (rec.get("figures") or [])],
            "created_at": rec.get("created_at"),
            "local_copy": str(SOURCE_COPY.relative_to(ROOT)),
            "contract": {"source_hash": "sha256:" + CONTRACT_SOURCE_HASH, "chars": CONTRACT_CHARS,
                         "title": CONTRACT_TITLE, "scenario_key": CONTRACT_SCENARIO},
            "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "chars_matches_contract": len(md) == CONTRACT_CHARS,
            "title_matches_contract": (rec.get("title") or "") == CONTRACT_TITLE,
            "scenario_matches_contract": (rec.get("scenario_key") or "") == CONTRACT_SCENARIO,
        },
        "assets": assets,
        "references": refs,
        "regulation_references": regs,
        "locators": locators,
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-8583-01 sets objective.register_assets=true / classify_report_type=false "
            "and notes 'claims 允许为空数组'; constraints no_forced_claim_generation=true and "
            "do_not_mark_claims_as_verified=true apply. This package registers asset identity "
            "(report_id, markdown byte hash, resolvable attachments/artefacts) only -- knowledge "
            "extraction is a downstream package -- so an empty claims array is the complete "
            "result, not an omission."),
        "counts": {
            "assets_total": len(assets),
            "sections_registered": len(SECTIONS),
            "figures_declared_in_record": len(rec.get("figures") or []),
            "figures_with_bytes": sum(1 for v in fig_probes.values() if v["http_status"] == 200),
            "references_total": len(refs),
            "references_resolved_in_worktree": sum(1 for r in refs if r["resolution"]["status"] ==
                                                   "resolved_in_worktree"),
            "references_unresolved": sum(1 for r in refs if r["resolution"]["status"] == "unresolved"),
            "references_declared_only": sum(1 for r in refs if r["resolution"]["status"] ==
                                            "declared_only"),
            "regulation_references": len(regs),
            "locators": len(locators),
            "locators_resolved": sum(1 for x in locators if x["resolved"]),
            "claims": 0,
            "assets_by_status": {s: statuses.count(s) for s in sorted(set(statuses))},
            "kind_status_histogram": dict(sorted(kinds.items())),
        },
        "id_integrity": {"ids_checked": len(all_ids), "duplicates": dupes, "unique": not dupes},
        "unresolved": [
            {"asset_id": a["asset_id"], "name": a.get("name"),
             "status": a["resolution"]["status"], "reason": a["resolution"].get("reason")}
            for a in assets + refs if a["resolution"]["status"] in UNRESOLVED_LIKE
        ],
        "observations": [
            "Markdown is structurally complete: H1 title line, §①–§⑥ and the honest 声明 footer "
            "(L%d-L%d) are all present." % (len(lines) - 2, len(lines)),
            "All %d figure names in the record metadata also appear in the body figure index §④, "
            "so record and prose agree on the figure set; only the bytes are unavailable."
            % len(rec.get("figures") or []),
            "The report's own §⑤ item 7 flags the IMO coefficients as offline transcription "
            "-> WITHHELD by the author; this package does not raise that evidence grade.",
            "Every artefact path named in the body (tools/…, artifacts/cii_ice_in69n10/…, "
            "docs/CII_ICE_COMPLIANCE_IN69N10.md, chain.py, commit 7925bc0e, the calculations REST "
            "route) belongs to the producing solver worktree and is therefore unresolved here.",
        ],
        "limitations": [
            "Registration only: no claim/evidence extraction, no report-type classification, no "
            "verified marks (verification is computed by the platform gate).",
            "source_hash scope = sha256 over the UTF-8 bytes of the markdown string returned by "
            "GET /api/v1/tensor/reports/8583; any edit of the stored markdown invalidates it.",
            "Figure bytes are not served by the platform (probed, see fig_probe); no image hash is "
            "claimed and no pixel-level statement is made.",
            "Reference resolution is limited to this delivery worktree; an absent path is reported "
            "as unresolved and never as a broken upstream artefact.",
            "Direct psql read of tensor_reports is denied to this role in this worktree, so the "
            "platform API is the only source channel used.",
        ],
        "fig_probe": fig_probes,
    }


# ---------------------------------------------------------------- envelope
def build_envelope() -> dict:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    live = sha256_hex((fetch_record().get("markdown") or "").encode("utf-8"))
    if live != man["source"]["sha256"]:
        raise SystemExit("live hash %s != manifest %s -- refusing to emit envelope"
                         % (live, man["source"]["sha256"]))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + live,
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": utcnow(),
            "notes": ("sha256 recomputed from GET /api/v1/tensor/reports/8583 markdown UTF-8 "
                      "bytes; equals contract source_hash sha256:%s" % CONTRACT_SOURCE_HASH),
        },
        "outputs": {"asset_manifest.json": man},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return env


# -------------------------------------------------------------- verification
def verify() -> dict:
    from jsonschema import Draft202012Validator

    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = fetch_record().get("markdown") or ""
    lines = md.rstrip("\n").split("\n")
    live = sha256_hex(md.encode("utf-8"))

    checks = {}
    checks["valid_json"] = {"ok": True,
                            "detail": "asset_manifest.json + kf_result envelope parsed by json.loads"}

    errs = [e.message for e in Draft202012Validator(
        json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text())
    ).iter_errors(env)]
    struct = []
    for key in ("package_id", "task_type", "report_id", "source", "assets", "locators", "claims",
                "counts", "id_integrity", "limitations"):
        if key not in man:
            struct.append("missing key %s" % key)
    if man.get("package_id") != PACKAGE_ID:
        struct.append("manifest package_id != %s" % PACKAGE_ID)
    if man.get("report_id") != REPORT_ID:
        struct.append("manifest report_id != %s" % REPORT_ID)
    checks["schema_pass"] = {"ok": not errs and not struct,
                             "detail": {"kf_result.v1": errs or "0 errors",
                                        "manifest_structure": struct or "0 errors"}}

    bad, span_bad = [], []
    spans = {a["asset_id"]: a["locator"] for a in man["assets"]
             if a["locator"].get("method") == "char_span"}
    for loc in man["locators"]:
        ln = loc["line"]
        q = lines[ln - 1] if 0 < ln <= len(lines) else None
        if loc["asset_id"] in spans:                       # multi-line block: re-slice the range
            sl = spans[loc["asset_id"]]
            q = "\n".join(lines[sl["start_line"] - 1:sl["end_line"]])
        if q is None or q not in md or sha256_hex(q.encode("utf-8")) != loc["quote_sha256"]:
            bad.append(loc["asset_id"])
    for a in man["assets"]:
        loc = a["locator"]
        if loc.get("method") == "char_span" and md[loc["char_start"]:loc["char_end"]] != loc["quote"]:
            span_bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "ok": not bad and not span_bad and all(x["resolved"] for x in man["locators"]),
        "detail": {"locators_checked": len(man["locators"]), "unresolvable": bad,
                   "char_span_mismatch": span_bad,
                   "all_quotes_unique": all(x["occurrences_in_source"] == 1 for x in man["locators"]),
                   "rechecked_against": "live GET /tensor/reports/8583, not the local copy"}}

    checks["source_hash_matches"] = {
        "ok": (live == CONTRACT_SOURCE_HASH == man["source"]["sha256"]
               and env["provenance"]["source_hash"] == "sha256:" + live),
        "detail": {"recomputed": "sha256:" + live, "contract": "sha256:" + CONTRACT_SOURCE_HASH,
                   "envelope": env["provenance"]["source_hash"],
                   "chars_live": len(md), "chars_contract": CONTRACT_CHARS}}

    ids = [a["asset_id"] for a in man["assets"] + man["references"] + man["regulation_references"]]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    checks["no_duplicate_ids"] = {"ok": not dupes and len(ids) == len(set(ids)),
                                  "detail": {"ids": len(ids), "duplicates": dupes}}

    problems = []
    for a in man["assets"] + man["references"] + man["regulation_references"]:
        st = (a.get("resolution") or {}).get("status")
        if st not in ALLOWED_RESOLUTION:
            problems.append("%s bad status %r" % (a["asset_id"], st))
        if st in UNRESOLVED_LIKE and not a["resolution"].get("reason"):
            problems.append("%s missing unresolved reason" % a["asset_id"])
    for c in man["claims"] + env["claims"]:
        if not c.get("evidence") and not c.get("unresolved_reason") and c.get("status") is None:
            problems.append("claim without evidence/unresolved status: %r" % c.get("claim_id"))
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": not problems,
        "detail": {"claims": len(man["claims"]),
                   "claims_empty_reason_present": bool(man.get("claims_empty_reason")),
                   "entries_with_explicit_status": len(man["assets"]) + len(man["references"])
                   + len(man["regulation_references"]),
                   "problems": problems}}

    verdict = {
        "package_id": PACKAGE_ID, "report_id": REPORT_ID, "task_type": TASK_TYPE,
        "verified_at": utcnow(), "source_hash": "sha256:" + live,
        "acceptance": checks, "all_pass": all(c["ok"] for c in checks.values()),
        "checks_passed": sum(1 for c in checks.values() if c["ok"]),
        "checks_total": len(checks),
        "note": "self-checks run by this package on its own artefacts; the platform gate "
                "independently recomputes hash/schema/locators and owns the final verdict. No claim "
                "is marked verified here.",
    }
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return verdict


# -------------------------------------------------------------------- figure
def make_figure() -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = fetch_record().get("markdown") or ""
    n = len(md)
    secs = [a for a in man["assets"] if a["locator"].get("method") == "char_span"]
    covered = sorted((a["locator"]["char_start"], a["locator"]["char_end"]) for a in secs)
    union, gaps, cur = [], [], 0
    for s_, e_ in covered:                                  # union of (possibly nested) spans
        if union and s_ <= union[-1][1]:
            union[-1] = (union[-1][0], max(union[-1][1], e_))
        else:
            union.append((s_, e_))
    for s, e in covered:
        if s > cur:
            gaps.append((cur, s))
        cur = max(cur, e)
    if cur < n:
        gaps.append((cur, n))

    fig, ax = plt.subplots(figsize=(11, 3.6))
    for i, a in enumerate(secs):
        loc = a["locator"]
        ax.barh(0.6, loc["char_end"] - loc["char_start"], left=loc["char_start"], height=0.30,
                color="#2b6cb0", alpha=0.85, edgecolor="black", linewidth=0.4)
        ax.text((loc["char_start"] + loc["char_end"]) / 2, 0.86, "S%02d" % (i + 1),
                ha="center", va="bottom", fontsize=7)
    for s, e in gaps:
        ax.barh(0.2, e - s, left=s, height=0.16, color="#cbd5e0", edgecolor="none")
    ax.set_yticks([0.2, 0.6])
    ax.set_yticklabels(["unregistered\ngap", "registered\nblock"], fontsize=8)
    ax.set_xlim(0, n)
    ax.set_xlabel("character offset in report %s markdown (total %d chars / %d bytes utf-8)"
                  % (REPORT_ID, len(md), len(md.encode("utf-8"))))
    ax.set_title("wp-8583-01 locator coverage: %d/%d quotes resolve verbatim, %d blocks, sha256 %s…"
                 % (man["counts"]["locators_resolved"], man["counts"]["locators"], len(secs),
                    man["source"]["sha256"][:12]), fontsize=9)
    ax.grid(axis="x", alpha=0.25, linestyle=":")
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=140)
    plt.close(fig)
    meta = {"path": str(FIGURE.relative_to(ROOT)), "sha256": sha256_hex(FIGURE.read_bytes()),
            "registered_chars": sum(e - s for s, e in union),
            "registered_chars_sum_of_blocks": sum(e - s for s, e in covered),
            "blocks_nested_overlap": True,
            "unregistered_gap_chars": sum(e - s for s, e in gaps),
            "total_chars": n, "blocks": len(secs)}
    FIGMETA.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


# -------------------------------------------------------------------- report
def render_report() -> str:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    ver = json.loads(VERDICT.read_text(encoding="utf-8"))
    fig = json.loads(FIGMETA.read_text(encoding="utf-8")) if FIGMETA.exists() else {}
    c, src = man["counts"], man["source"]

    rows = []
    for a in man["assets"]:
        if a["locator"].get("method") != "char_span":
            continue
        q = a["locator"]["quote"].replace("|", "\\|").replace("\n", " / ")
        rows.append("| %s | %s | %s | %s | %s |" % (
            a["asset_id"], a["asset_class"], a["in_report_section"],
            q[:130] + ("…" if len(q) > 130 else ""), a["locator"]["quote_sha256"][:16]))
    refs = "".join("| %s | `%s` | %s | L%d |\n" % (
        r["asset_id"], r["name"], r["resolution"]["status"], r["locator"]["line"])
        for r in man["references"])
    regs = "".join("| %s | %s | declared_only | L%d |\n" % (
        r["asset_id"], r["name"], r["locator"]["line"]) for r in man["regulation_references"])
    acc = "".join("| %s | %s | %s |\n" % (
        k, "PASS" if v["ok"] else "FAIL", json.dumps(v["detail"], ensure_ascii=False)[:240])
        for k, v in ver["acceptance"].items())

    if fig:
        fig_line = ("![locator coverage](%s)\n\n图 1：报告 %s markdown 的定位器覆盖图 —— %d 个登记块覆盖 "
                    "%d/%d 字符，%d/%d 引文逐字可解析；浅灰条=未登记间隙（§标题、表格分隔等脚手架字符）。"
                    "由 `scripts/kf_wp8583_01_register.py figure` 生成，png sha256 `%s…`。\n"
                    % (fig["path"], REPORT_ID, c["sections_registered"], fig["registered_chars"],
                       fig["total_chars"], c["locators_resolved"], c["locators"], fig["sha256"][:16]))
    else:
        fig_line = "（本工序未生成图：figure 子命令未运行。）\n"
    probe0 = str(list(man["fig_probe"].values())[0]["http_status"]) if man["fig_probe"] else "n/a"

    P = []
    P.append("# KF-RESULT %s\n" % PACKAGE_ID)
    P.append("工作包 `%s`（task_type `%s`，lane C）· report_id `%s` · 源 `%s#%s` · status `draft`"
             "（verification 由平台门计算，本工序不标 verified）\n"
             % (PACKAGE_ID, TASK_TYPE, REPORT_ID, SOURCE_URI, src["source_field"]))
    P.append("tags：`kf-wp:%s`, `01-asset-registration`, `report:%s`, `lane:C`, `draft`, "
             "`polar_cii_compliance`\n" % (PACKAGE_ID, REPORT_ID))
    P.append("## ① 本工序做了什么\n")
    P.append("登记报告 %s 的**源资产身份**：确认 report_id 与其 `markdown` 字段的字节哈希等于契约值，"
             "再把正文中可解析的结构块、记录里的 %d 张图声明、正文声明的工件/接口/法规引用逐条落成带定位器的"
             "资产条目（%d 个资产 + %d 条正文引用 + %d 条法规引用；定位器 %d 条）。"
             "**不做抽取**：claims 为空数组（契约 `objective.classify_report_type=false`、"
             "`no_forced_claim_generation=true`、`do_not_mark_claims_as_verified=true`）。\n"
             % (REPORT_ID, c["figures_declared_in_record"], c["assets_total"], c["references_total"],
                c["regulation_references"], c["locators"]))
    P.append("## ② 怎么做的（步骤/工具/关键设置）\n")
    P.append("1. 单脚本 `scripts/kf_wp8583_01_register.py`（build/envelope/verify/figure/report/publish）；"
             "凭据只从 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS` 读，不落盘。")
    P.append("2. `build`：`GET /api/v1/tensor/reports/%s` 取 `markdown` 原始 UTF-8 字节 → 本地重算 sha256 → "
             "与契约比对（hash_matches_contract=%s）；chars %d vs 契约 %d（%s）；"
             "title/scenario 亦比对契约（%s/%s）。"
             % (REPORT_ID, str(src["hash_matches_contract"]).lower(), src["chars"],
                src["contract"]["chars"], str(src["chars_matches_contract"]).lower(),
                str(src["title_matches_contract"]).lower(),
                str(src["scenario_matches_contract"]).lower()))
    P.append("3. 结构块登记：每块给**唯一锚点字符串**，运行时在 md 中定位行号（命中≠1 直接 SystemExit），"
             "截取行区间原文作 `quote`，并断言该 quote 在 md 中恰好出现 1 次；char span 由行偏移累加得出，"
             "verify 用 `md[start:end] == quote` 反向切片复核。")
    P.append("4. 引用扫描两遍：① 正则抽全部反引号 token 并分类 path/api/symbol；② 再扫**纯散文**里的文件名与 "
             "`commit <sha>`（如 chain.py / summary.json / 7925bc0e），避免只在行文中出现的工件漏登记。"
             "path 在本交付工作树 `exists()` 判定，缺失记 `unresolved` + 原因（不臆造地址、不宣称上游工件损坏）。")
    P.append("5. 图登记：`GET /tensor/reports/%s/figures/<name>` 探针逐个实测（结果见清单 `fig_probe`；"
             "实测 HTTP %s）→ 无字节，登记 `metadata_only`，不声明任何哈希。"
             % (REPORT_ID, probe0))
    P.append("6. `verify`：`schemas/kf_result.v1.schema.json`（jsonschema Draft202012）+ 清单结构检查 + "
             "定位器对抗性复核（对**实时** API 重取 markdown 重解析，而非信本地副本）。\n")
    P.append("## ③ 产出物清单\n")
    P.append("| 文件 | 要点 |\n|---|---|")
    P.append("| `docs/kf/%s/asset_manifest.json` | 清单主体：%d 资产 / %d 引用 / %d 法规 / %d 定位器 |"
             % (PACKAGE_ID, c["assets_total"], c["references_total"], c["regulation_references"],
                c["locators"]))
    P.append("| `docs/kf/%s/kf_result.%s.json` | 结果信封（kf_result.v1），`provenance.source_hash` = 实测哈希 |"
             % (PACKAGE_ID, PACKAGE_ID))
    P.append("| `docs/kf/%s/verification.json` | 自检 %d/%d |"
             % (PACKAGE_ID, ver["checks_passed"], ver["checks_total"]))
    P.append("| `docs/kf/%s/fig_locator_coverage.png` | 定位器覆盖图（图 1） |" % PACKAGE_ID)
    P.append("| `docs/kf/%s/KF-RESULT-%s.md` | 本报告（唯一 json 代码块 = 结果信封） |"
             % (PACKAGE_ID, PACKAGE_ID))
    P.append("| `runs/%s/report_%s.md` | 源 markdown 逐字节副本（本地核对用） |\n"
             % (PACKAGE_ID, REPORT_ID))
    P.append(fig_line)
    P.append("## ④ 证据定位表（字段 → 原文引文片段，逐字取自 `markdown`）\n")
    P.append("| asset_id | 类别 | 行区间 | 原文引文（截断，多行以 / 连接） | quote sha256[:16] |")
    P.append("|---|---|---|---|---|")
    P.extend(rows)
    P.append("")
    P.append("正文引用（反引号 token 全量 %d 条）：\n" % c["references_total"])
    P.append("| asset_id | token | resolution | 行 |\n|---|---|---|---|")
    P.append(refs.rstrip("\n"))
    P.append("")
    P.append("法规引用（%d 条）：\n" % c["regulation_references"])
    P.append("| asset_id | token | resolution | 行 |\n|---|---|---|---|")
    P.append(regs.rstrip("\n"))
    P.append("")
    P.append("## ⑤ 注意点与局限\n")
    P.append("1. **图只有元数据**：图字节路由实测 HTTP %s，故 %d 张图登记为 `metadata_only`，不声明图片哈希，"
             "也不对图像内容作任何判断。" % (probe0, c["figures_declared_in_record"]))
    P.append("2. **工件路径全部不可解析**：`tools/run_cii_ice_optimization.py`、`artifacts/cii_ice_in69n10/`、"
             "`docs/CII_ICE_COMPLIANCE_IN69N10.md`、`chain.py`、commit `7925bc0e`、"
             "`POST /api/v1/calculations/cii-ice-optimization` 属产出方（solver）工作树，不在本 "
             "TensorKnowledge 交付工作树内；一律 `unresolved`/`declared_only`，"
             "**既不宣称存在，也不把\\\"此处缺失\\\"当作上游故障**。")
    P.append("3. **哈希口径**：`source_hash` = 平台 `GET /tensor/reports/%s` 返回 markdown 的 UTF-8 字节 "
             "sha256；任何对该字段的改动（含空白）都会使本登记失效。" % REPORT_ID)
    P.append("4. **源通道单一**：本角色直读 `tensor_reports` 表被拒（permission denied），API 为唯一通道，如实记录。")
    P.append("5. **不做价值判断**：本工序只登记\\\"报告写了什么、在哪个字符位置\\\"——不重算数字、不评价对错、"
             "不把报告自述的判据 a–g 结论当成已验证事实；报告 §⑤ 第 7 条自述\\\"法规系数离线转录 → WITHHELD\\\"，"
             "本工序保持该证据等级不变。")
    P.append("6. **不覆盖其它报告**：脚本内 REPORT_ID 硬编码为 %s，无跨报告读写。\n" % REPORT_ID)
    P.append("## ⑥ 自检（逐条对照 acceptance）\n")
    P.append("| acceptance | 结果 | 证据 |\n|---|---|---|")
    P.append(acc.rstrip("\n"))
    P.append("")
    P.append("综合：**%d/%d PASS**（`docs/kf/%s/verification.json`，all_pass=%s）。"
             % (ver["checks_passed"], ver["checks_total"], PACKAGE_ID,
                str(ver["all_pass"]).lower()))
    P.append("诚实声明：以上是**本工序自己的**验收脚本结论；平台门独立重算哈希/结构/定位器，最终判级归平台。"
             "若出现未通过项，本表写 FAIL 而不粉饰。\n")
    P.append("### repro_cmd（一键复跑）\n")
    P.append("```bash\ncd <TensorKnowledge worktree>\n"
             "python3 scripts/kf_wp8583_01_register.py all   # build+envelope+verify+figure+report\n"
             "python3 scripts/kf_wp8583_01_register.py publish   # 发布本报告到平台\n```\n")
    P.append("## 结果信封（唯一 json 代码块）\n")
    P.append("```json\n" + json.dumps(env, ensure_ascii=False, indent=2) + "\n```\n")

    md = "\n".join(P)
    REPORT_MD.write_text(md, encoding="utf-8")
    return md


def publish() -> dict:
    md = REPORT_MD.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    if len(blocks) != 1:
        raise SystemExit("report must contain exactly one json block, found %d" % len(blocks))
    json.loads(blocks[0])
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    c = man["counts"]
    figures = []
    if FIGURE.exists():
        figures = [{"name": FIGURE.name,
                    "caption": "wp-8583-01 定位器覆盖图：报告 %s markdown 的登记块 char-span 与未登记"
                               "间隙（%d/%d 引文逐字可解析）"
                               % (REPORT_ID, c["locators_resolved"], c["locators"]),
                    "png_base64": base64.b64encode(FIGURE.read_bytes()).decode()}]
    summary = ("%s (01-asset-registration, report %s): markdown sha256 recomputed = contract %s, "
               "chars %d; %d block locators + %d body references + %d regulation references "
               "registered; %d/%d quotes resolve verbatim; %d figure records metadata_only (no "
               "bytes); claims=[] by contract."
               % (PACKAGE_ID, REPORT_ID, man["source"]["sha256"][:16], man["source"]["chars"],
                  c["sections_registered"], c["references_total"], c["regulation_references"],
                  c["locators_resolved"], c["locators"], c["figures_declared_in_record"]))
    payload = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": summary,
        "scenario_key": CONTRACT_SCENARIO,
        "mission_id": UPSTREAM_MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + REPORT_ID,
                 "lane:C", "draft", "knowledge-factory", "cii", "polar_cii_compliance"],
        "markdown": md,
        "figures": figures,
    }
    st, resp = _req("/tensor/reports", payload, tok=login())
    print(st, resp[:400])
    if st not in (200, 201):
        raise SystemExit("publish failed")
    return json.loads(resp) if resp.strip().startswith("{") else {"status": st, "raw": resp[:400]}


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("build", "all"):
        man = build_manifest(fetch_record())
        MANIFEST.write_text(json.dumps(man, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("build: %d assets, %d refs, %d regs, %d locators, hash_matches_contract=%s"
              % (man["counts"]["assets_total"], man["counts"]["references_total"],
                 man["counts"]["regulation_references"], man["counts"]["locators"],
                 man["source"]["hash_matches_contract"]))
    if cmd in ("envelope", "all"):
        print("envelope:", build_envelope()["provenance"]["source_hash"])
    if cmd in ("verify", "all"):
        v = verify()
        print("verify: %d/%d pass, all_pass=%s"
              % (v["checks_passed"], v["checks_total"], v["all_pass"]))
        if not v["all_pass"]:
            for k, val in v["acceptance"].items():
                if not val["ok"]:
                    print("  FAIL %s: %s" % (k, json.dumps(val["detail"], ensure_ascii=False)[:400]))
    if cmd in ("figure", "all"):
        f = make_figure()
        print("figure:", f["path"], f["sha256"][:16],
              "coverage %d/%d chars" % (f["registered_chars"], f["total_chars"]))
    if cmd in ("report", "all"):
        render_report()
        print("report:", str(REPORT_MD.relative_to(ROOT)))
    if cmd == "publish":
        print(publish())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv))
