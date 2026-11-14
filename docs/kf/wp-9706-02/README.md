# wp-9706-02 — report 9706, process 02 (classification / parse)

One work package = one (report, process) unit. This package touches **report_id 9706 only**.

| item | value |
|---|---|
| package_id | `wp-9706-02` |
| task_type | `02-classification-parse` |
| source | `tensor://reports/9706`, field `markdown`, `sha256:7d0e024b…d13534` (12546 chars / 20505 bytes) |
| report_type decision | `experimental-validation` (confidence **medium**, falsifiable) |
| selected skill | `xsk-experimental-validation` (`template-created`) |
| delivered | `classification.json`, `kf_result.wp-9706-02.json`, `KF-RESULT-wp-9706-02.md` |
| status | **draft** — nothing here is marked verified; verification level is computed by the platform gate |

## Files

| file | role |
|---|---|
| `wp9706_data.py` | declarative tables: 45 evidence anchors, signal judgements, claims, flags |
| `build.py` | builder: source hash gate → structure parse → mechanical quote slicing → classification → contract/result JSON → figures → report |
| `classification.json` | process-02 output (six-type decision, candidates, structure, locators, claims, unresolved flags) |
| `kf_result.wp-9706-02.json` | contract channel, validated against `schemas/kf_result.v1.schema.json` |
| `work-package.json` | process-02 contract, validated against `schemas/work-package-contract.schema.json` |
| `verify.py` | independent re-check (re-pulls the report from the API, re-derives every hash/locator) |
| `selfcheck.json` | producer self-check + measured pipeline-gate verdict (**not** a verification ticket) |
| `figures/` | structure-segment map + six-type signal coverage |
| `KF-RESULT-wp-9706-02.md` | six-part report carrying the single `json` result block |
| `sources` | `docs/kf/sources/9706.md` (byte-exact source cache used by the resolver) |

## Reproduce

```bash
python docs/kf/wp-9706-02/build.py        # rebuild every artefact (offline, hash-gated)
python docs/kf/wp-9706-02/verify.py       # 16 independent checks (API + substring search)
python -m pytest tests/test_kf_wp9706_02.py -q
python docs/kf/wp-9706-02/publish.py      # push the KF-RESULT report to the platform
```

## Honest notes

1. **Zero hand-copy**: each quote is the whole source line sliced around a unique anchor; the builder
   aborts if an anchor is missing or non-unique, so no number is re-typed from memory.
2. **Type decision is a hypothesis** (`epistemic_status: draft`). `experimental-validation` wins on
   matched `identify_signals` (test matrix / validation case / baseline comparison);
   `scientific-computation` is the substantive runner-up (governing equations + solver convergence, but
   no discretisation / mesh / timing signals). Rationale: `classification.json.confidence_reason`.
3. **Registry signals are English** — a literal keyword scan of a Chinese report body hits nothing
   (`figures/signal_coverage.png`, red bars). Selection therefore depends on reader judgement and is
   *not* fully machine-recomputable. What **is** machine-recomputable (hash, locator slicing, structure
   offsets, signal arithmetic) is 100 % reproduced.
4. **Four unresolved items, recorded not resolved**: table-8 vs table-5 worst-sector inconsistency,
   truncated sha256 in table 10, cross-repository test/endpoint claims, and the source's own
   honest-FAIL on absolute wind speed. See `classification.json.consistency_flags`.
5. **Pipeline gate G1 cannot pass for a process-02 package** as `ke/wp_gate.py` is written: S1 requires the
   four process-03 files and S5/S12/S13/S14 depend on `extraction_summary.json`, while a 02 contract
   declares only `classification.json` (S7). Faking 03 artefacts to go green would violate both S7 and
   `no_forced_claim_generation`, so the package records the failure instead. Measured verdict lives in
   `selfcheck.json.pipeline_gate`.