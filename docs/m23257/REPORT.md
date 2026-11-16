# PROD-RA STATUS 发布（m23257）：RA 行 code_implemented 置 true、scenario_validated 拒置 true

- 发布目标：`TensorBench/products/STATUS.json` v2 的 RA 行（canonical 文件属 TensorBench 仓，
  本工作树是 TensorKnowledge 检出，故交付"逐字节可应用的补丁 + 校验器 + 复核证据"）
- 复核基准：`main@3fbd3b35c02dd9457fbd46a1905384972883ec8e`（冷提取，仅 tracked 文件，无 legacy `runs/m22059`）
- 判据：`TensorBench/schemas/acceptance-status.schema.json` + `tensorbench/contracts.py::_status_errors`
- **处置：`code_implemented=true`（已置）；`scenario_validated=false`（拒置，honest-FAIL）**

## 1. 案例介绍（审的是什么）

RA（Research Audit）是四条产品线（AE/RA/BE/PV）之一：对研究断言做引用—证据可追溯审计。
真实场景试点全链为：m22059 初审 FAIL（row 903，level 2，D1–D12）→ m22760 返修（PR#499）→
m23111 残差修复（PR#511）→ m23157 独立复审（R5）。本单的任务是把这条链的结果写进 RA 行。

发布对象参数表（均为本次实测值）：

| 量 | 值 | 来源 |
|---|---|---|
| 被审 HEAD | `3fbd3b35c02d…`（`Merge #513 (m23157)`） | `git rev-parse HEAD` |
| PR#511 合并点 | `3a70ce80b74a885ede35a8d3d369f1648527ff50`（`Merge #511 (m23111)`），`merge-base --is-ancestor` = 真 | `status_evidence.json#pr511_merge` |
| 主线上 `docs/review_m22059_prod_ra/recheck.py` | sha256 `2cfa2454…b1090` | 与 R5 复审所依据的修复件**逐字节相同** |
| 修复前同文件（`cbd754b`） | sha256 `62b31f54…d9ee4` | `git show cbd754b:…` 实算 |
| 证据 item / claim / 失败台账 | 5 / 11 / 3 | `docs/m22059/validation-report.json` |
| file locator 字段 | 144 | `verify_status.py`（复用 R5 枚举器） |
| 指标 | 目标 | 实测 |
|---|---|---|
| locator 冷启动解析率 | 100% | **11.8%**（17/144） |
| 审阅包 manifest 自洽 | 18/18 | **12/18**（4 缺文件 + 2 摘要不符） |
| 契约违例数（proposed payload） | 0 | **0** |

## 2. 怎么做的（方法/流程/工具链）

1. **不引用，只重算**：`docs/m23257/verify_status.py` 直接 `import` R5 复审的枚举器
   （`docs/m23157/verify_r5.py::collect_locators / d6_evidence / sha256sums_audit`），
   保证新证据与它审计的那份复审**同一口径**，不会出现"换标尺得新结论"。
2. **第三人视角**：冷提取用 `git archive HEAD | tar -x`（只 tracked 文件），
   因此 legacy `runs/m22059/`（被 .gitignore）必然缺席 —— 这正是第三方拿到仓时的条件。
3. **入口点实跑**：在冷提取根上直接执行主线 `recheck.py`，记录 exit code、stderr 末行与输出节名。
4. **判据机器化**：补丁不靠人眼判合法性，而是喂给 TensorBench 自己的
   `contracts.validate_payload("status", payload)` 与 `contracts._status_errors`。
5. **台账直读尝试**：`psql tensorplatform -c "SELECT … tensor_maturity_verdicts WHERE id IN (903,917,918) …"`
   → `ERROR: permission denied for table tensor_maturity_verdicts`（本角色无 SELECT，与 R5 同）。
   故不冒称读过台账，改以仓内 file:line 引用入账（`status_evidence.json#verdict_ledger`）。
6. **补丁机制**：`build_payload.py` 从 canonical 文件生成 proposed successor（只动 RA 行 +
   新增 `mission_baseline_reconciliation` 与 `evidence_index`）；`apply_status_patch.py`
   校验源文件 sha256 后原地应用，源漂移即拒（exit 3）。

## 3. 计算结果

### 3.1 两项独立状态字段的裁决

| 字段 | 任务书主张 | 实测支撑 | 本单写入 | 依据 |
|---|---|---|---|---|
| `code_implemented` | true | **成立** | **true** | 审计引擎已在其属主仓：主线 `recheck.py` 与 PR#511 被审修复件 sha256 相同；冷提取 exit 0；六检全过 |
| `scenario_validated` | true | **不成立** | **false** | R5 回执 `verdict=changes_requested`（见 3.2），且 `contracts._status_errors` 明令 `scenario_validated=true` 要求 `verdict=pass` |

### 3.2 R5 回执到底是什么（这是本单的核心事实）

`docs/m23157/REVIEW-RECEIPT-R5.json`（sha256 `6c29270d…932b`）：

| 字段 | 值 |
|---|---|
| `verdict` | `changes_requested` |
| `scenario_validated` | `false`（`"复审单不抢跑；由协调者依裁决置位"`） |
| `six_checks.all_six_pass` | `true` |
| `residuals` | R5-1 blocking / R5-2 major / R5-3 minor / R5-4 info |

任务书称"m23157 accepted=true、R5 复审绿"。可核对的是：**六检确实全绿、R4-2 确实成立、
PR#511 确实已并**——这四点本单独立复算全部为真。但**整体裁决是 `changes_requested`**，
且 R5-1（blocking）在 `main@3fbd3b3` 上原样未修。故 `accepted=true` 只能理解为
"m23157 这张复审单作为交付被验收"，不能理解为"RA 场景通过验收"。二者混用会把
`changes_requested` 洗成 acceptance —— 本单拒绝把这一混淆编码进 STATUS。

### 3.3 残差在主线上的实测（本单独立重算，非引用）

| 残差 | R5 记录 | 本单 `main@3fbd3b3` 实测 | 结论 |
|---|---|---|---|
| R5-1 locator 冷启动 | 144 字段 / 17 可解析 | 144 字段 / **17 可解析（11.8%）**、122 仅前缀重写后可解析、5 重写也不可解析、114 仍用 legacy `runs/m22059/`、17 为 `/srv/tensor/agent` 绝对外域 | 原样未修 |
| R5-2 manifest | 18 条中 5 条不成立 | 18 条中 **6 条**不成立：4 缺文件（`raw/adjacent_unit_tests.log`、`raw/evidence_schema_validation.log`、`raw/pytest_collect_base.log`、`raw/pytest_collect_reviewed.log`）＋ 2 摘要不符（`raw/SHA256SUMS` 自摘要、`recheck.py`） | **变差 1 条**（见下） |
| R5-3 D6 指纹 | 1/5 无 `input_sha256`，3/5 绝对外域 | 5/5 schema 合法；`ev-kb10k-incompatibility` 仍无 `input_sha256`；3 条仍指向 `/srv/tensor/agent/work/m22760`；`source_ref` 冷启动可解析 0/5、实算摘要命中 0/5 | 原样未修 |
| R5-4 recheck 语义 | 作者席 exit 0 无验收权重 | 主线同一文件；本单只据其 exit 0 佐证"引擎可运行"，不据其判验收 | 维持 |

**新发现（R5-2 恶化）**：`docs/review_m22059_prod_ra/SHA256SUMS` 第 13 行仍声明修复前摘要
`62b31f54…`，而 PR#511 已把该目录下 `recheck.py` 换成 `2cfa2454…`。即 PR#511 合并后
审阅包 manifest 多出 1 条不符项。`git show cbd754b:…/recheck.py | sha256sum` = `62b31f54…`，
`git show d1d5c49:…` = `2cfa2454…`，两条命令可复核。

### 3.4 契约校验（判据机器化）

```
$ python3 docs/m23257/apply_status_patch.py           # dry run，目标=canonical 副本
RA code_implemented=True scenario_validated=False verdict=changes_requested
untouched lines: [('AE', True, False), ('BE', True, True), ('PV', True, True)]
validation errors: none
```

对照试验（把任务书要求的值塞进去）：

```
scenario_validated=True + verdict=changes_requested
  -> "RA: scenario_validated=true requires acceptance_evidence.verdict=pass (got 'changes_requested')"
scenario_validated=True + verdict=pass               -> validation errors: none（对造好了）
```

即：**不是本单主观不放行，是 canonical 校验器拒绝**。反向对照证明校验器并非"永远报错"。

### 3.5 图

- `figures/ra-locator-coldstart.png`：144 个 locator 的三段分解（冷解析 / 仅前缀重写 / 彻底不可解析）
- `figures/ra-entrypoint-exitcodes.png`：入口点五种变体 exit code（修复前 1、修复后 0 的缺陷实证）
- `figures/ra-status-reconciliation.png`：任务书主张 vs 实测支撑（两个状态字段逐一对照）

## 4. 产物与证据绑定

| 产物 | 作用 | sha256 |
|---|---|---|
| `docs/m23257/status_evidence.json` | 本单全部实测数据（冷提取重算） | 见 `SHA256SUMS` |
| `docs/m23257/products_STATUS.proposed.json` | 可直接应用的 STATUS.json 后继版本（schema 合法） | 见 `SHA256SUMS` |
| `docs/m23257/verify_status.py` | 复算脚本（复用 R5 枚举器） | 见 `SHA256SUMS` |
| `docs/m23257/build_payload.py` | 从 canonical 生成补丁，禁手抄 | 见 `SHA256SUMS` |
| `docs/m23257/apply_status_patch.py` | 属主仓原地应用 + 契约校验 + 源漂移拒绝 | 见 `SHA256SUMS` |
| `docs/m23257/test_status_publication.py` | 9 条不变式测试（`9 passed`） | 见 `SHA256SUMS` |
| `docs/m23257/make_figures.py` | 图（数据全部程序化注入） | 见 `SHA256SUMS` |

引用而不重造的证据：`docs/m22059/validation-report.json`（`466f2299…bd7`）、
`docs/m22059/criteria.json`（`c12873d3…74a`）、`docs/m23157/REVIEW-RECEIPT-R5.json`（`6c29270d…32b`）。

## 5. 注意点（坑与局限）

1. **canonical 文件不在本仓**：`products/STATUS.json` 属 TensorBench，本工作树为 TensorKnowledge
   检出。按"只改工作树内文件"的约束，本单不制造第二份 canonical 文件，交付物为补丁 + 应用器；
   合并到 TensorBench 需另一张单在 TensorBench 工作树执行 `apply_status_patch.py --write`。
   若把 RA 行写进 TensorKnowledge 的 `products/`，将产生两个真源，属于制造分叉。
2. **台账不可直读**：`tensor_maturity_verdicts` 对本角色无 SELECT，行 903/918 原文取自仓内引用
   （`docs/review_m22059_prod_ra/REVIEW-R4.md:6,163`、`docs/m23157/REVIEW-R5.md:5`）。
   任务书写的"917/918"与仓内一致记录的是"903/918"，仓内**未见**任何对行 917 的引用，
   故本单把"917"记为未核对，而不是顺手写成 918 让它看起来自洽。
3. **作者席 exit 0 不构成验收**（R5-4）：本单只用它证明引擎可运行，不用它判通过。
4. **`reviewed_commit` 的口径**：按任务书写 PR#511 合并点 `3a70ce8`；但 R5 回执实际审的是
   `main@cbd754b` + 单独修复件 `d1d5c49`。两个 sha 都写进 RA 行 `baseline_note`，避免
   "用一个 commit 号概括两次不同的复审条件"。
5. **适用范围**：RA 的验证是契约级（可复现性/可移植性），不是准确率。无专家标注 holdout、
   无 per-class precision/recall —— 这一条已列入 RA 行 `not_implemented_or_unverified`。

## 6. 误差判定（显式回答"是否 <3%"）

本单不涉及物理量，**无实验/解析基准**，因此 `<3%` 精度判据不适用；等价判据为契约违例数与
locator 冷解析率，逐项如下：

| 判据 | 基准/目标 | 实测 | 误差 | 是否 <3% |
|---|---|---|---|---|
| proposed STATUS.json 契约违例数 | 0 | 0 | 0 | **是（0%）** |
| RA 行 verdict 与回执一致性 | 必须相等 | `changes_requested` = `changes_requested` | 0 | **是（0%）** |
| 主线 `recheck.py` = 被审修复件 | 逐字节相同 | sha256 相同 | 0 | **是（0%）** |
| locator 冷启动解析率 | 100% | 11.8%（17/144） | **88.2 pp** | **否（honest-FAIL）** |
| 审阅包 manifest 自洽率 | 100% | 66.7%（12/18） | **33.3 pp** | **否（honest-FAIL）** |
| D6 `source_ref` 冷启动可解析 | 5/5 | 0/5 | **100 pp** | **否（honest-FAIL）** |

**结论**：`code_implemented` 达线并已置 true；`scenario_validated` 三项支撑判据全部远超容差，
按判据不得置 true，本单按 honest-FAIL 报，并给出可复算的翻盘条件（修 R5-1/R5-2/R5-3 →
取得一票 `pass` 裁决 → 同一次改动里置 true）。翻盘条件已机器化写入
`test_scenario_validated_follows_locator_residual`：一旦 locator 全部冷解析，该测试反过来要求
状态字段与 `verdict` 对齐，防止"修好了却忘了置位"。

## 7. 未跑项

- TensorKnowledge 全量 pytest 套件（未跑；本单只跑 `docs/m23257/test_status_publication.py`，
  `9 passed`，以及冷提取上的 `recheck.py` 全流程）
- `tensor_maturity_verdicts` 行 917 的读取（无权限，见 §5.2）
- 跨机器 / 跨 Python 版本复跑
- TensorBench 侧的 `apply_status_patch.py --write` 实际落盘（本工作树无 TensorBench 检出）