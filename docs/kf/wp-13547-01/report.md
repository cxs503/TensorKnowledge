# KF-RESULT wp-13547-01

> 工序 01-asset-registration · report_id=13547 · lane C · 产出 `asset_manifest.json`（登记，不抽取）
> source_hash（平台可独立重算，sha256 over markdown utf-8 bytes）= `sha256:2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42`
> 契约 source_hash = `sha256:2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42` → 逐字符一致

## ① 本工序做了什么

对 `report_id=13547`（《TensorKnowledge 质量审计（A+B）：14 个 scope 的成熟度判定与 main 红态根因》，scenario_key=`quality-audit`）执行**资产登记**：
确认报告 markdown 的字节哈希与契约一致（6168 字符 / 8782 字节 utf-8），把正文里可解析的附件/工件登记为带**可复算定位器**的清单：
内嵌图、源码/工件路径引用、表格、复现命令块、接口字段。**不做抽取、不生成 claim、不标注 verified**
（契约 `objective.classify_report_type=false`，`notes` 明确 claims 允许为空数组）。

规模：登记资产 **22** 项，claims **0** 项；`counts.by_resolution` = `{"resolved_in_source": 12, "referenced_unresolved": 10}`。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET /api/v1/tensor/reports/13547` 取 `markdown` 字段（`scripts/kf/kf01_register.py::fetch_report`）；只碰这一个 report_id，全程未凭记忆复述。
2. **哈希门**：对 markdown 的 utf-8 字节做 sha256，与契约 `source_hash`/`chars` 双比对，不一致直接 `SystemExit`（不产出半成品）。
3. **定位器生成**：`Source` 用逐行长度前缀和求出每行起始字符偏移，资产定位器一律为**绝对字符跨度** + 反推的 1-based 行号；
   `quote` 取自源字节切片 `md[s:e]`，**不存在手抄环节**（这也使平台侧「子串独立重算」必然成立）。
4. **扫描规则**（确定性、无领域硬编码；域参数经包配置传入）：行内代码/围栏代码中的 `*.py|json|png|md|csv|yaml` 路径 → 路径引用（出现级身份 = 路径 × 行号）；`record.figures[]` → 内嵌图（`png_base64` 为空则 `metadata_only`，不伪造字节哈希）；
   连续 `|` 行 → 表格（只记行数×列数几何，不复述内容）；``` 围栏 → 复现命令块；配置声明的接口端点/字段 → `api_endpoint`/`api_field`。
5. **本地解析**：路径只在**本交付工作树**内解析（`os.path.isfile` + 命中文件 sha256）；属产出仓 cxs503/TensorKnowledge（被审计仓 = 本工作树） 的路径
   越界即如实记 `referenced_unresolved`，不读别的仓。
6. **信封 + 自检**：`kf_result.json` 按 `schemas/kf_result.v1.schema.json` 生成；`verification.json` 用 jsonschema（draft 2020-12）
   分别校验信封与清单，并逐条重算 acceptance 项。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `asset_manifest.json` | 22 项资产；`by_class`={"report_markdown": 1, "embedded_figure": 3, "document_reference": 2, "source_code_reference": 9, "report_table": 5, "db_table": 1, "schema_field": 1}；claims=0；sha256 `4af934893732bf713346bca16c467d3f7445160bf3a480c6773a4d6404e8df93` |
| `kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims）；sha256 `f2d8ca054b8f715b0ef09b75e0861647443dea7c44901315ab6873d710788cd7` |
| `verification.json` | 10 项 acceptance 自检逐条 pass/fail + 重算哈希；`all_pass`=True |
| `report.md` | 本报告（由清单/信封/自检**程序化渲染**，无手抄）|
| `figures/wp-13547-01_asset_locator_map.png` | A) 资产类别×解析状态计数；B) 每个资产的字符跨度覆盖图 |
| `evidence_git_probe.json` | git 探针：2/2 个 ref 在本工作树实存；范围探针 1 条 |

资产类别分布：`{"report_markdown": 1, "embedded_figure": 3, "document_reference": 2, "source_code_reference": 9, "report_table": 5, "db_table": 1, "schema_field": 1}`。

## ④ 结果图

![asset locator map](figures/wp-13547-01_asset_locator_map.png)

**图注**：A) 资产类别 × 解析状态（绿=源内已解析、红=引用未解析、灰=声明缺失）；B) 每个资产在 markdown 中的字符跨度
（横轴=字符偏移，源文档 6168 字符）。两图直接由 `asset_manifest.json` 绘出，零手抄。
红色条不是缺陷而是**边界的正确表达**：审计结论图在 `record.figures[]` 里只有 name+caption（`png_base64` 为空），本包不伪造字节哈希，如实记 `referenced_unresolved`（metadata_only）；绿条则是本工作树内**真的解析到**的路径（被审计仓即本仓）。

## ④-b git 证据探针（报告点名的 commit 在本工作树是否真实存在）

| ref | 出处行 | 实存 | 解析 sha | 提交时间 | 主题 / 说明 | HEAD 祖先链 |
|---|---:|---|---|---|---|---|
| `edbc20a` | 3 | 是 | `edbc20a61ade` | 2026-11-10T00:26:11+08:00 | Merge #17 (m8688) via push-merge | 是 |
| `2d3c446` | 3 | 是 | `2d3c446388d4` | 2026-11-11T09:56:48+08:00 | Merge pull request #26 from cxs503/agent/m8817 | 是 |

范围探针：`edbc20a..2d3c446`（两端实存，`rev-list --count`=33）。范围探针只回答「区间在本工作树可解析」，**不复核**报告自报的文件/行数口径。

**边界**：identification evidence only: it answers «is the git object the report names real in this worktree?», never «is the report's verdict correct?». Claim grading stays with the platform gate.

仓库身份：工作树 HEAD `d87375feac49`（分支 `agent/m20589`，可达对象 1568 个）；报告点名仓 `cxs503/TensorKnowledge`；`slug_match`=`match`。

**发布状态**：`awaiting_pr_merge`（本报告渲染于 `publish` 之前，最终状态以 `published.json` 为准；本包不自称已发布）。

## ⑤ 证据定位表（资产 → 原文逐字片段，均由 `md[start_char:end_char]` 计算）

| asset_id | 类别 | 解析 | 行 | 原文片段（逐字） |
|---|---|---|---|---|
| A01 | report_markdown | resolved_in_source | L1 | `# TensorKnowledge 质量审计（A+B）：可验证功能交付判定  **mission 14492 · verdict` |
| A02 | embedded_figure | referenced_unresolved | L1 | `# TensorKnowledge 质量审计（A+B）：可验证功能交付判定  **mission 14492 · verdict` |
| A03 | embedded_figure | referenced_unresolved | L1 | `# TensorKnowledge 质量审计（A+B）：可验证功能交付判定  **mission 14492 · verdict` |
| A04 | embedded_figure | referenced_unresolved | L1 | `# TensorKnowledge 质量审计（A+B）：可验证功能交付判定  **mission 14492 · verdict` |
| A05 | document_reference | resolved_in_source | L13 | `\| 证据目录 \| 'artifacts/audit/*.log'、'artifacts/audit/figures/'、'a` |
| A06 | source_code_reference | resolved_in_source | L25 | `   - 'python -m pytest tests/ -q --ignore=tests/test_sediment_m7` |
| A07 | source_code_reference | resolved_in_source | L26 | `   - 'python -m pytest tests/test_ke_export.py tests/test_datase` |
| A08 | source_code_reference | referenced_unresolved | L28 | `   - 'cd runs/oss-lbm-kruger-8676 && python analyze_validation.p` |
| A09 | source_code_reference | referenced_unresolved | L53 | `\| 全仓测试（剔除该文件） \| 'pytest tests/ --ignore=...m7437.py' \| 83 pas` |
| A10 | source_code_reference | referenced_unresolved | L57 | `\| 知识包校验 \| 'validate_oss_lbm.py' / 'validate_kruger.py' \| PASS` |
| A11 | source_code_reference | referenced_unresolved | L57 | `\| 知识包校验 \| 'validate_oss_lbm.py' / 'validate_kruger.py' \| PASS` |
| A12 | source_code_reference | referenced_unresolved | L58 | `\| ontology v1 \| 'validate_ontology_v1.py' \| 6 schemas PASS，3 ` |
| A13 | source_code_reference | referenced_unresolved | L59 | `\| sediment verify ×3 \| 'verify_sediment_m2400/m5490/m7485.py' ` |
| A14 | source_code_reference | referenced_unresolved | L61 | `\| 基准复现 \| 'analyze_validation.py' 重跑 \| 'git status -- runs/' 空` |
| A15 | document_reference | resolved_in_source | L96 | `- **报告 ≠ 证据**：2 份 sediment 报告 + 1 份 MISSION_COMPLETION 的"验证完成"均为` |
| A16 | report_table | resolved_in_source | L7 | `\| 项目 \| 值 \| \|---\|---\| \| 仓库 \| 'cxs503/TensorKnowledge'（mai` |
| A17 | report_table | resolved_in_source | L35 | `\| 类别 \| 文件 \| 行数 \| \|---\|---:\|---:\| \| 核心功能模块 'ke/' \| 5 \|` |
| A18 | report_table | resolved_in_source | L50 | `\| 对象 \| 命令 \| 结果 \| 判定 \| \|---\|---\|---\|---\| \| 全仓测试（默认） \|` |
| A19 | report_table | resolved_in_source | L65 | `\| L \| 数量 \| scope \| \|---\|---:\|---\| \| L5 \| 0 \| — \| \| ` |
| A20 | report_table | resolved_in_source | L76 | `\| 算例 \| 关键量 \| 实测 \| 基准（解析） \| 误差 \| <3%? \| \|---\|---\|---\|-` |
| A21 | db_table | resolved_in_source | L14 | `tensor_maturity_verdicts` |
| A22 | schema_field | resolved_in_source | L97 | `epistemic_status.enum` |

（完整 quote 与字符跨度见 `asset_manifest.json` 各 `locator`；平台可对每条 quote 做子串 + 行号独立复核。）

## ⑥ 注意点与局限

1. **登记 ≠ 抽取**：清单只回答「报告里有哪些可解析工件、在其中何处」，不回答「报告说了什么」。claims 为空是契约允许的完整结果。
2. **不标 verified**：清单与信封里没有任何 `verified` 状态；验证由平台门计算，本工序只提供可复算的定位器与哈希。
3. **图只有元数据**：报告记录 `figures[]` 共 3 项均无 `png_base64` 载荷（0 字节），故只登记 name/caption + 正文出现位置，
   记 `metadata_only`（`resolution=referenced_unresolved`），**不宣称拿到图字节**。
4. **同仓可解析、越界如实留白**：本报告的审计对象就是本工作树（`cxs503/TensorKnowledge`），
   故 `audit_report.md`、`docs/sediment-m2591-report.md` 等路径在包内**实解析**（记 sha256 + 字节数）；
   `artifacts/audit/*.log`（通配符而非单文件）与仅以裸名引用的脚本（如 `validate_oss_lbm.py` 实位于 `scripts/`）
   仍记 `referenced_unresolved` 并写明原因，不用「大概存在」补齐。
5. **表格内容未复述**：5 张表只登记几何（行×列）与字符跨度，避免把报表数字二次转写引入漂移。
6. **schema 口径**：仓库内 `schemas/asset_manifest.v1.schema.json` 把 `package_id/task_type/report_id`/`source.uri` 钉死为 wp-448-01 的包级取值，
   自检时**仅放松这四处包级固定值**（`source.uri` 改为 `^tensor://reports/[0-9]+$`，其余约束照常生效）并如实记录在 `detail` 里，避免把「本包必挂」伪装成通过。

## ⑦ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 细节 |
|---|---|---|
| valid_json | PASS | json.loads OK for asset_manifest.json and kf_result.json |
| schema_pass | PASS | jsonschema draft2020-12 errors=0 [] \| asset_manifest.v1 checked with its four package-pinned consts relaxed (package_id/task_type/report_id/source.ur |
| source_locator_resolvable | PASS | checked 22 locators (char span + verbatim quote + 1-based line map + token span); unresolvable=[] |
| source_hash_matches | PASS | recomputed=2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42 manifest=2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42  |
| no_duplicate_ids | PASS | assets=22 unique=22 |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | claims=0 violating=0 (empty array: vacuously satisfied per contract notes) |
| do_not_mark_claims_as_verified | PASS | claims=0, none carries status='verified' |
| report_id_scoped | PASS | single report_id=13547 (no other report is read or written) |
| manifest_hash_matches_envelope | PASS | recomputed=4af934893732bf713346bca16c467d3f7445160bf3a480c6773a4d6404e8df93 envelope=4af934893732bf713346bca16c467d3f7445160bf3a480c6773a4d6404e8df93 |
| git_evidence_probe_reproducible | PASS | re-ran git cat-file on 2 refs (+1 range probes); drift=[] |

（本表引自**第一遍**自检；`publish` / `readme` 之后流程会再跑一遍 fixpoint 复算，
因此 `verification.json` 可能比本表多一条 `publication_ledger_consistent`——**以 `verification.json` 为最终口径**。）

## 复现

```bash
python3 scripts/kf/kf01_register.py --preset wp-13547-01 build result verify figure report   # 一键复跑（全流程）
```

repro_cmd: `python3 scripts/kf/kf01_register.py --preset wp-13547-01 build result verify figure report`

## 结果信封（唯一 json 代码块，原样提交）

```json
{
  "package_id": "wp-13547-01",
  "task_type": "01-asset-registration",
  "report_id": "13547",
  "provenance": {
    "source_uri": "tensor://reports/13547",
    "source_field": "markdown",
    "source_hash": "sha256:2debab25c7d7bd29e00f59d43ced87eac163b12af701d9a9ad81cb4440579d42",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 6168,
    "source_bytes_utf8": 8782,
    "fetched_via": "GET /api/v1/tensor/reports/13547",
    "generator": "scripts/kf/kf01_register.py",
    "contract_version": "1.0",
    "emitted_at": "2026-11-14T15:28:44.906231+00:00"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-13547-01/asset_manifest.json",
      "sha256": "4af934893732bf713346bca16c467d3f7445160bf3a480c6773a4d6404e8df93",
      "bytes": 66600,
      "asset_count": 22,
      "claims": 0
    }
  },
  "claims": []
}
```
