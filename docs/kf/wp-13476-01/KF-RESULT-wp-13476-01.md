# KF-RESULT wp-13476-01

## (1) 本工序做了什么

本工作包 `wp-13476-01`（`01-asset-registration`, lane C）只做一件事：把 **report_id=13476** 的源资产登记下来
——确认 `report_id` 与其 `markdown` 字段的字节哈希，逐字定位报告声明的图/工件/表，产出 `asset_manifest.json`。
**不做抽取**（`objective.classify_report_type=false`）；**不标 verified**（验证归平台门）；`claims` 为空数组。
全程只读写 report 13476，未触及其它 report_id。

## (2) 怎么做的（步骤/工具/关键设置）

1. `GET /api/v1/tensor/reports/13476` 取 `markdown`（Bearer = `$TENSOR_AGENT_USER` 登录 token），对
   **utf-8 字节**做 sha256：本地重算 `sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0`，契约 `sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0` -> **一致**；
   `chars=12871`（契约 12871）、`bytes_utf8=13103`、`lines=321`。
2. 资产发现全程序化（零手抄）：(a) 源文档本身；(b) `record.figures` 声明的 3 张图；
   (c) 正文反引号码内的路径引用（正则只认带扩展名路径）；(d) fenced code block（代码/公式）；
   (e) markdown 表格。每个资产带定位器（start/end char、start/end line、逐字 quote、唯一性）：
   `char_span` 型断言 `md[start:end] == quote`；`document` 型（A01）断言覆盖 chars 0-12871 且以首行为锚；
   `record_json_path` 型（A02-A04，仅元数据图）锚在 `record.figures[i].caption`，**不虚构 markdown 偏移**。
3. 可解析性判定：探测 `GET /tensor/reports/13476/{artifacts,figures,assets}` -> 全部 404
   （记录于 `work/wp-13476-01/source/platform_probes.json`），故图只有元数据，**不声明任何图字节/图哈希**；
   正文路径指向 TensorDEM 仓（`benchmarks/`、`artifacts/`、`docs/`），不在本工作树 -> 登记为
   `referenced_unresolved` 并保留逐字定位（丢弃=禁止）。
4. 六项 acceptance 由 `verify` 子命令机器判定，定位器**对 fresh fetch 复核**（不是对缓存副本）。

## (3) 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-13476-01/asset_manifest.json` | 主产物：17 个资产 = 9 in-source + 8 unresolved；`claims=[]` 附显式理由 |
| `docs/kf/wp-13476-01/kf_result.json` | kf_result.v1 信封，`provenance.source_hash` = 实测哈希 |
| `docs/kf/wp-13476-01/verification.json` | 6 项自检（`all_pass=True`） |
| `docs/kf/wp-13476-01/asset_manifest.schema.json` | 本地钉住的 manifest 形状（否则 `schema_pass` 只是断言） |
| `docs/kf/wp-13476-01/source_markdown.md` | 原文逐字副本，供离线复核定位 |
| `docs/kf/wp-13476-01/figures/asset_locator_map.png` | 资产生成图：文档字符轴上的定位器分布 + 哈希一致性面板 |
| `scripts/kf_wp13476_01_register.py` | 一键复跑脚本（fetch/build/envelope/verify/figure/report/publish） |

| id | class | label | 节 | resolution |
|---|---|---|---|---|
| A01 | source_document | `report 13476 markdown (source_field=markdown)` | whole document | resolved_in_source |
| A02 | figure_reference | `settling_velocity_correction.png` | record.figures (declared metad | referenced_unresolved |
| A03 | figure_reference | `repose_angle_expected.png` | record.figures (declared metad | referenced_unresolved |
| A04 | figure_reference | `coordination_number_expected.png` | record.figures (declared metad | referenced_unresolved |
| A05 | in_source_table | `markdown table L66-L72` | 2. Implementation | resolved_in_source |
| A06 | in_source_expression | `fenced none block L75-L78` | 2. Implementation | resolved_in_source |
| A07 | in_source_expression | `fenced none block L107-L115` | 3. Results | resolved_in_source |
| A08 | in_source_expression | `fenced none block L119-L122` | 3. Results | resolved_in_source |
| A09 | in_source_table | `markdown table L134-L138` | 3. Results | resolved_in_source |
| A10 | in_source_table | `markdown table L146-L152` | 3. Results | resolved_in_source |
| A11 | in_source_table | `markdown table L162-L168` | 3. Results | resolved_in_source |
| A12 | source_code_reference | `particle/clump.py` | 4. Discussion | referenced_unresolved |
| A13 | source_code_reference | `particle/clump_dem.py` | 4. Discussion | referenced_unresolved |
| A14 | source_code_reference | `benchmarks/clump_shape_verification/p447w2_n02_clump_shape_study.py` | 7. Artifacts & Reproducibility | referenced_unresolved |
| A15 | data_artifact_reference | `artifacts/dem/clump_shape_verification/clump_shape_verification_results.json` | 7. Artifacts & Reproducibility | referenced_unresolved |
| A16 | code_reproduction_snippet | `fenced python block L287-L305` | 7. Artifacts & Reproducibility | resolved_in_source |
| A17 | document_reference | `docs/clump_multisphere_particles.md` | 8. References | referenced_unresolved |

## (4) 证据定位表

所有引文均为 markdown 原文子串（平台可独立重算 sha256 与子串）：

| claim/字段 | 所属节 | 原文引文片段（逐字）+ 定位 |
|---|---|---|
| A01 `report 13476 markdown (source_field=markdown)` | whole document | markdown `# DEM Clump Shape Effect Verification Report (p447w2-n02)` (L1-321, chars 0-12871, unique=true) |
| A02 `settling_velocity_correction.png` | record.figures (declared metadata) | record `Settling Velocity Correction` (L1-321, chars 0-12871, unique=true) |
| A03 `repose_angle_expected.png` | record.figures (declared metadata) | record `Repose Angle Expected` (L1-321, chars 0-12871, unique=true) |
| A04 `coordination_number_expected.png` | record.figures (declared metadata) | record `Coordination Number Expected` (L1-321, chars 0-12871, unique=true) |
| A05 `markdown table L66-L72` | 2. Implementation | markdown `| ψ_target | Aspect ratio a/b | n_spheres | Clump length [mm] | / |----------|---------...` (L66-72, chars 2610-3057, unique=true) |
| A06 `fenced none block L75-L78` | 2. Implementation | markdown ```` / ψ = A_eq / A_ellipsoid / A_ellipsoid = 2πb²(1 + (a/be)arcsin(e)), e = √(1 - b²/a²...` (L75-78, chars 3111-3199, unique=true) |
| A07 `fenced none block L107-L115` | 3. Results | markdown ```` / Step  1: ω_max = 3.3 × 10⁰ rad/s / Step  2: ω_max = 1.4 × 10⁴ rad/s / Step  3: ω_...` (L107-115, chars 4000-4206, unique=true) |
| A08 `fenced none block L119-L122` | 3. Results | markdown ```` / ω_dot = I⁻¹ · (τ - ω × (I · ω)) / ω_new = ω + ω_dot · dt / ```` (L119-122, chars 4271-4333, unique=true) |
| A09 `markdown table L134-L138` | 3. Results | markdown `| Metric | Value | Target | Status | / |--------|-------|--------|--------| / | θ_mean ...` (L134-138, chars 5010-5216, unique=true) |
| A10 `markdown table L146-L152` | 3. Results | markdown `| ψ | K_theoretical | v_terminal [m/s] | v_stokes [m/s] | / |---|---------------|------...` (L146-152, chars 5606-5891, unique=true) |
| A11 `markdown table L162-L168` | 3. Results | markdown `| ψ | Z_expected | Z_sphere | ΔZ | / |---|------------|----------|----| / | 1.0 | 6.0 |...` (L162-168, chars 6268-6471, unique=true) |
| A12 `particle/clump.py` | 4. Discussion | markdown `1. **Infrastructure**: The TensorDEM clump geometry module (`particle/clump.py`) correc...` (L180-180, chars 6735-6883, unique=true) |
| A13 `particle/clump_dem.py` | 4. Discussion | markdown `1. **Multi-sphere clump DEM**: The clump dynamics engine (`particle/clump_dem.py`) has ...` (L187-187, chars 7224-7399, unique=true) |
| A14 `benchmarks/clump_shape_verification/p447w2_n02_clump_shape_study.py` | 7. Artifacts & Reproducibility | markdown `- **Study script**: `benchmarks/clump_shape_verification/p447w2_n02_clump_shape_study.py`` (L274-274, chars 10964-11053, unique=true) |
| A15 `artifacts/dem/clump_shape_verification/clump_shape_verification_results.json` | 7. Artifacts & Reproducibility | markdown `- **Results JSON**: `artifacts/dem/clump_shape_verification/clump_shape_verification_re...` (L280-280, chars 11183-11281, unique=true) |
| A16 `fenced python block L287-L305` | 7. Artifacts & Reproducibility | markdown ````python / from tensordem.particle.clump import ellipsoid_clump / from tensordem.parti...` (L287-305, chars 11424-12175, unique=true) |
| A17 `docs/clump_multisphere_particles.md` | 8. References | markdown `4. TensorDEM documentation: `docs/clump_multisphere_particles.md`` (L314-314, chars 12580-12645, unique=true) |

源身份事实（逐字，行号 1-based；A01 的 `quote` 为整篇 markdown，此处不重复粘贴）：

| fact | 行 | 原文引文（逐字） | quote sha256（前 16） |
|---|---|---|---|
| title | 1 | `# DEM Clump Shape Effect Verification Report (p447w2-n02)` | `2f1f89333f1b78c3` |
| mission-line | 3 | `**Mission**: p447w2-n02  ` | `b931e76a6921c6ca` |
| status-line | 5 | `**Status**: PARTIAL SUCCESS with critical bug discovery  ` | `abc4d9f05d35a5ef` |
| honest-assessment-line | 23 | `---` | `cb3f91d54eee30e5` |
| artifacts-header | 270 | `## 7. Artifacts & Reproducibility` | `2c313a4a85718f7a` |

A01 覆盖 chars 0-12871（整篇 markdown），`slice_matches_quote=true` 由 verify 对 fresh fetch 复核。

## (5) 注意点与局限

- **图字节不可得**：3 张图只在 `record.figures` 有 name+caption，平台无 artifact 端点（探测全 404），
  因此只登记元数据、不声称图内容或图哈希——这是 WITHHELD，不是"没有图"。
- **路径引用不可解析**：`benchmarks/...`、`artifacts/dem/...`、`docs/clump_multisphere_particles.md`
  属 TensorDEM 仓，本工作树无此内容；登记为 `referenced_unresolved`，需下游包在 TensorDEM 检出内二次解析。
- **零抽取**：不判断报告结论真假、不生成 claim；`claims=[]` 是契约允许的完整结果而非遗漏，
  报告本身的 honest-FAIL 内容留给下游抽取/审计工序。
- **定位口径**：行号 = `markdown.rstrip('\n').split('\n')` 的 1-based 逻辑行；字符偏移按 unicode
  字符计（非字节），与平台按字符切片校验的口径一致。

## (6) 自检（逐条对照 acceptance）

| acceptance | 结果 | 证据 |
|---|---|---|
| valid_json | PASS | "asset_manifest.json + kf_result.json both parse" |
| schema_pass | PASS | {"kf_result.v1": "valid", "asset_manifest (pinned)": "valid"} |
| source_locator_resolvable | PASS | {"locators": 17, "markdown_locators": 14, "record_locators": 3, "unresolvable": [], "checked_against": "fresh GET /tensor/reports/13476 (markdown slice + record.figures)"} |
| source_hash_matches | PASS | {"recomputed": "sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0", "contract": "sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0", "manifest": "sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba |
| no_duplicate_ids | PASS | {"assets": 17, "distinct": 17, "duplicates": []} |
| all_claims_have_evidence_or_explicit_unresolved_status | PASS | {"claims": 0, "empty_claims_with_explicit_reason": true, "reason": "Contract wp-13476-01 sets objective.register_assets=true, objective.classify_report_type=false, constraints.no_forced_claim_generation=true, and notes state 'claims 允许为空数组' |

一键复跑（worktree 根目录执行）：

```
python3 scripts/kf_wp13476_01_register.py all
```

（`all` = fetch+build+envelope+verify+figure+report；`publish` 单独执行以投递本报告。）

```json
{
  "package_id": "wp-13476-01",
  "task_type": "01-asset-registration",
  "report_id": "13476",
  "provenance": {
    "source_hash": "sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0",
    "source_field": "markdown",
    "source_uri": "tensor://reports/13476",
    "producer": "kf-worker/m15760",
    "emitted_at": "2026-11-12T02:32:30Z",
    "chars": 12871,
    "bytes_utf8": 13103,
    "hash_matches_contract": true,
    "tool": "scripts/kf_wp13476_01_register.py",
    "notes": "Hash computed locally over the utf-8 bytes of the markdown field returned by GET /tensor/reports/13476; no other report_id was read. Registration only: no claims, no verified marks."
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "manifest_version": "1.0",
      "package_id": "wp-13476-01",
      "task_type": "01-asset-registration",
      "report_id": "13476",
      "lane": "C",
      "generated_at": "2026-11-12T02:32:30Z",
      "producer": "kf-worker/m15760",
      "objective": {
        "register_assets": true,
        "classify_report_type": false,
        "extraction_performed": false
      },
      "source": {
        "uri": "tensor://reports/13476",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0",
        "contract_hash": "sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0",
        "hash_matches_contract": true,
        "chars": 12871,
        "contract_chars": 12871,
        "chars_match_contract": true,
        "bytes_utf8": 13103,
        "lines": 321,
        "has_crlf": false,
        "has_trailing_newline": true,
        "line_counting": "logical lines = markdown.rstrip('\\n').split('\\n'); 1-based",
        "title": "DEM Clump Shape Effect Verification (p447w2-n02): Partial Success with Critical Bug Discovery",
        "title_matches_contract": true,
        "scenario_key": "p447w2-n02",
        "scenario_matches_contract": true,
        "platform_record_id": 13476,
        "platform_status": "published",
        "platform_mission_id": 13998,
        "platform_created_at": "2026-11-11T07:03:41.177940+00:00",
        "platform_tags": [
          "DEM",
          "clump",
          "shape-effect",
          "sphericity",
          "repose-angle",
          "bug-discovery",
          "honest-fail"
        ],
        "platform_figures": [
          {
            "name": "settling_velocity_correction.png",
            "caption": "Settling Velocity Correction"
          },
          {
            "name": "repose_angle_expected.png",
            "caption": "Repose Angle Expected"
          },
          {
            "name": "coordination_number_expected.png",
            "caption": "Coordination Number Expected"
          }
        ],
        "fetched_via": "GET /api/v1/tensor/reports/13476",
        "platform_artifact_probes": {
          "/tensor/reports/13476/artifacts": {
            "path": "/tensor/reports/13476/artifacts",
            "http_status": 404
          },
          "/tensor/reports/13476/figures": {
            "path": "/tensor/reports/13476/figures",
            "http_status": 404
          },
          "/tensor/reports/13476/assets": {
            "path": "/tensor/reports/13476/assets",
            "http_status": 404
          }
        }
      },
      "counts": {
        "assets": 17,
        "by_class": {
          "code_reproduction_snippet": 1,
          "data_artifact_reference": 1,
          "document_reference": 1,
          "figure_reference": 3,
          "in_source_expression": 3,
          "in_source_table": 4,
          "source_code_reference": 3,
          "source_document": 1
        },
        "by_resolution": {
          "referenced_unresolved": 8,
          "resolved_in_source": 9
        },
        "resolved_in_source": 9,
        "referenced_unresolved": 8,
        "declared_absent": 0,
        "figures_declared_in_record": 3,
        "claims": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "source_document",
          "label": "report 13476 markdown (source_field=markdown)",
          "in_report_section": "whole document",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 12871,
            "start_line": 1,
            "end_line": 321,
            "quote": "# DEM Clump Shape Effect Verification Report (p447w2-n02)",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /tensor/reports/13476 -> markdown field",
            "result": "resolved"
          },
          "note": "Canonical asset of this package: sha256 over the utf-8 markdown bytes is recomputed on every run and compared with provenance.source_hash."
        },
        {
          "asset_id": "A02",
          "asset_class": "figure_reference",
          "label": "settling_velocity_correction.png",
          "in_report_section": "record.figures (declared metadata)",
          "locator": {
            "method": "record_json_path",
            "source_field": "record",
            "record_path": "figures[0].caption",
            "start_char": 0,
            "end_char": 12871,
            "start_line": 1,
            "end_line": 321,
            "quote": "Settling Velocity Correction",
            "unique": true,
            "occurrences_in_source": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure name in markdown=False; platform artifact endpoints probed (r13476/artifacts=404, r13476/assets=404, r13476/figures=404)",
            "result": "unresolved"
          },
          "note": "Declared in record.figures with caption 'Settling Velocity Correction'; the platform serves no artifact/figures endpoint for this report, so no bytes and no figure hash are registered."
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_reference",
          "label": "repose_angle_expected.png",
          "in_report_section": "record.figures (declared metadata)",
          "locator": {
            "method": "record_json_path",
            "source_field": "record",
            "record_path": "figures[1].caption",
            "start_char": 0,
            "end_char": 12871,
            "start_line": 1,
            "end_line": 321,
            "quote": "Repose Angle Expected",
            "unique": true,
            "occurrences_in_source": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure name in markdown=False; platform artifact endpoints probed (r13476/artifacts=404, r13476/assets=404, r13476/figures=404)",
            "result": "unresolved"
          },
          "note": "Declared in record.figures with caption 'Repose Angle Expected'; the platform serves no artifact/figures endpoint for this report, so no bytes and no figure hash are registered."
        },
        {
          "asset_id": "A04",
          "asset_class": "figure_reference",
          "label": "coordination_number_expected.png",
          "in_report_section": "record.figures (declared metadata)",
          "locator": {
            "method": "record_json_path",
            "source_field": "record",
            "record_path": "figures[2].caption",
            "start_char": 0,
            "end_char": 12871,
            "start_line": 1,
            "end_line": 321,
            "quote": "Coordination Number Expected",
            "unique": true,
            "occurrences_in_source": 0
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "figure name in markdown=False; platform artifact endpoints probed (r13476/artifacts=404, r13476/assets=404, r13476/figures=404)",
            "result": "unresolved"
          },
          "note": "Declared in record.figures with caption 'Coordination Number Expected'; the platform serves no artifact/figures endpoint for this report, so no bytes and no figure hash are registered."
        },
        {
          "asset_id": "A05",
          "asset_class": "in_source_table",
          "label": "markdown table L66-L72",
          "in_report_section": "2. Implementation",
          "locator": {
            "method": "char_span",
            "start_char": 2610,
            "end_char": 3057,
            "start_line": 66,
            "end_line": 72,
            "quote": "| ψ_target | Aspect ratio a/b | n_spheres | Clump length [mm] |\n|----------|------------------|-----------|-------------------|\n| 1.0      | 1.000            | 1         | 4.0               |\n| 0.9      | 2.324            | 5         | 9.3               |\n| 0.8      | 3.691            | 7         | 14.8              |\n| 0.7      | 5.789            | 11        | 23.2              |\n| 0.6      | 9.409            | 19        | 37.6              |",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table span slice equals quote",
            "result": "resolved"
          },
          "note": "Tabulated data carried in-report (header row: '| ψ_target | Aspect ratio a/b | n_spheres | Clump length [mm] |'); registered as an in-source asset -- this package does NOT re-extract its numbers."
        },
        {
          "asset_id": "A06",
          "asset_class": "in_source_expression",
          "label": "fenced none block L75-L78",
          "in_report_section": "2. Implementation",
          "locator": {
            "method": "char_span",
            "start_char": 3111,
            "end_char": 3199,
            "start_line": 75,
            "end_line": 78,
            "quote": "```\nψ = A_eq / A_ellipsoid\nA_ellipsoid = 2πb²(1 + (a/be)arcsin(e)), e = √(1 - b²/a²)\n```",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "fenced span slice equals quote",
            "result": "resolved"
          },
          "note": "Mathematical/expression block carried in-report; registered as text."
        },
        {
          "asset_id": "A07",
          "asset_class": "in_source_expression",
          "label": "fenced none block L107-L115",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 4000,
            "end_char": 4206,
            "start_line": 107,
            "end_line": 115,
            "quote": "```\nStep  1: ω_max = 3.3 × 10⁰ rad/s\nStep  2: ω_max = 1.4 × 10⁴ rad/s\nStep  3: ω_max = 1.7 × 10⁵ rad/s\n...\nStep 14: ω_max = 2.5 × 10¹²¹ rad/s\nStep 15: ω_max = ∞\nStep 16: ω_max = NaN → simulation crashes\n```",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "fenced span slice equals quote",
            "result": "resolved"
          },
          "note": "Mathematical/expression block carried in-report; registered as text."
        },
        {
          "asset_id": "A08",
          "asset_class": "in_source_expression",
          "label": "fenced none block L119-L122",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 4271,
            "end_char": 4333,
            "start_line": 119,
            "end_line": 122,
            "quote": "```\nω_dot = I⁻¹ · (τ - ω × (I · ω))\nω_new = ω + ω_dot · dt\n```",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "fenced span slice equals quote",
            "result": "resolved"
          },
          "note": "Mathematical/expression block carried in-report; registered as text."
        },
        {
          "asset_id": "A09",
          "asset_class": "in_source_table",
          "label": "markdown table L134-L138",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 5010,
            "end_char": 5216,
            "start_line": 134,
            "end_line": 138,
            "quote": "| Metric | Value | Target | Status |\n|--------|-------|--------|--------|\n| θ_mean | 50.0° | 25-30° | ⚠️ High (rolling friction effect) |\n| θ_std | <1° | ≤2° | ✅ Pass |\n| n_particles | 352 | >100 | ✅ Pass |",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table span slice equals quote",
            "result": "resolved"
          },
          "note": "Tabulated data carried in-report (header row: '| Metric | Value | Target | Status |'); registered as an in-source asset -- this package does NOT re-extract its numbers."
        },
        {
          "asset_id": "A10",
          "asset_class": "in_source_table",
          "label": "markdown table L146-L152",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 5606,
            "end_char": 5891,
            "start_line": 146,
            "end_line": 152,
            "quote": "| ψ | K_theoretical | v_terminal [m/s] | v_stokes [m/s] |\n|---|---------------|------------------|----------------|\n| 1.0 | 1.000 | 0.0059 | 0.0059 |\n| 0.9 | 1.074 | 0.0055 | 0.0059 |\n| 0.8 | 1.160 | 0.0051 | 0.0059 |\n| 0.7 | 1.274 | 0.0046 | 0.0059 |\n| 0.6 | 1.406 | 0.0042 | 0.0059 |",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table span slice equals quote",
            "result": "resolved"
          },
          "note": "Tabulated data carried in-report (header row: '| ψ | K_theoretical | v_terminal [m/s] | v_stokes [m/s] |'); registered as an in-source asset -- this package does NOT re-extract its numbers."
        },
        {
          "asset_id": "A11",
          "asset_class": "in_source_table",
          "label": "markdown table L162-L168",
          "in_report_section": "3. Results",
          "locator": {
            "method": "char_span",
            "start_char": 6268,
            "end_char": 6471,
            "start_line": 162,
            "end_line": 168,
            "quote": "| ψ | Z_expected | Z_sphere | ΔZ |\n|---|------------|----------|----|\n| 1.0 | 6.0 | 6.0 | 0.0 |\n| 0.9 | 6.5 | 6.0 | +0.5 |\n| 0.8 | 7.2 | 6.0 | +1.2 |\n| 0.7 | 8.0 | 6.0 | +2.0 |\n| 0.6 | 9.0 | 6.0 | +3.0 |",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "table span slice equals quote",
            "result": "resolved"
          },
          "note": "Tabulated data carried in-report (header row: '| ψ | Z_expected | Z_sphere | ΔZ |'); registered as an in-source asset -- this package does NOT re-extract its numbers."
        },
        {
          "asset_id": "A12",
          "asset_class": "source_code_reference",
          "label": "particle/clump.py",
          "in_report_section": "4. Discussion",
          "locator": {
            "method": "char_span",
            "start_char": 6735,
            "end_char": 6883,
            "token": "particle/clump.py",
            "token_start_char": 6796,
            "token_end_char": 6813,
            "start_line": 180,
            "end_line": 180,
            "quote": "1. **Infrastructure**: The TensorDEM clump geometry module (`particle/clump.py`) correctly generates multi-sphere clumps with controlled sphericity.",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)",
            "result": "unresolved"
          },
          "note": "Path reference declared in the report body; the target lives in the TensorDEM repository, which is not part of this worktree and is not served by the platform for this report, so no bytes are registered and no content hash is claimed."
        },
        {
          "asset_id": "A13",
          "asset_class": "source_code_reference",
          "label": "particle/clump_dem.py",
          "in_report_section": "4. Discussion",
          "locator": {
            "method": "char_span",
            "start_char": 7224,
            "end_char": 7399,
            "token": "particle/clump_dem.py",
            "token_start_char": 7283,
            "token_end_char": 7304,
            "start_line": 187,
            "end_line": 187,
            "quote": "1. **Multi-sphere clump DEM**: The clump dynamics engine (`particle/clump_dem.py`) has a numerical stability bug that prevents practical simulation of non-spherical particles.",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)",
            "result": "unresolved"
          },
          "note": "Path reference declared in the report body; the target lives in the TensorDEM repository, which is not part of this worktree and is not served by the platform for this report, so no bytes are registered and no content hash is claimed."
        },
        {
          "asset_id": "A14",
          "asset_class": "source_code_reference",
          "label": "benchmarks/clump_shape_verification/p447w2_n02_clump_shape_study.py",
          "in_report_section": "7. Artifacts & Reproducibility",
          "locator": {
            "method": "char_span",
            "start_char": 10964,
            "end_char": 11053,
            "token": "benchmarks/clump_shape_verification/p447w2_n02_clump_shape_study.py",
            "token_start_char": 10985,
            "token_end_char": 11052,
            "start_line": 274,
            "end_line": 274,
            "quote": "- **Study script**: `benchmarks/clump_shape_verification/p447w2_n02_clump_shape_study.py`",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)",
            "result": "unresolved"
          },
          "note": "Path reference declared in the report body; the target lives in the TensorDEM repository, which is not part of this worktree and is not served by the platform for this report, so no bytes are registered and no content hash is claimed."
        },
        {
          "asset_id": "A15",
          "asset_class": "data_artifact_reference",
          "label": "artifacts/dem/clump_shape_verification/clump_shape_verification_results.json",
          "in_report_section": "7. Artifacts & Reproducibility",
          "locator": {
            "method": "char_span",
            "start_char": 11183,
            "end_char": 11281,
            "token": "artifacts/dem/clump_shape_verification/clump_shape_verification_results.json",
            "token_start_char": 11204,
            "token_end_char": 11280,
            "start_line": 280,
            "end_line": 280,
            "quote": "- **Results JSON**: `artifacts/dem/clump_shape_verification/clump_shape_verification_results.json`",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)",
            "result": "unresolved"
          },
          "note": "Path reference declared in the report body; the target lives in the TensorDEM repository, which is not part of this worktree and is not served by the platform for this report, so no bytes are registered and no content hash is claimed."
        },
        {
          "asset_id": "A16",
          "asset_class": "code_reproduction_snippet",
          "label": "fenced python block L287-L305",
          "in_report_section": "7. Artifacts & Reproducibility",
          "locator": {
            "method": "char_span",
            "start_char": 11424,
            "end_char": 12175,
            "start_line": 287,
            "end_line": 305,
            "quote": "```python\nfrom tensordem.particle.clump import ellipsoid_clump\nfrom tensordem.particle.clump_dem import ClumpDEM\nfrom tensordem.contact.clump_contact import ContactParams, BoxObstacle\nimport numpy as np\n\n# Create 10 ellipsoid clumps (ψ=0.9)\nparticles = [ellipsoid_clump(0.00465, 0.002, n_spheres=5, density=2500.0) for _ in range(10)]\npositions = np.array([[i * 0.005, 0.0, 0.02] for i in range(10)])\nfloor = BoxObstacle(center=(0, 0, -0.001), half=(0.1, 0.1, 0.001))\n\nsim = ClumpDEM(particles, positions, obstacles=[floor],\n               params=ContactParams(kn=1e5, mu=0.5, mu_roll=0.3), dt=1e-4)\n\n# Run 20 steps → NaN at step 16\nfor i in range(20):\n    sim.step()\n    print(f\"Step {i+1}: ω_max = {np.linalg.norm(sim.omega, axis=1).max():.3e}\")\n```",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "fenced span slice equals quote",
            "result": "resolved"
          },
          "note": "Executable-looking code carried in-report (reproduction example); registered as a source-embedded asset, not executed by this package."
        },
        {
          "asset_id": "A17",
          "asset_class": "document_reference",
          "label": "docs/clump_multisphere_particles.md",
          "in_report_section": "8. References",
          "locator": {
            "method": "char_span",
            "start_char": 12580,
            "end_char": 12645,
            "token": "docs/clump_multisphere_particles.md",
            "token_start_char": 12609,
            "token_end_char": 12644,
            "start_line": 314,
            "end_line": 314,
            "quote": "4. TensorDEM documentation: `docs/clump_multisphere_particles.md`",
            "unique": true,
            "occurrences_in_source": 1
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)",
            "result": "unresolved"
          },
          "note": "Path reference declared in the report body; the target lives in the TensorDEM repository, which is not part of this worktree and is not served by the platform for this report, so no bytes are registered and no content hash is claimed."
        }
      ],
      "locators": [
        {
          "asset_id": "A01",
          "source_field": "markdown",
          "method": "document",
          "record_path": null,
          "start_char": 0,
          "end_char": 12871,
          "line": 1,
          "quote": "# DEM Clump Shape Effect Verification Report (p447w2-n02)",
          "quote_sha256": "2f1f89333f1b78c3c8293c7ff7ae539d9e3a6f552297d42763acf2a1cd1b33ef",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A02",
          "source_field": "record",
          "method": "record_json_path",
          "record_path": "figures[0].caption",
          "start_char": 0,
          "end_char": 12871,
          "line": 1,
          "quote": "Settling Velocity Correction",
          "quote_sha256": "df1a247f2d306d67f332a45f44f52b811289aaf3c686427f4c0de419b6fc7bde",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A03",
          "source_field": "record",
          "method": "record_json_path",
          "record_path": "figures[1].caption",
          "start_char": 0,
          "end_char": 12871,
          "line": 1,
          "quote": "Repose Angle Expected",
          "quote_sha256": "db32851f6737ba34f51cddfd67e7a139f993a16c4094cdc441904a10a89d648a",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A04",
          "source_field": "record",
          "method": "record_json_path",
          "record_path": "figures[2].caption",
          "start_char": 0,
          "end_char": 12871,
          "line": 1,
          "quote": "Coordination Number Expected",
          "quote_sha256": "cc7d84d23e9b1aade8f23539f44fcd0cb1612ef45cd12746f8bc7f376b0a0104",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A05",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 2610,
          "end_char": 3057,
          "line": 66,
          "quote": "| ψ_target | Aspect ratio a/b | n_spheres | Clump length [mm] |\n|----------|------------------|-----------|-------------------|\n| 1.0      | 1.000            | 1         | 4.0               |\n| 0.9      | 2.324            | 5         | 9.3               |\n| 0.8      | 3.691            | 7         | 14.8              |\n| 0.7      | 5.789            | 11        | 23.2              |\n| 0.6      | 9.409            | 19        | 37.6              |",
          "quote_sha256": "375ecb2c9484424f689d52493f292c673c185cb19befcc9f9adfd81f532002a3",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A06",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 3111,
          "end_char": 3199,
          "line": 75,
          "quote": "```\nψ = A_eq / A_ellipsoid\nA_ellipsoid = 2πb²(1 + (a/be)arcsin(e)), e = √(1 - b²/a²)\n```",
          "quote_sha256": "f1d5bb2fd54cdf08ef916f031e050d43fba8e0512eaacbf8ba77e864888dc5fa",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A07",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 4000,
          "end_char": 4206,
          "line": 107,
          "quote": "```\nStep  1: ω_max = 3.3 × 10⁰ rad/s\nStep  2: ω_max = 1.4 × 10⁴ rad/s\nStep  3: ω_max = 1.7 × 10⁵ rad/s\n...\nStep 14: ω_max = 2.5 × 10¹²¹ rad/s\nStep 15: ω_max = ∞\nStep 16: ω_max = NaN → simulation crashes\n```",
          "quote_sha256": "1ddc83730e7f17a70427abe0d11b554369e5d37c0df24dde557944c08ed80686",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A08",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 4271,
          "end_char": 4333,
          "line": 119,
          "quote": "```\nω_dot = I⁻¹ · (τ - ω × (I · ω))\nω_new = ω + ω_dot · dt\n```",
          "quote_sha256": "ea49cafb9e521537c3bbd8787cbe2ae45b78e38b0b8353f680d0d879a7647485",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A09",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 5010,
          "end_char": 5216,
          "line": 134,
          "quote": "| Metric | Value | Target | Status |\n|--------|-------|--------|--------|\n| θ_mean | 50.0° | 25-30° | ⚠️ High (rolling friction effect) |\n| θ_std | <1° | ≤2° | ✅ Pass |\n| n_particles | 352 | >100 | ✅ Pass |",
          "quote_sha256": "714e37b3d60846902a0d5d8786defeb12fb91a0a7602ff53db087faf4a7a76fd",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A10",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 5606,
          "end_char": 5891,
          "line": 146,
          "quote": "| ψ | K_theoretical | v_terminal [m/s] | v_stokes [m/s] |\n|---|---------------|------------------|----------------|\n| 1.0 | 1.000 | 0.0059 | 0.0059 |\n| 0.9 | 1.074 | 0.0055 | 0.0059 |\n| 0.8 | 1.160 | 0.0051 | 0.0059 |\n| 0.7 | 1.274 | 0.0046 | 0.0059 |\n| 0.6 | 1.406 | 0.0042 | 0.0059 |",
          "quote_sha256": "cc35f7ae999c47a7c58c9fece1d0aafee3115c0e5796ca99d33e15bb1abfa34f",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A11",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 6268,
          "end_char": 6471,
          "line": 162,
          "quote": "| ψ | Z_expected | Z_sphere | ΔZ |\n|---|------------|----------|----|\n| 1.0 | 6.0 | 6.0 | 0.0 |\n| 0.9 | 6.5 | 6.0 | +0.5 |\n| 0.8 | 7.2 | 6.0 | +1.2 |\n| 0.7 | 8.0 | 6.0 | +2.0 |\n| 0.6 | 9.0 | 6.0 | +3.0 |",
          "quote_sha256": "2bcc1309f9bc9a7a53a39f3dcfe395db1feba4b720c11cba9b809c7549da5e5e",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A12",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 6735,
          "end_char": 6883,
          "line": 180,
          "quote": "1. **Infrastructure**: The TensorDEM clump geometry module (`particle/clump.py`) correctly generates multi-sphere clumps with controlled sphericity.",
          "quote_sha256": "596a9946cadd4ff6e9743e777116da13baa9dd52576fc3e13c7fd237d2e54848",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A13",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 7224,
          "end_char": 7399,
          "line": 187,
          "quote": "1. **Multi-sphere clump DEM**: The clump dynamics engine (`particle/clump_dem.py`) has a numerical stability bug that prevents practical simulation of non-spherical particles.",
          "quote_sha256": "5e8d2e065ff66d5fd15aa059484eca723cc61b22caefa65d70ceda170fd98665",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A14",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 10964,
          "end_char": 11053,
          "line": 274,
          "quote": "- **Study script**: `benchmarks/clump_shape_verification/p447w2_n02_clump_shape_study.py`",
          "quote_sha256": "7d9f1d4848064b750ac18f6242d5b7af0bdd202a07a9689ec67e8b538e59640f",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A15",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 11183,
          "end_char": 11281,
          "line": 280,
          "quote": "- **Results JSON**: `artifacts/dem/clump_shape_verification/clump_shape_verification_results.json`",
          "quote_sha256": "e1c01e4ab02dbfc95ea5af7a5ff3d855c73edf86113ced097c85c3a1d0383aa1",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A16",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 11424,
          "end_char": 12175,
          "line": 287,
          "quote": "```python\nfrom tensordem.particle.clump import ellipsoid_clump\nfrom tensordem.particle.clump_dem import ClumpDEM\nfrom tensordem.contact.clump_contact import ContactParams, BoxObstacle\nimport numpy as np\n\n# Create 10 ellipsoid clumps (ψ=0.9)\nparticles = [ellipsoid_clump(0.00465, 0.002, n_spheres=5, density=2500.0) for _ in range(10)]\npositions = np.array([[i * 0.005, 0.0, 0.02] for i in range(10)])\nfloor = BoxObstacle(center=(0, 0, -0.001), half=(0.1, 0.1, 0.001))\n\nsim = ClumpDEM(particles, positions, obstacles=[floor],\n               params=ContactParams(kn=1e5, mu=0.5, mu_roll=0.3), dt=1e-4)\n\n# Run 20 steps → NaN at step 16\nfor i in range(20):\n    sim.step()\n    print(f\"Step {i+1}: ω_max = {np.linalg.norm(sim.omega, axis=1).max():.3e}\")\n```",
          "quote_sha256": "6a9481e1fcc536a16222991d7ea33fa665ee8190b1aa2c2a89079bf751dc4398",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        },
        {
          "asset_id": "A17",
          "source_field": "markdown",
          "method": "char_span",
          "record_path": null,
          "start_char": 12580,
          "end_char": 12645,
          "line": 314,
          "quote": "4. TensorDEM documentation: `docs/clump_multisphere_particles.md`",
          "quote_sha256": "337cb00240b094f5a37f54cace8a7f03e1ccd2129b2f69cba19ad2bbf621a9a4",
          "quote_in_source": true,
          "slice_matches_quote": true,
          "occurrences_in_source": 1
        }
      ],
      "identity_facts": [
        {
          "fact_id": "title",
          "line": 1,
          "quote": "# DEM Clump Shape Effect Verification Report (p447w2-n02)",
          "quote_sha256": "2f1f89333f1b78c3c8293c7ff7ae539d9e3a6f552297d42763acf2a1cd1b33ef",
          "quote_in_source": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "mission-line",
          "line": 3,
          "quote": "**Mission**: p447w2-n02  ",
          "quote_sha256": "b931e76a6921c6ca4ccf8a97287a2ff4ecc61a931a41995153b1ce63eb25e2d4",
          "quote_in_source": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "status-line",
          "line": 5,
          "quote": "**Status**: PARTIAL SUCCESS with critical bug discovery  ",
          "quote_sha256": "abc4d9f05d35a5efe1a27fd11cf3bd4274fe997c5d118ca9507264a8fc4af6f5",
          "quote_in_source": true,
          "occurrences_in_source": 1
        },
        {
          "fact_id": "honest-assessment-line",
          "line": 23,
          "quote": "---",
          "quote_sha256": "cb3f91d54eee30e53e35b2b99905f70f169ed549fd78909d3dac2defc9ed8d3b",
          "quote_in_source": true,
          "occurrences_in_source": 62
        },
        {
          "fact_id": "artifacts-header",
          "line": 270,
          "quote": "## 7. Artifacts & Reproducibility",
          "quote_sha256": "2c313a4a85718f7a4cfd088fdd86313531e5b2a7d6f64fb06c3ed89206e60da0",
          "quote_in_source": true,
          "occurrences_in_source": 1
        }
      ],
      "id_integrity": {
        "ids_checked": 17,
        "duplicates": [],
        "unique": true,
        "id_format_ok": true
      },
      "claims": [],
      "claims_empty_reason": "Contract wp-13476-01 sets objective.register_assets=true, objective.classify_report_type=false, constraints.no_forced_claim_generation=true, and notes state 'claims 允许为空数组'. This package registers asset identity only (report_id, markdown byte hash, declared figures/artefacts and their in-source locators); extraction is a downstream package, so an empty claims array is the complete result, not an omission.",
      "not_registered": [
        {
          "what": "literature citations in '## 8. References'",
          "reason": "external publications, not report-owned assets; they carry no retrievable bytes and this package does not extract claims"
        },
        {
          "what": "figures ['settling_velocity_correction.png', 'repose_angle_expected.png', 'coordination_number_expected.png']",
          "reason": "declared in record metadata only; the platform exposes no artifact/figures endpoint for report 13476 (r13476/artifacts=404, r13476/assets=404, r13476/figures=404), so bytes and hashes are deliberately NOT claimed"
        }
      ],
      "unresolved": [
        {
          "asset_id": "A02",
          "label": "settling_velocity_correction.png",
          "reason": "figure name in markdown=False; platform artifact endpoints probed (r13476/artifacts=404, r13476/assets=404, r13476/figures=404)"
        },
        {
          "asset_id": "A03",
          "label": "repose_angle_expected.png",
          "reason": "figure name in markdown=False; platform artifact endpoints probed (r13476/artifacts=404, r13476/assets=404, r13476/figures=404)"
        },
        {
          "asset_id": "A04",
          "label": "coordination_number_expected.png",
          "reason": "figure name in markdown=False; platform artifact endpoints probed (r13476/artifacts=404, r13476/assets=404, r13476/figures=404)"
        },
        {
          "asset_id": "A12",
          "label": "particle/clump.py",
          "reason": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)"
        },
        {
          "asset_id": "A13",
          "label": "particle/clump_dem.py",
          "reason": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)"
        },
        {
          "asset_id": "A14",
          "label": "benchmarks/clump_shape_verification/p447w2_n02_clump_shape_study.py",
          "reason": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)"
        },
        {
          "asset_id": "A15",
          "label": "artifacts/dem/clump_shape_verification/clump_shape_verification_results.json",
          "reason": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)"
        },
        {
          "asset_id": "A17",
          "label": "docs/clump_multisphere_particles.md",
          "reason": "path exists in TensorKnowledge worktree=False (target repo = TensorDEM, outside this package's scope)"
        }
      ],
      "observations": [
        "Source identity holds: live markdown sha256 sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0 equals the contract hash sha256:da5ef00db5752534a6f7d70022bd449a88f4ad649ba36e458dc246c61b2392c0 (12871 chars / 13103 utf-8 bytes, 321 lines).",
        "The report declares 3 figures in record.figures; none is reachable as bytes through the platform API (r13476/artifacts=404, r13476/assets=404, r13476/figures=404).",
        "Body path references point into the TensorDEM repository (benchmarks/, artifacts/, docs/); they are outside this worktree's scope and are registered as referenced_unresolved with verbatim locators, not dropped.",
        "No extraction and no verified marks: status stays draft for the platform gate."
      ]
    }
  },
  "claims": []
}
```
