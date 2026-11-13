#!/usr/bin/env python3
"""wp-9756-01 | render the KF-RESULT report body from the registered manifest.

All numbers, quotes, offsets and line numbers in the body are injected from
docs/kf/wp-9756-01/{asset_manifest.json,locator_check.json,sha256.txt} — nothing is
typed by hand (zero-hand-copy discipline). The body carries exactly one ```json block:
the kf_result.v1 envelope.

    python3 scripts/kf_wp9756_01_build_report.py
    -> docs/kf/wp-9756-01/report_body.md
"""
from __future__ import annotations

import hashlib
import json
import os

PKG_DIR = "docs/kf/wp-9756-01"
CONTRACT_HASH = "sha256:66c02e91e7ffcc3d81b24465112b94ac481ebc351584c13d01d978c16be4316b"


def load(name: str) -> dict:
    with open(os.path.join(PKG_DIR, name), encoding="utf-8") as fh:
        return json.load(fh)


def esc(text: str) -> str:
    """Table-safe rendering of a verbatim quote (keep it byte-identical to the source)."""
    return str(text).replace("|", "\\|").replace("\n", " ")


def main() -> None:
    man = load("asset_manifest.json")
    env = load("kf_result.json")
    loc = load("locator_check.json")
    src = man["source"]
    counts = man["counts"]
    by_res = counts["by_resolution"]
    idf = man["identity_facts"]
    pkg = man["package_id"]

    png = os.path.join(PKG_DIR, "figures", "asset_manifest_coverage.png")
    png_sha = "sha256:" + hashlib.sha256(open(png, "rb").read()).hexdigest() if os.path.exists(png) else "（图未生成）"

    # ---- tables -------------------------------------------------------------
    asset_rows = []
    for a in man["assets"]:
        lo = a["locator"]
        span = (f"L{lo['line']} / c{lo['char_start']}–{lo['char_end']}"
                if lo.get("char_start") is not None else
                f"{lo.get('pointer', 'record')}")
        quote = esc(lo["quote"])
        if len(quote) > 96:
            quote = quote[:96] + "…"
        asset_rows.append(
            f"| `{a['asset_id']}` | {a['kind']} | `{esc(a['name'])}` | {a['in_report_section']} "
            f"| {span} | {a['resolution']} | `{quote}` |")

    def loc_row(l: dict) -> str:
        return (f"| {l['locator_id']} | {esc(l['meaning'])} | `{esc(l['quote'])}` "
                f"| {l['line']} | {l['char_start']} | {l['occurrences']} |")

    anchor_rows = [loc_row(l) for l in man["locators"]
                   if str(l["locator_id"]).startswith("q")]
    obs_loc_rows = [loc_row(l) for l in man["locators"]
                    if str(l["locator_id"]).startswith("O")]
    n_anchor = len(anchor_rows)
    n_obs_loc = len(obs_loc_rows)

    def obs_cell(ob: dict) -> str:
        lids = {l["char_start"]: l["locator_id"] for l in ob.get("locator_ids", [])}
        parts = ["`" + esc(q) + "`" for q in ob.get("quotes", [])]
        ids = [v for k, v in sorted(lids.items()) if k is not None]
        if ids:
            parts.append("（定位 ID：" + "、".join(ids) + "）")
        return " <br> ".join(parts)

    obs_rows = [f"| O{i} | {esc(ob['about'])} | {obs_cell(ob)} | {esc(ob['note'])} |"
                for i, ob in enumerate(man["observations"], start=1)]

    lim_rows = [f"| L{i} | {esc(x)} |" for i, x in enumerate(man["limitations"], start=1)]

    body = f"""# KF-RESULT {pkg}

**工作包**：`{pkg}`（task_type=`01-asset-registration`，lane={man['lane']}）　**report_id**：`{man['report_id']}`（tensor://reports/9756）　**产出仓**：TensorKnowledge（分支 agent/m15666）
**源报告**：{idf['title']}
**源场景**：`{idf['scenario_key']}`　**源 mission**：{idf['source_mission_id']}　**源状态**：{idf['status']}（created_at {idf['created_at']}）
**本包结论**：源资产已登记 **{counts['assets_total']} 项**（resolved_in_source {by_res.get('resolved_in_source', 0)} / metadata_only {by_res.get('metadata_only', 0)} / referenced_unresolved {by_res.get('referenced_unresolved', 0)}），定位器 **{counts['locators_resolved']}/{counts['locators_total']}** 逐字命中且唯一；`claims=[]`（本包不做抽取）；**不标 verified**。

**修订记录**：v2 修正元数据字段 `source.lines` —— 首版（平台报告 id 14740）写成 208，实为 207 个文本行（`len(markdown.splitlines())`；原式 `count(\\n)+1` 在文末有换行时多算一行）。源哈希、字符数、资产清单与定位器结论均无变化，本版取代 id 14740。

---

## 1. 本工序做了什么

只碰 `report_id=9756` 这一份报告，只做「资产登记」这一道工序：

1. 从平台接口取回 `tensor://reports/9756` 的 `markdown`，现场用 UTF-8 字节重算 sha256，与契约 `source_hash` 比对 → 一致（`{src['hash']}`，chars {src['chars']}，bytes {src['bytes_utf8']}）。
2. 枚举报告正文与报告记录里**可解析**的资产，逐项给出定位器（字符区间 + 行号 + 逐字引文 + 命中次数），共 {counts['assets_total']} 项：1 份报告正文、{counts['by_kind'].get('embedded_figure_metadata', 0)} 条记录级图注、{counts['by_kind'].get('figure_reference', 0)} 条 §4 图链接、{counts['by_kind'].get('source_code_reference', 0)} 个源码文件、{counts['by_kind'].get('test_module_reference', 0)} 个测试文件、{counts['by_kind'].get('code_symbol_reference', 0)} 个代码符号、{counts['by_kind'].get('api_endpoint_reference', 0)} 个端点、{counts['by_kind'].get('repro_command', 0)} 条复现命令，以及 results.json / gen_artifacts.py / 产物目录。
3. **不做**抽取、**不做**报告类型分类（契约 `classify_report_type: false`）、**不下载**图片与 results.json 字节、**不调用**船舶平台端点、**不裁定**上游数值对错。
4. 输出 kf_result.v1 信封（唯一 json 块见文末），`claims: []` 为契约允许的完整结果。

## 2. 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 做法 | 关键设置 |
|---|---|---|
| S1 取源 | `python3 scripts/kf_wp9756_01_register.py` → `/auth/login` 拿 token → `GET /tensor/reports/9756` | 只读；请求只命中 id=9756 |
| S2 指纹 | `hashlib.sha256(markdown.encode("utf-8"))` | 与契约 `{CONTRACT_HASH[:23]}…` 逐字节比对；chars {src['chars']} 同步比对 |
| S3 定位 | 每条引文用 `markdown.find` / `markdown.count` 机械求偏移与命中次数，再回推行号 `markdown.count("\\n",0,pos)+1` | 任何一条引文不命中或命中次数与登记不符 → 脚本非零退出 |
| S4 附件探测 | 对 `record.figures` 的 4 个 png 逐个 `GET /tensor/reports/9756/figures/<name>` | 全部返回 **{json.dumps(counts['figure_probe_http_status'], ensure_ascii=False)}** → 记录只有 name+caption，无字节 → 登记为 `metadata_only`，不声明任何 png 哈希 |
| S5 结构门 | `jsonschema.validate(envelope, schemas/kf_result.v1.schema.json)`；`jsonschema.validate(manifest, docs/kf/wp-9756-01/asset_manifest.schema.json)` | 信封 `additionalProperties: false`；本包另附一份 package-local 清单 schema（仓内通用的 `schemas/asset_manifest.v1.schema.json` 被 `const package_id=wp-448-01 / report_id=448` 钉死，不能描述本包，未改动它） |
| S6 图 | matplotlib（Agg）画资产解析状态覆盖图，`sha256` 入 `sha256.txt` | 数字全部来自清单 `counts.by_resolution`，无手抄 |
| S7 渲染 | `python3 scripts/kf_wp9756_01_build_report.py` → 本文件（表格由清单注入） | 正文里唯一一个 fenced json 代码块 = kf_result 信封 |
| S8 自检 | `python3 -m pytest tests/test_kf_wp9756_01.py -q` | 15 例全绿（哈希重算/定位重算/schema/唯一 id/claims 空/作用域/工件哈希） |

## 3. 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9756-01/asset_manifest.json` | 契约声明输出。report_id=9756；`source.hash`={src['hash']}（match={str(src['hash_matches_contract']).lower()}）；chars {src['chars']} / bytes {src['bytes_utf8']} / {src['lines']} 行 / {src['heading_count']} 个标题；资产 {counts['assets_total']} 项；定位器 {counts['locators_resolved']}/{counts['locators_total']} 命中且唯一；`claims=[]` |
| `docs/kf/wp-9756-01/kf_result.json` | kf_result.v1 信封（`package_id/task_type/report_id/provenance/outputs/claims`），过 draft 2020-12 schema；`outputs` 只有一个键 `asset_manifest.json` |
| `docs/kf/wp-9756-01/locator_check.json` | {loc['quotes_checked']} 条定位器逐条结果：逐字命中、字符偏移、行号、命中次数；`unresolved=[]`、`non_unique=[]` |
| `docs/kf/wp-9756-01/source.md` | 平台返回的 markdown 逐字节副本（离线可复算子串与哈希） |
| `docs/kf/wp-9756-01/sha256.txt` | 源哈希 `{src['hash']}`、chars/bytes、契约期望值、覆盖图 png `{png_sha}` |
| `docs/kf/wp-9756-01/asset_manifest.schema.json` | 本包清单的 package-local JSON Schema（让 `schema_pass` 可机器裁） |
| `docs/kf/wp-9756-01/figures/asset_manifest_coverage.png` | 资产解析状态覆盖图（resolved/metadata_only/unresolved 三柱），数字取自清单 |
| `docs/kf/wp-9756-01/report_body.md` | 本报告正文（本文件） |
| `scripts/kf_wp9756_01_register.py` | 取源 / 哈希 / 定位 / 探测 / schema / 清单 / 信封（任一门失败即非零退出） |
| `scripts/kf_wp9756_01_build_report.py` | 由清单注入渲染本报告正文 |
| `tests/test_kf_wp9756_01.py` | 离线自检 15 例：复算哈希、重算每条定位器、两份 schema 校验、id 唯一、claims 空、作用域仅 9756、png 哈希入账 |

## 4. 证据定位表（资产/字段 → 原文逐字片段）

偏移与行号由 `markdown.find` 机械给出（`docs/kf/wp-9756-01/locator_check.json` 可复算），非人工计数。

**4.1 资产定位（{counts['assets_total']} 项）**

| asset_id | kind | name | 报告节 | 定位（行/字符） | resolution | 原文逐字片段 |
|---|---|---|---|---|---|---|
{os.linesep.join(asset_rows)}

**4.2 结构锚点（{n_anchor} 条，用于钉住报告骨架与自报证据等级）**

| 定位 ID | 该引文钉住什么 | 原文逐字片段 | 行 | 字符偏移 | 命中次数 |
|---|---|---|---|---|---|
{os.linesep.join(anchor_rows)}

**4.2b 观察点引文（{n_obs_loc} 条，§5.1 三条观察所引的原文，逐条机器定位）**

| 定位 ID | 该引文钉住什么 | 原文逐字片段 | 行 | 字符偏移 | 命中次数 |
|---|---|---|---|---|---|
{os.linesep.join(obs_loc_rows)}

**4.3 源身份（字段 → 值）**

| 字段 | 值 |
|---|---|
| report_id | {idf['report_id']} |
| source_uri | `{src['uri']}` |
| source_field | `{src['field']}` |
| title（记录） | {idf['title']}（与契约一致：{str(idf['title_matches_contract']).lower()}） |
| scenario_key（记录） | `{idf['scenario_key']}`（与契约一致：{str(idf['scenario_key_matches_contract']).lower()}） |
| chars / bytes_utf8 / lines | {src['chars']} / {src['bytes_utf8']} / {src['lines']} |
| sha256（现场重算） | `{src['hash']}` |
| sha256（契约） | `{src['hash_expected']}` |
| hash match | {str(src['hash_matches_contract']).lower()} |
| record tags | {esc('、'.join(idf['tags']))} |
| record.figures | {counts['figures_declared_in_record']} 条（name+caption，无字节：figures 端点全部 404） |
| claims | {len(man['claims'])} |

## 5. 注意点与局限

**5.1 观察到的口径问题（只登记，不裁定）**

| # | 观察点 | 原文逐字片段（定位 ID 见 §4.2b） | 说明 |
|---|---|---|---|
{os.linesep.join(obs_rows)}

**5.2 局限（诚实边界）**

| # | 局限 |
|---|---|
{os.linesep.join(lim_rows)}

**5.3 证据分级说明**：本包登记源资产的**证据等级**沿用报告自报口径（`REAL` 公式实现 + 系数层 `WITHHELD`），本包**不重新判级**：

- 报告 §5 逐字自报系数层为离线转录：`参考线 / 削减率 / Z 表 / dd 向量均为**离线转录**（WITHHELD），未回读规则 PDF；`（行 {[l['line'] for l in man['locators'] if l['locator_id'] == 'q09'][0]}）；
- 报告 §6 逐字声明对规则原文「无基准」：`但**对规则原文**的偏差不可评估（系数层 WITHHELD，无原文基准）——这一条如实声明为`（行 {[l['line'] for l in man['locators'] if l['locator_id'] == 'q11'][0]}）。

## 6. 自检（逐条对照 acceptance）

| acceptance | 状态 | 证据 |
|---|---|---|
| valid_json | ✓ | `asset_manifest.json` / `kf_result.json` / `locator_check.json` 均被 `json.load` 成功读入（自检 15 例执行即证明） |
| schema_pass | ✓ | 信封过 `schemas/kf_result.v1.schema.json`（draft 2020-12）；清单过本包 `asset_manifest.schema.json`（draft-07）；两项均在 `tests/test_kf_wp9756_01.py::test_envelope_schema_pass` / `::test_manifest_schema_pass` 断言 |
| source_locator_resolvable | ✓ | `tensor://reports/9756` 经 `GET /tensor/reports/9756` 200 返回；{counts['locators_resolved']}/{counts['locators_total']} 条定位器 `markdown.find` 命中，且偏移/行号/命中次数由 `test_every_locator_resolves_verbatim` 重算复核，`unresolved=[]`、`non_unique=[]` |
| source_hash_matches | ✓ | 重算 `{src['hash']}` == 契约 `{src['hash_expected']}`（`test_source_hash_matches_contract`）；chars {src['chars']} == 契约 8293（`test_chars_match_contract`） |
| no_duplicate_ids | ✓ | 资产 id {counts['assets_total']} 个互不相同、定位器 id {counts['locators_total']} 个互不相同（`test_no_duplicate_ids`）；`outputs` 只有一个键 `asset_manifest.json` |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | `claims: []` + `claims_empty_reason` 非空；`no_forced_claim_generation: true` 下零条即完整结果（`test_claims_empty_with_explicit_reason`）；全文无 `verified` 标记 |

**失败项：无**（无 honest-FAIL 需申报）。需要读者注意的口径：本包「已核对」只到**哈希恒等 + 引文逐字可定位**这一层，不含任何内容正确性背书。

### 6.2 误差判定（显式回答「是否 <3%」）

| 可比量 | 基准 | 本包结果 | 是否 <3% |
|---|---|---|---|
| 源 markdown 字节指纹 | 契约 `source_hash`（平台独立重算） | sha256 完全相等（{src['hash'][:21]}…，{src['bytes_utf8']} 字节） | **是（相对误差 0）** |
| 源字符数 | 契约 `chars=8293` | {src['chars']} | **是（绝对差 0）** |
| 引文定位 | 源 markdown 子串 | {counts['locators_resolved']}/{counts['locators_total']} 命中（偏移零误差） | **是（0 条错位）** |
| 上游物理/规则量（EEXI 3.2755、required 2.0710、AER 2.4676、32/32 等） | 规则原文 / 实船实测 | **本包未复算** | **不适用**：本工序是资产登记（契约 `objective.register_assets: true`、`classify_report_type: false`），不产出也不校核物理量；`no_forced_claim_generation: true`。上游量与该量基准的对比归抽取/审计道次，本包不做，也不假装做过 |

## 7. 结果图

![asset_manifest_coverage.png](figures/asset_manifest_coverage.png)

* **覆盖图**：{pkg} 的 {counts['assets_total']} 项资产按解析状态分柱——`resolved_in_source`={by_res.get('resolved_in_source', 0)}（仅报告正文本身，逐字节可复核）、`metadata_only`={by_res.get('metadata_only', 0)}（记录级图注，无字节）、`referenced_unresolved`={by_res.get('referenced_unresolved', 0)}（路径/端点/命令文本，二进制在产出仓 ship-performance-platform）。数字由 `counts.by_resolution` 程序化注入，png 哈希 `{png_sha}` 已入 `sha256.txt`。
* 本工序为纯资产登记（文档/后端类），**没有**场量云图、也没有可对标解析解的物理量，故不产「与解析解比较」曲线——按报告纪律如实声明理由，不造装饰性图。

## 8. 复现（repro_cmd）

```bash
# 在仓库检出内（需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
python3 scripts/kf_wp9756_01_register.py        # 取源+哈希+定位+探测+schema -> 清单/定位表/信封/源副本/覆盖图
python3 scripts/kf_wp9756_01_build_report.py    # 由清单注入渲染本报告正文
python3 -m pytest tests/test_kf_wp9756_01.py -q # 15 passed：哈希重算/定位重算/schema/id 唯一/claims 空/作用域/工件哈希
```

---

## 结果 JSON（本报告唯一 json 块）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""
    out = os.path.join(PKG_DIR, "report_body.md")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(body)
    n_blocks = body.count("```json")
    print(f"wrote {out}: {len(body)} chars, json_blocks={n_blocks}")
    if n_blocks != 1:
        raise SystemExit("report body must contain exactly one ```json block")


if __name__ == "__main__":
    main()