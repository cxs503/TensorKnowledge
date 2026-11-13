# KF-RESULT wp-14137-01

本报告是工作包 `wp-14137-01`（task_type=`01-asset-registration`，lane C）的唯一结果信道。
登记对象=报告 `14137`（`tensor://reports/14137`，字段 `markdown`，7569 字符 /
12344 UTF-8 字节，sha256 `6f65040f0d3483ee5ca35f81c0fa4e5af147165e066e6c9c1cdb9a815faa8c30`）。**只登记资产，不做抽取、不做分类、不标 verified。**

## ① 本工序做了什么

1. 从平台 API 取回报告 14137 的 `markdown` 字段，本地重算 sha256 并与契约 `source_hash` 逐字比对
   （结果：6f65040f0d3483ee… 一致，字符数 7569 与契约 `input.chars` 一致）。
2. 从正文中解析出 24 条**被引用的资产**并逐条登记：类别（code_pointer×5, in_source_table×4, mission_ref×3, platform_table×2, code_symbol×1, test_file×1, data_artifact×1, sql_artifact×1, figure×1, cluster_job×1, code_constant×1, cluster_filesystem×1, bibliography×1, repro_command_block×1）、所在章节、
   字符区间 locator、解析判定（resolved_in_source=5 /
   referenced_unresolved=19 / declared_absent=0）。
3. 对每条资产跑一条**机器判据**（worktree 路径存在性 / 只读 SQL 计数 / 集群作业状态 / 平台 figures 字段 /
   地址抽取），判定结果与其理由一并写入 manifest——不可解析的**如实标 unresolved 并写原因**，不猜地址。
4. 产出 `asset_manifest.json` + 结果信封 `kf_result.v1`，并写 18 项独立验收机检（见 ⑥）。
5. `claims` 为空数组：契约 `objective.classify_report_type=false`、本工序无抽取，空数组是合法完整结果
   （schema 原话「零条=合法完整结果」），不为填指标造知识。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 工具 / 命令 | 关键设置 |
|---|---|---|
| 取源 | `python3 scripts/kf_fetch_14137.py` | Bearer 登录 env 凭据；只 GET `/tensor/reports/14137`，不写回源报告 |
| 登记 | `python3 scripts/kf_register_14137.py` | 每个 `quote` 从 markdown **切片**得到（锚点=唯一行 + 行跨度），写盘前校验 `quote` 是唯一子串；锚点不唯一/不存在则整单中止 |
| 证据判据 | 同上 `resolution_check()` | 判据类型见 ④ 表；DB 用只读 `select count(*)`；集群用 `run_cluster ps` 落盘到 `runs/wp-14137-01/cluster_cj974_probe.txt` |
| 验收 | `python3 scripts/kf_verify_14137.py`（`--offline --out <path>` = 断网复跑，另存文件不覆盖交付物） | 不复用登记脚本，独立重算：哈希三路（本地/字段/信封）+ 在线重取、locator 重切片、行号重算、id 去重、schema 校验 |
| 测试 | `python3 -m pytest tests/test_kf_wp14137_01.py -q` | 6 项断言（离线，不联网） |
| 图 | `python3 scripts/kf_figures_14137.py` | 数字全部从 manifest 读，不手抄 |

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-14137-01/asset_manifest.json` | 主产物：24 条资产、locator、resolution_check、counts、integrity（含 schema_pass 记录） |
| `runs/wp-14137-01/kf_result.wp-14137-01.json` | `kf_result.v1` 结果信封（本报告唯一 json 块的来源，二者内容一致） |
| `runs/wp-14137-01/report_14137.md` / `report_14137.json` | 源 markdown 与原始 API 载荷（字节级固定，便于复算哈希） |
| `runs/wp-14137-01/cluster_cj974_probe.txt` | 集群作业 cj974 状态探测原始输出（资产 A13 的判据依据） |
| `artifacts/wp-14137-01/acceptance.json` | 18 项 acceptance 机检逐条结果 |
| `artifacts/wp-14137-01/fig_asset_manifest.png` | 图 1（见 ④ 后） |
| `scripts/kf_fetch_14137.py` / `kf_register_14137.py` / `kf_verify_14137.py` / `kf_figures_14137.py` / `kf_publish_14137.py` | 一键复跑链 |
| `tests/test_kf_wp14137_01.py` | 契约不变量的 pytest 断言 |

## ④ 证据定位表（资产 → 原文引文片段）

locator 全部为 `char_span`，`md[start_char:end_char] == quote` 且 `quote` 在 markdown 中唯一（机检见 ⑥）。

| id | 类别 | 所在章节 | char 区间 (行) | 解析 / 判据 → 结果 | 引文首行（逐字） |
|---|---|---|---|---|---|
| A01 | code_pointer | `### 2.1 `src/tensordem/contact/rol` | [2281:2340] (L53–53) | referenced_unresolved / `worktree_path_exists` → unresolved | ### 2.1 `src/tensordem/contact/rolling_static.py`（新增，149 行 |
| A02 | code_pointer | `### 2.1 `src/tensordem/contact/rol` | [2756:2813] (L63–63) | referenced_unresolved / `worktree_path_exists` → unresolved | * 接入点：`clump_dem.py` 的 pair 与 wall 两条滚动分支（opt-in，默认仍为旧律）， |
| A03 | code_symbol | `### 2.1 `src/tensordem/contact/rol` | [2814:2869] (L64–64) | referenced_unresolved / `symbol_reference_only` → unresolved |   `ContactParams` 新增 `rolling_model` / `rolling_lever`。 |
| A04 | test_file | `### 2.2 验证（机器可判，`tests/test_rollin` | [2871:2932] (L66–66) | referenced_unresolved / `worktree_path_exists` → unresolved | ### 2.2 验证（机器可判，`tests/test_rolling_static.py`，**13 passed |
| A05 | code_pointer | `## 7 复现` | [6510:6602] (L171–171) | referenced_unresolved / `worktree_path_exists` → unresolved | python benchmarks/gap_dem_clump/run_round2_scan.py --case  |
| A06 | code_pointer | `## 7 复现` | [6657:6752] (L174–174) | referenced_unresolved / `worktree_path_exists` → unresolved | python benchmarks/gap_dem_clump/shard_round2.py --i 0 --n  |
| A07 | code_pointer | `## 5 注意点（踩坑，供下一轮）` | [5848:5946] (L147–148) | referenced_unresolved / `worktree_path_exists` → unresolved | 4. 前轮 `run_gap_dem_clump.py::main()` 死代码（payload 写在 `retur |
| A08 | data_artifact | `## 3 扫描结果（真数据；`artifacts/GAP-DEM-C` | [3775:3831] (L90–90) | referenced_unresolved / `worktree_path_exists` → unresolved | ## 3 扫描结果（真数据；`artifacts/GAP-DEM-CLUMP-R2/results.json`） |
| A09 | sql_artifact | `### 1.3 选型沉淀（①-③）` | [1773:1834] (L38–38) | referenced_unresolved / `worktree_path_exists` → unresolved | `artifacts/GAP-DEM-CLUMP-R2/oss_solutions_insert.sql` + 已入 |
| A10 | figure | `## 3 扫描结果（真数据；`artifacts/GAP-DEM-C` | [4588:4659] (L113–113) | referenced_unresolved / `platform_figures_field` → unresolved | 图：`artifacts/GAP-DEM-CLUMP-R2/gap_dem_clump_r2.png`（左：三配置  |
| A11 | platform_table | `### 1.3 选型沉淀（①-③）` | [1720:1834] (L37–38) | referenced_unresolved / `readonly_sql_count` → unresolved | `oss_solutions` 共 6 行（feature_slug=`GAP-DEM-CLUMP`，见 |
| A12 | platform_table | `### 1.1 开源横向（①-①）` | [362:534] (L17–17) | referenced_unresolved / `readonly_sql_count` → unresolved | \| `SELECT repo, license, methods FROM oss_inventory WHERE  |
| A13 | cluster_job | `## 7 复现` | [7027:7109] (L182–183) | referenced_unresolved / `cluster_job_state_probe` → unresolved | 6 路并行跑完 a/b ∈{1.0,1.5,2.0}×3 配置（a/b=3.0 与 seed=1 网格已递交集群 c |
| A14 | mission_ref | `# GAP-DEM-CLUMP · round 2 (m15028)` | [0:52] (L0–0) | referenced_unresolved / `platform_mission_id_field` → present | # GAP-DEM-CLUMP · round 2 (m15028) — 静态滚动阻力 + 形状效应验证 |
| A15 | mission_ref | `# GAP-DEM-CLUMP · round 2 (m15028)` | [197:305] (L6–7) | referenced_unresolved / `mission_id_reference_only` → unresolved | 前轮（m14996）honest-FAIL，未留 `fail_stage`/`failure_reason`；本轮把 |
| A16 | mission_ref | `## 5 注意点（踩坑，供下一轮）` | [5915:5946] (L148–148) | referenced_unresolved / `mission_id_reference_only` → unresolved |    m14681 修复，本轮沿用修复后的入口，不做重复工作。 |
| A17 | code_constant | `### 1.2 方法谱系（①-②，external_anchor 落` | [1569:1699] (L33–33) | referenced_unresolved / `symbol_reference_only` → unresolved | \| Zhou et al. (1999) *Physica A* 269:536–553 \| lifted-box  |
| A18 | cluster_filesystem | `### 1.1 开源横向（①-①）` | [535:635] (L18–18) | referenced_unresolved / `filesystem_reachability` → unresolved | \| 集群节点 `~/oss-cache`（n315/n330） \| 只有 LBM 包（Maarten-vd-Sand |
| A19 | bibliography | `### 1.2 方法谱系（①-②，external_anchor 落` | [967:1699] (L30–33) | referenced_unresolved / `address_extraction` → unresolved | \| Ai, Chen, Rotter, Ooi (2011) *Powder Technol.* 206:269–2 |
| A20 | in_source_table | `### 2.2 验证（机器可判，`tests/test_rollin` | [2934:3563] (L68–82) | resolved_in_source / `char_span_in_source_markdown` → resolved | \| id \| 判据 \| 实测 \| |
| A21 | in_source_table | `## 3 扫描结果（真数据；`artifacts/GAP-DEM-C` | [3932:4239] (L95–100) | resolved_in_source / `char_span_in_source_markdown` → resolved | \| a/b \| 匹配填充高度 h [m] \| n_particles \| 墙高 [m] \| 判定 \| |
| A22 | in_source_table | `## 4 误差判定（关键量 vs 基准，逐项）` | [4741:5159] (L120–127) | resolved_in_source / `char_span_in_source_markdown` → resolved | \| 量 \| 基准 \| 实测 \| 误差 \| <3%? \| |
| A23 | in_source_table | `## 附表：三配置有效/失效计数（程序生成）` | [7135:7315] (L187–191) | resolved_in_source / `char_span_in_source_markdown` → resolved | \| 配置 \| 有效算例 \| quiesced=false \| 有效 repose [deg] \| |
| A24 | repro_command_block | `## 7 复现` | [6504:6880] (L170–176) | resolved_in_source / `char_span_in_source_markdown` → resolved | # 单算例 |

图 1：`fig_asset_manifest.png` —— 左：24 条登记资产按类别与解析判定的分布；右：每条资产 locator 在 7569 字符源 markdown 中的字符区间（绿=源内可解析，红=引用但本工序不可解析）。

## ⑤ 注意点与局限

1. **19/24 条资产判为 referenced_unresolved，这是真相不是缺陷**：报告 14137 的代码/数据/图件都在
   TensorDEM 仓（`src/tensordem/contact/rolling_static.py`、`artifacts/GAP-DEM-CLUMP-R2/results.json` 等），
   本工作树是 TensorKnowledge 检出，契约又禁止改写外部仓产物 ⇒ 只登记路径，不解析版本（报告未给 commit hash）。
2. **平台表行数未能机检**：只读 `select count(*)` 被拒（`permission denied for table oss_solutions`），
   故 A11 的「6 行」、A12 的「218 行 / 140 个 feature_slug」只是**报告自报值**，登记为 unresolved，
   未升级为已核实。任何下游引用须注明「自报、未复核」。
3. **集群作业 cj974 仍 queued**（探测时点 656.8 min），报告自己声明「未回的数不引用」；本工序据此不给任何 a/b=3.0
   与 seed=1 的数值登记。
4. **图件有元数据无载荷**：平台 `figures` 字段只有 `name`+`caption`（`gap_dem_clump_r2.png`），无 `png_base64`；
   图件本体只在 TensorDEM 仓路径下 ⇒ A10 仍 unresolved。
5. **本工序不判定上游结论真伪**：报告 14137 自报 13 项内核测试通过、repose 低于文献带 22–37% 的 honest-FAIL、
   fail_stage=`repose_mass_matched_fill_infeasible`，这些仅作为**被登记的内容**存在于 ④ 表内嵌表格
   （A20–A23 四条 in_source_table），本工序既未复跑测试也未复核数值。zero-hand-transcription：所有引用由脚本切片。
6. **schema 口径**：`schemas/asset_manifest.v1.schema.json` 是 wp-448-01 写的仓内本地 schema，其
   `package_id`/`report_id`/`source.uri` 为 `const`。本工序**在内存中替换这三个身份常量**后校验并在
   `integrity.schema_pass` 显式记录（不改上游文件）；若平台侧 schema 更严，平台门为准。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 依据（机检输出摘要） |
|---|---|---|
| valid_json:asset_manifest | ✅ PASS | artifacts/wp-14137-01/asset_manifest.json parses |
| valid_json:kf_result | ✅ PASS | runs/wp-14137-01/kf_result.wp-14137-01.json parses |
| source_hash_matches:local_recompute | ✅ PASS | sha256(runs md)=6f65040f0d3483ee5ca35f81c0fa4e5af147165e066e6c9c1cdb9a815faa8c30 |
| source_hash_matches:manifest_field | ✅ PASS | manifest.source.hash |
| source_hash_matches:envelope_provenance | ✅ PASS | envelope.provenance.source_hash |
| source_hash_matches:platform_refetch | ✅ PASS | re-fetched from platform API |
| source_chars_matches_contract | ✅ PASS | len(markdown)=7569 contract=7569 |
| schema_pass | ✅ PASS | asset_manifest.v1 (identity consts substituted for this package) + kf_result.v1 both validate |
| source_locator_resolvable:quote_slices | ✅ PASS | 24 assets; md[start:end]==quote for all |
| source_locator_resolvable:quote_unique | ✅ PASS | every quote is a unique substring of the markdown |
| source_locator_resolvable:line_numbers_consistent | ✅ PASS | start_line/end_line recomputed from char offsets match |
| no_duplicate_ids | ✅ PASS | 24 asset ids, 24 unique |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ PASS | claims=0 (empty array is legitimate here: no extraction in task_type 01) |
| kf_result_claims_constraint | ✅ PASS | envelope claims=0 |
| envelope_outputs_equal_manifest | ✅ PASS | outputs['asset_manifest.json'] is byte-identical in content to the artifact file |
| envelope_identity | ✅ PASS | package_id/report_id/task_type fields |
| not_marked_verified | ✅ PASS | no asset carries a 'verified' label; registration only |
| counts_consistent | ✅ PASS | counts.by_resolution / counts.assets recomputed |

合计 **18/18 PASS**（`artifacts/wp-14137-01/acceptance.json`）。
另：`pytest tests/test_kf_wp14137_01.py -q` → 6 passed（测试跑的是 `--offline --out acceptance.offline.json`，
不覆盖本表的在线结果）。
若有失败项：本行如实写结果；本次运行无失败项，**未粉饰**（含 ⑤ 第 2 条 permission denied 已记为 unresolved 而非 pass）。

## 复现（一键）

```bash
cd <TensorKnowledge worktree>
python3 scripts/kf_fetch_14137.py            # 取源 + 校验 sha256（应打印 MATCH: True）
python3 scripts/kf_register_14137.py         # 登记 24 条资产 → artifacts/wp-14137-01/asset_manifest.json
python3 scripts/kf_verify_14137.py           # 18 项 acceptance 机检（--offline 可断网复跑）
python3 scripts/kf_figures_14137.py          # 图 1
python3 -m pytest tests/test_kf_wp14137_01.py -q
```

## 结果信封（全文唯一 json 代码块，机器门按此解析）

```json
{
  "package_id": "wp-14137-01",
  "task_type": "01-asset-registration",
  "report_id": "14137",
  "provenance": {
    "source_hash": "sha256:6f65040f0d3483ee5ca35f81c0fa4e5af147165e066e6c9c1cdb9a815faa8c30",
    "source_field": "markdown",
    "producer": "agent/m15782 wp-14137-01 (scripts/kf_fetch_14137.py + scripts/kf_register_14137.py)",
    "emitted_at": "2026-11-12T02:40:38+00:00",
    "notes": "sha256 本地重算并与契约 source_hash 逐字比对一致；assets 的 quote 均由脚本从 markdown 切片，逐条校验唯一子串；未做抽取、未标 verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-14137-01",
      "task_type": "01-asset-registration",
      "report_id": "14137",
      "source": {
        "uri": "tensor://reports/14137",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "6f65040f0d3483ee5ca35f81c0fa4e5af147165e066e6c9c1cdb9a815faa8c30",
        "chars": 7569,
        "bytes_utf8": 12344,
        "title": "GAP-DEM-CLUMP 第2轮：静态+形状感知滚动阻力（13项内核测试）与质量匹配 repose 扫描的 honest-FAIL 定位",
        "scenario_key": "dem_clump_shape_effect",
        "platform_figures": [
          {
            "name": "gap_dem_clump_r2.png",
            "caption": "角度自然坡角 vs 长径比（质量匹配，三配置）+ 形状效应 Δ 与 3° 判据"
          }
        ],
        "platform_tags": [
          "DEM",
          "clump",
          "rolling-resistance",
          "repose-angle",
          "shape-effect",
          "honest-FAIL"
        ]
      },
      "counts": {
        "assets": 24,
        "by_class": {
          "code_pointer": 5,
          "code_symbol": 1,
          "test_file": 1,
          "data_artifact": 1,
          "sql_artifact": 1,
          "figure": 1,
          "platform_table": 2,
          "cluster_job": 1,
          "mission_ref": 3,
          "code_constant": 1,
          "cluster_filesystem": 1,
          "bibliography": 1,
          "in_source_table": 4,
          "repro_command_block": 1
        },
        "by_resolution": {
          "referenced_unresolved": 19,
          "resolved_in_source": 5
        },
        "resolved_in_source": 5,
        "referenced_unresolved": 19,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "code_pointer",
          "label": "src/tensordem/contact/rolling_static.py（新增，149 行；静态 + 形状感知滚动律）",
          "in_report_section": "### 2.1 `src/tensordem/contact/rolling_static.py`（新增，149 行）",
          "locator": {
            "method": "char_span",
            "start_char": 2281,
            "end_char": 2340,
            "start_line": 53,
            "end_line": 53,
            "quote": "### 2.1 `src/tensordem/contact/rolling_static.py`（新增，149 行）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "src/tensordem/contact/rolling_static.py"
            ],
            "missing": [
              "src/tensordem/contact/rolling_static.py"
            ],
            "result": "unresolved",
            "host_probe_glob": "/root/tp-agent/work/*/.../rolling_static.py",
            "host_probe_hits": 42,
            "host_probe_sample": [
              "/root/tp-agent/work/m15028/src/tensordem/contact/rolling_static.py",
              "/root/tp-agent/work/m15061/src/tensordem/contact/rolling_static.py",
              "/root/tp-agent/work/m15145/src/tensordem/contact/rolling_static.py"
            ],
            "detail": "本工作树(TensorKnowledge)无此路径；报告未给 commit，故其它检出不能用于解析本报告的版本"
          },
          "note": "TensorDEM 仓内路径；报告未给 commit/分支，无法从 tensor://reports/14137 解析到具体版本"
        },
        {
          "asset_id": "A02",
          "asset_class": "code_pointer",
          "label": "clump_dem.py（pair 与 wall 两条滚动分支接入点）",
          "in_report_section": "### 2.1 `src/tensordem/contact/rolling_static.py`（新增，149 行）",
          "locator": {
            "method": "char_span",
            "start_char": 2756,
            "end_char": 2813,
            "start_line": 63,
            "end_line": 63,
            "quote": "* 接入点：`clump_dem.py` 的 pair 与 wall 两条滚动分支（opt-in，默认仍为旧律），",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "missing": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "result": "unresolved",
            "detail": "引用的相对路径属 TensorDEM 仓；本工作树无 src/ 与 artifacts/GAP-DEM-CLUMP-R2/，且契约禁止改写外部仓产物 ⇒ 只登记不解析"
          },
          "note": "TensorDEM 仓内引擎代码；无 commit 锚点"
        },
        {
          "asset_id": "A03",
          "asset_class": "code_symbol",
          "label": "ContactParams 新增 rolling_model / rolling_lever 两个参数",
          "in_report_section": "### 2.1 `src/tensordem/contact/rolling_static.py`（新增，149 行）",
          "locator": {
            "method": "char_span",
            "start_char": 2814,
            "end_char": 2869,
            "start_line": 64,
            "end_line": 64,
            "quote": "  `ContactParams` 新增 `rolling_model` / `rolling_lever`。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_reference_only",
            "symbol": "ContactParams 新增 rolling_model / rolling_lever 两个参数",
            "result": "unresolved",
            "detail": "报告只给符号名/常量名，未给文件+版本；本工序不猜测其定义位置"
          },
          "note": "符号级引用，无版本锚点，无法机器解析"
        },
        {
          "asset_id": "A04",
          "asset_class": "test_file",
          "label": "tests/test_rolling_static.py（13 项内核测试；报告自报 13 passed）",
          "in_report_section": "### 2.2 验证（机器可判，`tests/test_rolling_static.py`，**13 passed**）",
          "locator": {
            "method": "char_span",
            "start_char": 2871,
            "end_char": 2932,
            "start_line": 66,
            "end_line": 66,
            "quote": "### 2.2 验证（机器可判，`tests/test_rolling_static.py`，**13 passed**）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "tests/test_rolling_static.py"
            ],
            "missing": [
              "tests/test_rolling_static.py"
            ],
            "result": "unresolved",
            "host_probe_glob": "/root/tp-agent/work/*/.../test_rolling_static.py",
            "host_probe_hits": 0,
            "host_probe_sample": [],
            "detail": "本工作树(TensorKnowledge)无此路径；报告未给 commit，故其它检出不能用于解析本报告的版本"
          },
          "note": "TensorDEM 仓内测试文件；本工序只登记文件名与自报计数，未复跑（不冒充复验）"
        },
        {
          "asset_id": "A05",
          "asset_class": "code_pointer",
          "label": "benchmarks/gap_dem_clump/run_round2_scan.py（单算例 + 聚合入口）",
          "in_report_section": "## 7 复现",
          "locator": {
            "method": "char_span",
            "start_char": 6510,
            "end_char": 6602,
            "start_line": 171,
            "end_line": 171,
            "quote": "python benchmarks/gap_dem_clump/run_round2_scan.py --case ar=1.0,seed=0,config=coulomb/com \\",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "missing": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "result": "unresolved",
            "detail": "引用的相对路径属 TensorDEM 仓；本工作树无 src/ 与 artifacts/GAP-DEM-CLUMP-R2/，且契约禁止改写外部仓产物 ⇒ 只登记不解析"
          },
          "note": "TensorDEM 仓内基准脚本；无 commit 锚点"
        },
        {
          "asset_id": "A06",
          "asset_class": "code_pointer",
          "label": "benchmarks/gap_dem_clump/shard_round2.py（8 片分片入口）",
          "in_report_section": "## 7 复现",
          "locator": {
            "method": "char_span",
            "start_char": 6657,
            "end_char": 6752,
            "start_line": 174,
            "end_line": 174,
            "quote": "python benchmarks/gap_dem_clump/shard_round2.py --i 0 --n 8 --outdir artifacts/GAP-DEM-CLUMP-R2",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "missing": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "result": "unresolved",
            "detail": "引用的相对路径属 TensorDEM 仓；本工作树无 src/ 与 artifacts/GAP-DEM-CLUMP-R2/，且契约禁止改写外部仓产物 ⇒ 只登记不解析"
          },
          "note": "TensorDEM 仓内基准脚本；无 commit 锚点"
        },
        {
          "asset_id": "A07",
          "asset_class": "code_pointer",
          "label": "run_gap_dem_clump.py::main()（前轮死代码，m14681 已修）",
          "in_report_section": "## 5 注意点（踩坑，供下一轮）",
          "locator": {
            "method": "char_span",
            "start_char": 5848,
            "end_char": 5946,
            "start_line": 147,
            "end_line": 148,
            "quote": "4. 前轮 `run_gap_dem_clump.py::main()` 死代码（payload 写在 `return` 之后）已在\n   m14681 修复，本轮沿用修复后的入口，不做重复工作。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "missing": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "result": "unresolved",
            "detail": "引用的相对路径属 TensorDEM 仓；本工作树无 src/ 与 artifacts/GAP-DEM-CLUMP-R2/，且契约禁止改写外部仓产物 ⇒ 只登记不解析"
          },
          "note": "TensorDEM 仓内入口脚本；修复提交仅以任务号 m14681 指代，无 git hash"
        },
        {
          "asset_id": "A08",
          "asset_class": "data_artifact",
          "label": "artifacts/GAP-DEM-CLUMP-R2/results.json（扫描真数据）",
          "in_report_section": "## 3 扫描结果（真数据；`artifacts/GAP-DEM-CLUMP-R2/results.json`）",
          "locator": {
            "method": "char_span",
            "start_char": 3775,
            "end_char": 3831,
            "start_line": 90,
            "end_line": 90,
            "quote": "## 3 扫描结果（真数据；`artifacts/GAP-DEM-CLUMP-R2/results.json`）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "missing": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "result": "unresolved",
            "detail": "引用的相对路径属 TensorDEM 仓；本工作树无 src/ 与 artifacts/GAP-DEM-CLUMP-R2/，且契约禁止改写外部仓产物 ⇒ 只登记不解析"
          },
          "note": "TensorDEM 仓 artifacts 目录路径，未内嵌于报告；本工作树无此文件"
        },
        {
          "asset_id": "A09",
          "asset_class": "sql_artifact",
          "label": "artifacts/GAP-DEM-CLUMP-R2/oss_solutions_insert.sql（选型沉淀入库脚本）",
          "in_report_section": "### 1.3 选型沉淀（①-③）",
          "locator": {
            "method": "char_span",
            "start_char": 1773,
            "end_char": 1834,
            "start_line": 38,
            "end_line": 38,
            "quote": "`artifacts/GAP-DEM-CLUMP-R2/oss_solutions_insert.sql` + 已入库）：",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "paths": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "missing": [
              "src",
              "artifacts/GAP-DEM-CLUMP-R2"
            ],
            "result": "unresolved",
            "detail": "引用的相对路径属 TensorDEM 仓；本工作树无 src/ 与 artifacts/GAP-DEM-CLUMP-R2/，且契约禁止改写外部仓产物 ⇒ 只登记不解析"
          },
          "note": "TensorDEM 仓 artifacts 路径；本工作树无此文件"
        },
        {
          "asset_id": "A10",
          "asset_class": "figure",
          "label": "artifacts/GAP-DEM-CLUMP-R2/gap_dem_clump_r2.png（repose vs a/b + 形状效应 Δ）",
          "in_report_section": "## 3 扫描结果（真数据；`artifacts/GAP-DEM-CLUMP-R2/results.json`）",
          "locator": {
            "method": "char_span",
            "start_char": 4588,
            "end_char": 4659,
            "start_line": 113,
            "end_line": 113,
            "quote": "图：`artifacts/GAP-DEM-CLUMP-R2/gap_dem_clump_r2.png`（左：三配置 repose vs a/b",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figures_field",
            "platform_figures_count": 1,
            "metadata_name_match": true,
            "png_bytes_present": false,
            "result": "unresolved",
            "detail": "平台 figures 记录里有同名图件元数据（name+caption），但无 png_base64 字节；矢量内容只在 TensorDEM 仓 artifacts/ 下 ⇒ 地址仍不可由本报告解析"
          },
          "note": "图件以路径引用，报告内未内嵌 base64；平台 figures 字段为空（见 resolution_check）"
        },
        {
          "asset_id": "A11",
          "asset_class": "platform_table",
          "label": "平台表 oss_solutions（feature_slug=GAP-DEM-CLUMP 共 6 行）",
          "in_report_section": "### 1.3 选型沉淀（①-③）",
          "locator": {
            "method": "char_span",
            "start_char": 1720,
            "end_char": 1834,
            "start_line": 37,
            "end_line": 38,
            "quote": "`oss_solutions` 共 6 行（feature_slug=`GAP-DEM-CLUMP`，见\n`artifacts/GAP-DEM-CLUMP-R2/oss_solutions_insert.sql` + 已入库）：",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "readonly_sql_count",
            "sql": "select count(*) from oss_solutions where feature_slug='GAP-DEM-CLUMP'",
            "exit_code": 1,
            "stdout": "",
            "stderr": "ERROR:  permission denied for table oss_solutions",
            "result": "unresolved",
            "detail": "只读计数失败（权限不足），故报告自报行数不判 resolved"
          },
          "note": "报告断言已入库 6 行；本工序以只读 SQL 复核计数，权限不足（见 resolution_check），故不判 resolved"
        },
        {
          "asset_id": "A12",
          "asset_class": "platform_table",
          "label": "平台表 oss_inventory（报告称 218 行 / 140 个 feature_slug）",
          "in_report_section": "### 1.1 开源横向（①-①）",
          "locator": {
            "method": "char_span",
            "start_char": 362,
            "end_char": 534,
            "start_line": 17,
            "end_line": 17,
            "quote": "| `SELECT repo, license, methods FROM oss_inventory WHERE methods/summary/focus ILIKE {clump, multi-sphere, rolling resistance}` | **0 行**（表内共 218 行 / 140 个 feature_slug） |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "readonly_sql_count",
            "sql": "select count(*) from oss_inventory",
            "exit_code": 1,
            "stdout": "",
            "stderr": "ERROR:  permission denied for table oss_inventory",
            "result": "unresolved",
            "detail": "只读计数失败（权限不足），故报告自报行数不判 resolved"
          },
          "note": "只读复核被拒（见 resolution_check）；行数系报告自报"
        },
        {
          "asset_id": "A13",
          "asset_class": "cluster_job",
          "label": "集群作业 cj974（a/b=3.0 与 seed=1 网格，排队未回；未回的数不引用）",
          "in_report_section": "## 7 复现",
          "locator": {
            "method": "char_span",
            "start_char": 7027,
            "end_char": 7109,
            "start_line": 182,
            "end_line": 183,
            "quote": "6 路并行跑完 a/b ∈{1.0,1.5,2.0}×3 配置（a/b=3.0 与 seed=1 网格已递交集群 cj974，\n排队未回；未回的数**不引用**）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "cluster_job_state_probe",
            "probe_file": "runs/wp-14137-01/cluster_cj974_probe.txt",
            "observed": "queued -",
            "result": "unresolved",
            "detail": "作业未出结果 ⇒ 无工件可解析（报告亦声明未回的数不引用）"
          },
          "note": "作业未完成，无结果工件；查询时点状态见 resolution_check"
        },
        {
          "asset_id": "A14",
          "asset_class": "mission_ref",
          "label": "本轮任务锚 m15028",
          "in_report_section": "# GAP-DEM-CLUMP · round 2 (m15028) — 静态滚动阻力 + 形状效应验证",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 52,
            "start_line": 0,
            "end_line": 0,
            "quote": "# GAP-DEM-CLUMP · round 2 (m15028) — 静态滚动阻力 + 形状效应验证",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_mission_id_field",
            "record_mission_id": 15028,
            "matches_report_anchor": true,
            "result": "present",
            "detail": "记录字段 mission_id 与本行任务号一致；任务本体（执行历史/工件）不在报告内，故仍判 unresolved 级解析"
          },
          "note": "任务号引用，不是工件；本工序不解析任务库"
        },
        {
          "asset_id": "A15",
          "asset_class": "mission_ref",
          "label": "前轮 m14996（honest-FAIL，未留 fail_stage/failure_reason）",
          "in_report_section": "# GAP-DEM-CLUMP · round 2 (m15028) — 静态滚动阻力 + 形状效应验证",
          "locator": {
            "method": "char_span",
            "start_char": 197,
            "end_char": 305,
            "start_line": 6,
            "end_line": 7,
            "quote": "前轮（m14996）honest-FAIL，未留 `fail_stage`/`failure_reason`；本轮把失败点定位到\n**协议几何不可行**（§3），而不是\"没跑完\"，因此下一轮拿到的是可执行的重启条件。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "mission_id_reference_only",
            "result": "unresolved",
            "detail": "任务号是引用键不是工件；本工序不查询任务库（越界）"
          },
          "note": "任务号引用；前轮报告本体不在本工件范围内"
        },
        {
          "asset_id": "A16",
          "asset_class": "mission_ref",
          "label": "m14681（run_gap_dem_clump.py::main() 死代码修复任务）",
          "in_report_section": "## 5 注意点（踩坑，供下一轮）",
          "locator": {
            "method": "char_span",
            "start_char": 5915,
            "end_char": 5946,
            "start_line": 148,
            "end_line": 148,
            "quote": "   m14681 修复，本轮沿用修复后的入口，不做重复工作。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "mission_id_reference_only",
            "result": "unresolved",
            "detail": "任务号是引用键不是工件；本工序不查询任务库（越界）"
          },
          "note": "任务号引用，无 commit hash"
        },
        {
          "asset_id": "A17",
          "asset_class": "code_constant",
          "label": "仓内文献锚常量 LIT（球基线带 22–25° 来源）",
          "in_report_section": "### 1.2 方法谱系（①-②，external_anchor 落 `oss_solutions`）",
          "locator": {
            "method": "char_span",
            "start_char": 1569,
            "end_char": 1699,
            "start_line": 33,
            "end_line": 33,
            "quote": "| Zhou et al. (1999) *Physica A* 269:536–553 | lifted-box 沙堆 repose 标定算例；球 22–25°，角砾/椭球 35–45° | **外部锚**：趋势方向 + 球基线带（沿用仓内 `LIT`） |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "symbol_reference_only",
            "symbol": "仓内文献锚常量 LIT",
            "result": "unresolved",
            "detail": "报告只给符号名/常量名，未给文件+版本；本工序不猜测其定义位置"
          },
          "note": "TensorDEM 仓内常量名；具体取值以引用文献 Zhou 1999 为准，本工序不复核"
        },
        {
          "asset_id": "A18",
          "asset_class": "cluster_filesystem",
          "label": "集群节点 ~/oss-cache（n315/n330 开源包缓存，报告称只有 LBM 包）",
          "in_report_section": "### 1.1 开源横向（①-①）",
          "locator": {
            "method": "char_span",
            "start_char": 535,
            "end_char": 635,
            "start_line": 18,
            "end_line": 18,
            "quote": "| 集群节点 `~/oss-cache`（n315/n330） | 只有 LBM 包（Maarten-vd-Sande_lbm、hschwane、pylbm），**无 DEM/clump 实现** |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "filesystem_reachability",
            "path": "~/oss-cache (n315/n330)",
            "result": "unresolved",
            "detail": "集群节点家目录，控制面无挂载点；报告断言不可在本工序机器化"
          },
          "note": "集群节点家目录路径，本控制面不可挂载核验；报告断言无法在本工序落实为机器检查"
        },
        {
          "asset_id": "A19",
          "asset_class": "bibliography",
          "label": "外部文献 4 条：Ai 2011 / Wensrich 2012 / Jiang 2005 / Zhou 1999",
          "in_report_section": "### 1.2 方法谱系（①-②，external_anchor 落 `oss_solutions`）",
          "locator": {
            "method": "char_span",
            "start_char": 967,
            "end_char": 1699,
            "start_line": 30,
            "end_line": 33,
            "quote": "| Ai, Chen, Rotter, Ooi (2011) *Powder Technol.* 206:269–282 | 四种滚动阻力模型评估：常数力矩 / 粘性 / **速率比例正则化 `w/(w+ε)`** / 弹性-塑性滚动弹簧 + Coulomb 上限 | **判据来源**：速率比例型（本仓旧法就是这一族）**没有静态分支**，不能支撑坡面静平衡 → 用它测 repose 趋势，趋势无法归因于滚动阻力 |\n| Wensrich & Katterfeld (2012) *Powder Technol.* 217:409–417 | 滚动摩擦是**形状的替代量**：球的 repose 随 μ_r 单调升（μ_r 0→0.5 对应 21°→32°） | **设计规则**：μ_r 必须在\"球基线\"上标定后**固定**，形状族比较才不混淆（本轮 `MU_ROLL=0.3` 全配置唯一） |\n| Jiang, Yu, Harris (2005) *Comput. Geotech.* 32:340–357 | 弹性-塑性滚动弹簧 `M=-k_rθ`，`k_r=2.25 μ_r² k_n R²`，塑性上限 `μ_r R |Fn|` | **可行性算例**（§2.3）：在本基准的软接触参数下屈服角 ≈ 1.6 rad ⇒ 退化为弱弹性弹簧，故**不采纳**为默认（记录理由，不试错硬套） |\n| Zhou et al. (1999) *Physica A* 269:536–553 | lifted-box 沙堆 repose 标定算例；球 22–25°，角砾/椭球 35–45° | **外部锚**：趋势方向 + 球基线带（沿用仓内 `LIT`） |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "address_extraction",
            "result": "unresolved",
            "addresses_found": [],
            "detail": "仅在引用文本内检索 URL/DOI（不联网猜地址）；4 条文献均只给期刊卷页"
          },
          "note": "仅期刊名+卷页，无 DOI/URL；本工序不联网猜地址（见 resolution_check 地址抽取）"
        },
        {
          "asset_id": "A20",
          "asset_class": "in_source_table",
          "label": "§2.2 13 项内核测试判据表（R1a–R4c）",
          "in_report_section": "### 2.2 验证（机器可判，`tests/test_rolling_static.py`，**13 passed**）",
          "locator": {
            "method": "char_span",
            "start_char": 2934,
            "end_char": 3563,
            "start_line": 68,
            "end_line": 82,
            "quote": "| id | 判据 | 实测 |\n|---|---|---|\n| R1a | 单球 `com` 力臂 == `member` 力臂 | 64 方向，`atol=1e-15` 通过 |\n| R1b | 长轴 clump 端/侧力臂各向异性 | 端/侧 > 2.0 倍通过 |\n| R2a | `|ω|=100 ω_eps` 时满额 Coulomb | 相对误差 1e-12 内 |\n| R2b | `|ω|=0.1 ω_eps` 时一步刹停 | `ω_after=0`（1e-18 内） |\n| R3a | 力矩恒与 `ω_rel` 反向且不超上限 | 200 随机构型通过 |\n| R3b | 旧律逐位复现 | `np.array_equal` 通过 |\n| R4a | 引擎级：竖直轴自转球 | 静态 **2 步**停（0.5→0.193→0），旧律 20 步后仍 6.6e-4 rad/s |\n| R4b | 坡面蠕变（`I dω/dt = M_drive − M_roll`） | 静态残差 = 一步驱动增量 `M_drive dt/I`，比旧律稳态低 **11×** |\n| R4c | 能量账本 | 400 步内 `E` 不增（耗散律） |\n\n### 2.3 弹性-塑性弹簧的可行性算术（不采纳的理由，量化）\n\n`k_r = 2.25 μ_r² k_n R² = 2.25·0.09·150·(1.2e-3)² = 4.4e-8 N·m/rad`；",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表体随报告 markdown 内嵌，字符区间可直接定位"
        },
        {
          "asset_id": "A21",
          "asset_class": "in_source_table",
          "label": "§3 质量匹配填充高度 / n_particles / 墙高判定表（4 行）",
          "in_report_section": "## 3 扫描结果（真数据；`artifacts/GAP-DEM-CLUMP-R2/results.json`）",
          "locator": {
            "method": "char_span",
            "start_char": 3932,
            "end_char": 4239,
            "start_line": 95,
            "end_line": 100,
            "quote": "| a/b | 匹配填充高度 h [m] | n_particles | 墙高 [m] | 判定 |\n|---|---|---|---|---|\n| 1.0 | **0.0689** | 648 | 0.06 | h > 墙高，但床顶仅在墙上方 9 mm，流动后仍能静止 → **有效** |\n| 1.5 | **0.1187** | 440 | 0.06 | **床高 = 2.0×墙高 → 侧墙无法\"提起清空\" → 协议失效** |\n| 2.0 | **0.0938** | 324 | 0.06 | **1.56×墙高 → 协议失效** |\n| 3.0 | （同量级） | 216 | 0.06 | 同上 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表体内嵌；登记其存在与位置，不复核数值"
        },
        {
          "asset_id": "A22",
          "asset_class": "in_source_table",
          "label": "§4 误差判定表（关键量 vs 基准，6 行）",
          "in_report_section": "## 4 误差判定（关键量 vs 基准，逐项）",
          "locator": {
            "method": "char_span",
            "start_char": 4741,
            "end_char": 5159,
            "start_line": 120,
            "end_line": 127,
            "quote": "| 量 | 基准 | 实测 | 误差 | <3%? |\n|---|---|---|---|---|\n| 球力臂（单球 `com` vs `member`） | 解析相等 | 差 = 0 | 0 | **是** |\n| 静态分支满额限值 | `μ_r R |Fn|` | 相对 1e-12 | 1e-12 | **是** |\n| 一步刹停 | `ω_after = 0` | 0（<1e-18） | 0 | **是** |\n| 旧律复现 | 前轮公式 | `array_equal` | 0 | **是** |\n| **球 repose vs 22–25° 带** | 22–25° | 14.86–17.47° | **−22 % … −37 %**（相对带中心 23.5°） | **否** |\n| **形状趋势（C3）** | 单调升 + Δ≥3° | **不可估计**（只有 1 个有效 a/b） | — | **无法判定** |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表体内嵌；含 honest-FAIL 行（repose −22%…−37%）"
        },
        {
          "asset_id": "A23",
          "asset_class": "in_source_table",
          "label": "附表：三配置有效/失效计数表（程序生成）",
          "in_report_section": "## 附表：三配置有效/失效计数（程序生成）",
          "locator": {
            "method": "char_span",
            "start_char": 7135,
            "end_char": 7315,
            "start_line": 187,
            "end_line": 191,
            "quote": "| 配置 | 有效算例 | quiesced=false | 有效 repose [deg] |\n|---|---|---|---|\n| coulomb/com | 1 | 2 | 1.0:15.09 |\n| coulomb/member | 1 | 2 | 1.0:14.86 |\n| viscous/member | 1 | 2 | 1.0:17.47 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "表体内嵌，声明为程序生成"
        },
        {
          "asset_id": "A24",
          "asset_class": "repro_command_block",
          "label": "§7 复现命令块（4 段：单算例 / 分片 / 聚合 / 内核测试）",
          "in_report_section": "## 7 复现",
          "locator": {
            "method": "char_span",
            "start_char": 6504,
            "end_char": 6880,
            "start_line": 170,
            "end_line": 176,
            "quote": "# 单算例\npython benchmarks/gap_dem_clump/run_round2_scan.py --case ar=1.0,seed=0,config=coulomb/com \\\n  --outdir artifacts/GAP-DEM-CLUMP-R2\n# 全网格（集群分片，8 片）\npython benchmarks/gap_dem_clump/shard_round2.py --i 0 --n 8 --outdir artifacts/GAP-DEM-CLUMP-R2\n# 聚合 + 判据 + 图（quiesced=false 自动排除并计数）\npython benchmarks/gap_dem_clump/run_round2_scan.py --aggregate artifacts/GAP-DEM-CLUMP-R2",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "只取命令行本身（不含 ``` fences，避免结果信封内出现三反引号导致 json 块被截断）；路径指向 TensorDEM 仓，本工作树无法直接执行"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": true,
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "contract_chars_expected": 7569,
        "chars_matches_contract": true,
        "registered_not_verified": "resolution 只表示定位可解析性；报告结论未经本工序复核，未标 verified",
        "schema_pass": {
          "asset_manifest_v1": {
            "schema_file": "schemas/asset_manifest.v1.schema.json",
            "ok": true,
            "identity_consts_substituted": [
              "package_id",
              "report_id",
              "source.uri"
            ]
          },
          "kf_result_v1": {
            "schema_file": "schemas/kf_result.v1.schema.json",
            "ok": true,
            "note": "provenance.source_hash placeholder checked against real hash below"
          }
        }
      }
    }
  },
  "claims": []
}
```
