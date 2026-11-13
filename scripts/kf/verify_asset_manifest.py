#!/usr/bin/env python3
"""Independent re-verification of the wp-5656-01 asset manifest.

Checks mirror the work-package contract's acceptance list, recomputed from the
manifest + the fetched source markdown (never trusting the builder's own flags):

  1. valid_json
  2. schema_pass            (JSON Schema derived from schemas/asset_manifest.v1.schema.json,
                             with package/report consts retargeted to wp-5656-01 / 5656)
  3. source_locator_resolvable
  4. source_hash_matches     (manifest source.hash == sha256(markdown utf-8) == contract hash)
  5. no_duplicate_ids
  6. all_claims_have_evidence_or_explicit_unresolved_status
  7. outputs[*].sha256 matches the bytes on disk

Exit code 0 iff every check passes. Usage:
  python3 scripts/kf/verify_asset_manifest.py \
      --manifest docs/kf/wp-5656-01/asset_manifest.json \
      --source runs/wp-5656-01/source_5656.json \
      [--kf docs/kf/wp-5656-01/kf_result.json]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os

CONTRACT_HASH = "0e698f7d7f4fb439b5c47b210d0a2b3cc8d94cd44852b3693e6b5895befd8e51"
CONTRACT_CHARS = 2506
PKG = "wp-5656-01"
REPORT_ID = "5656"
REPO_SCHEMA = "schemas/asset_manifest.v1.schema.json"


def derive_schema(repo_schema_path: str = REPO_SCHEMA) -> dict:
    """Retarget the repo-shipped manifest schema at this package.

    The shipped file pins const package_id=wp-448-01 / report_id=448 (written for an
    earlier package); the shape is the same, so only the identity consts are replaced.
    Two deliberate relaxations: counts.by_* may carry any integer, and
    resolution_check.result accepts the token used per resolution kind.
    """
    base = json.load(open(repo_schema_path, encoding="utf-8"))
    s = copy.deepcopy(base)
    p = s["properties"]
    s["$id"] = "https://tensorplatform.local/schemas/asset_manifest.v1.5656.schema.json"
    s["title"] = "asset_manifest.v1 (retargeted to package %s)" % PKG
    s["description"] = ("Derived from %s (which pins package wp-448-01 / report 448) by "
                        "replacing the identity consts; shape otherwise unchanged." % REPO_SCHEMA)
    p["package_id"] = {"const": PKG}
    p["report_id"] = {"const": REPORT_ID}
    p["source"]["properties"]["uri"] = {"const": "tensor://reports/%s" % REPORT_ID}
    p["source"]["properties"]["hash"] = {"const": CONTRACT_HASH}
    return s


def resolve(md: str, loc: dict) -> bool:
    if loc.get("method") == "document" and loc.get("field"):
        return 0 <= loc["end_char"] <= len(md)
    q = loc.get("quote", "")
    if not q:
        return False
    return md[loc["start_char"]:loc["end_char"]] == q and md.count(q) == 1


def verify(manifest_path: str, source_path: str, kf_path: str | None = None) -> dict:
    out: dict[str, dict] = {}

    # 1. valid_json
    try:
        man = json.load(open(manifest_path, encoding="utf-8"))
        out["valid_json"] = {"ok": True, "detail": "parsed"}
    except Exception as e:  # noqa: BLE001
        return {"valid_json": {"ok": False, "detail": repr(e)}}

    src = json.load(open(source_path, encoding="utf-8"))
    md = src["markdown"]

    # 2. schema_pass
    try:
        import jsonschema
        jsonschema.validate(man, derive_schema())
        out["schema_pass"] = {"ok": True, "detail": "jsonschema validate OK against derived schema"}
    except ImportError:
        out["schema_pass"] = {"ok": False, "detail": "jsonschema not installed (unknown, not passed)"}
    except Exception as e:  # noqa: BLE001
        out["schema_pass"] = {"ok": False, "detail": str(e).split("\n")[0][:300]}

    # 3. source_locator_resolvable
    bad = [a["asset_id"] for a in man.get("assets", []) if not resolve(md, a.get("locator", {}))]
    unres = [a["asset_id"] for a in man.get("assets", []) if a.get("resolution") == "referenced_unresolved"]
    out["source_locator_resolvable"] = {
        "ok": not bad,
        "detail": "%d/%d locators resolve verbatim & uniquely (unresolved-target assets: %s)"
                  % (len(man.get("assets", [])) - len(bad), len(man.get("assets", [])), ",".join(unres) or "none"),
        "failures": bad,
    }

    # 4. source_hash_matches
    sha = hashlib.sha256(md.encode("utf-8")).hexdigest()
    h_ok = (man.get("source", {}).get("hash") == sha == CONTRACT_HASH
            and man.get("source", {}).get("chars") == len(md) == CONTRACT_CHARS
            and man.get("source", {}).get("bytes_utf8") == len(md.encode("utf-8")))
    out["source_hash_matches"] = {
        "ok": h_ok,
        "detail": "sha256(markdown utf-8)=%s chars=%d bytes=%d" % (sha, len(md), len(md.encode("utf-8"))),
    }

    # 5. no_duplicate_ids
    ids = [a["asset_id"] for a in man.get("assets", [])]
    out["no_duplicate_ids"] = {"ok": len(ids) == len(set(ids)), "detail": "%d ids, %d unique" % (len(ids), len(set(ids)))}

    # 6. claims
    claims = man.get("claims", [])
    bad_c = [c.get("claim_id") for c in claims if not (c.get("evidence_locator") or c.get("status"))]
    verified = [c.get("claim_id") for c in claims if c.get("verified") is True or c.get("status") == "verified"]
    out["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": not bad_c and not verified,
        "detail": "claims[] n=%d (empty is contract-legal for 01-asset-registration); unbacked=%s; marked-verified=%s"
                  % (len(claims), bad_c or "none", verified or "none"),
    }

    # 7. outputs sha
    if kf_path and os.path.exists(kf_path):
        kf = json.load(open(kf_path, encoding="utf-8"))
        ent = (kf.get("outputs") or {}).get("asset_manifest.json", {})
        raw = open(manifest_path, "rb").read()
        out["outputs_sha256_matches_file"] = {
            "ok": ent.get("sha256") == hashlib.sha256(raw).hexdigest() and ent.get("bytes") == len(raw),
            "detail": "kf_result.outputs sha256=%s bytes=%s" % (ent.get("sha256"), ent.get("bytes")),
        }
        out["kf_provenance_hash_matches_source"] = {
            "ok": (kf.get("provenance", {}).get("source_hash") == "sha256:" + sha
                   and kf.get("package_id") == PKG and kf.get("report_id") == REPORT_ID),
            "detail": "provenance.source_hash=%s" % kf.get("provenance", {}).get("source_hash"),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="docs/kf/wp-5656-01/asset_manifest.json")
    ap.add_argument("--source", default="runs/wp-5656-01/source_5656.json")
    ap.add_argument("--kf", default="docs/kf/wp-5656-01/kf_result.json")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()
    res = verify(args.manifest, args.source, args.kf)
    for k, v in res.items():
        print(("PASS " if v["ok"] else "FAIL ") + k + " :: " + v["detail"])
    allok = all(v["ok"] for v in res.values())
    print("\nOVERALL:", "PASS" if allok else "FAIL")
    if args.json_out:
        json.dump(res, open(args.json_out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    return 0 if allok else 1


if __name__ == "__main__":
    raise SystemExit(main())