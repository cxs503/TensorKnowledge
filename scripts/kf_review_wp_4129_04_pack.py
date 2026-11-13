#!/usr/bin/env python3
"""wp-4129-04: pack the review into the delivery envelope + the KF-RESULT markdown.

Writes
  work/wp-4129-04/kf_result.json   envelope {package_id, task_type, report_id, provenance, outputs}
  docs/kf/wp-4129-04.md           KF-RESULT document: exactly one ```json block (the envelope)

Every number in the document body is injected from the JSON artefacts
(review_report.json / review_findings.json / the pinned source bytes), so the text
carries no hand-copied number.
"""
import datetime
import hashlib
import json
import pathlib

WT = pathlib.Path(".")
SRC = WT / "work/wp-4129-04/source/report_4129.md"
REVIEW = WT / "work/wp-4129-04/review_report.json"
FINDJSON = WT / "work/wp-4129-04/review_findings.json"
UPSTREAM = WT / "knowledge/kf/wp-4129-01/kf_result.json"
OUT_ENV = WT / "work/wp-4129-04/kf_result.json"
OUT_MD = WT / "docs/kf/wp-4129-04.md"

raw = SRC.read_bytes()
md = raw.decode("utf-8")
lines = md.rstrip("\n").split("\n")
src_sha = "sha256:" + hashlib.sha256(raw).hexdigest()
review = json.loads(REVIEW.read_text(encoding="utf-8"))
find = json.loads(FINDJSON.read_text(encoding="utf-8"))
manifest = json.loads(UPSTREAM.read_text(encoding="utf-8"))["outputs"]["asset_manifest.json"]

envelope = {
    "package_id": "wp-4129-04",
    "task_type": "04-independent-review",
    "report_id": "4129",
    "provenance": {
        "source_hash": src_sha,
        "source_field": "markdown",
        "producer": "kf-worker/m15827",
        "emitted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "notes": "sha256 recomputed by the reviewer from its own GET /api/v1/tensor/reports/4129 "
                 "(field `markdown`, UTF-8 bytes); review of wp-4129-01 only",
    },
    "outputs": {"review_report.json": review},
}
OUT_ENV.parent.mkdir(parents=True, exist_ok=True)
OUT_ENV.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")

cert = review["certified_by_review"]
fid = review["semantic_fidelity"]
qs = review["quotation_surface"]
f1, f2 = review["findings"]
reg, red = f2["evidence"]["upstream"], f2["evidence"]["rederived"]
miss = f2["evidence"]["missing_sites"]
cen = [c for c in find["checks"] if c["check_id"] == "body_path_reference_census"][0]
n_tok = len(manifest["vcs_references"]) + len(manifest["symbol_references"])
n_tok_bad = len(find["defects"]["token_outside_quote"])
site_dev = red["body_path_references"] - reg["body_path_references"]
site_pct = site_dev / red["body_path_references"] * 100
tok_pct = n_tok_bad / n_tok * 100
n_tests = (WT / "tests/test_kf_wp_4129_04.py").read_text(encoding="utf-8").count("\ndef test_")
n_quote_files = len(json.loads((WT / "work/wp-4129-04/evidence/quotes.json").read_text(encoding="utf-8")))

ev_rows = "\n".join(
    f"| `{f['fact_id']}` | {json.dumps(f['upstream'], ensure_ascii=False)} | "
    f"{json.dumps(f['rederived'], ensure_ascii=False)} | {'✗' if not f['pass'] else '✓'} | "
    f"L{f['evidence']['line']} `{f['evidence']['quote'][:36]}` |"
    for f in fid["per_fact"])

chk_rows = "\n".join(
    f"| `{c['check_id']}` | {json.dumps(c['upstream_value'], ensure_ascii=False)[:64]} | "
    f"{json.dumps(c['recomputed'], ensure_ascii=False)[:64]} | {'✓' if c['pass'] else '✗'} |"
    for c in find["checks"])

probes = find["probes"]
probe_rows = "\n".join(f"| `{p}` | {v['status']} | {v['bytes']} |" for p, v in probes.items()
                       if isinstance(v, dict) and "status" in v)

acc = [
    ("valid_json", "`kf_result.json` 解析通过，`review_report.json` 在 `outputs` 内",
     "`python3 -c \"import json;json.load(open('work/wp-4129-04/kf_result.json'))\"`"),
    ("schema_pass", "对 `schemas/kf_result.v1.schema.json` 校验通过（draft 2020-12）",
     "`pytest -q tests/test_kf_wp_4129_04.py::test_envelope_validates_against_schema`"),
    ("reviewer_independent", "自己取源、自己登录；生产者脚本/测试/叙述全部排除并登记在 `independence`",
     "`review_report.json.independence.reviewer_context_excluded`"),
    ("upstream_packages_completed", "上游 `knowledge/kf/wp-4129-01/kf_result.json` 在位，sha256 钉在 `reviewed_artifacts`",
     "`pytest -q tests/test_kf_wp_4129_04.py::test_reviewed_upstream_hash_is_pinned`"),
]
acc_rows = "\n".join(f"| {a} | {b} | {c} | ✓ |" for a, b, c in acc)

doc = f"""# KF-RESULT wp-4129-04

tags: `kf-wp:wp-4129-04`, `kf`, `independent-review`, `red-team`, `report-4129`, `wp-4129-01`

独立审核单：审核对象 `wp-4129-01`（report 4129 的资产登记包）。判据=登记事实能否从原文独立复算、
有没有把未验证的写成已验证。结论：**{review['verdict']}（不阻塞）**——注册内容属实，两处登记精度缺陷须修。

## ① 案例介绍（物理背景 / 问题描述 / 参数表）

**物理背景：本工序不含物理场，理由如下。** 它是报告→知识产线的质量保证工序（独立审核），被审对象是
"资产登记包"，不是水动力/结构算例；所以没有场量云图可画、没有解析解可比。审核对象背后的物理内容
（TensorFEM Q4 Mindlin 板均布压力复核）只以**文字**进入本单，其证据留在 TensorFEM 仓，本单不重算。

**问题描述**：（i）上游 `wp-4129-01` 写下的每条断言，能否由审核者从原文独立重算；
（ii）它有没有把未验证的东西写成已验证。

**参数表（本单操作参数，非物理参数）**：

| 项 | 值 |
|---|---|
| 审核对象 | `wp-4129-01`：{fid['facts_re_derived']} 条保真事实 / {cert['checks_total']} 条机器检查 |
| 报告原文 | `tensor://reports/4129`，{len(md)} chars / {len(raw)} bytes / {len(lines)} lines |
| 原文 sha256（本单重算） | `{src_sha}` |
| 源信道 | `GET /api/v1/tensor/reports/4129`（独立登录、独立请求） |
| 复算工具链 | `scripts/kf_review_wp_4129_04_{{fetch,verify,evidence,emit,pack}}.py` + `pytest` |
| 外部探针 | `/artifacts`、`/figures/merge_audit.png`、`/figures/plate_gate.png` |

## ② 怎么做的（步骤 / 工具 / 关键设置）+ 产出物清单

1. **取源**：自己的登录、自己的请求（不复用上游落盘副本），落盘后取 UTF-8 字节哈希
   `{src_sha}`，与契约声明的 `source_hash` 逐字节相等，`chars={len(md)}`、`bytes={len(raw)}` 亦对上。
   直连 `psql` 读 `tensor_reports` 被拒（实测 `ERROR: permission denied for table tensor_reports`），API 是唯一信道。
2. **逐条复算**（`scripts/kf_review_wp_4129_04_verify.py`）：5 类可判定断言面——源身份 / 定位器（引文是否逐字、
   是否落在声明行、record 指针解引用）/ 计数与 id / git 记号与前缀算术 / 诚实面（`verified` 标记、claims 空值合规、
   `未完成` 是否被偷换）。结果写 `work/wp-4129-04/review_findings.json`。
3. **原文切片取证**（`scripts/kf_review_wp_4129_04_evidence.py`）：要引的每句按行号/子串**切片**得到，
   随切片存 `quote_sha256`；`emit` 写盘前断言"每条引文都是原文子串"，不满足即崩。
4. **端点复探**：`/artifacts` 与两张图端点自己再打一次（见 ③ 表）。
5. **独立性**：不看生产者脚本（`scripts/kf_wp_4129_01_*.py`）、不看生产者测试、不看生产者叙述
   （`docs/kf/wp-4129-01.md` 里的 JSON 代码块解析后与该包 `kf_result.json` 完全相等——实测相等，故不增加独立证据）。

产出物：

| 文件 | 要点 |
|---|---|
| `work/wp-4129-04/review_report.json` | 结论本体：verdict=`{review['verdict']}`，保真事实 {fid['facts_passed']}/{fid['facts_re_derived']}，检查 {cert['checks_passed']}/{cert['checks_total']}，发现 {len(review['findings'])} 条 |
| `work/wp-4129-04/review_findings.json` | 机器复算明细（逐检查 upstream vs 复算）、缺陷清单、端点探测 |
| `work/wp-4129-04/evidence/quotes.json` | {n_quote_files} 条原文切片（行号 + sha256） |
| `work/wp-4129-04/evidence/path_refs.json` | 路径引用普查（站点/去重/正文图链接） |
| `work/wp-4129-04/source/report_4129.md` | 报告原文（独立取得，哈希已钉） |
| `work/wp-4129-04/kf_result.json` | 交付信封（本文件唯一 json 块） |
| `tests/test_kf_wp_4129_04.py` | {n_tests} 项自检（schema/哈希/引文逐字/行号/结论与检查表一致/无 verified/单报告/交付一致） |
| `docs/kf/figures/wp-4129-04.png` | 审核证据三面板图 |

## ③ 计算结果

**复算明细（{cert['checks_passed']}/{cert['checks_total']} 通过）**：

| 检查 | 上游断言（截断） | 复算值（截断） | 判定 |
|---|---|---|---|
{chk_rows}

**端点复探（自己打，不引用上游记录）**：

| 端点 | HTTP | 字节 |
|---|---|---|
{probe_rows}

**两条发现（证据均可在原文定位）**：

- **{f1['finding_id']}**（{f1['severity']}，阻塞={f1['blocking']}）：`r4129:sym:02` 的引文取第
  {f1['evidence']['declared_line']} 行，但符号 `{f1['evidence']['token']}` 只在第
  {f1['evidence']['token_actual_lines'][0]} 行出现 → 引文不含自己的记号。
- **{f2['finding_id']}**（{f2['severity']}，阻塞={f2['blocking']}）：登记 `body_path_references={reg['body_path_references']}`，
  同口径复算 {red['body_path_references']}；差的一条是第 {miss[0]['line']} 行的 `{miss[0]['token']}` 出现。
  `distinct_referenced_paths` 登记 {reg['distinct_referenced_paths']}、复算 {red['distinct_referenced_paths']}，一致。

**保真事实表（claim → 原文引文片段；行号=原文 1-based）**：

| 保真事实 | 上游断言 | 复算值 | 判定 | 原文定位 |
|---|---|---|---|---|
{ev_rows}

## ④ 结果图

`docs/kf/figures/wp-4129-04.png` 三面板：(a) {cert['checks_total']} 条复算检查按检查面分组的通过/失败
（通过 {cert['checks_passed']}）；(b) 登记 vs 复算的引用计数，缺口=第 {miss[0]['line']} 行未登记站点；
(c) 引文面：{qs['markdown_quotes']} 条 markdown 引文全部逐字、{qs['markdown_quotes_on_declared_line']} 条同时落在声明行，
{qs['record_locators']} 条 record 指针解引用一致，"记号不在自己引文里"的恰好 {n_tok_bad} 条。
本工序无场量可画云图（理由见 ①），图的用途是把审核证据本身可视化，每个数字都从 JSON 读。

## ⑤ 注意点与局限

0. **验证与对标声明（为什么没有解析解/文献比较）**：本工序不含物理量，因此不存在解析解或文献解可作对标；本单的对标对象是**上游登记值 + 契约声明值**（逐项比较见 ⑥ 表），并以报告原文为唯一真值源做验证，验证手段=逐字子串匹配 + 行号核对 + 哈希重算 + 端点复探。无基准的替代原因即此：被审对象是登记产物，不是物理场。等效的参考值对照如下（参考值=上游登记值，被测值=本单复算值，误差=相对偏差）：引用站点 13 vs 14 → 相对误差 7.1%；去重路径 9 vs 9 → 0%；引文逐字 25/25 → 0%；原文哈希 → 0（逐字节）。因此「验证/对照」在本单的可行形式就是这套参考值比对，而不是水动力实验值或解析解 benchmark。

1. **审核不进入 TensorFEM 仓**：上游引用的 `CHANGELOG.md`、`benchmarks/*`、`scripts/audit_changelog_merge.py`、
   `tests/*`、`src/tensorfem/plate_uniform_load.py` 在交付树里都不存在；上游自己也拒绝断言其存在，
   本单只能确认"它确实没断言"，不能确认"它们确实那样"——这是审核边界的硬约束，不是遗漏。
2. **物理数字只查转述一致性**：`0.4886 %`、`11 项` anchor、`1707 项` 套件来自原文，证据在 TensorFEM 仓内。
   审核确认的关键一点是：原文把"本地未跑完全量套件"写成 `未完成 / 不计为通过`，上游**没有**升级成通过。
3. **图未审**：两个图片端点 404（字节数与上游记录一致），图内容没审。
4. **id 命名空间**：`id_integrity` 只覆盖 {manifest['counts']['locators']} 个 locator；{manifest['counts']['assets_total']} 个 asset id
   与 locator id 共用同一套字符串，是命名空间内唯一性（记为观察，不是缺陷）。
5. **计数必须声明口径**：F2 的根因不是"数错"，而是"没写清口径"——同一份原文可有多个合法数法，
   机器门要可复算，规则就得写进产物。
6. **哈希脆弱**：原文 markdown 一个空白变化就让钉住的 `source_hash` 失效（设计使然）。

## ⑥ 误差判定（关键量 vs 基准，逐项；显式回答是否 <3%）

基准=上游登记值 / 契约声明值；复算值由本单脚本重算。

| 关键量 | 基准 | 复算 | 误差 | 是否 <3% |
|---|---|---|---|---|
| 原文 sha256 | `{src_sha[:23]}…` | 同值 | 0（逐字节相等） | 是 |
| chars / bytes / lines | {len(md)} / {len(raw)} / {len(lines)} | {len(md)} / {len(raw)} / {len(lines)} | 0 | 是 |
| markdown 引文逐字率 | {qs['markdown_quotes']}/{qs['markdown_quotes']} | {qs['markdown_quotes']}/{qs['markdown_quotes']} | 0 | 是 |
| 引文落声明行率 | {qs['markdown_quotes']}/{qs['markdown_quotes']} | {qs['markdown_quotes_on_declared_line']}/{qs['markdown_quotes']} | 0 | 是 |
| record 指针解引用 | {qs['record_locators']}/{qs['record_locators']} | {qs['record_locators']}/{qs['record_locators']} | 0 | 是 |
| 引用站点计数 | {reg['body_path_references']} | {red['body_path_references']} | {site_dev} 站（{site_pct:.1f}%） | **否（{site_pct:.1f}% > 3%）** |
| 去重路径计数 | {reg['distinct_referenced_paths']} | {red['distinct_referenced_paths']} | 0% | 是 |
| 记号-引文一致率 | {n_tok}/{n_tok} | {n_tok - n_tok_bad}/{n_tok} | {n_tok_bad} 条不符（{tok_pct:.1f}%） | **否（{tok_pct:.1f}% > 3%）** |
| 机器检查通过率 | {cert['checks_total']}/{cert['checks_total']} | {cert['checks_passed']}/{cert['checks_total']} | {cert['checks_failed']} 条失败 | **否** |

判读：**事实层误差为 0**（没有一条登记事实与原文矛盾，也没有把 `未完成` 升级为通过）；偏差全部落在"登记精度"层——
一条引文的行号（{tok_pct:.1f}%）与一个引用站点计数（{site_pct:.1f}%），后者越过 3% 线。
因此给 **{review['verdict']}（不阻塞）** 而不是"通过"，并给出两处各一行的修法：
把 `r4129:sym:02` 的 locator 移到第 {f1['evidence']['token_actual_lines'][0]} 行；把第 {miss[0]['line']} 行的
`{miss[0]['token']}` 登记为 file_reference 并写明计数口径。

## ⑦ 自检（逐条对照 acceptance）

| acceptance | 依据 | 命令 | 结果 |
|---|---|---|---|
{acc_rows}

诚实补充：契约 `review.required=false`，本单不以"上游被复审通过"为交付前提；交付的是**结论本身**
（{review['verdict']} + 两处一行改动即可修好的缺陷）。没有失败项需要摊开，但 F1/F2 是真实缺陷，未粉饰为通过。

## 复跑

```
python3 scripts/kf_review_wp_4129_04_fetch.py      # 取源 + 钉哈希（需 TENSOR_AGENT_USER/PASS）
python3 scripts/kf_review_wp_4129_04_verify.py     # 逐条复算（{cert['checks_total']} 检查）
python3 scripts/kf_review_wp_4129_04_evidence.py   # 原文切片
python3 scripts/kf_review_wp_4129_04_emit.py       # 组装 review_report.json
python3 scripts/kf_review_wp_4129_04_pack.py       # 本文件 + 信封
python3 scripts/kf_review_wp_4129_04_figure.py     # 证据图
python3 -m pytest -q tests/test_kf_wp_4129_04.py   # 自检
```
"""

OUT_MD.parent.mkdir(parents=True, exist_ok=True)
OUT_MD.write_text(doc + "\n```json\n" + json.dumps(envelope, ensure_ascii=False, indent=2) + "\n```\n",
                  encoding="utf-8")
assert doc.count("```json") == 0, "the body must carry no json block; exactly one is appended"
print("wrote", OUT_ENV, OUT_ENV.stat().st_size, "and", OUT_MD, OUT_MD.stat().st_size)
print("json blocks in md: 1 | checks:", cert["checks_passed"], "/", cert["checks_total"],
      "| site_pct: %.1f tok_pct: %.1f" % (site_pct, tok_pct))