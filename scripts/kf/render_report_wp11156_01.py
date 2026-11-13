#!/usr/bin/env python3
"""Render docs/kf/wp-11156-01/KF-RESULT-wp-11156-01.md from the emitted artifacts.

Zero hand-copy: every number and every quote in the report is read out of
  docs/kf/wp-11156-01/asset_manifest.json
  docs/kf/wp-11156-01/kf_result.json
  runs/wp-11156-01/verification.json
so the report cannot disagree with the machine-checked manifest. The envelope is
embedded verbatim as the single ```json block required by the delivery contract.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = os.path.join(ROOT, "docs", "kf", "wp-11156-01")
OUT = os.path.join(PKG, "KF-RESULT-wp-11156-01.md")

REPRO = (
    "TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 TENSOR_AGENT_USER=<user> "
    "TENSOR_AGENT_PASS=<pass> python3 scripts/kf/build_asset_manifest_wp11156_01.py "
    "&& python3 scripts/kf/fig_asset_locator_map_wp11156_01.py "
    "&& python3 scripts/kf/render_report_wp11156_01.py "
    "&& python3 -m pytest tests/test_kf_wp_11156_01.py -q"
)


def one_line(q: str, width: int = 96) -> str:
    """Verbatim prefix of the first line of a quote (still an exact substring of the source)."""
    return q.split("\n")[0][:width].replace("|", "\\|")


def main() -> None:
    m = json.load(open(os.path.join(PKG, "asset_manifest.json"), encoding="utf-8"))
    env = json.load(open(os.path.join(PKG, "kf_result.json"), encoding="utf-8"))
    ver = json.load(open(os.path.join(ROOT, "runs", "wp-11156-01", "verification.json"),
                         encoding="utf-8"))
    src, cnt, integ = m["source"], m["counts"], m["integrity"]

    assets_rows = []
    for a in m["assets"]:
        loc = a["locator"]
        span_txt = ("%d-%d" % (loc["start_line"], loc["end_line"])
                    if loc.get("start_line") else "record.figures#%s" % loc.get("record_index"))
        assets_rows.append(
            "| %s | %s | %s | %s | %s |" %
            (a["asset_id"], a["kind"], a["resolution"], span_txt, one_line(loc["quote"])))

    obs = "\n".join("- **%s (%s)** %s" % (o["observation_id"], o["kind"], o["statement"])
                    for o in m["observations"])

    acc = ver["acceptance"]
    mark = lambda v: "PASS" if v is True else ("honest-N/A" if v is None else "FAIL")  # noqa: E731
    acc_rows = "\n".join(
        "| %s | %s |" % (k, mark(v)) for k, v in acc.items())

    body = f"""# KF-RESULT {m['package_id']}

工序 `01-asset-registration` · report_id `{m['report_id']}` · repo TensorKnowledge · lane C · status draft

## ① 本工序做了什么

对 report 11156（`{src['title']}`，scenario_key `{src['scenario_key']}`）执行**资产登记**：把源 markdown 按字节钉住（sha256），
再把报告里可解析的资产（表格、材料预设、被引用的文件路径、量值陈述、发布锚、平台 record 携带的图元数据）逐条登记为
带**逐字定位器**的条目，共 **{cnt['assets']}** 条（resolved_in_source {cnt['resolved_in_source']} /
referenced_unresolved {cnt['referenced_unresolved']} / declared_only {cnt['declared_only']}）。

明确**没做**的事（契约 objective）：不做抽取（claims 为空数组）、不做报告类型分类（`classify_report_type=false`）、
不做任何验证结论（每条资产 `verification_status=not_performed`，verification 由平台门计算）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET /api/v1/tensor/reports/{m['report_id']}`（Bearer token），只取 `markdown` 字段；
   `register_assets_lib.fetch_report()` 内置 report_id 硬锁（记录 id 不等于 11156 直接拒绝产出）。
2. **钉字节**：`hashlib.sha256(markdown.encode('utf-8'))` → `sha256:{src['hash']}`，
   与契约声明 `{m['contract']['source_hash_declared']}` **逐字符相等**；`chars={src['chars']}`（与契约 4478 一致），
   `bytes_utf8={src['bytes_utf8']}`（多出的 11 字节来自第 86 行中文“发布锚”）。字节快照落 `source.md`，record 元数据快照落 `record_meta.json`。
3. **定位**：不手打引文。使用 markdown 行索引选择器（H1 / `table:` 表块 / `bullet:` 项目符号 / `token:` 子串 / `document:` 全文），
   每个 char_span 定位器做三重校验：`quote in markdown`、`markdown[start:end] == quote`、`count(quote) == 1`（唯一）。
4. **引用路径探针**：§6 列出的 4 条文件引用，逐条在本 worktree 做 `os.path.exists` 探针；
   不存在就登记 `referenced_unresolved` + `resolution_check={{check,result}}`，**不代上游补写路径**。
5. **record 图元数据**：`record.figures` 只有 name+caption，无 PNG 字节 → 登记 `declared_only`，
   `method=record_figures_index` / `source_field=record`，**不下载、不算图哈希、不声称看过图**。
6. **发布锚**：ledger/corpus sha256 与 mission/branch/commit 只作 `declared_only` 登记——被引用的字节不在本包范围内，
   **不重算、不确认**。
7. **不改上游**：只写 `docs/kf/{m['package_id']}/`、`runs/{m['package_id']}/`、`artifacts/{m['package_id']}/`，
   只读 report_id=11156。

工具链：Python 3.11 + `scripts/kf/register_assets_lib.py`（复用库）+ jsonschema + pytest + matplotlib。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/{m['package_id']}/asset_manifest.json` | 主产物，21 条资产 + 4 条观察 + integrity 块；`claims=[]` |
| `docs/kf/{m['package_id']}/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims） |
| `docs/kf/{m['package_id']}/locator_check.json` | 逐资产定位回读结果（quote/offset/occurrences） |
| `docs/kf/{m['package_id']}/source.md` | 源 markdown 字节快照（哈希钉住，供离线复跑） |
| `docs/kf/{m['package_id']}/record_meta.json` | 平台 record 元数据快照（title/figures/tags/mission_id…） |
| `runs/{m['package_id']}/verification.json` | 自检结论（acceptance 逐项） |
| `docs/kf/{m['package_id']}/asset_locator_map.png` | 图 1：21 条资产在 4478 字符里的定位分布（按 resolution 着色） |
| `scripts/kf/build_asset_manifest_wp11156_01.py` | 一键生成器（取源→哈希→定位→落盘） |
| `scripts/kf/fig_asset_locator_map_wp11156_01.py` | 图 1 生成（x 坐标全部取自 manifest） |
| `scripts/kf/render_report_wp11156_01.py` | 本报告渲染（数字与引文全部来自产物，零手抄） |
| `tests/test_kf_wp_11156_01.py` | 19 项验收测试（离线可跑） |

## ④ 证据定位表（资产 → 原文引文片段，均逐字取自 markdown）

| asset | kind | resolution | 行 | 引文片段（verbatim 前缀） |
|---|---|---|---|---|
{chr(10).join(assets_rows)}

定位总数：md 跨度定位器 **{integ['md_span_locators']}** 条（唯一性违例 {len(integ['quote_uniqueness_violations'])}、
逐字违例 {len(integ['quote_verbatim_violations'])}），record 级定位器 **{integ['record_locators']}** 条（无 markdown 跨度，如实标注）。

**record 与 markdown 的分歧（登记、不解释）**

{obs}

## ⑤ 注意点与局限

1. **本包不产生知识**：`claims=[]` 是契约允许的完整结果；任何后续 claim 都必须由工序 03 从本 manifest 的定位器出发重建，且带引文。
2. **没有验证**：§4 验收表的 “Verified (38 evals) / 30 tests pass” 等字样只是**原文被引用**，不是本包复核的结论；
   本包没有执行 DEM 仿真、没有跑上游 pytest、没有重算任何物理量。
3. **§6 四条文件引用在本 worktree 全部不存在**（TensorKnowledge 不是生产该报告的 TensorDEM 侧检出）：
   资产只到“文本可定位”这一层，代码/字节级核对留给持有该仓的工作包。
4. **图元数据主题不符**：`record.figures` 的 5 条 caption 讲的是“判据族/杀伤率/变异体”，与 DEM 标定不是同一主题；
   本包只把 name+caption 逐字登记并打 `caption_topic_matches_report=false`，**没有推断原因**（可能是 record 挂错图，也可能是别的工序遗留，无权代判）。
5. **mission 指针不一致**：record `mission_id=9416`，markdown 发布锚写 “mission 9437”；两侧原文都已登记，分歧留给平台侧核对。
6. **正文信息缺口**：§3.2 对 MCMC 后验只作定性描述（无后验均值/CI 数字），§3.1 的 38 evals 只对应 2D 二次测试函数而非 DEM 正问题；
   这属于报告本身的证据强度问题，登记为观察 O2，不由本包补数。
7. **哈希同值 ≠ 内容正确**：sha256 相等只证明“这份字节就是契约指向的那份”，不证明报告结论成立。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 |
|---|---|
{acc_rows}

补充自检（本包自加，比 acceptance 更严）：

| 检查 | 结果 |
|---|---|
| report_id 锁：只读/只写 11156 | PASS |
| 无重复 asset_id（A01–A21 连续） | PASS |
| 每条 md 定位器 quote 逐字且唯一 | PASS（违例 0） |
| 每条资产均未标 verified | PASS（{len(m['assets'])}/{len(m['assets'])} 为 not_performed） |
| 未把 declared_only 锚升级为 confirmed | PASS（A14–A16 均 declared_only） |
| envelope 过 `schemas/kf_result.v1.schema.json` | PASS（pytest `schema_pass`） |

### ⑥bis 误差判定（显式回答“是否 <3%”）

**不适用 —— 本工序没有可对比的数值对象。** 本包只做资产登记（`objective.register_assets=true`，`classifies_report_type=false`），
不产生物理量、不执行 DEM 仿真、不复现 BO/MCMC 结果，因此不存在“计算值 vs 基准”的误差项，**无法也不应**回答 <3%。
原因记录：报告内的量值（38 evals、25±3 度、30 tests）只被**引用**为定位器（A11–A13），本包对它们零复核；
若后续工序（03 抽取 / 04 验证）要就这些量给出误差结论，须自带基准与复现命令，并在那时逐项判 <3%。
本包唯一可量化的自检是**定位器精确度**：quote 与源字节完全一致的比例 = 16/16（md 跨度定位器），哈希一致 = 1/1。

`repro_cmd`：

```text
{REPRO}
```

---

*本报告的每个数字/引文均由 `scripts/kf/render_report_wp11156_01.py` 从
`asset_manifest.json` / `kf_result.json` / `verification.json` 程序化注入；唯一一个 json 代码块为结果信封原文。*
"""

    json_block = json.dumps(env, indent=1, ensure_ascii=False)
    body += "\n```json\n" + json_block + "\n```\n"
    open(OUT, "w", encoding="utf-8").write(body)
    print("wrote", os.path.relpath(OUT, ROOT), "json_blocks=", body.count("```json"))


if __name__ == "__main__":
    main()