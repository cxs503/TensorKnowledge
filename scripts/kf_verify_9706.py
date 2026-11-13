"""Independent verification of work package wp-9706-01 (report 9706 asset registration).

This is the acceptance gate for the package. It re-derives everything it can from the raw
markdown instead of trusting the generator:

  valid_json                              envelope + manifest parse strictly (json.loads, no NaN/Inf)
  schema_pass                             envelope vs schemas/kf_result.v1.schema.json,
                                          manifest vs schemas/asset_manifest.wp-9706-01.schema.json
  source_locator_resolvable               every quote is a unique substring of the markdown AND
                                          md[start_char:end_char] == quote AND start_line is the
                                          line that actually contains start_char
  source_hash_matches                     sha256(markdown) == contract source_hash == envelope provenance
                                          (optionally re-fetched from the API with --from-api)
  no_duplicate_ids                        asset_id unique + envelope/manifest identity agrees
  all_claims_have_evidence_or_explicit... every claim (0 here) has an evidence locator or a status,
                                          and no claim is marked as verified

Extra invariants (beyond the contract's acceptance list):
  * resolution status is consistent with its own machine check result;
  * counts block agrees with the asset list;
  * no reference to any report other than 9706 anywhere in the deliverables.

Usage: python3 scripts/kf_verify_9706.py [--from-api]
Outputs: runs/wp-9706-01/acceptance.json, docs/wp-9706-01/acceptance.json, stdout summary
Exit: 0 all pass, 1 any failure (honest FAIL is printed, never masked).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

REPORT_ID = "9706"
PACKAGE_ID = "wp-9706-01"
TASK_TYPE = "01-asset-registration"
EXPECTED_HASH = "7d0e024b8630cd3390f5efc0c3f5abfb467e85a869c78126bbb210a1a2d13534"
EXPECTED_CHARS = 12546

RUN_DIR = pathlib.Path("runs") / PACKAGE_ID
ART_DIR = pathlib.Path("artifacts") / PACKAGE_ID
DOC_DIR = pathlib.Path("docs") / PACKAGE_ID
SCHEMA_ENVELOPE = pathlib.Path("schemas/kf_result.v1.schema.json")
SCHEMA_MANIFEST = pathlib.Path("schemas/asset_manifest.wp-9706-01.schema.json")

RESOLUTION_OK = {
    "resolved_in_source": {"resolved", "present"},
    "referenced_unresolved": {"unresolved"},
    "declared_absent": {"absent"},
}


def sha256_hex(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def strict_load(path: pathlib.Path):
    """Parse JSON strictly: reject NaN/Infinity and duplicate keys."""
    def no_const(x):
        raise ValueError(f"non-JSON constant {x} in {path}")
    def no_dup(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise ValueError(f"duplicate JSON object key in {path}: {sorted(keys)}")
        return dict(pairs)
    return json.loads(path.read_text(encoding="utf-8"),
                      parse_constant=no_const, object_pairs_hook=no_dup)


def fetch_markdown() -> bytes:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    tok = None
    if user and pwd:
        for path in ("/auth/login", "/auth/token", "/login"):
            req = urllib.request.Request(base + path,
                                         data=json.dumps({"username": user, "password": pwd}).encode(),
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.loads(r.read().decode())
                tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
                if tok:
                    break
            except Exception:
                continue
    req = urllib.request.Request(base + "/tensor/reports/" + REPORT_ID)
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.loads(r.read().decode())
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    return payload["markdown"].encode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-api", action="store_true",
                    help="also re-fetch report 9706 from the platform API and compare bytes")
    args = ap.parse_args()

    checks: list[dict] = []

    def rec(name, ok, detail=None):
        checks.append(dict(item=name, status="pass" if ok else "fail", detail=detail or {}))
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  <- " + json.dumps(detail, ensure_ascii=False)[:400]))
        return ok

    env_path = RUN_DIR / f"kf_result.{PACKAGE_ID}.json"
    man_path = ART_DIR / "asset_manifest.json"
    md_path = RUN_DIR / f"report_{REPORT_ID}.md"

    # ---- valid_json ----------------------------------------------------------------
    try:
        env = strict_load(env_path)
        man = strict_load(man_path)
        strict_load(DOC_DIR / f"kf_result.{PACKAGE_ID}.json")
        strict_load(DOC_DIR / "asset_manifest.json")
        valid_json = True
        detail = dict(files=[str(env_path), str(man_path),
                             str(DOC_DIR / f"kf_result.{PACKAGE_ID}.json"), str(DOC_DIR / "asset_manifest.json")])
    except Exception as exc:
        env = man = None
        valid_json = False
        detail = dict(error=str(exc))
    rec("valid_json", valid_json, detail)
    if not valid_json:
        return 1

    md_bytes = md_path.read_bytes()
    md = md_bytes.decode("utf-8")

    # ---- schema_pass ---------------------------------------------------------------
    schema_ok, schema_detail = True, {}
    try:
        jsonschema.validate(env, json.loads(SCHEMA_ENVELOPE.read_text(encoding="utf-8")))
        schema_detail["envelope"] = "valid vs " + str(SCHEMA_ENVELOPE)
    except Exception as exc:
        schema_ok = False
        schema_detail["envelope"] = f"{type(exc).__name__}: {exc}"
    try:
        jsonschema.validate(man, json.loads(SCHEMA_MANIFEST.read_text(encoding="utf-8")))
        schema_detail["manifest"] = "valid vs " + str(SCHEMA_MANIFEST)
    except Exception as exc:
        schema_ok = False
        schema_detail["manifest"] = f"{type(exc).__name__}: {exc}"
    rec("schema_pass", schema_ok, schema_detail)

    # ---- source_hash_matches -------------------------------------------------------
    local_hash = sha256_hex(md_bytes)
    prov_hash = (env.get("provenance") or {}).get("source_hash", "")
    contract_ok = local_hash == EXPECTED_HASH and len(md) == EXPECTED_CHARS
    prov_ok = prov_hash == "sha256:" + EXPECTED_HASH
    man_ok = man["source"]["hash"] == EXPECTED_HASH and man["source"]["chars"] == len(md)
    detail = dict(local_sha256=local_hash, contract_sha256=EXPECTED_HASH,
                  provenance_source_hash=prov_hash, chars=len(md), chars_expected=EXPECTED_CHARS,
                  manifest_hash=man["source"]["hash"], manifest_chars=man["source"]["chars"])
    api_ok = None
    if args.from_api:
        try:
            api_bytes = fetch_markdown()
            api_ok = api_bytes == md_bytes
            detail["api_refetch_sha256"] = sha256_hex(api_bytes)
            detail["api_refetch_identical_to_local"] = api_ok
        except Exception as exc:
            api_ok = False
            detail["api_refetch_error"] = f"{type(exc).__name__}: {exc}"
    rec("source_hash_matches",
        bool(contract_ok and prov_ok and man_ok and (api_ok is not False)), detail)

    # ---- identity / no_duplicate_ids -----------------------------------------------
    ids = [a["asset_id"] for a in man["assets"]]
    ident = dict(
        env_package=env.get("package_id"), man_package=man.get("package_id"),
        env_task=env.get("task_type"), man_task=man.get("task_type"),
        env_report=env.get("report_id"), man_report=man.get("report_id"),
        assets=len(ids), unique_assets=len(set(ids)),
        envelope_outputs_keys=sorted((env.get("outputs") or {}).keys()),
    )
    ident_ok = (env.get("package_id") == PACKAGE_ID == man.get("package_id")
                and env.get("task_type") == TASK_TYPE == man.get("task_type")
                and str(env.get("report_id")) == REPORT_ID == str(man.get("report_id"))
                and len(ids) == len(set(ids)) == len(man["assets"])
                and "asset_manifest.json" in (env.get("outputs") or {}))
    rec("no_duplicate_ids", ident_ok, ident)

    # ---- source_locator_resolvable -------------------------------------------------
    lines, offs, pos = [], [], 0
    for ln in md.split("\n"):
        lines.append(ln)
        offs.append(pos)
        pos += len(ln) + 1
    bad = []
    for a in man["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        problems = []
        if md.count(q) != 1:
            problems.append(f"quote_occurrences={md.count(q)}")
        if not loc["unique"]:
            problems.append("locator.unique=false")
        if loc["method"] == "document":
            if q != md or loc["start_char"] != 0 or loc["end_char"] != len(md):
                problems.append("document span != whole markdown")
        else:
            if md[loc["start_char"]:loc["end_char"]] != q:
                problems.append("md[start_char:end_char] != quote")
        # start_line must be the 1-based line containing start_char
        containing = max(i for i, o in enumerate(offs) if o <= loc["start_char"])
        if containing + 1 != loc["start_line"]:
            problems.append(f"start_line {loc['start_line']} != line containing start_char ({containing + 1})")
        if loc["end_char"] < loc["end_line"] and loc["method"] != "document":
            problems.append("end_char before end_line offset")
        if not (0 <= loc["start_char"] < loc["end_char"] <= len(md)):
            problems.append("char offsets out of range")
        if problems:
            bad.append(dict(asset_id=a["asset_id"], problems=problems))
    rec("source_locator_resolvable", not bad,
        dict(assets_checked=len(man["assets"]), failing=bad))

    # ---- all_claims_have_evidence_or_explicit_unresolved_status ---------------------
    claims = man.get("claims", []) + (env.get("claims") or [])
    claim_problems = []
    for c in claims:
        has_ev = bool(c.get("evidence")) or bool(c.get("evidence_locator"))
        has_status = c.get("status") in {"supported", "partially-supported", "unresolved", "refuted"}
        if not (has_ev or has_status):
            claim_problems.append(dict(claim_id=c.get("claim_id"), problem="no evidence and no explicit status"))
        if str(c.get("status", "")).lower() == "verified" or c.get("verified") is True:
            claim_problems.append(dict(claim_id=c.get("claim_id"), problem="claim self-marked verified"))
    rec("all_claims_have_evidence_or_explicit_unresolved_status", not claim_problems,
        dict(claims=len(claims), problems=claim_problems,
             note="claims=[] by contract (objective.classify_report_type=false, no extraction); "
                  "the item is therefore satisfied without generating any claim"))

    # ---- extra invariant: resolution status vs its own machine check ----------------
    mismatch = []
    for a in man["assets"]:
        allowed = RESOLUTION_OK[a["resolution"]]
        if a["resolution_check"]["result"] not in allowed:
            mismatch.append(dict(asset_id=a["asset_id"], resolution=a["resolution"],
                                 check_result=a["resolution_check"]["result"]))
    rec("resolution_status_consistent_with_check", not mismatch, dict(mismatching=mismatch))

    # ---- extra invariant: counts agree with the asset list --------------------------
    by_res, by_cls = {}, {}
    for a in man["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
        by_cls[a["asset_class"]] = by_cls.get(a["asset_class"], 0) + 1
    c = man["counts"]
    counts_ok = (c["assets"] == len(man["assets"]) and c["by_class"] == by_cls
                 and c["by_resolution"] == by_res
                 and c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
                 and c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
                 and c["declared_absent"] == by_res.get("declared_absent", 0))
    rec("counts_consistent", counts_ok, dict(declared=c, recomputed_by_resolution=by_res))

    # ---- extra invariant: no other report_id referenced ----------------------------
    blob = json.dumps(env, ensure_ascii=False) + json.dumps(man, ensure_ascii=False)
    import re
    refs = sorted(set(re.findall(r"tensor://reports/(\d+)", blob)))
    rec("only_report_9706_referenced", refs == [REPORT_ID], dict(report_refs=refs))

    # ---- extra invariant: not self-marked verified ---------------------------------
    vs = (env.get("provenance") or {}).get("verification_status")
    ivs = (man.get("integrity") or {}).get("verification_status")
    rec("not_self_marked_verified", vs == "not_verified" and ivs == "not_verified",
        dict(provenance_verification_status=vs, manifest_verification_status=ivs))

    # ---- extra invariant: envelope carries the manifest verbatim --------------------
    out = (env.get("outputs") or {}).get("asset_manifest.json")
    rec("envelope_outputs_match_manifest", out == man,
        dict(envelope_output_equals_file=out == man))

    # ---- extra invariant: platform-gate-style extraction of the submitted report ----
    # Mirrors ops/knowledge_factory/gates.py::extract_payload (non-greedy ```json fence) so the
    # submission channel is exercised locally instead of being assumed to work.
    import re as _re
    rep_path = DOC_DIR / f"KF-RESULT-{PACKAGE_ID}.md"
    gate_detail = dict(report=str(rep_path))
    if not rep_path.exists():
        rec("gate_style_extract_decodes_and_equals_envelope", False,
            dict(gate_detail, error="report markdown missing (run scripts/kf_report_9706.py)"))
    else:
        rep = rep_path.read_text(encoding="utf-8")
        blocks = _re.findall(r"```json\s*\n(.*?)```", rep, _re.S)
        gate_detail["json_blocks"] = len(blocks)
        ok = len(blocks) == 1
        if ok:
            try:
                decoded = json.loads(blocks[0])
                ok = decoded == env
                gate_detail["decoded_equals_envelope"] = ok
                gate_detail["backticks_left_in_block"] = blocks[0].count("`")
            except Exception as exc:
                ok = False
                gate_detail["decode_error"] = f"{type(exc).__name__}: {exc}"
        gate_detail["source_hash_matches_source_markdown"] = (
            (env.get("provenance") or {}).get("source_hash") == "sha256:" + sha256_hex(md_bytes))
        gate_detail["identity"] = dict(package_id=env.get("package_id"),
                                       report_id=env.get("report_id"),
                                       task_type_stage=str(env.get("task_type")).split("-")[0])
        ok = ok and gate_detail["source_hash_matches_source_markdown"] and \
            gate_detail["identity"] == dict(package_id=PACKAGE_ID, report_id=REPORT_ID,
                                            task_type_stage="01")
        rec("gate_style_extract_decodes_and_equals_envelope", ok, gate_detail)

    all_pass = all(ch["status"] == "pass" for ch in checks)
    acceptance = dict(
        package_id=PACKAGE_ID,
        task_type=TASK_TYPE,
        report_id=REPORT_ID,
        contract_version="1.0",
        generated_by="scripts/kf_verify_9706.py",
        from_api=bool(args.from_api),
        source=dict(uri="tensor://reports/9706", field="markdown",
                    sha256=local_hash, chars=len(md), bytes_utf8=len(md_bytes)),
        acceptance_items={ch["item"]: ch["status"] for ch in checks},
        all_pass=all_pass,
        checks=checks,
        note=("Acceptance items required by the contract are the first six entries; the remaining ones are "
              "extra invariants added by this work package. status=pass means the local check ran and held; "
              "it is NOT a platform verification stamp (verification is computed by the platform gate)."),
    )
    blob_out = json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n"
    (RUN_DIR / "acceptance.json").write_text(blob_out, encoding="utf-8")
    (DOC_DIR / "acceptance.json").write_text(blob_out, encoding="utf-8")
    print("\nall_pass =", all_pass, "| checks:", len(checks),
          "| failure:", [ch["item"] for ch in checks if ch["status"] != "pass"])
    print("acceptance:", RUN_DIR / "acceptance.json")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())