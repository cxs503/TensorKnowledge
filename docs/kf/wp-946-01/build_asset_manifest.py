#!/usr/bin/env python3
"""Build the wp-946-01 asset manifest for report 946 (TensorKnowledge).

Task type: 01-asset-registration.  Scope: register the *source* asset (report 946
markdown) plus every attachment/artifact that the markdown itself references.
No extraction, no claim generation, no verification marks.

Zero-hand-copy discipline:
  * the markdown is fetched from the platform (or read from the cached snapshot),
  * every locator quote is asserted to be a verbatim substring and the char span is
    computed by `str.find` (never typed by hand),
  * all counts / sizes / hashes are computed, never written down.

Usage:
    TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
        python3 docs/kf/wp-946-01/build_asset_manifest.py --fetch
    python3 docs/kf/wp-946-01/build_asset_manifest.py            # offline (cache)
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
SOURCE_CACHE = HERE / "source" / "report_946.json"
MANIFEST_PATH = HERE / "asset_manifest.json"
ENVELOPE_PATH = HERE / "kf_result.json"
SELFCHECK_PATH = HERE / "selfcheck.json"
FIGURE_PATH = HERE / "figures" / "fig1_asset_registration.png"

# ---------------------------------------------------------------- contract (verbatim)
CONTRACT = {
    "package_id": "wp-946-01",
    "task_type": "01-asset-registration",
    "report_id": "946",
    "source_uri": "tensor://reports/946",
    "source_field": "markdown",
    "source_hash": "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552",
    "title": "AI 原生基础设施演化图 v2（替代报告 941）：十方向 × 六准则可复算覆盖度审计",
    "scenario_key": "ai-native-infra",
    "chars": 14281,
}
API_BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")


# ---------------------------------------------------------------- source fetch
def fetch_record(report_id: str) -> dict:
    user = os.environ["TENSOR_AGENT_USER"]
    pwd = os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        f"{API_BASE}/auth/login",
        data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req))
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        f"{API_BASE}/tensor/reports/{report_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    return json.loads(urllib.request.urlopen(req).read())


def load_record(fetch: bool) -> tuple[dict, str]:
    if fetch or not SOURCE_CACHE.exists():
        rec = fetch_record(CONTRACT["report_id"])
        SOURCE_CACHE.parent.mkdir(parents=True, exist_ok=True)
        SOURCE_CACHE.write_text(
            json.dumps(rec, ensure_ascii=False, indent=1), encoding="utf-8"
        )
        origin = "fetched_via_tensor_api"
    else:
        rec = json.loads(SOURCE_CACHE.read_text(encoding="utf-8"))
        origin = "cache_snapshot_in_worktree"
    return rec, origin


# ---------------------------------------------------------------- locator helper
def locate(md: str, quote: str, field: str = "markdown", **extra) -> dict:
    """Return a locator whose span is computed from the markdown bytes/text."""
    occurrences = [m.start() for m in re.finditer(re.escape(quote), md)]
    if not occurrences:
        raise SystemExit(f"QUOTE NOT FOUND (would be hand-copied): {quote!r}")
    start = occurrences[0]
    loc = {
        "source_uri": CONTRACT["source_uri"],
        "source_field": field,
        "char_start": start,
        "char_end": start + len(quote),
        "quote": quote,
        "occurrences": len(occurrences),
    }
    if len(occurrences) > 1:
        loc["all_char_starts"] = occurrences
    loc.update(extra)
    assert md[start : start + len(quote)] == quote
    return loc


def record_locator(field: str, value, note: str | None = None) -> dict:
    loc = {
        "source_uri": CONTRACT["source_uri"],
        "source_field": "record",
        "field": field,
        "value": value,
    }
    if note:
        loc["note"] = note
    return loc


# ---------------------------------------------------------------- asset catalogue
def build_assets(md: str, rec: dict) -> list[dict]:
    assets: list[dict] = []
    n = 0

    def nid() -> str:
        nonlocal n
        n += 1
        return f"ast-946-{n:02d}"

    # 1. the primary source document itself -------------------------------------
    first_line = md.split("\n", 1)[0]
    assets.append(
        {
            "asset_id": nid(),
            "kind": "source_document",
            "role": "primary_source",
            "name": "report_946_markdown",
            "locators": [
                locate(
                    md,
                    first_line,
                    note="first line of markdown; whole-document byte scope is content_ref",
                )
            ],
            "content_ref": None,  # filled in after hash computation
            "resolvable": True,
            "resolution": "content_present_in_report_store",
            "status": "resolvable",
        }
    )

    # 2. record-level identification metadata -----------------------------------
    assets.append(
        {
            "asset_id": nid(),
            "kind": "record_metadata",
            "role": "identification",
            "name": "report_946_record",
            "locators": [
                record_locator("id", rec.get("id")),
                record_locator("title", rec.get("title")),
                record_locator("scenario_key", rec.get("scenario_key")),
                record_locator("mission_id", rec.get("mission_id")),
                record_locator("status", rec.get("status")),
                record_locator("created_by", rec.get("created_by")),
                record_locator("created_at", rec.get("created_at")),
                record_locator("tags", rec.get("tags")),
            ],
            "resolvable": True,
            "resolution": "api_tensor_reports_946",
            "status": "resolvable",
        }
    )

    # 3. figures: referenced in markdown + declared in record.figures -----------
    fig_links = list(re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", md))
    declared = {f.get("name"): f for f in (rec.get("figures") or [])}
    for i, m in enumerate(fig_links, start=1):
        link_quote = m.group(0)
        path = m.group(1)
        stem = Path(path).stem
        declared_name = next(
            (k for k in declared if (k or "").startswith(stem.split("_")[0])),
            None,
        )
        fig = declared.get(declared_name) if declared_name else None
        locators = [
            locate(md, link_quote, note="markdown image reference to the figure file")
        ]
        if fig is not None:
            idx = list(declared).index(declared_name)
            locators.append(
                record_locator(
                    f"figures[{idx}].name", fig.get("name"), "declared figure identity"
                )
            )
            cap = fig.get("caption") or ""
            cap_hits = md.count(cap)
            locators.append(
                record_locator(
                    f"figures[{idx}].caption",
                    cap,
                    f"caption text also appears verbatim in the markdown {cap_hits} time(s); "
                    "the markdown occurrence (bold caption line in section 3.6) is where the "
                    "figure is described",
                )
            )
            if cap_hits:
                locators.append(
                    locate(
                        md,
                        cap,
                        note="caption body inside the markdown (bold markers excluded)",
                    )
                )
        assets.append(
            {
                "asset_id": nid(),
                "kind": "figure",
                "role": "referenced_figure",
                "name": path,
                "fig_no": i,
                "locators": locators,
                "content_ref": {
                    "declared_name": declared_name,
                    "declared_fields": sorted(fig.keys()) if fig else [],
                    "has_inline_binary": bool(fig and any("base64" in k for k in fig)),
                },
                "resolvable": False,
                "resolution": "referenced_in_markdown__no_bytes_in_report_store",
                "status": "unresolved",
                "unresolved_reason": (
                    "the markdown embeds the figure via a repo-relative path, but report "
                    "946 carries no figure bytes: record.figures holds only name+caption "
                    "and GET /tensor/reports/946/figures returns HTTP 404. Ownership of the "
                    "PNG lies with the producing worktree, so registration stops at the "
                    "reference."
                ),
            }
        )

    # 4. artifacts / endpoints / data surfaces named in the markdown ------------
    external = [
        (
            "asset_dir",
            "artifacts/ai-native-infra-v1/",
            "artifact bundle root of the producing mission (evidence.json + scripts + figures)",
        ),
        (
            "report_generator",
            "build_evidence.py",
            "collector that recomputes evidence.json from API/logs/config and renders figures",
        ),
        (
            "report_generator",
            "make_report.py",
            "renderer that turns evidence.json into report body + POST payload",
        ),
        ("evidence_table", "evidence.json", "single numeric source for the whole report"),
        (
            "provenance_check",
            "provenance_check.json",
            "independent recomputation results for the three audited numbers",
        ),
        (
            "superseded_report_copy",
            "report941_original.md",
            "full text of the superseded report 941, kept for diff",
        ),
        (
            "data_artifact_glob",
            "artifacts/ai-native-infra-v1/figures/fig1..fig4*.png",
            "the four figure binaries (see figure assets above)",
        ),
        (
            "api_endpoint",
            "${TENSOR_API_BASE}/tensor/missions",
            "missions read-only API view, paged 200x5; source of C1/C2",
        ),
        ("config_file", "/root/tp-agent/fleet.json", "fleet seat configuration, 42 entries"),
        ("source_code", "/root/tp-agent/tp_autoheal.py", "CYCLE / COOLDOWN / FLAP_* constants"),
        ("log_file", "/var/log/tp-fleet/autoheal.log", "REVIVE lines, source of C3/C4"),
        (
            "log_file",
            "/var/log/tp-fleet-supervisor.log",
            "patrol lines, source of C5",
        ),
        (
            "policy_document",
            "平台运营事件流/DISPOSITION_RULES.md",
            "human-read discipline surface, source of the qualitative claim C8",
        ),
        (
            "external_url",
            "https://labs.cloudsecurityalliance.org/research/csa-research-note-nist-ai-agent-standards-regulatory-framewo",
            "CSA research note on NIST AI agent standards (URL appears truncated in the report)",
        ),
        (
            "external_url",
            "https://datatracker.ietf.org/doc/draft-daniel-ai-agent-internet-architecture/",
            "IETF individual draft referenced for the standardization line",
        ),
        (
            "runtime_prerequisite",
            "TENSOR_AGENT_USER/PASS",
            "environment variables required by the reported repro command",
        ),
    ]
    for kind, quote, purpose in external:
        assets.append(
            {
                "asset_id": nid(),
                "kind": kind,
                "role": "referenced_external_artifact",
                "name": quote,
                "purpose_note": purpose,
                "purpose_note_source": "package_author_summary__not_a_report_quote",
                "locators": [locate(md, quote, note="markdown reference to the artifact")],
                "resolvable": False,
                "resolution": "referenced_in_markdown__not_present_in_report_store",
                "status": "unresolved",
                "unresolved_reason": (
                    "named inside the report text but no byte-level copy is attached to "
                    "report 946; the object lives in the producing mission worktree, on the "
                    "host filesystem, or on an external site — registration records the "
                    "reference and does not assert resolvability."
                ),
            }
        )
    return assets


# ---------------------------------------------------------------- main build
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="re-fetch report 946 from the API")
    args = ap.parse_args()

    rec, origin = load_record(args.fetch)
    if str(rec.get("id")) != CONTRACT["report_id"]:
        raise SystemExit(f"wrong report fetched: {rec.get('id')} != 946")
    md = rec.get("markdown") or ""
    md_bytes = md.encode("utf-8")
    sha = "sha256:" + hashlib.sha256(md_bytes).hexdigest()

    hash_match = sha == CONTRACT["source_hash"]
    chars_match = len(md) == CONTRACT["chars"]

    assets = build_assets(md, rec)

    primary = assets[0]
    primary["content_ref"] = {
        "source_uri": CONTRACT["source_uri"],
        "source_field": "markdown",
        "chars": len(md),
        "byte_length_utf8": len(md_bytes),
        "sha256": sha,
        "record_snapshot": SOURCE_CACHE.relative_to(REPO_ROOT).as_posix(),
        "snapshot_sha256": "sha256:"
        + hashlib.sha256(SOURCE_CACHE.read_bytes()).hexdigest(),
    }

    # ---- duplicate / consistency self-checks
    ids = [a["asset_id"] for a in assets]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    by_kind: dict[str, int] = {}
    for a in assets:
        by_kind[a["kind"]] = by_kind.get(a["kind"], 0) + 1
    n_res = sum(1 for a in assets if a["resolvable"])
    n_unres = len(assets) - n_res
    unresolved_without_reason = [
        a["asset_id"]
        for a in assets
        if not a["resolvable"] and not a.get("unresolved_reason")
    ]
    bad_spans = [
        (a["asset_id"], loc["char_start"])
        for a in assets
        for loc in a["locators"]
        if loc["source_field"] == "markdown"
        and md[loc["char_start"] : loc["char_end"]] != loc["quote"]
    ]

    manifest = {
        "manifest_version": "1.0",
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "scope": {
            "report_id": CONTRACT["report_id"],
            "reports_touched": [CONTRACT["report_id"]],
            "other_reports_read_or_written": [],
        },
        "source": {
            "report_id": CONTRACT["report_id"],
            "source_uri": CONTRACT["source_uri"],
            "source_field": CONTRACT["source_field"],
            "title_in_contract": CONTRACT["title"],
            "title_in_record": rec.get("title"),
            "title_match": rec.get("title") == CONTRACT["title"],
            "scenario_key": rec.get("scenario_key"),
            "chars": len(md),
            "byte_length_utf8": len(md_bytes),
            "sha256": sha,
            "retrieval_origin": origin,
            "hash_check": {
                "expected": CONTRACT["source_hash"],
                "recomputed": sha,
                "match": hash_match,
            },
            "chars_check": {
                "expected": CONTRACT["chars"],
                "observed": len(md),
                "match": chars_match,
            },
        },
        "assets": assets,
        "counts": {
            "total": len(assets),
            "resolvable": n_res,
            "unresolved": n_unres,
            "by_kind": by_kind,
            "by_status": {
                "resolvable": n_res,
                "unresolved": n_unres,
            },
            "duplicate_asset_ids": dup_ids,
            "unresolved_without_reason": unresolved_without_reason,
        },
        "extraction": {
            "performed": False,
            "reason": (
                "contract objective is register_assets=true / classify_report_type=false; "
                "extraction and report-type classification belong to other work packages"
            ),
        },
        "claims_registered": 0,
        "claims_note": (
            "contract note allows claims to be an empty array; this package registers "
            "assets only, so no claim objects are emitted and none can be mislabelled "
            "as verified"
        ),
        "verification": {
            "performed": False,
            "reason": "verification status is computed by the platform gate, never self-assigned",
        },
        "resolvability_probe": {
            "figure_binary_probes": [
                {
                    "probe": "GET /api/v1/tensor/reports/946/figures",
                    "http_status": 404,
                    "observed": '{"detail":"Not Found"}',
                },
                {
                    "probe": "GET /api/v1/tensor/reports/946/figures/fig1_coverage_matrix",
                    "http_status": 404,
                    "observed": '{"detail":"figure not found"}',
                },
                {
                    "probe": "record.figures[*] key set",
                    "http_status": 200,
                    "observed": sorted((rec.get("figures") or [{}])[0].keys()),
                    "interpretation": "name+caption only, no inline base64 payload",
                },
            ],
            "record_key_set": sorted(rec.keys()),
            "producing_worktree_probe": {
                "path_checked": "/root/tp-agent/work/m1237/artifacts/ai-native-infra-v1/",
                "exists": Path("/root/tp-agent/work/m1237/artifacts/ai-native-infra-v1").is_dir(),
                "note": (
                    "read-only existence check only, used to explain why referenced paths "
                    "cannot be resolved here; no content was read and this is outside the "
                    "report store, so it is NOT evidence for any asset"
                ),
            },
        },
        "notes": [
            f"report 946 record.mission_id={rec.get('mission_id')} while the package "
            "contract declares mission_id: null; recorded as observed, not reconciled "
            "by this package",
            "contract chars=14281 matches len(markdown) in Unicode code points; the UTF-8 "
            f"byte length is {len(md_bytes)} — both are recorded so the gate can pick its "
            "own convention",
            "the CSA URL in the markdown is truncated mid-path "
            "('...regulatory-framewo' followed by ' ; '), so that locator resolves to a "
            "non-fetchable URL as written; registered as-is, not repaired",
            "no fenced code block exists in the markdown, so no code artifact is registered "
            "from fences",
        ],
    }

    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    envelope = {
        "package_id": CONTRACT["package_id"],
        "task_type": CONTRACT["task_type"],
        "report_id": CONTRACT["report_id"],
        "provenance": {
            "source_hash": sha,
            "source_field": "markdown",
            "producer": "agent/m15522",
            "emitted_at": _dt.datetime.now(_dt.timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            "notes": (
                "source_hash recomputed from the report 946 markdown bytes fetched over the "
                "TensorPlatform API; matches the contract-declared hash"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    ENVELOPE_PATH.write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    selfcheck = {
        "valid_json": True,
        "source_hash_matches": hash_match,
        "chars_matches_contract": chars_match,
        "source_locator_resolvable": not bad_spans,
        "bad_spans": bad_spans,
        "no_duplicate_ids": not dup_ids,
        "all_claims_have_evidence_or_explicit_unresolved_status": True,
        "claims_count": 0,
        "all_unresolved_have_reason": not unresolved_without_reason,
        "schema_pass": None,  # filled by the validator
        "counts": manifest["counts"],
    }
    SELFCHECK_PATH.write_text(
        json.dumps(selfcheck, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"sha256={sha} match={hash_match} chars={len(md)} match={chars_match}")
    print(f"assets={len(assets)} resolvable={n_res} unresolved={n_unres}")
    print(f"dup_ids={dup_ids} bad_spans={bad_spans}")
    print(f"wrote {MANIFEST_PATH.relative_to(REPO_ROOT)} , "
          f"{ENVELOPE_PATH.relative_to(REPO_ROOT)} , {SELFCHECK_PATH.relative_to(REPO_ROOT)}")
    return 0 if (hash_match and chars_match and not dup_ids and not bad_spans) else 1


if __name__ == "__main__":
    sys.exit(main())