"""Independent re-check of the wp-14445-01 asset registration (report 14445).

Hermetic: the test never calls the platform API.  It re-derives every acceptance
property from two committed artefacts:

  * ``runs/wp-14445-01/source_14445.md``      — byte snapshot of the report markdown
  * ``docs/kf/wp-14445-01/asset_manifest.json`` / ``kf_result.json``

The producer (``scripts/kf/kf01_register.py --preset wp-14445-01``) computed these
locators; this test recomputes them from the snapshot instead of trusting the
producer's own self-check, so a stale or hand-edited manifest fails here.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
PKG_DIR = REPO / "docs" / "kf" / "wp-14445-01"
SNAPSHOT = REPO / "runs" / "wp-14445-01" / "source_14445.md"

# contract values (work package wp-14445-01)
CONTRACT_HASH = "0fad2f03c7cceceba726538a60a0c9e206b0a932e9d53e10f5e32388da25c85b"
CONTRACT_CHARS = 8040
PACKAGE_ID = "wp-14445-01"
REPORT_ID = "14445"
ACCEPTANCE = (
    "valid_json",
    "schema_pass",
    "source_locator_resolvable",
    "source_hash_matches",
    "no_duplicate_ids",
    "all_claims_have_evidence_or_explicit_unresolved_status",
)


@pytest.fixture(scope="module")
def md() -> str:
    assert SNAPSHOT.is_file(), "missing committed snapshot %s" % SNAPSHOT
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((PKG_DIR / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def result() -> dict:
    return json.loads((PKG_DIR / "kf_result.json").read_text(encoding="utf-8"))


def test_source_snapshot_hash_and_length(md):
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_report_scoped_to_14445(manifest, result):
    assert manifest["report_id"] == result["report_id"] == REPORT_ID
    assert result["package_id"] == PACKAGE_ID
    assert result["task_type"] == "01-asset-registration"


def test_envelope_source_hash_matches_contract(result, manifest):
    assert result["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == CONTRACT_CHARS


def test_every_locator_resolves_against_snapshot(md, manifest):
    """>= the gate's locator check: char span slices back to the identical quote,
    the 1-based line map agrees, and inline token spans sit inside the span."""
    line_starts = [0]
    for line in md.split("\n")[:-1]:
        line_starts.append(line_starts[-1] + len(line) + 1)

    def line_of(pos: int) -> int:  # 1-based
        lo, hi = 0, len(line_starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if line_starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    assert manifest["assets"], "manifest has no assets"
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        assert 0 <= s < e <= len(md), a["asset_id"]
        assert md[s:e] == q, "char span does not slice back to the quote: %s" % a["asset_id"]
        assert q in md
        assert line_of(s) == loc["start_line"], a["asset_id"]
        assert line_of(e - 1) == loc["end_line"], a["asset_id"]
        if "token" in loc:
            ts, te = loc["token_span"]
            assert md[ts:te] == loc["token"], a["asset_id"]
            assert s <= ts < te <= e, a["asset_id"]


def test_asset_ids_unique_and_sequential(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert ids == ["A%02d" % i for i in range(1, len(ids) + 1)]


def test_resolution_vocabulary(manifest):
    allowed = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
    for a in manifest["assets"]:
        assert a["resolution"] in allowed, a["asset_id"]
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent", "present"}
    # nothing outside this worktree may be claimed as resolved
    assert manifest["counts"]["assets"] == len(manifest["assets"])
    assert manifest["counts"]["by_resolution"]["resolved_in_source"] == sum(
        1 for a in manifest["assets"] if a["resolution"] == "resolved_in_source"
    )


def test_claims_empty_and_nothing_marked_verified(manifest, result):
    assert manifest["claims"] == []
    assert result["claims"] == []
    blob = json.dumps(manifest, ensure_ascii=False) + json.dumps(result, ensure_ascii=False)
    assert '"verified"' not in blob


def test_registered_figures_carry_no_fabricated_hash(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    assert len(figs) == 3  # record.figures[] of report 14445
    for a in figs:
        assert a.get("sha256") is None and a.get("bytes") is None, (
            "figure bytes were never fetched, so no hash/size may be claimed: %s" % a["asset_id"])
        assert a["resolution"] == "referenced_unresolved"


def test_envelope_manifest_hash_matches_file(result):
    raw = (PKG_DIR / "asset_manifest.json").read_bytes()
    assert result["outputs"]["asset_manifest.json"]["sha256"] == hashlib.sha256(raw).hexdigest()


def test_report_publishes_exactly_one_json_block_and_all_acceptance_pass():
    text = (PKG_DIR / "report.md").read_text(encoding="utf-8")
    assert text.count("```json") == 1
    block = re.search(r"```json\n(.*?)\n```", text, re.S).group(1)
    envelope = json.loads(block)
    assert envelope == json.loads((PKG_DIR / "kf_result.json").read_text(encoding="utf-8"))
    assert text.startswith("# KF-RESULT %s" % PACKAGE_ID)

    verdict = json.loads((PKG_DIR / "verification.json").read_text(encoding="utf-8"))
    assert set(ACCEPTANCE) <= set(verdict["checks"])
    failed = {k: v for k, v in verdict["checks"].items() if not v["pass"]}
    assert not failed, "acceptance failures: %s" % failed
    assert verdict["all_pass"] is True