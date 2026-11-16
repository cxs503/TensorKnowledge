# PROD-RA R5：m22059 残差修复（m23111 / PR#511）终点复审

- 被审主线：`origin/main@cbd754bbe`（`Merge #510 (m20865) via merge-master`）
- 修复件：PR#511 = `d1d5c49`（`origin/agent/m23111` 尖端）。**实测该 commit 尚未并入 main**（`git merge-base --is-ancestor d1d5c49 origin/main` 为假），故本轮以冷克隆 main + 单独取 `d1d5c49` 版 `recheck.py` 的方式分别核验"主线现状"与"修复件主张"
- 判据基准：`tensor_maturity_verdicts` 行 903（12 条缺陷原文，D6 即其一）＋ 行 918（R4 五条残差 R4-1…R4-5）＋ `REPAIR-NOTES.md`（m23111）逐条自述
- **处置：`changes_requested`（窄口径）** —— R4-2 实质修复并经实跑证实，六检在修复件上复跑全过；但 R4-1 **未修复**（残差原样，且交付分支根本没带上该改动），R4-3 未动，D6 的 1/5 输入指纹缺口与绝对外域引用仍在。`scenario_validated` 本席不置位。

## 1. 案例介绍（审的是什么、判据是什么）

被测对象是一个"研究断言审计"产物包：`docs/m22059/validation-report.json` 及其证据束（5 条 evidence item、11 条 claim 记录、负向语料、失败台账、回归范围声明），外加作者席交付的复审入口 `docs/review_m22059_prod_ra/recheck.py`。判据不是物理精度，而是**可复现性与可移植性**这两条契约：

1. 任一条 finding 必须能在**纯仓内、无外部工作树**的条件下从被引来源复现（PRD 的 source-span 条款）；
2. 复审入口在同一条件下必须 `exit 0` 并产出六节结果。

参数表（全部为被测包实测规模）：

| 量 | 值 |
|---|---|
| 证据 item 数 | 5 |
| claim 记录数 | 11 |
| 失败台账记录数 | 3 |
| 文件级 locator 字段数（本席口径，见 §5） | 144 |
| 审阅包 manifest 条目数 | 18 |
| 冷克隆（第三人视角） | `/tmp/cold_r5` @ main，**未挂载** `/root/tp-agent/work/m22059` |

## 2. 怎么做的（方法与工具链）

1. **冷启动克隆**：把 main 尖端克隆到独立目录，确认 `runs/m22059` 不存在 —— 模拟第三人拿到仓库时的条件。
2. **locator 枚举器**（`verify_r5.py::collect_locators`）：递归遍历 `docs/m22059/**/*.json` 与 `docs/review_m22059_prod_ra/**/*.json`，取所有形如路径的字符串（以及命令串里的路径 token），逐个在冷克隆根下解析；对 `runs/m22059/X` 另做一次"机械前缀重写"解析，以区分"仅前缀坏"和"内容缺失"。
3. **入口点实跑**（`verify_r5.py::main` 的 B 段）：五个变体——主线 as-shipped ×（冷克隆、旧工作树、补齐 runs/ 布局）、PR#511 修复件 ×（冷克隆、旧工作树）；逐次记录 exit_code 与 stderr 末行。
4. **D6 复算**：5 条 evidence item 逐条 `jsonschema` 校验（`TensorBench/schemas/evidence-item.schema.json`），检查 `provenance.input_sha256`/`input_refs` 存在性、`source_ref` 冷启动可解析性、`source_ref` 实算 sha256 与声明值比对，并用 `tensorbench.criteria.canonical_sha256` 复算 bundle 自摘要。
5. **六检复跑**：直接用修复件 `recheck.py` 在冷克隆上产出六节结果，再由 `six_checks()` 按**成文语义**判定（`citation_audit` 在无语料目录时 `inconclusive`+exit 1 是 R4-5 已接受的既有局限，判别力在 finding 集，故不按 exit 0 判负）。
6. **manifest 审计**：18 条 `SHA256SUMS` 逐条实算。

## 3. 计算结果

### 3.1 R4-1（locator 冷启动可解析性）

| 口径 | 数量 |
|---|---|
| file locator fields (path-valued JSON strings) | 144 |
| of which still use the legacy runs/m22059/ prefix | 114 |
| of which are absolute refs into a foreign worktree (/root/tp-agent/...) | 17 |
| resolved by a cold clone as-is | 17 |
| resolved only after a mechanical runs/ -> docs/ rewrite | 122 |
| unresolvable even after that rewrite | 5 |
| all path tokens searched (commands included): total / unresolved | 200 / 182 |

冷启动未解析率 = **88.2%**（127/144），与 R4 的 96 处口径差异见 §5。

### 3.2 R4-2（复审入口实跑 exit_code）

| 变体 | exit_code | stderr 末行 |
|---|---|---|
| as_shipped | 1 | FileNotFoundError: [Errno 2] No such file or directory: '/tmp/co |
| as_shipped_legacy_target | 1 | FileNotFoundError: [Errno 2] No such file or directory: '/root/t |
| as_shipped_prepared_runs_layout | 1 | KeyError: 'item_id' |
| fixed_cold_start | 0 | (no stderr) |
| fixed_legacy_target | 0 | (no stderr) |

结论：修复件在**冷克隆与旧工作树两种条件下均 exit 0**；主线 as-shipped 在两种条件下均失败（冷启动是 `FileNotFoundError: runs/m22059/...`；补齐 runs/ 布局后即复现 R4-2 的 `KeyError: 'item_id'`）。R4-2 修复成立。

### 3.3 D6（evidence bundle 逐项核，行 903 缺陷 + 行 918 残差）

| evidence_id | schema | input_sha256 | source_ref 冷启动可解析 | sha256 实算一致 | 绝对外域 input_refs |
|---|---|---|---|---|---|
| ev-citation-audit | ok | yes | NO | NO | - |
| ev-claim-evidence-audit | ok | yes | NO | NO | /root/tp-agent/work/m22760/runs/m22059/audit_corpus/ |
| ev-negative-citation | ok | yes | NO | NO | - |
| ev-negative-claim-evidence | ok | yes | NO | NO | /root/tp-agent/work/m22760/runs/m22059/negative_test |
| ev-kb10k-incompatibility | ok | NO | NO | NO | /root/tp-agent/work/m22760 |

- schema：**5/5** 通过；bundle 自摘要 `canonical_sha256` 复算 = 声明值（True）。
- 输入指纹：**4/5** 带 `provenance.input_sha256`，缺口是 `ev-kb10k-incompatibility`（目录树型输入）。
- 冷启动：`source_ref` **0/5** 可解析 —— D6 的形状缺陷已修，但**引用可移植性未修**。

### 3.4 六检复跑（修复件，冷克隆）

| 检查 | 判定 | 实测 |
|---|---|---|
| 1 artifact_identity | PASS | 2/2 input digests match |
| 2 criteria frozen | PASS | canonical sha256 match=True |
| 3 evidence traceability | PASS | unresolvable=0 |
| 4 independent rerun | PASS | claim audit passed; negatives detected |
| 5 failure record | PASS | 1/5 items without input_sha256 |
| 6 regression scope | PASS | 12 passed, 1 warning in 0.13s |

`all_six_pass = True`。

### 3.5 审阅包 manifest（R4-3）

- 条目 18，缺失 4（raw/adjacent_unit_tests.log, raw/evidence_schema_validation.log, raw/pytest_collect_base.log, raw/pytest_collect_reviewed.log），摘要不符 1（raw/SHA256SUMS：声明为**空串摘要** `e3b0c442…b855`，实际 `ac75e224…cda`）。

## 4. 图

1. `figures/r5-locator-coldstart.png` —— 144 个文件级 locator 的冷启动解析分类（已解析 / 仅机械重写后可解析 / 重写也不可解析）。
2. `figures/r5-entrypoint-exitcodes.png` —— 复审入口五个变体的实测 exit_code 与失败原因（同一脚本，两种条件下结论相反）。
3. `figures/r5-sixchecks-d6.png` —— 六检判定与 D6 复算摘要（论文式状态表）。

## 5. 注意点（踩过的坑 / 局限 / 适用范围）

1. **"exit_code=0" 在本案不是验收证据**：修复件 `recheck.py` 的 `main()` 以**无条件 `return 0`** 收尾（第 231 行），任何检查结论都不改变进程退出码；m23111 自述"实跑 exit_code=0"只能证明脚本跑通。本轮改以六节结果本身判定。
2. **修复件里有一个假失败信号**：`recheck.py:214` 在 item 顶层取 `input_sha256`，而 D6 修复后该字段嵌在 `provenance` 内，于是它把 **5/5** item 都报成"无指纹"；独立复算是 **4/5 有指纹**。作者把这解释为"报告口径问题"，本席同意该解释，但这恰恰说明该脚本不能作为验收工具。
3. **locator 计数口径**：R4 记 96 处，本席记 144 个"路径型 JSON 字段"（含负向语料与审阅包内 JSON；命令串内的路径另计，共 200 个 token）。两者不矛盾，是范围不同；判定不依赖具体数字，而依赖"冷启动解析率 = 11.8%"。
4. **m23111 修的是"另一个工作树"而不是"仓内可移植"**：其本地版本把 `/root/tp-agent/work/m22760/` 改成 `/root/tp-agent/work/m23111/`，仍是外域绝对路径；即便该改动进了主线，冷启动解析率也不会归零。且该改动（`docs/m22059/` 7 个 JSON + `REPORT.md` 等）**未出现在交付分支** `d1d5c49` 上（该 commit 相对 main 只动了 `recheck.py` 4 行 + `REPAIR-NOTES.md`）。
5. **台账不可直读**：本席 psql 角色对 `tensor_maturity_verdicts` 无 SELECT 权限，行 903/918 的原文取自仓内 `REVIEW-R4.md` 的引用；如协调者需绝对独立，应在有读权限的席位复核一次。
6. **全量 pytest 未跑**（冷克隆内未递交全量套件），只跑相邻审计器单测 12 passed；不冒充全量。
7. 适用范围：本判定只对"文档/证据包可复现性"，不含 PRD 语义精度（无语料 holdout，仍是 not_measured）。

## 6. 误差判定（逐项 vs 判据，显式回答是否 <3%）

本案无物理量基准，判据是"必须为 0 的不合规计数"。故逐项给出实测率与判据阈值（0%），并显式回答：

| 关键量 | 实测 | 判据 | 偏差率 | 是否 <3% |
|---|---|---|---|---|
| 冷启动不可解析的 locator 字段 | 127/144 | 0 | **88.2%** | **否** |
| D6 无输入指纹的 evidence item | 1/5 | 0 | **20.0%** | **否** |
| evidence `source_ref` 冷启动不可解析 | 5/5 | 0 | **100.0%** | **否** |
| manifest 不成立条目 | 5/18 | 0 | **27.8%** | **否** |
| 六检不通过数（修复件） | 0/6 | 0 | **0.0%** | **是（0%）** |
| D6 evidence-item schema 不合规 | 0/5 | 0 | **0.0%** | **是（0%）** |
| bundle 自摘要不符 | 0/1 | 0 | **0.0%** | **是（0%）** |
| 复审入口实跑（修复件，冷克隆） | exit 0 | exit 0 | 0% | **是** |

**总判**：项目级判据（locator 冷启动解析、输入指纹、manifest）未达标，偏差率双位数百分比，远超 3% 阈值；只有 D6 的形状类判据与六检达标。故 `changes_requested`，`scenario_validated` 不置位。

## 7. 未跑 / 未证

- full pytest suite in the cold clone (suite is large; the reviewed bundle records not_run for it too)
- cross-machine / cross-python rerun
- verbatim audit of all 15 criteria against matrix/PRD (unchanged from R4: 7 sampled)
- tensor_maturity_verdicts rows 903/918 read-back (psql role lacks SELECT on that table; texts used come from the in-repo quotations in docs/review_m22059_prod_ra/REVIEW-R4.md)
