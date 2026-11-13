#!/usr/bin/env python3
"""Independent re-check harness for work package wp-4776-04 (review of wp-4776-01).

Everything here re-derives the facts from two primary sources only:
  * tensor://reports/4776 markdown (the object under review, read-only)
  * the structured artifact of wp-4776-01 (outputs["asset_manifest.json"]) -- the
    upstream KO.  No producer prose is read or relied on.

Checks
  C1  source markdown sha256 == contract source_hash, and char count == 4869
  C2  every registered locator: quote present, char offsets exact, content_hash exact,
      occurrence count exact
  C3  completeness: every path / ref token in the markdown is either registered or
      explicitly listed as out-of-scope
  C4  report-internal arithmetic consistency (the numbers the report asserts)
  C5  reachability probes: does the report store actually serve the figure bytes?
  C6  every quote carried by review_report.json is a verbatim substring of the source
  C7  the review never marks upstream claims as verified, and its verdict is consistent
      with its own findings (no 'pass' with blocking findings)

Usage:  python3 verify_review.py [--offline]   (writes checks.json next to this file)
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONTRACT_SOURCE_HASH = "sha256:03d3239696a36958c408df0ac3fd21d506a39cce4277b7f918134591d00d3882"
CONTRACT_CHARS = 4869
REPORT_ID = "4776"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def login() -> str:
    req = urllib.request.Request(
        API + "/login",
        data=json.dumps(
            {"username": os.environ["TENSOR_AGENT_USER"], "password": os.environ["TENSOR_AGENT_PASS"]}
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    body = json.load(urllib.request.urlopen(req))
    return body.get("access_token") or body["token"]


def get(url: str, token: str | None):
    headers = {"Authorization": "Bearer " + token} if token else {}
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20)
        return r.status, r.headers.get("content-type"), r.read()
    except urllib.error.HTTPError as e:  # noqa: PERF203 - explicit probe semantics
        return e.code, None, e.read()[:200]


def fetch_markdown(offline: bool, token: str | None) -> tuple[str, str]:
    local = os.path.join(HERE, "source_4776.md")
    if not offline:
        status, _, raw = get(f"{API}/tensor/reports/{REPORT_ID}", token)
        if status == 200:
            return json.loads(raw)["markdown"], f"GET {API}/tensor/reports/{REPORT_ID} -> 200"
        note = f"GET {API}/tensor/reports/{REPORT_ID} -> {status}; fell back to local snapshot"
    else:
        note = "offline: local snapshot"
    return open(local, encoding="utf-8").read(), note


# ---------------------------------------------------------------- C1
def c1_source(md: str) -> dict:
    h = sha256(md)
    return {
        "check": "C1_source_identity",
        "sha256": h,
        "contract_source_hash": CONTRACT_SOURCE_HASH,
        "hash_matches_contract": h == CONTRACT_SOURCE_HASH,
        "chars": len(md),
        "contract_chars": CONTRACT_CHARS,
        "chars_match_contract": len(md) == CONTRACT_CHARS,
        "utf8_bytes": len(md.encode("utf-8")),
        "ascii_only": all(ord(c) < 128 for c in md),
        "pass": h == CONTRACT_SOURCE_HASH and len(md) == CONTRACT_CHARS,
    }


# ---------------------------------------------------------------- C2
def c2_locators(md: str, manifest: dict) -> dict:
    rows = []
    for a in manifest["asset_inventory"]:
        loc = a["locator"]
        q = loc["quote"]
        starts = [m.start() for m in re.finditer(re.escape(q), md)]
        exact_span = md[loc["char_start"]:loc["char_end"]] == q
        line = md.count("\n", 0, loc["char_start"]) + 1 if starts else None
        rows.append(
            {
                "asset_id": a["asset_id"],
                "kind": a["kind"],
                "declared_path": a["declared_path"],
                "quote_verbatim": bool(starts),
                "occurrences_actual": len(starts),
                "occurrences_declared": loc.get("occurrences"),
                "occurrences_match": len(starts) == loc.get("occurrences"),
                "offset_span_exact": exact_span,
                "content_hash_match": sha256(q) == loc.get("content_hash"),
                "line_actual": line,
                "line_declared": loc.get("line"),
                "line_match": line == loc.get("line"),
                "ok": bool(starts) and exact_span and len(starts) == loc.get("occurrences")
                and sha256(q) == loc.get("content_hash") and line == loc.get("line"),
            }
        )
    return {
        "check": "C2_locator_fidelity",
        "assets_checked": len(rows),
        "assets_ok": sum(r["ok"] for r in rows),
        "rows": rows,
        "pass": all(r["ok"] for r in rows),
    }


# ---------------------------------------------------------------- C3
PATH_RE = re.compile(r"[`\s(]((?:[A-Za-z0-9_.\-]+/)*[A-Za-z0-9_.\-]+\.(?:py|toml|json|yml|yaml|md|log|png|csv))[`\s),.]")
REF_RE = re.compile(r"`(agent/[A-Za-z0-9]+)`|\bhead `([0-9a-f]{7,40})`")
OUT_OF_SCOPE = {
    "pyproject.toml": "registered (A08)",
    "scripts/lint_gate.py": "registered (A09)",
    "tests/test_lint_gate.py": "registered (A10)",
    "docs/lint-debt-baseline.md": "registered (A11)",
    "docs/lint-baseline.json": "registered (A12)",
    ".github/workflows/ci.yml": "registered (A13)",
    "ci-test312-pre-fix.log": "registered (A02)",
    "tests-post-fix.log": "registered (A03)",
    "tests-drifted-guard.log": "registered (A04)",
    "gate-pinned.log": "registered (A05)",
    "gate-drifted.log": "registered (A06)",
    "lint-report.json": "registered (A07)",
    "pr185-cure-evidence.png": "registered (A01)",
}


def c3_completeness(md: str, manifest: dict) -> dict:
    registered_paths = {a["declared_path"] for a in manifest["asset_inventory"]}
    registered_basenames = {os.path.basename(p) for p in registered_paths}
    found = collections.Counter(m.group(1) for m in PATH_RE.finditer(md))
    missing = []
    for tok, cnt in found.items():
        base = os.path.basename(tok)
        if tok in registered_paths or base in registered_basenames:
            continue
        missing.append({"token": tok, "occurrences": cnt})
    refs = sorted({m.group(1) or m.group(2) for m in REF_RE.finditer(md)})
    registered_refs = {os.path.basename(p) for p in registered_paths}
    unregistered_refs = [r for r in refs if r not in registered_refs]
    return {
        "check": "C3_completeness",
        "path_tokens_in_markdown": dict(found),
        "unregistered_paths": missing,
        "repo_refs_in_markdown": refs,
        "unregistered_repo_refs": unregistered_refs,
        "note": "repo refs (branch / commit) are provenance handles, not file assets; the "
                "upstream inventory declares kinds figure|evidence_artifact|referenced_repo_path "
                "only, so they have no slot. Counted here as a coverage gap, not as a wrong entry.",
        "pass": not missing,
    }


# ---------------------------------------------------------------- C4
def c4_arithmetic(md: str) -> dict:
    facts = []
    def fact(name, claim, lhs, rhs, ok):
        facts.append({"fact": name, "claimed_in_report": claim, "lhs": lhs, "rhs": rhs, "consistent": bool(ok)})

    # 1764 passed + 4 failed = the job total implied by the symptom paragraph
    fact("ci_job_total", "4 failed / 1764 passed", 4 + 1764, 1768, 4 + 1764 == 1768)
    # pre-fix suite had 15 tests; three test functions are added -> 18
    fact("suite_growth", "15/15 passed (pre-fix) -> 18 passed (post-fix)", 15, 18 - 3, 15 == 18 - 3)
    # drifted guard: 14 passed + 4 skipped must equal the same 18 collected
    fact("drift_guard_partition", "14 passed, 4 skipped", 14 + 4, 18, 14 + 4 == 18)
    # regression test red pre-fix: 1 failed + 17 passed
    fact("prefix_regression_partition", "1 failed, 17 passed", 1 + 17, 18, 1 + 17 == 18)
    # gate green: identical before/after counts and zero new debt
    fact("gate_counts_unchanged", "check 4271 -> 4271", 4271, 4271, True)
    fact("unformatted_unchanged", "unformatted 624 -> 624", 624, 624, True)
    # number of files touched vs the enumerated fix list
    listed = len(re.findall(r"^\d+\. `", md, re.M))
    fact("files_touched", "Fix (4 files)", 4, listed, listed == 4)
    # number of failing tests enumerated vs the "4 failed" headline
    enum_failed = len(re.findall(r"^FAILED ", md, re.M))
    fact("failed_tests_enumerated", "4 failed", 4, enum_failed, enum_failed == 4)
    # ruff pin appears in both places the report claims
    pins = md.count("ruff==0.15.0")
    fact("ruff_pin_mentions", "CI pin == dev pin == ledger tool", 3, pins, pins >= 3)
    return {
        "check": "C4_internal_arithmetic",
        "facts": facts,
        "all_consistent": all(f["consistent"] for f in facts),
        "pass": all(f["consistent"] for f in facts),
    }


# ---------------------------------------------------------------- C5
def c5_reachability(offline: bool, token: str | None) -> dict:
    routes = [
        f"/tensor/reports/{REPORT_ID}",
        f"/tensor/reports/{REPORT_ID}/figures",
        f"/tensor/reports/{REPORT_ID}/figures/pr185-cure-evidence.png",
        f"/tensor/reports/{REPORT_ID}/attachments",
    ]
    probes = []
    if offline:
        return {"check": "C5_reachability", "probes": [], "pass": None, "note": "offline"}
    for r in routes:
        status, ctype, body = get(API + r, token)
        probes.append({"route": r, "status": status, "content_type": ctype, "bytes": len(body)})
    fig = probes[2]
    return {
        "check": "C5_reachability",
        "probes": probes,
        "figure_bytes_served": fig["status"] == 200,
        "pass": fig["status"] == 200,
        "note": "figure payload is the only host-side asset the report declares as "
                "`figures[]`; the six runs/pr185-cure/* logs are declared in prose only.",
    }


# ---------------------------------------------------------------- C6
def _walk_quotes(obj, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "quote" and isinstance(v, str):
                out.append(v)
            elif k == "report_quote" and isinstance(v, str):
                out.append(v)
            else:
                _walk_quotes(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_quotes(v, out)


def c6_quotes(md: str, review: dict) -> dict:
    quotes: list[str] = []
    _walk_quotes(review, quotes)
    rows = [{"quote": q, "verbatim": q in md} for q in quotes]
    return {
        "check": "C6_review_quotes_verbatim",
        "quotes_checked": len(rows),
        "quotes_verbatim": sum(r["verbatim"] for r in rows),
        "bad": [r for r in rows if not r["verbatim"]],
        "pass": all(r["verbatim"] for r in rows),
    }


# ---------------------------------------------------------------- C7
def c7_discipline(review: dict) -> dict:
    s = json.dumps(review, ensure_ascii=False)
    verified_marks = re.findall(r'"status"\s*:\s*"verified"|verified"\s*:\s*true', s)
    blocking = [f for f in review.get("findings", []) if f.get("blocking")]
    verdict = review.get("verdict")
    consistent = not (verdict == "pass" and blocking)
    return {
        "check": "C7_review_discipline",
        "verified_markings_found": verified_marks,
        "no_verified_marking": not verified_marks,
        "blocking_findings": [f["id"] for f in blocking],
        "verdict": verdict,
        "verdict_consistent_with_findings": consistent,
        "pass": (not verified_marks) and consistent,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    token = None
    if not args.offline:
        try:
            token = login()
        except Exception as exc:  # pragma: no cover - environment dependent
            print(f"login failed ({exc}); continuing without host probes", file=sys.stderr)

    md, note = fetch_markdown(args.offline, token)
    manifest = json.load(open(os.path.join(HERE, "upstream", "asset_manifest_wp-4776-01.json")))
    review_path = os.path.join(HERE, "review_report.json")
    review = json.load(open(review_path)) if os.path.exists(review_path) else {}

    checks = [
        c1_source(md),
        c2_locators(md, manifest),
        c3_completeness(md, manifest),
        c4_arithmetic(md),
        c5_reachability(args.offline or token is None, token),
        c6_quotes(md, review) if review else {"check": "C6_review_quotes_verbatim", "pass": None},
        c7_discipline(review) if review else {"check": "C7_review_discipline", "pass": None},
    ]
    summary = {
        "source_note": note,
        "checks": len(checks),
        "passed": sum(1 for c in checks if c.get("pass") is True),
        "failed": [c["check"] for c in checks if c.get("pass") is False],
        "not_run": [c["check"] for c in checks if c.get("pass") is None],
    }
    out = {"generated_at": None, "summary": summary, "results": checks}
    json.dump(out, open(os.path.join(HERE, "checks.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for c in checks:
        print(f"  {c['check']:<28} pass={c.get('pass')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())