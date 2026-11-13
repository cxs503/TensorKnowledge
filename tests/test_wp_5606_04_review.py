"""wp-5606-04 独立审核的回归测试。

把四条不可退让的性质钉成断言：
1. 被审原文的字节哈希等于契约 source_hash（审核对象身份不可漂移）；
2. 审核报告里的每条原文引用都能在原文中逐字定位（零手抄）；
3. 上游账本的算术/分类守恒（百分比由计数导出、分类闭合 21 项）；
4. 交付物过 schema 且正文只有唯一一个 ```json 块（结果信道不歧义）。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

PKG = Path(__file__).resolve().parents[1] / "artifacts" / "wp-5606-04"
REPO = PKG.parents[1]
if str(PKG) not in sys.path:  # 复算脚本与测试同目录，直接复用其 QUOTE 表
    sys.path.insert(0, str(PKG))
SOURCE_HASH = "sha256:da0d91e5c5eae1aa240fba2fcc6b0ebab3960fb49f0f31378cf9a7f866b14edd"


@pytest.fixture(scope="module")
def built():
    """先复算再产交付面，保证断言针对本次运行的结果。"""
    subprocess.run([sys.executable, str(PKG / "indep_check.py")], check=True, cwd=REPO,
                   capture_output=True)
    subprocess.run([sys.executable, str(PKG / "build_report.py")], check=True, cwd=PKG / "..",
                   capture_output=True)
    return {
        "indep": json.loads((PKG / "indep_check.json").read_text(encoding="utf-8")),
        "report": json.loads((PKG / "review_report.json").read_text(encoding="utf-8")),
        "events": json.loads((PKG / "review_events.json").read_text(encoding="utf-8")),
        "pkg": json.loads((PKG / "work-package.json").read_text(encoding="utf-8")),
        "envelope": json.loads((PKG / "kf_result_envelope.json").read_text(encoding="utf-8")),
        "source": (PKG / "report_source_5606.md").read_text(encoding="utf-8"),
        "md": (PKG / "KF-RESULT_wp-5606-04.md").read_text(encoding="utf-8"),
    }


def test_source_identity(built):
    assert built["indep"]["source"]["sha256"] == SOURCE_HASH
    assert built["envelope"]["provenance"]["source_hash"] == SOURCE_HASH
    assert built["report"]["reviewed_artifact"]["sha256"] == SOURCE_HASH


def test_zero_handcopy_quotes_locatable(built):
    indep, src = built["indep"], built["source"]
    assert len(indep["quote_index"]) >= 30
    for key, info in indep["quote_index"].items():
        from indep_check import QUOTE  # noqa: PLC0415

        assert src[info["offset"]:info["offset"] + info["chars"]] == QUOTE[key], key


def test_every_report_quote_is_a_verbatim_substring(built):
    src = built["source"]

    checked = 0
    # 只有 quote 字段承担「逐字引用」义务；claim/verdict/detail 是本审核者的措辞
    quotes = [f["quote"] for f in built["report"]["claim_fidelity"]]
    quotes += [f["evidence"]["quote"] for f in
               built["report"]["findings"]["major"] + built["report"]["findings"]["minor"]
               + built["report"]["findings"]["informational"]]
    quotes += [o["quote"] for o in built["report"]["overstated_claims"]]
    for quote in quotes:
        for part in re.split(r"；|\s/\s", quote):
            part = part.strip()
            if not part:
                continue
            assert part in src, part[:80]
            checked += 1
    assert checked >= 25


def test_upstream_arithmetic_conservation(built):
    cons = built["indep"]["derived"]["conservation"]
    assert cons["n_rows"] == 20
    assert cons["percent_max_rel_err"] < 1e-3
    assert cons["divergence_partition"]["equals_total"] is True
    assert cons["claimed_vs_reconciled"]["explained_by"]["sum"] == 18
    # 计件法高估：20 条记录只有 14 条互异 SQL
    assert cons["distinct_sql_prefixes"] == 14
    assert len(cons["duplicate_value_groups"]) >= 5


def test_findings_are_not_silently_passed(built):
    """not_run/fail 必须显式登记；报告不得自封 verified（出现处必须是否定语境）。"""
    cs = built["indep"]["checks_summary"]
    assert len(cs["fail"]) >= 1 and len(cs["not_run"]) >= 1
    flat = json.dumps(built["report"], ensure_ascii=False)
    banned = ("verification_status", "verification_level", "is_verified", "verified\":")
    assert not [b for b in banned if b in flat], "报告出现生产者侧 verified 字段"
    for m in re.finditer("verified", flat):
        window = flat[max(0, m.start() - 40):m.end() + 5]
        assert "不" in window, f"'verified' 出现在非否定语境: {window!r}"
    assert built["report"]["disposition"] == "request-changes"
    assert built["events"][0]["decision"] == "request-changes"


def test_deliverables_pass_schemas(built):
    for schema_file, doc in (
        ("kf_result.v1.schema.json", built["envelope"]),
        ("work-package-contract.schema.json", built["pkg"]),
        ("review-event.schema.json", built["events"][0]),
    ):
        schema = json.loads((REPO / "schemas" / schema_file).read_text(encoding="utf-8"))
        jsonschema.validate(doc, schema)


def test_single_json_result_channel(built):
    md = built["md"]
    assert md.count("```json") == 1
    assert md.count("```") == 2
    block = re.search(r"```json\n(.*?)\n```", md, re.S).group(1)
    assert json.loads(block)["package_id"] == "wp-5606-04"
    assert md.startswith("# KF-RESULT wp-5606-04")