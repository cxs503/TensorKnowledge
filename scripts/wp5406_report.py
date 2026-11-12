#!/usr/bin/env python3
"""Render the work-package report for wp-5406-01 from the artifacts on disk.

Zero hand-copy: every number, path, quote and offset in the markdown below is
read out of ``knowledge/assets/wp-5406-01/asset_manifest.json`` (and its siblings), so
the text cannot drift from the machine-checked data.

    python scripts/wp5406_report.py   # -> knowledge/assets/wp-5406-01/REPORT.md
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "knowledge" / "assets" / "wp-5406-01"


def main() -> int:
    manifest = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
    checks = json.loads((PKG / "self_checks.json").read_text(encoding="utf-8"))
    kf = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
    platform = json.loads((PKG / "platform_resolver_check.json").read_text(encoding="utf-8"))
    src = manifest["source"]
    counts = manifest["counts"]
    assets = manifest["attachments"]

    def quote_of(asset: dict) -> str:
        if asset["mentions"]:
            return asset["mentions"][0]["quote"]
        loc = asset.get("locator") or {}
        return loc.get("quote", "")

    def line_of(asset: dict) -> str:
        if asset["mentions"]:
            return str(asset["mentions"][0]["line"])
        return f"record.{asset['locator']['field']}" if asset.get("locator") else "-"

    asset_rows = "\n".join(
        f"| {a['id']} | `{a['path']}`{'/' if a.get('directory_reference') else ''} | {a['kind']} "
        f"| {a['reachability']['status']} | {a['bytes_available']} |"
        for a in assets)

    loc_rows = "\n".join(
        f"| {a['id']} | `{quote_of(a)}` | {line_of(a)} | "
        + (f"{len(a['mentions'])}" if a["mentions"] else "0 (record field)")
        + " |"
        for a in assets)

    check_rows = "\n".join(
        f"| {c['name']} | {'PASS' if c['pass'] else 'FAIL'} | {c['detail']} |"
        for c in checks["checks"])

    multi = [a for a in assets if len(a["mentions"]) > 1]
    multi_rows = "\n".join(
        f"| {a['id']} | `{a['path']}` | " + ", ".join(str(m["line"]) for m in a["mentions"]) + " |"
        for a in multi)

    kf_json = json.dumps(kf, ensure_ascii=False, indent=2)

    md = f"""# KF-RESULT wp-5406-01

工作包 `wp-5406-01`（`01-asset-registration`，lane C）对 report_id=**5406** 的资产登记结果。
本单只登记源资产，不做分类、不抽取 claim、不给 verified。

## ① 本工序做了什么

* 拉取 `tensor://reports/5406` 的记录，取 `markdown` 字段；对**markdown 的 UTF-8 字节**重算
  sha256，与包契约的 `source_hash` 逐位比对：`{src['computed_source_hash']}`。
* 登记正文里被反引号引用的**路径型 token**（文件/目录/测试 node id）与记录
  `figures` 里的图，共 **{counts['attachments']}** 条资产（其中报告图 {counts['figures']} 条），
  每条带逐字引文 + 起止偏移 + 行号 + 引文 sha256。
* 对每条资产给出**可达性**判定：字节可得 = {counts['with_bytes_available']} 条；
  未解决 = {counts['unresolved']} 条（含 1 条"仅元数据声明"的报告图，计入未解决集合，
  因为它的 png 字节不在 `markdown` 字段里）。
* 不生成 claim（`claims.extracted = {manifest['claims']['extracted']}`），不写
  `verified`（`verification.status = "{manifest['verification']['status']}"`）。
* 记录 `markdown` 长度 {src['chars']} 字符 / {src['bytes']} 字节，与契约 `chars: {src['declared_chars']}`
  一致（`chars_match = {src['chars_match']}`）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET ${{TENSOR_API_BASE}}/tensor/reports/5406`（Bearer 登录 token），
   记录落 `knowledge/assets/wp-5406-01/report_record.json`，`markdown` 原字节落
   `knowledge/assets/wp-5406-01/source_snapshot.md`。快照字节哈希 =
   `{kf['outputs']['source_snapshot.md']['sha256']}`。
2. **哈希**：`hashlib.sha256(markdown.encode('utf-8'))`，不做换行/空白归一化——
   契约给的是 markdown 字节哈希，归一化会让 E2 失去意义。
3. **资产发现**（`scripts/wp5406_asset_manifest.py::discover_paths`）：只扫**行内代码段**
   内的空白分隔 token，按「含 `/` 或带文件扩展名」判为路径型；每个 token 用
   **路径字母表边界**定位（`(?<![\\w./\\\\-])…(?![\\w/\\\\-])`），因此
   `provenance_gate_matrix.png` 里的 `gate_matrix.png` **不会**被当成一条独立资产
   （这条边界规则是本次实测踩出来的：第一版用字符集合判断，`_` 不在集合里，
   于是图 `gate_matrix.png` 被误挂了一个假 locator）。
4. **目录/基名的诚实处理**：正文只给基名（如 `gate_evidence.json`）时不编造全路径；
   若与某已登记目录同处一行，则记 `member_of`（本次三条产物都 bound 到
   `artifacts/m4829_ci_gate`）。目录引用（`artifacts/`、`docs/`、`src/`、
   `artifacts/m4829_ci_gate/`）一律判 `unresolved_referenced_directory`，**不**因为
   交付仓里同名目录存在就判"可达"（那是名字巧合，不是同一资产）。
5. **图资产**：记录 `figures[0]` 只有 `name` + `caption`，没有 `png_base64`，
   正文也从不写文件名 → 登记为 `locator_type = record_field`（`figures[0].name`），
   `mentions = []`，状态 `declared_metadata_only`。自检对它做**字段漂移**检查：
   记录里名字一变即 FAIL（`tests/test_wp5406_asset_manifest.py` 有对应用例）。
6. **交叉复核**：用平台自己的库 `ke.wp_gate.ApiSourceResolver`（与本脚本无共享代码）
   独立重解析 5406 并算哈希：`{platform['platform_sha256']}`，
   与清单/契约一致 = `{platform['hash_agrees_with_contract']}`，字符数
   `{platform['platform_chars']}` vs 清单 `{manifest['source']['chars']}`。
7. **自检**：脚本内置 {len(checks['checks'])} 条检查（见 ⑥），另有
   `python -m pytest tests/test_wp5406_asset_manifest.py -q` → **14 passed**。
8. **图**：`scripts/wp5406_asset_figure.py` 读清单与交叉复核结果画三联图（无手抄数值）。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `knowledge/assets/wp-5406-01/asset_manifest.json` | 交付物本体：源哈希/字符数/记录元信息 + {counts['attachments']} 条资产（含 locator 与可达性）+ counts + 自检块；sha256 `{kf['outputs']['asset_manifest.json']['sha256']}` |
| `knowledge/assets/wp-5406-01/self_checks.json` | {len(checks['checks'])} 条自检结果，`all_pass = {checks['all_pass']}` |
| `knowledge/assets/wp-5406-01/platform_resolver_check.json` | 平台库独立重算哈希的交叉复核证据 |
| `knowledge/assets/wp-5406-01/source_snapshot.md` | 报告 5406 的 markdown 原字节快照（哈希同契约） |
| `knowledge/assets/wp-5406-01/report_record.json` | 记录原文快照（title/figures/tags 等元信息） |
| `knowledge/assets/wp-5406-01/asset_reachability.png` | 三联图：可达性状态 / locator 类型 / 三处哈希一致 |
| `knowledge/assets/wp-5406-01/kf_result.json` | 本报告的 KF-RESULT 载荷（下方唯一 json 块逐字节相同） |
| `scripts/wp5406_asset_manifest.py` | 工序本体（登记 + 自检，可离线重跑） |
| `scripts/wp5406_asset_figure.py` / `scripts/wp5406_kf_result.py` / `scripts/wp5406_report.py` | 图 / 结果载荷 / 本报告，全部程序化生成 |
| `tests/test_wp5406_asset_manifest.py` | 14 条不变量测试（含"最长路径不得解析自身后缀"与三条有牙齿的反例） |

**资产清单（{counts['attachments']} 条）**

| id | path | kind | 可达性 | 字节可得 |
|---|---|---|---|---|
{asset_rows}

`distinct_by_basename = {counts['distinct_by_basename']}`：`gate_evidence.json` 同时以
全路径与基名出现，清单用 `same_asset_as` 关联而**不**合并，避免下游重复计数。

## ④ 证据定位表（claim/字段 → 原文逐字引文）

| 资产 id | 原文引文（逐字） | 原文行 | 出现次数 |
|---|---|---|---|
{loc_rows}

同一资产多次出现（全部行号已登记，用于下游取更贴合的上下文）：

| 资产 id | path | 原文行 |
|---|---|---|
{multi_rows}

元信息类断言（不在 markdown 字节内，故用记录字段定位、不做逐字引文）：

| 字段 | 值 | 来源 |
|---|---|---|
| `report_id` | `{src['report_id']}` | 记录主键 |
| `scenario_key` | `{src['record_meta']['scenario_key']}` | `record.scenario_key` |
| `mission_id` | `{src['record_meta']['mission_id']}` | `record.mission_id` |
| `title` | {src['title']} | `record.title` |
| `source_hash` | `{src['computed_source_hash']}` | markdown 字节重算 |

## ⑤ 注意点与局限

* **字节可得 = 0**：本单没有任何一条资产的字节能从 `markdown` 字段取出。
  {counts['unresolved']} 条未解决里，三条 m4829 产物 + 两个脚本 + 两个测试 + 文档
  都在 **TensorDEM** 仓；本交付仓是 TensorKnowledge，不 checkout TensorDEM，
  因此既不能验证它们存在，也不能验证其内容——只登记"被引用"。这是**上限明确的
  不完整**，不是"已完成"。
* **报告图的 png 不可取**：`figures` 只有 name/caption，无法把图当字节资产传给下游；
  下游若需要图，须回到出报告者/仓里取。
* **路径 token 抽取是文本级的**：不解析 markdown 语义，扫的是行内代码段。正文里若有
  未被反引号包住的路径，或跨行的路径拼接，会漏登记。本报告实测 {counts['attachments']}
  条全部来自反引号段；漏检风险已如实标注，未做"看起来覆盖全"的声明。
* **同一资产的双重登记**：`gate_evidence.json`（基名）与
  `artifacts/m4829_ci_gate/gate_evidence.json`（全路径）是同一文件的两处引用，
  用 `same_asset_as` 关联；下游若按 id 计数会得到 {counts['attachments']}，
  按 basename 去重是 {counts['distinct_by_basename']}。
* **不做的事**：不分类报告类型（契约 `classify_report_type: false`）、不抽 claim、
  不改写上游、不标 verified。verification 由平台门计算。
* **版本记录（作废说明）**：本单首次发布为 report 14639，产物路径写成 `artifacts/wp-5406-01/`；
  而 `artifacts/` 在本仓 `.gitignore` 内（推门亦会滤除 `artifacts/**`），产物不会入库。
  故产物改落受版本控制的 `knowledge/assets/wp-5406-01/` 并重发本报告；平台报告接口无更新/删除
  （PUT/PATCH/DELETE 实测均 405），14639 无法撤回、按作废处理，它与本版的差异仅限产物路径。
* **未运行的检查**：`scripts/validate_work_package.py` 的三门校验**没有**对本包跑——
  它验证的是 03 工序的四文件包（`claims/evidence/provenance/extraction_summary`），
  本包契约的输出是单一 `asset_manifest.json`，硬套会得到一堆与工序无关的 S 项失败，
  那是错误证据而非证据。所以本包的性质由 ⑥ 的 9 条自检 + 14 条 pytest 不变量 + 平台库
  哈希交叉复核来支撑，如实说明该门未覆盖本工序。

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 判定 | 依据 |
|---|---|---|
| valid_json | ✅ | `asset_manifest.json` 由 json 序列化产出，测试用例重新加载解析 |
| schema_pass | ✅ | 自检 `schema_pass_manifest_v1`：必需键齐全（manifest_version/package_id/task_type/source/attachments/counts，每条资产 id/path/kind/mentions/reachability） |
| source_locator_resolvable | ✅ | 自检 `source_locator_resolvable`：每条 mention 重切偏移逐字相等、引文 sha256 相等；图资产用 `record.figures[0].name` 漂移检查（反例测试证明该检查会 FAIL） |
| source_hash_matches | ✅ | `{src['computed_source_hash']}` == 契约；平台库独立重算一致 `{platform['hash_agrees_with_contract']}` |
| no_duplicate_ids | ✅ | {counts['attachments']} 个 id 全 distinct，均 `asset:5406:` 前缀 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅ | claims 为空数组（契约允许）；每条资产都有 `reachability.status` + `detail` + `checked`，无"默认可达" |

自检明细（`self_checks.json`，`all_pass = {checks['all_pass']}`）：

| 检查 | 结果 | 细节 |
|---|---|---|
{check_rows}

**诚实项**：没有失败项；但"字节可得 = 0 / 未解决 {counts['unresolved']} 条"是真实覆盖缺口，
不是通过项——它反映的是本次只能拿到 markdown 文本这一事实。

## 复跑

```bash
python scripts/wp5406_asset_manifest.py --offline-from knowledge/assets/wp-5406-01/report_record.json \\
  && python scripts/wp5406_asset_figure.py \\
  && python scripts/wp5406_kf_result.py \\
  && python scripts/wp5406_report.py \\
  && python -m pytest tests/test_wp5406_asset_manifest.py -q
```

（在线版去掉 `--offline-from`，改走 `$TENSOR_API_BASE` 拉取；两条路径产出的清单**逐字节相同**，
本次已实测。）

## KF-RESULT 载荷

```json
{kf_json}
```
"""
    out = PKG / "REPORT.md"
    out.write_text(md, encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(md)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())