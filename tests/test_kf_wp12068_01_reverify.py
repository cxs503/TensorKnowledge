"""wp-12068-01 follow-through: the package must stay re-verifiable **without** platform access.

``tests/test_kf_wp12068_01.py`` already re-resolves each locator against the live platform markdown
and skips when the API is unreachable — which means a no-network run never re-proves anything. These
tests cover the pinned-source layer that closes that hole:

* the pinned markdown is byte-identical to the contract hash (no re-typing, no drift);
* every hash/locator/count the package claims is re-derived here, with an implementation written
  independently of ``scripts/kf/wp12068_01_reverify.py`` (a bug in the checker cannot certify itself
  through cross-import; the checker is additionally exercised end-to-end as a subprocess);
* the checker actually **fails** on tampering, so a green run means something;
* publication discipline: nothing is claimed as verified/published, state stays awaiting_pr_merge.
"""
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-12068-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
PINNED = PKG / "source" / "report-12068.md"
PIN = PKG / "source" / "source_manifest.json"
REVERIFY = PKG / "reverify.json"
SCRIPT = REPO / "scripts" / "kf" / "wp12068_01_reverify.py"

CONTRACT_HASH = "de2f16253ed522c619246898f442983d5a66f3a2bec42c2fe271847a2020cbf0"
CONTRACT_CHARS = 1086
CONTRACT_BYTES = 1113
REPORT_ID = "12068"
PACKAGE_ID = "wp-12068-01"


def _load_script():
    spec = importlib.util.spec_from_file_location("wp12068_01_reverify", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text())


@pytest.fixture(scope="module")
def md():
    return PINNED.read_bytes().decode("utf-8")


# --------------------------------------------------------------------------- the pin
def test_pinned_source_is_the_contract_bytes():
    raw = PINNED.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert len(raw) == CONTRACT_BYTES
    assert len(raw.decode("utf-8")) == CONTRACT_CHARS


def test_pin_record_matches_the_pinned_bytes():
    pin = json.loads(PIN.read_text())
    raw = PINNED.read_bytes()
    assert pin["package_id"] == PACKAGE_ID
    assert pin["report_id"] == REPORT_ID
    assert pin["sha256"] == hashlib.sha256(raw).hexdigest() == pin["contract_hash"]
    assert pin["chars"] == CONTRACT_CHARS and pin["bytes_utf8"] == CONTRACT_BYTES
    assert pin["contract_hash_matches"] is True
    assert pin["path"].endswith("docs/kf/wp-12068-01/source/report-12068.md")
    # metadata-only figures recorded with zero payload bytes, never a fabricated hash
    figs = pin["platform"]["figures"]
    assert [f["name"] for f in figs] == [
        "sod_shock_tube", "lax_shock_tube", "isentropic_vortex",
        "double_mach_reflection", "supersonic_cylinder",
    ]
    assert all(f["png_bytes"] == 0 for f in figs)


def test_package_hashes_all_agree_with_the_pin(manifest):
    envelope = json.loads(ENVELOPE.read_text())
    digest = hashlib.sha256(PINNED.read_bytes()).hexdigest()
    assert manifest["source"]["hash"] == digest
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert envelope["provenance"]["source_hash"] == f"sha256:{digest}"
    assert envelope["provenance"]["source_chars"] == CONTRACT_CHARS
    assert str(manifest["report_id"]) == str(envelope["report_id"]) == REPORT_ID


# ------------------------------------------------- locators re-derived independently
def test_every_locator_resolves_against_the_pinned_bytes(md, manifest):
    for asset in manifest["assets"]:
        loc = asset["locator"]
        s, e = loc["start_char"], loc["end_char"]
        assert 0 <= s < e <= len(md), asset["asset_id"]
        assert md[s:e] == loc["quote"], f"{asset['asset_id']}: quote is not the source slice"
        assert md.count(loc["quote"]) == 1, f"{asset['asset_id']}: quote is ambiguous"
        assert md.count("\n", 0, s) + 1 == loc["start_line"], f"{asset['asset_id']}: start_line"
        assert md.count("\n", 0, e - 1) + 1 == loc["end_line"], f"{asset['asset_id']}: end_line"


def test_resolved_assets_use_real_spans_and_figures_do_not_overclaim(md, manifest):
    for asset in manifest["assets"]:
        loc = asset["locator"]
        if asset["resolution"] == "resolved_in_source" and asset["asset_class"] != "report_markdown":
            # every *resolvable* asset is a precise span; the document-level self-record is not
            assert loc["method"] == "char_span", asset["asset_id"]
            assert (loc["start_char"], loc["end_char"]) != (0, len(md)), asset["asset_id"]
        if asset["asset_class"] == "embedded_figure":
            assert asset["resolution"] == "referenced_unresolved", asset["asset_id"]
            assert loc["method"] == "document", asset["asset_id"]
            # the honest claim "the figure names never appear in the body" is checkable
            assert asset["label"] not in md


def test_counts_are_recomputed_not_trusted(manifest):
    by_class, by_res = {}, {}
    for asset in manifest["assets"]:
        by_class[asset["asset_class"]] = by_class.get(asset["asset_class"], 0) + 1
        by_res[asset["resolution"]] = by_res.get(asset["resolution"], 0) + 1
    counts = manifest["counts"]
    assert counts["assets"] == len(manifest["assets"]) == 9
    assert counts["by_class"] == by_class
    assert counts["by_resolution"] == by_res
    assert counts["resolved_in_source"] == 4 and counts["referenced_unresolved"] == 5


# ------------------------------------------------------------- the checker end-to-end
def test_checker_runs_offline_and_passes(tmp_path):
    out = tmp_path / "reverify.json"
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "verify", "--check", "--out", str(out)],
        cwd=REPO, capture_output=True, text=True, timeout=180,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    result = json.loads(out.read_text())
    assert result["all_pass"] is True
    assert result["n_fail"] == 0
    assert result["mode"] == "offline+pinned"          # no network was used
    assert not any(c["id"] == "live_source_matches_pin" for c in result["checks"])


def test_shipped_reverify_record_is_honest():
    result = json.loads(REVERIFY.read_text())
    assert result["package_id"] == PACKAGE_ID and result["report_id"] == REPORT_ID
    assert result["all_pass"] is True
    assert result["n_checks"] == len(result["checks"])
    assert result["n_checks"] == result["n_pass"] + result["n_fail"] + result["n_skipped"]
    assert result["publication_state"] == "awaiting_pr_merge"
    assert result["pinned_source"]["sha256"] == CONTRACT_HASH
    # no self-promotion, ever
    blob = json.dumps(result)
    assert '"verified"' not in blob and '"published"' not in blob
    live = result["live_drift"]
    if live["checked"]:
        assert live["drift"] is False and live["live_sha256"] == CONTRACT_HASH
    else:
        # a skipped live check must say so, never masquerade as a pass
        assert "unavailable" in live["detail"] or "not requested" in live["detail"]


def test_checker_detects_tampering(tmp_path, monkeypatch):
    """A green run must mean something: corrupt one quote and the same code must fail."""
    module = _load_script()
    pkg = tmp_path / "wp-12068-01"
    (pkg / "source").mkdir(parents=True)
    shutil.copy2(MANIFEST, pkg / "asset_manifest.json")
    shutil.copy2(ENVELOPE, pkg / "kf_result.json")
    shutil.copy2(PIN, pkg / "source" / "source_manifest.json")
    shutil.copy2(PINNED, pkg / "source" / "report-12068.md")
    monkeypatch.setattr(module, "PKG", pkg)
    monkeypatch.setattr(module, "MANIFEST", pkg / "asset_manifest.json")
    monkeypatch.setattr(module, "ENVELOPE", pkg / "kf_result.json")
    monkeypatch.setattr(module, "SOURCE_DIR", pkg / "source")
    monkeypatch.setattr(module, "PINNED_SOURCE", pkg / "source" / "report-12068.md")
    monkeypatch.setattr(module, "SOURCE_MANIFEST", pkg / "source" / "source_manifest.json")
    monkeypatch.setattr(module, "REVERIFY", pkg / "reverify.json")

    clean = module.cmd_verify()
    assert clean["all_pass"] is True

    tampered = json.loads((pkg / "asset_manifest.json").read_text())
    tampered["assets"][6]["locator"]["quote"] += " "          # plausible-looking, still wrong
    (pkg / "asset_manifest.json").write_text(json.dumps(tampered, ensure_ascii=False))
    dirty = module.cmd_verify()
    assert dirty["all_pass"] is False
    failed = {c["id"] for c in dirty["checks"] if c["pass"] is False}
    assert "locator_quotes_re_slice_verbatim" in failed
    assert "delivered_manifest_matches_envelope" in failed

    # a source that drifts from the contract hash must also be caught
    (pkg / "asset_manifest.json").write_text(
        json.dumps(json.loads(MANIFEST.read_text()), ensure_ascii=False))
    (pkg / "source" / "report-12068.md").write_bytes(PINNED.read_bytes() + b"\n")
    drifted = module.cmd_verify()
    assert drifted["all_pass"] is False
    assert {c["id"] for c in drifted["checks"] if c["pass"] is False} >= {
        "pinned_source_hash_matches_pin", "pinned_source_matches_contract"}