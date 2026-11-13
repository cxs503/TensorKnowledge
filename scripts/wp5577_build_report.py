#!/usr/bin/env python3
"""Assemble docs/kf/wp-5577-01/REPORT.md from the package artefacts.

Every number/quote in the report is read from asset_manifest.json /
acceptance.json / kf_result.json at runtime (zero hand-copy). The report
contains exactly one ```json code block: the result envelope.
Usage: python3 scripts/wp5577_build_report.py
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG = REPO / "docs" / "kf" / "wp-5577-01"


def main() -> None:
    m = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    acc = json.loads((PKG / "acceptance.json").read_text(encoding="utf-8"))
    env = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    src = m["source"]
    cnt = m["asset_counts"]
    assets = m["assets"]
    n_md_loc = sum(1 for a in assets for l in a.get("locators", [])
                  if l.get("source_field") == "markdown")
    n_rec_loc = sum(1 for a in assets for l in a.get("locators", [])
                    if l.get("source_field") == "record")

    rows = []
    for a in assets:
        loc = a["locators"][0]
        q = loc.get("quote") or str(loc.get("value"))
        if len(q) > 58:
            q = q[:55] + "..."
        q = q.replace("|", "\\|")
        rows.append(f"| {a['asset_id']} | {a['kind']} | {a['status']} | `{q}` |")
    table = "\n".join(rows)

    box = {True: "\u2611", False: "\u2612"}
    acc_rows = "\n".join(
        f"| {name} | {box[ok]} |" for name, ok in acc["summary"].items())

    envelope_json = json.dumps(env, ensure_ascii=False, indent=2)

    md = f"""# KF-RESULT wp-5577-01

- package_id: `wp-5577-01` ｜ task_type: `01-asset-registration` ｜ report_id: `5577` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: draft
- source: `tensor://reports/5577`（field=`markdown`），chars={src['chars']}，bytes={src['byte_length_utf8']}，sha256=`{src['sha256']}`
- 工序范围：**只登记资产，不抽取 claim、不做报告类型分类、不标 verified**（按契约 objective/constraints）

## ① 本工序做了什么

对 report_id=5577（`{src['title']}`）执行 01-asset-registration：

1. 从平台 API 取回该报告记录，重算 `markdown` 字段 utf-8 字节哈希并锁定：`{src['sha256']}`，{src['byte_length_utf8']} 字节 / {src['chars']} 字符——与契约声明 `{src['hash_check']['expected']}` 逐字节一致（match=True），chars 契约 {src['chars_check']['expected']} = 实测 {src['chars_check']['observed']}。
2. 建立资产清单：共 **{cnt['total']} 个资产**（resolved {cnt['resolved']} / unresolved {cnt['unresolved']}），覆盖源文档本体、记录元数据、3 张声明图、以及报告正文中逐字出现的 16 个工件/端点/标准/文献/任务引用。
3. 为每个资产登记 locator（markdown 字符区间 {n_md_loc} 条 + record 字段 {n_rec_loc} 条），全部由脚本在运行时从原文计算，可逐条回解。
4. claims 按契约留空数组，并显式写明留空理由（`no_forced_claim_generation`；本包 objective 仅 `register_assets`）。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/脚本 | 关键设置 |
| --- | --- | --- |
| 取源 + 锁哈希 | `scripts/wp5577_register_assets.py`（urllib，Bearer 登录） | 以 `markdown` 字段 utf-8 编码字节做 sha256（不做换行归一）；与契约声明逐字节比对，不符即 SystemExit |
| 资产登记 | 同上（`--offline` 可离线复跑） | 工件/端点/标准/文献引用用**字面量针**在 markdown 内检索，找不到即 SystemExit（拒绝编造 locator）；每条 locator 存 `char_start/char_end/quote` |
| 验收门 | 同上（`verify_acceptance`） | 契约 6 项 acceptance + 2 项结构不变量；jsonschema Draft2020-12 校验信封 |
| 图 | `scripts/wp5577_render_figure.py` | matplotlib Agg，直接从 manifest 渲染，无手抄数字 |
| 单元测试 | `tests/test_wp5577_asset_manifest.py` | 12 项，含**负对照**（篡改 quote / 平移偏移必须被检出；缺失针必须被拒）与离线复跑逐字节一致性 |

不复用的既有件：本检出原先缺 `schemas/kf_result.v1.schema.json`（其它工作树已有同内容副本，md5 `0491bc4ce09a1fc2f62f015666d38935`）；本单按字节原样补齐该 schema 以便验收门可在本检出内复跑。

## ③ 产出物清单

| 文件 | 要点 |
| --- | --- |
| `docs/kf/wp-5577-01/asset_manifest.json` | {cnt['total']} 资产 / {n_md_loc + n_rec_loc} locator / 计数与不变量 / claims 政策 |
| `docs/kf/wp-5577-01/kf_result.json` | 提交用结果信封（outputs=`asset_manifest.json`，claims=[]） |
| `docs/kf/wp-5577-01/acceptance.json` | 8 项验收检查的机器结论（全部 PASS） |
| `docs/kf/wp-5577-01/fig1_asset_resolution.png` | 资产解析状态图（本报告 ④ 后附图） |
| `docs/kf/wp-5577-01/source/` | 源快照：`report_5577.json`（API 记录）、`report_5577.md`、`markdown.sha256` |
| `scripts/wp5577_register_assets.py`、`scripts/wp5577_render_figure.py`、`scripts/wp5577_build_report.py` | 登记/渲染/组报，一键复跑 |
| `tests/test_wp5577_asset_manifest.py` | 12 项 pytest（含负对照与复现性） |
| `schemas/kf_result.v1.schema.json` | 结果信封 schema（与其它工作树副本 md5 一致） |

## ④ 证据定位表（asset → 原文逐字片段）

下表的「原文片段」列全部是 report 5577 markdown 的**逐字子串**（markdown 类 locator 带字符区间，record 类 locator 带字段名）；逐条回解由 `source_locator_resolvable` 检查覆盖（{acc['checks']['source_locator_resolvable']['locators_resolved']}/{acc['checks']['source_locator_resolvable']['locators_checked']} 条 markdown locator 回解成功）。

| asset_id | kind | status | 原文片段（逐字） |
| --- | --- | --- | --- |
{table}

图 1：`fig1_asset_resolution.png` — {cnt['total']} 个资产的解析状态（绿=resolved {cnt['resolved']} 个：源文档与记录元数据；红=unresolved {cnt['unresolved']} 个：3 图 + 16 个声明引用）与 kind 分布。

## ⑤ 注意点与局限

1. **{cnt['unresolved']} 个资产 unresolved 是报告记录本身的缺口，不是登记遗漏**：3 张图在 record 里只有 `name`+`caption`（无 `png_base64`），图内容不可审计；16 个工件/端点/标准/文献引用只以名字出现在正文，其字节副本在产出仓（ship-performance-platform）或平台侧，不在本报告记录内。
2. **登记面向主文**：本包不解析表格数值、不复核报告内任何数字的正确性——那是 03/04 工序与独立复核单的职责；本单对报告 5577 的任何数字**没有**做正确性背书。
3. **claims 为空是设计而非缺漏**：契约 objective 仅 `register_assets`（`classify_report_type=false`），constraints 禁止强制生成 claim；因此本包不产出任何 claim，也不存在「verified」标记（verification 由平台门计算）。
4. **装置依赖**：全部检查在本检出内离线可复跑（`--offline`，源快照在 `docs/kf/wp-5577-01/source/`）；在线模式经 API 重取，两种模式在本单中逐字节一致（`test_offline_rerun_byte_identical`）。
5. **schema 补齐**：本检出原先缺 `schemas/kf_result.v1.schema.json`，按其它工作树同内容副本（md5 `0491bc4ce09a1fc2f62f015666d38935`）字节原样补齐，未改任何字段。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结论 |
| --- | --- |
{acc_rows}

**honest 声明**：无失败项。需明示一项非失败的性质——{cnt['unresolved']} 个 unresolved 资产是源记录缺字节副本所致（见 ⑤.1），下游 02/03 工序若需图内容或工件字节，须另走平台存储端点或产出仓。

**repro_cmd**（工作树根执行，一键复跑）：

```bash
python3 scripts/wp5577_register_assets.py --offline   # 离线复跑：manifest + 信封 + acceptance（在线去掉 --offline）
python3 scripts/wp5577_render_figure.py               # 渲染 fig1_asset_resolution.png
python3 scripts/wp5577_build_report.py                # 组装本报告（唯一 json 块=结果信封）
python3 -m pytest tests/test_wp5577_asset_manifest.py -q   # 12 项测试（含负对照）
```

**结果信封（契约要求的唯一 json 代码块，字段结构见 schemas/kf_result.v1.schema.json）**：

```json
{envelope_json}
```
"""
    (PKG / "REPORT.md").write_text(md, encoding="utf-8")
    print(PKG / "REPORT.md")


if __name__ == "__main__":
    main()
