"""Offline unit tests for the wp-9777-01 asset-registration helpers.

No network, no platform access: only the pure parsers are exercised, so the
extraction rules (which decide what counts as an asset) are pinned by CI.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "kf_wp9777_01", ROOT / "scripts" / "kf_wp9777_01_register.py")
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)

SAMPLE = """# demo report

**脚本**：`bench/run_calib.py` · **模块**：`pkg.kernel_core`（内核）·
**图**：`figures/demo/`

![curve](figures/demo/curve.png)

壁面应力（乘 `(1-1/2τ)` 因子）与 `config.json` 一致。

### 3.3 drag table
| case | Re |
|---|---|
| drag_re012 | 0.12 | 172.6 |
| not_a_case | 1 |

### 3.4 closing
| krieger_dougherty | calibrated |

## 6. verdicts
| check | verdict | value |
|---|---|---|
| wall_momentum_balance | PASS | {'case_a': 0.01, 'case_b': 0.02} |
""".rstrip("\n").split("\n")


def test_is_pathlike_rejects_expressions_and_modules():
    assert mod.is_pathlike("bench/run_calib.py")
    assert mod.is_pathlike("figures/demo/")
    assert not mod.is_pathlike("pkg.kernel_core")      # module name, not a path
    assert not mod.is_pathlike("(1-1/2τ)")             # expression with a slash
    assert not mod.is_pathlike("http://example/x.py")


def test_classify_directory_and_figure():
    assert mod.classify("figures/demo/") == "directory_reference"
    assert mod.classify("figures/demo/curve.png") == "figure_reference"
    assert mod.classify("config.json") == "data_artifact_reference"


def test_scan_refs_collects_paths_once_per_line():
    refs = mod.scan_refs(SAMPLE)
    names = [r["token"] for r in refs]
    assert "bench/run_calib.py" in names
    assert "figures/demo/curve.png" in names
    assert "config.json" in names
    assert "pkg.kernel_core" not in names
    assert "(1-1/2τ)" not in names
    # one asset per (path, line)
    assert len(names) == len(set(zip(names, [r["line"] for r in refs])))


def test_scan_case_ids_scopes_drag_table_and_dict_literal():
    got = {c["case_id"]: c for c in mod.scan_case_ids(SAMPLE)}
    assert set(got) == {"drag_re012", "case_a", "case_b"}
    assert "krieger_dougherty" not in got      # §3.4 table is out of scope
    assert "not_a_case" not in got             # 1 numeric cell is not a case row


def test_scan_case_ids_ignores_tables_outside_33():
    lines = ["### 3.4 closing", "| some_case_name | x |"]
    assert mod.scan_case_ids(lines) == []


def test_scan_symbols_finds_modules_not_paths():
    syms = mod.scan_symbols(SAMPLE)
    toks = {s["token"] for s in syms}
    assert "pkg.kernel_core" in toks
    assert "bench/run_calib.py" not in toks


def test_resolve_in_worktree_marks_absent_path_unresolved():
    res = mod.resolve_in_worktree("definitely/not/present/here.py")
    assert res["status"] == "unresolved"
    assert res["scope"] == "delivery_worktree"
    res2 = mod.resolve_in_worktree("scripts/kf_wp9777_01_register.py")
    assert res2["status"] == "resolved"
    assert res2["sha256"].startswith("sha256:")


def test_sha256_hex_is_utf8_byte_hash():
    assert mod.sha256_hex("冰".encode()) == (
        "sha256:" + __import__("hashlib").sha256("冰".encode("utf-8")).hexdigest())


def test_manifest_file_exists_and_valid():
    """Integration: the generated manifest is valid JSON with expected keys."""
    import json
    manifest_path = ROOT / "docs" / "kf" / "wp-9777-01" / "asset_manifest.json"
    assert manifest_path.exists(), "manifest not found"
    m = json.loads(manifest_path.read_text())
    assert m["package_id"] == "wp-9777-01"
    assert m["report_id"] == "9777"
    assert "assets" in m
    assert len(m["assets"]) > 0


def test_envelope_file_exists_and_valid():
    """Integration: the generated envelope is valid JSON with expected keys."""
    import json
    envelope_path = ROOT / "docs" / "kf" / "wp-9777-01" / "kf_result.json"
    assert envelope_path.exists(), "envelope not found"
    e = json.loads(envelope_path.read_text())
    assert e["package_id"] == "wp-9777-01"
    assert e["report_id"] == "9777"
    assert e["verification_status"] == "not_verified"


def test_verification_file_exists_and_pass():
    """Integration: the generated verification has all checks passing."""
    import json
    verif_path = ROOT / "docs" / "kf" / "wp-9777-01" / "verification.json"
    assert verif_path.exists(), "verification not found"
    v = json.loads(verif_path.read_text())
    assert v["overall"] == "PASS"
    assert all(c["result"] == "pass" for c in v["checks"])


def test_source_copy_exists():
    """Integration: the source markdown copy exists."""
    source_path = ROOT / "docs" / "kf" / "wp-9777-01" / "source" / "r9777.md"
    assert source_path.exists(), "source copy not found"
    content = source_path.read_text()
    assert "Timoshenko" in content
    assert "DSM" in content


def test_figure_file_exists():
    """Integration: the asset locator map figure exists."""
    fig_path = ROOT / "docs" / "kf" / "wp-9777-01" / "figures" / "fig1_asset_locator_map.png"
    assert fig_path.exists(), "figure not found"
    data = fig_path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a valid PNG"
