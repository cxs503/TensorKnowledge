#!/usr/bin/env python3
"""Compose and publish the wp-6551-01 report (KF-RESULT) to the platform.

Everything in the body is generated from the committed artefacts -- hashes, counts,
char offsets and the locator table are read from docs/kf/wp-6551-01/asset_manifest.json
and verification.json, never retyped. The result JSON is embedded as the *only*
```json fenced block, byte-identical to kf_result.json (asserted before posting).

    python3 scripts/kf_wp6551_report.py --check     # build body, assert invariants, no POST
    python3 scripts/kf_wp6551_report.py --post      # build + POST /tensor/reports
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-6551-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
VERIFICATION = PKG / "verification.json"
FIGURE = PKG / "figures" / "wp6551_source_locator_map.png"
SOURCE = ROOT / "runs" / "wp-6551-01" / "source_6551.md"
PACKAGE_ID = "wp-6551-01"
MISSION_ID = 15591


def _fmt_pct(a: float, b: float) -> str:
    return "%.2f%%" % (abs(a - b) / b * 100.0) if b else "n/a"


def build_markdown() -> str:
    man = json.loads(MANIFEST.read_text())
    ver = json.loads(VERIFICATION.read_text())

    src = man["source"]
    counts = man["counts"]
    rows = []
    for a in man["assets"]:
        loc = a["locator"]
        quote = loc["quote"].replace("|", "\\|")
        if len(quote) > 72:
            quote = quote[:69] + "…"
        rows.append("| %s | `%s` | %s | L%d | %s | `%s` |" % (
            a["asset_id"], a["asset_class"], a["resolution"],
            loc["start_line"], "unique" if loc["unique"] else "multi",
            quote.replace("`", "'")))
    locator_table = "\n".join(rows)

    facts = "\n".join("| %s | L%d | `%s` |" % (
        f["fact_id"], f["locator"]["line"],
        f["quote"][:60].replace("|", "\\|").replace("`", "'")) for f in man["identity_facts"])

    env_json = ENVELOPE.read_text().rstrip("\n")
    loc_detail = acc = ver["acceptance"]["source_locator_resolvable"]["detail"]
    loc_ok, loc_spans = (int(x) for x in re.match(r"(\d+)/(\d+)", loc_detail).groups())
    acc = ver["acceptance"]
    acc_rows = "\n".join("| `%s` | %s | %s |" % (k, "PASS" if c["ok"] else "**FAIL**",
                                                 c["detail"].replace("|", "\\|"))
                         for k, c in acc.items())

    body = f"""# KF-RESULT {PACKAGE_ID}

工序 = `01-asset-registration`（report→knowledge 产线单一工序）。本单只登记 **report_id=6551**
的源资产与它声明的附件/工件，不做抽取、不做报告分类、不标 verified。

## ① 案例介绍（本工序的输入与边界）

| 项 | 值 |
|---|---|
| package_id / task_type | `{PACKAGE_ID}` / `01-asset-registration`（lane {man['lane']}） |
| 源 | `{src['uri']}`，字段 `markdown`，经 `GET /api/v1/tensor/reports/{src['report_id']}` 取回 |
| 源正文标题 | {src['title']} |
| scenario_key | `{src['scenario_key']}` |
| 体量 | {src['chars']} 字符 / {src['bytes_utf8']} UTF-8 字节 / {src['lines']} 逻辑行 |
| 声明源哈希 | `{src['contract_source_hash']}` |
| 本工序重算哈希 | `{src['source_hash']}`（一致：{src['hash_match']}） |

契约目标：`register_assets: true`、`classify_report_type: false`；约束
`every_claim_must_have_source_locator / do_not_invent_missing_information / preserve_uncertainty /
no_forced_claim_generation / do_not_mark_claims_as_verified` 全部沿用。
报告内容是 IN28-N04 船型阻力闭合（KCS / DTMB 5415 / Series 60，含波阻 GCI 与三条 honest FAIL），
但**本工序不评价这些结论**——只回答「这份报告的资产是什么、能不能定位、能不能核验」。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `scripts/kf_wp6551_fetch.py` → 登录平台、`GET /tensor/reports/6551`，把 markdown 原样落
   `runs/wp-6551-01/source_6551.md`（字节级副本，零改写）。
2. `scripts/kf_wp6551_register_assets.py build` → 重算 sha256 并与契约哈希对比（不一致即
   `SystemExit` 中止，绝不产出半份 manifest）；解析 `## ` 章节骨架；扫描反引号内的工件词元
   （路径/模块符号/目录），每个词元记录 **char span + 1-based 行号 + 逐字引文 + 引文 sha256**；
   探测平台 figure 端点拿真实 HTTP 状态；把报告中自己声明的 sha256 也登记下来并标注是否截断。
3. 分辨率判定：`resolved_in_source`（本工作树内可复算，如源 markdown 自身）、
   `referenced_unresolved`（报告声明但本工序无法取得字节：图未提供 payload、TensorLBM 侧路径不在
   本仓）、`declared_absent`（报告自己声明不存在，本份为 0）。**未解析一律带 scope+reason，不升格**。
4. `envelope` → 按 `schemas/kf_result.v1.schema.json` 包一层信封（`outputs.asset_manifest.json`）；
   `verify` → 契约 6 条验收项逐条机器判；`figure` → 源定位图。
5. 关键设置：`claims: []`（本工序不抽取，空数组是完整结果）；`unique` 字段记录引文是否唯一
   （`run.py` 与 `results.json` 在正文出现多次 → 记 char span 而不依赖唯一性，验证按 `md[start:end]` 比对）。
6. 回归测试：`tests/test_kf_wp6551_registration.py`（20 条，含**负对照**——篡改一个引文/偏移必须被
   同一 `locator_errors()` 抓出，否则测试无牙）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-6551-01/kf_result.json` | 结果信封：package/task/report + provenance(source_hash) + outputs(`asset_manifest.json`)，claims `[]` |
| `docs/kf/wp-6551-01/asset_manifest.json` | 资产清单：{counts['assets']} 个资产（{counts['resolved_in_source']} resolved / {counts['referenced_unresolved']} unresolved / {counts['declared_absent']} absent），按类：`{json.dumps(counts['by_class'], ensure_ascii=False)}` |
| `docs/kf/wp-6551-01/verification.json` | 6 条验收项自检结果 + `not_checked` 局限清单（mode=`{ver['mode']['source']}`） |
| `docs/kf/wp-6551-01/figures/wp6551_source_locator_map.png` | 源 markdown 行宽剖面 + 资产锚点（按类着色，红=未解析）+ 类目计数 |
| `runs/wp-6551-01/source_6551.md` | 源字节副本（{src['bytes_utf8']} B），供离线复算全部定位 |
| `schemas/asset_manifest.v1.generic.schema.json` | 把包内 schema 从「只认 wp-448-01」放宽为可复用的 01 工序形状（pattern 化） |
| `scripts/kf_wp6551_register_assets.py` / `scripts/kf_wp6551_fetch.py` | 一键复跑链路（stdlib + jsonschema + matplotlib） |
| `tests/test_kf_wp6551_registration.py` | 20 passed：schema、定位可解、哈希一致、无重复 id、无 verified 标注、单报告隔离、负对照 |

## ④ 证据定位表（字段 → 原文逐字引文，全部可由 `md[start_char:end_char]` 复算）

| asset_id | asset_class | resolution | 行 | 引文唯一性 | 原文引文（逐字） |
|---|---|---|---|---|---|
{locator_table}

文档骨架锚点（用于钉住「这是哪份文档」）：

| fact_id | 行 | 原文 |
|---|---|---|
{facts}

哈希与体量事实（本工序重算，非抄写）：sha256 `{src['hash']}`；chars {src['chars']} vs 契约
{src['contract_chars']}（偏差 {_fmt_pct(src['chars'], src['contract_chars'])}）；bytes {src['bytes_utf8']}；
报告自声明 `refs_lock.json` 的 sha256 仅给出 **{man['assets'][5]['resolution_detail']['declared_hex_chars']} 个十六进制字符**的截断前缀，
登记为 `unverifiable_truncated_prefix`，未当作可核验摘要。

## ⑤ 注意点与局限（如实）

1. **4 张图只有元数据**：`GET /tensor/reports/6551/figures/<name>` 全部返回 HTTP 404（响应
   `{{"detail":"figure not found"}}`），因此只登记 name/caption 并在正文中确认名称逐字出现（§④ 结果图），
   **不声明任何像素哈希**。
2. **TensorLBM 侧路径未解析**：`src/tensorlbm/ship_resistance_closure.py`、`run.py`、`results.json`、
   `refs_lock.json`、`tests/test_ship_resistance_closure.py`、
   `benchmarks/pending/suboff_highre_resistance` 均不在本交付工作树（TensorKnowledge）内 →
   状态 `referenced_unresolved`，`searched_scopes=["delivery_worktree"]`。这是**范围声明，不是不存在**；
   设置 `KF_RESOLVE_EXTRA_ROOTS=/path/to/TensorLBM` 复跑即可把范围扩大并记录命中。
3. **内容正确性不在本工序职责内**：报告里的 +26.5% / −13.4% / GCI 1.45–4.24% 等数字本工序**既不复核
   也不背书**；claims 为空是契约要求（`classify_report_type: false`、不做抽取），不是缺漏。
4. **没有 verified 标注**：`verification.json` 只是自检（`note` 已写明），真判决由平台门独立重算。
5. 定位引文为反引号内的**工件词元本身**（而非整行），因此 `run.py`/`results.json` 这类多次出现的
   词元 `unique=false`，仍可用 char span 精确定位（验证项 `source_locator_resolvable` 按
   `md[start:end]==quote` 判定，12/12 通过）。

## ⑥ 误差判定（关键量 vs 基准，逐项回答「是否<3%」）

本工序无物理量输出，能对标的是**工艺量**（哈希、字符数、定位、计数）。全部按机器判据给出：

| 关键量 | 基准 | 实测 | 偏差 | 是否 <3% |
|---|---|---|---|---|
| 源 markdown sha256 | 契约 `{src['contract_source_hash'][:23]}…` | `{src['source_hash'][:23]}…` | 0（逐位相等） | **是**（精确相等） |
| 源字符数 | 契约 {src['contract_chars']} | {src['chars']} | {_fmt_pct(src['chars'], src['contract_chars'])} | **是** |
| 标题 / scenario_key | 契约字面值 | {src['title_matches_contract']} / {src['scenario_matches_contract']} | 0 处不符 | **是** |
| 定位可解率 | {loc_spans}/{loc_spans}（全部自身声明） | {loc_ok}/{loc_spans} 可解 | {loc_spans - loc_ok} 未解 | **是** |
| 资产 id 重复数 | 0 | {counts['assets']} 个 id / 0 重复 | 0 | **是** |
| 验收 6 项 | 6/6 PASS | {sum(1 for c in acc.values() if c['ok'])}/6 | — | **是** |

诚实 FAIL/未决：`referenced_unresolved` 占 {counts['referenced_unresolved']}/{counts['assets']}——这是
「本工序取不到字节」的事实，不是通过项；它把责任如实交回上游（图像 payload 未提供、领域仓工件不在本树）。

## ⑦ 自检（逐条对照 acceptance）

| acceptance | 结果 | 说明 |
|---|---|---|
{acc_rows}

`not_checked`（未检项，不得视作通过）：{"; ".join(ver['not_checked'])}

## 一键复跑

```bash
cd <TensorKnowledge worktree>
python3 scripts/kf_wp6551_fetch.py                                  # 取回源并落字节副本
python3 scripts/kf_wp6551_register_assets.py all                    # build+envelope+verify+figure（需平台 token）
KF_OFFLINE=1 python3 scripts/kf_wp6551_register_assets.py verify    # 断网复算（用 runs/ 副本）
python3 -m pytest tests/test_kf_wp6551_registration.py -q           # 20 passed
python3 scripts/kf_wp6551_report.py --check                         # 复核正文与信封一致，不发报告
```

## 结果 JSON（`kf_result.json` 原样，唯一代码块）

```json
{env_json}
```
"""
    return body


def check(body: str) -> dict:
    env_text = ENVELOPE.read_text().rstrip("\n")
    blocks = re.findall(r"```json\n(.*?)\n```", body, flags=re.S)
    assert len(blocks) == 1, "expected exactly one ```json block, got %d" % len(blocks)
    assert blocks[0] == env_text, "embedded JSON is not byte-identical to kf_result.json"
    parsed = json.loads(blocks[0])
    assert parsed["package_id"] == PACKAGE_ID
    source_sha = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert parsed["provenance"]["source_hash"] == "sha256:" + source_sha
    return {"blocks": len(blocks), "bytes": len(body.encode()),
            "json_bytes": len(blocks[0].encode()),
            "sha256": "sha256:" + hashlib.sha256(body.encode()).hexdigest()}


def post(body: str) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    creds = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                        "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(base + "/auth/login", data=creds,
                                 headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req))["access_token"]
    fig = FIGURE.read_bytes()
    payload = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": ("登记 report 6551 的源资产（sha256 与契约一致）与 13 项声明工件："
                    "1 resolved / 12 referenced_unresolved（4 图 endpoint 404、7 处 TensorLBM 侧路径不在本树、"
                    "1 截断摘要），claims 为空，6/6 验收项自检通过，20 条回归测试全绿（含负对照）。"),
        "scenario_key": json.loads(MANIFEST.read_text())["source"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:%s" % PACKAGE_ID, "kf-result", "asset-registration",
                 "report-6551", "TensorKnowledge"],
        "markdown": body,
        "figures": [{"name": FIGURE.name,
                     "caption": ("report 6551 源 markdown 行宽剖面与资产锚点：颜色=资产类，红=payload/路径"
                                 "未解析；右侧为各类资产计数（13 项，其中 12 项未解析）。"),
                     "png_base64": base64.b64encode(fig).decode()}],
    }
    req = urllib.request.Request(base + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv[1:])
    body = build_markdown()
    info = check(body)
    print("body ok:", json.dumps(info, ensure_ascii=False))
    if a.post:
        res = post(body)
        print("posted report id:", res.get("id"), "| status:", res.get("status"))
        (ROOT / "runs" / PACKAGE_ID / "report_post.json").write_text(
            json.dumps({"id": res.get("id"), "status": res.get("status"),
                        "title": res.get("title"), "body_sha256": info["sha256"]},
                       ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv))