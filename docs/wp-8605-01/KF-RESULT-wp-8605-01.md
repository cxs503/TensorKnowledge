# KF-RESULT wp-8605-01

工作包 `wp-8605-01` · task_type=`01-asset-registration` · report_id=`8605` · 仓：TensorKnowledge · 分支 `agent/m18080`

> **本包做什么、不做什么**：只做**源资产登记**（asset registration）——把 `tensor://reports/8605` 的 markdown 冻结成可复算的字节快照，把正文里机械可查的引用逐条登记成带 locator 的资产，并如实标注每条资产能否在本仓检出内解析。**不做抽取、不做分类、不产生内容层 claim、不补齐任何缺失资产、不生成替代数据**。

**一句话结论**：登记 36 项资产（10 类），其中 1 项 `resolved_in_source`（正文自身）、32 项 `referenced_unresolved`、3 项 `declared_absent`；源快照 sha256=`a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36`（8006 字符）与本包冻结副本逐字节一致；9 项自检门 **PASS**（另有 10 个负向对照用例证明这些检查真的能失败）。

---

## ① 案例介绍（被登记的对象是谁）

| 字段 | 值 |
|---|---|
| 报告 id / 平台 mission | `8605` / `7260` |
| 标题 | P138W2-N09 CII/EEXI 营运能效动态评级与碳强度漂移预警（四门过，实船锚 WITHHELD） |
| scenario_key | `P138W2-N09` |
| 主题（源报告自述） | CII/EEXI 营运能效动态评级 + 海况修正 + 漂移预警；四道机器门 + 实船锚 WITHHELD |
| 标签 | `CII`, `EEXI`, `营运能效`, `漂移预警`, `海况修正`, `OSSE`, `IMO` |
| 正文字符数 / UTF-8 字节 | 8006 / 13153 |
| markdown sha256 | `a0488678cd1241a31152fc71c6fc86856a77cbcc4c94612a78a8a20cdd4a8e36` |
| 平台元数据声明的图件 | 4 张（仅名称+说明，payload 不含 png 字节） |
| 取源方式 | `GET http://127.0.0.1:8010/api/v1/tensor/reports/8605`（登录后 Bearer token） |
| 冻结副本 | `docs/wp-8605-01/source_report_8605.md` |

源报告声明的图件（本包**只登记名字，不补齐字节**）：

| 图名 | 说明（源报告原文） | 状态 |
|---|---|---|
| `fig1_calibration.png` (A02) | 图1 年末 CII 预测校准：200 个 OSSE 仿真年，真值 vs 预测（±80% PI），虚线为 y=x | referenced_unresolved |
| `fig2_gate_deviation.png` (A03) | 图2 四道门实测偏差 vs 判据容差（对数轴）；第四组为 gate_4 的 80% PI 覆盖率 vs 名义 0.80 | referenced_unresolved |
| `fig3_annual_rating.png` (A04) | 图3 年度 CII 轨迹（观测/天气归一）叠加 A–E 评级边界与 6 月末年末预测（±80% PI） | referenced_unresolved |
| `fig4_weather_decomposition.png` (A05) | 图4 左：逐月海况功率增量份额 f_sea；右：碳强度漂移分解（观测=效率+天气） | referenced_unresolved |

源报告**自己声明缺失**的资产（本包按 `declared_absent` 登记，引用原文片段为证）：

| asset_id | 类别 | 原文片段（逐字） | 原文行 |
|---|---|---|---|
| `A34` | ship_anchor | 沙箱内没有 noon report / 船级社评级记录 | L125 |
| `A35` | model_test_table | 本仓无该表 | L120 |
| `A36` | regulation_text | 离线不可回读原文 | L124 |

## ② 怎么做的（方法 / 流程 / 关键设置 / 工具链）

1. **取源并断言作用域**：`GET /tensor/reports/8605`；若返回的 `id != 8605` 脚本直接退出——单报告作用域硬保护。
2. **冻结快照**：`markdown` 原样写入 `docs/wp-8605-01/source_report_8605.md`（不做换行/编码归一化）。若冻结副本已存在且与实时 API 不一致，脚本**拒绝覆盖并退出码 3**（防止源漂移悄悄改变登记结果）。
3. **机械扫描**：6 条确定性正则规则（无 LLM、无语义猜测）；同一 token 只登记一次（按 token 去重），locator 取**首次出现**位置，`unique` = 该 token 在全文是否只出现 1 次。
4. **locator 机器生成**：`quote = md[start:end]`（切片而非手打），`start_line/end_line` 由字符偏移数换行得到，`in_report_section` 由「该位置之前最近的 `## ` 标题」决定——三者都可被任何一方独立复算。
5. **解析判定（保守优先）**：只有「正文自身」算 `resolved_in_source`；另一仓/离线文本/外部服务一律 `referenced_unresolved`；报告自述缺失的三项用**原文声明片段**锚定为 `declared_absent`（不是本脚本的断言）。**没有任何一条被”补齐“**。
6. **自检门**：9 项检查（含 schema 校验、locator 重切、计数一致、规则召回、图形字节哈希、claim 证据），结果写 `verification.json`，任一失败脚本返回非 0。
7. **图形**：matplotlib(Agg) 三张图全部由 manifest/verification 现算，无随机、无时间戳。
8. **测试**：`tests/test_kf_wp8605.py` 25 个用例，其中 10 个是**负向对照**（篡改源/篡改 quote/偏移 span/改 section/伪造 resolved/双 id/改计数/丢规则命中/删图/改图字节/非 PNG/schema 反例）。

扫描规则与命中（全部命中均登记，去重只合并同一 token）：

| 规则 | asset_class | 登记数 | 示例 token |
|---|---|---|---|
| `fig\d_[a-z0-9_]+\.png` | figure_reference | 4 | `fig1_calibration.png` |
| `[A-Za-z_][A-Za-z0-9_./-]*\.py` | code_file | 12 | `api.py` |
| `[A-Za-z_][A-Za-z0-9_./-]*\.(?:json\|csv)` | data_artifact | 5 | `artifacts/op_cii_n09/forecast_calibration.csv` |
| `(?:backend\|artifacts)/[A-Za-z0-9_/]*/` | directory | 4 | `artifacts/op_cii_n09/` |
| `(?:MEPC\|ISO)[ .]\d+(?:\(\d+\))?` | standard_reference | 5 | `ISO 15016` |
| `(?:GET\|POST\|PUT\|DELETE) /[^\s`,、）)]+` | service_endpoint | 2 | `GET /evidence` |
| （声明缺失清单，人工锚定原文片段） | ship_anchor / model_test_table / regulation_text | 3 | `本仓无该表` |

工具链：Python 3 标准库（urllib/json/hashlib/re）+ jsonschema 4.26 + matplotlib 3.10.8；无第三方网络依赖，全部在本仓检出内执行。

## ③ 计算结果（数字表，程序化注入）

### 3.1 资产总量与解析分布

| 量 | 值 |
|---|---|
| 资产总数 | 36 |
| 类别数 | 10 |
| `resolved_in_source` | 1（仅 A01 正文自身） |
| `referenced_unresolved` | 32 |
| `declared_absent` | 3 |
| claim 数 | 3（全部 `supported`，**无一条标 verified**——verify 由平台门计算） |

| asset_class | 数量 | asset_id 范围 |
|---|---|---|
| code_file | 12 | `A06`–`A17` |
| data_artifact | 5 | `A18`–`A22` |
| standard_reference | 5 | `A27`–`A31` |
| directory | 4 | `A23`–`A26` |
| figure_reference | 4 | `A02`–`A05` |
| service_endpoint | 2 | `A32`–`A33` |
| document | 1 | `A01` |
| model_test_table | 1 | `A35` |
| regulation_text | 1 | `A36` |
| ship_anchor | 1 | `A34` |

### 3.2 自检门（PASS）

| # | check | 结果 | 证据摘要 |
|---|---|---|---|
| 1 | `source_hash_recomputed` | PASS | recomputed=`a0488678cd1241a3…` 与 manifest 一致，8006 字符 / 13153 字节 |
| 2 | `locators_reslice` | PASS | 36 条 locator 全部重切成功，失败 0 |
| 3 | `resolution_honesty` | PASS | resolved 1 / unresolved 32 / absent 3，伪造 0 |
| 4 | `counts_consistent` | PASS | 总数 36、类别 10、分布 3 项与实测逐项相等 |
| 5 | `asset_ids` | PASS | 36 个 id 唯一且符合 `A[0-9]{2}` |
| 6 | `figures_present` | PASS | 2 张图字节哈希已记录、PNG 签名有效（`fig_verification.png` 自指不入哈希） |
| 7 | `rule_recall` | PASS | 6 条规则 / 32 个不同 token，漏登记 0 |
| 8 | `claims_have_evidence` | PASS | C01, C02, C03 均带 evidence/evidence_locator |
| 9 | `schema_pass` | PASS | `schemas/asset_manifest.v1.generic.schema.json` 校验通过 |

### 3.3 产出物（sha256 现算）

| 文件 | 字节 | sha256（前 16） | 要点 |
|---|---|---|---|
| `asset_manifest.json` | 44147 | `3f9671f2952e104a…` | 主产物：36 资产 + 3 claim + 源哈希/字符数 |
| `fig_asset_inventory.png` | 73929 | `c378dd3359ea8e55…` | 图 1：资产类别 × 解析状态 |
| `fig_locator_coverage.png` | 84912 | `c8d8852d95091ac8…` | 图 2：locator 定位图 + 按类登记数 |
| `fig_verification.png` | 50827 | `27fe7f63c10ea9d9…` | 图 3：自检门逐项结果 |
| `source_report_8605.md` | 13153 | `a0488678cd1241a3…` | 源 markdown 逐字节快照（离线复算用） |
| `verification.json` | 3686 | `49c77fc9de82b009…` | 9 项自检结果 + 图件 sha256 锚 |

（本报告 `KF-RESULT-wp-8605-01.md` 不入上表：写入后自身字节即变，与 `fig_verification.png` 同理，避免自指哈希。）

## ④ 结果图（三张，程序化生成，无手抄）

| 图 | 内容 | 文件 | sha256（前 16） |
|---|---|---|---|
| 图 1 | 资产类别分布（按解析状态堆叠）+ 解析状态合计 | `fig_asset_inventory.png` | `c378dd3359ea8e55…` |
| 图 2 | 全部 35 条 char_span locator 在源文中的位置（按解析状态着色）+ 按类登记数（召回） | `fig_locator_coverage.png` | `c8d8852d95091ac8…` |
| 图 3 | 9 项自检门逐项 PASS/FAIL + 源哈希指纹 | `fig_verification.png` | `27fe7f63c10ea9d9…` |

**无场量云图的理由**：本工作包是资产登记（登记/定位/判定），不做数值求解，没有物理场可言；三张图画的是登记结果本身（分布 / 定位 / 自检），全部由 `asset_manifest.json` 与 `verification.json` 现算，图件 sha256 记入 `verification.json` 作为防替换锚（再跑一次 `verify` 会对不上即 FAIL——见负向对照）。

## ⑤ 注意点（踩过的坑 / 局限 / 适用范围）

1. **契约端点不存在**：`GET /tensor/kf/packages/wp-8605-01` 与 `/tensor/work-packages/wp-8605-01` 均返回 404，没有契约 `source_hash` 可比。因此 `integrity.hash_matches_contract` 显式置 **null**（=无法比对，不是「一致」），并在 `integrity_note` 写明原因。`hash_recomputed_locally` 指「冻结副本 vs 实时 API 逐字节一致」。
2. **旧 PR #158 的病**：它的文件清单里夹着 `ke/__pycache__/*.pyc` 两个编译缓存，且自带一份**单包专用** schema `schemas/asset_manifest.wp8605.v1.schema.json`（把 package_id/report_id 写成 const，其它工作包无法复用）。本次重开**不含任何 pycache**，并改用仓内既有 `schemas/asset_manifest.v1.generic.schema.json`（该文件的 description 明确要求不要为每个包新增 const schema）。
3. **源漂移保护**：登记值绑定源字节，若 API 上的 markdown 变了，脚本拒绝覆盖冻结副本（退出码 3）。要改登记必须显式删除快照重跑——这样「数字怎么来的」永远可追。
4. **自指图不入哈希**：`fig_verification.png` 从 `verification.json` 渲染，若把它自己的哈希写回该文件会形成循环。因此只有另两张图的 sha256 入锚，自指图只校验存在性与 PNG 签名；这一点在 `detail.not_hashed` 里写明。
5. **去重语义**：`gate_results.json`（正文以 `gate_results.json:ship` 形式引用）与 `artifacts/op_cii_n09/gate_results.json` 是两个不同 token，登记成两条资产——宁可多登记，不合并语义相近但字面不同的引用。
6. **召回 ≠ 完备**：6 条规则只覆盖「有形状」的引用（文件名/路径/标准号/端点）。正文里的散装数值、自然语言描述的外部数据不在登记范围（那是 task_type 02+ 的事），因此本包不能声称「报告里所有引用都登记了」，只能声称「规则命中 32/32 全部登记、0 漏」（`rule_recall` 门）。
7. **适用范围**：只对 report 8605 的 markdown 字段有效；不含 figures 字节、不含另一仓（ship-performance-platform）的代码与数据。所以本包**不产生任何船舶物理结论**，也不改变源报告的 WITHHELD 标签。

## ⑥ 误差判定（本包的「关键量」都是可精确复算的整数，逐项回答「是否 <3%」）

| 关键量 | 基准 | 本包实测 | 误差 | <3%？ |
|---|---|---|---|---|
| 源 markdown sha256 | 实时 API 返回的 markdown | 与冻结副本逐字节一致 | 0（完全相等） | **是** |
| 源字符数 / 字节数 | API 返回长度 | 8006 字符 / 13153 字节（重算相等） | 0 | **是** |
| locator 可重解析率 | 全部 36 条 | 36/36 | 0 | **是** |
| locator 归属章节 | 由字符偏移重算的最近 `## ` 标题 | 全部一致（失败 0） | 0 | **是** |
| 资产计数（总数/类别/分辨率） | 从资产表重算 | 逐项相等 | 0 | **是** |
| 规则召回 | 6 条正则命中的不同 token | 32/32 登记 | 0 | **是** |
| 图件字节 | 首次写入 `verification.json` 的 sha256 | 再验一致（篡改即 FAIL） | 0 | **是** |

**显式结论**：本包 6 类关键量全部是**恒等/计数类**检查，误差 **0%**（远小于 3%）；**没有任何物理量参与**，因此不存在「与实验/参考值比 15%」的判据可谈——源报告的物理锚（实船油耗/船级社评级）本身是 WITHHELD，本包按 `declared_absent` 继承该诚实标签，不做任何数值替代。

## ⑦ 复现与审计链

```bash
# 1) 取源 + 冻结 + 登记 + 出图 + 自检（需 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
python3 scripts/kf_fetch_8605.py
# 2) 仅从冻结副本重建（离线，不联网）
python3 scripts/kf_fetch_8605.py --from-cache
# 3) 单独重画三张图（并重算 verification.json）
python3 scripts/kf_figures_8605.py
# 4) 全量不变量测试（含负向对照）
python3 -m pytest tests/test_kf_wp8605.py -q
```

| 环节 | 脚本 / 文件 |
|---|---|
| 取源与登记 | `scripts/kf_fetch_8605.py`（`fetch_report` / `scan_assets` / `build_manifest` / `verify`） |
| 图形 | `scripts/kf_figures_8605.py` |
| 测试 | `tests/test_kf_wp8605.py` |
| 主产物 | `docs/wp-8605-01/asset_manifest.json` |
| 自检结果 | `docs/wp-8605-01/verification.json` |
| 源快照 | `docs/wp-8605-01/source_report_8605.md` |

## ⑧ 与既有工作的关系 / 与旧 PR #158 的差异

| 维度 | 旧 PR #158（已关闭） | 本次重开 |
|---|---|---|
| 编译缓存 | 含 `ke/__pycache__/*.pyc` 2 个 | **不含**任何 `__pycache__` |
| schema | 新建单包 const schema `asset_manifest.wp8605.v1.schema.json` | 复用仓内 `schemas/asset_manifest.v1.generic.schema.json`（包无关） |
| 源快照 | 未冻结，登记值不可离线复算 | 冻结 `source_report_8605.md` + 漂移保护（不一致拒绝覆盖） |
| 自检 | 仅 `verification.json` 静态记录 | 9 项门 + **规则召回门** + 图件 sha256 锚（再验比对） |
| 测试 | 无 | 25 个 pytest 用例，10 个负向对照 |
| 文件数 | 11（含 2 pyc + 1 单包 schema） | 10（含 1 泛型 schema 复用，0 编译产物） |

与仓内同族工作包（`docs/wp-448-01`、`docs/wp-5690-01`、`docs/kf/wp-14214-01`）保持同一 `asset_manifest.v1` 形状与同一登记纪律；本包新增的可复用件是 `check_figures`（图件字节锚 + 再验比对）与 `check_resolution_honesty`（禁止把无字节资产标成 resolved）。

