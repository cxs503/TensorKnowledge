"""Regression tests for work package wp-12445-01 (asset registration).

These assert invariants, not just "code ran":
  * the pinned markdown still hashes to the contract source_hash and the char count;
  * every asset/anchor locator resolves to its exact quote at its exact char span
    and that quote occurs exactly once in the document (so a locator can never
    silently drift to a different occurrence after an edit);
  * the manifest and the delivery envelope stay schema-valid and byte-consistent
    with each other (envelope.outputs == manifest);
  * no claim is emitted without evidence/status, and no claim is marked verified.

Run: pytest -q tests/test_kf_wp12445_01.py
"""
import hashlib
import json
import pathlib

import pytest

PKG = "wp-12445-01"
ROOT = pathlib.Path(__file__).resolve().parents[1]
KF = ROOT / "docs" / "kf" / PKG
MANIFEST = KF / "asset_manifest.json"
ENVELOPE = KF / "kf_result.json"
MD = ROOT / "runs" / PKG / "report_12445.md"
CONTRACT_HASH = "f86e8247d5dff43152a883b11207b09d96d5dd70892d7f62cab187746f85f23f"
CONTRACT_CHARS = 3554


@pytest.fixture(scope="module")
def md():
    return MD.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads(ENVELOPE.read_text(encoding="utf-8"))


def test_source_hash_and_length_pinned(md, manifest):
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS == manifest["source"]["chars"]


def test_envelope_provenance_hash_matches(md, envelope):
    digest = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert envelope["provenance"]["source_hash"] == "sha256:" + digest
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["package_id"] == PKG and envelope["report_id"] == "12445"


def test_envelope_embeds_manifest_verbatim(envelope, manifest):
    assert envelope["outputs"]["asset_manifest.json"] == manifest


@pytest.mark.parametrize("kind", ["assets", "anchors"])
def test_locators_resolve_exactly_once(md, manifest, kind):
    items = manifest[kind]
    assert items, "no %s to check" % kind
    for it in items:
        loc = it["locator"] if kind == "assets" else it
        quote, s, e = loc["quote"], loc["start_char"], loc["end_char"]
        assert md[s:e] == quote, "%s char span drifted" % it.get("asset_id", it.get("anchor_id"))
        assert md.count(quote) == 1, "%s quote not unique" % it.get("asset_id", it.get("anchor_id"))
        assert e - s == len(quote)


def test_asset_ids_unique_and_counts_consistent(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids)) == manifest["counts"]["assets"]
    assert sum(manifest["counts"]["by_class"].values()) == manifest["counts"]["assets"]
    assert sum(manifest["counts"]["by_resolution"].values()) == manifest["counts"]["assets"]


def test_every_asset_declares_a_resolution_check(manifest):
    for a in manifest["assets"]:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved", "declared_absent"}
        assert a["resolution_check"]["check"] and a["resolution_check"]["result"]
        assert a["note"].strip()


def test_claims_empty_or_evidenced_and_never_verified(manifest, envelope):
    claims = manifest["claims"]
    assert isinstance(claims, list)
    for c in claims:
        assert ("evidence_locator" in c) or ("status" in c)
        assert "verified" not in json.dumps(c, ensure_ascii=False).lower()
    # task_type 01 does no extraction -> contract-legitimate empty array
    assert claims == []
    assert "verified" not in json.dumps(envelope, ensure_ascii=False).lower()


def test_schemas_pass(manifest, envelope):
    from jsonschema import Draft202012Validator
    env_s = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    man_s = json.loads((KF / "asset_manifest.schema.json").read_text(encoding="utf-8"))
    assert not list(Draft202012Validator(env_s).iter_errors(envelope))
    assert not list(Draft202012Validator(man_s).iter_errors(manifest))


def test_no_cross_report_reference_in_scripts():
    """Boundary: this package must only touch report 12445.

    Any literal report id in a /tensor/reports/<id> URL must be 12445; ids coming
    from a variable (e.g. the published result-report id) are allowed.
    """
    import re

    scripts = sorted((ROOT / "scripts").glob("kf_wp12445_*.py"))
    assert len(scripts) >= 5, "expected the full fetch/register/verify/figure/report chain"
    offenders = []
    targeted = set()
    for p in scripts:
        for line in p.read_text(encoding="utf-8").splitlines():
            for m in re.finditer(r"reports/(\d+)", line):
                targeted.add(m.group(1))
                if m.group(1) != "12445":
                    offenders.append((p.name, line.strip()))
    assert not offenders, offenders
    assert "12445" in targeted, "no script pins report 12445 -> test would be vacuous"
