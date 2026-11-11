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

# 1) benchmark cases for the anchor
for p in [
    "/tensor/benchmark-cases?anchor_slug=KBM-SCHEMA-W1",
    "/tensor/benchmark/cases?anchor_slug=KBM-SCHEMA-W1",
    "/benchmark/cases?anchor_slug=KBM-SCHEMA-W1",
]:
    d = get(p)
    if "error" not in d:
        print("HIT", p)
        print(json.dumps(d, ensure_ascii=False)[:3000])
        break
else:
    print("no benchmark endpoint hit; trying mission result")

# 2) mission 15180 result
for p in ["/tensor/missions/15180", "/missions/15180", "/tensor/mission/15180"]:
    d = get(p)
    if "error" not in d:
        print("MISSION HIT", p)
        print(json.dumps(d, ensure_ascii=False)[:4000])
        break
