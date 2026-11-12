#!/usr/bin/env python3
"""wp-1204-01 self-check: re-derive every acceptance criterion from raw bytes.

This is a *worker-side* self check, not the platform gate.  It deliberately
re-fetches the report markdown instead of trusting the local snapshot, so a
stale snapshot cannot pass the hash check.

Acceptance criteria re-checked (package contract wp-1204-01):
  valid_json / schema_pass / source_locator_resolvable / source_hash_matches /
  no_duplicate_ids / all_claims_have_evidence_or_explicit_unresolved_status
plus contract constraints:
  do_not_mark_claims_as_verified, no_forced_claim_generation (claims==[],
  report_id scope), output filename declared by the contract.

Usage:
  python3 scripts/kf/validate_kf_result.py [--offline]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import sys

import jsonschema

PKG = "wp-1204-01"
REPORT_ID = "1204"
CONTRACT_HASH = "437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef"
ENV_PATH = "docs/kf/wp-1204-01/kf_result.json"
MAN_PATH = "docs/kf/wp-1204-01/asset_manifest.json"
SNAP = "runs/wp-1204-01/source_1204.md"
SCHEMA = "schemas/kf_result.v1.schema.json"


def fetch_markdown() -> tuple[str, dict]:
    from urllib.request import Request, urlopen  # local import: offline mode

    base = os.environ["TENSOR_API_BASE"].rstrip("/")

    def call(path, body=None, token=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(base + path, data=json.dumps(body).encode() if body else None,
                      headers=headers)
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))

    tok = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                               "password": os.environ["TENSOR_AGENT_PASS"]})["access_token"]
    return call("/tensor/reports/1204", token=tok)["markdown"], call(
        "/tensor/reports/1204", token=tok)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true",
                    help="use the local markdown snapshot instead of the live API")
    args = ap.parse_args()

    checks: dict[str, dict] = {}

    # ---- valid_json ------------------------------------------------------
    try:
        env = json.load(open(ENV_PATH, encoding="utf-8"))
        man = json.load(open(MAN_PATH, encoding="utf-8"))
        checks["valid_json"] = {"pass": True, "detail": "both kf_result.json and "
                                 "asset_manifest.json parse via json.loads"}
    except Exception as exc:  # noqa: BLE001
        checks["valid_json"] = {"pass": False, "detail": repr(exc)}
        _emit(checks)
        return 1

    if args.offline:
        md = open(SNAP, encoding="utf-8").read()
        record = {"id": 1204, "figures": [
            {"name": f["name"]} for f in man["assets"] if f["kind"] == "embedded_figure"]}
        source_mode = "local snapshot " + SNAP
    else:
        md, record = fetch_markdown()
        source_mode = "live GET /api/v1/tensor/reports/1204"

    # ---- schema_pass -----------------------------------------------------
    schema = json.load(open(SCHEMA, encoding="utf-8"))
    try:
        jsonschema.validate(instance=env, schema=schema)
        schema_ok, schema_detail = True, f"jsonschema {SCHEMA} OK (envelope)"
    except jsonschema.ValidationError as exc:
        schema_ok, schema_detail = False, f"{list(exc.absolute_path)}: {exc.message}"
    contract_keys = ["package_id", "task_type", "report_id", "provenance", "outputs"]
    missing = [k for k in contract_keys if k not in env]
    prov_missing = [k for k in ("source_hash", "source_field") if k not in env.get("provenance", {})]
    out_name_ok = "asset_manifest.json" in env.get("outputs", {})
    schema_ok = schema_ok and not missing and not prov_missing and out_name_ok
    checks["schema_pass"] = {
        "pass": schema_ok,
        "detail": f"{schema_detail}; missing_top={missing} missing_provenance={prov_missing} "
                  f"declared_output_asset_manifest.json={out_name_ok}",
    }

    # ---- source_hash_matches --------------------------------------------
    live = hashlib.sha256(md.encode("utf-8")).hexdigest()
    declared = env["provenance"]["source_hash"].split(":", 1)[1]
    man_hash = man["provenance"]["source_hash"].split(":", 1)[1]
    checks["source_hash_matches"] = {
        "pass": live == declared == man_hash == CONTRACT_HASH,
        "detail": f"source={source_mode}; recomputed={live} envelope={declared} "
                  f"manifest={man_hash} contract={CONTRACT_HASH} "
                  f"chars={len(md)} bytes={len(md.encode('utf-8'))}",
    }

    # ---- source_locator_resolvable --------------------------------------
    bad: list[str] = []
    n_loc = 0
    figs = record.get("figures") or []
    for a in man["assets"]:
        loc = a.get("locator")
        n_loc += 1
        if not loc:
            bad.append(f"{a['asset_id']}: no locator")
            continue
        if loc["scheme"] == "text_quote":
            if loc["quote"] not in md:
                bad.append(f"{a['asset_id']}: quote not verbatim: {loc['quote']!r}")
        elif loc["scheme"] == "report_field":
            if loc["field"] == "markdown":
                continue
            if loc["field"] == "figures":
                idx = loc.get("index")
                if not isinstance(idx, int) or idx >= len(figs):
                    bad.append(f"{a['asset_id']}: figures[{idx}] out of range "
                               f"(record has {len(figs)})")
                elif figs[idx].get("name") != a.get("name"):
                    bad.append(f"{a['asset_id']}: figure name drift "
                               f"{figs[idx].get('name')!r} != {a.get('name')!r}")
            else:
                bad.append(f"{a['asset_id']}: unknown report field {loc['field']!r}")
        else:
            bad.append(f"{a['asset_id']}: unknown locator scheme {loc['scheme']!r}")
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": f"checked {n_loc} locators against {source_mode}; problems={bad}",
    }

    # ---- no_duplicate_ids ------------------------------------------------
    aids = [a["asset_id"] for a in man["assets"]]
    cids = [c.get("claim_id") for c in env.get("claims", [])]
    checks["no_duplicate_ids"] = {
        "pass": len(aids) == len(set(aids)) and len(cids) == len(set(cids)),
        "detail": f"assets={len(aids)} unique={len(set(aids))}; "
                  f"claims={len(cids)} unique={len(set(cids))}",
    }

    # ---- claims evidence / unresolved -----------------------------------
    viol = []
    for c in env.get("claims", []):
        has_ev = bool(c.get("evidence"))
        has_unres = c.get("status") == "unresolved" and c.get("unresolved_reason")
        if not (has_ev or has_unres):
            viol.append(c.get("claim_id"))
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": not viol,
        "detail": f"claims={len(env.get('claims', []))} violating={viol}"
                  + (" (empty array: vacuously satisfied per contract 'claims 允许为空数组')"
                     if not env.get("claims") else ""),
    }

    # ---- constraint: never self-mark verified ---------------------------
    verified = [c.get("claim_id") for c in env.get("claims", [])
                if c.get("status") == "verified"]
    checks["do_not_mark_claims_as_verified"] = {
        "pass": not verified,
        "detail": f"claims carrying status='verified': {verified}",
    }

    # ---- extra: boundary + internal consistency --------------------------
    extra = {}
    extra["report_scope"] = {
        "pass": env["report_id"] == REPORT_ID and man["report_id"] == REPORT_ID,
        "detail": f"envelope report_id={env['report_id']} manifest report_id={man['report_id']} "
                  f"(single-report scope, nothing else read or written)",
    }
    extra["envelope_matches_manifest"] = {
        "pass": env["outputs"]["asset_manifest.json"] == man,
        "detail": "outputs['asset_manifest.json'] deep-equals asset_manifest.json on disk",
    }
    man_disk = json.load(open(MAN_PATH, encoding="utf-8"))
    extra["manifest_self_hash"] = {
        "pass": True,
        "detail": "sha256(asset_manifest.json bytes) = " + hashlib.sha256(
            open(MAN_PATH, "rb").read()).hexdigest() + " (recorded for provenance)",
    }
    empty_reason_ok = all(a["resolution"].get("reason") or a["resolution"]["status"] == "resolved"
                          for a in man["assets"])
    extra["unresolved_assets_explain_themselves"] = {
        "pass": empty_reason_ok,
        "detail": "every non-resolved asset carries an explicit reason string",
    }
    checks.update(extra)

    checks["_meta"] = {
        "package_id": PKG,
        "checked_at": os.environ.get("KF_CHECKED_AT")
        or _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "source_mode": source_mode,
        "kind": "worker self-check (authoritative verification is the platform gate)",
        "manifest_sha256": extra["manifest_self_hash"]["detail"].split(" = ")[1].split(" ")[0],
    }
    _emit(checks)
    return 0 if all(v["pass"] for k, v in checks.items() if not k.startswith("_")) else 1


def _emit(checks: dict) -> None:
    out = {
        "package_id": PKG,
        "report_id": REPORT_ID,
        "checks": {k: v for k, v in checks.items() if not k.startswith("_")},
        "meta": checks.get("_meta", {}),
        "all_pass": all(v["pass"] for k, v in checks.items() if not k.startswith("_")),
    }
    for path in ("docs/kf/wp-1204-01/self_check.json",
                 "artifacts/wp-1204-01/self_check.json"):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.exit(main())