# KF-RESULT wp-5611-01

tags: kf-wp:wp-5611-01, 01-asset-registration, report-5611, TensorKnowledge

## ① 本工序做了什么

本工作包 `wp-5611-01` 为 **01-asset-registration**（资产登记）工序，仅对 `report_id=5611` 进行哈希锚定的资产清点与索引登记。不执行知识抽取（03）、不分类报告类型、不标注 verified。产出为 `asset_manifest.json`，内含 14 项已登记资产（1 份源文档 + 1 条记录元数据 + 3 张结果图 + 5 个代码引用 + 4 个证据工件引用），claims 数组为空（符合契约允许）。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取报告**：通过 TensorPlatform API `GET /api/v1/tensor/reports/5611`（Bearer token 认证）获取完整记录，提取 `markdown` 字段。
2. **哈希校验**：对 markdown 字段的 UTF-8 字节计算 SHA-256，结果为 `sha256:41d35315395fcd30eb99e57e8fe1c7aaf521bfa1db147dddfeb9a421abc9863d`，与契约声明的 `source_hash` 完全一致。
3. **字符数校验**：markdown 字符数 7533，与契约声明的 `chars: 7533` 一致。
4. **资产清点**：扫描 markdown 全文，识别并登记以下资产类别：
   - 源文档本身（report_5611_markdown）
   - 记录元数据（id/title/scenario_key/mission_id/status/tags）
   - 声明的 3 张结果图（fig1/fig2/fig3）
   - 报告中引用的 5 个代码/测试文件路径
   - 报告中引用的 4 个证据工件路径
5. **生成信封**：按 `kf_result.v1.schema.json` 结构组装 `package_id`/`task_type`/`report_id`/`provenance`/`outputs`/`claims`。
6. **零手抄纪律**：所有引文逐字来自报告 markdown，所有数字来自 API 返回的记录字段或契约声明。

## ③ 产出物清单

| 输出文件 | 要点 |
|---|---|
| `docs/kf/wp-5611-01/kf_result.json` | 知识工厂结果信封（v1 schema），含 provenance + outputs + claims=[] |
| `docs/kf/wp-5611-01/kf_result.json` 内 `outputs.asset_manifest.json` | 资产清单：14 项资产，含哈希校验通过标记、逐资产定位器 |
| `artifacts/kf/wp-5611-01/kf_result.json` | 同上（artifact 副本） |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 来源 |
|---|---|---|
| source_hash | `sha256:41d35315395fcd30eb99e57e8fe1c7aaf521bfa1db147dddfeb9a421abc9863d` | 契约声明 + API 返回 markdown 重算 |
| chars | `7533` | 契约声明 + `len(markdown)` |
| title | `IN15-O1 饱和脉搏度量管线成熟化：三态采集器+幂等建表+趋势报表（TensorPlatform）` | API 返回 `title` 字段 |
| scenario_key | `platform-saturation-pulse` | API 返回 `scenario_key` 字段 |
| 代码引用 saturation_pulse.py | `tools/pulse/saturation_pulse.py` | 报告 markdown §② 第1点 |
| 代码引用 001_saturation_pulse.sql | `tools/pulse/sql/001_saturation_pulse.sql` | 报告 markdown §② 第2点 |
| 代码引用 pulse_report.py | `tools/pulse/pulse_report.py` | 报告 markdown §② 第3点 |
| 代码引用 acceptance_evidence.py | `tools/pulse/acceptance_evidence.py` | 报告 markdown §② 第4点 |
| 测试引用 test_saturation_pulse.py | `tests/pulse/test_saturation_pulse.py` | 报告 markdown §② 第5点 |
| 证据引用 acceptance_IN15-O1.json | `artifacts/m4959/acceptance_IN15-O1.json` | 报告 markdown 审计链段 |
| 证据引用 cross_check_psql.json | `cross_check_psql.json` | 报告 markdown 审计链段 |
| 证据引用 pulse_samples.jsonl | `pulse_samples.jsonl` | 报告 markdown 审计链段 |
| 证据引用 pytest_pulse.txt | `pytest_pulse.txt` | 报告 markdown 审计链段 |
| 图引用 fig1_pulse_trend.png | `fig1_pulse_trend.png` | API 返回 `figures[0].name` |
| 图引用 fig2_verification.png | `fig2_verification.png` | API 返回 `figures[1].name` |
| 图引用 fig3_state_reconciliation.png | `fig3_state_reconciliation.png` | API 返回 `figures[2].name` |

## ⑤ 注意点与局限

1. **仅登记不抽取**：本工序为 01-asset-registration，claims 数组为空是合法完整结果，非遗漏。
2. **代码/证据工件未获取内容**：报告中引用的代码文件和证据工件仅按路径登记（`resolvable: false`），未实际 fetch 其内容——这符合 01 工序"inventory only"的契约范围。
3. **图文件未获取二进制**：3 张结果图仅登记元数据（name/caption），未获取 PNG 二进制内容。
4. **零手抄**：所有数字/引文均逐字来自 API 返回或契约声明，无凭记忆重述。
5. **未标注 verified**：按契约约束 `do_not_mark_claims_as_verified: true`，所有资产均未加 verified 标记。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ PASS | kf_result.json 经 json.load() 解析无异常 |
| schema_pass | ✅ PASS | 包含全部 required 字段（package_id/task_type/report_id/provenance/outputs）；provenance 含 source_hash + source_field；outputs 含 asset_manifest.json；无 additionalProperties |
| source_locator_resolvable | ✅ PASS | 源文档 ast-5611-01 通过 TensorPlatform API 成功 fetch；记录元数据 ast-5611-02 通过 API 解析；3 张图在 figures 数组中可定位 |
| source_hash_matches | ✅ PASS | 契约声明 `sha256:41d35315395fcd30eb99e57e8fe1c7aaf521bfa1db147dddfeb9a421abc9863d`，API 返回 markdown 重算结果完全一致 |
| no_duplicate_ids | ✅ PASS | 14 项资产 asset_id 分别为 ast-5611-01 至 ast-5611-14，无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ PASS | claims 数组为空（[]），符合契约"claims 允许为空数组"；无 claims 即无未覆盖证据要求 |

## 复现命令

```bash
# 一键复跑：获取报告 → 校验哈希 → 生成 kf_result.json
python3 -c "
import urllib.request, json, hashlib
token = 'YOUR_TOKEN'
url = 'http://127.0.0.1:8010/api/v1/tensor/reports/5611'
req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
md = data['markdown']
h = hashlib.sha256(md.encode('utf-8')).hexdigest()
assert h == '41d35315395fcd30eb99e57e8fe1c7aaf521bfa1db147dddfeb9a421abc9863d', f'Hash mismatch: {h}'
print(f'Hash verified: sha256:{h}')
print(f'Chars: {len(md)}, Bytes: {len(md.encode(\"utf-8\"))}')
"
```

```json
{
  "package_id": "wp-5611-01",
  "task_type": "01-asset-registration",
  "report_id": "5611",
  "provenance": {
    "source_hash": "sha256:41d35315395fcd30eb99e57e8fe1c7aaf521bfa1db147dddfeb9a421abc9863d",
    "source_field": "markdown",
    "source_uri": "tensor://reports/5611",
    "producer": "agent/m15570 (TensorKnowledge) · package wp-5611-01",
    "emitted_at": "2026-11-12T01:16:00+00:00",
    "notes": "01-asset-registration: hash-pinned inventory of report 5611; claims intentionally empty; no extraction, no report_type classification, no verification stamp"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-5611-01",
      "task_type": "01-asset-registration",
      "generated_at": "2026-11-12T01:16:00+00:00",
      "scope": {
        "report_id": "5611",
        "reports_touched": ["5611"]
      },
      "source": {
        "report_id": "5611",
        "source_uri": "tensor://reports/5611",
        "source_field": "markdown",
        "title": "IN15-O1 饱和脉搏度量管线成熟化：三态采集器+幂等建表+趋势报表（TensorPlatform）",
        "scenario_key": "platform-saturation-pulse",
        "chars": 7533,
        "byte_length_utf8": 10925,
        "sha256": "sha256:41d35315395fcd30eb99e57e8fe1c7aaf521bfa1db147dddfeb9a421abc9863d",
        "hash_check": {
          "expected": "sha256:41d35315395fcd30eb99e57e8fe1c7aaf521bfa1db147dddfeb9a421abc9863d",
          "recomputed": "sha256:41d35315395fcd30eb99e57e8fe1c7aaf521bfa1db147dddfeb9a421abc9863d",
          "match": true
        },
        "chars_check": {
          "expected": 7533,
          "observed": 7533,
          "match": true
        }
      },
      "assets": [
        {
          "asset_id": "ast-5611-01",
          "kind": "source_document",
          "role": "primary_source",
          "name": "report_5611_markdown",
          "locators": [
            {
              "source_uri": "tensor://reports/5611",
              "source_field": "markdown",
              "char_start": 0,
              "char_end": 43,
              "quote": "## ① 案例介绍",
              "note": "first line of markdown; whole-document span is recorded in content_ref"
            }
          ],
          "content_ref": {
            "source_uri": "tensor://reports/5611",
            "source_field": "markdown",
            "chars": 7533,
            "sha256": "sha256:41d35315395fcd30eb99e57e8fe1c7aaf521bfa1db147dddfeb9a421abc9863d"
          },
          "resolvable": true,
          "resolution": "fetched_via_tensor_api",
          "byte_length_utf8": 10925
        },
        {
          "asset_id": "ast-5611-02",
          "kind": "record_metadata",
          "role": "identification",
          "name": "report_5611_record",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "record", "field": "id", "value": 5611},
            {"source_uri": "tensor://reports/5611", "source_field": "record", "field": "title", "value": "IN15-O1 饱和脉搏度量管线成熟化：三态采集器+幂等建表+趋势报表（TensorPlatform）"},
            {"source_uri": "tensor://reports/5611", "source_field": "record", "field": "scenario_key", "value": "platform-saturation-pulse"},
            {"source_uri": "tensor://reports/5611", "source_field": "record", "field": "mission_id", "value": 4959},
            {"source_uri": "tensor://reports/5611", "source_field": "record", "field": "status", "value": "published"},
            {"source_uri": "tensor://reports/5611", "source_field": "record", "field": "tags", "value": ["IN15-O1", "saturation_pulse", "telemetry", "platform", "autoregressive", "pytest"]}
          ],
          "values": {
            "report_id": "5611",
            "title": "IN15-O1 饱和脉搏度量管线成熟化：三态采集器+幂等建表+趋势报表（TensorPlatform）",
            "scenario_key": "platform-saturation-pulse",
            "mission_id": 4959,
            "status": "published",
            "tags": ["IN15-O1", "saturation_pulse", "telemetry", "platform", "autoregressive", "pytest"],
            "created_by": 1,
            "created_at": "2026-11-07T00:54:23.898697+00:00"
          },
          "resolvable": true,
          "resolution": "fetched_via_tensor_api"
        },
        {
          "asset_id": "ast-5611-03",
          "kind": "figure",
          "role": "result_visualization",
          "name": "fig1_pulse_trend.png",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "figures", "index": 0, "field": "name", "value": "fig1_pulse_trend.png"}
          ],
          "caption": "Fig.1 三态负载与 held 节点的 24 次落库趋势（橙=busy 活claim，蓝=idle，深蓝线=held DAG 节点；柱顶数字为 online）；下图为 queued 与 released。",
          "resolvable": true,
          "resolution": "declared_in_report_figures"
        },
        {
          "asset_id": "ast-5611-04",
          "kind": "figure",
          "role": "result_visualization",
          "name": "fig2_verification.png",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "figures", "index": 1, "field": "name", "value": "fig2_verification.png"}
          ],
          "caption": "Fig.2 验收证据：(a) 同一固定时刻 dry-run 与 --commit 的快照逐项相等（全部 delta=0）；(b) 审计链摘要（连续落库、只读锁足迹、DDL 幂等、负值拒收、pytest 24 通过、独立 SQL 对账 delta=0）。",
          "resolvable": true,
          "resolution": "declared_in_report_figures"
        },
        {
          "asset_id": "ast-5611-05",
          "kind": "figure",
          "role": "result_visualization",
          "name": "fig3_state_reconciliation.png",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "figures", "index": 2, "field": "name", "value": "fig3_state_reconciliation.png"}
          ],
          "caption": "Fig.3 定标发现：同一时刻仅读 worker 表（state/current_mission_id 全未维护）得到 online=23/busy=0，并入 mission 活 claim 后为 online=52/busy=32；busy 指标必须由活 claim 推导。",
          "resolvable": true,
          "resolution": "declared_in_report_figures"
        },
        {
          "asset_id": "ast-5611-06",
          "kind": "code_reference",
          "role": "implementation_artifact",
          "name": "tools/pulse/saturation_pulse.py",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "markdown", "quote": "tools/pulse/saturation_pulse.py", "note": "三态采集器主脚本，见报告§②第1点"}
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown_not_fetched",
          "note": "Asset registered by reference only; file content not fetched per 01-asset-registration scope"
        },
        {
          "asset_id": "ast-5611-07",
          "kind": "code_reference",
          "role": "implementation_artifact",
          "name": "tools/pulse/sql/001_saturation_pulse.sql",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "markdown", "quote": "tools/pulse/sql/001_saturation_pulse.sql", "note": "幂等建表 DDL，见报告§②第2点"}
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown_not_fetched",
          "note": "Asset registered by reference only"
        },
        {
          "asset_id": "ast-5611-08",
          "kind": "code_reference",
          "role": "implementation_artifact",
          "name": "tools/pulse/pulse_report.py",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "markdown", "quote": "tools/pulse/pulse_report.py", "note": "趋势报表 CLI，见报告§②第3点"}
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown_not_fetched",
          "note": "Asset registered by reference only"
        },
        {
          "asset_id": "ast-5611-09",
          "kind": "code_reference",
          "role": "implementation_artifact",
          "name": "tools/pulse/acceptance_evidence.py",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "markdown", "quote": "tools/pulse/acceptance_evidence.py", "note": "证据链一键重建脚本，见报告§②第4点"}
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown_not_fetched",
          "note": "Asset registered by reference only"
        },
        {
          "asset_id": "ast-5611-10",
          "kind": "code_reference",
          "role": "test_artifact",
          "name": "tests/pulse/test_saturation_pulse.py",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "markdown", "quote": "tests/pulse/test_saturation_pulse.py", "note": "24条测试（22纯逻辑+2连库），见报告§②第5点"}
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown_not_fetched",
          "note": "Asset registered by reference only"
        },
        {
          "asset_id": "ast-5611-11",
          "kind": "evidence_artifact",
          "role": "acceptance_evidence",
          "name": "artifacts/m4959/acceptance_IN15-O1.json",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "markdown", "quote": "artifacts/m4959/acceptance_IN15-O1.json", "note": "判据数字+产物路径，见报告审计链段"}
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown_not_fetched",
          "note": "Asset registered by reference only"
        },
        {
          "asset_id": "ast-5611-12",
          "kind": "evidence_artifact",
          "role": "acceptance_evidence",
          "name": "cross_check_psql.json",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "markdown", "quote": "cross_check_psql.json", "note": "独立 SQL 对账结果，见报告审计链段"}
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown_not_fetched",
          "note": "Asset registered by reference only"
        },
        {
          "asset_id": "ast-5611-13",
          "kind": "evidence_artifact",
          "role": "acceptance_evidence",
          "name": "pulse_samples.jsonl",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "markdown", "quote": "pulse_samples.jsonl", "note": "追加式样本日志，见报告审计链段"}
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown_not_fetched",
          "note": "Asset registered by reference only"
        },
        {
          "asset_id": "ast-5611-14",
          "kind": "evidence_artifact",
          "role": "acceptance_evidence",
          "name": "pytest_pulse.txt",
          "locators": [
            {"source_uri": "tensor://reports/5611", "source_field": "markdown", "quote": "pytest_pulse.txt", "note": "pytest 输出，见报告审计链段"}
          ],
          "resolvable": false,
          "resolution": "referenced_in_markdown_not_fetched",
          "note": "Asset registered by reference only"
        }
      ],
      "registration_note": "01-asset-registration: hash-pinned inventory of report 5611; claims intentionally empty; no extraction, no report_type classification, no verification stamp"
    }
  },
  "claims": []
}
```
