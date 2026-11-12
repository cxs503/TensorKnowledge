#!/usr/bin/env python3
"""CLI for the three-gate validator of the report-to-knowledge production line.

    # one package, offline sources
    python scripts/validate_work_package.py tests/fixtures/extraction/ok-basic \
        --sources tests/fixtures/extraction/sources

    # every package under a directory (the production sweep uses this)
    python scripts/validate_work_package.py --root knowledge/extraction \
        --online --review-ledger-dir knowledge/reviews --tickets-dir knowledge/tickets \
        --json runs/gate-report.json

    # also re-check the Extraction Skill Library registry
    python scripts/validate_work_package.py --root knowledge/extraction \
        --skills extraction-skills/registry.json

Exit codes: 0 = every package passed both programmatic gates (the semantic gate
stays *pending*: it is decided by an independent reviewer, never by this CLI),
2 = at least one structural (G1) failure, 3 = at least one evidence (G2) failure,
4 = the skill registry failed, 5 = usage error.

The gate report is the machine-readable evidence artifact: it names every rule,
its outcome and its detail, plus the verification level and the reason it is
capped. ``verdict=PASS_PROGRAMMATIC_PENDING_REVIEW`` never means "knowledge is
correct".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ke import wp_gate  # noqa: E402


def discover(root: Path) -> list[Path]:
    """Package directories under ``root`` (a dir holding work-package.json)."""
    if (root / wp_gate.CONTRACT_FILE).is_file():
        return [root]
    return sorted(p.parent for p in root.glob(f"*/{wp_gate.CONTRACT_FILE}"))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("packages", nargs="*", help="package directories")
    ap.add_argument("--root", help="directory to sweep for work packages")
    ap.add_argument("--sources", help="directory of offline source documents")
    ap.add_argument("--online", action="store_true",
                    help="resolve sources through $TENSOR_API_BASE instead of --sources")
    ap.add_argument("--min-quote-chars", type=int, default=12)
    ap.add_argument("--prompts-dir", help="directory with producer-v1.md / reviewer-v1.md")
    ap.add_argument("--skills", help="Extraction Skill Library registry.json to validate")
    ap.add_argument("--review-ledger-dir",
                    help="directory of <package_id>.review_events.json (never inside the package)")
    ap.add_argument("--tickets-dir",
                    help="directory of <package_id>.verification_ticket.json (platform issued)")
    ap.add_argument("--json", help="write the aggregate gate report here")
    args = ap.parse_args(argv)

    targets = [Path(p) for p in args.packages]
    if args.root:
        targets.extend(discover(Path(args.root)))
    if not targets:
        ap.error("no package given: pass directories or --root")

    producer_prompt = reviewer_prompt = None
    if args.prompts_dir:
        base = Path(args.prompts_dir)
        producer_prompt = (base / "producer-v1.md").read_text(encoding="utf-8")
        reviewer_prompt = (base / "reviewer-v1.md").read_text(encoding="utf-8")

    reports = []
    for pkg in targets:
        field = "markdown"
        contract_path = pkg / wp_gate.CONTRACT_FILE
        if contract_path.is_file():
            try:
                field = json.loads(contract_path.read_text(encoding="utf-8"))["input"]["source_field"]
            except (json.JSONDecodeError, KeyError):
                pass
        if args.online:
            resolver = wp_gate.ApiSourceResolver(field=field)
        elif args.sources:
            resolver = wp_gate.DirSourceResolver(args.sources, field=field)
        else:
            resolver = None  # run_gates falls back to <package>/../sources
        report = wp_gate.run_gates(
            pkg, resolver, min_quote_chars=args.min_quote_chars,
            producer_prompt=producer_prompt, reviewer_prompt=reviewer_prompt,
            review_ledger_dir=args.review_ledger_dir, tickets_dir=args.tickets_dir,
        )
        reports.append(report)
        print(wp_gate.render_gate_report(report))
        print()

    out: dict = {"gate": wp_gate.GATE_VERSION, "n_packages": len(reports),
                 "verdicts": sorted({r["verdict"] for r in reports}), "packages": reports}
    if args.skills:
        out["skills"] = wp_gate.validate_skill_registry(args.skills)
        print(json.dumps(out["skills"]["summary"], ensure_ascii=False, indent=2))
    if args.json:
        dest = Path(args.json)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {dest}")

    codes = {r["verdict"] for r in reports}
    if "FAIL_STRUCTURAL" in codes:
        return 2
    if "FAIL_EVIDENCE" in codes:
        return 3
    if args.skills and not out["skills"]["pass"]:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())