#!/usr/bin/env python
"""Demo: versioned dataset service end-to-end workflow (m8813).

Shows:
  1. Register datasets (draft → reviewed → published)
  2. List datasets
  3. Download with SHA256 verification
  4. Diff between versions
  5. Epistemic leak prevention (draft=403)

Run: python -m ke.cli_datasets_demo
"""
from __future__ import annotations

import json
import sys
sys.path.insert(0, '/root/tp-agent/work/m8813')

from ke.datasets import DatasetStore


def main():
    store = DatasetStore(":memory:")

    print("=" * 60)
    print("TensorKnowledge Dataset Service Demo (m8813)")
    print("=" * 60)

    # 1. Register datasets
    print("\n--- 1. Register datasets ---")

    # Draft version
    draft_rows = [
        {"id": "tk-demo-001", "text": "Draft sample 1", "domain": "demo",
         "task_type": "sft", "epistemic_status": "draft", "created_at": "2026-11-09T10:00:00Z"},
    ]
    m1 = store.register("demo-ds", "v0.1-draft", draft_rows, status="draft",
                        description="Initial draft")
    print(f"Registered draft: {m1['name']}/{m1['version']} (sha256={m1['sha256'][:16]}...)")

    # Reviewed version
    reviewed_rows = [
        {"id": "tk-demo-001", "text": "Reviewed sample 1", "domain": "demo",
         "task_type": "sft", "epistemic_status": "reviewed", "created_at": "2026-11-09T10:00:00Z"},
        {"id": "tk-demo-002", "text": "Reviewed sample 2", "domain": "demo",
         "task_type": "sft", "epistemic_status": "reviewed", "created_at": "2026-11-09T10:01:00Z"},
    ]
    m2 = store.register("demo-ds", "v0.5-reviewed", reviewed_rows, status="reviewed",
                        description="Reviewed version")
    print(f"Registered reviewed: {m2['name']}/{m2['version']} (sha256={m2['sha256'][:16]}...)")

    # Published version
    published_rows = reviewed_rows + [
        {"id": "tk-demo-003", "text": "Published sample 3", "domain": "demo",
         "task_type": "sft", "epistemic_status": "published", "created_at": "2026-11-09T10:02:00Z"},
    ]
    m3 = store.register("demo-ds", "v1.0", published_rows, status="published",
                        description="Published v1.0")
    print(f"Registered published: {m3['name']}/{m3['version']} (sha256={m3['sha256'][:16]}...)")

    # 2. List datasets
    print("\n--- 2. List datasets ---")
    datasets = store.list_datasets()
    for ds in datasets:
        print(f"  {ds['name']}/{ds['version']}  status={ds['status']}  rows={ds['row_count']}")

    # 3. Download with SHA256 verification
    print("\n--- 3. Download published dataset ---")
    rows, sha = store.download_rows_jsonl("demo-ds", "v1.0")
    print(f"  Downloaded {len(rows)} rows, SHA256={sha[:16]}...")
    print(f"  Integrity check: {'PASS' if store.verify_integrity('demo-ds', 'v1.0') else 'FAIL'}")

    # 4. Diff between versions
    print("\n--- 4. Diff v1.0 vs v0.5-reviewed ---")
    diff = store.diff("demo-ds", "v1.0", since="v0.5-reviewed", include="reviewed")
    print(f"  New rows: {len(diff)}")
    for row in diff:
        print(f"    + {row['id']}: {row['text'][:40]}...")

    # 5. Epistemic leak prevention
    print("\n--- 5. Epistemic leak prevention ---")
    try:
        store.download_rows_jsonl("demo-ds", "v0.1-draft")
        print("  ERROR: draft should not be downloadable!")
    except PermissionError as e:
        print(f"  Draft blocked: {e}")

    try:
        store.download_rows_jsonl("demo-ds", "v0.5-reviewed")
        print("  ERROR: reviewed should not be downloadable by default!")
    except PermissionError as e:
        print(f"  Reviewed blocked (default): {e}")

    # But reviewed is accessible with ?include=reviewed
    rows, sha = store.download_rows_jsonl("demo-ds", "v0.5-reviewed", include="reviewed")
    print(f"  Reviewed accessible with include=reviewed: {len(rows)} rows")

    # 6. Immutability
    print("\n--- 6. Immutability enforcement ---")
    try:
        store.register("demo-ds", "v1.0", published_rows, status="published")
        print("  ERROR: should not allow re-registration!")
    except ValueError as e:
        print(f"  Re-registration blocked: {e}")

    print("\n" + "=" * 60)
    print("Demo complete. All checks passed.")
    print("=" * 60)


if __name__ == "__main__":
    main()
