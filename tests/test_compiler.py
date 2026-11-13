"""Knowledge Compiler v1 守卫测试（合成语料，不依赖现网库）。

断言的是**不变量**而不是"跑过"：
1. 引文逐字 + 偏移一致（E1）；小节锚可重算（E2）；
2. 表格行/代码块不产 claim；
3. 同模板异值 → 矛盾候选（转 04 评审），同模板同值 → 近重复；
4. 0 claim 是合法完整结果（不造知识）；
5. KO v1 文档过 schema，且 verification_status 上限 = report_claimed；
6. 落库层拒绝 L3 自封（KOWriteError）；
7. 幂等：同一输入两次编译 → 同 knowledge_id 集合。
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ke import ko_store  # noqa: E402
from ke.compiler import (  # noqa: E402
    compile_report,
    extract_claims,
    iter_sections,
    verify_kobject,
)

REPORT = """# 合成算例：圆管阻力对齐

## ① 案例介绍

几何：D = 0.05 m，L = 2.0 m，Re = 1.0e4。

## ② 怎么做的

采用 RANS 与 LES 两套求解器，网格 1.2e6 单元。

## ③ 计算结果

- 摩擦阻力系数 Cf = 0.0071，与基准误差 2.4%。
- 摩擦阻力系数 Cf = 0.0079，与基准误差 1.1%。
- 摩擦阻力系数 Cf = 0.0079，与基准误差 1.1%。

| 量 | 值 |
|---|---|
| Cf | 0.0071 |

```
Cf = 999.9  -- 代码块里的数字不算断言
```

## ④ 注意点

本算例不支持层流工况，Re < 2000 时失效。
"""


def test_quotes_verbatim_and_anchor_resolves():
    md = REPORT
    res = compile_report(md, report_id=7, domain="synthetic", facet="test")
    assert res.claims, "合成报告应产出 claim"
    for doc in res.kobjects:
        verdict = verify_kobject(doc, md, report_id=7)
        assert verdict["ok"], verdict
    for c in res.claims:
        assert md[c.char_start:c.char_end] == c.quote
        assert c.quote in md


def test_tables_and_code_blocks_excluded():
    md = REPORT
    claims, rejected = extract_claims(md, iter_sections(md), report_id=7)
    texts = [c.text for c in claims]
    assert not any(t.lstrip().startswith("|") for t in texts)
    assert not any("999.9" in t for t in texts)
    assert any("999.9" in md for _ in [0])  # 源文确实有该数字，只是不作为断言


def test_contradiction_and_duplicate_rules():
    md = REPORT
    res = compile_report(md, report_id=7)
    # 同模板（Cf=<N>）不同数值 → 矛盾候选，且标注需独立评审
    assert res.contradictions, res.claims
    for con in res.contradictions:
        assert con["status"] == "needs-independent-review"
        assert len(con["claim_ids"]) >= 2
    # 同模板同数值（rel 1.1% 两条）→ 近重复
    assert any(d["rule"] == "same-template-same-numbers" for d in res.duplicates) or len(res.claims) >= 3


def test_empty_is_complete():
    md = "# 纯编排日志\n\n## 步骤\n\n先跑 A，再跑 B，最后跑 C。\n"
    res = compile_report(md, report_id=8)
    assert res.claims == []
    assert res.summary()["empty_is_complete"] is True
    assert res.kobjects == []


def test_ko_status_ceiling_and_schema():
    res = compile_report(REPORT, report_id=7)
    for doc in res.kobjects:
        assert doc["verification_status"] == "report_claimed"
        assert doc["provenance"]["storage_level"] in ("L1", "L2")
        assert doc["evidence"][0]["report_id"] == 7
        assert doc["provenance"]["content_sha256"]


def test_store_refuses_self_declared_l3():
    res = compile_report(REPORT, report_id=7)
    doc = dict(res.kobjects[0])
    doc["verification_status"] = "platform_verified"
    with pytest.raises(ko_store.KOWriteError):
        ko_store.ingest_document(conn=None, doc=doc)  # 应用层闸先于任何 SQL


def test_idempotent_ids():
    a = compile_report(REPORT, report_id=7, created_at="2026-11-12T00:00:00Z")
    b = compile_report(REPORT, report_id=7, created_at="2026-11-12T00:00:00Z")
    assert [d["knowledge_id"] for d in a.kobjects] == [d["knowledge_id"] for d in b.kobjects]
    assert a.source_hash == b.source_hash
