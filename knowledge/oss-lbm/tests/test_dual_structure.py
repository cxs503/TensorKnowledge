#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Dual-structure invariants for the OSS-LBM knowledge package.

These tests are deliberately paired with *negative controls*: a validator that
only ever prints PASS would be worthless, so each structural guarantee is also
shown to fail when the tree is mutated in the corresponding way (dropped claim,
diverged ingress record).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1]          # knowledge/oss-lbm
REPO = PKG.parents[1]                              # repo root
VALIDATOR = PKG / "validate_oss_lbm.py"
MERGE = PKG / "tools" / "merge_record_files.py"
MANIFEST = PKG / "lineage" / "m8634-landing-manifest.json"


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, *cmd], capture_output=True, text=True, cwd=cwd)


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sandbox(tmp_path: Path) -> Path:
    """Copy the package (and the schemas it validates against) into a tmp repo."""
    root = tmp_path / "repo"
    shutil.copytree(PKG, root / "knowledge" / "oss-lbm")
    shutil.copytree(REPO / "schemas", root / "schemas")
    return root / "knowledge" / "oss-lbm"


def test_validator_all_pass():
    result = run([str(VALIDATOR)])
    assert result.returncode == 0, f"validator failed:\n{result.stdout}\n{result.stderr}"
    assert "ALL PASS" in result.stdout
    for structure in ("structure A", "structure B", "structure C", "landing manifest"):
        assert structure in result.stdout


def test_gen2_claims_all_locatable():
    manifest = load(MANIFEST)
    assert manifest["counts"] == {"files": 61, "claim": 23, "evidence": 30, "provenance": 8}
    agg = {c["id"] for c in load(PKG / "claims" / "claims.json")}
    gen2 = [r["id"] for r in manifest["records"] if r["kind"] == "claim"]
    assert len(gen2) == 23
    assert set(gen2) <= agg, f"lost gen-2 claims: {sorted(set(gen2) - agg)}"
    # every gen-2 claim also has its own per-record ingress file in the tree
    for rec in manifest["records"]:
        assert (REPO / rec["dest_path"]).exists(), rec["dest_path"]


def test_generations_are_disjoint_and_additive():
    manifest = load(MANIFEST)
    gen2 = {r["id"] for r in manifest["records"] if r["kind"] == "claim"}
    agg = [c["id"] for c in load(PKG / "claims" / "claims.json")]
    gen1 = set(agg) - gen2
    assert len(agg) == 50, "aggregate claim count changed"
    assert len(gen1) == 27, f"gen-1 claim count changed: {len(gen1)}"
    assert not (gen1 & gen2), "generations must not share claim ids"
    assert len(set(agg)) == len(agg), "duplicate claim ids in aggregate"


def test_gen2_evidence_and_provenance_links_resolve():
    manifest = load(MANIFEST)
    claims = {c["id"] for c in load(PKG / "claims" / "claims.json")}
    evidence = {e["id"]: e for e in load(PKG / "evidence" / "evidence.json")}
    prov = {p["id"] for p in load(PKG / "provenance" / "provenance.json")}
    for row in manifest["records"]:
        if row["kind"] == "evidence":
            assert row["id"] in evidence
            assert set(evidence[row["id"]]["claim_refs"]) <= claims
        elif row["kind"] == "provenance":
            assert row["id"] in prov


def test_merge_tool_is_idempotent(tmp_path):
    pkg = sandbox(tmp_path)
    agg_files = [pkg / "claims" / "claims.json", pkg / "evidence" / "evidence.json",
                 pkg / "provenance" / "provenance.json"]
    before = {p: p.read_bytes() for p in agg_files}
    result = run([str(pkg / "tools" / "merge_record_files.py")], cwd=pkg)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "+0 merged" in result.stdout
    for path, blob in before.items():
        assert path.read_bytes() == blob, f"{path.name} was rewritten by a no-op merge"


def test_validator_detects_dropped_claim(tmp_path):
    """Negative control: losing a gen-2 claim from the aggregate must FAIL."""
    pkg = sandbox(tmp_path)
    claims_path = pkg / "claims" / "claims.json"
    claims = load(claims_path)
    dropped = next(c for c in claims if c["id"] == "tkc:oss-lbm:sailfish-sympy-codegen")
    claims_path.write_text(
        json.dumps([c for c in claims if c["id"] != dropped["id"]], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    result = run([str(pkg / "validate_oss_lbm.py")])
    assert result.returncode != 0
    # either the aggregate cross-reference check or the ingress mirror check trips first
    assert "missing from the aggregate" in result.stdout or "references missing claim" in result.stdout


def test_validator_detects_diverged_ingress_file(tmp_path):
    """Negative control: silently editing an ingress record must FAIL."""
    pkg = sandbox(tmp_path)
    ingress = pkg / "claims" / "tkc-oss-lbm-kruger-guo-force-term.json"
    rec = load(ingress)
    rec["statement"] = rec["statement"] + " (silently reworded)"
    ingress.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result = run([str(pkg / "validate_oss_lbm.py")])
    assert result.returncode != 0
    assert "diverges from the aggregate" in result.stdout


def test_validator_detects_manifest_sha_drift(tmp_path):
    """Negative control: touching an ingress file body (whitespace) must FAIL on sha256."""
    pkg = sandbox(tmp_path)
    ingress = pkg / "evidence" / "tke-oss-lbm-luma-kernels.json"
    ingress.write_text(ingress.read_text().replace("\n", "\n\n"), encoding="utf-8")
    result = run([str(pkg / "validate_oss_lbm.py")])
    assert result.returncode != 0
    assert "sha256 mismatch" in result.stdout


def test_subpackage_overlap_must_be_identical(tmp_path):
    """Negative control: a sub-package record may not diverge from the aggregate."""
    pkg = sandbox(tmp_path)
    mflbm = pkg / "mflbm" / "claims.json"
    claims = load(mflbm)
    claims[0]["statement"] = claims[0]["statement"] + " (diverged copy)"
    mflbm.write_text(json.dumps(claims, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    result = run([str(pkg / "validate_oss_lbm.py")])
    assert result.returncode != 0
    assert "overlaps the aggregate but differs" in result.stdout


def test_package_validator_still_passes_under_repo_pytest():
    """The repo-level test (test_oss_lbm.py) discovers PASS from stdout; keep it so."""
    result = run([str(VALIDATOR)], cwd=REPO)
    assert result.returncode == 0
    assert "PASS" in result.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))