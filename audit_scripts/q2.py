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

d = get("/tensor/missions/15180")
res = d.get("result", {})
# print keys of result
print("result keys:", list(res.keys()))
ev = res.get("evidence", {})
print("evidence keys:", list(ev.keys()))
s = ev.get("summary", {})
print("summary keys:", list(s.keys()))
# look for benchmark anywhere in the result
txt = json.dumps(res, ensure_ascii=False)
import re
for m in re.finditer(r"benchmark", txt):
    pass
idx = txt.find("benchmark")
print("first benchmark mention ctx:", txt[max(0, idx-200):idx+400] if idx >= 0 else "NONE")
# checks field
print("checks:", repr(res.get("checks"))[:500])
print("headline:", res.get("headline"))
# save full result for inspection
with open("/tmp/m15180_result.json", "w") as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
print("saved /tmp/m15180_result.json")
