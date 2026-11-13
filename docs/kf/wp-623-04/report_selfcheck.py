#!/usr/bin/env python3
"""Machine self-check for the wp-623-04 deliverable.

Fails closed: any unverifiable quote, schema error, stray json block or illegal
review transition turns the corresponding entry to ok=false. The producer never
writes a 'verified' verdict here either — this file only reports what was checked.

Outputs: docs/kf/wp-623-04/report_selfcheck.json
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PKG = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import jsonschema  # noqa: E402
from ke_state_machine import fold, is_independent, producer_identity, submit  # noqa: E402

MD = PKG / "KF-RESULT-wp-623-04.md"
KF = json.loads((PKG / "kf_result.json").read_text())
RR = json.loads((PKG / "review_report.json").read_text())
EV = json.loads((PKG / "review_events.json").read_text())
CON = json.loads((PKG / "work-package.json").read_text())
text = MD.read_text()

res: dict = {"checks": {}, "ok": True}


def chk(name: str, ok: bool, detail) -> None:
    res["checks"][name] = {"ok": bool(ok), "detail": detail}
    if not ok:
        res["ok"] = False


def validate(schema_name: str, doc) -> list[str]:
    schema = json.loads((ROOT / "schemas" / schema_name).read_text())
    return [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(doc)]


# --- 1. envelope: exactly one json block, equal to kf_result.json -----------
blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
chk("single_json_block", len(blocks) == 1, f"json_blocks={len(blocks)}")
chk("no_stray_json_fence_token", text.count("```json") == 1,
    f"occurrences of the ```json token anywhere in the document = {text.count('```json')}")
if blocks:
    parsed = json.loads(blocks[0])
    chk("json_block_equals_kf_result_file", parsed == KF,
        "block text parsed and compared to kf_result.json")
    chk("json_block_text_equals_file",
        blocks[0] == json.dumps(KF, ensure_ascii=False, indent=1),
        f"block_chars={len(blocks[0])}")

# --- 2. title / sections -----------------------------------------------------
chk("title_line", text.splitlines()[0] == "# KF-RESULT wp-623-04", text.splitlines()[0][:60])
secs = ["① 本工序做了什么", "② 怎么做的", "③ 产出物清单", "④ 证据定位表", "⑤ 注意点与局限", "⑥ 自检"]
chk("six_sections", all(s in text for s in secs), [s for s in secs if s not in text])
chk("repro_cmd_present", "repro_cmd" in text and "verify_upstream.py" in text, "bash block + scripts named")

# --- 3. source + quote re-verification (zero hand transcription) -----------
TOKEN = __import__("os").environ.get("TENSOR_KF_TOKEN", "")
if TOKEN:
    req = urllib.request.Request(__import__("os").environ["TENSOR_API_BASE"] + "/tensor/reports/623",
                                 headers={"Authorization": "Bearer " + TOKEN})
    rec = json.loads(urllib.request.urlopen(req, timeout=60).read())
    src, src_from = rec["markdown"], "live API"
else:                                        # offline fallback: the shipped copy
    src = (ROOT / "work/w623/source_623.md").read_text()
    src_from = "work/w623/source_623.md"
lines = src.rstrip("\n").split("\n")
live_hash = "sha256:" + hashlib.sha256(src.encode("utf-8")).hexdigest()
chk("source_hash_recomputed", live_hash == KF["provenance"]["source_hash"],
    f"source={src_from} live={live_hash} envelope={KF['provenance']['source_hash']}")
chk("envelope_source_hash_equals_contract_input",
    live_hash == CON["input"]["source_hash"], CON["input"]["source_hash"])

cites = re.findall(r"L(\d+) ▸ 「(.+?)」", text)
bad = []
for lineno, quote in cites:
    n = int(lineno)
    if not (1 <= n <= len(lines)) or quote not in lines[n - 1]:
        bad.append({"line": n, "quote": quote[:60]})
chk("body_citations_verbatim", not bad, f"{len(cites)} citations re-resolved; bad={bad}")

rr_quotes = [ev for f in RR["findings"] for ev in f["evidence"]]
bad_q = [{"line": e["line"], "chars": len(e.get("quote", ""))}
         for e in rr_quotes
         if e.get("quote") and e["quote"] not in lines[e["line"] - 1]]
chk("review_report_quotes_verbatim", not bad_q,
    f"{len(rr_quotes)} evidence quotes (" + str(sum(1 for e in rr_quotes if e.get('quote'))) +
    " non-empty) re-resolved; bad=" + str(bad_q))
empty_documented = all(e.get("note") for e in rr_quotes if not e.get("quote"))
chk("empty_quotes_documented", empty_documented,
    f"empty quotes={[e['line'] for e in rr_quotes if not e.get('quote')]}")
sha_ok = all(
    e.get("quote_sha256") == "sha256:" + hashlib.sha256(lines[e["line"] - 1].encode("utf-8")).hexdigest()
    for e in rr_quotes)
chk("evidence_quote_sha256_recomputed", sha_ok, f"{len(rr_quotes)} evidence lines hashed")

# --- 4. schemas -------------------------------------------------------------
chk("schema_kf_result", not validate("kf_result.v1.schema.json", KF),
    validate("kf_result.v1.schema.json", KF))
chk("schema_work_package", not validate("work-package-contract.schema.json", CON),
    validate("work-package-contract.schema.json", CON))
ev_errs = [e for i, d in enumerate(EV) for e in
           (f"[{i}] " + m for m in validate("review-event.schema.json", d))]
chk("schema_review_events", not ev_errs, ev_errs)

# --- 5. review ledger: legality + independence ------------------------------
producer_ids = [str(RR["reviewed_package"]["producer"])]
start = submit({"producer_ids": producer_ids}, "draft")   # draft -> in-review (system transition)
state, codes = fold(EV, {"producer_ids": producer_ids}, initial_state=start)
approvals = [e for e in EV if e["decision"] == "approve"]
indep = [dict(zip(("ok", "basis"),
                  is_independent(e["reviewer"], producer_identity({"producer_ids": producer_ids}))))
         for e in approvals]
chk("review_state_legal", state in ("approved", "changes-requested", "rejected"),
    f"state={state} codes={codes} producer_ids={producer_ids}")
chk("reviewer_independent", all(i["ok"] for i in indep) if indep else False, indep)

# --- 6. no self-verification, verdict consistency --------------------------
blob = json.dumps(KF["outputs"], ensure_ascii=False)
markers = [m for m in ("verified", "verification_status", "verification_level", "is_verified")
           if f'"{m}"' in blob]
chk("no_verified_field_in_outputs", not markers, markers)
chk("verdict_uses_no_verified_word",
    "verified" not in RR["verdict"], RR["verdict"])
cs = RR["checks_summary"]
chk("checks_summary_arithmetic",
    cs["total"] == len(RR["checks_performed"])
    and cs["passed"] == sum(1 for c in RR["checks_performed"] if c["ok"]),
    f"claimed total/passed={cs['total']}/{cs['passed']} "
    f"recomputed={len(RR['checks_performed'])}/{sum(1 for c in RR['checks_performed'] if c['ok'])}")
chk("every_finding_has_evidence_and_repro",
    all(f["evidence"] and f["reproduction"] for f in RR["findings"]),
    [f["finding_id"] for f in RR["findings"]])
chk("failed_checks_referenced_by_findings",
    all(any(fc in f["reproduction"] for f in RR["findings"]) for fc in cs["failed"]),
    cs["failed"])

failed = [k for k, v in res["checks"].items() if not v["ok"]]
res["summary"] = {"checks_total": len(res["checks"]),
                  "checks_failed": failed,
                  "ok": res["ok"],
                  "checks_result_envelope_ok": not [k for k in failed if k != "schema_work_package"],
                  "declared_conflict": "schema_work_package fails only because the owner YAML declares "
                                       "review.required/independent_reviewer=false while "
                                       "schemas/work-package-contract.schema.json 04 branch pins both to const "
                                       "true; see review_report.json -> contract_schema_conflicts",
                  "source": src_from,
                  "note": "self-check only: no claim is marked verified here; the platform gate recomputes "
                          "hash/locators and the verification level."}
(PKG / "report_selfcheck.json").write_text(json.dumps(res, ensure_ascii=False, indent=1) + "\n")
print(json.dumps(res["summary"], ensure_ascii=False, indent=1))
raise SystemExit(0 if res["ok"] else 1)
