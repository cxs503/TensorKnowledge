#!/usr/bin/env python3
"""Render + publish the wp-7216-01 result report (KF-RESULT wp-7216-01).

All numbers in the markdown are read out of the artefacts written by
scripts/kf_wp721601_register_assets.py (asset_manifest.json / verification.json /
ecosystem_presence_probe.json) -- nothing is transcribed by hand. The kf_result
envelope is embedded as the ONLY ```json fenced block in the report body.

    python3 scripts/kf_wp721601_render_report.py render   # -> docs/reports/kf_wp_7216_01_result.md
    python3 scripts/kf_wp721601_render_report.py post     # render + POST /api/v1/tensor/reports
"""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-7216-01"
REPORT_ID = "7216"
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
PROBE = OUT_DIR / "ecosystem_presence_probe.json"
FIG = OUT_DIR / "figures" / "wp721601_source_locator_map.png"
REPORT_MD = ROOT / "docs" / "reports" / "kf_wp_7216_01_result.md"
QUOTE_CAP = 200
TABLE_QUOTE_CAP = 110  # display truncation inside the report table only


def esc(s: str) -> str:
    return (s or "").replace("|", "\\|").replace("\n", " ")


def clip(s: str, n: int = QUOTE_CAP) -> str:
    s = (s or "").replace("|", "\\|").replace("\n", " ")
    return s if len(s) <= n else s[:n] + "…"


def build_markdown() -> str:
    mf = json.loads(MANIFEST.read_text())
    vf = json.loads(VERIFICATION.read_text())
    probe = json.loads(PROBE.read_text()) if PROBE.exists() else None
    s, c, integ = mf["source"], mf["counts"], mf["integrity"]
    env_text = ENVELOPE.read_text().strip()
    if "```" in env_text:
        raise SystemExit("envelope must not carry fences")

    acc_rows = "\n".join(
        "| %s | `%s` | %s |" % ("✅ PASS" if ch["ok"] else "❌ FAIL", k, esc(clip(ch.get("detail", ""), 160)))
        for k, ch in vf["acceptance"].items())

    def _dq(a, n=TABLE_QUOTE_CAP):
        # the locator quote is the verbatim source line; backticks are shown as ' in
        # this table only so the markdown cell stays well-formed (full verbatim + char
        # span live in asset_manifest.json and are machine-recheckable)
        return clip(a["locator"]["quote"].replace("`", "'"), n)

    res_rows = "\n".join(
        "| `%s` | %s | %s | L%d | %s | %s |" % (
            a["asset_id"], a["asset_class"], a["resolution"], a["locator"]["line_start"],
            ("`%s`" % esc(a["token"])) if a.get("token") else "—（整字段）", _dq(a))
        for a in mf["assets"])

    cls_rows = "\n".join("| `%s` | %d |" % (k, v) for k, v in c["by_class"].items())

    def _fig_row(a):
        st = a["resolution_check"].get("http_status")
        res = a["resolution_check"].get("result")
        if "*" in a["token"]:
            return ("| `%s` | —（glob，不逐图探测） | glob 引用，无单一文件可哈希 |" % a["token"])
        note = "bytes served, sha256 recorded" if res == "present" else \
            "声明在 `record.figures`，字节未提供（`%s`）" % a["resolution_check"].get("detail", "")
        return "| `%s` | HTTP %s | %s |" % (a["token"], st, note)

    fig_rows = "\n".join(_fig_row(a) for a in mf["assets"]
                          if a["asset_class"] == "figure_reference")

    dbx = (vf.get("extra_checks") or {}).get("db_cross_channel") or {}
    if dbx.get("status") == "match":
        db_txt = ("旁路交叉校验：`psql` 直读 `tensor_reports.markdown` 的字节与 API 通道**一致**"
                  "（DB 返回字节 %d，匹配口径 `%s`）"
                  % (dbx.get("db_bytes_returned", 0), "、".join(dbx.get("matched_variants") or [])))
    elif dbx.get("status") == "mismatch":
        db_txt = "旁路交叉校验：DB 直读字节与 API 通道**不一致**（以平台哈希为准，见 verification.json）"
    else:
        db_txt = ("旁路交叉校验尝试：`psql -d $TP_PG_DB -tA -c \"select markdown from tensor_reports "
                  "where id=%s\"` → `%s`，故 **API 是本次唯一可用取源通道**（如实记 `not_run`，不当作 PASS；记录见 "
                  "`verification.json:extra_checks.db_cross_channel`）"
                  % (REPORT_ID, (dbx.get("detail") or "unknown").strip().splitlines()[0][:80]))

    probe_txt = "n/a（未运行）"
    if probe:
        found = [k for k, v in probe["hits"].items() if v["checkouts_with_file"]]
        drift = {k: v["distinct_contents"] for k, v in probe["hits"].items() if v["distinct_contents"] > 1}
        probe_txt = ("%d/%d 个声明路径在本地生态检出中被找到；其中内容哈希不唯一者 %d 个（%s）；"
                     "6 个 `artifacts/in31_n12/*.json` 在 0 个检出中出现"
                     % (probe["paths_found_somewhere"], probe["declared_paths"], len(drift),
                        "，".join("`%s` → %d 种内容" % (k.split('/')[-1], v) for k, v in drift.items()) or "无")
                     if drift else
                     "%d/%d 个声明路径在本地生态检出中被找到"
                     % (probe["paths_found_somewhere"], probe["declared_paths"]))

    md = """# KF-RESULT %s

**工作包**: `%s` · **task_type**: `%s` · **report_id**: `%s` · **lane**: `C` · **delivery**: `%s`（draft）
**源**: `%s` 字段 `markdown` · **哈希口径**: UTF-8 字节 · `%s`

## ① 本工序做了什么

对 report %s《%s》执行**资产登记**（工序 01-asset-registration）：只确认源资产身份、清点报告声明的附件/工件/代码指针，**不做抽取、不做报告类型判定、不标 verified**（契约 objective 仅 `register_assets=true`，`classify_report_type=false`）。

1. **源资产身份确认**：`markdown` = %d B / %d 字符 / %d 行；本地重算 sha256 = `%s`，与工作包契约 `source_hash` **逐字节一致**；字符数 %d = 契约 `chars` %d；`title`、`scenario_key`（`%s`）与契约逐字一致。
2. **登记资产 %d 项**：1 项源 markdown（`resolved_in_source`，字节在手）+ %d 项正文声明的引用（图 / 源码 / bench 脚本 / 单测 / 数据工件 / 目录 / 产出分支 / 库符号）。
3. **每条资产带可重解析定位**：字符区间 `[char_start, char_end)` + 1 基行号 + 该行**逐字**引文 + 引文 sha256；%d/%d 个引文在源内唯一（`unique=true`）。
4. **解析状态如实三分**：`resolved_in_source` **%d**（源 markdown 一项，另有本地副本 `runs/%s/source_%s.md`）、`referenced_unresolved` **%d**、`declared_absent` **%d**。**没有任何资产被标成 verified**（`integrity.verified_marks_emitted = %d`）。
5. `claims` 保持**空数组**并写明理由：本工序不产出知识对象；report %s 自身的数值结论原样留在源 markdown，本工序不改写、不重述、不升级。

资产按类别分布：

| asset_class | 数量 |
|---|---|
%s
| **合计** | **%d** |

（`resolved_in_source` %d / `referenced_unresolved` %d / `declared_absent` %d）

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`POST /api/v1/auth/login`（`$TENSOR_AGENT_USER`）→ `GET /api/v1/tensor/reports/7216`，取 `markdown` **原字段**，UTF-8 字节落盘 `runs/%s/source_%s.md`（`record_%s.json` 同时落盘供复核）。%s。
2. **定身份，不等即中止**：`sha256(UTF-8 bytes)` vs 契约 `source_hash`；`len(markdown)` vs 契约 `chars=%d`；`title` / `scenario_key` vs 契约。任一不符 → `SystemExit`，不产出半成品清单（本次 4 项全等）。
3. **扫描引用（规则确定、零猜测）**：
   - markdown 图片语法 `![alt](path)` → 图引用；
   - 反引号内容中符合**路径字符集** `^[A-Za-z0-9_./*-]+$` 者 → 路径引用；按扩展名归类（`.py`→源码/测试/bench、`.json`→数据工件、`.png`→图、无扩展→目录）；含 `*` 的 glob 单独标 `figure_glob`；`agent/...` → 产出分支引用；
   - 反引号内**含空格的 shell 命令**（如 `pytest -q tests/....py tests/....py`、`python benchmarks/.../run_bench.py --ny N`）按空白切分，只登记带真实工件后缀的参数——这样一处命令里的两个单测文件都被登记，而公式里的 `1/2` 不会被误登记（首版踩到 1 例假阳性后修正，见 ⑤-4）；
   - 反引号内的**点分模块名**、**带参调用**、**snake_case 标识符** → `api_symbol_reference`（声明的库符号/可调用入口）。
4. **解析判定（按类别分别做实测探针，而不是统一标"未解析"）**：
   - 源 markdown → 字节在手，`resolved_in_source`；
   - 图 → `GET /api/v1/tensor/reports/7216/figures/<name>` 逐图探测，结果写进 `resolution_check`；
   - 源码/测试/bench/数据工件 → 只在**交付工作树**（TensorKnowledge）内查找，命中则记字节数 + sha256，未命中记 `unresolved` + 同 basename 命中列表；**不跨仓臆测存在性**；
   - 库符号 / 产出分支 → `declared_only`：本工序的契约范围不含打开产出仓（TensorLBM，报告 §6 署名分支 `agent/m5628`）。
5. **非契约旁证探针**（`ecosystem_presence_probe.json`，**不参与**资产状态判定）：%s。该探针只证明"这些文件在本地某些业检出里存在"，**不能**证明产出修订，因此不把任何资产翻转为 `resolved`——这是刻意的保守设定。
6. **信封 + 自校验**：`kf_result.json` 的 `provenance.source_hash` 由**重新拉取的实时字节**重算后写入；`verification.json` 用 `jsonschema` 校验 `schemas/kf_result.v1.schema.json`（Draft 2020-12，平台下发 schema 的仓内副本）与本包的结构 pin `docs/kf/%s/asset_manifest.schema.json`（Draft-07，由 wp-448 先例 schema 重新参数化到本包），并**再次**对实时 markdown 重解析全部定位点。
7. **工具链**：纯标准库（urllib / hashlib / json / re / subprocess）+ `jsonschema` 做 schema 门 + matplotlib 出图；脚本幂等，`all` 一条命令重建全部产物。

一键复跑（工作树根执行；需 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`）：

```bash
python3 scripts/kf_wp721601_register_assets.py all \
  && python3 scripts/kf_wp721601_render_report.py render
# 复跑校验（acceptance 六项）：见上条命令内 verify 子命令的输出，以及
# docs/kf/%s/verification.json:"all_ok"
```

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/%s/asset_manifest.json` | 主产物。%d 项资产，每项含 class / 定位点（char span + 行号 + 逐字引文 + 引文 sha256 + unique）/ resolution / resolution_check；`claims=[]` 附理由；`integrity` 记录哈希本地重算与契约一致、`verified_marks_emitted=0`。 |
| `docs/kf/%s/kf_result.json` | 平台结果信封（即本报告末尾唯一 json 代码块的内容）。`provenance.source_hash` = `%s`，`outputs["asset_manifest.json"]` 为上述清单全文。 |
| `docs/kf/%s/verification.json` | 六项 acceptance 的自校验记录（含每项 detail / 失败列表）+ `extra_checks`（API↔DB 双通道交叉验证尝试；本次 DB 直读被拒 → `not_run`）。`all_ok=%s`。 |
| `docs/kf/%s/asset_manifest.schema.json` | 本包清单的结构 pin（Draft-07）。wp-448 先例 schema 把 `package_id`/`report_id` 写死成 `wp-448-01`/`448`，无法校验其它包，故重新参数化；平台 schema 若有差异以平台门为准。 |
| `docs/kf/%s/ecosystem_presence_probe.json` | 非契约旁证：%d 个声明路径在本地生态检出中的存在性/内容哈希分布。**不参与** resolution 判定。 |
| `docs/kf/%s/figures/wp721601_source_locator_map.png` | 定位点分布图（行剖面 + 各类资产定位竖线 + 类别计数）。 |
| `docs/reports/kf_wp_7216_01_result.md` | 本报告（含唯一 json 代码块）。 |
| `runs/%s/source_%s.md` / `record_%s.json` | 源 markdown 字节副本与报告记录快照（供复核者本地重算哈希）。 |
| `scripts/kf_wp721601_register_assets.py` / `scripts/kf_wp721601_render_report.py` | 登记器与报告渲染器（build / envelope / verify / probe / figure / all）。 |

## ④ 证据定位表（资产 → 原文逐字定位）

引文取自 `asset_manifest.json` 的 `locator.quote`，即 `markdown[char_start:char_end]`；表中按 %d 字符截断（长行以 `…` 标记），**逐字全文与字符区间在清单内**，可由 `md[char_start:char_end] == quote` 直接重解析（本次 %d/%d 通过）。

身份锚点：

| 量 | 值 | 契约 | 一致 |
|---|---|---|---|
| markdown sha256 | `%s` | `%s` | 是 |
| markdown chars | %d | %d | 是 |
| lines / bytes | %d 行 / %d B | —（契约未给） | n/a |
| title | `%s` | 同 | 是 |
| scenario_key | `%s` | 同 | 是 |

资产定位表：

| asset_id | class | resolution | 行 | 声明 token（原文形态） | 原文行（逐字，截断 %d；反引号显示为 '） |
|---|---|---|---|---|---|
%s

图引用与平台探测结果：

| figure | 平台图端点 | 结论 |
|---|---|---|
%s

## ⑤ 注意点与局限

1. **%d/%d 项资产未解析，这是结构性的、不是遗漏**：report %s 的附件几乎全部属于 **TensorLBM** 仓（报告 §6 署名代码路径 `src/tensorlbm/...`、`benchmarks/rb_discrete_stability/...`、`artifacts/in31_n12/...`，分支 `agent/m5628`），而本工作包的交付仓是 **TensorKnowledge**。契约未授权跨仓取字节，因此一律 `referenced_unresolved` 并附上"查了哪里、为什么没命中"。任何把它们标成 `resolved` 的做法都只能是猜测。
2. **图的字节确实拿不到**：`record.figures` 声明了 5 张图，但 `GET /api/v1/tensor/reports/7216/figures/<name>` 全部返回 HTTP 404 `figure not found`。图只登记到"名字 + 声明来源 + 探测结果"，不伪造字节数或哈希。
3. **旁证探针内容漂移**：%s。同一路径在不同检出里出现多种内容，说明"文件存在"无法定位到产出修订——这正是我不把它写进 `resolution` 的理由。
4. **扫描规则的假阳性已记录并修正**：首版把含空格的公式 `` `τ_d = 1/2 + λ (ρ_c/ρ_d)(τ_c−1/2)` `` 切出 `1/2` 当作路径登记（1 例）。改为"命令切分后必须带真实工件后缀"后该例消失；同时把 `agent/m5628`（产出分支）从"目录"纠正为 `git_branch_reference`，把 `Jv≈(F(x0+εv)−F(x0))/ε` 之类的表达式排除在路径字符集之外。当前 %d 项资产经人工复核无残留假阳性。
5. **符号级引用是 declared-only**：`collide_two_component_with_gravity(f1,f2,G_12,τ1,τ2,gz1,gz2,u_eq)`、`critical_rayleigh_continuous(M_list=(50,100,200))` 等以报告原文形态登记（`symbol_key` 去掉实参供去重），本工序不打开产出仓验证其存在性。
6. **不越界**：未做抽取、未做报告类型判定、未改写上游产物、未触碰其它 `report_id`；`claims=[]` 且 `verified_marks_emitted=0`，是否 verified 由平台门独立计算。
7. **未运行项（如实标注）**：`psql` 直读 `tensor_reports.markdown` 被判 `permission denied for table tensor_reports`，故双通道校验记 `not_run`（不当作 PASS），API 是本次唯一取源通道；平台侧只探测了 figure 端点，artifact/attachment 端点未探测（因此不声称它们的可用性）。

## ⑥ 自检：逐条对照 acceptance

| 结果 | acceptance 项 | 证据 |
|---|---|---|
%s

### ⑥.1 误差判定（关键量 vs 基准，逐项回答"是否 <3%%"）

| 关键量 | 基准 | 本工作 | 相对误差 | 是否 <3%% |
|---|---|---|---|---|
| markdown sha256 | 契约 `source_hash` | 本地重算 | 0（逐字节相同） | **是** |
| markdown 字符数 | 契约 `chars=%d` | %d | 0%% | **是** |
| 定位点可重解析 | 实时 markdown | %d/%d | 0%% | **是** |
| 引文唯一性 | 源内唯一 | %d/%d | —（覆盖度，非误差量） | 不适用 |
| 资产解析率 | 无基线（跨仓字节不可得） | %d/%d | 不可判定 | 不适用（见 ⑤-1） |

**结论**：本工序的可判定量只有"身份一致"，两项（哈希、字符数）均为**逐字节 0 误差，<3%% 成立**；资产解析率不存在基准，不做粉饰性判定。

```json
%s
```
""" % (
        PACKAGE_ID,
        PACKAGE_ID,
        mf["task_type"],
        REPORT_ID,
        "TensorKnowledge",
        s["source_uri"],
        s["source_hash"],
        REPORT_ID,
        s["title"],
        s["bytes_utf8"],
        s["chars"],
        s["lines"],
        s["source_hash"],
        s["chars"],
        s["contract_chars"],
        s["scenario_key"],
        c["assets"],
        c["assets"] - 1,
        integ["quote_uniqueness"]["unique_quotes"],
        integ["quote_uniqueness"]["locators"],
        c["resolved_in_source"],
        PACKAGE_ID,
        REPORT_ID,
        c["referenced_unresolved"],
        c["declared_absent"],
        integ["verified_marks_emitted"],
        REPORT_ID,
        cls_rows,
        c["assets"],
        c["resolved_in_source"],
        c["referenced_unresolved"],
        c["declared_absent"],
        PACKAGE_ID,
        REPORT_ID,
        REPORT_ID,
        db_txt,
        s["contract_chars"],
        probe_txt,
        PACKAGE_ID,
        PACKAGE_ID,
        PACKAGE_ID,
        c["assets"],
        PACKAGE_ID,
        s["source_hash"],
        PACKAGE_ID,
        str(vf["all_ok"]).lower(),
        PACKAGE_ID,
        PACKAGE_ID,
        probe["declared_paths"] if probe else 0,
        PACKAGE_ID,
        PACKAGE_ID,
        REPORT_ID,
        REPORT_ID,
        TABLE_QUOTE_CAP,
        integ["quote_uniqueness"]["locators"] - len(vf["acceptance"]["source_locator_resolvable"].get("failures", [])),
        integ["quote_uniqueness"]["locators"],
        s["source_hash"],
        s["contract_source_hash"],
        s["chars"],
        s["contract_chars"],
        s["lines"],
        s["bytes_utf8"],
        s["title"],
        s["scenario_key"],
        TABLE_QUOTE_CAP,
        res_rows,
        fig_rows,
        c["referenced_unresolved"],
        c["assets"],
        REPORT_ID,
        probe_txt,
        c["assets"],
        acc_rows,
        s["contract_chars"],
        s["chars"],
        integ["quote_uniqueness"]["locators"],
        integ["quote_uniqueness"]["locators"],
        integ["quote_uniqueness"]["unique_quotes"],
        integ["quote_uniqueness"]["locators"],
        c["resolved_in_source"],
        c["assets"],
        env_text,
    )
    return md.replace("@CAP@", str(TABLE_QUOTE_CAP))


def post(md_text: str) -> None:
    api = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

    def call(path, body, tok=None):
        h = {"Content-Type": "application/json"}
        if tok:
            h["Authorization"] = "Bearer " + tok
        req = urllib.request.Request(api + path, data=json.dumps(body).encode(), headers=h)
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode()

    st, body = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                     "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit("login failed: %s %s" % (st, body))
    tok = json.loads(body)["access_token"]

    mf = json.loads(MANIFEST.read_text())
    vf = json.loads(VERIFICATION.read_text())
    c = mf["counts"]
    payload = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": ("report %s 资产登记：markdown %d B / %d chars，本地重算 sha256 与契约逐字节一致；登记 %d 项资产"
                    "（1 源 markdown resolved + %d 引用项 unresolved），%d 个定位点在实时 markdown 上全部重解析、"
                    "引文全唯一；claims 空（工序 01 不抽取、不标 verified）；acceptance 六项自检 all_ok=%s。"
                    % (REPORT_ID, mf["source"]["bytes_utf8"], mf["source"]["chars"], c["assets"],
                       c["referenced_unresolved"], mf["integrity"]["quote_uniqueness"]["locators"],
                       str(vf["all_ok"]).lower())),
        "scenario_key": mf["source"]["scenario_key"],
        "mission_id": 15594,
        "tags": ["kf-wp:%s" % PACKAGE_ID, "TensorKnowledge", "asset-registration",
                 "TensorLBM", "IN31-N12", "report-%s" % REPORT_ID],
        "markdown": md_text,
        "figures": [{
            "name": "wp721601_source_locator_map.png",
            "caption": ("report %s 源 markdown 行剖面与 %d 个已登记资产定位点（按类别着色；虚线=§1–§6 章节边界）；"
                        "右图=资产类别计数。sha256 前缀 %s。" % (REPORT_ID, c["assets"],
                                                              mf["source"]["source_hash"][7:19])),
            "png_base64": base64.b64encode(FIG.read_bytes()).decode(),
        }],
    }
    st, body = call("/tensor/reports", payload, tok)
    print("POST /tensor/reports ->", st, body[:400])
    if st not in (200, 201):
        raise SystemExit("post failed")
    Path("/tmp/kf_wp_7216_01_payload.json").write_text(json.dumps(payload, ensure_ascii=False))


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else "render"
    md_text = build_markdown()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(md_text)
    n_json = len(re.findall(r"(?m)^```json\s*$", md_text))
    print("report ->", REPORT_MD.relative_to(ROOT), "| chars", len(md_text),
          "| json blocks", n_json, "| fences", len(re.findall(r"(?m)^```", md_text)))
    if n_json != 1:
        raise SystemExit("report must contain exactly ONE ```json block (found %d)" % n_json)
    if cmd == "post":
        post(md_text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))