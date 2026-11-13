# wp-7216-04 independent review checks

reviewed: wp-7216-01 (report 7216) · verdict: **pass** (disposition `approve`) · rules: 37 · failed: 0

| rule | ok | detail |
|---|---|---|
| `R1.sha256_recomputed` | PASS | live=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b manifest=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b |
| `R2.hash_matches_contract` | PASS | live=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b contract=sha256:34538b9b7245a6ecd5a792f92df4b25ae827d62e9fc72177eb74fc515e1b9e0b |
| `R3.chars` | PASS | live=11338 manifest=11338 contract=11338 |
| `R4.bytes_utf8` | PASS | live=17984 manifest=17984 |
| `R5.lines` | PASS | live(rstrip-convention)=210 manifest=210 |
| `R6.eol_flags` | PASS | crlf live=False manifest=False; trailing newline live=True manifest=True |
| `R7.title_matches_record` | PASS | manifest='IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison' record='IN31-N12: LBM Rayleigh-Benard discrete linear stability + two-phase lambda/rho decoupling and Hadamard-Rybczynski comparison' |
| `R8.scenario_and_mission` | PASS | scenario manifest='lbm_rb_hr_validation' record='lbm_rb_hr_validation'; mission manifest=5628 record=5628 |
| `R9.status_matches_record` | PASS | manifest='published' record='published' |
| `R10.attachments_manifest_not_needed` | PASS | record has no attachments field; nothing to resolve by manifest |
| `M1.reviewer_is_not_producer` | PASS | producer='kf-worker/m15594' reviewer='kf-worker/m15851' |
| `M2.producer_selfcheck_not_used_as_input` | PASS | inputs = live markdown + asset_manifest.json only; gate_sim.json / verification.json / AUDIT_NOTES.md excluded from the review context |
| `C1.count_assets` | PASS | declared=40 actual=40 |
| `C2.by_class` | PASS | declared={'api_symbol_reference': 17, 'benchmark_script_reference': 3, 'data_artifact_reference': 6, 'directory_reference': 1, 'figure_reference': 6, 'git_branch_reference': 1, 'report_markdown': 1, 'source_code_reference': 3, 'test_reference': 2} actual={'report_markdown': 1, 'git_branch_reference': 1, 'api_symbol_reference': 17, 'directory_reference': 1, 'source_code_reference': 3, 'benchmark_script_reference': 3, 'figure_reference': 6, 'data_artifact_reference': 6, 'test_reference': 2} |
| `C3.by_resolution` | PASS | declared={'referenced_unresolved': 39, 'resolved_in_source': 1} actual={'resolved_in_source': 1, 'referenced_unresolved': 39} |
| `C4.resolved_pair` | PASS | declared=1/39 actual=1/39 |
| `C5.figure_declarations_in_prose` | PASS | declared=6 distinct prose names=6 (7 textual occurrences) registered figure assets=6; sets equal=True |
| `C6.record_figures` | PASS | declared=5 record_len=5 names=['hr_decoupling_settling.png', 'rb_base_profile.png', 'rb_eig_vs_sim.png', 'rb_growth_rate.png', 'rb_ra_c_convergence.png'] |
| `C7.every_record_figure_declared_in_prose` | PASS | record figures missing from prose declarations=[] |
| `C8.claims_empty_reason` | PASS | claims=[] reason_chars=332 (empty claim set is legal for a registration-only package; S12 of the line) |
| `L1.char_span_in_bounds` | PASS | bad=[] |
| `L2.quote_verbatim_at_span` | PASS | mismatched=[] (0 total) |
| `L3.quote_sha256` | PASS | mismatched=[] |
| `L4.line_numbers` | PASS | mismatched=[] (0 total) |
| `L5.occurrence_lines` | PASS | declared lists match neither the substring nor the standalone reading for [] (0 total) |
| `L6.token_inside_quote` | PASS | tokens outside their own span=[] |
| `L7.locator_unique_flag` | PASS | unique flag disagrees with in-document occurrence count=[] |
| `L8.section_attribution` | PASS | heading attribution mismatches=[] (0 total) |
| `L9.integrity_block` | PASS | declared locators=40 unique_quotes=40 hash=True; recomputed locators=40 unique_quotes=40 hash=True |
| `L11.local_copies_hash_to_declared` | PASS | local copies re-hashed=1 mismatch=none ([]) |
| `L10.ids_unique` | PASS | ids=40 keys=40 n=40 |
| `S1.backticked_coverage` | PASS | 45 unique backticked tokens; 39 registered tokens; 5 unregistered (file/symbol-shaped: []) |
| `X1.no_verified_marks` | PASS | manifest emits no verified marker; integrity.verified_marks_emitted=0 |
| `X2.resolution_vocabulary` | PASS | resolution values=['referenced_unresolved', 'resolved_in_source'] |
| `X3.resolution_consistent_with_check` | PASS | resolution label equals its resolution_check.result for every asset |
| `X4.figure_bytes_not_served_claim` | PASS | independent probe of the platform figure endpoint: ['/tensor/reports/7216/figures', '/tensor/reports/7216/figures/rb_growth_rate.png'] -> HTTP [404] (supports the manifest's referenced_unresolved figure class) |
| `X5.same_basename_hits_exist` | PASS | declared same-basename hits that do not exist in this worktree=[] (checked 1 paths) |
