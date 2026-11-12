"""Guards for KF work package wp-7840-01 (01-asset-registration, report_id=7840).

These tests assert *invariants* of the delivered manifest, not merely that the builder ran:
every locator must still resolve against the live source, every path token in the body must be
covered by a registered asset, ids must be unique, and nothing may be marked verified.

Scope: only report_id=7840 is touched (no other report is fetched).

Run:  pytest -q tests/test_kf_wp_7840_01.py
      (live-source tests skip if TENSOR_AGENT_USER / TENSOR_API_BASE are not set)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-7840-01"
MANIFEST = json.loads((PKG_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
RESULT = json.loads((PKG_DIR / "kf_result.json").read_text(encoding="utf-8"))

REPORT_ID = "7840"
CONTRACT_HASH = "eaf940b5a606c4b1ad613ea2283219434fb88265bee60999953e2f33d35a2a3d"
CONTRACT_CHARS = 6896
CODE_EXT = r"(?:json|png|py|md|txt|csv|ya?ml|sql|sh)"


def _live_markdown():
    base = os.environ.get("TENSOR_API_BASE")
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        pytest.skip("platform credentials not set; live-source checks not run")
    base = base.rstrip("/")

    def post(url, body, ctype="application/json"):
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", ctype)
        return json.loads(urllib.request.urlopen(req, timeout=30).read().decode())

    d = post(base + "/auth/login", json.dumps({"username": user, "password": pwd}).encode())
    tok = d.get("access_token") or d.get("token")
    req = urllib.request.Request(base + "/tensor/reports/%s" % REPORT_ID)
    req.add_header("Authorization", "Bearer " + tok)
    rec = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    if isinstance(rec.get("data"), dict):
        rec = rec["data"]
    return rec, rec["markdown"]


# ------------------------------------------------------------------ static invariants


def test_envelope_shape_matches_kf_result_v1():
    assert set(RESULT) <= {"package_id", "task_type", "report_id", "provenance", "outputs", "claims"}
    assert RESULT["package_id"] == "wp-7840-01"
    assert RESULT["task_type"] == "01-asset-registration"
    assert RESULT["report_id"] == REPORT_ID
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", RESULT["provenance"]["source_hash"])
    assert RESULT["provenance"]["source_field"] == "markdown"
    assert "asset_manifest.json" in RESULT["outputs"]
    # the envelope must point at the manifest bytes it actually shipped
    assert RESULT["outputs"]["asset_manifest.json"]["sha256"] == hashlib.sha256(
        (PKG_DIR / "asset_manifest.json").read_bytes()).hexdigest()


def test_single_report_scope():
    assert MANIFEST["report_id"] == REPORT_ID
    assert MANIFEST["provenance"]["source_uri"] == "tensor://reports/7840"


def test_hash_and_char_count_pinned_by_contract():
    assert MANIFEST["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert MANIFEST["provenance"]["source_chars"] == CONTRACT_CHARS
    assert MANIFEST["provenance"]["source_bytes_utf8"] > CONTRACT_CHARS  # CJK markdown: bytes > chars


def test_asset_ids_unique_and_non_empty():
    ids = [a["asset_id"] for a in MANIFEST["assets"]]
    assert ids and len(ids) == len(set(ids))


def test_every_asset_has_locator_and_known_resolution_status():
    vocab = {"resolved", "unresolved", "metadata_only"}
    for a in MANIFEST["assets"]:
        loc = a["locator"]
        assert loc["scheme"] in {"markdown_line", "report_field"}, a["asset_id"]
        assert a["resolution"]["status"] in vocab, a["asset_id"]
        if loc["scheme"] == "markdown_line":
            assert isinstance(loc["line"], int) and loc["line"] >= 1
            assert isinstance(loc["quote"], str) and loc["quote"]


def test_constructed_paths_are_disclosed():
    """No inferred path may masquerade as verbatim source text."""
    for a in MANIFEST["assets"]:
        if "path_reference" not in a:
            continue
        assert "path_reference_literal" in a, a["asset_id"]
        assert a["path_reference_constructed"] == (a["path_reference"] != a["path_reference_literal"])


def test_metadata_only_figures_claim_no_hash():
    for a in MANIFEST["assets"]:
        if a["kind"] == "embedded_figure":
            assert a["resolution"]["status"] == "metadata_only"
            assert a["sha256"] is None


def test_no_claims_and_nothing_verified():
    assert MANIFEST["claims"] == []
    assert RESULT.get("claims", []) == []
    for c in MANIFEST["claims"] + RESULT.get("claims", []):
        assert c["status"] != "verified"


def test_coverage_sweep_is_gap_free():
    sweep = MANIFEST["coverage_sweep"]
    assert sweep["sweep_token_count"] > 0
    assert sweep["unregistered_tokens"] == []


def test_counts_agree_with_asset_list():
    counts = MANIFEST["counts"]
    assert counts["assets"] == len(MANIFEST["assets"])
    assert sum(counts["by_resolution"].values()) == len(MANIFEST["assets"])
    for kind, n in counts["by_kind"].items():
        assert n == sum(1 for a in MANIFEST["assets"]
                        if "%s/%s" % (a["kind"], a["resolution"]["status"]) == kind)


# ------------------------------------------------------------------ live-source invariants


def test_live_source_hash_matches_contract_and_envelope():
    _rec, md = _live_markdown()
    live = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert live == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    assert len(md.encode("utf-8")) == MANIFEST["provenance"]["source_bytes_utf8"]
    assert RESULT["provenance"]["source_hash"] == "sha256:" + live


def test_every_locator_quote_is_verbatim_in_live_source():
    rec, md = _live_markdown()
    lines = md.split("\n")
    for a in MANIFEST["assets"]:
        loc = a["locator"]
        if loc["scheme"] == "markdown_line":
            quote = loc["quote"]
            assert quote in md, a["asset_id"]
            assert lines[loc["line"] - 1] == quote, a["asset_id"]
        elif loc.get("field") == "figures":
            assert 0 <= loc["index"] < len(rec.get("figures") or []), a["asset_id"]


def test_scan_misses_nothing_an_independent_tokeniser_finds():
    _rec, md = _live_markdown()
    tok_re = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_./*-]*\." + CODE_EXT)
    registered = {a["path_reference_literal"] for a in MANIFEST["assets"] if "path_reference_literal" in a}
    basenames = {t.rsplit("/", 1)[-1] for t in registered}
    missing = set()
    for line in md.split("\n"):
        for m in tok_re.finditer(line):
            tok = m.group(0)
            if tok not in registered and tok.rsplit("/", 1)[-1] not in basenames:
                missing.add(tok)
    assert not missing, sorted(missing)
