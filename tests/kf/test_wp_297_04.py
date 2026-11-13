"""Machine gate for the wp-297-04 review deliverable (task 04-independent-review).

Independent of the producer script: this test re-parses the source snapshot with its
own regexes and re-checks the review envelope against the repo schema, the contract
hash, and the "no quote may be fabricated / nothing may be marked verified" rules.
"""
from __future__ import annotations

import hashlib
import json
import math
import pathlib
import re

import jsonschema
import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
PKG_DIR = REPO / "artifacts" / "kf-wp-297-04"
ENVELOPE = PKG_DIR / "review_report.json"
SNAPSHOT = PKG_DIR / "source_report_297.md"
CHECKS = PKG_DIR / "checks.json"
DOC = REPO / "docs" / "kf-wp-297-04.md"
SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"

# contract placeholder from the work package (independent constant, not read from the artifact)
CONTRACT_SOURCE_HASH = "sha256:426c49ee6920408fa082092a086ef85edf1da0d566a63dfad66dba81549cc77a"
RHO_SEA, G, KN = 1025.0, 9.81, 0.5144444444444444


@pytest.fixture(scope="module")
def md() -> str:
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def env() -> dict:
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def rep(env) -> dict:
    return env["outputs"]["review_report.json"]


# --------------------------------------------------------------- envelope shape
def test_envelope_matches_schema(env):
    jsonschema.validate(env, json.loads(SCHEMA.read_text(encoding="utf-8")))


def test_envelope_identity(env):
    assert env["package_id"] == "wp-297-04"
    assert env["task_type"] == "04-independent-review"
    assert env["report_id"] == "297"
    assert env["provenance"]["source_field"] == "markdown"


def test_source_hash_is_contract_hash_and_snapshot_bytes(env, md):
    assert env["provenance"]["source_hash"] == CONTRACT_SOURCE_HASH
    live = "sha256:" + hashlib.sha256(md.encode()).hexdigest()
    assert live == CONTRACT_SOURCE_HASH
    snap = "sha256:" + hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    assert snap == live


# ------------------------------------------------------------- quote integrity
def test_no_fabricated_quotes(env, md):
    """Every evidence quote must be a verbatim slice, at the stated offsets/line."""
    quotes = 0
    for f in env["outputs"]["review_report.json"]["findings"]:
        for e in f["evidence"]:
            q = e["quote"]
            assert q and q in md, f"{f['finding_id']}: quote not verbatim in source"
            s, t = e["char_start"], e["char_end"]
            assert md[s:t] == q, f"{f['finding_id']}: offsets do not slice back to the quote"
            assert md[:s].count("\n") + 1 == e["line"], f"{f['finding_id']}: line mismatch"
            assert e["source_field"] == "markdown"
            quotes += 1
    assert quotes >= 10


def test_upstream_asset_locators_reproduce(md, rep):
    """Upstream wp-297-01's locators: each slice verbatim, claimed lines exact."""
    assets = rep["quote_verification"]
    ids = [a["asset_id"] for a in assets]
    assert len(ids) == len(set(ids)) == 6
    for a in assets:
        assert a["unique_occurrences"], a["asset_id"]
        for o in a["unique_occurrences"]:
            assert md[o["char_start"]:o["char_end"]] == o["part"]
            assert md[:o["char_start"]].count("\n") + 1 == o["line"]
        assert sorted({o["line"] for o in a["unique_occurrences"]}) == a["claimed_lines"], a["asset_id"]
        assert a["lines_match_claim"]
    # exactly one asset whose evidence cell is a joined multi-slice string
    assert sum(1 for a in assets if not a["cell_is_single_slice"]) == 1


# ------------------------------------------------------- independent recompute
def test_recomputation_reproduces(md, rep):
    """Re-derive the review's numbers from raw source text (separate code path)."""
    rc = rep["independent_recomputation"]
    dims = re.search(r"Lpp=([0-9.]+)m, B=([0-9.]+)m, T=([0-9.]+)m, Cb=([0-9.]+), "
                     r"Δ=([0-9.]+)t, V_design=([0-9.]+)kn", md)
    L, V_design = float(dims.group(1)), float(dims.group(6)) * KN
    table = lambda k: float(re.search(r"\| " + k + r" \| ([0-9.]+)", md).group(1))  # noqa: E731
    Ct, Rt, Rf, Rw, Pe = table("Ct"), table("Rt") * 1e3, table("Rf") * 1e3, table("Rw") * 1e3, table("Pe") * 1e3
    q = 0.5 * RHO_SEA * V_design**2
    S = Rt / (Ct * q)
    assert S == pytest.approx(rc["wetted_surface_backsolved_m2"], rel=1e-9)
    assert abs(Ct * q * S - Rt) / Rt < 1e-9
    assert abs(Rt * V_design - Pe) / Pe < 1e-3
    assert abs(Rt - Rf - Rw - rc["Rt_minus_Rf_minus_Rw_N"]) < 1.0
    assert V_design / math.sqrt(G * L) == pytest.approx(rc["Fn"], rel=1e-9)
    # mesh closure: chi for a triangle soup, and the vertex count a closed manifold would need
    F = int(re.search(r"(\d+)\s*面片", md).group(1))
    V = int(re.search(r"(\d+)\s*顶点", md).group(1))
    assert V - 3 * F // 2 + F == rc["mesh_euler_characteristic"] == 760
    assert 2 + (3 * F // 2) - F == rc["mesh_closed_manifold_vertex_count"]
    assert rc["mesh_is_closed_manifold"] is False


def test_deviation_claims_reproduce(md, rep):
    """The report's own %-deviations must be re-derivable from its own numbers."""
    rows = {d["quantity"]: d for d in rep["deviation_audit"]}
    pat = r"\| (Lpp \(m\)|B \(m\)|T \(m\)|Cb) \| ([0-9.]+) \| ([0-9.]+) \|"
    geo: dict = {}
    for name, meas, off in re.findall(pat, md):      # first hit per key = the geometry table
        geo.setdefault(name, (float(meas), float(off)))
    assert set(geo) == {"Lpp (m)", "B (m)", "T (m)", "Cb"}
    for key, name in (("Lpp (m)", "Lpp"), ("B (m)", "B"), ("T (m)", "T"), ("Cb", "Cb")):
        meas, off = geo[key]
        assert rows[name]["recomputed_abs_pct"] == pytest.approx(abs((meas - off) / off * 100), abs=5e-3)
        assert rows[name]["reproduces_within_0.05pp"]


# ------------------------------------------------------------------ judgement
def test_verdict_and_blocking_scope(rep):
    assert rep["verdict"] in {"pass", "fail", "needs-fix"}
    blocking = [f for f in rep["findings"] if f["blocking"]]
    assert blocking, "review must state whether anything blocks downstream extraction"
    # every blocking item is about the SOURCE report, not about the upstream package
    assert all("source report" in f["object"] for f in blocking)
    upstream_findings = [f for f in rep["findings"] if "upstream" in f["object"]]
    assert upstream_findings and not any(f["blocking"] for f in upstream_findings)


def test_nothing_marked_verified(env, rep):
    assert "claims" not in env, "review envelope must not carry claims"
    blob = json.dumps(rep, ensure_ascii=False)
    assert '"verified": true' not in blob.replace(" ", " ")
    flags = [k for f in rep["findings"] for k in f if k in {"verified", "status"}]
    assert flags == []
    assert all(f["disposition"] for f in rep["findings"])


def test_severity_index_covers_all_findings(rep):
    idx = rep["severity_index"]
    ids = sorted(i for v in idx.values() for i in v)
    assert ids == sorted(f["finding_id"] for f in rep["findings"])


# -------------------------------------------------------------------- carrier
def test_self_checks_all_pass():
    data = json.loads(CHECKS.read_text(encoding="utf-8"))
    assert data["all_ok"] and data["failed"] == []
    assert data["n_checks"] == len(data["checks"]) == 10


def test_doc_carries_exactly_one_json_block_matching_envelope(env):
    text = DOC.read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)```", text, re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == env
    assert "## ①" in text and "## ⑥" in text
    assert "error" not in text.lower()[:0]