#!/usr/bin/env bash
# Reproducibility command for the Krüger OSS-LBM knowledge package.
# Mission: m8676 (FEAT-TK-OSS-LANDING)
#
# This script reproduces the full validation pipeline:
# 1. Offline discipline checks (schema, cross-refs, GAP anchors, verbatim index)
# 2. Pytest suite (offline tier; live tier skipped without KRUGER_REPO)
# 3. Benchmark: reference-vs-got numerical comparison
# 4. Entry point smoke test
#
# Usage:
#   bash knowledge/oss-lbm/kruger/repro_cmd.sh
#   KRUGER_REPO=/path/to/code bash knowledge/oss-lbm/kruger/repro_cmd.sh  # live tier

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../../../.." && pwd)"

echo "============================================"
echo "Krüger OSS-LBM Knowledge Package — Repro"
echo "============================================"
echo "Repo root: $REPO_ROOT"
echo "Package:   $SCRIPT_DIR"
echo ""

# --- Step 1: Offline discipline checks ---
echo "[1/4] Offline discipline checks..."
python3 "$SCRIPT_DIR/validate_kruger.py" -v
echo ""

# --- Step 2: Pytest suite ---
echo "[2/4] Pytest suite (offline tier)..."
cd "$REPO_ROOT"
python3 -m pytest -q "$SCRIPT_DIR/tests/test_kruger_claims.py" -v --tb=short 2>&1 | tail -20
echo ""

# --- Step 3: Benchmark (ref vs got) ---
echo "[3/4] Benchmark: reference-vs-got numerical comparison..."
python3 -c "
import json, sys
sys.path.insert(0, '$SCRIPT_DIR')
from benchmark import run_all_benchmarks
results = run_all_benchmarks()
s = results['summary']
print(f'Benchmarks: {s[\"passed\"]}/{s[\"total\"]} passed ({s[\"pass_rate\"]*100:.0f}%)')
for name, r in results['benchmarks'].items():
    status = 'PASS' if r.get('passed') else 'FAIL'
    print(f'  [{status}] {name}')
"
echo ""

# --- Step 4: Entry point smoke test ---
echo "[4/4] Entry point smoke test..."
python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from entry import KrugerReference

ref = KrugerReference()

# Poiseuille
u = ref.poiseuille_velocity(0.5, 0.01, 0.0, 1.0)
print(f'  Poiseuille u(0.5) = {u:.6e}')

# Couette
u = ref.couette_velocity(0.5, 0.01, 0.0, 1.0)
print(f'  Couette u(0.5) = {u:.6e}')

# Taylor-Green
ux, uy = ref.taylor_green_velocity(0.5, 0.5, 0.0, 0.01, 1.0/6.0)
print(f'  TG u(0.5,0.5,0) = ({ux:.6e}, {uy:.6e})')

# Young-Laplace
gamma = ref.young_laplace_gamma(0.00127, 16.32)
print(f'  Young-Laplace gamma = {gamma:.6e}')

# TRT
omega_plus = ref.trt_omega_plus(0.3, 1.0/6.0)
print(f'  TRT omega_plus (magic=1/6, omega=0.3) = {omega_plus:.6f}')

# Claims
claims = ref.get_claims()
print(f'  Claims loaded: {len(claims)}')

print('  Entry point smoke test: PASS')
"
echo ""

echo "============================================"
echo "Repro complete."
echo "============================================"
