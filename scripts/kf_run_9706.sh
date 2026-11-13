#!/usr/bin/env bash
# One-shot reproduction of work package wp-9706-01 (report 9706 asset registration).
#
# Why two report builds: the report embeds the acceptance table (runs/wp-9706-01/acceptance.json),
# and the acceptance gate includes a check on the *submitted report* (gate-style ```json extraction).
# The two are mutually dependent, so the report is built, gated, then rebuilt as the final copy.
#
# Usage: bash scripts/kf_run_9706.sh [--publish]
set -euo pipefail
cd "$(dirname "$0")/.."
PUB="${1:-}"

echo "== 1/6 fetch source markdown (sha256 gate) =="
python3 scripts/kf_fetch_9706.py

echo "== 2/6 register assets (verbatim slicing) =="
python3 scripts/kf_register_9706.py

echo "== 3/6 figures + coverage metrics =="
python3 scripts/kf_figures_9706.py

echo "== 4/6 build report (pass 1) =="
python3 scripts/kf_report_9706.py

echo "== 5/6 acceptance gate (re-fetch from API) =="
python3 scripts/kf_verify_9706.py --from-api

echo "== 6/6 rebuild report with final acceptance table + tests =="
python3 scripts/kf_report_9706.py
python3 -m pytest tests/test_kf_wp_9706_01.py -q

if [ "$PUB" = "--publish" ]; then
  echo "== publish KF-RESULT to platform =="
  python3 scripts/kf_report_9706.py --publish
fi

echo "DONE. Deliverables:"
ls -l docs/wp-9706-01/ artifacts/wp-9706-01/ runs/wp-9706-01/