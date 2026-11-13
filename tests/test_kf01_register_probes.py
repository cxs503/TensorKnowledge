"""Unit tests for the probe layer added to scripts/kf/kf01_register.py.

The probe layer exists because KF reports cite artifact shapes that are not files with an
extension (globs, bare directories, commit anchors, commit ranges, repository slugs, registry
tables, paths outside the delivery worktree). These tests use synthetic names only and never
touch the network, so they run in any checkout.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "kf"))

import kf01_register as reg  # noqa: E402


def _git(*args):
    return subprocess.run(["git", *args], cwd=str(REPO), capture_output=True, text=True, check=True).stdout.strip()


# ------------------------------------------------------------------ resolve_local
def _unique_nested_basename():
    """A filename that occurs exactly once in the checkout, and not at the repository root."""
    idx = {}
    for f in REPO.rglob("*"):
        if f.is_file() and ".git" not in f.parts:
            idx.setdefault(f.name, []).append(f.relative_to(REPO))
    for name, ps in sorted(idx.items()):
        if len(ps) == 1 and ps[0].parent != Path(".") and "/" not in name and " " not in name:
            return name, str(ps[0])
    return None, None


def test_bare_basename_resolves_only_by_unique_match():
    name, rel = _unique_nested_basename()
    if name is None:
        pytest.skip("no unique non-root basename in this checkout")
    res = reg.resolve_local(name, REPO, allow_basename=True)
    assert res["status"] == "resolved_in_source", res
    assert res["resolved_paths"] == [rel]
    assert len(res["sha256"]) == 64


def test_bare_basename_ambiguous_is_not_resolved():
    idx = {}
    for f in REPO.rglob("*"):
        if f.is_file() and ".git" not in f.parts:
            idx.setdefault(f.name, []).append(f)
    # a name with no root-level copy, so the exact-path branch cannot resolve it first
    name = next((n for n, ps in sorted(idx.items())
                 if len(ps) > 1 and "/" not in n and " " not in n and not (REPO / n).is_file()), None)
    if name is None:
        pytest.skip("no duplicated basename in this checkout")
    res = reg.resolve_local(name, REPO, allow_basename=True)
    assert res["status"] == "referenced_unresolved"
    assert "ambiguous" in res["detail"]


def test_bare_basename_feature_is_off_by_default():
    name, _rel = _unique_nested_basename()
    if name is None:
        pytest.skip("no unique non-root basename in this checkout")
    assert reg.resolve_local(name, REPO)["status"] == "referenced_unresolved", \
        "basename resolution must be opt-in per package"


def test_elided_reference_keeps_its_dots():
    res = reg.resolve_local("...m7437.py", REPO, allow_basename=True)
    assert res["status"] == "referenced_unresolved"
    assert "elided" in res["detail"], res["detail"]


def test_absolute_path_outside_worktree_is_refused():
    res = reg.resolve_local("/definitely/not/here.py", REPO)
    assert res["status"] == "referenced_unresolved"
    assert "outside the delivery worktree" in res["detail"]


def test_dot_slash_prefix_still_resolves():
    res = reg.resolve_local("./ruff.toml", REPO)
    assert res["status"] == "resolved_in_source"


# ------------------------------------------------------------------ run_probe
def test_probe_dir_and_glob_resolve_inside_worktree():
    d = reg.run_probe({"probe": "dir", "label": "tests"}, REPO)
    assert d[0] == "resolved_in_source" and d[2] == "resolved"
    g = reg.run_probe({"probe": "glob", "label": "docs/kf/wp-13547-01/*.json"}, REPO)
    assert g[0] == "resolved_in_source" and len(g[4]["matched_files"]) >= 2


def test_probe_glob_miss_reports_git_history_not_a_bare_miss():
    res = reg.run_probe({"probe": "glob", "label": "no_such_dir_xyz/*.log"}, REPO)
    assert res[0] == "referenced_unresolved"
    assert res[2] == "unresolved"
    assert res[4]["entries_at_head"] == 0


def test_probe_git_commit_and_range():
    head = _git("rev-parse", "HEAD")
    c = reg.run_probe({"probe": "git_commit", "label": head}, REPO)
    assert c[0] == "resolved_in_source" and c[4]["ancestor_of_head"] is True
    r = reg.run_probe({"probe": "git_range", "label": "%s..%s" % (head, head)}, REPO)
    assert r[0] == "resolved_in_source" and r[4]["commits_in_range"] == 0
    missing = reg.run_probe({"probe": "git_commit", "label": "0" * 40}, REPO)
    assert missing[0] == "referenced_unresolved"


def test_probe_repo_slug_reads_origin():
    url = _git("remote", "get-url", "origin")
    assert url, "checkout has no origin remote"
    slug = url.rstrip("/").split(":")[-1].split("/")[-2:]
    res = reg.run_probe({"probe": "repo_slug", "label": "/".join(slug)}, REPO)
    assert res[0] == "resolved_in_source"


def test_probe_external_path_absent_when_report_declares_it():
    spec = {"probe": "external_path", "label": "/root/not/this/worktree",
            "absent_declared_by_report": True}
    assert reg.run_probe(spec, REPO)[0] == "declared_absent"
    spec.pop("absent_declared_by_report")
    assert reg.run_probe(spec, REPO)[0] == "referenced_unresolved"


def test_unknown_probe_kind_is_rejected():
    with pytest.raises(SystemExit):
        reg.run_probe({"probe": "nonsense", "label": "x"}, REPO)


# ------------------------------------------------------------------ scan_probes wiring
def test_scan_probes_pins_each_token_to_a_verbatim_span():
    md = "# t\n\nsee `tests` and `x.py` here\n"
    src = reg.Source(md)
    cfg = {"extra_probes": [{"asset_class": "dir_ref", "label": "tests", "probe": "dir"}]}
    out = reg.scan_probes(src, cfg, REPO)
    assert len(out) == 1
    loc = out[0]["locator"]
    assert md[loc["token_span"][0]:loc["token_span"][1]] == "tests"
    assert loc["quote"] in md and loc["start_line"] == 3
    assert out[0]["resolution"] == "resolved_in_source"


def test_scan_probes_refuses_a_token_that_is_absent_from_the_source():
    src = reg.Source("nothing here\n")
    with pytest.raises(SystemExit):
        reg.scan_probes(src, {"extra_probes": [{"asset_class": "x", "label": "tests", "probe": "dir"}]}, REPO)
