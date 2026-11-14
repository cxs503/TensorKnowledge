"""工序 02 产物（wp-14478-02）的机器校验：G1 类不变量，不做语义判定。

被校验对象：
  docs/kf/wp-14478-02/classification.json   （schemas/classification.v1.schema.json）
  docs/kf/wp-14478-02/kf_result.json        （schemas/kf_result.v1.schema.json）
  docs/kf/wp-14478-02/source/report_14478.md（源快照，字节等价于平台 markdown 字段）

每个测试都独立重算，不复用生成脚本的中间结果（避免“测试只是重跑生成器”）。
run: pytest tests/test_kf_wp14478_02.py -q
"""
from __future__ import annotations

import hashlib
import json
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "docs" / "kf" / "wp-14478-02"
SNAPSHOT = OUT / "source" / "report_14478.md"
CLASSIFICATION = OUT / "classification.json"
KF_RESULT = OUT / "kf_result.json"
SCRIPT = REPO / "scripts" / "kf" / "wp14478_02_classify.py"
REGISTRY = REPO / "extraction-skills" / "registry.json"

CONTRACT_HASH = "sha256:8fbd643e2e79a0fece5f9ae2fbe87a0045f268d61da54927711e260c14b206b0"
CONTRACT_CHARS = 6156
PACKAGE_ID = "wp-14478-02"
REPORT_ID = "14478"


def sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def md() -> str:
    assert SNAPSHOT.exists(), f"缺源快照 {SNAPSHOT}"
    return SNAPSHOT.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def cls() -> dict:
    return json.loads(CLASSIFICATION.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kf() -> dict:
    return json.loads(KF_RESULT.read_text(encoding="utf-8"))


# --- 源身份 ---------------------------------------------------------------
def test_source_snapshot_is_byte_identical_to_contract(md):
    assert sha256(md) == CONTRACT_HASH
    assert len(md) == CONTRACT_CHARS


def test_provenance_declares_the_same_hash(cls, kf, md):
    assert cls["source"]["recomputed_hash"] == CONTRACT_HASH == sha256(md)
    assert cls["source"]["contract_hash"] == CONTRACT_HASH
    assert cls["source"]["source_hash_matches"] is True
    assert kf["provenance"]["source_hash"] == CONTRACT_HASH
    assert kf["provenance"]["source_hash_matches"] is True
    assert kf["provenance"]["source_uri"] == "tensor://reports/14478"
    assert kf["provenance"]["source_field"] == "markdown"


# --- schema ---------------------------------------------------------------
@pytest.mark.parametrize("doc_path,schema_path", [
    (CLASSIFICATION, REPO / "schemas" / "classification.v1.schema.json"),
    (KF_RESULT, REPO / "schemas" / "kf_result.v1.schema.json"),
])
def test_documents_conform_to_schema(doc_path, schema_path):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    doc = json.loads(doc_path.read_text(encoding="utf-8"))
    errors = sorted(Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path))
    assert not errors, [(list(e.path), e.message) for e in errors[:5]]


# --- locator 可解析（独立重算偏移与哈希）----------------------------------
def test_every_locator_resolves_by_offsets_and_quote_hash(cls, md):
    n = 0
    for coll in ("signals", "topics"):
        for rec in cls[coll]:
            for loc in rec.get("evidence", []):
                n += 1
                s, e, q = loc["start_offset"], loc["end_offset"], loc["quote"]
                assert 0 <= s < e <= len(md), f"{rec['id']} 偏移越界 {s}-{e}"
                assert md[s:e] == q, f"{rec['id']} 偏移处的文本与 quote 不一致"
                assert sha256(q) == loc["content_hash"], f"{rec['id']} quote 哈希不符"
                assert loc["value"].endswith(f"chars:{s}-{e}")
    assert n >= 20, f"locator 数量异常偏少：{n}"


def test_every_quote_is_unique_in_source(cls, md):
    """引文必须能在原文唯一定位（否则 offset 可漂移，二次确认会失败）。"""
    for coll in ("signals", "topics"):
        for rec in cls[coll]:
            for loc in rec.get("evidence", []):
                assert md.count(loc["quote"]) == 1, f"{rec['id']} 引文在原文出现多次"


# --- acceptance: 无重复 id / 证据或显式 unresolved ------------------------
def test_no_duplicate_ids(cls):
    ids = ([r["id"] for r in cls["signals"]]
           + [t["id"] for t in cls["topics"]]
           + [s["id"] for s in cls["structure"]["sections"]]
           + [c["id"] for c in cls["report_type"]["candidates"]])
    assert len(ids) == len(set(ids)), "存在重复 id"


def test_every_signal_has_evidence_or_explicit_unresolved(cls):
    for rec in cls["signals"]:
        has_ev = bool(rec.get("evidence"))
        has_unres = "unresolved" in rec and len(rec["unresolved"]["reason"]) >= 20
        assert has_ev or has_unres, f"{rec['id']} 既无 locator 也无显式 unresolved"
        for loc in rec.get("evidence", []):
            assert loc["quote"].strip(), f"{rec['id']} 引文为空"
    # 判定为 matched 的信号必须带逐字证据（不许只靠理由）
    for rec in cls["signals"]:
        if rec["verdict"] == "matched":
            assert rec.get("evidence"), f"{rec['id']} matched 却无 locator"


# --- 类型与 skill 的注册表一致性 -----------------------------------------
def test_report_type_and_skill_are_registry_consistent(cls):
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rt = cls["report_type"]["id"]
    assert rt in reg["report_types"]
    skills = {s["skill_id"]: s for s in reg["skills"]}
    skill = skills[cls["report_type"]["chosen_skill_id"]]
    assert skill["report_type"] == rt
    assert cls["report_type"]["skill_version"] == skill["skill_version"]
    # 接受的类型唯一，且其 rationale 引用的信号都存在
    accepted = [c for c in cls["report_type"]["candidates"] if c["verdict"] == "accepted"]
    assert [c["id"] for c in accepted] == [rt]
    known = {r["id"] for r in cls["signals"]}
    for cand in cls["report_type"]["candidates"]:
        assert set(cand["signal_ids"]) <= known, f"{cand['id']} 引用了不存在的信号"


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys(v)


def test_classification_does_no_extraction(cls):
    """工序 02 不做抽取、不自证：产物里不得出现 claims 键或 verified 键。"""
    keys = set(_keys(cls))
    assert "claims" not in keys and "evidence.json" not in keys
    assert "verified" not in keys
    assert cls["objective"]["extract_claims"] is False
    assert cls["objective"]["register_assets"] is False


# --- 结构切分 -------------------------------------------------------------
def test_structure_is_contiguous_and_covers_whole_source(cls, md):
    secs = cls["structure"]["sections"]
    assert secs[0]["start_offset"] == 0
    assert secs[-1]["end_offset"] == len(md)
    for a, b in zip(secs, secs[1:]):
        assert a["end_offset"] == b["start_offset"]
    for s in secs:
        head = md[s["start_offset"]:s["end_offset"]].split("\n", 1)[0]
        assert head.startswith("#") and head.lstrip("# ").strip() == s["heading"]


# --- 不得自证 verified / 不得越界 ----------------------------------------
def test_producer_did_not_self_verify(cls, kf):
    v = cls["verification"]
    assert v["epistemic_status"] == "draft"
    assert v["assessment_status"] == "unassessed"
    assert v["verification_performed_by_producer"] is False
    assert kf["package_id"] == PACKAGE_ID and kf["task_type"] == "02-classification-parse"
    assert kf["report_id"] == REPORT_ID == cls["report_id"]


def test_outputs_only_classification(cls, kf):
    assert set(kf["outputs"]) == {"classification.json"}
    assert kf["outputs"]["classification.json"] == cls


# --- 生成器可复跑且确定性 -------------------------------------------------
def test_generator_reproduces_identical_artifacts(tmp_path):
    out = tmp_path / "wp-14478-02"
    rc = subprocess.run(
        [sys.executable, str(SCRIPT), "--check",
         "--snapshot", str(SNAPSHOT),
         "--out-dir", str(out),
         "--figure", str(tmp_path / "fig.png")],
        capture_output=True, text=True, cwd=REPO)
    assert rc.returncode == 0, rc.stdout + rc.stderr
    for name in ("classification.json", "kf_result.json"):
        fresh = json.loads((out / name).read_text(encoding="utf-8"))
        assert fresh == json.loads((OUT / name).read_text(encoding="utf-8")), f"{name} 不可确定性复现"

# --- 报告侧：唯一 JSON 代码块 === kf_result -------------------------------
def test_report_markdown_has_single_json_block_equal_to_kf_result(kf):
    import re
    report = OUT / "report.md"
    assert report.exists(), "缺 docs/kf/wp-14478-02/report.md"
    md = report.read_text(encoding="utf-8")
    assert md.startswith("# KF-RESULT wp-14478-02"), "报告标题不符"
    blocks = re.findall(r"```json\n(.*?)\n```", md, re.S)
    assert len(blocks) == 1, f"json 代码块数量 {len(blocks)} != 1"
    assert json.loads(blocks[0]) == kf, "报告内 JSON 块与 kf_result.json 不一致"
    assert md.count("kf-wp:wp-14478-02") >= 1, "报告未声明 kf-wp 标签"
    # 报告里的每个偏移区间都必须能在源快照上解析（报告数字不得手抄错）
    for a, b in re.findall(r"\| (\d+)–(\d+) \|", md):
        s, e = int(a), int(b)
        src = SNAPSHOT.read_text(encoding="utf-8")
        assert 0 <= s < e <= len(src), f"报告偏移越界 {s}-{e}"


def test_publish_payload_declares_required_title_and_tags():
    spec = importlib.util.spec_from_file_location(
        "wp14478_02_report", REPO / "scripts" / "kf" / "wp14478_02_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    assert f"kf-wp:{PACKAGE_ID}" in mod.TAGS
    assert mod.build()[1]["title"] == "KF-RESULT wp-14478-02"
    assert mod.build()[1]["figures"][0]["png_base64"]


def test_repro_cmd_works_with_relative_snapshot_path(tmp_path):
    """回归：repro_cmd 里 --snapshot 是相对工作树根的路径，必须能跑通（曾因 relative_to 抛错）。"""
    rel = SNAPSHOT.relative_to(REPO).as_posix()
    rc = subprocess.run(
        [sys.executable, "scripts/kf/wp14478_02_classify.py", "--check",
         "--snapshot", rel,
         "--out-dir", str(tmp_path / "out"),
         "--figure", str(tmp_path / "fig.png")],
        capture_output=True, text=True, cwd=REPO)
    assert rc.returncode == 0, rc.stdout + rc.stderr
    assert "ALL CHECKS PASS" in rc.stdout
