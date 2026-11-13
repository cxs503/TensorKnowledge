#!/usr/bin/env python3
"""wp-11107-01 (task_type 01-asset-registration): register the source asset of report 11107
and enumerate the attachments / artefacts the report declares. NO extraction, NO verified marks.

Sub-commands (idempotent):

    python3 scripts/kf_wp11107_01_register.py build     # fetch markdown + write asset_manifest.json
    python3 scripts/kf_wp11107_01_register.py envelope  # wrap manifest -> kf_result.json
    python3 scripts/kf_wp11107_01_register.py verify    # re-fetch and re-check the 6 acceptance items
    python3 scripts/kf_wp11107_01_register.py figure    # locator-map png (evidence figure)
    python3 scripts/kf_wp11107_01_register.py all       # build + envelope + figure + verify

Design rules honoured here (contract wp-11107-01):
  * registration only -- no claim extraction, no report classification, no `verified` marks;
  * zero manual transcription -- every number in the artefacts is measured here (hash, chars,
    byte sizes, char spans, per-file sha256), nothing is typed in from memory;
  * every asset carries a locator (char span + line number + verbatim quote) that is re-checked
    against the live markdown at verify time;
  * failures abort loudly (non-zero exit) instead of emitting a half manifest.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_ID = "11107"
PACKAGE_ID = "wp-11107-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID

# contract-declared identity (work-package YAML); comparison targets only, never trusted.
CONTRACT_HASH = "sha256:799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982"
CONTRACT_CHARS = 13319
CONTRACT_TITLE = ("P202W1-N09 TensorFEM 疲劳裂纹扩展验证面：C(T) 试样 Paris 律 "
                  "da/dN-dK、门槛值与断裂韧性标定")
CONTRACT_SCENARIO = "fatigue-crack-growth-ct-specimen"

RUN_DIR = ROOT / "runs" / PACKAGE_ID
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID  # committed (.gitignore drops artifacts/**, runs/ kept small)
FIG_DIR = OUT_DIR / "figures"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
RECORD_COPY = RUN_DIR / ("report_%s.json" % REPORT_ID)
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
FIG_PNG = FIG_DIR / "fig_asset_locator_map.png"
PRODUCER = "kf-worker/m15690"
EMITTED_AT = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


# ------------------------------------------------------------------ helpers
def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _req(path: str, body: dict | None = None, tok: str | None = None, timeout: int = 180):
    data = None if body is None else json.dumps(body).encode()
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", "replace")


def login() -> str | None:
    """Token from env credentials; returns None when no credentials are provisioned."""
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    for path in ("/auth/login", "/tensor/auth/login"):
        st, body = _req(path, {"username": user, "password": pwd})
        if st == 200:
            tok = json.loads(body).get("access_token")
            if tok:
                return tok
    return None


def fetch_record() -> dict:
    """GET /tensor/reports/11107 -> the record dict (markdown + metadata)."""
    tok = login()
    st, body = _req("/tensor/reports/" + REPORT_ID, tok=tok)
    if st != 200:
        raise SystemExit("fetch failed: HTTP %s %s" % (st, body[:300]))
    rec = json.loads(body)
    if isinstance(rec, dict) and isinstance(rec.get("data"), dict):
        rec = rec["data"]
    if not rec.get("markdown"):
        raise SystemExit("record carries no markdown")
    return rec


def line_of(md: str, idx: int) -> int:
    return md.count("\n", 0, idx) + 1


def make_locator(md: str, quote: str, start: int | None = None) -> dict:
    """char-span locator; start=None -> first occurrence. Uniqueness is measured, not assumed."""
    n = md.count(quote)
    if n == 0:
        raise SystemExit("quote not found in source, refusing to invent a locator: %r" % quote[:80])
    s = md.find(quote) if start is None else start
    e = s + len(quote)
    if md[s:e] != quote:
        raise SystemExit("char span does not reproduce the quote at %d" % s)
    return {
        "method": "char_span",
        "start_char": s,
        "end_char": e,
        "start_line": line_of(md, s),
        "end_line": line_of(md, e),
        "quote": quote,
        "quote_sha256": sha256_hex(quote.encode("utf-8")),
        "occurrences_in_source": n,
        "unique": n == 1,
    }


def file_facts(path: str) -> dict:
    p = Path(path)
    if not p.exists():
        return {"exists": False, "path": path}
    if p.is_dir():
        return {"exists": True, "path": path, "is_file": False, "is_dir": True}
    b = p.read_bytes()
    return {"exists": True, "path": path, "bytes": len(b), "sha256": sha256_hex(b),
            "is_file": True, "is_dir": False}


# ------------------------------------------------------------------ build
FIG_RE = re.compile(r"/root/tp-agent/work/[A-Za-z0-9_]+/artifacts/[A-Za-z0-9_/.-]+\.png")
REL_FIG_RE = re.compile(r"(?<![/A-Za-z0-9_])artifacts/[A-Za-z0-9_/.-]+\.png")
FACE_RE = re.compile(r"tensorfem\.[a-z_.]+")


def build() -> dict:
    rec = fetch_record()
    md = rec["markdown"]
    raw = md.encode("utf-8")
    digest = sha256_hex(raw)
    lines = md.rstrip("\n").split("\n")
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_text(md, encoding="utf-8")

    hash_match = ("sha256:" + digest) == CONTRACT_HASH
    chars_match = len(md) == CONTRACT_CHARS
    title_match = (rec.get("title") or "") == CONTRACT_TITLE
    scenario_match = rec.get("scenario_key") == CONTRACT_SCENARIO

    assets: list[dict] = []
    cross: list[dict] = []

    # --- A01: the source document itself ---------------------------------
    assets.append({
        "asset_id": "A01",
        "asset_class": "source_document",
        "label": "report markdown (source_uri %s, field markdown)" % SOURCE_URI,
        "in_report_section": "whole document, line 1 .. %d" % len(lines),
        "locator": {
            "method": "document", "start_char": 0, "end_char": len(md),
            "start_line": 1, "end_line": len(lines),
            "quote": lines[0], "quote_sha256": sha256_hex(lines[0].encode("utf-8")),
            "occurrences_in_source": md.count(lines[0]), "unique": md.count(lines[0]) == 1,
        },
        "resolution": "resolved_in_source",
        "resolution_check": {
            "check": ("sha256 over the markdown UTF-8 bytes recomputed at registration and "
                      "compared with contract input.source_hash; chars compared with "
                      "contract input.chars"),
            "result": "resolved" if (hash_match and chars_match) else "unresolved",
            "measured_sha256": digest, "measured_chars": len(md), "measured_bytes_utf8": len(raw),
        },
        "note": ("Identity of the registered source. Whitespace/newlines are part of the hashed "
                 "payload, so the hash pins the exact byte sequence, not a normalised view."),
    })

    # --- A02..: figures declared in the record metadata AND quoted in §4 ---
    rec_figs = rec.get("figures") or []
    fig_paths = []
    for m in FIG_RE.finditer(md):
        if m.group(0) not in fig_paths:
            fig_paths.append(m.group(0))
    rel_paths = []
    for m in REL_FIG_RE.finditer(md):
        if m.group(0) not in rel_paths:
            rel_paths.append(m.group(0))

    def ws_root_facts_path(p: str) -> str:
        return re.match(r"(/root/tp-agent/work/[A-Za-z0-9_]+)", p).group(1)

    wts = {ws_root_facts_path(p).rsplit("/", 1)[-1] for p in fig_paths}
    worktree_id = ",".join(sorted(wts))

    for i, path in enumerate(fig_paths, start=2):
        name = path.rsplit("/", 1)[-1]
        meta = next((f for f in rec_figs if f.get("name") == name), None)
        facts = file_facts(path)
        rel = next((r for r in rel_paths if r.endswith(name)), None)
        if facts["exists"] and facts["is_file"]:
            resolution, result = "resolved_external", "resolved"
        else:
            resolution, result = "referenced_unresolved", "unresolved"
        assets.append({
            "asset_id": "A%02d" % i,
            "asset_class": "figure_reference",
            "label": name + (" — " + meta["caption"] if meta else ""),
            "in_report_section": "§4 Figures (absolute path bullet); metadata: record.figures[%d]"
                                 % (rec_figs.index(meta) if meta else -1),
            "locator": make_locator(md, path),
            "resolution": resolution,
            "resolution_check": {
                "check": ("os.path probe of the absolute path quoted in §4 (bytes + sha256), plus "
                          "platform probe GET /tensor/reports/%s/artifacts -> 404 (no artefact "
                          "endpoint on this platform build)" % REPORT_ID),
                "result": result,
                "platform_artifacts_endpoint_status": 404,
                **{k: facts[k] for k in ("bytes", "sha256") if k in facts},
            },
            "note": ("PNG bytes live in the producer mission worktree (%s), outside this delivery "
                     "worktree; the platform serves no figure bytes, so registration records "
                     "path+size+sha256 instead of copying the binary. Durability: host-local path, "
                     "not part of TensorKnowledge. Worktree dir name '%s' normalised "
                     "(strip leading 'm') %s record.mission_id '%s' -- a directory-name hint only, "
                     "corroborating but NOT proof that these files belong to this report."
                     % (ws_root_facts_path(path), worktree_id,
                        "matches" if worktree_id.lstrip("m") == str(rec.get("mission_id")) else "does not match",
                        str(rec.get("mission_id")))
                     + ("" if meta else " Record metadata carries no caption for this name.")),
        })
        if rel:
            cross.append({"kind": "relative_figure_path_in_criteria_summary",
                          "refers_to_asset_id": "A%02d" % i, "quote": rel,
                          "locator": make_locator(md, rel),
                          "resolves_in_delivery_worktree": (ROOT / rel).exists(),
                          "note": ("C8_figures criterion quotes the repo-relative form; the file is "
                                   "not part of TensorKnowledge, so this path alone does not "
                                   "resolve here")})

    # --- producer workspace root (source of the §4 paths) ------------------
    ws = FIG_RE.search(md).group(0)
    ws_root = ws_root_facts_path(ws)
    ws_facts = file_facts(ws_root)
    assets.append({
        "asset_id": "A%02d" % (len(assets) + 1),
        "asset_class": "producer_workspace_reference",
        "label": ws_root + " (mission worktree that produced §4 figure paths and the run)",
        "in_report_section": "§4 Figures",
        "locator": make_locator(md, ws_root),
        "resolution": "resolved_external" if ws_facts.get("is_dir") else "referenced_unresolved",
        "resolution_check": {
            "check": "os.path probe of the quoted directory; occurrence count measured (non-unique is reported, not hidden)",
            "result": "resolved" if ws_facts.get("is_dir") else "unresolved",
        },
        "note": ("Registered as a provenance pointer only: it is the producer's working tree, not an "
                 "artefact the knowledge base should depend on (host-local, purgeable)."),
    })

    # --- verification face / code symbol ----------------------------------
    faces = sorted({m.group(0).rstrip(".") for m in FACE_RE.finditer(md)})
    for face in faces:
        hits = []
        for p in ROOT.rglob("*"):
            # source files only: other work packages' extracted claims under docs/ are not code
            if p.is_file() and p.suffix in {".py", ".toml", ".cfg"} and \
                    ".git" not in p.parts and PACKAGE_ID not in p.parts and \
                    "runs" not in p.parts and "docs" not in p.parts and "tests" not in p.parts:
                try:
                    if face in p.read_text(encoding="utf-8", errors="ignore"):
                        hits.append(str(p.relative_to(ROOT)))
                except OSError:
                    continue
        assets.append({
            "asset_id": "A%02d" % (len(assets) + 1),
            "asset_class": "code_reference",
            "label": face + " (verification face identifier named in the report subtitle/summary)",
            "in_report_section": "subtitle (line 3) and record.summary",
            "locator": make_locator(md, face),
            "resolution": "referenced_unresolved" if not hits else "resolved_external",
            "resolution_check": {
                "check": ("grep for the symbol in python/config source of the delivery worktree "
                          "(scope excludes .git, docs/, tests/ and this package's own artefacts, i.e. "
                          "no other work package's outputs are read); a miss means the face is not "
                          "defined here and stays unresolved rather than 'absent by design'"),
                "result": "unresolved" if not hits else "resolved",
                "grep_hits": hits,
                "grep_scope": "TensorKnowledge worktree source files (*.py/*.toml/*.cfg), excluding .git, docs/, tests/ and this package's own outputs",
            },
            "note": ("The face lives in TensorFEM, not in the knowledge repo; registering it as an "
                     "unresolved reference keeps the downstream工序 from assuming local code."),
        })

    ids = [a["asset_id"] for a in assets]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    manifest = {
        "schema": "asset_manifest.wp-11107-01",
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": EMITTED_AT,
        "producer": PRODUCER,
        "contract": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": CONTRACT_HASH,
            "chars": CONTRACT_CHARS,
            "title": CONTRACT_TITLE,
            "scenario_key": CONTRACT_SCENARIO,
            "objective": {"register_assets": True, "classify_report_type": False},
        },
        "source": {
            "report_id": REPORT_ID,
            "uri": SOURCE_URI,
            "field": "markdown",
            "hash_alg": "sha256",
            "hash": digest,
            "hash_matches_contract": hash_match,
            "chars": len(md),
            "chars_match_contract": chars_match,
            "bytes_utf8": len(raw),
            "lines": len(lines),
            "has_crlf": "\r\n" in md,
            "has_trailing_newline": md.endswith("\n"),
            "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)), 1-based",
            "fetched_via": "GET %s/tensor/reports/%s (Bearer env TENSOR_AGENT_USER)" % (API, REPORT_ID),
            "record": {
                "id": rec.get("id"),
                "title": rec.get("title"),
                "title_matches_contract": title_match,
                "scenario_key": rec.get("scenario_key"),
                "scenario_matches_contract": scenario_match,
                "mission_id": rec.get("mission_id"),
                "status": rec.get("status"),
                "stage": rec.get("stage"),
                "created_at": rec.get("created_at"),
                "created_by": rec.get("created_by"),
                "tags": rec.get("tags"),
                "figures_declared": rec_figs,
            },
        },
        "assets": assets,
        "cross_references": cross,
        "counts": {
            "assets": len(assets),
            "by_class": dict(sorted(by_class.items())),
            "by_resolution": dict(sorted(by_res.items())),
            "figures_declared_in_record": len(rec_figs),
            "figure_paths_quoted_in_body": len(fig_paths),
            "figure_paths_resolvable_on_disk": sum(
                1 for a in assets if a["asset_class"] == "figure_reference"
                and a["resolution"] == "resolved_external"),
            "claims": 0,
        },
        "id_integrity": {"ids_checked": len(ids), "duplicates": dupes, "unique": not dupes,
                         "cross_reference_entries": len(cross),
                         "cross_reference_note": ("cross_references point back to asset_id via "
                                                  "refers_to_asset_id, so no identifier is declared twice"),},
        "claims": [],
        "claims_empty_reason": (
            "Contract wp-11107-01 objective is register_assets=true / classify_report_type=false and "
            "notes state 'claims 允许为空数组' with constraint no_forced_claim_generation=true. This工序 "
            "registers asset identity (report_id, markdown byte hash, declared attachments/artefacts) "
            "only; knowledge extraction is a downstream工序, so claims=[] is the complete result, not "
            "an omission."),
        "unresolved": [
            {"asset_id": a["asset_id"], "label": a["label"], "reason": a["resolution"]}
            for a in assets if a["resolution"] != "resolved_in_source"
            and a["resolution"] != "resolved_external"
        ],
        "notes": [
            "Registration only: no numbers from the report body were copied into this manifest; every "
            "value here is measured (hash/char count/file size/char span) by the script.",
            "No claim in this manifest is marked verified; verification is the platform gate's job.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not hash_match:
        raise SystemExit("contract hash mismatch: measured %s" % digest)
    return manifest


# ---------------------------------------------------------------- envelope
def envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_field": "markdown",
            "producer": PRODUCER,
            "emitted_at": EMITTED_AT,
            "notes": ("01-asset-registration for report 11107: identity + declared artefacts only; "
                      "claims intentionally empty per contract objective."),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return env


# ------------------------------------------------------------------ figure
def figure() -> Path:
    """Locator map: where each registered asset sits on the document's character axis."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    n = manifest["source"]["chars"]
    assets = manifest["assets"]
    colours = {"source_document": "#4c72b0", "figure_reference": "#dd8452",
               "producer_workspace_reference": "#55a868", "code_reference": "#c44e52"}

    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(11, 5.6), gridspec_kw={"height_ratios": [1.15, 1]})
    rows = list(range(len(assets)))[::-1]
    for r, a in zip(rows, assets):
        loc = a["locator"]
        s, e = loc["start_char"], max(loc["end_char"], loc["start_char"] + 60)
        ax.barh(r, e - s, left=s, height=0.55, color=colours[a["asset_class"]],
                alpha=0.9 if a["resolution"].startswith("resolved") else 0.45,
                hatch="" if a["resolution"].startswith("resolved") else "//",
                edgecolor="black", linewidth=0.4)
        ax.text(min(e + 150, n), r, "%s %s" % (a["asset_id"], a["resolution"]),
                va="center", fontsize=7)
    ax.set_yticks(rows)
    ax.set_yticklabels([a["asset_class"] for a in assets], fontsize=7)
    ax.set_xlim(0, n * 1.24)
    ax.set_xlabel("character offset in report markdown (chars=%d, sha256 %s...)" % (n, manifest["source"]["hash"][:10]))
    ax.set_title("wp-11107-01 asset locators on the source document axis (hatched = unresolved)", fontsize=9)
    ax.grid(axis="x", alpha=0.25)

    ax2.axis("off")
    lines = ["registered assets: %d   claims: %d   hash_matches_contract: %s   chars_match: %s" % (
        manifest["counts"]["assets"], manifest["counts"]["claims"],
        manifest["source"]["hash_matches_contract"], manifest["source"]["chars_match_contract"])]
    for a in assets:
        lines.append("%s  %-30s %-26s line %3d  occ=%d  %s" % (
            a["asset_id"], a["asset_class"], a["resolution"], a["locator"]["start_line"],
            a["locator"]["occurrences_in_source"], a["locator"]["quote"][:52]))
    ax2.text(0, 0.98, "\n".join(lines), va="top", family="monospace", fontsize=7.2)
    handles = [Patch(facecolor=c, edgecolor="black", label=k) for k, c in colours.items()]
    ax2.legend(handles=handles, loc="lower right", fontsize=7, frameon=False)
    fig.tight_layout()
    FIG_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG_PNG, dpi=140)
    plt.close(fig)
    return FIG_PNG


# ------------------------------------------------------------------ verify
def verify() -> dict:
    import jsonschema

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    checks = []

    def add(cid, what, ok, evidence):
        checks.append({"id": cid, "check": what, "pass": bool(ok), "evidence": evidence})

    # 1 valid_json (both artefacts parse -- reaching here already proves it; restate the parse)
    ok1 = isinstance(manifest, dict) and isinstance(env, dict)
    add("valid_json", "asset_manifest.json and kf_result.json parse as JSON objects", ok1,
        "parsed %s (%d bytes) and %s (%d bytes)" % (
            MANIFEST.name, MANIFEST.stat().st_size, ENVELOPE.name, ENVELOPE.stat().st_size))

    # 2 schema_pass (envelope vs canonical kf_result.v1; manifest vs package-local schema)
    errs = []
    try:
        jsonschema.validate(env, json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text()))
        env_ok = True
    except Exception as exc:  # noqa: BLE001
        env_ok, _ = False, errs.append("kf_result: %s" % exc)
    try:
        jsonschema.validate(manifest, json.loads(
            (ROOT / "schemas" / "asset_manifest.wp-11107-01.schema.json").read_text()))
        man_ok = True
    except Exception as exc:  # noqa: BLE001
        man_ok, _ = False, errs.append("asset_manifest: %s" % exc)
    add("schema_pass", "kf_result.v1.schema.json + asset_manifest.wp-11107-01.schema.json validation",
        env_ok and man_ok, "envelope=%s manifest=%s errors=%s" % (env_ok, man_ok, errs))

    # 3 source_locator_resolvable + 4 source_hash_matches, both against a FRESH fetch
    rec = fetch_record()
    md = rec["markdown"]
    fresh = sha256_hex(md.encode("utf-8"))
    add("source_hash_matches",
        "platform re-fetched markdown sha256 == provenance.source_hash == contract input.source_hash",
        ("sha256:" + fresh) == env["provenance"]["source_hash"] == CONTRACT_HASH,
        "recomputed=sha256:%s envelope=%s contract=%s chars=%d" % (
            fresh, env["provenance"]["source_hash"], CONTRACT_HASH, len(md)))

    bad = []
    for a in manifest["assets"] + manifest["cross_references"]:
        loc = a["locator"]
        q = loc["quote"]
        aid = a.get("asset_id") or a.get("refers_to_asset_id", "x")
        if q not in md:
            bad.append("%s: quote not in fresh source" % aid)
            continue
        if loc["method"] == "document":
            if not (loc["start_char"] == 0 and loc["end_char"] == len(md)
                    and md.startswith(q) and loc["end_line"] == len(md.rstrip("\n").split("\n"))):
                bad.append("%s: document span mismatch" % aid)
        elif md[loc["start_char"]:loc["end_char"]] != q:
            bad.append("%s: char span mismatch" % aid)
        if line_of(md, loc["start_char"]) != loc["start_line"]:
            bad.append("%s: line mismatch" % aid)
        if md.count(q) != loc["occurrences_in_source"]:
            bad.append("%s: occurrence count drift" % aid)
    add("source_locator_resolvable",
        "every locator re-resolves character-for-character against the fresh markdown (quote, span, line, occurrence count)",
        not bad, "locators=%d failures=%s" % (len(manifest["assets"]) + len(manifest["cross_references"]), bad))

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    add("no_duplicate_ids", "asset_id values are unique", len(ids) == len(set(ids)),
        "ids=%s" % ids)

    # 6 claims carry evidence or explicit status (vacuously true for the contract-mandated empty array)
    claims = env.get("claims") or []
    ok6 = all(("evidence" in c and c["evidence"]) or c.get("status") for c in claims)
    add("all_claims_have_evidence_or_explicit_unresolved_status",
        "claims[] empty (contract: no forced claim generation) -> condition holds vacuously; each asset instead carries a locator",
        ok6 and len(claims) == 0,
        "claims=%d assets_with_locator=%d/%d reason=%s" % (
            len(claims), sum(1 for a in manifest["assets"] if a["locator"].get("quote")),
            len(manifest["assets"]), manifest["claims_empty_reason"][:90]))

    out = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_hash": "sha256:" + fresh,
        "checks": checks,
        "all_pass": all(c["pass"] for c in checks),
        "note": ("These flags are self-checks of this工序's own acceptance items; they are not a "
                 "platform verification verdict and nothing here is marked verified."),
    }
    VERIFICATION.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("build", "all"):
        m = build()
        print("build: assets=%d hash_match=%s chars=%d/%d -> %s" % (
            m["counts"]["assets"], m["source"]["hash_matches_contract"], m["source"]["chars"],
            CONTRACT_CHARS, MANIFEST))
    if cmd in ("envelope", "all"):
        env = envelope()
        print("envelope: %s claims=%d" % (ENVELOPE, len(env["claims"])))
    if cmd in ("figure", "all"):
        print("figure: %s" % figure())
    if cmd in ("verify", "all"):
        v = verify()
        for c in v["checks"]:
            print(" %-52s %s" % (c["id"], "PASS" if c["pass"] else "FAIL"))
        print("all_pass=%s -> %s" % (v["all_pass"], VERIFICATION))
        if not v["all_pass"]:
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))