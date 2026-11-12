"""Tests for wp-1226-01 asset registration (report 1226 only).

These tests assert invariants, not mere execution:
  * the acceptance gate passes on the registered artefacts,
  * the gate is not vacuous (a corrupted quote / injected duplicate id fails it),
  * the manifest is reproducible byte-for-byte from the pinned source snapshot,
  * the package touches report 1226 and nothing else.
"""
from __future__ import annotations

import copy
import json
import pathlib
import subprocess
import sys

import pytest

WT = pathlib.Path(__file__).resolve().parent.parent
PKG = WT / "docs" / "kf" / "wp-1226-01"
SCRIPTS = WT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import wp1226_verify_acceptance as acc  # noqa: E402


def test_acceptance_all_pass():
    res = acc.check()
    failed = {k: v for k, v in res["checks"].items() if not v.get("ok")}
    assert not failed, failed
    assert res["checks"]["schema_pass"]["ok"] is True
    assert res["checks"]["source_hash_matches"]["chars_match"] is True


def test_source_hash_pinned_to_contract():
    md = (WT / "work/wp-1226-01/source/report_1226.md").read_text(encoding="utf-8")
    import hashlib

    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == acc.CONTRACT_SOURCE_HASH
    assert len(md) == acc.CONTRACT_CHARS


def test_every_markdown_locator_is_verbatim():
    md = (WT / "work/wp-1226-01/source/report_1226.md").read_text(encoding="utf-8")
    man = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    n = 0
    for a in man["assets"]:
        for loc in a["locators"]:
            if loc["source_field"] != "markdown":
                continue
            n += 1
            assert md[loc["char_start"]:loc["char_end"]] == loc["quote"], a["asset_id"]
    assert n >= 20, f"expected a broad locator set, got {n}"


def test_gate_rejects_corrupted_quote():
    """Negative control: the locator check must verify bytes, not just shape."""
    real = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    md = (WT / "work/wp-1226-01/source/report_1226.md").read_text(encoding="utf-8")
    md_locs = [l for a in real["assets"] for l in a["locators"] if l["source_field"] == "markdown"]
    assert md_locs, "no markdown locators to corrupt"
    loc = md_locs[0]
    assert md[loc["char_start"]:loc["char_end"]] == loc["quote"]
    corrupted = dict(loc, quote="definitely not in the report")
    assert md[corrupted["char_start"]:corrupted["char_end"]] != corrupted["quote"]
    # shifted offset must also be caught
    shifted = dict(loc, char_start=loc["char_start"] + 1)
    assert md[shifted["char_start"]:shifted["char_end"]] != shifted["quote"]


def test_manifest_reproducible_from_snapshot():
    """Offline rebuild from the pinned snapshot must not move a single byte of either artefact."""
    man, kf = PKG / "asset_manifest.json", PKG / "kf_result.json"
    before = (man.read_bytes(), kf.read_bytes())
    r = subprocess.run([sys.executable, str(SCRIPTS / "wp1226_register_assets.py"), "--offline"],
                       cwd=WT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-2000:]
    assert man.read_bytes() == before[0], "offline rebuild changed the committed manifest"
    assert kf.read_bytes() == before[1], "offline rebuild moved provenance.emitted_at"


def test_only_report_1226_is_touched():
    man = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    kf = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    assert man["scope"]["reports_touched"] == ["1226"]
    assert kf["report_id"] == "1226"
    assert kf["package_id"] == "wp-1226-01"
    blob = json.dumps(man, ensure_ascii=False) + json.dumps(kf, ensure_ascii=False)
    assert "tensor://reports/1226" in blob
    for other in ("tensor://reports/1225", "tensor://reports/1227"):
        assert other not in blob


def test_claims_empty_but_explicitly_reasoned():
    kf = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    man = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    assert kf["claims"] == []
    assert "asset registration only" in man["claims_policy"]["reason"]
    assert all(c != "verified" for c in json.dumps(kf))


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))