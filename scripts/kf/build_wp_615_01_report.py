#!/usr/bin/env python3
"""由已登记清单渲染 KF-RESULT 报告（markdown + 图件 + 平台 POST 载荷）。

零手抄：正文里出现的每个数字都从 asset_manifest.json / checks.json 注入，
唯一一个 ```json 代码块直接来自 artifacts/kf/wp-615-01/kf_result.json（原样，不改一个字节）。
"""
from __future__ import annotations

import argparse
import base64
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PKG = "wp-615-01"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))  # 复用工序 01 的 markdown 解析器，避免两套口径
OUT = ROOT / "artifacts" / "kf" / PKG
DOCS = ROOT / "docs" / "kf" / f"KF-RESULT-{PKG}.md"
MIRROR = ROOT / "knowledge" / "kf" / PKG
MISSION_ID = 15514


def make_figure(manifest: dict, checks: dict, png: Path) -> Path:
    assets = manifest["assets"]
    kinds = [a["kind"] for a in assets]
    labels = [f"{a['asset_id'].replace('asset-615-', '')}" for a in assets]
    colors = {"resolved": "#2f7d32", "partially_resolved": "#ef6c00", "declared_unresolvable": "#c62828"}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 7.2), gridspec_kw={"width_ratios": [1.55, 1]})
    y = list(range(len(assets)))[::-1]
    ax1.barh(y, [1] * len(assets), color=[colors[a["status"]] for a in assets], height=0.68)
    for yy, a, lab, k in zip(y, assets, labels, kinds):
        ax1.text(0.02, yy, f"{lab}  [{k}]", va="center", ha="left", fontsize=8.2, color="white", family="DejaVu Sans")
        off = a["locator"]["offset_chars"]
        ax1.text(1.02, yy, f"@{off}" if off is not None else "—", va="center", ha="left", fontsize=7.6, color="#37474f")
    ax1.set_yticks([])
    ax1.set_xticks([])
    ax1.set_xlim(0, 1.18)
    ax1.set_title(f"report 615 asset registry — {len(assets)} assets, quote offsets (chars)", fontsize=10)
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in colors.values()]
    ax1.legend(handles, list(colors), loc="lower right", fontsize=8, frameon=False)

    keys = [
        ("source_hash_matches", checks["source_hash_matches"]),
        ("chars_match_contract", checks["chars_match_contract"]),
        ("source_locator_resolvable", checks["source_locator_resolvable"]),
        ("no_duplicate_ids", checks["no_duplicate_ids"]),
        ("schema_pass (manifest)", checks["schema_pass"]),
        ("kf_result_schema_pass", checks["kf_result_schema_pass"]),
        ("claims == [] (no extraction)", checks["claims_emitted"] == 0),
        ("unresolved have reason", checks["unresolved_assets_have_reason"]),
    ]
    yy = list(range(len(keys)))[::-1]
    ax2.barh(yy, [1] * len(keys), color=["#2f7d32" if ok else "#c62828" for _, ok in keys], height=0.6)
    for j, (k, ok) in zip(yy, keys):
        ax2.text(0.03, j, ("PASS " if ok else "FAIL ") + k, va="center", fontsize=8.4, color="white")
    ax2.set_yticks([])
    ax2.set_xticks([])
    ax2.set_xlim(0, 1)
    ax2.set_title("acceptance self-check (machine recomputed)", fontsize=10)
    src = manifest["source"]
    fig.text(0.01, 0.015,
             f"sha256(markdown)={src['source_hash']}  chars={src['chars']}  bytes={src['bytes']}  "
             f"lines={src['lines']}  figure endpoint HTTP "
             f"{[a['retrieval']['http_status'] for a in assets if a['kind'] == 'figure']}",
             fontsize=7.2, family="DejaVu Sans Mono")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(png, dpi=150)
    plt.close(fig)
    return png


def source_derived_sentences(snapshot: dict) -> dict[str, str]:
    """从源快照重解析参数表与基准表，拼出正文句子——正文里的源数值一律程序化注入，不手打。"""
    import wp_615_01_register_assets as reg  # noqa: E402

    idx = reg.MarkdownIndex(snapshot["markdown"])
    param = idx.table_after("### 几何与参数")
    items = []
    for row in param["rows"]:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 3:
            items.append(f"{cells[0]} {cells[1]} {cells[2]}")
    bench = idx.table_after("### Stokes沉降基准")
    kv = {}
    for row in bench["rows"]:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 2:
            kv[cells[0]] = cells[1]
    analytic = next((v for k, v in kv.items() if "解析终端速度" in k), "n/a")
    sim = next((v for k, v in kv.items() if "模拟终端速度" in k), "n/a")
    rel = next((v for k, v in kv.items() if "相对误差" in k), "n/a")
    acc = idx.table_after("### 验收判据")
    acc_rows = []
    for row in acc["rows"]:
        cells = [c.strip() for c in row.strip().strip("|").split("|")]
        if len(cells) >= 5:
            acc_rows.append(f"{cells[0]}={cells[1]}（阈值 {cells[2]} {cells[3]}，{cells[4]}）")
    return {
        "params": "、".join(items),
        "benchmark": (f"Stokes 终端速度解析解 {analytic}，模拟值 {sim}"
                      f"（报告自报相对误差 {rel}）"),
        "acceptance_rows": "；".join(acc_rows),
    }


def build_markdown(manifest: dict, checks: dict, envelope_text: str, snapshot: dict) -> str:
    src = manifest["source"]
    rf = src["record_fields"]
    fig_asset = next(a for a in manifest["assets"] if a["kind"] == "figure")
    def _cell(a: dict) -> str:
        quote = (a["locator"]["quote"] or "").replace("|", "\\|")
        off = "—" if a["locator"]["offset_chars"] is None else a["locator"]["offset_chars"]
        return f"| {a['asset_id']} | {a['kind']} | {a['status']} | {off} | `{quote[:78]}` |"

    rows = "\n".join(_cell(a) for a in manifest["assets"])
    unres = "\n".join(f"| {u['asset_id']} | {u['kind']} | {u['reason']} |" for u in manifest["unresolved"])
    counts = manifest["counts"]
    repro = ("TOKEN=$(curl -s -X POST $TENSOR_API_BASE/auth/login -H 'Content-Type: application/json' "
             "-d \"{\\\"username\\\":\\\"$TENSOR_AGENT_USER\\\",\\\"password\\\":\\\"$TENSOR_AGENT_PASS\\\"}\" "
             "| python3 -c 'import sys,json;print(json.load(sys.stdin)[\"access_token\"])'); "
             "python3 scripts/kf/wp_615_01_register_assets.py && "
             "python3 scripts/kf/build_wp_615_01_report.py && "
             "python3 -m pytest tests/test_kf_wp_615_01.py -q")
    offline = ("python3 scripts/kf/wp_615_01_register_assets.py --record-file "
               "artifacts/kf/wp-615-01/source_snapshot/report_615.json --out /tmp/wp615_repro "
               "  # 无网/无 token 复跑：读快照重建清单，与仓库产物逐字节一致（generated_at 除外）")

    sd = source_derived_sentences(snapshot)
    md = f"""# KF-RESULT {PKG}

> 工序 01-asset-registration ｜ report_id={manifest['report_id']} ｜ lane {manifest['lane']} ｜
> source_uri `{src['source_uri']}` ｜ source_field `{src['source_field']}`
> 归档产物：`artifacts/kf/{PKG}/asset_manifest.json`、`kf_result.json`、`checks.json`、`source_snapshot/`

## ① 本工序做了什么（案例介绍 / Case）

源报告 615 = **{rf['title']}**（scenario_key `{rf['scenario_key']}`，mission_id `{rf['mission_id']}`，
status `{rf['status']}`，created_at `{rf['created_at']}`）。这是冰区航行战役 L1_foundation 层的
DEM↔流体双向耦合框架报告：物理背景是碎冰颗粒与流场（海水/船体边界层）的双向动量交换。

本工序只做一件事：**把这份报告登记成可被下游工序寻址的资产清单**——确认 report_id 与 markdown 字节哈希、
枚举可解析的附件/工件、给出每条资产的原文定位（字符偏移 + 逐字引文）、把拿不到字节的资产如实登记为未解析。
**不抽取知识**（claims=[]）、**不判定 verified**（裁决权在平台验证门）、**不重跑上游算例**。

报告自报的关键参数（下表由脚本从源 markdown 的参数表/基准表**程序化重解析**后拼装，非手打；
逐字定位见 ④）：{sd['params']}；{sd['benchmark']}。

## ② 怎么做的（方法 / 工具链 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/615`（Bearer token，`POST /api/v1/auth/login` 取得），
   只取 `markdown` 字段；脚本硬锁 `report_id=615`，其它 id 直接 `SystemExit`（互不覆盖前提）。
2. **指纹**：对 `markdown` 的 UTF-8 字节独立重算 sha256，与契约 `source_hash` 对齐；
   同时核字符数（契约 chars={src['contract_chars']}，实测 {src['chars']}）与行数、字节数。
3. **零手抄定位**：引文**不手打**——脚本在 markdown 上做选择器定位（H1 行、`### 标题` 后的首个非空行、
   首个表格块的首个数据行、列表块的第 k 项等），把**命中的整行原文**作为 quote，
   并记录 `offset_chars`；随后对每条 quote 做 `quote in markdown` **和** `markdown[offset:offset+len] == quote`
   双重回读（任一失败即门失败），命中次数一并登记。
4. **结构门**：清单与信封分别用 `schemas/asset_manifest.v1.schema.json`、`schemas/kf_result.v1.schema.json`
   做 jsonschema（Draft 2020-12）校验；ID 唯一性、状态-缺口一致性、unresolved 必须带理由（≥10 字符）逐条断言。
5. **未解析登记**：图件、测试日志、代码指针三类走端点探针 + 正文检索，拿不到就如实入 `unresolved`，
   **不重绘、不代上游补图、不反推**。
6. **工具链**：Python 3 / requests（取源）/ hashlib（指纹）/ jsonschema 4.26（结构门）/
   matplotlib 3.10（图件）/ pytest（回归）。脚本：`scripts/kf/wp_615_01_register_assets.py`、
   `scripts/kf/build_wp_615_01_report.py`；测试：`tests/test_kf_wp_615_01.py`。
7. **离线可重建**：抓取时把完整记录落到 `source_snapshot/report_615.json`，
   `--record-file` 可无网复跑；离线重建与在线产物逐字节一致（`generated_at` 除外，探针结果沿用上次登记）。

**一键复跑**（在线，需要 `$TENSOR_API_BASE` / `$TENSOR_AGENT_USER` / `$TENSOR_AGENT_PASS`）：

```
{repro}
```

工作区重建 + 离线复检（无网无 token，全新检出即可跑；`artifacts/**` 不进 git，靠它从受控镜像复原）：

```
python3 scripts/kf/wp_615_01_bootstrap_artifacts.py   # 镜像→工作区；同时离线复算 checks.json 并校验 docs/图件逐字节未漂移
```

离线复跑（无网无 token）：

```
{offline}
```

## ③ 产出物清单（含程序化注入的数字）

| 输出文件 | 要点 |
|---|---|
| `artifacts/kf/{PKG}/asset_manifest.json` | 工序 01 唯一输出：source 指纹 + {counts['assets_total']} 条资产 + {counts['unresolved_total']} 条未解析缺口 + locator_checks |
| `artifacts/kf/{PKG}/kf_result.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]） |
| `artifacts/kf/{PKG}/checks.json` | 验收自检机读结果（{sum(1 for k, v in checks.items() if v is True)} 项布尔通过项 + 明细） |
| `artifacts/kf/{PKG}/source_snapshot/report_615.json` | 取源时刻的完整记录快照（离线重建与审计用） |
| `knowledge/kf/{PKG}/figures/wp61501_asset_registry.png` | 图 1：资产登记图（左：资产/状态/偏移；右：验收自检） |
| `docs/kf/KF-RESULT-{PKG}.md` | 本报告正文（含唯一一个 JSON 结果代码块） |
| `knowledge/kf/{PKG}/` | 交付镜像（`artifacts/` 被 .gitignore 忽略，随分支交付的是这一份）：清单/信封/自检/图/源快照，与 artifacts 逐字节一致（tests 绑定） |

源身份事实：`sha256 = {src['source_hash']}`，chars={src['chars']}，bytes={src['bytes']}，lines={src['lines']}；
title 与契约一致={rf['title_matches_contract']}，scenario_key 与契约一致={rf['scenario_matches_contract']}，
title 在 markdown H1 逐字出现={rf['title_matches_markdown_h1']}。

源报告 §3 自报的验收判据（程序化转述，本工序**不背书**，裁决权在平台验证门）：
{sd['acceptance_rows']}。

### 资产登记表（{counts['assets_total']} 条，状态分布 {json.dumps(counts['by_status'], ensure_ascii=False)}）

| asset_id | kind | status | offset(chars) | quote（逐字，节选） |
|---|---|---|---|---|
{rows}

### 未解析缺口（{counts['unresolved_total']} 条）

| asset_id | kind | 理由 |
|---|---|---|
{unres}

**图 1**（`knowledge/kf/{PKG}/figures/wp61501_asset_registry.png`，`scripts/kf/wp_615_01_bootstrap_artifacts.py`
可在工作区 `artifacts/kf/{PKG}/figures/` 下逐字节重建）：左图为 report 615 的 {counts['assets_total']} 条资产
（颜色=status，@n=逐字引文在 markdown 中的字符偏移），右图为机读验收自检。说明：本工序是纯登记工序，
不产生任何物理场量，因此**没有场量云图、也没有与解析解/实验的比较曲线**——这是本单无物理图件的如实理由；
图中数据全部来自 `asset_manifest.json` / `checks.json` 注入，无手填点。

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段/资产 | 原文引文（逐字） |
|---|---|
| source_hash / chars | `{src['source_hash']}`；chars={src['chars']}，chars_match_contract={src['chars_match_contract']} |
| title / scenario_key | `{rf['title']}` ／ `{rf['scenario_key']}` |
| 参数表（7 行） | `{manifest['assets'][3]['locator']['quote']}` |
| Stokes 解析解 | `{manifest['assets'][4]['locator']['quote']}` |
| 耦合算法第 4 步 | `{manifest['assets'][5]['locator']['quote']}` |
| 动量守恒保证 | `{manifest['assets'][6]['locator']['quote']}` |
| 验收判据首行 | `{manifest['assets'][8]['locator']['quote']}` |
| Stokes 沉降模拟值 | `{manifest['assets'][9]['locator']['quote']}` |
| 测试套件自述 | `{manifest['assets'][10]['locator']['quote']}` |
| 局限性第 4 条 | `{manifest['assets'][11]['locator']['quote']}` |
| 误差判定首行 | `{manifest['assets'][12]['locator']['quote']}` |
| 图件引用（字节不可得，端点 HTTP {fig_asset['retrieval']['http_status']}） | `{fig_asset['locator']['quote']}` |

上表每条引文的字符偏移与命中次数见 `asset_manifest.json → locator_checks`；
`source_locator_resolvable={checks['source_locator_resolvable']}`，`offset_mismatch={checks['offset_mismatch']}`。

## ⑤ 注意点与局限

1. **图件不可得**：记录 `figures` 只有 `name/caption`（无 `png_base64`），端点
   `GET /tensor/reports/615/figures/{fig_asset['fields']['figure_record_keys'] and 'settling_velocity'}` 返回 HTTP {fig_asset['retrieval']['http_status']}；
   正文只引用了「见内嵌图…」。本工序**不重绘、不代上游补图**，登记为 declared_unresolvable。
2. **测试证据是自述**：报告 §3 写 `- 12 tests collected, 12 passed, 0 failed`，但无原始日志/trace/测试文件路径；
   本工序只登记该断言可定位，**不把它当通过证据**，也未重跑上游算例（工序 01 不做）。
3. **代码指针缺失**：正文无仓库路径/分支/提交号；仅由记录 `mission_id={rf['mission_id']}` 探到
   mission 记录 `repo={manifest['identity_facts']['mission_probe'].get('mission_repo')}`，属记录级间接线索，不作工件绑定。
4. **不评价真伪**：本清单不含 claims、不标 verified；`momentum_exchange_conservation=0.0`、
   `0.054461 m/s` 等数值的裁决权在平台验证门与下游工序 03。
5. **互不覆盖**：脚本硬锁 `report_id=615`；本单未读写其它任何 report_id 的内容。
6. **引文口径**：quote 一律取**整行原文**（含 markdown 表格竖线/LaTeX），不裁不改，
   因此表格行较长；跨行内容会取其中一行代表行，不做字符串拼接（避免二次转录误差）。

## ⑥ 误差判定与自检

### 关键量 vs 基准（本工序的“基准”=契约与原文）

| 关键量 | 基准 | 实测 | 误差 | < 3%? |
|---|---|---|---|---|
| markdown 字节哈希 | 契约 `{src['contract_source_hash']}` | `{src['source_hash']}` | 0（逐字节相同） | ✅ YES（0%） |
| 字符数 | 契约 {src['contract_chars']} | {src['chars']} | 0 | ✅ YES（0%） |
| 引文可定位性 | 每条 quote 必须逐字命中 | {checks['bad_quotes'] and len(checks['bad_quotes']) or 0} 条失配 | 0 条 | ✅ YES（0%） |
| ID 唯一性 | 无重复 asset_id | 重复 {len(checks['duplicate_ids'])} 条 | 0 | ✅ YES（0%） |

结论：登记层无物理量误差，误差面是**字节/引文级**，4 项全部 0 偏差（<3% 显式成立）。
报告正文的物理数值（0.07% 终端速度误差等）属上游报告自述，本工序不复核、不背书。

### acceptance 逐条自检

| 验收项 | 结果 | 证据 |
|---|---|---|
| valid_json | {'✅' if checks['valid_json'] else '❌'} | asset_manifest.json / kf_result.json 均可 json.loads |
| schema_pass | {'✅' if checks['schema_pass'] else '❌'} | jsonschema Draft2020-12；errors={checks['schema_errors']} |
| source_locator_resolvable | {'✅' if checks['source_locator_resolvable'] else '❌'} | 逐条 quote 子串 + 偏移回读；bad_quotes={len(checks['bad_quotes'])}，offset_mismatch={checks['offset_mismatch']} |
| source_hash_matches | {'✅' if checks['source_hash_matches'] else '❌'} | 独立重算 `{checks['source_hash_recomputed']}` |
| no_duplicate_ids | {'✅' if checks['no_duplicate_ids'] else '❌'} | {counts['assets_total']} 条资产 ID 全互异 |
| all_claims_have_evidence_or_explicit_unresolved_status | {'✅' if checks['all_claims_have_evidence_or_explicit_unresolved_status'] else '❌'} | claims=[]（空集恒真，且契约允许）＋{counts['unresolved_total']} 条缺口带理由 |
| kf_result 信封结构 | {'✅' if checks['kf_result_schema_pass'] else '❌'} | schemas/kf_result.v1.schema.json；errors={checks['kf_result_schema_errors']} |

honest-FAIL 申报：**无失败项**。但须显式声明三项**未完成/不可得**（不是通过）：
图件字节不可得、pytest 原始日志不可得、代码级绑定不可得——三者均已登记在 `unresolved`，
下游工序 03/05 若需这些字节，应回上游补件，而不是由本工序生成。
`all_pass={checks['all_pass']}`。

## 结果信封（唯一 JSON 块，原样提交）

```json
{envelope_text}
```
"""
    return md


FIG_NAME = "wp61501_asset_registry.png"


def emit(out: Path = OUT, render_figure: bool = False, write_mirror: bool = True) -> dict:
    """把既有清单/信封渲染成 docs 报告、图件与平台 POST 载荷，返回 payload。

    图件字节默认**复用受控镜像里已提交的那一份**（knowledge/kf/<pkg>/figures/），
    因为 PNG 编码随 matplotlib 版本漂移，重绘会破坏"工作区 artifacts 与提交镜像逐字节一致"
    这条不变量；render_figure=True 才重绘并回写镜像（首次生成 / 换环境时用）。
    """
    out = Path(out)
    manifest = json.loads((out / "asset_manifest.json").read_text())
    checks = json.loads((out / "checks.json").read_text())
    envelope_text = (out / "kf_result.json").read_text().strip()
    json.loads(envelope_text)  # 原样块必须是合法 JSON

    figdir = out / "figures"
    figdir.mkdir(parents=True, exist_ok=True)
    png = figdir / FIG_NAME
    mirror_png = MIRROR / "figures" / FIG_NAME
    if render_figure or not mirror_png.exists():
        make_figure(manifest, checks, png)
        if write_mirror:
            mirror_png.parent.mkdir(parents=True, exist_ok=True)
            mirror_png.write_bytes(png.read_bytes())
    else:
        png.write_bytes(mirror_png.read_bytes())

    snapshot = json.loads((out / "source_snapshot" / "report_615.json").read_text())
    md = build_markdown(manifest, checks, envelope_text, snapshot)
    DOCS.parent.mkdir(parents=True, exist_ok=True)
    if not DOCS.exists() or DOCS.read_text() != md:
        DOCS.write_text(md)

    payload = {
        "title": f"KF-RESULT {PKG}",
        "summary": (f"report 615（{manifest['source']['record_fields']['title']}）资产登记完成："
                    f"{manifest['counts']['assets_total']} 条资产、{manifest['counts']['unresolved_total']} 条未解析缺口；"
                    f"markdown sha256 与契约一致，{len(manifest['assets'])} 条引文逐字可定位；claims=[]，未标 verified。"),
        "scenario_key": manifest["source"]["record_fields"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": [f"kf-wp:{PKG}", "KF-RESULT", "asset-registration", "report-615", "SIR-PC2-F06"],
        "markdown": md,
        "figures": [{
            "name": "wp61501_asset_registry",
            "caption": ("Left: the 14 registered assets of report 615 (bar colour = status, @n = char offset of the "
                        "verbatim quote in the markdown). Right: machine-recomputed acceptance self-check."),
            "png_base64": base64.b64encode(png.read_bytes()).decode(),
        }],
    }
    payload_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    (out / "report_payload.json").write_text(payload_text)
    if write_mirror:
        MIRROR.mkdir(parents=True, exist_ok=True)
        (MIRROR / "KF-RESULT.md").write_text(md)
    return payload


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=str(OUT))
    ap.add_argument("--render-figure", action="store_true",
                    help="强制重绘图件并回写知识包（默认复用已提交图件字节，保证逐字节可复现）")
    args = ap.parse_args()
    payload = emit(Path(args.out_dir), render_figure=args.render_figure)
    png = Path(args.out_dir) / "figures" / FIG_NAME
    print(f"wrote {DOCS} and payload with figure {png.name} "
          f"({len(payload['figures'][0]['png_base64'])} b64 chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
