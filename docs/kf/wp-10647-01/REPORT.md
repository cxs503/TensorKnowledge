# wp-10647-01 · 报告 10647 源资产登记

- **package / task_type**：`wp-10647-01` / `01-asset-registration`（lane C，delivery repo = TensorKnowledge，status = draft）
- **report_id**：`10647` — 《【长跑生存层】核心转储取证 + 位级幂等断点续跑 + 资源降级阶梯（m9082 / p148w2-n03）》
- **scenario_key**：`crash-forensics-resume`（平台基础设施 / 长跑生存层，无船舶域语义）
- **source**：`tensor://reports/10647` · field=`markdown` ·
  sha256=`aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31` · chars=10814 · bytes_utf8=17194
- **产物**：`artifacts/wp-10647-01/asset_manifest.json`（交付物）、`artifacts/wp-10647-01/verification.json`、
  `artifacts/wp-10647-01/fig1_asset_resolution.png`、`runs/wp-10647-01/kf_result.wp-10647-01.json`
- **本工序边界**：只登记资产（register_assets=true / classify_report_type=false），**不做抽取**，claims 为空数组，
  **不把任何结论标成 verified**（verification 由平台门计算）。

---

## ① 本工序做了什么

1. 从平台 API 取回 report_id=10647 的 `markdown` 字段（`scripts/kf_fetch_10647.py`），逐字节落盘并重算哈希：
   sha256 = `aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31`，与工作包契约声明的 `aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31` **一致**，
   字符数 10814 与契约 `chars: 10814` 一致。
2. 把报告里可定位的资产登记成 31 条清单（`scripts/kf_register_10647.py`）：类别分布见 counts.by_class，
   可解析性 declared_absent=1、referenced_unresolved=13、resolved_in_source=17。
3. 对每条资产执行一次**可复现的解析检查**并把结果写进 `resolution_check`（工作树路径存在性 / 平台 figure 元数据 /
   容器 core_pattern 探针 / 工件可溯源性），不猜测地址、不编造缺失信息。
4. 独立复验（`scripts/kf_verify_10647.py`：新登录 + 重新拉取 + 重算哈希 + 重切每条引文 + JSON-Schema 校验），
   六项 acceptance 全过（见 ⑥）。
5. 出图（`scripts/fig_asset_inventory_wp10647_01.py`）：可解析性分布 / 类别分布 / 引文跨度地图。

**没有做的事（诚实边界）**：没有抽取任何知识对象；没有复算上游数字（复算需要 `runs/m9082/evidence.json`，
该工件不在本工作树）；没有判定上游结论对错。

## ② 怎么做的（步骤 / 工具 / 关键设置）

```
scripts/kf_fetch_10647.py      # API 登录 → GET /tensor/reports/10647 → 落盘 md/json → 重算 sha256
scripts/kf_register_10647.py   # 锚点切片 + 唯一性断言 + 解析检查 → asset_manifest.json + 结果信封
scripts/kf_verify_10647.py     # 独立复验（新登录重取 + jsonschema + 逐条重切 + counts/nesting 一致性）
scripts/fig_asset_inventory_wp10647_01.py   # 三面板总览图（数字全部读自 manifest）
```

关键设置与设计决定：

| 决定 | 理由 |
|---|---|
| 引文一律**程序化切片**（锚点唯一 + 切片后 `md.count(quote)==1` 断言） | 零手抄；任何手工重述都会在断言处失败 |
| `in_report_section` 由文档自动推导（最近的前置标题行） | 章节名也不许手打 |
| 切片模式分 `line / block / bullet / table / table_after / fence` | 表格与代码块边界由结构决定，避免把相邻资产吞进来（A27/A28 曾因 block 模式越界，改 `bullet` 修复） |
| `resolution` 三值：`resolved_in_source` / `referenced_unresolved` / `declared_absent` | 只描述"能否定位/解析"，不表达"对错"；`resolution_check.result` 必须与之一致（verifier 额外检查） |
| 数值表只登记不复核，`resolution_check.check=artifact_trace` 记录 `evidence.json` 缺失 | 避免"看起来核过"的假象 |
| 新增 `schemas/asset_manifest.v2.schema.json`（把 v1 的两个 `const` 放宽为 pattern，其余不变） | v1 把 `package_id`/`report_id` 钉死为 wp-448-01/448，无法校验其它包；v1 保持原样以存证 |

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-10647-01/asset_manifest.json` | 交付物本体：31 条资产、source 块、counts、integrity；claims=[] |
| `artifacts/wp-10647-01/verification.json` | 六项 acceptance + 6 项额外检查的机器结果（本次 all_pass=true） |
| `artifacts/wp-10647-01/fig1_asset_resolution.png` | 三面板总览：可解析性分布 / 类别分布 / 引文跨度地图 |
| `runs/wp-10647-01/report_10647.md` · `.json` | 源 markdown 逐字节副本与 API 原始 payload（哈希可复算） |
| `runs/wp-10647-01/kf_result.wp-10647-01.json` | 结果信封（kf_result.v1 结构），`provenance.source_hash` = 源 md 哈希 |
| `runs/wp-10647-01/kf_result_block.wp-10647-01.json` | 与信封逐字节相同，供本报告内唯一的结果围栏块原样提交 |
| `docs/kf/wp-10647-01/REPORT.md` · `kf_result.json` · `acceptance.json` | 本报告与镜像件 |
| `schemas/asset_manifest.v2.schema.json` | 包无关的清单 schema（v1 的 const → pattern 泛化） |
| `scripts/kf_fetch_10647.py` · `kf_register_10647.py` · `kf_verify_10647.py` · `fig_asset_inventory_wp10647_01.py` | 一键复跑链（fetch → register → verify → figure） |
| `tests/test_kf_wp10647.py` | 离线回归：schema/定位/唯一性/哈希/claims/无 verified 标记 |

## ④ 证据定位表（claim/字段 → 原文逐字切片）

下表每一行的 `quote` 都是源 markdown 的**字符区间逐字切片**（`start–end` 为字符偏移，行号为 0 基），
独立复验时按同一区间重切并比对（`source_locator_resolvable` 检查）。

| asset | class | resolution | char span | line span | snippet |
|---|---|---|---|---|---|
| `A01` | code_module | referenced_unresolved | 117–176 | 3–3 | `**落库**：`TensorPlatform` → 新模块 `tools/longrun/`（零领域语义，纯共性机制）` |
| `A02` | evidence_dataset | referenced_unresolved | 177–258 | 4–4 | `**证据**：`runs/m9082/evidence.json`（全部数字由 `tools/longrun/bench_m9082.py` 程序化生成，零手抄）` |
| `A03` | figure_set | referenced_unresolved | 259–308 | 5–5 | `**图**：`runs/m9082/figures/fig1..4`（matplotlib 生成）` |
| `A04` | test_suite | referenced_unresolved | 309–393 | 6–6 | `**测试**：`tests/test_longrun_{forensics,checkpoint_resume,ladder,overhead}.py` 共 32 用例` |
| `A05` | code_module | referenced_unresolved | 662–755 | 20–20 | `\| 崩溃取证 \| `guardian.py`（ptrace 监护 + gdb 取证）、`forensics.py`（机载记录仪/分类/完整率） \| 故意崩溃 → 取证完整率 100% \|` |
| `A06` | code_module | referenced_unresolved | 756–837 | 21–21 | `\| 断点续跑 \| `checkpoint.py`（位级摘要+原子写+链式清单）、`resume.py`（幂等键+审计） \| 同输入+同断点 → 同输出（位级） \|` |
| `A07` | code_module | referenced_unresolved | 838–892 | 22–22 | `\| 资源降级 \| `ladder.py`（四级阶梯） \| 压力上升 → 按序降级 → 优雅退出且末态可续 \|` |
| `A08` | code_module | referenced_unresolved | 893–948 | 23–23 | `\| 负控 \| `runner.py` + `bench_m9082.py` \| 正常作业取证开销 ≤ 2% \|` |
| `A09` | test_job_spec | referenced_unresolved | 950–1114 | 25–27 | `测试作业 `job.py::SyntheticIterativeJob` 是刻意"无物理语义"的线性迭代松弛 ⏎ `u ← u + dt·(∇²u + c)`（周期网格、种子固定、纯逐元素 IEEE-754 运算），只用…` |
| `A10` | design_table | resolved_in_source | 629–948 | 18–23 | `\| 能力 \| 部件 \| 关键判据 \| ⏎ \|---\|---\|---\| ⏎ \| 崩溃取证 \| `guardian.py`（ptrace 监护 + gdb 取证）、`forensics.py`（机载记录仪…` |
| `A11` | procedure_spec | resolved_in_source | 1667–2233 | 48–61 | ```` ⏎ fork → 子进程 ptrace(PTRACE_TRACEME) → execve(job) ⏎ 父进程 poll waitpid： ⏎   SIGTRAP(exec)      → PTRACE_CONT…` |
| `A12` | measurement_table | resolved_in_source | 2588–2838 | 73–76 | `\| 级别 \| 内容 \| 体积（实测） \| 默认 \| ⏎ \|---\|---\|---\|---\| ⏎ \| tier-1 `stackcore.json` \| 全线程 backtrace、符号化帧、内存映…` |
| `A13` | measurement_protocol | resolved_in_source | 5236–5398 | 143–145 | `**方法学留证**：AB-only（每轮固定先裸后带）曾测出"幻影 +5.27 %"，把顺序对调后变成 −3.03 %， ⏎ 即位置偏置（cache/TLB 预热与频率漂移）主导了信号 → 故改用 ABBA 与中位数门，…` |
| `A14` | measurement_table | resolved_in_source | 4946–5234 | 135–141 | `\| 指标 \| 值 \| ⏎ \|---\|---\| ⏎ \| 逐轮开销（%） \| −6.39, −15.85, −14.49, 3.93, −1.45, −0.69, 0.80, −12.00, 1.46, 3.…` |
| `A15` | measurement_schema | resolved_in_source | 5433–5941 | 149–155 | `\| 模式 \| 判定 \| 信号(si_code) \| 退出 \| tier-1 工件 \| 原生帧/已符号化 \| 完整率 \| ⏎ \|---\|---\|---\|---\|---\|---\|---\| ⏎ …` |
| `A16` | measurement_schema | resolved_in_source | 5943–6144 | 157–159 | `完整率按 15 个必需字段计（schema/job_id/pid/起止时间/exit_code/term_signal/failure_mode/ ⏎ 分类理由/Python 栈快照/状态日志尾/内存探测/运行环境/代码…` |
| `A17` | measurement_table | resolved_in_source | 6199–6486 | 165–170 | `\| 续跑点 \| 结果摘要（sha256 前 16） \| 与不间断运行位级一致 \| 幂等键（前 12） \| 两次重复键一致 \| ⏎ \|---\|---\|---\|---\|---\| ⏎ \| 不间断 \|…` |
| `A18` | formula | resolved_in_source | 6488–6550 | 172–172 | `位级 = `sha256(dtype‖shape‖状态字节)`，即 **0 ULP、0 位差**，不是容差意义下的"一致"。` |
| `A19` | measurement_table | resolved_in_source | 6569–6876 | 176–182 | `\| 探针 \| 翻转数 \| 检出 \| 检出率 \| ⏎ \|---\|---\|---\|---\| ⏎ \| 数组载荷内随机字节（zip 条目数据区，按 header 偏移精确取样） \| 40 \| 40 \|…` |
| `A20` | measurement_note | resolved_in_source | 6878–6988 | 184–185 | `注：盲翻转若落进 zip 的 extra-field/padding，任何读者都看不到且状态**可证明未变**，这不是 ⏎ "漏检"而是"无所谓"；开发期一次盲取样确实出现 58/60，故测试改为按载荷取样以断言真正的性…` |
| `A21` | measurement_table | resolved_in_source | 7004–7336 | 189–195 | `\| 项 \| 值 \| ⏎ \|---\|---\| ⏎ \| 触及顺序 \| `reduce_precision → reduce_grid → reduce_timestep → graceful_exit` \|…` |
| `A22` | measurement_table | resolved_in_source | 7362–7677 | 199–204 | `\| 项 \| 值 \| ⏎ \|---\|---\| ⏎ \| 小进程真核 \| 14 048 136 B，`core_status = stackcore+elf`，独立 `gdb exe core -ex bt` …` |
| `A23` | figure | referenced_unresolved | 7724–7815 | 212–212 | `\| `fig1_overhead.png` \| 12 轮 ABBA 逐轮开销柱状 + 2 % 预算线 + 中位线 \| 柱子在 0 附近正负抖动（噪声），无系统性抬升；红线远在上方 \|` |
| `A24` | figure | referenced_unresolved | 7816–7943 | 213–213 | `\| `fig2_autopsy.png` \| 五种崩溃模式完整率（左）与 tier-1 工件体积（右） \| 左图全 100 %；右图 `exception`/`memory_error`/`sigkill` 无核（…` |
| `A25` | figure | referenced_unresolved | 7944–8011 | 214–214 | `\| `fig3_resume.png` \| 断点位置 vs 位级一致性 \| 所有断点落在 "identical" 水平线（3/3） \|` |
| `A26` | figure | referenced_unresolved | 8012–8093 | 215–215 | `\| `fig4_ladder.png` \| 上：内存利用率探测与四级阈值；下：状态占用阶梯 \| 每次跨阈值，占用阶梯下降，末端落到 graceful exit \|` |
| `A27` | environment_limitation | declared_absent | 8733–8933 | 235–237 | `* **内核 core_pattern 在本容器不可用**：`core_pattern` 是 `\|/usr/lib/systemd/systemd-coredump`， ⏎   而容器无 systemd（`coredu…` |
| `A28` | scope_limitation | resolved_in_source | 9044–9147 | 240–241 | `* **位级一致限于同机同库**：跨 ISA（loong64 vs x86）浮点结果可能不同，届时须改用 ⏎   `tools/repro_digest`（ULP/12 位有效数字）判据，而不是 sha256。` |
| `A29` | measurement_table | resolved_in_source | 9560–10081 | 254–263 | `\| 关键量 \| 基准 \| 实测 \| 相对误差 \| < 3 % ? \| ⏎ \|---\|---\|---\|---\|---\| ⏎ \| 取证层开销（中位数） \| 裸循环 CPU 时间 \| −0.65 …` |
| `A30` | repro_command | resolved_in_source | 10181–10449 | 272–276 | ````bash ⏎ python3 -m pytest tests/test_longrun_forensics.py tests/test_longrun_checkpoint_resume.py \ ⏎       …` |
| `A31` | code_snippet | resolved_in_source | 10458–10814 | 280–286 | ````python ⏎ from tools.longrun import supervise ⏎ rep = supervise.supervise({"job": {"grid": 256}, "steps": 20…` |

**范围外但重要的登记事实**

- 图件：平台 payload 提供 4 条 figure 元数据（name/caption 齐备），但 `png_base64` 长度为 0，
  `runs/m9082/figures/` 也不在本工作树 → 四张图登记为 `referenced_unresolved`（元数据可解析、位图在本环境不可得）。
  **同平台实测**（本工单提交的图件 `png_base64` 长度 234512 → API 返回 0；图件下载端点 /tensor/reports/14772/figures→404, /tensor/figures/14772/fig1_asset_resolution.png→404），说明"响应里没有字节"不等于"作者没附图"，故清单只声明"不可得"、不推断上游缺失。
- 代码/测试/证据工件：TensorPlatform 仓路径，在本工作树（TensorKnowledge）逐一探测为缺失：
  `runs/m9082/evidence.json`, `runs/m9082/figures/`, `tests/test_longrun_checkpoint_resume.py`, `tests/test_longrun_forensics.py`, `tests/test_longrun_ladder.py`, `tests/test_longrun_overhead.py`, `tools/longrun/`, `tools/longrun/bench_m9082.py`, `tools/longrun/checkpoint.py`, `tools/longrun/forensics.py`, `tools/longrun/guardian.py`, `tools/longrun/job.py`, `tools/longrun/ladder.py`, `tools/longrun/resume.py`, `tools/longrun/runner.py`。
- 环境限制 A27（内核自发 core 采集）：`declared_absent`，并附本容器实测探针
  （core_pattern = `|/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %h`，
  pipe 目标是否存在 = True，
  `coredumpctl` = `/usr/bin/coredumpctl`，
  可用性 = True）。
  **探针对象是本工作树容器，不是报告作者的容器**，故不改写上游结论，只留可复跑记录。

## ⑤ 注意点与局限（honest）

1. **不做抽取**：claims=[] 是契约允许的完整结果，不是遗漏。下游 03 工序如需知识对象，应基于本清单的
   `asset_id` 引用，而不是重新手抄原报告。
2. **数字未复核**：报告 ③⑥ 两节的量化结论（开销中位数 −0.65 %、完整率 100 %、位级一致、检出 40/40 等）
   在本清单里只是**被定位的文本**（`artifact_trace` 检查记录 `runs/m9082/evidence.json` 缺失）。
   任何下游若要使用这些数字，必须先取回 evidence.json 复算。
3. **图件不可取**：4 张图只有 name/caption；本报告自己的图（fig1）是**新生成**的登记总览图，
   不是上游图的复现。
4. **A10 与 A05–A08 刻意嵌套**：设计表是容器级跨度，包含自身 4 行；verifier 的 `span_nesting`
   白名单只允许这 4 对，其它重叠会判 FAIL。
5. **A27 探针≠上游环境**：见 ④ 末尾；`coredumpctl` 存在于本镜像但报告作者容器无 systemd，两者不可互相推翻。
6. **schema 泛化是本地决定**：平台侧 `kf_result.v1.schema.json` 校验信封；清单本体用的是本仓新增的
   `asset_manifest.v2.schema.json`（v1 的 const 钉死 wp-448-01，无法复用）。若平台另有清单 schema，以平台为准，
   本清单需按其调整——这是本工序唯一"可能与平台不同步"的点。
7. **`in_report_section` 是最近前置标题**：报告头部 5 行资产的 section 因此是 H1 标题行，属预期行为。
8. 未做独立评审（契约 review.required=false），本报告的全部 PASS 来自自检脚本，非第三方结论。
9. **平台图件回传**：本报告提交时附了非空 PNG，但 API 响应与 GET 均返回 `png_base64` 长度 0，且无图件下载端点
   （`/tensor/reports/<id>/figures`、`/tensor/figures/...` 均 404，见 `docs/kf/wp-10647-01/platform_figure_probe.json`）。
   因此平台侧只能看到图件元数据；图件本体见仓内 `artifacts/wp-10647-01/fig1_asset_resolution.png`。
   这条对全部 KF 报告通用：**不要把"payload 无图字节"记成"上游未附图"**。
10. **本包曾两次重复发布**（report id 14766、14772，同 package 早期草稿：14766 报告正文里混入了 2 处围栏标记词（散文提及），
   破坏"唯一结果块"信道，已改写并在生成器里加了"围栏块计数必须为 1"的硬断言；14772 早于本报告对图件回传的实测与 A23–A26
   注记修订）。两条草稿平台不提供更新/删除接口（PUT/PATCH/DELETE 均 405），故以本报告为准。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据摘要（`artifacts/wp-10647-01/verification.json`） |
|---|---|---|
| `valid_json` | ✔ | {"files": ["artifacts/wp-10647-01/asset_manifest.json", "runs/wp-10647-01/kf_result.wp-10647-01.json", "runs/wp-10647-01/kf_result_block.wp-10647-01.json"]} |
| `schema_pass` | ✔ | {"manifest_schema": "schemas/asset_manifest.v2.schema.json", "envelope_schema": "schemas/kf_result.v1.schema.json", "manifest_errors": [], "envelope_errors": [] |
| `source_locator_resolvable` | ✔ | {"locators_checked": 31, "locators_resolved": 31, "failures": [], "independence": "fresh API login + re-fetch in this process"} |
| `source_hash_matches` | ✔ | {"contract_declared": "sha256:aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31", "provenance": "sha256:aa10fd7a44acab4a0c877a58dab70f087877e249a |
| `no_duplicate_ids` | ✔ | {"asset_id_count": 31, "duplicate_asset_ids": [], "duplicate_locators": 0} |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✔ | {"claim_count": 0, "vacuous": true, "claims_without_evidence_or_status": [], "contract_note": "objective.classify_report_type=false / notes: claims 允许为空数组"} |

额外一致性检查（非契约要求，但可作为回归护栏）：

| 检查 | 结果 |
|---|---|
| `counts_consistent` | ✔ |
| `resolution_check_result_consistent` | ✔ |
| `span_nesting` | ✔ |
| `no_verified_marks` | ✔ |
| `envelope_identity` | ✔ |
| `platform_figure_metadata` | ✔ |

**误差/偏差判定（对照本工序的基准，显式回答）**

| 关键量 | 基准 | 实测 | 偏差 | 是否 < 3 % |
|---|---|---|---|---|
| 源 markdown sha256 | 契约 `aa10fd7a…bf31` | 重算 `aa10fd7a44acab4a…` | 0 位差 | **是**（exact） |
| 源字符数 | 契约 `10814` | 10814 | 0 % | **是**（exact） |
| 引文可定位率 | 31/31 | 31/31 | 0 % | **是** |
| 引文唯一性 | 100 % | 100 %（`no_duplicate_ids` 的 duplicate_locators=0） | 0 % | **是** |

无基准项（如实声明，不以"未测"充数）：上游数值结论的复算误差——基准工件 `runs/m9082/evidence.json`
不在本工作树，本工序无基准可对，故**不复算、不判定**。

## 复现（一键）

```bash
# 环境：TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE（默认 http://127.0.0.1:8010/api/v1）
python3 scripts/kf_fetch_10647.py              # 取回 report 10647（校验 sha256 与 10814 字符）
python3 scripts/kf_register_10647.py           # 生成 asset_manifest.json + 结果信封
python3 scripts/kf_verify_10647.py             # 独立复验六项 acceptance（新登录重取 + 重切引文）
python3 scripts/fig_asset_inventory_wp10647_01.py   # 重新出图
python3 -m pytest tests/test_kf_wp10647.py -q  # 离线回归（无需网络）
```

## 附录：结果信封（kf_result.v1，与报告内唯一结果围栏块逐字节相同）

```json
{
  "package_id": "wp-10647-01",
  "task_type": "01-asset-registration",
  "report_id": "10647",
  "provenance": {
    "source_uri": "tensor://reports/10647",
    "source_field": "markdown",
    "source_hash": "sha256:aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31",
    "chars": 10814,
    "bytes_utf8": 17194,
    "title": "【长跑生存层】核心转储取证 + 位级幂等断点续跑 + 资源降级阶梯（m9082 / p148w2-n03）",
    "scenario_key": "crash-forensics-resume",
    "producer": "scripts/kf_register_10647.py",
    "emitted_at": "2026-11-12T01:48:38+00:00",
    "notes": "asset registration only; claims intentionally empty; nothing marked verified",
    "contract_declared_hash": "sha256:aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31",
    "hash_match": true,
    "platform_mission_id": 9082,
    "platform_status": "published",
    "platform_tags": [
      "long-run",
      "crash-forensics",
      "core-dump",
      "ptrace",
      "gdb",
      "checkpoint",
      "idempotent-resume",
      "graceful-degradation",
      "platform-infra",
      "p148w2-n03"
    ]
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-10647-01",
      "task_type": "01-asset-registration",
      "report_id": "10647",
      "source": {
        "uri": "tensor://reports/10647",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "aa10fd7a44acab4a0c877a58dab70f087877e249a28e2684f9a6a7a2d6dfbf31",
        "chars": 10814,
        "bytes_utf8": 17194,
        "title": "【长跑生存层】核心转储取证 + 位级幂等断点续跑 + 资源降级阶梯（m9082 / p148w2-n03）",
        "scenario_key": "crash-forensics-resume",
        "platform_figures": [
          {
            "name": "fig1_overhead.png",
            "caption": "ABBA 分块实验：取证层相对裸循环的 CPU 时间开销逐轮值；中位数 -0.65%（红线=2% 预算），仪器自计成本 0.089%。",
            "png_bytes": 0
          },
          {
            "name": "fig2_autopsy.png",
            "caption": "五种故意崩溃模式的取证完整率（全部 100%）与一级 stackcore 工件体积。",
            "png_bytes": 0
          },
          {
            "name": "fig3_resume.png",
            "caption": "断点续跑位级幂等性：从 10/20/35 步断点续跑（各重复 2 次）与不间断运行的最终状态 sha256 完全一致（3/3）。",
            "png_bytes": 0
          },
          {
            "name": "fig4_ladder.png",
            "caption": "资源降级阶梯：内存利用率探测曲线与阈值（上）、状态占用面积随阶梯下台阶梯式下降（下），总降幅 0.125×。",
            "png_bytes": 0
          }
        ],
        "platform_tags": [
          "long-run",
          "crash-forensics",
          "core-dump",
          "ptrace",
          "gdb",
          "checkpoint",
          "idempotent-resume",
          "graceful-degradation",
          "platform-infra",
          "p148w2-n03"
        ],
        "platform_mission_id": 9082,
        "platform_status": "published"
      },
      "counts": {
        "assets": 31,
        "by_class": {
          "code_module": 5,
          "code_snippet": 1,
          "design_table": 1,
          "environment_limitation": 1,
          "evidence_dataset": 1,
          "figure": 4,
          "figure_set": 1,
          "formula": 1,
          "measurement_note": 1,
          "measurement_protocol": 1,
          "measurement_schema": 2,
          "measurement_table": 7,
          "procedure_spec": 1,
          "repro_command": 1,
          "scope_limitation": 1,
          "test_job_spec": 1,
          "test_suite": 1
        },
        "by_resolution": {
          "declared_absent": 1,
          "referenced_unresolved": 13,
          "resolved_in_source": 17
        },
        "resolved_in_source": 17,
        "referenced_unresolved": 13,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "code_module",
          "label": "TensorPlatform 新模块目录 tools/longrun/（零领域语义共性机制）",
          "in_report_section": "# 长跑作业生存层：核心转储取证 + 位级幂等断点续跑 + 资源降级阶梯",
          "locator": {
            "method": "char_span",
            "start_char": 117,
            "end_char": 176,
            "start_line": 3,
            "end_line": 3,
            "quote": "**落库**：`TensorPlatform` → 新模块 `tools/longrun/`（零领域语义，纯共性机制）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "repo": "TensorKnowledge",
            "paths": [
              "tools/longrun/"
            ],
            "present": [],
            "missing": [
              "tools/longrun/"
            ],
            "result": "unresolved"
          },
          "note": "TensorPlatform 仓内路径；本工作树（TensorKnowledge）无该目录，模块实体不可在此解析"
        },
        {
          "asset_id": "A02",
          "asset_class": "evidence_dataset",
          "label": "证据工件 runs/m9082/evidence.json（全部数字的程序化来源）",
          "in_report_section": "# 长跑作业生存层：核心转储取证 + 位级幂等断点续跑 + 资源降级阶梯",
          "locator": {
            "method": "char_span",
            "start_char": 177,
            "end_char": 258,
            "start_line": 4,
            "end_line": 4,
            "quote": "**证据**：`runs/m9082/evidence.json`（全部数字由 `tools/longrun/bench_m9082.py` 程序化生成，零手抄）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "repo": "TensorKnowledge",
            "paths": [
              "runs/m9082/evidence.json"
            ],
            "present": [],
            "missing": [
              "runs/m9082/evidence.json"
            ],
            "result": "unresolved"
          },
          "note": "报告声明全部数字由此工件程序化生成；工件不在本工作树，故本工序只定位不复核数值"
        },
        {
          "asset_id": "A03",
          "asset_class": "figure_set",
          "label": "图工件目录 runs/m9082/figures/fig1..4（matplotlib 生成）",
          "in_report_section": "# 长跑作业生存层：核心转储取证 + 位级幂等断点续跑 + 资源降级阶梯",
          "locator": {
            "method": "char_span",
            "start_char": 259,
            "end_char": 308,
            "start_line": 5,
            "end_line": 5,
            "quote": "**图**：`runs/m9082/figures/fig1..4`（matplotlib 生成）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "repo": "TensorKnowledge",
            "paths": [
              "runs/m9082/figures/"
            ],
            "present": [],
            "missing": [
              "runs/m9082/figures/"
            ],
            "result": "unresolved"
          },
          "note": "目录不在本工作树；四张图的名称/说明另见平台 payload（A22–A25）"
        },
        {
          "asset_id": "A04",
          "asset_class": "test_suite",
          "label": "测试套件 tests/test_longrun_{forensics,checkpoint_resume,ladder,overhead}.py（共 32 用例）",
          "in_report_section": "# 长跑作业生存层：核心转储取证 + 位级幂等断点续跑 + 资源降级阶梯",
          "locator": {
            "method": "char_span",
            "start_char": 309,
            "end_char": 393,
            "start_line": 6,
            "end_line": 6,
            "quote": "**测试**：`tests/test_longrun_{forensics,checkpoint_resume,ladder,overhead}.py` 共 32 用例",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "repo": "TensorKnowledge",
            "paths": [
              "tests/test_longrun_forensics.py",
              "tests/test_longrun_checkpoint_resume.py",
              "tests/test_longrun_ladder.py",
              "tests/test_longrun_overhead.py"
            ],
            "present": [],
            "missing": [
              "tests/test_longrun_forensics.py",
              "tests/test_longrun_checkpoint_resume.py",
              "tests/test_longrun_ladder.py",
              "tests/test_longrun_overhead.py"
            ],
            "result": "unresolved"
          },
          "note": "TensorPlatform 的 tests/；本仓 tests/ 内无同名文件（本仓 tests/ 是 TensorKnowledge 的）"
        },
        {
          "asset_id": "A05",
          "asset_class": "code_module",
          "label": "崩溃取证部件 guardian.py（ptrace 监护 + gdb 取证）与 forensics.py（记录仪/分类/完整率）",
          "in_report_section": "## ① 案例介绍（问题背景与对象）",
          "locator": {
            "method": "char_span",
            "start_char": 662,
            "end_char": 755,
            "start_line": 20,
            "end_line": 20,
            "quote": "| 崩溃取证 | `guardian.py`（ptrace 监护 + gdb 取证）、`forensics.py`（机载记录仪/分类/完整率） | 故意崩溃 → 取证完整率 100% |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "repo": "TensorKnowledge",
            "paths": [
              "tools/longrun/guardian.py",
              "tools/longrun/forensics.py"
            ],
            "present": [],
            "missing": [
              "tools/longrun/guardian.py",
              "tools/longrun/forensics.py"
            ],
            "result": "unresolved"
          },
          "note": "能力表首行；模块实体在 TensorPlatform 仓，本工作树不可解析"
        },
        {
          "asset_id": "A06",
          "asset_class": "code_module",
          "label": "断点续跑部件 checkpoint.py（位级摘要+原子写+链式清单）与 resume.py（幂等键+审计）",
          "in_report_section": "## ① 案例介绍（问题背景与对象）",
          "locator": {
            "method": "char_span",
            "start_char": 756,
            "end_char": 837,
            "start_line": 21,
            "end_line": 21,
            "quote": "| 断点续跑 | `checkpoint.py`（位级摘要+原子写+链式清单）、`resume.py`（幂等键+审计） | 同输入+同断点 → 同输出（位级） |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "repo": "TensorKnowledge",
            "paths": [
              "tools/longrun/checkpoint.py",
              "tools/longrun/resume.py"
            ],
            "present": [],
            "missing": [
              "tools/longrun/checkpoint.py",
              "tools/longrun/resume.py"
            ],
            "result": "unresolved"
          },
          "note": "能力表第二行；模块实体不在本工作树"
        },
        {
          "asset_id": "A07",
          "asset_class": "code_module",
          "label": "资源降级部件 ladder.py（四级阶梯）",
          "in_report_section": "## ① 案例介绍（问题背景与对象）",
          "locator": {
            "method": "char_span",
            "start_char": 838,
            "end_char": 892,
            "start_line": 22,
            "end_line": 22,
            "quote": "| 资源降级 | `ladder.py`（四级阶梯） | 压力上升 → 按序降级 → 优雅退出且末态可续 |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "repo": "TensorKnowledge",
            "paths": [
              "tools/longrun/ladder.py"
            ],
            "present": [],
            "missing": [
              "tools/longrun/ladder.py"
            ],
            "result": "unresolved"
          },
          "note": "能力表第三行；模块实体不在本工作树"
        },
        {
          "asset_id": "A08",
          "asset_class": "code_module",
          "label": "负控部件 runner.py 与基准脚本 bench_m9082.py",
          "in_report_section": "## ① 案例介绍（问题背景与对象）",
          "locator": {
            "method": "char_span",
            "start_char": 893,
            "end_char": 948,
            "start_line": 23,
            "end_line": 23,
            "quote": "| 负控 | `runner.py` + `bench_m9082.py` | 正常作业取证开销 ≤ 2% |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "repo": "TensorKnowledge",
            "paths": [
              "tools/longrun/runner.py",
              "tools/longrun/bench_m9082.py"
            ],
            "present": [],
            "missing": [
              "tools/longrun/runner.py",
              "tools/longrun/bench_m9082.py"
            ],
            "result": "unresolved"
          },
          "note": "能力表第四行；模块实体不在本工作树"
        },
        {
          "asset_id": "A09",
          "asset_class": "test_job_spec",
          "label": "测试作业 job.py::SyntheticIterativeJob（线性迭代松弛 u ← u + dt·(∇²u + c)，无物理语义）",
          "in_report_section": "## ① 案例介绍（问题背景与对象）",
          "locator": {
            "method": "char_span",
            "start_char": 950,
            "end_char": 1114,
            "start_line": 25,
            "end_line": 27,
            "quote": "测试作业 `job.py::SyntheticIterativeJob` 是刻意\"无物理语义\"的线性迭代松弛\n`u ← u + dt·(∇²u + c)`（周期网格、种子固定、纯逐元素 IEEE-754 运算），只用于让上述机制可被\n位级验证；**不含任何船舶/物理域词条**（TensorPlatform 铁律：零领域语义）。",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "worktree_path_exists",
            "repo": "TensorKnowledge",
            "paths": [
              "tools/longrun/job.py"
            ],
            "present": [],
            "missing": [
              "tools/longrun/job.py"
            ],
            "result": "unresolved"
          },
          "note": "合成作业定义在 TensorPlatform 仓；本工作树无此文件，作业实现不可解析"
        },
        {
          "asset_id": "A10",
          "asset_class": "design_table",
          "label": "能力→部件→判据映射表（4 行）",
          "in_report_section": "## ① 案例介绍（问题背景与对象）",
          "locator": {
            "method": "char_span",
            "start_char": 629,
            "end_char": 948,
            "start_line": 18,
            "end_line": 23,
            "quote": "| 能力 | 部件 | 关键判据 |\n|---|---|---|\n| 崩溃取证 | `guardian.py`（ptrace 监护 + gdb 取证）、`forensics.py`（机载记录仪/分类/完整率） | 故意崩溃 → 取证完整率 100% |\n| 断点续跑 | `checkpoint.py`（位级摘要+原子写+链式清单）、`resume.py`（幂等键+审计） | 同输入+同断点 → 同输出（位级） |\n| 资源降级 | `ladder.py`（四级阶梯） | 压力上升 → 按序降级 → 优雅退出且末态可续 |\n| 负控 | `runner.py` + `bench_m9082.py` | 正常作业取证开销 ≤ 2% |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "上游自报的部件划分与判据；本工序只登记不复核判据是否达成。本资产为容器级跨度，刻意包含 A05–A08 四个逐行资产（见 artifacts/wp-10647-01/verification.json 的 span_nesting 白名单）"
        },
        {
          "asset_id": "A11",
          "asset_class": "procedure_spec",
          "label": "ptrace 监护流程伪代码（fork→PTRACE_TRACEME→execve→waitpid→DETACH→gdb -batch→SIGKILL）",
          "in_report_section": "### 2.2 ptrace 监护（`guardian.py::run_guarded`）",
          "locator": {
            "method": "char_span",
            "start_char": 1667,
            "end_char": 2233,
            "start_line": 48,
            "end_line": 61,
            "quote": "```\nfork → 子进程 ptrace(PTRACE_TRACEME) → execve(job)\n父进程 poll waitpid：\n  SIGTRAP(exec)      → PTRACE_CONT(0)\n  非致命信号          → PTRACE_CONT(sig)   # 语义透传，作业行为不变\n  致命信号(SIGSEGV/ABRT/BUS/FPE/ILL)\n        → PTRACE_GETSIGINFO（si_signo/si_code/si_addr）\n        → PTRACE_DETACH(data=SIGSTOP)     # 冻结，等 gdb 接管\n        → gdb -p <pid> -batch: info threads / thread apply all bt 12 /\n                               info proc mappings / thread apply all info registers /\n                               [可选] gcore <path>\n        → addr2line -f -C 补全 ? 帧\n        → SIGKILL 收尸\n```",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "tool_probe",
            "tools": {
              "gdb": "/usr/bin/gdb",
              "addr2line": "/usr/bin/addr2line"
            },
            "all_present": true,
            "result": "resolved",
            "detail": "流程规范自身可在原文解析；工具探测只记录本容器现状"
          },
          "note": "流程图以代码块给出；工具可用性探测见 resolution_check（探测对象=本工作树容器，非作者容器）"
        },
        {
          "asset_id": "A12",
          "asset_class": "measurement_table",
          "label": "两级取证工件表（tier-1 stackcore.json 8.9–30.8 KB / tier-2 ELF core 14 MB 与 4.44 GB）",
          "in_report_section": "### 2.3 两级取证工件（为什么不是\"永远一个 4 GB core\"）",
          "locator": {
            "method": "char_span",
            "start_char": 2588,
            "end_char": 2838,
            "start_line": 73,
            "end_line": 76,
            "quote": "| 级别 | 内容 | 体积（实测） | 默认 |\n|---|---|---|---|\n| tier-1 `stackcore.json` | 全线程 backtrace、符号化帧、内存映射、寄存器、siginfo、gdb 版本 | **8.9–30.8 KB** | 开 |\n| tier-2 ELF core | `gcore` 真核，可独立 `gdb <exe> <core> -ex bt` 复现栈 | 小进程 **14 MB**；numpy 进程 **4.44 GB** | 关（可开） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "体积数字唯一可溯源副本为 runs/m9082/evidence.json（本工作树缺失），故只定位不复算"
        },
        {
          "asset_id": "A13",
          "asset_class": "measurement_protocol",
          "label": "开销测量方法学留证：AB-only 位置偏置（幻影 +5.27 %/−3.03 %）→ ABBA + 中位数门",
          "in_report_section": "### 3.1 负控：正常作业取证开销 ≤ 2%",
          "locator": {
            "method": "char_span",
            "start_char": 5236,
            "end_char": 5398,
            "start_line": 143,
            "end_line": 145,
            "quote": "**方法学留证**：AB-only（每轮固定先裸后带）曾测出\"幻影 +5.27 %\"，把顺序对调后变成 −3.03 %，\n即位置偏置（cache/TLB 预热与频率漂移）主导了信号 → 故改用 ABBA 与中位数门，并把这条写进\n`tests/test_longrun_overhead.py` 的文档字符串，防止后人再踩。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "描述了测量协议的迭代与理由；逐轮开销值见 A14 上游（§3.1 表）"
        },
        {
          "asset_id": "A14",
          "asset_class": "measurement_table",
          "label": "§3.1 负控开销表（逐轮 12 值、中位数 −0.65 %、最大 +14.52 %、仪器自计 0.0889 %）",
          "in_report_section": "### 3.1 负控：正常作业取证开销 ≤ 2%",
          "locator": {
            "method": "char_span",
            "start_char": 4946,
            "end_char": 5234,
            "start_line": 135,
            "end_line": 141,
            "quote": "| 指标 | 值 |\n|---|---|\n| 逐轮开销（%） | −6.39, −15.85, −14.49, 3.93, −1.45, −0.69, 0.80, −12.00, 1.46, 3.33, −0.60, 14.52 |\n| **中位数** | **−0.65 %**（噪声主导，低于测噪底） |\n| 最大（干扰尖峰） | +14.52 % |\n| 仪器自计成分开销 | **0.0889 %**（journal + 内存探测，`overhead_ns / layer_cpu_seconds`） |\n| 判据 | 中位数 ≤2 % ✔，仪器自计 ≤2 % ✔ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "artifact_trace",
            "artifact": "runs/m9082/evidence.json",
            "present_in_worktree": false,
            "result": "resolved",
            "detail": "引文可定位（resolved）；数值复算需 runs/m9082/evidence.json，本工作树缺失 → 未复算"
          },
          "note": "数值可逐字定位；复算需 evidence.json（本工作树缺失）→ 仅登记，不做数值复核"
        },
        {
          "asset_id": "A15",
          "asset_class": "measurement_schema",
          "label": "崩溃取证表（5 种注入模式：segv/abort/exception/memory_error/sigkill，完整率均 100 %）",
          "in_report_section": "### 3.2 崩溃取证：五种故意崩溃 → 完整率 100 %",
          "locator": {
            "method": "char_span",
            "start_char": 5433,
            "end_char": 5941,
            "start_line": 149,
            "end_line": 155,
            "quote": "| 模式 | 判定 | 信号(si_code) | 退出 | tier-1 工件 | 原生帧/已符号化 | 完整率 |\n|---|---|---|---|---|---|---|\n| `segv` | native_segfault | 11 (1 = SEGV_MAPERR, addr 0x0) | −11 | 30831 B | 19/19 | **100 %** |\n| `abort` | native_abort | 6 (−6 = SI_TKILL) | −6 | 30712 B | 19/19 | **100 %** |\n| `exception` | python_exception | — | 70 | 无核（非信号） | — | **100 %** |\n| `memory_error` | python_memory_error | — | 71 | 无核（非信号） | — | **100 %** |\n| `sigkill` | killed_externally | 9（cgroup oom_kill 未增长，故不判 OOM） | −9 | 无核 | — | **100 %** |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "artifact_trace",
            "artifact": "runs/m9082/evidence.json",
            "present_in_worktree": false,
            "result": "resolved",
            "detail": "引文可定位（resolved）；数值复算需 runs/m9082/evidence.json，本工作树缺失 → 未复算"
          },
          "note": "上传上游自报 100 %；本工序不复核，也不标 verified"
        },
        {
          "asset_id": "A16",
          "asset_class": "measurement_schema",
          "label": "取证完整率口径：15 个必需字段（schema/job_id/pid/…/最后检查点摘要）+ 信号类崩溃额外计入 ELF core",
          "in_report_section": "### 3.2 崩溃取证：五种故意崩溃 → 完整率 100 %",
          "locator": {
            "method": "char_span",
            "start_char": 5943,
            "end_char": 6144,
            "start_line": 157,
            "end_line": 159,
            "quote": "完整率按 15 个必需字段计（schema/job_id/pid/起止时间/exit_code/term_signal/failure_mode/\n分类理由/Python 栈快照/状态日志尾/内存探测/运行环境/代码版本/最后检查点摘要；ELF core 在\n信号类崩溃额外计入必需）。网格/序列号/摘要均可回溯到 `runs/m9082/artifacts/bundle_crash_*.json`。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "完整率的分母定义在此；缺此口径则 100 % 不可解释"
        },
        {
          "asset_id": "A17",
          "asset_class": "measurement_table",
          "label": "§3.3 位级幂等续跑表（断点 10/20/35，摘要 f80ed84ab59f2374 全一致，幂等键 1dbad8a55a4f/93f94d256fec）",
          "in_report_section": "### 3.3 位级幂等续跑",
          "locator": {
            "method": "char_span",
            "start_char": 6199,
            "end_char": 6486,
            "start_line": 165,
            "end_line": 170,
            "quote": "| 续跑点 | 结果摘要（sha256 前 16） | 与不间断运行位级一致 | 幂等键（前 12） | 两次重复键一致 |\n|---|---|---|---|---|\n| 不间断 | `f80ed84ab59f2374` | — | — | — |\n| 10 | `f80ed84ab59f2374` | ✔ | `1dbad8a55a4f` | ✔ |\n| 20 | `f80ed84ab59f2374` | ✔ | `93f94d256fec` | ✔ |\n| 35 | `f80ed84ab59f2374` | ✔ | （见 evidence.json） | ✔ |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "artifact_trace",
            "artifact": "runs/m9082/evidence.json",
            "present_in_worktree": false,
            "result": "resolved",
            "detail": "引文可定位（resolved）；数值复算需 runs/m9082/evidence.json，本工作树缺失 → 未复算"
          },
          "note": "断点 35 的幂等键上游明确留白（见 evidence.json），本工序不补造"
        },
        {
          "asset_id": "A18",
          "asset_class": "formula",
          "label": "位级摘要定义：sha256(dtype‖shape‖状态字节)，即 0 ULP 判据而非容差判据",
          "in_report_section": "### 3.3 位级幂等续跑",
          "locator": {
            "method": "char_span",
            "start_char": 6488,
            "end_char": 6550,
            "start_line": 172,
            "end_line": 172,
            "quote": "位级 = `sha256(dtype‖shape‖状态字节)`，即 **0 ULP、0 位差**，不是容差意义下的\"一致\"。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "该定义决定“一致”的含义（位级 vs 容差）；跨 ISA 适用性限制登记为 A28"
        },
        {
          "asset_id": "A19",
          "asset_class": "measurement_table",
          "label": "§3.4 检查点损坏检出表（载荷翻转 40/40、盲翻转 60/60、清单篡改 1/1、删数组 1/1、残留 .tmp 正确忽略）",
          "in_report_section": "### 3.4 检查点损坏检出",
          "locator": {
            "method": "char_span",
            "start_char": 6569,
            "end_char": 6876,
            "start_line": 176,
            "end_line": 182,
            "quote": "| 探针 | 翻转数 | 检出 | 检出率 |\n|---|---|---|---|\n| 数组载荷内随机字节（zip 条目数据区，按 header 偏移精确取样） | 40 | 40 | **100 %** |\n| 整文件盲翻转（含 zip 簿记区） | 60 | 60 | 100 %（本次盲取样全部落在载荷内） |\n| 清单字段篡改（改 `scalars.dt`） | 1 | 1 | 100 %（清单摘要不符） |\n| 删除一个数组 | 1 | 1 | 100 %（`unexpected/missing arrays`） |\n| 残留 `.tmp` 半成品存在 | 1 | — | 正确忽略，仍加载完整档 |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "artifact_trace",
            "artifact": "runs/m9082/evidence.json",
            "present_in_worktree": false,
            "result": "resolved",
            "detail": "引文可定位（resolved）；数值复算需 runs/m9082/evidence.json，本工作树缺失 → 未复算"
          },
          "note": "检出率为上游自报；探针构造方式依赖 checkpoint.py（本工作树缺失）不可复现"
        },
        {
          "asset_id": "A20",
          "asset_class": "measurement_note",
          "label": "盲翻转落进 zip 簿记区（extra-field/padding）不算漏检的论证（开发期曾 58/60）",
          "in_report_section": "### 3.4 检查点损坏检出",
          "locator": {
            "method": "char_span",
            "start_char": 6878,
            "end_char": 6988,
            "start_line": 184,
            "end_line": 185,
            "quote": "注：盲翻转若落进 zip 的 extra-field/padding，任何读者都看不到且状态**可证明未变**，这不是\n\"漏检\"而是\"无所谓\"；开发期一次盲取样确实出现 58/60，故测试改为按载荷取样以断言真正的性质。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "上游对“检出率不足 100 %”的反例与辩解，保留原文不做判定"
        },
        {
          "asset_id": "A21",
          "asset_class": "measurement_table",
          "label": "§3.5 降级阶梯结果（占用 65536→8192 B=0.125×、末态 grid 32→16、退出码 75）",
          "in_report_section": "### 3.5 降级阶梯",
          "locator": {
            "method": "char_span",
            "start_char": 7004,
            "end_char": 7336,
            "start_line": 189,
            "end_line": 195,
            "quote": "| 项 | 值 |\n|---|---|\n| 触及顺序 | `reduce_precision → reduce_grid → reduce_timestep → graceful_exit` |\n| 状态占用 | 65536 B → 8192 B（**0.125×**，下降 8 倍） |\n| 末态 | grid 32→16、precision float32、dt 0.25→0.5 |\n| 退出码 | **75**（`GRACEFUL_EXIT_CODE`），`failure_mode = graceful_degraded_exit` |\n| 末态检查点 | 可加载、`digest` 自校验通过，`bundle completeness = 1.0` |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "artifact_trace",
            "artifact": "runs/m9082/evidence.json",
            "present_in_worktree": false,
            "result": "resolved",
            "detail": "引文可定位（resolved）；数值复算需 runs/m9082/evidence.json，本工作树缺失 → 未复算"
          },
          "note": "退出码 75 语义（sysexits EX_TEMPFAIL）在 §2.7 阶梯表给出"
        },
        {
          "asset_id": "A22",
          "asset_class": "measurement_table",
          "label": "§3.6 ELF 真核结果（14 048 136 B、reopen_ok=True、13 帧、取证 0.264 s、cap=1 MiB 守卫）",
          "in_report_section": "### 3.6 ELF 真核（tier-2）",
          "locator": {
            "method": "char_span",
            "start_char": 7362,
            "end_char": 7677,
            "start_line": 199,
            "end_line": 204,
            "quote": "| 项 | 值 |\n|---|---|\n| 小进程真核 | 14 048 136 B，`core_status = stackcore+elf`，独立 `gdb exe core -ex bt` **reopen_ok=True**，13 帧 |\n| 取证耗时 | 0.264 s |\n| 尺寸守卫（cap=1 MiB） | 核先算 sha256/体积 → 删除 → `stackcore_only:elf_core_oversize`，tier-1 仍保留 |\n| 运行时最大匿名映射 | 4 294 967 296 B（4 GiB）→ numpy 进程真核实测 4 448 817 440 B（开发期一次，未重跑以省磁盘） |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "artifact_trace",
            "artifact": "runs/m9082/evidence.json",
            "present_in_worktree": false,
            "result": "resolved",
            "detail": "引文可定位（resolved）；数值复算需 runs/m9082/evidence.json，本工作树缺失 → 未复算"
          },
          "note": "numpy 进程 4 448 817 440 B 为“开发期一次，未重跑省磁盘”，不可复现项已由上游自陈"
        },
        {
          "asset_id": "A23",
          "asset_class": "figure",
          "label": "图 fig1_overhead.png（12 轮 ABBA 开销柱状 + 2 % 预算线 + 中位线）",
          "in_report_section": "## ④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 7724,
            "end_char": 7815,
            "start_line": 212,
            "end_line": 212,
            "quote": "| `fig1_overhead.png` | 12 轮 ABBA 逐轮开销柱状 + 2 % 预算线 + 中位线 | 柱子在 0 附近正负抖动（噪声），无系统性抬升；红线远在上方 |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figure_metadata",
            "figure_name": "fig1_overhead.png",
            "name_in_payload": true,
            "caption_in_payload": true,
            "png_bytes_in_payload": 0,
            "name_in_quote": true,
            "result": "unresolved",
            "detail": "payload 提供 name/caption；png_base64 为空且目录不在本工作树 → 位图在本环境不可得。同平台实测（docs/kf/wp-10647-01/platform_figure_probe.json）：本工单提交的非空 png 在 API 响应中同样返回 0 字节，且无图件下载端点 → 空字节是响应侧行为，不能据此推断作者未附图"
          },
          "note": "平台 payload 有 name/caption；png_base64 为空且 runs/m9082/figures/ 不在本工作树 → 位图在本环境不可得（平台响应不回传图件字节，见 platform_figure_probe.json，不推断作者是否附图）"
        },
        {
          "asset_id": "A24",
          "asset_class": "figure",
          "label": "图 fig2_autopsy.png（五模式完整率 + tier-1 体积）",
          "in_report_section": "## ④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 7816,
            "end_char": 7943,
            "start_line": 213,
            "end_line": 213,
            "quote": "| `fig2_autopsy.png` | 五种崩溃模式完整率（左）与 tier-1 工件体积（右） | 左图全 100 %；右图 `exception`/`memory_error`/`sigkill` 无核（Python 级/外部杀），标注说明 |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figure_metadata",
            "figure_name": "fig2_autopsy.png",
            "name_in_payload": true,
            "caption_in_payload": true,
            "png_bytes_in_payload": 0,
            "name_in_quote": true,
            "result": "unresolved",
            "detail": "payload 提供 name/caption；png_base64 为空且目录不在本工作树 → 位图在本环境不可得。同平台实测（docs/kf/wp-10647-01/platform_figure_probe.json）：本工单提交的非空 png 在 API 响应中同样返回 0 字节，且无图件下载端点 → 空字节是响应侧行为，不能据此推断作者未附图"
          },
          "note": "同上：仅元数据可解析，位图在本环境不可得"
        },
        {
          "asset_id": "A25",
          "asset_class": "figure",
          "label": "图 fig3_resume.png（断点位置 vs 位级一致性）",
          "in_report_section": "## ④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 7944,
            "end_char": 8011,
            "start_line": 214,
            "end_line": 214,
            "quote": "| `fig3_resume.png` | 断点位置 vs 位级一致性 | 所有断点落在 \"identical\" 水平线（3/3） |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figure_metadata",
            "figure_name": "fig3_resume.png",
            "name_in_payload": true,
            "caption_in_payload": true,
            "png_bytes_in_payload": 0,
            "name_in_quote": true,
            "result": "unresolved",
            "detail": "payload 提供 name/caption；png_base64 为空且目录不在本工作树 → 位图在本环境不可得。同平台实测（docs/kf/wp-10647-01/platform_figure_probe.json）：本工单提交的非空 png 在 API 响应中同样返回 0 字节，且无图件下载端点 → 空字节是响应侧行为，不能据此推断作者未附图"
          },
          "note": "同上：仅元数据可解析，位图在本环境不可得"
        },
        {
          "asset_id": "A26",
          "asset_class": "figure",
          "label": "图 fig4_ladder.png（内存利用率探测/阈值 + 状态占用阶梯）",
          "in_report_section": "## ④ 结果图",
          "locator": {
            "method": "char_span",
            "start_char": 8012,
            "end_char": 8093,
            "start_line": 215,
            "end_line": 215,
            "quote": "| `fig4_ladder.png` | 上：内存利用率探测与四级阈值；下：状态占用阶梯 | 每次跨阈值，占用阶梯下降，末端落到 graceful exit |",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "platform_figure_metadata",
            "figure_name": "fig4_ladder.png",
            "name_in_payload": true,
            "caption_in_payload": true,
            "png_bytes_in_payload": 0,
            "name_in_quote": true,
            "result": "unresolved",
            "detail": "payload 提供 name/caption；png_base64 为空且目录不在本工作树 → 位图在本环境不可得。同平台实测（docs/kf/wp-10647-01/platform_figure_probe.json）：本工单提交的非空 png 在 API 响应中同样返回 0 字节，且无图件下载端点 → 空字节是响应侧行为，不能据此推断作者未附图"
          },
          "note": "同上：仅元数据可解析，位图在本环境不可得"
        },
        {
          "asset_id": "A27",
          "asset_class": "environment_limitation",
          "label": "内核自发 core 采集不可用（容器 core_pattern 指向 systemd-coredump，无 systemd）",
          "in_report_section": "## ⑤ 注意点（踩坑、局限、适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 8733,
            "end_char": 8933,
            "start_line": 235,
            "end_line": 237,
            "quote": "* **内核 core_pattern 在本容器不可用**：`core_pattern` 是 `|/usr/lib/systemd/systemd-coredump`，\n  而容器无 systemd（`coredumpctl` 不可用）→ 内核自发 core 拿不到，本层用 ptrace+gdb 自取\n  （这一路由实测可用，见 §3.6）。若宿主有可用 `core_pattern`，两者可并存。",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "core_pattern_probe",
            "result": "absent",
            "probe": "cat /proc/sys/kernel/core_pattern + coredumpctl availability",
            "container_note": "本工作树容器，非报告作者的容器；只作可复现探针记录，不据此判定上游结论",
            "core_pattern": "|/usr/lib/systemd/systemd-coredump %P %u %g %s %t %c %h",
            "pipe_target": "/usr/lib/systemd/systemd-coredump",
            "pipe_target_exists": true,
            "coredumpctl": "/usr/bin/coredumpctl",
            "coredumpctl_version_rc": 0,
            "coredumpctl_stderr_head": [],
            "coredumpctl_functional": true,
            "result_note": "内核自发 core 路由不可用 = 上游声明；本容器探针仅记录现状"
          },
          "note": "上游明确记为“无基准项”而非“未测充数”；本工序在本容器复跑同一探针，不改写上游结论"
        },
        {
          "asset_id": "A28",
          "asset_class": "scope_limitation",
          "label": "适用范围限制：位级一致限同机同库，跨 ISA（loong64 vs x86）须改用 tools/repro_digest（ULP/12 位有效数字）",
          "in_report_section": "## ⑤ 注意点（踩坑、局限、适用范围）",
          "locator": {
            "method": "char_span",
            "start_char": 9044,
            "end_char": 9147,
            "start_line": 240,
            "end_line": 241,
            "quote": "* **位级一致限于同机同库**：跨 ISA（loong64 vs x86）浮点结果可能不同，届时须改用\n  `tools/repro_digest`（ULP/12 位有效数字）判据，而不是 sha256。",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "该限制是 A17/A18 位级判据的适用边界，登记以备下游抽取时携带"
        },
        {
          "asset_id": "A29",
          "asset_class": "measurement_table",
          "label": "§6 误差判定表（8 行，逐项显式回答“是否 < 3 %”）",
          "in_report_section": "## ⑥ 误差判定（逐项，显式回答\"是否 < 3 %\"）",
          "locator": {
            "method": "char_span",
            "start_char": 9560,
            "end_char": 10081,
            "start_line": 254,
            "end_line": 263,
            "quote": "| 关键量 | 基准 | 实测 | 相对误差 | < 3 % ? |\n|---|---|---|---|---|\n| 取证层开销（中位数） | 裸循环 CPU 时间 | −0.65 % | \\|0.65 %\\| | **是** |\n| 取证层开销（仪器自计） | 裸循环 CPU 时间 | +0.0889 % | 0.09 % | **是** |\n| 续跑末态一致性 | 不间断运行 sha256 | 位级相同（0 位差） | 0 % | **是** |\n| 断电/崩溃后检查点完整性 | 写入即自校验 | 40/40 载荷翻转检出、清单/缺数组/半成品全检出 | 0 % 漏检 | **是** |\n| 崩溃取证完整率 | 100 %（判据） | 5/5 模式 = 100 % | 0 % | **是** |\n| 阶梯末态可续 | 可加载且自校验 | 通过 | 0 % | **是** |\n| 崩溃判定分类正确率 | 5 种注入模式 + 11 条单元矩阵 | 5/5 与 11/11 | 0 % | **是** |\n| ELF 核可解析性 | `gdb exe core -ex bt` 成功 | 成功（13 帧） | — | **是** |",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "artifact_trace",
            "artifact": "runs/m9082/evidence.json",
            "present_in_worktree": false,
            "result": "resolved",
            "detail": "引文可定位（resolved）；数值复算需 runs/m9082/evidence.json，本工作树缺失 → 未复算"
          },
          "note": "误差栏全部为 0 %/0 位差型判据；本工序只登记不复核，且不把“是否<3%”标成 verified"
        },
        {
          "asset_id": "A30",
          "asset_class": "repro_command",
          "label": "一键复现命令块（pytest 四模块 + bench_m9082 重生成 evidence.json 与图）",
          "in_report_section": "## 复现",
          "locator": {
            "method": "char_span",
            "start_char": 10181,
            "end_char": 10449,
            "start_line": 272,
            "end_line": 276,
            "quote": "```bash\npython3 -m pytest tests/test_longrun_forensics.py tests/test_longrun_checkpoint_resume.py \\\n                 tests/test_longrun_ladder.py tests/test_longrun_overhead.py -q\npython3 -m tools.longrun.bench_m9082 --outdir runs/m9082     # 重生成 evidence.json + 图\n```",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "命令指向 TensorPlatform 仓；本工作树无法执行（仓内无 tools.longrun）"
        },
        {
          "asset_id": "A31",
          "asset_class": "code_snippet",
          "label": "单次使用示例（supervise.supervise(...) 返回 failure_mode/core.status/bundle_completeness）",
          "in_report_section": "## 复现",
          "locator": {
            "method": "char_span",
            "start_char": 10458,
            "end_char": 10814,
            "start_line": 280,
            "end_line": 286,
            "quote": "```python\nfrom tools.longrun import supervise\nrep = supervise.supervise({\"job\": {\"grid\": 256}, \"steps\": 200, \"checkpoint_every\": 20,\n                           \"crash\": {\"at_step\": 120, \"mode\": \"segv\"}},\n                          workdir=\"/tmp/run1\", job_id=\"job1\")\nrep[\"failure_mode\"], rep[\"core\"][\"status\"], rep[\"bundle_completeness\"][\"completeness\"]\n```",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "char_span_in_source_markdown",
            "result": "resolved"
          },
          "note": "API 契约样例；import 目标模块不在本工作树，未执行"
        }
      ],
      "claims": [],
      "claims_note": "按工作包契约 objective.classify_report_type=false 且 notes 允许 claims 为空数组：本工序只登记资产定位，不做抽取，不生成未经抽取的“知识”条目；claim 抽取由下游工序负责。",
      "integrity": {
        "quote_uniqueness": "每条引文均为源 markdown 的唯一子串（本脚本 slice 后 md.count(quote)==1 断言；scripts/kf_verify_10647.py 独立重算）",
        "hash_recomputed_locally": true,
        "hash_matches_contract": true,
        "claims_empty_by_contract": true,
        "no_verified_marker": true,
        "verified_status_objects": 0,
        "word_verified_disclaimers": [
          {
            "asset_id": "A15",
            "field": "note",
            "snippet": "上传上游自报 100 %；本工序不复核，也不标 verified"
          },
          {
            "asset_id": "A29",
            "field": "note",
            "snippet": "误差栏全部为 0 %/0 位差型判据；本工序只登记不复核，且不把“是否<3%”标成 verified"
          }
        ]
      }
    }
  },
  "claims": []
}
```
