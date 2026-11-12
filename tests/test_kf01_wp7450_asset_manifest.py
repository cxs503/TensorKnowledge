"""Independent re-check of docs/kf/wp-7450-01/asset_manifest.json against report 7450.

Deliberately does NOT import scripts/kf/kf01_register.py: it re-derives the hash and every
locator from the platform-returned markdown, so a bug in the builder cannot hide here.
Skips (does not pass) when the platform API is unreachable, and never touches another report_id.
"""
import hashlib
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "docs" / "kf" / "wp-7450-01" / "asset_manifest.json"
RESULT = REPO / "docs" / "kf" / "wp-7450-01" / "kf_result.json"
CONTRACT_HASH = "4b20aadcaabc128bc8fb10e8f9f164de670421c2b67d36d2837fc5781d96bfac"
CONTRACT_CHARS = 6312
REPORT_ID = "7450"


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _markdown():
    base = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
    user = os.environ.get("TENSOR_AGENT_USER")
    pwd = os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        pytest.skip("platform API credentials not present in this environment")
    try:
        d = _req(base + "/auth/login", data=json.dumps({"username": user, "password": pwd}).encode())
    except urllib.error.HTTPError:
        d = _req(base + "/auth/login",
                 data=urllib.parse.urlencode({"username": user, "password": pwd}).encode(),
                 ctype="application/x-www-form-urlencoded")
    except (urllib.error.URLError, OSError) as e:  # platform down -> unknown, not passed
        pytest.skip("platform API unreachable: %s" % e)
    tok = d.get("access_token") or d.get("token")
    rep = _req(base + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(rep, dict) and isinstance(rep.get("data"), dict):
        rep = rep["data"]
    return rep["markdown"]


@pytest.fixture(scope="module")
def md():
    return _markdown()


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_source_hash_matches_contract(md):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_manifest_and_envelope_agree(manifest, md):
    envelope = json.loads(RESULT.read_text(encoding="utf-8"))
    assert manifest["report_id"] == envelope["report_id"] == REPORT_ID
    assert envelope["provenance"]["source_hash"] == "sha256:" + hashlib.sha256(md.encode()).hexdigest()
    assert envelope["outputs"]["asset_manifest.json"]["sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert envelope["outputs"]["asset_manifest.json"]["asset_count"] == len(manifest["assets"])


def test_every_locator_resolves_verbatim(manifest, md):
    lines = md.split("\n")
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if not (0 <= s < e <= len(md)) or md[s:e] != q or q not in md:
            bad.append((a["asset_id"], "span/quote"))
            continue
        start_line = next(i for i in range(len(starts)) if starts[i] <= s and (i + 1 >= len(starts) or starts[i + 1] > s))
        if start_line + 1 != loc["start_line"]:
            bad.append((a["asset_id"], "start_line"))
        if "token" in loc:
            ts, te = loc["token_span"]
            if md[ts:te] != loc["token"] or not (s <= ts and te <= e):
                bad.append((a["asset_id"], "token_span"))
    assert bad == []


def test_ids_unique_and_claims_honest(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert manifest["claims"] == []
    assert all(c.get("status") != "verified" for c in manifest["claims"])


def test_registered_paths_are_not_claimed_present(manifest):
    """A referenced path either exists in this worktree or is explicitly unresolved."""
    for a in manifest["assets"]:
        if "path_reference" in a:
            exists = (REPO / a["path_reference"].lstrip("./")).is_file()
            if exists:
                assert a["resolution"] == "resolved_in_source", a["asset_id"]
            else:
                assert a["resolution"] == "referenced_unresolved", a["asset_id"]


def test_figures_without_payload_are_not_overclaimed(manifest, md):
    for a in manifest["assets"]:
        if a["asset_class"] == "embedded_figure":
            assert a["sha256"] is None and a["bytes"] is None
            assert a["resolution_detail"] == "metadata_only"
            assert a["label"] in md  # the name is registered only because it occurs verbatim
