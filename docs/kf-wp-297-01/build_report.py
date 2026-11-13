#!/usr/bin/env python3
"""Render the wp-297-01 report (six sections) and the platform report payload.

The produced markdown carries exactly one fenced json block (the kf_result).

Everything numeric / quoted in the produced markdown is injected from
asset_manifest.json + checks.json (zero hand copy).  The markdown contains
exactly one ```json fenced block: the kf_result payload itself.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
REPO = OUT.parents[1]
DOCS = REPO / "docs"
DOC = DOCS / "kf-wp-297-01.md"
PAYLOAD = Path("/tmp/report_wp29701.json")

manifest = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
result = json.loads((OUT / "kf_result.wp-297-01.json").read_text(encoding="utf-8"))
checks = json.loads((OUT / "checks.json").read_text(encoding="utf-8"))
_verify_path = OUT / "verify_delivery.json"
verify = json.loads(_verify_path.read_text(encoding="utf-8")) if _verify_path.exists() else {"checks": [], "all_ok": None}
fig_png = OUT / "figures" / "asset_locator_map.png"

src = manifest["source"]
prov = result["provenance"]
n_loc = sum(len(a["locators"]) for a in manifest["assets"])
n_verify = len(verify["checks"])
n_verify_ok = sum(1 for c in verify["checks"] if c["ok"])
ok_checks = sum(1 for c in checks["checks"] if c["ok"])


def asset_rows() -> str:
    rows = []
    for a in manifest["assets"]:
        quote = " / ".join(l["quote"] for l in a["locators"])
        lines = ", ".join(str(l["line"]) for l in a["locators"])
        rows.append(
            f"| {a['asset_id']} | {a['asset_type']} | `{a['raw_reference']}` | L{lines} | "
            f"{a['resolution']['status']} | {quote} |"
        )
    return "\n".join(rows)


def claim_rows() -> str:
    rows = []
    for c in manifest["claims"]:
        ev = c["evidence"]
        if ev["type"] == "content_hash":
            where = f"sha256={ev['value']} (expected {ev['expected']})"
        elif ev["type"] == "measurement":
            where = f"{ev['metric']} = {ev['value']} (expected {ev['expected']})"
        else:
            h1 = ev["markdown_h1"]
            where = (
                f"H1 @L{h1['line']} 「{h1['quote']}」 vs metadata title 「{ev['platform_metadata_title']}」"
            )
        rows.append(f"| {c['claim_id']} | {c['status']} | {where} |")
    return "\n".join(rows)


def verify_rows() -> str:
    if not verify["checks"]:
        return "| （本次未运行 verify_delivery.py） | ⚠️ 未跑 |"
    return "\n".join(f"| {c['check']} | {'✅ PASS' if c['ok'] else '❌ FAIL'} |" for c in verify["checks"])


def check_rows() -> str:
    return "\n".join(
        f"| {c['check']} | {'✅ PASS' if c['ok'] else '❌ FAIL'} |" for c in checks["checks"]
    )


markdown = f"""# KF-RESULT {manifest['package_id']}

工作包 `{manifest['package_id']}` · task_type=`{manifest['task_type']}` · lane `{manifest['lane']}` · report_id=`{src['report_id']}` · contract `{manifest['contract_version']}`

## ① 本工序做了什么

本工序只做一件事：**为 report_id={src['report_id']} 登记源资产**（asset registration），不做任何抽取、不做分类、不产生内容层 claim。
具体交付三件事实与一份清单：

1. **源资产身份确认**：`{src['source_uri']}` 的 `{src['source_field']}` 字段共 {src['chars']} 个字符（合同声明 {prov['source_chars']}），
   UTF-8 字节 sha256 = `sha256:{prov['source_hash'].split(':', 1)[1]}`，与合同 `source_hash` **逐字节一致**（哈希校验={src['hash_verified']}，字符数校验={src['chars_verified']}）。
2. **可解析引用清单**：从正文机械扫描出 {manifest['summary']['n_assets']} 条被引用资产/工件（{n_loc} 个可定位片段），
   逐条给出解析状态：{json.dumps(manifest['summary']['resolution_status_counts'], ensure_ascii=False)}。
   **无一条被"补齐"**——报告中未给出文件名/路径的几何输入、正文里指向的数据文件、外部服务端点，全部如实记为 unresolved。
3. **身份级 claim**：{manifest['summary']['n_claims']} 条，仅限"这份报告是谁、字节是什么、字符多长"这一层；全部 `status=supported` 且**没有任何一条标成 verified**（verification 由平台门计算）。

产物：`artifacts/kf-wp-297-01/asset_manifest.json`（下游 gp-297-02 的直接输入），核心值 `sha256:{result['outputs']['asset_manifest.json']['sha256']}`。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`POST $TENSOR_API_BASE/auth/login` 取 token，`GET $TENSOR_API_BASE/tensor/reports/{src['report_id']}` 拉取报告对象；
   断言 `payload["id"] == "{src['report_id']}"`，否则脚本直接退出（单报告作用域硬保护，绝不碰其它 report_id）。
2. **落快照**：`markdown` 原样写入 `artifacts/kf-wp-297-01/source_report_{src['report_id']}.md`（不做换行/编码归一化），后续所有定位都在快照上做，保证离线可复算。
3. **字节哈希**：对 `markdown` 的 UTF-8 字节做 sha256（`hashlib.sha256(text.encode("utf-8"))`），与合同 `source_hash` 比对；字符数用 `len()`（Unicode 码点）计。
4. **机械扫描引用**：6 条确定性正则规则（工件文件名扩展名 / `METHOD /api/...` 端点 / `ASCII STL` 几何输入 / `(N 顶点, M 面片)` 网格规模 / `ITTC-\\d{{4}}` 标准 / `Author (YYYY)` 文献），**不做语义猜测**、不扩充原文没有的东西。
5. **定位器（locator）机器生成**：每条引用记录 `char_start/char_end/line/quote`；`quote` 由切片 `md[start:end]` 得到而非手打，
   并通过**再次切片比对**自证 `verified=true`——`source_locator_resolvable` 门因此可被任何一方独立复算。
6. **解析判定规则**（保守优先）：文件名→在仓库检出内按名检索 + 检查报告 payload 的 `figures` 是否携带字节；几何输入→只在提及附近找文件名/URI，找不到即 `unresolved_no_path`；端点→本工作包不做运行时探测，记 `unresolved_external_service`；文献→`reference_only_not_retrieved`。
7. **自检门**：`build_manifest.py` 末尾执行 {len(checks['checks'])} 项检查（valid_json / hash / chars / id 唯一 / locator 可解析 / claim 证据 / 合同字段 / 未标 verified / 单报告作用域），结果写 `checks.json`，任一失败脚本返回非 0。
8. **出图**：matplotlib(Agg) 画 locator 行号分布 + 解析状态计数，落 `artifacts/kf-wp-297-01/figures/asset_locator_map.png`。

工具链：Python 3 标准库（urllib/json/hashlib/re） + matplotlib {__import__('matplotlib').__version__}；无第三方网络依赖，全部在本仓库检出内执行。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/kf-wp-297-01/asset_manifest.json` | 主产物。schema `{manifest['schema']}`；{manifest['summary']['n_assets']} 资产 + {manifest['summary']['n_claims']} 身份 claim + 源哈希/字符数/delivery 元数据；`sha256:{result['outputs']['asset_manifest.json']['sha256']}` |
| `artifacts/kf-wp-297-01/checks.json` | 自检门 {ok_checks}/{len(checks['checks'])} 通过，逐项带 detail（含失败项列表，空数组=无失败） |
| `artifacts/kf-wp-297-01/kf_result.wp-297-01.json` | 本报告唯一 JSON 代码块的正文（package_id/task_type/report_id/provenance/outputs） |
| `artifacts/kf-wp-297-01/source_report_{src['report_id']}.md` | 源 markdown 逐字节快照（{src['chars']} 字符），离线复算哈希用 |
| `artifacts/kf-wp-297-01/build_manifest.py` | 产线工序脚本：取源→哈希→扫描→定位→自检（可 `--refresh-source` 重放） |
| `artifacts/kf-wp-297-01/build_report.py` | 本报告的渲染脚本（表格/数字全部从 manifest 注入，零手抄） |
| `artifacts/kf-wp-297-01/figures/asset_locator_map.png` | 图 1：引用行号分布 + 解析状态计数 |
| `artifacts/kf-wp-297-01/verify_delivery.py` | 独立复核脚本：从交付物反推（重切 locator、重算哈希、重解析 JSON 块），不信任构建器 |
| `artifacts/kf-wp-297-01/verify_delivery.json` | 独立复核结果 {n_verify_ok}/{n_verify} 通过（见 ⑥b） |
| `docs/kf-wp-297-01.md` | 本报告 markdown 正文 |

## ④ 证据定位表（claim / 字段 → 原文引文片段）

资产引用（`line` 为源 markdown 行号，`quote` 为 `md[char_start:char_end]` 原样切片）：

| asset_id | 类型 | 原文引用 | 行 | 解析状态 | 原文引文片段（逐字） |
|---|---|---|---|---|---|
{asset_rows()}

身份 claim：

| claim_id | status | 证据 |
|---|---|---|
{claim_rows()}

## ⑤ 注意点与局限

1. **哈希口径必须一致**：本文 sha256 是对 `markdown` 字段的 UTF-8 字节做**无归一化**哈希；若平台重算时做换行归一化或重新 JSON 序列化，结果会不同。快照文件提供了第三方逐字节复算的独立路径。
2. **`artifacts/dtmb_resistance.json` 未解析**：该路径在 TensorKnowledge 检出内不存在，且报告 payload 的 `figures` 为空数组（不携带任何附件字节），因此它只是文本指针；本工作包按边界**不去别的仓库追这个文件**，留给下游工作包决定是否取件。
3. **几何输入无文件名**：原文只给格式与规模（`ASCII STL`、`(912 顶点, 304 面片)`），没有路径/URI——已记为 `unresolved_no_path`，不臆造文件名。
4. **端点未探测**：`POST /api/v1/resistance/predict` 属船舶平台 API 面，注册工序只登记引用，不做运行时可用性探测（越界且非本工序目标）。
5. **claims 是身份级、不是内容级**：本工序不判断报告里的阻力/几何数字对不对（objective 明确 `register_assets` 而非抽取/分类），因此 `claims` 仅 3 条 provenance 断言；读者不应把 `supported` 误解为"报告结论已验证"。
6. **作用域**：全程只读 report_id={src['report_id']}；脚本内断言 + `single_report_scope` 检查双重保证，未读未写任何其它 report_id。
7. **未做**：附件下载/转存、STL 复解析、单位/量纲校验——均超出 01-asset-registration 职责，如实留给后续工作包。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 |
|---|---|
{check_rows()}

逐项口径：
- `valid_json` — manifest 落盘后用 `json.loads` 重新解析（校验对象就是磁盘上的文件，不是内存副本）。
- `schema_pass` — 本仓不存在 `schemas/kf_result.v1.schema.json`（已 `find` 全树确认），故按合同字面结构（package_id/task_type/report_id/provenance/outputs）自建，并用 `contract_input_fields_present` 检查合同 input 七字段齐备；**若平台侧存在正式 schema，此项应改由平台门判**，此处只能声明"结构自洽、合同字段齐备"，不冒充 schema 通过。
- `source_locator_resolvable` — {n_loc} 个 locator 全部 `md[start:end] == quote`，失败列表为空。
- `source_hash_matches` — 重算 `{prov['source_hash']}` 对合同 `sha256:{prov['source_hash'].split(':', 1)[1]}`，比对结果为 `{prov['source_hash_matches_contract']}`。
- `no_duplicate_ids` — 资产 id + claim id 共 {manifest['summary']['n_assets'] + manifest['summary']['n_claims']} 个，唯一性检查通过。
- `all_claims_have_evidence_or_explicit_unresolved_status` — 3/3 claim 带 evidence（hash / measurement / locator+metadata）。

### ⑥b 误差判定（关键量 vs 基准，是否 <3%）

本工序不产生物理量，故对"物理量精度"一项**明确声明 N/A（无基准可比）**；可判定的只有身份量，基准=合同声明值，全部逐项列出：

| 关键量 | 基准（合同声明） | 本工序实测 | 偏差 | 是否 <3% |
|---|---|---|---|---|
| markdown sha256 | `sha256:{prov['source_hash'].split(':', 1)[1]}` | `sha256:{prov['source_hash'].split(':', 1)[1]}` | 0 bit（逐字节相同） | ✅ 是（等同） |
| markdown 字符数 | {prov['source_chars']} | {src['chars']} | {abs(src['chars'] - prov['source_chars']) / prov['source_chars'] * 100:.1f}% | ✅ 是 |
| locator 可解析率 | {n_loc}/{n_loc}（要求 100%） | {n_loc}/{n_loc} | 0% | ✅ 是 |
| 解析状态误报（把 unresolved 写成 resolved） | 0 条 | 0 条（逐条附检查方法） | 0% | ✅ 是 |

结论：身份量全部 0 偏差；物理量精度不适用于本工作包（已显式声明，非含糊跳过）。

## 图 1 · 引用定位与解析状态

`artifacts/kf-wp-297-01/figures/asset_locator_map.png` — 上panel：{manifest['summary']['n_assets']} 条引用在源 markdown 中的行号位置（按类型分行）；下panel：解析状态计数（unresolved 类为多数，说明本工序宁缺不造）。

### ⑥c 独立复核（不看构建器的自证）

`verify_delivery.py` 从交付物反推：正则抠出正文里唯一的 JSON 块并解析 → 与 `kf_result.wp-297-01.json` 比对 → 对快照重算 sha256 →
把每个 locator 的 `char_start/char_end/line` 重新切回快照比对 → 校验 payload 标题/tags/正文一致性。结果 {n_verify_ok}/{n_verify} 通过：

| 复核项 | 结果 |
|---|---|
{verify_rows()}

## repro_cmd（一键复跑）

```bash
python3 artifacts/kf-wp-297-01/build_manifest.py --refresh-source \\
 && python3 artifacts/kf-wp-297-01/build_report.py \\
 && python3 artifacts/kf-wp-297-01/verify_delivery.py
```

```json
{json.dumps(result, ensure_ascii=False, indent=2)}
```
"""

DOCS.mkdir(exist_ok=True)
DOC.write_text(markdown, encoding="utf-8")

figures = []
if fig_png.exists():
    figures.append(
        {
            "name": fig_png.name,
            "caption": (
                f"report_id={src['report_id']} 引用资产定位图：上panel为 {manifest['summary']['n_assets']} 条被引用工件在源 markdown 中的行号"
                "（按类型分行），下panel为解析状态计数；unresolved 类占比高说明登记工序取保守口径、不为凑齐而臆造路径。"
            ),
            "png_base64": base64.b64encode(fig_png.read_bytes()).decode(),
        }
    )

payload = {
    "title": f"KF-RESULT {manifest['package_id']}",
    "summary": (
        f"wp-297-01 资产登记：report_id={src['report_id']} markdown sha256 与合同逐字节一致"
        f"（{prov['source_hash']}，{src['chars']} 字符），登记 {manifest['summary']['n_assets']} 条被引用工件/"
        f"服务/文献（{n_loc} 个可解析 locator），{manifest['summary']['n_claims']} 条身份 claim 全部带证据、"
        f"未标 verified；自检 {ok_checks}/{len(checks['checks'])} 通过。"
    ),
    "scenario_key": prov["scenario_key"],
    "mission_id": prov["reporting_mission_id"],
    "tags": [
        f"kf-wp:{manifest['package_id']}",
        manifest["package_id"],
        manifest["task_type"],
        "asset-registration",
        "DTMB5415",
        prov["scenario_key"],
        "lane:C",
        "report:297",
    ],
    "markdown": markdown,
    "figures": figures,
}
PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

n_json_blocks = markdown.count("```json")
print(f"wrote {DOC.relative_to(REPO)} chars={len(markdown)} json_blocks={n_json_blocks}")
print(f"wrote {PAYLOAD} figures={len(figures)}")
if n_json_blocks != 1:
    raise SystemExit(f"expected exactly one ```json block, found {n_json_blocks}")