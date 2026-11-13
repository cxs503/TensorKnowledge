# KF-RESULT wp-11930-01

**report_id** 11930 · **task_type** 01-asset-registration · **source** `tensor://reports/11930` · **sha256** `5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325`

## ① 本工序做了什么

对 `report_id=11930`（《BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）》）执行 **01-asset-registration**：确认源资产（markdown）与其字节哈希，枚举报告中可定位的文件类工件（图/脚本/模块/测试/数据），逐个给出字符级 locator 与解析状态。**不做抽取、不做分类、不生成 claim**（`objective.classify_report_type=false`，`no_forced_claim_generation`）。

产出 `asset_manifest.json`：14 个资产，其中 resolved_in_source 6、referenced_unresolved 7、declared_absent 1；`claims` 为空数组（本工序按契约合法）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文（零手抄）**：`GET /api/v1/tensor/reports/11930`（Bearer 登录 token），把 `markdown` 字段**按原字节**落盘为 `artifacts/wp-11930-01/source_11930.md`，本地复算 sha256 → `5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325`，与契约 `source_hash` 逐字一致；chars = 13121，bytes_utf8 = 22324。脚本：`scripts/kf_wp11930_fetch.py`。
2. **枚举工件**：路径引用（`src/`、`scripts/`、`tests/`、`runs/`、`artifacts/`、`figures/`）与图链接由脚本内固定的候选清单对原文做**逐字查找**（`md.find`），找不到即报错退出——不存在凭记忆补写。
3. **locator**：以命中的 token 为中心向两侧扩张到软分隔符（`·`、`、`、`|`、换行），得到"最小自描述片段"；若片段非唯一则退化为整行、再多给一行上下文。记录 `start_char/end_char/start_line/end_line/quote/unique`，并要求 `md[start:end] == quote` 且 `md.count(quote) == 1`（all 14/14 locator quotes occur exactly once in the source markdown）。
4. **解析状态判定**：
   - 6 张图走平台图端点 `GET /api/v1/tensor/reports/11930/figures/<name>`（HTTP 200 / image/png），记录 PNG 字节数与 sha256，判 `resolved_in_source`；
   - 7 个代码/数据路径查本工作树（TensorKnowledge 检出）是否存在 → 均不存在，判 `referenced_unresolved`，并写明"属 TensorDEM 仓、需回 source repo 解析"；
   - 报告中显式自述缺失的原始 JSONL 记为 `declared_absent`，只登记引文与原因，不补造内容。
5. **自校验**：`pytest tests/test_wp11930_asset_manifest.py`（10 项）覆盖 acceptance 每一条：JSON 合法、两套 schema 校验、哈希一致、每个 locator 可在原文逐字解析且唯一、id 无重复、counts 自洽、claims 为空但显式声明、未解析资产确有理由且本地确实不存在、6 图带平台哈希。

## ③ 产出物清单（文件 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/wp-11930-01/asset_manifest.json` | 交付主体：14 资产 + 逐条 locator + counts + integrity 块 |
| `artifacts/wp-11930-01/kf_result.wp-11930-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]） |
| `artifacts/wp-11930-01/source_11930.md` | 平台 markdown 原字节（sha256 已核） |
| `artifacts/wp-11930-01/source_meta.json` | 源记录元数据（title/scenario_key/chars/bytes/figures/tags） |
| `artifacts/wp-11930-01/evidence_table.md` | ④ 证据定位表（程序化生成） |
| `artifacts/wp-11930-01/fig_asset_registration_summary.png` | 本工序结果图（资产分类×解析状态；locator 位置/长度） |
| `schemas/asset_manifest.v1.wp-11930-01.schema.json` | 为本包钉死的 manifest schema（派生自 `asset_manifest.v1`） |
| `scripts/kf_wp11930_fetch.py` / `kf_wp11930_register.py` / `kf_wp11930_figure.py` / `kf_wp11930_publish.py` | 取原文 / 生成 manifest / 出图与证据表 / 发报告 |
| `tests/test_wp11930_asset_manifest.py` | 10 项 acceptance 校验 |

## ④ 证据定位表（字段 / 资产 → 原文引文片段）

| asset_id | class | section | resolution | line(s) | quote (verbatim, unique) |
|---|---|---|---|---|---|
| A01 | module | header | referenced_unresolved | 4–4 | “**新增模块** `src/tensordem/bpm_calibration_feasibility.py`” |
| A02 | script | header | referenced_unresolved | 4–4 | “**战役脚本** `scripts/p270w2c_n08_feasibility.py`（sample/analyze）” |
| A03 | script | header | referenced_unresolved | 4–4 | “**图/报告渲染** `scripts/p270w2c_n08_figures.py`” |
| A04 | script | header | referenced_unresolved | 4–4 | “`scripts/p270w2c_n08_report.py`” |
| A05 | test | §0 | referenced_unresolved | 18–18 | “`tests/test_bpm_calibration_feasibility.py`（42 项，见 §6）” |
| A06 | data | header | referenced_unresolved | 5–5 | “**原始数据** `runs/p270w2c_n08/records.jsonl`（逐任务记录）” |
| A07 | data | header | referenced_unresolved | 5–5 | “**判据数字** `artifacts/p270w2c_n08/report.json`（本报告的唯一数字来源）” |
| A08 | figure | §3.7 | resolved_in_source | 184–184 | “![response surface](figures/p270w2c_n08/fig_response_surface.png)” |
| A09 | figure | §3.7 | resolved_in_source | 188–188 | “![identifiability](figures/p270w2c_n08/fig_jacobian.png)” |
| A10 | figure | §3.7 | resolved_in_source | 192–192 | “![pareto](figures/p270w2c_n08/fig_pareto.png)” |
| A11 | figure | §3.7 | resolved_in_source | 196–196 | “![size effect](figures/p270w2c_n08/fig_size_effect.png)” |
| A12 | figure | §3.7 | resolved_in_source | 200–200 | “![brazilian](figures/p270w2c_n08/fig_brazilian.png)” |
| A13 | figure | §3.7 | resolved_in_source | 204–204 | “![ucs](figures/p270w2c_n08/fig_ucs.png)” |
| A14 | data | §4 · 注意点 条 1b | declared_absent | 211–211 | “原始 JSONL 因磁盘配额已清理” |

Source metadata: title=BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）；scenario_key=p270w2c-n08-bpm-calibration-feasibility；chars=13121；bytes_utf8=22324。

Platform figure index (6): fig_response_surface.png, fig_jacobian.png, fig_pareto.png, fig_size_effect.png, fig_brazilian.png, fig_ucs.png

## ⑤ 注意点与局限

1. **只做登记，不做抽取**：本包不含任何 claim，`claims: []` 是设计结果而非遗漏；下游 03 抽取包才消费这些 locator。
2. **7 个代码/数据工件不可在本仓解析**：它们属 TensorDEM（节点 P270W2C-N08 / 任务 m9756），TensorKnowledge 检出内不存在，报告也未内联其内容。因此判 `referenced_unresolved` 而不是"已核验存在"；下游若需内容，必须回 source repo 取同一 commit。
3. **图的解析只到字节级**：6 张 PNG 可从平台端点取回（字节数/sha256 已记录），但本包**不解读图像像素**，图与表格数字是否一致不在本工序职责内（那是 04/05 审计包的活）。
4. **`declared_absent` 依赖报告自述**：原始 JSONL 因磁盘配额清理是报告正文的声明，本包无法独立验证其确实不存在于历史存储，只如实转记并附引文。
5. **一个 report 边界内操作**：全程只读写 report_id=11930，未触碰其它报告；未改动上游产物，未把任何结论标 verified。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
| valid_json | ✅ | `json.loads` 两个产物均通过（test_artifacts_are_valid_json） |
| schema_pass | ✅ | `schemas/asset_manifest.v1.wp-11930-01.schema.json` 与 `schemas/kf_result.v1.schema.json` 双通过（test_manifest_schema_pass / test_envelope_schema_pass） |
| source_locator_resolvable | ✅ | all 14/14 locator quotes occur exactly once in the source markdown；`md[start:end]==quote` 且行号一致（test_every_locator_resolves_verbatim） |
| source_hash_matches | ✅ | 本地复算 `sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325` == 契约值（test_source_hash_matches_contract） |
| no_duplicate_ids | ✅ | asset_id 与 path_in_report 均无重复（test_no_duplicate_ids） |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅（空集） | claims=[]，且 integrity 中显式声明 `no_claims_by_design`；每个未解析资产均带 reason（test_claims_empty_is_explicit_not_fabricated） |

自检命令：`python3 -m pytest tests/test_wp11930_asset_manifest.py -q` → **10 passed**。无失败项，故无 honest-FAIL。

## 误差判定

本包是**登记类**工序，无物理量、无实验基准，故不存在"关键量 vs 基准误差"。唯一可量化的正确性判据是**逐字可定位性与哈希一致**：locator 唯一率 14/14（100%），源哈希 1/1 一致，acceptance 6/6 通过（10 项 pytest 全绿）。显式回答"是否 < 3%"：**不适用**（无基准量可比），代之以"定位失败数 = 0 / 哈希不符数 = 0"。

repro_cmd：

```bash
cd <worktree> && python3 scripts/kf_wp11930_fetch.py && python3 scripts/kf_wp11930_register.py \
  && python3 scripts/kf_wp11930_figure.py && python3 -m pytest tests/test_wp11930_asset_manifest.py -q
```


## 结果信封（唯一 json 块，交付信道）

```json
{
  "package_id": "wp-11930-01",
  "task_type": "01-asset-registration",
  "report_id": "11930",
  "provenance": {
    "source_hash": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
    "source_field": "markdown",
    "producer": "agent/m15731 · scripts/kf_wp11930_register.py",
    "emitted_at": "2026-11-12T02:20:50+00:00",
    "notes": "markdown fetched via GET /api/v1/tensor/reports/11930; hash recomputed from bytes on disk"
  },
  "outputs": {
    "asset_manifest.json": {
      "schema": "asset_manifest.v1",
      "package_id": "wp-11930-01",
      "task_type": "01-asset-registration",
      "report_id": "11930",
      "source": {
        "uri": "tensor://reports/11930",
        "field": "markdown",
        "hash_alg": "sha256",
        "hash": "5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
        "chars": 13121,
        "bytes_utf8": 22324,
        "title": "BPM 微观参数三目标联合标定的可行性判定与可辨识性审计（P270W2C-N08）",
        "scenario_key": "p270w2c-n08-bpm-calibration-feasibility",
        "platform_figures": [
          {
            "name": "fig_response_surface.png",
            "caption": "响应面切片：每列一个微观参数（单位立方体坐标），每行一个宏观响应（UCS / σc/σt / Weibull m）；绿色带为验收目标带。"
          },
          {
            "name": "fig_jacobian.png",
            "caption": "可辨识性审计：量纲一化 Jacobian dlog10(y)/du、参数相关矩阵（JᵀJ 归一化）与 Brun collinearity index。"
          },
          {
            "name": "fig_pareto.png",
            "caption": "代理响应面上的 NSGA-II 种群与 Pareto 前沿（三目标两两投影）；越界量 0 表示目标满足。"
          },
          {
            "name": "fig_size_effect.png",
            "caption": "Weibull 尺寸效应：参考 θ 的五厚度族与幂律拟合（虚线为留出厚度），右图为留出厚度外推误差。"
          },
          {
            "name": "fig_brazilian.png",
            "caption": "巴西圆盘中心主应力比 vs 应力平均区半径（三种点阵分辨率）与 Hondros −3.0 容差带；右图为比值读数历史。"
          },
          {
            "name": "fig_ucs.png",
            "caption": "参考 θ 的单轴压缩应力–应变迹（hold 末读数）与 AC6 负控 200 组随机 θ 的 UCS 分布。"
          }
        ],
        "platform_tags": [
          "DEM",
          "BPM",
          "calibration",
          "identifiability",
          "Weibull",
          "Brazilian-test",
          "NSGA-II",
          "TensorDEM",
          "P270W2C-N08"
        ]
      },
      "counts": {
        "assets": 14,
        "by_class": {
          "module": 1,
          "script": 3,
          "test": 1,
          "data": 3,
          "figure": 6
        },
        "by_resolution": {
          "referenced_unresolved": 7,
          "resolved_in_source": 6,
          "declared_absent": 1
        },
        "resolved_in_source": 6,
        "referenced_unresolved": 7,
        "declared_absent": 1
      },
      "assets": [
        {
          "asset_id": "A01",
          "asset_class": "module",
          "label": "新增模块（本节点实现）",
          "path_in_report": "src/tensordem/bpm_calibration_feasibility.py",
          "in_report_section": "header",
          "locator": {
            "method": "char_span",
            "seed_span": [
              114,
              158
            ],
            "start_char": 104,
            "end_char": 159,
            "start_line": 4,
            "end_line": 4,
            "quote": "**新增模块** `src/tensordem/bpm_calibration_feasibility.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "本工作树（TensorKnowledge 检出）内 os.path.exists(path)",
            "result": "unresolved"
          },
          "note": "报告声明该工件属于 TensorDEM 仓（节点 P270W2C-N08 / 任务 m9756）；TensorKnowledge 检出内不存在，也未随报告携带字节，故只登记引用不复制，解析需回 source repo。"
        },
        {
          "asset_id": "A02",
          "asset_class": "script",
          "label": "战役脚本 sample/analyze",
          "path_in_report": "scripts/p270w2c_n08_feasibility.py",
          "in_report_section": "header",
          "locator": {
            "method": "char_span",
            "seed_span": [
              172,
              206
            ],
            "start_char": 162,
            "end_char": 223,
            "start_line": 4,
            "end_line": 4,
            "quote": "**战役脚本** `scripts/p270w2c_n08_feasibility.py`（sample/analyze）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "本工作树（TensorKnowledge 检出）内 os.path.exists(path)",
            "result": "unresolved"
          },
          "note": "报告声明该工件属于 TensorDEM 仓（节点 P270W2C-N08 / 任务 m9756）；TensorKnowledge 检出内不存在，也未随报告携带字节，故只登记引用不复制，解析需回 source repo。"
        },
        {
          "asset_id": "A03",
          "asset_class": "script",
          "label": "图渲染脚本",
          "path_in_report": "scripts/p270w2c_n08_figures.py",
          "in_report_section": "header",
          "locator": {
            "method": "char_span",
            "seed_span": [
              237,
              267
            ],
            "start_char": 225,
            "end_char": 268,
            "start_line": 4,
            "end_line": 4,
            "quote": "**图/报告渲染** `scripts/p270w2c_n08_figures.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "本工作树（TensorKnowledge 检出）内 os.path.exists(path)",
            "result": "unresolved"
          },
          "note": "报告声明该工件属于 TensorDEM 仓（节点 P270W2C-N08 / 任务 m9756）；TensorKnowledge 检出内不存在，也未随报告携带字节，故只登记引用不复制，解析需回 source repo。"
        },
        {
          "asset_id": "A04",
          "asset_class": "script",
          "label": "报告渲染脚本",
          "path_in_report": "scripts/p270w2c_n08_report.py",
          "in_report_section": "header",
          "locator": {
            "method": "char_span",
            "seed_span": [
              270,
              299
            ],
            "start_char": 269,
            "end_char": 300,
            "start_line": 4,
            "end_line": 4,
            "quote": "`scripts/p270w2c_n08_report.py`",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "本工作树（TensorKnowledge 检出）内 os.path.exists(path)",
            "result": "unresolved"
          },
          "note": "报告声明该工件属于 TensorDEM 仓（节点 P270W2C-N08 / 任务 m9756）；TensorKnowledge 检出内不存在，也未随报告携带字节，故只登记引用不复制，解析需回 source repo。"
        },
        {
          "asset_id": "A05",
          "asset_class": "test",
          "label": "AC8 pytest 套件（42 项）",
          "path_in_report": "tests/test_bpm_calibration_feasibility.py",
          "in_report_section": "§0",
          "locator": {
            "method": "char_span",
            "seed_span": [
              1470,
              1511
            ],
            "start_char": 1469,
            "end_char": 1523,
            "start_line": 18,
            "end_line": 18,
            "quote": "`tests/test_bpm_calibration_feasibility.py`（42 项，见 §6）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "本工作树（TensorKnowledge 检出）内 os.path.exists(path)",
            "result": "unresolved"
          },
          "note": "报告声明该工件属于 TensorDEM 仓（节点 P270W2C-N08 / 任务 m9756）；TensorKnowledge 检出内不存在，也未随报告携带字节，故只登记引用不复制，解析需回 source repo。"
        },
        {
          "asset_id": "A06",
          "asset_class": "data",
          "label": "逐任务原始记录（审计链第一层）",
          "path_in_report": "runs/p270w2c_n08/records.jsonl",
          "in_report_section": "header",
          "locator": {
            "method": "char_span",
            "seed_span": [
              313,
              343
            ],
            "start_char": 303,
            "end_char": 351,
            "start_line": 5,
            "end_line": 5,
            "quote": "**原始数据** `runs/p270w2c_n08/records.jsonl`（逐任务记录）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "本工作树（TensorKnowledge 检出）内 os.path.exists(path)",
            "result": "unresolved"
          },
          "note": "报告声明该工件属于 TensorDEM 仓（节点 P270W2C-N08 / 任务 m9756）；TensorKnowledge 检出内不存在，也未随报告携带字节，故只登记引用不复制，解析需回 source repo。"
        },
        {
          "asset_id": "A07",
          "asset_class": "data",
          "label": "判据/数字来源（审计链第二层）",
          "path_in_report": "artifacts/p270w2c_n08/report.json",
          "in_report_section": "header",
          "locator": {
            "method": "char_span",
            "seed_span": [
              363,
              396
            ],
            "start_char": 353,
            "end_char": 409,
            "start_line": 5,
            "end_line": 5,
            "quote": "**判据数字** `artifacts/p270w2c_n08/report.json`（本报告的唯一数字来源）",
            "unique": true
          },
          "resolution": "referenced_unresolved",
          "resolution_check": {
            "check": "本工作树（TensorKnowledge 检出）内 os.path.exists(path)",
            "result": "unresolved"
          },
          "note": "报告声明该工件属于 TensorDEM 仓（节点 P270W2C-N08 / 任务 m9756）；TensorKnowledge 检出内不存在，也未随报告携带字节，故只登记引用不复制，解析需回 source repo。"
        },
        {
          "asset_id": "A08",
          "asset_class": "figure",
          "label": "图 1 响应面切片",
          "path_in_report": "figures/p270w2c_n08/fig_response_surface.png",
          "in_report_section": "§3.7",
          "locator": {
            "method": "char_span",
            "seed_span": [
              8885,
              8929
            ],
            "start_char": 8865,
            "end_char": 8930,
            "start_line": 184,
            "end_line": 184,
            "quote": "![response surface](figures/p270w2c_n08/fig_response_surface.png)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /api/v1/tensor/reports/11930/figures/fig_response_surface.png (HTTP 200, image/png)",
            "result": "resolved"
          },
          "note": "平台报告记录 figures[] 含该文件名与逐字 caption；PNG 字节可取回，bytes_utf8=101650，sha256=51110cf7696adcee081421d2a92605a7cce80808ca294b7901120c4cc4756eec（本地复算，供下游二次比对）。",
          "platform_bytes": 101650,
          "platform_sha256": "51110cf7696adcee081421d2a92605a7cce80808ca294b7901120c4cc4756eec"
        },
        {
          "asset_id": "A09",
          "asset_class": "figure",
          "label": "图 2 可辨识性审计",
          "path_in_report": "figures/p270w2c_n08/fig_jacobian.png",
          "in_report_section": "§3.7",
          "locator": {
            "method": "char_span",
            "seed_span": [
              9062,
              9098
            ],
            "start_char": 9043,
            "end_char": 9099,
            "start_line": 188,
            "end_line": 188,
            "quote": "![identifiability](figures/p270w2c_n08/fig_jacobian.png)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /api/v1/tensor/reports/11930/figures/fig_jacobian.png (HTTP 200, image/png)",
            "result": "resolved"
          },
          "note": "平台报告记录 figures[] 含该文件名与逐字 caption；PNG 字节可取回，bytes_utf8=98897，sha256=412e3b536a4f35bdf37b52254700e12dcf766e51e3efdb497489481efcb97f28（本地复算，供下游二次比对）。",
          "platform_bytes": 98897,
          "platform_sha256": "412e3b536a4f35bdf37b52254700e12dcf766e51e3efdb497489481efcb97f28"
        },
        {
          "asset_id": "A10",
          "asset_class": "figure",
          "label": "图 3 NSGA-II 种群与 Pareto 前沿",
          "path_in_report": "figures/p270w2c_n08/fig_pareto.png",
          "in_report_section": "§3.7",
          "locator": {
            "method": "char_span",
            "seed_span": [
              9184,
              9218
            ],
            "start_char": 9174,
            "end_char": 9219,
            "start_line": 192,
            "end_line": 192,
            "quote": "![pareto](figures/p270w2c_n08/fig_pareto.png)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /api/v1/tensor/reports/11930/figures/fig_pareto.png (HTTP 200, image/png)",
            "result": "resolved"
          },
          "note": "平台报告记录 figures[] 含该文件名与逐字 caption；PNG 字节可取回，bytes_utf8=72532，sha256=8fe9f1a288cfa41ab23b1afbf52019d25b4088394977461772648efa173a247c（本地复算，供下游二次比对）。",
          "platform_bytes": 72532,
          "platform_sha256": "8fe9f1a288cfa41ab23b1afbf52019d25b4088394977461772648efa173a247c"
        },
        {
          "asset_id": "A11",
          "asset_class": "figure",
          "label": "图 4 Weibull 尺寸效应",
          "path_in_report": "figures/p270w2c_n08/fig_size_effect.png",
          "in_report_section": "§3.7",
          "locator": {
            "method": "char_span",
            "seed_span": [
              9339,
              9378
            ],
            "start_char": 9324,
            "end_char": 9379,
            "start_line": 196,
            "end_line": 196,
            "quote": "![size effect](figures/p270w2c_n08/fig_size_effect.png)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /api/v1/tensor/reports/11930/figures/fig_size_effect.png (HTTP 200, image/png)",
            "result": "resolved"
          },
          "note": "平台报告记录 figures[] 含该文件名与逐字 caption；PNG 字节可取回，bytes_utf8=74350，sha256=cc650deaa8c0878edeb662e262b1edd719d1aa18e8020908f58cb4ccf32dc743（本地复算，供下游二次比对）。",
          "platform_bytes": 74350,
          "platform_sha256": "cc650deaa8c0878edeb662e262b1edd719d1aa18e8020908f58cb4ccf32dc743"
        },
        {
          "asset_id": "A12",
          "asset_class": "figure",
          "label": "图 5 巴西圆盘中心主应力比",
          "path_in_report": "figures/p270w2c_n08/fig_brazilian.png",
          "in_report_section": "§3.7",
          "locator": {
            "method": "char_span",
            "seed_span": [
              9450,
              9487
            ],
            "start_char": 9437,
            "end_char": 9488,
            "start_line": 200,
            "end_line": 200,
            "quote": "![brazilian](figures/p270w2c_n08/fig_brazilian.png)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /api/v1/tensor/reports/11930/figures/fig_brazilian.png (HTTP 200, image/png)",
            "result": "resolved"
          },
          "note": "平台报告记录 figures[] 含该文件名与逐字 caption；PNG 字节可取回，bytes_utf8=100699，sha256=52c4b300d8668a5b3c2588b2d0aefdd15de10606cb6a0893e3bb7505e90296f8（本地复算，供下游二次比对）。",
          "platform_bytes": 100699,
          "platform_sha256": "52c4b300d8668a5b3c2588b2d0aefdd15de10606cb6a0893e3bb7505e90296f8"
        },
        {
          "asset_id": "A13",
          "asset_class": "figure",
          "label": "图 6 UCS 应力–应变迹与负控分布",
          "path_in_report": "figures/p270w2c_n08/fig_ucs.png",
          "in_report_section": "§3.7",
          "locator": {
            "method": "char_span",
            "seed_span": [
              9576,
              9607
            ],
            "start_char": 9569,
            "end_char": 9608,
            "start_line": 204,
            "end_line": 204,
            "quote": "![ucs](figures/p270w2c_n08/fig_ucs.png)",
            "unique": true
          },
          "resolution": "resolved_in_source",
          "resolution_check": {
            "check": "GET /api/v1/tensor/reports/11930/figures/fig_ucs.png (HTTP 200, image/png)",
            "result": "resolved"
          },
          "note": "平台报告记录 figures[] 含该文件名与逐字 caption；PNG 字节可取回，bytes_utf8=51010，sha256=a3f41eb663ea84ad0234d73a5c7c81613efc19a288eb4b6da11f5780e70fafd6（本地复算，供下游二次比对）。",
          "platform_bytes": 51010,
          "platform_sha256": "a3f41eb663ea84ad0234d73a5c7c81613efc19a288eb4b6da11f5780e70fafd6"
        },
        {
          "asset_id": "A14",
          "asset_class": "data",
          "label": "voided-campaign raw JSONL",
          "path_in_report": "n/a (declared absent)",
          "in_report_section": "§4 · 注意点 条 1b",
          "locator": {
            "method": "char_span",
            "seed_span": [
              10316,
              10333
            ],
            "start_char": 10316,
            "end_char": 10333,
            "start_line": 211,
            "end_line": 211,
            "quote": "原始 JSONL 因磁盘配额已清理",
            "unique": true
          },
          "resolution": "declared_absent",
          "resolution_check": {
            "check": "报告正文显式声明缺失（逐字引文）",
            "result": "absent"
          },
          "note": "报告自述因磁盘配额已清理；不作补造、不推断内容。"
        }
      ],
      "claims": [],
      "integrity": {
        "quote_uniqueness": "all 14/14 locator quotes occur exactly once in the source markdown",
        "all_quotes_unique": true,
        "hash_recomputed_locally": "sha256:5adb132dcf96ba20285065cd2c5b1d6e73a1ca6c99b20cee90e0fb74e2dbf325",
        "hash_matches_contract": true,
        "no_claims_by_design": "objective.classify_report_type=false; task_type=01 registers assets only",
        "unresolved_assets_have_reason": true
      }
    }
  },
  "claims": []
}
```
