"""wp-895-04（04-independent-review，对象 report 895 / 上游 wp-895-01）交付物不变量测试。

这些测试只验证「本审核包自证」的不变量，不重跑上游物理：
  1. 源快照 sha256 与工作包契约 source_hash 一致；
  2. 上游包 7/7 artifact locator 在原文中逐字可定位；
  3. 上游信封过 kf_result.v1 schema；
  4. 三个 JSON 产物无自封验证字段名（审核者不写 verification）；
  5. 审核 finding 里每条引文在原文中逐字存在；
  6. review_events.json 折叠为 approved 且审核者身份独立；
  7. 复算锚点（ω、Hankel w(0)、刚体封闭解、kei 零环）与报告值相符；
  8. 文本报告的 json 代码块唯一且可解析。

上游活工作树不可达时，用本包快照 runs/wp-895-04/upstream_wp-895-01_result.json。
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import sys

import jsonschema
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ke_state_machine as sm  # noqa: E402

RUNS = ROOT / "runs/wp-895-04"
WORK = ROOT / "work/wp-895-04"
SOURCE = RUNS / "source_report_895.md"
UPSTREAM = RUNS / "upstream_wp-895-01_result.json"
CONTRACT_HASH = "sha256:31f6794efa547c7dc66c6b9d84edd509c977b7e1ffdf138023d880edbf166b39"
FORBIDDEN = ("verified", "verification_status", "verification_level", "is_verified",
             "gate_confirmed")


def _md() -> str:
    return SOURCE.read_text(encoding="utf-8")


def _load(p: pathlib.Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_required_artifacts_exist():
    for p in (SOURCE, UPSTREAM, RUNS / "audit.json",
              WORK / "review_report.json", WORK / "review_events.json",
              WORK / "kf_result.wp-895-04.json"):
        assert p.is_file(), p


def test_source_hash_and_chars_match_contract():
    md = _md()
    assert "sha256:" + hashlib.sha256(md.encode("utf-8")).hexdigest() == CONTRACT_HASH
    assert len(md) == 9459


def test_upstream_locators_resolve_verbatim():
    md = _md()
    am = _load(UPSTREAM)["outputs"]["asset_manifest.json"]
    arts = am["artifacts"]
    assert len(arts) == 7
    missing = [a["name"] for a in arts if a["locator"] not in md]
    assert not missing, missing


def test_upstream_envelope_schema():
    schema = _load(ROOT / "schemas/kf_result.v1.schema.json")
    jsonschema.Draft202012Validator(schema).validate(_load(UPSTREAM))


def test_products_carry_no_self_seal_fields():
    for p in (WORK / "review_report.json", WORK / "review_events.json",
              WORK / "kf_result.wp-895-04.json"):
        blob = p.read_text(encoding="utf-8").lower()
        hits = {w: blob.count(w) for w in FORBIDDEN if w in blob}
        assert not hits, (p.name, hits)


def test_finding_quotes_are_verbatim_in_source():
    md = _md()
    review = _load(WORK / "review_report.json")
    assert review["findings"], "至少要有一条 finding 或显式说明零发现"
    for f in review["findings"]:
        for e in f["evidence"]:
            assert e["quote"] in md, (f["id"], e["quote"][:40])
            assert e["offset"] == md.find(e["quote"])
            assert e["source_hash"] == CONTRACT_HASH


def test_review_ledger_folds_to_approved_and_is_independent():
    events = _load(WORK / "review_events.json")
    upstream = _load(UPSTREAM)
    ctx = {"producer_ids": [upstream["provenance"]["producer"]]}
    for e in events:
        jsonschema.Draft202012Validator(
            _load(ROOT / "schemas/review-event.schema.json")).validate(e)
    state, codes = sm.fold(events, ctx, initial_state="in-review")
    assert state == "approved" and codes == ["OK_APPROVED"]
    ok, basis = sm.is_independent(events[0]["reviewer"], sm.producer_identity(ctx))
    assert ok and basis == "distinct-identity"


def test_recomputed_anchors_match_report():
    checks = {c["quantity"]: c for c in
              _load(RUNS / "audit.json")["physics"]["checks"]}
    for q in ("ω(k=2π/105.0256, h=1.0)", "c_p = ω/k",
              "w(0) 高斯斑 σ=4 m（独立 Hankel 求积）", "w(0) 点载极限 Pℓ_c²/8D",
              "零环半径 = kei 首零点·ℓ_c", "刚体封闭解 F_peak",
              "峰值压碎面积 A", "能量账闭合 压碎+板+阻尼", "最小相速度 c_min"):
        assert checks[q]["rel_err_pct"] < 1.0, (q, checks[q]["rel_err_pct"])
    # 已知的两项源报告缺陷：必须仍在册（防"修好不更新"或"悄悄抹掉"）
    assert checks["断裂触发时刻 t_c（首个超阈采样点）"]["rel_err_pct"] > 30
    assert 1.0 < checks["断裂触发瞬间 F vs δ 口径一致"]["rel_err_pct"] < 5


def test_text_report_has_single_parseable_json_block():
    md = (WORK / "KF-RESULT-wp-895-04.md").read_text(encoding="utf-8")
    assert md.count("```json") == 1
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    envelope = json.loads(blocks[0])
    assert envelope["package_id"] == "wp-895-04"
    assert envelope["provenance"]["source_hash"] == CONTRACT_HASH
    jsonschema.Draft202012Validator(
        _load(ROOT / "schemas/kf_result.v1.schema.json")).validate(envelope)


def test_verdict_is_declared_and_not_a_verification_claim():
    review = _load(WORK / "review_report.json")
    assert review["verdict"] in ("pass", "needs-fix", "fail")
    assert review["disposition"] == "approve-with-notes"
    # 审核者不得替平台门计算 verification：包里不得有 verification_level 之类字段
    assert "verification_level" not in json.dumps(review)