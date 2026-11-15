"""KF wp-12068-01 — see-through chain + publication-state ledger guards (round 3, m22417).

The original PR#492 (m20257 deliverables) was closed by the owner because the same 10-file
deliverable set had already reached main via PR#436; the follow-through chain then continued with
the offline re-verification layer (PR#493, m22391).  ``docs/kf/wp-12068-01/STATE.json`` records
that chain and the package's current publication state.  These guards make the ledger
machine-checkable instead of prose:

* the publication state must stay ``awaiting_pr_merge`` — no ``verified``/``published`` claim;
* the chain must be sequential (rounds 1..N) with valid states, and the current round must be the
  open one (its PR number is assigned by the platform, so it is ``null`` until then);
* the original PR#492 must be recorded as closed by the owner (the reason for the reopen);
* the offline re-verification block must match a **fresh** run of
  ``scripts/kf/wp12068_01_reverify.py`` — the ledger cannot drift from the actual re-derivation.
"""
import importlib.util
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-12068-01"
STATE = PKG / "STATE.json"
REVERIFY_SCRIPT = REPO / "scripts" / "kf" / "wp12068_01_reverify.py"

PACKAGE_ID = "wp-12068-01"
REPORT_ID = "12068"
MISSION_ID = 15738
VALID_STATES = {"merged", "open", "closed"}


def _state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8"))


def test_state_is_valid_json_and_scoped_to_the_package():
    s = _state()
    assert s["package_id"] == PACKAGE_ID
    assert s["report_id"] == REPORT_ID
    assert s["mission_id"] == MISSION_ID
    assert s["base_ref"] == "main"


def test_publication_state_stays_awaiting_pr_merge():
    s = _state()
    assert s["publication_state"] == "awaiting_pr_merge"
    # no self-promotion, ever: the ledger must not contain a verified/published claim
    blob = STATE.read_text(encoding="utf-8")
    assert '"verified"' not in blob
    assert '"published"' not in blob


def test_chain_is_sequential_with_valid_states():
    s = _state()
    chain = s["chain"]
    assert len(chain) >= 3
    assert [c["round"] for c in chain] == list(range(1, len(chain) + 1))
    for c in chain:
        assert c["state"] in VALID_STATES, c
        assert isinstance(c["mission_id"], int) and c["mission_id"] > 0
    # the merged rounds carry their PR numbers; the current round is open and unnumbered
    for c in chain[:-1]:
        assert c["state"] == "merged" and isinstance(c["pr"], int)
    assert chain[-1]["state"] == "open"
    assert chain[-1]["pr"] is None
    assert chain[-1]["mission_id"] == 22417


def test_original_pr_492_recorded_as_closed_by_owner():
    s = _state()
    op = s["original_pr"]
    assert op["pr"] == 492
    assert op["state"] == "closed"
    assert op["closed_by"] == "owner"
    assert op["closed_at"]
    # the closure reason must point at the duplicate merge, not at a quality verdict
    assert "436" in op["reason"]


def test_offline_reverify_block_matches_a_fresh_run(tmp_path):
    """The ledger's offline block is re-derived, not trusted: run the checker into tmp_path."""
    spec = importlib.util.spec_from_file_location("wp12068_01_reverify_under_test", REVERIFY_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
        result = mod.cmd_verify(live=False, out=tmp_path / "reverify.json")
    finally:
        sys.modules.pop(spec.name, None)
    assert result["all_pass"] is True, "the package itself must still re-verify offline"
    block = _state()["verification"]["offline_reverify"]
    assert block["n_checks"] == result["n_checks"]
    assert block["all_pass"] is result["all_pass"]
    # the checker wrote its record to the temp dir, not over the shipped reverify.json
    assert (tmp_path / "reverify.json").exists()


def test_live_drift_block_is_honest():
    """A live observation must say whether it was checked; a skip must not masquerade as a pass."""
    live = _state()["verification"]["live_drift"]
    assert live["checked"] is True
    assert live["drift"] is False
    assert live["live_sha256"] == "de2f16253ed522c619246898f442983d5a66f3a2bec42c2fe271847a2020cbf0"
    assert live["checked_at"]
