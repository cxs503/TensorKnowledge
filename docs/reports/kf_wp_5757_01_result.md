# KF-RESULT wp-5757-01

tags: kf-wp:wp-5757-01, 01-asset-registration, gate-auto-release, report-5757

## ① 本工序做了什么

对 `report_id=5757`（标题：放门自动化成熟化：gate_auto_release daemon（IN20-R2，G13–G20 六门演练））执行资产登记（asset registration）。确认报告 markdown 的字节哈希与合同一致，识别报告中引用的全部代码/配置/工件/图表/数据库对象共 15 项，生成 `asset_manifest.json`。本工序不做内容抽取（`classify_report_type=false`），claims 为空数组。

## ② 怎么做的（步骤/工具/关键设置）

1. **获取报告**：通过 `GET /api/v1/tensor/reports/5757`（Bearer token 认证）获取 markdown 字段，保存至 `/tmp/report_5757.md`。
2. **哈希校验**：`sha256` 计算得 `d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915`，与合同 `source_hash` 一致。字节数 8027，字符数 5061。
3. **资产识别**：逐段扫描报告，定位所有路径引用（代码文件、配置文件、工件路径、图表、数据库表/schema），对每项记录 char_span 定位器（start_char/end_char/start_line/end_line/quote）。
4. **分辨率分类**：代码/配置类标记为 `referenced_unresolved`（位于其他仓库）；工件类标记为 `declared_absent`（报告明确 not_found）；图表标记为 `referenced_unresolved`。
5. **生成清单**：输出 `asset_manifest.json`（15 项资产，0 项 claims）。

关键设置：零手抄原则——所有定位器的 quote 字段逐字来自报告原文；claims 为空（合同允许）。

## ③ 产出物清单

| 输出文件 | 路径 | 大小 | 要点 |
|---|---|---|---|
| asset_manifest.json | docs/kf/wp-5757-01/asset_manifest.json | 11737 bytes | 15 项资产（code×4, config×2, artifact×5, figure×1, database×3）；claims=[] |
| kf_result.wp-5757-01.json | docs/kf/wp-5757-01/kf_result.wp-5757-01.json | 826 bytes | 结果登记，含 provenance 与 outputs 哈希 |

## ④ 证据定位表

| claim/字段 | 原文引文片段 | 定位 |
|---|---|---|
| source_hash | `d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915` | sha256sum /tmp/report_5757.md |
| A01 gate_auto_release.py | `ops/taskplane/gate_auto_release.py` | 第 20 行，② 怎么做的 |
| A02 gate_auto_release_loop.sh | `gate_auto_release_loop.sh` | 第 20 行，② 怎么做的 |
| A03 gate-auto-release.service | `deploy/taskplane/gate-auto-release.service` | 第 20 行，② 怎么做的 |
| A04 gate_drill.py | `tools/gate_drill.py` | 第 20 行，② 怎么做的 |
| A05 supervise.py | `supervise.py` | 第 20 行，② 怎么做的 |
| A06 taskplane.manifest.yaml | `taskplane.manifest.yaml` | 第 20 行，② 怎么做的 |
| A07 system_pierce_acceptance.json | `artifacts/system_pierce_acceptance.json` | 第 33 行，③ 计算结果 |
| A08 deepwater_gap_ledger_update.json | `artifacts/deepwater_gap_ledger_update.json` | 第 34 行，③ 计算结果 |
| A09 autoregression_acceptance.md | `artifacts/autoregression_acceptance.md` | 第 35 行，③ 计算结果 |
| A10 chronicler_acceptance.json | `artifacts/chronicler_acceptance.json` | 第 36 行，③ 计算结果 |
| A11 spec_impl_acceptance.json | `artifacts/spec_impl_acceptance.json` | 第 37 行，③ 计算结果 |
| A12 gate_auto_release_drill.png | `artifacts/gate_auto_release_drill.png` | 第 53 行，④ 结果图 |
| A13 gate_release_audit | `gate_release_audit` | 第 44 行，③ 计算结果 |
| A14 campaign_nodes | `tensorplatform.campaign_nodes` | 第 10 行，① 案例介绍 |
| A15 gate_drill schema | `gate_drill` | 第 22 行，② 怎么做的 |

## ⑤ 注意点与局限

1. **资产仅路径引用**：本工序为资产登记（task_type=01-asset-registration），不做内容验证或抽取。所有 code/config 资产标记为 `referenced_unresolved`，因为它们位于 TensorPlatform 等其他仓库。
2. **工件全部 declared_absent**：报告的生产只读矩阵显示 5 个判据工件均为 not_found，故标记为 `declared_absent`。
3. **claims 为空**：合同明确 `classify_report_type=false`，且 notes 说明「claims 允许为空数组」。
4. **无物理量基准**：本报告为后端/治理机制报告，不涉及物理计算，故无解析解/实验基准可比。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 状态 | 说明 |
|---|---|---|
| valid_json | ✅ | asset_manifest.json 与 kf_result.json 均通过 json.load() 解析 |
| schema_pass | ✅ | 结构对齐 asset_manifest.v1.schema.json 与 wp-542-01 先例 |
| source_locator_resolvable | ✅ | 所有 15 项资产的 quote 均可在报告原文中逐字定位（char_span） |
| source_hash_matches | ✅ | 本地 sha256 = `d85b5a16...` 与合同 `source_hash` 一致 |
| no_duplicate_ids | ✅ | asset_id A01–A15 无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims=[]（空数组，合同允许） |

```json
{
  "package_id": "wp-5757-01",
  "task_type": "01-asset-registration",
  "report_id": "5757",
  "provenance": {
    "source_uri": "tensor://reports/5757",
    "source_field": "markdown",
    "source_hash": "sha256:d85b5a16b5062cdf22dfb828c57a433f8799ecfe324bd31efa72ba27449bd915",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 5061,
    "source_bytes_utf8": 8027,
    "fetched_via": "GET /api/v1/tensor/reports/5757",
    "generator": "manual asset registration for wp-5757-01",
    "contract_version": "1.0"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-5757-01/asset_manifest.json",
      "sha256": "b862588da2bd3a23dba41589def84ee756653f89eb8246fd4a760b9eeabbc256",
      "bytes": 11737,
      "asset_count": 15,
      "claims": 0
    }
  }
}
```

**repro_cmd**: `python3 -c "import requests,json; r=requests.get('http://127.0.0.1:8010/api/v1/tensor/reports/5757',headers={'Authorization':'Bearer \$TOKEN'}); md=r.json()['markdown']; open('/tmp/r5757.md','w').write(md); import hashlib; print(hashlib.sha256(md.encode()).hexdigest())"`
