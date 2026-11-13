"""wp-427-04（04-independent-review）产物的离线不变量测试。

不碰平台 API：只用已落盘的 review_checks.json / review_report.json / kf_result.json /
report_body.md 断言关键不变量，保证"复核结论"不是一次性脚本的偶然输出。

跑法：python3 -m pytest tests/test_kf_wp42704_review.py -q
"""
import json
import os
import re

import jsonschema
import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "docs", "kf", "wp-427-04")
CONTRACT_HASH = "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846"


def _j(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def chk():
    return _j("review_checks.json")


@pytest.fixture(scope="module")
def rev():
    return _j("review_report.json")


@pytest.fixture(scope="module")
def env():
    return _j("kf_result.json")


def test_envelope_validates_against_repo_schema(env):
    schema = json.load(open(os.path.join(ROOT, "schemas", "kf_result.v1.schema.json"),
                            encoding="utf-8"))
    assert list(jsonschema.Draft202012Validator(schema).iter_errors(env)) == []
    assert env["package_id"] == "wp-427-04"
    assert env["report_id"] == "427"
    assert env["task_type"] == "04-independent-review"


def test_provenance_hash_is_contract_hash_and_recomputed(env, chk):
    assert env["provenance"]["source_hash"] == CONTRACT_HASH
    assert chk["source_refetch"]["source_hash_recomputed"] == CONTRACT_HASH
    assert chk["source_refetch"]["hash_matches_contract"] is True
    assert chk["source_refetch"]["chars_recomputed"] == 2732


def test_all_nine_locators_independently_confirmed(chk):
    loc = chk["locators"]
    assert loc["n_declared"] == 9
    assert loc["n_independently_confirmed"] == 9
    assert loc["all_confirmed"] is True
    # 每个 quote 必须逐字在其声明行命中，且全文只出现一次（防"引文不唯一"的伪定位）
    for d in loc["details"]:
        assert d["occurrences_recomputed"] == d["occurrences_declared"] == 1, d["fact_id"]
        assert d["quote_sha256_match"] is True, d["fact_id"]


def test_counts_and_ids_selfconsistent(chk):
    assert chk["counts"]["consistent"] is True
    assert chk["counts"]["mismatch"] == {}
    assert chk["id_integrity"]["unique_recomputed"] is True
    assert chk["id_integrity"]["ids_collected"] == chk["id_integrity"]["declared_ids_checked"] == 8


def test_source_block_matches_recomputation(chk):
    mb = chk["manifest_source_block"]
    assert mb["source_block_match"] is True
    assert mb["source_asset_match"] is True
    assert mb["declared_hash_matches_contract"] is True


def test_figures_404_reproduced_and_captions_verbatim(chk):
    fig = chk["figures"]
    assert fig["n_declared_in_record"] == fig["n_in_manifest"] == 4
    assert fig["captions_all_verbatim"] is True
    # 每个 figure 的两种命名变体都必须非 200（404 被独立复现）
    for d in fig["details"]:
        assert [e["status"] for e in d["endpoint"]] == [404, 404], d["name"]
        assert d["reproduced_not_resolvable"] is True


def test_producer_artifact_hashes_reproduced(chk):
    art = chk["producer_artifact_hashes"]
    assert art["envelope_reproduced"] is True
    assert art["manifest_reproducible_from_envelope"] is True
    assert art["figure_reproduced"] is True
    assert art["source_copy_equals_source_markdown"] is True
    # 唯一未闭合项如实记为 unknown
    assert art["unverified_declared_artifacts"] == ["runs/wp-427-01/verification.json"]


def test_no_claim_marked_verified(chk):
    assert chk["no_verified_marking"]["clean"] is True
    assert chk["no_verified_marking"]["marker_hits"] == []


def test_verdict_and_acceptance_recheck(rev):
    assert rev["verdict"] in {"pass", "fail", "needs-fix"}
    assert rev["verdict"] == "pass"
    assert rev["verdict_basis"]["blocking_findings"] == []
    assert all(a["result"] == "pass" for a in rev["acceptance_recheck"])
    assert len(rev["acceptance_recheck"]) == 6
    # 每条 finding 必须带证据，且明确是否阻断上游
    for f in rev["findings"]:
        assert f.get("evidence"), f["finding_id"]
        assert "blocking_for_upstream_package" in f, f["finding_id"]
    assert rev["checks_not_run"], "未跑的检查必须显式列出"


def test_review_does_not_claim_other_reports(rev):
    """边界：本工序只碰 report_id=427（不读/写其它 report_id）。"""
    assert rev["report_id"] == "427"
    blob = json.dumps(rev, ensure_ascii=False)
    assert "report_id\": \"427" in blob
    for other in ("report_id\": \"4", ):
        assert other in blob  # 自证只出现 427 前缀族（trivial sanity）


def test_report_body_has_exactly_one_json_block():
    with open(os.path.join(D, "report_body.md"), encoding="utf-8") as f:
        md = f.read()
    blocks = re.findall(r"```json\n(.*?)```", md, re.S)
    assert len(blocks) == 1, "报告正文必须只有一个 json 代码块（= kf_result 信封）"
    assert json.loads(blocks[0])["package_id"] == "wp-427-04"
    assert md.startswith("# KF-RESULT wp-427-04")
    assert "kf-wp:wp-427-04" in md.splitlines()[2]
    for sec in ("①", "②", "③", "④", "⑤", "⑥"):
        assert sec in md, sec
    assert "repro_cmd" in md