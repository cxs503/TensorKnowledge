# KF-RESULT wp-7545-01 — 报告 7545 源资产登记（01-asset-registration）

> 工序=01-asset-registration ｜ lane=C ｜ 输入 `tensor://reports/7545` 字段 `markdown` ｜
> 源字节 sha256 = `84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60`（3583 字符 / 6333 字节 UTF-8）｜
> 契约声明哈希 = `sha256:84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60` ｜ 一致：True

## ① 本工序做了什么

严格按契约只做登记：确认真实报告 7545 的 markdown 字节哈希与契约 `source_hash` 一致，
把这一个报告里**可逐字定位的资产**（正文本身 + 平台 figures 元数据 + 正文引用的附件/工件/代码/命令）
登记成 `asset_manifest.json`，并为每个资产绑一个**字符级定位器**（start/end char + line + 逐字 quote + 唯一性）。

不做的事（契约硬约束，一条都没越界）：不做文本抽取、不生成知识 claim（`claims: []`，0 条）、
不把任何结论标 `verified`、不改写上游/其它工作包产物、不读不写其它 `report_id`。
登记结果：**18 个资产**，其中 `resolved_in_source` 1 个、
`referenced_unresolved` 13 个、`declared_absent` 4 个。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/7545`（Bearer token 来自 `POST /api/v1/auth/login`），
   取 `markdown` 字段原样落地，**不在本地重排/规范化**——哈希必须对原始字节计算。
2. **哈希门**：`sha256(markdown.encode('utf-8'))` = `84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60`，与契约 `source_hash` 逐字符比对；
   不一致直接 `SystemExit`，不写任何产物（先门后写）。
3. **资产发现**（只做正则扫描，不做语义抽取）：
   - 正文本身 → 1 个 `report_markdown`，定位器 `method=document`（0..3583）；
   - 反引号文件引用 → `data_artifact_reference` / `source_code_reference`，带 `:pin` 锚点（如 `experiments.json:spec`）；
   - 反引号目录引用 → `directory_reference`；反引号 shell 命令 → `test_command_reference`（只登记文本，不执行）；
   - 平台 `figures` 元数据 4 条 → `embedded_figure`，名称/图注照抄，并对每个
     `GET /api/v1/tensor/reports/7545/figures/<name>` 做**字节探测**。
4. **定位器构造**：`start = md.find(quote)`、`end = start + len(quote)`、行号 = 前缀换行计数 + 1；
   `unique = md.count(quote) == 1`。quote 一律用 `md[...]` 切片得到，**不手打**（结构性防手抄）。
5. **解析判定**（worktree + git index 双查）：命中本检出 → `resolved_in_source`；不在本检出 → `referenced_unresolved`（不跨仓猜）。
6. **自检**：`verify` 子命令**重新登录、重新取报告**，独立重算哈希、逐个切片复验 quote、跑两份 JSON Schema。

关键设置：`EXPECTED_HASH=84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60`、`EXPECTED_CHARS=3583`
（写成常量做一次性断言，防止"顺手"换源）；schema 校验用 `schemas/asset_manifest.v1.schema.json`，其 `package_id/report_id/uri`
三个 `const` 在内存中重绑定到本包（该文件原本 `const` 到 wp-448-01），`schemas/kf_result.v1.schema.json` 原样使用。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-7545-01/asset_manifest.json` | 18 个资产，sha256=`82bb6145f8a9f5ff…`（20697 B），claims=0 |
| `docs/kf/wp-7545-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims），过 `kf_result.v1` schema |
| `docs/kf/wp-7545-01/verification.json` | 独立自检回执，7 项检查逐条 pass |
| `docs/kf/wp-7545-01/fig1_asset_inventory.png` | 资产分类与解析状态柱状图（数据由 manifest 注入） |
| `docs/kf/wp-7545-01/REPORT.md` | 本报告 |
| `scripts/kf/build_asset_manifest_7545.py` | 登记器 + 校验器（build/result/verify） |
| `scripts/kf/report_7545_01.py` | 出图与报告渲染/发布 |

资产分类（`counts.by_class`）：{"report_markdown": 1, "embedded_figure": 4, "data_artifact_reference": 8, "source_code_reference": 2, "directory_reference": 1, "test_command_reference": 2}
解析状态（`counts.by_resolution`）：{"resolved_in_source": 1, "declared_absent": 4, "referenced_unresolved": 13}

**资产台账**

| id | class | label | 正文节 | 行 | quote（逐字） | resolution |
|---|---|---|---|---|---|---|
| A01 | report_markdown | 报告 markdown 全文字节（source_uri 指向的主资产） | （整篇） | L1 | `# IN59-P2 冰层断裂与接触模型：五角色×七环 ABM 与理论/实现/实验三腿闭合` | resolved_in_source |
| A02 | embedded_figure | fig1_stress_strain.png | ④ 结果图 | L61 | `图 1：单轴压缩与直接拉伸的加载曲线（峰值与broken演化）` | declared_absent |
| A03 | embedded_figure | fig2_blind_cards.png | ④ 结果图 | L62 | `图 2：预测盲卡片——封存预测与实测的相对误差 vs sealed tolerance` | declared_absent |
| A04 | embedded_figure | fig3_six_dim.png | ④ 结果图 | L63 | `图 3：六维对照（实验组 vs 对照组，对数轴）` | declared_absent |
| A05 | embedded_figure | fig4_three_legs.png | ④ 结果图 | L64 | `图 4：三腿闭合误差与tolerance gate` | declared_absent |
| A06 | data_artifact_reference | experiments.json:spec | ① 案例介绍（物理背景 / 几何 / 参数表） | L9 | `'experiments.json:spec'` | referenced_unresolved |
| A07 | source_code_reference | run_abm.py:KNOWLEDGE_PACKS | ② 怎么做的（方法 / 流程 / 工具链） | L25 | `'run_abm.py:KNOWLEDGE_PACKS'` | referenced_unresolved |
| A08 | source_code_reference | dem_bpm.py | ② 怎么做的（方法 / 流程 / 工具链） | L29 | `'dem_bpm.py'` | referenced_unresolved |
| A09 | data_artifact_reference | artifacts/IN59-P2/trace.jsonl | 审计链 | L92 | `'artifacts/IN59-P2/trace.jsonl'` | referenced_unresolved |
| A10 | data_artifact_reference | artifacts/IN59-P2/blind_cards.json | 审计链 | L93 | `'artifacts/IN59-P2/blind_cards.json'` | referenced_unresolved |
| A11 | data_artifact_reference | artifacts/IN59-P2/experiments.json | 审计链 | L94 | `'artifacts/IN59-P2/experiments.json'` | referenced_unresolved |
| A12 | data_artifact_reference | six_dim_table.json | 审计链 | L94 | `'six_dim_table.json'` | referenced_unresolved |
| A13 | data_artifact_reference | three_leg.json | 审计链 | L94 | `'three_leg.json'` | referenced_unresolved |
| A14 | data_artifact_reference | acceptance.json | 审计链 | L94 | `'acceptance.json'` | referenced_unresolved |
| A15 | data_artifact_reference | control_arm.json | 审计链 | L94 | `'control_arm.json'` | referenced_unresolved |
| A16 | directory_reference | tools/abm | ② 怎么做的（方法 / 流程 / 工具链） | L27 | `'tools/abm'` | referenced_unresolved |
| A17 | test_command_reference | pytest tests/abm domains/ice_fracture_contact/tests | ② 怎么做的（方法 / 流程 / 工具链） | L33 | `'pytest tests/abm domains/ice_fracture_contact/tests'` | referenced_unresolved |
| A18 | test_command_reference | pytest tests/abm domains/ice_fracture_contact/tests -q | 审计链 | L95 | `'pytest tests/abm domains/ice_fracture_contact/tests -q'` | referenced_unresolved |

## ④ 证据定位表（资产 → 原文引文片段）

全部 18 条 quote 均满足「`md[start:end] == quote` ∧ 落在声明的行上 ∧ 全文字符串唯一」
（`integrity.quote_uniqueness.unique = 18/18`，非唯一项：[]）。
`claims` 为空数组，故本工序**没有 claim→证据**的映射表可填；下表是资产级的等价物（每个资产 = 一个可复核的"报告说过这里有这个东西"）：

| 资产 | 用途/声明位置 | quote | 行 | 唯一性 |
|---|---|---|---|---|
| A01 | report_markdown | `# IN59-P2 冰层断裂与接触模型：五角色×七环 ABM 与理论/实现/实验三腿闭合` | 1 | 唯一 |
| A02 | embedded_figure | `图 1：单轴压缩与直接拉伸的加载曲线（峰值与broken演化）` | 61 | 唯一 |
| A03 | embedded_figure | `图 2：预测盲卡片——封存预测与实测的相对误差 vs sealed tolerance` | 62 | 唯一 |
| A04 | embedded_figure | `图 3：六维对照（实验组 vs 对照组，对数轴）` | 63 | 唯一 |
| A05 | embedded_figure | `图 4：三腿闭合误差与tolerance gate` | 64 | 唯一 |
| A06 | data_artifact_reference | `'experiments.json:spec'` | 9 | 唯一 |
| A07 | source_code_reference | `'run_abm.py:KNOWLEDGE_PACKS'` | 25 | 唯一 |
| A08 | source_code_reference | `'dem_bpm.py'` | 29 | 唯一 |
| A09 | data_artifact_reference | `'artifacts/IN59-P2/trace.jsonl'` | 92 | 唯一 |
| A10 | data_artifact_reference | `'artifacts/IN59-P2/blind_cards.json'` | 93 | 唯一 |
| A11 | data_artifact_reference | `'artifacts/IN59-P2/experiments.json'` | 94 | 唯一 |
| A12 | data_artifact_reference | `'six_dim_table.json'` | 94 | 唯一 |
| A13 | data_artifact_reference | `'three_leg.json'` | 94 | 唯一 |
| A14 | data_artifact_reference | `'acceptance.json'` | 94 | 唯一 |
| A15 | data_artifact_reference | `'control_arm.json'` | 94 | 唯一 |
| A16 | directory_reference | `'tools/abm'` | 27 | 唯一 |
| A17 | test_command_reference | `'pytest tests/abm domains/ice_fracture_contact/tests'` | 33 | 唯一 |
| A18 | test_command_reference | `'pytest tests/abm domains/ice_fracture_contact/tests -q'` | 95 | 唯一 |

## ⑤ 注意点与局限

- **图注在、字节不在**：平台 `figures` 4 条元数据齐全，但 `GET .../figures/<name>` 四条全部 `404 {"detail":"figure not found"}`。
  故 ['A02', 'A03', 'A04', 'A05'] 判 `declared_absent`（`resolution_check.result=absent`），**不臆造图片哈希**，也不从别处拷贝同名图。这是登记工序应报的事实。
- **跨仓引用一律不解析**：报告引用的 `tools/abm`、`dem_bpm.py`、`run_abm.py`、`artifacts/IN59-P2/*` 等属于产生该报告的域仓/任务树，
  不在 TensorKnowledge 检出内（worktree 与 git index 双查均无），13 个资产判 `referenced_unresolved`。
  边界使然，不是缺陷：跨仓拷贝会破坏"互不覆盖"前提。
- **不执行测试命令**：正文与审计链各出现一次 `pytest ...`（A17/A18，出现级标识所以两条），本包只登记文本可定位性；
  报告声称的 `19 passed` **未在本包复核**，登记 ≠ 背书。
- **不做数值复核**：报告里的 `σ_c=2.261 MPa`、`σ_t=0.813 MPa`、`E=nan GPa`、`m_eff=nan` 等数字本包只当作"报告文本"登记，
  不判真伪、不改写、不补算；误差判定与 honest-FAIL 结论归平台门与下游工序。
- **只登记 1 份报告**：全部步骤以 `report_id=7545` 硬编码，脚本没有任何其它 report 的写入路径。
- **schema 的 const 冲突是已知事实**：`schemas/asset_manifest.v1.schema.json` 把 `package_id` 固定成 `wp-448-01`，
  本包校验在内存中重绑定 `package_id/report_id/source.uri` 三个 const（已在 `verification.json` 里写明），不改远端 schema 文件。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 证据 |
|---|---|---|
| valid_json | ✔ | `asset_manifest.json`、`kf_result.json` 均 `json.loads` 通过 |
| schema_pass | ✔ | asset_manifest.v1（const 重绑定）+ kf_result.v1 校验，errors=[] |
| source_locator_resolvable | ✔ | 重新取报告后逐个切片复验 18 个定位器，失败=[] |
| source_hash_matches | ✔ | 重算=manifest=契约=`84010e0091071d59…` |
| no_duplicate_ids | ✔ | 18 个 id 全唯一且匹配 `^A[0-9]{2}$` |
| all_claims_have_evidence_or_explicit_unresolved_status | ✔ | claims=[] ⇒ 空数组合法（契约 `no_forced_claim_generation: true`），违例 0 |
| do_not_mark_claims_as_verified | ✔ | 无任何 `status=verified`；manifest `contract.status=draft` |

**失败项：无**（7/7 pass，`verification.json: all_pass=True`）。如实声明未做的：抽取/核验/数值复核/执行测试，均在本包边界外。

## 复跑

```bash
# 一键复跑（取源→哈希门→登记→结果信封→独立自检；需 TENSOR_API_BASE/TENSOR_AGENT_USER/TENSOR_AGENT_PASS）
python3 scripts/kf/build_asset_manifest_7545.py build result verify
# 出图 + 渲染本报告
python3 scripts/kf/report_7545_01.py render
```

## 结果信封

```json
{
  "package_id": "wp-7545-01",
  "task_type": "01-asset-registration",
  "report_id": "7545",
  "provenance": {
    "source_uri": "tensor://reports/7545",
    "source_field": "markdown",
    "source_hash": "sha256:84010e0091071d5971888931b9d6b73fc3bba4f217dcd17ab739979fc1c5ae60",
    "hash_alg": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 3583,
    "source_bytes_utf8": 6333,
    "fetched_via": "GET /api/v1/tensor/reports/7545",
    "generator": "scripts/kf/build_asset_manifest_7545.py",
    "contract_version": "1.0",
    "producer": "agent/m15597",
    "emitted_at": "2026-11-12T01:27:49.904917+00:00"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-7545-01/asset_manifest.json",
      "sha256": "82bb6145f8a9f5ffd7acc0cbc1c45faecf118eafd8a8b45f4e7463d3cb350f4a",
      "bytes": 20697,
      "asset_count": 18,
      "by_resolution": {
        "resolved_in_source": 1,
        "declared_absent": 4,
        "referenced_unresolved": 13
      },
      "claims": 0
    }
  },
  "claims": []
}
```
