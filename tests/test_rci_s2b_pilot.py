"""RCI S2b 200-object pilot tests (anchor KBM-RCI-S2B-PILOT).

守四件事：
  1. 抽样可复现（同语料 → 同样本，分层保底与预算都对）；
  2. 断言的是**不变量**而不是「跑过一遍」：映射出的 ID 合法且唯一、
     strict v1 必然拒绝仓内语料、v1.1 投影能救回来、R1/R5 不得解锁 L3；
  3. 报告数字零手抄：`metrics.json` 重算摘要一致、表格块逐字符相等；
  4. 图能从工件重建（PNG 魔数 + 体积下限），不靠 git 里那张图「看起来对」。
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
ART = REPO / "docs" / "rci-s2b-pilot200"
DOC = REPO / "docs" / "rci-s2b-pilot200-report.md"
FIG_DIR = REPO / "docs" / "assets" / "rci"


def _load_pilot():
    path = REPO / "scripts" / "rci_s2b_pilot.py"
    spec = importlib.util.spec_from_file_location("rci_s2b_pilot", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("rci_s2b_pilot", mod)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pilot():
    return _load_pilot()


@pytest.fixture(scope="module")
def frame(pilot):
    return pilot.build_frame()


@pytest.fixture(scope="module")
def samp(pilot, frame):
    return pilot.sample(frame)


@pytest.fixture(scope="module")
def measured(pilot, frame, samp):
    return pilot.measure(frame, samp)


@pytest.fixture(scope="module")
def metrics(pilot, frame, samp, measured):
    return pilot.summarize(frame, samp, measured)


def _committed(name: str) -> dict:
    path = ART / name
    if not path.exists():
        pytest.skip(f"missing artifact {path} (run scripts/rci_s2b_pilot.py)")
    return json.loads(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ 1. sampling
def test_frame_is_deduplicated_real_corpus(pilot, frame):
    claims = frame["claims"]
    assert len(claims) == len(set(claims)) > 5000, "抽样框应是仓内真实语料的去重全集"
    assert all("statement" in c for c in claims.values())
    assert frame["evidence"], "evidence 索引不能为空"
    # 全部 facet 都要有层
    assert {k[0] for k in frame["strata"]} == set(pilot.CORPORA)


def test_sample_is_deterministic(pilot, frame, samp):
    again = pilot.sample(frame)
    assert [r["claim_id"] for r in again["rows"]] == [r["claim_id"] for r in samp["rows"]]
    assert again["n"] == samp["n"] == pilot.PILOT_N


def test_sample_respects_strata_budget_and_floor(pilot, frame, samp):
    strata = frame["strata"]
    counts: dict[tuple[str, str], int] = {}
    for row in samp["rows"]:
        key = (row["facet"], row["source_claim_type"])
        counts[key] = counts.get(key, 0) + 1
    assert set(counts) == set(strata), "每层都要有代表，层数不能漏"
    for key, member_ids in strata.items():
        size = len(member_ids)
        got = counts[key]
        assert got <= size
        assert got >= min(pilot.MIN_PER_STRATUM, size), f"层 {key} 未达保底"
    assert len(samp["rows"]) <= pilot.PILOT_N
    # 权重 = 层规模 / 抽中数（用于把样本比率还原成总体比率）
    for row in samp["rows"]:
        assert row["weight"] == pytest.approx(row["stratum_size"] / counts[(row["facet"], row["source_claim_type"])])


def test_sample_order_key_is_hash_of_seed_and_id(pilot, samp):
    import hashlib

    for row in samp["rows"][:25]:
        expected = hashlib.sha256(f"{pilot.SEED}:{row['claim_id']}".encode()).hexdigest()
        assert row["order_key"] == expected


# ------------------------------------------------------------------ 2. mapping
def test_knowledge_ids_match_schema_and_are_unique(pilot, samp, measured):
    pattern = re.compile(r"^ko:[a-z0-9][a-z0-9._-]*:[a-z0-9][a-z0-9._-]*$")
    ids = [it["doc"]["knowledge_id"] for it in measured["items"]]
    assert len(ids) == len(set(ids))
    assert all(pattern.match(i) for i in ids)


def test_section_anchor_respects_schema_charset(pilot, samp, measured):
    anchor_re = re.compile(r"^[a-z0-9\u4e00-\u9fff][a-z0-9\u4e00-\u9fff-]*$")
    anchors = [ev["section"]["anchor"] for it in measured["items"] for ev in it["doc"]["evidence"]]
    assert anchors, "样本里应有证据"
    assert all(anchor_re.match(a) for a in anchors)


def test_unmapped_source_types_are_not_silently_retyped(pilot, samp, measured):
    unmapped = [it for it in measured["items"] if not it["audit"]["type_mapped"]]
    assert unmapped, "本语料确实存在无诚实映射的 claim_type（interpretive/hypothesis）"
    for it in unmapped:
        assert any(e.startswith("R3:") for e in it["projected_errors"]), "无映射必须显式拒收，不能静默挂 definition"
        assert it["doc"]["type"] not in pilot.CARD_TYPES


# --------------------------------------------------- 3. strict v1 vs projection
def test_strict_v1_rejects_whole_repo_corpus(measured):
    """仓内语料 0 条证据带 report_id ⇒ strict v1 必须全体失败（这是被度量的发现，不是缺陷）。"""
    assert all(it["strict_errors"] for it in measured["items"])
    assert all("R1_evidence_locator" in it["strict_categories"] for it in measured["items"])


def test_projection_recovers_most_of_the_sample(pilot, samp, metrics):
    assert metrics["projected_v1_1"]["rate"] >= 0.9
    assert metrics["strict_v1"]["rate"] == 0.0
    remaining = metrics["projected_v1_1"]["blockers"]
    assert set(remaining) <= {"R1_evidence_locator", "R3_type_bridge", "payload_card_body"}, remaining


def test_r1_never_unlocks_report_claimed(pilot, measured):
    """R1 只放宽证据定位符，不得让 locator 型证据把对象抬进 report_claimed。"""
    validator = pilot._load_validator()
    schema = pilot.projected_schema(validator._load_schema(validator.SCHEMA_V1))
    doc = json.loads(json.dumps(measured["items"][0]["doc"]))
    doc["verification_status"] = "report_claimed"
    errors = pilot.validate_projected(doc, schema, validator)
    assert any("report_id" in e for e in errors), errors


def test_r1_r5_never_unlock_l3(pilot, measured):
    """v1.1 投影不得触碰 L3 通道：无平台验证单即拒。"""
    validator = pilot._load_validator()
    schema = pilot.projected_schema(validator._load_schema(validator.SCHEMA_V1))
    doc = json.loads(json.dumps(measured["items"][0]["doc"]))
    doc["verification_status"] = "platform_verified"
    doc["provenance"]["storage_level"] = "L3"
    errors = pilot.validate_projected(doc, schema, validator)
    assert any("platform_verified" in e for e in errors), errors
    # 权威校验器同样拒绝（不经投影也进不去）
    strict_errors = pilot.validate_strict(doc, validator)
    assert any("platform_verified" in e or "verification" in e for e in strict_errors), strict_errors


def test_quote_span_hash_is_labelled_not_faked(pilot, frame, samp, measured):
    """R5 自算哈希必须标 kind=quote_span，且不得冒充 source_file。"""
    kinds = {
        ev["locator"]["content_sha256_kind"]
        for it in measured["items"]
        for ev in it["doc"]["evidence"]
    }
    assert kinds <= {"source_file", "quote_span", "none"}
    for it in measured["items"]:
        for ev in it["doc"]["evidence"]:
            loc = ev["locator"]
            if loc["content_sha256_kind"] == "source_file":
                assert re.fullmatch(r"[0-9a-f]{64}", loc["content_sha256"])
            if loc["content_sha256_kind"] == "none":
                assert loc["content_sha256"] == ""


# ------------------------------------------------------------------ 4. metrics
def test_rqs_is_bounded_and_equals_published_weights(pilot, measured):
    assert sum(pilot.RQS_WEIGHTS.values()) == pytest.approx(1.0)
    for it in measured["items"]:
        rqs = it["rqs"]
        assert 0.0 <= rqs["RQS"] <= 1.0
        manual = sum(pilot.RQS_WEIGHTS[k] * rqs[k] for k in pilot.RQS_WEIGHTS)
        assert rqs["RQS"] == pytest.approx(round(manual, 4), abs=1e-4)


def test_review_field_rates_are_counts_not_guesses(metrics):
    for row in metrics["review_fields"]:
        assert row["n"] == metrics["sample"]["n"]
        assert row["derivable_v10"] <= row["derivable"] <= row["n"]
        assert row["invariant_consistent"] + row["conflicts"] == row["derivable"]
        assert 0.0 <= row["accuracy"] <= 1.0
    basis = next(r for r in metrics["review_fields"] if r["field"] == "confidence.basis")
    assert basis["derivable_v10"] == 0, "v1.0 词表表达不了 code/dataset 证据 → basis 必须派生不出"
    assert basis["derivable"] > 0, "v1.1 增补 basis 词后应能派生"


def test_evidence_gates_sum_to_counts(metrics):
    ev = metrics["evidence"]
    gates = ev["gates"]
    assert ev["evidence_traceable"] <= gates["content_addressed"]
    assert ev["evidence_traceable"] <= gates["quote_present"]
    assert ev["trace_rate"] == pytest.approx(round(ev["evidence_traceable"] / ev["evidence_total"], 4))
    assert len(ev["per_object_trace_rate"]) == metrics["sample"]["n"]


# --------------------------------------------------- 5. zero hand-copy discipline
def test_committed_metrics_reproduce(pilot, metrics):
    """工件不是手写快照：重算必须得到同一个稳定摘要（除时间戳）。"""
    committed = _committed("metrics.json")
    assert committed["reproducibility"]["metrics_sha256"] == metrics["reproducibility"]["metrics_sha256"]
    assert committed["strict_v1"] == metrics["strict_v1"]
    assert committed["projected_v1_1"] == metrics["projected_v1_1"]


def test_committed_tables_equal_rendered(pilot, metrics):
    _committed("metrics.json")
    rendered = pilot.render_tables(metrics)
    doc = DOC.read_text(encoding="utf-8")
    assert rendered in doc, "报告里的数字块必须与渲染结果逐字符一致（禁止手抄）"


def test_error_table_matches_committed_rates(pilot, metrics):
    rates = _committed("full_frame_rates.json")
    rendered = pilot.render_error_table(metrics, rates)
    assert rendered in DOC.read_text(encoding="utf-8"), "§6 误差表必须由 full_frame_rates.json 渲染（禁止手抄）"
    # 基准必须是全样本枚举，不是又一次抽样
    assert rates["population"] >= 10000


def test_population_baseline_is_consistent_with_sample(pilot, metrics):
    """§6 的核心断言：加权估计贴近全样本真值，不加权值允许偏离。"""
    rates = _committed("full_frame_rates.json")
    assert rates["strict_v1_pass"] == 0
    assert abs(metrics["projected_v1_1"]["weighted_rate"] - rates["projected_v1_1_rate"]) < 0.01
    assert abs(metrics["strict_v1"]["weighted_rate"] - rates["strict_v1_rate"]) < 0.01
    assert rates["type_unmapped"] == 4


# ------------------------------------------------------------------ 6. figures
def test_figures_rebuild_from_metrics(pilot, metrics, tmp_path):
    pngs = [
        pilot.figure_quality_by_type(metrics, tmp_path / "ko_quality_by_type.png"),
        pilot.figure_review_accuracy(metrics, tmp_path / "review_field_accuracy.png"),
        pilot.figure_rqs(metrics, tmp_path / "rqs_distribution.png"),
    ]
    for png in pngs:
        assert png.exists() and png.stat().st_size > 5000
        assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    for name in ("ko_quality_by_type.png", "review_field_accuracy.png", "rqs_distribution.png"):
        assert (FIG_DIR / name).exists(), f"仓库内应提交 {name}"


def test_report_documents_declared_limits(pilot):
    """报告必须显式回答「是否 <3%」与未测项，不能只写结论。"""
    doc = DOC.read_text(encoding="utf-8")
    for needle in ("<3 pp", "未测", "honest", "不适用"):
        assert needle in doc, f"报告缺少声明：{needle}"
    rev = (REPO / "docs" / "rci-s2b-schema-revisions.md").read_text(encoding="utf-8")
    for rid in ("R1", "R2", "R3", "R4", "R5", "R6"):
        assert rid in rev
    assert "不采纳" in rev