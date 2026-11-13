# KF-RESULT wp-615-01

> 工序 01-asset-registration ｜ report_id=615 ｜ lane C ｜
> source_uri `tensor://reports/615` ｜ source_field `markdown`
> 归档产物：`artifacts/kf/wp-615-01/asset_manifest.json`、`kf_result.json`、`checks.json`、`source_snapshot/`

## ① 本工序做了什么（案例介绍 / Case）

源报告 615 = **SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework**（scenario_key `SIR-PC2|F06`，mission_id `706`，
status `published`，created_at `2026-10-31T04:20:06.619069+00:00`）。这是冰区航行战役 L1_foundation 层的
DEM↔流体双向耦合框架报告：物理背景是碎冰颗粒与流场（海水/船体边界层）的双向动量交换。

本工序只做一件事：**把这份报告登记成可被下游工序寻址的资产清单**——确认 report_id 与 markdown 字节哈希、
枚举可解析的附件/工件、给出每条资产的原文定位（字符偏移 + 逐字引文）、把拿不到字节的资产如实登记为未解析。
**不抽取知识**（claims=[]）、**不判定 verified**（裁决权在平台验证门）、**不重跑上游算例**。

报告自报的关键参数（下表由脚本从源 markdown 的参数表/基准表**程序化重解析**后拼装，非手打；
逐字定位见 ④）：颗粒密度 ρ_p 1100 kg/m³、流体密度 ρ_f 1000 kg/m³、颗粒半径 R 0.5 mm、动力粘度 μ 1.0×10⁻³ Pa·s、重力加速度 g 9.81 m/s²、流体网格 8×8×8 cells、域尺寸 40×40×40 mm³；Stokes 终端速度解析解 0.054500 m/s，模拟值 0.054461 m/s（报告自报相对误差 0.000709 (0.07%)）。

## ② 怎么做的（方法 / 工具链 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/615`（Bearer token，`POST /api/v1/auth/login` 取得），
   只取 `markdown` 字段；脚本硬锁 `report_id=615`，其它 id 直接 `SystemExit`（互不覆盖前提）。
2. **指纹**：对 `markdown` 的 UTF-8 字节独立重算 sha256，与契约 `source_hash` 对齐；
   同时核字符数（契约 chars=2125，实测 2125）与行数、字节数。
3. **零手抄定位**：引文**不手打**——脚本在 markdown 上做选择器定位（H1 行、`### 标题` 后的首个非空行、
   首个表格块的首个数据行、列表块的第 k 项等），把**命中的整行原文**作为 quote，
   并记录 `offset_chars`；随后对每条 quote 做 `quote in markdown` **和** `markdown[offset:offset+len] == quote`
   双重回读（任一失败即门失败），命中次数一并登记。
4. **结构门**：清单与信封分别用 `schemas/asset_manifest.v1.schema.json`、`schemas/kf_result.v1.schema.json`
   做 jsonschema（Draft 2020-12）校验；ID 唯一性、状态-缺口一致性、unresolved 必须带理由（≥10 字符）逐条断言。
5. **未解析登记**：图件、测试日志、代码指针三类走端点探针 + 正文检索，拿不到就如实入 `unresolved`，
   **不重绘、不代上游补图、不反推**。
6. **工具链**：Python 3 / requests（取源）/ hashlib（指纹）/ jsonschema 4.26（结构门）/
   matplotlib 3.10（图件）/ pytest（回归）。脚本：`scripts/kf/wp_615_01_register_assets.py`、
   `scripts/kf/build_wp_615_01_report.py`；测试：`tests/test_kf_wp_615_01.py`。
7. **离线可重建**：抓取时把完整记录落到 `source_snapshot/report_615.json`，
   `--record-file` 可无网复跑；离线重建与在线产物逐字节一致（`generated_at` 除外，探针结果沿用上次登记）。

**一键复跑**（在线，需要 `$TENSOR_API_BASE` / `$TENSOR_AGENT_USER` / `$TENSOR_AGENT_PASS`）：

```
TOKEN=$(curl -s -X POST $TENSOR_API_BASE/auth/login -H 'Content-Type: application/json' -d "{\"username\":\"$TENSOR_AGENT_USER\",\"password\":\"$TENSOR_AGENT_PASS\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])'); python3 scripts/kf/wp_615_01_register_assets.py && python3 scripts/kf/build_wp_615_01_report.py && python3 -m pytest tests/test_kf_wp_615_01.py -q
```

离线复跑（无网无 token）：

```
python3 scripts/kf/wp_615_01_register_assets.py --record-file artifacts/kf/wp-615-01/source_snapshot/report_615.json --out /tmp/wp615_repro   # 无网/无 token 复跑：读快照重建清单，与仓库产物逐字节一致（generated_at 除外）
```

## ③ 产出物清单（含程序化注入的数字）

| 输出文件 | 要点 |
|---|---|
| `artifacts/kf/wp-615-01/asset_manifest.json` | 工序 01 唯一输出：source 指纹 + 14 条资产 + 3 条未解析缺口 + locator_checks |
| `artifacts/kf/wp-615-01/kf_result.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]） |
| `artifacts/kf/wp-615-01/checks.json` | 验收自检机读结果（13 项布尔通过项 + 明细） |
| `artifacts/kf/wp-615-01/source_snapshot/report_615.json` | 取源时刻的完整记录快照（离线重建与审计用） |
| `artifacts/kf/wp-615-01/figures/wp61501_asset_registry.png` | 图 1：资产登记图（左：资产/状态/偏移；右：验收自检） |
| `docs/kf/KF-RESULT-wp-615-01.md` | 本报告正文（含唯一一个 JSON 结果代码块） |
| `knowledge/kf/wp-615-01/` | 交付镜像（`artifacts/` 被 .gitignore 忽略，随分支交付的是这一份）：清单/信封/自检/图/源快照，与 artifacts 逐字节一致（tests 绑定） |

源身份事实：`sha256 = sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75`，chars=2125，bytes=3310，lines=87；
title 与契约一致=True，scenario_key 与契约一致=True，
title 在 markdown H1 逐字出现=True。

源报告 §3 自报的验收判据（程序化转述，本工序**不背书**，裁决权在平台验证门）：
momentum_exchange_conservation=0.0（阈值 < 1e-10 kg·m/s，✅ PASS）；single_particle_settling_vs_stokes=0.000709（阈值 < 0.05 ratio，✅ PASS）；pytest_test_dem_fluid_coupling=PASS（阈值 PASS bool，✅ PASS）。

### 资产登记表（14 条，状态分布 {"resolved": 13, "declared_unresolvable": 1}）

| asset_id | kind | status | offset(chars) | quote（逐字，节选） |
|---|---|---|---|---|
| asset-615-01-report-markdown | report_markdown | resolved | 1 | `# SIR-PC2\|F06: 3D DEM↔Fluid Bidirectional Coupling Framework` |
| asset-615-02-report-record | report_record_metadata | resolved | 3 | `SIR-PC2\|F06: 3D DEM↔Fluid Bidirectional Coupling Framework` |
| asset-615-03-section-physics-background | section_prose | resolved | 102 | `冰区航行中，碎冰颗粒与流场（海水/船体边界层）的双向耦合是预测冰载荷的关键。本任务实现DEM颗粒与LBM/CFD流场的双向动量交换框架，为冰区航行战役提供基` |
| asset-615-04-table-geometry-parameters | parameter_table | resolved | 237 | `\| 颗粒密度 ρ_p \| 1100 \| kg/m³ \|` |
| asset-615-05-equation-stokes-terminal-velocity | equation | resolved | 439 | `$$v_t = \frac{2}{9}\frac{(\rho_p - \rho_f)\,g\,R^2}{\mu} = 0.054500 \text{ m/s` |
| asset-615-06-method-coupling-steps | method_steps | resolved | 683 | `4. **力分配**：使用与速度采样相同的三线性权重将力分配到流体网格（伴随操作）` |
| asset-615-07-equation-momentum-conservation | equation | resolved | 779 | `由于使用相同的插值权重进行速度采样和力分配，且严格遵循Newton第三定律，离散动量守恒精确成立：` |
| asset-615-08-toolchain-list | toolchain_list | resolved | 933 | `- PyTorch (float64) 用于数值精度` |
| asset-615-09-table-acceptance-criteria | acceptance_table | resolved | 1095 | `\| momentum_exchange_conservation \| 0.0 \| < 1e-10 \| kg·m/s \| ✅ PASS \|` |
| asset-615-10-table-stokes-benchmark | result_table | resolved | 1375 | `\| 模拟终端速度 v_t \| 0.054461 m/s \|` |
| asset-615-11-test-suite-summary | test_evidence_summary | resolved | 1491 | `- 12 tests collected, 12 passed, 0 failed` |
| asset-615-12-limitations-list | limitations_list | resolved | 1803 | `4. **润滑力**：未包含近壁颗粒的润滑力模型` |
| asset-615-13-table-error-judgement | result_table | resolved | 1933 | `\| 终端速度 v_t \| Stokes解析 0.05450 m/s \| 0.05446 m/s \| 0.07% \| ✅ YES \|` |
| asset-615-14-figure-settling_velocity | figure | declared_unresolvable | 1603 | `见内嵌图：单颗粒沉降速度时间历程与Stokes解析解对比。` |

### 未解析缺口（3 条）

| asset_id | kind | 理由 |
|---|---|---|
| asset-615-14-figure-settling_velocity | figure | 记录 figures 只有 ['caption', 'name']（无 png_base64 载荷），图件端点 HTTP 404 = figure not found，字节不可经 API 取得；本工序不重绘、不代上游补图，保留未解析。 |
| asset-615-15-test-run-artifact | run_artifact | §3 自述 12 tests collected / 12 passed，但报告未附原始 pytest 日志、trace 或测试文件路径，工件字节不可得；工序 01 不重跑上游算例，故保留未解析（断言可定位：asset-615-11）。 |
| asset-615-16-codebase-pointer | codebase_pointer | 报告 markdown 正文不含代码仓库路径、分支或提交号，无法把「工具链/12 项测试」绑定到具体文件；仅能由记录 mission_id=706 解析到 mission 记录 repo=TensorDEM，属记录级间接线索，不认定为工件绑定。 |

**图 1**（`artifacts/kf/wp-615-01/figures/wp61501_asset_registry.png`）：左图为 report 615 的 14 条资产
（颜色=status，@n=逐字引文在 markdown 中的字符偏移），右图为机读验收自检。说明：本工序是纯登记工序，
不产生任何物理场量，因此**没有场量云图、也没有与解析解/实验的比较曲线**——这是本单无物理图件的如实理由；
图中数据全部来自 `asset_manifest.json` / `checks.json` 注入，无手填点。

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段/资产 | 原文引文（逐字） |
|---|---|
| source_hash / chars | `sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75`；chars=2125，chars_match_contract=True |
| title / scenario_key | `SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework` ／ `SIR-PC2|F06` |
| 参数表（7 行） | `| 颗粒密度 ρ_p | 1100 | kg/m³ |` |
| Stokes 解析解 | `$$v_t = \frac{2}{9}\frac{(\rho_p - \rho_f)\,g\,R^2}{\mu} = 0.054500 \text{ m/s}$$` |
| 耦合算法第 4 步 | `4. **力分配**：使用与速度采样相同的三线性权重将力分配到流体网格（伴随操作）` |
| 动量守恒保证 | `由于使用相同的插值权重进行速度采样和力分配，且严格遵循Newton第三定律，离散动量守恒精确成立：` |
| 验收判据首行 | `| momentum_exchange_conservation | 0.0 | < 1e-10 | kg·m/s | ✅ PASS |` |
| Stokes 沉降模拟值 | `| 模拟终端速度 v_t | 0.054461 m/s |` |
| 测试套件自述 | `- 12 tests collected, 12 passed, 0 failed` |
| 局限性第 4 条 | `4. **润滑力**：未包含近壁颗粒的润滑力模型` |
| 误差判定首行 | `| 终端速度 v_t | Stokes解析 0.05450 m/s | 0.05446 m/s | 0.07% | ✅ YES |` |
| 图件引用（字节不可得，端点 HTTP 404） | `见内嵌图：单颗粒沉降速度时间历程与Stokes解析解对比。` |

上表每条引文的字符偏移与命中次数见 `asset_manifest.json → locator_checks`；
`source_locator_resolvable=True`，`offset_mismatch=[]`。

## ⑤ 注意点与局限

1. **图件不可得**：记录 `figures` 只有 `name/caption`（无 `png_base64`），端点
   `GET /tensor/reports/615/figures/settling_velocity` 返回 HTTP 404；
   正文只引用了「见内嵌图…」。本工序**不重绘、不代上游补图**，登记为 declared_unresolvable。
2. **测试证据是自述**：报告 §3 写 `- 12 tests collected, 12 passed, 0 failed`，但无原始日志/trace/测试文件路径；
   本工序只登记该断言可定位，**不把它当通过证据**，也未重跑上游算例（工序 01 不做）。
3. **代码指针缺失**：正文无仓库路径/分支/提交号；仅由记录 `mission_id=706` 探到
   mission 记录 `repo=TensorDEM`，属记录级间接线索，不作工件绑定。
4. **不评价真伪**：本清单不含 claims、不标 verified；`momentum_exchange_conservation=0.0`、
   `0.054461 m/s` 等数值的裁决权在平台验证门与下游工序 03。
5. **互不覆盖**：脚本硬锁 `report_id=615`；本单未读写其它任何 report_id 的内容。
6. **引文口径**：quote 一律取**整行原文**（含 markdown 表格竖线/LaTeX），不裁不改，
   因此表格行较长；跨行内容会取其中一行代表行，不做字符串拼接（避免二次转录误差）。

## ⑥ 误差判定与自检

### 关键量 vs 基准（本工序的“基准”=契约与原文）

| 关键量 | 基准 | 实测 | 误差 | < 3%? |
|---|---|---|---|---|
| markdown 字节哈希 | 契约 `sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75` | `sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75` | 0（逐字节相同） | ✅ YES（0%） |
| 字符数 | 契约 2125 | 2125 | 0 | ✅ YES（0%） |
| 引文可定位性 | 每条 quote 必须逐字命中 | 0 条失配 | 0 条 | ✅ YES（0%） |
| ID 唯一性 | 无重复 asset_id | 重复 0 条 | 0 | ✅ YES（0%） |

结论：登记层无物理量误差，误差面是**字节/引文级**，4 项全部 0 偏差（<3% 显式成立）。
报告正文的物理数值（0.07% 终端速度误差等）属上游报告自述，本工序不复核、不背书。

### acceptance 逐条自检

| 验收项 | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | asset_manifest.json / kf_result.json 均可 json.loads |
| schema_pass | ✅ | jsonschema Draft2020-12；errors=[] |
| source_locator_resolvable | ✅ | 逐条 quote 子串 + 偏移回读；bad_quotes=0，offset_mismatch=[] |
| source_hash_matches | ✅ | 独立重算 `sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75` |
| no_duplicate_ids | ✅ | 14 条资产 ID 全互异 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[]（空集恒真，且契约允许）＋3 条缺口带理由 |
| kf_result 信封结构 | ✅ | schemas/kf_result.v1.schema.json；errors=[] |

honest-FAIL 申报：**无失败项**。但须显式声明三项**未完成/不可得**（不是通过）：
图件字节不可得、pytest 原始日志不可得、代码级绑定不可得——三者均已登记在 `unresolved`，
下游工序 03/05 若需这些字节，应回上游补件，而不是由本工序生成。
`all_pass=True`。

## 结果信封（唯一 JSON 块，原样提交）

```json
{
  "package_id": "wp-615-01",
  "task_type": "01-asset-registration",
  "report_id": "615",
  "provenance": {
    "source_hash": "sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75",
    "source_field": "markdown",
    "producer": "kf-worker/tp-native-1",
    "emitted_at": "2026-11-12T00:54:43+00:00",
    "notes": "asset_manifest.json 见 outputs；引文均由脚本从 markdown 按行取子串，逐条做 quote in markdown + 偏移回读确认；未抽取 claims，未标 verified。"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-615-01",
      "task_type": "01-asset-registration",
      "report_id": "615",
      "lane": "C",
      "generated_at": "2026-11-12T00:54:43+00:00",
      "producer": "kf-worker/tp-native-1",
      "source": {
        "report_id": "615",
        "source_uri": "tensor://reports/615",
        "source_field": "markdown",
        "source_hash": "sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75",
        "contract_source_hash": "sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75",
        "hash_algo": "sha256",
        "hash_scope": "UTF-8 bytes of tensor_reports.markdown",
        "hash_match": true,
        "chars": 2125,
        "contract_chars": 2125,
        "chars_match_contract": true,
        "bytes": 3310,
        "lines": 87,
        "fetched_via": "GET /api/v1/tensor/reports/615 (Bearer token)",
        "record_fields": {
          "title": "SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework",
          "scenario_key": "SIR-PC2|F06",
          "mission_id": 706,
          "status": "published",
          "created_at": "2026-10-31T04:20:06.619069+00:00",
          "tags": [
            "DEM",
            "fluid-coupling",
            "momentum-conservation",
            "Stokes",
            "ice-navigation",
            "L1_foundation"
          ],
          "contract_title": "SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework",
          "contract_scenario_key": "SIR-PC2|F06",
          "title_matches_contract": true,
          "scenario_matches_contract": true,
          "title_matches_markdown_h1": true
        }
      },
      "assets": [
        {
          "asset_id": "asset-615-01-report-markdown",
          "kind": "report_markdown",
          "uri": "tensor://reports/615#markdown",
          "status": "resolved",
          "retrieval": {
            "endpoint": "GET /api/v1/tensor/reports/615",
            "field": "markdown",
            "http_status": 200
          },
          "sha256": "sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75",
          "chars": 2125,
          "bytes": 3310,
          "locator": {
            "source_field": "markdown",
            "section": "H1",
            "quote": "# SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework",
            "quote_verified": true,
            "offset_chars": 1,
            "note": "markdown 首行 H1，全文指纹载体"
          },
          "notes": "哈希口径=markdown 字段 UTF-8 字节；生产者独立重算后与契约 source_hash 对齐。"
        },
        {
          "asset_id": "asset-615-02-report-record",
          "kind": "report_record_metadata",
          "uri": "tensor://reports/615#record",
          "status": "resolved",
          "retrieval": {
            "endpoint": "GET /api/v1/tensor/reports/615",
            "field": "record",
            "http_status": 200
          },
          "fields": {
            "id": 615,
            "title": "SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework",
            "scenario_key": "SIR-PC2|F06",
            "mission_id": 706,
            "status": "published",
            "created_at": "2026-10-31T04:20:06.619069+00:00",
            "tags": [
              "DEM",
              "fluid-coupling",
              "momentum-conservation",
              "Stokes",
              "ice-navigation",
              "L1_foundation"
            ]
          },
          "locator": {
            "source_field": "markdown",
            "section": "record.title",
            "quote": "SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework",
            "quote_verified": true,
            "offset_chars": 3,
            "note": "记录 title 在 markdown H1 行内逐字出现"
          }
        },
        {
          "asset_id": "asset-615-03-section-physics-background",
          "kind": "section_prose",
          "uri": "tensor://reports/615#markdown/§1-物理背景",
          "status": "resolved",
          "chars": 84,
          "locator": {
            "source_field": "markdown",
            "section": "① 案例介绍 / 物理背景",
            "quote": "冰区航行中，碎冰颗粒与流场（海水/船体边界层）的双向耦合是预测冰载荷的关键。本任务实现DEM颗粒与LBM/CFD流场的双向动量交换框架，为冰区航行战役提供基础耦合能力。",
            "quote_verified": true,
            "offset_chars": 102,
            "note": "物理背景段首句（原文首行）"
          }
        },
        {
          "asset_id": "asset-615-04-table-geometry-parameters",
          "kind": "parameter_table",
          "uri": "tensor://reports/615#markdown/§1-几何与参数",
          "status": "resolved",
          "rows": 7,
          "fields": {
            "n_cols": 3,
            "header": "| 参数 | 值 | 单位 |"
          },
          "locator": {
            "source_field": "markdown",
            "section": "① 案例介绍 / 几何与参数",
            "quote": "| 颗粒密度 ρ_p | 1100 | kg/m³ |",
            "quote_verified": true,
            "offset_chars": 237,
            "note": "表首个数据行"
          }
        },
        {
          "asset_id": "asset-615-05-equation-stokes-terminal-velocity",
          "kind": "equation",
          "uri": "tensor://reports/615#markdown/§1-Stokes终端速度解析解",
          "status": "resolved",
          "chars": 81,
          "locator": {
            "source_field": "markdown",
            "section": "① 案例介绍 / Stokes终端速度解析解",
            "quote": "$$v_t = \\frac{2}{9}\\frac{(\\rho_p - \\rho_f)\\,g\\,R^2}{\\mu} = 0.054500 \\text{ m/s}$$",
            "quote_verified": true,
            "offset_chars": 439,
            "note": "LaTeX 解析解行"
          }
        },
        {
          "asset_id": "asset-615-06-method-coupling-steps",
          "kind": "method_steps",
          "uri": "tensor://reports/615#markdown/§2-耦合算法",
          "status": "resolved",
          "items": 5,
          "locator": {
            "source_field": "markdown",
            "section": "② 方法 / 耦合算法",
            "quote": "4. **力分配**：使用与速度采样相同的三线性权重将力分配到流体网格（伴随操作）",
            "quote_verified": true,
            "offset_chars": 683,
            "note": "第 4 步（力分配/伴随操作）"
          }
        },
        {
          "asset_id": "asset-615-07-equation-momentum-conservation",
          "kind": "equation",
          "uri": "tensor://reports/615#markdown/§2-动量守恒保证",
          "status": "resolved",
          "chars": 49,
          "locator": {
            "source_field": "markdown",
            "section": "② 方法 / 动量守恒保证",
            "quote": "由于使用相同的插值权重进行速度采样和力分配，且严格遵循Newton第三定律，离散动量守恒精确成立：",
            "quote_verified": true,
            "offset_chars": 779
          }
        },
        {
          "asset_id": "asset-615-08-toolchain-list",
          "kind": "toolchain_list",
          "uri": "tensor://reports/615#markdown/§2-工具链",
          "status": "resolved",
          "items": 3,
          "locator": {
            "source_field": "markdown",
            "section": "② 方法 / 工具链",
            "quote": "- PyTorch (float64) 用于数值精度",
            "quote_verified": true,
            "offset_chars": 933
          }
        },
        {
          "asset_id": "asset-615-09-table-acceptance-criteria",
          "kind": "acceptance_table",
          "uri": "tensor://reports/615#markdown/§3-验收判据",
          "status": "resolved",
          "rows": 3,
          "fields": {
            "n_cols": 5,
            "header": "| 判据 | 计算值 | 阈值 | 单位 | 状态 |"
          },
          "locator": {
            "source_field": "markdown",
            "section": "③ 计算结果 / 验收判据",
            "quote": "| momentum_exchange_conservation | 0.0 | < 1e-10 | kg·m/s | ✅ PASS |",
            "quote_verified": true,
            "offset_chars": 1095,
            "note": "表首个数据行"
          }
        },
        {
          "asset_id": "asset-615-10-table-stokes-benchmark",
          "kind": "result_table",
          "uri": "tensor://reports/615#markdown/§3-Stokes沉降基准",
          "status": "resolved",
          "rows": 5,
          "fields": {
            "n_cols": 2,
            "header": "| 量 | 值 |"
          },
          "locator": {
            "source_field": "markdown",
            "section": "③ 计算结果 / Stokes沉降基准",
            "quote": "| 模拟终端速度 v_t | 0.054461 m/s |",
            "quote_verified": true,
            "offset_chars": 1375,
            "note": "模拟终端速度行"
          }
        },
        {
          "asset_id": "asset-615-11-test-suite-summary",
          "kind": "test_evidence_summary",
          "uri": "tensor://reports/615#markdown/§3-测试套件",
          "status": "resolved",
          "locator": {
            "source_field": "markdown",
            "section": "③ 计算结果 / 测试套件",
            "quote": "- 12 tests collected, 12 passed, 0 failed",
            "quote_verified": true,
            "offset_chars": 1491,
            "note": "报告内自述的 pytest 汇总行（无原始日志附件）"
          }
        },
        {
          "asset_id": "asset-615-12-limitations-list",
          "kind": "limitations_list",
          "uri": "tensor://reports/615#markdown/§5-注意点",
          "status": "resolved",
          "items": 5,
          "locator": {
            "source_field": "markdown",
            "section": "⑤ 注意点（Limitations）",
            "quote": "4. **润滑力**：未包含近壁颗粒的润滑力模型",
            "quote_verified": true,
            "offset_chars": 1803,
            "note": "第 4 条（润滑力缺失）"
          }
        },
        {
          "asset_id": "asset-615-13-table-error-judgement",
          "kind": "result_table",
          "uri": "tensor://reports/615#markdown/§6-误差判定",
          "status": "resolved",
          "rows": 3,
          "fields": {
            "n_cols": 5,
            "header": "| 关键量 | 基准 | 计算值 | 误差 | < 3%? |"
          },
          "locator": {
            "source_field": "markdown",
            "section": "⑥ 误差判定",
            "quote": "| 终端速度 v_t | Stokes解析 0.05450 m/s | 0.05446 m/s | 0.07% | ✅ YES |",
            "quote_verified": true,
            "offset_chars": 1933,
            "note": "表首个数据行"
          }
        },
        {
          "asset_id": "asset-615-14-figure-settling_velocity",
          "kind": "figure",
          "uri": "tensor://reports/615/figures/settling_velocity",
          "status": "declared_unresolvable",
          "retrieval": {
            "endpoint": "GET /api/v1/tensor/reports/615/figures/settling_velocity",
            "http_status": 404,
            "body": {
              "detail": "figure not found"
            }
          },
          "sha256": null,
          "bytes": 0,
          "caption": "Single-particle settling: DEM↔fluid coupling (blue) vs Stokes analytical (red dashed). Terminal velocity ratio converges to 1.0 within 0.07% error.",
          "fields": {
            "figure_record_keys": [
              "caption",
              "name"
            ],
            "png_base64_present": false
          },
          "locator": {
            "source_field": "markdown",
            "section": "④ 结果图",
            "quote": "见内嵌图：单颗粒沉降速度时间历程与Stokes解析解对比。",
            "quote_verified": true,
            "offset_chars": 1603,
            "note": "正文引用了图件"
          }
        }
      ],
      "unresolved": [
        {
          "asset_id": "asset-615-14-figure-settling_velocity",
          "kind": "figure",
          "reason": "记录 figures 只有 ['caption', 'name']（无 png_base64 载荷），图件端点 HTTP 404 = figure not found，字节不可经 API 取得；本工序不重绘、不代上游补图，保留未解析。"
        },
        {
          "asset_id": "asset-615-15-test-run-artifact",
          "kind": "run_artifact",
          "reason": "§3 自述 12 tests collected / 12 passed，但报告未附原始 pytest 日志、trace 或测试文件路径，工件字节不可得；工序 01 不重跑上游算例，故保留未解析（断言可定位：asset-615-11）。"
        },
        {
          "asset_id": "asset-615-16-codebase-pointer",
          "kind": "codebase_pointer",
          "reason": "报告 markdown 正文不含代码仓库路径、分支或提交号，无法把「工具链/12 项测试」绑定到具体文件；仅能由记录 mission_id=706 解析到 mission 记录 repo=TensorDEM，属记录级间接线索，不认定为工件绑定。"
        }
      ],
      "counts": {
        "assets_total": 14,
        "by_status": {
          "resolved": 13,
          "declared_unresolvable": 1
        },
        "unresolved_total": 3
      },
      "locator_checks": {
        "asset-615-01-report-markdown": {
          "quote": "# SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework",
          "resolvable_in_markdown": true,
          "offset_chars": 1,
          "count_occurrences": 1
        },
        "asset-615-02-report-record": {
          "quote": "SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework",
          "resolvable_in_markdown": true,
          "offset_chars": 3,
          "count_occurrences": 1
        },
        "asset-615-03-section-physics-background": {
          "quote": "冰区航行中，碎冰颗粒与流场（海水/船体边界层）的双向耦合是预测冰载荷的关键。本任务实现DEM颗粒与LBM/CFD流场的双向动量交换框架，为冰区航行战役提供基础耦合能力。",
          "resolvable_in_markdown": true,
          "offset_chars": 102,
          "count_occurrences": 1
        },
        "asset-615-04-table-geometry-parameters": {
          "quote": "| 颗粒密度 ρ_p | 1100 | kg/m³ |",
          "resolvable_in_markdown": true,
          "offset_chars": 237,
          "count_occurrences": 1
        },
        "asset-615-05-equation-stokes-terminal-velocity": {
          "quote": "$$v_t = \\frac{2}{9}\\frac{(\\rho_p - \\rho_f)\\,g\\,R^2}{\\mu} = 0.054500 \\text{ m/s}$$",
          "resolvable_in_markdown": true,
          "offset_chars": 439,
          "count_occurrences": 1
        },
        "asset-615-06-method-coupling-steps": {
          "quote": "4. **力分配**：使用与速度采样相同的三线性权重将力分配到流体网格（伴随操作）",
          "resolvable_in_markdown": true,
          "offset_chars": 683,
          "count_occurrences": 1
        },
        "asset-615-07-equation-momentum-conservation": {
          "quote": "由于使用相同的插值权重进行速度采样和力分配，且严格遵循Newton第三定律，离散动量守恒精确成立：",
          "resolvable_in_markdown": true,
          "offset_chars": 779,
          "count_occurrences": 1
        },
        "asset-615-08-toolchain-list": {
          "quote": "- PyTorch (float64) 用于数值精度",
          "resolvable_in_markdown": true,
          "offset_chars": 933,
          "count_occurrences": 1
        },
        "asset-615-09-table-acceptance-criteria": {
          "quote": "| momentum_exchange_conservation | 0.0 | < 1e-10 | kg·m/s | ✅ PASS |",
          "resolvable_in_markdown": true,
          "offset_chars": 1095,
          "count_occurrences": 1
        },
        "asset-615-10-table-stokes-benchmark": {
          "quote": "| 模拟终端速度 v_t | 0.054461 m/s |",
          "resolvable_in_markdown": true,
          "offset_chars": 1375,
          "count_occurrences": 1
        },
        "asset-615-11-test-suite-summary": {
          "quote": "- 12 tests collected, 12 passed, 0 failed",
          "resolvable_in_markdown": true,
          "offset_chars": 1491,
          "count_occurrences": 1
        },
        "asset-615-12-limitations-list": {
          "quote": "4. **润滑力**：未包含近壁颗粒的润滑力模型",
          "resolvable_in_markdown": true,
          "offset_chars": 1803,
          "count_occurrences": 1
        },
        "asset-615-13-table-error-judgement": {
          "quote": "| 终端速度 v_t | Stokes解析 0.05450 m/s | 0.05446 m/s | 0.07% | ✅ YES |",
          "resolvable_in_markdown": true,
          "offset_chars": 1933,
          "count_occurrences": 1
        },
        "asset-615-14-figure-settling_velocity": {
          "quote": "见内嵌图：单颗粒沉降速度时间历程与Stokes解析解对比。",
          "resolvable_in_markdown": true,
          "offset_chars": 1603,
          "count_occurrences": 1
        }
      },
      "identity_facts": {
        "markdown_h1": "SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework",
        "record_title": "SIR-PC2|F06: 3D DEM↔Fluid Bidirectional Coupling Framework",
        "title_consistent": true,
        "scenario_key": "SIR-PC2|F06",
        "mission_id": 706,
        "mission_probe": {
          "endpoint": "GET /api/v1/tensor/missions/706",
          "http_status": 200,
          "mission_repo": "TensorDEM"
        },
        "figures_declared": 1,
        "figure_payload_present": false,
        "markdown_sha256": "sha256:3c1b5f9dc373359c9ca5692b5f822bc1ee8c13b50dc015b9b84c7530e29b7e75",
        "chars": 2125,
        "bytes_utf8": 3310
      },
      "scope": {
        "extraction_performed": false,
        "claims_emitted": 0,
        "verification_performed": false,
        "note": "工序 01 只登记资产与指纹：不抽取知识、不判定 verified、不重跑上游算例；claims 允许为空数组，本单为空。"
      },
      "limitations": [
        "图件字节不可得：figures 记录仅 name/caption，端点 404；未重绘、未代上游补图。",
        "报告正文无代码路径/提交号：代码级绑定不可解析，仅记录级 mission 线索。",
        "pytest 12/12 为报告自述断言，无原始日志工件；本工序不重跑上游，不作为通过证据。",
        "本清单不评价报告结论真伪；误差/守恒量的裁决权在平台验证门。"
      ]
    }
  },
  "claims": []
}
```
