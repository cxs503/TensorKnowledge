"""Regression tests for the Knowledge-Engine evaluation package.

These tests do not need a framework install and do not touch the network:

  * the evaluation corpus validates against the repository's own schemas and
    its document locators resolve to the exact line the claim quotes;
  * the decision matrix is internally consistent (weights sum to 100, every
    option scores every dimension, the ranking matches the totals);
  * the thin layer's deterministic embedder is stable (same text -> same
    vector) so the hybrid-retrieval numbers in the report are reproducible.

Run: python -m pytest tests/test_ke_eval.py -q
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "demos" / "ke_eval"))

import tk_corpus  # noqa: E402
import score_matrix  # noqa: E402
from thinlayer import hashed_ngram_vec  # noqa: E402


def test_corpus_validates_against_repo_schemas():
    corpus = tk_corpus.build(REPO)
    report = tk_corpus.validate(REPO, corpus)
    assert {k: v["valid"] == v["records"] for k, v in report.items()} == \
           {k: True for k in report}, report
    assert len(corpus["claims"]) >= 20
    assert len(corpus["evidence"]) >= 20
    # evidence relations must cover the closed enum used by the contracts
    rels = {e["relation"] for e in corpus["evidence"]}
    assert {"supports", "refutes", "qualifies", "contextualizes"} <= rels


def test_document_locators_resolve_to_their_line():
    for rel_path, marker, _stmt, _rel, _ctype, _dom in tk_corpus.DOC_CLAIMS:
        line = tk_corpus._line_of(REPO / rel_path, marker)
        text = (REPO / rel_path).read_text(encoding="utf-8").splitlines()[line - 1]
        assert marker in text


def test_decision_matrix_is_consistent():
    weights = {d[0]: d[2] for d in score_matrix.DIMENSIONS}
    assert sum(weights.values()) == 100
    for opt, per in score_matrix.SCORES.items():
        assert set(per) == set(weights), f"{opt} missing/extra dimensions"
        for dim, (score, why, ref) in per.items():
            assert 1 <= score <= 5
            assert why and ref, f"{opt}/{dim} lacks justification or evidence pointer"


def test_matrix_numbers_match_artefact():
    out = REPO / "artifacts" / "ke_eval" / "decision_matrix.json"
    if not out.exists():
        subprocess.run([sys.executable, str(REPO / "demos/ke_eval/score_matrix.py")],
                       check=True, cwd=REPO, capture_output=True)
    d = json.loads(out.read_text())
    for opt, block in d["options"].items():
        recomputed = sum(r["score"] / 5 * r["weight"] for r in block["rows"])
        assert abs(recomputed - block["weighted_total"]) < 0.01
    assert d["ranking"] == sorted(d["ranking"],
                                  key=lambda k: -d["options"][k]["weighted_total"])


def test_embedder_is_deterministic_and_normalised():
    a = hashed_ngram_vec("provenance is a replaceable backend")
    b = hashed_ngram_vec("provenance is a replaceable backend")
    c = hashed_ngram_vec("temporal graph of evolving facts")
    assert a == b
    assert a != c
    assert abs(sum(x * x for x in a) - 1.0) < 1e-9
    assert len(a) == 256