"""Acceptance tests for KF work package wp-5656-01 (01-asset-registration).

Positive: every contract acceptance item passes on the committed artifacts.
Negative: the verifier is shown to *fail* on the failure modes it claims to catch,
so the green result above is not the vacuous kind (a test that only executes code).

Run: pytest tests/kf/test_wp_5656_asset_manifest.py -q
Offline: reads only files in this worktree (no API calls).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "scripts", "kf"))

import verify_asset_manifest as V  # noqa: E402

MANIFEST = os.path.join(ROOT, "docs/kf/wp-5656-01/asset_manifest.json")
SOURCE = os.path.join(ROOT, "runs/wp-5656-01/source_5656.json")
KF = os.path.join(ROOT, "docs/kf/wp-5656-01/kf_result.json")
LOCAL_MD = os.path.join(ROOT, "runs/wp-5656-01/report_5656.md")


@pytest.fixture(scope="module")
def manifest():
    return json.load(open(MANIFEST, encoding="utf-8"))


@pytest.fixture(scope="module")
def source():
    return json.load(open(SOURCE, encoding="utf-8"))


def test_all_acceptance_checks_pass():
    res = V.verify(MANIFEST, SOURCE, KF)
    failed = {k: v["detail"] for k, v in res.items() if not v["ok"]}
    assert not failed, failed


def test_contract_identity_and_hash(manifest, source):
    assert manifest["package_id"] == "wp-5656-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "5656"
    assert manifest["source"]["uri"] == "tensor://reports/5656"
    assert manifest["source"]["hash"] == V.CONTRACT_HASH
    assert manifest["source"]["hash"] == hashlib.sha256(source["markdown"].encode("utf-8")).hexdigest()
    assert manifest["source"]["chars"] == V.CONTRACT_CHARS == len(source["markdown"])


def test_local_copy_hash_equals_source_hash():
    raw = open(LOCAL_MD, "rb").read()
    assert hashlib.sha256(raw).hexdigest() == V.CONTRACT_HASH


def test_every_quote_is_verbatim_and_unique(manifest, source):
    md = source["markdown"]
    for a in manifest["assets"]:
        loc = a["locator"]
        if loc.get("method") == "char_span":
            assert md[loc["start_char"]:loc["end_char"]] == loc["quote"], a["asset_id"]
            assert md.count(loc["quote"]) == 1, a["asset_id"]
            assert loc["unique"] is True


def test_no_asset_claimed_verified(manifest):
    blob = json.dumps(manifest)
    assert '"verified": true' not in blob
    assert manifest["claims"] == []


def test_only_report_5656_touched(manifest):
    """Boundary: no other report_id may appear as the registered source."""
    blob = json.dumps(manifest)
    assert "tensor://reports/5656" in blob
    for other in ("tensor://reports/448", "tensor://reports/542"):
        assert other not in blob


# ---------------- negative controls: the verifier must catch these ----------------
def _write_tampered(tmp_path, mutate):
    man = json.load(open(MANIFEST, encoding="utf-8"))
    mutate(man)
    p = tmp_path / "asset_manifest.json"
    p.write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
    kf = json.load(open(KF, encoding="utf-8"))
    kfp = tmp_path / "kf_result.json"
    kfp.write_text(json.dumps(kf), encoding="utf-8")
    return str(p), str(kfp)


def test_negative_tampered_quote_is_caught(tmp_path):
    def mut(m):
        m["assets"][2]["locator"]["quote"] = m["assets"][2]["locator"]["quote"].replace("27", "19", 1)
    mp, kp = _write_tampered(tmp_path, mut)
    res = V.verify(mp, SOURCE, kp)
    assert res["source_locator_resolvable"]["ok"] is False


def test_negative_duplicate_ids_is_caught(tmp_path):
    def mut(m):
        m["assets"][1]["asset_id"] = m["assets"][0]["asset_id"]
    mp, kp = _write_tampered(tmp_path, mut)
    res = V.verify(mp, SOURCE, kp)
    assert res["no_duplicate_ids"]["ok"] is False


def test_negative_wrong_hash_is_caught(tmp_path):
    def mut(m):
        m["source"]["hash"] = "0" * 64
    mp, kp = _write_tampered(tmp_path, mut)
    res = V.verify(mp, SOURCE, kp)
    assert res["source_hash_matches"]["ok"] is False
    assert res["schema_pass"]["ok"] is False  # const in schema also pins the hash


def test_negative_claim_marked_verified_is_caught(tmp_path):
    def mut(m):
        m["claims"] = [{"claim_id": "C1", "text": "x", "verified": True}]
    mp, kp = _write_tampered(tmp_path, mut)
    res = V.verify(mp, SOURCE, kp)
    assert res["all_claims_have_evidence_or_explicit_unresolved_status"]["ok"] is False


def test_negative_stale_outputs_hash_is_caught(tmp_path):
    mp, kp = _write_tampered(tmp_path, lambda m: m.update({"generated_at": "x"}))
    res = V.verify(mp, SOURCE, kp)
    assert res["outputs_sha256_matches_file"]["ok"] is False