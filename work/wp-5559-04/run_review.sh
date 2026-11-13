#!/usr/bin/env bash
# wp-5559-04 · one-click reproduction of the independent review of wp-5559-01.
# Prereq: TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS in env, run from the repo root.
set -euo pipefail
cd "$(dirname "$0")/../.."
OUT=work/wp-5559-04
python3 - <<'PY'
import base64, json, os, urllib.request
base = os.environ["TENSOR_API_BASE"]
body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                   "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
req = urllib.request.Request(base + "/auth/login", data=body, headers={"Content-Type": "application/json"})
tok = json.load(urllib.request.urlopen(req, timeout=20))["access_token"]
open("/tmp/tok.txt", "w").write(tok)
req = urllib.request.Request(base + "/tensor/reports/5559", headers={"Authorization": "Bearer " + tok})
d = json.load(urllib.request.urlopen(req, timeout=30))
open("work/wp-5559-04/record_5559.json", "w").write(json.dumps(d, ensure_ascii=False, indent=1))
open("work/wp-5559-04/source_5559.md", "w", encoding="utf-8").write(d["markdown"])
print("fetched", len(d["markdown"].encode()), "bytes")
PY
python3 $OUT/verify_upstream_ko.py
# exit 1 from report_side_math.py means 'at least one displayed triple is inconsistent'
# (expected here: F-02), so it is a signal, not a failure of the run
python3 $OUT/report_side_math.py >/dev/null || [ $? -eq 1 ]
python3 $OUT/probe_endpoints.py >/dev/null
python3 $OUT/build_review_report.py
python3 $OUT/make_kf_result.py
python3 $OUT/fig_relerr.py
python3 -m pytest tests/test_wp_5559_04_review.py -q
echo "OK: see $OUT/review_report.json and $OUT/kf_result.json"
