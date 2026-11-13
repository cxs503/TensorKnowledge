# KF-RESULT wp-10618-01

**package_id**: `wp-10618-01` · **task_type**: `01-asset-registration` · **report_id**: `10618` · **lane**: `C`
**source_uri**: `tensor://reports/10618` · **source_field**: `markdown`
**source_hash (measured)**: `19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01` — equals contract hash: **True**
**chars**: 7463 (contract 7463) · **bytes_utf8**: 7585 · **lines**: 212
**title**: IMO Polar Code Ice Stability Assessment — Complete Implementation · **scenario_key**: `p485w1-n07-spp-ice-stability` · **mission_id**: 9105

## ① 本工序做了什么

只做 01-asset-registration：把 report 10618 的 markdown 当成**源资产**登记——逐字节复算 sha256 并与契约比对，
再把 markdown 内部**可解析的工件**（文档本体、4 张数据表、4 处图引用、2 处代码文件引用、4 个测试标识、3 条标准引用）
逐一登记为带字符区间定位符的资产条目。**不做任何抽取**：`claims` 为空数组（契约 objective.classify_report_type=false），
不产出任何 `verified` 标记（verification 由平台门计算）。共登记 **18** 个资产：
resolved_in_source 5、referenced_unresolved 13、
declared_absent 0。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/10618`（Bearer token 由 `/auth/login` 换取），只读 `markdown` 字段；
   原始快照落 `runs/wp-10618-01/source_10618.md`。**未读/未写任何其它 report_id**。
2. **验身份**：`sha256(markdown.encode('utf-8'))` 本地复算 → `19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01`，与契约 `sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01` 逐字符比对（脚本内
   `hash_matches_contract`，不一致直接 `SystemExit`，不出半成品 manifest）。
3. **定位**：先建 1-based 逻辑行 → 半开字符区间 `[start_char, end_char)` 映射；每个资产以**逐字子串搜索**取真实偏移，
   不手填偏移；同时统计该子串在全文出现次数（`occurrences`），**只有 ==1 才记 `unique: true`**。
4. **资产发现规则**（全部程序化，无人工挑选）：markdown 表格 = 围栏外连续 `|` 行（≥2 行）成块；图 = `![cap](path)`；
   代码引用 = 行内代码里带扩展名的路径；测试 = 行内代码 `test_*`；标准 = §5 三条列表项的整行正则匹配。
5. **解析判定**（resolution）三态，口径写在 manifest 里：`resolved_in_source` = 资产内容本身就在 markdown 中；
   `referenced_unresolved` = 报告指向外部工件，源 markdown 与本交付树都取不到；`declared_absent` = 报告明确声明不存在（本单 0 条）。
   每条的 `resolution_check` 写明实际做过的检查（如 `os.path.exists('/tmp/fig1_gz_curves.png')`）。
6. **附件端点探测**：`GET /tensor/reports/10618/figures` → HTTP 404；
   `GET /tensor/reports/10618/artifacts` → HTTP 404，
   即平台未暴露图/附件字节，仅 record 里有 4 条 figure `name/caption` 元数据。
7. **结构门自检**：manifest 按 `schemas/asset_manifest.v1.schema.json`（jsonschema Draft-07）、信封按
   `schemas/kf_result.v1.schema.json`（Draft 2020-12）校验；因上游 schema 把 `package_id/report_id` 写成 `const`，
   校验时**在内存里重绑**这两个 const 到本包，**不改上游文件**。
8. **一键复跑**：`python3 scripts/kf_wp10618_01_register.py all`。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-10618-01/asset_manifest.json` | 本工序主产物：source 身份块（hash/chars/bytes/lines/title/scenario 全为实测）+ counts + 18 条 assets + 空 claims + integrity |
| `docs/kf/wp-10618-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），`provenance.source_hash` = 实测 hash |
| `docs/kf/wp-10618-01/verification.json` | 6+2 条 acceptance 自查逐项 PASS/FAIL（**本地预检**，非 verified 标记） |
| `docs/kf/wp-10618-01/figures/wp10618_01_asset_map.png` | 左：资产类别 × 解析状态堆叠条形；右：每条资产的字符区间定位图 |
| `runs/wp-10618-01/source_10618.md` | 原文快照（复跑时用于离线比对/复核 locator） |
| `scripts/kf_wp10618_01_register.py` | 可复跑脚本：build/envelope/verify/result/figure/all |

## ④ 证据定位表（claim/字段 → 原文引文片段）

资产清单（字符区间为半开区间，行号为 1-based；`quote` 字段保存逐字引文，完整值见 asset_manifest.json）：

| asset_id | 类别 | 标签 | 章节 | 行区间 | 解析状态 | check |
|---|---|---|---|---|---|---|
| A01 | report_document | report 10618 markdown (whole document) | document | L1–L212 | resolved_in_source | resolved |
| A02 | data_table:4col | table #1 (lines 21-31) | Ship Parameters | L21–L31 | resolved_in_source | resolved |
| A03 | data_table:4col | table #2 (lines 83-89) | Hydrostatics | L83–L89 | resolved_in_source | resolved |
| A04 | data_table:4col | table #3 (lines 93-98) | Ice Accretion | L93–L98 | resolved_in_source | resolved |
| A05 | data_table:5col | table #4 (lines 102-106) | Area Criteria (Cargo Ship) | L102–L106 | resolved_in_source | resolved |
| A06 | figure_reference | GZ Curves | §4 | L121–L121 | referenced_unresolved | absent |
| A07 | figure_reference | Ice Distribution | §4 | L127–L127 | referenced_unresolved | absent |
| A08 | figure_reference | Area Criteria | §4 | L133–L133 | referenced_unresolved | absent |
| A09 | figure_reference | FSC Sensitivity | §4 | L139–L139 | referenced_unresolved | absent |
| A10 | source_code_reference | backend/api/ice_stability.py | §2 | L46–L46 | referenced_unresolved | absent |
| A11 | source_code_reference | stability_core.py | §2 | L74–L74 | referenced_unresolved | absent |
| A12 | test_reference | test_single_surface_analytical | §6 | L178–L178 | referenced_unresolved | unresolved |
| A13 | test_reference | test_gz_wall_sided_formula | §6 | L183–L183 | referenced_unresolved | unresolved |
| A14 | test_reference | test_area_0_40_equals_0_30_plus_30_40 | §6 | L188–L188 | referenced_unresolved | unresolved |
| A15 | test_reference | test_single_rectangular_tank_analytical | §6 | L193–L193 | referenced_unresolved | unresolved |
| A16 | standard_reference | IMO Polar Code Part II-A, Chapter 2 (Intact Stability) | §5 | L168–L168 | referenced_unresolved | unresolved |
| A17 | standard_reference | IMO IS Code 2008, Part A, Chapter 2 | §5 | L169–L169 | referenced_unresolved | unresolved |
| A18 | standard_reference | ISO 19906:2019 (Arctic offshore structures — ice load reference) | §5 | L170–L170 | referenced_unresolved | unresolved |

定位符自检（逐字引文首行 + 实测偏移 + 出现次数）：

| asset_id | quote（首行，截断） | char span | 全文出现次数 | unique |
|---|---|---|---|---|
| A01 | `# IMO Polar Code Ice Stability Assessment — Mission m9105` | 0–7463 | 1 | yes |
| A02 | `\| Parameter \| Cargo Ship \| Polar Vessel \| Box Barge \|` | 721–1111 | 1 | yes |
| A03 | `\| Quantity \| Cargo Ship \| Polar Vessel \| Box Barge \|` | 2530–2820 | 1 | yes |
| A04 | `\| Quantity \| Cargo Ship \| Polar Vessel \| Box Barge \|` | 2841–3106 | 1 | yes |
| A05 | `\| Criterion \| Required (m·rad) \| Original \| Ice-Corrected \| Met? \|` | 3140–3405 | 1 | yes |
| A06 | `![GZ Curves](/tmp/fig1_gz_curves.png)` | 3666–3703 | 1 | yes |
| A07 | `![Ice Distribution](/tmp/fig2_ice_distribution.png)` | 3920–3971 | 1 | yes |
| A08 | `![Area Criteria](/tmp/fig3_area_criteria.png)` | 4133–4178 | 1 | yes |
| A09 | `![FSC Sensitivity](/tmp/fig4_fsc_sensitivity.png)` | 4329–4378 | 1 | yes |
| A10 | ``backend/api/ice_stability.py`` | 1408–1438 | 1 | yes |
| A11 | ``stability_core.py`` | 2385–2404 | 1 | yes |
| A12 | ``test_single_surface_analytical`` | 6044–6076 | 1 | yes |
| A13 | ``test_gz_wall_sided_formula`` | 6243–6271 | 1 | yes |
| A14 | ``test_area_0_40_equals_0_30_plus_30_40`` | 6456–6495 | 1 | yes |
| A15 | ``test_single_rectangular_tank_analytical`` | 6677–6718 | 1 | yes |
| A16 | `- IMO Polar Code Part II-A, Chapter 2 (Intact Stability)` | 5784–5840 | 1 | yes |
| A17 | `- IMO IS Code 2008, Part A, Chapter 2` | 5841–5878 | 1 | yes |
| A18 | `- ISO 19906:2019 (Arctic offshore structures — ice load reference)` | 5879–5946 | 1 | yes |

字段级证据表（值全部实测，可逐条复算）：

| manifest 字段 | 实测值 | 证据/复算方式 |
|---|---|---|
| `source.hash` / `source.source_hash` | `sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01` | `sha256(markdown.encode('utf-8'))` 本地复算，与契约 `sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01` 相等：True |
| `source.chars` / `bytes_utf8` / `lines` | 7463 / 7585 / 212 | `len(markdown)`、`len(markdown.encode('utf-8'))`、`markdown.split(chr(10))` |
| `source.title` | IMO Polar Code Ice Stability Assessment — Complete Implementation | `GET /tensor/reports/10618` record 字段；与契约 title 相等：True |
| `source.scenario_key` + `source.markdown_node` | `p485w1-n07-spp-ice-stability` / `p485w1-n07-spp-ice-stability` | record 字段 与 markdown 第 5 行 `**Node**: …` 双源一致：True |
| `counts.assets` / `by_class` / `by_resolution` | 18 / {"report_document": 1, "data_table:4col": 3, "data_table:5col": 1, "figure_reference": 4, "source_code_reference": 2, "test_reference": 4, "standard_reference": 3} / {"resolved_in_source": 5, "referenced_unresolved": 13} | 对 `assets[*].asset_class` 与 `.resolution` 的聚合计数 |
| `integrity.quote_uniqueness` | 18/18 locator quotes occur exactly once in the source markdown | verify 阶段二次独立 fetch 后逐条 `count(quote)==1` 复算 |
| `source.attachment_endpoint_probes` | figures HTTP 404 / artifacts HTTP 404 | 对平台两个附件端点各发一次 GET 并记录状态码 |

hash/chars 上游出处：hash/chars 来自 `GET /tensor/reports/10618` 的 `markdown` 字节（7585 bytes）；
title/scenario_key/mission_id 来自同一次 fetch 的 record 字段；`IMO Polar Code Ice Stability Assessment — Complete Implementation` 与契约 title 一致：
**True**；scenario `p485w1-n07-spp-ice-stability` 与契约一致：**True**。

## ⑤ 注意点与局限

1. **4 张图全部为 referenced_unresolved**：报告里写的是本机临时路径（`/tmp/fig1_gz_curves.png` 等），交付主机上
   `os.path.exists` 为假，平台也没有图字节端点（上面两条 404）。record 里只剩 `name/caption` 元数据。
   → 图**不能**被下游当可复现工件消费；重生成需 ship-performance-platform 的绘图脚本，超出本包范围。
2. **一处跨节数值巧合（只登记，不裁决）**：§3 Ice Accretion 表 Polar Vessel 列 `Total ice mass (kg)` = 2700；
   §6 criterion (a) 的算例写 `m = ρ×h×A = 900×0.03×100 = 2700 kg`。两者数值相同，但 §1 参数表里
   Polar Vessel 是 `h_ice (mm)`=50 / `ρ_ice (kg/m³)`=1000，而算例用的是 900 / 0.03（与 Cargo Ship、Box Barge 的
   ρ_ice=900、h_ice=30 一致），原文未标明该算例对应哪条船。→ 本包只登记两个可定位的数字（A04 表 / A12 测试标识所在段），
   一致性判定属抽取与审查工序，`claims` 保持为空。
3. **`stability_core.py`/`backend/api/ice_stability.py` 不可见**：它们在 ship-performance-platform 仓，
   本交付树（TensorKnowledge）无此路径，故登记为 referenced_unresolved，**没有跨仓读取**（边界纪律）。
4. **测试标识只到"名字 + 一行断言"粒度**：`test_*` 的执行证据在原文里是自述（原文 §5 "36 tests"、§6(e) "36 tests passed, 99% coverage"），
   本包不复制为事实，不产生 verified 标记。
5. **上游 schema 的两个缺陷（已规避，未改）**：`schemas/asset_manifest.v1.schema.json` 里 `package_id`/`report_id`
   是 `const wp-448-01`/`const 448`，跨包复用必须重绑；其 description 声称 `kf_result.v1.schema.json`
   "NOT present in this worktree"，实际该文件存在（本次信封校验即用它）——描述已过期。
6. **可复现性策略**：`generated_at` 固定取自源报告 record 的 `created_at`（可用环境变量 `KF_BUILD_TIMESTAMP` 覆盖），
   `kf_result.provenance.emitted_at` 与之相同，故重复执行 `build/envelope/result` 的 manifest / envelope / result.md
   **逐字节不变**（已实测连续两次 `all` 的 sha256 相同）。`verification.json` 的 `checked_at` 仍记真实时间——它是审计日志，不是产物。
7. **overlap 说明**：A01（整篇文档，span 0…7463）与其它资产的 span 必然重叠，这是"文档本体是资产"的语义结果，不是定位错误。

## ⑥ 自检：逐条对照 acceptance

**偏差/误差判定（关键量 vs 基准，逐项）**

| 关键量 | 本包实测 | 基准（来源） | 偏差 | 是否 <3% |
|---|---|---|---|---|
| source markdown sha256 | `sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01` | 契约 `source_hash`（work-package YAML） | 0 bit（逐字节相等） | ✓ |
| source chars | 7463 | 契约 `chars` = 7463 | 0 | ✓ |
| 资产定位符可解析率 | 18/18 | acceptance: 100% 可解析 | 0 | ✓ |
| 逐字引文唯一率 | 18/18 | acceptance: 唯一 | 0 | ✓ |
| 资产 id 重复数 | 0 | acceptance: 无重复 | 0 | ✓ |

本工序不产生物理量或数值解，因此**没有解析解/实验/文献基准可比**——按"无基准须声明原因"如实声明：
可比的只有身份类量（哈希、字符数、定位符可解析率），其偏差只能取 0 或非 0（哈希恒等），
百分比误差门槛在这里不适用；上表仍按纪律列百分比口径（全为 0%）。不把"结构门通过"说成"数值精度达标"。

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✓ | manifest + envelope 均 `json.load` 通过 |
| schema_pass | ✓ | asset_manifest.v1.schema.json（const 内存重绑）+ kf_result.v1.schema.json 双通过，0 error |
| source_locator_resolvable | ✓ | 第二次独立 fetch 逐条复核：`live_md.count(quote)==1` 且 `live_md[start:end]==quote` |
| source_hash_matches | ✓ | 复算 hash == envelope == manifest == 契约 |
| no_duplicate_ids | ✓ | 18 个 id 全互异 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims 为空数组（契约允许），空集上真值 |
| no_claim_marked_verified（附加） | ✓ | 未产出任何 verified 标记 |
| chars 与契约一致（附加） | ✓ | 实测 7463 vs 契约 7463 |

逐项明细（verify 的输出原文）：

- **valid_json**: asset_manifest.json and kf_result.json both parsed by json.load → ✓
- **schema_pass**: schemas/asset_manifest.v1.schema.json (package_id/report_id consts re-bound in memory for this package; upstream file untouched) -> 0 error(s); schemas/kf_result.v1.schema.json -> 0 error(s) → ✓
- **source_locator_resolvable**: 18/18 locators re-resolved against a second live fetch (verbatim substring == recorded char span, quote unique) → ✓
- **source_hash_matches**: independent re-fetch hash sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01 == envelope sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01 == manifest 19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01 == contract sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01 → ✓
- **no_duplicate_ids**: 18 asset ids, 18 distinct, duplicates=none → ✓
- **all_claims_have_evidence_or_explicit_unresolved_status**: claims=0 (empty by contract, objective.classify_report_type=false); vacuously satisfied, reason recorded in integrity.claims_empty_reason → ✓
- **no_claim_marked_verified**: status enum in schema has no 'verified' member; claims list empty -> nothing to mark → ✓
- **source_chars_match_contract**: measured chars=7463, contract chars=7463, live chars=7463 → ✓
- **markdown_node_matches_scenario**: markdown '**Node**:' line = 'p485w1-n07-spp-ice-stability' == record scenario_key 'p485w1-n07-spp-ice-stability' == contract 'p485w1-n07-spp-ice-stability' → ✓

无失败项则如上全 PASS；若有 FAIL 会在此如实保留（本单为 True）。

repro_cmd:

```
# 一键复跑（工作树根）
python3 scripts/kf_wp10618_01_register.py all
# 逐段复跑
python3 scripts/kf_wp10618_01_register.py build && python3 scripts/kf_wp10618_01_register.py envelope \
  && python3 scripts/kf_wp10618_01_register.py verify && python3 scripts/kf_wp10618_01_register.py result \
  && python3 scripts/kf_wp10618_01_register.py figure
```

## 结果信封（唯一 JSON 块）

```json
{
  "package_id": "wp-10618-01",
  "task_type": "01-asset-registration",
  "report_id": "10618",
  "provenance": {
    "source_hash": "sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01",
    "source_field": "markdown",
    "source_uri": "tensor://reports/10618",
    "producer": "kf-worker/m15687",
    "emitted_at": "2026-11-10T07:48:02.653428+00:00",
    "emitted_at_policy": "== manifest.generated_at (deterministic, see manifest.generated_at_policy)",
    "notes": "01-asset-registration: 18 assets registered, claims empty by contract; no verified marks emitted (verification is the platform gate's job)."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-10618-01",
      "task_type": "01-asset-registration",
      "report_id": "10618",
      "lane": "C",
      "generated_at": "2026-11-10T07:48:02.653428+00:00",
      "generated_at_policy": "pinned to record.created_at (overridable with KF_BUILD_TIMESTAMP) so that re-running this script is byte-identical -- no wall-clock drift",
      "producer": "kf-worker/m15687",
      "source": {
        "uri": "tensor://reports/10618",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01",
        "source_hash": "sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01",
        "contract_hash": "sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01",
        "hash_matches_contract": true,
        "chars": 7463,
        "bytes_utf8": 7585,
        "contract_chars": 7463,
        "chars_matches_contract": true,
        "lines": 212,
        "has_trailing_newline": true,
        "title": "IMO Polar Code Ice Stability Assessment — Complete Implementation",
        "scenario_key": "p485w1-n07-spp-ice-stability",
        "mission_id": 9105,
        "status": "published",
        "tags": [
          "imo-polar-code",
          "ice-stability",
          "gz-curve",
          "free-surface",
          "ship-stability"
        ],
        "contract_title": "IMO Polar Code Ice Stability Assessment — Complete Implementation",
        "title_matches_contract": true,
        "contract_scenario_key": "p485w1-n07-spp-ice-stability",
        "scenario_matches_contract": true,
        "platform_figures": [
          {
            "name": "fig1_gz_curves",
            "caption": "Fig1 Gz Curves"
          },
          {
            "name": "fig2_ice_distribution",
            "caption": "Fig2 Ice Distribution"
          },
          {
            "name": "fig3_area_criteria",
            "caption": "Fig3 Area Criteria"
          },
          {
            "name": "fig4_fsc_sensitivity",
            "caption": "Fig4 Fsc Sensitivity"
          }
        ],
        "fetched_via": "GET /api/v1/tensor/reports/10618",
        "attachment_endpoint_probes": {
          "figures": {
            "path": "tensor/reports/10618/figures",
            "http_status": 404,
            "body_present": false
          },
          "artifacts": {
            "path": "tensor/reports/10618/artifacts",
            "http_status": 404,
            "body_present": false
          }
        },
        "markdown_node": "p485w1-n07-spp-ice-stability",
        "node_matches_contract_scenario": true,
        "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based (a single trailing newline does not create a phantom line); char spans are half-open [start_char, end_char) over the UTF-8-decoded markdown"
      },
      "counts": {
        "assets": 18,
        "by_class": {
          "report_document": 1,
          "data_table:4col": 3,
          "data_table:5col": 1,
          "figure_reference": 4,
          "source_code_reference": 2,
          "test_reference": 4,
          "standard_reference": 3
        },
        "by_resolution": {
          "resolved_in_source": 5,
          "referenced_unresolved": 13
        },
        "resolved_in_source": 5,
        "referenced_unresolved": 13,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "report_document",
          "label": "report 10618 markdown (whole document)",
          "in_report_section": "document",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 7463,
            "start_line": 1,
            "end_line": 212,
            "quote": "# IMO Polar Code Ice Stability Assessment — Mission m9105",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(markdown.encode('utf-8')) recomputed locally and compared with contract.source_hash",
            "result": "resolved"
          },
          "note": "chars=7463 bytes_utf8=7585; hash == contract hash (see source.hash_matches_contract)"
        },
        {
          "asset_id": "A02",
          "asset_class": "data_table:4col",
          "label": "table #1 (lines 21-31)",
          "in_report_section": "Ship Parameters",
          "locator": {
            "method": "char_span",
            "start_char": 721,
            "end_char": 1111,
            "start_line": 21,
            "end_line": 31,
            "quote": "| Parameter | Cargo Ship | Polar Vessel | Box Barge |\n|-----------|-----------|--------------|-----------|\n| L (m) | 150.0 | 80.0 | 100.0 |\n| B (m) | 24.0 | 16.0 | 20.0 |\n| T (m) | 8.0 | 5.5 | 6.0 |\n| D (m) | 14.0 | 9.0 | 10.0 |\n| Δ (tonnes) | 20000 | 5000 | 12000 |\n| Cb | 0.70 | 0.65 | 1.00 |\n| KG (m) | 7.0 | 4.5 | 5.0 |\n| h_ice (mm) | 30 | 50 | 30 |\n| ρ_ice (kg/m³) | 900 | 1000 | 900 |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim block re-found at measured char span; uniqueness counted",
            "result": "resolved"
          },
          "note": "rows=11 (header+separator+9 data rows)"
        },
        {
          "asset_id": "A03",
          "asset_class": "data_table:4col",
          "label": "table #2 (lines 83-89)",
          "in_report_section": "Hydrostatics",
          "locator": {
            "method": "char_span",
            "start_char": 2530,
            "end_char": 2820,
            "start_line": 83,
            "end_line": 89,
            "quote": "| Quantity | Cargo Ship | Polar Vessel | Box Barge |\n|----------|-----------|--------------|-----------|\n| KB (m) | 4.106 | 2.962 | 3.000 |\n| BM (m) | 6.085 | 4.242 | 5.556 |\n| KM (m) | 10.191 | 7.204 | 8.556 |\n| GM_orig (m) | 3.191 | 2.704 | 3.556 |\n| GM_corr (m) | 2.690 | 2.515 | 3.522 |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim block re-found at measured char span; uniqueness counted",
            "result": "resolved"
          },
          "note": "rows=7 (header+separator+5 data rows)"
        },
        {
          "asset_id": "A04",
          "asset_class": "data_table:4col",
          "label": "table #3 (lines 93-98)",
          "in_report_section": "Ice Accretion",
          "locator": {
            "method": "char_span",
            "start_char": 2841,
            "end_char": 3106,
            "start_line": 93,
            "end_line": 98,
            "quote": "| Quantity | Cargo Ship | Polar Vessel | Box Barge |\n|----------|-----------|--------------|-----------|\n| Total ice mass (kg) | 3888 | 2700 | 2295 |\n| Total ice weight (kN) | 38.1 | 26.5 | 22.5 |\n| δKG (mm) | 33.7 | 55.7 | 5.7 |\n| FSC (m) | 0.467 | 0.133 | 0.000 |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim block re-found at measured char span; uniqueness counted",
            "result": "resolved"
          },
          "note": "rows=6 (header+separator+4 data rows)"
        },
        {
          "asset_id": "A05",
          "asset_class": "data_table:5col",
          "label": "table #4 (lines 102-106)",
          "in_report_section": "Area Criteria (Cargo Ship)",
          "locator": {
            "method": "char_span",
            "start_char": 3140,
            "end_char": 3405,
            "start_line": 102,
            "end_line": 106,
            "quote": "| Criterion | Required (m·rad) | Original | Ice-Corrected | Met? |\n|-----------|-----------------|----------|---------------|------|\n| Area 0°-30° | 0.055 | 0.218 | 0.198 | ✓ |\n| Area 0°-40° | 0.090 | 0.352 | 0.322 | ✓ |\n| Area 30°-40° | 0.030 | 0.134 | 0.124 | ✓ |",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim block re-found at measured char span; uniqueness counted",
            "result": "resolved"
          },
          "note": "rows=5 (header+separator+3 data rows)"
        },
        {
          "asset_id": "A06",
          "asset_class": "figure_reference",
          "label": "GZ Curves",
          "in_report_section": "§4",
          "locator": {
            "method": "char_span",
            "start_char": 3666,
            "end_char": 3703,
            "start_line": 121,
            "end_line": 121,
            "quote": "![GZ Curves](/tmp/fig1_gz_curves.png)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('/tmp/fig1_gz_curves.png') on the delivery host",
            "result": "absent"
          },
          "note": "platform record metadata: GET /tensor/reports/10618/figures -> HTTP 404; only name/caption metadata is exposed, no bytes"
        },
        {
          "asset_id": "A07",
          "asset_class": "figure_reference",
          "label": "Ice Distribution",
          "in_report_section": "§4",
          "locator": {
            "method": "char_span",
            "start_char": 3920,
            "end_char": 3971,
            "start_line": 127,
            "end_line": 127,
            "quote": "![Ice Distribution](/tmp/fig2_ice_distribution.png)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('/tmp/fig2_ice_distribution.png') on the delivery host",
            "result": "absent"
          },
          "note": "platform record metadata: GET /tensor/reports/10618/figures -> HTTP 404; only name/caption metadata is exposed, no bytes"
        },
        {
          "asset_id": "A08",
          "asset_class": "figure_reference",
          "label": "Area Criteria",
          "in_report_section": "§4",
          "locator": {
            "method": "char_span",
            "start_char": 4133,
            "end_char": 4178,
            "start_line": 133,
            "end_line": 133,
            "quote": "![Area Criteria](/tmp/fig3_area_criteria.png)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('/tmp/fig3_area_criteria.png') on the delivery host",
            "result": "absent"
          },
          "note": "platform record metadata: GET /tensor/reports/10618/figures -> HTTP 404; only name/caption metadata is exposed, no bytes"
        },
        {
          "asset_id": "A09",
          "asset_class": "figure_reference",
          "label": "FSC Sensitivity",
          "in_report_section": "§4",
          "locator": {
            "method": "char_span",
            "start_char": 4329,
            "end_char": 4378,
            "start_line": 139,
            "end_line": 139,
            "quote": "![FSC Sensitivity](/tmp/fig4_fsc_sensitivity.png)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists('/tmp/fig4_fsc_sensitivity.png') on the delivery host",
            "result": "absent"
          },
          "note": "platform record metadata: GET /tensor/reports/10618/figures -> HTTP 404; only name/caption metadata is exposed, no bytes"
        },
        {
          "asset_id": "A10",
          "asset_class": "source_code_reference",
          "label": "backend/api/ice_stability.py",
          "in_report_section": "§2",
          "locator": {
            "method": "char_span",
            "start_char": 1408,
            "end_char": 1438,
            "start_line": 46,
            "end_line": 46,
            "quote": "`backend/api/ice_stability.py`",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(<repo root>/backend/api/ice_stability.py) in the TensorKnowledge delivery worktree",
            "result": "absent"
          },
          "note": "owned by ship-performance-platform, not by the delivery repo; content therefore not inspectable from here (no cross-repo read attempted)"
        },
        {
          "asset_id": "A11",
          "asset_class": "source_code_reference",
          "label": "stability_core.py",
          "in_report_section": "§2",
          "locator": {
            "method": "char_span",
            "start_char": 2385,
            "end_char": 2404,
            "start_line": 74,
            "end_line": 74,
            "quote": "`stability_core.py`",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "os.path.exists(<repo root>/stability_core.py) in the TensorKnowledge delivery worktree",
            "result": "absent"
          },
          "note": "owned by ship-performance-platform, not by the delivery repo; content therefore not inspectable from here (no cross-repo read attempted)"
        },
        {
          "asset_id": "A12",
          "asset_class": "test_reference",
          "label": "test_single_surface_analytical",
          "in_report_section": "§6",
          "locator": {
            "method": "char_span",
            "start_char": 6044,
            "end_char": 6076,
            "start_line": 178,
            "end_line": 178,
            "quote": "`test_single_surface_analytical`",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "test body/harness is not part of report markdown nor of this worktree",
            "result": "unresolved"
          },
          "note": "only the identifier and its one-line assertion are present in the source; no executable artefact registered"
        },
        {
          "asset_id": "A13",
          "asset_class": "test_reference",
          "label": "test_gz_wall_sided_formula",
          "in_report_section": "§6",
          "locator": {
            "method": "char_span",
            "start_char": 6243,
            "end_char": 6271,
            "start_line": 183,
            "end_line": 183,
            "quote": "`test_gz_wall_sided_formula`",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "test body/harness is not part of report markdown nor of this worktree",
            "result": "unresolved"
          },
          "note": "only the identifier and its one-line assertion are present in the source; no executable artefact registered"
        },
        {
          "asset_id": "A14",
          "asset_class": "test_reference",
          "label": "test_area_0_40_equals_0_30_plus_30_40",
          "in_report_section": "§6",
          "locator": {
            "method": "char_span",
            "start_char": 6456,
            "end_char": 6495,
            "start_line": 188,
            "end_line": 188,
            "quote": "`test_area_0_40_equals_0_30_plus_30_40`",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "test body/harness is not part of report markdown nor of this worktree",
            "result": "unresolved"
          },
          "note": "only the identifier and its one-line assertion are present in the source; no executable artefact registered"
        },
        {
          "asset_id": "A15",
          "asset_class": "test_reference",
          "label": "test_single_rectangular_tank_analytical",
          "in_report_section": "§6",
          "locator": {
            "method": "char_span",
            "start_char": 6677,
            "end_char": 6718,
            "start_line": 193,
            "end_line": 193,
            "quote": "`test_single_rectangular_tank_analytical`",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "test body/harness is not part of report markdown nor of this worktree",
            "result": "unresolved"
          },
          "note": "only the identifier and its one-line assertion are present in the source; no executable artefact registered"
        },
        {
          "asset_id": "A16",
          "asset_class": "standard_reference",
          "label": "IMO Polar Code Part II-A, Chapter 2 (Intact Stability)",
          "in_report_section": "§5",
          "locator": {
            "method": "char_span",
            "start_char": 5784,
            "end_char": 5840,
            "start_line": 168,
            "end_line": 168,
            "quote": "- IMO Polar Code Part II-A, Chapter 2 (Intact Stability)",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external standard document: not attached to the report and not in this worktree",
            "result": "unresolved"
          },
          "note": "citation located verbatim; the standard text itself is out of scope for registration and is not asserted here"
        },
        {
          "asset_id": "A17",
          "asset_class": "standard_reference",
          "label": "IMO IS Code 2008, Part A, Chapter 2",
          "in_report_section": "§5",
          "locator": {
            "method": "char_span",
            "start_char": 5841,
            "end_char": 5878,
            "start_line": 169,
            "end_line": 169,
            "quote": "- IMO IS Code 2008, Part A, Chapter 2",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external standard document: not attached to the report and not in this worktree",
            "result": "unresolved"
          },
          "note": "citation located verbatim; the standard text itself is out of scope for registration and is not asserted here"
        },
        {
          "asset_id": "A18",
          "asset_class": "standard_reference",
          "label": "ISO 19906:2019 (Arctic offshore structures — ice load reference)",
          "in_report_section": "§5",
          "locator": {
            "method": "char_span",
            "start_char": 5879,
            "end_char": 5946,
            "start_line": 170,
            "end_line": 170,
            "quote": "- ISO 19906:2019 (Arctic offshore structures — ice load reference)\n",
            "unique": true,
            "occurrences": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external standard document: not attached to the report and not in this worktree",
            "result": "unresolved"
          },
          "note": "citation located verbatim; the standard text itself is out of scope for registration and is not asserted here"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "18/18 locator quotes occur exactly once in the source markdown",
        "quote_uniqueness_all": true,
        "hash_recomputed_locally": "sha256:19c4e1d87eb2c923fd346b060dc3b46c657691080b8600a1305e280f7a5bfd01",
        "hash_matches_contract": true,
        "claim_extraction_performed": false,
        "claims_empty_reason": "objective.classify_report_type=false and this package is 01-asset-registration only: no extraction, no forced claims",
        "verified_marks_emitted": false
      }
    }
  },
  "claims": []
}
```
