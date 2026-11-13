# Production-line runner — run log (generated)

- fixture matrix: 8 extraction packages, 3 cleared, 5 failed, 0 blocked upstream; base_processing_complete=False
- clearing subset: 3 packages, synthesis ready=True, eligible=2, refused=1, claims=10, duplicate_candidates=5
  - refused wp-ok-zero-claim: NOT_EVIDENCE_BOUND (level=L1 reason=EMPTY_PACKAGE_NO_CLAIM_TO_VERIFY)
- benchmark verdict_agreement: 1.0000 (threshold 1.0)
- benchmark rule_agreement: 1.0000 (threshold 1.0)
- benchmark level_agreement: 1.0000 (threshold 1.0)
- benchmark mutation_detection: 1.0000 (threshold 1.0)
- benchmark rule_coverage: 1.0000 (threshold 0.9)
- rule coverage: 27/27 implemented rules reddened by at least one mutant or fixture; uncovered=[]
- process 01 (live platform): 5/5 reachable, 0 unreachable
  - 15050: reachable=True hash=sha256:f0e9443043caa8dc55c54c09f1151351dad03df18ca4930aa6f142621036b788 chars=2703
  - 15048: reachable=True hash=sha256:c57675380b12f4ae0fe5eec450e2e4240ed15e73b5890c0f855f3f08b8e1f723 chars=3098
  - 15047: reachable=True hash=sha256:4bd338c40a90c245f3fe64963a3dc1ce051b65efbacb3f865971119533c76d1e chars=3716
  - 15045: reachable=True hash=sha256:60e03f194ca853f8d58a3c6075ad1e74c57b15c788adc111d3abfdb29d86c2cd chars=4186
  - 15044: reachable=True hash=sha256:c0e164f64203f4b28bcf3a428625e87bffc6897761b3d45220806abce530c3c5 chars=4956

Regenerate with: python scripts/wp_line_artifacts.py --out docs/production/run-artifacts --online
