import json, os, hashlib, urllib.request

base = os.environ["TENSOR_API_BASE"]
user = os.environ["TENSOR_AGENT_USER"]
pw = os.environ["TENSOR_AGENT_PASS"]

req = urllib.request.Request(
    base + "/auth/login",
    data=json.dumps({"username": user, "password": pw}).encode(),
    headers={"Content-Type": "application/json"},
    method="POST",
)
tok = json.load(urllib.request.urlopen(req))["access_token"]
open("/tmp/tk_token.txt", "w").write(tok)

req2 = urllib.request.Request(
    base + "/tensor/reports/14041",
    headers={"Authorization": "Bearer " + tok},
)
d = json.load(urllib.request.urlopen(req2))
md = d.get("markdown", "")
open("/tmp/report_14041.md", "w").write(md)
print("keys:", sorted(d.keys()))
print("md_len:", len(md))
print("sha256:", hashlib.sha256(md.encode("utf-8")).hexdigest())
print("title:", d.get("title"))
print("scenario_key:", d.get("scenario_key"))
