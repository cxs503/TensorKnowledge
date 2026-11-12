> **发布说明（路径更正版，supersedes report #14669）**：同一工作包的结果重发布。与 #14669 相比，`json` 信封内容**完全相同**（同一 report 7808、同一 sha256），唯一差异是本版产物路径由 `artifacts/wp-7808-01/` 改为 `docs/kf/wp-7808-01/`——`artifacts/` 被 `.gitignore` 忽略并被推送门禁过滤（`docs/ops/filter-audit.md`），留在那里会在推出的仓库里变成悬空引用。#14669 因此作废，以本报告为准。

## ① 本工序做了什么

本单执行 `01-asset-registration`（Lane C，package_id=`wp-7808-01`），只对 **report_id=7808** 一份报告做**源资产登记**，不做抽取、不做报告类型分类、不写任何 verified 标记：

1. 取回 report 7808 的 `markdown` 字段（source_uri=`tensor://reports/7808`），独立重算 UTF-8 字节 sha256；
2. 与工作包契约 `input.source_hash` / `input.chars` 逐项比对；
3. 列出报告正文中可解析的附件/工件（代码路径、G21 孤儿模块表行、内嵌 pytest 日志块、图集），每个资产给一条**逐字可定位**引文（char 区间 + 行号 + 引文 sha256）；
4. 对每个引用如实给出 `resolved_in_source` / `referenced_unresolved` / `declared_absent` 三态之一，解析能力边界仅限 TensorKnowledge 交付工作树与平台附件端点；
5. 产出 `asset_manifest.json`，包进 `kf_result.v1` 信封。

`claims` 允许为空数组（契约 notes），本包按 `no_forced_claim_generation=true` 不做强造，**claims = []** 是完整结果而非缺项。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 工具 | 关键设置 |
|---|---|---|
| 取源 | `GET $TENSOR_API_BASE/tensor/reports/7808`（Bearer 登录令牌） | 只取 `markdown` 字段原文，不做任何规范化/换行改写 |
| 哈希 | `hashlib.sha256(md.encode('utf-8'))` | 作用域=存储串的 UTF-8 字节；字符数同时比对契约 3389 |
| 定位 | 自写 `locate()`：`str.find` + 出现次数 | 记录 `start_char/end_char`（左闭右开）、`start_line/end_line`（1 基）、`occurrences_in_source`、`char_span_roundtrip_ok` |
| 资产枚举 | 正则 `[A-Za-z0-9_./-]+\.(?:py|png|csv|json|md|txt|h5|dat|pdf|log|ipynb)` + §7 表格行 | 正文所有文件类 token 全覆盖，未覆盖即 fail |
| 解析判定 | `os.path.exists` 探交付工作树候选路径 + `GET reports/7808/{figures,artifacts}` | figures/artifacts 端点均返回 HTTP 404，记录 record.figures=[] |
| 结果封装 | `jsonschema` 4.x | 信封 `schemas/kf_result.v1.schema.json` + 本包 manifest schema 双校验 |
| 复现 | pytest 11 项离线测试 | 读 `docs/kf/wp-7808-01/source_markdown.md`（与契约同哈希的字节副本），无需联网 |

一键复跑（工作树根目录，凭据取自环境变量）：

```
python3 scripts/kf_register_7808.py --validate && python3 -m pytest tests/test_kf_register_7808.py -q && python3 scripts/plot_wp7808_assets.py && python3 scripts/emit_wp7808_report.py
```

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7808-01/asset_manifest.json` | 契约输出。11 个资产：resolved_in_source=2、referenced_unresolved=8、declared_absent=1；claims=0；含 source 身份块（hash/chars/bytes/lines/record 字段/平台端点探针）、逐资产 locator、coverage、id_integrity、integrity、unresolved、observations、limitations |
| `docs/kf/wp-7808-01/kf_result.json` | `kf_result.v1` 信封（package_id/task_type/report_id/provenance/outputs/claims），provenance.source_hash = `sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e` |
| `docs/kf/wp-7808-01/report_selfcheck.json` | acceptance 逐项机器自检结果（8/8 pass，all_pass=True） |
| `docs/kf/wp-7808-01/work_package_contract.json` | 本包 YAML 契约的 JSON 转写（字段名/值不变），供生成器无 YAML 依赖地读取阈值 |
| `docs/kf/wp-7808-01/asset_manifest.schema.json` | 本包 manifest 形状的本地 schema（**未改动**共享的 `schemas/asset_manifest.v1.schema.json`，后者被 const 钉死在 wp-448-01 上，属别的工作包） |
| `scripts/kf_register_7808.py` | 生成+自检脚本（fetch / hash / locator / resolution / coverage / 双 schema 校验） |
| `scripts/plot_wp7808_assets.py` | 资产盘点图生成脚本（数据全部来自 manifest，无手抄数字） |
| `scripts/emit_wp7808_report.py` | 本报告生成脚本：证据表由 locator 程序化注入，信封按字节原样嵌入 json 块 |
| `tests/test_kf_register_7808.py` | 11 项离线验收测试（哈希、locator 逐字可解、ID 唯一、claims 空且未标 verified、token 覆盖、计数自洽、报告范围仅 7808、unresolved 必须带原因） |
| `docs/kf/wp-7808-01/source_markdown.md` | 报告 markdown 的**字节精确副本**（sha256=`sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e`），仅为离线复跑测试留存，非抽取非手抄 |
| `docs/kf/wp-7808-01/source_markdown.provenance.json` | 上述副本的来源与哈希声明 |
| `docs/kf/wp-7808-01/figures/asset_inventory.png` | 图：资产盘点（类别×解析状态）与完整性计数 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

源身份：`report_id=7808`，`chars=3389`（契约 3389），`bytes=5210`，`lines=160`，`sha256=sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e`，与契约一致=True。记录字段：title=「DDES/SAS 混合湍流模块单元测试验证（G21 缺口填补）」，scenario_key=ddes_unit_verification，mission_id=6583，status=published，figures=[]。

| asset / claim | 字段 | 原文引文（逐字） | 定位 (char, line) | resolution |
|---|---|---|---|---|
| A01 tensor://reports/7808 markdown (H1 title line as document anchor) | markdown | 「# DDES/SAS 混合湍流模块验证报告（G21 缺口填补）」 | [0,31) L1 | resolved_in_source |
| A02 src/tensorlbm/ddes.py | markdown | 「`src/tensorlbm/ddes.py`（370 行，G21 孤儿模块）」 | [135,174) L6 | referenced_unresolved |
| A03 tests/test_ddes_unit.py | markdown | 「`tests/test_ddes_unit.py`（22 项，全部通过）」 | [185,221) L7 | referenced_unresolved |
| A04 ddes.py (G21 orphan module table row) | markdown | 「\| ddes.py \|」 | [3057,3068) L150 | referenced_unresolved |
| A05 des_turbulence.py (G21 orphan module table row) | markdown | 「\| des_turbulence.py \|」 | [3092,3113) L151 | referenced_unresolved |
| A06 rans_wall_bc.py (G21 orphan module table row) | markdown | 「\| rans_wall_bc.py \|」 | [3158,3177) L152 | referenced_unresolved |
| A07 d3q27_collide.py (G21 orphan module table row) | markdown | 「\| d3q27_collide.py \|」 | [3196,3216) L153 | referenced_unresolved |
| A08 hybrid_solver.py (G21 orphan module table row) | markdown | 「\| hybrid_solver.py \|」 | [3236,3256) L154 | referenced_unresolved |
| A09 prism_solver.py (G21 orphan module table row) | markdown | 「\| prism_solver.py \|」 | [3273,3292) L155 | referenced_unresolved |
| A10 figures of report 7808 (empty set) | markdown | 「本任务为纯单元测试验证，无数值模拟场量，故无云图/曲线生成。」 | [2259,2289) L103 | declared_absent |
| A11 pytest run summary block (22 passed, 1 warning in 6.30s) | markdown | 「22 passed, 1 warning in 6.30s」 | [1772,1801) L81 | resolved_in_source |
| （无 claim） | — | 本包不产 claim，claims=[] 为合法完整结果 | — | — |

未解析引用（如实登记，不当作上游缺失）：

| asset | 路径/对象 | 未解析原因 |
|---|---|---|
| A02 | src/tensorlbm/ddes.py | path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header |
| A03 | tests/test_ddes_unit.py | path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header |
| A04 | ddes.py (G21 orphan module table row) | path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header |
| A05 | des_turbulence.py (G21 orphan module table row) | path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header |
| A06 | rans_wall_bc.py (G21 orphan module table row) | path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header |
| A07 | d3q27_collide.py (G21 orphan module table row) | path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header |
| A08 | hybrid_solver.py (G21 orphan module table row) | path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header |
| A09 | prism_solver.py (G21 orphan module table row) | path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header |

## ⑤ 注意点与局限

1. **只登记不抽取**：契约 `objective.classify_report_type=false`，本包不产任何知识 claim，也不对报告结论（"22 项全部通过""数学实现正确"）表态；这些仍是**上游断言**，验证由平台门计算，本包不标 verified。
2. **哈希作用域**：sha256 覆盖存储串的 UTF-8 字节，任何改动（哪怕一个空格）都会使哈希失效；契约的 `chars=3389` 与实测字符数一致，但字节约为 5210（中文多字节），两者不是同一量。
3. **解析边界**：本包只在 TensorKnowledge 交付工作树内探测路径。`ddes.py`、`tests/test_ddes_unit.py`、G21 表里另 5 个模块都属报告头声明的 TensorLBM 仓，本工作树没有 → 一律登记 `referenced_unresolved` + 原因，**不得**解读为上游文件缺失。
4. **二次通道受限**：想用 `psql -d tensorplatform -c "select markdown from tensor_reports where id=7808"` 做独立复核，返回 `permission denied for table tensor_reports`；因此本包只走平台 API 一条信道，另以两次独立 GET + 本地字节副本互为印证（三者哈希相同）。
5. **图**：本报告含 1 张图，但**不是物理场量图**——本工序是登记工序，没有数值结果。图为 manifest 计数的可视化（类别×解析状态 + 完整性计数），标注写明数据来源，不能当作物理验证证据。
6. **报告自述数字未复算**：`ddes.py` 370 行、`22 passed, 1 warning in 6.30s` 均为报告内自述（后者作为 `embedded_run_log` 资产登记），本包未重跑 TensorLBM 测试，故不复核。
7. **产物落点与推送门禁**：`artifacts/` 被 `.gitignore` 忽略且被推送门禁过滤（见 `docs/ops/filter-audit.md`），因此全部产物落在 `docs/kf/wp-7808-01/`（含 `figures/`）；源 markdown 的字节副本也放这里，否则离线验收测试在推出仓库后必然找不到夹具。这是**字节副本**（哈希钉死），不是抽取、不是手抄。
8. **边界纪律**：本包只读/只写 report_id=7808；未触碰任何其它 report_id（本单自身发布报告的 id 由平台分配，不参与本包登记）。

## ⑥ 自检：逐条对照 acceptance

| acceptance item | 结果 | 验证方式/证据 |
|---|---|---|
| valid_json | ✅ pass | both kf_result.json and asset_manifest.json re-parsed by json.load |
| schema_pass | ✅ pass | kf_result.v1 envelope: pass; asset_manifest schema: pass |
| source_locator_resolvable | ✅ pass | 11 locators re-resolved against re-fetched markdown; failures=[] |
| source_byte_copy_identical | ✅ pass | docs/kf/wp-7808-01/source_markdown.md vs freshly fetched markdown: identical=True |
| source_hash_matches | ✅ pass | recomputed=sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e contract=sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e provenance=sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e |
| asset_list_covers_body_path_tokens | ✅ pass | 9 distinct file-like tokens, unmapped=[] |
| no_duplicate_ids | ✅ pass | 11 ids, 11 distinct |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ pass | claims == [] (contract notes: 允许为空数组; no_forced_claim_generation=true) -> vacuously satisfied, and no claim is marked verified |

失败项：无（若上表出现 ❌ 即为 honest-FAIL，本行同步改写，不粉饰）。复跑自检：`python3 scripts/kf_register_7808.py --validate`（非 0 退出码即失败）；离线验收：`python3 -m pytest tests/test_kf_register_7808.py -q`。

## 交付信封（唯一 json 块，原样提交）

```json
{
  "package_id": "wp-7808-01",
  "task_type": "01-asset-registration",
  "report_id": "7808",
  "provenance": {
    "source_hash": "sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e",
    "source_field": "markdown",
    "producer": "kf-worker/m15601",
    "emitted_at": "2026-11-12T01:30:28.636519+00:00",
    "notes": "hash recomputed from the markdown string of report 7808 (GET http://127.0.0.1:8010/api/v1/tensor/reports/7808); matches contract source_hash sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e: True"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-7808-01",
      "task_type": "01-asset-registration",
      "report_id": "7808",
      "lane": "C",
      "generated_at": "2026-11-12T01:30:28.634027+00:00",
      "producer": "kf-worker/m15601",
      "source": {
        "report_id": "7808",
        "source_uri": "tensor://reports/7808",
        "source_field": "markdown",
        "source_hash": "sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e",
        "contract_source_hash": "sha256:ffc30cee99ff03d89aff6a284c91acc4fa94497cbcf63c03cb10b3ecc0f4df7e",
        "hash_alg": "sha256",
        "hash_scope": "utf-8 bytes of record.markdown (exact stored string, no normalisation)",
        "hash_match": true,
        "chars": 3389,
        "contract_chars": 3389,
        "chars_match_contract": true,
        "bytes_utf8": 5210,
        "lines": 160,
        "line_counting": "logical lines = markdown.rstrip(chr(10)).split(chr(10)); 1-based",
        "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/7808",
        "record_fields": {
          "title": "DDES/SAS 混合湍流模块单元测试验证（G21 缺口填补）",
          "contract_title": "DDES/SAS 混合湍流模块单元测试验证（G21 缺口填补）",
          "title_matches_contract": true,
          "scenario_key": "ddes_unit_verification",
          "contract_scenario_key": "ddes_unit_verification",
          "scenario_matches_contract": true,
          "mission_id": 6583,
          "status": "published",
          "stage": null,
          "created_at": "2026-11-08T06:21:17.124925+00:00",
          "tags": [
            "G21",
            "DDES",
            "unit_test",
            "verification",
            "TensorLBM"
          ],
          "figures": []
        },
        "platform_attachment_probes": {
          "GET /tensor/reports/7808/figures": {
            "http_status": 404,
            "bytes": 22
          },
          "GET /tensor/reports/7808/artifacts": {
            "http_status": 404,
            "bytes": 22
          }
        }
      },
      "counts": {
        "assets": 11,
        "by_class": {
          "report_markdown": 1,
          "source_code_reference": 1,
          "test_reference": 1,
          "orphan_module_reference": 6,
          "figure_set": 1,
          "embedded_run_log": 1
        },
        "by_resolution": {
          "resolved_in_source": 2,
          "referenced_unresolved": 8,
          "declared_absent": 1
        },
        "resolved_in_source": 2,
        "referenced_unresolved": 8,
        "declared_absent": 1,
        "figures_declared_in_record": 0,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "report_markdown",
          "label": "tensor://reports/7808 markdown (H1 title line as document anchor)",
          "in_report_section": "whole document (H1 at line 1)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "sha256(utf-8 markdown bytes) recomputed and compared with contract.input.source_hash",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 31,
            "start_line": 1,
            "end_line": 1,
            "quote": "# DDES/SAS 混合湍流模块验证报告（G21 缺口填补）",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:400211c8e7f1d52b9e38a7d405bece36c357584bb22f86f7b8289b3af67c82e3",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "Document-scope asset. The identity of this asset is the whole-markdown byte hash; the quote locates the H1 anchor only. Verified separately in integrity.hash_* and in the source block."
        },
        {
          "asset_id": "A02",
          "asset_class": "source_code_reference",
          "label": "src/tensorlbm/ddes.py",
          "in_report_section": "header block (仓/文件 lines) and §1 模块功能",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "existence probe in delivery worktree TensorKnowledge (candidate paths below)",
            "result": "unresolved",
            "searched": [
              "src/tensorlbm/ddes.py",
              "tensorlbm/ddes.py"
            ],
            "found_at": null
          },
          "locator": {
            "method": "char_span",
            "start_char": 135,
            "end_char": 174,
            "start_line": 6,
            "end_line": 6,
            "quote": "`src/tensorlbm/ddes.py`（370 行，G21 孤儿模块）",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:97340d19383dfa8c63cb47896c67d0720f493e3d8e9053ae2e4e2d324135febe",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "Module under test lives in the TensorLBM repo (report header: 仓: TensorLBM); it is not part of the TensorKnowledge delivery worktree, so the reference cannot be resolved here. Line count 370 is asserted by the report only and was NOT re-checked."
        },
        {
          "asset_id": "A03",
          "asset_class": "test_reference",
          "label": "tests/test_ddes_unit.py",
          "in_report_section": "header block (测试 line)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "existence probe in delivery worktree TensorKnowledge (candidate paths below)",
            "result": "unresolved",
            "searched": [
              "tests/test_ddes_unit.py",
              "test_ddes_unit.py"
            ],
            "found_at": null
          },
          "locator": {
            "method": "char_span",
            "start_char": 185,
            "end_char": 221,
            "start_line": 7,
            "end_line": 7,
            "quote": "`tests/test_ddes_unit.py`（22 项，全部通过）",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:a4d6ee417bf7a932784b3ba04d14062708db639b6e41a031190609f0731aa68b",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "Test module of the TensorLBM repo; absent from this worktree. The '22 项' count is a report assertion registered as a reference, not re-executed (out of scope for registration)."
        },
        {
          "asset_id": "A04",
          "asset_class": "orphan_module_reference",
          "label": "ddes.py (G21 orphan module table row)",
          "in_report_section": "§7 G21 缺口状态更新 (table)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "existence probe in delivery worktree TensorKnowledge (candidate paths below)",
            "result": "unresolved",
            "searched": [
              "src/tensorlbm/ddes.py",
              "tensorlbm/ddes.py",
              "ddes.py"
            ],
            "found_at": null,
            "table_cell_quote": "本任务完成"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3057,
            "end_char": 3068,
            "start_line": 150,
            "end_line": 150,
            "quote": "| ddes.py |",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:22475dae045b14c55bb77207e3cb86d03e738ae57cdd87c44ec7190ecd158646",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "The row under validation by this very report (§7). Registered as a reference only; no verification claim is made here."
        },
        {
          "asset_id": "A05",
          "asset_class": "orphan_module_reference",
          "label": "des_turbulence.py (G21 orphan module table row)",
          "in_report_section": "§7 G21 缺口状态更新 (table)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "existence probe in delivery worktree TensorKnowledge (candidate paths below)",
            "result": "unresolved",
            "searched": [
              "src/tensorlbm/turbulence/des_turbulence.py",
              "src/tensorlbm/des_turbulence.py",
              "tensorlbm/des_turbulence.py",
              "des_turbulence.py"
            ],
            "found_at": null,
            "table_cell_quote": "重定向到 turbulence/des_turbulence.py"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3092,
            "end_char": 3113,
            "start_line": 151,
            "end_line": 151,
            "quote": "| des_turbulence.py |",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:27a12320682d1cb5cac6b04065875b6fcb4478a75051ae1f517a9b6ec2bfe9d6",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "Report says the module is redirected to turbulence/des_turbulence.py; target path also absent here. Registered as a reference only; no verification claim is made here."
        },
        {
          "asset_id": "A06",
          "asset_class": "orphan_module_reference",
          "label": "rans_wall_bc.py (G21 orphan module table row)",
          "in_report_section": "§7 G21 缺口状态更新 (table)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "existence probe in delivery worktree TensorKnowledge (candidate paths below)",
            "result": "unresolved",
            "searched": [
              "src/tensorlbm/rans_wall_bc.py",
              "tensorlbm/rans_wall_bc.py",
              "rans_wall_bc.py"
            ],
            "found_at": null,
            "table_cell_quote": "壁函数边界条件"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3158,
            "end_char": 3177,
            "start_line": 152,
            "end_line": 152,
            "quote": "| rans_wall_bc.py |",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:beda7f4bb10d1805ef21929ddbd0fdf35792c42c9ab8da9517ea911c623aa421",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "Listed as 待验证 (not verified). Registered as a reference only; no verification claim is made here."
        },
        {
          "asset_id": "A07",
          "asset_class": "orphan_module_reference",
          "label": "d3q27_collide.py (G21 orphan module table row)",
          "in_report_section": "§7 G21 缺口状态更新 (table)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "existence probe in delivery worktree TensorKnowledge (candidate paths below)",
            "result": "unresolved",
            "searched": [
              "src/tensorlbm/d3q27_collide.py",
              "tensorlbm/d3q27_collide.py",
              "d3q27_collide.py"
            ],
            "found_at": null,
            "table_cell_quote": "D3Q27 碰撞"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3196,
            "end_char": 3216,
            "start_line": 153,
            "end_line": 153,
            "quote": "| d3q27_collide.py |",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:08d0ca4e4f710f1d40038ea396572d07b89f7407acaa2988da000d14987d693b",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "Listed as 待验证 (not verified). Registered as a reference only; no verification claim is made here."
        },
        {
          "asset_id": "A08",
          "asset_class": "orphan_module_reference",
          "label": "hybrid_solver.py (G21 orphan module table row)",
          "in_report_section": "§7 G21 缺口状态更新 (table)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "existence probe in delivery worktree TensorKnowledge (candidate paths below)",
            "result": "unresolved",
            "searched": [
              "src/tensorlbm/hybrid_solver.py",
              "tensorlbm/hybrid_solver.py",
              "hybrid_solver.py"
            ],
            "found_at": null,
            "table_cell_quote": "混合求解器"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3236,
            "end_char": 3256,
            "start_line": 154,
            "end_line": 154,
            "quote": "| hybrid_solver.py |",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:d50aafcbbe705cf36bd5267d21b1c5fa2276583e98029c383868f238cc7ef827",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "Listed as 待验证 (not verified). Registered as a reference only; no verification claim is made here."
        },
        {
          "asset_id": "A09",
          "asset_class": "orphan_module_reference",
          "label": "prism_solver.py (G21 orphan module table row)",
          "in_report_section": "§7 G21 缺口状态更新 (table)",
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "existence probe in delivery worktree TensorKnowledge (candidate paths below)",
            "result": "unresolved",
            "searched": [
              "src/tensorlbm/prism_solver.py",
              "tensorlbm/prism_solver.py",
              "prism_solver.py"
            ],
            "found_at": null,
            "table_cell_quote": "棱柱求解器"
          },
          "locator": {
            "method": "char_span",
            "start_char": 3273,
            "end_char": 3292,
            "start_line": 155,
            "end_line": 155,
            "quote": "| prism_solver.py |",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:1cbec1a181af4fc4a0d275f68c8f515d04ad5e69a18fb5c78984665cba43a383",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "Listed as 待验证 (not verified). Registered as a reference only; no verification claim is made here."
        },
        {
          "asset_id": "A10",
          "asset_class": "figure_set",
          "label": "figures of report 7808 (empty set)",
          "in_report_section": "§4 结果图 and platform record field figures",
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "platform record figures == [] AND GET reports/7808/{figures,artifacts} probed",
            "result": "absent"
          },
          "locator": {
            "method": "char_span",
            "start_char": 2259,
            "end_char": 2289,
            "start_line": 103,
            "end_line": 103,
            "quote": "本任务为纯单元测试验证，无数值模拟场量，故无云图/曲线生成。",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:a3e4037cda25539e14bce735b221e9a787dde5ee5fc9e23b65ff2bcebe18c513",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "The report declares no figures and the platform serves none: record.figures is an empty list, /tensor/reports/7808/figures -> HTTP 404, /tensor/reports/7808/artifacts -> HTTP 404. Nothing is claimed about figure bytes."
        },
        {
          "asset_id": "A11",
          "asset_class": "embedded_run_log",
          "label": "pytest run summary block (22 passed, 1 warning in 6.30s)",
          "in_report_section": "§3 计算结果 (fenced block)",
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim substring present and unique in markdown",
            "result": "resolved"
          },
          "locator": {
            "method": "char_span",
            "start_char": 1772,
            "end_char": 1801,
            "start_line": 81,
            "end_line": 81,
            "quote": "22 passed, 1 warning in 6.30s",
            "unique": true,
            "end_char_exclusive": false,
            "quote_sha256": "sha256:25a6ac2e91e11f1a2e759eec1c10defc4359ac435d42175885320c463a64a211",
            "occurrences_in_source": 1,
            "char_span_roundtrip_ok": true
          },
          "note": "In-report artefact (a pasted terminal line). It is registered as-is: the worker did not re-run the TensorLBM test suite, so the 22-pass figure stays an upstream assertion."
        }
      ],
      "claims": [],
      "claims_empty_reason": "Contract objective is register_assets=true / classify_report_type=false and notes state 'claims 允许为空数组'; constraint no_forced_claim_generation=true forbids inventing knowledge to fill the field. Extraction is a downstream work package, so an empty claims array is the complete result for wp-7808-01.",
      "id_integrity": {
        "ids_checked": 11,
        "duplicates": [],
        "pattern_ok": true,
        "unique": true
      },
      "coverage": {
        "path_token_regex": "[A-Za-z0-9_./-]+\\.(?:py|png|csv|json|md|txt|h5|dat|pdf|log|ipynb)",
        "distinct_tokens": 9,
        "tokens": [
          "d3q27_collide.py",
          "ddes.py",
          "des_turbulence.py",
          "hybrid_solver.py",
          "prism_solver.py",
          "rans_wall_bc.py",
          "src/tensorlbm/ddes.py",
          "tests/test_ddes_unit.py",
          "turbulence/des_turbulence.py"
        ],
        "token_to_asset_ids": {
          "d3q27_collide.py": [
            "A07"
          ],
          "ddes.py": [
            "A02",
            "A04"
          ],
          "des_turbulence.py": [
            "A05"
          ],
          "hybrid_solver.py": [
            "A08"
          ],
          "prism_solver.py": [
            "A09"
          ],
          "rans_wall_bc.py": [
            "A06"
          ],
          "src/tensorlbm/ddes.py": [
            "A02",
            "A04"
          ],
          "tests/test_ddes_unit.py": [
            "A03"
          ],
          "turbulence/des_turbulence.py": [
            "A05"
          ]
        },
        "unmapped_tokens": [],
        "full_coverage": true
      },
      "integrity": {
        "quote_uniqueness": "every asset quote verified verbatim in markdown; duplicates flagged",
        "quote_occurrences": {
          "A01": 1,
          "A02": 1,
          "A03": 1,
          "A04": 1,
          "A05": 1,
          "A06": 1,
          "A07": 1,
          "A08": 1,
          "A09": 1,
          "A10": 1,
          "A11": 1
        },
        "quotes_not_found": [],
        "quotes_not_unique": [],
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "chars_match_contract": true,
        "valid_json": true
      },
      "unresolved": [
        {
          "asset_id": "A02",
          "name": "src/tensorlbm/ddes.py",
          "reason": "path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header"
        },
        {
          "asset_id": "A03",
          "name": "tests/test_ddes_unit.py",
          "reason": "path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header"
        },
        {
          "asset_id": "A04",
          "name": "ddes.py (G21 orphan module table row)",
          "reason": "path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header"
        },
        {
          "asset_id": "A05",
          "name": "des_turbulence.py (G21 orphan module table row)",
          "reason": "path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header"
        },
        {
          "asset_id": "A06",
          "name": "rans_wall_bc.py (G21 orphan module table row)",
          "reason": "path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header"
        },
        {
          "asset_id": "A07",
          "name": "d3q27_collide.py (G21 orphan module table row)",
          "reason": "path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header"
        },
        {
          "asset_id": "A08",
          "name": "hybrid_solver.py (G21 orphan module table row)",
          "reason": "path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header"
        },
        {
          "asset_id": "A09",
          "name": "prism_solver.py (G21 orphan module table row)",
          "reason": "path not present in delivery worktree TensorKnowledge; lives in the TensorLBM repo named in the report header"
        }
      ],
      "observations": [
        "Markdown is 3389 chars / 5210 bytes, 160 lines; H1 title and §1-§7 all present; hash and char count match the contract exactly.",
        "The report declares no figures (record.figures == []) and states in §4 that no field plots were produced; figure bytes are therefore not claimed at all.",
        "Nine of eleven registered assets are code/module references that live in TensorLBM, not in this delivery worktree; they are registered as unresolved references, not as broken upstream artefacts.",
        "Six public function names (ddes_shielding_function, ddes_length_scale, ddes_eddy_viscosity, sas_source_term, apply_ddes_collision, run_ddes_diagnostics) appear in §1 模块功能; they are code symbols inside the referenced module, not standalone artefacts, so they are recorded here as an observation rather than padded into the asset list.",
        "Body path-token coverage is complete: every distinct file-like token in the markdown maps to at least one registered asset (see counts/coverage); no attachment, URL or figure reference was left unregistered.",
        "The pytest summary line '22 passed, 1 warning in 6.30s' is registered as an embedded run-log artefact; it was not re-executed by this work package."
      ],
      "limitations": [
        "Registration only: no claim extraction, no report-type classification, no verified marks (verification is computed by the platform gate).",
        "source_hash scope = UTF-8 bytes of the exact markdown string stored for report 7808; any edit (even whitespace) invalidates it.",
        "Reference resolution is limited to the TensorKnowledge delivery worktree; a missing path here means 'not resolvable in this repo', never 'absent upstream'.",
        "The report's own counts (370 lines of ddes.py, 22 passing tests) are upstream assertions and were not re-measured.",
        "A byte-exact copy of the source markdown is committed under docs/kf/wp-7808-01/ (hash-pinned) only to make the acceptance checks re-runnable offline: artifacts/ is gitignored and is dropped by the mission push gate, so keeping the fixture there would silently break the tests in the pushed repo."
      ]
    }
  },
  "claims": []
}
```
