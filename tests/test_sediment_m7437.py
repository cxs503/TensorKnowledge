"""Regression test for the m7437 sediment package (knowledge/sediment/m7437).

Runs in CI without the source repository: schema validation, cross-reference
closure, INDEX consistency and producer-discipline checks always run; the
quote-reproduction check (``git show <sha>:<path> | grep -nF``) runs when a
TensorLBM checkout is available via ``TENSORLBM_REPO`` and is skipped
otherwise (skipped is reported, never counted as passed).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

PKG = Path(__file__).resolve().parents[1] / "knowledge" / "sediment" / "m7437"
sys.path.insert(0, str(PKG))

import verify_records as vr  # noqa: E402

SHA = "aecabea25cc776b211f372d225ab3a5aa4d09cdc"


def _load(sub: str) -> dict:
    return {json.loads(p.read_text(encoding="utf-8"))["id"]: json.loads(p.read_text(encoding="utf-8"))
            for p in (PKG / sub).glob("*.json")}


def test_package_present() -> None:
    for f in ("INDEX.md", "build_records.py", "verify_records.py", "number_checks.py",
              "number_checks.json"):
        assert (PKG / f).exists(), f
    assert len(list((PKG / "claims").glob("*.json"))) >= 3


def test_schemas_validate() -> None:
    reg, docs = vr.load_registry()
    vr.RESULTS.clear()
    vr.validate_schemas(reg, docs)
    bad = [(n, d) for n, ok, d in vr.RESULTS if not ok]
    assert not bad, bad


def test_xref_and_index_and_discipline() -> None:
    vr.RESULTS.clear()
    claims, evid, prov = vr.verify_xref()
    vr.verify_index(claims, evid, prov, SHA)
    vr.verify_discipline(claims, evid)
    bad = [(n, d) for n, ok, d in vr.RESULTS if not ok]
    assert not bad, bad


def test_number_checks_agree() -> None:
    d = json.loads((PKG / "number_checks.json").read_text(encoding="utf-8"))
    assert d["n_checks"] >= 10
    assert d["n_agree"] == d["n_checks"], [c["name"] for c in d["checks"] if not c["aggregates"]]


def test_quotes_reproduce_in_source() -> None:
    repo = os.environ.get("TENSORLBM_REPO", "/root/tp-agent/work/m7437")
    if not (Path(repo) / ".git").exists():
        pytest.skip(f"source repo not available at {repo}; quote reproduction not run")
    vr.RESULTS.clear()
    vr.verify_quotes(Path(repo), SHA)
    bad = [(n, d) for n, ok, d in vr.RESULTS if not ok]
    assert not bad, bad