#!/usr/bin/env python3
"""wp-14041-01 · publish KF-RESULT report + readback checks + receipt."""
import base64
import hashlib
import json
import os
import re
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = "wp-14041-01"
OUT = os.path.join(ROOT, "docs", "kf", PKG)

body = open(os.path.join(OUT, "report.md")).read()
envelope = json.load(open(os.path.join(OUT, "kf_result.json")))
fig = json.load(open("/tmp/wp14041_01_fig.json"))

m = re.search(r"```json\n(.*?)\n```", body, re.S)
assert m, "no json block"
block = json.loads(m.group(1))
assert block == envelope, "json block != kf_result.json"
assert len(re.findall(r"```json", body)) == 1, "more than one json block"

base = os.environ["TENSOR_API_BASE"]
req = urllib.request.Request(
    base + "/auth/login",
    data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                     "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
    headers={"Content-Type": "application/json"}, method="POST")
tok = json.load(urllib.request.urlopen(req))["access_token"]

payload = {
    "title": f"KF-RESULT {PKG}",
    "summary": ("01-asset-registration for report 14041 (TensorFEM m14683 board audit): "
                "27 assets registered with recomputable char-span locators (9 resolved_in_source, "
                "18 referenced_unresolved), 0 claims, source sha256 matches contract "
                "sha256:4bc4b0b4cfb133914e8ff18a867690e903e952d20b7967e798c83cc6acfa5256."),
    "scenario_key": "tensorfem-m14683-board-audit",
    "mission_id": 15778,
    "tags": [f"kf-wp:{PKG}", "asset-registration", "lane-C", "TensorKnowledge", "report_id:14041"],
    "markdown": body,
    "figures": [{"name": "wp-14041-01_asset_locator_map.png",
                 "caption": "A) 资产类别计数（绿=resolved_in_source 9 / 红=referenced_unresolved 18）；B) 27 个定位器在源 markdown（2990 字符）中的字符跨度。",
                 "png_base64": base64.b64encode(open(fig["figure"], "rb").read()).decode()}],
}
req = urllib.request.Request(
    base + "/tensor/reports",
    data=json.dumps(payload).encode(),
    headers={"Authorization": "Bearer " + tok, "Content-Type": "application/json"},
    method="POST")
resp = json.load(urllib.request.urlopen(req))
new_id = resp.get("id") or resp.get("report_id")
print("published report_id:", new_id)

# readback
req2 = urllib.request.Request(base + f"/tensor/reports/{new_id}",
                              headers={"Authorization": "Bearer " + tok})
rb = json.load(urllib.request.urlopen(req2))
rb_md = rb["markdown"]
blocks = re.findall(r"```json\n(.*?)\n```", rb_md, re.S)
assert len(blocks) == 1
rb_block = json.loads(blocks[0])
assert rb_block == envelope, "readback json block mismatch"
src_md = open(os.path.join(OUT, "source.md")).read()
h = hashlib.sha256(src_md.encode("utf-8")).hexdigest()
receipt = {
    "package_id": PKG,
    "report_id": "14041",
    "task_type": "01-asset-registration",
    "published_report_id": new_id,
    "published_title": rb["title"],
    "published_status": rb["status"],
    "mission_id": rb["mission_id"],
    "tags": rb["tags"],
    "readback_checks": {
        "single_json_block": len(blocks) == 1,
        "json_block_equals_kf_result": rb_block == envelope,
        "envelope_provenance_hash_equals_source_14041_markdown_sha256":
            rb_block["provenance"]["source_hash"] == "sha256:" + h,
        "manifest_embedded_in_envelope": rb_block["outputs"]["asset_manifest.json"]["source"]["hash"] == h,
        "tags_contain_kf_wp": f"kf-wp:{PKG}" in rb["tags"],
    },
}
json.dump(receipt, open(os.path.join(OUT, "publish_receipt.json"), "w"), ensure_ascii=False, indent=2)
print(json.dumps(receipt, ensure_ascii=False, indent=2))
