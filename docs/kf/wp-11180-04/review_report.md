# KF-RESULT wp-11180-04

- package_id: `wp-11180-04` ｜ task_type: `04-independent-review` ｜ report_id: `11180` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: in-review
- source: `tensor://reports/11180`（field=`markdown`）, chars=490, bytes=670, sha256=`sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292`
- 审核对象：`wp-11180-01`（01-asset-registration，producer=agent/m15692）
- 审核方法：adversarial-review（未使用生产者解释作依据；未把任何结论标为 verified）
- **处置：needs-fix**（对 01 的语义忠实度 = pass；对报告 11180 的证据包 = needs-fix）

## ① 本工序做了什么

对 report_id=11180（`EEXI Attained 闭合链路精度传递验证 (P74-N02)`，scenario=`green_shipping_eexi_chain`）执行 **04-independent-review**：

1. 独立复算源报告字节哈希与体量：`sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292`，490 字符 / 670 字节 UTF-8，与契约 `source_hash` 逐字节一致。
2. 把报告里 11 处被审核的表述用 `str.find` 逐字定位（char_span + 行号），11/11 全部命中且唯一——审核引用零手抄。
3. 复核上游 wp-11180-01 的 4 个资产定位：按声明的 char_span 重切原文，4/4 字节精确、引文唯一（4/4 唯一）；用 `os.path.exists` 复核其 `referenced_unresolved` 判定，4/4 复现。
4. 用报告自己的三个误差判定其内部算术：最大 12.1%、均值 6.7%、<3% 者 1/3。`均 <15%` 自洽，但**全文没有 <3% 的判定**。
5. 对「WITHHELD → REAL」做三条独立复算尝试，全部不可达（端点 404 / 能力台账缺失 / 验证工件不可解），记为 fail 而非「错」。
6. 产出 18 项检查（pass 9 / fail 8 / not_run 1）与 10 项分级发现（blocking 3 项）。

## ② 怎么做的（步骤/工具/关键设置）

| 步骤 | 工具/方法 | 关键设置 |
| --- | --- | --- |
| 取原文 | `GET /api/v1/tensor/reports/11180`（Bearer 登录换 token）+ 字节快照 `docs/kf/wp-11180-04/source/report_11180.md` | 不做换行归一化；`sha256(markdown.encode('utf-8'))` |
| 零手抄绑定 | `str.find` + `str.count` + 切片重切 | 引用未命中即判 fail；同时记录 char_span 与行号 |
| 上游复核 | 解析 `docs/report_wp11180_01.md` 中唯一 json 块；重切每个 char_span；`os.path.exists` 复核分辨率 | 上游叙述文字只作被审对象，不作证据 |
| schema 严格度 | 读 `schemas/kf_result.v1.schema.json` 的 `required` / `additionalProperties`，手写等价校验（不引入 jsonschema 依赖） | 逐层检查顶层 / provenance / outputs 的额外键 |
| 数值复算 | 从已定位引文用正则抽数（`(\d+\.\d+)%`），不重抄 | 只复算报告自洽性，不假设任何外部基准 |
| 独立复算尝试 | 端点探测（`calculations/eexi`、`green-shipping/eexi/attained`、`openapi.json`）+ 能力台账读取 | 404 / 文件缺失一律记 fail(不可达)，不记「假」 |
| 出图 | matplotlib（Agg） | 误差 vs 15%/3% 双阈值；敏感度闭合缺口 |

**独立性**：审核者 agent/m19782 与生产者 agent/m15692 不同身份；被审上下文 = 490 字符原文 + 01 的机器输出。局限：同平台同模型家族（身份级独立而非模型级）；未执行 ship-performance-platform 代码。

## ③ 产出物清单

| 文件 | 要点 |
| --- | --- |
| `docs/kf/wp-11180-04/review_report.json` | 审核报告本体（18 项检查 + 10 项发现 + 处置），同时是提交信封 `outputs['review_report.json']` |
| `docs/kf/wp-11180-04/review_checks.json` | 原始检查数据（哈希/引文绑定/char_span 重切/像素外的全部数值） |
| `docs/kf/wp-11180-04/source/report_11180.md` | 源报告字节快照（670 字节，哈希与契约一致） |
| `docs/kf/wp-11180-04/fig_review_checks.png` | 结果图：三船误差 vs 15%/3% 阈值 + 敏感度闭合缺口 |
| `scripts/kf_wp11180_04_checks.py` | 一键检查器（`--live` 会重新 git-free 拉取原文并比对快照） |
| `scripts/kf_wp11180_04_emit.py` | 从检查结果程序化注入生成 review_report.json / .md（零手抄） |
| `tests/test_wp11180_04_review.py` | pytest：哈希、引文子串、char_span 重切、单 json 块、schema 严格度、处置一致性 |
| `docs/kf/wp-11180-04/review_report.md` | 本文件 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

| claim/字段 | 原文引文（逐字） | 定位 |
| --- | --- | --- |
| goal | `将 EEXI attained 能力从 WITHHELD(99.9%误差) 推进到 REAL(<15%误差)` | char 34–88 / line 4 |
| method | `建立端到端同源链路：Holtrop 阻力 → BEMT 推进 → EEXI attained` | char 96–142 / line 7 |
| errors_line | `- 三船对标误差: 12.1% / 7.0% / 1.0% (均 <15%)` | char 150–188 / line 10 |
| same_source | `- 链路同源: grep 验证 4 处调用` | char 189–210 / line 11 |
| sensitivity | `- 敏感度分析: V_ref 主导 (57.1%)` | char 211–236 / line 12 |
| degenerate | `- 退化一致性: 验证通过` | char 237–250 / line 13 |
| asset_impl | `backend/api/green_shipping.py::_gn_eexi_from_physics()` | char 264–318 / line 16 |
| asset_test | `backend/tests/test_eexi_chain_p74n02.py` | char 325–364 / line 17 |
| asset_json | `artifacts/eexi_verification.json` | char 371–403 / line 18 |
| asset_doc | `docs/eexi_verification_report_p74n02.md` | char 410–449 / line 19 |
| conclusion | `EEXI attained 能力: WITHHELD → REAL` | char 457–490 / line 22 |

关键复算数字：三船误差 = [12.1, 7.0, 1.0]%（来自 `三船对标误差` 行，非重抄）；最大 12.1%、均值 6.7%；敏感度 `V_ref` 贡献 57.1%，未分解残差 42.9%。

## ⑤ 注意点与局限

- **处置的两面性**：wp-11180-01 本身是合格的资产登记（定位可逐字节复现、不可解状态如实披露，F-09），needs-fix 针对的是**报告证据包**——两者不可混为一谈。
- **fail ≠ 假**：F-02/F-10 是「不可复算」，不是「已证伪」；审核者没有权限也没有证据否定作者做过的工作。
- **F-07 一处严格模式违规**：上游信封在顶层多出 `claims` 键，`additionalProperties: false` 下会被严格校验器拒收；这不是语义错误。
- **报告过薄**：490 字符无法承载一次端到端精度传递验证；F-01/F-03/F-05/F-06 的根因主要在此（源报告质量问题，不是 01 的缺陷）。
- **未做的事**：未运行 ship-performance-platform 的任何代码/测试，未读取 `artifacts/eexi_verification.json`（不存在），未取得平台能力台账。
- **不可外推**：本审核只对 report_id=11180 有效，不涉及其它报告或其它 EEXI 证据。

### 检查明细

| id | check | status |
| --- | --- | --- |
| C1 | source_hash_recompute | pass |
| C2 | source_size_and_shape | pass |
| C3 | live_api_equals_snapshot | pass |
| C4 | quote_binding_zero_handcopy | pass |
| C5 | upstream_package_present | pass |
| C6 | upstream_asset_spans_reproduce | pass |
| C7 | upstream_resolution_claim_reproduced | pass |
| C8 | upstream_envelope_schema_strict | fail |
| C9 | headline_numbers_internal_arithmetic | pass |
| C10 | explicit_3pct_error_judgement | fail |
| C11 | per_ship_traceability | fail |
| C12 | sensitivity_decomposition | fail |
| C13 | same_source_chain_evidence | fail |
| C14 | degenerate_limit_definition | fail |
| C15 | prior_state_basis | not_run |
| C16 | grade_claim_independently_recomputable | fail |
| C17 | source_report_structure_vs_platform_discipline | fail |
| C18 | reviewer_marks_nothing_verified | pass |

### 发现清单（severity 排序）

| id | severity | blocking | 标题 |
| --- | --- | --- | --- |
| F-01 | high | 是 | 三个对标误差无任何可复算结构：无船名/主尺度/参考值/绝对 attained 值 |
| F-02 | high | 是 | 「WITHHELD → REAL」是平台门的输出，不是报告可自证的结论，且本审核者无法独立复算 |
| F-03 | medium | 是 | 缺平台报告纪律第 6 要素：没有显式回答「是否 <3%」 |
| F-04 | medium | 否 | 敏感度只报一个因子 57.1%，剩余 42.9% 未分解、方法未写 |
| F-05 | medium | 否 | 「链路同源: grep 验证 4 处调用」不是同源一致性证明 |
| F-06 | medium | 否 | 「退化一致性: 验证通过」不可反驳：退化极限与容差都未定义 |
| F-07 | low | 否 | 上游 wp-11180-01 信封违反 additionalProperties:false：顶层 claims + provenance 三个自有键 |
| F-08 | low | 否 | 源报告结构不满足平台 6 要素（无参数表、无图、无注意点/局限段） |
| F-09 | info | 否 | 正面发现：wp-11180-01 的资产定位可逐字节复现，且对不可解事实如实披露 |
| F-10 | info | 否 | 被超越的旧状态（WITHHELD 99.9%）同样无出处 |

blocking 说明：F-01（核心误差无法复算）、F-02（等级结论不可独立复算）、F-03（缺 <3% 显式判定）阻断放行；F-04…F-07 为需修正但不阻断语义忠实度的项。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结果 | 说明 |
| --- | --- | --- |
| `valid_json` | ✅ | review_report.json 与 review_checks.json 均 json.load 往返通过；提交块由同一对象序列化 |
| `schema_pass` | ✅ | 信封对照 `schemas/kf_result.v1.schema.json`：required 4 项齐备、`contract_version="1.0"`、provenance 无额外键、outputs 键合法；由 pytest 断言 |
| `reviewer_independent` | ✅ | distinct-identity（m19782 vs m15692），未使用生产者解释作依据 |
| `upstream_packages_completed` | ✅（带 note） | wp-11180-01 存在、输出可解析、4 个 char_span 字节精确；另发现 1 处信封严格模式违规（F-07），不影响其语义忠实度 |
| `review_prompt_not_copied_from_producer` | ✅ | 检查项由契约 YAML + 报告原文自行推导；未复制 01 的自检表 |
| `reviewer_context_excludes_producer_explanation` | ✅ | 01 的叙述文字仅作被审对象；证据表所有引文均来自报告 markdown |
| `do_not_mark_claims_as_verified` | ✅ | `claims_marked_verified = 0`；处置只到 needs-fix，等级由平台门计算 |
| honest 声明 | ✅ | fail 项 8 个照实列出（含 C8/C10-C14/C16/C17），not_run 1 项（C15）如实标注，无粉饰 |

**是否放行：否（needs-fix）**——F-01/F-02/F-03 三项 blocking 未消除。问题定位与修复建议见每项 `recommendation`；本次不代改上游产物（边界约束）。

## 复跑命令

```bash
cd /root/tp-agent/work/m19782
python3 scripts/kf_wp11180_04_checks.py --live && python3 scripts/kf_wp11180_04_emit.py && python3 -m pytest tests/test_wp11180_04_review.py -q
```

`--live` 会重新登录平台拉取 report 11180 并与 `source/report_11180.md` 逐字节比对（不一致即告警）。

```json
{
  "package_id": "wp-11180-04",
  "task_type": "04-independent-review",
  "contract_version": "1.0",
  "report_id": "11180",
  "provenance": {
    "source_uri": "tensor://reports/11180",
    "source_field": "markdown",
    "source_hash": "sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292",
    "source_hash_matches": true,
    "title": "EEXI Attained 闭合链路精度传递验证 (P74-N02)",
    "scenario_key": "green_shipping_eexi_chain",
    "chars": 490
  },
  "outputs": {
    "review_report.json": {
      "review_report_version": "1.0",
      "package_id": "wp-11180-04",
      "task_type": "04-independent-review",
      "report_id": "11180",
      "reviewer_role": "red-team-reviewer",
      "reviewed_package": {
        "package_id": "wp-11180-01",
        "task_type": "01-asset-registration",
        "artifact": "docs/report_wp11180_01.md",
        "source_hash": "sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292",
        "assets_registered": 4,
        "asset_spans_byte_exact": 4,
        "schema_deviations": [
          {
            "kind": "additional_property",
            "keys": [
              "claims"
            ]
          },
          {
            "kind": "additional_property",
            "path": "provenance",
            "keys": [
              "emitted_at",
              "notes",
              "producer"
            ]
          }
        ]
      },
      "provenance": {
        "source_uri": "tensor://reports/11180",
        "source_field": "markdown",
        "source_hash": "sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292",
        "source_hash_matches": true,
        "title": "EEXI Attained 闭合链路精度传递验证 (P74-N02)",
        "scenario_key": "green_shipping_eexi_chain",
        "chars": 490,
        "utf8_bytes": 670,
        "snapshot": "docs/kf/wp-11180-04/source/report_11180.md"
      },
      "decision": {
        "disposition": "needs-fix",
        "ledger_decision": "needs-fix",
        "scope": "对上游工序 wp-11180-01：语义忠实度 pass（资产定位逐字节可复现、不可解状态如实披露，仅一处信封 schema 违规）。对报告 11180 的证据包：needs-fix（核心误差不可复算、缺 <3% 判定、等级变更不可独立复算）。",
        "rationale": "18 项检查中 pass 9 / fail 8 / not_run 1；3 项 blocking 发现（F-01, F-02, F-03）。无一份可复算的验证工件，且「REAL」这一等级结论在平台门之外不可达，故不放行、也不判假。",
        "claims_marked_verified": 0,
        "verification_owner": "platform-gate"
      },
      "scope": {
        "in_scope": [
          "report 11180 markdown 的字节哈希、体量、结构与全部定量/定性声明",
          "上游 wp-11180-01 的资产登记输出（char_span、引文唯一性、分辨率判定、信封 schema 严格度）",
          "把报告声明与原文逐字绑定的可复现性（零手抄）",
          "对等级结论的独立复算尝试（端点/台账/工件三条路径）"
        ],
        "out_of_scope": [
          "ship-performance-platform 源码与实际 EEXI 实现（不在本工作树，端点 404）",
          "Holtrop / BEMT 的绝对精度（报告未提供任何参考值或数据集）",
          "平台门对 wp-11180-01 的最终 schema_pass 结论（本审核只复算，不代替下判）",
          "知识抽取与综合（工序 03/05）"
        ]
      },
      "independence": {
        "reviewer": "agent/m19782 (TensorKnowledge) · package wp-11180-04 · red-team-reviewer",
        "producer": "agent/m15692 (TensorKnowledge) · package wp-11180-01",
        "basis": "distinct-identity",
        "limitations": [
          "审核者与被审包来自同一平台/同一模型家族：独立性是身份级与方法级的，不是模型级的",
          "被审上下文只有 490 字符原文 + 01 的机器输出；报告本身过薄，某些声明（如 99.9%）只能标证据不足而非判错",
          "平台能力台账不可达、EEXI 端点 404，等级结论的复算只能记为 fail(不可达)，不能记为「错」",
          "本审核未执行任何 ship-performance-platform 代码，也未运行其测试"
        ]
      },
      "context_isolation": {
        "evidence_basis": [
          "report 11180 markdown（live API 抓取 + 字节快照 docs/kf/wp-11180-04/source/report_11180.md）",
          "docs/report_wp11180_01.md 内的机器输出（asset_manifest / kf_result 信封）"
        ],
        "objects_under_test_not_evidence": [
          "docs/report_wp11180_01.md 的叙述文字（§1-§6 自检），仅作被审对象，未作为任何声明成立的依据"
        ],
        "producer_explanation_used_as_support": false,
        "review_prompt_source": "工作包契约 YAML + 报告原文；未复制生产者自检/叙述"
      },
      "checks": [
        {
          "id": "C1",
          "name": "source_hash_recompute",
          "status": "pass",
          "method": "sha256 over the UTF-8 bytes of the markdown, no newline normalisation",
          "detail": {
            "computed": "sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292",
            "contract": "sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292",
            "equal": true
          },
          "evidence": []
        },
        {
          "id": "C2",
          "name": "source_size_and_shape",
          "status": "pass",
          "method": "recomputed char/byte/line counts and the H1 title",
          "detail": {
            "characters": 490,
            "utf8_bytes": 670,
            "lines": 22,
            "h1": "# EEXI Attained 闭合链路精度传递验证",
            "contract_chars": 490,
            "title_in_h1": true
          },
          "evidence": []
        },
        {
          "id": "C3",
          "name": "live_api_equals_snapshot",
          "status": "pass",
          "method": "GET /tensor/reports/11180 -> sha256(markdown) vs the pinned snapshot",
          "detail": {
            "live": "sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292",
            "snapshot": "sha256:9adfdac400ff0e205a17c20a761625acca0acf0e55f9ff477bf2c1c5c8bf3292",
            "equal": true,
            "source_url": "http://127.0.0.1:8010/api/v1/tensor/reports/11180"
          },
          "evidence": []
        },
        {
          "id": "C4",
          "name": "quote_binding_zero_handcopy",
          "status": "pass",
          "method": "every quote used by the review is located by str.find in the source bytes",
          "detail": {
            "quotes": 11,
            "found": 11,
            "all_unique": true
          },
          "evidence": [
            {
              "quote": "将 EEXI attained 能力从 WITHHELD(99.9%误差) 推进到 REAL(<15%误差)",
              "char_span": [
                34,
                88
              ],
              "line": 4
            },
            {
              "quote": "建立端到端同源链路：Holtrop 阻力 → BEMT 推进 → EEXI attained",
              "char_span": [
                96,
                142
              ],
              "line": 7
            },
            {
              "quote": "- 三船对标误差: 12.1% / 7.0% / 1.0% (均 <15%)",
              "char_span": [
                150,
                188
              ],
              "line": 10
            },
            {
              "quote": "- 链路同源: grep 验证 4 处调用",
              "char_span": [
                189,
                210
              ],
              "line": 11
            },
            {
              "quote": "- 敏感度分析: V_ref 主导 (57.1%)",
              "char_span": [
                211,
                236
              ],
              "line": 12
            },
            {
              "quote": "- 退化一致性: 验证通过",
              "char_span": [
                237,
                250
              ],
              "line": 13
            },
            {
              "quote": "backend/api/green_shipping.py::_gn_eexi_from_physics()",
              "char_span": [
                264,
                318
              ],
              "line": 16
            },
            {
              "quote": "backend/tests/test_eexi_chain_p74n02.py",
              "char_span": [
                325,
                364
              ],
              "line": 17
            },
            {
              "quote": "artifacts/eexi_verification.json",
              "char_span": [
                371,
                403
              ],
              "line": 18
            },
            {
              "quote": "docs/eexi_verification_report_p74n02.md",
              "char_span": [
                410,
                449
              ],
              "line": 19
            },
            {
              "quote": "EEXI attained 能力: WITHHELD → REAL",
              "char_span": [
                457,
                490
              ],
              "line": 22
            }
          ]
        },
        {
          "id": "C5",
          "name": "upstream_package_present",
          "status": "pass",
          "method": "locate wp-11180-01's submitted envelope; require exactly one json block",
          "detail": {
            "doc": "docs/report_wp11180_01.md",
            "json_blocks": 1,
            "package_id": "wp-11180-01",
            "task_type": "01-asset-registration",
            "report_id": "11180",
            "declared_assets": 4
          },
          "evidence": []
        },
        {
          "id": "C6",
          "name": "upstream_asset_spans_reproduce",
          "status": "pass",
          "method": "slice the source markdown at each declared char_span and compare byte-for-byte",
          "detail": {
            "assets": 4,
            "byte_exact": 4,
            "unique": 4
          },
          "evidence": [
            {
              "asset_id": "A01",
              "declared_span": [
                264,
                318
              ],
              "recomputed": "backend/api/green_shipping.py::_gn_eexi_from_physics()",
              "byte_exact": true,
              "unique": true,
              "resolution": "referenced_unresolved",
              "resolution_reproduced": true
            },
            {
              "asset_id": "A02",
              "declared_span": [
                325,
                364
              ],
              "recomputed": "backend/tests/test_eexi_chain_p74n02.py",
              "byte_exact": true,
              "unique": true,
              "resolution": "referenced_unresolved",
              "resolution_reproduced": true
            },
            {
              "asset_id": "A03",
              "declared_span": [
                371,
                403
              ],
              "recomputed": "artifacts/eexi_verification.json",
              "byte_exact": true,
              "unique": true,
              "resolution": "referenced_unresolved",
              "resolution_reproduced": true
            },
            {
              "asset_id": "A04",
              "declared_span": [
                410,
                449
              ],
              "recomputed": "docs/eexi_verification_report_p74n02.md",
              "byte_exact": true,
              "unique": true,
              "resolution": "referenced_unresolved",
              "resolution_reproduced": true
            }
          ]
        },
        {
          "id": "C7",
          "name": "upstream_resolution_claim_reproduced",
          "status": "pass",
          "method": "os.path.exists() for every quoted asset path inside this worktree",
          "detail": {
            "declared": "referenced_unresolved",
            "reproduced_unresolved": 4,
            "assets": 4,
            "consequence": "no upstream artifact is reachable to re-derive the reported errors"
          },
          "evidence": [
            {
              "asset_id": "A01",
              "path_quoted": "backend/api/green_shipping.py::_gn_eexi_from_physics()",
              "exists_in_worktree": false
            },
            {
              "asset_id": "A02",
              "path_quoted": "backend/tests/test_eexi_chain_p74n02.py",
              "exists_in_worktree": false
            },
            {
              "asset_id": "A03",
              "path_quoted": "artifacts/eexi_verification.json",
              "exists_in_worktree": false
            },
            {
              "asset_id": "A04",
              "path_quoted": "docs/eexi_verification_report_p74n02.md",
              "exists_in_worktree": false
            }
          ]
        },
        {
          "id": "C8",
          "name": "upstream_envelope_schema_strict",
          "status": "fail",
          "method": "constraints of schemas/kf_result.v1.schema.json applied to the submitted envelope",
          "detail": {
            "deviations": [
              {
                "kind": "additional_property",
                "keys": [
                  "claims"
                ]
              },
              {
                "kind": "additional_property",
                "path": "provenance",
                "keys": [
                  "emitted_at",
                  "notes",
                  "producer"
                ]
              }
            ]
          },
          "evidence": []
        },
        {
          "id": "C9",
          "name": "headline_numbers_internal_arithmetic",
          "status": "pass",
          "method": "parse the three errors out of the located quote; test the report's own '均 <15%'",
          "detail": {
            "errors_pct": [
              12.1,
              7.0,
              1.0
            ],
            "max": 12.1,
            "mean": 6.7,
            "claim_all_below_15": true,
            "all_below_3": false,
            "n_below_3": 1
          },
          "evidence": []
        },
        {
          "id": "C10",
          "name": "explicit_3pct_error_judgement",
          "status": "fail",
          "method": "substring scan for an explicit <3% verdict (platform report discipline element 6)",
          "detail": {
            "'3%' in markdown": false,
            "thresholds_stated": [
              "<15%",
              "<15%"
            ]
          },
          "evidence": []
        },
        {
          "id": "C11",
          "name": "per_ship_traceability",
          "status": "fail",
          "method": "scan for per-ship geometry / absolute EEXI / reference-value fields needed to recompute a % error",
          "detail": {
            "fields_present": [],
            "fields_missing": [
              "Cb",
              "L/B",
              "B/T",
              "gCO2",
              "MCR",
              "SFC",
              "capacity",
              "reference",
              "对标船名"
            ],
            "absolute_eexi_value_present": false,
            "reference_value_present": false
          },
          "evidence": []
        },
        {
          "id": "C12",
          "name": "sensitivity_decomposition",
          "status": "fail",
          "method": "count independently reported sensitivity contributions; require a closed decomposition",
          "detail": {
            "contributions_reported": [
              "57.1"
            ],
            "sum_pct": 57.1,
            "residual_undecomposed_pct": 42.9,
            "method_stated": false
          },
          "evidence": []
        },
        {
          "id": "C13",
          "name": "same_source_chain_evidence",
          "status": "fail",
          "method": "look for file:line call sites / numeric equality tolerance behind the 'grep 4 calls' claim",
          "detail": {
            "claim": "- 链路同源: grep 验证 4 处调用",
            "file_line_locators": [],
            "numeric_equality_tolerance": false,
            "call_sites_enumerated": 0
          },
          "evidence": []
        },
        {
          "id": "C14",
          "name": "degenerate_limit_definition",
          "status": "fail",
          "method": "require a stated degenerate limit and tolerance behind '退化一致性: 验证通过'",
          "detail": {
            "claim": "- 退化一致性: 验证通过",
            "limit_defined": false,
            "tolerance_stated": false
          },
          "evidence": []
        },
        {
          "id": "C15",
          "name": "prior_state_basis",
          "status": "not_run",
          "method": "look for the reference behind 'WITHHELD(99.9%误差)'",
          "detail": {
            "claim": "将 EEXI attained 能力从 WITHHELD(99.9%误差) 推进到 REAL(<15%误差)",
            "reference_or_dataset_in_report": false,
            "note": "report 11180 states the prior 99.9% figure without any reference value; not re-derivable from 490 chars"
          },
          "evidence": []
        },
        {
          "id": "C16",
          "name": "grade_claim_independently_recomputable",
          "status": "fail",
          "method": "attempt independent reproduction: platform capability ledger + EEXI endpoints + the quoted verification artifact",
          "detail": {
            "capability_ledger": "not reachable from this worktree (/root/ship-performance-platform-incoming/.../capabilities.json missing)",
            "eexi_endpoints_probed": [
              "calculations/eexi -> 404",
              "green-shipping/eexi/attained -> 404",
              "openapi.json -> 404"
            ],
            "verification_artifact_reachable": false,
            "verdict": "the WITHHELD->REAL grade cannot be recomputed by this reviewer"
          },
          "evidence": []
        },
        {
          "id": "C17",
          "name": "source_report_structure_vs_platform_discipline",
          "status": "fail",
          "method": "section-header inventory vs the platform's 6-element report discipline",
          "detail": {
            "headers": [
              "EEXI Attained 闭合链路精度传递验证",
              "目标",
              "方法",
              "结果",
              "产物",
              "结论"
            ],
            "element2_method": true,
            "element3_results": true,
            "element4_figures": false,
            "element5_caveats": false,
            "element6_error_verdict": false
          },
          "evidence": []
        },
        {
          "id": "C18",
          "name": "reviewer_marks_nothing_verified",
          "status": "pass",
          "method": "assert the review output never asserts verification (platform gate owns it)",
          "detail": {
            "reviewer_role": "red-team-reviewer",
            "claims_marked_verified": 0,
            "note": "constraint do_not_mark_claims_as_verified honoured by construction"
          },
          "evidence": []
        }
      ],
      "findings": [
        {
          "id": "F-01",
          "severity": "high",
          "blocking": true,
          "title": "三个对标误差无任何可复算结构：无船名/主尺度/参考值/绝对 attained 值",
          "detail": "报告只给出 `- 三船对标误差: 12.1% / 7.0% / 1.0% (均 <15%)`。按平台证据标准（几何必须先验证 Cb/L/B、零手抄、误差须能逐字定位到基准），要复算一个百分比误差至少需要：船名或编号、L/B/T/Cb、绝对 attained EEXI（gCO2/t·nm）、以及所用参考值的出处。这四类字段在 490 字符的原文中一个都没有（C11 fields_missing 全为空缺；`gCO2` 未出现）。三个数中最大值 12.1% 已接近 15% 判废线，因此这条缺口不是形式问题：上游 01 登记的 4 个资产全部`referenced_unresolved`（C7：4/4 在本工作树不存在），任何第三方（含本审核者）都无法重算这三个数。",
          "evidence": [
            {
              "quote": "- 三船对标误差: 12.1% / 7.0% / 1.0% (均 <15%)",
              "where": "## 结果 (char 150-188, line 10)"
            },
            {
              "quote": "artifacts/eexi_verification.json",
              "where": "## 产物 (char 371-403)，worktree 内不存在"
            }
          ],
          "recommendation": "报告侧补一张三船参数表（船名/L/B/T/Cb/V_ref/参考值来源/绝对 attained）并让 artifacts/eexi_verification.json 可解析；下游 03/05 在此之前不得把 12.1/7.0/1.0 提升为知识主张。",
          "affected_scope": "report 11180 的核心定量结论；工序 03/05 的下游引用"
        },
        {
          "id": "F-02",
          "severity": "high",
          "blocking": true,
          "title": "「WITHHELD → REAL」是平台门的输出，不是报告可自证的结论，且本审核者无法独立复算",
          "detail": "报告结论行把能力等级变更写成既成事实。本次独立复算三条路都不通：① EEXI 端点探测 `calculations/eexi`、`green-shipping/eexi/attained`、`openapi.json` 全部 404；② 平台能力台账不可达（capabilities.json 文件缺失）；③ 所引验证工件不在工作树。按工作包约束 `do_not_mark_claims_as_verified`，本审核不给该结论任何 verified 标记，也不把它降级为假——它只是**不可复算**（C16 fail）。",
          "evidence": [
            {
              "quote": "EEXI attained 能力: WITHHELD → REAL",
              "where": "## 结论 (char 457-490)"
            },
            {
              "quote": "将 EEXI attained 能力从 WITHHELD(99.9%误差) 推进到 REAL(<15%误差)",
              "where": "## 目标 (char 34-88)"
            }
          ],
          "recommendation": "把结论改写为「提交平台门复算」的候选声明；修复端点可达性或附上可解析的验证工件，再谈等级变更。",
          "affected_scope": "能力证据分级台账；green_shipping_eexi_chain 场景"
        },
        {
          "id": "F-03",
          "severity": "medium",
          "blocking": true,
          "title": "缺平台报告纪律第 6 要素：没有显式回答「是否 <3%」",
          "detail": "全文出现的阈值只有 `均 <15%`（C10：`3%` 子串不存在）。按平台 2026-10-29 报告令，关键量须逐项给出 vs 基准误差并显式回答是否 <3%。用报告自己的三个数判断：仅 1/3 船 <3%，最大 12.1%、均值 6.7%——即「<15% 的 REAL 门槛」与「<3% 的可发表门槛」在这份报告里被混为一谈，读者无法区分二者。",
          "evidence": [
            {
              "quote": "- 三船对标误差: 12.1% / 7.0% / 1.0% (均 <15%)",
              "where": "## 结果 唯一带阈值的一句"
            },
            {
              "quote": "将 EEXI attained 能力从 WITHHELD(99.9%误差) 推进到 REAL(<15%误差)",
              "where": "## 目标：唯一出现 15% 判据的位置"
            }
          ],
          "recommendation": "补 ⑥误差判定段：逐船列出误差 + 显式写「是否 <3%」，并说明 12.1% 这艘船的偏差来源。",
          "affected_scope": "报告可发表性判定"
        },
        {
          "id": "F-04",
          "severity": "medium",
          "blocking": false,
          "title": "敏感度只报一个因子 57.1%，剩余 42.9% 未分解、方法未写",
          "detail": "`- 敏感度分析: V_ref 主导 (57.1%)` 是全文唯一的敏感度信息。57.1% 单独的数值无法判断是单变量摄动（OAT）还是方差分解（Sobol），摄动步长未知；其余 42.9% 落在哪些参数上没有交代，因此「V_ref 主导」这句只能算观察，不能算结论。它同时暗示：EEXI ∝ 1/V_ref 的情形下，链路误差很可能由输入 V_ref 的取值而非算法精度主导——这会改变「REAL」的含义，值得作者正面回应。",
          "evidence": [
            {
              "quote": "- 敏感度分析: V_ref 主导 (57.1%)",
              "where": "## 结果 (line 12)"
            }
          ],
          "recommendation": "给出参数表 + 摄动区间 + 完整归一化贡献（合计 100%）+ 方法名（OAT 或方差分解）。",
          "affected_scope": "精度传递结论的可解释性"
        },
        {
          "id": "F-05",
          "severity": "medium",
          "blocking": false,
          "title": "「链路同源: grep 验证 4 处调用」不是同源一致性证明",
          "detail": "调用点计数只能证明调用存在，不能证明四条链路用的是同一套输入与同一版公式。C13 显示：原文没有任何 `file.py:line` 定位，也没有数值一致性容差（如 1e-9/相对偏差 ≤ x%）。所谓「同源」可被两种常见缺陷伪造：调用同名函数但传不同单位/不同参考状态；或同一函数被测试桩替换。",
          "evidence": [
            {
              "quote": "- 链路同源: grep 验证 4 处调用",
              "where": "## 结果 (line 11)"
            }
          ],
          "recommendation": "贴出 4 处调用点清单（file:line）+ 端到端数值一致性断言及其容差，最好引一个测试名。",
          "affected_scope": "「同源链路」这一方法论卖点"
        },
        {
          "id": "F-06",
          "severity": "medium",
          "blocking": false,
          "title": "「退化一致性: 验证通过」不可反驳：退化极限与容差都未定义",
          "detail": "C14 未在原文找到任何退化极限定义（如 J→0 / n→0 / V→0 时 BEMT 退化为哪个解析式）与容差。「验证通过」是不可反驳的表述：任何实现都能宣称自己通过了一个未定义的检验。这不是说验证没做，而是报告层面无法区分「做过」与「写了一句」。",
          "evidence": [
            {
              "quote": "- 退化一致性: 验证通过",
              "where": "## 结果 (line 13)"
            }
          ],
          "recommendation": "写明退化极限的解析参考式 + 触发参数 + 通过容差 + 实测偏差值。",
          "affected_scope": "BEMT 推进段的可信度"
        },
        {
          "id": "F-07",
          "severity": "low",
          "blocking": false,
          "title": "上游 wp-11180-01 信封违反 additionalProperties:false：顶层 claims + provenance 三个自有键",
          "detail": "`schemas/kf_result.v1.schema.json` 对顶层与 `provenance` 都声明 `additionalProperties: false`，`claims` 只允许作为 `outputs.claims.json`（工序 03）。C8 复算出的偏差为 `[{\"kind\": \"additional_property\", \"keys\": [\"claims\"]}, {\"kind\": \"additional_property\", \"path\": \"provenance\", \"keys\": [\"emitted_at\", \"notes\", \"producer\"]}]`：即顶层多出 claims，provenance 多出 producer / emitted_at / notes 三个自有键。这不影响 01 的**语义**忠实度（见 F-09），但严格校验器会拒收该信封；平台门是否放行无法从本工作树观测，本审核不代其下判。",
          "evidence": [
            {
              "quote": "schemas/kf_result.v1.schema.json -> properties.outputs.properties.claims.json",
              "where": "契约 schema 文件"
            }
          ],
          "recommendation": "把顶层 claims 移入 outputs（或删除），重发 01 信封。",
          "affected_scope": "对方工作包的信封 schema_pass 项"
        },
        {
          "id": "F-08",
          "severity": "low",
          "blocking": false,
          "title": "源报告结构不满足平台 6 要素（无参数表、无图、无注意点/局限段）",
          "detail": "C17 的 header 清单只有「目标/方法/结果/产物/结论」五段：无案例介绍与参数表、无图、无注意点与局限、无逐项误差判定。490 字符（670 字节）的体量也低于能承载一次精度传递验证所需的信息量。这属于源报告质量问题，不是 01 工序的缺陷；但它是 F-01/F-03 的根因。",
          "evidence": [
            {
              "quote": "EEXI Attained 闭合链路精度传递验证",
              "where": "H1 标题"
            }
          ],
          "recommendation": "报告侧按平台 6 要素重写（本次不代改上游产物）。",
          "affected_scope": "报告可发表性"
        },
        {
          "id": "F-09",
          "severity": "info",
          "blocking": false,
          "title": "正面发现：wp-11180-01 的资产定位可逐字节复现，且对不可解事实如实披露",
          "detail": "独立重切 4 个 char_span：4/4 字节精确命中、4/4 引文唯一；`os.path.exists` 复核 4/4 确为不可解。即 01 没有编造资产、没有把未知说成已解，只是把不可解状态如实登记——这一点是产线应有的行为，不应因为下游证据链不足被追责。",
          "evidence": [
            {
              "quote": "backend/api/green_shipping.py::_gn_eexi_from_physics()",
              "where": "A01 char 264-318"
            },
            {
              "quote": "backend/tests/test_eexi_chain_p74n02.py",
              "where": "A02 char 325-364"
            },
            {
              "quote": "artifacts/eexi_verification.json",
              "where": "A03 char 371-403"
            },
            {
              "quote": "docs/eexi_verification_report_p74n02.md",
              "where": "A04 char 410-449"
            }
          ],
          "recommendation": "无需修改；下游 03/05 沿用该不可解标记即可。",
          "affected_scope": "工序 01 交付质量"
        },
        {
          "id": "F-10",
          "severity": "info",
          "blocking": false,
          "title": "被超越的旧状态（WITHHELD 99.9%）同样无出处",
          "detail": "C15 not_run：原文只用一句话交代旧状态，无参考值、无数据集、无失败记录。因此「从 99.9% 降到 12.1%」这一进步叙事在本审核中既不能证实也不能证伪，只能标为证据不足。",
          "evidence": [
            {
              "quote": "将 EEXI attained 能力从 WITHHELD(99.9%误差) 推进到 REAL(<15%误差)",
              "where": "## 目标"
            }
          ],
          "recommendation": "若保留该对比，需给出 99.9% 的复现路径与基准。",
          "affected_scope": "改进幅度声明的可信度"
        }
      ],
      "counts": {
        "pass": 9,
        "fail": 8,
        "not_run": 1,
        "findings": 10,
        "blocking_findings": 3,
        "severity": {
          "high": 2,
          "medium": 4,
          "low": 2,
          "info": 2
        }
      },
      "acceptance_selfcheck": {
        "valid_json": "ok — review_report.json 经 json.load 往返；review_checks.json 同",
        "schema_pass": "ok — 提交信封（package_id/task_type/report_id/provenance/outputs）逐条对照 schemas/kf_result.v1.schema.json 的 required/pattern/additionalProperties",
        "reviewer_independent": "ok — distinct-identity（agent/m19782 vs agent/m15692），且未使用生产者解释作依据",
        "upstream_packages_completed": "ok-with-note — wwp-11180-01 存在且输出可解析（4 资产 / 4 个 char_span 字节精确）；另发现 1 处严格模式违规（F-07，非阻断语义忠实度）"
      },
      "checks_not_run": [
        "C15 旧状态 99.9% 的基准（原文无参考值，无法复算）",
        "EEXI 端点 / 能力台账复算（calculations/eexi、green-shipping/eexi/attained、openapi.json 均 404；capabilities.json 缺失）",
        "ship-performance-platform 单测与 Holtrop/BEMT 内核（仓库不在本工作树）",
        "artifacts/eexi_verification.json 内容审计（文件不存在，01 已如实标 referenced_unresolved）"
      ],
      "repro_cmd": "python3 scripts/kf_wp11180_04_checks.py --live && python3 scripts/kf_wp11180_04_emit.py && python3 -m pytest tests/test_wp11180_04_review.py -q",
      "artifacts": {
        "checks_raw": "docs/kf/wp-11180-04/review_checks.json",
        "figure": "docs/kf/wp-11180-04/fig_review_checks.png",
        "source_snapshot": "docs/kf/wp-11180-04/source/report_11180.md",
        "tests": "tests/test_wp11180_04_review.py"
      },
      "generated_at": "2026-11-14T03:52:53Z"
    },
    "review_events.json": [
      {
        "event": "review_started",
        "package_id": "wp-11180-04",
        "reviewed_package": "wp-11180-01",
        "at": "2026-11-14T03:52:53Z",
        "basis": "source bytes + upstream machine output only"
      },
      {
        "event": "checks_completed",
        "at": "2026-11-14T03:52:53Z",
        "counts": {
          "pass": 9,
          "fail": 8,
          "not_run": 1,
          "findings": 10,
          "blocking_findings": 3,
          "severity": {
            "high": 2,
            "medium": 4,
            "low": 2,
            "info": 2
          }
        },
        "checks": [
          {
            "id": "C1",
            "status": "pass"
          },
          {
            "id": "C2",
            "status": "pass"
          },
          {
            "id": "C3",
            "status": "pass"
          },
          {
            "id": "C4",
            "status": "pass"
          },
          {
            "id": "C5",
            "status": "pass"
          },
          {
            "id": "C6",
            "status": "pass"
          },
          {
            "id": "C7",
            "status": "pass"
          },
          {
            "id": "C8",
            "status": "fail"
          },
          {
            "id": "C9",
            "status": "pass"
          },
          {
            "id": "C10",
            "status": "fail"
          },
          {
            "id": "C11",
            "status": "fail"
          },
          {
            "id": "C12",
            "status": "fail"
          },
          {
            "id": "C13",
            "status": "fail"
          },
          {
            "id": "C14",
            "status": "fail"
          },
          {
            "id": "C15",
            "status": "not_run"
          },
          {
            "id": "C16",
            "status": "fail"
          },
          {
            "id": "C17",
            "status": "fail"
          },
          {
            "id": "C18",
            "status": "pass"
          }
        ]
      },
      {
        "event": "decision",
        "at": "2026-11-14T03:52:53Z",
        "disposition": "needs-fix",
        "blocking_findings": [
          "F-01",
          "F-02",
          "F-03"
        ],
        "claims_marked_verified": 0
      }
    ]
  }
}
```
