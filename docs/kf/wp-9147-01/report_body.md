# ①本工序做了什么

本工作包 `wp-9147-01`（task_type=`01-asset-registration`，lane C）只做一件事：**为 report_id=9147 登记源资产**。
不做抽取、不做分类（契约 `objective.register_assets=true` / `classify_report_type=false`），不把任何结论标为
verified（verification 由平台门计算）。

具体产出：

1. 取回 `tensor://reports/9147` 的 `markdown` 字段，**逐字节**落盘并重算 sha256；
2. 用**程序化锚点**（行搜索）在 markdown 内切出 12 个资产的定位窗口，引文一律由切片产生（零手抄）；
3. 每个资产给出 `resolution`：`resolved_in_source`（本体在 markdown 内）/ `referenced_unresolved`
   （markdown 内只有路径文本，payload 不在报告记录里）/ `declared_absent`（声明了槽位但记录无载荷）；
4. 输出 `asset_manifest.json` 与配套定位/校验工件，并把结果装进 `kf_result.v1` 信封。

# ②怎么做的（步骤/工具/关键设置）

1. **取数**：`GET {TENSOR_API_BASE}/tensor/reports/9147`（Bearer token 由 `/auth/login` 用
   `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS` 换取，脚本不硬编码凭据）。只读、只碰 9147，不触碰任何其它
   report_id。落地 `runs/wp-9147-01/report_9147.{json,md,meta.json}`，写盘用 `write_bytes` 避免换行翻译。
2. **哈希核对**：`hashlib.sha256(markdown.encode("utf-8"))`，与契约 `source_hash` 逐字符比对；
   同时核对 `title`/`scenario_key`/`chars` 三件套与契约一致。
3. **资产登记**：资产表在代码里只写**锚点子串**与相对行窗（`scripts/kf_wp9147_01_register.py::ASSETS`），
   引文由 `"\n".join(lines[start:end+1])` 在运行时切出，再回写 `start_char/end_char`（用 `md.find()` 实测偏移，
   不做累加推算），并断言：引文是 markdown 的子串、出现次数 = 1、`md[start:end] == quote`。
   任一断言失败脚本 `SystemExit`，不产生半成品清单。
4. **分辨率判定**：依据可机械核验的事实——引文命中 → `resolved_in_source`；只有路径文本 → `referenced_unresolved`；
   平台记录 `figures == []` → `declared_absent`。**不猜测**仓库内的文件是否存在（本工作树不是生产仓，
   去读生产仓既越界也无法作为本报告的定位证据）。
5. **信封与渲染**：`kf_result.json` 按 `schemas/kf_result.v1.schema.json` 用 `jsonschema.validate` 校验；
   报告正文由模板 + 运行时注入的表格/JSON 渲染（KF_RESULT_JSON / EVIDENCE_TABLE / IDENTITY_TABLE / ACCEPTANCE_TABLE 四个占位符），正文数字全部来自工件，
   非手写。
6. **自检**：`scripts/kf_wp9147_01_check.py` 逐条复算 6 项 acceptance，输出 `acceptance_check.json`。

# ③产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9147-01/asset_manifest.json` | **契约要求的唯一输出**：`outputs["asset_manifest.json"]` 的同一对象；12 个资产 + 定位 + 分辨率 + 计数 + 完整性声明 |
| `docs/kf/wp-9147-01/locator_check.json` | 每个资产的 `[start_char,end_char)` 切回原文的逐条比对（`slice_matches`/`occurrences`），全部 true/1 |
| `docs/kf/wp-9147-01/kf_result.json` | `kf_result.v1` 信封（package_id/task_type/report_id/provenance/outputs），schema 通过 |
| `docs/kf/wp-9147-01/acceptance_check.json` | 6 项 acceptance 的逐条复算结果（本报告 ⑥ 节的机器来源） |
| `docs/kf/wp-9147-01/asset_manifest.wp-9147-01.schema.json` | 本包使用的 asset_manifest 形状钉死版（由仓内 `schemas/asset_manifest.v1.schema.json` 派生，把 const 换成 9147 的值），让 `schema_pass` 可复算而非自称 |
| `docs/kf/wp-9147-01/source.md` / `sha256.txt` | markdown 逐字节副本 + 重算摘要（供第三方复核定位） |
| `docs/kf/wp-9147-01/figures/asset_locator_map.png` | 资产定位覆盖图（横轴=字符偏移，每行一个资产），由图脚本从 manifest 程序化生成 |
| `docs/kf_result_wp-9147-01.md` | 本报告（含唯一一个 fenced json 结果块） |

`runs/wp-9147-01/` 保留取数现场（原始 payload / markdown / meta），`docs/` 下是对外提交的定稿副本。

# ④证据定位表（字段 → 原文逐字片段）

@@IDENTITY_TABLE@@

@@EVIDENCE_TABLE@@

### 结果图：资产定位覆盖图

![asset locator map](kf/wp-9147-01/figures/asset_locator_map.png)

横轴=markdown 字符偏移（0…`chars`），每行一个资产，条形长度=定位窗口宽度 `end_char-start_char`；
颜色=分辨率（绿 resolved_in_source / 橙 referenced_unresolved / 紫 declared_absent）。图由
`scripts/kf_wp9147_01_figure.py` 直接读 `asset_manifest.json` 渲染，无手填数字；可核对：
绿色条形全部落在文档内且互不重叠，橙色/紫色条形很窄（仅路径文本 / 附件槽声明）。

注：表中 A01 的引文即整篇 markdown，因过长以 `…` 省略中段（首尾仍逐字）；完整引文与偏移见
`docs/kf/wp-9147-01/asset_manifest.json` 与 `locator_check.json`，平台可按偏移独立切片复核。

`in_report_section` 的行号均指 `docs/kf/wp-9147-01/source.md` 的 1-based 行号；字符偏移指 UTF-8
解码后的 Python 字符串下标（`chars` 亦按字符计）。

# ⑤注意点与局限

1. **只登记不判断**：A04 的 6 条判据（`< 0.001% error`、`47/47 = 100%` 等）与 A05 的 5 个数值
   （2.3564 / 2.0068 / 1.174 / B / dd 边界）都是**报告自陈**，本工序没有复算，也没有把它们标成 verified。
   报告自己在 A06 里把 Required EEXI/CII 系数标为 `WITHHELD`——这个不确定度被原样保留，没有被"登记"动作抹平。
2. **5 个路径资产未解析**（A07–A11）：`green_compliance.py`、测试文件、`compliance_report.json`、
   `fig_eexi_cii_analysis.png`、`P77_N03_green_compliance.md` 的 payload 都不在报告记录里，只在 markdown
   以路径文本出现。本工序**没有**去生产仓验证它们是否存在/是否与 47 tests 自陈一致——这既越出"只碰 9147"的边界，
   也无法作为本报告记录内的定位证据。因此它们一律 `referenced_unresolved`，不是"已验证存在"。
3. **图件缺口**（A12）：`GET /api/v1/tensor/reports/9147` 的 `figures` 是空数组，而 markdown 的 Files 节
   声明了 1 张 PNG。这是**记录级缺附件**，登记为 `declared_absent`，不当成资产存在。
4. **claims 为空是合法结果**：契约明示允许空数组。为了不制造指标，本包不生成任何 claim；
   `all_claims_have_evidence_or_explicit_unresolved_status` 因此是**空真**（vacuous true），
   这一点在 ⑥ 里如实标注，不当作"证据完备性已证明"。
5. **哈希相等 ≠ 内容为真**：sha256 命中只证明"我读到的字节 = 契约声明的字节"，与报告结论是否正确无关。
6. **字符数口径**：契约 `chars: 1649` 与本包 `chars` 一致；`bytes_utf8 = 1694`（中文与 ✅/₂ 等字符导致
   字节数大于字符数）。若平台用字节口径重算，请以本包 `bytes_utf8` 为准。
7. **时区/时间**：`provenance.emitted_at` 取自首次运行的 UTC 时间戳，重跑会复用该值以保证工件字节可复现。

# ⑥自检：逐条对照 acceptance

@@ACCEPTANCE_TABLE@@

另附交付不变量测试 `tests/test_kf_wp9147_01.py`（8 个用例，全部通过；离线运行，不依赖凭据）：
它把上面 6 项重新以**断言**的形式钉住（引文按声明偏移切回、行窗自洽、计数与资产一致、
报告内 fenced json 块与 `kf_result.json` 逐值相等、无任何 claim 被标 verified）。

判定口径：`valid_json`/`schema_pass`/`no_duplicate_ids` 是纯机械检查；`source_locator_resolvable`
按"引文可在 markdown 内以声明偏移逐字切回且唯一"判定；`source_hash_matches` 按 sha256 重算判定；
第 6 项因 `claims: []` 而**空真成立**（已在 ⑤-4 声明，不夸大）。

# 复跑

```
# 一键复跑（工作树根执行；需要 TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE）
bash scripts/kf_wp9147_01_run_all.sh
# 分步：
python3 scripts/kf_wp9147_01_fetch.py      # 取数 + sha256 核对（只读 report 9147）
python3 scripts/kf_wp9147_01_register.py   # 资产登记 -> docs/kf/wp-9147-01/asset_manifest.json
python3 scripts/kf_wp9147_01_result.py      # 信封 + schema 校验 + 渲染本报告
python3 scripts/kf_wp9147_01_check.py       # 6 项 acceptance 复算 -> acceptance_check.json
python3 scripts/kf_wp9147_01_figure.py      # 定位覆盖图
python3 -m pytest tests/test_kf_wp9147_01.py -q   # 交付不变量测试（8 passed，离线、无需凭据）
```

# 结果信封（全文唯一的 fenced json 代码块）

@@KF_RESULT_JSON@@