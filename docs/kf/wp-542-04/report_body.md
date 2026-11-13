# KF-RESULT wp-542-04

**工作包**: `wp-542-04` (`04-independent-review`) · **被审对象**: `wp-542-01` (report 542)
**审核角色**: red-team-reviewer · **结论**: **pass**（阻断项 0）

## ① 本工序做了什么

对 report 542（《FEM/DEM 能力盘点与成组任务树 — m605 进展报告》）的上游工作包 `wp-542-01`（task_type `01-asset-registration`）做独立对抗式审核：不看生产者解释，只以**报告原文 + 上游知识产物**（`kf_result.json` / `asset_manifest.json` / `verification.json`）为上下文，独立重算哈希、路径清点的召回/精确率、定位符逐字一致性、身份去重口径、报告内部数值自洽性，判定上游能否放行给下游工序。**本轮不改上游任何产物，也不把任何结论标成 verified。**

## ② 怎么做的（步骤/工具/关键设置）

1. 取原文：`GET /api/v1/tensor/reports/542` 的 `markdown` 字段落盘为 `source_snapshot.md`，重算 SHA256 与契约声明比对（C1）。
2. 取上游产物：`docs/kf/wp-542-01/*.json`，重算 `asset_manifest.json` 字节哈希与其在 `kf_result.json` 中的自声明比对（C3）。
3. 路径清点：对原文做**独立**正则抽取 `[A-Za-z0-9_./-]+\.(py|json|png|md|csv|dat)`，与 manifest 的 `path_reference` 集合做双向差集——召回（C4）/ 无捏造（C5）。
4. 定位符核验：对每条 `locator.scheme=markdown_line` 资产，检查 `quote` 是否为其**声明行**的逐字子串，且 `path_reference` 出现在同一行（C6）。
5. 身份核验：`asset_id` 唯一性（C7）、`(path, markdown_line)` 重复、basename 归一后的**真实文件数**。
6. 报告内部自洽：任务树节点/工时/并行组算术（C11-C13）；§6「无数值结果」与 §3.4/3.5 雷达分数的冲突（C15）；PASS 类结论与可解析证据的比例（C14）。
7. 全部引文由程序断言为原文逐字子串，findings 内的引文同样复查（C17）；miss 即 check fail，不做人工修补。

## ③ 产出物清单

| 文件 | 要点 |
|------|------|
| `docs/kf/wp-542-04/review_report.json` | 机读审核结论：verdict / checks / findings / limitations（本单交付物） |
| `docs/kf/wp-542-04/kf_result.json` | 结果信封（package_id / task_type / report_id / provenance / outputs） |
| `docs/kf/wp-542-04/source_snapshot.md` | 被审 markdown 字节级快照（`--offline` 复跑输入） |
| `docs/kf/wp-542-04/report_body.md` | 本报告正文（数字由脚本注入，零手抄） |
| `scripts/kf/review_wp542_04.py` | 一键复跑全部检查（见 ⑧） |
| `docs/kf/wp-542-04/figs/review_overview.png` | 三分面：解析状态分布 / 引用数与真实文件数 / L1 节点数 vs 组员数 |

## ④ 证据定位表（claim/字段 → 原文逐字引文）

> 引文由脚本断言 `quote in markdown`；行号=平台 markdown 行号（1-based）。

| # | 判定对象 | 原文引文（逐字） | 行 |
|---|----------|------------------|----|
| C1 | 原文哈希锚点（参数表首行） | `\| 冰密度 ρ_ice \| 917 kg/m³ \| dem3d.py:24 硬编码 \|` | 27 |
| C4/C5 | 路径清点：qualified 形式 | `tensorfem/shell4.py` | 31 |
| F-01 | 同一文件的 qualified 写法（别名组） | `tensorfem/cohesive.py:32` | 32 |
| F-01 | 同一文件的 unqualified 写法 | `\| cohesive.py \| 两节点cohesive界面 \| ✅有测试 \| PASS \| test_cohesive.py (6 tests) \|` | 85 |
| C4/C5 | 同一行并列两条路径 | `tensorfem/dynamics.py, explicit_dynamics.py` | 33 |
| C15 | §6「无数值结果」声明 | `本单为 **能力盘点与任务规划**，无数值计算结果，故无误差判定` | 216 |
| C15 | §3.4 量化差距断言 | `整体差距在 4-6 分（10分制）` | 126 |
| C15 | §3.4 分项评分（无评分表） | `TensorFEM 在时间积分(7)和断裂(6)方面较强，但在自适应(1)、并行(2)、工程规模(2)方面严重不足` | 124 |
| C11 | 任务树 L1 行（8 节点 / A(5),B(4),C(3)） | `\| L1 基础能力 \| 8 \| 136h \| A(5并行), B(4), C(3) \|` | 156 |
| C13 | 任务树 L2 行（重列 A/B/C） | `\| L2 验证锚 \| 4 \| 50h \| B(2), C(1), A(1) \|` | 157 |
| C12 | 任务树合计 16 节点 278h | `\| **合计** \| **16** \| **278h** \| — \|` | 159 |
| C13 | 组A 5 个任务（跨层，含 V04） | `- **立即启动（组A）**：F01, F03, F04, F05, V04 — 5个任务可并行` | 172 |
| F-03 | 只读审计的证据基础 | `1. **只读审计**：未修改任何 src/ 代码，所有论断基于源码 + 已有测试` | 194 |
| F-03 | PASS 结论下唯一的量化演示规模 | `2. **规模限制**：SI-4 演示为 smoke 级（12颗粒），非工程规模` | 195 |
| F-03 | GPU 能力自述（未验证） | `3. **GPU 未验证**：dem3d.py 声称支持 CUDA，但 cell list 可能同步阻塞` | 196 |
| F-03 | 模块自承精度不合格 | 4. **物理精度**：coupled_hull.py 的 `physical_accuracy_qualified` 硬编码为 False | 197 |
| F-06 | SIR 缩写的唯一出处 | `SIR（Suboff Icebreaking Research）` | 14 |

## ⑤ 注意点与局限

1. **上游 47/51 资产 unresolved**（resolved=1, metadata_only=3, unresolved=47）：TensorFEM/TensorDEM 源码树不在本仓边界内，故本单只裁「登记是否忠实于原文」，**不裁**「PASS 是否成立」——能力真伪属领域仓/下游取证范围。
2. **上游自门记录只作证据**：`verification.json` 的 `all_pass` 被读取但未被采纳为本单裁决（C16=`not_run`）。
3. **未读生产者解释**：上下文仅原文 + 上游三件产物，未引入任何生产者叙述性说明。
4. **未运行** TensorFEM/TensorDEM 的任何测试或算例（越界），对报告的能力论断保持 unresolved。
5. 引文行号绑定平台当前 markdown（sha256 已固定）；报告若被重新编辑，行号需重算，哈希门会先失败。
6. **同仓独立性局限**：与上游共用同一 worktree，独立性是方法学的（独立重算 + 不同检查面），非组织隔离；已在 `review_report.json` 的 `reviewer_independence` 中登记。

## ⑥ 自检（对照 acceptance 逐条）

| acceptance 项 | 结果 | 依据 |
|---------------|------|------|
| valid_json | ✅ | `json.load` 通过（review_report.json / kf_result.json） |
| schema_pass | ✅ | 信封五键齐备；`task_type` 匹配 `^[0-9]{2}(-[a-z0-9-]+)?$`；`provenance` 含 `source_hash`+`source_field` |
| reviewer_independent | ✅ | 上下文=原文+上游产物；未读生产者解释；哈希/清点/定位符独立重算（局限见 ⑤-6） |
| upstream_packages_completed | ✅ | `wp-542-01` 三件产物齐备且 manifest 哈希自洽（C3） |

**审核校验面**：13 pass / 2 fail / 2 not_run；**发现项**：阻断 0 / medium 3 / low 2 / info 1。

**如实列的未通过/未跑项**：C14（能力真伪不可由本仓校验）、C16（上游自门记录不采纳）为 `not_run`；C13（L1 并行组员数与节点数不符）与 C15（§6 与 §3.4/3.5 冲突）为 `fail`，分别对应 F-04、F-05，未做粉饰。

## ⑦ 误差判定

本单为审核工序，不产生物理计算量、**无基准量可比**，故不适用「<3%」物理误差判定；可量化的一致性指标是**精确计数**（离散比对，无浮点误差）：

- 路径清点：召回 36/36（漏登 0、误登 0）→ 偏差 **0%**；
- 定位符逐字一致：47 条 `markdown_line`，quote 不符 0、path 不符 0 → 偏差 **0%**；
- 身份口径：资产计数 51 / 路径串 36 / 归一文件 33（差 3 源于 qualified/unqualified 别名，见 F-01）；
- 任务树算术：8+4+4=16（合计 16，偏差 0%）；工时 136+50+92=278（合计 278，偏差 0%）；但 L1 行组员数 12 ≠ L1 节点数 8（F-04）。

**是否 <3%？** 就「登记忠实度」类指标：**是**（均为 0%，精确匹配）。就报告自身的能力论断：**无法判定**（证据 unresolved，不冒充通过）。

## ⑧ 复跑命令

```bash
# 在线（需 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
python3 scripts/kf/review_wp542_04.py --out docs/kf/wp-542-04
# 离线（用本包已提交的 source_snapshot.md 字节快照，不联网）
python3 scripts/kf/review_wp542_04.py --offline --out docs/kf/wp-542-04
python3 -c "import json;print(json.load(open('docs/kf/wp-542-04/review_report.json'))['verdict'])"
```

