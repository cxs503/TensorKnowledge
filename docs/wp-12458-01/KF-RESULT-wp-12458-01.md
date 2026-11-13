# KF-RESULT wp-12458-01

## ① 本工序做了什么

本工作包（wp-12458-01，task_type=01-asset-registration，lane=C）对报告 report_id=12458（标题 "test report"，scenario_key=test）执行**源资产登记**：确认 report_id 与其 markdown 的字节哈希（sha256），列出 markdown 内可解析的附件/工件，不做 claim 抽取（claims 允许为空数组）。本工序只登记、不抽取、不把任何结论标成 verified（verification 由平台门计算）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：通过平台接口 `GET http://127.0.0.1:8010/api/v1/tensor/reports/12458`（Bearer=eco_admin 登录 token）取回 `markdown` 字段，落盘为 `runs/wp-12458-01/report_12458.json`（本地镜像）。
2. **哈希确认**：对 markdown 字节串独立重算 sha256 = `e82df280a4f31a4a0aba360eaf3761377251d4c4bb18458c5140ea7eb8921ee5`，与契约 `source_hash` 逐字一致（MATCH）。
3. **资产定位**：用 `scripts/kf_register_12458.py` 按锚点表（A01 全文 / A02 标题 / A03 正文声明）在 markdown 内做 char_span 定位，逐条校验 quote 为唯一子串、char 跨度与原文重合。
4. **产出**：生成 `artifacts/wp-12458-01/asset_manifest.json`（字节镜像到 `docs/wp-12458-01/`）与结果信封 `runs/wp-12458-01/kf_result.wp-12458-01.json`。
5. **自检**：用 jsonschema 对结果信封做 `schemas/kf_result.v1.schema.json` 校验（PASS），并逐条核对 acceptance 六项。

关键设置：`TENSOR_API_BASE=http://127.0.0.1:8010/api/v1`；`contract_version=1.0`；`lane=C`；`verification_status=not_verified`（不自行认证）。

## ③ 产出物清单（输出文件名 → 要点）

| 输出文件 | 要点 |
|---|---|
| `artifacts/wp-12458-01/asset_manifest.json` | 源资产清单：3 项资产（A01 全文 / A02 标题 / A03 正文声明），全部 `resolved_in_source`；source.hash 与契约一致；claims=[] |
| `docs/wp-12458-01/asset_manifest.json` | 上述清单的字节镜像（push 门保留的持久副本，与 artifact 字节一致） |
| `runs/wp-12458-01/kf_result.wp-12458-01.json` | 结果信封（kf_result.v1 结构：package_id/task_type/report_id/provenance/outputs/claims），本报告 ```json 块即此文件原样 |
| `runs/wp-12458-01/kf_result_block.wp-12458-01.json` | 同信封，供 ```json 块提交用 |
| `runs/wp-12458-01/report_12458.json` | 平台 API 原始载荷镜像（含 markdown 字段） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段/claim | 原文引文片段（逐字） | 定位 |
|---|---|---|
| source.hash（sha256） | `# Test Report` + `This is a test report with sufficient length to pass validation.`（整篇 markdown 字节串） | 全文，char 0–79 |
| A01 全文（document） | `# Test Report\n\nThis is a test report with sufficient length to pass validation.` | char 0–79，line 0–2 |
| A02 标题（heading） | `# Test Report` | char 0–13，line 0 |
| A03 正文声明（statement） | `This is a test report with sufficient length to pass validation.` | char 15–79，line 2 |
| platform_figures（无图） | API 载荷 `"figures":[]`（空数组） | 平台字段，非 markdown 内 |
| platform_tags | API 载荷 `"tags":["test"]` | 平台字段，非 markdown 内 |

所有引文均逐字来自 report_id=12458 的 markdown 原文（平台独立重算 sha256 与子串做二次确认）。

## ⑤ 注意点与局限

- **本报告为最小测试报告**（79 字符）：markdown 内无表格、无外部数据集、无图件、无 URL/DOI/绝对路径引用，因此可解析附件/工件仅限 markdown 本体（A01–A03）；`platform_figures` 为空数组，无图可登记。
- **不做抽取**：按契约 `objective.classify_report_type=false` 且 notes 允许 claims 为空数组，本工序只登记资产定位，不生成任何 claim；claim 抽取由下游工作包负责。
- **不标 verified**：`verification_status=not_verified`，verification 由平台门独立计算，本工序不自行认证。
- **schema 口径**：结果信封按 `schemas/kf_result.v1.schema.json`（`additionalProperties:false`）组织，顶层仅 package_id/task_type/report_id/provenance/outputs/claims 六键；未沿用旧脚本的 `schema_version` 顶层键（该键不在当前 schema 白名单内，会判门失败）。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 说明 |
|---|---|---|
| valid_json | ✅ | 结果信封为合法 JSON（json.load 通过） |
| schema_pass | ✅ | jsonschema 校验 `schemas/kf_result.v1.schema.json` 通过 |
| source_locator_resolvable | ✅ | 3 条 quote 均为 markdown 唯一子串，char 跨度与原文重合 |
| source_hash_matches | ✅ | 重算 sha256=`e82df280…` 与契约 `source_hash` 一致 |
| no_duplicate_ids | ✅ | asset_id 集合 {A01,A02,A03} 无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[]（空数组，契约允许），无未带证据的 claim |

六项全部通过，无失败项（honest-FAIL 无）。

**repro_cmd**：`python3 scripts/kf_register_12458.py`（需先 `runs/wp-12458-01/report_12458.json` 就位；该文件由 `GET http://127.0.0.1:8010/api/v1/tensor/reports/12458` 落盘）。

```json
{
  "package_id": "wp-12458-01",
  "task_type": "01-asset-registration",
  "report_id": "12458",
  "provenance": {
    "source_uri": "tensor://reports/12458",
    "source_field": "markdown",
    "source_hash": "sha256:e82df280a4f31a4a0aba360eaf3761377251d4c4bb18458c5140ea7eb8921ee5",
    "source_chars": 79,
    "source_bytes_utf8": 79,
    "source_title": "test report",
    "scenario_key": "test",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-12458-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/12458",
    "local_copy": "runs/wp-12458-01/report_12458.md",
    "generator": "scripts/kf_register_12458.py",
    "verifier": "scripts/kf_verify_12458.py",
    "verification_status": "not_verified"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "artifacts/wp-12458-01/asset_manifest.json",
      "artifact_sha256": "3f4903c60eee7fabdab7afa9a0e19357fe5f96c764ac38f0b8cb011cef5b73e2",
      "artifact_bytes": 3371,
      "schema": "asset_manifest.v1",
      "package_id": "wp-12458-01",
      "task_type": "01-asset-registration",
      "report_id": "12458",
      "source": {
        "uri": "tensor://reports/12458",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "e82df280a4f31a4a0aba360eaf3761377251d4c4bb18458c5140ea7eb8921ee5",
        "chars": 79,
        "bytes_utf8": 79,
        "title": "test report",
        "scenario_key": "test",
        "platform_id": 12458,
        "platform_mission_id": 11091,
        "platform_figures": [],
        "platform_tags": [
          "test"
        ],
        "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/12458",
        "local_copy": "runs/wp-12458-01/report_12458.md"
      },
      "counts": {
        "assets": 3,
        "by_class": {
          "document": 1,
          "heading": 1,
          "statement": 1
        },
        "by_resolution": {
          "resolved_in_source": 3
        },
        "resolved_in_source": 3,
        "referenced_unresolved": 0,
        "declared_absent": 0
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告 markdown 全文（源资产本体）",
          "in_report_section": "(document)",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 79,
            "start_line": 0,
            "end_line": 2,
            "quote": "# Test Report\n\nThis is a test report with sufficient length to pass validation.",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "整篇 markdown 即源资产；sha256 见 source.hash"
        },
        {
          "asset_id": "A02",
          "asset_class": "heading",
          "label": "报告标题",
          "in_report_section": "(document)",
          "locator": {
            "method": "char_span",
            "start_char": 0,
            "end_char": 13,
            "start_line": 0,
            "end_line": 0,
            "quote": "# Test Report",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "标题行；与 API title 字段同源"
        },
        {
          "asset_id": "A03",
          "asset_class": "statement",
          "label": "报告正文声明（验证用文本）",
          "in_report_section": "# Test Report",
          "locator": {
            "method": "char_span",
            "start_char": 15,
            "end_char": 79,
            "start_line": 2,
            "end_line": 2,
            "quote": "This is a test report with sufficient length to pass validation.",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "正文唯一声明行；无数字/无外部引用，仅作长度与格式验证"
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组：本工序只登记资产定位，不做 claim 抽取；claim 抽取由下游工作包负责。",
      "integrity": {
        "quote_uniqueness": "all quotes confirmed unique substrings of source markdown (scripts/kf_register_12458.py, checks.source_locator_resolvable)",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      }
    }
  },
  "claims": []
}
```
