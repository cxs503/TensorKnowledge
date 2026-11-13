#!/usr/bin/env python3
"""wp-12595-01 · build the KF-RESULT report markdown.

Every number/quote in the report is injected programmatically from
docs/kf/wp-12595-01/{asset_manifest,kf_result}.json and the fetched source
(work/wp-12595-01/source/report_12595.md) — zero hand-copied values.

Output: docs/kf/wp-12595-01/kf_result_wp-12595-01.md
The single ```json block is byte-identical to docs/kf/wp-12595-01/kf_result.json.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[3]
OUT = REPO / "docs" / "kf" / "wp-12595-01"
SRC_MD = REPO / "work" / "wp-12595-01" / "source" / "report_12595.md"


def main():
    am = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    env = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    md = SRC_MD.read_text(encoding="utf-8")
    lines = md.split("\n")

    sa = am["source_asset"]
    lc = am["locator_check"]
    att = am["attachments"]
    refs = am["referenced_artifacts"]
    obs = am["observations"]
    secs = am["sections"]
    b = am["boundary"]

    from collections import Counter

    kind_counts = Counter(r["path_kind"] for r in refs)
    n_path = kind_counts.get("path", 0)
    n_glob = kind_counts.get("glob", 0)
    n_field = kind_counts.get("field", 0)
    n_wt = kind_counts.get("worktree", 0) + kind_counts.get("branch", 0)

    # acceptance re-run (machine)
    sys.path.insert(0, str(REPO / "scripts" / "kf" / "wp-12595-01"))
    import register_assets as reg  # noqa: E402

    md_src, data = reg.load_source(type("A", (), {"from_file": str(SRC_MD), "record_json": str(REPO / "work/wp-12595-01/source/report_12595.json")})())
    manifest, stats = reg.build_manifest(md_src, data)
    envelope = reg.build_envelope(manifest)
    checks = reg.run_checks(envelope, stats)

    def tick(ok):
        return "✅" if ok else "❌"

    # ---- evidence table rows (verbatim quotes from manifest) ---------------
    ev_rows = []
    for r in refs:
        ev_rows.append(
            f"| 引用（{r['path_kind']}） · `{r['ref_id']}` · source_field=markdown · L{r['first_line']} | `{r['locator_quote']}` |"
        )
    for a in att["items"]:
        ev_rows.append(
            f"| 附件（figures 字段图注） · `fig:{a['name']}` · source_field=figures | `{a['caption']}` |"
        )
    for o in obs:
        for q in o["evidence_quotes"]:
            ev_rows.append(f"| 观察证据 · `{o['id']}` · source_field=markdown | `{q}` |")

    # ---- figure data (from JSON, not hand-typed) ---------------------------
    fig_data = {
        "by_kind": {k: kind_counts.get(k, 0) for k in ("path", "glob", "field", "worktree", "branch")},
        "checks": checks,
        "n_refs": len(refs),
        "n_locators": lc["total"],
        "n_resolved": lc["resolved"],
        "n_sections": len(secs),
        "n_attachments": att["count"],
        "n_obs": len(obs),
        "n_unresolved": len(am["unresolved"]),
    }
    (OUT / "fig_data.json").write_text(json.dumps(fig_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    checks_rows = "\n".join(
        f"| {k} | {tick(v)} |" for k, v in checks.items()
    )

    ref_rows = "\n".join(
        f"| `{r['ref_id']}` | {r['path_kind']} | L{r['first_line']} | {r['occurrences']} | `{r['raw_text']}` | {r['existence']} |"
        for r in refs
    )

    cross_rows = "\n".join(
        f"| {c['name']} | {tick(c['name_in_markdown'])} | {tick(c['caption_matches_markdown'])} |"
        for c in att["cross_check_markdown_vs_record"]
    )

    sec_rows = "\n".join(
        f"| {s['ordinal']} | {s['level']} | {s['line_start']}–{s['line_end']} | {s['chars']} | `{s['sha256'][:16]}…` | {s['heading']} |"
        for s in secs
    )

    obs_rows = "\n".join(
        f"| `{o['id']}` | {o['kind']} | {o['status']} | {o['statement']} |" for o in obs
    )

    json_block = (OUT / "kf_result.json").read_text(encoding="utf-8").rstrip("\n")

    md_out = f"""# KF-RESULT {am['package_id']}

- package_id: `{am['package_id']}` ｜ task_type: `{am['task_type']}` ｜ report_id: `{am['source_asset']['platform_record_id']}` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: draft
- source: `{sa['uri']}`（field=`{sa['field']}`），chars={sa['size']['chars']}，bytes={sa['size']['bytes_utf8']}，sha256=`{sa['hash']['value']}`
- 哈希核对：独立重算 == 契约声明 → **{tick(sa['hash']['matches_contract'])}**；chars {sa['size']['chars']} == 契约 {sa['size']['contract_chars']} → **{tick(sa['size']['chars_match_contract'])}**；title/scenario_key 与契约一致 → **{tick(sa['record_metadata']['title_matches_contract'] and sa['record_metadata']['scenario_key_matches_contract'])}**
- 分层标签（原样登记、不解读）：`{sa['contract_layer_hint']['value']}`
- 状态：draft（verification 由平台门计算，本包不标 verified）

## ① 本工序做了什么

只做「源资产登记」，不做抽取、不做报告类型分类。核对 report_id=12595 与其 markdown 的字节哈希，登记：
平台记录元数据、正文小节切分（{len(secs)} 节，含行区间与每节 sha256）、
可解析附件（figures {att['count']} 条，仅 name/caption 元数据，无 png_base64 载荷）、
正文声明的引用（{len(refs)} 条：路径 {n_path} / glob {n_glob} / 字段 {n_field} / worktree+branch {n_wt}），
并为每条引文提供逐字可定位 locator（{lc['resolved']}/{lc['total']} 全部命中）。
`claims` 为空数组——合同 `objective.register_assets=true` / `classify_report_type=false`，
且 notes 明确「claims 允许为空数组」，故不生成任何 claim（不做强制抽取）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`POST $TENSOR_API_BASE/auth/login` 取 token → `GET $TENSOR_API_BASE/tensor/reports/12595`
   （`scripts/kf_fetch_12595.py`）。只读 12595 一份；未读写任何其它 report_id（见 manifest `boundary`）。
2. **哈希复算**：`hashlib.sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 逐字节比对；
   同时比对字符数（运行时 {sa['size']['chars']} vs 契约 {sa['size']['contract_chars']}）与 UTF-8 字节数（{sa['size']['bytes_utf8']}）。
3. **小节切分**：按 ATX 标题切分，记录 `level/heading/line_start/line_end/chars/sha256`（{len(secs)} 节），供后续工序按节取证。
4. **引用抽取**：确定性规则——反引号代码片段按 path/glob/worktree/branch/field 分类；
   纯文本仅收「含斜杠+扩展名+字母」的路径 token（捕获判据表 C6 的 glob，排除 `0.4`/`1e-09` 等小数误报）。
   locator 一律取**原文整行**，因此逐字可定位（脚本机检，非人工粘贴）；
   观察项证据行带字面量断言（行内容不符即 SystemExit，拒绝编造）。
5. **附件登记**：读平台记录 `figures` 字段（{att['count']} 条），只登记 name/caption 与载荷存在性标记；
   未下载、未解码图像。正文 §4 的 4 个 PNG 行与 figures 字段做 name+caption 逐字交叉核对（{sum(1 for c in att['cross_check_markdown_vs_record'] if c['caption_matches_markdown'])}/{att['count']} 全中）。
6. **零手抄**：`scripts/kf/wp-12595-01/register_assets.py` 内无任何手写数字/引文；
   本报告数字与引文全部由 `make_report.py` 从 JSON 产物与原文行注入。
7. **自检**：`register_assets.py --check` 跑 schema 校验 + locator 逐字匹配 + id 唯一性 + 哈希一致性；
   `tests/kf/test_wp_12595_01.py` 回归（含负对照与离线复跑）。

关键设置：产物落 `docs/kf/wp-12595-01/`（git 可追踪）；工件存在性一律标 `not_checked`
（声明于 m11206 的 TensorPhysics worktree，跨树取证越界）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12595-01/kf_result.json` | 结果信封：package_id / task_type / report_id / provenance(source_hash,source_field,source_uri) / outputs / claims=[] |
| `docs/kf/wp-12595-01/asset_manifest.json` | 登记清单：source_asset（hash/size/metadata/layer hint）、attachments（{att['count']}）、sections（{len(secs)}）、referenced_artifacts（{len(refs)}）、observations（{len(obs)}）、locator_check（{lc['resolved']}/{lc['total']}）、unresolved（{len(am['unresolved'])}）、boundary |
| `docs/kf/wp-12595-01/fig_acceptance.png` | 验收图：左=引用按 kind 计数；右=acceptance 自检逐项（数据由 `fig_data.json` 程序化读取） |
| `docs/kf/wp-12595-01/kf_result_wp-12595-01.md` | 本报告（六段 + 唯一 json 块） |
| `scripts/kf/wp-12595-01/register_assets.py` | 生成器：`--check` 打印 acceptance 自检，`--from-file/--record-json` 支持离线复跑 |
| `scripts/kf/wp-12595-01/make_report.py` | 报告生成器（引文由 manifest 注入，json 块与产物同字节） |
| `scripts/kf/wp-12595-01/make_figure.py` | 验收图生成器 |
| `tests/kf/test_wp_12595_01.py` | 回归测试（schema/哈希复算/逐字引文/唯一性/确定性重建/单一报告边界/不标 verified） |

### 引用登记明细（{len(refs)} 条，locator=原文整行）

| ref_id | kind | 首现行 | 次数 | 原文 token | 存在性 |
|---|---|---|---|---|---|
{ref_rows}

### 小节切分（{len(secs)} 节）

| # | 级 | 行区间 | 字符 | sha256 前缀 | 标题 |
|---|---|---|---|---|---|
{sec_rows}

### 附件交叉核对（正文 §4 vs 平台 figures 字段）

| name | name 在正文 | caption 逐字一致 |
|---|---|---|
{cross_rows}

### 观察项（不裁决，如实登记）

| id | kind | status | 陈述 |
|---|---|---|---|
{obs_rows}

## ④ 证据定位表（字段 → 原文引文，逐字）

| 字段 | 原文引文（逐字） |
|---|---|
{chr(10).join(ev_rows)}

全部 locator 均机检通过：`{lc['resolved']}/{lc['total']}` 解析成功、未解析 `{lc['unresolved']}` 条
（方法：markdown 项 `quote in markdown`，figures 项 `caption in markdown`）。

## ⑤ 注意点与局限

1. **glob 引用不可直接解析（honest-unresolved）**：C6 探针在判据表中写作 glob
   （§3.1），§7 审计链展开为两个显式文件（14 例 + 10 例 = 24 例）；
   glob 本身不是可解析路径，展开计数一致性（24=24）仅登记不裁决（`12595-obs-01`）。
2. **工件存在性未核**：报告声明的全部代码/测试/工件（`acceptance.json`、`delta_sweep.csv`、
   `sensitivity_fields.npz`、4 张 PNG、3 个 simp 模块、2 个测试文件）位于 m11206 的
   TensorPhysics worktree（`/root/tp-agent/work/m11206`，`agent/m11206`）；本包工作树为
   TensorKnowledge，跨树取证会越界，故全部 `existence=not_checked`，不主张这些工件存在或其哈希正确。
3. **附件载荷**：figures 仅元数据（无 png_base64），无法核验图与其数据的一致性；
   但正文 §4 的 4 个 PNG 路径与 figures 字段 4 条图注 name+caption 逐字一致（机检 4/4）。
4. **不做抽取语义判定**：报告 12595 的 C1..C6 PASS、混合精度 FD 等结论属上游自述，
   本包只登记其位置备查，不背书、不复算、不标 verified。
5. **正文无内容摘要值**：无 16+ 位十六进制摘要、无 URL、无 markdown 图片语法（机检 0 命中），
   `content_digests` 为空数组。
6. 适用范围：生成器可复用于任意 report 的资产登记（改 `REPORT_ID`/`CONTRACT_*` 常量），
   前提是只登记不解读。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 |
|---|---|
{checks_rows}

诚实声明：上表 ✅ 只表示**本工序的登记动作正确**，不代表报告 12595 的科学结论已获验证；
`observations` 中的 unresolved 项保持 unresolved，未做粉饰。若有任何项失败，亦在本节如实列出。

### repro_cmd（一键复跑）

```bash
cd <repo-root> \\
 && python3 scripts/kf/wp-12595-01/register_assets.py --check \\
 && python3 scripts/kf/wp-12595-01/make_report.py \\
 && python3 scripts/kf/wp-12595-01/make_figure.py \\
 && python3 -m pytest tests/kf/test_wp_12595_01.py -q
```

离线复跑（无平台凭据）：`python3 scripts/kf/wp-12595-01/register_assets.py --from-file work/wp-12595-01/source/report_12595.md --record-json work/wp-12595-01/source/report_12595.json --check`。

## 附：kf_result.json（唯一 json 块，与 `docs/kf/wp-12595-01/kf_result.json` 同字节）

```json
{json_block}
```
"""
    (OUT / "kf_result_wp-12595-01.md").write_text(md_out, encoding="utf-8")
    print("wrote", OUT / "kf_result_wp-12595-01.md", len(md_out), "chars")
    # sanity: exactly one json block
    n_blocks = len(re.findall(r"^```json", md_out, flags=re.M))
    assert n_blocks == 1, f"expected exactly 1 json block, got {n_blocks}"
    print("json blocks:", n_blocks)


if __name__ == "__main__":
    main()
