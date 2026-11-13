"""Independent re-check of docs/wp-13946-01/asset_manifest.json against report 13946.

Two layers:
  * offline layer (always runs): the committed manifest mirrors artifacts/ byte-for-byte, parses,
    validates against schemas/asset_manifest.wp-13946-01.schema.json, has unique asset ids, carries
    the contract hash, and every locator re-resolves inside the fetched run copy of the markdown
    (runs/wp-13946-01/report_13946.md) -- so a drifted quote fails the test.
  * live layer (skips when the platform API is unreachable): re-fetch report 13946 from the API,
    recompute sha256(markdown) and re-resolve every locator against the *server* bytes.

Deliberately does NOT import scripts/kf_register_13946.py (a builder bug must not be able to hide),
and only ever touches report_id=13946.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOC_MANIFEST = REPO / "docs" / "wp-13946-01" / "asset_manifest.json"
ART_MANIFEST = REPO / "artifacts" / "wp-13946-01" / "asset_manifest.json"
DOC_RESULT = REPO / "docs" / "wp-13946-01" / "kf_result.json"
RUN_MD = REPO / "runs" / "wp-13946-01" / "report_13946.md"
SCHEMA = REPO / "schemas" / "asset_manifest.wp-13946-01.schema.json"
ENV_SCHEMA = REPO / "schemas" / "kf_result.v1.schema.json"

REPORT_ID = "13946"
PACKAGE_ID = "wp-13946-01"
CONTRACT_HASH = "eb37b6effecdfc9396ded7a80f236173e234f2785fd984a948efba4a9b671072"
CONTRACT_CHARS = 5534


def _load():
    assert DOC_MANIFEST.exists(), "committed manifest missing: %s" % DOC_MANIFEST
    return json.loads(DOC_MANIFEST.read_text())


def test_manifest_mirror_byte_identical():
    """artifacts/ is gitignored, so after a fresh checkout only the docs mirror exists."""
    if not ART_MANIFEST.exists():
        pytest.skip("artifacts/ not present (gitignored); docs mirror is the committed copy")
    assert DOC_MANIFEST.read_bytes() == ART_MANIFEST.read_bytes()


def test_schema_valid_and_identity():
    jsonschema = pytest.importorskip("jsonschema")
    man = _load()
    jsonschema.validate(man, json.loads(SCHEMA.read_text()))
    envelope = json.loads(DOC_RESULT.read_text())
    jsonschema.validate(envelope, json.loads(ENV_SCHEMA.read_text()))
    assert man["package_id"] == PACKAGE_ID and man["report_id"] == REPORT_ID
    assert envelope["package_id"] == PACKAGE_ID and envelope["report_id"] == REPORT_ID
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH


def test_hash_and_counts():
    man = _load()
    assert man["source"]["hash"] == CONTRACT_HASH
    assert man["source"]["chars"] == CONTRACT_CHARS
    assert man["counts"]["assets"] == len(man["assets"])
    ids = [a["asset_id"] for a in man["assets"]]
    assert len(ids) == len(set(ids))
    by_res = {}
    for a in man["assets"]:
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert by_res == man["counts"]["by_resolution"]


def test_claims_empty_or_evidenced():
    for c in _load()["claims"]:
        assert c.get("evidence") or c.get("evidence_locator") or c.get("status")


def _locators_resolve(md: str):
    man = _load()
    assert hashlib.sha256(md.encode()).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS
    for a in man["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        assert md[s:e] == q, a["asset_id"]
        assert md.count(q) == 1, a["asset_id"]
        assert loc["start_line"] == md.count("\n", 0, s), a["asset_id"]


def test_locators_resolve_offline():
    if not RUN_MD.exists():
        pytest.skip("run copy of report 13946 not present (runs/ is not committed)")
    _locators_resolve(RUN_MD.read_text())


def test_locators_resolve_against_platform():
    base = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        pytest.skip("platform API credentials not present in this environment")

    def req(url, payload=None, token=None):
        data = json.dumps(payload).encode() if payload is not None else None
        r = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        if data:
            r.add_header("Content-Type", "application/json")
        if token:
            r.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read().decode())

    try:
        tok = None
        for path in ("/auth/login", "/auth/token", "/login"):
            try:
                d = req(base + path, {"username": user, "password": pwd})
            except urllib.error.HTTPError:
                continue
            tok = d.get("access_token") or d.get("token")
            if tok:
                break
        assert tok, "login failed on all known endpoints"
        rep = req(base + "/tensor/reports/" + REPORT_ID, token=tok)
    except (urllib.error.URLError, OSError) as exc:  # platform down -> unknown, not passed
        pytest.skip("platform API unreachable: %s" % exc)
    if isinstance(rep, dict) and isinstance(rep.get("data"), dict):
        rep = rep["data"]
    _locators_resolve(rep["markdown"])