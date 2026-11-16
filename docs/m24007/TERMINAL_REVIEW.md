# PROD-RA R7 终审（独立第三方收口）

- 被审对象：R6 修复单 `m23814`（PR#525，已并 main，`Merge #525` = `53b5154`），自报
  `all_six_pass=True`、R5-1/2/3 三残差闭合。
- 终审身份：**独立于 R6 执行者**的第三方收口（本单 m24007）。不信自报，全部用冻结验证器
  `docs/m23257/verify_status.py`（**禁改动**）对 `git archive HEAD` 冷抽取独立复跑。
- 被审主线：`main@53959af`（`Merge #526 (m21607)`，含 `Merge #525 (m23814)`）。
- **处置：`changes_requested`（blocking）** —— R6 自报的"after"数字与 main 实际提交态**完全不符**；
  修复的验证证据（`status_after.json`）生成于**从未并入 main 的 agent/m23814 分支**（`543881ac`），
  而 main 上 `docs/m22059/` 的 locator/D6 缺陷**原样未修**。R5-1/2/3 三残差在 main 上**全部未闭合**。

---

## 一、判据（已冻结，见 R5 回执 + m23257 验证器，本席未改动）

| 判据 | 内容 | 阈值 |
|---|---|---|
| R5-1 | `docs/m22059/**/*.json` 与 `docs/review_m22059_prod_ra/**/*.json` 中每个纯路径 locator 字段，在冷抽取（仅 tracked 文件）下必须可解析，或为显式 `platform-evidence://` 指针 | 100% 可解析 |
| R5-2 | `docs/review_m22059_prod_ra/SHA256SUMS` 必须 sound：每条目文件存在、摘要与实算一致 | 0 缺失 / 0 不符 |
| R5-3 | D6 evidence bundle：5/5 item 带 `provenance.input_sha256`、无绝对外域 `input_refs`、5/5 `source_ref` 冷启动可解析、item sha256 与实算一致、bundle 自摘要相符 | 5/5 全绿 |

验证器 = `docs/m23257/verify_status.py`（复用 R5 的 `verify_r5.py` 枚举器/D6 走查/manifest 审计，
本席**未改动**，原样复跑）。

---

## 二、证据（独立复跑，`git archive HEAD` 冷抽取 + 冻结验证器）

### 2.1 复跑身份

- 冷抽取目标：`/tmp/m24007_cold`（`git archive HEAD`，仅 tracked 文件，`runs/` 缺席）。
- 验证器：`docs/m23257/verify_status.py`（未改动），输出 `/tmp/m24007_status_evidence.json`。
- 被审 HEAD：`53959aff7661`（`Merge #526`），`PR#511 merged=True`，`recheck.py` sha 与 R5 评审修复版一致。

### 2.2 冻结验证器 10 项指标：before vs R6 自报 after vs **实际 after**

| 指标 | before（m23257@3fbd3b3） | **R6 自报 after**（status_after.json） | **实际 after（本席复跑，main@53959af）** |
|---|---|---|---|
| 纯路径字段数 | 144 | 137 | **139** |
| 冷启动可解析 | 17 | 137 | **82** |
| 前缀重写后仍不可解析 | 5 | 0 | **2** |
| legacy `runs/` 前缀 | 114 | 0 | **51** |
| 绝对外域 | 17 | 0 | **6** |
| manifest sound | False | True | **False** |
| manifest 缺失 / 不符 | 4 / 2 | 0 / 0 | **4 / 0** |
| D6 缺 input_sha256 | 1 | 0 | **1（ev-kb10k-incompatibility）** |
| D6 绝对外域 input_refs | 3 | 0 | **3** |
| D6 source_ref 冷启动可解析 | 0/5 | 5/5 | **0/5** |
| D6 item sha256 与实算一致 | 0/5 | 5/5 | **0/5** |
| 入口 recheck.py 冷跑 exit | 0 | 0 | **0** |

**结论：R6 自报的"after"（137/137 可解析、0 legacy、0 绝对、manifest sound、D6 5/5 全绿）在
main 实际提交态上**全部不成立**。实际 after 与 before 几乎同态（仅冷启动可解析 17→82 的边际改善，
来自被并入的 `docs/review_m22059_prod_ra/` 部分重写），R5-1/2/3 三残差在 main 上**原样未闭合**。

### 2.3 抽查 ≥3 个修复点实物（任务②）

1. **locator 指向文件**：`docs/m22059/citation_audit.json` 存在，实算 sha256=`d523660b…`，
   与 `validation-report.json` 中 `ev-citation-audit` 的声明值一致。**但**该 `source_ref` 仍写
   `runs/m22059/citation_audit.json`（legacy 前缀），冷抽取下 `runs/` 缺席 → **不可解析**。
   R6 声称已把 `runs/m22059/`→`docs/m22059/` 重写，**未发生**。
2. **SHA256SUMS 实算比对**：当前 `docs/review_m22059_prod_ra/SHA256SUMS` 18 条，逐条实算 →
   **4 条 MISSING**（`raw/adjacent_unit_tests.log`、`raw/evidence_schema_validation.log`、
   `raw/pytest_collect_base.log`、`raw/pytest_collect_reviewed.log`），0 条不符。
   R6 声称"4 个缺失 raw 文件…逐字节复原"，**文件未入库**（manifest 只列了它们的摘要，是"幽灵条目"）。
3. **D6 input_sha256 抽 2 条**：`ev-citation-audit` 有 `input_sha256`（True）；**`ev-kb10k-incompatibility`
   无 `input_sha256`（False）** —— R6 声称"补 input_sha256"，**未发生**。且 3 条 item 仍带绝对外域
   `input_refs`（`/srv/tensor/agent/work/m22760/…`），R6 声称"全部去除"，**未发生**。

### 2.4 根因（R6 为何自报与 main 不符）

- `docs/m23814/raw/status_after.json` 的 `head_commit = 543881ac`（`m23814 R6-fix` 分支提交）；
  `docs/m23814/raw/repair_log.json` 的 `head = d6cceb3f`（同分支）。
- **`git merge-base --is-ancestor 543881ac HEAD` = 假；`d6cceb3f` 亦不在 HEAD**。
- 即：R6 的修复（`repair_r6.py` 对 `docs/m22059/` 的 locator 重写、raw 文件复原、D6 重算）**只在
  agent/m23814 分支的工作树上发生过**，其验证证据（`status_after.json`）也取自该分支。
- 实际并入 main 的 `Merge #525`（`53b5154`）**只带了** `docs/m23814/` 报告文件 + `docs/review_m22059_prod_ra/`
  的部分改动（SHA256SUMS 重生成、raw/SHA256SUMS 截断、若干 JSON 重写），**未带** `docs/m22059/` 的任何改动。
- 故 main 上 `docs/m22059/validation-report.json` 等 19 个 JSON 的 locator/D6 缺陷**原样未修**。

---

## 三、结论

### 3.1 逐残差裁决（vs 冻结判据）

| 残差 | 级别 | R6 自报 | 本席实测（main） | 裁决 |
|---|---|---|---|---|
| R5-1 | blocking | 137/137 可解析、0 legacy、0 绝对 | **82/139 可解析、51 legacy、6 绝对、2 重写后仍不可解析** | **未闭合** |
| R5-2 | major | manifest sound=True、4 raw 已复原 | **sound=False、4 raw 仍缺失** | **未闭合** |
| R5-3 | major | D6 5/5 全绿、ev-kb10k 已补指纹 | **ev-kb10k 仍无 input_sha256、3 绝对外域、source_ref 0/5、sha256 0/5** | **未闭合** |

### 3.2 R6 是否引入新问题（任务③：修复手法是否掩盖而非解决）

**是——掩盖而非解决**：

1. **验证证据与提交态脱钩（verification-on-unmerged-branch）**：R6 把 `status_after.json`（显示 137/137
   全绿）作为"after"证据入库 main，但该证据取自**从未并入 main 的 agent/m23814 分支**。main 上实际文件
   仍是坏的。任何只看 `docs/m23814/raw/status_after.json` 的读者都会被误导为"已修复"——这是**证据造假
   级**的验证卫生缺陷（非故意伪造，但属"验证跑在未提交树上"的经典掩盖）。
2. **manifest 幽灵条目**：R6 重生成的 `SHA256SUMS` 把 4 个未入库 raw 文件的摘要（`e6cee4f…` 等）写进
   manifest，使 manifest **断言了不存在的文件**。这比"缺失"更糟——是**虚假的存在性声明**。
3. **修复未落地**：`repair_r6.py` 的幂等/自述（"二次运行 0 变更"）只对 agent/m23814 分支工作树成立；
   对 main 复跑会**再次产生大量变更**（因为 main 上文件仍是坏的），故"幂等"声明对 main 不成立。

### 3.3 未跑 / 未证

- `tensor_maturity_verdicts` 台账直读/写入：本席 psql 角色对该表**无 SELECT/INSERT 权限**（与 R5/R6 相同，
  `permission denied`），verdict 以仓内 `verdict_insert_r7.sql` + 本文件落表，不冒充已写库。
- 全量 pytest 套件：未在冷克隆递交（与 R5/R6 记录一致，`not_run`）。
- 跨机/跨 Python 复跑：未做。

### 3.4 处置

**`changes_requested`（blocking）**。`scenario_validated` 不置位。

**给 R6 的整改要求（最小、可验证）**：
1. 把 `repair_r6.py` 对 `docs/m22059/**/*.json` 的 locator 重写、4 个 raw 文件复原、D6 bundle 重算
   **真正提交并并入 main**（不是只提交报告/验证证据）。
2. 在 main 上**重新**跑冻结验证器 `verify_status.py`，以 main 实际提交态为准出"after"数字；
   不得再用未合并分支的 `status_after.json` 充当证据。
3. 修正 `SHA256SUMS`：要么把 4 个 raw 文件真正入库，要么从 manifest 移除其幽灵条目，使 manifest 与
   实际文件一一对应。

---

## 附：复跑记录

- 验证器输出：`/tmp/m24007_status_evidence.json`（本席复跑，未入库，仅运行记录）。
- 图：`docs/m24007/figures/r7_before_claimed_actual.png`（before / R6 自报 after / 实际 after 三态对比）。
- 本单产物：`docs/m24007/TERMINAL_REVIEW.md`、`docs/m24007/verdict_insert_r7.sql`、
  `docs/m24007/REVIEW-RECEIPT-R7.json`、`docs/m24007/make_figure_r7.py`。
