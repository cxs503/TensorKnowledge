# KF-RESULT wp-1204-01

**工序**：`01-asset-registration`（登记源资产，不做抽取、不做验证）
**报告**：report_id=`1204` · 《EX1-P1 KCS 阻力盲预测 prereg v1（Holtrop–Mennen 1984 公式链 + append-only MD5 锚定）》 · scenario=`ex1_kcs_prereg` · mission_id=`1626` · status=`published`
**源字节哈希**：`sha256:437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef`（5853 字符 / 9016 字节 UTF-8，与契约声明逐字节一致）
**产出**：`artifacts/wp-1204-01/asset_manifest.json`（15 项资产：resolved 1 / metadata_only 4 / unresolved 10）

## ① 本工序做了什么

对 report 1204 做**资产登记**，只回答三件事：这份报告的源字节是什么、它声明了哪些可解析的附件/工件、这些工件在本包范围内解析到什么程度。

- 拉取 `GET /api/v1/tensor/reports/1204` 的 `markdown` 字段，按 UTF-8 编码重算 SHA-256 → `sha256:437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef`，与契约 `source_hash` 比对**相等**后才允许继续（不等即 `FATAL` 退出，不生成任何清单）。
- 登记 15 项资产：源 markdown 1 项（REAL，字节到手）、记录 `figures[]` 的 4 张图（metadata_only：记录只存 name+caption，无 png_base64 载荷，故**不给哈希**）、报告正文引用的 6 个代码/数据文件路径、2 个外部对象（函数 `calculate_holtrop_full`、端点 `/api/v1/resistance/predict`）、正文自带的 2 个 MD5 锚（prereg 正文 / 文件）。
- 每项都带**可解析定位符**：正文引用一律用「逐字子串」定位（生成器强制 `quote in markdown`，否则立即失败），记录字段一律用 `field[/index]` 定位。
- **不做的事**（写进清单 `explicit_non_actions`）：不抽取 claim（`claims=[]`，契约允许）、不验证任何技术结论、不重算报告自带的 MD5 锚、不下载/渲染图。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **活取 + 硬哈希闸门**：`scripts/kf/build_asset_manifest_wp1204_01.py` 先 `POST /auth/login` 取 token，再 `GET /tensor/reports/1204`；`hashlib.sha256(markdown.encode('utf-8'))` 与契约常量比对，不等直接 `SystemExit`（不存在"哈希对不上但还是先出清单"的路径）。
2. **定位符先验证再落盘**：所有 `text_quote` 资产在写入前断言 `quote in markdown`。第一次运行就**抓住一处我的臆断**：契约/正文里我以为路径是 `docs/prereg/ex1_kcs/run_prereg.py`，实际正文只写了裸文件名 `run_prereg.py`（全路径靠上下文推断）→ 改为「短引文逐字 + `path_derivation_note` 标注推断来源 + `path_is_verbatim=false`」，不把推断包装成引文。
3. **解析状态三值化**：`resolved`（字节到手并哈希）/ `metadata_only`（平台只存元数据）/ `unresolved`（目标在本包范围外，含原因字符串）。生成器对本工作树实际 `os.path.isfile` 探测引用路径——6 个引用路径在 TensorKnowledge 检出里**全部不存在**，因此全部 `unresolved`，一个都不"顺手算解决"。
4. **跨仓只读旁证（不升级为 resolved）**：另存在一份独立检出 `/root/ship-performance-platform-incoming/ship-performance-platform`，其中同名文件确实存在；生成器只读记录其 `sha256/size/commit`，并写死 `used_to_resolve=false` + 免责声明（该检出分支/commit 未被证明就是 1204 生成时的那份）。测试 `test_unresolved_assets_state_a_reason_and_are_not_overclaimed` 断言这一条不可被悄悄改成 resolved。
5. **自检 = 从原始字节重算**：`scripts/kf/validate_kf_result.py` 不信任本地快照，**重新调 API** 再算一次哈希、再验 15 个定位符、再用 `schemas/kf_result.v1.schema.json` 做 jsonschema 校验，产出 `artifacts/wp-1204-01/self_check.json`（`all_pass=True`）。
6. **离线不变量测试**：`tests/test_kf_wp1204_01.py` 10 条，断言的是**不变量**（哈希恒等、定位符逐字、字段/索引可达、id 唯一、计数自洽、锚点未标 confirmed、claims 策略），不是"跑一遍不报错"。

repro_cmd（一键复跑；工作树根为仓库检出）：

```bash
cd "$(git rev-parse --show-toplevel)" && \
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 TENSOR_AGENT_USER=$TENSOR_AGENT_USER TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS && \
python3 scripts/kf/build_asset_manifest_wp1204_01.py && \
python3 scripts/kf/fig_asset_inventory_wp1204_01.py && \
python3 scripts/kf/validate_kf_result.py && \
python3 -m pytest tests/test_kf_wp1204_01.py -q && \
python3 scripts/kf/render_report_wp1204_01.py
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-1204-01/asset_manifest.json` | 本工序主交付：15 项资产、每项定位符+解析状态+原因；`provenance.source_hash=sha256:437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef`；含 `structure_index`（6 个标题的行号，供下游工序做定位脚手架，不含内容抽取） |
| `artifacts/wp-1204-01/kf_result.json` | 结果信封（`package_id/task_type/report_id/provenance/outputs/claims`），`outputs["asset_manifest.json"]` 与上表清单对象**深度相等** |
| `artifacts/wp-1204-01/self_check.json` | 自检结果，逐条对应契约 acceptance，`all_pass=True` |
| `artifacts/wp-1204-01/fig_asset_inventory.png`（同图 `docs/kf/wp-1204-01/`） | 资产按 kind×解析状态的分布图，数字全部由清单读出作图 |
| `runs/wp-1204-01/source_1204.md` | 源字节快照（5853 字符），供离线测试复算哈希 |
| `scripts/kf/build_asset_manifest_wp1204_01.py` · `validate_kf_result.py` · `fig_asset_inventory_wp1204_01.py` · `tests/test_kf_wp1204_01.py` | 生成器 / 自检 / 作图 / 不变量测试 |
| `schemas/kf_result.v1.schema.json` | 契约引用的信封 schema；本仓原先缺此文件，按契约路径补齐（与生态内其他工作树副本 md5 一致：`0491bc4ce09a1fc2f62f015666d38935`） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

清单里每条资产的定位符即下表的「原文定位」；全部经 `quote in markdown` 逐字校验（15/15 通过，见 self_check `source_locator_resolvable`）。

| asset_id | kind | 解析等级 | 原文定位 |
|---|---|---|---|
| `r1204:source` | report_markdown | REAL(字节到手并哈希) | 记录字段 markdown（整篇） |
| `r1204:figure:01` | embedded_figure | WITHHELD(记录无字节载荷) | 记录字段 figures[0] |
| `r1204:figure:02` | embedded_figure | WITHHELD(记录无字节载荷) | 记录字段 figures[1] |
| `r1204:figure:03` | embedded_figure | WITHHELD(记录无字节载荷) | 记录字段 figures[2] |
| `r1204:figure:04` | embedded_figure | WITHHELD(记录无字节载荷) | 记录字段 figures[3] |
| `r1204:ref:docs-prereg-ex1-kcs-test-prereg-py` | referenced_repo_artifact | WITHHELD(目标在本包范围外) | markdown 子串 `docs/prereg/ex1_kcs/test_prereg.py` |
| `r1204:ref:docs-prereg-ex1-kcs-holtrop-mennen-py` | referenced_repo_artifact | WITHHELD(目标在本包范围外) | markdown 子串 `docs/prereg/ex1_kcs/holtrop_mennen.py` |
| `r1204:ref:docs-prereg-ex1-kcs-run-prereg-py` | referenced_repo_artifact | WITHHELD(目标在本包范围外) | markdown 子串 `run_prereg.py` |
| `r1204:ref:docs-prereg-ex1-kcs-audit-platform-chain-py` | referenced_repo_artifact | WITHHELD(目标在本包范围外) | markdown 子串 `audit_platform_chain.py` |
| `r1204:ref:backend-data-standard-models-detailed-py` | referenced_repo_artifact | WITHHELD(目标在本包范围外) | markdown 子串 `backend/data/standard_models_detailed.py` |
| `r1204:ref:backend-api-resistance-advanced-py` | referenced_repo_artifact | WITHHELD(目标在本包范围外) | markdown 子串 `backend/api/resistance_advanced.py` |
| `r1204:ext:calculate-holtrop-full` | external_dependency | WITHHELD(目标在本包范围外) | markdown 子串 `calculate_holtrop_full` |
| `r1204:ext:api-v1-resistance-predict` | external_dependency | WITHHELD(目标在本包范围外) | markdown 子串 `/api/v1/resistance/predict` |
| `r1204:anchor:md5:44a19245` | declared_hash_anchor | WITHHELD(目标在本包范围外) | markdown 子串 `44a19245db893f5eb56fa7e54fc53931` |
| `r1204:anchor:md5:885b2c07` | declared_hash_anchor | WITHHELD(目标在本包范围外) | markdown 子串 `885b2c07805a413df281d23743e64856` |

补充：源资产 `r1204:source` 的定位是整篇 `markdown` 字段，绑定哈希 `sha256:437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef`；报告标题/场景/mission_id 均取自同一条 API 记录（`fetched_via: GET /api/v1/tensor/reports/1204`），非记忆重述。

## ⑤ 注意点与局限

1. **4 张图无字节载荷**：记录 `figures[]` 只有 `name`+`caption`，没有 `png_base64`，所以 `sha256=null`——这是"平台没存"而不是"我没算"，下游若需图必须回到生成侧，不能拿本清单当图证据。
2. **两个 MD5 锚标为 declared / 未重算**：正文声明 prereg 正文 MD5 `44a19245db893f5eb56fa7e54fc53931`、文件 MD5 `885b2c07805a413df281d23743e64856`，但被覆盖的字节不在 report 1204 的 markdown 里，本包**无法重算**，故 `recomputed=false`、`status=unresolved`。**风险**：下游工序若把这两个值当"已验证"就是越权；测试已锁死这一条。
3. **推断路径与引文分离**：`run_prereg.py` / `audit_platform_chain.py` 正文只给裸文件名，目录靠上下文推断；清单里 `path_is_verbatim=false` 且带 `path_derivation_note`，不允许"推断当引文"。
4. **6 个引用工件在本仓缺席**：`docs/prereg/ex1_kcs/*`、`backend/{data,api}/*.py` 在 TensorKnowledge 检出中不存在（属 ship-performance-platform 域），清单如实记 `unresolved` + 原因；另存的独立检出里同名文件存在，但分支/commit 未证同一，只作只读旁证（`used_to_resolve=false`），**不**拿来充当解析结论。
5. **独立第二读路缺失（诚实记录）**：我尝试用 `psql -d tensorplatform -c "select markdown from tensor_reports where id=1204"` 做与 API 的二次交叉验证，返回 `ERROR: permission denied for table tensor_reports`，因此源哈希只有 **API 单一路径**证据；这属于本单的独立性局限，未粉饰。
6. **资产召回率未被机器证明**：资产清单由我通读 5853 字符正文后**人工列条目**、再由生成器机器校验定位符；未做正则/链接图扫描（易产生假阳性）。因此"是否漏掉某处引用"没有机器保证——这是覆盖范围的已知边界，不是已验证的完整性结论。
7. **不做类型判定**：契约 `classify_report_type: false`，本单未对报告做 scenario 归类判断（scenario_key 只是原样转录记录字段）。
8. **自审（adversarial review，自我挑战，非独立评审）**：严重度排序——(a) **阻断级（已消解）**：若清单把 declared MD5 锚或外部同名副本写成 resolved，将污染下游"验证"语义，已用 `recomputed=false/used_to_resolve=false` + 两条测试锁死；(b) **高**：图资产无载荷易被误用，已在 `resolution.reason` 与⑤-1 双处显式声明；(c) **中**：schema 文件为本单补入，若生态内版本漂移会导致结构门假绿，已记录 md5 并在此声明来源；(d) **低**：`structure_index` 仅标题行号，不含内容，避免与工序 03 抢边界。**处置：approve with notes**，但按纪律本单 `review.required=false`，我的自审**不构成**独立评审。

## ⑥ 自检：逐条对照 acceptance

| acceptance 判据 | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | both kf_result.json and asset_manifest.json parse via json.loads |
| schema_pass | ✅ | jsonschema schemas/kf_result.v1.schema.json OK (envelope); missing_top=[] missing_provenance=[] declared_output_asset_manifest.json=True |
| source_hash_matches | ✅ | source=live GET /api/v1/tensor/reports/1204; recomputed=437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef envelope=437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef manifest=437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef contract=437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef chars=5853 bytes=9016 |
| source_locator_resolvable | ✅ | checked 15 locators against live GET /api/v1/tensor/reports/1204; problems=[] |
| no_duplicate_ids | ✅ | assets=15 unique=15; claims=0 unique=0 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=0 violating=[] (empty array: vacuously satisfied per contract 'claims 允许为空数组') |
| do_not_mark_claims_as_verified | ✅ | claims carrying status='verified': [] |
| report_scope | ✅ | envelope report_id=1204 manifest report_id=1204 (single-report scope, nothing else read or written) |
| envelope_matches_manifest | ✅ | outputs['asset_manifest.json'] deep-equals asset_manifest.json on disk |
| manifest_self_hash | ✅ | sha256(asset_manifest.json bytes) = 28045e526d60e0c6f2f9b37afe9b50efc3fbe6238a911827d0fe5bf68fdd93f2 (recorded for provenance) |
| unresolved_assets_explain_themselves | ✅ | every non-resolved asset carries an explicit reason string |

复跑命令见②；`self_check.json` 由 `python3 scripts/kf/validate_kf_result.py` 从**活取字节**重算生成（`source_mode: live GET /api/v1/tensor/reports/1204`），非本地快照自证。pytest：`10 passed`。若有失败项会如实标 ❌——本单无失败项、亦无"已 verified"声明（verification 由平台门计算）。

```json
{
  "package_id": "wp-1204-01",
  "task_type": "01-asset-registration",
  "report_id": "1204",
  "provenance": {
    "source_uri": "tensor://reports/1204",
    "source_field": "markdown",
    "source_hash": "sha256:437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef",
    "producer": "kf-worker:wp-1204-01",
    "emitted_at": "2026-11-12T00:55:45.285018+00:00",
    "notes": "01-asset-registration only: source bytes hashed live, figure metadata indexed, quoted references probed against the TensorKnowledge worktree. No extraction, no verification, claims intentionally empty. contract_expected_hash=437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-1204-01",
      "task_type": "01-asset-registration",
      "report_id": "1204",
      "objective": {
        "register_assets": true,
        "classify_report_type": false
      },
      "generated_at": "2026-11-12T00:55:45.284775+00:00",
      "provenance": {
        "source_uri": "tensor://reports/1204",
        "source_field": "markdown",
        "source_hash": "sha256:437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef",
        "hash_algo": "sha256",
        "hashed_bytes": "markdown encoded as utf-8",
        "source_chars": 5853,
        "source_bytes_utf8": 9016,
        "report_title": "EX1-P1 KCS 阻力盲预测 prereg v1（Holtrop–Mennen 1984 公式链 + append-only MD5 锚定）",
        "report_scenario_key": "ex1_kcs_prereg",
        "report_mission_id": 1626,
        "report_status": "published",
        "report_created_at": "2026-11-01T09:15:59.420762+00:00",
        "report_created_by": 1,
        "report_tags": [
          "EX-1",
          "KCS",
          "blind-prediction",
          "prereg",
          "holtrop-mennen",
          "resistance",
          "audit"
        ],
        "fetched_via": "GET /api/v1/tensor/reports/1204",
        "generator": "scripts/kf/build_asset_manifest_wp1204_01.py",
        "contract_version": "1.0",
        "contract_expected_hash": "437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef"
      },
      "resolution_status_vocabulary": {
        "resolved": "bytes located and hashed (source markdown or a file inside this worktree)",
        "unresolved": "reference parsed from the report but the target is outside this package's scope",
        "metadata_only": "platform lists the asset but stores no byte payload, so no hash is claimable"
      },
      "structure_index": {
        "note": "headings only, offsets are character positions into the markdown string — provided as locator scaffolding for downstream 工序, no content is extracted here",
        "headings": [
          {
            "level": 1,
            "text": "EX1-P1 KCS 阻力盲预测 prereg（水池锚定 · 公信力底线）",
            "line_no": 1
          },
          {
            "level": 2,
            "text": "① 案例介绍",
            "line_no": 5
          },
          {
            "level": 2,
            "text": "② 怎么做的",
            "line_no": 20
          },
          {
            "level": 2,
            "text": "③ 计算结果（prereg v1 名义链，实船裸船体）",
            "line_no": 28
          },
          {
            "level": 2,
            "text": "④ 结果图",
            "line_no": 60
          },
          {
            "level": 2,
            "text": "⑤ 注意点（踩过的坑与局限）",
            "line_no": 64
          },
          {
            "level": 2,
            "text": "⑥ 误差判定（关键量 vs 基准，是否 <3%）",
            "line_no": 73
          }
        ]
      },
      "assets": [
        {
          "asset_id": "r1204:source",
          "kind": "report_markdown",
          "uri": "tensor://reports/1204",
          "source_field": "markdown",
          "title": "EX1-P1 KCS 阻力盲预测 prereg v1（Holtrop–Mennen 1984 公式链 + append-only MD5 锚定）",
          "chars": 5853,
          "bytes_utf8": 9016,
          "sha256": "437b758c609448aa2141812afb6f27f323b30f83e08399f4befdb53e397ea2ef",
          "locator": {
            "scheme": "report_field",
            "field": "markdown"
          },
          "resolution": {
            "status": "resolved",
            "scope": "platform_api",
            "via": "GET /tensor/reports/1204"
          }
        },
        {
          "asset_id": "r1204:figure:01",
          "kind": "embedded_figure",
          "uri": "tensor://reports/1204#figures[0]",
          "name": "fig1_Rt_Pe_vs_Fn.png",
          "caption": "图1 KCS 实船裸船体总阻力 Rt(Fn) 名义 Holtrop–Mennen 1984 曲线与公式间总包络（左），有效功率 Pe（右）。",
          "bytes": null,
          "sha256": null,
          "locator": {
            "scheme": "report_field",
            "field": "figures",
            "index": 0
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "has_payload": false,
            "reason": "report record lists this figure by name+caption only; no png_base64 payload is stored in figures[], so no byte hash can be computed"
          }
        },
        {
          "asset_id": "r1204:figure:02",
          "kind": "embedded_figure",
          "uri": "tensor://reports/1204#figures[1]",
          "name": "fig2_coefficients_vs_Fn.png",
          "caption": "图2 阻力系数 CF/CR/Ct（左）、形状因子 1+k（中）、无量纲兴波阻力 Rw/(ρg∇)（右）随 Fn 变化。",
          "bytes": null,
          "sha256": null,
          "locator": {
            "scheme": "report_field",
            "field": "figures",
            "index": 1
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "has_payload": false,
            "reason": "report record lists this figure by name+caption only; no png_base64 payload is stored in figures[], so no byte hash can be computed"
          }
        },
        {
          "asset_id": "r1204:figure:03",
          "kind": "embedded_figure",
          "uri": "tensor://reports/1204#figures[2]",
          "name": "fig3_breakdown_frictionlaws.png",
          "caption": "图3 阻力成分分解 RF(1+k)/Rw/RA（左）与三条摩擦线（ITTC-57/Schoenherr/Prandtl–Schlichting）下 Rt 的散布（右）。",
          "bytes": null,
          "sha256": null,
          "locator": {
            "scheme": "report_field",
            "field": "figures",
            "index": 2
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "has_payload": false,
            "reason": "report record lists this figure by name+caption only; no png_base64 payload is stored in figures[], so no byte hash can be computed"
          }
        },
        {
          "asset_id": "r1204:figure:04",
          "kind": "embedded_figure",
          "uri": "tensor://reports/1204#figures[3]",
          "name": "fig_platform_vs_prereg.png",
          "caption": "图4 审计：prereg 公式链 vs 平台 /resistance/predict（内置标称「Holtrop」）的 Rt 对比（左）与兴波阻力占比物理合理性检查（右）。",
          "bytes": null,
          "sha256": null,
          "locator": {
            "scheme": "report_field",
            "field": "figures",
            "index": 3
          },
          "resolution": {
            "status": "metadata_only",
            "scope": "platform_api",
            "has_payload": false,
            "reason": "report record lists this figure by name+caption only; no png_base64 payload is stored in figures[], so no byte hash can be computed"
          }
        },
        {
          "asset_id": "r1204:ref:docs-prereg-ex1-kcs-test-prereg-py",
          "kind": "referenced_repo_artifact",
          "role_in_report": "pytest_judgement_suite",
          "declared_path": "docs/prereg/ex1_kcs/test_prereg.py",
          "path_is_verbatim": true,
          "uri": "tensor://reports/1204#docs/prereg/ex1_kcs/test_prereg.py",
          "locator": {
            "scheme": "text_quote",
            "quote": "docs/prereg/ex1_kcs/test_prereg.py",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "worktree",
            "checked_path": "docs/prereg/ex1_kcs/test_prereg.py",
            "present_in_this_worktree": false,
            "reason": "path is quoted in the report but does not exist in the TensorKnowledge checkout used for this package; the reference stays unresolved here (no content claim is made); a same-named file exists in a separate ship-performance-platform checkout (see external_copy_observed) but that checkout's branch/commit is unverified, so it is recorded as an observation, not as a resolution"
          },
          "external_copy_observed": {
            "path": "/root/ship-performance-platform-incoming/ship-performance-platform/docs/prereg/ex1_kcs/test_prereg.py",
            "repo_root": "/root/ship-performance-platform-incoming/ship-performance-platform",
            "commit": "3ab633eff",
            "branch": "master",
            "bytes": 8696,
            "sha256": "caf6fd14bdb756a6b3594be7f591601ef3865264de3c71407d958d656e5dab95",
            "used_to_resolve": false,
            "caveat": "read-only observation in a foreign checkout; branch/commit is not proven to be the one report 1204 was generated from, so this does NOT resolve the reference and no content claim is made"
          }
        },
        {
          "asset_id": "r1204:ref:docs-prereg-ex1-kcs-holtrop-mennen-py",
          "kind": "referenced_repo_artifact",
          "role_in_report": "formula_chain_implementation",
          "declared_path": "docs/prereg/ex1_kcs/holtrop_mennen.py",
          "path_is_verbatim": true,
          "uri": "tensor://reports/1204#docs/prereg/ex1_kcs/holtrop_mennen.py",
          "locator": {
            "scheme": "text_quote",
            "quote": "docs/prereg/ex1_kcs/holtrop_mennen.py",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "worktree",
            "checked_path": "docs/prereg/ex1_kcs/holtrop_mennen.py",
            "present_in_this_worktree": false,
            "reason": "path is quoted in the report but does not exist in the TensorKnowledge checkout used for this package; the reference stays unresolved here (no content claim is made); a same-named file exists in a separate ship-performance-platform checkout (see external_copy_observed) but that checkout's branch/commit is unverified, so it is recorded as an observation, not as a resolution"
          },
          "external_copy_observed": {
            "path": "/root/ship-performance-platform-incoming/ship-performance-platform/docs/prereg/ex1_kcs/holtrop_mennen.py",
            "repo_root": "/root/ship-performance-platform-incoming/ship-performance-platform",
            "commit": "3ab633eff",
            "branch": "master",
            "bytes": 12962,
            "sha256": "dc2a89fe6347b9e8b67a24e8e693e72fc7169f48b402e2631574a97d9a014ce8",
            "used_to_resolve": false,
            "caveat": "read-only observation in a foreign checkout; branch/commit is not proven to be the one report 1204 was generated from, so this does NOT resolve the reference and no content claim is made"
          }
        },
        {
          "asset_id": "r1204:ref:docs-prereg-ex1-kcs-run-prereg-py",
          "kind": "referenced_repo_artifact",
          "role_in_report": "prereg_generator",
          "declared_path": "docs/prereg/ex1_kcs/run_prereg.py",
          "path_is_verbatim": false,
          "uri": "tensor://reports/1204#docs/prereg/ex1_kcs/run_prereg.py",
          "locator": {
            "scheme": "text_quote",
            "quote": "run_prereg.py",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "worktree",
            "checked_path": "docs/prereg/ex1_kcs/run_prereg.py",
            "present_in_this_worktree": false,
            "reason": "path is quoted in the report but does not exist in the TensorKnowledge checkout used for this package; the reference stays unresolved here (no content claim is made); a same-named file exists in a separate ship-performance-platform checkout (see external_copy_observed) but that checkout's branch/commit is unverified, so it is recorded as an observation, not as a resolution"
          },
          "path_derivation_note": "bare filename in the report; directory inferred from the same step's sibling paths (docs/prereg/ex1_kcs/), not verbatim",
          "external_copy_observed": {
            "path": "/root/ship-performance-platform-incoming/ship-performance-platform/docs/prereg/ex1_kcs/run_prereg.py",
            "repo_root": "/root/ship-performance-platform-incoming/ship-performance-platform",
            "commit": "3ab633eff",
            "branch": "master",
            "bytes": 24368,
            "sha256": "916b29455b2aaa571213c6f71547677b74912c5933a710425050aaa0b1438ea5",
            "used_to_resolve": false,
            "caveat": "read-only observation in a foreign checkout; branch/commit is not proven to be the one report 1204 was generated from, so this does NOT resolve the reference and no content claim is made"
          }
        },
        {
          "asset_id": "r1204:ref:docs-prereg-ex1-kcs-audit-platform-chain-py",
          "kind": "referenced_repo_artifact",
          "role_in_report": "platform_chain_audit_script",
          "declared_path": "docs/prereg/ex1_kcs/audit_platform_chain.py",
          "path_is_verbatim": false,
          "uri": "tensor://reports/1204#docs/prereg/ex1_kcs/audit_platform_chain.py",
          "locator": {
            "scheme": "text_quote",
            "quote": "audit_platform_chain.py",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "worktree",
            "checked_path": "docs/prereg/ex1_kcs/audit_platform_chain.py",
            "present_in_this_worktree": false,
            "reason": "path is quoted in the report but does not exist in the TensorKnowledge checkout used for this package; the reference stays unresolved here (no content claim is made); a same-named file exists in a separate ship-performance-platform checkout (see external_copy_observed) but that checkout's branch/commit is unverified, so it is recorded as an observation, not as a resolution"
          },
          "path_derivation_note": "bare filename in the report; directory inferred from the same step's sibling paths (docs/prereg/ex1_kcs/), not verbatim",
          "external_copy_observed": {
            "path": "/root/ship-performance-platform-incoming/ship-performance-platform/docs/prereg/ex1_kcs/audit_platform_chain.py",
            "repo_root": "/root/ship-performance-platform-incoming/ship-performance-platform",
            "commit": "3ab633eff",
            "branch": "master",
            "bytes": 4185,
            "sha256": "4be881b220fb49411eb32b712da5a084c196665b91583ae8106de165944174fc",
            "used_to_resolve": false,
            "caveat": "read-only observation in a foreign checkout; branch/commit is not proven to be the one report 1204 was generated from, so this does NOT resolve the reference and no content claim is made"
          }
        },
        {
          "asset_id": "r1204:ref:backend-data-standard-models-detailed-py",
          "kind": "referenced_repo_artifact",
          "role_in_report": "input_parameter_source",
          "declared_path": "backend/data/standard_models_detailed.py",
          "path_is_verbatim": true,
          "uri": "tensor://reports/1204#backend/data/standard_models_detailed.py",
          "locator": {
            "scheme": "text_quote",
            "quote": "backend/data/standard_models_detailed.py",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "worktree",
            "checked_path": "backend/data/standard_models_detailed.py",
            "present_in_this_worktree": false,
            "reason": "path is quoted in the report but does not exist in the TensorKnowledge checkout used for this package; the reference stays unresolved here (no content claim is made); a same-named file exists in a separate ship-performance-platform checkout (see external_copy_observed) but that checkout's branch/commit is unverified, so it is recorded as an observation, not as a resolution"
          },
          "external_copy_observed": {
            "path": "/root/ship-performance-platform-incoming/ship-performance-platform/backend/data/standard_models_detailed.py",
            "repo_root": "/root/ship-performance-platform-incoming/ship-performance-platform",
            "commit": "3ab633eff",
            "branch": "master",
            "bytes": 33223,
            "sha256": "b298ae590a61dfd5df7f747477f06911c690ae97238178fab83695d5ff118b1c",
            "used_to_resolve": false,
            "caveat": "read-only observation in a foreign checkout; branch/commit is not proven to be the one report 1204 was generated from, so this does NOT resolve the reference and no content claim is made"
          }
        },
        {
          "asset_id": "r1204:ref:backend-api-resistance-advanced-py",
          "kind": "referenced_repo_artifact",
          "role_in_report": "platform_resistance_module",
          "declared_path": "backend/api/resistance_advanced.py",
          "path_is_verbatim": true,
          "uri": "tensor://reports/1204#backend/api/resistance_advanced.py",
          "locator": {
            "scheme": "text_quote",
            "quote": "backend/api/resistance_advanced.py",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "worktree",
            "checked_path": "backend/api/resistance_advanced.py",
            "present_in_this_worktree": false,
            "reason": "path is quoted in the report but does not exist in the TensorKnowledge checkout used for this package; the reference stays unresolved here (no content claim is made); a same-named file exists in a separate ship-performance-platform checkout (see external_copy_observed) but that checkout's branch/commit is unverified, so it is recorded as an observation, not as a resolution"
          },
          "external_copy_observed": {
            "path": "/root/ship-performance-platform-incoming/ship-performance-platform/backend/api/resistance_advanced.py",
            "repo_root": "/root/ship-performance-platform-incoming/ship-performance-platform",
            "commit": "3ab633eff",
            "branch": "master",
            "bytes": 18232,
            "sha256": "7c2b4bbe1f542bc3d0be3cd4d773df616fa3939df970d23e68840b3e1a9d7f74",
            "used_to_resolve": false,
            "caveat": "read-only observation in a foreign checkout; branch/commit is not proven to be the one report 1204 was generated from, so this does NOT resolve the reference and no content claim is made"
          }
        },
        {
          "asset_id": "r1204:ext:calculate-holtrop-full",
          "kind": "external_dependency",
          "dependency_kind": "function",
          "name": "calculate_holtrop_full",
          "locator": {
            "scheme": "text_quote",
            "quote": "calculate_holtrop_full",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "out_of_package",
            "reason": "named in the report as an object to be audited/used; this package only registers the reference — the service/function was not called or inspected, so its behaviour is neither confirmed nor refuted here"
          }
        },
        {
          "asset_id": "r1204:ext:api-v1-resistance-predict",
          "kind": "external_dependency",
          "dependency_kind": "http_endpoint",
          "name": "/api/v1/resistance/predict",
          "locator": {
            "scheme": "text_quote",
            "quote": "/api/v1/resistance/predict",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "out_of_package",
            "reason": "named in the report as an object to be audited/used; this package only registers the reference — the service/function was not called or inspected, so its behaviour is neither confirmed nor refuted here"
          }
        },
        {
          "asset_id": "r1204:anchor:md5:44a19245",
          "kind": "declared_hash_anchor",
          "algorithm": "md5",
          "value": "44a19245db893f5eb56fa7e54fc53931",
          "declared_for": "prereg_body_bytes",
          "locator": {
            "scheme": "text_quote",
            "quote": "44a19245db893f5eb56fa7e54fc53931",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "out_of_package",
            "recomputed": false,
            "reason": "anchor is *declared inside the report*; the bytes it covers (prereg body/file) are not part of report 1204's markdown, so this package cannot recompute it — registered as declared, not as confirmed"
          }
        },
        {
          "asset_id": "r1204:anchor:md5:885b2c07",
          "kind": "declared_hash_anchor",
          "algorithm": "md5",
          "value": "885b2c07805a413df281d23743e64856",
          "declared_for": "prereg_file",
          "locator": {
            "scheme": "text_quote",
            "quote": "885b2c07805a413df281d23743e64856",
            "source_field": "markdown"
          },
          "resolution": {
            "status": "unresolved",
            "scope": "out_of_package",
            "recomputed": false,
            "reason": "anchor is *declared inside the report*; the bytes it covers (prereg body/file) are not part of report 1204's markdown, so this package cannot recompute it — registered as declared, not as confirmed"
          }
        }
      ],
      "counts": {
        "assets_total": 15,
        "resolved": 1,
        "unresolved": 10,
        "metadata_only": 4
      },
      "explicit_non_actions": [
        "no claim extracted (claims=[] by contract: register_assets only, no forced claim generation)",
        "no technical statement of the report was verified or refuted; the platform gate computes verification",
        "declared MD5 anchors were not recomputed (covered bytes are out of scope)",
        "figures were not downloaded or rendered (no byte payload in the record)"
      ]
    }
  },
  "claims": []
}
```
