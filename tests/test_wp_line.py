"""Tests for the production-line runner (:mod:`ke.wp_line`).

The runner is the executable side of ``docs/production/PRODUCTION-LINE-v1.md``
§2, so these tests assert *invariants of the line*, not just that functions run:

* the five processes form a DAG and the order in code equals the order in the
  spec (drift between doc and code is a failure);
* a contract of every process validates against the one shared schema;
* a downstream process does not run while its upstream is uncleared;
* 05 synthesis input contains only evidence-bound, independently approved work,
  and refusals carry reason codes instead of silence;
* the fixture benchmark reproduces the reference table of GATE-RULES.md and the
  mutation matrix really reddens the rule it declares.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ke import wp_gate, wp_line  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "extraction"
SPEC_DOC = ROOT / "docs" / "production" / "PRODUCTION-LINE-v1.md"


# ---------------------------------------------------------------------------
# process table
# ---------------------------------------------------------------------------
def test_five_processes_and_spec_order():
    assert len(wp_line.PROCESSES) == 5
    assert wp_line.PROCESS_ORDER == tuple(wp_line.PROCESSES)
    spec = SPEC_DOC.read_text(encoding="utf-8")
    positions = [spec.index(p) for p in wp_line.PROCESS_ORDER]
    assert positions == sorted(positions), "process order in code differs from the spec"


def test_synthesis_declares_every_basic_process_as_dependency():
    deps = set(wp_line.PROCESSES["05-synthesis-research"]["depends_on"])
    assert deps == set(wp_line.PROCESS_ORDER[:-1])


def test_declared_dependencies_precede_their_process():
    for idx, task_type in enumerate(wp_line.PROCESS_ORDER):
        for dep in wp_line.PROCESSES[task_type]["depends_on"]:
            assert task_type != dep
            assert wp_line.PROCESS_ORDER.index(dep) < idx


# ---------------------------------------------------------------------------
# contracts
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("task_type", wp_line.PROCESS_ORDER)
def test_contract_of_every_process_matches_the_shared_schema(task_type):
    contract = wp_line.build_contract(
        task_type, report_id="9001", source_hash="sha256:" + "a" * 64,
        reviewed_package={"package_id": "wp-9001-03", "claims_sha256": "sha256:" + "b" * 64,
                          "evidence_sha256": "sha256:" + "c" * 64}
        if task_type == "04-independent-review" else None,
        upstream_packages=[{"package_id": "wp-9001-01", "status": "completed"},
                           {"package_id": "wp-9001-02", "status": "completed"},
                           {"package_id": "wp-9001-03", "status": "completed"},
                           {"package_id": "wp-9001-04", "status": "completed"}]
        if task_type == "05-synthesis-research" else None,
    )
    assert wp_line.validate_contract(contract) == ""
    assert contract["delivery"]["status"] == "draft"
    assert contract["review"]["independent_reviewer"] is True


def test_unknown_process_is_rejected_not_guessed():
    with pytest.raises(KeyError):
        wp_line.build_contract("06-whatever", report_id="9001",
                               source_hash="sha256:" + "a" * 64)


def test_attachments_require_a_manifest():
    kwargs = dict(report_id="9001", source_hash="sha256:" + "a" * 64)
    with pytest.raises(ValueError):
        wp_line.build_contract("01-asset-registration",
                               attachments=[{"filename": "a.csv", "uri": "file://a.csv",
                                             "sha256": "sha256:" + "d" * 64}], **kwargs)
    contract = wp_line.build_contract(
        "01-asset-registration",
        attachments=[{"filename": "a.csv", "uri": "file://a.csv",
                      "sha256": "sha256:" + "d" * 64}],
        attachments_manifest="file://manifest.json", **kwargs)
    assert wp_line.validate_contract(contract) == ""


def test_package_ids_are_stable_and_schema_shaped():
    a = wp_line.make_package_id("9001", "03-knowledge-extraction")
    b = wp_line.make_package_id("9001", "03-knowledge-extraction")
    assert a == b == "wp-9001-03"
    assert wp_line.make_package_id("Report/42 A", "05-synthesis-research").startswith("wp-")


def test_plan_writes_packages_and_refuses_to_overwrite(tmp_path):
    basic = ("01-asset-registration", "02-classification-parse",
             "03-knowledge-extraction")
    rows = wp_line.plan_report("9001", "sha256:" + "a" * 64, tmp_path, processes=basic)
    assert [r["task_type"] for r in rows] == list(basic)
    for row in rows:
        assert (tmp_path / row["package_id"] / wp_line.CONTRACT_FILE).is_file()
    with pytest.raises(FileExistsError):
        wp_line.plan_report("9001", "sha256:" + "a" * 64, tmp_path, processes=basic)
    wp_line.plan_report("9001", "sha256:" + "a" * 64, tmp_path, processes=basic,
                        overwrite=True)


def test_plan_refuses_review_before_extraction_exists(tmp_path):
    with pytest.raises(ValueError, match="run 03 first"):
        wp_line.plan_report("9001", "sha256:" + "a" * 64, tmp_path,
                            processes=("04-independent-review",))


def test_plan_binds_review_and_synthesis_to_real_digests(tmp_path):
    wp_line.plan_report("9001", "sha256:" + "a" * 64, tmp_path,
                        processes=("03-knowledge-extraction",))
    pkg03 = tmp_path / "wp-9001-03"
    for name in ("claims.json", "evidence.json", "provenance.json",
                 "extraction_summary.json"):
        shutil.copyfile(FIXTURES / "ok-basic" / name, pkg03 / name)
    rows = wp_line.plan_report("9001", "sha256:" + "a" * 64, tmp_path,
                               processes=("04-independent-review",
                                          "05-synthesis-research"))
    review = json.loads((tmp_path / rows[0]["package_id"] / wp_line.CONTRACT_FILE)
                        .read_text(encoding="utf-8"))
    synt = json.loads((tmp_path / rows[1]["package_id"] / wp_line.CONTRACT_FILE)
                      .read_text(encoding="utf-8"))
    assert review["input"]["reviewed_package"]["claims_sha256"] == (
        "sha256:" + __import__("hashlib").sha256(
            (pkg03 / "claims.json").read_bytes()).hexdigest())
    assert [p["status"] for p in synt["input"]["upstream_packages"]] == ["pending"] * 4


# ---------------------------------------------------------------------------
# spine gate (processes without the 03 rule set)
# ---------------------------------------------------------------------------
def _register_one(tmp_path: Path, report_id: str = "9001") -> Path:
    resolver = wp_gate.DirSourceResolver(FIXTURES / "sources")
    wp_line.register_assets([report_id], resolver, tmp_path / "reg")
    return tmp_path / "reg" / wp_line.make_package_id(report_id, "01-asset-registration")


def test_spine_gate_passes_a_registered_asset(tmp_path):
    pkg = _register_one(tmp_path)
    contract = next(c for c in wp_line.discover(pkg))
    gate = wp_line.spine_gate(contract)
    assert gate["pass"] is True
    manifest = json.loads((pkg / "asset_manifest.json").read_text(encoding="utf-8"))
    declared = json.loads((pkg / wp_line.CONTRACT_FILE).read_text(encoding="utf-8"))
    assert manifest["source_hash"] == declared["input"]["source_hash"]
    assert manifest["length_chars"] == len((FIXTURES / "sources" / "9001.md")
                                           .read_text(encoding="utf-8"))


def test_spine_gate_reddens_a_missing_artifact(tmp_path):
    pkg = _register_one(tmp_path)
    (pkg / "asset_manifest.json").unlink()
    gate = wp_line.spine_gate(next(c for c in wp_line.discover(pkg)))
    assert gate["pass"] is False
    assert "P3.declared_artifacts" in {c["name"] for c in gate["checks"] if not c["ok"]}


def test_unreachable_source_is_recorded_not_skipped(tmp_path):
    out = wp_line.register_assets(["9001", "9999"],
                                  wp_gate.DirSourceResolver(FIXTURES / "sources"),
                                  tmp_path / "reg")
    assert out["n_reports"] == 2
    assert out["n_reachable"] == 1 and out["n_unreachable"] == 1
    bad = next(r for r in out["reports"] if r["report_id"] == "9999")
    assert bad["reachable"] is False and "error" in bad


# ---------------------------------------------------------------------------
# the line: ordering + gate binding
# ---------------------------------------------------------------------------
def _run_fixtures(root: Path) -> dict:
    return wp_line.run_line(root, resolver=wp_gate.DirSourceResolver(root / "sources"),
                            review_ledger_dir=root / "ledgers",
                            tickets_dir=root / "tickets",
                            prompts_dir=wp_line.PROMPTS_DIR)


def test_line_reproduces_the_declared_fixture_verdicts():
    report = _run_fixtures(FIXTURES)
    rows = {c.package_dir.name: r for c in wp_line.discover(FIXTURES)
            for proc in report["processes"] for r in proc["packages"]
            if r["package_id"] == c.package_id}
    refs = wp_line.parse_reference_table()
    assert set(refs) == set(rows), "fixture set and reference table diverged"
    for name, ref in refs.items():
        assert rows[name]["verdict"] == ref["verdict"], name
        assert rows[name]["level"] == ref["level"], name
        assert set(ref["rules"]) <= set(rows[name]["failed_rules"]), name


def test_line_does_not_run_a_downstream_package_on_a_failed_upstream(tmp_path):
    root = tmp_path / "extraction"
    shutil.copytree(FIXTURES, root)
    claims = json.loads((root / "ok-basic" / "claims.json").read_text(encoding="utf-8"))
    claims[0]["evidence_refs"] = []
    (root / "ok-basic" / "claims.json").write_text(json.dumps(claims), encoding="utf-8")
    # a review package that declares ok-basic as its reviewed upstream
    contract = wp_line.build_contract(
        "04-independent-review", report_id="9001", source_hash="sha256:" + "a" * 64,
        reviewed_package={"package_id": "wp-ok-basic", "claims_sha256": "sha256:" + "b" * 64,
                          "evidence_sha256": "sha256:" + "c" * 64})
    wp_line.plan_package(contract, root)

    report = _run_fixtures(root)
    review = next(p for p in report["processes"]
                  if p["task_type"] == "04-independent-review")
    assert review["n_blocked_upstream"] == 1
    assert review["packages"][0]["blocked_on"] == ["03-knowledge-extraction"]
    assert report["base_processing_complete"] is False


def test_line_reports_synthesis_blocked_on_incomplete_base():
    report = _run_fixtures(FIXTURES)
    assert report["base_processing_complete"] is False
    assert report["synthesis_unblocked"] is False


# ---------------------------------------------------------------------------
# synthesis input
# ---------------------------------------------------------------------------
def _ok_subset(tmp_path: Path) -> Path:
    root = tmp_path / "ok-subset"
    root.mkdir()
    for name in ("ok-basic", "ok-verified", "ok-zero-claim"):
        shutil.copytree(FIXTURES / name, root / name)
    for sub in ("sources", "ledgers", "tickets"):
        shutil.copytree(FIXTURES / sub, root / sub)
    return root


def test_synthesis_admits_only_evidence_bound_approved_packages(tmp_path):
    root = _ok_subset(tmp_path)
    bundle = wp_line.assemble_synthesis_input(root, _run_fixtures(root))
    assert bundle["ready"] is True
    assert {p["package_id"] for p in bundle["eligible_packages"]} == {"wp-ok-basic",
                                                                     "wp-ok-verified"}
    refused = {r["package_id"]: r["code"] for r in bundle["refusals"]}
    assert refused == {"wp-ok-zero-claim": "NOT_EVIDENCE_BOUND"}
    assert bundle["n_claims"] == sum(p["n_claims"] for p in bundle["eligible_packages"])


def test_synthesis_flags_cross_package_duplicates_without_merging(tmp_path):
    root = _ok_subset(tmp_path)
    bundle = wp_line.assemble_synthesis_input(root, _run_fixtures(root))
    assert bundle["n_duplicate_candidates"] > 0
    # nothing was dropped or merged: every claim is still in the bundle
    assert bundle["n_claims"] == sum(p["n_claims"] for p in bundle["eligible_packages"])
    for dup in bundle["duplicates"]:
        assert dup["similarity"] >= 0.9
        assert len(set(dup["packages"])) == 2


def test_synthesis_refuses_when_the_base_is_incomplete():
    bundle = wp_line.assemble_synthesis_input(FIXTURES, _run_fixtures(FIXTURES))
    assert bundle["ready"] is False
    assert bundle["blocked_reason"] == "UPSTREAM_INCOMPLETE"
    assert all(r["code"] in wp_line.REFUSAL_CODES for r in bundle["refusals"])


def test_synthesis_refuses_a_gate_failed_package():
    bundle = wp_line.assemble_synthesis_input(FIXTURES, _run_fixtures(FIXTURES))
    refused = {r["package_id"]: r["code"] for r in bundle["refusals"]}
    assert refused["wp-bad-source-hash"] == "GATE_FAILED"
    assert "wp-bad-source-hash" not in {p["package_id"]
                                        for p in bundle["eligible_packages"]}


# ---------------------------------------------------------------------------
# benchmark: reference table + mutation matrix
# ---------------------------------------------------------------------------
def test_reference_table_parses_the_ditto_rows():
    refs = wp_line.parse_reference_table()
    assert len(refs) == 8
    assert refs["ok-verified"]["verdict"] == "PASS_PROGRAMMATIC_PENDING_REVIEW"
    assert refs["bad-source-hash"]["rules"] == ["E2"]
    assert refs["bad-self-review"]["level"] == "L0"


def test_benchmark_meets_its_predeclared_thresholds():
    bench = wp_line.run_benchmark()
    assert bench["pass"] is True, bench["below_threshold"]
    assert bench["metrics"]["verdict_agreement"] == 1.0
    assert bench["metrics"]["rule_agreement"] == 1.0
    assert bench["metrics"]["mutation_detection"] == 1.0
    assert bench["rules"]["uncovered"] == []


def test_one_mutation_reddens_exactly_the_declared_rule():
    mutation = next(m for m in wp_line.MUTATIONS if m.name.startswith("m02-"))
    row = wp_line.run_mutation(mutation)
    assert row["detected"] is True
    assert row["verdict_changed"] is True
    assert row["got_rules"] == ["E2"]


def test_rule_coverage_counts_only_rules_the_gate_actually_implements():
    rules = wp_line.implemented_rules()
    assert {"S1", "E2", "M4"} <= set(rules)
    assert all(name.startswith(rule + ".") for rule, names in rules.items()
               for name in names)


# ---------------------------------------------------------------------------
# CLI surfaces
# ---------------------------------------------------------------------------
def test_cli_bench_writes_a_report(tmp_path):
    dest = tmp_path / "bench.json"
    assert wp_line.main(["bench", "--json", str(dest)]) == 0
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["pass"] is True and payload["n_fixtures"] == 8


def test_cli_run_exits_non_zero_when_a_package_fails(tmp_path):
    dest = tmp_path / "line.json"
    code = wp_line.main(["run", "--root", str(FIXTURES),
                         "--sources", str(FIXTURES / "sources"),
                         "--review-ledger-dir", str(FIXTURES / "ledgers"),
                         "--tickets-dir", str(FIXTURES / "tickets"),
                         "--json", str(dest)])
    assert code == 2
    payload = json.loads(dest.read_text(encoding="utf-8"))
    assert payload["n_packages"] == 8


def test_cli_plan_rejects_an_unknown_process(tmp_path):
    code = wp_line.main(["plan", "--report", "9001", "--source-hash",
                         "sha256:" + "a" * 64, "--out", str(tmp_path),
                         "--processes", "07-nonsense"])
    assert code == 2
    assert not list(tmp_path.glob("*/work-package.json"))


def test_platform_wrapper_exposes_the_same_entry():
    wrapper = ROOT / "scripts" / "run_wp_line.py"
    assert wrapper.is_file()
    assert "from ke.wp_line import main" in wrapper.read_text(encoding="utf-8")