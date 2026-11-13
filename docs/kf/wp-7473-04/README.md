# KF-RESULT wp-7473-04

**独立性**：审核上下文 = report 7473 原文（sha256 逐字节校验）+ 上游 KO（`docs/kf/wp-7473-01/`）
+ 仓内公开代码与 git 历史。未读生产者的解释性叙述；产物不含生产者自评材料。

**结论（disposition）**：`request-changes`（needs-fix）。severity：blocking 0 ·
major 2 · minor 3 · informational 1。
科学结论全部独立复现、无造假迹象；两处证据表标注/判据问题必须在入账前修。

---

## ① 本工序做了什么

对 report_id=7473（TensorLBM 湍流槽道求解器验证欠账清偿 R1）做**独立红队审核**，审核对象
= 上游包 `wp-7473-01`。三件事：
1. 逐条把报告的 9 组主张绑定到原文引文，并对每个可观测量做**外部复算/重测**（不引用生产者的
   `results.json`，因为它未随仓交付）；
2. 对报告自己的数值表做**算术审计**（tau+/s+/拟合残差/误差百分比/参数恒等式）；
3. 用 git 历史核对代码侧主张（默认值、白名单、合入时是否无测试）。

不改上游产物、不改 report 7473、不写 verified 之类字段（验证级别留给平台门）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具/设置 |
|---|---|---|
| 1 | 取原文 | `GET /api/v1/tensor/reports/7473`，重算 sha256 = `c3b3d0954d289cf1f7849f83889e995c71c39bbc15122ddf9f823f5d698d0f6b`，与契约一致 |
| 2 | 读上游 KO | `docs/kf/wp-7473-01/{asset_manifest.json,verification.json}`（38 资产，结构化检查全过） |
| 3 | 算术审计 | `work/wp-7473-04/independent_probe.py`（纯算术层：tau+=0.5+3nu、s+=1/tau+、拟合残差、误差百分比） |
| 4 | 力项重测 | 同上脚本第二层：8×18×8、a=1e-4、12 步、体相 x∈[6,12) 平均、CPU float32 单线程；5 个 nu × 2 scheme + campaign nu + A′ nu + 120 步长 run |
| 5 | 孪生重测 | `work/wp-7473-04/independent_twin.py`：`run_laminar_poiseuille` halfway/interpolated × 800/2000 步 + `u_max_target=None` 负控 |
| 6 | 代码溯源 | `git -C /root/tensor-ecosystem/TensorLBM`：`show 520d3282:…`（#891）、`log --diff-filter=A -- tests/…`（#894）、`-S` 找 #927 |
| 7 | 引文落库 | `work/wp-7473-04/build_review.py`：每条 quote 按"唯一行"提取并断言是原文子串，失败即中止 |

环境：python 3.11 + torch 2.7.1；TensorLBM main `da452346`（含 #927 之后的状态，见局限）。
一键复跑：`bash work/wp-7473-04/repro.sh`。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7473-04/review_report.json` | 审核报告：9 条主张裁定、6 条 finding（severity 分级）、复现命令、not_run 清单、局限 |
| `docs/kf/wp-7473-04/review_events.json` | 审核台账（`request-changes`，带 findings；过 `schemas/review-event.schema.json` 与 `scripts/ke_state_machine.py` 折叠 → `draft` / `OK_CHANGES_REQUESTED`） |
| `docs/kf/wp-7473-04/kf_result.json` | 结果信封（过 `schemas/kf_result.v1.schema.json`） |
| `work/wp-7473-04/independent_probe.py` + `probe_2026-11-12.json` | 力项重测原始数（可机读） |
| `work/wp-7473-04/independent_twin.py` + `twin_repro.json` | 孪生/负控重测原始数 |
| `work/wp-7473-04/fig_review_force_injection.png` | 图 1：guo_sp 注入率实测 vs 报告拟合式 |
| `work/wp-7473-04/source_7473.md` | 原文快照（8934 bytes，sha256 与契约一致） |

## ④ 证据定位表（claim → 原文引文）

| claim | 裁定 | 原文引文（逐字） |
|---|---|---|
| C1 默认值 guo_sp→trt_split + 白名单 | supported | `| 1 | `force_scheme` 默认 `"guo_sp"` → **`"trt_split"`**，并把注释里被写反的结论改正 | 表 1：`trt_split` 在全部 `tau+` 上 `dU/dt = a`（≤0.06 %）；`guo_sp` 是受 τ 调制的错解 |` |
| C2 trt_split 力项精确 | supported | `| 0.0020 | 0.5060 | 1.9763 | **1.0001** | 0.0277 |` |
| C3 guo_sp 战役下 0.63% | supported | `时**注入量趋于 0**。在战役粘性下它只给出 **0.63 %** 的驱动力。` |
| C4 孪生 L2/峰值比/壁面原点 | supported | `| 层流孪生峰值比 `u_max^sim/u_max^exact` | 0.99065 | 1 | 0.94 % | 是 |` |
| C5 插值反弹不收敛 | supported | `2. **插值反弹（`q≠0.5`）不收敛到解析抛物线**：`q=0.625` 下 L2 2.46 %→3.11 %（800→2000 步` |
| C6 旧标定发散 | partially-supported | `| 沿用战役参数（`u_max_target=None`）的层流孪生 | `u_max = 0.896`，`Ma = 1.55`，`L2 = nan` | 旧标定路径在战役 `Re_tau` 下**必然发散** |` |
| C7 wall_exchange 42% 根因 | supported | `   `u_tau_wall_exchange = 0.03556`，而 `body_force` 路线 = 0.025（孪生自身 `u_tau`），` |
| C8 合入时无测试 | supported | `> **合入时无任何 pytest 用例、无验证文档**，benchmark 仍停留在 `benchmarks/pending/channel_turb_3d/`）。` |
| C9 未做项声明 | supported | `3. 本单只验证**层流锚**。Re_tau=180/395 的壁面解析湍流（MKM DNS、Reichardt 复合律、` |

全部 17 条引文均由脚本断言为原文逐字子串，并记录字符偏移（`review_report.json.evidence.locator`）。

## ⑤ 注意点与局限

* **F1（major）** 表 1 末行把 `nu=2.22e-3 / tau+=0.5067` 与 `s+=1.9947 / guo=0.0063` 写在同一行。
  重测：campaign nu=4.444e-4（tau+=0.50133）下 guo_sp = 0.006258（= 报告的 0.63% ✓）；
  而按行内 nu=2.22e-3（tau+=0.50666, s+=1.97371）实测 guo_sp = 0.030659（3.07%）。
  结论对、标注错：照行取参会差 4.9 倍。
* **F2（major）** §6 表头是"是否 <3 %"，而"壁面原点（halfway）…5.5 %…**是**"用"(几何量)"事后改判据。
* **F3（minor）** 拟合式 `2.11 - 1.045 s+` 在 s+=1.9763 处偏 61.6%、在 s+=1.9947 处偏 305%（预测 0.0255 vs 实测 0.0063）。
* **F4（minor）** 表 3 把解析 u_max=0.896 与 `L2 = nan` 并置未标注：复现得 `u_max_mean=nan`、
  `u_max_analytic=0.896484`；恒等式 u_tau·Re/2 实为 0.900，0.896 是 y=7.5 上的离散解析极大。
* **F5（minor）** §7 复跑指针 `artifacts/turbulent_channel3d_verification/` 未随仓交付（树内不存在）。
* **F6（informational）** §5-1 的 42% 待办已由 merge #927 修复：现测
  `u_tau_wall_exchange=0.025145` vs `body_force=0.025`（0.6%）。
* 本审局限：重测走被审模块 API（重测非重实现，kernel 共模误差看不见）；复现跑在 main 的后续状态
  （测试 21 条 vs 报告 18 条）；§5-3 壁面湍流锚与 §5-4 的 LES/统计面报告声明未做，本审不评。
* 语义保真（M6）的强模型抽样不在本单执行，本审语义判定为单席位意见。

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | 三个 JSON 均 `json.load` 通过 |
| schema_pass | ✅ | envelope 过 `schemas/kf_result.v1.schema.json`；review_events 过 `schemas/review-event.schema.json` |
| reviewer_independent | ✅ | 上下文=原文+KO+公开代码/git；未读生产者解释；prompt 未复制生产 prompt |
| upstream_packages_completed | ✅ | `docs/kf/wp-7473-01/verification.json` 全检查 pass，source_hash 三方一致 |
| do_not_mark_claims_as_verified | ✅ | 无 any verified/verification_* 字段（脚本扫描）；disposition 仅 `request-changes` |

honest 说明：本单**未**通过（disposition=request-changes）。不通过的原因不是数据造假——所有关键
数字都独立复现——而是 F1/F2 两处证据面缺陷会让下游错误使用这份报告。

## 图 1

`fig_review_force_injection.png`：guo_sp 注入率实测点（含 campaign nu=4.444e-4 的
0.006258 a）与报告拟合线的偏离——拟合在 s+>1.9 端明显高估，实测点按
1.9763 → 1.9947 单调降到 0.63%，支撑定性结论而不支撑拟合式。

---

```json
{
 "package_id": "wp-7473-04",
 "task_type": "04-independent-review",
 "report_id": "7473",
 "provenance": {
  "source_uri": "tensor://reports/7473",
  "source_field": "markdown",
  "source_hash": "sha256:c3b3d0954d289cf1f7849f83889e995c71c39bbc15122ddf9f823f5d698d0f6b",
  "producer": "m15853",
  "emitted_at": "2026-11-12T02:58:00Z",
  "notes": "独立审核 wp-7473-01；审核上下文=原文+上游 KO+公开代码/git，未读生产者解释"
 },
 "outputs": {
  "review_report.json": {
   "package_id": "wp-7473-04",
   "task_type": "04-independent-review",
   "report_id": "7473",
   "reviewed_package": "wp-7473-01",
   "review_target": "report 7473 markdown（TensorLBM 湍流槽道求解器验证欠账清偿 R1）",
   "source": {
    "uri": "tensor://reports/7473",
    "field": "markdown",
    "sha256": "sha256:c3b3d0954d289cf1f7849f83889e995c71c39bbc15122ddf9f823f5d698d0f6b",
    "sha256_hex": "c3b3d0954d289cf1f7849f83889e995c71c39bbc15122ddf9f823f5d698d0f6b",
    "chars": 5942,
    "bytes_utf8": 8934,
    "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/7473",
    "snapshot": "work/wp-7473-04/source_7473.md"
   },
   "reviewer": {
    "id": "m15853-red-team-reviewer",
    "role": "red-team-reviewer",
    "reviewer_type": "agent",
    "independent_of_producer": true,
    "independence_basis": "审核上下文只含 report 7473 原文、上游 KO（docs/kf/wp-7473-01/asset_manifest.json + verification.json）与仓内公开代码/git 历史；未读生产者的解释性叙述；产物不含生产者自评材料",
    "prompt_provenance": "审核 prompt 由本单现场指令组装，未复制生产 prompt"
   },
   "context": {
    "used": [
     "report_7473_markdown",
     "upstream_ko_wp-7473-01",
     "tensorlbm_code_and_git_history"
    ],
    "excluded": [
     "producer_explanation",
     "producer_self_assessment"
    ]
   },
   "disposition": "request-changes",
   "disposition_label": "needs-fix",
   "disposition_reason": "科学结论全部独立复现（力项 1.0000 / guo_sp 0.626% / 孪生 L2 6.76e-3 / 原点 0.4725 / 插值 2.46->3.11%），无造假迹象；但证据表有两处会误导下游的标注/判据问题（F1 表 1 末行参数自洽性、F2 §6 5.5% 判 '是'），必须在入账前修；另有 3 条 minor。故 request-changes 而非 approve。",
   "severity_summary": {
    "blocking": 0,
    "major": 2,
    "minor": 3,
    "informational": 1
   },
   "findings": [
    {
     "id": "F1",
     "severity": "major",
     "kind": "evidence-label-mismatch",
     "title": "表 1 末行的 nu/tau+ 与同一行的 s+/比率不自洽：0.63% 复现的是 campaign nu=4.44e-4，不是行内写的 2.22e-3",
     "evidence": [
      {
       "quote": "| 2.22e-3（战役 Re_tau=180 粘性） | 0.5067 | 1.9947 | **1.0000** | **0.0063** |",
       "source_field": "markdown",
       "locator": {
        "start_char": 2091,
        "end_char": 2164,
        "line": 54
       },
       "note": "§3 表 1 末行（nu=2.22e-3, tau+=0.5067, s+=1.9947, guo=0.0063）"
      },
      {
       "quote": "| A′ 战役粘性 | (8,18,8) | `nu = u_tau·h/180 = 2.22e-3`，`tau+ = 0.5067` 量级 | 同上 |",
       "source_field": "markdown",
       "locator": {
        "start_char": 879,
        "end_char": 956,
        "line": 26
       },
       "note": "§1 参数表 A′ 行（把 2.22e-3 标成战役粘性）"
      }
     ],
     "reproduction": {
      "arithmetic": {
       "tau_plus_from_0.5_plus_3nu_at_2.22e-3": 0.50666,
       "s_plus_from_1_over_tau_plus_at_2.22e-3": 1.97371,
       "nu_implied_by_s_plus_1.9947": 0.0004428,
       "campaign_nu_u_tau_h_over_re_tau": 0.0004444
      },
      "remeasure": {
       "guo_sp_at_nu_2.22e-3": 0.030659,
       "guo_sp_at_campaign_nu_4.444e-4": 0.006258,
       "trt_split_at_nu_2.22e-3": 1.000053
      }
     },
     "impact": "结论（guo_sp 在战役工作点只给 0.63% 驱动力）成立且可复现；但单元格式把两个不同粘度的数写进同一行：照行内 nu/tau+ 复跑得 3.07%，与 0.63% 差 4.9 倍。下游若按行取参会得到相反量级的缺陷评估。",
     "required_fix": "末行拆分或在 nu 单元格注明 campaign nu = u_tau*h/Re_tau = 4.444e-4（tau+=0.5013）；§1 A′ 行的 '战役粘性' 标签改成其真实出处（2.22e-3 对应 u_tau=0.05）。"
    },
    {
     "id": "F2",
     "severity": "major",
     "kind": "acceptance-criterion-relabeled",
     "title": "§6 把 5.5% 的偏差标成 '<3% = 是'，用 '(几何量)' 事后改判据",
     "evidence": [
      {
       "quote": "| 实测壁面原点（halfway，`q=0.5`） | 0.4725 | 0.5 | 5.5 %（绝对偏差 −0.0275 格） | 是（几何量） |",
       "source_field": "markdown",
       "locator": {
        "start_char": 2625,
        "end_char": 2700,
        "line": 67
       },
       "note": "§6 行：5.5% 却打 '是（几何量）'"
      },
      {
       "quote": "三条 `否` 都对应明确的未清偿项，不是测量噪声：两条已写成会红的冻结测试，一条写进待办。",
       "source_field": "markdown",
       "locator": {
        "start_char": 5446,
        "end_char": 5491,
        "line": 124
       },
       "note": "§6 末句：只承认三条 否"
      }
     ],
     "reproduction": {
      "abs_dev": 0.0275,
      "pct_of_0.5": 5.5,
      "threshold_in_column_header": 3.0
     },
     "impact": "验收列的表头是 '是否 <3 %'，该单元格 5.5% 判 '是' 与表头矛盾；把 '几何量' 免检写进结论等于事后放宽预声明判据。仓内其余 >3% 项都诚实打了 '否'，故这是单点判据污染，但它落在验收列上，会抬高整表通过率。",
     "required_fix": "该格改 '否'（保留绝对量解释），或在 §6 开头预声明 '几何量按绝对格数判定 (<0.05 格)'；二者择一，且不得在看到结果后追加。"
    },
    {
     "id": "F3",
     "severity": "minor",
     "kind": "model-overreach",
     "title": "引用的线性拟合 2.11 - 1.045 s+ 在其物理相关端（高 s+）失效",
     "evidence": [
      {
       "quote": "`guo_sp` 的注入率近似 `2.11 - 1.045·s+`：`s+ → 2`（即 `tau+ → 1/2`，战役的真实工作点）",
       "source_field": "markdown",
       "locator": {
        "start_char": 2166,
        "end_char": 2233,
        "line": 56
       },
       "note": "§3 拟合句"
      }
     ],
     "reproduction": {
      "residuals_from_own_rows": {
       "1.9763": {
        "reported": 0.0277,
        "fit": 0.04477,
        "rel_dev_pct": 61.61
       },
       "1.7857": {
        "reported": 0.2451,
        "fit": 0.24394,
        "rel_dev_pct": 0.47
       },
       "1.6129": {
        "reported": 0.4359,
        "fit": 0.42452,
        "rel_dev_pct": 2.61
       },
       "1.1628": {
        "reported": 0.9083,
        "fit": 0.89487,
        "rel_dev_pct": 1.48
       },
       "0.9091": {
        "reported": 1.1601,
        "fit": 1.15999,
        "rel_dev_pct": 0.01
       },
       "1.9947": {
        "reported": 0.0063,
        "fit": 0.02554,
        "rel_dev_pct": 305.37
       }
      },
      "fit_at_campaign_s_plus_1.9947": 0.02554,
      "measured_at_campaign_s_plus_1.99468": 0.006258
     },
     "impact": "'s+ -> 2 注入趋于 0' 由实测点（0.0277 / 0.0063）支持；但拟合式在 s+=1.9763 处偏 61.6%、在 s+=1.9947 处偏 305%（预测约 4 倍于实测），不能当外推模型用。",
     "required_fix": "拟合限定 s+ in [0.9, 1.8] 并注明端部由实测点给出，或改为实测表 + 单调性说明。"
    },
    {
     "id": "F4",
     "severity": "minor",
     "kind": "evidence-ambiguity",
     "title": "表 3 负控格把解析 u_max=0.896 与 NaN 仿真输出并置且未标注；§1 又把 0.896 说成恒等式 u_tau*Re/2 的值（恒等式给 0.900）",
     "evidence": [
      {
       "quote": "| 沿用战役参数（`u_max_target=None`）的层流孪生 | `u_max = 0.896`，`Ma = 1.55`，`L2 = nan` | 旧标定路径在战役 `Re_tau` 下**必然发散** |",
       "source_field": "markdown",
       "locator": {
        "start_char": 3027,
        "end_char": 3134,
        "line": 77
       },
       "note": "§3 表 3 负控行"
      },
      {
       "quote": "`u_max = u_tau·Re_tau/2` 是这组参数化下的恒等式：`Re_tau=180, u_tau=0.01` 给出 `u_max=0.896`，",
       "source_field": "markdown",
       "locator": {
        "start_char": 1188,
        "end_char": 1267,
        "line": 31
       },
       "note": "§1 恒等式句"
      }
     ],
     "reproduction": {
      "legacy_run_u_max_mean": "nan",
      "legacy_run_u_max_analytic": 0.896484,
      "identity_u_max": 0.9,
      "Ma_at_identity": 1.5588,
      "why_0.896": "halfway 壁面原点 0.5 使最近节点落在 y=7.5 而非 H/2=8，离散解析极大 = a*7.5*8.5/(2nu) = 0.896484"
     },
     "impact": "读者可由该格误以为发散运行产出了 u_max=0.896（复现显示仿真场是 NaN，u_max_mean=nan）。数值本身没错，标注缺失。",
     "required_fix": "该格把 0.896 标为 'analytic max on staggered grid'，Ma 用 1.559（或注明 1.55 由 0.896 折算）；§1 区分连续恒等式 0.900 与离散 0.896。"
    },
    {
     "id": "F5",
     "severity": "minor",
     "kind": "reproducibility-pointer",
     "title": "§7 的一键复跑指针指向未随仓交付的 artifacts/ 目录",
     "evidence": [
      {
       "quote": "* 工件：`artifacts/turbulent_channel3d_verification/{run_probe.py,results.json,fig1_force_source.png,fig2_laminar_twin.png}`",
       "source_field": "markdown",
       "locator": {
        "start_char": 5717,
        "end_char": 5838,
        "line": 130
       },
       "note": "§7 工件指针"
      },
      {
       "quote": "`stress_fit`），\"三者的相互吻合是战役的自洽门\"。本次验证只用**闭式解**做锚，不做求解器互比。",
       "source_field": "markdown",
       "locator": {
        "start_char": 645,
        "end_char": 700,
        "line": 19
       },
       "note": "文首 '所有数字由 ... 程序化生成'"
      }
     ],
     "reproduction": {
      "checked": "ls /root/tensor-ecosystem/TensorLBM/artifacts/turbulent_channel3d_verification -> No such file or directory",
      "consequence": "§7 的复核命令在交付树内不可执行；本审用自写探针重导了全部关键数（work/wp-7473-04/*.py）"
     },
     "impact": "结论仍可复现（本次已独立重测），但 '无手抄/一键复跑' 的可审计性依赖一个仓外目录。",
     "required_fix": "把 run_probe.py + results.json 纳入仓（或给出带 sha256 的工件清单），保持 §7 指针可解析。"
    },
    {
     "id": "F6",
     "severity": "informational",
     "kind": "status-stale",
     "title": "§5-1 的 wall_exchange 42% 待办已由后续合入修复，报告/台账需注明状态",
     "evidence": [
      {
       "quote": "   `u_tau_wall_exchange = 0.03556`，而 `body_force` 路线 = 0.025（孪生自身 `u_tau`），",
       "source_field": "markdown",
       "locator": {
        "start_char": 3941,
        "end_char": 4016,
        "line": 93
       },
       "note": "§5-1 观测"
      },
      {
       "quote": "   而非每步公式。本单**未修**（超出最小改动范围），已固化为待办：",
       "source_field": "markdown",
       "locator": {
        "start_char": 4135,
        "end_char": 4171,
        "line": 96
       },
       "note": "§5-1 '本单未修'"
      }
     ],
     "reproduction": {
      "current_main_u_tau_wall_exchange": 0.025145,
      "current_main_u_tau_body_force": 0.025,
      "rel_dev_pct": 0.58,
      "fix_commit": "b3470562 merge #927 (m6442) — 'must not be divided by the (shorter) averaging window' + test_production_run_does_not_book_spinup_wall_flux",
      "test_suite_current_main": "21 passed in 41.68s（报告：18 条）"
     },
     "impact": "不是报告缺陷（当时确实未修，根因判断正确）。但下游若照 '未清偿项' 记账会重复劳动；需标注已由 #927 关闭。",
     "required_fix": "§5-1 与 §6 末行补一句状态（由 #927 关闭，实测 0.6%），或由知识台账记一条 superseding 关系。"
    }
   ],
   "claim_assessments": [
    {
     "claim_id": "R1-C1-default-flip",
     "text": "模块默认 force_scheme 由 guo_sp 改为 trt_split，并新增 validate() 白名单。",
     "status": "supported",
     "evidence": [
      {
       "quote": "| 1 | `force_scheme` 默认 `\"guo_sp\"` → **`\"trt_split\"`**，并把注释里被写反的结论改正 | 表 1：`trt_split` 在全部 `tau+` 上 `dU/dt = a`（≤0.06 %）；`guo_sp` 是受 τ 调制的错解 |",
       "source_field": "markdown",
       "locator": {
        "start_char": 3284,
        "end_char": 3426,
        "line": 84
       },
       "note": "§4 改动表第 1 行"
      },
      {
       "quote": "| 2 | `validate()` 新增 `force_scheme` 白名单 | 原实现里拼错的值会**静默落到 else 分支**（等价于 `trt_split`），不可审计 |",
       "source_field": "markdown",
       "locator": {
        "start_char": 3427,
        "end_char": 3519,
        "line": 85
       },
       "note": "§4 改动表第 2 行：改白名单的理由"
      }
     ],
     "independent_check": {
      "method": "git 历史（外部工件，非生产者叙述）",
      "observed": "merge #891 (m6230) 引入模块 832 行且 force_scheme 默认 guo_sp；merge #894 (m6291) 首次新增 tests/test_turbulent_channel3d.py、默认改 trt_split、validate() 增加白名单",
      "commands": [
       "git -C /root/tensor-ecosystem/TensorLBM show 520d3282:src/tensorlbm/turbulence/turbulent_channel3d.py | wc -l  # 832",
       "git -C /root/tensor-ecosystem/TensorLBM show 520d3282:src/tensorlbm/turbulence/turbulent_channel3d.py | grep -n 'force_scheme: str'  # 132: guo_sp",
       "git -C /root/tensor-ecosystem/TensorLBM log --diff-filter=A -- tests/test_turbulent_channel3d.py  # fa86281d merge #894"
      ]
     }
    },
    {
     "claim_id": "R1-C2-trt-split-exact",
     "text": "trt_split 在全部扫描的 tau+ 上给出 (dU/dt)/a = 1（≤0.06%）。",
     "status": "supported",
     "evidence": [
      {
       "quote": "| 0.0020 | 0.5060 | 1.9763 | **1.0001** | 0.0277 |",
       "source_field": "markdown",
       "locator": {
        "start_char": 1836,
        "end_char": 1886,
        "line": 49
       },
       "note": "表 1 首行"
      },
      {
       "quote": "tau_w = rho * a * h,   u_tau = sqrt(a h),   a = 2 u_tau^2 / H,   nu = u_tau h / Re_tau",
       "source_field": "markdown",
       "locator": {
        "start_char": 488,
        "end_char": 574,
        "line": 15
       },
       "note": "§1 动量平衡"
      }
     ],
     "independent_check": {
      "method": "module API 重测（8x18x8，a=1e-4，12 步，体相 x 6..11 平均）",
      "observed": {
       "nu_0.002": 1.000117,
       "nu_0.02": 0.999987,
       "nu_0.04": 0.999961,
       "nu_0.12": 0.99983,
       "nu_0.2": 0.999408,
       "campaign_nu": 1.000014,
       "campaign_nu_120_steps": 0.999883
      },
      "max_abs_dev_from_1": 0.0005920000000000369
     }
    },
    {
     "claim_id": "R1-C3-guo-sp-underdrive",
     "text": "guo_sp 在战役粘性下只注入 0.63% 的驱动力（锚 A 对力项缺陷有 >150x 鉴别力）。",
     "status": "supported",
     "evidence": [
      {
       "quote": "时**注入量趋于 0**。在战役粘性下它只给出 **0.63 %** 的驱动力。",
       "source_field": "markdown",
       "locator": {
        "start_char": 2234,
        "end_char": 2274,
        "line": 57
       },
       "note": "§3 表 1 结论句"
      },
      {
       "quote": "| 2.22e-3（战役 Re_tau=180 粘性） | 0.5067 | 1.9947 | **1.0000** | **0.0063** |",
       "source_field": "markdown",
       "locator": {
        "start_char": 2091,
        "end_char": 2164,
        "line": 54
       },
       "note": "§3 表 1 末行"
      }
     ],
     "independent_check": {
      "method": "module API 重测 campaign nu = u_tau*h/Re_tau = 0.01*8/180",
      "observed": {
       "nu": 0.00044444444444444447,
       "tau_plus": 0.501333,
       "s_plus": 1.994681,
       "guo_sp_ratio": 0.006258,
       "trt_split_ratio": 1.000014,
       "discrimination_ratio": 159.8
      },
      "note": "0.006258 vs 报告 0.0063 —— 数值一致。但表 1 末行的 nu/tau+ 单元格与同一行的 s+/比率不自洽，见 F1。"
     }
    },
    {
     "claim_id": "R1-C4-laminar-twin",
     "text": "重标定后的层流孪生在 halfway 下 L2=6.76e-3、峰值比 0.99065、实测壁面原点 0.4725（偏移 -0.0275 格）。",
     "status": "supported",
     "evidence": [
      {
       "quote": "| 层流孪生 L2（halfway） | 6.76e-3 | — | 0.68 % | 是 |",
       "source_field": "markdown",
       "locator": {
        "start_char": 2456,
        "end_char": 2503,
        "line": 64
       },
       "note": "§3 表 2"
      },
      {
       "quote": "| 层流孪生峰值比 `u_max^sim/u_max^exact` | 0.99065 | 1 | 0.94 % | 是 |",
       "source_field": "markdown",
       "locator": {
        "start_char": 2562,
        "end_char": 2624,
        "line": 66
       },
       "note": "§3 表 2"
      }
     ],
     "independent_check": {
      "method": "run_laminar_poiseuille(cfg(8,18,8,Re_tau=180,u_tau=0.01), steps=800)",
      "observed": {
       "relative_l2_error": 0.00676,
       "peak_ratio": 0.99064,
       "wall_origin_measured": 0.4725,
       "wall_origin_shift": -0.0275,
       "tau_plus": 0.65
      }
     }
    },
    {
     "claim_id": "R1-C5-interpolated-limitation",
     "text": "插值反弹 q=0.625 的 L2 由 2.46% 涨到 3.11%（800→2000 步），壁面原点指针恒为 ~0.495 而非几何 0.375。",
     "status": "supported",
     "evidence": [
      {
       "quote": "2. **插值反弹（`q≠0.5`）不收敛到解析抛物线**：`q=0.625` 下 L2 2.46 %→3.11 %（800→2000 步",
       "source_field": "markdown",
       "locator": {
        "start_char": 4315,
        "end_char": 4384,
        "line": 99
       },
       "note": "§5-2"
      },
      {
       "quote": "   不降），最大逐点 5.6 %，且壁面原点指针恒返回 ≈0.495 而非几何值 0.375。",
       "source_field": "markdown",
       "locator": {
        "start_char": 4385,
        "end_char": 4433,
        "line": 100
       },
       "note": "§5-2"
      }
     ],
     "independent_check": {
      "method": "run_laminar_poiseuille(cfg(wall_origin=0.375, wall_scheme=interpolated)) steps=800/2000",
      "observed": {
       "l2_800": 0.024636,
       "l2_2000": 0.031105,
       "wall_origin_800": 0.495,
       "wall_origin_2000": 0.5375
      }
     }
    },
    {
     "claim_id": "R1-C6-legacy-diverges",
     "text": "沿用战役参数（u_max_target=None）的层流孪生必然发散（L2=nan，u_max=0.896，Ma=1.55）。",
     "status": "partially-supported",
     "evidence": [
      {
       "quote": "| 沿用战役参数（`u_max_target=None`）的层流孪生 | `u_max = 0.896`，`Ma = 1.55`，`L2 = nan` | 旧标定路径在战役 `Re_tau` 下**必然发散** |",
       "source_field": "markdown",
       "locator": {
        "start_char": 3027,
        "end_char": 3134,
        "line": 77
       },
       "note": "§3 表 3 负控"
      }
     ],
     "unresolved_reason": "NaN 与 u_max=0.896 同格并置但未标注 u_max 是解析值：复现得 u_max_mean=nan、u_max_analytic=0.896484；'必然发散' 由单次配置外推。见 F4。",
     "independent_check": {
      "method": "run_laminar_poiseuille(cfg(Re_tau=180,u_tau=0.01), steps=800, u_max_target=None)",
      "observed": {
       "u_max_mean": "nan",
       "u_max_analytic": 0.896484,
       "relative_l2_error": "nan",
       "nu": 0.000444,
       "tau_plus": 0.501333
      }
     }
    },
    {
     "claim_id": "R1-C7-wall-exchange-anomaly",
     "text": "孪生里 wall_exchange 路线的 u_tau=0.03556 相对 body_force 的 0.025 高估 42%，原因是聚合窗口口径而非每步公式；本单未修。",
     "status": "supported",
     "evidence": [
      {
       "quote": "   `u_tau_wall_exchange = 0.03556`，而 `body_force` 路线 = 0.025（孪生自身 `u_tau`），",
       "source_field": "markdown",
       "locator": {
        "start_char": 3941,
        "end_char": 4016,
        "line": 93
       },
       "note": "§5-1 观测"
      },
      {
       "quote": "   而非每步公式。本单**未修**（超出最小改动范围），已固化为待办：",
       "source_field": "markdown",
       "locator": {
        "start_char": 4135,
        "end_char": 4171,
        "line": 96
       },
       "note": "§5-1 未修声明"
      },
      {
       "quote": "   复核 `run_laminar_poiseuille` 中 `flux += _wall_flux_accum` 的窗口边界",
       "source_field": "markdown",
       "locator": {
        "start_char": 4172,
        "end_char": 4237,
        "line": 97
       },
       "note": "§5-1 待办"
      }
     ],
     "independent_check": {
      "method": "根因算术 + 当前 main 复现",
      "observed": {
       "pre_fix_arithmetic": "不带半步复位时累加器含预热段，tau_w 被放大 nsteps//window = 2 倍，u_tau x sqrt(2) = 1.414 -> +41.4%（报告 42%）",
       "current_main_u_tau_wall_exchange": 0.025145,
       "current_main_u_tau_body_force": 0.025,
       "fix_landed_in": "merge #927 (m6442)：step == nsteps//2 复位 + 以实测 flux_steps 作分母"
      },
      "note": "根因判断正确；但 '未修' 状态已过期，见 F6。"
     }
    },
    {
     "claim_id": "R1-C8-merge-without-tests",
     "text": "模块随 merge #891 合入 main 时 832 行、无任何 pytest 用例与验证文档。",
     "status": "supported",
     "evidence": [
      {
       "quote": "> **合入时无任何 pytest 用例、无验证文档**，benchmark 仍停留在 `benchmarks/pending/channel_turb_3d/`）。",
       "source_field": "markdown",
       "locator": {
        "start_char": 126,
        "end_char": 209,
        "line": 4
       },
       "note": "文首对象说明"
      }
     ],
     "independent_check": {
      "method": "git 历史",
      "observed": "520d3282 (#891) 引入 832 行模块；tests/test_turbulent_channel3d.py 首次出现在 fa86281d (#894)"
     }
    },
    {
     "claim_id": "R1-C9-not-done-scope",
     "text": "本单只验证层流锚；壁面解析湍流（MKM/Reichardt）、stress_fit、Smagorinsky、turbulence_energy 未做。",
     "status": "supported",
     "evidence": [
      {
       "quote": "3. 本单只验证**层流锚**。Re_tau=180/395 的壁面解析湍流（MKM DNS、Reichardt 复合律、",
       "source_field": "markdown",
       "locator": {
        "start_char": 4581,
        "end_char": 4642,
        "line": 104
       },
       "note": "§5-3"
      },
      {
       "quote": "   `u+ = log(y+)/κ + B`）需要 `benchmarks/pending/channel_turb_3d/` 的完整战役，",
       "source_field": "markdown",
       "locator": {
        "start_char": 4643,
        "end_char": 4714,
        "line": 105
       },
       "note": "§5-3"
      }
     ],
     "independent_check": {
      "method": "范围声明核对（不评估未做项）",
      "observed": "报告明确列出未做项并给出原因，未把未做项写成结论"
     }
    }
   ],
   "overstated_claims": [
    "§6 '壁面原点（halfway） ... 5.5 % ... 是' —— 与同列表头 '<3 %' 冲突（F2）",
    "§3 'guo_sp 的注入率近似 2.11 - 1.045·s+' —— s+>1.9 端偏 61.6%~305%，非可用近似（F3）",
    "§1 'u_max = u_tau·Re_tau/2 是这组参数化下的恒等式 ... 给出 u_max=0.896' —— 恒等式给 0.900，0.896 是离散 y=7.5 上的解析极大（F4）",
    "§3 表 3 'u_max = 0.896, Ma = 1.55, L2 = nan' —— 未标注 0.896 为解析值，仿真实测为 NaN（F4）",
    "§3 '使整个战役驱动力失效' —— 就 guo_sp 而言成立（0.63%），但报告内只有单步/均匀流探针，战役侧实跑证据未给出；因果链在报告内只到 '默认值错' 这一环"
   ],
   "remediation_required": [
    {
     "finding": "F1",
     "action": "表 1 末行拆行或把 nu 标注改为 4.444e-4（tau+=0.5013）；§1 A′ 行改标真实出处",
     "blocking_for": "evidence-table reproducibility"
    },
    {
     "finding": "F2",
     "action": "5.5% 格改 '否'，或在 §6 预声明几何量的绝对判据（不得事后追加）",
     "blocking_for": "acceptance-criteria integrity"
    },
    {
     "finding": "F3",
     "action": "拟合式限定区间 + 端部用实测点"
    },
    {
     "finding": "F4",
     "action": "标注 0.896 为离散解析极大；Ma 用 1.559 或注明折算"
    },
    {
     "finding": "F5",
     "action": "工件入仓或给 sha256 清单，保持 §7 指针可解析"
    },
    {
     "finding": "F6",
     "action": "§5-1 状态更新为已由 #927 关闭（实测 0.6%）"
    }
   ],
   "reproduction": {
    "env": "CPU float32 单线程；python 3.11 + torch 2.7.1；TensorLBM @ /root/tensor-ecosystem/TensorLBM (main, da452346)",
    "scripts": [
     "work/wp-7473-04/independent_probe.py",
     "work/wp-7473-04/independent_twin.py",
     "work/wp-7473-04/make_figure.py",
     "work/wp-7473-04/build_review.py"
    ],
    "artifacts": [
     "work/wp-7473-04/probe_2026-11-12.json",
     "work/wp-7473-04/twin_repro.json",
     "work/wp-7473-04/fig_review_force_injection.png"
    ],
    "one_liner": "bash work/wp-7473-04/repro.sh",
    "test_suite_current_main": "21 passed in 41.68s"
   },
   "limitations_of_this_review": [
    "重测使用被审模块 API：模块 kernel 若有共模误差，本审不具鉴别力（未做独立求解器对冲）",
    "复现运行在 TensorLBM main 的后续状态（da452346，含 #927 之后的改动）；被审报告的时点状态是 #894，测试数 21 vs 18 的差异由此而来；表 1/表 2 数值逐项对上，不影响可复现性结论",
    "未评估 §5-3 壁面解析湍流锚、§5-4 stress_fit/Smagorinsky/turbulence_energy —— 报告声明未做，本审只评声明的诚实性",
    "M6 semantic fidelity 的强模型抽样不在本单执行；本审语义判定为单席位意见",
    "未检查并行/GPU 路径与不同架构下的数值差异（报告声明 CPU 单线程）"
   ],
   "acceptance_self_check": {
    "valid_json": "pass",
    "schema_pass": "pass（result envelope 用 schemas/kf_result.v1.schema.json 校验）",
    "reviewer_independent": "pass（上下文=原文+上游 KO+公开代码；未读生产者解释）",
    "upstream_packages_completed": "pass（docs/kf/wp-7473-01/verification.json 全部检查 pass，source_hash 三方一致）",
    "do_not_mark_claims_as_verified": "pass（本包无 verified/verification_* 字段；验证级别留给平台门）"
   }
  },
  "review_events.json": [
   {
    "id": "tkr:wp-7473-01:review-wp-7473-04",
    "object_ref": "wp-7473-01",
    "object_version": "report-7473@sha256:c3b3d0954d289cf1f7849f83889e995c71c39bbc15122ddf9f823f5d698d0f6b",
    "decision": "request-changes",
    "reviewer": {
     "id": "m15853-red-team-reviewer",
     "reviewer_type": "agent",
     "role": "red-team-reviewer"
    },
    "reviewed_at": "2026-11-12T02:58:00Z",
    "policy_version": "ke-review-v0.1",
    "rationale": "结论可复现但证据表有两处需修的标注/判据问题（F1/F2）；见 review_report.json",
    "findings": [
     {
      "severity": "major",
      "finding": "F1 表 1 末行 nu/tau+ 与同格 s+/比率不自洽（0.63% 属 campaign nu=4.444e-4；行内 nu=2.22e-3 实测 3.07%）",
      "related_claim_refs": [
       "R1-C3-guo-sp-underdrive"
      ]
     },
     {
      "severity": "major",
      "finding": "F2 §6 把 5.5% 偏差标成 '<3% = 是'，事后用 '(几何量)' 改判据",
      "related_claim_refs": [
       "R1-C4-laminar-twin"
      ]
     },
     {
      "severity": "minor",
      "finding": "F3 拟合式 2.11-1.045 s+ 在 s+>1.9 端偏 61.6%~305%",
      "related_claim_refs": [
       "R1-C3-guo-sp-underdrive"
      ]
     },
     {
      "severity": "minor",
      "finding": "F4 表 3 把解析 u_max=0.896 与 NaN 仿真并置未标注；§1 恒等式实为 0.900",
      "related_claim_refs": [
       "R1-C6-legacy-diverges"
      ]
     },
     {
      "severity": "minor",
      "finding": "F5 §7 复跑指针指向未随仓交付的 artifacts/ 目录"
     },
     {
      "severity": "informational",
      "finding": "F6 §5-1 wall_exchange 42% 已由 merge #927 修复（实测 0.6%），'未修' 状态过期",
      "related_claim_refs": [
       "R1-C7-wall-exchange-anomaly"
      ]
     }
    ],
    "conditions": [
     "F1 修正表 1 末行/§1 A′ 标注后可复核 0.63% 的可追踪性",
     "F2 改判 '否' 或预声明几何量判据后重评 §6 列"
    ]
   }
  ]
 },
 "claims": [
  {
   "claim_id": "R1-C1-default-flip",
   "text": "模块默认 force_scheme 由 guo_sp 改为 trt_split，并新增 validate() 白名单。",
   "status": "supported",
   "evidence": [
    {
     "quote": "| 1 | `force_scheme` 默认 `\"guo_sp\"` → **`\"trt_split\"`**，并把注释里被写反的结论改正 | 表 1：`trt_split` 在全部 `tau+` 上 `dU/dt = a`（≤0.06 %）；`guo_sp` 是受 τ 调制的错解 |",
     "source_field": "markdown",
     "note": "§4 改动表第 1 行"
    },
    {
     "quote": "| 2 | `validate()` 新增 `force_scheme` 白名单 | 原实现里拼错的值会**静默落到 else 分支**（等价于 `trt_split`），不可审计 |",
     "source_field": "markdown",
     "note": "§4 改动表第 2 行：改白名单的理由"
    }
   ]
  },
  {
   "claim_id": "R1-C2-trt-split-exact",
   "text": "trt_split 在全部扫描的 tau+ 上给出 (dU/dt)/a = 1（≤0.06%）。",
   "status": "supported",
   "evidence": [
    {
     "quote": "| 0.0020 | 0.5060 | 1.9763 | **1.0001** | 0.0277 |",
     "source_field": "markdown",
     "note": "表 1 首行"
    },
    {
     "quote": "tau_w = rho * a * h,   u_tau = sqrt(a h),   a = 2 u_tau^2 / H,   nu = u_tau h / Re_tau",
     "source_field": "markdown",
     "note": "§1 动量平衡"
    }
   ]
  },
  {
   "claim_id": "R1-C3-guo-sp-underdrive",
   "text": "guo_sp 在战役粘性下只注入 0.63% 的驱动力（锚 A 对力项缺陷有 >150x 鉴别力）。",
   "status": "supported",
   "evidence": [
    {
     "quote": "时**注入量趋于 0**。在战役粘性下它只给出 **0.63 %** 的驱动力。",
     "source_field": "markdown",
     "note": "§3 表 1 结论句"
    },
    {
     "quote": "| 2.22e-3（战役 Re_tau=180 粘性） | 0.5067 | 1.9947 | **1.0000** | **0.0063** |",
     "source_field": "markdown",
     "note": "§3 表 1 末行"
    }
   ]
  },
  {
   "claim_id": "R1-C4-laminar-twin",
   "text": "重标定后的层流孪生在 halfway 下 L2=6.76e-3、峰值比 0.99065、实测壁面原点 0.4725（偏移 -0.0275 格）。",
   "status": "supported",
   "evidence": [
    {
     "quote": "| 层流孪生 L2（halfway） | 6.76e-3 | — | 0.68 % | 是 |",
     "source_field": "markdown",
     "note": "§3 表 2"
    },
    {
     "quote": "| 层流孪生峰值比 `u_max^sim/u_max^exact` | 0.99065 | 1 | 0.94 % | 是 |",
     "source_field": "markdown",
     "note": "§3 表 2"
    }
   ]
  },
  {
   "claim_id": "R1-C5-interpolated-limitation",
   "text": "插值反弹 q=0.625 的 L2 由 2.46% 涨到 3.11%（800→2000 步），壁面原点指针恒为 ~0.495 而非几何 0.375。",
   "status": "supported",
   "evidence": [
    {
     "quote": "2. **插值反弹（`q≠0.5`）不收敛到解析抛物线**：`q=0.625` 下 L2 2.46 %→3.11 %（800→2000 步",
     "source_field": "markdown",
     "note": "§5-2"
    },
    {
     "quote": "   不降），最大逐点 5.6 %，且壁面原点指针恒返回 ≈0.495 而非几何值 0.375。",
     "source_field": "markdown",
     "note": "§5-2"
    }
   ]
  },
  {
   "claim_id": "R1-C6-legacy-diverges",
   "text": "沿用战役参数（u_max_target=None）的层流孪生必然发散（L2=nan，u_max=0.896，Ma=1.55）。",
   "status": "partially-supported",
   "evidence": [
    {
     "quote": "| 沿用战役参数（`u_max_target=None`）的层流孪生 | `u_max = 0.896`，`Ma = 1.55`，`L2 = nan` | 旧标定路径在战役 `Re_tau` 下**必然发散** |",
     "source_field": "markdown",
     "note": "§3 表 3 负控"
    }
   ],
   "unresolved_reason": "NaN 与 u_max=0.896 同格并置但未标注 u_max 是解析值：复现得 u_max_mean=nan、u_max_analytic=0.896484；'必然发散' 由单次配置外推。见 F4。"
  },
  {
   "claim_id": "R1-C7-wall-exchange-anomaly",
   "text": "孪生里 wall_exchange 路线的 u_tau=0.03556 相对 body_force 的 0.025 高估 42%，原因是聚合窗口口径而非每步公式；本单未修。",
   "status": "supported",
   "evidence": [
    {
     "quote": "   `u_tau_wall_exchange = 0.03556`，而 `body_force` 路线 = 0.025（孪生自身 `u_tau`），",
     "source_field": "markdown",
     "note": "§5-1 观测"
    },
    {
     "quote": "   而非每步公式。本单**未修**（超出最小改动范围），已固化为待办：",
     "source_field": "markdown",
     "note": "§5-1 未修声明"
    },
    {
     "quote": "   复核 `run_laminar_poiseuille` 中 `flux += _wall_flux_accum` 的窗口边界",
     "source_field": "markdown",
     "note": "§5-1 待办"
    }
   ]
  },
  {
   "claim_id": "R1-C8-merge-without-tests",
   "text": "模块随 merge #891 合入 main 时 832 行、无任何 pytest 用例与验证文档。",
   "status": "supported",
   "evidence": [
    {
     "quote": "> **合入时无任何 pytest 用例、无验证文档**，benchmark 仍停留在 `benchmarks/pending/channel_turb_3d/`）。",
     "source_field": "markdown",
     "note": "文首对象说明"
    }
   ]
  },
  {
   "claim_id": "R1-C9-not-done-scope",
   "text": "本单只验证层流锚；壁面解析湍流（MKM/Reichardt）、stress_fit、Smagorinsky、turbulence_energy 未做。",
   "status": "supported",
   "evidence": [
    {
     "quote": "3. 本单只验证**层流锚**。Re_tau=180/395 的壁面解析湍流（MKM DNS、Reichardt 复合律、",
     "source_field": "markdown",
     "note": "§5-3"
    },
    {
     "quote": "   `u+ = log(y+)/κ + B`）需要 `benchmarks/pending/channel_turb_3d/` 的完整战役，",
     "source_field": "markdown",
     "note": "§5-3"
    }
   ]
  }
 ]
}
```
