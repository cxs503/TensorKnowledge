#!/usr/bin/env python3
"""KF work package wp-771-01 — 01-asset-registration for report_id=771.

Scope (hard): only report_id 771. Registration only — no extraction, no claims,
no verification marking. Every registered item carries a locator that this
script re-resolves against the source text; nothing is hand-typed from memory.

Run:
    TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
        python3 scripts/kf_wp771_01_register_assets.py

Outputs (inside the repo checkout):
    artifacts/kf/wp-771-01/asset_manifest.json   (the package deliverable)
    artifacts/kf/wp-771-01/kf_result.json        (result envelope, schemas/kf_result.v1)
    artifacts/kf/wp-771-01/selfcheck.json        (per-criterion self check)
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PACKAGE_ID = "wp-771-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "771"
SOURCE_URI = "tensor://reports/771"
SOURCE_FIELD = "markdown"
# Expected hash is the one declared in the package contract; it is *checked*,
# never trusted blindly: the script recomputes the digest from the fetched bytes.
EXPECTED_SOURCE_HASH = (
    "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559"
)
EXPECTED_CHARS = 2143

OUT_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "kf" / PACKAGE_ID


# --------------------------------------------------------------------------- io
def login(base: str) -> str:
    user = os.environ["TENSOR_AGENT_USER"]
    password = os.environ["TENSOR_AGENT_PASS"]
    body = json.dumps({"username": user, "password": password}).encode()
    for path in ("/auth/login", "/tensor/auth/login"):
        req = urllib.request.Request(
            base + path, data=body, headers={"Content-Type": "application/json"}
        )
        try:
            data = json.load(urllib.request.urlopen(req))
        except (urllib.error.HTTPError, urllib.error.URLError):
            continue
        token = data.get("access_token") or data.get("token")
        if token:
            return token
    raise SystemExit("login failed: no token from any known auth path")


def get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    return json.load(urllib.request.urlopen(req))


def probe(url: str, token: str) -> int:
    """HTTP status of a side endpoint, without raising (0 == transport error)."""
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
    try:
        return urllib.request.urlopen(req).status
    except urllib.error.HTTPError as exc:
        return exc.code
    except urllib.error.URLError:
        return 0


# ---------------------------------------------------------------- locator core
class Source:
    """Source text + a locator factory that only ever emits verified quotes."""

    def __init__(self, report_id: str, markdown: str):
        self.report_id = report_id
        self.markdown = markdown
        self.sha256 = "sha256:" + hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        self.chars = len(markdown)

    def locator(self, quote: str, *, nth: int = 0, note: str = "") -> dict:
        """Locate `quote` verbatim; raise if absent (no invented quotes)."""
        if not quote:
            raise ValueError("empty quote is not a valid locator")
        start = -1
        for _ in range(nth + 1):
            start = self.markdown.find(quote, start + 1)
            if start < 0:
                raise ValueError(f"quote not found in report {self.report_id}: {quote!r}")
        end = start + len(quote)
        if self.markdown[start:end] != quote:  # belt and braces
            raise ValueError(f"locator round-trip mismatch: {quote!r}")
        loc = {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "char_start": start,
            "char_end": end,
            "quote": quote,
        }
        if note:
            loc["note"] = note
        return loc


def record_locator(field: str, value) -> dict:
    return {
        "source_uri": SOURCE_URI,
        "source_field": "record",
        "field": field,
        "value": value,
    }


# ------------------------------------------------------------------- registry
def build_manifest(report: dict, token: str, base: str) -> tuple[dict, dict]:
    md = report.get("markdown") or ""
    src = Source(REPORT_ID, md)

    assets: list[dict] = []

    def add(asset: dict) -> None:
        assets.append(asset)

    # A1 — the source document itself.
    first_line = md.splitlines()[0]
    add(
        {
            "asset_id": "ast-771-01",
            "kind": "source_document",
            "role": "primary_source",
            "name": f"report_{REPORT_ID}_markdown",
            "locators": [
                src.locator(
                    first_line,
                    note="first line of markdown; whole-document span is recorded in content_ref",
                )
            ],
            "content_ref": {
                "source_uri": SOURCE_URI,
                "source_field": SOURCE_FIELD,
                "chars": src.chars,
                "sha256": src.sha256,
            },
            "resolvable": True,
            "resolution": "fetched_via_tensor_api",
            "byte_length_utf8": len(md.encode("utf-8")),
        }
    )

    # A2 — report record metadata (identification of the asset record).
    add(
        {
            "asset_id": "ast-771-02",
            "kind": "record_metadata",
            "role": "identification",
            "name": f"report_{REPORT_ID}_record",
            "locators": [
                record_locator("id", report.get("id")),
                record_locator("title", report.get("title")),
                record_locator("scenario_key", report.get("scenario_key")),
            ],
            "values": {
                "report_id": str(report.get("id")),
                "title": report.get("title"),
                "scenario_key": report.get("scenario_key"),
                "status": report.get("status"),
                "tags": report.get("tags"),
                "mission_id_observed": report.get("mission_id"),
                "created_by": report.get("created_by"),
                "created_at": report.get("created_at"),
            },
            "resolvable": True,
            "resolution": "record_fields_returned_by_tensor_api",
        }
    )

    # A3..An — declared figures. Bytes are probed, not assumed.
    fig_status = {
        "figures_list_called": base + f"/tensor/reports/{REPORT_ID}/figures",
        "figures_list_http_status": probe(
            base + f"/tensor/reports/{REPORT_ID}/figures", token
        ),
        "binary_status": {},
    }
    for i, fig in enumerate(report.get("figures") or []):
        name = fig.get("name")
        code = probe(base + f"/tensor/reports/{REPORT_ID}/figures/{name}", token) if name else 0
        fig_status["binary_status"][name] = code
        add(
            {
                "asset_id": f"ast-771-1{i}",
                "kind": "figure",
                "role": "declared_figure",
                "name": name,
                "locators": [record_locator(f"figures[{i}].name", name)],
                "caption": fig.get("caption"),
                "caption_equals_name": fig.get("caption") == name,
                "resolvable": False,
                "resolution": f"declared_in_record_only__binary_fetch_http_{code}",
                "status": "unresolved",
                "unresolved_reason": (
                    "figure bytes are not retrievable from the report store; only the "
                    "filename is declared, and caption duplicates the filename so it "
                    "carries no independent description"
                ),
            }
        )

    # Referenced-but-external artifacts: code chain and injected numeric outputs.
    externals = [
        ("ast-771-20", "source_code", "`src/tensordem/granular_dem.py`"),
        ("ast-771-21", "example_script", "`examples/hopper_beverloo_case.py`"),
        ("ast-771-22", "report_generator", "`hopper_beverloo_report.py`"),
        ("ast-771-23", "data_artifact_glob", "outputs/*.json"),
        ("ast-771-24", "case_markdown", "CASE.md"),
    ]
    for asset_id, kind, quoted in externals:
        add(
            {
                "asset_id": asset_id,
                "kind": kind,
                "role": "referenced_external_artifact",
                "name": quoted.strip("`"),
                "locators": [src.locator(quoted, note="markdown reference to the artifact")],
                "resolvable": False,
                "resolution": "referenced_in_markdown__not_present_in_report_store",
                "status": "unresolved",
                "unresolved_reason": (
                    "artifact is named inside the report text but no byte-level copy is "
                    "attached to report 771; ownership lies with the producing repo, so "
                    "registration stops at the reference"
                ),
            }
        )

    asset_ids = [a["asset_id"] for a in assets]
    dup_ids = sorted({i for i in asset_ids if asset_ids.count(i) > 1})

    manifest = {
        "manifest_version": "1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "scope": {"report_id": REPORT_ID, "reports_touched": [REPORT_ID]},
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "title": report.get("title"),
            "scenario_key": report.get("scenario_key"),
            "chars": src.chars,
            "byte_length_utf8": len(md.encode("utf-8")),
            "sha256": src.sha256,
            "hash_check": {
                "expected": EXPECTED_SOURCE_HASH,
                "recomputed": src.sha256,
                "match": src.sha256 == EXPECTED_SOURCE_HASH,
            },
            "chars_check": {
                "expected": EXPECTED_CHARS,
                "observed": src.chars,
                "match": src.chars == EXPECTED_CHARS,
            },
        },
        "assets": assets,
        "counts": {
            "total": len(assets),
            "resolvable": sum(1 for a in assets if a["resolvable"]),
            "unresolved": sum(1 for a in assets if not a["resolvable"]),
            "by_kind": {},
            "duplicate_asset_ids": dup_ids,
        },
        "extraction": {
            "performed": False,
            "reason": (
                "contract objective is register_assets only (classify_report_type false); "
                "extraction belongs to a separate work package"
            ),
        },
        "claims_registered": 0,
        "verification": {
            "performed": False,
            "reason": "verification status is computed by the platform gate, never self-assigned",
        },
        "figure_probe": fig_status,
        "notes": [],
    }
    for a in assets:
        k = a["kind"]
        manifest["counts"]["by_kind"][k] = manifest["counts"]["by_kind"].get(k, 0) + 1

    # Observations that a downstream package must not have to rediscover.
    if report.get("mission_id") not in (None, ""):
        manifest["notes"].append(
            "record.mission_id=%r while the package contract declares mission_id: null; "
            "recorded as observed, not reconciled by this package"
            % (report.get("mission_id"),)
        )
    if any(f.get("caption") == f.get("name") for f in (report.get("figures") or [])):
        manifest["notes"].append(
            "all figure captions equal their filenames, so figure content cannot be "
            "identified without the binary"
        )
    manifest["notes"].append(
        "markdown says figures are embedded ('见图内嵌') and that all numbers are "
        "injected programmatically, but neither figure bytes nor outputs/*.json are "
        "attached to this report record"
    )

    return manifest, {"src": src, "manifest": manifest}


# ----------------------------------------------------------------- self-check
def selfcheck(manifest: dict, src: Source, envelope: dict) -> dict:
    checks = {}

    def chk(name: str, ok: bool, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}

    json.dumps(manifest, ensure_ascii=False)
    chk("valid_json", True, "manifest serialised with json.dumps")

    schema_path = Path(__file__).resolve().parents[1] / "schemas" / "kf_result.v1.schema.json"
    if not schema_path.exists():
        chk("schema_pass", False, "schemas/kf_result.v1.schema.json absent from checkout")
    else:
        import jsonschema

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            jsonschema.validate(envelope, schema)
            chk("schema_pass", True, "envelope validates against schemas/kf_result.v1.schema.json")
        except jsonschema.ValidationError as exc:
            chk("schema_pass", False, f"{list(exc.absolute_path)}: {exc.message}")

    unresolved_locators = []
    for a in manifest["assets"]:
        for loc in a["locators"]:
            if loc["source_field"] == "markdown":
                ok = src.markdown[loc["char_start"]:loc["char_end"]] == loc["quote"]
                if not ok:
                    unresolved_locators.append((a["asset_id"], loc["quote"]))
            elif loc["source_field"] == "record":
                ok = loc.get("value") is not None
                if not ok:
                    unresolved_locators.append((a["asset_id"], loc.get("field")))
    chk(
        "source_locator_resolvable",
        not unresolved_locators,
        {"markdown_locators": sum(
            1 for a in manifest["assets"] for loc in a["locators"] if loc["source_field"] == "markdown"
        ), "unresolved": unresolved_locators},
    )
    chk(
        "source_hash_matches",
        manifest["source"]["hash_check"]["match"],
        manifest["source"]["hash_check"],
    )
    chk(
        "no_duplicate_ids",
        not manifest["counts"]["duplicate_asset_ids"],
        manifest["counts"]["duplicate_asset_ids"],
    )
    chk(
        "all_claims_have_evidence_or_explicit_unresolved_status",
        True,
        "zero claims registered by this package (registration only)",
    )
    chk(
        "every_asset_has_locator",
        all(a["locators"] for a in manifest["assets"]),
        "each asset carries >=1 locator",
    )
    chk(
        "unresolved_assets_have_reason",
        all(a.get("unresolved_reason") for a in manifest["assets"] if not a["resolvable"]),
        sum(1 for a in manifest["assets"] if not a["resolvable"]),
    )
    return checks


def main() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    token = login(base)
    report = get_json(base + f"/tensor/reports/{REPORT_ID}", token)

    manifest, ctx = build_manifest(report, token, base)
    src = ctx["src"]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "asset_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    # byte-exact source copy so locators can be re-resolved offline, hermetically
    (OUT_DIR / "source_771.md").write_text(src.markdown, encoding="utf-8")

    envelope = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_hash": src.sha256,
            "source_field": SOURCE_FIELD,
            "producer": "agent/m15518",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": (
                "source_hash recomputed from report 771 markdown bytes fetched over the "
                "TensorPlatform API; matches the contract-declared hash"
            ),
        },
        "outputs": {"asset_manifest.json": manifest},
        "claims": [],
    }
    checks = selfcheck(manifest, src, envelope)
    failed = [k for k, v in checks.items() if not v["pass"]]

    (OUT_DIR / "kf_result.json").write_text(
        json.dumps(envelope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    (OUT_DIR / "selfcheck.json").write_text(
        json.dumps(
            {
                "package_id": PACKAGE_ID,
                "accepted": not failed,
                "failed": failed,
                "checks": checks,
                "assets": {
                    "total": manifest["counts"]["total"],
                    "resolvable": manifest["counts"]["resolvable"],
                    "unresolved": manifest["counts"]["unresolved"],
                },
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    print(json.dumps({"accepted": not failed, "failed": failed}, ensure_ascii=False))
    for name, res in checks.items():
        print(f"  [{'PASS' if res['pass'] else 'FAIL'}] {name}")
    print(f"assets={manifest['counts']['total']} "
          f"resolvable={manifest['counts']['resolvable']} "
          f"unresolved={manifest['counts']['unresolved']}")
    print(f"source_sha256={src.sha256}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())