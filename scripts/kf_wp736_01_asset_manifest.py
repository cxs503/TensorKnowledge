#!/usr/bin/env python3
"""KF work package wp-736-01 — asset registration for report_id=736.

Scope (contract wp-736-01, task_type 01-asset-registration)
-----------------------------------------------------------
Registration only: confirm the report identity + markdown byte hash, enumerate
the *declarative* attachments/artifacts the report points at, and pin a
locator (verbatim quote + char offsets) for every registered asset.  No
extraction, no claim generation, no classification, nothing marked verified.

Guarantees implemented here (each is asserted, not assumed):

* ``source_hash`` is recomputed from the bytes actually fetched in this run and
  must equal the contract hash ``sha256:9726d9bc…5ef0`` (mismatch -> exit 1).
* Every ``locator.quote`` satisfies ``markdown[char_start:char_end] == quote``
  (zero-based, half-open, Python *str* indices over the UTF-8-decoded
  markdown) — so the platform can re-slice the markdown and match verbatim.
* No asset is marked ``verified``; assets whose bytes are not retrievable
  through the declared channel carry an explicit unresolved status.
* ``claims`` is an empty list (allowed by the contract: no forced claims).

Usage::

    python3 scripts/kf_wp736_01_asset_manifest.py --out docs/kf/wp-736-01
    python3 scripts/kf_wp736_01_asset_manifest.py --verify \
        --out docs/kf/wp-736-01        # re-fetch + re-check pinned manifest
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

REPORT_ID = "736"
PACKAGE_ID = "wp-736-01"
TASK_TYPE = "01-asset-registration"
SOURCE_URI = "tensor://reports/736"
SOURCE_FIELD = "markdown"
EXPECTED_SOURCE_HASH = "sha256:9726d9bcd05657bd5cf0833a4c47a855d683bc5c5ae19b89f6ca49af4b945ef0"
EXPECTED_CHARS = 8500

MANIFEST_NAME = "asset_manifest.json"
RESULT_NAME = "kf_result_wp-736-01.json"

# Declarative artifact references the report makes, as verbatim backticked spans.
# Resolution status is decided by the resolver, never assumed.
INLINE_REFERENCE_QUOTES = [
    "tests/e2e1b_negative/attack_cases.py",
    "scripts/e2e1b_negative_runner.py",
    "scripts/validate_lineage.py",
    "examples/lineage_couette_pass.json",
    "examples/lineage_baseline_no_version.json",
    "src.validation.solver_config",
    "src.validation.run_admission",
    "outputs/e2e1b_negative/evidence.json",
    "docs/benchmarks/e2e1_negative_tests/VERDICTS.md",
    "docs/benchmarks/e2e1_negative_tests/DEFECTS.md",
    "contracts/tensorphysics-run-manifest-v1.schema.json",
    "tools/sample_db/backfill.py",
    "backend/services/control_project_runtime.py",
]

# Figure anchors: the report's own prose pointer to each figure (verbatim).
FIGURE_ANCHORS = [
    {"name": "gate_matrix.png", "quote": "图 1 为攻击 × 门 拦截矩阵"},
    {"name": "tau_nu_domain.png", "quote": "图 2 为 τ–ν 判据域与 Ma 上限"},
]


# ---------------------------------------------------------------------------
# retrieval
# ---------------------------------------------------------------------------
def _login(base: str) -> str:
    user = os.environ.get("TENSOR_AGENT_USER")
    password = os.environ.get("TENSOR_AGENT_PASS")
    if not (user and password):
        raise SystemExit("TENSOR_AGENT_USER / TENSOR_AGENT_PASS not set")
    req = urllib.request.Request(
        base.rstrip("/") + "/auth/login",
        data=json.dumps({"username": user, "password": password}).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.load(resp)
    token = payload.get("access_token") or payload.get("token")
    if not token:
        raise SystemExit("login returned no access_token")
    return token


def probe_api(path: str, token: str | None = None) -> dict:
    """Read-only probe of a platform route; records the outcome verbatim."""
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        return {"path": path, "outcome": "skipped", "note": "TENSOR_API_BASE not set"}
    tok = token or _login(base)
    req = urllib.request.Request(base.rstrip("/") + path, headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return {
                "path": path,
                "http_status": resp.status,
                "content_type": resp.headers.get("content-type"),
                "body_bytes": len(resp.read()),
            }
    except Exception as exc:  # noqa: BLE001 - the failure text *is* the evidence
        body = getattr(exc, "read", lambda: b"")()
        return {
            "path": path,
            "http_status": getattr(exc, "code", None),
            "detail": body.decode("utf-8", "replace")[:200] if body else str(exc),
        }


def fetch_report(report_id: str = REPORT_ID) -> dict:
    """GET the report through the platform API (the only channel used here)."""
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        raise SystemExit("TENSOR_API_BASE not set")
    token = _login(base)
    req = urllib.request.Request(
        base.rstrip("/") + f"/tensor/reports/{report_id}",
        headers={"Authorization": "Bearer " + token},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def locate(markdown: str, quote: str, start_at: int = 0) -> dict:
    """Resolve a verbatim quote to a half-open char range; raise if absent."""
    start = markdown.find(quote, start_at)
    if start < 0:
        raise SystemExit(f"quote not found in markdown: {quote!r}")
    end = start + len(quote)
    if markdown[start:end] != quote:  # belt and braces
        raise SystemExit(f"locator slice mismatch for {quote!r}")
    return {
        "field": SOURCE_FIELD,
        "char_start": start,
        "char_end": end,
        "quote": quote,
    }


def host_probe(rel_path: str) -> dict:
    """Read-only existence probe against the producing worktree, if present.

    The referenced paths are relative to the *producing* repo (mission 810
    worktree), not to this worktree.  We only record what is observable; the
    absence of a copy is reported, never papered over.
    """
    candidates = [Path("/root/tp-agent/work/m810") / rel_path]
    for cand in candidates:
        if cand.exists():
            return {
                "status": "present_on_host",
                "observed_path": str(cand),
                "note": "existence only; no bytes ingested, no checksum registered",
            }
    return {
        "status": "unresolved",
        "reason": (
            "referenced path is relative to the producing repo (mission 810 worktree); "
            "no copy exists on this host and the package declares no retrieval channel "
            "for it in this worktree — recorded as a declarative reference only"
        ),
    }


# ---------------------------------------------------------------------------
# manifest construction
# ---------------------------------------------------------------------------
def build_manifest(report: dict) -> tuple[dict, dict]:
    markdown = report.get("markdown") or ""
    if not isinstance(markdown, str) or not markdown:
        raise SystemExit("report markdown missing/empty -> cannot register")

    source_hash = sha256_text(markdown)
    if source_hash != EXPECTED_SOURCE_HASH:
        raise SystemExit(
            "source_hash mismatch: contract=%s recomputed=%s"
            % (EXPECTED_SOURCE_HASH, source_hash)
        )
    chars, nbytes = len(markdown), len(markdown.encode("utf-8"))
    if chars != EXPECTED_CHARS:
        raise SystemExit(f"char count mismatch: contract={EXPECTED_CHARS} actual={chars}")

    figures_meta = {f.get("name"): f for f in (report.get("figures") or [])}

    assets: list[dict] = []

    # --- asset 1: the report markdown itself (primary source) --------------
    h1 = markdown.splitlines()[0]
    assets.append(
        {
            "asset_id": "ast-736-report-markdown",
            "kind": "report_markdown",
            "role": "primary_source",
            "declared_uri": f"{SOURCE_URI}#{SOURCE_FIELD}",
            # anchor = the report's own H1 line (verbatim, single line); the
            # asset itself spans the whole field (see covers).
            "locator": locate(markdown, h1),
            "covers": {"field": SOURCE_FIELD, "char_start": 0, "char_end": len(markdown)},
            "hash": {"algorithm": "sha256", "value": source_hash, "scope": "utf-8 bytes of the markdown field"},
            "size": {"chars": chars, "bytes": nbytes},
            "status": "registered",
            "extraction": {"performed": False, "reason": "package objective is registration only"},
        }
    )

    # --- figures: declared in report metadata, anchored by report prose ----
    probe_paths = [
        f"/tensor/reports/{REPORT_ID}/figures/{a['name']}" for a in FIGURE_ANCHORS
    ] + [f"/tensor/reports/{REPORT_ID}/attachments"]
    channel_probes = [probe_api(p) for p in probe_paths]

    for idx, anchor in enumerate(FIGURE_ANCHORS, start=1):
        meta = figures_meta.get(anchor["name"]) or {}
        assets.append(
            {
                "asset_id": f"ast-736-fig{idx:02d}",
                "kind": "figure",
                "role": "report_figure",
                "declared_uri": f"{SOURCE_URI}/figures/{anchor['name']}",
                "figure_name": anchor["name"],
                "caption": meta.get("caption"),
                "caption_source": "report metadata figures[].caption (verbatim)",
                "locator": locate(markdown, anchor["quote"]),
                "hash": None,
                "payload_status": "declared_not_fetched",
                "payload_probe": next(
                    (c for c in channel_probes if c.get("path", "").endswith(anchor["name"])),
                    None,
                ),
                "status": "unresolved",
                "unresolved_reason": (
                    "figure bytes are not retrievable through this package's declared channel "
                    "(tensor://reports/736 markdown field); name+caption registered, payload not ingested"
                ),
                "extraction": {"performed": False, "reason": "no extraction in this package"},
            }
        )

    # --- inline artifact references ---------------------------------------
    for idx, quote in enumerate(sorted(INLINE_REFERENCE_QUOTES), start=1):
        probe = host_probe(quote)
        assets.append(
            {
                "asset_id": f"ast-736-ref{idx:02d}",
                "kind": "inline_artifact_reference",
                "role": "referenced_artifact",
                "declared_uri": None,
                "referenced_path": quote,
                "locator": locate(markdown, quote),
                "markup_context": "quoted as a code span in the report body",
                "hash": None,
                "payload_status": "not_ingested",
                "status": probe["status"],
                **({k: v for k, v in probe.items() if k != "status"}),
                "extraction": {"performed": False, "reason": "reference registration only"},
            }
        )

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate asset_id in manifest")

    unresolved = [a["asset_id"] for a in assets if a["status"] != "registered"]
    manifest = {
        "schema_version": "kf-asset-manifest/1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generator": "scripts/kf_wp736_01_asset_manifest.py",
        "source": {
            "uri": SOURCE_URI,
            "field": SOURCE_FIELD,
            "hash": {"algorithm": "sha256", "value": source_hash, "recomputed_in_run": True, "matches_contract": True},
            "size": {"chars": chars, "bytes": nbytes},
            "report_facts": {
                "title": report.get("title"),
                "scenario_key": report.get("scenario_key"),
                "mission_id": report.get("mission_id"),
                "status": report.get("status"),
                "created_at": report.get("created_at"),
                "tags": report.get("tags"),
            },
        },
        "channel_probes": channel_probes,
        "assets": assets,
        "asset_count": len(assets),
        "registered_count": len(assets) - len(unresolved),
        "unresolved_count": len(unresolved),
        "unresolved_asset_ids": unresolved,
        "claims": [],
        "claims_note": (
            "empty by contract: objective.register_assets=true, objective.classify_report_type=false, "
            "no_forced_claim_generation=true — this package registers assets and does not extract claims"
        ),
        "verification": {
            "marked_verified_claims": 0,
            "note": "verification is computed by the platform gate; this manifest marks nothing verified",
        },
    }
    return manifest, {"markdown": markdown, "source_hash": source_hash, "chars": chars, "bytes": nbytes}


def build_result(manifest: dict, manifest_path: Path, repro_cmd: str, retrieved_at: str) -> dict:
    return {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": manifest["source"]["hash"]["value"],
            "source_hash_algorithm": "sha256",
            "source_hash_scope": "utf-8 bytes of the tensor_reports.markdown field",
            "source_hash_recomputed_in_run": manifest["source"]["hash"]["value"],
            "source_hash_matches_contract": True,
            "source_chars": manifest["source"]["size"]["chars"],
            "source_bytes": manifest["source"]["size"]["bytes"],
            "retrieved_at": retrieved_at,
            "retrieval": {
                "method": "platform_api_read",
                "endpoint": "GET ${TENSOR_API_BASE}/tensor/reports/736",
                "auth": "bearer token (agent user), no write to the source",
            },
            "producer": {
                "repo": "TensorKnowledge",
                "worktree": "/root/tp-agent/work/m15516",
                "branch": "agent/m15516",
            },
            "generator": "scripts/kf_wp736_01_asset_manifest.py",
            "repro_cmd": repro_cmd,
        },
        "outputs": {
            "asset_manifest.json": {
                "path": str(manifest_path),
                "sha256": sha256_file(manifest_path),
                "assets": manifest["asset_count"],
                "registered": manifest["registered_count"],
                "unresolved": manifest["unresolved_count"],
                "claims": len(manifest["claims"]),
            }
        },
    }


# ---------------------------------------------------------------------------
# verify mode
# ---------------------------------------------------------------------------
def verify(out_dir: Path) -> int:
    manifest_path = out_dir / MANIFEST_NAME
    if not manifest_path.is_file():
        print(f"FAIL missing manifest {manifest_path}")
        return 1
    manifest = json.loads(manifest_path.read_text())
    report = fetch_report(manifest.get("report_id", REPORT_ID))
    markdown = report.get("markdown") or ""
    problems: list[str] = []

    if sha256_text(markdown) != EXPECTED_SOURCE_HASH:
        problems.append("source hash drift vs contract pin")
    if len(markdown) != manifest["source"]["size"]["chars"]:
        problems.append("char count drift vs manifest")
    if manifest.get("claims") != []:
        problems.append("claims must stay an empty list in this package")
    ids = [a["asset_id"] for a in manifest.get("assets", [])]
    if len(ids) != len(set(ids)):
        problems.append("duplicate asset_id")
    for asset in manifest.get("assets", []):
        loc = asset.get("locator") or {}
        quote = loc.get("quote")
        if not isinstance(quote, str) or not quote:
            problems.append(f"{asset.get('asset_id')}: missing locator quote")
            continue
        s, e = loc.get("char_start"), loc.get("char_end")
        if not isinstance(s, int) or not isinstance(e, int) or markdown[s:e] != quote:
            problems.append(f"{asset.get('asset_id')}: locator does not resolve")
        cov = asset.get("covers")
        if cov is not None:
            if cov.get("char_start") != 0 or cov.get("char_end") != len(markdown):
                problems.append(f"{asset.get('asset_id')}: covers range drift vs markdown length")
        if not asset.get("hash") and asset.get("status") == "registered":
            problems.append(f"{asset.get('asset_id')}: registered without a hash")
        if asset.get("status") == "verified":
            problems.append(f"{asset.get('asset_id')}: must not be marked verified")

    if problems:
        for p in problems:
            print("FAIL", p)
        return 1
    print(f"OK verify: {len(ids)} assets, locators resolve, hash pinned, claims empty")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="docs/kf/wp-736-01", help="output directory (inside the worktree)")
    ap.add_argument("--verify", action="store_true", help="re-fetch the report and re-check the pinned manifest")
    args = ap.parse_args(argv)

    out_dir = Path(args.out)
    if args.verify:
        return verify(out_dir)

    retrieved_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    report = fetch_report()
    manifest, facts = build_manifest(report)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = out_dir / MANIFEST_NAME
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

    repro_cmd = (
        "python3 scripts/kf_wp736_01_asset_manifest.py --out docs/kf/wp-736-01 "
        "&& python3 scripts/kf_wp736_01_asset_manifest.py --verify --out docs/kf/wp-736-01"
    )
    result = build_result(manifest, manifest_path, repro_cmd, retrieved_at)
    (out_dir / RESULT_NAME).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

    print(json.dumps({
        "manifest": str(manifest_path),
        "manifest_sha256": result["outputs"]["asset_manifest.json"]["sha256"],
        "source_hash": facts["source_hash"],
        "chars": facts["chars"],
        "bytes": facts["bytes"],
        "assets": manifest["asset_count"],
        "registered": manifest["registered_count"],
        "unresolved": manifest["unresolved_count"],
        "unresolved_ids": manifest["unresolved_asset_ids"],
        "claims": len(manifest["claims"]),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())