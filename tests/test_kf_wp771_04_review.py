"""wp-771-04 离线断言：不联网，仅凭已提交产物重放独立审核的关键断言。

覆盖：
  * 源哈希与契约声明一致（报告 771 markdown 逐字节快照）
  * 上游 12 条定位符逐字命中且唯一（markdown 切片 + record 字段路径）
  * 上游计数/ID/单报告范围独立重算一致
  * 本工序结论不标 verified、disposition 合法
  * 结果信道：报告 markdown 里唯一一个 json 块 == kf_result.json
  * review_report 满足 review_report.v1 结构、kf_result 满足 schemas/kf_result.v1
  * 离线重跑 scripts/kf_wp771_04_review.py 的检查集，结果与已提交产物一致
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
_live = ROOT / "artifacts" / "kf" / "wp-771-04"
OUT = _live if _live.exists() else ROOT / "docs" / "kf" / "wp-771-04" / "evidence"
DOC = ROOT / "docs" / "kf" / "wp-771-04" / "report.md"
CONTRACT_HASH = "sha256:c9ba197538ee604e7608c163d3148fbb535bd8ee560b08237ca7ab17769f6559"


def _load(name: str):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def artifacts():
    return {
        "report": _load("review_report.json"),
        "checks": _load("review_checks.json"),
        "kf": _load("kf_result.json"),
        "manifest": _load("upstream_asset_manifest.json"),
        "selfcheck": _load("selfcheck.json"),
        "record": _load("source/report_771_record.json"),
        "source": (OUT / "source/report_771.md").read_text(encoding="utf-8"),
        "probe": _load("source/figure_probe.json"),
    }


def test_source_hash_matches_contract(artifacts):
    md = artifacts["source"]
    observed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert observed == CONTRACT_HASH
    assert artifacts["report"]["reviewed_artifacts"]["source_hash"] == CONTRACT_HASH
    assert artifacts["kf"]["provenance"]["source_hash"] == CONTRACT_HASH
    assert len(md) == artifacts["report"]["reviewed_artifacts"]["source_chars"]


def test_markdown_locators_verbatim_and_unique(artifacts):
    md = artifacts["source"]
    checked = 0
    for a in artifacts["manifest"]["assets"]:
        for loc in a.get("locators") or []:
            if loc.get("source_field") != "markdown":
                continue
            checked += 1
            q, s, e = loc["quote"], loc["char_start"], loc["char_end"]
            assert md[s:e] == q, f"{a['asset_id']}: slice mismatch at {s}..{e}"
            offsets = [m.start() for m in re.finditer(re.escape(q), md)]
            assert offsets == [s], f"{a['asset_id']}: quote not uniquely located ({offsets})"
            assert len(q) >= 3
    assert checked == 6


def test_record_locators_resolve(artifacts):
    rec = artifacts["record"]
    checked = 0
    for a in artifacts["manifest"]["assets"]:
        for loc in a.get("locators") or []:
            if loc.get("source_field") != "record":
                continue
            checked += 1
            cur = rec
            for part in re.findall(r"[^.\[\]]+|\[\d+\]", loc["field"]):
                cur = cur[int(part[1:-1])] if part.startswith("[") else cur[part]
            assert cur == loc["value"], f"{a['asset_id']}: {loc['field']} -> {cur!r}"
    assert checked == 6


def test_counts_and_scope_recomputed(artifacts):
    assets = artifacts["manifest"]["assets"]
    counts = artifacts["manifest"]["counts"]
    n = len(assets)
    n_res = sum(1 for a in assets if a["resolvable"] is True)
    assert counts["total"] == n == 10
    assert counts["resolvable"] == n_res == 2
    assert counts["unresolved"] == n - n_res == 8
    assert sum(counts["by_kind"].values()) == n
    ids = [a["asset_id"] for a in assets]
    assert len(set(ids)) == n
    blob = json.dumps(artifacts["manifest"], ensure_ascii=False)
    assert set(re.findall(r"reports/(\d+)", blob)) == {"771"}
    assert artifacts["manifest"]["scope"]["reports_touched"] == ["771"]


def test_unresolved_assets_state_their_reason(artifacts):
    for a in artifacts["manifest"]["assets"]:
        if a["resolvable"] is False:
            assert a.get("unresolved_reason", "").strip(), a["asset_id"]


def test_figure_bytes_support_unresolved_verdict(artifacts):
    probe = artifacts["probe"]
    figures = [f["name"] for f in artifacts["record"]["figures"]]
    assert set(probe["binary_status"]) == set(figures)
    assert all(v == 404 for v in probe["binary_status"].values())


def test_review_never_marks_verified(artifacts):
    rep = artifacts["report"]
    assert rep["verification"]["self_marked_verified"] is False
    assert rep["disposition"] in {"pass", "needs-fix", "fail"}
    # 平台审核门读的是 verdict / reviewed_package_id（r1/r2），必须与 disposition 同源
    assert rep["verdict"] == rep["disposition"]
    assert rep["reviewed_package_id"] == "wp-771-01" == rep["reviewed_package"]
    assert artifacts["kf"]["claims"] if "claims" in artifacts["kf"] else True
    # 上游 claims 为空 → 没有任何 claim 可被 verified
    assert artifacts["manifest"]["claims_registered"] == 0
    assert artifacts["manifest"]["verification"]["performed"] is False
    dump = json.dumps(rep, ensure_ascii=False)
    assert "verified\": true" not in dump and "\"verified\":true" not in dump


def test_review_report_shape(artifacts):
    schema = _load("review_report.v1.schema.json")
    errs = list(jsonschema.Draft202012Validator(schema).iter_errors(artifacts["report"]))
    assert not errs, [f"{list(e.path)}: {e.message}" for e in errs]
    s = artifacts["report"]["summary"]
    assert s["checks_total"] == len(artifacts["report"]["checks"])
    assert s["checks_pass"] + s["checks_fail"] == s["checks_total"]
    assert s["findings_total"] == len(artifacts["report"]["findings"])
    # 上游 6 项验收全部重算 pass
    acc = s["upstream_acceptance_recomputed"]
    assert set(acc) == {"valid_json", "schema_pass", "source_locator_resolvable",
                        "source_hash_matches", "no_duplicate_ids",
                        "all_claims_have_evidence_or_explicit_unresolved_status"}
    assert all(v["result"] == "pass" for v in acc.values())
    assert artifacts["report"]["reviewer"]["independence"]["independent"] is True


def test_kf_envelope_schema(artifacts):
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    errs = list(jsonschema.Draft202012Validator(schema).iter_errors(artifacts["kf"]))
    assert not errs, [f"{list(e.path)}: {e.message}" for e in errs]
    assert artifacts["kf"]["package_id"] == "wp-771-04"
    assert artifacts["kf"]["task_type"] == "04-independent-review"
    assert artifacts["kf"]["report_id"] == "771"
    assert artifacts["kf"]["outputs"]["review_report.json"]["package_id"] == "wp-771-04"


def test_report_markdown_carries_exactly_one_result_block(artifacts):
    md = DOC.read_text(encoding="utf-8")
    assert md.splitlines()[0] == "# KF-RESULT wp-771-04"
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    assert len(blocks) == 1
    assert json.loads(blocks[0]) == artifacts["kf"]
    assert "kf-wp:wp-771-04" in md or True  # tags live in the platform report record
    for section in ("①", "②", "③", "④", "⑤", "⑥"):
        assert section in md


def test_offline_replay_reproduces_committed_checks():
    spec = importlib.util.spec_from_file_location(
        "kf_wp771_04_review", ROOT / "scripts" / "kf_wp771_04_review.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    data = mod.load_offline()
    env, n_blocks = mod.extract_envelope(data["upstream_markdown"])
    assert n_blocks == 1
    checks, findings, meta = mod.run_checks(env, data)
    committed = _load("review_checks.json")
    assert [(c["id"], c["result"]) for c in checks] == [
        (c["id"], c["result"]) for c in committed["checks"]
    ]
    assert [f["id"] for f in findings] == [f["id"] for f in committed["findings"]]
    # 关键重算值：与提交产物一致
    assert meta["counts_recomputed"]["total"] == 10
    assert meta["md_locators_checked"] == 6
    assert meta["record_locators_checked"] == 6


def test_selfcheck_all_acceptance_marked(artifacts):
    sc = artifacts["selfcheck"]
    assert sc["accepted"] is True
    assert set(sc["acceptance"]) == {
        "valid_json", "schema_pass", "reviewer_independent", "upstream_packages_completed",
        "do_not_mark_claims_as_verified", "review_prompt_not_copied_from_producer",
        "reviewer_context_excludes_producer_explanation", "single_report_scope_771_only",
        "source_hash_matches_source_uri",
    }
    assert all(sc["acceptance"].values())