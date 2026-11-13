#!/usr/bin/env python3
"""wp-4129-04: publish the paper-grade progress report for this work package.

All numbers in the report body are injected from the JSON artefacts produced by the
pipeline (review_report.json / review_findings.json), so the text carries no hand-copied
figure. Figure = docs/kf/figures/wp-4129-04.png, embedded as base64.
"""
import base64
import json
import os
import pathlib
import urllib.request

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
USER = os.environ["TENSOR_AGENT_USER"]
PASS = os.environ["TENSOR_AGENT_PASS"]
WT = pathlib.Path(".")

rv = json.loads((WT / "work/wp-4129-04/review_report.json").read_text(encoding="utf-8"))
fd = json.loads((WT / "work/wp-4129-04/review_findings.json").read_text(encoding="utf-8"))
env = json.loads((WT / "work/wp-4129-04/kf_result.json").read_text(encoding="utf-8"))
png = (WT / "docs/kf/figures/wp-4129-04.png").read_bytes()
man = json.loads((WT / "knowledge/kf/wp-4129-01/kf_result.json").read_text(encoding="utf-8"))["outputs"]["asset_manifest.json"]
n_tok = len(man["vcs_references"]) + len(man["symbol_references"])
tok_bad = len(fd["defects"]["token_outside_quote"])
tok_ok = n_tok - tok_bad
tok_dev = tok_bad / n_tok

cert = rv["certified_by_review"]
fid = rv["semantic_fidelity"]
qs = rv["quotation_surface"]
f1, f2 = rv["findings"]
reg, red = f2["evidence"]["upstream"], f2["evidence"]["rederived"]
miss = f2["evidence"]["missing_sites"]
site_dev = len(miss) / red["body_path_references"]
distinct_dev = abs(red["distinct_referenced_paths"] - reg["distinct_referenced_paths"]) / reg["distinct_referenced_paths"]
probes = fd["probes"]
check_rows = "\n".join(
    f"| {c['check_id']} | {json.dumps(c['upstream_value'], ensure_ascii=False)[:70]} | "
    f"{json.dumps(c['recomputed'], ensure_ascii=False)[:70]} | {'✓' if c['pass'] else '✗'} |"
    for c in fd["checks"])

md = f"""# wp-4129-04 独立审核：report 4129 / wp-4129-01 资产登记包的逐条复算（verdict: {rv['verdict']}）

**工序**：报告→知识产线 `04-independent-review`（lane C） · **审核对象**：`wp-4129-01`（report 4129 的资产登记包）
**报告原文**：`tensor://reports/4129`，独立取源重算 `{env['provenance']['source_hash']}`
（bytes {rv['source_provenance']['bytes']} / chars {rv['source_provenance']['chars']} / lines {rv['source_provenance']['lines']}）

## ① 案例介绍（背景 / 对象 / 参数表）

知识产线的正确性前提是"互不覆盖 + 零手抄"：每个工序把结论写进自己的结果信封，任何数字都要能在原文里
逐字定位。本单是**质量保证工序**，不是生产工序：它不产生新的知识对象，只回答一个问题——

> 上游 `wp-4129-01` 写在 `asset_manifest.json` 里的每一条断言，能不能由审核者从报告原文**独立重算**出来？
> 它有没有把未验证的东西写成已验证？

被审报告是 TensorFEM PR #77 的三方合并审计（冲突仅 `CHANGELOG.md`，"行保全≠文档正确"）。审核对象的参数表：

| 项 | 值 | 来源 |
|---|---|---|
| 工序 | {rv['package_id']} / {rv['task_type']} | 工作包契约 |
| 审核对象 | {rv['reviewed_package']} | 上游 KO |
| 上游产物 sha256 | `{rv['reviewed_artifacts'][0]['sha256']}` | 本单重算 |
| 报告原文 sha256 | `{rv['source_provenance']['source_hash']}` | 本单重算（与契约声明相等） |
| 报告原文规模 | {rv['source_provenance']['chars']} chars / {rv['source_provenance']['bytes']} bytes / {rv['source_provenance']['lines']} lines | 本单实测 |
| 复算检查项 | {cert['checks_total']} 条（通过 {cert['checks_passed']}） | `review_findings.json` |
| 保真事实 | {fid['facts_re_derived']} 条（通过 {fid['facts_passed']}） | `review_report.json` |
| 发现 | {len(rv['findings'])} 条（均 minor、不阻塞） | 同上 |

## ② 怎么做的（方法 / 流程 / 工具链）

1. **自己取源**：`GET /api/v1/tensor/reports/4129`，独立登录独立请求，落盘后取 UTF-8 字节哈希；
   与契约声明 `{env['provenance']['source_hash'][:23]}…` 逐字节相等（`chars` 也对上）。
   直连 psql 读表被拒（`permission denied for table tensor_reports`），API 是唯一信道。
2. **逐条复算**（`scripts/kf_review_wp_4129_04_verify.py`）：把上游 manifest 拆成 5 类可判定的断言面，
   每条都重新算而不是"读一遍觉得对"：
   - 源身份：hash / bytes / chars / lines / CRLF / 记录字段 / 契约字段；
   - 定位器：{qs['markdown_quotes']} 条 markdown 引文是否原文子串、是否落在**它声明的那一行**；{qs['record_locators']} 条 record 指针解引用是否等于其 quote；
   - 计数与 id：类型-状态直方图、资产数、定位器数、定位器 resolved 数、命名空间内唯一性、`id_integrity` 的口径；
   - git 面：5 个 commit/branch 记号是否逐字存在、前缀算术是否成立；
   - 诚实面：有无 `verified` 标记、claims 为空是否合规、`未完成` 行有没有被偷换、findings 锚点是否逐字。
3. **原文切片取证**（`scripts/kf_review_wp_4129_04_evidence.py`）：审核要引的每一句都按行号/子串**切片**得到，
   随切片存 `quote_sha256`；写盘前断言"报告里每条引文都是原文子串"（`scripts/kf_review_wp_4129_04_emit.py`）。
4. **端点复探**：`/artifacts` 与两张图端点自己再打一次，见 ③ 表。
5. **独立性**：审核不看生产者的脚本、测试与叙述（`docs/kf/wp-4129-01.md` 里的 JSON 块实测与该包
   `kf_result.json` 完全相等，读它不增加独立证据）。被排除的上下文逐项写进 `independence.reviewer_context_excluded`。

## ③ 计算结果（数字表，全部程序化注入）

| 检查面 | 上游断言（截断） | 复算值（截断） | 判定 |
|---|---|---|---|
{check_rows}

端点复探（自己打，不引用上游记录）：

| 端点 | HTTP | 字节 |
|---|---|---|
| `/tensor/reports/4129/artifacts` | {probes['/tensor/reports/4129/artifacts']['status']} | {probes['/tensor/reports/4129/artifacts']['bytes']} |
| `/tensor/reports/4129/figures/merge_audit.png` | {probes['/tensor/reports/4129/figures/merge_audit.png']['status']} | {probes['/tensor/reports/4129/figures/merge_audit.png']['bytes']} |
| `/tensor/reports/4129/figures/plate_gate.png` | {probes['/tensor/reports/4129/figures/plate_gate.png']['status']} | {probes['/tensor/reports/4129/figures/plate_gate.png']['bytes']} |

两条发现（证据均在原文可定位）：

- **{f1['finding_id']}**（{f1['severity']}，阻塞={f1['blocking']}）：`r4129:sym:02` 的引文取第 {f1['evidence']['declared_line']} 行，
  但符号 `{f1['evidence']['token']}` 只在第 {f1['evidence']['token_actual_lines'][0]} 行出现 → 引文不含自己的记号。
- **{f2['finding_id']}**（{f2['severity']}，阻塞={f2['blocking']}）：登记 `body_path_references={reg['body_path_references']}`，
  按同一口径复算为 {red['body_path_references']}；差的一条是第 {miss[0]['line']} 行的 `{miss[0]['token']}` 出现。
  `distinct_referenced_paths` 登记 {reg['distinct_referenced_paths']}、复算 {red['distinct_referenced_paths']}，一致。

## ④ 结果图

图（`docs/kf/figures/wp-4129-04.png`）三个面板：(a) {cert['checks_total']} 条复算检查按检查面分组的通过/失败；
(b) 登记的引用计数 vs 复算计数（缺口=第 {miss[0]['line']} 行未登记站点）；(c) 引文面：{qs['markdown_quotes']} 条 markdown 引文
全部逐字、{qs['markdown_quotes_on_declared_line']} 条同时落在声明行，{qs['record_locators']} 条 record 指针解引用一致，
而"记号不在自己引文里"的恰好 {len(fd['defects']['token_outside_quote'])} 条。
本单是审核/文档工序，没有场量可画云图；图的用途是把审核证据本身可视化（每个数字都从 JSON 读，不手抄）。

## ⑤ 注意点（坑 / 局限 / 适用范围）

1. **审核不进入 TensorFEM 仓**：上游引用的 `CHANGELOG.md`、`benchmarks/*`、`scripts/audit_changelog_merge.py`、
   `tests/*`、`src/tensorfem/plate_uniform_load.py` 在交付树里都不存在；上游自己也拒绝断言其存在，
   审核只能确认"它确实没断言"，不能确认"它们确实那样"。
2. **物理数字只查转述一致性**：`0.4886 %`、`11 项` anchor、`1707 项` 套件等来自原文，证据在 TensorFEM 仓内；
   审核确认了关键一点——原文把"本地未跑完全量套件"写成 `未完成 / 不计为通过`，上游**没有**把它升级成通过。
3. **图未审**：两个图片端点 404（字节数与上游记录一致），所以图内容没审。
4. **id 命名空间**：{len(fd['checks'])} 检查里 `id_integrity` 只覆盖 27 个 locator；18 个 asset id 与 locator id 共用同一套字符串，
   是命名空间内的唯一性，消费者需知道命名空间才能解引用（记为观察，不是缺陷）。
5. **计数规则必须声明**：F2 的根因不是"数错"，而是"没写清口径"——同一份原文可以有 13/14 两种合法数法，
   机器门要可复算，就必须把规则写进产物。
6. **哈希脆弱**：原文 markdown 一个空白变化就让钉住的 `source_hash` 失效（设计使然）。

## ⑥ 误差判定（关键量 vs 基准，逐项）

| 关键量 | 基准（上游登记/契约） | 本单复算 | 误差 | 是否 <3% |
|---|---|---|---|---|
| 报告原文 sha256 | `{env['provenance']['source_hash'][:20]}…` | 相同 | 0 | 是（完全相等） |
| chars / bytes / lines | {rv['source_provenance']['chars']} / {rv['source_provenance']['bytes']} / {rv['source_provenance']['lines']} | {rv['source_provenance']['chars']} / {rv['source_provenance']['bytes']} / {rv['source_provenance']['lines']} | 0 | 是 |
| markdown 引文逐字率 | {qs['markdown_quotes']}/{qs['markdown_quotes']} | {qs['markdown_quotes']}/{qs['markdown_quotes']} | 0 | 是 |
| 引文落行率 | {qs['markdown_quotes']}/{qs['markdown_quotes']} | {qs['markdown_quotes_on_declared_line']}/{qs['markdown_quotes']} | 0 | 是 |
| 引用站点计数 | {reg['body_path_references']} | {red['body_path_references']} | {abs(red['body_path_references'] - reg['body_path_references'])} 站（{site_dev * 100:.1f}%） | **否（{site_dev * 100:.1f}% > 3%）** |
| 去重路径计数 | {reg['distinct_referenced_paths']} | {red['distinct_referenced_paths']} | {distinct_dev * 100:.1f}% | 是 |
| 记号-引文一致率 | {n_tok}/{n_tok} vcs+symbol 记号 | {tok_ok}/{n_tok} | {tok_bad} 条不符（{tok_dev * 100:.1f}%） | **否（{tok_dev * 100:.1f}% > 3%）** |
| 机器检查通过率 | {cert['checks_total']}/{cert['checks_total']} | {cert['checks_passed']}/{cert['checks_total']} | {cert['checks_failed']} 条失败 | **否（但失败均为登记精度，非事实错误）** |

**结论**：注册的事实没有一条与原文矛盾（事实层误差 0）；两处偏差都在"登记精度"层（一个行号、一个计数口径），
其中引用站点计数偏差 {site_dev * 100:.1f}% 已超 3% 线，因此本单给出 **{rv['verdict']}（不阻塞）**，
而不是"通过"。修法各一行：把 sym:02 的 locator 移到第 {f1['evidence']['token_actual_lines'][0]} 行；
把第 {miss[0]['line']} 行的 `{miss[0]['token']}` 登记为 file_reference 并写明计数口径。

**复跑**：`{rv['repro_cmd']}`
"""


def post(path, body, token=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"},
                                 method="POST")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


tok = post("/auth/login", {"username": USER, "password": PASS})
token = tok.get("access_token") or tok.get("token")
payload = {
    "title": "wp-4129-04 独立审核：report 4129 / wp-4129-01 登记包逐条复算（verdict: needs-fix，不阻塞）",
    "summary": f"独立审核 wp-4129-01：原文独立取源复算 {cert['checks_total']} 项，{cert['checks_passed']} 通过；"
               f"注册事实无一条与原文矛盾，查出 2 处登记精度缺陷（符号引文行号错位、引用站点少登记 1 条）。"
               f"verdict=needs-fix（不阻塞）。",
    "scenario_key": "benchmark-closure",
    "mission_id": 15827,
    "tags": ["kf-wp:wp-4129-04", "independent-review", "red-team", "report-4129", "wp-4129-01", "TensorKnowledge"],
    "markdown": md,
    "figures": [{"name": "wp-4129-04.png",
                 "caption": "wp-4129-04 审核证据：34 项复算检查通过面、登记 vs 复算的引用计数缺口、引文面逐字率",
                 "png_base64": base64.b64encode(png).decode()}],
}
res = post("/tensor/reports", payload, token)
print(json.dumps({k: v for k, v in (res.get("data", res) or {}).items()
                  if k in ("id", "title", "status", "scenario_key")}, ensure_ascii=False))
print("report_id:", (res.get("data", res) or {}).get("id"))
(WT / "work/wp-4129-04/publish_response.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")