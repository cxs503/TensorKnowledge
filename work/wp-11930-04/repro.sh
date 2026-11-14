#!/usr/bin/env bash
# One-shot reproduction of wp-11930-04 (independent review of report 11930 / package wp-11930-01).
# Reviewer side only: fetches the report fresh, re-derives every recomputable number,
# rebuilds the deliverables and re-checks the acceptance gates.
set -euo pipefail
cd "$(dirname "$0")/../.."   # repo checkout root

python3 work/wp-11930-04/fetch_source.py
python3 work/wp-11930-04/verify_wp-11930-04.py
python3 work/wp-11930-04/build_review.py
python3 work/wp-11930-04/make_figure.py
python3 work/wp-11930-04/build_report_md.py
python3 work/wp-11930-04/selfcheck.py
echo "OK: docs/kf/wp-11930-04/{review_report.json,review_events.json,kf_result.wp-11930-04.json}"