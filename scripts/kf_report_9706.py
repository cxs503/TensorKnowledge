"""Build and publish the KF-RESULT report for work package wp-9706-01.

Numbers are injected programmatically from the machine artifacts (no hand transcription):
  artifacts/wp-9706-01/asset_manifest.json  -> asset counts, locator table
  runs/wp-9706-01/acceptance.json           -> acceptance item statuses
  runs/wp-9706-01/coverage.json             -> locator coverage metrics
  runs/wp-9706-01/kf_result.<pkg>.json      -> the single ```json block (result envelope)

Outputs:
  docs/wp-9706-01/KF-RESULT-wp-9706-01.md   (report body, reproducible offline)
  platform report POSTed with title "KF-RESULT wp-9706-01" and tag kf-wp:wp-9706-01

Usage:
  python3 scripts/kf_report_9706.py            # build markdown only
  python3 scripts/kf_report_9706.py --publish  # build + POST to the platform
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import re
import sys
import urllib.request

PKG = "wp-9706-01"
REPORT_ID = "9706"
MISSION_ID = 15665
ROOT = pathlib.Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / PKG
ART_DIR = ROOT / "artifacts" / PKG
DOC_DIR = ROOT / "docs" / PKG
OUT_MD = DOC_DIR / f"KF-RESULT-{PKG}.md"
FIG = DOC_DIR / "fig_asset_coverage.png"


def cell(s: str, limit: int = 46) -> str:
    """Make a quote safe inside a markdown table cell.

    Display-only transformation (the verbatim quote stays authoritative in the manifest):
    pipes escaped, newlines -> " ⏎ ", backtick runs -> "[tick]" (a bare ``` inside a table cell
    would both break the table and, if it landed in the json block, truncate a non-greedy
    ```json fence extractor), long cells truncated with "…".
    """
    s = re.sub(r"`+", "[tick]", s).replace("|", "\\|").replace("\n", " ⏎ ")
    return s if len(s) <= limit else s[:limit] + "…"


def test_counts() -> dict:
    """Count the tests that actually exist (no hand-written test counts in the report)."""
    src = (ROOT / "tests" / "test_kf_wp_9706_01.py").read_text(encoding="utf-8")
    names = re.findall(r"^def (test_\w+)", src, re.M)
    return dict(total=len(names),
                mutation=sum(1 for n in names if n.startswith("test_mutation_")),
                positive=sum(1 for n in names if not n.startswith("test_mutation_")))


def summary_text(man: dict, acc: dict) -> str:
    """One-line package summary, generated from the artifacts (used in the body AND as platform summary)."""
    c = man["counts"]
    return ("报告 9706（DP 系统能力评估，PSV-6450）资产登记工序：%d 个资产（%d 源内唯一解析 / %d 跨仓或"
            "缺行不可解析 / %d 声明缺席）；claims=[] 按契约不抽取；%d 项验收自检 all_pass=%s。"
            % (c["assets"], c["resolved_in_source"], c["referenced_unresolved"], c["declared_absent"],
               len(acc["checks"]), acc["all_pass"]))


def build_markdown() -> str:
    man = json.loads((ART_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
    env = json.loads((RUN_DIR / f"kf_result.{PKG}.json").read_text(encoding="utf-8"))
    acc = json.loads((RUN_DIR / "acceptance.json").read_text(encoding="utf-8"))
    cov = json.loads((RUN_DIR / "coverage.json").read_text(encoding="utf-8"))
    c = man["counts"]
    tc = test_counts()
    tc_tables = c["by_class"].get("table", 0)
    src = man["source"]

    loc_rows = []
    for a in man["assets"]:
        loc = a["locator"]
        loc_rows.append("| %s | %s | %s | %s | %d–%d (行 %d–%d) | %s | `%s` |" % (
            a["asset_id"], a["asset_class"], a["resolution"], a["resolution_check"]["result"],
            loc["start_char"], loc["end_char"], loc["start_line"], loc["end_line"],
            a["in_report_section"][:34].replace("|", "\\|"), cell(loc["quote"])))
    loc_table = "\n".join(loc_rows)

    acc_rows = []
    for ch in acc["checks"]:
        detail = json.dumps(ch["detail"], ensure_ascii=False)
        acc_rows.append("| `%s` | %s | %s |" % (
            ch["item"], "✅ pass" if ch["status"] == "pass" else "❌ fail",
            cell(detail, 120).replace("\\|", "|")))
    acc_table = "\n".join(acc_rows)

    unresolved = [a for a in man["assets"] if a["resolution"] != "resolved_in_source"]

    # Escaping rule (necessary, not cosmetic): the platform gate extracts the result with the
    # non-greedy pattern re.compile(r"```json\s*\n(.*?)```", re.S) -- see
    # ops/knowledge_factory/gates.py::extract_payload. Verbatim quotes of the two fenced blocks
    # (A09 flow diagram, A28 repro commands) contain "```", which would terminate that block early
    # and make the payload undecodable. Backticks therefore travel as the JSON escape \u0060:
    # the decoded object is byte-for-byte identical, while the block no longer contains "```".
    json_block = json.dumps(env, ensure_ascii=False, indent=2).replace("`", "\\u0060")
    assert "```" not in json_block

    md = f"""# KF-RESULT {PKG}

知识产线工序 **01-asset-registration（资产登记）**，只服务 `report_id=9706` 这一份报告；上游/其它工作包产物一律未读未写。

- 源：`{src['uri']}` 字段 `{src['field']}`，{src['chars']} 字符 / {src['bytes_utf8']} 字节 UTF-8，`sha256:{src['hash']}`
- 平台标题：{src['title']}
- scenario_key：`{src['scenario_key']}`（合同一致：`{src['contract_scenario_key']}`）｜源报告平台 mission_id：`{src['platform_mission_id']}`（≠ 本工作包 mission {MISSION_ID}）
- 工件摘要（= 平台 summary）：{summary_text(man, acc)}
- 合同标题 `{src['contract_title']}` 与正文标题行**不完全相同**（合同是摘要式命名）；本工序以 markdown 字节哈希为唯一身份，差异如实登记在资产 A02 的 `resolution_check.identical=false`。

---

## ① 本工序做了什么

把报告 9706 的**源资产登记**做成一页可机器校验的清单（`asset_manifest.json`），共 **{c['assets']}** 个资产：

- **resolved_in_source {c['resolved_in_source']} 个**——在 markdown 内能唯一解析到字符区间（{tc_tables} 个表格块、7 段方法/陷阱/局限文本、4 个图件引用行、2 个 JSON 工件行、代码围栏流程图与复现命令块、章节标题与溯源头等）；
- **referenced_unresolved {c['referenced_unresolved']} 个**——报告提到但本工作树**不可解析**：`acceptance.json`（§7 提及、表 10 无该行、无字节数与哈希）与两个跨仓代码指针 `backend/physics/dp_capability/`、`physics.wave_spectrum_core`（属上游仓 ship-performance-platform，本仓无此路径）。**没有编造任何地址**；
- **declared_absent {c['declared_absent']} 个**——报告用否定句显式声明未纳入的能力（DP 控制器动力学 / 波浪中瞬时推力波动 / 锚泊拖轮辅助 / 冰区冰载荷），按缺席登记、不推断其数值。

**不做的事**：不做 claim 抽取（合同 `objective.classify_report_type=false`，`claims` 允许空数组 → 本包 `claims=[]` 并写明理由）；不把任何条目标成 verified；不复制、不改写原文结论。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取证（不凭记忆）**：`GET /api/v1/tensor/reports/9706` → `markdown` 落盘 `runs/{PKG}/report_9706.md`；本地重算 `sha256` = `{src['hash']}`，与合同 `source_hash` 逐字节一致、字符数 {src['chars']} 与合同 `chars` 一致，才继续（不一致脚本 `FATAL` 退出）。
2. **定位而非抄写**：`scripts/kf_register_9706.py` 维护锚点表（资产 id / 唯一锚点串 / 块规则：`table` `until_blank` `until_marker` `fence` `line` `doc`）。运行时用锚点在 markdown 中定位行号 → 由行偏移算 `[start_char,end_char)` → **直接从原文切片**得到 `quote`；每个 quote 再断言「在全文出现次数 == 1」，不唯一即中止。**全文没有一个人工键入的引文字符串**。
3. **可解析性判定（不猜）**：每个资产跑一次机器检查，并与声明状态强绑定（`resolved_in_source`↔resolved/present、`referenced_unresolved`↔unresolved、`declared_absent`↔absent）：
   - 页内资产 → `char_span_roundtrip_and_uniqueness`；
   - 工件行 → `artifact_row_size_and_hash_prefix_present`：正则取出字节数与 16 位哈希前缀，并显式记 `full_sha256_available=false`；
   - `acceptance.json` → `table10_artifact_row_lookup`：实测表 10 无该行 → unresolved；
   - 跨仓指针 → `worktree_path_exists`：在本工作树实测路径是否存在 → 均不存在 → unresolved；
   - 缺席能力 → `absent_capability_markers_in_quote`：要求引文中确实出现"不含/未接入"。
4. **独立校验（gate）**：`scripts/kf_verify_9706.py` 在**新进程**里重跑全部验收项，含 `--from-api` 模式重新登录拉取 markdown 并**与本地副本逐字节比对**（`api_refetch_identical_to_local`），JSON 严格解析（拒绝 NaN/Infinity 与重复键），JSON Schema 双校验（信封 `schemas/kf_result.v1.schema.json`、清单 `schemas/asset_manifest.{PKG}.schema.json`）。
5. **反向对照（证明检查会红）**：`tests/test_kf_wp_9706_01.py` {tc["total"]} 项，其中 {tc["mutation"]} 个变异探针：篡改 quote、平移 char span、重复 asset_id、错哈希、无证据却标 verified 的 claim、resolved 谎报为 unresolved —— 每个变异都必须被同一套判定捕获。
6. **出图**：`scripts/kf_figures_9706.py` 从 manifest 直接算定位覆盖与类别分布（不含整篇条目 A01，否则覆盖率恒为 100%，是自证循环）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/{PKG}/asset_manifest.json` | 主产物：{c['assets']} 个资产，{c['resolved_in_source']} resolved_in_source / {c['referenced_unresolved']} referenced_unresolved / {c['declared_absent']} declared_absent |
| `schemas/asset_manifest.{PKG}.schema.json` | 本地 pin 的 manifest 形状约束（含 const 化的 package_id/report_id），使 `schema_pass` 可复现 |
| `runs/{PKG}/report_9706.md` / `.json` | 源证据快照（markdown 与 API 原始响应） |
| `runs/{PKG}/kf_result.{PKG}.json` | 结果信封（package_id/task_type/report_id/provenance/outputs） |
| `runs/{PKG}/acceptance.json` | {len(acc['checks'])} 项验收自检逐项结果，all_pass={acc['all_pass']} |
| `runs/{PKG}/coverage.json` | 定位覆盖度量（本章表 1 数字的唯一来源） |
| `docs/{PKG}/fig_asset_coverage.png` | 图 1 定位地图（左：资产在源字符轴上的位置；右：类别×可解析状态） |
| `scripts/kf_fetch_9706.py` `kf_register_9706.py` `kf_verify_9706.py` `kf_figures_9706.py` `kf_report_9706.py` | 取证 / 登记 / 校验 / 出图 / 报报告 |
| `tests/test_kf_wp_9706_01.py` | {tc["total"]} 项测试（含 {tc["mutation"]} 个变异探针：证明检查会红） |

## ④ 证据定位表（claim/字段 → 原文引文片段，全部为运行时切片）

字符区间为 0 基（Python str 索引），行号为 1 基闭区间。`result` 是该资产的机器检查结果。

| 资产 | 类别 | resolution | check | char span (行) | 所在章节 | 原文引文（截断，逐字切片） |
|---|---|---|---|---|---|---|
{loc_table}

完整引文（不截断）见 `artifacts/{PKG}/asset_manifest.json` 各资产的 `locator.quote`；每个都被断言为原文唯一子串。

## ⑤ 注意点与局限

1. **`resolved_in_source` 不等于"文件已验证"**。4 个图件与 2 个 JSON 工件只在表 10 里留下**字节数 + sha256 前 16 位**；PNG/JSON 本体不在源内，本工序**无法**校验文件字节，只能登记前缀（`full_sha256_available=false` 已逐条写明）。任何下游若把 `resolved_in_source` 读成"工件已核验"，就是误用。
2. **合同标题与正文标题行不同**：合同是摘要式命名，正文是完整标题。身份判定只认 markdown 哈希；本工序未改写任何一侧。
3. **报告内部口径差异不调和**：表 5 最差扇区 59.41 kn（24 航向），表 8 baseline 61.88 kn（航向取样不同）。登记只记录位置，**不做数值仲裁**——仲裁属下游证据审计工序。
4. **跨仓指针不可解析**：`backend/physics/dp_capability/`、`physics.wave_spectrum_core`、`scripts/gen_dp_capability_*.py` 均属上游仓 ship-performance-platform；本工作树（TensorKnowledge）内不存在，按 `referenced_unresolved` 登记，未猜路径。
5. **固定点 × 覆盖率**：按章节级定位器并集，源 markdown 覆盖率 **{cov['coverage_fraction']:.1%}**（{cov['chars_covered_by_section_level_locators']}/{cov['source_chars']} 字符，{cov['uncovered_regions']} 段未覆盖，最大未覆盖段 {cov['largest_uncovered_gap'][0]} 字符 @{cov['largest_uncovered_gap'][1]}–{cov['largest_uncovered_gap'][2]}）。登记是**选择性**的：未覆盖段是各表间的过渡说明文字，不属资产。该度量**无外部基准**，只作过程透明度指标，不当作质量判据。
6. **`claims=[]` 不是遗漏**：合同明确 `objective.classify_report_type=false` 且 notes 允许空数组；为凑指标造 claim 才是违规。
7. **发布足迹与元数据一致性**：同一段正文最初以 report id `14778` 发布，其 `summary` 记为初稿口径（"11 项验收"）。
   平台无原地更新通道（`PUT/PATCH /tensor/reports/{id}` 均 405），且 `(mission_id, md5(markdown))` 唯一约束拒绝重复发布同正文，
   因此定稿把 summary 计数写入正文第一屏（见头部「工件摘要」）再发布——正文与元数据同源可查，旧条 `14778` 保留为过程痕迹。
8. **本包未做任何数值复核**：表 3–表 9 的数字只登记位置。报告中自报的"<3%"结论在本工序**未复算**，`verification_status=not_verified`（验证由平台门计算）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 证据 |
|---|---|---|
{acc_table}

**关键量 vs 基准（显式回答是否 < 3%）**

| 关键量 | 基准 | 本次 | 相对偏差 | 是否 < 3% |
|---|---|---|---|---|
| markdown sha256 | 合同 `source_hash` | 逐字节相同 | 0 | **是** |
| markdown 字符数 | 合同 `chars` = 12546 | {src['chars']} | 0 | **是** |
| 定位可解析率 | 合同要求可解析（100%） | {c['resolved_in_source']}/{c['assets']} 章节/工件级引文全部唯一命中 | 0 | **是**（外部指针按 unresolved 显式登记，不计入分母） |
| id 唯一性 | 无重复 | {c['assets']} 个 id 全唯一 | 0 | **是** |
| claims 证据策略 | 每条 claim 有证据或显式状态 | claims=0（契约允许） | 不适用 | **不适用**（无 claim，声明原因：只登记不抽取） |
| 章节级定位覆盖率 | 无外部基准 | {cov['coverage_fraction']:.2%} | — | **不适用**（无基准，声明） |

**一键复跑（repro_cmd）**

```bash
bash scripts/kf_run_9706.sh              # 取数 → 登记 → 出图 → 报告(1st) → 验收门 → 报告(2nd) → pytest
bash scripts/kf_run_9706.sh --publish    # 同上并发布 KF-RESULT 到平台
```

报告与验收表互为输入（验收门要检查"已提交报告能否被门正则取出并解码"，报告又要内嵌验收表），
因此脚本对报告跑两遍，第二遍即定稿；这是定式，不是重试。

环境：Python 3 + `jsonschema` + `matplotlib`；凭据经 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS`/`TENSOR_API_BASE` 注入，脚本内不含任何凭据。

**图件说明**：本工序是登记工序，无物理场量。图 1 给出资产定位地图（唯一的可视化对象就是"资产 ↔ 源文本位置"映射本身）。

### 图 1 资产定位地图与会话口径

![fig_asset_coverage](fig_asset_coverage.png)

- 左：横轴 = 源 markdown 字符偏移（0–{cov['source_chars']}），每行一个资产（A01–A{c['assets']:02d}），颜色 = resolution 状态，竖虚线 = `## ` 章节边界（S1–S{cov['sections_with_boundaries']}）。
- 右：资产类别 × 可解析状态（表 {sum(1 for a in man['assets'] if a['asset_class']=='table')} 张表是最大类别）。

---

## 结果信封（唯一 json 代码块）

```json
{json_block}
```
"""
    return md


def publish(md: str, dry: bool = False) -> dict:
    man = json.loads((ART_DIR / "asset_manifest.json").read_text(encoding="utf-8"))
    acc = json.loads((RUN_DIR / "acceptance.json").read_text(encoding="utf-8"))
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    tok = None
    if user and pwd:
        for path in ("/auth/login", "/auth/token", "/login"):
            req = urllib.request.Request(base + path,
                                         data=json.dumps({"username": user, "password": pwd}).encode(),
                                         headers={"Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.loads(r.read().decode())
                tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
                if tok:
                    break
            except Exception:
                continue
    png = FIG.read_bytes()
    fig_b64 = base64.b64encode(png).decode()
    payload = dict(
        title=f"KF-RESULT {PKG}",
        summary=summary_text(man, acc),
        scenario_key="dp_capability",
        mission_id=MISSION_ID,
        tags=["kf-wp:" + PKG, "KF-RESULT", "asset-registration", "DP", "dp_capability",
              "report-9706", "lane-B", "TensorKnowledge"],
        markdown=md,
        figures=[dict(name="fig_asset_coverage",
                      caption=("图 1 资产定位地图：左=40 个资产在源 markdown 字符轴上的定位区间（颜色=可解析状态，"
                               "竖虚线=章节边界）；右=资产类别×可解析状态分布"),
                      png_base64=fig_b64)],
    )
    if dry:
        return dict(dry_run=True, title=payload["title"], markdown_chars=len(md),
                    figure_bytes=len(png))
    req = urllib.request.Request(base + "/tensor/reports",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="POST the report to the platform")
    args = ap.parse_args()
    md = build_markdown()
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")
    blocks = re.findall(r"```json\s*\n(.*?)```", md, re.S)
    if len(blocks) != 1:
        print("FATAL: expected exactly one ```json block, got", len(blocks))
        return 2
    try:
        decoded = json.loads(blocks[0])
    except json.JSONDecodeError as exc:
        print("FATAL: gate-style extraction does not decode:", exc)
        return 2
    env = json.loads((RUN_DIR / f"kf_result.{PKG}.json").read_text(encoding="utf-8"))
    if decoded != env:
        print("FATAL: decoded payload != envelope file")
        return 2
    print("gate-style extract ok: 1 block, decodes, equals envelope")

    n_json_blocks = md.count("```json")
    print("report:", OUT_MD, len(md), "chars | json_blocks =", n_json_blocks,
          "| fences =", md.count("```"))
    if n_json_blocks != 1:
        print("FATAL: report must contain exactly one ```json block")
        return 2
    res = publish(md, dry=not args.publish)
    print("publish:", json.dumps(res, ensure_ascii=False)[:400])
    if args.publish:
        (RUN_DIR / "publish_response.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())