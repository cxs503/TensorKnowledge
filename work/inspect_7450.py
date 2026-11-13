import json, os, urllib.request

base = os.environ["TENSOR_API_BASE"]
tok = open("/tmp/tk_token.txt").read().strip()
req = urllib.request.Request(
    base + "/tensor/reports/14675",
    headers={"Authorization": "Bearer " + tok},
)
d = json.load(urllib.request.urlopen(req))
print("title:", d["title"])
print("scenario_key:", d["scenario_key"])
print("tags:", d["tags"])
print("mission_id:", d["mission_id"])
print("status:", d["status"])
md = d["markdown"]
print("md_len:", len(md))
open("/tmp/kf_result_7450_report.md", "w").write(md)
# show structure: headings and json block boundaries
for i, l in enumerate(md.split("\n"), 1):
    if l.startswith("#") or l.strip().startswith("```"):
        print(f"{i:4d}| {l[:100]}")
