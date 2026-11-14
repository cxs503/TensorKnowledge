# KF-RESULT wp-12595-01

- package_id: `wp-12595-01` ｜ task_type: `01-asset-registration` ｜ report_id: `12595` ｜ lane: C ｜ repo: TensorKnowledge ｜ status: draft
- source: `tensor://reports/12595`（field=`markdown`），chars=6420，bytes=9931，sha256=`sha256:1233e5e4fece836d70b124a36a82438a1e48dbfddfc168b14f4c1f7efd7a08ce`
- 哈希核对：独立重算 == 契约声明 → **✅**；chars 6420 == 契约 6420 → **✅**；title/scenario_key 与契约一致 → **✅**
- 分层标签（原样登记、不解读）：`IN157-N06|in157_n06_simp_sensitivity_consistency|m`
- 状态：draft（verification 由平台门计算，本包不标 verified）

## ① 本工序做了什么

只做「源资产登记」，不做抽取、不做报告类型分类。核对 report_id=12595 与其 markdown 的字节哈希，登记：
平台记录元数据、正文小节切分（11 节，含行区间与每节 sha256）、
可解析附件（figures 4 条，仅 name/caption 元数据，无 png_base64 载荷）、
正文声明的引用（19 条：路径 11 / glob 1 / 字段 5 / worktree+branch 2），
并为每条引文提供逐字可定位 locator（27/27 全部命中）。
`claims` 为空数组——合同 `objective.register_assets=true` / `classify_report_type=false`，
且 notes 明确「claims 允许为空数组」，故不生成任何 claim（不做强制抽取）。

## ② 怎么做的（步骤/工具/关键设置）

1. **取原文**：`POST $TENSOR_API_BASE/auth/login` 取 token → `GET $TENSOR_API_BASE/tensor/reports/12595`
   （`scripts/kf_fetch_12595.py`）。只读 12595 一份；未读写任何其它 report_id（见 manifest `boundary`）。
2. **哈希复算**：`hashlib.sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 逐字节比对；
   同时比对字符数（运行时 6420 vs 契约 6420）与 UTF-8 字节数（9931）。
3. **小节切分**：按 ATX 标题切分，记录 `level/heading/line_start/line_end/chars/sha256`（11 节），供后续工序按节取证。
4. **引用抽取**：确定性规则——反引号代码片段按 path/glob/worktree/branch/field 分类；
   纯文本仅收「含斜杠+扩展名+字母」的路径 token（捕获判据表 C6 的 glob，排除 `0.4`/`1e-09` 等小数误报）。
   locator 一律取**原文整行**，因此逐字可定位（脚本机检，非人工粘贴）；
   观察项证据行带字面量断言（行内容不符即 SystemExit，拒绝编造）。
5. **附件登记**：读平台记录 `figures` 字段（4 条），只登记 name/caption 与载荷存在性标记；
   未下载、未解码图像。正文 §4 的 4 个 PNG 行与 figures 字段做 name+caption 逐字交叉核对（4/4 全中）。
6. **零手抄**：`scripts/kf/wp-12595-01/register_assets.py` 内无任何手写数字/引文；
   本报告数字与引文全部由 `make_report.py` 从 JSON 产物与原文行注入。
7. **自检**：`register_assets.py --check` 跑 schema 校验 + locator 逐字匹配 + id 唯一性 + 哈希一致性；
   `tests/kf/test_wp_12595_01.py` 回归（含负对照与离线复跑）。

关键设置：产物落 `docs/kf/wp-12595-01/`（git 可追踪）；工件存在性一律标 `not_checked`
（声明于 m11206 的 TensorPhysics worktree，跨树取证越界）。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-12595-01/kf_result.json` | 结果信封：package_id / task_type / report_id / provenance(source_hash,source_field,source_uri) / outputs / claims=[] |
| `docs/kf/wp-12595-01/asset_manifest.json` | 登记清单：source_asset（hash/size/metadata/layer hint）、attachments（4）、sections（11）、referenced_artifacts（19）、observations（3）、locator_check（27/27）、unresolved（2）、boundary |
| `docs/kf/wp-12595-01/fig_acceptance.png` | 验收图：左=引用按 kind 计数；右=acceptance 自检逐项（数据由 `fig_data.json` 程序化读取） |
| `docs/kf/wp-12595-01/kf_result_wp-12595-01.md` | 本报告（六段 + 唯一 json 块） |
| `scripts/kf/wp-12595-01/register_assets.py` | 生成器：`--check` 打印 acceptance 自检，`--from-file/--record-json` 支持离线复跑 |
| `scripts/kf/wp-12595-01/make_report.py` | 报告生成器（引文由 manifest 注入，json 块与产物同字节） |
| `scripts/kf/wp-12595-01/make_figure.py` | 验收图生成器 |
| `tests/kf/test_wp_12595_01.py` | 回归测试（schema/哈希复算/逐字引文/唯一性/确定性重建/单一报告边界/不标 verified） |

### 引用登记明细（19 条，locator=原文整行）

| ref_id | kind | 首现行 | 次数 | 原文 token | 存在性 |
|---|---|---|---|---|---|
| `12595-ref-01` | path | L3 | 1 | `artifacts/in157_n06_simp_sensitivity/acceptance.json` | not_checked |
| `12595-ref-02` | field | L33 | 3 | `longdouble` | not_checked |
| `12595-ref-03` | path | L37 | 1 | `simp/interface_adapter.py` | not_checked |
| `12595-ref-04` | field | L37 | 1 | `interface_contract` | not_checked |
| `12595-ref-05` | glob | L50 | 1 | `tests/test_simp_sensitivity_consistency*.py` | not_checked |
| `12595-ref-06` | path | L80 | 1 | `artifacts/in157_n06_simp_sensitivity/fig1_sensitivity_and_error_maps.png` | not_checked |
| `12595-ref-07` | path | L81 | 1 | `artifacts/in157_n06_simp_sensitivity/fig2_delta_convergence.png` | not_checked |
| `12595-ref-08` | path | L82 | 1 | `artifacts/in157_n06_simp_sensitivity/fig3_per_design_errors.png` | not_checked |
| `12595-ref-09` | path | L83 | 1 | `artifacts/in157_n06_simp_sensitivity/fig4_parity.png` | not_checked |
| `12595-ref-10` | field | L88 | 1 | `strict_monotone_1e-4_to_1e-8` | not_checked |
| `12595-ref-11` | field | L91 | 1 | `numerics.longdouble_mantissa_bits` | not_checked |
| `12595-ref-12` | field | L92 | 1 | `interface_adapter.assert_contract` | not_checked |
| `12595-ref-13` | path | L108 | 1 | `tests/test_simp_sensitivity_consistency_in157.py` | not_checked |
| `12595-ref-14` | path | L108 | 1 | `tests/test_simp_sensitivity_consistency.py` | not_checked |
| `12595-ref-15` | path | L109 | 1 | `acceptance.json` | not_checked |
| `12595-ref-16` | path | L109 | 1 | `delta_sweep.csv` | not_checked |
| `12595-ref-17` | path | L109 | 1 | `sensitivity_fields.npz` | not_checked |
| `12595-ref-18` | worktree | L111 | 1 | `/root/tp-agent/work/m11206` | not_checked |
| `12595-ref-19` | branch | L111 | 1 | `agent/m11206` | not_checked |

### 小节切分（11 节）

| # | 级 | 行区间 | 字符 | sha256 前缀 | 标题 |
|---|---|---|---|---|---|
| 1 | 1 | 1–4 | 134 | `sha256:e16fd45c7…` | IN157-N06 SIMP 灵敏度一致性验证面（伴随法 vs 有限差分） |
| 2 | 2 | 5–19 | 629 | `sha256:97e696654…` | 1 案例与物理背景 |
| 3 | 2 | 20–38 | 694 | `sha256:886006111…` | 2 方法 |
| 4 | 2 | 39–40 | 10 | `sha256:21433f8fd…` | 3 计算结果 |
| 5 | 3 | 41–51 | 604 | `sha256:1260a234e…` | 3.1 判据表（C1..C6） |
| 6 | 3 | 52–65 | 796 | `sha256:41a22710a…` | 3.2 逐设计误差（满场/采样） |
| 7 | 3 | 66–77 | 658 | `sha256:15fb6178c…` | 3.3 步长收敛表（C4/C5） |
| 8 | 2 | 78–84 | 812 | `sha256:8c7462da2…` | 4 图 |
| 9 | 2 | 85–93 | 869 | `sha256:877955edd…` | 5 注意点与局限 |
| 10 | 2 | 94–104 | 711 | `sha256:ca0793b2e…` | 6 误差判定（vs 基准，逐项） |
| 11 | 2 | 105–112 | 493 | `sha256:5589511d1…` | 7 审计链 |

### 附件交叉核对（正文 §4 vs 平台 figures 字段）

| name | name 在正文 | caption 逐字一致 |
|---|---|---|
| fig1_sensitivity_and_error_maps.png | ✅ | ✅ |
| fig2_delta_convergence.png | ✅ | ✅ |
| fig3_per_design_errors.png | ✅ | ✅ |
| fig4_parity.png | ✅ | ✅ |

### 观察项（不裁决，如实登记）

| id | kind | status | 陈述 |
|---|---|---|---|
| `12595-obs-01` | glob_reference | unresolved | C6 探针在判据表中写作 glob（§3.1），§7 审计链将其展开为两个显式测试文件（14 例 + 10 例 = 24 例）；glob 本身不可直接解析，展开计数一致性（24=24）仅登记不裁决 |
| `12595-obs-02` | cross_check_positive | resolved | 正文 §4 声明的 4 张 PNG 与平台记录 figures 字段的 4 条图注逐字一致（name 与 caption 全匹配，机检见 attachments.cross_check_markdown_vs_record） |
| `12595-obs-03` | boundary | unresolved | 报告 §7 声明全部代码/测试/工件位于 m11206 的 TensorPhysics worktree；本包工作树为 TensorKnowledge，跨树取证越界，故全部工件 existence=not_checked，不主张其存在或内容正确 |

## ④ 证据定位表（字段 → 原文引文，逐字）

| 字段 | 原文引文（逐字） |
|---|---|
| 引用（path） · `12595-ref-01` · source_field=markdown · L3 | `**结论：PASS** — 判据 C1..C6 全部满足（机器判定，见 `artifacts/in157_n06_simp_sensitivity/acceptance.json`）。` |
| 引用（field） · `12595-ref-02` · source_field=markdown · L33 | `2. **混合精度精化 FD**（本节点新增能力）：同一差分商，但每个柔度用“双精度 LU + `longdouble` 残差的迭代精化”求到 ~1 ulp，把线性求解器的 `kappa(K)*eps` 前向误差从差分商里剔除；差分本身、扰动本身不变。` |
| 引用（path） · `12595-ref-03` · source_field=markdown · L37 | `上游契约按“推定接口 + 适配层”处理：所有对 IN157-N05（密度滤波验证面）的依赖收敛在 `simp/interface_adapter.py`（构造/应用/算子/链式法则四个薄函数），接口漂移只改适配层。推定契约（数据结构/单位/调用面/文件格式）写入报告 JSON 的 `interface_contract` 字段。` |
| 引用（field） · `12595-ref-04` · source_field=markdown · L37 | `上游契约按“推定接口 + 适配层”处理：所有对 IN157-N05（密度滤波验证面）的依赖收敛在 `simp/interface_adapter.py`（构造/应用/算子/链式法则四个薄函数），接口漂移只改适配层。推定契约（数据结构/单位/调用面/文件格式）写入报告 JSON 的 `interface_contract` 字段。` |
| 引用（glob） · `12595-ref-05` · source_field=markdown · L50 | `| C6 | tests/test_simp_sensitivity_consistency*.py | 24 | 10 | PASS |` |
| 引用（path） · `12595-ref-06` · source_field=markdown · L80 | `- `artifacts/in157_n06_simp_sensitivity/fig1_sensitivity_and_error_maps.png` — 图1 标准悬臂梁 50x25（Vf=0.4, p=3, 端部集中力）SIMP 最优设计上：左=伴随解析灵敏度 dC/drho 场；中=普通双精度重分解有限差分与解析值之差（采样，含 ~1e-4 量级舍入底噪）；右=混合精度（扩展精度残差迭代精化）有限差分误差场（满场，~1e-8）` |
| 引用（path） · `12595-ref-07` · source_field=markdown · L81 | `- `artifacts/in157_n06_simp_sensitivity/fig2_delta_convergence.png` — 图2 扰动步长 Delta 收敛曲线（log-log）：普通中心差分呈 U 形（截断 O(Delta^2) 与舍入 eps·C/Delta 竞争，最优 Delta≈1e-4）；精化中心差分与精化复步差分在截断段分别给出斜坡 2 与 2（实测率见 CSV），并在 Delta<1e-7 触及 ~2e-12 的浮点噪声底（远低于 C1 容差 1e-4）` |
| 引用（path） · `12595-ref-08` · source_field=markdown · L82 | `- `artifacts/in157_n06_simp_sensitivity/fig3_per_design_errors.png` — 图3 三个设计（SIMP 最优/uniform 0.4/伪随机灰）上的最大绝对误差对比与 C1(1e-4)/C2(1e-5) 容差线：普通重分解 FD 在 uniform/灰设计上超 C1；精化 FD 与复步差分全部低于容差 3 个数量级以上` |
| 引用（path） · `12595-ref-09` · source_field=markdown · L83 | `- `artifacts/in157_n06_simp_sensitivity/fig4_parity.png` — 图4 解析伴随灵敏度 vs 有限差分的 1:1 对照（左=精化 FD，满场 1250 单元；右=普通 FD，采样）：精化 FD 落在 1:1 线上，普通 FD 可见系统性偏离` |
| 引用（field） · `12595-ref-10` · source_field=markdown · L88 | `2. **实数扰动无法把误差单调压到 Delta=1e-8**：差分商存在 `eps*C/Delta` 的抵消底噪，误差曲线必然是 U 形。C4 因此按“截断段单调下降 + 收敛阶符合理论 + 噪声底 <= 1e-9”操作化，并如实登记 `strict_monotone_1e-4_to_1e-8` 标志与全部实数差分曲线（caveats 字段）。` |
| 引用（field） · `12595-ref-11` · source_field=markdown · L91 | `5. **适用范围**：验证面覆盖二维 Q4 平面应力柔度问题（88 行代码族）；三维、多工况、自重、应力约束的伴随项未覆盖。`longdouble` 在非 x86/loongarch 平台常等于双精度，此时 C1..C3 会退化为普通 FD 数值（已在报告字段 `numerics.longdouble_mantissa_bits` 记录，并可机器判定）。` |
| 引用（field） · `12595-ref-12` · source_field=markdown · L92 | `6. **上游接口**：N05 尚在飞；本节点的滤波只用于构造“真实优化设计”，若 N05 的半径约定/算子形状变化，仅适配层需改动（`interface_adapter.assert_contract` 会在启动时报警）。` |
| 引用（path） · `12595-ref-13` · source_field=markdown · L108 | `- 测试：`tests/test_simp_sensitivity_consistency_in157.py`（14 例）+ 既有 `tests/test_simp_sensitivity_consistency.py`（10 例）= 24 例，C6 由 AST 计数机器判定` |
| 引用（path） · `12595-ref-14` · source_field=markdown · L108 | `- 测试：`tests/test_simp_sensitivity_consistency_in157.py`（14 例）+ 既有 `tests/test_simp_sensitivity_consistency.py`（10 例）= 24 例，C6 由 AST 计数机器判定` |
| 引用（path） · `12595-ref-15` · source_field=markdown · L109 | `- 工件：`acceptance.json`（判据与数字）、`delta_sweep.csv`（步长表）、`sensitivity_fields.npz`（满场解析/三种探针/误差）、4 张 PNG` |
| 引用（path） · `12595-ref-16` · source_field=markdown · L109 | `- 工件：`acceptance.json`（判据与数字）、`delta_sweep.csv`（步长表）、`sensitivity_fields.npz`（满场解析/三种探针/误差）、4 张 PNG` |
| 引用（path） · `12595-ref-17` · source_field=markdown · L109 | `- 工件：`acceptance.json`（判据与数字）、`delta_sweep.csv`（步长表）、`sensitivity_fields.npz`（满场解析/三种探针/误差）、4 张 PNG` |
| 引用（worktree） · `12595-ref-18` · source_field=markdown · L111 | `- 工作树/分支：`/root/tp-agent/work/m11206`，`agent/m11206`（基线 main）` |
| 引用（branch） · `12595-ref-19` · source_field=markdown · L111 | `- 工作树/分支：`/root/tp-agent/work/m11206`，`agent/m11206`（基线 main）` |
| 附件（figures 字段图注） · `fig:fig1_sensitivity_and_error_maps.png` · source_field=figures | `图1 标准悬臂梁 50x25（Vf=0.4, p=3, 端部集中力）SIMP 最优设计上：左=伴随解析灵敏度 dC/drho 场；中=普通双精度重分解有限差分与解析值之差（采样，含 ~1e-4 量级舍入底噪）；右=混合精度（扩展精度残差迭代精化）有限差分误差场（满场，~1e-8）` |
| 附件（figures 字段图注） · `fig:fig2_delta_convergence.png` · source_field=figures | `图2 扰动步长 Delta 收敛曲线（log-log）：普通中心差分呈 U 形（截断 O(Delta^2) 与舍入 eps·C/Delta 竞争，最优 Delta≈1e-4）；精化中心差分与精化复步差分在截断段分别给出斜坡 2 与 2（实测率见 CSV），并在 Delta<1e-7 触及 ~2e-12 的浮点噪声底（远低于 C1 容差 1e-4）` |
| 附件（figures 字段图注） · `fig:fig3_per_design_errors.png` · source_field=figures | `图3 三个设计（SIMP 最优/uniform 0.4/伪随机灰）上的最大绝对误差对比与 C1(1e-4)/C2(1e-5) 容差线：普通重分解 FD 在 uniform/灰设计上超 C1；精化 FD 与复步差分全部低于容差 3 个数量级以上` |
| 附件（figures 字段图注） · `fig:fig4_parity.png` · source_field=figures | `图4 解析伴随灵敏度 vs 有限差分的 1:1 对照（左=精化 FD，满场 1250 单元；右=普通 FD，采样）：精化 FD 落在 1:1 线上，普通 FD 可见系统性偏离` |
| 观察证据 · `12595-obs-01` · source_field=markdown | `| C6 | tests/test_simp_sensitivity_consistency*.py | 24 | 10 | PASS |` |
| 观察证据 · `12595-obs-01` · source_field=markdown | `- 测试：`tests/test_simp_sensitivity_consistency_in157.py`（14 例）+ 既有 `tests/test_simp_sensitivity_consistency.py`（10 例）= 24 例，C6 由 AST 计数机器判定` |
| 观察证据 · `12595-obs-02` · source_field=markdown | `- `artifacts/in157_n06_simp_sensitivity/fig1_sensitivity_and_error_maps.png` — 图1 标准悬臂梁 50x25（Vf=0.4, p=3, 端部集中力）SIMP 最优设计上：左=伴随解析灵敏度 dC/drho 场；中=普通双精度重分解有限差分与解析值之差（采样，含 ~1e-4 量级舍入底噪）；右=混合精度（扩展精度残差迭代精化）有限差分误差场（满场，~1e-8）` |
| 观察证据 · `12595-obs-03` · source_field=markdown | `- 工作树/分支：`/root/tp-agent/work/m11206`，`agent/m11206`（基线 main）` |

全部 locator 均机检通过：`27/27` 解析成功、未解析 `0` 条
（方法：markdown 项 `quote in markdown`，figures 项 `caption in markdown`）。

## ⑤ 注意点与局限

1. **glob 引用不可直接解析（honest-unresolved）**：C6 探针在判据表中写作 glob
   （§3.1），§7 审计链展开为两个显式文件（14 例 + 10 例 = 24 例）；
   glob 本身不是可解析路径，展开计数一致性（24=24）仅登记不裁决（`12595-obs-01`）。
2. **工件存在性未核**：报告声明的全部代码/测试/工件（`acceptance.json`、`delta_sweep.csv`、
   `sensitivity_fields.npz`、4 张 PNG、3 个 simp 模块、2 个测试文件）位于 m11206 的
   TensorPhysics worktree（`/root/tp-agent/work/m11206`，`agent/m11206`）；本包工作树为
   TensorKnowledge，跨树取证会越界，故全部 `existence=not_checked`，不主张这些工件存在或其哈希正确。
3. **附件载荷**：figures 仅元数据（无 png_base64），无法核验图与其数据的一致性；
   但正文 §4 的 4 个 PNG 路径与 figures 字段 4 条图注 name+caption 逐字一致（机检 4/4）。
4. **不做抽取语义判定**：报告 12595 的 C1..C6 PASS、混合精度 FD 等结论属上游自述，
   本包只登记其位置备查，不背书、不复算、不标 verified。
5. **正文无内容摘要值**：无 16+ 位十六进制摘要、无 URL、无 markdown 图片语法（机检 0 命中），
   `content_digests` 为空数组。
6. 适用范围：生成器可复用于任意 report 的资产登记（改 `REPORT_ID`/`CONTRACT_*` 常量），
   前提是只登记不解读。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 |
|---|---|
| valid_json | ✅ |
| schema_pass | ✅ |
| source_locator_resolvable | ✅ |
| source_hash_matches | ✅ |
| no_duplicate_ids | ✅ |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ |
| single_report_boundary | ✅ |
| no_verified_marks | ✅ |

诚实声明：上表 ✅ 只表示**本工序的登记动作正确**，不代表报告 12595 的科学结论已获验证；
`observations` 中的 unresolved 项保持 unresolved，未做粉饰。若有任何项失败，亦在本节如实列出。

### repro_cmd（一键复跑）

```bash
cd <repo-root> \
 && python3 scripts/kf/wp-12595-01/register_assets.py --check \
 && python3 scripts/kf/wp-12595-01/make_report.py \
 && python3 scripts/kf/wp-12595-01/make_figure.py \
 && python3 -m pytest tests/kf/test_wp_12595_01.py -q
```

离线复跑（无平台凭据）：`python3 scripts/kf/wp-12595-01/register_assets.py --from-file work/wp-12595-01/source/report_12595.md --record-json work/wp-12595-01/source/report_12595.json --check`。

## 附：kf_result.json（唯一 json 块，与 `docs/kf/wp-12595-01/kf_result.json` 同字节）

```json
{
  "package_id": "wp-12595-01",
  "task_type": "01-asset-registration",
  "report_id": "12595",
  "provenance": {
    "source_hash": "sha256:1233e5e4fece836d70b124a36a82438a1e48dbfddfc168b14f4c1f7efd7a08ce",
    "source_field": "markdown",
    "source_uri": "tensor://reports/12595",
    "producer": "agent/m20380",
    "emitted_at": "2026-11-14T12:32:37Z",
    "notes": "01-asset-registration：仅登记源资产/附件/引用清单与引文定位，未做抽取；claims=[]（合同允许），verification 交平台门计算"
  },
  "outputs": {
    "asset_manifest.json": {
      "manifest_version": "1.0",
      "package_id": "wp-12595-01",
      "task_type": "01-asset-registration",
      "objective": {
        "register_assets": true,
        "classify_report_type": false,
        "extraction_performed": false
      },
      "generated_at": "2026-11-14T12:32:37Z",
      "generator": "agent/m20380",
      "source_asset": {
        "uri": "tensor://reports/12595",
        "field": "markdown",
        "platform_record_id": 12595,
        "hash": {
          "algorithm": "sha256",
          "value": "sha256:1233e5e4fece836d70b124a36a82438a1e48dbfddfc168b14f4c1f7efd7a08ce",
          "scope": "UTF-8 bytes of tensor_reports.markdown (report 12595)",
          "contract_expected": "sha256:1233e5e4fece836d70b124a36a82438a1e48dbfddfc168b14f4c1f7efd7a08ce",
          "matches_contract": true
        },
        "size": {
          "chars": 6420,
          "bytes_utf8": 9931,
          "lines": 112,
          "contract_chars": 6420,
          "chars_match_contract": true
        },
        "record_metadata": {
          "title": "IN157-N06 SIMP 灵敏度一致性验证面：伴随法 vs 有限差分（混合精度参考，50x25 悬臂梁）",
          "title_matches_contract": true,
          "scenario_key": "in157_n06_simp_sensitivity_consistency",
          "scenario_key_matches_contract": true,
          "tags": [
            "IN157-N06",
            "SIMP",
            "topology-optimization",
            "adjoint-sensitivity",
            "finite-difference",
            "mixed-precision",
            "iterative-refinement",
            "verification",
            "cantilever-50x25"
          ],
          "status": "published",
          "created_by": 1,
          "created_at": "2026-11-10T21:58:55.686514+00:00",
          "mission_id": 11206,
          "stage": null
        },
        "contract_layer_hint": {
          "value": "IN157-N06|in157_n06_simp_sensitivity_consistency|m",
          "interpreted": false,
          "note": "契约 notes 中的分层标签原样登记；objective.classify_report_type=false，不解读"
        }
      },
      "attachments": {
        "count": 4,
        "items": [
          {
            "name": "fig1_sensitivity_and_error_maps.png",
            "caption": "图1 标准悬臂梁 50x25（Vf=0.4, p=3, 端部集中力）SIMP 最优设计上：左=伴随解析灵敏度 dC/drho 场；中=普通双精度重分解有限差分与解析值之差（采样，含 ~1e-4 量级舍入底噪）；右=混合精度（扩展精度残差迭代精化）有限差分误差场（满场，~1e-8）",
            "payload_field_present": false,
            "png_base64_len": 0
          },
          {
            "name": "fig2_delta_convergence.png",
            "caption": "图2 扰动步长 Delta 收敛曲线（log-log）：普通中心差分呈 U 形（截断 O(Delta^2) 与舍入 eps·C/Delta 竞争，最优 Delta≈1e-4）；精化中心差分与精化复步差分在截断段分别给出斜坡 2 与 2（实测率见 CSV），并在 Delta<1e-7 触及 ~2e-12 的浮点噪声底（远低于 C1 容差 1e-4）",
            "payload_field_present": false,
            "png_base64_len": 0
          },
          {
            "name": "fig3_per_design_errors.png",
            "caption": "图3 三个设计（SIMP 最优/uniform 0.4/伪随机灰）上的最大绝对误差对比与 C1(1e-4)/C2(1e-5) 容差线：普通重分解 FD 在 uniform/灰设计上超 C1；精化 FD 与复步差分全部低于容差 3 个数量级以上",
            "payload_field_present": false,
            "png_base64_len": 0
          },
          {
            "name": "fig4_parity.png",
            "caption": "图4 解析伴随灵敏度 vs 有限差分的 1:1 对照（左=精化 FD，满场 1250 单元；右=普通 FD，采样）：精化 FD 落在 1:1 线上，普通 FD 可见系统性偏离",
            "payload_field_present": false,
            "png_base64_len": 0
          }
        ],
        "scan": {
          "record_figures_len": 4,
          "png_base64_present": false,
          "markdown_image_syntax_hits": 0,
          "external_url_hits": 0,
          "returned_all": true
        },
        "cross_check_markdown_vs_record": [
          {
            "name": "fig1_sensitivity_and_error_maps.png",
            "name_in_markdown": true,
            "caption_matches_markdown": true
          },
          {
            "name": "fig2_delta_convergence.png",
            "name_in_markdown": true,
            "caption_matches_markdown": true
          },
          {
            "name": "fig3_per_design_errors.png",
            "name_in_markdown": true,
            "caption_matches_markdown": true
          },
          {
            "name": "fig4_parity.png",
            "name_in_markdown": true,
            "caption_matches_markdown": true
          }
        ],
        "note": "附件=平台记录 figures 字段登记的 4 张图（仅 name/caption 元数据，无 png_base64 载荷）；未下载/未解码图像载荷；正文 §4 的 4 个 PNG 路径引用另在 referenced_artifacts 登记"
      },
      "sections": [
        {
          "ordinal": 1,
          "level": 1,
          "heading": "IN157-N06 SIMP 灵敏度一致性验证面（伴随法 vs 有限差分）",
          "line_start": 1,
          "line_end": 4,
          "chars": 134,
          "sha256": "sha256:e16fd45c7c579c06ed99d2d83d43e1b9d3afcc26f4c36b316e9c4974d9f3b695"
        },
        {
          "ordinal": 2,
          "level": 2,
          "heading": "1 案例与物理背景",
          "line_start": 5,
          "line_end": 19,
          "chars": 629,
          "sha256": "sha256:97e696654fa82c96138d1b90b720b5d00bf1c1e51ef910abf75c190fe34d8b63"
        },
        {
          "ordinal": 3,
          "level": 2,
          "heading": "2 方法",
          "line_start": 20,
          "line_end": 38,
          "chars": 694,
          "sha256": "sha256:886006111a8e05fb4718be4a4cb40057ecbb0a851f15979c16367daf71dc724f"
        },
        {
          "ordinal": 4,
          "level": 2,
          "heading": "3 计算结果",
          "line_start": 39,
          "line_end": 40,
          "chars": 10,
          "sha256": "sha256:21433f8fd7aeb8a4616c3762c81c9056a0e4edfd1cabc4fd10e14c5b000cc62a"
        },
        {
          "ordinal": 5,
          "level": 3,
          "heading": "3.1 判据表（C1..C6）",
          "line_start": 41,
          "line_end": 51,
          "chars": 604,
          "sha256": "sha256:1260a234ed3edc439d956e73de1fbef204999b1962d8fb843f2b7fb5b5e85e92"
        },
        {
          "ordinal": 6,
          "level": 3,
          "heading": "3.2 逐设计误差（满场/采样）",
          "line_start": 52,
          "line_end": 65,
          "chars": 796,
          "sha256": "sha256:41a22710a5b5b180c0715445234b3289d515f52accb4f21e5e7e7a1940be11d4"
        },
        {
          "ordinal": 7,
          "level": 3,
          "heading": "3.3 步长收敛表（C4/C5）",
          "line_start": 66,
          "line_end": 77,
          "chars": 658,
          "sha256": "sha256:15fb6178c2f0b1dd5171c94c1e28374b79d7ee9a44a482ff07360e84354fa17b"
        },
        {
          "ordinal": 8,
          "level": 2,
          "heading": "4 图",
          "line_start": 78,
          "line_end": 84,
          "chars": 812,
          "sha256": "sha256:8c7462da20045b6e9ef41f5297ac0a955bf14f961739b14386d53efa718aa425"
        },
        {
          "ordinal": 9,
          "level": 2,
          "heading": "5 注意点与局限",
          "line_start": 85,
          "line_end": 93,
          "chars": 869,
          "sha256": "sha256:877955edda50b46da779d9dcda22baccc22b62ab08e69f582b93dd6aa5d35023"
        },
        {
          "ordinal": 10,
          "level": 2,
          "heading": "6 误差判定（vs 基准，逐项）",
          "line_start": 94,
          "line_end": 104,
          "chars": 711,
          "sha256": "sha256:ca0793b2e9ab212b7a7f534eb7b7360c7775f0bce9b0becbff73efba1a3d362d"
        },
        {
          "ordinal": 11,
          "level": 2,
          "heading": "7 审计链",
          "line_start": 105,
          "line_end": 112,
          "chars": 493,
          "sha256": "sha256:5589511d169700af69b12e3dee84bec578244044072fe9cee3b979a3529b4e7b"
        }
      ],
      "referenced_artifacts": [
        {
          "raw_text": "artifacts/in157_n06_simp_sensitivity/acceptance.json",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 3,
          "in_report_section": "§1 IN157-N06 SIMP 灵敏度一致性验证面（伴随法 vs 有限差分）",
          "locator_quote": "**结论：PASS** — 判据 C1..C6 全部满足（机器判定，见 `artifacts/in157_n06_simp_sensitivity/acceptance.json`）。",
          "ref_id": "12595-ref-01",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "longdouble",
          "path_kind": "field",
          "occurrences": 3,
          "first_line": 33,
          "in_report_section": "§3 2 方法",
          "locator_quote": "2. **混合精度精化 FD**（本节点新增能力）：同一差分商，但每个柔度用“双精度 LU + `longdouble` 残差的迭代精化”求到 ~1 ulp，把线性求解器的 `kappa(K)*eps` 前向误差从差分商里剔除；差分本身、扰动本身不变。",
          "ref_id": "12595-ref-02",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "simp/interface_adapter.py",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 37,
          "in_report_section": "§3 2 方法",
          "locator_quote": "上游契约按“推定接口 + 适配层”处理：所有对 IN157-N05（密度滤波验证面）的依赖收敛在 `simp/interface_adapter.py`（构造/应用/算子/链式法则四个薄函数），接口漂移只改适配层。推定契约（数据结构/单位/调用面/文件格式）写入报告 JSON 的 `interface_contract` 字段。",
          "ref_id": "12595-ref-03",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "interface_contract",
          "path_kind": "field",
          "occurrences": 1,
          "first_line": 37,
          "in_report_section": "§3 2 方法",
          "locator_quote": "上游契约按“推定接口 + 适配层”处理：所有对 IN157-N05（密度滤波验证面）的依赖收敛在 `simp/interface_adapter.py`（构造/应用/算子/链式法则四个薄函数），接口漂移只改适配层。推定契约（数据结构/单位/调用面/文件格式）写入报告 JSON 的 `interface_contract` 字段。",
          "ref_id": "12595-ref-04",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "tests/test_simp_sensitivity_consistency*.py",
          "path_kind": "glob",
          "occurrences": 1,
          "first_line": 50,
          "in_report_section": "§5 3.1 判据表（C1..C6）",
          "locator_quote": "| C6 | tests/test_simp_sensitivity_consistency*.py | 24 | 10 | PASS |",
          "ref_id": "12595-ref-05",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "artifacts/in157_n06_simp_sensitivity/fig1_sensitivity_and_error_maps.png",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 80,
          "in_report_section": "§8 4 图",
          "locator_quote": "- `artifacts/in157_n06_simp_sensitivity/fig1_sensitivity_and_error_maps.png` — 图1 标准悬臂梁 50x25（Vf=0.4, p=3, 端部集中力）SIMP 最优设计上：左=伴随解析灵敏度 dC/drho 场；中=普通双精度重分解有限差分与解析值之差（采样，含 ~1e-4 量级舍入底噪）；右=混合精度（扩展精度残差迭代精化）有限差分误差场（满场，~1e-8）",
          "ref_id": "12595-ref-06",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "artifacts/in157_n06_simp_sensitivity/fig2_delta_convergence.png",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 81,
          "in_report_section": "§8 4 图",
          "locator_quote": "- `artifacts/in157_n06_simp_sensitivity/fig2_delta_convergence.png` — 图2 扰动步长 Delta 收敛曲线（log-log）：普通中心差分呈 U 形（截断 O(Delta^2) 与舍入 eps·C/Delta 竞争，最优 Delta≈1e-4）；精化中心差分与精化复步差分在截断段分别给出斜坡 2 与 2（实测率见 CSV），并在 Delta<1e-7 触及 ~2e-12 的浮点噪声底（远低于 C1 容差 1e-4）",
          "ref_id": "12595-ref-07",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "artifacts/in157_n06_simp_sensitivity/fig3_per_design_errors.png",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 82,
          "in_report_section": "§8 4 图",
          "locator_quote": "- `artifacts/in157_n06_simp_sensitivity/fig3_per_design_errors.png` — 图3 三个设计（SIMP 最优/uniform 0.4/伪随机灰）上的最大绝对误差对比与 C1(1e-4)/C2(1e-5) 容差线：普通重分解 FD 在 uniform/灰设计上超 C1；精化 FD 与复步差分全部低于容差 3 个数量级以上",
          "ref_id": "12595-ref-08",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "artifacts/in157_n06_simp_sensitivity/fig4_parity.png",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 83,
          "in_report_section": "§8 4 图",
          "locator_quote": "- `artifacts/in157_n06_simp_sensitivity/fig4_parity.png` — 图4 解析伴随灵敏度 vs 有限差分的 1:1 对照（左=精化 FD，满场 1250 单元；右=普通 FD，采样）：精化 FD 落在 1:1 线上，普通 FD 可见系统性偏离",
          "ref_id": "12595-ref-09",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "strict_monotone_1e-4_to_1e-8",
          "path_kind": "field",
          "occurrences": 1,
          "first_line": 88,
          "in_report_section": "§9 5 注意点与局限",
          "locator_quote": "2. **实数扰动无法把误差单调压到 Delta=1e-8**：差分商存在 `eps*C/Delta` 的抵消底噪，误差曲线必然是 U 形。C4 因此按“截断段单调下降 + 收敛阶符合理论 + 噪声底 <= 1e-9”操作化，并如实登记 `strict_monotone_1e-4_to_1e-8` 标志与全部实数差分曲线（caveats 字段）。",
          "ref_id": "12595-ref-10",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "numerics.longdouble_mantissa_bits",
          "path_kind": "field",
          "occurrences": 1,
          "first_line": 91,
          "in_report_section": "§9 5 注意点与局限",
          "locator_quote": "5. **适用范围**：验证面覆盖二维 Q4 平面应力柔度问题（88 行代码族）；三维、多工况、自重、应力约束的伴随项未覆盖。`longdouble` 在非 x86/loongarch 平台常等于双精度，此时 C1..C3 会退化为普通 FD 数值（已在报告字段 `numerics.longdouble_mantissa_bits` 记录，并可机器判定）。",
          "ref_id": "12595-ref-11",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "interface_adapter.assert_contract",
          "path_kind": "field",
          "occurrences": 1,
          "first_line": 92,
          "in_report_section": "§9 5 注意点与局限",
          "locator_quote": "6. **上游接口**：N05 尚在飞；本节点的滤波只用于构造“真实优化设计”，若 N05 的半径约定/算子形状变化，仅适配层需改动（`interface_adapter.assert_contract` 会在启动时报警）。",
          "ref_id": "12595-ref-12",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "tests/test_simp_sensitivity_consistency_in157.py",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 108,
          "in_report_section": "§11 7 审计链",
          "locator_quote": "- 测试：`tests/test_simp_sensitivity_consistency_in157.py`（14 例）+ 既有 `tests/test_simp_sensitivity_consistency.py`（10 例）= 24 例，C6 由 AST 计数机器判定",
          "ref_id": "12595-ref-13",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "tests/test_simp_sensitivity_consistency.py",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 108,
          "in_report_section": "§11 7 审计链",
          "locator_quote": "- 测试：`tests/test_simp_sensitivity_consistency_in157.py`（14 例）+ 既有 `tests/test_simp_sensitivity_consistency.py`（10 例）= 24 例，C6 由 AST 计数机器判定",
          "ref_id": "12595-ref-14",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "acceptance.json",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 109,
          "in_report_section": "§11 7 审计链",
          "locator_quote": "- 工件：`acceptance.json`（判据与数字）、`delta_sweep.csv`（步长表）、`sensitivity_fields.npz`（满场解析/三种探针/误差）、4 张 PNG",
          "ref_id": "12595-ref-15",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "delta_sweep.csv",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 109,
          "in_report_section": "§11 7 审计链",
          "locator_quote": "- 工件：`acceptance.json`（判据与数字）、`delta_sweep.csv`（步长表）、`sensitivity_fields.npz`（满场解析/三种探针/误差）、4 张 PNG",
          "ref_id": "12595-ref-16",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "sensitivity_fields.npz",
          "path_kind": "path",
          "occurrences": 1,
          "first_line": 109,
          "in_report_section": "§11 7 审计链",
          "locator_quote": "- 工件：`acceptance.json`（判据与数字）、`delta_sweep.csv`（步长表）、`sensitivity_fields.npz`（满场解析/三种探针/误差）、4 张 PNG",
          "ref_id": "12595-ref-17",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "/root/tp-agent/work/m11206",
          "path_kind": "worktree",
          "occurrences": 1,
          "first_line": 111,
          "in_report_section": "§11 7 审计链",
          "locator_quote": "- 工作树/分支：`/root/tp-agent/work/m11206`，`agent/m11206`（基线 main）",
          "ref_id": "12595-ref-18",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        },
        {
          "raw_text": "agent/m11206",
          "path_kind": "branch",
          "occurrences": 1,
          "first_line": 111,
          "in_report_section": "§11 7 审计链",
          "locator_quote": "- 工作树/分支：`/root/tp-agent/work/m11206`，`agent/m11206`（基线 main）",
          "ref_id": "12595-ref-19",
          "existence": "not_checked",
          "existence_reason": "该路径声明于 m11206 的 TensorPhysics worktree（报告 §7 审计链），本包工作树为 TensorKnowledge 且边界=只触碰 report_id=12595，不跨 worktree 取证，存在性/内容一致性留待上游门或后续工序"
        }
      ],
      "content_digests": [],
      "content_digests_note": "正文无 16+ 位十六进制摘要值、无 URL、无 markdown 图片语法（机检 0 命中）",
      "observations": [
        {
          "id": "12595-obs-01",
          "kind": "glob_reference",
          "status": "unresolved",
          "statement": "C6 探针在判据表中写作 glob（§3.1），§7 审计链将其展开为两个显式测试文件（14 例 + 10 例 = 24 例）；glob 本身不可直接解析，展开计数一致性（24=24）仅登记不裁决",
          "evidence_lines": [
            50,
            108
          ],
          "evidence_quotes": [
            "| C6 | tests/test_simp_sensitivity_consistency*.py | 24 | 10 | PASS |",
            "- 测试：`tests/test_simp_sensitivity_consistency_in157.py`（14 例）+ 既有 `tests/test_simp_sensitivity_consistency.py`（10 例）= 24 例，C6 由 AST 计数机器判定"
          ]
        },
        {
          "id": "12595-obs-02",
          "kind": "cross_check_positive",
          "status": "resolved",
          "statement": "正文 §4 声明的 4 张 PNG 与平台记录 figures 字段的 4 条图注逐字一致（name 与 caption 全匹配，机检见 attachments.cross_check_markdown_vs_record）",
          "evidence_lines": [
            80
          ],
          "evidence_quotes": [
            "- `artifacts/in157_n06_simp_sensitivity/fig1_sensitivity_and_error_maps.png` — 图1 标准悬臂梁 50x25（Vf=0.4, p=3, 端部集中力）SIMP 最优设计上：左=伴随解析灵敏度 dC/drho 场；中=普通双精度重分解有限差分与解析值之差（采样，含 ~1e-4 量级舍入底噪）；右=混合精度（扩展精度残差迭代精化）有限差分误差场（满场，~1e-8）"
          ]
        },
        {
          "id": "12595-obs-03",
          "kind": "boundary",
          "status": "unresolved",
          "statement": "报告 §7 声明全部代码/测试/工件位于 m11206 的 TensorPhysics worktree；本包工作树为 TensorKnowledge，跨树取证越界，故全部工件 existence=not_checked，不主张其存在或内容正确",
          "evidence_lines": [
            111
          ],
          "evidence_quotes": [
            "- 工作树/分支：`/root/tp-agent/work/m11206`，`agent/m11206`（基线 main）"
          ]
        }
      ],
      "locator_check": {
        "total": 27,
        "resolved": 27,
        "unresolved": 0,
        "all_resolved": true,
        "items": [
          {
            "ref_id": "12595-ref-01",
            "source_field": "markdown",
            "quote": "**结论：PASS** — 判据 C1..C6 全部满足（机器判定，见 `artifacts/in157_n06_simp_sensitivity/acceptance.json`）。",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-02",
            "source_field": "markdown",
            "quote": "2. **混合精度精化 FD**（本节点新增能力）：同一差分商，但每个柔度用“双精度 LU + `longdouble` 残差的迭代精化”求到 ~1 ulp，把线性求解器的 `kappa(K)*eps` 前向误差从差分商里剔除；差分本身、扰动本身不变。",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-03",
            "source_field": "markdown",
            "quote": "上游契约按“推定接口 + 适配层”处理：所有对 IN157-N05（密度滤波验证面）的依赖收敛在 `simp/interface_adapter.py`（构造/应用/算子/链式法则四个薄函数），接口漂移只改适配层。推定契约（数据结构/单位/调用面/文件格式）写入报告 JSON 的 `interface_contract` 字段。",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-04",
            "source_field": "markdown",
            "quote": "上游契约按“推定接口 + 适配层”处理：所有对 IN157-N05（密度滤波验证面）的依赖收敛在 `simp/interface_adapter.py`（构造/应用/算子/链式法则四个薄函数），接口漂移只改适配层。推定契约（数据结构/单位/调用面/文件格式）写入报告 JSON 的 `interface_contract` 字段。",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-05",
            "source_field": "markdown",
            "quote": "| C6 | tests/test_simp_sensitivity_consistency*.py | 24 | 10 | PASS |",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-06",
            "source_field": "markdown",
            "quote": "- `artifacts/in157_n06_simp_sensitivity/fig1_sensitivity_and_error_maps.png` — 图1 标准悬臂梁 50x25（Vf=0.4, p=3, 端部集中力）SIMP 最优设计上：左=伴随解析灵敏度 dC/drho 场；中=普通双精度重分解有限差分与解析值之差（采样，含 ~1e-4 量级舍入底噪）；右=混合精度（扩展精度残差迭代精化）有限差分误差场（满场，~1e-8）",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-07",
            "source_field": "markdown",
            "quote": "- `artifacts/in157_n06_simp_sensitivity/fig2_delta_convergence.png` — 图2 扰动步长 Delta 收敛曲线（log-log）：普通中心差分呈 U 形（截断 O(Delta^2) 与舍入 eps·C/Delta 竞争，最优 Delta≈1e-4）；精化中心差分与精化复步差分在截断段分别给出斜坡 2 与 2（实测率见 CSV），并在 Delta<1e-7 触及 ~2e-12 的浮点噪声底（远低于 C1 容差 1e-4）",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-08",
            "source_field": "markdown",
            "quote": "- `artifacts/in157_n06_simp_sensitivity/fig3_per_design_errors.png` — 图3 三个设计（SIMP 最优/uniform 0.4/伪随机灰）上的最大绝对误差对比与 C1(1e-4)/C2(1e-5) 容差线：普通重分解 FD 在 uniform/灰设计上超 C1；精化 FD 与复步差分全部低于容差 3 个数量级以上",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-09",
            "source_field": "markdown",
            "quote": "- `artifacts/in157_n06_simp_sensitivity/fig4_parity.png` — 图4 解析伴随灵敏度 vs 有限差分的 1:1 对照（左=精化 FD，满场 1250 单元；右=普通 FD，采样）：精化 FD 落在 1:1 线上，普通 FD 可见系统性偏离",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-10",
            "source_field": "markdown",
            "quote": "2. **实数扰动无法把误差单调压到 Delta=1e-8**：差分商存在 `eps*C/Delta` 的抵消底噪，误差曲线必然是 U 形。C4 因此按“截断段单调下降 + 收敛阶符合理论 + 噪声底 <= 1e-9”操作化，并如实登记 `strict_monotone_1e-4_to_1e-8` 标志与全部实数差分曲线（caveats 字段）。",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-11",
            "source_field": "markdown",
            "quote": "5. **适用范围**：验证面覆盖二维 Q4 平面应力柔度问题（88 行代码族）；三维、多工况、自重、应力约束的伴随项未覆盖。`longdouble` 在非 x86/loongarch 平台常等于双精度，此时 C1..C3 会退化为普通 FD 数值（已在报告字段 `numerics.longdouble_mantissa_bits` 记录，并可机器判定）。",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-12",
            "source_field": "markdown",
            "quote": "6. **上游接口**：N05 尚在飞；本节点的滤波只用于构造“真实优化设计”，若 N05 的半径约定/算子形状变化，仅适配层需改动（`interface_adapter.assert_contract` 会在启动时报警）。",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-13",
            "source_field": "markdown",
            "quote": "- 测试：`tests/test_simp_sensitivity_consistency_in157.py`（14 例）+ 既有 `tests/test_simp_sensitivity_consistency.py`（10 例）= 24 例，C6 由 AST 计数机器判定",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-14",
            "source_field": "markdown",
            "quote": "- 测试：`tests/test_simp_sensitivity_consistency_in157.py`（14 例）+ 既有 `tests/test_simp_sensitivity_consistency.py`（10 例）= 24 例，C6 由 AST 计数机器判定",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-15",
            "source_field": "markdown",
            "quote": "- 工件：`acceptance.json`（判据与数字）、`delta_sweep.csv`（步长表）、`sensitivity_fields.npz`（满场解析/三种探针/误差）、4 张 PNG",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-16",
            "source_field": "markdown",
            "quote": "- 工件：`acceptance.json`（判据与数字）、`delta_sweep.csv`（步长表）、`sensitivity_fields.npz`（满场解析/三种探针/误差）、4 张 PNG",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-17",
            "source_field": "markdown",
            "quote": "- 工件：`acceptance.json`（判据与数字）、`delta_sweep.csv`（步长表）、`sensitivity_fields.npz`（满场解析/三种探针/误差）、4 张 PNG",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-18",
            "source_field": "markdown",
            "quote": "- 工作树/分支：`/root/tp-agent/work/m11206`，`agent/m11206`（基线 main）",
            "resolved": true
          },
          {
            "ref_id": "12595-ref-19",
            "source_field": "markdown",
            "quote": "- 工作树/分支：`/root/tp-agent/work/m11206`，`agent/m11206`（基线 main）",
            "resolved": true
          },
          {
            "ref_id": "fig:fig1_sensitivity_and_error_maps.png",
            "source_field": "figures",
            "quote": "图1 标准悬臂梁 50x25（Vf=0.4, p=3, 端部集中力）SIMP 最优设计上：左=伴随解析灵敏度 dC/drho 场；中=普通双精度重分解有限差分与解析值之差（采样，含 ~1e-4 量级舍入底噪）；右=混合精度（扩展精度残差迭代精化）有限差分误差场（满场，~1e-8）",
            "resolved": true
          },
          {
            "ref_id": "fig:fig2_delta_convergence.png",
            "source_field": "figures",
            "quote": "图2 扰动步长 Delta 收敛曲线（log-log）：普通中心差分呈 U 形（截断 O(Delta^2) 与舍入 eps·C/Delta 竞争，最优 Delta≈1e-4）；精化中心差分与精化复步差分在截断段分别给出斜坡 2 与 2（实测率见 CSV），并在 Delta<1e-7 触及 ~2e-12 的浮点噪声底（远低于 C1 容差 1e-4）",
            "resolved": true
          },
          {
            "ref_id": "fig:fig3_per_design_errors.png",
            "source_field": "figures",
            "quote": "图3 三个设计（SIMP 最优/uniform 0.4/伪随机灰）上的最大绝对误差对比与 C1(1e-4)/C2(1e-5) 容差线：普通重分解 FD 在 uniform/灰设计上超 C1；精化 FD 与复步差分全部低于容差 3 个数量级以上",
            "resolved": true
          },
          {
            "ref_id": "fig:fig4_parity.png",
            "source_field": "figures",
            "quote": "图4 解析伴随灵敏度 vs 有限差分的 1:1 对照（左=精化 FD，满场 1250 单元；右=普通 FD，采样）：精化 FD 落在 1:1 线上，普通 FD 可见系统性偏离",
            "resolved": true
          },
          {
            "ref_id": "12595-obs-01",
            "source_field": "markdown",
            "quote": "| C6 | tests/test_simp_sensitivity_consistency*.py | 24 | 10 | PASS |",
            "resolved": true
          },
          {
            "ref_id": "12595-obs-01",
            "source_field": "markdown",
            "quote": "- 测试：`tests/test_simp_sensitivity_consistency_in157.py`（14 例）+ 既有 `tests/test_simp_sensitivity_consistency.py`（10 例）= 24 例，C6 由 AST 计数机器判定",
            "resolved": true
          },
          {
            "ref_id": "12595-obs-02",
            "source_field": "markdown",
            "quote": "- `artifacts/in157_n06_simp_sensitivity/fig1_sensitivity_and_error_maps.png` — 图1 标准悬臂梁 50x25（Vf=0.4, p=3, 端部集中力）SIMP 最优设计上：左=伴随解析灵敏度 dC/drho 场；中=普通双精度重分解有限差分与解析值之差（采样，含 ~1e-4 量级舍入底噪）；右=混合精度（扩展精度残差迭代精化）有限差分误差场（满场，~1e-8）",
            "resolved": true
          },
          {
            "ref_id": "12595-obs-03",
            "source_field": "markdown",
            "quote": "- 工作树/分支：`/root/tp-agent/work/m11206`，`agent/m11206`（基线 main）",
            "resolved": true
          }
        ]
      },
      "unresolved": [
        {
          "id": "12595-obs-01",
          "kind": "glob_reference",
          "reason": "C6 探针在判据表中写作 glob（§3.1），§7 审计链将其展开为两个显式测试文件（14 例 + 10 例 = 24 例）；glob 本身不可直接解析，展开计数一致性（24=24）仅登记不裁决"
        },
        {
          "id": "12595-obs-03",
          "kind": "boundary",
          "reason": "报告 §7 声明全部代码/测试/工件位于 m11206 的 TensorPhysics worktree；本包工作树为 TensorKnowledge，跨树取证越界，故全部工件 existence=not_checked，不主张其存在或内容正确"
        }
      ],
      "boundary": {
        "report_ids_read": [
          "12595"
        ],
        "report_ids_written": [
          "12595"
        ],
        "verification_status": "none",
        "claims_generated": 0,
        "note": "只触碰 report_id=12595；不标 verified（verification 由平台门计算）；claims=[]（合同允许）"
      }
    }
  },
  "claims": []
}
```
