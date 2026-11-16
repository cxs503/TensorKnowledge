# wp-9645-01 — 证据可复现层（源资产快照）

本文件说明工作包 `docs/kf/wp-9645-01/`（report_id=9645，工序 01 asset-registration）
在新补的快照层下**怎么离线复核**，以及哪些复核项仍然不在本包边界内。

## 1. 原有缺口

工序 01 的产物把源报告 9645 的 SHA-256（`a8bb8902…fb00`，11824 字符）钉进了
`asset_manifest.json`，但**被哈希的字节没有进工作树**：

* `source.md` 只有摘要（690 B），`report_body.md` 只有登记报告（1.7 KB）——
  两者都不是 11824 字符的源 markdown；
* 于是 8 个 section 哈希、`locator_check.json` 的 `all_pass`、`sha256.txt` 的两行
  都成了「不可再推导的常数」，只能靠再问一次平台 API 才能核对；
* 换言之，`hash self-证` 这一项当时是**靠信任过的，不是靠重算过的**（WITHHELD 级证据），
  离线 CI 无法证伪任何一处哈希漂移。

## 2. 补的东西（不新增论断，只补被哈希的字节 + 复核工具）

| 文件 | 作用 |
|---|---|
| `source/report_9645.md` | 源 markdown 逐字节快照，15967 B / 11824 字符 / 196 行，`sha256:a8bb8902…fb00` |
| `source/record_9645.json` | record 元数据（id/title/summary/scenario_key/tags/figures/status/created_at…），`markdown` 载荷以 `markdown_sha256`/`markdown_chars` 指针替代 |
| `source/snapshot.json` | 快照自身 provenance：抓取时间、快照哈希/长度、与 manifest 钉住值的逐项比对结果 |
| `scripts/kf/wp_9645_01_snapshot.py` | `--fetch`（抓取→**先校验后落盘**，漂移即拒写）/ `--verify`（纯离线复核） |
| `tests/test_kf_wp9645_01.py` | 17 项验收回归：全部从快照重算，不需要网络与凭据 |
| `scripts/kf/wp_9645_01_inverse_audit.py` | 独立闭式复核（§5）：纯标准库重算整条可靠度链，出 `inverse_audit.{json,png}` |
| `tests/test_kf_wp9645_01_inverse_audit.py` | 17 项复核验收 + 6 条负控：门禁、数值路径交叉、局部性与证伪能力 |

抓取时脚本从 `asset_manifest.json` 读钉住值（零手抄），平台返回体一旦与钉住值不符，
`--fetch` 返回非零且**不覆盖**已提交快照——源头漂移必须由人显式处理，不允许被静默吸收。

## 3. 可重算矩阵（离线，`pytest tests/test_kf_wp9645_01.py`）

| 复核项 | 方式 | 结论 |
|---|---|---|
| 源哈希 / 字符数 / UTF-8 字节数 / 行数 | 对 `source/report_9645.md` 重算，与 manifest 钉住值比对 | 4/4 一致 |
| `asset_manifest.json` | `build_manifest(record)` 用快照重建，逐字段比对 | 除 `generated_at`（墙钟）外完全一致 |
| `asset_manifest.schema.json` | `build_schema(manifest)` | JSON 完全一致 |
| `locator_check.json` | `build_locator_check(manifest, snapshot)` | 完全一致，`all_pass=true`，8/8 |
| `report_body.md` / `source.md` / `sha256.txt` | 对应 builder 重建 | 逐字节一致 |
| `kf_result.json` 内嵌 manifest | 与磁盘 manifest 比对 | 完全一致 |
| 引用定位符（3 条：1 绝对路径 + 2 Python 模块） | 行号/整行引文/出现次数 | 3/3 在快照中逐字命中 |
| `asset_coverage.png` | PNG 魔数 + IHDR 尺寸 + 尾部 | 1782×881 / 61673 B，非 1×1 matplotlib 缺省占位 |

负控（证伪能力，防止「永远绿」的门）：

* 快照里翻转 1 个字符 → `verify_snapshot` 必须 `all_pass=false`（`sha256` 项失败）；
* 篡改 1 个 section 哈希 → `build_locator_check` 必须只在该项失败（计数恰为 1）；
* 给抓取工具喂漂移载荷 → `do_fetch` 返回 1 且已提交快照字节不变。

## 4. 边界（不做的事，如实登记）

* 快照是 **2026-11-15 抓取的字节**，不是「平台当前字节」的实时镜像；上游若编辑
  report 9645，需显式重跑 `--fetch`（脚本会先判断漂移）。
* `referenced_artifacts` 的 3 条引用（`/root/tp-agent/work/m8350/.../in101_n09_results.json`、
  `p_area_joint.py`、`target_reliability_inverse.py`）位于工作树之外，本包**不读取、不核验存在性**，
  `existence=not_checked` 保持不变——本次补的是「引文是否逐字在源里」这一层，不是工件内容一致性。
* `figures` 的 6 张图件载荷仍未下载（工序 01 只登记元数据）；`attachments.scan` 的
  6 次 markdown 图片语法命中已可从快照重算。
* 本包 `claims=[]`（工序 01 不抽取），因此登记层本身没有数值断言；
  但 report 9645 的可靠度链已由 §5 的独立闭式复核单独过门（51 项，3 % 门），
  那条链的误差判定不再为空——见 `inverse_audit.json` 的 `summary`/`checks`。

## 5. 独立闭式复核层（数值层：把「靠信任」换成「靠重算」）

### 5.1 补的原因

`claims=[]` 让本包当时**没有任何数值断言**需要 vs 基准比对（见 §4 第 4 条）：工序 01 只登记
「源资产是什么」。但 report 9645 的实质内容是**一整条可靠度链**（σ_lnF → ρ → κ* → γ_f*/ψ* →
ISO 表对裁决 → 负控），这条链此前只被产出它的求解器（`tensorphysics.structural.reliability`
的 FORM/Nataf/IS/MC）验证过——自证。若求解器与报告同错，登记侧看不出来。

### 5.2 补的方式（与求解器无关的第二条推导路径）

`scripts/kf/wp_9645_01_inverse_audit.py`：**纯标准库**（`json/math/re/statistics`，无
`tensorphysics`/`numpy`/`scipy` 模块级 import），从快照 ① 参数表解析输入，用闭式重算全链：

* 散度链：σ_lnA=0.339939、σ_lnp=0.201841、ρ_lnp,lnA=-0.673675、σ_lnF=0.271665、σ_lnR=0.119571、σ_tot=0.296815；
* 反问题：本问题失效域在对数正态空间是半空间 ⇒ Hasofer–Lind 距离即真值，
  κ* = exp(β_T σ_tot − q05 σ_lnR − q99 σ_lnF)、γ_f* = exp(−q99 σ_lnF + β_T σ_lnF²/σ_tot) 为**解析**解；
* ISO A.2×A.3 十行的 Δκ / 按表 β / 「不保守」判定列逐行复算；
* 负控（ρ=0）与 β_T 敏感性（表 7）复算；表 8 的 ∂β/∂θ 仅作参考，不入门禁。

**第二条数值路径（自检）**：u 空间复合 Simpson 积分求 P_f 再取 Φ⁻¹（步数 4000、区间 ±10，
Φ 用 `statistics.NormalDist`），并对 β_numeric(κ)=β_T 二分反解 κ*。它不做任何解析归约，
因此可以检验上面对闭式的推导本身：β(κ*) 闭式 4.000000000000 vs 数值 4.000000000000，κ* 闭式 1.431318073922 vs 数值 1.431318073922。

### 5.3 结果（51 项逐项门禁，3 % 门；数字由脚本写入 `inverse_audit.json`，本表从 JSON 注入）

| 关键量 | 报告值 | 独立闭式复核 | 相对误差 | <3 % ? |
|---|---|---|---|---|
| σ_lnF（计入负相关） | 0.2717 | 0.271665 | -1.28e-04 | 是 |
| σ_lnF（ρ=0 对照） | 0.4077 | 0.407736 | 8.82e-05 | 是 |
| ρ_lnp,lnA | -0.6737 | -0.673675 | 3.71e-05 | 是 |
| κ* | 1.43132 | 1.43132 | 5.16e-08 | 是 |
| γ_f* | 1.43706 | 1.43706 | 3.24e-07 | 是 |
| ψ* | 0.996007 | 0.996007 | -1.58e-07 | 是 |
| F*（设计点冰力） | 33.795 | 33.7953 | 7.60e-06 | 是 |
| R*（设计点抗力） | 33.795 | 33.7953 | 7.60e-06 | 是 |
| β(κ*)，物理模型 | 4 | 4 | 4.44e-16 | 是 |
| β（把 ρ=0 的 κ* 用到物理模型） | 4.6597 | 4.65973 | 7.27e-06 | 是 |

* 门禁统计：`n_gated=51`、`n_pass=51`、`n_fail=0`、`max|rel err|=1.28e-04`、`median=4.97e-06`、
  `verdict=PASS at 3 % gate`。
* 最大误差 1.28e-04 出现在 σ_lnF 一项——报告只印 4 位有效数字（0.2717 vs 0.271665），这就是舍入地板，
  不是模型差异。
* 图 `inverse_audit.png`：左=β(κ) 两条曲线（物理模型 / ρ=0 对照）+ 标定解 + ISO 表对的落点；
  右=报告值 vs 复核值的奇偶图（±3 % 带）。非场量云图，因为本包的对象是**标量与系数表**，
  没有空间场可画（理由如实登记）。

### 5.4 证伪能力（负控，`pytest tests/test_kf_wp9645_01_inverse_audit.py`，17 项）

| 动作 | 期望 | 实测 |
|---|---|---|
| β_T 4.0→4.3（表 1 一个数字） | κ*/γ_f* 与表 4 各行变红 | 命中 |
| β_T 4.0→3.9（+0.1 小漂移） | κ* 仍 <3 % 门（−2.9 %）→ 只能靠表 4 绝对差门抓到 | 命中（如实登记门的灵敏度） |
| ISO 表对 κ 1.4850→1.5500 | 只有该行的 Δκ/β 两项变红 | 命中（2 项） |
| 参数表 σ_lnF 0.2717→0.3000 | 只有 `sigma_lnF (correlated)` 变红 | 命中（1 项） |
| 特征冰力 F_k 23.517→25.000 | 只有 F*/R* 两项变红，κ* 不动 | 命中（2 项） |
| 删掉参数表 CoV 行 | 必须抛 KeyError，不许拿默认值算出一份绿表 | 命中 |

### 5.5 边界（本层不做、也做不了的事）

* **验的是换算，不是假设**：闭式与数值两条路径都吃同一套建模约定（年极值面积对数正态、
  单一幂律指数、抗力独立）。若约定本身错，本层跟着一起错——这需要外部实验/规范原文才能判，
  不在本包边界内。
* 表 2（FORM / 设计点 IS / 粗 MC / Rao–Blackwell）、表 3（伴随 vs 中心差分）是**求解器内部**
  一致性检查，没有第二条可离线重算的路径可独立复核；本层只对「求解器输出的中间量 → 报告表值」
  这一层负责。故这几项的证据等级仍是 WITHHELD（求解器自证），如实登记不升格。
* 表 8 的 ∂β/∂θ 只在 JSON 里做参考对照（不同差分步长可差几个百分点），不参与门禁。
* 本包 `claims=[]`（工序 01 不抽取），因此**没有**任何数值断言需要 vs 基准比对；
  误差判定项为空是合同允许的完整结果，不是空完成。
