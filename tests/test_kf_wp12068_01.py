"""KF wp-12068-01 (report 12068, DG Compressible Euler) asset registration — independent checks.

Two layers, deliberately separated:

* offline checks read only the delivered files and their internal consistency; they never
  import ``scripts/kf/kf01_register.py``, so a bug in the builder cannot certify itself;
* live checks re-derive the sha256 and every locator from the platform-returned markdown and
  **skip** (never pass) when the platform API is unreachable.

The package registers 9 assets of a 1086-char report that contains no file-path references and
whose 5 figures carry no payload: the honest outcome is 4 resolved table/markdown spans plus 5
``metadata_only`` figure records, and claims=[] (registration is not extraction).
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
PKG = REPO / "docs" / "kf" / "wp-12068-01"
MANIFEST = PKG / "asset_manifest.json"
RESULT = PKG / "kf_result.json"
VERIFY = PKG / "verification.json"
REPORT = PKG / "report.md"
PAYLOAD = PKG / "report_payload.json"
FIGURE = PKG / "figures" / "wp-12068-01_asset_locator_map.png"

CONTRACT_HASH = "de2f16253ed522c619246898f442983d5a66f3a2bec42c2fe271847a2020cbf0"
CONTRACT_CHARS = 1086
REPORT_ID = "12068"
PACKAGE_ID = "wp-12068-01"
MISSION_ID = 15738


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


# ------------------------------------------------------------------ offline: manifest
def test_manifest_source_contract(manifest):
    src = manifest["source"]
    assert manifest["package_id"] == PACKAGE_ID
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == REPORT_ID
    assert src["hash"] == CONTRACT_HASH
    assert src["chars"] == CONTRACT_CHARS
    assert src["uri"] == "tensor://reports/" + REPORT_ID
    assert src["bytes_utf8"] >= src["chars"]  # utf-8 is never shorter than the char count


def test_counts_are_recomputed_from_the_asset_list(manifest):
    assets = manifest["assets"]
    c = manifest["counts"]
    assert c["assets"] == len(assets) == 9
    by_class = {}
    by_res = {"resolved_in_source": 0, "referenced_unresolved": 0, "declared_absent": 0}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] += 1
    assert c["by_class"] == by_class
    for k, v in by_res.items():
        assert c[k] == v
    assert c["by_resolution"] == {k: v for k, v in by_res.items() if v}
    assert by_class == {"report_markdown": 1, "embedded_figure": 5, "report_table": 3}


def test_locator_geometry_is_inside_the_source(manifest):
    n = manifest["source"]["chars"]
    lines = [a for a in manifest["assets"]]
    for a in lines:
        loc = a["locator"]
        assert loc["method"] in ("char_span", "document"), a["asset_id"]
        assert 0 <= loc["start_char"] < loc["end_char"] <= n, a["asset_id"]
        assert 1 <= loc["start_line"] <= loc["end_line"], a["asset_id"]
        assert loc["quote"], a["asset_id"]
        assert len(loc["quote"]) == loc["end_char"] - loc["start_char"], a["asset_id"]
    # the report_markdown asset must span the whole document
    md_asset = [a for a in lines if a["asset_class"] == "report_markdown"][0]
    assert md_asset["locator"]["start_char"] == 0 and md_asset["locator"]["end_char"] == n


def test_figures_are_registered_as_metadata_only_not_overclaimed(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    names = [f["label"] for f in figs]
    assert names == ["sod_shock_tube", "lax_shock_tube", "isentropic_vortex",
                     "double_mach_reflection", "supersonic_cylinder"]
    assert names == manifest["source"]["platform_figures"]
    for f in figs:
        assert f["sha256"] is None and f["bytes"] is None    # no byte hash is invented
        assert f["resolution_detail"] == "metadata_only"
        assert f["resolution"] == "referenced_unresolved"
        assert f["resolution_check"]["result"] == "unresolved"
        assert f["figure_uri"] == "tensor://reports/12068#figures[%d]" % names.index(f["label"])


def test_tables_record_geometry_only(manifest):
    tabs = [a for a in manifest["assets"] if a["asset_class"] == "report_table"]
    assert len(tabs) == 3
    for t in tabs:
        assert t["resolution"] == "resolved_in_source"
        assert t["rows"] >= 2 and t["columns"] >= 2
        assert t["resolution_check"]["detail"] == "%d rows x %d columns" % (t["rows"], t["columns"])
        assert "rows x" in t["resolution_check"]["detail"]
        # content is not restated as knowledge
        assert "not extract" in t["note"]


def test_no_path_assets_because_the_source_has_no_paths(manifest):
    assert manifest["counts"]["distinct_referenced_paths"] == 0
    assert [a for a in manifest["assets"] if "path_reference" in a] == []


def test_ids_unique_and_claims_honest(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert len(ids) == len(set(ids))
    assert all(i.startswith("A") for i in ids)
    assert manifest["claims"] == []
    # nothing is marked verified: verification is the platform gate's verdict, not ours
    assert all(a.get("verified") is None and a.get("status") != "verified"
               for a in manifest["assets"])


# ------------------------------------------------------------------ offline: envelope / report
def test_envelope_hash_and_counts_match_delivered_files(envelope):
    assert envelope["package_id"] == PACKAGE_ID
    assert envelope["task_type"] == "01-asset-registration"
    assert envelope["report_id"] == REPORT_ID
    prov = envelope["provenance"]
    assert prov["source_hash"] == "sha256:" + CONTRACT_HASH
    assert prov["source_chars"] == CONTRACT_CHARS
    out = envelope["outputs"]["asset_manifest.json"]
    raw = MANIFEST.read_bytes()
    assert out["sha256"] == hashlib.sha256(raw).hexdigest()
    assert out["bytes"] == len(raw)
    assert out["path"] == "docs/kf/wp-12068-01/asset_manifest.json"
    assert out["claims"] == 0
    assert envelope["claims"] == []


def test_verification_all_pass_and_self_consistent():
    v = json.loads(VERIFY.read_text(encoding="utf-8"))
    assert v["all_pass"] is True
    assert v["checks"], "no acceptance checks recorded"
    assert all(c["pass"] for c in v["checks"].values())
    named = set(v["checks"])
    for required in ("schema_pass", "source_hash_matches", "source_locator_resolvable",
                     "no_duplicate_ids", "report_id_scoped", "manifest_hash_matches_envelope"):
        assert required in named, required
    assert "producing agent" in v["scope_note"]  # self-check is not the platform gate


def test_report_md_is_rendered_not_handwritten(envelope):
    text = REPORT.read_text(encoding="utf-8")
    assert text.count("```json") == 1
    assert text.count("![asset locator map](figures/wp-12068-01_asset_locator_map.png)") == 1
    # the embedded envelope is the delivered envelope, byte-for-byte
    body = text.split("```json", 1)[1].split("```", 1)[0].strip()
    assert json.loads(body) == envelope
    # the repro command names this package, not the template's default one
    assert "kf01_register.py --preset wp-12068-01 build result verify figure report" in text
    assert "wp-7450-01" not in text
    # single-report scope
    assert "report 7450" not in text
    assert "report_id=%s" % REPORT_ID in text


def test_report_numbers_are_injected_programmatically(manifest, envelope):
    text = REPORT.read_text(encoding="utf-8")
    assert "%d 项资产" % manifest["counts"]["assets"] in text
    assert "共 %d 项均无 `png_base64`" % manifest["counts"]["by_class"]["embedded_figure"] in text
    assert "%d 张表只登记几何" % manifest["counts"]["by_class"]["report_table"] in text
    assert hashlib.sha256(MANIFEST.read_bytes()).hexdigest() in text
    assert envelope["provenance"]["source_hash"].split(":", 1)[1] in text


def test_payload_scoped_to_mission_and_figure_bytes(payload):
    assert payload["scenario_key"] == "p315w1-n07-dg-compressible-euler"
    assert payload["mission_id"] == MISSION_ID
    assert "kf-wp:" + PACKAGE_ID in payload["tags"]
    assert "report_id:" + REPORT_ID in payload["tags"]
    assert payload["title"] == "KF-RESULT " + PACKAGE_ID
    figs = payload["figures"]
    assert len(figs) == 1
    png = __import__("base64").b64decode(figs[0]["png_base64"])
    assert png == FIGURE.read_bytes()          # the embedded figure is the delivered figure
    assert PACKAGE_ID in figs[0]["caption"]
    assert payload["markdown"] == REPORT.read_text(encoding="utf-8")


def test_locator_map_png_is_a_real_figure():
    raw = FIGURE.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert w >= 800 and h >= 400
    assert len(raw) > 20_000                   # a plot, not a placeholder pixel


# ------------------------------------------------------------------ offline: registrar regression
def _load_registrar(monkeypatch):
    """Import the registrar with dummy credentials: only the PRESETS table is inspected."""
    for k, v in (("TENSOR_API_BASE", "http://127.0.0.1:1/api/v1"),
                 ("TENSOR_AGENT_USER", "u"), ("TENSOR_AGENT_PASS", "p")):
        monkeypatch.setenv(k, v)
    path = REPO / "scripts" / "kf" / "kf01_register.py"
    spec = importlib.util.spec_from_file_location("kf01_register_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    try:
        spec.loader.exec_module(mod)
    finally:
        sys.modules.pop(spec.name, None)
    return mod


def test_new_preset_added(monkeypatch):
    presets = _load_registrar(monkeypatch).PRESETS
    cfg = presets[PACKAGE_ID]
    assert cfg["report_id"] == REPORT_ID
    assert cfg["expected_hash"] == CONTRACT_HASH
    assert cfg["expected_chars"] == CONTRACT_CHARS
    assert cfg["out_dir"] == "docs/kf/wp-12068-01"
    assert cfg["mission_id"] == MISSION_ID
    assert cfg["scenario_key"] == "p315w1-n07-dg-compressible-euler"
    # the package declares the two facts that make its报告 differ from the template default
    assert "无跨仓路径引用" in cfg["cross_repo_note"][0]
    assert "5 张图" in cfg["figure_note"]


def test_existing_presets_keep_their_contracts(monkeypatch):
    """The parameterisation must not drift the presets that were merged before it."""
    presets = _load_registrar(monkeypatch).PRESETS
    wp7450 = presets["wp-7450-01"]
    assert (wp7450["report_id"], wp7450["expected_chars"]) == ("7450", 6312)
    assert wp7450["out_dir"] == "docs/kf/wp-7450-01"
    wp14068 = presets["wp-14068-01"]
    assert (wp14068["report_id"], wp14068["expected_chars"]) == ("14068", 4557)
    assert wp14068["mission_id"] == 15780
    assert presets["wp-7450-01"]["expected_hash"] == (
        "4b20aadcaabc128bc8fb10e8f9f164de670421c2b67d36d2837fc5781d96bfac")


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


def test_live_tables_quote_contiguous_markdown(md, manifest):
    for a in manifest["assets"]:
        if a["asset_class"] != "report_table":
            continue
        block = a["locator"]["quote"]
        assert block in md
        rows = block.split("\n")
        assert len(rows) == a["rows"]
        assert all(r.strip().startswith("|") for r in rows)