# KF-RESULT wp-13278-01

**工作包**：`wp-13278-01` · **工序**：`01-asset-registration` · **source**：`tensor://reports/13278` (report_id=13278, field=markdown)
**分层**：TensorBEM | research | C · **mission**：m15757 · **交付仓**：TensorKnowledge（status=draft）
**source sha256**：`f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a16bb29406537cfac742dcc90f` ｜ **chars**：1592 ｜ **bytes(utf-8)**：2167 ｜ **平台 title**：TensorBEM bem_finite_depth 验证算例缺失图件补全
**provenance.verification_status**：`not_verified`（verification 由平台门计算，本单不做、不标）

## ① 本工序做了什么

只做一件事：**为 report_id=13278 登记源资产**。取平台 markdown → 本地重算 sha256 并与契约 `source_hash` 对齐 →
把报告里**可解析的**与**仅被引用的**资产逐条定位到字符区间，落成 `asset_manifest.json`（16 条资产）。
按契约 `objective.register_assets=true`、`objective.classify_report_type=false`、`notes` 明示 "claims 允许为空数组"，
本工序**不做抽取**（`claims=[]`），不改上游产物，不跨 report_id，不标 verified。

被测报告本身是 TensorBEM 仓的**工件补全单**（补 4 张 bem_finite_depth 验证图）。本工序对它只做资产账，不对其结论背书：
报告中「17 条测试全部通过」「4 张图已生成」均为上游自述，登记为 statement/execution_log，不升级为已验证事实。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET http://127.0.0.1:8010/api/v1/tensor/reports/13278`（Bearer token，脚本内登录），把 `markdown` 原样写盘
   （`runs/wp-13278-01/report_13278.md`），同时保存完整 payload 供元数据交叉核对。
2. **哈希门（先于一切分析）**：本地 `sha256(markdown)` = `f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a16bb29406537cfac742dcc90f`，与契约 `sha256:f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a16bb29406537cfac742dcc90f` 逐字符比对一致；
   `chars=1592` 与契约 `chars` 一致。两者任一不符脚本直接 FATAL 退出（不产出半成品）。
3. **资产锚定**：按语义单元建 16 条资产锚（文档/标题/元数据/EDIT_WHITELIST/各节/外部署名文件/图件声明/日志/局限），
   每条锚给**行区间**，脚本用行偏移表换算为 `char_span`，引文 = `markdown[start:end]` **逐字切片**，
   并要求 `markdown.count(quote)==1`（唯一性），否则拒绝写盘。→ 零手抄：引文不是敲进去的，是切出来的。
4. **可解析性分级**：`resolved_in_source`（本体即引文）/ `referenced_unresolved`（仅被引用、报告未携带本体）/
   `declared_absent`。对外部仓库的相对路径另做一次**只读存在性探测**（`/root/tp-agent/work/m13784/tests/test_bem_finite_depth_anchors.py` 所在树），
   探测结果只作旁证写进 `resolution_check.probe`，**不影响** resolution 判级（报告没给地址就是没给）。
5. **落盘 + 镜像**：产物写 `artifacts/wp-13278-01/asset_manifest.json`，并写**字节相同**的持久镜像 `docs/wp-13278-01/asset_manifest.json`
   （push 门会丢弃 `artifacts/**`、`runs/**`，提交面在 `docs/`）。脚本内 assert 两者 sha256 相同。
6. **独立复核**：`scripts/kf_verify_wp13278.py` 在**新进程**里重新登录、重新取 markdown、重新算哈希、重新切片，
   逐条回放 6 项 acceptance + 7 项附加检查；结果落 `artifacts/wp-13278-01/verification.json`（下第⑥段）。图件由 `matplotlib` 程序化生成。
7. **工具链**：Python 3 + `urllib`（HTTP）+ `hashlib`（哈希）+ `jsonschema`（Draft-07 manifest / Draft 2020-12 envelope）+ `matplotlib`。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-13278-01/asset_manifest.json` | 主产物：16 条资产，`by_resolution={"resolved_in_source": 11, "referenced_unresolved": 5}`，`coverage=98.43%`；sha256=`9a7a431129dc89f0a351c0157e07365d72d3f2a4fa64116115c3148aa9abfcbb` |
| `docs/wp-13278-01/asset_manifest.json` | 字节相同镜像（提交面） |
| `runs/wp-13278-01/kf_result.wp-13278-01.json` | 结果信封（`kf_result.v1`，仅 5 个允许字段，`additionalProperties=false` 下严格通过） |
| `docs/wp-13278-01/KF-RESULT-wp-13278-01.md` | 本报告（**唯一一个** ```json 代码块 = 结果信封） |
| `docs/wp-13278-01/fig_asset_coverage.png` | 图件：资产定位图 + class 普查（sha256=`c7f82756b69062ac…`） |
| `artifacts/wp-13278-01/verification.json` | 6 项 acceptance 逐项证据 |
| `runs/wp-13278-01/report_13278.md` | 取回源副本（≡source，用于离线复核） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

`chars` 为 `markdown[start:end]` 的字符区间（0 基），引文全部逐字切片自 `tensor://reports/13278`。

| asset_id | class | resolution | char span | lines | 原文引文（逐字切片） |
|---|---|---|---|---|---|
| A01 | document | resolved_in_source | 0-1592 | 0-52 | `（整篇 markdown）` |
| A02 | heading | resolved_in_source | 0-46 | 0-0 | `# TensorBEM 补全 bem_finite_depth 验证算例缺失的 4 张结果图` |
| A03 | metadata_block | resolved_in_source | 48-194 | 2-4 | `**任务**：m13784（selfstart·data 席） · **分支**：`agent/m137…` |
| A04 | edit_whitelist | resolved_in_source | 196-257 | 6-6 | `EDIT_WHITELIST: benchmarks/verified/bem_finite_depth…` |
| A05 | section | resolved_in_source | 264-530 | 10-15 | `## 1. 问题` |
| A06 | external_file_ref | referenced_unresolved | 274-362 | 12-12 | ``tests/test_bem_finite_depth_anchors.py::test_case_a…` |
| A07 | external_dir_ref | referenced_unresolved | 363-437 | 13-13 | ``benchmarks/verified/bem_finite_depth/figures/` 目录下至…` |
| A08 | ci_evidence_ref | referenced_unresolved | 438-530 | 14-15 | `导致测试在 clean main 上必败。该问题在 PR#306（m8788）和 PR#312（m879…` |
| A09 | external_code_ref | referenced_unresolved | 532-617 | 17-17 | ``src/tensorbem/benchmarks/bem_finite_depth_anchors.p…` |
| A10 | figure_declaration | resolved_in_source | 618-807 | 18-21 | `- `fig_energy_identities.png`：各工况的反射/透射能量守恒残差` |
| A11 | repro_command | resolved_in_source | 809-927 | 23-29 | `## 2. 修复` |
| A12 | execution_log | resolved_in_source | 929-1257 | 31-37 | `输出：` |
| A13 | figure_binary | referenced_unresolved | 937-1017 | 33-33 | `figure -> benchmarks/verified/bem_finite_depth/figur…` |
| A14 | test_evidence | resolved_in_source | 1259-1433 | 39-44 | `## 3. 验证` |
| A15 | statement | resolved_in_source | 1435-1504 | 46-46 | `全部 17 条测试通过（此前 `test_case_artifacts_and_documentatio…` |
| A16 | limitation_set | resolved_in_source | 1506-1591 | 48-51 | `## 4. 局限` |

**仅被引用、报告未携带本体**的资产（resolution=`referenced_unresolved`）：

| asset_id | 资产 | 不可解析原因 | 只读探测（Host） |
|---|---|---|---|
| A06 | 失败测试文件 tests/test_bem_finite_depth_anc | 报告只给出相对路径/编号，无 URL/DOI/commit/内容哈希；本工作树内不可解析 | `/root/tp-agent/work/m13784/tests/test_bem_finite_depth_anchors.py` → present |
| A07 | 被断言存在的图件目录 benchmarks/verified/bem_fin | 报告只给出相对路径/编号，无 URL/DOI/commit/内容哈希；本工作树内不可解析 | `/root/tp-agent/work/m13784/benchmarks/verified/bem_finite_depth/figures` → present |
| A08 | 历史 CI 记录 PR#306(m8788) / PR#312(m8799) | 报告只给出相对路径/编号，无 URL/DOI/commit/内容哈希；本工作树内不可解析 | 未探测 |
| A09 | 图件生成模块 src/tensorbem/benchmarks/bem_fi | 报告只给出相对路径/编号，无 URL/DOI/commit/内容哈希；本工作树内不可解析 | `/root/tp-agent/work/m13784/src/tensorbem/benchmarks/bem_finite_depth_anchors.py` → present |
| A13 | 4 个 PNG 图件本体（fig_energy_identities / f | 平台 figures 字段为空数组（0 条），报告未内嵌图件；仅有 A12 日志中的仓库相对路径 | `/root/tp-agent/work/m13784/benchmarks/verified/bem_finite_depth/figures` → present |

## ⑤ 注意点与局限

- **本单无「已验证」结论**：`claims=[]`（契约允许）；报告里的「17 passed」「4 张图已生成」只登记不背书。
  内容级 verification 由平台门计算，本单显式写 `verification_status=not_verified`。
- **图件本体不可核**：平台 `figures` 字段为空数组（0 条），
  4 个 PNG 只以**仓库相对路径**出现在执行日志里，无 sha256、无 URL —— 因此登记为 `referenced_unresolved`，
  不因「宿主某处存在同名文件」而升格（同名 ≠ 同字节，未做内容比对，也不敢做：那是 TensorBEM 仓的产物）。
- **历史 CI 证据不可解析**：PR#306/PR#312 只有编号，无 URL/run id/日志工件，下游若要复核必须回 TensorBEM 仓检索。
- **测试证据粒度粗**：报告只给汇总行（17 passed），无 junit/逐用例结果；「唯一失败项已修复」无法从报告内部证实。
- **标题双源**：markdown H1 与平台 `title` 字段措辞不同（H1 是长句，title 是受控短名）；本单两者都登记，不互相覆盖。
- **覆盖率 98.43% 而非 100%**：未覆盖的是空行与 `---` 分隔线（25 字符），无信息量。
- **不联网猜测**：所有「不可解析」结论基于报告文本 + 本机只读探测，未做任何外部检索。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结果 | 证据要点 |
|---|---|---|
| valid_json | PASS | {"parsed": true, "bytes": 21085} |
| schema_pass | PASS | {"manifest_errors": [], "envelope_errors": [], "manifest_schema": "schemas/asset_manifest.wp-13278-01.schema.json", "envelope_schema": "schemas/kf_res… |
| source_locator_resolvable | PASS | {"assets_checked": 16, "failures": [], "method": "re-fetched markdown, md[start:end]==quote, uniqueness for char_span"} |
| source_hash_matches | PASS | {"recomputed": "sha256:f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a16bb29406537cfac742dcc90f", "contract": "sha256:f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a1… |
| no_duplicate_ids | PASS | {"assets": 16, "duplicates": []} |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | {"claims": 0, "orphans": [], "vacuous": true, "note": "claims=[] is declared legitimate by the package contract (objective.classify_report_type=false)… |
| E1_envelope_contract_shape | PASS | {"problems": [], "verification_status": "not_verified"} |
| E2_report_block_single_json | PASS | {"json_blocks": 1, "doc": "docs/wp-13278-01/KF-RESULT-wp-13278-01.md", "parses": true} |
| E3_no_verified_markers | PASS | {"offenders": []} |
| E4_counts_consistent | PASS | {"counts.assets": 16, "len(assets)": 16, "by_resolution": {"resolved_in_source": 11, "referenced_unresolved": 5}} |
| E5_scope_single_report | PASS | {"report_id": "13278", "boundary": "report_id=13278 only"} |
| E6_durable_mirror_identical | PASS | {"mirror": "docs/wp-13278-01/asset_manifest.json"} |
| E7_source_chars_match_contract | PASS | {"chars": 1592, "contract": 1592} |

**六项 acceptance**：`valid_json` ✅ ｜ `schema_pass` ✅ ｜ `source_locator_resolvable` ✅ ｜ `source_hash_matches` ✅ ｜
`no_duplicate_ids` ✅ ｜ `all_claims_have_evidence_or_explicit_unresolved_status` ✅（`claims=0`，契约允许的空数组，vacuous-pass 已在 verification 中显式标注）。
**总判**：`PASS`（本单自检，非平台终判）。

### 一键复跑

```bash
cd <worktree>  # 本工作树根
python3 scripts/kf_register_wp13278.py    # 取源→哈希门→定位→写 manifest/镜像/信封
python3 scripts/kf_verify_wp13278.py      # 独立复核：重新取源+重算哈希+重放 6 项 acceptance
python3 scripts/kf_report_wp13278.py      # 渲染图件+生成本报告（--no-post 可只生成不发）
python3 -m pytest tests/test_kf_wp13278.py -q
```

## 结果信封（唯一 ```json 块）

```json
{
  "package_id": "wp-13278-01",
  "task_type": "01-asset-registration",
  "report_id": "13278",
  "provenance": {
    "source_uri": "tensor://reports/13278",
    "source_field": "markdown",
    "source_hash": "sha256:f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a16bb29406537cfac742dcc90f",
    "source_chars": 1592,
    "source_bytes_utf8": 2167,
    "source_title": "TensorBEM bem_finite_depth 验证算例缺失图件补全",
    "scenario_key": "bem_finite_depth_verification",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-13278-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/13278",
    "local_copy": "runs/wp-13278-01/report_13278.md",
    "generator": "scripts/kf_register_wp13278.py",
    "verifier": "scripts/kf_verify_wp13278.py",
    "artifact_path": "artifacts/wp-13278-01/asset_manifest.json",
    "artifact_sha256": "9a7a431129dc89f0a351c0157e07365d72d3f2a4fa64116115c3148aa9abfcbb",
    "artifact_bytes": 21085,
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-13278-01",
      "task_type": "01-asset-registration",
      "report_id": "13278",
      "source": {
        "uri": "tensor://reports/13278",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "f9c336f0d77c618b2a03ff4dd4fbc7d04b0d78a16bb29406537cfac742dcc90f",
        "chars": 1592,
        "bytes_utf8": 2167,
        "title": "TensorBEM bem_finite_depth 验证算例缺失图件补全",
        "scenario_key": "bem_finite_depth_verification",
        "platform_id": 13278,
        "platform_mission_id": 13784,
        "platform_status": "published",
        "platform_figures": [],
        "platform_tags": [
          "TensorBEM",
          "verification",
          "artifact",
          "bem_finite_depth"
        ],
        "contract_title": "TensorBEM bem_finite_depth 验证算例缺失图件补全",
        "contract_chars": 1592,
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/13278",
        "local_copy": "runs/wp-13278-01/report_13278.md"
      },
      "counts": {
        "assets": 16,
        "by_class": {
          "document": 1,
          "heading": 1,
          "metadata_block": 1,
          "edit_whitelist": 1,
          "section": 1,
          "external_file_ref": 1,
          "external_dir_ref": 1,
          "ci_evidence_ref": 1,
          "external_code_ref": 1,
          "figure_declaration": 1,
          "repro_command": 1,
          "execution_log": 1,
          "figure_binary": 1,
          "test_evidence": 1,
          "statement": 1,
          "limitation_set": 1
        },
        "by_resolution": {
          "resolved_in_source": 11,
          "referenced_unresolved": 5
        },
        "resolved_in_source": 11,
        "referenced_unresolved": 5,
        "declared_absent": 0
      },
      "coverage": {
        "covered_chars": 1567,
        "source_chars": 1592,
        "pct": 98.43,
        "method": "union of char_span locators (document locator excluded)"
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告正文（markdown 全文，1592 字符）",
          "in_report_section": "# TensorBEM 补全 bem_finite_depth 验证算例缺失的 4 张结果图",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 1592,
            "start_line": 0,
            "end_line": 52,
            "quote": "# TensorBEM 补全 bem_finite_depth 验证算例缺失的 4 张结果图\n\n**任务**：m13784（selfstart·data 席） · **分支**：`agent/m13784` · **日期**：2026-11-11\n**仓**：TensorBEM\n**归仓理由**：求解器仓的验证算例工件补全（ECOSYSTEM-MAP：求解器→对应 Tensor* 库）\n\nEDIT_WHITELIST: benchmarks/verified/bem_finite_depth/figures/\n\n---\n\n## 1. 问题\n\n`tests/test_bem_finite_depth_anchors.py::test_case_artifacts_and_documentation_exist` 断言\n`benchmarks/verified/bem_finite_depth/figures/` 目录下至少有 4 张 PNG 图，但该目录从未入库，\n导致测试在 clean main 上必败。该问题在 PR#306（m8788）和 PR#312（m8799）的 CI 日志中均被记录为\n\"与本 PR 无关的既有失败\"，但一直未被修复。\n\n`src/tensorbem/benchmarks/bem_finite_depth_anchors.py` 的 `make_figures()` 函数可生成 4 张图：\n- `fig_energy_identities.png`：各工况的反射/透射能量守恒残差\n- `fig_kramers_kronig.png`：Ursell 解析阻尼与面板扫描的 KK 因果性对比\n- `fig_deep_water_limit.png`：有限深→无限深渐近收敛\n- `fig_section_matrix.png`：截面×深度×频率矩阵的附加质量/阻尼热力图\n\n## 2. 修复\n\n运行基准程序生成图：\n\n```bash\nPYTHONPATH=src python -m tensorbem.benchmarks.bem_finite_depth_anchors --stage merge\n```\n\n输出：\n```\nfigure -> benchmarks/verified/bem_finite_depth/figures/fig_energy_identities.png\nfigure -> benchmarks/verified/bem_finite_depth/figures/fig_kramers_kronig.png\nfigure -> benchmarks/verified/bem_finite_depth/figures/fig_deep_water_limit.png\nfigure -> benchmarks/verified/bem_finite_depth/figures/fig_section_matrix.png\n```\n\n## 3. 验证\n\n```\n$ PYTHONPATH=src python -m pytest tests/test_bem_finite_depth_anchors.py -v\n======================== 17 passed, 1 warning in 3.98s =========================\n```\n\n全部 17 条测试通过（此前 `test_case_artifacts_and_documentation_exist` 为唯一失败项）。\n\n## 4. 局限\n\n- 本单仅补全缺失工件，未修改任何求解器代码或测试逻辑。\n- 图的生成依赖 `result.json` 中的已有数据；若未来基准参数变更，需重新生成。\n",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 1592,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "整篇 markdown 即源资产本体；sha256 由 provenance/contract 双端复核一致"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题（markdown H1）",
          "in_report_section": "# TensorBEM 补全 bem_finite_depth 验证算例缺失的 4 张结果图",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 46,
            "start_line": 0,
            "end_line": 0,
            "quote": "# TensorBEM 补全 bem_finite_depth 验证算例缺失的 4 张结果图",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 46,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "H1 与平台 title 字段措辞不同（title 为受控短名），此处二者都登记但不互相覆盖"
        },
        {
          "asset_id": "A03",
          "asset_class": "metadata_block",
          "label": "任务/分支/日期/仓/归仓理由 声明",
          "in_report_section": "# TensorBEM 补全 bem_finite_depth 验证算例缺失的 4 张结果图",
          "locator": {
            "method": "char_span",
            "start_char": 48,
            "end_char": 194,
            "start_line": 2,
            "end_line": 4,
            "quote": "**任务**：m13784（selfstart·data 席） · **分支**：`agent/m13784` · **日期**：2026-11-11\n**仓**：TensorBEM\n**归仓理由**：求解器仓的验证算例工件补全（ECOSYSTEM-MAP：求解器→对应 Tensor* 库）",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 146,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "上游任务号 m13784、分支 agent/m13784、仓 TensorBEM 的唯一来源"
        },
        {
          "asset_id": "A04",
          "asset_class": "edit_whitelist",
          "label": "EDIT_WHITELIST 声明（仅 figures/ 目录）",
          "in_report_section": "# TensorBEM 补全 bem_finite_depth 验证算例缺失的 4 张结果图",
          "locator": {
            "method": "char_span",
            "start_char": 196,
            "end_char": 257,
            "start_line": 6,
            "end_line": 6,
            "quote": "EDIT_WHITELIST: benchmarks/verified/bem_finite_depth/figures/",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 61,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "写入边界的自证：本单只允许改该目录，与「未修改求解器代码」的自述互相印证"
        },
        {
          "asset_id": "A05",
          "asset_class": "section",
          "label": "§1 问题陈述",
          "in_report_section": "## 1. 问题",
          "locator": {
            "method": "char_span",
            "start_char": 264,
            "end_char": 530,
            "start_line": 10,
            "end_line": 15,
            "quote": "## 1. 问题\n\n`tests/test_bem_finite_depth_anchors.py::test_case_artifacts_and_documentation_exist` 断言\n`benchmarks/verified/bem_finite_depth/figures/` 目录下至少有 4 张 PNG 图，但该目录从未入库，\n导致测试在 clean main 上必败。该问题在 PR#306（m8788）和 PR#312（m8799）的 CI 日志中均被记录为\n\"与本 PR 无关的既有失败\"，但一直未被修复。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 266,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "失败断言+目录缺失+历史 CI 记录的整段上下文"
        },
        {
          "asset_id": "A06",
          "asset_class": "external_file_ref",
          "label": "失败测试文件 tests/test_bem_finite_depth_anchors.py::test_case_artifacts_and_documentation_exist",
          "in_report_section": "## 1. 问题",
          "locator": {
            "method": "char_span",
            "start_char": 274,
            "end_char": 362,
            "start_line": 12,
            "end_line": 12,
            "quote": "`tests/test_bem_finite_depth_anchors.py::test_case_artifacts_and_documentation_exist` 断言",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_body_not_carried_by_report",
            "result": "unresolved",
            "detail": "报告只给出相对路径/编号，无 URL/DOI/commit/内容哈希；本工作树内不可解析",
            "probe": {
              "exists_on_host": true,
              "probe_path": "/root/tp-agent/work/m13784/tests/test_bem_finite_depth_anchors.py",
              "note": "只读存在性探测（不联网、不改外部树）；命中不代表报告已给出可解析地址"
            }
          },
          "note": "报告只给仓库相对路径，无 URL/commit 锚；本工作树（TensorKnowledge）内不存在该文件"
        },
        {
          "asset_id": "A07",
          "asset_class": "external_dir_ref",
          "label": "被断言存在的图件目录 benchmarks/verified/bem_finite_depth/figures/（≥4 张 PNG）",
          "in_report_section": "## 1. 问题",
          "locator": {
            "method": "char_span",
            "start_char": 363,
            "end_char": 437,
            "start_line": 13,
            "end_line": 13,
            "quote": "`benchmarks/verified/bem_finite_depth/figures/` 目录下至少有 4 张 PNG 图，但该目录从未入库，",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_body_not_carried_by_report",
            "result": "unresolved",
            "detail": "报告只给出相对路径/编号，无 URL/DOI/commit/内容哈希；本工作树内不可解析",
            "probe": {
              "exists_on_host": true,
              "probe_path": "/root/tp-agent/work/m13784/benchmarks/verified/bem_finite_depth/figures",
              "note": "只读存在性探测（不联网、不改外部树）；命中不代表报告已给出可解析地址"
            }
          },
          "note": "目录本体不在报告内；「≥4 张」为断言阈值，不是实测计数"
        },
        {
          "asset_id": "A08",
          "asset_class": "ci_evidence_ref",
          "label": "历史 CI 记录 PR#306(m8788) / PR#312(m8799)",
          "in_report_section": "## 1. 问题",
          "locator": {
            "method": "char_span",
            "start_char": 438,
            "end_char": 530,
            "start_line": 14,
            "end_line": 15,
            "quote": "导致测试在 clean main 上必败。该问题在 PR#306（m8788）和 PR#312（m8799）的 CI 日志中均被记录为\n\"与本 PR 无关的既有失败\"，但一直未被修复。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_body_not_carried_by_report",
            "result": "unresolved",
            "detail": "报告只给出相对路径/编号，无 URL/DOI/commit/内容哈希；本工作树内不可解析"
          },
          "note": "无 PR URL / run id / 日志工件地址，报告侧不可解析；只能作为下游复核的检索线索"
        },
        {
          "asset_id": "A09",
          "asset_class": "external_code_ref",
          "label": "图件生成模块 src/tensorbem/benchmarks/bem_finite_depth_anchors.py 的 make_figures()",
          "in_report_section": "## 1. 问题",
          "locator": {
            "method": "char_span",
            "start_char": 532,
            "end_char": 617,
            "start_line": 17,
            "end_line": 17,
            "quote": "`src/tensorbem/benchmarks/bem_finite_depth_anchors.py` 的 `make_figures()` 函数可生成 4 张图：",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_body_not_carried_by_report",
            "result": "unresolved",
            "detail": "报告只给出相对路径/编号，无 URL/DOI/commit/内容哈希；本工作树内不可解析",
            "probe": {
              "exists_on_host": true,
              "probe_path": "/root/tp-agent/work/m13784/src/tensorbem/benchmarks/bem_finite_depth_anchors.py",
              "note": "只读存在性探测（不联网、不改外部树）；命中不代表报告已给出可解析地址"
            }
          },
          "note": "生成逻辑本体不在报告内；报告只声明存在该函数与其产物"
        },
        {
          "asset_id": "A10",
          "asset_class": "figure_declaration",
          "label": "4 张图件的名称-内容声明",
          "in_report_section": "## 1. 问题",
          "locator": {
            "method": "char_span",
            "start_char": 618,
            "end_char": 807,
            "start_line": 18,
            "end_line": 21,
            "quote": "- `fig_energy_identities.png`：各工况的反射/透射能量守恒残差\n- `fig_kramers_kronig.png`：Ursell 解析阻尼与面板扫描的 KK 因果性对比\n- `fig_deep_water_limit.png`：有限深→无限深渐近收敛\n- `fig_section_matrix.png`：截面×深度×频率矩阵的附加质量/阻尼热力图",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 189,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "四条声明的原文；图件二进制本体登记为 A13（未解析）"
        },
        {
          "asset_id": "A11",
          "asset_class": "repro_command",
          "label": "复跑命令（§2 bash 块）",
          "in_report_section": "## 2. 修复",
          "locator": {
            "method": "char_span",
            "start_char": 809,
            "end_char": 927,
            "start_line": 23,
            "end_line": 29,
            "quote": "## 2. 修复\n\n运行基准程序生成图：\n\n```bash\nPYTHONPATH=src python -m tensorbem.benchmarks.bem_finite_depth_anchors --stage merge\n```",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 118,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "含 `--stage merge` 关键参数；命令未在本工序执行（属 TensorBEM 仓，越界）"
        },
        {
          "asset_id": "A12",
          "asset_class": "execution_log",
          "label": "生成输出日志（4 行 figure -> 路径）",
          "in_report_section": "## 2. 修复",
          "locator": {
            "method": "char_span",
            "start_char": 929,
            "end_char": 1257,
            "start_line": 31,
            "end_line": 37,
            "quote": "输出：\n```\nfigure -> benchmarks/verified/bem_finite_depth/figures/fig_energy_identities.png\nfigure -> benchmarks/verified/bem_finite_depth/figures/fig_kramers_kronig.png\nfigure -> benchmarks/verified/bem_finite_depth/figures/fig_deep_water_limit.png\nfigure -> benchmarks/verified/bem_finite_depth/figures/fig_section_matrix.png\n```",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 328,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "上游粘贴的控制台输出；本工序仅登记不复跑，不视作已复现证据"
        },
        {
          "asset_id": "A13",
          "asset_class": "figure_binary",
          "label": "4 个 PNG 图件本体（fig_energy_identities / fig_kramers_kronig / fig_deep_water_limit / fig_section_matrix）",
          "in_report_section": "## 2. 修复",
          "locator": {
            "method": "char_span",
            "start_char": 937,
            "end_char": 1017,
            "start_line": 33,
            "end_line": 33,
            "quote": "figure -> benchmarks/verified/bem_finite_depth/figures/fig_energy_identities.png",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "external_body_not_carried_by_report",
            "result": "unresolved",
            "detail": "平台 figures 字段为空数组（0 条），报告未内嵌图件；仅有 A12 日志中的仓库相对路径",
            "probe": {
              "exists_on_host": true,
              "probe_path": "/root/tp-agent/work/m13784/benchmarks/verified/bem_finite_depth/figures",
              "note": "只读存在性探测（不联网、不改外部树）；命中不代表报告已给出可解析地址"
            },
            "platform_figures_count": 0
          },
          "note": "报告未内嵌任何图件（平台 figures 字段为空数组），也未给 sha256；仅 A12 日志给出相对路径。同目录另 3 条路径见 A12 第 34-36 行"
        },
        {
          "asset_id": "A14",
          "asset_class": "test_evidence",
          "label": "§3 验证块（pytest 命令 + 17 passed 汇总行）",
          "in_report_section": "## 3. 验证",
          "locator": {
            "method": "char_span",
            "start_char": 1259,
            "end_char": 1433,
            "start_line": 39,
            "end_line": 44,
            "quote": "## 3. 验证\n\n```\n$ PYTHONPATH=src python -m pytest tests/test_bem_finite_depth_anchors.py -v\n======================== 17 passed, 1 warning in 3.98s =========================\n```",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 174,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "上游粘贴的测试摘要；无 junit/日志工件，逐条用例结果不可核 —— 只登记不回填"
        },
        {
          "asset_id": "A15",
          "asset_class": "statement",
          "label": "全通过断言（17 条，唯一历史失败项已修复）",
          "in_report_section": "## 3. 验证",
          "locator": {
            "method": "char_span",
            "start_char": 1435,
            "end_char": 1504,
            "start_line": 46,
            "end_line": 46,
            "quote": "全部 17 条测试通过（此前 `test_case_artifacts_and_documentation_exist` 为唯一失败项）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 69,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "属上游自述结论，登记为陈述而非已验证事实（verification 由平台门计算）"
        },
        {
          "asset_id": "A16",
          "asset_class": "limitation_set",
          "label": "§4 局限（2 条）",
          "in_report_section": "## 4. 局限",
          "locator": {
            "method": "char_span",
            "start_char": 1506,
            "end_char": 1591,
            "start_line": 48,
            "end_line": 51,
            "quote": "## 4. 局限\n\n- 本单仅补全缺失工件，未修改任何求解器代码或测试逻辑。\n- 图的生成依赖 `result.json` 中的已有数据；若未来基准参数变更，需重新生成。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved",
            "quote_len": 85,
            "detail": "引文为源 markdown 的逐字切片，且 md.count(quote)==1"
          },
          "note": "含「仅补工件、未改求解器/测试」与「依赖 result.json 已有数据」两条边界"
        }
      ],
      "claims": [],
      "claims_note": "契约 objective.classify_report_type=false 且 notes 明确 claims 允许为空数组：本工序只登记资产定位，不做抽取；claim 抽取属下游工作包。",
      "integrity": {
        "quote_uniqueness": "all 15 char_span quotes verified unique substrings of the fetched markdown",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "chars_matches_contract": true
      }
    }
  }
}
```
