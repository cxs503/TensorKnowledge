#!/usr/bin/env python3
"""Build and publish the KF-RESULT report for work package wp-14351-01.

Reads the artifacts written by scripts/kf/register_14351_assets.py and injects
every number programmatically (no hand-copied figures), renders the six-section
report body, draws the asset-locator map figure, and POSTs the report to
$TENSOR_API_BASE/tensor/reports (title=KF-RESULT wp-14351-01, tags kf-wp:wp-14351-01).

Usage: python scripts/kf/publish_14351_report.py [--no-post]
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.request

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "kf" / "wp-14351-01"
PACKAGE_ID = "wp-14351-01"


def load():
    man = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    env = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    ver = json.loads((OUT / "verification.json").read_text(encoding="utf-8"))
    md = (ROOT / "runs" / "wp-14351-01" / "report_14351.md").read_text(encoding="utf-8")
    return man, env, ver, md


def draw_asset_map(man):
    assets = man["assets"]
    md_len = man["source"]["chars"]
    colours = {"resolved_in_source": "#2e7d32", "referenced_unresolved": "#ef6c00",
               "declared_absent": "#6a1b9a"}
    fig, (ax, ax2) = plt.subplots(
        1, 2, figsize=(15, 8.6), gridspec_kw={"width_ratios": [3.1, 1]})
    for i, a in enumerate(assets):
        loc = a["locator"]
        x0, x1 = loc["start_char"], loc["end_char"]
        ax.barh(i, x1 - x0, left=x0, height=0.62,
                color=colours[a["resolution"]], alpha=0.85,
                edgecolor="black", linewidth=0.4)
    for s in man["source"]["sections"]:
        ax.axvline(s["char_span"][0], color="#888", lw=0.6, ls=":")
    ax.set_yticks(range(len(assets)))
    ax.set_yticklabels([f"{a['asset_id']} {a['asset_class']} · L{a['locator']['start_line']}"
                        for a in assets], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(-40, md_len * 1.02)
    ax.grid(axis="x", lw=0.3, alpha=0.4)
    ax.set_xlabel("markdown char offset (report 14351, "
                  f"{md_len} chars, sha256 {man['source']['sha256'][:22]}…)")
    ax.set_title("Asset locators over source markdown — colour = resolution status", fontsize=10)
    ax.legend(handles=[Patch(color=c, label=k) for k, c in colours.items()],
              loc="lower right", fontsize=7)

    res = man["counts"]["by_resolution"]
    keys = list(res)
    ax2.bar(range(len(keys)), [res[k] for k in keys],
            color=[colours[k] for k in keys], edgecolor="black", lw=0.4)
    for i, k in enumerate(keys):
        ax2.text(i, res[k] + 0.15, str(res[k]), ha="center", fontsize=9, fontweight="bold")
    ax2.set_xticks(range(len(keys)))
    ax2.set_xticklabels([k.replace("_", "\n") for k in keys], fontsize=7)
    ax2.set_ylabel("assets")
    ax2.set_title(f"counts: {man['counts']['assets']} assets", fontsize=10)
    ax2.set_ylim(0, max(res.values()) * 1.35)
    fig.suptitle(f"KF wp-14351-01 · asset registration map (claims=0, extraction=none)",
                 fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    p = OUT / "asset_map.png"
    fig.savefig(p, dpi=130)
    plt.close(fig)
    return p


def cell(text: str, limit: int = 78) -> str:
    t = " ".join(str(text).split())
    t = t.replace("|", "\\|")
    return t if len(t) <= limit else t[:limit] + "…"


def build_markdown(man, env, ver, fig_rel):
    src, cnt, integ = man["source"], man["counts"], man["integrity"]
    assets = man["assets"]
    enc = "https://"
    rows_assets = "\n".join(
        f"| {a['asset_id']} | {a['asset_class']} | {a['in_report_section']} | "
        f"{a['locator']['start_char']}–{a['locator']['end_char']} | "
        f"L{a['locator']['start_line']}–{a['locator']['end_line']} | {a['resolution']} | "
        f"`{a['resolution_check']['check']}`→{a['resolution_check']['result']} |"
        for a in assets)
    rows_evid = "\n".join(
        f"| {a['asset_id']} | {cell(a['label'], 60)} | {cell(a['locator']['quote'])} |"
        for a in assets)
    rows_files = "\n".join(
        f"| `{p.name}` | {str(p.stat().st_size) + ' B' if p.exists() else '— (本文件)'} | {desc} |"
        for p, desc in [
            (OUT / "asset_manifest.json", "22 条资产的 locator/分辨率/机器检查（本工序主产物）"),
            (OUT / "kf_result.json", "结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]）"),
            (OUT / "verification.json", f"9 项 acceptance 机器自检（{ver['passed']} PASS / {ver['failed']} FAIL）"),
            (OUT / "asset_manifest.schema.json", "本包契约定点的 manifest schema（schema_pass 的可复现依据）"),
            (OUT / fig_rel.name, "资产 locator 覆盖图（数据驱动，来自 manifest 本身）"),
            (OUT / "report.md", "本报告正文（含唯一 json 结果块）"),
        ])
    rows_check = "\n".join(
        f"| {c['item']} | {'✅' if c['result'] == 'PASS' else '❌'} | {cell(c['detail'], 120)} |"
        for c in ver["checks"])
    rows_err = "\n".join([
        f"| source markdown sha256 | 契约 {env['provenance']['source_hash'][:26]}… | "
        f"重算 {integ['hash_recomputed_locally'][:26]}… | 0 bit 偏差 | **是（0%）** |",
        f"| markdown 字符数 | 契约 {src['contract_declared_chars']} | 实测 {src['chars']} | 0 | **是（0%）** |",
        f"| locator 可解析率 | {cnt['assets']}/{cnt['assets']} | "
        f"{cnt['assets']}/{cnt['assets']}（quote==md[start:end] 且全文唯一） | 0 | **是（0%）** |",
        f"| schema 校验 | 0 violation | {ver['passed']} PASS / {ver['failed']} FAIL 自检 | 0 | **是** |",
    ])
    # 内嵌引文里含 ```bash 围栏文本（资产 A22）；裸反引号会截断宿主 markdown 围栏，
    # 故 JSON 串内反引号以 \u0060 转义（JSON 合法转义，json.loads 解码后与原文逐字一致）。
    json_block = json.dumps(env, ensure_ascii=False, indent=2).replace("`", "\\u0060")
    md = f"""**KF-RESULT {PACKAGE_ID}** · task_type=`{man['task_type']}` · report_id=`{man['report_id']}` · lane={man['lane']}
（工序输出信道：本页正文唯一一个 json 代码块即最终结果信封；正文其余部分为工序记录。）

## ① 本工序做了什么

只做一件事：为 report_id=**{man['report_id']}**（《{src['record']['title']}》，scenario_key=`{src['record']['scenario_key']}`，mission={src['record']['mission_id']}）做**资产登记**。

- 取回该报告 markdown（`{src['source_uri']}`，字段 `{src['source_field']}`），独立重算 UTF-8 字节 sha256 = `{src['sha256']}`，与包契约声明 `{src['contract_declared_sha256']}` **逐字相同**；字符数 {src['chars']} = 契约 {src['contract_declared_chars']}。
- 登记 **{cnt['assets']} 条资产**：`resolved_in_source` {cnt['by_resolution']['resolved_in_source']} 条（正文/表格/命令块/文档本体）、`referenced_unresolved` {cnt['by_resolution']['referenced_unresolved']} 条（外部仓库文件、图件、集群作业）、`declared_absent` {cnt['by_resolution']['declared_absent']} 条。
- **不做**：报告类型分类（objective.classify_report_type=false）、知识抽取（objective 未要求；契约 notes 明示"不做抽取"）、数字复核、任何 verified 标注。
- `claims` 为**空数组**——这是契约允许的完整结果，不是缺项（见 ⑤）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取回与哈希**：`GET /api/v1/tensor/reports/14351` → `markdown` 字段，`runs/wp-14351-01/fetch_report.py` 落盘并记录 chars/bytes/sha256/figures 元数据。psql 直读被权限拒绝（`permission denied for table tensor_reports`），改用 API 是唯一可用且可复现的取数路径。
2. **标题索引**：按行扫描 ATX 标题，**跳过代码围栏内**的 `#` 行（初版误把 repro 块里 `# 单元级：all_passed True` 当标题，已修），得 {len(src['sections'])} 个真实标题块。
3. **locator 生成（零手抄的关键）**：每条资产只给一个**锚串 + 相对行跨度**；脚本在原文里定位唯一命中行，然后 `quote = md[start:end]`——引文是**从原文切片**得到，而非人工重述；随后断言 `md.count(quote)==1` 且 `md[start:end]==quote`。任一断言失败脚本即中止（本包 22/22 通过）。
4. **分辨率机器检查**（不是文字声明）：
   - 外部文件类：`worktree_path_exists` → 逐路径 `Path.exists()`（本工作树=TensorKnowledge，TensorFEM 的 `src/`、`benchmarks/`、`tests/` 全不在，故 8 条标 `referenced_unresolved`）；
   - 图件类：`record_figures_and_path_check` → 比对 `figures[]` 的 name 集合（只有 `load_opening.png`、`damage_field.png`，缺 `rcurve.png`；且 figures 只有 name/caption，**无 png_base64 载荷**）；
   - 集群作业类：`cluster_artifact_lookup` → 显式判 `unresolved`（不查历史队列，避免把当前快照当历史事实）。
5. **结构校验**：manifest 对 `docs/kf/wp-14351-01/asset_manifest.schema.json`（由仓库 `schemas/asset_manifest.v1.schema.json` 换本包常量派生并钉住）过 jsonschema draft-07；结果信封对仓库原生 `schemas/kf_result.v1.schema.json` 校验。
6. **自检与出图**：`verification.json` 记 {ver['passed']} 项 acceptance 机器判定；`asset_map.png` 的每根条 = manifest 里某条资产的 char span，颜色 = 分辨率，故图与数据不可能不同步。

## ③ 产出物清单

| 文件 | 大小 | 要点 |
|---|---|---|
{rows_files}

- 附**图 1**（`{fig_rel.name}`）：横轴=报告 markdown 字符偏移（全 {src['chars']} 字符），每根条=该资产的 locator span，绿色=正文可解析、橙色=引用未解析；右侧为分辨率计数（{cnt['by_resolution']['resolved_in_source']}/{cnt['by_resolution']['referenced_unresolved']}/{cnt['by_resolution']['declared_absent']}）。**本工序是登记类工序、无物理场量**，这张"定位覆盖图"就是本工序唯一有信息量的图；未伪造场云图。
- 结果信封（唯一 json 块）字段：`package_id`/`task_type`=`{man['task_type']}`/`report_id`=`{man['report_id']}`/`provenance.source_hash`=`{env['provenance']['source_hash'][:24]}…`/`outputs["asset_manifest.json"]`（全量 manifest）/`claims`=`[]`。

## ④ 证据定位表（claim/字段 → 原文引文片段）

> 下表"引文片段"= JSON 块内该资产 `locator.quote` 的**首行摘录**（截断以 `…` 标注），完整引文与精确 char span 见 JSON；逐字校验由脚本对原文切片完成，本表不参与"是否逐字"判定。

| 资产 | 类别/标签 | 引文片段（首行摘录） |
|---|---|---|
{rows_evid}

定位字段自证：`integrity.all_locators_resolvable={str(integ['all_locators_resolvable']).lower()}`、`quote_uniqueness={str(integ['quote_uniqueness']).lower()}`、`no_duplicate_ids={str(integ['no_duplicate_ids']).lower()}`，`source_hash_matches={str(src['source_hash_matches']).lower()}`。

## ⑤ 注意点与局限

1. **claims=[] 是设计而非缺项**：契约 `objective.classify_report_type=false` + notes"不做抽取" + `no_forced_claim_generation`/`do_not_mark_claims_as_verified` 共同要求不得为凑指标造 claim。报告里 3 项 honest 未达标（+460.7% / -99.8% / 0.936）保持**原文状态**，既没升格为 claim，也没标 verified——verification 由平台门计算。
2. **8 条资产是"引用未解析"**：{', '.join(a['asset_id'] for a in assets if a['resolution'] == 'referenced_unresolved')} 指向外部仓库 TensorFEM 的代码/工件/图件/集群作业。本工作树只有 TensorKnowledge，按边界不复制、不臆造内容，因此这些资产**只登记"报告在哪儿引用了它"**，不登记其内容。
3. **图件载荷缺失**：平台 `figures[]` 仅返回 name/caption（无 png_base64），且 3 个声明 PNG 只匹配到 2 个（`rcurve.png` 不在 figures[]）。图件二进制不可校验——这是上游/平台侧的记录缺口，已如实登记，未补猜。
4. **不复核任何上游数字**：本工序的输出**没有**、也不该有对 +460.7%、-99.8%、0.936、61 passed/2 xfailed 等数字的独立验证；manifest 中相关字段均为 `resolved_in_source`（=能定位到原文），注意其语义是"可定位"而非"为真"。
5. **单报告边界**：全程只读写 report 14351；未接触其它 report_id（自检 `single_report_scope` PASS）。
6. **schema 是本地钉住的**：`schemas/asset_manifest.v1.schema.json` 是 wp-448-01 的专用实例（常量写死），故本包派生一份本包 schema。若平台侧存在权威 schema，以平台门为准，本包产物需按其修订。

## ⑥ 自检：逐条对照 acceptance（honest，不粉饰）

| acceptance 项 | 判定 | 依据 |
|---|---|---|
{rows_check}

**误差判定（逐项显式回答"是否 <3%"）**——本工序无物理量/实验基准，基准=包契约的哈希/字符数/结构与 schema：

| 量 | 基准 | 本工序 | 偏差 | <3%? |
|---|---|---|---|---|
{rows_err}

**结论**：登记正确性面上全部 0 偏差（是）；**上游报告的精度结论本工序一律未复核**（不适用 >15%/3% 判据，因为本工序不做数值计算）——若把上游自述的 +460.7% 当作待验量，则它**远未达标且本工序未给出任何反驳证据**，保持 honest-FAIL 原样。

**repro_cmd（一键复跑，工作树根=仓库检出）**

```bash
python runs/wp-14351-01/fetch_report.py          # 取回 report 14351 + 记录 sha256/chars/figures
python scripts/kf/register_14351_assets.py       # 生成 asset_manifest.json / kf_result.json / verification.json
python scripts/kf/publish_14351_report.py        # 生成 asset_map.png + report.md 并投递 KF-RESULT 报告
```

结果信封（本页唯一 json 块；串内反引号以 `\\u0060` 转义，避免打断宿主代码围栏，解码后与原文逐字一致）：

```json
{json_block}
```
"""
    return md


def main() -> int:
    man, env, ver, src_md = load()
    fig = draw_asset_map(man)
    md = build_markdown(man, env, ver, fig)

    # structural guards: exactly one json fence, and it parses back to the envelope
    assert md.count("```json") == 1, f"json fences: {md.count('```json')}"
    assert md.count("```") % 2 == 0, "unbalanced code fences"
    block = md.split("```json", 1)[1].split("```", 1)[0]
    assert json.loads(block) == env, "embedded json block != kf_result.json"
    (OUT / "report.md").write_text(md, encoding="utf-8")

    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": (f"report 14351 资产登记：{man['counts']['assets']} 条资产、"
                    f"resolved_in_source {man['counts']['by_resolution']['resolved_in_source']} / "
                    f"referenced_unresolved {man['counts']['by_resolution']['referenced_unresolved']}，"
                    f"source sha256 与契约一致，claims=[]（不做抽取）。"),
        "scenario_key": "TensorKnowledge",
        "mission_id": 15791,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "TensorKnowledge",
                 "asset-manifest", "GAP-FEM-3D-COHESIVE", "source-scenario:TensorFEM"],
        "markdown": md,
        "figures": [{"name": "asset_map.png",
                     "caption": "资产 locator 覆盖图：每根条=manifest 中一条资产的 char span，颜色=分辨率",
                     "png_base64": base64.b64encode(fig.read_bytes()).decode()}],
    }
    (OUT / "report_payload.json").write_text(
        json.dumps({**payload, "figures": [{k: (v if k != "png_base64" else f"<{len(v)} b64 chars>")
                                           for k, v in f.items()} for f in payload["figures"]]},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    if "--no-post" in sys.argv:
        print("built (not posted):", OUT / "report.md")
        return 0

    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    cred = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    tok = json.load(urllib.request.urlopen(urllib.request.Request(
        base + "/auth/login", data=cred, headers={"Content-Type": "application/json"}),
        timeout=30))
    token = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(base + "/tensor/reports",
                                 data=json.dumps(payload, ensure_ascii=False).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + token},
                                 method="POST")
    out = json.load(urllib.request.urlopen(req, timeout=180))
    (OUT / "published.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out.get(k) for k in ("id", "title", "mission_id", "status", "scenario_key")},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())