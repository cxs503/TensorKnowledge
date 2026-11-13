# wp-5559-04 · independent review of wp-5559-01 (report 5559)

Red-team review of the upstream asset-registration package for report 5559
(IN10-A1 · field_synth). Verdict: **pass / approve-with-notes**, 0 blocking findings,
6 non-blocking (1 major, 2 minor, 3 info).

| file | what it is |
|---|---|
| `review_report.json` | the review itself (findings, adjudications, checks run/not run, independence) |
| `kf_result.json` | kf_result.v1 envelope; `outputs["review_report.json"]` is the deliverable |
| `review_checks.json` | machine output: source identity, 48-locator re-resolution, counts, figures, digests, schema |
| `report_side_math.json` | reviewer re-derivations (12 identities + 3 physics relations + per-row §3.2 self-consistency + G3 coverage) |
| `endpoint_probes.json` | replay of the attachment probes (9 endpoints, 9 × HTTP 404) |
| `report.md` | the published KF-RESULT report (single ```json block = the envelope) |
| `source_5559.md`, `record_5559.json` | frozen inputs the review is bound to (sha256 pinned by the contract) |
| `fig1_review_relerr.png` | §3.2 declared-vs-recomputed error + G3 domain-fraction coverage |
| `*.py`, `run_review.sh` | reviewer toolchain; `bash work/wp-5559-04/run_review.sh` reproduces everything |

Independence: the reviewer fetched the report with its own API call and wrote its own
verifier; the producer's narrative and producer scripts were not read or imported.
All 15 quoted evidence strings were asserted to be verbatim substrings of the source
before the review was written.

Key findings: **F-01** the G3 "four states REAL" row is backed by computed domain
fractions for only 2 of 4 states (`level_ice`/`broken_ice` are null) and neither the
report nor the registration says so; **F-02** the §3.2 sampling-side floe-slope row
(2.050 / 2.170 / 5.003e-02) cannot be reproduced from its own displayed numbers;
**F-03** the 30 measurement-table rows carry no registered locator, so 03 has to
re-locate every number itself.
