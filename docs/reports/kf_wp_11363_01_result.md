# KF-RESULT wp-11363-01

**工作包** `wp-11363-01` ｜ **工序** `01-asset-registration` ｜ **report_id** `11363` ｜ **lane** C ｜ **状态** draft（verification 由平台门计算，本工序不做 verified 标记）

**源** `tensor://reports/11363` · field=`markdown` · sha256=`sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23`（6902 chars / 9618 bytes UTF-8 / 124 行）

**标题** ESD 节能装置收益评估成熟化（p228w1-N09）：分项+能量上界门+自航点耦合

## ① 本工序做了什么

只做一件事：**登记 report_id=11363 的源资产**——确认报告身份与其 `markdown` 字段的字节哈希，把报告自己声明过的附件/工件/代码锚点逐条列成可解析的定位表（每条一个原文引文 + 字符区间），**不做抽取、不做报告类型分类、不生成 claim、不标 verified**。

为什么不抽取：本包契约 `objective.register_assets: true` / `objective.classify_report_type: false`，且 `output.asset_manifest.json` 是唯一交付物，notes 明确「claims 允许为空数组」。报告 11363 的领域结论（<15% 文献吻合、能量上界门）属于上游节点 mission 9564 的能力证据，在本工序里登记它们就等于越界背书，因此 `claims=[]` 并写明空集理由。

登记结果：**25 个资产**（declared_reference_only=1、referenced_unresolved=6、resolved=1、resolved_with_bytes=4、unresolved=13），**25 条 char-span 定位**全部通过「子串命中 + 偏移回读 + 行号重算 + 出现次数重算」四项独立校验（all_verified=True）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源（唯一信道）**：`GET /api/v1/tensor/reports/11363`（Bearer token），只取 `markdown` 字段。`scripts/kf/register_assets_lib.py` 内置 report_id 硬锁——返回记录的 id 不等于 `11363` 或 markdown 为空即拒产，从结构上保证本单不会写到别的 report_id。
2. **哈希先过门**：对 markdown 的 **UTF-8 字节**算 sha256，先与契约 `source_hash` 比对，不一致直接 `SystemExit`，不写任何产物。实测 `sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23` = 契约值（match）。
3. **枚举资产（不手挑）**：三类扫描器，规则固定、可复跑——
   · 平台 record 的 `figures[]`（name/caption）→ `embedded_figure`，并回正文找该图名的整行作为 markdown 定位；
   · 正文里所有反引号 token → 按后缀/形态分类（`.py`→source_code、`.json/.csv`→data_artifact、`.md`→document、`.png`→figure、尾 `/`→directory、`/api/...`→api_endpoint、点号标识符/全大写常量→symbol、`x = REAL`→capability_declaration），公式类 token（含 `=`、空格、`|`、`Δ` 等）显式排除，避免把 `P_D=2πnQ/η_R` 当路径；
   · 同一 token 只登记一次（token 去重，其余出现记为 `further_occurrences`），杜绝 id 重复。
4. **定位方式**：引文一律取 **markdown 整行原文**（不裁剪、不改写），存 `line` / `start_char` / `end_char` / `count_occurrences` / `unique`；每条做双重校验 `quote in markdown` 且 `markdown[start:end] == quote`。
5. **附件字节**：对 4 张图逐个探 `GET /api/v1/tensor/reports/11363/figures/<name>`，全部 **HTTP 200**，共 373525 字节，取流内 sha256 并校验 PNG magic（`\x89PNG`）；**字节不入库**（只在清单里留哈希+端点，任何人可复取复核），避免仓内堆二进制。
6. **工件引用**：`artifacts/esd/` 下的 10 文件包属 **ship-performance-platform** 仓，本工序只在交付工作树（TensorKnowledge）里探测路径，探测不到就如实记 `unresolved`，**不跨仓取字节、不猜**。
7. **自检**：`scripts/kf_wp11363_01_verify.py` 从原始字节重算全部验收项（默认**重新拉取** markdown，所以陈旧快照无法蒙过哈希门；`--offline` 才用快照并显式声明）。另配 `tests/test_kf_wp11363_01.py` 13 个不变式测试，其中 5 个是**变异测试**（改引文/挪偏移/造重复 id/换哈希/换 report_id）——证明每项检查真的会红，而不是只会绿。

## ③ 产出物清单（输出文件名 → 要点）

| 产出 | 路径 | 要点 |
|---|---|---|
| `asset_manifest.json`（契约声明输出） | `docs/kf/wp-11363-01/asset_manifest.json` | 25 资产 / 25 定位 / claims=[] / 哈希=346ef4c6322f… |
| 结果信封 | `docs/kf/wp-11363-01/kf_result.json` | package_id/task_type/report_id/provenance/outputs，本页唯一 json 块 |
| 自检报告 | `docs/kf/wp-11363-01/report_selfcheck.json` | 11 项检查，11 通过，0 失败（all_pass=True） |
| 源快照 | `runs/wp-11363-01/source_11363.md` | markdown 原样字节快照（9618 bytes），离线重建用 |
| 定位图 | `docs/kf/wp-11363-01/figures/wp11363_01_locator_map.png` | 上：资产清点；下：每条定位在 6902 字符轴上的真实位置 |
| 生成器/校验器 | `scripts/kf_wp11363_01_register_assets.py`、`kf_wp11363_01_verify.py`、`kf_wp11363_01_figure.py`、`kf_wp11363_01_render_report.py` | 一键复跑 |
| 清单 schema | `schemas/asset_manifest_wp11363_01.schema.json` | 把 package_id/report_id/hash 钉成 const，杜绝跨报告复用 |
| 不变式测试 | `tests/test_kf_wp11363_01.py` | 13 tests（8 不变式 + 5 变异），离线可跑 |

说明：契约 `delivery.repo: TensorKnowledge`、`delivery.status: draft`，产物全部落在工作树内。清单正文同时嵌进 `outputs.asset_manifest.json`，所以平台门只读信封也能拿到完整清单。

## ④ 证据定位表（claim/字段 → 原文引文片段）

### 4.1 资产 → 定位（全部可从原文逐字定位）

| asset_id | kind | section | locator | resolution |
|---|---|---|---|---|
| `r11363:source-markdown` | report_markdown | ESD 节能装置收益评估成熟 | L1 · chars [0,29) | resolved |
| `r11363:figure:01` | embedded_figure | ④ 结果图 | L87 · chars [5056,5117) | resolved_with_bytes (`http 200`, bytes=55500, sha256 `sha256:333035f7049386bf…`) |
| `r11363:figure:02` | embedded_figure | ④ 结果图 | L88 · chars [5118,5193) | resolved_with_bytes (`http 200`, bytes=192545, sha256 `sha256:411fb6d7836e18fc…`) |
| `r11363:figure:03` | embedded_figure | ④ 结果图 | L89 · chars [5194,5260) | resolved_with_bytes (`http 200`, bytes=53786, sha256 `sha256:5221d33b542e11eb…`) |
| `r11363:figure:04` | embedded_figure | ④ 结果图 | L90 · chars [5261,5323) | resolved_with_bytes (`http 200`, bytes=71694, sha256 `sha256:135db99c731212ff…`) |
| `r11363:ref:01` | source_directory_reference | ESD 节能装置收益评估成熟 | L3 · chars [31,146) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:02` | source_code_reference | ② 怎么做的（方法/流程/关 | L19 · chars [921,1145) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:03` | symbol_reference | ② 怎么做的（方法/流程/关 | L19 · chars [921,1145) | referenced_unresolved — symbol is named in the report prose; its defining line is not given as a resolvable path i |
| `r11363:ref:04` | source_code_reference | ② 怎么做的（方法/流程/关 | L20 · chars [1146,1392) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:05` | symbol_reference | ② 怎么做的（方法/流程/关 | L20 · chars [1146,1392) | referenced_unresolved — symbol is named in the report prose; its defining line is not given as a resolvable path i |
| `r11363:ref:06` | symbol_reference | ② 怎么做的（方法/流程/关 | L20 · chars [1146,1392) | referenced_unresolved — symbol is named in the report prose; its defining line is not given as a resolvable path i |
| `r11363:ref:07` | symbol_reference | ② 怎么做的（方法/流程/关 | L22 · chars [1537,1620) | referenced_unresolved — symbol is named in the report prose; its defining line is not given as a resolvable path i |
| `r11363:ref:08` | source_code_reference | ② 怎么做的（方法/流程/关 | L23 · chars [1621,1728) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:09` | source_directory_reference | 审计链 | L119 · chars [6383,6530) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:10` | data_artifact_reference | 审计链 | L120 · chars [6531,6579) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:11` | symbol_reference | 审计链 | L121 · chars [6580,6638) | referenced_unresolved — symbol is named in the report prose; its defining line is not given as a resolvable path i |
| `r11363:ref:12` | source_code_reference | 审计链 | L122 · chars [6639,6779) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:13` | source_code_reference | 审计链 | L122 · chars [6639,6779) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:14` | source_code_reference | 审计链 | L122 · chars [6639,6779) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:15` | source_code_reference | 审计链 | L122 · chars [6639,6779) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:16` | source_code_reference | 审计链 | L122 · chars [6639,6779) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:17` | document_reference | 审计链 | L123 · chars [6780,6819) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:18` | capability_declaration_reference | 审计链 | L124 · chars [6820,6901) | declared_reference_only |
| `r11363:ref:19` | data_artifact_reference | 审计链 | L124 · chars [6820,6901) | unresolved — declared by report 11363 as a ship-performance-platform artefact; not present in the deliv |
| `r11363:ref:upstream-resistance` | upstream_dependency_reference | ① 案例介绍（物理背景与几何 | L15 · chars [722,892) | referenced_unresolved — report states R_T comes from the resistance endpoint's Holtrop-1984 kernel but gives no pa |

### 4.2 逐字引文（整行原文，`|` 已转义）

| asset_id | 原文引文（逐字，整行） | 唯一 |
|---|---|---|
| `r11363:source-markdown` | # ESD 节能装置收益评估成熟化（p228w1-N09） | 是 |
| `r11363:figure:01` | - 图 1 `fig1_per_device_savings.png`：3 船型 × 4 装置分项节能柱状图（数值标注）。 | 是 |
| `r11363:figure:02` | - 图 2 `fig2_combined_vs_sum.png`：45 组合的"组合节能 / Σ 分项"曲线 + 交互余量带（本任务的等效"场图"）。 | 是 |
| `r11363:figure:03` | - 图 3 `fig3_selfprop_coupling.png`：全 4 装置下 ΔP/P 对 Δn/n 的散点，判据线 5%。 | 是 |
| `r11363:figure:04` | - 图 4 `fig4_benchmark.png`：文献对标（公开 nominal + 区间 + 预测 + 逐案例误差）。 | 是 |
| `r11363:ref:01` | **仓库** ship-performance-platform　**分支** agent/m9564　**落点** `backend/physics/esd/` + `POST /api/v1/calculati… | 是 |
| `r11363:ref:02` | 1. **装置模型**（`physics/esd/devices.py`，规格表外置 `DEVICE_SPECS`）：预旋导管 Δw=0.75·C_Td、Δη_R=0.15·C_Td、T_d=C_Td·½ρV_a²… | 是 |
| `r11363:ref:03` | 1. **装置模型**（`physics/esd/devices.py`，规格表外置 `DEVICE_SPECS`）：预旋导管 Δw=0.75·C_Td、Δη_R=0.15·C_Td、T_d=C_Td·½ρV_a²… | 是 |
| `r11363:ref:04` | 2. **自航点耦合**（`selfprop.py`）：解 `T(n)(1−t')+T_dev = R_T+ΔR_dev`，K_T/K_Q 取自 BEMT 敞水核 `modules.propeller_bemt.b… | 是 |
| `r11363:ref:05` | 2. **自航点耦合**（`selfprop.py`）：解 `T(n)(1−t')+T_dev = R_T+ΔR_dev`，K_T/K_Q 取自 BEMT 敞水核 `modules.propeller_bemt.b… | 是 |
| `r11363:ref:06` | 2. **自航点耦合**（`selfprop.py`）：解 `T(n)(1−t')+T_dev = R_T+ΔR_dev`，K_T/K_Q 取自 BEMT 敞水核 `modules.propeller_bemt.b… | 是 |
| `r11363:ref:07` | 4. **判据门**：几何/参数越界拒绝；自航点残差 >1e-3 报错；`energy_upper_bound.satisfied` 与 Δn/n<5% 同响应返回。 | 是 |
| `r11363:ref:08` | 5. **工具链**：`tools/gen_esd_artifacts.py` 程序化产出全部表/图/回归金标/清单 sha256；63 个测试覆盖能量上界、分项为正、自航点耦合、文献对标、API 契约、回归金标。 | 是 |
| `r11363:ref:09` | - 工件：`artifacts/esd/`（benchmark_results.json、golden_regression.json、per_device_table.csv、combined_table.csv… | 是 |
| `r11363:ref:10` | - 清单 sha256：`artifacts/esd/manifest.json`（10 文件） | 是 |
| `r11363:ref:11` | - 金标：45 组合逐位可复现（`test_golden_grid_reproducible`，相对差 <1e-9） | 是 |
| `r11363:ref:12` | - 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_… | 是 |
| `r11363:ref:13` | - 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_… | 是 |
| `r11363:ref:14` | - 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_… | 是 |
| `r11363:ref:15` | - 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_… | 是 |
| `r11363:ref:16` | - 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_… | 是 |
| `r11363:ref:17` | - 文档：`docs/ESD_ENERGY_SAVING.md`（六要素全文） | 是 |
| `r11363:ref:18` | - 能力：`propulsion.esd_energy_saving = REAL`（`artifacts/esd/capability_delta.json`） | 是 |
| `r11363:ref:19` | - 能力：`propulsion.esd_energy_saving = REAL`（`artifacts/esd/capability_delta.json`） | 是 |
| `r11363:ref:upstream-resistance` | 几何先验全通过：Cb 与 ∇/(L·B·T) 偏差 <0.02，L/B∈[4,11]、B/T∈[1.8,6]、D/T∈[0.35,0.90]、P/D∈[0.5,1.6]、Ae/Ao∈[0.3,1.2]；任一越界即拒… | 是 |

### 4.3 身份字段 → 证据

| 字段 | 值 | 证据 |
|---|---|---|
| `report_id` | `11363` | API 返回记录 `id` 与契约一致（lib 硬锁，不一致即拒产） |
| `provenance.source_hash` | `sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23` | 本地重算 UTF-8 字节 sha256 = 契约值；chars=6902 = 契约 6902 |
| title（身份校验） | ESD 节能装置收益评估成熟化（p228w1-N09）：分项+能量上界门+自航点耦合 | record.title == 契约 title（True） |
| scenario_key | `p228w1-N09` | record.scenario_key == 契约（True） |
| 图 4 张 | `fig1_per_device_savings.png`、`fig2_combined_vs_sum.png`、`fig3_selfprop_coupling.png`、`fig4_benchmark.png` | record `figures[]` name+caption；正文 ④ 段逐图整行引文 |
| 工件清单自洽 | 报告称「10 文件」，枚举成员合计 10 | 审计链「工件：」整行：benchmark_results.json、golden_regression.json、per_device_table.csv、combined_table.csv、report_tables.md、4 张 png、manifest.json（count match=True） |

**为何没有云图**：本工序是登记工序，读数只有「源字段字节哈希 + 引文定位」，没有数值场量，任何云图都会是凭空生成的假证据；故以「资产清点 + 定位位置图」这一真实的二维数据结构图替代，坐标轴即清单里的字符偏移，无手绘成分。

图（程序化生成，非手绘）：

![wp11363_01_locator_map](figures/wp11363_01_locator_map.png)

图注：上图为资产清点（kind × 解析状态，计数直接读清单）；下图为每条 char-span 定位在 6902 字符源字段上的真实位置（竖虚线=章节标题 H1..H7：H1..H6 对应报告 ①–⑥，H7=审计链）。绿色=有字节/可哈希，红色=引用无法在本工作树解析（工件在 ship-performance-platform 仓）。

## ⑤ 注意点与局限

1. Registration only: no claim/evidence extraction, no report-type classification, no verified marks (verification is computed by the platform gate).
2. source_hash scope = UTF-8 bytes of the markdown string returned by the platform API; any change to the stored markdown, even whitespace, invalidates it.
3. Resolution is probed against the delivery worktree (TensorKnowledge) only; report 11363's artefacts live in ship-performance-platform and are therefore reported as unresolved rather than fetched across repositories.
4. Quotes are whole markdown lines, so char spans include table pipes / leading list markers; they are verbatim and re-verifiable, not minimal spans.
5. Report 11363 makes domain claims (<15% literature agreement, energy upper bound gate). Registering them would be extraction, which is explicitly out of this package's scope; none of them is endorsed or refuted here.

补充（本工序实际踩到的坑）：

· **图的字节其实取得到**：与既往同类包（record 只有 name/caption、字节端点 404）不同，本报告 4 张图的 `/figures/<name>` 全返回 200 并可哈希；但 `GET /tensor/reports/11363/figures`（不带名）仍 404，所以「列附件」必须逐名探，不能只看列表端点。
· **路径扫描必须排除公式**：正文里有 `P_D=2πnQ/η_R`、`T(n)(1−t')+T_dev = R_T+ΔR_dev` 这类带 `/` 或 `.` 的反引号 token，不做 `=`/空白/`Δ` 排除就会误登记成路径资产（本单已排除）。
· **图名会重复登记**：图名既出现在 record `figures[]` 也出现在正文 ④ 段；若不按 token 去重，4 张图会各多出一条同义 `figure_reference`（实测未去重时为 29 条、去重后 25 条）。
· **schema 钉不住 report_id**：通用信封 schema 的 `report_id` 只有 `^[0-9]+$`，单靠 schema_pass 抓不到「信封里塞了别家 report_id」；因此另加 `constraint_envelope_manifest_consistency` 交叉一致性检查，并用变异测试钉住（`test_foreign_report_id_is_caught`）。

**未完成/不做**：不解析报告数值表；不核对上游 `artifacts/esd/` 的 10 个文件是否存在/一致（跨仓，无字节）；不评价报告的领域结论（<15%、能量上界门）——那属于 mission 9564 的能力证据与平台门。

## ⑥ 自检（逐条对照 acceptance）

| 验收项 | 结果 | 证据 |
|---|---|---|
| `valid_json` | ✅ PASS | envelope and manifest parsed via json.loads (input to run_checks) |
| `schema_pass` | ✅ PASS | schemas/kf_result.v1.schema.json (envelope) + schemas/asset_manifest_wp11363_01.schema.json (manifest) both validate; declared output name = asset_manifest.json |
| `source_locator_resolvable` | ✅ PASS | 25 char_span locators re-verified against live GET /api/v1/tensor/reports/11363 (substring + offset back-read + line number + occurrence count); 25 are unique in the source; failures=[] |
| `source_hash_matches` | ✅ PASS | source=live GET /api/v1/tensor/reports/11363; recomputed=346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23 envelope=346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23 manifest=346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9f |
| `no_duplicate_ids` | ✅ PASS | 25 asset ids, duplicates=[], pattern_ok=True |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ PASS | claims=[] in both envelope and manifest (objective.classify_report_type=false, no extraction); reason recorded: 'objective.classify_report_type=false and the contract allows'; vacuously satisfied, violations=[] |

契约约束（额外自查）：

| 约束 | 结果 | 证据 |
|---|---|---|
| `do_not_mark_claims_as_verified` | ✅ PASS | no claim carries status='verified' or verified=true; verification is left to the platform gate (violations=[]) |
| `report_id_scope` | ✅ PASS | every report_id/source_uri in the deliverables resolves to 11363; offenders=[] |
| `preserve_uncertainty` | ✅ PASS | 5 limitations + 19 unresolved asset ids recorded; figure byte absence is reported per figure instead of being papered over |
| `contract_identity` | ✅ PASS | package_id=wp-11363-01 report_id=11363 chars=6902 hash_match=True |
| `envelope_manifest_consistency` | ✅ PASS | package_id/report_id/task_type/source_hash agree between envelope and manifest and outputs.asset_manifest.json is the manifest itself; mismatches=[] |

**honest 结论**：全部验收项与约束项通过（11/11）。

误差判定（本工序为登记工序，无物理基准）：

| 关键量 | 本工序结果 | 基准 | 是否 <3% |
|---|---|---|---|
| markdown 字节 sha256 | `sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23` | 契约 `sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23` | 一致（0 位差异，故 <3% 成立） |
| chars | 6902 | 契约 6902 | 0% 差异 |
| 引文定位一致率 | 25/25 = 100% | 全部可解析 | 0% 差异 |
| 图字节 | 4/4 HTTP 200，PNG magic 全通过，共 373525 bytes | 端点实际返回 | 无物理基准（哈希自证） |

以上数字全部由脚本注入（`report_selfcheck.json` / `asset_manifest.json`），无手抄。

## 复现（一键）

```bash
cd <worktree-root>   # TensorKnowledge 检出，分支 agent/m15697
python3 scripts/kf_wp11363_01_register_assets.py   # 拉源→校验哈希→生成清单+信封（哈希不符即拒产）
python3 scripts/kf_wp11363_01_verify.py            # 默认重新拉源重算全部验收项（--offline 用快照）
python3 scripts/kf_wp11363_01_figure.py            # 定位图（数据全部读清单）
python3 -m pytest tests/test_kf_wp11363_01.py -q   # 13 tests：8 不变式 + 5 变异
python3 scripts/kf_wp11363_01_render_report.py     # 重渲染本报告（--post 发布）
```

## 结果信封（本页唯一 json 块）

```json
{
  "package_id": "wp-11363-01",
  "task_type": "01-asset-registration",
  "report_id": "11363",
  "provenance": {
    "source_hash": "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23",
    "source_field": "markdown",
    "producer": "kf-worker/m15697",
    "emitted_at": "2026-11-12T01:53:58.870296+00:00",
    "notes": "GET /api/v1/tensor/reports/11363 -> markdown; sha256 over UTF-8 bytes; contract hash re-checked before any output was written"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-11363-01",
      "task_type": "01-asset-registration",
      "report_id": "11363",
      "lane": "C",
      "generated_at": "2026-11-12T01:53:58.870296+00:00",
      "producer": "kf-worker/m15697",
      "source": {
        "report_id": "11363",
        "source_uri": "tensor://reports/11363",
        "source_field": "markdown",
        "source_hash": "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23",
        "contract_source_hash": "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23",
        "hash_algo": "sha256",
        "hash_match": true,
        "chars": 6902,
        "contract_chars": 6902,
        "chars_match_contract": true,
        "bytes": 9618,
        "lines": 124,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "logical lines = markdown.splitlines(); 1-based",
        "fetched_via": "GET /api/v1/tensor/reports/11363 (Bearer token)",
        "record_fields": {
          "title": "ESD 节能装置收益评估成熟化（p228w1-N09）：分项+能量上界门+自航点耦合",
          "scenario_key": "p228w1-N09",
          "mission_id": 9564,
          "stage": "S2",
          "status": "published",
          "created_at": "2026-11-10T13:09:43.324008+00:00",
          "tags": [
            "ESD",
            "节能装置",
            "预旋导管",
            "PBCF",
            "舵球",
            "毂帽鳍",
            "自航点耦合",
            "能量上界门"
          ],
          "contract_title": "ESD 节能装置收益评估成熟化（p228w1-N09）：分项+能量上界门+自航点耦合",
          "contract_scenario_key": "p228w1-N09",
          "title_matches_contract": true,
          "scenario_matches_contract": true
        }
      },
      "platform_attachment_probes": {
        "figures_endpoint": {
          "endpoint": "/tensor/reports/11363/figures",
          "http_status": 404,
          "bytes": 0
        },
        "fig1_per_device_savings.png": {
          "endpoint": "/tensor/reports/11363/figures/fig1_per_device_savings.png",
          "http_status": 200,
          "bytes": 55500,
          "payload_sha256": "sha256:333035f7049386bfd7c41fb2dc1099285296075aebfdb10c55a1237cd43ff187",
          "png_magic_ok": true,
          "stored": false,
          "note": "payload hashed in-flight; blob not committed (re-fetchable from the endpoint)"
        },
        "fig2_combined_vs_sum.png": {
          "endpoint": "/tensor/reports/11363/figures/fig2_combined_vs_sum.png",
          "http_status": 200,
          "bytes": 192545,
          "payload_sha256": "sha256:411fb6d7836e18fc70f49acc268cc0561a30e628727f79e2b39d57df39b5fa2e",
          "png_magic_ok": true,
          "stored": false,
          "note": "payload hashed in-flight; blob not committed (re-fetchable from the endpoint)"
        },
        "fig3_selfprop_coupling.png": {
          "endpoint": "/tensor/reports/11363/figures/fig3_selfprop_coupling.png",
          "http_status": 200,
          "bytes": 53786,
          "payload_sha256": "sha256:5221d33b542e11ebb45b444d8d51b600922bd260ab2be8383734bcafeb3fedf9",
          "png_magic_ok": true,
          "stored": false,
          "note": "payload hashed in-flight; blob not committed (re-fetchable from the endpoint)"
        },
        "fig4_benchmark.png": {
          "endpoint": "/tensor/reports/11363/figures/fig4_benchmark.png",
          "http_status": 200,
          "bytes": 71694,
          "payload_sha256": "sha256:135db99c731212ff89f52a2853670ac0ea35a478e669e181670ba064fa9edc1d",
          "png_magic_ok": true,
          "stored": false,
          "note": "payload hashed in-flight; blob not committed (re-fetchable from the endpoint)"
        }
      },
      "assets": [
        {
          "asset_id": "r11363:source-markdown",
          "kind": "report_markdown",
          "label": "report-11363-markdown",
          "section": "ESD 节能装置收益评估成熟",
          "locator": {
            "source_field": "markdown",
            "line": 1,
            "start_char": 0,
            "end_char": 29,
            "quote": "# ESD 节能装置收益评估成熟化（p228w1-N09）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "source_uri": "tensor://reports/11363",
          "media_type": "text/markdown",
          "bytes": 9618,
          "chars": 6902,
          "lines": 124,
          "sha256": "sha256:346ef4c6322f2c40bb1dda58a6336eed4e90122132009f11a4d1a9fe8a065c23",
          "hash_scope": "UTF-8 bytes of the `markdown` field served by GET /api/v1/tensor/reports/11363",
          "local_copy": "runs/wp-11363-01/source_11363.md",
          "resolution": {
            "status": "resolved",
            "scope": "platform_api",
            "via": "GET /api/v1/tensor/reports/11363 (Bearer token)"
          }
        },
        {
          "asset_id": "r11363:figure:01",
          "kind": "embedded_figure",
          "label": "fig1_per_device_savings.png",
          "name": "fig1_per_device_savings.png",
          "caption": "图1 ESD 分项节能（3 船型 × 4 装置，等速等阻力）",
          "record_pointer": "/figures/0/name",
          "section": "④ 结果图",
          "bytes": 55500,
          "sha256": "sha256:333035f7049386bfd7c41fb2dc1099285296075aebfdb10c55a1237cd43ff187",
          "resolution": {
            "status": "resolved_with_bytes",
            "scope": "platform_api",
            "via": "GET /tensor/reports/11363/figures/fig1_per_device_savings.png",
            "http_status": 200,
            "payload_sha256": "sha256:333035f7049386bfd7c41fb2dc1099285296075aebfdb10c55a1237cd43ff187",
            "png_magic_ok": true,
            "reason": "figure payload served with HTTP 200; sha256 taken in flight, blob deliberately not committed"
          },
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "line": 87,
            "start_char": 5056,
            "end_char": 5117,
            "quote": "- 图 1 `fig1_per_device_savings.png`：3 船型 × 4 装置分项节能柱状图（数值标注）。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "body_reference_line": 87
          }
        },
        {
          "asset_id": "r11363:figure:02",
          "kind": "embedded_figure",
          "label": "fig2_combined_vs_sum.png",
          "name": "fig2_combined_vs_sum.png",
          "caption": "图2 能量上界门：45 组合的组合节能对 Σ 分项节能（含交互余量带）",
          "record_pointer": "/figures/1/name",
          "section": "④ 结果图",
          "bytes": 192545,
          "sha256": "sha256:411fb6d7836e18fc70f49acc268cc0561a30e628727f79e2b39d57df39b5fa2e",
          "resolution": {
            "status": "resolved_with_bytes",
            "scope": "platform_api",
            "via": "GET /tensor/reports/11363/figures/fig2_combined_vs_sum.png",
            "http_status": 200,
            "payload_sha256": "sha256:411fb6d7836e18fc70f49acc268cc0561a30e628727f79e2b39d57df39b5fa2e",
            "png_magic_ok": true,
            "reason": "figure payload served with HTTP 200; sha256 taken in flight, blob deliberately not committed"
          },
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "line": 88,
            "start_char": 5118,
            "end_char": 5193,
            "quote": "- 图 2 `fig2_combined_vs_sum.png`：45 组合的\"组合节能 / Σ 分项\"曲线 + 交互余量带（本任务的等效\"场图\"）。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "body_reference_line": 88
          }
        },
        {
          "asset_id": "r11363:figure:03",
          "kind": "embedded_figure",
          "label": "fig3_selfprop_coupling.png",
          "name": "fig3_selfprop_coupling.png",
          "caption": "图3 自航点耦合：全部 4 装置下总节能对转速偏移（判据 5%）",
          "record_pointer": "/figures/2/name",
          "section": "④ 结果图",
          "bytes": 53786,
          "sha256": "sha256:5221d33b542e11ebb45b444d8d51b600922bd260ab2be8383734bcafeb3fedf9",
          "resolution": {
            "status": "resolved_with_bytes",
            "scope": "platform_api",
            "via": "GET /tensor/reports/11363/figures/fig3_selfprop_coupling.png",
            "http_status": 200,
            "payload_sha256": "sha256:5221d33b542e11ebb45b444d8d51b600922bd260ab2be8383734bcafeb3fedf9",
            "png_magic_ok": true,
            "reason": "figure payload served with HTTP 200; sha256 taken in flight, blob deliberately not committed"
          },
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "line": 89,
            "start_char": 5194,
            "end_char": 5260,
            "quote": "- 图 3 `fig3_selfprop_coupling.png`：全 4 装置下 ΔP/P 对 Δn/n 的散点，判据线 5%。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "body_reference_line": 89
          }
        },
        {
          "asset_id": "r11363:figure:04",
          "kind": "embedded_figure",
          "label": "fig4_benchmark.png",
          "name": "fig4_benchmark.png",
          "caption": "图4 文献对标：5 nominal 案例逐案例误差 + 1 组合区间案例",
          "record_pointer": "/figures/3/name",
          "section": "④ 结果图",
          "bytes": 71694,
          "sha256": "sha256:135db99c731212ff89f52a2853670ac0ea35a478e669e181670ba064fa9edc1d",
          "resolution": {
            "status": "resolved_with_bytes",
            "scope": "platform_api",
            "via": "GET /tensor/reports/11363/figures/fig4_benchmark.png",
            "http_status": 200,
            "payload_sha256": "sha256:135db99c731212ff89f52a2853670ac0ea35a478e669e181670ba064fa9edc1d",
            "png_magic_ok": true,
            "reason": "figure payload served with HTTP 200; sha256 taken in flight, blob deliberately not committed"
          },
          "locator": {
            "source_field": "markdown",
            "method": "char_span",
            "line": 90,
            "start_char": 5261,
            "end_char": 5323,
            "quote": "- 图 4 `fig4_benchmark.png`：文献对标（公开 nominal + 区间 + 预测 + 逐案例误差）。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "body_reference_line": 90
          }
        },
        {
          "asset_id": "r11363:ref:01",
          "kind": "source_directory_reference",
          "label": "backend/physics/esd/",
          "section": "ESD 节能装置收益评估成熟",
          "locator": {
            "source_field": "markdown",
            "line": 3,
            "start_char": 31,
            "end_char": 146,
            "quote": "**仓库** ship-performance-platform　**分支** agent/m9564　**落点** `backend/physics/esd/` + `POST /api/v1/calculations/esd`",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "backend/physics/esd/",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:02",
          "kind": "source_code_reference",
          "label": "physics/esd/devices.py",
          "section": "② 怎么做的（方法/流程/关",
          "locator": {
            "source_field": "markdown",
            "line": 19,
            "start_char": 921,
            "end_char": 1145,
            "quote": "1. **装置模型**（`physics/esd/devices.py`，规格表外置 `DEVICE_SPECS`）：预旋导管 Δw=0.75·C_Td、Δη_R=0.15·C_Td、T_d=C_Td·½ρV_a²·A_d（环隙，间隙比 0.15）；PBCF Δη_R=0.020·ε 且鳍片推力 0.008·ε·R_T；舵球 ΔR=−0.012·ε·R_T、Δη_R=+0.005·ε、Δt=+0.002·ε；毂帽鳍 Δη_R=+0.011·ε。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "physics/esd/devices.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:03",
          "kind": "symbol_reference",
          "label": "DEVICE_SPECS",
          "section": "② 怎么做的（方法/流程/关",
          "locator": {
            "source_field": "markdown",
            "line": 19,
            "start_char": 921,
            "end_char": 1145,
            "quote": "1. **装置模型**（`physics/esd/devices.py`，规格表外置 `DEVICE_SPECS`）：预旋导管 Δw=0.75·C_Td、Δη_R=0.15·C_Td、T_d=C_Td·½ρV_a²·A_d（环隙，间隙比 0.15）；PBCF Δη_R=0.020·ε 且鳍片推力 0.008·ε·R_T；舵球 ΔR=−0.012·ε·R_T、Δη_R=+0.005·ε、Δt=+0.002·ε；毂帽鳍 Δη_R=+0.011·ε。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "DEVICE_SPECS",
          "resolution": {
            "status": "referenced_unresolved",
            "scope": "declared_in_prose_only",
            "reason": "symbol is named in the report prose; its defining line is not given as a resolvable path inside this 工序's scope"
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:04",
          "kind": "source_code_reference",
          "label": "selfprop.py",
          "section": "② 怎么做的（方法/流程/关",
          "locator": {
            "source_field": "markdown",
            "line": 20,
            "start_char": 1146,
            "end_char": 1392,
            "quote": "2. **自航点耦合**（`selfprop.py`）：解 `T(n)(1−t')+T_dev = R_T+ΔR_dev`，K_T/K_Q 取自 BEMT 敞水核 `modules.propeller_bemt.bem_point`（与 /propulsion/predict 同源），转速用 Illinois 括号法反解（容差 1e-7；与 `solve_n_for_thrust` 等价性由测试钉住，实测相对差 3e-6），`P_D=2πnQ/η_R`（Holtrop 1984 定义）。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "selfprop.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:05",
          "kind": "symbol_reference",
          "label": "modules.propeller_bemt.bem_point",
          "section": "② 怎么做的（方法/流程/关",
          "locator": {
            "source_field": "markdown",
            "line": 20,
            "start_char": 1146,
            "end_char": 1392,
            "quote": "2. **自航点耦合**（`selfprop.py`）：解 `T(n)(1−t')+T_dev = R_T+ΔR_dev`，K_T/K_Q 取自 BEMT 敞水核 `modules.propeller_bemt.bem_point`（与 /propulsion/predict 同源），转速用 Illinois 括号法反解（容差 1e-7；与 `solve_n_for_thrust` 等价性由测试钉住，实测相对差 3e-6），`P_D=2πnQ/η_R`（Holtrop 1984 定义）。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "modules.propeller_bemt.bem_point",
          "resolution": {
            "status": "referenced_unresolved",
            "scope": "declared_in_prose_only",
            "reason": "symbol is named in the report prose; its defining line is not given as a resolvable path inside this 工序's scope"
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:06",
          "kind": "symbol_reference",
          "label": "solve_n_for_thrust",
          "section": "② 怎么做的（方法/流程/关",
          "locator": {
            "source_field": "markdown",
            "line": 20,
            "start_char": 1146,
            "end_char": 1392,
            "quote": "2. **自航点耦合**（`selfprop.py`）：解 `T(n)(1−t')+T_dev = R_T+ΔR_dev`，K_T/K_Q 取自 BEMT 敞水核 `modules.propeller_bemt.bem_point`（与 /propulsion/predict 同源），转速用 Illinois 括号法反解（容差 1e-7；与 `solve_n_for_thrust` 等价性由测试钉住，实测相对差 3e-6），`P_D=2πnQ/η_R`（Holtrop 1984 定义）。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "solve_n_for_thrust",
          "resolution": {
            "status": "referenced_unresolved",
            "scope": "declared_in_prose_only",
            "reason": "symbol is named in the report prose; its defining line is not given as a resolvable path inside this 工序's scope"
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:07",
          "kind": "symbol_reference",
          "label": "energy_upper_bound.satisfied",
          "section": "② 怎么做的（方法/流程/关",
          "locator": {
            "source_field": "markdown",
            "line": 22,
            "start_char": 1537,
            "end_char": 1620,
            "quote": "4. **判据门**：几何/参数越界拒绝；自航点残差 >1e-3 报错；`energy_upper_bound.satisfied` 与 Δn/n<5% 同响应返回。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "energy_upper_bound.satisfied",
          "resolution": {
            "status": "referenced_unresolved",
            "scope": "declared_in_prose_only",
            "reason": "symbol is named in the report prose; its defining line is not given as a resolvable path inside this 工序's scope"
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:08",
          "kind": "source_code_reference",
          "label": "tools/gen_esd_artifacts.py",
          "section": "② 怎么做的（方法/流程/关",
          "locator": {
            "source_field": "markdown",
            "line": 23,
            "start_char": 1621,
            "end_char": 1728,
            "quote": "5. **工具链**：`tools/gen_esd_artifacts.py` 程序化产出全部表/图/回归金标/清单 sha256；63 个测试覆盖能量上界、分项为正、自航点耦合、文献对标、API 契约、回归金标。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "tools/gen_esd_artifacts.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:09",
          "kind": "source_directory_reference",
          "label": "artifacts/esd/",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 119,
            "start_char": 6383,
            "end_char": 6530,
            "quote": "- 工件：`artifacts/esd/`（benchmark_results.json、golden_regression.json、per_device_table.csv、combined_table.csv、report_tables.md、4 张 png、manifest.json）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "artifacts/esd/",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": [
            {
              "line": 44,
              "quote": "**组合节能与 Σ 分项（节选：全 4 装置 + 两个代表性双装置；全表见 artifacts/esd/combined_table.csv）**",
              "quote_verified": true
            },
            {
              "line": 120,
              "quote": "- 清单 sha256：`artifacts/esd/manifest.json`（10 文件）",
              "quote_verified": true
            },
            {
              "line": 124,
              "quote": "- 能力：`propulsion.esd_energy_saving = REAL`（`artifacts/esd/capability_delta.json`）",
              "quote_verified": true
            }
          ]
        },
        {
          "asset_id": "r11363:ref:10",
          "kind": "data_artifact_reference",
          "label": "artifacts/esd/manifest.json",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 120,
            "start_char": 6531,
            "end_char": 6579,
            "quote": "- 清单 sha256：`artifacts/esd/manifest.json`（10 文件）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "artifacts/esd/manifest.json",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": [
              "docs/sediment/tk-sediment-m5054/figures/manifest.json",
              "knowledge/kb10k/manifest.json",
              "knowledge/sediment/sloshing-impact-lbm/manifest.json"
            ]
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:11",
          "kind": "symbol_reference",
          "label": "test_golden_grid_reproducible",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 121,
            "start_char": 6580,
            "end_char": 6638,
            "quote": "- 金标：45 组合逐位可复现（`test_golden_grid_reproducible`，相对差 <1e-9）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "test_golden_grid_reproducible",
          "resolution": {
            "status": "referenced_unresolved",
            "scope": "declared_in_prose_only",
            "reason": "symbol is named in the report prose; its defining line is not given as a resolvable path inside this 工序's scope"
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:12",
          "kind": "source_code_reference",
          "label": "tests/test_esd_energy_upper_bound.py",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "quote": "- 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_api.py`、`test_esd_regression.py`）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "tests/test_esd_energy_upper_bound.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:13",
          "kind": "source_code_reference",
          "label": "test_esd_devices.py",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "quote": "- 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_api.py`、`test_esd_regression.py`）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "test_esd_devices.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:14",
          "kind": "source_code_reference",
          "label": "test_esd_benchmark.py",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "quote": "- 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_api.py`、`test_esd_regression.py`）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "test_esd_benchmark.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:15",
          "kind": "source_code_reference",
          "label": "test_esd_api.py",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "quote": "- 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_api.py`、`test_esd_regression.py`）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "test_esd_api.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:16",
          "kind": "source_code_reference",
          "label": "test_esd_regression.py",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "quote": "- 测试：63 例全绿（`tests/test_esd_energy_upper_bound.py`、`test_esd_devices.py`、`test_esd_benchmark.py`、`test_esd_api.py`、`test_esd_regression.py`）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "test_esd_regression.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:17",
          "kind": "document_reference",
          "label": "docs/ESD_ENERGY_SAVING.md",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 123,
            "start_char": 6780,
            "end_char": 6819,
            "quote": "- 文档：`docs/ESD_ENERGY_SAVING.md`（六要素全文）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "docs/ESD_ENERGY_SAVING.md",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:18",
          "kind": "capability_declaration_reference",
          "label": "propulsion.esd_energy_saving = REAL",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 124,
            "start_char": 6820,
            "end_char": 6901,
            "quote": "- 能力：`propulsion.esd_energy_saving = REAL`（`artifacts/esd/capability_delta.json`）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "propulsion.esd_energy_saving = REAL",
          "resolution": {
            "status": "declared_reference_only",
            "scope": "declared_in_prose_only",
            "reason": "the report declares this capability grade; this 工序 records the declaration verbatim and does NOT verify it (the platform gate computes verification), so no grade is endorsed here"
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:19",
          "kind": "data_artifact_reference",
          "label": "artifacts/esd/capability_delta.json",
          "section": "审计链",
          "locator": {
            "source_field": "markdown",
            "line": 124,
            "start_char": 6820,
            "end_char": 6901,
            "quote": "- 能力：`propulsion.esd_energy_saving = REAL`（`artifacts/esd/capability_delta.json`）",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "token": "artifacts/esd/capability_delta.json",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree TensorKnowledge",
            "reason": "declared by report 11363 as a ship-performance-platform artefact; not present in the delivery worktree, and this 工序 does not cross repository boundaries to fetch bytes",
            "same_basename_hits": []
          },
          "further_occurrences": []
        },
        {
          "asset_id": "r11363:ref:upstream-resistance",
          "kind": "upstream_dependency_reference",
          "label": "Holtrop-1984 resistance kernel feeding R_T",
          "section": "① 案例介绍（物理背景与几何",
          "locator": {
            "source_field": "markdown",
            "line": 15,
            "start_char": 722,
            "end_char": 892,
            "quote": "几何先验全通过：Cb 与 ∇/(L·B·T) 偏差 <0.02，L/B∈[4,11]、B/T∈[1.8,6]、D/T∈[0.35,0.90]、P/D∈[0.5,1.6]、Ae/Ao∈[0.3,1.2]；任一越界即拒绝（API 422），不外推。R_T 由阻力端点同源 Holtrop-1984 核注入（ESD 模块不重复算阻力，避免双源）。",
            "quote_verified": true,
            "count_occurrences": 1,
            "unique": true,
            "method": "char_span"
          },
          "resolution": {
            "status": "referenced_unresolved",
            "scope": "declared_in_prose_only",
            "reason": "report states R_T comes from the resistance endpoint's Holtrop-1984 kernel but gives no path/URI; not derivable without leaving this 工序"
          }
        }
      ],
      "locators": {
        "count": 25,
        "all_in_markdown": true,
        "all_back_read_ok": true,
        "all_verified": true,
        "checks": [
          {
            "asset_id": "r11363:source-markdown",
            "line": 1,
            "start_char": 0,
            "end_char": 29,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:figure:01",
            "line": 87,
            "start_char": 5056,
            "end_char": 5117,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:figure:02",
            "line": 88,
            "start_char": 5118,
            "end_char": 5193,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:figure:03",
            "line": 89,
            "start_char": 5194,
            "end_char": 5260,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:figure:04",
            "line": 90,
            "start_char": 5261,
            "end_char": 5323,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:01",
            "line": 3,
            "start_char": 31,
            "end_char": 146,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:02",
            "line": 19,
            "start_char": 921,
            "end_char": 1145,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:03",
            "line": 19,
            "start_char": 921,
            "end_char": 1145,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:04",
            "line": 20,
            "start_char": 1146,
            "end_char": 1392,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:05",
            "line": 20,
            "start_char": 1146,
            "end_char": 1392,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:06",
            "line": 20,
            "start_char": 1146,
            "end_char": 1392,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:07",
            "line": 22,
            "start_char": 1537,
            "end_char": 1620,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:08",
            "line": 23,
            "start_char": 1621,
            "end_char": 1728,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:09",
            "line": 119,
            "start_char": 6383,
            "end_char": 6530,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:10",
            "line": 120,
            "start_char": 6531,
            "end_char": 6579,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:11",
            "line": 121,
            "start_char": 6580,
            "end_char": 6638,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:12",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:13",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:14",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:15",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:16",
            "line": 122,
            "start_char": 6639,
            "end_char": 6779,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:17",
            "line": 123,
            "start_char": 6780,
            "end_char": 6819,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:18",
            "line": 124,
            "start_char": 6820,
            "end_char": 6901,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:19",
            "line": 124,
            "start_char": 6820,
            "end_char": 6901,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          },
          {
            "asset_id": "r11363:ref:upstream-resistance",
            "line": 15,
            "start_char": 722,
            "end_char": 892,
            "in_markdown": true,
            "back_read_ok": true,
            "count_occurrences": 1
          }
        ]
      },
      "bundle_consistency": {
        "declared_in_manifest_line": 10,
        "enumerated_members": [
          "benchmark_results.json",
          "golden_regression.json",
          "per_device_table.csv",
          "combined_table.csv",
          "report_tables.md",
          "4 张 png",
          "manifest.json"
        ],
        "member_file_count": 10,
        "matches": true,
        "quote": "- 工件：`artifacts/esd/`（benchmark_results.json、golden_regression.json、per_device_table.csv、combined_table.csv、report_tables.md、4 张 png、manifest.json）",
        "line": 119
      },
      "identity_facts": {
        "report_id_matches_contract": true,
        "source_hash_matches_contract": true,
        "chars_match_contract": true,
        "title_matches_contract": true,
        "scenario_matches_contract": true,
        "figure_count_in_record": 4
      },
      "claims": [],
      "claims_empty_reason": "objective.classify_report_type=false and the contract allows claims==[]; this 工序 registers assets only, so no claim is generated and no claim is marked verified (do_not_mark_claims_as_verified / no_forced_claim_generation).",
      "counts": {
        "assets_total": 25,
        "figures_declared_in_record": 4,
        "figures_with_bytes": 4,
        "assets_by_status": {
          "resolved": 1,
          "resolved_with_bytes": 4,
          "unresolved": 13,
          "referenced_unresolved": 6,
          "declared_reference_only": 1
        },
        "kind_status_histogram": {
          "report_markdown/resolved": 1,
          "embedded_figure/resolved_with_bytes": 4,
          "source_directory_reference/unresolved": 2,
          "source_code_reference/unresolved": 8,
          "symbol_reference/referenced_unresolved": 5,
          "data_artifact_reference/unresolved": 2,
          "document_reference/unresolved": 1,
          "capability_declaration_reference/declared_reference_only": 1,
          "upstream_dependency_reference/referenced_unresolved": 1
        },
        "locators": 25,
        "claims": 0
      },
      "id_integrity": {
        "count": 25,
        "unique": true,
        "duplicate_ids": [],
        "pattern_ok": true
      },
      "unresolved": [
        "r11363:ref:01",
        "r11363:ref:02",
        "r11363:ref:03",
        "r11363:ref:04",
        "r11363:ref:05",
        "r11363:ref:06",
        "r11363:ref:07",
        "r11363:ref:08",
        "r11363:ref:09",
        "r11363:ref:10",
        "r11363:ref:11",
        "r11363:ref:12",
        "r11363:ref:13",
        "r11363:ref:14",
        "r11363:ref:15",
        "r11363:ref:16",
        "r11363:ref:17",
        "r11363:ref:19",
        "r11363:ref:upstream-resistance"
      ],
      "observations": [
        "Report 11363 is a results report of a finished work node (mission 9564): its 审计链 section enumerates a 10-file artefact bundle under artifacts/esd/ that lives in another repository, so registration can only confirm the references, not the bytes.",
        "All four figures are declared in the platform record with captions, but the /figures byte endpoints answer 404, so no figure hash is claimed.",
        "The report's own internal consistency (bundle line '10 文件' vs the enumerated members) is checked arithmetically in bundle_consistency; it is a consistency note, not a verification of the upstream artefact."
      ],
      "limitations": [
        "Registration only: no claim/evidence extraction, no report-type classification, no verified marks (verification is computed by the platform gate).",
        "source_hash scope = UTF-8 bytes of the markdown string returned by the platform API; any change to the stored markdown, even whitespace, invalidates it.",
        "Resolution is probed against the delivery worktree (TensorKnowledge) only; report 11363's artefacts live in ship-performance-platform and are therefore reported as unresolved rather than fetched across repositories.",
        "Quotes are whole markdown lines, so char spans include table pipes / leading list markers; they are verbatim and re-verifiable, not minimal spans.",
        "Report 11363 makes domain claims (<15% literature agreement, energy upper bound gate). Registering them would be extraction, which is explicitly out of this package's scope; none of them is endorsed or refuted here."
      ]
    }
  },
  "claims": []
}
```
