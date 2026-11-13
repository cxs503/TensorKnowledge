import json, os, urllib.request

base = os.environ["TENSOR_API_BASE"]
tok = open("/tmp/tk_token.txt").read().strip()
req = urllib.request.Request(
    base + "/tensor/reports/14041",
    headers={"Authorization": "Bearer " + tok},
)
d = json.load(urllib.request.urlopen(req))
md = d["markdown"]
print("title:", d["title"])
print("scenario_key:", d["scenario_key"])
print("tags:", d["tags"])
print("status:", d["status"], "stage:", d["stage"], "mission_id:", d["mission_id"])
print("created_at:", d["created_at"], "created_by:", d["created_by"])
figs = d.get("figures") or []
print("n_figures:", len(figs))
for i, f in enumerate(figs):
    if isinstance(f, dict):
        print(f"  fig{i}:", {k: (v[:60] + "..." if isinstance(v, str) and len(v) > 60 else v) for k, v in f.items()})
    else:
        print(f"  fig{i}:", str(f)[:120])
print("summary:", (d.get("summary") or "")[:200])
print("md_bytes_utf8:", len(md.encode("utf-8")))
