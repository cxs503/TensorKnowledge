#!/usr/bin/env python3
"""Independent re-verification of work package wp-14179-01 (task_type=01-asset-registration).

Nothing here trusts the register script: the source markdown is re-fetched from the
platform, re-hashed, and every locator / id / count / schema assertion is recomputed
from the raw bytes.  It also checks the deliverable report body (single ```json block
== the envelope) when that file exists.

Writes docs/kf/wp-14179-01/verification.json and prints the acceptance self-check table.
Exit code 0 only if every blocking check passes.

Usage: python3 scripts/kf_wp14179_01_verify.py
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

PACKAGE_ID = "wp-14179-01"
REPORT_ID = "14179"
CONTRACT_HASH = "2352b96c50e792447e06d9d7450f16f0b34ba7ce2cbf1bf775c3402dcee59315"
CONTRACT_CHARS = 5506
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

DOC = pathlib.Path("docs/kf/wp-14179-01")
ART = pathlib.Path("artifacts/wp-14179-01")
ENV_SCHEMA = pathlib.Path("schemas/kf_result.v1.schema.json")
MAN_SCHEMA = DOC / "asset_manifest.v1.wp-14179-01.schema.json"


def _json(url, body=None, token=None, timeout=90):
    req = urllib.request.Request(url,
                                 data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def fetch_markdown() -> tuple[str, dict]:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    d = _json(BASE + "/auth/login", {"username": u, "password": p})
    tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
    rec = _json(BASE + "/tensor/reports/" + REPORT_ID, token=tok)
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    return rec["markdown"], rec


def main() -> int:
    checks: list[dict] = []

    def add(name, ok, detail, blocking=True):
        checks.append(dict(check=name, ok=bool(ok), detail=detail, blocking=blocking))

    md, rec = fetch_markdown()
    md_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()

    result = json.loads((DOC / "kf_result.json").read_text(encoding="utf-8"))
    manifest = json.loads((ART / "asset_manifest.json").read_text(encoding="utf-8"))
    mirror = json.loads((DOC / "asset_manifest.json").read_text(encoding="utf-8"))

    # ---- acceptance: source_hash_matches -----------------------------------
    add("source_hash_matches",
        md_hash == CONTRACT_HASH == manifest["source"]["hash"]
        == result["provenance"]["source_hash"].replace("sha256:", ""),
        f"live sha256={md_hash} | contract={CONTRACT_HASH} | manifest={manifest['source']['hash']} "
        f"| envelope={result['provenance']['source_hash']}")
    add("chars_match_contract", len(md) == CONTRACT_CHARS == manifest["source"]["chars"],
        f"len(markdown)={len(md)} contract={CONTRACT_CHARS} manifest={manifest['source']['chars']}")
    add("utf8_bytes_recorded",
        manifest["source"]["bytes_utf8"] == len(md.encode("utf-8")),
        f"bytes_utf8={manifest['source']['bytes_utf8']} vs {len(md.encode('utf-8'))} "
        f"(chars {len(md)} != bytes: CJK body)")
    add("title_scenario_match",
        rec.get("title") == result["provenance"]["source_title"]
        == manifest["source"]["title"],
        f"title from live record reproduced verbatim: {rec.get('title')[:40]}…; "
        f"scenario_key={rec.get('scenario_key')}")
    add("report_id_consistent",
        manifest["report_id"] == result["report_id"] == REPORT_ID,
        f"manifest/envelope report_id == {REPORT_ID}; record.id={rec.get('id')}")
    add("mirror_byte_identical",
        (ART / "asset_manifest.json").read_bytes() == (DOC / "asset_manifest.json").read_bytes(),
        "artifacts/ copy == docs/kf/ durable mirror (sha256 "
        + hashlib.sha256((ART / "asset_manifest.json").read_bytes()).hexdigest()[:16] + "…)")

    # ---- acceptance: valid_json / schema_pass ------------------------------
    for p in (ART / "asset_manifest.json", DOC / "kf_result.json", DOC / "locator_check.json"):
        try:
            json.loads(p.read_text(encoding="utf-8"))
            add(f"valid_json[{p.name}]", True, "json.loads round-trip OK")
        except Exception as exc:
            add(f"valid_json[{p.name}]", False, str(exc))

    try:
        import jsonschema
        env_schema = json.loads(ENV_SCHEMA.read_text(encoding="utf-8"))
        man_schema = json.loads(MAN_SCHEMA.read_text(encoding="utf-8"))
        jsonschema.Draft202012Validator(env_schema).validate(result)
        add("schema_pass[kf_result.v1]", True,
            f"envelope validates against {ENV_SCHEMA} (draft 2020-12)")
        jsonschema.Draft7Validator(man_schema).validate(manifest)
        add("schema_pass[asset_manifest.v1 pinned]", True,
            f"manifest validates against {MAN_SCHEMA} (draft-07, locally pinned)")
    except ImportError:
        add("schema_pass", False, "jsonschema not installed", blocking=True)
    except Exception as exc:
        add("schema_pass", False, f"{type(exc).__name__}: {str(exc)[:300]}")

    # ---- acceptance: source_locator_resolvable -----------------------------
    bad = []
    for a in manifest["assets"]:
        q, s, e = a["locator"]["quote"], a["locator"]["start_char"], a["locator"]["end_char"]
        if md[s:e] != q:
            bad.append((a["asset_id"], "char span mismatch"))
        elif md.count(q) != 1:
            bad.append((a["asset_id"], f"quote occurs {md.count(q)}x"))
        elif a["locator"]["method"] == "char_span":
            # line numbers must agree with the characters we claim
            seg = md[:s]
            if seg.count("\n") != a["locator"]["start_line"]:
                bad.append((a["asset_id"], "start_line disagrees with start_char"))
    add("source_locator_resolvable", not bad,
        f"{len(manifest['assets'])}/{len(manifest['assets'])} locators: md[start:end]==quote, "
        f"unique, line offsets consistent; failures={bad}")

    # ---- acceptance: no_duplicate_ids --------------------------------------
    ids = [a["asset_id"] for a in manifest["assets"]]
    add("no_duplicate_ids", len(ids) == len(set(ids)),
        f"{len(ids)} asset ids, {len(set(ids))} distinct, format ok="
        f"{all(re.fullmatch(r'A[0-9]{2}', i) for i in ids)}")

    # ---- acceptance: claims policy ----------------------------------------
    claims = manifest.get("claims", [])
    env_claims = result.get("claims", [])
    serialized = json.dumps(manifest, ensure_ascii=False) + json.dumps(result, ensure_ascii=False)
    add("all_claims_have_evidence_or_explicit_unresolved_status",
        claims == [] and env_claims == [] and '"status": "verified"' not in serialized,
        "claims=[] in manifest and envelope (contract: classify_report_type=false, no extraction) "
        "-> acceptance item is vacuously satisfied; no claim carries status=verified")
    add("nothing_marked_verified",
        result["provenance"].get("verification_status") == "not_verified"
        and "verified" not in [c for c in (rec.get("tags") or [])],
        "envelope.verification_status=not_verified; verification is computed by the platform gate")
    add("boundary_respected",
        manifest["boundary"]["only_report_id"] == REPORT_ID
        and manifest["boundary"]["read_other_reports"] is False
        and manifest["boundary"]["marked_verified"] is False,
        json.dumps(manifest["boundary"], ensure_ascii=False))

    # ---- internal consistency ---------------------------------------------
    by_res = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    by_cls = {}
    for a in manifest["assets"]:
        by_cls[a["asset_class"]] = by_cls.get(a["asset_class"], 0) + 1
    c = manifest["counts"]
    add("counts_consistent",
        c["assets"] == len(manifest["assets"]) and c["by_resolution"] == by_res
        and c["by_class"] == by_cls
        and c["resolved_in_source"] == by_res.get("resolved_in_source", 0)
        and c["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
        and c["declared_absent"] == by_res.get("declared_absent", 0),
        f"assets={c['assets']} by_resolution={by_res}")
    add("every_asset_has_resolution_check",
        all(a["resolution_check"].get("result") for a in manifest["assets"]),
        f"{len(manifest['assets'])}/{len(manifest['assets'])} assets carry a machine-check result")
    add("envelope_output_is_the_manifest",
        result["outputs"]["asset_manifest.json"] == manifest,
        "outputs['asset_manifest.json'] is byte-equal (as JSON value) to artifacts/wp-14179-01/asset_manifest.json")
    add("no_invented_information",
        all((a["locator"]["quote"] in md) for a in manifest["assets"]),
        "every registered quote is a substring of the live markdown (fetched fresh in this run)")

    # ---- published report round-trip (informational) ----------------------
    pub = DOC / "published.json"
    if pub.exists():
        pj = json.loads(pub.read_text(encoding="utf-8"))
        add("published_report_roundtrip", bool(pj.get("roundtrip_identical")),
            f"report {pj.get('report_id')} stored markdown sha256={pj.get('stored_markdown_sha256', '')[:16]}… "
            f"== local body sha256; figures={pj.get('figures')}; tags contain kf-wp tag="
            f"{('kf-wp:' + PACKAGE_ID) in (pj.get('tags') or [])}", blocking=False)
    else:
        add("published_report_roundtrip", False, "published.json absent (not published yet)",
            blocking=False)

    # ---- deliverable report body ------------------------------------------
    body = DOC / "report_body.md"
    if body.exists():
        text = body.read_text(encoding="utf-8")
        blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
        ok = False
        detail = f"{len(blocks)} json block(s)"
        if len(blocks) == 1:
            try:
                ok = json.loads(blocks[0]) == result
                detail += "; the single json block equals docs/kf/wp-14179-01/kf_result.json"
            except Exception as exc:
                detail += "; parse error " + str(exc)
        add("report_body_single_json_block_equals_envelope", ok, detail)
        add("report_body_title_and_tags",
            text.startswith("# KF-RESULT " + PACKAGE_ID)
            and ("kf-wp:" + PACKAGE_ID) in text,
            "title line '# KF-RESULT wp-14179-01' + tag kf-wp:wp-14179-01 present")
    else:
        add("report_body_single_json_block_equals_envelope", False,
            "report_body.md not generated yet", blocking=False)

    out = dict(package_id=PACKAGE_ID, report_id=REPORT_ID,
               source_hash="sha256:" + md_hash, chars=len(md),
               verifier="scripts/kf_wp14179_01_verify.py",
               blocking_failures=[c["check"] for c in checks if c["blocking"] and not c["ok"]],
               all_passed=all(c["ok"] for c in checks if c["blocking"]),
               checks=checks)
    (DOC / "verification.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for c in checks:
        print(("PASS " if c["ok"] else "FAIL ") + c["check"] + " :: " + c["detail"][:220])
    print("\nall_passed:", out["all_passed"],
          "| blocking failures:", out["blocking_failures"])
    return 0 if out["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())