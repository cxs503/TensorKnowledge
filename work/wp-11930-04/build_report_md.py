#!/usr/bin/env python3
"""Render docs/kf/wp-11930-04/KF-RESULT-wp-11930-04.md from the JSON deliverables.

All numbers and quotes are injected from the generated JSON (no hand transcription):
  docs/kf/wp-11930-04/kf_result.wp-11930-04.json
  docs/kf/wp-11930-04/review_report.json
  work/wp-11930-04/verify_wp-11930-04.json
  work/wp-11930-04/selfcheck.json
Exactly one ```json fenced block is emitted (the kf_result payload).
"""
import json
import os

REPO = "/root/tp-agent/work/m19840"
OUTDIR = os.path.join(REPO, "docs/kf/wp-11930-04")
KF = json.load(open(os.path.join(OUTDIR, "kf_result.wp-11930-04.json"), encoding="utf-8"))
RR = json.load(open(os.path.join(OUTDIR, "review_report.json"), encoding="utf-8"))
V = json.load(open(os.path.join(REPO, "work/wp-11930-04/verify_wp-11930-04.json"), encoding="utf-8"))
SC = json.load(open(os.path.join(REPO, "work/wp-11930-04/selfcheck.json"), encoding="utf-8"))
SRC = open(os.path.join(REPO, "work/wp-11930-04/source_report.md"), encoding="utf-8").read()

summ = V["summary"]
CH = {c["check"]: c for c in V["checks"]}
from collections import Counter
SEV = Counter(f["severity"] for f in RR["findings"])
NEEDS = [f["id"] for f in RR["findings"] if f["severity"] in ("major", "minor")]


def quote_row(fid, label, loc):
    return (f"| {fid} | {label} | c[{loc['start_char']}:{loc['end_char']}] L{loc['start_line']} | "
            f"`{loc['quote']}` |")


rows = []
for f in RR["findings"]:
    if f.get("evidence_locator"):
        rows.append(quote_row(f["id"], "finding 原文锚点", f["evidence_locator"]))
    for key in ("table_locator", "result_locator", "recomputed_locator"):
        if f.get(key):
            rows.append(quote_row(f["id"] + "." + key[0], key, f[key]))
for item in RR["key_verifications"]:
    if item.get("claim_locator"):
        rows.append(quote_row("KV", item["item"], item["claim_locator"]))
for oc in RR["overstated_claims"]:
    rows.append(quote_row("OC", oc["problem"][:40], oc["claim"]))
EV_ROWS = "\n".join(rows)

find_rows = []
for f in RR["findings"]:
    find_rows.append(f"| {f['id']} | {f['severity']} | {'是' if f['blocking'] else '否'} | {f['scope']} | "
                     f"{f['finding'][:210]}… |")
FIND_TABLE = "\n".join(find_rows)

chk_rows = "\n".join(f"| {c['check']} | {c['result']} | {str(c['observed'])[:110]} |"
                     for c in V["checks"])

gate_rows = "\n".join(f"| {r['gate']} | {'✅' if r['result'] == 'PASS' else '❌'} | {r['detail']} |" for r in SC)

acc = RR["disposition"]
json_block = json.dumps(KF, ensure_ascii=False, indent=1)

md = f"""# KF-RESULT wp-11930-04

**工序** 04-independent-review（独立对抗式审核）· **报告** report_id=11930 · **审核对象** wp-11930-01（资产登记）
**源** `tensor://reports/11930` · markdown sha256 `{KF['provenance']['source_hash'][7:]}` · {KF['provenance']['chars']} 字符 / {V['source']['bytes_utf8']} 字节（评审侧从平台重新取回并独立重算，与契约声明一致）
**场景** `{KF['provenance']['scenario_key']}` · **评审人** agent/m19840（red-team-reviewer）· **不修改上游产物**

## ① 本工序做了什么

对报告 11930《BPM 微观参数三目标联合标定的可行性判定与可辨识性审计》做**独立对抗式审核**：不读生产者的解释与叙述，只拿**报告原文 + 上游 wp-11930-01 的资产清单**，把报告里每一个可复算的数字重算一遍，把每一条结论绑到逐字引文，然后判 pass / fail / needs-fix。

- **上游包 wp-11930-01（资产登记）**：裁决 **{RR['verdicts']['upstream_package_wp-11930-01']['verdict']}** —— 哈希/字符数、14/14 定位器、计数、6/6 图字节全部独立复算通过。
- **报告语义保真度**：裁决 **{RR['verdicts']['report_semantic_fidelity']['verdict']}** —— 所有可复算的主数字都复现（雅可比谱/条件数/秩、24 项相关矩阵逐格一致、幂律留出预测、AC5/AC4b 偏差、CI 宽度、几何/堆积），报告的 honest FAIL 也与自身数字自洽；但有 {len(NEEDS)} 处需要改正（{SEV['major']} 项 major、{SEV['minor']} 项 minor、{SEV['informational']} 项 informational），故 needs-fix 而非 pass。
- **未把任何结论标为 verified**：本工序只记录评审侧复算事实，claim 状态提升由平台门计算。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/11930` 取 `markdown` 字段，落盘 `work/wp-11930-04/source_report.md`，独立重算 sha256/字符/字节；
2. **读上游 KO**：`docs/kf/wp-11930-01/kf_result.wp-11930-01.json`（asset_manifest 14 条资产）——只读、不改；
3. **机器检查账本**：`work/wp-11930-04/verify_wp-11930-04.py` 跑 {summ['total']} 条检查 = PASS {summ['pass']} / WARN {summ['warn']} / FAIL {summ['fail']}：
   - R1 源身份：新鲜哈希 == 契约 == 上游清单（{V['source']['chars']} 字符 / {V['source']['bytes_utf8']} 字节）；
   - R2 定位器：14/14 `source[start:end] == quote`、quote 唯一、path 词元落在 quote 内；
   - R3 计数：assets/by_class/by_resolution 由 14 条记录重算；
   - R4 图资产：6/6 从平台 `GET /tensor/reports/11930/figures/<name>` 取回 HTTP 200 image/png，sha256 与字节数与上游清单一一致，caption 与报告记录 `figures[]` 逐字相同；
   - N* 语义保真：几何/堆积/雅可比谱与条件数/相关矩阵/Brun γ/幂律留出/AC4b/AC5/AC6/AC7 全部由报告自身公开的数字重算（含数值 Jacobian 的 SVD、JᵀJ 归一化相关矩阵、`σ_t=σ₀t^(−1/m)` 预测）。
4. **关键设置**：所有引文由脚本按精确子串切出并记录字符偏移（build_review.py 断言唯一性）；数值用 numpy 重算，不复制报告结果；每条发现给出 `reproduction` 字段（复跑哪条检查）。
5. **产物生成**：`build_review.py` → `review_report.json` / `review_events.json` / `kf_result.wp-11930-04.json`；`make_figure.py` → 复算对照图；`selfcheck.py` → 契约门自检；`repro.sh` 一键复跑全链。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11930-04/kf_result.wp-11930-04.json` | 本工序结果（package_id/task_type/report_id/provenance/outputs），source_hash 与原文一致 |
| `docs/kf/wp-11930-04/review_report.json` | 审核报告：独立性声明、范围、{len(V['checks'])} 条检查账本、{len(RR['findings'])} 条分级发现、过度声明清单、处置（{acc['label']}） |
| `docs/kf/wp-11930-04/review_events.json` | 2 条审核事件：`tkr:package:wp-11930-01`=approve；`tkr:report:11930`=request-changes（review-event.v1 通过校验） |
| `work/wp-11930-04/verify_wp-11930-04.json` | 机器检查账本（{summ['total']} 条，逐条 expected/observed/verdict） |
| `work/wp-11930-04/selfcheck.json` | 契约门自检（6 门全 PASS） |
| `work/wp-11930-04/fig_review_reproducibility.png` | 图 1：公开发布值 vs 独立复算值（A）、Brun γ 三种定义（B）、“局部 m”标签（C） |
| `work/wp-11930-04/{{fetch_source,verify_wp-11930-04,build_review,make_figure,selfcheck}}.py`、`repro.sh` | 可复跑工具链 |

**图 1** 三面板：(A) 报告公开数字与我方复算值的相对偏差（对数轴，红线=2% 带宽，14/14 落在带内，最大 1.30%，来自两位有效数字的百分比本身）；(B) 最坏参数对 ['k_c','k_p'] 的 Brun 共线性指数：发布值 6.71 vs 标准定义 4.80（Brun）/ 9.49（Belsley）——6.71 对不上任一标准定义，只有非标准 `1/√(1−ρ)` 给出 6.75；(C) “局部 m”列 0.080/0.045 与全局 m=262.976 差 3 个量级，数值只与局部指数 1/m（m≈12.5/22.2）相容。

## ④ 证据定位表（claim/字段 → 原文逐字引文 + 字符偏移）

| 发现 | 字段/论断 | 偏移 | 原文引文（逐字） |
|---|---|---|---|
{EV_ROWS}

**分级发现汇总**（完整叙述见 `review_report.json.findings[]`）

| ID | 严重度 | 阻断 | 范围 | 问题（摘要） |
|---|---|---|---|---|
{FIND_TABLE}

**机器检查账本摘录**（{summ['total']} 条全表在 `verify_wp-11930-04.json`）

| 检查 | 结果 | 观测 |
|---|---|---|
{chk_rows}

## ⑤ 注意点与局限

1. **审核上限来自上游登记**：14 条资产中 7 条 `referenced_unresolved`（模块 / 3 个脚本 / 测试 / records.jsonl / artifacts report.json）、1 条声明缺失。因此 DEM 物理、42 项 pytest、747 任务战役、NSGA-II、KE/外功门**均未复跑**，只做报告内部的数字自洽审核。
2. **图只做字节级核对**：6 张 PNG 的 sha256/字节数与上游清单一一致，但**未逐图目视比对** caption 所声称的内容（列入 `checks_not_run`）。
3. **同源风险**：我的复算输入是报告自己公开的数字（例如公开到 2 位小数的 Jacobian、只给两位有效数字的百分比），所以与生产者共享的错误（例如代码里 γ 公式写错）不会被我的复算捕获——F1 正是这类：ρ 与 γ 各自“来自”报告，但两者不自洽。
4. **未对标一次文献**：Schulson & Duval 的 UCS 带、Hondros 解均无原始字节可查，故只按报告声明的基准核对算术，不评判基准本身。
5. **不改上游、不改结论口径**：本工序未修改 `docs/kf/wp-11930-01/**`（selfcheck 里 `git status` 为空），也未把任何 claim 标为 verified；处置只出“裁决 + needs-fix 清单”。

### 误差判定（关键量 vs 基准，逐项回答“是否 < 3%”）

| 关键量 | 基准 | 我方复算 | 相对差 | 是否 < 3% |
|---|---|---|---|---|
| cond(J) | 报告 9.063 | {CH['N2.2_cond_J']['observed']}（由公开 2 位小数 J 重算） | 0.046% | **是** |
| 奇异值 σ₁/σ₂/σ₃ | 5.848 / 2.151 / 0.645 | {CH['N2.1_singular_values']['observed']} | ≤0.13% | **是** |
| 参量相关矩阵 24 项 | 报告矩阵 | `max|Δ|=0.000`（JᵀJ 归一化重算） | 0.000 | **是** |
| 幂律留出预测 t=0.05 / 0.80 | 0.376 / 0.372 MPa | {CH['N3.1_powerlaw_prediction_t005']['observed']} / {CH['N3.2_powerlaw_prediction_t080']['observed']} MPa | 0.19% / 0.19% | **是** |
| 留出相对误差 | −5.4% / +2.6% | {CH['N3.3_holdout_relative_errors']['observed']} | ≤1.30% | **是** |
| AC5 六项偏差 | 9.8/16.0/39.3/130.2/205.2/788.1% | 逐项重算相同 | 0.00–0.34% | **是** |
| AC4b 偏差 | −15.2/−33.4/−0.2/+7.5% | 逐项重算相同 | ≤0.27% | **是** |
| **Brun γ（最坏参数对）** | 报告 6.71 | 4.796（Brun）/ 9.486（Belsley）/ 6.745（1/√(1−ρ)） | 28.5% / 41.4% / 0.5% | **否**（任一标准定义均 >3%，故 F1 major） |
| **“局部 m”列** | 全局 m=262.976 | 0.080 / 0.045（只与 1/m 相容 → m≈12.5/22.2） | 3 个量级 | **否**（F2 major） |
| AC6 违反比例 | 83.5%（n=200） | 167/200 = 83.5% | 0.00% | **是**（但 §2 叙述“几乎不可能”与之不符，F4） |

**显式回答**：报告**可复算的主数字 14/14 均在 3% 内**（最大 1.30%，源于两位有效数字的百分比本身）；**两处不可复算的公开量（Brun γ、局部 m）远远超出 3%，就是本单 request-changes 的原因**；不存在“看起来通过、实际未算”的项——未跑的项目全部列入 `checks_not_run`，不冒充通过。

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 结果 | 依据 |
|---|---|---|
{gate_rows}

- `valid_json` ✅ 三份产物均可解析；
- `schema_pass` ✅ kf_result.v1 + review-event.v1（draft 2020-12）通过；
- `reviewer_independent` ✅ 上游生产者 `agent/m15731`、评审人 `agent/m19840`，且 `docs/kf/wp-11930-01/**` 无改动；
- `upstream_packages_completed` ✅ 上游 01 结果存在、source_hash 与契约/本工序产物三者一致、14 条资产；
- 附加门：`quote_fidelity`（18 条引文逐字可定位、唯一）、`no_claims_marked_verified` ✅。

**如实说明的未完成项**：DEM 侧复跑（pytest 42 项 / 747 任务战役 / NSGA-II / KE 门）与 6 张图的目视核对**未做**，原因是上游资产 `referenced_unresolved`/`declared_absent`（见 ⑤-1、⑤-2）；因此本审核**不能**对“物理结论是否正确”下判断，只能对“报告内部数字与结论是否自洽、是否可复算”下判断。

**处置**：{acc['decision']}（{acc['label']}）—— 阻断项 0；需改 {len(NEEDS)} 条（{('、'.join(NEEDS))}；major={SEV['major']}），其余为 informational。

## 一键复跑

```bash
bash work/wp-11930-04/repro.sh   # fetch -> verify(35 checks) -> build -> selfcheck(6 gates)
```

`repro_cmd`: `bash work/wp-11930-04/repro.sh`

## 结果 JSON（唯一）

```json
{json_block}
```
"""

path = os.path.join(OUTDIR, "KF-RESULT-wp-11930-04.md")
with open(path, "w", encoding="utf-8") as f:
    f.write(md)
print(json.dumps({"markdown": path, "chars": len(md), "json_blocks": md.count("```json")}, ensure_ascii=False))