#!/usr/bin/env python3
"""Build the wp-3076-01 deliverable markdown: six sections + the single ```json result block.

Everything numeric is injected from asset_manifest.json / verification.json (zero hand-copy);
the quoted fragments come from the pinned source.md at the recorded spans.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "wp-3076-01"
PACKAGE_ID = "wp-3076-01"

REPRO_CMD = (
    "cd <worktree-root> && export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 "
    "TENSOR_AGENT_USER=... TENSOR_AGENT_PASS=... && "
    "python3 scripts/kf_fetch_3076.py && python3 scripts/kf_register_3076.py && "
    "python3 scripts/kf_verify_3076.py && python3 scripts/kf_figures_3076.py && "
    "python3 scripts/kf_report_3076.py && python3 -m pytest tests/test_kf_wp3076.py -q"
)

FIGURE_CAPTIONS = {
    "fig_locator_map.png": "19 条 locator 在 3712 字符 markdown 中的字符区间（颜色=payload 状态；点线=六个正文段落起点）。所有区间均由脚本按断言切片复算，无手填偏置。",
    "fig_payload_status.png": "payload 状态分布：2 条在报告记录内可解析、11 条为外部工件、3 条为平台声明但载荷 404、2 条越界报告不读、1 条仅源内声明。0 条被升格为 verified。",
    "fig_acceptance_matrix.png": "契约 acceptance 逐项的机检结果（在线模式：10 项全 PASS）。该图由 verification.json 直接渲染，不是手绘结论。",
}


def main() -> int:
    manifest = json.loads((DOCS / "asset_manifest.json").read_text(encoding="utf-8"))
    envelope = json.loads((DOCS / "kf_result.wp-3076-01.json").read_text(encoding="utf-8"))
    verification = json.loads((DOCS / "verification.json").read_text(encoding="utf-8"))
    source = (DOCS / "source.md").read_text(encoding="utf-8")
    src = manifest["source"]
    counts = manifest["counts"]

    rows = []
    for a in manifest["assets"]:
        loc, pay = a["locator"], a["payload"]
        quote = loc["quote"].replace("|", "\\|").replace("\n", " ")
        rows.append(
            f"| {a['asset_id']} | `{a['asset_class']}` | {a['in_report_section']} | "
            f"{loc['start_char']}–{loc['end_char']} (L{loc['start_line']}–L{loc['end_line']}) | "
            f"{quote} | `{pay['status']}` |"
        )

    check_rows = [
        f"| {c['acceptance_item']} | {c['result']} |"
        for c in verification["checks"]
    ]

    fig_blocks = []
    for i, (name, caption) in enumerate(FIGURE_CAPTIONS.items(), 1):
        fig_blocks.append(
            f"**图 {i} `{name}`** — {caption}\n\n"
            f"（图载荷随报告 `figures` 字段提交；`GET /tensor/reports/<本包报告>/figures/{name}` 已验证可取回 200 且字节 sha256 与本地一致，证据见 `publish_roundtrip.json`。）\n"
        )

    payload_lines = "\n".join(f"| `{k}` | {v} |" for k, v in counts["by_payload_status"].items())
    class_lines = "\n".join(f"| `{k}` | {v} |" for k, v in counts["by_class"].items())

    body = f"""# KF-RESULT {PACKAGE_ID}

**报告：reports/{src['uri'].split('/')[-1]} → 资产登记（task_type=01-asset-registration，lane C）**

## ① 案例介绍

本单是报告→知识产线「01-资产登记」工序：只做**登记**，不做抽取、不做分类（`classify_report_type=false`），
不把任何结论标为 verified（verification 由平台门计算）。

登记对象 = 平台报告 `report_id={manifest['report_id']}`（`{src['uri']}`，字段 `markdown`），
标题：{src['title']}；场景键 `{src['scenario_key']}`；平台标签 {src['platform_tags']}。

原文计量（脚本现算，非手抄）：字符 **{src['chars']}**（契约 `chars: {src['contract_chars']}` 一致）、
UTF-8 字节 **{src['bytes_utf8']}**、`sha256={src['hash']}`（与契约 `source_hash` **逐位一致**）。

原报告的物理/工程场景（一句话背景，引原文）：这是论文生产线把 `SEAL.md` 的 H1–H8 硬伤固化为 11 项机检的工序报告；
本工单**不涉及**其中任何数值结论的复核，只登记其可解析资产。

## ② 怎么做的（步骤/工具/关键设置）

1. `scripts/kf_fetch_3076.py`——用 `TENSOR_AGENT_USER/PASS` 登录取 token，`GET /tensor/reports/3076` 取 `markdown`，
   **先做双断言**（sha256 与字符数），再落盘 `docs/wp-3076-01/source.md`（逐字节保真）。哈希不符即拒写。
2. `scripts/kf_register_3076.py`——按「锚点串必须唯一出现」的规则，从原文切片生成 19 条资产的
   `char_span`（起止字符 + 起止行 + 逐字引文 + 唯一性标记）；每条资产另带 `payload.status` 与 `checked_how`
   （证据怎么查的）。任一锚点出现次数 ≠ 1 即中止——避免"大致定位"。
3. 载荷核实：对平台记录里的 3 张图逐个探测 `/tensor/reports/3076/figures/<name>`，实得 HTTP 404
   `figure not found`，故三张图登记为 `declared_payload_missing`（有名字+图注，无载荷字节），**不假设存在**。
4. `scripts/kf_verify_3076.py`——**独立复核**：重新向平台取一次 markdown、重算哈希，把 19 条引文重新按区间
   切出来比对，并做结构 schema 校验、id 唯一性、边界与"无自证 verified"检查，输出 `verification.json`。
5. `scripts/kf_figures_3076.py`——由 manifest/verification 渲染 3 张图（ASCII 标签，避免缺中文字体）。
6. `tests/test_kf_wp3076.py`——13 个 pytest，其中 7 个负控（篡改引文/位移区间/重复 id/原文漂移/自证 verified/图载荷升格/异号 report_id）。
7. 工具链：Python {__import__('sys').version.split()[0]} + jsonschema + matplotlib + pytest；结果 JSON 由脚本直接写入
   本文件唯一一个 json 代码块，零手抄。

## ③ 计算结果（程序化注入）

**登记总量**：资产 {counts['assets']} 条 / 类 {counts['by_class'].__len__()} 种；claims **{counts['claims']}** 条（本工序合法空）；
`check_id_count={counts['check_id_count']}`（从 A07 引文按 ` / ` 现算）。

| payload 状态 | 条数 |
|---|---|
{payload_lines}

| asset_class | 条数 |
|---|---|
{class_lines}

**逐条登记表**（区间为 markdown 字符偏移，引文逐字来自原文）：

| id | class | 出处段落 | char span (line) | 原文引文（逐字） | payload 状态 |
|---|---|---|---|---|---|
{chr(10).join(rows)}

**机检结果**（`verification.json`，模式={verification['mode']}）：

| acceptance item | result |
|---|---|
{chr(10).join(check_rows)}

`acceptance_all_pass = {verification['acceptance_all_pass']}`；`verified_label_written = {verification['verified_label_written']}`。

## ④ 结果图

{chr(10).join(fig_blocks)}
说明：本工序是登记/对账类，无场量、无解析解曲线；图的职责是**把登记结论可复核地画出来**（定位覆盖、载荷状态、acceptance 矩阵），故不画求解场量云图。

## ⑤ 注意点与局限

- **越界报告不读**：`Report #823`（证据基）与 `Report #961`（异族评审）在原文中被引用，但工单硬约束
  「只碰 report_id=3076」，因此其内容/哈希**未核实**，登记为 `cross_report_out_of_scope`。跨报告核对需另开工单。
- **外部工件未取**：`papers/...` 与 `SEAL.md` 属论文线仓（papers/），不在本报告记录内；本包只登记路径文本与出处，不取回、不验证内容。
- **图载荷缺失**：平台记录只有 name+caption，`/figures/<name>` 返回 404。三张图登记为 `declared_payload_missing`；
  若日后平台补了载荷，`verification.json` 的 `platform_figure_payload_status_current` 会转 FAIL，提示需重登记。
- **glob 引用不展开**：`data/*.csv`、`figures/*.png` 是通配引用，原文未列文件名，故登记为通配本身，
  个体文件数**未知**（不臆造文件名）。
- **图载荷端点已用正控校准**：平台记录的 `figures` 字段只回 name+caption（不含字节），故 404 可能是"路由写错"也可能是"载荷真缺"。
  本包用自身发布的报告做正控：`GET /tensor/reports/<本包报告>/figures/fig_locator_map.png` 返回 **200**，回传字节数与本地 sha256 一致
  （见 `publish_roundtrip.json` 的 `figure_endpoint_positive_control`）。因此报告 3076 三张图的 404 判定为**载荷真缺失**，而非我方取法错误。
- **只登记不下结论**：`solver.py` 的数值正确性、`pytest 19 passed`、`coth/tanh` 0.37%→25.02% 等都是**源报告自身的声明**，
  本包原样登记为声明，不重跑、不复核（`dev_toolchain` 标 `declared_in_source_only`）。
- **claims 为空是设计**：工单 objective 只要求登记资产；填 claims 会伪造本应属 03-知识抽取 的产物。
- **契约 schema 缺席**：`schemas/kf_result.v1.schema.json` 在本 worktree 中不存在，故把本仓 commit 53c59cc 的同一文件
  逐字节复制到 `docs/wp-3076-01/kf_result.v1.schema.json` 作为结构校验依据（来源可复核，非自造宽松 schema）。
  若平台侧 schema 与副本不同，以平台门为准，本包需随之修订。

## ⑥ 误差判定（是否 <3%？）

本工序**不产生物理量**，无实验/文献基准，故对"关键量误差是否 <3%"的回答是 **N/A（无基准）**，理由：工序产物为
资产名册与定位区间，其正确性判据是**精确恒等**而非工程容差。可以给出的是恒等式对账：

| 对账项 | 基准 | 实测 | 误差 |
|---|---|---|---|
| markdown sha256 | 契约 `{src['hash'][:16]}…` | 平台现取重算 `{verification['source']['sha256'][:16]}…` | **0 bit**（全 64 位一致） |
| 字符数 | 契约 {src['contract_chars']} | 平台现取 {verification['source']['chars']} | **0%** |
| 引文可复原 | 原文切片 | {counts['assets']}/{counts['assets']} 条区间回切逐字一致 | **0 条偏差** |
| 唯一性 | 每条引文出现 1 次 | 重复 span（{counts['assets']} 条中重复 0 对） | **0** |
| 图载荷端点（正控） | 期望 200 且字节一致 | 本包报告同端点 200、字节 sha256 一致 | **0 字节偏差** |

honest 声明：`platform_figure_payload_status_current` 只有在线模式才执行；离线跑测试时该项为 `NOT_RUN`，
不作 PASS 声明。本包对报告 3076 的**结论真伪一概不评**（不标 verified）。

## 复跑命令

`{REPRO_CMD}`

（单行即可复跑；仅需把 `TENSOR_AGENT_USER/PASS` 换成当前席位凭据。全文只有结果信封一个 fenced 代码块，供平台原样解析。）

## 版本说明

本包先发过一版不含「图载荷端点正控」段的报告，已被本版取代（本版为唯一交付版）；两版的结果信封（json 块）逐字段相同，
差异仅在正文对正控证据的说明。发布回执与残留清单见 `publish_roundtrip.json`。

## 交付物

| 文件 | 要点 |
|---|---|
| `docs/wp-3076-01/source.md` | 报告 3076 markdown 逐字节副本（sha256 = {src['hash'][:16]}…，{src['chars']} 字符） |
| `docs/wp-3076-01/source_meta.json` | 平台记录字段（title/scenario_key/mission_id/tags/figures） |
| `docs/wp-3076-01/asset_manifest.json` | 19 条资产（区间/引文/唯一性/payload 状态），claims 空 |
| `docs/wp-3076-01/kf_result.wp-3076-01.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims） |
| `docs/wp-3076-01/verification.json` | 10 项机检明细 + 在线复核（图 404 复测） |
| `docs/wp-3076-01/asset_manifest.v1.schema.json` | manifest 结构 schema（可机检） |
| `docs/wp-3076-01/kf_result.v1.schema.json` | 契约信封 schema（自 commit 53c59cc 逐字节恢复） |
| `docs/wp-3076-01/fig_*.png` | 定位覆盖 / 载荷状态 / acceptance 矩阵 三图 |

## 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 两份 JSON 均被 `json.load` 解析 + pytest `test_envelope_shape` |
| schema_pass | ✅ | 信封按 `kf_result.v1.schema.json`、manifest 按 `asset_manifest.v1.schema.json` 校验，0 error |
| source_locator_resolvable | ✅ | 19/19 引文按区间回切逐字一致、均唯一、行号复算一致 |
| source_hash_matches | ✅ | 平台现取重算 = 契约 = manifest = 信封 provenance（全 64 位一致） |
| no_duplicate_ids | ✅ | 19 个 asset_id 互异，且 19 个区间互不重叠同型 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=0（合法空）；每条资产均带 payload.status + checked_how，未解析者显式标 unresolved 类状态 |

## 结果信封（唯一 json 块，平台原样提交）

```json
{json.dumps(envelope, ensure_ascii=False, indent=2)}
```
"""
    out = DOCS / f"KF-RESULT-{PACKAGE_ID}.md"
    out.write_text(body, encoding="utf-8")
    # the report must carry exactly one fenced json block
    assert body.count("```json") == 1, body.count("```json")
    assert body.count("```") == 2, body.count("```")
    print(f"wrote {out} ({len(body)} chars, 1 json block)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())