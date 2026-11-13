#!/usr/bin/env python3
"""Independent verifier for wp-12044-01 (01-asset-registration, report 12044).

Re-does the acceptance checks from scratch (it does not trust the builder's printout):

  1. source.md sha256 == contract source_hash, and (with --online) == platform GET again
  2. every asset locator quote is a verbatim, unique substring with matching offsets
  3. asset ids unique, resolution statuses in the allowed enum
  4. asset_manifest.json digest equals the envelope's artifact_sha256 and artifact_bytes
  5. kf_result.json validates against schemas/kf_result.v1.schema.json
  6. report_body.md contains exactly one ```json block, it parses, and equals kf_result.json
  7. nothing claims verification (no "verified" truth flag by the producer)

Exit code 0 = all checks pass. Usage:
    python3 scripts/kf_wp12044_01_verify.py [--online]
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys

import jsonschema

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-12044-01"
SCHEMA = ROOT / "schemas" / "kf_result.v1.schema.json"
EXPECTED = "74cbbb52b6682ff4bb865490e1b4cce8511d023ed1a48afa19a9f2d22a0220b6"
ALLOWED_RES = {"resolved_in_source", "referenced_unresolved", "declared_absent"}

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def main() -> int:
    md = (PKG / "source.md").read_text(encoding="utf-8")
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    body = (PKG / "report_body.md").read_text(encoding="utf-8")

    # 1. hash
    h = hashlib.sha256(md.encode()).hexdigest()
    check("hash/local_matches_contract", h == EXPECTED, h)
    check("hash/manifest_field", manifest["source"]["hash"] == h, manifest["source"]["hash"])
    check("hash/envelope_field", result["provenance"]["source_hash"] == "sha256:" + h,
          result["provenance"]["source_hash"])
    check("hash/chars_bytes", (manifest["source"]["chars"], manifest["source"]["bytes_utf8"])
          == (len(md), len(md.encode())), f"{len(md)}/{len(md.encode())}")

    if "--online" in sys.argv:
        import urllib.request

        base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
        req = urllib.request.Request(
            base + "/auth/login",
            data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                             "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            tok = json.loads(r.read().decode())
        if isinstance(tok.get("data"), dict):
            tok = tok["data"]
        req = urllib.request.Request(base + "/tensor/reports/12044",
                                     headers={"Authorization": "Bearer " + tok.get("access_token")
                                              or tok.get("token")})
        with urllib.request.urlopen(req, timeout=60) as r:
            live = json.loads(r.read().decode())
        if isinstance(live.get("data"), dict):
            live = live["data"]
        live_md = live.get("markdown") or ""
        check("hash/platform_refetch_equal",
              hashlib.sha256(live_md.encode()).hexdigest() == EXPECTED,
              f"live chars={len(live_md)}")

    # 2/3. locators + ids
    ids = []
    for a in manifest["assets"]:
        ids.append(a["asset_id"])
        loc = a["locator"]
        q = loc["quote"]
        inside = md[loc["start_char"]:loc["end_char"]] == q
        uniq = md.count(q) == 1
        check(f"locator/{a['asset_id']}_verbatim_and_unique", inside and uniq,
              f"occ={md.count(q)} inside={inside} span={loc['start_char']}-{loc['end_char']}")
        check(f"locator/{a['asset_id']}_resolution_enum", a["resolution"] in ALLOWED_RES,
              a["resolution"])
        check(f"locator/{a['asset_id']}_check_row", a["resolution_check"]["result"] in
              {"resolved", "unresolved", "absent", "present"}, a["resolution_check"]["result"])
        if a["asset_id"] == "A04":
            check("figure/A04_unresolved_honest",
                  a["resolution"] == "referenced_unresolved"
                  and a["resolution_check"]["result"] == "unresolved",
                  str(a["resolution_check"].get("figures_endpoint_status")))
    check("ids/no_duplicates", len(ids) == len(set(ids)), ",".join(ids))
    check("counts/consistent",
          manifest["counts"]["assets"] == len(manifest["assets"]) == 4,
          str(manifest["counts"]["assets"]))

    # 4. artifact digest: file == envelope field == field in the published json block
    a1 = (PKG / "asset_manifest.json").read_bytes()
    a1_hash = hashlib.sha256(a1).hexdigest()
    check("artifact/envelope_sha",
          result["outputs"]["asset_manifest.json"]["artifact_sha256"] == a1_hash,
          "envelope vs file")
    check("artifact/envelope_bytes",
          result["outputs"]["asset_manifest.json"]["artifact_bytes"] == len(a1),
          str(len(a1)))

    # 5. schema
    try:
        jsonschema.validate(result, json.loads(SCHEMA.read_text(encoding="utf-8")))
        check("schema/kf_result_v1", True, "jsonschema.validate ok")
    except jsonschema.ValidationError as exc:
        check("schema/kf_result_v1", False, exc.message)

    # 6. single json block == kf_result.json
    blocks = re.findall(r"```json\s*\n(.*?)```", body, flags=re.S)
    check("body/exactly_one_json_block", len(blocks) == 1, f"n={len(blocks)}")
    if len(blocks) == 1:
        try:
            parsed = json.loads(blocks[0])
            check("body/json_block_equals_kf_result", parsed == result, "parsed == kf_result.json")
        except json.JSONDecodeError as exc:
            check("body/json_block_equals_kf_result", False, f"JSONDecodeError: {exc}")
    check("body/title", body.lstrip().startswith("# KF-RESULT wp-12044-01"), body.splitlines()[0])
    # tags live on the platform record, not in the body: read the publish receipt
    receipt_path = PKG / "publish_receipt.json"
    if receipt_path.exists():
        rc = json.loads(receipt_path.read_text(encoding="utf-8"))
        check("publish/tag_present", "kf-wp:wp-12044-01" in (rc.get("tags") or []),
              ",".join(rc.get("tags") or []))
        check("publish/report_created", bool(rc.get("created_report_id")),
              "created_report_id=%s" % rc.get("created_report_id"))
    else:
        check("publish/tag_present", False, "publish_receipt.json missing (report not published)")

    # figure digest must equal the manifest-computed digest in figures.json
    fj = PKG / "figures.json"
    if fj.exists():
        meta = json.loads(fj.read_text(encoding="utf-8"))[0]
        png = PKG / meta["figure"]
        check("figure/digest_matches",
              png.exists() and hashlib.sha256(png.read_bytes()).hexdigest() == meta["sha256"],
              meta["figure"])
        check("figure/caption_len_ok", len(meta["caption"]) <= 300, str(len(meta["caption"])))

    # 6b. the published report must carry exactly this body (needs --online)
    if "--online" in sys.argv:
        rc = json.loads((PKG / "publish_receipt.json").read_text(encoding="utf-8"))
        base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
        req = urllib.request.Request(
            base + "/auth/login",
            data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                             "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
            headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=60) as r:
            tok = json.loads(r.read().decode())
        if isinstance(tok.get("data"), dict):
            tok = tok["data"]
        t = tok.get("access_token") or tok.get("token")
        req = urllib.request.Request(base + "/tensor/reports/" + str(rc["created_report_id"]),
                                     headers={"Authorization": "Bearer " + t})
        with urllib.request.urlopen(req, timeout=60) as r:
            pub = json.loads(r.read().decode())
        if isinstance(pub.get("data"), dict):
            pub = pub["data"]
        check("publish/body_matches_published", (pub.get("markdown") or "") == body,
              "report %s" % rc["created_report_id"])

    # 7. no self-verified claim
    flat = json.dumps(result, ensure_ascii=False)
    check("honesty/not_verified",
          "not_verified" in flat and '"verified": true' not in flat.replace(" ", ""),
          "verification_status=not_verified")

    bad = [r for r in results if not r[1]]
    for name, ok, detail in results:
        print(("PASS " if ok else "FAIL ") + name + (("  | " + detail) if detail else ""))
    print(f"\n{len(results) - len(bad)}/{len(results)} checks passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())