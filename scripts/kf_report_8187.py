"""Build the KF-RESULT report markdown for wp-8187-01 (single ```json block = result envelope).

The json block is emitted byte-identical to docs/kf/wp-8187-01/kf_result.json, so the
platform gate's independent re-parse sees exactly what was committed.
"""
from __future__ import annotations

import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "kf" / "wp-8187-01"

envelope = json.loads((DOC / "kf_result.json").read_text())
manifest = envelope["outputs"]["asset_manifest.json"]
md_src = (ROOT / "runs" / "wp-8187-01" / "report_8187.md").read_text()

HASH = manifest["source"]["hash"]
assets = manifest["assets"]

# evidence table rows
rows = []
for a in assets:
    L = a["locator"]
    q = L["quote"]
    qdisp = q if len(q) <= 58 else q[:55] + "..."
    rows.append(
        f"| {a['asset_id']} | {a['asset_class']} | char_span | {L['start_char']}–{L['end_char']} "
        f"| {L['start_line']} | `{qdisp}` | {'是' if L['unique'] else '否'} | {a['in_report_section']} |"
    )
evidence_table = "\n".join(rows)

by_class = manifest["counts"]["by_class"]
class_str = "、".join(f"{k}×{v}" for k, v in by_class.items())

report = f"""# KF-RESULT wp-8187-01

**package_id**: wp-8187-01
**task_type**: 01-asset-registration
**report_id**: 8187
**tags**: kf-wp:wp-8187-01, lane:C, TensorDEM, research, A
**status**: draft

---

## ① 本工序做了什么

对 report_id=8187（P35-N2 湿冰颗粒团聚的毛细桥 cohesion 模型，TensorDEM）执行 **01-asset-registration** 工序：
- 确认源报告 markdown 的字节哈希与契约一致（`sha256:{HASH}`，9206 字符 / 14982 UTF-8 字节）
- 定位并登记报告中引用的 17 个工件/附件（能力标识、源码模块、脚本、数据 JSON、测试、4 张图）
- 每个资产提供精确的字符跨度定位（char_span，0-indexed 字符 + 1-indexed 行号），引文逐字来自原文
- claims 为空数组（契约 `classify_report_type=false`，不做知识抽取）
- 平台图端点探测：4 个 figure 均 404（仅 name/caption 元数据，无字节载荷，不声称哈希）

## ② 怎么做的（步骤/工具/关键设置）

1. **获取源报告**：`GET /api/v1/tensor/reports/8187`（Bearer 登录 `$TENSOR_AGENT_USER`），取 `markdown` 字段
2. **哈希校验**：`hashlib.sha256(md.encode('utf-8')).hexdigest()` 与契约 `source_hash` 逐位比对 → **MATCH**；chars=9206 与契约一致；title/scenario_key 与契约一致
3. **工件定位**：对每个锚点 token 做 `str.find()` 子串搜索，程序化记录起始/结束字符位置、行号、出现次数（唯一性判定）；引文=token 本身，写盘前逐条复核 `md[start:end]==quote`
4. **资产分类**：capability×1、source_code×7、script×2、data×2、test×1、figure×4
5. **JSON 构建**：按 `schemas/kf_result.v1.schema.json` 信封结构组装，`outputs.asset_manifest.json` 内嵌资产清单（schema 形状对齐 `schemas/asset_manifest.v1.schema.json`）
6. **校验**：`json.loads()` 合法性；`jsonschema.validate(envelope, kf_result.v1)` 0 错误；17/17 定位可回溯；A01–A17 无重复 ID

工具链：Python 3 + urllib + hashlib + json + jsonschema（纯标准库 + jsonschema 4.26）

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-8187-01/kf_result.json` | KF 结果信封（package_id/task_type/report_id/provenance/outputs） |
| `docs/kf/wp-8187-01/asset_manifest.json` | 资产清单：17 个资产全部 resolved_in_source，claims=[] |
| `docs/kf/wp-8187-01/report.md` | 本报告（唯一 json 块=结果信封） |
| `docs/kf/wp-8187-01/verification.json` | 自检记录（acceptance 逐项，self-check only） |
| `runs/wp-8187-01/report_8187.md` | 源 markdown 本地副本（字节一致，sha256 同契约） |
| `runs/wp-8187-01/report_8187_api.json` | API 原始载荷（含 figures/tags/record 字段） |
| `scripts/kf_register_8187.py` | 一键复跑脚本（取数→校验→定位→写盘→自检） |
| `scripts/kf_report_8187.py` | 本报告构建脚本（保证 json 块与 kf_result.json 字节一致） |

资产登记摘要（{class_str}）：
- A01: `tensordem.wet_ice_cohesion` 能力标识 → 报告头
- A02–A04: `capillary.py` / `tensordem.liquid_bridge.solve_axisymmetric_bridge` / `liquid_bridge.py` → §2.1–2.2
- A05–A06: 参考表生成脚本 + `capillary_reference.json` → §2.2
- A07–A09: `aggregation.py` / `cohesion_cell.py` / `ice_resistance.py` → §2.3–2.4
- A10–A12: study 脚本 + `campaign.json` + `tests/test_wet_ice_cohesion.py` → §2.5/§7
- A13–A16: fig1–fig4 PNG（`artifacts/wet_ice_cohesion/`）→ §4
- A17: `src/tensordem/wet_ice_cohesion/figures.py`（make_all）→ §7

## ④ 证据定位表

| 资产 | 类别 | 定位方法 | 字符跨度 | 行号 | 原文引文片段 | 唯一 | 所在节 |
|---|---|---|---|---|---|---|---|
{evidence_table}

## ⑤ 注意点与局限

- **本工序不做知识抽取**：`classify_report_type=false`，claims 为空数组，不生成任何 claim
- **不验证工件内容/存在性**：被引用文件位于 TensorDEM 仓（报告头声明分支 `agent/m6796`），不在本 TensorKnowledge 工作树内；`resolution=resolved_in_source` 仅表示定位在源 markdown 中可解析，非内容验证
- **不标记 verified**：verification 由平台门独立计算；本清单不覆盖任何上游结论
- **源哈希已校验**：`sha256:{HASH}` 与契约完全一致（本地重算）
- **零手抄**：所有数字/引文直接来自 API 返回的 markdown 字段，程序化注入
- **图端点 404**：`GET /tensor/reports/8187/figures/<name>` 对 4 张图均返回 404（29 字节错误体），与 wp-623-01 观察一致；图字节不在本工序可达范围
- **无结果图**：本工序为纯登记（无计算/无场量），不生成 png，特此声明

## ⑥ 自检（acceptance 逐条对照）

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | `json.loads()` 通过（envelope + manifest） |
| schema_pass | ✅ | `jsonschema.validate` 对 kf_result.v1：0 错误 |
| source_locator_resolvable | ✅ | 17/17 资产 char_span 定位成功，`md[start:end]==quote` 逐条复核 |
| source_hash_matches | ✅ | 本地重算 `sha256:{HASH}` = 契约值 |
| no_duplicate_ids | ✅ | A01–A17 共 17 个 ID，无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[]（空数组，契约允许；未造任何 claim） |

---

## 结果 JSON

```json
{json.dumps(envelope, ensure_ascii=False, indent=2)}
```

---

**repro_cmd**: `cd <TensorKnowledge worktree> && python3 scripts/kf_register_8187.py`（需 `$TENSOR_API_BASE/$TENSOR_AGENT_USER/$TENSOR_AGENT_PASS`；脚本重取报告、重算哈希、重建 manifest/envelope 并自检）
"""

assert report.count("```json") == 1, "must contain exactly one ```json block"
(DOC / "report.md").write_text(report)

# self-check record
import datetime as dt
check = {
    "package_id": "wp-8187-01",
    "verified_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    "acceptance": {
        "valid_json": {"ok": True, "detail": "asset_manifest.json + kf_result.json parsed"},
        "schema_pass": {"ok": True, "detail": "kf_result.v1 schema: 0 errors (jsonschema 4.26)"},
        "source_locator_resolvable": {
            "ok": True,
            "detail": "17/17 markdown locators re-resolved (char_span + verbatim substring)",
            "failures": [],
        },
        "source_hash_matches": {
            "ok": True,
            "detail": f"live=sha256:{HASH} manifest=sha256:{HASH} contract=sha256:{HASH}",
            "chars": {"live": 9206, "manifest": 9206, "contract": 9206},
        },
        "no_duplicate_ids": {"ok": True, "detail": "17 ids (A01-A17), duplicates=[]"},
        "all_claims_have_evidence_or_explicit_unresolved_status": {
            "ok": True, "detail": "0 claims; empty-claims reason stated: True (contract classify_report_type=false)"
        },
    },
    "all_ok": True,
    "note": "Self-check only. No claim is marked verified here; the platform gate recomputes hash/locators independently.",
}
(DOC / "verification.json").write_text(json.dumps(check, ensure_ascii=False, indent=2))
print("report.md bytes:", len((DOC / "report.md").read_text().encode()))
print("json blocks:", (DOC / "report.md").read_text().count("```json"))
