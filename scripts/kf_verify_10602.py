"""Independently verify the wp-10602-01 asset registration (report 10602).

Independence: this script does *not* trust the producer's cached files. It re-fetches the markdown
from the platform API, recomputes sha256, and re-resolves every locator against the freshly fetched
text. Acceptance items of the contract are checked one by one and printed as PASS/FAIL:

  valid_json                      -> envelope + manifest parse as JSON
  schema_pass                     -> envelope vs schemas/kf_result.v1.schema.json,
                                     manifest vs schemas/asset_manifest.v1.1.schema.json
  source_locator_resolvable       -> md[start_char:end_char] == quote for every asset, and, when
                                     locator.unique, md.count(quote) == 1
  source_hash_matches             -> sha256(fresh markdown) == contract hash == manifest hash ==
                                     envelope provenance.source_hash
  no_duplicate_ids                -> asset_id unique
  all_claims_have_evidence_or_explicit_unresolved_status
                                  -> claims empty (allowed by the contract) or every claim carries
                                     evidence / explicit status; no claim marked verified

Exit code 0 iff every check passes. Usage: python3 scripts/kf_verify_10602.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import jsonschema

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kf_fetch_10602 as fetch  # noqa: E402  (same worktree, read-only reuse of the fetch client)

PACKAGE_ID = "wp-10602-01"
REPORT_ID = "10602"
EXPECTED_HASH = "55cb6ccf85a7c340cac1543f97efe631f85b0ed45816f2b484bab5ed9b010687"
CONTRACT_CHARS = 6037

DOC = pathlib.Path("docs/wp-10602-01")
ENVELOPE = DOC / "kf_result.wp-10602-01.json"
MANIFEST = DOC / "asset_manifest.json"
SCHEMAS = pathlib.Path("schemas")


def fresh_markdown() -> str:
    tok = fetch.login()
    payload = fetch._get_json(fetch.BASE + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    return payload["markdown"]


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append((name, ok, detail))

    md = fresh_markdown()
    raw = md.encode("utf-8")

    # ---- valid_json
    try:
        env = json.loads(ENVELOPE.read_text())
        man = json.loads(MANIFEST.read_text())
        check("valid_json", True, f"envelope {len(ENVELOPE.read_text())} B, manifest {len(MANIFEST.read_text())} B parsed")
    except Exception as exc:  # noqa: BLE001
        check("valid_json", False, repr(exc))
        print_results(results)
        return 1

    # ---- schema_pass
    env_schema = json.loads((SCHEMAS / "kf_result.v1.schema.json").read_text())
    man_schema = json.loads((SCHEMAS / "asset_manifest.v1.1.schema.json").read_text())
    try:
        jsonschema.validate(env, env_schema)
        env_ok, env_msg = True, "envelope vs kf_result.v1: ok"
    except jsonschema.ValidationError as exc:
        env_ok, env_msg = False, "envelope: " + exc.message[:200]
    out_man = (env.get("outputs") or {}).get("asset_manifest.json")
    try:
        jsonschema.validate(out_man, man_schema)
        man_ok, man_msg = True, "manifest(in envelope) vs asset_manifest.v1.1: ok"
    except jsonschema.ValidationError as exc:
        man_ok, man_msg = False, "manifest(in envelope): " + exc.message[:200]
    try:
        jsonschema.validate(man, man_schema)
        man2_ok, man2_msg = True, "manifest(standalone) vs asset_manifest.v1.1: ok"
    except jsonschema.ValidationError as exc:
        man2_ok, man2_msg = False, "manifest(standalone): " + exc.message[:200]
    check("schema_pass", env_ok and man_ok and man2_ok, " | ".join([env_msg, man_msg, man2_msg]))
    check("envelope_matches_manifest", out_man == man,
          "outputs['asset_manifest.json'] byte-identical to docs copy")

    # ---- source_hash_matches
    h = hashlib.sha256(raw).hexdigest()
    prov = (env.get("provenance") or {}).get("source_hash", "")
    hash_ok = (h == EXPECTED_HASH == man["source"]["hash"] == prov.replace("sha256:", ""))
    check("source_hash_matches", hash_ok,
          f"fresh={h[:16]}… contract={EXPECTED_HASH[:16]}… manifest={man['source']['hash'][:16]}… "
          f"envelope={prov[:23]}…")
    check("chars_match_contract", len(md) == CONTRACT_CHARS == man["source"]["chars"],
          f"fresh chars={len(md)}, contract={CONTRACT_CHARS}, manifest={man['source']['chars']}")

    # ---- source_locator_resolvable
    bad = []
    for a in man["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        if md[loc["start_char"]:loc["end_char"]] != q:
            bad.append(a["asset_id"] + ":char_span")
            continue
        if loc["unique"] and md.count(q) != 1:
            bad.append(a["asset_id"] + f":multiplicity={md.count(q)}")
            continue
        if md.count(q) < 1:
            bad.append(a["asset_id"] + ":absent")
            continue
        # line numbers must agree with the character span
        s_line = md.count("\n", 0, loc["start_char"])
        e_line = md.count("\n", 0, loc["end_char"])
        if s_line != loc["start_line"] or e_line != loc["end_line"]:
            bad.append(a["asset_id"] + f":line{loc['start_line']}/{loc['end_line']} vs {s_line}/{e_line}")
    check("source_locator_resolvable", not bad,
          f"{len(man['assets'])}/{len(man['assets'])} locators re-resolve on fresh markdown"
          + ("" if not bad else " FAILED: " + ", ".join(bad)))

    # ---- no_duplicate_ids
    ids = [a["asset_id"] for a in man["assets"]]
    check("no_duplicate_ids", len(ids) == len(set(ids)),
          f"{len(set(ids))} unique ids / {len(ids)} assets; contiguous={ids == ['A%02d' % (i + 1) for i in range(len(ids))]}")

    # ---- claims discipline
    claims = man["claims"]
    env_claims = env.get("claims", [])
    claim_bad = []
    for c in claims:
        if not (c.get("evidence_locator") or c.get("evidence") or c.get("status")):
            claim_bad.append(c.get("claim_id", "?"))
        if c.get("status") == "verified":
            claim_bad.append(c.get("claim_id", "?") + ":verified")
    check("all_claims_have_evidence_or_explicit_unresolved_status", not claim_bad,
          f"claims={len(claims)} manifest / {len(env_claims)} envelope (empty = allowed for task_type 01); "
          f"violations={claim_bad or 'none'}")
    check("no_claim_marked_verified", '"verified"' not in ENVELOPE.read_text(),
          "envelope contains no 'verified' status marker")

    # ---- report-id scoping (boundary of the work package)
    check("report_scope_10602_only",
          env["report_id"] == man["report_id"] == REPORT_ID == str(man["source"]["uri"]).rsplit("/", 1)[-1],
          f"envelope/manifest report_id = {env['report_id']}/{man['report_id']}, uri={man['source']['uri']}")
    check("package_identity", env["package_id"] == man["package_id"] == PACKAGE_ID
          and env["task_type"] == "01-asset-registration",
          f"package_id={env['package_id']}, task_type={env['task_type']}")

    # ---- counts self-consistency
    cnt = man["counts"]
    byres = cnt["by_resolution"]
    cnt_ok = (cnt["assets"] == len(man["assets"])
              and sum(byres.values()) == len(man["assets"])
              and byres.get("resolved_in_source", 0) == cnt["resolved_in_source"]
              and byres.get("referenced_unresolved", 0) == cnt["referenced_unresolved"]
              and byres.get("declared_absent", 0) == cnt["declared_absent"])
    check("counts_self_consistent", cnt_ok, json.dumps(cnt, ensure_ascii=False))

    ok = all(r[1] for r in results)
    print_results(results)
    return 0 if ok else 1


def print_results(results):
    w = max(len(r[0]) for r in results)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(w)}  {detail}")


if __name__ == "__main__":
    sys.exit(main())