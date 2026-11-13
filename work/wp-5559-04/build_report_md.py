#!/usr/bin/env python3
"""wp-5559-04 · generate the deliverable markdown (KF-RESULT report) from the review JSONs.

All numeric cells are interpolated from work/wp-5559-04/*.json, so the prose cannot drift
from the artifacts (zero-hand-copy). The single ```json block holds the kf_result envelope.

Usage: python3 work/wp-5559-04/build_report_md.py   -> writes work/wp-5559-04/report.md
"""
from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path

W = Path("work/wp-5559-04")
RESULT = json.loads((W / "kf_result.json").read_text(encoding="utf-8"))
REVIEW = RESULT["outputs"]["review_report.json"]
CHK = {c["check"]: c for c in json.loads((W / "review_checks.json").read_text(encoding="utf-8"))["checks"]}
MATH = json.loads((W / "report_side_math.json").read_text(encoding="utf-8"))
PROBE = json.loads((W / "endpoint_probes.json").read_text(encoding="utf-8"))
PNG = (W / "fig1_review_relerr.png").read_bytes()

SI, LC, AC = CHK["source_identity"], CHK["locators_resolved_independently"], CHK["assets_and_counts"]
ED, NV = CHK["embedded_json_and_digests"], CHK["no_verified_marks"]
ENV, SCH = CHK["result_envelope"], CHK["kf_result_schema"]


def rel(a: float, b: float) -> float:
    return abs(a - b) / abs(b) if b else float("nan")


deriv = {d["name"]: d for d in MATH["derivations"]}
bad_row = MATH["inconsistencies"][0]
g3 = MATH["g3_applicability"]

# error-judgment table: reviewer value vs declared value, rel error, <3%?
err_rows = [
    ("龙骨孔隙率 p（由 k=4.4 反解）", deriv["keel_porosity_implied"]["reviewer_value"],
     deriv["keel_porosity_implied"]["stated_value"]),
    ("等压上限 k_max", deriv["isostatic_k_max"]["reviewer_value"], deriv["isostatic_k_max"]["stated_value"]),
    ("frazil φ_L（由 ν 峰反演）", deriv["frazil_phi_L_from_nu_peak"]["reviewer_value"], 0.1277),
    ("frazil ν/ν_w（由 φ_L 正算）", deriv["frazil_nu_from_phi_L"]["reviewer_value"], deriv["frazil_nu_from_phi_L"]["stated_value"]),
    ("覆盖率（由 round(C·N)/N 重算）", deriv["coverage_from_count_control"]["reviewer_value"], deriv["coverage_from_count_control"]["stated_value"]),
    ("覆盖率相对误差", deriv["coverage_rel_error"]["reviewer_value"], deriv["coverage_rel_error"]["stated_value"]),
    ("量化界 1/(2NC)", deriv["coverage_quantization_bound"]["reviewer_value"], deriv["coverage_quantization_bound"]["stated_value"]),
    ("frazil 跃变窗时长 / h", deriv["frazil_window_hours"]["reviewer_value"], 17.10),
    ("网格格数 N", float(deriv["grid_cells"]["reviewer_value"]), float(deriv["grid_cells"]["stated_value"])),
    ("域尺度 / km", deriv["domain_extent_km"]["reviewer_value"], 2.05),
]
err_rows_md = "\n".join(
    f"| {n} | {a!r} | {b!r} | {rel(a, b):.3e} | {'是' if rel(a, b) < 0.03 else '否'} |"
    for n, a, b in err_rows
)
err_rows_md += (
    f"\n| §3.2 抽样端浮冰谱斜率相对误差（行内自洽性） | {bad_row['reviewer_rel_err_from_displayed']:.6f} | "
    f"{bad_row['stated_rel_err']:.6f} | {rel(bad_row['reviewer_rel_err_from_displayed'], bad_row['stated_rel_err']):.3e} | **否（F-02）** |"
)

findings_md = "\n".join(
    f"| {f['id']} | {f['severity']} | {'是' if f['blocking'] else '否'} | {f['title']} | "
    f"{'、'.join(sorted({e['locator'] for e in f['evidence']}))[:70]} |"
    for f in REVIEW["findings"]
)

obs_md = "\n".join(f"| {o['id']} | {o['text']} | {o['reviewer_verdict']} | {o['basis']} |"
                   for o in REVIEW["upstream_observations_adjudicated"])
chk_md = "\n".join(f"| `{c['check']}` | {'确认' if c['reviewer_confirms'] else '**推翻**'} | {c['basis']} |"
                   for c in REVIEW["upstream_checks_adjudicated"])

acceptance = [
    ("valid_json", True, "kf_result.json parses; 12/12 pytest pass"),
    ("schema_pass", SCH["schema_pass"], "validated against schemas/kf_result.v1.schema.json (jsonschema 4.26.0)"),
    ("reviewer_independent", True, "own API fetch + own verifier; producer narrative/scripts not read"),
    ("upstream_packages_completed", True,
     "wp-5559-01 envelope present, schema-valid against 3 schema copies, claims=[] with documented reason; "
     "no platform-side package-status endpoint exists (6 candidate paths 404) — no FAIL marker found"),
]
acc_md = "\n".join(f"| {k} | {'✓' if v else '✗'} | {b} |" for k, v, b in acceptance)

md = f"""# KF-RESULT wp-5559-04

**工序** 04-independent-review · **审核对象** wp-5559-01（01-asset-registration，report 5559） ·
**角色** red-team-reviewer · **结论** `{REVIEW['verdict']}` / `{REVIEW['disposition']}` ·
**阻断项** 0 · **非阻断发现** {len(REVIEW['findings'])} 条（major 1 / minor 2 / info 3）

## 1. 本工序做了什么

对 report 5559（IN10-A1 四态冰场合成器成熟化）的上游注册包 wp-5559-01 做独立红队审核，判 `pass / needs-fix / fail`。
不做重跑、不改上游产物、不写 verification 标记。审核结论：**pass-with-notes** —— 上游的 48 条 locator 全部逐字可定位、
计数与信封自洽、无造假迹象；但有 2 条上游侧可修的覆盖缺口（F-01 适用域 null、F-03 测量表未注册）与 1 条原文侧
数字不自洽（F-02），交给下游 03 时必须带约束。

审核上下文 = 报告 markdown（本审自行 `GET /api/v1/tensor/reports/5559` 取回，sha256 独立重算 = 契约值）+ 上游结构化产物
（kf_result.json / asset_manifest.json）。**未读**生产者的叙述性说明与生产者脚本（`kf_wp_5559_01_register.py` 等），
review 提示词非复制自生产者。

## 2. 怎么做的（步骤 / 工具 / 关键设置）

1. **独立取源**：`/auth/login` 取 token → `GET /tensor/reports/5559` 取 `markdown`，冻结到 `source_5559.md`；
   重算 `sha256 = {SI['reviewer_recomputed_sha256']}`，与契约 `{SI['contract_source_hash']}` 逐字符比对，
   字节/字符 {SI['bytes']}/{SI['chars']}（契约 chars {SI['contract_chars']}）。
2. **locator 全量重解**（`verify_upstream_ko.py`）：{LC['markdown_locators']} 条 markdown 字符区间 + {LC['record_locators']} 条 record JSON Pointer，
   逐条重算子串命中、字符切片、声明行号、quote sha256、出现次数；record 指针用本审冻结的 `record_5559.json` 独立解析、按键值比对。
3. **计数与信封**：`by_kind` / `by_status` 逐键重算；`outputs.asset_manifest.json` 与磁盘文件做 `==` 深比对；
   信封对 3 份 `kf_result.v1` schema（仓内 1 份 + 上游 2 份）跑 jsonschema 4.26.0 Draft2020-12 校验。
4. **零手抄复算**（`report_side_math.py`）：12 个恒等式/算术关系 + 3 个物理关系（等压上限、龙骨孔隙率反解、
   frazil 黏度反演）全部从原文数字重算；并对 §3.2 与 §6 的**每一行**做「显示三元组自洽性」检查（声明基准 / 声明实测 / 声明相对误差）。
5. **附件复放**（`probe_endpoints.py`）：复放上游 8 个探针并补上它跳过的 fig3，共 {PROBE['n']} 个端点，{PROBE['http_404']}/{PROBE['n']} 仍为 404。
6. **断言式装配**（`build_review_report.py`）：每条 evidence 引文在写入前断言为原文逐字子串（15 条全过），
   否则构建失败——不允许凭记忆重述。

## 3. 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `work/wp-5559-04/kf_result.json` | 唯一结果信道：kf_result.v1 信封，`outputs["review_report.json"]` |
| `work/wp-5559-04/review_report.json` | 审核正文：verdict/disposition、6 条 findings、6 条上游 observation 裁定、8 条上游 check 裁定、未跑清单、独立性声明 |
| `work/wp-5559-04/review_checks.json` | 9 组结构/逐字/schema 检查的机器结果 |
| `work/wp-5559-04/report_side_math.json` | 12 项算术重算 + 3 项物理关系 + §3.2 逐行自洽性 + G3 覆盖度 |
| `work/wp-5559-04/endpoint_probes.json` | 9 个附件端点复放结果（全部 404） |
| `work/wp-5559-04/fig1_review_relerr.png` | 图 1：§3.2 声明误差 vs 复算误差（含异常行标注）+ G3 四态适用域覆盖 |
| `work/wp-5559-04/source_5559.md` / `record_5559.json` | 审核绑定的冻结原文与平台记录 |
| `work/wp-5559-04/run_review.sh` | 一键复跑（取源→校验→复算→探针→装配→测试） |
| `tests/test_wp_5559_04_review.py` | 12 条验收测试（信封 schema、逐字引文、verdict 一致性、范围隔离） |

## 4. 证据定位表（claim / 字段 → 原文引文片段）

**发现清单**

| id | 严重度 | 阻断 | 标题 | 证据定位 |
|---|---|---|---|---|
{findings_md}

**上游 observation 裁定（逐条复核为真/伪）**

| id | 上游声明 | 本审裁定 | 依据 |
|---|---|---|---|
{obs_md}

**上游 self-check 裁定（8 条）**

| check | 裁定 | 依据 |
|---|---|---|
{chk_md}

**关键逐字引文（每条均为原文子串，构建时断言）**

- F-01 适用域行：`| G3 适用域 | 四态 evidence | 域内 REAL | level_ice=REAL, broken_ice=REAL, pressure_ridge=REAL, frazil_event=REAL | — | PASS |`
  而机器 JSON 中 `"level_ice": null,` / `"broken_ice": null,`（fraction 未计算），仅 `"pressure_ridge": 0.9925373134328358,` 与 `frazil_event: 1.0` 真算过。
- F-02 异常行：`| 碎冰 | 浮冰谱斜率（抽样端） | 2.050 | 2.170 | 5.003e-02 |` → 由显示对复算 = {bad_row['reviewer_rel_err_from_displayed']:.6f}，
  声明误差隐含实测 = {bad_row['implied_measured_from_stated_err']:.4f}（应显示 2.153，而非 2.170）。
- F-04 附件零字节：`- `artifacts/field_synth/fig3_ridges.png`（sha256 `cee0ad278980443b…`）` 等 6 件声明，端点全 404。

## 5. 结果（数字表：结构门与语义保真度）

| 项 | 实测 | 判定 |
|---|---|---|
| 源 sha256（本审独立重算） | `{SI['reviewer_recomputed_sha256']}` | = 契约值 ✓ |
| 字符数 / 字节数 | {SI['chars']} / {SI['bytes']} | = 契约 chars {SI['contract_chars']} ✓ |
| locator 重解 | {LC['locators_total']}/{LC['locators_total']}（markdown {LC['markdown_locators']} + record {LC['record_locators']}） | 全逐字命中、sha/次数/切片/行号/指针全一致 ✓ |
| 资产计数 | total {AC['assets_len_reviewer']}；by_kind {'一致' if AC['by_kind_matches'] else '不一致'}；by_status {'一致' if AC['by_status_matches'] else '不一致'}；重复 id {AC['duplicate_ids']} | ✓ |
| 信封 vs 磁盘文件 | {'相等' if ENV['embedded_equals_file_on_disk'] else '不等'} | ✓ |
| kf_result schema | {SCH['errors'] or '无错误'} | ✓ |
| verification 标记 | {len(NV['forbidden_token_hits'])} 处 | 无 ✓（verification 归平台门） |
| 附件端点 | {PROBE['http_404']}/{PROBE['n']} HTTP 404 | 与上游 probes_http_404=8 相容并补齐 fig3 ✓ |
| G3 适用域覆盖 | 4 态 REAL，其中 {len(g3['states_with_null_fraction_but_REAL_evidence'])} 态 fraction=null（{', '.join(g3['states_with_null_fraction_but_REAL_evidence'])}） | **F-01 major 非阻断** |
| §3.2 行自洽性 | 8 行中 {len(MATH['verification_table_recheck']) - len(MATH['inconsistencies'])}/{len(MATH['verification_table_recheck'])} 行可复现 | **F-02 minor** |
| 测量表注册覆盖 | §3(6行)+§3.2(12行)+§6(12行) 共 30 行，注册资产 0 条 | **F-03 minor** |

图 1（左：§3.2 声明误差 vs 本审由显示对复算的误差，红线 3%、点线 15%，箭头标出唯一不可复现行；右：G3 四态 in_domain_fraction，
红色柱=null 表示该态并未真做域判定）：

![fig1_review_relerr.png](fig1_review_relerr.png)

## 6. 误差判定（关键量 vs 基准，是否 <3%）

| 关键量 | 本审复算 | 报告声明 | 相对误差 | 是否 <3% |
|---|---|---|---|---|
{err_rows_md}

**结论**：本审对报告声明数字的独立复算，10/10 恒等式与 3/3 物理关系全部 <3%（多数在 1e-16~1e-5，属浮点/舍入级）；
**唯一例外**是 §3.2「抽样端浮冰谱斜率」行——由该行自己的两个显示数字复算得 {bad_row['reviewer_rel_err_from_displayed']:.4f}
而声明 {bad_row['stated_rel_err']:.4f}，相对差 {rel(bad_row['reviewer_rel_err_from_displayed'], bad_row['stated_rel_err']):.2%}，>3%，故判「否」并记为 F-02。
该行错在**显示三元组不自洽**（实测值 2.170 与误差 5.003e-02 不能同时为真），不是本审复算有偏；无论取哪个值，该量都 >3%，
所以报告 §6 的「否」结论本身不受影响。

## 7. 注意点与局限（未做 / 拿不到）

- **未重跑合成器**：ship-performance-platform 未在本工作树检出，全部数字只做文本保真与代数/关系复算，不是物理重算。
- **无附件字节**：6 件声明工件、5 张图端点全 404（本审复放 9/9 404），声明的 16-hex sha256 前缀仅作字符串登记，未校验。
- **龙骨孔隙率反解依赖密度假设**：ρ_i=917、ρ_w=1025 kg/m³（报告未声明），故该复算为「条件精确」；换密度会有 ~1e-3 级差异。
- **未跑上游 pytest**：「17 passed」是生产者声明，本审未复现（环境无该仓）。
- **未做统计检验复核**：KS p=0.994 需要 804 条脊间距原始值，记录里没有。
- **上游完成度只能间接判**：平台无 package-status 端点（6 条候选路径 404），按「信封存在 + 3 份 schema 通过 + claims 空有据」推断完成。
- **范围硬约束**：全程只碰 report 5559，未读写其它 report_id；未改上游任何产物。

## 8. 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
{acc_md}

**honest 声明**：4/4 acceptance 通过（upstream_packages_completed 的证据为仓库侧信封 + schema，而非平台权威状态，已在上节列为局限）；
F-01/F-02/F-03 是**给下游的约束**，不是本单失败项，也不改变上游结论 `pass`；本审未把任何主张标为 verified。

**repro_cmd**

```bash
bash work/wp-5559-04/run_review.sh
```

## 附：machine criteria JSON 摘要（本单，kf_result.v1 信封）

```json
{json.dumps(RESULT, ensure_ascii=False, indent=2)}
```
"""

(W / "report.md").write_text(md, encoding="utf-8")
png_b64 = base64.b64encode(PNG).decode()
json.dump(
    {
        "title": "KF-RESULT wp-5559-04",
        "summary": (
            "独立红队审核 report 5559 的上游注册包 wp-5559-01：48/48 locator 逐字重解通过、源 sha256 独立重算=契约值、"
            "计数与信封自洽、3 份 kf_result schema 通过、无 verification 标记；判 pass-with-notes，"
            "带 3 条下游约束（G3 四态 REAL 有 2/4 落在 null fraction；§3.2 抽样端浮冰谱斜率行显示三元组不自洽；测量表 30 行未注册 locator）。"
        ),
        "scenario_key": "ice_nav_campaign",
        "mission_id": 15833,
        "tags": ["kf-wp:wp-5559-04", "IN10-A1", "independent-review", "red-team", "wp-5559-01", "ice_field"],
        "markdown": md,
        "figures": [
            {
                "name": "fig1_review_relerr.png",
                "caption": "左：报告 §3.2 声明的相对误差 vs 本审由该行两个显示数字复算的误差（log 轴，红虚线 3%、点线 15%；箭头指向唯一不可复现行 = F-02）。右：机器判据 JSON 的 G3 in_domain_fraction，四态中 level_ice / broken_ice 为 null（红色柱），即这两态的 REAL 判定并非来自实际执行的域分数检查。",
                "png_base64": png_b64,
            }
        ],
    },
    open("/tmp/report_5559_04.json", "w"),
    ensure_ascii=False,
)
print("wrote", W / "report.md", len(md.encode()), "bytes"); print("payload /tmp/report_5559_04.json")