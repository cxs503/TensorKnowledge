# Knowledge Asset Management (m8811)

## Overview

This module implements knowledge asset management for TensorKnowledge, providing:

1. **KO Version Chain & Lifecycle** — Each knowledge object (KO) has a version history with a state machine (draft → in_review → published → deprecated). Old versions are superseded, not deleted.

2. **Dataset-level Assets** — SFT/eval/triples exports from m8810 are registered as first-class assets with version, manifest (record count, status distribution, sha256, generation parameters, upstream commit), and immutability discipline.

3. **Quality Ledger** — Per-KO aggregated metrics (evidence count, citation count, falsified count, last review time) with stale detection (published KOs with >30 days since last review).

4. **ASSET-INDEX Export** — Platform-compatible JSON export for ledger_line ingestion.

## Architecture

### Database Schema

The asset management extends the existing KE SQLite schema with four new tables:

| Table | Purpose |
|-------|---------|
| `ko_versions` | Version chain for each KO (id, ko_id, version, state, superseded_by) |
| `review_events` | Append-only review decisions (approve/reject/deprecate) |
| `dataset_assets` | Dataset-level assets (sft/eval/triples) with immutability |
| `quality_ledger` | Materialized view of per-KO quality metrics |

### State Machine

```
draft → in_review → published → deprecated
  ↓         ↓          ↓
deprecated  draft    in_review
```

Terminal state: `deprecated` (no further transitions allowed).

### CLI Commands

```bash
# List all registered KO versions
python -m ke.cli assets list --db <path>

# Show KO details (with optional full lineage)
python -m ke.cli assets show <ko_id> --db <path> [--lineage]

# Deprecate a KO version
python -m ke.cli assets deprecate <vid> --db <path> [--reviewer <id>] [--rationale <text>]

# Generate health report
python -m ke.cli assets report --db <path> [--stale-days N]

# Export ASSET-INDEX compatible JSON
python -m ke.cli assets export-index --db <path> [--output <path>]

# Register a dataset asset
python -m ke.cli assets register-dataset --db <path> --asset-id <id> --type <sft|eval|triples> --version <ver> --count <N> --sha256 <hash>
```

## Supersede Chain Demo

The demo KO `tko:demo:supersede-chain` shows a 3-version evolution:

| Version | State | Superseded By |
|---------|-------|---------------|
| v1.0.0 | published | v1.1.0 |
| v1.1.0 | published | v2.0.0 |
| v2.0.0 | published | — (latest) |

Each transition is recorded with a review event.

## OSS-LBM Registration

All 118 unique OSS-LBM claims have been registered as KO versions:

- 128 total claims scanned
- 10 duplicates skipped (mflbm claims appear in both top-level and subdirectory)
- 118 unique KOs registered
- 3 dataset assets registered (sft, eval, triples)

## Quality Report

```
Total KOs: 119
Published: 119
Stale (>30d): 118
Deprecated: 0
Draft/Review: 0
```

Note: 118 KOs are stale because they were published without a review event. The demo supersede chain is not stale because review events were created during registration.

## ASSET-INDEX Format

The exported JSON follows the `asset-index-v1` format:

```json
{
  "format": "asset-index-v1",
  "generated_at": "...",
  "total_entries": 124,
  "entries": [
    {
      "asset_id": "tko:demo:supersede-chain:v1.0.0",
      "asset_type": "knowledge_object",
      "version": "1.0.0",
      "state": "published",
      "sha256": "...",
      "lineage": ["tko:demo:supersede-chain:v1.1.0"],
      "metadata": {...}
    }
  ]
}
```

## Files

| File | Purpose |
|------|---------|
| `ke/assets.py` | Core asset management module |
| `ke/store.py` | Extended SQLite schema (includes asset tables) |
| `ke/cli.py` | CLI with `assets` subcommand group |
| `scripts/register_assets.py` | Full registration pipeline |
| `tests/test_assets.py` | 29 tests covering all functionality |
| `artifacts/asset-index.json` | Exported ASSET-INDEX (124 entries) |
| `artifacts/health-report.json` | Quality ledger report |

## Tests

```bash
python -m pytest tests/test_assets.py -v  # 29 tests
python -m pytest test_oss_lbm.py -v       # 6 tests (existing)
```

All 35 tests pass.
