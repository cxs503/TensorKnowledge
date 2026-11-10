#!/usr/bin/env python3
"""Probe the platform API for the /tensor/reports contract (read-only)."""
import json
import os
import urllib.request

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")
ROOT = BASE.split("/api/")[0]


def get(url: str):
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def main() -> int:
    for cand in (f"{ROOT}/openapi.json", f"{BASE}/openapi.json", f"{ROOT}/api/v1/openapi.json"):
        try:
            spec = get(cand)
        except Exception as exc:
            print("miss", cand, exc)
            continue
        print("openapi:", cand, "paths:", len(spec.get("paths", {})))
        for path, ops in spec.get("paths", {}).items():
            if "report" not in path:
                continue
            for method, op in ops.items():
                print(f"--- {method.upper()} {path} :: {op.get('summary')}")
                rb = op.get("requestBody") or {}
                ref = (((rb.get("content") or {}).get("application/json") or {}).get("schema") or {}).get("$ref")
                if ref:
                    name = ref.split("/")[-1]
                    sch = spec["components"]["schemas"][name]
                    print("    required:", sch.get("required"))
                    for k, v in sch.get("properties", {}).items():
                        print(f"      {k:20s} {v.get('type')}  {(v.get('description') or '')[:70]}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())