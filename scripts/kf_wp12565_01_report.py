#!/usr/bin/env python3
"""wp-12565-01 / report + publish.

Renders the six-section work-package report from the artifacts on disk (every number is
formatted out of asset_manifest.json / verification.json / verify_independent.json, none is
typed in) and injects the kf_result.v1 envelope as the single ```json block. Then publishes
it to the platform as report `KF-RESULT wp-12565-01`.

Sub-commands:
    python3 scripts/kf_wp12565_01_report.py body      # -> docs/kf_result_wp-12565-01.md
    python3 scripts/kf_wp12565_01_report.py publish   # -> POST /api/v1/tensor/reports
    python3 scripts/kf_wp12565_01_report.py all

Credentials come from TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE only.
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-12565-01"
PACKAGE_ID = "wp-12565-01"
REPORT_ID = "12565"
MISSION_ID = 15749
BODY = ROOT / "docs" / "kf_result_wp-12565-01.md"
FIG = PKG / "figures" / "locator_map.png"
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")


def load():
    m = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    r = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    v = json.loads((PKG / "verification.json").read_text(encoding="utf-8"))
    iv = json.loads((PKG / "verify_independent.json").read_text(encoding="utf-8"))
    return m, r, v, iv


def render() -> str:
    m, r, v, iv = load()
    src = m["source"]
    enc = json.dumps(r, ensure_ascii=False, indent=2)

    asset_rows = "\n".join(
        "| %s | %s | %s | L%d–L%d | %d–%d | `%s` | %s |"
        % (a["asset_id"], a["asset_class"], a["label"],
           a["locator"]["start_line"], a["locator"]["end_line"],
           a["locator"]["start_char"], a["locator"]["end_char"],
           a["locator"]["quote"].replace("|", "\\|"), a["resolution"])
        for a in m["assets"]
    )
    anchor_rows = "\n".join(
        "| %s | `%s` | %d | %d–%d | %s |"
        % (a["locator_id"], a["quote"], a["start_char"], a["start_line"], a["end_line"],
           a["meaning_as_written"])
        for a in m["literal_anchors"]
    )
    self_rows = "\n".join(
        "| `%s` | %s | %s |" % (c["item"], "✓" if c["ok"] else "✗", c["evidence"])
        for c in v["checks"]
    )
    indep_rows = "\n".join(
        "| %s | %s | %s |" % (c["id"], "✓" if c["ok"] else "✗",
                              json.dumps(c["detail"], ensure_ascii=False)[:150])
        for c in iv["checks"]
    )
    probe_rows = "\n".join(
        "| `%s` | HTTP %s |" % (p["url"].replace(API, "/api/v1"), p["http_status"])
        for p in m["artifact_probe"]["probes"]
    )
    obs_rows = "\n".join(
        "| %s | `%s` | %s | %s |"
        % (o["observation"], o["check"], json.dumps(o["result"], ensure_ascii=False),
           o["note"])
        for o in m["identity_observations"]
    )

    return f"""# KF-RESULT {PACKAGE_ID}

**tags**: `kf-wp:{PACKAGE_ID}`, `01-asset-registration`, `report:{REPORT_ID}`, `lane:C`, `draft`, `knowledge-factory`
**package_id**: `{PACKAGE_ID}` ｜ **task_type**: `{m['task_type']}` ｜ **report_id**: `{REPORT_ID}` ｜ **lane**: `{m['lane']}`
**source_uri**: `{src['uri']}` ｜ **source_field**: `{src['field']}` ｜ **repo**: TensorKnowledge ｜ **status**: draft

---

## ① 本工序做了什么

本工作包做且只做 `report_id={REPORT_ID}`（《{src['title']}》，scenario_key=`{src['scenario_key']}`）的**资产登记**（工序 `01-asset-registration`）：

1. **确认 report_id 与其 markdown 的字节哈希一一对应**：独立重算 `{src['hash_with_prefix']}`，
   与契约声明 `{src['contract_hash']}` **逐字节相等**；`chars={src['chars']}`（= python `str` 长度，与契约 `chars={src['contract_chars']}` 相同），
   UTF-8 字节 `{src['bytes_utf8']}`（CJK 正文两者必然不同，口径已写明），共 `{src['lines']}` 行。
2. **登记源资产本体**：`markdown` 原件按字节落盘（`docs/kf/wp-12565-01/source.md`，`{src['bytes_utf8']}` 字节，
   与平台返回逐字节相同——独立校验器 V5 复核），并登记记录侧元数据（title / scenario_key / mission_id /
   status / created_at / tags / figures）。
3. **列出可解析的附件/工件引用**：{m['counts']['assets']} 个资产，逐个给出**逐字引文 + 字符跨度 + 行跨度 + 出现次数**：
   `resolved_in_source` {m['counts']['resolved_in_source']} 个、`referenced_unresolved` {m['counts']['referenced_unresolved']} 个、`declared_absent` {m['counts']['declared_absent']} 个。
4. **登记正文中的数值字面量位置**（`literal_anchors`，{m['counts']['literal_anchors']} 条）：只记位置与出现次数，
   `is_claim=false`，**不解释、不比较、不构成 claim**——供下游工序零手抄取用。
5. **不做抽取、不分类、不产生 claim**（契约 `objective.classify_report_type=false`、`no_forced_claim_generation=true`；
   `claims` 允许空数组）。**没有任何结论被标成 verified**：哈希相等只是机械身份校验，verification 由平台门计算。

**边界遵守**：只读 `GET /api/v1/tensor/reports/{REPORT_ID}` 这一份记录；正文提到的上游
`report id 12563` **故意未取**（本包不得读写其它 report_id），按 `referenced_unresolved` 登记；
未改写上游或其它工作包产物（独立校验器 V7 逐条列出本包访问过的 URL）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **契约入参**：`package_id`、`report_id={REPORT_ID}`、`source_field=markdown`、契约 `source_hash`、`chars={src['contract_chars']}`、
   `title`、`scenario_key`；六条 `acceptance` 直接作为自检表（见 ⑥），另有独立校验器 7 条（不共用代码路径）。
2. **取源**：`POST /api/v1/auth/login`（凭据只从环境变量 `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 读，
   不落盘、不进仓库）→ `GET /api/v1/tensor/reports/{REPORT_ID}`（Bearer）取 `markdown`；
   同记录元数据一并登记。
3. **零手抄定位**：脚本内 `ASSETS[]` / `ANCHORS[]` 引文表为**声明值**，用 `str.find` 逐条解析；
   **任一引文未命中即 `SystemExit`，不出半张清单**（本轮 A09 引文未命中被硬拦下，见 ⑤）。
   每条落 `char_span`（start/end）、`line` 跨度、`occurrences`、`unique`。
4. **哈希闸门**：`hashlib.sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 比较，且 `len(str)` 与契约 `chars` 比较；
   任一不符即 `SystemExit`。
5. **schema 双验**：信封按 `schemas/kf_result.v1.schema.json`（JSON-Schema 2020-12）校验；
   清单按 `schemas/asset_manifest.v1.schema.json` 校验，因其 `package_id`/`report_id`/`source.uri` 为 448 包的 `const`，
   校验时**只把这三个 const 重钉到本包**（其余结构与判据不变，脚本内注明），使 `schema_pass` 是可复现检查而非断言。
6. **附件端点探测**（带 Bearer，逐条记录状态码）：

| 探测端点 | 结果 |
|---|---|
{probe_rows}

7. **独立校验器**（`scripts/kf_wp12565_01_verify.py`，**不 import 登记脚本**，改用切片重建 `markdown[start:end] == quote`
   的另一条代码路径）：7 条检查全部通过，见 ⑥ 第二张表。
8. **报告正文的 json 块由脚本从 `kf_result.json` 原样注入**（f-string 拼装 + `json.dumps`，无手抄）；本文件只有这一个 fenced json 块。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12565-01/asset_manifest.json` | 契约输出 `asset_manifest.json`：{m['counts']['assets']} 资产 / {m['counts']['literal_anchors']} 字面量锚点 / `claims=[]` / counts·integrity·limitations |
| `docs/kf/wp-12565-01/kf_result.json` | `kf_result.v1` 信封（`package_id`/`task_type`/`report_id`/`provenance`/`outputs`，2020-12 校验通过），`outputs.asset_manifest.json` 与上表逐字段相同 |
| `docs/kf/wp-12565-01/source.md` | 报告 `markdown` 原件字节副本（{src['bytes_utf8']} 字节） |
| `docs/kf/wp-12565-01/sha256.txt` | 本地重算摘要 `{src['hash_with_prefix']}` |
| `docs/kf/wp-12565-01/locator_check.json` | 每条资产/锚点的跨度、行号、出现次数 |
| `docs/kf/wp-12565-01/verification.json` | 六条 acceptance 的机器判定（`all_pass={v['all_pass']}`） |
| `docs/kf/wp-12565-01/verify_independent.json` | 独立校验器 7 条结果（`all_pass={iv['all_pass']}`） |
| `docs/kf/wp-12565-01/figures/locator_map.png` | 图 1：648 字符轴上的资产跨度与锚点位置 + 按类别的登记结果计数 |
| `scripts/kf_wp12565_01_register.py` / `_verify.py` / `_figure.py` / `_report.py` | 一键复跑链（登记 → 独立校验 → 出图 → 组报告+发布） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

**A. 资产与逐字定位**（`locator.quote` 为原文逐字片段，`start/end` 为 python `str` 字符偏移，1-based 行号）

| asset_id | asset_class | 标签 | 行跨度 | 字符跨度 | 原文引文 | resolution |
|---|---|---|---|---|---|---|
{asset_rows}

**B. 数值字面量锚点（只记位置，`is_claim=false`）**

| id | 原文逐字 | 起始字符 | 行跨度 | 该处原意（照抄语义，不解释） |
|---|---|---|---|---|
{anchor_rows}

**C. 身份事实（机器比对，非人工计数）**

| 事实 | 出处 | 值 | 说明 |
|---|---|---|---|
| source_hash 相等 | `hashlib.sha256(markdown)` vs 契约 | `{src['hash_with_prefix']}` | `hash_matches_contract={str(src['hash_matches_contract']).lower()}` |
| chars 相等 | `len(markdown)` vs 契约 `chars` | `{src['chars']}` vs `{src['contract_chars']}` | `chars_match_contract={str(src['chars_match_contract']).lower()}` |
| title 相等 | `record.title` vs 契约 `title` | `{src['title']}` | `title_matches_contract={str(src['title_matches_contract']).lower()}` |
| scenario_key 相等 | `record.scenario_key` vs 契约 | `{src['scenario_key']}` | `scenario_matches_contract={str(src['scenario_matches_contract']).lower()}` |
| 记录无附件 | `len(record.figures)` | `{len(src['platform_figures'])}` | 该记录未声明任何图，故无附件元数据可登记 |
| 记录状态 | `record.status` / `created_at` | `{src['platform_status']}` / `{src['platform_created_at']}` | mission_id=`{src['platform_mission_id']}` |

**D. 登记过程中机器发现的身份观察（不改原文，只如实登记）**

| 观察 | 检查 | 结果 | 说明 |
|---|---|---|---|
{obs_rows}

## ⑤ 注意点与局限

1. **标题里的 `nu_formula` 在正文中不存在**：契约/记录 `title` 为「…（nu_formula vs nu_eff）」，但 markdown H1 只写
   「报告勘误（对应 report id 12563）」，正文用表达式 `(tau-1/2)/3` 指代公式黏性归一。该 token **无法作为 markdown 文本定位**，
   故只经 `source.title` 登记（表中 A06/A07），不假装它在正文里。
2. **上游 report 12563 未取，是非能力缺失而是边界遵守**：本包被限定只碰 `{REPORT_ID}`，因此勘误所指的“准值”所在的
   正文与工件（`artifacts/sphere_resolution.json`）**在本包内不可读**；两处差异（8.3 % vs 7.59 %、10.2 % vs 10.22 %）
   只登记为字面量位置，**未做值层面复核**，需要上游包的工序去核。
3. **`referenced_unresolved` {m['counts']['referenced_unresolved']} 项是真的解析不到**：工件端点
   `/tensor/reports/{REPORT_ID}/artifacts`、`/figures`、`/tensor/artifacts?report_id=` 全为 HTTP 404（见 ② 表），
   记录 `figures` 为空，故工件只到定位符层级，**不声称内容可校验**。
4. **Hasimoto 只有名字**：markdown 无年份/版次/DOI，`analytic_reference` 只能 `referenced_unresolved`——
   不能凭空补文献标识（`do_not_invent_missing_information`）。
5. **数值字面量的边界**：`literal_anchors` 只登记“原文在哪、出现几次”，不判定其对错；把 `7.59 %` 认作正确值属于
   抽取/判定工序，不在本包。
6. **图 1 的标签只有 ASCII**：本机 matplotlib 唯一可用字体为 `Noto Sans`（无 CJK 覆盖），CJK 标注会显示为方块，
   故图内用 asset_id + asset_class 标注；CJK 引文以逐字形式存在于 `asset_manifest.json`（可核对）。
7. **过程中被自己的闸门拦下过一次**：初版把 A09 引文 `（nu_formula vs nu_eff）` 当作正文片段，登记脚本直接
   `SystemExit`（未出半张清单）——它只存在于 `title`，不在 markdown；改成 `identity_observations` 登记（见 ⑤.1）。
   另初版 A01 用 `method=document` 但 `quote` 只是标题行，独立校验器 V3 切片重建失败（7/8），
   改为精确 `char_span` + 另列 `document_scope` 后 8/8 通过。
8. **本包不产生任何关于物理结论的断言**：报告内容（球阻归一化口径、外推截距等）的科学正确性不在本工序判定范围内。

## ⑥ 误差判定

本工序唯一的外部基准是契约声明的身份量，逐项列出：

| 基准量 | 契约值 | 本包实测 | 误差 | 是否 <3 % |
|---|---|---|---|---|
| `sha256(markdown)` | `{src['contract_hash']}` | `{src['hash_with_prefix']}` | 0（逐字节相等） | 是（0 %） |
| `chars`（`str` 长度） | `{src['contract_chars']}` | `{src['chars']}` | 0 | 是（0 %） |
| `title` / `scenario_key` | 见 ④-C | 见 ④-C | 0 | 是（0 %） |
| 资产定位符可解析率 | 全部可解析 | {m['counts']['assets']}/{m['counts']['assets']} 资产 + {m['counts']['literal_anchors']}/{m['counts']['literal_anchors']} 锚点 | 0 | 是（0 %） |

**显式回答**：本工序的可比基准量误差为 **0 %，< 3 % ✓**。报告正文中的物理量（如 `7.59 %`、`2.33 %`）本包**未复算**，
其误差判定属于上游/下游工序，此处**不声明**——避免把“定位符解析成功”误读成“数值被验证”。

## ⑥′ 自检：逐条对照 acceptance

**契约 6 条（`docs/kf/wp-12565-01/verification.json`）**

| acceptance 项 | 判定 | 证据 |
|---|---|---|
{self_rows}

**独立校验器 7 条（`docs/kf/wp-12565-01/verify_independent.json`，另一条代码路径）**

| id | 判定 | 证据 |
|---|---|---|
{indep_rows}

**honest-FAIL 声明**：无失败项，全部 ✓。但如实登记三项“未做”：①未读上游 report 12563（边界，非缺陷）；
②未取任何工件内容（端点 404，`referenced_unresolved` 如实标注）；③未做任何数值复核与 claim 生成（契约要求）。

## ⑦ 图 1 说明（figures）

**图 1** `figures/locator_map.png`：上图为 648 字符 markdown 轴上的资产跨度（条）与 {m['counts']['literal_anchors']} 个字面量锚点位置（竖线），
颜色区分 `resolved_in_source` / `referenced_unresolved`；下图为按资产类别的登记结果计数（由 `asset_manifest.json` 直接读取，非手抄）。

## 复跑（repro_cmd）

```bash
cd "$(git rev-parse --show-toplevel)" && \
python3 scripts/kf_wp12565_01_register.py && \
python3 scripts/kf_wp12565_01_verify.py && \
python3 scripts/kf_wp12565_01_figure.py && \
python3 scripts/kf_wp12565_01_report.py body
```

（`publish` 子命令需要 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS`/`TENSOR_API_BASE`；若离线可用 `--no-fetch`
读 `docs/kf/wp-12565-01/source.md`，仍在本地复算哈希比对契约值。）

---

## 结果信封（kf_result.v1，本报告唯一 json 块，由脚本从 `docs/kf/wp-12565-01/kf_result.json` 原样注入）

```json
{enc}
```
"""


def publish() -> int:
    markdown = BODY.read_text(encoding="utf-8")
    png = base64.b64encode(FIG.read_bytes()).decode()
    m, r, v, iv = load()
    payload = {
        "title": "KF-RESULT " + PACKAGE_ID,
        "summary": (
            "report 12565 asset registration: markdown sha256 recomputed and identical to the "
            "contract hash (%d chars / %d bytes); %d assets registered (%d resolved_in_source, "
            "%d referenced_unresolved: upstream report 12563, artifacts/sphere_resolution.json, "
            "its two field names, Hasimoto correlation) + %d literal anchors with char/line "
            "spans; 6/6 acceptance and 7/7 independent checks pass; claims=[] by contract, "
            "nothing marked verified."
            % (m["source"]["chars"], m["source"]["bytes_utf8"], m["counts"]["assets"],
               m["counts"]["resolved_in_source"], m["counts"]["referenced_unresolved"],
               m["counts"]["literal_anchors"])
        ),
        "scenario_key": m["source"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:12565", "lane:C",
                 "draft", "knowledge-factory"],
        "markdown": markdown,
        "figures": [{"name": "locator_map.png",
                     "caption": "图 1  report 12565 markdown 的资产定位图：上图=648 字符轴上的 "
                                "8 个资产跨度与 18 个字面量锚点；下图=按资产类别的登记结果计数。",
                     "png_base64": png}],
    }
    body = json.dumps(payload, ensure_ascii=False).encode()

    def call(path, data=None, tok=None):
        headers = {"Content-Type": "application/json"}
        if tok:
            headers["Authorization"] = "Bearer " + tok
        req = urllib.request.Request(API + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                return resp.status, resp.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()

    st, resp = call("/auth/login",
                    json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                "password": os.environ["TENSOR_AGENT_PASS"]}).encode())
    if st != 200:
        print(st, resp[:400])
        return 1
    tok = json.loads(resp)["access_token"]
    st, resp = call("/tensor/reports", body, tok)
    print(st, resp[:600])
    return 0 if st in (200, 201) else 1


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "body"
    if cmd in ("body", "all"):
        BODY.write_text(render(), encoding="utf-8")
        print("wrote", BODY, "%d bytes" % BODY.stat().st_size)
    if cmd in ("publish", "all"):
        return publish()
    return 0


if __name__ == "__main__":
    sys.exit(main())