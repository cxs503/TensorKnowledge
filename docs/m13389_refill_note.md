# m13389 Refill Note

**Date**: 2026-11-11  
**Context**: Zombie window failed resend (排空期 worker 重启/磁盘满窗遗留)

## Status

This mission (m14356) subsumes the m13389 refill work. The sediment→ke relay infrastructure
built here provides the mechanism for future refills:

1. **Extraction packages** are now generated and stored in `knowledge/sediment/`
2. **Relay script** (`scripts/sediment_ke_relay.py`) can re-process any subset of missions
3. **Idempotency** ensures re-running doesn't duplicate or corrupt data
4. **Failure isolation** means bad records don't block the batch

## Refill Procedure (for future use)

```bash
# Re-relay specific missions (e.g., after fixing bad records)
python scripts/sediment_ke_relay.py --db /path/to/ke.db --missions m8381 m2591

# Full re-relay (idempotent)
python scripts/sediment_ke_relay.py --db /path/to/ke.db

# Verify after refill
python scripts/sediment_ke_relay.py --db /path/to/ke.db --verify
```

## Work Tree Status

The work tree contains all necessary artifacts:
- `knowledge/sediment/` — 9 sediment packages (102 claims, 142 evidence, 9 provenance)
- `scripts/sediment_ke_relay.py` — relay script (常设化)
- `scripts/sediment_generate_from_oss_lbm.py` — oss-lbm converter
- `scripts/sediment_generate_from_reports.py` — report-based generator
- `tests/test_sediment_ke_relay.py` — acceptance test suite (5/5 pass)
- `runs/sediment_relay_summary.json` — latest relay summary
- `docs/sediment_ke_relay.md` — documentation

No additional refill action needed; the infrastructure is in place for automated future refills.
