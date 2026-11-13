#!/usr/bin/env bash
# One-key reproduction for work package wp-2506-04 (independent review of report 2506).
# Reviewer-side only: writes inside this worktree, never modifies the TensorFVM checkout.
set -euo pipefail
ROOT="${ROOT:-$(cd "$(dirname "$0")/../.." && pwd)}"
TFVM="${TFVM:-/root/tensor-ecosystem/TensorFVM}"
WP="$ROOT/work/wp-2506-04"

echo "== 1. fetch report 2506 and verify sha256 against the contract =="
python3 "$ROOT/scripts/kf_fetch_2506.py"
cp /tmp/r2506.md "$WP/source_2506.md"

echo "== 2. re-run the producer's 41-geometry audit into the reviewer's own output dir =="
( cd "$TFVM" && PYTHONPATH=src python3 scripts/audit_compatible_viscous_dissipativity.py --out "$WP/repro" )

echo "== 3. reviewer probes (measurements the producer did not make) =="
( cd "$WP" && PYTHONPATH="$TFVM/src" python3 probe_energy_rate.py probe_energy_rate.json )
( cd "$WP" && PYTHONPATH="$TFVM/src" python3 probe_affine_gradient.py )

echo "== 4. rebuild deliverables and re-verify quotes / numbers / verdict =="
python3 "$WP/build_review.py"
python3 "$WP/verify_review.py"