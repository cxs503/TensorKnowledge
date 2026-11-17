# RA R8 修复报告（m24117）：把 R6 修复真正并入 main 的提交态

- 战役锚点：PROD-RA（R7 终审 `changes_requested` 后的返修单）
- 被返修对象：R6 修复 `e4d086e`（agent/m23814 分支，从未并入 main 的修复本体）
- 本单分支：`agent/m24117`，修复提交 `1ad7b60`（cherry-pick `-x` of `e4d086e`）
- 验证器：`docs/m23257/verify_status.py`（冻结，本单未改动）
- 证据：`docs/m24117/raw/status_after_m24117.json`（冷抽取 `git archive HEAD` 复跑）

---

## ① 案例介绍

PROD-RA 评审束（`docs/m22059/` + `docs/review_m22059_prod_ra/`）承载 m22059 的
claim-evidence 审计证据链。R5 独立复审（m23157）冻结了三条残差判据：

| 判据 | 内容 | 阈值 |
|---|---|---|
| R5-1 | 两个目录下每个纯路径 locator 字段在冷抽取（仅 tracked 文件）下可解析，或为显式 `platform-evidence://` 指针 | 100% 可解析 |
| R5-2 | `SHA256SUMS` sound：每条目文件存在、摘要与实算一致 | 0 缺失 / 0 不符 |
| R5-3 | D6 evidence bundle：5/5 带 `provenance.input_sha256`、无绝对外域 `input_refs`、5/5 `source_ref` 冷启动可解析、item sha256 与实算一致、bundle 自摘要相符 | 5/5 全绿 |

R6（m23814）自报三残差闭合，但 R7 终审（m24007，verdict 行 931）证伪：修复只在
agent/m23814 分支发生过，`Merge #525` 未携带 `docs/m22059/` 的任何修复。main@53959af
实测：冷解析 82/139、legacy 51、绝对外域 6、manifest sound=False（4 个 raw 幽灵条目）、
D6 缺 input_sha256 1 + 绝对外域 3 + source_ref 冷启动 0/5。

## ② 怎么做的

1. **找回修复（禁手抄）**：`git cherry-pick -x e4d086e` 到 `agent/m24117`（基于
   origin/main@5319f99）。git 自动跳过 main 上已存在的同内容文件（`docs/m23814/` 报告、
   `docs/review_m22059_prod_ra/` 的 10 个 JSON——这些已由 #525 带入），干净落盘 11 个文件：
   - `docs/m22059/` 7 个 JSON 的 locator 字段级重写（114 legacy `runs/` 前缀 → 仓内、
     12 绝对路径 → 仓内、5 裸 worktree 根 → `platform-evidence://` 指针、8 个 `#sha256:`
     片段刷新为实算摘要）；
   - `docs/review_m22059_prod_ra/raw/` 4 个 raw 文件逐字节入库（sha256 与 manifest 声明一致）；
   - D6 bundle 重算（5 个 item sha256 实算、ev-kb10k-incompatibility 补
     `provenance.input_sha256`（目录摘要约定）、3 条绝对外域 `input_refs` 去除、
     `bundle_sha256` 按 `tensorbench.criteria.canonical_sha256` 重算）。
2. **逐字节核对**：`git diff HEAD e4d086e -- docs/m22059/ docs/review_m22059_prod_ra/
   docs/m23814/` 为空 → 修复文件与分支态完全一致，无手抄。
3. **幂等性保留验证**：在修复后的树上复跑 `docs/m23814/repair_r6.py` →
   `locator_fields_changed=0 sha_fragments_refreshed=0 manifest_entries=18`，
   `git status` 仅 `docs/m23814/raw/repair_log.json`（运行日志追加，设计使然）有变化，
   内容文件 0 变更（`raw/idempotency_rerun.json`）。
4. **冷抽取复跑冻结验证器**：`git archive HEAD` → `/tmp/m24117_cold`（3991 文件，
   `runs/` 缺席）→ `docs/m23257/verify_status.py` 原样复跑（未改动）。
5. **并 main 模拟**：`origin/main` 上 `git merge --no-ff agent/m24117`（模拟平台
   merge-master）→ 合并提交 `51a3fee` 与分支 HEAD 树完全一致（`git diff` 为空），
   对合并提交再复跑验证器，数字不变。

## ③ 计算结果（程序化注入，零手抄）

冻结验证器 10 项指标，四态对比（R8 列读自 `raw/status_after_m24117.json`）：

| 指标 | before (m23257) | R6 自报 after | R7 实测 (main@53959af) | **R8 修复后 (1ad7b60)** |
|---|---|---|---|---|
| 纯路径字段数 | 144 | 137 | 139 | **137** |
| 冷启动可解析 | 17 | 137 | 82 | **137 (100%)** |
| 前缀重写后仍不可解析 | 5 | 0 | 2 | **0** |
| legacy `runs/` 前缀 | 114 | 0 | 51 | **0** |
| 绝对外域 | 17 | 0 | 6 | **0** |
| manifest sound | False | True | False | **True** |
| manifest 缺失 / 不符 | 4 / 2 | 0 / 0 | 4 / 0 | **0 / 0** |
| D6 缺 input_sha256 | 1 | 0 | 1 | **0** |
| D6 绝对外域 input_refs | 3 | 0 | 3 | **0** |
| D6 source_ref 冷启动可解析 | 0/5 | 5/5 | 0/5 | **5/5** |
| D6 item sha256 与实算一致 | 0/5 | 5/5 | 0/5 | **5/5** |
| 入口 recheck.py 冷跑 exit | 0 | 0 | 0 | **0** |

- 纯路径字段数 139→137 的原因：5 个裸 worktree 根 locator 被重写为显式
  `platform-evidence://worktree/<mid>` 指针（判据允许的形态），其中 2 个字段所在文件
  不再含任何纯路径 token，故计数下降——不是字段丢失。
- D6 bundle 自摘要：`bundle_sha256 = 19cf7160c094f5a89d4ff9a842a12c9819afcabf4d3e88e3ef0e27a730e45cc8`
  （`tensorbench.criteria.canonical_sha256`，重算=声明）。
- 4 个 raw 文件逐字节核验（实算 sha256 = manifest 声明）：
  `adjacent_unit_tests.log e6cee4f8…`、`evidence_schema_validation.log 3f92deed…`、
  `pytest_collect_base.log 5967a6b8…`、`pytest_collect_reviewed.log 4c020fde…`。
- 幂等性：修复后树上复跑 `repair_r6.py` → `locator_fields_changed=0
  sha_fragments_refreshed=0 manifest_entries=18`，内容文件 0 变更（仅运行日志追加，
  设计使然；`raw/idempotency_rerun.json`）。
- 并 main 模拟：`origin/main` 上 `git merge --no-ff agent/m24117` → 合并提交 `51a3fee`
  与分支 HEAD 树完全一致（`git diff` 为空）；对合并提交复跑冻结验证器，数字不变。

## ④ 结果图

`figures/r8_four_state.png`：冻结验证器 10 项指标在 before / R6-claimed / R7-actual /
R8-fixed 四态的对比（R8 列程序化读自 `raw/status_after_m24117.json`，其余三态读自
冻结的 R7 回执 `docs/m24007/REVIEW-RECEIPT-R7.json`，零手抄）。本单为文档/证据完整性
任务，无场量云图；该对比图即本单的核心结果图。

## ⑤ 注意点

- **验证必须跑在提交态**：R6 的教训是"验证跑在未合并分支上"。本单所有 after 数字取自
  `git archive HEAD` 冷抽取（3991 文件，`runs/` 缺席），且对模拟合并提交（`51a3fee`，
  与分支 HEAD 树完全一致）复跑复核，数字不变。
- **纯路径字段数 139→137 不是丢失**：5 个裸 worktree 根 locator 按判据允许的形态重写为
  `platform-evidence://worktree/<mid>` 显式指针，其中 2 个字段所在文件不再含纯路径 token。
- **verdict 行**：本席 psql 角色对 `tensor_maturity_verdicts` 无 SELECT/INSERT 权限
  （验证器探针 `permission denied`，已如实记录），verdict 行由协调者落表。
- **未跑**：全量 pytest 套件（冷克隆）、跨机/跨 Python 复跑（与 R5/R6/R7 记录一致，
  `not_run`）。
- 4 个 raw 文件的复原源是 m22508 worktree（机器本地路径）；文件已入库且 sha256 与
  manifest 声明逐字节一致，后续不再依赖该本地路径。

## ⑥ 误差判定

本单无物理量，关键量 = 冻结验证器 10 项指标。基准 = 冻结验证器对提交态的独立重算
（`raw/status_after_m24117.json`）；自报数字程序化注入自该 JSON，逐项偏差 **0%（<3%，
精确相等）**：

| 关键量 | 自报 | 基准（验证器重算） | 偏差 | <3%? |
|---|---|---|---|---|
| 纯路径冷解析 | 137/137 | 137/137 | 0 | 是（精确相等） |
| legacy 前缀 | 0 | 0 | 0 | 是 |
| 绝对外域 | 0 | 0 | 0 | 是 |
| manifest sound | True | True（18 条 0 缺失 0 不符） | 0 | 是 |
| D6 全绿 | 5/5 | 5/5（input_sha256/abs_refs/src_cold/sha256/bundle） | 0 | 是 |
| bundle_sha256 | 19cf7160… | 19cf7160…（canonical_sha256 重算=声明） | 0 | 是 |

**结论：R5-1/2/3 三残差在提交态上全部闭合；自报与独立重算零偏差。**
