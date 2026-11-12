# wp-1561-01 — asset registration for report 1561

**Task type:** `01-asset-registration` (工序 01) · **Lane:** C · **Report:** `1561` ·
**Source:** `tensor://reports/1561` (`markdown`)

注册范围（与契约逐字一致）：*"登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的
附件/工件，不做抽取。claims 允许为空数组。"* 本包不抽取知识、不做报告分类、不打 verified 戳。

## 1. 输入与哈希钉扎

| 项 | 值 |
|---|---|
| 契约 hash | `sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620` |
| 平台重算 hash（UTF-8 bytes） | `sha256:19203e6ea7f05573f0b06835f9c0e1f08fb54fc5481787ace02487d5ac6d1620` |
| 一致 | `True` |
| 大小 | 11620 bytes / 7340 chars / 163 lines |
| 标题（record） | m1838 推进端点推力闭合修复：Kt=0.3-0.2J 直线式 → BEMT 反解转速，5 型船闸门 verdict_fail=0 |
| 标题与契约一致 | `True` |
| record 状态 / mission / 创建时间 | `published` / `1838` / `2026-11-02T00:32:11.021164+00:00` |

快照：`source/report_1561.md`（与平台 `markdown` 字段逐字节相同，供离线复跑）;
record 元数据：`report_record.json`。

## 2. 产出物

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 资产清单：57 条，每条含 verbatim quote + 行级 locator + 可解析性状态 |
| `kf_result.json` | `kf_result.v1` 信封（`outputs["asset_manifest.json"]` 内嵌同一清单，claims=[]） |
| `selfcheck.json` | 18 项自检及三件产物 sha256 |
| `figure_fetch.json` | 5 张声明图的取回探测结果（副本二进制可用性） |
| `fig_inventory.png` | 清单/可解析性统计图（由本目录 JSON 程序化生成） |
| `source/report_1561.md` | 报告 `markdown` 字节快照 |

## 3. 资产分布

| kind | count |
|---|---|
| `gate_predicate` | 8 |
| `report_cross_reference` | 7 |
| `citation_reference` | 6 |
| `section` | 6 |
| `figure` | 5 |
| `api_endpoint` | 4 |
| `artifact_path` | 4 |
| `code_path` | 4 |
| `code_block` | 3 |
| `run_output_token` | 3 |
| `table` | 3 |
| `api_contract_field_list` | 1 |
| `command` | 1 |
| `report_document` | 1 |
| `test_path` | 1 |

可解析性（每条资产都必须落在某一档，不许沉默）：

| resolvability | count |
|---|---|
| `declared_and_markdown_referenced_binary_not_served` | 5 |
| `named_no_locator` | 21 |
| `referenced_only_not_resolvable_from_this_record` | 14 |
| `resolved_in_markdown` | 17 |

## 4. 未解析项（显式声明，不静默）

| id | kind | status | reason |
|---|---|---|---|
| `1561-o000` | `internal_numeric_relation` | `unresolved` | which denominator the endpoint uses is not stated in the report |
| `1561-o001` | `asset_payload_unavailable` | `unresolved` | figure binary not served by the report API at registration time |
| `1561-o002` | `provenance_gap` | `unresolved` | no commit identity or digest supplied inside report 1561 |
| `1561-o003` | `self_declared_non_pass_rows` | `unresolved` | left exactly as the source states it (否 / 未判定) |

图中二进制取回探测（主动探测，非假设）：

| figure | HTTP | body |
|---|---|---|
| `fig1_thrust_power.png` | 404 | {"detail":"figure not found"} |
| `fig2_cross_pe.png` | 404 | {"detail":"figure not found"} |
| `fig3_eta0_vs_diameter.png` | 404 | {"detail":"figure not found"} |
| `fig4_open_water.png` | 404 | {"detail":"figure not found"} |
| `fig5_pitch_sweep.png` | 404 | {"detail":"figure not found"} |

## 5. 局限

- 上游 `ship-performance-platform` 的代码/工件路径只以文本形式出现在报告里，本仓无法 hash 钉扎
  （报告只给分支名 `agent/m1838`，无 commit sha）→ 登记为 `referenced_only_*`，`present_in_worktree=false`。
- 5 张声明的图二进制取不到（见上表 404），因此任何依赖图内容的工序只能引用 markdown 文字描述。
- 引用（ITTC-78 / B4-70 / Holtrop / Taylor / Wageningen B）仅登记名字，报告未给版次或 DOI，故标
  `named_no_locator`，未尝试解析到外部文献。
- 本包不判断报告结论真伪；⑥ 表中自报「否 / 未判定」两行原样保留（`1561-o003`）。

## 6. 自检（acceptance 逐条）

| check | result |
|---|---|
| `source_hash_matches_contract` | PASS |
| `source_hash_matches_record_metadata` | PASS |
| `no_duplicate_ids` | PASS |
| `asset_id_pattern` | PASS |
| `asset_ids_contiguous` | PASS |
| `source_locator_resolvable` | PASS |
| `counts_consistent` | PASS |
| `claims_empty_or_evidenced` | PASS |
| `no_verified_stamp` | PASS |
| `figures_all_registered` | PASS |
| `non_resolved_assets_explained` | PASS |
| `observations_quote_bound` | PASS |
| `envelope_schema_pass` | PASS |
| `envelope_report_id` | PASS |
| `envelope_package_id` | PASS |
| `envelope_source_field` | PASS |
| `envelope_declares_manifest_output` | PASS |
| `envelope_manifest_matches_file` | PASS |

契约 acceptance 映射：`valid_json` → 产物可解析 + `envelope_schema_pass`；`schema_pass` → 同上；
`source_locator_resolvable` → 逐条 quote∈原文且行号命中；`source_hash_matches` → 契约/重算/manifest 三方一致；
`no_duplicate_ids` → id 唯一且连续；`all_claims_have_evidence_or_explicit_unresolved_status` → claims=[]（契约允许的
完整结果）+ 每条非 resolved 资产带显式状态/原因。

## 7. 一键复跑

```bash
cd <TensorKnowledge worktree>
python3 scripts/kf_wp1561_01_asset_manifest.py && \
python3 scripts/kf_wp1561_01_asset_manifest.py --verify && \
python3 -m pytest tests/test_wp1561_01_asset_registration.py -q && \
python3 runs/wp-1561-01/make_fig.py && \
python3 runs/wp-1561-01/make_readme.py
```

`--fetch` 会重新从平台 API 取 `markdown` 与图二进制探测结果（需要 `$TENSOR_API_BASE` 与 agent 凭据）。

producer: `agent/m15529 (TensorKnowledge) · package wp-1561-01` · emitted_at `2026-11-12T00:56:08+00:00`
