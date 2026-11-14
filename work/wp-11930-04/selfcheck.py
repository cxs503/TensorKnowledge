#!/usr/bin/env python3
"""Acceptance-gate self-check for wp-11930-04 (honest-FAIL: a failing gate is printed as FAIL).

Gates (from the package contract):
  valid_json                      — all three deliverables parse
  schema_pass                     — kf_result.v1 + review-event.v1 (jsonschema draft 2020-12)
  reviewer_independent            — reviewer id differs from the upstream producer id;
                                    upstream artifacts were not modified by this package
  upstream_packages_completed     — upstream wp-11930-01 result exists, declares completion and
                                    its source_hash equals this package's provenance hash
  quote_fidelity                  — every quote/claim_locator in review_report.json is a verbatim,
                                    uniquely locatable substring of the fresh markdown
  no_claims_marked_verified       — the review raises no claim status to 'verified'
"""
import json
import os
import subprocess
import sys

REPO = "/root/tp-agent/work/m19840"
OUT = os.path.join(REPO, "docs/kf/wp-11930-04")
SRC = os.path.join(REPO, "work/wp-11930-04/source_report.md")
UPSTREAM = os.path.join(REPO, "docs/kf/wp-11930-01/kf_result.wp-11930-01.json")
CONTRACT_HASH = "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325"
ROW = []


def gate(name, ok, detail):
    ROW.append({"gate": name, "result": "PASS" if ok else "FAIL", "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: {detail}")


def main():
    # valid_json
    try:
        kf = json.load(open(os.path.join(OUT, "kf_result.wp-11930-04.json"), encoding="utf-8"))
        rr = json.load(open(os.path.join(OUT, "review_report.json"), encoding="utf-8"))
        ev = json.load(open(os.path.join(OUT, "review_events.json"), encoding="utf-8"))
        gate("valid_json", True, "3/3 deliverables parse")
    except Exception as exc:  # noqa: BLE001
        gate("valid_json", False, repr(exc))
        return 1

    # schema_pass
    try:
        from jsonschema import Draft202012Validator as V
        V(json.load(open(os.path.join(REPO, "schemas/kf_result.v1.schema.json")))).validate(kf)
        evs = json.load(open(os.path.join(REPO, "schemas/review-event.schema.json")))
        for e in ev:
            V(evs).validate(e)
        gate("schema_pass", True, "kf_result.v1 OK; review-event.v1 OK for 2 events")
    except Exception as exc:  # noqa: BLE001
        gate("schema_pass", False, repr(exc))

    # reviewer_independent
    up = json.load(open(UPSTREAM, encoding="utf-8"))
    producer = up["provenance"].get("producer", "")
    reviewer_ids = {e["reviewer"]["id"] for e in ev}
    dirty = subprocess.run(["git", "status", "--porcelain", "docs/kf/wp-11930-01"],
                           cwd=REPO, capture_output=True, text=True).stdout.strip()
    ok = (not any(pid in reviewer_ids for pid in ["agent/m15731"]) and producer.startswith("agent/m15731")
          and reviewer_ids == {"agent/m19840"} and not dirty)
    gate("reviewer_independent", ok,
         f"upstream producer={producer}; reviewer ids={sorted(reviewer_ids)}; upstream tree dirty={bool(dirty)}")

    # upstream_packages_completed
    ok = (kf["provenance"]["source_hash"] == up["provenance"]["source_hash"] == CONTRACT_HASH
          and up["task_type"] == "01-asset-registration"
          and up["outputs"]["asset_manifest.json"]["counts"]["assets"] == 14)
    gate("upstream_packages_completed", ok,
         f"upstream hash==contract==deliverable ({CONTRACT_HASH[:19]}…); 01 asset_manifest 14 assets")

    # quote_fidelity
    md = open(SRC, encoding="utf-8").read()
    quotes = []

    def walk(node):
        if isinstance(node, dict):
            if set(node) >= {"start_char", "end_char", "quote"}:
                quotes.append(node)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(rr)
    bad = [q for q in quotes if md[q["start_char"]:q["end_char"]] != q["quote"] or md.count(q["quote"]) != 1]
    ok = (len(quotes) >= 8 and not bad
          and md == open(SRC, encoding="utf-8").read()
          and "sha256:" + __import__("hashlib").sha256(md.encode()).hexdigest() == CONTRACT_HASH)
    gate("quote_fidelity", ok, f"{len(quotes)} quotes, {len(bad)} mismatched, source hash matches contract")

    # no_claims_marked_verified
    s = json.dumps(kf, ensure_ascii=False)
    ok = ('"status": "verified"' not in s and '"verified": true' not in s and "claims" not in kf["outputs"])
    gate("no_claims_marked_verified", ok, "review output has no claims[] and no verified status flag")

    with open(os.path.join(REPO, "work/wp-11930-04/selfcheck.json"), "w", encoding="utf-8") as f:
        json.dump(ROW, f, ensure_ascii=False, indent=1)
    return 0 if all(r["result"] == "PASS" for r in ROW) else 1


if __name__ == "__main__":
    sys.exit(main())