#!/usr/bin/env python3
"""KF work package wp-14539-01 · task_type 01-asset-registration · report_id 14539 (single report).

Registers the *machine-parsable assets* of one report: the markdown document itself, every pipe
table, every fenced block, every path-like artefact reference in code spans, every declared figure,
and the platform ledger row the report cites. It does NOT extract knowledge: `claims` stays an
empty array (contract objective: register_assets=true, classify_report_type=false), and nothing is
marked `verified` - verification is computed by the platform gate.

Every locator is a byte span in the fetched markdown (`md[start:end] == quote`), so the platform's
independent sha256 + substring recheck necessarily agrees, and no number or sentence here is typed
from memory.

Usage (all steps):
    python3 scripts/kf/kf_wp14539_01_register.py build result verify figure report
Optional (explicit, network side effect):
    python3 scripts/kf/kf_wp14539_01_register.py publish
"""
from __future__ import annotations

import argparse
import base64
import bisect
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

CFG = {
    "package_id": "wp-14539-01",
    "report_id": "14539",
    "task_type": "01-asset-registration",
    "expected_hash": "d2dfc774d825389350411f5562f457cd13f44b17e3d8cf5b3c8470c80677b82b",
    "expected_chars": 14807,
    "title": "CASE-CAVITY-RE1000-FVM 第2轮：TensorFVM 方腔 Re=1000 收敛解与 <5% 基准对照（n=64 PASS）",
    "scenario_key": "CASE-CAVITY-RE1000-FVM",
    "mission_id": 15794,
    "out_dir": "docs/kf/wp-14539-01",
}

BACKTICK_RE = re.compile(r"`([^`\n]+)`")
# path-like: relative (>=1 directory component) or absolute; braces/parens terminate a match
PATH_RE = re.compile(
    r"(?:\.\./)?(?:[A-Za-z0-9_.\-]+/)+[A-Za-z0-9_.\-]*|/[A-Za-z0-9_.\-]+(?:/[A-Za-z0-9_.\-]+)*"
)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


# --------------------------------------------------------------------- platform I/O
def _req(url, token=None, data=None, ctype="application/json", timeout=60):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode()
        return r.status, (json.loads(body) if body else None)


def login():
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    creds = {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    try:
        _, d = _req(base + "/auth/login", data=json.dumps(creds).encode())
    except urllib.error.HTTPError:
        _, d = _req(base + "/auth/login", data=urllib.parse.urlencode(creds).encode(),
                    ctype="application/x-www-form-urlencoded")
    tok = (d or {}).get("access_token") or (d or {}).get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d or {}))
    return base, tok


def fetch_report(base, token, report_id):
    _, d = _req(base + "/tensor/reports/" + report_id, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    if str((d or {}).get("id")) != str(report_id):
        raise SystemExit("report_id mismatch: requested %r got %r" % (report_id, (d or {}).get("id")))
    md = (d or {}).get("markdown")
    if not isinstance(md, str) or not md:
        raise SystemExit("report %s has no markdown field" % report_id)
    return d, md


# --------------------------------------------------------------------- source geometry
class Source:
    """Fetched markdown + char/line geometry, so every locator is computed, never guessed."""

    def __init__(self, md: str):
        self.md = md
        self.lines = md.split("\n")
        self.starts = [0]
        for m in re.finditer("\n", md):
            self.starts.append(m.end())

    def line_of(self, pos: int) -> int:
        return bisect.bisect_right(self.starts, pos) - 1

    def line_span(self, i: int) -> tuple[int, int]:
        s = self.starts[i]
        e = self.starts[i + 1] - 1 if i + 1 < len(self.starts) else len(self.md)
        return s, e

    def section_of(self, pos: int) -> str:
        i = self.line_of(pos)
        for j in range(i, -1, -1):
            m = HEADING_RE.match(self.lines[j])
            if m:
                return "%s %s" % ("#" * len(m.group(1)), m.group(2).strip())
        return "(preamble)"

    def locator(self, start: int, end: int, extra: dict | None = None) -> dict:
        quote = self.md[start:end]
        loc = {
            "method": "char_span",
            "start_char": start,
            "end_char": end,
            "start_line": self.line_of(start) + 1,
            "end_line": self.line_of(end - 1) + 1,
            "quote": quote,
            "unique": self.md.count(quote) == 1,
        }
        if extra:
            loc.update(extra)
        return loc


def by_class(assets):
    out = {}
    for a in assets:
        out[a["asset_class"]] = out.get(a["asset_class"], 0) + 1
    return dict(sorted(out.items()))


def by_resolution(assets):
    out = {}
    for a in assets:
        out[a["resolution"]] = out.get(a["resolution"], 0) + 1
    return dict(sorted(out.items()))
# --------------------------------------------------------------------- scanners
def scan_tables(src: Source):
    out, i = [], 0
    while i < len(src.lines):
        if src.lines[i].startswith("|"):
            j = i
            while j + 1 < len(src.lines) and src.lines[j + 1].startswith("|"):
                j += 1
            s, _ = src.line_span(i)
            _, e = src.line_span(j)
            cols = src.lines[i].count("|") - 1
            out.append({
                "asset_class": "report_table",
                "label": "pipe table @ lines %d-%d" % (i + 1, j + 1),
                "in_report_section": src.section_of(s),
                "locator": src.locator(s, e),
                "resolution": "resolved_in_source",
                "resolution_check": {
                    "check": "pipe-table block occupies the recorded char span and is byte-identical there",
                    "result": "resolved",
                    "detail": "%d rows x %d columns (geometry only; cell values are not extracted)" % (j - i + 1, cols),
                },
                "rows": j - i + 1,
                "columns": cols,
                "note": "in-report data table; registered as an addressable block, contents not transcribed.",
            })
            i = j + 1
        else:
            i += 1
    return out


def scan_fences(src: Source):
    out, i = [], 0
    while i < len(src.lines):
        if src.lines[i].strip().startswith("```"):
            lang = src.lines[i].strip()[3:].strip()
            j = i + 1
            while j < len(src.lines) and not src.lines[j].strip().startswith("```"):
                j += 1
            last = min(j, len(src.lines) - 1)
            s, _ = src.line_span(i)
            _, e = src.line_span(last)
            body = [ln for ln in src.lines[i + 1:last] if ln.strip()]
            out.append({
                "asset_class": "repro_command_block",
                "label": "%s fence @ lines %d-%d" % (lang or "plain", i + 1, last + 1),
                "in_report_section": src.section_of(s),
                "locator": src.locator(s, e),
                "resolution": "resolved_in_source",
                "resolution_check": {
                    "check": "fenced block present at the recorded char span",
                    "result": "resolved",
                    "detail": "%d non-empty body line(s), language=%s" % (len(body), lang or "plain"),
                },
                "language": lang or "plain",
                "note": "reproduction block as written by the author; this work package does not execute it.",
            })
            i = last + 1
        else:
            i += 1
    return out


def iter_code_spans(src: Source):
    """Yield (origin, start, end) of every inline-code span and every fenced block, in document order."""
    fence_ranges, i = [], 0
    while i < len(src.lines):
        if src.lines[i].strip().startswith("```"):
            j = i + 1
            while j < len(src.lines) and not src.lines[j].strip().startswith("```"):
                j += 1
            s, _ = src.line_span(i)
            _, e = src.line_span(min(j, len(src.lines) - 1))
            fence_ranges.append((s, e))
            i = j + 1
        else:
            i += 1
    for m in BACKTICK_RE.finditer(src.md):
        if any(s <= m.start() < e for s, e in fence_ranges):
            continue
        yield ("inline_code", m.start(1), m.end(1))
    for s, e in fence_ranges:
        yield ("code_fence", s, e)


def is_path_asset(token: str) -> bool:
    """Accept a token as a path-like artefact reference; reject math slashes (``L/2``, ``p/rho``) and
    glob fragments (``fields/Re1000_n`` from ``fields/Re1000_n{32,64,128}.pt``)."""
    t = token.rstrip("/")
    comps = [c for c in t.split("/") if c]
    if not comps:
        return False
    last = comps[-1]
    if re.fullmatch(r"[A-Za-z0-9_.\-]{1,}\.[A-Za-z0-9]{1,6}", last):
        return True                                   # file with an extension
    if t.startswith("/") and re.fullmatch(r"[A-Za-z0-9_.\-]{2,}", last):
        return True                                   # absolute path
    if token.endswith("/") and len(comps) >= 2 and re.fullmatch(r"[A-Za-z0-9_.\-]{3,}", last):
        return True                                   # relative directory with trailing slash
    if len(comps) >= 2 and "-" in last and re.fullmatch(r"[A-Za-z0-9_.\-]{3,}", last):
        return True                                   # kebab-case directory cited without slash
    return False


def scan_paths(src: Source, worktree: Path):
    out, seen = [], set()
    md = src.md
    for origin, s, e in iter_code_spans(src):
        for m in PATH_RE.finditer(md, s, e):
            token = m.group(0)
            if token.lower().endswith(".png"):
                continue  # folded into the declared_figure assets
            ts = m.start()
            key = (token, src.line_of(ts))
            if key in seen:
                continue
            seen.add(key)
            probe = token.rstrip("/")
            if not is_path_asset(token):
                continue
            outside = probe.startswith("/")
            target = Path(probe) if outside else (worktree / probe)
            if not outside and target.is_file():
                status, result = "resolved_in_source", "resolved"
                detail = "file present in this worktree; sha256=%s" % hashlib.sha256(target.read_bytes()).hexdigest()
            elif not outside and target.is_dir():
                status, result = "resolved_in_source", "present"
                detail = "directory present in this worktree (%d entries)" % len(list(target.iterdir()))
            elif outside:
                status, result = "referenced_unresolved", "unresolved"
                detail = ("absolute path outside this worktree (host existence=%s); resolution is restricted to "
                          "the worktree, so nothing is claimed about its contents" % target.exists())
            else:
                status, result = "referenced_unresolved", "unresolved"
                detail = ("absent from this worktree (%s); the producer repository holds the bytes and is out of "
                          "scope for this package - not guessed, not fetched" % worktree.name)
            if md[m.end():m.end() + 1] == "{":
                cls = "artifact_bundle"
            elif probe.endswith((".pt", ".npz", ".h5", ".npy")):
                cls = "dataset_checkpoint"
            else:
                cls = "code_or_artifact_path"
            out.append({
                "asset_class": cls,
                "label": "%s (line %d)" % (probe, src.line_of(ts) + 1),
                "in_report_section": src.section_of(ts),
                "locator": src.locator(ts, ts + len(token), {"token": token}),
                "resolution": status,
                "resolution_check": {"check": "worktree membership probe (isfile/isdir) on the cited path",
                                     "result": result, "detail": detail},
                "path_reference": probe,
                "origin": origin,
                "note": "path-like reference harvested from %s; resolution is limited to this worktree." % origin,
            })
    return out
def scan_figures(src: Source, meta: dict):
    out = []
    for n, fig in enumerate(meta.get("figures") or []):
        name = fig.get("name") or "figure[%d]" % n
        b64 = fig.get("png_base64") or ""
        try:
            blob = base64.b64decode(b64) if b64 else b""
        except Exception:  # noqa: BLE001
            blob = b""
        pos = src.md.find(name)
        if pos >= 0:
            loc = src.locator(pos, pos + len(name), {"token": name})
            section = src.section_of(pos)
        else:
            loc = {"method": "document", "start_char": 0, "end_char": len(src.md),
                   "start_line": 1, "end_line": len(src.lines), "quote": src.lines[0], "unique": True}
            section = "(record field figures; not named in markdown)"
        detail = ("figures[%d] declares name+caption only: png_base64 is empty (%d chars), so no byte payload "
                  "and no byte hash exist" % (n, len(b64))) if not blob else (
                  "figures[%d] carries %d payload bytes, sha256=%s" % (n, len(blob), hashlib.sha256(blob).hexdigest()))
        out.append({
            "asset_class": "declared_figure",
            "label": name,
            "in_report_section": section,
            "locator": loc,
            "resolution": "referenced_unresolved" if not blob else "resolved_in_source",
            "resolution_check": {"check": "record.figures[i].name located in markdown + png_base64 payload length",
                                 "result": "unresolved" if not blob else "resolved", "detail": detail},
            "figure_uri": "tensor://reports/%s#figures[%d]" % (meta.get("id"), n),
            "caption": fig.get("caption"),
            "payload_bytes": len(blob) or None,
            "payload_sha256": hashlib.sha256(blob).hexdigest() if blob else None,
            "note": "figure declared by the report record; bytes are not served, so only the declaration is registered.",
        })
    return out


def scan_ledger_rows(src: Source):
    """Platform ledger rows cited as inline code - registered as identities, never read or written."""
    out, seen = [], set()
    for m in BACKTICK_RE.finditer(src.md):
        token = m.group(1).strip()
        if not re.fullmatch(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+", token) or token in seen:
            continue
        line = src.lines[src.line_of(m.start(1))]
        if "row" not in line and "table" not in line:
            continue
        seen.add(token)
        out.append({
            "asset_class": "platform_ledger_reference",
            "label": token,
            "in_report_section": src.section_of(m.start(1)),
            "locator": src.locator(m.start(1), m.end(1), {"token": token}),
            "resolution": "referenced_unresolved",
            "resolution_check": {
                "check": "ledger row identity asserted in markdown (read back byte-identically)",
                "result": "unresolved",
                "detail": "row key registered as cited; ledger membership is neither re-read nor written here",
            },
            "note": "cross-reference to a platform ledger row; no ledger read/mutation happens in this package.",
        })
    return out


# --------------------------------------------------------------------- build
def build(cfg, out_dir: Path, worktree: Path):
    base, token = login()
    meta, md = fetch_report(base, token, cfg["report_id"])
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != cfg["expected_hash"]:
        raise SystemExit("SOURCE HASH MISMATCH: contract=%s actual=%s" % (cfg["expected_hash"], digest))
    if len(md) != cfg["expected_chars"]:
        raise SystemExit("SOURCE CHAR COUNT MISMATCH: contract=%d actual=%d" % (cfg["expected_chars"], len(md)))

    src = Source(md)
    title_line = src.lines[0]
    assets = [{
        "asset_class": "report_document",
        "label": "markdown of report %s" % cfg["report_id"],
        "in_report_section": "(whole document)",
        "locator": {"method": "document", "start_char": 0, "end_char": len(md),
                    "start_line": 1, "end_line": len(src.lines),
                    "quote": title_line, "unique": md.count(title_line) == 1},
        "resolution": "resolved_in_source",
        "resolution_check": {
            "check": "GET /api/v1/tensor/reports/%s returned markdown that re-hashes to the contract value"
                     % cfg["report_id"],
            "result": "resolved",
            "detail": "%d chars / %d utf-8 bytes / sha256 %s" % (len(md), len(raw), digest),
        },
        "note": "registered source document; whole-document span is 0..len(markdown).",
    }]
    assets += scan_tables(src)
    assets += scan_fences(src)
    assets += scan_paths(src, worktree)
    assets += scan_figures(src, meta)
    assets += scan_ledger_rows(src)
    for n, a in enumerate(assets):
        a["asset_id"] = "A%02d" % n

    counts = {
        "assets": len(assets),
        "by_class": by_class(assets),
        "by_resolution": by_resolution(assets),
        "resolved_in_source": sum(1 for a in assets if a["resolution"] == "resolved_in_source"),
        "referenced_unresolved": sum(1 for a in assets if a["resolution"] == "referenced_unresolved"),
        "declared_absent": sum(1 for a in assets if a["resolution"] == "declared_absent"),
        "tables": sum(1 for a in assets if a["asset_class"] == "report_table"),
        "fenced_blocks": sum(1 for a in assets if a["asset_class"] == "repro_command_block"),
        "figures_declared": len(meta.get("figures") or []),
        "claims": 0,
    }
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": cfg["package_id"],
        "task_type": cfg["task_type"],
        "report_id": cfg["report_id"],
        "source": {
            "uri": "tensor://reports/%s" % cfg["report_id"],
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": cfg["title"],
            "scenario_key": meta.get("scenario_key") or cfg["scenario_key"],
            "platform_figures": [{"name": f.get("name"), "caption": f.get("caption"),
                                  "png_base64_len": len(f.get("png_base64") or "")}
                                 for f in (meta.get("figures") or [])],
            "platform_tags": meta.get("tags") or [],
            "record_title_served": meta.get("title"),
            "mission_id": meta.get("mission_id"),
            "retrieved_via": "GET %s/tensor/reports/%s (Bearer)" % (base, cfg["report_id"]),
        },
        "counts": counts,
        "assets": assets,
        "claims": [],
        "integrity": {
            "quote_uniqueness": {
                "total": len(assets),
                "unique": sum(1 for a in assets if a["locator"]["unique"]),
                "not_unique": [a["asset_id"] for a in assets if not a["locator"]["unique"]],
            },
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == cfg["expected_hash"],
            "char_count_matches_contract": len(md) == cfg["expected_chars"],
        },
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "source").mkdir(parents=True, exist_ok=True)
    (out_dir / "source" / "markdown.txt").write_text(md, encoding="utf-8")
    keep = {k: meta.get(k) for k in ("id", "title", "scenario_key", "mission_id", "tags")}
    keep["figures"] = [{"name": f.get("name"), "caption": f.get("caption"),
                        "png_base64_len": len(f.get("png_base64") or "")}
                       for f in (meta.get("figures") or [])]
    (out_dir / "source" / "record.json").write_text(
        json.dumps(keep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    mp = out_dir / "asset_manifest.json"
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets, sha256 %s)" % (mp.relative_to(REPO), len(assets),
                                               hashlib.sha256(mp.read_bytes()).hexdigest()))
    return manifest, mp, md, src, meta


# --------------------------------------------------------------------- envelope
def emit_result(cfg, out_dir: Path):
    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    result = {
        "package_id": cfg["package_id"],
        "task_type": cfg["task_type"],
        "report_id": cfg["report_id"],
        "provenance": {
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_field": "markdown",
            "producer": "kf-worker m15794 (TensorKnowledge) · scripts/kf/kf_wp14539_01_register.py",
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "notes": "single-report scope; assets only, no extraction; claims intentionally empty",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    rp = out_dir / "kf_result.json"
    rp.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (sha256 %s)" % (rp.relative_to(REPO), hashlib.sha256(rp.read_bytes()).hexdigest()))
    return result, rp
# --------------------------------------------------------------------- independent self-check
def verify(cfg, out_dir: Path, worktree: Path):
    import jsonschema

    mp = out_dir / "asset_manifest.json"
    rp = out_dir / "kf_result.json"
    manifest = json.loads(mp.read_text(encoding="utf-8"))
    result = json.loads(rp.read_text(encoding="utf-8"))
    md_path = out_dir / "source" / "markdown.txt"
    src_md = md_path.read_text(encoding="utf-8") if md_path.is_file() else None
    checks = {}

    checks["valid_json"] = {
        "pass": isinstance(manifest, dict) and isinstance(result, dict) and src_md is not None,
        "detail": "manifest + envelope parse via json.loads; stored source markdown byte copy present=%s"
                  % (src_md is not None),
    }

    env_schema = json.loads((worktree / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    env_errs = sorted(jsonschema.Draft202012Validator(env_schema).iter_errors(result), key=lambda e: list(e.path))
    man_schema = json.loads((worktree / "schemas/asset_manifest.v1.schema.json").read_text(encoding="utf-8"))
    # Retarget the package-level pins of the in-repo schema to THIS package; no structural constraint is
    # loosened (the shipped consts simply name a different package), and the change is reported verbatim.
    man_schema["properties"]["package_id"]["const"] = cfg["package_id"]
    man_schema["properties"]["report_id"]["const"] = cfg["report_id"]
    man_schema["properties"]["source"]["properties"]["uri"]["const"] = "tensor://reports/%s" % cfg["report_id"]
    man_schema["title"] = "asset_manifest.v1 retargeted to %s" % cfg["package_id"]
    man_errs = sorted(jsonschema.Draft7Validator(man_schema).iter_errors(manifest), key=lambda e: list(e.path))
    checks["schema_pass"] = {
        "pass": not env_errs and not man_errs,
        "detail": "kf_result.v1 (draft 2020-12): %d error(s) %s | asset_manifest.v1 (package pins retargeted, "
                  "structure untouched): %d error(s) %s" % (
                      len(env_errs), [e.message[:90] for e in env_errs[:4]],
                      len(man_errs), [e.message[:90] for e in man_errs[:4]]),
    }

    bad, src_loc = [], (Source(src_md) if src_md else None)
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if not src_md:
            bad.append([a["asset_id"], "no_source_copy"])
            continue
        if loc["method"] == "document":
            if not (s == 0 and e == len(src_md) and q in src_md):
                bad.append([a["asset_id"], "document_span"])
            continue
        if not (0 <= s < e <= len(src_md)) or src_md[s:e] != q or q not in src_md:
            bad.append([a["asset_id"], "char_span_or_quote"])
            continue
        if src_loc.line_of(s) + 1 != loc["start_line"] or src_loc.line_of(e - 1) + 1 != loc["end_line"]:
            bad.append([a["asset_id"], "line_map"])
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": "re-resolved %d locators against the stored markdown bytes (char span + verbatim quote + "
                  "1-based line map); failures=%s" % (len(manifest["assets"]), bad),
    }

    actual = hashlib.sha256(src_md.encode("utf-8")).hexdigest() if src_md is not None else "unavailable"
    checks["source_hash_matches"] = {
        "pass": actual == manifest["source"]["hash"] == cfg["expected_hash"]
        and result["provenance"]["source_hash"] == "sha256:" + actual,
        "detail": "recomputed=%s manifest=%s envelope=%s contract=%s" % (
            actual, manifest["source"]["hash"], result["provenance"]["source_hash"], cfg["expected_hash"]),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    keys = [(a["asset_class"], a["label"]) for a in manifest["assets"]]
    spans = [(a["locator"]["start_char"], a["locator"]["end_char"]) for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": bool(ids) and len(ids) == len(set(ids)) and len(keys) == len(set(keys))
        and len(spans) == len(set(spans)),
        "detail": "assets=%d; unique asset_id=%d, unique (class,label)=%d, unique (start,end) span=%d "
                  "(the same path cited on different lines is a distinct occurrence, disambiguated by line + offset)"
                  % (len(ids), len(set(ids)), len(set(keys)), len(set(spans))),
    }

    claims = manifest.get("claims", [])
    viol = [c.get("claim_id") for c in claims if not c.get("evidence") and c.get("status") != "unresolved"]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not viol,
        "detail": "claims=%d violating=%d (empty array: satisfied vacuously, as the package notes allow)" % (
            len(claims), len(viol)),
    }
    checks["do_not_mark_claims_as_verified"] = {
        "pass": all(c.get("status") != "verified" for c in claims),
        "detail": "claims=%d, none carries status='verified'; no manifest field claims verification" % len(claims),
    }
    checks["report_id_scoped"] = {
        "pass": manifest["report_id"] == result["report_id"] == cfg["report_id"],
        "detail": "single report_id=%s; the builder rejects any other id returned by the API" % cfg["report_id"],
    }
    checks["outputs_match_file"] = {
        "pass": result["outputs"]["asset_manifest.json"] == manifest,
        "detail": "envelope outputs['asset_manifest.json'] equals the committed manifest object "
                  "(file sha256 %s)" % hashlib.sha256(mp.read_bytes()).hexdigest(),
    }
    uniq = manifest["integrity"]["quote_uniqueness"]
    dup_offsets = [a["locator"]["start_char"] for a in manifest["assets"] if not a["locator"]["unique"]]
    checks["duplicate_quotes_disambiguated_by_offset"] = {
        "pass": len(dup_offsets) == len(set(dup_offsets)),
        "detail": "%d/%d quotes occur exactly once; the %d repeated quotes (short tokens / recurring paths) are "
                  "each pinned to a distinct char offset, so every locator resolves to exactly one position"
                  % (uniq["unique"], uniq["total"], uniq["total"] - uniq["unique"]),
    }

    verdict = {
        "package_id": cfg["package_id"],
        "report_id": cfg["report_id"],
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(mp.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(mp.read_bytes()).hexdigest(),
        "envelope_sha256": hashlib.sha256(rp.read_bytes()).hexdigest(),
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks.values()),
        "scope_note": "self-check by the producing agent; the authoritative verification is the platform gate.",
    }
    (out_dir / "verification.json").write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    print(json.dumps({k: v["pass"] for k, v in checks.items()}, ensure_ascii=False))
    print("all_pass=%s" % verdict["all_pass"])
    return verdict
# --------------------------------------------------------------------- figure
def render_figure(cfg, out_dir: Path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    assets = manifest["assets"]
    classes = sorted({a["asset_class"] for a in assets},
                     key=lambda c: (-sum(1 for a in assets if a["asset_class"] == c), c))
    color = {"resolved_in_source": "#2e7d32", "referenced_unresolved": "#c62828", "declared_absent": "#616161"}
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8.0), gridspec_kw={"height_ratios": [1, 1.3]})

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
    ax1.invert_yaxis()
    ax1.set_xlabel("assets")
    ax1.set_title("A) asset inventory: class x resolution (n=%d, report %s)" % (len(assets), manifest["report_id"]),
                  fontsize=10)
    ax1.legend(fontsize=7, loc="lower right")
    ax1.grid(axis="x", alpha=0.3)

    for a in assets:
        y = classes.index(a["asset_class"])
        s, e = a["locator"]["start_char"], a["locator"]["end_char"]
        ax2.barh(y, max(e - s, 1), left=s, height=0.6, color=color[a["resolution"]], alpha=0.85)
        if e - s > manifest["source"]["chars"] * 0.02:
            ax2.text(s, y + 0.42, a["asset_id"], fontsize=6)
    ax2.set_yticks(ys)
    ax2.set_yticklabels(classes, fontsize=8)
    ax2.invert_yaxis()
    ax2.set_xlim(0, manifest["source"]["chars"])
    ax2.set_xlabel("character offset in markdown (source: %d chars / %d utf-8 bytes; sha256 %s...)"
                   % (manifest["source"]["chars"], manifest["source"]["bytes_utf8"],
                      manifest["source"]["hash"][:12]))
    ax2.set_title("B) locator coverage: char span of every registered asset (computed from md[start:end])",
                  fontsize=10)
    ax2.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out = out_dir / "figures" / ("%s_asset_locator_map.png" % cfg["package_id"])
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print("wrote %s" % out.relative_to(REPO))
    return out
# --------------------------------------------------------------------- report
def render_report(cfg, out_dir: Path, png: Path):
    manifest = json.loads((out_dir / "asset_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((out_dir / "kf_result.json").read_text(encoding="utf-8"))
    verdict = json.loads((out_dir / "verification.json").read_text(encoding="utf-8"))
    assets = manifest["assets"]
    n = len(assets)
    counts = manifest["counts"]
    msha = hashlib.sha256((out_dir / "asset_manifest.json").read_bytes()).hexdigest()
    rsha = hashlib.sha256((out_dir / "kf_result.json").read_bytes()).hexdigest()
    fig_rel = png.relative_to(out_dir).as_posix()
    rid = cfg["report_id"]

    def cell(text, limit=120):
        t = str(text).replace("\n", " ⏎ ").replace("|", "\\|")
        return t if len(t) <= limit else t[:limit - 1] + "…"

    rows = ["| `%s` | %s | %s | %d–%d | `%s` |" % (
        a["asset_id"], a["asset_class"], a["resolution"], a["locator"]["start_line"],
        a["locator"]["end_line"], cell(a["locator"]["quote"])) for a in assets]

    class_rows = []
    for cls, k in counts["by_class"].items():
        got = {r: sum(1 for a in assets if a["asset_class"] == cls and a["resolution"] == r)
               for r in counts["by_resolution"]}
        class_rows.append("| `%s` | %d | %d | %d | %d |" % (
            cls, k, got.get("resolved_in_source", 0), got.get("referenced_unresolved", 0),
            got.get("declared_absent", 0)))

    selfrows = ["| `%s` | %s | %s |" % (k, "✅ pass" if v["pass"] else "❌ fail", cell(v["detail"], 170))
                for k, v in verdict["checks"].items()]

    paths = [a for a in assets if a["asset_class"] in ("code_or_artifact_path", "artifact_bundle", "dataset_checkpoint")]
    resolved_paths = [a for a in paths if a["resolution"] == "resolved_in_source"]
    tables = [a for a in assets if a["asset_class"] == "report_table"]
    figs = [a for a in assets if a["asset_class"] == "declared_figure"]
    ledger = [a for a in assets if a["asset_class"] == "platform_ledger_reference"]
    uniq = manifest["integrity"]["quote_uniqueness"]

    lines = [
        "# KF-RESULT %s" % cfg["package_id"],
        "",
        "- task_type `%s` · report_id `%s` · lane B · 分层 `FVM|%s`" % (
            cfg["task_type"], rid, cfg["scenario_key"]),
        "- 源：`tensor://reports/%s`，字段 `markdown`，sha256 `%s`，%d 字符 / %d 字节" % (
            rid, manifest["source"]["hash"], manifest["source"]["chars"], manifest["source"]["bytes_utf8"]),
        "- 一句话结论：登记 **%d 项**可解析资产（`%s`），源哈希与契约逐字节一致；**未做抽取**（`claims=[]`）；**未标 verified**。" % (
            n, json.dumps(counts["by_resolution"], ensure_ascii=False)),
        "",
        "> 本报告由 `scripts/kf/kf_wp14539_01_register.py report` 从 `asset_manifest.json` / `kf_result.json` / "
        "`verification.json` **程序化渲染**：表中每个数字都由清单计算得出，每条引文都是 `md[start:end]` 切片。",
        "",
        "## ① 本工序做了什么",
        "",
        "只做一件事：把 report_id=%s 的源文档登记为**可寻址资产清单**。不抽取、不分类、不生成知识条目、不给结论。" % rid,
        "",
        "1. 经平台接口取回 markdown，独立重算 sha256 并与契约值比对——不一致立即终止，绝不带病产出。",
        "2. 从源字节扫描五类可解析资产：文档本身、连续 `|` 行构成的表格、围栏代码块、代码跨度中的路径型工件引用、"
        "记录字段 `figures[]` 声明的图；另登记报告以 inline code 引用的平台台账行身份。",
        "3. 每个资产给一个字节跨度定位器（`start_char` / `end_char` / `start_line` / `end_line` / `quote` / `unique`），"
        "`quote` 直接取 `md[start:end]`，因此不存在手抄环节，平台子串独立重算必然成立。",
        "4. 本地解析只做「本工作树内是否存在」的探针：命中记 `resolved_in_source` 并附文件 sha256；未命中如实记 "
        "`referenced_unresolved`，不猜、不去别的仓捞。",
        "5. 结果信封 `kf_result.json`：`outputs['asset_manifest.json']` 即清单全文对象（与落盘文件逐字段相同）。",
        "6. 用 jsonschema 独立自检信封与清单，并逐条重算 acceptance 八项 → `verification.json`（自检非终判，终判归平台门）。",
        "",
        "范围边界：只读 report_id=%s 一份报告，未读写任何其它 report_id；未改上游产物；未写 `verified`。" % rid,
        "",
        "## ② 怎么做的（步骤 / 工具 / 关键设置）",
        "",
        "| 环节 | 做法 |",
        "|---|---|",
        "| 取源 | `GET $TENSOR_API_BASE/tensor/reports/%s`（Bearer，$TENSOR_AGENT_USER 登录）；响应 id 与契约不符即拒绝产出 |" % rid,
        "| 完整性 | `hashlib.sha256(markdown.encode('utf-8'))` 与契约 `%s` 比对，另校 `chars=%d` |" % (
            cfg["expected_hash"], cfg["expected_chars"]),
        "| 行/列几何 | `Source`：`split('\\n')` + 累计偏移，`line_of(pos)` 走 `bisect`；对外行号 1-based |",
        "| 表格 | 连续以 `|` 开头的行合并为一块，`quote` = 整块原文；只记 `rows × columns` 几何，不复述单元格 |",
        "| 围栏 | ``` 到配对 ``` 为整块，记语言标签与非空行数；其中命令不执行 |",
        "| 路径引用 | 正则 `(?:\\.\\./)?(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.-]*` 只作用于代码跨度（行内代码 + 围栏）；`.png` 交由图资产去重；"
        "紧跟 `{` 者记 `artifact_bundle`，`.pt/.npz/.h5/.npy` 记 `dataset_checkpoint` |",
        "| 图 | `record.figures[i]`：名字在 markdown 中定位；`png_base64` 为空则只登记**声明**，`payload_bytes=null` |",
        "| 台账行 | inline code 中形如 `KEY-WITH-DASHES` 且所在行含 `row`/`table` 者，登记为身份引用（不读台账） |",
        "| 自检 | `jsonschema` draft 2020-12 校信封、draft-07 校清单（仅把仓库内 schema 的**包级固定值**重定向到本包，结构约束一条未放松）；"
        "再逐条重算定位器 / 哈希 / 去重 / claims 状态 |",
        "| 出图 | matplotlib(Agg)，全部数据取自清单字段 |",
        "",
        "关键设置：`report_id` 硬锁 %s；`claims` 固定空数组（`objective.classify_report_type=false`，登记不抽取）；"
        "`resolution` 三值口径 `resolved_in_source` / `referenced_unresolved` / `declared_absent`；"
        "quote 唯一性逐条统计写入 `integrity.quote_uniqueness`。" % rid,
        "",
        "## ③ 产出物清单（输出文件名 → 要点）",
        "",
        "| 文件 | 要点 |",
        "|---|---|",
        "| `asset_manifest.json` | %d 项资产；`by_class`=%s；`by_resolution`=%s；`claims=0`；sha256 `%s` |" % (
            n, json.dumps(counts["by_class"], ensure_ascii=False),
            json.dumps(counts["by_resolution"], ensure_ascii=False), msha),
        "| `kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs / claims）；sha256 `%s` |" % rsha,
        "| `verification.json` | %d 项 acceptance 自检逐条 pass/fail + 重算哈希；`all_pass=%s`；manifest sha256 `%s` |" % (
            len(verdict["checks"]), verdict["all_pass"], verdict["manifest_sha256"]),
        "| `report.md` / `report_payload.json` | 本报告 + 可直接 POST 到 `/tensor/reports` 的载荷 |",
        "| `figures/%s` | A) 资产类别 × 解析状态计数；B) 每个资产的字符跨度覆盖图 |" % png.name,
        "| `source/markdown.txt` | 源 markdown 的逐字节副本（%d 字节），供离线复核定位器与哈希 |" % manifest["source"]["bytes_utf8"],
        "| `source/record.json` | 源记录元数据（title / scenario_key / mission_id / tags / figures 声明） |",
        "",
        "资产类别分布：",
        "",
        "| asset_class | 合计 | resolved_in_source | referenced_unresolved | declared_absent |",
        "|---|---|---|---|---|",
        *class_rows,
        "",
        "计数覆盖：表格 %d 个 · 围栏块 %d 个 · `figures[]` 声明 %d 张 · 路径型引用 %d 条（本工作树内可解析 %d 条）· 台账行引用 %d 条。" % (
            len(tables), counts["fenced_blocks"], len(figs), len(paths), len(resolved_paths), len(ledger)),
        "",
        "## ④ 结果图",
        "",
        "![asset locator map](%s)" % fig_rel,
        "",
        "**图注**：A) 资产类别 × 解析状态（绿=源内已解析，红=引用未解析）；B) 每个资产在 markdown 中的字符跨度"
        "（横轴=字符偏移，源文档 %d 字符）。两张子图都由 `asset_manifest.json` 字段直接绘出，未手抄数字。" % manifest["source"]["chars"],
        "A 图红色部分不是缺陷而是边界的正确表达：这些路径属产出仓 TensorFVM，本包不得读写，只能如实记 `referenced_unresolved`。",
        "",
        "## ⑤ 证据定位表（asset_id / 字段 → 原文逐字片段）",
        "",
        "| asset_id | 类别 | 解析 | 行 | 原文片段（`md[start:end]`，逐字） |",
        "|---|---|---|---|---|",
        *rows,
        "",
        "（完整 quote 与字符跨度见 `asset_manifest.json` 各 `locator`；平台可对每条 quote 做子串 + 行号独立复核。）",
        "",
    ]
    lines += [
        "## ⑥ 注意点与局限",
        "",
        "1. **登记 ≠ 抽取**：清单只回答「有哪些可解析工件、在原文何处」，不回答「报告结论是什么」。`claims=[]` 是契约允许的完整结果，"
        "不是漏做；`objective.classify_report_type=false`，故未做报告类型判定。",
        "2. **不标 verified**：清单与信封里没有任何 `verified` 状态；`verification.json` 是产出自检，终判归平台门。",
        "3. **图只有声明**：`record.figures` %d 项的 `png_base64` 长度均为 0，故只登记 name/caption 与正文出现位置、`payload_bytes=null`，"
        "不宣称拿到图字节，也不伪造字节哈希。" % len(figs),
        "4. **跨仓引用不解析**：报告引用的 `scripts/…`、`src/tensorfvm/…`、`artifacts/…`、`docs/…`、`fields/…` 属产出仓 TensorFVM，"
        "本工作树（TensorKnowledge）内不存在 → 全部 `referenced_unresolved`，理由写在 `resolution_check.detail`，不做「大概存在」的推断。",
        "5. **表格内容不复述**：%d 个表格只登记几何（行×列）与字符跨度，避免把报表数字二次转写引入漂移；数字的唯一权威仍是源报告。" % len(tables),
        "6. **路径扫描口径**：只扫代码跨度（行内代码 + 围栏），不扫纯文本散文中的路径；花括号展开的产物清单（`artifacts/…/{a,b,c}`）"
        "记为一个 `artifact_bundle`，不逐成员展开——有意保守：宁可少登，不臆造。",
        "7. **schema 口径**：仓库内 `schemas/asset_manifest.v1.schema.json` 是 wp-448-01 时代的文件，把 `package_id`/`report_id`/`source.uri` "
        "钉成该包取值；自检时仅把这四处**包级固定值**重定向到本包（结构与其余约束原样），并在 `schema_pass.detail` 如实写明，"
        "未把「本包必挂」伪装成通过。",
        "8. **report_id 互不覆盖**：全流程只读 %s 一份；`fetch_report()` 对 API 返回 id 做硬校验，读到别的 id 立即终止。" % rid,
        "",
        "### 误差判定（本工序的精度口径）",
        "",
        "本工序不产生物理量，不存在「vs 实验/解析解误差」；其可判定量是**登记完整性**：",
        "",
        "| 判据 | 期望 | 实得 | 偏差 |",
        "|---|---|---|---|",
        "| markdown sha256 | `%s`（契约） | `%s` | 0（逐字节相同） |" % (cfg["expected_hash"], manifest["source"]["hash"]),
        "| 字符数 | %d（契约） | %d | 0 |" % (cfg["expected_chars"], manifest["source"]["chars"]),
        "| quote 可唯一定位 | 每条 quote 指向唯一位置 | 文本唯一 %d/%d，其余 %d 条靠互不相同的字符偏移消歧 | 0 |" % (
            uniq["unique"], uniq["total"], uniq["total"] - uniq["unique"]),
        "| 定位器可解析 | %d/%d | %d/%d | 0 |" % (
            n, n, n if verdict["checks"]["source_locator_resolvable"]["pass"] else 0, n),
        "",
        "结论：**源哈希偏差 0.000%**（逐字节一致，满足 <3% 判据）；但这是**登记完整性**结论，不是对源报告物理结论"
        "（如方腔 n=64 的 5% 判据）的复核——后者不在本包范围，也不得由本包标 verified。",
        "",
        "## ⑦ 自检（逐条对照 acceptance）",
        "",
        "| acceptance 项 | 结果 | 细节 |",
        "|---|---|---|",
        *selfrows,
        "",
        "自检结论：`all_pass=%s`（共 %d 项）。若有 ❌ 即为本单未达成项，如实列出而非粉饰。" % (
            verdict["all_pass"], len(verdict["checks"])),
        "",
        "## 复现",
        "",
        "```bash",
        "python3 scripts/kf/kf_wp14539_01_register.py build result verify figure report   # 一键全流程",
        "```",
        "",
        "repro_cmd: `python3 scripts/kf/kf_wp14539_01_register.py build result verify figure report`",
        "",
        "## 结果信封（唯一 json 代码块，原样提交）",
        "",
        "```json",
        json.dumps(result, ensure_ascii=False, indent=2),
        "```",
        "",
    ]
    text = "\n".join(lines)
    if text.count("```json") != 1:
        raise SystemExit("report must contain exactly one ```json block, found %d" % text.count("```json"))
    rp = out_dir / "report.md"
    rp.write_text(text, encoding="utf-8")
    print("wrote %s" % rp.relative_to(REPO))

    payload = {
        "title": "KF-RESULT %s" % cfg["package_id"],
        "summary": "资产登记 %s / report_id=%s：%d 项资产（%s），源 sha256 与契约逐字节一致；claims=0（登记不抽取）。" % (
            cfg["package_id"], rid, n, json.dumps(counts["by_resolution"], ensure_ascii=False)),
        "scenario_key": cfg["scenario_key"],
        "mission_id": cfg["mission_id"],
        "tags": ["kf-wp:%s" % cfg["package_id"], "asset-registration", "lane-B", "TensorKnowledge",
                 "report_id:%s" % rid],
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


# --------------------------------------------------------------------- publish
def publish(cfg, out_dir: Path):
    payload = json.loads((out_dir / "report_payload.json").read_text(encoding="utf-8"))
    base, token = login()
    status, resp = _req(base + "/tensor/reports", token, data=json.dumps(payload).encode(), timeout=180)
    receipt = {"posted_at": datetime.now(timezone.utc).isoformat(), "http_status": status,
               "endpoint": base + "/tensor/reports", "response_id": (resp or {}).get("id"),
               "response": resp if isinstance(resp, (int, str)) else {k: v for k, v in (resp or {}).items()
                                                                      if k not in ("markdown",)}}
    (out_dir / "publish_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
    print("published: id=%s status=%s" % (receipt["response_id"], status))
    return receipt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("actions", nargs="*", default=["build", "result", "verify", "figure", "report"])
    a = ap.parse_args()
    cfg = CFG
    out_dir = REPO / cfg["out_dir"]
    acts = set(a.actions)
    png = out_dir / "figures" / ("%s_asset_locator_map.png" % cfg["package_id"])
    if "build" in acts:
        build(cfg, out_dir, REPO)
    if "result" in acts:
        emit_result(cfg, out_dir)
    if "verify" in acts:
        verify(cfg, out_dir, REPO)
    if "figure" in acts:
        png = render_figure(cfg, out_dir)
    if "report" in acts:
        render_report(cfg, out_dir, png)
    if "publish" in acts:
        publish(cfg, out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
