# KF-RESULT wp-5716-01

## ① 本工序做了什么

工作包 `wp-5716-01`（task_type `01-asset-registration`，lane C）只做一件事：给 report_id=5716 做**源资产登记**——确认报告 markdown 的字节哈希与契约值一致，把可解析的附图与文中引用的路径逐条登记为资产，对每条登记给出可复算的定位（行号 + 原文逐字引文），拿不到字节的资产如实标 unresolved / metadata_only。

不做抽取、不做报告分类、不生成 claim（`claims` 为空数组，契约允许），也不给任何条目打 verified —— verification 由平台门计算。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`GET GET http://127.0.0.1:8010/api/v1/tensor/reports/5716`（Bearer 登录 token），写入 worktree 内 `runs/wp-5716-01/report_5716.md`，对 `markdown` 的 UTF-8 字节算 sha256。
2. **哈希门先于登记**：实算哈希与契约 `input.source_hash` 比对，不一致就直接中止（拒绝登记漂移字节）。实算 = `4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377`，chars=4790，bytes_utf8=8108。
3. **资产抽取（三条腿）**：a) 报告本体=1 条 `report_markdown`；b) 平台 `figures[]` 记录逐条登记（有 `png_base64` 才算 resolved，否则 `metadata_only`）；c) 正文里所有路径样式引用（markdown 图片、反引号包住的路径、裸路径、以及 glob 通配）按 (path, line) 出现级登记，行号 1-based、引文取**整行原文**。
4. **解析边界**：引用路径只在 TensorKnowledge 交付 worktree 内解析（不跨仓猜测）；通配引用（如 `*.png`）登记为 pattern 资产，不枚举成员、不给字节哈希。
5. **平台附件端点探测（只读）**：`{"/artifacts": {"status": "http_404"}, "/files": {"status": "http_404"}, "/attachments": {"status": "http_404"}}` → 全部 404，说明平台不存报告附件的字节载荷，故附图只能到 `metadata_only`。
6. **自检**：`verify` 子命令独立重跑全部 acceptance 项（重新登录、重新取原文、重新逐条解析定位），结果落 `docs/kf/wp-5716-01/verification.json`；`pytest tests/test_kf_asset_manifest_5716.py` 再以离线+在线双路复核。

复跑命令（一键）：

```bash
cd <repo>
python3 scripts/kf/build_asset_manifest_5716.py build result verify   # 登记→信封→自检
python3 scripts/kf/fig_asset_inventory_5716.py                        # 资产盘点图
python3 -m pytest tests/test_kf_asset_manifest_5716.py -q            # 9 passed
```

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-5716-01/asset_manifest.json` | 资产清单：18 条资产（resolved 1 / unresolved 13 / metadata_only 4）、claims=0、provenance 带源哈希 |
| `docs/kf/wp-5716-01/verification.json` | 自检判据表：7 项 acceptance 全 pass=True；manifest_sha256=851f8a8f9f1a10df |
| `docs/kf/wp-5716-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），source_hash 与平台报告 markdown 字节一致；outputs 内嵌 manifest sha256=851f8a8f9f1a10df |
| `docs/kf/wp-5716-01/fig_asset_inventory.png` | 资产盘点图（按 kind × resolution 堆叠，数字直接读 manifest） |
| `scripts/kf/build_asset_manifest_5716.py` | 登记器 + 自检器 + 信封生成器（含 report_id 作用域断言） |
| `scripts/kf/fig_asset_inventory_5716.py` | 盘点图生成器（零手抄：全部读 manifest） |
| `tests/test_kf_asset_manifest_5716.py` | 9 条不变量测试：哈希/定位逐字/ID 唯一/claims 空/汇总自洽/信封绑定/在线复取 |
| `runs/wp-5716-01/report_5716.md` | 平台报告原文的字节级副本（离线复核定位的锚） |

资产分类明细（来自 manifest `summary.by_kind`）：

| kind / resolution | 条数 |
|---|---|
| `data_artifact_reference/unresolved` | 4 |
| `document_reference/unresolved` | 1 |
| `embedded_figure/metadata_only` | 4 |
| `figure_set_pattern/unresolved` | 1 |
| `report_markdown/resolved` | 1 |
| `source_code_reference/unresolved` | 7 |

## ④ 证据定位表（claim/字段 → 原文逐字引文）

清单里每一条资产的 `locator` 都带 (line, quote)；下表把**每条登记资产**的定位与引文原样摊开（引文由程序从报告字节切片得到，非手抄；`quote` 与所在行整行相等，可直接 grep 复核）。

| asset_id | kind | resolution | line | 原文引文（逐字） |
|---|---|---|---|---|
| `r5716:source` | report_markdown | resolved | — | 报告字段 `markdown`（报告本体，字节即源哈希） |
| `r5716:figure:01` | embedded_figure | metadata_only | — | 报告字段 `figures`[0] `fig2_contract_regrid.png` |
| `r5716:figure:02` | embedded_figure | metadata_only | — | 报告字段 `figures`[1] `fig4_speed_profile.png` |
| `r5716:figure:03` | embedded_figure | metadata_only | — | 报告字段 `figures`[2] `fig6_fatigue.png` |
| `r5716:figure:04` | embedded_figure | metadata_only | — | 报告字段 `figures`[3] `fig7_uikku_anchor.png` |
| `r5716:ref:01` | source_code_reference | unresolved | 9 | `阶段全部调用上游模块本体（不重写物理），本战役只新增**契约层与验收层**：`contracts.py`（单位表/坐标系/保守重映射/方向探针）、`chain.py`（L1 案例单源注入 + 逐阶段 sha256 台账）、`assertions.py`（16 项门断言 + 7 项披露）、`assets.py`（跨库资产对账）、`figures.py`/`report.py`（图与报告程序化生成）。数据流：L1→A2→[保守重映射]→D1→C3→E1，B2 的 8 MN 与 C3 设计点喂给 E1，D1 航线冰厚分箱喂给 C3。一条命令：`cd backend && python -m modules.campaign_ice_nav.run_campaign`，墙钟 50.7 s。` |
| `r5716:ref:02` | source_code_reference | unresolved | 9 | `阶段全部调用上游模块本体（不重写物理），本战役只新增**契约层与验收层**：`contracts.py`（单位表/坐标系/保守重映射/方向探针）、`chain.py`（L1 案例单源注入 + 逐阶段 sha256 台账）、`assertions.py`（16 项门断言 + 7 项披露）、`assets.py`（跨库资产对账）、`figures.py`/`report.py`（图与报告程序化生成）。数据流：L1→A2→[保守重映射]→D1→C3→E1，B2 的 8 MN 与 C3 设计点喂给 E1，D1 航线冰厚分箱喂给 C3。一条命令：`cd backend && python -m modules.campaign_ice_nav.run_campaign`，墙钟 50.7 s。` |
| `r5716:ref:03` | source_code_reference | unresolved | 9 | `阶段全部调用上游模块本体（不重写物理），本战役只新增**契约层与验收层**：`contracts.py`（单位表/坐标系/保守重映射/方向探针）、`chain.py`（L1 案例单源注入 + 逐阶段 sha256 台账）、`assertions.py`（16 项门断言 + 7 项披露）、`assets.py`（跨库资产对账）、`figures.py`/`report.py`（图与报告程序化生成）。数据流：L1→A2→[保守重映射]→D1→C3→E1，B2 的 8 MN 与 C3 设计点喂给 E1，D1 航线冰厚分箱喂给 C3。一条命令：`cd backend && python -m modules.campaign_ice_nav.run_campaign`，墙钟 50.7 s。` |
| `r5716:ref:04` | source_code_reference | unresolved | 9 | `阶段全部调用上游模块本体（不重写物理），本战役只新增**契约层与验收层**：`contracts.py`（单位表/坐标系/保守重映射/方向探针）、`chain.py`（L1 案例单源注入 + 逐阶段 sha256 台账）、`assertions.py`（16 项门断言 + 7 项披露）、`assets.py`（跨库资产对账）、`figures.py`/`report.py`（图与报告程序化生成）。数据流：L1→A2→[保守重映射]→D1→C3→E1，B2 的 8 MN 与 C3 设计点喂给 E1，D1 航线冰厚分箱喂给 C3。一条命令：`cd backend && python -m modules.campaign_ice_nav.run_campaign`，墙钟 50.7 s。` |
| `r5716:ref:05` | source_code_reference | unresolved | 9 | `阶段全部调用上游模块本体（不重写物理），本战役只新增**契约层与验收层**：`contracts.py`（单位表/坐标系/保守重映射/方向探针）、`chain.py`（L1 案例单源注入 + 逐阶段 sha256 台账）、`assertions.py`（16 项门断言 + 7 项披露）、`assets.py`（跨库资产对账）、`figures.py`/`report.py`（图与报告程序化生成）。数据流：L1→A2→[保守重映射]→D1→C3→E1，B2 的 8 MN 与 C3 设计点喂给 E1，D1 航线冰厚分箱喂给 C3。一条命令：`cd backend && python -m modules.campaign_ice_nav.run_campaign`，墙钟 50.7 s。` |
| `r5716:ref:06` | source_code_reference | unresolved | 9 | `阶段全部调用上游模块本体（不重写物理），本战役只新增**契约层与验收层**：`contracts.py`（单位表/坐标系/保守重映射/方向探针）、`chain.py`（L1 案例单源注入 + 逐阶段 sha256 台账）、`assertions.py`（16 项门断言 + 7 项披露）、`assets.py`（跨库资产对账）、`figures.py`/`report.py`（图与报告程序化生成）。数据流：L1→A2→[保守重映射]→D1→C3→E1，B2 的 8 MN 与 C3 设计点喂给 E1，D1 航线冰厚分箱喂给 C3。一条命令：`cd backend && python -m modules.campaign_ice_nav.run_campaign`，墙钟 50.7 s。` |
| `r5716:ref:07` | data_artifact_reference | unresolved | 63 | `\| A2 复现上游工件（同配置） \| 0.0000% \| artifacts/ice_da_forecast_a2/metrics.json \| 是 \|` |
| `r5716:ref:08` | data_artifact_reference | unresolved | 64 | `\| B2 复现上游工件（同输入） \| 0.0000% \| artifacts/fatigue_pc6.json \| 是 \|` |
| `r5716:ref:09` | data_artifact_reference | unresolved | 65 | `\| D1 基准场 vs 上游工件 \| ≤1e-9 绝对 \| artifacts/ice_route_opt/summary.json \| 是 \|` |
| `r5716:ref:10` | data_artifact_reference | unresolved | 86 | `工件：`artifacts/campaign_ice_nav/campaign_acceptance.json`（含全链 sha256 清单）、`docs/campaign/ice_nav_campaign_report.md`、`artifacts/campaign_ice_nav/figures/*.png`；pytest `backend/tests/test_campaign_ice_nav.py` 13 passed；上游四套测试（ICE_DA 69、route 14、speed_profile 14、ice_belt 19）仍全绿。` |
| `r5716:ref:11` | document_reference | unresolved | 86 | `工件：`artifacts/campaign_ice_nav/campaign_acceptance.json`（含全链 sha256 清单）、`docs/campaign/ice_nav_campaign_report.md`、`artifacts/campaign_ice_nav/figures/*.png`；pytest `backend/tests/test_campaign_ice_nav.py` 13 passed；上游四套测试（ICE_DA 69、route 14、speed_profile 14、ice_belt 19）仍全绿。` |
| `r5716:ref:12` | source_code_reference | unresolved | 86 | `工件：`artifacts/campaign_ice_nav/campaign_acceptance.json`（含全链 sha256 清单）、`docs/campaign/ice_nav_campaign_report.md`、`artifacts/campaign_ice_nav/figures/*.png`；pytest `backend/tests/test_campaign_ice_nav.py` 13 passed；上游四套测试（ICE_DA 69、route 14、speed_profile 14、ice_belt 19）仍全绿。` |
| `r5716:ref:13` | figure_set_pattern | unresolved | 86 | `工件：`artifacts/campaign_ice_nav/campaign_acceptance.json`（含全链 sha256 清单）、`docs/campaign/ice_nav_campaign_report.md`、`artifacts/campaign_ice_nav/figures/*.png`；pytest `backend/tests/test_campaign_ice_nav.py` 13 passed；上游四套测试（ICE_DA 69、route 14、speed_profile 14、ice_belt 19）仍全绿。` |

资产盘点观察（`inventory_observations`，只登记、不判定，均非 verified）：

- **O01-figure-count**（status=`unresolved_discrepancy`）：The report declares 4 figures in the figures field and 7 figures overall; the platform report record stores 4 figure entries (metadata only, no bytes). The difference is recorded as an unresolved inventory discrepancy, not silently reconciled.
  - L42：`（4 张图见 figures 字段：契约重映射 / 航速剖面 / 疲劳 S-N 与利用率 / Uikku 实冰锚）`
  - L78：`一致性门 16/16 通过、一条命令端到端跑通、JSON/报告/7 图齐全。**但有 4 项披露项如实不通过，不覆盖：**`
- **O02-artifact-diagram-set**（status=`unresolved`）：The report cites a figure set by glob (1 glob reference(s) registered as pattern assets); member files are not enumerable from the report alone, so the set is registered unresolved.
  - L86：`工件：`artifacts/campaign_ice_nav/campaign_acceptance.json`（含全链 sha256 清单）、`docs/campaign/ice_nav_campaign_report.md`、`artifacts/campaign_ice_nav/figures/*.png`；pytest `backend/tests/test_campaign_ice_nav.py` 13 passed；上游四套测试（ICE_DA 69、route 14、speed_profile 14、ice_belt 19）仍全绿。`

## ⑤ 注意点与局限

1. Registration only: no text extraction, no claim generation, no verified marks (verification is platform-gated).
2. Referenced paths resolve strictly inside the TensorKnowledge delivery worktree; other repos are outside this work package's boundary, so cross-repo source references stay unresolved by design.
3. Absent artefacts are registered as unresolved rather than assumed present; no target was fetched to fill a gap.
4. Glob references (e.g. figures/*.png) are registered as pattern assets: the referenced set has no single byte target, so its members are not enumerated or hashed here.
5. inventory_observations records asset-inventory-level discrepancies found while registering (with verbatim quotes and explicit unresolved status). No domain claim is drawn from them and none is marked verified.
6. 附图只到 `metadata_only`：平台 `figures[]` 只有 name/caption，无 `png_base64`，且 `/artifacts|/files|/attachments` 三端点均 404，因此 4 张图**没有**字节哈希可声明。
7. 文中 13 条路径引用全部 unresolved，属设计而非失败：它们指向 campaign 侧产物（`artifacts/campaign_ice_nav/...`）与 `backend/...` 代码，均不在本仓交付 worktree 内；本包不跨仓取数、不臆测存在性。
8. 观察 O01 记录一处**清单层面**的不一致：报告第 42 行称 figures 字段有 4 张图、第 78 行称 7 图齐全，平台记录实际存 4 条 figure 元数据。本包只登记该差异（附逐字引文），不做任何领域结论，也不代为调和。
9. 引用正则的已知盲区：不含扩展名的路径（如目录级引用）不会登记；glob 只登记模式不展开成员。

## ⑥ 误差判定与自检

**误差判定（显式回答是否 <3%）**：本工序不产生物理量，唯一可比的数值是**字节恒等**类指标，逐项如下：

| 误差项 | 实测 | 基准 | 绝对差 | 是否 <3% |
|---|---|---|---|---|
| 报告 markdown 的 sha256 vs 契约 `input.source_hash` | `4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377` | `4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377` | 0（完全相等） | 是（同等式，非物理误差） |
| 字符数（平台 markdown, 实算）vs 契约 `input.chars` | 4790 | 4790 | 0 | 是 |
| 每条 locator 引文 vs 该行原文 | 13/13 条整行相等 | 原文逐字 | 0 | 是（逐字相等） |
| manifest 字节 vs 信封 `outputs.asset_manifest.json.sha256` | `851f8a8f9f1a10df…` | `851f8a8f9f1a10df…` | 0 | 是 |

**无物理基准的声明**：01-asset-registration 只是登记源资产业节与定位，不计算阻力/推进/耐波等任何物理量，因此不存在实验值/参考解可对标；上表全是**恒等校验**（差为 0 只说明字节一致，不构成物理精度承诺）。登记不到字节的资产一律显式标 `unresolved`/`metadata_only`，不用估计值填空。

**自检：逐条对照 acceptance**

| acceptance 项 | 结果 | 依据（自检明细） |
|---|---|---|
| `valid_json` | ✔ pass | json.loads OK |
| `schema_pass` | ✔ pass | missing_top=[] missing_provenance=[] |
| `source_locator_resolvable` | ✔ pass | checked 18 locators; unresolvable=[] |
| `source_hash_matches` | ✔ pass | recomputed=4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377 declared=4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377 contract=4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377 |
| `no_duplicate_ids` | ✔ pass | assets=18 unique=18 |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✔ pass | claims=0 violating=0 (empty array: vacuously satisfied per contract notes) |
| `do_not_mark_claims_as_verified`（补充不变量） | ✔ pass | claims carry no 'verified' status |

全部 7 项自检 通过（`all_pass=True`）。**注意**：这是本包自己的自检，不是平台门结论；本包未把任何条目标成 verified。

## 结果信封（唯一 json 代码块，原样提交）

```json
{
  "package_id": "wp-5716-01",
  "task_type": "01-asset-registration",
  "report_id": "5716",
  "provenance": {
    "source_uri": "tensor://reports/5716",
    "source_field": "markdown",
    "source_hash": "sha256:4f9848b22b55515826476e1d5b2fcd15da80087a3d261d6a937a4c17cda68377",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 4790,
    "source_bytes_utf8": 8108,
    "fetched_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5716",
    "generator": "scripts/kf/build_asset_manifest_5716.py",
    "contract_version": "1.0"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-5716-01/asset_manifest.json",
      "sha256": "851f8a8f9f1a10df3a3941d7157f0fa7381a26385350c73d49a22c84953deaa9",
      "bytes": 22994,
      "asset_count": 18,
      "claims": 0
    }
  }
}
```
