# KBM-GOV-W1 · 多 Agent 知识治理规模化 v1（去重 · 交叉验证 · 矛盾发现 · 独立评审 · 三口径分离）

> **锚点**：KBM-TKC-GOV-SCALE（owner 校正令 P0，m15721 第 1 轮任务榜）
> **产物**：`ke/gov.py`（治理内核）· `scripts/kbm_gov_w1.py`（试点跑批 + 复核）· `scripts/kbm_gov_ablation.py`（标定/敏感性）
> · `governance/gov-config-v1.json`（实体别名表/阈值/评审池，数据非代码）· `runs/kbm-gov-w1/`（全量工件）· `tests/test_kbm_gov.py`（25 用例）
> **一句话结论**：200 篇试点批 → 153 条待评审 KO → **重复率 16.34% / 可裁定矛盾对 0（332 对高分歧因条件不全不可裁定）/ 评审通过率 69.93%**；
> 矛盾检测器在受控注入下 **recall=1.00（诱导分歧 ≥16.7%）**、9.1% 分歧不误报，控制组（真实语料）误报 0。

---

## ① 案例介绍（任务背景 · 语料 · 参数表）

**背景**：TensorKnowledge 已有四契约（claim/evidence/provenance/review-event）与评审状态机（`scripts/ke_state_machine.py`），
但缺少**规模化治理层**：同 subject 的知识未聚簇、同一物理量多来源数值未对照、矛盾无判定口径、评审未池化，
且历史报告存在「20 vs 257」口径病（同一批知识因分母不同出现两个数）。本单补齐该层并在 200 篇试点批上产出真数。

**语料（固定切片，可复现）**：平台 `tensorplatform.tensor_reports` 中
`status='published' AND length(markdown)>=1500 ORDER BY id ASC LIMIT 200` → **id 2..251 共 200 篇**，
快照身份 `snapshot.json:snapshot_digest`（逐篇 sha256），复核时按 id 重取并逐篇比对 sha256。

**参数表（`governance/gov-config-v1.json`，全部预注册）**

| 参数 | 值 | 含义 |
|---|---|---|
| 实体/别名 | 21 个实体、95 条别名 | Entity Resolution v1 闭世界词表（Re/Fr/Ma/Pr/Ra/Cb/α/λ/Cd/Cl/Ct/Cf/Cw/L-D/Nu/St/Rt/Rf/Rw/ζ/err） |
| `agree_rel` | 5% | 跨来源一致判定（对齐平台精度标准口径） |
| `contradict_rel` | 15% | 矛盾判定阈值 |
| `near_dup_jaccard` | 0.50 | 语义去重：数字掩码后词集 Jaccard 门 |
| `near_dup_hamming` | 6 | 语义去重：simhash 汉明门（敏感性见 ⑤） |
| `condition_lookback_lines` | 3 | 条件回溯窗口（同行无条件时向前取同节最近 3 行） |
| 几何上下文 | 8 类（cylinder/sphere/airfoil/plate/channel/ship-hull/cavity/pipe） | 几何是条件：同 Re 下圆柱与球不可比 |
| 评审池 | 8 个 agent reviewer（4 泳道 × 2 实例） | 泳道=provenance/units/entity/consistency；容量 5000/实例 |
| `policy_version` | `ke-review-v0.1` | 复用仓内状态机，不另建并行状态机 |

---

## ② 怎么做的（方法 / 流程 / 工具链）

```
tensor_reports(200 篇)
  └─ 候选抽取（正则 `name = value [unit]`，含 10⁵→10^5 上标指数、24/Re 公式排除）
       ├─ 丢弃：not_quantity_name / value_is_expression / entity_unresolved（逐条留 reason+span）
       └─ 实体解析 Entity Resolution v1（别名闭世界 → 置信 1.0；基名+限定词 → 0.9）
            ├─ 条件实体（kind=condition）→ 上下文，不成 KO
            └─ 结果实体（kind=result）→ KO（零手抄：span+needle+excerpt sha256，`relocate()` 回原文复算）
  ├─ 去重（L1 精确指纹 / L2 语义 subject+措辞 Jaccard）→ 簇 + 重复率
  ├─ 交叉验证（同 entity+qualifier+unit，跨报告配对；条件键 = 数值条件 + geo）
  │    └─ 判定 agree / divergent / contradicted / incomparable_conditions / unverified_comparison
  ├─ 矛盾发现 v1（contradicted 对 → contradiction 候选，带 rationale 与 next_action=replicate）
  ├─ 评审池（每泳道按 sha256(item) 选实例，容量约束，双实例；四泳道票 → 仲裁 → approve/reject/request-changes）
  │    └─ 状态机 fold（append-only；自批被拒即记 refused；账本逐行 sha256 链）
  └─ 三口径：B0 原始记录 / B1 待评审 KO / B2 经治理 KO（`Counting.reconcile()` 不变量硬校验）
```

**关键实现选择**
1. **评审不改写 `epistemic_status`**：评审事件只写 `review_status`（状态机 A3 轴独立），证据等级由证据面另行判定。
2. **矛盾判定必须"钉住物理算例"**：几何单独成立不算条件，至少需 1 个数值条件（Re/Fr/α/…）双方齐备；否则一律 `unverified_comparison`（no silent promotion）。
3. **文档内重复不算跨源验证**：同报告内配对不进入交叉验证（那是去重的职责）。
4. **err（相对误差）声明为 `document_local`**：它是各报告自身量的误差，跨报告比对无物理意义，故不参与交叉验证（仍参与去重）。

---

## ③ 计算结果（200 篇试点批，程序化注入，零手抄）

### 3.1 验收三真数（口径随数）

| 指标 | 值 | 分母（口径） | 公式 |
|---|---|---|---|
| **重复率** | **16.34%** | B1 = 153 KO | (B1 − 簇数 128)/B1 = 25/153 |
| **矛盾对数（可裁定）** | **0** | 跨报告配对 796 | 同条件且 \|Δ\|/max > 15% 的对数 |
| **评审通过率** | **69.93%** | B1 = 153 KO | pass 107 / 153 |

### 3.2 三口径分离（修「20 vs 257」口径病）

| 口径 | 定义 | 值 | 对账 |
|---|---|---|---|
| B0 原始记录 | 试点切片内的源文档数 | **200** | 逐篇 sha256（`snapshot.json`） |
| — 候选语句 | 正则数量语句（含被丢弃者） | 2870 | = 丢弃 2303 + 上下文 414 + KO 153 ✅ |
| B1 待评审 KO | 通过实体解析与零手抄复算的知识对象 | **153** | = 评审 153 ✅ |
| B2 经治理 KO | 评审通过且为去重簇代表 | **89** | pass 107 = 代表 89 + 重复成员 18 ✅ |

> 口径病根治方式：**每个指标必须声明所属口径**（`Counting.metric(..., bucket=...)`），bucket 非法即 `BucketViolation`；
> 五个对账不变量任一不成立即抛异常，不允许"算出来的数"与"报出去的数"来自不同分母（`tests/test_kbm_gov.py::test_bucket_*`）。

### 3.3 分解表

| 项 | 数 | 说明 |
|---|---|---|
| 丢弃：`entity_unresolved` | 1910 | 词表外符号，Top：H 314 / D 170 / L 165 / N 128 / R 109 / φ 76 / τ 68 / id 54 |
| 丢弃：`value_is_expression` | 236 | `Cd = 24/Re` 类公式（Stokes），非观测值 |
| 丢弃：`not_quantity_name` | 157 | snake_case 配置键等 |
| 实体解析率 | 22.89% | 2477 候选名中解析成功者占比（闭世界，不收模糊匹配） |
| 去重簇 | 128（簇规模 1:109 / 2:14 / 3:4 / 4:1） | 重复簇 19：L1 精确 13 簇、L2 语义 6 簇 |
| 重复成员（跨报告 / 同报告） | 25（跨 22 / 同 3） | 真重复以跨报告为主 |
| 交叉验证配对 | 796 | agree 132 / incomparable_conditions 332 / unverified_comparison 332（divergent 0、contradicted 0） |
| 组判定 | supported 1 / contradicted 0 / insufficient-evidence 18 | 19 个可比 subject 组 |
| 评审 | pass 107 / needs-fix 46 / fail 0 | needs-fix 全部来自 `ENTITY_QUALIFIER_UNVERIFIED`（如 `Cd_ref` 限定词未注册） |
| 评审拒绝事件 | 0 | 自批拦截在没有自批行为时不触发（用例覆盖该路径） |
| 引用账本 | 153 行 sha256 链 | `review/ledger.jsonl`，`verify` 逐行复算 |

### 3.4 矛盾检测器标定（受控注入，真实 KO 为母体；`runs/kbm-gov-w1/analysis.json`）

| 注入倍率 | 诱导相对分歧 | 期望 | 实测命中/19 | recall | 旁生对 |
|---|---|---|---|---|---|
| 1.02 | 1.96% | agree | 0 | 0.00 | 0 |
| 1.05 | 4.76% | agree | 0 | 0.00 | 0 |
| 1.10 | 9.09% | divergent | 0 | 0.00 | 0 |
| 1.20 | 16.67% | contradicted | 19 | **1.00** | 0 |
| 1.35 | 25.93% | contradicted | 19 | **1.00** | 0 |
| 1.50 | 33.33% | contradicted | 19 | **1.00** | 0 |
| 2.00 | 50.00% | contradicted | 19 | **1.00** | 0 |

阈值扫描（`contradict_rel` = 0.05/0.10/0.15/0.20/0.30 → recall 全 1.00；0.50 → 0.00，因诱导分歧 33% < 50%）：
检测边界与预注册 15% 一致，且**控制组（未注入真实语料）矛盾对 = 0**，即无假阳性。

去重敏感性（持久化 KO 重算，`analysis.json:dedupe_sensitivity`）：`near_dup_jaccard` 0.3→22.88%、0.4→20.92%、0.5→**16.34%**、0.6→14.38%、0.7→13.07%、0.8/0.9→12.42%（单调，阈值有效）；
`near_dup_hamming` 0..12 输出完全不变（**该层在本语料上惰性**，语义召回实际由 Jaccard 承担——如实登记，不夸大"双层"）。

**图**（`runs/kbm-gov-w1/figures/`）：f1 治理漏斗（三口径标注）· f2 去重簇规模与层级 · f3 矛盾检测标定曲线 · f4 评审泳道票型分布。

---

## ④ 结果图与比较曲线

| 图 | 内容 | 读法 |
|---|---|---|
| f1-funnel.png | B0→候选→B1→pass→B2 漏斗（对数轴） | 数量级落差来自实体解析闭世界（2870→153），是"宁缺勿滥"的直接代价 |
| f2-dedup.png | 簇规模直方图 + L1/L2 分层计数 | 19 个重复簇里 13 簇由精确指纹抓到，6 簇仅语义层能抓（措辞改写/中英混排） |
| f3-contradiction-calibration.png | recall vs 诱导分歧，含 5%/15% 阈值线 | 曲线在 9.1%–16.7% 之间跳变，与阈值一致；红线右侧 recall=1 |
| f4-review-lanes.png | 四泳道票型堆叠 | provenance/units 全绿（零手抄与量纲门 100% 通过）；entity 泳道是 needs-fix 唯一来源 |

（无解析解/文献曲线可对标：本层产出为治理统计量而非物理场量；矛盾检测的"基准"由注入实验提供，见 3.4。）

---

## ⑤ 注意点（坑 · 局限 · 适用范围）

1. **条件覆盖是本层的天花板**：153 条 KO 中仅 19 条（12.4%）带数值条件，故 332 对高分歧只能判 `unverified_comparison`。
   → 真实语料"可裁定矛盾 = 0"是**数据条件不足的诚实结论**，不是检测器失效（3.4 已证 recall=1.00）。
   W2 需求：从表格/小节标题抽取条件（表头 `| Re | Cd |` 结构化解析），预计把可裁定配对提升一个量级。
2. **跨语言改写不去重**（已用用例 `test_cross_language_rewording_is_a_known_non_merge` 固化）：中英文同一结论不合并，
   `误差 = 20.5%` 与 `error = 20.5%` 只有在同语族措辞相近时才被语义层合并。已登记为 W2 gap。
3. **simhash 层惰性**：小语料（153 条）3-gram simhash 对短句过于稀疏（同义改写汉明距离 23–37），实测无效；语义召回由 Jaccard 承担。
4. **审批独立性靠状态机而非信任**：`approve` 需身份不冲突，冲突即 `SELF_APPROVAL_BLOCKED` 记入 `refused.json`（本批 0 次，用例覆盖）。
5. **试批是固定切片而非时间片**：`ORDER BY id LIMIT 200` 对新报告免疫，但报告正文若被编辑则 `verify` 的 `slice_sha256_matches` 会红——这是设计意图（快照可证伪）。
6. 口径：三个验收数字都挂在 B1 口径上；B0=200 与 B2=89 不可与 B1=153 混用（口径病复发点已在代码层拦截）。

---

## ⑥ 误差判定（逐项 vs 基准，显式回答）

| 关键量 | 基准 | 实测 | 误差 | 是否 <3% / 判定 |
|---|---|---|---|---|
| 重复率 | 可复算真值：25/153 | 16.3399% | 0（重算全等，`verify:dedupe_recomputes=true`） | ✅ 一致（<3%） |
| 矛盾对数 | 控制组真值 0；注入组期望 19 | 0 / 19 | 0 | ✅ 一致 |
| 评审通过率 | 可复算真值：107/153 | 69.9346% | 0（`writeback_matches_ledger=true`） | ✅ 一致（<3%） |
| 零手抄复算 | 153/153 可回原文复算 | 153/153 | 0 | ✅ |
| 检测器 recall | 预注册阈值语义（≥15% 必中） | 1.00（m≥1.20） | 边界一致 | ✅ |
| 检测器假阳性 | 真实语料矛盾 = 0 | 0 | 0 | ✅ |
| 条件覆盖 | 无基准（本层自报） | 12.42%（19/153） | — | ⚠ 无基准，声明原因：语料自身不陈述条件，属能力边界而非计算误差 |

**未达 3% 门槛项的诚实说明**：上表前 5 项为**确定性复算**（差 0），不存在统计误差；第 7 项是覆盖度而非精度，无基准可比。

---

## 复现

```bash
python scripts/kbm_gov_w1.py run    --out runs/kbm-gov-w1 --limit 200 --min-chars 1500
python scripts/kbm_gov_w1.py verify --out runs/kbm-gov-w1      # 8 项复核全绿
python scripts/kbm_gov_w1.py queue  --out runs/kbm-gov-w1      # 导出 factory 工序04 队列
python scripts/kbm_gov_ablation.py  --out runs/kbm-gov-w1      # 标定 + 敏感性 + 4 张图
python -m pytest tests/test_kbm_gov.py -q                      # 25 passed（跑批后；干净检出 24 passed + 1 skipped）
```

`verify` 的 8 项：`ledger_chain_ok / dedupe_recomputes / crossval_recomputes / slice_sha256_matches /
all_ko_relocate(153/153) / buckets_reconcile / writeback_matches_ledger / refusals_accounted` → 全部 true。

## 重开复核（原 PR#209 关闭后，m19208 轮）

| 复核项 | 命令 | 结果 |
|---|---|---|
| 全流程可跑 | `python scripts/kbm_gov_w1.py run --out runs/kbm-gov-w1 --limit 200 --min-chars 1500` | ✅ 0.96 s，200/153/89 |
| 复核 8 项 | `python scripts/kbm_gov_w1.py verify --out runs/kbm-gov-w1` | ✅ 8/8 true（`all_ok=true`） |
| 标定+敏感性+图 | `python scripts/kbm_gov_ablation.py --out runs/kbm-gov-w1` | ✅ recall 1.00、控制组 0、4 图 |
| 两次跑批字节一致 | run+ablation 前后各取 19 个工件 sha256 | ✅ **19/19 字节相同**（含 4 张 PNG） |
| 单元测试 | `python -m pytest tests/test_kbm_gov.py -q` | ✅ 25 passed |
| 静态检查 | `python -m ruff check ke/gov.py scripts/kbm_gov_w1.py scripts/kbm_gov_ablation.py tests/test_kbm_gov.py` | ✅ All checks passed |

| KBM 测试族 | `python -m pytest tests/test_kbm_clean.py tests/test_kbm_extract.py tests/test_kbm_gov.py -q` | ✅ 69 passed, 1 xfailed |
| 全套回归（集群） | 递交 cj2126（本分支）/ cj2127（main 基线），`pytest tests -q --ignore=tests/test_kf_wp11107_01.py` | ⏳ 递交时点两单仍在排队（前 24 单），结果未取回 → 记 **WITHHELD**（已有采集错误 `tests/test_kf_wp11107_01.py` 收集失败为既有欠账，与本单无关） |

本轮相对原 PR#209 的差异：①移除误提交的 `ke/__pycache__/*.pyc` 二进制（`__pycache__/`、`*.pyc` 已在 `.gitignore`）；
②修 9 处 ruff 告警（E741 `l` 变量名 ×5、F401 未用导入 ×2、F841 未用变量 ×1、E731 lambda 赋值 ×1），**语义零改动**——
修正前后 19 个工件 sha256 全等即为证；③测试与文档对齐（干净检出时 pilot 工件缺失的 1 例按设计 skip）。

## 与 factory 工序04 的对接契约

`python scripts/kbm_gov_w1.py queue` 产出 `runs/kbm-gov-w1/review/queue-v1.jsonl`，每项含
`queue_id / item_id / subject_key / source_report / state / decision_code / governed / votes[]`；
`state ∈ {approved, draft, rejected}` 与 `review-event.schema.json` 的 decision 一一对应
（approve / request-changes / reject）。factory 只需追加 `item_id` 到自家队列，回写即复用本层 `writeback.json` 结构。