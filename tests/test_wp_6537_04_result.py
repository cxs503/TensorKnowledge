"""Invariant tests for the wp-6537-04 review package (independent review of wp-6537-01).

These assert *properties of the delivered evidence*, not merely that code runs:

  * the review envelope is complete and its provenance binds the exact bytes reviewed;
  * every finding quote resolves byte-exactly inside its declared source file;
  * the verdict follows from the blocking/non-blocking finding split;
  * the review's headline numbers (31 span-tested / 6 skipped, 5 unresolvable figure
    locators, 72 canonical-schema errors, TtW residual, slip crossover) are **recomputed**
    here from primary bytes — a stale or hand-edited number turns the suite red;
  * mutation cases prove the locator check can actually go red (it is not vacuous);
  * the delivery contains no build junk (the original PR#330 shipped two .pyc files).

Run: pytest -q tests/test_wp_6537_04_result.py
"""

import hashlib
import importlib.util
import json
import os
import re

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "docs", "kf", "wp-6537-04")
UP = os.path.join(ROOT, "docs", "kf", "wp-6537-01")
SNAPSHOT = os.path.join(UP, "source_6537.md")
MANIFEST = os.path.join(UP, "asset_manifest.json")
VERIFICATION = os.path.join(UP, "verification.json")
SCRIPT = os.path.join(ROOT, "scripts", "kf", "review_wp_6537_04.py")

CONTRACT_HASH = "aaf27418db0e671d671f7cafa2aecf6d68e235f593384832f3fb46cf152d1f71"
REVIEWED_MANIFEST_SHA = "5afa3314a56cda0010c8de63fea5f5218d8009f8a6388220ead0f5cf668468a2"
EXPECTED_ARTEFACTS = {
    "KF-RESULT-wp-6537-04.md",
    "fig_review_6537_04.png",
    "review_events.json",
    "review_report.json",
}


def _load_module():
    spec = importlib.util.spec_from_file_location("review_6537_04", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_module()


@pytest.fixture(scope="module")
def report():
    with open(os.path.join(OUT, "review_report.json"), encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def inner(report):
    return report["outputs"]["review_report.json"]


@pytest.fixture(scope="module")
def manifest():
    with open(MANIFEST, encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def md():
    with open(SNAPSHOT, encoding="utf-8") as fh:
        return fh.read()


# ----------------------------------------------------------------- envelope


def test_envelope_identity_and_source_binding(report, inner):
    assert report["package_id"] == "wp-6537-04"
    assert report["task_type"] == "04-independent-review"
    assert report["report_id"] == "6537"
    prov = report["provenance"]
    assert prov["source_hash"] == "sha256:" + CONTRACT_HASH
    assert prov["reviewed_package"] == "wp-6537-01"
    assert prov["reviewed_manifest_sha256"] == REVIEWED_MANIFEST_SHA
    assert inner["reviewed_package"] == "wp-6537-01"
    assert inner["reviewed_report_id"] == "6537"
    assert inner["claims_reviewed_and_marked_verified"] == 0


def test_reviewed_source_bytes_unchanged(md):
    raw = open(SNAPSHOT, "rb").read()
    assert hashlib.sha256(raw).hexdigest() == CONTRACT_HASH
    assert hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == 10530 and len(md.encode("utf-8")) == 15951


def test_upstream_manifest_not_modified():
    """The review must be read-only w.r.t. the artefact it audits."""
    raw = open(MANIFEST, "rb").read()
    assert hashlib.sha256(raw).hexdigest() == REVIEWED_MANIFEST_SHA


# ----------------------------------------------------------------- checks / counts


def test_every_check_has_four_fields_and_a_legal_verdict(inner):
    legal = {"pass", "fail", "unknown", "info"}
    checks = inner["checks"]
    assert len(checks) >= 60
    for c in checks:
        for key in ("id", "group", "assertion", "expected", "actual", "verdict"):
            assert key in c and c[key] != "", (c.get("id"), key)
        assert c["verdict"] in legal, c
    ids = [c["id"] for c in checks]
    assert len(ids) == len(set(ids)), "duplicate check ids"


def test_declared_counts_match_the_check_array(inner):
    checks = inner["checks"]
    counts = inner["counts"]
    assert counts["checks_total"] == len(checks)
    for verdict in ("pass", "fail", "unknown", "info"):
        assert counts["checks_%s" % verdict] == sum(1 for c in checks if c["verdict"] == verdict)
    by_group = {}
    for c in checks:
        g = by_group.setdefault(c["group"], {})
        g[c["verdict"]] = g.get(c["verdict"], 0) + 1
    for group, hist in by_group.items():
        declared = counts["by_group"][group]
        for verdict, n in hist.items():
            assert declared[verdict] == n, (group, verdict)


def test_verdict_follows_from_findings(inner):
    blocking = [f for f in inner["findings"] if f.get("blocking")]
    assert inner["verdict"] == ("needs-fix" if blocking else "pass")
    assert inner["disposition"] == ("request-changes" if blocking else "accept")
    severities = {f["severity"] for f in inner["findings"]}
    assert severities <= {"major", "medium", "minor"}
    assert blocking, "this review claims blocking defects; make the split explicit"


def test_locator_checks_cover_every_registered_asset(inner, manifest):
    covered = {c["id"].split(":", 1)[1] for c in inner["checks"]
               if c["id"].startswith("L:") and "_" not in c["id"].split(":", 1)[1]}
    asset_ids = {a["asset_id"] for a in manifest["assets"]}
    assert asset_ids <= covered, sorted(asset_ids - covered)


# ----------------------------------------------------------------- independent recomputation


def test_upstream_verification_gap_is_reproduced(mod, manifest, md):
    """31 of 37 locators are span-tested; the other 6 are branched out before the test."""
    replay = mod.upstream_verify_predicate(manifest, md)
    assert len(replay["span_tested"]) == 31
    assert sorted(replay["skipped"]) == ["A01", "A02", "A03", "A04", "A05", "A06"]
    assert replay["bad"] == [], "the upstream gate does reproduce as 'all pass'"
    with open(VERIFICATION, encoding="utf-8") as fh:
        v = json.load(fh)
    assert v["all_pass"] is True
    assert "checked 37 locators" in v["checks"]["source_locator_resolvable"]["detail"]


def test_strict_rule_fails_exactly_the_figure_metadata_assets(mod, manifest, md):
    strict = mod.strict_locator_resolution(manifest, md)
    failing = sorted(x["asset_id"] for x in strict if not x.get("ok"))
    assert failing == ["A01", "A02", "A03", "A04", "A05", "A06"]
    figs = [x for x in strict if x["asset_id"].startswith("A0") and x["asset_id"] != "A01"]
    assert len(figs) == 5
    for x in figs:
        assert x["quote_in_markdown"] == 0, x
        assert x["span_len"] == 10530
        assert x["unique_flag"] is True and x["verified_flag"] is True


def test_locator_check_bites_under_mutation(mod, manifest, md):
    """Shift a correct span by one character -> the strict rule must go red."""
    mutated = json.loads(json.dumps(manifest))
    target = next(a for a in mutated["assets"] if a["asset_id"] == "A101")
    target["locator"]["start_char"] += 1
    rows = mod.strict_locator_resolution(mutated, md)
    bad = [x["asset_id"] for x in rows if not x.get("ok")]
    assert "A101" in bad
    # ...and a locator that *does* bracket its quote resolves, i.e. the failure is about the
    # bytes, not about the checker being hard-wired.
    fig = next(a for a in mutated["assets"] if a["asset_id"] == "A02")
    caption = fig["locator"]["quote"]
    patched_md = md + "\n" + caption
    fig["locator"]["start_char"] = len(md) + 1
    fig["locator"]["end_char"] = len(md) + 1 + len(caption)
    rows2 = mod.strict_locator_resolution(mutated, patched_md)
    a02 = next(x for x in rows2 if x["asset_id"] == "A02")
    assert a02["ok"] is True, a02


def test_canonical_schema_errors_are_reproduced(mod, inner):
    with open(MANIFEST, encoding="utf-8") as fh:
        manifest = json.load(fh)
    n, _msgs = mod.schema_errors(manifest)
    if n is None:  # pragma: no cover - jsonschema missing
        pytest.skip("jsonschema not installed")
    assert n == inner["numeric_tables"]["schema_validation"]["errors"] == 72
    baseline = inner["numeric_tables"]["schema_validation"]["peer_baseline"]
    assert baseline["schema_clean"] > 0, "if no peer validates clean, this is repo drift, not a package defect"


def test_report_arithmetic_recomputed_from_markdown(mod, md, inner):
    rows = mod.parse_fuel_table(md)
    assert len(rows) == 12
    by = {r["fuel"]: r for r in rows}
    # TtW of the carbon paths rebuilt with the report's *declared* GWP100_CH4 = 29.8
    gwp, die = 29.8, by["lng_diesel"]
    n2o = (die["ttw"] - die["cf"] * 1000.0 / die["lhv"]
           - die["slip"] / 100.0 * 1000.0 / die["lhv"] * gwp)
    for r in rows:
        if r["cf"] <= 0:
            continue  # zero-carbon paths: TtW is a declared fuel-specific N2O term
        pred = r["cf"] * 1000.0 / r["lhv"] + r["slip"] / 100.0 * 1000.0 / r["lhv"] * gwp + n2o
        assert abs(pred - r["ttw"]) <= 0.10, (r["fuel"], pred, r["ttw"])
    # full-chain crossover where LNG-Otto meets VLSFO (report: 2.30 %)
    ott, vlsfo = by["lng_otto"], by["vlsfo"]
    slip = ((vlsfo["wtw"] - ott["wtt"]) - ott["cf"] * 1000.0 / ott["lhv"] - n2o) \
        / (1000.0 / ott["lhv"] * gwp) * 100.0
    assert abs(slip - 2.30) <= 0.02, slip
    assert inner["numeric_tables"]["slip_crossover"]["claimed_slip_pct"] == 2.30


def test_findings_quotes_resolve_byte_exactly(inner):
    for f in inner["findings"]:
        ev = f["evidence"]
        src_path = os.path.join(ROOT, ev["source_file"])
        with open(src_path, encoding="utf-8") as fh:
            src = fh.read()
        quote = ev["quote_from_source"]
        assert quote in src, (f["id"], ev["source_file"], quote)
        assert src.count(quote) >= 1


def test_offline_recomputation_matches_delivered_checks(mod, inner):
    """Delivery reproducibility: the network-independent groups must be identical."""
    offline = mod.run(live=False)
    stable = {"structure", "locator", "upstream-verify", "schema", "targets", "arithmetic"}
    skip = {"L:figmap"}  # needs record.figures[] from the platform API
    delivered = {c["id"]: c for c in inner["checks"] if c["group"] in stable and c["id"] not in skip}
    recomputed = {c["id"]: c for c in offline["checks"] if c["group"] in stable and c["id"] not in skip}
    assert delivered.keys() == recomputed.keys()
    for cid, c in recomputed.items():
        assert c["verdict"] == delivered[cid]["verdict"], cid


# ----------------------------------------------------------------- artefacts / hygiene


def test_events_log_is_monotonic_and_ends_with_the_verdict():
    with open(os.path.join(OUT, "review_events.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
    events = doc["events"]
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert all(e["event"] and e["target"] and e["result"] for e in events)
    assert events[-1]["event"] == "verdict_assigned"
    assert "needs-fix" in events[-1]["result"]


def test_figure_is_a_real_png_and_is_cited(inner):
    path = os.path.join(OUT, "fig_review_6537_04.png")
    raw = open(path, "rb").read()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(raw) > 20000
    assert inner["figure"].endswith("fig_review_6537_04.png")
    md_text = open(os.path.join(OUT, "KF-RESULT-wp-6537-04.md"), encoding="utf-8").read()
    assert "fig_review_6537_04.png" in md_text
    # exactly one json envelope block, and it parses back to the delivered report
    blocks = re.findall(r"```json\n(.*?)```", md_text, re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0])["package_id"] == "wp-6537-04"


def test_delivery_contains_no_build_junk():
    """The original PR#330 shipped ke/__pycache__/*.pyc; the redone delivery must not."""
    present = set(os.listdir(OUT))
    assert present == EXPECTED_ARTEFACTS, sorted(present)
    for name in present:
        full = os.path.join(OUT, name)
        assert not os.path.isdir(full)
        assert not name.endswith((".pyc", ".pyo"))
    junk = []
    for dirpath, dirnames, filenames in os.walk(OUT):
        if "__pycache__" in dirpath:
            junk.append(dirpath)
        junk.extend(f for f in filenames if f.endswith((".pyc", ".pyo")))
    assert junk == []


def test_figure_locator_checks_are_red_not_green(inner):
    """Guard against a 'fix' that silently flips the finding to green without evidence."""
    red = [c["id"] for c in inner["checks"]
           if c["group"] == "locator" and c["verdict"] == "fail"]
    assert sorted(red) == ["L:A02", "L:A03", "L:A04", "L:A05", "L:A06"]

def test_review_envelope_satisfies_canonical_kf_result_schema(report, inner):
    """F3 says the reviewed manifest declares a schema it does not validate against; the
    review must not repeat that mistake with the shared kf_result.v1 contract."""
    jsonschema = pytest.importorskip("jsonschema")
    with open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"), encoding="utf-8") as fh:
        schema = json.load(fh)
    v = jsonschema.validators.validator_for(schema)(schema)
    assert list(v.iter_errors(report)) == []
    assert inner["envelope_schema_validation"]["errors"] == 0
    # the envelope is delivered in review_report.json and verbatim in the KF-RESULT block;
    # no standalone kf_result.json is committed because that would require regenerating the
    # shared envelope census (docs/kf/wp-459-01/envelope_conformance.json) in this PR.
    assert not os.path.exists(os.path.join(OUT, "kf_result.json"))
