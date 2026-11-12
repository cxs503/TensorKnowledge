# KF-RESULT wp-4463-01

**工序** 01-asset-registration · **报告** report_id=4463 · **仓** TensorKnowledge · **分支** agent/m15536

## ① 本工序做了什么

对 report_id=4463（标题「PR #75 CI 治愈（m4087）：ruff 41→0，报告正文零字节改动」）执行资产登记工序（01-asset-registration）。
确认源报告的 markdown 字段字节哈希与契约一致（sha256:b341405b2074f846737de717391b54b340592704ba4865b315f552f670fff13a，4807 字符），
解析报告结构为 7 个章节段，登记 5 个引用工件路径与 7 个外部引用（git commit/branch/PR/mission），
未做知识抽取（claims 为空数组，合同允许）。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取源报告**：通过平台 API `GET /api/v1/tensor/reports/4463`（Bearer token 认证，用户 eco_admin）获取 report 记录，取 `markdown` 字段。
2. **哈希校验**：用 `hashlib.sha256(markdown.encode()).hexdigest()` 计算 UTF-8 字节哈希，与契约 `sha256:b341405b2074f846737de717391b54b340592704ba4865b315f552f670fff13a` 比对，确认一致。
3. **章节解析**：按 Markdown 标题语法（`#{1,6} `）逐行扫描，将报告切分为 7 个段落，每段记录起止行号、字符数、SHA-256。
4. **附件扫描**：用正则 `!\[.*?\]\(.*?\)` 扫描内嵌图语法（0 命中），用 `https?://` 扫描外链（0 命中），确认 `record.figures` 为空（0 项）。
5. **工件登记**：从报告正文提取 5 个引用文件路径（tools/ 下 3 个脚本、docs/ 下 1 个报告、artifacts/ 下 1 个目录）与 7 个外部引用（git commit 2 个、branch 1 个、PR 2 个、mission 2 个）。
6. **信封组装**：按 `kf_result.v1.schema.json` 组装结果信封，包含 provenance（source_hash/source_field/source_uri）、outputs（asset_manifest.json）、claims（空数组）。
7. **JSON 校验**：用 Python `json.loads()` 验证输出为合法 JSON，字段名与 schema 一致。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-4463-01/kf_result.json` | KF 结果信封：package_id=wp-4463-01, task_type=01-asset-registration, report_id=4463, provenance.source_hash 与契约一致, outputs.asset_manifest.json 含 7 sections + 5 referenced_artifacts + 7 external_references, claims=[] |
| `docs/kf/wp-4463-01/kf_result_wp-4463-01.md` | 本报告（六段式进展报告） |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 定位 |
|---|---|---|
| source_hash | `sha256:b341405b2074f846737de717391b54b340592704ba4865b315f552f670fff13a` | 契约 contract.source_hash |
| chars=4807 | 报告 markdown 字段 `len(md)==4807` | API 返回数据 |
| title | `PR #75 CI 治愈（m4087）：ruff 41→0，报告正文零字节改动` | API 返回 `data['title']` |
| scenario_key | `tensorcad_ci_cure` | API 返回 `data['scenario_key']` |
| mission_id | `4087` | API 返回 `data['mission_id']` |
| tags | `["TensorCAD", "CI-cure", "PR75", "agent/m3778", "ruff"]` | API 返回 `data['tags']` |
| 7 sections | h1 标题 + 6 个 h2 章节（①~⑥） | 正则 `^(#{1,6})\s+` 扫描 |
| 5 referenced_artifacts | `tools/m3778_publish_report.py` 等 | 报告正文第 4 行「产物」行 + 第 1 节表格 |
| 0 figures | `record.figures` 为空，正文无 `![` 语法 | API 返回 `data['figures']==[]` + 正则扫描 |

## ⑤ 注意点与局限

- **零抽取**：本工序为 01-asset-registration，仅做资产登记，不做知识抽取（claims 为空数组）。
- **零改写**：未修改源报告任何字段，仅读取与登记。
- **哈希验证**：source_hash 经独立计算与契约比对，确认一致。
- **无图**：本报告为文档/后端工序，不产场量云图或比较曲线。
- **verification 延迟**：claims 的 verification 由平台门计算，本工序不标记任何 claim 为 verified。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结果 | 说明 |
|---|---|---|
| valid_json | ✅ | `json.loads()` 通过，无语法错误 |
| schema_pass | ✅ | 字段名与 `kf_result.v1.schema.json` 一致（package_id/task_type/report_id/provenance/outputs/claims） |
| source_locator_resolvable | ✅ | `tensor://reports/4463` 通过平台 API 成功获取 |
| source_hash_matches | ✅ | 计算值 `sha256:b341405b2074f846737de717391b54b340592704ba4865b315f552f670fff13a` = 契约值 |
| no_duplicate_ids | ✅ | claims 为空数组，无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组（合同允许），无需证据 |

**repro_cmd**: `python3 -c "import urllib.request,json,hashlib; token='...'; req=urllib.request.Request('http://127.0.0.1:8010/api/v1/tensor/reports/4463', headers={'Authorization':'Bearer '+token}); data=json.loads(urllib.request.urlopen(req).read()); md=data['markdown']; print('hash:', hashlib.sha256(md.encode()).hexdigest()); print('chars:', len(md))"`

```json
{
  "package_id": "wp-4463-01",
  "task_type": "01-asset-registration",
  "report_id": "4463",
  "provenance": {
    "source_hash": "sha256:b341405b2074f846737de717391b54b340592704ba4865b315f552f670fff13a",
    "source_field": "markdown",
    "source_uri": "tensor://reports/4463",
    "producer": "m15536",
    "emitted_at": "2026-11-12T00:57:37Z",
    "notes": "01-asset-registration：仅登记源资产与引用清单，未做抽取；claims 为空数组（合同允许），verification 交由平台门计算"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-4463-01",
      "task_type": "01-asset-registration",
      "objective": {
        "register_assets": true,
        "classify_report_type": false,
        "extraction_performed": false
      },
      "generated_at": "2026-11-12T00:57:37Z",
      "generator": "agent/m15536",
      "source_asset": {
        "uri": "tensor://reports/4463",
        "field": "markdown",
        "platform_record_id": 4463,
        "hash": {
          "algorithm": "sha256",
          "value": "sha256:b341405b2074f846737de717391b54b340592704ba4865b315f552f670fff13a",
          "scope": "UTF-8 bytes of tensor_reports.markdown (report 4463)",
          "contract_expected": "sha256:b341405b2074f846737de717391b54b340592704ba4865b315f552f670fff13a",
          "matches_contract": true
        },
        "size": {
          "chars": 4807,
          "bytes_utf8": 7880,
          "lines": 98,
          "contract_chars": 4807,
          "chars_match_contract": true
        },
        "record_metadata": {
          "title": "PR #75 CI 治愈（m4087）：ruff 41→0，报告正文零字节改动",
          "scenario_key": "tensorcad_ci_cure",
          "tags": [
            "TensorCAD",
            "CI-cure",
            "PR75",
            "agent/m3778",
            "ruff"
          ],
          "status": "published",
          "created_by": 1,
          "created_at": "2026-11-05T10:31:42.268517+00:00",
          "mission_id": 4087,
          "stage": null,
          "summary_sha256": "sha256:82a293590bc82905e7bb2edc29bc7b5a807983d6f894c9c52292e27f7006987b"
        },
        "contract_layer_hint": {
          "value": "TensorCAD|research|A",
          "interpreted": false,
          "note": "契约 notes 原样登记；本工序 objective.classify_report_type=false，不解读分层标签"
        }
      },
      "attachments": {
        "count": 0,
        "items": [],
        "scan": {
          "record_figures_len": 0,
          "markdown_image_syntax_hits": 0,
          "markdown_url_hits": 0,
          "returned_all": true
        },
        "note": "record.figures 为空且正文无内嵌图/外链语法 → 本报告无可解析附件（不含 png_base64 载荷）"
      },
      "sections": [
        {
          "ordinal": 1,
          "level": 1,
          "heading": "PR #75 CI 治愈（m4087）：三个 mission 工具的 lint 红 → 绿，报告正文零字节改动",
          "line_start": 1,
          "line_end": 5,
          "chars": 282,
          "sha256": "sha256:f1462967481d68d89a8310b70bcf0684251af63b8a9af034e56205fdf555e7ea"
        },
        {
          "ordinal": 2,
          "level": 2,
          "heading": "① 案例介绍",
          "line_start": 6,
          "line_end": 20,
          "chars": 586,
          "sha256": "sha256:c2e97bd629a19e329af03419d5ede0e1b67f9c63bd6a31a30c8916b79064e40e"
        },
        {
          "ordinal": 3,
          "level": 2,
          "heading": "② 怎么做的（复现 → 定位 → 最小治愈 → 等价性证明）",
          "line_start": 21,
          "line_end": 44,
          "chars": 1237,
          "sha256": "sha256:19375b512d6283ff468619b27c50fd21f0e7417fae3876491fecb33c7616dd17"
        },
        {
          "ordinal": 4,
          "level": 2,
          "heading": "③ 计算结果（程序化，命令即证据）",
          "line_start": 45,
          "line_end": 57,
          "chars": 646,
          "sha256": "sha256:ba1abcacb2dbb9da942cccb03e9fccfd08ba780f055ed6d2d0674b2ab9992009"
        },
        {
          "ordinal": 5,
          "level": 2,
          "heading": "④ 结果图",
          "line_start": 58,
          "line_end": 63,
          "chars": 167,
          "sha256": "sha256:e0325609c1b48a5906f22e249ca5b08f386653fec5e1a213c8d7cc9de4c5ba25"
        },
        {
          "ordinal": 6,
          "level": 2,
          "heading": "⑤ 注意点（踩过的坑 / 局限 / 适用范围）",
          "line_start": 64,
          "line_end": 86,
          "chars": 1414,
          "sha256": "sha256:8656ef85ac30f19f131d4de2794713dab6076d0f47b49d443d84f12d97d045fc"
        },
        {
          "ordinal": 7,
          "level": 2,
          "heading": "⑥ 误差判定",
          "line_start": 87,
          "line_end": 98,
          "chars": 469,
          "sha256": "sha256:df4223860a32fc99abea4786fceb187409c07f35e1138f7ea5cc31d0ac557ef5"
        }
      ],
      "referenced_artifacts": [
        {
          "path": "tools/m3778_publish_report.py",
          "role": "平台报告 payload 生成器",
          "mentioned_in_section": 1
        },
        {
          "path": "tools/m3778_pr41_figures.py",
          "role": "两张证据图生成器",
          "mentioned_in_section": 1
        },
        {
          "path": "tools/verify_merge_pr41.py",
          "role": "PR #41 合并治愈的机读证据生成器（22 个探针）",
          "mentioned_in_section": 1
        },
        {
          "path": "docs/m3778_pr41_merge_cure.md",
          "role": "治愈报告",
          "mentioned_in_section": 1
        },
        {
          "path": "artifacts/m3778/*",
          "role": "证据 JSON + 两张 PNG（4 文件）",
          "mentioned_in_section": 1
        }
      ],
      "external_references": [
        {
          "type": "git_commit",
          "value": "2ff80b2",
          "context": "PR #75 合并基"
        },
        {
          "type": "git_commit",
          "value": "273e772",
          "context": "agent/m3778 head"
        },
        {
          "type": "git_branch",
          "value": "agent/m3778",
          "context": "PR #75 源分支"
        },
        {
          "type": "pr",
          "value": "#75",
          "context": "TensorCAD PR，8 文件 / +954 行"
        },
        {
          "type": "pr",
          "value": "#41",
          "context": "PR #41 合并治愈（被 verify_merge_pr41.py 验证）"
        },
        {
          "type": "mission",
          "value": "m4087",
          "context": "本单 mission ID"
        },
        {
          "type": "mission",
          "value": "m3778",
          "context": "原始 mission（报告正文来源）"
        }
      ],
      "unresolved": [],
      "boundary": {
        "scope": "仅登记源资产与引用清单，未做知识抽取",
        "claims_empty_reason": "工序 01-asset-registration 仅做资产登记，claims 为空数组（合同允许）",
        "verification_deferred": "verification 由平台门计算，本工序不标记任何 claim 为 verified"
      }
    }
  },
  "claims": []
}
```
