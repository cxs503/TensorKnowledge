# KF-RESULT wp-9083-01 — 资产登记（report_id=9083）

- package_id: `wp-9083-01` ｜ task_type: `01-asset-registration` ｜ lane C ｜ report_id `9083`
- source: `tensor://reports/9083` ｜ field `markdown` ｜ sha256 `345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8`
- chars `258` ｜ utf8 bytes `258` ｜ emitted_at `2026-11-12T01:32:15+00:00`
- 交付仓: TensorKnowledge ｜ status: draft（verification 由平台门计算，本工序不标 verified）
- tags: kf-wp:wp-9083-01, KF-RESULT, asset-registration, CFD-DEM ｜ mission_id 15628

## ① 本工序做了什么（案例介绍）

本工序只做契约里的一件事：**登记 report_id=9083 这一份报告的源资产**，不做抽取、不做报告类型分类、不生成知识claim。

登记对象（案例身份）：

| 项 | 值 |
|---|---|
| report_id | 9083 |
| title（record 字段） | Dense Particle-Fluid CFD-DEM Coupling: Bed Closure Verification |
| scenario_key | p50w2-arb7250-n03-dense-dem-cfd |
| source_uri | tensor://reports/9083 |
| source_field | markdown |
| markdown sha256 | 345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8（与契约 input.source_hash 逐字节一致） |
| chars / bytes_utf8 | 258 / 258 |

共登记 **8** 个资产：其中 3 个在源文中可直接定位（文档本体 + 2 个可定位小节），5 个为「record 声明但不可取回」的图件（声明 5 个，可取回 0 个）。claims 为空数组（契约允许；objective.classify_report_type=false）。

## ② 怎么做的（方法/流程/工具链/关键设置）

流程（全部由 `scripts/kf_register_9083.py` 一次跑完，零手抄）：

1. **取源**：`POST /api/v1/auth/login` 拿 Bearer token，`GET /api/v1/tensor/reports/9083` 取 `markdown` 字段（不走 psql，避免旁路）。
2. **字节级校验**：本地对 `markdown` 重新计算 `sha256`、`chars`、`bytes_utf8`、`lines`；与契约 `source_hash` / `chars=258` 断言相等，不等即 `SystemExit`（硬失败，不产出）。
3. **定位器生成**：每个引文用 `re.finditer` 在 markdown 中求出现次数，**必须恰为 1**，否则脚本拒跑；再换算 char span 与 line span。文档级资产用 `method=document`（quote=整篇 markdown）。
4. **附件探针**：对 record `figures` 里声明的每个图件名调用 `GET /api/v1/tensor/reports/9083/figures/{name}`，如实记录 HTTP 状态、返回字节数与 `detail`；同时检查图件名是否为 markdown 子串。
5. **结构校验**：结果信封对 `schemas/kf_result.v1.schema.json` 用 `jsonschema` 严格校验；资产清单对 `schemas/asset_manifest.v1.schema.json` 校验（该文件被上游钉死在另一个包的 const 上，本工序**仅把 package_id/report_id/task_type/uri 四个 const 重绑到本包**后复用结构体——这是已知偏差，平台侧 schema 优先）。
6. **渲染报告**：本报告由 `docs/kf/wp-9083-01/REPORT.template.md` 模板 + 程序化注入生成；脚本断言全文**恰有 1 个 json 代码块**，且该块 `json.loads` 回来的对象与 `artifacts/kf/wp-9083-01/kf_result.json` 完全相等（防止信封与正文漂移）。

关键设置：只读源（除本包产物目录外不写任何路径）；不触碰其它 report_id；不写 verified；图件缺失不猜测、不补造。

**结果图说明（无图理由）**：本工序是纯登记/文档工序，没有任何物理量计算，画图会是无信息量的装饰图；源报告声明的 5 张图件在平台接口上全部 HTTP 404、无可渲染字节（见 ③ 表），因此本报告**不附图片**，并在此显式声明理由。

## ③ 产出物清单与计算结果（数字表）

| 输出文件 | 要点 |
|---|---|
| `artifacts/kf/wp-9083-01/asset_manifest.json` | 资产清单：source 块 + 8 个资产 + counts + integrity；claims=[] |
| `artifacts/kf/wp-9083-01/kf_result.json` | 结果信封（kf_result.v1）：provenance.source_hash=`345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8`，outputs.asset_manifest.json 内嵌 |
| `runs/kf/wp-9083-01/registration_run.json` | 复算与探针原始记录：哈希复算、figure 探针 HTTP 结果、每个 quote 的出现次数、schema 校验结论 |
| `runs/kf/wp-9083-01/source_markdown.snapshot.md` | 源 markdown 逐字节快照（sha256 与契约一致），供离线复算上游哈希、不依赖网络 |
| `docs/kf/wp-9083-01/REPORT.md` | 本报告（含唯一 json 代码块） |
| `docs/kf/wp-9083-01/REPORT.template.md` | 报告模板（占位符，供复跑重渲染） |
| `scripts/kf_register_9083.py` | 一键复跑脚本（含全部断言） |

登记结果的量化事实：

| 指标 | 值 |
|---|---|
| markdown sha256（本地复算） | `345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8` |
| 与契约 source_hash 一致 | 是（字节级相等） |
| markdown chars / bytes_utf8 | 258 / 258 |
| 登记资产总数 | 8 |
| resolved_in_source | 3 |
| referenced_unresolved | 5 |
| record 声明图件数 | 5 |
| 图件可取回数 | 0 |

图件探针逐条结果（原始值来自 `registration_run.json`）：

| figure_name | HTTP | bytes_returned | detail | retrievable |
|---|---|---|---|---|
| fig1_rz_curve.png | 404 | 29 | figure not found | False |
| fig2_ergun_pressure_drop.png | 404 | 29 | figure not found | False |
| fig3_momentum_conservation.png | 404 | 29 | figure not found | False |
| fig4_grid_convergence.png | 404 | 29 | figure not found | False |
| fig5_superficial_velocity.png | 404 | 29 | figure not found | False |

资产 span 一览（char/line 由脚本计算）：

| asset | locator method | line start | line end | char start | char end | quote chars |
|---|---|---|---|---|---|---|
| A01 | document | 1 | 11 | 0 | 258 | 258 |
| A02 | char_span | 3 | 8 | 39 | 195 | 156 |
| A03 | char_span | 10 | 11 | 197 | 258 | 61 |
| A04 | document | 1 | 11 | 0 | 258 | 258 |
| A05 | document | 1 | 11 | 0 | 258 | 258 |
| A06 | document | 1 | 11 | 0 | 258 | 258 |
| A07 | document | 1 | 11 | 0 | 258 | 258 |
| A08 | document | 1 | 11 | 0 | 258 | 258 |

## ④ 证据定位表（claim/字段 → 原文引文片段）

本包 claims 为空，因此下表定位的是**资产本身**而非结论：每条 locator 的 quote 都是 markdown 的逐字子串且出现次数恰为 1（脚本强制）。

| asset | 字段 | resolution | 原文引文（逐字） | span |
|---|---|---|---|---|
| A01 | markdown of report 9083 (258 chars, 11 lines) | resolved_in_source | `# Dense CFD-DEM Coupling Verification

## Results
- RZ ex...` | L1-11 [0,258) |
| A02 | section starting at '## Results' (156 chars) | resolved_in_source | `## Results
- RZ exponent: n=3.01
- Ergun error: <0.01%
- ...` | L3-8 [39,195) |
| A03 | section starting at '## Tests' (61 chars) | resolved_in_source | `## Tests
31 tests including 3 negative controls, all pass...` | L10-11 [197,258) |
| A04 | fig1_rz_curve.png | referenced_unresolved | `# Dense CFD-DEM Coupling Verification

## Results
- RZ ex...` | L1-11 [0,258) |
| A05 | fig2_ergun_pressure_drop.png | referenced_unresolved | `# Dense CFD-DEM Coupling Verification

## Results
- RZ ex...` | L1-11 [0,258) |
| A06 | fig3_momentum_conservation.png | referenced_unresolved | `# Dense CFD-DEM Coupling Verification

## Results
- RZ ex...` | L1-11 [0,258) |
| A07 | fig4_grid_convergence.png | referenced_unresolved | `# Dense CFD-DEM Coupling Verification

## Results
- RZ ex...` | L1-11 [0,258) |
| A08 | fig5_superficial_velocity.png | referenced_unresolved | `# Dense CFD-DEM Coupling Verification

## Results
- RZ ex...` | L1-11 [0,258) |

图件资产的 quote 是**整篇 markdown**（`method=document`）：因为它们的名字不在 markdown 里、字节也不可取回，用文档级 span 表达「已检索全文、确实不存在」，而不是伪造一个不存在的引用位置。它们的声明出处另存于资产字段 `declaration_source`（`record.figures[i]` 的 name/caption 逐字）。

## ⑤ 注意点与局限

1. **源报告极薄**：markdown 仅 258 字符（2 个小节 + 6 行要点+1 行测试说明），无几何、无参数表、无收敛设置、无误差表。本工序据此只登记资产，不臆造上游没有的内容（`do_not_invent_missing_information`）。
2. **5 张图件全部不可取回**：`GET /tensor/reports/9083/figures/{name}` 对 `.png` 名与去扩展名名统一返回 `404 {"detail":"figure not found"}`；record 里只有 name 与通用 caption（"Verification figure 1..5"），没有 base64、没有文件路径、库里也没有 figure 表。故状态登记为 `referenced_unresolved` 而非 resolved——这是本包最有信息量的结论，下游若要用图必须先补图源。
3. **record.title 与 markdown H1 不一致**：record title 为 `Dense Particle-Fluid CFD-DEM Coupling: Bed Closure Verification`，markdown 首行为 `# Dense CFD-DEM Coupling Verification`（更短）。本包 source.title 采契约/record 值，H1 值另在 A01 的 quote 中逐字保留；不判断哪个是"对的"（超出本工序）。
4. **schema 偏差**：`schemas/asset_manifest.v1.schema.json` 是上游为另一个包本地钉的（`const: wp-448-01/448`），本包只重绑 4 个 const 复用其结构；若平台侧 schema 字段更严，以平台门为准，本产物需按门失败信息修订。
5. **未做/不做**：未做抽取（claims=[]）、未做报告类型分类（契约 false）、未标 verified（verification 属平台门）。除本包目录外未写任何路径，未读其它 report_id。
6. **图件探针的口径**：仅测平台 HTTP 接口层；不排除图件存放在平台未暴露的存储中，但"当前接口取不回"这一事实成立，登记状态以此为准。

误差判定：本包无物理基准量（纯字节/结构登记），唯一定量校验是**哈希与字符数**——sha256 逐字节相等（误差 0），chars 258 与契约 258 相等（误差 0），故 **是否 <3%：不适用（无物理量）；字节级校验为精确相等，严格优于 3%**。图件可取回率 = 0/5 = 0%，该 0% 如实记录，不上调为"部分可取回"。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 判定 | 依据 |
|---|---|---|
| valid_json | 通过 | 脚本 `json.loads` 全部产物；报告内唯一 json 块反序列化后与 `kf_result.json` 相等 |
| schema_pass | 通过 | `jsonschema` 对 `kf_result.v1.schema.json` 严格通过；`asset_manifest.v1.schema.json`（const 重绑后）通过（见 ⑤-4 偏差说明） |
| source_locator_resolvable | 通过 | 全部 8 条 locator 的 quote 在 markdown 中出现次数恰为 1，char/line span 由脚本计算并可复算 |
| source_hash_matches | 通过 | 本地复算 `345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8` == 契约 `sha256:345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8` |
| no_duplicate_ids | 通过 | A01..A8 唯一，脚本内 `len(set)==len` 断言 |
| all_claims_have_evidence_or_explicit_unresolved_status | 通过 | claims=[]（契约允许）；未生成任何无证据结论。唯一"未解决"对象（图件）已以 `referenced_unresolved` + 探针证据显式登记，未粉饰 |

一键复跑：

    TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS python3 scripts/kf_register_9083.py
    # 仅结构复校（不访问平台写路径，只读已有产物 + 离线快照）：
    python3 scripts/kf_register_9083.py --check
    python3 -m pytest tests/test_kf_wp_9083_01.py -q

## 结果信封（唯一 json 代码块，原样提交）

```json
{
  "package_id": "wp-9083-01",
  "task_type": "01-asset-registration",
  "report_id": "9083",
  "provenance": {
    "source_hash": "sha256:345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8",
    "source_field": "markdown",
    "producer": "scripts/kf_register_9083.py",
    "emitted_at": "2026-11-12T01:32:15+00:00",
    "notes": "asset registration only; source_hash recomputed from the platform markdown field, not copied; every locator quote re-verified unique in that markdown"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-9083-01",
      "task_type": "01-asset-registration",
      "report_id": "9083",
      "source": {
        "uri": "tensor://reports/9083",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8",
        "chars": 258,
        "bytes_utf8": 258,
        "title": "Dense Particle-Fluid CFD-DEM Coupling: Bed Closure Verification",
        "scenario_key": "p50w2-arb7250-n03-dense-dem-cfd",
        "platform_status": "published",
        "platform_tags": [
          "CFD-DEM",
          "dense coupling",
          "fluidization",
          "Ergun",
          "Richardson-Zaki"
        ],
        "platform_figures": [
          {
            "name": "fig1_rz_curve.png",
            "caption": "Verification figure 1"
          },
          {
            "name": "fig2_ergun_pressure_drop.png",
            "caption": "Verification figure 2"
          },
          {
            "name": "fig3_momentum_conservation.png",
            "caption": "Verification figure 3"
          },
          {
            "name": "fig4_grid_convergence.png",
            "caption": "Verification figure 4"
          },
          {
            "name": "fig5_superficial_velocity.png",
            "caption": "Verification figure 5"
          }
        ],
        "platform_mission_id": 7742,
        "contract_chars": 258,
        "contract_hash_matches": true
      },
      "counts": {
        "assets": 8,
        "by_class": {
          "report_document": 1,
          "results_block": 1,
          "tests_block": 1,
          "declared_figure": 5
        },
        "by_resolution": {
          "resolved_in_source": 3,
          "referenced_unresolved": 5
        },
        "resolved_in_source": 3,
        "referenced_unresolved": 5,
        "declared_absent": 0,
        "figures_declared": 5,
        "figures_retrievable": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "report_document",
          "label": "markdown of report 9083 (258 chars, 11 lines)",
          "in_report_section": "whole document",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 258,
            "start_line": 1,
            "end_line": 11,
            "quote": "# Dense CFD-DEM Coupling Verification\n\n## Results\n- RZ exponent: n=3.01\n- Ergun error: <0.01%\n- u_mf: 0.01085 m/s, Re_mf=10.83\n- Momentum conservation: 0 (machine precision)\n- All 7 criteria pass\n\n## Tests\n31 tests including 3 negative controls, all passing.",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9083 -> field 'markdown'; sha256 recomputed locally == contract source_hash",
            "result": "resolved"
          },
          "note": "byte-exact match: sha256:345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8 == contract source_hash; chars 258 == contract chars 258"
        },
        {
          "asset_id": "A02",
          "asset_class": "results_block",
          "label": "section starting at '## Results' (156 chars)",
          "in_report_section": "## Results",
          "locator": {
            "method": "char_span",
            "start_char": 39,
            "end_char": 195,
            "start_line": 3,
            "end_line": 8,
            "quote": "## Results\n- RZ exponent: n=3.01\n- Ergun error: <0.01%\n- u_mf: 0.01085 m/s, Re_mf=10.83\n- Momentum conservation: 0 (machine precision)\n- All 7 criteria pass",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "section byte span located in markdown; quote occurs exactly once",
            "result": "resolved"
          },
          "note": "structure pointer only; no numeric extraction performed in this package"
        },
        {
          "asset_id": "A03",
          "asset_class": "tests_block",
          "label": "section starting at '## Tests' (61 chars)",
          "in_report_section": "## Tests",
          "locator": {
            "method": "char_span",
            "start_char": 197,
            "end_char": 258,
            "start_line": 10,
            "end_line": 11,
            "quote": "## Tests\n31 tests including 3 negative controls, all passing.",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "section byte span located in markdown; quote occurs exactly once",
            "result": "resolved"
          },
          "note": "structure pointer only; no numeric extraction performed in this package"
        },
        {
          "asset_id": "A04",
          "asset_class": "declared_figure",
          "label": "fig1_rz_curve.png",
          "in_report_section": "not referenced in markdown; declared only in record field figures[0]",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 258,
            "start_line": 1,
            "end_line": 11,
            "quote": "# Dense CFD-DEM Coupling Verification\n\n## Results\n- RZ exponent: n=3.01\n- Ergun error: <0.01%\n- u_mf: 0.01085 m/s, Re_mf=10.83\n- Momentum conservation: 0 (machine precision)\n- All 7 criteria pass\n\n## Tests\n31 tests including 3 negative controls, all passing.",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9083/figures/fig1_rz_curve.png -> HTTP 404 detail='figure not found'; and figure name is not a substring of the markdown",
            "result": "unresolved"
          },
          "declaration_source": {
            "field": "record",
            "path": "figures[0]",
            "verbatim": {
              "name": "fig1_rz_curve.png",
              "caption": "Verification figure 1"
            },
            "in_markdown": false
          },
          "note": "declared in report record metadata, bytes not retrievable through the platform figure endpoint (HTTP 404); caption is generic text, not evidence"
        },
        {
          "asset_id": "A05",
          "asset_class": "declared_figure",
          "label": "fig2_ergun_pressure_drop.png",
          "in_report_section": "not referenced in markdown; declared only in record field figures[1]",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 258,
            "start_line": 1,
            "end_line": 11,
            "quote": "# Dense CFD-DEM Coupling Verification\n\n## Results\n- RZ exponent: n=3.01\n- Ergun error: <0.01%\n- u_mf: 0.01085 m/s, Re_mf=10.83\n- Momentum conservation: 0 (machine precision)\n- All 7 criteria pass\n\n## Tests\n31 tests including 3 negative controls, all passing.",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9083/figures/fig2_ergun_pressure_drop.png -> HTTP 404 detail='figure not found'; and figure name is not a substring of the markdown",
            "result": "unresolved"
          },
          "declaration_source": {
            "field": "record",
            "path": "figures[1]",
            "verbatim": {
              "name": "fig2_ergun_pressure_drop.png",
              "caption": "Verification figure 2"
            },
            "in_markdown": false
          },
          "note": "declared in report record metadata, bytes not retrievable through the platform figure endpoint (HTTP 404); caption is generic text, not evidence"
        },
        {
          "asset_id": "A06",
          "asset_class": "declared_figure",
          "label": "fig3_momentum_conservation.png",
          "in_report_section": "not referenced in markdown; declared only in record field figures[2]",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 258,
            "start_line": 1,
            "end_line": 11,
            "quote": "# Dense CFD-DEM Coupling Verification\n\n## Results\n- RZ exponent: n=3.01\n- Ergun error: <0.01%\n- u_mf: 0.01085 m/s, Re_mf=10.83\n- Momentum conservation: 0 (machine precision)\n- All 7 criteria pass\n\n## Tests\n31 tests including 3 negative controls, all passing.",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9083/figures/fig3_momentum_conservation.png -> HTTP 404 detail='figure not found'; and figure name is not a substring of the markdown",
            "result": "unresolved"
          },
          "declaration_source": {
            "field": "record",
            "path": "figures[2]",
            "verbatim": {
              "name": "fig3_momentum_conservation.png",
              "caption": "Verification figure 3"
            },
            "in_markdown": false
          },
          "note": "declared in report record metadata, bytes not retrievable through the platform figure endpoint (HTTP 404); caption is generic text, not evidence"
        },
        {
          "asset_id": "A07",
          "asset_class": "declared_figure",
          "label": "fig4_grid_convergence.png",
          "in_report_section": "not referenced in markdown; declared only in record field figures[3]",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 258,
            "start_line": 1,
            "end_line": 11,
            "quote": "# Dense CFD-DEM Coupling Verification\n\n## Results\n- RZ exponent: n=3.01\n- Ergun error: <0.01%\n- u_mf: 0.01085 m/s, Re_mf=10.83\n- Momentum conservation: 0 (machine precision)\n- All 7 criteria pass\n\n## Tests\n31 tests including 3 negative controls, all passing.",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9083/figures/fig4_grid_convergence.png -> HTTP 404 detail='figure not found'; and figure name is not a substring of the markdown",
            "result": "unresolved"
          },
          "declaration_source": {
            "field": "record",
            "path": "figures[3]",
            "verbatim": {
              "name": "fig4_grid_convergence.png",
              "caption": "Verification figure 4"
            },
            "in_markdown": false
          },
          "note": "declared in report record metadata, bytes not retrievable through the platform figure endpoint (HTTP 404); caption is generic text, not evidence"
        },
        {
          "asset_id": "A08",
          "asset_class": "declared_figure",
          "label": "fig5_superficial_velocity.png",
          "in_report_section": "not referenced in markdown; declared only in record field figures[4]",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 258,
            "start_line": 1,
            "end_line": 11,
            "quote": "# Dense CFD-DEM Coupling Verification\n\n## Results\n- RZ exponent: n=3.01\n- Ergun error: <0.01%\n- u_mf: 0.01085 m/s, Re_mf=10.83\n- Momentum conservation: 0 (machine precision)\n- All 7 criteria pass\n\n## Tests\n31 tests including 3 negative controls, all passing.",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "GET http://127.0.0.1:8010/api/v1/tensor/reports/9083/figures/fig5_superficial_velocity.png -> HTTP 404 detail='figure not found'; and figure name is not a substring of the markdown",
            "result": "unresolved"
          },
          "declaration_source": {
            "field": "record",
            "path": "figures[4]",
            "verbatim": {
              "name": "fig5_superficial_velocity.png",
              "caption": "Verification figure 5"
            },
            "in_markdown": false
          },
          "note": "declared in report record metadata, bytes not retrievable through the platform figure endpoint (HTTP 404); caption is generic text, not evidence"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "all locator quotes re-verified unique in markdown (8/8)",
        "hash_recomputed_locally": "sha256:345797326b826eafbe0bc05f0db0fd6da866a6297f5a14fdc6444117fdb6dfd8",
        "hash_matches_contract": true,
        "no_claim_verification": "claims empty by contract (objective.classify_report_type=false, no extraction); nothing marked verified"
      }
    }
  },
  "claims": []
}
```