import json, os, urllib.request

base = os.environ["TENSOR_API_BASE"]
tok = open("/tmp/tk_token.txt").read().strip()

def get(path):
    req = urllib.request.Request(base + path, headers={"Authorization": "Bearer " + tok})
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)}

cands = [
    "/tensor/benchmark-cases?anchor_slug=KBM-SCHEMA-W1",
    "/tensor/benchmark_cases?anchor_slug=KBM-SCHEMA-W1",
    "/tensor/benchmarks?anchor_slug=KBM-SCHEMA-W1",
    "/tensor/benchmark/cases?anchor_slug=KBM-SCHEMA-W1",
    "/tensor/benchmark?anchor_slug=KBM-SCHEMA-W1",
    "/tensor/benchmark-cases",
    "/tensor/benchmark_cases",
    "/tensor/benchmarks",
    "/tensor/maturity-verdicts",
    "/tensor/maturity/verdicts",
    "/tensor/verdicts",
    "/tensor/reports?scenario_key=KBM-SCHEMA-W1",
    "/tensor/reports?mission_id=15180",
]
for p in cands:
    d = get(p)
    if "error" not in d:
        print("HIT", p)
        print(json.dumps(d, ensure_ascii=False)[:2500])
        print("----")
    else:
        print("miss", p, str(d.get("error"))[:80])
