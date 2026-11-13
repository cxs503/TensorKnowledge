# KF-RESULT wp-427-04

tags: kf-wp:wp-427-04, 04-independent-review, report:427, lane:C, in-review

本报告是**报告→知识产线工序 04（独立审核）**的工作包结果，审核对象=`wp-427-01`（01-asset-registration），
被审源报告 `report_id=427`（DIT 衰减各向同性湍流验证诊断报告，m518）。
审核输入仅两样：源报告 `markdown` 原文（本进程内重取）+ 上游信封内 `outputs["asset_manifest.json"]`；
上游结果报告正文的解释/自评（⑤⑥ 结论）**不作判据**。

## ① 案例介绍（审核对象与被审对象）

| 项 | 值（程序化注入） |
|---|---|
| 审核工作包 | `wp-427-04`（`04-independent-review`，reviewer_role=`red-team-reviewer`） |
| 被审工作包 | `wp-427-01`（`01-asset-registration`），结果报告 id=`14590` |
| 被审源报告 | `report_id=427` → `DIT 衰减各向同性湍流验证诊断报告（m518）`，scenario_key=`dit_turbulence` |
| 上游信封 sha256 | `sha256:0a979439748792d22fad8d8518c51b33c10c0fc34217a0ebeef6140c942524a0`（= 交付 json 块字节） |
| 交付信道合规 | title=`KF-RESULT wp-427-01`（ok=True）、tag=`kf-wp:wp-427-01`（ok=True）、json 块数=`1` |

**为什么需要本工序**：01 工序的 objective 是"只登记资产、不抽 claim"，因此 `claims=[]`；
平台门 `g5_source_locator_resolvable` 在 claims 为空时不遍历 locator 数组（`checked=0`、`locator_rate=null`），
**9 条 locator 全部是生产者自报、未经机器校验**。本工序把这 9 条连同哈希/计数/ID 逐条重算，把自报变成可复核事实。

## ② 怎么做的（方法/工具链/关键设置）

1. `POST /api/v1/auth/login`（`$TENSOR_AGENT_USER`）取 Bearer token；`GET /api/v1/tensor/reports/427` 重取 `markdown`（**不采信上游数字**）。
2. 本进程内算 `sha256(markdown.encode('utf-8'))`、`len()`、`len(md.splitlines())`、`b'\r\n'` 检查，与契约 `input.source_hash` / `chars=2732` 比对（精确相等判据，非阈值）。
3. `GET /api/v1/tensor/reports/14590` 取上游结果报告，**只解析其中唯一的 ```json 代码块**（= 上游交付的 `kf_result_envelope.json` 字节），正文叙述跳过。
4. 信封 → `jsonschema`（Draft 2020-12，仓库 `schemas/kf_result.v1.schema.json`）校验；`provenance.source_hash` 与步骤 2 的独立重算值比对。
5. 9 条 locator：逐条重算 `sha256(quote)`、全文出现次数、`quote ∈ lines[line-1]`（1-indexed），与自报三个布尔值 + 次数 + 哈希对齐。
6. `asset_manifest.source` 块（hash/chars/lines）与 `source_document` 资产（bytes/has_crlf/sha256）分别与重算值比对；`counts` 7 项与数组实际长度自洽；递归收集 `*_id` 查重。
7. 4 张 figure：`GET /tensor/reports/427/figures/<name>` 与 `<name>.png` 两种变体独立探测；caption 与记录字段逐字比对。
8. 生产者 §③ 工件哈希表（5 条）逐条尝试复算：信封/图件直接取交付信道字节；manifest 用 64 种 `json.dumps`
   参数组合（indent × separators × sort_keys × 尾换行）反推复现配方。
9. matplotlib 3.10.8（Agg，150 dpi）出图 1 张；一键复跑：`python3 scripts/kf_wp42704_review.py && python3 scripts/kf_wp42704_publish.py --post-report`。

关键设置：**零手抄**（所有数字脚本内计算后注入）；**边界**=只碰 report_id=427；不生成任何 claim，不标 verified。

## ③ 计算结果（数字表，程序化注入）

### 源报告身份（独立重算 vs 契约）

| 量 | 契约/上游声明 | 本工序重算 | 一致 |
|---|---|---|---|
| markdown sha256 | `sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846` | `sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846` | True |
| 字符数 | 2732 | 2732 | True |
| UTF-8 字节数 | 4067 | 4067 | True |
| 行数（splitlines） | 111 | 111 | True |
| has_crlf | False | False | True |

### 9 条 locator 逐条重算（1-indexed 行号）

| fact_id | 声明行 | 全文出现次数（重算） | quote sha256 一致 | 在该行逐字命中 |
|---|---|---|---|---|
| report-title | 1 | 1 | ✓ | ✓ |
| lattice-model | 12 | 1 | ✓ | ✓ |
| collision-model | 13 | 1 | ✓ | ✓ |
| slope-N64 | 42 | 1 | ✓ | ✓ |
| decay-N128 | 53 | 1 | ✓ | ✓ |
| cpu-walltime | 63 | 1 | ✓ | ✓ |
| cpu-gpu-bitwise | 67 | 1 | ✓ | ✓ |
| figure-pointer | 71 | 1 | ✓ | ✓ |
| pre-rework-chars | 99 | 1 | ✓ | ✓ |

汇总：**9/9** 条与自报完全一致（自报"9/9 resolved"被证实，非越界标注）。

### 计数与 ID 自洽

| 量 | 声明 | 重算 | 一致 |
|---|---|---|---|
| source_documents | 1 | 1 | True |
| figures_declared / resolved | 4 / 0 | 4 / 0 | True |
| locators / resolved | 9 / 9 | 9 / 9 | True |
| derived_artifacts | 3 | 3 | True |
| claims | 0 | 0 | True |
| `*_id` 收集 / 重复 | 8 / 0 | 8 / 0 | True |

### figure 可取回性（独立探测，两种命名变体）

| figure | caption 逐字一致 | 端点状态（name / name.png） |
|---|---|---|
| spectra_evolution | True | spectra_evolution=404 / spectra_evolution.png=404 |
| energy_decay | True | energy_decay=404 / energy_decay.png=404 |
| slope_evolution | True | slope_evolution=404 / slope_evolution.png=404 |
| cpu_vs_gpu | True | cpu_vs_gpu=404 / cpu_vs_gpu.png=404 |

### 生产者 §③ 工件哈希表的复算覆盖率

| 工件 | 声明字节 | 复算结果 |
|---|---|---|
| `runs/wp-427-01/kf_result_envelope.json` | 11324 | ✓ 复现（= 交付 json 块字节，sha256 相等） |
| `runs/wp-427-01/asset_manifest.json` | 9672 | ✓ 复现（配方 indent=2 + 尾换行，sha256 相等） |
| `runs/wp-427-01/fig_locator_map.png` | 51654 | ✓ 复现（IHDR 几何 {'valid_png': True, 'width': 1650, 'height': 540}） |
| `runs/wp-427-01/source_427.md` | 4067 | ✓ 字节数与哈希均与源 markdown 重算值一致 |
| `runs/wp-427-01/verification.json` | 2557 | unknown（生产者工作树不可达，未证实未证伪） |

## ④ 结果图

`wp42704_recheck_scorecard.png`：左=6 项 acceptance 的自报 vs 独立复算（全绿）；右=9 条 locator 在 111 行源文档中的落点与全文出现次数。
用途：一眼看出"自报值"与"重算值"是否同源失真——9 个点全部落在声明的行上且次数为 1，排除了
"引文存在但不在声明行"与"引文不唯一（可被多处复用做伪定位）"两类典型失败模式。

## ⑤ 注意点与局限（发现分级）

| 编号 | 严重度 | 作用域 | 结论 |
|---|---|---|---|
| F1 | medium | source_record(report_id=427) / upstream-of-package | 源记录声明 4 张 figure，但 figure 端点对两种命名变体均取不到 PNG 字节；报告正文 ④ 却写「4 张 PNG 内嵌」。上游按 resolvable=false + 404 原文登记，该登记被本审核独立复现。缺陷在源记录，不在 wp-427-01 产出。 |
| F2 | low | platform gate coverage / wp-427-01 | 平台门 g5_source_locator_resolvable 记 checked=0、locator_rate=null（claims 为空时门不遍历 locator 数组），故 9 条 locator 未经机器校验；本审核逐条重算后 9/9 与自报一致，缺口被补上但不构成上游错误。 |
| F3 | low | wp-427-01 derived_artifacts | manifest 登记 3 个派生工件（源副本/verification/envelope）及其 sha256，均位于生产者工作树，审核方不可达；本审核把它们记为 unknown，不判 pass。 |
| F5 | info | wp-427-01 delivery channel | 把生产者自报的工件哈希从『自报』升级为『已独立复现』：asset_manifest.json、fig_locator_map.png、kf_result_envelope.json、source_427.md（含字节数；manifest 的复现配方 = {"indent": 2, "sep": [",", ": "], "tail": "\n", "sort": false, "sha256": "sha256:93ade4961e23932351147a76780060770233ca9d57285a4b27d540f0df99f91e"}）。未复现：runs/wp-427-01/verification.json（生产者工作树不可达）。 |
| F6 | low | source_record(report_id=427) / risk for downstream wp-427-02/03 | 源报告末尾『治理升级』附录把 ①~⑥ 六节全部标为『待补充』，而正文六节实际齐备；上游把该附录语句作为事实 locator（pre-rework-chars）登记，未标注矛盾。对 01（只登记资产）不构成违约，但 02/03 若把附录当成『章节缺失』证据会失真——本审核显式预警。 |

- **F1（medium，源记录缺陷，非本工作包缺陷）**：4/4 figure 端点 404（`{"detail":"figure not found"}`），而报告正文 ④ 写"4 张 PNG 内嵌"。上游按 `resolvable=false`+404 原文登记，本审核独立复现该 404。
- **F2（low，门覆盖缺口）**：01 工序 claims 为空 → 平台 locator 门 `checked=0`，9 条 locator 全靠自报。本工序逐条复算补上了这个缺口，建议把 locator 数组纳入 01 的机器门。
- **F3（low，unknown 不判 pass）**：3 个派生工件位于生产者工作树；其中 `verification.json` 无法从交付信道复算 → 记 unknown。
- **F5（info，正向）**：生产者自报的 5 条工件哈希中 4 条已由交付信道独立复现（含 manifest 的序列化配方），可追溯性优于"仅自报"。
- **F6（low，下游风险预警）**：源报告末尾"治理升级"附录把 ①~⑥ 全标"待补充"，而正文六节齐备 —— 01 只登记资产不算违约，但 02/03 若把附录当"章节缺失"证据会失真。

**局限**（诚实列出，不当 pass 计）：
- 生产者"同 endpoint 对其它记录返回 200/67,305 B"的对照：越本单 `report_id=427` 边界，未复核 → F1 中"端点非故障"结论在审核侧仅 partially-supported。
- figure 图像内容 vs 正文数字一致性：无 payload，无可校验对象。
- `verification.json` 字节：不可达。

## ⑥ 误差判定：是否 <3%

| 判据 | 基准 | 本工序值 | 误差 | <3%？ |
|---|---|---|---|---|
| markdown sha256 | 契约 `sha256:09c640623dff50ac9…` | 重算同值 | 0（精确相等） | ✓ |
| 字符数 | 2732 | 2732 | 0 | ✓ |
| locator 逐字命中 | 9/9（自报） | 9/9 | 0 | ✓ |
| counts 自洽 | 7 项 | 7/7 一致 | 0 | ✓ |
| ID 唯一 | 8 无重复 | 8 无重复 | 0 | ✓ |
| figure 可取回 | 4/4（报告宣称"内嵌"） | 0/4 | 100%（全面缺失） | ✗（F1，缺陷在源记录） |
| 工件哈希复现 | 5 条 | 4/5 | 20%（1 条 unknown） | ✗（F3，非缺陷但未闭合） |

**结论**：wp-427-01 的 6 项 acceptance **全部独立复核通过**（verdict=`pass`，disposition=`approve`，
blocking findings=0）。两项不达标（figure 可取回率 0/4、工件哈希覆盖 4/5）都**不落在 01 工序的义务面**：
前者是源记录缺 payload，后者是文件不可达；审核侧如实记为 unknown/源缺陷，不粉饰为通过。

## ⑦ 自检：逐条对照 acceptance

| acceptance 项 | 本工序自检 |
|---|---|
| valid_json | ✓ `review_report.json`/`kf_result.json` 均 `json.loads` 通过 |
| schema_pass | ✓ 信封过 `schemas/kf_result.v1.schema.json`（jsonschema 4.26.0，errors=none） |
| reviewer_independent | ✓ 独立重取源、独立重算全部数字；上游叙述仅取事实性哈希表，未采信其结论 |
| upstream_packages_completed | ✓ `wp-427-01.status=review`、`gates_ok=true`（平台表 tk_work_packages），result_report_id=14590 可取回 |

另：`do_not_mark_claims_as_verified` ✓（manifest 全文扫描 "verified"/"已核验" 命中 0 条）；本工序 `claims=[]`（审核工序不产知识）。

repro_cmd：`cd <worktree> && python3 scripts/kf_wp42704_review.py && python3 scripts/kf_wp42704_publish.py --post-report`

```json
{
  "package_id": "wp-427-04",
  "task_type": "04-independent-review",
  "report_id": "427",
  "provenance": {
    "source_hash": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
    "source_field": "markdown",
    "producer": "kf-worker/m15789",
    "emitted_at": "2026-11-12T02:39:57.476351+00:00",
    "notes": "source_hash recomputed in-process from GET /tensor/reports/427 markdown UTF-8 bytes; reviewed package wp-427-01 result_report_id=14590"
  },
  "outputs": {
    "review_report.json": {
      "review_id": "review:wp-427-04:wp-427-01",
      "package_id": "wp-427-04",
      "task_type": "04-independent-review",
      "reviews_package_id": "wp-427-01",
      "report_id": "427",
      "reviewer_role": "red-team-reviewer",
      "reviewed_at": "2026-11-12T02:39:57.470265+00:00",
      "subject": {
        "package_id": "wp-427-01",
        "result_report_id": "14590",
        "result_report_markdown_sha256": "sha256:f8b2e7702b572514604e55c58d054fa10765137e8ac351993dc40118bfae853f",
        "result_report_chars": 16148
      },
      "independence": {
        "inputs_used": [
          "report 427 markdown (platform API refetch)",
          "report 427 record fields (title/scenario_key/figures)",
          "upstream envelope json block (outputs.asset_manifest.json)",
          "wp-427-01 contract (objective/acceptance) for legality judgement"
        ],
        "narrative_use": "上游正文仅用于取两处**事实性**元数据：§③ 工件哈希表（用于复算）与 ①②节的法条/工单号；其解释与自评（⑤⑥ 结论、'端点非故障'等）不作判据。",
        "excluded": [
          "上游结果报告正文第①~⑥节叙述（生产者的解释与自评）",
          "生产者工作树内文件内容"
        ],
        "review_prompt_not_copied_from_producer": true,
        "reviewer_context_excludes_producer_explanation": true,
        "numbers_source": "全部在本进程内重算（hashlib/len/splitlines/urllib），零手抄"
      },
      "verdict": "pass",
      "verdict_basis": {
        "acceptance_recheck_all_true": true,
        "blocking_findings": [],
        "non_blocking_findings": [
          "F1",
          "F2",
          "F3",
          "F5",
          "F6"
        ],
        "delivery_channel_ok": {
          "title_ok": true,
          "tag_ok": true,
          "single_json_block": true
        }
      },
      "acceptance_recheck": [
        {
          "item": "valid_json",
          "upstream_claim": true,
          "independently_recomputed": true,
          "result": "pass"
        },
        {
          "item": "schema_pass",
          "upstream_claim": true,
          "independently_recomputed": true,
          "result": "pass"
        },
        {
          "item": "source_hash_matches",
          "upstream_claim": true,
          "independently_recomputed": true,
          "result": "pass"
        },
        {
          "item": "source_locator_resolvable",
          "upstream_claim": "9/9",
          "independently_recomputed": 9,
          "result": "pass"
        },
        {
          "item": "no_duplicate_ids",
          "upstream_claim": true,
          "independently_recomputed": true,
          "result": "pass"
        },
        {
          "item": "all_claims_have_evidence_or_explicit_unresolved_status",
          "upstream_claim": "claims=[] + 契约理由",
          "independently_recomputed": true,
          "result": "pass"
        }
      ],
      "findings": [
        {
          "finding_id": "F1",
          "severity": "medium",
          "scope": "source_record(report_id=427) / upstream-of-package",
          "statement": "源记录声明 4 张 figure，但 figure 端点对两种命名变体均取不到 PNG 字节；报告正文 ④ 却写「4 张 PNG 内嵌」。上游按 resolvable=false + 404 原文登记，该登记被本审核独立复现。缺陷在源记录，不在 wp-427-01 产出。",
          "evidence": [
            {
              "check": "figures.details[*].endpoint",
              "detail": [
                {
                  "name": "spectra_evolution",
                  "endpoint": [
                    {
                      "variant": "spectra_evolution",
                      "status": 404,
                      "bytes": 29,
                      "body_head": "{\"detail\":\"figure not found\"}"
                    },
                    {
                      "variant": "spectra_evolution.png",
                      "status": 404,
                      "bytes": 29,
                      "body_head": "{\"detail\":\"figure not found\"}"
                    }
                  ]
                },
                {
                  "name": "energy_decay",
                  "endpoint": [
                    {
                      "variant": "energy_decay",
                      "status": 404,
                      "bytes": 29,
                      "body_head": "{\"detail\":\"figure not found\"}"
                    },
                    {
                      "variant": "energy_decay.png",
                      "status": 404,
                      "bytes": 29,
                      "body_head": "{\"detail\":\"figure not found\"}"
                    }
                  ]
                },
                {
                  "name": "slope_evolution",
                  "endpoint": [
                    {
                      "variant": "slope_evolution",
                      "status": 404,
                      "bytes": 29,
                      "body_head": "{\"detail\":\"figure not found\"}"
                    },
                    {
                      "variant": "slope_evolution.png",
                      "status": 404,
                      "bytes": 29,
                      "body_head": "{\"detail\":\"figure not found\"}"
                    }
                  ]
                },
                {
                  "name": "cpu_vs_gpu",
                  "endpoint": [
                    {
                      "variant": "cpu_vs_gpu",
                      "status": 404,
                      "bytes": 29,
                      "body_head": "{\"detail\":\"figure not found\"}"
                    },
                    {
                      "variant": "cpu_vs_gpu.png",
                      "status": 404,
                      "bytes": 29,
                      "body_head": "{\"detail\":\"figure not found\"}"
                    }
                  ]
                }
              ]
            },
            {
              "markdown_quote": "见 figures 字段（4 张 PNG 内嵌）。"
            }
          ],
          "blocking_for_upstream_package": false,
          "impact": "下游像素级工序（图件抽取/图像核验）在 427 上无可校验对象，只能登记缺口。"
        },
        {
          "finding_id": "F2",
          "severity": "low",
          "scope": "platform gate coverage / wp-427-01",
          "statement": "平台门 g5_source_locator_resolvable 记 checked=0、locator_rate=null（claims 为空时门不遍历 locator 数组），故 9 条 locator 未经机器校验；本审核逐条重算后 9/9 与自报一致，缺口被补上但不构成上游错误。",
          "evidence": [
            {
              "gate_record": "gates.g5_source_locator_resolvable.checked = 0"
            },
            {
              "check": "locators.n_independently_confirmed",
              "value": 9
            }
          ],
          "blocking_for_upstream_package": false,
          "impact": "若上游自报 locator 有误，平台门不会拦；建议 01 工序把 locator 纳入机器门。"
        },
        {
          "finding_id": "F3",
          "severity": "low",
          "scope": "wp-427-01 derived_artifacts",
          "statement": "manifest 登记 3 个派生工件（源副本/verification/envelope）及其 sha256，均位于生产者工作树，审核方不可达；本审核把它们记为 unknown，不判 pass。",
          "evidence": [
            {
              "paths": [
                "runs/wp-427-01/source_427.md",
                "scripts/kf_wp42701_register_assets.py",
                "runs/wp-427-01/fig_locator_map.png"
              ]
            }
          ],
          "blocking_for_upstream_package": false,
          "impact": "不影响信封级判据（source_hash/locator/counts 均已独立复算）。"
        },
        {
          "finding_id": "F5",
          "severity": "info",
          "scope": "wp-427-01 delivery channel",
          "statement": "把生产者自报的工件哈希从『自报』升级为『已独立复现』：asset_manifest.json、fig_locator_map.png、kf_result_envelope.json、source_427.md（含字节数；manifest 的复现配方 = {\"indent\": 2, \"sep\": [\",\", \": \"], \"tail\": \"\\n\", \"sort\": false, \"sha256\": \"sha256:93ade4961e23932351147a76780060770233ca9d57285a4b27d540f0df99f91e\"}）。未复现：runs/wp-427-01/verification.json（生产者工作树不可达）。",
          "evidence": [
            {
              "envelope_sha256": "sha256:0a979439748792d22fad8d8518c51b33c10c0fc34217a0ebeef6140c942524a0",
              "figure_sha256": "sha256:ae1eafc00e6fbe48031de88321a8db18b5a6591895f33bfad44e035e199f5722",
              "figure_bytes": {
                "fig_locator_map.png": {
                  "variant": "fig_locator_map.png",
                  "bytes": 51654,
                  "sha256": "sha256:ae1eafc00e6fbe48031de88321a8db18b5a6591895f33bfad44e035e199f5722",
                  "geometry": {
                    "valid_png": true,
                    "width": 1650,
                    "height": 540
                  }
                }
              }
            }
          ],
          "blocking_for_upstream_package": false
        },
        {
          "finding_id": "F6",
          "severity": "low",
          "scope": "source_record(report_id=427) / risk for downstream wp-427-02/03",
          "statement": "源报告末尾『治理升级』附录把 ①~⑥ 六节全部标为『待补充』，而正文六节实际齐备；上游把该附录语句作为事实 locator（pre-rework-chars）登记，未标注矛盾。对 01（只登记资产）不构成违约，但 02/03 若把附录当成『章节缺失』证据会失真——本审核显式预警。",
          "evidence": [
            {
              "markdown_quote_a": "| ① 案例介绍 | 待补充 |",
              "markdown_quote_b": "## ① 案例介绍",
              "markdown_quote_c": "| ⑥ 误差判定 | 待补充 |",
              "markdown_quote_d": "## ⑥ 误差判定"
            },
            {
              "upstream_locator": "pre-rework-chars",
              "quote": "> 原始长度: 2460 字符。"
            }
          ],
          "blocking_for_upstream_package": false,
          "impact": "下游抽取工序的判据输入污染风险（非 01 工序错误）。"
        }
      ],
      "checks_not_run": [
        "派生工件（3 个）字节存在性与 sha256：生产者工作树不可达 -> unknown（F3）",
        "生产者『同端点对其它记录返回 200/67,305 B』对照：越本单 report_id 边界，未复核",
        "figure 图像内容 vs 正文数字一致性：无 payload，无可校验对象（F1）",
        "asset_manifest.json 与 verification.json 的文件级 sha256：不可从交付信道复算（F4）/不可达"
      ],
      "overstated_claims": [
        "上游把 figures 4/4 不可取回归因于『源记录缺 payload』——本审核复现了 404，但『其它记录 200/67,305 B』这一对照未复核，故『端点非故障』的结论在审核侧仅 partially-supported。"
      ],
      "checks_performed_detail": {
        "source_refetch": {
          "http_status": 200,
          "source_hash_recomputed": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
          "contract_source_hash": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
          "hash_matches_contract": true,
          "chars_recomputed": 2732,
          "contract_chars": 2732,
          "chars_match_contract": true,
          "bytes_utf8": 4067,
          "lines_splitlines": 111,
          "has_crlf": false,
          "record_title": "DIT 衰减各向同性湍流验证诊断报告（m518）",
          "record_scenario_key": "dit_turbulence",
          "record_figures_declared": [
            "spectra_evolution",
            "energy_decay",
            "slope_evolution",
            "cpu_vs_gpu"
          ]
        },
        "envelope_extraction": {
          "json_blocks_found": 1,
          "single_block": true,
          "envelope_sha256": "sha256:bf554c704cb244e613fb7520b6caaeda590e1ab1a46a46c9f6b6506bb3b57dfe",
          "envelope_keys": [
            "claims",
            "outputs",
            "package_id",
            "provenance",
            "report_id",
            "task_type"
          ],
          "envelope_top_level_claims": []
        },
        "provenance": {
          "claimed_source_hash": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
          "recomputed_source_hash": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
          "match": true,
          "source_field": "markdown",
          "source_field_ok": true,
          "report_id_in_envelope": "427",
          "package_id_in_envelope": "wp-427-01",
          "identity_ok": true
        },
        "schema": {
          "schema_path": "schemas/kf_result.v1.schema.json",
          "jsonschema_version": "4.26.0",
          "valid": true,
          "errors": []
        },
        "manifest_source_block": {
          "declared_source_block": {
            "source_hash": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
            "chars": 2732,
            "lines": 111
          },
          "declared_source_asset": {
            "sha256": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
            "bytes": 4067,
            "chars": 2732,
            "lines": 111,
            "has_crlf": false
          },
          "recomputed": {
            "hash": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
            "chars": 2732,
            "bytes": 4067,
            "lines": 111,
            "has_crlf": false
          },
          "source_block_match": true,
          "source_asset_match": true,
          "all_match": true,
          "declared_hash_matches_contract": true,
          "declared_hash_match_flag": true
        },
        "locators": {
          "n_declared": 9,
          "n_independently_confirmed": 9,
          "all_confirmed": true,
          "details": [
            {
              "fact_id": "report-title",
              "declared_line": 1,
              "quote_len": 26,
              "quote_sha256_recomputed": "sha256:c2eaf206281e9af89d7a688ea8b4ac2390f8ffb122a350f263ef0d86a802c764",
              "quote_sha256_declared": "sha256:c2eaf206281e9af89d7a688ea8b4ac2390f8ffb122a350f263ef0d86a802c764",
              "quote_sha256_match": true,
              "in_source_recomputed": true,
              "occurrences_recomputed": 1,
              "occurrences_declared": 1,
              "on_declared_line_recomputed": true,
              "declared_quote_in_source": true,
              "declared_quote_on_line": true,
              "declared_resolved": true,
              "agree": true
            },
            {
              "fact_id": "lattice-model",
              "declared_line": 12,
              "quote_len": 16,
              "quote_sha256_recomputed": "sha256:6bd0d88b3e64950a9bc715411a6787d5cdb08b9696770cfd6f7777707a067ed7",
              "quote_sha256_declared": "sha256:6bd0d88b3e64950a9bc715411a6787d5cdb08b9696770cfd6f7777707a067ed7",
              "quote_sha256_match": true,
              "in_source_recomputed": true,
              "occurrences_recomputed": 1,
              "occurrences_declared": 1,
              "on_declared_line_recomputed": true,
              "declared_quote_in_source": true,
              "declared_quote_on_line": true,
              "declared_resolved": true,
              "agree": true
            },
            {
              "fact_id": "collision-model",
              "declared_line": 13,
              "quote_len": 35,
              "quote_sha256_recomputed": "sha256:9b385f71ef2a97910b01b7cd5d738d234eeea23aaf8e4e9c4f78ca25174cd9a3",
              "quote_sha256_declared": "sha256:9b385f71ef2a97910b01b7cd5d738d234eeea23aaf8e4e9c4f78ca25174cd9a3",
              "quote_sha256_match": true,
              "in_source_recomputed": true,
              "occurrences_recomputed": 1,
              "occurrences_declared": 1,
              "on_declared_line_recomputed": true,
              "declared_quote_in_source": true,
              "declared_quote_on_line": true,
              "declared_resolved": true,
              "agree": true
            },
            {
              "fact_id": "slope-N64",
              "declared_line": 42,
              "quote_len": 47,
              "quote_sha256_recomputed": "sha256:b5ba134312253bb059cb34c1f620775cb88a691a15d7cf2ceb1b269e3991f445",
              "quote_sha256_declared": "sha256:b5ba134312253bb059cb34c1f620775cb88a691a15d7cf2ceb1b269e3991f445",
              "quote_sha256_match": true,
              "in_source_recomputed": true,
              "occurrences_recomputed": 1,
              "occurrences_declared": 1,
              "on_declared_line_recomputed": true,
              "declared_quote_in_source": true,
              "declared_quote_on_line": true,
              "declared_resolved": true,
              "agree": true
            },
            {
              "fact_id": "decay-N128",
              "declared_line": 53,
              "quote_len": 38,
              "quote_sha256_recomputed": "sha256:50b6415b93f162ef31ad5ca6704ee6f9541748d2c319189c2f51c157068a1f15",
              "quote_sha256_declared": "sha256:50b6415b93f162ef31ad5ca6704ee6f9541748d2c319189c2f51c157068a1f15",
              "quote_sha256_match": true,
              "in_source_recomputed": true,
              "occurrences_recomputed": 1,
              "occurrences_declared": 1,
              "on_declared_line_recomputed": true,
              "declared_quote_in_source": true,
              "declared_quote_on_line": true,
              "declared_resolved": true,
              "agree": true
            },
            {
              "fact_id": "cpu-walltime",
              "declared_line": 63,
              "quote_len": 14,
              "quote_sha256_recomputed": "sha256:7e9398dfff74b984c97a5cd6abaaabac46ec3f93b969f905dd59c1032fb4f643",
              "quote_sha256_declared": "sha256:7e9398dfff74b984c97a5cd6abaaabac46ec3f93b969f905dd59c1032fb4f643",
              "quote_sha256_match": true,
              "in_source_recomputed": true,
              "occurrences_recomputed": 1,
              "occurrences_declared": 1,
              "on_declared_line_recomputed": true,
              "declared_quote_in_source": true,
              "declared_quote_on_line": true,
              "declared_resolved": true,
              "agree": true
            },
            {
              "fact_id": "cpu-gpu-bitwise",
              "declared_line": 67,
              "quote_len": 28,
              "quote_sha256_recomputed": "sha256:6b91190ce25ae9808e8876b44b7a10d9c7323f8cdb4f99cd6d57f9339708f5fe",
              "quote_sha256_declared": "sha256:6b91190ce25ae9808e8876b44b7a10d9c7323f8cdb4f99cd6d57f9339708f5fe",
              "quote_sha256_match": true,
              "in_source_recomputed": true,
              "occurrences_recomputed": 1,
              "occurrences_declared": 1,
              "on_declared_line_recomputed": true,
              "declared_quote_in_source": true,
              "declared_quote_on_line": true,
              "declared_resolved": true,
              "agree": true
            },
            {
              "fact_id": "figure-pointer",
              "declared_line": 71,
              "quote_len": 25,
              "quote_sha256_recomputed": "sha256:cc5b8e189b045a8cd029b87724f477e5dc1b1af74a617eb7608181cac90ed048",
              "quote_sha256_declared": "sha256:cc5b8e189b045a8cd029b87724f477e5dc1b1af74a617eb7608181cac90ed048",
              "quote_sha256_match": true,
              "in_source_recomputed": true,
              "occurrences_recomputed": 1,
              "occurrences_declared": 1,
              "on_declared_line_recomputed": true,
              "declared_quote_in_source": true,
              "declared_quote_on_line": true,
              "declared_resolved": true,
              "agree": true
            },
            {
              "fact_id": "pre-rework-chars",
              "declared_line": 99,
              "quote_len": 16,
              "quote_sha256_recomputed": "sha256:40461a6a33870651a2e91491fdb75f4c9b3818eb6880d8ed177a11372fc9ecbd",
              "quote_sha256_declared": "sha256:40461a6a33870651a2e91491fdb75f4c9b3818eb6880d8ed177a11372fc9ecbd",
              "quote_sha256_match": true,
              "in_source_recomputed": true,
              "occurrences_recomputed": 1,
              "occurrences_declared": 1,
              "on_declared_line_recomputed": true,
              "declared_quote_in_source": true,
              "declared_quote_on_line": true,
              "declared_resolved": true,
              "agree": true
            }
          ],
          "min_line": 1,
          "max_line": 99
        },
        "id_integrity": {
          "ids_collected": 8,
          "declared_ids_checked": 8,
          "duplicates_recomputed": [],
          "unique_recomputed": true,
          "declared_unique": true
        },
        "counts": {
          "declared": {
            "source_documents": 1,
            "figures_declared": 4,
            "figures_resolved": 0,
            "figures_total_bytes": 0,
            "locators": 9,
            "locators_resolved": 9,
            "claims": 0,
            "derived_artifacts": 3
          },
          "recomputed": {
            "source_documents": 1,
            "figures_declared": 4,
            "figures_resolved": 0,
            "locators": 9,
            "locators_resolved": 9,
            "claims": 0,
            "derived_artifacts": 3
          },
          "mismatch": {},
          "consistent": true
        },
        "figures": {
          "n_declared_in_record": 4,
          "n_in_manifest": 4,
          "captions_all_verbatim": true,
          "resolvable_reproduced": [
            true,
            true,
            true,
            true
          ],
          "details": [
            {
              "name": "spectra_evolution",
              "caption_verbatim_match": true,
              "record_has_caption": true,
              "endpoint": [
                {
                  "variant": "spectra_evolution",
                  "status": 404,
                  "bytes": 29,
                  "body_head": "{\"detail\":\"figure not found\"}"
                },
                {
                  "variant": "spectra_evolution.png",
                  "status": 404,
                  "bytes": 29,
                  "body_head": "{\"detail\":\"figure not found\"}"
                }
              ],
              "declared_resolvable": false,
              "declared_error": "HTTP 404",
              "reproduced_not_resolvable": true
            },
            {
              "name": "energy_decay",
              "caption_verbatim_match": true,
              "record_has_caption": true,
              "endpoint": [
                {
                  "variant": "energy_decay",
                  "status": 404,
                  "bytes": 29,
                  "body_head": "{\"detail\":\"figure not found\"}"
                },
                {
                  "variant": "energy_decay.png",
                  "status": 404,
                  "bytes": 29,
                  "body_head": "{\"detail\":\"figure not found\"}"
                }
              ],
              "declared_resolvable": false,
              "declared_error": "HTTP 404",
              "reproduced_not_resolvable": true
            },
            {
              "name": "slope_evolution",
              "caption_verbatim_match": true,
              "record_has_caption": true,
              "endpoint": [
                {
                  "variant": "slope_evolution",
                  "status": 404,
                  "bytes": 29,
                  "body_head": "{\"detail\":\"figure not found\"}"
                },
                {
                  "variant": "slope_evolution.png",
                  "status": 404,
                  "bytes": 29,
                  "body_head": "{\"detail\":\"figure not found\"}"
                }
              ],
              "declared_resolvable": false,
              "declared_error": "HTTP 404",
              "reproduced_not_resolvable": true
            },
            {
              "name": "cpu_vs_gpu",
              "caption_verbatim_match": true,
              "record_has_caption": true,
              "endpoint": [
                {
                  "variant": "cpu_vs_gpu",
                  "status": 404,
                  "bytes": 29,
                  "body_head": "{\"detail\":\"figure not found\"}"
                },
                {
                  "variant": "cpu_vs_gpu.png",
                  "status": 404,
                  "bytes": 29,
                  "body_head": "{\"detail\":\"figure not found\"}"
                }
              ],
              "declared_resolvable": false,
              "declared_error": "HTTP 404",
              "reproduced_not_resolvable": true
            }
          ],
          "markdown_claim_about_figures": "见 figures 字段（4 张 PNG 内嵌）。"
        },
        "source_self_contradiction": {
          "appendix_marks_sections_todo": true,
          "body_has_sections": true,
          "quote_appendix": "| ① 案例介绍 | 待补充 |",
          "quote_body": "## ① 案例介绍",
          "contradiction": true
        },
        "no_verified_marking": {
          "marker_hits": [],
          "clean": true
        },
        "claims_empty_legality": {
          "n_claims": 0,
          "has_reason": true,
          "reason_quote_head": "工作包 wp-427-01 的 objective 只有 register_assets=true、classify_r",
          "objective_register_assets_only": true
        },
        "delivery_channel": {
          "result_report_id": "14590",
          "http_status": 200,
          "title": "KF-RESULT wp-427-01",
          "title_ok": true,
          "tags": [
            "kf-wp:wp-427-01",
            "01-asset-registration",
            "report:427",
            "lane:C",
            "draft"
          ],
          "tag_ok": true,
          "single_json_block": true,
          "n_figures_in_channel": 1,
          "envelope_bytes_sha256": "sha256:0a979439748792d22fad8d8518c51b33c10c0fc34217a0ebeef6140c942524a0",
          "figure_bytes": {
            "fig_locator_map.png": {
              "variant": "fig_locator_map.png",
              "bytes": 51654,
              "sha256": "sha256:ae1eafc00e6fbe48031de88321a8db18b5a6591895f33bfad44e035e199f5722",
              "geometry": {
                "valid_png": true,
                "width": 1650,
                "height": 540
              }
            }
          }
        },
        "producer_artifact_hashes": {
          "declared_in_producer_table": {
            "runs/wp-427-01/source_427.md": {
              "declared_bytes": 4067,
              "declared_sha256": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846"
            },
            "runs/wp-427-01/asset_manifest.json": {
              "declared_bytes": 9672,
              "declared_sha256": "sha256:93ade4961e23932351147a76780060770233ca9d57285a4b27d540f0df99f91e"
            },
            "runs/wp-427-01/verification.json": {
              "declared_bytes": 2557,
              "declared_sha256": "sha256:738bff72a2dccfdf0b22538fc7bee2d1e7ddb39f4fbb870824bfff41bf7909e1"
            },
            "runs/wp-427-01/kf_result_envelope.json": {
              "declared_bytes": 11324,
              "declared_sha256": "sha256:0a979439748792d22fad8d8518c51b33c10c0fc34217a0ebeef6140c942524a0"
            },
            "runs/wp-427-01/fig_locator_map.png": {
              "declared_bytes": 51654,
              "declared_sha256": "sha256:ae1eafc00e6fbe48031de88321a8db18b5a6591895f33bfad44e035e199f5722"
            }
          },
          "markdown_hash_recomputed": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
          "manifest_serializations_tried": [
            {
              "indent": null,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:298aabd4a3d56025632400cd42134753dd19a22c5db4f39f7c4c69ef0918f504"
            },
            {
              "indent": null,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:39e94a45e53e39fd112c79b090752ca43625641a522e9d1066cd0fd9bdfaf5b1"
            },
            {
              "indent": null,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:b9460fdf7b72c23be7ef54fef90a610bb22eeddfc256eb50817a4524dbb14520"
            },
            {
              "indent": null,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:c7dffad34fac0c3a7978a25648db188bc21c99a9ecf363fde536b2d6b7d19102"
            },
            {
              "indent": null,
              "sep": [
                ",",
                ": "
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:da71c8a05c87652e06c050f9c8b769925b4cfafd43eebc83087ea34cbd24909c"
            },
            {
              "indent": null,
              "sep": [
                ",",
                ": "
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:4d202d1a5e24e87213b7aa4d9e0497cb88025d3e5648695008aaae037a31f514"
            },
            {
              "indent": null,
              "sep": [
                ",",
                ": "
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:73f5e391d05d3e583e44b060ff794459379d1e00636445ab39af516aca70401d"
            },
            {
              "indent": null,
              "sep": [
                ",",
                ": "
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:dad3b6fa50cedf1f2266f2dbedecaca2eec5c8668cccc2cad9b61bb271685a03"
            },
            {
              "indent": null,
              "sep": [
                ",",
                ":"
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:1a7d5a29cf9a91af60c6860ea281e64a2f706c4820669bebe958b531e3f29cbf"
            },
            {
              "indent": null,
              "sep": [
                ",",
                ":"
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:5cb15eb5a719421f00c2f91dd9677e8f3d9f463ca38f8429aa5c058283267af4"
            },
            {
              "indent": null,
              "sep": [
                ",",
                ":"
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:61716b844569002a2fd0c6e530297596b93848e0f546db5b4e1efd802b5e3c9d"
            },
            {
              "indent": null,
              "sep": [
                ",",
                ":"
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:320947dc443a6ea76a0579e2556ee8eb162ad24e5a956939e08455bf47fb6ad2"
            },
            {
              "indent": null,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:f8daf03d06577f7debd4552cfe64b9891e465957076449a9893c8d8629190197"
            },
            {
              "indent": null,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:b5809f9982e14916df01fc468ad66d8afa448d8048134dc3485c7142c4c23a5b"
            },
            {
              "indent": null,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:e97694ecaf150fc58c107ac19265407bf512351ffa3d2c2a08ca0e8b214125e7"
            },
            {
              "indent": null,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:48cb1c3561cec184b5155c524bae3c04fed658e4fa1db6e283c8dcb41c9efae6"
            },
            {
              "indent": 1,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:00848f462061a5a8bfc99f318261a0985cbb6594982a4a3354d5ad06e58a18d5"
            },
            {
              "indent": 1,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:a8b4bc58a1db634ae9235afd307eaafece933f54dee38e17e8574a5e516296e5"
            },
            {
              "indent": 1,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:146d261ceb520673a99f10929ad2065ed63b6bcfb6491b19d58f6bfb3afc45f4"
            },
            {
              "indent": 1,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:279b3da6cddd90d084787429302dbe3c6ec87734ff723a135be904b03f378bd1"
            },
            {
              "indent": 1,
              "sep": [
                ",",
                ": "
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:56fca9eb2e3dca8b989a5f9f2291e727c6333cc36fa7e7ac56aaf83b980cbb7b"
            },
            {
              "indent": 1,
              "sep": [
                ",",
                ": "
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:4f3678f8ec023064fa6dbd9229f0715a5ecc3b852331ad8e76e04b0fa785c6a1"
            },
            {
              "indent": 1,
              "sep": [
                ",",
                ": "
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:778e4321ddcd913721d91271c8fdb0b89b4266dd489e12d1d69929150961c92f"
            },
            {
              "indent": 1,
              "sep": [
                ",",
                ": "
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:2b538f7c0f86de8d03059e3e830b6fe790dfbf915b04474ee58acfc6982a30d6"
            },
            {
              "indent": 1,
              "sep": [
                ",",
                ":"
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:eef3d40469a06428fbe46bb959c049618ddd4f9aac9714edd8752a91fec5cad8"
            },
            {
              "indent": 1,
              "sep": [
                ",",
                ":"
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:6407189dd39bbf64a60b887e689235446daa651885cc5a0fcb136aaf0567d3a0"
            },
            {
              "indent": 1,
              "sep": [
                ",",
                ":"
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:21ba3b08a334cdbf3c030b28aa6912421ef7ded85241e260ff183cce87029db0"
            },
            {
              "indent": 1,
              "sep": [
                ",",
                ":"
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:c05b4b45894d0c1bd1950cfa793cec3e98cc5eb8d8245d469a1f29b2b4389abc"
            },
            {
              "indent": 1,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:bbad2cefacadae6c01d11a4ae43702d196589a46fae3c3525a1512bf34cdc6d5"
            },
            {
              "indent": 1,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:592040e5061125fb29c3d0306f125d1bcd4f71c2eb6cc55684466a102e35368e"
            },
            {
              "indent": 1,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:94bb5018798a955e77717a52279d6935857f241dd8ef4d62ab7636bfde84feaa"
            },
            {
              "indent": 1,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:4198839073273d7426b6346e6642801dce579b682ab385c276ddf56e04bb1e0e"
            },
            {
              "indent": 2,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:6794e9a7bca22fa4c0bd1eb7d303bcc9a41a030ac2013d332263acd290955a92"
            },
            {
              "indent": 2,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:1f78cf965a806e4090cf04f38af9f643b534afef801989d5eaa5f8f34859dcf2"
            },
            {
              "indent": 2,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:a079af5980bdaae2c956929f21ca3fc38b35d3faf25e638ed7cc5f08677ad0bf"
            },
            {
              "indent": 2,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:945b3f202460c524e298df035d0b1376cff60367769b0d78ce4395c4b276a472"
            },
            {
              "indent": 2,
              "sep": [
                ",",
                ": "
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:a4ec63c0613bc1e6d5bfd44d639998eebf023234a3c2bf1862b667cc34b1c94e"
            },
            {
              "indent": 2,
              "sep": [
                ",",
                ": "
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:331dff436e00df3685f27f2cc0279f1dc9ff7e54cdfdc599afbc86aac415b463"
            },
            {
              "indent": 2,
              "sep": [
                ",",
                ": "
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:93ade4961e23932351147a76780060770233ca9d57285a4b27d540f0df99f91e"
            },
            {
              "indent": 2,
              "sep": [
                ",",
                ": "
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:1c3ba22ba8dbae598c7f4c4da22dfaf8994b8c41678b23f741cf7925426c8f0b"
            },
            {
              "indent": 2,
              "sep": [
                ",",
                ":"
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:8f0dcb3583dccbc7e198ebe26134c0abfc32ad6af8c0752ba0e5869b10ee39f8"
            },
            {
              "indent": 2,
              "sep": [
                ",",
                ":"
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:f867ec12b0aa12ee5c797c5ddfe1069906f26013477a2b411317c07477bb8189"
            },
            {
              "indent": 2,
              "sep": [
                ",",
                ":"
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:16a3c86fb17d319799aa197efa5fe5e91233cb92dc9559a6678a4c6e5f5ca648"
            },
            {
              "indent": 2,
              "sep": [
                ",",
                ":"
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:8ab911263c5fd1b2a5a350c41d44155840b12a1a115c0ebbcfb3482a2942c7fa"
            },
            {
              "indent": 2,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:0c9c2a67b5d58d7670fc1006f24df50969dba75570ae7a16ca274272a736c2db"
            },
            {
              "indent": 2,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:361ec61301dc32a3ddeede7e73f3202816bfdcfbb35182229973c9f029fef1de"
            },
            {
              "indent": 2,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:076c6582db8ceb21c95c0b0bacd4fd722131599744a8bf2b3777d475199611b4"
            },
            {
              "indent": 2,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:2f536113a3351b030befe24ed53c0f9750e1589b0486a1e1e7df3a9991687a5f"
            },
            {
              "indent": 4,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:238db7efe712817b982939c3a6025e629d1897d8ebec642a0eb4bad921e7ec60"
            },
            {
              "indent": 4,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:9a89a43651a0f54b6c1a4e90eda63b8409d09656a56f63454e69e7e36144ad7f"
            },
            {
              "indent": 4,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:cd9029337ec4bc5c56a3a9e5811e30e16e5cf7d9f0675e06124cc27b1b771bd3"
            },
            {
              "indent": 4,
              "sep": [
                ", ",
                ": "
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:2e12fcb7bf342e05d7df0cfc495abe0fec4662ee813489f6c65cc070c0306235"
            },
            {
              "indent": 4,
              "sep": [
                ",",
                ": "
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:726b40551f77e0359df27e67810b506d7f315050b51d4318ba32558d53b0a504"
            },
            {
              "indent": 4,
              "sep": [
                ",",
                ": "
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:ee7bd38eeaba5949ad3ccbd983dc39f1bef8d187f00d4df5b6110b97c014565e"
            },
            {
              "indent": 4,
              "sep": [
                ",",
                ": "
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:d9f6286e27194449333187d408c6265516e39e67f635e736e85098111a73f882"
            },
            {
              "indent": 4,
              "sep": [
                ",",
                ": "
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:a60ba273d93cafa947e73370fba56043763681783d77822a824f9adba1f8b3cf"
            },
            {
              "indent": 4,
              "sep": [
                ",",
                ":"
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:fc3778e9b98fd1541d466f7eb61fd32ba712d3166468d1df0a801c65cc9f09d1"
            },
            {
              "indent": 4,
              "sep": [
                ",",
                ":"
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:26b57343864c835d742926f496bb0447801694441b9168be0e089a888b177ba6"
            },
            {
              "indent": 4,
              "sep": [
                ",",
                ":"
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:56d79c897c4af181382221fe52dca5b7d47461a5b3cd8d0f0208f76e55799f89"
            },
            {
              "indent": 4,
              "sep": [
                ",",
                ":"
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:142ef943a7c6d07a240b88f6c0330d046f235b72fed0fc81898aa5f34704c6d7"
            },
            {
              "indent": 4,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "",
              "sort": false,
              "sha256": "sha256:006b8e9d94afee1ee16acd2c03b0e18e376d52673c2f6547dc8aa22458ff6445"
            },
            {
              "indent": 4,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "",
              "sort": true,
              "sha256": "sha256:b500abd9906402d410b00d73e88a85ab74606577c2ba1010d274361bc4f6cab1"
            },
            {
              "indent": 4,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "\n",
              "sort": false,
              "sha256": "sha256:4e903e617dd56254d577f253c7848bd3bb4bac8786eb3b8e2db3b3949d63820c"
            },
            {
              "indent": 4,
              "sep": [
                ", ",
                ":"
              ],
              "tail": "\n",
              "sort": true,
              "sha256": "sha256:bf632a7fbfa215040edae0ddc6eb01306ec3628bbf9d695f03b8d5f4dd8b134b"
            }
          ],
          "envelope_sha256_declared": "sha256:0a979439748792d22fad8d8518c51b33c10c0fc34217a0ebeef6140c942524a0",
          "envelope_sha256_reproduced": "sha256:0a979439748792d22fad8d8518c51b33c10c0fc34217a0ebeef6140c942524a0",
          "envelope_reproduced": true,
          "figure_sha256_declared": "sha256:ae1eafc00e6fbe48031de88321a8db18b5a6591895f33bfad44e035e199f5722",
          "figure_sha256_reproduced": "sha256:ae1eafc00e6fbe48031de88321a8db18b5a6591895f33bfad44e035e199f5722",
          "figure_bytes_reproduced": 51654,
          "figure_reproduced": true,
          "source_copy_sha256_declared": "sha256:09c640623dff50ac9def329238d10890cfb9a30172a1aa48d6541879b2b65846",
          "source_copy_equals_source_markdown": true,
          "manifest_sha256_declared": "sha256:93ade4961e23932351147a76780060770233ca9d57285a4b27d540f0df99f91e",
          "manifest_reproducible_from_envelope": true,
          "manifest_reproduction_recipe": {
            "indent": 2,
            "sep": [
              ",",
              ": "
            ],
            "tail": "\n",
            "sort": false,
            "sha256": "sha256:93ade4961e23932351147a76780060770233ca9d57285a4b27d540f0df99f91e"
          },
          "n_serializations_tried": 64,
          "bytes_reproduced": {
            "source_427.md": {
              "declared": 4067,
              "recomputed_markdown_bytes": 4067
            },
            "kf_result_envelope.json": {
              "declared": 11324,
              "recomputed_json_block_bytes": 11324
            },
            "asset_manifest.json": {
              "declared": 9672,
              "recomputed": 9672
            }
          },
          "verified_declared_artifacts": [
            "asset_manifest.json",
            "fig_locator_map.png",
            "kf_result_envelope.json",
            "source_427.md"
          ],
          "unverified_declared_artifacts": [
            "runs/wp-427-01/verification.json"
          ],
          "verification_json": {
            "declared_bytes": 2557,
            "declared_sha256": "sha256:738bff72a2dccfdf0b22538fc7bee2d1e7ddb39f4fbb870824bfff41bf7909e1"
          }
        },
        "not_independently_checkable": {
          "derived_artifacts_on_producer_worktree": [
            "runs/wp-427-01/source_427.md",
            "scripts/kf_wp42701_register_assets.py",
            "runs/wp-427-01/fig_locator_map.png"
          ],
          "note": "生产者工作树内文件（本地副本/verification.json）不在审核方可达范围；其存在性与 sha256 未复核 -> 记 unknown/not_run，不计 pass。",
          "control_claim_by_producer": "同端点对其它记录返回 200/67,305 B —— 越本单 report_id 边界，未复核"
        }
      },
      "disposition": "approve",
      "remediation": []
    }
  },
  "claims": []
}
```
