# KF-RESULT wp-7920-01 — 报告 7920 资产登记（01-asset-registration）

> 本文件由 `scripts/kf/publish_report.py render` 从 `docs/kf/wp-7920-01/asset_manifest.json`
> 与 `verification.json` 程序化生成，数字零手抄。

## ① 案例介绍（本工序对象）

| 项 | 值 |
|---|---|
| 工序 | `01-asset-registration`（lane C） |
| 工作包 | `wp-7920-01` |
| 源报告 | `tensor://reports/7920`（report_id `7920`） |
| 标题 | IN154-P4 混合推进能量管理（电池-柴油并联）验证：功率分配/峰值削减/负荷优化/能量平衡闭环 |
| scenario_key | `green_shipping.hybrid_propulsion_energy_management` |
| 源字段 | `markdown`，6421 字符 / 10592 字节 / 161 行 |
| sha256(markdown) | `sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b` |
| 钉扎来源 | self_pinned_at_registration: no platform work-package contract endpoint is available to this lane; the registration-time measurement is pinned and re-derived independently by the verification step |
| 平台图件 | fig1_power_split_soc.png, fig2_peak_shaving.png, fig3_load_optimization.png, fig4_battery_and_criteria.png, fig5_efficiency_sensitivity.png |

## ② 怎么做的（方法 / 流程 / 工具链）

1. **取源（只读）**：`GET $TENSOR_API_BASE/tensor/reports/7920`（Bearer=agent token），
   只读 `markdown` / `title` / `scenario_key` / `tags` / `figures` 字段；字节副本落
   `docs/kf/wp-7920-01/source_7920.json`，使本包可离线复跑。
2. **登记（`scripts/kf/register_assets.py`，通用、确定性、无时间戳）**：从文本抽取全部路径型引用
   （`*.py|json|csv|png|md|txt|yaml|toml|sh`）→ 按「裸文件名 ↔ 点分路径」canonical 合并 →
   逐条给出可解 locator（`char_span` + 逐字 quote + 行号 + 出现次数 + quote sha256）→
   每条给出 resolution 与 resolution_check（record 内是否有 png 载荷 / 是否在本工作树存在）。
   不支持的证据一律降级为 `referenced_unresolved` / `declared_absent`，不猜。
3. **出信封**：`kf_result.json`（`schemas/kf_result.v1.schema.json`）内嵌整份 manifest，
   `provenance.source_hash` 与 manifest 同源。
4. **自验（`scripts/kf/publish_report.py verify`）**：两个产物分别过共享门 schema；从 record 字节
   独立重算 sha256；逐条重解 locator；查 id 唯一性与空 claims 契约；产 `verification.json`。
   任何一项不通过即 `all_ok=false`，本包不得发布。
5. **发布（`... publish`）**：把本报告 POST 到 `/tensor/reports`，回读并解析内嵌 JSON 块，
   校验 `package_id` / `report_id` / `source_hash` 往返一致，落 `publish_receipt.json`。

## ③ 计算结果（数字表）

| 量 | 值 |
|---|---|
| 登记资产数 | 11 |
| 按类 | data=2, dataset=1, figure=5, report_markdown=1, source_code=2 |
| 按可达性 | declared_absent=5, referenced_unresolved=5, resolved_in_source=1 |
| 文本 locator 数 | 10 |
| quote 唯一数 | 10（非唯一 1） |
| 哈希本地重算 | true |
| 哈希与钉扎一致 | true |
| 自验结论 | `all_ok=true` |

**验收项**

| 项 | 结果 | 说明 |
|---|---|---|
| `valid_json` | ✓ | asset_manifest.json + kf_result.json parsed as JSON objects |
| `schema_pass` | ✓ | asset_manifest vs schemas/asset_manifest.v1.schema.json, kf_result vs schemas/kf_result.v1.schema.json; errors=0 |
| `source_hash_matches` | ✓ | live=sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b manifest=sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b envelope=sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b pinned=sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b |
| `source_locator_resolvable` | ✓ | 11/11 asset locators re-resolved on live bytes (10 text spans + document locator; char span + verbatim quote + line + uniqueness); 161 source lines |
| `no_duplicate_ids` | ✓ | 11 asset ids, duplicates=[] |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✓ | 0 claims; empty-claims reason stated: True |
| `envelope_matches_manifest` | ✓ | kf_result.outputs['asset_manifest.json'] is byte-identical to asset_manifest.json; package_id/report_id agree |
| `counts_consistent` | ✓ | assets=11 len(assets)=11 by_class_sum=11 by_resolution_sum=11 |

**资产清单**

| id | label | 类 | resolution | 行 | check |
|---|---|---|---|---|---|
| `A01` | `reports/7920#markdown` | report_markdown | resolved_in_source | 1 | resolved |
| `A02` | `backend/modules/hybrid_propulsion/report_md.py` | source_code | declared_absent | 3 | absent |
| `A03` | `artifacts/hybrid_propulsion/results.json` | data | declared_absent | 3 | absent |
| `A04` | `pipeline.py` | source_code | declared_absent | 56 | absent |
| `A05` | `artifacts/hybrid_propulsion/fig1_power_split_soc.png` | figure | referenced_unresolved | 115 | unresolved |
| `A06` | `artifacts/hybrid_propulsion/fig2_peak_shaving.png` | figure | referenced_unresolved | 119 | unresolved |
| `A07` | `artifacts/hybrid_propulsion/fig3_load_optimization.png` | figure | referenced_unresolved | 123 | unresolved |
| `A08` | `artifacts/hybrid_propulsion/fig4_battery_and_criteria.png` | figure | referenced_unresolved | 127 | unresolved |
| `A09` | `artifacts/hybrid_propulsion/fig5_efficiency_sensitivity.png` | figure | referenced_unresolved | 131 | unresolved |
| `A10` | `timeseries_mixed_24h.csv` | dataset | declared_absent | 160 | absent |
| `A11` | `report.json` | data | declared_absent | 160 | absent |

## ④ 结果图

本工序为登记类（纯结构化数据，无场量/曲线），不出图；可发表图件属被登记报告
`7920` 自身（fig1_power_split_soc.png, fig2_peak_shaving.png, fig3_load_optimization.png, fig4_battery_and_criteria.png, fig5_efficiency_sensitivity.png，本包仅登记其元数据，
record 未提供 png 载荷，故不哈希图像字节）。

## ⑤ 注意点（坑 / 局限 / 适用范围）

1. **图件只有元数据**：`GET /tensor/reports/7920/figures/<name>` 在本平台返回 404，
   record 的 `png_base64` 为空，因此图件登记为 `referenced_unresolved`，不声称任何图像哈希。
2. **`declared_absent` 不是缺陷**：被登记报告的脚本/工件属其他仓（船舶平台），
   本仓工作树查不到是预期结果，manifest 用 `resolution_check.scope` 明示检查范围。
3. **无平台契约哈希**：本 lane 拿不到 work-package 契约端点（404），
   `contract_source_hash` 为登记时钉扎值并在 `contract_origin` 里写明来源；
   `verification` 再独立重算一次，若报告被改写则该验收项直接变红。
4. **登记≠验证**：manifest 从不标记任何资产「已验证」；门禁（平台）自己重算哈希与 locator。

## ⑥ 误差判定（关键量 vs 基准）

| 量 | 实测 | 基准 | 相对误差 | 是否 < 3% |
|---|---|---|---|---|
| sha256(markdown) | `sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b` | 钉扎值 `sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b` | 0（逐位相同） | 是（0%） |
| chars | 6421 | 6421（manifest 与 record 同源） | 0 | 是（0%） |
| locator 复解 | 11 条全解 | 同条数 | 0 | 是（0%） |

本工序是确定性登记：能 100% 复算的量只有哈希/字符数/locator 可解性，误差均为 0；
其余为分类计数（非测量量，不做误差判定）。

---

**审计链**：`docs/kf/wp-7920-01/source_7920.json`（源字节副本）→
`asset_manifest.json`（登记）→ `kf_result.json`（信封）→ `verification.json`（自验）→
`publish_receipt.json`（发布往返）。
复跑：`python3 scripts/kf/publish_report.py verify --package-dir docs/kf/wp-7920-01`

```json
{
  "package_id": "wp-7920-01",
  "task_type": "01-asset-registration",
  "contract_version": "1.0",
  "report_id": "7920",
  "provenance": {
    "source_uri": "tensor://reports/7920",
    "source_field": "markdown",
    "source_hash": "sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b",
    "source_hash_matches": true,
    "title": "IN154-P4 混合推进能量管理（电池-柴油并联）验证：功率分配/峰值削减/负荷优化/能量平衡闭环",
    "scenario_key": "green_shipping.hybrid_propulsion_energy_management",
    "chars": 6421
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-7920-01",
      "task_type": "01-asset-registration",
      "report_id": "7920",
      "lane": "C",
      "producer": "scripts/kf/register_assets.py",
      "generator_inputs": {
        "report_id": "7920",
        "package_id": "wp-7920-01",
        "expect_sha256": "sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b",
        "expect_chars": null,
        "record_path_or_api": "GET /tensor/reports/7920"
      },
      "source": {
        "uri": "tensor://reports/7920",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b",
        "contract_source_hash": "sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b",
        "contract_origin": "self_pinned_at_registration: no platform work-package contract endpoint is available to this lane; the registration-time measurement is pinned and re-derived independently by the verification step",
        "chars": 6421,
        "bytes_utf8": 10592,
        "lines": 161,
        "title": "IN154-P4 混合推进能量管理（电池-柴油并联）验证：功率分配/峰值削减/负荷优化/能量平衡闭环",
        "scenario_key": "green_shipping.hybrid_propulsion_energy_management",
        "platform_figures": [
          "fig1_power_split_soc.png",
          "fig2_peak_shaving.png",
          "fig3_load_optimization.png",
          "fig4_battery_and_criteria.png",
          "fig5_efficiency_sensitivity.png"
        ],
        "platform_tags": [
          "IN154-P4",
          "混合推进",
          "能量管理",
          "EMS",
          "绿色航行",
          "SOC",
          "动态规划",
          "peak-shaving"
        ],
        "chars_match_contract": null
      },
      "counts": {
        "assets": 11,
        "by_class": {
          "report_markdown": 1,
          "source_code": 2,
          "data": 2,
          "figure": 5,
          "dataset": 1
        },
        "by_resolution": {
          "resolved_in_source": 1,
          "declared_absent": 5,
          "referenced_unresolved": 5
        },
        "resolved_in_source": 1,
        "referenced_unresolved": 5,
        "declared_absent": 5,
        "markdown_locators": 10
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "report_markdown",
          "label": "reports/7920#markdown",
          "token": null,
          "in_report_section": "document",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 6421,
            "start_line": 1,
            "end_line": 161,
            "quote": "# 混合推进能量管理（电池-柴油并联）验证报告 — IN154-P4",
            "quote_sha256": "43e5e8f3bd7d1c3f2c33c2594f4710e7d9ed55ec6d1add02a299f64a6118f684",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(utf-8 markdown bytes) == manifest.source.hash",
            "result": "resolved"
          },
          "note": "6421 chars / 10592 bytes, quoted locators below are slices of these bytes"
        },
        {
          "asset_id": "A02",
          "asset_class": "source_code",
          "label": "backend/modules/hybrid_propulsion/report_md.py",
          "token": "backend/modules/hybrid_propulsion/report_md.py",
          "in_report_section": "混合推进能量管理（电池-柴油并联）验证报告 — IN154-P4",
          "locator": {
            "method": "char_span",
            "start_char": 44,
            "end_char": 90,
            "start_line": 3,
            "end_line": 3,
            "quote": "backend/modules/hybrid_propulsion/report_md.py",
            "quote_sha256": "d964adcf0f9adfe5ae1b4dfcf51e4116deba66387d8c93f734df6ccf6c01eaef",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "worktree existence: backend/modules/hybrid_propulsion/report_md.py",
            "result": "absent"
          },
          "note": "referenced 1x in markdown; declared artefact lives outside this repository (checked scope = TensorKnowledge worktree)"
        },
        {
          "asset_id": "A03",
          "asset_class": "data",
          "label": "artifacts/hybrid_propulsion/results.json",
          "token": "artifacts/hybrid_propulsion/results.json",
          "in_report_section": "混合推进能量管理（电池-柴油并联）验证报告 — IN154-P4",
          "locator": {
            "method": "char_span",
            "start_char": 95,
            "end_char": 135,
            "start_line": 3,
            "end_line": 3,
            "quote": "artifacts/hybrid_propulsion/results.json",
            "quote_sha256": "3409e4674bfa03897e788b6f2972c02e12fdb489c139738cace1c32af9865726",
            "unique": false,
            "occurrences": 2
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "worktree existence: artifacts/hybrid_propulsion/results.json",
            "result": "absent"
          },
          "note": "referenced 2x in markdown; declared artefact lives outside this repository (checked scope = TensorKnowledge worktree)"
        },
        {
          "asset_id": "A04",
          "asset_class": "source_code",
          "label": "pipeline.py",
          "token": "pipeline.py",
          "in_report_section": "② 怎么做的（方法 / 流程 / 关键设置）",
          "locator": {
            "method": "char_span",
            "start_char": 2181,
            "end_char": 2192,
            "start_line": 56,
            "end_line": 56,
            "quote": "pipeline.py",
            "quote_sha256": "6b92e3e77956f8020482ca91889a24f3411c9a4854f2aaaac30ee504ef26ede4",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "worktree existence: pipeline.py",
            "result": "absent"
          },
          "note": "referenced 1x in markdown; declared artefact lives outside this repository (checked scope = TensorKnowledge worktree)"
        },
        {
          "asset_id": "A05",
          "asset_class": "figure",
          "label": "artifacts/hybrid_propulsion/fig1_power_split_soc.png",
          "token": "artifacts/hybrid_propulsion/fig1_power_split_soc.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4028,
            "end_char": 4080,
            "start_line": 115,
            "end_line": 115,
            "quote": "fig1_power_split_soc.png](artifacts/hybrid_propulsio",
            "quote_sha256": "b5659ed5eea18a8b33ca7369d530017a14963c8979b7199e17ea81eed1bda131",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[0].png_base64 / GET /tensor/reports/7920/figures/fig1_power_split_soc.png",
            "result": "unresolved"
          },
          "note": "record carries name+caption only (no png payload; figure endpoint absent), so no image bytes are hashed here"
        },
        {
          "asset_id": "A06",
          "asset_class": "figure",
          "label": "artifacts/hybrid_propulsion/fig2_peak_shaving.png",
          "token": "artifacts/hybrid_propulsion/fig2_peak_shaving.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4190,
            "end_char": 4239,
            "start_line": 119,
            "end_line": 119,
            "quote": "fig2_peak_shaving.png](artifacts/hybrid_propulsio",
            "quote_sha256": "622bcf69779f76b90a1f921485233a3042872065b9bf3df11dc94fba42778c83",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[1].png_base64 / GET /tensor/reports/7920/figures/fig2_peak_shaving.png",
            "result": "unresolved"
          },
          "note": "record carries name+caption only (no png payload; figure endpoint absent), so no image bytes are hashed here"
        },
        {
          "asset_id": "A07",
          "asset_class": "figure",
          "label": "artifacts/hybrid_propulsion/fig3_load_optimization.png",
          "token": "artifacts/hybrid_propulsion/fig3_load_optimization.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4329,
            "end_char": 4383,
            "start_line": 123,
            "end_line": 123,
            "quote": "fig3_load_optimization.png](artifacts/hybrid_propulsio",
            "quote_sha256": "e8f9bc2f4ff96af5818183e033db463eb7c39e8fe84aa55cb478fed43d8b03b5",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[2].png_base64 / GET /tensor/reports/7920/figures/fig3_load_optimization.png",
            "result": "unresolved"
          },
          "note": "record carries name+caption only (no png payload; figure endpoint absent), so no image bytes are hashed here"
        },
        {
          "asset_id": "A08",
          "asset_class": "figure",
          "label": "artifacts/hybrid_propulsion/fig4_battery_and_criteria.png",
          "token": "artifacts/hybrid_propulsion/fig4_battery_and_criteria.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4483,
            "end_char": 4540,
            "start_line": 127,
            "end_line": 127,
            "quote": "fig4_battery_and_criteria.png](artifacts/hybrid_propulsio",
            "quote_sha256": "75f2114f5c505532fbe84138a9ff57a1c3eb2412455eabac6652ce126cca1b8b",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[3].png_base64 / GET /tensor/reports/7920/figures/fig4_battery_and_criteria.png",
            "result": "unresolved"
          },
          "note": "record carries name+caption only (no png payload; figure endpoint absent), so no image bytes are hashed here"
        },
        {
          "asset_id": "A09",
          "asset_class": "figure",
          "label": "artifacts/hybrid_propulsion/fig5_efficiency_sensitivity.png",
          "token": "artifacts/hybrid_propulsion/fig5_efficiency_sensitivity.png",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 4645,
            "end_char": 4704,
            "start_line": 131,
            "end_line": 131,
            "quote": "fig5_efficiency_sensitivity.png](artifacts/hybrid_propulsio",
            "quote_sha256": "cee4cf25c4078cad143422f59c39c3426c45c27d5aa36357ea172f4a6c2a14b3",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "record.figures[4].png_base64 / GET /tensor/reports/7920/figures/fig5_efficiency_sensitivity.png",
            "result": "unresolved"
          },
          "note": "record carries name+caption only (no png payload; figure endpoint absent), so no image bytes are hashed here"
        },
        {
          "asset_id": "A10",
          "asset_class": "dataset",
          "label": "timeseries_mixed_24h.csv",
          "token": "timeseries_mixed_24h.csv",
          "in_report_section": "⑥ 误差判定（逐项 vs 基准）",
          "locator": {
            "method": "char_span",
            "start_char": 6248,
            "end_char": 6272,
            "start_line": 160,
            "end_line": 160,
            "quote": "timeseries_mixed_24h.csv",
            "quote_sha256": "7f632f60fa3db86a27186394ec7f023ae48300063727a4fd0fba68bab5a1745d",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "worktree existence: timeseries_mixed_24h.csv",
            "result": "absent"
          },
          "note": "referenced 1x in markdown; declared artefact lives outside this repository (checked scope = TensorKnowledge worktree)"
        },
        {
          "asset_id": "A11",
          "asset_class": "data",
          "label": "report.json",
          "token": "report.json",
          "in_report_section": "⑥ 误差判定（逐项 vs 基准）",
          "locator": {
            "method": "char_span",
            "start_char": 6295,
            "end_char": 6306,
            "start_line": 160,
            "end_line": 160,
            "quote": "report.json",
            "quote_sha256": "9dbd9380216097555c9deac98aaf3b54257134bb78ccbae4d771b3935525d9ef",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "worktree existence: report.json",
            "result": "absent"
          },
          "note": "referenced 1x in markdown; declared artefact lives outside this repository (checked scope = TensorKnowledge worktree)"
        }
      ],
      "claims": [],
      "claims_note": "registration only: no extraction, no classification, no verification; empty claims list is the contract for task_type=01-asset-registration",
      "resolution_semantics": {
        "resolved_in_source": "bytes/text resolved (markdown itself, file present in the checked worktree, or figure payload present in the record)",
        "referenced_unresolved": "referenced by the report but not resolvable from the record (figure metadata only)",
        "declared_absent": "declared by the report, expected outside the checked worktree",
        "checked_scope": "TensorKnowledge worktree"
      },
      "integrity": {
        "quote_uniqueness": {
          "unique": 10,
          "non_unique": 1
        },
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "verified_logic": "no asset is marked verified here; the platform gate re-hashes the markdown and re-resolves every locator"
      }
    }
  }
}
```
