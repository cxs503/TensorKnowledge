#!/usr/bin/env python3
"""wp-12595-01 regression tests (01-asset-registration, report 12595).

Run: python3 -m pytest tests/kf/test_wp_12595_01.py -q
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / "wp-12595-01"
SRC_MD = REPO / "work" / "wp-12595-01" / "source" / "report_12595.md"
SRC_REC = REPO / "work" / "wp-12595-01" / "source" / "report_12595.json"
SCRIPT = REPO / "scripts" / "kf" / "wp-12595-01" / "register_assets.py"

CONTRACT_HASH = "sha256:1233e5e4fece836d70b124a36a82438a1e48dbfddfc168b14f4c1f7efd7a08ce"


@pytest.fixture(scope="module")
def env():
    return json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def am(env):
    return env["outputs"]["asset_manifest.json"]


@pytest.fixture(scope="module")
def md():
    return SRC_MD.read_text(encoding="utf-8")


def test_envelope_schema_pass(env):
    import jsonschema

    schema = json.loads((REPO / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(env, schema)


def test_source_hash_recomputed(env, md):
    digest = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert digest == CONTRACT_HASH
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert env["outputs"]["asset_manifest.json"]["source_asset"]["hash"]["matches_contract"] is True


def test_size_and_metadata(env, md):
    sa = env["outputs"]["asset_manifest.json"]["source_asset"]
    assert sa["size"]["chars"] == len(md) == 6420
    assert sa["size"]["bytes_utf8"] == len(md.encode("utf-8"))
    assert sa["record_metadata"]["title_matches_contract"] is True
    assert sa["record_metadata"]["scenario_key_matches_contract"] is True


def test_all_locators_verbatim_in_source(env, md):
    items = env["outputs"]["asset_manifest.json"]["locator_check"]["items"]
    assert len(items) >= 20
    for it in items:
        assert it["quote"] in md, it["ref_id"]
        assert it["resolved"] is True


def test_no_duplicate_ids(env):
    am = env["outputs"]["asset_manifest.json"]
    ids = [r["ref_id"] for r in am["referenced_artifacts"]] + [o["id"] for o in am["observations"]]
    assert len(ids) == len(set(ids))


def test_single_report_boundary_and_no_verified(env):
    am = env["outputs"]["asset_manifest.json"]
    b = am["boundary"]
    assert b["report_ids_read"] == ["12595"]
    assert b["report_ids_written"] == ["12595"]
    assert b["verification_status"] == "none"
    assert b["claims_generated"] == 0
    assert env["claims"] == []
    blob = json.dumps(env, ensure_ascii=False)
    assert '"verified"' not in blob
    assert '"status": "verified"' not in blob


def test_attachments_cross_check(env):
    att = env["outputs"]["asset_manifest.json"]["attachments"]
    assert att["count"] == 4
    for c in att["cross_check_markdown_vs_record"]:
        assert c["name_in_markdown"] is True
        assert c["caption_matches_markdown"] is True
    assert att["scan"]["png_base64_present"] is False


def test_c6_glob_registered(env):
    am = env["outputs"]["asset_manifest.json"]
    globs = [r for r in am["referenced_artifacts"] if r["path_kind"] == "glob"]
    assert len(globs) == 1
    assert globs[0]["raw_text"] == "tests/test_simp_sensitivity_consistency*.py"
    assert globs[0]["first_line"] == 50


def test_sections_cover_document(env, md):
    secs = env["outputs"]["asset_manifest.json"]["sections"]
    assert secs[0]["line_start"] == 1
    assert secs[-1]["line_end"] == len(md.split("\n"))
    lines = md.split("\n")
    for s in secs:
        body = "\n".join(lines[s["line_start"] - 1 : s["line_end"]])
        assert "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest() == s["sha256"]


def test_report_has_single_json_block_identical_to_artifact(env):
    rep = (OUT / "kf_result_wp-12595-01.md").read_text(encoding="utf-8")
    blocks = re.findall(r"^```json\n(.*?)\n```$", rep, flags=re.M | re.S)
    assert len(blocks) == 1
    block = json.loads(blocks[0])
    # identical except emission timestamps (re-runs refresh them)
    for d in (block, env):
        d.pop("provenance", None)
        d["outputs"]["asset_manifest.json"].pop("generated_at", None)
    assert block == env
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$",
                     json.loads(blocks[0])["provenance"]["emitted_at"])
    assert rep.startswith("# KF-RESULT wp-12595-01")


def test_negative_control_tampered_pinned_line_aborts(md):
    """Tampering a pinned evidence line must hard-abort (refuse-to-fabricate)."""
    sys.path.insert(0, str(SCRIPT.parent))
    import register_assets as reg

    md_tampered = md.replace(
        "fig1_sensitivity_and_error_maps.png", "fig1_sensitivity_and_error_mapsX.png", 1
    )
    rec = json.loads(SRC_REC.read_text(encoding="utf-8"))
    data = rec.get("data", rec)
    with pytest.raises(SystemExit, match="refuse-to-fabricate"):
        reg.build_manifest(md_tampered, data)


def test_negative_control_tampered_unpinned_line_hash_mismatch(md):
    """Tampering an unpinned line must be caught by the contract hash check."""
    sys.path.insert(0, str(SCRIPT.parent))
    import register_assets as reg

    md_tampered = md.replace("5.599e-08", "5.599e-09", 1)
    rec = json.loads(SRC_REC.read_text(encoding="utf-8"))
    data = rec.get("data", rec)
    manifest, stats = reg.build_manifest(md_tampered, data)
    assert stats["hash_match"] is False
    assert manifest["source_asset"]["hash"]["matches_contract"] is False


def test_pinned_evidence_lines_contain_literals(md):
    """Refuse-to-fabricate pins: each observation line must carry its literal."""
    lines = md.split("\n")
    assert "test_simp_sensitivity_consistency*.py" in lines[49]
    assert "test_simp_sensitivity_consistency_in157.py" in lines[107]
    assert "fig1_sensitivity_and_error_maps.png" in lines[79]
    assert "/root/tp-agent/work/m11206" in lines[110]


def test_offline_rerun_deterministic():
    """Offline re-run passes all acceptance checks and reproduces the manifest
    (modulo emission timestamps); committed artifacts are restored afterwards."""
    committed_am = (OUT / "asset_manifest.json").read_text(encoding="utf-8")
    committed_env = (OUT / "kf_result.json").read_text(encoding="utf-8")
    try:
        r = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--from-file",
                str(SRC_MD),
                "--record-json",
                str(SRC_REC),
                "--check",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO),
        )
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert all(out["acceptance"].values())
        fresh = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
        fresh.pop("generated_at", None)
        committed = json.loads(committed_am)
        committed.pop("generated_at", None)
        assert fresh == committed
    finally:
        (OUT / "asset_manifest.json").write_text(committed_am, encoding="utf-8")
        (OUT / "kf_result.json").write_text(committed_env, encoding="utf-8")


def test_figure_exists():
    p = OUT / "fig_acceptance.png"
    assert p.exists() and p.stat().st_size > 10_000


# ---------------------------------------------------------------------------
# Reopen round (mission m20380): guards for the two defect classes that sank
# the original PR#268 — (a) stale figure data drifting from the manifest,
# (b) bytecode (*.pyc / __pycache__) leaking into the delivery tree.
# ---------------------------------------------------------------------------
def test_fig_data_is_derived_from_committed_manifest(env):
    """fig_data.json must be a pure function of the committed manifest/envelope."""
    am = env["outputs"]["asset_manifest.json"]
    fd = json.loads((OUT / "fig_data.json").read_text(encoding="utf-8"))
    refs = am["referenced_artifacts"]
    counts = {}
    for r in refs:
        counts[r["path_kind"]] = counts.get(r["path_kind"], 0) + 1
    assert fd["by_kind"] == {k: counts.get(k, 0) for k in ("path", "glob", "field", "worktree", "branch")}
    assert fd["n_refs"] == len(refs) == 19
    assert fd["n_locators"] == am["locator_check"]["total"] == 27
    assert fd["n_resolved"] == am["locator_check"]["resolved"] == 27
    assert fd["n_sections"] == len(am["sections"]) == 11
    assert fd["n_attachments"] == am["attachments"]["count"] == 4
    assert fd["n_obs"] == len(am["observations"]) == 3
    assert fd["n_unresolved"] == len(am["unresolved"]) == 2
    # acceptance rows in fig_data must equal a fresh machine re-check
    sys.path.insert(0, str(SCRIPT.parent))
    import register_assets as reg

    md_src, data = reg.load_source(
        type("A", (), {"from_file": str(SRC_MD), "record_json": str(SRC_REC)})()
    )
    manifest, stats = reg.build_manifest(md_src, data)
    assert fd["checks"] == reg.run_checks(reg.build_envelope(manifest), stats)


def test_png_is_a_real_raster():
    raw = (OUT / "fig_acceptance.png").read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    width = int.from_bytes(raw[16:20], "big")
    height = int.from_bytes(raw[20:24], "big")
    assert (width, height) == (1540, 588) or (width > 1000 and height > 400)
    assert len(raw) > 10_000


def test_no_bytecode_or_pycache_in_delivery_paths():
    """PR#268 shipped ke/__pycache__/*.pyc; the delivery paths must stay clean."""
    # on-disk bytecode is gitignored and may be produced by importing the
    # generators at test time; what must never happen is bytecode *shipped*
    # as part of the deliverable set (docs/) or *tracked* by git.
    assert not list(OUT.rglob("*.pyc"))
    assert not list(OUT.rglob("__pycache__"))
    tracked = subprocess.run(
        [
            "git",
            "-C",
            str(REPO),
            "ls-files",
            "--",
            "docs/kf/wp-12595-01",
            "scripts/kf/wp-12595-01",
            "work/wp-12595-01",
            "tests/kf/test_wp_12595_01.py",
            "scripts/kf_fetch_12595.py",
        ],
        capture_output=True,
        text=True,
    )
    if tracked.returncode == 0:
        bad = [p for p in tracked.stdout.split() if p.endswith((".pyc", ".pyo")) or "__pycache__" in p]
        assert bad == []


def test_fetch_script_pins_contract_hash():
    src = (REPO / "scripts" / "kf_fetch_12595.py").read_text(encoding="utf-8")
    assert CONTRACT_HASH in src
    assert "TENSOR_AGENT_PASS" in src and '"password"' in src  # creds from env, not literal
    reg_src = SCRIPT.read_text(encoding="utf-8")
    assert CONTRACT_HASH in reg_src and "refuse-to-fabricate" in reg_src
