#!/usr/bin/env bash
# wp-9147-01 one-shot replay (worktree root). Read-only on the platform: only report 9147 is GET'd.
# Env: TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE
set -euo pipefail
python3 scripts/kf_wp9147_01_fetch.py      # fetch markdown, recompute sha256, assert == contract
python3 scripts/kf_wp9147_01_register.py   # assets -> docs/kf/wp-9147-01/asset_manifest.json
python3 scripts/kf_wp9147_01_result.py     # phase A: kf_result.json envelope + schema pin
python3 scripts/kf_wp9147_01_check.py      # 6 acceptance items -> acceptance_check.json
python3 scripts/kf_wp9147_01_result.py     # phase B: render docs/kf_result_wp-9147-01.md
python3 scripts/kf_wp9147_01_figure.py     # locator map PNG
echo "wp-9147-01 replay OK"
