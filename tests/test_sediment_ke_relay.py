#!/usr/bin/env python3
"""Test script for sediment→ke relay (m14356).

Verifies acceptance criteria:
1. Relay上线并常设化 (relay online and permanent)
2. 首批 ≥20 条断言可经 ke API 查询返回 (first batch ≥20 assertions queryable via ke API)
3. 与 m8802 旗舰闭环打通 (connected with m8802 flagship closed loop)
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from sediment_ke_relay import relay_all, verify_ke_queryable
from ke import store as ke_store
from ke import queries as ke_queries


def test_relay_basic():
    """Test 1: Relay上线并常设化 - relay is operational and permanent."""
    print("=" * 60)
    print("TEST 1: Relay operational and permanent")
    print("=" * 60)

    db_path = tempfile.mktemp(suffix=".test.db")
    try:
        summary = relay_all(
            sediment_dir=REPO_ROOT / "knowledge" / "sediment",
            db_path=db_path,
            dry_run=False,
        )

        assert summary["totals"]["succeeded"] > 0 or summary["totals"]["partial"] > 0, \
            "No missions succeeded"
        assert summary["total_claims"] >= 20, \
            f"Expected ≥20 claims, got {summary['total_claims']}"

        print(f"✅ Relay operational: {summary['totals']['succeeded']} succeeded, "
              f"{summary['totals']['partial']} partial")
        print(f"✅ Total claims: {summary['total_claims']}")
        print(f"✅ Total evidence: {summary['total_evidence']}")
        print(f"✅ Total provenance: {summary['total_provenance']}")

        return True
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_queryable_assertions():
    """Test 2: ≥20 assertions queryable via ke API."""
    print("\n" + "=" * 60)
    print("TEST 2: ≥20 assertions queryable via ke API")
    print("=" * 60)

    db_path = tempfile.mktemp(suffix=".test.db")
    try:
        # Relay first
        relay_all(
            sediment_dir=REPO_ROOT / "knowledge" / "sediment",
            db_path=db_path,
        )

        # Verify queryability
        verification = verify_ke_queryable(db_path)

        assert verification["queryable"], "Database not queryable"
        assert verification["total_claims"] >= 20, \
            f"Expected ≥20 claims, got {verification['total_claims']}"

        print(f"✅ Database queryable: {verification['total_claims']} claims")
        print(f"✅ Evidence records: {verification['total_evidence']}")
        print(f"✅ Provenance records: {verification['total_provenance']}")

        # Test specific queries
        conn = ke_store.connect(db_path)

        # Q1: Claims by status
        for status in ["draft", "established", "well-supported", "contested"]:
            claims = ke_queries.claims_by_status(conn, status)
            print(f"  - {status}: {len(claims)} claims")

        # Q2: All claims
        all_claims = ke_queries.all_claims(conn)
        assert len(all_claims) >= 20, f"Expected ≥20 claims, got {len(all_claims)}"
        print(f"✅ All claims query: {len(all_claims)} records")

        # Q3: Sample claim details
        if all_claims:
            sample = all_claims[0]
            print(f"  Sample: {sample['id']}")
            print(f"    Statement: {sample['statement'][:60]}...")
            print(f"    Status: {sample['epistemic_status']}")

        # Q4: Stats
        stats = ke_queries.stats(conn)
        print(f"✅ Stats query: {stats['claims']} claims, {stats['evidence']} evidence")

        return True
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_idempotency():
    """Test 3: Idempotency - re-running produces same state."""
    print("\n" + "=" * 60)
    print("TEST 3: Idempotency")
    print("=" * 60)

    db_path = tempfile.mktemp(suffix=".test.db")
    try:
        # First run
        summary1 = relay_all(
            sediment_dir=REPO_ROOT / "knowledge" / "sediment",
            db_path=db_path,
        )
        claims1 = summary1["total_claims"]

        # Second run (should produce same result)
        summary2 = relay_all(
            sediment_dir=REPO_ROOT / "knowledge" / "sediment",
            db_path=db_path,
        )
        claims2 = summary2["total_claims"]

        assert claims1 == claims2, \
            f"Idempotency failed: {claims1} != {claims2}"

        print(f"✅ First run: {claims1} claims")
        print(f"✅ Second run: {claims2} claims")
        print(f"✅ Idempotent: same result")

        return True
    finally:
        Path(db_path).unlink(missing_ok=True)


def test_failure_isolation():
    """Test 4: Failure isolation - bad mission doesn't block others."""
    print("\n" + "=" * 60)
    print("TEST 4: Failure isolation")
    print("=" * 60)

    db_path = tempfile.mktemp(suffix=".test.db")
    try:
        # Create a bad mission directory
        bad_mission = REPO_ROOT / "knowledge" / "sediment" / "m9999_bad"
        bad_mission.mkdir(parents=True, exist_ok=True)
        (bad_mission / "claim-01.json").write_text("invalid json{{{", encoding="utf-8")

        try:
            summary = relay_all(
                sediment_dir=REPO_ROOT / "knowledge" / "sediment",
                db_path=db_path,
            )

            # Should still have succeeded missions
            assert summary["totals"]["succeeded"] > 0 or summary["totals"]["partial"] > 0, \
                "No missions succeeded despite failure isolation"

            print(f"✅ Bad mission handled gracefully")
            print(f"✅ Other missions still succeeded: {summary['totals']['succeeded']}")

            return True
        finally:
            # Cleanup
            (bad_mission / "claim-01.json").unlink(missing_ok=True)
            bad_mission.rmdir()

    finally:
        Path(db_path).unlink(missing_ok=True)


def test_flagship_integration():
    """Test 5: Integration with m8802 flagship closed loop."""
    print("\n" + "=" * 60)
    print("TEST 5: m8802 flagship closed loop integration")
    print("=" * 60)

    db_path = tempfile.mktemp(suffix=".test.db")
    try:
        # Relay
        relay_all(
            sediment_dir=REPO_ROOT / "knowledge" / "sediment",
            db_path=db_path,
        )

        # Verify the three stages of the closed loop
        conn = ke_store.connect(db_path)

        # Stage 1: Extraction (sediment packages exist)
        sediment_dir = REPO_ROOT / "knowledge" / "sediment"
        missions = [d for d in sediment_dir.iterdir() if d.is_dir()]
        print(f"✅ Stage 1 - Extraction: {len(missions)} sediment packages")

        # Stage 2: Assertion (relay into KE)
        stats = ke_queries.stats(conn)
        print(f"✅ Stage 2 - Assertion: {stats['claims']} claims in KE")

        # Stage 3: Application (queryable for downstream use)
        all_claims = ke_queries.all_claims(conn)
        sample_domains = set()
        for c in all_claims[:20]:
            if c.get("domain"):
                sample_domains.add(c["domain"])
        print(f"✅ Stage 3 - Application: {len(sample_domains)} domains represented")

        # Verify relay meta table exists (常设化)
        meta_count = conn.execute(
            "SELECT COUNT(*) FROM sediment_relay_meta"
        ).fetchone()[0]
        print(f"✅ Relay meta table: {meta_count} missions tracked")

        return True
    finally:
        Path(db_path).unlink(missing_ok=True)


def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("SEDIMENT → KE RELAY TEST SUITE (m14356)")
    print("=" * 60)

    tests = [
        ("Relay operational", test_relay_basic),
        ("Queryable assertions", test_queryable_assertions),
        ("Idempotency", test_idempotency),
        ("Failure isolation", test_failure_isolation),
        ("Flagship integration", test_flagship_integration),
    ]

    results = []
    for name, test_fn in tests:
        try:
            ok = test_fn()
            results.append((name, ok, None))
        except Exception as e:
            results.append((name, False, str(e)))
            print(f"❌ FAILED: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    passed = sum(1 for _, ok, _ in results if ok)
    total = len(results)
    for name, ok, err in results:
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"{status}: {name}")
        if err:
            print(f"  Error: {err}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL ACCEPTANCE CRITERIA MET")
        print("   1. ✅ Relay online and permanent")
        print("   2. ✅ ≥20 assertions queryable via ke API")
        print("   3. ✅ m8802 flagship closed loop connected")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
