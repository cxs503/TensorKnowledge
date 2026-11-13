# wp-6607-04 — independent review of wp-6607-01 (report 6607)

- Source pinned by hash: `work/wp-6607-04/source/report_6607.md` (sha256 == contract).
- Reviewed object: the published envelope of `wp-6607-01` (platform report 14665), json block only.
- Deliverable: `review_report.json` (verdict `needs-fix`, blocking `false`, 34 checks, 2 findings).
- Result channel: `report_markdown.md` (exactly one json block = `kf_result.json`);
  published as platform report 14993, title `KF-RESULT wp-6607-04`.
- Not reviewed: existence/content of the 9 registered files in the DEM worktree, figure pixels,
  physical validity of the report's numbers. No claim is marked verified.

Reproduce:

    python3 scripts/kf/fetch_report_6607.py
    python3 scripts/kf/wp_6607_04_review.py
    python3 scripts/kf/wp_6607_04_emit.py
    python3 scripts/kf/wp_6607_04_publish.py        # add --dry-run to skip the POST
    python3 -m pytest tests/test_wp_6607_04_review.py -q
