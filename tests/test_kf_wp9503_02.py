"""wp-9503-02（report 9503 分类解析）离线验收测试。

不联网：用包内 `source/report_9503.md` 快照复算，验证
① 快照哈希 = 契约 source_hash；② kf_result 过 schema 硬约束；
③ 分类结果可确定性复算（primary/排序/定位数与提交件一致）；
④ 每条定位在原文可解析（md[start:end]==quote 且 sha256 一致）；
⑤ id 唯一；⑥ 主题标签与 unresolved 账目一致；
⑦ 报告 md 只有一个 json 块且与 kf_result.json 逐字节等价；
⑧ 未把结论标成 verified；
⑨ 定位校验器本身有牙（篡改引文必须被抓住）。
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-9503-02"
SNAP = PKG / "source" / "9503.md"
MD_REPORT = PKG / "KF-RESULT-wp-9503-02.md"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CLS = _load("wp9503_classify", ROOT / "scripts" / "kf" / "wp9503_02_classify.py")
REP = _load("wp9503_report", ROOT / "scripts" / "kf" / "wp9503_02_report.py")


@pytest.fixture(scope="module")
def artifacts():
    return {
        "contract": json.loads((PKG / "work-package.json").read_text(encoding="utf-8")),
        "cls": json.loads((PKG / "classification.json").read_text(encoding="utf-8")),
        "kf": json.loads((PKG / "kf_result.json").read_text(encoding="utf-8")),
        "md": SNAP.read_text(encoding="utf-8"),
    }


def bad_locators(md: str, locs) -> list[dict]:
    """定位校验器：偏移一致性 + quote 哈希 + 子串可解析。"""
    bad = []
    for l in locs:
        if md[l["start"]:l["end"]] != l["quote"]:
            bad.append(l)
            continue
        if "sha256:" + hashlib.sha256(l["quote"].encode()).hexdigest() != l["content_hash"]:
            bad.append(l)
            continue
        if l["quote"] not in md:
            bad.append(l)
            continue
        if not (l["start"] <= l["match"][0] < l["match"][1] <= l["end"]):
            bad.append(l)
    return bad


def test_source_snapshot_hash_matches_contract(artifacts):
    declared = artifacts["contract"]["input"]["source_hash"]
    computed = "sha256:" + hashlib.sha256(SNAP.read_bytes()).hexdigest()
    assert computed == declared
    assert artifacts["kf"]["provenance"]["source_hash"] == declared
    assert artifacts["kf"]["provenance"]["source_hash_matches"] is True
    assert len(artifacts["md"]) == artifacts["contract"]["input"]["chars"]


def test_kf_result_passes_schema_hard_constraints(artifacts):
    assert REP.validate_kf_result(artifacts["kf"]) == []


def test_classification_replays_deterministically(artifacts):
    md = artifacts["md"]
    seg = CLS.segment(md)
    scores = CLS.score_types(md, seg, "combined")
    primary, confidence, rows = CLS.primary_of(scores)
    cls = artifacts["cls"]
    assert primary == cls["classification"]["primary_report_type"]
    assert confidence == cls["classification"]["confidence"]
    assert [r["report_type"] for r in rows] == [r["report_type"] for r in cls["type_scores"]]
    assert [r["distinct_signals_matched"] for r in rows] == \
           [r["distinct_signals_matched"] for r in cls["type_scores"]]
    assert sum(len(r["locators"]) for r in rows) == \
           sum(len(r["locators"]) for r in cls["type_scores"])
    assert [s["heading"] for s in seg["sections"]] == \
           [s["heading"] for s in cls["structure"]["sections"]]


def test_every_locator_is_resolvable(artifacts):
    cls, md = artifacts["cls"], artifacts["md"]
    locs = [l for r in cls["type_scores"] for l in r["locators"]]
    locs += [t["evidence"] for t in cls["topics"]]
    locs += [t["evidence"] for t in cls["platform_tag_alignment"] if t["verbatim_in_markdown"]]
    assert len(locs) >= 30
    assert bad_locators(md, locs) == []


def test_locator_checker_has_teeth(artifacts):
    cls, md = artifacts["cls"], artifacts["md"]
    loc = dict(cls["type_scores"][0]["locators"][0])
    loc["quote"] = loc["quote"][:-1] + ("X" if not loc["quote"].endswith("X") else "Y")
    assert bad_locators(md, [loc]) != []
    loc2 = dict(cls["type_scores"][0]["locators"][0])
    loc2["content_hash"] = "sha256:" + "0" * 64
    assert bad_locators(md, [loc2]) != []


def test_no_duplicate_ids(artifacts):
    cls = artifacts["cls"]
    sec = [s["section_id"] for s in cls["structure"]["sections"]]
    topics = [t["topic_id"] for t in cls["topics"]]
    sig = ["%s:%s" % (r["report_type"], m["signal"])
           for r in cls["type_scores"] for m in r["matched_signals"]]
    for ids in (sec, topics, sig):
        assert len(ids) == len(set(ids))


def test_topic_ledger_is_consistent(artifacts):
    cls = artifacts["cls"]
    assert len(cls["topics"]) + len(cls["topics_unresolved"]) == 10
    for t in cls["topics"]:
        assert t["evidence"]["quote"] and t["anchor"] in t["evidence"]["quote"]
    for u in cls["topics_unresolved"]:
        assert u["status"] == "unresolved" and u["reason"]
    tags = cls["platform_tag_alignment"]
    assert all(("verbatim_in_markdown" in t) for t in tags)
    assert all((t["verbatim_in_markdown"] or t["status"] == "unresolved") for t in tags)


def test_repo_gate_cross_check_is_recorded_and_evidence_clean(artifacts):
    """用本仓三门校验器复跑，钉住披露内容：E1–E7 必须全通过，结构失败项必须只是 03 口径 + schema 漂移。"""
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from ke import wp_gate

    rep = wp_gate.run_gates(PKG, wp_gate.DirSourceResolver(PKG / "source", field="markdown"))
    ev = {c["name"]: c["ok"] for c in rep["evidence"]["checks"]}
    assert ev and all(ev.values()), ev
    fails = {c["name"] for c in rep["structural"]["checks"] if not c["ok"]}
    assert fails <= {"S1.files_present", "S3.contract_schema", "S5.summary_schema",
                     "S12.zero_claim_legality", "S13.counts_consistent", "S14.source_identity"}
    probe = artifacts["cls"]["repo_gate_probe"]
    assert probe["status"] == "ran"
    assert probe["verdict"] == rep["verdict"]
    assert probe["evidence_fail"] == []
    assert {f["rule"] for f in probe["structural_fail"]} == fails


def test_routing_mirrors_contract(artifacts):
    cls, contract = artifacts["cls"], artifacts["contract"]
    assert cls["routing"]["scenario_key"] == contract["input"]["scenario_key"]
    assert cls["routing"]["lane"] == contract["lane"]
    assert cls["routing"]["declared_layer"] == "EEXI|p73w2b-n02-eexi-closed-loop|l"
    assert cls["routing"]["declared_layer"] in contract["notes"]


def test_selected_skill_matches_primary_type(artifacts):
    cls = artifacts["cls"]
    reg = json.loads((ROOT / "extraction-skills" / "registry.json").read_text(encoding="utf-8"))
    by_type = {s["report_type"]: s for s in reg["skills"]}
    prim = cls["classification"]["primary_report_type"]
    assert cls["selected_skill"]["skill_id"] == by_type[prim]["skill_id"]
    assert cls["selected_skill"]["lifecycle_state_as_observed"] == "template-created"


def test_report_md_has_exactly_one_json_block_equal_to_kf_result(artifacts):
    md = MD_REPORT.read_text(encoding="utf-8")
    assert md.startswith("# KF-RESULT wp-9503-02")
    assert "kf-wp:wp-9503-02" in md
    assert md.count("```json") == 1
    body = re.search(r"```json\n(.*?)\n```", md, re.S).group(1)
    assert json.loads(body) == artifacts["kf"]
    # 反向：篡改一个数字后必须不再等价
    tampered = dict(artifacts["kf"])
    tampered["report_id"] = "9504"
    assert json.loads(body) != tampered


def test_no_verified_status_claimed(artifacts):
    kf = artifacts["kf"]
    blob = json.dumps(kf, ensure_ascii=False)
    assert '"verified": true' not in blob
    assert "epistemic_status\": \"verified" not in blob
    cls = artifacts["cls"]
    assert "verified" not in json.dumps(cls["selected_skill"], ensure_ascii=False)


def test_acceptance_self_check_reports_no_failures(artifacts):
    chk = artifacts["cls"]["acceptance_self_check"]
    assert chk["valid_json"] is True
    assert chk["schema_pass"] is True
    assert chk["source_locator_resolvable"]["pass"] is True
    assert chk["source_locator_resolvable"]["failures"] == []
    assert chk["source_hash_matches"]["pass"] is True
    assert chk["no_duplicate_ids"]["pass"] is True
    assert chk["all_claims_have_evidence_or_explicit_unresolved_status"]["pass"] is True