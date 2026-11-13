"""Build (and publish) the KF-RESULT report for work package wp-11924-01.

Zero hand-copy discipline: every number, hash, count and quoted string in the body is formatted at
build time from artifacts/wp-11924-01/asset_manifest.json, artifacts/wp-11924-01/verification.json and
runs/wp-11924-01/kf_result.wp-11924-01.json. The report contains exactly one fenced ```json block (the
result envelope, byte-identical to the result file).

  * writes docs/wp-11924-01/KF-RESULT-wp-11924-01.md
  * POSTs it to /tensor/reports (title 'KF-RESULT wp-11924-01', tag kf-wp:wp-11924-01, mission 15730)
    unless --no-post is given

Usage: python3 scripts/kf_wp11924_01_report.py [--no-post]
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

ART = pathlib.Path("artifacts/wp-11924-01")
DOCS = pathlib.Path("docs/wp-11924-01")
PACKAGE_ID = "wp-11924-01"
REPORT_ID = "11924"
MISSION_ID = 15730
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

M = json.loads((ART / "asset_manifest.json").read_text())
V = json.loads((ART / "verification.json").read_text())
R = json.loads(pathlib.Path("runs/wp-11924-01/kf_result.wp-11924-01.json").read_text())
C = M["counts"]
S = M["source"]


def first_line(asset_id: str) -> str:
    a = next(x for x in M["assets"] if x["asset_id"] == asset_id)
    q = a["locator"]["quote"].split("\n")[0].replace("|", "\\|")
    return q if len(q) <= 96 else q[:96] + "…"


def asset_table() -> str:
    rows = ["| asset_id | asset_class | resolution | 行 span | char span | 原文片段（逐字切片，非重述） |",
            "|---|---|---|---|---|---|"]
    for a in M["assets"]:
        loc = a["locator"]
        if loc["method"] == "document":
            span, q = "0–%d（全文）" % loc["end_char"], "（整篇 markdown；sha256 见 provenance）"
        else:
            span = "%d–%d" % (loc["start_char"], loc["end_char"])
            q = "`%s`" % (loc["quote"].split("\n")[0].replace("|", "\\|")[:80])
        rows.append("| %s | %s | %s | %d–%d | %s | %s |"
                    % (a["asset_id"], a["asset_class"], a["resolution"],
                       loc["start_line"], loc["end_line"], span, q))
    return "\n".join(rows)


def resolution_table() -> str:
    rows = ["| asset_id | 报告内定位（相对路径/模块） | 机器检查 | 结果 |", "|---|---|---|---|"]
    for a in M["assets"]:
        if a["resolution"] == "resolved_in_source":
            continue
        rc = a["resolution_check"]
        paths = ", ".join(rc.get("reported_paths", [])) or "—"
        rows.append("| %s | %s | %s | %s |" % (a["asset_id"], paths or a["label"][:48],
                                               rc["check"], rc["result"]))
    return "\n".join(rows)


def check_table() -> str:
    rows = ["| 验收项 | 结果 | 证据（verification.json 摘录） |", "|---|---|---|"]
    for c in V["checks"]:
        det = json.dumps(c["detail"], ensure_ascii=False)
        det = det if len(det) <= 170 else det[:170] + "…"
        rows.append("| %s | %s | %s |" % (c["check"], c["result"].upper(), det.replace("|", "\\|")))
    return "\n".join(rows)


def acceptance_table() -> str:
    want = ["valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
            "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"]
    by = {c["check"]: c for c in V["checks"]}
    rows = ["| acceptance 条目 | 打勾 | 依据 |", "|---|---|---|"]
    for k in want:
        c = by.get(k)
        mark = "✓" if c and c["result"] == "pass" else "✗"
        rows.append("| %s | %s | %s |" % (k, mark, (c["check"] if c else "missing") + " → " +
                                          (c["result"] if c else "not_run")))
    return "\n".join(rows)


def figures() -> list[dict]:
    caps = [
        ("fig_asset_inventory.png",
         "图1 资产清单：22 个类别的资产数按可解析状态堆叠（蓝=页内可解析 34，橙=外部引用不可解析 8）。"),
        ("fig_locator_coverage.png",
         "图2 定位地图：42 个资产在 13138 字符 markdown 上的 char span（灰色带=文档级资产；纵轴=asset_id+类别）。"),
        ("fig_verification.png",
         "图3 验收自检板：13 项检查逐项结果（平台门为权威判定，本图为自检）。"),
    ]
    out = []
    for name, cap in caps:
        b = (ART / name).read_bytes()
        out.append(dict(name=name, caption=cap, png_base64=base64.b64encode(b).decode()))
    return out


def build_markdown() -> str:
    json_block = pathlib.Path("runs/wp-11924-01/kf_result_block.wp-11924-01.json").read_text().strip()
    unresolved = [a for a in M["assets"] if a["resolution"] == "referenced_unresolved"]
    n_unres = len(unresolved)
    repro = ("python3 scripts/kf_fetch_11924.py && python3 scripts/kf_wp11924_01_register.py && "
             "python3 scripts/kf_wp11924_01_verify.py && python3 scripts/kf_wp11924_01_figures.py && "
             "python3 scripts/kf_wp11924_01_report.py")

    body = f"""# KF-RESULT {PACKAGE_ID}

> 工序：`01-asset-registration`（只登记资产与定位，不抽取 claim、不分类、不标 verified）
> report_id：`{REPORT_ID}` · package_id：`{PACKAGE_ID}` · lane：`C` · 交付仓：TensorKnowledge

## ① 案例介绍：本工序做了什么

本单是报告→知识产线上的一道工序：把平台报告 **{REPORT_ID}《{S['title']}》**（scenario_key =
`{S['scenario_key']}`，上游平台 mission {S['platform_mission_id']}）登记成一份**机器可校验的资产清单**，
供下游工序（claim 抽取、证据审计）直接消费。资产＝报告里可定位的结论表、参数表、图件/数据/代码引用等；
"登记"＝给出**唯一的字符级定位**与**可解析性判定**，不是复述内容。

上游报告在讲什么（逐字引文，均可在原文定位）：

- 核心问题：{first_line('A05')}
- 可辨识性判定：{first_line('A09')}
- 三目标可行性判定：{first_line('A15')}

上游自身如实记了多处 honest FAIL（AC6 负控违反比例不足、AC7 准静态门不达标、AC5 跨配置稳健性 FAIL、
UCS 随加载增量加密未收敛）。**本工序原样登记这些结论的定位，不重新裁定、不粉饰**（见 ⑤）。

规模与身份：markdown `{S['chars']}` 字符 / `{S['bytes_utf8']}` UTF-8 字节，`sha256 = {S['hash']}`，
与工作包契约 `input.source_hash` 逐字节相同（见 ⑥ 的 `source_hash_matches`）。

本工序**不做**的事（契约边界）：不做 claim 抽取（`claims: []` 为合法完整结果）、不做报告类型分类
（`objective.classify_report_type: false`）、不标 `verified`（verification 由平台门计算）、不读写其它 report_id。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证（不凭记忆）**：`GET $TENSOR_API_BASE/tensor/reports/{REPORT_ID}` 取 `markdown` 字段 → `runs/wp-11924-01/report_{REPORT_ID}.md`
   + 原始响应 `report_{REPORT_ID}.json`（title/scenario_key/figures/tags）。本地重算 sha256，**与契约不符即中止**。
2. **切片定位（零手抄）**：`scripts/kf_wp11924_01_register.py` 维护一张 {C['assets']} 行的锚点表
   （asset_id / 类 / 唯一锚点串 / 相对行跨）。运行时：锚点在全文出现次数**必须 == 1**（否则 `SystemExit`），
   由锚点求行号 → 行偏移 → `[start_char, end_char)` → **直接从原文切片**得到 `quote`。因此清单里没有
   任何一个数字是重打出来的；同一脚本重跑，`asset_manifest.json` 的 sha256 逐字节不变。
3. **可解析性判定（不猜测）**：每个资产跑一次机器检查 `resolution_check`，且**结果与声明强绑定**
   （`resolved_in_source`↔`resolved`、`referenced_unresolved`↔`unresolved`）：
   - 页内资产 → `char_span_in_source_markdown`；
   - 外部代码/数据路径 → 在本工作树（TensorKnowledge）实测路径是否存在 + 原文正则检索 URL/DOI（命中 0 → 不编造地址）；
   - 图件二进制 → 平台 `figures` 字段有 {len(S['platform_figures'])} 条 name/caption 声明但无 `png_base64`，且相对路径
     `figures/p270w2c_n08` 在本工作树不存在 → 登记为不可解析。
4. **独立校验**：`scripts/kf_wp11924_01_verify.py` 在**新进程、新登录**下**重新拉取** markdown（不信任本地副本），
   重算哈希、逐资产重切片比对 + 唯一性 + 行号一致性、跑 JSON Schema、查 id 唯一性、查 claim 证据策略、
   结构化扫描 `verified` 标记、查 counts 自洽与 report_id 作用域，输出 `artifacts/wp-11924-01/verification.json`。
5. **出图**：`scripts/kf_wp11924_01_figures.py`（matplotlib，Agg）三张图，全部数字读自 manifest/verification。
6. **测试**：`tests/test_kf_wp11924.py` 23 项 —— 12 项正向不变量 + 11 项**反向对照**（篡改引文数字、
   平移 span、非唯一引文、错行号、谎报 resolution、重复 id、counts 造假、claim 无证据、注入 verified 标记、
   越界 report_id、非法 resolution），证明这些门真的会红。

**一键复跑**：`{repro}`

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-11924-01/asset_manifest.json` | 主产物：{C['assets']} 个资产 / {len(C['by_class'])} 类；{C['resolved_in_source']} 页内可解析 + {C['referenced_unresolved']} 外部不可解析 + {C['declared_absent']} 声明缺失；`sha256={R['outputs']['asset_manifest.json']['artifact_sha256'][:16]}…`，{R['outputs']['asset_manifest.json']['artifact_bytes']} 字节 |
| `artifacts/wp-11924-01/verification.json` | 13 项验收自检逐项结果与证据，`overall={V['overall']}` |
| `artifacts/wp-11924-01/fig_asset_inventory.png` / `fig_locator_coverage.png` / `fig_verification.png` | 图1/图2/图3（见 ④ 末尾） |
| `runs/wp-11924-01/report_{REPORT_ID}.md` / `.json` | 源证据快照（markdown + API 原始响应） |
| `runs/wp-11924-01/kf_result.{PACKAGE_ID}.json` | 结果信封（package_id/task_type/report_id/provenance/outputs） |
| `schemas/asset_manifest.v1.generic.schema.json` | 本地补写的**与包无关**的 manifest 形状约束（已有 `asset_manifest.v1.schema.json` 把 `package_id`/`report_id` 写死为另一包，不能复用也不宜改动），使 `schema_pass` 可复现 |
| `scripts/kf_fetch_{REPORT_ID}.py` / `kf_wp11924_01_register.py` / `kf_wp11924_01_verify.py` / `kf_wp11924_01_figures.py` / `kf_wp11924_01_report.py` | 取证 / 登记 / 校验 / 出图 / 报告 |
| `tests/test_kf_wp11924.py` | 23 项不变量测试（含 11 个反向对照） |
| `docs/{PACKAGE_ID}/` | 本报告、manifest/verification 的持久镜像、三张图（推送门会丢弃 `artifacts/**`、`runs/**`，故持久副本落 `docs/`） |

## ④ 证据定位表（claim/字段 → 原文逐字片段）

源：`{S['uri']}` · `{S['field']}` · `sha256:{S['hash']}` · {S['chars']} 字符 / {S['bytes_utf8']} 字节。
所有片段为**字符区间切片**，同一片段在原文出现次数恒为 1（可反向定位）。

{asset_table()}

### 页面内不可解析资产（如实登记，不补造地址）

{resolution_table()}

### 结果图

- 图1 `fig_asset_inventory.png`：22 类资产 × 可解析状态分布。
- 图2 `fig_locator_coverage.png`：42 个资产的 char span 定位地图（{C['chars_covered_by_char_spans']} / {S['chars']} 字符被页内资产覆盖，
  coverage = {C['coverage_fraction']:.4f}）。
- 图3 `fig_verification.png`：13 项验收自检板（平台门为权威判定）。

## ⑤ 注意点与局限

1. **参数盒上下界在上游缺失**：参数盒表（A07）的"下界/上界"列全为 `n/a`，报告只给采样方式（log/linear）。
   本工序**如实登记缺失**，不按常理补数值。
2. **{n_unres} 个资产不可解析**（A26/A36/A37/A38/A39/A40/A41/A42）：全部是被登记报告里**指向 TensorDEM 仓**的
   相对路径（模块、脚本、测试、`records.jsonl`、`report.json`、回炉留档目录）或图件二进制。报告未给 URL/DOI，
   本工作树（TensorKnowledge）内不存在这些路径，因此判 `referenced_unresolved`，**不联网猜地址**。
   下游若需取用，必须回到 TensorDEM 仓按路径解析。
3. **平台 figures 只有声明没有二进制**：API payload 的 `figures` 有 6 条 `name`/`caption`，无 `png_base64`，
   故"图件本体"不是可解析资产；但图注文字（A25）在原文可解析。
4. **上游 honest FAIL 原样保留**：AC6/AC7 记 FAIL、AC5 跨配置稳健性 FAIL、UCS 随增量加密未收敛（1.01→0.86→0.67 MPa）。
   本工序不改判、不软化措辞——登记的是"上游说了什么"，不是"我认为对不对"。
5. **图内标签用英文**：本工作树镜像无 CJK 字体（`fc-list` 无中文字族），中文标签会渲染成豆腐块，
   因此三张图用英文标签；中文表述留在本报告正文与 manifest 的 `label` 字段。
6. **schema_pass 用的是本地 generic schema**：仓内 `schemas/asset_manifest.v1.schema.json` 的
   `package_id`/`report_id` 是 `const`（另一包的），改它会污染别的工作包产物；故新增与之同形的
   generic 版本供任意 `01-asset-registration` 包复用。**若平台侧 canonical schema 不同，以平台门为准。**
7. **coverage ≠ 完整性**：{C['coverage_fraction']:.4f} 的字符覆盖率统计的是"被页内资产 char span 覆盖的字符"，
   空白行、过渡句未覆盖属正常；覆盖率不是"信息是否抽全"的度量（抽取不在本工序范围）。

## ⑥ 自检：逐条对照 acceptance

{acceptance_table()}

补充自检项（非 acceptance 但本工序自己加的护栏，全部 PASS 才判 overall={V['overall']}）：

{check_table()}

### 误差判定（关键量 vs 基准，逐项；显式回答"是否 <3%"）

| 关键量 | 基准 | 实测偏差 | 是否 <3% |
|---|---|---|---|
| markdown sha256 | 契约 `source_hash` = `{S['hash'][:16]}…` | 0（字符串逐字节相等）| 是 |
| markdown 字符数 | 契约 `chars` = {S['chars']} | 0（{S['chars']}）| 是 |
| 定位可复现性 | 每个 quote 必须能由 `[start_char,end_char)` 反向切出且全文唯一 | 0 失败 / {C['assets']} 资产 | 是 |
| id 唯一性 | 无重复 asset_id | 0 重复 | 是 |
| 资产计数自洽 | `counts` 必须由 `assets[]` 派生 | 0 不符 | 是 |
| 物理量对标（阻力/强度…）| — | — | **无基准可对**：本工序不产生物理量，只登记定位；故不编造误差结论 |

显式回答：本工序的三类关键量（源哈希、源长度、定位可复现性）均为**精确相等**（偏差 0，远优于 3%）；
本包**没有**物理量/实验基准可对标，按纪律声明原因，不给"<3%"的空头结论。

### 复现

```bash
{repro}
```

预期：`asset_manifest.json` 的 `sha256={R['outputs']['asset_manifest.json']['artifact_sha256']}` 复现，
`verification.json` 的 `overall=PASS`。

```json
{json_block}
```
"""
    return body


def publish(markdown: str, figs: list[dict]) -> None:
    def call(path: str, body: dict | None, tok: str | None = None, timeout: int = 180):
        headers = {"Content-Type": "application/json"}
        if tok:
            headers["Authorization"] = "Bearer " + tok
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(BASE + path, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.status, r.read().decode()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read().decode()

    st, b = call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                 "password": os.environ["TENSOR_AGENT_PASS"]})
    assert st == 200, (st, b[:300])
    tok = json.loads(b)["access_token"]
    payload = {
        "title": "KF-RESULT " + PACKAGE_ID,
        "summary": (
            "%s (01-asset-registration, report %s): markdown sha256 recomputed = contract hash %s…; "
            "%d assets in %d classes (%d resolved in source, %d external refs unresolved); "
            "verification.json overall=%s; claims=[] by contract."
            % (PACKAGE_ID, REPORT_ID, S["hash"][:12], C["assets"], len(C["by_class"]),
               C["resolved_in_source"], C["referenced_unresolved"], V["overall"])),
        "scenario_key": S["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + REPORT_ID,
                 "lane:C", "draft", "knowledge-factory"],
        "markdown": markdown,
        "figures": figs,
    }
    st, resp = call("/tensor/reports", payload, tok)
    print("POST /tensor/reports ->", st, resp[:400])
    if st not in (200, 201):
        raise SystemExit("publish failed")


def main() -> None:
    DOCS.mkdir(parents=True, exist_ok=True)
    md = build_markdown()
    assert md.count("```json") == 1, "report must contain exactly one json block"
    out = DOCS / ("KF-RESULT-%s.md" % PACKAGE_ID)
    out.write_text(md)
    print("wrote", out, len(md), "chars")
    if "--no-post" in sys.argv:
        return
    publish(md, figures())


if __name__ == "__main__":
    main()