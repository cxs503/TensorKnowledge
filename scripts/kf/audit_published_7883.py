#!/usr/bin/env python3
"""Independent audit of the PUBLISHED wp-7883-01 report (adversarial re-derivation).

Deliberately does not import the builder: it re-reads the platform report, re-extracts the
single json fence, and re-checks every acceptance item against both the live source markdown
and the committed files on disk.

  python3 scripts/kf/audit_published_7883.py 14687
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
REPO = Path(__file__).resolve().parents[2]
PKG_DIR = REPO / "docs" / "kf" / "wp-7883-01"
REPORT_ID = "7883"
EXPECTED_HASH = "fc4d21ec4e30740b8596ea5b2892c877444ab58e274d5d301638322ae5fd77f5"


def get(path, tok=None):
    req = urllib.request.Request(BASE + path, headers={"Authorization": "Bearer " + tok} if tok else {})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    data = json.dumps({"username": USER, "password": PASS}).encode()
    req = urllib.request.Request(BASE + "/auth/login", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())["access_token"]


def main(pub_id: str) -> int:
    tok = login()
    pub = get("/tensor/reports/%s" % pub_id, tok)
    src = get("/tensor/reports/%s" % REPORT_ID, tok)
    md_src = src["markdown"]
    md_pub = pub["markdown"]
    findings: dict[str, dict] = {}
    observations: dict[str, dict] = {}

    def rec(name, ok, detail):
        findings[name] = {"pass": bool(ok), "detail": detail}

    rec("publish_title", pub["title"] == "KF-RESULT wp-7883-01", pub["title"])
    rec("publish_tag", "kf-wp:wp-7883-01" in (pub.get("tags") or []), pub.get("tags"))
    rec("publish_scenario", pub.get("scenario_key") == "green_compliance_eedi_eexi_cii", pub.get("scenario_key"))
    rec("publish_mission", pub.get("mission_id") == 15604, pub.get("mission_id"))

    # contract wording: the kf_result envelope must be the ONLY ```json block (other, non-json fences are allowed)
    n_fence = md_pub.count("```json")
    n_close = md_pub.count("```")
    rec("single_json_fence", n_fence == 1 and n_close % 2 == 0,
        "json_fences=%d total_fences=%d (non-json fenced blocks=%d)" % (n_fence, n_close, n_close // 2 - 1))
    observations["markdown_fences"] = {"json": n_fence, "all": n_close}

    blk = md_pub.split("```json", 1)[1].split("```", 1)[0] if n_fence == 1 else ""
    try:
        env = json.loads(blk)
        rec("fence_parses", True, "keys=%s" % sorted(env))
    except Exception as e:  # noqa: BLE001
        rec("fence_parses", False, str(e))
        env = {}

    rec("envelope_ids", env.get("package_id") == "wp-7883-01" and env.get("report_id") == REPORT_ID
        and env.get("task_type") == "01-asset-registration",
        "%s/%s/%s" % (env.get("package_id"), env.get("task_type"), env.get("report_id")))

    live_hash = hashlib.sha256(md_src.encode("utf-8")).hexdigest()
    declared = (env.get("provenance") or {}).get("source_hash", "").split("sha256:")[-1]
    rec("source_hash_matches_live", live_hash == declared == EXPECTED_HASH,
        "live=%s declared=%s contract=%s" % (live_hash[:16], declared[:16], EXPECTED_HASH[:16]))

    man = (env.get("outputs") or {}).get("asset_manifest.json") or {}
    disk = json.loads((PKG_DIR / "asset_manifest.json").read_text(encoding="utf-8"))

    def semantic(m: dict) -> dict:
        """Drop build-time volatile fields so a later rebuild cannot fake a mismatch (generated_at is documented)."""
        d = {k: v for k, v in m.items() if k != "generated_at"}
        d.pop("provenance", None)
        d["provenance_stable"] = {k: v for k, v in (m.get("provenance") or {}).items()
                                  if k not in {"generated_at"}}
        return d

    rec("embedded_manifest_equals_disk", semantic(man) == semantic(disk),
        "assets_embedded=%s assets_disk=%s generated_at_embedded=%s generated_at_disk=%s"
        % (len(man.get("assets") or []), len(disk.get("assets") or []),
           man.get("generated_at"), disk.get("generated_at")))

    # locator re-resolution straight from the live markdown
    lines = md_src.split("\n")
    bad = []
    for a in man.get("assets") or []:
        loc = a.get("locator") or {}
        sch = loc.get("scheme")
        if sch == "markdown_line":
            ln, q = loc.get("line"), loc.get("quote")
            if not (isinstance(ln, int) and 1 <= ln <= len(lines) and lines[ln - 1] == q and q in md_src):
                bad.append(a.get("asset_id"))
        elif sch == "markdown_line_range":
            s, e, q = loc.get("line_start"), loc.get("line_end"), loc.get("quote")
            if not (isinstance(s, int) and isinstance(e, int) and 1 <= s <= e <= len(lines)
                    and "\n".join(lines[s - 1:e]) == q and q in md_src):
                bad.append(a.get("asset_id"))
    rec("locators_resolve_in_live_source", not bad, "unresolvable=%s" % bad)

    ids = [a.get("asset_id") for a in man.get("assets") or []]
    rec("unique_asset_ids", len(ids) == len(set(ids)) and all(ids), "n=%d unique=%d" % (len(ids), len(set(ids))))

    claims = man.get("claims")
    rec("claims_empty_no_extraction", claims == [] and env.get("claims") == [],
        "manifest_claims=%r envelope_claims=%r" % (claims, env.get("claims")))
    rec("no_verified_marks", '"verified"' not in json.dumps(env, ensure_ascii=False),
        "no 'verified' status anywhere in the envelope")

    figs = pub.get("figures") or []
    rec("figure_metadata_present", bool(figs) and all(f.get("name") and f.get("caption") for f in figs),
        [f.get("name") for f in figs])
    observations["figure_payload_retained"] = {
        "observed": any((f.get("png_base64") or "") for f in figs),
        "note": "platform returns figures[] with name+caption only; png_base64 is stripped on ingest "
                "(same shape as source report 7883), so embedded figure bytes are not hash-verifiable via the API; "
                "the authoritative copy is the repo file docs/kf/wp-7883-01/fig1_asset_coverage_map.png",
        "repo_png_sha256": hashlib.sha256((PKG_DIR / "fig1_asset_coverage_map.png").read_bytes()).hexdigest()
        if (PKG_DIR / "fig1_asset_coverage_map.png").is_file() else None,
    }

    # scope guard: this publication must not reference any other report_id
    foreign = sorted({m for m in re.findall(r"reports/(\d+)", md_pub) if m != REPORT_ID})
    rec("scope_single_report", not foreign, "foreign_report_ids=%s" % foreign)

    ok = all(f["pass"] for f in findings.values())
    out = {"published_report_id": pub_id, "source_report_id": REPORT_ID,
           "audited_at_epoch": int(__import__("time").time()),
           "published_markdown_sha256": hashlib.sha256(md_pub.encode("utf-8")).hexdigest(),
           "findings": findings, "observations": observations, "all_pass": ok}
    (PKG_DIR / "audit_published.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "14687"))