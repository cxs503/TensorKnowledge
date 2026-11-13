"""Acceptance + mutation tests for work package wp-9706-01 (report 9706 asset registration).

Two kinds of assertions, deliberately separated:

1. Positive: the acceptance gate (scripts/kf_verify_9706.py) exits 0 and each contract
   acceptance item is 'pass'.
2. Negative (mutation probes): the same predicates MUST fail on a tampered copy. A green
   suite that cannot go red proves nothing, so every acceptance item is probed with a
   realistic defect: broken quote, duplicated id, wrong source hash, claim without evidence
   marked verified, resolution status inconsistent with its own check.

Run: python -m pytest tests/test_kf_wp_9706_01.py -q
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = "wp-9706-01"
RUN_DIR = ROOT / "runs" / PKG
MAN_PATH = ROOT / "artifacts" / PKG / "asset_manifest.json"
EXPECTED_HASH = "7d0e024b8630cd3390f5efc0c3f5abfb467e85a869c78126bbb210a1a2d13534"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MAN_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def markdown():
    return (RUN_DIR / "report_9706.md").read_text(encoding="utf-8")


def _locators_resolve(md: str, man: dict) -> list:
    bad = []
    for a in man["assets"]:
        loc = a["locator"]
        if md.count(loc["quote"]) != 1:
            bad.append(a["asset_id"])
        elif loc["method"] == "char_span" and md[loc["start_char"]:loc["end_char"]] != loc["quote"]:
            bad.append(a["asset_id"])
    return bad


def _ids_unique(man: dict) -> bool:
    ids = [a["asset_id"] for a in man["assets"]]
    return len(ids) == len(set(ids))


def _hash_ok(md: str, man: dict) -> bool:
    return (hashlib.sha256(md.encode("utf-8")).hexdigest() == EXPECTED_HASH
            and man["source"]["hash"] == EXPECTED_HASH)


def _claims_ok(man: dict) -> bool:
    ok = True
    for c in man.get("claims", []):
        has_ev = bool(c.get("evidence")) or bool(c.get("evidence_locator"))
        has_status = c.get("status") in {"supported", "partially-supported", "unresolved", "refuted"}
        if not (has_ev or has_status) or c.get("verified") is True:
            ok = False
    return ok


# ---------------------------------------------------------------------------------------
# 1. positive: the real package passes its own gate
# ---------------------------------------------------------------------------------------
def test_verify_gate_passes():
    r = subprocess.run([sys.executable, "scripts/kf_verify_9706.py"], cwd=str(ROOT),
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, f"gate failed:\n{r.stdout}\n{r.stderr}"
    acc = json.loads((RUN_DIR / "acceptance.json").read_text(encoding="utf-8"))
    required = ["valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
                "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"]
    for item in required:
        assert acc["acceptance_items"][item] == "pass", item
    assert acc["all_pass"] is True


def test_manifest_identity(manifest):
    assert manifest["package_id"] == "wp-9706-01"
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == "9706"
    assert manifest["source"]["uri"] == "tensor://reports/9706"
    assert manifest["source"]["field"] == "markdown"


def test_all_locators_resolve(manifest, markdown):
    assert _locators_resolve(markdown, manifest) == []
    assert all(a["locator"]["unique"] for a in manifest["assets"])


def test_counts_match(manifest):
    by_res = {}
    for a in manifest["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert manifest["counts"]["assets"] == len(manifest["assets"])
    assert manifest["counts"]["by_resolution"] == by_res


def test_claims_empty_by_contract(manifest):
    assert manifest["claims"] == []  # registration only, no forced claim generation
    assert "classify_report_type=false" in manifest["claims_note"]


def test_not_self_marked_verified(manifest):
    r = json.loads((RUN_DIR / f"kf_result.{PKG}.json").read_text(encoding="utf-8"))
    assert r["provenance"]["verification_status"] == "not_verified"
    assert manifest["integrity"]["verification_status"] == "not_verified"


def test_durable_mirror_is_identical():
    a = (ROOT / "artifacts" / PKG / "asset_manifest.json").read_bytes()
    b = (ROOT / "docs" / PKG / "asset_manifest.json").read_bytes()
    assert a == b


# ---------------------------------------------------------------------------------------
# 2. negative: mutation probes -- each defect must be caught
# ---------------------------------------------------------------------------------------
def test_mutation_broken_quote_is_caught(manifest, markdown):
    mut = copy.deepcopy(manifest)
    mut["assets"][5]["locator"]["quote"] = mut["assets"][5]["locator"]["quote"] + "（手抄加字）"
    assert _locators_resolve(markdown, mut) == [mut["assets"][5]["asset_id"]]


def test_mutation_wrong_offsets_is_caught(manifest, markdown):
    mut = copy.deepcopy(manifest)
    mut["assets"][10]["locator"]["start_char"] += 1
    assert _locators_resolve(markdown, mut) == [mut["assets"][10]["asset_id"]]


def test_mutation_duplicate_asset_id_is_caught(manifest):
    mut = copy.deepcopy(manifest)
    mut["assets"][1]["asset_id"] = mut["assets"][0]["asset_id"]
    assert _ids_unique(mut) is False


def test_mutation_wrong_hash_is_caught(manifest, markdown):
    mut = copy.deepcopy(manifest)
    mut["source"]["hash"] = "0" * 64
    assert _hash_ok(markdown, mut) is False
    mut2 = copy.deepcopy(manifest)
    mut2["source"]["hash"] = hashlib.sha256((markdown + " ").encode("utf-8")).hexdigest()
    assert _hash_ok(markdown + " ", mut2) is False


def test_mutation_unsupported_claim_is_caught(manifest):
    mut = copy.deepcopy(manifest)
    mut["claims"] = [{"claim_id": "C01", "text": "无证据的推断", "verified": True}]
    assert _claims_ok(mut) is False
    mut["claims"] = [{"claim_id": "C01", "text": "有证据", "evidence_locator": {"start_char": 0}}]
    assert _claims_ok(mut) is True


def test_mutation_resolution_status_mismatch_is_caught(manifest):
    allowed = {"resolved_in_source": {"resolved", "present"},
               "referenced_unresolved": {"unresolved"},
               "declared_absent": {"absent"}}
    mut = copy.deepcopy(manifest)
    for a in mut["assets"]:
        if a["resolution"] == "referenced_unresolved":
            a["resolution_check"]["result"] = "resolved"  # lies about resolvability
            break
    mism = [a["asset_id"] for a in mut["assets"]
            if a["resolution_check"]["result"] not in allowed[a["resolution"]]]
    assert len(mism) == 1


def test_source_hash_gate_uses_contract_value():
    md = (RUN_DIR / "report_9706.md").read_bytes()
    assert hashlib.sha256(md).hexdigest() == EXPECTED_HASH
    assert len(md.decode("utf-8")) == 12546

# ---------------------------------------------------------------------------------------
# 3. submission channel: the platform gate reads the result out of the report markdown with a
#    non-greedy ```json fence regex (ops/knowledge_factory/gates.py::extract_payload), so the
#    report body must be gated here locally instead of assumed to be well-formed.
# ---------------------------------------------------------------------------------------
def test_report_has_exactly_one_decodable_json_block(manifest):
    import re
    rep = (ROOT / "docs" / "wp-9706-01" / "KF-RESULT-wp-9706-01.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\s*\n(.*?)```", rep, re.S)
    assert len(blocks) == 1, f"expected 1 json block, got {len(blocks)}"
    decoded = json.loads(blocks[0])
    assert decoded == json.loads((RUN_DIR / f"kf_result.{PKG}.json").read_text(encoding="utf-8"))
    assert "`" not in blocks[0], "backticks must be \\u0060-escaped or the non-greedy fence truncates"


def test_report_body_sections():
    rep = (ROOT / "docs" / "wp-9706-01" / "KF-RESULT-wp-9706-01.md").read_text(encoding="utf-8")
    assert rep.splitlines()[0].strip() == "# KF-RESULT wp-9706-01"
    for sec in ("## ①", "## ②", "## ③", "## ④", "## ⑤", "## ⑥"):
        assert sec in rep, sec
    assert "repro_cmd" in rep or "kf_run_9706.sh" in rep


def test_acceptance_includes_gate_style_item():
    acc = json.loads((RUN_DIR / "acceptance.json").read_text(encoding="utf-8"))
    assert acc["all_pass"] is True
    assert acc["acceptance_items"]["gate_style_extract_decodes_and_equals_envelope"] == "pass"
