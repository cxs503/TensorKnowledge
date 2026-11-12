# KF-RESULT wp-4537-04

**工作包** `wp-4537-04` · task_type `04-independent-review` · lane C · report_id **4537** · mission_id 15829 · 审核对象 `wp-4537-01` · disposition **needs-fix**（verification 由平台门计算，本单不做 verified 标记）

## ① 案例介绍（审核对象与判据）

**案例背景**：源报告 4537 讲的是 TensorFEM PR#128 的 CI 修红——把一个永久红的全仓 lint 门拆成「正确性阻塞门 + 格式棘轮 + 历史债计数」。上游工序 01 为该报告做了资产登记（`wp-4537-01`，27 项资产）。本工序是产线上的**红队审核位**：上下文只有报告原文 + 上游包，生产者对方法的自述不作为证据。

| 参数 | 值 |
|---|---|
| report_id | 4537 |
| source_field / source_uri | `markdown` / `tensor://reports/4537` |
| 契约哈希 | `sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08` |
| 审核方重算哈希 | `sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08` |
| 字符数 | 7931 |
| 审核席位 | `reviewer-m15829-redteam`（red-team-reviewer，agent） |
| 独立性 | ok=True，basis=`distinct-identity` |
| ruff 版本（复现用） | `ruff 0.15.0` |

**判据（先于动手确定）**：

1. `provenance.source_hash` 必须等于平台独立重算的 markdown 字节哈希（不等=门失败）；
2. 审核报告中每条证据引文必须能在其声明的 corpus 字符区间上**逐字复现**（span 漂移即失败）；
3. disposition 必须与 findings 的 blocking 位一致（有阻塞项则不得写 pass）；
4. 独立审阅必须给出可复现的**证伪尝试**：对报告的关键机制论断做同版本复现，而不是只读文本；
5. 上游包的结构性缺陷必须如实留痕（失败的检查不得被改写成通过）。

## ② 怎么做的（方法/流程/工具链）

**只读范围**：`GET /tensor/reports/4537` 取 `markdown`（只此一个 report_id，不读不写其它报告），`docs/kf/wp-4537-01/kf_result.json` 取上游包。工具链=纯标准库 + `jsonschema` + `pytest` + `ruff 0.15.0`（与报告钉的版本一致）+ `matplotlib`。

流程分四段：

**A. 结构 / 保真审计（F 检查，14 条，脚本内一次成文）**：
独立重算源哈希与字符数；把上游包**全部** locator occurrence 按声明 span 从原文重新切一遍并复算 sha256（不复用生产者的中间量）；复算资产计数与分类分布；查「不存在的工件是否被塞了哈希」；查 verified 标记泄漏与跨报告越界；再做一次**完整性对账**——把原文里出现的每个文件路径 token 与「已登记 ∪ 已未决」比对，找静默丢弃。

**B. 复现探针（R 探针，5 条，本机实跑 ruff）**：报告的可判部分不是物理量而是**工具行为**，因此可以原样重跑：E701/E702 是否有 lint autofix、`ruff format` 会不会拆语句、`[tool.ruff.lint] select` 与命令行 `--select` 的作用域差异、未加引号的 `name: ruff: correctness` 是否真的让 workflow 非法、临时目录是否真的丢 ruff 配置。全部在 `mkdtemp` 里做，不碰工作树。

**C. 独立性与台账**：复用引擎自己的状态机（`scripts/ke_state_machine.is_independent`，A2 别名封闭）判定审核方与生产者身份不相交；评审事件按 `ke-review-v0.1` 合法转移写出（`review_events.json`）。

**D. 自检**：`tests/test_kf_wp4537_04.py` 10 条断言，把上面的结论从磁盘字节重新导一遍（schema / 哈希 / 引文 span / disposition 一致性 / 台账合法性 / 独立性 / 无 verified 标记 / 探针可复现）。

## ③ 计算结果（程序化注入，零手抄）

**表 1 — 审计矩阵（14 条检查：11 通过 / 3 失败）**

| 检查 | 判定 | 详情（脚本输出原文） |
|---|---|---|
| `F1` | PASS | reviewer recomputed sha256=de0b4b17cb6e270f… chars=7931 upstream_declared=sha256:de0b4b17c… |
| `F1b` | PASS | chars=7931 contract=7931 |
| `F2` | PASS | 37 occurrences re-sliced from source; mismatches=[] |
| `F3` | PASS | names absent from markdown=[] |
| `F4` | PASS | recomputed total=27 by_status={'resolved': 2, 'declared_metadata_only': 6, 'declared_shorthand': 6, 'declar… |
| `F5` | PASS | n=27 unique=27 |
| `F6` | PASS | absent-but-hashed assets=[] |
| `F7` | PASS | claims=0; 'verified' occurrences=0 |
| `F8` | PASS | foreign report ids referenced=[] |
| `F9` | **FAIL** | 2/15 declared paths in markdown not covered by wp-4537-01: ['tests/test_v1_readiness.py', 'tests/test_valid… |
| `F10` | **FAIL** | \|unresolved\|=25 \|assets with status!=resolved\|=25 sets_equal=True |
| `F11` | PASS | Σrules=4268 (report 合计 4268); 3962/4268=92.83% (report 92.8%); 8/624=1.28% (report 1.28%) |
| `F12` | PASS | honest marker at char 7158; '未直接观测' present=True; 1 'PR #128 CI 变绿' mention(s), all inside the disclaimer=True |
| `F13` | **FAIL** | probe R1b verdict=refuted: codes before=['E701', 'E702'] after `ruff format`=[] (ruff 0.15.0, the version t… |

**表 2 — 复现探针（5 条：4 confirmed / 1 refuted）**

| 探针 | 报告论断 | 实测 | 结论 |
|---|---|---|---|
| `e701-e702-have-no-lint-fix` | E701/E702 这类**不可自动修复**的排版债 | `confirmed` | 论断成立 |
| `ruff-format-splits-e701-e702` | `ruff format` 也不会拆语句；E701/E702 这类债无法通过 `ruff format` 消解 | `refuted` | **论断被证伪** |
| `config-select-vs-cli-select` | `select` 只影响**阻塞**规则集，`ruff check --select E4,E7,E9,F` 在修复后依旧报 4268 条 | `confirmed` | 论断成立 |
| `unquoted-colon-in-step-name` | step `name` 里出现 `ruff: correctness` 会因 "mapping values are not allowed here" 直接让 workfl… | `confirmed` | 论断成立 |
| `temp-dir-loses-ruff-config` | 临时基线文件在系统临时目录，故 `ruff format` 会回落到 ruff 默认配置（line-length 88）；脚本显式传 --line-length 100 --… | `confirmed` | 论断成立 |

**表 3 — 审核结论（findings 3 条，其中阻塞 2 条；disposition=needs-fix）**

| finding | 严重度 | 阻塞 | 对象 | 标题 |
|---|---|---|---|---|
| `FN-4537-04-01` | medium | 是 | `wp-4537-01` | 注册完整性缺口：报告点名的测试文件路径未进 assets[]，也不在 unresolved[] |
| `FN-4537-04-02` | low | 否 | `wp-4537-01` | unresolved[] 与 assets[status!=resolved] 集合完全同构，不是独立未决清单 |
| `FN-4537-04-03` | medium | 是 | `report:4537` | 报告的关键机制论断被同版本复现证伪：`ruff format` 会拆 E701/E702 语句 |

**表 4 — 证伪证据的原始数字（零手抄，取自探针 stdout）**

| 量 | 修复/格式化前 | 后 |
|---|---|---|
| `ruff check --select E701,E702` 命中数（3 语句探针文件） | 2 | 0 |
| 探针文件经 `ruff format` 后是否只剩单语句行 | 否（含 `;` 与单行冒号） | 是 |
| F401 经 `ruff check --fix` 后未使用 import 是否消失（对照） | 存在 | 消失 |

**表 5 — 决定性引文（每条都按 span 从 corpus 重切，durable 定位）**

| finding | corpus | span | 引文 |
|---|---|---|---|
| `FN-4537-04-01` | `source_report_4537.md` | 4999–5065 | pytest -q tests/test_validation_gate.py tests/test_v1_readiness.py |
| `FN-4537-04-01` | `register_4537_assets.py` | 225–268 | and every file/path the report *references* |
| `FN-4537-04-01` | `source_report_4537.md` | 4995–5066 | 抽查 `pytest -q tests/test_validation_gate.py tests/test_v1_readiness… |
| `FN-4537-04-02` | `asset_manifest.json` | 22489–22513 | 仅出现文件名/简化名，完整路径须由上下文唯一确定 |
| `FN-4537-04-03` | `source_report_4537.md` | 1309–1376 | 其中 3962 条（92.8%）是 E701/E702 这类**不可自动修复**的排版债，且 `ruff format` 也不会拆语句 |
| `FN-4537-04-03` | `source_report_4537.md` | 6102–6145 | `E701/E702` 这类不可自动修复的债无法通过 `ruff format` 消解 |

## ④ 结果图

图 1（三联）：左=上游包 14 条审计检查的通过矩阵（红格=可见缺陷，未粉饰）；中=5 条复现探针的判定（绿=论断成立，红=**论断被证伪**）；右=证伪证据的原始计数柱（同一 3 语句探针文件在 `ruff format` 前后的 E701+E702 命中数，以及 F401 lint-autofix 的对照组）。三栏数字全部由 `review_report.json` 渲染，未手抄。

## ⑤ 注意点与局限

- 独立性局限：同一平台、同一模型族内的两个会话；id 不同只能证明会话不同，不能证明利益不同
- 独立性局限：审核上下文仅含报告原文 + 上游包 JSON；生产者对方法的自述未被采信为证据
- 未跑（如实记为 not_run，不算通过）：GitHub check run 结论（报告 §5.1 自述出站被拦；本环境同样无 gh / REST 通路）
- 未跑（如实记为 not_run，不算通过）：TensorFEM 树上 4268 / 616 的原地复算（本工作树无 TensorFEM 检出，且不得跨仓读）
- 未跑（如实记为 not_run，不算通过）：artifacts/lint-gate-m4175/* 逐字节复核（工件不在本仓）
- 未跑（如实记为 not_run，不算通过）：5 个控制实验的原始退出码（evidence.log 不可及）
- 未跑（如实记为 not_run，不算通过）：M5 语义保真的 claim 级全量判定（上游 01 包 claims=[]，无 KO 可审；本单只做资产级保真判定）
- 报告声明复核：8/8 条断言 PASS / lint_gate.py 212 行 → `not_run`：artifacts/lint-gate-m4175/evidence.log 与 scripts/lint_gate.py 的本体不在本工作树，无法逐字节复核；本审核不把未复核的量化声明记为已证
- 报告声明复核：ruff==0.15.0（本地与 CI 一致） → `partially-supported`：本地实测 ruff 0.15.0，与报告钉的版本一致；CI 侧一致性无法在本环境证实
- 报告声明复核：脚本对**所有**检查显式传 --line-length 100 --target-version py311（与 [tool.ruff] 同步） → `partially-supported`：R4 证实临时目录确实丢配置且该两参数可复原；但『与 [tool.ruff] 同步』只覆盖 line-length/target-version 两个旋钮，formatter 的 quote-style / skip-magic-trailing-comma 等未同步
- 上游 01 包 `claims=[]`（登记工序不抽知识），因此本单的『语义保真』判定落在**资产级**（名称逐字、定位可解、计数自洽），而非 claim 级；claim 级保真需等 03 工序产出后再审。
- 证伪只针对**机制论断**（formatter 行为）；报告里 4268/616/92.8% 等**数值**在本环境无法原地复算（无 TensorFEM 检出），只能做内部算术自洽校验（F11 通过）。

## ⑥ 误差判定（逐项、显式回答「是否 <3%」）

本单无物理场量、无解析解基准，故「相对误差 vs 实验/参考值」**N/A**（明确声明，非规避）；可判定量为离散量，全部是精确匹配或**零容差**判定：

| 判据量 | 基准/期望 | 实测 | 相对偏差 | 是否 <3% |
|---|---|---|---|---|
| markdown 字节 sha256 | `sha256:de0b4b17cb6e270f…` | `sha256:de0b4b17cb6e270f…` | 0.0%（精确相等） | **是** |
| 上游 locator 逐字复现 | 37/37 无漂移 | 37 occurrences re-sliced from source | 0.0% | **是** |
| 报告内部算术（规则表求和 / 占比） | 4268 / 92.8% | Σrules=4268 (report 合计 4268); 3962/4268=92.83% (report 92.8%); 8/624=1.28% (report 1.28%) | ≤0.05 个百分点 | **是** |
| 复现探针一致性 | 5 条全部给出确定判定 | confirmed 4 / refuted 1 / 未定 0 | — | **是（无未定项）** |
| 上游注册完整性 | 原文点名的路径 100% 被登记或未决 | 漏 2/15 条（FN-4537-04-01） | 漏登率 13.3% | **否（>3%，故判 needs-fix）** |

结论：源哈希与引文定位为**精确匹配**（0 偏差，优于 3%）；复现探针无未定项；但上游注册完整性存在 >3% 的漏登（2/15=13.3%），加上报告的一处关键机制论断被证伪，因此 disposition = **needs-fix**，并明确：PR#128 的 CI 最终 check run 结论在本环境**未直接观测**，本审核不声称其变绿（honest-FAIL 保持原样，未被升级）。

## 复现入口

```bash
python3 scripts/kf/fetch_4537.py            # 取报告并复核 sha256（需 TENSOR_* 环境变量）
python3 scripts/kf/review_4537_04.py        # 审计 + 复现探针 → review_report.json/review_events.json
python3 scripts/kf/make_figure_4537_04.py   # 图 1
python3 -m pytest tests/test_kf_wp4537_04.py -q
```

## 结果信封（唯一 json 代码块）

```json
{
  "package_id": "wp-4537-04",
  "task_type": "04-independent-review",
  "report_id": "4537",
  "provenance": {
    "source_hash": "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08",
    "source_field": "markdown",
    "source_uri": "tensor://reports/4537",
    "producer": "scripts/kf/review_4537_04.py",
    "emitted_at": "2026-11-12T02:48:32Z",
    "notes": "source_hash 由本脚本对 markdown UTF-8 字节独立重算后写入并复核；审核对象=wp-4537-01；本包不写 epistemic status、不标 verified"
  },
  "outputs": {
    "review_report.json": {
      "review_report_version": 1,
      "package_id": "wp-4537-04",
      "task_type": "04-independent-review",
      "reviewed_package_id": "wp-4537-01",
      "report_id": "4537",
      "reviewed_source": {
        "source_uri": "tensor://reports/4537",
        "source_field": "markdown",
        "source_hash": "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08",
        "reviewer_recomputed_hash": "sha256:de0b4b17cb6e270fc0b3f390715ddb329ab127e826c985388f948b5fac856d08",
        "chars": 7931
      },
      "reviewer": {
        "id": "reviewer-m15829-redteam",
        "reviewer_type": "agent",
        "role": "red-team-reviewer"
      },
      "producer_ids": [
        "scripts/kf/register_4537_assets.py",
        "1"
      ],
      "independence": {
        "ok": true,
        "basis": "distinct-identity",
        "rule": "scripts/ke_state_machine.is_independent (A2, alias-closed)",
        "limitations": [
          "同一平台、同一模型族内的两个会话；id 不同只能证明会话不同，不能证明利益不同",
          "审核上下文仅含报告原文 + 上游包 JSON；生产者对方法的自述未被采信为证据"
        ]
      },
      "disposition": "needs-fix",
      "disposition_reason": "无 blocker；1 条 medium 阻塞项（FN-4537-04-01，注册完整性缺口）需上游补登记；报告本体（原文）对不可观测量的诚实标注通过复核，不被本单升级",
      "checks": [
        {
          "id": "F1",
          "rule": "source_hash_recomputed",
          "pass": true,
          "detail": "reviewer recomputed sha256=de0b4b17cb6e270f… chars=7931 upstream_declared=sha256:de0b4b17c…"
        },
        {
          "id": "F1b",
          "rule": "chars_match_contract",
          "pass": true,
          "detail": "chars=7931 contract=7931"
        },
        {
          "id": "F2",
          "rule": "upstream_locators_resolve",
          "pass": true,
          "detail": "37 occurrences re-sliced from source; mismatches=[]"
        },
        {
          "id": "F3",
          "rule": "asset_names_verbatim_in_source",
          "pass": true,
          "detail": "names absent from markdown=[]"
        },
        {
          "id": "F4",
          "rule": "asset_counts_recomputed",
          "pass": true,
          "detail": "recomputed total=27 by_status={'resolved': 2, 'declared_metadata_only': 6, 'declared_shorthand': 6, 'declared_only': 13} by_kind={'report_markdown': 1, 'report_record_metadata': 1, 'report_figure': 1, 'path_basename_shorthand': 6, 'path_directory': 3, 'path_file': 10, 'vcs_branch': 1, 'vcs_commit': 4}"
        },
        {
          "id": "F5",
          "rule": "asset_ids_unique",
          "pass": true,
          "detail": "n=27 unique=27"
        },
        {
          "id": "F6",
          "rule": "absent_artifact_has_no_hash",
          "pass": true,
          "detail": "absent-but-hashed assets=[]"
        },
        {
          "id": "F7",
          "rule": "no_verification_marked",
          "pass": true,
          "detail": "claims=0; 'verified' occurrences=0"
        },
        {
          "id": "F8",
          "rule": "single_report_scope",
          "pass": true,
          "detail": "foreign report ids referenced=[]"
        },
        {
          "id": "F9",
          "rule": "every_declared_path_registered_or_unresolved",
          "pass": false,
          "detail": "2/15 declared paths in markdown not covered by wp-4537-01: ['tests/test_v1_readiness.py', 'tests/test_validation_gate.py']"
        },
        {
          "id": "F10",
          "rule": "unresolved_inventory_distinct_from_status_mirror",
          "pass": false,
          "detail": "|unresolved|=25 |assets with status!=resolved|=25 sets_equal=True"
        },
        {
          "id": "F11",
          "rule": "report_internal_arithmetic_consistent",
          "pass": true,
          "detail": "Σrules=4268 (report 合计 4268); 3962/4268=92.83% (report 92.8%); 8/624=1.28% (report 1.28%)"
        },
        {
          "id": "F12",
          "rule": "unobserved_outcome_not_claimed",
          "pass": true,
          "detail": "honest marker at char 7158; '未直接观测' present=True; 1 'PR #128 CI 变绿' mention(s), all inside the disclaimer=True"
        },
        {
          "id": "F13",
          "rule": "e701_e702_not_cleared_by_ruff_format",
          "pass": false,
          "detail": "probe R1b verdict=refuted: codes before=['E701', 'E702'] after `ruff format`=[] (ruff 0.15.0, the version the report pins)"
        }
      ],
      "findings": [
        {
          "finding_id": "FN-4537-04-01",
          "severity": "medium",
          "blocking": true,
          "scope": "wp-4537-01",
          "title": "注册完整性缺口：报告点名的测试文件路径未进 assets[]，也不在 unresolved[]",
          "claim_under_review": "wp-4537-01 自述登记「报告引用的每一个文件/路径」，且 unresolved[] 覆盖未决项",
          "evidence": [
            {
              "source_field": "markdown",
              "corpus": "runs/m15829_wp4537_04/source_report_4537.md",
              "quote": "pytest -q tests/test_validation_gate.py tests/test_v1_readiness.py",
              "span": [
                4999,
                5065
              ],
              "content_hash": "sha256:793fdbf5da500e410acacd4841d822276fff6b45e7fdadf5e3eb89935feadf74"
            },
            {
              "source_field": "record",
              "corpus": "scripts/kf/register_4537_assets.py",
              "quote": "and every file/path the report *references*",
              "span": [
                225,
                268
              ],
              "content_hash": "sha256:1cb34c6b0c86719bf74e6ab19c3af8518af6e06f1cc46561f601eabe5d48242d"
            },
            {
              "source_field": "markdown",
              "corpus": "runs/m15829_wp4537_04/source_report_4537.md",
              "quote": "抽查 `pytest -q tests/test_validation_gate.py tests/test_v1_readiness.py`",
              "span": [
                4995,
                5066
              ],
              "content_hash": "sha256:d065fbf6c6a20463956165ec4444e035c1d9f977388b199e5344db4d74d53983"
            }
          ],
          "observed": {
            "declared_paths_missing": [
              "tests/test_v1_readiness.py",
              "tests/test_validation_gate.py"
            ],
            "n_declared_paths": 15,
            "n_missing": 2,
            "registered": false,
            "in_unresolved": false
          },
          "reproduction": "python3 -c \"import json,re;md=open('runs/m15829_wp4537_04/source_report_4537.md',encoding='utf-8').read();m=json.load(open('docs/kf/wp-4537-01/kf_result.json'))['outputs']['asset_manifest.json'];n={a['name'] for a in m['assets']};print([t for t in ['tests/test_validation_gate.py','tests/test_v1_readiness.py'] if t in md and t not in n])\"",
          "root_cause": "两条路径整体落在一个 inline code span 里（命令 `pytest -q …`），01 的 tokenizer 把含空白的 span 判为 command_line 后整段跳过，span 内的路径不再进入资产分类器",
          "impact": "下游 03/04 的抽取面缺两个被报告明确点名的验证入口文件；报告 §3 的回归面证据不可被下游重建",
          "remediation": "在 scripts/kf/register_4537_assets.py 的 command span 上再做一次路径切分，或在 unresolved[] 显式登记这两条路径；加一条回归断言（tests/test_kf_wp4537_01.py）"
        },
        {
          "finding_id": "FN-4537-04-02",
          "severity": "low",
          "blocking": false,
          "scope": "wp-4537-01",
          "title": "unresolved[] 与 assets[status!=resolved] 集合完全同构，不是独立未决清单",
          "claim_under_review": "unresolved[] 语义 = 需下游/人工补齐的不确定项",
          "evidence": [
            {
              "source_field": "record",
              "corpus": "docs/kf/wp-4537-01/asset_manifest.json",
              "quote": "仅出现文件名/简化名，完整路径须由上下文唯一确定",
              "span": [
                22489,
                22513
              ],
              "content_hash": "sha256:04027e230e3130fa05cc8eea141b1aefc0d90954fa9bd78b859a61de306d2627"
            }
          ],
          "observed": {
            "n_unresolved": 25,
            "n_mirror": 25
          },
          "reproduction": "python3 scripts/kf/review_4537_04.py  # F10",
          "impact": "下游按 unresolved 计欠账时会把已声明资产重复计为未决（同一批 25 条）",
          "remediation": "unresolved[] 只放真正未决项，或改名 status_mirror 并在 manifest 说明"
        },
        {
          "finding_id": "FN-4537-04-03",
          "severity": "medium",
          "blocking": true,
          "scope": "report:4537",
          "title": "报告的关键机制论断被同版本复现证伪：`ruff format` 会拆 E701/E702 语句",
          "claim_under_review": "（a）「其中 3962 条（92.8%）是 E701/E702 这类**不可自动修复**的排版债，且 `ruff format` 也不会拆语句」；（b）「E701/E702 这类不可自动修复的债无法通过 `ruff format` 消解」",
          "evidence": [
            {
              "source_field": "markdown",
              "corpus": "runs/m15829_wp4537_04/source_report_4537.md",
              "quote": "其中 3962 条（92.8%）是 E701/E702 这类**不可自动修复**的排版债，且 `ruff format` 也不会拆语句",
              "span": [
                1309,
                1376
              ],
              "content_hash": "sha256:6b6f4eadb8dba1a55e7328b3e9e5d55d28899fb4b17385d948af874237b7c889"
            },
            {
              "source_field": "markdown",
              "corpus": "runs/m15829_wp4537_04/source_report_4537.md",
              "quote": "`E701/E702` 这类不可自动修复的债无法通过 `ruff format` 消解",
              "span": [
                6102,
                6145
              ],
              "content_hash": "sha256:540f47df956b9388d3151cb5f95c03e94788abdd47e901eb5d13d28ac3422e99"
            }
          ],
          "counter_evidence": {
            "probe": "R1b（ruff 0.15.0，与报告钉版本一致）",
            "input": "import os\n\nx = 1; y = 2\nif True: pass\nprint(1)\n",
            "ruff_check_before": [
              "E701",
              "E702"
            ],
            "after_ruff_format_file": "import os\n\nx = 1\ny = 2\nif True:\n    pass\nprint(1)\n",
            "ruff_check_after": [],
            "after_rc": 0
          },
          "reproduction": "python3 scripts/kf/review_4537_04.py  # probe R1b（临时目录内 ruff format + ruff check --select E701,E702）",
          "root_cause": "把『lint 规则无 autofix』外推成『formatter 也不会动它』；formatter 对复合语句会展开成多行（与 Black 同源行为）",
          "impact": "(1) 3962/4268=92.8% 的债并非只能手改：一次 `ruff format` 批量即可消解 E701/E702，burn-down 的『E7xx 只能手改』成本被高估；(2) 『ruff format --check』的 616 文件待重排本身就说明 formatter 会动这些文件，两处论断互相矛盾；(3) 数值部分（4268/616/92.8%）不受影响，已由 F11 复算通过",
          "non_blocking_for_ship": false,
          "remediation": "改写 §1 与 §5.5 的措辞为『E701/E702 无 lint autofix，只能由 ruff format 批量展开（代价=616 文件 churn）』；docs/ci-lint-gate.md 的 burn-down 把 E7xx 阶段改为一次 formatter 批处理，保留『不在本 PR 内重排全仓』的决策不变"
        }
      ],
      "reproduction_probes": [
        {
          "probe": "R1a-e701-e702-have-no-lint-fix",
          "report_claim": "E701/E702 这类**不可自动修复**的排版债",
          "fix_diff_empty": true,
          "still_reported_after_fix": [
            "E701",
            "E702"
          ],
          "control_f401_autofix_removed_import": true,
          "verdict": "confirmed"
        },
        {
          "probe": "R1b-ruff-format-splits-e701-e702",
          "report_claim": "`ruff format` 也不会拆语句；E701/E702 这类债无法通过 `ruff format` 消解",
          "ruff_version": "ruff format m.py",
          "codes_before": [
            "E701",
            "E702"
          ],
          "format_rc": 0,
          "file_after_format": "import os\n\nx = 1\ny = 2\nif True:\n    pass\nprint(1)\n",
          "semicolon_statement_split": true,
          "inline_colon_split": true,
          "codes_after": [],
          "after_rc": 0,
          "verdict": "refuted"
        },
        {
          "probe": "R2-config-select-vs-cli-select",
          "report_claim": "`select` 只影响**阻塞**规则集，`ruff check --select E4,E7,E9,F` 在修复后依旧报 4268 条",
          "blocking_step_codes": [
            "F821"
          ],
          "blocking_step_rc": 1,
          "backlog_counter_codes": [
            "E701",
            "E702",
            "F401",
            "F821"
          ],
          "backlog_counter_rc": 1,
          "blocking_set_only_f821": true,
          "backlog_still_reports_style_debt": true,
          "verdict": "confirmed"
        },
        {
          "probe": "R3-unquoted-colon-in-step-name",
          "report_claim": "step `name` 里出现 `ruff: correctness` 会因 \"mapping values are not allowed here\" 直接让 workflow 非法",
          "unquoted_raises": true,
          "unquoted_error": "mapping values are not allowed here   in \"<unicode string>\", line 4, column 19:           - name: ruff: correctness                       ^",
          "error_is_mapping_values": true,
          "quoted_parses": true,
          "verdict": "confirmed"
        },
        {
          "probe": "R4-temp-dir-loses-ruff-config",
          "report_claim": "临时基线文件在系统临时目录，故 `ruff format` 会回落到 ruff 默认配置（line-length 88）；脚本显式传 --line-length 100 --target-version py311",
          "synthetic_line_chars": 93,
          "project_dir_check_rc": 0,
          "temp_dir_check_rc": 1,
          "temp_dir_explicit_args_rc": 0,
          "temp_dir_ancestors_with_ruff_config": [],
          "verdict": "confirmed"
        }
      ],
      "ruff_version_used": "ruff 0.15.0",
      "overstated_claims": [
        {
          "claim": "8/8 条断言 PASS / lint_gate.py 212 行",
          "status": "not_run",
          "why": "artifacts/lint-gate-m4175/evidence.log 与 scripts/lint_gate.py 的本体不在本工作树，无法逐字节复核；本审核不把未复核的量化声明记为已证"
        },
        {
          "claim": "ruff==0.15.0（本地与 CI 一致）",
          "status": "partially-supported",
          "why": "本地实测 ruff 0.15.0，与报告钉的版本一致；CI 侧一致性无法在本环境证实"
        },
        {
          "claim": "脚本对**所有**检查显式传 --line-length 100 --target-version py311（与 [tool.ruff] 同步）",
          "status": "partially-supported",
          "why": "R4 证实临时目录确实丢配置且该两参数可复原；但『与 [tool.ruff] 同步』只覆盖 line-length/target-version 两个旋钮，formatter 的 quote-style / skip-magic-trailing-comma 等未同步"
        }
      ],
      "checks_not_run": [
        "GitHub check run 结论（报告 §5.1 自述出站被拦；本环境同样无 gh / REST 通路）",
        "TensorFEM 树上 4268 / 616 的原地复算（本工作树无 TensorFEM 检出，且不得跨仓读）",
        "artifacts/lint-gate-m4175/* 逐字节复核（工件不在本仓）",
        "5 个控制实验的原始退出码（evidence.log 不可及）",
        "M5 语义保真的 claim 级全量判定（上游 01 包 claims=[]，无 KO 可审；本单只做资产级保真判定）"
      ],
      "checks_failed": [
        "F9",
        "F10",
        "F13"
      ],
      "summary": {
        "n_checks": 14,
        "n_checks_passed": 11,
        "n_findings": 3,
        "n_blocking": 2,
        "n_probes_confirmed": 4,
        "n_probes_refuted": 1,
        "n_probes": 5
      }
    },
    "review_events.json": [
      {
        "id": "tkr:wp-4537-04:needs-fix",
        "decision": "request-changes",
        "policy_version": "ke-review-v0.1",
        "reviewer": {
          "id": "reviewer-m15829-redteam",
          "reviewer_type": "agent"
        },
        "reviewed_at": "2026-11-12T02:48:32Z",
        "subject_package_id": "wp-4537-01",
        "independence_basis": "distinct-identity",
        "findings": [
          {
            "finding_id": "FN-4537-04-01",
            "severity": "medium",
            "title": "注册完整性缺口：报告点名的测试文件路径未进 assets[]，也不在 unresolved[]"
          },
          {
            "finding_id": "FN-4537-04-02",
            "severity": "low",
            "title": "unresolved[] 与 assets[status!=resolved] 集合完全同构，不是独立未决清单"
          },
          {
            "finding_id": "FN-4537-04-03",
            "severity": "medium",
            "title": "报告的关键机制论断被同版本复现证伪：`ruff format` 会拆 E701/E702 语句"
          }
        ],
        "review_report": "review_report.json",
        "touches_epistemic_status": false
      }
    ]
  },
  "claims": []
}
```
