#!/usr/bin/env python3
"""KF task_type=01-asset-registration — generic source-asset registrar + verifier.

Generalised from scripts/kf/build_asset_manifest.py (which hardcoded report 542).
Nothing here is report specific: the report markdown is fetched from the platform,
its byte hash is recomputed, and every locator quote is a *programmatic slice* of
the fetched bytes (never retyped), so `quote` is a verbatim substring of the source
by construction.

Scope guard (inherited from the work-package contract): the tool touches exactly one
report_id per invocation, emits no claims, extracts nothing, and never marks anything
as verified (verification is computed by the platform gate).

Usage:
  python3 scripts/kf/register_source_assets.py \
      --package-id wp-7554-01 --report-id 7554 \
      --expected-hash d64a8ba8... --out-dir docs/kf/wp-7554-01 \
      build verify
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# ---- asset specs are supplied per report as a JSON "discovery plan" -------------
# Each entry: asset_id / asset_class / label / in_report_section / kind / uri /
# resolution / anchor (a string that MUST occur exactly once in the markdown).
# The locator span is the anchor itself; anything outside the source is impossible.

RESOLVED = "resolved_in_source"
UNRESOLVED = "referenced_unresolved"
ABSENT = "declared_absent"


# --------------------------------------------------------------- platform I/O
def _req(url, token=None, data=None):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch_report(base, user, password, report_id):
    tok = _req(base + "/auth/login",
               data=json.dumps({"username": user, "password": password}).encode())
    token = tok.get("access_token") or tok.get("token")
    if not token:
        raise SystemExit("login returned no access token")
    payload = _req(base + "/tensor/reports/%s" % report_id, token=token)
    rec = payload.get("data", payload) if isinstance(payload, dict) else payload
    md = rec.get("markdown")
    if not md:
        raise SystemExit("report %s has no markdown field" % report_id)
    return rec, md


# ------------------------------------------------------------------- locators
def locate(md, anchor, asset_id):
    n = md.count(anchor)
    if n != 1:
        raise SystemExit("anchor for %s occurs %d times (need exactly 1): %r"
                         % (asset_id, n, anchor))
    start = md.index(anchor)
    end = start + len(anchor)
    return {
        "method": "char_span",
        "start_char": start,
        "end_char": end,
        "start_line": md.count("\n", 0, start) + 1,
        "end_line": md.count("\n", 0, end) + 1,
        "quote": md[start:end],          # slice, never retyped
        "unique": md.count(md[start:end]) == 1,
    }


def document_locator(md):
    """Whole-document asset: the span is the title line so that md[start:end] == quote
    still round-trips; `covers_document`+`document_chars` carry the whole-document claim.
    Using start=0/end=len(md) with a title-line quote would break the round-trip invariant."""
    head = md.split("\n", 1)[0]
    return {
        "method": "document",
        "start_char": 0,
        "end_char": len(head),
        "start_line": 1,
        "end_line": 1,
        "quote": head,                   # slice, never retyped
        "unique": md.count(head) == 1,
        "covers_document": True,
        "document_chars": len(md),
    }


# --------------------------------------------------------------------- build
def build(report, md, spec):
    source = {
        "uri": spec["source_uri"],
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": hashlib.sha256(md.encode("utf-8")).hexdigest(),
        "chars": len(md),
        "bytes_utf8": len(md.encode("utf-8")),
        "title": report.get("title") or "",
        "scenario_key": report.get("scenario_key") or "",
        # NOTE: record only what the read path actually exposes. The report read API returns
        # {name, caption} and no payload field, so "no bytes visible" must NOT be written up as
        # "no bytes stored" (that would be an unverified claim about server-side storage).
        "platform_figures": [
            {"name": f.get("name"), "caption": f.get("caption"),
             "fields_exposed_by_read_api": sorted(f.keys()),
             "payload_field_present": any(
                 k not in ("name", "caption") and f.get(k) for k in f)}
            for f in (report.get("figures") or [])
        ],
        "platform_tags": report.get("tags") or [],
        "platform_report_meta": {
            "id": report.get("id"),
            "mission_id": report.get("mission_id"),
            "created_at": report.get("created_at"),
            "status": report.get("status"),
        },
    }

    assets = []
    for a in spec["assets"]:
        loc = document_locator(md) if a.get("method") == "document" else locate(
            md, a["anchor"], a["asset_id"])
        entry = {
            "asset_id": a["asset_id"],
            "asset_class": a["asset_class"],
            "label": a["label"],
            "in_report_section": a["in_report_section"],
            "kind": a["kind"],
            "uri": a["uri"].replace("{report_id}", spec["report_id"]),
            "locator": loc,
            "resolution": a["resolution"],
            "resolution_check": a["resolution_check"],
            "note": a["note"],
        }
        if "present_in_worktree" in a:
            entry["present_in_worktree"] = a["present_in_worktree"]
        assets.append(entry)

    by_class, by_res = {}, {RESOLVED: 0, UNRESOLVED: 0, ABSENT: 0}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] += 1

    md_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()
    manifest = {
        "schema": "asset_manifest.v1",
        "manifest_version": "1.0",
        "package_id": spec["package_id"],
        "task_type": "01-asset-registration",
        "report_id": spec["report_id"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "scripts/kf/register_source_assets.py",
        "contract_version": spec.get("contract_version", "1.0"),
        "source": source,
        "resolution_vocabulary": {
            RESOLVED: "bytes located inside this report's own markdown and re-sliced from it",
            UNRESOLVED: "reference parsed from the markdown, but the target bytes are outside this package's scope (other report / other repo / platform stores metadata only)",
            ABSENT: "the report itself declares the asset does not exist (no bytes were ever produced)",
        },
        "counts": {
            "assets": len(assets),
            "by_class": by_class,
            "by_resolution": by_res,
            "resolved_in_source": by_res[RESOLVED],
            "referenced_unresolved": by_res[UNRESOLVED],
            "declared_absent": by_res[ABSENT],
        },
        "assets": assets,
        # 01-asset-registration performs no extraction: zero claims is a complete result.
        "claims": [],
        "integrity": {
            "quote_uniqueness": "checked",
            "hash_recomputed_locally": True,
            "hash_matches_contract": md_hash == spec["expected_hash"],
        },
    }
    return manifest


# -------------------------------------------------------------------- verify
def verify(manifest, md, spec, out_dir):
    checks, failures = [], []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})
        if not ok:
            failures.append(name)

    actual_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()
    chk("source_hash_matches_contract", actual_hash == spec["expected_hash"],
        "recomputed=%s contract=%s" % (actual_hash, spec["expected_hash"]))
    manifest["integrity"]["hash_matches_contract"] = actual_hash == spec["expected_hash"]

    chk("source_chars_matches_contract", len(md) == int(spec["expected_chars"]),
        "actual=%d contract=%s" % (len(md), spec["expected_chars"]))

    bad_sub, bad_uniq, bad_span = [], [], []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if q not in md:
            bad_sub.append(a["asset_id"])
            continue
        if md.count(q) != 1 or loc["unique"] is not True:
            bad_uniq.append(a["asset_id"])
        if loc["method"] == "char_span" and md[loc["start_char"]:loc["end_char"]] != q:
            bad_span.append(a["asset_id"])
    chk("source_locator_resolvable", not bad_sub, "non-substring quotes: %s" % bad_sub)
    chk("quote_uniqueness", not bad_uniq, "non-unique quotes: %s" % bad_uniq)
    chk("locator_char_span_roundtrip", not bad_span, "span!=quote: %s" % bad_span)

    ids = [a["asset_id"] for a in manifest["assets"]]
    chk("no_duplicate_ids", len(ids) == len(set(ids)), "n=%d unique=%d" % (len(ids), len(set(ids))))

    c = manifest["counts"]
    chk("counts_consistent",
        c["assets"] == len(manifest["assets"])
        and sum(c["by_resolution"].values()) == c["assets"]
        and sum(c["by_class"].values()) == c["assets"],
        "assets=%d by_resolution=%s" % (c["assets"], c["by_resolution"]))

    claims_ok = all(
        ("evidence_locator" in cl) or (cl.get("status") in
         ("supported", "partially-supported", "unresolved", "refuted"))
        for cl in manifest["claims"])
    chk("all_claims_have_evidence_or_explicit_unresolved_status", claims_ok,
        "claims=%d (zero claims is a legal complete result for 01)" % len(manifest["claims"]))

    # schema_pass: kf_result against the canonical envelope schema, manifest against
    # the canonical asset_manifest schema re-parameterised for this package.
    import copy
    import jsonschema
    kf = json.loads((out_dir / "kf_result.json").read_text())
    kf_schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text())
    try:
        jsonschema.validate(kf, kf_schema)
        chk("kf_result_schema_pass", True, "schemas/kf_result.v1.schema.json")
    except jsonschema.ValidationError as e:
        chk("kf_result_schema_pass", False, str(e).splitlines()[0])

    base_schema = json.loads((REPO / "schemas" / "asset_manifest.v1.schema.json").read_text())
    ps = copy.deepcopy(base_schema)
    ps["$id"] = "https://tensorplatform.local/schemas/asset_manifest.v1.%s.json" % spec["package_id"]
    ps["description"] = ("Derived at build time from schemas/asset_manifest.v1.schema.json by "
                         "re-binding the package_id / report_id / source uri consts to %s. "
                         "Nothing else is changed, so the canonical shape still governs."
                         % spec["package_id"])
    ps["properties"]["package_id"] = {"const": spec["package_id"]}
    ps["properties"]["report_id"] = {"const": spec["report_id"]}
    ps["properties"]["source"]["properties"]["uri"] = {"const": spec["source_uri"]}
    (out_dir / "asset_manifest.schema.pkg.json").write_text(
        json.dumps(ps, ensure_ascii=False, indent=2) + "\n")
    try:
        jsonschema.validate(manifest, ps)
        chk("manifest_schema_pass", True, "derived from schemas/asset_manifest.v1.schema.json")
    except jsonschema.ValidationError as e:
        chk("manifest_schema_pass", False, str(e).splitlines()[0])

    out = {
        "package_id": spec["package_id"],
        "report_id": spec["report_id"],
        "verified_at": datetime.now(timezone.utc).isoformat(),
        "checks": checks,
        "failures": failures,
        "gate_note": ("These are the *worker-side* self-checks named by the contract. They are NOT "
                      "the platform verification gate; no claim in any artifact is marked verified."),
        "verdict": "self-checks-pass" if not failures else "self-checks-FAIL",
    }
    (out_dir / "verification.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--package-id", required=True)
    ap.add_argument("--report-id", required=True)
    ap.add_argument("--expected-hash", required=True)
    ap.add_argument("--expected-chars", required=True)
    ap.add_argument("--source-uri", default=None)
    ap.add_argument("--spec", required=True, help="discovery plan JSON (asset specs)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("actions", nargs="*", default=["build", "verify"])
    args = ap.parse_args()

    out_dir = (REPO / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = json.loads(Path(args.spec).read_text())
    spec.update({
        "package_id": args.package_id,
        "report_id": args.report_id,
        "expected_hash": args.expected_hash,
        "expected_chars": args.expected_chars,
        "source_uri": args.source_uri or ("tensor://reports/%s" % args.report_id),
    })

    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    report, md = fetch_report(base, os.environ["TENSOR_AGENT_USER"],
                              os.environ["TENSOR_AGENT_PASS"], args.report_id)
    # keep the exact fetched bytes for offline re-checks
    (out_dir / "source_snapshot.md").write_text(md)

    def emit(manifest):
        (out_dir / "asset_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        m_bytes = (out_dir / "asset_manifest.json").read_bytes()
        (out_dir / "asset_manifest.sha256").write_text(
            hashlib.sha256(m_bytes).hexdigest() + "\n")
        kf = {
            "package_id": spec["package_id"],
            "task_type": "01-asset-registration",
            "report_id": spec["report_id"],
            "provenance": {
                "source_uri": spec["source_uri"],
                "source_field": "markdown",
                "source_hash": "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest(),
                "hash_algo": "sha256",
                "hashed_bytes": "markdown encoded as utf-8",
                "source_chars": len(md),
                "source_bytes_utf8": len(md.encode("utf-8")),
                "fetched_via": "GET /tensor/reports/%s" % spec["report_id"],
                "generator": "scripts/kf/register_source_assets.py",
                "contract_version": spec.get("contract_version", "1.0"),
                "emitted_at": datetime.now(timezone.utc).isoformat(),
                "notes": ("Hashes and locator spans are recomputed at build time from the fetched "
                          "markdown; no quote was retyped by hand."),
            },
            "outputs": {
                "asset_manifest.json": manifest,
            },
            "claims": [],
        }
        (out_dir / "kf_result.json").write_text(
            json.dumps(kf, ensure_ascii=False, indent=2) + "\n")
        return len(m_bytes)

    if "build" in args.actions:
        manifest = build(report, md, spec)
        n = emit(manifest)
        print("built %s (manifest %d bytes, assets=%d)"
              % (out_dir / "asset_manifest.json", n, manifest["counts"]["assets"]))

    if "verify" in args.actions:
        manifest = json.loads((out_dir / "asset_manifest.json").read_text())
        before = manifest["integrity"]["hash_matches_contract"]
        res = verify(manifest, md, spec, out_dir)
        if manifest["integrity"]["hash_matches_contract"] != before:
            emit(manifest)   # keep the persisted flag and the envelope in sync
        for c in res["checks"]:
            print("[%s] %-52s %s" % (c["result"], c["check"], c["detail"][:90]))
        print("verdict:", res["verdict"])
        if res["failures"]:
            sys.exit(1)


if __name__ == "__main__":
    main()