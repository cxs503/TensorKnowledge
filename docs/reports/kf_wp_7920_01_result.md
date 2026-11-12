# KF-RESULT wp-7920-01

**工作包**: `wp-7920-01` · **task_type**: `01-asset-registration` · **report_id**: `7920` · **lane**: C · **delivery**: TensorKnowledge (draft)

## ① 本工序做了什么

对 report_id=7920《IN154-P4 混合推进能量管理（电池-柴油并联）验证：功率分配/峰值削减/负荷优化/能量平衡闭环》执行**资产登记**（不做抽取、不生成 claim、不标 verified）：

1. **确认源资产身份**：`tensor://reports/7920` 的 `markdown` 字段，UTF-8 字节 **10592 B** / **6421 字符**，sha256 = `sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b`，与工作包契约 `source_hash` **逐字节一致**（脚本内不相等即 `SystemExit`，不产出半成品）。
2. **清点可解析的附件/工件**：共登记 **19** 个资产 = 1 源资产 + 5 条平台图元数据 + 13 条正文路径/模块引用。
3. **逐条给定位**（1 基行号 + 该行逐字引文 + 字符区间），并对每条**尝试解析**：只在交付工作树 TensorKnowledge 内判定 resolved，工作树外一律 unresolved 并写明原因。
4. **补充证据（非权威）**：对正文引用再做一次只读探针，看生产仓 `ship-performance-platform` 的本地检出里是否存在该文件（记录字节数，状态不进 resolution 字段，避免把跨仓信息当成本单的解析结论）。
5. `claims` 按契约 notes 保持**空数组**；全流程无 `verified` 标记（verification 由平台门计算）。

资产状态分布：

| asset_class | 数量 |
|---|---|
| data_artifact_reference | 4 |
| embedded_figure_metadata | 5 |
| figure_reference | 5 |
| module_reference | 2 |
| report_markdown | 1 |
| source_code_reference | 2 |

| resolution.status | 数量 |
|---|---|
| metadata_only | 5 |
| resolved | 1 |
| unresolved | 13 |

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET $TENSOR_API_BASE/tensor/reports/7920`（Bearer token，由 `$TENSOR_AGENT_USER`/`$TENSOR_AGENT_PASS` 登录换得）。本机 `psql -d tensorplatform` 直读 `tensor_reports` 被拒（`permission denied for table tensor_reports`），因此**唯一取源通道是平台 API**；这一点如实记录，不掩饰。
2. **定身份**：对 `markdown` 的 UTF-8 字节做 sha256，与契约 `source_hash`(`6e60d3f3ab63e255…`) 及契约 `chars=6421` 双向比对，任一不符即中止。
3. **扫描引用**（四条正则，全部只读原文，不猜测、不补全）：
   - `!\[alt\](path)` → `markdown_image`；
   - 反引号内的路径 token（可选 `:line` / `:l1-l2` 引脚）→ `inline_code_path`，按扩展名分类；
   - 反引号外的裸路径 token → `bare_path`；
   - 反引号内的点号模块名（如 `reference.dp_optimal`）→ `module_reference`（不是文件，单列一类，避免与文件路径混淆）。
4. **去重粒度**：资产按 **(path, markdown_line) 出现级** 标识；同一文件出现在不同行=不同 asset_id，各带自己的引文。去重视图见 `counts.distinct_referenced_paths = 12`。
5. **解析**：`os.path.isfile(<worktree>/path)`，并做**越界防护**（`resolve()` 后必须以工作树为前缀，否则直接判 unresolved，不得读工作树外文件冒充 resolved）。
6. **平台图**：`figures` 元数据逐条按 `name`+`caption` **逐字**回抄进 locator，`verify` 时再与实时 `GET` 结果比对，防止清单与平台记录漂移。
7. **产物**：`asset_manifest.json`（主产物）→ `kf_result.json`（信封，`source_hash` 用**重新拉取的实时字节**重算，与清单声明不一致即中止）→ `verification.json`（独立复算 6 项 acceptance + 3 项附加项）→ 本报告（表格与 json 块**全部由脚本从清单回读生成**，零手抄）。
8. **关键设置**：纯 Python 标准库（urllib/hashlib/json/re），无第三方依赖；幂等，可重复运行；`_guard_out_dir` 拒绝把本包产物写进别的包目录（互不覆盖的机器级保证）。

一键复跑（唯一入口）：

```bash
python3 scripts/kf/register_assets.py build result report verify --package-id wp-7920-01
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7920-01/asset_manifest.json` | 主产物：19 资产 + provenance + 空 claims；24520 B，sha256 `65e38e8b9e781fc8bef474a1180feca0e258aa17597334a7c86f42a9d1324c56` |
| `docs/kf/wp-7920-01/kf_result.json` | 交付信封：package_id/task_type/report_id/provenance/outputs 五键，`source_hash` 实时重算绑定 |
| `docs/kf/wp-7920-01/verification.json` | 自校验：6 项 acceptance + 5 项附加项，`all_pass=True` |
| `tests/test_kf_register_assets.py` | 11 条不变式测试（信封 schema / 哈希绑定 / 引文逐字 / 引用召回 / 唯一 json 块 / 目录守卫） |
| `scripts/kf/register_assets.py` | 参数化资产登记器（build/result/report/verify 四动作 + 包注册表 + 目录守卫），本单新增 |
| `docs/reports/kf_wp_7920_01_result.md` | 本报告（六段式 + 唯一 json 块） |

## ④ 证据定位表（asset → 原文引文片段）

定位方案：`markdown_line`（1 基行号，`quote` = 该行原文逐字整行，`start_char/end_char` 给出字符区间，校验条件 `lines[line-1] == quote == md[start:end]` 且 `quote in md`）；`report_field`（`markdown` 整字段 / `figures[i]` 的 `name`+`caption`）。下表由脚本从清单回读生成，**无一条手抄**。

| asset_id | asset_class | resolution | 定位 | 原文引文（逐字） |
|---|---|---|---|---|
| `A00` | report_markdown | resolved | markdown(整个字段) | tensor://reports/7920#markdown |
| `A01` | embedded_figure_metadata | metadata_only | figures[0] | fig1_power_split_soc.png |
| `A02` | embedded_figure_metadata | metadata_only | figures[1] | fig2_peak_shaving.png |
| `A03` | embedded_figure_metadata | metadata_only | figures[2] | fig3_load_optimization.png |
| `A04` | embedded_figure_metadata | metadata_only | figures[3] | fig4_battery_and_criteria.png |
| `A05` | embedded_figure_metadata | metadata_only | figures[4] | fig5_efficiency_sensitivity.png |
| `A06` | source_code_reference | unresolved | L3 | > 本文件由 `backend/modules/hybrid_propulsion/report_md.py` 从 `artifacts/hybrid_propulsion/results.… |
| `A07` | data_artifact_reference | unresolved | L3 | > 本文件由 `backend/modules/hybrid_propulsion/report_md.py` 从 `artifacts/hybrid_propulsion/results.… |
| `A08` | module_reference | unresolved | L54 | - 参考解：SOC 网格 + 功率决策网格的**动态规划**（`reference.dp_optimal`），给出全局最优目标值，并对网格分辨率做灵敏度自证。 |
| `A09` | source_code_reference | unresolved | L56 | **工具链**：numpy（向量化 DP/积分）、scipy（无——DP 自实现）、matplotlib（图件）、FastAPI（端点）、pytest（回归）。全部判据由 `pipeline… |
| `A10` | figure_reference | unresolved | L115 | ![fig1_power_split_soc.png](artifacts/hybrid_propulsion/fig1_power_split_soc.png) |
| `A11` | figure_reference | unresolved | L119 | ![fig2_peak_shaving.png](artifacts/hybrid_propulsion/fig2_peak_shaving.png) |
| `A12` | figure_reference | unresolved | L123 | ![fig3_load_optimization.png](artifacts/hybrid_propulsion/fig3_load_optimization.png) |
| `A13` | figure_reference | unresolved | L127 | ![fig4_battery_and_criteria.png](artifacts/hybrid_propulsion/fig4_battery_and_criteria.png) |
| `A14` | figure_reference | unresolved | L131 | ![fig5_efficiency_sensitivity.png](artifacts/hybrid_propulsion/fig5_efficiency_sensitivity.png) |
| `A15` | data_artifact_reference | unresolved | L160 | **审计链**：`artifacts/hybrid_propulsion/results.json`（全部数值）、`timeseries_mixed_24h.csv`（24 h 时程，含 S… |
| `A16` | data_artifact_reference | unresolved | L160 | **审计链**：`artifacts/hybrid_propulsion/results.json`（全部数值）、`timeseries_mixed_24h.csv`（24 h 时程，含 S… |
| `A17` | data_artifact_reference | unresolved | L160 | **审计链**：`artifacts/hybrid_propulsion/results.json`（全部数值）、`timeseries_mixed_24h.csv`（24 h 时程，含 S… |
| `A18` | module_reference | unresolved | L160 | **审计链**：`artifacts/hybrid_propulsion/results.json`（全部数值）、`timeseries_mixed_24h.csv`（24 h 时程，含 S… |

正文引用在生产仓本地检出中的只读探针结果（**非权威**，仅用于区分"交付工作树里没有"与"哪里都没有"）：

| asset_id | 引用路径 | 生产仓检出 |
|---|---|---|
| `A06` | `backend/modules/hybrid_propulsion/report_md.py` | 未找到 |
| `A07` | `artifacts/hybrid_propulsion/results.json` | 未找到 |
| `A09` | `pipeline.py` | 未找到 |
| `A10` | `artifacts/hybrid_propulsion/fig1_power_split_soc.png` | 未找到 |
| `A11` | `artifacts/hybrid_propulsion/fig2_peak_shaving.png` | 未找到 |
| `A12` | `artifacts/hybrid_propulsion/fig3_load_optimization.png` | 未找到 |
| `A13` | `artifacts/hybrid_propulsion/fig4_battery_and_criteria.png` | 未找到 |
| `A14` | `artifacts/hybrid_propulsion/fig5_efficiency_sensitivity.png` | 未找到 |
| `A15` | `artifacts/hybrid_propulsion/results.json` | 未找到 |
| `A16` | `timeseries_mixed_24h.csv` | 未找到 |
| `A17` | `report.json` | 未找到 |

## ⑤ 注意点与局限

1. **只登记不抽取**：`claims` 为空数组是契约允许的完整结果（`objective.classify_report_type=false`，不做抽取）；本单不为凑指标造知识。
2. **解析边界**：本单只在交付工作树 TensorKnowledge 内判 resolved。报告的生产者是 `ship-performance-platform` 仓（`backend/modules/hybrid_propulsion/`、`artifacts/hybrid_propulsion/`），跨仓读取超出工作包边界，故正文引用一律 `unresolved` + 写明原因；生产仓检出探针只作补充，**不进** resolution 字段。
3. **图件只有元数据**：平台 `figures` 只存 `name`+`caption`，PNG 字节不在报告记录里；本单不复制字节、不假装有哈希，标 `metadata_only`。
4. **行号锚的脆弱性**：`markdown_line` 定位绑定**当前** source_hash 的字节；报告若被编辑（换行/措辞），旧清单必须重建——`verify` 会因 quote 不再是原行而直接失败，这是设计意图而非缺陷。
5. **重复引用**：按出现级登记会让同一文件出现多次（如 `results.json` 在 L3 与 L160 各一条），去重视图见 `distinct_referenced_paths`；不合并是为了每条引用都带自己的逐字锚点。
6. **无图声明**：本单是纯文档/登记工序，不产生场量或曲线，故不内嵌 PNG；报告正文图件属**上游产线节点**的产物（本单只登记其元数据）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 细节 |
|---|---|---|
| valid_json | ✅ | asset_manifest.json + kf_result.json both json.loads OK |
| schema_pass | ✅ | kf_result.v1 envelope=True manifest=True |
| source_locator_resolvable | ✅ | checked 19 locators; unresolvable=[] |
| source_hash_matches | ✅ | recomputed=6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b manifest=6e60d3f3ab63e2553858f7a08344e5c87e… |
| no_duplicate_ids | ✅ | assets=19 unique=19 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=0 violating=0 (empty array satisfies the item vacuously per contract notes) |

附加自检（契约约束项）：

| 项 | 结果 | 细节 |
|---|---|---|
| do_not_mark_claims_as_verified | ✅ | no 'verified' status anywhere |
| scope_single_report | ✅ | all products bound to report_id=7920 only |
| reference_recall_probe | ✅ | independent scanner found 15 distinct path-like tokens; uncovered=[] |
| quote_uniqueness_matches_measurement | ✅ | integrity.quote_uniqueness re-measured against the live markdown |
| contract_chars_match | ✅ | chars=6421 contract=6421 |

**回归测试**（不变式级，非"跑过就算过"）：`python3 -m pytest tests/test_kf_register_assets.py -q` → **11 passed**。断言内容：信封通过 `schemas/kf_result.v1.schema.json` 校验、`source_hash` 与清单/信封三方一致、每条 `markdown_line` 引文是原文子串且 `md[start:end] == lines[line-1] == quote`、独立粗扫描器零漏检、报告恰好一个 JSON 代码块且与 `kf_result.json` 逐字段相等、`_guard_out_dir` 拒绝跨包写入。

**结论**：`all_pass = True`，无失败项。若上游 source 被改写，`source_hash_matches` 与 `source_locator_resolvable` 会同步变红，属预期行为。

---

**交付信封（下方为全文唯一的 JSON 代码块，原样提交）：**

```json
{
  "package_id": "wp-7920-01",
  "task_type": "01-asset-registration",
  "report_id": "7920",
  "provenance": {
    "source_uri": "tensor://reports/7920",
    "source_field": "markdown",
    "source_hash": "sha256:6e60d3f3ab63e2553858f7a08344e5c87ea0c7275bceefbd16a9cd254493961b",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 6421,
    "source_bytes_utf8": 10592,
    "fetched_via": "GET /tensor/reports/7920",
    "generator": "scripts/kf/register_assets.py",
    "emitted_at": "2026-11-12T01:30:41.023700+00:00",
    "contract_version": "1.0"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-7920-01/asset_manifest.json",
      "sha256": "65e38e8b9e781fc8bef474a1180feca0e258aa17597334a7c86f42a9d1324c56",
      "bytes": 24520,
      "asset_count": 19,
      "claims": 0
    }
  },
  "claims": []
}
```
