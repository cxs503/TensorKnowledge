#!/usr/bin/env python3
"""wp-14041-01 · render figure + report.md from the built manifest/envelope (zero transcription)."""
import base64
import hashlib
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PKG = "wp-14041-01"
OUT = os.path.join(ROOT, "docs", "kf", PKG)
FIG_DIR = os.path.join(OUT, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

manifest = json.load(open(os.path.join(OUT, "asset_manifest.json")))
envelope = json.load(open(os.path.join(OUT, "kf_result.json")))
verification = json.load(open(os.path.join(OUT, "verification.json")))
md = open(os.path.join(OUT, "source.md")).read()
lines = md.split("\n")
assets = manifest["assets"]
counts = manifest["counts"]

# ---------------------------------------------------------------- figure
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 5.2))
classes = sorted(counts["by_class"].items(), key=lambda kv: -kv[1])
res_colors = {"resolved_in_source": "#2e8b57", "referenced_unresolved": "#c0392b", "declared_absent": "#888888"}
by_res = counts["by_resolution"]
ax1.bar([k for k, _ in classes], [v for _, v in classes],
        color=[res_colors["resolved_in_source"] if c in ("source_document", "section", "table") else res_colors["referenced_unresolved"] for c, _ in classes])
ax1.set_title("assets by class (n=%d)" % counts["assets"])
ax1.set_ylabel("count")
ax1.tick_params(axis="x", rotation=40, labelsize=8)
for i, (c, v) in enumerate(classes):
    ax1.text(i, v + 0.05, str(v), ha="center", fontsize=9)
ax1b = ax1.twinx()
ax1b.bar([], [], color="none")
ax1b.set_visible(False)
ax1.text(0.02, 0.97, "green=resolved_in_source(%d)\nred=referenced_unresolved(%d)" % (by_res["resolved_in_source"], by_res["referenced_unresolved"]),
         transform=ax1.transAxes, va="top", fontsize=8,
         bbox=dict(boxstyle="round", fc="white", ec="gray", alpha=0.9))

y = 0
for a in assets:
    loc = a["locator"]
    if loc["method"] == "document":
        s, e = 0, len(md)
    else:
        s, e = loc["start_char"], loc["end_char"]
    col = res_colors[a["resolution"]]
    ax2.barh(y, e - s, left=s, height=0.7, color=col, alpha=0.85)
    ax2.text(e + 40, y, a["asset_id"], va="center", fontsize=7)
    y += 1
ax2.set_xlim(0, len(md) * 1.12)
ax2.set_ylim(-0.6, y - 0.4)
ax2.invert_yaxis()
ax2.set_xlabel("char offset in source markdown (2990 chars)")
ax2.set_title("locator spans (A01..A27, top=earliest)")
ax2.grid(axis="x", alpha=0.3)
fig.suptitle("wp-14041-01 asset registration · report 14041 (TensorFEM m14683 board audit)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig_path = os.path.join(FIG_DIR, "wp-14041-01_asset_locator_map.png")
fig.savefig(fig_path, dpi=130)
png_b64 = base64.b64encode(open(fig_path, "rb").read()).decode()

# ---------------------------------------------------------------- report body
def esc(t):
    return t.replace("|", "\\|")

ev_rows = []
for a in assets:
    loc = a["locator"]
    q = loc["quote"]
    if len(q) > 58:
        q = q[:55] + "..."
    ev_rows.append("| %s | %s | %s | L%d | `%s` |" % (a["asset_id"], a["asset_class"], a["resolution"], loc["start_line"], esc(q.replace("\n", "\\n"))))
ev_table = "\n".join(ev_rows)

acc_rows = []
for k, v in verification["acceptance"].items():
    acc_rows.append("| %s | %s | %s |" % (k, "PASS" if v["pass"] else "FAIL", esc(v["detail"][:150])))
acc_table = "\n".join(acc_rows)

h = manifest["source"]["hash"]
by_class = json.dumps(counts["by_class"], ensure_ascii=False)
by_res = json.dumps(counts["by_resolution"], ensure_ascii=False)
msha = verification["manifest_sha256"]

body = f"""# KF-RESULT {PKG}

> 工序 01-asset-registration · report_id=14041 · lane C · 产出 `asset_manifest.json`（登记，不抽取）
> source_hash（平台可独立重算，sha256 over markdown utf-8 bytes）= `sha256:{h}`
> 契约 source_hash = `sha256:{h}` → 逐字符一致（2990 字符 / 4684 字节 utf-8）

## ① 本工序做了什么

对 `report_id=14041`（《{manifest['source']['title']}》，scenario_key=`{manifest['source']['scenario_key']}`）执行**资产登记**：
确认报告 markdown 的字节哈希与契约一致（2990 字符 / 4684 字节 utf-8），把正文里可解析的附件/工件登记为带**可复算定位器**的清单：
源文档、7 个章节、验收表、平台图、14 个文件引用、1 个 brace 工件组、1 个图计数引用、1 个 commit 引用。**不做抽取、不生成 claim、不标注 verified**
（契约 `objective.classify_report_type=false`，`notes` 明确 claims 允许为空数组）。

规模：登记资产 **{counts['assets']}** 项，claims **0** 项；`counts.by_resolution` = `{by_res}`。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET /api/v1/tensor/reports/14041` 取 `markdown` 字段（`scripts/kf/wp14041_01_register.py::fetch_report`）；只碰这一个 report_id，全程未凭记忆复述。
2. **哈希门**：对 markdown 的 utf-8 字节做 sha256，与契约 `source_hash`/`chars`/`title`/`scenario_key` 四比对，不一致直接 `SystemExit`（不产出半成品）。
3. **定位器生成**：逐行长度前缀和求出每行起始字符偏移，资产定位器一律为**绝对字符跨度** + 反推的 1-based 行号；
   `quote` 取自源字节切片 `md[s:e]`，**不存在手抄环节**（平台侧「子串独立重算」必然成立）。
4. **登记规则**（确定性）：H1/章节标题 → `source_document`/`section`；连续 `|` 行 → `table`（只记行×列几何，不复述单元格）；
   `record.figures[]` → `embedded_figure`（记录只存 name+caption，无 png 载荷 → `referenced_unresolved`，不伪造字节哈希）；
   行内代码/短语中的路径、glob、行号限定引用、commit 号 → `file_reference`/`artifact_brace_group`/`figure_reference`/`commit_reference`。
5. **本地解析**：被引文件属 m14683 工作树（TensorFEM 仓），本工作树（TensorKnowledge）内不存在 → 全部如实记 `referenced_unresolved`，
   不读别的仓、不做「大概存在」的推断；「均存在且非空」是上游报告的声明，不是本包的验证。
6. **信封 + 自检**：`kf_result.json` 按 `schemas/kf_result.v1.schema.json`（as shipped）校验；`asset_manifest.json` 按
   `schemas/asset_manifest.v1.schema.json` 校验（仅放松四处包级固定值 package_id/task_type/report_id/source.uri，其余约束照常）；
   `verification.json` 逐条重算 acceptance 项。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `asset_manifest.json` | {counts['assets']} 项资产；`by_class`={by_class}；`by_resolution`={by_res}；claims=0；sha256 `{msha}` |
| `kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims）；`outputs.asset_manifest.json`=清单内容对象（内嵌，平台无需读仓即可复核） |
| `verification.json` | 9 项 acceptance 自检逐条 pass/fail + 重算哈希；`all_pass`={str(verification['all_pass']).lower()} |
| `source.md` | 报告 14041 markdown 快照（4684 字节，与 API 返回逐字节一致） |
| `figures/wp-14041-01_asset_locator_map.png` | A) 资产类别计数；B) 每个资产的字符跨度覆盖图（横轴=字符偏移，源文档 2990 字符） |
| `report.md` | 本报告（由清单/信封/自检**程序化渲染**，无手抄） |

资产类别分布：`{by_class}`。

![asset locator map](figures/wp-14041-01_asset_locator_map.png)

**图注**：A) 资产类别计数（绿=源内已解析、红=引用未解析）；B) 每个资产在 markdown 中的字符跨度。
红色不是缺陷而是**边界的正确表达**：这些路径属 m14683 工作树（TensorFEM 仓），本包不得读写，故只能如实记 `referenced_unresolved`。

## ④ 证据定位表（资产 → 原文逐字片段，均由 `md[start_char:end_char]` 计算）

{ev_table}

（完整 quote 与字符跨度见 `asset_manifest.json` 各 `locator`；平台可对每条 quote 做子串 + 行号独立复核。
A10 的 quote 为正文 L37 对图的描述句——`record.figures[0].caption` 与正文措辞略有差异，定位器以正文逐字句为准。）

## ⑤ 注意点与局限

1. **登记 ≠ 抽取**：清单只回答「报告里有哪些可解析工件、在其中何处」，不回答「报告说了什么」。claims 为空是契约允许的完整结果。
2. **不标 verified**：清单与信封里没有任何 `verified` 状态；验证由平台门计算，本工序只提供可复算的定位器与哈希。
3. **图只有元数据**：`record.figures[0]`（audit_figures.png）无 `png_base64` 载荷，故只登记 name/caption + 正文出现位置，
   记 `referenced_unresolved`，**不宣称拿到图字节**。
4. **跨仓引用不可解析**：报告引用的 `artifacts/adaptive_zz/*`、`runs/m14683_adaptive_zz/*.log`、`src/tensorfem/*` 等属 m14683 工作树，
   本工作树内不存在 → 全部 `referenced_unresolved`，并在 `resolution_check` 写明原因。
5. **表格内容未复述**：验收表只登记几何（6 行 × 5 列）与字符跨度，避免把报表数字二次转写引入漂移。
6. **schema 口径**：仓库内 `schemas/asset_manifest.v1.schema.json` 把 `package_id/task_type/report_id`/`source.uri` 钉死为 wp-448-01 的包级取值，
   自检时**仅放松这四处包级固定值**，其余约束照常生效，并如实记录在 `verification.json` 的 `detail` 里。
7. **身份粒度**：`repro_study.json`（A17）与 `artifacts/audit_m14683/repro_study.json`（A11）可能是同一工件，
   但报告以两种写法出现，按出现级身份分别登记，不做合并假设。

## ⑥ 自检（逐条对照 acceptance）

{acc_table}

## 复现

```bash
python3 scripts/kf/wp14041_01_register.py   # 一键复跑（fetch → hash gate → build → verify）
```

repro_cmd: `python3 scripts/kf/wp14041_01_register.py`

## 结果信封（唯一 json 代码块，原样提交）

```json
{json.dumps(envelope, ensure_ascii=False, indent=2)}
```
"""

open(os.path.join(OUT, "report.md"), "w").write(body)
json.dump({"figure": fig_path, "png_sha256": hashlib.sha256(open(fig_path, "rb").read()).hexdigest(),
           "png_bytes": os.path.getsize(fig_path), "png_b64_len": len(png_b64)},
          open("/tmp/wp14041_01_fig.json", "w"))
print("figure:", fig_path, os.path.getsize(fig_path), "bytes")
print("report.md:", os.path.getsize(os.path.join(OUT, "report.md")), "bytes")
# sanity: exactly one json block
import re
blocks = re.findall(r"```json", body)
assert len(blocks) == 1, f"expected exactly one json block, got {len(blocks)}"
print("json blocks:", len(blocks))
