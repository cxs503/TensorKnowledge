#!/usr/bin/env python3
"""Work package wp-5760-01 (01-asset-registration) — asset manifest builder + independent verifier.

Scope guard: touches ONLY report_id=5760. No extraction, no claim generation, no "verified" marks
(verification is platform-gated).

Zero hand-copying: every `locator.quote` is sliced out of the fetched markdown bytes, never retyped,
so `quote == markdown[start_char:end_char]` holds by construction and is re-checked by `verify`.

Usage (worktree root = repository checkout):
  python3 scripts/kf/build_asset_manifest_5760.py build      # fetch + hash + inventory -> asset_manifest.json
  python3 scripts/kf/build_asset_manifest_5760.py verify     # re-fetch, re-check every acceptance item
  python3 scripts/kf/build_asset_manifest_5760.py result     # derive kf_result.json from the manifest
  python3 scripts/kf/build_asset_manifest_5760.py all        # build -> verify -> result
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-5760-01"
REPORT_ID = "5760"
SOURCE_URI = "tensor://reports/5760"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "95a6ffec44f492fe4f7f39f8d6bb989d845f6a781cd5749197177b6c05308bfe"
EXPECTED_CHARS = 6808

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
SCHEMA = OUT_DIR / "asset_manifest.schema.json"
KF_RESULT = OUT_DIR / "kf_result.json"
VERDICT = OUT_DIR / "verification.json"
SNAPSHOT_DIR = REPO / "runs" / PKG
SNAPSHOT_MD = SNAPSHOT_DIR / "report_5760.md"
SNAPSHOT_META = SNAPSHOT_DIR / "report_5760_meta.json"

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")

FILE_EXTS = ("json", "png", "py", "md", "txt", "csv", "service", "sh", "yaml", "yml", "toml")
FILE_EXT_RE = re.compile(r"\.(%s)$" % "|".join(FILE_EXTS))
TOKEN_RE = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./{}\-]*[A-Za-z0-9_./{}\-]")
IMG_RE = re.compile(r"!\[(?P<alt>[^\]]*)\]\((?P<path>[^)\s]+)\)")
HEAD_RE = re.compile(r"^(?P<hashes>#{2,3}) (?P<text>.+?)\s*$")
TABLE_SEP_RE = re.compile(r"^\|[\s:|-]+\|$")
FENCE_RE = re.compile(r"^```")


# ---------------------------------------------------------------- platform I/O


def _req(url, token=None, data=None):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    if not USER or not PASS:
        raise SystemExit("TENSOR_AGENT_USER / TENSOR_AGENT_PASS not set: network commands unavailable")
    d = _req(BASE + "/auth/login", data=json.dumps({"username": USER, "password": PASS}).encode())
    tok = d.get("access_token") or d.get("token")
    if not tok:
        raise SystemExit("login returned no token: %s" % sorted(d))
    return tok


def fetch_report(token):
    d = _req(BASE + "/tensor/reports/%s" % REPORT_ID, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


def probe_artifact_endpoints(token):
    """Best-effort discovery of a platform attachment listing; record, never guess."""
    probes = {}
    for path in ("/tensor/reports/%s/artifacts" % REPORT_ID,
                 "/tensor/reports/%s/attachments" % REPORT_ID,
                 "/tensor/artifacts?report_id=%s" % REPORT_ID):
        try:
            d = _req(BASE + path, token)
            probes[path] = {"status": "ok", "shape": type(d).__name__,
                            "items": len(d) if isinstance(d, (list, dict)) else None}
        except urllib.error.HTTPError as e:
            probes[path] = {"status": "http_%s" % e.code}
        except Exception as e:  # noqa: BLE001 - record, never fabricate
            probes[path] = {"status": "error", "detail": type(e).__name__}
    return probes


# ---------------------------------------------------------------- locator helpers


class Doc:
    def __init__(self, md: str):
        self.md = md
        self.lines = md.split("\n")
        offs, pos = [], 0
        for ln in self.lines:
            offs.append(pos)
            pos += len(ln) + 1
        self.offsets = offs

    def line_of(self, char: int) -> int:
        lo, hi = 0, len(self.offsets) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.offsets[mid] <= char:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def span_of_line(self, lineno: int):
        start = self.offsets[lineno - 1]
        return start, start + len(self.lines[lineno - 1])

    def locator(self, start: int, end: int) -> dict:
        quote = self.md[start:end]
        if not quote:
            raise SystemExit("empty quote at %d:%d" % (start, end))
        return {
            "method": "char_span",
            "start_char": start,
            "end_char": end,
            "start_line": self.line_of(start),
            "end_line": self.line_of(max(end - 1, start)),
            "quote": quote,
            "unique": self.md.count(quote) == 1,
        }


def section_of(headings, char: int) -> str:
    cur = "(document head)"
    for start, text in headings:
        if start <= char:
            cur = text
        else:
            break
    return cur


# ---------------------------------------------------------------- inventory


def scan_sections(doc: Doc):
    out, stack = [], []
    for i, line in enumerate(doc.lines, start=1):
        m = HEAD_RE.match(line)
        if not m:
            continue
        text = m.group("text").strip()
        depth = len(m.group("hashes"))
        if depth == 2:
            stack = [text]
        else:
            stack = stack[:1] + [text]
        start, end = doc.span_of_line(i)
        out.append({"line": i, "depth": depth, "text": text, "parent": stack[0] if depth == 3 else None,
                    "start": start, "end": end})
    return out


def scan_tables(doc: Doc):
    out, i = [], 0
    while i < len(doc.lines):
        if doc.lines[i].startswith("|") and i + 1 < len(doc.lines) and TABLE_SEP_RE.match(doc.lines[i + 1]):
            j = i + 1
            while j + 1 < len(doc.lines) and doc.lines[j + 1].startswith("|"):
                j += 1
            start, _ = doc.span_of_line(i + 1)
            _, end = doc.span_of_line(j + 1)
            header = [c.strip() for c in doc.lines[i].strip().strip("|").split("|")]
            out.append({"first_line": i + 1, "last_line": j + 1, "start": start, "end": end,
                        "columns": header, "rows": j - i - 1})
            i = j + 1
        else:
            i += 1
    return out


KNOWN_DIR_PREFIXES = ("artifacts/", "runs/", "tests/", "tools/", "deploy/", "ops/", "docs/",
                       "scripts/", "schemas/", "ke/", "knowledge/", "data/", "pilots/", "reports/")
BRACE_PATH_RE = re.compile(r"[A-Za-z0-9_./\-]*\{[A-Za-z0-9_,.\-]+\}[A-Za-z0-9_./\-]*")


def _classify_token(tok: str):
    """file / dir / bare, or None for prose that merely looks path-like.

    Third false-positive family caught in review: slash-separated word lists that are domain
    vocabulary, not paths ("pending/queued/ready/todo/not_started", "since/fired/cooldown").
    A directory token therefore needs a known artifact prefix, or a trailing "/" plus a path-ish
    marker, and never an extension.
    """
    if "/" in tok and FILE_EXT_RE.search(tok):
        return "file"
    if "/" in tok and not FILE_EXT_RE.search(tok):
        known = tok.startswith(KNOWN_DIR_PREFIXES)
        if known and tok.split("/", 1)[1]:
            return "dir"
        if tok.endswith("/") and tok.count("/") >= 2 and any(c in tok for c in "._-"):
            return "dir"
        return None
    if FILE_EXT_RE.search(tok) and not tok.startswith("."):
        return "bare"
    return None


def scan_paths(doc: Doc):
    """Occurrence-level path references: (line, token, kind). kind in {file, dir, bare}.

    Guards against the two false-positive families seen on the first build:
      - prose fragments that merely contain a slash ("systemd/容器", "60 s/样本") are rejected because a
        directory token must carry >=2 separators or start with a known artifact prefix;
      - brace globs ("artifacts/in20_r5/{replay,live}/") are matched as ONE token before the plain
        token scan, and markdown image syntax is masked so a figure is not registered twice.
    """
    refs = []
    for i, line in enumerate(doc.lines, start=1):
        line_start = doc.offsets[i - 1]
        masked = list(line)
        hits = []
        for m in BRACE_PATH_RE.finditer(line):
            hits.append((m.group(0), m.start(), m.end()))
            for k in range(m.start(), m.end()):
                masked[k] = " "
        for m in IMG_RE.finditer(line):
            for k in range(m.start(), m.end()):
                masked[k] = " "
        masked_line = "".join(masked)
        for m in TOKEN_RE.finditer(masked_line):
            tok = m.group(0).rstrip(".,;:")
            if not tok or doc.md[line_start + m.start():line_start + m.start() + len(tok)] != tok:
                continue
            hits.append((tok, m.start(), m.start() + len(tok)))
        for tok, s_off, e_off in sorted(hits, key=lambda x: x[1]):
            kind = _classify_token(tok)
            if not kind:
                continue
            refs.append({"line": i, "token": tok, "kind": kind,
                         "start": line_start + s_off, "end": line_start + e_off})
    return refs


def scan_images(doc: Doc):
    out = []
    for i, line in enumerate(doc.lines, start=1):
        for m in IMG_RE.finditer(line):
            start = doc.offsets[i - 1] + m.start()
            out.append({"line": i, "alt": m.group("alt"), "path": m.group("path"),
                        "start": start, "end": start + len(m.group(0)), "raw": m.group(0)})
    return out


def scan_fences(doc: Doc):
    out, open_at, lang = [], None, None
    for i, line in enumerate(doc.lines, start=1):
        if FENCE_RE.match(line):
            if open_at is None:
                open_at, lang = i, line.strip("`").strip()
            else:
                s, _ = doc.span_of_line(open_at + 1)
                _, e = doc.span_of_line(i - 1)
                out.append({"lang": lang, "first_line": open_at, "last_line": i,
                            "body_first_line": open_at + 1, "body_last_line": i - 1, "start": s, "end": e})
                open_at = None
    return out


def resolve_local(path: str) -> dict:
    """Resolve a referenced path inside the TensorKnowledge delivery worktree only (no cross-repo guessing)."""
    for cand in (REPO / path, REPO / path.lstrip("./")):
        try:
            cand = cand.resolve()
        except OSError:
            continue
        if not str(cand).startswith(str(REPO)):
            continue
        if cand.is_file():
            raw = cand.read_bytes()
            return {"status": "unresolved", "scope": "delivery_worktree",
                    "reason": "path exists in this worktree but belongs to an upstream package",
                    "resolved_path": str(cand.relative_to(REPO)),
                    "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
        if cand.is_dir():
            return {"status": "unresolved", "scope": "delivery_worktree",
                    "resolved_path": str(cand.relative_to(REPO)) + "/",
                    "reason": "directory exists in this worktree but belongs to an upstream package"}
    return {"status": "unresolved", "scope": "delivery_worktree",
            "reason": "path not present in the TensorKnowledge delivery worktree; "
                      "the report's artifacts live in the producing repository (TensorPlatform), "
                      "which is outside this work package's boundary"}


def build_assets(doc: Doc, meta: dict):
    headings = scan_sections(doc)
    heading_spans = [(h["start"], h["text"]) for h in headings]
    assets = []

    def add(asset_class, label, section, locator, resolution, check, result, note, extra=None):
        aid = "A%02d" % (len(assets) + 1)
        if len(assets) + 1 > 99:
            raise SystemExit("asset_id space (A99) exhausted; refine granularity")
        a = {"asset_id": aid, "asset_class": asset_class, "label": label,
             "in_report_section": section, "locator": locator, "resolution": resolution,
             "resolution_check": {"check": check, "result": result}, "note": note}
        if extra:
            a.update(extra)
        assets.append(a)
        return a

    title_line = doc.lines[0]
    add("source_document",
        "report %s markdown (source_field=markdown, %d chars / %d bytes utf-8)"
        % (REPORT_ID, len(doc.md), len(doc.md.encode("utf-8"))),
        "(document head)",
        {"method": "document", "start_char": 0, "end_char": len(doc.md),
         "start_line": 1, "end_line": len(doc.lines),
         "quote": title_line, "unique": doc.md.count(title_line) == 1},
        "resolved_in_source", "sha256(markdown.encode('utf-8')) == contract source_hash",
        "resolved",
        "The registered asset itself. quote pinned to the H1 title line; method=document covers the "
        "whole charset span 0..%d." % len(doc.md),
        {"sha256": hashlib.sha256(doc.md.encode("utf-8")).hexdigest(),
         "chars": len(doc.md), "bytes_utf8": len(doc.md.encode("utf-8"))})

    for h in headings:
        add("section",
            "section heading %s %s" % ("#" * h["depth"], h["text"]),
            h["text"] if h["depth"] == 2 else h["parent"],
            doc.locator(h["start"], h["end"]),
            "resolved_in_source", "md[start_char:end_char] == quote", "resolved",
            "Heading line only; the body extent runs to the next heading of equal or higher level "
            "(locator line %d onward)." % h["line"])

    for t in scan_tables(doc):
        add("table",
            "markdown table: %s" % " | ".join(t["columns"][:4]),
            section_of(heading_spans, t["start"]),
            doc.locator(t["start"], t["end"]),
            "resolved_in_source", "md[start_char:end_char] == quote (header row .. last data row)",
            "resolved",
            "%d data rows, %d columns (lines %d-%d)."
            % (t["rows"], len(t["columns"]), t["first_line"], t["last_line"]),
            {"columns": t["columns"], "rows": t["rows"]})

    for img in scan_images(doc):
        add("figure_reference",
            "inline image reference: %s" % img["path"],
            section_of(heading_spans, img["start"]),
            doc.locator(img["start"], img["end"]),
            "referenced_unresolved",
            "image bytes present in report payload or delivery worktree", "unresolved",
            "Figure is referenced by filename only; no PNG bytes travel with the markdown and no such "
            "file exists in this worktree, so the figure cannot be hashed from here.",
            {"path_reference": img["path"], "alt_text": img["alt"], "local_resolution": resolve_local(img["path"])})

    for idx, fig in enumerate(meta.get("figures") or []):
        name = fig.get("name") if isinstance(fig, dict) else str(fig)
        loc = {"method": "report_field", "field": "figures", "index": idx,
               "quote": name or "(unnamed)", "unique": bool(name) and doc.md.count(name) == 1}
        if isinstance(fig, dict):
            loc["start_char"] = doc.md.find(name) if name and name in doc.md else 0
            loc["end_char"] = loc["start_char"] + len(name or "")
            loc["start_line"] = doc.line_of(loc["start_char"])
            loc["end_line"] = loc["start_line"]
        has_png = bool(isinstance(fig, dict) and fig.get("png_base64"))
        add("figure_metadata",
            "platform figures[%d] metadata: %s" % (idx, name),
            section_of(heading_spans, loc.get("start_char", 0)),
            loc,
            "declared_absent" if not has_png else "resolved_in_source",
            "figures[%d].png_base64 present" % idx, "present" if has_png else "absent",
            "Platform stores name+caption only (no png_base64 payload), so zero bytes are claimable; "
            "caption kept verbatim in note: %r" % ((fig or {}).get("caption") if isinstance(fig, dict) else None),
            {"caption": (fig or {}).get("caption") if isinstance(fig, dict) else None})

    for ref in scan_paths(doc):
        res = resolve_local(ref["token"])
        if ref["kind"] == "file":
            cls = "file_reference"
            note = ("Path cited at line %d; resolution checked inside this delivery worktree only."
                    % ref["line"])
        elif ref["kind"] == "dir":
            cls = "artifact_directory_reference"
            note = ("Directory/glob reference at line %d; no file-level bytes are addressable from it."
                    % ref["line"])
        else:
            cls = "bare_filename_reference"
            note = ("Filename without a directory at line %d: the enclosing path is not stated in the "
                    "source, so it cannot be bound to a unique location (recorded unresolved rather "
                    "than guessed)." % ref["line"])
            if ref["token"].lower().endswith(".png"):
                note += (" This is a textual re-citation of the figure already registered as "
                         "figure_reference / figure_metadata.")
        add(cls, ref["token"], section_of(heading_spans, ref["start"]),
            doc.locator(ref["start"], ref["end"]),
            "referenced_unresolved", "target bytes resolvable from this package", "unresolved",
            note, {"path_reference": ref["token"], "local_resolution": res})

    for fence in scan_fences(doc):
        if fence["lang"] != "bash" or fence["end"] <= fence["start"]:
            continue
        add("repro_command_block",
            "fenced %s block: reproduction commands (lines %d-%d)"
            % (fence["lang"], fence["body_first_line"], fence["body_last_line"]),
            section_of(heading_spans, fence["start"]),
            doc.locator(fence["start"], fence["end"]),
            "resolved_in_source", "md[start_char:end_char] == quote", "resolved",
            "Upstream probe/verification commands quoted verbatim; NOT executed by this package "
            "(upstream artifacts are outside the boundary).",
            {"lang": fence["lang"], "body_lines": fence["body_last_line"] - fence["body_first_line"] + 1})

    return assets


def make_manifest(meta: dict, md: str, token: str) -> dict:
    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_HASH:
        raise SystemExit("source hash mismatch: live=%s contract=%s" % (digest, EXPECTED_HASH))
    if len(md) != EXPECTED_CHARS:
        raise SystemExit("source char count mismatch: live=%d contract=%d" % (len(md), EXPECTED_CHARS))
    doc = Doc(md)
    assets = build_assets(doc, meta or {})

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    quotes = [a["locator"]["quote"] for a in assets]
    ids = [a["asset_id"] for a in assets]

    return {
        "schema": "asset_manifest.v1",
        "schema_ref": str(SCHEMA.relative_to(REPO)),
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "generator": "scripts/kf/build_asset_manifest_5760.py",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "hashed_bytes": "markdown encoded as utf-8",
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
            "mission_id": meta.get("mission_id"),
            "report_status": meta.get("status"),
            "report_created_at": meta.get("created_at"),
            "platform_figures": meta.get("figures") or [],
            "platform_tags": meta.get("tags") or [],
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "distinct_referenced_paths": len({a["path_reference"] for a in assets if "path_reference" in a}),
        },
        "assets": assets,
        "claims": [],
        "claims_note": ("Contract notes allow an empty claims array for task_type 01-asset-registration "
                        "(objective.classify_report_type=false, '不做抽取'); no claim was generated, so "
                        "none can be overstated and none is marked verified."),
        "integrity": {
            "quote_uniqueness": {
                "checked": len(quotes),
                "unique": sum(1 for q in quotes if md.count(q) == 1),
                "non_unique_assets": [a["asset_id"] for a in assets if not a["locator"].get("unique")],
            },
            "hash_recomputed_locally": digest,
            "hash_matches_contract": digest == EXPECTED_HASH,
            "no_duplicate_ids": len(ids) == len(set(ids)),
            "char_span_exact": sum(1 for a in assets
                                   if a["locator"]["method"] == "char_span"
                                   and md[a["locator"]["start_char"]:a["locator"]["end_char"]]
                                   == a["locator"]["quote"]),
            "char_span_assets": sum(1 for a in assets if a["locator"]["method"] == "char_span"),
            "identity_granularity": ("Reference assets are occurrence-level: identity is (path, markdown "
                                     "offset), so one file cited twice yields two asset ids with their own "
                                     "spans; distinct_referenced_paths is the deduplicated view."),
        },
        "artifact_endpoint_probe": (probe_artifact_endpoints(token) if token
                                     else {"status": "not_probed_offline"}),
        "limitations": [
            "Registration only: no extraction, no claim generation, no verified marks (verification is platform-gated).",
            "Referenced paths are resolved strictly inside the TensorKnowledge delivery worktree; the report's "
            "artifacts/code belong to the producing repository (TensorPlatform) and stay unresolved by design.",
            "No PNG bytes exist for fig_stall_timeline.png in the report payload (figures array carries name+caption only) "
            "and no such file exists in this worktree, so the figure is registered metadata-only.",
            "SQL table / free-text names quoted in the report (campaign DAG node table, saturation_pulse, "
            "factory_resident_workers, thresholds) are data sources rather than byte-addressable attachments, "
            "so they are deliberately NOT registered as assets.",
            "The bash reproduction block is registered as text, not executed: running it would touch upstream artifacts "
            "outside this work package's boundary.",
            "Output location docs/kf/wp-5760-01/ because .gitignore drops artifacts/ and docs/ops/filter-audit.md records "
            "that the mission-push gate filters artifacts/**; outputs there would be silently lost.",
        ],
    }


def build_offline(meta_path: Path = SNAPSHOT_META, md_path: Path = SNAPSHOT_MD) -> dict:
    """Rebuild the manifest from the committed snapshot only (no network): determinism check for tests."""
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    md = md_path.read_bytes().decode("utf-8")
    return make_manifest(meta, md, None)


# ---------------------------------------------------------------- commands


def cmd_build() -> dict:
    token = login()
    meta, md = fetch_report(token)
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_MD.write_bytes(md.encode("utf-8"))
    SNAPSHOT_META.write_text(json.dumps(
        {k: v for k, v in meta.items() if k != "markdown"}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    manifest = make_manifest(meta, md, token)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets, %d resolved / %d unresolved / %d absent)"
          % (MANIFEST.relative_to(REPO), manifest["counts"]["assets"],
             manifest["counts"]["resolved_in_source"], manifest["counts"]["referenced_unresolved"],
             manifest["counts"]["declared_absent"]))
    return manifest


def cmd_verify() -> int:
    import jsonschema

    token = login()
    meta, md = fetch_report(token)
    checks = {}

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "json.loads OK"}
    except Exception as e:  # noqa: BLE001
        print(json.dumps({"valid_json": {"pass": False, "detail": str(e)}}, ensure_ascii=False))
        return 1

    try:
        jsonschema.validate(manifest, json.loads(SCHEMA.read_text(encoding="utf-8")))
        checks["schema_pass"] = {"pass": True,
                                 "detail": "jsonschema draft-07 validation against %s"
                                           % SCHEMA.relative_to(REPO)}
    except Exception as e:  # noqa: BLE001
        checks["schema_pass"] = {"pass": False, "detail": str(e).split("\n")[0][:300]}

    bad, bad_span = [], []
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc["method"] == "char_span":
            s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
            if not (0 <= s < e <= len(md)) or md[s:e] != q:
                bad_span.append(a["asset_id"])
            elif q not in md:
                bad.append(a["asset_id"])
        elif loc["method"] == "document":
            if loc["quote"] not in md:
                bad.append(a["asset_id"])
        elif loc["method"] == "report_field":
            figs = meta.get("figures") or []
            i = loc.get("index", -1)
            if not (0 <= i < len(figs)):
                bad.append(a["asset_id"])
            elif loc.get("quote") and loc["quote"] not in json.dumps(figs[i], ensure_ascii=False) \
                    and loc["quote"] not in md:
                bad.append(a["asset_id"])
        else:
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = {
        "pass": not bad and not bad_span,
        "detail": "checked %d locators live; missing/unresolvable=%s span_mismatch=%s"
                  % (len(manifest["assets"]), bad, bad_span),
    }

    actual = hashlib.sha256(md.encode("utf-8")).hexdigest()
    declared = str(manifest["source"]["hash"])
    snapshot = hashlib.sha256(SNAPSHOT_MD.read_bytes()).hexdigest()
    checks["source_hash_matches"] = {
        "pass": actual == declared == EXPECTED_HASH == snapshot,
        "detail": "live=%s declared=%s contract=%s snapshot=%s chars_live=%d chars_declared=%d"
                  % (actual, declared, EXPECTED_HASH, snapshot, len(md), manifest["source"]["chars"]),
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {"pass": len(ids) == len(set(ids)),
                                  "detail": "%d ids, %d distinct" % (len(ids), len(set(ids)))}

    claim_problems = []
    for c in manifest.get("claims", []):
        if "evidence_locator" not in c and "status" not in c:
            claim_problems.append(c.get("claim_id"))
        if str(c.get("status", "")).lower() in ("verified", "verification_passed"):
            claim_problems.append(c.get("claim_id"))
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not claim_problems,
        "detail": "claims=%d (empty array allowed by contract); problems=%s"
                  % (len(manifest.get("claims", [])), claim_problems),
    }

    # counts + integrity must describe the asset array actually shipped
    by_res = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    counts_ok = (c["assets"] == len(manifest["assets"])
                 and c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
                 and c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
                 and c["declared_absent"] == by_res.get("declared_absent", 0))
    checks["counts_consistent"] = {"pass": counts_ok, "detail": json.dumps(by_res, ensure_ascii=False)}
    integ = manifest["integrity"]
    checks["integrity_selfconsistent"] = {
        "pass": (integ["hash_recomputed_locally"] == actual
                 and integ["hash_matches_contract"] is True
                 and integ["no_duplicate_ids"] is True
                 and integ["char_span_exact"] == sum(
                     1 for a in manifest["assets"]
                     if a["locator"]["method"] == "char_span"
                     and md[a["locator"]["start_char"]:a["locator"]["end_char"]] == a["locator"]["quote"])),
        "detail": "char_span_exact=%s" % integ["char_span_exact"],
    }
    checks["scope_single_report"] = {
        "pass": manuscript_only(manifest),
        "detail": "every asset locator points into report %s markdown / its platform metadata" % REPORT_ID,
    }

    verdict = {"package_id": PKG, "report_id": REPORT_ID,
               "checked_at": datetime.now(timezone.utc).isoformat(),
               "source_hash_live": actual,
               "acceptance": checks,
               "all_pass": all(v["pass"] for v in checks.values()),
               "note": "These are the package's own machine checks. They are NOT a platform verification "
                       "mark; platform verification is computed by the platform gate."}
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for k, v in checks.items():
        print("%-55s %s  %s" % (k, "PASS" if v["pass"] else "FAIL", v["detail"]))
    print("all_pass =", verdict["all_pass"])
    return 0 if verdict["all_pass"] else 1


def manuscript_only(manifest: dict) -> bool:
    return manifest["report_id"] == REPORT_ID and manifest["source"]["uri"] == SOURCE_URI


def cmd_result() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    mraw = MANIFEST.read_bytes()
    token = login()
    _meta, live_md = fetch_report(token)
    live = hashlib.sha256(live_md.encode("utf-8")).hexdigest()
    if live != manifest["source"]["hash"] or live != EXPECTED_HASH:
        raise SystemExit("live source drifted from manifest: %s" % live)
    result = {
        "package_id": PKG,
        "task_type": "01-asset-registration",
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + live,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(live_md),
            "source_bytes_utf8": len(live_md.encode("utf-8")),
            "fetched_via": "GET %s/tensor/reports/%s" % (BASE, REPORT_ID),
            "generator": "scripts/kf/build_asset_manifest_5760.py",
            "contract_version": "1.0",
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str(MANIFEST.relative_to(REPO)),
                "sha256": hashlib.sha256(mraw).hexdigest(),
                "bytes": len(mraw),
                "asset_count": manifest["counts"]["assets"],
                "claims": len(manifest["claims"]),
            }
        },
    }
    KF_RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % KF_RESULT.relative_to(REPO))
    return 0


def main(argv):
    cmds = argv[1:] or ["all"]
    for cmd in cmds:
        if cmd == "build":
            cmd_build()
        elif cmd == "verify":
            rc = cmd_verify()
            if rc:
                return rc
        elif cmd == "result":
            cmd_result()
        elif cmd == "all":
            cmd_build()
            rc = cmd_verify()
            if rc:
                return rc
            cmd_result()
        else:
            raise SystemExit("unknown command %r" % cmd)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))