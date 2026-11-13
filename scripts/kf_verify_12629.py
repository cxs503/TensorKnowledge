"""Independent verification of produce wp-12629-01 (asset registration for report 12629).

Independence: this script does NOT reuse runs/wp-12629-01/report_12629.md. It re-fetches the report
from the platform API in-process, recomputes sha256, and re-resolves every locator in the manifest
against that fresh copy. It then schema-validates the result envelope (schemas/kf_result.v1.schema.json,
platform-side) and the manifest (schemas/asset_manifest.wp-12629-01.schema.json, package-scoped), and
checks the delivered report markdown carries exactly one ```json block equal to the envelope.

Usage: python3 scripts/kf_verify_12629.py
Output: docs/wp-12629-01/verification.json  (+ exit code 0 = all checks PASS)
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

REPORT_ID = "12629"
PACKAGE_ID = "wp-12629-01"
CONTRACT_HASH = "6cbf559cfaec918c26cf69c0081a2a3dcdceee4f7870797b35a27af8ca7e10eb"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

DOC_DIR = pathlib.Path("docs/wp-12629-01")
ART_DIR = pathlib.Path("artifacts/wp-12629-01")


def _json(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login() -> str | None:
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _json(BASE + path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_markdown() -> tuple[str, dict]:
    tok = login()
    payload = _json(BASE + "/tensor/reports/" + REPORT_ID, token=tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    return payload.get("markdown") or "", payload


def main() -> int:
    out: dict = {"package_id": PACKAGE_ID, "report_id": REPORT_ID, "checks": {}}
    C = out["checks"]

    # --- 1. independent re-fetch + hash
    md, rec = fetch_markdown()
    h = hashlib.sha256(md.encode("utf-8")).hexdigest()
    C["independent_refetch"] = {
        "source": "%s/tensor/reports/%s" % (BASE, REPORT_ID),
        "chars": len(md), "sha256_recomputed": h, "contract_hash": CONTRACT_HASH,
        "pass": h == CONTRACT_HASH and len(md) == 1899,
    }

    # --- 2. artifacts
    man = json.loads((ART_DIR / "asset_manifest.json").read_text())
    env = json.loads((pathlib.Path("runs") / PACKAGE_ID / ("kf_result.%s.json" % PACKAGE_ID)).read_text())
    C["artifacts_present"] = {
        "artifact_manifest": (ART_DIR / "asset_manifest.json").exists(),
        "docs_manifest_mirror_identical":
            (ART_DIR / "asset_manifest.json").read_bytes() == (DOC_DIR / "asset_manifest.json").read_bytes(),
        "envelope_present": True,
        "pass": (ART_DIR / "asset_manifest.json").exists()
        and (ART_DIR / "asset_manifest.json").read_bytes() == (DOC_DIR / "asset_manifest.json").read_bytes(),
    }

    # --- 3. hash field inside manifests is consistent with the independent recomputation
    C["source_hash_matches"] = {
        "manifest.source.hash": man["source"]["hash"],
        "envelope.provenance.source_hash": env["provenance"]["source_hash"],
        "pass": man["source"]["hash"] == h and env["provenance"]["source_hash"] == "sha256:" + h,
    }

    # --- 4. re-resolve every locator against the freshly fetched markdown
    bad = []
    lines = [0]
    for i, ch in enumerate(md):
        if ch == "\n":
            lines.append(i + 1)
    for a in man["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        checks = {
            "quote_equals_slice": md[s:e] == q,
            "quote_unique": md.count(q) == 1,
            "start_line_ok": md.count("\n", 0, s) + 1 == loc["start_line"],
            "end_line_ok": md.count("\n", 0, max(e - 1, s)) + 1 == loc["end_line"],
            "in_bounds": 0 <= s < e <= len(md),
        }
        if not all(checks.values()):
            bad.append({"asset_id": a["asset_id"], "failed": [k for k, v in checks.items() if not v]})
    C["source_locator_resolvable"] = {
        "assets_checked": len(man["assets"]), "failures": bad, "pass": not bad,
    }

    # --- 5. id hygiene / counts / claims policy
    ids = [a["asset_id"] for a in man["assets"]]
    C["no_duplicate_ids"] = {
        "n": len(ids), "unique": len(set(ids)) == len(ids),
        "sequential": ids == ["A%02d" % i for i in range(1, len(ids) + 1)],
        "pass": len(set(ids)) == len(ids) and ids == ["A%02d" % i for i in range(1, len(ids) + 1)],
    }
    res_counts: dict[str, int] = {}
    for a in man["assets"]:
        res_counts[a["resolution"]] = res_counts.get(a["resolution"], 0) + 1
    C["counts_consistent"] = {
        "counts.assets": man["counts"]["assets"], "len(assets)": len(man["assets"]),
        "counts.by_resolution": man["counts"]["by_resolution"], "recount": res_counts,
        "pass": man["counts"]["assets"] == len(man["assets"]) and res_counts == man["counts"]["by_resolution"],
    }
    C["claims_policy"] = {
        "claims_len": len(man["claims"]), "envelope_claims_len": len(env.get("claims", [])),
        "claims_marked_verified": man["boundaries"]["claims_marked_verified"],
        "pass": len(man["claims"]) == 0 and len(env.get("claims", [])) == 0
        and man["boundaries"]["claims_marked_verified"] == 0,
    }
    unresolved_ok = all(
        a.get("resolution_check", {}).get("check")
        for a in man["assets"] if a["resolution"] != "resolved_in_source")
    C["unresolved_items_documented"] = {
        "items": [a["asset_id"] for a in man["assets"] if a["resolution"] != "resolved_in_source"],
        "each_has_check": unresolved_ok, "pass": unresolved_ok,
    }

    # --- 6. schema validation
    import jsonschema  # noqa: PLC0415  (deliberate: schema pass is the point of this section)
    kf_schema = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text())
    man_schema = json.loads(pathlib.Path("schemas/asset_manifest.wp-12629-01.schema.json").read_text())
    errs = {}
    try:
        jsonschema.validate(env, kf_schema)
    except jsonschema.ValidationError as exc:  # pragma: no cover
        errs["kf_result.v1"] = exc.message
    try:
        jsonschema.validate(man, man_schema)
    except jsonschema.ValidationError as exc:  # pragma: no cover
        errs["asset_manifest.wp-12629-01"] = exc.message
    C["schema_pass"] = {"validated_against": ["schemas/kf_result.v1.schema.json",
                                              "schemas/asset_manifest.wp-12629-01.schema.json"],
                        "errors": errs, "pass": not errs}

    # --- 7. delivered report markdown: exactly one ```json block, equal to the envelope
    rp = DOC_DIR / ("KF-RESULT-%s.md" % PACKAGE_ID)
    text = rp.read_text() if rp.exists() else ""
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
    parsed = json.loads(blocks[0]) if len(blocks) == 1 else None
    C["report_single_json_block"] = {
        "report": str(rp), "n_json_blocks": len(blocks),
        "equals_envelope": parsed == env,
        "has_required_title": text.startswith("# KF-RESULT %s" % PACKAGE_ID) or ("KF-RESULT %s" % PACKAGE_ID) in text.split("\n")[0],
        "has_wp_tag": ("kf-wp:%s" % PACKAGE_ID) in text,
        "pass": len(blocks) == 1 and parsed == env and ("kf-wp:%s" % PACKAGE_ID) in text,
    }

    ok = all(v.get("pass") for v in C.values())
    out["all_pass"] = ok
    out["verifier"] = "scripts/kf_verify_12629.py (independent re-fetch, in-process)"
    DOC_DIR.mkdir(parents=True, exist_ok=True)
    (DOC_DIR / "verification.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    for k, v in C.items():
        print(("PASS " if v.get("pass") else "FAIL ") + k)
    print("ALL_PASS:", ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())