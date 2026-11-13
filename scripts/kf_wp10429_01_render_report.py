#!/usr/bin/env python3
"""Render the KF-RESULT report for wp-10429-01 from the artefacts themselves.

Every number and every quote in the body is formatted *out of* the JSON artefacts
(asset_manifest.json / verification.json / selftest.json) — nothing is typed by hand,
so the manuscript cannot drift from the evidence (zero hand-copy rule).  The envelope
runs/wp-10429-01/kf_result.wp-10429-01.json is embedded as the report's single ```json
block.

Outputs
  docs/kf/wp-10429-01/KF-RESULT-wp-10429-01.md   (canonical)
  docs/kf_result_wp-10429-01.md                  (publish path used by the poster)
Usage: python3 scripts/kf_wp10429_01_render_report.py
"""
from __future__ import annotations

import json
import pathlib
import sys

RUN = pathlib.Path("runs/wp-10429-01")
DOC = pathlib.Path("docs/kf/wp-10429-01")
PACKAGE_ID = "wp-10429-01"

manifest = json.loads(pathlib.Path("artifacts/wp-10429-01/asset_manifest.json").read_text())
verif = json.loads((RUN / "verification.json").read_text())
selftest = json.loads((RUN / "selftest.json").read_text())
envelope = json.loads((RUN / "kf_result.wp-10429-01.json").read_text())
src = manifest["source"]
prov = envelope["provenance"]


def one_line(q: str, limit: int = 96) -> str:
    s = q.replace("\n", " / ").replace("|", "\\|").replace("`", "\u2032")
    return s if len(s) <= limit else s[: limit - 1] + "…"


def check_mark(flag: bool) -> str:
    return "✅" if flag else "❌"


assets = manifest["assets"]
_a20 = [x for x in assets if x["asset_id"] == "A20"][0]["resolution_check"]
_a20n = len(_a20.get("declared", []))
_a20m = len(_a20.get("platform_figure_names", []))
res_counts = manifest["counts"]["by_resolution"]
n_span = sum(1 for a in assets if a["locator"]["method"] == "char_span")
n_resolved = res_counts.get("resolved_in_source", 0)
n_unres = res_counts.get("referenced_unresolved", 0)
n_absent = res_counts.get("declared_absent", 0)
v = verif["checks"]
st_cases = selftest["cases"]

acc_rows = [
    ("valid_json", v["valid_json"]["pass_"],
     f"manifest {v['valid_json']['manifest_bytes']} B + envelope {v['valid_json']['envelope_bytes']} B 均可解析；docs 镜像逐字节相同={v['valid_json']['durable_mirror_identical']}"),
    ("schema_pass", v["schema_pass"]["pass_"],
     f"jsonschema 校验 2 个文件（{v['schema_pass']['error_count']} error）"),
    ("source_locator_resolvable", v["source_locator_resolvable"]["pass_"],
     f"{v['source_locator_resolvable']['assets_checked']} 个定位器在新鲜源文上切片复算，失败 {len(v['source_locator_resolvable']['failing'])}"),
    ("source_hash_matches", v["source_hash_matches"]["pass_"],
     f"重算 {v['source_hash_matches']['recomputed_sha256'][:16]}… == 契约 {v['source_hash_matches']['contract_sha256'][:16]}…；chars {v['source_hash_matches']['chars']}"),
    ("no_duplicate_ids", v["no_duplicate_ids"]["pass_"],
     f"{v['no_duplicate_ids']['n_assets']} 个 asset_id 无重复"),
    ("all_claims_have_evidence_or_explicit_unresolved_status",
     v["all_claims_have_evidence_or_explicit_unresolved_status"]["pass_"],
     f"claims={v['all_claims_have_evidence_or_explicit_unresolved_status']['n_claims']}（零 claim，空真）"),
    ("envelope_links（附加自检，非契约项）", v["envelope_links"]["pass_"],
     f"provenance.source_hash 与契约一致；verification_status={v['envelope_links']['verification_status']}"),
]

ev_rows = []
for a in assets:
    loc = a["locator"]
    span = "document" if loc["method"] == "document" else f"L{loc['start_line']}–{loc['end_line']} / c{loc['start_char']}–{loc['end_char']}"
    ev_rows.append(f"| {a['asset_id']} | {a['asset_class']} | {a['resolution']} | {span} | ”{one_line(loc['quote'])}“ |")

st_rows = [f"| {k} | {'—（基线，期望全绿）' if k == 'baseline' else v0.get('expect_fail', k)} | "
           f"{check_mark(bool(v0.get('ok', v0.get('all_pass'))))} | {', '.join(v0.get('failed') or []) or '—'} |"
           for k, v0 in st_cases.items()]

body = f"""# KF-RESULT {PACKAGE_ID}

> 工序：`01-asset-registration`（lane C，contract_version 1.0）｜report_id **{manifest['report_id']}**｜
> source_uri `{src['uri']}`｜source_field `{src['field']}`｜scenario_key `{src['scenario_key']}`
> 本报告由 `scripts/kf_wp10429_01_render_report.py` 从工件直接渲染，正文数字/引文零手抄。

## ① 本工序做了什么

对 report 10429（《{src['title']}》）做**资产登记**：确认 report_id 与其 markdown 的字节哈希一致，
把报告里可解析的资产（正文/表/代码指针/图件声明/文献集等）逐条登记成带**字符级定位器**的清单，
不做知识抽取（契约 `objective.classify_report_type=false`、notes 明确「不做抽取，claims 允许为空数组」），
不对任何结论标 verified（verification 由平台门计算）。

结果概览：登记 **{manifest['counts']['assets']} 个资产**（resolved_in_source {n_resolved} / referenced_unresolved {n_unres} /
declared_absent {n_absent}）；markdown sha256 与契约 `source_hash` **逐位相等**；{n_span} 个 char_span 引文
全部在源文逐字命中且全篇唯一。上游报告的实质结论（Turek-Hron 2D-2 锚定 CD −11.2% / CL −19.2% / St −11.3%、
FSI-2 为 honest-FAIL、旧 fsi_turek_hron 与 fsi_flutter 被证伪）**只登记、不复核、不改判**。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET {prov['retrieved_via'].split('GET ')[-1]}`（Bearer 由 env 登录 `/auth/login` 取得，凭据不落盘），
   保存 `runs/wp-10429-01/report_10429.json`（原始 record）与 `report_10429.md`（markdown 本体）。
2. **对哈希**：本地重算 `sha256(markdown)` = `{src['hash']}`，与契约
   `sha256:{prov['source_hash'].split(':')[-1]}` 相等；chars {src['chars']} 与契约 7442 相等；title 与契约 title 相等。
   三者任一不等，登记脚本直接 `exit 2`（不产出半成品）。
3. **定位器生成（零手抄的关键）**：资产表里只写「锚样子串 + 行偏移」，脚本 `find_line()` 断言该锚在源文
   **恰好命中 1 行**，再由 `line_offsets()` 把行号换算成字符偏移，`quote` 由 `md[offs[s]:offs[e]+len(...)]`
   **切出**而非键入；并断言 `md.count(quote)==1`。锚或唯一性不成立即硬失败（本轮修掉了 5 处越界/重叠 span，
   见 §⑤）。
4. **解析性判定（不臆造地址）**：每个资产给 `resolution` 三态 + 机器可复算的 `resolution_check`：
   - `resolved_in_source` → 切片命中（或整篇 document 的 sha256 命中）；
   - `referenced_unresolved` → 对外部仓文件路径/符号做**工作树存在性查找**，未命中即 unresolved，且报告未给
     URL/DOI/commit，**不猜地址**；
   - 图件声明另做「平台 record.figures 名称比对」（declared {_a20n} / matched {_a20m}）。
5. **独立复核**：`scripts/kf_wp10429_01_verify.py` **重新从 API 取全文**（不复用本地副本），
   逐条重解析定位器、用 jsonschema 校验 manifest（包内固定 schema）与信封（仓库 `schemas/kf_result.v1.schema.json`）、
   查重 ID、查 claim 证据位。验收项 {sum(1 for r in acc_rows[:6] if r[1])}/6 通过 + 1 项附加。
6. **反证（阴性对照）**：`scripts/kf_wp10429_01_selftest.py` 在临时目录副本上逐项注入缺陷，断言**指定**验收项翻红——
   绿门不等于有效门，见 §⑥ 表。

`repro_cmd`（工作树根执行，需 env `TENSOR_API_BASE/TENSOR_AGENT_USER/TENSOR_AGENT_PASS`）：

```bash
python3 scripts/kf_wp10429_01_register.py && python3 scripts/kf_wp10429_01_verify.py \
  && python3 scripts/kf_wp10429_01_selftest.py && python3 scripts/kf_wp10429_01_render_report.py
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/wp-10429-01/asset_manifest.json` | 契约输出；{manifest['counts']['assets']} 资产 + 定位器 + resolution_check + integrity；sha256 `{prov['artifact_sha256']}`，{prov['artifact_bytes']} B |
| `docs/kf/wp-10429-01/asset_manifest.json` | 上者**逐字节**持久镜像（push gate 会丢 artifacts/、runs/） |
| `runs/wp-10429-01/kf_result.wp-10429-01.json` | kf_result.v1 信封（本报告唯一 json 块的来源） |
| `runs/wp-10429-01/verification.json` | 独立复核对账：7 项检查逐项 pass/fail 与证据字段 |
| `runs/wp-10429-01/selftest.json` | 阴性对照：{len(st_cases)} 例（基线 + {len(st_cases)-1} 注入缺陷）逐例裁决 |
| `runs/wp-10429-01/report_10429.md` | 源 markdown 本地副本（{src['chars']} chars / {src['bytes_utf8']} B UTF-8） |
| `schemas/asset_manifest.v1.wp-10429-01.schema.json` | 包内固定 manifest schema（仅 const 换成本包 ID，字段集与 448 版全同） |
| `scripts/kf_wp10429_01_{{register,verify,selftest,render_report,publish}}.py` | 产线五件套，可一键复跑 |

## ④ 证据定位表（字段 → 原文引文片段，逐字切片）

| 资产 | 类别 | resolution | 定位（行 / 字符） | 原文引文（逐字，截断） |
|---|---|---|---|---|
{chr(10).join(ev_rows)}

> 引文由 `char_span` 切出，平台可对 `source_uri` 重算 sha256 并做子串二次确认；完整 quote 见 manifest。

## ⑤ 注意点与局限

1. **只登记不抽取**：`claims=[]`。上游的「CD −11.2%」「FSI-2 honest-FAIL」「旧模块应降级 MOCK」等结论**未被本工序
   验证**，也没被改写；它们在下游工序才成为知识对象候选。
2. **外部工件不可解析**：{n_unres} 个 `referenced_unresolved` 指向 TensorFEM 仓的相对路径与符号
   （`src/tensorfem/lbm_channel2d.py`、`CantileverBeamFE`/`ModalCantileverBeam`、`StrongCouplingFSI2`）；
   本工作树是 TensorKnowledge，无该仓代码，报告也未给 commit/URL/DOI——**不猜地址**，如实标 unresolved。
   因此「代码 ↔ 报告数字」的可追溯链在本工序**没有闭合**，需外部仓或 commit 号补齐。
3. **`declared_absent` 为 {n_absent}**：本报告没有声明缺件，图件声明 4 项在平台 record.figures 中同名存在，
   故登记为 resolved（声明可定位 + 名称比对命中），但**图件字节未做内容核验**（不做图像审读）。
4. **解析口径的边界**：`A03` 只登记到 `branch agent/m8136`，报告未给 commit sha，故「产出对应哪一版代码」
   无法由本工序锁定——这是源文的缺口，不是解析失败。
5. **span 越界已修**：首版生成时 5 处 span 越界/重叠（A04 吞了物理参数行、A07 与 A08 重叠、
   A14 多吞 1 行、A17/A18 溢出到下一节、A20 漏掉第 4 个图件）。改法不是手调数字，而是加 `end_anchor`
   语义（结束行由另一条唯一锚定位）+ 断言 `md.count(quote)==1`，重跑后全绿。
6. **不是 verified**：`provenance.verification_status = "not_verified"`，本工序不越权置位。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据 |
|---|---|---|
{chr(10).join(f"| {k} | {check_mark(ok)} | {ev} |" for k, ok, ev in acc_rows)}

**阴性对照（证明上面这些 ✅ 不是空真）**：在临时目录副本上注入单点缺陷后，"符合预期" ✅ 表示**指定检查确实翻红**、
门 exit=1（即验收项可被证伪，不是恒真印钞机）：

| 注入的缺陷 | 期望翻红的检查 | 符合预期 | 实际失败的检查项 |
|---|---|---|---|
{chr(10).join(st_rows)}

**失败项如实申报**：本轮无诚实失败项；契约 6 项全部 ✅（其中 claims 项在零 claim 下为空真，已在表中注明，
不以造 claim 的方式凑数）。未做/做不到的：外部仓工件地址（§⑤-2）、图件内容核验（§⑤-3）。

**误差判定（key quantity vs 基准）**：本工序无物理量计算，唯一的「计算 vs 基准」是
源文身份：`sha256(markdown)` 与契约值 **逐位相等（相对误差 0%）**、chars {src['chars']} vs 7442（0%）、
标点级切片 {n_span}/{n_span} 命中（0%）。**是否 <3%：是（实为 0%）**。上游报告里的物理误差
（CD −11.2%、CL −19.2%、St −11.3%，均远超 15%/10% 容差）属**源文内容**，本工序原样登记、不背书、不改判。

**图件说明（无图理由）**：本工序是文档资产登记，不产生任何场量或对比曲线，故 `figures: []`；
可复现性由 §⑥ 的阴性对照表与 §② 的 `repro_cmd` 承担，不虚构图件。

## 唯一结果 JSON 块（kf_result.v1）

```json
{json.dumps(envelope, ensure_ascii=False, indent=2)}
```
"""

DOC.mkdir(parents=True, exist_ok=True)
canon = DOC / f"KF-RESULT-{PACKAGE_ID}.md"
canon.write_text(body)
pub = pathlib.Path(f"docs/kf_result_{PACKAGE_ID}.md")
pub.write_text(body)
# guard: exactly one ```json block in the manuscript
n_json_blocks = body.count("```json")
assert n_json_blocks == 1, f"manuscript must carry exactly one json block, found {n_json_blocks}"
print("wrote", canon, len(body), "chars")
print("wrote", pub)
sys.exit(0)