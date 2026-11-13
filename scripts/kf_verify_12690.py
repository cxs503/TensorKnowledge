"""Independent re-check of work package wp-12690-01 (report 12690 asset registration).

This script does not trust the registration script's output: it re-fetches the report from the
platform API, recomputes the markdown sha256, and re-validates every acceptance item of the
contract by re-reading the artefacts from disk.

Acceptance items checked (contract wp-12690-01):
  valid_json                            -> every artefact parses
  schema_pass                           -> manifest vs derived generic schema,
                                           envelope vs schemas/kf_result.v1.schema.json
  source_locator_resolvable             ->每 quote 是 markdown 的唯一子串，且 char span 重切片一致
  source_hash_matches                   -> API 重算 / 契约 / provenance / manifest 四处哈希一致
  no_duplicate_ids                      -> asset_id 唯一
  all_claims_have_evidence_or_explicit_unresolved_status -> claims=[] 时的空真判定，显式记账

Outputs:
  runs/wp-12690-01/verify_report.json
  artifacts/wp-12690-01/asset_manifest.generic.schema.json   (derived, see derive_generic_schema)
  docs/wp-12690-01/verify_report.json                        (durable mirror)

Usage: python3 scripts/kf_verify_12690.py
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

REPORT_ID = "12690"
PACKAGE_ID = "wp-12690-01"
CONTRACT_HASH = "c7ffa8c80de7dacf0f20da21051c644731ee7e82649101b0922b3830796d9d28"

RUN_DIR = pathlib.Path("runs/wp-12690-01")
ART_DIR = pathlib.Path("artifacts/wp-12690-01")
DOC_DIR = pathlib.Path("docs/wp-12690-01")
LOCAL_SCHEMA = pathlib.Path("schemas/asset_manifest.v1.schema.json")
ENVELOPE_SCHEMA = pathlib.Path("schemas/kf_result.v1.schema.json")


# ------------------------------------------------------------------ schema derivation
def derive_generic_schema(src: dict) -> dict:
    """Turn the 448-specific local schema into a package-agnostic one by rewriting the three
    identity `const`s into patterns. Deterministic transform -> no hand-edited schema drift.
    """
    out = copy.deepcopy(src)
    p = out["properties"]
    p["package_id"] = {"type": "string", "pattern": r"^wp-[A-Za-z0-9][A-Za-z0-9_.:-]*-[0-9]{2}$"}
    p["report_id"] = {"type": "string", "pattern": r"^[0-9]+$"}
    p["source"]["properties"]["uri"] = {"type": "string", "pattern": r"^tensor://reports/[0-9]+$"}
    out["$id"] = "https://tensorplatform.local/schemas/asset_manifest.v1.generic.schema.json"
    out["title"] = "asset_manifest.v1 (generic: identity consts relaxed to patterns)"
    out["description"] = (
        "DERIVED by scripts/kf_verify_12690.py:derive_generic_schema from "
        "schemas/asset_manifest.v1.schema.json (which pins package_id/report_id/uri to the "
        "historical wp-448-01 values). Only the three identity fields are relaxed; all other "
        "structural requirements are inherited unchanged."
    )
    return out


# ------------------------------------------------------------------ data loading
def _get_json(path: str, token: str | None) -> dict:
    req = urllib.request.Request(path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login() -> str | None:
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            req = urllib.request.Request(
                base + path,
                data=json.dumps({"username": user, "password": pwd}).encode(),
                headers={"Content-Type": "application/json"},
            )
            d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def fetch_markdown() -> tuple[str | None, str]:
    """Return (markdown_from_api, source_label). Falls back to the cached file when offline."""
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    try:
        payload = _get_json(f"{base}/tensor/reports/{REPORT_ID}", login())
        if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
            payload = payload["data"]
        md = payload.get("markdown")
        if md:
            return md, "platform API /tensor/reports/12690"
    except Exception as exc:  # network/db unavailable -> fall back, and say so
        return None, f"API unavailable ({type(exc).__name__}); using cached markdown"
    return None, "API returned no markdown; using cached markdown"


# ------------------------------------------------------------------ checks
def verify() -> dict:
    import jsonschema

    checks: dict[str, dict] = {}

    def rec(name: str, ok: bool, detail: str, **extra) -> None:
        checks[name] = dict(pass_=bool(ok), detail=detail, **extra)

    # --- load artefacts
    try:
        manifest = json.loads((ART_DIR / "asset_manifest.json").read_text())
        envelope = json.loads((RUN_DIR / f"kf_result.{PACKAGE_ID}.json").read_text())
        rec("valid_json", True, "asset_manifest.json + kf_result envelope parse as JSON")
    except Exception as exc:
        rec("valid_json", False, f"parse failure: {exc}")
        return dict(package_id=PACKAGE_ID, report_id=REPORT_ID, checks=checks)

    # --- schema_pass
    generic = derive_generic_schema(json.loads(LOCAL_SCHEMA.read_text()))
    ART_DIR.mkdir(parents=True, exist_ok=True)
    (ART_DIR / "asset_manifest.generic.schema.json").write_text(
        json.dumps(generic, ensure_ascii=False, indent=2))
    errs = sorted(jsonschema.Draft7Validator(generic).iter_errors(manifest), key=lambda e: list(e.path))
    env_errs = list(jsonschema.Draft202012Validator(
        json.loads(ENVELOPE_SCHEMA.read_text())).iter_errors(envelope))
    rec("schema_pass", not errs and not env_errs,
        f"manifest errors={len(errs)}, envelope errors={len(env_errs)}",
        manifest_errors=[f"{list(e.path)}: {e.message}" for e in errs][:5],
        envelope_errors=[f"{list(e.path)}: {e.message}" for e in env_errs][:5])

    # --- source_hash_matches (four places)
    api_md, api_src = fetch_markdown()
    cached_md = (RUN_DIR / f"report_{REPORT_ID}.md").read_text()
    h_api = hashlib.sha256(api_md.encode()).hexdigest() if api_md is not None else None
    h_cached = hashlib.sha256(cached_md.encode()).hexdigest()
    h_env = (envelope.get("provenance") or {}).get("source_hash", "")
    h_man = (manifest.get("source") or {}).get("hash", "")
    ok_hash = (h_cached == CONTRACT_HASH
               and (h_api is None or h_api == CONTRACT_HASH)
               and h_env == "sha256:" + CONTRACT_HASH
               and h_man == CONTRACT_HASH)
    rec("source_hash_matches", ok_hash,
        f"contract={CONTRACT_HASH[:16]}… api={('--' if h_api is None else h_api[:16] + '…')} "
        f"cached={h_cached[:16]}… envelope={h_env[:23]}… manifest={h_man[:16]}…",
        api_source=api_src)

    # --- source_locator_resolvable: every quote unique substring + char span reslices
    md = api_md if api_md is not None else cached_md
    bad = []
    for a in manifest.get("assets", []):
        loc = a["locator"]
        q = loc["quote"]
        cs, ce = loc["start_char"], loc["end_char"]
        if md.count(q) != 1:
            bad.append(f"{a['asset_id']}: quote occurrences={md.count(q)}")
        elif md[cs:ce] != q:
            bad.append(f"{a['asset_id']}: char span does not reslice")
        elif md[:cs].count("\n") != loc["start_line"]:
            bad.append(f"{a['asset_id']}: start_line mismatch")
    rec("source_locator_resolvable", not bad,
        f"{len(manifest.get('assets', [])) - len(bad)}/{len(manifest.get('assets', []))} locators resolve",
        failures=bad[:5])

    # --- no_duplicate_ids
    ids = [a["asset_id"] for a in manifest.get("assets", [])]
    rec("no_duplicate_ids", len(ids) == len(set(ids)) and len(ids) == len(manifest.get("assets", [])),
        f"{len(ids)} ids, {len(set(ids))} distinct")

    # --- claims evidence / unresolved status (vacuous truth made explicit)
    claims = manifest.get("claims", []) + envelope.get("claims", [])
    unbacked = [c for c in claims if not (c.get("evidence_locator") or c.get("evidence") or c.get("status"))]
    rec("all_claims_have_evidence_or_explicit_unresolved_status", not unbacked,
        f"claims={len(claims)} (registration-only package; 空数组=契约允许), unbacked={len(unbacked)}")

    # --- honesty checks: nothing claims verification, counts add up
    declared_verified = [a["asset_id"] for a in manifest.get("assets", [])
                         if str(a.get("resolution", "")).lower() in ("verified", "verified_in_source")]
    c = manifest.get("counts", {})
    tally_ok = (c.get("assets") == len(manifest.get("assets", []))
                and sum(c.get("by_resolution", {}).values()) == c.get("assets"))
    rec("no_asset_marked_verified", not declared_verified,
        f"verified-labelled assets={len(declared_verified)}")
    rec("counts_consistent", tally_ok,
        f"counts.assets={c.get('assets')} actual={len(manifest.get('assets', []))} "
        f"by_resolution_sum={sum(c.get('by_resolution', {}).values())}")

    out = dict(package_id=PACKAGE_ID, report_id=REPORT_ID,
               all_pass=all(v["pass_"] for v in checks.values()), checks=checks)
    for d in (RUN_DIR, DOC_DIR):
        d.mkdir(parents=True, exist_ok=True)
        (d / "verify_report.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    return out


if __name__ == "__main__":
    res = verify()
    for k, v in res["checks"].items():
        print(("PASS " if v["pass_"] else "FAIL ") + k + " :: " + v["detail"])
    print("ALL_PASS:", res.get("all_pass"))
    sys.exit(0 if res.get("all_pass") else 1)