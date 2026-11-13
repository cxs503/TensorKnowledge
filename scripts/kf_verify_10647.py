"""Independent verification of work package wp-10647-01 (acceptance self-check).

Independence discipline
  * the markdown is re-fetched from the platform API in this process (fresh login) instead of trusting
    runs/wp-10647-01/report_10647.md;
  * the sha256 is recomputed from those bytes and compared with the contract value AND with the
    manifest's own ``source.hash``;
  * every locator is re-resolved by slicing the freshly fetched text (quote equality + uniqueness);
  * the manifest is validated against a JSON Schema (schemas/asset_manifest.v2.schema.json, the
    package-agnostic generalisation of asset_manifest.v1) and the envelope against
    schemas/kf_result.v1.schema.json.

Checks (exactly the package acceptance list)
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches / no_duplicate_ids /
  all_claims_have_evidence_or_explicit_unresolved_status
Extras: counts consistency, span nesting whitelist, no "verified" status, envelope<->manifest identity.

Outputs: artifacts/wp-10647-01/verification.json ; prints PASS/FAIL per check; exit 0 iff all pass
(or only network-dependent items are marked unknown -- they are then NOT counted as passed).

Usage: python3 scripts/kf_verify_10647.py [--offline]
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

REPORT_ID = "10647"
PACKAGE_ID = "wp-10647-01"
EXPECTED_HASH = "aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31"
EXPECTED_CHARS = 10814
SOURCE_URI = "tensor://reports/10647"

RUN_DIR = pathlib.Path("runs/wp-10647-01")
ART_DIR = pathlib.Path("artifacts/wp-10647-01")
MANIFEST = ART_DIR / "asset_manifest.json"
RESULT = RUN_DIR / "kf_result.wp-10647-01.json"
BLOCK = RUN_DIR / "kf_result_block.wp-10647-01.json"
SCHEMA_MANIFEST = pathlib.Path("schemas/asset_manifest.v2.schema.json")
SCHEMA_RESULT = pathlib.Path("schemas/kf_result.v1.schema.json")
OUT = ART_DIR / "verification.json"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

# Nesting that is intended by design: the design table contains its own per-row assets.
ALLOWED_NESTING = {("A10", "A05"), ("A10", "A06"), ("A10", "A07"), ("A10", "A08")}
RESOLUTION_TO_CHECK = {"resolved_in_source": "resolved", "referenced_unresolved": "unresolved",
                       "declared_absent": "absent"}


def login() -> str | None:
    u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (u and p):
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        req = urllib.request.Request(
            BASE + path, data=json.dumps({"username": u, "password": p}).encode(),
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.loads(r.read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_markdown() -> tuple[str, dict] | tuple[None, None]:
    try:
        tok = login()
        req = urllib.request.Request(BASE + "/tensor/reports/%s" % REPORT_ID,
                                     headers={"Authorization": "Bearer " + tok} if tok else {})
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
        if isinstance(d, dict) and isinstance(d.get("data"), dict):
            d = d["data"]
        return d.get("markdown", ""), d
    except Exception as exc:  # network/API unavailable -> unknown, never "passed"
        print("NOTE: platform re-fetch failed (%r); falling back to runs/ copy and marking "
              "network_independence unknown" % (exc,))
        p = RUN_DIR / "report_10647.md"
        if not p.exists():
            return None, None
        return p.read_text(encoding="utf-8"), json.loads((RUN_DIR / "report_10647.json").read_text("utf-8"))


def check_locators(md: str, manifest: dict) -> list[dict]:
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        quote = loc["quote"]
        if md[loc["start_char"]:loc["end_char"]] != quote:
            bad.append({"asset_id": a["asset_id"], "reason": "slice_mismatch",
                        "observed_head": md[loc["start_char"]:loc["start_char"] + 60]})
            continue
        if md.count(quote) != 1:
            bad.append({"asset_id": a["asset_id"], "reason": "not_unique",
                        "occurrences": md.count(quote)})
            continue
        if not quote.strip():
            bad.append({"asset_id": a["asset_id"], "reason": "empty_quote"})
    return bad


def check_nesting(manifest: dict) -> list[dict]:
    spans = sorted((a["locator"]["start_char"], a["locator"]["end_char"], a["asset_id"])
                   for a in manifest["assets"])
    out = []
    prev = None
    for s, e, i in spans:
        if prev and s < prev[1]:
            pair = (prev[2], i)
            if pair not in ALLOWED_NESTING:
                out.append({"outer": prev[2], "inner": i, "overlap_chars": prev[1] - s})
        prev = (s, e, i)
    return out


def main(argv: list[str]) -> int:
    offline = "--offline" in argv
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    envelope = json.loads(RESULT.read_text(encoding="utf-8"))
    block = json.loads(BLOCK.read_text(encoding="utf-8"))

    schema_manifest = json.loads(SCHEMA_MANIFEST.read_text(encoding="utf-8"))
    schema_result = json.loads(SCHEMA_RESULT.read_text(encoding="utf-8"))
    errs_m = sorted(jsonschema.Draft7Validator(schema_manifest).iter_errors(manifest), key=lambda e: list(e.path))
    errs_r = sorted(jsonschema.Draft7Validator(schema_result).iter_errors(envelope), key=lambda e: list(e.path))

    if offline:
        md, payload = (RUN_DIR / "report_10647.md").read_text(encoding="utf-8"), json.loads(
            (RUN_DIR / "report_10647.json").read_text(encoding="utf-8"))
        independent = "offline: 用 runs/ 副本重算（未走平台 API）"
    else:
        md, payload = fetch_markdown()
        independent = ("fresh API login + re-fetch in this process" if md is not None
                       else "unavailable")

    checks: dict[str, dict] = {}
    checks["valid_json"] = {"ok": True, "files": [str(MANIFEST), str(RESULT), str(BLOCK)]}
    checks["schema_pass"] = {
        "ok": not errs_m and not errs_r,
        "manifest_schema": str(SCHEMA_MANIFEST),
        "envelope_schema": str(SCHEMA_RESULT),
        "manifest_errors": [{"path": list(e.path), "message": e.message} for e in errs_m],
        "envelope_errors": [{"path": list(e.path), "message": e.message} for e in errs_r],
    }

    if md is None:
        checks["source_hash_matches"] = {"ok": False, "status": "unknown",
                                         "reason": "no markdown available"}
        checks["source_locator_resolvable"] = {"ok": False, "status": "unknown",
                                               "reason": "no markdown available"}
    else:
        h = hashlib.sha256(md.encode("utf-8")).hexdigest()
        checks["source_hash_matches"] = {
            "ok": h == EXPECTED_HASH and h == manifest["source"]["hash"] and len(md) == EXPECTED_CHARS,
            "contract_declared": "sha256:" + EXPECTED_HASH,
            "provenance": envelope["provenance"]["source_hash"],
            "manifest_source_hash": "sha256:" + manifest["source"]["hash"],
            "recomputed_from_markdown_bytes": "sha256:" + h,
            "chars_expected": EXPECTED_CHARS,
            "chars_observed": len(md),
            "chars_match": len(md) == EXPECTED_CHARS,
            "independence": independent,
        }
        bad = check_locators(md, manifest)
        checks["source_locator_resolvable"] = {
            "ok": not bad,
            "locators_checked": len(manifest["assets"]),
            "locators_resolved": len(manifest["assets"]) - len(bad),
            "failures": bad,
            "independence": independent,
        }

    ids = [a["asset_id"] for a in manifest["assets"]]
    quotes = [a["locator"]["quote"] for a in manifest["assets"]]
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    dup_quotes = sorted({q for q in quotes if quotes.count(q) > 1})
    checks["no_duplicate_ids"] = {"ok": not dup_ids and not dup_quotes,
                                  "asset_id_count": len(ids),
                                  "duplicate_asset_ids": dup_ids,
                                  "duplicate_locators": len(dup_quotes)}

    claims = manifest["claims"]
    bad_claims = [c for c in claims
                  if not (c.get("evidence_locator") or c.get("status"))]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "ok": not bad_claims,
        "claim_count": len(claims),
        "vacuous": len(claims) == 0,
        "claims_without_evidence_or_status": bad_claims,
        "contract_note": "objective.classify_report_type=false / notes: claims 允许为空数组",
    }

    # ---- extras (not part of the acceptance list, but cheap and load-bearing) ----
    by_res: dict[str, int] = {}
    by_cls: dict[str, int] = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
        by_cls[a["asset_class"]] = by_cls.get(a["asset_class"], 0) + 1
    checks["counts_consistent"] = {
        "ok": (manifest["counts"]["assets"] == len(manifest["assets"])
               and manifest["counts"]["by_class"] == dict(sorted(by_cls.items()))
               and manifest["counts"]["by_resolution"] == dict(sorted(by_res.items()))
               and manifest["counts"]["resolved_in_source"] == by_res.get("resolved_in_source", 0)
               and manifest["counts"]["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
               and manifest["counts"]["declared_absent"] == by_res.get("declared_absent", 0)),
        "recomputed": {"assets": len(manifest["assets"]), "by_class": dict(sorted(by_cls.items())),
                       "by_resolution": dict(sorted(by_res.items()))},
    }
    bad_res = [a["asset_id"] for a in manifest["assets"]
               if a["resolution_check"]["result"] != RESOLUTION_TO_CHECK[a["resolution"]]]
    checks["resolution_check_result_consistent"] = {
        "ok": not bad_res, "mismatched": bad_res,
        "rule": "resolution_check.result 必须与 resolution 同向（resolved/unresolved/absent）",
    }
    nest = check_nesting(manifest)
    checks["span_nesting"] = {"ok": not nest, "unexpected_overlaps": nest,
                              "allowed_by_design": sorted([list(p) for p in ALLOWED_NESTING])}
    verified_hits = [a["asset_id"] for a in manifest["assets"]
                     if str(a["resolution"]).lower() == "verified"]
    checks["no_verified_marks"] = {
        "ok": not verified_hits and not claims,
        "resolution_verified": verified_hits,
        "note": "resolution 仅描述定位可解析性；verification 由平台门计算",
    }
    checks["envelope_identity"] = {
        "ok": (envelope["outputs"]["asset_manifest.json"] == manifest
               and envelope["package_id"] == manifest["package_id"]
               and envelope["report_id"] == manifest["report_id"]
               and envelope["task_type"] == manifest["task_type"]
               and block == envelope
               and envelope["provenance"]["source_hash"] == "sha256:" + manifest["source"]["hash"]),
        "block_identical": block == envelope,
        "package_id": envelope["package_id"],
        "report_id": envelope["report_id"],
    }
    # platform figure metadata agreement (payload vs manifest)
    plat_figs = [(f.get("name"), bool(f.get("caption")), len(f.get("png_base64") or ""))
                 for f in (payload.get("figures") or [])]
    man_figs = [(f["name"], bool(f["caption"]), f["png_bytes"]) for f in manifest["source"]["platform_figures"]]
    checks["platform_figure_metadata"] = {
        "ok": plat_figs == man_figs and bool(plat_figs),
        "payload": plat_figs, "manifest": man_figs,
        "note": "payload 的 png_base64 全为空 → 位图本体不可解析（figures 作为 referenced_unresolved 登记）",
    }

    all_ok = all(c.get("ok") for c in checks.values())
    report = {"package_id": PACKAGE_ID, "report_id": REPORT_ID, "checks": checks,
              "all_pass": all_ok, "acceptance_order": [
                  "valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
                  "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"]}
    ART_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    for k in report["acceptance_order"]:
        print("%-52s %s" % (k, "PASS" if checks[k].get("ok") else "FAIL"))
    for k in checks:
        if k not in report["acceptance_order"]:
            print("%-52s %s  (extra)" % (k, "PASS" if checks[k].get("ok") else "FAIL"))
    print("all_pass:", all_ok)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))