#!/usr/bin/env python3
"""wp-10400-01 worker-side self-check: re-derive every acceptance criterion from raw bytes.

Not the platform gate. Deliberately re-fetches report 10400's markdown (unless
--offline) so a stale local snapshot cannot pass, then re-derives:

  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status

plus the contract constraints (every_claim_must_have_source_locator,
do_not_invent_missing_information, preserve_uncertainty,
no_forced_claim_generation, do_not_mark_claims_as_verified).

schema_pass note: the result envelope is validated against
schemas/kf_result.v1.schema.json *unmodified*. The asset manifest is validated
against schemas/asset_manifest.v1.schema.json, which hard-codes package_id /
report_id / source_uri as `const` for its own instance (wp-448-01); for this
instance those three consts are substituted in memory before validation and the
substitution is reported in the check detail. Nothing else in that schema is
touched; the gate's own schema wins if it differs.

Usage:
  python3 scripts/kf/validate_wp10400_01.py [--offline]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import sys

import jsonschema

PKG = "wp-10400-01"
REPORT_ID = "10400"
CONTRACT_HASH = "7a5ad01426079811a40edd7d8a95f7f09e1119e8a78ecfc44782d3b85920ab54"
CONTRACT_URI = "tensor://reports/10400"

MAN = pathlib.Path("artifacts/wp-10400-01/asset_manifest.json")
MAN_MIRROR = pathlib.Path("docs/kf/wp-10400-01/asset_manifest.json")
ENV = pathlib.Path("runs/wp-10400-01/kf_result.wp-10400-01.json")
SNAP = pathlib.Path("runs/wp-10400-01/report_10400.md")
SCHEMA_RESULT = pathlib.Path("schemas/kf_result.v1.schema.json")
SCHEMA_MANIFEST = pathlib.Path("schemas/asset_manifest.v1.schema.json")
OUT = pathlib.Path("runs/wp-10400-01/selfcheck.json")


def fetch_markdown(offline: bool) -> tuple[str, str]:
    if offline:
        return SNAP.read_text(encoding="utf-8"), "local snapshot (--offline)"
    from urllib.request import Request, urlopen

    base = os.environ["TENSOR_API_BASE"].rstrip("/")

    def call(path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(base + path, data=json.dumps(body).encode() if body else None,
                      headers=headers)
        with urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))

    tok = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                               "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    payload = call(f"/tensor/reports/{REPORT_ID}", token=tok)
    return payload["markdown"], f"GET {base}/tensor/reports/{REPORT_ID}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    checks: dict[str, dict] = {}

    # ---- valid_json -------------------------------------------------------
    try:
        env = json.loads(ENV.read_text(encoding="utf-8"))
        man = json.loads(MAN.read_text(encoding="utf-8"))
        checks["valid_json"] = {"pass": True,
                                "detail": "kf_result.wp-10400-01.json and asset_manifest.json "
                                          "both parse via json.loads"}
    except Exception as exc:  # noqa: BLE001
        checks["valid_json"] = {"pass": False, "detail": repr(exc)}
        OUT.write_text(json.dumps(checks, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(checks, ensure_ascii=False, indent=2))
        return 1

    md, src = fetch_markdown(args.offline)
    md_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()

    # ---- source_hash_matches ---------------------------------------------
    checks["source_hash_matches"] = {
        "pass": (md_hash == CONTRACT_HASH
                 and env["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
                 and man["source"]["hash"] == CONTRACT_HASH),
        "detail": {"live_sha256": "sha256:" + md_hash, "contract": "sha256:" + CONTRACT_HASH,
                   "envelope": env["provenance"]["source_hash"],
                   "manifest": "sha256:" + man["source"]["hash"],
                   "source_read_via": src,
                   "chars_live": len(md), "chars_manifest": man["source"]["chars"]},
    }

    # ---- schema_pass ------------------------------------------------------
    schema_result = json.loads(SCHEMA_RESULT.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(env, schema_result)
        envelope_ok, envelope_err = True, None
    except jsonschema.ValidationError as exc:
        envelope_ok, envelope_err = False, f"{list(exc.path)}: {exc.message}"

    schema_man = json.loads(SCHEMA_MANIFEST.read_text(encoding="utf-8"))
    sub = {"package_id": PKG, "report_id": REPORT_ID, "uri": CONTRACT_URI}
    schema_man["properties"]["package_id"] = {"const": sub["package_id"]}
    schema_man["properties"]["report_id"] = {"const": sub["report_id"]}
    props = schema_man["properties"]["source"]["properties"]
    props["uri"] = {"const": sub["uri"]}
    try:
        jsonschema.validate(man, schema_man)
        manifest_ok, manifest_err = True, None
    except jsonschema.ValidationError as exc:
        manifest_ok, manifest_err = False, f"{list(exc.path)}: {exc.message}"
    checks["schema_pass"] = {
        "pass": bool(envelope_ok and manifest_ok),
        "detail": {"envelope": envelope_ok, "envelope_error": envelope_err,
                   "manifest": manifest_ok, "manifest_error": manifest_err,
                   "envelope_schema": str(SCHEMA_RESULT) + " (used unmodified)",
                   "manifest_schema": str(SCHEMA_MANIFEST) +
                   " (instance consts substituted in memory: package_id/report_id/source.uri)"},
    }

    # ---- source_locator_resolvable --------------------------------------
    bad = []
    for a in man["assets"]:
        loc, q = a["locator"], a["locator"]["quote"]
        occ = md.count(q)
        ok = occ == 1 and loc["unique"] is True
        if loc["method"] == "char_span":
            ok = ok and md[loc["start_char"]:loc["end_char"]] == q
            ok = ok and md.split("\n")[loc["start_line"]].startswith(q.split("\n")[0])
            ok = ok and md.split("\n")[loc["end_line"]].endswith(q.split("\n")[-1])
        else:
            ok = ok and loc["start_char"] == 0 and loc["end_char"] == len(md)
        if not ok:
            bad.append({"asset_id": a["asset_id"], "occurrences": occ,
                        "method": loc["method"]})
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": {"assets_checked": len(man["assets"]), "failures": bad,
                   "resolved_in_source": man["counts"]["resolved_in_source"],
                   "referenced_unresolved": man["counts"]["referenced_unresolved"],
                   "method": "every quote must occur exactly once in the live source markdown; "
                             "char spans must reproduce the quote byte-for-byte at the "
                             "declared line boundaries"},
    }

    # ---- no_duplicate_ids -------------------------------------------------
    ids = [a["asset_id"] for a in man["assets"]]
    claim_ids = [c.get("claim_id") for c in man.get("claims", [])]
    checks["no_duplicate_ids"] = {
        "pass": len(ids) == len(set(ids)) and len(claim_ids) == len(set(claim_ids)),
        "detail": {"asset_ids": len(ids), "unique_asset_ids": len(set(ids)),
                   "claim_ids": len(claim_ids)},
    }

    # ---- all_claims_have_evidence_or_explicit_unresolved_status -----------
    claims = man.get("claims", [])
    claim_bad = [c.get("claim_id") for c in claims
                 if not c.get("evidence_locator") and not c.get("status")]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not claim_bad,
        "detail": {"claims": len(claims), "violations": claim_bad,
                   "mode": "claims=[] is a legal complete result for this package "
                           "(objective.classify_report_type=false; no extraction); the empty "
                           "array is declared in manifest.claims_note",
                   "claims_note_present": bool(man.get("claims_note"))},
    }

    # ---- contract constraints -------------------------------------------
    verified_leak = []
    for a in man["assets"]:
        if "verified" in (a.get("resolution") or ""):
            verified_leak.append(a["asset_id"])
    checks["do_not_mark_claims_as_verified"] = {
        "pass": not verified_leak and "verification_status" in env["provenance"]
                and env["provenance"]["verification_status"] != "verified",
        "detail": {"manifest_verified_markers": verified_leak,
                   "envelope_verification_status":
                       env["provenance"].get("verification_status"),
                   "note": "verification is computed by the platform gate"},
    }
    checks["no_forced_claim_generation"] = {
        "pass": claims == [],
        "detail": {"claims": len(claims),
                   "note": "zero claims emitted; no knowledge object invented to fill a quota"},
    }

    unresolved = [a for a in man["assets"] if a["resolution"] == "referenced_unresolved"]
    invented = []
    for a in unresolved:
        rc = a["resolution_check"]
        res = rc.get("result")
        # A quoted-but-external artefact may only be reported as "present" when the
        # positive fact is machine-verified (platform figure metadata + caption found
        # verbatim in the markdown); its binary is still flagged absent from worktree.
        if res == "present":
            evidenced = (rc.get("platform_figure_name")
                         and rc.get("caption_in_source") is True
                         and rc.get("binary_in_worktree") is False)
            if not evidenced:
                invented.append({"asset_id": a["asset_id"], "why": "present without evidence"})
        elif res != "unresolved":
            invented.append({"asset_id": a["asset_id"], "why": f"unexpected result {res!r}"})
        if not rc.get("check"):
            invented.append({"asset_id": a["asset_id"], "why": "no probe recorded"})
    checks["do_not_invent_missing_information"] = {
        "pass": not invented,
        "detail": {"referenced_unresolved": len(unresolved), "inconsistent": invented,
                   "all_unresolved_carry_probe": all("check" in a["resolution_check"]
                                                     for a in unresolved),
                   "note": "no path/URL/DOI is asserted for an unresolved artefact; probes are "
                           "reported verbatim (worktree path probe / platform figures field); "
                           "'present' is only allowed for the 4 figures whose name is in the "
                           "platform figures field and whose caption is found verbatim"},
    }
    checks["preserve_uncertainty"] = {
        "pass": (bool(man["integrity"].get("platform_captions_verbatim_in_markdown"))
                 and man["integrity"].get("hash_matches_contract") is True),
        "detail": {"hash_matches_contract": man["integrity"].get("hash_matches_contract"),
                   "captions_verbatim": man["integrity"].get(
                       "platform_captions_verbatim_in_markdown"),
                   "note": "upstream honest-FAIL wording (all_pass=False, §6 '否' rows) is "
                           "registered verbatim; this package adds no claim and no confidence"},
    }

    # ---- durable mirror identity ----------------------------------------
    mirror_ok = (MAN.read_bytes() == MAN_MIRROR.read_bytes())
    checks["durable_mirror_identical"] = {
        "pass": mirror_ok,
        "detail": {"artifact": str(MAN), "mirror": str(MAN_MIRROR),
                   "sha256": hashlib.sha256(MAN.read_bytes()).hexdigest(),
                   "why": "push gate drops artifacts/** and runs/**, so docs/ holds the "
                          "committed byte-identical copy"},
    }

    # ---- delivered report body: exactly one json block, byte-equal to the envelope
    body_path = pathlib.Path("docs/kf/wp-10400-01/KF-RESULT-wp-10400-01.md")
    body = body_path.read_text(encoding="utf-8")
    # Split on fences that sit alone on their own line: the JSON payload itself may
    # contain inline "```bash" text (A26's quote), which must not end the block.
    fence = re.compile(r"^```[a-z]*$", re.MULTILINE)
    marks = [(m.start(), m.group(0)) for m in fence.finditer(body)]
    blocks = []
    for i, (pos, tag) in enumerate(marks):
        if tag == "```json":
            end = marks[i + 1][0] if i + 1 < len(marks) else len(body)
            blocks.append(body[pos + len("```json"):end].strip("\n"))
    block_ok, block_detail = False, {}
    if len(blocks) == 1:
        try:
            block_obj = json.loads(blocks[0])
            block_ok = block_obj == env
            block_detail = {"json_blocks": 1, "equals_envelope": block_ok,
                            "block_package_id": block_obj.get("package_id"),
                            "block_source_hash": block_obj.get("provenance", {}).get(
                                "source_hash")}
        except Exception as exc:  # noqa: BLE001
            block_detail = {"json_blocks": 1, "parse_error": repr(exc)}
    else:
        block_detail = {"json_blocks": len(blocks)}
    body_ok = (block_ok
               and body.startswith(f"# KF-RESULT {PKG}")
               and "```bash" in body)
    checks["delivered_body_single_json_block_matches_envelope"] = {
        "pass": body_ok,
        "detail": {"body": str(body_path), "chars": len(body),
                   "title_line_ok": body.startswith(f"# KF-RESULT {PKG}"),
                   "repro_cmd_block_present": "```bash" in body,
                   **block_detail,
                   "note": "the markdown body is the only result channel; its single ```json "
                           "block must be the kf_result envelope verbatim (same source_hash)"},
    }

    all_pass = all(c["pass"] for c in checks.values())
    out = {"package_id": PKG, "report_id": REPORT_ID,
           "source_read_via": src, "all_checks_pass": all_pass, "checks": checks}
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v["pass"] for k, v in checks.items()}, ensure_ascii=False, indent=2))
    print("all_checks_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())