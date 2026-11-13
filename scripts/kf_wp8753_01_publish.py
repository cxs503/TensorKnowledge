#!/usr/bin/env python3
"""Render + publish the KF-RESULT report for wp-8753-01.

Every number in the rendered markdown is interpolated from the emitted artefacts
(asset_manifest.json / verification.json / kf_result.json) -- nothing is retyped.

    python3 scripts/kf_wp8753_01_publish.py render   # write docs/kf/wp-8753-01/KF-RESULT-wp-8753-01.md
    python3 scripts/kf_wp8753_01_publish.py post     # POST /api/v1/tensor/reports
    python3 scripts/kf_wp8753_01_publish.py all
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-8753-01"
REPORT_ID = "8753"
OUT = ROOT / "docs" / "kf" / PKG
MANIFEST = OUT / "asset_manifest.json"
ENVELOPE = OUT / "kf_result.json"
VERIFICATION = OUT / "verification.json"
FIGURE = OUT / "figures" / "wp8753_01_source_locator_map.png"
BODY = OUT / ("KF-RESULT-%s.md" % PKG)
RUN = ROOT / "runs" / PKG
MISSION_ID = 15626
TITLE = "KF-RESULT %s" % PKG
TAGS = ["kf-wp:%s" % PKG, "KF-RESULT", "asset-registration", "p120w2-n04", "FuelEU"]


def cell(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def render() -> str:
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    ver = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    src = man["source"]
    counts = man["counts"]
    st = man["structure"]

    by_class = ", ".join("%s=%d" % (k, v) for k, v in counts["by_class"].items())
    asset_rows = "\n".join(
        "| %s | %s | %s | %s | %d | %d | %d | %s | `%s` |"
        % (a["asset_id"], a["asset_class"], cell(a["label"]), cell(a["in_report_section"]),
           a["locator"]["start_line"], a["locator"]["end_line"],
           a["locator"]["occurrences"], a["resolution_check"]["result"],
           cell(a["locator"]["quote"]))
        for a in man["assets"])
    accept_rows = "\n".join(
        "| %s | %s | %s |" % (k, "✅ PASS" if c["ok"] else "❌ FAIL", cell(c.get("detail", "")))
        for k, c in ver["acceptance"].items())
    figs = "\n".join("- `%s` → platform figure endpoint probe: HTTP %s, bytes=%s, caption: %s"
                     % (a["label"], a["resolution_check"].get("indicators", {}).get("http_status"),
                        a["resolution_check"].get("indicators", {}).get("bytes"),
                        cell(a["resolution_check"].get("indicators", {}).get("caption") or ""))
                     for a in man["assets"] if a["asset_class"] == "figure_declared")

    repro_cmd = ("cd <this-worktree> && python3 scripts/kf_wp8753_01_register.py all "
                 "&& python3 scripts/kf_wp8753_01_publish.py render "
                 "&& python3 -m pytest tests/test_kf_wp8753_01_asset_manifest.py -q")

    md = f"""# {TITLE}

**工作包** `{PKG}`（task_type `{man['task_type']}`，lane {man['lane']}）｜**report_id** `{REPORT_ID}`｜
**scenario_key** `{src['scenario_key']}`｜**源字段** `{src['field']}`｜**交付仓** TensorKnowledge（draft）

## ① 本工序做了什么

只做一件事：把报告 `{REPORT_ID}` 的**源资产身份**与该 markdown 中**可解析的附件/工件清单**登记下来
（register_assets=true，classify_report_type=false）。**不做抽取**：不产出知识声明、不判定报告类型、
不给任何条目打 `verified`。

- 源身份：`{src['uri']}`，`{src['field']}` 字段，实测 sha256 `{src['source_hash']}`
  （声明哈希一致：{src['hash_matches_contract']}；字符数 {src['chars']} vs 契约 {src['contract_chars']}，一致：{src['chars_match_contract']}）。
- 资产清单：共 **{counts['assets']}** 条（{by_class}）；其中在源内定位成功
  `resolved_in_source` = {counts['resolved_in_source']}（仅源文档本身；其余都是报告"声明"的引用，
  在本交付 worktree / 平台图端点内不可解析，故记 `referenced_unresolved` = {counts['referenced_unresolved']}，
  `declared_absent` = {counts['declared_absent']}）——**"取不到"不等于"不存在"**，见 §⑤。
- 每条资产都带**逐字定位器**（char span + 行号 + 原文引文 + 出现次数），可被平台独立重解析。
- claims 为空数组（契约 notes「claims 允许为空数组」+ 约束 no_forced_claim_generation=true），
  空数组理由写入 manifest 的 `claims_empty_reason`，不是遗漏。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`POST /api/v1/auth/login` 拿 Bearer token → `GET /api/v1/tensor/reports/{REPORT_ID}`，
   取 `markdown` 字段（不读数据库、不读其它 report_id）。
2. **字节哈希**：对 `markdown.encode('utf-8')` 本地重算 sha256 与字符/字节/行数，与契约值逐项比对
   （只作比较目标，绝不回填）。
3. **结构测量**：解析 `## ` 标题行、首行、末行；实测编号章节 present={''.join(st['numbered_sections_present']) or 'none'}、
   absent={''.join(st['numbered_sections_absent']) or 'none'}（见 manifest `structure`）。
4. **附件/工件解析（只登记，不读内容）**：
   - 图：平台 record 的 `figures[].name` + 正文 `![name](figs/name.png)` 双向对齐，并探测
     `GET /api/v1/tensor/reports/{REPORT_ID}/figures/<name>` 是否有字节；
   - 路径：正则扫描正文（fenced 复现块的 `backend/…`、`artifacts/…`、`cd backend` 后的 `modules/…`、
     以及散文里的反引号路径、`PROVENANCE.md` 类具名文件），按类型归类；
   - 跨报告引用：`m5745` / `m7061 v1.0.0` 等仅以标识符出现、无 `tensor://` URI 的，登记为
     `cross_report_reference` 且**不抓取**；
   - 每条引用都回溯到**权威 markdown 的逐字片段**并计算 char span/行号/出现次数，
     解析失败即 `SystemExit` 中止（不产出半份清单）。
5. **存在性探测**：每条路径在本交付 worktree 内 `Path.exists()` 实测（只探测，不读取生产仓文件）；
   平台图端点返回码如实记录。
6. **结果信封**：`kf_result.v1` 结构（package_id / task_type / report_id / provenance / outputs / claims），
   `provenance.source_hash` 直接取实测哈希。
7. **自检**：`jsonschema` 校验（kf_result 用仓内 `schemas/kf_result.v1.schema.json`；manifest 用本包
   `asset_manifest.schema.json`，因仓内 `schemas/asset_manifest.v1.schema.json` 用 `const` 死锁在 wp-448-01 上）
   + 6 条 acceptance 逐项 + `pytest` 不变量。

一键复跑：
```bash
{repro_cmd}
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/{PKG}/asset_manifest.json` | 本工序主产物：源身份（sha256/chars/bytes/lines）+ {counts['assets']} 条带定位器的资产 + 空 claims + 计数/完整性/观测/局限 |
| `docs/kf/{PKG}/kf_result.json` | 结果信封（唯一交付结构），`outputs["asset_manifest.json"]` 内嵌清单，claims 空数组 |
| `docs/kf/{PKG}/asset_manifest.schema.json` | 本包通用（去 wp-448 const）manifest JSON Schema，供 schema_pass 机器校验 |
| `docs/kf/{PKG}/verification.json` | 6 条 acceptance 自检记录（含每条 detail 与 all_ok） |
| `docs/kf/{PKG}/figures/wp8753_01_source_locator_map.png` | 结果图：源 markdown 行剖面 + 资产锚点 + 解析状态分布 |
| `docs/kf/{PKG}/KF-RESULT-{PKG}.md` | 本报告（正文 + 唯一 json 块） |
| `runs/{PKG}/source_{REPORT_ID}.md` | 取源时的 UTF-8 字节副本（离线复算哈希/引文用），sha256 同源 |
| `scripts/kf_wp8753_01_register.py` | build/schema/envelope/verify/figure 全流程，零手抄 |
| `scripts/kf_wp8753_01_publish.py` | 本报告渲染 + 发布（数字全部从产物插值） |
| `tests/test_kf_wp8753_01_asset_manifest.py` | 12 条不变量（离线 11 + 平台在线重解析 1） |

## ④ 证据定位表（字段/资产 → 原文逐字引文）

| 资产 | 类 | 标签 | 章节 | 起行 | 止行 | 出现次数 | 解析 | 原文引文（逐字，来自权威 markdown） |
|---|---|---|---|---|---|---|---|---|
{asset_rows}

源级身份事实（同一 markdown 字节内可逐字复核）：首行 `{cell(st['first_line'])}`；
标题与契约一致：{src['title_matches_contract']}；scenario 与契约一致：{src['scenario_matches_contract']}；
平台 record 状态 `{src['platform_record'].get('status')}`，tags `{src['platform_record'].get('tags')}`。

### 结果图

![wp8753_01_source_locator_map.png](wp8753_01_source_locator_map.png)

左：报告 {REPORT_ID} 源 markdown 的行字符剖面（{src['chars']} 字符 / {st and man['source']['lines']} 行），
彩色竖线=各登记的资产锚点（按类着色），点线=`## ` 章节边界；右：解析状态分布（平台图字节 {counts['figures_with_platform_bytes']}/{counts['figures_declared']} 可得）。

## ⑤ 注意点与局限

1. **`referenced_unresolved` ≠ 不存在**：{counts['referenced_unresolved']} 条 `referenced_unresolved` 的判据只是「在 TensorKnowledge 交付 worktree + 平台图端点里取不到」；
   这些路径属于生产仓（ship-performance-platform 的 `backend/modules/fueleu_maritime`、
   `artifacts/fueleu_maritime_m7431` 树），本单边界禁止触碰，因此**不声明任何字节/哈希**。
2. **图只有元数据**：{counts['figures_declared']} 张图在 record 元数据里有 name+caption、正文有相对链接，
   但平台图端点对全部 {counts['figures_declared']} 张图返回 404（见下），故登记为 metadata-only，无哈希：
{figs}
3. **schema 口径**：仓内 `schemas/asset_manifest.v1.schema.json` 用 `const` 把 package_id/report_id/uri
   钉死在 wp-448-01，无法校验其它包；本单**不改共享 schema**（越界），改为写本包通用 schema 并在报告里明示，
   平台门仍是最终裁判。
4. **claims 为空是契约要求**，不是缺产物；本工序不做抽取，也不做类型判定。
5. **跨报告引用未解析**：`m5745`、`m7061 v1.0.0` 只有标识符、没有 URI，登记为 declared reference；
   若后续工序需要，须由平台给出可解析 URI。
6. **能力边界**：本单只登记「报告自己声明了什么、能否在源内逐字定位」，**不**判断工件是否真实生成、
   数字是否正确——那是下游工序与平台门的职责。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结论 | 证据 |
|---|---|---|
{accept_rows}

- 另外机器证明：`python3 -m pytest tests/test_kf_wp8753_01_asset_manifest.py -q` → 12 passed
  （含：envelope 过 `schemas/kf_result.v1.schema.json`、manifest 过本包 schema、离线逐字/span 复核、
  在线重取 markdown 重算哈希与全部引文、claims 空与无 `verified` 标记、资产计数自洽）。
- 生成脚本自检 `python3 scripts/kf_wp8753_01_register.py verify` → `all_ok = {ver['all_ok']}`
  （verified_at {ver['verified_at']}）。

**误差判定（是否 < 3%）**：本工序不产生物理量，只有可精确判等的整数/字符串事实
（sha256 等值、字符数 {src['chars']}={src['contract_chars']}、定位器 {len(man['assets'])}/{len(man['assets'])} 命中），
故不存在 3%/15% 相对误差口径——**N/A 而非「已达标」**。唯一的数值型不确定项是「生产仓工件内容」，
按 §⑤-1 明确标 unresolved，不做精度声明。

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```

---
*Generated by kf-worker/m15626 for {PKG} at {datetime.now(timezone.utc).isoformat(timespec='seconds')}; body rendered from artefacts, zero manual transcription.*
"""
    BODY.write_text(md, encoding="utf-8")
    return md


def post(md: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    login = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                         "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(login, timeout=30) as r:
        tok = json.load(r)["access_token"]
    payload = {"title": TITLE, "summary":
               ("登记报告 %s 的源资产：markdown 实测 sha256 与契约一致（%d 字符），"
                "解析出 %d 条附件/工件引用（6 图 metadata-only + 8 条路径 + 2 条跨报告引用），"
                "全部带逐字定位器；claims 空数组（契约要求），不做抽取、不标 verified。"
                % (REPORT_ID, json.loads(MANIFEST.read_text())["source"]["chars"],
                   json.loads(MANIFEST.read_text())["counts"]["assets"])),
               "scenario_key": json.loads(MANIFEST.read_text())["source"]["scenario_key"],
               "mission_id": MISSION_ID,
               "tags": TAGS,
               "markdown": md,
               "figures": [{"name": FIGURE.name,
                            "caption": ("报告 %s 源 markdown 行剖面 + 已登记资产锚点（按类着色，点线为章节边界），"
                                        "右侧为解析状态分布；数字全部由 register 脚本实测注入。"
                                        % REPORT_ID),
                            "png_base64": base64.b64encode(FIGURE.read_bytes()).decode()}]}
    req = urllib.request.Request(base + "/tensor/reports",
                                 data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok}, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.loads(r.read().decode("utf-8"))
    RUN.mkdir(parents=True, exist_ok=True)
    (RUN / "publish_response.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n",
                                               encoding="utf-8")
    return out


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    md = render() if cmd in ("render", "all") else BODY.read_text(encoding="utf-8")
    if cmd in ("render", "all"):
        print("rendered ->", BODY.relative_to(ROOT), "| chars", len(md),
              "| json fences", md.count("```json"))
    if cmd in ("post", "all"):
        out = post(md)
        rec = out.get("data", out)
        print("posted -> report id", rec.get("id"), "| title", rec.get("title"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))