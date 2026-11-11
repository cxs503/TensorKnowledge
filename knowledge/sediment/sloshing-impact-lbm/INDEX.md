# Sediment package: sloshing-impact LBM calibration (source mission 7437)

| claim | type | statement digest | first locator | quote sha256 | evidence |
|---|---|---|---|---|---|
| `tkc:sloshing-lbm:bore-reflection-shock-condition` | mathematical | `26788b17c48e9a31` | `TensorLBM@aecabea25cc776b211f372d225ab3a5aa4d09cdc:src/tensorlbm/sloshing_impact_calibration.py#L193-L201` | `71d4dd674df1892f` | 2 |
| `tkc:sloshing-lbm:forced-frequency-vs-exact-dispersion` | descriptive | `980b1f5e58f379a1` | `TensorLBM@aecabea25cc776b211f372d225ab3a5aa4d09cdc:docs/SLOSHING_IMPACT_LBM_CALIBRATION.md#L21-L21` | `f02da4228c2adcb2` | 3 |
| `tkc:sloshing-lbm:impact-peak-below-low-order-band` | descriptive | `e703d139035655f0` | `TensorLBM@aecabea25cc776b211f372d225ab3a5aa4d09cdc:docs/SLOSHING_IMPACT_LBM_CALIBRATION.md#L94-L94` | `39562c8f58bb6157` | 3 |
| `tkc:sloshing-lbm:mass-conservation-vs-hydrostatic-pressure` | descriptive | `d362b84262f1d504` | `TensorLBM@aecabea25cc776b211f372d225ab3a5aa4d09cdc:docs/SLOSHING_IMPACT_LBM_CALIBRATION.md#L100-L100` | `938fb1d39b1d071e` | 4 |
| `tkc:sloshing-lbm:swe-frequency-validity-bound` | methodological | `41bb354336a46fe2` | `TensorLBM@aecabea25cc776b211f372d225ab3a5aa4d09cdc:docs/SLOSHING_IMPACT_LBM_CALIBRATION.md#L118-L118` | `3a23ed82513095f9` | 2 |

Producer: platform mission m14530 (rework of the m7437 sediment line). Source: TensorLBM@aecabea25cc776b211f372d225ab3a5aa4d09cdc (mission 7437, branch agent/m7437, PR 1221). Claims are `draft`, evidence is `unassessed`: no review is implied.

Numbers are located, not typed: `number_checks.json` is the plan and `python3 scripts/verify_sediment_sloshing.py` re-executes it (ref = value recorded by the source at the pinned sha, got = value re-derived by `scripts/sloshing_reference.py`).
