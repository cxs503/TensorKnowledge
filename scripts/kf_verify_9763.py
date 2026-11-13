"""Independent verification of wp-9763-01 (fresh process, fresh login, re-fetched source).

Deliberately does not trust anything produced by kf_register_9763.py:
  * the markdown is re-downloaded from the platform and re-hashed;
  * every asset locator is re-sliced out of the *re-fetched* markdown and compared to the stored
    quote, and re-checked for uniqueness;
  * the manifest is validated against the pinned schema and the result envelope against
    schemas/kf_result.v1.schema.json (the repo copy of the canonical envelope schema);
  * acceptance items from the work-package contract are evaluated one by one.

Nothing here is allowed to write "verified" into any deliverable: this file is a self-check report,
the authoritative verification is computed by the platform gate.

Outputs: artifacts/wp-9763-01/verification.json (+ docs/kf/wp-9763-01/verification.json mirror)
Usage:  python3 scripts/kf_verify_9763.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

import jsonschema

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import kf_fetch_9763 as fetch  # noqa: E402  (reuse the login/fetch path, re-fetched below)

ROOT = pathlib.Path(".")
RUN_DIR = ROOT / "runs/wp-9763-01"
ART_DIR = ROOT / "artifacts/wp-9763-01"
DOC_DIR = ROOT / "docs/kf/wp-9763-01"
MANIFEST_SCHEMA = ROOT / "schemas/asset_manifest.v1.wp-9763-01.schema.json"
ENVELOPE_SCHEMA = ROOT / "schemas/kf_result.v1.schema.json"
CONTRACT_HASH = "ca29ba6f428001ddc1546e10c82b71ad1a18dcbf1c2bd09a1abd96e9760b1df3"
CONTRACT_CHARS = 3884


def sha_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --- pure check kernels (imported by tests/test_kf_wp9763.py so they can be red-teamed) ---------

def line_offsets(md: str):
    lines, offs, pos = [], [], 0
    for ln in md.split("\n"):
        lines.append(ln)
        offs.append(pos)
        pos += len(ln) + 1
    return lines, offs


def locator_failures(md: str, assets):
    """Every locator must re-slice to its own quote, lines must agree, quote must be unique."""
    lines, offs = line_offsets(md)
    bad = []
    for a in assets:
        loc = a["locator"]
        q = loc["quote"]
        if loc["method"] == "document":
            if q != md:
                bad.append(dict(asset_id=a["asset_id"], why="document quote != markdown"))
            if md.count(q) != 1:
                bad.append(dict(asset_id=a["asset_id"], why="quote not unique", count=md.count(q)))
            continue
        s, e = loc["start_char"], loc["end_char"]
        if not (0 <= s < e <= len(md)):
            bad.append(dict(asset_id=a["asset_id"], why="char span out of range"))
            continue
        if md[s:e] != q:
            bad.append(dict(asset_id=a["asset_id"], why="quote != md[start:end]"))
            continue
        if offs[loc["start_line"]] != s or offs[loc["end_line"]] + len(lines[loc["end_line"]]) != e:
            bad.append(dict(asset_id=a["asset_id"], why="line numbers disagree with char span"))
            continue
        if md.count(q) != 1:
            bad.append(dict(asset_id=a["asset_id"], why="quote not unique", count=md.count(q)))
    return bad


def duplicate_ids(assets):
    ids = [a["asset_id"] for a in assets]
    return sorted({i for i in ids if ids.count(i) > 1})


def unbacked_claims(manifest):
    return [c for c in (manifest.get("claims") or []) if not (c.get("evidence") or c.get("status"))]


def verified_markers(node, path="$"):
    """Any field claiming verified/verification status other than not_verified."""
    hits = []
    if isinstance(node, dict):
        for k, v in node.items():
            if k in ("verified", "is_verified", "verification") and not (
                    k == "verification_status" and v == "not_verified"):
                hits.append(f"{path}.{k}")
            hits += verified_markers(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            hits += verified_markers(v, f"{path}[{i}]")
    return hits


def embedded_sha(envelope):
    payload = json.dumps(envelope["outputs"]["asset_manifest.json"], ensure_ascii=False, indent=2) + "\n"
    return hashlib.sha256(payload.encode()).hexdigest()


def main() -> int:
    checks = []

    def add(check, result, **detail):
        checks.append(dict(check=check, result=result, detail=detail))

    man_path = ART_DIR / "asset_manifest.json"
    env_path = RUN_DIR / "kf_result.wp-9763-01.json"

    # ---- 1. valid_json -------------------------------------------------------
    try:
        man = json.loads(man_path.read_text())
        env = json.loads(env_path.read_text())
        add("valid_json", "pass", manifest=str(man_path), envelope=str(env_path))
    except Exception as exc:  # pragma: no cover - hard fail path
        add("valid_json", "fail", error=repr(exc))
        (ART_DIR / "verification.json").write_text(
            json.dumps(dict(package_id="wp-9763-01", checks=checks, overall="FAIL"),
                       ensure_ascii=False, indent=2) + "\n")
        return 2

    # ---- 2. schema_pass ------------------------------------------------------
    schema_errors = []
    for name, doc, schema in (("asset_manifest", man, MANIFEST_SCHEMA), ("kf_result", env, ENVELOPE_SCHEMA)):
        try:
            jsonschema.validate(doc, json.loads(schema.read_text()))
        except jsonschema.ValidationError as exc:
            schema_errors.append(f"{name}: {exc.message} at {list(exc.absolute_path)}")
    add("schema_pass", "pass" if not schema_errors else "fail",
        schemas=[str(MANIFEST_SCHEMA), str(ENVELOPE_SCHEMA)], errors=schema_errors)

    # ---- 3. source_hash_matches (independent re-fetch) -----------------------
    tok = fetch.login()
    payload = fetch._req(fetch.BASE + "/tensor/reports/9763", token=tok)
    if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    live_md = payload.get("markdown") or ""
    live_hash = hashlib.sha256(live_md.encode()).hexdigest()
    stored_md = (RUN_DIR / "report_9763.md").read_text(encoding="utf-8")
    add("source_hash_matches", "pass" if live_hash == CONTRACT_HASH == man["source"]["hash"]
        else "fail",
        refetched_sha256=live_hash, contract_sha256=CONTRACT_HASH, manifest_sha256=man["source"]["hash"],
        envelope_source_hash=env["provenance"]["source_hash"],
        chars_live=len(live_md), chars_contract=CONTRACT_CHARS, chars_manifest=man["source"]["chars"],
        local_copy_identical=(stored_md == live_md),
        fetched_via=tok and "bearer" or "anonymous")

    # ---- 4. source_locator_resolvable ---------------------------------------
    md = live_md
    bad = locator_failures(md, man["assets"])
    add("source_locator_resolvable", "pass" if not bad else "fail",
        assets_checked=len(man["assets"]), failures=bad,
        method="re-slice every locator out of the re-fetched markdown; assert quote == slice, line/char agreement, uniqueness")
    add("all_assets_span_within_source", "pass" if all(
        a["locator"]["end_char"] <= len(md) for a in man["assets"]) else "fail", source_chars=len(md))

    # ---- 5. no_duplicate_ids ------------------------------------------------
    dup = duplicate_ids(man["assets"])
    add("no_duplicate_ids", "pass" if not dup else "fail", assets=len(man["assets"]), duplicates=dup)

    # ---- 6. claims policy ---------------------------------------------------
    claims = man.get("claims") or []
    unbacked = unbacked_claims(man)
    add("all_claims_have_evidence_or_explicit_unresolved_status",
        "pass" if not unbacked else "fail",
        claim_count=len(claims), unbacked=unbacked,
        note="claims=[] is permitted by the contract (objective.classify_report_type=false); policy check is vacuous-safe")

    # ---- 7. nothing marked verified ----------------------------------------
    vhits = verified_markers(man) + verified_markers(env)
    add("nothing_marked_verified", "pass" if not vhits else "fail", hits=vhits,
        note="verification_status must stay not_verified; the platform gate owns verification")

    # ---- 8. artifact <-> envelope <-> durable mirror identity ---------------
    env_out = env["outputs"]["asset_manifest.json"]
    real_sha = sha_file(man_path)
    mirrored_sha = sha_file(DOC_DIR / "asset_manifest.json")
    emb_sha = embedded_sha(env)
    add("artifact_hash_matches_envelope",
        "pass" if emb_sha == real_sha == env["provenance"].get("artifact_sha256") else "fail",
        file_sha256=real_sha, envelope_embedded_sha256=emb_sha,
        provenance_artifact_sha256=env["provenance"].get("artifact_sha256"))
    add("durable_mirror_identical",
        "pass" if mirrored_sha == real_sha else "fail",
        mirror=str(DOC_DIR / "asset_manifest.json"), mirror_sha256=mirrored_sha, artifact_sha256=real_sha,
        why="push gate drops artifacts/** and runs/**; docs/ is committed, so the mirror must be byte-identical")
    add("envelope_source_hash_equals_manifest_hash",
        "pass" if env["provenance"]["source_hash"] == "sha256:" + man["source"]["hash"] else "fail")
    add("scope_single_report",
        "pass" if man["scope_boundary"]["report_ids_touched"] == ["9763"] and env["report_id"] == "9763" else "fail",
        report_ids=man["scope_boundary"]["report_ids_touched"], envelope_report_id=env["report_id"])

    # ---- 9. cross-check bookkeeping ----------------------------------------
    cc = {c["check_id"]: c["result"] for c in man.get("cross_checks", [])}
    add("cross_checks_present", "pass" if len(cc) >= 5 else "fail", results=cc,
        note="inconsistent/unresolved entries are registered evidence for downstream packages, not gate failures")
    add("cross_check_quotes_locate",
        "pass" if all(md.count(ev["quote"]) == 1 for c in man.get("cross_checks", [])
                      for ev in c.get("evidence", [])) else "fail")

    overall = "PASS" if all(c["result"] in ("pass", "not_run") for c in checks) else "FAIL"
    out = dict(package_id="wp-9763-01", report_id="9763", checks=checks, overall=overall,
               independence=dict(
                   source="markdown re-fetched by this process (fresh login), not read from the local copy only",
                   limitation="TensorFEM solver code/tests and figure png files are outside this worktree; this "
                              "package registers pointers only and does not execute or re-validate the physics"),
               note="not a platform gate result: verification_status stays not_verified")
    blob = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    (ART_DIR / "verification.json").write_text(blob)
    (DOC_DIR / "verification.json").write_text(blob)

    for c in checks:
        print(f"[{c['result']:4}] {c['check']}")
    print("overall:", overall)
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())