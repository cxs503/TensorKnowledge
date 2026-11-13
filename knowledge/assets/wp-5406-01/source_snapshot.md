# TensorDEM main CI 清红（m4857）：红测的根因是合并把证据 blob 丢了

## 1 案例介绍

**对象**：TensorDEM 主分支 `main@cb6c562`（Merge #346 via merge-master）。本单修的是仓库的**证据门禁**
（evidence gate），不涉及 DEM 求解器的物理/数值内核。

**物理背景**：无场量求解——判据是「文档引用的每个路径在干净 clone 里都能解析」。红项：

| 红项 | 现象 |
|---|---|
| `tests/test_doc_evidence_pointers.py::DocumentedEvidenceGateTests::test_committed_ledger_is_current` | `audit --check` 返回 1：账本登记的三条指针判为 `MISSING` |
| `...::test_cited_source_docs_and_tests_are_tracked`（CI 同批报红） | 同一批指针在 CI 上被判不可解析 |

**关键对象**：

| 量 | 值 |
|---|---|
| 被引用的文档 | `docs/ci_clearance_m4829.md`（第 21/22/61 行各引一个产物） |
| 被引用的产物 | `artifacts/m4829_ci_gate/` 下 `gate_evidence.json`、`provenance_gate_matrix.png`、`ledger_regeneration.png` |
| 账本判定 | 三条均 `TRACKED`（断言「git 里有这个 blob，clone 后引用成立」） |
| main 的提交结构 | `cb6c562` 只有 **1 个父提交**（`git cat-file -p` 实测） |
| 产物的原提交 | `8023bb0`（m4829 分支）确实包含这三个 blob（`git show --stat` 实测） |
| 账本规模 | 152 篇文档 / 879 条指针 |

## 2 怎么做的

1. **复现**：`git clone` 到临时目录（= 干净 clone 语义）后跑该门禁文件 → 14 passed / 1 failed，
   失败输出只有 `+/-` 三行状态差。
2. **归因（不猜，用 git 断言）**：`git rev-list --parents -n1 cb6c562` = 单父；
   `git ls-tree -r cb6c562 -- artifacts/m4829_ci_gate` 为空，而 `8023bb0` 的 `--stat` 里三个文件都在。
   即：**文档与账本随合并到了 main，被它们引用的 blob 没有到**。这不是账本「过期」，
   而是账本对 git 的断言在 main 上为假。
3. **修复（最小）**：`git checkout 8023bb0 -- artifacts/m4829_ci_gate`，把三个 blob 原样恢复。
   账本与文档一个字节都不用改（`--check` 立刻 0），阈值/白名单也一律不动。
4. **加固（这次踩到的判别缺口）**：`--check` 原先把「账本说有、树里没有」与普通过期混在同一个
   `+/-` 列表里，诱使下一个人用「重生成账本」清红——那会把文档声称的证据**降级**成 `MISSING`，
   红转绿但证据消失。现在 `lost_from_history()` 单独把它们点出来，并直接写明该恢复而不是重生成：
   `! docs/ci_clearance_m4829.md:21 artifacts/m4829_ci_gate/gate_evidence.json -> MISSING`。
   配 5 条控制测试（仍在 / 文档已不再引用 / 本来就没 TRACKED 三条**非**丢失 + 丢失 + 端到端诊断）。
5. **证据脚本**：`scripts/m4857_ci_gate_evidence.py` 把门禁的**两个输入都钉到修订**——
   `--check` 读的账本与该修订 `git ls-tree` 的 tracked 集。只钉账本不钉索引会让工作树里恢复的
   blob 把回归**遮住**（脚本第一版就出现了这个假绿，已修）。

## 3 计算结果（程序化注入，零手抄）

| 被引用产物 | main 账本判定 | main(cb6c562) 的 git 树 | 修复提交(c707c98) 的 git 树 |
|---|---|---|---|
| `gate_evidence.json` | TRACKED | **无** | 有 |
| `provenance_gate_matrix.png` | TRACKED | **无** | 有 |
| `ledger_regeneration.png` | TRACKED | **无** | 有 |

| 指标 | main `cb6c562` | 修复 `c707c98` |
|---|---|---|
| 门禁 `--check` 退出码 | 1 | 0 |
| 诊断是否点名丢失 blob | True | False |
| 账本记 `TRACKED` 而树里没有的 blob 数 | 3 / 3 | 0 |
| 两个提交之间 `docs/` 的差异 | True（文档逐字节相同，唯一变量就是 blob 在不在） | 同 |
| 门禁文件测试 | 14 passed / 1 failed | **19 passed**（+5 控制） |

## 4 结果图

左：三条被引用 blob 的「账本断言 vs git 现实 vs 修复后」三列对照，红=不在 git；
右：门禁退出码从 main 的 1 变为修复后的 0。数值全部由 `gate_evidence.json` 程序化读出。

**关于「场量云图/与解析解比较曲线」**：本单无物理场量、无解析解基准（对象是 git 树与账本的一致性），
因此不渲云图；替代的定量对照是上面这张门禁判定矩阵 + 退出码条形图，其基准即 main 的实测退出码 1。

## 5 注意点

- **单父「合并」会丢 blob**：merge-master 落到 main 的是单父提交，文本文件随行、
  三个产物（含两个二进制 png）没跟上。账本与文档一致地到了 main，只有 blob 缺席——
  这正是「文件级证据」门禁应当抓住、也确实抓住的形态。
- **不要用重生成账本清红**：对这类红，重生成会把 `TRACKED` 静默改判 `MISSING`，
  CI 变绿但 m4829 文档的溯源主张变成无凭。恢复 blob 才是正确修复方向。
- **证据脚本自己踩过的坑**：只钉账本不钉 tracked 集时，工作树里恢复的 blob 让 main 的账本
  「看起来是新的」，`--check` 假绿返回 0。钉住两个输入后 main 才如实返回 1。
- **全量测试的诚实交代**：本机跑 `python -m pytest -q`（1672 个用例）时，整跑在 ~90% 处被宿主回收
  （无汇总行），分段复跑中出现两处**与本改动无关**的顺序相关失败
  （`tests/test_threefield_fragmentation_analytic.py::WeibullFitRecoveryTests::test_cdf_agreement_r2_high_for_weibull_data`
  → `KeyError: 'r2'`，单独跑 24 例 / 46 例均通过）。本单只改 `scripts/audit_doc_evidence.py`、
  该门禁测试文件与 `artifacts/`（未触碰 `src/`、未触碰那两处测试），故这些不在本单修复范围，
  也未在本机获得「1672 全绿」的单一汇总证据——CI 的最终裁决以 runner 上的整跑为准。

## 6 误差判定

本单的判据全是**离散量**（退出码、blob 在/不在、指针状态计数），由脚本从 git 与账本重算，
不是估计量：

| 关键量 | 基准（main 实测） | 修复后实测 | 误差 |
|---|---|---|---|
| 门禁退出码 | 1 | 0 | 离散量，逐位相等（0%） |
| 丢失 blob 数 | 3（账本断言 3 个 TRACKED，树里 0 个） | 0 | 0% |
| 门禁测试用例 | 14 passed / 1 failed | 19 passed / 0 failed | 0% |

**是否 <3%**：是——所有关键量都是精确整数/布尔，程序化重算两次一致，误差 0%。
本单不涉及物理量，故不存在「vs 实验/解析解」的百分比误差可报。未完成项如上（整跑无单一汇总证据）。
