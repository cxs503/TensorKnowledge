"""KF wp-12724-01 (report 12724, IL70-N08 ice-route optimisation) asset registration.

Same two-layer split as the sibling packages, deliberately kept:

* offline checks read only the delivered files and their internal consistency; they never import
  ``scripts/kf/kf01_register.py`` for the asset facts, so a bug in the builder cannot certify
  itself (the registrar is imported only to pin the *preset contract*);
* live checks re-derive the sha256, every locator and every table block from the markdown the
  platform returns and **skip** (never pass) when the platform API is unreachable.

The package registers 28 assets of a 7373-char report: 1 whole-document markdown record,
4 metadata-only figures (``record.figures[]`` has no ``png_base64``), 9 source-code plus
3 data-artifact path references that all live in the producing repo (hence
``referenced_unresolved`` by design), 10 pipe tables (geometry only) and 1 API endpoint token.
``claims`` is empty: registration is not extraction.
"""
import hashlib
import importlib.util
import json
import os
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-12724-01"
MANIFEST = PKG / "asset_manifest.json"
RESULT = PKG / "kf_result.json"
VERIFY = PKG / "verification.json"
REPORT = PKG / "report.md"
PAYLOAD = PKG / "report_payload.json"
FIGURE = PKG / "figures" / "wp-12724-01_asset_locator_map.png"

PACKAGE_ID = "wp-12724-01"
REPORT_ID = "12724"
MISSION_ID = 20442
CONTRACT_HASH = "c8c552fa8e470d9b7180aada951c667ad6c6c76ac3ade5a7b123d687a6339f5e"
CONTRACT_CHARS = 7373
SCENARIO_KEY = "ice_route_optimization"

BY_CLASS = {
    "report_markdown": 1,
    "embedded_figure": 4,
    "source_code_reference": 9,
    "data_artifact_reference": 3,
    "report_table": 10,
    "api_endpoint": 1,
}
# ``by_resolution`` only lists classes that actually occur (no zero-filled declared_absent key);
# the flat counters next to it carry the full triple.
BY_RESOLUTION = {"resolved_in_source": 12, "referenced_unresolved": 16}
FIGURE_NAMES = {
    "fig1_uniform_field.png",
    "fig2_ridge_detour.png",
    "fig3_speed_profile.png",
    "fig4_cost_comparison.png",
}


# ------------------------------------------------------------------ fixtures (offline)
@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads(RESULT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def payload():
    return json.loads(PAYLOAD.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ offline: manifest contract
def test_manifest_source_contract(manifest):
    assert manifest["package_id"] == PACKAGE_ID
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == REPORT_ID
    assert manifest["contract_version"] == "1.0"
    src = manifest["source"]
    assert src["uri"] == "tensor://reports/" + REPORT_ID
    assert src["field"] == "markdown"
    assert src["hash"] == CONTRACT_HASH          # the contract hash, not a re-typed copy
    assert src["chars"] == CONTRACT_CHARS
    assert manifest["claims"] == []


def test_manifest_counts_are_the_inventory(manifest):
    counts = manifest["counts"]
    assert counts["assets"] == len(manifest["assets"]) == 28
    assert counts["by_class"] == BY_CLASS
    assert counts["by_resolution"] == BY_RESOLUTION
    assert (counts["resolved_in_source"], counts["referenced_unresolved"],
            counts["declared_absent"]) == (12, 16, 0)
    assert counts["distinct_referenced_paths"] == 8
    assert len({a["asset_id"] for a in manifest["assets"]}) == 28


def test_every_asset_has_a_computed_locator(manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["method"] in {"document", "char_span", "line_span"}
        assert 0 <= loc["start_char"] < loc["end_char"] <= CONTRACT_CHARS
        assert 1 <= loc["start_line"] <= loc["end_line"]
        assert isinstance(loc["quote"], str) and loc["quote"]
        assert a["resolution"] in BY_RESOLUTION


def test_no_verified_marks_anywhere(manifest):
    """Registration never certifies itself: the gate, not the producer, says verified."""
    raw = MANIFEST.read_text(encoding="utf-8")
    assert '"status": "verified"' not in raw
    # the word may only appear in the *negative* limitation ("no `verified` marks") ...
    assert raw.count("`verified`") == 1
    assert "no `verified` marks" in raw
    # ... never as an asset status or a resolution value
    assert all(a["resolution"] != "verified" for a in manifest["assets"])
    assert all(a["resolution_check"]["result"] != "verified" for a in manifest["assets"])


def test_figures_are_metadata_only(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    assert {f["label"] for f in figs} == FIGURE_NAMES
    for f in figs:
        assert f["resolution"] == "referenced_unresolved"
        assert f["resolution_check"]["result"] == "unresolved"
        # no fabricated bytes: the key only appears inside the explanation of *why* it is empty
        assert "png_base64" not in f
        assert "png_base64 is empty" in f["resolution_check"]["detail"]
        assert f["resolution_check"]["detail"]
    # the 4 figures are also the only names the report claims to have published
    assert sum(1 for a in manifest["assets"] if a["asset_class"] == "embedded_figure") == 4


def test_cross_repo_paths_stay_unresolved_by_design(manifest):
    paths = [a for a in manifest["assets"]
             if a["asset_class"] in ("source_code_reference", "data_artifact_reference")]
    assert len(paths) == 12
    for a in paths:
        assert a["resolution"] == "referenced_unresolved"
        assert a["resolution_check"]["result"] == "unresolved"
        assert a["path_reference"] not in (None, "")
        # the reason is recorded, not guessed
        assert "not in" in a["resolution_check"]["detail"].lower() or \
               "跨仓" in a["resolution_check"]["detail"] or \
               "producing" in a["resolution_check"]["detail"].lower()


def test_tables_register_geometry_only(manifest):
    tables = [a for a in manifest["assets"] if a["asset_class"] == "report_table"]
    assert len(tables) == 10
    for t in tables:
        assert t["resolution"] == "resolved_in_source"
        assert t["rows"] >= 2 and t["columns"] >= 2
        rows = t["locator"]["quote"].split("\n")
        assert len(rows) == t["rows"]
        assert all(r.strip().startswith("|") for r in rows)
        assert all(r.count("|") >= t["columns"] for r in rows)
        # contents are not re-transcribed into the manifest
        assert t["note"].startswith("registered as an in-report data artifact")


def test_api_endpoint_token_is_registered(manifest):
    eps = [a for a in manifest["assets"] if a["asset_class"] == "api_endpoint"]
    assert len(eps) == 1
    ep = eps[0]
    assert ep["label"] == "/ice-navigation/route"
    assert ep["resolution"] == "resolved_in_source"
    assert ep["locator"]["quote"] == "/ice-navigation/route"
    assert ep["locator"]["start_char"] < ep["locator"]["end_char"]


# ------------------------------------------------------------------ offline: envelope / verify / report
def test_envelope_pins_the_delivered_manifest(envelope):
    assert envelope["package_id"] == PACKAGE_ID
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == REPORT_ID
    prov = envelope["provenance"]
    assert prov["source_hash"] == "sha256:" + CONTRACT_HASH
    assert prov["source_chars"] == CONTRACT_CHARS
    assert prov["fetched_via"] == "GET /api/v1/tensor/reports/" + REPORT_ID
    out = envelope["outputs"]["asset_manifest.json"]
    assert out["path"] == "docs/kf/wp-12724-01/asset_manifest.json"
    assert out["sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert out["bytes"] == len(MANIFEST.read_bytes())
    assert out["asset_count"] == 28
    assert envelope["claims"] == []


def test_verification_reports_every_acceptance_item():
    v = json.loads(VERIFY.read_text(encoding="utf-8"))
    assert v["package_id"] == PACKAGE_ID and v["report_id"] == REPORT_ID
    assert v["all_pass"] is True
    assert len(v["checks"]) == 9
    for name, c in v["checks"].items():
        assert c["pass"] is True, name
        assert c["detail"]
    assert v["manifest_sha256"] == hashlib.sha256(MANIFEST.read_bytes()).hexdigest()
    assert "authoritative verification is the platform gate" in v["scope_note"]


def test_report_is_rendered_not_transcribed(envelope):
    text = REPORT.read_text(encoding="utf-8")
    assert text.count("```json") == 1                       # single envelope block
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() in text
    assert envelope["provenance"]["source_hash"].split(":", 1)[1] in text
    assert CONTRACT_HASH in text                             # contract hash quoted verbatim
    # regression guard: the closed original PR left the renderer's default preset in place here
    assert "--preset wp-12724-01" in text
    assert "wp-7450-01" not in text
    # the package-specific prose (not the shared default) must reach the report
    assert "backend/api/ice/route_optimization.py" in text
    assert "共 4 项均无 `png_base64`" in text
    assert "10 张表只登记几何" in text


def test_payload_scoped_to_mission_and_figure_bytes(payload):
    assert payload["scenario_key"] == SCENARIO_KEY
    assert payload["mission_id"] == MISSION_ID
    assert payload["title"] == "KF-RESULT " + PACKAGE_ID
    assert "kf-wp:" + PACKAGE_ID in payload["tags"]
    assert "report_id:" + REPORT_ID in payload["tags"]
    figs = payload["figures"]
    assert len(figs) == 1
    import base64
    png = base64.b64decode(figs[0]["png_base64"])
    assert png == FIGURE.read_bytes()          # the embedded figure is the delivered figure
    assert PACKAGE_ID in figs[0]["caption"]
    assert payload["markdown"] == REPORT.read_text(encoding="utf-8")


def test_locator_map_png_is_a_real_figure():
    raw = FIGURE.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert w >= 800 and h >= 400
    assert len(raw) > 20_000                   # a plot, not a placeholder pixel


# ------------------------------------------------------------------ offline: registrar preset
def _load_registrar(monkeypatch):
    """Import the registrar with dummy credentials: only the PRESETS table is inspected."""
    for k, v in (("TENSOR_API_BASE", "http://127.0.0.1:1/api/v1"),
                 ("TENSOR_AGENT_USER", "u"), ("TENSOR_AGENT_PASS", "p")):
        monkeypatch.setenv(k, v)
    path = REPO / "scripts" / "kf" / "kf01_register.py"
    spec = importlib.util.spec_from_file_location("kf01_register_wp12724", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


def test_preset_registered(monkeypatch):
    cfg = _load_registrar(monkeypatch).PRESETS[PACKAGE_ID]
    assert cfg["report_id"] == REPORT_ID
    assert cfg["expected_hash"] == CONTRACT_HASH
    assert cfg["expected_chars"] == CONTRACT_CHARS
    assert cfg["out_dir"] == "docs/kf/wp-12724-01"
    assert cfg["mission_id"] == MISSION_ID
    assert cfg["scenario_key"] == SCENARIO_KEY
    assert cfg["declared_tokens"]["api_endpoint"] == ["/ice-navigation/route"]
    # the package declares why its prose differs from the template default
    assert cfg["producing_repo"] == "ship-performance-platform"
    assert "backend/api/ice/route_optimization.py" in "".join(cfg["cross_repo_note"])


def test_existing_presets_keep_their_contracts(monkeypatch):
    """Adding a preset must not drift the presets merged before it."""
    presets = _load_registrar(monkeypatch).PRESETS
    wp7450 = presets["wp-7450-01"]
    assert (wp7450["report_id"], wp7450["expected_chars"]) == ("7450", 6312)
    assert wp7450["expected_hash"] == (
        "4b20aadcaabc128bc8fb10e8f9f164de670421c2b67d36d2837fc5781d96bfac")
    wp14068 = presets["wp-14068-01"]
    assert (wp14068["report_id"], wp14068["expected_chars"], wp14068["mission_id"]) == ("14068", 4557, 15780)
    wp12068 = presets["wp-12068-01"]
    assert (wp12068["report_id"], wp12068["expected_chars"]) == ("12068", 1086)


# ------------------------------------------------------------------ live (skips without API)
def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _live_markdown():
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
    except (urllib.error.URLError, OSError) as e:   # platform down -> unknown, not passed
        pytest.skip("platform API unreachable: %s" % e)
    tok = d.get("access_token") or d.get("token")
    rep = _req(base + "/tensor/reports/" + REPORT_ID, tok)
    if isinstance(rep, dict) and isinstance(rep.get("data"), dict):
        rep = rep["data"]
    return rep["markdown"]


@pytest.fixture(scope="module")
def md():
    return _live_markdown()


def test_live_source_hash_matches_contract(md):
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_every_locator_resolves_verbatim_live(manifest, md):
    lines = md.split("\n")
    starts, off = [], 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if md[s:e] != q or q not in md:
            bad.append((a["asset_id"], "span/quote"))
            continue
        start_line = max(i for i in range(len(starts)) if starts[i] <= s)
        if start_line + 1 != loc["start_line"]:
            bad.append((a["asset_id"], "start_line"))
        end_line = max(i for i in range(len(starts)) if starts[i] <= e - 1)
        if end_line + 1 != loc["end_line"]:
            bad.append((a["asset_id"], "end_line"))
    assert bad == []


def test_live_tables_quote_contiguous_markdown(manifest, md):
    for a in manifest["assets"]:
        if a["asset_class"] != "report_table":
            continue
        block = a["locator"]["quote"]
        assert block in md
        rows = block.split("\n")
        assert len(rows) == a["rows"]
        assert all(r.strip().startswith("|") for r in rows)


def test_live_figure_names_are_really_listed(md, manifest):
    """The 4 figure assets must be the report's own names, not invented ones."""
    for name in FIGURE_NAMES:
        assert name in md
    listed = {a["label"] for a in manifest["assets"] if a["asset_class"] == "embedded_figure"}
    assert listed == FIGURE_NAMES