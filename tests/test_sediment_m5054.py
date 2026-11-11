"""Guard the m5054 sediment package (knowledge/sediment/m5054).

The package is only worth anything if its quotes still match the source commit
and its numbers still match the source artifacts, so the validator is run as a
test instead of being a one-off script.  Quote checks need the TensorSPH
checkout that holds sha 82b72a15; without it the test skips (honest NOT_RUN,
never a silent pass).
"""
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "knowledge" / "sediment" / "m5054"
SRC = Path(os.environ.get("TENSORSPH_REPO", "/root/tp-agent/work/m5054"))

pytest.importorskip("jsonschema")


@pytest.mark.skipif(not (SRC / ".git").exists(),
                    reason="TensorSPH source checkout (sha 82b72a15) not available")
def test_sediment_m5054_validates():
    proc = subprocess.run(["python3", str(PKG / "validate_m5054.py")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout[-3000:] + proc.stderr[-2000:]
    assert "checks passed" in proc.stdout


def test_sediment_m5054_has_four_contracts_and_no_self_review():
    import json

    claims = sorted((PKG / "claims").glob("*.json"))
    evidence = sorted((PKG / "evidence").glob("*.json"))
    prov = sorted((PKG / "provenance").glob("*.json"))
    assert len(claims) >= 3
    assert len(evidence) >= len(claims)
    assert len(prov) == len(claims)
    assert not list(PKG.rglob("*review*")), "producer must not write review events"
    for p in claims:
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert rec["epistemic_status"] == "provisional"   # schema-side draft
        assert rec["evidence_refs"]
    for p in evidence:
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert rec["assessment_status"] == "unassessed"
        assert len(rec["locator"]["quote"]) >= 20
    for p in prov:
        rec = json.loads(p.read_text(encoding="utf-8"))
        assert "5054" in rec["derived_from"]
        assert rec["activity"]["parameters"]["task_key"] == "tk-sediment-m5054"
    assert (PKG / "INDEX.md").is_file()
