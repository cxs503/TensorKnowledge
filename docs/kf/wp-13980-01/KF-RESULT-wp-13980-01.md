# KF-RESULT wp-13980-01 — 报告 13980 资产登记（01-asset-registration）

**Package**: `wp-13980-01` · **Task**: `01-asset-registration` · **Report**: `13980` (`ice_resistance`) · **Producer**: `kf-worker/m20603` · **Generated**: `2026-11-14T15:40:31Z`

**源标题**: A2-ICE-MODULES 第1轮：冰区端点 8×5 功能全扫（35 真跑 / 5 honest GAP，54 项基准 46 通过）

> 本包只做**资产登记**：钉住源字节、为每个资产给出可机器复核的定位符、用 PNG 字节探针与路由存在性探针把「图确实存在」「端点确实存在」「某端点确实不存在」三类事实变成证据。**不抽取断言、不做报告分类、不重算冰区物理**（02/03 工序职责），因此 `claims = []` 是完整结果而非遗漏。

## 1. 源取证（门禁可独立复算）

| 项 | 值 |
|---|---|
| source_uri | `tensor://reports/13980`（字段 `markdown`） |
| sha256 | `sha256:2e506d3c8285306a34dd397de133f8c48f6f02a604629adbc0c79eb81ce83ce6` |
| 本地副本 | `docs/kf/wp-13980-01/source_markdown.md`（byte-exact，无换行改写） |
| 规模 | 8267 chars / 11213 B utf-8 / 120 逻辑行 |
| 平台记录 | id=`13980` status=`published` mission=`14895` created=`2026-11-11T12:25:19.160375+00:00` |
| tags | `A2-ICE-MODULES, ice, endpoint-sweep, coverage, m14895` |
| 契约核对 | title_match=True scenario_match=True |

源哈希由本包从**本地副本重算**（校验项 C02），平台侧可再算一次比对；登记时与回环时两个独立断点取值相等（§6）。

## 2. 资产总账（28 项）

| asset_class | 数量 | | resolution | 数量 |
|---|---|---|---|---|
| `artifact_reference` | 2 | | `declared_absent` | 1 |
| `endpoint` | 7 | | `referenced_unresolved` | 6 |
| `endpoint_declared_absent` | 1 | | `resolved_in_source` | 21 |
| `figure` | 8 | |  |  |
| `parameter_block` | 1 | |  |  |
| `script_reference` | 4 | |  |  |
| `source_document` | 1 | |  |  |
| `table` | 4 | |  |  |

### 2.1 逐资产登记表

| id | class | label | family | 源行 | resolution | 证据 |
|---|---|---|---|---|---|---|
| A01 | `source_document` | tensor_reports[13980].markdown | `—` | 1 | `resolved_in_source` | quote sha256 `d7325917c4dd…`；出现 1 次 |
| A02 | `figure` | fig1_ice_resistance.png | `F1_ice_resistance` | 97 | `resolved_in_source` | §④ token `F1 三法交叉` @ quote[16:23]；png sha256 `3eb8eb758f10…` |
| A03 | `figure` | fig2_ice_maneuvering.png | `F2_ice_maneuvering` | 97 | `resolved_in_source` | §④ token `F2 回转` @ quote[24:29]；png sha256 `de86c71fca70…` |
| A04 | `figure` | fig3_ice_load_inversion.png | `F4_ice_load_inversion` | 97 | `resolved_in_source` | §④ token `F3 反演` @ quote[30:35]；png sha256 `802a5f17d89c…` |
| A05 | `figure` | fig4_polaris.png | `F5_polaris` | 97 | `resolved_in_source` | §④ token `F4 POLARIS` @ quote[36:46]；png sha256 `05213abb0806…` |
| A06 | `figure` | fig5_marine_icing.png | `F6_marine_icing` | 97 | `resolved_in_source` | §④ token `F5 结冰率` @ quote[47:53]；png sha256 `fc5cec1c3e27…` |
| A07 | `figure` | fig6_grease_envelope.png | `F7_grease_ice` | 97 | `resolved_in_source` | §④ token `F6 包络` @ quote[54:59]；png sha256 `d7316a5cf432…` |
| A08 | `figure` | fig7_ice_cii.png | `F8_ice_cii` | 97 | `resolved_in_source` | §④ token `F7 CII` @ quote[60:66]；png sha256 `09d12437dcbb…` |
| A09 | `figure` | fig8_coverage.png | `coverage` | 97 | `resolved_in_source` | §④ token `覆盖矩阵` @ quote[67:71]；png sha256 `0772181d4969…` |
| A10 | `table` | coverage matrix (8 families x 5 conditions: 真跑/基准/GAP) | `—` | 18 | `resolved_in_source` | quote sha256 `17105d3e2e8d…`；块范围 18–27 行 |
| A11 | `table` | per-condition core quantities under the coverage matrix | `—` | 31 | `resolved_in_source` | quote sha256 `a43a950bfa9b…`；块范围 31–72 行 |
| A12 | `table` | benchmark table excerpt (54 scored items; full table in benchmarks.csv) | `—` | 75 | `resolved_in_source` | quote sha256 `eccb369ca3d4…`；块范围 75–94 行 |
| A13 | `table` | §⑥ error judgement: key quantity vs baseline, <3% answered per item | `—` | 109 | `resolved_in_source` | quote sha256 `d44dd6356729…`；块范围 109–120 行 |
| A14 | `parameter_block` | reference ship Baltic 1A 145 m principal particulars | `—` | 4 | `resolved_in_source` | quote sha256 `de10da04f55b…`；出现 1 次 |
| A15 | `endpoint` | /api/v1/ice-navigation/resistance | `F1_ice_resistance` | 20 | `resolved_in_source` | 路由探针 HTTP `422`（present=True） |
| A16 | `endpoint` | /api/v1/podded-ice-maneuvering/turning | `F2_ice_maneuvering` | 21 | `resolved_in_source` | 路由探针 HTTP `200`（present=True） |
| A17 | `endpoint` | /api/v1/calculations/ice-load-inversion | `F4_ice_load_inversion` | 23 | `resolved_in_source` | 路由探针 HTTP `422`（present=True） |
| A18 | `endpoint` | /api/v1/polaris/assess | `F5_polaris` | 24 | `resolved_in_source` | 路由探针 HTTP `422`（present=True） |
| A19 | `endpoint` | /api/v1/calculations/marine-icing-stability | `F6_marine_icing` | 25 | `resolved_in_source` | 路由探针 HTTP `422`（present=True） |
| A20 | `endpoint` | /api/v1/calculations/grease_ice_envelope | `F7_grease_ice` | 26 | `resolved_in_source` | 路由探针 HTTP `200`（present=True） |
| A21 | `endpoint` | /api/v1/calculations/cii-ice-correction | `F8_ice_cii` | 27 | `resolved_in_source` | 路由探针 HTTP `200`（present=True） |
| A22 | `endpoint_declared_absent` | ice-mooring endpoint (drift load / mooring load) | `F3_ice_mooring` | 22 | `declared_absent` | 报告行 `endpoint=None`；5/5 候选路由 404 |
| A23 | `script_reference` | runs/ice_8x5/run_sweep.py | `—` | 8 | `referenced_unresolved` | worktree_exists=False |
| A24 | `script_reference` | cross_method.py | `—` | 8 | `referenced_unresolved` | worktree_exists=False |
| A25 | `script_reference` | make_tables.py | `—` | 9 | `referenced_unresolved` | worktree_exists=False |
| A26 | `script_reference` | tests/test_ice_8x5_sweep.py | `—` | 10 | `referenced_unresolved` | worktree_exists=False |
| A27 | `artifact_reference` | results.csv | `—` | 9 | `referenced_unresolved` | worktree_exists=False |
| A28 | `artifact_reference` | benchmarks.csv | `—` | 9 | `referenced_unresolved` | worktree_exists=False |

`claims` 为空的原因（机器可读同字段见 manifest `claims_empty_reason`）：Task type is 01-asset-registration: this package pins source bytes and registers asset identity/locators only. objective.classify_report_type=false, objective.extraction_performed=false. Claim extraction is the 03-knowledge-extraction stage and independent review is the 04 stage, so an empty claims array is the complete result of this stage, not an omission.

## 3. 图件字节层（8 幅 PNG 逐幅钉哈希）

| # | name | family | HTTP | bytes | sha256 | 段号/图注号 |
|---|---|---|---|---|---|---|
| 1 | `fig1_ice_resistance.png` | `F1_ice_resistance` | 200 | 67289 | `3eb8eb758f102e72…` | F1 / F1 |
| 2 | `fig2_ice_maneuvering.png` | `F2_ice_maneuvering` | 200 | 57488 | `de86c71fca70ac86…` | F2 / F2 |
| 3 | `fig3_ice_load_inversion.png` | `F4_ice_load_inversion` | 200 | 48256 | `802a5f17d89ce9a8…` | F3 / F4 |
| 4 | `fig4_polaris.png` | `F5_polaris` | 200 | 38794 | `05213abb0806b398…` | F4 / F5 |
| 5 | `fig5_marine_icing.png` | `F6_marine_icing` | 200 | 53056 | `fc5cec1c3e275606…` | F5 / F6 |
| 6 | `fig6_grease_envelope.png` | `F7_grease_ice` | 200 | 75410 | `d7316a5cf4322b49…` | F6 / F7 |
| 7 | `fig7_ice_cii.png` | `F8_ice_cii` | 200 | 48110 | `09d12437dcbb7018…` | F7 / F8 |
| 8 | `fig8_coverage.png` | `coverage` | 200 | 31831 | `0772181d49698ec6…` | — / — |

**段号/图注号一致性**：比较 8 幅，一致 3 幅，不一致 5 幅。§④ numbers its own list F1..F7 sequentially while record captions keep family numbers (F3_ice_mooring is the honest GAP, so captions F4..F8 sit against section F3..F7). Family binding is made by caption semantics, not by figure number; the mismatch is recorded here rather than silently repaired in the source.

PNG 本体**不随本包入库**（登记钉的是身份不是像素）：`platform_bytes.bytes_committed=false`，校验项 C25 断言没有任何图件字节被声称为已入库。复核方式=按 §7 命令重取并比对 sha256。

## 4. 端点路由存在性 + F3 缺口取证

| family | path | probe | status | present |
|---|---|---|---|---|
| `F1_ice_resistance` | `/api/v1/ice-navigation/resistance` | POST `{}` | 422 | True |
| `F2_ice_maneuvering` | `/api/v1/podded-ice-maneuvering/turning` | POST `{}` | 200 | True |
| `F4_ice_load_inversion` | `/api/v1/calculations/ice-load-inversion` | POST `{}` | 422 | True |
| `F5_polaris` | `/api/v1/polaris/assess` | POST `{}` | 422 | True |
| `F6_marine_icing` | `/api/v1/calculations/marine-icing-stability` | POST `{}` | 422 | True |
| `F7_grease_ice` | `/api/v1/calculations/grease_ice_envelope` | POST `{}` | 200 | True |
| `F8_ice_cii` | `/api/v1/calculations/cii-ice-correction` | POST `{}` | 200 | True |

**F3 冰区系泊（报告标 `NOT_SUPPORTED`）**：报告覆盖矩阵该行 `endpoint=None`，5/5 工况未真跑。本包用候选路由探针把「没有这个端点」从断言升级为证据：

| 候选路由 | 探针结果 |
|---|---|
| `/api/v1/ice-mooring/loads` | HTTP 404 |
| `/api/v1/calculations/ice-mooring` | HTTP 404 |
| `/api/v1/ice-mooring/drift-loads` | HTTP 404 |
| `/api/v1/calculations/ice-drift-mooring` | HTTP 404 |
| `/api/v1/ice-navigation/mooring-loads` | HTTP 404 |

探针判别规则：`POST {}` 返回 422/405/200 说明**路由存在**（422=存在但请求体校验失败），404 说明**路由不存在**。该规则以报告已真跑的 F1 端点作阳性对照（若阳性对照也 404，则探针失效，C20 会失败）。

## 5. 未解析引用（如实登记，不丢）

| id | 引用 | 源行 | 未解析原因 |
|---|---|---|---|
| A23 | `runs/ice_8x5/run_sweep.py` | 8 | path text resolved in the report; the script belongs to the report's mission run environment, not to the TensorKnowledge worktree, so no bytes are pinned |
| A24 | `cross_method.py` | 8 | path text resolved in the report; the script belongs to the report's mission run environment, not to the TensorKnowledge worktree, so no bytes are pinned |
| A25 | `make_tables.py` | 9 | path text resolved in the report; the script belongs to the report's mission run environment, not to the TensorKnowledge worktree, so no bytes are pinned |
| A26 | `tests/test_ice_8x5_sweep.py` | 10 | path text resolved in the report; the script belongs to the report's mission run environment, not to the TensorKnowledge worktree, so no bytes are pinned |
| A27 | `results.csv` | 9 | programmatic output of the report's own sweep; not part of this repository, occurrences in source = 1 |
| A28 | `benchmarks.csv` | 9 | programmatic output of the report's own sweep; not part of this repository, occurrences in source = 2 |

## 6. 机器校验（26 pass / 0 skipped / 0 fail，共 26 项）

| id | check | result | detail |
|---|---|---|---|
| C01 | `source_field_is_markdown` | **pass** | source_field=markdown |
| C02 | `local_copy_hash_equals_source_hash` | **pass** | recomputed sha256:2e506d3c8285306a34dd397de133f8c48f6f02a604629adbc0c79eb81ce83ce6 |
| C03 | `chars_match` | **pass** | chars=8267 |
| C04 | `utf8_bytes_match` | **pass** | bytes_utf8=11213 |
| C05 | `line_count_match` | **pass** | lines=120 |
| C06 | `title_matches_contract` | **pass** | title=A2-ICE-MODULES 第1轮：冰区端点 8×5 功能全扫（35 … |
| C07 | `scenario_matches_contract` | **pass** | scenario_key=ice_resistance |
| C08 | `platform_status_published` | **pass** | status=published |
| C09 | `report_sections_present` | **pass** | §①–§⑥ all present in source |
| C10 | `declared_figures_registered` | **pass** | record=8, registered=8 |
| C11 | `figure_bytes_fetched` | **pass** | 8/8 HTTP 200 |
| C12 | `figure_hashes_pinned` | **pass** | 8/8 sha256 pinned |
| C13 | `caption_family_binding_one_to_one` | **pass** | 8 distinct families for 8 figures |
| C14 | `locators_resolve_to_quote` | **pass** | 28/28 char spans reproduce their quote |
| C15 | `locator_line_numbers` | **pass** | 28/28 line numbers consistent |
| C16 | `figure_section_tokens_resolve` | **pass** | 8/8 §④ tokens hit their own family |
| C17 | `asset_id_unique_and_format` | **pass** | 28 ids, duplicates=[] |
| C18 | `counts_consistent` | **pass** | assets=28, by_resolution=28, by_class=28 |
| C19 | `claims_empty_with_reason` | **pass** | claims=[] (registration only) + claims_empty_reason present |
| C20 | `endpoint_routes_present` | **pass** | 7/7 routes answered non-404 (422 = route exists, body validated) |
| C21 | `mooring_absence_evidenced` | **pass** | 5/5 candidate ice-mooring routes answered 404 |
| C22 | `publish_roundtrip_identical` | **pass** | second fetch sha256 2e506d3c8285… equal=True |
| C23 | `manifest_schema_valid` | **pass** | schemas/asset_manifest.registration.v1.schema.json |
| C24 | `kf_result_schema_valid` | **pass** | schemas/kf_result.v1.schema.json |
| C25 | `figure_bytes_not_claimed_committed` | **pass** | figure PNGs are pinned by hash only; no PNG bytes are committed or claimed as committed |
| C26 | `doc_pins_source_hash` | **pass** | KF-RESULT document quotes 2e506d3c8285… |

**verdict**: `PASS` — 由 `scripts/kf_fetch_13980.py` 生成 `verify_report.json`，pytest `tests/kf/test_wp_13980_info.py` 在离线态重跑同一组定位符/哈希不变量。

## 7. 发布往返（publish round-trip）

| 断点 | 时间 | chars | sha256 |
|---|---|---|---|
| 登记取源 | 2026-11-14T15:40:26Z | 8267 | `sha256:2e506d3c8285306a34dd397de133f8c48f6f02a604629adbc0c79eb81ce83ce6` |
| 回环复核 | 2026-11-14T15:40:31Z | 8267 | `sha256:2e506d3c8285306a34dd397de133f8c48f6f02a604629adbc0c79eb81ce83ce6` |

判定：`hash_equal=True`，`chars_equal=True`，平台记录 `status=published` → **IDENTICAL**。（同进程内两次独立取数，用于证明源不是被缓存篡改的本地副本。）

## 8. 复现

```bash
# 在线重建（需平台凭据：TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
python3 scripts/kf_fetch_13980.py
# 离线重建（只用已入库字节；路由/字节探针记录沿用上次结果）
python3 scripts/kf_fetch_13980.py --offline
# 验收不变量
python3 -m pytest tests/kf/test_wp_13980_01.py -q
```

本包产物（sha256 见 `kf_result.wp-13980-01.json` → `outputs`）：

| 文件 | bytes | sha256 |
|---|---|---|
| `asset_manifest.json` | 44894 | `791a417bd907d667ed652ebc…` |
| `publish_roundtrip.json` | 951 | `e04a99e6a318702c7463adc0…` |
| `verify_report.json` | 4369 | `de9840b35d700660e715d9cf…` |
| `fig1_asset_registration.png` | 102779 | `c8cff66a6028119097203d04…` |
| `KF-RESULT-wp-13980-01.md` | 0 | 见 `kf_result.wp-13980-01.json` → `outputs`（本文件不能自指自己的哈希） |

## 9. 边界与局限（诚实声明）

1. **不做精度判定**。报告里 `<3% / <15%` 的误差结论属于 03 工序与平台闸门，本包不复制、不背书；本包只保证「报告写了什么、写在哪一行、哈希对得上」。
2. **图件按哈希登记，不按像素入库**。平台图件端点若变更/下线，C11/C12 会失败而不是静默通过。
3. **路由探针只证明路由存在**，不证明返回数值正确（那需要工况真跑，属报告自身与本包之外的工作）。F3 缺口的证据强度=5 条候选路由 404，不排除命名完全不同的实现存在。
4. **报告 §④ 段号与平台图注号不一致 5/8**。本包以图注语义绑定 family，并把不一致如实记录在 §3 与 manifest `figures.label_alignment`，**不修改源 markdown**（源是不可变证据）。
5. **未抽取断言**：`claims=[]`，因此本包不能替代独立的 03 抽取与 04 审核；verification level 最高只到 L2（证据可解）而非 L3（独立审核通过）。

