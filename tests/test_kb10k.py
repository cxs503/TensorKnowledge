"""KPI-KB-10K corpus gate — asserts the *invariants*, not just that code runs.

The corpus is generated (``scripts/kb10k_harvest.py``) and the裁判 is
``scripts/kb10k_verify.py``; these tests pin the properties that make the
10,000 knowledge objects a governed corpus rather than 10,000 files:

* every KO carries the four-contract minimum (claim + evidence + provenance);
* ids are unique and schema-patterned;
* every evidence quote's sha256 is recomputed from the committed bytes;
* the package stays inside the platform push gate's file/size budget;
* the aggregate-shard layout is actually readable by the KE contract
  (``ke.contract.discover`` + ``ke.validate.schema_report_records``), because a
  per-record-file layout would blow the 80-file budget.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "knowledge" / "kb10k"
sys.path.insert(0, str(ROOT))

from ke import contract, validate  # noqa: E402

MANIFEST = json.loads((PKG / "manifest.json").read_text(encoding="utf-8"))
FOUND = contract.discover(PKG)


def test_target_reached_and_tiers_reconcile():
    n = len(FOUND.records["claims"])
    assert n >= 10_000, f"KPI-KB-10K needs >=10000 KOs, got {n}"
    assert n == MANIFEST["counts"]["knowledge_objects"]
    tiers = MANIFEST["counts"]["by_tier"]
    assert sum(tiers.values()) == n
    assert all(tiers[t] > 0 for t in ("A", "B", "C")), tiers


def test_four_contract_coverage_per_object():
    claims, evidence, prov = (FOUND.records[k] for k in ("claims", "evidence", "provenance"))
    ev_by_claim = {}
    for eid, (e, _rel) in evidence.items():
        for cid in e.get("claim_refs", []):
            ev_by_claim[cid] = ev_by_claim.get(cid, 0) + 1
    prov_by_claim = {}
    for _pid, (p, _rel) in prov.items():
        gid = (p.get("generated_entity") or {}).get("id")
        prov_by_claim[gid] = prov_by_claim.get(gid, 0) + 1
    incomplete = [cid for cid in claims
                  if ev_by_claim.get(cid, 0) < 1 or prov_by_claim.get(cid, 0) < 1]
    assert incomplete == []


def test_ids_unique_and_ids_do_not_collide_across_tiers():
    ids = [k for kind in ("claims", "evidence", "provenance") for k in FOUND.records[kind]]
    assert len(ids) == len(set(ids)) == 30_000


def test_every_quote_hash_recomputes_from_committed_bytes():
    bad = []
    for eid, (e, _rel) in FOUND.records["evidence"].items():
        q = e["locator"]["quote"]
        want = "sha256:" + hashlib.sha256(q.encode("utf-8")).hexdigest()
        if want != e["locator"]["content_hash"] or len(q) > 1200:
            bad.append(eid)
    assert bad == [], bad[:5]


def test_push_gate_budget():
    files = [p for p in PKG.rglob("*") if p.is_file()]
    assert len(files) <= 80, len(files)
    assert max(p.stat().st_size for p in files) < 4 * 1024 * 1024


def test_aggregate_shards_validate_against_repo_schemas():
    lines = validate.schema_report_records(PKG)
    assert lines, "no records discovered"
    fails = [ln for ln in lines if not ln[1]]
    assert fails == [], fails[:3]


def test_harvest_manifest_pins_sources_with_commits():
    repos = MANIFEST["repos"]
    assert len(repos) >= 10
    for name, meta in repos.items():
        assert meta["commit"] != "unknown", f"{name} not pinned"


def test_verifier_passes_offline():
    """The裁判 must pass with no external repo present (offline mode)."""
    r = subprocess.run([sys.executable, "scripts/kb10k_verify.py", "--offline"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-2000:] + r.stderr[-1000:]
    assert '"verdict": "PASS"' in r.stdout
    assert "[NOT_RUN] C9 online_reproduction" in r.stdout


@pytest.mark.parametrize("locator_type,claim_type", [
    ("code-location", "definition"),
    ("section", "descriptive"),
    ("row-range", None),          # tier C: descriptive | methodological
])
def test_tier_claim_types_are_honest(locator_type, claim_type):
    """Extracted structural claims are 'definition'/'descriptive'/'methodological'
    and are never marked established (no producer self-review)."""
    ev_by_claim = {e["claim_refs"][0]: e for _eid, (e, _r)
                   in FOUND.records["evidence"].items()}
    seen = 0
    for cid, (c, _rel) in FOUND.records["claims"].items():
        e = ev_by_claim[cid]
        if e["locator"]["locator_type"] != locator_type:
            continue
        seen += 1
        assert c["epistemic_status"] == "provisional", c["id"]
        assert c["claim_type"] in {"definition", "descriptive", "methodological"}
        if claim_type:
            assert c["claim_type"] == claim_type, c["id"]
    assert seen > 0, f"no {locator_type} records"
