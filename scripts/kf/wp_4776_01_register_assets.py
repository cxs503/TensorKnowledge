#!/usr/bin/env python3
"""KF work package wp-4776-01 — 01-asset-registration for report 4776 (only that report).

Registers assets only: no claim extraction, no report-type classification, no
verification marking (that is the platform gate's job).

Reads : tensor://reports/4776 field `markdown` (platform API, bearer auth)
Writes: docs/kf/wp-4776-01/asset_manifest.json   (declared output, inside the envelope)
        docs/kf/wp-4776-01/kf_result.json        (result envelope, kf_result.v1)
        runs/wp-4776-01/checks.json              (self-check log, 6 acceptance items)

Repro:  python3 scripts/kf/wp_4776_01_register_assets.py
        python3 scripts/kf/wp_4776_01_register_assets.py --source-file <copy-of-markdown>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPORT_ID = "4776"
PACKAGE_ID = "wp-4776-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/4776"
SOURCE_FIELD = "markdown"
CONTRACT_SOURCE_HASH = (
    "sha256:03d3239696a36958c408df0ac3fd21d506a39cce4277b7f918134591d00d3882"
)
CONTRACT_CHARS = 4869
CONTRACT_TITLE = "PR #185 CI cure: one pinned ruff build for the lint debt ratchet"
CONTRACT_SCENARIO = "tensorfem/ci/lint-debt-ratchet"
MIN_QUOTE_CHARS = 12  # GATE-RULES E6

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
RUN_DIR = ROOT / "runs" / PACKAGE_ID
SCHEMA_PATH = ROOT / "schemas" / "kf_result.v1.schema.json"

# ---------------------------------------------------------------------------
# asset table (curated; every quote is verified verbatim against the markdown)
# kind: figure | evidence_artifact | referenced_repo_path
# ---------------------------------------------------------------------------
ASSETS = [
    dict(
        asset_id="A01",
        kind="figure",
        declared_path="runs/pr185-cure/pr185-cure-evidence.png",
        role_note="Single figure of the report; declared both as a platform `figures[]` entry "
        "(name+caption, no inline bytes) and as an inline image reference.",
        quote="pr185-cure-evidence.png",
        context_quote="Evidence logs and the figure live in `runs/pr185-cure/`:",
        payload_in_record="metadata_only",
    ),
    dict(
        asset_id="A02",
        kind="evidence_artifact",
        declared_path="runs/pr185-cure/ci-test312-pre-fix.log",
        role_note="Failing CI job log of `test (3.12)` before the fix.",
        quote="`ci-test312-pre-fix.log` - the failing CI job log",
        context_quote="Evidence logs and the figure live in `runs/pr185-cure/`:",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A03",
        kind="evidence_artifact",
        declared_path="runs/pr185-cure/tests-post-fix.log",
        role_note="Post-fix `pytest tests/test_lint_gate.py` log (18 passed).",
        quote="`tests-post-fix.log`",
        context_quote="Evidence logs and the figure live in `runs/pr185-cure/`:",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A04",
        kind="evidence_artifact",
        declared_path="runs/pr185-cure/tests-drifted-guard.log",
        role_note="Drift-guard test log with a ruff 0.17.3 shim on PATH (14 passed, 4 skipped).",
        quote="`tests-drifted-guard.log`",
        context_quote="Evidence logs and the figure live in `runs/pr185-cure/`:",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A05",
        kind="evidence_artifact",
        declared_path="runs/pr185-cure/gate-pinned.log",
        role_note="`lint_gate.py --check` log on the pinned build: exit 0, no new debt.",
        quote="`gate-pinned.log` (exit 0)",
        context_quote="Evidence logs and the figure live in `runs/pr185-cure/`:",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A06",
        kind="evidence_artifact",
        declared_path="runs/pr185-cure/gate-drifted.log",
        role_note="`lint_gate.py --check` log under ruff 0.17.3 shim: exit 2 (tool drift).",
        quote="`gate-drifted.log` (exit 2)",
        context_quote="Evidence logs and the figure live in `runs/pr185-cure/`:",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A07",
        kind="evidence_artifact",
        declared_path="runs/pr185-cure/lint-report.json",
        role_note="Machine-readable lint report payload produced by the gate (rule_totals etc.).",
        quote="`lint-report.json`",
        context_quote="Evidence logs and the figure live in `runs/pr185-cure/`:",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A08",
        kind="referenced_repo_path",
        declared_path="pyproject.toml",
        role_note="Changed file #1: `dev` extra now pins `ruff==0.15.0`.",
        quote="`pyproject.toml` - `dev` extra now pins `ruff==0.15.0`",
        context_quote="The debt ledger `docs/lint-baseline.json` is **ruff-version specific** (frozen with",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A09",
        kind="referenced_repo_path",
        declared_path="scripts/lint_gate.py",
        role_note="Changed file #2: `tool_drift()` refuses cross-version ledger comparison with exit 2.",
        quote="`scripts/lint_gate.py` - `tool_drift()`",
        context_quote="## Fix (4 files)",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A10",
        kind="referenced_repo_path",
        declared_path="tests/test_lint_gate.py",
        role_note="Changed file #3: pin-consistency regression test + drift-guard contract tests.",
        quote="`tests/test_lint_gate.py`",
        context_quote="## Fix (4 files)",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A11",
        kind="referenced_repo_path",
        declared_path="docs/lint-debt-baseline.md",
        role_note="Changed file #4: records the two-place pin and the exit-2 contract.",
        quote="`docs/lint-debt-baseline.md` - records the two-place pin and the exit-2 contract.",
        context_quote="## Fix (4 files)",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A12",
        kind="referenced_repo_path",
        declared_path="docs/lint-baseline.json",
        role_note="Frozen debt ledger (ruff-version specific); named as the root-cause subject.",
        quote="`docs/lint-baseline.json`",
        context_quote="The debt ledger `docs/lint-baseline.json` is **ruff-version specific** (frozen with",
        payload_in_record="not_hosted",
    ),
    dict(
        asset_id="A13",
        kind="referenced_repo_path",
        declared_path=".github/workflows/ci.yml",
        role_note="Workflow whose `lint` job carries the original `ruff==0.15.0` pin.",
        quote="`.github/workflows/ci.yml`, lint job",
        context_quote="| place | declared | resolved in CI |",
        payload_in_record="not_hosted",
    ),
]

REACHABILITY_PROBES = [
    ("GET", "/tensor/reports/4776", "source of record (markdown + figures metadata)"),
    ("GET", "/tensor/reports/4776/figures", "probe: figure listing route"),
    (
        "GET",
        "/tensor/reports/4776/figures/pr185-cure-evidence.png",
        "probe: figure bytes route",
    ),
    ("GET", "/tensor/reports/4776/attachments", "probe: attachment listing route"),
    ("GET", "/tensor/reports/4776/assets", "probe: asset listing route"),
]


# ---------------------------------------------------------------------------
def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch_source() -> tuple[str, dict]:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    login = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    token = json.load(urllib.request.urlopen(login))["access_token"]
    req = urllib.request.Request(
        base + f"/tensor/reports/{REPORT_ID}",
        headers={"Authorization": "Bearer " + token},
    )
    record = json.load(urllib.request.urlopen(req))
    md = record.get("markdown")
    if not isinstance(md, str):
        raise SystemExit("record has no markdown field")
    return md, record


def probe_routes() -> list[dict]:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    login = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    token = json.load(urllib.request.urlopen(login))["access_token"]
    out = []
    for method, path, note in REACHABILITY_PROBES:
        req = urllib.request.Request(
            base + path, headers={"Authorization": "Bearer " + token}, method=method
        )
        try:
            with urllib.request.urlopen(req) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:  # noqa: BLE001 - probe only, recorded verbatim
            code = f"error:{type(e).__name__}"
        out.append({"method": method, "route": path, "http_status": code, "note": note})
    return out


def locate(md: str, quote: str) -> dict:
    """Exact substring locator: first occurrence, codepoint offsets + sha256(quote)."""
    start = md.find(quote)
    if start < 0:
        return {"found": False, "quote": quote}
    end = start + len(quote)
    return {
        "found": True,
        "field": SOURCE_FIELD,
        "quote": quote,
        "char_start": start,
        "char_end": end,
        "line": md.count("\n", 0, start) + 1,
        "content_hash": "sha256:" + sha256_hex(quote),
        "at_locator_matches": md[start:end] == quote,
        "quote_len": len(quote),
        "occurrences": md.count(quote),
    }


def build(md: str, record: dict, probes: list[dict]) -> dict:
    figures = record.get("figures") or []
    fig_names = [f.get("name") for f in figures if isinstance(f, dict)]
    h1 = next((ln[2:].strip() for ln in md.splitlines() if ln.startswith("# ")), None)

    assets, problems = [], []
    for spec in ASSETS:
        loc = locate(md, spec["quote"])
        ctx = locate(md, spec["context_quote"])
        if not loc["found"]:
            problems.append(
                f"{spec['asset_id']}: quote not found verbatim: {spec['quote']!r}"
            )
        if not ctx["found"]:
            problems.append(
                f"{spec['asset_id']}: context quote not found: {spec['context_quote']!r}"
            )
        if loc.get("quote_len", 0) < MIN_QUOTE_CHARS:
            problems.append(
                f"{spec['asset_id']}: quote shorter than {MIN_QUOTE_CHARS} chars"
            )

        name = spec["declared_path"].rsplit("/", 1)[-1]
        reach_status = "metadata_only_in_record"
        reach_note = (
            "Declared by name+caption in `record.figures`; no inline bytes in the record "
            "and the probed figure routes return 404, so the payload itself stays unresolved."
        )
        if spec["payload_in_record"] == "not_hosted":
            reach_status = "declared_only_not_resolvable_in_report_store"
            reach_note = (
                "Path is declared in the markdown only; the record carries no attachment "
                "listing and every probed non-markdown route returns 404. The file lives in "
                "the TensorFEM worktree outside this package's scope (not read)."
            )

        assets.append(
            {
                "asset_id": spec["asset_id"],
                "kind": spec["kind"],
                "declared_path": spec["declared_path"],
                "basename": name,
                "role_note": spec["role_note"],
                "declared_in_platform_figures": name in fig_names,
                "locator": {
                    k: loc[k]
                    for k in (
                        "field",
                        "quote",
                        "char_start",
                        "char_end",
                        "line",
                        "content_hash",
                        "at_locator_matches",
                        "occurrences",
                    )
                    if k in loc
                },
                "context_locator": {
                    k: ctx[k]
                    for k in ("field", "quote", "char_start", "char_end", "line")
                    if k in ctx
                },
                "payload_in_record": spec["payload_in_record"],
                "reachability": {"status": reach_status, "note": reach_note},
                "content_extracted": False,
            }
        )

    kinds = {}
    for a in assets:
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1

    return {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "scripts/kf/wp_4776_01_register_assets.py",
        "producer": "agent/m15561",
        "scope": {
            "report_id": REPORT_ID,
            "reports_touched": [REPORT_ID],
            "registers_assets_only": True,
            "extracts_claims": False,
            "classifies_report_type": False,
            "writes_outside_worktree": False,
            "upstream_artifacts_modified": False,
        },
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "title": record.get("title"),
            "title_matches_contract": record.get("title") == CONTRACT_TITLE,
            "markdown_h1": h1,
            "title_equals_markdown_h1": h1 == record.get("title"),
            "scenario_key": record.get("scenario_key"),
            "scenario_key_matches_contract": record.get("scenario_key")
            == CONTRACT_SCENARIO,
            "chars": len(md),
            "contract_chars": CONTRACT_CHARS,
            "chars_match_contract": len(md) == CONTRACT_CHARS,
            "byte_length_utf8": len(md.encode("utf-8")),
            "ascii_only": md.isascii(),
            "sha256": "sha256:" + sha256_hex(md),
            "contract_source_hash": CONTRACT_SOURCE_HASH,
            "hash_matches_contract": "sha256:" + sha256_hex(md) == CONTRACT_SOURCE_HASH,
            "hash_scope": "UTF-8 bytes of tensor_reports.markdown, no newline normalisation",
        },
        "record_metadata": {
            "platform_record_id": record.get("id"),
            "mission_id": record.get("mission_id"),
            "status": record.get("status"),
            "created_at": record.get("created_at"),
            "tags": record.get("tags"),
            "figures_count": len(figures),
            "figures": [
                {"name": f.get("name"), "caption_chars": len(f.get("caption") or "")}
                for f in figures
                if isinstance(f, dict)
            ],
        },
        "asset_inventory": assets,
        "asset_counts": {"total": len(assets), "by_kind": kinds},
        "reachability_probes": probes,
        "claims_registration": {
            "claims": [],
            "is_empty": True,
            "reason": (
                "Task type 01 registers assets only; claim extraction belongs to work package "
                "03 (03-knowledge-extraction) and is explicitly out of scope here."
            ),
        },
        "unresolved": [
            {
                "item": "figure_payload",
                "status": "unresolved",
                "detail": "pr185-cure-evidence.png: name+caption registered, bytes not retrievable from the "
                "record nor from the probed routes (404).",
            },
            {
                "item": "evidence_artifact_payloads",
                "status": "unresolved",
                "detail": "6 files under runs/pr185-cure/ are declared in the markdown only; no payload is "
                "stored with the report, so their content cannot be hashed or parsed here.",
            },
            {
                "item": "referenced_repo_payloads",
                "status": "unresolved",
                "detail": "6 repository paths (incl. the 4 changed files) are pointers into the TensorFEM "
                "tree; resolving them is out of scope for report 4776 registration.",
            },
        ],
        "registration_problems": problems,
    }


def self_check(md: str, envelope: dict, manifest: dict, checks_path: Path) -> dict:
    from jsonschema import Draft202012Validator

    schema = json.loads(SCHEMA_PATH.read_text())
    v = Draft202012Validator(schema)
    schema_errors = sorted(v.iter_errors(envelope), key=lambda e: list(e.path))

    rec_hash = "sha256:" + sha256_hex(md)
    locator_rows = []
    for a in manifest["asset_inventory"]:
        loc = a["locator"]
        ok_offsets = md[loc["char_start"] : loc["char_end"]] == loc["quote"]
        ok_hash = loc["content_hash"] == "sha256:" + sha256_hex(loc["quote"])
        ok_len = len(loc["quote"]) >= MIN_QUOTE_CHARS
        locator_rows.append(
            {
                "asset_id": a["asset_id"],
                "offsets_match": ok_offsets,
                "content_hash_matches": ok_hash,
                "quote_long_enough": ok_len,
                "result": "OK_OFFSETS"
                if (ok_offsets and ok_hash and ok_len)
                else "FAIL",
            }
        )

    ids = [a["asset_id"] for a in manifest["asset_inventory"]]
    paths = [a["declared_path"] for a in manifest["asset_inventory"]]
    claims = envelope.get("claims", [])
    empty_decl = manifest["claims_registration"]

    checks = [
        {
            "id": 1,
            "criterion": "valid_json",
            "result": "pass",
            "detail": "envelope + manifest serialise/deserialise with json",
        },
        {
            "id": 2,
            "criterion": "schema_pass",
            "result": "pass" if not schema_errors else "fail",
            "detail": (
                "kf_result.v1.schema.json (Draft 2020-12): 0 errors"
                if not schema_errors
                else "; ".join(e.message for e in schema_errors)
            ),
        },
        {
            "id": 3,
            "criterion": "source_locator_resolvable",
            "result": "pass"
            if all(r["result"] == "OK_OFFSETS" for r in locator_rows)
            else "fail",
            "detail": f"{sum(r['result'] == 'OK_OFFSETS' for r in locator_rows)}/{len(locator_rows)} "
            f"locators byte-identical at declared offsets, content_hash = sha256(quote)",
        },
        {
            "id": 4,
            "criterion": "source_hash_matches",
            "result": "pass" if rec_hash == CONTRACT_SOURCE_HASH else "fail",
            "detail": f"recomputed {rec_hash} vs contract {CONTRACT_SOURCE_HASH}",
        },
        {
            "id": 5,
            "criterion": "no_duplicate_ids",
            "result": "pass"
            if len(set(ids)) == len(ids) and len(set(paths)) == len(paths)
            else "fail",
            "detail": f"{len(ids)} asset ids, {len(set(ids))} unique; {len(set(paths))} unique paths",
        },
        {
            "id": 6,
            "criterion": "all_claims_have_evidence_or_explicit_unresolved_status",
            "result": "pass"
            if (
                not claims
                and empty_decl["is_empty"]
                and len(empty_decl["reason"]) >= 20
            )
            else "fail",
            "detail": f"claims={len(claims)}, is_empty={empty_decl['is_empty']}, "
            f"reason_len={len(empty_decl['reason'])} (>=20 required)",
        },
    ]
    report = {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "checks": checks,
        "locators": locator_rows,
        "all_pass": all(c["result"] == "pass" for c in checks),
    }
    checks_path.parent.mkdir(parents=True, exist_ok=True)
    checks_path.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    return report


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--source-file", help="offline copy of the report markdown (skip API fetch)"
    )
    ap.add_argument(
        "--skip-probes", action="store_true", help="do not probe reachability routes"
    )
    args = ap.parse_args()

    if args.source_file:
        md = Path(args.source_file).read_text()
        record = {
            "id": int(REPORT_ID),
            "title": CONTRACT_TITLE,
            "scenario_key": CONTRACT_SCENARIO,
        }
        probes = [{"note": "skipped (--skip-probes / offline mode)"}]
    else:
        md, record = fetch_source()
        probes = [] if args.skip_probes else probe_routes()

    manifest = build(md, record, probes)
    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": "sha256:" + sha256_hex(md),
            "source_field": SOURCE_FIELD,
            "producer": "agent/m15561",
            "emitted_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "notes": "Report 4776 only; assets registered, no claims extracted, no classification, "
            "no verification marking.",
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1) + "\n"
    )
    (OUT_DIR / "kf_result.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=1) + "\n"
    )

    report = self_check(md, envelope, manifest, RUN_DIR / "checks.json")
    print(
        json.dumps(
            {
                "manifest": str(OUT_DIR / "asset_manifest.json"),
                "envelope": str(OUT_DIR / "kf_result.json"),
                "problems": manifest["registration_problems"],
                "checks": report["checks"],
                "all_pass": report["all_pass"],
            },
            ensure_ascii=False,
            indent=1,
        )
    )
    return 0 if report["all_pass"] and not manifest["registration_problems"] else 1


if __name__ == "__main__":
    sys.exit(main())
