#!/usr/bin/env python3
"""wp-1204-01 · 01-asset-registration · report_id=1204

Registers the *assets* of report 1204 (EX1-P1 KCS resistance blind-prediction
prereg v1).  No extraction, no verification, no claim generation:
  * source markdown is fetched live and hashed (sha256 over utf-8 bytes);
  * figures listed in the platform record are registered as metadata-only
    (the record carries name+caption, no byte payload -> no hash is claimable);
  * file/symbol/endpoint references quoted in the markdown are registered with
    a verbatim text locator, and their resolution status is probed against this
    worktree (absent => unresolved, never silently resolved);
  * MD5 anchors printed inside the markdown are registered as *declared*
    anchors; the referenced bytes are outside this package's scope, so they are
    NOT recomputed and NOT confirmed.

Usage (repro):
  TENSOR_API_BASE=... TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... \
    python3 scripts/kf/build_asset_manifest_wp1204_01.py
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

PKG = "wp-1204-01"
REPORT_ID = "1204"
TASK_TYPE = "01-asset-registration"
CONTRACT_HASH = "437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef"
SOURCE_URI = "tensor://reports/1204"
SCENARIO_KEY = "ex1_kcs_prereg"
OUT_DIRS = ["docs/kf/wp-1204-01", "artifacts/wp-1204-01"]  # docs = committed canonical, artifacts = run area
SNAP = "runs/wp-1204-01/source_1204.md"

# References that the report itself quotes (verbatim substrings are checked
# against the fetched markdown before they are written into the manifest).
# (verbatim quote in markdown, role, derived path or None, derivation note or None)
# NOTE: the report writes run_prereg.py / audit_platform_chain.py as bare file
# names; the docs/prereg/ex1_kcs/ prefix is *inferred* from the surrounding
# sentence, so the verbatim quote is kept short and the prefix is recorded as a
# derivation instead of being presented as if it were quoted.
REPO_ARTIFACTS = [
    ("docs/prereg/ex1_kcs/test_prereg.py", "pytest_judgement_suite",
     "docs/prereg/ex1_kcs/test_prereg.py", None),
    ("docs/prereg/ex1_kcs/holtrop_mennen.py", "formula_chain_implementation",
     "docs/prereg/ex1_kcs/holtrop_mennen.py", None),
    ("run_prereg.py", "prereg_generator",
     "docs/prereg/ex1_kcs/run_prereg.py",
     "bare filename in the report; directory inferred from the same step's "
     "sibling paths (docs/prereg/ex1_kcs/), not verbatim"),
    ("audit_platform_chain.py", "platform_chain_audit_script",
     "docs/prereg/ex1_kcs/audit_platform_chain.py",
     "bare filename in the report; directory inferred from the same step's "
     "sibling paths (docs/prereg/ex1_kcs/), not verbatim"),
    ("backend/data/standard_models_detailed.py", "input_parameter_source",
     "backend/data/standard_models_detailed.py", None),
    ("backend/api/resistance_advanced.py", "platform_resistance_module",
     "backend/api/resistance_advanced.py", None),
]
SYMBOLS = [
    ("calculate_holtrop_full", "function"),
    ("/api/v1/resistance/predict", "http_endpoint"),
]
HASH_ANCHORS = [
    ("44a19245db893f5eb56fa7e54fc53931", "md5", "prereg_body_bytes"),
    ("885b2c07805a413df281d23743e64856", "md5", "prereg_file"),
]


def _api(path: str, token: str | None = None, body: dict | None = None):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(base + path, data=data, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def login() -> str:
    tok = _api("/auth/login", body={
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"],
    })
    return tok["access_token"]


# Read-only cross-check root: a *separate* checkout of the ship-performance
# platform (not this package's repo, not modified).  Used only to record that a
# same-named copy exists somewhere; it never upgrades a reference to "resolved"
# because that checkout's branch/commit is unverified against report 1204.
EXTERNAL_ROOTS = [
    "/root/ship-performance-platform-incoming/ship-performance-platform",
]


def external_copy(rel_path: str) -> dict | None:
    import subprocess

    for root in EXTERNAL_ROOTS:
        cand = os.path.join(root, rel_path)
        if not os.path.isfile(cand):
            continue
        with open(cand, "rb") as fh:
            raw = fh.read()
        try:
            commit = subprocess.run(
                ["git", "-C", root, "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=20).stdout.strip() or None
            branch = subprocess.run(
                ["git", "-C", root, "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=20).stdout.strip() or None
        except Exception:  # noqa: BLE001
            commit = branch = None
        return {
            "path": cand,
            "repo_root": root,
            "commit": commit,
            "branch": branch,
            "bytes": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "used_to_resolve": False,
            "caveat": ("read-only observation in a foreign checkout; branch/commit is "
                       "not proven to be the one report 1204 was generated from, so this "
                       "does NOT resolve the reference and no content claim is made"),
        }
    return None


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build(report: dict, expected_hash: str, generated_at: str | None = None,
          emitted_at: str | None = None) -> tuple[dict, dict]:
    stamp = generated_at or _dt.datetime.now(_dt.timezone.utc).isoformat()
    emit = emitted_at or _dt.datetime.now(_dt.timezone.utc).isoformat()
    md = report["markdown"]
    digest = sha256_hex(md)
    if digest != expected_hash:
        raise SystemExit(
            f"FATAL source_hash mismatch: live={digest} contract={expected_hash}; "
            "refusing to register a manifest against unverified bytes")

    figures = report.get("figures") or []
    assets: list[dict] = []

    assets.append({
        "asset_id": "r1204:source",
        "kind": "report_markdown",
        "uri": SOURCE_URI,
        "source_field": "markdown",
        "title": report["title"],
        "chars": len(md),
        "bytes_utf8": len(md.encode("utf-8")),
        "sha256": digest,
        "locator": {"scheme": "report_field", "field": "markdown"},
        "resolution": {"status": "resolved", "scope": "platform_api",
                       "via": "GET /tensor/reports/1204"},
    })

    for i, fig in enumerate(figures):
        name = fig.get("name")
        has_payload = bool(fig.get("png_base64"))
        assets.append({
            "asset_id": f"r1204:figure:{i + 1:02d}",
            "kind": "embedded_figure",
            "uri": f"{SOURCE_URI}#figures[{i}]",
            "name": name,
            "caption": fig.get("caption"),
            "bytes": len(fig["png_base64"]) if has_payload else None,
            "sha256": None,
            "locator": {"scheme": "report_field", "field": "figures", "index": i},
            "resolution": {
                "status": "metadata_only" if not has_payload else "resolved",
                "scope": "platform_api",
                "has_payload": has_payload,
                "reason": ("report record lists this figure by name+caption only; "
                           "no png_base64 payload is stored in figures[], so no byte "
                           "hash can be computed" if not has_payload else
                           "inline png payload present"),
            },
        })

    for quote, role, derived, deriv_note in REPO_ARTIFACTS:
        if quote not in md:
            raise SystemExit(f"FATAL locator not verbatim in markdown: {quote!r}")
        present = bool(derived) and os.path.isfile(derived)
        entry = {
            "asset_id": "r1204:ref:" + re.sub(r"[^a-z0-9]+", "-", (derived or quote).lower()).strip("-"),
            "kind": "referenced_repo_artifact",
            "role_in_report": role,
            "declared_path": derived or quote,
            "path_is_verbatim": deriv_note is None,
            "uri": "tensor://reports/1204#" + (derived or quote),
            "locator": {"scheme": "text_quote", "quote": quote, "source_field": "markdown"},
            "resolution": {
                "status": "resolved" if present else "unresolved",
                "scope": "worktree",
                "checked_path": derived or quote,
                "present_in_this_worktree": present,
            },
        }
        if deriv_note:
            entry["path_derivation_note"] = deriv_note
        if present:
            with open(derived, "rb") as fh:
                raw = fh.read()
            entry["bytes"] = len(raw)
            entry["sha256"] = hashlib.sha256(raw).hexdigest()
        else:
            entry["resolution"]["reason"] = (
                "path is quoted in the report but does not exist in the "
                "TensorKnowledge checkout used for this package; the reference stays "
                "unresolved here (no content claim is made)")
            obs = external_copy(derived or quote)
            if obs:
                entry["external_copy_observed"] = obs
                entry["resolution"]["reason"] += (
                    "; a same-named file exists in a separate ship-performance-platform "
                    "checkout (see external_copy_observed) but that checkout's "
                    "branch/commit is unverified, so it is recorded as an observation, "
                    "not as a resolution")
        assets.append(entry)

    for token, kind in SYMBOLS:
        if token not in md:
            raise SystemExit(f"FATAL locator not verbatim in markdown: {token!r}")
        assets.append({
            "asset_id": "r1204:ext:" + re.sub(r"[^a-z0-9]+", "-", token.lower()).strip("-"),
            "kind": "external_dependency",
            "dependency_kind": kind,
            "name": token,
            "locator": {"scheme": "text_quote", "quote": token, "source_field": "markdown"},
            "resolution": {
                "status": "unresolved",
                "scope": "out_of_package",
                "reason": ("named in the report as an object to be audited/used; this "
                           "package only registers the reference — the service/function "
                           "was not called or inspected, so its behaviour is neither "
                           "confirmed nor refuted here"),
            },
        })

    for value, algo, target in HASH_ANCHORS:
        if value not in md:
            raise SystemExit(f"FATAL locator not verbatim in markdown: {value!r}")
        assets.append({
            "asset_id": "r1204:anchor:" + algo + ":" + value[:8],
            "kind": "declared_hash_anchor",
            "algorithm": algo,
            "value": value,
            "declared_for": target,
            "locator": {"scheme": "text_quote", "quote": value, "source_field": "markdown"},
            "resolution": {
                "status": "unresolved",
                "scope": "out_of_package",
                "recomputed": False,
                "reason": ("anchor is *declared inside the report*; the bytes it "
                           "covers (prereg body/file) are not part of report 1204's "
                           "markdown, so this package cannot recompute it — registered "
                           "as declared, not as confirmed"),
            },
        })

    ids = [a["asset_id"] for a in assets]
    if len(ids) != len(set(ids)):
        raise SystemExit("FATAL duplicate asset_id in generated manifest")

    manifest = {
        "manifest_version": "1.0",
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "objective": {"register_assets": True, "classify_report_type": False},
        "generated_at": stamp,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + digest,
            "hash_algo": "sha256",
            "hashed_bytes": "markdown encoded as utf-8",
            "source_chars": len(md),
            "source_bytes_utf8": len(md.encode("utf-8")),
            "report_title": report["title"],
            "report_scenario_key": report["scenario_key"],
            "report_mission_id": report["mission_id"],
            "report_status": report["status"],
            "report_created_at": report["created_at"],
            "report_created_by": report["created_by"],
            "report_tags": report["tags"],
            "fetched_via": "GET /api/v1/tensor/reports/1204",
            "generator": "scripts/kf/build_asset_manifest_wp1204_01.py",
            "contract_version": "1.0",
            "contract_expected_hash": expected_hash,
        },
        "resolution_status_vocabulary": {
            "resolved": "bytes located and hashed (source markdown or a file inside this worktree)",
            "unresolved": "reference parsed from the report but the target is outside this package's scope",
            "metadata_only": "platform lists the asset but stores no byte payload, so no hash is claimable",
        },
        "structure_index": {
            "note": "headings only, offsets are character positions into the markdown "
                    "string — provided as locator scaffolding for downstream 工序, "
                    "no content is extracted here",
            "headings": [],
        },
        "assets": assets,
        "counts": {
            "assets_total": len(assets),
            "resolved": sum(1 for a in assets if a["resolution"]["status"] == "resolved"),
            "unresolved": sum(1 for a in assets if a["resolution"]["status"] == "unresolved"),
            "metadata_only": sum(1 for a in assets if a["resolution"]["status"] == "metadata_only"),
        },
        "explicit_non_actions": [
            "no claim extracted (claims=[] by contract: register_assets only, "
            "no forced claim generation)",
            "no technical statement of the report was verified or refuted; the "
            "platform gate computes verification",
            "declared MD5 anchors were not recomputed (covered bytes are out of scope)",
            "figures were not downloaded or rendered (no byte payload in the record)",
        ],
    }

    for line_no, line in enumerate(md.splitlines(keepends=True)):
        if line.startswith("#"):
            manifest["structure_index"]["headings"].append({
                "level": len(line) - len(line.lstrip("#")),
                "text": line.strip("# \n"),
                "line_no": line_no + 1,
            })

    envelope = {
        "package_id": PKG,
        "task_type": TASK_TYPE,
        "report_id": REPORT_ID,
        "provenance": {
            "source_uri": SOURCE_URI,
            "source_field": "markdown",
            "source_hash": "sha256:" + digest,
            "producer": "kf-worker:wp-1204-01",
            "emitted_at": emit,
            "notes": ("01-asset-registration only: source bytes hashed live, figure "
                      "metadata indexed, quoted references probed against the "
                      "TensorKnowledge worktree. No extraction, no verification, "
                      f"claims intentionally empty. contract_expected_hash={expected_hash}"),
        },
        "outputs": {
            "asset_manifest.json": manifest,
        },
        "claims": [],
    }
    return manifest, envelope


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expected-hash", default=CONTRACT_HASH)
    ap.add_argument("--emitted-at", default=None, help="freeze envelope emitted_at")
    ap.add_argument("--generated-at", default=None,
                    help="freeze the timestamp so regeneration is byte-identical "
                         "(used to prove the committed envelope == the published one)")
    args = ap.parse_args()

    token = login()
    report = _api("/tensor/reports/1204", token=token)
    if str(report.get("id")) != REPORT_ID:
        raise SystemExit(f"FATAL wrong report returned: {report.get('id')!r}")

    md = report["markdown"]
    os.makedirs(os.path.dirname(SNAP), exist_ok=True)
    with open(SNAP, "w", encoding="utf-8") as fh:
        fh.write(md)

    manifest, envelope = build(report, args.expected_hash, args.generated_at, args.emitted_at)

    mpath = epath = None
    for out_dir in OUT_DIRS:
        os.makedirs(out_dir, exist_ok=True)
        mpath = os.path.join(out_dir, "asset_manifest.json")
        with open(mpath, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=2, sort_keys=False)
            fh.write("\n")
        epath = os.path.join(out_dir, "kf_result.json")
        with open(epath, "w", encoding="utf-8") as fh:
            json.dump(envelope, fh, ensure_ascii=False, indent=2)
            fh.write("\n")

    print(json.dumps({
        "manifest": mpath,
        "kf_result": epath,
        "source_snapshot": SNAP,
        "source_sha256": manifest["provenance"]["source_hash"],
        "counts": manifest["counts"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())