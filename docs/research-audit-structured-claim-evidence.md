# ResearchAudit: structured claim/evidence audit

The structured audit complements the Markdown citation audit. It consumes existing TensorKnowledge claim and evidence JSON records and checks:

- bidirectional claim.evidence_refs / evidence.claim_refs integrity;
- source citation confinement to an explicit local source root;
- exact quote equality at declared character offsets;
- SHA-256 integrity of the extracted quote;
- consistency between declared relation and independent assessment status.

## Run

    python scripts/research_audit/claim_evidence_audit.py \
      --claims knowledge/kbm/demo-sample/extract/claims \
      --evidence knowledge/kbm/demo-sample/extract/evidence \
      --source-root . \
      --output research-audit.json

Exit codes: 0 = passed, 1 = failed or inconclusive. A structurally sound but unassessed evidence item yields inconclusive, not passed.

## Important boundary

This is a deterministic provenance and linkage gate, not an LLM semantic entailment judge. It cannot establish that a source logically supports a claim. External URLs are not fetched. Semantic review must be a separate, attributable review event.
