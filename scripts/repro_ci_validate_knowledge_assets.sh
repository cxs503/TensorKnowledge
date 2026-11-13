#!/usr/bin/env bash
# One-command reproduction of the "Validate knowledge assets" CI job.
#
# The GitHub job runs on a *bare* python-3.12 runner:
#
#     python -m pip install -r requirements-validation.txt
#     python scripts/validate_knowledge_assets.py
#
# and it checks out only this repository, so the read-only source repository of a
# sediment package (TensorLBM) is absent.  This script reproduces both facts
# locally in a throw-away venv:
#
#   DEPS=install|none     install requirements-validation.txt or not
#   SOURCE=absent|present hide the sediment source repo or use the local one
#
# Usage:
#   scripts/repro_ci_validate_knowledge_assets.sh                 # CI conditions
#   DEPS=none scripts/repro_ci_validate_knowledge_assets.sh       # drop the deps step
#   SOURCE=present scripts/repro_ci_validate_knowledge_assets.sh # full verification
#
# Exit code is the validator's own exit code (0 = gate green).
set -u
cd "$(dirname "$0")/.." || exit 2

DEPS=${DEPS:-install}
SOURCE=${SOURCE:-absent}
VENV=${VENV:-$(mktemp -d)/ci-venv}
MISSING_SRC=${MISSING_SRC:-/tmp/ci-no-such-repo}

echo "# repro: DEPS=$DEPS SOURCE=$SOURCE venv=$VENV"
if [ "$DEPS" = install ]; then
  # --system-site-packages keeps this usable on an offline machine: pip then
  # finds the pinned versions already satisfied instead of downloading them.
  python3 -m venv --system-site-packages "$VENV" || exit 2
  "$VENV/bin/python" -m pip install -q -r requirements-validation.txt || {
    echo "# WARNING: pip install failed (offline?); requirements may be unmet"; }
else
  python3 -m venv "$VENV" || exit 2
fi

if [ "$SOURCE" = absent ]; then
  export SLOSHING_SRC_REPO="$MISSING_SRC"
else
  unset SLOSHING_SRC_REPO
fi
echo "# python: $("$VENV/bin/python" -V 2>&1)  jsonschema: $("$VENV/bin/python" -c 'import jsonschema,importlib.metadata as m;print(m.version("jsonschema"))' 2>/dev/null || echo ABSENT)"
echo "# SLOSHING_SRC_REPO=${SLOSHING_SRC_REPO:-<unset: package default_root>}"
"$VENV/bin/python" scripts/validate_knowledge_assets.py
rc=$?
echo "# validator exit code: $rc"
exit $rc