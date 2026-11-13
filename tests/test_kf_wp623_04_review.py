"""Offline regression tests for the wp-623-04 independent review of report 623.

No network here: the shipped copy of the source markdown is the reference, so
the same assertions the reviewer ran online can be re-checked in CI.

Deliberate honesty: the work-package.json schema test asserts the *known,
declared* conflict between the owner YAML (review.required/independent_reviewer
= false) and schemas/work-package-contract.schema.json's 04 branch (both const
true). If that conflict is ever resolved upstream, the test tells us which way.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs/kf/wp-623-04"
UP = ROOT / "docs/kf/wp-623-01"
SRC = ROOT / "work/w623/source_623.md"
SCHEMAS = ROOT / "schemas"

sys.path.insert(0, str(ROOT / "scripts"))
from ke_state_machine import fold, submit  # noqa: E402


def _json(p: Path):
    return json.loads(p.read_text())


def _errors(schema_name: str, doc) -> list[str]:
    schema = _json(SCHEMAS / schema_name)
    return [e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(doc)]


def test_source_copy_hash_matches_contract_and_envelope():
    src = SRC.read_text()
    digest = "sha256:" + hashlib.sha256(src.encode("utf-8")).hexdigest()
    contract = _json(PKG / "work-package.json")
    envelope = _json(PKG / "kf_result.json")
    assert digest == contract["input"]["source_hash"]
    assert digest == envelope["provenance"]["source_hash"]
    assert envelope["report_id"] == "623"


def test_envelope_is_schema_valid():
    assert _errors("kf_result.v1.schema.json", _json(PKG / "kf_result.json")) == []


def test_review_events_are_schema_valid_and_fold_to_approved():
    events = _json(PKG / "review_events.json")
    for ev in events:
        assert _errors("review-event.schema.json", ev) == []
    obj = {"producer_ids": ["kf-worker/m15515"]}
    state, codes = fold(events, obj, initial_state=submit(obj, "draft"))
    assert state == "approved"
    assert codes == ["OK_APPROVED"]


def test_producer_cannot_approve_own_package():
    """The same ledger with the producer as reviewer must be refused."""
    from ke_state_machine import StateMachineError

    events = _json(PKG / "review_events.json")
    bad = json.loads(json.dumps(events))
    bad[0]["reviewer"]["id"] = "kf-worker/m15515"
    obj = {"producer_ids": ["kf-worker/m15515"]}
    with pytest.raises(StateMachineError):
        fold(bad, obj, initial_state="in-review")


def test_every_review_quote_is_verbatim_on_its_declared_line():
    lines = SRC.read_text().rstrip("\n").split("\n")
    rr = _json(PKG / "review_report.json")
    n = 0
    for finding in rr["findings"]:
        assert finding["evidence"], finding["finding_id"]
        assert finding["reproduction"], finding["finding_id"]
        for ev in finding["evidence"]:
            if not ev["quote"]:
                assert ev.get("note"), "an empty quote must be documented as such"
                continue
            n += 1
            assert ev["quote"] in lines[ev["line"] - 1], (finding["finding_id"], ev["line"])
            assert ev["quote_sha256"] == (
                "sha256:" + hashlib.sha256(lines[ev["line"] - 1].encode("utf-8")).hexdigest())
    assert n >= 10


def test_body_citations_resolve_against_source_lines():
    md = (PKG / "KF-RESULT-wp-623-04.md").read_text()
    lines = SRC.read_text().rstrip("\n").split("\n")
    cites = re.findall(r"L(\d+) ▸ 「(.+?)」", md)
    assert len(cites) >= 10
    for lineno, quote in cites:
        assert quote in lines[int(lineno) - 1], (lineno, quote)


def test_deliverable_has_one_json_block_equal_to_envelope():
    md = (PKG / "KF-RESULT-wp-623-04.md").read_text()
    blocks = re.findall(r"```json\n(.*?)\n```", md, flags=re.S)
    assert len(blocks) == 1
    envelope = _json(PKG / "kf_result.json")
    assert json.loads(blocks[0]) == envelope
    assert md.splitlines()[0] == "# KF-RESULT wp-623-04"
    for marker in ("① 本工序做了什么", "② 怎么做的", "③ 产出物清单",
                   "④ 证据定位表", "⑤ 注意点与局限", "⑥ 自检"):
        assert marker in md


def test_no_claim_is_marked_verified():
    rr = _json(PKG / "review_report.json")
    assert "verified" not in rr["verdict"]
    blob = json.dumps(_json(PKG / "kf_result.json")["outputs"], ensure_ascii=False)
    for marker in ("is_verified", "verification_status", "verification_level"):
        assert f'"{marker}"' not in blob


def test_work_package_schema_conflict_is_the_only_failure():
    """Known conflict, declared: exactly the two review const clauses fail."""
    errs = _errors("work-package-contract.schema.json", _json(PKG / "work-package.json"))
    assert errs == ["True was expected", "True was expected"], errs
    wp = _json(PKG / "work-package.json")
    assert wp["review"] == {"required": False, "independent_reviewer": False,
                            "reviewer_role": "red-team-reviewer"}
    assert wp["input"]["reviewed_package"]["package_id"] == "wp-623-01"


def test_upstream_package_identity_is_reproducible():
    """The reviewed artefact itself: hash + locator counts, not a restatement."""
    man = _json(UP / "asset_manifest.json")
    src = SRC.read_text()
    assert "sha256:" + hashlib.sha256(src.encode("utf-8")).hexdigest() == man["source"]["source_hash"]
    assert man["source"]["chars"] == len(src)
    assert man["counts"]["assets_total"] == len(man["assets"]) == 16
    assert man["counts"]["locators"] == len(man["locators"]) == 17
    ok = 0
    for a in man["assets"]:
        loc = a.get("locator") or {}
        if loc.get("quote") and loc.get("line"):
            assert src.rstrip("\n").split("\n")[loc["line"] - 1].count(loc["quote"]) >= 1
            ok += 1
    # 16 assets = 1 markdown (no quote: the document itself) + 2 embedded figures
    # (record pointer, metadata_only) + 13 body references; the 13 references carry
    # the quotable locators, 2 of which share one source line (line 53).
    assert ok == 13
    vac = [f for f in man["identity_facts"] if not f["quote"]]
    assert [f["fact_id"] for f in vac] == ["closing-note"]   # F-02, still unfixed upstream
