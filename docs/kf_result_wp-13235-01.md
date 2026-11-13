# KF-RESULT wp-13235-01

> 元数据（供补报单直接 POST 用）：title=`KF-RESULT wp-13235-01`；scenario_key=`in234w2_n09_ice_stat_spectrum`；mission_id=`15755`；tags=`kf-wp:wp-13235-01`
> 状态声明：本会话 run_shell 工具持续故障（每次调用返回 `KeyError: 'command'`，参数被 harness 丢弃，重试 15+ 次均失败），curl 登录/取报告/POST 报告三条路径全部不可用。本报告以 worktree 文件形式交付，**尚未 POST 到平台**（见 ⑤⑥）。

## ① 本工序做了什么

执行工作包 wp-13235-01（task_type=01-asset-registration，lane C）：为 report_id=13235 登记源资产——确认 report_id 与其 markdown 的字节哈希、列出可解析的附件/工件、不做抽取。产出 `asset_manifest.json`（1 个资产条目）与结果信封 `kf_result.json`。claims 为空数组（契约允许，且本工序不产知识）。

## ② 怎么做的（步骤/工具/关键设置）

1. 读 `schemas/kf_result.v1.schema.json`（worktree 内），确定信封结构：package_id/task_type/report_id/provenance/outputs 必填，claims 可选。
2. 尝试获取报告原文：`GET $TENSOR_API_BASE/tensor/reports/13235`（需 curl 登录）与 `psql -d tensorplatform` 两条路径均依赖 run_shell；本会话 run_shell 每次调用均返回 `TOOL ERROR: KeyError: 'command'`（参数被 harness 丢弃），重试 15+ 次无效。
3. 改用 write_file 将交付物落盘 worktree：`work/wp-13235-01/asset_manifest.json`、`work/wp-13235-01/kf_result.json`、本报告。
4. 零手抄纪律：manifest 中所有数字/字符串（report_id=13235、source_hash、title、scenario_key、chars=11779）逐字取自工作包契约 YAML（本单输入），未凭记忆重述任何报告正文内容；未获取到正文，故不引用正文任何片段。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `work/wp-13235-01/asset_manifest.json` | 1 个资产条目（asset-report-13235）：source_uri/source_field/source_hash/title/scenario_key/chars；hash_verification.status=not_run_local（如实标注）；attachments=[]（未枚举，不猜测）；extraction=not_performed |
| `work/wp-13235-01/kf_result.json` | 结果信封（符合 kf_result.v1.schema.json）：provenance.source_hash 与契约一致；outputs.asset_manifest.json 内嵌 manifest；claims=[] |
| `docs/kf_result_wp-13235-01.md` | 本报告（唯一结果信道内容，含唯一 ```json 块） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段 | 值 | 引文（逐字，来源=工作包契约 YAML） |
|---|---|---|
| report_id | 13235 | `report_id: '13235'` |
| source_uri | tensor://reports/13235 | `source_uri: tensor://reports/13235` |
| source_field | markdown | `source_field: markdown` |
| source_hash | sha256:f5d74cb0…f39b6 | `source_hash: sha256:f5d74cb0c70e28338e959f8d271ae806dd6091eb7b2e78c56ac60dcf5c9f39b6` |
| title | IN234W2-N09 冰载荷统计收敛判据与冰致振动频谱分析（8/8 判据 PASS） | `title: IN234W2-N09 冰载荷统计收敛判据与冰致振动频谱分析（8/8 判据 PASS）` |
| scenario_key | in234w2_n09_ice_stat_spectrum | `scenario_key: in234w2_n09_ice_stat_spectrum` |
| chars | 11779 | `chars: 11779` |
| 工序范围 | 仅登记不抽取 | `notes: 登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的附件/工件，不做抽取。claims 允许为空数组。` |

注：报告正文（markdown 字段）本会话未能获取，上表引文全部来自契约输入而非报告正文；这是本单最大的证据缺口（见 ⑤）。

## ⑤ 注意点与局限

- **run_shell 工具故障**：本会话所有 run_shell 调用均 `KeyError: 'command'`（harness 层参数丢失，非命令错误）。后果：(a) 无法本地重算 sha256 做二次确认；(b) 无法枚举附件/工件；(c) 无法 POST 本报告到平台（报告未发=欠账，需补报单）。
- **source_hash 未经本地验证**：哈希逐字取自契约 input.source_hash，平台门会独立重算；若契约哈希与库中实际字节不符，门会判失败——这是诚实的 unknown，不是 PASS。
- **附件枚举缺失**：attachments 为空数组是「未执行」而非「无附件」，已在 manifest 的 attachments_note 中显式区分。
- 无图：纯文档/登记任务，无计算场量，无图合理（且无 shell 无法跑 matplotlib）。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 判定 | 说明 |
|---|---|---|
| valid_json | ✓（结构自检） | kf_result.json 按 schema 手写；未跑 json 解析器（无 shell），标注为未机器验证 |
| schema_pass | ✓（结构自检） | 逐字段对照 schemas/kf_result.v1.schema.json：package_id 匹配 `^wp-…-[0-9]{2}$`，task_type 匹配 `^[0-9]{2}(-[a-z0-9-]+)?$`，report_id 纯数字，source_hash 匹配 `^sha256:[0-9a-f]{64}$`，source_field=markdown，outputs 非空 |
| source_locator_resolvable | ✓ | `tensor://reports/13235#markdown` 指向平台报告 markdown 字段，平台可解析 |
| source_hash_matches | ⚠ 未本地验证（honest） | 本地 run_shell 故障无法重算；哈希逐字取自契约，平台门独立重算裁决 |
| no_duplicate_ids | ✓ | 单资产单 id（asset-report-13235），claims 空 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓ | claims=[]（契约允许）；未决项（哈希验证/附件枚举）在 manifest 中以 status=not_run_local 与 note 显式标注 |

repro_cmd（一键复跑，供补报单/后续会话）：
```
TOKEN=$(curl -s -X POST "$TENSOR_API_BASE/tensor/auth/login" -H 'Content-Type: application/json' -d "{\"username\":\"$TENSOR_AGENT_USER\",\"password\":\"$TENSOR_AGENT_PASS\"}" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])') && \
curl -s "$TENSOR_API_BASE/tensor/reports/13235" -H "Authorization: Bearer $TOKEN" -o /tmp/r13235.json && \
python3 -c 'import json,hashlib;m=json.load(open("/tmp/r13235.json"))["markdown"];print("sha256:"+hashlib.sha256(m.encode()).hexdigest())' && \
curl -s -X POST "$TENSOR_API_BASE/tensor/reports" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d @/tmp/report.json
```

```json
{
  "package_id": "wp-13235-01",
  "task_type": "01-asset-registration",
  "report_id": "13235",
  "provenance": {
    "source_hash": "sha256:f5d74cb0c70e28338e959f8d271ae806dd6091eb7b2e78c56ac60dcf5c9f39b6",
    "source_field": "markdown",
    "producer": "agent/m15755 (mission 15755, lane C, wp-13235-01)",
    "emitted_at": "2026-11-12",
    "notes": "source_hash 逐字取自工作包契约 input.source_hash；本会话 run_shell 工具故障（KeyError: 'command'），本地未重算，由平台门独立重算校验。"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-13235-01",
      "task_type": "01-asset-registration",
      "contract_version": "1.0",
      "lane": "C",
      "registered_at": "2026-11-12",
      "assets": [
        {
          "asset_id": "asset-report-13235",
          "asset_type": "report",
          "report_id": "13235",
          "source_uri": "tensor://reports/13235",
          "source_field": "markdown",
          "source_hash": "sha256:f5d74cb0c70e28338e959f8d271ae806dd6091eb7b2e78c56ac60dcf5c9f39b6",
          "title": "IN234W2-N09 冰载荷统计收敛判据与冰致振动频谱分析（8/8 判据 PASS）",
          "scenario_key": "in234w2_n09_ice_stat_spectrum",
          "chars": 11779,
          "locator": "tensor://reports/13235#markdown",
          "hash_verification": {
            "status": "not_run_local",
            "note": "本会话 run_shell 工具持续故障（每次调用返回 KeyError: 'command'），无法执行 psql/curl 重算 sha256。哈希值逐字取自工作包契约 input.source_hash（非记忆重述）；由平台门独立重算校验。"
          }
        }
      ],
      "attachments": [],
      "attachments_note": "附件/工件枚举未执行：本会话未能获取报告 markdown（run_shell 故障，API 与 psql 两条获取路径均不可用）。依 do_not_invent_missing_information，不列任何附件，不猜测。",
      "extraction": "not_performed",
      "claims": [],
      "notes": "01-asset-registration 工序：仅登记源资产（report_id 与其 markdown 字节哈希），不做抽取（契约 notes 原文：'登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的附件/工件，不做抽取。claims 允许为空数组。'）。"
    }
  },
  "claims": []
}
```
