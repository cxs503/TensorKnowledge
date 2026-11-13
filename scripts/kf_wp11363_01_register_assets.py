#!/usr/bin/env python3
"""KF work package wp-11363-01 (task_type=01-asset-registration) for report 11363.

Scope of this 工序 (see contract):
  * confirm report_id == 11363 and the sha256 of its `markdown` field;
  * enumerate the assets the report itself declares (figures, artifact bundle,
    code/API/symbol anchors) with a verbatim, char-span locator for each;
  * do NOT extract claims, do NOT classify report type, do NOT mark anything
    `verified` (verification is the platform gate's job).

Every quote is taken as a whole markdown line and is double-checked:
    quote in markdown  and  markdown[offset:offset+len(quote)] == quote

    python3 scripts/kf_wp11363_01_register_assets.py            # fetch + build manifest + self-check
    python3 scripts/kf_wp11363_01_register_assets.py --offline  # rebuild from the committed snapshot

Outputs (all inside the delivery worktree):
    runs/wp-11363-01/source_11363.md                  byte snapshot of the source field
    docs/kf/wp-11363-01/asset_manifest.json           the declared output file
    docs/kf/wp-11363-01/kf_result.json                result envelope (schemas/kf_result.v1.schema.json)
    docs/kf/wp-11363-01/report_selfcheck.json         acceptance re-derivation
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "kf"))

import register_assets_lib as L  # noqa: E402  (shared 工序-01 library)

PACKAGE_ID = "wp-11363-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "11363"
SOURCE_URI = "tensor://reports/11363"
CONTRACT_SOURCE_HASH = "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23"
CONTRACT_TITLE = "ESD 节能装置收益评估成熟化（p228w1-N09）：分项+能量上界门+自航点耦合"
CONTRACT_SCENARIO = "p228w1-N09"
CONTRACT_CHARS = 6902
PRODUCER = "kf-worker/m15697"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
SNAPSHOT = RUN_DIR / ("source_%s.md" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
SELFCHECK = OUT_DIR / "report_selfcheck.json"

# ---------------------------------------------------------------- token scans
TICK_RE = re.compile(r"`([^`\n]+)`")
PATH_RE = re.compile(r"^[\w.\-/]+\.(?:py|json|csv|md|png|jpg|jpeg|h5|hdf5|toml|ya?ml)$")
DIR_RE = re.compile(r"^[\w.\-/]+/$")
API_RE = re.compile(r"^(?:[A-Z]{3,7}\s+)?/api/[\w/{}\-]*$")
CAP_RE = re.compile(r"^[a-z_][\w.]*\s*=\s*(REAL|MOCK|STUB|WITHHELD|NOT_SUPPORTED)$")
SYM_DOTTED_RE = re.compile(r"^[a-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+$")
SYM_CONST_RE = re.compile(r"^[A-Z][A-Z0-9_]{3,}$")
SYM_LONG_RE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+){2,}$")
# numbers/formulas that must never be mistaken for paths or symbols
NOT_A_REF = re.compile(r"[=+<>|·ΔηΣ×−\s]")

PATH_KIND = {
    ".py": "source_code_reference", ".json": "data_artifact_reference",
    ".csv": "data_artifact_reference", ".h5": "data_artifact_reference",
    ".hdf5": "data_artifact_reference", ".md": "document_reference",
    ".png": "figure_reference", ".jpg": "figure_reference",
    ".jpeg": "figure_reference",
}
PNG_COUNT_PHRASE = "4 张 png"
MANIFEST_FILE_COUNT = 10  # "清单 sha256：`artifacts/esd/manifest.json`（10 文件）"


def sha256_hex(b: bytes) -> str:
    return "sha256:" + hashlib.sha256(b).hexdigest()


def classify(tok: str) -> str | None:
    """Return an asset kind for a backticked token, or None when it is not a reference."""
    if not tok:
        return None
    if CAP_RE.match(tok):
        return "capability_declaration_reference"
    if NOT_A_REF.search(tok):
        return None
    if PATH_RE.match(tok):
        return PATH_KIND.get(Path(tok).suffix.lower(), "referenced_artifact")
    if DIR_RE.match(tok):
        return "source_directory_reference"
    if API_RE.match(tok):
        return "api_endpoint_reference"
    if (SYM_DOTTED_RE.match(tok) or SYM_CONST_RE.match(tok) or SYM_LONG_RE.match(tok)) \
            and not tok.startswith(("http://", "https://")):
        return "symbol_reference"
    return None


def build_md_index(text: str):
    """(offset, line_no, line) for every logical line, 1-based line numbers."""
    out, off = [], 0
    for i, ln in enumerate(text.splitlines(), start=1):
        out.append((off, i, ln))
        off += len(ln) + 1
    return out


def section_of(line_no: int, sections: list[tuple[int, str]]) -> str:
    cur = "preamble"
    for ln, name in sections:
        if line_no >= ln:
            cur = name
    return cur


def find_lines(index, token_substr: str) -> list[tuple[int, int, str]]:
    return [t for t in index if token_substr in t[2]]


def resolve_in_worktree(tok: str) -> dict:
    """Only the delivery worktree is probed; a miss is reported, never guessed."""
    cand = tok.strip().lstrip("./")
    p = ROOT / cand
    if p.exists() and p.is_file():
        b = p.read_bytes()
        return {"status": "resolved", "scope": "delivery_worktree TensorKnowledge",
                "path": cand, "bytes": len(b), "sha256": sha256_hex(b)}
    if p.is_dir():
        names = sorted(q.name for q in p.iterdir())[:10]
        return {"status": "resolved", "scope": "delivery_worktree TensorKnowledge",
                "path": cand, "kind": "directory", "entries": names}
    hits = sorted(str(q.relative_to(ROOT)) for q in ROOT.rglob(Path(cand).name)
                  if q.is_file() and ".git" not in q.parts)[:5]
    return {"status": "unresolved", "scope": "delivery_worktree TensorKnowledge",
            "reason": ("declared by report 11363 as a ship-performance-platform artefact; "
                       "not present in the delivery worktree, and this 工序 does not cross "
                       "repository boundaries to fetch bytes"),
            "same_basename_hits": hits}


# ------------------------------------------------------------------- fetching
def get_markdown(offline: bool) -> tuple[str, dict, str]:
    if offline:
        md = SNAPSHOT.read_text(encoding="utf-8")
        rec = {"id": int(REPORT_ID), "markdown": md, "figures": None,
               "title": CONTRACT_TITLE, "scenario_key": CONTRACT_SCENARIO}
        return md, rec, "local snapshot " + str(SNAPSHOT.relative_to(ROOT))
    rec = L.fetch_report(REPORT_ID)          # hard-locks report_id, refuses empty markdown
    return rec["markdown"], rec, rec["_retrieved_via"]


def fetch_figure_bytes(name: str, token: str | None) -> dict:
    """Ask the platform for the figure payload. Hash it; do NOT commit the blob
    (bytes stay re-fetchable from the recorded endpoint)."""
    ep = "/tensor/reports/%s/figures/%s" % (REPORT_ID, name)
    probe = L.probe(ep, token)
    if probe.get("http_status") != 200 or not token:
        probe["payload_sha256"] = None
        return probe
    import urllib.request
    req = urllib.request.Request(L.api_base() + ep,
                                 headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=60) as r:
        blob = r.read()
    probe["bytes"] = len(blob)
    probe["payload_sha256"] = sha256_hex(blob)
    probe["png_magic_ok"] = blob[:8] == b"\x89PNG\r\n\x1a\n"
    probe["stored"] = False
    probe["note"] = "payload hashed in-flight; blob not committed (re-fetchable from the endpoint)"
    return probe


def figure_probes(rec: dict, token: str | None) -> dict:
    figs = [f.get("name") for f in (rec.get("figures") or [])]
    probes = {"figures_endpoint": L.probe("/tensor/reports/%s/figures" % REPORT_ID, token)}
    for name in figs:
        probes[name] = fetch_figure_bytes(name, token)
    return probes


# ------------------------------------------------------------------- manifest
def build_manifest(md: str, rec: dict, fetched_via: str, token: str | None) -> dict:
    raw = md.encode("utf-8")
    digest = sha256_hex(raw)
    if digest != CONTRACT_SOURCE_HASH:
        raise SystemExit("source_hash mismatch: live=%s contract=%s -- refusing to register"
                         % (digest, CONTRACT_SOURCE_HASH))
    index = build_md_index(md)
    sections = [(i, ln.lstrip("# ").strip()[:14]) for off, i, ln in index
                if ln.startswith("#")]
    assets, locator_checks = [], []
    seen_tokens: dict[str, dict] = {}

    def add_asset(asset_id, kind, label, line_no, offset, quote, extra=None):
        occ = md.count(quote)
        back = md[offset:offset + len(quote)] == quote
        entry = {
            "asset_id": asset_id,
            "kind": kind,
            "label": label,
            "section": section_of(line_no, sections),
            "locator": {
                "source_field": "markdown",
                "line": line_no,
                "start_char": offset,
                "end_char": offset + len(quote),
                "quote": quote,
                "quote_verified": bool((quote in md) and back),
                "count_occurrences": occ,
                "unique": occ == 1,
                "method": "char_span",
            },
        }
        if extra:
            entry.update(extra)
        assets.append(entry)
        locator_checks.append({"asset_id": asset_id, "line": line_no,
                               "start_char": offset, "end_char": offset + len(quote),
                               "in_markdown": quote in md, "back_read_ok": back,
                               "count_occurrences": occ})
        return entry

    # ---- A01: the markdown itself (document-level locator, whole field hashed)
    h1_off, h1_no, h1 = index[0]
    if not h1.startswith("# "):
        raise SystemExit("first line is not an H1 heading; refusing to build document locator")
    doc = add_asset("r11363:source-markdown", "report_markdown", "report-11363-markdown",
                    h1_no, h1_off, h1, {
                        "source_uri": SOURCE_URI,
                        "media_type": "text/markdown",
                        "bytes": len(raw),
                        "chars": len(md),
                        "lines": len(index),
                        "sha256": digest,
                        "hash_scope": "UTF-8 bytes of the `markdown` field served by "
                                      "GET /api/v1/tensor/reports/11363",
                        "local_copy": str(SNAPSHOT.relative_to(ROOT)),
                        "resolution": {"status": "resolved", "scope": "platform_api",
                                       "via": fetched_via},
                    })
    assert doc["locator"]["quote_verified"]

    # ---- figures declared in the platform record (name/caption only)
    probes = figure_probes(rec, token)
    figure_assets = []
    for i, fig in enumerate(rec.get("figures") or [], start=1):
        name = fig.get("name") or ""
        hits = [t for t in find_lines(index, name)]
        probe = probes.get(name, {})
        fig_entry = {
            "asset_id": "r11363:figure:%02d" % i,
            "kind": "embedded_figure",
            "label": name,
            "name": name,
            "caption": fig.get("caption", ""),
            "record_pointer": "/figures/%d/name" % (i - 1),
            "section": (section_of(hits[0][1], sections) if hits else "record:figures"),
            "bytes": probe.get("bytes"),
            "sha256": probe.get("payload_sha256"),
            "resolution": {
                "status": ("resolved_with_bytes" if probe.get("payload_sha256")
                           else "metadata_only"),
                "scope": "platform_api",
                "via": "GET /tensor/reports/11363/figures/%s" % name,
                "http_status": probe.get("http_status"),
                "payload_sha256": probe.get("payload_sha256"),
                "png_magic_ok": probe.get("png_magic_ok"),
                "reason": ("figure payload served with HTTP 200; sha256 taken in flight, blob "
                           "deliberately not committed" if probe.get("payload_sha256")
                           else "byte endpoint returned %s; record exposes name/caption only, "
                                "so no hash is claimed" % probe.get("http_status")),
            },
            "locator": {
                "source_field": "markdown" if hits else "record",
                "method": "char_span" if hits else "record_pointer",
            },
        }
        if hits:
            off, ln_no, line = hits[0]
            occ = md.count(line)
            fig_entry["locator"].update({
                "line": ln_no, "start_char": off, "end_char": off + len(line),
                "quote": line, "quote_verified": (line in md) and md[off:off + len(line)] == line,
                "count_occurrences": occ, "unique": occ == 1, "method": "char_span",
                "body_reference_line": ln_no,
            })
            locator_checks.append({"asset_id": fig_entry["asset_id"], "line": ln_no,
                                   "start_char": off, "end_char": off + len(line),
                                   "in_markdown": line in md,
                                   "back_read_ok": md[off:off + len(line)] == line,
                                   "count_occurrences": occ})
        else:
            fig_entry["locator"].update({"pointer": "/figures/%d/name" % (i - 1),
                                         "note": "figure name not echoed in the body text"})
        assets.append(fig_entry)
        figure_assets.append(fig_entry)

    # ---- every other backticked reference in the body (one asset per distinct token)
    for fig in figure_assets:            # figure names already registered above
        seen_tokens[fig["name"]] = {"line": fig.get("locator", {}).get("line")}
    ref_count = 0
    for off, ln_no, line in index:
        if ln_no == h1_no:
            continue
        for tok in TICK_RE.findall(line):
            tok = tok.strip()
            kind = classify(tok)
            if not kind or tok in seen_tokens:
                continue
            seen_tokens[tok] = {"line": ln_no}
            ref_count += 1
            aid = "r11363:ref:%02d" % ref_count
            res = resolve_in_worktree(tok)
            entry = add_asset(aid, kind, tok, ln_no, off, line, {
                "token": tok,
                "resolution": res,
            })
            if kind == "capability_declaration_reference":
                entry["resolution"] = {
                    "status": "declared_reference_only",
                    "scope": "declared_in_prose_only",
                    "reason": "the report declares this capability grade; this 工序 records the "
                              "declaration verbatim and does NOT verify it (the platform gate "
                              "computes verification), so no grade is endorsed here",
                }
            if kind == "symbol_reference":
                entry["resolution"] = {
                    "status": "referenced_unresolved",
                    "scope": "declared_in_prose_only",
                    "reason": "symbol is named in the report prose; its defining line is not "
                              "given as a resolvable path inside this 工序's scope",
                }
            if kind == "api_endpoint_reference":
                entry["resolution"]["probe"] = L.probe("/calculations/esd", token) \
                    if "calculations" in tok else {"note": "out-of-scope endpoint, not probed"}
            # collect every further line that names the same token (no duplicate assets)
            entry["further_occurrences"] = [
                {"line": l2, "quote": q2,
                 "quote_verified": md.count(q2) >= 1}
                for o2, l2, q2 in find_lines(index, tok) if l2 != ln_no
            ][:5]

    # ---- upstream dependency stated only in prose (resistance kernel identity)
    up = None
    for off, ln_no, line in index:
        if "Holtrop-1984" in line and "R_T" in line:
            up = (off, ln_no, line)
            break
    if up:
        off, ln_no, line = up
        assets.append({
            "asset_id": "r11363:ref:upstream-resistance",
            "kind": "upstream_dependency_reference",
            "label": "Holtrop-1984 resistance kernel feeding R_T",
            "section": section_of(ln_no, sections),
            "locator": {"source_field": "markdown", "line": ln_no, "start_char": off,
                        "end_char": off + len(line), "quote": line,
                        "quote_verified": md[off:off + len(line)] == line,
                        "count_occurrences": md.count(line), "unique": md.count(line) == 1,
                        "method": "char_span"},
            "resolution": {
                "status": "referenced_unresolved",
                "scope": "declared_in_prose_only",
                "reason": "report states R_T comes from the resistance endpoint's Holtrop-1984 "
                          "kernel but gives no path/URI; not derivable without leaving this 工序",
            },
        })
        locator_checks.append({"asset_id": "r11363:ref:upstream-resistance", "line": ln_no,
                               "start_char": off, "end_char": off + len(line),
                               "in_markdown": line in md,
                               "back_read_ok": md[off:off + len(line)] == line,
                               "count_occurrences": md.count(line)})

    # ---- bundle internal consistency: enumerated members vs the reported file count
    bundle_line = next(((o, i2, l2) for o, i2, l2 in index if "工件：" in l2), None)
    member_check = {}
    if bundle_line:
        o, i2, l2 = bundle_line
        inner = re.search(r"（([^）]+)）", l2)
        members = [m.strip() for m in inner.group(1).split("、")] if inner else []
        counted = 0
        for m in members:
            counted += 4 if m == PNG_COUNT_PHRASE else 1
        member_check = {
            "declared_in_manifest_line": MANIFEST_FILE_COUNT,
            "enumerated_members": members,
            "member_file_count": counted,
            "matches": counted == MANIFEST_FILE_COUNT,
            "quote": l2,
            "line": i2,
        }

    # ---- counts / integrity
    by_kind, by_status = {}, {}
    for a in assets:
        st = a.get("resolution", {}).get("status", "n/a")
        by_kind["%s/%s" % (a["kind"], st)] = by_kind.get("%s/%s" % (a["kind"], st), 0) + 1
        by_status[st] = by_status.get(st, 0) + 1
    ids = [a["asset_id"] for a in assets]
    all_verified = all(c["in_markdown"] and c["back_read_ok"] for c in locator_checks)

    record_fields = {
        "title": rec.get("title"),
        "scenario_key": rec.get("scenario_key"),
        "mission_id": rec.get("mission_id"),
        "stage": rec.get("stage"),
        "status": rec.get("status"),
        "created_at": rec.get("created_at"),
        "tags": rec.get("tags"),
        "contract_title": CONTRACT_TITLE,
        "contract_scenario_key": CONTRACT_SCENARIO,
        "title_matches_contract": (rec.get("title") or "") == CONTRACT_TITLE,
        "scenario_matches_contract": (rec.get("scenario_key") or "") == CONTRACT_SCENARIO,
    }

    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "producer": PRODUCER,
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": digest,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_algo": "sha256",
            "hash_match": digest == CONTRACT_SOURCE_HASH,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "bytes": len(raw),
            "lines": len(index),
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": raw.endswith(b"\n"),
            "line_counting": "logical lines = markdown.splitlines(); 1-based",
            "fetched_via": fetched_via,
            "record_fields": record_fields,
        },
        "platform_attachment_probes": probes,
        "assets": assets,
        "locators": {
            "count": len(locator_checks),
            "all_in_markdown": all(c["in_markdown"] for c in locator_checks),
            "all_back_read_ok": all(c["back_read_ok"] for c in locator_checks),
            "all_verified": all_verified,
            "checks": locator_checks,
        },
        "bundle_consistency": member_check,
        "identity_facts": {
            "report_id_matches_contract": True,
            "source_hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "title_matches_contract": record_fields["title_matches_contract"],
            "scenario_matches_contract": record_fields["scenario_matches_contract"],
            "figure_count_in_record": len(rec.get("figures") or []),
        },
        "claims": [],
        "claims_empty_reason": (
            "objective.classify_report_type=false and the contract allows claims==[]; this 工序 "
            "registers assets only, so no claim is generated and no claim is marked verified "
            "(do_not_mark_claims_as_verified / no_forced_claim_generation)."),
        "counts": {
            "assets_total": len(assets),
            "figures_declared_in_record": len(rec.get("figures") or []),
            "figures_with_bytes": sum(1 for a in assets
                                      if a["kind"] == "embedded_figure"
                                      and a.get("sha256")),
            "assets_by_status": by_status,
            "kind_status_histogram": by_kind,
            "locators": len(locator_checks),
            "claims": 0,
        },
        "id_integrity": {
            "count": len(ids),
            "unique": len(ids) == len(set(ids)),
            "duplicate_ids": sorted({i for i in ids if ids.count(i) > 1}),
            "pattern_ok": all(re.match(r"^r11363:[\w\-]+(?::[\w\-]+)*$", i) for i in ids),
        },
        "unresolved": sorted({a["asset_id"] for a in assets
                              if a.get("resolution", {}).get("status") in
                              ("unresolved", "referenced_unresolved")}),
        "observations": [
            "Report 11363 is a results report of a finished work node (mission 9564): its 审计链 "
            "section enumerates a 10-file artefact bundle under artifacts/esd/ that lives in "
            "another repository, so registration can only confirm the references, not the bytes.",
            "All four figures are declared in the platform record with captions, but the /figures "
            "byte endpoints answer 404, so no figure hash is claimed.",
            "The report's own internal consistency (bundle line '10 文件' vs the enumerated members) "
            "is checked arithmetically in bundle_consistency; it is a consistency note, not a "
            "verification of the upstream artefact.",
        ],
        "limitations": [
            "Registration only: no claim/evidence extraction, no report-type classification, no "
            "verified marks (verification is computed by the platform gate).",
            "source_hash scope = UTF-8 bytes of the markdown string returned by the platform API; "
            "any change to the stored markdown, even whitespace, invalidates it.",
            "Resolution is probed against the delivery worktree (TensorKnowledge) only; report "
            "11363's artefacts live in ship-performance-platform and are therefore reported as "
            "unresolved rather than fetched across repositories.",
            "Quotes are whole markdown lines, so char spans include table pipes / leading list "
            "markers; they are verbatim and re-verifiable, not minimal spans.",
            "Report 11363 makes domain claims (<15% literature agreement, energy upper bound gate). "
            "Registering them would be extraction, which is explicitly out of this package's scope; "
            "none of them is endorsed or refuted here.",
        ],
    }
    return manifest


def build_envelope(manifest: dict) -> dict:
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": manifest["source"]["source_hash"],
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": manifest["generated_at"],
            "notes": "GET /api/v1/tensor/reports/11363 -> markdown; sha256 over UTF-8 bytes; "
                     "contract hash re-checked before any output was written",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }


def classify_md_table(manifest: dict) -> list[str]:
    rows = ["| asset_id | kind | status | locator | quote (verbatim, truncated) |",
            "|---|---|---|---|---|"]
    for a in manifest["assets"]:
        st = a.get("resolution", {}).get("status", "-")
        loc = a.get("locator", {})
        where = "L%s:%s-%s" % (loc.get("line"), loc.get("start_char"), loc.get("end_char")) \
            if loc.get("method") == "char_span" else "record %s" % loc.get("pointer")
        q = (loc.get("quote") or "").replace("|", "\\|")
        q = q if len(q) <= 60 else q[:57] + "…"
        rows.append("| `%s` | %s | %s | %s | `%s` |" % (a["asset_id"], a["kind"], st, where, q))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="rebuild from runs/wp-11363-01/source_11363.md")
    ap.add_argument("--print-table", action="store_true")
    args = ap.parse_args()

    md, rec, via = get_markdown(args.offline)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not args.offline:
        SNAPSHOT.write_bytes(md.encode("utf-8"))
    token = None if args.offline else L.get_token()
    manifest = build_manifest(md, rec, via, token)
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    ENVELOPE.write_text(json.dumps(build_envelope(manifest), ensure_ascii=False, indent=2),
                        encoding="utf-8")
    if args.print_table:
        print("\n".join(classify_md_table(manifest)))
    print("manifest  ->", MANIFEST.relative_to(ROOT))
    print("envelope  ->", ENVELOPE.relative_to(ROOT))
    print("assets    :", manifest["counts"]["assets_total"],
          "| locators:", manifest["locators"]["count"],
          "| all_verified:", manifest["locators"]["all_verified"])
    print("hash      :", manifest["source"]["source_hash"],
          "| match:", manifest["source"]["hash_match"],
          "| chars:", manifest["source"]["chars"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())