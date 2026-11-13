# KF-RESULT wp-10329-01

**工序**：01-asset-registration（资产登记，lane C）· **report_id**：10329 ·
**源**：`tensor://reports/10329`（field=`markdown`）·
**来源标题**：IN13-W3-N03 碎冰/冰晶悬浮液有效粘度闭合的 LBM 标定（含诚实负面结果） ·
**scenario_key**：`in13_w3_n03_suspension_rheology` ·
**producer**：kf-worker/m15679 · **manifest generated_at**：2026-11-12T01:44:59.430331+00:00 ·
**envelope emitted_at**：2026-11-12T01:42:44.536965+00:00

> 边界声明：本工序只登记源资产（report_id、markdown 字节哈希、报告声明的附件/工件/图/算例 id），
> **不做任何抽取、不做报告分类、不标 verified**（verification 由平台门计算）。
> claims 为空数组是契约允许的完整结果，不是缺项。

## ① 本工序做了什么

1. 拉取 `GET /api/v1/tensor/reports/10329`，取 `markdown` 字段（UTF-8 字节）重算 sha256，
   与契约声明值逐字符比对：**一致**（`sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d`，chars=7644，
   lines=211），并把源字节落盘为 `docs/kf/wp-10329-01/source/r10329.md` 作为哈希锚。
2. 枚举报告**声明**的四类资产：正文路径引用（脚本/测试/工件 JSON/图），
   记录元数据里声明的 5 张图（name+caption，另从图服务取字节算哈希），
   散文里点名的代码模块，以及验收表/阻力表里出现的算例 id。
3. 给每个资产一个可复算的定位器（markdown 行号 + 逐字引文 + 引文 sha256 + 出现次数），
   并在 verify 阶段对**实时 markdown** 复解一遍（35/35 解出）。
4. 不做的事：不打开 TensorLBM 仓、不判定报告结论真假、不给任何资产/数值标 verified。

## ② 怎么做的（步骤 / 工具 / 关键设置）

* 通道：平台 API（`/auth/login` 拿 token → `GET /tensor/reports/10329`；
  图的字节走 `GET /tensor/reports/10329/figures/<name>`）。
  **psql 直读被拒**（`permission denied for table tensor_reports`），因此只走 API 单通道，
  已在 manifest 的 limitations 里写明。
* 定位器方法：`char_span` 型——以「1-based 逻辑行号（`markdown.rstrip('\n').split('\n')`）+
  整行逐字引文」为锚，`quote_sha256` 与 `occurrences_in_source` 一并记录；
  verify 时不读缓存、重新拉取实时 markdown 复解。
* 引用提取是**程序化正则**（Markdown 图片链接、反引号路径、裸路径）而非人眼转录；
  反引号 token 只有带已知扩展名或形如纯路径字符组成的目录路径才算路径
  （模块名 `tensorlbm.*`、表达式 `(1-1/2τ)` 都被排除，避免假资产）。
* 算例 id 从两处**逐字结构**解析：§6 验收表的 `wall_momentum_balance` 字典字面量键（L187），
  与 §3.3 阻力表首列（L94–L95）。共 13 个。
* 解析范围仅限交付工作树（TensorKnowledge）。报告声明的 TensorLBM 产物在本树内不存在，
  一律登记为 `unresolved` 并附同基名命中列表，**不冒充上游缺失**；
  图资产因图服务返回真 PNG 字节而 `resolved`（含本地副本 + sha256）。
* 信封：`kf_result.json` 的 `provenance.source_hash` 在写信封前**重新拉取**实时 markdown 重算，
  与 manifest 不一致则拒绝写信封（fail loud）。
* 工具链：Python 3 stdlib（urllib/hashlib/json/re）+ jsonschema（结构门自检）+ matplotlib（图）。

## ③ 产出物清单（输出文件 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-10329-01/asset_manifest.json` | 资产清单主体：22 个资产 + 1 个声明集合 + 4 个模块引用 + 13 个算例 id；35 个定位器全部可解；claims=[]（附空数组理由） |
| `docs/kf/wp-10329-01/kf_result.json` | 平台结果信封（`kf_result.v1` 结构）：package_id/task_type/report_id/provenance/outputs；`source_hash=sha256:9541130e9906db22f2d…` |
| `docs/kf/wp-10329-01/verification.json` | 6 项 acceptance 自检 + 3 项附加检查（本地字节复算/无 verified 标记/本地 448 专用 schema 不适用说明） |
| `docs/kf/wp-10329-01/source/r10329.md` | 源 markdown 本地副本（哈希锚，11225 bytes / 7644 chars） |
| `docs/kf/wp-10329-01/figures/r10329/*.png` | 报告声明的 5 张图字节（从图服务取回，逐张 sha256 记录） |
| `docs/kf/wp-10329-01/figures/asset_resolution_map.png` | 本工序自产图：资产按 kind×resolution 的堆叠分布（数字与 manifest 同源） |
| `scripts/kf_wp10329_01_register.py` | 可复跑登记器：`build / envelope / verify / figure / all` |
| `scripts/kf_wp10329_01_report.py` | 报告渲染 + 发布器（校验「唯一一个 json 块」与逐字引文再验） |

### 资产明细（22 条，按 resolution 分布：{"resolved": 11, "unresolved": 11}）

| asset_id | kind | name | sha256(head) | resolution | via / reason |
|---|---|---|---|---|---|
| `r10329:source-markdown` | report_markdown | ⟦report-10329-markdown⟧ | `sha256:9541130e9906` | resolved | ⟦GET /tensor/reports/10329⟧ |
| `r10329:figure:01` | embedded_figure | ⟦eta_rel_vs_phi.png⟧ | `sha256:4ea9620fba0e` | resolved | ⟦GET /tensor/reports/10329/figures/eta_rel_vs_phi.png⟧ |
| `r10329:figure:02` | embedded_figure | ⟦eta_rel_vs_Rep.png⟧ | `sha256:7965fbb805b1` | resolved | ⟦GET /tensor/reports/10329/figures/eta_rel_vs_Rep.png⟧ |
| `r10329:figure:03` | embedded_figure | ⟦drag_curve.png⟧ | `sha256:c8a1fffe1074` | resolved | ⟦GET /tensor/reports/10329/figures/drag_curve.png⟧ |
| `r10329:figure:04` | embedded_figure | ⟦applicability_map.png⟧ | `sha256:767275078ec2` | resolved | ⟦GET /tensor/reports/10329/figures/applicability_map.png⟧ |
| `r10329:figure:05` | embedded_figure | ⟦apparatus_audit.png⟧ | `sha256:e59fee216a63` | resolved | ⟦GET /tensor/reports/10329/figures/apparatus_audit.png⟧ |
| `r10329:ref:01` | source_code_reference | ⟦benchmarks/suspension_rheology_calib.py⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:02` | source_code_reference | ⟦tests/test_suspension_rheology.py⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:03` | data_artifact_reference | ⟦artifacts/suspension_rheology/calibration.json⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:04` | directory_reference | ⟦figures/suspension_rheology/⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:05` | data_artifact_reference | ⟦calibration.json⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:06` | figure_reference | ⟦figures/suspension_rheology/eta_rel_vs_phi.png⟧ | `sha256:4ea9620fba0e` | resolved | ⟦cross-reference to r10329:figure:01 (basename match, bytes hashed there)⟧ |
| `r10329:ref:07` | figure_reference | ⟦figures/suspension_rheology/eta_rel_vs_Rep.png⟧ | `sha256:7965fbb805b1` | resolved | ⟦cross-reference to r10329:figure:02 (basename match, bytes hashed there)⟧ |
| `r10329:ref:08` | figure_reference | ⟦figures/suspension_rheology/drag_curve.png⟧ | `sha256:c8a1fffe1074` | resolved | ⟦cross-reference to r10329:figure:03 (basename match, bytes hashed there)⟧ |
| `r10329:ref:09` | figure_reference | ⟦figures/suspension_rheology/applicability_map.png⟧ | `sha256:767275078ec2` | resolved | ⟦cross-reference to r10329:figure:04 (basename match, bytes hashed there)⟧ |
| `r10329:ref:10` | figure_reference | ⟦figures/suspension_rheology/apparatus_audit.png⟧ | `sha256:e59fee216a63` | resolved | ⟦cross-reference to r10329:figure:05 (basename match, bytes hashed there)⟧ |
| `r10329:ref:11` | data_artifact_reference | ⟦calibration.json⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:12` | source_code_reference | ⟦benchmarks/suspension_rheology_calib.py⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:13` | source_code_reference | ⟦benchmarks/suspension_rheology_calib.py⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:14` | source_code_reference | ⟦benchmarks/suspension_rheology_calib.py⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:15` | source_code_reference | ⟦benchmarks/suspension_rheology_doc.py⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |
| `r10329:ref:16` | source_code_reference | ⟦tests/test_suspension_rheology.py⟧ | `-` | unresolved | ⟦path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)⟧ |

### 声明集合（无路径，只有描述）

| set_id | label | locator | resolution |
|---|---|---|---|
| `r10329:set:01` | artifacts/suspension_rheology/<per-case>.json | L8 | unresolved |

### 模块引用（declared_only）

| symbol_id | token | locator | resolution |
|---|---|---|---|
| `r10329:sym:01` | `tensorlbm.suspension_lbm` | L4 | declared_only |
| `r10329:sym:02` | `tensorlbm.suspension_rheology` | L5 | declared_only |
| `r10329:sym:03` | `tensorlbm.frazil_rheology` | L17 | declared_only |
| `r10329:sym:04` | `contract.bingham_handoff` | L112 | declared_only |

### 算例 id（13 个，仅声明）

`drag_re012`, `drag_re090`, `chk_radius4`, `control`, `phi_002`, `phi_005`, `phi_010`, `phi_020`, `phi_020_seed1`, `phi_030`, `phi_040`, `re_004`, `re_035`

## ④ 证据定位表（字段 → 原文逐字片段）

| 定位对象 | 行 | 逐字引文（截断显示） | quote_sha256(head) | 出现次数 |
|---|---|---|---|---|
| `r10329:source-markdown` | L1 | ⟦# IN13-W3-N03 — 碎冰/冰晶悬浮液有效粘度闭合的 LBM 标定⟧ | `47e174d38e53` | 1 |
| `r10329:figure:01` | record `/figures/*/name` | ⟦eta_rel_vs_phi.png⟧ | `4ea9620fba0e` (bytes) | 1 |
| `r10329:figure:05` | record `/figures/*/name` | ⟦apparatus_audit.png⟧ | `e59fee216a63` (bytes) | 1 |
| `r10329:ref:01` | L6 | ⟦**标定脚本**：'benchmarks/suspension_rheology_calib.py' ·⟧ | `98f3cf6ff569` | 1 |
| `r10329:ref:03` | L8 | ⟦**工件**：'artifacts/suspension_rheology/calibration.json'（+ 每例原始 JSON）·⟧ | `0b2fa0ee957a` | 1 |
| `r10329:set:01` | L8 | ⟦**工件**：'artifacts/suspension_rheology/calibration.json'（+ 每例原始 JSON）·⟧ | `0b2fa0ee957a` | 1 |
| `r10329:sym:01` | L4 | ⟦**仓库**：TensorLBM · **模块**：'tensorlbm.suspension_lbm'（测量内核）、⟧ | `28873e236cd6` | 1 |
| `r10329:sym:02` | L5 | ⟦'tensorlbm.suspension_rheology'（闭合/契约层）·⟧ | `3c51fcd0cec2` | 1 |

### 文档身份事实（结构地标，防止「换了文档仍报同一哈希」）

| fact_id | 行 | 逐字引文 |
|---|---|---|
| title-line | L1 | ⟦# IN13-W3-N03 — 碎冰/冰晶悬浮液有效粘度闭合的 LBM 标定⟧ |
| node-block | L3 | ⟦**节点**：IN13-W3-N03（物理域，全新前沿）·⟧ |
| sec1-header | L13 | ⟦## 1. 案例介绍（物理背景 / 几何 / 参数）⟧ |
| sec6-header | L166 | ⟦## 6. 误差判定（逐项，明确回答是否 <3%）⟧ |
| repro-fence | L205 | ⟦'''bash⟧ |
| last-line | L211 | ⟦'''⟧ |

源字段比对（契约 vs 实测，全部由脚本重算）：

| 契约字段 | 契约值 | 实测值 | 一致 |
|---|---|---|---|
| source_hash | `sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d` | `sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d` | ✓ |
| chars | 7644 | 7644 | ✓ |
| title | （见契约） | IN13-W3-N03 碎冰/冰晶悬浮液有效粘度闭合的 LBM 标定（含诚实负面结果） | ✓ |
| scenario_key | `in13_w3_n03_suspension_rheology` | `in13_w3_n03_suspension_rheology` | ✓ |

## ⑤ 注意点与局限

1. **登记 ≠ 内容正确**。本工序只证明「报告 10329 的 markdown 是这个字节序列，它声明了这些资产」，
   不证明报告里的 η_r 表、KD 拟合、C_D 误差成立。原报告 §6 自带 4 FAIL / 4 PASS 的诚实判定，
   不在本工序复判（也不得标 verified）。
2. **图服务确实有字节**（5/5 张返回 `image/png`，PNG magic 校验通过），因此图资产是 `resolved` 带哈希；
   我在 manifest 里没有对图内容（曲线数值）做任何断言。
3. **正文路径一律 unresolved**：`tensorlbm/*`、`benchmarks/*`、`tests/*`、`artifacts/suspension_rheology/*`
   属 TensorLBM 仓，不在本交付树。这是**解析范围限制**，不是上游缺件；`existence_asserted_by_worker=false`。
4. **`（+ 每例原始 JSON）` 无路径**：报告没有给出每例文件名/命名模式，
   因此登记为 `declared_artifact_set`（unresolved），只把验收表里逐字出现的 13 个算例 id 记下来。
   若下游要逐例 JSON，需要上游补命名契约——这是本工序**没有**解决的部分，如实记在此。
5. **单通道读取**：psql 直读被权限拒绝，只有 API 一路；两者本应是同一列，但仍属单点。
6. **本地 `schemas/asset_manifest.v1.schema.json` 不适用**：它把 `package_id`/`report_id` 用 const 钉死在
   wp-448-01/448，无法校验本包；契约点名的结构门是 `kf_result.v1`（信封自检 0 error）。
   已在 verification.extra_checks 里写明，避免把「不适用的 schema 通过」当成绩。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 明细 |
|---|---|---|
| valid_json | ✓ PASS | asset_manifest.json + kf_result.json parsed |
| schema_pass | ✓ PASS | kf_result.v1 schema: 0 errors |
| source_locator_resolvable | ✓ PASS | 35/35 markdown locators re-resolved (line + verbatim + quote_sha256) |
| source_hash_matches | ✓ PASS | live=sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d manifest=sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d contract=sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d |
| no_duplicate_ids | ✓ PASS | 23 ids, duplicates=[] |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ PASS | 0 claims (empty allowed by contract); empty-claims reason stated: True |

附加检查（非契约项，保护产物本身）：

| extra check | 结果 | 明细 |
|---|---|---|
| stored_bytes_match_recorded_sha256 | ✓ PASS | re-hashed 6 local copies on disk (0 mismatch, 0 copies would be a bug) |
| no_verified_marks | ✓ PASS | result carries 0 claims and no `verified` key; verification is the gate's |
| local_asset_manifest_v1_applicable | ✓ PASS | schemas/asset_manifest.v1.schema.json pins package_id const='wp-448-01' and report_id const='448', so it cannot validate wp-10329-01; it is the wp-448-01 local shape, not the canonical gate (contract names kf_result.v1) |

**总判定**：`all_ok = True`。若有失败项应如实写；本次无一失败，
且 `no_verified_marks` 通过（结果里 0 claims、无 `verified` 键）。
本自检是**自证**，平台门会独立重算哈希与定位器，门的结果优先于本表。

## 图

![asset resolution map](asset_resolution_map.png)

**图 1** 报告 10329 的资产登记分布：横轴=资产数，纵轴=资产类别，颜色=解析状态
（resolved=11 含 1 份 markdown + 5 张图资产 + 5 条正文图引用交叉解析；unresolved=11 为 TensorLBM 仓内路径）。
本工序不产生物理场量，因此没有云图；报告自带的 η_r–φ、C_D–Re 等图作为源资产按字节登记
（`figures/r10329/*.png`，逐张 sha256 已记录），不在本工序复现或复判。

## 复现命令（一键）

```bash
cd "$(git rev-parse --show-toplevel)"           # 仓库根 = TensorKnowledge 工作树
python3 scripts/kf_wp10329_01_register.py all   # build→envelope→figure→verify（需要 TENSOR_API_BASE/USER/PASS）
python3 scripts/kf_wp10329_01_report.py render  # 生成本报告 markdown
python3 scripts/kf_wp10329_01_report.py publish # 发布到平台（同标题幂等）
```

## 结果 JSON（唯一一个 json 代码块，与 kf_result.json 逐字节一致）

```json
{
  "package_id": "wp-10329-01",
  "task_type": "01-asset-registration",
  "report_id": "10329",
  "provenance": {
    "source_hash": "sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d",
    "source_field": "markdown",
    "producer": "kf-worker/m15679",
    "emitted_at": "2026-11-12T01:42:44.536965+00:00",
    "notes": "hash recomputed from GET /api/v1/tensor/reports/10329 markdown (UTF-8 bytes); matches contract source_hash sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-10329-01",
      "task_type": "01-asset-registration",
      "report_id": "10329",
      "lane": "C",
      "generated_at": "2026-11-12T01:42:44.118427+00:00",
      "producer": "kf-worker/m15679",
      "source": {
        "report_id": "10329",
        "source_uri": "tensor://reports/10329",
        "source_field": "markdown",
        "source_hash": "sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d",
        "contract_source_hash": "sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d",
        "hash_algo": "sha256",
        "hash_match": true,
        "chars": 7644,
        "contract_chars": 7644,
        "chars_match_contract": true,
        "bytes": 11225,
        "lines": 211,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
        "fetched_via": "GET /api/v1/tensor/reports/10329",
        "record_fields": {
          "title": "IN13-W3-N03 碎冰/冰晶悬浮液有效粘度闭合的 LBM 标定（含诚实负面结果）",
          "scenario_key": "in13_w3_n03_suspension_rheology",
          "mission_id": 6911,
          "status": "published",
          "tags": [
            "IN13-W3-N03",
            "TensorLBM",
            "suspension",
            "rheology",
            "Krieger-Dougherty",
            "mu(I)",
            "IBM",
            "honest-FAIL"
          ],
          "created_at": "2026-11-10T02:44:50.740758+00:00",
          "contract_title": "IN13-W3-N03 碎冰/冰晶悬浮液有效粘度闭合的 LBM 标定（含诚实负面结果）",
          "contract_scenario_key": "in13_w3_n03_suspension_rheology",
          "contract_layer": "IN13-W3-N03|in13_w3_n03_suspension_rheology|m",
          "title_matches_contract": true,
          "scenario_matches_contract": true
        },
        "platform_attachment_probes": {
          "GET /tensor/reports/10329/artifacts": "not_probed_here",
          "figure_probe": {
            "eta_rel_vs_phi.png": {
              "http_status": 200,
              "bytes": 75602,
              "media_type": "image/png",
              "sha256": "sha256:4ea9620fba0e1e6edf2ba0e5c8d66ee86a1f8a7f0552cf252f5d4104bbb24922",
              "png_magic_ok": true,
              "local_copy": "docs/kf/wp-10329-01/figures/r10329/eta_rel_vs_phi.png"
            },
            "eta_rel_vs_Rep.png": {
              "http_status": 200,
              "bytes": 67248,
              "media_type": "image/png",
              "sha256": "sha256:7965fbb805b1dcacb63be4113f81db5fb5e2f7741b885d98aeda376adc346d8e",
              "png_magic_ok": true,
              "local_copy": "docs/kf/wp-10329-01/figures/r10329/eta_rel_vs_Rep.png"
            },
            "drag_curve.png": {
              "http_status": 200,
              "bytes": 53390,
              "media_type": "image/png",
              "sha256": "sha256:c8a1fffe10748d166847b87ba7ae1d27ed4c67979676e4809515bd42f9819db3",
              "png_magic_ok": true,
              "local_copy": "docs/kf/wp-10329-01/figures/r10329/drag_curve.png"
            },
            "applicability_map.png": {
              "http_status": 200,
              "bytes": 28274,
              "media_type": "image/png",
              "sha256": "sha256:767275078ec2c6de9388499478db48ca8d1cb9d892be8ac99231dc548012d771",
              "png_magic_ok": true,
              "local_copy": "docs/kf/wp-10329-01/figures/r10329/applicability_map.png"
            },
            "apparatus_audit.png": {
              "http_status": 200,
              "bytes": 138261,
              "media_type": "image/png",
              "sha256": "sha256:e59fee216a632e0f798ed5adf032881c06de21033503a1e6374e8de0c1e54a98",
              "png_magic_ok": true,
              "local_copy": "docs/kf/wp-10329-01/figures/r10329/apparatus_audit.png"
            }
          }
        }
      },
      "assets": [
        {
          "asset_id": "r10329:source-markdown",
          "kind": "report_markdown",
          "name": "report-10329-markdown",
          "locator": {
            "source_field": "markdown",
            "line": 1
          },
          "source_uri": "tensor://reports/10329",
          "media_type": "text/markdown",
          "bytes": 11225,
          "chars": 7644,
          "lines": 211,
          "sha256": "sha256:9541130e9906db22f2da835d346b0205d8e573cd9812d989094e227b7971ec7d",
          "hash_scope": "UTF-8 bytes of the markdown field as served by GET /api/v1/tensor/reports/10329",
          "local_copy": "docs/kf/wp-10329-01/source/r10329.md",
          "resolution": {
            "status": "resolved",
            "scope": "platform_api",
            "via": "GET /tensor/reports/10329"
          },
          "hash_matches_contract": true,
          "chars_matches_contract": true
        },
        {
          "asset_id": "r10329:figure:01",
          "kind": "embedded_figure",
          "name": "eta_rel_vs_phi.png",
          "caption": "实测 eta_r(phi)（误差棒为块平均标准误）与 Einstein 直线、标定 KD、文献 KD 对照",
          "locator": {
            "source_field": "record",
            "pointer": "/figures/0/name",
            "quote": "eta_rel_vs_phi.png"
          },
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "GET /tensor/reports/10329/figures/eta_rel_vs_phi.png",
            "http_status": 200,
            "bytes": 75602,
            "sha256": "sha256:4ea9620fba0e1e6edf2ba0e5c8d66ee86a1f8a7f0552cf252f5d4104bbb24922",
            "media_type": "image/png",
            "local_copy": "docs/kf/wp-10329-01/figures/r10329/eta_rel_vs_phi.png"
          }
        },
        {
          "asset_id": "r10329:figure:02",
          "kind": "embedded_figure",
          "name": "eta_rel_vs_Rep.png",
          "caption": "固定 phi=0.20 的速率依赖（惯性支）：冻结微结构给出零速率依赖",
          "locator": {
            "source_field": "record",
            "pointer": "/figures/1/name",
            "quote": "eta_rel_vs_Rep.png"
          },
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "GET /tensor/reports/10329/figures/eta_rel_vs_Rep.png",
            "http_status": 200,
            "bytes": 67248,
            "sha256": "sha256:7965fbb805b1dcacb63be4113f81db5fb5e2f7741b885d98aeda376adc346d8e",
            "media_type": "image/png",
            "local_copy": "docs/kf/wp-10329-01/figures/r10329/eta_rel_vs_Rep.png"
          }
        },
        {
          "asset_id": "r10329:figure:03",
          "kind": "embedded_figure",
          "name": "drag_curve.png",
          "caption": "单颗粒 C_D(Re) 与 Stokes / Schiller-Naumann 对照",
          "locator": {
            "source_field": "record",
            "pointer": "/figures/2/name",
            "quote": "drag_curve.png"
          },
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "GET /tensor/reports/10329/figures/drag_curve.png",
            "http_status": 200,
            "bytes": 53390,
            "sha256": "sha256:c8a1fffe10748d166847b87ba7ae1d27ed4c67979676e4809515bd42f9819db3",
            "media_type": "image/png",
            "local_copy": "docs/kf/wp-10329-01/figures/r10329/drag_curve.png"
          }
        },
        {
          "asset_id": "r10329:figure:04",
          "kind": "embedded_figure",
          "name": "applicability_map.png",
          "caption": "适用域相图：每测点落在哪支闭合的容差内",
          "locator": {
            "source_field": "record",
            "pointer": "/figures/3/name",
            "quote": "applicability_map.png"
          },
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "GET /tensor/reports/10329/figures/applicability_map.png",
            "http_status": 200,
            "bytes": 28274,
            "sha256": "sha256:767275078ec2c6de9388499478db48ca8d1cb9d892be8ac99231dc548012d771",
            "media_type": "image/png",
            "local_copy": "docs/kf/wp-10329-01/figures/r10329/applicability_map.png"
          }
        },
        {
          "asset_id": "r10329:figure:05",
          "kind": "embedded_figure",
          "name": "apparatus_audit.png",
          "caption": "装置审计：J_xy(y) 动量通量剖面与 u_x(y) 平均速度剖面",
          "locator": {
            "source_field": "record",
            "pointer": "/figures/4/name",
            "quote": "apparatus_audit.png"
          },
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "GET /tensor/reports/10329/figures/apparatus_audit.png",
            "http_status": 200,
            "bytes": 138261,
            "sha256": "sha256:e59fee216a632e0f798ed5adf032881c06de21033503a1e6374e8de0c1e54a98",
            "media_type": "image/png",
            "local_copy": "docs/kf/wp-10329-01/figures/r10329/apparatus_audit.png"
          }
        },
        {
          "asset_id": "r10329:ref:01",
          "kind": "source_code_reference",
          "name": "benchmarks/suspension_rheology_calib.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 6,
            "quote": "**标定脚本**：`benchmarks/suspension_rheology_calib.py` ·"
          },
          "quote_token": "benchmarks/suspension_rheology_calib.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:02",
          "kind": "source_code_reference",
          "name": "tests/test_suspension_rheology.py",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 7,
            "quote": "**测试**：`tests/test_suspension_rheology.py` ·"
          },
          "quote_token": "tests/test_suspension_rheology.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:03",
          "kind": "data_artifact_reference",
          "name": "artifacts/suspension_rheology/calibration.json",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 8,
            "quote": "**工件**：`artifacts/suspension_rheology/calibration.json`（+ 每例原始 JSON）·"
          },
          "quote_token": "artifacts/suspension_rheology/calibration.json",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:04",
          "kind": "directory_reference",
          "name": "figures/suspension_rheology/",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 9,
            "quote": "**图**：`figures/suspension_rheology/`"
          },
          "quote_token": "figures/suspension_rheology/",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:05",
          "kind": "data_artifact_reference",
          "name": "calibration.json",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 65,
            "quote": "`u_x(y)` 剖面、壁面动量平衡残差、颗粒受力），`calibration.json` 只做"
          },
          "quote_token": "calibration.json",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:06",
          "kind": "figure_reference",
          "name": "figures/suspension_rheology/eta_rel_vs_phi.png",
          "reference_form": "markdown_image_link",
          "locator": {
            "source_field": "markdown",
            "line": 128,
            "quote": "![eta_r vs phi](figures/suspension_rheology/eta_rel_vs_phi.png)"
          },
          "quote_token": "figures/suspension_rheology/eta_rel_vs_phi.png",
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "cross-reference to r10329:figure:01 (basename match, bytes hashed there)",
            "bytes": 75602,
            "sha256": "sha256:4ea9620fba0e1e6edf2ba0e5c8d66ee86a1f8a7f0552cf252f5d4104bbb24922",
            "cross_reference": "r10329:figure:01",
            "note": "declared path itself is absent from the delivery worktree; the byte identity is established through the record figure store"
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:07",
          "kind": "figure_reference",
          "name": "figures/suspension_rheology/eta_rel_vs_Rep.png",
          "reference_form": "markdown_image_link",
          "locator": {
            "source_field": "markdown",
            "line": 133,
            "quote": "![eta_r vs Re_p](figures/suspension_rheology/eta_rel_vs_Rep.png)"
          },
          "quote_token": "figures/suspension_rheology/eta_rel_vs_Rep.png",
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "cross-reference to r10329:figure:02 (basename match, bytes hashed there)",
            "bytes": 67248,
            "sha256": "sha256:7965fbb805b1dcacb63be4113f81db5fb5e2f7741b885d98aeda376adc346d8e",
            "cross_reference": "r10329:figure:02",
            "note": "declared path itself is absent from the delivery worktree; the byte identity is established through the record figure store"
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:08",
          "kind": "figure_reference",
          "name": "figures/suspension_rheology/drag_curve.png",
          "reference_form": "markdown_image_link",
          "locator": {
            "source_field": "markdown",
            "line": 137,
            "quote": "![drag curve](figures/suspension_rheology/drag_curve.png)"
          },
          "quote_token": "figures/suspension_rheology/drag_curve.png",
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "cross-reference to r10329:figure:03 (basename match, bytes hashed there)",
            "bytes": 53390,
            "sha256": "sha256:c8a1fffe10748d166847b87ba7ae1d27ed4c67979676e4809515bd42f9819db3",
            "cross_reference": "r10329:figure:03",
            "note": "declared path itself is absent from the delivery worktree; the byte identity is established through the record figure store"
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:09",
          "kind": "figure_reference",
          "name": "figures/suspension_rheology/applicability_map.png",
          "reference_form": "markdown_image_link",
          "locator": {
            "source_field": "markdown",
            "line": 141,
            "quote": "![applicability](figures/suspension_rheology/applicability_map.png)"
          },
          "quote_token": "figures/suspension_rheology/applicability_map.png",
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "cross-reference to r10329:figure:04 (basename match, bytes hashed there)",
            "bytes": 28274,
            "sha256": "sha256:767275078ec2c6de9388499478db48ca8d1cb9d892be8ac99231dc548012d771",
            "cross_reference": "r10329:figure:04",
            "note": "declared path itself is absent from the delivery worktree; the byte identity is established through the record figure store"
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:10",
          "kind": "figure_reference",
          "name": "figures/suspension_rheology/apparatus_audit.png",
          "reference_form": "markdown_image_link",
          "locator": {
            "source_field": "markdown",
            "line": 145,
            "quote": "![audit](figures/suspension_rheology/apparatus_audit.png)"
          },
          "quote_token": "figures/suspension_rheology/apparatus_audit.png",
          "resolution": {
            "status": "resolved",
            "scope": "platform_figure_store",
            "via": "cross-reference to r10329:figure:05 (basename match, bytes hashed there)",
            "bytes": 138261,
            "sha256": "sha256:e59fee216a632e0f798ed5adf032881c06de21033503a1e6374e8de0c1e54a98",
            "cross_reference": "r10329:figure:05",
            "note": "declared path itself is absent from the delivery worktree; the byte identity is established through the record figure store"
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:11",
          "kind": "data_artifact_reference",
          "name": "calibration.json",
          "reference_form": "backticked_path",
          "locator": {
            "source_field": "markdown",
            "line": 176,
            "quote": "**判定**：验收表见下（机器判据，全部来自 `calibration.json`）："
          },
          "quote_token": "calibration.json",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:12",
          "kind": "source_code_reference",
          "name": "benchmarks/suspension_rheology_calib.py",
          "reference_form": "bare_path",
          "locator": {
            "source_field": "markdown",
            "line": 206,
            "quote": "python3 benchmarks/suspension_rheology_calib.py --plan        # 列算例"
          },
          "quote_token": "benchmarks/suspension_rheology_calib.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:13",
          "kind": "source_code_reference",
          "name": "benchmarks/suspension_rheology_calib.py",
          "reference_form": "bare_path",
          "locator": {
            "source_field": "markdown",
            "line": 207,
            "quote": "python3 benchmarks/suspension_rheology_calib.py --jobs 8      # 跑全部"
          },
          "quote_token": "benchmarks/suspension_rheology_calib.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:14",
          "kind": "source_code_reference",
          "name": "benchmarks/suspension_rheology_calib.py",
          "reference_form": "bare_path",
          "locator": {
            "source_field": "markdown",
            "line": 208,
            "quote": "python3 benchmarks/suspension_rheology_calib.py --assemble    # 聚合+图+验收"
          },
          "quote_token": "benchmarks/suspension_rheology_calib.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:15",
          "kind": "source_code_reference",
          "name": "benchmarks/suspension_rheology_doc.py",
          "reference_form": "bare_path",
          "locator": {
            "source_field": "markdown",
            "line": 209,
            "quote": "python3 benchmarks/suspension_rheology_doc.py                 # 生成本报告"
          },
          "quote_token": "benchmarks/suspension_rheology_doc.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        },
        {
          "asset_id": "r10329:ref:16",
          "kind": "source_code_reference",
          "name": "tests/test_suspension_rheology.py",
          "reference_form": "bare_path",
          "locator": {
            "source_field": "markdown",
            "line": 210,
            "quote": "python3 -m pytest tests/test_suspension_rheology.py -q"
          },
          "quote_token": "tests/test_suspension_rheology.py",
          "resolution": {
            "status": "unresolved",
            "scope": "delivery_worktree",
            "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)",
            "same_basename_hits": []
          },
          "declared_in_report": true,
          "existence_asserted_by_worker": false
        }
      ],
      "declared_artifact_sets": [
        {
          "set_id": "r10329:set:01",
          "kind": "declared_artifact_set",
          "label": "artifacts/suspension_rheology/<per-case>.json",
          "locator": {
            "source_field": "markdown",
            "line": 8,
            "quote": "**工件**：`artifacts/suspension_rheology/calibration.json`（+ 每例原始 JSON）·"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "declaration_only",
            "reason": "report declares '+ 每例原始 JSON' but states no per-case file name or path pattern; the case ids themselves are registered below from the acceptance table"
          },
          "existence_asserted_by_worker": false
        }
      ],
      "symbol_references": [
        {
          "symbol_id": "r10329:sym:01",
          "kind": "module_reference",
          "token": "tensorlbm.suspension_lbm",
          "locator": {
            "source_field": "markdown",
            "line": 4,
            "quote": "**仓库**：TensorLBM · **模块**：`tensorlbm.suspension_lbm`（测量内核）、"
          },
          "resolution": {
            "status": "declared_only",
            "reason": "named in the report prose; this工序 registers the reference, it does not open the TensorLBM repository"
          },
          "existence_asserted_by_worker": false
        },
        {
          "symbol_id": "r10329:sym:02",
          "kind": "module_reference",
          "token": "tensorlbm.suspension_rheology",
          "locator": {
            "source_field": "markdown",
            "line": 5,
            "quote": "`tensorlbm.suspension_rheology`（闭合/契约层）·"
          },
          "resolution": {
            "status": "declared_only",
            "reason": "named in the report prose; this工序 registers the reference, it does not open the TensorLBM repository"
          },
          "existence_asserted_by_worker": false
        },
        {
          "symbol_id": "r10329:sym:03",
          "kind": "module_reference",
          "token": "tensorlbm.frazil_rheology",
          "locator": {
            "source_field": "markdown",
            "line": 17,
            "quote": "内核的 phi-依赖项。此前仓内只有**解析闭合面**（`tensorlbm.frazil_rheology`："
          },
          "resolution": {
            "status": "declared_only",
            "reason": "named in the report prose; this工序 registers the reference, it does not open the TensorLBM repository"
          },
          "existence_asserted_by_worker": false
        },
        {
          "symbol_id": "r10329:sym:04",
          "kind": "module_reference",
          "token": "contract.bingham_handoff",
          "locator": {
            "source_field": "markdown",
            "line": 112,
            "quote": "契约要点（`contract.bingham_handoff`）："
          },
          "resolution": {
            "status": "declared_only",
            "reason": "named in the report prose; this工序 registers the reference, it does not open the TensorLBM repository"
          },
          "existence_asserted_by_worker": false
        }
      ],
      "measurement_cases": [
        {
          "case_id": "drag_re012",
          "case_ref": "r10329:case:drag_re012",
          "locator": {
            "source_field": "markdown",
            "line": 94,
            "quote": "| drag_re012 | 0.12 | 172.6 | 200 | stokes | -13.7% |"
          },
          "derivation": "first column of a case row in the §3.3 drag-gate table",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "drag_re090",
          "case_ref": "r10329:case:drag_re090",
          "locator": {
            "source_field": "markdown",
            "line": 95,
            "quote": "| drag_re090 | 0.9 | 34.59 | 36.16 | hasimoto_box_corrected_stokes | -4.3% |"
          },
          "derivation": "first column of a case row in the §3.3 drag-gate table",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "chk_radius4",
          "case_ref": "r10329:case:chk_radius4",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "control",
          "case_ref": "r10329:case:control",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "phi_002",
          "case_ref": "r10329:case:phi_002",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "phi_005",
          "case_ref": "r10329:case:phi_005",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "phi_010",
          "case_ref": "r10329:case:phi_010",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "phi_020",
          "case_ref": "r10329:case:phi_020",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "phi_020_seed1",
          "case_ref": "r10329:case:phi_020_seed1",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "phi_030",
          "case_ref": "r10329:case:phi_030",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "phi_040",
          "case_ref": "r10329:case:phi_040",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "re_004",
          "case_ref": "r10329:case:re_004",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        },
        {
          "case_id": "re_035",
          "case_ref": "r10329:case:re_035",
          "locator": {
            "source_field": "markdown",
            "line": 187,
            "quote": "| wall_momentum_balance | PASS | {'chk_radius4': 0.01035921904220731, 'control': 0.057454504077730895, 'phi_002': 0.0424596002350618, 'phi_005': 0.0652582022343936, 'phi_010': 0.09065410478147186, 'phi_020': 0.016422777096088744, 'phi_020_seed1': 0.005219882773372588, 'phi_030': 0.001001251478136939, 'phi_040': 0.004131278272974447, 're_004': 0.01626666803870348, 're_035': 0.016597240104817026} | 0.1 |"
          },
          "derivation": "key of the wall_momentum_balance dict literal (§6 acceptance table)",
          "resolution": {
            "status": "declared_only",
            "reason": "case id appears in the report; its per-case JSON is neither present in the delivery worktree nor named by path"
          }
        }
      ],
      "locators": [
        {
          "id": "r10329:source-markdown",
          "locator": {
            "source_field": "markdown",
            "line": 1
          },
          "quote_sha256": "sha256:47e174d38e536d4fc1565bf137de06c8b38ac2c3332859860a05a0c0b4a58f91",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:01",
          "locator": {
            "source_field": "markdown",
            "line": 6
          },
          "quote_sha256": "sha256:98f3cf6ff569fe6e8af0cc2dcf91af5b7136a87f4d905f34f9e015abde753071",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:02",
          "locator": {
            "source_field": "markdown",
            "line": 7
          },
          "quote_sha256": "sha256:e4e0d2455d7d36b68dc1eca713d607d75dd8a4fbb2b375543184ffe4a726ad93",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:03",
          "locator": {
            "source_field": "markdown",
            "line": 8
          },
          "quote_sha256": "sha256:0b2fa0ee957a320d3c3acbaeb0bf3dd7766369d86cc953e70c310c1556ed52d1",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:04",
          "locator": {
            "source_field": "markdown",
            "line": 9
          },
          "quote_sha256": "sha256:165a8e942b12fbeb38d234eca5dc39079ba0001c4cc2ad6b7bb972d8c7033354",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:05",
          "locator": {
            "source_field": "markdown",
            "line": 65
          },
          "quote_sha256": "sha256:33b5863c456109d601748c946c639e53118ef350eef2df25912b5c32f564bb04",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:06",
          "locator": {
            "source_field": "markdown",
            "line": 128
          },
          "quote_sha256": "sha256:c8748f9e55ab6db2c2b8778cfb32e19bd9bbde467b31289b0361e5a656fcb9d6",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:07",
          "locator": {
            "source_field": "markdown",
            "line": 133
          },
          "quote_sha256": "sha256:003bb53a00c40dac920a7fa9bc8f15d02c5d58a988864ee9bb3fe0c06944752e",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:08",
          "locator": {
            "source_field": "markdown",
            "line": 137
          },
          "quote_sha256": "sha256:98f6bf235982e4c7c9ef5b5047c8b52b457aadeef5aa14a6095408fb2ca49714",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:09",
          "locator": {
            "source_field": "markdown",
            "line": 141
          },
          "quote_sha256": "sha256:125cd33570c97de50b45d6a7d6152bb280b10856dc4fcfbe2ed9384181dd3f92",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:10",
          "locator": {
            "source_field": "markdown",
            "line": 145
          },
          "quote_sha256": "sha256:955a892e883b941425a99b248947ec3c56b103bb2cae214f8ce83f30d652f2e2",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:11",
          "locator": {
            "source_field": "markdown",
            "line": 176
          },
          "quote_sha256": "sha256:e7455cb844ee263db31453cfadb239b3dfd6d0ad7bbd7b6ec23fed9864ac7e40",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:12",
          "locator": {
            "source_field": "markdown",
            "line": 206
          },
          "quote_sha256": "sha256:c54fc70cd2e00b5371ae61bd42f635cbe894b30210cf6630f5e32a6d4fc20bd3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:13",
          "locator": {
            "source_field": "markdown",
            "line": 207
          },
          "quote_sha256": "sha256:55ac62bcad19551ac669022f1b689af54518abebb12eab68de1f338f6825b3d5",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:14",
          "locator": {
            "source_field": "markdown",
            "line": 208
          },
          "quote_sha256": "sha256:1d479fad5eb78d3116010cde88e8afaa625f3bbdd830aa1de6efa9c1ca7ecce1",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:15",
          "locator": {
            "source_field": "markdown",
            "line": 209
          },
          "quote_sha256": "sha256:d5b9b63d9e73d3facfffe6a8192cd2ef7410accbef62d06fc1f7a1f235b71479",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:ref:16",
          "locator": {
            "source_field": "markdown",
            "line": 210
          },
          "quote_sha256": "sha256:bc383eb7d85292472f8f2327144e9afdb2df345b936c115fcf0c8bebe0273c88",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:set:01",
          "locator": {
            "source_field": "markdown",
            "line": 8
          },
          "quote_sha256": "sha256:0b2fa0ee957a320d3c3acbaeb0bf3dd7766369d86cc953e70c310c1556ed52d1",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:sym:01",
          "locator": {
            "source_field": "markdown",
            "line": 4
          },
          "quote_sha256": "sha256:28873e236cd6b0de581c806dcee634d9b1d1a83143ffb52a77ff73894f0a3222",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:sym:02",
          "locator": {
            "source_field": "markdown",
            "line": 5
          },
          "quote_sha256": "sha256:3c51fcd0cec2f96c6adfa1e3cecc5237a57104baab4fadb888830017c7497149",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:sym:03",
          "locator": {
            "source_field": "markdown",
            "line": 17
          },
          "quote_sha256": "sha256:147b1b8f905cb259d20295e2966ccde7af025669c03f70167ea2a3f00bdc920f",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:sym:04",
          "locator": {
            "source_field": "markdown",
            "line": 112
          },
          "quote_sha256": "sha256:4a333bf9036370e52f943ed712df494586cd8df839a30bacd49a7d261d32e6f6",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:drag_re012",
          "locator": {
            "source_field": "markdown",
            "line": 94
          },
          "quote_sha256": "sha256:7e452f07560ae24a303ee05d16523f3bfc704781e5404d35b0714cf1337e7779",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:drag_re090",
          "locator": {
            "source_field": "markdown",
            "line": 95
          },
          "quote_sha256": "sha256:34ed9340f955b41b1d02b89be873f9179ec650fea8913dd45a2cbbd6c1eafce5",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:chk_radius4",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:control",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:phi_002",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:phi_005",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:phi_010",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:phi_020",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:phi_020_seed1",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:phi_030",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:phi_040",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:re_004",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        },
        {
          "id": "r10329:case:re_035",
          "locator": {
            "source_field": "markdown",
            "line": 187
          },
          "quote_sha256": "sha256:fec7afe172b1fdbf4bc56658c8041e2fe43811a8e56ab43a502c65606adca2c3",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1,
          "resolved": true
        }
      ],
      "identity_facts": [
        {
          "fact_id": "title-line",
          "locator": {
            "source_field": "markdown",
            "line": 1
          },
          "quote": "# IN13-W3-N03 — 碎冰/冰晶悬浮液有效粘度闭合的 LBM 标定",
          "quote_sha256": "sha256:47e174d38e536d4fc1565bf137de06c8b38ac2c3332859860a05a0c0b4a58f91",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "node-block",
          "locator": {
            "source_field": "markdown",
            "line": 3
          },
          "quote": "**节点**：IN13-W3-N03（物理域，全新前沿）·",
          "quote_sha256": "sha256:3c347e680d188b2dda12b84603aca364f857153e76a424a07aab75b73dd1d4c0",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "sec1-header",
          "locator": {
            "source_field": "markdown",
            "line": 13
          },
          "quote": "## 1. 案例介绍（物理背景 / 几何 / 参数）",
          "quote_sha256": "sha256:6ffb43d959d567f901e0ad2be6e031045ec40a34ac8df8477cc394a7586549dc",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "sec6-header",
          "locator": {
            "source_field": "markdown",
            "line": 166
          },
          "quote": "## 6. 误差判定（逐项，明确回答是否 <3%）",
          "quote_sha256": "sha256:0aaac8e4df79572e663c6de988821f12003860b42b9564d10186ca68aa97e5bd",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "repro-fence",
          "locator": {
            "source_field": "markdown",
            "line": 205
          },
          "quote": "```bash",
          "quote_sha256": "sha256:ad332335cfaa348c5bd715c3479844622270d5f7389ae070b81b135d521a221a",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "last-line",
          "locator": {
            "source_field": "markdown",
            "line": 211
          },
          "quote": "```",
          "quote_sha256": "sha256:f1b901847390b0ed7e374e7c1e464ec17b46a427c487a5ad6cbd2906405083d5",
          "quote_in_source": true,
          "quote_on_declared_line": true,
          "occurrences_in_source": 2
        }
      ],
      "claims": [],
      "claims_empty_reason": "Contract wp-10329-01 objective is register_assets=true / classify_report_type=false, and notes state 'claims 允许为空数组' with constraints no_forced_claim_generation=true and do_not_mark_claims_as_verified=true. This工序 registers asset identity only (report_id, markdown byte hash, declared attachments/artifacts/figures/cases); extraction is a downstream工序, so an empty claims array is the complete result, not an omission.",
      "counts": {
        "source_documents": 1,
        "figures_declared_in_record": 5,
        "figures_with_bytes": 5,
        "figures_with_sha256": 5,
        "body_references": 16,
        "distinct_referenced_paths": 11,
        "assets_total": 22,
        "assets_by_resolution": {
          "resolved": 11,
          "unresolved": 11
        },
        "declared_artifact_sets": 1,
        "symbol_references": 4,
        "measurement_cases": 13,
        "locators": 35,
        "locators_resolved": 35,
        "claims": 0,
        "kind_status_histogram": {
          "data_artifact_reference/unresolved": 3,
          "directory_reference/unresolved": 1,
          "embedded_figure/resolved": 5,
          "figure_reference/resolved": 5,
          "report_markdown/resolved": 1,
          "source_code_reference/unresolved": 7
        }
      },
      "id_integrity": {
        "ids_checked": 23,
        "duplicates": [],
        "unique": true
      },
      "unresolved": [
        {
          "asset_id": "r10329:ref:01",
          "name": "benchmarks/suspension_rheology_calib.py",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:02",
          "name": "tests/test_suspension_rheology.py",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:03",
          "name": "artifacts/suspension_rheology/calibration.json",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:04",
          "name": "figures/suspension_rheology/",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:05",
          "name": "calibration.json",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:11",
          "name": "calibration.json",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:12",
          "name": "benchmarks/suspension_rheology_calib.py",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:13",
          "name": "benchmarks/suspension_rheology_calib.py",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:14",
          "name": "benchmarks/suspension_rheology_calib.py",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:15",
          "name": "benchmarks/suspension_rheology_doc.py",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        },
        {
          "asset_id": "r10329:ref:16",
          "name": "tests/test_suspension_rheology.py",
          "reason": "path not present in delivery worktree TensorKnowledge (report declares it in the TensorLBM repository)"
        }
      ],
      "observations": [
        "Markdown is complete and self-consistent: first line is the H1 title, sections 1-8 present (211 lines); sections 5/6 carry the honest negative result and the FAIL verdicts verbatim.",
        "The 5 figures are declared in the record (name+caption) and linked in-body as relative paths figures/suspension_rheology/<name>.png; GET /tensor/reports/10329/figures/<name> serves PNG bytes for all of them, so each carries a local copy + sha256 (no figure claim is made about their content).",
        "All body path references point at TensorLBM artefacts (tensorlbm/*, benchmarks/*, tests/*, artifacts/suspension_rheology/*, figures/*) which are not present in the TensorKnowledge delivery worktree; they are registered as declared references with existence_asserted_by_worker=false."
      ],
      "limitations": [
        "Registration only: no claim/evidence extraction, no report-type classification, no verified marks (the platform gate computes verification).",
        "source_hash scope = UTF-8 bytes of the markdown string returned by the platform API; any change to the stored markdown (even whitespace) invalidates it.",
        "Direct psql read of tensor_reports was denied for this role, so the API is the only source channel used; both channels would be the same column, but this is still a single-channel read.",
        "Reference resolution is limited to the delivery worktree; a missing path is reported unresolved, never as a broken upstream artefact.",
        "Asset registration is not evidence of numerical validity; the report's own verdicts (4 FAIL / 4 PASS in §6) are recorded elsewhere and are not re-judged here."
      ]
    }
  },
  "claims": []
}
```
