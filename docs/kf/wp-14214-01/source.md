# W23 论文生产线研究总结：增量证据、双轨重标、research_plan 销项推进与成稿门加固

**任务**：paper-mine-w23（首席研究员选题）· 仓 `TensorPapers` · 2026-11-11
**窗口**：`id > 13481（W22 冻结上界，不重叠）且 id <= 14210（本波开工快照）`；报告 **430** 篇、图 **994** 张、判据行 **3624** 行；EVO-1 盲评剔除 **0** 篇。

## ① 案例介绍（研究域与证据面）

本波不是写作波而是**证据组织波**：把论文生产线的 45 个课题按「有没有外部定量锚」重新分流，只让锚可核销的课题进顶刊轨；再以顶刊审稿人视角把每个课题拆成可派科研任务，用「任务是否产出真报告」机器判定销项。学科域覆盖阻力/推进/耐波/操纵/稳性/结构/振动噪声/绿色航行/冰区九域。

| 指标 | 数值 |
|---|---|
| 窗口报告 | 430 |
| 判词 PASS / FAIL / WITHHELD | 184 / 138 / 60 |
| 含 `<3%` 类判据行报告 | 260 |
| 平台累计发布 | 9401 |

## ② 怎么做的（方法 / 工具链）

1. **增量扫描**（`w23_extract.py`）：psql 只读直读 `tensor_reports`，窗口下界取 W22 冻结上界 13481，上界冻结为本波开工快照 14210（之后新增归 W24，不回头改）；EVO-1 只看计数不读正文。
2. **锚目录重建**（`w23_anchors.py`）：24 条外部锚、A/B/C 三级可达性复检（23 条可达），作为双轨重标与成稿门的唯一锚来源。
3. **双轨重标**（`w23_tracks.py`）：45 课题逐条判 external/internal，external 必须挂 ≥1 个可达锚；internal（ledger/gate/canon/台账类）目标产物=tech report。
4. **销项收割**（`w23_plan.py`）：任务销项 = 至少产出 1 篇报告（判据达标或 honest FAIL 均算）；承接 = 重试单 goal 逐字点名前身；工件在位性按 research_plan.md 表格**列名定位**后在仓内 main 检出核验。
5. **成稿门加固**（`w23_draftgate.py`）：W22 四门 + 本波新增 G5 五门证据质量门，全机裁。
6. **派单**（`w23_payloads.py` + `w23_dispatch.py`）：goal 三要素 + 数字归属机检 + 全库查重 + POST 后 DB 回读。

## ③ 计算结果（数字表，程序化注入）

**research_plan 销项推进**

| 指标 | W22 | W23 | 变化 |
|---|---|---|---|
| 计划内 exp 任务 | 59 | 73 | +14 |
| 已销项 | 51 | 63 | +12 |
| 封口计划 | 24 | 33 | +9 |
| 承接 / 未销项 | — | 7 / 3 | — |

**计划工件在位核**：在位 48 / 缺失 28（口径限制：只查 main 检出，分支未合并工件计为缺失，故作阻断依据、不作达标依据）。

**成稿门判决**（九门全真才放行）

- 放行 **2**：`damaged-stability-flooding-td`、`wind-load-blendermann-weather-criterion`
- 阻断 **23**；主要阻断门计数：G5e_anchor_task_not_fail=11、G5c_artifact_ratio_ge_0.5=8、G5a_pass_report_ge1=11、G5d_fail_not_dominant=8、G5b_pass_rows_ge3=8、G4_no_draft=9、G2_plan_closed=2

**派单回执**（DB 回读）

| task_key | mission | 状态 | 模型 | repo |
|---|---|---|---|---|
| `paper-exp-ice-coupled-6dof-3` | None | validated-dry | deepseek-v4-flash | TensorFEM |
| `paper-exp-ice-nav-operational-chain-4` | None | validated-dry | deepseek-v4-flash | ship-performance-platform |
| `paper-exp-ship-hull-girder-structure-2` | None | validated-dry | deepseek-v4-flash | TensorFEM |
| `paper-exp-undex-shock-chain-2` | None | validated-dry | deepseek-v4-flash | TensorFEM |
| `paper-exp-green-shipping-iso19030-2` | None | validated-dry | deepseek-v4-flash | ship-performance-platform |
| `paper-exp-composite-laminate-verification-2` | None | validated-dry | deepseek-v4-flash | TensorFEM |
| `paper-exp-resistance-ittc-traceable-chain-2` | None | validated-dry | deepseek-v4-flash | ship-performance-platform |
| `paper-exp-resistance-ittc-traceable-chain-3` | None | validated-dry | deepseek-v4-flash | ship-performance-platform |
| `paper-draft-damaged-stability-flooding-td` | None | validated-dry | qwen3.6-plus | TensorPapers |
| `paper-draft-wind-load-blendermann-weather-criterion` | None | validated-dry | deepseek-v4-flash | TensorPapers |
| `paper-exp-ice-coupled-6dof-3` | 15092 | claimed | deepseek-v4-flash | TensorFEM |
| `paper-exp-ice-nav-operational-chain-4` | 15093 | queued | deepseek-v4-flash | ship-performance-platform |
| `paper-exp-ship-hull-girder-structure-2` | 15094 | queued | deepseek-v4-flash | TensorFEM |
| `paper-exp-undex-shock-chain-2` | 15095 | queued | deepseek-v4-flash | TensorFEM |
| `paper-exp-green-shipping-iso19030-2` | 15096 | queued | deepseek-v4-flash | ship-performance-platform |
| `paper-exp-composite-laminate-verification-2` | 15097 | queued | deepseek-v4-flash | TensorFEM |
| `paper-exp-resistance-ittc-traceable-chain-2` | 15098 | queued | deepseek-v4-flash | ship-performance-platform |
| `paper-exp-resistance-ittc-traceable-chain-3` | 15099 | queued | deepseek-v4-flash | ship-performance-platform |
| `paper-draft-damaged-stability-flooding-td` | 15100 | queued | qwen3.6-plus | TensorPapers |
| `paper-draft-wind-load-blendermann-weather-criterion` | 15101 | queued | deepseek-v4-flash | TensorPapers |

数字归属机检：284 个数字 token 全部归类，锚行越界 token 0 个。离线机检 **PASSED 414/414**。

## ④ 结果图

- `papers/figures/w23_window_composition.png`（sha256_16 `00a0936204e0b70d`，脚本 `papers/tools/w23_figures.py`，输入 digest.json）
- `papers/figures/w23_track_split.png`（sha256_16 `d889e66d3739a24e`，脚本 `papers/tools/w23_figures.py`，输入 tracks.json）
- `papers/figures/w23_plan_progress.png`（sha256_16 `371b8fc472428b13`，脚本 `papers/tools/w23_figures.py`，输入 research_plan_ledger.json）
- `papers/figures/w23_draft_gate.png`（sha256_16 `3a48cfafc642d093`，脚本 `papers/tools/w23_figures.py`，输入 draft_gate.json）
- `papers/figures/w23_artifact_presence.png`（sha256_16 `4a1693ff2284f6e6`，脚本 `papers/tools/w23_figures.py`，输入 research_plan_ledger.json）

## ⑤ 注意点（坑与局限）

1. **目录销项 ≠ 证据合格**：6 个课题计划已封口，但 2 个判词全 FAIL/未判、4 个计划工件在 main 检出为零；W22 四门会全部放行。旗舰课题 `lbm-suboff-tau` 销项 7/9 却因 4 篇 FAIL + 最大 PASS 行 0 + 工件在位率 0.222 被 G5 阻断——本波不开特例。
2. **自审先于审人**：`w23_plan.py` 首版按 `cells[-3]` 猜列，把判据列当领域仓，导致工件在位率被系统性判成 0（48 例误判）；改列名定位后复活。同一错误若发生在评审层，会把有工件的课题误杀——已写进 KNOWN_TRAPS 口径（工具内注释 + 本节）。
3. **图件字段名坑**：`digest.json` 的判词计数在顶层而非 `counts` 嵌套，首版图 1 的 PASS 计数读成 0，已改为直读顶层键并重跑。
4. **append-only 纪律**：`w23_planmd.py` 首版覆盖了 2 个既有 research_plan.md，已 `git checkout` 回滚并改为只追加 W23 状态块；机检 ⑨ 断言「既有计划无实质删除行」。
5. **internal 轨本波 0 派单**：缺 tech report 的 4 个内部课题中 1 个受 EVO-1 阻断、3 个窗口证据为 0，不以内部轨名义凑单。

## ⑥ 误差判定（关键量 vs 基准）

| 关键量 | 基准 | 结果 | 是否 <3% |
|---|---|---|---|
| 窗口报告计数 | psql `count(*)` 直读 | 与 inventory/digest 双源一致（机检 ①②） | 是（0 误差，恒等核） |
| 任务销项计数 | DB mission→report 关联 | 账本 partition 恒等（closed+superseded+open=tasks） | 是（0 误差） |
| 数字 token 归属 | 锚目录 + specs | 284/284 归类，锚越界 0 | 是（0 误归） |
| 工件在位率 | git 检出存在性 | 48 在位 / 28 缺失（口径=main 检出，非真值下界） | 不适用（无外部基准，如实声明） |
| 图件完整性 | figures.json 登记 sha256 | 5/5 逐文件复算一致 | 是（0 误差） |

**honest FAIL 留痕**：本波未产出任何领域精度量（本波不跑仿真），故不存在「平台值 vs 外部锚」的误差判定；所有精度判定由本波派出的 8 个科研任务在下游给出，销项与判词回写 registry，不得由本波代填。

## 附：工具与工件

- 工具：`papers/tools/w23_{extract,anchors,plan,tracks,specs,payloads,dispatch,draftgate,planmd,figures,registry}.py`、`test_w23_artifacts.py`
- 数据：`papers/data/w23-2026-11-11/`；新立计划：`papers/composite-laminate-verification/research_plan.md, papers/green-shipping-iso19030/research_plan.md, papers/resistance-ittc-traceable-chain/research_plan.md, papers/ship-hull-girder-structure/research_plan.md, papers/undex-shock-chain/research_plan.md`
- registry：`papers/registry.md` W23 段（append-only）
