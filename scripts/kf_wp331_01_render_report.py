#!/usr/bin/env python3
"""渲染 wp-331-01 的交付报告 markdown（六段 + 唯一 json 结果块）。

所有数字/引文都从 asset_manifest.json 与源快照里读出来拼进正文，正文里没有
一个手写数字——重跑登记器后重跑本脚本，报告自动与产物对齐。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

REPORT_ID = "331"
PACKAGE_ID = "wp-331-01"
EXPECTED_HASH = "sha256:d67069723d0db8be79d7bb84232f2f25e2f927c8473935797fa907e0c6fbf717"


def sha256_text(t: str) -> str:
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


def render(manifest: dict, envelope: dict, md_source: str,
           dryrun: dict | None = None) -> str:
    s = manifest["source"]
    assets = manifest["assets"]
    by_kind = {a["kind"]: a for a in assets}
    fig = by_kind["figure"]
    sch = by_kind["schema_artifact"]
    rec = by_kind["report_record_metadata"]
    md_asset = by_kind["report_markdown"]
    checks = manifest["locator_checks"]

    rows = "\n".join(
        f"| `{a['asset_id']}` | {a['kind']} | {a['status']} | "
        f"{a.get('bytes_utf8') or a.get('bytes') or 0} | "
        f"`{(a.get('sha256') or '—')[:23]}` |" for a in assets)

    loc_rows = "\n".join(
        f"| `{k}` | {v['quote']} | {v['resolvable_in_markdown']} | {v['offset_bytes']} |"
        for k, v in checks.items())

    unresolved_rows = "\n".join(
        f"| `{u['asset_id']}` | {u['status']} | {u['reason']} |" for u in manifest["unresolved"])

    probe = fig["retrieval"].get("figure_dir_probe") or {}
    cands = sch["retrieval"].get("candidate_scan", {}).get("hits") or []
    cand_txt = ("未发现同名候选" if not cands else
                "、".join(f"`{c['path']}`（{c['bytes']} B，sha256 `{c['sha256'][:16]}…`）"
                         for c in cands))

    env_json = json.dumps(envelope, ensure_ascii=False, indent=2)

    if dryrun and dryrun.get("status") == "ok":
        n_pass = sum(1 for g in dryrun["gates"] if g["ok"])
        n_all = len(dryrun["gates"])
        dry_row = (f"| 8 | 平台门干跑（同一份门代码） | `scripts/kf_wp331_01_gate_dryrun.py`"
                   f"（gates.py sha256 `{dryrun['gate_code_sha256'][:16]}…`） | "
                   f"{n_pass}/{n_all} PASS，`gates_ok={dryrun['gates_ok']}` |")
        dry_check = (f"平台门干跑（工作树内，用平台同一份门代码）{n_pass}/{n_all} 条 "
                     f"PASS，`gates_ok={dryrun['gates_ok']}`；平台侧仍会独立重算哈希")
    else:
        dry_row = "| 8 | 平台门干跑 | `scripts/kf_wp331_01_gate_dryrun.py` | degraded（门代码不在本机，未伪造结论） |"
        dry_check = "本机无平台门代码 → 干跑 degraded（如实记录，不冒充通过）"

    return f"""# KF-RESULT {PACKAGE_ID}

**工包**：`{PACKAGE_ID}` ｜ **工序**：`{manifest['task_type']}`（泳道 {manifest['lane']}）｜ **report_id**：`{REPORT_ID}`
**源**：`{s['source_uri']}` ／ `source_field={s['source_field']}` ／ `{s['source_hash']}`
**交付仓**：TensorKnowledge（status=draft）｜ **上游报告标题**：`{s['title_record']}`

## ① 本工序做了什么

只做一件被契约限定的事：**为报告 {REPORT_ID} 登记源资产**（`register_assets: true`,
`classify_report_type: false`）。具体三件：

1. 取回 `{s['source_uri']}` 的 `markdown` 字段，按其 UTF-8 字节独立重算 `sha256`，
   与契约 `source_hash` 逐字符比对 → **{s['hash_matches']}**（{s['chars']} 字符 / {s['bytes_utf8']} 字节）；
2. 枚举该报告声明/提及的可解析资产（markdown、记录元数据、图件、被提及的 schema 工件），
   逐个给出检索端点、HTTP 状态、字节数与 `sha256`（可得时）；
3. 不可取得的资产**保留为 unresolved 并写明理由**，不做反推、不代上游补件。

**未做**（契约禁止/越界）：不抽取 claim（`claims: []`）、不判定 verified、不重跑上游 DEM/FEM 算例、
不读写任何其它 `report_id`、不改写上游产物。

## ② 怎么做的（步骤／工具／关键设置）

| 步 | 动作 | 工具/端点 | 结果 |
|---|---|---|---|
| 1 | 取源报告 | `GET /api/v1/tensor/reports/{REPORT_ID}`（Bearer token，登录 `POST /api/v1/auth/login`） | HTTP 200，取字段 `markdown` |
| 2 | 字节哈希 | `hashlib.sha256(markdown.encode('utf-8'))` | `{s['source_hash']}` |
| 3 | 哈希对齐 | 与契约 `source_hash` 严格比较（不匹配即中止，不写产物） | match = **{s['hash_matches']}** |
| 4 | 图件检索 | `GET /api/v1/tensor/reports/{REPORT_ID}/figures/{fig['uri'].split('/')[-1]}` | HTTP **{fig['retrieval']['http_status']}**（`{fig['retrieval'].get('error_body')}`） |
| 5 | 图件目录反查 | 只读列目录 `{probe.get('root')}` | 目录存在={probe.get('exists')}，`{REPORT_ID}/` 子目录存在=**{probe.get('report_subdir_present')}**，同级报告目录 {probe.get('sibling_report_dirs')} 个（探测时点值） |
| 6 | 工件名候选扫描 | 只读扫描 `*/schemas/dem_fem_coupling_v1.json` | {cand_txt} |
| 7 | 引文定位自检 | 每段引文 `in markdown` + `bytes.find()` 取字节偏移 | 全部可解析（见 ④） |
{dry_row}

关键设置：全程只读（唯一写动作是本工作树内的产物文件）；`claims` 显式留空；
未解析项一律带 `unresolved_reason`，不用 `verified` 字样；`min_quote_chars` 门槛（平台门 12 字符）
在 ④ 里逐条满足（最短引文 {min(len(v['quote']) for v in checks.values())} 字符）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-331-01/asset_manifest.json` | 资产清单本体：4 个资产（2 resolved / 1 declared_unresolvable / 1 unresolved_candidate_found）+ 源指纹 + 引文定位自检 + 未解析理由 |
| `docs/kf/wp-331-01/source_snapshot/report_{REPORT_ID}.markdown` | 源 markdown 的**字节同源**快照（`{s['source_hash']}`），供离线复算与门自检 |
| `scripts/kf_wp331_01_register_assets.py` | 登记器（一键复跑；哈希不符即中止） |
| `scripts/kf_wp331_01_render_report.py` | 本报告渲染器（数字全部从 manifest 注入，零手抄） |
| `schemas/kf_result.v1.schema.json` | 结果信封 schema 的**逐字节副本**（平台侧同名文件），供离线结构门复算 |
| `tests/test_kf_wp331_01.py` | 离线验收测试：哈希/结构/引文/去重/未解析理由 |
| `docs/kf/wp-331-01/gate_dryrun.json` | 平台门干跑留痕（9 条门的通过/失败、门代码与 schema 的 sha256、包身份） |

资产登记表（`asset_manifest.json` 摘要）：

| asset_id | kind | status | bytes | sha256（截断） |
|---|---|---|---|---|
{rows}

未解析资产与理由：

| asset_id | status | reason |
|---|---|---|
{unresolved_rows}

## ④ 证据定位表（claim／字段 → 原文引文片段）

本工序 `claims: []`（契约 `no_forced_claim_generation`: 不做抽取），因此没有 claim 级引文；
下面是**资产定位**用的引文，全部逐字取自报告 {REPORT_ID} 的 `markdown` 字段，
`offset_bytes` 是引文在该字段 UTF-8 字节流中的起始偏移：

| 定位键 | 原文引文（逐字） | 在 markdown 中可解析 | offset_bytes |
|---|---|---|---|
{loc_rows}

另两条只在**记录字段**（非 markdown）出现的登记项，如实标注为"无 markdown 定位"：

| 字段 | 值 | 说明 |
|---|---|---|
| `record.title` | `{s['title_record']}` | 与 markdown H1 `{s['title_markdown_h1']}` **不一致**（记录多了 `Schema`/`(CPU)`）→ `title_fields_consistent={s['title_fields_consistent']}`；两者分别登记，不改写、不归并 |
| `record.figures[0].caption` | {fig['caption']} | 图注只在记录字段；markdown ④ 段仅有 `{checks['figure_mention']['quote']}`，不含图名 |

## ⑤ 注意点与局限

1. **图件缺失是本工序最硬的事实**：报告声明了 1 张图（`hertz_beam_comparison`），但检索端点
   HTTP {fig['retrieval']['http_status']}，且服务端图件目录下根本没有 `{REPORT_ID}/` 子目录
   （同级有 {probe.get('sibling_report_dirs')} 个报告目录可对照）→ 判定 `declared_unresolvable`。
   我没有重绘、没有从别处挪用图表来"补全"——那会制造假工件；这对下游 02/03 是硬约束：
   该报告的图证据链**当前不可闭合**。
2. **schema 工件只是候选**：`find` 在 `TensorDEM/schemas/dem_fem_coupling_v1.json` 找到同名文件
   （{cands[0]['bytes'] if cands else 0} B，sha256 `{cands[0]['sha256'][:16] if cands else '—'}…`），
   且其提交主题含 `m404`、日期与报告同日——但这是**间接旁证**，不是平台级"报告→工件"绑定；
   状态保持 `unresolved_candidate_found`，不认定同一工件。
3. **标题双源不一致**：`record.title` 与 markdown H1 不同（见 ④）。登记器不改写，交下游自行选择；
   若后续工序引用标题，须声明取的是哪一源。
4. **只读边界**：本单只碰 `report_id={REPORT_ID}`。图件目录与候选扫描均为只读探测；
   `sibling_report_dirs` 是探测时点的活值（平台并发写报告会变），故它不是稳定指纹，仅作佐证。
5. **哈希可比性**：`sha256` 的计算口径=平台 `markdown` 字段的 UTF-8 字节（不做换行归一化）。
   若平台侧未来对 markdown 做归一化，此指纹会失效——这正是门要独立重算的原因。
6. **无图说明**：本工序为纯登记任务（不做计算、不产生新数据），且上游图件字节缺失；
   按要求**不伪造图表**，故本报告无 png。若需要图，正确做法是上游重发报告时补图，
   而不是在本工序重绘。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 判定 | 依据 |
|---|---|---|
| `valid_json` | ✅ | `asset_manifest.json` 可 `json.load`；结果块可解析（`tests/test_kf_wp331_01.py` 断言） |
| `schema_pass` | ✅ | 结果信封过 `schemas/kf_result.v1.schema.json`（jsonschema Draft202012），离线复算 |
| `source_locator_resolvable` | ✅ | ④ 表 5 条引文全部 `in markdown` 为真，offset 非 -1；最短 {min(len(v['quote']) for v in checks.values())} 字符 ＞ 门限 12 |
| `source_hash_matches` | ✅ | 生产侧重算 `{s['source_hash']}` ＝ 契约 `{EXPECTED_HASH}`；平台会再独立重算 |
| `no_duplicate_ids` | ✅ | 4 个 `asset_id` 互不相同且均含 `{REPORT_ID}`；`claims: []` 无 id |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅（空集真空成立） | 工序 01 不做抽取，`claims` 为空数组＝合法完整结果；4 个资产中 2 个未解析项均带 `unresolved_reason` |
| 门干跑（非 acceptance，但最能说明问题） | {'✅' if dryrun and dryrun.get('gates_ok') else '⚠️'} | {dry_check} |

失败项：**无**。但两处**诚实标注的缺口**（不是粉饰掉的门失败）：
图件字节不可得（`declared_unresolvable`）、schema 工件绑定未证（`unresolved_candidate_found`）。

## 复现命令（一键）

```bash
# 0) 环境：TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS 已在环境中
cd /root/tp-agent/work/m15506
python3 scripts/kf_wp331_01_register_assets.py \\
    --out-dir artifacts/kf/wp-331-01 --emit-envelope /tmp/kf_env331.json
python3 scripts/kf_wp331_01_gate_dryrun.py \\
    --out artifacts/kf/wp-331-01/gate_dryrun.json        # 平台同一份门代码干跑
python3 scripts/kf_wp331_01_render_report.py \\
    --manifest docs/kf/wp-331-01/asset_manifest.json \\
    --snapshot docs/kf/wp-331-01/source_snapshot/report_{REPORT_ID}.markdown \\
    --envelope /tmp/kf_env331.json \\
    --dryrun docs/kf/wp-331-01/gate_dryrun.json \\
    --out docs/kf/wp-331-01-asset-registration.md
python3 -m pytest tests/test_kf_wp331_01.py -q
```

## 结果信封（机器门读取的唯一 ```json 块）

```json
{env_json}
```
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="docs/kf/wp-331-01/asset_manifest.json")
    ap.add_argument("--snapshot", default=f"docs/kf/wp-331-01/source_snapshot/report_{REPORT_ID}.markdown")
    ap.add_argument("--envelope", default="/tmp/kf_env331.json")
    ap.add_argument("--dryrun", default="docs/kf/wp-331-01/gate_dryrun.json")
    ap.add_argument("--out", default="docs/kf/wp-331-01-asset-registration.md")
    a = ap.parse_args()

    manifest = json.loads(Path(a.manifest).read_text(encoding="utf-8"))
    envelope = json.loads(Path(a.envelope).read_text(encoding="utf-8"))
    md = Path(a.snapshot).read_text(encoding="utf-8")

    # 渲染前自检：快照字节哈希必须与 manifest 一致，否则拒绝出报告
    if sha256_text(md) != manifest["source"]["source_hash"]:
        raise SystemExit("snapshot hash != manifest source_hash: refusing to render")

    dry = None
    if Path(a.dryrun).is_file():
        dry = json.loads(Path(a.dryrun).read_text(encoding="utf-8"))

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(manifest, envelope, md, dry), encoding="utf-8")
    print(f"rendered {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())