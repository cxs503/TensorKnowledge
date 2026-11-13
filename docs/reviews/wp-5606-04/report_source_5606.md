# IN18-T3 顶刊报告框架与防造假溯源管线（论文生产线 v2 血统）

## 1. 案例介绍

本节点不是物理算例，而是**论文生产线的基准面工程**：为船舶总体性能平台的审计报告建立
「证据冻结 → 数字注入 → 机器裁定」三段式管线。物理语境等价于一次**计量学实验**：
被测对象是平台自身的能力台账（21 项能力的证据等级与对账结果），
测量仪器是 SQL + SHA-256，被测量的真实值定义为「快照上重跑查询的结果」。

被冻结的真实工件：`/root/tp-agent/work/m4976/artifacts/capability_ledger/capability_ledger_resolved.json`；
快照哈希 `f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d67c7e20dfcb374f9f572`（采集于 `2026-11-07T00:50:00+00:00`），
含 n/a 能力行 / 证据行若干。

参数表（程序化注入，见第 3 节）：

| 参数 | 值 |
|---|---|
| 快照哈希（SQLite 字节 SHA-256） | `f46ab6f316a2c10c1c38b67594643eb0483c0e7cbe7d67c7e20dfcb374f9f572` |
| 溯源记录数 | 23（数字 20 / 图 3） |
| 强制块数 | 2 |
| 块内带标记数字 | 23 |
| 块内裸数字 | 0 |
| 重跑 SQL 条数 | 20 |
| 校验图件文件数 | 6 |
| 门禁裁定 | **PASS**（FAIL 0 / WARN 0） |

## 2. 怎么做的

- **快照层** `snapshot.py`：真实工件 JSON → SQLite（capability/evidence/视图）→ 对库文件字节取
  SHA-256 作 `snapshot_hash`；连接以 `mode=ro` 打开，校验器物理上无法改写自己的证据。
- **溯源层** `provenance.py`：稿中数字唯一合法形态为 `数值 {{prov:<id>}}`，记录绑定
  `(sql, params, snapshot_hash, snapshot_ts)`；强制范围是 `prov:begin/end` 块。
- **骨架层** `skeleton.py`：十节顶刊结构（Abstract/Introduction/System Architecture/Methods/
  Experimental Setup/Results/Discussion/Limitations/Threats to Validity/Reproducibility），
  结构校验检查缺节、**乱序（规范序号的单调性，而非名字集合相等）**、空节。
- **图件层** `figures.py`：饱和曲线 / 覆盖度热图 / 成功漏斗，数组全部由 SQL 窗口函数与分组查询产出，
  绘图代码只做坐标映射；PNG+PDF 双出，两文件哈希均入账。
- **门禁层** `verify.py`：重跑每条记录的 SQL、重算快照与图件哈希、比对印刷值，
  8 类 FAIL 码 + 2 类 WARN 码；`unverifiable` 一律不判 PASS。
- 工具链：Python 3.10 / matplotlib 2.4.6 后端 Agg / numpy / stdlib sqlite3；无新增第三方依赖。

## 3. 计算结果（全部程序化注入）

表 1 快照统计（来自 manuscript 的 Results 表，20 个数字记录，逐条可重跑）：

| 指标 | 值（SQL 注入） |
|---|---|
| 注册能力总数 | 21 |
| 证据行总数 | 10 |
| 带证据能力数 | 3 |
| 宣称 REAL | 18 |
| 对账 REAL | 1（4.8 %） |
| 一致 OK | 4（19.0 %） |
| 过度宣称 OVERCLAIM | 2（9.5 %） |
| 未验证 UNVERIFIED | 15 |
| 证据获取饱和比 | 0.300（3 能力 / 10 证据行） |
| 领域数 | 10 |

溯源记录与 SQL 对照（节选全部数字记录）：

| pid | 值 | SQL | 快照哈希前缀 |
|---|---|---|---|
| `n-004` | 21 | `SELECT COUNT(*) FROM capability` | `f46ab6f316a2` |
| `n-005` | 10 | `SELECT COUNT(*) FROM evidence` | `f46ab6f316a2` |
| `n-006` | 10 | `SELECT COUNT(DISTINCT domain) FROM capability` | `f46ab6f316a2` |
| `n-007` | 1 | `SELECT COUNT(*) FROM capability WHERE reconciled_level = 'REAL'` | `f46ab6f316a2` |
| `n-008` | 4.7619 | `SELECT 100.0 * SUM(CASE WHEN reconciled_level = 'REAL' THEN 1 ELSE 0 END) / COUNT(*) FRO` | `f46ab6f316a2` |
| `n-009` | 19.0476 | `SELECT 100.0 * SUM(CASE WHEN divergence = 'OK' THEN 1 ELSE 0 END) / COUNT(*) FROM capabi` | `f46ab6f316a2` |
| `n-010` | 21 | `SELECT COUNT(*) FROM capability` | `f46ab6f316a2` |
| `n-011` | 10 | `SELECT COUNT(*) FROM evidence` | `f46ab6f316a2` |
| `n-012` | 3 | `SELECT COUNT(*) FROM capability WHERE evidence_count > 0` | `f46ab6f316a2` |
| `n-013` | 18 | `SELECT COUNT(*) FROM capability WHERE claimed_level = 'REAL'` | `f46ab6f316a2` |
| `n-014` | 1 | `SELECT COUNT(*) FROM capability WHERE reconciled_level = 'REAL'` | `f46ab6f316a2` |
| `n-015` | 4.7619 | `SELECT 100.0 * SUM(CASE WHEN reconciled_level = 'REAL' THEN 1 ELSE 0 END) / COUNT(*) FRO` | `f46ab6f316a2` |
| `n-016` | 4 | `SELECT COUNT(*) FROM capability WHERE divergence = 'OK'` | `f46ab6f316a2` |
| `n-017` | 19.0476 | `SELECT 100.0 * SUM(CASE WHEN divergence = 'OK' THEN 1 ELSE 0 END) / COUNT(*) FROM capabi` | `f46ab6f316a2` |
| `n-018` | 2 | `SELECT COUNT(*) FROM capability WHERE divergence = 'OVERCLAIM'` | `f46ab6f316a2` |
| `n-019` | 9.52381 | `SELECT 100.0 * SUM(CASE WHEN divergence = 'OVERCLAIM' THEN 1 ELSE 0 END) / COUNT(*) FROM` | `f46ab6f316a2` |
| `n-020` | 15 | `SELECT COUNT(*) FROM capability WHERE divergence = 'UNVERIFIED'` | `f46ab6f316a2` |
| `n-021` | 0.3 | `SELECT COUNT(DISTINCT capability_id) * 1.0 / COUNT(*) FROM evidence` | `f46ab6f316a2` |
| `n-022` | 10 | `SELECT COUNT(DISTINCT domain) FROM capability` | `f46ab6f316a2` |
| `n-023` | 3 | `SELECT COUNT(DISTINCT reconciled_level) FROM capability` | `f46ab6f316a2` |

图件账本（文件字节哈希，替换即 FAIL）：

| pid | 图 | 文件 | sha256 前缀 |
|---|---|---|---|
| `fig-001` | fig1_saturation | fig1_saturation.png, fig1_saturation.pdf | `c2c890360ad3, 037bb6c488eb` |
| `fig-002` | fig2_coverage_heatmap | fig2_coverage_heatmap.png, fig2_coverage_heatmap.pdf | `00e5bb968654, fea7a9751b20` |
| `fig-003` | fig3_success_funnel | fig3_success_funnel.png, fig3_success_funnel.pdf | `f5a14a4b1ddf, d1996496a632` |

## 4. 结果图

图 1 证据获取饱和曲线：横轴为按 (capability_id, report_id) 排序后累计消耗的证据行数，
纵轴为累计获得证据的能力数；红点线为无饱和线性上界。终态饱和比 0.30 表示后半程证据行
几乎不再覆盖新能力——这是本报告"证据缺口"论断的量化来源。

图 2 覆盖度热图：领域 × 证据等级。REAL 列极稀疏，而 claimed REAL 达 18 项、
对账后仅 1 项 —— 这是本次审计最重要的定量发现。

图 3 成功漏斗：claimed 21 → reconciled → machine-checked → OK 4 → REAL 1，
各阶段为 SQL 谓词定义，计数单调不增，未做任何平滑。

（三图均为 PNG+PDF 双出，正文嵌入 PNG。）

## 5. 注意点（踩坑与局限）

1. `DISTINCT` 不支持窗口函数（SQLite 直接报错），饱和曲线改用 `firsts` CTE + 相关子查询实现
   累计去重计数；这保证了「图数组 = 一条可重跑 SQL」的性质不被破坏。
2. 构建镜像无 CJK 字体，图内刻度出现豆腐块 → 领域刻度改用英文转写，**数据值与 provenance 保留原文**，
   并在图注中声明；不做静默替换。
3. 门禁首版对 `表 1`、`图 1–3` 这类**结构序号**误判为裸数字 → 增加标签数码豁免规则；
   该豁免只在数字紧贴标签词时生效，测得的数值仍必须带标记（有单测覆盖）。
4. **契约级 bug 由负例测试抓到**：`validate_skeleton` 的乱序检查最初写成「文档序 vs 规范序过滤后
   的名字列表相等」，两列表恒等，永远不触发。改为规范序号的单调性检查后才真正能 FAIL。
   这是本节点最直接的教训：**没有负例的门禁等于没有门禁**。
5. 局限：① 只实现一种工件摄取器；② 哈希是篡改*证据*非*证明*（工作树无私钥，无法防一致重写）；
   ③ 强制范围仅 2 个块，非全文；④ 门禁判「值是否一致」不判「物理是否正确」；
   ⑤ 未知造假形态（重写工件→重建快照→一致重算哈希）可绕过，需外部时间戳/签名。

## 6. 误差判定

本节点无物理基准量，因此**不存在对实验/参考值的百分比误差**；「误差」被替换为两把更硬的尺子：

| 判据 | 定义 | 实测 | 是否通过 |
|---|---|---|---|
| 数字-记录一致 | 印刷值 vs 记录值（容差 = 半量级） | 20 条全部一致 | 是 |
| 记录-SQL 一致 | 记录值 vs 重跑 SQL（rtol 1e-9） | 20 条全部复现 | 是 |
| 快照未被改 | sqlite 字节哈希 | `f46ab6f316a2c10c…` 与清单一致 | 是 |
| 图件未被改 | PNG/PDF 字节哈希 | 6 个文件全部一致 | 是 |
| 负例可被拒 | 5 类伪造注入必须 FAIL | FABRICATED/SOURCE_DRIFT/SNAP_HASH/FIGURE_HASH/UNMARKED 全部命中 | 是 |
| 骨架完整性 | 十节齐备且有序 | 10/10 节，结构校验 PASS | 是 |

是否 <3%？—— 本节点无数值型物理基准，**不适用**；上述判据是**精确判定**（计数与哈希，
容差 0 或半量级），严于 3%。物理精度（阻力/推进/耐波等 <15%/<3%）仍归各物理验证节点。

自评：管线、门禁、负例、图件均达成；未完成项为「多工件摄取器」与「签名级防篡改」，如实列出不粉饰。
