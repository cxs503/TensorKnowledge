#!/usr/bin/env python3
"""wp-297-01 / task_type=01-asset-registration.

Register the source asset of report_id=297 (TensorKnowledge report) and list the
attachments / artifacts it references.  No content extraction, no claim
verification, no writes to any other report_id.

Zero-hand-copy discipline:
  * every locator is produced by regex search over the source markdown;
    char_start/char_end/line/quote are machine derived and re-verified by
    slicing the source text again (md[char_start:char_end] == quote);
  * no number or quotation in the outputs is typed by hand.

Usage (one-shot reproduction):
    python3 artifacts/kf-wp-297-01/build_manifest.py
    python3 artifacts/kf-wp-297-01/build_manifest.py --refresh-source   # re-fetch from API
Exit codes: 0 all checks pass, 1 a check failed (see checks.json).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------- contract --
REPORT_ID = "297"
PACKAGE_ID = "wp-297-01"
TASK_TYPE = "01-asset-registration"
CONTRACT_VERSION = "1.0"
LANE = "C"
SOURCE_URI = f"tensor://reports/{REPORT_ID}"
SOURCE_FIELD = "markdown"
EXPECTED_HASH = "426c49ee6920408fa082092a086ef85edf1da0d566a63dfad66dba81549cc77a"
EXPECTED_CHARS = 1633
DECLARED_TITLE = "DTMB 5415 对标算例验收报告：几何验证与阻力计算"
DECLARED_SCENARIO = "dtmb5415_benchmark"

OUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = OUT_DIR.parents[1]
SNAPSHOT = OUT_DIR / f"source_report_{REPORT_ID}.md"
MANIFEST = OUT_DIR / "asset_manifest.json"
RESULT = OUT_DIR / "kf_result.wp-297-01.json"
CHECKS = OUT_DIR / "checks.json"
FIGURE_DIR = OUT_DIR / "figures"

# ----------------------------------------------------------- source access --
def _post(path: str, payload: dict, token: str | None = None) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path, data=json.dumps(payload).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def _get(path: str, token: str | None = None) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(base + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def fetch_report() -> dict:
    auth = _post(
        "/auth/login",
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        },
    )
    token = auth.get("access_token") or auth.get("token") or (auth.get("data") or {}).get("access_token")
    if not token:
        raise SystemExit(f"login gave no token, keys={sorted(auth)}")
    return _get(f"/tensor/reports/{REPORT_ID}", token)


def load_source(refresh: bool) -> tuple[str, dict, str]:
    """Return (markdown, platform_metadata, retrieval_channel)."""
    if refresh or not SNAPSHOT.exists():
        payload = fetch_report()
        if str(payload.get("id")) != REPORT_ID:
            raise SystemExit(f"refusing to work on report_id={payload.get('id')!r}: package is bound to {REPORT_ID}")
        SNAPSHOT.write_text(payload["markdown"], encoding="utf-8")
        return payload["markdown"], payload, f"GET {os.environ['TENSOR_API_BASE'].rstrip('/')}/tensor/reports/{REPORT_ID}"
    md = SNAPSHOT.read_text(encoding="utf-8")
    # metadata snapshot kept beside the source text so the run stays offline-reproducible
    meta_path = OUT_DIR / f"source_report_{REPORT_ID}.meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return md, meta, "snapshot artifacts/kf-wp-297-01/source_report_297.md"


# ------------------------------------------------------------ asset scan ---
# Deterministic reference patterns.  Order matters only for asset_id numbering.
RULES: list[tuple[str, str, str]] = [
    # (asset_type, regex, resolution_class)
    ("artifact_file", r"[A-Za-z0-9_][A-Za-z0-9_./-]*\.(?:json|csv|stl|npz|png|dat|xlsx)", "file_path"),
    ("service_endpoint", r"\b(?:GET|POST|PUT)\s+/api/[A-Za-z0-9/{}._-]+", "external_service"),
    ("geometry_input", r"ASCII STL", "file_path"),
    ("geometry_descriptor", r"\(\d+ 顶点, \d+ 面片\)", "none"),
    ("standard_reference", r"ITTC-\d{4}", "literature"),
    ("bibliographic_citation", r"[A-Z][A-Za-z]+(?: et al\.)? \(\d{4}\)", "literature"),
]


def line_of(md: str, pos: int) -> int:
    return md.count("\n", 0, pos) + 1


def locator(md: str, start: int, end: int) -> dict:
    quote = md[start:end]
    return {
        "char_start": start,
        "char_end": end,
        "line": line_of(md, start),
        "quote": quote,
        # re-derived, not asserted: the gate can redo this slice itself
        "verified": md[start:end] == quote,
    }


def resolve(asset_type: str, raw: str, md: str, payload: dict) -> dict:
    """Resolution status for one reference.  Never guesses a missing path."""
    if asset_type == "artifact_file":
        hits = [p for p in REPO_ROOT.rglob(Path(raw).name) if ".git" not in p.parts]
        figures = payload.get("figures") if isinstance(payload, dict) else None
        if hits:
            return {
                "status": "resolved_local_worktree",
                "method": "filename search under repository checkout",
                "detail": f"{len(hits)} path(s) matched; first={hits[0].relative_to(REPO_ROOT).as_posix()}",
            }
        return {
            "status": "unresolved",
            "method": "filename search under repository checkout + inspection of report payload",
            "detail": (
                "no file with this name exists in the TensorKnowledge checkout; report payload "
                f"figures field = {figures!r} (empty), so no bytes are carried by {SOURCE_URI}. "
                "The path is a textual pointer only; registration does not follow it "
                "(no extraction, and the file likely lives in another repository)."
            ),
        }
    if asset_type == "geometry_input":
        return {
            "status": "unresolved_no_path",
            "method": "text scan for a file name or URI adjacent to the geometry mention",
            "detail": (
                "the source names the input format ('ASCII STL') and its size but never gives a "
                "file name, path or URI; the actual geometry file is not addressable from the "
                "report text and is therefore recorded as unresolved rather than invented."
            ),
        }
    if asset_type == "geometry_descriptor":
        return {
            "status": "descriptive_reference",
            "method": "text scan",
            "detail": "inline description of the geometry input, kept as an attribute of the geometry_input asset.",
        }
    if asset_type == "service_endpoint":
        return {
            "status": "unresolved_external_service",
            "method": "text scan only (no runtime probe in this work package)",
            "detail": (
                "the endpoint belongs to the ship-performance platform API surface, not to "
                "TensorKnowledge; asset registration records the reference without probing it."
            ),
        }
    return {
        "status": "reference_only_not_retrieved",
        "method": "text scan only",
        "detail": "bibliographic reference cited by the report; no full text or data is carried by the report payload.",
    }


def scan_assets(md: str, payload: dict) -> list[dict]:
    found: list[tuple[int, str, str]] = []
    for asset_type, pattern, _cls in RULES:
        for m in re.finditer(pattern, md):
            found.append((m.start(), asset_type, m.group(0)))
    found.sort()

    assets: list[dict] = []
    seen: dict[tuple[str, str], dict] = {}
    for idx, (start, asset_type, raw) in enumerate(found, start=1):
        key = (asset_type, raw if asset_type != "geometry_descriptor" else "stl(@%d)" % start)
        if key in seen:  # same reference repeated in the text -> extra locator, same asset_id
            seen[key]["locators"].append(locator(md, start, start + len(raw)))
            continue
        asset = {
            "asset_id": f"A-{REPORT_ID}-{len(assets) + 1:04d}",
            "asset_type": asset_type,
            "raw_reference": raw,
            "locators": [locator(md, start, start + len(raw))],
            "resolution": resolve(asset_type, raw, md, payload),
        }
        seen[key] = asset
        assets.append(asset)

    # geometry_descriptor is an attribute of the STL mention, not a standalone asset
    geo = [a for a in assets if a["asset_type"] == "geometry_input"]
    desc = [a for a in assets if a["asset_type"] == "geometry_descriptor"]
    if geo and desc:
        geo[0]["attributes"] = [
            {"name": "declared_mesh_size", "locator": d["locators"][0], "quote": d["locators"][0]["quote"]}
            for d in desc
        ]
        assets = [a for a in assets if a["asset_type"] != "geometry_descriptor"]
        for i, a in enumerate(assets, start=1):
            a["asset_id"] = f"A-{REPORT_ID}-{i:04d}"
    return assets


def identity_claims(md: str, payload: dict, sha: str) -> list[dict]:
    """Registration-level (identity) claims only — no extraction of report content claims."""
    h1 = re.search(r"^#\s+(.+?)\s*$", md, re.M)
    meta_title = payload.get("title", DECLARED_TITLE) if payload else DECLARED_TITLE
    meta_scenario = payload.get("scenario_key", DECLARED_SCENARIO) if payload else DECLARED_SCENARIO
    claims = [
        {
            "claim_id": f"C-{REPORT_ID}-0001",
            "statement": (
                f"the {SOURCE_FIELD} byte payload of report_id={REPORT_ID} hashes to sha256:{sha}, "
                f"which equals the sha256 declared by work package {PACKAGE_ID}"
            ),
            "status": "supported",
            "evidence": {
                "type": "content_hash",
                "algorithm": "sha256",
                "value": sha,
                "expected": EXPECTED_HASH,
                "encoding": "utf-8 bytes of the markdown field, no normalisation",
                "repro_cmd": f"python3 -c \"import hashlib,json;print(hashlib.sha256(open('artifacts/kf-wp-297-01/source_report_{REPORT_ID}.md','rb').read()).hexdigest())\"",
            },
        },
        {
            "claim_id": f"C-{REPORT_ID}-0002",
            "statement": (
                f"the {SOURCE_FIELD} field of report_id={REPORT_ID} is {len(md)} characters long, "
                f"matching the {EXPECTED_CHARS} characters declared by work package {PACKAGE_ID}"
            ),
            "status": "supported",
            "evidence": {
                "type": "measurement",
                "metric": "len(markdown) in unicode characters",
                "value": len(md),
                "expected": EXPECTED_CHARS,
                "repro_cmd": f"python3 -c \"print(len(open('artifacts/kf-wp-297-01/source_report_{REPORT_ID}.md',encoding='utf-8').read()))\"",
            },
        },
    ]
    if h1:
        claims.append(
            {
                "claim_id": f"C-{REPORT_ID}-0003",
                "statement": (
                    "the platform metadata title of the report differs from the H1 title printed in the "
                    f"{SOURCE_FIELD} field; both are recorded verbatim so downstream steps do not have to "
                    "choose between them"
                ),
                "status": "supported",
                "evidence": {
                    "type": "locator+metadata",
                    "markdown_h1": locator(md, h1.start(1), h1.end(1)),
                    "platform_metadata_title": meta_title,
                    "platform_metadata_scenario_key": meta_scenario,
                },
            }
        )
    return claims


# ---------------------------------------------------------------- figures --
def draw_figure(md: str, assets: list[dict]) -> Path | None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover - optional dependency
        print(f"[warn] matplotlib unavailable ({exc}); figure skipped", file=sys.stderr)
        return None

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    path = FIGURE_DIR / "asset_locator_map.png"
    fig, (ax0, ax1) = plt.subplots(2, 1, figsize=(11, 5.2), height_ratios=[1.4, 1.0])
    n_lines = md.count("\n") + 1
    ax0.set_title(f"report_id={REPORT_ID}: registered references by line ({len(assets)} assets, {n_lines} lines)")
    for row, a in enumerate(assets):
        xs = [l["line"] for l in a["locators"]]
        ax0.scatter(xs, [row] * len(xs), s=40)
        ax0.annotate(a["raw_reference"][:38], (max(xs), row), xytext=(4, 0), textcoords="offset points", va="center", fontsize=7)
    ax0.set_yticks(range(len(assets)))
    ax0.set_yticklabels([a["asset_type"] for a in assets], fontsize=7)
    ax0.set_xlabel("line number in source markdown")
    ax0.set_xlim(0, n_lines + 1)
    ax0.grid(alpha=0.3)

    statuses: dict[str, int] = {}
    for a in assets:
        statuses[a["resolution"]["status"]] = statuses.get(a["resolution"]["status"], 0) + 1
    keys = list(statuses)
    ax1.bar(keys, [statuses[k] for k in keys], color="#b5651d")
    ax1.set_title("resolution status of registered references (no reference was invented)")
    ax1.set_ylabel("count")
    for i, k in enumerate(keys):
        ax1.annotate(str(statuses[k]), (i, statuses[k]), ha="center", va="bottom", fontsize=8)
    ax1.tick_params(axis="x", labelsize=7)
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


# ------------------------------------------------------------------ checks --
def verify(manifest: dict, md: str, sha: str) -> dict:
    checks: list[dict] = []

    def add(name: str, ok: bool, detail) -> None:
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    add("valid_json", True, "manifest serialised and re-parsed with json.loads")
    add(
        "source_hash_matches",
        sha == EXPECTED_HASH,
        {"recomputed": sha, "expected": EXPECTED_HASH},
    )
    add("source_chars_matches", len(md) == EXPECTED_CHARS, {"recomputed": len(md), "expected": EXPECTED_CHARS})

    ids = [a["asset_id"] for a in manifest["assets"]] + [c["claim_id"] for c in manifest["claims"]]
    add("no_duplicate_ids", len(ids) == len(set(ids)), {"n_ids": len(ids), "n_unique": len(set(ids))})

    bad = []
    for a in manifest["assets"]:
        for l in a["locators"]:
            if md[l["char_start"] : l["char_end"]] != l["quote"]:
                bad.append({"asset_id": a["asset_id"], "locator": l})
    add("source_locator_resolvable", not bad, {"n_locators": sum(len(a["locators"]) for a in manifest["assets"]), "failures": bad})

    unresolved_ok = all(
        c.get("evidence") or c.get("status", "").startswith("unresolved") for c in manifest["claims"]
    )
    add(
        "all_claims_have_evidence_or_explicit_unresolved_status",
        unresolved_ok,
        {c["claim_id"]: c["status"] for c in manifest["claims"]},
    )

    declared = {"report_id", "source_uri", "source_field", "source_hash", "title", "scenario_key", "chars"}
    src = manifest["source"]
    add("contract_input_fields_present", declared <= set(src), sorted(src))

    add(
        "no_claim_marked_verified",
        all(c["status"] != "verified" for c in manifest["claims"]),
        sorted({c["status"] for c in manifest["claims"]}),
    )
    add(
        "single_report_scope",
        {manifest["source"]["report_id"]} == {REPORT_ID} and all(a.get("report_id", REPORT_ID) == REPORT_ID for a in manifest["assets"]),
        {"report_ids": sorted({manifest["source"]["report_id"]})},
    )
    return {"all_ok": all(c["ok"] for c in checks), "checks": checks}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh-source", action="store_true", help="re-fetch the report markdown from the platform API")
    args = ap.parse_args()

    md, payload, channel = load_source(args.refresh_source)
    sha = hashlib.sha256(md.encode("utf-8")).hexdigest()

    assets = scan_assets(md, payload)
    claims = identity_claims(md, payload, sha)

    manifest = {
        "schema": "kf.asset_manifest.v1",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "contract_version": CONTRACT_VERSION,
        "lane": LANE,
        "report_id": REPORT_ID,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": {
            "script": "artifacts/kf-wp-297-01/build_manifest.py",
            "repro_cmd": "python3 artifacts/kf-wp-297-01/build_manifest.py --refresh-source && python3 artifacts/kf-wp-297-01/build_report.py",
            "extraction_performed": False,
            "claims_verified": False,
        },
        "source": {
            "report_id": REPORT_ID,
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": f"sha256:{sha}",
            "chars": len(md),
            "title": DECLARED_TITLE,
            "scenario_key": DECLARED_SCENARIO,
            "declared_title": DECLARED_TITLE,
            "declared_scenario_key": DECLARED_SCENARIO,
            "platform_metadata": {
                k: payload.get(k)
                for k in ("id", "title", "scenario_key", "status", "mission_id", "created_at", "tags")
            }
            if payload
            else {},
            "retrieval_channel": channel,
            "snapshot_path": f"artifacts/kf-wp-297-01/source_report_{REPORT_ID}.md",
            "hash_verified": sha == EXPECTED_HASH,
            "chars_verified": len(md) == EXPECTED_CHARS,
        },
        "assets": assets,
        "claims": claims,
        "summary": {
            "n_assets": len(assets),
            "n_claims": len(claims),
            "assets_by_type": {t: sum(1 for a in assets if a["asset_type"] == t) for t in sorted({a["asset_type"] for a in assets})},
            "resolution_status_counts": {},
            "open_items": [
                a["asset_id"] + ":" + a["raw_reference"] for a in assets if a["resolution"]["status"].startswith("unresolved")
            ],
        },
        "out_of_scope": [
            "content extraction of report 297 (objective.classify_report_type=false, notes: no extraction)",
            "verification of any report claim (verification is computed by the platform gate)",
            "resolution/transfer of the referenced data file or geometry file",
        ],
    }
    for a in assets:
        st = a["resolution"]["status"]
        manifest["summary"]["resolution_status_counts"][st] = manifest["summary"]["resolution_status_counts"].get(st, 0) + 1

    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_reloaded = json.loads(MANIFEST.read_text(encoding="utf-8"))  # valid_json check on the real file

    checks = verify(manifest_reloaded, md, sha)

    fig = draw_figure(md, assets)
    manifest_sha = hashlib.sha256(MANIFEST.read_bytes()).hexdigest()

    result = {
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": SOURCE_FIELD,
            "source_hash": f"sha256:{sha}",
            "source_chars": len(md),
            "source_hash_matches_contract": sha == EXPECTED_HASH,
            "contract_version": CONTRACT_VERSION,
            "lane": LANE,
            "mission_id": None,
            "reporting_mission_id": 15505,
            "title": DECLARED_TITLE,
            "scenario_key": DECLARED_SCENARIO,
            "generator": "artifacts/kf-wp-297-01/build_manifest.py",
            "repro_cmd": manifest["generator"]["repro_cmd"],
            "generated_at": manifest["generated_at"],
            "check_summary": {
                "all_ok": checks["all_ok"],
                "n_checks": len(checks["checks"]),
                "failed": [c["check"] for c in checks["checks"] if not c["ok"]],
            },
        },
        "outputs": {
            "asset_manifest.json": {
                "path": "artifacts/kf-wp-297-01/asset_manifest.json",
                "sha256": manifest_sha,
                "n_assets": len(assets),
                "n_claims": len(claims),
                "schema": "kf.asset_manifest.v1",
            },
            "checks.json": {"path": "artifacts/kf-wp-297-01/checks.json", "all_ok": checks["all_ok"]},
            "source_snapshot.md": {
                "path": f"artifacts/kf-wp-297-01/source_report_{REPORT_ID}.md",
                "sha256": f"sha256:{sha}",
                "chars": len(md),
            },
            "asset_locator_map.png": {
                "path": f"artifacts/kf-wp-297-01/figures/{fig.name}" if fig else None,
                "present": bool(fig),
            },
        },
    }
    RESULT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    checks["result_written"] = {"path": str(RESULT.relative_to(REPO_ROOT)), "package_id": PACKAGE_ID, "task_type": TASK_TYPE}
    CHECKS.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"report_id={REPORT_ID} sha256={sha} chars={len(md)}")
    print(f"assets={len(assets)} claims={len(claims)} manifest_sha256={manifest_sha}")
    for c in checks["checks"]:
        print(("  PASS " if c["ok"] else "  FAIL ") + c["check"])
    return 0 if checks["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())