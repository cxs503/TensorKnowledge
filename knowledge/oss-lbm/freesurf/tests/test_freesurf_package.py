"""Pytest wrapper for the freesurf knowledge subpackage.

Runs:
1. parent package validator (knowledge/oss-lbm/validate_oss_lbm.py)
2. freesurf subpackage validator (validate_freesurf.py, incl. verbatim quote gate)
3. jsonschema conformance of all three JSON files against repo schemas
4. verbatim quote check against the source cache (skipped if cache absent)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
OSS_LBM = PKG.parent
REPO_ROOT = OSS_LBM.parent.parent
SCHEMAS = REPO_ROOT / "schemas"
CACHE = Path("/root/oss-cache/Maarten-vd-Sande_lbm")


def _run_validator(script: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(script)],
        capture_output=True, text=True, timeout=300,
    )


def test_parent_validator_green():
    r = _run_validator(OSS_LBM / "validate_oss_lbm.py")
    assert r.returncode == 0, f"parent validator failed:\n{r.stdout}\n{r.stderr}"


def test_freesurf_validator_green():
    r = _run_validator(PKG / "validate_freesurf.py")
    assert r.returncode == 0, f"freesurf validator failed:\n{r.stdout}\n{r.stderr}"


def test_claim_count_at_least_8():
    claims = json.loads((PKG / "claims" / "claims.json").read_text(encoding="utf-8"))
    assert len(claims) >= 8, f"expected >=8 claims, got {len(claims)}"


def test_schema_conformance():
    try:
        import jsonschema
    except ImportError:
        import pytest
        pytest.skip("jsonschema not installed")
    files = {
        "claims/claims.json": "claim-record.schema.json",
        "evidence/evidence.json": "evidence-record.schema.json",
        "provenance/provenance.json": "provenance-record.schema.json",
    }
    for rel, schema_name in files.items():
        items = json.loads((PKG / rel).read_text(encoding="utf-8"))
        schema = json.loads((SCHEMAS / schema_name).read_text(encoding="utf-8"))
        for item in items:
            jsonschema.validate(instance=item, schema=schema)


def test_verbatim_quotes_against_cache():
    import pytest
    if not CACHE.is_dir():
        pytest.skip("source cache /root/oss-cache/Maarten-vd-Sande_lbm absent")
    evidence = json.loads((PKG / "evidence" / "evidence.json").read_text(encoding="utf-8"))
    for ev in evidence:
        loc = ev["locator"]
        m = re.match(r"^Maarten-vd-Sande/lbm@[0-9a-f]+ (\S+):(\d+)(?:-(\d+))?$", loc["value"])
        assert m, f"unparseable locator: {loc['value']}"
        path, lo = m.group(1), int(m.group(2))
        hi = int(m.group(3) or m.group(2))
        lines = (CACHE / path).read_text(encoding="utf-8").splitlines()
        actual = lines[lo - 1:hi]
        quote = loc["quote"].split("\n")
        assert len(quote) <= 3, f"{ev['id']}: quote has {len(quote)} lines"
        assert actual == quote, (
            f"{ev['id']}: quote not verbatim at {path}:{lo}-{hi}\n"
            f"file={actual!r}\nquote={quote!r}"
        )


def test_every_claim_has_gap_anchor():
    claims = json.loads((PKG / "claims" / "claims.json").read_text(encoding="utf-8"))
    for c in claims:
        assert any("GAP-" in n for n in c.get("notes", [])), f"{c['id']} missing GAP anchor"


def test_no_self_approval():
    evidence = json.loads((PKG / "evidence" / "evidence.json").read_text(encoding="utf-8"))
    for ev in evidence:
        assert ev["assessment_status"] == "unassessed", f"{ev['id']} self-approved"
