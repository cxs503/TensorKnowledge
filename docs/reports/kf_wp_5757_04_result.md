# KF-RESULT wp-5757-04

tags: kf-wp:wp-5757-04, 04-independent-review, gate-auto-release, report-5757, red-team-reviewer

## ① 本工序做了什么

对 `report_id=5757`（《放门自动化成熟化：gate_auto_release daemon（IN20-R2，G13–G20 六门演练）》，mission 5046）执行**独立审核（红队）**，审核对象是上游工作包 `wp-5757-01`（资产登记）的产物 `docs/kf/wp-5757-01/asset_manifest.json`，判据面为「语义保真」：出处在原文是否逐字可定位、哈希是否可独立重算、分类与 resolution 状态是否与原文相符、资产召回有无遗漏，并把报告 ③ 的数字算术自洽性作为保真的必要条件一并复算。

**版本说明（v2）**：v1 发于 report id=14961；发布后为复核 F5，用同一 GET 回读自证：任何报告（含本单内嵌 png_base64 发布的那份）回读后 `figures` 都只剩 `name`+`caption` → 图件载荷缺失是**平台读侧行为**，不是报告 5757 或 wp-5757-01 的遗漏，F5 的归属据此更正（`probe_figure_payload.py` 可复现）。平台无 `PUT /tensor/reports/<built-in function id>`（实测 405），故以本 v2 为准，v1 作废。

不做的三件事（边界）：不改写上游产物、不标任何结论为 verified（本单只给 pass/fail/needs-fix 与分级发现）、不读写其它 report_id 的 markdown/产物。

结论：**verdict = pass**（无 blocking 缺陷）。15/15 资产 locator 的 char_span 与行号在原文逐字命中；provenance 哈希独立重算与合同一致；未发现凭空捏造的资产。查出 10/15 项机检通过；共 6 条非阻断发现（3 minor + 3 note），其中 5 条由机检复现（C6/C8/C13/C14/C15）、1 条靠跨仓旁证（F6）；归属上 2 条可在 wp-01 侧小改（F1/F2），4 条归报告侧或版本同步（F3–F6）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`POST /api/v1/auth/login` 取 Bearer token → `GET /api/v1/tensor/reports/5757` 取 `markdown`，落 `/tmp/report_5757.json`。独立重算 `sha256` = `d85b5a16…bd915`、chars = 5061，与合同 `source_hash` 一致（不采信上游自述，重算后比对）。
2. **读上游 KO**：只读 `docs/kf/wp-5757-01/asset_manifest.json` 与 `kf_result.wp-5757-01.json`；不读生产者对它的解释（约束 `reviewer_context_excludes_producer_explanation`）。审核清单由本单自拟（约束 `review_prompt_not_copied_from_producer`）。
3. **locator 复核（C5/C6）**：对 15 个资产逐个断言 `md[start_char:end_char] == quote`、行号 `md[:start].count('\n')+1 == start_line`、`md.count(quote)`、`md.find(quote) == start_char`。
4. **召回复核（C7/C8）**：用正则独立抽取原文所有 `*.py|*.sh|*.yaml|*.yml|*.json|*.md|*.png` 形态的路径与反引号标识符，与 manifest 的 quote 集合求差；并单点检查报告以「10 条 pytest 覆盖」作证据的测试套件是否登记。
5. **算术复算（C9–C12）**：从原文表格行解析生产矩阵与沙箱矩阵的行动作序列，与自述「动作计数」「审计动作计数」逐键比对；派生「6 门动作 + plan 21 G21 一行 = 7 行」并核账；核 release↔rollback 配对（4 放 4 回滚）。
6. **隐蔽缺陷探测（C13–C15）**：判据表是否声明 C3 先于 C2 的优先级（G20 判 hold 而非 wait 依赖此优先级）；生产快照哈希是否给全（`…` 截断 → 外部不可复算）；图件是否带 png 载荷（下游能否验图）。
7. **旁证（非权威）**：在主机上一个 TensorPlatform 检出（commit 3d6ff8aba，只读）核对 6 个 code/config 资产路径是否存在、`test_gate_auto_release.py` 的 `def test_` 计数是否等于报告自述的 10 条。
8. **产物**：`checks.json`（15 项机检结果 + 15×(span,行号,出现次数,首个命中)矩阵）→ `review_report.json`（含 6 条 findings、5 条 claim 级判定、not_run 清单、overstated 清单）→ `kf_result.json`（信封，schema 校验）→ 审核矩阵图。

关键设置：所有断言可复跑（`verify_wp_5757_04.py` 退出码=是否存在 blocking 失败）；引文零手抄——本报告 ④ 的每条引文在生成期被断言为原文子串，否则构建失败。

## ③ 产出物清单

| 输出文件 | 路径 | 要点 |
|---|---|---|
| review_report.json | docs/kf/wp-5757-04/review_report.json | 审核正文：15 项 checks、6 条 findings（0 blocking / 3 minor / 3 note）、5 条 claim 判定（supported 3 / partially-supported 1 / refuted 1）、3 条 checks_not_run、3 条 overstated_claims、verdict=pass |
| kf_result.json | docs/kf/wp-5757-04/kf_result.json | 结果信封（本报告唯一 json 块的来源），`schemas/kf_result.v1.schema.json` 校验通过 |
| checks.json | docs/kf/wp-5757-04/checks.json | 机检原始结果：10/15 pass，blocking=[]，含 15 个 locator 的 span/行号/出现次数/首个命中四元组 |
| verify_wp_5757_04.py | docs/kf/wp-5757-04/verify_wp_5757_04.py | 一键复跑：取原文→重算哈希→15 项检查→写 checks.json（退出码=是否有 blocking 失败） |
| build_review_report.py | docs/kf/wp-5757-04/build_review_report.py | 由 checks.json 生成 review_report.json / kf_result.json / 审核矩阵图 |
| probe_figure_payload.py | docs/kf/wp-5757-04/probe_figure_payload.py | 图件载荷探针：`python3 … 5757 14961` → 两份报告都是 `keys=[caption,name] png_payload=False`，证 F5 归平台读侧 |
| review_matrix.png | docs/kf/wp-5757-04/review_matrix.png | 图 1：A 面板=locator 出现次数（橙=unique=true 不成立但首个命中仍对位）；B 面板=15 项检查 pass/fail 与影响分级 |

## ④ 证据定位表

| claim / 字段 | 原文引文片段（逐字，脚本断言） | 复核方式与结论 |
|---|---|---|
| A01 主脚本 locator（span 1301–1335） | `ops/taskplane/gate_auto_release.py` | `md[1301:1335]==quote` ✅ 且 `md.find(quote)==1301` |
| A14 库表 locator（span 339–368） | `tensorplatform.campaign_nodes` | `md[339:368]==quote` ✅（原文即写作 `tensorplatform.campaign_nodes`） |
| A12 图件 locator（span 3721–3758） | `artifacts/gate_auto_release_drill.png` | span 命中 ✅；但 report 记录 `figures[0]` 只有 name+caption、**无 png_base64** → 图内容不可验（F5） |
| manifest `provenance.hash/chars` | （非引文，独立重算） | 重算 `sha256:d85b5a16b5062cdf…`、chars=5061，与 manifest 及合同三方一致 ✅ |
| A13/A15 `locator.unique=true` | `gate_release_audit` / `gate_drill` | `md.count(quote)` = 2 / 2 → unique 为假（F1）；但 `md.find()` 仍等于记录 span，first-occurrence 解析不受影响 |
| 六门判据工件 declared_absent | `证据在临时根按 `<repo>/artifacts/…` 同形造出 （显式 `synthetic: true`）` | 生产侧 not_found 与矩阵 5 行一致 ✅，但沙箱内同形存在 → `declared_absent` 只对生产侧成立（claim C-04 = partially-supported） |
| G20 治理门判 hold | `governance_marker=SPEC军` | 185 行动作 `hold_owner_only` 与理由一致 ✅；但判据表只有 ``metadata.owner_only` 非真 + 门名/goal 无治理标记` + `永不自动放`，未写 C3>C2 优先级（F3） |
| 生产动作计数 | `- 动作计数：release=0 / wait=5 /` + 续行 `hold_owner_only=1` | 与 6 行矩阵解析值 `{'wait': 5, 'hold_owner_only': 1}` 逐键相等 ✅（C9） |
| 首轮审计 7 行 | `六门 `wait` ×6` | 算术 5(wait)+1(hold)+1(G21)=7 ✅ 自洽；但措辞把第 6 个 wait 归给「六门」不实（六门中 wait=5、hold=1）→ overstated_claims 第 3 条 |
| 生产快照未变 | `56e8ab792ceeeb40db68538a…` | 哈希被 `…` 截断 → `production_untouched=True` 外部不可复算（F4） |
| 报告局限「不判内容」 | 只判「工件在不在、json 是否合法」，不判内容对错（内容由验收链负责） | 与仓内 `ops/taskplane/gate_content_criteria.py` + `evaluate_gate()` 的 `# C2b 判据内容` 分支可能版本失同步（F6，note 级） |
| 测试证据 | 10 条 pytest 覆盖 | 旁证：TensorPlatform 检出 `tests/test_gate_auto_release.py` 的 `def test_` = 10 ✅；但该套件未登记为资产（F2） |

## ⑤ 注意点与局限

1. **无权复核的部分如实标 not_run**：`psql -d tensorplatform -c "select … from campaign_nodes"` 返回 `permission denied for table campaign_nodes`，因此报告里的上游依赖数（8/11/8/11/4/9）、六门 `status`、`metadata.owner_only` 实测值**未独立复核**；本单只核了它们在正文表格里的自洽性。
2. **旁证≠生产版本**：仓内实现判断（C3 短路、C2b 内容层）基于主机上一个 TensorPlatform 检出（commit 3d6ff8aba），与产线提交可能不同 → 相关结论一律降级为 note，不据此判 fail。
3. **未做沙箱写路径复现**：真 UPDATE + rollback 需隔离 schema 写权限，且本单边界禁止改上游状态，故 C10/C11 只做「表 vs 自述」的算术核账，未复现数据库动作。
4. **审核偏保守**：把「机器可读字段为假」（F1 的 unique）判 minor 而非 note，理由是字段一旦被下游当不变量使用会错位；但它不改写原文、不影响哈希与 span。
5. **两处判定口径**：①「declared_absent」按生产侧解释；②「六门 wait ×6」按其后续派生总数 7 正确而不判 blocking。
6. **图件载荷缺失已改判为平台侧**：实测 `GET /tensor/reports/5757` 与 `GET /tensor/reports/14961`（本单自己内嵌 png 发布的报告）回读 `figures[0].keys()` 均为 `[caption, name]`，`png_payload=False` → 下游无法验任何图；这既解释了报告 5757 的 ④ 图为何无法核对，也说明 wp-5757-01 把 A12 记为 `referenced_unresolved` 是正确分类。
7. **本单不产出知识对象**：`claims=[]`（审核结论留在 review_report.json 的 claims_assessed / findings 里，不与 03 的知识对象混用）。

## ⑥ 误差判定：关键量 vs 基准，逐项回答是否 <3%

无物理场量（治理/后端机制的审核单），故以「独立重算值 / 合同声明值 / 上游自述值」为基准做逐项对表。

| 关键量 | 机制结果 | 基准 | 偏差 | <3% ? |
|---|---|---|---|---|
| markdown sha256 | `d85b5a16…bd915`（重算） | 合同 `source_hash` | 0（逐字节相同） | **是** |
| markdown 字符数 | 5061 | 合同 `chars` / manifest `chars` | 0% | **是** |
| 资产数 | 15 | manifest `summary.total_assets`=15、`len(assets)`=15 | 0% | **是** |
| locator 逐字命中 | 15/15 | 全命中 | 0/15 | **是** |
| locator 行号命中 | 15/15 | 全命中 | 0/15 | **是** |
| 首个命中==记录 span | 15/15 | 全一致 | 0/15 | **是** |
| `unique=true` 为真 | 13/15 | 15/15 | 2/15 = 13.3% | **否（F1，minor）** |
| 路径型资产召回 | 11/11 覆盖 | manifest 15 项 | 0 漏（文件型） | **是** |
| 报告内证据类资产召回 | 测试套件 0/1 | 应登记 1 | 1/1 = 100% | **否（F2，minor）** |
| 生产矩阵行动作计数 | wait=5, hold=1, release=0 | 自述动作计数 | 0% | **是** |
| 沙箱行动作计数 | release=4, wait=1, hold=1, rollback=4 | 自述审计动作计数 | 0% | **是** |
| release↔rollback 配对 | 4/4 | 4 放 4 回滚 | 0% | **是** |
| 首轮审计行数 | 7 | 5+1+1=7 派生 | 0% | **是** |
| 机检通过率 | 10/15 = 66.7% | 全 pass | 5 项 | **否**（其中 blocking=0） |

**逐项结论**：凡「可与原文/合同逐字比对」的量，偏差一律 0%，<3% 成立；两处 <3% 不成立的量（`unique` 真实性 13.3% 错、测试套件召回 100% 缺）**如实列出且判为 minor、非阻断**——它们不改变 locator 解析结果与 provenance，故 verdict 仍为 pass，但已写进 review_report.json 的 `remediation_required` 建议。`campaign_nodes` 实测类指标因权限缺失**未测**，按纪律记 not_run，不折算成 0% 偏差。

```json
{
  "package_id": "wp-5757-04",
  "task_type": "04-independent-review",
  "report_id": "5757",
  "provenance": {
    "source_hash": "sha256:d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915",
    "source_field": "markdown",
    "producer": "red-team-reviewer (m15840)",
    "emitted_at": "2026-11-07T03:36:09.837420+00:00",
    "notes": "独立审核 wp-5757-01；上下文=报告原文+上游 KO，未读生产者解释；未将任何结论标为 verified"
  },
  "outputs": {
    "review_report.json": {
      "schema": "kf-independent-review.v1",
      "package_id": "wp-5757-04",
      "task_type": "04-independent-review",
      "reviewed_package": "wp-5757-01",
      "report_id": "5757",
      "reviewer_role": "red-team-reviewer",
      "reviewed_artifact": {
        "path": "docs/kf/wp-5757-01/asset_manifest.json",
        "sha256": "sha256:b862588da2bd3a23dba41589def84ee756653f89eb8246fd4a760b9eeabbc256",
        "upstream_result": "docs/kf/wp-5757-01/kf_result.wp-5757-01.json"
      },
      "independence": {
        "context_used": [
          "report 5757 markdown（平台 API，独立重算哈希）",
          "上游 wp-5757-01 产物（asset_manifest.json / kf_result）",
          "仓内代码与 schema（worktree，只读）",
          "主机上 TensorPlatform 检出（只读 grep，仅作旁证）"
        ],
        "context_excluded": [
          "生产者对 wp-5757-01 的口头/文字解释（未读）",
          "其它 report_id 的 markdown/产物（未读）"
        ],
        "review_prompt_not_copied_from_producer": true,
        "limitations": [
          "生产库 tensorplatform.campaign_nodes 无读权限 → 报告里的 8/11/8/11/4/9 依赖数、门状态、owner_only 值无法独立复核，记 not_run。",
          "旁证只读自主机上一个 TensorPlatform 检出（commit 3d6ff8aba），不保证等于生产侧产线提交 → 关于实现的判断降级为 note。",
          "报告快照哈希被截断，production_untouched=True 无法独立复算。"
        ]
      },
      "scope": {
        "in_scope": [
          "wp-5757-01 出处可定位性（hash/chars/char_span/行号/唯一性）",
          "wp-5757-01 资产分类与 resolution 状态的可辩护性",
          "wp-5757-01 资产召回（是否有报告内资产漏登记）",
          "报告 ③ 数字的内部算术一致性（作为上游 fidelity 的必要条件）"
        ],
        "out_of_scope": [
          "report 5757 的作者结论正确性（release 逻辑是否安全）——由平台门/后续 wp 判",
          "生产库真实状态（无权限）"
        ]
      },
      "checks": [
        {
          "check_id": "C1",
          "name": "provenance 哈希与被审 markdown 一致",
          "result": "pass",
          "severity_if_fail": "blocking",
          "detail": {
            "recomputed": "sha256:d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915",
            "expected": "sha256:d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915",
            "chars": 5061,
            "bytes_utf8": 8027
          }
        },
        {
          "check_id": "C2",
          "name": "上游 manifest 的 provenance 哈希/字符数与本报告一致",
          "result": "pass",
          "severity_if_fail": "blocking",
          "detail": {
            "manifest_hash": "d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915",
            "recomputed": "d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915",
            "manifest_chars": 5061,
            "actual_chars": 5061
          }
        },
        {
          "check_id": "C3",
          "name": "上游 manifest 声明的 asset_count 与 assets 数组一致",
          "result": "pass",
          "severity_if_fail": "blocking",
          "detail": {
            "total_assets": 15,
            "len": 15
          }
        },
        {
          "check_id": "C4",
          "name": "asset 编号唯一且无空 locator",
          "result": "pass",
          "severity_if_fail": "blocking",
          "detail": {
            "ids": [
              "A01",
              "A02",
              "A03",
              "A04",
              "A05",
              "A06",
              "A07",
              "A08",
              "A09",
              "A10",
              "A11",
              "A12",
              "A13",
              "A14",
              "A15"
            ]
          }
        },
        {
          "check_id": "C5",
          "name": "15 个 locator 的 char_span 与行号逐字命中原文",
          "result": "pass",
          "severity_if_fail": "blocking",
          "detail": {
            "checked": 15,
            "failed": []
          }
        },
        {
          "check_id": "C6",
          "name": "locator.unique=true 与实际出现次数相符（机器可读字段须为真）",
          "result": "fail",
          "severity_if_fail": "minor",
          "detail": {
            "non_unique_quotes": [
              "A13",
              "A15"
            ],
            "mitigation": "md.find(quote) 与记录 start_char 全部一致，first-occurrence 解析不受影响",
            "reproducible_by_index": true
          }
        },
        {
          "check_id": "C7",
          "name": "file/path 型资产召回无遗漏",
          "result": "pass",
          "severity_if_fail": "minor",
          "detail": {
            "candidate_paths": [
              "artifacts/autoregression_acceptance.md",
              "artifacts/chronicler_acceptance.json",
              "artifacts/deepwater_gap_ledger_update.json",
              "artifacts/gate_auto_release_drill.png",
              "artifacts/spec_impl_acceptance.json",
              "artifacts/system_pierce_acceptance.json",
              "gate_auto_release_loop.sh",
              "ops/taskplane/gate_auto_release.py",
              "supervise.py",
              "taskplane.manifest.yaml",
              "tools/gate_drill.py"
            ],
            "registered": [
              "artifacts/autoregression_acceptance.md",
              "artifacts/chronicler_acceptance.json",
              "artifacts/deepwater_gap_ledger_update.json",
              "artifacts/gate_auto_release_drill.png",
              "artifacts/spec_impl_acceptance.json",
              "artifacts/system_pierce_acceptance.json",
              "deploy/taskplane/gate-auto-release.service",
              "gate_auto_release_loop.sh",
              "gate_drill",
              "gate_release_audit",
              "ops/taskplane/gate_auto_release.py",
              "supervise.py",
              "taskplane.manifest.yaml",
              "tensorplatform.campaign_nodes",
              "tools/gate_drill.py"
            ],
            "uncovered": []
          }
        },
        {
          "check_id": "C8",
          "name": "报告引用的 pytest 覆盖套件是否登记为资产",
          "result": "fail",
          "severity_if_fail": "minor",
          "detail": {
            "report_says": [
              "10 条 pytest 覆盖，**尚无生产 release 审计行**——如实披露，不粉饰。"
            ],
            "registered_test_assets": []
          }
        },
        {
          "check_id": "C9",
          "name": "生产 6 门矩阵的行动作计数与自述『动作计数』一致",
          "result": "pass",
          "severity_if_fail": "blocking",
          "detail": {
            "matrix_rows": 6,
            "matrix_counts": {
              "hold_owner_only": 1,
              "wait": 5
            },
            "stated": {
              "release": "0",
              "wait": "5",
              "hold_owner_only": "1"
            },
            "quote": "- 动作计数：release=0 / wait=5 /",
            "quote_continuation": "hold_owner_only=1",
            "note": "该行在原文里被硬换行折成两行（首行以 '/' 结尾，续行为 hold_owner_only=1）；计数按合并后文本解析"
          }
        },
        {
          "check_id": "C10",
          "name": "沙箱表行动作计数 == 自述审计动作计数，且 release 集合一致",
          "result": "pass",
          "severity_if_fail": "blocking",
          "detail": {
            "sandbox_counts": {
              "hold_owner_only": 1,
              "release": 4,
              "wait": 1
            },
            "audit_counts": {
              "rollback": 4,
              "hold_owner_only": 1,
              "release": 4,
              "wait": 1
            },
            "released": [
              129,
              144,
              153,
              170
            ],
            "quote": "- 审计动作计数：{'rollback': 4, 'hold_owner_only': 1, 'release': 4, 'wait': 1}；字段完整性 `audit_rows_complete=True`；"
          }
        },
        {
          "check_id": "C11",
          "name": "release↔rollback 配对自洽（4 放 / 4 回滚）",
          "result": "pass",
          "severity_if_fail": "blocking",
          "detail": {
            "release": 4,
            "rollback": 4,
            "released_rows": 4
          }
        },
        {
          "check_id": "C12",
          "name": "生产首轮审计行数 7 = 6 门动作 + G21 一行的算术自洽",
          "result": "pass",
          "severity_if_fail": "minor",
          "detail": {
            "six_gate_wait": 5,
            "six_gate_hold": 1,
            "g21_wait": 1,
            "derived_total": 7,
            "note": "总数自洽；但正文把 6 个 wait 行写成『六门 wait ×6』，而六门中 wait=5、hold=1，第 6 个 wait 来自 plan 21 的 G21",
            "prose_quote": "- 首轮 `gate_release_audit` 落 7 行（G20 `hold_owner_only` ×1 + 六门 `wait` ×6，"
          }
        },
        {
          "check_id": "C13",
          "name": "判据表显式声明 C3(治理门) 先于 C2(工件可解析) 的判定优先级",
          "result": "fail",
          "severity_if_fail": "minor",
          "detail": {
            "gate185_row": [
              "185",
              "SPEC军G20·S×E闭环验收门",
              "done",
              "`artifacts/spec_impl_acceptance.json`→not_found",
              "`hold_owner_only`",
              "`governance_marker=SPEC军`"
            ],
            "explanation": "185 行判据工件 not_found（C2 不满足）却给 hold_owner_only（C3），说明实现让 C3 短路 C2；判据表只列 C1/C2/C3 未写优先级，仅靠 C3 描述里的『永不自动放』隐含",
            "criteria_table": [
              [
                "C1 上游就绪",
                "每个 `dependencies` 节点存在且 `status='done'`",
                "继续等（`upstream_pending`）"
              ],
              [
                "C2 判据工件可解析",
                "metadata 声明的证据路径在 roots 中解析到**非空文件**；`.json` 还需 json 合法；`metadata.repo` 声明时命中路径须在该仓内",
                "继续等（`artifact_missing`）"
              ],
              [
                "C3 非治理门",
                "`metadata.owner_only` 非真 + 门名/goal 无治理标记",
                "只标 `owner_only=1`，**永不自动放**"
              ]
            ]
          }
        },
        {
          "check_id": "C14",
          "name": "生产快照哈希给全（可被独立重算/比对）",
          "result": "fail",
          "severity_if_fail": "minor",
          "detail": {
            "quote": "- 生产全表快照：before `56e8ab792ceeeb40db68538a…` =",
            "truncated": true,
            "impact": "production_untouched=True 只能采信程序结论，外部无法复算"
          }
        },
        {
          "check_id": "C15",
          "name": "图件 A12 的 png 载荷随报告记录发布（下游可否验图）",
          "result": "fail",
          "severity_if_fail": "minor",
          "detail": {
            "figures": [
              {
                "name": "gate_auto_release_drill.png...",
                "caption": "左：G13–G20 六门判据矩阵（上游/工件/非治理 × 6 门）与判词；右：生..."
              }
            ],
            "impact": "上游把 A12 记为 referenced_unresolved 是诚实的；但图内容对下游不可验"
          }
        }
      ],
      "locator_matrix": [
        {
          "asset_id": "A01",
          "quote": "ops/taskplane/gate_auto_release.py",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 1301,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A02",
          "quote": "gate_auto_release_loop.sh",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 1439,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A03",
          "quote": "deploy/taskplane/gate-auto-release.service",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 1486,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A04",
          "quote": "tools/gate_drill.py",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 1632,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A05",
          "quote": "supervise.py",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 1558,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A06",
          "quote": "taskplane.manifest.yaml",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 1583,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A07",
          "quote": "artifacts/system_pierce_acceptance.json",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 2042,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A08",
          "quote": "artifacts/deepwater_gap_ledger_update.json",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 2158,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A09",
          "quote": "artifacts/autoregression_acceptance.md",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 2278,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A10",
          "quote": "artifacts/chronicler_acceptance.json",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 2467,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A11",
          "quote": "artifacts/spec_impl_acceptance.json",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 2583,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A12",
          "quote": "artifacts/gate_auto_release_drill.png",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 3721,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A13",
          "quote": "gate_release_audit",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 2,
          "declared_unique": true,
          "first_index": 1387,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A14",
          "quote": "tensorplatform.campaign_nodes",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 1,
          "declared_unique": true,
          "first_index": 339,
          "first_index_equals_span": true
        },
        {
          "asset_id": "A15",
          "quote": "gate_drill",
          "span_exact": true,
          "line_ok": true,
          "occurrences": 2,
          "declared_unique": true,
          "first_index": 1638,
          "first_index_equals_span": true
        }
      ],
      "claims_assessed": [
        {
          "claim_id": "C-01",
          "text": "wp-5757-01 provenance.source_hash / source_chars 与 report 5757 markdown 字节一致",
          "status": "supported",
          "evidence": {
            "recomputed_hash": "sha256:d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915",
            "chars": 5061
          }
        },
        {
          "claim_id": "C-02",
          "text": "15 个资产的 char_span/行号在原文逐字命中",
          "status": "supported",
          "evidence": {
            "checked": 15,
            "failed": []
          }
        },
        {
          "claim_id": "C-03",
          "text": "locator.unique=true 对全部资产成立",
          "status": "refuted",
          "evidence": {
            "non_unique": [
              "A13",
              "A15"
            ]
          }
        },
        {
          "claim_id": "C-04",
          "text": "5 个判据工件 declared_absent",
          "status": "partially-supported",
          "evidence": {
            "quote": "证据在临时根按 `<repo>/artifacts/…` 同形造出\n（显式 `synthetic: true`）",
            "note": "生产侧确实 not_found（A07–A11 表行一致），但沙箱内同形存在；manifest 的 per-asset note 写了『生产侧 not_found』，状态词表本身未带这个限定"
          }
        },
        {
          "claim_id": "C-05",
          "text": "code/config 资产 referenced_unresolved 因为它们住在其它仓",
          "status": "supported",
          "evidence": {
            "note": "主机上 TensorPlatform 检出内 6/6 路径存在（gate_auto_release.py 849 行、gate_auto_release_loop.sh 48 行、deploy/taskplane/gate-auto-release.service 34 行、tools/gate_drill.py 262 行、ops/taskplane/supervise.py、ops/taskplane/taskplane.manifest.yaml）；在 TensorKnowledge 工作树内确实不可解析 → unresolved 分类诚实"
          }
        }
      ],
      "findings": [
        {
          "id": "F1",
          "severity": "minor",
          "likelihood": "certain",
          "title": "locator.unique=true 对 A13/A15 不成立（引文在原文出现 2 次）",
          "scope": "wp-5757-01 asset_manifest.json assets[12].locator、assets[14].locator",
          "evidence": {
            "asset_ids": [
              "A13",
              "A15"
            ],
            "quotes": [
              "gate_release_audit",
              "gate_drill"
            ],
            "occurrences": {
              "A13": 2,
              "A15": 2
            },
            "first_index_equals_recorded_span": {
              "A13": true,
              "A15": true
            }
          },
          "reproduction": "python3 docs/kf/wp-5757-04/verify_wp_5757_04.py → 检查项 C6",
          "impact": "机器可读字段与事实不符；但 md.find(quote) 对 15/15 资产都等于记录 start_char，按 first-occurrence 解析的下游不会错位；只有依赖『引文唯一』不变量的消费方会被绊倒。",
          "remediation": "把 unique 改成 occurrence_count=1/2 的真实计数，或改用 (start_char,end_char) 作为唯一键。",
          "blocking": false
        },
        {
          "id": "F2",
          "severity": "minor",
          "likelihood": "certain",
          "title": "召回缺口：报告以『pytest 覆盖』为证据的测试套件未登记为资产",
          "scope": "asset_manifest.json summary.total_assets=15 的资产全集",
          "evidence": {
            "report_quote": "10 条 pytest 覆盖，**尚无生产 release 审计行**——如实披露，不粉饰。",
            "registered_test_assets": [],
            "host_corroboration": "TensorPlatform 检出（commit 3d6ff8aba 的 worktree）tests/test_gate_auto_release.py 含 10 个 def test_，与报告『10 条』相符"
          },
          "reproduction": "verify C8；grep -c '^def test_' tests/test_gate_auto_release.py（TensicrosoftPlatform 检出）",
          "impact": "资产清单作为下游 inventory 基线时，release 路径的唯一测试证据不可定位。",
          "remediation": "增补 asset（class=test），locator 指向报告里出现 pytest 的那一行。",
          "blocking": false
        },
        {
          "id": "F3",
          "severity": "minor",
          "likelihood": "certain",
          "title": "判据表未声明 C3 先于 C2 的优先级，但结果（G20 判 hold 而非 wait）依赖该优先级",
          "scope": "报告 ② 判据表 vs ③ 生产矩阵 G20(185) 行",
          "evidence": {
            "gate185_row": "185 | SPEC军G20·S×E闭环验收门 | done | `artifacts/spec_impl_acceptance.json`→not_found | `hold_owner_only` | `governance_marker=SPEC军`",
            "criteria_quote": "C3 非治理门 | `metadata.owner_only` 非真 + 门名/goal 无治理标记 | 只标 `owner_only=1`，**永不自动放**"
          },
          "reproduction": "verify C13",
          "impact": "实现层 evaluate_gate() 以 owner_only 短路（见外部核对）；报告只靠『永不自动放』隐含，若下游按表中 C1→C2→C3 顺序重实现，G20 会得到 wait 而不是 hold，owner_only 保护叙事被削弱。",
          "remediation": "判据表加一行明文『优先级 C3 > C1 > C2』。",
          "blocking": false
        },
        {
          "id": "F4",
          "severity": "note",
          "likelihood": "certain",
          "title": "生产快照哈希被截断展示（56e8ab79…），production_untouched 外部不可复算",
          "scope": "报告 ③ 生产只读矩阵末条",
          "evidence": {
            "quote": "- 生产全表快照：before `56e8ab792ceeeb40db68538a…` ="
          },
          "reproduction": "verify C14",
          "impact": "只能采信程序结论；跨轮比对与归档无法验证快照未变的强证据。",
          "remediation": "程序化注入完整 64 hex 摘要（before/after）。",
          "blocking": false
        },
        {
          "id": "F5",
          "severity": "note",
          "likelihood": "certain",
          "title": "图件 A12 只带 name+caption、GET 读接口不回传 png_base64（平台读侧行为，非生产者漏发）",
          "scope": "平台 report 5757 figures[0]；manifest A12 resolution=referenced_unresolved",
          "evidence": {
            "figure_name": "gate_auto_release_drill.png",
            "figure_keys": [
              "caption",
              "name"
            ],
            "manifest_quote": "artifacts/gate_auto_release_drill.png",
            "self_roundtrip": "本单自己的 KF-RESULT 报告以 figures[].png_base64 内嵌发布后，经同一 GET /api/v1/tensor/reports/<id> 回读，figures 也只剩 name+caption（复现：python3 docs/kf/wp-5757-04/probe_figure_payload.py 5757 <id>）"
          },
          "reproduction": "verify C15；GET /api/v1/tensor/reports/5757 → figures[0] 无 png_base64；探针见 probe_figure_payload.py",
          "impact": "上游把 A12 记为 referenced_unresolved 是**完全正确**的分类；缺失不在报告 5757、也不在 wp-5757-01，而在平台读侧不返回图件载荷 → 任何下游都验不了图。因此本项归属平台侧改进，不构成对上游的缺陷。",
          "remediation": "平台读侧提供图件下载端点或回传 png sha256；wp-5757-01 / report 5757 侧无需改动。",
          "blocking": false
        },
        {
          "id": "F6",
          "severity": "note",
          "likelihood": "likely",
          "title": "『只判工件在不在、不判内容对错』与仓内新增 gate_content_criteria 层可能版本失同步",
          "scope": "报告 ⑤.5 局限 vs TensorPlatform 检出 ops/taskplane/gate_content_criteria.py + evaluate_gate() 内 C2b 分支",
          "evidence": {
            "report_quote": "只判「工件在不在、json 是否合法」，不判内容对错（内容由验收链负责）",
            "host_files": "ops/taskplane/gate_content_criteria.py、gate_auto_release.py 中 '# C2b 判据内容' 分支"
          },
          "reproduction": "grep -n 'C2b' ops/taskplane/gate_auto_release.py（TensorPlatform 检出）",
          "impact": "若产线版本已含 C2b，则报告局限描述偏保守/过期；但未绑定 commit，无法定论 → 记 note 而非 defect。",
          "remediation": "报告补 commit sha；或注明 C2b 仅在门显式声明 checks 时生效。",
          "blocking": false
        }
      ],
      "checks_not_run": [
        {
          "id": "N1",
          "what": "生产 campaign_nodes 六门的 dependencies/status/metadata.owner_only 实测",
          "reason": "psql: permission denied for table campaign_nodes"
        },
        {
          "id": "N2",
          "what": "浮点/物理量基线比对",
          "reason": "非该类报告（治理/后端机制，无物理量）"
        },
        {
          "id": "N3",
          "what": "沙箱 UPDATE/rollback 真跑复现",
          "reason": "需写生产库隔离 schema 权限；按本单边界不改上游状态"
        }
      ],
      "overstated_claims": [
        {
          "claim": "locator.unique=true（A13/A15）",
          "why": "引文各出现 2 次",
          "finding": "F1"
        },
        {
          "claim": "declared_absent 对 A07–A11",
          "why": "只对生产侧成立，沙箱内同形存在（report 自述 synthetic:true）",
          "finding": "F2 相关"
        },
        {
          "claim": "「六门 wait ×6」",
          "why": "六门中 wait=5、hold=1，第 6 个 wait 来自 plan 21 的 G21；总行数 7 仍自洽",
          "finding": "F7(算术措辞)"
        }
      ],
      "summary_counts": {
        "checks_total": 15,
        "checks_pass": 10,
        "checks_fail": 5,
        "blocking_failures": [],
        "findings": {
          "blocking": 0,
          "major": 0,
          "minor": 3,
          "note": 3
        }
      },
      "remediation_required": [
        {
          "id": "R1",
          "owner": "wp-5757-01",
          "from_finding": "F1",
          "action": "locator.unique 改为真实 occurrence_count（A13/A15=2），或以 (start_char,end_char) 作唯一键",
          "blocking": false
        },
        {
          "id": "R2",
          "owner": "wp-5757-01",
          "from_finding": "F2",
          "action": "增补 test 类资产（pytest 套件），locator 指向『10 条 pytest 覆盖』所在行",
          "blocking": false
        },
        {
          "id": "R3",
          "owner": "report-5757",
          "from_finding": "F3",
          "action": "判据表补一行『优先级 C3 > C1 > C2』",
          "blocking": false
        },
        {
          "id": "R4",
          "owner": "report-5757",
          "from_finding": "F4",
          "action": "程序化注入完整 64-hex 快照摘要（before/after）",
          "blocking": false
        },
        {
          "id": "R5",
          "owner": "platform",
          "from_finding": "F5",
          "action": "读侧提供图件下载端点或回传 png sha256（wp-01 与 report 5757 侧无需改动）",
          "blocking": false
        },
        {
          "id": "R6",
          "owner": "report-5757",
          "from_finding": "F6",
          "action": "报告补产线 commit sha；或注明 C2b 仅在门显式声明 checks 时生效",
          "blocking": false
        }
      ],
      "verdict": "pass",
      "disposition": "pass with notes（无 blocking 缺陷；F1/F2/F3 建议在 wp-01 侧小改，F4/F5/F6 归报告侧或下游）",
      "verdict_rule": "blocking=出处/哈希不可定位、资产凭空捏造、分类与原文矛盾；以上均未触发（15/15 locator 逐字命中、哈希独立重算一致、无虚构资产）。minor=机器可读字段为假或召回缺口（不改变下游解析结果）。",
      "do_not_mark_claims_as_verified": true,
      "emitted_at": "2026-11-07T03:36:09.837420+00:00"
    }
  },
  "claims": []
}
```

**repro_cmd**（工作树根执行；一键复跑机检并重建审核正文与图）：

```bash
# 1) 取原文并独立重算哈希/字符数（打印值须 = sha256:d85b5a16…bd915 / chars=5061）
python3 - <<'PY'
import json, os, urllib.request, hashlib
b = os.environ["TENSOR_API_BASE"].rstrip("/")
r = json.load(urllib.request.urlopen(urllib.request.Request(
    b + "/auth/login",
    data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                     "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
    headers={"Content-Type": "application/json"})))
d = json.load(urllib.request.urlopen(urllib.request.Request(
    b + "/tensor/reports/5757",
    headers={"Authorization": "Bearer " + r["access_token"]})))
open("/tmp/report_5757.json", "w").write(json.dumps(d, ensure_ascii=False))
print("sha256:" + hashlib.sha256(d["markdown"].encode()).hexdigest(), "chars:", len(d["markdown"]))
PY
# 2) 15 项机检（退出码 0 = 无 blocking 失败）
python3 docs/kf/wp-5757-04/verify_wp_5757_04.py
# 3) 重建 review_report.json / kf_result.json / 审核矩阵图
python3 docs/kf/wp-5757-04/build_review_report.py
# 4) 重建本报告正文与发布载荷
python3 docs/kf/wp-5757-04/build_report_md.py
# 5) 信封 schema 校验
python3 -c "import json,jsonschema;jsonschema.validate(json.load(open('docs/kf/wp-5757-04/kf_result.json')),json.load(open('schemas/kf_result.v1.schema.json')));print('schema PASS')"
```
```
