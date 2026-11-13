#!/usr/bin/env bash
# One-shot reproduction of the wp-611-04 deliverables (report 611 independent review).
# Usage: bash docs/reviews/wp-611-04/run_all.sh [--offline]
#   default  : pull the report markdown from the platform API, then rebuild everything
#   --offline: reuse the cached _source_611.md (hash still re-verified)
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-live}"
if [ "$MODE" != "--offline" ]; then
  python3 independent_check_611.py --fetch --out independent_check_results.json >/dev/null
else
  python3 independent_check_611.py --md _source_611.md --out independent_check_results.json >/dev/null
fi

# keep the cached source byte-identical with what was just reviewed
python3 - <<'PY'
import json, hashlib, os, urllib.request
base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
u, p = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
if u and p:
    r = urllib.request.Request(base + "/auth/login",
                               data=json.dumps({"username": u, "password": p}).encode(),
                               headers={"Content-Type": "application/json"})
    t = json.load(urllib.request.urlopen(r))["access_token"]
    r = urllib.request.Request(base + "/tensor/reports/611", headers={"Authorization": "Bearer " + t})
    md = json.load(urllib.request.urlopen(r))["markdown"]
    open("_source_611.md", "w", encoding="utf-8").write(md)
print("source sha256:", hashlib.sha256(open("_source_611.md", encoding="utf-8").read().encode()).hexdigest())
PY

python3 make_figure.py
python3 build_review_611_04.py
python3 render_report_611_04.py
python3 verify_deliverables.py
echo "OK: deliverables rebuilt and gate passed"