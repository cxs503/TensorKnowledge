# 质量门复绿：TensorKnowledge `Validate knowledge assets` main-red 根因与修复（mission 17202）

锚点 `FEAT-TK-VALIDATE-GREEN`；CI run 43349700247 / job 131637481275；分支 `agent/m17202`；基线 main `5c85d2f`。

## 1. 现象（Observation）

- CI job 报 `knowledge/sediment/sloshing-impact-lbm: verifier scripts/verify_sediment_sloshing.py failed (rc=1)`，whole gate 红。
- 本地**完整复现**（见 `scripts/repro_ci_validate_knowledge_assets.sh`，一次性脚本建 venv 模拟 runner）：

  | 场景 | 解释器依赖 | 只读源仓 | 结果 |
  |---|---|---|---|
  | 修复前 + CI 真实条件（workflow 无 pip 步） | 无 `jsonschema` | 缺失 | 5 条错误：4 条 schema + **`verifier ... failed (rc=1)`**（与 CI 日志逐字一致）→ `artifacts/m17202/repro_before_ci_no_deps.log` |
  | 修复前 + 只补依赖 | 有 | 缺失 | 仍红：4 条 schema 错误（隐藏的第二因）→ `artifacts/m17202/repro_before_ci_deps_source_absent.log` |
  | 修复后 + CI 真实条件 | 有 | 缺失 | `Knowledge asset validation PASSED ... 1 sediment package(s) (0 verified, 1 skipped)`，exit 0 → `artifacts/m17202/repro_after_ci_deps_source_absent.log` |
  | 修复后 + 全量本地复核 | 有 | 本地 TensorLBM 在 | `pass sloshing-impact-lbm rc=0`，verifier 104/104 checks pass，exit 0 → `artifacts/m17202/repro_after_full_local.log` |

## 2. 竞争假设与判定（hypothesis-generation）

| # | 假设 | 机制 | 判别证据 | 判定 |
|---|---|---|---|---|
| H1 | 资产内容坏（数字/引文对不上源 blob） | verifier 真检查失败 | 有源仓时跑 verifier：104/104 PASS，`bench:worst-error` max\|rel\|=1.59e-3 | **否证** |
| H2 | verifier 脚本逻辑坏（独立于环境） | 纯 Python 逻辑缺陷 | 同一脚本在装好依赖的解释器里 rc=0（两种源仓场景一致） | **否证** |
| H3 | CI 解释器缺 `jsonschema`，verifier 在 `SchemaSet()` 处 `ModuleNotFoundError` 崩溃 | 崩溃发生在任何检查行之前 → 无 PASS/FAIL 输出 → 运行器按 "非 0 且无 skip 标记" 判 `fail` | 用无 jsonschema 的 venv 跑：rc=1、stdout 空、stderr 为 `ModuleNotFoundError: No module named 'jsonschema'`（`scripts/verify_sediment_sloshing.py:142`）；workflow 是 5 个 workflow 里唯一没有 `pip install -r requirements-validation.txt` 的 | **确认（主因）** |
| H4 | 只读源仓在 CI 缺失导致 fail | 源仓缺失应判 skip | 缺失源仓时 verifier 打 `source:available FAIL ... NOT run`，运行器判 `skipped-source-unavailable`，validator exit 0 | **否证**（该路径本来就对） |
| H5 | Python 3.12 与 3.11 行为差异 | 版本相关差异 | 失败发生在 `import jsonschema`，与语言版本无关；依赖补上后 3.11 venv 全绿 | **否证** |

隐藏第二因（H1–H5 之外的独立缺陷）：修好依赖后 gate **仍然红** —— 4 条与 sediment 无关的 schema 规则错误：

- `schemas/asset_manifest.v1.schema.json`、`asset_manifest.v1.wp-5949-01.schema.json`、`asset_manifest.wp-9840-01.schema.json` 声明 `draft-07`，违反仓库「`schemas/*.schema.json` 必须 2020-12」规则（文件名被 11-12/11-13 合并的 KF 包带入）；
- `schemas/knowledge-object-v1.schema.json` 的 `version` 是 **整数修订号**（`type=integer, minimum=1`，语义为"对象修订号，从 1 起"），而规则只接受 `^MAJOR.MINOR.PATCH$` 字符串。

两者叠加解释了「main 红 → PR 全 unstable → `merge_master RED⊆main-red` 放行」的失明链：红灯从未被区分成因，于是没有人被迫看它。

## 3. 修复（改动最小、可验证）

1. **主因** `.github/workflows/validate-knowledge-assets.yml`：加 `python -m pip install -r requirements-validation.txt`（其余 4 个 workflow 早已这么做，唯独跑 sediment verifier 的这个没有）。
2. **单一失败即全门失明的诊断盲区** `scripts/validate_sediment_packages.py`：
   - `manifest.entry.requires` 声明 verifier 依赖的 python 模块，运行器**先探测**（`import` 探针），缺依赖 → `blocked-missing-dependency` + 缺哪个模块 + 安装命令，且不再把资产内容判成 fail；
   - 退出码之外的分类：`pass` / `skipped-source-unavailable` / `blocked-missing-dependency` / `error-verifier-crashed`（无任何检查行的崩溃）/ `fail`（真检查失败）；
   - **失败资产索引**：每个资产一行状态，末尾 `FAILED ASSETS (n):` 逐条列 `资产: 状态 rc=原因`；`--json` 输出结构化 `summary.failure_index`。
   - 闸门不放水：`fail` / `error-verifier-crashed` / `blocked-missing-dependency` 仍全部保持红（未验证成功的资产不能让门变绿），改进的是"**哪种红**"，不是"红不红"。
3. **verifier 侧** `scripts/sediment_lib.py` + `scripts/verify_sediment_sloshing.py`：缺依赖时抛 `DependencyError` 并在检查表里记 `FAIL env:dependency`（带安装命令），而不是裸 traceback —— 让运行器能把"环境缺件"与"资产内容错"分开。
4. **dialect 假阳性**：3 个 `asset_manifest*.schema.json` 的 `$schema` 改为 2020-12。**不是**改规则迁就文件：先用 `Draft7Validator` 与 `Draft202012Validator` 对各自真实 manifest 做等价性验证（`docs/wp-448-01`、`docs/kf/wp-5949-01`、`docs/wp-9840-01`，两种方言均 0 错误，逐条错误集相同），确认只是方言声明漂移后修正。
5. **version 规则精确化** `scripts/validate_knowledge_assets.py`：`check_schema_version_rule()` —— 定义 `version` 的 schema 必须钉住可接受形态，接受两种：(a) 字符串 + `^MAJOR.MINOR.PATCH$`；(b) 整数修订号 `type=integer, minimum>=1`。**仍然拒绝**：无 pattern 的字符串、`^v[0-9]+$`、`^[0-9]+\.[0-9]+$` 等松形态（单测参数化钉死）。
6. `scripts/repro_ci_validate_knowledge_assets.sh`：一条命令复现 CI job（`DEPS=install|none`、`SOURCE=absent|present`），离线机器可用（venv `--system-site-packages` + pip 已满足即不下载）。

## 4. 验证

| 检查 | 命令 | 结果 |
|---|---|---|
| sediment verifier（有源仓） | `python3 scripts/verify_sediment_sloshing.py --no-write` | 104/104 checks pass，rc=0 |
| 仓库门（有源仓） | `python3 scripts/validate_knowledge_assets.py` | PASSED（14 nodes / 29 schemas / 1 sediment package verified）rc=0 |
| CI 条件（无源仓、有依赖） | `scripts/repro_ci_validate_knowledge_assets.sh` | PASSED，1 skipped，rc=0 |
| CI 条件 + 缺依赖（诊断回归） | `DEPS=none scripts/repro_ci_validate_knowledge_assets.sh` | 红，但出现 `FAILED ASSETS (1): - sloshing-impact-lbm: blocked-missing-dependency ... missing python module 'jsonschema' ... python -m pip install -r requirements-validation.txt` |
| 新增单测 | `pytest tests/test_validate_knowledge_assets.py -q` | 20 passed |
| 受影响回归子集（sediment + KF asset_manifest 相关 6 个文件） | `pytest tests/test_sediment_sloshing.py tests/test_kf_9840_asset_manifest.py tests/test_kf_wp5949.py tests/test_kf_wp448.py tests/test_kf_wp5776_01.py tests/test_assets.py -q` | 修复前 3 failed/105 passed/14 errors，修复后**同数**（失败为缺外部源仓副本的 FileNotFoundError，与本次改动无关） |
| builder 确定性 | `python3 scripts/sediment_sloshing_extract.py --check` | `package up to date: 27 files`（`requires` 声明同时写进 builder 模板，避免与 `--check` 漂移） |

全量套件（`pytest -q`，1131 tests）：修复前 56 failed/957 passed/93 errors，修复后 57 failed/976 passed/93 errors —— 增量为新增 20 个测试（本次改动相关面全绿），全量红/错集由"缺外部源仓副本"的既有 FileNotFoundError 主导，**非本次引入**（`test_sediment_ke_relay` / `test_sediment_m5054` 等在基线即红）。

## 5. 注意点 / 局限

- 环境内**无外网**，`pip install -r requirements-validation.txt` 只能以「venv `--system-site-packages` 中已满足 4.26.0（满足 pin `>=4.18,<5`）」等价验证；GitHub 侧仍是真 pip 下载。Python 版本用 3.11 模拟（CI 为 3.12），差异不落在 `import jsonschema` 这条路径上。
- **未动资产内容**：`sloshing-impact-lbm` 的 104 项检查全过，按负知识流程下架=错杀，故保留并复绿；判定依据即本文件第 2 节 H1/H2 否证证据，写入本节而非删除资产。
- 运行器仍接受历史 `source:available ... NOT run` 文本作为 skip 依据（向后兼容），新包应改用 `entry.requires` + `env:dependency` 协议。
- 门禁"单资产失败不整门红"**未**采纳字面实现（那会让未验证的资产随门一起变绿），改为"失败资产单独标红 + 清单输出 + 原因分类"，理由见第 3 节第 2 条。
- main 复绿的最终证据需平台推送本分支后的 Actions run conclusion；本单只能提供 CI 条件的本地等价复现（第 4 节第 3 行）。

## 6. 误差判定

本单无物理量算例，基准为"CI 条件下 validator 退出码 / sediment verifier 通过项数"：

- `sloshing-impact-lbm` verifier 通过项 104/104 = 100%（差 0 项，远小于 3% 门槛）；
- benchmark 数字复用性：`bench:worst-error` max|rel| = **1.588e-03**（0.16% < 3%），`bench:exact-reproductions` 12/15 复现源值到 ≤1e-9；
- 门禁行为：修复前后同一 CI 条件退出码 1 → 0（布尔量，无误差概念）。
> 复现日志副本（`artifacts/` 目录被 `.gitignore` 忽略，故同内容入库于 `docs/sediment/evidence/m17202/`）：`repro_before_ci_no_deps.log`（与 CI 日志逐字一致的红）、`repro_before_ci_deps_source_absent.log`（隐藏第二因）、`repro_after_ci_deps_source_absent.log`（CI 条件复绿）、`repro_after_ci_no_deps.log`（缺依赖被正确定性为 blocked-missing-dependency）、`repro_after_full_local.log`（有源仓全量 104/104）。
