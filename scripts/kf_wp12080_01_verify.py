"""Independent re-check of work package wp-12080-01 deliverables.

Nothing here trusts the generator: it re-reads the source markdown from disk, re-slices
every locator quote, re-validates the envelope against the canonical platform schema
(schemas/kf_result.v1.schema.json) and asserts that the delivery report body contains
exactly ONE JSON fence which parses to exactly the emitted envelope.

Optional platform-side re-check: --published <report_id> re-fetches the published
KF-RESULT report and compares its fence content with the local envelope (substring /
hash of the whole markdown is NOT comparable because the platform may normalise
whitespace, so the fence content is compared structurally).

Exit code 0 = all checks pass. Writes runs/wp-12080-01/verification.json.
Recorded status stays "not_verified": the platform gate is the only verifier.
"""
from __future__ import annotations

import argparse
import re
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

import jsonschema

PKG = "wp-12080-01"
CONTRACT_HASH = "fe235db998e65d47ead6658e95916dbdf9764ffd213002e7ffe8ca58809c93e0"
CONTRACT_CHARS = 7931
RUN = pathlib.Path("runs") / PKG
DOC = pathlib.Path("docs") / PKG
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def split_single_fence(md: str):
    """Return (n_fences, parsed_json_or_None)."""
    fences = md.count("```")
    n_blocks = 0
    i = 0
    payload = None
    while True:
        j = md.find("```", i)
        if j < 0:
            break
        k = md.find("\n", j)
        if k < 0:
            break
        info = md[j + 3:k].strip()
        close = md.find("```", k)
        if close < 0:
            break
        n_blocks += 1
        if info == "json":
            payload = md[k + 1:close]
        i = close + 3
    return fences, n_blocks, payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--published", default=None, help="report_id of the published KF-RESULT")
    args = ap.parse_args()

    checks = {}
    detail = {}
    md = (RUN / "report_12080.md").read_text(encoding="utf-8")
    env = json.loads((DOC / ("kf_result.%s.json" % PKG)).read_text(encoding="utf-8"))
    manifest = env["outputs"]["asset_manifest.json"]

    # ---- 1. source hash / size
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    checks["source_hash_matches_contract"] = digest == CONTRACT_HASH
    checks["provenance_hash_matches_local_sha256"] = env["provenance"]["source_hash"] == "sha256:" + digest
    checks["source_chars_match_contract"] = len(md) == CONTRACT_CHARS
    checks["manifest_hash_matches_local_sha256"] = manifest["source"]["hash"] == digest
    checks["manifest_bytes_consistent"] = manifest["source"]["bytes_utf8"] == len(md.encode("utf-8"))
    detail["sha256"] = digest

    # ---- 2. canonical envelope schema (platform-side file, unmodified)
    schema = json.loads(pathlib.Path("schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator(schema).validate(env)
        checks["kf_result_schema_pass"] = True
        detail["schema_error"] = None
    except jsonschema.ValidationError as exc:  # pragma: no cover
        checks["kf_result_schema_pass"] = False
        detail["schema_error"] = "%s at %s" % (exc.message, list(exc.absolute_path))

    # ---- 3. manifest structure + locator resolvability
    checks["manifest_identity"] = (
        manifest["schema"] == "asset_manifest.v1"
        and manifest["package_id"] == PKG
        and manifest["task_type"] == "01-asset-registration"
        and manifest["report_id"] == "12080"
        and manifest["source"]["uri"] == "tensor://reports/12080"
        and manifest["source"]["field"] == "markdown"
    )
    required = ("asset_id", "asset_class", "label", "in_report_section", "locator",
                "resolution", "resolution_check", "note")
    checks["asset_records_complete"] = all(all(k in a for k in required) for a in manifest["assets"])
    ids = [a["asset_id"] for a in manifest["assets"]]
    checks["no_duplicate_ids"] = len(ids) == len(set(ids)) and len(ids) == len(set(i.upper() for i in ids))
    checks["asset_id_format"] = all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)

    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        ok = (
            isinstance(loc["start_char"], int) and isinstance(loc["end_char"], int)
            and 0 <= loc["start_char"] < loc["end_char"] <= len(md)
            and md[loc["start_char"]:loc["end_char"]] == q
            and md.count(q) == 1
            and loc["unique"] is True
            and q.strip() != ""
            and "```" not in q
        )
        if not ok:
            bad.append(a["asset_id"])
    checks["source_locator_resolvable"] = not bad
    detail["locator_failures"] = bad
    detail["locators_checked"] = len(manifest["assets"])
    detail["quotes_unique_chars"] = sum(len(a["locator"]["quote"]) for a in manifest["assets"])

    counts = manifest["counts"]
    by_res = counts["by_resolution"]
    checks["counts_consistent"] = (
        counts["assets"] == len(manifest["assets"])
        and sum(counts["by_class"].values()) == counts["assets"]
        and sum(by_res.values()) == counts["assets"]
        and counts["resolved_in_source"] == by_res.get("resolved_in_source", 0)
        and counts["referenced_unresolved"] == by_res.get("referenced_unresolved", 0)
        and counts["declared_absent"] == by_res.get("declared_absent", 0)
    )
    fig_quotes = [a["locator"]["quote"] for a in manifest["assets"] if a["asset_class"] == "figure"]
    fig_names = sorted(re.findall(r"[A-Za-z0-9_\-]+\.png", " ".join(fig_quotes)))
    checks["figures_registered_match_metadata"] = fig_names == sorted(manifest["source"]["platform_figures"])

    # uncertainty / status vocabulary used anywhere in the envelope
    allowed_status = {"supported", "partially-supported", "unresolved", "refuted"}
    checks["claim_status_vocabulary"] = all(c.get("status", "supported") in allowed_status
                                            for c in env.get("claims", []))

    # ---- 4. claims guard: every claim carries evidence or an explicit status
    def claim_ok(c):
        return ("evidence" in c and len(c["evidence"]) > 0) or c.get("unresolved_reason") or "status" in c

    checks["claims_have_evidence_or_status"] = all(claim_ok(c) for c in env.get("claims", []))
    checks["no_claim_marked_verified"] = all(
        c.get("status") != "verified" and "verified" not in c.get("text", "") for c in env.get("claims", []))
    checks["verification_status_not_verified"] = env["provenance"]["verification_status"] == "not_verified"
    checks["manifest_integrity_flags"] = (
        manifest["integrity"]["hash_recomputed_locally"] is True
        and manifest["integrity"]["hash_matches_contract"] is True)

    # ---- 5. delivery body: exactly one fence, parses to the envelope
    body = (DOC / ("KF-RESULT-%s.md" % PKG)).read_text(encoding="utf-8")
    fences, n_blocks, payload = split_single_fence(body)
    checks["body_single_fence_block"] = fences == 2 and n_blocks == 1
    checks["body_title"] = body.splitlines()[0].strip() == "# KF-RESULT " + PKG
    try:
        parsed = json.loads(payload)
        checks["body_json_equals_envelope"] = parsed == env
    except Exception as exc:
        detail["body_json_error"] = str(exc)
        checks["body_json_equals_envelope"] = False

    # ---- 6. optional: published copy re-fetch
    if args.published:
        tok = None
        try:
            req = urllib.request.Request(
                BASE + "/auth/login",
                data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                 "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                headers={"Content-Type": "application/json"})
            tok = json.load(urllib.request.urlopen(req, timeout=60))["access_token"]
            req = urllib.request.Request(BASE + "/tensor/reports/" + args.published,
                                         headers={"Authorization": "Bearer " + tok})
            pub = json.load(urllib.request.urlopen(req, timeout=60))
            pub = pub.get("data", pub) if isinstance(pub, dict) else pub
            pf, pb, ppayload = split_single_fence(pub["markdown"])
            checks["published_single_fence_block"] = pf == 2 and pb == 1
            checks["published_json_equals_envelope"] = json.loads(payload) == json.loads(ppayload)
            # append-only: the published body must be byte-identical to the tree copy
            checks["published_body_byte_identical"] = pub["markdown"] == body
            detail["published_report_id"] = args.published
            detail["published_tags"] = pub.get("tags")
            detail["published_title"] = pub.get("title")
        except Exception as exc:  # pragma: no cover
            checks["published_json_equals_envelope"] = False
            detail["published_error"] = str(exc)

    out = {
        "package_id": PKG, "report_id": "12080",
        "status": "not_verified",
        "note": "local self-check only; the platform gate computes verification independently",
        "all_pass": all(checks.values()),
        "checks": checks, "detail": detail,
    }
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "verification.json").write_text(json.dumps(out, ensure_ascii=False, indent=2))
    for k, v in checks.items():
        print(("PASS " if v else "FAIL ") + k)
    print("all_pass =", out["all_pass"])
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())