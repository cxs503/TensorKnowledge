# wp-12068-01 — 离线可复现层（管到底）

> 包：`wp-12068-01`（report 12068，scenario_key=`p315w1-n07-dg-compressible-euler`，mission 15738）
> 状态：`awaiting_pr_merge` —— 本包不自称已验证、不自称已发布；晋升由平台 pr-gate 在合并时判定。

## 为什么加这一层

原包（`asset_manifest.json` / `kf_result.json` / `verification.json` / `report.md` / 两张图 / `kf01_register.py` 预设 /
`tests/test_kf_wp12068_01.py`）已能证明「发出当天」的定位器与哈希自洽，且 `tests/test_kf_wp12068_01.py` 有 live 层：
重新拉取平台 markdown 并逐条复算 quote。但那一层在**平台不可达时是 skip（不是 pass）**，因此在无网环境里
没有任何东西再复核这 9 个定位器 —— 包的可信度只剩「发出当天」那一刻。

本层把源字节**钉进包里**，让复核不再依赖平台：

| 文件 | 作用 |
|---|---|
| `source/report-12068.md` | report 12068 `markdown` 字段的**逐字节快照**（1113 字节 / 1086 字符），sha256=`de2f1625…20cbf0`，与契约一致 |
| `source/source_manifest.json` | 快照台账：endpoint、字段、sha256/chars/bytes、抓取时间、平台元数据（title/scenario_key/tags/status/5 张图的 name+caption+payload 字节数=0） |
| `scripts/kf/wp12068_01_reverify.py` | `snapshot` 抓取钉存；`verify` 只读快照，离线复算全部哈希与 9 条定位器，`--live` 额外做漂移检查 |
| `reverify.json` | 复核台账（16 项逐条 pass/fail + 漂移结论 + `publication_state=awaiting_pr_merge`） |
| `tests/test_kf_wp12068_01_reverify.py` | 9 项守卫：快照哈希、独立复算定位器、检查器端到端、**篡改必须变红**、发布纪律 |

快照是**副本，不是重打**：写入的是 `GET /api/v1/tensor/reports/12068` 返回的 `markdown` 原始 utf-8 字节，
因此 `source/report-12068.md` 的 sha256 与 `kf_result.json.provenance.source_hash`、
`asset_manifest.json.source.hash`、契约哈希四者逐字符一致（`verify` 的 `pinned_source_matches_contract` 项）。

## 怎么用

```bash
# 离线（无网也行）：复算哈希 + 9 条定位器（char span / 逐字 quote / 1-based 行号 / 唯一性 / 计数 / 信封交叉）
python3 scripts/kf/wp12068_01_reverify.py verify --check

# 有网：额外确认平台源未漂移（漂移则 pinned 包过期，必须重发）
python3 scripts/kf/wp12068_01_reverify.py verify --live --check

# 重新钉存（仅在平台源合法变更后，且必须再生成 manifest/信封/报告）
python3 scripts/kf/wp12068_01_reverify.py snapshot --force

# 只跑守卫
python -m pytest tests/test_kf_wp12068_01_reverify.py tests/test_kf_wp12068_01.py -q
```

## 复核口径（与 `reverify.json` 一一对应）

1. `pinned_source_hash_matches_pin` / `pinned_source_matches_contract`：快照字节 → sha256/chars/bytes 对契约；
2. `manifest_source_matches_pin` / `envelope_provenance_matches_pin`：清单 `source.*` 与信封 `provenance.*` 对快照；
3. `report_id_scoped`：manifest / envelope / pin 三处 report_id 均为 12068（本工具只读这一个报告）；
4. `locator_spans_inside_source` / `locator_quotes_re_slice_verbatim` / `locator_line_map_recomputed` /
   `locator_quotes_unique_in_source`：9 条资产逐条 `md[start:end] == quote`、行号复算（约定：
   `end_line = md.count('\n', 0, end_char-1) + 1`）、quote 全文唯一；`char_span` 类资产不允许退化成整文档；
5. `counts_recomputed_from_assets`：`counts.by_class/by_resolution` 由资产列表重算，不采信写入值；
6. `claims_empty_and_nothing_verified`：`claims=[]`，无任何资产 `status='verified'`；
7. `figures_metadata_only_and_absent_from_body`：5 张图 payload 字节=0、且 5 个图名确实**不出现在正文**里
   —— 即报告里「图名未在正文中出现、定位器退化为整文档跨度」这条**局限说明本身**是被机器复核的；
8. `delivered_manifest_matches_envelope`：信封记录的 manifest sha256/字节数/asset_count/claims 对交付文件重算；
9. `live_source_matches_pin`（仅 `--live`）：平台源与快照一致 → `drift=false`；不可达时记 `SKIP` + 原因，不伪装 pass。

## 局限（不掩饰）

1. 快照只锁 **report 12068 的 markdown 字段**，不含 `record.figures[]` 的图片字节（平台侧 5 张图 payload 为空，
   本包**不伪造**字节哈希）；图仍是 `metadata_only` + `referenced_unresolved`。
2. 5 张图的定位器仍是整文档跨度（`method=document`）：正文里没有任何图名/路径，硬凑一个更「好看」的跨度
   等于编造。要变精确，只能等平台把图字节或图题写进 markdown。
3. `reverify.json` 是产出方（producing agent）的离线复核台账，不是平台判定；`all_pass=true` 只说明
   「对钉存字节自洽」，不等于专家认可，也不等于已发布。
4. 源一旦在平台侧合法变更，快照就必须重钉并**重发整包**（清单、信封、报告、两张图同批），否则 `--live` 会报
   `drift=true` —— 这是设计意图，不是缺陷。