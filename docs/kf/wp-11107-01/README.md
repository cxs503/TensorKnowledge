# wp-11107-01 — 01-asset-registration for report 11107

工序：`KF-RESULT wp-11107-01`（report_id=11107，source `tensor://reports/11107`，字段 `markdown`）。
**只做登记，不做抽取**：`claims=[]` 是契约要求（`register_assets: true / classify_report_type: false`，
`no_forced_claim_generation: true`），本目录任何文件都没有把结论标成 `verified`。

## 结论（全部由脚本测量）

| 项 | 值 |
|---|---|
| markdown sha256 | `sha256:799d7ffedf0f95500aca8aa289c2778f4e9d15795c29cd32a412c41aae57c982` |
| 与契约 `input.source_hash` | 一致 |
| chars / bytes_utf8 / lines | 13319 / 13335 / 276（chars 与契约一致） |
| title / scenario_key | 与契约逐字一致 |
| 登记资产 | 7（document 1 / figure 4 / producer-worktree 1 / code-ref 1） |
| 解析状态 | resolved_in_source 1 · resolved_external 5 · referenced_unresolved 1 |
| acceptance 自检 | 6/6 PASS（`verification.json`） |
| 发布回环 | 5/5 PASS（`publish_check.json`，结果报告 id 14784） |

## 文件

| 文件 | 内容 |
|---|---|
| `asset_manifest.json` | 资产清单本体（source 身份 + 7 资产的定位器/解析探测/备注 + counts + id_integrity + claims=[]） |
| `kf_result.json` | 工序结果信封，即平台门校验的对象（`provenance.source_hash` = 源 markdown 字节哈希） |
| `verification.json` | 6 条 acceptance 自检 + 证据字符串 |
| `publish_check.json` | 发布后回环（5 项）：平台存储的 markdown 与本地逐字节一致、本地副本 == 发布快照、json 块 == 信封、两张图 sha256 一致、源报告未被改动 |
| `published.json` | 发布快照（report_id / markdown sha256 / 图 sha256），用来判定工作树副本是否已与已发布报告脱钩 |
| `figures/fig_asset_locator_map.png` | 图 1：资产在原文字符轴上的定位 + 解析状态 |
| `figures/fig_identity_census.png` | 图 2：身份量 measured vs contract + 解析状态普查 |

## 版本说明

- 结果报告 id **14784** 发布时（`published_at` 见 `published.json`）测试套件为 17 例；发布后又补了 2 例
  发布快照测试（`test_worktree_copy_is_the_published_snapshot` / `test_publish_roundtrip_report_all_pass`），现为 19 例。
  报告正文里写的「17 个离线验收测试用例」是**发布时的测量值**，未回改（报告不可变）。

## 已知未解（不计入 acceptance 失败，但下游必须知悉）

1. 4 张上游 png 的字节在**上游任务工作树** `/root/tp-agent/work/m9374` 内（宿主本地路径），
   平台 `GET /tensor/reports/11107/artifacts|figures` 均 404，所以只登记「路径 + 字节数 + sha256」（`resolved_external`），未拷贝二进制，
   知识库不得依赖该路径；目录名 `m9374` 与 `record.mission_id=9374` 只是**提示性**吻合，不构成归属证明。
2. `tensorfem.fatigue.ct_specimen` 是 TensorFEM 的验证面，本仓无求解器代码 → `referenced_unresolved`（不是「不存在」）。
3. §3.7 `C8_figures` 判据里的仓库相对路径 `artifacts/fatigue_ct_e647/*.png` 在本工作树不解析（cross-reference 已登记该事实）。

## 一键复跑（工作树根）

漂移检查（推荐，幂等、不改任何已发布内容）：

```
python3 scripts/kf_wp11107_01_register.py verify \
  && python3 -m pytest tests/test_kf_wp11107_01.py -q \
  && python3 scripts/kf_wp11107_01_publish_check.py 14784
```

`verify` = **重新从平台拉一次**原文、重算 sha256、重放全部 11 个定位器并重跑 6 条 acceptance。

从头复现（注意：`build` 会刷新 `generated_at`/`emitted_at` 两个时间戳，因此重建后 `docs/kf_result_wp-11107-01.md`
与已发布报告 id 14784 的字节不再相同——此时要么重发布，要么用 `report.py adopt 14784` 把工作树拉回发布快照）：

```
python3 scripts/kf_wp11107_01_register.py all \
  && python3 scripts/kf_wp11107_01_report.py render \
  && python3 -m pytest tests/test_kf_wp11107_01.py -q \
  && python3 scripts/kf_wp11107_01_publish_check.py 14784
```

`register.py all` = build（取原文 + 算身份 + 枚举资产）/ envelope / figure / verify。
凭据只从环境变量 `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS` / `TENSOR_API_BASE` 读取，不落盘。