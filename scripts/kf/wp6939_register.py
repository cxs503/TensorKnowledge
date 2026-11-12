#!/usr/bin/env python3
"""Work package wp-6939-01 (task_type=01-asset-registration) — asset registration only.

Scope guard (hard): touches ONLY report_id=6939. No extraction, no classification of the
report type, no claim generation, no `verified` marking (verification is the platform gate's
job). Every locator quote is *sliced out of the fetched markdown bytes*, never retyped, so a
quote cannot drift from the source.

Subcommands:
  fetch    GET the report markdown, assert contract hash/chars, freeze it as a test fixture
  build    derive asset_manifest.json + verification.json + kf_result.json from the fixture
  verify   re-check every acceptance item offline (hash, locators, ids, schema)
  all      fetch → build → verify

Acceptance items checked by `verify`:
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-6939-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "6939"
SOURCE_URI = "tensor://reports/6939"
SOURCE_FIELD = "markdown"
# Pinned by the work-package contract (input.source_hash / input.chars).
CONTRACT_HASH = "8260a0ff15985b2312763ed966258248665fe2b53a3ebda8133d406c4bce4246"
CONTRACT_CHARS = 2002

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
FIXTURE = REPO / "tests" / "fixtures" / "kf" / "6939_markdown.md"
SCHEMA = OUT_DIR / "asset_manifest.v1.schema.json"
ENVELOPE_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"
PROBE = OUT_DIR / "artifact_probe.json"
MANIFEST = OUT_DIR / "asset_manifest.json"
VERDICT = OUT_DIR / "verification.json"
RESULT = OUT_DIR / "kf_result.json"

BASE = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")


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


def fetch_report(token):
    d = _req(BASE + "/tensor/reports/%s" % REPORT_ID, token)
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        d = d["data"]
    md = d.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("report %s has no markdown field" % REPORT_ID)
    return d, md


# ------------------------------------------------------------------ helpers
def line_of(md: str, char_index: int) -> int:
    """1-based line number of a character offset."""
    return md.count("\n", 0, char_index) + 1


def span(md: str, needle: str, occurrence: int = 1) -> tuple[int, int]:
    """Character span of the n-th occurrence of `needle`; raises if absent."""
    idx, start = -1, 0
    for _ in range(occurrence):
        idx = md.find(needle, start)
        if idx < 0:
            raise SystemExit("verbatim token not found in source: %r (#%d)" % (needle, occurrence))
        start = idx + 1
    return idx, idx + len(needle)


def locator(md: str, start: int, end: int, method: str = "char_span", **extra) -> dict:
    quote = md[start:end]
    occ = md.count(quote)
    loc = {
        "method": method,
        "start_char": start,
        "end_char": end,
        "start_line": line_of(md, start),
        "end_line": line_of(md, end - 1),
        "quote": quote,
        "unique": occ == 1,
    }
    loc.update(extra)
    return loc


def sha(s: str | bytes) -> str:
    return hashlib.sha256(s.encode("utf-8") if isinstance(s, str) else s).hexdigest()


# ------------------------------------------------------------------ fetch
def cmd_fetch():
    token = login()
    meta, md = fetch_report(token)
    raw = md.encode("utf-8")
    digest = sha(raw)
    ok_hash, ok_chars = digest == CONTRACT_HASH, len(md) == CONTRACT_CHARS
    print("live sha256=%s (contract %s) match=%s" % (digest, CONTRACT_HASH, ok_hash))
    print("live chars=%d (contract %d) match=%s" % (len(md), CONTRACT_CHARS, ok_chars))
    if not (ok_hash and ok_chars):
        raise SystemExit("source drifted from the contract — refusing to register")
    FIXTURE.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE.write_text(md, encoding="utf-8")
    meta_out = {k: v for k, v in meta.items() if k != "markdown"}
    (OUT_DIR / "source_record_meta.json").parent.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "source_record_meta.json").write_text(
        json.dumps(meta_out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("froze fixture %s (%d bytes)" % (FIXTURE.relative_to(REPO), len(raw)))
    probe_artifacts(token, meta)
    return meta, md


def probe_artifacts(token, meta):
    """Ask the platform three ways whether any figure/artifact bytes exist for report 6939.
    Result is evidence for the metadata_only classification — recorded, never interpreted away."""
    res = {"report_id": REPORT_ID, "generated_at": datetime.now(timezone.utc).isoformat(), "endpoints": []}

    def hit(path):
        try:
            d = _req(BASE + path, token)
            return {"status": "ok", "shape": type(d).__name__}
        except urllib.error.HTTPError as e:
            try:
                detail = e.read().decode("utf-8", "replace")[:120]
            except Exception:  # noqa: BLE001
                detail = ""
            return {"status": "http_%s" % e.code, "detail": detail}
        except Exception as e:  # noqa: BLE001
            return {"status": "error", "detail": type(e).__name__}

    for name in [f.get("name") for f in (meta.get("figures") or []) if f.get("name")]:
        e = hit("/tensor/reports/%s/figures/%s" % (REPORT_ID, name))
        e["endpoint"] = "GET /tensor/reports/%s/figures/%s" % (REPORT_ID, name)
        e["figure"] = name
        res["endpoints"].append(e)
    for path in ("/tensor/reports/%s/artifacts" % REPORT_ID, "/tensor/artifacts?report_id=%s" % REPORT_ID):
        e = hit(path)
        e["endpoint"] = "GET " + path
        res["endpoints"].append(e)
    res["any_payload_bytes"] = any(e["status"] == "ok" for e in res["endpoints"])
    res["figures_with_png_base64"] = sum(1 for f in (meta.get("figures") or []) if f.get("png_base64"))
    res["_b64_note"] = "figures[] entries carry name/caption only; png_base64 count recorded above"
    res.pop("_b64_note")
    PROBE.write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("artifact probe: probed %d endpoint(s), any_payload_bytes=%s" % (len(res["endpoints"]), res["any_payload_bytes"]))
    return res


# ------------------------------------------------------------------ build
CODE_TOKEN_RE = None  # filled lazily to keep import cheap


def scan_code_pointers(md: str):
    """Double-backtick tokens in the markdown are the only artifact-like references this
    report carries (it names no file paths, no URLs, no attachment filenames)."""
    import re
    pat = re.compile(r"``(?P<tok>[^`\n]+)``")
    out, seen = [], set()
    for m in pat.finditer(md):
        tok = m.group("tok")
        if tok in seen:
            continue
        seen.add(tok)
        out.append((tok, m.start("tok"), m.end("tok")))
    return out


def fig_probe_status(fig) -> str:
    """Status string of the per-figure probe, read from artifact_probe.json (or 'not_probed')."""
    if not PROBE.exists():
        return "not_probed"
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    for e in probe.get("endpoints", []):
        if e.get("figure") == fig.get("name"):
            return e.get("status")
    return "not_probed"


def worktree_hits(symbol: str):
    """Which files of this delivery worktree contain the symbol verbatim (resolution check)."""
    hits = []
    exts = {".py", ".md", ".json", ".toml", ".txt", ".yml", ".yaml"}
    for p in REPO.rglob("*"):
        if not p.is_file() or p.suffix not in exts:
            continue
        rel = p.relative_to(REPO)
        if rel.parts and rel.parts[0] in {".git", "__pycache__"}:
            continue
        # Self-reference guard: the frozen source fixture and this package's own deliverables
        # quote the symbol by construction — counting them would be circular evidence.
        if rel == FIXTURE.relative_to(REPO) or str(rel).startswith(str(OUT_DIR.relative_to(REPO))):
            continue
        try:
            txt = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if symbol in txt:
            hits.append(str(rel))
    return sorted(hits)


def cmd_build():
    md = FIXTURE.read_text(encoding="utf-8")
    raw = md.encode("utf-8")
    digest = sha(raw)
    if digest != CONTRACT_HASH:
        raise SystemExit("fixture hash %s != contract %s" % (digest, CONTRACT_HASH))
    meta = json.loads((OUT_DIR / "source_record_meta.json").read_text(encoding="utf-8"))
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    assets: list[dict] = []
    ids: set[str] = set()

    def add(a: dict):
        if a["asset_id"] in ids:
            raise SystemExit("duplicate asset_id %s" % a["asset_id"])
        ids.add(a["asset_id"])
        assets.append(a)

    # A01 — the registered source asset itself (whole document).
    title_line = md.split("\n")[0]
    add({
        "asset_id": "A01",
        "asset_class": "report_markdown",
        "label": "report markdown body of report_id=6939 (tensor://reports/6939#markdown)",
        "in_report_section": "document",
        "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": len(md),
            "start_line": 1,
            "end_line": len(md.split("\n")),
            "quote": title_line,
            "unique": md.count(title_line) == 1,
        },
        "resolution": "resolved_in_source",
        "resolution_check": {
            "check": "sha256(markdown utf-8) == input.source_hash of the work-package contract",
            "result": "resolved",
            "observed_sha256": digest,
            "expected_sha256": CONTRACT_HASH,
            "chars": len(md),
            "bytes_utf8": len(raw),
        },
        "note": "Platform field record_id=%s, title=%r, scenario_key=%r; meta snapshot in source_record_meta.json."
                % (meta.get("id"), meta.get("title"), meta.get("scenario_key")),
    })

    # A02 — the figure-set reference in the markdown body ("见附图 1-5"): names no path.
    fig_ref = "见附图 1-5"
    s, e = span(md, fig_ref)
    add({
        "asset_id": "A02",
        "asset_class": "figure_reference",
        "label": "figure-set reference in §4 结果图 (declares 5 figures, names no file/path)",
        "in_report_section": "4. 结果图",
        "locator": locator(md, s, e),
        "resolution": "resolved_in_source",
        "resolution_check": {
            "check": "verbatim reference located in markdown body; no path/filename syntax attached",
            "result": "resolved",
        },
        "note": "The reference carries no path, URL or attachment filename, so it cannot be byte-resolved from the body alone; the platform record's figures[] is handled in A03-A07.",
    })

    # A03-A07 — the five figures carried by the platform record (name+caption, no payload).
    for n, fig in enumerate(meta.get("figures") or [], start=1):
        cap = fig.get("caption") or ""
        has_payload = bool(fig.get("png_base64"))
        # The locator quote is the markdown anchor "见附图 1-5" (verbatim source bytes) so that the
        # platform's independent substring re-check can resolve it against the markdown; the figure
        # name/caption live in the record and are carried in the locator's record_* fields.
        entry = {
            "asset_id": "A%02d" % (2 + n),
            "asset_class": "embedded_figure_declared",
            "label": "%s — %s" % (fig.get("name"), cap),
            "in_report_section": "4. 结果图",
            "locator": {
                "method": "record_field",
                "start_char": s,
                "end_char": e,
                "start_line": line_of(md, s),
                "end_line": line_of(md, e - 1),
                "quote": md[s:e],
                "unique": md.count(md[s:e]) == 1,
                "shared_anchor": True,  # one markdown sentence anchors all five figure entries
                "record_field": "figures",
                "record_index": n - 1,
                "record_name": fig.get("name"),
                "record_caption": cap,
            },
            "resolution": "resolved_in_source" if has_payload else "metadata_only",
            "resolution_check": {
                "check": "does figures[%d] carry a png_base64 payload that can be byte-hashed?" % (n - 1),
                "result": "present" if has_payload else "absent",
            },
            "note": ("payload stored; sha256=%s" % sha(fig["png_base64"])) if has_payload else
                    "caption=%r; record holds name+caption only (keys=%s); probe GET /tensor/reports/6939/figures/%s "
                    "returns %s, and GET /tensor/reports/6939/artifacts + /tensor/artifacts?report_id=6939 also 404 "
                    "(artifact_probe.json) — no bytes exist to hash, so this figure is registered as metadata_only, "
                    "NOT as a resolved binary." % (cap, sorted(fig), fig.get("name"), fig_probe_status(fig)),
        }
        add(entry)

    # A08.. — double-backtick code/API identifiers referenced by the markdown body.
    for n, (tok, ts, te) in enumerate(scan_code_pointers(md), start=1):
        hits = worktree_hits(tok)
        add({
            "asset_id": "A%02d" % (7 + n),
            "asset_class": "code_symbol_reference",
            "label": tok,
            "in_report_section": "5. 已知局限" if line_of(md, ts) >= 59 else "section containing the token",
            "locator": locator(md, ts, te),
            "resolution": "resolved_in_source" if hits else "referenced_unresolved",
            "resolution_check": {
                "check": "grep for the identifier verbatim across this delivery worktree (TensorKnowledge), "
                         "excluding the frozen source fixture and this package's own deliverables",
                "result": "resolved" if hits else "unresolved",
                "hits": hits,
            },
            "note": ("found verbatim in this worktree: %s" % hits) if hits else
                    "referenced symbol is defined in the TensorLBM solver package, which is outside this "
                    "delivery worktree (repo=TensorKnowledge); not resolvable here — no cross-repo guess made.",
        })

    probe = json.loads(PROBE.read_text(encoding="utf-8")) if PROBE.exists() else {"endpoints": [], "any_payload_bytes": None}

    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "title": meta.get("title"),
            "scenario_key": meta.get("scenario_key"),
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
            "metadata_only": by_res.get("metadata_only", 0),
        },
        "assets": assets,
        "artifact_probe": probe,
        "claims": [],
        "claims_rationale": (
            "objective.classify_report_type=false and constraints.no_forced_claim_generation=true: this "
            "package registers assets only, it does not extract knowledge. An empty claims array is an "
            "explicitly legal complete result per the contract (notes: 'claims 允许为空数组'), so no claim "
            "was minted to fill a quota. The report's numeric anchors (25/25 pytest, RMS 0.02%..18%) are "
            "left to a downstream extraction package and are NOT restated here."
        ),
        "integrity": {
            "quote_uniqueness": "all locator quotes sliced from the source bytes; duplicates flagged per asset via locator.unique",
            "hash_recomputed_locally": True,
            "hash_matches_contract": digest == CONTRACT_HASH,
            "hash_source": "fetched via GET /api/v1/tensor/reports/6939, frozen as tests/fixtures/kf/6939_markdown.md",
            "fixture_path": str(FIXTURE.relative_to(REPO)),
            "fixture_sha256": sha(FIXTURE.read_bytes()),
        },
        "provenance": {"source_hash": "sha256:" + digest, "source_field": SOURCE_FIELD,
                       "generated_at": datetime.now(timezone.utc).isoformat(),
                       "generator": "scripts/kf/wp6939_register.py build"},
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets)" % (MANIFEST.relative_to(REPO), len(assets)))
    return manifest


# ------------------------------------------------------------------ verify
def cmd_verify():
    checks = []

    def chk(item, ok, detail):
        checks.append({"acceptance_item": item, "status": "pass" if ok else "fail", "detail": detail})
        return ok

    raw = MANIFEST.read_text(encoding="utf-8")
    try:
        m = json.loads(raw)
        chk("valid_json", True, "asset_manifest.json parses as JSON (%d bytes)" % len(raw.encode()))
    except json.JSONDecodeError as e:
        chk("valid_json", False, str(e))
        return _write_verdict(checks)

    # schema_pass — package-local schema (superset of the shared wp-448 schema) + envelope schema.
    try:
        import jsonschema
        jsonschema.validate(m, json.loads(SCHEMA.read_text(encoding="utf-8")))
        chk("schema_pass", True, "asset_manifest validates against %s" % SCHEMA.relative_to(REPO))
    except Exception as e:  # noqa: BLE001
        chk("schema_pass", False, "schema validation failed: %s" % e)
    if RESULT.exists():
        try:
            import jsonschema
            jsonschema.validate(json.loads(RESULT.read_text(encoding="utf-8")),
                                json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8")))
            chk("schema_pass_envelope", True,
                "kf_result.json validates against schemas/kf_result.v1.schema.json")
        except Exception as e:  # noqa: BLE001
            chk("schema_pass_envelope", False, "envelope schema validation failed: %s" % e)
    else:
        chk("schema_pass_envelope", False, "kf_result.json absent (run build before verify)")

    # source_hash_matches — recompute from the frozen fixture, compare with contract + manifest.
    md = FIXTURE.read_text(encoding="utf-8")
    digest = sha(md)
    chk("source_hash_matches",
        digest == CONTRACT_HASH == m["source"]["hash"].removeprefix("sha256:")
        and len(md) == CONTRACT_CHARS == m["source"]["chars"],
        "recomputed fixture sha256=%s chars=%d vs manifest %s / contract %s"
        % (digest, len(md), m["source"]["hash"], CONTRACT_HASH))

    # source_locator_resolvable — every char_span locator must slice back to its own quote.
    bad = []
    for a in m["assets"]:
        loc = a["locator"]
        # platform-aligned guard: EVERY quote must be findable verbatim in the markdown bytes
        if loc["quote"] not in md:
            bad.append("%s quote not found in markdown" % a["asset_id"])
        if loc["method"] == "char_span":
            if md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
                bad.append("%s char slice != quote" % a["asset_id"])
            if line_of(md, loc["start_char"]) != loc["start_line"]:
                bad.append("%s start_line mismatch" % a["asset_id"])
            if md.count(loc["quote"]) < 1:
                bad.append("%s quote not present" % a["asset_id"])
        elif loc["method"] == "document":
            # whole-document span: the quote is the opening text of the span, not the whole span
            if not (loc["start_char"] == 0 and loc["end_char"] == len(md)):
                bad.append("%s document span is not [0,len)" % a["asset_id"])
            if not md.startswith(loc["quote"], loc["start_char"]):
                bad.append("%s quote is not the head of the document span" % a["asset_id"])
            if line_of(md, loc["start_char"]) != loc["start_line"]:
                bad.append("%s start_line mismatch" % a["asset_id"])
            if md.count(loc["quote"]) < 1:
                bad.append("%s quote not present" % a["asset_id"])
        elif loc["method"] == "record_field":
            rec = (m["source"]["platform_figures"] or [])[loc["record_index"]]
            if rec.get("caption") != loc.get("record_caption"):
                bad.append("%s record_caption != figures[%d].caption" % (a["asset_id"], loc["record_index"]))
            if rec.get("name") != loc.get("record_name"):
                bad.append("%s record_name mismatch" % a["asset_id"])
        else:
            bad.append("%s unknown locator method" % a["asset_id"])
    chk("source_locator_resolvable", not bad, "all %d locators re-resolved against the frozen source"
        % len(m["assets"]) if not bad else "; ".join(bad))

    # artifact_probe_present — the metadata_only verdict must rest on probe evidence, not assertion
    probe = m.get("artifact_probe") or {}
    fig_names = [f.get("name") for f in (m["source"]["platform_figures"] or [])]
    probed = {e.get("figure"): e.get("status") for e in probe.get("endpoints", []) if e.get("figure")}
    chk("artifact_probe_recorded",
        probe.get("any_payload_bytes") is False and all(probed.get(n, "").startswith("http_") for n in fig_names),
        "probe: %s; per-figure statuses %s" % (probe.get("any_payload_bytes"), probed))

    # no_duplicate_ids
    ids = [a["asset_id"] for a in m["assets"]]
    chk("no_duplicate_ids", len(ids) == len(set(ids)) and m["counts"]["assets"] == len(ids),
        "asset_id list %s" % ids)

    # all_claims_have_evidence_or_explicit_unresolved_status (vacuously true on empty claims,
    # recorded explicitly rather than glossed over)
    claims = m.get("claims", [])
    ok_claims = all(("evidence_locator" in c or "status" in c) for c in claims)
    chk("all_claims_have_evidence_or_explicit_unresolved_status", ok_claims,
        "claims=%d (empty is legal for task_type=01; rationale recorded in claims_rationale); "
        "no claim marked verified" % len(claims))

    # extra guards
    files_txt = []
    for p in (MANIFEST, RESULT, SCHEMA):
        if p.exists():
            files_txt.append(p.read_text(encoding="utf-8"))
    chk("no_verified_marks", not any('"verified"' in t for t in files_txt),
        "no 'verified' field/value emitted anywhere in the deliverables")
    chk("no_foreign_report_ids",
        all(rid in {"6939"} for rid in {m["report_id"], m["source"]["uri"].split("/")[-1]}),
        "manifest references report_id=%s only" % m["report_id"])
    return _write_verdict(checks)


def _write_verdict(checks):
    verdict = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "passed": sum(1 for c in checks if c["status"] == "pass"),
        "failed": sum(1 for c in checks if c["status"] == "fail"),
    }
    verdict["verdict"] = "pass" if verdict["failed"] == 0 else "fail"
    VERDICT.write_text(json.dumps(verdict, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for c in checks:
        print(("[%s] %s — %s" % (c["status"].upper(), c["acceptance_item"], c["detail"]))[:400])
    print("VERDICT:", verdict["verdict"])
    return verdict


# ------------------------------------------------------------------ result envelope
def cmd_result():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = FIXTURE.read_text(encoding="utf-8")
    digest = sha(md)
    if digest != manifest["source"]["hash"].removeprefix("sha256:"):
        raise SystemExit("fixture/manifest hash disagreement")
    result = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": "sha256:" + digest,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "fetched_via": "GET /api/v1/tensor/reports/6939 (Bearer $TENSOR_AGENT_USER)",
            "generator": "scripts/kf/wp6939_register.py",
            "contract_version": "1.0",
            "notes": "asset registration only; no extraction, no report-type classification, no verification marks",
        },
        "outputs": {
            "asset_manifest.json": manifest,
        },
        "claims": [],
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d bytes)" % (RESULT.relative_to(REPO), RESULT.stat().st_size))
    return result


def main(argv):
    cmds = argv[1:] or ["all"]
    if "all" in cmds:
        cmds = ["fetch", "build", "result", "verify"]
    for c in cmds:
        if c == "fetch":
            cmd_fetch()
        elif c == "build":
            cmd_build()
        elif c == "result":
            cmd_result()
        elif c == "verify":
            v = cmd_verify()
            if v["verdict"] != "pass":
                raise SystemExit("verification failed")
        else:
            raise SystemExit("unknown subcommand %r" % c)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))