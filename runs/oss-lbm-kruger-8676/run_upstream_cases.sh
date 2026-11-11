#!/usr/bin/env bash
# Reproduce every upstream-code execution behind mission m8676.
#
#   KRUGER_REPO=/path/to/lbm-principles-practice-code ./run_upstream_cases.sh
#
# The repository is taken from the OSS cache when present
# (/root/oss-cache/lbm-principles-practice-code).  In the m8676 image that cache
# directory did not exist; the checkout was therefore obtained from the upstream
# remote at the pinned commit recorded in run_meta.json (see the mission report
# for the deviation note).  Nothing in the upstream sources is modified: the only
# edits are compile-time knobs the sources themselves expose (verified droplet
# radius, python resolution factor) applied to *copies* in a scratch directory.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${KRUGER_REPO:-/root/oss-cache/lbm-principles-practice-code}"
SCRATCH="${SCRATCH:-/tmp/m8676-scratch}"
LOGS="$HERE/logs"
mkdir -p "$LOGS" "$SCRATCH"

if [ ! -d "$REPO" ]; then
  echo "ERROR: repo not found at $REPO (set KRUGER_REPO=)" >&2
  exit 2
fi

COMMIT="$(git -C "$REPO" rev-parse HEAD)"
echo "repo: $REPO  commit: $COMMIT"

# ---------------------------------------------------------------- Taylor-Green
# chapter13/python3/vortexdecay.py, three resolution factors (NX = 32*scale).
for s in 1 2 4; do
  sed "s/^scale  = 2 /scale  = $s /" "$REPO/chapter13/python3/vortexdecay.py" \
      > "$SCRATCH/tg_s$s.py"
  MPLBACKEND=Agg python "$SCRATCH/tg_s$s.py" > "$LOGS/tg_scale$s.log" 2>&1
  echo "  chapter13/python3 scale=$s -> logs/tg_scale$s.log"
done

# ------------------------------------------------- Shan-Chen droplet (Laplace)
# chapter9/shanchen.cpp, as shipped (radius 15) and with radius 12 to test dp ~ 1/r.
cp "$REPO/chapter9/shanchen.cpp" "$SCRATCH/shanchen_r15.cpp"
sed 's/const double radius = 15.;/const double radius = 12.;/' \
    "$REPO/chapter9/shanchen.cpp" > "$SCRATCH/shanchen_r12.cpp"
for tag in r15 r12; do
  ( cd "$SCRATCH" && g++ -O2 -o "sc_$tag" "shanchen_$tag.cpp" && ./"sc_$tag" > "$LOGS/shanchen_radius${tag#r}.log" 2>&1 )
  echo "  chapter9/shanchen.cpp ($tag) -> logs/shanchen_radius${tag#r}.log"
done

# ------------------------------------------------------- IBM-LBM Poiseuille
( cd "$SCRATCH" && cp "$REPO/chapter11/IBLBM_2D_Poiseuille.cpp" . \
  && g++ -O2 -o ib IBLBM_2D_Poiseuille.cpp && ./ib > "$LOGS/iblbm_poiseuille.log" 2>&1 )
cp "$SCRATCH/data/fluid_t2000.dat" "$LOGS/iblbm_fluid_t2000.dat"
echo "  chapter11/IBLBM_2D_Poiseuille.cpp -> logs/iblbm_poiseuille.log"

# -------------------------------------------------- ports of chapter5/*.m (MATLAB)
python "$HERE/kruger_bench_port.py" --out "$HERE" > "$LOGS/port_chapter5.log" 2>&1
echo "  chapter5 port -> logs/port_chapter5.log"

# --------------------------------------------------------------------- metadata
python - "$REPO" "$COMMIT" "$HERE/run_meta.json" <<'PY'
import json, platform, subprocess, sys, datetime
repo, commit, out = sys.argv[1], sys.argv[2], sys.argv[3]
def ver(cmd):
    try:
        return subprocess.run(cmd, capture_output=True, text=True).stdout.splitlines()[0]
    except Exception:
        return "unavailable"
json.dump({
    "repo": "lbm-principles-practice/code",
    "commit": commit,
    "remote": subprocess.run(["git", "-C", repo, "remote", "get-url", "origin"],
                             capture_output=True, text=True).stdout.strip(),
    "commit_date": subprocess.run(["git", "-C", repo, "log", "-1", "--format=%ci"],
                                  capture_output=True, text=True).stdout.strip(),
    "used_entities": ["chapter5/poiseuille_BB.m (port)", "chapter5/couette_BB.m (port)",
                      "chapter9/shanchen.cpp (executed)", "chapter11/IBLBM_2D_Poiseuille.cpp (executed)",
                      "chapter13/python3/vortexdecay.py (executed)"],
    "toolchain": {"python": platform.python_version(), "g++": ver(["g++", "--version"]),
                  "numpy": ver(["python", "-c", "import numpy;print(numpy.__version__)"]),
                  "matplotlib": ver(["python", "-c", "import matplotlib;print(matplotlib.__version__)"])},
    "executed_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
}, open(out, "w"), indent=2)
print("wrote", out)
PY

python "$HERE/analyze_validation.py" --dir "$HERE"
echo "done. logs in $LOGS"