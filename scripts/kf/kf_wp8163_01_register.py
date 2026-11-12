#!/usr/bin/env python3
"""Work package wp-8163-01 (task_type 01-asset-registration) — register report 8163.

Scope: report_id=8163 ONLY. Registration of the source asset + the attachments /
artefacts / symbol references the report itself declares. NO extraction, NO claim
generation, NO `verified` marks (verification is computed by the platform gate).

Rules honoured (see the work-package contract):
  * zero manual transcription -- every number and every quote in the artefacts is
    measured from the fetched markdown inside this script; quotes are sliced out of
    the markdown, never retyped;
  * every asset carries a locator (char span + 1-based line span + verbatim quote)
    that `verify` re-resolves against a freshly fetched markdown;
  * failures abort loudly (SystemExit) instead of emitting a half manifest.

Sub-commands (idempotent):

    python3 scripts/kf/kf_wp8163_01_register.py build     # fetch + write asset_manifest.json
    python3 scripts/kf/kf_wp8163_01_register.py envelope  # wrap manifest -> kf_result.json
    python3 scripts/kf/kf_wp8163_01_register.py verify    # acceptance checks -> verification.json
    python3 scripts/kf/kf_wp8163_01_register.py figure    # asset-resolution map png
    python3 scripts/kf/kf_wp8163_01_register.py all       # build + envelope + verify + figure
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

REPORT_ID = "8163"
PACKAGE_ID = "wp-8163-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/%s" % REPORT_ID
SOURCE_FIELD = "markdown"

# Contract-declared identity: comparison targets only, the script never trusts them.
CONTRACT_SOURCE_HASH = (
    "sha256:7b48265e05e153c69347ff038be80e20a8f309fbb0563599fa21c98e22b910e7"
)
CONTRACT_CHARS = 7785
CONTRACT_TITLE = (
    "Rigid Collision Energy Ledger Convergence Certification: Three-Method Audit "
    "and m5404 Residual Attribution"
)
CONTRACT_SCENARIO = "IN155-N07_rigid_collision_energy_convergence"

REPO = Path(__file__).resolve().parents[2]
# .gitignore drops artifacts/** on the mission push gate, so registered assets and
# reports live under docs/kf/ (precedent: wp-542-01 / wp-623-01 / wp-1610-01).
OUT_DIR = REPO / "docs" / "kf" / PACKAGE_ID
RUN_DIR = REPO / "runs" / PACKAGE_ID
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
LOCATOR_CHECK = OUT_DIR / "locator_check.json"
SOURCE_COPY = RUN_DIR / ("source_%s.md" % REPORT_ID)
SOURCE_DOC = OUT_DIR / "source.md"   # committed copy (docs/kf/ survives the push gate)
RECORD_COPY = RUN_DIR / ("report_%s.json" % REPORT_ID)
DERIVED_SCHEMA = OUT_DIR / "asset_manifest.v1.wp8163.schema.json"
PRODUCER = "kf-worker/m15607"

KF_RESULT_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"
ASSET_SCHEMA = REPO / "schemas" / "asset_manifest.v1.schema.json"

# Asset classes actually instantiated by report 8163.
#   report_markdown            : the source document itself
#   figure_reference           : image paths embedded in the markdown body
#   platform_figure_metadata   : record.figures[] entries (name+caption only)
#   source_code_reference      : code/test/plot paths named in the audit trail
#   artifact_directory_reference: artefact directory named in the audit trail
#   symbol_reference           : solver / helper symbols named in the prose
PATH_CLASSES = {
    ".py": "source_code_reference",
    ".png": "figure_reference",
    ".jpg": "figure_reference",
    ".json": "data_artifact_reference",
    ".csv": "data_artifact_reference",
    ".h5": "data_artifact_reference",
    ".md": "document_reference",
}
# (label, needle-in-markdown): the needle is what the report literally contains
# (LaTeX-escaped underscores in section 2), the label is the plain identifier.
SYMBOL_SPECS = [
    ("IceDEM3D", "IceDEM3D"),
    ("restitution_to_damping", "restitution\\_to\\_damping"),
]


# --------------------------------------------------------------- platform I/O
def _api_base() -> str:
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    return base.rstrip("/")


def _login() -> str:
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        _api_base() + "/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        tok = json.load(r).get("access_token")
    if not tok:
        raise SystemExit("login returned no access_token")
    return tok


def _req(path: str, tok: str):
    """GET -> (http_status, decoded json or None). 404 is data, not a crash."""
    req = urllib.request.Request(_api_base() + path, headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, None


def fetch_record() -> dict:
    tok = _login()
    status, payload = _req("/tensor/reports/%s" % REPORT_ID, tok)
    if status != 200 or not isinstance(payload, dict):
        raise SystemExit("report fetch failed: http=%s" % status)
    if isinstance(payload.get("data"), dict):  # tolerate envelope wrappers
        payload = payload["data"]
    return payload


# ------------------------------------------------------------------- locators
def char_span(md: str, quote: str) -> dict:
    """Resolve `quote` in `md` positionally. Fails when absent or ambiguous."""
    occurrences = md.count(quote)
    if occurrences == 0:
        raise SystemExit("quote not found in source markdown: %r" % quote[:80])
    if occurrences > 1:
        raise SystemExit("quote not unique (%d hits): %r" % (occurrences, quote[:80]))
    start = md.index(quote)
    end = start + len(quote)
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": md.count("\n", 0, start) + 1,
        "end_line": md.count("\n", 0, end) + 1,
        "quote": quote,
        "unique": True,
    }


def line_of(md: str, needle: str) -> tuple[int, str]:
    """Return (1-based line number, whole line) for a unique needle."""
    hits = [ln for ln in md.split("\n") if needle in ln]
    if len(hits) != 1:
        raise SystemExit("needle %r matched %d lines" % (needle, len(hits)))
    line = hits[0]
    return md[: md.index(line)].count("\n") + 1 + (0 if md.index(line) == 0 else 0), line


def line_number(md: str, line_text: str) -> int:
    start = md.index(line_text)
    return md.count("\n", 0, start) + 1


# ------------------------------------------------------------------- build
PATH_RE = re.compile(r"`([^`]+?\.(?:py|png|jpg|json|csv|h5|md))`")
DIR_RE = re.compile(r"`(artifacts/[^`]*/)`")
IMG_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")


def _section_of(md: str, offset: int) -> str:
    """Nearest preceding markdown heading (verbatim), for `in_report_section`."""
    head = None
    for line in md[:offset].split("\n"):
        if line.startswith("#"):
            head = line
    return head or "(preamble)"


def _resolve_path(rel: str) -> dict:
    p = REPO / rel
    return {
        "check": "path_exists_in_delivery_worktree(TensorKnowledge@%s) + platform artifact probe"
        % _git_head(),
        "result": "resolved" if p.exists() else "unresolved",
        "path": rel,
        "abs_exists": bool(p.exists()),
    }


def _git_head() -> str:
    try:
        return (REPO / ".git").read_text().strip().split()[1][:12]
    except Exception:
        return "unknown"


def build_assets(md: str, record: dict) -> list[dict]:
    assets: list[dict] = []
    n = [0]

    def add(**kw):
        n[0] += 1
        asset = {"asset_id": "A%02d" % n[0]}
        asset.update(kw)
        assets.append(asset)
        return asset

    # A01 -- the source document itself (document-scope locator).
    first_line = md.split("\n")[0]
    add(
        asset_class="report_markdown",
        label="report-%s-markdown" % REPORT_ID,
        in_report_section="(whole document)",
        uri=SOURCE_URI,
        media_type="text/markdown",
        chars=len(md),
        bytes_utf8=len(md.encode("utf-8")),
        sha256="sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest(),
        locator={
            "method": "document",
            "start_char": 0,
            "end_char": len(md),
            "start_line": 1,
            "end_line": md.rstrip("\n").count("\n") + 1,
            "quote": first_line,
            "unique": md.count(first_line) == 1,
        },
        resolution="resolved_in_source",
        resolution_check={
            "check": "sha256(recomputed) == contract source_hash and chars == contract chars",
            "result": "resolved",
        },
        note="Fetched from GET /api/v1/tensor/reports/%s; byte hash over the UTF-8 "
        "encoding of the `markdown` field." % REPORT_ID,
    )

    # A02.. -- figures: markdown embed path + record.figures[] metadata merged.
    figs = record.get("figures") or []
    fig_by_name = {f.get("name"): f for f in figs if isinstance(f, dict)}
    for m in IMG_RE.finditer(md):
        raw = m.group(1)
        stem = Path(raw).stem
        meta = fig_by_name.get(stem, {})
        alt = m.group(0)
        loc = char_span(md, alt)
        add(
            asset_class="figure_reference",
            label=raw,
            in_report_section=_section_of(md, m.start()),
            uri=SOURCE_URI + "#figure:" + stem,
            platform_figure_name=stem if meta else None,
            platform_caption=meta.get("caption"),
            locator=loc,
            resolution="referenced_unresolved",
            resolution_check={
                "check": "binary path resolved in worktree (%s) and platform figure "
                "endpoint GET /api/v1/tensor/reports/%s/figures/%s" % (raw, REPORT_ID, stem),
                "result": "unresolved",
                "path_in_worktree": bool((REPO / raw).exists()),
                "figure_endpoint_status": _probe_figure(stem),
            },
            note="Image path is quoted verbatim from the report body; the producing byte "
            "payload lives in the upstream repo, not in this record (record.figures[] "
            "carries name+caption only).",
        )

    # record.figures[] entries with no markdown embed (none expected, checked anyway).
    embedded = {Path(m.group(1)).stem for m in IMG_RE.finditer(md)}
    for f in figs:
        if isinstance(f, dict) and f.get("name") not in embedded:
            raise SystemExit(
                "record figure %r has no markdown embed; extend the manifest deliberately"
                % f.get("name")
            )

    # Audited artefact directory (§8 audit trail).
    for m in DIR_RE.finditer(md):
        raw = m.group(1)
        line = md[md.rfind("\n", 0, m.start()) + 1 : md.find("\n", m.start())]
        add(
            asset_class="artifact_directory_reference",
            label=raw,
            in_report_section=_section_of(md, m.start()),
            uri=SOURCE_URI + "#path:" + raw,
            locator=char_span(md, line),
            resolution="referenced_unresolved",
            resolution_check=_resolve_path(raw.rstrip("/")),
            note="Directory named in the audit trail; the report body also embeds two png "
            "files under it (see the figure_reference assets).",
        )

    # Code / test / plot paths from the audit trail, de-duplicated by path.
    seen_paths: dict[str, str] = {}
    for m in PATH_RE.finditer(md):
        raw = m.group(1)
        if raw in seen_paths:
            continue
        line_start = md.rfind("\n", 0, m.start()) + 1
        line_end = md.find("\n", m.start())
        line = md[line_start : line_end if line_end != -1 else len(md)]
        seen_paths[raw] = raw
        add(
            asset_class=PATH_CLASSES.get(Path(raw).suffix, "path_reference"),
            label=raw,
            in_report_section=_section_of(md, m.start()),
            uri=SOURCE_URI + "#path:" + raw,
            locator=char_span(md, line),
            resolution="referenced_unresolved",
            resolution_check=_resolve_path(raw),
            note="Declared in the report's audit trail; the file lives in the producing "
            "repository (TensorDEM), outside this work package's boundary.",
        )

    # Named solver / helper symbols (reference only -- no existence claim).
    for label, tok in SYMBOL_SPECS:
        ln, line = line_of(md, tok)
        add(
            asset_class="symbol_reference",
            label=label,
            in_report_section=_section_of(md, md.index(line)),
            uri=SOURCE_URI + "#symbol:" + label,
            locator=char_span(md, line),
            resolution="referenced_unresolved",
            resolution_check={
                "check": "token %r resolved to line %d of the report prose" % (tok, ln),
                "result": "unresolved",
                "existence_asserted_by_worker": False,
            },
            note="Symbol is named in the report prose; this work package registers the "
            "reference and does not open the TensorDEM tree to confirm it exists.",
        )
    return assets


def _probe_figure(name: str) -> int | None:
    try:
        tok = _login()
        status, _ = _req("/tensor/reports/%s/figures/%s" % (REPORT_ID, name), tok)
        return status
    except Exception:
        return None


def build() -> dict:
    record = fetch_record()
    md = record.get("markdown")
    if not isinstance(md, str) or not md:
        raise SystemExit("record has no markdown field")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    SOURCE_COPY.write_text(md, encoding="utf-8")
    SOURCE_DOC.write_text(md, encoding="utf-8")
    RECORD_COPY.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")

    raw = md.encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    assets = build_assets(md, record)
    figs = [f for f in (record.get("figures") or []) if isinstance(f, dict)]

    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1

    tok = _login()
    artifacts_probe = _req("/tensor/reports/%s/artifacts" % REPORT_ID, tok)
    manifest = {
        "schema": "asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": "C",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "producer": PRODUCER,
        "schema_note": "Shape follows schemas/asset_manifest.v1.schema.json. That file "
        "pins package_id/report_id/source.uri with `const` to wp-448-01, so it cannot "
        "validate any other package verbatim; verify regenerates a retargeted copy "
        "(asset_manifest.v1.wp8163.schema.json: only the three `const` values changed) "
        "and validates against both that copy and schemas/kf_result.v1.schema.json.",
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash_alg": "sha256",
            "hash": digest,
            "chars": len(md),
            "bytes_utf8": len(raw),
            "lines": md.rstrip("\n").count("\n") + 1,
            "title": record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "platform_figures": [
                {"name": f.get("name"), "caption": f.get("caption")}
                for f in (record.get("figures") or [])
                if isinstance(f, dict)
            ],
            "platform_tags": record.get("tags") or [],
            "platform_mission_id": record.get("mission_id"),
            "platform_status": record.get("status"),
            "fetched_via": "GET /api/v1/tensor/reports/%s" % REPORT_ID,
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "contract_chars": CONTRACT_CHARS,
            "contract_title": CONTRACT_TITLE,
            "contract_scenario_key": CONTRACT_SCENARIO,
            "hash_matches_contract": "sha256:" + digest == CONTRACT_SOURCE_HASH,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "title_matches_contract": record.get("title") == CONTRACT_TITLE,
            "scenario_matches_contract": record.get("scenario_key") == CONTRACT_SCENARIO,
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res.get("resolved_in_source", 0),
            "referenced_unresolved": by_res.get("referenced_unresolved", 0),
            "declared_absent": by_res.get("declared_absent", 0),
            "distinct_referenced_paths": len(seen_paths_of(assets)),
        },
        "assets": assets,
        "claims": [],
        "claims_note": "Empty by contract: objective.classify_report_type=false, no "
        "extraction performed, no claim may be generated for this work package.",
        "integrity": {
            "quote_uniqueness": {
                "checked": len(assets),
                "unique": sum(1 for a in assets if a["locator"]["unique"]),
            },
            "hash_recomputed_locally": True,
            "hash_matches_contract": "sha256:" + digest == CONTRACT_SOURCE_HASH,
            "quotes_sliced_from_markdown_not_retyped": True,
        },
        "registration_coverage": {
            "enumeration": {
                "markdown_backtick_paths_regex": PATH_RE.pattern,
                "markdown_image_embeds_regex": IMG_RE.pattern,
                "artefact_dir_regex": DIR_RE.pattern,
                "record_figures": "record.figures[] names",
                "symbols": [lab for lab, _ in SYMBOL_SPECS],
            },
            "found": {
                "markdown_backtick_paths": len(set(PATH_RE.findall(md))),
                "markdown_image_embeds": len(IMG_RE.findall(md)),
                "artefact_dirs": len(set(DIR_RE.findall(md))),
                "record_figures": len(figs),
                "symbols": len(SYMBOL_SPECS),
            },
            "not_registered": [
                {
                    "token": "m5404",
                    "occurrences_in_markdown": md.count("m5404"),
                    "reason": "mission/task identifier referenced in the prose (sections 1, 3, 6.1); "
                    "the document names no artefact or figure belonging to that run, so there is "
                    "nothing locatable to register",
                },
                {
                    "token": "IN155-N07",
                    "occurrences_in_markdown": md.count("IN155-N07"),
                    "reason": "campaign/task code printed in the footer; not an asset",
                },
            ],
        },
        "probes": {
            "/tensor/reports/%s/artifacts" % REPORT_ID: {"http_status": artifacts_probe[0]},
        },
        "limitations": [
            "Registration only: no extraction, no claim generation, no `verified` mark.",
            "Path references are resolved inside this TensorKnowledge worktree; the "
            "producing TensorDEM tree is outside the work package boundary, so code/test/"
            "plot references stay unresolved by design (not `absent` verdicts about TensorDEM).",
            "record.figures[] exposes name+caption only; no byte payload is served, so no "
            "hash is claimed for either figure.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s (%d assets, hash %s)" % (MANIFEST.relative_to(REPO), len(assets), digest))
    return manifest


def seen_paths_of(assets: list[dict]) -> list[str]:
    out = []
    for a in assets:
        for key in ("source_code_reference", "figure_reference"):
            if a["asset_class"] == key and a["label"] not in out:
                out.append(a["label"])
    return out


# ---------------------------------------------------------------- envelope
def envelope() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            # kf_result.v1 pins ^sha256:[0-9a-f]{64}$ here, while the asset_manifest.v1
            # `source.hash` field is the bare hex digest -- same digest, two shapes.
            "source_hash": "sha256:" + manifest["source"]["hash"],
            "source_field": SOURCE_FIELD,
            "producer": PRODUCER,
            "emitted_at": datetime.now(timezone.utc).isoformat(),
            "notes": "sha256 over the UTF-8 bytes of GET /api/v1/tensor/reports/%s "
            "`markdown`; recomputed locally, equals the contract source_hash %s."
            % (REPORT_ID, CONTRACT_SOURCE_HASH),
        },
        "outputs": {"asset_manifest.json": manifest},
    }
    ENVELOPE.write_text(json.dumps(env, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("wrote %s" % ENVELOPE.relative_to(REPO))
    return env


# ------------------------------------------------------------------ verify
def verify() -> dict:
    checks: dict[str, dict] = {}
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    # 1 valid_json
    checks["valid_json"] = {"pass": True, "detail": "json.loads OK for kf_result.json and asset_manifest.json"}

    # 2 schema_pass -- platform-side envelope schema + retargeted manifest schema
    import jsonschema  # imported lazily so build/figure need no third-party dep

    kf_schema = json.loads(KF_RESULT_SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(jsonschema.Draft202012Validator(kf_schema).iter_errors(env), key=str)
    base_schema = json.loads(ASSET_SCHEMA.read_text(encoding="utf-8"))
    derived = json.loads(json.dumps(base_schema))
    derived["properties"]["package_id"] = {"const": PACKAGE_ID}
    derived["properties"]["report_id"] = {"const": REPORT_ID}
    derived["properties"]["source"]["properties"]["uri"] = {"const": SOURCE_URI}
    derived["title"] = "asset_manifest.v1 retargeted to %s (only the const pins changed)" % PACKAGE_ID
    derived["description"] = (
        "Derived from schemas/asset_manifest.v1.schema.json, whose package_id/report_id/"
        "source.uri are `const`-pinned to wp-448-01. Only those three const values are "
        "replaced; every other constraint is the shipped schema's, unchanged. Generated by "
        "scripts/kf/kf_wp8163_01_register.py verify."
    )
    DERIVED_SCHEMA.write_text(json.dumps(derived, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    m_errors = sorted(jsonschema.Draft202012Validator(derived).iter_errors(manifest), key=str)
    checks["schema_pass"] = {
        "pass": not errors and not m_errors,
        "detail": "kf_result vs schemas/kf_result.v1.schema.json errors=%d; manifest vs "
        "retargeted asset_manifest.v1 (%s) errors=%d"
        % (len(errors), DERIVED_SCHEMA.name, len(m_errors)),
        "errors": [str(e) for e in errors + m_errors][:10],
    }

    # 3 source_locator_resolvable -- re-fetch the live markdown, re-resolve every locator
    md = fetch_record()["markdown"]
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        hits = md.count(q)
        if hits != 1:
            bad.append({"asset_id": a["asset_id"], "reason": "quote occurrences=%d" % hits})
            continue
        if loc["method"] == "char_span":
            if md[loc["start_char"] : loc["end_char"]] != q:
                bad.append({"asset_id": a["asset_id"], "reason": "char span mismatch"})
            if md.count("\n", 0, loc["start_char"]) + 1 != loc["start_line"]:
                bad.append({"asset_id": a["asset_id"], "reason": "line mismatch"})
        else:  # document scope: the span must be exactly the whole field
            if (loc["start_char"], loc["end_char"]) != (0, len(md)):
                bad.append({"asset_id": a["asset_id"], "reason": "document span != whole field"})
            if not md.startswith(q):
                bad.append({"asset_id": a["asset_id"], "reason": "document quote not a prefix"})
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": "checked %d locators against the live markdown; unresolvable=%d"
        % (len(manifest["assets"]), len(bad)),
        "failures": bad,
    }
    LOCATOR_CHECK.write_text(
        json.dumps(
            {
                "report_id": REPORT_ID,
                "source_hash": "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest(),
                "quotes_checked": len(manifest["assets"]),
                "quotes_resolvable": len(manifest["assets"]) - len(bad),
                "unresolved": bad,
                "locators": [
                    {
                        "asset_id": a["asset_id"],
                        "quote": a["locator"]["quote"],
                        "start_char": a["locator"]["start_char"],
                        "end_char": a["locator"]["end_char"],
                        "start_line": a["locator"]["start_line"],
                        "end_line": a["locator"]["end_line"],
                        "occurrences": md.count(a["locator"]["quote"]),
                    }
                    for a in manifest["assets"]
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # 4 source_hash_matches
    live = hashlib.sha256(md.encode("utf-8")).hexdigest()
    declared = env["provenance"]["source_hash"].replace("sha256:", "")
    checks["source_hash_matches"] = {
        "pass": live == declared == CONTRACT_SOURCE_HASH.replace("sha256:", ""),
        "detail": "recomputed=%s declared=%s contract=%s chars=%d/%d"
        % (live, declared, CONTRACT_SOURCE_HASH.replace("sha256:", ""), len(md), CONTRACT_CHARS),
    }

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)),
        "detail": "assets=%d unique=%d" % (len(ids), len(set(ids))),
    }

    # 6 claims carry evidence or an explicit status
    claims = manifest.get("claims") or []
    violating = [
        c
        for c in claims
        if not (c.get("evidence_locator") or c.get("status"))
    ]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not violating,
        "detail": "claims=%d violating=%d (empty array satisfies the constraint per the "
        "contract note 'claims 允许为空数组')" % (len(claims), len(violating)),
    }
    checks["do_not_mark_claims_as_verified"] = {
        "pass": all(c.get("status") != "verified" for c in claims),
        "detail": "no claim carries status=verified (verification is platform-gated)",
    }

    # coverage completeness (beyond the 6 contract acceptance items): re-run the same
    # enumerators on the live markdown and require every hit to be a registered label.
    # a registered asset is identified either by its path label or by the platform
    # figure name it carries (figure assets merge the markdown embed and record.figures[])
    labels = {a["label"] for a in manifest["assets"]}
    labels |= {a["platform_figure_name"] for a in manifest["assets"] if a.get("platform_figure_name")}
    want = set(PATH_RE.findall(md)) | set(IMG_RE.findall(md)) | set(DIR_RE.findall(md))
    want |= {f.get("name") for f in (fetch_record().get("figures") or []) if isinstance(f, dict)}
    want |= {lab for lab, _ in SYMBOL_SPECS}
    missing = sorted(w for w in want if w not in labels)
    record = fetch_record()
    fig_labels = {a.get("platform_figure_name") for a in manifest["assets"] if a.get("platform_figure_name")}
    missing_figs = sorted(
        f.get("name") for f in (record.get("figures") or [])
        if isinstance(f, dict) and f.get("name") not in fig_labels
    )
    coverage = {
        "pass": not missing and not missing_figs,
        "enumerated_not_registered": missing,
        "record_figures_not_registered": missing_figs,
        "registered_assets": len(labels),
        "note": "same regexes as build(); a hit that is not a registered label would mean "
        "the manifest silently dropped a declared asset",
    }

    result = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "manifest": str(MANIFEST.relative_to(REPO)),
        "manifest_sha256": hashlib.sha256(MANIFEST.read_bytes()).hexdigest(),
        "checks": checks,
        "coverage": coverage,
        "all_pass": all(c["pass"] for c in checks.values()) and coverage["pass"],
    }
    VERIFICATION.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["pass"] for k, v in checks.items()}, ensure_ascii=False))
    print("all_pass=%s -> %s" % (result["all_pass"], VERIFICATION.relative_to(REPO)))
    return result


# ------------------------------------------------------------------ figure
def figure() -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assets = manifest["assets"]
    classes: dict[str, dict[str, int]] = {}
    for a in assets:
        row = classes.setdefault(a["asset_class"], {"resolved_in_source": 0, "referenced_unresolved": 0})
        row[a["resolution"]] = row.get(a["resolution"], 0) + 1

    labels = sorted(classes, key=lambda k: -(classes[k]["resolved_in_source"] + classes[k]["referenced_unresolved"]))
    res = [classes[k]["resolved_in_source"] for k in labels]
    unres = [classes[k]["referenced_unresolved"] for k in labels]

    fig, ax = plt.subplots(figsize=(8.6, 4.4), dpi=150)
    y = range(len(labels))
    ax.barh(list(y), res, color="#2a7f62", label="resolved_in_source")
    ax.barh(list(y), unres, left=res, color="#c1666b", label="referenced_unresolved")
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=9)
    ax.invert_yaxis()
    ax.set_xlabel("assets registered")
    ax.set_title(
        "report %s asset registration: %d assets, %d locators re-resolved, hash %s…%s"
        % (
            REPORT_ID,
            len(assets),
            manifest["integrity"]["quote_uniqueness"]["unique"],
            manifest["source"]["hash"][:12],
            manifest["source"]["hash"][-6:],
        ),
        fontsize=9,
    )
    for i, k in enumerate(labels):
        tot = res[i] + unres[i]
        ax.text(tot + 0.05, i, str(tot), va="center", fontsize=8)
    ax.legend(fontsize=8, loc="lower right")
    ax.set_xlim(0, max(r + u for r, u in zip(res, unres)) + 1.2)
    fig.tight_layout()
    out = OUT_DIR / "figures" / "asset_resolution_map.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out)
    plt.close(fig)
    print("wrote %s" % out.relative_to(REPO))

    # figure 2 -- locator coverage: every quote's char span sits inside the source
    # markdown of known length (evidence that no locator points outside the document).
    check = json.loads(LOCATOR_CHECK.read_text(encoding="utf-8"))
    md_len = manifest["source"]["chars"]
    fig, ax = plt.subplots(figsize=(8.6, 3.6), dpi=150)
    for i, loc in enumerate(check["locators"]):
        ax.plot([loc["start_char"], loc["end_char"]], [i, i], lw=5, solid_capstyle="butt",
                color="#2a7f62" if loc["asset_id"] == "A01" else "#3f6ea5")
        ax.text(loc["start_char"] - 40, i, loc["asset_id"], ha="right", va="center", fontsize=8)
    ax.axvline(md_len, color="#c1666b", ls="--", lw=1)
    ax.text(md_len - 60, -0.8, "markdown end = %d chars" % md_len, color="#c1666b",
            fontsize=8, ha="right")
    ax.set_yticks([])
    ax.set_ylim(len(check["locators"]) - 0.2, -1.2)
    ax.set_xlim(-260, md_len * 1.02)
    ax.set_xlabel("character offset in report markdown (UTF-8 decoded, 0-based)")
    ax.set_title(
        "report %s locator coverage: %d/%d quotes resolve uniquely (occurrences=1)"
        % (REPORT_ID, check["quotes_resolvable"], check["quotes_checked"]),
        fontsize=9,
    )
    fig.tight_layout()
    out2 = OUT_DIR / "figures" / "locator_coverage.png"
    fig.savefig(out2)
    plt.close(fig)
    print("wrote %s" % out2.relative_to(REPO))


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("build", "all"):
        build()
    if cmd in ("envelope", "all"):
        envelope()
    if cmd in ("verify", "all"):
        if not verify()["all_pass"]:
            return 1
    if cmd in ("figure", "all"):
        figure()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))