#!/usr/bin/env bash
# One-click reproduction of wp-14137-01 (fetch -> register -> verify -> figures -> pytest).
# Requires env: TENSOR_API_BASE, TENSOR_AGENT_USER, TENSOR_AGENT_PASS (read-only use of the API).
# Writes: runs/wp-14137-01/repro.log  (full transcript; PASS/FAIL lines are machine-greppable)
set -u
cd "$(dirname "$0")/.." || exit 1
LOG=runs/wp-14137-01/repro.log
: > "$LOG"
run() { echo "### $*" | tee -a "$LOG"; "$@" >>"$LOG" 2>&1; rc=$?; echo "### rc=$rc" | tee -a "$LOG"; return $rc; }
fail=0
run python3 scripts/kf_fetch_14137.py      || fail=1
run python3 scripts/kf_register_14137.py   || fail=1
run python3 scripts/kf_verify_14137.py     || fail=1
run python3 scripts/kf_figures_14137.py    || fail=1
run python3 -m pytest tests/test_kf_wp14137_01.py -q || fail=1
echo "=== overall fail=$fail ===" | tee -a "$LOG"
grep -E 'MATCH:|assets=|PASS |FAIL |passed|wrote' "$LOG" | tail -30
exit "$fail"