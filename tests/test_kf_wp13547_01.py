"""KF wp-13547-01 (report 13547, TensorKnowledge A+B quality audit) asset registration.

Layout kept identical to the sibling packages on purpose:

* offline checks read only the delivered files and their internal consistency. They never import the
  registrar for asset facts (a bug in the builder must not be able to certify itself); the registrar
  is imported only to pin the *preset contract*, and ``git`` is re-run to confirm the probe evidence;
* live checks re-derive the sha256, every locator and every line map from the markdown the platform
  returns, and **skip** (never pass) when the platform API is unreachable.

The package registers 22 assets of a 6168-char report: 1 whole-document markdown record, 3
metadata-only figures (``record.figures[]`` carries no ``png_base64``), 11 path references (2 of
which resolve inside this very worktree because the audited repository *is* TensorKnowledge),
5 pipe tables (geometry only) and 2 declared interface tokens. ``claims`` is empty: registration is
not extraction. ``evidence_git_probe.json`` adds identification evidence for the two commits and one
commit range the report names; ``published.json`` records staging (awaiting the pr-gate), not a
publication receipt.
"""
import hashlib
import importlib.util
import json
import os
import struct
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-13547-01"
MANIFEST = PKG / "asset_manifest.json"
RESULT = PKG / "kf_result.json"
VERIFY = PKG / "verification.json"
REPORT = PKG / "report.md"
PAYLOAD = PKG / "report_payload.json"
PROBE = PKG / "evidence_git_probe.json"
LEDGER = PKG / "published.json"
README = PKG / "README.md"
FIGURE = PKG / "figures" / "wp-13547-01_asset_locator_map.png"

PACKAGE_ID = "wp-13547-01"
REPORT_ID = "13547"
MISSION_ID = 20589
CONTRACT_HASH = "2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42"
CONTRACT_CHARS = 6168
SCENARIO_KEY = "quality-audit"

BY_CLASS = {
    "report_markdown": 1,
    "embedded_figure": 3,
    "document_reference": 2,
    "source_code_reference": 9,
    "report_table": 5,
    "db_table": 1,
    "schema_field": 1,
}
BY_RESOLUTION = {"resolved_in_source": 12, "referenced_unresolved": 10}
FIGURE_NAMES = {"fig1_maturity_levels.png", "fig2_suite_health.png", "fig3_kruger_benchmark.png"}
# the two commits the audited report pins as its baseline / merge point
PROBE_REFS = {"edbc20a", "2d3c446"}
RESOLVED_PATHS = {"audit_report.md", "docs/sediment-m2591-report.md",
                  "tests/test_sediment_m7437.py", "tests/test_ke_export.py"}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------ fixtures
@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope():
    return json.loads(RESULT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def payload():
    return json.loads(PAYLOAD.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def probe():
    return json.loads(PROBE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger():
    return json.loads(LEDGER.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def verdict():
    return json.loads(VERIFY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def registrar():
    """Import the tool only to pin the preset contract, never for asset facts."""
    spec = importlib.util.spec_from_file_location("kf01_register", REPO / "scripts" / "kf" / "kf01_register.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ offline: manifest contract
def test_manifest_source_contract(manifest):
    assert manifest["package_id"] == PACKAGE_ID
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == REPORT_ID
    assert manifest["contract_version"] == "1.0"
    assert manifest["source"]["uri"] == "tensor://reports/" + REPORT_ID
    assert manifest["source"]["field"] == "markdown"
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert manifest["source"]["bytes_utf8"] == 8782
    assert manifest["source"]["scenario_key"] == SCENARIO_KEY
    assert manifest["claims"] == []


def test_manifest_counts_are_the_inventory(manifest):
    counts = manifest["counts"]
    assert counts["assets"] == len(manifest["assets"]) == 22
    assert counts["by_class"] == BY_CLASS
    assert counts["by_resolution"] == BY_RESOLUTION
    assert (counts["resolved_in_source"], counts["referenced_unresolved"],
            counts["declared_absent"]) == (12, 10, 0)
    assert counts["distinct_referenced_paths"] == 10
    assert len({a["asset_id"] for a in manifest["assets"]}) == 22


def test_every_asset_has_a_computed_locator(manifest):
    for a in manifest["assets"]:
        loc = a["locator"]
        assert loc["method"] in {"document", "char_span"}
        assert 0 <= loc["start_char"] < loc["end_char"] <= CONTRACT_CHARS
        assert 1 <= loc["start_line"] <= loc["end_line"]
        assert isinstance(loc["quote"], str) and loc["quote"]
        assert a["resolution"] in BY_RESOLUTION


def test_figures_are_metadata_only(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    assert {a["label"] for a in figs} == FIGURE_NAMES
    for a in figs:
        # no png_base64 in record.figures[] -> no byte hash may be claimed
        assert a["sha256"] is None and a["bytes"] is None
        assert a["resolution"] == "referenced_unresolved"
        assert a["resolution_detail"] == "metadata_only"
        assert "png_base64" in a["note"]


def test_resolution_is_honest_in_both_directions(manifest):
    """The audited repository *is* this worktree, so some paths must really resolve; a package that
    resolved everything (or nothing) would be reporting its own convenience, not the source."""
    resolved = {a["path_reference"] for a in manifest["assets"]
                if "path_reference" in a and a["resolution"] == "resolved_in_source"}
    assert resolved == RESOLVED_PATHS
    unresolved = [a for a in manifest["assets"] if a["resolution"] == "referenced_unresolved"
                  and a["asset_class"] != "embedded_figure"]
    assert unresolved, "the wildcard / bare-name references must not be silently resolved"
    for a in unresolved:
        assert a["resolution_check"]["result"] == "unresolved"
        assert "not" in a["resolution_check"]["detail"] or "absent" in a["resolution_check"]["detail"] \
            or "escapes" in a["resolution_check"]["detail"]


def test_no_verified_marks_anywhere():
    raw = MANIFEST.read_text(encoding="utf-8")
    assert '"status": "verified"' not in raw
    assert '"verified": true' not in raw.lower()
    for p in (RESULT, VERIFY, PROBE, LEDGER):
        assert '"verified": true' not in p.read_text(encoding="utf-8").lower()


# ------------------------------------------------------------------ offline: git evidence probe
def _git_ok(ref: str) -> bool:
    p = subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", ref + "^{commit}"],
                       capture_output=True, text=True)
    return p.returncode == 0


def test_probe_refs_really_exist_in_this_worktree(probe):
    refs = {r["ref"] for r in probe["refs"]}
    assert PROBE_REFS <= refs
    for r in probe["refs"]:
        assert r["probe"] == "git cat-file -e %s^{commit}" % r["ref"]
        # recomputed here, not trusted from the artifact
        assert r["present"] is _git_ok(r["ref"])
        if r["present"]:
            assert len(r["resolved_sha"]) == 40 and all(c in "0123456789abcdef" for c in r["resolved_sha"])
            assert r["ancestor_of_head"] is True
        else:
            assert "detail" in r


def test_probe_counters_and_range(probe):
    assert probe["all_refs_present"] is all(r["present"] for r in probe["refs"])
    assert probe["all_refs_present"] is True
    assert probe["source_hash"] == "sha256:" + CONTRACT_HASH
    assert probe["package_id"] == PACKAGE_ID and probe["report_id"] == REPORT_ID
    assert probe["ranges"], "the report's audit baseline is an explicit commit range"
    for x in probe["ranges"]:
        a, b = x["range"].split("..")
        assert x["endpoints_present"] is (_git_ok(a) and _git_ok(b))
        assert isinstance(x["commits_between"], int) and x["commits_between"] > 0
        assert "NOT re-verified" in x["note"]          # structural scope stated, not implied
    assert "never" in probe["scope_note"]


def test_probe_repo_identity(probe):
    repo = probe["repo"]
    assert repo["slug_claimed_in_report"] == "cxs503/TensorKnowledge"
    assert repo["slug_candidates"] == ["cxs503/TensorKnowledge"]
    assert repo["slug_match"] in {"match", "undecidable_no_remote", "remote_configured_but_slug_differs"}
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"],
                          capture_output=True, text=True).stdout.strip()
    # the probe records the worktree it ran in; on a later branch head may differ, so only shape is pinned
    assert len(repo["head"]) == 40 and len(head) == 40
    assert repo["objects_reachable"] >= 1


# ------------------------------------------------------------------ offline: ledger, report, readme
def test_publication_ledger_is_staging_not_receipt(ledger):
    assert ledger["package_id"] == PACKAGE_ID
    assert ledger["report_id"] == REPORT_ID
    assert ledger["status"] == "awaiting_pr_merge"
    assert ledger["payload_sha256"] == _sha(PAYLOAD)
    assert ledger["payload_markdown_sha256"] == _sha(REPORT)
    assert "not a publication receipt" in ledger["gate"]


def test_payload_markdown_is_the_report_bytes(payload):
    assert payload["markdown"] == REPORT.read_text(encoding="utf-8")
    assert payload["mission_id"] == MISSION_ID
    assert payload["scenario_key"] == SCENARIO_KEY
    assert len(payload["figures"]) == 1
    fig = payload["figures"][0]
    assert fig["name"] == FIGURE.name
    assert hashlib.sha256(__import__("base64").b64decode(fig["png_base64"])).hexdigest() == _sha(FIGURE)


def test_report_has_six_elements_and_one_json_block(envelope):
    text = REPORT.read_text(encoding="utf-8")
    for marker in ("## ① ", "## ② ", "## ③ ", "## ④ ", "## ⑥ ", "## ⑦ "):
        assert marker in text, marker
    assert "## ④-b git 证据探针" in text
    assert text.count("```json") == 1
    block = text.split("```json")[1].split("```")[0]
    assert json.loads(block) == envelope            # the envelope in the report is the envelope file


def test_report_states_the_fixpoint_and_the_probe(probe):
    text = REPORT.read_text(encoding="utf-8")
    assert "fixpoint" in text                       # verification runs again after publish
    for r in probe["refs"]:
        assert "`%s`" % r["ref"] in text
    assert "awaiting_pr_merge" in text


def test_readme_hashes_are_recomputed():
    text = README.read_text(encoding="utf-8")
    assert "README.md" not in text.split("## 文件清单")[1].split("##")[0]
    listed = 0
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        rel, size, digest = [c.strip() for c in line.strip("|").split("|")][:3]
        rel = rel.strip("`")
        p = PKG / rel
        if not p.is_file():
            continue
        assert size == str(len(p.read_bytes())), rel
        assert digest.strip("`") == _sha(p), rel
        listed += 1
    assert listed == 8, "every package file except README.md itself is listed"


def test_verification_covers_the_matured_artifacts(verdict, manifest):
    assert verdict["all_pass"] is True
    assert verdict["manifest_sha256"] == _sha(MANIFEST)
    assert "git_evidence_probe_reproducible" in verdict["checks"]
    assert "publication_ledger_consistent" in verdict["checks"]
    assert all(c["pass"] for c in verdict["checks"].values())
    assert verdict["checks"]["source_locator_resolvable"]["detail"].startswith("checked 22 locators")


def test_envelope_matches_manifest_on_disk(envelope):
    assert envelope["report_id"] == REPORT_ID
    assert envelope["package_id"] == PACKAGE_ID
    out = envelope["outputs"]["asset_manifest.json"]
    assert out["sha256"] == _sha(MANIFEST)
    assert out["bytes"] == len(MANIFEST.read_bytes())
    assert out["asset_count"] == 22
    assert envelope["provenance"]["source_hash"] == "sha256:" + CONTRACT_HASH
    assert envelope["claims"] == []


def test_figure_png_is_a_real_png():
    raw = FIGURE.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    w, h = struct.unpack(">II", raw[16:24])
    assert w > 500 and h > 400 and len(raw) > 20000


# ------------------------------------------------------------------ tool contract
def test_preset_pins_the_contract(registrar):
    cfg = registrar.PRESETS[PACKAGE_ID]
    assert cfg["report_id"] == REPORT_ID
    assert cfg["expected_hash"] == CONTRACT_HASH
    assert cfg["expected_chars"] == CONTRACT_CHARS
    assert cfg["out_dir"] == "docs/kf/wp-13547-01"
    assert cfg["mission_id"] == MISSION_ID
    assert cfg["scenario_key"] == SCENARIO_KEY
    assert cfg["declared_tokens"] == {"db_table": ["tensor_maturity_verdicts"],
                                     "schema_field": ["epistemic_status.enum"]}


def test_tool_exposes_the_matured_stages(registrar):
    for name in ("probe_git_evidence", "emit_publication", "render_readme", "_matured_extras",
                 "_check_matured_evidence"):
        assert callable(getattr(registrar, name)), name
    src = (REPO / "scripts" / "kf" / "kf01_register.py").read_text(encoding="utf-8")
    for action in ('"gitprobe" in acts', '"publish" in acts', '"readme" in acts'):
        assert action in src


def test_sibling_packages_still_parse(registrar):
    """The new stages are additive: previous presets must keep their contract untouched."""
    assert {"wp-7450-01", "wp-14068-01", "wp-12068-01", "wp-12724-01", PACKAGE_ID} <= set(registrar.PRESETS)
    assert "git_probe" not in registrar.PRESETS["wp-12724-01"]


# ------------------------------------------------------------------ live (skip when API is down)
def _live_markdown():
    base = os.environ.get("TENSOR_API_BASE")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    if not (base and user and pwd):
        pytest.skip("platform API env not configured")
    try:
        req = urllib.request.Request(base.rstrip("/") + "/auth/login",
                                     data=json.dumps({"username": user, "password": pwd}).encode(),
                                     method="POST", headers={"Content-Type": "application/json"})
        token = json.loads(urllib.request.urlopen(req, timeout=20).read().decode())["access_token"]
        req = urllib.request.Request(base.rstrip("/") + "/tensor/reports/" + REPORT_ID,
                                     headers={"Authorization": "Bearer " + token})
        rec = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    except (urllib.error.URLError, OSError, KeyError, ValueError) as exc:
        pytest.skip("platform API unreachable: %s: %s" % (type(exc).__name__, exc))
    return rec


def test_live_source_hash_matches_contract():
    rec = _live_markdown()
    md = rec["markdown"]
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_live_locators_recompute(manifest):
    md = _live_markdown()["markdown"]
    starts, off = [], 0
    for line in md.split("\n"):
        starts.append(off)
        off += len(line) + 1

    def line_of(char):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= char:
                lo = mid
            else:
                hi = mid - 1
        return lo

    for a in manifest["assets"]:
        loc = a["locator"]
        s, e = loc["start_char"], loc["end_char"]
        assert md[s:e] == loc["quote"], a["asset_id"]
        assert md.count(loc["quote"]) >= 1
        assert line_of(s) + 1 == loc["start_line"], a["asset_id"]
        assert line_of(e - 1) + 1 == loc["end_line"], a["asset_id"]


def test_live_figure_metadata_matches():
    rec = _live_markdown()
    figs = {f["name"] for f in rec.get("figures") or []}
    assert FIGURE_NAMES <= figs
    assert all(not (f.get("png_base64") or "") for f in rec["figures"]), (
        "the package registered these figures as metadata-only; bytes appearing here means the "
        "manifest must be rebuilt")