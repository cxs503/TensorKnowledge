"""m24139 (管到底第2轮 / PROD-RA R8c): the R5-1/R5-2/R5-3 residuals of the
m22059 PROD-RA review bundle must hold on the *committed* tree.

Background
----------
The R6/R8 repair (commit e4d086e / cherry-pick 1ad7b60) closed the three R5
residuals, but the platform pusher gate filtered the repair files out of the
merge (docs/m22059/** is a foreign mission segment; raw/*.log is a record
extension), so main kept the pre-repair bytes while the review package
already carried the post-repair manifest.  This test pins the three frozen
criteria (R5 receipt + docs/m23257/verify_status.py semantics) so a future
regression of the same kind is caught by the suite instead of by a re-review
round:

* R5-1  every pure-path locator field in docs/m22059/**/*.json and
        docs/review_m22059_prod_ra/**/*.json resolves from the repo root
        (cold-start, tracked files only) or is an explicit
        platform-evidence:// pointer; 0 legacy ``runs/m22059/`` prefixes,
        0 absolute foreign worktree paths.
* R5-2  docs/review_m22059_prod_ra/SHA256SUMS is sound: every entry's file
        exists and its sha256 equals the recomputed digest (0 missing /
        0 mismatch).
* R5-3  D6 evidence bundle in docs/m22059/validation-report.json: 5/5 items
        carry provenance.input_sha256, 0 absolute foreign input_refs, 5/5
        source_ref cold-resolvable, 5/5 item sha256 equal to the actual
        source digest, bundle self-digest matches under the canonical
        convention (sorted compact JSON, UTF-8).
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
M22059 = REPO / "docs" / "m22059"
REVIEW = REPO / "docs" / "review_m22059_prod_ra"

LEGACY_PREFIX = "runs/m22059/"
FOREIGN_ROOT = "/root/tp-agent/"
PLATFORM_POINTER = "platform-evidence://"

PATH_TOKEN = re.compile(r"(?:runs/|docs/m22059/|/root/tp-agent/)[^\s\"',)\]]*")


def _sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _canonical_sha256(obj) -> str:
    """tensorbench.criteria.canonical_sha256 without the import dependency."""
    canon = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _walk_strings(obj, path="$"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_strings(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_strings(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def _is_pure_path(s: str) -> bool:
    core = s.split("#")[0]
    return bool(core) and not re.search(r"\s", core) and core.startswith(
        ("runs/", "docs/m22059/", "/root/tp-agent/"))


def _pure_path_locators():
    """Yield (file, json_path, locator) for every pure-path locator field."""
    for base in (M22059, REVIEW):
        for f in sorted(base.rglob("*.json")):
            try:
                obj = json.loads(f.read_text(encoding="utf-8"))
            except Exception:
                continue
            for jpath, s in _walk_strings(obj):
                if not any(t in s for t in ("runs/", "docs/m22059/", "/root/tp-agent/")):
                    continue
                if _is_pure_path(s):
                    yield f, jpath, s


@pytest.fixture(scope="module")
def locators():
    return list(_pure_path_locators())


def test_r5_1_no_legacy_runs_prefix(locators):
    bad = [(str(f.relative_to(REPO)), jp, s) for f, jp, s in locators
           if s.split("#")[0].startswith(LEGACY_PREFIX)]
    assert not bad, f"legacy runs/m22059/ locators still present: {bad[:5]}"


def test_r5_1_no_absolute_foreign_worktree_paths(locators):
    bad = [(str(f.relative_to(REPO)), jp, s) for f, jp, s in locators
           if s.split("#")[0].startswith(FOREIGN_ROOT)]
    assert not bad, f"absolute foreign worktree locators still present: {bad[:5]}"


def test_r5_1_every_pure_path_locator_cold_resolves(locators):
    unresolved = []
    for f, jp, s in locators:
        core = s.split("#")[0]
        if core.startswith(PLATFORM_POINTER):
            continue  # explicit pointer, allowed form per the frozen criterion
        if not (REPO / core).exists():
            unresolved.append((str(f.relative_to(REPO)), jp, s))
    assert not unresolved, f"locators unresolvable from repo root: {unresolved[:5]}"


def test_r5_2_manifest_sound():
    sums = REVIEW / "SHA256SUMS"
    assert sums.is_file(), "review package manifest missing"
    missing, mismatch = [], []
    entries = 0
    for line in sums.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        digest, _, rel = line.partition("  ")
        entries += 1
        p = REVIEW / rel
        if not p.is_file():
            missing.append(rel)
        elif _sha256_file(p) != digest:
            mismatch.append(rel)
    assert entries >= 14, f"manifest unexpectedly small: {entries} entries"
    assert not missing, f"manifest entries with missing files: {missing}"
    assert not mismatch, f"manifest entries with digest mismatch: {mismatch}"


def test_r5_3_d6_bundle_all_green():
    report = json.loads((M22059 / "validation-report.json").read_text(encoding="utf-8"))
    bundle = report["evidence_bundle"]
    items = bundle["evidence_items"]
    assert len(items) == 5, f"expected 5 evidence items, got {len(items)}"

    no_fingerprint, abs_refs, bad_src, bad_sha = [], {}, [], []
    for it in items:
        eid = it.get("evidence_id")
        prov = it.get("provenance", {}) or {}
        if not prov.get("input_sha256"):
            no_fingerprint.append(eid)
        refs = prov.get("input_refs")
        flat = ([refs] if isinstance(refs, str) else list(refs or []))
        foreign = [r for r in flat if str(r).startswith("/root/")]
        if foreign:
            abs_refs[eid] = foreign
        src = str(it.get("source_ref", "")).split("#")[0]
        src_p = REPO / src
        if not src_p.exists():
            bad_src.append((eid, src))
        elif _sha256_file(src_p) != it.get("sha256"):
            bad_sha.append(eid)
    assert not no_fingerprint, f"items without provenance.input_sha256: {no_fingerprint}"
    assert not abs_refs, f"items with absolute foreign input_refs: {abs_refs}"
    assert not bad_src, f"source_ref not cold-resolvable: {bad_src}"
    assert not bad_sha, f"item sha256 != actual source digest: {bad_sha}"

    canon = {k: v for k, v in bundle.items() if k != "integrity"}
    declared = (bundle.get("integrity") or {}).get("bundle_sha256")
    assert declared == _canonical_sha256(canon), (
        f"bundle_sha256 mismatch: declared {declared} != recomputed "
        f"{_canonical_sha256(canon)}")


def test_review_package_entry_point_still_runs():
    """The reviewer entry point must still run clean on the repaired tree."""
    import subprocess
    import sys
    out = REPO / "docs" / "m24139" / "raw" / "recheck_cold_r8c.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        [sys.executable, str(REVIEW / "recheck.py"),
         "--target", str(REPO), "--out", str(out)],
        cwd=str(REPO), capture_output=True, text=True, timeout=600)
    payload = json.loads(out.read_text(encoding="utf-8"))
    six = payload.get("six_checks", {})
    assert six.get("all_six_pass") is True, (
        f"six checks not all green: { {k: v.get('pass') for k, v in six.items() if isinstance(v, dict)} }")
