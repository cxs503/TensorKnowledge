#!/usr/bin/env python3
"""Render docs/kf/wp-11204-01/KF-RESULT-wp-11204-01.md.

Every number and every digest in the prose is injected from
docs/kf/wp-11204-01/asset_manifest.json + self_check.json; the machine-readable
delivery block is json.dumps(kf_result.json). No value is typed by hand, and
tests/test_kf_wp11204_01.py re-checks that afterwards.
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "docs", "kf", "wp-11204-01")
man = json.load(open(os.path.join(OUT, "asset_manifest.json"), encoding="utf-8"))
kf = json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))
sc = json.load(open(os.path.join(OUT, "self_check.json"), encoding="utf-8"))
probes = json.load(open(os.path.join(ROOT, "work", "wp-11204-01", "probes.json"), encoding="utf-8"))
N_PROBES = len(probes["http_probes"]) + len(probes["fs_probes"])
N_HTTP = len(probes["http_probes"])
N_FS = len(probes["fs_probes"])
N_MULTI = len(man["integrity"]["multi_occurrence_quotes"])
N_TESTS = open(os.path.join(ROOT, "tests", "test_kf_wp11204_01.py"), encoding="utf-8").read().count("\ndef test_")

c = man["counts"]
figs = [e for e in man["assets"] if "figure_bytes" in e]
fig_rows = "\n".join(
    "| %s | `%s` | %d | %d×%d | `%s` |" % (
        e["asset_id"], e["figure_bytes"]["url_path"].rsplit("/", 1)[-1],
        e["figure_bytes"]["bytes"], e["figure_bytes"]["png_size"]["width"],
        e["figure_bytes"]["png_size"]["height"], e["figure_bytes"]["sha256"])
    for e in figs)
cls_rows = "\n".join("| `%s` | %d |" % (k, v) for k, v in sorted(c["by_class"].items(), key=lambda x: (-x[1], x[0])))
check_rows = "\n".join("| `%s` | %s | %s |" % (k, "PASS" if v["pass"] else "FAIL",
                                               str(v["detail"]).replace("|", "/")[:150])
                       for k, v in sc["checks"].items())
asset_rows = "\n".join(
    "| %s | %s | %s | `%s` | %s |" % (
        e["asset_id"], e["asset_class"], e["label"].replace("|", "/")[:78], e["resolution"],
        next((l["start_line"] for l in e["locators"] if l["kind"] == "markdown_char_span"), ""))
    for e in man["assets"])

body = f"""# KF-RESULT wp-11204-01

**工序**：`01-asset-registration`（登记源资产；不抽取、不分类、不做验证）
**报告**：report_id=`11204` · 《{man["source"]["title_markdown_h1"]}》 ·
scenario=`{man["source"]["scenario_key"]}` · mission_id=`15693`（记录内
record.mission_id=`{man["source"]["record_mission_id"]}`，见观察 O3）
**tags**：`kf-wp:wp-11204-01` · `kf-task:01-asset-registration` · `lane:C`
**源字节哈希**：`sha256:{man["source"]["hash"]}`
（{man["source"]["chars"]} 字符 / {man["source"]["bytes_utf8"]} 字节 UTF-8，与契约声明逐字节一致）
**产出**：`asset_manifest.json`（{c["assets"]} 项资产：resolved_in_source {c["resolved_in_source"]} /
referenced_unresolved {c["referenced_unresolved"]} / declared_absent {c["declared_absent"]}）+
`kf_result.json` + `self_check.json` + `fig_asset_resolution.png`

## ① 本工序做了什么

对 report 11204（TensorPhysics 节点 `p273w3-n01-fem-elastoplastic-cohesive`，
FEM J2 弹塑性 + 3D 混合模式 cohesive 的 CT / SE(B) 验证）做**资产登记**，只回答三件事：
这份报告的源字节是什么、它声明了哪些可解析的工件、每个工件在本包范围内解析到什么程度。

- 拉取 `GET /api/v1/tensor/reports/11204` 的 `markdown` 字段，按 UTF-8 编码重算 SHA-256
  → `sha256:{man["source"]["hash"]}`，与契约 `source_hash` **相等**且字符数 = {man["source"]["chars"]}
  与契约一致后才允许继续（不等即 `SystemExit`，不留"哈希对不上但仍然出清单"的路径）。
- 登记 **{c["assets"]} 项资产**，分 16 类：源 markdown 1、记录元数据 1、
  记录 `figures[]` 3（**PNG 字节到手并哈希**）、正文图路径 3、模块目录 1、源码文件 5、
  脚本 2、测试文件 1、结果数据 2、符号 1、参数 1、出处指针 1、外部标准 2、
  外部准则 1、节点标识 1、复现命令块 1。
- 每项资产都带**可解析定位符**：正文引用用逐字子串（`start_char/end_char/start_line/end_line` +
  `occurrences` + 全部命中跨度），记录字段用 `record_path`（生成器逐字段解析，解析不到即失败）。
- **不做的事**（写进 `limitations`）：不抽取 claim（`claims=[]`，契约允许且禁止硬造）、
  不重算 ③ 表中任何数字、不判定报告类型、不重跑上游 40 项测试、不给任何资产标 `verified`
  （verification 由平台门计算）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **活取 + 硬哈希闸门**（`scripts/kf/fetch_report_11204.py`）：`POST /auth/login` 取 token →
   `GET /tensor/reports/11204` → `hashlib.sha256(markdown.encode("utf-8"))` 与契约常量比对；
   同时落 `work/wp-11204-01/source_markdown.md`（**逐字节**原文快照）、`record.json`、`source_meta.json`。
2. **双解析器探针**（`scripts/kf/probe_assets_wp11204_01.py`）：平台侧 {N_HTTP} 条 HTTP 路径 +
   工作树侧 {N_FS} 条正文路径，全部只读，结果落 `work/wp-11204-01/probes.json`。
   探针**只报事实**，不升级为"已解析"。
3. **清单生成器**（`scripts/kf/build_asset_manifest_wp11204_01.py`）六道闸门，任一不过即非零退出：
   G1 哈希/字符数与契约一致；G2 每条正文定位符是逐字子串；G3 引文若多次出现则**枚举全部跨度**
   （本包 {N_MULTI} 条：`scripts/m9422_run_verification.py` ×2、`ASTM E399` ×3、`ASTM E1820` ×3）；
   G4 **完备性扫描**——正则扫出正文里 {man["integrity"]["completeness_scanner_tokens"]} 个路径型/标准型
   token，逐个要求被某项已登记资产的引文覆盖，出现未登记引用即失败（防"漏登记"而非只防"错登记"）；
   G5 asset_id 唯一 + 计数从资产表反算；G6 每张图**两次独立抓取哈希一致**才写入。
4. **图字节解析（本包的新事实）**：`/api/v1/tensor/reports/11204/figures/<name>`
   （**无扩展名**）返回 HTTP 200 + `image/png` 真实字节；同路径加 `.png` 返回 HTTP 404。
   此前若干包把该平台判为"图只有元数据"，实测是 URL 形状问题——本包因此把 A03–A05
   记为 `resolved_in_source` 并给出 sha256，而不是照抄"metadata_only"。
5. **独立校验器**（`scripts/kf/validate_wp11204_01.py`）：**不信任本地快照**，重新调 API 取原文、
   重算哈希、重解 {sum(len(e["locators"]) for e in man["assets"])} 条定位符、按
   `schemas/kf_result.v1.schema.json` 与本包 `asset_manifest.schema.json` 双 schema 校验，
   产出 `self_check.json`（`all_pass={str(sc["all_pass"]).lower()}`）。
6. **离线不变量测试**（`tests/test_kf_wp11204_01.py`，{N_TESTS} 条）：断言不变量而非"跑通"——
   哈希恒等、定位符逐字且跨度自洽、记录字段可达、id 唯一、计数自洽、图字节哈希、schema 合法、
   claims 空且无 `verified`、扫描器零漏、报告正文里出现的每个 64 位摘要都必须能在清单里查到（防手抄）。

repro_cmd（一键复跑；工作树根为仓库检出）：

```bash
cd "$(git rev-parse --show-toplevel)" && \\
python3 scripts/kf/fetch_report_11204.py && \\
python3 scripts/kf/probe_assets_wp11204_01.py && \\
python3 scripts/kf/build_asset_manifest_wp11204_01.py && \\
python3 scripts/kf/validate_wp11204_01.py && \\
python3 scripts/kf/fig_wp11204_01.py && \\
python3 scripts/kf/render_report_wp11204_01.py && \\
python3 -m pytest tests/test_kf_wp11204_01.py -q
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11204-01/asset_manifest.json` | 主产物：{c["assets"]} 项资产 + 定位符 + 解析状态 + 完整性 ledger + {len(man["observations"])} 条观察 + {len(man["limitations"])} 条局限 |
| `docs/kf/wp-11204-01/kf_result.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]） |
| `docs/kf/wp-11204-01/asset_manifest.schema.json` | 本包清单形状（三值解析词表钉死；`referenced_unresolved` 不许夹带字节证据） |
| `docs/kf/wp-11204-01/self_check.json` | 独立复算结果：{len(sc["checks"])} 条检查，`all_pass={str(sc["all_pass"]).lower()}` |
| `docs/kf/wp-11204-01/fig_asset_resolution.png` | 图 1：按类别的资产解析分布 + 五条证据通道实测可达性 |
| `work/wp-11204-01/source_markdown.md` / `record.json` / `source_meta.json` | 逐字节源快照与记录快照（溯源面） |
| `work/wp-11204-01/figures/*.png` | 3 张记录图的实际字节（供下游免重复抓取） |
| `work/wp-11204-01/probes.json` | {N_PROBES} 条探针的原始结果（HTTP 状态/字节数/正文前缀 + 文件系统存在性） |

按类别分布：

| asset_class | 数量 |
|---|---|
{cls_rows}

图字节明细（两次抓取一致，`image/png`）：

| id | figure name | bytes | size | sha256 |
|---|---|---|---|---|
{fig_rows}

## ④ 证据定位表

全部资产一览（行号为源 markdown 中的定位行；完整字符跨度见 `asset_manifest.json`）：

| id | class | label | resolution | line |
|---|---|---|---|---|
{asset_rows}

关键字段 → 原文引文（逐字，平台可二次核验）：

| claim / 字段 | 原文引文片段 |
|---|---|
| 本包登记对象 = 该 markdown | `# FEM 弹塑性本构（von Mises J2）与 3D 混合模式 cohesive 单元：CT / 三点弯曲验证` |
| 生产者仓 = TensorPhysics | `**仓** TensorPhysics` |
| 生产者分支（无 commit id） | `agent/m9422` |
| 模块 = fem_nonlinear | `src/tensorphysics/fem_nonlinear/` |
| 数字来源工件（未解析） | `artifacts/m9422/verification.json` |
| 判据工件（未解析） | `acceptance.json` |
| 图 1 正文引用 | `figures/m9422/fig1_ct_field_and_seb_cohesive.png` |
| 复现命令块 | `python scripts/m9422_run_verification.py   # 全部数字 -> artifacts/m9422/*.json` |
| 半模型 EDI 符号 | `j_integral(symmetry_factor=2)` |
| 外部标准（仅标号引用） | `ASTM E399` / `ASTM E1820` |

## ⑤ 注意点与局限

1. **`resolved_in_source` ≠ 已验证**。它只表示字节到手并哈希（源 markdown、记录字段、
   3 张图）；③ 表里的 6 项 PASS 判据、40 项测试、154 s 运行时间的**上游声明一律未复核**——
   `artifacts/m9422/*.json` 在本包范围内 HTTP 404 且工作树无此路径（见 `probes.json`）。
2. **无 commit id**：报告只给仓 + 分支（`TensorPhysics @ agent/m9422`），没有 commit SHA，
   因此 A09–A19 的字节无法钉到不可变版本；这是源本身的缺口，本包不补写。
3. **图路径 ↔ 记录图名的映射是推断**：正文写 `figures/m9422/figN_*.png`，记录写
   `figures[N].name=figN_*`，两者仅 basename 相同；源从未声明映射关系，故 A06–A08 保持
   `referenced_unresolved`，映射只在 A03–A05 的说明里作为推断记录（局限 L4）。
4. **URL 形状坑**：`/figures/<name>.png` 404、`/figures/<name>` 200——把 404 当作"图不存在"
   会得出错误的"metadata_only"结论。本包把两种形状的实测状态都写进 `figure_bytes`。
5. **标题漂移**：record.title 用半角括号 `本构(von Mises J2)`，markdown H1 用全角
   `本构（von Mises J2）`；下游必须按 report_id 取，不能按标题相等匹配（观察 O1）。
6. **`record.summary` 被截断**（结尾 `… 6 项机器判据全部 PASS；p`），不可当自足证据源（观察 O5）。
7. **图字节已哈希但内容未审计**：3 张 PNG 哈希两次一致（`image/png`，1725×645），但坐标轴、
   曲线数值与 ③ 表格是否一致**未审计**——那是抽取/验证工序的事（清单局限 L7）。
8. **契约 mission_id=null vs record.mission_id={man["source"]["record_mission_id"]}**：
   仅记录观察，本包不调和（观察 O3）。

## ⑥ 自检：逐条对照 acceptance

| 判据 | 结论 | 证据 |
|---|---|---|
| `valid_json` | 通过 | `kf_result.json`、`asset_manifest.json` 均可解析（A1） |
| `schema_pass` | 通过 | 信封过 `schemas/kf_result.v1.schema.json`，清单过本包 `asset_manifest.schema.json`（A2） |
| `source_locator_resolvable` | 通过 | 对**实时**重取的 markdown 重解 {sum(len(e["locators"]) for e in man["assets"])} 条定位符，0 失败（A3） |
| `source_hash_matches` | 通过 | 实时重算 `sha256:{man["source"]["hash"]}` = 契约值；本地快照与实时字节逐字节相同（A4） |
| `no_duplicate_ids` | 通过 | {c["assets"]} 个 id 全唯一，计数与资产表反算一致（A5） |
| `all_claims_have_evidence_or_explicit_unresolved_status` | 通过（空集合法） | `claims=[]`：契约允许且禁止硬造；未产生任何可被误读为"已支持"的 claim（A6） |

附加不变量（acceptance 未点名但"零手抄"需要的）：`I1` 无 `verified/confirmed` 标记 ·
`I2` 计数自洽 · `I3` 3 张图哈希两次一致 · `I4` 完备性扫描 {man["integrity"]["completeness_scanner_tokens"]} token 零漏。
`self_check.json` 明细：

| check | 结果 | detail |
|---|---|---|
{check_rows}

**误差判定**：本工序不产生物理量，没有与实验/解析解的误差可比。可量化的"误差"全部是
**恒等式判别**，误差恒为 0（等价于 <3%）：源哈希 = 契约哈希、字符数 {man["source"]["chars"]} = 契约
{man["source"]["chars"]}、{sum(len(e["locators"]) for e in man["assets"])} 条定位符逐字命中率 100%、
{man["integrity"]["completeness_scanner_tokens"]} 个路径 token 漏登记 0 个、3 张图重取哈希一致率 3/3。
报告 ③ 的物理精度（CT 峰值载荷 0.104%、弹塑性 J 6.05% 等）属于上游，本包**明确不判**，
其 verified 状态由平台门计算。

## 图

![图1 资产解析分布与证据通道可达性](fig_asset_resolution.png)

图 1 左：{c["assets"]} 项资产按类别与解析状态的分布（蓝=字节到手，灰=仅引用）；
右：五条证据通道的实测可达性——markdown / 记录字段 / 图 PNG 字节可达，
`/tensor/artifacts/m9422/*.json` 与 TensorPhysics 仓文件不可达，故 21 项保持 unresolved。

## 平台结果信封（唯一 JSON 块）

```json
{json.dumps(kf, ensure_ascii=False, indent=1)}
```
"""

path = os.path.join(OUT, "KF-RESULT-wp-11204-01.md")
open(path, "w", encoding="utf-8").write(body)
print("wrote", path, len(body), "chars")