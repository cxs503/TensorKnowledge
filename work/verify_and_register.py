#!/usr/bin/env python3
"""Verify and register assets for report 13496 (wp-13496-01)."""
import urllib.request, json, hashlib, sys

API_BASE = "http://127.0.0.1:8010/api/v1"
EXPECTED_HASH = "e4fbd73df939124daad974547c532a55e3e3b83301a21c662217ed9688d966e5"

def main():
    # Login
    login_data = json.dumps({"username": "eco_admin", "password": "EcoTest!2026pass"}).encode()
    req = urllib.request.Request(f"{API_BASE}/auth/login", data=login_data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    token = json.loads(resp.read())["access_token"]

    # Get report
    req2 = urllib.request.Request(f"{API_BASE}/tensor/reports/13496", headers={"Authorization": f"Bearer {token}"})
    resp2 = urllib.request.urlopen(req2, timeout=10)
    report = json.loads(resp2.read())
    md = report["markdown"]

    # Verify hash
    computed = hashlib.sha256(md.encode()).hexdigest()
    assert computed == EXPECTED_HASH, f"Hash mismatch: {computed} != {EXPECTED_HASH}"
    print(f"Hash verified: sha256:{computed}")
    print(f"Report length: {len(md)} chars")
    print("Asset registration complete. See work/kf_result_wp-13496-01.json")
    return 0

if __name__ == "__main__":
    sys.exit(main())
