#!/usr/bin/env python3
"""Acceptance tests for wp-9645-02 (02-classification-parse on report 9645).

These assert invariants (not merely that code runs):
  * provenance.source_hash equals sha256 of the source snapshot AND the contract value;
  * every evidence locator re-slices the source by char/byte offset to the same quote;
  * every claim has resolvable evidence or an explicit unresolved status + reason;
  * ids are unique; the six-type classification never claims 'verified';
  * the delivered markdown carries exactly ONE fenced block = the kf_result envelope.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "kf", "wp-9645-02")
EXPECTED = "a8bb89020ad334b6b176aaa607852d61596fefcca86c8deaac6a22c6e2d8fb00"
REPORT_TYPES = {"literature-review", "scientific-computation", "algorithm-implementation",
                "software-engineering", "technical-proposal", "experimental-validation"}
MATCH_STATES = {"exact", "partial", "absent", "not_applicable"}


def _load(name):
    with open(os.path.join(OUT, name), encoding="utf-8") as f:
        return json.load(f)


def source_md():
    with open(os.path.join(OUT, "source_9645.md"), encoding="utf-8") as f:
        return f.read()


def test_source_hash_matches_contract():
    md = source_md()
    h = hashlib.sha256(md.encode("utf-8")).hexdigest()
    kf = _load("kf_result.json")
    assert h == EXPECTED
    assert kf["provenance"]["source_hash"] == "sha256:" + EXPECTED
    assert kf["provenance"]["source_hash_matches"] is True
    assert kf["provenance"]["chars"] == len(md)


def test_kf_result_envelope_schema_subset():
    kf = _load("kf_result.json")
    assert set(kf) == {"package_id", "task_type", "contract_version", "report_id",
                       "provenance", "outputs"}
    assert kf["package_id"] == "wp-9645-02"
    assert kf["task_type"] == "02-classification-parse"
    assert kf["contract_version"] == "1.0"
    assert kf["report_id"] == "9645"
    assert re.match(r"^(https?://\S+|file://\S+|tensor://\S+)$", kf["provenance"]["source_uri"])
    assert kf["provenance"]["source_field"] in {"markdown", "summary", "record"}
    assert "classification.json" in kf["outputs"]


def test_locators_resolve_against_source():
    md = source_md()
    raw = md.encode("utf-8")
    cls = _load("classification.json")
    locs = cls["evidence_locators"]
    assert len(locs) >= 20
    for lo in locs:
        assert md[lo["start_char"]:lo["end_char"]] == lo["quote"], lo["id"]
        assert raw[lo["byte_start"]:lo["byte_end"]].decode("utf-8") == lo["quote"], lo["id"]
        assert lo["quote"] in md, lo["id"]
        assert lo["content_hash"] == "sha256:" + hashlib.sha256(lo["quote"].encode("utf-8")).hexdigest()
        assert lo["resolvable"] is True


def test_no_duplicate_ids():
    cls = _load("classification.json")
    cids = [c["id"] for c in cls["claims"]]
    lids = [lo["id"] for lo in cls["evidence_locators"]]
    uids = [u["id"] for u in cls["unresolved"]]
    sids = [s["segment_id"] for s in cls["structural_segmentation"]]
    assert len(set(cids)) == len(cids)
    assert len(set(lids)) == len(lids)
    assert len(set(uids)) == len(uids)
    assert len(set(sids)) == len(sids)
    assert not set(cids) & set(lids)


def test_every_claim_has_evidence_or_is_explicitly_unresolved():
    cls = _load("classification.json")
    lids = {lo["id"] for lo in cls["evidence_locators"]}
    for c in cls["claims"]:
        assert c["status"] in {"supported", "unresolved"}, c["id"]
        if c["status"] == "supported":
            assert c["locator_ids"], c["id"]
        else:
            assert c.get("unresolved_reason"), c["id"]
        for r in c["locator_ids"]:
            assert r in lids, (c["id"], r)


def test_classification_declares_type_and_skill():
    cls = _load("classification.json")
    rt = cls["report_type"]
    assert rt["primary"] in REPORT_TYPES
    assert 0.0 <= rt["confidence"] <= 1.0
    assert rt["primary"] not in {a["report_type"] for a in rt["alternatives"]}
    for a in rt["alternatives"]:
        assert a["report_type"] in REPORT_TYPES
    assert cls["selected_skill"]["skill_id"] == "xsk-scientific-computation"
    for s in cls["selected_skill"]["signal_match"] + cls["secondary_type_signals"]["signal_match"]:
        assert s["matched"] in MATCH_STATES, s


def test_no_verified_marking_and_uncertainty_preserved():
    blob = json.dumps(_load("classification.json"), ensure_ascii=False)
    kf = json.dumps(_load("kf_result.json"), ensure_ascii=False)
    assert '"verified": true' not in blob and '"verified": true' not in kf
    assert '"status": "verified"' not in blob
    cls = _load("classification.json")
    assert cls["unresolved"], "uncertainty must be preserved, not dropped"
    assert cls["constraints_compliance"]["do_not_mark_claims_as_verified"] is True


def test_segments_cover_source_monotonically():
    md = source_md()
    segs = _load("classification.json")["structural_segmentation"]
    assert segs and segs[0]["char_start"] == 0
    for s in segs:
        assert md[s["char_start"]:s["char_end"]].startswith(s["heading"]), s["segment_id"]
    for a, b in zip(segs, segs[1:]):
        assert a["char_end"] == b["char_start"]


def test_delivered_markdown_has_exactly_one_json_block_equal_to_envelope():
    path = os.path.join(OUT, "KF-RESULT.wp-9645-02.md")
    with open(path, encoding="utf-8") as f:
        body = f.read()
    blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
    assert len(blocks) == 1, "delivery channel allows exactly one json block"
    assert body.count("```") == 2
    assert blocks[0] == json.dumps(_load("kf_result.json"), ensure_ascii=False, indent=2)
    for heading in ("① ", "② ", "③ ", "④ ", "⑤ ", "⑥ "):
        assert heading in body, heading


def test_selfcheck_all_pass():
    chk = _load("report_selfcheck.json")
    assert chk["all_pass"] is True
    items = {c["acceptance_item"] for c in chk["checks"]}
    assert items == {"valid_json", "schema_pass", "source_locator_resolvable",
                     "source_hash_matches", "no_duplicate_ids",
                     "all_claims_have_evidence_or_explicit_unresolved_status"}


def test_payload_is_publishable_and_scoped_to_9645():
    p = _load("platform_payload.json")
    assert p["title"] == "KF-RESULT wp-9645-02"
    assert "kf-wp:wp-9645-02" in p["tags"]
    assert p["mission_id"] == 19801
    assert p["markdown"].count("```") == 2
    other_ids = set(re.findall(r"tensor://reports/(\w+)", p["markdown"]))
    assert other_ids <= {"9645"}, other_ids

# --- zero-hand-copying guard: source facts quoted in claims must live in the cited quote.
# Numbers that belong to this classification itself (confidence / alternative weight) are
# exempt; anything else must be findable verbatim in at least one cited locator.
OWN_CONFIDENCE = {"0.40", "0.20", "0.05", "0.85", "0.70", "0.60", "0.65", "0.90", "0.95", "0.75"}


def test_claim_numbers_are_locatable_in_their_own_evidence():
    cls = _load("classification.json")
    quotes = {lo["id"]: lo["quote"] for lo in cls["evidence_locators"]}
    for c in cls["claims"]:
        blob = " ".join(quotes[r] for r in c["locator_ids"])
        for tok in re.findall(r"\d+\.\d+|\d+/\d+|\d{2,}", c["statement"]):
            if tok in OWN_CONFIDENCE or tok.startswith("9645"):
                continue
            assert tok in blob, (c["id"], tok, blob[:120])


def test_report_numbers_are_injected_from_artifacts():
    cls = _load("classification.json")
    with open(os.path.join(OUT, "KF-RESULT.wp-9645-02.md"), encoding="utf-8") as f:
        body = f.read()
    assert "%d 条逐字定位器" % cls["counts"]["evidence_locators"] in body
    assert "结构切分 %d 段" % cls["counts"]["segments"] in body
    assert cls["source"]["source_hash"][7:] in body          # full sha256, injected
    assert "source_hash_matches=True" in body
    assert "chars=%d" % cls["source"]["chars"] in body
    # every locator quote shown in the evidence table must be a real source substring
    md = source_md()
    for lo in cls["evidence_locators"]:
        assert lo["quote"][:40] in md


def test_evidence_is_non_redundant_and_fully_wired():
    """Adversarial guard: no duplicate quotes, no nesting, no orphan evidence."""
    cls = _load("classification.json")
    quotes = [lo["quote"] for lo in cls["evidence_locators"]]
    assert len(set(quotes)) == len(quotes), "duplicate quotes = padding"
    for a in quotes:
        for b in quotes:
            if a != b:
                assert a not in b, "nested quotes make naive substring resolution ambiguous"
    used = set()
    for c in cls["claims"]:
        used |= set(c["locator_ids"])
    for t in cls["topic_tags"]:
        used |= set(t["locator_ids"])
    used |= set(cls["domain_labels"]["discipline_locator_ids"])
    for a in cls["report_type"]["alternatives"]:
        used |= set(a["locator_ids"])
    for s in cls["selected_skill"]["signal_match"] + cls["secondary_type_signals"]["signal_match"]:
        used |= set(s["locator_ids"])
    allids = {lo["id"] for lo in cls["evidence_locators"]}
    assert allids - used == set(), "orphan locators: %s" % sorted(allids - used)
    assert used - allids == set()


def test_counts_are_consistent_with_content():
    cls = _load("classification.json")
    c = cls["counts"]
    assert c["claims"] == len(cls["claims"])
    assert c["claims_supported"] == sum(1 for x in cls["claims"] if x["status"] == "supported")
    assert c["claims_unresolved"] == sum(1 for x in cls["claims"] if x["status"] == "unresolved")
    assert c["evidence_locators"] == len(cls["evidence_locators"])
    assert c["segments"] == len(cls["structural_segmentation"])
    assert c["topic_tags"] == len(cls["topic_tags"])
    assert c["unresolved_items"] == len(cls["unresolved"])
