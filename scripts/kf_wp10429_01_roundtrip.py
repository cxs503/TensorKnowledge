#!/usr/bin/env python3
"""Round-trip check: what the platform stored for this package equals what we committed.

The KF contract says the result JSON must be the report's *single* ```json block.  This
script re-reads the published report, asserts (a) exactly one json block, (b) it parses
to the committed envelope, (c) the stored markdown is byte-identical to the local
manuscript, and (d) the stored provenance.source_hash is the contract hash.

Usage: python3 scripts/kf_wp10429_01_roundtrip.py [report_id]
Outputs: runs/wp-10429-01/roundtrip.json (+ docs mirror); exit 0 iff all assertions hold.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sys
import urllib.request

API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
REPORT_ID = sys.argv[1] if len(sys.argv) > 1 else "14764"
PACKAGE_ID = "wp-10429-01"
CONTRACT_HASH = "sha256:6e48f09bc41ac354d46463f6f91ef5b6d34a1ffa7748dcf6a3083c4f6944be1d"
# Earlier drafts of this package's report, kept for audit.  Draft 14764 carried a
# non-verbatim display quote for asset A01 (elided head + marker text); a gate that
# resolves every quote by substring search would have failed on it, so the quote was
# made a verbatim slice and the package was republished.  Platform DELETE is not
# available (405 Method Not Allowed), so the draft is left in place, superseded.
SUPERSEDED = [dict(
    report_id=14764,
    reason=("A01 locator quote was an elided display string, not a verbatim slice; "
            "republished after making it verbatim (this report supersedes it)"),
)]
RUN = pathlib.Path("runs/wp-10429-01")
DOC = pathlib.Path("docs/kf/wp-10429-01")
MD = pathlib.Path("docs/kf_result_wp-10429-01.md")


def get(path: str, tok: str | None = None):
    req = urllib.request.Request(API + path)
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    return json.load(urllib.request.urlopen(req, timeout=120))


def main() -> int:
    creds = {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
    req = urllib.request.Request(API + "/auth/login", data=json.dumps(creds).encode(),
                                 headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req, timeout=60))["access_token"]
    rec = get(f"/tensor/reports/{REPORT_ID}", tok)
    rec = rec.get("data", rec)
    md = rec["markdown"]

    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    posted = json.loads(blocks[0]) if len(blocks) == 1 else None
    committed = json.loads((RUN / "kf_result.wp-10429-01.json").read_text())
    local_md = MD.read_text()

    checks = {
        "single_json_block": len(blocks) == 1,
        "block_equals_committed_envelope": posted == committed,
        "stored_markdown_identical_to_local": md == local_md,
        "stored_source_hash_is_contract_hash": bool(posted) and posted["provenance"]["source_hash"] == CONTRACT_HASH,
        "title_and_tags": rec["title"] == f"KF-RESULT {PACKAGE_ID}" and f"kf-wp:{PACKAGE_ID}" in rec["tags"],
        "no_figures_and_reason_in_body": (rec.get("figures") == [] and "无图理由" in md),
    }
    ok = all(checks.values())
    out = dict(package_id=PACKAGE_ID, published_report_id=int(REPORT_ID), all_pass=ok, checks=checks,
               stored_markdown_sha256=hashlib.sha256(md.encode()).hexdigest(),
               stored_markdown_chars=len(md), tags=rec["tags"], mission_id=rec.get("mission_id"),
               scenario_key=rec.get("scenario_key"), superseded=SUPERSEDED,
               invocation="python3 scripts/kf_wp10429_01_roundtrip.py " + str(REPORT_ID))
    for p in (RUN / "roundtrip.json", DOC / "roundtrip.json"):
        p.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: v for k, v in out.items() if k != "tags"}, ensure_ascii=False, indent=1))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())