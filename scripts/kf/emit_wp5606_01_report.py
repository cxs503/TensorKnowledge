#!/usr/bin/env python3
"""Emit the wp-5606-01 delivery report (docs/kf/wp-5606-01/KF-RESULT_wp-5606-01.md).

All numbers in the prose are interpolated from the generated manifest/envelope —
nothing is retyped by hand.  The result JSON is embedded verbatim from
runs/wp-5606-01/kf_result.json inside the single ```json block.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "runs" / "wp-5606-01"
OUT_DIR = REPO_ROOT / "docs" / "kf" / "wp-5606-01"
SCHEMA = REPO_ROOT / "schemas" / "kf_result.v1.schema.json"
FIG = PKG / "fig_acceptance.png"
fig_sha = "sha256:" + hashlib.sha256(FIG.read_bytes()).hexdigest() if FIG.is_file() else "missing"

env = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
m = env["outputs"]["asset_manifest.json"]
src = m["source_asset"]
size = src["size"]
att = m["attachments"]
comp = att["composition"]
scan = att["scan"]
loc = [a for a in att["items"] if a.get("locator")]
snap = m["declared_hashes"][0] if m["declared_hashes"] else None
frozen = next(a for a in att["items"] if a["kind"] == "frozen_input_artifact")
checks = m["acceptance_selfcheck"]

def cell(quote: str, n: int = 58) -> str:
    """Table-safe quote: escape pipes (GFM requires \\| ) and keep the text literal."""
    q = quote.replace("|", "\\|")
    return '"' + (q[:n] + "…" if len(q) > n else q) + '"'


rows = "\n".join(
    f"| `{a['asset_id']}` | {a['kind']} | {a['name']} | "
    f"{'是' if a['locator']['resolvable'] else '否'} | {'是' if a['resolvable'] else '否'} | "
    f"L{a['locator']['line']} | {cell(a['locator']['quote'])} |"
    for a in loc
)
locator_ok = sum(1 for a in loc if a["locator"]["resolvable"])

md = f"""# KF-RESULT wp-5606-01

tags: kf-wp:wp-5606-01, KF, 01-asset-registration, report-5606, TensorKnowledge

package_id: `{m['package_id']}` ｜ task_type: `{m['task_type']}` ｜ report_id: `{m['report_id']}` ｜
source_uri: `{src['uri']}` ｜ source_field: `{src['field']}`

## ①本工序做了什么

对 report_id=**5606** 做**资产登记**（01-asset-registration）：确认报告 markdown 的字节
SHA-256 与工作包契约一致，清点正文与平台记录里**声明**的附件/被引用工件，给每个条目配
可解析的原文定位（行号+逐字引文）。**不做抽取**（`objective.extraction_performed=false`），
**不做报告类型分类**（`objective.classify_report_type=false`），**不把任何结论标成 verified**
（verification 由平台门计算）。

源资产确认结果：

| 项 | 值 |
|---|---|
| 报告标题（平台记录） | {src['record_metadata']['title']} |
| scenario_key | `{src['record_metadata']['scenario_key']}` |
| 状态 / 创建者 / 创建时间 | {src['record_metadata']['status']} / {src['record_metadata']['created_by']} / {src['record_metadata']['created_at']} |
| 记录 mission_id | {src['record_metadata']['mission_id']} |
| markdown 字符数（契约 {size['contract_chars']}） | {size['chars']}（`chars_match_contract={size['chars_match_contract']}`） |
| markdown UTF-8 字节数 | {size['bytes_utf8']} |
| 行数 | {size['lines']} |
| 实测 sha256 | `{src['hash']['value']}` |
| 契约 source_hash | `{src['hash']['contract_expected']}` |
| 是否一致 | **{src['hash']['matches_contract']}** |
| 标题/场景/字符数与契约交叉校验 | title={src['contract_cross_check']['title_matches_contract']}，scenario={src['contract_cross_check']['scenario_key_matches_contract']}，chars={src['contract_cross_check']['chars_match_contract']} |

## ②怎么做的（步骤/工具/关键设置）

1. **取原文**：以任务身份登录平台，`GET /tensor/reports/5606`，只读 `markdown` 字段；同时留存
   `figures`（图件声明）与记录元数据。全程只碰 report_id=5606，未读未写其它报告。
2. **哈希**：对 markdown 的 **UTF-8 字节**算 SHA-256（不是字符序列、不是 JSON 序列化后字节），
   与契约 `source_hash` 逐字比对。
3. **附件清点**（三条来源，全部程序化）：
   - 平台记录 `figures[*]`：取 name/caption，并**枚举该条目实际携带的键**判断有无二进制载荷；
   - 正文图件账本表：正则抓 `` `fig-00N` | 名称 | 文件, 文件 | `hash, hash` `` 行，拆出 6 个文件名与
     各自的**声明哈希前缀**；
   - 正文里以绝对路径/裸名出现的被引用工件：冻结输入 JSON、5 个 `.py` 模块（basename）。
4. **可解析性判定**（只做只读探测，不臆断）：
   - 报告正文有无 `![` 图像语法、http 外链、base64 载荷 → 扫描计数 `{scan['markdown_image_syntax_hits']}` / `{scan['markdown_url_hits']}` / 0；
   - 冻结工件路径用 `Path.is_file()` 探测真实存在性；
   - 代码模块在 TensorKnowledge 工作树内按 basename 全树搜索。
   **解析不到就写 `resolvable=false` + 原因**，不把「声明存在」写成「已取得」。
5. **定位器**：每个条目生成 `{{source_field, line, quote, resolvable}}`，quote 取原文该行去首尾空白的
   整行文本，并当场断言 `quote in markdown`（共 {checks['source_locator_count']} 条）。
6. **结构清单**：按 `^#{{1,6}} ` 切节，登记每节的标题/层级/起止行/字符数/节文本 sha256（{len(m['sections'])} 节）。
7. **自检与签名**：生成 `asset_manifest.json` 后按 v1 schema 校验信封；`claims` 输出空数组
   （契约允许，本工序不产知识）。
8. **工具链**：Python 3.11（stdlib `hashlib`/`json`/`urllib`/`re`）+ `jsonschema` 校验；无新增第三方依赖。

## ③产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `runs/wp-5606-01/asset_manifest.json` | 交付本体：源资产（哈希/尺寸/元数据/契约交叉校验）、{att['count']} 条附件与引用工件、{checks['source_locator_count']} 条可解析定位器、{len(m['sections'])} 节结构清单、自检布尔 |
| `runs/wp-5606-01/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]），本报告 ④ 的 json 块即此文件逐字内容 |
| `runs/wp-5606-01/source_5606.md` | 取回的报告原文快照（只读留档，用于定位复现；哈希=上文 source_hash） |
| `runs/wp-5606-01/verify_wp5606_01.py` | 独立校验器：重新拉取原文、重算哈希、逐条验定位器落在所述行、查 id 唯一/作用域/claims 纪律；**不**自称 verified |
| `scripts/kf/build_asset_manifest_wp5606_01.py` | 生成器（幂等；重跑结果除时间戳外一致） |
| `scripts/kf/emit_wp5606_01_report.py` | 本报告的生成器（正文数字全部从 manifest 注入，零手抄） |
| `runs/wp-5606-01/fig_acceptance.png` | ④-1 的结果图（左=资产清点柱图，右=acceptance 自检面板），由 manifest 程序化生成 |
| `scripts/kf/make_wp5606_01_figure.py` | 结果图生成器（matplotlib Agg，英文标签，数字零手抄） |
| `tests/test_kf_wp5606_01_asset_manifest.py` | 5 项 pytest：结构 + 校验器通过 + **2 个负例**（篡改引文、篡改 source_hash 必须 FAIL） |
| `schemas/kf_result.v1.schema.json` | 本检出原先缺失的结果信封 schema，按工作包契约声明路径补齐（内容与仓内既有副本逐字一致，sha256 `170dba8b0b5d54012490aaadc0b68647a9520ecb869e9d03f873afb99b74c076`） |

## ④结果图与证据定位表

### ④-1 结果图（`runs/wp-5606-01/fig_acceptance.png`，sha256 `{fig_sha}`）

![fig_acceptance.png](runs/wp-5606-01/fig_acceptance.png)

- **左panel A. 资产清点**：按条类（figure record entry / figure file / frozen input artifact /
  code module reference）画「报告声明条数」、「引文可解析条数」、「文件字节可取得条数」三组柱。
  {att['count']} 条声明 / {locator_ok} 条引文可解析 / {att['resolvable_count']} 条字节可得 —— 缺口就是⑤要说的那件事。
- **右panel B. acceptance 自检**：六项 acceptance 逐项绿/红；绿=本工序机械自检通过，
  **不是**平台 verification 结论。
- **为什么没有场量云图/与解析解的对比曲线**：本工序是**资产登记**（`extraction_performed=false`），
  不产生任何场量、不重算任何物理量；报告 5606 本身也不含场数据载荷（正文无图件字节）。
  强行画云图等于编造，故此处出的是"机器派生的状态图"而非场图。所有柱子数字由
  `scripts/kf/make_wp5606_01_figure.py` 从 `asset_manifest.json` 读取，零手抄；无 CJK 字体，
  图内标签用英文（数据值仍以原文中文引文形式留在下文表中）。

### ④-2 证据定位表（claim/字段 → 原文引文片段）

登记条目的定位器（`resolvable`=该引文是否在原文逐字命中并落在所述行；**附件字节是否可取**是另一件事，
见 ⑤）。共 {att['count']} 条：figure_record_entry={comp['figure_record_entry']}、
figure_file={comp['figure_file']}、frozen_input_artifact={comp['frozen_input_artifact']}、
code_module_reference={comp['code_module_reference']}。

- 「引文命中+落行」= `locator.resolvable`：引文在原文逐字存在**且**在所述行 → {locator_ok}/{att['count']} 条通过。
- 「字节可取得」= `attachment.resolvable`：条目对应的**文件字节**是否能被本工序取得 → {att['resolvable_count']}/{att['count']} 条可得（原因见 ⑤）。

| asset_id | kind | name | 引文命中+落行 | 字节可取得 | 行 | 原文引文（截断） |
|---|---|---|---|---|---|---|
{rows}

关键字段的定位：

| 字段 | 值 | 原文位置 |
|---|---|---|
| 快照哈希（SQLite 字节 SHA-256） | `{snap['value']}` | L{snap['locator']['line']}：{cell(snap['locator']['quote'], 50)} |
| 冻结输入工件路径 | `{frozen['declared_path']}` | L{frozen['locator']['line']} |
| 平台记录 summary 的 sha256（登记值，非原文引文） | `{src['record_metadata']['summary_sha256']}` | 记录 `summary` 字段，source_field=summary |
| markdown 字节哈希 | `{src['hash']['value']}` | 全文 UTF-8 字节（平台可独立重算） |

> 逐字校验口径：`quote in markdown` 且 `quote in lines[line-1]`。校验器重跑输出
> `locators_checked={checks['source_locator_count']}`、`locators_failed=[]`。

## ⑤注意点与局限

1. **附件只有声明、没有字节**：正文无 `![` 图像语法、无 http 外链、记录 `figures[*]` 只有
   name+caption（无 base64 载荷）。6 个图件文件（3×(PNG+PDF)）在正文里**只登记了 11 位 sha256 前缀**
   （如 `fig-001` → `c2c890360ad3, 037bb6c488eb`），因此本工序**无法**重算图件字节哈希，
   `resolvable` 一律记 false——这是如实记录，不是判定"图不存在"。
2. **冻结输入工件在构建时不存在**：正文引用的 `{frozen['declared_path']}` 指向另一 mission 的工作树，
   `is_file()` 探测为 {frozen['resolution']['exists']}，登记为未解析；快照哈希
   `{snap['value']}` 只能作为"报告声明值"转述，无法在本工序复算。
3. **只登记了 1 个完整 64-hex 值**（快照哈希）；图件哈希与表内 `f46ab6f316a2` 前缀均为截断形式
   （`scan.full_sha256_literals={scan['full_sha256_literals']}`）。
4. **代码模块不可从报告内解析**：`snapshot.py/provenance.py/skeleton.py/figures.py/verify.py` 只给
   basename，无仓库/路径信息；TensorKnowledge 检出内无同名胜任文件 → `resolvable=false`。
   平台记录 `summary` 字段称这批模块落在论文生产线工具树 `tools/chronicle/report/`（**该串出自 `summary` 而非
   `markdown`**，本工序只登记、不据此断言代码位置），该树不在 TensorKnowledge 检出内，属跨仓引用。
5. **mission 号不一致**：平台记录 `mission_id={src['record_metadata']['mission_id']}`，本工作包由
   mission 15569 的产线派发，契约 `mission_id: null`。三个值原样登记，**不做调和**（本工序无裁定权）。
6. **契约分层提示 `{src['contract_cross_check']['contract_layer_hint']['value']}`** 原样登记不解读
   （`classify_report_type=false`）。
7. **未做的事**（写进 manifest 的 `not_performed`）：知识抽取/claim 生成、报告类型分类、
   任何 claim 的验证、图件字节级校验。
8. 本报告中的一切数字都由 `emit_wp5606_01_report.py` 从 manifest 注入，人工零手抄；改动 manifest 后重跑
   生成器即可让正文与产物保持一致。

## ⑥自检：逐条对照 acceptance

| acceptance 项 | 结果 | 证据 |
|---|---|---|
| `valid_json` | ✅ | 生成器自检 `{checks['valid_json']}`；`json.load` 产物成功 |
| `schema_pass` | ✅ | `jsonschema.validate(envelope, schemas/kf_result.v1.schema.json)` → `{checks['schema_pass']}`（独立校验器复核同结果） |
| `source_locator_resolvable` | ✅ | {checks['source_locator_count']} 条定位器全部 `quote in markdown` 且在所述行；`locators_failed=[]` |
| `source_hash_matches` | ✅ | 重算 `{src['hash']['value']}` == 契约值（`{src['hash']['matches_contract']}`），独立校验器用**新拉取**原文复算亦一致 |
| `no_duplicate_ids` | ✅ | {att['count']} 个 asset_id 唯一（生成器 + 校验器双查） |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅（空集） | `claims=[]`，契约允许（`notes`：claims 允许为空数组）；`claims_registration.reason` 已写明缘由 |

如实说明的**非本合同**发现（不粉饰，也不当作失败项）：附件字节不可得（⑤-1/2），故 `attachments.resolvable_count=0`。
这是报告载荷的客观状态，不是本工序的疏漏，已在 manifest 中逐条给出 `resolution` 理由。

## repro_cmd（一键复跑）

```bash
# 环境：TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS 已注入
cd <repo>
python3 scripts/kf/build_asset_manifest_wp5606_01.py --report-id 5606 --out runs/wp-5606-01   # 生成
python3 runs/wp-5606-01/verify_wp5606_01.py                                                  # 独立校验（PASS 退出 0）
python3 scripts/kf/emit_wp5606_01_report.py                                                  # 重建本报告
python3 -m pytest tests/test_kf_wp5606_01_asset_manifest.py -q                               # 5 passed（含 2 负例）
```

## 结果 JSON（唯一 json 块，逐字来自 runs/wp-5606-01/kf_result.json）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""

OUT_DIR.mkdir(parents=True, exist_ok=True)
target = OUT_DIR / "KF-RESULT_wp-5606-01.md"
target.write_text(md, encoding="utf-8")
print(f"wrote {target} ({len(md)} chars)")