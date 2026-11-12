# TensorDEM main CI 清红（m4829）：runner 路径断言与证据账本过期

## ① 案例介绍

**对象**：TensorDEM（冰区船舶结构/冰载荷离散元库）仓库 `main@524821fd`（Merge #343）的 CI 红项。
本单不含任何物理/数值任务，红项全部落在**验证门禁**层：一条把 CI runner 挂载目录名当成不变量的
溯源测试，以及一份过期且含失效指针的文档证据账本。

**环境/输入参数表**（判据可机器裁，故列全）：

| 项 | 值 |
|---|---|
| 被测提交（修复前） | `524821fd` |
| 证据生成提交 | `524821f` |
| 架构 | loongarch64（自托管 runner `ci-loong64`，workflow 为 `runs-on: ci-loong64`） |
| 测试入口 | `python -m pytest -q`（CI 的 `unit-tests` 作业） |
| 关键量 1 | `check_provenance()` 判定（布尔 gate） |
| 关键量 2 | 证据账本 扫描文档数/指针数/逐状态计数（整数） |
| 关键量 3 | 失效指针 ORPHAN 数（整数，须为 0） |

## ② 怎么做的

1. **逐条归因（不猜）**
   - `test_provenance` 断言 `os.sep + "work" + os.sep in path`：GitHub 托管 runner 目录是
     `/home/runner/work/<repo>/<repo>`（含 `/work/`），自托管 runner 检出在 `.../_work/<repo>/<repo>`
     （只有 `_work/`）。同一棵干净的树，只换挂载前缀就红/绿翻转——断言测的是 runner，不是仓库。
   - `test_cited_source_docs_and_tests_are_tracked`：`docs/threefield_fragmentation_analytic_verification.md`
     把子包路径写成 `fragmentation.py`（漏 `src/tensordem/threefield/` 前缀）→ `code:MISSING`。
   - `test_committed_ledger_is_current`：`docs/doc_evidence_ledger.json` 冻结在 145 篇/831 条，
     m4819 合并后树里已有 151 篇（本单完成后 152 篇），且 `artifacts/m4812_ledger_negative_controls/`
     三产物被门禁滤除后账本仍记 `TRACKED`。
2. **修门禁而非放松门禁**：`check_provenance(module_path=None)` 支持注入被测路径；测试断言改为
   「解析后落在本树 `src/tensordem/__init__.py`」，并新增负控 `test_provenance_rejects_a_foreign_tree`
   （外部 checkout 必须 `RuntimeError`），防止判定退化为恒真；顺手清零该文件 3 条 F401。
3. **账本重生成**：`python scripts/audit_doc_evidence.py --json docs/doc_evidence_ledger.json`，
   `--check` 复核 `ledger up to date`。
4. **证据程序化**：`scripts/m4829_ci_gate_evidence.py` 从 `git show HEAD:docs/doc_evidence_ledger.json`
   与工作树账本直接读计数、逐布局复算两代门禁，输出
   `artifacts/m4829_ci_gate/gate_evidence.json` 与两张图（零手抄）。
5. **端到端复现**：整树复制到 `/tmp/_work/TensorDEM/TensorDEM`（自托管布局同形），
   `main` 版测试 → 1 failed（红项复现）；修复版 → 20 passed。

## ③ 计算结果

**溯源门禁逐布局判定**：

| 检出布局 | main 门禁（"/work/" in path） | 修复后门禁（须落在本树 src/tensordem） |
|---|---|---|
| github-hosted (/home/runner/work/...) | PASS | PASS |
| self-hosted loong64 (.../ci_env/_work/...) | FAIL | PASS |
| agent worktree (/root/tp-agent/work/m4829) | PASS | PASS |
| tmp sandbox (/tmp/_work/TensorDEM/TensorDEM) | FAIL | PASS |
| negative control (foreign checkout) | FAIL | FAIL |

**证据账本计数**：

| 量 | 提交态（过期） | 重生成后 |
|---|---|---|
| 扫描文档数 | 145 | 152 |
| 指针数 | 831 | 879 |
| `code:TRACKED` | 275 | 290 |
| `test:TRACKED` | 251 | 263 |
| `data:MISSING`（可重建） | 44 | 47 |
| 判 `TRACKED` 占比 | 0.8472 | 0.8476 |
| 失效指针 ORPHAN | 0 | 0 |

状态翻转 3 条（三产物 TRACKED→MISSING+REGENERABLE），
新增指针 51 条（36 条来自 m4819 合并文档，15 条来自本清红文档与产物）。

**验证执行**：

| 命令 | 结果 |
|---|---|
| `pytest -q tests/test_doc_evidence_pointers.py tests/test_dem2d_fracture_ledger.py` | 20 passed |
| 同上，整树复制到 `/tmp/_work/TensorDEM/TensorDEM`（自托管布局同形） | 20 passed |
| `main` 版测试文件在 `/tmp/_work/...` 布局下 | 1 failed（红项复现） |
| `pytest -q`（账本相关 4 文件） | 36 passed |
| `audit_doc_evidence.py --check` | `ledger up to date` |
| `ruff check`（改动 3 个 py） | All checks passed |

## ④ 结果图

图 1：两代门禁 × 四种检出布局的判定矩阵（红 FAIL / 绿 PASS）；唯一仍 FAIL 的是负控（外部 checkout），
这是门禁应有的行为。图 2：账本逐状态计数重生成前后对比，增量全部落在 `code/test/doc:TRACKED`
与可重建 `data:MISSING`，ORPHAN 保持 0。

## ⑤ 注意点（坑与局限）

- **门禁不能测 runner**：依赖 `cwd`、`/home/runner`、`$GITHUB_WORKSPACE` 或目录名的断言在自托管
  runner 上必假红；判据须是仓库内不变量。
- **不能靠删断言清红**：必须有负控（本单 `test_provenance_rejects_a_foreign_tree`）。
- **账本重生成要如实**：被门禁滤除的产物降级为 `MISSING + REGENERABLE`（producer 在树内），
  不能手改回 `TRACKED`。
- **集群不适用**：外协方双节点 loong64 环境缺 `libflexiblas.so.3`/`scipy`，`pytest` 收集期即
  130 errors（环境缺库，与代码无关），故全量只在本地 loongarch64 跑。
- **honest-FAIL**：本轮未把 `python -m pytest -q` 全量跑完（harness 单次 shell 上限 120 s，
  后台进程被回收）。已跑的定向套件 36 passed 覆盖全部改动面，但「全量 0 failed」只能由 CI 给出。

## ⑥ 误差判定

本单关键量均为布尔门禁与整数计数，判据是**精确相等**：

| 关键量 | 基准 | 实测 | 误差 | 是否 < 3% |
|---|---|---|---|---|
| main 门禁在自托管布局 | 应 PASS（树干净） | FAIL（假红） | 判定错误（非数值） | 不适用（布尔） |
| 修复后门禁在自托管布局 | PASS | PASS | 0 | 是（0%） |
| 负控（外部 checkout） | 必须 FAIL | FAIL（RuntimeError） | 0 | 是（0%） |
| 账本扫描文档数 | 树内 md 实数 | 152 = 实数 | 0 | 是（0%） |
| 账本 ORPHAN 数 | 0 | 0 | 0 | 是（0%） |
| 账本 TRACKED 占比 | > 0.60（非空洞阈值） | 0.8476 | +0.2476 | 是 |

结论：可比关键量全部精确匹配（0% 误差），满足 <3% 判据；未完成项仅「全量套件端到端」，
故本单不自称 CI 已绿，只声明三处红项根因已修复并在同形环境复现—验证通过。
