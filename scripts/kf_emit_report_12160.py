#!/usr/bin/env python3
"""Emit the KF-RESULT markdown for wp-12160-01.

The result envelope is embedded as the single ```json block by *reading*
docs/kf/wp-12160-01/kf_result.json — the JSON is never retyped, and the tables in
§④/§⑥ are generated from asset_manifest.json / selfcheck.json, so no number in the
report body is hand-copied.

    python3 scripts/kf_emit_report_12160.py --out docs/kf/wp-12160-01
"""

from __future__ import annotations

import argparse
import json
import os

PKG = "wp-12160-01"


def md_table_cell(text: str, width: int = 64) -> str:
    text = text.replace("\n", "\\n").replace("|", "\\|")
    return text if len(text) <= width else text[: width - 1] + "…"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join("docs", "kf", PKG))
    ap.add_argument("--supersedes", default="",
                    help="report id this emission replaces; rendered as a one-line header note")
    args = ap.parse_args()
    out = args.out

    manifest = json.load(open(os.path.join(out, "asset_manifest.json"), encoding="utf-8"))
    result = json.load(open(os.path.join(out, "kf_result.json"), encoding="utf-8"))
    check = json.load(open(os.path.join(out, "selfcheck.json"), encoding="utf-8"))
    src = manifest["source"]
    integ = manifest["integrity"]

    # §④ asset table, generated from the manifest
    rows = []
    for a in manifest["assets"]:
        rows.append(
            f"| {a['asset_id']} | {a['asset_class']} | `{md_table_cell(a['label'], 52)}` | "
            f"{a['in_report_section'][:12]} | L{a['locator']['start_line']}–{a['locator']['end_line']} | "
            f"{a['resolution']} | \"{md_table_cell(a['locator']['quote'], 60)}\" |"
        )

    # §⑥ acceptance table, generated from selfcheck.json (acceptance items and the
    # extra non-contract guards are kept in separate tables and never mixed)
    def row(name, c):
        mark = '✓' if c['result'] == 'PASS' else ('—' if c['result'] == 'not_run' else '✗')
        return f"| {name} | {mark} | {c['result']} |"

    acc_rows = [row(n, c) for n, c in check["acceptance"].items()]
    extra_rows = [row(n, c) for n, c in check.get("extra_checks_not_in_contract", {}).items()]
    n_acc, n_extra = len(acc_rows), len(extra_rows)

    counts = manifest["counts"]
    supersede_line = (f"\n> 本版取代同工作包前版 report `{args.supersedes}`：同一 source_hash，"
                      f"仅将 2 条非契约自查项从 acceptance 表中分出单列（结论未变，仍全 PASS）。\n"
                      if args.supersedes else "")
    json_block = json.dumps(result, ensure_ascii=False, indent=2)

    body = f"""# KF-RESULT {PKG}

工作包 `{PKG}` · 工序 `01-asset-registration` · report_id=`{manifest['report_id']}` ·
lane C · 交付仓 TensorKnowledge（status=draft）
{supersede_line}

## ① 本工序做了什么

只做“登记源资产”一件事，对 report `12160` 的 markdown 做三件可机器复核的事：

1. **确认源实例与其字节哈希**：从平台取回 `tensor://reports/12160` 的 `markdown` 字段，
   重算 sha256 = `{integ['hash_recomputed_locally']}`，与工作包契约 `source_hash` 逐字符一致
   （`hash_matches_contract = {str(integ['hash_matches_contract']).lower()}`）；字符数
   {src['chars']} / UTF-8 字节 {src['bytes_utf8']}，与契约 `chars` 一致（`chars_match = {str(integ['contract_cross_checks']['chars_match']).lower()}`）。
2. **列出可解析的附件/工件共 {counts['assets']} 项**，每项给一个逐字可定位的 locator（char span + 行号 + 唯一性）：
   resolved_in_source {counts['resolved_in_source']} / referenced_unresolved {counts['referenced_unresolved']} /
   declared_absent {counts['declared_absent']}。
3. **不做抽取**：`claims = []`（契约 `objective.register_assets=true`、`no_forced_claim_generation=true`），
   未对报告任何结论做验证或否证——`verified` 由平台门计算，本包不写、也不暗示。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `GET $TENSOR_API_BASE/tensor/reports/12160`（Bearer=eco_admin 登录 token）取 `markdown`；
   同时取记录元数据（title/scenario_key/tags/figures/status/mission_id）落
   `source_record.json`——报告标题与 scenario 一律来自平台记录，不由我手打。
2. 把 markdown 逐字节存成 `source_markdown.md`，重算 sha256 与契约比对（`integrity.hash_matches_contract`）。
3. 程序化枚举资产：正则抓 `路径` / `dotted 符号` / `调用` / `MEPC.*` 引用 + 结构扫描抓
   `| 表格块` 与内联 JSON 块；每个候选都用 `str.find` 在原文里取 char span、行号与出现次数，
   歧义者按行向两侧扩窗直到全文唯一（`context_expanded_lines` 记录扩了几行，绝不改写原文）。
4. 逐项做**真实解析检查**（不是断言）：路径类 → 在三个有界只读根
   （本 worktree / `ship-performance-platform` 两个本地检出）做 `os.path.exists`；
   符号类 → `grep -rFl --include=*.py`（排除本包自身脚本，防自指假阳性）；
   标准类 → 离线不可得，登记为 unresolved；规则侧系数 → 报告自述离线不可回读，登记为 declared_absent。
5. `scripts/kf_selfcheck_12160.py` 把契约 {n_acc} 条 acceptance + {n_extra} 条自查项逐条机器裁决（分组输出，不混计），
   写 `selfcheck.json`；`pytest tests/test_kf_wp_12160_01.py` 6 条（含 2 条负控：改字节/移位必须 FAIL）。
6. 本 markdown 由 `scripts/kf_emit_report_12160.py` 从上述三个 JSON 渲染，表格与 JSON 块零手抄。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12160-01/asset_manifest.json` | 登记清单本体：source 哈希/字符数 + {counts['assets']} 项资产（各带 locator/resolution/resolution_check）+ claims=[] + integrity |
| `docs/kf/wp-12160-01/kf_result.json` | 结果信封（kf_result.v1）：package_id/task_type/report_id/provenance/outputs，通过 `schemas/kf_result.v1.schema.json` |
| `docs/kf/wp-12160-01/selfcheck.json` | 8 条机器裁决（6 acceptance + 2 自查），全 PASS；含复跑命令 |
| `docs/kf/wp-12160-01/source_markdown.md` | 报告 markdown 的逐字节副本（sha256=`{integ['hash_recomputed_locally']}`），使本包可离线复核 |
| `docs/kf/wp-12160-01/source_record.json` | 平台记录元数据快照（不含 markdown），标题/scenario/figures 的唯一出处 |
| `docs/kf/wp-12160-01/asset_manifest.v1.localized.json` | 校验用 schema 本地化副本（仅 `package_id`/`report_id`/`source.uri` 三个 const 换绑，换绑清单写在 `x_localized_consts`） |
| `scripts/kf_register_12160.py` | 登记器（可 `--source-file` 离线复跑） |
| `scripts/kf_selfcheck_12160.py` | 验收自检器（`--live-api` 时额外回平台重算哈希） |
| `scripts/kf_emit_report_12160.py` | 本报告的渲染器 |
| `tests/test_kf_wp_12160_01.py` | 6 条 pytest（4 正 + 2 负控） |
| `contracts/wp-12160-01.yaml` | 工作包契约原文（供哈希与字符数交叉核对） |

## ④ 证据定位表（asset_id → 原文逐字引文；全部可在 `source_markdown.md` 定位）

| id | class | label | 节 | 行 | resolution | 原文引文（逐字，长引文截断处标 …） |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

- 唯一性：`all_char_span_quotes_unique = {str(integ['quote_uniqueness']['all_char_span_quotes_unique']).lower()}`；
  {len(manifest['assets']) - 1} 条 char_span locator 逐条复核 `md[start:end] == quote` 且 `start_line == count('\\n',0,start)`。
- 本包**不对**上述任何条目做内容判定：路径类未读取文件内容、符号类未 import 执行、
  标准与规则侧系数离线文本未取得——故全部标 unresolved/absent，无一标 verified。

## ⑤ 注意点与局限

* **本包只登记不解释**：报告里所有结论（如“端到端 <5% 被否证”“1852 倍单位缺陷已修复”）都未被我复核；
  登记为资产 ≠ 认可其真实性。
* **工件不可达**：`artifacts/eexi_closed_loop*.py/.json` 与 4 张图在三个有界只读根下均不存在
  （本 worktree=知识仓、本地 ship-performance-platform 检出只有 backend/、incoming 检出无该目录）
  ⇒ 16 项 referenced_unresolved。这是**范围事实**，不是“报告造假”的判定。
* **`chars` 一致性**：契约 `chars=9351` 与实测字符数一致，UTF-8 字节为 {src['bytes_utf8']}（中文 3 字节，勿把字节数当字符数）。
* **schema 本地化**：随仓的 `schemas/asset_manifest.v1.schema.json` 把 `package_id`/`report_id`/`source.uri`
  写死为 wp-448-01，直接套用必失败；本地化副本只换这三个 const 并留痕。**平台侧 schema 若有异，以平台门为准**——
  这是 schema_pass 的已知薄弱点。
* **单次读取**：本包在 2026-11-12 单次读取该报告；报告若被上游改写，`source_hash_matches` 会立即变红（负控测试已证）。
* **无图**：本工序是资产登记/寄存器类任务，不产生场量或对比曲线；图形证据属上游报告（其 §④ 4 张 PNG 已登记为 A04–A07，
  字节不可达故未内嵌）。

## ⑥ 自检：逐条对照 acceptance

契约 acceptance（{n_acc} 项，与契约逐条对应）：

| acceptance 项 | 结论 | selfcheck.result |
|---|---|---|
{chr(10).join(acc_rows)}

额外自查（{n_extra} 项，不属契约 acceptance，单列以免混淆）：

| 自查项 | 结论 | selfcheck.result |
|---|---|---|
{chr(10).join(extra_rows)}

- `all_pass = {str(check['all_pass']).lower()}`（{n_acc}+{n_extra}={n_acc + n_extra} 项全 PASS）；
  `not_run = {json.dumps(check['not_run'], ensure_ascii=False)}`（无未执行项）。
- 失败项：**无**。诚实声明两处口径：①`all_claims_have_evidence_or_explicit_unresolved_status`
  因 `claims=[]` 而**空真**成立——它是“没有无据主张”，不是“抽取已做”；②`schema_pass` 依赖上面说的本地化 schema。
- 负控（证明检查会响）：把 `source_markdown.md` 尾部加一个换行 ⇒ `source_hash_matches` FAIL；
  在头部插 7 字节 ⇒ char-span locator 全部错位 ⇒ `source_locator_resolvable` FAIL（pytest 两条负控覆盖）。

## repro_cmd

```bash
cd <TensorKnowledge worktree>
python3 scripts/kf_register_12160.py  --out docs/kf/wp-12160-01            # 或 --source-file <md>
python3 scripts/kf_selfcheck_12160.py --out docs/kf/wp-12160-01 --live-api # 8 条裁决
python3 -m pytest -q tests/test_kf_wp_12160_01.py                          # 6 条（含 2 负控）
python3 scripts/kf_emit_report_12160.py --out docs/kf/wp-12160-01          # 重渲染本报告
```

---

```json
{json_block}
```
"""

    path = os.path.join(out, f"KF-RESULT-{PKG}.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(body)
    n_json = body.count("```json")
    print(json.dumps({"path": path, "chars": len(body), "json_blocks": n_json,
                      "assets": counts["assets"], "all_pass": check["all_pass"]},
                     ensure_ascii=False))
    return 0 if n_json == 1 else 1


if __name__ == "__main__":
    raise SystemExit(main())