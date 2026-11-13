#!/usr/bin/env python3
"""Independent re-resolution of wp-9085-01's asset manifest.

This file does not import the generator's helpers: it reads the committed
asset_manifest.json, re-fetches report 9085, and re-derives every locator from the
raw markdown bytes. If the manifest were hand-edited, mis-offset, or contained an
invented reference, this check fails.

Checks
  hash        sha256(markdown UTF-8) == manifest.source.hash == contract hash
  chars       len(markdown) == manifest.source.chars (and contract chars)
  scope       only report 9085 is registered; no other report id appears in ids/uris
  ids         unique, and match ^A[0-9]{2}$
  locators    quote is a substring; md[start:end] == quote; declared line == line of
              start_char; quote unique; occurrences re-resolved individually
  resolution  every asset has a status in the enum and a resolution_check.result
  claims      empty or every claim carries evidence/unresolved status; none verified
  counts      declared counts recomputed from the asset list

Usage: python3 scripts/kf_wp9085_01_verify.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-9085-01"
REPORT_ID = "9085"
CONTRACT_SOURCE_HASH = (
    "sha256:6d424777af46c0c47d01887a47e4de261416aa154a7bbb86d6f1a81502d61d0a"
)
CONTRACT_CHARS = 9761
MANIFEST = ROOT / "docs" / "kf" / PACKAGE_ID / "asset_manifest.json"
ENVELOPE = ROOT / "docs" / "kf" / PACKAGE_ID / "kf_result.json"
RESOLUTIONS = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
CHECK_RESULTS = {"resolved", "unresolved", "absent", "present"}


def fetch_markdown() -> str:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps(
        {
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }
    ).encode()
    tok = json.load(
        urllib.request.urlopen(
            urllib.request.Request(
                base + "/auth/login", data=body,
                headers={"Content-Type": "application/json"},
            )
        )
    )["access_token"]
    req = urllib.request.Request(
        base + "/tensor/reports/%s" % REPORT_ID,
        headers={"Authorization": "Bearer " + tok},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r).get("markdown") or ""


def line_of(md: str, offset: int) -> int:
    """1-based line number containing the character offset."""
    return md.count("\n", 0, offset) + 1


def verify(record: dict | None = None) -> dict:
    md = (record or {}).get("markdown")
    if md is None:
        md = fetch_markdown()
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    failures: list[str] = []

    def check(name: str, ok: bool, detail=None):
        if not ok:
            failures.append(name)
        return {"check": name, "ok": bool(ok), "detail": detail}

    locator_rows, occurrence_rows = [], []
    n_lines = len(md.rstrip("\n").split("\n"))
    for a in manifest["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        in_src = q in md
        uni = md.count(q) == 1
        on_line = line_of(md, loc["start_char"]) == loc["start_line"]
        if loc["method"] == "document":
            # a document-level locator spans the whole field: the quote is a probe
            # string (title line), so span equality is not applicable by design
            span_ok = loc["start_char"] == 0 and loc["end_char"] == len(md)
            ok = in_src and uni and on_line and span_ok and loc["end_line"] == n_lines
            detail = {"method": "document", "spans_whole_field": span_ok,
                      "end_line_matches_document": loc["end_line"] == n_lines,
                      "quote_in_source": in_src, "occurrences_in_source": md.count(q)}
        else:
            span_ok = md[loc["start_char"]:loc["end_char"]] == q
            ok = (span_ok and in_src and on_line and uni
                  and loc["start_line"] <= loc["end_line"])
            detail = {"method": "char_span", "quote_in_source": in_src,
                      "span_matches_quote": span_ok,
                      "start_line_matches_offset": on_line,
                      "occurrences_in_source": md.count(q),
                      "start_line": loc["start_line"],
                      "start_char": loc["start_char"]}
        locator_rows.append(check("locator/%s" % a["asset_id"], ok, detail))
        for k, o in enumerate(a.get("occurrences") or []):
            occurrence_rows.append(
                check(
                    "occurrence/%s/%d" % (a["asset_id"], k),
                    md[o["start_char"]:o["end_char"]] == o["quote"]
                    and o["quote"] in md
                    and line_of(md, o["start_char"]) == o["line"],
                    {"line": o["line"], "form": o["form"]},
                )
            )

    ids = [a["asset_id"] for a in manifest["assets"]]
    recomputed = {
        "by_class": {},
        "by_resolution": {},
    }
    for a in manifest["assets"]:
        recomputed["by_class"][a["asset_class"]] = (
            recomputed["by_class"].get(a["asset_class"], 0) + 1
        )
        recomputed["by_resolution"][a["resolution"]] = (
            recomputed["by_resolution"].get(a["resolution"], 0) + 1
        )

    schema_level = manifest["schema"]
    checks = [
        check("schema_field", schema_level == "asset_manifest.v1", schema_level),
        check("package_id", manifest["package_id"] == PACKAGE_ID),
        check("task_type", manifest["task_type"] == "01-asset-registration"),
        check("report_id", manifest["report_id"] == REPORT_ID),
        check("source_uri", manifest["source"]["uri"] == "tensor://reports/%s" % REPORT_ID),
        check("source_field", manifest["source"]["field"] == "markdown"),
        check("hash_matches_contract", digest == CONTRACT_SOURCE_HASH
              and ("sha256:" + manifest["source"]["hash"]) == CONTRACT_SOURCE_HASH
              and manifest["source"]["hash_prefixed"] == CONTRACT_SOURCE_HASH,
              {"recomputed": digest, "contract": CONTRACT_SOURCE_HASH}),
        check("chars_matches_contract", len(md) == CONTRACT_CHARS
              and manifest["source"]["chars"] == CONTRACT_CHARS, len(md)),
        check("bytes_matches", manifest["source"]["bytes_utf8"] == len(md.encode("utf-8"))),
        check("ids_unique", len(ids) == len(set(ids)) and "" not in ids),
        check("ids_pattern", all(len(i) == 3 and i[0] == "A" and i[1:].isdigit()
                                 for i in ids)),
        check("single_report_scope",
              all(REPORT_ID == str(n) for n in _report_ids_in(manifest))),
        check("counts_match",
              manifest["counts"]["assets"] == len(manifest["assets"])
              and manifest["counts"]["by_class"] == recomputed["by_class"]
              and manifest["counts"]["by_resolution"] == recomputed["by_resolution"]
              and manifest["counts"]["resolved_in_source"]
              == recomputed["by_resolution"].get("resolved_in_source", 0)
              and manifest["counts"]["referenced_unresolved"]
              == recomputed["by_resolution"].get("referenced_unresolved", 0)
              and manifest["counts"]["declared_absent"]
              == recomputed["by_resolution"].get("declared_absent", 0),
              recomputed),
        check("resolution_enum",
              all(a["resolution"] in RESOLUTIONS for a in manifest["assets"])),
        check("resolution_check_present",
              all(a["resolution_check"]["result"] in CHECK_RESULTS
                  and a["resolution_check"]["check"]
                  for a in manifest["assets"])),
        check("claims_status_valid",
              all(c.get("status") != "verified"
                  and (c.get("evidence") or c.get("status") or c.get("evidence_locator")
                       or c.get("unresolved_reason"))
                  for c in manifest["claims"])),
        check("no_claim_marked_verified",
              all(c.get("status") != "verified" for c in manifest["claims"])),
        check("references_not_asserted_without_bytes",
              all(a["existence_asserted_by_worker"] is False
                  for a in manifest["assets"]
                  if a["asset_class"] != "report_markdown")),
    ]

    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    checks += [
        check("envelope_ids",
              env["package_id"] == PACKAGE_ID and env["report_id"] == REPORT_ID),
        check("envelope_hash", env["provenance"]["source_hash"] == digest),
        check("envelope_outputs",
              list(env["outputs"]) == ["asset_manifest.json"]
              and env["outputs"]["asset_manifest.json"]["assets"] == manifest["assets"]),
    ]

    return {
        "package_id": PACKAGE_ID,
        "report_id": REPORT_ID,
        "verified_against": "GET /api/v1/tensor/reports/%s (markdown field)" % REPORT_ID,
        "recomputed_source_hash": digest,
        "contract_source_hash": CONTRACT_SOURCE_HASH,
        "hash_matches_contract": digest == CONTRACT_SOURCE_HASH,
        "chars": len(md),
        "assets": len(manifest["assets"]),
        "locator_checks_passed": sum(1 for r in locator_rows if r["ok"]),
        "locator_checks_total": len(locator_rows),
        "occurrence_checks_passed": sum(1 for r in occurrence_rows if r["ok"]),
        "occurrence_checks_total": len(occurrence_rows),
        "checks": checks,
        "locators": locator_rows,
        "occurrences": occurrence_rows,
        "failures": failures,
        "overall_ok": not failures,
        "independence_note": "Same author as the generator; independence is limited to "
                             "not importing generator code paths — every locator is "
                             "re-derived from the raw markdown bytes.",
    }


def _report_ids_in(node) -> set[str]:
    """All report ids mentioned anywhere in ids/uris of the manifest (scope check)."""
    found: set[str] = set()

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in {"uri", "source_uri"} and isinstance(v, str) and "reports/" in v:
                    found.add(v.rsplit("/", 1)[-1])
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(node)
    found.discard(REPORT_ID)
    return found


if __name__ == "__main__":
    rep = verify()
    print(json.dumps({k: v for k, v in rep.items()
                      if k not in ("checks", "locators", "occurrences")},
                     ensure_ascii=False, indent=2))
    sys.exit(0 if rep["overall_ok"] else 1)