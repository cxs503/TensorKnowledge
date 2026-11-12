"""Three-gate validator for the report-to-knowledge production line.

Spec: ``docs/production/PRODUCTION-LINE-v1.md`` (gates) and
``docs/production/GATE-RULES.md`` (rule table with stable ids S*/E*/M*/V*).

The line has three gates and they are *not* interchangeable:

======== ============== ====================================================
gate     nature         implemented by
======== ============== ====================================================
G1       structural     this module, rules S*  (JSON / schema / id / fields)
G2       evidence       this module, rules E*  (locator resolvable in the
                        report text, quote matches, source_hash matches)
G3       semantic       an independent review agent + sampled strong model;
                        this module cannot pass it — it only prepares the
                        review request (M*) and refuses to claim the result
======== ============== ====================================================

Three axes are kept separate, and the separation is enforced, not documented:

* **mission state** (TensorPlatform: running/succeeded/failed) is never read
  here. A succeeded mission is not a pass, a failed mission is not a fail of
  the knowledge.
* **review state** is a fold of the append-only ``review_events.json`` ledger
  through ``scripts/ke_state_machine.py`` (reused, not re-implemented). No
  self-approval: a producer identity can never approve its own package.
* **verification level** (L0 declared / L1 structural / L2 evidence / L3
  verified) is *computed* by this module. L3 additionally requires a platform
  verification ticket marked ``confirmed`` and a matching claims digest; no
  agent-authored field can produce L3.

Reused assets (scope order: reuse KE + the four contracts, build no new
platform): ``scripts/sediment_lib.py`` (Checks accumulator + SchemaSet over
``schemas/*.schema.json``), ``scripts/ke_state_machine.py`` (review-event
state machine), ``schemas/claim-record|evidence-record|provenance-record``.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[1]
_SCHEMA_DIR = REPO_ROOT / "schemas"
_SCRIPTS = REPO_ROOT / "scripts"
if str(_SCRIPTS) not in sys.path:  # sediment_lib / ke_state_machine live here
    sys.path.insert(0, str(_SCRIPTS))

from ke_state_machine import (  # noqa: E402  (reuse: review axis)
    StateMachineError,
    fold as fold_review_events,
    is_independent,
    producer_identity,
    submit as submit_for_review,
)
from sediment_lib import Checks, SchemaSet  # noqa: E402  (reuse: schema + checks)

GATE_VERSION = "ko-gate-v1"

CONTRACT_SCHEMA = "work-package-contract.schema.json"
SUMMARY_SCHEMA = "extraction-summary.schema.json"
SKILL_SCHEMA = "extraction-skill.schema.json"
CONTRACT_FILE = "work-package.json"

#: filename -> (schema file, is a list of records?)
OUTPUT_SCHEMAS: dict[str, tuple[str, bool]] = {
    "claims.json": ("claim-record.schema.json", True),
    "evidence.json": ("evidence-record.schema.json", True),
    "provenance.json": ("provenance-record.schema.json", True),
    "extraction_summary.json": (SUMMARY_SCHEMA, False),
}
REQUIRED_OUTPUTS = tuple(OUTPUT_SCHEMAS)

REPORT_TYPES = (
    "literature-review",
    "scientific-computation",
    "algorithm-implementation",
    "software-engineering",
    "technical-proposal",
    "experimental-validation",
)

#: producer-side fields that must never reach the independent reviewer
#: ("审核者上下文=原文+知识对象，禁看生产者解释").
FORBIDDEN_REVIEW_KEYS = frozenset(
    {
        "extraction_summary",
        "self_assessment",
        "producer_rationale",
        "producer_notes",
        "producer_summary",
        "rationale",
        "why_i_did_this",
    }
)
REVIEW_CONTEXT_WHITELIST = ("source", "claims", "evidence", "provenance")

#: verification ladder — L3 is only reachable through a platform ticket.
VERIFICATION_LEVELS = ("L0", "L1", "L2", "L3")
LEVEL_MEANING = {
    "L0": "declared: records exist, nothing machine-checked",
    "L1": "structural: G1 (S* rules) passed",
    "L2": "evidence-bound: G1 + G2 (E* rules) passed",
    "L3": "verified: L2 + independent approval + platform verification ticket confirmed",
}


# ---------------------------------------------------------------------------
# source access — the evidence gate can only resolve what a resolver returns
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SourceDoc:
    """The source bytes a locator is resolved against."""

    report_id: str
    text: str
    uri: str
    field: str

    @property
    def sha256(self) -> str:
        return "sha256:" + hashlib.sha256(self.text.encode("utf-8")).hexdigest()


def canonical_record_text(record: dict) -> str:
    """``source_field="record"`` text: canonical JSON, stable across runs."""
    return json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def report_text(record: dict, field: str = "markdown") -> str:
    """Select the text a package declares its ``source_hash`` over.

    ``markdown`` is the canonical report body and the only field claims may be
    extracted from. A record without ``markdown`` falls back to ``summary`` so
    the gate reports a real hash mismatch instead of a missing source (the
    package must still have declared ``markdown``).
    """
    if field == "record":
        return canonical_record_text(record)
    if field == "summary":
        return str(record.get("summary") or "")
    text = record.get("markdown")
    if text is None:
        text = record.get("summary") or ""
    return str(text)


class SourceUnavailable(LookupError):
    """The resolver cannot reach the source; the evidence gate must fail closed."""


class DirSourceResolver:
    """Offline resolver over a directory of source documents.

    Accepted file names per report id: ``<id>.md`` (text as-is), ``<id>.txt``,
    ``<id>.json`` (report record; text selected by ``report_text``).
    """

    def __init__(self, root: Path | str, field: str = "markdown"):
        self.root = Path(root)
        self.field = field

    def resolve(self, report_id: str) -> SourceDoc:
        for suffix in (".md", ".txt", ".json"):
            path = self.root / f"{report_id}{suffix}"
            if not path.is_file():
                continue
            if suffix == ".json":
                record = json.loads(path.read_text(encoding="utf-8"))
                text = report_text(record, self.field)
            else:
                text = path.read_text(encoding="utf-8")
            return SourceDoc(report_id, text, f"file://{path}", self.field)
        raise SourceUnavailable(f"no source document for report {report_id!r} under {self.root}")


class ApiSourceResolver:
    """Resolver against the TensorPlatform report API (``$TENSOR_API_BASE``).

    Used for the live production sweep; the offline fixtures use
    :class:`DirSourceResolver` so the gate is testable without the platform.
    """

    def __init__(self, api_base: str | None = None, token: str | None = None,
                 field: str = "markdown", timeout: int = 60):
        import os
        import urllib.request

        self._urllib = urllib.request
        self.base = (api_base or os.environ.get("TENSOR_API_BASE",
                                                "http://127.0.0.1:8010/api/v1")).rstrip("/")
        self.token = token or os.environ.get("TENSOR_API_TOKEN")
        self.field = field
        self.timeout = timeout
        self._cache: dict[str, dict] = {}

    def _login(self) -> str:
        import os

        body = json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode()
        req = self._urllib.Request(
            self.base + "/auth/login", data=body, headers={"Content-Type": "application/json"}
        )
        return json.loads(self._urllib.urlopen(req, timeout=self.timeout).read())["access_token"]

    def fetch_record(self, report_id: str) -> dict:
        if report_id in self._cache:
            return self._cache[report_id]
        token = self.token or self._login()
        req = self._urllib.Request(
            f"{self.base}/tensor/reports/{report_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            record = json.loads(self._urllib.urlopen(req, timeout=self.timeout).read())
        except Exception as exc:  # noqa: BLE001 — any transport error fails closed
            raise SourceUnavailable(f"report {report_id}: {exc}") from exc
        self._cache[report_id] = record
        return record

    def resolve(self, report_id: str) -> SourceDoc:
        record = self.fetch_record(report_id)
        return SourceDoc(report_id, report_text(record, self.field),
                         f"tensor://reports/{report_id}", self.field)


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------
def sha256_of_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _ids(records: Iterable[dict]) -> list[str]:
    return [str(r.get("id", "")) for r in records]


def locator_matches(text: str, locator: dict) -> tuple[bool, str, str]:
    """Resolve one locator against the source text.

    Returns ``(ok, code, detail)``. Byte-exact when offsets are declared (the
    offsets are the contract); otherwise the quote is searched for verbatim and
    the found offset range is returned so the reviewer can re-check it.
    """
    quote = locator.get("quote") or ""
    value = locator.get("value") or ""
    start, end = locator.get("start_offset"), locator.get("end_offset")
    if not quote and not value:
        return False, "LOCATOR_EMPTY", "locator has neither quote nor value"
    if start is not None and end is not None:
        if not isinstance(start, int) or not isinstance(end, int):
            return False, "LOCATOR_BAD_OFFSETS", f"offsets not integers: {start!r},{end!r}"
        if start < 0 or end <= start or end > len(text):
            return False, "LOCATOR_OUT_OF_RANGE", f"[{start},{end}) outside text of length {len(text)}"
        window = text[start:end]
        if quote and window != quote:
            return False, "QUOTE_NOT_AT_LOCATOR", (
                f"text[{start}:{end}]={window[:60]!r} != quote {quote[:60]!r}"
            )
        if not quote and value and value not in window:
            return False, "VALUE_NOT_AT_LOCATOR", f"{value[:60]!r} not inside text[{start}:{end}]"
        return True, "OK_OFFSETS", f"[{start},{end})"
    if quote:
        pos = text.find(quote)
        if pos < 0:
            return False, "QUOTE_NOT_FOUND", f"quote {quote[:60]!r} absent from source"
        return True, "OK_SEARCH", f"found at [{pos},{pos + len(quote)})"
    pos = text.find(value)
    if pos < 0:
        return False, "VALUE_NOT_FOUND", f"value {value[:60]!r} absent from source"
    return True, "OK_SEARCH", f"value found at {pos}"


def _unresolved_claim_ids(pkg: Path) -> set[str]:
    """``unresolved.json`` — claims identified but without locatable evidence.

    Kept as a separate optional file so an unresolved claim is *recorded*, never
    silently dropped and never promoted by inventing a locator.
    """
    path = Path(pkg) / "unresolved.json"
    if not path.is_file():
        return set()
    try:
        doc = _load(path)
    except json.JSONDecodeError:
        return set()
    items = doc.get("claims", []) if isinstance(doc, dict) else doc
    out: set[str] = set()
    for item in items:
        if isinstance(item, dict) and item.get("id") and item.get("status") == "unresolved":
            out.add(str(item["id"]))
    return out


# ---------------------------------------------------------------------------
# G1 structural gate
# ---------------------------------------------------------------------------
def _gate_structural(checks: Checks, pkg: Path, contract: dict | None,
                     schemas: SchemaSet) -> dict:
    """Rules S1..S14. Returns the parsed outputs so later gates can reuse them."""
    parsed: dict[str, Any] = {}

    # S1 files_present
    missing = [name for name in (CONTRACT_FILE, *REQUIRED_OUTPUTS) if not (pkg / name).is_file()]
    checks.check("S1.files_present", not missing, f"missing={missing}")

    # S2 valid_json
    parse_errors: list[str] = []
    for name in (CONTRACT_FILE, *REQUIRED_OUTPUTS):
        path = pkg / name
        if not path.is_file():
            continue
        try:
            parsed[name] = _load(path)
        except json.JSONDecodeError as exc:
            parse_errors.append(f"{name}: {exc.msg} (line {exc.lineno})")
    checks.check("S2.valid_json", not parse_errors, f"errors={parse_errors}")

    # S3 contract_schema — the declared contract must be a well-formed package
    if isinstance(parsed.get(CONTRACT_FILE), dict):
        contract = parsed[CONTRACT_FILE]
        err = schemas.validate(CONTRACT_SCHEMA, contract)
        checks.check("S3.contract_schema", not err, err or "work-package.json valid")
    else:
        checks.check("S3.contract_schema", False, "work-package.json missing or not an object")

    # S4 record_schema
    schema_errors: list[str] = []
    for name, (schema_file, is_list) in OUTPUT_SCHEMAS.items():
        doc = parsed.get(name)
        if doc is None:
            continue
        if is_list and not isinstance(doc, list):
            schema_errors.append(f"{name}: expected JSON array")
            continue
        records = doc if isinstance(doc, list) else [doc]
        for i, record in enumerate(records):
            if not isinstance(record, dict):
                schema_errors.append(f"{name}[{i}]: not an object")
                continue
            err = schemas.validate(schema_file, record)
            if err:
                schema_errors.append(f"{name}[{i}] {err}")
    checks.check("S4.record_schema", not schema_errors, f"errors={schema_errors[:5]}")

    # S5 summary_schema
    summary = parsed.get("extraction_summary.json")
    summary_err = (
        schemas.validate(SUMMARY_SCHEMA, summary) if isinstance(summary, dict) else "no summary object"
    )
    checks.check("S5.summary_schema", not summary_err, summary_err or "extraction_summary.json valid")

    claims = parsed.get("claims.json") if isinstance(parsed.get("claims.json"), list) else []
    evidence = parsed.get("evidence.json") if isinstance(parsed.get("evidence.json"), list) else []
    provenance = parsed.get("provenance.json") if isinstance(parsed.get("provenance.json"), list) else []

    # S6 unique ids (across the whole bundle: a claim and an evidence may not share an id)
    all_ids = _ids(claims) + _ids(evidence) + _ids(provenance)
    dupes = sorted({i for i in all_ids if all_ids.count(i) > 1})
    checks.check("S6.unique_ids", not dupes and "" not in all_ids,
                 f"duplicates={dupes[:5]} empty_ids={'' in all_ids}")

    # S7 output_declaration — declared outputs are exactly the knowledge files on disk
    on_disk = {p.name for p in pkg.glob("*.json")}
    declared = set((contract or {}).get("output") or {})
    knowledge_files = on_disk & set(OUTPUT_SCHEMAS)
    undeclared = sorted(knowledge_files - declared)
    not_shipped = sorted(declared - on_disk)
    checks.check("S7.output_declaration", not undeclared and not not_shipped,
                 f"undeclared={undeclared} declared_but_absent={not_shipped}")

    # S8 producer_draft_only — do_not_mark_claims_as_verified at record level
    bad_status = [c.get("id") for c in claims if c.get("epistemic_status") != "draft"]
    checks.check("S8.producer_draft_only", not bad_status, f"non-draft claims={bad_status[:5]}")

    # S9 no_self_verification — no producer-written verification field anywhere
    markers = ("verified", "verification_status", "verification_level", "is_verified", "gate_confirmed")
    docs = (("claims.json", claims), ("evidence.json", evidence),
            ("provenance.json", provenance),
            ("extraction_summary.json", [summary] if isinstance(summary, dict) else []))
    offenders = [
        f"{name}[{i}].{m}"
        for name, records in docs
        for i, record in enumerate(records)
        if isinstance(record, dict)
        for m in markers
        if m in record
    ]
    checks.check("S9.no_self_verification", not offenders,
                 f"producer verification markers={offenders[:5]}")

    # S10 xref_closure — evidence_refs <-> claim_refs, both directions, no orphans
    ev_ids, claim_ids = set(_ids(evidence)), set(_ids(claims))
    dangling_c = [(c.get("id"), r) for c in claims
                  for r in (c.get("evidence_refs") or []) if r not in ev_ids]
    dangling_e = [(e.get("id"), r) for e in evidence
                  for r in (e.get("claim_refs") or []) if r not in claim_ids]
    orphan_ev = [i for i in ev_ids if not any(i in (c.get("evidence_refs") or []) for c in claims)]
    checks.check("S10.xref_closure", not (dangling_c or dangling_e or orphan_ev),
                 f"claim->evidence={dangling_c[:3]} evidence->claim={dangling_e[:3]} "
                 f"orphan_evidence={orphan_ev[:3]}")

    # S11 claim_evidence_or_unresolved
    unresolved = _unresolved_claim_ids(pkg)
    no_evidence = [c.get("id") for c in claims
                   if not (c.get("evidence_refs") or []) and c.get("id") not in unresolved]
    checks.check("S11.claim_evidence_or_unresolved", not no_evidence,
                 f"claims without evidence and without explicit unresolved status={no_evidence[:5]}")

    # S12 zero_claim_legality — no_forced_claim_generation
    n_claims = len(claims)
    empty = (summary or {}).get("empty_result") or {}
    if n_claims == 0:
        ok = bool(empty.get("is_empty")) and len(str(empty.get("reason", ""))) >= 20
        checks.check("S12.zero_claim_legality", ok,
                     f"empty claim set, stated reason={str(empty.get('reason'))[:80]!r}")
    else:
        checks.check("S12.zero_claim_legality", empty.get("is_empty") is False,
                     f"{n_claims} claims; empty_result.is_empty must be false")

    # S13 counts_consistent — the summary may not over- or under-state what shipped
    counts = (summary or {}).get("counts") or {}
    mismatch = {
        "claims": (counts.get("claims"), n_claims),
        "evidence": (counts.get("evidence"), len(evidence)),
        "provenance": (counts.get("provenance"), len(provenance)),
    }
    bad = {k: v for k, v in mismatch.items() if v[0] != v[1]}
    checks.check("S13.counts_consistent", not bad, f"summary vs files mismatch={bad}")

    # S14 source_identity — package, summary and evidence agree on the source
    src = (contract or {}).get("input") or {}
    ssrc = (summary or {}).get("source") or {}
    ident = [(src.get("report_id"), ssrc.get("report_id")),
             (src.get("source_hash"), ssrc.get("source_hash"))]
    evidence_src = {(e.get("source") or {}).get("persistent_id") for e in evidence} - {None, ""}
    ok = all(a == b for a, b in ident) and (not evidence_src or evidence_src == {src.get("report_id")})
    checks.check("S14.source_identity", ok,
                 f"contract/summary={ident} evidence.persistent_ids={sorted(evidence_src)} "
                 f"report_id={src.get('report_id')!r}")

    # S15 no_self_supplied_review_material — the review axis and the verification
    # axis may not be fed by files the producer can write. A process-03 package
    # that carries its own approvals or ticket is refused, not trusted.
    own = [(pkg / name).name for name in ("review_events.json", "verification_ticket.json",
                                          "review_report.json")
           if (pkg / name).is_file()]
    task_type = str((contract or {}).get("task_type") or "")
    ok = not own if task_type == "03-knowledge-extraction" else True
    if task_type == "04-independent-review":
        ok = (pkg / "review_events.json").is_file()
    checks.check("S15.no_self_supplied_review_material", ok,
                 f"task_type={task_type} self-supplied={own}")

    return {"contract": contract, "claims": claims, "evidence": evidence,
            "provenance": provenance, "summary": summary, "unresolved": unresolved}


# ---------------------------------------------------------------------------
# G2 evidence gate
# ---------------------------------------------------------------------------
def _gate_evidence(checks: Checks, contract: dict, evidence: Sequence[dict],
                   resolver, *, min_quote_chars: int = 12) -> dict:
    """Rules E1..E6 against the source bytes.

    Every rule fails closed: an unreachable source, an unhashable quote or a
    locator that cannot be resolved is a FAIL, never a skip.
    """
    src = (contract or {}).get("input") or {}
    report_id = str(src.get("report_id") or "")
    declared_hash = src.get("source_hash") or ""
    field_name = src.get("source_field") or "markdown"

    doc: SourceDoc | None = None
    try:
        doc = resolver.resolve(report_id)
        checks.check("E1.source_reachable", True,
                     f"{doc.uri} ({len(doc.text)} chars, field={doc.field})")
    except SourceUnavailable as exc:
        checks.check("E1.source_reachable", False, str(exc))

    # E2 source_hash_matches
    if doc is None:
        checks.check("E2.source_hash_matches", False, "source unavailable")
    else:
        checks.check("E2.source_hash_matches", doc.sha256 == declared_hash,
                     f"declared={declared_hash} computed={doc.sha256}")

    # E3..E6 per evidence record
    per_evidence: dict[str, dict] = {}
    unlocatable: list[str] = []
    for ev in evidence:
        ev_id = str(ev.get("id"))
        locator = ev.get("locator") or {}
        if doc is None:
            ok, code, detail = False, "NO_SOURCE", "source unavailable"
        else:
            ok, code, detail = locator_matches(doc.text, locator)
        quote = locator.get("quote") or ""
        quote_ok = len(quote) >= min_quote_chars
        hash_declared = locator.get("content_hash")
        digest = hashlib.sha256(quote.encode("utf-8")).hexdigest()
        hash_ok = True if not hash_declared else hash_declared in (digest, "sha256:" + digest)
        per_evidence[ev_id] = {"locator": ok, "code": code, "detail": detail,
                               "quote_chars": len(quote), "quote_long_enough": quote_ok,
                               "quote_hash_consistent": hash_ok}
        if not ok:
            unlocatable.append(f"{ev_id}:{code}")
    checks.check("E3.locator_resolvable", not unlocatable, f"unresolvable={unlocatable[:5]}")
    at_locator = [k for k, v in per_evidence.items() if v["code"] == "QUOTE_NOT_AT_LOCATOR"]
    checks.check("E4.quote_matches_source", not at_locator, f"offset mismatch={at_locator[:5]}")
    bad_hash = [k for k, v in per_evidence.items() if not v["quote_hash_consistent"]]
    checks.check("E5.quote_hash_consistent", not bad_hash, f"content_hash mismatch={bad_hash[:5]}")
    short = [k for k, v in per_evidence.items() if not v["quote_long_enough"]]
    checks.check("E6.quote_not_trivial", not short,
                 f"quotes shorter than {min_quote_chars} chars={short[:5]}")

    return {"source": {"report_id": report_id, "field": field_name,
                       "declared_hash": declared_hash,
                       "computed_hash": doc.sha256 if doc else None,
                       "chars": len(doc.text) if doc else 0},
            "per_evidence": per_evidence, "text": doc.text if doc else ""}


def _gate_evidence_coverage(checks: Checks, claims: Sequence[dict], evidence: Sequence[dict],
                            per_evidence: dict) -> None:
    """E7 — every claim is backed by at least one evidence record that passed E3/E4/E6."""
    ev_by_id = {str(e.get("id")): e for e in evidence}
    failing = []
    for claim in claims:
        refs = [r for r in (claim.get("evidence_refs") or []) if r in ev_by_id]
        if not refs:
            continue  # S11 already reports unresolved claims
        if not any(per_evidence.get(r, {}).get("locator")
                   and per_evidence.get(r, {}).get("quote_long_enough") for r in refs):
            failing.append(str(claim.get("id")))
    checks.check("E7.evidence_covers_claims", not failing,
                 f"claims with no resolvable evidence={failing[:5]}")


# ---------------------------------------------------------------------------
# G3 semantic gate — prepared here, decided by an independent reviewer
# ---------------------------------------------------------------------------
def build_review_request(contract: dict, claims: Sequence[dict], evidence: Sequence[dict],
                         provenance: Sequence[dict], source: dict, *, sample_rate: float = 1.0,
                         prompt_id: str = "reviewer-prompt-v1") -> dict:
    """Reviewer packet: source text + knowledge objects only.

    The producer's own explanations (``extraction_summary`` and anything in
    :data:`FORBIDDEN_REVIEW_KEYS`) are deliberately excluded: the reviewer must
    re-derive its judgement from the source, otherwise the review only echoes
    the producer's reasoning.
    """
    n = len(claims)
    k = max(1, int(round(n * sample_rate))) if n else 0
    return {
        "review_id": "rrq:" + str(contract.get("package_id", "unknown")),
        "gate": GATE_VERSION,
        "prompt_id": prompt_id,
        "package_id": contract.get("package_id"),
        "context": {
            "source": source,
            "claims": list(claims),
            "evidence": list(evidence),
            "provenance": list(provenance),
        },
        "excluded": ["extraction_summary.json (producer explanation)",
                     "producer.self_assessment"],
        "sample": {"claims_total": n, "claims_to_open": k, "sample_rate": sample_rate},
        "instructions": [
            "For each sampled claim: does the quoted source passage actually state it?",
            "Is the statement stronger than the source (over-claim)? Quote counter-evidence.",
            "Are assumptions/limitations of the source preserved?",
            "Verdict per claim: supports / qualifies / refutes / insufficient.",
            "Record a review_event with decision approve|request-changes|reject and findings.",
        ],
    }


def context_leaks(packet: dict) -> list[str]:
    """Keys of the review packet that expose producer explanation (M2)."""
    leaks: list[str] = []
    ctx = packet.get("context") or {}
    leaks.extend(f"context.{key}" for key in sorted(set(ctx) - set(REVIEW_CONTEXT_WHITELIST)))

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in FORBIDDEN_REVIEW_KEYS:
                    leaks.append(f"{path}.{key}")
                walk(value, f"{path}.{key}")
        elif isinstance(node, list):
            for i, value in enumerate(node):
                walk(value, f"{path}[{i}]")

    walk(ctx, "context")
    return leaks


def prompt_similarity(producer_prompt: str, reviewer_prompt: str, n: int = 5) -> float:
    """Character n-gram Jaccard similarity of two prompt texts.

    "review prompt 不得复制生产 prompt" is otherwise a matter of trust; the gate
    makes it measurable with an explicit threshold (default 0.5).
    """

    def grams(text: str) -> set[str]:
        flat = re.sub(r"\s+", " ", text.lower().strip())
        return {flat[i:i + n] for i in range(max(0, len(flat) - n + 1))}

    a, b = grams(producer_prompt), grams(reviewer_prompt)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def build_review_prompts(skill_type: str, report_id: str) -> tuple[str, str]:
    """Default producer/reviewer prompt pair for a report type (no cross-copy).

    The reviewer prompt asks for refutation from the source; the producer prompt
    asks for verbatim extraction. They share only the report id, which is data,
    not procedure.
    """
    producer = (
        f"PRODUCER ({skill_type}) for report {report_id}: extract atomic claims. "
        "For every claim, copy a verbatim quote from the report markdown and record its "
        "character offsets as the locator. Do not infer numbers. If a section holds no "
        "reusable claim, skip it. Emit claims.json, evidence.json, provenance.json."
    )
    reviewer = (
        f"INDEPENDENT REVIEWER for report {report_id}: you receive the report text and the "
        "knowledge objects only. Try to refute each sampled claim: search the source for "
        "counterexamples, over-claims, dropped assumptions and scope drift. Judge fidelity "
        "on the quoted passage alone; return supports/qualifies/refutes/insufficient with findings."
    )
    return producer, reviewer


def _gate_semantic(checks: Checks, contract: dict, review_events: Sequence[dict] | None,
                   producer_prompt: str | None, reviewer_prompt: str | None,
                   producer_ids: Sequence[str]) -> dict:
    """Rules M1..M4. M5 (fidelity) can never be passed by code — it stays not_run."""
    review_cfg = contract.get("review") or {}
    checks.check("M1.review_required_declared",
                 bool(review_cfg.get("required")) and bool(review_cfg.get("independent_reviewer")),
                 f"review={review_cfg}")

    state, codes, refusal = "draft", [], None
    if review_events:
        try:
            # draft -> in-review is a system transition (task completion), never a
            # reviewer decision: fold() starts from the submitted state.
            ctx = {"producer_ids": list(producer_ids)}  # raw ids; fold() wraps them
            state = submit_for_review(ctx, "draft")
            state, codes = fold_review_events(list(review_events), ctx, initial_state=state)
        except StateMachineError as exc:
            refusal = f"{exc.code}: {exc.detail}"
    checks.check("M2.review_ledger_legal", refusal is None,
                 refusal or f"state={state} codes={codes}")

    independence = None
    reviewer = None
    for event in review_events or []:
        if event.get("decision") == "approve":
            reviewer = event.get("reviewer") or {}
            independence = dict(zip(("ok", "basis"),
                                    is_independent(reviewer, producer_identity(
                                        {"producer_ids": list(producer_ids)}))))
    checks.check("M3.reviewer_independent", independence is None or independence["ok"],
                 f"approve by {reviewer!r} -> {independence}")

    if producer_prompt and reviewer_prompt:
        sim = prompt_similarity(producer_prompt, reviewer_prompt)
        checks.check("M4.prompt_independent", sim < 0.5,
                     f"char-5gram Jaccard={sim:.3f} (<0.5 required)")
    else:
        checks.check("M4.prompt_independent", True, "prompts not supplied (not_run for this run)")

    return {"axis_state": "pending-independent-review", "review_state": state,
            "review_codes": codes, "refusal": refusal, "independence": independence,
            "reviewer_prompt_present": bool(reviewer_prompt),
            "producer_prompt_present": bool(producer_prompt),
            "M5_semantic_fidelity": ("not_run — requires an independent reviewer; "
                                     "code cannot pass this gate")}


# ---------------------------------------------------------------------------
# verification ladder — L3 only via platform ticket
# ---------------------------------------------------------------------------
def verification_level(*, structural_ok: bool, evidence_ok: bool, review_state: str,
                       ticket: dict | None, package_id: str, claims_sha256: str,
                       n_claims: int = 1) -> dict:
    """Compute the verification level; returns level, ceiling reason and meaning.

    Never call this to *set* a level: the level is a function of evidence, review
    state and a platform ticket. An invalid or foreign ticket caps at L2 and
    says why, instead of being ignored.
    """
    level, reason = "L0", "STRUCTURAL_GATE_FAILED"
    if structural_ok:
        level, reason = "L1", ("EMPTY_PACKAGE_NO_CLAIM_TO_VERIFY" if n_claims == 0
                               else "EVIDENCE_GATE_FAILED")
        if evidence_ok and n_claims > 0:
            level, reason = "L2", "REVIEW_NOT_APPROVED"
            if review_state == "approved":
                if ticket is None:
                    reason = "MISSING_PLATFORM_VERIFICATION_TICKET"
                elif not ticket.get("issued_by"):
                    reason = "TICKET_UNSIGNED"
                elif ticket.get("gate") != "confirmed":
                    reason = "TICKET_NOT_CONFIRMED"
                elif str(ticket.get("package_id")) != package_id:
                    reason = "TICKET_PACKAGE_MISMATCH"
                elif ticket.get("claims_sha256") != claims_sha256:
                    reason = "TICKET_CLAIMS_DIGEST_MISMATCH"
                else:
                    level, reason = "L3", "OK_PLATFORM_VERIFIED"
    return {"level": level, "meaning": LEVEL_MEANING[level], "ceiling_reason": reason,
            "ticket_required_for_L3": True}


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------
def run_gates(package_dir: Path | str, resolver=None, *, min_quote_chars: int = 12,
              producer_prompt: str | None = None, reviewer_prompt: str | None = None,
              review_events: Sequence[dict] | None = None,
              ticket: dict | None = None,
              review_ledger_dir: Path | str | None = None,
              tickets_dir: Path | str | None = None) -> dict:
    """Run G1 and G2, prepare G3, compute the verification level.

    ``verdict`` is one of ``FAIL_STRUCTURAL`` / ``FAIL_EVIDENCE`` /
    ``PASS_PROGRAMMATIC_PENDING_REVIEW``. There is deliberately no verdict that
    means "the knowledge is correct": that is G3's decision and out of scope
    for a program.
    """
    pkg = Path(package_dir)
    schemas = SchemaSet(_SCHEMA_DIR)
    contract_doc: dict | None = None
    if (pkg / CONTRACT_FILE).is_file():
        try:
            contract_doc = _load(pkg / CONTRACT_FILE)
        except json.JSONDecodeError:
            contract_doc = None
    if resolver is None:
        declared_field = str((((contract_doc or {}).get("input") or {}).get("source_field")) or "markdown")
        resolver = DirSourceResolver(pkg.parent / "sources", field=declared_field)

    s_checks = Checks()
    s_out = _gate_structural(s_checks, pkg, contract_doc, schemas)

    e_checks = Checks()
    e_out = _gate_evidence(e_checks, s_out["contract"] or {}, s_out["evidence"], resolver,
                           min_quote_chars=min_quote_chars)
    _gate_evidence_coverage(e_checks, s_out["claims"], s_out["evidence"], e_out["per_evidence"])

    summary = s_out["summary"] or {}
    producer_ids = sorted({str((summary.get("producer") or {}).get("agent_id", ""))} - {""}
                          | {str(c.get("created_by")) for c in s_out["claims"] if c.get("created_by")})

    package_id = str((s_out["contract"] or {}).get("package_id", ""))
    # Review material is never read from the producer's own directory (S15 also
    # refuses a package that ships it): the caller names the ledger / ticket store.
    if review_events is None and review_ledger_dir:
        candidate = Path(review_ledger_dir) / f"{package_id}.review_events.json"
        if candidate.is_file():
            review_events = _load(candidate)
    if ticket is None and tickets_dir:
        candidate = Path(tickets_dir) / f"{package_id}.verification_ticket.json"
        if candidate.is_file():
            ticket = _load(candidate)
    m_checks = Checks()
    m_out = _gate_semantic(m_checks, s_out["contract"] or {}, review_events,
                           producer_prompt, reviewer_prompt, producer_ids)

    claims_sha = (sha256_of_file(pkg / "claims.json") if (pkg / "claims.json").is_file()
                  else "sha256:" + "0" * 64)
    level = verification_level(
        structural_ok=s_checks.ok,
        evidence_ok=e_checks.ok,
        review_state=m_out["review_state"],
        ticket=ticket,
        package_id=package_id,
        claims_sha256=claims_sha,
        n_claims=len(s_out["claims"]),
    )

    verdict = "FAIL_STRUCTURAL"
    if s_checks.ok:
        verdict = "FAIL_EVIDENCE" if not e_checks.ok else "PASS_PROGRAMMATIC_PENDING_REVIEW"

    request = build_review_request(
        s_out["contract"] or {}, s_out["claims"], s_out["evidence"], s_out["provenance"],
        {"report_id": e_out["source"]["report_id"], "field": e_out["source"]["field"],
         "source_hash": e_out["source"]["declared_hash"], "text": e_out["text"]},
        sample_rate=float(((s_out["contract"] or {}).get("review") or {}).get("sample_rate") or 1.0),
    )
    m_checks.check("M5.reviewer_context_no_producer_explanation", not context_leaks(request),
                   f"leaked keys={context_leaks(request)}")

    return {
        "gate": GATE_VERSION,
        "package_id": (s_out["contract"] or {}).get("package_id"),
        "task_type": (s_out["contract"] or {}).get("task_type"),
        "axes": {
            "mission_state": "not consumed by the gate (succeeded != passed)",
            "review_state": m_out["review_state"],
            "verification_level": level["level"],
        },
        "structural": {"pass": s_checks.ok, "gate": "G1", "checks": s_checks.items,
                       "summary": s_checks.summary()},
        "evidence": {"pass": e_checks.ok, "gate": "G2", "checks": e_checks.items,
                     "summary": e_checks.summary(), "source": e_out["source"],
                     "per_evidence": e_out["per_evidence"]},
        "semantic": {"pass": None, "gate": "G3", "status": "pending-independent-review",
                     "checks": m_checks.items, "summary": m_checks.summary(),
                     "detail": m_out, "request": request},
        "verification": {**level, "claims_sha256": claims_sha},
        "verdict": verdict,
        "counts": {"claims": len(s_out["claims"]), "evidence": len(s_out["evidence"]),
                   "provenance": len(s_out["provenance"]),
                   "unresolved": len(s_out["unresolved"])},
    }


def render_gate_report(report: dict) -> str:
    """Human-readable rendering of one gate report (used by the CLI and docs)."""
    lines = [f"gate={report['gate']} package={report['package_id']} verdict={report['verdict']}"]
    for gate in ("structural", "evidence"):
        block = report[gate]
        lines.append(f"[{gate}] pass={block['pass']} "
                     f"({block['summary']['n_pass']}/{block['summary']['n_checks']})")
        for c in block["checks"]:
            lines.append(f"  {'PASS' if c['ok'] else 'FAIL'}  {c['name']:<36} {c['detail']}")
    sem = report["semantic"]
    lines.append(f"[semantic] status={sem['status']} "
                 f"({sem['summary']['n_pass']}/{sem['summary']['n_checks']} preparation checks)")
    for c in sem["checks"]:
        lines.append(f"  {'PASS' if c['ok'] else 'FAIL'}  {c['name']:<36} {c['detail']}")
    v = report["verification"]
    lines.append(f"[verification] level={v['level']} ({v['ceiling_reason']}) — {v['meaning']}")
    lines.append(f"[axes] mission_state={report['axes']['mission_state']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Extraction Skill Library registry checks
# ---------------------------------------------------------------------------
def validate_skill_registry(registry_path: Path | str, schemas: SchemaSet | None = None) -> dict:
    """Validate ``extraction-skills/registry.json`` against the lifecycle rules.

    K1 valid JSON with a ``skills`` array; K2 per-skill schema; K3 unique
    skill_id; K4 lifecycle preconditions (passing sample test before
    sample-tested, review before independent-review, reuse counter when
    registered); K5 registered skills carry a review event id and a reviewer
    distinct from any recorded producer; K6 all six report types are covered by
    a non-deprecated skill.
    """
    schemas = schemas or SchemaSet(_SCHEMA_DIR)
    checks = Checks()
    path = Path(registry_path)
    doc: Any = None
    try:
        doc = _load(path)
        ok = isinstance(doc, dict) and isinstance(doc.get("skills"), list)
        checks.check("K1.valid_json", ok,
                     f"{path.name}: {len(doc.get('skills', [])) if isinstance(doc, dict) else 0} skills")
    except (OSError, json.JSONDecodeError) as exc:
        checks.check("K1.valid_json", False, f"{path}: {exc}")

    skills = doc.get("skills", []) if isinstance(doc, dict) else []
    schema_errors = [f"{s.get('skill_id')}: {err}" for s in skills
                     if (err := schemas.validate(SKILL_SCHEMA, s))]
    checks.check("K2.skill_schema", not schema_errors, f"errors={schema_errors[:4]}")

    ids = [s.get("skill_id") for s in skills]
    checks.check("K3.unique_skill_ids", len(ids) == len(set(ids)), f"{len(ids)} ids")

    lifecycle_errors = []
    for s in skills:
        state = s.get("lifecycle_state")
        tests = s.get("sample_tests") or []
        if state in ("sample-tested", "independent-review", "registered") and \
                not any(t.get("outcome") == "pass" for t in tests):
            lifecycle_errors.append(f"{s.get('skill_id')}:{state} without a passing sample test")
        if state in ("independent-review", "registered") and not s.get("review"):
            lifecycle_errors.append(f"{s.get('skill_id')}:{state} without review")
        if state == "registered" and "reuse_count" not in s:
            lifecycle_errors.append(f"{s.get('skill_id')}:registered without reuse_count")
    checks.check("K4.lifecycle_preconditions", not lifecycle_errors,
                 f"errors={lifecycle_errors[:4]}")

    indep_errors = []
    for s in skills:
        review = s.get("review") or {}
        if s.get("lifecycle_state") == "registered":
            if not review.get("review_event_id"):
                indep_errors.append(f"{s.get('skill_id')}: no review_event_id")
            if review.get("reviewer_id") and review.get("reviewer_id") == s.get("created_by"):
                indep_errors.append(f"{s.get('skill_id')}: self-review")
    checks.check("K5.review_auditable", not indep_errors, f"errors={indep_errors[:4]}")

    covered = {s.get("report_type") for s in skills if s.get("lifecycle_state") != "deprecated"}
    missing = [t for t in REPORT_TYPES if t not in covered]
    checks.check("K6.six_type_coverage", not missing, f"uncovered report types={missing}")

    return {"gate": GATE_VERSION, "registry": str(path), "pass": checks.ok,
            "summary": checks.summary(), "checks": checks.items}


def main(argv: Sequence[str] | None = None) -> int:  # pragma: no cover - CLI shim
    """``python -m ke.wp_gate <package_dir> [--sources DIR] [--json OUT]``."""
    import argparse

    ap = argparse.ArgumentParser(description="Three-gate validator (G1 structural, G2 evidence)")
    ap.add_argument("package", help="work package directory")
    ap.add_argument("--sources", help="directory of source documents (default: ../sources)")
    ap.add_argument("--min-quote-chars", type=int, default=12)
    ap.add_argument("--json", help="write the machine-readable gate report here")
    ap.add_argument("--skills", help="also validate an Extraction Skill registry")
    ap.add_argument("--review-ledger-dir", help="directory with <package_id>.review_events.json")
    ap.add_argument("--tickets-dir", help="directory with <package_id>.verification_ticket.json")
    args = ap.parse_args(argv)

    resolver = DirSourceResolver(args.sources) if args.sources else None
    report = run_gates(args.package, resolver, min_quote_chars=args.min_quote_chars,
                       review_ledger_dir=args.review_ledger_dir,
                       tickets_dir=args.tickets_dir)
    if args.skills:
        report["skills"] = validate_skill_registry(args.skills)
    print(render_gate_report(report))
    if args.json:
        Path(args.json).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                                   encoding="utf-8")
    if report["verdict"] == "FAIL_STRUCTURAL":
        return 2
    if report["verdict"] == "FAIL_EVIDENCE":
        return 3
    return 0 if not args.skills or report["skills"]["pass"] else 4


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())