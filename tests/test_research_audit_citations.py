from scripts.research_audit.citation_audit import audit_markdown


def _write(tmp_path, content):
    path = tmp_path / "report.md"
    path.write_text(content, encoding="utf-8")
    return path


def test_citation_audit_passes_resolved_numeric_references(tmp_path):
    path = _write(tmp_path, """# Findings

A result is supported by the cited method [1]. Another statement cites two sources [1, 2].

## References
[1] Author A. Method paper. DOI: 10.1000/example1
[2] Author B. Dataset paper. https://example.org/paper2
""")
    report = audit_markdown(path)
    assert report["overall_status"] == "passed"
    assert report["summary"]["distinct_citations"] == 2
    assert report["summary"]["unresolved_citations"] == []
    assert all(check["state"] == "passed" for check in report["checks"])


def test_citation_audit_finds_unresolved_citation(tmp_path):
    path = _write(tmp_path, """# Findings

This statement cites a missing source [7].

## References
[1] Author A. Existing reference.
""")
    report = audit_markdown(path)
    assert report["overall_status"] == "failed"
    assert report["summary"]["unresolved_citations"] == ["7"]
    assert any(f["check_id"] == "unresolved_citation" for f in report["findings"])


def test_citation_audit_finds_duplicate_and_unused_references(tmp_path):
    path = _write(tmp_path, """# Findings

Only source [1] is cited.

## References
[1] Author A. First entry.
[1] Author A. Duplicate entry.
[2] Author B. Never cited.
""")
    report = audit_markdown(path)
    assert report["overall_status"] == "failed"
    assert report["summary"]["duplicate_reference_ids"] == ["1"]
    assert report["summary"]["unused_references"] == ["2"]


def test_citation_audit_is_inconclusive_without_bibliography_heading(tmp_path):
    path = _write(tmp_path, """# Findings

A claim cites [1], but the document has no recognizable references heading.
""")
    report = audit_markdown(path)
    assert report["overall_status"] == "inconclusive"
    assert report["checks"][0]["state"] == "inconclusive"
