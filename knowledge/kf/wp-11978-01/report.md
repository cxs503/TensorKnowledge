# KF-RESULT wp-11978-01

tags: `kf-wp:wp-11978-01` `asset-registration` `report-11978` `harness-defect`

## ① 本工序做了什么

对 report_id=11978（`tensor://reports/11978`，markdown 字段）执行 01-asset-registration：
登记源资产（report_id + markdown 字节哈希 + 元数据），产出 `asset_manifest.json`。
**honest-FAIL 声明**：本会话 `run_shell` 工具持续故障（每次调用均返回 `KeyError: 'command'`，≥7 次尝试），
导致两条规定的原文获取通道（curl API / psql）均不可用，markdown 原文未能取回。
因此：(a) 独立 sha256 重算 **未执行**，哈希值逐字取自机器下发的工单契约（平台建包时计算）；
(b) 附件/工件枚举 **未执行**，attachments 留空数组而非编造；(c) 本报告无法经 curl 发布到平台
（发布同样依赖 shell），按守望线机制将派补报单。所有未执行项在 manifest 的 `unresolved` 中显式登记。

## ② 怎么做的（步骤/工具/关键设置）

1. 读契约：工单 YAML（package_id=wp-11978-01，source_hash=sha256:c9b12f13…98987，chars=9907，
   scenario_key=thermo_mechanical_coupling，分层=FEM|thermo_mechanical_coupling|l）。
2. 尝试原文获取（均失败）：`run_shell` 7+ 次尝试全部 `KeyError: 'command'`（harness 参数丢失缺陷）；
   `list_dir`/`read_file`/`write_file` 正常（read_file 首次亦失败、重试成功，判定为间歇性参数丢失）。
3. 读 schema：`schemas/kf_result.v1.schema.json`（结果信封 v1：package_id/task_type/report_id/provenance/outputs，
   claims 允许空数组）。
4. 登记：仅用契约机器字段构造 manifest（零手抄：manifest 中每个值均可在工单契约中逐字定位，
   未引用任何报告正文内容，因为正文不可得）。
5. 产物落 worktree：`knowledge/kf/wp-11978-01/asset_manifest.json`（沿用既有 wp 目录约定）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `knowledge/kf/wp-11978-01/asset_manifest.json` | 源资产登记：uri/field/hash/title/scenario_key/chars；assets[1]；attachments=[]（unresolved）；claims=[]；unresolved[2] 显式登记两项未做 |
| `knowledge/kf/wp-11978-01/report.md` | 本报告（含唯一 ```json 结果信封块） |

## ④ 证据定位表（字段 → 出处引文）

| manifest 字段 | 值 | 出处（逐字） |
|---|---|---|
| source.uri | `tensor://reports/11978` | 契约 `source_uri: tensor://reports/11978` |
| source.field | `markdown` | 契约 `source_field: markdown` |
| source.hash | `sha256:c9b12f1302dc4663a0a731c49a286124c4756ce8ce8a466aba18fa4e65798987` | 契约 `source_hash: sha256:c9b12f1302dc4663a0a731c49a286124c4756ce8ce8a466aba18fa4e65798987` |
| source.title | `Thermo-mechanical coupling verification: bimetal / thermal stress concentration / thermal shock (FEM)` | 契约 `title:` 行 |
| source.scenario_key | `thermo_mechanical_coupling` | 契约 `scenario_key: thermo_mechanical_coupling` |
| source.chars | `9907` | 契约 `chars: 9907` |
| source.layer | `FEM\|thermo_mechanical_coupling\|l` | 契约 notes `分层=FEM\|thermo_mechanical_coupling\|l` |
| report_id | `11978` | 契约 `report_id: '11978'` |

注：因正文不可得，本表定位目标为**工单契约**（机器下发），非报告正文；未对报告正文做任何引文。

## ⑤ 注意点与局限

- **harness 缺陷**：`run_shell` 本会话 100% 失败（KeyError: 'command'），`read_file`/`write_file` 首次调用亦偶发同型错误、重试成功。建议平台侧排查工具参数传递。
- **哈希未独立验证**：`provenance.source_hash` 为契约原值，平台门独立重算 sha256 与子串做二次确认；本工序不标 verified。
- **附件未枚举**：正文不可得，attachments 留空；后续工序（02+）取回正文后应补枚举。
- **无图理由**：纯登记工序，无计算、无场量，无图。
- **发布欠账**：本报告以 worktree 文件形式留存，API 发布因 shell 故障未执行。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 判定 | 说明 |
|---|---|---|
| valid_json | ✓ | 信封按 schema 手工构造；本地无 shell 跑解析器（未跑=未跑，非通过） |
| schema_pass | ✓（同上注） | 顶层键=package_id/task_type/report_id/provenance/outputs/claims，均在 schema properties 内；source_hash 匹配 `^sha256:[0-9a-f]{64}$`（64 位小写 hex 已核） |
| source_locator_resolvable | ✓ | `tensor://reports/11978` 为平台可解析 URI |
| source_hash_matches | ⚠ 待平台重算 | 本会话无法独立重算（run_shell 故障）；值=契约原值，若契约哈希正确则门过 |
| no_duplicate_ids | ✓ | 仅 1 个 asset_id：`asset-11978-01-markdown` |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims=[]（契约允许）；两项未做在 unresolved 显式登记 |

repro_cmd（shell 恢复后一键复跑）：
`psql -d tensorplatform -tA -c "select markdown from tensor_reports where id=11978" | sha256sum`
（期望输出 `c9b12f1302dc4663a0a731c49a286124c4756ce8ce8a466aba18fa4e65798987`；或 GET $TENSOR_API_BASE/tensor/reports/11978 取 markdown 字段后 sha256sum）

## 结果信封（唯一 JSON 块）

```json
{
  "package_id": "wp-11978-01",
  "task_type": "01-asset-registration",
  "report_id": "11978",
  "provenance": {
    "source_hash": "sha256:c9b12f1302dc4663a0a731c49a286124c4756ce8ce8a466aba18fa4e65798987",
    "source_field": "markdown",
    "producer": "agent/m15732 · wp-11978-01 (01-asset-registration)",
    "emitted_at": "2026-11-12",
    "notes": "source_hash carried verbatim from the machine-issued work-package contract (platform-computed at package creation). Independent recomputation NOT performed in this session: run_shell tool defect (KeyError 'command' on every attempt). Platform gate recomputes independently."
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-11978-01",
      "task_type": "01-asset-registration",
      "contract_version": "1.0",
      "report_id": "11978",
      "source": {
        "uri": "tensor://reports/11978",
        "field": "markdown",
        "hash": "sha256:c9b12f1302dc4663a0a731c49a286124c4756ce8ce8a466aba18fa4e65798987",
        "hash_provenance": "carried verbatim from the machine-issued work-package contract (platform-computed at package creation); NOT independently recomputed in this session (run_shell harness defect: KeyError 'command' on every attempt)",
        "title": "Thermo-mechanical coupling verification: bimetal / thermal stress concentration / thermal shock (FEM)",
        "scenario_key": "thermo_mechanical_coupling",
        "chars": 9907,
        "layer": "FEM|thermo_mechanical_coupling|l"
      },
      "assets": [
        {
          "asset_id": "asset-11978-01-markdown",
          "kind": "report-markdown",
          "uri": "tensor://reports/11978",
          "field": "markdown",
          "hash": "sha256:c9b12f1302dc4663a0a731c49a286124c4756ce8ce8a466aba18fa4e65798987",
          "status": "registered-pending-platform-verification"
        }
      ],
      "attachments": [],
      "attachments_status": "unresolved: markdown body not retrievable in this session (run_shell tool defect); list intentionally left empty - nothing invented",
      "claims": [],
      "unresolved": [
        "independent sha256 recomputation of the markdown bytes: NOT performed (run_shell tool defect: KeyError 'command' on every attempt); hash value carried verbatim from the machine-issued work-package contract",
        "attachment/artifact enumeration: NOT performed (markdown body not retrievable in this session); attachments list left empty rather than invented"
      ],
      "verification": "delegated to platform gate (independent sha256 recompute + verbatim substring check); no claim marked verified by this work package"
    }
  },
  "claims": []
}
```
