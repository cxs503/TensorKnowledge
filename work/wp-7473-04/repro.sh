#!/usr/bin/env bash
# One-key reproduction of wp-7473-04 (independent review of report 7473).
# Prereqs: python3 + torch; TensorLBM checkout at /root/tensor-ecosystem/TensorLBM,
# or set TLBM=<your checkout>. CUDA-free, CPU float32 single thread, < 2 min.
set -euo pipefail
cd "$(dirname "$0")/../.."
TLBM="${TLBM:-/root/tensor-ecosystem/TensorLBM}"
export OMP_NUM_THREADS=1 PYTHONPATH="$TLBM/src:${PYTHONPATH:-}"

# 1) force-impulse re-measurement (Table 1 / Table 3 anchors)
python3 work/wp-7473-04/independent_probe.py work/wp-7473-04/probe_2026-11-12.json

# 2) laminar twin / negative control re-measurement (Table 2 / Table 3)
python3 work/wp-7473-04/independent_twin.py

# 3) reviewed module's own suite at the checkout under test
( cd "$TLBM" && python3 -m pytest -q tests/test_turbulent_channel3d.py )

# 4) figure + deliverables (quotes re-extracted verbatim; schema validated)
python3 work/wp-7473-04/make_figure.py
python3 work/wp-7473-04/build_review.py
python3 work/wp-7473-04/gen_report_md.py
echo "OK: docs/kf/wp-7473-04/{review_report.json,review_events.json,kf_result.json,README.md}"
