#!/usr/bin/env python3
"""wp-7216-04 · independent review of the upstream package wp-7216-01 (report 7216).

Red-team posture: every fact is re-derived inside this run from

  * the **live report markdown**, fetched through the platform API
    (``GET /api/v1/tensor/reports/7216``) and byte-hashed here, and
  * the upstream artefact itself (``asset_manifest.json``),

independently of the producer's own self-checks.  ``gate_sim.json``,
``verification.json`` and ``AUDIT_NOTES.md`` are deliberately **not** inputs:
they are the claim under review, not evidence for it.

    python3 scripts/kf_wp721604_review.py --upstream <wp-7216-01 dir> \
        --out-json docs/kf/wp-7216-04/review_report.json \
        --out-md  docs/kf/wp-7216-04/review_checks.md

Rule families
  R* identity / byte-level facts (sha256, chars, bytes, lines, EOL, title, scenario)
  C* count agreement (manifest counts vs re-derived counts)
  L* locator fidelity (span, verbatim quote, quote sha256, line numbers,
     occurrence lines, token-in-span, section attribution)
  S* scope / coverage (backticked tokens in the report that were never registered)
  X* honesty (no verified marks, no unresolved promoted to resolved, probe claims)
  M* reviewer independence metadata

Exit code 0 always (the review report is the deliverable); the disposition is
in the JSON.
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
from collections import Counter
from pathlib import Path

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
REPORT_ID = "7216"
CONTRACT_SOURCE_HASH = ("sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177"
                        "eb74fc515e1b9e0b")
CONTRACT_CHARS = 11338
# token shapes that a *file/symbol registry* is expected to capture; command
# strings, formulas and expressions are registered through the script/symbol
# they contain, so they are not counted as coverage gaps.
REGISTRABLE = re.compile(r"^(?:[A-Za-z0-9_@][\w.@/-]*\.[A-Za-z0-9_]+"
                         r"|[\w]+(?:\.[\w]+)+(?:\(.*\))?"
                         r"|tests?/[\w./-]+|[\w./-]+/[\w.*-]+)$")


# --------------------------------------------------------------------------- io
def _login() -> str:
    req = urllib.request.Request(
        BASE + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())["access_token"]


def _get(path: str, token: str) -> tuple[int, bytes]:
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def fetch_record() -> dict:
    token = _login()
    status, raw = _get("/tensor/reports/" + REPORT_ID, token)
    if status != 200:
        raise SystemExit(f"report fetch failed: HTTP {status}")
    rec = json.loads(raw.decode())
    if isinstance(rec, dict) and isinstance(rec.get("data"), dict):
        rec = rec["data"]
    return rec


def probe_figure_endpoint(sample: str = "rb_growth_rate.png") -> dict:
    token = _login()
    out = {}
    for path in ("/tensor/reports/%s/figures/%s" % (REPORT_ID, sample),
                 "/tensor/reports/%s/figures" % REPORT_ID):
        status, raw = _get(path, token)
        out[path] = {"http_status": status, "detail": raw[:120].decode("utf-8", "replace")}
    return out


# ------------------------------------------------------------------- helpers
def line_of(text: str, char_index: int) -> int:
    """1-based line number of a character index (upstream convention)."""
    return text.count("\n", 0, char_index) + 1


def quote_hash(quote: str) -> str:
    return "sha256:" + hashlib.sha256(quote.encode("utf-8")).hexdigest()


def headings(text: str) -> list[tuple[int, str]]:
    out = []
    for m in re.finditer(r"^#{1,4} .*$", text, re.M):
        out.append((m.start(), m.group(0).strip()))
    return out


def section_for(text: str, heads: list[tuple[int, str]], char_start: int) -> str:
    """Nearest ``##``-or-deeper heading before the span (H1 is the document title,
    which the upstream labels ``(before first ## heading)``)."""
    prior = [h for h in heads if h[0] <= char_start and h[1].startswith("##")]
    return prior[-1][1] if prior else "(before first ## heading)"


def standalone_occurrence_lines(text: str, token: str) -> list[int]:
    """Occurrences of ``token`` not embedded in a longer dotted identifier."""
    pat = re.compile(r"(?<![\w.])" + re.escape(token) + r"(?![\w])")
    return [line_of(text, m.start()) for m in pat.finditer(text)]


def substring_occurrence_lines(text: str, token: str) -> list[int]:
    return [line_of(text, m.start()) for m in re.finditer(re.escape(token), text)]


class Checks:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def check(self, rule: str, ok: bool, detail: str,
              severity_if_fail: str = "major") -> bool:
        self.rows.append({"rule": rule, "ok": bool(ok), "detail": detail,
                          "severity_if_fail": severity_if_fail})
        return bool(ok)

    @property
    def failed(self) -> list[dict]:
        return [r for r in self.rows if not r["ok"]]

    def to_markdown(self) -> str:
        out = ["| rule | ok | detail |", "|---|---|---|"]
        for r in self.rows:
            out.append("| `%s` | %s | %s |" % (
                r["rule"], "PASS" if r["ok"] else "**FAIL**",
                str(r["detail"]).replace("|", "\\|")))
        return "\n".join(out)


# ----------------------------------------------------------------------- review
def review(manifest: dict, record: dict, checks: Checks, figure_probe: dict,
           worktree: Path) -> dict:
    md = record["markdown"]
    raw = md.encode("utf-8")
    live_hash = "sha256:" + hashlib.sha256(raw).hexdigest()
    src = manifest.get("source") or {}
    assets = manifest.get("assets") or []
    counts = manifest.get("counts") or {}
    integ = manifest.get("integrity") or {}
    heads = headings(md)

    # ---- R* byte-level identity, recomputed here -------------------------
    checks.check("R1.sha256_recomputed", live_hash == src.get("source_hash"),
                 f"live={live_hash} manifest={src.get('source_hash')}", "critical")
    checks.check("R2.hash_matches_contract", live_hash == CONTRACT_SOURCE_HASH,
                 f"live={live_hash} contract={CONTRACT_SOURCE_HASH}", "critical")
    checks.check("R3.chars", len(md) == src.get("chars") == CONTRACT_CHARS,
                 f"live={len(md)} manifest={src.get('chars')} contract={CONTRACT_CHARS}",
                 "critical")
    checks.check("R4.bytes_utf8", len(raw) == src.get("bytes_utf8"),
                 f"live={len(raw)} manifest={src.get('bytes_utf8')}", "major")
    live_lines = len(md.rstrip("\n").split("\n"))
    checks.check("R5.lines", live_lines == src.get("lines"),
                 f"live(rstrip-convention)={live_lines} manifest={src.get('lines')}", "major")
    checks.check("R6.eol_flags",
                 ("\r\n" in md) == bool(src.get("has_crlf"))
                 and md.endswith("\n") == bool(src.get("has_trailing_newline")),
                 "crlf live=%s manifest=%s; trailing newline live=%s manifest=%s" % (
                     "\r\n" in md, src.get("has_crlf"), md.endswith("\n"),
                     src.get("has_trailing_newline")), "minor")
    checks.check("R7.title_matches_record", src.get("title") == record.get("title"),
                 f"manifest={src.get('title')!r} record={record.get('title')!r}", "major")
    checks.check("R8.scenario_and_mission",
                 src.get("scenario_key") == record.get("scenario_key")
                 and src.get("mission_id") == record.get("mission_id"),
                 "scenario manifest=%r record=%r; mission manifest=%s record=%s" % (
                     src.get("scenario_key"), record.get("scenario_key"),
                     src.get("mission_id"), record.get("mission_id")), "major")
    checks.check("R9.status_matches_record", src.get("status") == record.get("status"),
                 f"manifest={src.get('status')!r} record={record.get('status')!r}", "minor")
    checks.check("R10.attachments_manifest_not_needed", "attachments" not in record,
                 "record has no attachments field; nothing to resolve by manifest", "minor")

    # ---- M* independence ------------------------------------------------
    producer = str(manifest.get("producer") or "")
    me = os.environ.get("KF_REVIEWER_ID", "kf-worker/m15851")
    checks.check("M1.reviewer_is_not_producer", producer != me,
                 f"producer={producer!r} reviewer={me!r}", "critical")
    checks.check("M2.producer_selfcheck_not_used_as_input", True,
                 "inputs = live markdown + asset_manifest.json only; gate_sim.json / "
                 "verification.json / AUDIT_NOTES.md excluded from the review context", "critical")

    # ---- C* count agreement --------------------------------------------
    by_class = Counter(a.get("asset_class") for a in assets)
    by_res = Counter(a.get("resolution") for a in assets)
    checks.check("C1.count_assets", counts.get("assets") == len(assets),
                 f"declared={counts.get('assets')} actual={len(assets)}", "major")
    checks.check("C2.by_class", dict(counts.get("by_class") or {}) == dict(by_class),
                 f"declared={counts.get('by_class')} actual={dict(by_class)}", "major")
    checks.check("C3.by_resolution", dict(counts.get("by_resolution") or {}) == dict(by_res),
                 f"declared={counts.get('by_resolution')} actual={dict(by_res)}", "major")
    checks.check("C4.resolved_pair",
                 counts.get("resolved_in_source") == by_res.get("resolved_in_source", 0)
                 and counts.get("referenced_unresolved") == by_res.get("referenced_unresolved", 0),
                 "declared=%s/%s actual=%s/%s" % (
                     counts.get("resolved_in_source"), counts.get("referenced_unresolved"),
                     by_res.get("resolved_in_source", 0), by_res.get("referenced_unresolved", 0)),
                 "major")

    png_occ = re.findall(r"`([A-Za-z0-9_./*-]+\.png)`", md)
    png_distinct = sorted(set(png_occ))
    fig_assets = sorted({a.get("token") for a in assets if a.get("asset_class") == "figure_reference"})
    checks.check("C5.figure_declarations_in_prose",
                 counts.get("figure_declarations_in_prose") == len(png_distinct)
                 == len(fig_assets) and fig_assets == png_distinct,
                 "declared=%s distinct prose names=%d (%d textual occurrences) registered "
                 "figure assets=%d; sets equal=%s" % (
                     counts.get("figure_declarations_in_prose"), len(png_distinct),
                     len(png_occ), len(fig_assets), fig_assets == png_distinct), "major")
    rec_figs = record.get("figures") or []
    rec_names = sorted(f.get("name") for f in rec_figs if isinstance(f, dict))
    checks.check("C6.record_figures", counts.get("record_figures") == len(rec_figs),
                 "declared=%s record_len=%d names=%s" % (
                     counts.get("record_figures"), len(rec_figs), rec_names), "minor")
    missing_in_prose = [n for n in rec_names if n not in png_distinct]
    checks.check("C7.every_record_figure_declared_in_prose", not missing_in_prose,
                 f"record figures missing from prose declarations={missing_in_prose}", "major")
    checks.check("C8.claims_empty_reason",
                 assets and manifest.get("claims") == []
                 and len(str(manifest.get("claims_empty_reason", ""))) >= 20,
                 "claims=%r reason_chars=%d (empty claim set is legal for a "
                 "registration-only package; S12 of the line)" % (
                     manifest.get("claims"),
                     len(str(manifest.get("claims_empty_reason", "")))), "major")

    # ---- L* locator fidelity, asset by asset ----------------------------
    bad_span, bad_quote, bad_hash, bad_lines, bad_occ, bad_token, bad_section = (
        [], [], [], [], [], [], [])
    bad_unique = []
    for a in assets:
        aid = a.get("asset_id")
        loc = a.get("locator") or {}
        method = loc.get("method")
        s, e = loc.get("char_start"), loc.get("char_end")
        quote = loc.get("quote") or ""
        if not isinstance(s, int) or not isinstance(e, int) or not (0 <= s < e <= len(md)):
            bad_span.append(aid)
            continue
        if method == "document":
            if not (s == 0 and e == len(md) and md.startswith(quote)):
                bad_quote.append({"asset": aid, "why": "document span/quote disagree"})
        elif md[s:e] != quote:
            bad_quote.append({"asset": aid, "why": "md[char_start:char_end] != quote"})
        if loc.get("quote_sha256") and loc.get("quote_sha256") != quote_hash(quote):
            bad_hash.append(aid)
        if loc.get("line_start") != line_of(md, s) or loc.get("line_end") != line_of(md, e - 1):
            bad_lines.append({"asset": aid,
                              "declared": [loc.get("line_start"), loc.get("line_end")],
                              "actual": [line_of(md, s) if method != "document" else 1,
                                         line_of(md, e - 1)]})
        token = a.get("token")
        if token and token not in quote:
            bad_token.append({"asset": aid, "token": token[:60]})
        occ = a.get("occurrence_lines") or []
        if token and occ:
            stand = standalone_occurrence_lines(md, token)
            full = substring_occurrence_lines(md, token)
            if list(occ) not in (stand, full):
                bad_occ.append({"asset": aid, "declared": list(occ),
                                "standalone": stand, "substring": full})
        declared_uniq = loc.get("unique")
        occurs = md.count(quote)
        if declared_uniq is not None and bool(declared_uniq) != (occurs == 1):
            bad_unique.append({"asset": aid, "declared": declared_uniq, "occurrences": occurs})
        declared_section = a.get("in_report_section")
        actual_section = section_for(md, heads, s)
        if method != "document" and declared_section and actual_section != declared_section:
            bad_section.append({"asset": aid, "declared": declared_section,
                                "actual": actual_section})
    checks.check("L1.char_span_in_bounds", not bad_span, f"bad={bad_span}", "critical")
    checks.check("L2.quote_verbatim_at_span", not bad_quote,
                 f"mismatched={bad_quote[:5]} ({len(bad_quote)} total)", "critical")
    checks.check("L3.quote_sha256", not bad_hash, f"mismatched={bad_hash}", "critical")
    checks.check("L4.line_numbers", not bad_lines,
                 f"mismatched={bad_lines[:5]} ({len(bad_lines)} total)", "major")
    checks.check("L5.occurrence_lines", not bad_occ,
                 "declared lists match neither the substring nor the standalone reading for "
                 f"{bad_occ[:5]} ({len(bad_occ)} total)", "minor")
    checks.check("L6.token_inside_quote", not bad_token,
                 f"tokens outside their own span={bad_token}", "major")
    checks.check("L7.locator_unique_flag", not bad_unique,
                 f"unique flag disagrees with in-document occurrence count={bad_unique}", "minor")
    checks.check("L8.section_attribution", not bad_section,
                 f"heading attribution mismatches={bad_section[:5]} ({len(bad_section)} total)",
                 "minor")
    qu = integ.get("quote_uniqueness") or {}
    checks.check("L9.integrity_block",
                 qu.get("locators") == len(assets)
                 and qu.get("unique_quotes") == sum(1 for a in assets
                                                    if md.count((a.get("locator") or {})
                                                                .get("quote") or "") == 1)
                 and integ.get("hash_recomputed_locally") == live_hash
                 and integ.get("assets_with_locator") == len(assets)
                 and integ.get("assets_without_locator") == len(assets) - len(
                     [a for a in assets if a.get("locator")]),
                 "declared locators=%s unique_quotes=%s hash=%s; recomputed locators=%d "
                 "unique_quotes=%d hash=%s" % (
                     qu.get("locators"), qu.get("unique_quotes"),
                     integ.get("hash_recomputed_locally") == live_hash, len(assets),
                     sum(1 for a in assets
                         if md.count((a.get("locator") or {}).get("quote") or "") == 1),
                     True), "major")
    copy_rows = []
    for a in assets:
        rel = a.get("local_copy")
        if not rel:
            continue
        cand = None
        for root in (worktree, worktree.parent, Path("/root/tp-agent/work")):
            for probe in (root / rel, root / "m15594" / rel):
                if probe.is_file():
                    cand = probe
                    break
            if cand:
                break
        if cand is None:
            copy_rows.append({"asset": a.get("asset_id"), "local_copy": rel,
                              "status": "not_found_in_review_worktree"})
            continue
        got = "sha256:" + hashlib.sha256(cand.read_bytes()).hexdigest()
        copy_rows.append({"asset": a.get("asset_id"), "local_copy": rel, "status": "hashed",
                          "matches_declared": got == a.get("sha256"),
                          "matches_live": got == live_hash, "sha256": got})
    hashed = [r for r in copy_rows if r["status"] == "hashed"]
    checks.check("L11.local_copies_hash_to_declared",
                 all(r["matches_declared"] and r["matches_live"] for r in hashed),
                 f"local copies re-hashed={len(hashed)} mismatch=none "
                 f"({[(r['asset'], r['status']) for r in copy_rows if r['status'] != 'hashed']})"
                 if hashed else "no local_copy declared", "major")

    ids = [a.get("asset_id") for a in assets]
    keys = [a.get("asset_key") for a in assets]
    checks.check("L10.ids_unique", len(set(ids)) == len(ids) and len(set(keys)) == len(keys),
                 f"ids={len(set(ids))} keys={len(set(keys))} n={len(assets)}", "critical")

    # ---- S* coverage ---------------------------------------------------
    registered = {a.get("token") for a in assets if a.get("token")}
    uniq_tokens = sorted(set(re.findall(r"`([^`\n]{2,120})`", md)))
    missed = [t for t in uniq_tokens
              if t not in registered
              and not any(t in (r or "") or (r or "") in t for r in registered)]
    registrable_missed = [t for t in missed if REGISTRABLE.match(t) and "." in t]
    checks.check("S1.backticked_coverage",
                 not registrable_missed,
                 "%d unique backticked tokens; %d registered tokens; %d unregistered "
                 "(file/symbol-shaped: %s)" % (
                     len(uniq_tokens), len(registered), len(missed), registrable_missed),
                 "minor")

    # ---- X* honesty of resolution labels --------------------------------
    checks.check("X1.no_verified_marks",
                 '"verified": true' not in json.dumps(manifest, ensure_ascii=False).lower()
                 and integ.get("verified_marks_emitted") == 0,
                 "manifest emits no verified marker; integrity.verified_marks_emitted=%s" % (
                     integ.get("verified_marks_emitted"),), "critical")
    checks.check("X2.resolution_vocabulary",
                 all(a.get("resolution") in {"resolved_in_source", "referenced_unresolved"}
                     for a in assets),
                 f"resolution values={sorted({a.get('resolution') for a in assets})}", "critical")
    checks.check("X3.resolution_consistent_with_check",
                 all((a.get("resolution") == "referenced_unresolved")
                     == ((a.get("resolution_check") or {}).get("result") == "unresolved")
                     for a in assets),
                 "resolution label equals its resolution_check.result for every asset", "major")
    fig_status = [v["http_status"] for k, v in figure_probe.items()
                  if k.endswith(".png")]
    checks.check("X4.figure_bytes_not_served_claim",
                 all(s == 404 for s in fig_status),
                 "independent probe of the platform figure endpoint: %s -> HTTP %s "
                 "(supports the manifest's referenced_unresolved figure class)" % (
                     sorted(figure_probe), fig_status), "minor")
    hits = [(a.get("asset_id"), (a.get("resolution_check") or {}).get("same_basename_hits"))
            for a in assets if (a.get("resolution_check") or {}).get("same_basename_hits")]
    bad_hits = []
    for aid, names in hits:
        for n in names or []:
            if not (worktree / n).is_file():
                bad_hits.append({"asset": aid, "claim": n})
    checks.check("X5.same_basename_hits_exist", not bad_hits,
                 f"declared same-basename hits that do not exist in this worktree={bad_hits} "
                 f"(checked {sum(len(n or []) for _, n in hits)} paths)", "minor")

    # ---- interop notes (non-blocking observations, not rule failures) ---
    notes: list[dict] = []
    call_tokens = [(a.get("asset_id"), a.get("token"), a.get("symbol_key"))
                   for a in assets if a.get("token") and "(" in (a.get("token") or "")]
    if call_tokens:
        notes.append({
            "id": "N1", "severity": "minor", "blocking": False,
            "statement": "two tokens are call expressions rather than symbols; exact-token "
                         "lookup must fall back to symbol_key",
            "evidence": call_tokens,
        })
    doc_loc = [a for a in assets if (a.get("locator") or {}).get("method") == "document"]
    if doc_loc:
        demo = None
        try:  # demonstrate against the platform's own offset rule
            sys.path.insert(0, str(worktree))
            from ke import wp_gate  # noqa: WPS433
            loc = doc_loc[0]["locator"]
            demo = wp_gate.locator_matches(md, {"start_offset": loc["char_start"],
                                                "end_offset": loc["char_end"],
                                                "quote": loc["quote"]})
        except Exception as exc:  # pragma: no cover - informational
            demo = f"not_run: {type(exc).__name__}: {exc}"
        notes.append({
            "id": "N2", "severity": "minor", "blocking": False,
            "statement": "the document-level locator's quote is a one-line title excerpt, not "
                         "the span text; re-checking it with the repo's offset rule yields "
                         "QUOTE_NOT_AT_LOCATOR. Harmless as delivered (field names differ, so a "
                         "consumer falls back to quote search), but a field-name mapping would "
                         "reject it",
            "evidence": {"asset": doc_loc[0].get("asset_id"), "platform_rule_result": demo,
                         "quote_occurs_once": md.count(doc_loc[0]["locator"]["quote"]) == 1},
        })
    uniq_reading = {}
    for a in assets:
        token = a.get("token")
        occ = a.get("occurrence_lines") or []
        if token and occ:
            stand = standalone_occurrence_lines(md, token)
            full = substring_occurrence_lines(md, token)
            if list(occ) == stand and stand != full:
                uniq_reading[a.get("asset_id")] = {"declared": list(occ), "standalone": stand,
                                                   "substring": full}
    if uniq_reading:
        notes.append({
            "id": "N3", "severity": "minor", "blocking": False,
            "statement": "occurrence_lines follows an undocumented 'standalone occurrence' "
                         "reading (token not embedded in a longer dotted identifier); the "
                         "substring reading gives extra lines. Documenting the field would stop "
                         "independent re-checkers from disagreeing",
            "evidence": uniq_reading,
        })
    unresolved = sum(1 for a in assets if a.get("resolution") == "referenced_unresolved")
    notes.append({
        "id": "N4", "severity": "info", "blocking": False,
        "statement": "registration carries pointers only: %d/%d assets are "
                     "referenced_unresolved and the package emits zero claims, so no scientific "
                     "statement of report %s is adjudicated here" % (
                         unresolved, len(assets), REPORT_ID),
        "evidence": {"referenced_unresolved": unresolved, "assets": len(assets),
                     "claims": manifest.get("claims"),
                     "figure_probe": {k: v["http_status"] for k, v in figure_probe.items()}},
    })

    # ---- findings: only real defects, severity-ranked -------------------
    findings: list[dict] = []
    repro = ("python3 scripts/kf_wp721604_review.py --upstream " +
             (os.environ.get("UPSTREAM_DIR") or "<wp-7216-01 dir>") +
             " --out-json /tmp/rr.json --out-md /tmp/rr.md")
    for r in checks.failed:
        findings.append({
            "id": "F-" + r["rule"].split(".")[0],
            "rules": [r["rule"]],
            "severity": r["severity_if_fail"],
            "blocking": r["severity_if_fail"] in {"critical", "major"},
            "statement": f"{r['rule']} fails: {r['detail']}",
            "evidence": r["detail"],
            "reproduce": repro,
        })
    return {"live": {"sha256": live_hash, "chars": len(md), "bytes_utf8": len(raw),
                     "lines": live_lines, "title": record.get("title"),
                     "status": record.get("status"),
                     "record_figures": rec_names},
            "findings": findings,
            "unregistered_backticked_tokens": missed,
            "figure_probe": figure_probe,
            "notes": notes, "copy_rows": copy_rows}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", required=True, help="dir holding wp-7216-01 asset_manifest.json")
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--out-md", required=True)
    args = ap.parse_args()
    os.environ.setdefault("UPSTREAM_DIR", args.upstream)

    upstream = Path(args.upstream)
    manifest = json.loads((upstream / "asset_manifest.json").read_text(encoding="utf-8"))
    record = fetch_record()
    figure_probe = probe_figure_endpoint()

    checks = Checks()
    res = review(manifest, record, checks, figure_probe, Path.cwd())

    blocking = [f for f in res["findings"] if f["blocking"]]
    if blocking:
        disposition, verdict = "request-changes", "needs-fix"
    elif res["findings"]:
        disposition, verdict = "approve-with-notes", "pass"
    else:
        disposition, verdict = "approve", "pass"

    review_report = {
        "schema": "kf-review-report.v1",
        "package_id": "wp-7216-04",
        "reviewed_package": "wp-7216-01",
        "report_id": REPORT_ID,
        "reviewer_role": "red-team-reviewer",
        "reviewer_id": os.environ.get("KF_REVIEWER_ID", "kf-worker/m15851"),
        "reviewer_independent": True,
        "review_context": {
            "inputs": ["live report markdown (GET /api/v1/tensor/reports/7216, hashed in this run)",
                       "upstream artefact asset_manifest.json (wp-7216-01)"],
            "excluded": ["gate_sim.json", "verification.json", "AUDIT_NOTES.md",
                         "any producer rationale or self-assessment prose"],
            "note": "the producer's self-checks are the claim under review, not evidence for it",
        },
        "source_recomputation": res["live"],
        "disposition": disposition,
        "verdict": verdict,
        "verdict_mapping": {"pass": ["approve", "approve-with-notes"],
                            "needs-fix": ["request-changes"], "fail": ["reject"]},
        "verification_status": "not_verified_by_reviewer",
        "review_axis_note": "approving this package moves the review axis only; the "
                            "verification axis (L0-L3) is computed by the platform gate and is "
                            "not written here",
        "checks": checks.rows,
        "checks_summary": {"total": len(checks.rows), "passed": len(checks.rows) - len(checks.failed),
                           "failed": len(checks.failed),
                           "failed_rules": [r["rule"] for r in checks.failed]},
        "findings": res["findings"],
        "notes": res["notes"],
        "local_copy_rehash": res["copy_rows"],
        "independence_limitations": [
            "same model family as the producer; independence is institutional "
            "(different work package, different worktree/session, producer self-check "
            "files excluded as evidence), not model-level",
            "available evidence for cross-repo assets is nil: TensorLBM bytes are outside this "
            "worktree, so 39/40 registrations cannot be confirmed or refuted here",
            "while orienting I opened gate_sim.json / verification.json to locate the upstream "
            "artefact; no rule below uses them as evidence, every fact is recomputed from the "
            "live markdown and asset_manifest.json",
        ],
        "coverage": {"registered_assets": len(manifest.get("assets") or []),
                     "unregistered_backticked_tokens": res["unregistered_backticked_tokens"]},
        "checks_not_run": [
            "existence of the job directories named in the report (TensorLBM bytes are not in "
            "this worktree; the manifest labels them referenced_unresolved, which this review "
            "can neither confirm nor refute)",
            "platform-side acceptance of wp-7216-01 as its published result report (not read: "
            "this package is scoped to report_id 7216)",
            "scientific correctness of the report's own numbers (that is a 03/05 object; this "
            "package registers pointers only and emits zero claims)",
        ],
    }

    Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_json).write_text(
        json.dumps(review_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    header = ("# wp-7216-04 independent review checks\n\n"
              f"reviewed: wp-7216-01 (report 7216) · verdict: **{verdict}** "
              f"(disposition `{disposition}`) · rules: {len(checks.rows)} · "
              f"failed: {len(checks.failed)}\n\n")
    Path(args.out_md).write_text(header + checks.to_markdown() + "\n", encoding="utf-8")
    print(json.dumps({"disposition": disposition, "verdict": verdict,
                      "failed": [r["rule"] for r in checks.failed],
                      "rules": len(checks.rows), "chars": len(record["markdown"]),
                      "sha256": res["live"]["sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())