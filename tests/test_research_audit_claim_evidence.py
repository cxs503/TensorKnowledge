from scripts.research_audit.claim_evidence_audit import audit_claim_evidence


def _bundle(tmp_path, *, quote="verified source sentence", status="unassessed", relation="supports"):
    import hashlib
    import json

    claims = tmp_path / "claims"
    evidence = tmp_path / "evidence"
    sources = tmp_path / "sources"
    for directory in (claims, evidence, sources):
        directory.mkdir()
    source_text = "Preamble. verified source sentence. End."
    (sources / "paper.txt").write_text(source_text, encoding="utf-8")
    start = source_text.index("verified source sentence")
    claim_id = "tkc:test:claim-one"
    evidence_id = "tke:test:evidence-one"
    claim = {
        "id": claim_id,
        "statement": "A test claim.",
        "claim_type": "descriptive",
        "epistemic_status": "draft",
        "evidence_refs": [evidence_id],
        "created_at": "2026-01-01T00:00:00Z",
        "version": "1.0.0",
    }
    evidence_record = {
        "id": evidence_id,
        "claim_refs": [claim_id],
        "source": {"source_type": "paper", "citation": "paper.txt"},
        "relation": relation,
        "locator": {
            "locator_type": "paragraph",
            "value": "paragraph 1",
            "start_offset": start,
            "end_offset": start + len(quote),
            "quote": quote,
            "content_hash": hashlib.sha256(quote.encode()).hexdigest(),
        },
        "captured_at": "2026-01-01T00:00:00Z",
        "assessment_status": status,
        "version": "1.0.0",
    }
    (claims / "claim.json").write_text(json.dumps(claim), encoding="utf-8")
    (evidence / "evidence.json").write_text(json.dumps(evidence_record), encoding="utf-8")
    return claims, evidence, sources


def test_valid_but_unreviewed_evidence_is_inconclusive(tmp_path):
    claims, evidence, sources = _bundle(tmp_path)
    report = audit_claim_evidence(claims, evidence, sources)
    assert report["overall_status"] == "inconclusive"
    assert report["counts"]["pending_review"] == 1
    assert all(check["state"] == "passed" for check in report["checks"])


def test_reviewed_relation_can_pass(tmp_path):
    claims, evidence, sources = _bundle(tmp_path, status="reviewed-supports")
    report = audit_claim_evidence(claims, evidence, sources)
    assert report["overall_status"] == "passed"


def test_quote_offset_mismatch_fails_closed(tmp_path):
    claims, evidence, sources = _bundle(tmp_path, quote="not the source text")
    report = audit_claim_evidence(claims, evidence, sources)
    assert report["overall_status"] == "failed"
    assert any(f["check_id"] == "quote_offset_mismatch" for f in report["findings"])


def test_relation_review_conflict_fails(tmp_path):
    claims, evidence, sources = _bundle(tmp_path, status="reviewed-refutes", relation="supports")
    report = audit_claim_evidence(claims, evidence, sources)
    assert report["overall_status"] == "failed"
    assert any(f["check_id"] == "relation_review_conflict" for f in report["findings"])


def test_source_path_escape_fails(tmp_path):
    claims, evidence, sources = _bundle(tmp_path)
    import json
    path = next(evidence.glob("*.json"))
    record = json.loads(path.read_text())
    record["source"]["citation"] = "../outside.txt"
    path.write_text(json.dumps(record))
    report = audit_claim_evidence(claims, evidence, sources)
    assert report["overall_status"] == "failed"
    assert any(f["check_id"] == "source_path_escape" for f in report["findings"])


def test_nonreciprocal_link_fails(tmp_path):
    claims, evidence, sources = _bundle(tmp_path)
    import json
    path = next(evidence.glob("*.json"))
    record = json.loads(path.read_text())
    record["claim_refs"] = []
    path.write_text(json.dumps(record))
    report = audit_claim_evidence(claims, evidence, sources)
    assert report["overall_status"] == "failed"
    assert any(f["check_id"] == "evidence_without_claim" for f in report["findings"])
