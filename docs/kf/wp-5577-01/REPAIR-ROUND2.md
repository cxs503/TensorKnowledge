# wp-5577-01 · 第 2 轮修复报告（源载荷漂移归零 + 产物全量重放）

> 工序：KF 01（asset-registration）· 源报告 5577「BP 示范工程报告：Agent 科研生产闭环端到端实证」
> 分支：`agent/m21126` · 前序 PR#363 已由 owner 裁定关闭（2026-11-05），本单为重开后的第 2 轮。
> 本文件与 `drift_forensics.png` 由 `scripts/kf/wp5577_drift_forensics.py` 取证生成表格；
> 其余数字全部来自 `scripts/wp5577_build_report.py` 与 pytest 的实测输出。

## ① 案例介绍（这不是物理算例，是一份「包内自洽」的算例）

本工序的交付物是**一份平台报告的可达性登记包**：把 report 5577 的 markdown 载荷逐字节入包，
再把它引用的 23 条资产（数据表 / 图 / 跨仓代码 / 端点 / 文献 / 数据集 / 符号 / 声明缺项）
定位成 `(start_char, end_char, start_line, end_line, quote)` 五元组，并给出可达性证据。

被登记的源报告 5577 的物理内容（供读者判断上游价值）：KRISO 公开基准船 KCS 集装箱船静水
裸船体阻力预报，Lpp/B/T = 230.0/32.2/10.8 m，∇ = 52030 m³，Cb/Cm/Cwp = 0.6509/0.9849/0.7630，
设计点 24 kn（Fn = 0.2600），主链 = ITTC-57 摩擦 + ITTC-1978 粗糙度 + Holtrop–Mennen(1984) 兴波。

| 项 | 修复前（main @ 3a0bd3f） | 修复后（本分支） |
|---|---|---|
| 源载荷 `source/report_5577.md` | 3700 字符 / 5709 字节（旧版） | 3702 字符 / 5707 字节（平台当前版） |
| 哈希钉子 `source/markdown.sha256` | 指向平台版（3702） | 指向平台版（3702） |
| `asset_manifest.json` 的 `source.chars` | 3702（与载荷不符） | 3702（与载荷一致） |
| `acceptance.json` 验收项 | 16 项（旧构建器产物） | 18 项（现行构建器产物） |
| `pytest tests/test_kf_wp_5577_01.py` | 5 failed / 25 passed | 32 passed |

**一句话根因**：上一轮把「钉子 + 清单 + 报告」同步到了平台当前版，却漏掉了两个**源载荷文件**
（`source/report_5577.md`、`source/report_5577.json`），于是同一个包里并存两个源版本：
长度/哈希按 3702 版声明，引文与行号按 3700 版切片。包内自洽性检查（quote 切片、行号反算、
哈希钉子）随即全线判红。

## ② 怎么做的

1. **先证后做**：向平台 `GET /api/v1/tensor/reports/5577` 取 markdown，重算 sha256 =
   `60575cfe91ed…`，与仓内哈希钉子逐字符相等；构建器内部再双次拉取自比对（不一致即
   `SystemExit`）。**即：仓内钉子早已正确，错的是载荷文件没跟着落盘**。
2. **载荷逐字节落盘**：`source/report_5577.md` 写平台返回值（3702 字符 / 5707 字节），
   `source/report_5577.json` 写平台响应原样（12 个字段，仅 `markdown` 与旧版不同）。
3. **产物全量重放**：`python scripts/wp5577_build_report.py` 一次跑出 6 件工件
   （`asset_manifest.json` / `kf_result.json` / `acceptance.json` / `REPORT.md` /
   `fig1_asset_resolution.png` / `figure_probe.json`）。manifest 的 23 条 locator 全部重算，
   引文文本被改动的资产只有两条：A01（「全文」，即整篇 markdown）与 A12（`cluster_exec.py nodes`
   那句，`外协方` → `外协方`）；其余 21 条引文文本不变，但因该句出现在第 25 行，其后所有资产的
   `start_char/end_char` 整体平移 ±2 字符，故必须重算而非照旧。
4. **加两道重放门**（本轮新增，防同类漂移复发）：`test_builder_reproduces_committed_acceptance`
   与 `test_builder_reproduces_committed_report` —— 离线重放 `build_acceptance()` /
   `render_report()`，要求与提交的 `acceptance.json` / `REPORT.md` **逐字段、逐字节相等**。
   这两道门正是上一轮缺的那一环：旧构建器产物（16 项）在上一轮没有任何用例会判红。
5. **取证出图**：`scripts/kf/wp5577_drift_forensics.py` 把 HEAD 版与工作树版逐工件分类
   （旧版载荷 / 平台版载荷 / 混合 / 不含载荷），出 `drift_forensics.png`，并把下表注入本文件。

<!-- FORENSICS:BEGIN 由 scripts/kf/wp5577_drift_forensics.py 生成，勿手改 -->

| 工件 | HEAD（修复前） | 工作树（修复后） | 判定依据 |
|---|---|---|---|
| `source/report_5577.md` | stale | live | 含源载荷 → 比哈希/独有串 |
| `source/report_5577.json` | stale | live | 含源载荷 → 比哈希/独有串 |
| `source/markdown.sha256` | live | live | 含源载荷 → 比哈希/独有串 |
| `source/figure_probe.json` | n/a | n/a | 只登记探活结果，不含源载荷 |
| `asset_manifest.json` | mixed | live | 含源载荷 → 比哈希/独有串 |
| `kf_result.json` | live | live | 含源载荷 → 比哈希/独有串 |
| `acceptance.json` | mixed | live | 含源载荷 → 比哈希/独有串 |
| `REPORT.md` | mixed | live | 含源载荷 → 比哈希/独有串 |

两版载荷长度：旧版 3700 字符 / 5709 UTF-8 字节（sha256 `6e9baa26ba09…`）；平台版 3702 字符 / 5707 UTF-8 字节（sha256 `60575cfe91ed…`）。

哈希钉子 `source/markdown.sha256` 实际指向：平台版（正确）。

<!-- FORENSICS:END -->

## ③ 计算结果（程序化注入，零手抄）

| 量 | 修复前 | 修复后 | 判定 |
|---|---|---|---|
| 源载荷 sha256 | 钉子 `60575cfe…` vs 文件 `6e9baa26…`（**不符**） | 钉子 = 文件 = `60575cfe…` | 一致 |
| 源载荷字符数 / 字节数 | 3700 / 5709（与 manifest 声明的 3702 / 5707 不符） | 3702 / 5707 | 一致 |
| 验收项总数 / PASS | 16 / 16（旧构建器，无 AC17/AC18） | 18 / 18 | 一致 |
| `REPORT.md` 可被构建器逐字节复现 | 未知（无用例覆盖） | 是 | 一致 |
| `pytest tests/test_kf_wp_5577_01.py` | 5 failed, 25 passed | 32 passed | 一致 |

清单自洽性指标（同一份 `asset_manifest.json` 分别配两版载荷现算）：

<!-- CONSISTENCY:BEGIN 由 scripts/kf/wp5577_drift_forensics.py 生成，勿手改 -->

| 自洽指标（同一份 `asset_manifest.json`） | HEAD（清单 3702 声明 + 载荷 3700） | 工作树（清单与载荷同为平台版） |
|---|---|---|
| 资产条数 | 23 | 23 |
| quote == md[start:end]（切片自洽） | 7/23 | 23/23 |
| quote 在源 payload 中唯一 | 23/23 | 23/23 |
| 行号可由字符偏移反算 | 7/23 | 23/23 |

修复前切片不符的资产共 16 条：A03, A04, A05, A06, A07, A08, A10, A11, A12, A13, A15, A16, A20, A21, A22, A23。

<!-- CONSISTENCY:END -->

包内一致性矩阵（HEAD vs 工作树）见 ② 注入表与 `drift_forensics.png` 面板 A；本次修复后
8 个工件全部指向平台版载荷（`figure_probe.json` 只登记探活结果，不含载荷，判 `n/a`）。

## ④ 结果图

`drift_forensics.png`（本目录）两面板：

* **面板 A**：8 个工件 × {HEAD（修复前）, 工作树（修复后）} 的载荷归属矩阵。修复前呈
  「红（旧版载荷）+ 橙（混合）+ 绿（平台版）」三色混杂 —— 这就是同一包内并存两版载荷的
  直观证据；修复后整列转绿。
* **面板 B**：两版载荷的长度（字符 / UTF-8 字节）与哈希钉子归属。旧版 3700 字符 / 5709 字节，
  平台版 3702 字符 / 5707 字节；钉子指向平台版（`60575cfe…`）。

`fig1_asset_resolution.png`（本包 23 条资产的解析矩阵图）本轮**字节未变**
（sha256 `6bb04a76…`），因为它按解析类别着色，与载荷文本无关。

> 说明：本工序为登记类工序，无场量云图；`drift_forensics.png` 是「包内自洽性」的证据图，
> 不是流体场图。

## ⑤ 注意点

* **「同步了钉子不等于同步了源」**：本轮故障的全部教训。哈希钉子、manifest、acceptance、
  REPORT.md 都是**派生件**，只有 `source/report_5577.md` 是**唯一源**。派生件先更新、源文件
  没更新，就会出现「声明 3702 / 切片 3700」这种自相矛盾的包。修法不是手改引文，而是把源
  落盘后让构建器重算一切。
* **旧构建器产物是静默漂移**：`acceptance.json` 停在 16 项（缺 AC17/AC18 图字节探活正对照），
  在上一轮没有任何用例会判红——因为没有用例把「提交的 acceptance」和「构建器的输出」对照。
  本轮补的两道重放门就是补这个洞。
* **不代造跨仓内容**：`bp_demo/`、`physics/holtrop`、`cluster_exec.py`、`artifacts/bp_demo/
  sha256_index.json` 在本仓均不存在，仍登记为 `referenced_unresolved`；`README` 级的
  「顺手造个同名文件」被 AC14 反向校验禁止。
* **图字节仍然 404（这不是本轮的活）**：平台 record 声明了 3 张图，`GET
  /tensor/reports/5577/figures/<name>` 三个全部 404，而同路由正对照 report 11621 的
  `fig1_geometry.png` 返回 200 / 71730 B ⇒ 缺口在报告侧，非路由或平台缺能力。本包按纪律
  只登记 `referenced_unresolved` + `http_status` + 字节数，**不代画、不代填 sha256**。
* **范围外的同类漂移（未在本 PR 修）**：姊妹包 `docs/kf/wp-5577-04/` 的源快照
  `source/report_5577.md` 仍是旧版（3700 字符 / `6e9baa26…`），而其
  `source/report_5577.md.sha256` 已指向 `60575cfe…`，因此
  `tests/test_wp5577_review.py` 在 main 上即为红（与本次改动无关：该用例只读
  `docs/kf/wp-5577-04/**` 与 `scripts/wp5577_review*.py`，本 PR 未触）。修它需要重跑
  04 工序的审核脚本、重算其 locator 与 findings，属另一个功能点，故按「单 PR 单一功能点」
  纪律不在本单夹带，登记追讨。

## ⑥ 误差判定（本工序无物理量；关键量是哈希/长度/验收项，容差 0）

| 项 | 关键量 | 实测 | 基准 | 偏差 | 是否<3% |
|---|---|---|---|---|---|
| K1 | 源载荷 sha256 | `60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8` | 平台返回值 / 仓内钉子（同值） | 0 bit | **是（逐位相等）** |
| K2 | 源载荷字符数 / UTF-8 字节 | 3702 / 5707 | manifest.source.chars / bytes_utf8 声明值（同值） | 0 / 0 | **是（相等）** |
| K3 | locator 切片自洽 | 23/23 | 23（全部资产） | 0 条 | **是（100%）** |
| K4 | 验收项 PASS | 18/18 | 18 | 0 | **是（100%）** |
| K5 | 单测通过率 | 32/32 | 32 | 0 | **是（100%）** |

**是否 <3%**：本工序不涉物理量，五个关键量都是**离散可判定量**（哈希逐位、长度整数、条数计数），
容差为 **0**，实测全部**完全相等**，故「偏差 0% < 3%」成立（哈希按位相等比 3% 更强）。
不设「近似通过」：任一量不等即失败，这正是本轮 5 红 → 0 红的意义。

**HONEST-FAIL / 未运行项**：源报告侧的 V3（遗留 mock，偏差 243.10%）与 V4（KVLCC2 全尺度，
偏差 −17.26%）是**上游报告**的 honest-FAIL 结论，本工序只登记为资产、不作复核；外部 EFD
对标与七维指标「生态/商业/经济性」仍 **NOT RUN**（缺 KCS 试验原始数据表与跨仓口径证据）——
本包不以估算充数。