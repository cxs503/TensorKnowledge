#!/usr/bin/env python3
"""wp-13560-01 — independent re-derivation of every acceptance item.

Deliberately shares no code with scripts/kf/kf01_register.py: the source is re-fetched, the
locators are re-sliced here, and the report block is re-parsed here. Purpose = a second opinion
that can disagree with the producer (adversarial-review discipline), not a re-run of its verifier.

Output: docs/kf/wp-13560-01/verification_independent.json  (exit 1 on any failed check)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs/kf/wp-13560-01"
BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
REPORT_ID = "13560"
CONTRACT_HASH = "b578c093ddeff7571dcdc5b98383da2b564f608fa77b5b3ea1a10f05b0722279"
CONTRACT_CHARS = 2887


def http(url, data=None, token=None):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    return json.load(urllib.request.urlopen(req, timeout=120))


def main() -> int:
    tok = http(BASE + "/auth/login", json.dumps({
        "username": os.environ["TENSOR_AGENT_USER"],
        "password": os.environ["TENSOR_AGENT_PASS"]}).encode())["access_token"]
    md = http(BASE + "/tensor/reports/" + REPORT_ID, token=tok)["markdown"]
    raw = md.encode("utf-8")
    checks = {}

    manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    report = (OUT / "report.md").read_text(encoding="utf-8")

    # 1 hash, recomputed from a fresh fetch
    digest = hashlib.sha256(raw).hexdigest()
    checks["source_hash_matches"] = {
        "pass": digest == CONTRACT_HASH == manifest["source"]["hash"]
        and result["provenance"]["source_hash"] == "sha256:" + digest,
        "detail": "fresh_fetch=%s contract=%s manifest=%s envelope=%s chars=%d/%d"
                  % (digest, CONTRACT_HASH, manifest["source"]["hash"],
                     result["provenance"]["source_hash"], len(md), CONTRACT_CHARS)}

    # 2 every locator re-sliced here; char span / quote / line map / uniqueness flag
    bad = []
    line_starts, acc = [], 0
    for ln in md.split("\n"):
        line_starts.append(acc)
        acc += len(ln) + 1

    def line_of(pos):
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo

    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if not (0 <= s < e <= len(md)):
            bad.append([a["asset_id"], "span_out_of_range"])
        elif md[s:e] != q or q not in md:
            bad.append([a["asset_id"], "quote_not_verbatim_slice"])
        elif line_of(s) + 1 != loc["start_line"] or line_of(e - 1) + 1 != loc["end_line"]:
            bad.append([a["asset_id"], "line_map_mismatch",
                        loc["start_line"], line_of(s) + 1, loc["end_line"], line_of(e - 1) + 1])
        elif loc["unique"] != (md.count(q) == 1):
            bad.append([a["asset_id"], "unique_flag_wrong", loc["unique"], md.count(q)])
        elif loc["method"] == "char_span" and md.count(q) == 0:
            bad.append([a["asset_id"], "missing"])
    checks["source_locator_resolvable"] = {
        "pass": not bad,
        "detail": "independently re-sliced %d locators (span/quote/line/uniqueness) failures=%s"
                  % (len(manifest["assets"]), bad)}

    # 3 no duplicate asset ids, and counts agree with the asset list
    ids = [a["asset_id"] for a in manifest["assets"]]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    cls, res = {}, {}
    for a in manifest["assets"]:
        cls[a["asset_class"]] = cls.get(a["asset_class"], 0) + 1
        res[a["resolution"]] = res.get(a["resolution"], 0) + 1
    c = manifest["counts"]
    checks["no_duplicate_ids"] = {"pass": not dup and len(ids) == c["assets"],
                                 "detail": "ids=%d unique=%d duplicates=%s counts.assets=%d"
                                           % (len(ids), len(set(ids)), dup, c["assets"])}
    checks["counts_consistent"] = {
        "pass": cls == c["by_class"] and res == c["by_resolution"]
        and c["resolved_in_source"] == res.get("resolved_in_source", 0)
        and c["referenced_unresolved"] == res.get("referenced_unresolved", 0)
        and c["declared_absent"] == res.get("declared_absent", 0),
        "detail": "recomputed by_class=%s by_resolution=%s" % (json.dumps(cls, ensure_ascii=False),
                                                              json.dumps(res, ensure_ascii=False))}

    # 4 claims discipline: empty is legal; nothing may be marked verified
    claims = manifest.get("claims", [])
    vhit = [n for n, txt in (("manifest", json.dumps(manifest, ensure_ascii=False)),
                             ("result", json.dumps(result, ensure_ascii=False)))
            if re.search(r'"(status|verification_status|verified)\s*:\s*"?(verified|true)', txt)]
    checks["all_claims_have_evidence_or_explicit_unresolved_status"] = {
        "pass": claims == [] and all("evidence" in cl or "status" in cl for cl in claims),
        "detail": "claims=%d (contract notes: empty array is a legitimate complete result)" % len(claims)}
    checks["no_verified_markers"] = {"pass": not vhit,
                                     "detail": "documents containing a verified marker: %s" % vhit}

    # 5 schema: envelope against the shipped schema, manifest against schemas/asset_manifest.v1.schema.json
    import jsonschema
    errs = []
    env_schema = json.loads((REPO / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    for e in jsonschema.Draft202012Validator(env_schema).iter_errors(result):
        errs.append("kf_result: %s at %s" % (e.message, list(e.path)))
    man_schema = json.loads((REPO / "schemas/asset_manifest.v1.schema.json").read_text(encoding="utf-8"))
    for key in ("package_id", "task_type", "report_id"):  # relax the wp-448-01 pinned consts only
        if "const" in man_schema["properties"][key]:
            man_schema["properties"][key] = {"type": "string", "minLength": 1}
    if "const" in man_schema["properties"]["source"]["properties"]["uri"]:
        man_schema["properties"]["source"]["properties"]["uri"] = {"type": "string",
                                                                   "pattern": r"^tensor://reports/[0-9]+$"}
    for e in jsonschema.Draft202012Validator(man_schema).iter_errors(manifest):
        errs.append("asset_manifest: %s at %s" % (e.message, list(e.path)))
    checks["schema_pass"] = {"pass": not errs, "detail": "errors=%d %s" % (len(errs), errs[:5])}
    checks["valid_json"] = {"pass": True, "detail": "three artifacts parsed by json.loads"}

    # 6 report discipline: exactly one fenced json block, byte-identical to kf_result.json,
    #   title/tags as the contract requires
    blocks = re.findall(r"```json\n(.*?)\n```", report, flags=re.S)
    same = len(blocks) == 1 and json.loads(blocks[0]) == result
    fences_all = report.count("```")
    payload = json.loads((OUT / "report_payload.json").read_text(encoding="utf-8")) if (OUT / "report_payload.json").exists() else {}
    checks["report_block_is_the_result"] = {
        "pass": same and fences_all % 2 == 0,
        "detail": "json_blocks=%d fenced_markers=%d block_equals_kf_result=%s" % (len(blocks), fences_all, same)}
    checks["report_title_and_tags"] = {
        "pass": payload.get("title") == "KF-RESULT wp-13560-01"
        and "kf-wp:wp-13560-01" in (payload.get("tags") or [])
        and str(payload.get("mission_id")) == "15764",
        "detail": "title=%r tags=%s mission_id=%s" % (payload.get("title"), payload.get("tags"),
                                                      payload.get("mission_id"))}

    # 7 scope: this package speaks about report 13560 only
    other = [rid for rid in re.findall(r"tensor://reports/(\d+)", json.dumps(manifest) + json.dumps(result))
             if rid != REPORT_ID]
    checks["report_id_scoped"] = {"pass": not other and manifest["report_id"] == result["report_id"] == REPORT_ID,
                                 "detail": "foreign report_ids mentioned=%s" % sorted(set(other))}

    out = {"package_id": "wp-13560-01", "report_id": REPORT_ID,
           "verified_by": "scripts/kf/kf_wp13560_01_independent_check.py",
           "independence_note": "separate implementation; shares no code with scripts/kf/kf01_register.py; "
                                "source re-fetched from the API, locators re-sliced, block re-parsed",
           "source_hash_recomputed": "sha256:" + digest,
           "checks": checks,
           "all_pass": all(v["pass"] for v in checks.values()),
           "scope_note": "self-check by the producing agent's independent checker; the authoritative "
                         "verification is the platform gate."}
    (OUT / "verification_independent.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                                      encoding="utf-8")
    for k, v in checks.items():
        print(("PASS " if v["pass"] else "FAIL ") + k)
    print("all_pass =", out["all_pass"])
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())