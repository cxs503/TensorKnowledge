"""wp-1200-01 资产登记的守护测试（离线、无网络）。

断言的是**不变量**，不是"代码跑过了"：
  - 源哈希与登记值一致（对 docs 内 markdown 副本重算）
  - 每个 locator 的 quote 是源文本的逐字切片（char/line 自洽）
  - 工件 anchor 逐字落在引用行内
  - id 全域唯一；claim 均有 quote 证据或显式 unresolved_reason；无 verified 标记
  - 变异验证：篡改 quote / 重复 id / 抹掉 unresolved_reason 必须被检出（证明检查有牙）
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "kf" / "wp-1200-01"
MD = (OUT / "source_1200.md").read_text(encoding="utf-8")
MANIFEST = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
ENVELOPE = json.loads((OUT / "result_envelope.json").read_text(encoding="utf-8"))
EXPECTED_HASH = "sha256:c75f5f263be1e61a6f4b6a557c31c743488e8c6c03364675567aef5fd44ede48"


# ---------------------------------------------------------------- helpers (被测不变量)
def locators(man: dict) -> list[tuple[str, dict]]:
    out = [("title", man["source"]["title_locator"])]
    out += [(f"schema:{e['ref_id']}", e["locator"]) for e in man["registered_schema_elements"]]
    out += [(f"metric:{m['metric_id']}", m["locator"]) for m in man["registered_metric_locators"]]
    for a in man["attachments"]:
        out += [(f"attach:{a['asset_id']}#{i}", loc) for i, loc in enumerate(a["mentioned_at"])]
    return out


def bad_locators(man: dict, md: str) -> list[str]:
    bad = []
    for name, loc in locators(man):
        quote, cs, ce = loc["quote"], loc["char_start"], loc["char_end"]
        if not (quote and quote == md[cs:ce] and quote in md
                and md.count("\n", 0, cs) + 1 == loc["line_start"]):
            bad.append(name)
    return bad


def duplicate_ids(man: dict) -> list[str]:
    ids = ["asset-report-1200"]
    ids += [e["ref_id"] for e in man["registered_schema_elements"]]
    ids += [m["metric_id"] for m in man["registered_metric_locators"]]
    ids += [a["asset_id"] for a in man["attachments"]]
    ids += [c["claim_id"] for c in man["claims"]]
    return sorted({i for i in ids if ids.count(i) > 1})


def claim_problems(envelope: dict, md: str) -> list[str]:
    probs = []
    for c in envelope.get("claims", []):
        ev = c.get("evidence", [])
        if not ev and not c.get("unresolved_reason"):
            probs.append(f"{c['claim_id']}:no-evidence-no-reason")
        if c.get("status") == "unresolved" and not c.get("unresolved_reason"):
            probs.append(f"{c['claim_id']}:unresolved-no-reason")
        probs += [f"{c['claim_id']}:quote-not-verbatim" for e in ev if e.get("quote") not in md]
    return probs


# ---------------------------------------------------------------- 正向不变量
def test_source_hash_and_size():
    assert "sha256:" + hashlib.sha256(MD.encode("utf-8")).hexdigest() == EXPECTED_HASH
    assert MANIFEST["source"]["sha256"] == EXPECTED_HASH
    assert ENVELOPE["provenance"]["source_hash"] == EXPECTED_HASH
    assert MANIFEST["source"]["chars"] == len(MD) == 3612
    assert MANIFEST["source"]["bytes"] == len(MD.encode("utf-8"))


def test_all_locators_verbatim():
    assert bad_locators(MANIFEST, MD) == []


def test_artifact_anchors_inside_reference_line():
    for a in MANIFEST["attachments"]:
        for loc in a["mentioned_at"]:
            assert loc["anchor_text"] == a["ref"]
            assert loc["char_start"] <= loc["anchor_char_start"] < loc["anchor_char_end"] <= loc["char_end"]
            assert md_slice(loc) == a["ref"]


def md_slice(loc: dict) -> str:
    return MD[loc["anchor_char_start"]:loc["anchor_char_end"]]


def test_no_duplicate_ids():
    assert duplicate_ids(MANIFEST) == []


def test_claims_compliance():
    assert claim_problems(ENVELOPE, MD) == []
    assert ENVELOPE["claims"] == MANIFEST["claims"]
    assert {c["status"] for c in ENVELOPE["claims"]} <= {
        "supported", "partially-supported", "unresolved", "refuted"}
    # 至少一条显式未决（保留不确定性），且本单不产出 verified
    assert any(c["status"] == "unresolved" for c in ENVELOPE["claims"])
    assert '"verified": true' not in json.dumps(ENVELOPE, ensure_ascii=False).replace(
        '"verified":true', '"verified": true')


def test_only_report_1200():
    assert ENVELOPE["report_id"] == "1200" == MANIFEST["source"]["report_id"]
    assert ENVELOPE["package_id"] == "wp-1200-01"
    assert ENVELOPE["task_type"] == "01-asset-registration"


def test_envelope_matches_schema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads((ROOT / "schemas" / "kf_result.v1.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(ENVELOPE, schema)


# ---------------------------------------------------------------- 变异验证（检查有牙）
def test_mutation_tampered_quote_is_detected():
    man = copy.deepcopy(MANIFEST)
    loc = man["registered_schema_elements"][0]["locator"]
    loc["quote"] = loc["quote"].replace("report_id", "report_ID")
    assert bad_locators(man, MD) == ["schema:schema-elem-01"]


def test_mutation_shifted_line_number_is_detected():
    man = copy.deepcopy(MANIFEST)
    man["registered_metric_locators"][0]["locator"]["line_start"] += 1
    assert bad_locators(man, MD) == ["metric:mig_files"]


def test_mutation_duplicate_id_is_detected():
    man = copy.deepcopy(MANIFEST)
    man["attachments"][1]["asset_id"] = man["attachments"][0]["asset_id"]
    assert duplicate_ids(man) == [man["attachments"][0]["asset_id"]]


def test_mutation_unresolved_without_reason_is_detected():
    env = copy.deepcopy(ENVELOPE)
    target = next(c for c in env["claims"] if c["status"] == "unresolved")
    target.pop("unresolved_reason")
    assert any("unresolved-no-reason" in p for p in claim_problems(env, MD))


def test_mutation_non_verbatim_claim_quote_is_detected():
    env = copy.deepcopy(ENVELOPE)
    env["claims"][0]["evidence"][0]["quote"] += "（本句不存在于原文）"
    assert any("quote-not-verbatim" in p for p in claim_problems(env, MD))