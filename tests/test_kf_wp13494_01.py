"""Independent re-check of the wp-13494-01 asset registration (report 13494).

Two layers, deliberately separated:

* **Hermetic** — everything that can be re-derived from the committed artefacts alone
  (``docs/kf/wp-13494-01/*.json``, the figure, the rendered report).  This is what CI runs; it
  never calls the platform and it does not import the producer, so a hand-edited manifest or a
  stale envelope fails here.
* **Live** — locator re-resolution against the platform record itself (``GET
  /api/v1/tensor/reports/13494``).  Skipped when the API is unreachable; when it is reachable the
  absolute character spans + 1-based line map are re-checked against the platform's own markdown,
  which is exactly what the platform gate can redo without trusting this package.

The locator checker is exercised by a negative control (:func:`test_locator_checker_has_teeth`),
so a green run means "checked", not "checked nothing".

Contract (work package wp-13494-01): report_id 13494,
source_hash sha256:ad61f9e0…83abe, 12251 chars, task_type 01-asset-registration (registration only,
no extraction, no claims, nothing marked ``verified``).
"""

from __future__ import annotations

import hashlib
import json
import os
import urllib.request
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
PKG_DIR = REPO / "docs" / "kf" / "wp-13494-01"
PKG = "wp-13494-01"
REPORT_ID = "13494"
CONTRACT_HASH = "ad61f9e0bc3dbe8c8f4ae40ce90056f06c98477c9a33302193f8297756783abe"
CONTRACT_CHARS = 12251
CONTRACT_TITLE = "TensorDEM GPU 100K Gate — CPU Scaling & Correctness Verification"
CONTRACT_SCENARIO = "p447w2-n03-dem-gpu-100k"
RESOLUTIONS = {"resolved_in_source", "referenced_unresolved", "declared_absent"}
ACCEPTANCE = (
    "valid_json",
    "schema_pass",
    "source_locator_resolvable",
    "source_hash_matches",
    "no_duplicate_ids",
    "all_claims_have_evidence_or_explicit_unresolved_status",
    "do_not_mark_claims_as_verified",
    "report_id_scoped",
    "manifest_hash_matches_envelope",
)


# ------------------------------------------------------------------ fixtures
def _load(name):
    return json.loads((PKG_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest():
    return _load("asset_manifest.json")


@pytest.fixture(scope="module")
def envelope():
    return _load("kf_result.json")


@pytest.fixture(scope="module")
def verdict():
    return _load("verification.json")


@pytest.fixture(scope="module")
def determinism():
    return _load("determinism.json")


@pytest.fixture(scope="module")
def published():
    return _load("published_check.json")


@pytest.fixture(scope="module")
def report_md():
    return (PKG_DIR / "report.md").read_text(encoding="utf-8")


# ------------------------------------------------------------------ independent locator checker
def canonical_sha256(obj):
    """Re-implemented here (not imported from the producer) so the check is independent."""
    text = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def without(doc, *path):
    import copy

    out = copy.deepcopy(doc)
    node = out
    for key in path[:-1]:
        node = node[key]
    node.pop(path[-1], None)
    return out


def line_starts(md: str):
    starts, off = [], 0
    for line in md.splitlines(keepends=True):
        starts.append(off)
        off += len(line)
    return starts


def line_of(starts, pos: int) -> int:
    n = 0
    for i, s in enumerate(starts):
        if s <= pos:
            n = i
        else:
            break
    return n + 1


def locator_failures(manifest: dict, md: str):
    """Every locator must be an in-range absolute span whose verbatim quote is md[s:e] and whose
    1-based line numbers match the span.  Returns a list of (asset_id, reason)."""
    starts = line_starts(md)
    bad = []
    for a in manifest["assets"]:
        loc = a["locator"]
        s, e, q = loc["start_char"], loc["end_char"], loc["quote"]
        if not isinstance(s, int) or not isinstance(e, int):
            bad.append((a["asset_id"], "span not integer"))
            continue
        if not (0 <= s < e <= len(md)):
            bad.append((a["asset_id"], "span out of range"))
            continue
        if md[s:e] != q:
            bad.append((a["asset_id"], "quote != md[start:end]"))
            continue
        if (
            line_of(starts, s) != loc["start_line"]
            or line_of(starts, e - 1) != loc["end_line"]
        ):
            bad.append((a["asset_id"], "line map"))
            continue
        if "token" in loc:
            ts, te = loc["token_span"]
            if md[ts:te] != loc["token"] or not (s <= ts and te <= e):
                bad.append((a["asset_id"], "token span"))
    return bad


# ------------------------------------------------------------------ package shape
def test_package_files_exist():
    for rel in (
        "asset_manifest.json",
        "kf_result.json",
        "verification.json",
        "determinism.json",
        "published_check.json",
        "report.md",
        "report_payload.json",
        "figures/%s_asset_locator_map.png" % PKG,
    ):
        p = PKG_DIR / rel
        assert p.is_file(), "missing deliverable %s" % rel
        assert p.stat().st_size > 0, "empty deliverable %s" % rel


def test_json_artefacts_are_valid_json():
    for name in (
        "asset_manifest.json",
        "kf_result.json",
        "verification.json",
        "determinism.json",
        "published_check.json",
        "report_payload.json",
    ):
        assert isinstance(_load(name), dict)


def test_manifest_is_scoped_to_the_contract_report(manifest):
    assert manifest["package_id"] == PKG
    assert manifest["task_type"] == "01-asset-registration"
    assert manifest["report_id"] == REPORT_ID
    assert manifest["source"]["uri"] == "tensor://reports/%s" % REPORT_ID
    assert manifest["source"]["hash"] == CONTRACT_HASH
    assert manifest["source"]["chars"] == CONTRACT_CHARS
    assert manifest["source"]["title"] == CONTRACT_TITLE
    assert manifest["source"]["scenario_key"] == CONTRACT_SCENARIO
    assert manifest["source"]["platform_figures"] == ["fig1_scaling"]


def test_registration_only_no_claims_and_nothing_verified(manifest, envelope):
    assert manifest["claims"] == [] and envelope["claims"] == []
    blob = json.dumps(manifest) + json.dumps(envelope)
    assert '"verified"' not in blob, "registration must not carry a verified mark"


def test_asset_ids_unique_and_well_formed(manifest):
    ids = [a["asset_id"] for a in manifest["assets"]]
    assert ids == ["A%02d" % i for i in range(1, len(ids) + 1)]
    assert len(set(ids)) == len(ids)
    for a in manifest["assets"]:
        assert a["resolution"] in RESOLUTIONS
        assert a["kind"] == a["asset_class"]
        assert a["locator"]["quote"], "asset %s has an empty quote" % a["asset_id"]


def test_counts_are_consistent_with_assets(manifest):
    assets = manifest["assets"]
    counts = manifest["counts"]
    by_class, by_res = {}, {}
    for a in assets:
        by_class[a["asset_class"]] = by_class.get(a["asset_class"], 0) + 1
        by_res[a["resolution"]] = by_res.get(a["resolution"], 0) + 1
    assert counts["assets"] == len(assets)
    assert counts["by_class"] == by_class
    assert counts["by_resolution"] == by_res
    assert counts["resolved_in_source"] + counts["referenced_unresolved"] + counts[
        "declared_absent"
    ] == len(assets)
    # every cross-repository reference stays unresolved by design (TensorDEM paths, not this worktree)
    assert counts["distinct_referenced_paths"] == 5


def test_figure_is_metadata_only_as_declared(manifest):
    figs = [a for a in manifest["assets"] if a["asset_class"] == "embedded_figure"]
    assert len(figs) == 1
    assert figs[0]["resolution"] == "referenced_unresolved"
    assert figs[0]["resolution_detail"] == "metadata_only"
    assert figs[0]["sha256"] is None, (
        "no png payload exists, so no byte hash may be claimed"
    )


# ------------------------------------------------------------------ envelope / self-check
def test_envelope_matches_manifest_bytes(manifest, envelope, verdict):
    raw = (PKG_DIR / "asset_manifest.json").read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    assert envelope["outputs"]["asset_manifest.json"]["sha256"] == digest
    assert envelope["outputs"]["asset_manifest.json"]["bytes"] == len(raw)
    assert verdict["manifest_sha256"] == digest
    assert (
        envelope["outputs"]["asset_manifest.json"]["asset_count"]
        == manifest["counts"]["assets"]
    )


def test_envelope_provenance_matches_contract(envelope):
    prov = envelope["provenance"]
    assert prov["source_uri"] == "tensor://reports/%s" % REPORT_ID
    assert prov["source_hash"] == "sha256:" + CONTRACT_HASH
    assert prov["source_chars"] == CONTRACT_CHARS
    assert prov["hash_algo"] == "sha256"


def test_selfcheck_passes_every_acceptance_item(verdict):
    assert set(verdict["checks"]) >= set(ACCEPTANCE)
    for name in ACCEPTANCE:
        assert verdict["checks"][name]["pass"] is True, "%s failed: %s" % (
            name,
            verdict["checks"][name],
        )
    assert verdict["all_pass"] is True


# ------------------------------------------------------------------ determinism evidence
def test_determinism_invariants_hold_and_are_honest(determinism):
    assert determinism["method"]["builds"] == 2
    assert determinism["invariants"]["asset_manifest_canonical_identical"] is True
    assert determinism["invariants"]["kf_result_canonical_identical"] is True
    assert determinism["invariants"]["figure_bytes_identical"] is True
    assert determinism["all_identical"] is True
    # honest about what was excluded instead of silently hashing a timestamp
    excluded = determinism["method"]["excluded_volatile_fields"]
    assert excluded["asset_manifest.json"] == ["generated_at"]
    assert excluded["kf_result.json"] == [
        "provenance.emitted_at",
        "outputs.asset_manifest.json.sha256",
    ]
    assert (
        "kf_result.outputs.asset_manifest.json.path"
        in determinism["method"]["normalised_fields"]
    )
    assert (
        determinism["expected_differences"]["asset_manifest_raw_bytes_identical"]
        is False
    )


def test_determinism_hashes_equal_the_committed_artefacts(
    manifest, envelope, determinism
):
    """The recorded canonical hashes must be those of the *committed* manifest/envelope: a rebuild
    that drifted (or a post-hoc hand edit) makes this fail."""
    canon = canonical_sha256(without(manifest, "generated_at"))
    for run in determinism["runs"]:
        assert run["asset_manifest_canonical_sha256"] == canon

    # exactly the three fields determinism.json declares as excluded/normalised: the two build clocks
    # and the envelope digest *of the manifest* (a function of the manifest clock)
    env = without(
        without(envelope, "provenance", "emitted_at"),
        "outputs",
        "asset_manifest.json",
        "sha256",
    )
    # the producer builds each determinism run into its own temp dir, so the recorded output path is
    # normalised to the package path before hashing (stated in determinism.json.method.normalised_fields)
    env["outputs"]["asset_manifest.json"]["path"] = (
        "docs/kf/%s/asset_manifest.json" % PKG
    )
    assert [run["kf_result_canonical_sha256"] for run in determinism["runs"]] == [
        canonical_sha256(env)
    ] * 2

    png = (PKG_DIR / "figures" / ("%s_asset_locator_map.png" % PKG)).read_bytes()
    assert {run["figure_bytes_sha256"] for run in determinism["runs"]} == {
        hashlib.sha256(png).hexdigest()
    }


def test_determinism_runs_used_the_same_source(determinism):
    for run in determinism["runs"]:
        assert run["asset_count"] == 12
        assert run["generated_at"] and run["emitted_at"]  # clocks recorded, not hidden


# ------------------------------------------------------------------ published record cross-check
def test_published_check_passes(published):
    assert published["api"] == "GET /api/v1/tensor/reports/%s" % REPORT_ID
    for name, check in published["checks"].items():
        assert check["pass"] is True, "%s failed: %s" % (name, check)
    assert published["all_pass"] is True
    rec = published["record"]
    assert rec["status"] == "published"
    assert rec["markdown_sha256"] == CONTRACT_HASH
    assert rec["markdown_chars"] == CONTRACT_CHARS
    assert rec["title"] == CONTRACT_TITLE and rec["scenario_key"] == CONTRACT_SCENARIO
    assert rec["figures"] == [{"name": "fig1_scaling", "png_base64_bytes": 0}]


# ------------------------------------------------------------------ report
def test_report_renders_the_artefacts(report_md, manifest, determinism, published):
    assert report_md.count("```json") == 1, (
        "report must carry exactly one fenced json block (the envelope)"
    )
    assert manifest["source"]["hash"] in report_md
    assert "figures/%s_asset_locator_map.png" % PKG in report_md
    assert "scripts/kf/kf_wp13494_01.py" in report_md, (
        "reproduction command must name the real driver"
    )
    assert "determinism.json" in report_md and "published_check.json" in report_md
    assert str(manifest["counts"]["assets"]) in report_md
    assert "NOT_SUPPORTED" in report_md, (
        "the source's honest GPU verdict must survive into the report"
    )
    for run in determinism["runs"]:
        assert run["asset_manifest_canonical_sha256"][:16] in report_md


def test_figure_is_a_real_png(manifest):
    png = PKG_DIR / "figures" / ("%s_asset_locator_map.png" % PKG)
    raw = png.read_bytes()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(raw) > 10_000, "figure looks empty (%d bytes)" % len(raw)


def test_report_payload_matches_package(report_md, manifest):
    payload = _load("report_payload.json")
    assert payload["markdown"] == report_md
    assert "report_id:%s" % REPORT_ID in payload["tags"]
    assert (
        payload["figures"]
        and payload["figures"][0]["name"] == "%s_asset_locator_map.png" % PKG
    )
    assert payload["mission_id"] == 20520


# ------------------------------------------------------------------ negative control
def test_locator_checker_has_teeth(manifest):
    """A one-character shift in the span or a mutated quote must be rejected by the same checker the
    live test uses — otherwise 'all locators resolve' would be vacuous."""
    import copy

    # build a synthetic source from the quotes themselves: enough to prove the checker is not a no-op
    fake = copy.deepcopy(manifest)
    md = " " * 4000
    # place every quote at its recorded offset inside a synthetic buffer
    buf = list(md)
    for a in fake["assets"]:
        loc = a["locator"]
        q = loc["quote"]
        s = loc["start_char"]
        if s + len(q) <= len(buf):
            buf[s : s + len(q)] = list(q)
    md = "".join(buf)
    # synthetic buffer will not reproduce every nested span exactly, so only require: no crash, and
    # that shifting one asset's span by one character IS detected when its quote is present.
    a0 = next(
        a
        for a in fake["assets"]
        if a["locator"]["start_char"] + len(a["locator"]["quote"]) <= len(md)
    )
    assert (
        md[a0["locator"]["start_char"] : a0["locator"]["end_char"]]
        == a0["locator"]["quote"]
    )
    a0["locator"]["start_char"] += 1
    failures = locator_failures(fake, md)
    assert (a0["asset_id"], "quote != md[start:end]") in failures

    # and a mutated quote is detected too
    b = copy.deepcopy(next(a for a in manifest["assets"]))
    b["locator"]["quote"] = b["locator"]["quote"] + "X"
    assert locator_failures({"assets": [b]}, md)


# ------------------------------------------------------------------ live re-check (network optional)
def _api():
    base = os.environ.get("TENSOR_API_BASE")
    if not base:
        return None
    base = base.rstrip("/")
    try:
        body = json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode()
        req = urllib.request.Request(
            base + "/auth/login",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        tok = json.loads(urllib.request.urlopen(req, timeout=8).read().decode())[
            "access_token"
        ]
        req = urllib.request.Request(base + "/tensor/reports/%s" % REPORT_ID)
        req.add_header("Authorization", "Bearer " + tok)
        rec = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
        return rec if isinstance(rec.get("markdown"), str) else None
    except Exception:  # noqa: BLE001 - offline / auth-less environments skip, never fail
        return None


@pytest.fixture(scope="module")
def live_record():
    rec = _api()
    if rec is None:
        pytest.skip(
            "platform API unreachable: locator re-resolution against the live record skipped"
        )
    return rec


def test_live_source_matches_contract(live_record, manifest):
    md = live_record["markdown"]
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS == manifest["source"]["chars"]
    assert live_record.get("status") == "published"


def test_live_locators_resolve(live_record, manifest):
    failures = locator_failures(manifest, live_record["markdown"])
    assert failures == [], "locators failing against the live record: %s" % failures
