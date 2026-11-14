"""wp-5624-04 回归：审核报告必须能被独立复算，且每条结论都绑定到可重放的证据。

设计原则：
- 只读已提交的输入（报告正文快照 + 上游 docs/ 镜像），不依赖被 .gitignore 排除的 artifacts/；
- 每个断言都从原始字节重算，而不是相信 review_report.json 里的字符串；
- 需要平台的用例标 needs_api：无凭据时 skip（不等于通过）；
- 确定性：同一输入两次生成必须字节一致。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
from pathlib import Path

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[2]
PKG = "wp-5624-04"
REVIEWED = "wp-5624-01"
OUT = ROOT / "docs" / "kf" / PKG
UPSTREAM = ROOT / "docs" / "kf" / REVIEWED
FIXTURE = ROOT / "tests" / "fixtures" / "kf" / "5624_markdown.md"
CONTRACT_HASH = "sha256:15b2f982058ab3d45a1177e94f1b8140660cd0aaff3c645b3f22de33a0bd7839"
ALLOWED_OUTPUTS = {
    "review_report.json",
    "kf_result.json",
    "kf_result_wp-5624-04.md",
    "fig_review_evidence.png",
}

needs_api = pytest.mark.skipif(
    not all(os.environ.get(k) for k in ("TENSOR_API_BASE", "TENSOR_AGENT_USER", "TENSOR_AGENT_PASS")),
    reason="无平台凭据，联网核验未执行（不是通过）",
)


def _load_reviewer():
    spec = importlib.util.spec_from_file_location(
        "review_wp_5624_01", ROOT / "scripts" / "kf" / PKG / "review_wp_5624_01.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def md() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def review() -> dict:
    return json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def envelope() -> dict:
    return json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def manifest() -> dict:
    return json.loads((UPSTREAM / "asset_manifest.json").read_text(encoding="utf-8"))


def _check(review: dict, cid: str) -> dict:
    return next(c for c in review["checks"] if c["id"] == cid)


def _finding(review: dict, fid: str) -> dict:
    return next(f for f in review["findings"] if f["id"] == fid)


# --------------------------------------------------------------------------- #
# 1. 信封
# --------------------------------------------------------------------------- #
def test_envelope_is_schema_valid(envelope: dict) -> None:
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(envelope, schema)
    assert envelope["package_id"] == PKG
    assert envelope["task_type"] == "04-independent-review"
    assert envelope["report_id"] == "5624"
    assert envelope["claims"] == []


def test_reviewed_package_and_report_are_pinned(review: dict, manifest: dict) -> None:
    assert review["reviewed_package"] == REVIEWED
    assert review["reviewed_report_id"] == manifest["source_asset"]["platform_record_id"].__str__()
    # 被审产物必须按内容哈希固定，不能只按路径引用
    for name, digest in review["reviewed_artifacts"].items():
        assert (UPSTREAM / name).is_file()
        actual = "sha256:" + hashlib.sha256((UPSTREAM / name).read_bytes()).hexdigest()
        assert digest == actual, f"{name} 哈希漂移：报告里是 {digest}，磁盘是 {actual}"


# --------------------------------------------------------------------------- #
# 2. 源哈希与规模：从字节重算，不信报告里的字符串
# --------------------------------------------------------------------------- #
def test_source_hash_rederived_from_bytes(review: dict, envelope: dict, md: str, manifest: dict) -> None:
    recomputed = "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert recomputed == CONTRACT_HASH
    assert review["source"]["recomputed_hash"] == recomputed
    assert envelope["provenance"]["source_hash"] == recomputed
    assert manifest["source_asset"]["hash"]["value"] == recomputed
    assert review["source"]["matches_contract"] is True


def test_source_size_rederived(review: dict, md: str, manifest: dict) -> None:
    assert len(md) == manifest["source_asset"]["size"]["chars"] == review["source"]["chars"]
    assert len(md.encode()) == manifest["source_asset"]["size"]["bytes_utf8"] == review["source"]["bytes_utf8"]


@needs_api
def test_snapshot_equals_live_platform_record(md: str) -> None:
    live = _load_reviewer().fetch_source()
    assert "sha256:" + hashlib.sha256(live.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert live == md


# --------------------------------------------------------------------------- #
# 3. 检查项必须真跑过（不是把结论抄进 JSON）
# --------------------------------------------------------------------------- #
def test_sections_are_independently_resplit(md: str, manifest: dict, review: dict) -> None:
    mine = _load_reviewer().split_sections(md)
    theirs = manifest["sections"]
    assert len(mine) == len(theirs) == 7
    for a, b in zip(mine, theirs):
        assert (a["chars"], a["sha256"], a["line_start"], a["line_end"]) == (
            b["chars"],
            b["sha256"],
            b["line_start"],
            b["line_end"],
        )
    assert _check(review, "C05")["result"] == "pass"
    assert review["method"]["sections_recomputed"] == 7


def test_locator_table_covers_every_locator(review: dict, md: str, manifest: dict) -> None:
    rows = review["method"]["locators"]["items"]
    assert len(rows) == manifest["locator_check"]["total"] == review["method"]["locators"]["total"]
    assert review["method"]["locators"]["resolved"] == manifest["locator_check"]["total"]
    md_rows = [r for r in rows if r["space"] == "markdown"]
    assert md_rows, "至少要有 markdown 空间的 locator"
    for r in md_rows:
        assert r["occurrences"] >= 1, f"{r['id']} 在正文里找不到"
    assert _check(review, "C06")["result"] == "pass"


def test_duplicate_locator_finding_is_reproducible(review: dict, md: str, manifest: dict) -> None:
    quotes = [r["locator_quote"] for r in manifest["referenced_artifacts"]]
    dupes = {q for q in quotes if quotes.count(q) > 1}
    assert dupes, "上游清单里应仍存在重复 locator_quote（F-C07 的前提）"
    quote = dupes.pop()
    assert md.count(quote) == 1, "重复引用的 quote 在正文里只出现一次"
    finding = _finding(review, "F-C07")
    groups = finding["evidence"]["duplicate_groups"]
    assert list(groups.values())[0] == ["referenced_artifacts:5624-ref-01", "referenced_artifacts:5624-ref-02"]
    assert _check(review, "C07")["result"] == "fail", "命中去重缺陷时 C07 必须如实为 fail"


def test_line_count_convention(md: str, manifest: dict, review: dict) -> None:
    declared = manifest["source_asset"]["size"]["lines"]
    assert declared == md.count("\n") == len(md.splitlines())
    assert md.split("\n")[-1] == "", "末尾换行是朴素切分多出一行的原因"
    assert _check(review, "C04")["result"] == "pass"
    assert _finding(review, "F-C04")["status"] == "closed_no_defect", "复算后判为无缺陷，须显式关闭而不是留作缺陷"


# --------------------------------------------------------------------------- #
# 4. 可复现性缺陷的 A/B 证据（上一轮审核只给了文字，本轮要求两条臂都在）
# --------------------------------------------------------------------------- #
def test_upstream_suite_has_no_gitignored_dependency() -> None:
    src = (ROOT / "tests" / "kf" / "test_wp_5624_01.py").read_text(encoding="utf-8")
    assert 'DOCS_OUT = ROOT / "docs" / "kf" / PKG' in src, "fixture 必须有 docs/ 镜像回退"
    assert (UPSTREAM / "kf_result.json").is_file(), "回退目标必须已提交"
    # 该路径被 gitignore 才有回退的意义
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "artifacts/" in gitignore


def test_ab_evidence_is_recorded(review: dict) -> None:
    finding = _finding(review, "F-C13")
    ev = finding["evidence"]
    before, after = ev["before_fix"], ev["after_fix"]
    assert ev["ab_experiment"]
    assert before["returncode"] != 0 and before["errors"] > 0, "对照臂必须复现缺陷"
    assert after["returncode"] == 0 and after["errors"] == 0, "修复臂必须在无 artifacts/ 的检出中通过"
    assert after["artifacts_tree_present"] is False
    assert finding["severity"] == "major" and finding["status"] == "fixed_in_this_package"
    assert _check(review, "C15")["result"] == "pass"


# --------------------------------------------------------------------------- #
# 5. 结论与诚实性
# --------------------------------------------------------------------------- #
def test_disposition_matches_findings(review: dict) -> None:
    sev = {f["severity"] for f in review["findings"]}
    if sev & {"critical", "blocking"}:
        assert review["disposition"] == "request_changes"
    else:
        assert review["disposition"] in {"approve", "approve_with_notes"}
        if sev - {"info"}:
            assert review["disposition"] == "approve_with_notes", "存在非 info 缺陷时不能是无条件 approve"


def test_checks_not_run_are_declared(review: dict) -> None:
    assert review["checks_not_run"], "跨 worktree / 无载荷的项必须如实登记为未跑"
    for item in review["checks_not_run"]:
        assert len(item.strip()) > 10, f"未跑项缺少可读理由：{item!r}"
    assert review["independence_limitations"]


def test_no_self_declared_verified(envelope: dict) -> None:
    def exact(obj, needle):
        if isinstance(obj, dict):
            return any(exact(v, needle) for v in obj.values())
        if isinstance(obj, list):
            return any(exact(v, needle) for v in obj)
        return obj == needle

    assert not exact(envelope["outputs"], "verified")
    assert "verification_status" not in envelope


def test_outputs_directory_is_clean() -> None:
    present = {p.name for p in OUT.iterdir()}
    assert present == ALLOWED_OUTPUTS, f"多余/缺失产物：{present ^ ALLOWED_OUTPUTS}"
    assert not any(p.suffix == ".pyc" for p in OUT.iterdir())


# --------------------------------------------------------------------------- #
# 6. 确定性：同一输入两次生成，字节一致
# --------------------------------------------------------------------------- #
def test_generation_is_deterministic(tmp_path: Path, review: dict) -> None:
    mod = _load_reviewer()
    a, b = tmp_path / "a", tmp_path / "b"
    assert mod.main(["--out", str(a)]) == 0
    assert mod.main(["--out", str(b)]) == 0
    assert (a / "review_report.json").read_bytes() == (b / "review_report.json").read_bytes()
    assert (a / "kf_result.json").read_bytes() == (b / "kf_result.json").read_bytes()
    # 离线重生成 = 已提交报告去掉联网/重放专属检查项后的同一份
    offline = json.loads((a / "review_report.json").read_text(encoding="utf-8"))
    only_when_flagged = {"C02", "C13", "C15"}  # --fetch / --fresh-clone 才有的检查项
    assert {c["id"] for c in offline["checks"]} == {c["id"] for c in review["checks"]} - only_when_flagged
    assert offline["source"] == review["source"]
    assert offline["reviewed_artifacts"] == review["reviewed_artifacts"]
    committed_findings = {f["id"]: f.get("status") for f in review["findings"] if f["id"] != "F-C13"}
    assert {f["id"]: f.get("status") for f in offline["findings"]} == committed_findings


def test_report_markdown_matches_json() -> None:
    """md 报告里的数字必须来自 JSON（程序化注入），不出现手抄漂移。"""
    text = (OUT / "kf_result_wp-5624-04.md").read_text(encoding="utf-8")
    review = json.loads((OUT / "review_report.json").read_text(encoding="utf-8"))
    assert review["source"]["recomputed_hash"] in text
    assert f"{review['checks_passed']}/{review['checks_total']}" in text
    assert review["disposition"] in text
    for f in review["findings"]:
        assert f["id"] in text