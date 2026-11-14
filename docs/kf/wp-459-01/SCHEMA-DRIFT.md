# wp-459-01 · kf_result.v1 契约漂移修复与热文件改动声明

- 工作包：`wp-459-01`（`task_type=01-asset-registration`，源报告 `report_id=459`）
- 触发：`pytest tests/test_kf_wp459_01_assets.py::test_result_matches_envelope_schema` 在 main 上**失败**
- 结论：本包 `report.md` §⑤ 第 2 项自称 `schema_pass = ✅`，实为**过度声明**——`jsonschema` 实际拒绝了
  `docs/kf/wp-459-01/kf_result.json`。本单把「声明」变成「事实」，并把同类漂移做成可复跑的仓级扫描。

## ① 热文件改动声明（owner 纪律：改动共享热文件前先声明）

| 文件 | 是否共享热文件 | 依据 | 本单改动性质 |
|---|---|---|---|
| `schemas/kf_result.v1.schema.json` | **是**（`tests/` 下 95 个测试文件引用；01–05 五工序共用信封契约） | `grep -rl kf_result.v1.schema tests/ \| wc -l` = 95 | **纯加法**：只新增可选属性 + 一条 `anyOf` 定位规则，不删除任何既有属性、不放宽任何 `required` 之外的严格性；仓级扫描证明 `regressions = []` |
| `docs/kf/wp-459-01/*` | 否（本包私有） | — | 新增证据产物（扫描 JSON、图、本文件） |
| `scripts/kf/*` | 否（新增两个独立脚本，不修改既有脚本） | — | 新增 `schema_conformance_scan.py`、`plot_schema_conformance.py` |
| `tests/test_kf_result_schema_claims.py` | 否（新增测试文件，不改既有测试） | — | 新增 |

未触碰 `scripts/kf/register_assets.py`、`scripts/kf/emit_kf_report.py`、`docs/kf/wp-459-01/kf_result.json`
与 `asset_manifest.json`（保持 PR#251 交付物字节稳定，避免把「契约修复」扩大成「重生成交付物」）。

## ② 缺陷（可复现）

```text
jsonschema.exceptions.ValidationError: Additional properties are not allowed ('claims' was unexpected)
  at <root>                        <- 顶层多了 claims（本包合法为空数组）
  at provenance                    <- 多了 notes / producer
  required 'source_uri' ...        <- 本包 provenance 未写 source_uri（取源路径写在 notes 里）
```

根因：信封生产者早已在使用可选字段，而 schema 仍按「最小信封」写成
`additionalProperties: false` 且 `provenance.required` 含 `source_uri`。仓内语料统计（`docs/kf`+`runs`+`work`，共 135 个 `kf_result` 信封）：

| 字段 | 带该字段的 kf_result 信封数 |
|---|---|
| `claims`（顶层） | 94 |
| `provenance.producer` | 105 |
| `provenance.notes` | 103 |
| `provenance.emitted_at` | 104 |
| `provenance.source_uri` | 67（即 68 个信封没有 URI，靠 notes 记取源路径） |

所以这不是本包一家的笔误，而是**契约落后于生产者现实**。

## ③ 修法（schema，纯加法）

1. 顶层新增可选 `claims`（`array`，`$ref: #/$defs/claim`）。每条 claim：
   `required: [claim_id, text]`，可选 `status`（`supported` / `partially-supported` / `unresolved` / `unsupported`）、
   `evidence[]`、`unresolved_reason`；并规定 `evidence`（非空）与 `unresolved_reason` **二者必居其一**——
   即「不许有无证据又不承认未决的主张」。
2. `$defs.claim_evidence`：`required: [quote, source_field]`，可选 `line` / `note`；
   逐字引文 + 字段名是硬约束（沿用 01 工序既有的 locator 语义）。
3. `provenance` 新增可选 `producer` / `notes` / `emitted_at`（均为非空字符串，自由文本）。
4. `provenance.required` 由 `[source_uri, source_field, source_hash]` 收紧为
   `[source_field, source_hash]` **加** `anyOf: [{required: [source_uri]}, {required: [notes]}]`：
   语料事实是生产者车道常常没有规范 URI，但它必须在 `notes` 里写明取源路径（本包即
   `GET /tensor/reports/459`），否则信封仍被拒——**溯源能力没有被削弱**。
5. 严格性保留项（有测试钉住）：顶层 / `provenance` / `outputs` / `claim` / `claim_evidence`
   全部 `additionalProperties: false`；顶层 `required` 集合不变；`source_hash` 仍是
   `^sha256:[0-9a-f]{64}$`。

## ④ 结果（程序化注入，零手抄）

仓级扫描：`scripts/kf/schema_conformance_scan.py`，扫描 `docs/kf` + `runs` + `work` 下
文件名以 `kf_result` 开头、含 `package_id|task_type|report_id` 的信封（`asset_manifest.json`
与 `review_report.json` 属别的契约，已显式排除）。

| 指标 | 修复前（main 的 schema） | 修复后 | 变化 |
|---|---|---|---|
| 参与扫描的信封 | 135 | 135 | — |
| 通过校验 | 6 | **88** | **+82** |
| 未通过 | 129 | 47 | −82 |
| 失败类别（分组数） | 46 | 39 | −7 |
| 回归（修复前通过、修复后失败） | — | **0** | 加法性成立 |

完整机器可读结果：`docs/kf/wp-459-01/schema_conformance.json`（含每个类别的受影响文件示例）。
图：`docs/kf/wp-459-01/figures/fig_wp459_01_schema_conformance.png`（左：信封通过/未通过；右：残留漂移类别）。

**本包** `docs/kf/wp-459-01/kf_result.json`：`jsonschema` 0 error（`pytest` 14/14 通过，含原失败项）。

## ⑤ 注意点 / 局限（诚实 FAIL 区）

1. **残留 47 个信封仍不通过**，本单**不**修，因为它们属于各包私有形状而非本包契约漂移：
   最大一类是 15 个信封的 `provenance` 额外键（`contract_version` / `fetched_via` / `generator` /
   `hash_algo` / `hashed_bytes` …），另有 3 个 `task_type` 写成简写 `"01"`、2 个写了顶层
   `schema_version` 等。要把它们纳入契约必须逐字段裁决语义（并可能让契约变成「什么都能塞」），
   应由 05 工序统一裁决，不在本单悄悄放行。
2. **扫描器判定口径是文件名 + 关键字段**：`kf_result*.json` 才计入信封。因此一个被改名成
   别名的信封不会被统计；`asset_manifest.json` 里同名字段不参与。口径写在脚本 docstring 里。
3. **本单不验证平台门**：`source_hash` 是否与平台重算一致由平台门判，这里只做结构与「可定位性」校验。
   （本包 `source_hash` 与快照 `source_459.json` 的 markdown 字节哈希在既有测试中逐字复算一致。）
4. **`additionalProperties: false` 仍是主策略**：本单是「把已经稳定的生产者字段写进契约」，
   不是放弃封闭性。新增字段仍有类型 / 枚举 / 非空约束，且 `claim` 必须有证据或显式未决。

## ⑥ 复跑方法

```bash
# 1) 本包验收测试（含原本失败的 schema 项）
python3 -m pytest tests/test_kf_wp459_01_assets.py -q

# 2) 契约回归测试（信封接受/拒绝两侧 + 扫描器加法性）
python3 -m pytest tests/test_kf_result_schema_claims.py -q

# 3) 仓级扫描（对 main 上的旧 schema 取基线）
git show main:schemas/kf_result.v1.schema.json > /tmp/kf_result.v1.baseline.json
python3 scripts/kf/schema_conformance_scan.py \
    --schema schemas/kf_result.v1.schema.json \
    --baseline-schema /tmp/kf_result.v1.baseline.json \
    --package-id wp-459-01 --out docs/kf/wp-459-01/schema_conformance.json

# 4) 图（数字全部来自 ③ 的 JSON）
python3 scripts/kf/plot_schema_conformance.py \
    --report docs/kf/wp-459-01/schema_conformance.json \
    --out docs/kf/wp-459-01/figures/fig_wp459_01_schema_conformance.png
```

## ⑦ 全仓测试对照（修复前 vs 修复后，同一命令、同一机器）

命令（在 work 树内，compute 节点 8 核）：

```bash
python3 -m pytest tests/ -q -n 4 -k "kf or schema" -p no:cacheprovider
```

| 指标 | 修复后（带本单改动） | 修复前（`git stash` 掉 schema 改动） | 差 |
|---|---|---|---|
| 失败/错误节点数 | 443 | 500 | **−57** |
| 本单引入的回归 | **0** | — | — |
| 被本单修好的既有失败 | — | — | **57**（含 `tests/test_kf_wp459_01_assets.py::test_result_matches_envelope_schema`
  以及 49 个兄弟包的 `test_envelope_*schema*` 项，说明漂移是全仓性的而不是单包问题） |

对照方法：`git stash push -- schemas/kf_result.v1.schema.json` → 跑同一命令 → `comm` 比较
`FAILED/ERROR` 节点集合；「只在修复后失败」的集合为**空**（无回归），「只在修复前失败」的集合为 57 项。

残留 443 个失败/错误节点是**先在问题**（与本单无关）：主要是各包测试依赖未入树的运行工件
（如 `runs/wp-11107-01/source_11107.md` 缺失 → `FileNotFoundError`，甚至造成
`tests/test_kf_wp11107_01.py` 收集期报错）以及 `PermissionError` 等沙箱限制。本单不修、也不掩饰。
