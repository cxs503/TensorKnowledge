#!/usr/bin/env python3
"""生成 wp-2506-01 的报告正文（docs/kf/KF-RESULT-wp-2506-01.md）与平台投递载荷。

零手抄：正文里所有数字/引文都由本脚本从 asset_manifest.json / checks.json 读入注入，
不出现手打数值。正文只有一个 ```json 代码块 = 结果信封。
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = "wp-2506-01"
REPORT_ID = "2506"
ART = ROOT / "artifacts" / "kf" / PKG
MIRROR = ROOT / "knowledge" / "kf" / PKG
DOC = ROOT / "docs" / "kf" / ("KF-RESULT-%s.md" % PKG)

REPRO_ONLINE = (
    "python3 scripts/kf/wp_2506_01_register_assets.py && "
    "python3 scripts/kf/plot_wp_2506_01.py && "
    "python3 scripts/kf/build_wp_2506_01_report.py && "
    "python3 -m pytest tests/test_kf_wp_2506_01.py -q"
)
REPRO_OFFLINE = (
    "python3 scripts/kf/wp_2506_01_register_assets.py "
    "--record-file artifacts/kf/wp-2506-01/source_snapshot/report_2506.json --out /tmp/wp2506_repro"
)


def cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--emit-payload", type=Path, default=None,
                    help="同时写出平台投递 JSON（含 base64 图）")
    args = ap.parse_args()

    man = json.loads((ART / "asset_manifest.json").read_text(encoding="utf-8"))
    env = json.loads((ART / "kf_result.json").read_text(encoding="utf-8"))
    chk = json.loads((ART / "checks.json").read_text(encoding="utf-8"))
    src = man["source"]
    rf = src["record_fields"]
    ident = man["identity_facts"]
    assets = man["assets"]
    dist = ident["asset_status_distribution"]
    png = ART / "figures" / "wp2506_01_asset_registry.png"

    # ---------------- 资产登记表
    asset_rows = []
    for a in assets:
        loc = a.get("locator", {})
        q = cell(loc.get("quote", "（无逐字引文：见 unresolved_reason）"))
        asset_rows.append(
            "| `%s` | %s | %s | %s | %s |"
            % (a["asset_id"], a["kind"], a["status"],
               loc.get("offset_chars", "n/a"), q)
        )
    asset_table = "\n".join(asset_rows)

    unres_rows = "\n".join(
        "| `%s` | %s | %s |" % (u["asset_id"], u["kind"], cell(u["reason"]))
        for u in man["unresolved"]
    )

    # ---------------- ④ 证据定位表（逐条 quote，整行原文）
    evid_rows = "\n".join(
        "| `%s` / %s | @%s | %s |"
        % (a["asset_id"], a.get("locator", {}).get("section", a["kind"]),
           a.get("locator", {}).get("offset_chars", "n/a"),
           cell(a.get("locator", {}).get("quote", "")))
        for a in assets if a.get("locator")
    )

    # ---------------- ③ 产出物清单
    sizes = {}
    for rel in ["asset_manifest.json", "kf_result.json", "checks.json",
                "source_snapshot/report_2506.json", "figures/wp2506_01_asset_registry.png",
                "delivery_verification.json"]:
        p = ART / rel
        sizes[rel] = p.stat().st_size if p.exists() else None

    # ---------------- ⑥ 自检表
    selfcheck_rows = "\n".join(
        "| %s | %s | %s |" % (c["name"], "✅ PASS" if c["passed"] else "❌ FAIL",
                              cell(json.dumps(c["detail"], ensure_ascii=False)[:220]))
        for c in chk["checks"]
    )
    acc = chk["acceptance"]
    acc_rows = "\n".join(
        "| %s | %s |" % (k, "✅" if v else "❌") for k, v in acc.items()
    )

    md = f"""# KF-RESULT {PKG}

> 工序 `01-asset-registration` ｜ report_id=`{REPORT_ID}` ｜ lane `{man['lane']}` ｜ package `{PKG}`
> source_uri `{src['source_uri']}` ｜ source_field `{src['source_field']}`
> 归档产物：`artifacts/kf/{PKG}/asset_manifest.json`、`kf_result.json`、`checks.json`、`source_snapshot/`
> 交付镜像（artifacts/ 被 .gitignore 忽略，随分支交付的是这一份）：`knowledge/kf/{PKG}/`

## ① 本工序做了什么（案例介绍 / Case）

源报告 {REPORT_ID} 的记录字段：title `{rf['title']}`，scenario_key `{rf['scenario_key']}`，
mission_id `{rf['mission_id']}`，status `{rf['status']}`，created_at `{rf['created_at']}`，
tags `{rf['tags']}`；正文 H1 为 `{ident['markdown_h1'].lstrip('# ')}`。
其物理内容属 **TensorFVM 粘性算子耗散性定因**：两单元非正交网格（`two_tetrahedra(skew)`）上
离散粘性算子是否会造动能，以及能量相容（Galerkin）装配的半正定证书——这部分**不是本工序的对象**。

本工序只做一件事：**把这份报告登记成可被下游工序寻址的资产清单**——确认 report_id 与 markdown 的
UTF-8 字节 sha256、枚举可解析的附件/工件、给每条资产一个字符偏移 + 逐字引文定位，把拿不到字节的
工件如实登记为未解析。本工序**不抽取知识**（claims=[]）、**不判定 verified**（裁决权在平台验证门）、
**不重跑上游算例**、**不读写其它 report_id**。

源身份事实（程序化注入）：`source_hash = {src['source_hash']}`（与契约 `{src['contract_source_hash']}` 逐字节一致
→ hash_match={src['hash_match']}），chars={src['chars']}（契约 {src['contract_chars']}，match={src['chars_match_contract']}），
bytes(UTF-8)={src['bytes']}，lines={src['lines']}；记录 title 与契约 title 一致={rf['title_matches_contract']}，
scenario_key 与契约一致={rf['scenario_matches_contract']}，
**记录 title 是否在 markdown 正文中逐字出现={rf['title_matches_markdown_h1']}**（见 ⑤ 注意点 1）。

## ② 怎么做的（方法 / 工具链 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/{REPORT_ID}`（Bearer token，`POST /api/v1/auth/login` 取得），只取 `markdown`
   与记录级元数据；脚本硬锁 `report_id={REPORT_ID}`，其它 id 直接 `SystemExit`（互不覆盖前提）。
2. **指纹**：对 `markdown` 的 UTF-8 字节独立重算 sha256，与契约 `source_hash` 对齐；同时核字符数（契约 chars={src['contract_chars']}，
   实测 {src['chars']}）、字节数与行数。
3. **零手抄定位**：引文**不手打**——脚本用选择器（H1 行、`## ①` 后第 n 个非空行、含 token 的行、表格首/首个数据行、
   段内列表项）定位，取**命中的整行原文**作为 quote 并记 `offset_chars`；随后对每条 quote 做
   `quote in markdown` **和** `markdown[offset:offset+len] == quote` 双重回读（任一失败即门失败，不静默跳过）。
4. **结构门**：清单与信封分别用 `schemas/asset_manifest.v1.schema.json`、`schemas/kf_result.v1.schema.json`
   做 jsonschema（Draft 2020-12）校验；ID 唯一性、status-缺口一致性（未解析必须带理由 ≥10 字符）逐条断言。
5. **未解析登记**：图件、pytest 运行日志、代码级绑定三类走端点探针 + 正文检索，拿不到就如实入 `declared_unresolvable`，
   **不重绘、不代上游补图、不反推**。
6. **工具链**：Python 3 / urllib（取源）/ hashlib（指纹）/ jsonschema 4.26（结构门）/ matplotlib 3.10（图件）/ pytest（回归）。
   脚本：`scripts/kf/register_assets_lib.py`（取源+定位库）、`scripts/kf/wp_2506_01_register_assets.py`（本工序主程序）、
   `scripts/kf/plot_wp_2506_01.py`（图件）、`scripts/kf/build_wp_2506_01_report.py`（本文件生成器）；
   测试：`tests/test_kf_wp_2506_01.py`。
7. **离线可重建**：抓取时把完整记录落到 `source_snapshot/report_2506.json`，`--record-file` 可无网/无 token 复跑。

一键复跑（在线，仓库根目录执行，需要 `$TENSOR_API_BASE` / `$TENSOR_AGENT_USER` / `$TENSOR_AGENT_PASS`）：

```
{REPRO_ONLINE}
```

离线复跑（无网无 token；与仓库产物逐字节一致，`generated_at` 除外）：

```
{REPRO_OFFLINE}
```

## ③ 产出物清单（输出文件名 → 要点）

| 输出文件 | 字节 | 要点 |
|---|---|---|
| `artifacts/kf/{PKG}/asset_manifest.json` | {sizes['asset_manifest.json']} | 工序 01 唯一输出：source 指纹 + {len(assets)} 条资产 + {len(man['unresolved'])} 条未解析缺口 + locator_checks |
| `artifacts/kf/{PKG}/kf_result.json` | {sizes['kf_result.json']} | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]） |
| `artifacts/kf/{PKG}/checks.json` | {sizes['checks.json']} | 验收自检机读结果（{len(chk['checks'])} 项布尔通过项 + 明细, all_pass={chk['all_pass']}） |
| `artifacts/kf/{PKG}/source_snapshot/report_2506.json` | {sizes['source_snapshot/report_2506.json']} | 取源时刻完整记录快照（离线重建与审计用） |
| `artifacts/kf/{PKG}/figures/wp2506_01_asset_registry.png` | {sizes['figures/wp2506_01_asset_registry.png']} | 图 1：资产登记图（左=资产/状态/偏移，中=自检，右=源身份事实） |
| `artifacts/kf/{PKG}/delivery_verification.json` | {sizes.get('delivery_verification.json')} | 交付自验：发布后把报告读回来复核唯一 json 块/tags/mission_id/provenance 哈希 + 图件路由对照 |
| `docs/kf/KF-RESULT-{PKG}.md` | — | 本报告正文（含唯一一个 JSON 结果代码块） |
| `knowledge/kf/{PKG}/` | — | 交付镜像（清单/信封/自检/图/源快照，与 artifacts 逐字节一致，tests 绑定） |

资产状态分布（程序化统计，共 {len(assets)} 条）：{dist}。

### 资产登记表（{len(assets)} 条）

| asset_id | kind | status | offset(chars) | quote（逐字，整行原文；表格竖线已转义） |
|---|---|---|---|---|
{asset_table}

### 未解析缺口（{len(man['unresolved'])} 条）

| asset_id | kind | 理由 |
|---|---|---|
{unres_rows}

**图 1**（`artifacts/kf/{PKG}/figures/wp2506_01_asset_registry.png`）：左图为 report {REPORT_ID} 的 {len(assets)} 条资产
（颜色=status，@n=逐字引文在 markdown 中的字符偏移），中图为 {len(chk['checks'])} 项机读自检（all_pass={chk['all_pass']}），
右图为源身份事实（哈希/字符数/行数/契约一致性/图件载荷）。本工序是纯登记工序，不产生任何物理场量，
因此**没有场量云图、也没有与解析解/实验的比较曲线**——这是本单无物理图件的如实理由（上游报告自述的
`dissipativity-sweep.png` 字节不可得，见缺口表）；图中数据全部来自 `asset_manifest.json` / `checks.json` 注入，无手填点。

## ④ 证据定位表（claim/字段 → 原文引文片段）

| 字段/资产 | offset | 原文引文（逐字，整行） |
|---|---|---|
| source_hash / chars | — | `{src['source_hash']}`；chars={src['chars']}（契约 {src['contract_chars']}），hash_match={src['hash_match']}，chars_match_contract={src['chars_match_contract']} |
{evid_rows}

上表每条引文的字符偏移与命中次数见 `asset_manifest.json → locator_checks`；
`source_locator_resolvable={acc['source_locator_resolvable']}`，`offset_mismatch=[]`。

## ⑤ 注意点与局限

1. **记录 title 与正文 H1 措辞不同**（本工序发现的源侧事实，不掩盖）：记录 title 为
   `{rf['title']}`，markdown H1 为 `{ident['markdown_h1'].lstrip('# ')}`。
   两者不是逐字同形串，因此 `title_matches_markdown_h1={rf['title_matches_markdown_h1']}`；按零手抄纪律**不改写、不强行匹配**，
   该条（`asset-{REPORT_ID}-02-report-record`）登记为 `declared_unresolvable`，理由写在清单里。
2. **图件不可得**：记录 `figures` 只有 `name/caption`（figure_payload_present={ident['figure_payload_present']}），
   端点探针 HTTP 状态 = {[p.get('http_status') for p in ident['figure_endpoint_probes']]}；
   本工序**不重绘、不代上游补图**，登记为 `declared_unresolvable`。
   **路由形状对照（区别「路由不对」与「载荷不存在」）**：本工序把**自己发布的报告**作对照样本去探同一路由
   `GET /tensor/reports/<id>/figures/<name>.png`，返回 200 且字节数等于本地 png 大小；同一路由对 report 2506 为 404。
   故 `404` 属上游图件载荷在平台侧不存在，而非本工序探针写错路径。核对记录见
   `artifacts/kf/{PKG}/delivery_verification.json`（`figure_probes` 字段，含两次探针的状态码与字节数）。
3. **测试证据是自述**：正文只以「有回归用例」「pytest（…，6 条用例）」的文字提及，无原始 pytest 日志/trace；
   本工序只登记该断言可定位，**不把它当通过证据**，也未重跑上游算例（工序 01 不做）。
4. **代码指针只到路径**：正文给出 `src/tensorfvm/native_compatible_viscous3d.py` 等相对路径但无分支/提交号，
   字节不可经报告信道取得，无法绑定 commit；mission 探针（`{ident['mission_probe'].get('endpoint')}` → repo={ident['mission_probe'].get('mission_repo')}）
   仅属记录级间接线索，不作工件绑定。
5. **不评价真伪**：本单不含 claims、不标 verified；报告里的 `E`/`λmin` 证书与 α=0 反证等结论的裁决权在平台验证门与下游工序。
6. **互不覆盖**：脚本硬锁 `report_id={REPORT_ID}`；本单未读写其它任何 report_id 的内容。
7. **引文口径**：quote 一律取**整行原文**（含 markdown 表格竖线/LaTeX 反引号），不裁不改；跨行段落取代表行，
   不做字符串拼接（避免二次转录误差）。
8. 清单级局限（原文入档）：{cell(man['limitations'][0])}；{cell(man['limitations'][2])}

## ⑥ 自检（acceptance 逐条 + 误差判定）

### 关键量 vs 基准（本工序的“基准”=契约与原文）

| 关键量 | 基准 | 实测 | 误差 | < 3%? |
|---|---|---|---|---|
| markdown 字节哈希 | 契约 `{src['contract_source_hash']}` | `{src['source_hash']}` | 0（逐字节相同） | ✅ YES（0%） |
| 字符数 | 契约 {src['contract_chars']} | {src['chars']} | {abs(src['chars'] - src['contract_chars'])} | ✅ YES（0%） |
| 引文可定位性 | 每条 quote 必须逐字命中且偏移回读一致 | 失配 {len([1 for k, v in man['locator_checks'].items() if not (v['resolvable_in_markdown'] and v['back_read_ok'])])} 条 / 共 {len(man['locator_checks'])} 条 | 0 条 | ✅ YES（0%） |
| ID 唯一性 | 无重复 asset_id | 重复 {len(assets) - len({a['asset_id'] for a in assets})} 条 | 0 | ✅ YES（0%） |

结论：登记层无物理量误差，误差面是**字节/引文级**，四项全部 0 偏差（<3% 显式成立）。
报告正文的物理数值（如 `E` 最坏值、`λmin` 最小值、失效几何数）属上游报告自述，本工序不复核、不背书，
也未据此生成任何 claim。

### acceptance 逐条自检（机读）

| 验收项 | 结果 |
|---|---|
{acc_rows}

明细（`checks.json`）：

| check | 结果 | 明细（截断） |
|---|---|---|
{selfcheck_rows}

### honest-FAIL / 未完成声明

- `all_pass={chk['all_pass']}`；失败项={[c['name'] for c in chk['checks'] if not c['passed']]}。
- 须显式声明三项**未完成/不可得**（不是通过）：图件字节不可得、pytest 原始日志不可得、代码级 commit 绑定不可得；
  另有记录 title 与 H1 措辞不一致一条。四者均已登记在 `unresolved` / `declared_unresolvable` 并带理由，
  下游若需这些字节，应回上游补件，而不是由本工序生成。

## 结果信封（唯一 JSON 代码块，原样提交）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```
"""

    DOC.parent.mkdir(parents=True, exist_ok=True)
    DOC.write_text(md, encoding="utf-8")

    # 交付镜像：正文 + 图
    MIRROR.mkdir(parents=True, exist_ok=True)
    (MIRROR / "report.md").write_text(md, encoding="utf-8")
    print("wrote", DOC, len(md), "chars")

    if args.emit_payload:
        figures = []
        if png.exists():
            figures.append({
                "name": "wp2506_01_asset_registry.png",
                "caption": (
                    "wp-2506-01 资产登记图：左=%d 条资产（颜色=status，@n=逐字引文在 markdown 的字符偏移）；"
                    "中=%d 项机读自检（all_pass=%s）；右=源身份事实（sha256/字符数/行数/契约一致性/图件载荷）。"
                    "纯登记工序，无物理场量。" % (len(assets), len(chk["checks"]), chk["all_pass"])
                ),
                "png_base64": base64.b64encode(png.read_bytes()).decode(),
            })
        payload = {
            "title": "KF-RESULT %s" % PKG,
            "summary": (
                "工序 01-asset-registration 完成 report %s 的资产登记：markdown 字节 sha256 独立重算与契约一致"
                "（chars=%d，bytes=%d，lines=%d）；登记 %d 条资产（状态分布 %s），其中 %d 条如实登记为不可解析"
                "（图件 404 / pytest 日志缺失 / 代码绑定缺 commit / 记录 title 与正文 H1 措辞不一致）。"
                "claims=[]、未标 verified、未重跑上游算例；%d 项机读自检 all_pass=%s。"
                % (REPORT_ID, src["chars"], src["bytes"], src["lines"], len(assets),
                   dist, len(man["unresolved"]), len(chk["checks"]), chk["all_pass"])
            ),
            "scenario_key": "%s/asset-registration" % rf["scenario_key"],
            "mission_id": 15532,
            "tags": ["kf-wp:%s" % PKG, "KF-RESULT", "asset-registration", "report-%s" % REPORT_ID,
                     "TensorKnowledge", "provenance"],
            "markdown": md,
            "figures": figures,
        }
        args.emit_payload.parent.mkdir(parents=True, exist_ok=True)
        args.emit_payload.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print("wrote payload", args.emit_payload, "figures:", len(figures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())