"""Submit KF-RESULT wp-8510-01 report to platform API.

Usage: python3 scripts/kf_submit_wp8510.py
"""
import json
import os
import sys
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def _post_json(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def login():
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not user or not pwd:
        return None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _post_json(BASE + path, {"username": user, "password": pwd})
        except Exception as exc:
            last = exc
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main():
    tok = login()
    if not tok:
        print("ERROR: login failed")
        return 1

    # Read the report markdown
    with open("docs/kf_result_wp-8510-01.md") as f:
        markdown = f.read()

    # Build the report payload
    payload = {
        "title": "KF-RESULT wp-8510-01",
        "summary": "源资产登记：report_id=8510（P248-N07 绿色航行 EEXI 达到值量纲缺陷修复与单位账本门成熟化）。确认 markdown 哈希 sha256:89c40d5daaece7b52882a5d137706680a8132e886aa8922092461a8d15208ad7 与契约一致；解析 9 章节、7 表格、1 图、7 代码引用、5 未解决资产；claims 留空（01-asset-registration 工序不做抽取）。",
        "scenario_key": "green_navigation_eexi_units",
        "mission_id": 15623,
        "tags": ["kf-wp:wp-8510-01", "asset-registration", "green_navigation_eexi_units", "P248-N07"],
        "markdown": markdown
    }

    # Submit the report
    result = _post_json(BASE + "/tensor/reports", payload, tok)
    print("Report submitted successfully")
    print("Response:", json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
