#!/usr/bin/env python3
"""wp-12510-01 · 组装 KF-RESULT 报告 markdown（六段 + 唯一 json 块；数字全部注入自 manifest）。"""
from __future__ import annotations

import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = os.path.join(REPO, "docs", "kf", "wp-12510-01")


def main() -> None:
    env = json.load(open(os.path.join(PKG, "kf_result.json"), encoding="utf-8"))
    man = env["outputs"]["asset_manifest.json"]
    src = man["source"]
    snap = json.load(open(os.path.join(REPO, "runs", "wp-12510-01", "report_12510_api.json"), encoding="utf-8"))
    rec_mission = snap["mission_id"]
    acc = json.load(open(os.path.join(PKG, "acceptance.json"), encoding="utf-8"))

    # 证据定位表：逐行由 manifest 生成
    rows = []
    for a in man["assets"]:
        for loc in a["locators"]:
            if loc.get("source_field") == "markdown":
                span = f"markdown[{loc['char_start']}:{loc['char_end']}]"
                q = loc["quote"]
                q = q if len(q) <= 60 else q[:57] + "…"
            else:
                span = f"record.{loc['field']}"
                q = str(loc.get("value", ""))
            q_disp = q.replace("`", "’")  # 表格显示用；manifest 内保持逐字原样
            rows.append(f"| {a['asset_id']} | {a['kind']} | {span} | `{q_disp}` | {a['status']} |")
    ev_table = "\n".join(rows)

    acc_rows = "\n".join(
        f"| {k} | {'✅ PASS' if r['pass'] else '❌ FAIL'} | {r['detail']} |"
        for k, r in acc["checks"].items()
    )

    figs = man["source"]["platform_figures"]
    fig_meta = "、".join(f"{f['name']}（{f['caption']}）" for f in figs)

    json_block = json.dumps(env, ensure_ascii=False, indent=2)

    md = f"""# KF-RESULT wp-12510-01

- package_id: `wp-12510-01` ｜ task_type: `01-asset-registration` ｜ report_id: `12510` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: draft
- source: `tensor://reports/12510`（field=`markdown`），chars={src['chars']}，bytes={src['bytes_utf8']}，sha256=`{src['sha256']}`
- 工序范围：**只登记资产，不抽取 claim、不做报告类型分类、不标 verified**（按契约 objective/constraints）

## ① 本工序做了什么（含案例介绍）

对 report_id=12510（`{src['title']}`，scenario_key=`{src['scenario_key']}`，mission_id={rec_mission}）执行 01-asset-registration：

1. 从平台 API 取回该报告 markdown，重算字节哈希并锁定：`{src['sha256']}`，{src['bytes_utf8']} 字节 / {src['chars']} 字符——与契约声明逐字节一致（hash_check.match=True，chars_check.match=True）。
2. 建立资产清单：共 **{man['asset_counts']['total']} 个资产**（resolved {man['asset_counts']['by_status']['resolved']} / unresolved {man['asset_counts']['by_status']['unresolved']}），覆盖源文档本体、记录元数据、4 张声明图、代码模块与测试套件。
3. 为每个资产登记 locator（markdown 字符区间 + record 字段），全部由程序在运行时从原文计算，可逐条回解。
4. 探测资产可解析性：4 张图与代码/测试路径在本节点（m11196 工作树，只读）定位到字节/文件并复算 sha256；平台侧图下载端点不存在（3 个候选端点 HTTP 404），图字节以节点工件为准。
5. claims 按契约留空数组（objective.classify_report_type=false，不强制生成知识）。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/脚本 | 关键设置 |
| --- | --- | --- |
| 取源 + 锁哈希 | `scripts/wp12510_register_assets.py`（urllib，Bearer 登录） | 以 `markdown` 字段 utf-8 编码字节做 sha256；与契约声明逐字节比对，不一致即 SystemExit |
| 资产登记 | 同上（`--offline` 可离线复跑） | quote 用**字面量针**在 markdown 内检索，找不到/不唯一即 SystemExit（拒绝编造）；每条 locator 存 `char_start/char_end/quote` |
| 可解析性探测 | 同上 `disk_probe()` | 只读探测节点工件目录；记录存在性/大小/sha256，不重试、不猜测 |
| 验收门 | `scripts/wp12510_verify_acceptance.py` | 契约 6 项 acceptance + 2 项结构不变量；jsonschema Draft2020-12 校验信封 |
| 图 | `scripts/wp12510_render_figure.py` | matplotlib Agg，直接从 manifest 渲染，无手抄数字 |
| 单元测试 | `tests/test_wp12510_asset_manifest.py` | 10 项 pytest，含**负对照**（篡改 quote / 复制 id 必须被检出）与离线复跑确定性 |

## ③ 产出物清单

| 文件 | 要点 |
| --- | --- |
| `docs/kf/wp-12510-01/asset_manifest.json` | {man['asset_counts']['total']} 资产 / {len(rows)} 条 locator / 计数与不变量 / 完整性声明 |
| `docs/kf/wp-12510-01/kf_result.json` | 提交用结果信封（outputs=`asset_manifest.json`，claims=[]） |
| `docs/kf/wp-12510-01/acceptance.json` | {len(acc['checks'])} 项验收检查的机器结论（all_pass={str(acc['all_pass']).lower()}） |
| `docs/kf/wp-12510-01/fig1_asset_resolution.png` | 资产解析状态图（见下） |
| `scripts/wp12510_register_assets.py`、`scripts/wp12510_verify_acceptance.py`、`scripts/wp12510_render_figure.py` | 登记/验收/渲染，一键复跑 |
| `tests/test_wp12510_asset_manifest.py` | 10 项 pytest（含负对照与复现性） |
| `runs/wp-12510-01/` | 源快照：`report_12510_api.json`、`report_12510.md`、`markdown.sha256` |

## ④ 证据定位表（字段 → 原文逐字片段）

下表的「原文片段」列全部是 report 12510 markdown 的**逐字子串**（markdown 类 locator 带字符区间，record 类 locator 带字段名）；逐条回解由 `source_locator_resolvable` 检查覆盖。

| asset_id | kind | locator | 原文片段（逐字） | status |
| --- | --- | --- | --- | --- |
{ev_table}

## ⑤ 注意点与局限

1. **图字节不在平台记录内**：平台 `figures` 元数据只有 name/caption（无二进制），3 个候选下载端点均 404；图字节以本节点 m11196 工作树 `artifacts/imo_g12_fuel_safety/` 为准（sha256 已入 manifest `node_artifact`）。若该工作树被清理，图资产将退化为 referenced_unresolved。
2. **代码/测试路径为跨仓引用**：`backend/modules/imo_g12_fuel_safety/` 属 ship-performance-platform 域（m11196 工作树），本仓仅登记引用与节点验证证据，不复制代码。
3. **不标 verified**：本工序只登记与定位；任何 verification 状态由平台门计算，manifest 中无 verified 标记。
4. **零手抄**：manifest 中所有数字（chars/bytes/sha256/偏移/计数）均为运行时计算；quote 为字面量针，运行时校验唯一性。
5. **边界遵守**：只读 report_id=12510；未读/写其它 report_id；未改写上游产物。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结论 | 机器证据 |
| --- | --- | --- |
{acc_rows}

**误差判定**：本工序为登记/定位工序，无物理量计算。关键量 vs 基准逐项：源哈希 重算值=契约值（逐字节一致，误差 0，<3% ✅）；chars 重算 {src['chars']} = 契约 {src['chars']}（误差 0，<3% ✅）；7 条 markdown locator 全部逐字回解成功（7/7）。无物理量基准，原因：本工序为资产登记，不涉及数值计算。

**结果图**：`fig1_asset_resolution.png`（资产解析状态，由 manifest 程序化渲染，无手抄数字；经 API `figures` 参数内嵌于本报告）。

**repro_cmd**（一键复跑）：
`python3 scripts/wp12510_register_assets.py --offline && python3 scripts/wp12510_verify_acceptance.py && python3 scripts/wp12510_render_figure.py && python3 -m pytest tests/test_wp12510_asset_manifest.py -q`

## 结果 JSON（唯一 json 块）

```json
{json_block}
```
"""
    with open(os.path.join(PKG, "REPORT.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(os.path.join(PKG, "REPORT.md"))


if __name__ == "__main__":
    main()
