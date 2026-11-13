"""Independent re-check of docs/kf/wp-13547-01/ against report 13547.

Deliberately does NOT import the builder: the hash, every locator and the envelope are
re-derived from the platform-returned markdown, so a bug in the generator cannot hide here.
Skips (does not pass) when the platform API is unreachable, and reads no other report_id.
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
OUT = REPO / "docs" / "kf" / "wp-13547-01"
CONTRACT_HASH = "2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42"
CONTRACT_CHARS = 6168
REPORT_ID = "13547"
PKG = "wp-13547-01"


def _login():
    base = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        pytest.skip("platform API credentials not present in this environment")
    body = json.dumps({"username": user, "password": pwd}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body, headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=30))
    return base, d.get("access_token") or d.get("token")


@pytest.fixture(scope="module")
def source():
    base, tok = _login()
    req = urllib.request.Request(base + "/tensor/reports/" + REPORT_ID,
                                 headers={"Authorization": "Bearer " + tok})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    return d["markdown"]


@pytest.fixture(scope="module")
def manifest():
    return json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


def test_source_hash_and_length_match_the_contract(source, manifest, envelope):
    digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert len(source) == CONTRACT_CHARS
    assert manifest["source"]["hash"] == digest
    assert envelope["provenance"]["source_hash"] == "sha256:" + digest


def test_every_locator_resolves_in_the_live_source(source, manifest):
    starts, off = [], 0
    for ln in source.split("\n"):
        starts.append(off)
        off += len(ln) + 1

    def line_of(c):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= c:
                lo = mid
            else:
                hi = mid - 1
        return lo

    problems = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if not (0 <= s < e <= len(source)) or source[s:e] != q or q not in source:
            problems.append([a["asset_id"], "span_quote"])
        elif line_of(s) + 1 != loc["start_line"] or line_of(e - 1) + 1 != loc["end_line"]:
            problems.append([a["asset_id"], "line_map"])
    assert problems == []


def test_no_duplicate_ids_and_no_verified_marks(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["claims"] == []
    assert not re.search(r'"status":\s*"verified"', json.dumps(manifest, ensure_ascii=False))


def test_resolution_vocabulary_is_closed(manifest):
    allowed = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
    for a in manifest["assets"]:
        assert a["resolution"] in allowed
        assert a["resolution_check"]["result"] in {"resolved", "unresolved", "absent", "present"}
        assert a["resolution_check"]["detail"]


def test_envelope_matches_schema_and_disk(manifest, envelope):
    jsonschema = pytest.importorskip("jsonschema")
    spec = json.loads((REPO / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(spec).validate(envelope)
    assert envelope["package_id"] == PKG and envelope["report_id"] == REPORT_ID
    assert envelope["outputs"]["asset_manifest.json"]["sha256"] == \
        hashlib.sha256((OUT / "asset_manifest.json").read_bytes()).hexdigest()


def test_rendered_report_carries_exactly_one_json_block_equal_to_the_envelope(envelope):
    text = (OUT / "report.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```json\n(.*?)\n```", text, re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == envelope
    assert text.startswith("# KF-RESULT %s" % PKG)


def test_registered_evidence_artifacts_are_reported_honestly(manifest):
    """The report's own evidence directory must not be claimed as resolved while HEAD lacks it."""
    by_label = {a.get("path_reference") or a["label"]: a for a in manifest["assets"]}
    ev = by_label["artifacts/audit/*.log"]
    if ev["resolution"] == "resolved_in_source":
        assert ev["resolution_check"]["detail"].startswith(str(len(ev["probe_evidence"]["matched_files"])))
    else:
        assert ev["resolution"] == "referenced_unresolved"
        assert "HEAD" in ev["resolution_check"]["detail"]
