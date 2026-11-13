# KF-RESULT wp-10344-01

> package `wp-10344-01` · task_type `01-asset-registration` · lane C · report_id `10344`
> scene `p158w1-n03-cfd-dem` · status draft · producer `agent/m15680`
> 一句话：报告 10344 的 markdown 字节哈希与契约一致，登记 17 个源资产（含 5 条附件元数据），
> 22/22 条引文逐字可定位，claims 为空数组（本工序只登记、不抽取）。

## 1. 本工序做了什么

只做 `wp-10344-01`（01-asset-registration）这一道工序，只碰 `report_id=10344`：

1. **取件与身份确认**：从 `tensor://reports/10344`（字段 `markdown`）取原文，重算 sha256，与契约声明的
   `sha256:a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900` 逐位比对 → `true`；
   顺带核 `chars=2888`（契约 2888）与标题、scenario_key（`p158w1-n03-cfd-dem`）一致性。
2. **资产枚举（不抽取）**：把原文中可解析的工件/附件声明登记成资产表——按类 benchmark_entrypoint=1、dataset=1、figure=5、repro_command=1、result_table=2、scope_declaration=1、source_module=5、test_file=1。
3. **分辨率判定（三分类）**：`resolved_in_source`=4（内容就在 markdown 里）、
   `referenced_unresolved`=12（原文点名但平台记录里没有字节：图 PNG、源码模块、测试与 benchmark 入口）、
   `declared_absent`=1（外部数据/DOI/URL 扫描命中 0 次 → 该报告不引用外部数据文件）。
4. **零手抄定位**：为每条资产与每条证据附 char span + 逐字 quote，由脚本断言 quote 是原文子串（22/22 条唯一）。
5. **不抽取知识**：`claims=[]`（契约 `objective.classify_report_type=false`、`no_forced_claim_generation=true`）；未把任何结论标成 verified。

**不做什么**（边界）：不改写上游产物、不重跑原文的 19 个测试与 5 个验证门、不对原文的精度结论做二次判定——那些属于后续工序与平台门。

## 2. 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 工具 / 脚本 | 关键设置 |
|---|---|---|
| 取件 + 登录 | `scripts/kf_wp10344_01_register.py` | `POST /api/v1/auth/login` 拿 Bearer；`GET /api/v1/tensor/reports/10344`；只读 |
| 哈希 | `hashlib.sha256` over `markdown.encode("utf-8")` | `characters` 用 `len(md)`、`bytes` 用 UTF-8 长度（2940 B ≠ 2888 chars，非 ASCII 字符所致） |
| 定位 | 脚本内 `md.count(quote)` / `md.find(quote)` + 行号换算 | 要求 occurrence ≥ 1；occurrence == 1 才标 `unique=true` |
| 附件交叉核 | `record.figures` 的 `name` vs 原文 `<name>.png` 词元 | 5/5 命中；PNG 字节不在记录内 → `referenced_unresolved` |
| 外部引用扫描 | 正则 `https?://\|doi\.org\|\bDOI\b\|\.csv\b\|\.npy\b\|\.h5\b\|\.zip\b\|zenodo\|osf\.io` | 命中 0 次 → `dataset` 资产判 `declared_absent` |
| schema 校验 | `jsonschema` 4.26.0 | 两个 schema 分别校验 envelope 与 manifest |
| 出图 | `matplotlib` 3.10.8（Agg） | 数据全部来自 manifest/source.md，无手填数字 |
| 复跑一键命令 | 见下 | 四脚本 + pytest 串起来，可完整重建本目录 |

```bash
python3 scripts/kf_wp10344_01_register.py && python3 scripts/kf_wp10344_01_figure.py && python3 scripts/kf_wp10344_01_check.py && python3 -m pytest tests/test_kf_wp10344_01.py -q && python3 scripts/kf_wp10344_01_report.py --publish
```

单元测试结果（本包唯一执行的测试）：`python3 -m pytest tests/test_kf_wp10344_01.py -q` → **10 passed**。

## 3. 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-10344-01/asset_manifest.json` | 资产登记表本体：17 个资产、8 个标题、5 条 record.figures 附件元数据；claims=[]（契约允许）；source_hash 与契约一致 |
| `docs/kf/wp-10344-01/kf_result.json` | 结果信封（schemas/kf_result.v1.schema.json）：package_id/task_type/report_id/provenance/outputs，provenance.source_hash = 契约声明哈希 |
| `docs/kf/wp-10344-01/source.md` | 报告 markdown 逐字副本（2888 chars / 2940 bytes UTF-8），供离线重算哈希与定位复核 |
| `docs/kf/wp-10344-01/sha256.txt` | 重算哈希 vs 契约哈希（match=true） |
| `docs/kf/wp-10344-01/locator_check.json` | 22 条引文的逐字定位结果（22/22 可解析，含 char_offset / 行号 / 出现次数） |
| `docs/kf/wp-10344-01/acceptance.json` | acceptance 六项逐条机器判定（schema/locator/hash/duplicate/claims） |
| `docs/kf/wp-10344-01/selfcheck.json` | 登记阶段自检快照（acceptance.json 的前身，保留以便对照） |
| `docs/kf/wp-10344-01/figures/wp10344_01_locator_map.png` | 图 1：17 个资产在原文中的字符区间地图 + 分辨率构成 |
| `docs/kf_result_wp-10344-01.md` | 本报告正文（含唯一一个 json 代码块 = kf_result.json 逐字内容） |
| `schemas/asset_manifest.v1.wp-10344-01.schema.json` | 本包 asset_manifest 形状的固定 schema（使 schema_pass 可复算而非断言） |
| `scripts/kf_wp10344_01_{register,figure,check,report}.py` | 取件/哈希/定位/登记、出图、验收复算、报告装配与发布的四个可复跑脚本 |
| `tests/test_kf_wp10344_01.py` | 离线验收测试（10 例）：重跑 check_all 并固定契约字段 |

## 4. 证据定位表（字段/资产 → 原文逐字引文片段）

- **source_hash** → 契约哈希即 `sha256(markdown UTF-8 bytes)`；本包重算值 `sha256:a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900`（见 `sha256.txt`）。
- **title / scenario_key** → 原文首行标题与记录字段一致：`Point-particle two-way CFD-DEM coupling: Stokes/Added-mass/Momentum/RZ/PG verification` / `p158w1-n03-cfd-dem`。
- **chars** → `2888`（契约 2888），`bytes_utf8` = `2940`。

资产逐条（每条均为原文逐字子串，可由 char span 复现）：

- **A01** `figure` · ## 4. Figures · resolution=`referenced_unresolved` · locator=chars[1842:1870] 行 34-34 · unique=true
  原文逐字："stokes_terminal_velocity.png"
- **A02** `figure` · ## 4. Figures · resolution=`referenced_unresolved` · locator=chars[1872:1898] 行 34-34 · unique=true
  原文逐字："added_mass_oscillation.png"
- **A03** `figure` · ## 4. Figures · resolution=`referenced_unresolved` · locator=chars[1900:1921] 行 34-34 · unique=true
  原文逐字："momentum_exchange.png"
- **A04** `figure` · ## 4. Figures · resolution=`referenced_unresolved` · locator=chars[1923:1942] 行 34-34 · unique=true
  原文逐字："richardson_zaki.png"
- **A05** `figure` · ## 4. Figures · resolution=`referenced_unresolved` · locator=chars[1944:1965] 行 34-34 · unique=true
  原文逐字："pressure_gradient.png"
- **A06** `source_module` · ## 2. Method · resolution=`referenced_unresolved` · locator=chars[768:875] 行 16-16 · unique=true
  原文逐字："`closures.py`: pure functions for all coefficients (Stokes drag, Schiller-Naumann, RZ exponent, added-mass)"
- **A07** `source_module` · ## 2. Method · resolution=`referenced_unresolved` · locator=chars[878:1026] 行 17-17 · unique=true
  原文逐字："`fluid.py`: triply periodic pseudo-spectral solver with exact viscous integrating factor, Leray projection, adjoint trilinear particle-grid transfer"
- **A08** `source_module` · ## 2. Method · resolution=`referenced_unresolved` · locator=chars[1029:1137] 行 18-18 · unique=true
  原文逐字："`particles.py`: vectorised Lagrangian particles with implicit added-mass integration `(m_p + C_A m_a) a = F`"
- **A09** `source_module` · ## 2. Method · resolution=`referenced_unresolved` · locator=chars[1140:1255] 行 19-19 · unique=true
  原文逐字："`coupling.py`: two-way loop with self-response correction, container-frame Galilean shift, momentum budget tracking"
- **A10** `source_module` · ## 2. Method · resolution=`referenced_unresolved` · locator=chars[1258:1312] 行 20-20 · unique=true
  原文逐字："`verification.py`: five closed-form verification faces"
- **A11** `test_file` · ## 7. Reproduction · resolution=`referenced_unresolved` · locator=chars[2750:2820] 行 57-57 · unique=true
  原文逐字："PYTHONPATH=src pytest tests/test_point_cfd_dem.py -v   # 19 tests pass"
- **A12** `benchmark_entrypoint` · ## 7. Reproduction · resolution=`referenced_unresolved` · locator=chars[2821:2883] 行 58-58 · unique=true
  原文逐字："PYTHONPATH=src python benchmarks/point_particle_cfd_dem/run.py"
- **A13** `result_table` · ## 3. Results · resolution=`resolved_in_source` · locator=chars[1405:1479] 行 26-26 · unique=true
  原文逐字："| Stokes terminal velocity | |U - v_t|/v_t ≤ 2% | 1.984% | 2% | **PASS** |"
- **A14** `result_table` · ## 6. Error Assessment · resolution=`resolved_in_source` · locator=chars[2429:2478] 行 48-48 · unique=true
  原文逐字："| Terminal velocity | Stokes v_t | 1.984% | YES |"
- **A15** `repro_command` · ## 7. Reproduction · resolution=`resolved_in_source` · locator=chars[2750:2820] 行 57-57 · unique=true
  原文逐字："PYTHONPATH=src pytest tests/test_point_cfd_dem.py -v   # 19 tests pass"
- **A16** `scope_declaration` · ## 5. Limitations · resolution=`resolved_in_source` · locator=chars[2296:2344] 行 42-42 · unique=true
  原文逐字："5. No walls — wall-bounded coupling out of scope"
- **A17** `dataset` · (whole document) · resolution=`declared_absent` · locator=chars[0:2888] 行 1-59
  原文逐字："# Point-particle (unresolved) two-way CFD-DEM coupling — Verification Report"

## 5. 注意点与局限

1. **registration ≠ verification**：哈希一致只是机械身份核对；原文的 5 个门 `PASS`（如 `1.984%`、`1.95e-14`、`0.816%`）与
   `19 tests pass` 都是**报告自己的声明**，本包未重跑、未复算、未标 verified。原文自身也承认一处超 3%：
   `8.681%`（Richardson-Zaki，报告内 10% 门内）——本包只登记该行，不作精度裁决。
2. **12/17 资产为 `referenced_unresolved`**：5 个图只有 `record.figures` 的 name/caption 元数据、
   5 个源码模块只给了裸文件名、测试与 benchmark 入口只给路径文本；生产仓不在本工作树内，无法解析出字节。这是**如实的分辨率状态**，
   不是登记失败；下游若要复算需先取得生产仓。
3. **模块名是裸文件名**（`closures.py` 等，无目录），因此无法据此唯一定位路径；`in_report_section` 只标所在章节。
4. **外部数据引用扫描是模式匹配**（0 命中），语义等价于"原文未出现 URL/DOI/数据文件后缀"；
   若原文用别的方式引用数据，此检查会漏。
5. **本包无 claim 级产出**：`claims=[]` 是契约允许的完整结果，不得为填指标造知识。
6. **图表说明**：图 1 是登记元数据的可视化（字符区间/分辨率构成），不是物理场结果；本工序不产生物理场量，故无云图/SHM 图。
7. **字符与字节不可混用**：2888 chars / 2940 B；哈希按字节算，locator 按字符算（含 `≠`、`ρ`、`Δ` 等非 ASCII）。
8. **scope**：只处理 report 10344；脚本与测试都断言不出现其它 `tensor://reports/<id>`。

## 6. 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✓ | 两份 JSON 均 json.load 成功 |
| schema_pass | ✓ | kf_result.json → schemas/kf_result.v1.schema.json；asset_manifest.json → schemas/asset_manifest.v1.wp-10344-01.schema.json（jsonschema 校验） |
| source_locator_resolvable | ✓ | 17 个资产的字符区间切片 == quote 且 start_char==md.find(quote)；22 条引文全部可解析 |
| source_hash_matches | ✓ | 重算 sha256:a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900 == 契约 sha256:a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900 |
| no_duplicate_ids | ✓ | 17 个 asset_id 唯一 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims=[]（契约允许空数组，未造知识）；同时全部资产都带 locator（char span + 逐字 quote） |

`failed_items = []` → **全部通过**。

## 7. KF-RESULT JSON（本报告唯一的一个 json 代码块，原样提交）

```json
{
  "package_id": "wp-10344-01",
  "task_type": "01-asset-registration",
  "report_id": "10344",
  "provenance": {
    "source_hash": "sha256:a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900",
    "source_field": "markdown",
    "producer": "agent/m15680",
    "emitted_at": "2026-11-12T01:41:09+00:00",
    "notes": "source_hash recomputed with hashlib.sha256 over the report markdown bytes fetched from GET /api/v1/tensor/reports/10344; equals the contract hash. Hash equality is a mechanical identity check only: no claim is marked verified, verification stays with the platform gate."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-10344-01",
      "task_type": "01-asset-registration",
      "report_id": "10344",
      "source_uri": "tensor://reports/10344",
      "source_field": "markdown",
      "source_hash": "sha256:a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900",
      "source_hash_expected": "sha256:a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900",
      "source_hash_matches": true,
      "hash_algorithm": "sha256 over UTF-8 bytes of the markdown field",
      "title": "Point-particle two-way CFD-DEM coupling: Stokes/Added-mass/Momentum/RZ/PG verification",
      "title_matches_contract": true,
      "scenario_key": "p158w1-n03-cfd-dem",
      "scenario_key_expected": "p158w1-n03-cfd-dem",
      "scenario_key_matches_contract": true,
      "source_mission_id": 8040,
      "source_status": "published",
      "source_created_at": "2026-11-10T02:54:30.170372+00:00",
      "source_tags": [
        "CFD-DEM",
        "point-particle",
        "two-way-coupling",
        "verification",
        "TensorDEM"
      ],
      "chars": 2888,
      "chars_expected": 2888,
      "chars_match_contract": true,
      "bytes_utf8": 2940,
      "heading_count": 8,
      "headings": [
        "# Point-particle (unresolved) two-way CFD-DEM coupling — Verification Report",
        "## 1. Case Introduction",
        "## 2. Method",
        "## 3. Results",
        "## 4. Figures",
        "## 5. Limitations",
        "## 6. Error Assessment",
        "## 7. Reproduction"
      ],
      "attachments": [
        {
          "name": "stokes_terminal_velocity",
          "caption": "Figure: stokes_terminal_velocity",
          "origin": "record.figures",
          "markdown_token": "stokes_terminal_velocity.png",
          "markdown_token_resolvable": true
        },
        {
          "name": "added_mass_oscillation",
          "caption": "Figure: added_mass_oscillation",
          "origin": "record.figures",
          "markdown_token": "added_mass_oscillation.png",
          "markdown_token_resolvable": true
        },
        {
          "name": "momentum_exchange",
          "caption": "Figure: momentum_exchange",
          "origin": "record.figures",
          "markdown_token": "momentum_exchange.png",
          "markdown_token_resolvable": true
        },
        {
          "name": "richardson_zaki",
          "caption": "Figure: richardson_zaki",
          "origin": "record.figures",
          "markdown_token": "richardson_zaki.png",
          "markdown_token_resolvable": true
        },
        {
          "name": "pressure_gradient",
          "caption": "Figure: pressure_gradient",
          "origin": "record.figures",
          "markdown_token": "pressure_gradient.png",
          "markdown_token_resolvable": true
        }
      ],
      "attachments_note": "figure name/caption metadata taken from record.figures; PNG payloads are neither downloaded nor checked in by this package",
      "external_reference_scan": {
        "pattern": "https?://|doi\\.org|\\bDOI\\b|\\.csv\\b|\\.npy\\b|\\.h5\\b|\\.zip\\b|zenodo|osf\\.io",
        "hits": 0,
        "distinct": []
      },
      "counts": {
        "assets": 17,
        "by_class": {
          "figure": 5,
          "source_module": 5,
          "test_file": 1,
          "benchmark_entrypoint": 1,
          "result_table": 2,
          "repro_command": 1,
          "scope_declaration": 1,
          "dataset": 1
        },
        "by_resolution": {
          "referenced_unresolved": 12,
          "resolved_in_source": 4,
          "declared_absent": 1
        },
        "resolved_in_source": 4,
        "referenced_unresolved": 12,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "figure",
          "label": "stokes_terminal_velocity.png",
          "in_report_section": "## 4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1842,
            "end_char": 1870,
            "start_line": 34,
            "end_line": 34,
            "quote": "stokes_terminal_velocity.png",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1); attachment metadata cross-checked against record.figures",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "figure named in the report; record.figures carries name+caption metadata only, the PNG bytes are not in the platform record",
          "attachment_metadata_present": true
        },
        {
          "asset_id": "A02",
          "asset_class": "figure",
          "label": "added_mass_oscillation.png",
          "in_report_section": "## 4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1872,
            "end_char": 1898,
            "start_line": 34,
            "end_line": 34,
            "quote": "added_mass_oscillation.png",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1); attachment metadata cross-checked against record.figures",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "figure named in the report; record.figures metadata only, no PNG bytes in the record",
          "attachment_metadata_present": true
        },
        {
          "asset_id": "A03",
          "asset_class": "figure",
          "label": "momentum_exchange.png",
          "in_report_section": "## 4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1900,
            "end_char": 1921,
            "start_line": 34,
            "end_line": 34,
            "quote": "momentum_exchange.png",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1); attachment metadata cross-checked against record.figures",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "figure named in the report; record.figures metadata only, no PNG bytes in the record",
          "attachment_metadata_present": true
        },
        {
          "asset_id": "A04",
          "asset_class": "figure",
          "label": "richardson_zaki.png",
          "in_report_section": "## 4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1923,
            "end_char": 1942,
            "start_line": 34,
            "end_line": 34,
            "quote": "richardson_zaki.png",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1); attachment metadata cross-checked against record.figures",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "figure named in the report; record.figures metadata only, no PNG bytes in the record",
          "attachment_metadata_present": true
        },
        {
          "asset_id": "A05",
          "asset_class": "figure",
          "label": "pressure_gradient.png",
          "in_report_section": "## 4. Figures",
          "locator": {
            "method": "char_span",
            "start_char": 1944,
            "end_char": 1965,
            "start_line": 34,
            "end_line": 34,
            "quote": "pressure_gradient.png",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1); attachment metadata cross-checked against record.figures",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "figure named in the report; record.figures metadata only, no PNG bytes in the record",
          "attachment_metadata_present": true
        },
        {
          "asset_id": "A06",
          "asset_class": "source_module",
          "label": "closures.py",
          "in_report_section": "## 2. Method",
          "locator": {
            "method": "char_span",
            "start_char": 768,
            "end_char": 875,
            "start_line": 16,
            "end_line": 16,
            "quote": "`closures.py`: pure functions for all coefficients (Stokes drag, Schiller-Naumann, RZ exponent, added-mass)",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "module cited by bare filename (no directory); producing repo is not part of this worktree, so the file is not resolvable from the platform record"
        },
        {
          "asset_id": "A07",
          "asset_class": "source_module",
          "label": "fluid.py",
          "in_report_section": "## 2. Method",
          "locator": {
            "method": "char_span",
            "start_char": 878,
            "end_char": 1026,
            "start_line": 17,
            "end_line": 17,
            "quote": "`fluid.py`: triply periodic pseudo-spectral solver with exact viscous integrating factor, Leray projection, adjoint trilinear particle-grid transfer",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "module cited by bare filename; not resolvable from the platform record"
        },
        {
          "asset_id": "A08",
          "asset_class": "source_module",
          "label": "particles.py",
          "in_report_section": "## 2. Method",
          "locator": {
            "method": "char_span",
            "start_char": 1029,
            "end_char": 1137,
            "start_line": 18,
            "end_line": 18,
            "quote": "`particles.py`: vectorised Lagrangian particles with implicit added-mass integration `(m_p + C_A m_a) a = F`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "module cited by bare filename; not resolvable from the platform record"
        },
        {
          "asset_id": "A09",
          "asset_class": "source_module",
          "label": "coupling.py",
          "in_report_section": "## 2. Method",
          "locator": {
            "method": "char_span",
            "start_char": 1140,
            "end_char": 1255,
            "start_line": 19,
            "end_line": 19,
            "quote": "`coupling.py`: two-way loop with self-response correction, container-frame Galilean shift, momentum budget tracking",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "module cited by bare filename; not resolvable from the platform record"
        },
        {
          "asset_id": "A10",
          "asset_class": "source_module",
          "label": "verification.py",
          "in_report_section": "## 2. Method",
          "locator": {
            "method": "char_span",
            "start_char": 1258,
            "end_char": 1312,
            "start_line": 20,
            "end_line": 20,
            "quote": "`verification.py`: five closed-form verification faces",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "module cited by bare filename; not resolvable from the platform record"
        },
        {
          "asset_id": "A11",
          "asset_class": "test_file",
          "label": "tests/test_point_cfd_dem.py",
          "in_report_section": "## 7. Reproduction",
          "locator": {
            "method": "char_span",
            "start_char": 2750,
            "end_char": 2820,
            "start_line": 57,
            "end_line": 57,
            "quote": "PYTHONPATH=src pytest tests/test_point_cfd_dem.py -v   # 19 tests pass",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "test path quoted verbatim; the stated 19 passing cases are a claim of the source report, NOT re-executed in this package"
        },
        {
          "asset_id": "A12",
          "asset_class": "benchmark_entrypoint",
          "label": "benchmarks/point_particle_cfd_dem/run.py",
          "in_report_section": "## 7. Reproduction",
          "locator": {
            "method": "char_span",
            "start_char": 2821,
            "end_char": 2883,
            "start_line": 58,
            "end_line": 58,
            "quote": "PYTHONPATH=src python benchmarks/point_particle_cfd_dem/run.py",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "unresolved"
          },
          "note": "benchmark entry point quoted verbatim; not executed in this package"
        },
        {
          "asset_id": "A13",
          "asset_class": "result_table",
          "label": "verification gate table (5 gates, measured vs threshold)",
          "in_report_section": "## 3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 1405,
            "end_char": 1479,
            "start_line": 26,
            "end_line": 26,
            "quote": "| Stokes terminal velocity | |U - v_t|/v_t ≤ 2% | 1.984% | 2% | **PASS** |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "resolved"
          },
          "note": "table body present inline in the markdown; rows are verbatim-resolvable"
        },
        {
          "asset_id": "A14",
          "asset_class": "result_table",
          "label": "error assessment table (5 quantities, error, <3%? verdict)",
          "in_report_section": "## 6. Error Assessment",
          "locator": {
            "method": "char_span",
            "start_char": 2429,
            "end_char": 2478,
            "start_line": 48,
            "end_line": 48,
            "quote": "| Terminal velocity | Stokes v_t | 1.984% | YES |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "resolved"
          },
          "note": "table body present inline; row A15-cited 8.681% row is the only non-<3% entry"
        },
        {
          "asset_id": "A15",
          "asset_class": "repro_command",
          "label": "PYTHONPATH=src pytest tests/test_point_cfd_dem.py -v",
          "in_report_section": "## 7. Reproduction",
          "locator": {
            "method": "char_span",
            "start_char": 2750,
            "end_char": 2820,
            "start_line": 57,
            "end_line": 57,
            "quote": "PYTHONPATH=src pytest tests/test_point_cfd_dem.py -v   # 19 tests pass",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "resolved"
          },
          "note": "command text resolved inline; execution NOT performed here (unit_cmd out of this package's scope)"
        },
        {
          "asset_id": "A16",
          "asset_class": "scope_declaration",
          "label": "no walls / no particle-particle contacts / periodic box (out-of-scope list)",
          "in_report_section": "## 5. Limitations",
          "locator": {
            "method": "char_span",
            "start_char": 2296,
            "end_char": 2344,
            "start_line": 42,
            "end_line": 42,
            "quote": "5. No walls — wall-bounded coupling out of scope",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "verbatim substring of markdown (occurrence count >= 1)",
            "occurrences": 1,
            "result": "resolved"
          },
          "note": "limitation list is the asset-level applicability boundary of every other asset"
        },
        {
          "asset_id": "A17",
          "asset_class": "dataset",
          "label": "none declared",
          "in_report_section": "(whole document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 2888,
            "start_line": 1,
            "end_line": 59,
            "quote": "# Point-particle (unresolved) two-way CFD-DEM coupling — Verification Report",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "regex scan https?://|doi\\.org|\\bDOI\\b|\\.csv\\b|\\.npy\\b|\\.h5\\b|\\.zip\\b|zenodo|osf\\.io over the whole markdown",
            "hits": 0,
            "result": "absent"
          },
          "note": "the report references no external data file, DOI or repository URL; inputs are analytic"
        }
      ],
      "claims": [],
      "claims_note": "claims intentionally empty: objective.register_assets=true and classify_report_type=false for this package; no extraction, no invented claims",
      "integrity": {
        "quote_uniqueness": {
          "quotes": 22,
          "unique_quotes": 22,
          "all_resolvable": true
        },
        "hash_recomputed_locally": "sha256:a125a5396015600c7865e9357d613ab245c0499a45ba5fbf51f9fdddc59fc900",
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
