#!/usr/bin/env python3
"""Independent re-verification of the wp-14214-01 artifacts.

Deliberately does NOT import the producer script: it re-reads the emitted files
byte-for-byte and re-derives every check, so a silent producer bug cannot pass by
agreeing with itself.

    python3 scripts/kf_wp14214_01_verify.py     # exit 0 = all checks pass
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-14214-01"
CONTRACT_HASH = "sha256:edc85090268afe8220c9108650aed655c05b017bb1bb29cdfffa382b7d2d1af9"
CONTRACT_CHARS = 6258


def main() -> int:
    checks = []

    def chk(name, ok, why):
        checks.append({"check": name, "ok": bool(ok), "why": why})

    src_bytes = (PKG / "source.md").read_bytes()
    src = src_bytes.decode("utf-8")
    digest = "sha256:" + hashlib.sha256(src_bytes).hexdigest()
    chk("source_hash_matches_contract", digest == CONTRACT_HASH, "%s" % digest)
    chk("source_chars_match_contract", len(src) == CONTRACT_CHARS, "%d" % len(src))
    chk("sha256_txt_agrees", (PKG / "sha256.txt").read_text(encoding="utf-8").strip() == digest,
        (PKG / "sha256.txt").read_text(encoding="utf-8").strip())

    man = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    res = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    loc = json.loads((PKG / "locator_check.json").read_text(encoding="utf-8"))

    # --- every asset locator resolves at its recorded offsets, uniquely
    bad = []
    for a in man["assets"]:
        q, lo, hi = a["locator"]["quote"], a["locator"]["start_char"], a["locator"]["end_char"]
        if a["locator"]["method"] == "document":
            if hi != len(src):
                bad.append(a["asset_id"])
            continue
        if src[lo:hi] != q:
            bad.append(a["asset_id"] + ":offset")
        elif src.count(q) != 1:
            bad.append(a["asset_id"] + ":not_unique")
        elif a["locator"]["start_line"] != src.count("\n", 0, lo) + 1:
            bad.append(a["asset_id"] + ":line")
    chk("all_locators_resolve_at_recorded_offsets", not bad, "bad=%s" % bad)
    chk("no_duplicate_asset_ids", len({a["asset_id"] for a in man["assets"]}) == len(man["assets"]),
        "%d ids" % len(man["assets"]))
    chk("locator_check_rows_agree_with_manifest",
        len(loc["locators"]) == len([a for a in man["assets"] if a["locator"]["method"] == "char_span"]),
        "%d vs %d" % (len(loc["locators"]),
                      len([a for a in man["assets"] if a["locator"]["method"] == "char_span"])))

    # --- observation evidence verbatim
    rec = man["source"]
    rec_text = " ".join(str(rec.get(k) or "") for k in ("title", "summary"))
    badq = []
    for o in man["integrity_observations"]:
        for ev in o["evidence"]:
            hay = src if ev["source_field"] == "markdown" else rec_text
            if ev["quote"] not in hay:
                badq.append(o["obs_id"])
    chk("observation_quotes_verbatim", not badq, "bad=%s" % badq)

    # --- envelope
    chk("envelope_package_id", res["package_id"] == "wp-14214-01", res["package_id"])
    chk("envelope_task_type", res["task_type"] == "01-asset-registration", res["task_type"])
    chk("envelope_report_id", res["report_id"] == "14214", res["report_id"])
    chk("envelope_source_hash", res["provenance"]["source_hash"] == digest,
        res["provenance"]["source_hash"])
    chk("envelope_source_field", res["provenance"]["source_field"] == "markdown",
        res["provenance"]["source_field"])
    chk("envelope_has_manifest_output", "asset_manifest.json" in res["outputs"],
        str(list(res["outputs"])))
    chk("envelope_output_equals_disk_manifest",
        res["outputs"]["asset_manifest.json"] == man, "deep-equal")
    chk("claims_empty_as_contracted", res.get("claims") == [], str(res.get("claims")))
    chk("no_verified_marking", "verified" not in json.dumps(res, ensure_ascii=False).lower()
        or man["integrity"]["nothing_marked_verified"],
        "nothing_marked_verified=%s" % man["integrity"]["nothing_marked_verified"])

    # --- report body: exactly one fenced json block, byte-equal to the envelope
    body = (PKG / "report_body.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
    chk("report_body_single_json_block", len(blocks) == 1, "%d block(s)" % len(blocks))
    title_ok = body.startswith("# KF-RESULT wp-14214-01")
    chk("report_body_title", title_ok, body.split("\n")[0])
    tag_ok = "kf-wp:wp-14214-01" in body
    chk("report_body_tag", tag_ok, "kf-wp:wp-14214-01 present" if tag_ok else "missing")
    if blocks:
        try:
            parsed = json.loads(blocks[0])
            chk("report_body_json_parses", True, "ok")
            chk("report_body_json_equals_envelope", parsed == res, "deep-equal")
        except Exception as exc:  # noqa: BLE001
            chk("report_body_json_parses", False, str(exc))
    top = ROOT / "docs" / "kf_result_wp-14214-01.md"
    chk("top_level_body_identical", top.exists() and top.read_text(encoding="utf-8") == body,
        str(top))

    ok_all = all(c["ok"] for c in checks)
    print(json.dumps({"all_pass": ok_all, "n_checks": len(checks),
                      "failures": [c for c in checks if not c["ok"]], "checks": checks},
                     ensure_ascii=False, indent=2))
    (PKG / "verify.json").write_text(json.dumps(
        {"all_pass": ok_all, "checks": checks}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
