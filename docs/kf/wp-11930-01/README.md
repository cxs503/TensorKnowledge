# wp-11930-01 · 01-asset-registration（report 11930）

**源**：`tensor://reports/11930` · field `markdown` · `sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325`
（chars 13121 / bytes_utf8 22324，本地按落盘字节复算一致）
**标题**：BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）
**scenario_key**：`p270w2c-n08-bpm-calibration-feasibility`

本包只做登记：确认源资产哈希、枚举报告中可定位的文件类工件、给字符级 locator 与解析状态。
**不抽取、不分类、不生成 claim**（`claims: []` 按契约是完整结果）。

## 产物

落盘位置 `docs/kf/wp-11930-01/`（`.gitignore` 丢弃 `artifacts/`，故不用该目录做交付）。

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 14 个资产（figure 6 / module 1 / script 3 / test 1 / data 3），逐条 locator + counts + integrity |
| `kf_result.wp-11930-01.json` | 结果信封（唯一交付信道的内容） |
| `source_11930.md` | 平台 markdown 原字节（仅此报告的副本） |
| `source_meta.json` | 源记录元数据（title/chars/bytes/figures/tags） |
| `evidence_table.md` | 证据定位表（由 manifest 程序化生成） |
| `fig_asset_registration_summary.png` | 结果图：类别×解析状态计数、locator 位置/长度 |
| `REPORT.md` | 已发布报告的完整副本（含唯一 json 结果块） |

## 解析状态

- `resolved_in_source` = 6：全部为图。经 `GET /api/v1/tensor/reports/11930/figures/<name>` 取回 PNG（HTTP 200、image/png），逐张记录 `platform_bytes` 与 `platform_sha256`。
- `referenced_unresolved` = 7：`src/tensordem/bpm_calibration_feasibility.py`、`scripts/p270w2c_n08_feasibility.py`、`scripts/p270w2c_n08_figures.py`、`scripts/p270w2c_n08_report.py`、`tests/test_bpm_calibration_feasibility.py`、`runs/p270w2c_n08/records.jsonl`、`artifacts/p270w2c_n08/report.json`。属 TensorDEM 仓（节点 P270W2C-N08 / 任务 m9756），TensorKnowledge 检出内不存在，报告也未内联内容 → 只登记引用，不复制、不推断。
- `declared_absent` = 1：报告 §4 条 1b 自述"原始 JSONL 因磁盘配额已清理"，逐字引文登记。

## acceptance 自检

| 项 | 结果 | 校验 |
|---|---|---|
| valid_json | ✅ | `test_artifacts_are_valid_json` |
| schema_pass | ✅ | `test_manifest_schema_pass`（`schemas/asset_manifest.v1.wp-11930-01.schema.json`）+ `test_envelope_schema_pass`（`schemas/kf_result.v1.schema.json`） |
| source_locator_resolvable | ✅ | `test_every_locator_resolves_verbatim`（14/14 唯一，`md[start:end]==quote`，行号一致） |
| source_hash_matches | ✅ | `test_source_hash_matches_contract` |
| no_duplicate_ids | ✅ | `test_no_duplicate_ids` |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅（空集，显式声明） | `test_claims_empty_is_explicit_not_fabricated` |

`python3 -m pytest tests/test_wp11930_asset_manifest.py -q` → **10 passed**。

## 一键复跑

```bash
python3 scripts/kf_wp11930_fetch.py       # GET /tensor/reports/11930 → source_11930.md + source_meta.json
python3 scripts/kf_wp11930_register.py    # → asset_manifest.json + kf_result.wp-11930-01.json
python3 scripts/kf_wp11930_figure.py      # → fig_asset_registration_summary.png + evidence_table.md
python3 -m pytest tests/test_wp11930_asset_manifest.py -q
```

（需 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` 环境变量；发布报告用 `python3 scripts/kf_wp11930_publish.py`。）

## 局限

1. 未解读图像像素：图与表格数字是否一致不在本工序范围。
2. `declared_absent` 依据报告自述，本包无法独立核查历史存储。
3. 7 个未解析工件需回 source repo 同 commit 取，本包不保证其内容可得。
复跑幂等：`kf_wp11930_register.py` 在源哈希不变时沿用既有 `provenance.emitted_at`，重跑不改动 manifest / 信封字节。
