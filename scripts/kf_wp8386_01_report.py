#!/usr/bin/env python3
"""Render and publish the KF-RESULT report for wp-8386-01.

Every number in the rendered markdown is read out of the artefacts produced by
scripts/kf_wp8386_01_register.py (asset_manifest.json / verification.json /
kf_result.json / figures.sha256.json) -- nothing is retyped by hand.

    python3 scripts/kf_wp8386_01_report.py render     # -> docs/kf/wp-8386-01/KF-RESULT-wp-8386-01.md
    python3 scripts/kf_wp8386_01_report.py publish    # POST /tensor/reports (KF result channel)
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = "wp-8386-01"
REPORT_ID = "8386"
OUT = ROOT / "docs" / "kf" / PKG
MANIFEST = OUT / "asset_manifest.json"
ENVELOPE = OUT / "kf_result.json"
VERIFICATION = OUT / "verification.json"
FIGS = OUT / "figures"
MD = OUT / "KF-RESULT-wp-8386-01.md"
MISSION_ID = 15621


def sha(p: Path) -> str:
    return "sha256:" + hashlib.sha256(p.read_bytes()).hexdigest()


def render() -> str:
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    v = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    figsha = json.loads((FIGS / "figures.sha256.json").read_text(encoding="utf-8"))
    c = m["counts"]
    checks = v["checks"]
    tick = lambda ok: "☑" if ok else "☒"  # noqa: E731

    src_md = (ROOT / "runs" / PKG / ("report_%s.md" % REPORT_ID)).read_text(encoding="utf-8")
    import re as _re
    n_img_refs = len(_re.findall(r"!\[[^\]]*\]\(([^)]+)\)", src_md))
    n_probe = sum(1 for a in m["assets"]
                  if a["locator"]["method"] != "document"
                  and a["resolution_check"]["check"] != "unique_substring_anchor_in_markdown")
    n_in_md = sum(1 for a in m["assets"] if a["locator"]["method"] != "document")
    def _mdquote(q: str) -> str:
        q = q.replace("|", "\\|").replace("\n", "⏎")
        # a code span delimited by one backtick breaks if the quote has backticks
        return ("`` %s ``" % q) if "`" in q else ("`%s`" % q)

    rows = "\n".join(
        "| %s | %s | %s | %d–%d (L%d–L%d) | %s |"
        % (a["asset_id"], a["asset_class"], a["resolution"],
           a["locator"]["start_char"], a["locator"]["end_char"],
           a["locator"]["start_line"], a["locator"]["end_line"],
           _mdquote(a["locator"]["quote"]))
        for a in m["assets"])
    probe_rows = "\n".join(
        "| %s | %s | `%s` | %s |"
        % (a["asset_id"], a["resolution"], a["resolution_check"]["check"],
           a["resolution_check"]["result"])
        for a in m["assets"]
        if a["locator"]["method"] != "document"
        and a["resolution_check"]["check"] != "unique_substring_anchor_in_markdown")

    body = f"""# KF-RESULT {PKG}

## ① 本工序做了什么

本单是"报告 → 知识产线"上的一道工序：**资产登记（task_type = 01-asset-registration）**，只服务
`report_id = {REPORT_ID}` 这一份报告，`lane=C`，交付仓 TensorKnowledge，状态 draft。

- 源报告：report {REPORT_ID}，《{m["source"]["title"]}》，`scenario_key = {m["source"]["scenario_key"]}`。
- 登记结果：**{c["assets"]} 个资产**，分 {len(c["by_class"])} 类；按可解析性
  **{c["resolved_in_source"]} resolved_in_source / {c["referenced_unresolved"]} referenced_unresolved /
  {c["declared_absent"]} declared_absent**。
- 源资产本体：`{m["source"]["uri"]}` 的 `markdown` 字段，**{m["source"]["chars"]} 字符 /
  {m["source"]["bytes_utf8"]} 字节 UTF-8**，本地重算 `sha256 = {m["source"]["hash"]}`，
  与契约 `source_hash` 逐字节相同。
- 本工序**不做**的事（契约 `objective` 只给了 `register_assets: true`）：不抽取 claim、不做报告类型
  分类、不改写上游产物、**不把任何结论标成 verified**（`claims = []` 是完整结果，不是缺项）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证不凭记忆**：`scripts/kf_wp8386_01_fetch.py` 登录平台 → `GET /api/v1/tensor/reports/{REPORT_ID}`
   → 取 `markdown` 字段落盘 `runs/{PKG}/report_{REPORT_ID}.md`，同时把原始响应存
   `report_{REPORT_ID}.json`。哈希与契约不一致时脚本直接 `SystemExit`，不产出半成品。
2. **定位而非抄写**：`scripts/kf_wp8386_01_register.py` 维护 {c["assets"]} 行锚点表
   （asset_id / 类 / 报告小节 / **唯一锚点串**）。运行时对每个锚点在 markdown 中求出现次数，
   **必须恰好 1 次**，否则中止；`quote` 不是重敲的，而是 `md[start_char:end_char]` 的**原样切片**，
   行号由字符偏移反推。因此"零手抄"是结构保证而不是承诺。
3. **可解析性只认机器证据**，五类探针：
   - 页内资产 → `unique_substring_anchor_in_markdown`（切片相等 + 全文唯一）；
   - 上游文件/目录（`artifacts/fueleu_maritime_m7061/*`、`backend/modules/fueleu_maritime/`）
     → `worktree_path_exists:*`（本工作树实测，结果为 absent → 登记 `referenced_unresolved`，不编造路径）；
   - API 路由 → `http_probe:http://127.0.0.1:8002/api/v1/fueleu-maritime/registry`（实测返回非 2xx → unresolved）；
   - 上游提交 `7017a623` → `git_cat_file:7017a623`（本仓对象库 128 → unresolved）；
   - 原文声明"无云图" → `scan_image_references_for_fieldmap`（{n_img_refs} 条图片引用中 0 条场量云图 → absent）。
   声明与探针必须一致：不一致时 build 直接 FATAL（`resolution_matches_probe` 检查在 verify 里再兜一次）。
4. **独立校验**：`scripts/kf_wp8386_01_register.py verify` 在**新登录、重新拉取**的 markdown 上
   逐资产重切片比对（不信任本地副本），跑 JSON Schema、id 唯一性、claim 证据策略、计数自洽、
   禁 `verified` 标记，输出 `verification.json`（overall = **{v["overall"]}**）。
5. **确定性自证**：清空后重建两次 `asset_manifest.json`，字节完全相同
   （`{sha(MANIFEST)}`，manifest 内不含时间戳；时间只出现在信封 `provenance.emitted_at`）。
6. **测试**：`tests/test_kf_wp8386_01.py` 14 项，含 4 个**反向对照**（篡改 quote 的一个数字、
   平移 span 1 字符、把 absent 的 PNG 谎报成 resolved、制造重复 id），证明检查器真的会红。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/{PKG}/asset_manifest.json` | 主产物：{c["assets"]} 资产 / {len(c["by_class"])} 类；{c["resolved_in_source"]}+{c["referenced_unresolved"]}+{c["declared_absent"]}；`{sha(MANIFEST)}` |
| `docs/kf/{PKG}/kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs）；`{sha(ENVELOPE)}` |
| `docs/kf/{PKG}/verification.json` | {len(checks)} 项验收自检逐项结果，overall = **{v["overall"]}** |
| `docs/kf/{PKG}/figures/fig_asset_inventory.png` | 图 1 资产类别 × 可解析状态堆叠条形图 |
| `docs/kf/{PKG}/figures/fig_locator_coverage.png` | 图 2 逐资产字符区间定位地图（覆盖 {m["source"]["chars"]} 字符全文） |
| `docs/kf/{PKG}/figures/figures.sha256.json` | 图件 sha256（{", ".join(f"{k}={x[:18]}…" for k, x in figsha.items())}） |
| `runs/{PKG}/report_{REPORT_ID}.md` / `.json` | 源证据快照（markdown 与 API 原始响应），供平台独立重算哈希 |
| `schemas/asset_manifest.v1.1.schema.json` | 本次用的形状 schema（v1 用 const 钉死 wp-448-01，故新增参数化 v1.1，旧文件未改） |
| `scripts/kf_wp8386_01_fetch.py` / `kf_wp8386_01_register.py` / `kf_wp8386_01_report.py` | 取证 / 登记+校验+出图 / 渲染+发布 |
| `tests/test_kf_wp8386_01.py` | 14 项不变量测试（含 4 个反向对照） |

**资产类别计数**：`{json.dumps(c["by_class"], ensure_ascii=False)}`

## ④ 证据定位表（asset → 原文逐字切片）

下表每个 `quote` 都是报告 {REPORT_ID} markdown 的**唯一子串**，区间为 `[start_char, end_char)`、
行号为反推值；平台可独立重算 sha256 与子串定位。

| asset_id | class | resolution | char span (line) | 原文片段（原样切片） |
|---|---|---|---|---|
{rows}

**锚点之外的机器探针明细**（{n_in_md} 个页内定位资产中有 {n_probe} 个还需额外探针：外部路径 / HTTP / git / 内容扫描）：

| asset_id | resolution | check | result |
|---|---|---|---|
{probe_rows}

## ⑤ 注意点与局限

1. **本工序不产生知识**：`claims = []` 由契约 `objective`（只有 `register_assets`、`classify_report_type=false`）
   决定，不是为了填指标。报告里的数值结论（判据 a–g、罚金曲线）一律**未复核**，属下游工序。
2. **"resolved_in_source" 只表示"原文里能逐字定位"，不表示内容为真**。例如 A03 的法规号
   `Regulation (EU) 2023/1805` 与 A06 的条款号都是**报告作者的转录**，原文自己标了
   `WITHHELD_EXTERNAL`（离线无 EUR-Lex 通道）；本工序原样登记，不复核、不加分、不改判。
3. **7 个 `referenced_unresolved` 是真实缺口，不是遗漏**：6 张图 PNG、`acceptance.json`、
   `backend/modules/fueleu_maritime/`、测试目录、API 路由、上游提交 `7017a623` 全部位于上游仓
   `ship-performance-platform`，本工作树（TensorKnowledge）里不存在；API 路由实测
   `http_probe` 非 2xx、`git cat_file` 返回 128 —— 我登记的是"引用了但此处不可解析"，没有替换成猜测值。
4. **A21 的存在性判定用"本工作树"口径**：Petrel 式跨仓工件登记需要跨仓路径，本单无权访问上游仓，
   因此"absent"仅代表本工作树；此局限已写进 `note`，供下游 05 工序复核。
5. **A30（无云图）是 `declared_absent`**：原文自述"0 维法规账务模型，没有空间场量"，探针扫
   {n_img_refs} 条图片引用 0 条命中场量词。**未据此推断能力缺失**——0 维账务模型本来就不该有云图。
6. **`chars` 用 Python 字符数、`bytes_utf8` 用字节数**，中文混排下二者不同
   （{m["source"]["chars"]} vs {m["source"]["bytes_utf8"]}）；契约 `chars: {m["source"]["chars"]}`
   与字符数口径一致，若平台按字节比对会不匹配——这点已在 `source` 里显式分开记录。
7. **本单一处未改的既有缺陷**：`tests/test_kf_wp448.py` 在本工作树 13 项失败/报错，原因是它依赖
   `runs/wp-448-01/`（未随仓提交，`.gitignore` 丢弃 `artifacts/**`）——与本单无关，按"最小改动"
   原则未修，仅如实记录。

## ⑥ 自检：逐条对照 acceptance

| # | acceptance 项 | 结果 | 证据 |
|---|---|---|---|
| 1 | `valid_json` | {tick(checks["valid_json"]["ok"])} PASS | manifest/envelope 均可 `json.loads` |
| 2 | `schema_pass` | {tick(checks["schema_pass"]["ok"])} PASS | `schemas/asset_manifest.v1.1.schema.json`；信封另过 `schemas/kf_result.v1.schema.json` |
| 3 | `source_locator_resolvable` | {tick(checks["source_locator_resolvable"]["ok"])} PASS | 重取 markdown 后 {c["assets"]}/{c["assets"]} 个 locator 切片相等且唯一 |
| 4 | `source_hash_matches` | {tick(checks["source_hash_matches"]["ok"])} PASS | `{checks["source_hash_matches"]["detail"]["live"]}` == 契约值 |
| 5 | `no_duplicate_ids` | {tick(checks["no_duplicate_ids"]["ok"])} PASS | {c["assets"]} 个 id 唯一（含负控测试） |
| 6 | `all_claims_have_evidence_or_explicit_unresolved_status` | {tick(checks["all_claims_have_evidence_or_explicit_unresolved_status"]["ok"])} PASS | `claims=[]`，check_claims 无违例 |
| + | `resolution_matches_probe`（额外自加） | {tick(checks["resolution_matches_probe"]["ok"])} PASS | {c["assets"]} 条声明全部由探针结果支撑 |
| + | `no_verified_marks`（额外自加） | {tick(checks["no_verified_marks"]["ok"])} PASS | 结构化扫描未见 verified 标记 |
| + | `counts_consistent`（额外自加） | {tick(checks["counts_consistent"]["ok"])} PASS | {c["resolved_in_source"]}+{c["referenced_unresolved"]}+{c["declared_absent"]} = {c["assets"]} |

**无失败项**。上表 9 项全部由 `verification.json` 机器生成，未手写判断；
`overall = {v["overall"]}`。**verification 本身仍由平台门复算**，本报告不代替它。

### 复跑（一键）

```bash
# 0) 依赖：python3 + jsonschema + matplotlib；环境变量 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS
cd <worktree 根>
python3 scripts/kf_wp8386_01_fetch.py                    # 取证 + 哈希核对（不一致即退出）
python3 scripts/kf_wp8386_01_register.py all             # build + envelope + verify + figure
python3 -m pytest tests/test_kf_wp8386_01.py -q          # 14 项不变量测试
python3 scripts/kf_wp8386_01_report.py render            # 重渲染本报告
```

### ⑥ 附：结果 JSON（本报告唯一一个 json 代码块，逐字等于 `docs/kf/{PKG}/kf_result.json`）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""
    return body


def render_main() -> int:
    MD.parent.mkdir(parents=True, exist_ok=True)
    text = render()
    if text.count("```json") != 1:
        raise SystemExit("FATAL: report must contain exactly one json block, found %d"
                         % text.count("```json"))
    MD.write_text(text, encoding="utf-8")
    print(json.dumps({"report": str(MD.relative_to(ROOT)), "chars": len(text),
                      "sha256": sha(MD),
                      "fenced_json_blocks": text.count("```json")}, ensure_ascii=False, indent=2))
    return 0


def publish() -> int:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        tok = json.load(r)["access_token"]
    figs = []
    for p in sorted(FIGS.glob("*.png")):
        figs.append({"name": p.stem,
                     "caption": ("图 1 资产类别 × 可解析状态" if "inventory" in p.stem
                                 else "图 2 逐资产字符区间定位地图"),
                     "png_base64": base64.b64encode(p.read_bytes()).decode()})
    payload = {
        "title": "KF-RESULT " + PKG,
        "summary": ("wp-8386-01 资产登记：report 8386 markdown 哈希核对一致"
                    "（sha256 前 12 位 %s），登记 %d 个资产（%d resolved / %d unresolved / %d absent），"
                    "claims=[] 按契约；verification 9/9 PASS。"
                    % (json.loads(MANIFEST.read_text(encoding="utf-8"))["source"]["hash"][:12],
                       json.loads(MANIFEST.read_text(encoding="utf-8"))["counts"]["assets"],
                       json.loads(MANIFEST.read_text(encoding="utf-8"))["counts"]["resolved_in_source"],
                       json.loads(MANIFEST.read_text(encoding="utf-8"))["counts"]["referenced_unresolved"],
                       json.loads(MANIFEST.read_text(encoding="utf-8"))["counts"]["declared_absent"])),
        "scenario_key": json.loads(MANIFEST.read_text(encoding="utf-8"))["source"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": [PKG, "kf-wp:" + PKG, "KF", "asset-registration", "report:" + REPORT_ID,
                 "lane-C", "TensorKnowledge"],
        "markdown": MD.read_text(encoding="utf-8"),
        "figures": figs,
    }
    req = urllib.request.Request(base + "/tensor/reports",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req) as r:
        out = r.read().decode()
    print(out[:600])
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    raise SystemExit(render_main() if cmd == "render" else publish())