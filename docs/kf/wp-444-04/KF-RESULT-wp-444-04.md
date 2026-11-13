# KF-RESULT wp-444-04

## ① 本工序做了什么

对上游工作包 **wp-444-01（01-asset-registration，result report 14623）** 做独立审核：
不看生产者解释，只用 `report_id=444` 的 markdown 与 14623 的 json 信封，逐条**独立重算**
其结构登记与证据定位声明，产出 `review_report.json`（判定 + 逐条 finding + 未跑项 + 越界观察）。
本单不抽取、不改上游产物、不写验证轴。

判定：**needs-fix（decision=request-changes）**——实质登记全部可独立复算并一致（无编造迹象），
但有 3 项中危缺陷需返修：①产出物键名不合契约 ②证据表 3 条压缩改写伪引文 ③清单细目不可跨会话解析。

## ② 怎么做的（步骤/工具/关键设置）

1. `python3 work/verify_wp444_01.py`：拉 `tensor://reports/444` 与 `14623`，独立计算
   sha256(markdown)、章节数（`^## `）、表格数（表头+分隔行起算的连续块）、figures 条数、
   反引号路径型代码引用数；对 ④ 表 9 条引文做**精确子串**判定；对行号定位做复算。
   离线复跑用 `--md/--upstream` 喂固定夹具，结果逐字节一致（同一 `measured` 块）。
2. `jsonschema`（Draft202012Validator）+ `schemas/kf_result.v1.schema.json` 校验上游信封：0 错。
3. 读 `tk_work_packages`（`runuser -u postgres psql` 只读）确认上游完成度：
   `wp-444-01 status=review, gates_ok=true, result_report_id=14623`。
4. `python3 work/observe_source_numbers.py` 把源报告 ⑥ 表的"基准"按它自己命名的公式重算
   （越界观察，不改判定）。
5. `python3 work/build_review_report.py` 生成 `review_report.json` + `review_events.json`
   （append-only，状态机复用 `scripts/ke_state_machine.py`）。
6. `python3 -m pytest tests/test_wp444_04_review.py -q` → **12 passed**。

## ③ 产出物清单

| 文件 | 要点 |
|------|------|
| `docs/kf/wp-444-04/review_report.json` | 判定 needs-fix；4 findings（F1/F2/F3 中危，F4 低）；14 项 checks_performed；4 项 checks_not_run；越界观察 1 组 |
| `docs/kf/wp-444-04/review_events.json` | 1 条 append-only 事件 `request-changes`（findings=[F1..F4] + 3 条返修条件） |
| `docs/kf/wp-444-04/KF-RESULT-wp-444-04.md` | 本文件（唯一 json 代码块=结果信封） |
| `artifacts/wp-444-04/verification.json` | 12 项机器检查原始值（哈希/计数/引文/路径可解析性） |
| `artifacts/wp-444-04/out_of_scope_observations.json` | 源 ⑥ 表 vs 解析公式的程序化重算 |
| `artifacts/wp-444-04/review_checks.png` | 双面板图：声明 vs 重算计数；⑥ 表基准 vs 公式 |
| `artifacts/wp-444-04/{source_markdown.md, upstream_report_14623.md, upstream_envelope_wp-444-01.json}` | 零依赖复跑夹具（源 markdown 哈希=契约哈希） |
| `work/verify_wp444_01.py`, `work/build_review_report.py`, `work/observe_source_numbers.py`, `work/make_figure.py`, `tests/test_wp444_04_review.py` | 可执行审核与回归 |

## ④ 证据定位表（claim → 原文引文片段，逐字）

| # | 引文片段（取自 report 444 markdown） | 定位结果 |
|---|--------------------------------------|----------|
| 1 | `AlphaEvolve-Style Verifier/Generator Separation: Held-Out Question Bank & Independent Verification for Ship Resistance` | 不在 markdown 中（非逐字） |
| 2 | `见 figures 附件：四面板图展示 ITTC-1957 摩擦线、平板边界层、逐公式通过率、逐题偏差` | 逐字命中 line [45] |
| 3 | `本报告经治理升级，补充六要素章节（背景/方法/结果/图件/注意点/误差判定）` | 逐字命中 line [69] |
| 4 | `ITTC-1957 / Blasius / P-S / Holtrop` | 不在 markdown 中（非逐字） |
| 5 | `ITTC-1957 5/5 / Blasius 3/3 / P-S 4/4 / HM 3/3 / 合计 15/15` | 不在 markdown 中（非逐字） |
| 6 | `ITTC-1957 Cf (Re=1e8) 0.0% / Blasius Cf 0.0% / P-S Cf 0.0% / HM 1+k 0.0%` | 不在 markdown 中（非逐字） |
| 7 | `pytest（12 项单元测试）` | 逐字命中 line [30] |
| 8 | `{name, caption}` | 不在 markdown 中（非逐字） |
| 9 | `png_base64` | 不在 markdown 中（非逐字） |

结构性证据（非 markdown 字段，单列不混算逐字）：`title` 字段=报告标题；
`figures`=[{name:"verifier_pilot_results", caption:"..."}]，无 `png_base64`。

## ⑤ 注意点与局限

- **本判定不授予 L3**：`verification_status` 由平台门计算，本单未写、也未把任何 claim 标 verified；
  `axes_untouched.claims_marked_verified=false`。
- **G5 结构性盲区**：上游 `claims=[]` → 门只检查了 **0** 个 locator，④ 表引文从未被机检；
  本评审用精确子串补检，9 条中 6 条不逐字（含 3 条压缩改写）。
- **生产者在同一记录的 prose 摘要不可剥离**：API 取回 KF-RESULT 报告时 markdown 自带生产者正文；
  本评审的判定只绑定源 markdown 重算与信封 JSON，未把该散文当证据（已在 independence.limitations 声明）。
- **未跑项**：`asset_manifest.json` 文件内容（路径不可解析）、figures 的 PNG 字节、
  报告"pytest（12 项单元测试）"的真伪（无附件线索）——一律记 `insufficient`，不当作通过。
- **域数值正确性不属本工序**：⑥ 表自洽不等于精度；下面的越界观察仅供 03/05 使用。

## ⑥ 误差判定（关键量 vs 基准，逐项）

| 关键量 | 基准 | 实际 | 偏差 | <3%? |
|--------|------|------|------|------|
| source_hash（markdown 字节） | 契约 `4068f88…57af2` | 独立重算 `4068f881c6722010…` | 0.000% | ✓ YES |
| sections_count | 7（声明） | 7（重算） | 0.0% | ✓ YES |
| tables_count | 4（声明） | 4（重算） | 0.0% | ✓ YES |
| figures_count | 1（声明） | 1（重算） | 0.0% | ✓ YES |
| code_references_count | 0（声明） | 0（重算） | 0.0% | ✓ YES |
| ④ 引文逐字率 | 9/9 逐字（零手抄要求） | 3/9 | **6/9 不逐字** | ✗ NO |

越界观察（源报告 ⑥ 表基准 vs 其自述解析式，程序化重算，**不进入本工序判定**）：

| 行 | 表中基准 | 公式值 | 相对偏差 | <15%? |
|----|----------|--------|----------|-------|
| ITTC-1957 Cf (Re=1e8) | 0.00217 | 0.002083 | +4.16% | 是 |
| Blasius Cf (Re_L=1e6) | 0.001328 | 0.001328 | +0.00% | 是 |
| P-S Cf (Re_L=1e8) | 0.002012 | 0.002128 | -5.47% | 是 |
| HM 1+k (Cb=0.6) | 1.0547 | nan | 报告未给出该简化式的解析形式，无法在评审上下文内重算 | 不可判 |

结论（**honest-FAIL 于流程一致性、PASS 于实质登记**）：上游登记的计数与哈希 100% 可复算、
偏差 0.000% < 3%；但"零手抄"一项 **3% 标准不适用**（它是计数型判据），实测 3/9 逐字，
故判 needs-fix。**未**宣称任何科学结论 verified。

**repro_cmd**：
```bash
cd $(git rev-parse --show-toplevel) && python3 work/verify_wp444_01.py   --md artifacts/wp-444-04/source_markdown.md   --upstream artifacts/wp-444-04/upstream_report_14623.md && python3 work/observe_source_numbers.py && python3 work/make_figure.py && python3 work/build_review_report.py && python3 -m pytest tests/test_wp444_04_review.py -q
```

```json
{
  "package_id": "wp-444-04",
  "task_type": "04-independent-review",
  "report_id": "444",
  "provenance": {
    "source_uri": "tensor://reports/444",
    "source_field": "markdown",
    "source_hash": "sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2",
    "producer": "m15795",
    "emitted_at": "2026-11-12T02:40:46Z",
    "notes": "独立审核；上下文=报告 markdown + wp-444-01 信封（result report 14623）；未读生产者解释性散文作证据；未写 verification_status"
  },
  "outputs": {
    "review_report.json": {
      "review_id": "rvw:wp-444-04:wp-444-01",
      "package_id": "wp-444-04",
      "package_id_reviewed": "wp-444-01",
      "task_type_reviewed": "01-asset-registration",
      "report_id": "444",
      "source_hash_recomputed": "sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2",
      "reviewer": {
        "id": "m15795",
        "reviewer_type": "agent",
        "role": "red-team-reviewer"
      },
      "policy_version": "ke-review-v0.1",
      "independence": {
        "reviewer_identity": "m15795",
        "producer_identity_hint": "m15508",
        "independent": true,
        "basis": "distinct-identity：评审会话 m15795 ≠ 生产者会话 m15508；未读生产者工作树，未参与 wp-444-01 生产",
        "limitations": [
          "评审上下文取自平台同一条 KF-RESULT 报告记录（markdown 含生产者正文摘要），无法在 API 层面只取 json 代码块；判定只绑定源 markdown 重算与信封 JSON，未使用生产者散文自述作证据",
          "生产 prompt 未在评审上下文出现，故 M4 未被本评审触发也未复验"
        ]
      },
      "scope": {
        "in_scope": [
          "wp-444-01 信封字段与契约一致性",
          "登记计数与源文本可复算性",
          "证据表引文逐字性",
          "产出物可解析性",
          "S15/S9 类自证材料检查"
        ],
        "out_of_scope": [
          "报告物理数值正确性（下游 03/05 与平台验证单）",
          "附件字节内容",
          "L3 验证级别授予"
        ]
      },
      "checks_performed": [
        {
          "id": "H1",
          "what": "source_hash 独立重算",
          "result": {
            "recomputed": "sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2",
            "declared": "sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2",
            "contract": "sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2",
            "pass": true
          }
        },
        {
          "id": "H2",
          "what": "sections_count 独立计数",
          "result": {
            "declared": 7,
            "recomputed": 7,
            "pass": true
          }
        },
        {
          "id": "H3",
          "what": "tables_count 独立计数",
          "result": {
            "declared": 4,
            "recomputed": 4,
            "pass": true
          }
        },
        {
          "id": "H4",
          "what": "figures_count 独立计数",
          "result": {
            "declared": 1,
            "recomputed": 1,
            "pass": true
          }
        },
        {
          "id": "H5",
          "what": "code_references_count 独立计数",
          "result": {
            "declared": 0,
            "recomputed": 0,
            "pass": true
          }
        },
        {
          "id": "H6",
          "what": "零 claim 合法性（01 不做抽取）",
          "result": {
            "declared": 0,
            "envelope_has_claims_key": false,
            "pass": true,
            "note": "01-asset-registration 不抽取；零 claim 合法"
          }
        },
        {
          "id": "H7",
          "what": "生产者未自带审核材料（S15）",
          "result": {
            "outputs_keys": [
              "asset_manifest"
            ],
            "forbidden_present": [],
            "pass": true
          }
        },
        {
          "id": "H8",
          "what": "信封未预支验证轴",
          "result": {
            "banned_tokens_found": [],
            "pass": true,
            "note": "provenance.source_hash_verified 是自算哈希自检（可程序化复现），不属 claim 验证"
          }
        },
        {
          "id": "H9",
          "what": "④ 证据表引文逐字性（9 条）",
          "result": {
            "non_verbatim": [
              "AlphaEvolve-Style Verifier/Generator Separation: Held-Out Question Bank & Independent Verification for Ship Resistance",
              "ITTC-1957 / Blasius / P-S / Holtrop",
              "ITTC-1957 5/5 / Blasius 3/3 / P-S 4/4 / HM 3/3 / 合计 15/15",
              "ITTC-1957 Cf (Re=1e8) 0.0% / Blasius Cf 0.0% / P-S Cf 0.0% / HM 1+k 0.0%",
              "{name, caption}",
              "png_base64"
            ]
          }
        },
        {
          "id": "H10",
          "what": "④ 行号定位复算",
          "result": [
            {
              "label": "参数表 4 行",
              "claimed": "lines 11-17",
              "anchor": "| 公式 | 输入 | 输出 | 参考值来源 |",
              "actual_lines": [
                12
              ],
              "anchor_present": true
            },
            {
              "label": "计算结果表 5 行",
              "claimed": "lines 35-41",
              "anchor": "| 题目类别 | 题数 | 通过 | 最大偏差 | 容差 |",
              "actual_lines": [
                35
              ],
              "anchor_present": true
            },
            {
              "label": "误差判定表 4 行",
              "claimed": "lines 55-60",
              "anchor": "| 关键量 | 基准 | 实际 | 偏差 | <3%? |",
              "actual_lines": [
                55
              ],
              "anchor_present": true
            },
            {
              "label": "图引用",
              "claimed": "line 45",
              "anchor": "见 figures 附件",
              "actual_lines": [
                45
              ],
              "anchor_present": true
            },
            {
              "label": "治理升级",
              "claimed": "line 69",
              "anchor": "本报告经治理升级",
              "actual_lines": [
                69
              ],
              "anchor_present": true
            }
          ]
        },
        {
          "id": "H11",
          "what": "产出物路径可解析性",
          "result": {
            "declared_path": "artifacts/wp-444-01/asset_manifest.json",
            "exists_in_review_worktree": false,
            "pass": false,
            "note": "路径相对生产者工作树；评审上下文中不可解析 → 清单细目不可独立核对"
          }
        },
        {
          "id": "H12",
          "what": "信封清单粒度",
          "result": {
            "envelope_asset_manifest_keys": [
              "claims_count",
              "code_references_count",
              "figures_count",
              "path",
              "sections_count",
              "source_hash_verified",
              "tables_count",
              "unresolved_assets_count"
            ],
            "has_sections_list": false,
            "has_tables_list": false,
            "has_figures_list": false,
            "pass": false
          }
        },
        {
          "id": "H13",
          "what": "信封过 schemas/kf_result.v1.schema.json",
          "result": {
            "pass": true,
            "validator": "jsonschema Draft202012Validator",
            "errors": "NONE"
          }
        },
        {
          "id": "H14",
          "what": "上游包完成度（acceptance.upstream_packages_completed）",
          "result": {
            "package": "wp-444-01",
            "factory_status": "review",
            "gates_ok": true,
            "result_report_id": 14623,
            "source": "tk_work_packages 行读取（runuser -u postgres psql，只读）"
          }
        }
      ],
      "checks_not_run": [
        {
          "id": "N1",
          "what": "报告 ⑥ 表 4 个数值的科学正确性",
          "why": "属 03/05 与平台验证单职责；01 工序不产出 claim，评审不越级给 L3",
          "evidence": "本报告 out_of_scope_observations 已给出程序化重算，供下游参考，不进入本判定"
        },
        {
          "id": "N2",
          "what": "figures 的 PNG 是否存在/内容是否正确",
          "why": "平台记录 figures 仅 name+caption，无 png_base64；评审上下文无附件字节",
          "evidence": "figures 字段实测：[\"verifier_pilot_results\"]"
        },
        {
          "id": "N3",
          "what": "生产者的 asset_manifest.json 文件内容",
          "why": "路径不可解析（F3），无法读取；只能从源文本反推计数",
          "evidence": "H11 exists_in_review_worktree=false"
        },
        {
          "id": "N4",
          "what": "命题『pytest 12 项单元测试』的真实性",
          "why": "报告未给测试文件名/路径，工作树内无线索，判定 insufficient",
          "evidence": "H9 中 \"pytest\\uff0812 \\u9879\\u5355\\u5143\\u6d4b\\u8bd5\\uff09\" 在源文本 line 30 逐字存在，但无附件可查"
        }
      ],
      "findings": [
        {
          "id": "F1",
          "severity": "medium",
          "category": "contract-conformance",
          "blocking_for_automation": true,
          "claim": "envelope.outputs 键名与契约声明的产物文件名不一致：契约 output={'asset_manifest.json': true}（tk_work_packages.contract），信封里是 outputs.asset_manifest",
          "evidence": {
            "declared_contract_output_key": "asset_manifest.json",
            "envelope_outputs_keys": [
              "asset_manifest"
            ],
            "sibling_package_14891_outputs_keys": [
              "asset_manifest.json"
            ]
          },
          "reproduction": "curl -s $TENSOR_API_BASE/tensor/reports/14623 → json 代码块 → json.loads(...)['outputs'].keys(); 对照 runuser -u postgres -- psql -d tensorplatform -tA -c \"select contract->'output' from tk_work_packages where package_id='wp-444-01'\"",
          "impact": "按声明文件名取产物的下游消费者（02 工序）会 KeyError；程序化门 g2_schema_pass 只校验信封 schema，不校验 outputs 键名与契约一致，故未被拦。"
        },
        {
          "id": "F2",
          "severity": "medium",
          "category": "quote-fidelity",
          "blocking_for_automation": false,
          "claim": "④ 证据定位表 9 条『原文引文片段』中 6 条不是 source_field=markdown 的逐字子串；其中 3 条是把表格内容压缩改写成的伪引文",
          "evidence": {
            "non_verbatim_count": 6,
            "checked_count": 9,
            "non_verbatim_quotes": [
              "AlphaEvolve-Style Verifier/Generator Separation: Held-Out Question Bank & Independent Verification for Ship Resistance",
              "ITTC-1957 / Blasius / P-S / Holtrop",
              "ITTC-1957 5/5 / Blasius 3/3 / P-S 4/4 / HM 3/3 / 合计 15/15",
              "ITTC-1957 Cf (Re=1e8) 0.0% / Blasius Cf 0.0% / P-S Cf 0.0% / HM 1+k 0.0%",
              "{name, caption}",
              "png_base64"
            ],
            "paraphrased_not_field_labelled": [
              "ITTC-1957 / Blasius / P-S / Holtrop",
              "ITTC-1957 5/5 / Blasius 3/3 / P-S 4/4 / HM 3/3 / 合计 15/15",
              "ITTC-1957 Cf (Re=1e8) 0.0% / Blasius Cf 0.0% / P-S Cf 0.0% / HM 1+k 0.0%"
            ],
            "machine_gate_locators_checked": 0,
            "note": "G5 只检查 claims 的 locator；本包 claims=[] → checked=0，证据表引文无人机检，属结构性盲区"
          },
          "reproduction": "python3 work/verify_wp444_01.py → checks.H9_locator_verbatim （q in source_markdown 的精确子串判定）",
          "impact": "零手抄纪律在本包未被机器执行；下游 03/05 若信任该表的逐字性会继承改写过的措辞。表内数字本身与源表一致，故不构成数字错误。"
        },
        {
          "id": "F3",
          "severity": "medium",
          "category": "artifact-resolvability",
          "blocking_for_automation": true,
          "claim": "产出物路径 artifacts/wp-444-01/asset_manifest.json 在评审上下文不可解析，且信封 outputs.asset_manifest 只携带汇总计数（无 sections/tables/figures 列表），故清单细目无法独立核对",
          "evidence": {
            "declared_path": "artifacts/wp-444-01/asset_manifest.json",
            "exists_in_review_worktree": false,
            "envelope_asset_manifest_keys": [
              "claims_count",
              "code_references_count",
              "figures_count",
              "path",
              "sections_count",
              "source_hash_verified",
              "tables_count",
              "unresolved_assets_count"
            ],
            "producer_repro_asserts_absent_keys": "len(manifest['sections'])==7 / len(manifest['tables'])==4"
          },
          "reproduction": "python3 work/verify_wp444_01.py → checks.H11/H12；ls artifacts/wp-444-01/asset_manifest.json（当前工作树不存在）",
          "impact": "登记表声称的 sections/tables/figures 条目名只在生产者工作树里，跨会话/跨机器不可审计；本评审只能从源文本反推计数（已反推，全部一致）。"
        },
        {
          "id": "F4",
          "severity": "low",
          "category": "provenance-self-check",
          "blocking_for_automation": false,
          "claim": "provenance.source_hash_verified=true 由生产者自算写入，且 §② 的 retrieved_at 为整十分钟值（2026-11-12T00:50:00Z），不可独立复核时点",
          "evidence": {
            "source_hash_verified": true,
            "retrieved_at": "2026-11-12T00:50:00Z",
            "recomputed_hash": "sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2"
          },
          "reproduction": "见 checks.H1（哈希本身已独立重算并一致）",
          "impact": "无 claim，故不触犯 do_not_mark_claims_as_verified；建议把哈希自检结果留在 gate 侧而非信封，避免与验证轴混淆。"
        }
      ],
      "out_of_scope_observations": [
        {
          "scope": "out-of-scope observation for downstream 03/05; does not change the wp-444-01 verdict",
          "why": "报告 ⑥ 表把『基准』与『实际』填成同一数值，所以 0.0% 是自洽而非精度；下游若把 0.0% 当精度证据会过强。",
          "rows": [
            {
              "row": "ITTC-1957 Cf (Re=1e8)",
              "table_baseline": 0.00217,
              "table_actual": 0.00217,
              "table_deviation": "0.0%",
              "formula": "ITTC-1957 Cf",
              "reynolds": 100000000.0,
              "formula_value": 0.0020833333333333333,
              "rel_error_vs_formula_pct": 4.16,
              "within_15pct_of_formula": true
            },
            {
              "row": "Blasius Cf (Re_L=1e6)",
              "table_baseline": 0.001328,
              "table_actual": 0.001328,
              "table_deviation": "0.0%",
              "formula": "Blasius Cf",
              "reynolds": 1000000.0,
              "formula_value": 0.001328,
              "rel_error_vs_formula_pct": 0.0,
              "within_15pct_of_formula": true
            },
            {
              "row": "P-S Cf (Re_L=1e8)",
              "table_baseline": 0.002012,
              "table_actual": 0.002012,
              "table_deviation": "0.0%",
              "formula": "P-S Cf",
              "reynolds": 100000000.0,
              "formula_value": 0.002128331291412549,
              "rel_error_vs_formula_pct": -5.466,
              "within_15pct_of_formula": true
            },
            {
              "row": "HM 1+k (Cb=0.6)",
              "table_baseline": 1.0547,
              "table_actual": 1.0547,
              "table_deviation": "0.0%",
              "formula": null,
              "note": "报告未给出该简化式的解析形式，无法在评审上下文内重算"
            }
          ],
          "method": "artifacts/wp-444-04/source_markdown.md 解析 ⑥ 表 → 逐个按报告自述的公式重算 → 相对偏差"
        }
      ],
      "verdict": {
        "decision": "request-changes",
        "verdict": "needs-fix",
        "semantic_fidelity": "passed-for-substance",
        "reason": "实质登记全部可独立复算并一致（哈希、7 章节/4 表/1 图/0 代码引用、claims=[]），无编造迹象；但存在 3 项中危缺陷（产出物键名不合契约、证据表 3 条改写伪引文、清单细目不可跨会话解析），需返修后重审。",
        "accepted": [
          "source_hash 与契约/独立重算三方一致：sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2",
          "sections/tables/figures/code_references 计数与独立计数一致：7/4/1/0",
          "claims=[] 且信封无 claims 键，符合 01 工序 no_forced_claim_generation",
          "未自带 review_events/verification_ticket/review_report（S15 通过）"
        ],
        "remediation": [
          "F1: outputs 键名改为契约声明的 asset_manifest.json（或回改契约声明，二者择一并留痕）",
          "F2: ④ 表 3 条压缩改写引文改为逐字切片；title/figures 字段类证据单列并注明取自 record",
          "F3: 信封内联 sections/tables/figures 条目名，或把清单提交为可解析工件路径",
          "F4: 自算哈希结果留在 gate 侧；retrieved_at 用真实时钟值"
        ]
      },
      "axes_untouched": {
        "verification_status_written": false,
        "epistemic_status_written": false,
        "claims_marked_verified": false
      },
      "artifacts": {
        "verification.json": "sha256:f65b87fb1b3fc5537c738e6548d28087bc7c8f613b62b41ce0459006eb60b0f6",
        "out_of_scope_observations.json": "sha256:2c95e57d4fa4efd78891797e64b9031b9ae346e917c4f870cbec7d3c5a070863",
        "source_markdown.md": "sha256:4068f881c6722010ea3cdf78ee673068d8fb56fdc12be39db9c7b3f764457af2",
        "upstream_envelope_wp-444-01.json": "sha256:e80a5dbbdf4500e94e2c1377f6ffad4fdd32285fb8a99bb66fe6d7496c28574f",
        "upstream_report_14623.md": "sha256:1aaf0cc1b1c167bcc8c83d4a0c9858e5cee74e2db72a46b59ec1531827af6b6c"
      },
      "repro_cmd": "cd $(git rev-parse --show-toplevel) && python3 work/verify_wp444_01.py --md artifacts/wp-444-04/source_markdown.md --upstream artifacts/wp-444-04/upstream_report_14623.md && python3 work/observe_source_numbers.py && python3 work/build_review_report.py && python3 -m pytest tests/test_wp444_04_review.py -q"
    }
  }
}
```
