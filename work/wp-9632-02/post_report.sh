#!/bin/bash
set -e
BASE="${TENSOR_API_BASE:-http://127.0.0.1:8010/api/v1}"
TOK=$(curl -s -X POST "$BASE/auth/login" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$TENSOR_AGENT_USER\",\"password\":\"$TENSOR_AGENT_PASS\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')
curl -s -X POST "$BASE/tensor/reports" \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  --data-binary @work/wp-9632-02/platform_report.json \
  -o /tmp/report_posted.json
python3 - <<'PY'
import json
d=json.load(open('/tmp/report_posted.json'))
print({k:d[k] for k in d if k in ('id','title','scenario_key','mission_id','tags','status','chars')})
PY