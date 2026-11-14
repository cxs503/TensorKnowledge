"""RCI S2b 试点报告的「零手抄」回归测试（anchor KBM-RCI-S2B-PILOT）。

背景（真实缺陷，不是假想）：`docs/rci-s2b-pilot200-report.md` 曾以**追加**而非
就地替换的方式落地过一轮修订（#359/#361 之后），结果同一个文件里同时存在：

* `10,238 条 evidence`（旧值，错）与 `10,107 条 evidence`（重算值，对）；
* ⑤7「E-TR 维度均值 0.83」（旧）与 0.87（= `metrics.json` 真值）；
* ④图注「0/1 两峰 + 中间少量」（与实测不符：中间值 0 个）；
* `--full-frame` 的耗时 44 s / 32 s 两个互相矛盾的估计。

读者没法判断哪一句是真的。本文件把这几类数字绑到**可重算的量**上：
数字变了而报告没变 ⇒ 测试红；报告被重复粘贴 ⇒ 测试红。

守四件事：
  1. 报告不得出现重复段落（检测「追加式修订」这一失败模式本身）；
  2. 报告里的 evidence 索引条数 == `build_frame()["evidence"]` 长度；
  3. E-TR 均值、零分对象构成、逐对象分布 == `measure()` 逐条重算的结果；
  4. 同一件事（全样本枚举耗时）在报告里只能有一个数，且「约 N s」与「实测 X s」自洽。
"""
from __future__ import annotations

import collections
import importlib.util
import json
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
DOC = REPO / "docs" / "rci-s2b-pilot200-report.md"
ART = REPO / "docs" / "rci-s2b-pilot200"


def _load_pilot():
    path = REPO / "scripts" / "rci_s2b_pilot.py"
    spec = importlib.util.spec_from_file_location("rci_s2b_pilot_report_integrity", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("rci_s2b_pilot_report_integrity", mod)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pilot():
    return _load_pilot()


@pytest.fixture(scope="module")
def text():
    return DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def frame(pilot):
    return pilot.build_frame()


@pytest.fixture(scope="module")
def measured(pilot, frame):
    return pilot.measure(frame, pilot.sample(frame))


@pytest.fixture(scope="module")
def etr_stats(measured):
    """把报告里被引用的那一组数从 measurement 里重算一遍（不读报告、不读 metrics.json）。"""
    items = measured["items"]
    zero = [x for x in items if x["rqs"]["evidence_traceability"] == 0.0]
    no_ev = [x for x in zero if not x["doc"].get("evidence")]
    holders = [x for x in zero if x["doc"].get("evidence")]
    evid = [ev for x in holders for ev in x["doc"]["evidence"]]
    no_quote = 0
    quote_no_locator = 0
    for ev in evid:
        loc = ev.get("locator") or {}
        art = ev.get("artifact_ref") or {}
        quoted = len(str(loc.get("quote") or "").strip()) >= 15
        local = bool(loc.get("citation")) and (REPO / str(loc["citation"])).exists()
        pinned = str(art.get("commit") or "") != ""
        value_pin = bool(re.search(r"@[0-9a-f]{7,40}\b", str(loc.get("value") or "")))
        if not quoted:
            no_quote += 1
        elif not (local or pinned or value_pin):
            quote_no_locator += 1
    span = sum(
        1
        for x in items
        for ev in x["doc"]["evidence"]
        if (ev.get("locator") or {}).get("content_sha256_kind") == "quote_span"
    )
    return {
        "n_items": len(items),
        "n_zero": len(zero),
        "n_no_evidence": len(no_ev),
        "n_holders": len(holders),
        "n_evidence": len(evid),
        "n_no_quote": no_quote,
        "n_quote_no_locator": quote_no_locator,
        "n_quote_span": span,
        "n_one": sum(1 for x in items if x["rqs"]["evidence_traceability"] == 1.0),
        "n_mid": sum(1 for x in items if 0 < x["rqs"]["evidence_traceability"] < 1),
        "mean": sum(x["rqs"]["evidence_traceability"] for x in items) / len(items),
    }


# ------------------------------------------------------ 1. 结构：不得有重复粘贴块
def test_report_has_no_duplicated_long_lines(text):
    """同一段话出现两次 ⇒ 上一轮「追加式修订」重演，直接把矛盾数字带进正文。"""
    long_lines = [ln.rstrip() for ln in text.splitlines() if len(ln.strip()) > 60]
    dupes = [ln for ln, n in collections.Counter(long_lines).items() if n > 1]
    assert dupes == [], "报告里出现重复段落：" + " | ".join(d[:60] for d in dupes)


def test_report_states_reproduce_command_exactly_once(text):
    """复现命令块是「追加式修订」最先重复的东西，单独钉住。"""
    assert text.count("> 复现：") == 1
    assert text.count("--full-frame") >= 1  # 至少头部那条复现命令在场


# -------------------------------------------- 2. 数字：与 build_frame() 重算值一致
def test_evidence_index_count_matches_recomputed_frame(text, frame):
    """`N 条 evidence` / `N evidence` 只能出现重算值，旧值不许残留。"""
    expected = f"{len(frame['evidence']):,}"
    found = set(re.findall(r"([\d,]+) 条 evidence", text)) | set(re.findall(r"/ ([\d,]+) evidence", text))
    assert found == {expected}, f"报告写着 {found}，重算 build_frame() = {expected}"
    assert "10,238" not in text, "旧值 10,238 是错值（重算为 10,107），不许再出现"


def test_etr_mean_matches_measurement_and_metrics(text, etr_stats):
    """⑤7 的 E-TR 均值必须同时等于 measure() 重算值与本轮提交的 metrics.json。"""
    metrics = json.loads((ART / "metrics.json").read_text(encoding="utf-8"))
    published = metrics["rqs"]["dimension_means"]["evidence_traceability"]
    assert round(etr_stats["mean"], 4) == round(published, 4) == 0.87

    quoted = re.findall(r"E-TR 维度均值 ([\d.]+)", text)
    assert quoted == [f"{etr_stats['mean']:.2f}"], f"报告写着 {quoted}，重算 {etr_stats['mean']:.4f}"


def test_zero_etr_breakdown_matches_measurement(text, etr_stats):
    """⑤7 里那串构成数（26 / 2 / 24 / 25 / 12 / 13）必须能从 measurement 复现。"""
    expected = (
        f"{etr_stats['n_zero']} 个 E-TR=0（其中 {etr_stats['n_no_evidence']} 个对象本身无证据条目；"
        f"其余 {etr_stats['n_holders']} 个对象名下的 {etr_stats['n_evidence']} 条证据中，"
        f"{etr_stats['n_no_quote']} 条 quote 不足 15 字符、"
        f"{etr_stats['n_quote_no_locator']} 条有哈希与 quote 但缺可解析定位"
    )
    assert expected in text
    assert etr_stats["n_no_quote"] + etr_stats["n_quote_no_locator"] == etr_stats["n_evidence"]


def test_etr_object_distribution_caption_matches_measurement(text, etr_stats):
    """④图注必须描述实测分布（只有 1.0 与 0.0 两端，中间值个数为 0）。"""
    assert etr_stats["n_mid"] == 0
    assert etr_stats["n_one"] + etr_stats["n_zero"] == etr_stats["n_items"]
    assert (
        f"只有两端：{etr_stats['n_one']} 个对象 1.0、{etr_stats['n_zero']} 个对象 0.0，无中间值"
    ) in text


def test_r5_backstop_counts_match_measurement(text, etr_stats):
    """⑥ honest 项的「N 条证据缺 quote、M 条靠 R5 兜底」也要对得上。"""
    expected = f"{etr_stats['n_no_quote']} 条证据缺 quote、{etr_stats['n_quote_span']} 条靠 R5 引文哈希兜底"
    assert expected in text


# --------------------------------------------- 3. 同一件事只能有一个数（耗时自洽）
def test_full_frame_runtime_claims_are_single_valued(text):
    """`--full-frame` 的耗时在报告里出现两处，两处必须是同一个数且与实测自洽。"""
    approx = {int(v) for v in re.findall(r"`--full-frame`（本机约 (\d+) s）", text)}
    cost = {int(v) for v in re.findall(r"成本 (\d+) s（本机实测 [\d.]+ s", text)}
    measured_s = re.findall(r"成本 \d+ s（本机实测 ([\d.]+) s", text)
    assert len(approx) == 1 and len(cost) == 1, (approx, cost)
    assert approx == cost, f"头部 {approx} s 与 ⑥ 结论 {cost} s 互相矛盾"
    assert len(measured_s) == 1
    assert round(float(measured_s[0])) == cost.pop(), "「约 N s」必须等于实测值的四舍五入"


def test_mainrun_runtime_claim_is_single_valued(text):
    approx = set(re.findall(r"rci_s2b_pilot\.py`（本机约 (\d+) s）", text))
    assert len(approx) == 1, approx
    assert int(next(iter(approx))) >= 1