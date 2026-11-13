"""Retrieval-facing four-dimension projection over KE records.

The storage contract (``ke/contract.py``) is *record shaped*: claims carry a
statement + scope, evidence carries source/locator/relation, provenance carries
an activity.  That shape answers "what was recorded", not "how would an agent
search for it".  Task KBM-TKC-INDEX-API asks for the missing retrieval plane:

    concept  — what is this object about   (domain / system / terms / tags)
    problem  — what open issue does it touch (gaps / questions / notes / limitations)
    method   — how was it established      (extraction method / source / activity)
    evidence — which evidence backs it     (evidence refs / relation / source type)

This module is a pure function library: it derives facet rows from a record and
has no knowledge of SQL or HTTP.  ``ke.apistore`` persists the rows into
``ke_facet`` and serves them; ``ke.api`` exposes ``/by-concept`` … ``/facets``.

Derivation rules are deliberately explicit and conservative (see
``docs/ke/retrieval-index.md``):

* verbatim identifiers (domain, system, evidence ids, extraction method, …)
  get high weight — they are exact needles;
* free text (statement / notes / quotes) is projected as tokens (ASCII words +
  CJK bigrams, same tokenizer as the KB read path) at lower weight — they let a
  concept query like ``poiseuille`` reach a statement, but never outrank an
  exact identifier hit;
* ``notes`` feed the *problem* dimension because in this corpus (and in the KE
  convention) notes hold gap anchors / "service improvement" items; a note is
  an open issue, not an established fact;
* an explicit ``facets`` object in the record is appended verbatim with the
  highest weight, so a producer can override any heuristic without code.

Nothing here is a truth claim: a facet is a *retrieval projection*, and every
row keeps the field it came from so a hit can always be traced back.
"""
from __future__ import annotations

import re

from .consume import tokenize

DIMS = ("concept", "problem", "method", "evidence")

MAX_VALUE = 240          # facet values are needles, not paragraphs
MAX_TOKENS = 24          # free-text token budget per object/field family
MAX_NOTE_TOKENS = 36

_WS = re.compile(r"\s+")

#: weight ladder — exact identifiers outrank free-text tokens by design
WEIGHTS = {
    "explicit": 1.5,      # record.facets[dim]
    "identifier": 1.0,    # domain / system / evidence id / method name
    "note": 0.8,          # notes (open issues)
    "attribute": 0.6,     # source_type / locator_type / assessment_status
    "token": 0.5,         # statement tokens
    "note_token": 0.4,    # notes tokens
}


def normalize(text: object) -> str:
    """Case-fold, collapse whitespace, cap length. Empty string if unusable."""
    if text is None:
        return ""
    s = _WS.sub(" ", str(text)).strip().lower()
    return s[:MAX_VALUE]


def _tokens(text: str, limit: int = MAX_TOKENS) -> list[str]:
    """Deterministic token list (sorted) from the shared tokenizer."""
    toks = sorted(t for t in tokenize(text or "") if len(t) >= 2)
    return toks[:limit]


def _add(out: list[dict], dim: str, value: object, field: str, weight: float) -> None:
    v = normalize(value)
    if not v:
        return
    out.append({"dim": dim, "value": v, "field": field, "weight": round(weight, 3)})


def _scope(doc: dict) -> dict:
    scope = doc.get("scope")
    return scope if isinstance(scope, dict) else {}


def project_doc(kind: str, doc: dict) -> list[dict]:
    """Derive ``[{dim, value, field, weight}]`` for one KE record.

    Deterministic: same record bytes -> same rows (sorted, de-duplicated by
    ``(dim, value, field)`` keeping the highest weight).
    """
    out: list[dict] = []

    # -- explicit producer facets (override surface) ---------------------
    explicit = doc.get("facets")
    if isinstance(explicit, dict):
        for dim in DIMS:
            vals = explicit.get(dim)
            if isinstance(vals, str):
                vals = [vals]
            if isinstance(vals, list):
                for v in vals:
                    _add(out, dim, v, "facets", WEIGHTS["explicit"])

    # -- concept ---------------------------------------------------------
    if kind == "claim":
        scope = _scope(doc)
        _add(out, "concept", scope.get("domain"), "scope.domain", WEIGHTS["identifier"])
        _add(out, "concept", scope.get("system"), "scope.system", WEIGHTS["identifier"])
        for i, cond in enumerate(scope.get("conditions") or []):
            _add(out, "concept", cond, f"scope.conditions[{i}]", WEIGHTS["attribute"])
        for key in ("tags", "concepts", "keywords"):
            vals = doc.get(key)
            if isinstance(vals, str):
                vals = [vals]
            if isinstance(vals, list):
                for v in vals:
                    _add(out, "concept", v, key, WEIGHTS["identifier"])
        for tok in _tokens(str(doc.get("statement") or "")):
            _add(out, "concept", tok, "statement.tokens", WEIGHTS["token"])

    # -- problem ---------------------------------------------------------
    if kind == "claim":
        if str(doc.get("claim_type") or "").lower() in ("question", "hypothesis"):
            _add(out, "problem", f"unresolved:{doc.get('claim_type')}", "claim_type",
                 WEIGHTS["identifier"])
            # an open question/hypothesis *is* a problem statement: its wording is
            # searchable in the problem dimension, not only in concept
            for tok in _tokens(str(doc.get("statement") or ""), MAX_NOTE_TOKENS):
                _add(out, "problem", tok, "statement.tokens", WEIGHTS["note_token"])
        for key in ("problem", "question", "hypothesis", "gap", "limitations"):
            vals = doc.get(key)
            if isinstance(vals, str):
                vals = [vals]
            if isinstance(vals, list):
                for i, v in enumerate(vals):
                    _add(out, "problem", v, f"{key}[{i}]", WEIGHTS["identifier"])
                    for tok in _tokens(str(v)):
                        _add(out, "problem", tok, f"{key}[{i}].tokens", WEIGHTS["note_token"])
        for key in ("next_actions",):
            vals = doc.get(key)
            if isinstance(vals, str):
                vals = [vals]
            if isinstance(vals, list):
                for i, v in enumerate(vals):
                    _add(out, "problem", v, f"{key}[{i}]", WEIGHTS["identifier"])
        for i, note in enumerate(doc.get("notes") or []):
            if not isinstance(note, str):
                continue
            _add(out, "problem", note, f"notes[{i}]", WEIGHTS["note"])
            for tok in _tokens(note, MAX_NOTE_TOKENS):
                _add(out, "problem", tok, f"notes[{i}].tokens", WEIGHTS["note_token"])

    # -- method ----------------------------------------------------------
    if kind == "evidence":
        _add(out, "method", doc.get("extraction_method"), "extraction_method",
             WEIGHTS["identifier"])
        src = doc.get("source") or {}
        loc = doc.get("locator") or {}
        _add(out, "method", src.get("source_type"), "source.source_type", WEIGHTS["attribute"])
        _add(out, "method", loc.get("locator_type"), "locator.locator_type", WEIGHTS["attribute"])
    if kind == "provenance":
        act = doc.get("activity") or {}
        _add(out, "method", act.get("activity_type"), "activity.activity_type",
             WEIGHTS["identifier"])
        _add(out, "method", doc.get("activity_type"), "activity_type", WEIGHTS["identifier"])
    if kind == "claim":
        for key in ("method", "methods"):
            vals = doc.get(key)
            if isinstance(vals, str):
                vals = [vals]
            if isinstance(vals, list):
                for v in vals:
                    _add(out, "method", v, key, WEIGHTS["identifier"])

    # -- evidence --------------------------------------------------------
    if kind == "claim":
        for i, eref in enumerate(doc.get("evidence_refs") or []):
            _add(out, "evidence", eref, f"evidence_refs[{i}]", WEIGHTS["identifier"])
    if kind == "evidence":
        _add(out, "evidence", doc.get("relation"), "relation", WEIGHTS["identifier"])
        src = doc.get("source") or {}
        loc = doc.get("locator") or {}
        _add(out, "evidence", src.get("source_type"), "source.source_type", WEIGHTS["identifier"])
        _add(out, "evidence", doc.get("assessment_status"), "assessment_status",
             WEIGHTS["attribute"])
        _add(out, "evidence", loc.get("locator_type"), "locator.locator_type", WEIGHTS["attribute"])
    if kind == "provenance":
        gen = doc.get("generated_entity") or {}
        if isinstance(gen, dict):
            _add(out, "evidence", gen.get("id"), "generated_entity.id", WEIGHTS["identifier"])
        for i, d in enumerate(doc.get("derived_from") or []):
            if isinstance(d, dict):
                _add(out, "evidence", d.get("id"), f"derived_from[{i}].id",
                     WEIGHTS["identifier"])
            elif isinstance(d, str):
                _add(out, "evidence", d, f"derived_from[{i}]", WEIGHTS["identifier"])

    # -- deterministic de-dup, keep max weight ---------------------------
    best: dict[tuple[str, str, str], dict] = {}
    for row in out:
        key = (row["dim"], row["value"], row["field"])
        prev = best.get(key)
        if prev is None or row["weight"] > prev["weight"]:
            best[key] = row
    return [best[k] for k in sorted(best)]


__all__ = ["DIMS", "WEIGHTS", "normalize", "project_doc"]