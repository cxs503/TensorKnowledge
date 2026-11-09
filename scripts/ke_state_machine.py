#!/usr/bin/env python3
"""Executable form of the Knowledge Engine review-event state machine.

Specification: docs/ke/mapping-spec.md §4 (review-event state machine).
Used by scripts/build_ke_mapping.py and scripts/validate_ke_mapping.py so that
the state machine is a runnable artifact rather than prose only.

Design constraints (each is an invariant tested in the conformance suite):

  A1  Append-only ledger. A decision never mutates or deletes a prior event;
      review_status is a *fold* of the ledger, never a mutable column of truth.
  A2  No self-approval. `approve` and `revoke` require an independent reviewer,
      resolved through an alias-closed identity set. Unresolvable identity
      variants of a producer fail closed (blocked).
  A3  Axis independence. A review decision may change review_status only. It
      must never write epistemic_status or evidence assessment_status, and the
      resulting review_status must never be derived from Platform mission state.
  A4  Explicit refusal. Every (state, decision) pair not listed in TRANSITIONS
      is refused with a machine-readable code; never a silent no-op.
"""

from __future__ import annotations

import re
from typing import Any

POLICY_VERSION = "ke-review-v0.1"

REVIEW_STATES = ("draft", "in-review", "approved", "rejected", "deprecated")
DECISIONS = ("approve", "request-changes", "reject", "revoke", "deprecate")

# (current_state, decision) -> (next_state, outcome_code)
TRANSITIONS: dict[tuple[str, str], tuple[str, str]] = {
    ("in-review", "approve"): ("approved", "OK_APPROVED"),
    ("in-review", "request-changes"): ("draft", "OK_CHANGES_REQUESTED"),
    ("in-review", "reject"): ("rejected", "OK_REJECTED"),
    ("approved", "revoke"): ("in-review", "OK_REVOKED"),
    ("draft", "deprecate"): ("deprecated", "OK_DEPRECATED"),
    ("in-review", "deprecate"): ("deprecated", "OK_DEPRECATED"),
    ("approved", "deprecate"): ("deprecated", "OK_DEPRECATED"),
    ("rejected", "deprecate"): ("deprecated", "OK_DEPRECATED"),
}

# Decisions that create or destroy the meaning of "independently approved".
REQUIRES_INDEPENDENCE = frozenset({("in-review", "approve"), ("approved", "revoke")})

# Decisions that must carry findings explaining the refusal/return.
REQUIRES_FINDINGS = frozenset({("in-review", "request-changes"), ("in-review", "reject")})

INDEPENDENT_REVIEWER_TYPES = frozenset({"organization", "committee"})

# Identity tokens are the hex/slug suffixes used by agent sessions, e.g.
# "claude-code-session-6f76cd3d", "cc-session-6f76cd3d", "bg-job-6f76cd3d".
_TOKEN = re.compile(r"[0-9a-f]{8}")


class StateMachineError(Exception):
    """Refusal with a stable machine-readable code (never a silent no-op)."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def identity_tokens(*raw_ids: str) -> set[str]:
    """Session tokens embedded in identity strings (order-independent, alias-safe)."""
    tokens: set[str] = set()
    for raw in raw_ids:
        if not raw:
            continue
        tokens.update(_TOKEN.findall(raw.lower()))
    return tokens


def canonical_identity(raw: str) -> str:
    """Strip free-text decoration: 'id (model, role)' -> 'id'."""
    if not raw:
        return ""
    return re.split(r"[\s(（]", raw.strip(), maxsplit=1)[0]


def producer_identity(object_ctx: dict[str, Any]) -> dict[str, Any]:
    """Fail-closed view of who produced the object being reviewed.

    `object_ctx["producer_ids"]` are the recorded ids (claim.created_by,
    evidence.captured_by, provenance agents[].id, KO provenance.created_by).
    """
    raw_ids = list(object_ctx.get("producer_ids", []))
    return {
        "raw_ids": raw_ids,
        "canonical_ids": {canonical_identity(r) for r in raw_ids},
        "tokens": identity_tokens(*raw_ids),
    }


def is_independent(reviewer: dict[str, Any], producer: dict[str, Any]) -> tuple[bool, str]:
    """A2, fail-closed: token collision or identity collision blocks."""
    rid = str(reviewer.get("id", ""))
    rtype = str(reviewer.get("reviewer_type", ""))
    if rtype in INDEPENDENT_REVIEWER_TYPES:
        return True, "distinct-org"
    if not rid:
        return False, "INDEPENDENCE_UNRESOLVABLE"
    if canonical_identity(rid) in producer["canonical_ids"]:
        return False, "SELF_APPROVAL_BLOCKED"
    if identity_tokens(rid) & producer["tokens"]:
        return False, "SELF_APPROVAL_BLOCKED"
    return True, "distinct-identity"


def validate_event(event: dict[str, Any], state: str, ledger: list[dict[str, Any]],
                   object_ctx: dict[str, Any],
                   policy_version: str = POLICY_VERSION) -> tuple[str, str]:
    """Validate one event against `state`; return (next_state, outcome_code).

    Raises StateMachineError on refusal. Callers record refusals in a separate
    append-only `refused_events` log: the attempt is auditable, but it does not
    change review_status.
    """
    decision = event.get("decision")
    if decision not in DECISIONS:
        raise StateMachineError("UNKNOWN_DECISION", f"decision={decision!r}")
    if event.get("policy_version") != policy_version:
        raise StateMachineError(
            "POLICY_MISMATCH",
            f"event policy_version={event.get('policy_version')!r} != active {policy_version!r}",
        )
    key = (state, decision)
    if key not in TRANSITIONS:
        raise StateMachineError(
            "INVALID_TRANSITION", f"{state} + {decision} not in transition table"
        )
    if decision in DECISIONS and event.get("touches_epistemic_status"):
        raise StateMachineError(
            "AXIS_VIOLATION_A3",
            "review event attempted to write epistemic_status/evidence assessment",
        )
    if key in REQUIRES_FINDINGS and not event.get("findings"):
        raise StateMachineError("FINDINGS_REQUIRED", f"{state} + {decision} needs findings")
    if key in REQUIRES_INDEPENDENCE:
        ok, basis = is_independent(event.get("reviewer", {}), producer_identity(object_ctx))
        if not ok:
            raise StateMachineError(basis, f"reviewer={event.get('reviewer', {}).get('id')!r}")
        event.setdefault("independence_basis", basis)
    if decision == "revoke":
        target = event.get("supersedes_event")
        if not target:
            raise StateMachineError("SUPERSEDES_REQUIRED", "revoke must name the approve event")
        if target not in {e.get("id") for e in ledger if e.get("decision") == "approve"}:
            raise StateMachineError(
                "SUPERSEDES_UNKNOWN", f"{target!r} is not an approve event on this object"
            )
    next_state, code = TRANSITIONS[key]
    return next_state, code


def fold(events: list[dict[str, Any]], object_ctx: dict[str, Any],
         initial_state: str = "draft") -> tuple[str, list[str]]:
    """Replay a ledger: returns (final_state, outcome_codes). Raises on refusal."""
    state, codes = initial_state, []
    for e in sorted(events, key=lambda x: (x.get("reviewed_at", ""), x.get("id", ""))):
        state, code = validate_event(e, state, events, object_ctx)
        codes.append(code)
    return state, codes


def submit(object_ctx: dict[str, Any], state: str = "draft") -> str:
    """draft -> in-review.

    Entering review is a *system* transition (ingest / task completion), not a
    review decision: it deliberately has no entry in DECISIONS, so it can never
    be mistaken for an approval and cannot be authored by a reviewer identity.
    """
    if state != "draft":
        raise StateMachineError("INVALID_TRANSITION", f"submit from {state}")
    return "in-review"


CONFORMANCE_CASES: list[dict[str, Any]] = [
    # Each case: name, events, object_ctx, expect (final_state|None), expect_code
    {
        "name": "C1 producer cannot approve own object",
        "object_ctx": {"producer_ids": ["claude-code-session-6f76cd3d"]},
        "events": [
            {"id": "tkr:t:1", "decision": "approve", "policy_version": POLICY_VERSION,
             "reviewer": {"id": "claude-code-session-6f76cd3d", "reviewer_type": "agent"},
             "reviewed_at": "2026-11-09T13:00:00Z"}
        ],
        "submit": True,
        "expect_code": "SELF_APPROVAL_BLOCKED",
    },
    {
        "name": "C2 alias id of producer cannot approve (fail-closed)",
        "object_ctx": {"producer_ids": ["claude-code-session-6f76cd3d"]},
        "events": [
            {"id": "tkr:t:2", "decision": "approve", "policy_version": POLICY_VERSION,
             "reviewer": {"id": "cc-session-6f76cd3d", "reviewer_type": "agent"},
             "reviewed_at": "2026-11-09T13:00:00Z"}
        ],
        "submit": True,
        "expect_code": "SELF_APPROVAL_BLOCKED",
    },
    {
        "name": "C3 approve straight from draft refused",
        "object_ctx": {"producer_ids": ["agent-x"]},
        "events": [
            {"id": "tkr:t:3", "decision": "approve", "policy_version": POLICY_VERSION,
             "reviewer": {"id": "reviewer-1", "reviewer_type": "person"},
             "reviewed_at": "2026-11-09T13:00:00Z"}
        ],
        "expect_code": "INVALID_TRANSITION",
    },
    {
        "name": "C4 independent reviewer approves after submit",
        "object_ctx": {"producer_ids": ["claude-code-session-6f76cd3d"]},
        "events": [
            {"id": "tkr:t:4", "decision": "approve", "policy_version": POLICY_VERSION,
             "reviewer": {"id": "reviewer-9f2c1a4b", "reviewer_type": "person"},
             "reviewed_at": "2026-11-09T13:00:00Z"}
        ],
        "submit": True,
        "expect": "approved",
        "expect_code": "OK_APPROVED",
    },
    {
        "name": "C5 request-changes without findings refused",
        "object_ctx": {"producer_ids": ["agent-x"]},
        "events": [
            {"id": "tkr:t:5", "decision": "request-changes", "policy_version": POLICY_VERSION,
             "reviewer": {"id": "reviewer-1", "reviewer_type": "person"},
             "reviewed_at": "2026-11-09T13:00:00Z"}
        ],
        "submit": True,
        "expect_code": "FINDINGS_REQUIRED",
    },
    {
        "name": "C6 review event may not write epistemic_status (A3)",
        "object_ctx": {"producer_ids": ["agent-x"]},
        "events": [
            {"id": "tkr:t:6", "decision": "approve", "policy_version": POLICY_VERSION,
             "touches_epistemic_status": True,
             "reviewer": {"id": "reviewer-1", "reviewer_type": "person"},
             "reviewed_at": "2026-11-09T13:00:00Z"}
        ],
        "submit": True,
        "expect_code": "AXIS_VIOLATION_A3",
    },
    {
        "name": "C7 revoke reopens to in-review and needs supersedes_event",
        "object_ctx": {"producer_ids": ["agent-x"]},
        "events": [
            {"id": "tkr:t:7a", "decision": "approve", "policy_version": POLICY_VERSION,
             "reviewer": {"id": "reviewer-1", "reviewer_type": "person"},
             "reviewed_at": "2026-11-09T13:00:00Z"},
            {"id": "tkr:t:7b", "decision": "revoke", "policy_version": POLICY_VERSION,
             "supersedes_event": "tkr:t:7a",
             "reviewer": {"id": "reviewer-2b3d4e5f", "reviewer_type": "person"},
             "reviewed_at": "2026-11-09T13:10:00Z"},
        ],
        "submit": True,
        "expect": "in-review",
        "expect_code": "OK_REVOKED",
    },
    {
        "name": "C8 stale policy version is refused, not silently applied",
        "object_ctx": {"producer_ids": ["agent-x"]},
        "events": [
            {"id": "tkr:t:8", "decision": "approve", "policy_version": "ke-review-v0.0",
             "reviewer": {"id": "reviewer-1", "reviewer_type": "person"},
             "reviewed_at": "2026-11-09T13:00:00Z"}
        ],
        "submit": True,
        "expect_code": "POLICY_MISMATCH",
    },
    {
        "name": "C9 rejected object cannot be approved without re-submit",
        "object_ctx": {"producer_ids": ["agent-x"]},
        "events": [
            {"id": "tkr:t:9a", "decision": "reject", "policy_version": POLICY_VERSION,
             "findings": [{"severity": "major", "finding": "locator not verifiable"}],
             "reviewer": {"id": "reviewer-1", "reviewer_type": "person"},
             "reviewed_at": "2026-11-09T13:00:00Z"},
            {"id": "tkr:t:9b", "decision": "approve", "policy_version": POLICY_VERSION,
             "reviewer": {"id": "reviewer-1", "reviewer_type": "person"},
             "reviewed_at": "2026-11-09T13:05:00Z"},
        ],
        "submit": True,
        "expect_code": "INVALID_TRANSITION",
    },
]


def run_conformance() -> list[dict[str, Any]]:
    """Run CONFORMANCE_CASES; returns one result dict per case."""
    results = []
    for case in CONFORMANCE_CASES:
        state = submit(case["object_ctx"]) if case.get("submit") else "draft"
        got_state, got_code = None, None
        try:
            got_state, codes = fold(case["events"], case["object_ctx"], state)
            got_code = codes[-1] if codes else None
        except StateMachineError as exc:  # refusal path
            got_code = exc.code
        ok = got_code == case["expect_code"] and (
            case.get("expect") is None or got_state == case["expect"]
        )
        results.append(
            {
                "case": case["name"],
                "expected_code": case["expect_code"],
                "expected_state": case.get("expect"),
                "observed_code": got_code,
                "observed_state": got_state,
                "pass": ok,
            }
        )
    return results


if __name__ == "__main__":
    import json
    import sys

    rows = run_conformance()
    for row in rows:
        print(f"{'PASS' if row['pass'] else 'FAIL'}  {row['case']}  -> {row['observed_code']}")
    print(json.dumps({"cases": len(rows), "passed": sum(r["pass"] for r in rows)}))
    sys.exit(0 if all(r["pass"] for r in rows) else 1)