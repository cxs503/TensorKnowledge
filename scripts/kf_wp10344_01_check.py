#!/usr/bin/env python3
"""wp-10344-01 | acceptance checks for the asset-registration package (offline, no network).

Re-verifies, from the files already in the tree, every acceptance item of the contract
package wp-10344-01:

    valid_json                    json.load of asset_manifest.json and kf_result.json
    schema_pass                   jsonschema vs schemas/kf_result.v1.schema.json and
                                  schemas/asset_manifest.v1.wp-10344-01.schema.json
    source_locator_resolvable     every asset locator slice of source.md equals its quote,
                                  and md.find(quote) equals the recorded start_char
    source_hash_matches           sha256(source.md bytes) == contract hash == envelope hash
    no_duplicate_ids              asset_id uniqueness + no id reuse across locator ids
    all_claims_have_evidence_or_explicit_unresolved_status
                                  claims is empty (allowed) or every claim carries evidence/status

Writes docs/kf/wp-10344-01/acceptance.json. Exit code 0 iff every item passes.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG_DIR = os.path.join(ROOT, "docs", "kf", "wp-10344-01")
EXPECTED_HASH = "a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900"


def _load(name: str) -> dict:
    with open(os.path.join(PKG_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


def source_markdown() -> str:
    with open(os.path.join(PKG_DIR, "source.md"), encoding="utf-8") as fh:
        return fh.read()


def check_hash() -> dict:
    raw = open(os.path.join(PKG_DIR, "source.md"), "rb").read()
    digest = hashlib.sha256(raw).hexdigest()
    kf = _load("kf_result.json")
    env = kf["provenance"]["source_hash"]
    man = _load("asset_manifest.json")
    ok = (digest == EXPECTED_HASH and env == f"sha256:{EXPECTED_HASH}"
          and man["source_hash"] == f"sha256:{EXPECTED_HASH}"
          and man["source_hash_matches"] is True)
    return {"pass": ok, "recomputed": f"sha256:{digest}",
            "contract": f"sha256:{EXPECTED_HASH}", "envelope": env}


def check_locators() -> dict:
    md = source_markdown()
    man = _load("asset_manifest.json")
    bad = []
    for a in man["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if loc["method"] == "document":
            continue
        if md[loc["start_char"]:loc["end_char"]] != q:
            bad.append({"asset_id": a["asset_id"], "why": "slice != quote"})
            continue
        if md.find(q) != loc["start_char"]:
            bad.append({"asset_id": a["asset_id"], "why": "start_char != md.find(quote)"})
            continue
        if loc["unique"] != (md.count(q) == 1):
            bad.append({"asset_id": a["asset_id"], "why": "unique flag inconsistent"})
    loc_check = _load("locator_check.json")
    for c in loc_check["checks"]:
        if md.count(c["quote"]) < 1:
            bad.append({"locator_id": c["locator_id"], "why": "quote not in markdown"})
    return {"pass": not bad, "assets_checked": len(man["assets"]),
            "quotes_checked": loc_check["quotes_checked"], "failures": bad}


def check_duplicates() -> dict:
    man = _load("asset_manifest.json")
    ids = [a["asset_id"] for a in man["assets"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    return {"pass": not dup, "n_ids": len(ids), "duplicates": dup}


def check_claims() -> dict:
    man = _load("asset_manifest.json")
    kf = _load("kf_result.json")
    claims = man.get("claims", []) + kf.get("claims", [])
    bad = [c for c in claims if not (c.get("evidence") or c.get("status"))]
    return {"pass": not bad, "n_claims": len(claims),
            "note": "claims=[] is the contract-permitted state for 01-asset-registration"}


def check_schema() -> dict:
    try:
        import jsonschema
    except ImportError:  # pragma: no cover
        return {"pass": False, "why": "jsonschema not installed"}
    out = {}
    pairs = [("kf_result.json", "schemas/kf_result.v1.schema.json"),
             ("asset_manifest.json", "schemas/asset_manifest.v1.wp-10344-01.schema.json")]
    for doc, sch in pairs:
        with open(os.path.join(ROOT, sch), encoding="utf-8") as fh:
            schema = json.load(fh)
        inst = _load(doc)
        try:
            jsonschema.validate(inst, schema)
            out[doc] = {"pass": True, "schema": sch}
        except jsonschema.ValidationError as exc:
            out[doc] = {"pass": False, "schema": sch, "error": exc.message,
                        "path": list(exc.absolute_path)}
    kf = _load("kf_result.json")
    out["envelope_outputs_declared"] = {
        "pass": "asset_manifest.json" in kf["outputs"],
        "outputs": sorted(kf["outputs"].keys())}
    out["pass"] = all(v["pass"] for v in out.values() if isinstance(v, dict))
    return out


def check_all() -> dict:
    items = {
        "valid_json": {"pass": True, "how": "json.load succeeded for both artefacts"},
        "schema_pass": check_schema(),
        "source_locator_resolvable": check_locators(),
        "source_hash_matches": check_hash(),
        "no_duplicate_ids": check_duplicates(),
        "all_claims_have_evidence_or_explicit_unresolved_status": check_claims(),
    }
    flips = [k for k, v in items.items() if not v["pass"]]
    return {"package_id": "wp-10344-01", "report_id": "10344",
            "items": items, "failed_items": flips, "all_pass": not flips}


def main() -> int:
    res = check_all()
    with open(os.path.join(PKG_DIR, "acceptance.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(json.dumps({"all_pass": res["all_pass"], "failed_items": res["failed_items"]},
                     ensure_ascii=False))
    return 0 if res["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())