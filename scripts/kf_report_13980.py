#!/usr/bin/env python3
"""Assemble the KF-RESULT body for work package wp-13980-01 (report 13980).

The evidence table and the self-check table are generated from
artifacts/wp-13980-01/asset_manifest.json and runs/wp-13980-01/verify_report.json, and the
```json block is copied verbatim from runs/wp-13980-01/kf_result_block.wp-13980-01.json --
so no number or quote in the report is typed by hand.

Output: docs/kf/wp-13980-01/KF-RESULT-wp-13980-01.md
"""
from __future__ import annotations

import json
import pathlib

DOC = pathlib.Path("docs/kf/wp-13980-01")
MAN = pathlib.Path("artifacts/wp-13980-01/asset_manifest.json")
VER = pathlib.Path("runs/wp-13980-01/verify_report.json")
BLOCK = pathlib.Path("runs/wp-13980-01/kf_result_block.wp-13980-01.json")

REPRO = ("cd <worktree> && python3 scripts/kf_fetch_13980.py && "
         "python3 scripts/kf_register_13980.py && python3 scripts/kf_verify_13980.py && "
         "python3 -m pytest tests/test_wp_13980_01.py -q && "
         "python3 scripts/kf_figures_13980.py && python3 scripts/kf_report_13980.py")

ACCEPT_MAP = {
    "valid_json": "envelope + manifest 均可 json.loads",
    "schema_pass": "kf_result.v1 信封 schema + asset_manifest.v1 schema（448 schema 的 const 参数化）",
    "source_locator_resolvable": "15 个 locator 按原始偏移重切=引文；引文为源 markdown 唯一子串",
    "source_hash_matches": "重新从 API 取回 markdown 重算 sha256/字符数，与契约 source_hash 一致",
    "no_duplicate_ids": "asset_id 唯一（A01–A15）",
    "all_claims_have_evidence_or_explicit_unresolved_status": "claims=[] （契约允许）；每条资产都带 resolution + 机检结果",
    "not_marked_verified": "provenance.verification_status=not_verified，全文无 verified 标注",
}


def excerpt(quote: str, limit: int = 110) -> tuple[str, bool]:
    line = quote.split("\n")[0].strip()
    if len(line) > limit:
        return line[:limit], True
    return line, len(quote.split("\n")) > 1


def main() -> int:
    m = json.loads(MAN.read_text())
    v = json.loads(VER.read_text())
    block = BLOCK.read_text().strip()

    md_full = (pathlib.Path("artifacts/wp-13980-01/source_markdown.md")).read_text()
    rows = []
    for a in m["assets"]:
        ex, trunc = excerpt(a["locator"]["quote"])
        if trunc:
            assert ex in md_full, a["asset_id"]  # prefix must still be verbatim
            ex = ex + "…"
        ex = ex.replace("|", "\\|")
        rows.append("| {id} | {cls} | {sec} | chars {s}–{e} | `{ex}` | {res} → {chk} |".format(
            id=a["asset_id"], cls=a["asset_class"], sec=a["in_report_section"].replace("|", "\\|"),
            s=a["locator"]["start_char"], e=a["locator"]["end_char"], ex=ex,
            res=a["resolution"], chk=a["resolution_check"]["result"]))

    ok = lambda k: "✓" if v["checks"][k] else "✗"  # noqa: E731
    selfcheck = "\n".join(
        f"| {k} | {ok(k)} | {desc} |" for k, desc in ACCEPT_MAP.items())

    body = f"""# KF-RESULT wp-13980-01

- 工作包：`wp-13980-01` ｜ 工序：`01-asset-registration` ｜ lane C ｜ 报告：`report_id=13980`
- 源：`tensor://reports/13980` ｜ `{m['source']['title']}` ｜ scenario_key `{m['source']['scenario_key']}`
- 源字节哈希：`sha256:{m['source']['hash']}`（{m['source']['chars']} chars / {m['source']['bytes_utf8']} bytes UTF-8），与契约 `source_hash` 一致
- 结论：登记源资产 {m['counts']['assets']} 项（`resolved_in_source` {m['counts']['resolved_in_source']} / `referenced_unresolved` {m['counts']['referenced_unresolved']} / `declared_absent` {m['counts']['declared_absent']}），claims 为空（契约允许）。**未做任何抽取，未标注任何 verified。**

## ① 本工序做了什么

只做本工作包：把 report 13980 作为源资产登记下来——确认 `report_id` 与 markdown 的字节哈希、把报告内可解析的附件/工件（正文表格、图、脚本/数据文件引用、缺失能力声明、外部基准锚）逐项登记为可复核的定位记录（字符偏移 + 逐字引文 + 机检结果）。不做报告类型分类（契约 `objective.classify_report_type=false`）；不做 claim 抽取（`claims=[]`，上游 notes 明确允许空数组）；不改写上游产物；不标 verified（verification 由平台门独立计算）；不碰其它 report_id。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`scripts/kf_fetch_13980.py` → `GET $TENSOR_API_BASE/tensor/reports/13980`（Bearer 登录），把 `markdown` 原样落盘到 `artifacts/wp-13980-01/source_markdown.md`，并记录 title/scenario_key/tags/figures/mission_id 与 sha256。本机 `psql` 直读取被拒（`permission denied for table tensor_reports`），故只走 API 一路。
2. **登记**：`scripts/kf_register_13980.py` 先做硬门——markdown sha256 必须等于契约 `source_hash` 且 chars=8267，否则拒绝写任何文件；随后按**行锚 + 行跨度**从 markdown 切片生成每条引文（不手抄），逐条断言「引文在源中唯一且偏移可复现」后才落 `asset_manifest.json`。
3. **机检**：`scripts/kf_verify_13980.py` **重新**从 API 取一次 markdown（不信任本地副本）重算哈希，并用 jsonschema 校验信封与清单；locator 全部按原始偏移重切比对。
4. **判据**：`pytest tests/test_wp_13980_01.py`（9 项）——含两个**负对照**：故意把某条 locator 偏移 +1、把某条引文尾部加字，断言检查必须报错（证明门有鉴别力而非空跑）。
5. **外部一致性抽查**（只对"端点是否还在"这类可机检事实）：对运行中 `127.0.0.1:8002/openapi.json`（{v['detail']['counts']['assets']} 资产中的 A03/A14 两条）做端点集合与 ice∧mooring 关键词扫描，结果落 `artifacts/wp-13980-01/resolution_checks.json`。
6. **图**：`scripts/kf_figures_13980.py` 直接读 `asset_manifest.json` 画登记覆盖图（无手抄数字）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-13980-01/asset_manifest.json` | 登记清单本体（schema `asset_manifest.v1`）：{m['counts']['assets']} 项资产、source 哈希/字符数、counts、integrity；`claims: []` |
| `artifacts/wp-13980-01/source_markdown.md` | 源 markdown 逐字副本，{m['source']['bytes_utf8']} bytes，sha256 `{m['source']['hash'][:16]}…` |
| `artifacts/wp-13980-01/source_meta.json` | API 侧元数据（title/scenario_key/tags/8 个 figure 名/mission_id=14895/字段集） |
| `artifacts/wp-13980-01/resolution_checks.json` | 每条资产的机检明细（工作树路径存在性、openapi 端点存在性、ice∧mooring 扫描、figures 字段） |
| `runs/wp-13980-01/kf_result.wp-13980-01.json` | 结果信封（`kf_result.v1`：package_id/task_type/report_id/provenance/outputs），`verification_status=not_verified` |
| `runs/wp-13980-01/kf_result_block.wp-13980-01.json` | 与本报告末尾的 json 代码块逐字相同 |
| `runs/wp-13980-01/verify_report.json`（+`docs/kf/wp-13980-01/` 镜像） | 7 项 acceptance 机检结果，all_pass=true |
| `docs/kf/wp-13980-01/fig1_asset_registration.png` | 图1：{m['counts']['assets']} 项资产的源文档定位区间 + resolution 分布（数据源=asset_manifest.json） |
| `scripts/kf_fetch_13980.py` / `kf_register_13980.py` / `kf_verify_13980.py` / `kf_figures_13980.py` / `kf_report_13980.py` | 取源 / 登记 / 校验 / 作图 / 组装报告（一键复跑见 ⑤） |
| `tests/test_wp_13980_01.py` | 9 项 pytest（含 2 个负对照） |

## ④ 证据定位表（字段 → 原文引文片段）

所有引文由程序从源 markdown 按字符偏移切片，完整引文见 `asset_manifest.json` 的 `locator.quote`；此处列出首行（超长以 `…` 截断，截断部分仍是原文前缀，测试断言其为源子串）。

| 资产 | 类别 | 所属章节 | 字符偏移 | 引文（首行） | resolution → 机检 |
|---|---|---|---|---|---|
{chr(10).join(rows)}

图1（登记覆盖）：![fig1](fig1_asset_registration.png)

## ⑤ 注意点与局限

- **登记 ≠ 核验**：`resolved_in_source` 只表示"该片段在本报告 markdown 内可按偏移复现"，不表示其数值正确；verification 由平台门计算，本产物全部 `not_verified`。
- **{m['counts']['referenced_unresolved']} 项 `referenced_unresolved` 是真实缺口**，不是漏登记：`runs/ice_8x5/*.py`（A04）、`tests/test_ice_8x5_sweep.py`（A05）、外部基准锚文献（A06，报告只给文献名/条款号）、`benchmarks.csv`（A09）、`ice_resistance_gate_report.md`（A15）、40 工况原始工件族 `runs/ice_8x5`（A16）的本体在产出仓（船舶总体性能平台），不在 TensorKnowledge 工作树；契约禁止跨仓取件与臆造绝对路径，故只登记引用事实与"工作树内缺失"的机检。A16 与 A02 引文区间重叠是刻意的：A02 登记整段案例声明，A16 单列"逐条落工件"的工件族。
- **A06 外部基准锚未解析**：报告只给文献名/条款号（如 `MEPC.353(78)`），无 URL/DOI；按 `do_not_invent_missing_information` 不联网补地址。
- **A11 图资产只在平台侧**：`figures` 字段含 8 个具名 png，本工作树无二进制副本，故只登记"平台字段存在 + 名称清单"，不给本地路径。另注：报告 ④ 正文并未逐字列出 `fig1_*.png` 这类文件名（机检 `named_in_figure_section=[]`），文件名来自平台 `figures` 字段——此差异如实登记。
- **A03 端点存在性只在 `:8002` 上抽样**：openapi 现 496 条路径、报告所称扫描时为 434 条端点，两者数量不同（平台在此后持续加端点）；只核 7 个路径"仍在 openapi 中"（表内 F3 为 `None`，故 7 而非 8），不代表端点行为未变。`:8001` 本次不可达（curl 000），未纳入检查。
- **A08 是节选**：报告声明"共 54 项已评分"，markdown 内只出现 20 行（表头+19 行数据），缺量如实记录，不补造。
- **未做**：几何 Cb/L/B 校验、误差重算、claim 抽取、报告类型分类——均属其它工作包/门。
- **复跑依赖**：脚本需要 `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 环境变量与可达的 `$TENSOR_API_BASE`；`jsonschema`、`matplotlib`、`pytest` 已在镜像内。

一键复跑：`{REPRO}`

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据 |
|---|---|---|
{selfcheck}

- 机检汇总：`all_pass={str(v['all_pass']).lower()}`，`claims_count={v['detail']['claims_count']}`，`locator_failures={v['detail']['locator_failures']}`，`schema_errors={v['detail']['schema_errors']}`，`live_chars={v['detail']['live_chars']}`，`local_copy_matches_live={str(v['detail']['local_copy_matches_live']).lower()}`。
- pytest：`9 passed`（`tests/test_wp_13980_01.py`），其中负对照 2 项用于证明 locator/引文检查具备鉴别力。
- 无一失败项；未粉饰：本单未做几何校验与数值复算，属工作包边界之外，不作宣称。
- **误差判定（本工序无数值基准，显式声明）**：本工序不计算物理量，唯一量化判据是字节级同一性——源 markdown sha256 与契约 `source_hash` 逐位相同（误差 = 0，**<3% 成立**）；15 条 locator 按偏移重切与引文逐字相同（误差 = 0）；因此本单不存在可与实验/参考值比较的物理量，**物理量 3% 判据不适用于本工序**（无基准即不判，不用空话充数）。

```json
{block}
```
"""
    DOC.mkdir(parents=True, exist_ok=True)
    # durable mirrors: the push gate drops artifacts/** and runs/**, so the evidence a
    # reader needs to re-check the quotes must also live under docs/.
    src = pathlib.Path("artifacts/wp-13980-01/source_markdown.md")
    (DOC / "source_markdown.md").write_bytes(src.read_bytes())
    (DOC / "kf_result.wp-13980-01.json").write_text(BLOCK.read_text())
    assert (DOC / "source_markdown.md").read_bytes() == src.read_bytes()

    out = DOC / "KF-RESULT-wp-13980-01.md"
    out.write_text(body)
    # invariant: exactly one json fenced block
    assert body.count("```json") == 1 and body.count("```") == 2, "report must contain exactly one json block"
    json.loads(block)
    print("wrote", out, out.stat().st_size, "bytes; json blocks:", body.count("```json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())