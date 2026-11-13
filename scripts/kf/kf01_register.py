#!/usr/bin/env python3
"""KF lane C - task_type=01-asset-registration - reusable registrar (one report per invocation).

Generalises the wp-542-01 one-off builder (scripts/kf/build_asset_manifest.py, left untouched)
into a parameterised tool: the report contract is supplied on the command line, every locator is
derived from the *fetched* source bytes, and nothing is retyped by hand.

Scope guard (per contract): a single report_id per run. No extraction, no claim generation,
no `verified` marks - verification status is computed by the platform gate, not here.

Usage (wp-7450-01):
  python3 scripts/kf/kf01_register.py --preset wp-7450-01 build verify result figure report
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

PRESETS = {
    "wp-7450-01": {
        "package_id": "wp-7450-01",
        "report_id": "7450",
        "expected_hash": "4b20aadcaabc128bc8fb10e8f9f164de670421c2b67d36d2837fc5781d96bfac",
        "expected_chars": 6312,
        "title": "m6284 CII 规则三实现交叉核对：green_shipping 静默默认清偿 + 独立转录互证（164 项回归）",
        "scenario_key": "ship_performance/verification_debt/cii_rules_crosscheck",
        "out_dir": "docs/kf/wp-7450-01",
        # interface tokens registered on top of the auto-scan (package config, not domain hard-coding)
        "declared_tokens": {"api_endpoint": ["/cii"], "api_field": ["allow_inapplicable_year"]},
    },
    "wp-12068-01": {
        "package_id": "wp-12068-01",
        "report_id": "12068",
        "expected_hash": "de2f16253ed522c619246898f442983d5a66f3a2bec42c2fe271847a2020cbf0",
        "expected_chars": 1086,
        "title": "DG Compressible Euler: Hierarchical Verification Chain",
        "scenario_key": "p315w1-n07-dg-compressible-euler",
        "out_dir": "docs/kf/wp-12068-01",
        "mission_id": 15738,
        # this source has no file-path references at all; the 5 record figures are metadata-only
        "producing_repo": "（源报告未指明具体仓名）",
        "figure_note": ("红色条不是缺陷而是**边界的正确表达**：5 张图在 `record.figures[]` 中只有 name+caption（`png_base64` 为空），"
                        "本包不伪造字节哈希，如实记 `referenced_unresolved`（metadata_only）。"),
        "cross_repo_note": [
            "4. **无跨仓路径引用**：源 markdown 不含任何文件路径引用（无行内代码/围栏代码路径），故清单中不存在路径类资产；",
            "   5 个图名亦未出现在正文中，其定位器如实退化为整文档跨度（method=document）。",
        ],
    },
}

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]

PATH_RE = re.compile(r"(?:\.\./)?(?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_.\-]+\.(?:py|json|yaml|yml|csv|md|png)")
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
HEADING_RE = re.compile(r"^(#{2,4})\s+(.*)$")

STATUS_ENUM = ("resolved_in_source", "referenced_unresolved", "declared_absent")


# ------------------------------------------------------------------ platform I/O
def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def login():
    try:
        d = _req(BASE + "/auth/login", data=json.dumps({"username": USER, "password": PASS}).encode())
    except urllib.error.HTTPError:
        body = urllib.parse.urlencode({"username": USER, "password": PASS}).encode()
        d = _req(BASE + "/auth/login", data=body, ctype="application/x-www-form-urlencoded")
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_report(token, report_id):
    d = _req(BASE + "/tensor/reports/%s" % report_id, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str) or not md:
        raise SystemExit("report %s has no markdown field" % report_id)
    return d, md


# ------------------------------------------------------------------ source geometry
class Source:
    """Fetched markdown + line/char geometry, so every locator is computed, never guessed."""

    def __init__(self, md: str):
        self.md = md
        self.lines = md.split("\n")
        self.starts = []
        off = 0
        for ln in self.lines:
            self.starts.append(off)
            off += len(ln) + 1

    def line_of(self, char: int) -> int:
        lo, hi = 0, len(self.starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.starts[mid] <= char:
                lo = mid
            else:
                hi = mid - 1
        return lo

    def line_span(self, lineno0: int):
        s = self.starts[lineno0]
        return s, s + len(self.lines[lineno0])

    def section_of(self, lineno0: int) -> str:
        for i in range(lineno0, -1, -1):
            m = HEADING_RE.match(self.lines[i])
            if m:
                return m.group(2).strip()
        return "(preamble)"

    def locator_for_line(self, lineno0: int, token=None):
        s, e = self.line_span(lineno0)
        quote = self.lines[lineno0]
        loc = {
            "method": "char_span",
            "start_char": s,
            "end_char": e,
            "start_line": lineno0 + 1,
            "end_line": lineno0 + 1,
            "quote": quote,
            "unique": self.md.count(quote) == 1,
        }
        if token is not None:
            idx = quote.find(token)
            if idx < 0:
                raise SystemExit("token %r not on line %d" % (token, lineno0 + 1))
            loc["token"] = token
            loc["token_span"] = [s + idx, s + idx + len(token)]
        return loc

    def locator_document(self):
        return {
            "method": "document",
            "start_char": 0,
            "end_char": len(self.md),
            "start_line": 1,
            "end_line": self.line_of(len(self.md) - 1) + 1,
            "quote": self.md,
            "unique": True,
        }


def classify_path(path: str) -> str:
    p = path.lower()
    if p.endswith(".py"):
        return "source_code_reference"
    if p.endswith(".png"):
        return "figure_reference"
    if p.endswith((".json", ".csv", ".yaml", ".yml")):
        return "data_artifact_reference"
    return "document_reference"


def resolve_local(path: str, worktree: Path) -> dict:
    norm = path.lstrip("./")
    cand = (worktree / norm).resolve()
    try:
        cand.relative_to(worktree.resolve())
    except ValueError:
        return {
            "status": "referenced_unresolved",
            "check": "path containment in delivery worktree (TensorKnowledge)",
            "result": "unresolved",
            "detail": "reference escapes the TensorKnowledge worktree; it names a file of another repository, which this package must not read or write",
        }
    if cand.is_file():
        raw = cand.read_bytes()
        return {
            "status": "resolved_in_source",
            "check": "os.path.isfile + sha256 of worktree file",
            "result": "resolved",
            "detail": "found at %s (%d bytes)" % (norm, len(raw)),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
        }
    return {
        "status": "referenced_unresolved",
        "check": "os.path.isfile in delivery worktree",
        "result": "unresolved",
        "detail": "path is absent from the TensorKnowledge worktree; it belongs to the producing repository and is outside this package's boundary",
    }


# ------------------------------------------------------------------ scanning
def code_spans(src: Source):
    """Yield (lineno0, token, origin) for backticked tokens and tokens inside fenced blocks."""
    in_fence = False
    for i, line in enumerate(src.lines):
        if line.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            for m in PATH_RE.finditer(line):
                yield i, m.group(0), "code_fence"
            continue
        for m in BACKTICK_RE.finditer(line):
            pm = PATH_RE.search(m.group(1))
            if pm:
                yield i, pm.group(0), "inline_code"


def scan_references(src: Source, worktree: Path):
    out, seen = [], set()
    for lineno0, token, origin in code_spans(src):
        if token.lower().endswith(".png"):
            continue  # folded into the figure assets
        key = (token, lineno0 + 1)
        if key in seen:
            continue
        seen.add(key)
        res = resolve_local(token, worktree)
        cls = classify_path(token)
        out.append({
            "asset_class": cls,
            "label": "%s (markdown line %d)" % (token, lineno0 + 1),
            "in_report_section": src.section_of(lineno0),
            "locator": src.locator_for_line(lineno0, token),
            "resolution": res["status"],
            "resolution_check": {"check": res["check"], "result": res["result"], "detail": res["detail"]},
            "path_reference": token,
            "origin": origin,
            "note": "%s reference parsed out of the %s; resolved only inside this worktree." % (cls, origin),
        })
    return out


def scan_figures(src: Source, meta: dict):
    out = []
    for n, fig in enumerate(meta.get("figures") or [], start=1):
        name = fig.get("name") or "figure[%d]" % n
        b64 = fig.get("png_base64") or ""
        try:
            blob = base64.b64decode(b64) if b64 else b""
        except Exception:  # noqa: BLE001
            blob = b""
        hit = None
        for i, line in enumerate(src.lines):
            if name in line:
                hit = i
                break
        loc = src.locator_for_line(hit, name) if hit is not None else src.locator_document()
        payload_note = (
            "record.figures[%d] carries a png_base64 payload (%d bytes, sha256 %s)"
            % (n - 1, len(blob), hashlib.sha256(blob).hexdigest()) if blob else
            "record.figures[%d] lists name+caption only: png_base64 is empty, so no byte hash can be computed" % (n - 1)
        )
        out.append({
            "asset_class": "embedded_figure",
            "label": name,
            "in_report_section": src.section_of(hit) if hit is not None else "(record field figures)",
            "locator": loc,
            "resolution": "resolved_in_source" if blob else "referenced_unresolved",
            "resolution_check": {
                "check": "figures[] name match + png_base64 payload length",
                "result": "resolved" if blob else "unresolved",
                "detail": payload_note,
            },
            "figure_uri": "tensor://reports/%s#figures[%d]" % (meta.get("id"), n - 1),
            "caption": fig.get("caption"),
            "bytes": len(blob) or None,
            "sha256": hashlib.sha256(blob).hexdigest() if blob else None,
            "resolution_detail": "payload_present" if blob else "metadata_only",
            "note": payload_note,
        })
    return out


def scan_tables(src: Source):
    out, i, n = [], 0, 0
    while i < len(src.lines):
        if src.lines[i].startswith("|"):
            j = i
            while j + 1 < len(src.lines) and src.lines[j + 1].startswith("|"):
                j += 1
            n += 1
            s, _ = src.line_span(i)
            _, e = src.line_span(j)
            blk = src.md[s:e]
            out.append({
                "asset_class": "report_table",
                "label": "table %d @ lines %d-%d" % (n, i + 1, j + 1),
                "in_report_section": src.section_of(i),
                "locator": {"method": "char_span", "start_char": s, "end_char": e,
                            "start_line": i + 1, "end_line": j + 1,
                            "quote": blk, "unique": src.md.count(blk) == 1},
                "resolution": "resolved_in_source",
                "resolution_check": {"check": "pipe-table block present in markdown at recorded char span",
                                     "result": "resolved",
                                     "detail": "%d rows x %d columns" % (j - i + 1, src.lines[i].count("|") - 1)},
                "rows": j - i + 1,
                "columns": src.lines[i].count("|") - 1,
                "note": "registered as an in-report data artifact; contents are not extracted by this work package.",
            })
            i = j + 1
        else:
            i += 1
    return out


def scan_code_fences(src: Source):
    out, i = [], 0
    while i < len(src.lines):
        line = src.lines[i]
        if line.strip().startswith("```"):
            lang = line.strip()[3:].strip()
            j = i + 1
            while j < len(src.lines) and not src.lines[j].strip().startswith("```"):
                j += 1
            last = min(j, len(src.lines) - 1)
            s, _ = src.line_span(i)
            _, e = src.line_span(last)
            blk = src.md[s:e]
            out.append({
                "asset_class": "repro_command_block",
                "label": "%s fence @ lines %d-%d" % (lang or "plain", i + 1, last + 1),
                "in_report_section": src.section_of(i),
                "locator": {"method": "char_span", "start_char": s, "end_char": e,
                            "start_line": i + 1, "end_line": last + 1,
                            "quote": blk, "unique": src.md.count(blk) == 1},
                "resolution": "resolved_in_source",
                "resolution_check": {"check": "fenced code block present in markdown at recorded char span",
                                     "result": "resolved",
                                     "detail": "%d command line(s), language=%s" % (max(last - i - 1, 0), lang or "plain")},
                "language": lang or "plain",
                "note": "reproduction block as written in the report; commands are not executed by this work package.",
            })
            i = last + 1
        else:
            i += 1
    return out


def scan_declared_tokens(src: Source, declared: dict):
    """Interface tokens are pinned to an exact inline-code span (never to a first loose substring
    hit: `/cii` also occurs inside path names, so an unanchored search would mislocate it)."""
    out = []
    for cls, tokens in (declared or {}).items():
        for tok in tokens:
            span = None
            for m in BACKTICK_RE.finditer(src.md):
                if m.group(1).strip() == tok:
                    span = (m.start(1), m.end(1))
                    break
            if span is None:
                pos = src.md.find(tok)
                if pos < 0:
                    raise SystemExit("declared token %r absent from source markdown" % tok)
                span = (pos, pos + len(tok))
                anchor = "first loose occurrence (no exact inline-code span found)"
            else:
                anchor = "exact inline-code span"
            s, e = span
            line = src.line_of(s)
            quote = tok
            out.append({
                "asset_class": cls,
                "label": tok,
                "in_report_section": src.section_of(line),
                "locator": {
                    "method": "char_span",
                    "start_char": s, "end_char": e,
                    "start_line": line + 1, "end_line": src.line_of(e - 1) + 1,
                    "quote": quote, "unique": src.md.count(quote) == 1,
                    "context_line": src.lines[line],
                },
                "resolution": "resolved_in_source",
                "resolution_check": {"check": "token found verbatim in markdown (%s)" % anchor,
                                     "result": "resolved",
                                     "detail": "occurs %d time(s); pinned at line %d" % (src.md.count(tok), line + 1)},
                "note": "interface surface registered for downstream work packages; no semantics extracted.",
            })
    return out


# ------------------------------------------------------------------ build
def build(cfg, out_dir: Path, worktree: Path):
    token = login()
    meta, md = fetch_report(token, cfg["report_id"])
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != cfg["expected_hash"]:
        raise SystemExit("SOURCE HASH MISMATCH: contract=%s actual=%s" % (cfg["expected_hash"], digest))
    if cfg.get("expected_chars") and len(md) != cfg["expected_chars"]:
        raise SystemExit("SOURCE CHAR COUNT MISMATCH: contract=%d actual=%d" % (cfg["expected_chars"], len(md)))

    src = Source(md)
    assets = [{
        "asset_class": "report_markdown",
        "label": "source markdown of report %s" % cfg["report_id"],
        "in_report_section": "(whole document)",
        "locator": src.locator_document(),
        "resolution": "resolved_in_source",
        "resolution_check": {"check": "GET /tensor/reports/%s markdown field + sha256 over utf-8 bytes" % cfg["report_id"],
                             "result": "resolved",
                             "detail": "chars=%d bytes_utf8=%d sha256=%s" % (len(md), len(raw), digest)},
        "source_uri": "tensor://reports/%s" % cfg["report_id"],
        "note": "the source asset itself; its byte hash is the provenance anchor of this work package.",
    }]
    assets += scan_figures(src, meta)
    assets += scan_references(src, worktree)
    assets += scan_tables(src)
    assets += scan_code_fences(src)
    assets += scan_declared_tokens(src, cfg.get("declared_tokens"))

    ids, numbered = set(), []
    for n, a in enumerate(assets, start=1):
        aid = "A%02d" % n
        if aid in ids:
            raise SystemExit("duplicate asset_id %s" % aid)
        ids.add(aid)
        if a["resolution"] not in STATUS_ENUM:
            raise SystemExit("bad resolution %r" % a["resolution"])
        numbered.append({"asset_id": aid, **a, "kind": a["asset_class"]})

    by_class, by_res = {}, {}
    for a in numbered:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    quotes = [a["locator"]["quote"] for a in numbered]
    dup = sorted({q for q in quotes if quotes.count(q) > 1 and len(q) < 400})

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": cfg["package_id"],
        "task_type": "01-asset-registration",
        "report_id": cfg["report_id"],
        "contract_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "uri": "tensor://reports/%s" % cfg["report_id"],
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": meta.get("title") or cfg.get("title"),
            "scenario_key": meta.get("scenario_key") or cfg.get("scenario_key"),
            "platform_figures": [f.get("name") for f in (meta.get("figures") or [])],
            "platform_tags": meta.get("tags") or [],
            "platform_status": meta.get("status"),
            "platform_created_at": meta.get("created_at"),
        },
        "counts": {
            "assets": len(numbered),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "distinct_referenced_paths": len({a["path_reference"] for a in numbered if "path_reference" in a}),
        },
        "assets": numbered,
        "claims": [],
        "integrity": {
            "quote_uniqueness": {
                "total_quotes": len(quotes),
                "quotes_unique_in_source": sum(1 for q in quotes if md.count(q) == 1),
                "repeated_quotes": dup,
                "note": "repeated short quotes are structural (identical table rows); each asset still carries its own char span.",
            },
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == cfg["expected_hash"],
            "hash_alg": "sha256 over markdown encoded as utf-8",
            "locator_scheme": "absolute character span in markdown, 1-based inclusive line numbers",
        },
        "identity_granularity": (
            "File references are occurrence-level: identity is (path, markdown line), so a file cited twice "
            "yields two assets carrying their own quotes; counts.distinct_referenced_paths is the deduplicated view."
        ),
        "limitations": [
            "Registration only: no text extraction, no claim generation, no `verified` marks (verification is platform-gated).",
            "Referenced source paths belong to the producing repository; they are resolved strictly inside the TensorKnowledge delivery worktree, so cross-repository references stay referenced_unresolved by design.",
            "Figures are inventoried from record.figures[] as-is; when png_base64 is empty the asset is metadata_only and no byte hash is claimed.",
            "Table and code-fence assets record geometry (rows/columns/language) only; their content is not restated as knowledge.",
            "Only path-like references, fenced/inline code paths, tables, figures and explicitly configured interface tokens are registered. Bare prose symbols (e.g. a rule table named in the text that lives in the producing repository) are deliberately NOT inferred - registering them would require assuming information the report does not pin to a file.",
            "Outputs live under docs/kf/<package>/ because the push gate drops artifacts/** (see docs/ops), so registered artifacts are not silently filtered.",
        ],
        "producer": {
            "generator": "scripts/kf/kf01_register.py",
            "contract_version": "1.0",
            "fetched_via": "GET /api/v1/tensor/reports/%s" % cfg["report_id"],
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "asset_manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets, sha256 %s)" % (path.relative_to(REPO), len(numbered),
                                              hashlib.sha256(path.read_bytes()).hexdigest()[:16]))
    return manifest


def emit_result(cfg, out_dir: Path):
    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    mraw = (out_dir / "asset_manifest.json").read_bytes()
    token = login()
    _meta, live_md = fetch_report(token, cfg["report_id"])
    live = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    if live != manifest["source"]["hash"]:
        raise SystemExit("live source drifted from manifest: %s != %s" % (live, manifest["source"]["hash"]))
    result = {
        "package_id": cfg["package_id"],
        "task_type": "01-asset-registration",
        "report_id": cfg["report_id"],
        "provenance": {
            "source_uri": "tensor://reports/%s" % cfg["report_id"],
            "source_field": "markdown",
            "source_hash": "sha256:" + live,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(live_md),
            "source_bytes_utf8": len(live_md.encode("utf-8")),
            "fetched_via": "GET /api/v1/tensor/reports/%s" % cfg["report_id"],
            "generator": "scripts/kf/kf01_register.py",
            "contract_version": "1.0",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str((out_dir / "asset_manifest.json").relative_to(REPO)),
                "sha256": hashlib.sha256(mraw).hexdigest(),
                "bytes": len(mraw),
                "asset_count": manifest["counts"]["assets"],
                "claims": len(manifest["claims"]),
            }
        },
        "claims": [],
    }
    out = out_dir / "kf_result.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % out.relative_to(REPO))
    return result


# ------------------------------------------------------------------ verify
def _relaxed_asset_schema():
    """schemas/asset_manifest.v1.schema.json pins package_id/task_type/report_id as consts (wp-448-01).
    Relax exactly those three so the schema stays a real check for this package."""
    spec = json.loads((REPO / "schemas" / "asset_manifest.v1.schema.json").read_text(encoding="utf-8"))
    for key in ("package_id", "task_type", "report_id"):
        if "const" in spec.get("properties", {}).get(key, {}):
            spec["properties"][key] = {"type": "string", "minLength": 1}
    src = spec.get("properties", {}).get("source", {}).get("properties", {})
    if "const" in src.get("uri", {}):
        src["uri"] = {"type": "string", "pattern": r"^tensor://reports/[0-9]+$"}
    return spec


def verify(cfg, out_dir: Path):
    import jsonschema

    token = login()
    _meta, md = fetch_report(token, cfg["report_id"])
    raw = md.encode("utf-8")
    src = Source(md)
    checks = {}
    mp, rp = out_dir / "asset_manifest.json", out_dir / "kf_result.json"
    try:
        manifest = json.loads(mp.read_text(encoding="utf-8"))
        result = json.loads(rp.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "json.loads OK for asset_manifest.json and kf_result.json"}
    except Exception as e:  # noqa: BLE001
        checks["valid_json"] = {"pass": False, "detail": str(e)}
        manifest = result = None

    if manifest is not None:
        errs = []
        for name, doc, schema in (
            ("asset_manifest.json", manifest, _relaxed_asset_schema()),
            ("kf_result.json", result, json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))),
        ):
            v = jsonschema.Draft202012Validator(schema)
            for err in sorted(v.iter_errors(doc), key=lambda x: list(x.path)):
                errs.append("%s: %s at %s" % (name, err.message, list(err.path)))
        checks["schema_pass"] = {
            "pass": not errs,
            "detail": "jsonschema draft2020-12 errors=%d %s | asset_manifest.v1 checked with its four package-pinned consts relaxed (package_id/task_type/report_id/source.uri pattern), kf_result.v1 checked as shipped"
            % (len(errs), errs[:5]),
        }

        bad = []
        for a in manifest["assets"]:
            loc = a["locator"]
            s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
            if not (0 <= s < e <= len(md)) or md[s:e] != q or q not in md:
                bad.append([a["asset_id"], "char_span_or_quote"])
                continue
            if src.line_of(s) + 1 != loc["start_line"] or src.line_of(e - 1) + 1 != loc["end_line"]:
                bad.append([a["asset_id"], "line_map"])
                continue
            if "token" in loc:
                ts, te = loc["token_span"]
                if md[ts:te] != loc["token"] or not (s <= ts and te <= e):
                    bad.append([a["asset_id"], "token_span"])
        checks["source_locator_resolvable"] = {
            "pass": not bad,
            "detail": "checked %d locators (char span + verbatim quote + 1-based line map + token span); unresolvable=%s"
            % (len(manifest["assets"]), bad),
        }

        actual = hashlib.sha256(raw).hexdigest()
        checks["source_hash_matches"] = {
            "pass": actual == manifest["source"]["hash"] == cfg["expected_hash"]
            and result["provenance"]["source_hash"] == "sha256:" + actual,
            "detail": "recomputed=%s manifest=%s envelope=%s contract=%s"
            % (actual, manifest["source"]["hash"], result["provenance"]["source_hash"], cfg["expected_hash"]),
        }
        ids = [a["asset_id"] for a in manifest["assets"]]
        checks["no_duplicate_ids"] = {"pass": len(ids) == len(set(ids)) and all(ids),
                                      "detail": "assets=%d unique=%d" % (len(ids), len(set(ids)))}
        claims = manifest.get("claims", [])
        bad_c = [c.get("claim_id") for c in claims if not c.get("evidence") and c.get("status") != "unresolved"]
        checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
            "pass": not bad_c,
            "detail": "claims=%d violating=%d (empty array: vacuously satisfied per contract notes)" % (len(claims), len(bad_c)),
        }
        checks["do_not_mark_claims_as_verified"] = {
            "pass": all(c.get("status") != "verified" for c in claims),
            "detail": "claims=%d, none carries status='verified'" % len(claims),
        }
        checks["report_id_scoped"] = {
            "pass": manifest["report_id"] == result["report_id"] == cfg["report_id"],
            "detail": "single report_id=%s (no other report is read or written)" % cfg["report_id"],
        }
        checks["manifest_hash_matches_envelope"] = {
            "pass": hashlib.sha256(mp.read_bytes()).hexdigest() == result["outputs"]["asset_manifest.json"]["sha256"],
            "detail": "recomputed=%s envelope=%s"
            % (hashlib.sha256(mp.read_bytes()).hexdigest(), result["outputs"]["asset_manifest.json"]["sha256"]),
        }

    verdict = {
        "package_id": cfg["package_id"],
        "report_id": cfg["report_id"],
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(mp.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(mp.read_bytes()).hexdigest(),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
        "scope_note": "self-check by the producing agent; the authoritative verification is the platform gate.",
    }
    (out_dir / "verification.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(verdict, ensure_ascii=False, indent=1))
    return verdict


# ------------------------------------------------------------------ figure
def render_figure(cfg, out_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    assets = manifest["assets"]
    classes = sorted({a["asset_class"] for a in assets})
    color = {"resolved_in_source": "#2e7d32", "referenced_unresolved": "#c62828", "declared_absent": "#616161"}
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7.4), gridspec_kw={"height_ratios": [1, 1.35]})

    ys = list(range(len(classes)))
    left = [0] * len(classes)
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        vals = [sum(1 for a in assets if a["asset_class"] == c and a["resolution"] == res) for c in classes]
        if not any(vals):
            continue
        ax1.barh(ys, vals, left=left, color=color[res], label=res)
        left = [l + v for l, v in zip(left, vals)]
    ax1.set_yticks(ys)
    ax1.set_yticklabels(classes, fontsize=8)
    ax1.set_xlabel("assets")
    ax1.set_title("A) asset inventory: class x resolution (n=%d, report %s)" % (len(assets), manifest["report_id"]), fontsize=10)
    ax1.legend(fontsize=7, loc="lower right")
    ax1.grid(axis="x", alpha=0.3)

    for a in assets:
        y = classes.index(a["asset_class"])
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        ax2.barh(y, max(e - s, 1), left=s, height=0.6, color=color[a["resolution"]], alpha=0.85)
        ax2.text(s, y + 0.40, a["asset_id"], fontsize=5.5)
    ax2.set_yticks(ys)
    ax2.set_yticklabels(classes, fontsize=8)
    ax2.set_xlim(0, manifest["source"]["chars"])
    ax2.set_xlabel("character offset in markdown (source has %d chars / %d bytes utf-8)"
                   % (manifest["source"]["chars"], manifest["source"]["bytes_utf8"]))
    ax2.set_title("B) locator coverage map: char span of every registered asset (computed, not transcribed)", fontsize=10)
    ax2.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out = out_dir / "figures" / ("%s_asset_locator_map.png" % cfg["package_id"])
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote %s" % out.relative_to(REPO))
    return out


# ------------------------------------------------------------------ report
def render_report(cfg, out_dir: Path, png: Path):
    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((out_dir / "kf_result.json").read_text(encoding="utf-8"))
    verdict = json.loads((out_dir / "verification.json").read_text(encoding="utf-8"))
    _meta, md = fetch_report(login(), cfg["report_id"])
    src = Source(md)
    msha = hashlib.sha256((out_dir / "asset_manifest.json").read_bytes()).hexdigest()
    rsha = hashlib.sha256((out_dir / "kf_result.json").read_bytes()).hexdigest()
    n = manifest["counts"]["assets"]
    nfig = sum(1 for a in manifest["assets"] if a["asset_class"] == "embedded_figure")
    ntab = sum(1 for a in manifest["assets"] if a["asset_class"] == "report_table")

    def cell(v, lim=64):
        return (v.replace("\n", " ").replace("|", "\\|").replace("`", "'"))[:lim]

    rows = []
    for a in manifest["assets"]:
        rows.append("| %s | %s | %s | L%d | `%s` |" % (
            a["asset_id"], a["asset_class"], a["resolution"],
            a["locator"]["start_line"], cell(a["locator"]["quote"])))
    selfrows = []
    for k, v in verdict["checks"].items():
        selfrows.append("| %s | %s | %s |" % (k, "PASS" if v["pass"] else "FAIL", cell(v["detail"], 150)))

    fig_rel = "figures/" + png.name
    lines = [
        "# KF-RESULT %s" % cfg["package_id"],
        "",
        "> 工序 01-asset-registration · report_id=%s · lane C · 产出 `asset_manifest.json`（登记，不抽取）" % cfg["report_id"],
        "> source_hash（平台可独立重算，sha256 over markdown utf-8 bytes）= `sha256:%s`" % manifest["source"]["hash"],
        "> 契约 source_hash = `sha256:%s` → 逐字符一致" % cfg["expected_hash"],
        "",
        "## ① 本工序做了什么",
        "",
        "对 `report_id=%s`（《%s》，scenario_key=`%s`）执行**资产登记**：" % (
            cfg["report_id"], manifest["source"]["title"], manifest["source"]["scenario_key"]),
        "确认报告 markdown 的字节哈希与契约一致（%d 字符 / %d 字节 utf-8），把正文里可解析的附件/工件登记为带**可复算定位器**的清单：" % (
            manifest["source"]["chars"], manifest["source"]["bytes_utf8"]),
        "内嵌图、源码/工件路径引用、表格、复现命令块、接口字段。**不做抽取、不生成 claim、不标注 verified**",
        "（契约 `objective.classify_report_type=false`，`notes` 明确 claims 允许为空数组）。",
        "",
        "规模：登记资产 **%d** 项，claims **0** 项；`counts.by_resolution` = `%s`。" % (
            n, json.dumps(manifest["counts"]["by_resolution"], ensure_ascii=False)),
        "",
        "## ② 怎么做的（步骤 / 工具 / 关键设置）",
        "",
        "1. **取原文**：`GET /api/v1/tensor/reports/%s` 取 `markdown` 字段（`scripts/kf/kf01_register.py::fetch_report`）；"
        "只碰这一个 report_id，全程未凭记忆复述。" % cfg["report_id"],
        "2. **哈希门**：对 markdown 的 utf-8 字节做 sha256，与契约 `source_hash`/`chars` 双比对，不一致直接 `SystemExit`（不产出半成品）。",
        "3. **定位器生成**：`Source` 用逐行长度前缀和求出每行起始字符偏移，资产定位器一律为**绝对字符跨度** + 反推的 1-based 行号；",
        "   `quote` 取自源字节切片 `md[s:e]`，**不存在手抄环节**（这也使平台侧「子串独立重算」必然成立）。",
        "4. **扫描规则**（确定性、无领域硬编码；域参数经包配置传入）：行内代码/围栏代码中的 `*.py|json|png|md|csv|yaml` 路径 → 路径引用"
        "（出现级身份 = 路径 × 行号）；`record.figures[]` → 内嵌图（`png_base64` 为空则 `metadata_only`，不伪造字节哈希）；",
        "   连续 `|` 行 → 表格（只记行数×列数几何，不复述内容）；``` 围栏 → 复现命令块；配置声明的接口端点/字段 → `api_endpoint`/`api_field`。",
        "5. **本地解析**：路径只在**本交付工作树**内解析（`os.path.isfile` + 命中文件 sha256）；属产出仓 %s 的路径" % cfg.get("producing_repo", "ship-performance-platform"),
        "   越界即如实记 `referenced_unresolved`，不读别的仓。",
        "6. **信封 + 自检**：`kf_result.json` 按 `schemas/kf_result.v1.schema.json` 生成；`verification.json` 用 jsonschema（draft 2020-12）",
        "   分别校验信封与清单，并逐条重算 acceptance 项。",
        "",
        "## ③ 产出物清单（文件名 → 要点）",
        "",
        "| 文件 | 要点 |",
        "|---|---|",
        "| `asset_manifest.json` | %d 项资产；`by_class`=%s；claims=0；sha256 `%s` |" % (
            n, json.dumps(manifest["counts"]["by_class"], ensure_ascii=False), msha),
        "| `kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims）；sha256 `%s` |" % rsha,
        "| `verification.json` | %d 项 acceptance 自检逐条 pass/fail + 重算哈希；`all_pass`=%s |" % (
            len(verdict["checks"]), verdict["all_pass"]),
        "| `report.md` | 本报告（由清单/信封/自检**程序化渲染**，无手抄）|",
        "| `figures/%s` | A) 资产类别×解析状态计数；B) 每个资产的字符跨度覆盖图 |" % png.name,
        "",
        "资产类别分布：`%s`。" % json.dumps(manifest["counts"]["by_class"], ensure_ascii=False),
        "",
        "## ④ 结果图",
        "",
        "![asset locator map](%s)" % fig_rel,
        "",
        "**图注**：A) 资产类别 × 解析状态（绿=源内已解析、红=引用未解析、灰=声明缺失）；B) 每个资产在 markdown 中的字符跨度",
        "（横轴=字符偏移，源文档 %d 字符）。两图直接由 `asset_manifest.json` 绘出，零手抄。" % manifest["source"]["chars"],
        cfg.get("figure_note", "红色柱不是缺陷而是**边界的正确表达**：这些路径属产出仓（ship-performance-platform），本包不得读写，故只能如实记 `referenced_unresolved`。"),
        "",
        "## ⑤ 证据定位表（资产 → 原文逐字片段，均由 `md[start_char:end_char]` 计算）",
        "",
        "| asset_id | 类别 | 解析 | 行 | 原文片段（逐字） |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "（完整 quote 与字符跨度见 `asset_manifest.json` 各 `locator`；平台可对每条 quote 做子串 + 行号独立复核。）",
        "",
        "## ⑥ 注意点与局限",
        "",
        "1. **登记 ≠ 抽取**：清单只回答「报告里有哪些可解析工件、在其中何处」，不回答「报告说了什么」。claims 为空是契约允许的完整结果。",
        "2. **不标 verified**：清单与信封里没有任何 `verified` 状态；验证由平台门计算，本工序只提供可复算的定位器与哈希。",
        "3. **图只有元数据**：报告记录 `figures[]` 共 %d 项均无 `png_base64` 载荷（0 字节），故只登记 name/caption + 正文出现位置，" % nfig,
        "   记 `metadata_only`（`resolution=referenced_unresolved`），**不宣称拿到图字节**。",
        *cfg.get("cross_repo_note", [
            "4. **跨仓引用不可解析**：报告引用的 `backend/...py`、`artifacts/cii_crosscheck_m6284/...py` 等属 ship-performance-platform 仓，",
            "   本工作树（TensorKnowledge）内不存在 → 全部 `referenced_unresolved`，并在 `resolution_check.detail` 写明原因，不做「大概存在」的推断。",
        ]),
        "5. **表格内容未复述**：%d 张表只登记几何（行×列）与字符跨度，避免把报表数字二次转写引入漂移。" % ntab,
        "6. **schema 口径**：仓库内 `schemas/asset_manifest.v1.schema.json` 把 `package_id/task_type/report_id`/`source.uri` 钉死为 wp-448-01 的包级取值，",
        "   自检时**仅放松这四处包级固定值**（`source.uri` 改为 `^tensor://reports/[0-9]+$`，其余约束照常生效）并如实记录在 `detail` 里，避免把「本包必挂」伪装成通过。",
        "",
        "## ⑦ 自检（逐条对照 acceptance）",
        "",
        "| acceptance 项 | 结果 | 细节 |",
        "|---|---|---|",
        *selfrows,
        "",
        "## 复现",
        "",
        "```bash",
        "python3 scripts/kf/kf01_register.py --preset %s build result verify figure report   # 一键复跑（全流程）" % cfg["package_id"],
        "```",
        "",
        "repro_cmd: `python3 scripts/kf/kf01_register.py --preset %s build result verify figure report`" % cfg["package_id"],
        "",
        "## 结果信封（唯一 json 代码块，原样提交）",
        "",
        "```json",
        json.dumps(result, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    text = "\n".join(lines)
    # contract hygiene: exactly one fenced json block
    if text.count("```json") != 1:
        raise SystemExit("report must contain exactly one ```json block, found %d" % text.count("```json"))
    rp = out_dir / "report.md"
    rp.write_text(text, encoding="utf-8")
    print("wrote %s" % rp.relative_to(REPO))

    payload = {
        "title": "KF-RESULT %s" % cfg["package_id"],
        "summary": "资产登记 %s / report_id=%s：%d 项资产（%s），source_hash 与契约逐字符一致；claims=0（登记不抽取）。" % (
            cfg["package_id"], cfg["report_id"], n, json.dumps(manifest["counts"]["by_resolution"], ensure_ascii=False)),
        "scenario_key": cfg["scenario_key"],
        "mission_id": cfg.get("mission_id", 15595),
        "tags": ["kf-wp:%s" % cfg["package_id"], "asset-registration", "lane-C", "TensorKnowledge",
                 "report_id:%s" % cfg["report_id"]],
        "markdown": text,
        "figures": [{
            "name": png.name,
            "caption": "%s asset inventory & locator coverage map (computed from asset_manifest.json)" % cfg["package_id"],
            "png_base64": base64.b64encode(png.read_bytes()).decode(),
        }],
    }
    pp = out_dir / "report_payload.json"
    pp.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote %s" % pp.relative_to(REPO))
    return text, payload


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preset", default="wp-7450-01")
    ap.add_argument("actions", nargs="*", default=["build", "result", "verify", "figure", "report"])
    a = ap.parse_args()
    cfg = dict(PRESETS[a.preset])
    out_dir = REPO / cfg["out_dir"]
    acts = set(a.actions)
    # canonical order: manifest -> envelope -> independent verification -> figure -> report
    if "build" in acts:
        build(cfg, out_dir, REPO)
    if "result" in acts:
        emit_result(cfg, out_dir)
    if "verify" in acts:
        verify(cfg, out_dir)
    png = None
    if "figure" in acts:
        png = render_figure(cfg, out_dir)
    if "report" in acts:
        if png is None:
            png = out_dir / "figures" / ("%s_asset_locator_map.png" % cfg["package_id"])
        render_report(cfg, out_dir, png)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
