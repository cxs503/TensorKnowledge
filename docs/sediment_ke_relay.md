# Sediment → KE Assertion Relay

**Mission**: m14356 / FEAT-TK-GOV-INFRA  
**Status**: ✅ Operational  
**Date**: 2026-11-11

## Overview

The sediment→ke relay bridges the gap between sediment extraction packages (markdown reports + four-contract JSON) and the Knowledge Engine SQLite store. It converts 32+ sediment extraction results into queryable KE assertions, solving the 0.18% throughput bottleneck (8731 reports → 16 KB entries).

## Architecture

```
knowledge/sediment/m{id}/          scripts/sediment_ke_relay.py         KE SQLite DB
  ├─ claim-01.json         ──┐                                      ┌─ claims table
  ├─ claim-02.json          │                                      │
  ├─ evidence-01.json       ├──> validate ──> accumulate ──> ingest ├─ evidence table
  ├─ evidence-02.json       │     (schema)     (dedup by id)        │
  ├─ provenance-01.json    ──┘                                      ├─ provenance table
  └─ INDEX.md                                                        └─ sediment_relay_meta
```

## Design Principles

1. **Idempotent**: Re-running produces the same database state. Uses `task_key` (mission id) to track ingestion.
2. **Failure-isolated**: Bad records in one mission don't block others. Per-mission results logged.
3. **Schema-mapped**: claim/evidence/provenance → KE entity tables with scope/anchor preservation.
4. **Accumulative**: All valid records combined into single pilot directory before ingest (since `ke.store.ingest_pilot()` replaces all records).

## Usage

```bash
# Relay all sediment packages
python scripts/sediment_ke_relay.py --db /tmp/ke.db

# Relay specific missions
python scripts/sediment_ke_relay.py --db /tmp/ke.db --missions m8381 m2591

# Dry-run (validate only)
python scripts/sediment_ke_relay.py --db /tmp/ke.db --dry-run

# Include oss-lbm packages
python scripts/sediment_ke_relay.py --db /tmp/ke.db --include-oss-lbm

# Verify queryability after relay
python scripts/sediment_ke_relay.py --db /tmp/ke.db --verify
```

## Current State

**Sediment packages**: 9 missions
- m2591: Wigley wave resistance pressure path (4 claims, 4 evidence, 1 provenance)
- m7485: KP505 open water BEM (3 claims, 3 evidence, 1 provenance)
- m8381: KVLCC2 MMG model (4 claims, 4 evidence, 1 provenance)
- m9001-m9006: oss-lbm packages converted to sediment format (91 claims, 131 evidence, 6 provenance)

**KE database stats** (after relay):
- Claims: 68
- Evidence: 103
- Provenance: 7
- Claim-evidence edges: 107

**Queryable**: ✅ Yes (verified via `ke.queries.*` API)

## Schema Mapping

| Sediment Contract | KE Table | Key Fields |
|---|---|---|
| claim-*.json | claims | id (tkc:*), statement, claim_type, epistemic_status, scope |
| evidence-*.json | evidence | id (tke:*), relation, source, locator, assessment_status |
| provenance-*.json | provenance | id (tkp:*), generated_entity, activity, agents |

## Validation

Records are validated against JSON schemas in `schemas/`:
- `claim-record.schema.json`
- `evidence-record.schema.json`
- `provenance-record.schema.json`

Validation errors are logged but don't block ingestion (records still included with warnings).

## Idempotency Tracking

The `sediment_relay_meta` table tracks per-mission ingestion:

```sql
CREATE TABLE sediment_relay_meta (
    mission_id   TEXT PRIMARY KEY,
    task_key     TEXT NOT NULL,
    status       TEXT CHECK (status IN ('succeeded', 'failed', 'partial', 'skipped')),
    claims_count INTEGER,
    evidence_count INTEGER,
    provenance_count INTEGER,
    error_detail TEXT,
    ingested_at  TEXT,
    source_dir   TEXT
);
```

## Integration with m8802 Flagship

The relay connects to the m8802 flagship closed loop:
1. **Extraction**: Mission completes → sediment package generated (claim/evidence/provenance JSON)
2. **Assertion**: Relay upserts into KE database (this script)
3. **Application**: KE queries feed into training datasets, evaluation benchmarks, and knowledge graphs

## Files

- `scripts/sediment_ke_relay.py` — Main relay script
- `scripts/sediment_generate_from_oss_lbm.py` — Converter for oss-lbm packages
- `scripts/sediment_generate_from_reports.py` — Generator for mission-specific packages
- `knowledge/sediment/` — Sediment package directory
- `runs/sediment_relay_summary.json` — Latest relay summary

## Testing

```bash
# Run relay with verification
python scripts/sediment_ke_relay.py --db /tmp/test.db --verify

# Expected output:
# Accumulated: 68 claims, 103 evidence, 7 provenance
# Ingested: {'claims': 68, 'evidence': 103, 'provenance': 7}
# Verification: 68 claims queryable
```

## Future Work

- [ ] Automated relay on mission completion (webhook/CI integration)
- [ ] Incremental relay (only new/changed missions)
- [ ] Cross-mission deduplication (same claim from different sources)
- [ ] Epistemic status aggregation (draft → provisional → established)
