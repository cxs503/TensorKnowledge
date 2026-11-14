"""wp-9246-02 回归测试：不依赖网络，直接对已落盘产物校验 acceptance 不变量。

跑：python3 -m pytest tests/test_kf_wp9246_02.py -q
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "production" / "wp-9246-02"
MIRROR = REPO / "artifacts" / "wp-9246-02"
FIXTURE = REPO / "tests" / "fixtures" / "kf" / "wp-9246-02" / "source_markdown.md"
DECLARED_HASH = "sha256:80bcb3216845e02d844926b8d2e733882e8de69ebd756ff706296a8ab3e165b5"

pytestmark = pytest.mark.skipif(
    not (OUT / "kf_result.json").exists(),
    reason="wp-9246-02 artifacts not built (run scripts/kf/kf9246_build.py)")


def _h(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads((OUT / "kf_result.json").read_text())


@pytest.fixture(scope="module")
def cls(result) -> dict:
    return result["outputs"]["classification.json"]


@pytest.fixture(scope="module")
def md() -> str:
    """源报告快照（带哈希的测试夹具；缺失则跳过，绝不静默用别的文件顶替）。"""
    for cand in (FIXTURE, MIRROR / "source_markdown.md"):
        if cand.exists():
            return cand.read_text()
    pytest.skip("source markdown snapshot missing (run scripts/kf/kf9246_build.py)")


def test_envelope_matches_schema(result):
    from jsonschema import Draft202012Validator
    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text())
    assert list(Draft202012Validator(schema).iter_errors(result)) == []


def test_package_identity(result):
    assert result["package_id"] == "wp-9246-02"
    assert result["task_type"] == "02-classification-parse"
    assert result["report_id"] == "9246"
    assert result["provenance"]["source_uri"] == "tensor://reports/9246"


def test_source_hash_matches_snapshot(result, md):
    assert _h(md) == result["provenance"]["source_hash"] == DECLARED_HASH
    assert len(md) == result["provenance"]["chars"] == 11250


def test_every_quote_resolves_verbatim(cls, md):
    for ev in cls["evidence"]:
        loc = ev["locator"]
        assert loc["quote"] in md, ev["id"]
        assert md.find(loc["quote"]) == loc["start_offset"], ev["id"]
        assert md[loc["start_offset"]:loc["end_offset"]] == loc["quote"], ev["id"]
        assert _h(loc["quote"]) == loc["content_hash"], ev["id"]
        assert loc["chars"] >= 12, ev["id"]


def test_ids_unique(cls):
    ids = ([e["id"] for e in cls["evidence"]]
           + [d["id"] for d in cls["decision_basis"]]
           + [u["id"] for u in cls["unresolved"]])
    assert len(ids) == len(set(ids))


def test_every_decision_bound_to_resolvable_evidence(cls):
    ev = {e["id"] for e in cls["evidence"]}
    ur = {u["id"] for u in cls["unresolved"]}
    for d in cls["decision_basis"]:
        assert d["evidence"], d["id"]
        assert set(d["evidence"]) <= ev, d["id"]
    for rows in cls["signals"]["step_fit"].values():
        for step in rows["steps"]:
            assert not step["evidence"] or step["evidence"] in ev | ur


def test_no_claim_or_conclusion_marked_verified(cls):
    blob = json.dumps(cls, ensure_ascii=False)
    assert '"verified"' not in blob
    assert '"verification_status"' not in blob
    for status in re.findall(r'"assessment_status"\s*:\s*"([^"]*)"', blob):
        assert status == "unassessed"
    for epistemic in re.findall(r'"epistemic_status"\s*:\s*"([^"]*)"', blob):
        assert epistemic == "draft"


def test_classification_decision_is_internally_consistent(cls):
    primary = cls["report_type"]["primary"]
    trace = cls["report_type"]["decision_trace"]
    sig = cls["signals"]["per_type"]
    assert primary in trace["eligible_after_R1"]
    assert sig[primary]["hits"] >= 2
    assert cls["signals"]["step_fit"][primary]["all_satisfiable"]
    assert cls["report_type"]["status"] in ("classified", "unclassified")
    assert cls["report_type"]["classification_is_hypothesis"] is True


def test_scope_lock_single_report_id(cls):
    guard = cls["scope_guard"]
    assert guard["report_ids_read"] == ["9246"]
    assert guard["report_ids_written"] == ["9246"]
    assert guard["upstream_artifacts_modified"] == []


def test_report_has_exactly_one_json_block_equal_to_envelope(result):
    text = (OUT / "KF-RESULT-wp-9246-02.md").read_text()
    blocks = re.findall(r"```json\n(.*?)\n```", text, flags=re.S)
    assert len(blocks) == 1
    assert text.count("```") == 2
    assert json.loads(blocks[0]) == result
    assert text.startswith("# KF-RESULT wp-9246-02\n")
    for sec in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥", "repro_cmd"):
        assert sec in text


def test_checks_json_all_passed():
    checks = json.loads((OUT / "checks.json").read_text())
    failed = [c["check"] for c in checks["checks"] if c["status"] != "passed"]
    assert checks["ok"] is True and failed == []