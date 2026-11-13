#!/bin/bash
# Independent re-run of m15810 RCI-S1 pipeline at a DIFFERENT shard count (N=8)
# Outputs go to the audit worktree only; subject worktree is used read-only.
set -uo pipefail
SUBJ=/root/tp-agent/work/m15810
HERE=/root/tp-agent/work/m15886
BASE=$HERE/audit/runs/repro
D=$BASE/data; SH=$BASE/shards; O=$BASE/out; N=${N:-8}
mkdir -p "$D" "$SH" "$O"
echo "[1/5] build_data"
python3 "$SUBJ/runs/rci-s1-registry/build_data.py" --out "$D" || exit 11
echo "[2/5] shards N=$N"
for i in $(seq 0 $((N-1))); do
  python3 "$SUBJ/runs/rci-s1-registry/rci_pipeline.py" shard --shard "$i" --n "$N" --data "$D" --out "$SH" &
done
wait
echo "[3/5] merge"
python3 "$SUBJ/runs/rci-s1-registry/rci_pipeline.py" merge --data "$D" --shards "$SH" --out "$O" --snapshot "m15810@2026-11-11T20:00:31Z" || exit 13
echo "[4/5] verify"
python3 "$SUBJ/runs/rci-s1-registry/rci_pipeline.py" verify --out "$O" || exit 14
echo "[5/5] sensitivity"
python3 "$SUBJ/runs/rci-s1-registry/sensitivity.py" --shards "$SH" --out "$O/sensitivity.json" || exit 15
echo REPRO_N${N}_OK