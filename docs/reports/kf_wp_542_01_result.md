# KF-RESULT wp-542-01

**工作包**: `wp-542-01` · **task_type**: `01-asset-registration` · **report_id**: `542` · **lane**: C · **delivery**: TensorKnowledge (draft)

## ① 本工序做了什么

对 report_id=542《FEM/DEM 能力盘点与成组任务树 — m605 进展报告》执行**资产登记**（不做抽取、不做 claim 生成、不标 verified）：

1. 确认源资产身份：`tensor://reports/542` 的 `markdown` 字段，UTF-8 字节 10333 B / 6599 字符，sha256 = `sha256:a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40`，与工作包契约 `source_hash` **逐字节一致**。
2. 清点可解析的附件/工件：共登记 **51** 个资产 = 1 源资产 + 3 报告记录内嵌图元数据 + 47 条正文路径引用。
3. 逐条给出可解析定位（行号 + 该行逐字引文），并对每条引用尝试解析（只在本交付工作树内解析，不跨仓臆测）。
4. `claims` 按契约 notes 保持空数组；未做任何 verified 标记。

资产状态分布：

| kind/status | 数量 |
|---|---|
| `data_artifact_reference/unresolved` | 4 |
| `document_reference/unresolved` | 1 |
| `embedded_figure/metadata_only` | 3 |
| `figure_reference/unresolved` | 6 |
| `report_markdown/resolved` | 1 |
| `source_code_reference/unresolved` | 36 |
| **合计** | **51** |

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET /api/v1/tensor/reports/542`（Bearer token，`$TENSOR_AGENT_USER` 登录）。本机 `psql -d tensorplatform` 直读 `tensor_reports` 被拒（`permission denied for table tensor_reports`），故唯一取源通道为平台 API——这一点如实记录，不掩饰。
2. **定身份**：对 `markdown` 的 UTF-8 字节做 sha256，与契约 `source_hash`、契约 `chars=6599` 双向比对，不等即中止（脚本内 `SystemExit`，不产出半成品清单）。
3. **扫描引用**（三条正则，全部只读原文，不猜测）：
   - Markdown 图片：`!\[alt\](path)` → `figure_reference`
   - 反引号路径 + 可选 `:line` 引脚：`` `path[:line]` `` → 按扩展名分类
   - 裸路径 + 可选 `:line` 引脚（如 `dem3d.py:27-28`）→ 按扩展名分类
4. **去重粒度**：资产按 **(path, markdown_line) 出现级** 标识，同一文件被引用于不同行=不同资产（各自带自己的引文）；去重视图另给 `distinct_referenced_paths = 36`。
5. **解析**：仅在交付工作树 TensorKnowledge 内查找；找到则算 sha256/字节数（`resolved`），找不到则 `unresolved` 并写明原因；平台记录了但无字节载荷的图 → `metadata_only`（不假装有哈希）。
6. **产物**：`asset_manifest.json`（主产物）→ `kf_result.json`（信封，`source_hash` 由**重新拉取的实时字节**重算，与清单声明不一致即中止）→ `verification.json`（独立复算全部验收项）。
7. **关键设置**：纯 Python 标准库（urllib/hashlib/json/re），无第三方依赖；脚本幂等，可重复运行。

一键复跑：

```bash
python3 scripts/kf/build_asset_manifest.py build result verify && python3 scripts/kf/render_report_542.py
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-542-01/asset_manifest.json` | 主产物：51 资产 + provenance + 空 claims；35028 B，sha256 `5f3b256eb953c08aa112cc6a155d8dc0e5dec40de2f627f24a564f5e115c5f71` |
| `docs/kf/wp-542-01/kf_result.json` | 交付信封：package_id/task_type/report_id/provenance/outputs 五键，`source_hash` 实时重算绑定 |
| `docs/kf/wp-542-01/verification.json` | 自校验报告：7 项验收全通过=True |
| `scripts/kf/build_asset_manifest.py` | 可复跑构建器（build / result / verify 三个动作） |
| `docs/reports/kf_wp_542_01_result.md` | 本报告（六段式 + 唯一 json 块） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

定位方案：`markdown_line`（1 基行号，引文=该行原文逐字，校验时 `lines[line-1] == quote` 且 `quote in markdown`）；`report_field`（`markdown` / `figures[i]`）。下表由脚本从清单回读生成，**无一条手抄**。

| asset_id | kind | 解析状态 | 定位 | 原文引文（逐字） |
|---|---|---|---|---|
| `r542:source` | report_markdown | resolved | markdown(整个字段) | sha256:`a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40`，6599 字符 |
| `r542:figure:01` | embedded_figure | metadata_only | figures[0] | name=`fig1_capability_radar.png`; caption=FEM/DEM Capability Radar: TensorPhysics vs Reference Codes |
| `r542:figure:02` | embedded_figure | metadata_only | figures[1] | name=`fig2_dependency_dag.png`; caption=Task Tree Dependency DAG (16 nodes, 20 edges) |
| `r542:figure:03` | embedded_figure | metadata_only | figures[2] | name=`fig3_gap_heatmap.png`; caption=Three-Layer Cross-Reference Gap Matrix |
| `r542:ref:01` | source_code_reference | unresolved | L27 | \| 冰密度 ρ_ice \| 917 kg/m³ \| dem3d.py:24 硬编码 \| |
| `r542:ref:02` | source_code_reference | unresolved | L28 | \| 键合断裂应变 \| 0.015 (拉) / 0.03 (剪) \| dem3d.py:27-28 \| |
| `r542:ref:03` | source_code_reference | unresolved | L29 | \| 接触刚度 \| 用户定义 \| dem3d.py:364 \| |
| `r542:ref:04` | source_code_reference | unresolved | L30 | \| 接触阻尼 \| 5.0 (默认) \| dem3d.py:29 \| |
| `r542:ref:05` | source_code_reference | unresolved | L31 | \| FEM 板单元 \| Shell4 (4节点壳) \| tensorfem/shell4.py \| |
| `r542:ref:06` | source_code_reference | unresolved | L32 | \| cohesive 模型 \| 双线性牵引-分离律 \| tensorfem/cohesive.py:32 \| |
| `r542:ref:07` | source_code_reference | unresolved | L33 | \| 瞬态积分 \| Newmark-β / 中心差分 \| tensorfem/dynamics.py, explicit_dynamics.py \| |
| `r542:ref:08` | source_code_reference | unresolved | L33 | \| 瞬态积分 \| Newmark-β / 中心差分 \| tensorfem/dynamics.py, explicit_dynamics.py \| |
| `r542:ref:09` | data_artifact_reference | unresolved | L34 | \| SI-4 演示规模 \| 25节点×16单元板, 12颗粒×30键 \| validation_report.json \| |
| `r542:ref:10` | data_artifact_reference | unresolved | L35 | \| SIR5 断裂规模 \| 405颗粒, 3560键, 624断裂 \| sir5 run_summary.json \| |
| `r542:ref:11` | source_code_reference | unresolved | L82 | \| beam2.py \| 2节点Euler-Bernoulli梁 \| ✅有测试 \| PASS \| test_beam.py \| |
| `r542:ref:12` | source_code_reference | unresolved | L82 | \| beam2.py \| 2节点Euler-Bernoulli梁 \| ✅有测试 \| PASS \| test_beam.py \| |
| `r542:ref:13` | source_code_reference | unresolved | L83 | \| shell4.py \| 4节点MITC4壳 \| ✅有测试 \| PASS \| test_shell4.py \| |
| `r542:ref:14` | source_code_reference | unresolved | L83 | \| shell4.py \| 4节点MITC4壳 \| ✅有测试 \| PASS \| test_shell4.py \| |
| `r542:ref:15` | source_code_reference | unresolved | L84 | \| solid3d.py \| 8节点六面体 \| ✅有测试 \| PASS \| test_solid3d.py \| |
| `r542:ref:16` | source_code_reference | unresolved | L84 | \| solid3d.py \| 8节点六面体 \| ✅有测试 \| PASS \| test_solid3d.py \| |
| `r542:ref:17` | source_code_reference | unresolved | L85 | \| cohesive.py \| 两节点cohesive界面 \| ✅有测试 \| PASS \| test_cohesive.py (6 tests) \| |
| `r542:ref:18` | source_code_reference | unresolved | L85 | \| cohesive.py \| 两节点cohesive界面 \| ✅有测试 \| PASS \| test_cohesive.py (6 tests) \| |
| `r542:ref:19` | source_code_reference | unresolved | L86 | \| mixed_mode_cohesive.py \| BK混合模式 \| ✅有测试 \| PASS \| test_mixed_mode_cohesive.py \| |
| `r542:ref:20` | source_code_reference | unresolved | L86 | \| mixed_mode_cohesive.py \| BK混合模式 \| ✅有测试 \| PASS \| test_mixed_mode_cohesive.py \| |
| `r542:ref:21` | source_code_reference | unresolved | L87 | \| ice_sheet.py \| 冰板(Winkler占位) \| ⚠️部分 \| 部分PASS \| 地基板未实现,浮力有测试 \| |
| `r542:ref:22` | source_code_reference | unresolved | L88 | \| dynamics.py \| Newmark-β隐式 \| ✅有测试 \| PASS \| test_beam_dynamics.py \| |
| `r542:ref:23` | source_code_reference | unresolved | L88 | \| dynamics.py \| Newmark-β隐式 \| ✅有测试 \| PASS \| test_beam_dynamics.py \| |
| `r542:ref:24` | source_code_reference | unresolved | L89 | \| explicit_dynamics.py \| 中心差分显式 \| ✅有测试 \| PASS \| test_explicit_dynamics.py \| |
| `r542:ref:25` | source_code_reference | unresolved | L89 | \| explicit_dynamics.py \| 中心差分显式 \| ✅有测试 \| PASS \| test_explicit_dynamics.py \| |
| `r542:ref:26` | source_code_reference | unresolved | L90 | \| coupled_hull.py \| 线性船体接收器 \| ⚠️间接 \| 间接PASS \| physical_accuracy=False \| |
| `r542:ref:27` | source_code_reference | unresolved | L91 | \| suboff_ice_collision.py \| SUBOFF碰撞全链 \| ✅有测试 \| PASS \| test_suboff_ice_collision.py \| |
| `r542:ref:28` | source_code_reference | unresolved | L91 | \| suboff_ice_collision.py \| SUBOFF碰撞全链 \| ✅有测试 \| PASS \| test_suboff_ice_collision.py \| |
| `r542:ref:29` | source_code_reference | unresolved | L97 | \| dem3d.py \| 3D键合球体DEM \| ✅有测试 \| PASS \| 105颗粒基准 \| |
| `r542:ref:30` | source_code_reference | unresolved | L98 | \| dem.py \| 2D IceDEM \| ✅有测试 \| PASS \| hull_contact集成 \| |
| `r542:ref:31` | source_code_reference | unresolved | L99 | \| dem3d_wedge.py \| 楔形船首接触 \| ✅有测试 \| PASS \| 有限/无限宽 \| |
| `r542:ref:32` | source_code_reference | unresolved | L100 | \| hull_contact.py \| 2D polyline船体 \| ✅有测试 \| PASS \| 反力平衡验证 \| |
| `r542:ref:33` | source_code_reference | unresolved | L101 | \| continuum_boundary_dem.py \| 连续体弹簧网络 \| ✅有测试 \| PASS \| 平面应力本构 \| |
| `r542:ref:34` | source_code_reference | unresolved | L102 | \| calibrated_wet_coupling.py \| 2D流-DEM耦合 \| ✅有测试 \| PASS \| subcycling \| |
| `r542:ref:35` | source_code_reference | unresolved | L103 | \| dem3d_energy.py \| 能量跟踪 \| ✅有测试 \| PASS \| 耗散率量化 \| |
| `r542:ref:36` | figure_reference | unresolved | L122 | ![能力雷达图](runs/m605/fig1_capability_radar.png) |
| `r542:ref:37` | figure_reference | unresolved | L130 | ![缺口热图](runs/m605/fig3_gap_heatmap.png) |
| `r542:ref:38` | figure_reference | unresolved | L140 | ![依赖DAG](runs/m605/fig2_dependency_dag.png) |
| `r542:ref:39` | data_artifact_reference | unresolved | L180 | 完整任务树已入库：`artifacts/fem_dem_task_tree.json` |
| `r542:ref:40` | source_code_reference | unresolved | L196 | 3. **GPU 未验证**：dem3d.py 声称支持 CUDA，但 cell list 可能同步阻塞 |
| `r542:ref:41` | source_code_reference | unresolved | L197 | 4. **物理精度**：coupled_hull.py 的 `physical_accuracy_qualified` 硬编码为 False |
| `r542:ref:42` | data_artifact_reference | unresolved | L244 | \| `artifacts/fem_dem_task_tree.json` \| 任务树 JSON（16节点，机器可读） \| |
| `r542:ref:43` | figure_reference | unresolved | L245 | \| `runs/m605/fig1_capability_radar.png` \| 能力雷达图 \| |
| `r542:ref:44` | figure_reference | unresolved | L246 | \| `runs/m605/fig2_dependency_dag.png` \| 依赖 DAG 图 \| |
| `r542:ref:45` | figure_reference | unresolved | L247 | \| `runs/m605/fig3_gap_heatmap.png` \| 缺口矩阵热图 \| |
| `r542:ref:46` | source_code_reference | unresolved | L248 | \| `runs/m605/generate_figures.py` \| 图表生成脚本 \| |
| `r542:ref:47` | document_reference | unresolved | L249 | \| `docs/reports/m605_fem_dem_audit_report.md` \| 本报告 \| |

## ⑤ 注意点与局限

- Registration only: no text extraction, no claim generation, no verified marks (verification is platform-gated).
- Referenced paths are resolved strictly inside the TensorKnowledge delivery worktree; TensorFEM/TensorDEM source trees are outside this work package's boundary, so source_code_reference entries stay unresolved by design.
- No artifacts/fem_dem_task_tree.json or runs/m605/*.png exist in this worktree, so the report's own appendix files are registered as unresolved rather than assumed.
- Report metadata 'figures' is inventoried as-is; no figure bytes are copied into the manifest.
- Output location: .gitignore ignores artifacts/ and docs/ops/filter-audit.md documents that the push gate drops artifacts/**; outputs therefore live under docs/kf/wp-542-01/ so they are not silently filtered.
- 资产状态三值语义已写入清单 `resolution_status_vocabulary`：`resolved` / `unresolved` / `metadata_only`；`unresolved` 是**显式状态**而非失败判决，`metadata_only` 明确表示不可算哈希。
- 未做抽取、未做报告类型判定（契约 `classify_report_type: false`），因此本单**没有**语义结论，报告正文里的能力/缺口论断一律不进 claim 面。
- 引用解析范围受限：报告的 36 条源码引用指向 TensorFEM/TensorDEM 源码树，不在本交付仓边界内，故一律 `unresolved` 并注明原因；这是**边界约束下的诚实结果**，不是声称这些文件不存在。
- 未做独立复核（契约 `review.required: false`）；verification 由平台门计算，本单不自标 verified。
- **关于图**：本工序是资产登记/文档型工作包，无场量计算、无解析解对比，故**不产出云图或比较曲线**；报告记录里引用的 3 张图（fig1_capability_radar / fig2_dependency_dag / fig3_gap_heatmap）按平台 `figures[]` 现状只能登记为 `metadata_only`（无字节载荷可复算哈希）。此处写明理由而非留空。

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | json.loads OK |
| schema_pass | ✅ | missing_top=[] missing_provenance=[] |
| source_locator_resolvable | ✅ | checked 51 locators; unresolvable=[] |
| source_hash_matches | ✅ | recomputed=a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40 declared=a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40 contract=a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40 |
| no_duplicate_ids | ✅ | assets=51 unique=51 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=0 violating=0 (empty array: vacuously satisfied per contract notes) |
| do_not_mark_claims_as_verified（附加） | ✅ | claims carry no 'verified' status |

无失败项（honest-FAIL 无需申报）。全部 7 项由 `python3 scripts/kf/build_asset_manifest.py build result verify && python3 scripts/kf/render_report_542.py` 复算，`all_pass=True`。

**误差判定**：本单无数值解，故无「计算值 vs 基准值」误差；可判定的是**身份一致性**这一关键量：

| 关键量 | 基准 | 实测 | 偏差 | 是否 <3% |
|---|---|---|---|---|
| 源 markdown sha256 | 契约 `a07bad25…9b40` | 复算同值 | 0 字节 / 0% | ✅ 是（严格 0 偏差） |
| 定位可解析率 | 要求 100% | 51/51 | 0 条失效 | ✅ 是 |
| 资产 ID 唯一性 | 无重复 | 51 唯一/51 总计 | 0 重复 | ✅ 是 |

结论：哈希三项（契约 / 清单声明 / 实时重算）逐字节相同，偏差严格为 0，优于 3% 阈值；`recomputed=a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40 declared=a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40 contract=a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40`。

## 交付 JSON（本报告唯一 json 代码块）

```json
{
  "package_id": "wp-542-01",
  "task_type": "01-asset-registration",
  "report_id": "542",
  "provenance": {
    "source_uri": "tensor://reports/542",
    "source_field": "markdown",
    "source_hash": "sha256:a07bad2500aeed73b47222738bffb3d6a70d39a16790e2c991e01f5bbb239b40",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 6599,
    "source_bytes_utf8": 10333,
    "fetched_via": "GET /api/v1/tensor/reports/542",
    "generator": "scripts/kf/build_asset_manifest.py",
    "contract_version": "1.0"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-542-01/asset_manifest.json",
      "sha256": "5f3b256eb953c08aa112cc6a155d8dc0e5dec40de2f627f24a564f5e115c5f71",
      "bytes": 35028,
      "asset_count": 51,
      "claims": 0
    }
  }
}
```
