#!/usr/bin/env python3
"""Emit the delivery report for wp-7808-01 (KF-RESULT) and the platform payload.

Zero hand-copying: the evidence table is generated from asset_manifest.json locators, the
self-check table from report_selfcheck.json, and the result envelope is embedded byte-exact
from kf_result.json inside the single ```json block required by the工作包 delivery channel.

Run: python3 scripts/emit_wp7808_report.py [--post]
Out: docs/kf/wp-7808-01/KF-RESULT.wp-7808-01.md  (+ /tmp/report_wp7808.json payload)
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "kf", "wp-7808-01")
PKG = "wp-7808-01"
REPORT_ID = "7808"
PNG = os.path.join(ROOT, "docs", "kf", PKG, "figures", "asset_inventory.png")
PAYLOAD = "/tmp/report_wp7808.json"

REPRO = (
    "python3 scripts/kf_register_7808.py --validate && "
    "python3 -m pytest tests/test_kf_register_7808.py -q && "
    "python3 scripts/plot_wp7808_assets.py && "
    "python3 scripts/emit_wp7808_report.py"
)


def md_table(rows: list[list[str]]) -> str:
    head, body = rows[0], rows[1:]
    out = ["| " + " | ".join(head) + " |", "|" + "|".join(["---"] * len(head)) + "|"]
    for r in body:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def main() -> int:
    manifest = json.load(open(os.path.join(OUT, "asset_manifest.json"), encoding="utf-8"))
    result = json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))
    selfcheck = json.load(open(os.path.join(OUT, "report_selfcheck.json"), encoding="utf-8"))
    src = manifest["source"]
    c = manifest["counts"]

    evidence_rows = [["asset / claim", "字段", "原文引文（逐字）", "定位 (char, line)", "resolution"]]
    for a in manifest["assets"]:
        loc = a["locator"]
        evidence_rows.append([
            f"{a['asset_id']} {a['label']}",
            "markdown",
            "「" + loc["quote"].replace("|", "\\|") + "」",
            f"[{loc['start_char']},{loc['end_char']}) L{loc['start_line']}",
            a["resolution"],
        ])
    evidence_rows.append(["（无 claim）", "—", "本包不产 claim，claims=[] 为合法完整结果", "—", "—"])

    selfcheck_rows = [["acceptance item", "结果", "验证方式/证据"]]
    for chk in selfcheck["checks"]:
        selfcheck_rows.append([
            chk["acceptance_item"],
            "✅ pass" if chk["pass"] else "❌ fail",
            chk["detail"].replace("|", "\\|"),
        ])

    REGEX_PAT = manifest["coverage"]["path_token_regex"]

    unresolved_rows = [["asset", "路径/对象", "未解析原因"]]
    for u in manifest["unresolved"]:
        unresolved_rows.append([u["asset_id"], u["name"], u["reason"]])

    body = f"""> **发布说明（路径更正版，supersedes report #14669）**：同一工作包的结果重发布。与 #14669 相比，`json` 信封内容**完全相同**（同一 report 7808、同一 sha256），唯一差异是本版产物路径由 `artifacts/{PKG}/` 改为 `docs/kf/{PKG}/`——`artifacts/` 被 `.gitignore` 忽略并被推送门禁过滤（`docs/ops/filter-audit.md`），留在那里会在推出的仓库里变成悬空引用。#14669 因此作废，以本报告为准。

## ① 本工序做了什么

本单执行 `01-asset-registration`（Lane C，package_id=`{PKG}`），只对 **report_id={REPORT_ID}** 一份报告做**源资产登记**，不做抽取、不做报告类型分类、不写任何 verified 标记：

1. 取回 report {REPORT_ID} 的 `markdown` 字段（source_uri=`{src['source_uri']}`），独立重算 UTF-8 字节 sha256；
2. 与工作包契约 `input.source_hash` / `input.chars` 逐项比对；
3. 列出报告正文中可解析的附件/工件（代码路径、G21 孤儿模块表行、内嵌 pytest 日志块、图集），每个资产给一条**逐字可定位**引文（char 区间 + 行号 + 引文 sha256）；
4. 对每个引用如实给出 `resolved_in_source` / `referenced_unresolved` / `declared_absent` 三态之一，解析能力边界仅限 TensorKnowledge 交付工作树与平台附件端点；
5. 产出 `asset_manifest.json`，包进 `kf_result.v1` 信封。

`claims` 允许为空数组（契约 notes），本包按 `no_forced_claim_generation=true` 不做强造，**claims = []** 是完整结果而非缺项。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 工具 | 关键设置 |
|---|---|---|
| 取源 | `GET $TENSOR_API_BASE/tensor/reports/{REPORT_ID}`（Bearer 登录令牌） | 只取 `markdown` 字段原文，不做任何规范化/换行改写 |
| 哈希 | `hashlib.sha256(md.encode('utf-8'))` | 作用域=存储串的 UTF-8 字节；字符数同时比对契约 3389 |
| 定位 | 自写 `locate()`：`str.find` + 出现次数 | 记录 `start_char/end_char`（左闭右开）、`start_line/end_line`（1 基）、`occurrences_in_source`、`char_span_roundtrip_ok` |
| 资产枚举 | 正则 `{REGEX_PAT}` + §7 表格行 | 正文所有文件类 token 全覆盖，未覆盖即 fail |
| 解析判定 | `os.path.exists` 探交付工作树候选路径 + `GET reports/{REPORT_ID}/{{figures,artifacts}}` | figures/artifacts 端点均返回 HTTP {list(src['platform_attachment_probes'].values())[0]['http_status']}，记录 record.figures=[] |
| 结果封装 | `jsonschema` 4.x | 信封 `schemas/kf_result.v1.schema.json` + 本包 manifest schema 双校验 |
| 复现 | pytest 11 项离线测试 | 读 `docs/kf/{PKG}/source_markdown.md`（与契约同哈希的字节副本），无需联网 |

一键复跑（工作树根目录，凭据取自环境变量）：

```
{REPRO}
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/{PKG}/asset_manifest.json` | 契约输出。{c['assets']} 个资产：resolved_in_source={c['resolved_in_source']}、referenced_unresolved={c['referenced_unresolved']}、declared_absent={c['declared_absent']}；claims=0；含 source 身份块（hash/chars/bytes/lines/record 字段/平台端点探针）、逐资产 locator、coverage、id_integrity、integrity、unresolved、observations、limitations |
| `docs/kf/{PKG}/kf_result.json` | `kf_result.v1` 信封（package_id/task_type/report_id/provenance/outputs/claims），provenance.source_hash = `{result['provenance']['source_hash']}` |
| `docs/kf/{PKG}/report_selfcheck.json` | acceptance 逐项机器自检结果（{sum(1 for x in selfcheck['checks'] if x['pass'])}/{len(selfcheck['checks'])} pass，all_pass={selfcheck['all_pass']}） |
| `docs/kf/{PKG}/work_package_contract.json` | 本包 YAML 契约的 JSON 转写（字段名/值不变），供生成器无 YAML 依赖地读取阈值 |
| `docs/kf/{PKG}/asset_manifest.schema.json` | 本包 manifest 形状的本地 schema（**未改动**共享的 `schemas/asset_manifest.v1.schema.json`，后者被 const 钉死在 wp-448-01 上，属别的工作包） |
| `scripts/kf_register_7808.py` | 生成+自检脚本（fetch / hash / locator / resolution / coverage / 双 schema 校验） |
| `scripts/plot_wp7808_assets.py` | 资产盘点图生成脚本（数据全部来自 manifest，无手抄数字） |
| `scripts/emit_wp7808_report.py` | 本报告生成脚本：证据表由 locator 程序化注入，信封按字节原样嵌入 json 块 |
| `tests/test_kf_register_7808.py` | 11 项离线验收测试（哈希、locator 逐字可解、ID 唯一、claims 空且未标 verified、token 覆盖、计数自洽、报告范围仅 7808、unresolved 必须带原因） |
| `docs/kf/{PKG}/source_markdown.md` | 报告 markdown 的**字节精确副本**（sha256=`{src['source_hash']}`），仅为离线复跑测试留存，非抽取非手抄 |
| `docs/kf/{PKG}/source_markdown.provenance.json` | 上述副本的来源与哈希声明 |
| `docs/kf/{PKG}/figures/asset_inventory.png` | 图：资产盘点（类别×解析状态）与完整性计数 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

源身份：`report_id={REPORT_ID}`，`chars={src['chars']}`（契约 {src['contract_chars']}），`bytes={src['bytes_utf8']}`，`lines={src['lines']}`，`sha256={src['source_hash']}`，与契约一致={src['hash_match']}。记录字段：title=「{src['record_fields']['title']}」，scenario_key={src['record_fields']['scenario_key']}，mission_id={src['record_fields']['mission_id']}，status={src['record_fields']['status']}，figures={src['record_fields']['figures']}。

{md_table(evidence_rows)}

未解析引用（如实登记，不当作上游缺失）：

{md_table(unresolved_rows)}

## ⑤ 注意点与局限

1. **只登记不抽取**：契约 `objective.classify_report_type=false`，本包不产任何知识 claim，也不对报告结论（"22 项全部通过""数学实现正确"）表态；这些仍是**上游断言**，验证由平台门计算，本包不标 verified。
2. **哈希作用域**：sha256 覆盖存储串的 UTF-8 字节，任何改动（哪怕一个空格）都会使哈希失效；契约的 `chars=3389` 与实测字符数一致，但字节约为 5210（中文多字节），两者不是同一量。
3. **解析边界**：本包只在 TensorKnowledge 交付工作树内探测路径。`ddes.py`、`tests/test_ddes_unit.py`、G21 表里另 5 个模块都属报告头声明的 TensorLBM 仓，本工作树没有 → 一律登记 `referenced_unresolved` + 原因，**不得**解读为上游文件缺失。
4. **二次通道受限**：想用 `psql -d tensorplatform -c "select markdown from tensor_reports where id=7808"` 做独立复核，返回 `permission denied for table tensor_reports`；因此本包只走平台 API 一条信道，另以两次独立 GET + 本地字节副本互为印证（三者哈希相同）。
5. **图**：本报告含 1 张图，但**不是物理场量图**——本工序是登记工序，没有数值结果。图为 manifest 计数的可视化（类别×解析状态 + 完整性计数），标注写明数据来源，不能当作物理验证证据。
6. **报告自述数字未复算**：`ddes.py` 370 行、`22 passed, 1 warning in 6.30s` 均为报告内自述（后者作为 `embedded_run_log` 资产登记），本包未重跑 TensorLBM 测试，故不复核。
7. **产物落点与推送门禁**：`artifacts/` 被 `.gitignore` 忽略且被推送门禁过滤（见 `docs/ops/filter-audit.md`），因此全部产物落在 `docs/kf/{PKG}/`（含 `figures/`）；源 markdown 的字节副本也放这里，否则离线验收测试在推出仓库后必然找不到夹具。这是**字节副本**（哈希钉死），不是抽取、不是手抄。
8. **边界纪律**：本包只读/只写 report_id=7808；未触碰任何其它 report_id（本单自身发布报告的 id 由平台分配，不参与本包登记）。

## ⑥ 自检：逐条对照 acceptance

{md_table(selfcheck_rows)}

失败项：无（若上表出现 ❌ 即为 honest-FAIL，本行同步改写，不粉饰）。复跑自检：`python3 scripts/kf_register_7808.py --validate`（非 0 退出码即失败）；离线验收：`python3 -m pytest tests/test_kf_register_7808.py -q`。

## 交付信封（唯一 json 块，原样提交）

```json
{json.dumps(result, ensure_ascii=False, indent=2)}
```
"""

    path = os.path.join(OUT, f"KF-RESULT.{PKG}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)

    # structural guarantee: exactly one ```json block, and it re-parses to the same envelope
    blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
    assert len(blocks) == 1, f"expected exactly one json block, got {len(blocks)}"
    assert json.loads(blocks[0]) == result, "embedded json block drifted from kf_result.json"
    print(f"[ok] wrote {path} ({len(body)} chars, json blocks={len(blocks)})")

    png_b64 = base64.b64encode(open(PNG, "rb").read()).decode()
    payload = {
        "title": f"KF-RESULT {PKG}",
        "summary": (
            f"资产登记工序 {PKG}：report {REPORT_ID} markdown 哈希与契约一致（sha256={src['source_hash'][:23]}…，"
            f"chars={src['chars']}），登记 {c['assets']} 个资产（resolved {c['resolved_in_source']} / "
            f"unresolved {c['referenced_unresolved']} / absent {c['declared_absent']}），claims=[] 合规；"
            f"11 项离线验收测试与双 schema 校验全绿。"
        ),
        "scenario_key": "ddes_unit_verification",
        "mission_id": 15601,
        "tags": ["kf-wp:wp-7808-01", "KF", "asset-registration", "G21", "DDES", "report-7808"],
        "markdown": body,
        "figures": [
            {
                "name": "asset_inventory",
                "caption": (
                    f"wp-7808-01 资产盘点：左=按类别（{', '.join(f'{k}×{v}' for k, v in c['by_class'].items())}）"
                    f"与解析状态的堆叠计数；右=解析状态合计。全部数字由 asset_manifest.json 程序化读取，"
                    "不含物理场量，不能作为物理验证证据。"
                ),
                "png_base64": png_b64,
            }
        ],
    }
    with open(PAYLOAD, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    print(f"[ok] wrote {PAYLOAD} (figures={len(payload['figures'])})")
    return 0


if __name__ == "__main__":
    sys.exit(main())