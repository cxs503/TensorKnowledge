"""wp-12072-01 (01-asset-registration, report 12072) acceptance tests.

Offline by default: every check runs against the artifacts committed under
``docs/kf/wp-12072-01/`` (including the byte-exact ``source.md`` snapshot), so the
acceptance gate can be re-run without platform credentials.  The live re-fetch
``python3 scripts/kf/kf01_register.py --preset wp-12072-01 build result verify figure report``
re-proves that those artifacts came from the live record; the last test below repeats the
hash check against the API when credentials are exported.

Scope: report_id=12072 only.  Nothing here reads or writes another report.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

import jsonschema
import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-12072-01"
ENVELOPE_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"
MANIFEST_SCHEMA = REPO / "schemas" / "asset_manifest.v1.schema.json"

CONTRACT_HASH = "sha256:493094b22bb67cac20e077c7990b46863cad81b1f523dea49ddbba8667ae2200"
CONTRACT_CHARS = 11171
PACKAGE_ID = "wp-12072-01"
REPORT_ID = "12072"
SCENARIO_KEY = "p161w2-arb-n02-eedi-optimization"


# ------------------------------------------------------------------ fixtures
def _load(name: str) -> dict:
    return json.loads((PKG / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def source() -> str:
    return (PKG / "source.md").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def manifest() -> dict:
    return _load("asset_manifest.json")


@pytest.fixture(scope="module")
def envelope() -> dict:
    return _load("kf_result.json")


@pytest.fixture(scope="module")
def verification() -> dict:
    return _load("verification.json")


@pytest.fixture(scope="module")
def report_body() -> str:
    return (PKG / "report.md").read_text(encoding="utf-8")


# ------------------------------------------------------- source identity (hash gate)
def test_source_snapshot_hash_matches_contract(source: str) -> None:
    digest = "sha256:" + hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert (PKG / "sha256.txt").read_text(encoding="utf-8").strip() == CONTRACT_HASH


def test_source_char_count_matches_contract(source: str) -> None:
    assert len(source) == CONTRACT_CHARS


def test_manifest_and_envelope_carry_same_identity(manifest: dict, envelope: dict) -> None:
    assert manifest["package_id"] == envelope["package_id"] == PACKAGE_ID
    assert manifest["task_type"] == envelope["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == envelope["report_id"] == REPORT_ID
    # asset_manifest.v1 pins source.hash to bare lowercase hex; the envelope carries "sha256:<hex>"
    assert manifest["source"]["hash"] == CONTRACT_HASH.split(":", 1)[1]
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    assert envelope["provenance"]["source_field"] == "markdown"
    assert envelope["provenance"]["source_uri"] == "tensor://reports/%s" % REPORT_ID
    assert manifest["source"]["scenario_key"] == SCENARIO_KEY


# ------------------------------------------------------------------ schema
def _relaxed_manifest_schema() -> dict:
    """schemas/asset_manifest.v1.schema.json pins four fields to the wp-448-01 package.

    Those package-level constants are relaxed to this package's values (everything else is
    kept), so a pass here means the shape is valid rather than "the check was skipped".
    """
    schema = json.loads(MANIFEST_SCHEMA.read_text(encoding="utf-8"))
    schema["properties"]["package_id"]["const"] = PACKAGE_ID
    schema["properties"]["report_id"]["const"] = REPORT_ID
    schema["properties"]["source"]["properties"]["uri"]["const"] = "tensor://reports/%s" % REPORT_ID
    return schema


def test_manifest_schema_pass(manifest: dict) -> None:
    jsonschema.Draft202012Validator.check_schema(_relaxed_manifest_schema())
    jsonschema.validate(manifest, _relaxed_manifest_schema())


def test_envelope_schema_pass(envelope: dict) -> None:
    schema = json.loads(ENVELOPE_SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.validate(envelope, schema)
    assert set(envelope["outputs"]) >= {"asset_manifest.json"}


# ------------------------------------------------------------------ locators
def test_every_locator_resolves_to_its_quote(manifest: dict, source: str) -> None:
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if not (0 <= s < e <= len(source)) or source[s:e] != q or q not in source:
            bad.append((a["asset_id"], "span_or_quote"))
        elif loc["method"] == "char_span" and not (
            "context_line" in loc or loc["start_line"] == loc["end_line"]
        ):
            # multi-line spans must still be internally consistent
            if source[s:e].count("\n") + 1 != loc["end_line"] - loc["start_line"] + 1:
                bad.append((a["asset_id"], "line_span"))
    assert bad == []


def test_line_numbers_match_char_offsets(manifest: dict, source: str) -> None:
    def line_of(char: int) -> int:
        return source.count("\n", 0, char) + 1

    for a in manifest["assets"]:
        loc = a["locator"]
        assert line_of(loc["start_char"]) == loc["start_line"], a["asset_id"]
        assert line_of(loc["end_char"] - 1) == loc["end_line"], a["asset_id"]


def test_locator_token_spans_stay_inside_their_line(manifest: dict, source: str) -> None:
    seen = 0
    for a in manifest["assets"]:
        loc = a["locator"]
        if "token" not in loc:
            continue
        seen += 1
        ts, te = loc["token_span"]
        assert source[ts:te] == loc["token"]
        assert loc["start_char"] <= ts and te <= loc["end_char"]
    assert seen >= 1


def test_asset_ids_unique_and_well_formed(manifest: dict) -> None:
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(re.fullmatch(r"A[0-9]{2}", i) for i in ids)
    assert manifest["counts"]["assets"] == len(ids) == len(manifest["assets"])


def test_counts_are_self_consistent(manifest: dict) -> None:
    assets = manifest["assets"]
    by_class: dict[str, int] = {}
    by_res: dict[str, int] = {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert manifest["counts"]["by_class"] == by_class
    assert manifest["counts"]["by_resolution"] == by_res
    assert manifest["counts"]["assets"] == len(assets)


# ------------------------------------------------------------------ claims / honesty
def test_claims_empty_or_evidenced(manifest: dict) -> None:
    claims = manifest["claims"]
    assert claims == []  # contract: registration only, no extraction, claims may be empty
    for c in claims:  # pragma: no cover - guard for future edits
        assert c.get("evidence") or c.get("status") == "unresolved"


def test_no_claim_is_marked_verified(manifest: dict, envelope: dict) -> None:
    """No claim, asset or provenance entry may carry a `verified` status: verification is the
    platform gate's output, not the producer's. (Prose limitations that *mention* verification
    are fine; status fields are what this asserts on.)"""
    for doc in (manifest, envelope):
        for c in doc.get("claims", []):
            assert c.get("status") not in {"verified", "VERIFIED"}
    for a in manifest["assets"]:
        assert a["resolution"] in {"resolved_in_source", "referenced_unresolved", "declared_absent"}
        for value in a.values():
            assert value != "verified"


def test_unresolved_assets_state_a_reason(manifest: dict) -> None:
    for a in manifest["assets"]:
        if a["resolution"] != "resolved_in_source":
            assert a["resolution_check"]["result"] in {"unresolved", "absent"}
            assert a["resolution_check"]["detail"].strip()
            assert a["note"].strip()


# ------------------------------------------------------------------ deliverable envelope
def test_manifest_hash_in_envelope_matches_file(envelope: dict) -> None:
    out = envelope["outputs"]["asset_manifest.json"]
    raw = (REPO / out["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == out["sha256"]
    assert len(raw) == out["bytes"]


def test_verification_all_pass(verification: dict) -> None:
    assert verification["all_pass"] is True, verification["checks"]
    assert set(verification["checks"]) >= {
        "valid_json",
        "schema_pass",
        "source_locator_resolvable",
        "source_hash_matches",
        "no_duplicate_ids",
        "all_claims_have_evidence_or_explicit_unresolved_status",
    }


def test_report_body_has_exactly_one_json_block_with_the_envelope(report_body: str) -> None:
    assert report_body.count("```json") == 1
    block = report_body.split("```json", 1)[1].split("```", 1)[0]
    embedded = json.loads(block)
    assert embedded == _load("kf_result.json")
    assert report_body.startswith("# KF-RESULT %s" % PACKAGE_ID)
    assert "kf-wp:%s" % PACKAGE_ID in _load("report_payload.json")["tags"]
    assert _load("report_payload.json")["title"] == "KF-RESULT %s" % PACKAGE_ID


# ------------------------------------------------------------------ live re-check (optional)
@pytest.mark.skipif(
    not (os.environ.get("TENSOR_API_BASE") and os.environ.get("TENSOR_AGENT_USER")
         and os.environ.get("TENSOR_AGENT_PASS")),
    reason="platform credentials not exported; offline snapshot check already ran",
)
def test_live_source_hash_still_matches() -> None:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    login = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({
            "username": os.environ["TENSOR_AGENT_USER"],
            "password": os.environ["TENSOR_AGENT_PASS"],
        }).encode(),
        headers={"Content-Type": "application/json"},
    )
    token = json.load(urllib.request.urlopen(login, timeout=30))["access_token"]
    req = urllib.request.Request(
        base + "/tensor/reports/%s" % REPORT_ID, headers={"Authorization": "Bearer " + token}
    )
    rec = json.load(urllib.request.urlopen(req, timeout=30))
    md = rec["markdown"]
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS