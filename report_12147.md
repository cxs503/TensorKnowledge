## ① 案例介绍

本单是 TensorPhysics 战役节点 `criterion-preregistration-gate`（mission 8598，重开为 m10569）的**验收计量门**：
它规定每个战役节点必须先冻结「机器验收判据」，事后再审计判据是否被偷偷放宽。审计对象是判据本身，不是船体物理量，因此本文的"基准"是
**生成器侧真值标签**（合成漂移语料由代码构造，标签即构造意图），而不是实验/文献值——这一点在第 ⑥ 节如实声明。

上一轮该节点合入 main 时留下一个真实缺陷：`docs/m8598/outputs/acceptance_criteria.json`
（本节点的验收记录）在 main 上是**另一个 mission 的记录**（8 行轴系扭振指标 + `pytest_test_shaft_torsion` 标记），
而唯一能发现它的守卫是"与完整重推导逐字节比对"，这个比对没有任何合并门在跑 → 漂移静默入 main。
本轮的靶子不是重写功能，而是把这个漏洞补成机制。

参数表：24 例合成漂移语料（13 漂移 / 11 非漂移）× 5 个种子；抽取器语料 20 例/种子（主 20261109，留出 42，OOD 无限定中文）；
阈值 recall≥0.92、precision≥0.95、字段级 F1≥0.95、零领域语义命中=0。

## ② 怎么做的

1. **记录自封存（seal）**：验收记录由 `scripts/run_criterion_prereg_eval.py` 从同一份 eval 载荷生成，并写入
   `payload_sha256` = 该记录 canonical body（排序键、紧凑分隔符、UTF-8）的 sha256；校验函数 `verify_deliverable()`
   不需要工件缓存、不需要重跑语料，离线即可判一份拷贝是否被手改/过期（fail-closed：无 seal 视为不通过）。
2. **合并门 `--check`**：脚本新增 `--check`，把 page + 记录重推导到临时目录，逐字节比对仓库内拷贝，并校验 seal，
   漂移即 exit 1（与 `render_criterion_prereg_doc.py --check` 同风格）。仓库零写入。
3. **根因修复**：`tests/test_shaft_torsion.py` 的验收汇总过去写 `<repo>/outputs/acceptance_criteria.json`，
   即**测试往仓库里拉了一个叫"验收记录"的文件**；main 上那份冒充记录正是它。改为写 pytest `tmp_path`，根治污染。
4. **回归证据**：`runs/m10569/seal_gate_evidence.py` 对已提交记录做 7 种变异，逐项统计三道守卫（逐字节 / 离线 seal / --check）
   的检出情况，输出 JSON+PNG，图与数字同源（不手抄）。

工具链：Python 3.11 + pytest + matplotlib(Agg)；判据冻结/漂移审计用仓内 `tensorphysics.campaign.criterion_prereg`
（manifest sha256 / semantic_digest / 五类漂移判定）。

## ③ 计算结果

验收判据（全部由 `scripts/run_criterion_prereg_eval.py` 程序化产出，路径 `artifacts/criterion_prereg/eval.json`）：

| 判据 | 指标 | 阈值 | 实测 | 通过 |
|---|---|---|---|---|
| (a) 24 例漂移检测 | recall / precision | ≥0.92 / ≥0.95 | 1.000 / 1.000 | ✅ |
| (a) 五类分类正确率 | class_accuracy | — | 1.000（13/24 正例） | ✅ 5 种子全通过 |
| (b) 抽取器字段级 | F1 | ≥0.95 | 1.000（留出种子 1.000，OOD 1.000） | ✅ |
| (c) fail-closed 负控 | 空 goal / 篡改 sha | unregistered / tampered+fail | `unregistered` / `tampered`+`fail` | ✅ |
| (d) 零领域语义扫描 | 命中数 | =0 | 0（6 文件 / 36 词条） | ✅ |

跨种子稳定性：

| seed | recall | precision | class_accuracy |
|---|---|---|---|
| `20261109` | 1.000 | 1.000 | 1.000 |
| `7` | 1.000 | 1.000 | 1.000 |
| `42` | 1.000 | 1.000 | 1.000 |
| `999` | 1.000 | 1.000 | 1.000 |
| `1` | 1.000 | 1.000 | 1.000 |

与基线（"goal 文本摘要变了就算漂移"）对照：基线 precision 0.542 / recall 1.000 / F1 0.703，
结构化审计 1.000 / 1.000 / F1=1.000；基线把 24 例全判成漂移（class_accuracy 0.000），
即"能发现变化，但分不清是哪类、松了还是紧了"。

真实目标 demo（本节点自己的判据 + 5 个 receipt）：prereg_coverage 0.800，
audit_pass_rate 0.200，drift_rate 0.125，fail_closed_rate 0.200；
篡改清单被 `tampered`+`fail` 拦下（负控生效）。

本轮新增缺陷修复的量化证据（7 种变异 × 3 道守卫）：

| 记录变异 | 逐字节 vs 重推导 | 离线 seal | `--check` 门 |
|---|---|---|---|
| threshold edited | ✅ | ✅ | ✅ |
| pass flag flipped | ✅ | ✅ | ✅ |
| negative control weakened | ✅ | ✅ | ✅ |
| wrong mission id | ✅ | ✅ | ✅ |
| overall verdict flipped | ✅ | ✅ | ✅ |
| payload_sha256 removed | ✅ | ✅ | ✅ |
| re-indented only (no semantic change) | ✅ | — | ✅ |

已提交记录的 seal = `60587073585c356c…`，`verify_deliverable` 返回 ok；离线 seal 用**零次语料重跑**抓住
6/6 项语义改动，纯重排版（语义不变）则由逐字节比对抓住——两者互补。

抽取器逐字段一致率：label=1.000, kind=1.000, metric=1.000, op=1.000, value=1.000, unit=1.000, count=1.000, scope=1.000。

## ④ 结果图

四张评测图（漂移分类混淆矩阵、结构化审计 vs 文本摘要基线、抽取器逐字段一致率、真实目标 demo KPI）+ 一张本轮新增的
"守卫 vs 变异"检出矩阵，全部由代码生成（`artifacts/criterion_prereg/fig_*.png`、`runs/m10569/fig_seal_gate.png`）。

## ⑤ 注意点

- **不是物理验证**：真值来自生成器构造，语料分布由代码定义；这些数字证明"门能判、能拦"，不证明任何船体物理结论。
- **seal 的边界**：canonical JSON 摘要对重排版不敏感（这是设计意图：语义不变≠漂移），因此"格式化篡改"必须靠逐字节比对/`--check` 兜底。
- **已知局限（如实登记，不计入验收）**：`limit-undelimited-cjk-2char` 探针（无限定二字中文指标名）抽取失败
  （matched 0/1）；补齐需要词表，会引入领域语义，故保持 fail-closed 的"未定义"分类。
- **环境事故**：过程中控制节点根分区一度 100% 满，`tmp_path` 无法创建，pytest 报 `No usable temporary directory`；释放后重跑通过，结论未受影响。
- **合并门依赖**：`--check` 需在 CI/合并前被调用才有意义；本单把它做成零写入、~3.5 s 的命令，方便挂到 pre-merge。

## ⑥ 误差判定

| 关键量 | 参考/基准 | 误差 | 是否 <3% |
|---|---|---|---|
| 漂移检测 recall / precision | 生成器真值（24 例） | 0.0% / 0.0% | 是 |
| 五类漂移分类正确率 | 生成器类标签 | 0.0% | 是 |
| 抽取器字段级 F1 | 生成器构造字段 | 0.0%（留出种子 0.0%） | 是 |
| 记录 seal 检出率（语义改动） | 6 项变异 | 漏检 0.0% | 是 |
| `--check` 门检出率（全部变异） | 7 项变异 | 漏检 0.0% | 是 |
| 基线（文本摘要）F1 | 同 24 例真值 | 29.7% | **否**（基线本身，非本方法） |

无实验/文献基准可对：本节点是验收计量门，其"真值"是构造即知的标签；因此用"与生成器标签的偏差"代替实验对标，
并显式声明不满足"对标实验"条件的原因，不做粉饰。

honest 记录：功能点在 main 上本已存在（缺陷是记录过期 + 门没跑），本轮补齐的是**可验证性**（seal + `--check`）+ 根因污染修复；
未做：把 `--check` 接入 CI workflow（属平台侧配置，不在本仓单 PR 范围）。
