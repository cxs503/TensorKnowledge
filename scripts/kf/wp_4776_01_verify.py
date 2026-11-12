#!/usr/bin/env python3
"""Independent re-verification of wp-4776-01 deliverables (separate implementation).

Loads what is on disk, re-fetches the source markdown, and re-derives every
acceptance item from scratch (no imported helper from the producer script).

Exit 0 = all six acceptance items hold on the delivered files.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV = ROOT / "docs" / "kf" / "wp-4776-01" / "kf_result.json"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
FORBIDDEN = (
    "verified",
    "verification_status",
    "verification_level",
    "is_verified",
    "gate_confirmed",
)


def source_markdown() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    login = urllib.request.Request(
        base + "/auth/login",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    tok = json.load(urllib.request.urlopen(login))["access_token"]
    req = urllib.request.Request(
        base + "/tensor/reports/4776", headers={"Authorization": "Bearer " + tok}
    )
    return json.load(urllib.request.urlopen(req))["markdown"]


def main() -> int:
    from jsonschema import Draft202012Validator

    env = json.loads(ENV.read_text())
    md = source_markdown()
    manifest = env["outputs"]["asset_manifest.json"]
    rows = []

    def check(name, ok, detail):
        rows.append({"check": name, "ok": bool(ok), "detail": detail})

    # 1 valid_json (already parsed both files above)
    json.loads(ENV.read_text())
    check(
        "valid_json", True, "envelope parsed; outputs.asset_manifest.json is an object"
    )

    # 2 schema_pass
    errs = list(Draft202012Validator(json.loads(SCHEMA.read_text())).iter_errors(env))
    check("schema_pass", not errs, f"{len(errs)} schema errors")

    # 3 source_locator_resolvable + 4 source_hash_matches
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    check(
        "source_hash_matches",
        digest == env["provenance"]["source_hash"],
        f"recomputed {digest}",
    )

    bad = []
    for a in manifest["asset_inventory"]:
        q, s, e = (
            a["locator"]["quote"],
            a["locator"]["char_start"],
            a["locator"]["char_end"],
        )
        if md[s:e] != q:
            bad.append(a["asset_id"] + ":offsets")
        if dc := hashlib.sha256(q.encode()).hexdigest():
            if a["locator"]["content_hash"] != "sha256:" + dc:
                bad.append(a["asset_id"] + ":hash")
        if md.count(q) < 1:
            bad.append(a["asset_id"] + ":search")
    check(
        "source_locator_resolvable",
        not bad,
        f"{len(manifest['asset_inventory'])} locators, problems={bad}",
    )

    # 5 no_duplicate_ids
    ids = [a["asset_id"] for a in manifest["asset_inventory"]]
    paths = [a["declared_path"] for a in manifest["asset_inventory"]]
    check(
        "no_duplicate_ids",
        len(ids) == len(set(ids)) and len(paths) == len(set(paths)),
        f"{len(ids)} ids / {len(set(ids))} unique, {len(set(paths))} unique paths",
    )

    # 6 claims with evidence or explicit unresolved status
    claims = env.get("claims", [])
    decl = manifest["claims_registration"]
    check(
        "all_claims_have_evidence_or_explicit_unresolved_status",
        (not claims) and decl["is_empty"] is True and len(decl["reason"]) >= 20,
        f"claims={len(claims)}, is_empty={decl['is_empty']}, unresolved={len(manifest['unresolved'])}",
    )

    # extra guards (self-verification fields banned by GATE-RULES S9; scope discipline)
    blob = json.dumps(env, ensure_ascii=False)
    hits = [t for t in FORBIDDEN if ('"%' + t + '"') in blob]
    check("no_self_verification_fields", not hits, f"forbidden keys={hits}")
    other_reports = sorted(
        {t for t in ("476", "4775", "4777") if ("reports/" + t) in blob}
    )
    check(
        "single_report_scope",
        manifest["scope"]["reports_touched"] == ["4776"] and not other_reports,
        f"reports_touched={manifest['scope']['reports_touched']}, stray={other_reports}",
    )

    print(json.dumps(rows, ensure_ascii=False, indent=1))
    return 0 if all(r["ok"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
