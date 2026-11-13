# KF-RESULT wp-5949-01

> package_id `wp-5949-01` · task_type `01-asset-registration` · report_id `5949` · tags `kf-wp:wp-5949-01` · lane C · status draft
> 源：`tensor://reports/5949`（field `markdown`）· sha256 `c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002` · 12605 字符 / 17867 字节 utf-8
> 本工序只登记资产：不抽取正文、不生成 claim、不标 verified（verification 由平台门计算）。

## ① 本工序做了什么

本工作包是「报告→知识」产线的第一道工序（asset registration），只处理 `report_id=5949`。产出是一份 `asset_manifest.json`：确认源资产的字节身份，并把报告里**可解析的附件/工件**逐条登记为资产（含逐字 locator），**不做抽取**，`claims` 为空数组。

登记结果：共 **23** 项资产——`resolved_in_source` 4 项（本文内可定位：源 markdown 本体、平台内嵌图 2 张、围栏代码块 1 个），`referenced_unresolved` 19 项（报告引用了、但目标不在本仓工作树内），`declared_absent` 0 项；另有 7 条**声明哈希前缀**（16 hex 位，`truncated=true`、`verifiable=false`）单独登记。

资产类别分布（程序化注入，来自 manifest `counts.by_class`）：

| 资产类别 | 数量 |
|---|---|
| `code_block` | 1 |
| `data_artifact_reference` | 9 |
| `directory_reference` | 1 |
| `embedded_figure` | 2 |
| `module_reference` | 1 |
| `report_markdown` | 1 |
| `source_code_reference` | 8 |

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文（不凭记忆）**：`POST /api/v1/auth/login` 拿 token → `GET /api/v1/tensor/reports/5949`，取 `markdown` 字段原文；登录用环境变量 `TENSOR_AGENT_USER/PASS`，脚本内不存任何秘密。
2. **字节身份先封口**：对 `markdown.encode('utf-8')` 求 sha256，与契约 `source_hash` 逐位比对，并核对字符数是否等于契约 `chars`；任一不符立即中止（`SystemExit`），不生成任何产物。
3. **资产发现（只认内联代码，不猜散文）**：扫描每行的反引号内联代码，分成四类形态——带扩展名文件路径、目录路径、花括号展开（`{a,b}.py`）、`path::symbol` 形式；再补上平台 `figures[]` 与围栏代码块。散文与数学式子一律不解析，避免把正文误登记成资产。
4. **locator 可复算**：以「行首字符偏移」表把行号换算成 `start_char/end_char`，写入 `quote` 并回读校验 `md[start:end] == quote`；同时记录该 quote 在全文中是否唯一。引文全部取自原文切片，**没有一处手抄**。
5. **解析（resolution）严格限域**：目标只在本仓交付工作树内解析，命中=文件/目录存在并给出其 sha256；未命中即 `referenced_unresolved`，写明原因，绝不凭记忆补内容、绝不用「应该有」代替「没找到」。
6. **schema 固定下来**：本仓没有契约所称的 `schemas/kf_result.v1.schema.json`（`schemas/` 下无 `kf_*`），因此按同族 `wp-448-01` 包形状派生本包专用 schema `schemas/asset_manifest.v1.wp-5949-01.schema.json`，`jsonschema` 实跑校验——`schema_pass` 是复算出来的，不是自述的。
7. **验收独立复算**：`verify` 子命令重新登录并**重新拉取**原文，重算哈希、重解析全部 locator、重查 id 唯一性与 claims 状态，结果写 `verification.json`；离线 pytest 再用本地副本复验一遍。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-5949-01/asset_manifest.json` | 主产物：23 项资产 + 7 条声明哈希前缀；counts/integrity/limitations 齐全；claims=[] |
| `docs/kf/wp-5949-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs），已原样写入本报告唯一的 json 代码块 |
| `docs/kf/wp-5949-01/verification.json` | 平台侧独立复算的 7 项 acceptance 结论（all_pass=True） |
| `docs/kf/wp-5949-01/source_5949.md` | 登记源的逐字副本（17867 字节），供离线复验 locator |
| `docs/kf/wp-5949-01/report.md` | 本报告 |
| `docs/kf/wp-5949-01/figures/asset_inventory.png` | 资产清单构成图（73499 字节，sha256 2c2b7acd3305bcfa…） |
| `scripts/kf/build_asset_manifest_5949.py` | build / result / verify 三合一，可一键复跑 |
| `schemas/asset_manifest.v1.wp-5949-01.schema.json` | 本包专用 schema（约束 package/report id 与分辨率词表） |
| `tests/test_kf_wp5949.py` | 离线 pytest：哈希、locator、唯一性、scope、报告单块结构 |

## ④ 证据定位表（字段 → 原文引文片段）

引文一律为原文**逐字切片**（渲染时逐条断言 `quote in source`，否则渲染直接失败）。

| # | manifest 字段 | 原文引文（逐字） | 行 | 取法 |
|---|---|---|---|---|
| 1 | `source.uri / source.hash / source.chars` | `# IN25-T2 · 多样性引擎：氏族矩阵 / 盲预测锁 / 同族查重` | 1 | A01 document locator（首行锚点） |
| 2 | `assets[A13] artifacts/in25_t2/coverage.json` | ``artifacts/in25_t2/coverage.json`` | 66 | inline code，行 66（同一 token 另见 A16 行 69） |
| 3 | `assets[A14] artifacts/in25_t2/roster_check.json` | ``artifacts/in25_t2/roster_check.json`` | 67 | inline code，行 67 |
| 4 | `assets[A15] artifacts/in25_t2/seats.json` | ``artifacts/in25_t2/seats.json`` | 68 | inline code，行 68 |
| 5 | `assets[A17] artifacts/in25_t2/seed_divergence.json` | ``artifacts/in25_t2/seed_divergence.json`` | 70 | inline code，行 70 |
| 6 | `assets[A18] artifacts/in25_t2/prereg_lock.json` | ``artifacts/in25_t2/prereg_lock.json`` | 71 | inline code，行 71 |
| 7 | `assets[A19] artifacts/in25_t2/dedup_ledger.json` | ``artifacts/in25_t2/dedup_ledger.json`` | 72 | inline code，行 72 |
| 8 | `assets[A21] artifacts/in25_t2/pytest_summary.json` | ``artifacts/in25_t2/pytest_summary.json`` | 73 | inline code，行 73 |
| 9 | `assets[A22] blind_scores.json` | ``blind_scores.json`` | 220 | inline code，行 220 |
| 10 | `assets[A05] tools/diversity/gen_doc.py` | ``tools/diversity/gen_doc.py`` | 4 | inline code，行 4 |
| 11 | `assets[A07] tools/diversity/{roster,prereg,dedup,run_node}.py` | ``tools/diversity/{roster,prereg,dedup,run_node}.py`` | 9 | inline code，行 9 |
| 12 | `assets[A08] tests/test_diversity_engine.py` | ``tests/test_diversity_engine.py`` | 9 | inline code，行 9（同一 token 另见 A20 行 73） |
| 13 | `assets[A09] roster.py` | ``roster.py`` | 40 | inline code，行 40（同一 token 另见 A23 行 229） |
| 14 | `assets[A12] ops/taskplane/campaign_dispatcher.py::_hollow()` | ``ops/taskplane/campaign_dispatcher.py::_hollow()`` | 59 | inline code，行 59 |
| 15 | `assets[A06] 工件目录` | ``artifacts/in25_t2/`` | 4 | inline code，行 4 |
| 16 | `declared_digests[coverage]` | `fddd78dbd6e61b17` | 5 | 声明哈希前缀（16 hex，行 5） |
| 17 | `declared_digests[seats]` | `d8ee5d316df9aa40` | 6 | 声明哈希前缀（16 hex，行 6） |
| 18 | `declared_digests[prereg_lock]` | `cc97b74b46f65d44` | 6 | 声明哈希前缀（16 hex，行 6） |
| 19 | `declared_digests[calibration]` | `694b8fe358e207c8` | 7 | 声明哈希前缀（16 hex，行 7） |
| 20 | `declared_digests[dedup_ledger]` | `9ece8a74de549404` | 7 | 声明哈希前缀（16 hex，行 7） |
| 21 | `declared_digests[blind]` | `0439b915d213c62f` | 8 | 声明哈希前缀（16 hex，行 8） |
| 22 | `declared_digests[lock_hash]` | `1b96a171b6000fb9` | 71 | 声明哈希前缀（16 hex，行 71） |
| 23 | `assets[A04] 代码块后的复算命令行` | `python3 -m tools.diversity.run_node` | 259 | 内联代码，紧随审计链块（块行 249-257） |
| 24 | `figures[0]（正文图注首行）` | `**图 1** 氏族覆盖矩阵：左攻坚者、右破坏者，格子里的数字是该 (族,框架) 格内席位数。` | 198 | 平台 figures[0] ↔ 正文图注首行（长图注在原文中折行，此处只取首行） |
| 25 | `figures[1]（正文图注首行）` | `**图 2** 相似度门的分离度：蓝=独立方案对，橙=克隆对，黑虚线=拒绝阈值` | 202 | 平台 figures[1] ↔ 正文图注首行（长图注在原文中折行，此处只取首行） |

> 注：表中 `…` 仅用于**展示截断**，manifest 内 `locator.quote` 保存的是完整片段；以 manifest 为准（`tests/test_kf_wp5949.py::test_locators_are_verbatim_char_spans` 逐项复验）。

## ⑤ 注意点与局限

- 仅登记资产：不抽取正文、不生成 claim、不写 verified（verification 由平台门计算）。
- 登记边界=report_id 5949；未读写任何其它 report_id。
- 报告所述 TensorPlatform 侧工件（tools/diversity/*、artifacts/in25_t2/*、tests/test_diversity_engine.py）不在本仓工作树内，一律登记为 referenced_unresolved，未凭记忆补内容。
- 内联代码之外的裸文本不解析为路径，避免把数学/散文误登记成资产。
- 平台 figures[] 只登记名称/说明与是否存在字节负载，不把图字节复制进 manifest。
- **声明哈希不可当证据用**：报告头部的 7 条工件快照 sha256 只给了 16 位前缀（`verifiable=false`），不足以复算；manifest 只登记声明值，不据此宣称一致。
- **围栏块内的文件名不单独登记**：`coverage.json`、`dedup_ledger.json`、`population.json`、`prereg_lock.json`、`seed_divergence.json` 只出现在审计链代码块内部，由整块资产（A04）覆盖；单列在 manifest `block_internal_names`，避免同一字节被记成两条身份。
- **同一个文件可能被引用多次**：资产身份是「引用出现级」（同一 token 在不同行各成一条），因此 `roster.py`、`tests/test_diversity_engine.py` 各出现两条——这是刻意的，便于每条引用各自携带证据。
- **schema 是本地派生的**：若平台侧 canonical schema 与本包 schema 不同，以平台门为准，本产物须返工。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 依据 |
|---|---|---|
| 合法 JSON | ✅ 通过 | json.loads OK |
| schema 通过（本仓固定 schema） | ✅ 通过 | jsonschema against schemas/asset_manifest.v1.wp-5949-01.schema.json; errors=[] |
| 每个 locator 可在原文解析 | ✅ 通过 | checked 23 locators against live markdown bytes; failing=[] |
| source_hash 与契约一致 | ✅ 通过 | recomputed=c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002 declared=c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002 contract=c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002 |
| asset_id 无重复 | ✅ 通过 | assets=23 unique=23 |
| claims 均带证据或显式未解析 | ✅ 通过 | claims=0 violating=0 (empty array: vacuously satisfied per contract output.asset_manifest notes) |
| 未把任何 claim 标成 verified | ✅ 通过 | claims carry no 'verified' status (claims=0) |

### ⑥.b 误差判定（是否 <3%）

本工序是**登记/校验类**任务，不产生物理量，物理基准判据不适用；可判的只有字节与指针的一致性，且全是精确比较而非近似：

| 量 | 基准 | 实测 | 误差 | <3%？ |
|---|---|---|---|---|
| markdown sha256 | 契约 `c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002` | `c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002` | 0 bit（逐位相同） | **是**（0.0%） |
| 字符数 | 契约 12605 | 12605 | 0 | **是**（0.0%） |
| locator 逐字命中 | 23/23 | 23/23 | 0 条不符 | **是**（0.0%） |
| asset_id 唯一性 | 23 唯一 | 23 | 0 重复 | **是**（0.0%） |
| claim 标 verified 数 | 0 | 0 | 0 | **是**（0.0%） |

**结论**：可用判据（哈希/字符数/locator/唯一性）误差均为 0，均 <3%；物理精度判据不适用于登记工序，已在 ⑤ 声明原因。

## 复跑（repro_cmd）

```bash
# 一等产物重建 + 平台侧独立复算（需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
python3 scripts/kf/build_asset_manifest_5949.py build result verify
# 渲染本报告（含图）
python3 scripts/kf/report_5949.py render
# 离线复验（不联网）
python3 -m pytest tests/test_kf_wp5949.py -q
```

## KF-RESULT JSON（本报告唯一 json 代码块）

```json
{
  "package_id": "wp-5949-01",
  "task_type": "01-asset-registration",
  "report_id": "5949",
  "provenance": {
    "source_uri": "tensor://reports/5949",
    "source_field": "markdown",
    "source_hash": "sha256:c4a082137e7667e9510c08c30ce681c563df072c4bc7c2cb7456e26b2cf20002",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 12605,
    "source_bytes_utf8": 17867,
    "fetched_via": "GET /api/v1/tensor/reports/5949",
    "generator": "scripts/kf/build_asset_manifest_5949.py",
    "contract_version": "1.0"
  },
  "outputs": {
    "asset_manifest.json": {
      "path": "docs/kf/wp-5949-01/asset_manifest.json",
      "sha256": "3c5564ea75d0988de761c7abca2ead5b259ff83a69333a2e369b8d81d449727e",
      "bytes": 40305,
      "asset_count": 23,
      "claims": 0
    }
  }
}
```
