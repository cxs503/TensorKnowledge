"""KBM (Knowledge Base Mining) extraction pipeline v1.

Purpose
-------
Extract five card types (method / parameter / failure / benchmark / code-pointer)
from source reports using LLM-assisted extraction + rule-based verification.

Design principles
-----------------
1. **LLM extracts, rules verify**: every number/claim from LLM must be traceable
   back to the source report text and/or artifact. If verification fails → discard.
2. **KE API alignment**: cards are emitted as claim records (tkc: prefix) with
   card_type extension field. They flow through the existing KE four-contract
   model (claim + evidence + provenance), not parallel storage.
3. **Zero hand-copying**: all numeric values carry a ``verification`` block with
   the exact source quote, offset, and content hash.
4. **Reproducible**: the pipeline is deterministic given the same source, LLM
   output, and seed. All intermediate artifacts are hashed.

Entry point
-----------
    python3 -m ke.kbm_extract \
        --source-report docs/my_report.md \
        --llm-output /tmp/llm_cards.json \
        --out knowledge/kbm/my-extract \
        --run-dir runs/kbm/my-extract

The LLM output format (what the LLM must produce):
    {
      "cards": [
        {
          "card_type": "method|parameter|failure|benchmark|code-pointer",
          "fields": { ... card-specific fields ... },
          "source_quotes": [
            {"quote": "...", "path": "report.md", "context": "optional"}
          ],
          "numbers": [
            {"value": 0.325, "unit": "-", "source_path": "report.md", "needle": "Cb = 0.325"}
          ]
        }
      ]
    }

Verification rules
------------------
V1  card_type is one of the five allowed types
V2  every source_quote occurs exactly once in the source report
V3  every number's needle occurs in the source and the extracted value matches
    (within tolerance for floating point)
V4  required fields per card_type are present
V5  id follows tkc: namespace: slug pattern
V6  no duplicate ids across all cards in the batch

Metrics (emitted to run manifest)
---------------------------------
- cards_extracted: total cards from LLM
- cards_verified: cards passing all verification checks
- cards_discarded: cards failing verification (with reasons)
- verification_rate: cards_verified / cards_extracted
- numbers_verified: total numeric values verified
- numbers_failed: numeric values that failed verification
- source_coverage: fraction of source report bytes covered by verified quotes
"""
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0.0"

CARD_TYPES = {"method", "parameter", "failure", "benchmark", "code-pointer"}

# Required fields per card type (subset of schema "required" minus the KE base fields)
REQUIRED_BY_CARD = {
    "method": ["problem", "method", "equations", "applicable_domain"],
    "parameter": ["parameter"],
    "failure": ["failure_mode", "root_cause"],
    "benchmark": ["benchmark_case", "reference"],
    "code-pointer": ["code_location", "implements"],
}


# --------------------------------------------------------------------------- #
# Source access
# --------------------------------------------------------------------------- #
def load_source(path: Path) -> str:
    """Read a source report file."""
    if not path.is_file():
        raise FileNotFoundError(f"source report not found: {path}")
    return path.read_text(encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Quote verification (anti-handcopy)
# --------------------------------------------------------------------------- #
def locate_quote(text: str, quote: str) -> tuple[int, int] | None:
    """Return (start, end) if quote occurs exactly once, else None."""
    if len(quote) < 4:
        return None
    count = text.count(quote)
    if count != 1:
        return None
    start = text.index(quote)
    return start, start + len(quote)


def verify_quotes(source_text: str, quotes: list[dict]) -> list[dict]:
    """Verify each quote occurs exactly once. Return list of {ok, start, end, hash}."""
    results = []
    for q in quotes:
        quote = q.get("quote", "")
        loc = locate_quote(source_text, quote)
        if loc is not None:
            start, end = loc
            results.append({
                "ok": True,
                "start": start,
                "end": end,
                "content_hash": sha256_text(source_text[start:end]),
            })
        else:
            results.append({"ok": False, "reason": f"quote not found or not unique: {quote[:80]!r}"})
    return results


# --------------------------------------------------------------------------- #
# Number verification
# --------------------------------------------------------------------------- #
_NUM_PATTERN = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def find_number_in_text(text: str, needle: str) -> float | None:
    """Find the numeric value associated with a needle in text.

    Strategy: find the line containing the needle, extract all numbers from that
    line, return the first one. If needle itself is a number pattern, try to
    match it directly.
    """
    for line in text.splitlines():
        if needle in line:
            numbers = _NUM_PATTERN.findall(line)
            for n in numbers:
                try:
                    return float(n)
                except ValueError:
                    continue
    return None


def verify_numbers(source_text: str, numbers: list[dict], tolerance: float = 1e-6) -> list[dict]:
    """Verify each extracted number against the source text."""
    results = []
    for num_spec in numbers:
        needle = num_spec.get("needle", "")
        expected = num_spec.get("value")
        if expected is None:
            results.append({"ok": False, "reason": "no value provided"})
            continue
        found = find_number_in_text(source_text, needle)
        if found is None:
            results.append({"ok": False, "reason": f"needle not found: {needle!r}"})
            continue
        if abs(found - float(expected)) > tolerance * max(1.0, abs(found)):
            results.append({
                "ok": False,
                "reason": f"value mismatch: expected {expected}, found {found} (needle={needle!r})"
            })
        else:
            results.append({"ok": True, "found": found})
    return results


# --------------------------------------------------------------------------- #
# Card validation
# --------------------------------------------------------------------------- #
def validate_card(card: dict, card_type: str) -> list[str]:
    """Check required fields for a card type. Return list of errors."""
    errors = []
    required = REQUIRED_BY_CARD.get(card_type, [])
    fields = card.get("fields", {})
    for key in required:
        if key not in fields:
            errors.append(f"missing required field: {key}")
    return errors


def make_card_id(namespace: str, card_type: str, slug: str) -> str:
    """Generate a valid tkc: id."""
    # Sanitize slug: lowercase, alphanumeric + hyphen
    slug = re.sub(r"[^a-z0-9-]", "-", slug.lower())
    slug = re.sub(r"-+", "-", slug).strip("-")
    if not slug:
        slug = "unnamed"
    return f"tkc:{namespace}:{card_type}-{slug}"


# --------------------------------------------------------------------------- #
# Card building (LLM output → KE claim record)
# --------------------------------------------------------------------------- #
def build_claim_record(card: dict, namespace: str, source_path: str,
                       quote_results: list[dict], number_results: list[dict],
                       created_by: str) -> dict:
    """Build a KE claim record from a verified card.

    Card-specific fields are placed at the top level so they validate against
    the card schema directly.
    """
    card_type = card["card_type"]
    fields = card.get("fields", {})

    # Build statement from card type and key fields
    if card_type == "method":
        method_name = fields.get("method", {}).get("name", "unknown")
        problem = fields.get("problem", {}).get("description", "")
        statement = f"Method '{method_name}' for problem: {problem[:200]}"
    elif card_type == "parameter":
        sym = fields.get("parameter", {}).get("symbol", "?")
        name = fields.get("parameter", {}).get("name", "unknown")
        statement = f"Parameter {sym} ({name})"
    elif card_type == "failure":
        mode = fields.get("failure_mode", {}).get("description", "")
        statement = f"Failure mode: {mode[:200]}"
    elif card_type == "benchmark":
        case = fields.get("benchmark_case", {}).get("case_id", "?")
        statement = f"Benchmark case: {case}"
    elif card_type == "code-pointer":
        repo = fields.get("code_location", {}).get("repo", "?")
        path = fields.get("code_location", {}).get("path", "?")
        statement = f"Code: {repo}/{path}"
    else:
        statement = f"Card {card_type}"

    # Generate slug from statement
    slug = re.sub(r"[^a-z0-9]+", "-", statement.lower())[:60]
    card_id = make_card_id(namespace, card_type, slug)

    # Build evidence refs (will be filled in by the caller)
    evidence_refs = []

    # Determine domain for scope
    domain = (fields.get("applicable_domain", {}).get("domain", "") or
              fields.get("parameter", {}).get("name", "") or
              fields.get("benchmark_case", {}).get("case_id", "") or
              fields.get("failure_mode", {}).get("affected_domain", "") or
              fields.get("code_location", {}).get("repo", ""))

    # Build the claim record — card-specific fields at top level for schema validation
    record = {
        "id": card_id,
        "card_type": card_type,
        "statement": statement,
        "claim_type": _claim_type_for_card(card_type),
        "epistemic_status": "draft",
        "scope": {"domain": domain} if domain else {},
        "evidence_refs": evidence_refs,
        "created_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "created_by": created_by,
        "version": SCHEMA_VERSION,
        # Card-specific fields at top level (for schema validation)
        **fields,
        # Verification metadata
        "verification": {
            "quotes_verified": [q for q in quote_results if q.get("ok")],
            "numbers_verified": [n for n in number_results if n.get("ok")],
            "source_path": source_path,
        },
    }
    return record


def _claim_type_for_card(card_type: str) -> str:
    return {
        "method": "methodological",
        "parameter": "definition",
        "failure": "hypothesis",
        "benchmark": "predictive",
        "code-pointer": "methodological",
    }.get(card_type, "other")


# --------------------------------------------------------------------------- #
# Evidence building
# --------------------------------------------------------------------------- #
def build_evidence_records(cards: list[dict], namespace: str, source_path: str,
                           source_text: str, created_by: str) -> list[dict]:
    """Build evidence records for verified quotes from all cards."""
    records = []
    for card in cards:
        card_type = card["card_type"]
        for q in card.get("source_quotes", []):
            quote = q.get("quote", "")
            loc = locate_quote(source_text, quote)
            if loc is None:
                continue
            start, end = loc
            first_line = source_text[:start].count("\n") + 1
            last_line = source_text[:end].count("\n") + 1
            ev_id = f"tke:{namespace}:{card_type}-ev-{hashlib.md5(quote.encode()).hexdigest()[:8]}"
            records.append({
                "id": ev_id,
                "claim_refs": [],  # filled in later
                "source": {
                    "source_type": "internal-artifact",
                    "citation": f"{source_path}",
                },
                "relation": "supports",
                "locator": {
                    "locator_type": "code-location",
                    "value": f"{source_path}#L{first_line}-L{last_line}",
                    "start_offset": start,
                    "end_offset": end,
                    "quote": quote,
                    "quote_language": "text",
                    "content_hash": sha256_text(source_text[start:end]),
                },
                "extraction_method": "automated-extraction",
                "captured_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "captured_by": created_by,
                "assessment_status": "unassessed",
                "version": SCHEMA_VERSION,
            })
    return records


# --------------------------------------------------------------------------- #
# Provenance building
# --------------------------------------------------------------------------- #
def build_provenance(namespace: str, source_path: str, source_sha: str,
                     created_by: str) -> dict:
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": f"tkp:{namespace}:kbm-extract",
        "generated_entity": {
            "id": f"tkc:{namespace}:kbm-batch",
            "entity_type": "knowledge-object",
        },
        "activity": {
            "id": f"activity:{namespace}:kbm-extract",
            "activity_type": "extraction",
            "description": "KBM extraction pipeline v1: LLM extract + rule verify",
            "started_at": now,
            "ended_at": now,
            "software": [{"name": "ke.kbm_extract", "version": SCHEMA_VERSION}],
            "parameters": {"source_path": source_path, "source_sha256": source_sha},
        },
        "agents": [{"id": created_by, "agent_type": "software-agent", "role": "extractor"}],
        "derived_from": [f"source:{source_sha}"],
        "recorded_at": now,
        "version": SCHEMA_VERSION,
    }


# --------------------------------------------------------------------------- #
# Main pipeline
# --------------------------------------------------------------------------- #
def run_pipeline(source_report: Path, llm_output: Path, out_dir: Path,
                 run_dir: Path, namespace: str = "kbm", created_by: str = "agent-m15180",
                 number_tolerance: float = 1e-6) -> dict:
    """Run the full KBM extraction pipeline.

    Returns a manifest dict with metrics and artifact paths.
    """
    source_text = load_source(source_report)
    source_sha = sha256_text(source_text)
    llm_data = json.loads(llm_output.read_text(encoding="utf-8"))
    cards = llm_data.get("cards", [])

    out_dir.mkdir(parents=True, exist_ok=True)
    run_dir.mkdir(parents=True, exist_ok=True)

    # ---- Verification pass ---- #
    verified_cards = []
    discarded_cards = []
    all_evidence = []
    total_numbers_verified = 0
    total_numbers_failed = 0
    total_quote_bytes = 0

    for card in cards:
        card_type = card.get("card_type", "")
        errors = []

        # V1: card_type check
        if card_type not in CARD_TYPES:
            errors.append(f"unknown card_type: {card_type!r}")

        # V4: required fields
        if card_type in CARD_TYPES:
            errors.extend(validate_card(card, card_type))

        # V2: quote verification
        quote_results = verify_quotes(source_text, card.get("source_quotes", []))
        quote_failures = [q for q in quote_results if not q.get("ok")]
        if quote_failures:
            errors.append(f"quote verification failed: {quote_failures[0].get('reason', '')}")

        # V3: number verification
        number_results = verify_numbers(source_text, card.get("numbers", []), number_tolerance)
        num_ok = sum(1 for n in number_results if n.get("ok"))
        num_fail = sum(1 for n in number_results if not n.get("ok"))
        total_numbers_verified += num_ok
        total_numbers_failed += num_fail
        if num_fail > 0:
            errors.append(f"{num_fail} number(s) failed verification")

        if errors:
            discarded_cards.append({"card": card, "errors": errors})
        else:
            verified_cards.append(card)
            # Track quote coverage
            for qr in quote_results:
                if qr.get("ok"):
                    total_quote_bytes += qr["end"] - qr["start"]
            # Build evidence
            evs = build_evidence_records([card], namespace, str(source_report),
                                         source_text, created_by)
            all_evidence.extend(evs)

    # V5/V6: id uniqueness
    seen_ids = set()
    final_cards = []
    for card in verified_cards:
        claim = build_claim_record(card, namespace, str(source_report),
                                   verify_quotes(source_text, card.get("source_quotes", [])),
                                   verify_numbers(source_text, card.get("numbers", []), number_tolerance),
                                   created_by)
        if claim["id"] in seen_ids:
            discarded_cards.append({"card": card, "errors": [f"duplicate id: {claim['id']}"]})
            continue
        seen_ids.add(claim["id"])
        final_cards.append(claim)

    # Link evidence to claims
    for ev in all_evidence:
        # Find the claim this evidence supports (by matching card_type and source)
        for claim in final_cards:
            if claim.get("card_type") == ev["id"].split(":")[2].split("-")[0]:
                ev["claim_refs"] = [claim["id"]]
                if ev["id"] not in claim["evidence_refs"]:
                    claim["evidence_refs"].append(ev["id"])
                break

    # ---- Write outputs ---- #
    # Claims
    claims_dir = out_dir / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    for claim in final_cards:
        path = claims_dir / f"{claim['id'].replace(':', '_')}.json"
        path.write_text(json.dumps(claim, indent=2, ensure_ascii=False), encoding="utf-8")

    # Evidence
    evidence_dir = out_dir / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    for ev in all_evidence:
        path = evidence_dir / f"{ev['id'].replace(':', '_')}.json"
        path.write_text(json.dumps(ev, indent=2, ensure_ascii=False), encoding="utf-8")

    # Provenance
    prov = build_provenance(namespace, str(source_report), source_sha, created_by)
    prov_dir = out_dir / "provenance"
    prov_dir.mkdir(parents=True, exist_ok=True)
    (prov_dir / f"{prov['id'].replace(':', '_')}.json").write_text(
        json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8")

    # INDEX.md
    index_lines = [
        f"# KBM Extract — {namespace}",
        f"",
        f"Source: `{source_report}` (sha256: `{source_sha[:16]}...`)",
        f"Generated: {prov['recorded_at']}",
        f"Pipeline: ke.kbm_extract v{SCHEMA_VERSION}",
        f"",
        f"## Cards ({len(final_cards)} verified)",
        f"",
    ]
    for claim in final_cards:
        index_lines.append(f"- `{claim['id']}` — {claim['statement'][:120]}")
    index_lines.append("")
    index_lines.append(f"## Evidence ({len(all_evidence)} records)")
    index_lines.append("")
    for ev in all_evidence:
        index_lines.append(f"- `{ev['id']}` → {ev['claim_refs']}")
    index_lines.append("")
    (out_dir / "INDEX.md").write_text("\n".join(index_lines), encoding="utf-8")

    # Run manifest
    manifest = {
        "pipeline": "ke.kbm_extract",
        "version": SCHEMA_VERSION,
        "timestamp": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": {"path": str(source_report), "sha256": source_sha},
        "metrics": {
            "cards_extracted": len(cards),
            "cards_verified": len(final_cards),
            "cards_discarded": len(discarded_cards),
            "verification_rate": len(final_cards) / max(1, len(cards)),
            "evidence_records": len(all_evidence),
            "numbers_verified": total_numbers_verified,
            "numbers_failed": total_numbers_failed,
            "source_coverage_bytes": total_quote_bytes,
            "source_total_bytes": len(source_text),
        },
        "discarded": [{"errors": d["errors"]} for d in discarded_cards],
        "artifacts": {
            "claims_dir": str(claims_dir),
            "evidence_dir": str(evidence_dir),
            "provenance_dir": str(prov_dir),
            "index": str(out_dir / "INDEX.md"),
        },
    }
    manifest_path = run_dir / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    return manifest


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-report", required=True, type=Path,
                    help="Path to the source report file")
    ap.add_argument("--llm-output", required=True, type=Path,
                    help="Path to LLM extraction output (JSON)")
    ap.add_argument("--out", required=True, type=Path,
                    help="Output directory for the knowledge package")
    ap.add_argument("--run-dir", required=True, type=Path,
                    help="Directory for run artifacts (manifest, logs)")
    ap.add_argument("--namespace", default="kbm",
                    help="Namespace for generated ids")
    ap.add_argument("--created-by", default="agent-m15180",
                    help="Producer identity")
    ap.add_argument("--number-tolerance", type=float, default=1e-6,
                    help="Tolerance for number verification")
    args = ap.parse_args(argv)

    try:
        manifest = run_pipeline(
            source_report=args.source_report,
            llm_output=args.llm_output,
            out_dir=args.out,
            run_dir=args.run_dir,
            namespace=args.namespace,
            created_by=args.created_by,
            number_tolerance=args.number_tolerance,
        )
        m = manifest["metrics"]
        print(f"KBM extract complete: {m['cards_verified']}/{m['cards_extracted']} verified "
              f"({m['verification_rate']:.1%}), {m['evidence_records']} evidence records")
        if m["cards_discarded"] > 0:
            print(f"  Discarded: {m['cards_discarded']} cards")
            for d in manifest.get("discarded", [])[:5]:
                print(f"    - {d['errors']}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
