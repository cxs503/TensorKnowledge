# KF-RESULT wp-5406-01

工作包 `wp-5406-01`（`01-asset-registration`，lane C）对 report_id=**5406** 的资产登记结果。
本单只登记源资产，不做分类、不抽取 claim、不给 verified。

## ① 本工序做了什么

* 拉取 `tensor://reports/5406` 的记录，取 `markdown` 字段；对**markdown 的 UTF-8 字节**重算
  sha256，与包契约的 `source_hash` 逐位比对：`sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a`。
* 登记正文里被反引号引用的**路径型 token**（文件/目录/测试 node id）与记录
  `figures` 里的图，共 **14** 条资产（其中报告图 1 条），
  每条带逐字引文 + 起止偏移 + 行号 + 引文 sha256。
* 对每条资产给出**可达性**判定：字节可得 = 0 条；
  未解决 = 13 条（含 1 条"仅元数据声明"的报告图，计入未解决集合，
  因为它的 png 字节不在 `markdown` 字段里）。
* 不生成 claim（`claims.extracted = 0`），不写
  `verified`（`verification.status = "not_marked_verified"`）。
* 记录 `markdown` 长度 3815 字符 / 6571 字节，与契约 `chars: 3815`
  一致（`chars_match = True`）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET ${TENSOR_API_BASE}/tensor/reports/5406`（Bearer 登录 token），
   记录落 `knowledge/assets/wp-5406-01/report_record.json`，`markdown` 原字节落
   `knowledge/assets/wp-5406-01/source_snapshot.md`。快照字节哈希 =
   `sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a`。
2. **哈希**：`hashlib.sha256(markdown.encode('utf-8'))`，不做换行/空白归一化——
   契约给的是 markdown 字节哈希，归一化会让 E2 失去意义。
3. **资产发现**（`scripts/wp5406_asset_manifest.py::discover_paths`）：只扫**行内代码段**
   内的空白分隔 token，按「含 `/` 或带文件扩展名」判为路径型；每个 token 用
   **路径字母表边界**定位（`(?<![\w./\\-])…(?![\w/\\-])`），因此
   `provenance_gate_matrix.png` 里的 `gate_matrix.png` **不会**被当成一条独立资产
   （这条边界规则是本次实测踩出来的：第一版用字符集合判断，`_` 不在集合里，
   于是图 `gate_matrix.png` 被误挂了一个假 locator）。
4. **目录/基名的诚实处理**：正文只给基名（如 `gate_evidence.json`）时不编造全路径；
   若与某已登记目录同处一行，则记 `member_of`（本次三条产物都 bound 到
   `artifacts/m4829_ci_gate`）。目录引用（`artifacts/`、`docs/`、`src/`、
   `artifacts/m4829_ci_gate/`）一律判 `unresolved_referenced_directory`，**不**因为
   交付仓里同名目录存在就判"可达"（那是名字巧合，不是同一资产）。
5. **图资产**：记录 `figures[0]` 只有 `name` + `caption`，没有 `png_base64`，
   正文也从不写文件名 → 登记为 `locator_type = record_field`（`figures[0].name`），
   `mentions = []`，状态 `declared_metadata_only`。自检对它做**字段漂移**检查：
   记录里名字一变即 FAIL（`tests/test_wp5406_asset_manifest.py` 有对应用例）。
6. **交叉复核**：用平台自己的库 `ke.wp_gate.ApiSourceResolver`（与本脚本无共享代码）
   独立重解析 5406 并算哈希：`sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a`，
   与清单/契约一致 = `True`，字符数
   `3815` vs 清单 `3815`。
7. **自检**：脚本内置 9 条检查（见 ⑥），另有
   `python -m pytest tests/test_wp5406_asset_manifest.py -q` → **14 passed**。
8. **图**：`scripts/wp5406_asset_figure.py` 读清单与交叉复核结果画三联图（无手抄数值）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `knowledge/assets/wp-5406-01/asset_manifest.json` | 交付物本体：源哈希/字符数/记录元信息 + 14 条资产（含 locator 与可达性）+ counts + 自检块；sha256 `sha256:f45d280b003d377097be044bf74a41963f4abc3eb44a582e5eddd21ea32ea476` |
| `knowledge/assets/wp-5406-01/self_checks.json` | 9 条自检结果，`all_pass = True` |
| `knowledge/assets/wp-5406-01/platform_resolver_check.json` | 平台库独立重算哈希的交叉复核证据 |
| `knowledge/assets/wp-5406-01/source_snapshot.md` | 报告 5406 的 markdown 原字节快照（哈希同契约） |
| `knowledge/assets/wp-5406-01/report_record.json` | 记录原文快照（title/figures/tags 等元信息） |
| `knowledge/assets/wp-5406-01/asset_reachability.png` | 三联图：可达性状态 / locator 类型 / 三处哈希一致 |
| `knowledge/assets/wp-5406-01/kf_result.json` | 本报告的 KF-RESULT 载荷（下方唯一 json 块逐字节相同） |
| `scripts/wp5406_asset_manifest.py` | 工序本体（登记 + 自检，可离线重跑） |
| `scripts/wp5406_asset_figure.py` / `scripts/wp5406_kf_result.py` / `scripts/wp5406_report.py` | 图 / 结果载荷 / 本报告，全部程序化生成 |
| `tests/test_wp5406_asset_manifest.py` | 14 条不变量测试（含"最长路径不得解析自身后缀"与三条有牙齿的反例） |

**资产清单（14 条）**

| id | path | kind | 可达性 | 字节可得 |
|---|---|---|---|---|
| asset:5406:p001 | `artifacts`/ | referenced_path_other | unresolved_referenced_directory | False |
| asset:5406:p002 | `artifacts/m4829_ci_gate`/ | referenced_artifact | unresolved_referenced_directory | False |
| asset:5406:p003 | `artifacts/m4829_ci_gate/gate_evidence.json` | referenced_artifact | unresolved_external_artifact | False |
| asset:5406:p004 | `docs`/ | referenced_path_other | unresolved_referenced_directory | False |
| asset:5406:p005 | `docs/ci_clearance_m4829.md` | referenced_doc | unresolved_external_artifact | False |
| asset:5406:p006 | `gate_evidence.json` | referenced_artifact | unresolved_bare_filename | False |
| asset:5406:p007 | `ledger_regeneration.png` | referenced_artifact | unresolved_bare_filename | False |
| asset:5406:p008 | `provenance_gate_matrix.png` | referenced_artifact | unresolved_bare_filename | False |
| asset:5406:p009 | `scripts/audit_doc_evidence.py` | referenced_script | unresolved_external_artifact | False |
| asset:5406:p010 | `scripts/m4857_ci_gate_evidence.py` | referenced_script | unresolved_external_artifact | False |
| asset:5406:p011 | `src`/ | referenced_path_other | unresolved_referenced_directory | False |
| asset:5406:p012 | `tests/test_doc_evidence_pointers.py::DocumentedEvidenceGateTests::test_committed_ledger_is_current` | referenced_test | unresolved_external_artifact | False |
| asset:5406:p013 | `tests/test_threefield_fragmentation_analytic.py::WeibullFitRecoveryTests::test_cdf_agreement_r2_high_for_weibull_data` | referenced_test | unresolved_external_artifact | False |
| asset:5406:f001 | `gate_matrix.png` | report_figure | declared_metadata_only | False |

`distinct_by_basename = 13`：`gate_evidence.json` 同时以
全路径与基名出现，清单用 `same_asset_as` 关联而**不**合并，避免下游重复计数。

## ④ 证据定位表（claim/字段 → 原文逐字引文）

| 资产 id | 原文引文（逐字） | 原文行 | 出现次数 |
|---|---|---|---|
| asset:5406:p001 | `artifacts/` | 82 | 1 |
| asset:5406:p002 | `artifacts/m4829_ci_gate/` | 20 | 3 |
| asset:5406:p003 | `artifacts/m4829_ci_gate/gate_evidence.json` | 39 | 1 |
| asset:5406:p004 | `docs/` | 58 | 1 |
| asset:5406:p005 | `docs/ci_clearance_m4829.md` | 19 | 2 |
| asset:5406:p006 | `gate_evidence.json` | 20 | 3 |
| asset:5406:p007 | `ledger_regeneration.png` | 20 | 2 |
| asset:5406:p008 | `provenance_gate_matrix.png` | 20 | 2 |
| asset:5406:p009 | `scripts/audit_doc_evidence.py` | 81 | 1 |
| asset:5406:p010 | `scripts/m4857_ci_gate_evidence.py` | 41 | 1 |
| asset:5406:p011 | `src/` | 82 | 1 |
| asset:5406:p012 | `tests/test_doc_evidence_pointers.py::DocumentedEvidenceGateTests::test_committed_ledger_is_current` | 12 | 1 |
| asset:5406:p013 | `tests/test_threefield_fragmentation_analytic.py::WeibullFitRecoveryTests::test_cdf_agreement_r2_high_for_weibull_data` | 80 | 1 |
| asset:5406:f001 | `gate_matrix.png` | record.figures[0].name | 0 (record field) |

同一资产多次出现（全部行号已登记，用于下游取更贴合的上下文）：

| 资产 id | path | 原文行 |
|---|---|---|
| asset:5406:p002 | `artifacts/m4829_ci_gate` | 20, 31, 34 |
| asset:5406:p005 | `docs/ci_clearance_m4829.md` | 19, 39 |
| asset:5406:p006 | `gate_evidence.json` | 20, 49, 64 |
| asset:5406:p007 | `ledger_regeneration.png` | 20, 51 |
| asset:5406:p008 | `provenance_gate_matrix.png` | 20, 50 |

元信息类断言（不在 markdown 字节内，故用记录字段定位、不做逐字引文）：

| 字段 | 值 | 来源 |
|---|---|---|
| `report_id` | `5406` | 记录主键 |
| `scenario_key` | `tensordem_ci_clearance` | `record.scenario_key` |
| `mission_id` | `4857` | `record.mission_id` |
| `title` | TensorDEM main CI 清红（m4857）：合并丢 blob 导致的证据账本红及其判别加固 | `record.title` |
| `source_hash` | `sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a` | markdown 字节重算 |

## ⑤ 注意点与局限

* **字节可得 = 0**：本单没有任何一条资产的字节能从 `markdown` 字段取出。
  13 条未解决里，三条 m4829 产物 + 两个脚本 + 两个测试 + 文档
  都在 **TensorDEM** 仓；本交付仓是 TensorKnowledge，不 checkout TensorDEM，
  因此既不能验证它们存在，也不能验证其内容——只登记"被引用"。这是**上限明确的
  不完整**，不是"已完成"。
* **报告图的 png 不可取**：`figures` 只有 name/caption，无法把图当字节资产传给下游；
  下游若需要图，须回到出报告者/仓里取。
* **路径 token 抽取是文本级的**：不解析 markdown 语义，扫的是行内代码段。正文里若有
  未被反引号包住的路径，或跨行的路径拼接，会漏登记。本报告实测 14
  条全部来自反引号段；漏检风险已如实标注，未做"看起来覆盖全"的声明。
* **同一资产的双重登记**：`gate_evidence.json`（基名）与
  `artifacts/m4829_ci_gate/gate_evidence.json`（全路径）是同一文件的两处引用，
  用 `same_asset_as` 关联；下游若按 id 计数会得到 14，
  按 basename 去重是 13。
* **不做的事**：不分类报告类型（契约 `classify_report_type: false`）、不抽 claim、
  不改写上游、不标 verified。verification 由平台门计算。
* **版本记录（作废说明）**：本单首次发布为 report 14639，产物路径写成 `artifacts/wp-5406-01/`；
  而 `artifacts/` 在本仓 `.gitignore` 内（推门亦会滤除 `artifacts/**`），产物不会入库。
  故产物改落受版本控制的 `knowledge/assets/wp-5406-01/` 并重发本报告；平台报告接口无更新/删除
  （PUT/PATCH/DELETE 实测均 405），14639 无法撤回、按作废处理，它与本版的差异仅限产物路径。
* **未运行的检查**：`scripts/validate_work_package.py` 的三门校验**没有**对本包跑——
  它验证的是 03 工序的四文件包（`claims/evidence/provenance/extraction_summary`），
  本包契约的输出是单一 `asset_manifest.json`，硬套会得到一堆与工序无关的 S 项失败，
  那是错误证据而非证据。所以本包的性质由 ⑥ 的 9 条自检 + 14 条 pytest 不变量 + 平台库
  哈希交叉复核来支撑，如实说明该门未覆盖本工序。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 判定 | 依据 |
|---|---|---|
| valid_json | ✅ | `asset_manifest.json` 由 json 序列化产出，测试用例重新加载解析 |
| schema_pass | ✅ | 自检 `schema_pass_manifest_v1`：必需键齐全（manifest_version/package_id/task_type/source/attachments/counts，每条资产 id/path/kind/mentions/reachability） |
| source_locator_resolvable | ✅ | 自检 `source_locator_resolvable`：每条 mention 重切偏移逐字相等、引文 sha256 相等；图资产用 `record.figures[0].name` 漂移检查（反例测试证明该检查会 FAIL） |
| source_hash_matches | ✅ | `sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a` == 契约；平台库独立重算一致 `True` |
| no_duplicate_ids | ✅ | 14 个 id 全 distinct，均 `asset:5406:` 前缀 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组（契约允许）；每条资产都有 `reachability.status` + `detail` + `checked`，无"默认可达" |

自检明细（`self_checks.json`，`all_pass = True`）：

| 检查 | 结果 | 细节 |
|---|---|---|
| valid_json | PASS | manifest built and re-serialised without error |
| source_hash_matches | PASS | declared=sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a computed=sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a |
| chars_match_declared | PASS | declared=3815 computed=3815 |
| no_duplicate_ids | PASS | 14 ids, 14 distinct |
| source_locator_resolvable | PASS | unresolvable=[] |
| every_asset_has_evidence_or_explicit_unresolved_status | PASS | assets without reachability status=[] |
| single_report_scope | PASS | only report 5406 is read |
| do_not_mark_claims_as_verified | PASS | not_marked_verified |
| schema_pass_manifest_v1 | PASS | required keys of manifest_version/package_id/task_type/source/attachments/counts |

**诚实项**：没有失败项；但"字节可得 = 0 / 未解决 13 条"是真实覆盖缺口，
不是通过项——它反映的是本次只能拿到 markdown 文本这一事实。

## 复跑

```bash
python scripts/wp5406_asset_manifest.py --offline-from knowledge/assets/wp-5406-01/report_record.json \
  && python scripts/wp5406_asset_figure.py \
  && python scripts/wp5406_kf_result.py \
  && python scripts/wp5406_report.py \
  && python -m pytest tests/test_wp5406_asset_manifest.py -q
```

（在线版去掉 `--offline-from`，改走 `$TENSOR_API_BASE` 拉取；两条路径产出的清单**逐字节相同**，
本次已实测。）

## KF-RESULT 载荷

```json
{
  "package_id": "wp-5406-01",
  "task_type": "01-asset-registration",
  "report_id": "5406",
  "provenance": {
    "source_uri": "tensor://reports/5406",
    "source_field": "markdown",
    "source_hash": "sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a",
    "source_chars": 3815,
    "source_bytes": 6571,
    "hash_recomputed_by": "scripts/wp5406_kf_result.py (sha256 of the fetched markdown bytes)",
    "platform_cross_check": {
      "library": "ke.wp_gate.ApiSourceResolver",
      "platform_sha256": "sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a",
      "agrees": true
    },
    "pipeline": "KBM-RCI-F1-FACTORY",
    "work_package": "wp-5406-01",
    "lane": "C",
    "report_snapshot": "knowledge/assets/wp-5406-01/source_snapshot.md",
    "record_snapshot": "knowledge/assets/wp-5406-01/report_record.json"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "knowledge/assets/wp-5406-01/asset_manifest.json",
      "sha256": "sha256:f45d280b003d377097be044bf74a41963f4abc3eb44a582e5eddd21ea32ea476",
      "attachments": 14,
      "figures": 1,
      "unresolved": 13,
      "with_bytes_available": 0,
      "checks_passed": true
    },
    "self_checks.json": {
      "path": "knowledge/assets/wp-5406-01/self_checks.json",
      "sha256": "sha256:c0284e52a71b096b48179c3cd1a6827383fce002dcf2954a6528be8f7c6fdf86",
      "checks": 9,
      "failed": []
    },
    "platform_resolver_check.json": {
      "path": "knowledge/assets/wp-5406-01/platform_resolver_check.json",
      "sha256": "sha256:ed36c55f434b9742e2e8a49bc0da819454726ae6f08ddfe62bec6ff3ab30b3db",
      "hash_agrees_with_contract": true
    },
    "source_snapshot.md": {
      "path": "knowledge/assets/wp-5406-01/source_snapshot.md",
      "sha256": "sha256:9c071693614c9bed438bea6aa35956a5f00e1790eb5d48ae48086cc2732ede8a"
    },
    "asset_reachability.png": {
      "path": "knowledge/assets/wp-5406-01/asset_reachability.png",
      "sha256": "sha256:4e55cd8c3f47de55c11102b95591141f1197098ce1e59c14dd4040a568bb6530"
    }
  },
  "repro_cmd": "python scripts/wp5406_asset_manifest.py --offline-from knowledge/assets/wp-5406-01/report_record.json && python scripts/wp5406_asset_figure.py && python scripts/wp5406_kf_result.py"
}
```
