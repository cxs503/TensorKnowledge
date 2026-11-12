# KF-RESULT wp-5761-01

锚点 `KBM-RCI-F1-FACTORY`｜工作包 `wp-5761-01`｜工序 `01-asset-registration`｜lane C｜
report_id **5761**｜mission 15581｜交付仓 TensorKnowledge（status: draft，未标 verified）

## ① 本工序做了什么

只做资产登记（PRODUCTION-LINE-v1 §2.1）：确认 report_id=5761 的 markdown 字节哈希与工作包契约一致，
把这份报告里**可定位的资产**逐条登记为 manifest——每条形如「什么资产 / 在报告哪一段 /
在源文中的字符区间与行号 / 逐字引文 / 定位状态」。不做分类（`classify_report_type=false`）、
不做 claim 抽取（`claims=[]`）、不改写原文、不标 verified（验证由平台门计算）。

一句话结果：源哈希 **`sha256:06f7e6a9d2164c64a916d4f11cc0e117af97766de133438d10fc884a35c2c4d7`**（4141 字符 / 7172 字节 UTF-8）与契约声明**逐字一致**；
登记资产 **31** 条，分 **17** 类、三档定位状态（resolved_in_source 22 /
referenced_unresolved 8 / declared_absent 1）；所有 31 条 locator 用重新拉取的
字节复切片全部命中（spans_resolved=31/31）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/5761`（Bearer token 由 `$TENSOR_AGENT_USER` 登录获得），
   取 `markdown` 字段；`sha256(markdown.encode("utf-8"))` 与契约 `06f7e6a9d216…` 比对，**不等即中止**
   （不做"大概一致"的继续）。副本以原始字节写 `docs/kf/wp-5761-01/report_5761.markdown`，不做换行归一。
2. **定锚切片**：每条资产用「定位锚 + 模式」声明：`line`（整行）/ `block`（整段，遇空行止）/
   `raw`（精确子串）/ `document`（全文）。生成器 `scripts/kf/build_asset_manifest_5761.py` 在源字节上
   搜索锚点、回切 `[start_char,end_char)`、并**强制 quote 在全文出现次数==1**，否则中止——引文全部来自
   切片结果，**没有一处手抄**；同时回算 `start_line/end_line` 与切片一一对应。
3. **登记口径**：资产=可在源文定位的对象（表 5 / 图题 3 / 注意点 5 / 方法步骤 / 公式 / 几何与参数声明 /
   代码与工件路径引用）。代码与工件（`route/tests/test_route_second_cut.py`、`make_route_lock.py`、
   `run_second_cut.py`、`artifacts/ice_route_second_cut/route_lock.json`、`summary.json`）**不在本交付工作树内**，
   按 `referenced_unresolved` 挂账——不猜路径、不臆造哈希；图1–图3 在平台 `figures[]` 里只有 name+caption、
   无 `png_base64` 载荷，同样 `referenced_unresolved`；⑤ 显式声明"非 A2 观测产品"的外部数据集登记为
   `declared_absent`。
4. **schema 可复现**：契约点名的 `schemas/kf_result.v1.schema.json` 在本工作树**不存在**；为使
   `schema_pass` 可机器复算，把仓内既有的 `schemas/asset_manifest.v1.schema.json`（sha256 `5a464a27d68edf52…`）**机械重钉**
   到本包（只替换 package_id / report_id / uri 三处身份 pin，共 3 处），生成
   `docs/kf/wp-5761-01/schema/asset_manifest.v1.wp-5761-01.schema.json`；`schema_binding.json` 记录父哈希与逐条替换。重钉后结构（required/asset_id 正则/
   resolution 枚举/locator 字段）与父 schema 完全一致，验证脚本显式断言这一点。
5. **独立复算**：`scripts/kf/verify_5761.py` 不 import 生成器，重新登录取源、重新切片、重新校验 schema、
   重新统计计数与 id，产出 `verification.json`（10 项检查，overall=PASS）。
6. **工具链**：Python 3.11 + `jsonschema`（draft-07 校验）+ `matplotlib`（图1/图2）+ `pytest`（离线回归 8 项）。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 字节 | sha256(前16) | 要点 |
|---|---|---|---|
| `docs/kf/wp-5761-01/report_5761.markdown` | 7172 | `06f7e6a9d2164c64…` | 报告 5761 markdown 逐字副本（来源字节，定位基准） |
| `docs/kf/wp-5761-01/asset_manifest.json` | 30797 | `962793f37a9fb02f…` | **主产物**：31 条资产定位 + 计数 + 空 claims + integrity |
| `docs/kf/wp-5761-01/schema/asset_manifest.v1.wp-5761-01.schema.json` | 5914 | `8251cc03c9566cbe…` | 由 `schemas/asset_manifest.v1.schema.json` 机械重钉（仅改 4 处身份 pin） |
| `docs/kf/wp-5761-01/schema_binding.json` | 955 | `896bc6ad432966b3…` | 父 schema 哈希 + 逐条替换记录（可复核重钉未放宽结构） |
| `docs/kf/wp-5761-01/kf_result.json` | 33585 | `c0cb470c7228ecb4…` | 结果信封：package_id/task_type/report_id/provenance/outputs（报告内唯一 json 块） |
| `docs/kf/wp-5761-01/verification.json` | 6208 | `956fc36d17fc25bd…` | 独立复算结论：10 项检查，overall=PASS |
| `docs/kf/wp-5761-01/fig_asset_inventory.png` | 91648 | `3f8487ea3e95c867…` | 图1 资产清单（按 class 与 resolution 分层，由 manifest 渲染） |
| `docs/kf/wp-5761-01/fig_locator_map.png` | 64633 | `5b2f566a7a548595…` | 图2 locator 覆盖图（31 条 span 在 4141 字符源文中的位置） |

> 说明：本仓 `.gitignore` 忽略 `artifacts/`，且推送门 `tp_pusher._EXCLUDE` 会滤掉 `artifacts/**`、`runs/**`，
> 因此**全部产物落 `docs/kf/wp-5761-01/`**，否则推送后产物消失（wp-448-01 已记此坑）。

图1 `fig_asset_inventory.png`：资产清单分层（resolved / unresolved / absent），计数由 manifest 直接渲染。
图2 `fig_locator_map.png`：31 条 locator 的字符区间在源文 0..4141 上的覆盖，颜色=定位状态
（A01 为 document 级，覆盖全文）。两图数字均程序注入，无手抄。

## ④ 证据定位表（字段 → 原文引文片段）

每条资产在 `asset_manifest.json` 中带完整逐字 `quote` 与 `[start_char,end_char)`；下表为同源摘要
（引文换行以 `⏎` 显示、超长以 `…` 截断，**完整引文以 manifest 为准**）：

| asset_id | asset_class | 段 | 定位（char span / line） | 原文引文（逐字） |
|---|---|---|---|---|
| A01 | document | 全文 | document 0..4141 | # IN16-K9 冰区 A* 航线测试面第二刀：边界工况 · 负例拒收 · 回归锁 |
| A02 | statement | 结论 | 44..194 / L3–L6 | **结论**：PASS。新增测试 **64** 项全绿、负例 **51** 项、 ⏎ 求解核心分支覆盖 **90.21%**（175/194，判据 ≥80%）、 ⏎ 基准航线 sha256 回… |
| A03 | method_scope_declaration | ① 案例介绍 | 223..417 / L10–L12 | 对象是船舶绿色航行-冰区域求解链上的**航线优化层** `modules.green_navigation_ice.route`： ⏎ "A2 冰情场 → 冰阻力与推进链（W3-N11）→ 冰… |
| A04 | cost_function_definition | ① 案例介绍 | 419..503 / L14–L14 | $$J = w_E\,\frac{E}{E_{ow}} + w_T\,\frac{T}{T_{ow}} + w_R\,\frac{R}{\Delta s_{gc}}$$ |
| A05 | case_declaration | ① 案例介绍 | 505..657 / L16–L18 | NO-GO/LAND 是硬约束（删边），CAUTION 进入风险代价。基准冰场为理想化喀拉海走廊 ⏎ （57×31 格，格距 9.61×10.07 nm）， ⏎ 起点 [68.6, 57.5]… |
| A06 | scope_statement | ① 案例介绍 | 659..708 / L20–L20 | 本节点的作用域是**测试面**（战役规定"只补测试不改算法"）：把 D1 交付的求解器在边界工况、 |
| A07 | method_step | ② 怎么做的 | 754..933 / L25–L27 | 1. **纳入既有实现**：IN10-D1 的 `route/` 包原样进入本工作树（`astar.py` 8 邻域 A* + 可采纳启发式、 ⏎    `optimize.py` 代价与双基… |
| A08 | source_code_reference | ② 怎么做的 | 934..993 / L28–L28 | 2. **第二刀测试面** `route/tests/test_route_second_cut.py`（64 项）： |
| A09 | boundary_case_set | ② 怎么做的 | 994..1117 / L29–L30 |    * 边界工况用**确定性构造小冰场**（无随机项）：全冰封（h=3 m、C=1 → 载荷比 3>1 → NO-GO）、 ⏎      单通道走廊（9×15、7 号列冰封、唯一缺口 (4,… |
| A10 | negative_case_set | ② 怎么做的 | 1118..1223 / L31–L32 |    * 负例：冰况谱越界（NaN/Inf 与物理上下界、经纬网格越界）、负风险/NaN 风险、退化代价权重 ⏎      （零和/负/NaN/非 3 元）、C3 速度剖面与 B2 包络契约、… |
| A11 | source_code_reference | ② 怎么做的 | 1233..1253 / L33–L33 | `make_route_lock.py` |
| A12 | data_artifact_reference | ② 怎么做的 | 1319..1367 / L34–L34 | `artifacts/ice_route_second_cut/route_lock.json` |
| A13 | method_step | ② 怎么做的 | 1387..1604 / L35–L38 | 3. **输入闸门（本节点唯一代码改动，全部为"拒收"而非"裁剪"）**： ⏎    `field.IceGrid.__post_init__` 冰况谱有限性与上下界；`risk.valida… |
| A14 | toolchain_declaration | ② 怎么做的 | 1605..1730 / L39–L40 | 4. **工具链**：pytest(junitxml) + coverage(--branch) + matplotlib + `run_second_cut.py` ⏎    （判据汇总 →… |
| A15 | source_code_reference | ② 怎么做的 | 1669..1688 / L39–L39 | `run_second_cut.py` |
| A16 | data_artifact_reference | ② 怎么做的 | 1700..1714 / L40–L40 | `summary.json` |
| A17 | table | ③ 计算结果 | 1748..1996 / L44–L50 | \| 判据 \| 目标 \| 实测 \| 结论 \| ⏎ \|---\|---\|---\|---\| ⏎ \| 第二刀新增测试项 \| ≥14 \| **64**（全绿 64） \| PAS… |
| A18 | table | ③ 计算结果 | 2019..2377 / L54–L62 | \| 模块 \| 语句 \| 分支 \| 分支覆盖 \| 语句覆盖 \| ⏎ \|---\|---\|---\|---\|---\| ⏎ \| `api.py` \| 84 \| 6 \| 1… |
| A19 | table | ③ 计算结果 | 2388..2660 / L66–L71 | \| 工况 \| 结果 \| 关键数字 \| ⏎ \|---\|---\|---\| ⏎ \| 全冰封（无可行路） \| `FAILED` \| primary=None；理由：balance… |
| A20 | table | ③ 计算结果 | 2676..2987 / L75–L80 | \| 航线 \| 长度 nm \| 油耗 t \| 航时 h \| sha256（前 16） \| ⏎ \|---\|---\|---\|---\|---\| ⏎ \| balanced \|… |
| A21 | figure_declaration | ④ 结果图 | 2999..3049 / L84–L84 | 图1 边界工况：全冰封判决（左）与单通道走廊强制穿越（右）（冰封判决与走廊强制穿越，背景为冰厚场）； |
| A22 | figure_declaration | ④ 结果图 | 3050..3092 / L85–L85 | 图2 route/ 求解核心逐模块分支覆盖（逐模块分支覆盖 vs 80% 判据线）； |
| A23 | figure_declaration | ④ 结果图 | 3093..3136 / L86–L86 | 图3 基准冰场 4 条已知航线（回归锁对象）（回归锁对象的 4 条已知航线叠冰厚场）。 |
| A24 | limitation | ⑤ 注意点 | 3163..3268 / L90–L91 | 1. **"零和权重"不是无害输入**：`0·inf = nan` 污染不可通行边的代价数组，"最小代价"退化为搜索顺序上的 ⏎    第一条可行路径（近似跳数最短路），结果看起来完全合法。第… |
| A25 | limitation | ⑤ 注意点 | 3269..3370 / L92–L93 | 2. **NaN 能绕过范围检查**：`np.any(arr < 0)` 对 NaN 恒假；冰厚/密集度的 NaN 会静默流入插值和边代价， ⏎    因此闸门用 `isfinite` + 上… |
| A26 | limitation | ⑤ 注意点 | 3371..3428 / L94–L94 | 3. **闸门是拒收不是裁剪**：边界值（h=20 m、T=−60 ℃、C=1）必须放行，另有专门测试防过度拒收。 |
| A27 | limitation | ⑤ 注意点 | 3429..3595 / L95–L97 | 4. **局限**：基准冰场是理想化构造（非 A2 观测产品），回归锁只锁"同一构造下的同一解"，不构成对真实冰区 ⏎    的绝对正确性主张；走廊是 9×15 玩具网格，用于拓扑判据而非标定… |
| A28 | external_dataset | ⑤ 注意点 | 3450..3459 / L95–L95 | 非 A2 观测产品 |
| A29 | limitation | ⑤ 注意点 | 3596..3659 / L98–L98 | 5. **D1 边界**：本节点不引入新求解算法；若 D1 分支后合入主干，三处闸门（注释含 `IN16-K9`）可机械重放。 |
| A30 | table | ⑥ 误差判定 | 3686..3978 / L102–L107 | \| 关键量 \| 基准 \| 误差 \| 是否 <3% \| ⏎ \|---\|---\|---\|---\| ⏎ \| 权重齐次标定（×10）后航线摘要 \| 原摘要 \| 0（逐位一致）… |
| A31 | error_judgment_statement | ⑥ 误差判定 | 3980..4140 / L109–L112 | 对最后一项的显式说明：走廊航线按 8 邻域对角线行走，长度必然大于分段大圆下界（本测例 ⏎ 8.62%），这是**网格离散度量**而非物理模型误差；判据因此定义为 ⏎ "≥ 解析下界（不可能更… |

## ⑤ 注意点与局限

1. **平台 title 与 markdown H1 不同文**：平台 `title`=`IN16-K9 冰区 A* 航线测试面第二刀：64 项测试全绿 / 分支覆盖 90.21% / 回归锁 MATCH`，H1=`# IN16-K9 冰区 A* 航线测试面第二刀：边界工况 · 负例拒收 · 回归锁`。manifest 的 `source.title`
   登记平台权威字段，H1 作为 A01 的 locator 原文保留，差异记入 `observations[O1]`——**不合并改写**。
   下游若按 title 匹配需知此差异。
2. **代码/工件不可达**：报告引用的 `route/` 包与 `route_lock.json`/`summary.json` 不在本工作树，
   故本包只能证明"报告里确实这样写了"，**不能证明这些文件存在或其哈希**。这是 01 工序的固有边界，
   不是本包的疏漏；如后续需要字节级核验，应由 02/03 工序或源码仓侧补证。
3. **图件无载荷**：三条 `figures[]` 只有 name+caption，无 `png_base64`，无字节可哈希；登记为
   `referenced_unresolved`，未用零字节占位冒充"已解析"。
4. **回归锁哈希只有前 16 位**（源文如此，如 `8c3d6e38fe4a1a7f…`）：本包按前缀登记，**不作全量哈希主张**。
5. **schema 的权威在平台侧**：`kf_result` 结构按契约文字（package_id/task_type/report_id/provenance/outputs）
   与已验收的 wp-448-01 / wp-542-01 先例实现；若平台侧真 schema 不同，`schema_pass` 应以平台为准，
   本包接受返修（主要残余风险，与 wp-448-01 同源）。
6. **未越界**：未读写任何其它 report_id，未改上游产物，未写任何 verified 标记；`claims=[]` 系契约允许
   （`no_forced_claim_generation`），并附 ≥20 字符理由。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据（由 verify_5761.py 程序复算） |
|---|---|---|
| valid_json | **PASS** | {"files": ["asset_manifest.json", "kf_result.json", "schema/…schema.json", "schema_binding.json"], "note": "all four parsed by json.loads"} |
| source_hash_matches | **PASS** | {"contract_sha256": "06f7e6a9d2164c64a916d4f11cc0e117af97766de133438d10fc884a35c2c4d7", "refetched_sha256": "06f7e6a9d2164c64a916d4f11cc0e117af97766de… |
| schema_pass | **PASS** | {"schema": "docs/kf/wp-5761-01/schema/asset_manifest.v1.wp-5761-01.schema.json", "schema_sha256": "8251cc03c9566cbe225a9329e767e6b692a550e805565f09e6a… |
| source_locator_resolvable | **PASS** | {"assets_checked": 31, "spans_resolved": 31, "failures": [], "method": "re-slice fresh markdown at [start_char,end_char), compare to quote, count occu… |
| no_duplicate_ids | **PASS** | {"asset_ids": ["A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "A10", "A11", "A12", "A13", "A14", "A15", "A16", "A17", "A18", "A19", "A… |
| counts_consistent | **PASS** | {"assets": 31, "by_resolution": {"resolved_in_source": 22, "referenced_unresolved": 8, "declared_absent": 1}, "by_class_rows": 31} |
| all_claims_have_evidence_or_explicit_unresolved_status | **PASS** | {"claims": 0, "offenders": [], "note": "claims=[] by contract (objective.register_assets only, classify_report_type=false); asset-level resolution sta… |
| no_verified_markers | **PASS** | {"structural_hits": [], "note": "producer must not mark anything verified (verification is the platform gate's job); the envelope carries only provena… |
| result_envelope_shape | **PASS** | {"keys": ["outputs", "package_id", "provenance", "report_id", "schema_version", "task_type"], "artifact_sha256": "962793f37a9fb02feaf606d7ca54bbbee221… |
| figures_present | **PASS** | {"fig_asset_inventory.png": 91648, "fig_locator_map.png": 64633} |

**三项数值判据**：源哈希 `06f7e6a9d216`（契约 = 重拉 = manifest = 信封 = 本地副本，5 处一致）；
locator 切片命中 31/31（逐字比对 + 唯一性 + 行号回算）；id/计数一致（31 条、
无重复、by_class 求和 = 31）。

**误差判定说明（诚实声明）**：本工序**不产生物理量计算**，因此不存在"关键量 vs 基准 <3%"的误差判定对象；
可判定的三量都是**精确量**（SHA-256 字节相等、切片逐字相等、id 集合相等），结果为 0 误差/逐位一致。
报告原文自身的数值（64 项测试、90.21% 分支覆盖、8.620% 走廊离散误差等）在本工序**只做定位登记、
不做复算**，不得引用为本包的核验结论——复算属下游工序；原文对 8.620% 已显式声明"否，且不应如此要求"，
本包不改变其结论强度。

```
# 一键复跑（工作树根执行；需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
python3 scripts/kf/build_asset_manifest_5761.py && python3 scripts/kf/verify_5761.py \
  && python3 -m pytest tests/test_kf_wp_5761_01.py -q && python3 scripts/kf/publish_5761.py
```

```json
{
  "schema_version": "kf_result.v1",
  "package_id": "wp-5761-01",
  "task_type": "01-asset-registration",
  "report_id": "5761",
  "provenance": {
    "source_uri": "tensor://reports/5761",
    "source_field": "markdown",
    "source_hash": "sha256:06f7e6a9d2164c64a916d4f11cc0e117af97766de133438d10fc884a35c2c4d7",
    "hash_algo": "sha256",
    "hashed_bytes": "markdown encoded as utf-8",
    "source_chars": 4141,
    "source_bytes_utf8": 7172,
    "source_title": "IN16-K9 冰区 A* 航线测试面第二刀：64 项测试全绿 / 分支覆盖 90.21% / 回归锁 MATCH",
    "scenario_key": "ship/ice-route/test-surface",
    "contract_version": "1.0",
    "lane": "C",
    "work_package": "wp-5761-01",
    "retrieved_via": "GET http://127.0.0.1:8010/api/v1/tensor/reports/5761",
    "local_copy": "docs/kf/wp-5761-01/report_5761.markdown",
    "generator": "scripts/kf/build_asset_manifest_5761.py",
    "verifier": "scripts/kf/verify_5761.py",
    "verification_note": "not_verified: verification is computed by the platform gate only; the producer does not certify its own products"
  },
  "outputs": {
    "asset_manifest.json": {
      "artifact_path": "docs/kf/wp-5761-01/asset_manifest.json",
      "artifact_sha256": "962793f37a9fb02feaf606d7ca54bbbee221d09c048cfbac1b9ed18ce9971940",
      "artifact_bytes": 30797,
      "schema": "asset_manifest.v1",
      "schema_path": "docs/kf/wp-5761-01/schema/asset_manifest.v1.wp-5761-01.schema.json",
      "schema_sha256": "8251cc03c9566cbe225a9329e767e6b692a550e805565f09e6a6717b90b33c73",
      "package_id": "wp-5761-01",
      "task_type": "01-asset-registration",
      "report_id": "5761",
      "counts": {
        "assets": 31,
        "by_class": {
          "document": 1,
          "statement": 1,
          "method_scope_declaration": 1,
          "cost_function_definition": 1,
          "case_declaration": 1,
          "scope_statement": 1,
          "method_step": 2,
          "source_code_reference": 3,
          "boundary_case_set": 1,
          "negative_case_set": 1,
          "data_artifact_reference": 2,
          "toolchain_declaration": 1,
          "table": 5,
          "figure_declaration": 3,
          "limitation": 5,
          "external_dataset": 1,
          "error_judgment_statement": 1
        },
        "by_resolution": {
          "resolved_in_source": 22,
          "referenced_unresolved": 8,
          "declared_absent": 1
        },
        "resolved_in_source": 22,
        "referenced_unresolved": 8,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "document",
          "label": "报告 markdown 全文（源资产本体）",
          "in_report_section": "全文",
          "locator": {
            "method": "document",
            "start_char": 0,
            "end_char": 4141,
            "start_line": 1,
            "end_line": 112,
            "quote": "# IN16-K9 冰区 A* 航线测试面第二刀：边界工况 · 负例拒收 · 回归锁",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "整份 markdown 即源资产；locator.method=document 表全文级，quote 取 H1 行作可核验锚点；end_char=4141 == source chars，start_line=1，end_line=112"
        },
        {
          "asset_id": "A02",
          "asset_class": "statement",
          "label": "结论段：PASS + 64 项测试 / 51 负例 / 90.21% 分支覆盖 / 回归锁 MATCH",
          "in_report_section": "结论",
          "locator": {
            "method": "char_span",
            "start_char": 44,
            "end_char": 194,
            "start_line": 3,
            "end_line": 6,
            "quote": "**结论**：PASS。新增测试 **64** 项全绿、负例 **51** 项、\n求解核心分支覆盖 **90.21%**（175/194，判据 ≥80%）、\n基准航线 sha256 回归锁 **MATCH**。求解算法（A* 搜索 / 代价合成 / 冰阻力-推进链 /\n风险矩阵）**零数值改动**。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "只登记位置与原文，不抽取 claim；数字以本段逐字为准"
        },
        {
          "asset_id": "A03",
          "asset_class": "method_scope_declaration",
          "label": "作用域声明：航线优化层 modules.green_navigation_ice.route 的求解链",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 223,
            "end_char": 417,
            "start_line": 10,
            "end_line": 12,
            "quote": "对象是船舶绿色航行-冰区域求解链上的**航线优化层** `modules.green_navigation_ice.route`：\n\"A2 冰情场 → 冰阻力与推进链（W3-N11）→ 冰中可达航速/油耗 → IMO MSC.1/Circ.1519 POLARIS 风险指数\n+ B2 结构载荷包络 → GO/CAUTION/NO-GO 分区 → 8 邻域网格 A*\"。代价为三目标加权和",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "给出 A2 冰情场→阻力推进→POLARIS/B2→GO/CAUTION/NO-GO→A* 的链路声明"
        },
        {
          "asset_id": "A04",
          "asset_class": "cost_function_definition",
          "label": "三目标加权代价函数 J",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 419,
            "end_char": 503,
            "start_line": 14,
            "end_line": 14,
            "quote": "$$J = w_E\\,\\frac{E}{E_{ow}} + w_T\\,\\frac{T}{T_{ow}} + w_R\\,\\frac{R}{\\Delta s_{gc}}$$",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "公式为原文 LaTeX，未改写"
        },
        {
          "asset_id": "A05",
          "asset_class": "case_declaration",
          "label": "基准冰场几何（57×31 格，9.61×10.07 nm）+ 起终点 + 船型 arctic_bulker_45",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 505,
            "end_char": 657,
            "start_line": 16,
            "end_line": 18,
            "quote": "NO-GO/LAND 是硬约束（删边），CAUTION 进入风险代价。基准冰场为理想化喀拉海走廊\n（57×31 格，格距 9.61×10.07 nm），\n起点 [68.6, 57.5] → 终点 [72.2, 83.0]；船型 `arctic_bulker_45`（PC6，Cb 几何自校验 PASS）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "几何/起终点/船型同段给出；Cb 几何自校验结论在原文中为 PASS"
        },
        {
          "asset_id": "A06",
          "asset_class": "scope_statement",
          "label": "节点作用域=测试面（只补测试不改算法）",
          "in_report_section": "① 案例介绍",
          "locator": {
            "method": "char_span",
            "start_char": 659,
            "end_char": 708,
            "start_line": 20,
            "end_line": 20,
            "quote": "本节点的作用域是**测试面**（战役规定\"只补测试不改算法\"）：把 D1 交付的求解器在边界工况、",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "该句是「零数值改动」主张的原文边界"
        },
        {
          "asset_id": "A07",
          "asset_class": "method_step",
          "label": "步骤1 纳入既有实现：astar/optimize/risk/field/speed/api 六模块",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 754,
            "end_char": 933,
            "start_line": 25,
            "end_line": 27,
            "quote": "1. **纳入既有实现**：IN10-D1 的 `route/` 包原样进入本工作树（`astar.py` 8 邻域 A* + 可采纳启发式、\n   `optimize.py` 代价与双基线、`risk.py` POLARIS+B2、`field.py` A2 场契约、`speed.py` C3 剖面、`api.py`\n   REST 端点），算法行未改；",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "六模块名逐一出现在 quote 内"
        },
        {
          "asset_id": "A08",
          "asset_class": "source_code_reference",
          "label": "第二刀测试文件 route/tests/test_route_second_cut.py（64 项）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 934,
            "end_char": 993,
            "start_line": 28,
            "end_line": 28,
            "quote": "2. **第二刀测试面** `route/tests/test_route_second_cut.py`（64 项）：",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_file_lookup",
            "result": "unresolved"
          },
          "note": "报告给出路径但该文件不在本交付工作树内，也无内联内容，无法核验哈希"
        },
        {
          "asset_id": "A09",
          "asset_class": "boundary_case_set",
          "label": "边界工况集（全冰封/单通道走廊/无缺口墙/起点 NO-GO/扩展上限 120）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 994,
            "end_char": 1117,
            "start_line": 29,
            "end_line": 30,
            "quote": "   * 边界工况用**确定性构造小冰场**（无随机项）：全冰封（h=3 m、C=1 → 载荷比 3>1 → NO-GO）、\n     单通道走廊（9×15、7 号列冰封、唯一缺口 (4,7)）、无缺口墙、起点落在 NO-GO、扩展上限 120；",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "明确「无随机项」=确定性构造"
        },
        {
          "asset_id": "A10",
          "asset_class": "negative_case_set",
          "label": "负例集（冰况谱越界/负风险/退化权重/C3-B2 契约/REST 非法请求）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1118,
            "end_char": 1223,
            "start_line": 31,
            "end_line": 32,
            "quote": "   * 负例：冰况谱越界（NaN/Inf 与物理上下界、经纬网格越界）、负风险/NaN 风险、退化代价权重\n     （零和/负/NaN/非 3 元）、C3 速度剖面与 B2 包络契约、REST 层非法请求；",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "负例口径=拒收（非法输入必须失败）"
        },
        {
          "asset_id": "A11",
          "asset_class": "source_code_reference",
          "label": "回归锁生成脚本 make_route_lock.py",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1233,
            "end_char": 1253,
            "start_line": 33,
            "end_line": 33,
            "quote": "`make_route_lock.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_file_lookup",
            "result": "unresolved"
          },
          "note": "脚本不在本工作树，仅路径可定位"
        },
        {
          "asset_id": "A12",
          "asset_class": "data_artifact_reference",
          "label": "回归锁文件 artifacts/ice_route_second_cut/route_lock.json",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1319,
            "end_char": 1367,
            "start_line": 34,
            "end_line": 34,
            "quote": "`artifacts/ice_route_second_cut/route_lock.json`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_file_lookup",
            "result": "unresolved"
          },
          "note": "锁文件路径被引用但未随报告提供；哈希只能核验其存在性主张，不能核验内容"
        },
        {
          "asset_id": "A13",
          "asset_class": "method_step",
          "label": "步骤3 输入闸门（field/risk/optimize/REST，唯一代码改动）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1387,
            "end_char": 1604,
            "start_line": 35,
            "end_line": 38,
            "quote": "3. **输入闸门（本节点唯一代码改动，全部为\"拒收\"而非\"裁剪\"）**：\n   `field.IceGrid.__post_init__` 冰况谱有限性与上下界；`risk.validate_risk_density`（负风险＝负代价边）；\n   `optimize.validate_weights`（零和权重使\"最小代价\"退化为任意路径，且 `0·inf = nan` 污染代价数组），\n   REST 层复用同一闸门（单源）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "原文声明闸门为「拒收」而非「裁剪」"
        },
        {
          "asset_id": "A14",
          "asset_class": "toolchain_declaration",
          "label": "步骤4 工具链（pytest junitxml / coverage --branch / matplotlib）",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1605,
            "end_char": 1730,
            "start_line": 39,
            "end_line": 40,
            "quote": "4. **工具链**：pytest(junitxml) + coverage(--branch) + matplotlib + `run_second_cut.py`\n   （判据汇总 → `summary.json` → 报告 md，数字零手抄）。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "工具链声明；具体版本号原文未给（不补）"
        },
        {
          "asset_id": "A15",
          "asset_class": "source_code_reference",
          "label": "第二刀运行脚本 run_second_cut.py",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1669,
            "end_char": 1688,
            "start_line": 39,
            "end_line": 39,
            "quote": "`run_second_cut.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_file_lookup",
            "result": "unresolved"
          },
          "note": "脚本不在本工作树"
        },
        {
          "asset_id": "A16",
          "asset_class": "data_artifact_reference",
          "label": "判据汇总工件 summary.json",
          "in_report_section": "② 怎么做的",
          "locator": {
            "method": "char_span",
            "start_char": 1700,
            "end_char": 1714,
            "start_line": 40,
            "end_line": 40,
            "quote": "`summary.json`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_file_lookup",
            "result": "unresolved"
          },
          "note": "工件被引用但未提供内容；报告称数字由其产出"
        },
        {
          "asset_id": "A17",
          "asset_class": "table",
          "label": "判据表（5 项判据 / 目标 / 实测 / 结论）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 1748,
            "end_char": 1996,
            "start_line": 44,
            "end_line": 50,
            "quote": "| 判据 | 目标 | 实测 | 结论 |\n|---|---|---|---|\n| 第二刀新增测试项 | ≥14 | **64**（全绿 64） | PASS |\n| 负例项（拒收/失败类） | ≥4 | **51** | PASS |\n| 新增逻辑分支覆盖 | ≥80% | **90.21%**（175/194） | PASS |\n| 回归锁 sha256 | 一致 | **MATCH** | PASS |\n| route 包全量 | 全绿 | 77/78（skip 1） | PASS |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "5 行判据全在 quote 内，未抄写任何数字到别处"
        },
        {
          "asset_id": "A18",
          "asset_class": "table",
          "label": "逐模块分支覆盖表（6 模块 + 合计）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2019,
            "end_char": 2377,
            "start_line": 54,
            "end_line": 62,
            "quote": "| 模块 | 语句 | 分支 | 分支覆盖 | 语句覆盖 |\n|---|---|---|---|---|\n| `api.py` | 84 | 6 | 100.00% | 93.33% |\n| `astar.py` | 89 | 36 | 91.67% | 95.20% |\n| `field.py` | 195 | 50 | 94.00% | 97.55% |\n| `optimize.py` | 298 | 70 | 84.29% | 93.48% |\n| `risk.py` | 130 | 20 | 95.00% | 99.33% |\n| `speed.py` | 51 | 12 | 91.67% | 96.83% |\n| **合计** | 847 | 194 | **90.21%** | 96.93% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "合计行 847/194/90.21%/96.93% 在 quote 内"
        },
        {
          "asset_id": "A19",
          "asset_class": "table",
          "label": "边界工况实测表（4 工况）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2388,
            "end_char": 2660,
            "start_line": 66,
            "end_line": 71,
            "quote": "| 工况 | 结果 | 关键数字 |\n|---|---|---|\n| 全冰封（无可行路） | `FAILED` | primary=None；理由：balanced: goal 不可达（不存在可通行路径） |\n| 单通道走廊 | `CONVERGED` | 穿越缺口 (4,7)：True；长度 161.68 nm；绕缺口几何下界 148.85 nm；no-go 段 0 nm |\n| 走廊无缺口 | `FAILED` | 不可达（如实 FAILED） |\n| 扩展上限 120 | `FAILED` | 如实 FAILED，不返回截断路径 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "含 FAILED 如实计数"
        },
        {
          "asset_id": "A20",
          "asset_class": "table",
          "label": "回归锁航线表（4 条航线长度/油耗/航时/sha256 前缀）",
          "in_report_section": "③ 计算结果",
          "locator": {
            "method": "char_span",
            "start_char": 2676,
            "end_char": 2987,
            "start_line": 75,
            "end_line": 80,
            "quote": "| 航线 | 长度 nm | 油耗 t | 航时 h | sha256（前 16） |\n|---|---|---|---|---|\n| balanced | 683.91 | 83.266 | 54.44 | `8c3d6e38fe4a1a7f…` |\n| min_energy | 697.12 | 82.873 | 55.46 | `7b32f7c66399d412…` |\n| min_time | 627.51 | 89.239 | 51.26 | `71e4c5aaa16d98d8…` |\n| min_risk | 690.47 | 83.000 | 54.95 | `8b0f4a4e9d974df0…` |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "sha256 仅给前 16 位（原文如此），登记为前缀截断，不作全量哈希主张"
        },
        {
          "asset_id": "A21",
          "asset_class": "figure_declaration",
          "label": "图1 边界工况（全冰封判决 / 单通道走廊穿越）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 2999,
            "end_char": 3049,
            "start_line": 84,
            "end_line": 84,
            "quote": "图1 边界工况：全冰封判决（左）与单通道走廊强制穿越（右）（冰封判决与走廊强制穿越，背景为冰厚场）；",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_file_lookup",
            "result": "unresolved"
          },
          "note": "④ 仅给图题文字；平台 figures[] 同索引条目也只有 name+caption，无 png_base64 载荷，故无字节可哈希"
        },
        {
          "asset_id": "A22",
          "asset_class": "figure_declaration",
          "label": "图2 逐模块分支覆盖 vs 80% 判据线",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 3050,
            "end_char": 3092,
            "start_line": 85,
            "end_line": 85,
            "quote": "图2 route/ 求解核心逐模块分支覆盖（逐模块分支覆盖 vs 80% 判据线）；",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_file_lookup",
            "result": "unresolved"
          },
          "note": "同上：图题存在、二进制载荷缺失"
        },
        {
          "asset_id": "A23",
          "asset_class": "figure_declaration",
          "label": "图3 基准冰场 4 条已知航线（回归锁对象）",
          "in_report_section": "④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 3093,
            "end_char": 3136,
            "start_line": 86,
            "end_line": 86,
            "quote": "图3 基准冰场 4 条已知航线（回归锁对象）（回归锁对象的 4 条已知航线叠冰厚场）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_file_lookup",
            "result": "unresolved"
          },
          "note": "同上：图题存在、二进制载荷缺失"
        },
        {
          "asset_id": "A24",
          "asset_class": "limitation",
          "label": "注意点1：零和权重使最小代价退化为任意可行路径",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 3163,
            "end_char": 3268,
            "start_line": 90,
            "end_line": 91,
            "quote": "1. **\"零和权重\"不是无害输入**：`0·inf = nan` 污染不可通行边的代价数组，\"最小代价\"退化为搜索顺序上的\n   第一条可行路径（近似跳数最短路），结果看起来完全合法。第二刀把它变成显式拒收。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "含 0·inf=nan 的机制解释"
        },
        {
          "asset_id": "A25",
          "asset_class": "limitation",
          "label": "注意点2：NaN 绕过范围检查",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 3269,
            "end_char": 3370,
            "start_line": 92,
            "end_line": 93,
            "quote": "2. **NaN 能绕过范围检查**：`np.any(arr < 0)` 对 NaN 恒假；冰厚/密集度的 NaN 会静默流入插值和边代价，\n   因此闸门用 `isfinite` + 上下界两段判据。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "闸门改用 isfinite + 上下界两段判据"
        },
        {
          "asset_id": "A26",
          "asset_class": "limitation",
          "label": "注意点3：闸门是拒收不是裁剪（边界值必须放行）",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 3371,
            "end_char": 3428,
            "start_line": 94,
            "end_line": 94,
            "quote": "3. **闸门是拒收不是裁剪**：边界值（h=20 m、T=−60 ℃、C=1）必须放行，另有专门测试防过度拒收。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "防过度拒收的专门测试在原文被提及"
        },
        {
          "asset_id": "A27",
          "asset_class": "limitation",
          "label": "注意点4：局限（理想化冰场/玩具网格/覆盖口径不含脚本层）",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 3429,
            "end_char": 3595,
            "start_line": 95,
            "end_line": 97,
            "quote": "4. **局限**：基准冰场是理想化构造（非 A2 观测产品），回归锁只锁\"同一构造下的同一解\"，不构成对真实冰区\n   的绝对正确性主张；走廊是 9×15 玩具网格，用于拓扑判据而非标定绕行代价量级；`figures.py`/`run_route.py`\n   脚本层不在\"新增逻辑\"覆盖口径（0%），其行为由工件存在性测试覆盖。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "适用范围声明：不构成真实冰区绝对正确性主张"
        },
        {
          "asset_id": "A28",
          "asset_class": "external_dataset",
          "label": "A2 观测冰情产品（被声明未使用）",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 3450,
            "end_char": 3459,
            "start_line": 95,
            "end_line": 95,
            "quote": "非 A2 观测产品",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "source_declaration_search",
            "result": "absent"
          },
          "note": "报告显式声明基准冰场为理想化构造、非 A2 观测产品；该外部数据集在源内被声明为不存在（子片段，落在 A27 段内）"
        },
        {
          "asset_id": "A29",
          "asset_class": "limitation",
          "label": "注意点5：D1 边界（不引入新算法，闸门可机械重放）",
          "in_report_section": "⑤ 注意点",
          "locator": {
            "method": "char_span",
            "start_char": 3596,
            "end_char": 3659,
            "start_line": 98,
            "end_line": 98,
            "quote": "5. **D1 边界**：本节点不引入新求解算法；若 D1 分支后合入主干，三处闸门（注释含 `IN16-K9`）可机械重放。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "给出合入主干后的可重放条件"
        },
        {
          "asset_id": "A30",
          "asset_class": "table",
          "label": "误差判定表（4 项，逐项问「是否 <3%」）",
          "in_report_section": "⑥ 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 3686,
            "end_char": 3978,
            "start_line": 102,
            "end_line": 107,
            "quote": "| 关键量 | 基准 | 误差 | 是否 <3% |\n|---|---|---|---|\n| 权重齐次标定（×10）后航线摘要 | 原摘要 | 0（逐位一致） | **是** |\n| 单目标解 vs balanced 解（自身目标） | balanced | 0.000%（min_* ≤ balanced，越界即失败） | **是** |\n| 回归锁 sha256（4 条航线 + 合计） | 锁文件 | MATCH（逐位） | **是** |\n| 走廊航线长度 vs 起点→缺口→终点大圆下界 | 148.848 nm（解析） | 8.620% | **否**，且不应如此要求 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "含一项答案为「否」的显式声明"
        },
        {
          "asset_id": "A31",
          "asset_class": "error_judgment_statement",
          "label": "对「走廊长度 8.620% 误差」的显式说明（网格离散度量而非模型误差）",
          "in_report_section": "⑥ 误差判定",
          "locator": {
            "method": "char_span",
            "start_char": 3980,
            "end_char": 4140,
            "start_line": 109,
            "end_line": 112,
            "quote": "对最后一项的显式说明：走廊航线按 8 邻域对角线行走，长度必然大于分段大圆下界（本测例\n8.62%），这是**网格离散度量**而非物理模型误差；判据因此定义为\n\"≥ 解析下界（不可能更短）且 ≤ 下界+15%\"，而不是假装满足 3%。真正可做 <3% 判定的三条数值项\n（齐次标定一致、单目标不劣、回归锁逐位）全部通过。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "原文把判据改为「≥下界且 ≤下界+15%」，未宣称满足 3%"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "every quote re-sliced from the same bytes and counted exactly once (scripts/kf/verify_5761.py, check source_locator_resolvable)",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true
      },
      "observations": [
        {
          "id": "O1",
          "kind": "title_mismatch",
          "detail": "平台报告 title 与 markdown H1 不同文：platform='IN16-K9 冰区 A* 航线测试面第二刀：64 项测试全绿 / 分支覆盖 90.21% / 回归锁 MATCH' / H1='IN16-K9 冰区 A* 航线测试面第二刀：边界工况 · 负例拒收 · 回归锁'。本包 source.title 登记平台权威字段，H1 作为 A01 locator 原文并保留差异，不合并改写。"
        },
        {
          "id": "O2",
          "kind": "figure_payload_absent",
          "detail": "平台 figures[] 三条仅含 name+caption，无 png_base64；④ 仅给图题。图1–图3 登记为 referenced_unresolved，未以零字节冒充已解析。"
        },
        {
          "id": "O3",
          "kind": "hash_prefix_only",
          "detail": "回归锁航线表只给 sha256 前 16 位（原文 8c3d6e38fe4a1a7f… 等），本包按前缀登记，不作全量哈希主张。"
        },
        {
          "id": "O4",
          "kind": "code_paths_not_in_worktree",
          "detail": "route/ 包、route/tests/test_route_second_cut.py、make_route_lock.py、run_second_cut.py、artifacts/ice_route_second_cut/route_lock.json、summary.json 均不在 TensorKnowledge 交付工作树内，按 referenced_unresolved 挂账，不猜路径、不臆造哈希。"
        }
      ]
    }
  }
}
```
