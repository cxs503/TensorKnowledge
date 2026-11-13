#!/bin/bash
# RCI-S1 registry: full reproduction (snapshot pin -> shards -> merge -> DB -> report)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; REPO="$(cd "$HERE/../.." && pwd)"
D=${DATA:-/tmp/rci-s1/data}; SH=${SHARDS:-/tmp/rci-s1/shards}; O=${OUT:-/tmp/rci-s1/out}
N=${N:-24}
python3 "$HERE/build_data.py" --out "$D"
mkdir -p "$SH" "$O"
for i in $(seq 0 $((N-1))); do python3 "$HERE/rci_pipeline.py" shard --shard "$i" --n "$N" --data "$D" --out "$SH" & done; wait
python3 "$HERE/rci_pipeline.py" merge --data "$D" --shards "$SH" --out "$O" --snapshot "m15810@2026-11-11T20:00:31Z"
python3 "$HERE/rci_pipeline.py" verify --out "$O"
python3 "$HERE/sensitivity.py" --shards "$SH" --out "$O/sensitivity.json"
python3 "$HERE/load_registry.py" --rows "$O/registry_rows.jsonl"
python3 "$HERE/verify_db.py" --summary "$O/summary.json" --out "$O/db_extras.json"
python3 "$HERE/gen_report.py" --out "$O" --figdir "$HERE/figures" --doc "$REPO/docs/rci-s1-registry.md"
echo REPRO_OK
