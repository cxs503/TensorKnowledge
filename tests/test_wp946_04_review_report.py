"""Offline regression tests for the wp-946-04 independent review of wp-946-01.

These re-derive the review's load-bearing invariants from the committed artefacts only
(no network): report 946 markdown hash, verbatim locators, offset slices, counts, scope,
and the absence of any self-assigned "verified" status.

Run: python3 -m pytest tests/test_wp946_04_review_report.py -q
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-946-04"
CONTRACT_HASH = "sha256:3ea029afd6df49a8d3e407e42df035654b58a7555f9678d657f5fdfc1fe35552"
CONTRACT_CHARS = 14281


def _load(name: str) -> dict:
    return json.loads((PKG / name).read_text(encoding="utf-8"))


def test_review_report_is_valid_json_and_envelope_shaped():
    r = _load("review_report.json")
    assert r["package_id"] == "wp-946-04"
    assert r["task_type"] == "04-independent-review"
    assert r["report_id"] == "946"
    assert r["review_target"]["package_id"] == "wp-946-01"
    assert r["verdict"] in ("pass", "needs-fix")
    assert r["decision"] in ("approve", "request-changes")
    assert r["checks"], "no checks recorded"


def test_all_checks_pass_and_none_is_silently_skipped():
    r = _load("review_report.json")
    statuses = {c["check_id"]: c["status"] for c in r["checks"]}
    assert r["verdict"] == "pass"
    assert r["blocking_failures"] == []
    assert all(s in ("pass", "not_run") for s in statuses.values())
    # every check id C01..C19 present
    assert len([k for k in statuses if re.fullmatch(r"C\d+", k)]) >= 19


def test_source_hash_recomputes_from_committed_markdown():
    md = (PKG / "source_report.md").read_text(encoding="utf-8")
    assert "sha256:" + hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    upstream = _load("upstream/wp-946-01.kf_result.json")
    assert upstream["provenance"]["source_hash"] == CONTRACT_HASH


def test_every_markdown_locator_is_verbatim_and_offsets_agree():
    md = (PKG / "source_report.md").read_text(encoding="utf-8")
    upstream = _load("upstream/wp-946-01.kf_result.json")
    assets = upstream["outputs"]["asset_manifest.json"]["assets"]
    n = 0
    for a in assets:
        for loc in a.get("locators", []):
            if loc.get("source_field") != "markdown":
                continue
            n += 1
            q = loc["quote"]
            assert q in md, (a["asset_id"], q[:60])
            if loc.get("char_start") is not None:
                assert md[loc["char_start"]:loc["char_end"]] == q, a["asset_id"]
            assert md.count(q) == loc["occurrences"], a["asset_id"]
    assert n == 25


def test_manifest_counts_recompute():
    upstream = _load("upstream/wp-946-01.kf_result.json")
    man = upstream["outputs"]["asset_manifest.json"]
    assets = man["assets"]
    kinds: dict[str, int] = {}
    for a in assets:
        kinds[a["kind"]] = kinds.get(a["kind"], 0) + 1
    assert man["counts"]["total"] == len(assets) == 22
    assert man["counts"]["by_kind"] == kinds
    assert man["counts"]["resolvable"] == sum(a["status"] == "resolvable" for a in assets)
    assert len({a["asset_id"] for a in assets}) == len(assets)
    assert all(a.get("unresolved_reason") for a in assets if a["status"] == "unresolved")


def test_scope_is_single_report_and_no_self_verification():
    upstream = _load("upstream/wp-946-01.kf_result.json")
    text = json.dumps(upstream, ensure_ascii=False)
    assert sorted(set(re.findall(r"reports/(\d+)", text))) == ["946"]
    man = upstream["outputs"]["asset_manifest.json"]
    assert man["verification"]["performed"] is False
    assert man["extraction"]["performed"] is False
    assert upstream["claims"] == []
    assert not any(a["status"] not in ("resolvable", "unresolved") for a in man["assets"])
    assert '"verified"' not in text


def test_review_never_reads_producer_explanation():
    """The reviewer's declared context must stay inside report + upstream deliverable."""
    r = _load("review_report.json")
    excluded = " ".join(r["reviewer"]["excluded"])
    for banned in ("report.md", "make_report.py", "build_asset_manifest.py"):
        assert banned in excluded