# KF-RESULT wp-11478-01

report_id **11478** · package `wp-11478-01` · task_type `01-asset-registration` · lane C · status `draft`
源：`tensor://reports/11478` 字段 `markdown`，
sha256 `b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258`（= 契约 source_hash，字符 4710 / UTF-8 字节 8163）。
投产版本说明：本文件为最终版，取代同题早期版本（平台 report 14834）——那一版把主产物路径写成 `artifacts/wp-11478-01/`，而本仓 `.gitignore` 整目录忽略 `artifacts/`（见 ⑤.6），产物会被推送门禁丢弃；本版已把全部交付物迁至受跟踪的 `docs/wp-11478-01/` 并加测试守护。

本工序**只登记资产、不做抽取**（objective: register_assets=true, classify_report_type=false），claims 允许为空数组——本单给了 4 条且全部带显式状态，无一标 verified。

## ① 本工序做了什么

把报告 11478 的 markdown 当作唯一事实面，逐条登记它引用到的 **21 个资产**（代码模块、脚本、工件、图件、表格、数值锚点、上游提交/变更、门禁正则、局限集、工具链），每个资产给出：类别、所在章节、**字节级 locator（char 区间 + 行号 + 引文原文）**、解析状态、以及**机器校验记录**（`resolution_check`：实际跑了什么检查、结果如何）。不做数值抽取、不复算上游数字、不把任何结论标 verified。

解析状态分布（机器重数，与本文件 ④ 表一致）：
| resolution | 数量 |
|---|---|
| declared_absent | 1 |
| referenced_unresolved | 8 |
| resolved_in_platform_record | 1 |
| resolved_in_source | 11 |

资产类别分布：
| asset_class | 数量 |
|---|---|
| acceptance_criterion | 1 |
| artifact | 1 |
| code_module | 2 |
| figure | 1 |
| figure_declaration | 1 |
| figure_product | 1 |
| limitation_set | 1 |
| numeric_anchor | 2 |
| numeric_series | 1 |
| parameter_table | 1 |
| pipeline_gate_pattern | 1 |
| provenance_discipline | 1 |
| script | 1 |
| table | 2 |
| test_module | 1 |
| toolchain | 1 |
| upstream_change_reference | 1 |
| vcs_commit | 1 |

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文并先验哈希**：`scripts/kf_fetch_11478.py` 用 `TENSOR_AGENT_USER` 登录平台，`GET /tensor/reports/11478` 取 `markdown`，落 `runs/wp-11478-01/report_11478.md` + 原始 payload。实测 sha256 = `b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258`，与契约 `source_hash` **逐位相同**（否则脚本 exit 2，不写任何产物）。
2. **locator 设计成可判定谓词**：不做「大概在第几行」的模糊引用，而是取原文的**字面子串**，要求 `md.count(quote) == 1`，char/line 偏移全部由 `md.index(quote)` 反算。于是「locator 可解析」= 可执行断言，而非声明。
3. **每个资产带一个真跑的检查**（不是声明式 resolution）：`worktree_path_exists`（外部路径逐条 stat）、`git_cat_file`（提交对象是否在本仓对象库）、`platform_figures_field`（平台 figures 字段计数）、`char_span_in_source_markdown`（span 往返比对）。
4. **claims 只写原文能支撑的部分**：4 条 claim 中，原文自身可证的入 `supported`/`partially-supported`，需外部件才能证的入 `unresolved` 并附 `unresolved_reason`；`verified` 字段一律不置 true（verification 归平台门）。
5. **自校验脚本独立复算**：`scripts/kf_verify_11478.py` **重新从 API 取一次 markdown**（不读本地缓存），逐条重算 6 项 acceptance + 2 项一致性，输出 `runs/wp-11478-01/verify_11478.json`。
6. **负控测试**：`tests/test_kf_wp11478.py` 对每个检查都喂**篡改副本**（改引文、移 span、重复 id、伪 resolution、自标 verified），证明检查会红而不是只会绿。

工具链：Python 3.11 + stdlib + jsonschema 4.26.0 + matplotlib（仅作图）+ pytest；重活无需集群（全流程 <1 s，纯文本处理）。

**结果图**（`scripts/kf_figure_11478.py` 程序化生成，数字全部来自 manifest，无手抄）：`docs/wp-11478-01/asset_span_map.png` 三面板——A 把 21 个资产 locator 画在报告字符轴上（按 resolution 着色，登记区间覆盖 3180/4710 字符 = 67.5%），B 按 resolution 重数，C 按章节 ①-⑥ 计数；对应平台 figures[0]。

**一键复跑**（工作树根执行，产物全部落 worktree 内）：
```bash
python3 scripts/kf_fetch_11478.py && python3 scripts/kf_claims_11478.py \
  && python3 scripts/kf_register_11478.py && python3 scripts/kf_verify_11478.py \
  && python3 scripts/kf_result_11478.py && python3 -m pytest -q tests/test_kf_wp11478.py
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `runs/wp-11478-01/report_11478.md` | 平台 markdown 原样落盘（8163 B），所有 locator 的基准 |
| `runs/wp-11478-01/report_11478.json` | 平台记录原 payload（含 figures/tags/title） |
| `runs/wp-11478-01/fetch_11478.json` | 取数元数据：端点、字段、chars/bytes、sha256、与契约比对结果 `True` |
| `runs/wp-11478-01/claims_11478.json` | 4 条 claim 全量版（含 char span locator） |
| `docs/wp-11478-01/asset_manifest.json` | **主产物**：21 资产 + 检查记录 + 计数 + integrity |
| `runs/wp-11478-01/register_11478.json` | 构建日志：每资产 resolution / check / check_result / span |
| `runs/wp-11478-01/verify_11478.json` | 独立复算的 8 项检查明细与 verdict = `pass` |
| `docs/wp-11478-01/kf_result.wp-11478-01.json` | kf_result.v1 信封（本报告 ⑦ 的 json 块与之逐字节同源） |
| `docs/wp-11478-01/KF-RESULT-wp-11478-01.md` | 本文件（论文级六段 + 自检） |
| `docs/wp-11478-01/asset_span_map.png` | 结果图（三面板，见 ② 末段），95718 B |
| `runs/wp-11478-01/figure_metrics_11478.json` | 作图用到的派生量：覆盖字符数/覆盖率/分节计数 |
| `schemas/asset_manifest.v2.schema.json` | 报告无关的 01 工序 schema（v1 用 const 钉死 wp-448-01，无法复用） |
| `scripts/kf_{fetch,claims,register,verify,result}_11478.py` | 全链路脚本，均为幂等（同输入 → 同输出，时间戳除外） |
| `tests/test_kf_wp11478.py` | 正向断言 + 负控（篡改必红） |

## ④ 证据定位表（claim / 资产 → 原文引文片段，chars 为 0-based 字符区间）

| asset_id | asset_class | char span | 原文引文片段 | resolution | check/result |
|---|---|---|---|---|---|
| A01 | code_module | `chars 141-169` (line 5) | `tools/abm/six_dim_power.py` | referenced_unresolved | worktree_path_exists/unresolved |
| A02 | acceptance_criterion | `chars 205-275` (line 5) | `tools/abm/acceptance.py` 的可选 E 环判据 `E1_six_dim_advantage_… | referenced_unresolved | worktree_path_exists/unresolved |
| A03 | parameter_table | `chars 301-883` (line 9) | \| 项 \| 值 \| ⏎ \|---\|---\| ⏎ \| 维数 m \| 6（correctness/accuracy/st… | resolved_in_source | char_span_in_source_markdown/resolved |
| A04 | numeric_anchor | `chars 479-508` (line 13) | min_perm_for_holm(0.05,6)=119 | resolved_in_source | char_span_in_source_markdown/resolved |
| A05 | pipeline_gate_pattern | `chars 1016-1057` (line 21) | `_EXCLUDE=^(artifacts?/\|runs/\|results-/)` | resolved_in_source | char_span_in_source_markdown/resolved |
| A06 | code_module | `chars 1171-1199` (line 25) | `ops/taskplane/tp_pusher.py` | referenced_unresolved | worktree_path_exists/unresolved |
| A07 | vcs_commit | `chars 1333-1346` (line 26) | 历史提交 48f78f87 | referenced_unresolved | git_cat_file/unresolved |
| A08 | script | `chars 1438-1491` (line 27) | `python docs/m9713/build_six_dim_power_validation.py` | referenced_unresolved | worktree_path_exists/unresolved |
| A09 | artifact | `chars 1494-1539` (line 27) | 生成 `docs/m9713/six_dim_power_validation.json` | referenced_unresolved | worktree_path_exists/unresolved |
| A10 | figure_product | `chars 1540-1563` (line 27) | 与两联图；模拟侧结果与历史 seed 逐位一致 | referenced_unresolved | figure_reference_in_source/unresolved |
| A11 | test_module | `chars 1671-1716` (line 29) | 新增 `tests/abm/test_m8716_provenance.py`（38 条） | referenced_unresolved | worktree_path_exists/unresolved |
| A12 | table | `chars 2054-2978` (line 37) | \| 量 \| 实测 \| 比较基准 \| 判定 \| ⏎ \|---\|---\|---\|---\| ⏎ \| G25：2 维真实改进… | resolved_in_source | char_span_in_source_markdown/resolved |
| A13 | table | `chars 3893-4482` (line 71) | \| 关键量 \| 基准 \| 误差 \| <3%？ \| ⏎ \|---\|---\|---\|---\| ⏎ \| 功效正控检出率 0… | resolved_in_source | char_span_in_source_markdown/resolved |
| A14 | figure_declaration | `chars 3008-3036` (line 54) | 无物理场（无空间网格、无场量分布），故「场量云图」不适用 | declared_absent | platform_figures_field_scan/absent |
| A15 | figure | `chars 3064-3084` (line 54) | 三面板，全部由工件 JSON 程序化生成 | resolved_in_platform_record | platform_figures_field/present |
| A16 | limitation_set | `chars 3299-3859` (line 60) | ## ⑤ 注意点 ⏎  ⏎ 1. **根因是门禁不是遗忘**：`^(artifacts?/\|runs/\|result… | resolved_in_source | char_span_in_source_markdown/resolved |
| A17 | numeric_series | `chars 2833-2880` (line 49) | 0.142/0.242/0.458/0.617/0.825/0.975/0.967/1.000 | resolved_in_source | char_span_in_source_markdown/resolved |
| A18 | toolchain | `chars 1909-1983` (line 33) | 工具链：Python 3.11 + stdlib（random/math/statistics）+ matplotl… | resolved_in_source | char_span_in_source_markdown/resolved |
| A19 | numeric_anchor | `chars 2636-2663` (line 46) | 0.880（CP CI [0.844, 0.910]） | resolved_in_source | char_span_in_source_markdown/resolved |
| A20 | upstream_change_reference | `chars 1088-1125` (line 21) | m8719 把 t 分位从 Cornish-Fisher 展开改为精确分位 | resolved_in_source | char_span_in_source_markdown/resolved |
| A21 | provenance_discipline | `chars 1722-1742` (line 30) | 34 个文档印值 ↔ 工件重算值逐项钉死 | resolved_in_source | char_span_in_source_markdown/resolved |

claims：
| claim_id | status | 首要证据（原文片段） |
|---|---|---|
| C01-report-values-come-from-m9713-artifact | unresolved | 生成 `docs/m9713/six_dim_power_validation.json… |
| C02-error-table-honest-no-cosmetic | supported | \| 族判决功效内部一致性 0.608（n=20 两维同时显著） \| 独立维预测 0.64… |
| C03-tests-abm-161-green-with-38-guards | unresolved | 新增 `tests/abm/test_m8716_provenance.py`（38 条… |
| C04-push-gate-is-root-cause | partially-supported | `_EXCLUDE=^(artifacts?/\|runs/\|results-/)` |

## ⑤ 注意点与局限

1. **8 个资产如实登记为 `referenced_unresolved`**：报告属 TensorPlatform 仓（`tools/abm/*`、`docs/m9713/*`、`ops/taskplane/tp_pusher.py`、commit 48f78f87），这些路径**在本 TensorKnowledge 工作树内预期不存在**；我把「不存在」当结果上报，而不是补一个看起来漂亮的 resolved。因此报告 §③ 的数值溯源链**在本工序内未闭合**——数值正确性属上游与平台门，本工序不担保。
2. **`resolved_in_platform_record` 是 v2 新增状态**：三面板图不在 markdown 正文里，而在平台记录 `figures[0]`（`six_dim_power_evidence.png`）。v1 schema 只有三值枚举，无此情形，故新建 v2 并**不动 v1**（v1 是 wp-448-01 的冻结契约）。
3. **`declared_absent` 与 `present` 并存不矛盾**：A14 指「场量云图」（报告声明不适用），A15 指替代的比较/校准图（平台确有 1 张）。两者分别登记，避免用「有图」掩盖「无场量云图」、也避免用「无场量云图」否定已有图件。
4. **本工序不重算任何上游数字**：`integrity.upstream_numbers_recomputed=false`。A12/A13 两张表只保证「原文能逐字定位」，不保证「数值正确」。
5. **`verified` 一律不置**：4 条 claim 无一标 verified；C01/C03 因缺外部件为 `unresolved`，C04 为 `partially-supported`（原文两处陈述是文本证据，但门禁实现不在本树，无法复现滤除行为）。
6. **本仓也有同一类门禁陷阱（本单实撞）**：`.gitignore` 里 `artifacts/` 被整目录忽略（注释写着「mission-push gate drops artifacts/**」），与源报告 §⑤.1「根因是门禁不是遗忘」所述 m8716 工件被 `^(artifacts?/|runs/|results-/)` 滤除属同一机制。本工序最初把主产物写在 `artifacts/wp-11478-01/`，`git check-ignore` 判定其为**不可入库**，故整体迁到受跟踪的 `docs/wp-11478-01/`；该判定已机器写入 `integrity.output_path_gitignored`（值 `False`）并有测试守护。
7. **幂等性边界**：`provenance.emitted_at` 为时间戳，故信封每次生成逐字节不同；其余产物（manifest / claims / register / verify / png）同输入逐字节一致——由 `tests/test_kf_wp11478.py::test_pipeline_rerun_is_byte_identical` 实跑两次比对证明，不是声明。
8. **只碰 report_id=11478**：脚本把 report_id 写成常量，`fetch` 只请求 `/11478`；不存在跨报告读写路径。

## ⑥ 自检：逐条对照 acceptance

| acceptance 条目 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | `json.load(asset_manifest.json)` 通过；信封亦通过 kf_result.v1 校验 |
| schema_pass | ✅ | jsonschema 对 `schemas/asset_manifest.v2.schema.json` 校验通过（v1 因 const 钉死 wp-448-01 不可复用，见 ⑤.2） |
| source_locator_resolvable | ✅ | 21 个资产 locator + claim 引文全部 `quote == md[start:end]` 且 `count==1`；**重新取数**后复算 |
| source_hash_matches | ✅ | 独立重取 markdown 的 sha256 = `b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258` = 契约值 |
| no_duplicate_ids | ✅ | asset_id 21 个互异；claim_id 互异 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | supported/partially-supported 均带原文证据，unresolved 均带 unresolved_reason；无 verified=true |

附加一致性（非 acceptance 条目，但同样机器复算）：counts_consistent ✅、sections_exist_in_source ✅。

**诚实声明（honest-FAIL 不粉饰）**：本次**没有**失败项；但弱项必须写明——① 8 个外部资产的解析在本树内不可能完成，属结构性未闭合；② 上游「34 印值↔工件」「161 passed」在本树无证据可复算，只能登记为 unresolved；③ 未做任何上游数值正确性判断。

## ⑦ result JSON（唯一 json 代码块，原样提交）

```json
{
  "package_id": "wp-11478-01",
  "task_type": "01-asset-registration",
  "report_id": "11478",
  "provenance": {
    "source_hash": "sha256:b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258",
    "source_field": "markdown",
    "producer": "scripts/kf_register_11478.py (worktree agent/m15724)",
    "emitted_at": "2026-11-12T02:24:06+00:00",
    "notes": "source=tensor://reports/11478 chars=4710 bytes_utf8=8163; asset_manifest.v2 assets=21 (referenced_unresolved=8, resolved_in_source=11, declared_absent=1, resolved_in_platform_record=1); claims=4; local verify status=pass; no upstream number was recomputed or marked verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v2",
      "package_id": "wp-11478-01",
      "task_type": "01-asset-registration",
      "report_id": "11478",
      "source": {
        "uri": "tensor://reports/11478",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258",
        "chars": 4710,
        "bytes_utf8": 8163,
        "title": "P143W2-N04 六维功效门证据溯源补齐：工件迁址 docs/m9713 + 文档印值机器校验（m9713）",
        "scenario_key": "platform/abm/six_dim_power",
        "platform_figures": [
          "six_dim_power_evidence.png"
        ],
        "platform_tags": [
          "ABM",
          "统计功效",
          "Holm校正",
          "置换检验",
          "证据溯源",
          "零手抄",
          "TensorPlatform"
        ]
      },
      "counts": {
        "assets": 21,
        "by_class": {
          "code_module": 2,
          "acceptance_criterion": 1,
          "parameter_table": 1,
          "numeric_anchor": 2,
          "pipeline_gate_pattern": 1,
          "vcs_commit": 1,
          "script": 1,
          "artifact": 1,
          "figure_product": 1,
          "test_module": 1,
          "table": 2,
          "figure_declaration": 1,
          "figure": 1,
          "limitation_set": 1,
          "numeric_series": 1,
          "toolchain": 1,
          "upstream_change_reference": 1,
          "provenance_discipline": 1
        },
        "by_resolution": {
          "referenced_unresolved": 8,
          "resolved_in_source": 11,
          "declared_absent": 1,
          "resolved_in_platform_record": 1
        },
        "resolved_in_source": 11,
        "referenced_unresolved": 8,
        "declared_absent": 1,
        "resolved_in_platform_record": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "code_module",
          "label": "六维功效门模块 tools/abm/six_dim_power.py",
          "in_report_section": "## ① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 141,
            "end_char": 169,
            "start_line": 4,
            "end_line": 4,
            "quote": "`tools/abm/six_dim_power.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "note": "报告只声明模块位置与设计（纯 stdlib、零领域语义、参数由调用方注入）；文件不在本工作树（属 TensorPlatform 仓）",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "tools/abm/six_dim_power.py"
            ],
            "missing": [
              "tools/abm/six_dim_power.py"
            ],
            "result": "unresolved",
            "detail": "报告属 TensorPlatform 仓，路径在本（TensorKnowledge）工作树预期缺失"
          }
        },
        {
          "asset_id": "A02",
          "asset_class": "acceptance_criterion",
          "label": "可选 E 环判据 E1_six_dim_advantage_statistical",
          "in_report_section": "## ① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 205,
            "end_char": 275,
            "start_line": 4,
            "end_line": 4,
            "quote": "`tools/abm/acceptance.py` 的可选 E 环判据 `E1_six_dim_advantage_statistical`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "note": "判据名与所在文件可定位；acceptance.py 本体不在本工作树",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "tools/abm/acceptance.py"
            ],
            "missing": [
              "tools/abm/acceptance.py"
            ],
            "result": "unresolved",
            "detail": "报告属 TensorPlatform 仓，路径在本（TensorKnowledge）工作树预期缺失"
          }
        },
        {
          "asset_id": "A03",
          "asset_class": "parameter_table",
          "label": "输入参数表（本次复核所用固定设计，9 行）",
          "in_report_section": "## ① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 301,
            "end_char": 883,
            "start_line": 8,
            "end_line": 18,
            "quote": "| 项 | 值 |\n|---|---|\n| 维数 m | 6（correctness/accuracy/stability/efficiency/reproducibility/applicability） |\n| 判决规则 G25 | Holm(α=0.05) 后 ≥min_dims=2 维方向性（greater）显著更好 |\n| 置换分辨率下限 | min_perm_for_holm(0.05,6)=119；族模拟用 499，G25 判决用 9999 |\n| G25 合成算例 | 12 对/维，accuracy d_z=1.94、efficiency d_z=1.65，其余 4 维零效应 |\n| 零效应族 | 200 族 × 20 对 × 499 置换（seed 11） |\n| A/A 空对照 | 60 族 × 3 seeds（31 主 + 0,1,2 稳定性），合并 180 族 |\n| 功效正控 | d=0.5, n=20, ρ=0.7 与 ρ=0；400 次模拟 × 999 置换（seed 5） |\n| 族功效曲线 | d_z=0.8, 2/6 维有效应, n∈{9,12,16,20,26,32,40,60}, 120 模拟/行 × 499 置换（seed 3） |\n| MDE 抽查 | n=20/40，1000 置换（seed 7） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "维数/判决规则/置换分辨率/算例规模/seed 全在表内，是本工序可核的唯一定义面",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A04",
          "asset_class": "numeric_anchor",
          "label": "置换分辨率下限 min_perm_for_holm(0.05,6)=119",
          "in_report_section": "## ① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 479,
            "end_char": 508,
            "start_line": 12,
            "end_line": 12,
            "quote": "min_perm_for_holm(0.05,6)=119",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "单值锚点；报告 §⑤ 另以「B≥119」复述同一约束",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A05",
          "asset_class": "pipeline_gate_pattern",
          "label": "推送门禁排除正则 _EXCLUDE=^(artifacts?/|runs/|results-/)",
          "in_report_section": "## ① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 1016,
            "end_char": 1057,
            "start_line": 20,
            "end_line": 20,
            "quote": "`_EXCLUDE=^(artifacts?/|runs/|results-/)`",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "根因声明：证据目录被整目录滤除（§⑤ 第 1 条同义复述）；本工序不复核门禁实现",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A06",
          "asset_class": "code_module",
          "label": "推送脚本 ops/taskplane/tp_pusher.py",
          "in_report_section": "## ② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1171,
            "end_char": 1199,
            "start_line": 24,
            "end_line": 24,
            "quote": "`ops/taskplane/tp_pusher.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "note": "报告称 _EXCLUDE/_EXCLUDE2 位于此文件；文件不在本工作树",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "ops/taskplane/tp_pusher.py"
            ],
            "missing": [
              "ops/taskplane/tp_pusher.py"
            ],
            "result": "unresolved",
            "detail": "报告属 TensorPlatform 仓，路径在本（TensorKnowledge）工作树预期缺失"
          }
        },
        {
          "asset_id": "A07",
          "asset_class": "vcs_commit",
          "label": "历史提交 48f78f87（取回构建脚本的来源）",
          "in_report_section": "## ② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1333,
            "end_char": 1346,
            "start_line": 25,
            "end_line": 25,
            "quote": "历史提交 48f78f87",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "note": "外部仓库提交号；本仓对象库无此对象（git cat-file 失败）",
          "resolution_check": {
            "check": "git_cat_file",
            "object": "48f78f87",
            "exit_code": 128,
            "result": "unresolved"
          }
        },
        {
          "asset_id": "A08",
          "asset_class": "script",
          "label": "构建脚本与其复现命令 docs/m9713/build_six_dim_power_validation.py",
          "in_report_section": "## ② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1438,
            "end_char": 1491,
            "start_line": 26,
            "end_line": 26,
            "quote": "`python docs/m9713/build_six_dim_power_validation.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "note": "复现命令原文；脚本不在本工作树，命令无法在本仓执行",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "docs/m9713/build_six_dim_power_validation.py"
            ],
            "missing": [
              "docs/m9713/build_six_dim_power_validation.py"
            ],
            "result": "unresolved",
            "detail": "报告属 TensorPlatform 仓，路径在本（TensorKnowledge）工作树预期缺失"
          }
        },
        {
          "asset_id": "A09",
          "asset_class": "artifact",
          "label": "证据工件 docs/m9713/six_dim_power_validation.json",
          "in_report_section": "## ② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1494,
            "end_char": 1539,
            "start_line": 26,
            "end_line": 26,
            "quote": "生成 `docs/m9713/six_dim_power_validation.json`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "note": "报告 §③ 声明全部数值取自该工件；工件不在本工作树，故数值溯源链在本工序未闭合",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "docs/m9713/six_dim_power_validation.json"
            ],
            "missing": [
              "docs/m9713/six_dim_power_validation.json"
            ],
            "result": "unresolved",
            "detail": "报告属 TensorPlatform 仓，路径在本（TensorKnowledge）工作树预期缺失"
          }
        },
        {
          "asset_id": "A10",
          "asset_class": "figure_product",
          "label": "构建脚本附带产出的「两联图」",
          "in_report_section": "## ② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1540,
            "end_char": 1563,
            "start_line": 26,
            "end_line": 26,
            "quote": "与两联图；模拟侧结果与历史 seed 逐位一致",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "note": "图件本体未随报告提交，平台 figures 仅 1 张（A15）；此为脚本副产物声明",
          "resolution_check": {
            "check": "figure_reference_in_source",
            "result": "unresolved",
            "detail": "原文仅声明脚本产出两联图，未给文件名/路径"
          }
        },
        {
          "asset_id": "A11",
          "asset_class": "test_module",
          "label": "溯源守卫测试 tests/abm/test_m8716_provenance.py（38 条）",
          "in_report_section": "## ② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1671,
            "end_char": 1716,
            "start_line": 28,
            "end_line": 28,
            "quote": "新增 `tests/abm/test_m8716_provenance.py`（38 条）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "note": "测试文件不在本工作树；「38 条」「161 passed」属上游自报，本工序未运行",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "tests/abm/test_m8716_provenance.py"
            ],
            "missing": [
              "tests/abm/test_m8716_provenance.py"
            ],
            "result": "unresolved",
            "detail": "报告属 TensorPlatform 仓，路径在本（TensorKnowledge）工作树预期缺失"
          }
        },
        {
          "asset_id": "A12",
          "asset_class": "table",
          "label": "③ 计算结果表（12 行·量/实测/比较基准/判定）",
          "in_report_section": "## ③ 计算结果（全部取自 `docs/m9713/six_dim_power_validation.json`，程序化导出零手抄）",
          "locator": {
            "method": "char_span",
            "start_char": 2054,
            "end_char": 2978,
            "start_line": 36,
            "end_line": 49,
            "quote": "| 量 | 实测 | 比较基准 | 判定 |\n|---|---|---|---|\n| G25：2 维真实改进 | n_significant_better=2, decision_pass=True；accuracy p_holm=0.0024, efficiency p_holm=0.0025；d_z=1.94/1.65 | 预声明规则 ≥2 维 Holm 显著 | 规则按设计触发 |\n| G25：零效应对照 | n_significant_better=0, decision_pass=False, max p_perm=1.0 | 不得判出优势 | 通过 |\n| FWER（≥1 维显著） | 0.060，CP 95% CI [0.031, 0.102] | 名义 α=0.05 | CI 覆盖 α |\n| 判决规则误报率（≥2 维显著） | 0.000（0/200），CI 上界 0.018 | ≤ α=0.05 | 通过 |\n| 逐维误报率最大值 | 0.020 | ≤ α=0.05 | 通过 |\n| 六维全显著族比例 | 0.000（0/200） | ≈0 | 通过 |\n| A/A 空对照（180 族合并） | 族判决误报率 0.000，CI 上界 0.060 | ≤ α=0.05 | pass=True |\n| 功效正控 ρ=0.7 | 0.880（CP CI [0.844, 0.910]） | 解析 0.8765 | 见 ⑥ |\n| 功效正控 ρ=0（保守） | 0.4325 | 解析 0.4412 | 见 ⑥ |\n| ρ 扫描 | 0.457 / 0.560 / 0.707 / 0.863 / 0.993（ρ=0,0.3,0.5,0.7,0.85） | 单调递增即配对收益成立 | 单调 |\n| 族判决功效 vs n | 0.142/0.242/0.458/0.617/0.825/0.975/0.967/1.000 | 目标 0.8 | required_n=26（网格命中） |\n| MDE n=20 / n=40 | 0.6937 / 0.4100 | 解析 0.6562 / 0.4529 | 见 ⑥ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "12 个数值行可在原文逐字定位；数值正确性属上游，本工序只登记",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A13",
          "asset_class": "table",
          "label": "⑥ 误差判定表（7 行·关键量/基准/误差/<3%？）",
          "in_report_section": "## ⑥ 误差判定（逐项 vs 基准，显式回答是否 <3%）",
          "locator": {
            "method": "char_span",
            "start_char": 3893,
            "end_char": 4482,
            "start_line": 70,
            "end_line": 78,
            "quote": "| 关键量 | 基准 | 误差 | <3%？ |\n|---|---|---|---|\n| 功效正控检出率 0.880（ρ=0.7） | 解析 0.8765（正态+t 修正） | 0.40% | **是** |\n| 功效正控检出率 0.4325（ρ=0，最保守） | 解析 0.4412 | 2.0% | **是** |\n| 族判决功效内部一致性 0.608（n=20 两维同时显著） | 独立维预测 0.644 | 绝对 0.036 / 相对 5.5% | **否**（Monte-Carlo + 独立维近似，如实列出） |\n| MDE(n) n=20 数值 0.6937 | 解析 0.6562（2.802σ/√n 口径） | +5.7% | **否**（<15% 精度标准内；小 n 由 t 分位主导） |\n| MDE(n) n=40 数值 0.4100 | 解析 0.4529 | −9.5% | **否**（同上，二分网格 + 置换离散所致） |\n| 判决规则误报率 0.000 | α=0.05 | 0/200，CI 上界 0.018 | 估计量在 CI 内，不予「<3%」声明 |\n| 族级 FWER 0.060 | α=0.05 | 点估计 +0.010，CI [0.031,0.102] | **否**（200 族分辨率 0.05/族，只能声明 CI 覆盖） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "含 3 行显式「否」判定，是报告诚实申报面",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A14",
          "asset_class": "figure_declaration",
          "label": "无场量云图声明（统计方法任务无空间场）",
          "in_report_section": "## ④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 3008,
            "end_char": 3036,
            "start_line": 53,
            "end_line": 53,
            "quote": "无物理场（无空间网格、无场量分布），故「场量云图」不适用",
            "unique": true
          },
          "resolution": "declared_absent",
          "note": "场量云图声明为不适用；平台 figures 字段非空（替代图见 A15）",
          "resolution_check": {
            "check": "platform_figures_field_scan",
            "terms": [
              "云图",
              "contour",
              "field plot",
              "场量"
            ],
            "platform_figures_count": 1,
            "figures": [
              "six_dim_power_evidence.png"
            ],
            "field_plot_hits": [],
            "result": "absent",
            "detail": "本资产指「场量云图」；平台 figures 内为替代比较/校准图（见 A15），名称与图注均无场量云图词汇"
          }
        },
        {
          "asset_id": "A15",
          "asset_class": "figure",
          "label": "三面板比较/校准图（平台 figures: six_dim_power_evidence.png）",
          "in_report_section": "## ④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 3064,
            "end_char": 3084,
            "start_line": 53,
            "end_line": 53,
            "quote": "三面板，全部由工件 JSON 程序化生成",
            "unique": true
          },
          "resolution": "resolved_in_platform_record",
          "note": "图件不在 markdown 内，但平台记录 figures[0] 存在（1 条），故登记为平台记录内可解析",
          "resolution_check": {
            "check": "platform_figures_field",
            "platform_figures_count": 1,
            "figures": [
              "six_dim_power_evidence.png"
            ],
            "result": "present"
          }
        },
        {
          "asset_id": "A16",
          "asset_class": "limitation_set",
          "label": "§⑤ 注意点与适用边界（6 条）",
          "in_report_section": "## ⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 3299,
            "end_char": 3859,
            "start_line": 59,
            "end_line": 66,
            "quote": "## ⑤ 注意点\n\n1. **根因是门禁不是遗忘**：`^(artifacts?/|runs/|results-/)` 会静默滤除证据目录，任何「文档引用 artifacts/」的岗位都会复现同样脱链——证据应默认落 `docs/m<本单>/`。\n2. **解析参照会随后续精度修复漂移**：m8719 的 t 分位精确化使解析列上移 ≤0.4%；没有 provenance 守卫时这种漂移无人发现（结论不变但印值已错）。\n3. **模拟侧不可随意重播种**：本单全部 seed 固定，跨进程逐位一致；改 seed 会让文档印值与工件脱钩（守卫会红，这是设计意图）。\n4. **Monte-Carlo 噪声边界**：族功效 n=32(0.975) > n=40(0.967) 是 120 次模拟的 SE≈0.014 内波动，不是效应回退；本单测试只约束「反向不超 0.05」。\n5. **适用边界**：配对设计要求同一 (lineage, seat) 两臂一一对应；独立双样本不支持（模块明确 NOT_SUPPORTED）。置换 p 值有分辨率下限（α=0.05, m=6 → B≥119），不足时结论是「分辨率不够」而非「无效应」。\n6. **统计显著 ≠ 物理重要**：模块只回答差异是否可靠，物理判据仍由领域决定。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "门禁根因/解析漂移/seed 纪律/MC 噪声/适用边界/统计≠物理，六条原文",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A17",
          "asset_class": "numeric_series",
          "label": "族判决功效 vs n 数列（8 点）",
          "in_report_section": "## ③ 计算结果（全部取自 `docs/m9713/six_dim_power_validation.json`，程序化导出零手抄）",
          "locator": {
            "method": "char_span",
            "start_char": 2833,
            "end_char": 2880,
            "start_line": 48,
            "end_line": 48,
            "quote": "0.142/0.242/0.458/0.617/0.825/0.975/0.967/1.000",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "单行 8 值；点数与 n 网格 {9,12,16,20,26,32,40,60} 对齐（本工序只登记不复算）",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A18",
          "asset_class": "toolchain",
          "label": "工具链声明（Python 3.11 + stdlib + matplotlib + pytest）",
          "in_report_section": "## ② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1909,
            "end_char": 1983,
            "start_line": 32,
            "end_line": 32,
            "quote": "工具链：Python 3.11 + stdlib（random/math/statistics）+ matplotlib（仅作图）+ pytest。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "本工序自有工具链于 runs 内记录，不复用上游声明",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A19",
          "asset_class": "numeric_anchor",
          "label": "功效正控 ρ=0.7 检出率 0.880 与 CP CI [0.844, 0.910]",
          "in_report_section": "## ③ 计算结果（全部取自 `docs/m9713/six_dim_power_validation.json`，程序化导出零手抄）",
          "locator": {
            "method": "char_span",
            "start_char": 2636,
            "end_char": 2663,
            "start_line": 45,
            "end_line": 45,
            "quote": "0.880（CP CI [0.844, 0.910]）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "与 §⑥ 解析基准 0.8765 配对的点估计；§⑥ 自报误差 0.40%",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A20",
          "asset_class": "upstream_change_reference",
          "label": "上游 m8719 精度修复：t 分位 Cornish-Fisher→精确分位",
          "in_report_section": "## ① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 1088,
            "end_char": 1125,
            "start_line": 20,
            "end_line": 20,
            "quote": "m8719 把 t 分位从 Cornish-Fisher 展开改为精确分位",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "解释「解析参照列漂移 ≤0.4%」的因果声明；属上游变更记录，本工序不复核",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        },
        {
          "asset_id": "A21",
          "asset_class": "provenance_discipline",
          "label": "34 个文档印值↔工件重算值逐项钉死",
          "in_report_section": "## ② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1722,
            "end_char": 1742,
            "start_line": 29,
            "end_line": 29,
            "quote": "34 个文档印值 ↔ 工件重算值逐项钉死",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "note": "零手抄机制的声明面；对应测试体 A11（未在本工作树）",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "span_roundtrip": true
          }
        }
      ],
      "claims": [
        {
          "claim_id": "C01-report-values-come-from-m9713-artifact",
          "text": "报告 §③/§⑥ 的全部数值唯一取自工件 docs/m9713/six_dim_power_validation.json",
          "status": "unresolved",
          "evidence": [
            {
              "quote": "生成 `docs/m9713/six_dim_power_validation.json`",
              "source_field": "markdown",
              "locator": {
                "method": "char_span",
                "start_char": 1494,
                "end_char": 1539,
                "start_line": 26,
                "end_line": 26,
                "quote": "生成 `docs/m9713/six_dim_power_validation.json`",
                "unique": true
              }
            },
            {
              "quote": "全部取自 `docs/m9713/six_dim_power_validation.json`",
              "source_field": "markdown",
              "locator": {
                "method": "char_span",
                "start_char": 1995,
                "end_char": 2042,
                "start_line": 34,
                "end_line": 34,
                "quote": "全部取自 `docs/m9713/six_dim_power_validation.json`",
                "unique": true
              }
            }
          ],
          "source_hash": "sha256:b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258",
          "verified": false,
          "unresolved_reason": "工件与生成脚本均不在本（TensorKnowledge）工作树，本工序只能登记「出处声明」本身，无法打开工件逐值核对；不标 verified"
        },
        {
          "claim_id": "C02-error-table-honest-no-cosmetic",
          "text": "§⑥ 对 3 项误差 >3% 的指标显式标注「否」，未以口径调整粉饰",
          "status": "supported",
          "evidence": [
            {
              "quote": "| 族判决功效内部一致性 0.608（n=20 两维同时显著） | 独立维预测 0.644 | 绝对 0.036 / 相对 5.5% | **否**（Monte-Carlo + 独立维近似，如实列出） |",
              "source_field": "markdown",
              "locator": {
                "method": "char_span",
                "start_char": 4053,
                "end_char": 4155,
                "start_line": 74,
                "end_line": 74,
                "quote": "| 族判决功效内部一致性 0.608（n=20 两维同时显著） | 独立维预测 0.644 | 绝对 0.036 / 相对 5.5% | **否**（Monte-Carlo + 独立维近似，如实列出） |",
                "unique": true
              }
            },
            {
              "quote": "| MDE(n) n=40 数值 0.4100 | 解析 0.4529 | −9.5% | **否**（同上，二分网格 + 置换离散所致） |",
              "source_field": "markdown",
              "locator": {
                "method": "char_span",
                "start_char": 4249,
                "end_char": 4320,
                "start_line": 76,
                "end_line": 76,
                "quote": "| MDE(n) n=40 数值 0.4100 | 解析 0.4529 | −9.5% | **否**（同上，二分网格 + 置换离散所致） |",
                "unique": true
              }
            }
          ],
          "source_hash": "sha256:b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258",
          "verified": false,
          "note": "判定依据=原文自身的三处「否」标注与结论句并列出现；只证「如实列出」这一文本事实，不证数值正确"
        },
        {
          "claim_id": "C03-tests-abm-161-green-with-38-guards",
          "text": "上游自报 tests/abm 161 条全绿，其中 38 条为「文档印值↔工件」溯源守卫",
          "status": "unresolved",
          "evidence": [
            {
              "quote": "新增 `tests/abm/test_m8716_provenance.py`（38 条）",
              "source_field": "markdown",
              "locator": {
                "method": "char_span",
                "start_char": 1671,
                "end_char": 1716,
                "start_line": 28,
                "end_line": 28,
                "quote": "新增 `tests/abm/test_m8716_provenance.py`（38 条）",
                "unique": true
              }
            },
            {
              "quote": "`tests/abm` 161 条全绿",
              "source_field": "markdown",
              "locator": {
                "method": "char_span",
                "start_char": 4689,
                "end_char": 4708,
                "start_line": 82,
                "end_line": 82,
                "quote": "`tests/abm` 161 条全绿",
                "unique": true
              }
            }
          ],
          "source_hash": "sha256:b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258",
          "verified": false,
          "unresolved_reason": "测试文件与测试运行记录均不在本工作树，本工序未执行该测试；「161 passed」「38 条」为上游自报"
        },
        {
          "claim_id": "C04-push-gate-is-root-cause",
          "text": "工件丢失根因是推送门禁正则整目录滤除 artifacts/runs，而非人工遗忘",
          "status": "partially-supported",
          "evidence": [
            {
              "quote": "`_EXCLUDE=^(artifacts?/|runs/|results-/)`",
              "source_field": "markdown",
              "locator": {
                "method": "char_span",
                "start_char": 1016,
                "end_char": 1057,
                "start_line": 20,
                "end_line": 20,
                "quote": "`_EXCLUDE=^(artifacts?/|runs/|results-/)`",
                "unique": true
              }
            },
            {
              "quote": "**根因是门禁不是遗忘**",
              "source_field": "markdown",
              "locator": {
                "method": "char_span",
                "start_char": 3312,
                "end_char": 3325,
                "start_line": 61,
                "end_line": 61,
                "quote": "**根因是门禁不是遗忘**",
                "unique": true
              }
            },
            {
              "quote": "会静默滤除证据目录",
              "source_field": "markdown",
              "locator": {
                "method": "char_span",
                "start_char": 3359,
                "end_char": 3368,
                "start_line": 61,
                "end_line": 61,
                "quote": "会静默滤除证据目录",
                "unique": true
              }
            }
          ],
          "source_hash": "sha256:b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258",
          "verified": false,
          "unresolved_reason": "原文两处同义陈述构成文本证据；门禁实现（ops/taskplane/tp_pusher.py）不在本工作树，本工序无法复现滤除行为，故不足以上升为 supported"
        }
      ],
      "integrity": {
        "quote_uniqueness": "all_pass",
        "hash_recomputed_locally": "b5b856a019926eb922be123bd6e34077d4a1b470775aa311e56761e680057258",
        "hash_matches_contract": true,
        "locator_roundtrip": "all_pass",
        "no_duplicate_ids": true,
        "verification_status": "not_verified_by_platform_gate",
        "upstream_numbers_recomputed": false,
        "output_path": "docs/wp-11478-01/asset_manifest.json",
        "output_path_gitignored": false
      }
    }
  },
  "claims": [
    {
      "claim_id": "C01-report-values-come-from-m9713-artifact",
      "text": "报告 §③/§⑥ 的全部数值唯一取自工件 docs/m9713/six_dim_power_validation.json",
      "status": "unresolved",
      "evidence": [
        {
          "quote": "生成 `docs/m9713/six_dim_power_validation.json`",
          "source_field": "markdown",
          "note": "chars 1494-1539 (lines 26-26), unique=True"
        },
        {
          "quote": "全部取自 `docs/m9713/six_dim_power_validation.json`",
          "source_field": "markdown",
          "note": "chars 1995-2042 (lines 34-34), unique=True"
        }
      ],
      "unresolved_reason": "工件与生成脚本均不在本（TensorKnowledge）工作树，本工序只能登记「出处声明」本身，无法打开工件逐值核对；不标 verified"
    },
    {
      "claim_id": "C02-error-table-honest-no-cosmetic",
      "text": "§⑥ 对 3 项误差 >3% 的指标显式标注「否」，未以口径调整粉饰",
      "status": "supported",
      "evidence": [
        {
          "quote": "| 族判决功效内部一致性 0.608（n=20 两维同时显著） | 独立维预测 0.644 | 绝对 0.036 / 相对 5.5% | **否**（Monte-Carlo + 独立维近似，如实列出） |",
          "source_field": "markdown",
          "note": "chars 4053-4155 (lines 74-74), unique=True"
        },
        {
          "quote": "| MDE(n) n=40 数值 0.4100 | 解析 0.4529 | −9.5% | **否**（同上，二分网格 + 置换离散所致） |",
          "source_field": "markdown",
          "note": "chars 4249-4320 (lines 76-76), unique=True"
        }
      ]
    },
    {
      "claim_id": "C03-tests-abm-161-green-with-38-guards",
      "text": "上游自报 tests/abm 161 条全绿，其中 38 条为「文档印值↔工件」溯源守卫",
      "status": "unresolved",
      "evidence": [
        {
          "quote": "新增 `tests/abm/test_m8716_provenance.py`（38 条）",
          "source_field": "markdown",
          "note": "chars 1671-1716 (lines 28-28), unique=True"
        },
        {
          "quote": "`tests/abm` 161 条全绿",
          "source_field": "markdown",
          "note": "chars 4689-4708 (lines 82-82), unique=True"
        }
      ],
      "unresolved_reason": "测试文件与测试运行记录均不在本工作树，本工序未执行该测试；「161 passed」「38 条」为上游自报"
    },
    {
      "claim_id": "C04-push-gate-is-root-cause",
      "text": "工件丢失根因是推送门禁正则整目录滤除 artifacts/runs，而非人工遗忘",
      "status": "partially-supported",
      "evidence": [
        {
          "quote": "`_EXCLUDE=^(artifacts?/|runs/|results-/)`",
          "source_field": "markdown",
          "note": "chars 1016-1057 (lines 20-20), unique=True"
        },
        {
          "quote": "**根因是门禁不是遗忘**",
          "source_field": "markdown",
          "note": "chars 3312-3325 (lines 61-61), unique=True"
        },
        {
          "quote": "会静默滤除证据目录",
          "source_field": "markdown",
          "note": "chars 3359-3368 (lines 61-61), unique=True"
        }
      ],
      "unresolved_reason": "原文两处同义陈述构成文本证据；门禁实现（ops/taskplane/tp_pusher.py）不在本工作树，本工序无法复现滤除行为，故不足以上升为 supported"
    }
  ]
}
```
