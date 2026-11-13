"""Independent verifier for KF work package wp-9091-01 (task_type=01-asset-registration).

Re-derives every acceptance item from the *source markdown* and the *manifest file* instead of
trusting the generator's printout:

  valid_json                 manifest parses as JSON, and so does the kf_result envelope
  schema_pass                manifest validates against schemas/asset_manifest.v1.generic.schema.json
                             + regression: docs/wp-448-01/asset_manifest.json still validates
                               against the untouched v1 schema (no cross-package breakage)
  source_locator_resolvable  for every asset: md[start_char:end_char] == quote, quote is a unique
                             substring of md, start_line/end_line agree with the char span
  source_hash_matches        sha256(local markdown) == manifest hash == contract hash
                             (and envelope provenance.source_hash == 'sha256:' + that hash)
  no_duplicate_ids           unique asset_id (and unique claim_id when claims are non-empty)
  claims_evidence            every claim carries evidence or an explicit status; nothing is
                             marked verified
  scope_isolation            manifest.report_id == '9091' and every quote stays inside this report

Nothing here writes to the platform or to any other report; it only reads the local artifacts.

Usage: python3 scripts/kf_verify_wp9091_01.py
Outputs: runs/wp-9091-01/verification.json, docs/wp-9091-01/verification.json, exit 0/1.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

REPORT_ID = "9091"
PACKAGE_ID = "wp-9091-01"
CONTRACT_HASH = "89c2a8f978e2915cb079337441118458e78017bcb4a177c38d8c8a00cc8c6f17"
CONTRACT_CHARS = 10060

RUN_DIR = pathlib.Path("runs/wp-9091-01")
DOC = pathlib.Path("docs/wp-9091-01")
ART = pathlib.Path("artifacts/wp-9091-01/asset_manifest.json")


def pick(*cands):
    """First existing path: artifacts/runs are stripped by the push filter, docs/ is not."""
    for c in cands:
        if pathlib.Path(c).exists():
            return pathlib.Path(c)
    raise SystemExit("none of %s exists" % (cands,))
SCHEMA = pathlib.Path("schemas/asset_manifest.v1.generic.schema.json")
SCHEMA_V1 = pathlib.Path("schemas/asset_manifest.v1.schema.json")
M448 = pathlib.Path("docs/wp-448-01/asset_manifest.json")
ENVELOPE = RUN_DIR / "kf_result.wp-9091-01.json"

checks = []


def rec(name, ok, detail=None, status=None):
    checks.append(dict(name=name, status=status or ("pass" if ok else "fail"), ok=bool(ok), detail=detail))
    return ok


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main() -> int:
    src_md = pick(RUN_DIR / ("report_%s.md" % REPORT_ID), DOC / ("report_%s.md" % REPORT_ID))
    manifest_path = pick(pathlib.Path("artifacts/wp-9091-01/asset_manifest.json"),
                         DOC / "asset_manifest.json")
    env_path = pick(RUN_DIR / "kf_result.wp-9091-01.json", DOC / "kf_result.wp-9091-01.json")
    md_bytes = src_md.read_bytes()
    md = md_bytes.decode()
    lines = md.split("\n")
    offs, pos = [], 0
    for ln in lines:
        offs.append(pos)
        pos += len(ln) + 1

    # ---------- C1 valid_json ----------
    try:
        manifest = json.loads(manifest_path.read_text())
        env = json.loads(env_path.read_text())
        rec("valid_json", True, {"manifest": str(manifest_path), "envelope": str(env_path)})
    except Exception as exc:
        rec("valid_json", False, "%s" % exc)
        return finish()

    # ---------- C2 schema_pass ----------
    try:
        import jsonschema
        jsonschema.validate(manifest, json.loads(SCHEMA.read_text()))
        rec("schema_pass", True, {"schema": str(SCHEMA),
                                  "note": "report-agnostic generalisation of v1 (pattern instead of const)"})
    except Exception as exc:
        rec("schema_pass", False, "%s: %s" % (type(exc).__name__, exc))
    # regression: the v1 schema is untouched and still accepts the other package's manifest
    if M448.exists():
        try:
            import jsonschema
            jsonschema.validate(json.loads(M448.read_text()), json.loads(SCHEMA_V1.read_text()))
            rec("schema_pass.regression_v1", True,
                {"note": "docs/wp-448-01/asset_manifest.json still validates against the untouched "
                         "schemas/asset_manifest.v1.schema.json (consts intact)"})
        except Exception as exc:
            rec("schema_pass.regression_v1", False, str(exc))

    # ---------- C3 source_locator_resolvable ----------
    bad = []
    for a in manifest.get("assets", []):
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if md[s:e] != q:
            bad.append((a["asset_id"], "char span does not reproduce quote"))
            continue
        if md.count(q) != 1:
            bad.append((a["asset_id"], "quote occurs %d times" % md.count(q)))
            continue
        if not loc["unique"]:
            bad.append((a["asset_id"], "locator.unique flag is false"))
            continue
        s_line = md.count("\n", 0, s)
        e_line = md.count("\n", 0, e - 1)
        if (s_line, e_line) != (loc["start_line"], loc["end_line"]):
            bad.append((a["asset_id"], "line span mismatch (%s,%s) vs (%s,%s)"
                        % (s_line, e_line, loc["start_line"], loc["end_line"])))
            continue
        if loc["method"] == "document" and not (s == 0 and e == len(md)):
            bad.append((a["asset_id"], "document method but span is not the whole markdown"))
    rec("source_locator_resolvable", not bad,
        {"assets_checked": len(manifest.get("assets", [])), "failures": bad})

    # ---------- C4 source_hash_matches ----------
    h = sha(md_bytes)
    ok = (h == manifest["source"]["hash"] == CONTRACT_HASH
          and env["provenance"]["source_hash"] == "sha256:" + h
          and manifest["source"]["chars"] == len(md) == CONTRACT_CHARS
          and manifest["source"]["bytes_utf8"] == len(md_bytes))
    rec("source_hash_matches", ok, {"local_sha256": h, "contract": CONTRACT_HASH,
                                    "manifest": manifest["source"]["hash"],
                                    "envelope": env["provenance"]["source_hash"],
                                    "chars": len(md), "bytes_utf8": len(md_bytes)})

    # ---------- C5 no_duplicate_ids ----------
    ids = [a["asset_id"] for a in manifest.get("assets", [])]
    cids = [c.get("claim_id") for c in manifest.get("claims", [])]
    rec("no_duplicate_ids", len(ids) == len(set(ids)) and len(cids) == len(set(cids)),
        {"assets": len(ids), "unique_assets": len(set(ids)), "claims": len(cids)})

    # ---------- C6 claims have evidence or explicit status ----------
    problems = []
    for c in manifest.get("claims", []):
        if not (c.get("evidence_locator") or c.get("status") or c.get("evidence")):
            problems.append((c.get("claim_id"), "neither evidence nor status"))
        if str(c.get("status", "")).lower() in ("verified", "confirmed"):
            problems.append((c.get("claim_id"), "claim marked verified by a 01 package"))
    env_verified = str(env["provenance"].get("verification_status")) == "not_verified"
    rec("claims_evidence_or_status", not problems and env_verified,
        {"claims": len(manifest.get("claims", [])),
         "note": "claims are allowed to be empty for task_type=01 (no extraction); "
                 "provenance.verification_status=not_verified so nothing is self-declared verified",
         "problems": problems})

    # ---------- C7 scope isolation ----------
    foreign = [a["asset_id"] for a in manifest.get("assets", [])
               if a["locator"]["end_char"] > len(md)]
    rec("scope_isolation", manifest["report_id"] == REPORT_ID and not foreign,
        {"report_id": manifest["report_id"], "source_uri": manifest["source"]["uri"],
         "out_of_source_spans": foreign})

    # ---------- summary ----------
    by_class, by_res = {}, {}
    for a in manifest["assets"]:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    out = dict(
        package_id=PACKAGE_ID, task_type=manifest["task_type"], report_id=REPORT_ID,
        verifier="scripts/kf_verify_wp9091_01.py",
        manifest_sha256=sha(manifest_path.read_bytes()),
        source_sha256=h,
        source_chars=len(md), source_bytes_utf8=len(md_bytes),
        counts=dict(assets=len(manifest["assets"]), by_class=by_class, by_resolution=by_res),
        checks=checks,
        acceptance=dict(
            valid_json=all(c["ok"] for c in checks if c["name"] == "valid_json"),
            schema_pass=all(c["ok"] for c in checks if c["name"].startswith("schema_pass")),
            source_locator_resolvable=all(c["ok"] for c in checks if c["name"] == "source_locator_resolvable"),
            source_hash_matches=all(c["ok"] for c in checks if c["name"] == "source_hash_matches"),
            no_duplicate_ids=all(c["ok"] for c in checks if c["name"] == "no_duplicate_ids"),
            all_claims_have_evidence_or_explicit_unresolved_status=all(
                c["ok"] for c in checks if c["name"] == "claims_evidence_or_status"),
        ),
        all_pass=all(c["ok"] for c in checks),
        verification_status="not_verified",
        note="本文件是本工序自检记录；正式 verification 由平台门计算，本工序不自标 verified",
    )
    blob = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if RUN_DIR.exists():
        (RUN_DIR / "verification.json").write_text(blob)
    DOC.mkdir(parents=True, exist_ok=True)
    (DOC / "verification.json").write_text(blob)
    for c in checks:
        print("%-32s %s  %s" % (c["name"], c["status"].upper(),
                                "" if c["status"] == "pass" else json.dumps(c["detail"], ensure_ascii=False)[:300]))
    print("all_pass:", out["all_pass"], "| assets:", len(manifest["assets"]),
          "| by_resolution:", json.dumps(by_res, ensure_ascii=False))
    return 0 if out["all_pass"] else 1


def finish() -> int:
    print(json.dumps(checks, ensure_ascii=False, indent=2))
    return 1


if __name__ == "__main__":
    sys.exit(main())