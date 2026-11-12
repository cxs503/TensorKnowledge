#!/usr/bin/env python3
"""KF work package wp-1716-01 — 01-asset-registration for report_id=1716.

Scope (hard): only report 1716. Register the source asset (report markdown,
hash-pinned), enumerate the parseable attachments / artifacts *declared* by the
report, and pin every one of them to a verbatim, re-sliceable locator in the
markdown. No extraction, no classification of report type, no claim generation,
nothing marked verified.

Design notes
------------
* The source of truth is the platform API field ``tensor_reports.markdown`` for
  id=1716.  The bytes are re-hashed in-run and compared both to the package
  contract (``source_hash`` in wp-1716-01) and to the on-disk snapshot, so the
  platform can replay the identity check independently.
* Every locator is a half-open ``[char_start, char_end)`` window over the
  markdown string plus the verbatim ``quote``; the generator asserts
  ``markdown[char_start:char_end] == quote`` for all of them and refuses to
  write the manifest otherwise.  All occurrences of each token are recorded so
  a consumer can also resolve the second/third mention.
* Unresolved assets are *not* silently upgraded: a missing byte channel is
  recorded as an explicit reason code (``no_byte_channel``, ``figure_payload_404``,
  ``producer_repo_not_in_worktree``), never as "present".
* No wall-clock field is written into the manifest, so re-running the generator
  is byte-stable (the report carries the run timestamp instead).
* Deliverables live under ``docs/kf/wp-1716-01/`` on purpose: the mission push
  gate drops ``artifacts/**`` (see docs/ops/filter-audit.md), so a manifest kept
  there would not reach GitHub and the locators would be unresolvable downstream.

Usage
-----
    python3 scripts/kf_wp1716_01_asset_manifest.py                 # fetch + build
    python3 scripts/kf_wp1716_01_asset_manifest.py --offline       # rebuild from snapshot
    python3 scripts/kf_wp1716_01_asset_manifest.py --verify        # re-check, no network
    python3 scripts/kf_wp1716_01_asset_manifest.py --verify --offline
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
from pathlib import Path

# ---------------------------------------------------------------- constants --
PACKAGE_ID = "wp-1716-01"
TASK_TYPE = "01-asset-registration"
REPORT_ID = "1716"
CONTRACT_SOURCE_HASH = (
    "sha256:79cd7a448000f110435f121ee33ed9909bc3989cc6ac1046b16c0203e3936a8b"
)
CONTRACT_SOURCE_CHARS = 4159
CONTRACT_TITLE = (
    "平台方差分解能力补齐与验证欠账清偿：黑箱 Sobol' 采样通道 + "
    "已合并 PCE 谱通道解析复核（34 测试绿）"
)
CONTRACT_SCENARIO_KEY = "platform_gsa_sobol_verification"
LANE = "C"

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = REPO_ROOT / "docs" / "kf" / "wp-1716-01"
SNAPSHOT = OUT_DIR / "source_report_1716.md"
MANIFEST = OUT_DIR / "asset_manifest.json"
CHECKS = OUT_DIR / "checks.json"

# 工件/附件引用：报告正文里以反引号标注的仓内相对路径（含可选的 ::symbol）。
PATH_TOKEN_RE = re.compile(
    r"`((?:backend|tools|tests|artifacts|docs)/[A-Za-z0-9_./-]+(?:::[A-Za-z0-9_]+)?)`"
)
FIG_TOKEN_RE = re.compile(r"`([A-Za-z0-9_-]+\.png)`")
GITREF_RE = re.compile(r"`(agent/[A-Za-z0-9_.\-/]+)`")


# ------------------------------------------------------------------ hashing --
def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


# ---------------------------------------------------------------- retrieval --
def _token() -> str:
    api = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    req = urllib.request.Request(
        api + "/auth/login", data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]


def api_get(token: str, path: str):
    """Return (status, body_text_or_bytes, content_type). Never raises on 4xx."""
    api = os.environ["TENSOR_API_BASE"].rstrip("/")
    req = urllib.request.Request(
        api + path, headers={"Authorization": "Bearer " + token}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read(), r.headers.get("content-type", "")
    except urllib.error.HTTPError as e:
        return e.code, e.read(), e.headers.get("content-type", "")


def fetch_report() -> dict:
    token = _token()
    status, body, _ = api_get(token, f"/tensor/reports/{REPORT_ID}")
    if status != 200:
        raise SystemExit(f"report fetch failed: HTTP {status}: {body[:200]!r}")
    return json.loads(body)


def probe_channels(token: str, figure_names: list[str]) -> list[dict]:
    probes = []
    paths = [f"/tensor/reports/{REPORT_ID}/figures/{n}" for n in figure_names]
    paths += [
        f"/tensor/reports/{REPORT_ID}/attachments",
        f"/tensor/reports/{REPORT_ID}/figures",
    ]
    for p in paths:
        status, body, _ = api_get(token, p)
        try:
            detail = json.loads(body)["detail"]
        except Exception:
            detail = body[:120].decode("utf-8", "replace")
        probes.append({"path": p, "http_status": status, "detail": detail})
    return probes


# ------------------------------------------------------------------ locator --
def occurrences(md: str, token: str) -> list[dict]:
    """All half-open char ranges where ``token`` occurs verbatim."""
    out, start = [], 0
    while True:
        i = md.find(token, start)
        if i < 0:
            break
        out.append({"char_start": i, "char_end": i + len(token), "quote": token})
        start = i + len(token)
    return out


def line_quote(md: str, needle: str) -> dict:
    """Char range of the first line containing ``needle`` (verbatim, no strip)."""
    i = md.find(needle)
    if i < 0:
        raise SystemExit(f"anchor not found in markdown: {needle!r}")
    s = md.rfind("\n", 0, i) + 1
    e = md.find("\n", i)
    e = len(md) if e < 0 else e
    return {"char_start": s, "char_end": e, "quote": md[s:e]}


def local_presence(relpath: str) -> dict:
    p = REPO_ROOT / relpath
    return {"probed_at": f"worktree:{REPO_ROOT}", "exists": p.exists()}


# ------------------------------------------------------------------ assets --
def build_assets(md: str, report: dict) -> list[dict]:
    figures_meta = report.get("figures") or []
    assets: list[dict] = []

    # 1. the report markdown itself — the only asset whose bytes we really hold
    head = md.split("\n", 1)[0]
    assets.append(
        {
            "asset_id": f"ast-{REPORT_ID}-report-markdown",
            "kind": "report_markdown",
            "role": "primary_source",
            "declared_uri": f"tensor://reports/{REPORT_ID}#markdown",
            "locator": {"field": "markdown", "char_start": 0, "char_end": len(head),
                        "quote": head},
            "covers": {"field": "markdown", "char_start": 0, "char_end": len(md)},
            "hash": {
                "algorithm": "sha256",
                "value": sha256_text(md),
                "scope": "utf-8 bytes of the markdown field",
                "recomputed_in_run": True,
            },
            "size": {"chars": len(md), "bytes": len(md.encode("utf-8"))},
            "status": "registered",
            "resolution": {
                "method": "platform_api_read",
                "endpoint": f"GET $TENSOR_API_BASE/tensor/reports/{REPORT_ID}",
                "bytes_obtained": True,
                "snapshot": str(SNAPSHOT.relative_to(REPO_ROOT)),
            },
        }
    )

    # 2. declared figures (name + caption live in the report metadata record)
    for idx, fig in enumerate(figures_meta, start=1):
        name = fig.get("name", "")
        if not name:
            continue
        occ = occurrences(md, name)
        if not occ:
            raise SystemExit(f"figure {name!r} has no verbatim anchor in markdown")
        assets.append(
            {
                "asset_id": f"ast-{REPORT_ID}-figure-{idx}-{Path(name).stem.replace('_','-')}",
                "kind": "figure",
                "role": "result_figure",
                "declared_uri": f"tensor://reports/{REPORT_ID}#figures/{name}",
                "declared_metadata": {"name": name, "caption": fig.get("caption")},
                "locator": {"field": "markdown", **occ[0]},
                "occurrences": occ,
                "hash": None,
                "size": None,
                "status": "declared_not_fetched",
                "resolution": {
                    "method": "metadata_field_plus_prose_anchor",
                    "bytes_obtained": False,
                    "unresolved_reason": {
                        "code": "figure_payload_404",
                        "detail": (
                            f"GET /tensor/reports/{REPORT_ID}/figures/{name} returns 404 "
                            "'figure not found'; the report record carries name+caption "
                            "only, so the PNG bytes are declared but not held here."
                        ),
                    },
                },
            }
        )

    # 3. inline artifact references (repo-relative paths named in the prose)
    seen: dict[str, dict] = {}
    for m in PATH_TOKEN_RE.finditer(md):
        tok = m.group(1)
        seen.setdefault(tok, {"token": tok, "positions": []})["positions"].append(m.start())
    for tok in seen:
        path_part, _, symbol = tok.partition("::")
        occ = occurrences(md, tok)
        probe = local_presence(path_part)
        assets.append(
            {
                "asset_id": "ast-{}-path-{}".format(
                    REPORT_ID,
                    re.sub(r"[^a-z0-9]+", "-", path_part.lower()).strip("-"),
                ),
                "kind": "referenced_artifact_path",
                "role": "declared_producer_or_output",
                "declared_uri": f"tensor://reports/{REPORT_ID}#{tok}",
                "declared_path": path_part,
                "declared_symbol": symbol or None,
                "locator": {"field": "markdown", **occ[0]},
                "occurrences": occ,
                "hash": None,
                "size": None,
                "status": "declared_not_fetched",
                "resolution": {
                    "method": "path_token_in_prose",
                    "bytes_obtained": False,
                    "local_worktree_probe": probe,
                    "unresolved_reason": {
                        "code": "producer_repo_not_in_worktree",
                        "detail": (
                            "the path is declared inside this report (repo TensorPlatform, "
                            "per the report header) but the artifact registry ships no byte "
                            "channel for it and the path is absent from this worktree "
                            f"(exists={probe['exists']}), so bytes are not held."
                        ),
                    },
                },
            }
        )

    # 4. producer git ref declared in the report header
    for m in GITREF_RE.finditer(md):
        tok = m.group(1)
        occ = occurrences(md, tok)
        assets.append(
            {
                "asset_id": f"ast-{REPORT_ID}-gitref-{re.sub(r'[^a-z0-9]+','-',tok.lower()).strip('-')}",
                "kind": "git_ref",
                "role": "provenance_pointer",
                "declared_uri": f"tensor://reports/{REPORT_ID}#{tok}",
                "declared_ref": tok,
                "declared_repo": "TensorPlatform",
                "locator": {"field": "markdown", **occ[0]},
                "occurrences": occ,
                "hash": None,
                "size": None,
                "status": "declared_not_fetched",
                "resolution": {
                    "method": "ref_token_in_prose",
                    "bytes_obtained": False,
                    "unresolved_reason": {
                        "code": "cross_repo_ref",
                        "detail": (
                            "branch name only; cross-repo (TensorPlatform) and not "
                            "resolvable from this worktree, so no commit id is pinned."
                        ),
                    },
                },
            }
        )
    return assets


# ------------------------------------------------------------------- checks --
REQUIRED_TOP = [
    "schema_version", "package_id", "task_type", "report_id", "source",
    "channel_probes", "assets", "claims", "verification_policy", "scope_notes",
]


def run_checks(manifest: dict, md: str) -> dict:
    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})

    missing = [k for k in REQUIRED_TOP if k not in manifest]
    add("schema_required_keys", not missing, f"missing={missing}")

    add("package_id", manifest.get("package_id") == PACKAGE_ID, manifest.get("package_id"))
    add("task_type", manifest.get("task_type") == TASK_TYPE, manifest.get("task_type"))
    add("report_id", manifest.get("report_id") == REPORT_ID, manifest.get("report_id"))

    src = manifest.get("source", {})
    h = src.get("hash", {})
    add("source_hash_matches_contract",
        h.get("value") == CONTRACT_SOURCE_HASH,
        f"contract={CONTRACT_SOURCE_HASH} manifest={h.get('value')}")
    add("source_hash_recomputed_in_run",
        h.get("recomputed_in_run") is True and h.get("matches_contract") is True,
        f"recomputed_in_run={h.get('recomputed_in_run')} matches={h.get('matches_contract')}")
    add("source_hash_matches_markdown_in_hand",
        sha256_text(md) == h.get("value"),
        f"live={sha256_text(md)}")
    add("source_chars_matches_contract",
        src.get("size", {}).get("chars") == CONTRACT_SOURCE_CHARS == len(md),
        f"contract={CONTRACT_SOURCE_CHARS} manifest={src.get('size',{}).get('chars')} live={len(md)}")

    assets = manifest.get("assets", [])
    ids = [a.get("asset_id") for a in assets]
    add("no_duplicate_ids", len(ids) == len(set(ids)), f"n={len(ids)} unique={len(set(ids))}")

    bad_loc = []
    for a in assets:
        loc = a.get("locator") or {}
        s, e, q = loc.get("char_start"), loc.get("char_end"), loc.get("quote")
        if not isinstance(s, int) or not isinstance(e, int) or not isinstance(q, str):
            bad_loc.append((a.get("asset_id"), "shape"))
            continue
        if md[s:e] != q:
            bad_loc.append((a.get("asset_id"), "slice_mismatch"))
        if q and q not in md:
            bad_loc.append((a.get("asset_id"), "quote_not_in_source"))
    add("source_locator_resolvable", not bad_loc, f"bad={bad_loc}")

    bad_occ = []
    for a in assets:
        for occ in a.get("occurrences", []) or []:
            if md[occ["char_start"]:occ["char_end"]] != occ["quote"]:
                bad_occ.append((a.get("asset_id"), occ["char_start"]))
    add("occurrence_locators_resolvable", not bad_occ, f"bad={bad_occ}")

    unresolved_no_reason = [
        a["asset_id"] for a in assets
        if a.get("status") != "registered"
        and not (a.get("resolution", {}).get("unresolved_reason") or {}).get("code")
    ]
    add("all_unresolved_have_reason_code", not unresolved_no_reason,
        f"missing={unresolved_no_reason}")

    registered_without_bytes = [
        a["asset_id"] for a in assets
        if a.get("status") == "registered"
        and not a.get("resolution", {}).get("bytes_obtained")
    ]
    add("registered_assets_have_bytes", not registered_without_bytes,
        f"bad={registered_without_bytes}")

    unresolved_claiming_bytes = [
        a["asset_id"] for a in assets
        if a.get("status") == "declared_not_fetched"
        and a.get("resolution", {}).get("bytes_obtained")
    ]
    add("declared_assets_do_not_claim_bytes", not unresolved_claiming_bytes,
        f"bad={unresolved_claiming_bytes}")

    claims = manifest.get("claims", [])
    claims_ok = isinstance(claims, list) and all(
        c.get("evidence_locator") or c.get("status") == "unresolved" for c in claims
    )
    add("all_claims_have_evidence_or_unresolved_status", claims_ok,
        f"n_claims={len(claims)}")

    blob = json.dumps(manifest, ensure_ascii=False)
    add("no_verified_marker",
        '"verified"' not in blob and "verified_by_platform" not in blob
        and not any(a.get("status") == "verified" for a in assets),
        "nothing marked verified; verification is computed by the platform gate")

    add("claims_not_forced", claims == [], f"claims={claims}")

    n_ok = sum(1 for c in checks if c["ok"])
    return {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "n_checks": len(checks),
        "n_ok": n_ok,
        "all_ok": n_ok == len(checks),
        "failed": [c for c in checks if not c["ok"]],
        "checks": checks,
    }


# -------------------------------------------------------------------- build --
def build(offline: bool) -> dict:
    if offline:
        md = SNAPSHOT.read_text(encoding="utf-8")
        token = None
        report = {
            "id": int(REPORT_ID),
            "title": CONTRACT_TITLE,
            "scenario_key": CONTRACT_SCENARIO_KEY,
            "mission_id": 1961,
            "status": "published",
            "created_at": "2026-11-02T03:38:58.558659+00:00",
            "tags": ["GSA", "Sobol", "sensitivity", "verification-debt",
                     "variance-decomposition", "ice-resistance"],
            "figures": json.loads(
                (OUT_DIR / "source_metadata.json").read_text(encoding="utf-8")
            )["figures"],
        }
        probes = json.loads(
            (OUT_DIR / "source_metadata.json").read_text(encoding="utf-8")
        )["channel_probes"]
    else:
        report = fetch_report()
        md = report["markdown"]
        figure_names = [f.get("name", "") for f in report.get("figures") or []]
        token = _token()
        probes = probe_channels(token, figure_names)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "source_metadata.json").write_text(
            json.dumps(
                {"figures": report.get("figures") or [], "channel_probes": probes},
                ensure_ascii=False, indent=2,
            ) + "\n",
            encoding="utf-8",
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SNAPSHOT.write_text(md, encoding="utf-8")

    live_hash = sha256_text(md)
    if live_hash != CONTRACT_SOURCE_HASH:
        raise SystemExit(
            f"source hash mismatch: contract={CONTRACT_SOURCE_HASH} live={live_hash}"
        )

    manifest = {
        "schema_version": "kf-asset-manifest/1.0",
        "package_id": PACKAGE_ID,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "lane": LANE,
        "contract_version": "1.0",
        "generator": "scripts/kf_wp1716_01_asset_manifest.py",
        "repro_cmd": (
            "python3 scripts/kf_wp1716_01_asset_manifest.py "
            "&& python3 scripts/kf_wp1716_01_asset_manifest.py --verify --offline"
        ),
        "determinism": {
            "wall_clock_fields_in_manifest": 0,
            "note": "no timestamp is written here; the report carries generated_at",
        },
        "source": {
            "uri": f"tensor://reports/{REPORT_ID}",
            "field": "markdown",
            "hash": {
                "algorithm": "sha256",
                "value": live_hash,
                "scope": "utf-8 bytes of the tensor_reports.markdown field",
                "recomputed_in_run": True,
                "matches_contract": live_hash == CONTRACT_SOURCE_HASH,
                "contract_value": CONTRACT_SOURCE_HASH,
            },
            "size": {"chars": len(md), "bytes": len(md.encode("utf-8"))},
            "snapshot": {
                "path": str(SNAPSHOT.relative_to(REPO_ROOT)),
                "hash": sha256_text(SNAPSHOT.read_text(encoding="utf-8")),
            },
            "report_facts": {
                "title": report.get("title"),
                "title_matches_contract": report.get("title") == CONTRACT_TITLE,
                "scenario_key": report.get("scenario_key"),
                "scenario_key_matches_contract":
                    report.get("scenario_key") == CONTRACT_SCENARIO_KEY,
                "mission_id": report.get("mission_id"),
                "status": report.get("status"),
                "created_at": report.get("created_at"),
                "tags": report.get("tags"),
            },
        },
        "channel_probes": probes,
        "assets": build_assets(md, report),
        "claims": [],
        "verification_policy": {
            "claims_marked_verified": 0,
            "note": (
                "registration only: assets are located and hash-pinned, no claim is "
                "extracted and no verification status is asserted; verification is "
                "computed by the platform gate."
            ),
        },
        "scope_notes": {
            "in_scope": [
                f"report_id {REPORT_ID} only",
                "markdown identity (sha256 + char/byte size) re-derived in-run",
                "declared figures, inline artifact paths and the producer git ref, "
                "each pinned to a verbatim locator",
            ],
            "out_of_scope": [
                "claim extraction / report type classification (classify_report_type=false)",
                "reading or writing any other report_id",
                "fetching bytes for assets with no byte channel (recorded as unresolved)",
            ],
            "not_registered_on_purpose": [
                {
                    "item": "benchmark case keys `ishigami`, `sobol_g_a_0_0.5_3_9_99`",
                    "reason": (
                        "case identifiers inside artifacts/gsa_sobol_benchmark.json, "
                        "not standalone attachments; registering them would imply a "
                        "container we do not hold"
                    ),
                },
                {
                    "item": "symbols `saltelli_sample`, `sobol_indices`, "
                            "`ice_resistance_uq.build_pce`",
                    "reason": (
                        "symbol-level pointers; the owning module paths are registered "
                        "separately, symbol-level assets need the module bytes"
                    ),
                },
            ],
        },
        "unresolved_summary": {},
    }

    ids = [a["asset_id"] for a in manifest["assets"]]
    if len(ids) != len(set(ids)):
        dup = sorted({i for i in ids if ids.count(i) > 1})
        raise SystemExit(f"duplicate asset_id: {dup}")

    counts: dict[str, int] = {}
    for a in manifest["assets"]:
        counts[a["status"]] = counts.get(a["status"], 0) + 1
    manifest["unresolved_summary"] = {
        "n_assets": len(manifest["assets"]),
        "by_status": counts,
        "reason_codes": sorted(
            {
                a["resolution"]["unresolved_reason"]["code"]
                for a in manifest["assets"]
                if a.get("status") != "registered"
            }
        ),
    }

    MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def verify(live: bool = False) -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    md = SNAPSHOT.read_text(encoding="utf-8")
    result = run_checks(manifest, md)
    if live:
        report = fetch_report()
        live_md = report["markdown"]
        token = _token()
        names = [f.get("name", "") for f in report.get("figures") or []]
        live_probes = probe_channels(token, names)
        checks = [
            {"check": "live_markdown_hash_matches_contract",
             "ok": sha256_text(live_md) == CONTRACT_SOURCE_HASH,
             "detail": sha256_text(live_md)},
            {"check": "live_markdown_equals_snapshot",
             "ok": live_md == md, "detail": f"live_chars={len(live_md)}"},
            {"check": "live_title_matches_manifest",
             "ok": report.get("title") == manifest["source"]["report_facts"]["title"],
             "detail": report.get("title")},
            {"check": "live_channel_probes_reproduce",
             "ok": [(p["path"], p["http_status"]) for p in live_probes]
                   == [(p["path"], p["http_status"]) for p in manifest["channel_probes"]],
             "detail": str([(p["path"], p["http_status"]) for p in live_probes])},
        ]
        result["checks"].extend(checks)
        result["live"] = True
        result["n_checks"] = len(result["checks"])
        result["n_ok"] = sum(1 for c in result["checks"] if c["ok"])
        result["all_ok"] = result["n_ok"] == result["n_checks"]
        result["failed"] = [c for c in result["checks"] if not c["ok"]]
    result["manifest"] = {
        "path": str(MANIFEST.relative_to(REPO_ROOT)),
        "sha256": sha256_text(MANIFEST.read_text(encoding="utf-8")),
    }
    CHECKS.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    for c in result["checks"]:
        print(("PASS " if c["ok"] else "FAIL ") + c["check"] + "  " + str(c["detail"]))
    print(f"\n{result['n_ok']}/{result['n_checks']} checks passed; all_ok={result['all_ok']}")
    return 0 if result["all_ok"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="rebuild from the on-disk snapshot instead of the API")
    ap.add_argument("--verify", action="store_true",
                    help="re-check the written manifest against the snapshot")
    ap.add_argument("--live", action="store_true",
                    help="with --verify: also re-fetch report 1716 and replay the "
                         "identity/probe checks against the live platform")
    args = ap.parse_args()

    if args.verify:
        return verify(live=args.live)
    manifest = build(args.offline)
    print(f"wrote {MANIFEST.relative_to(REPO_ROOT)} "
          f"({len(manifest['assets'])} assets, claims={len(manifest['claims'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())