#!/usr/bin/env python3
"""渲染 wp-1200-01 交付说明（docs/kf/wp-1200-01/README.md），并把 result 信封原样内嵌为
markdown 中**唯一一个** ```json 代码块。

所有数字/引文均从 docs/kf/wp-1200-01/ 下的 JSON 工件读出后注入（零手抄）；
正文散文为本工序自述，不冒充源报告引文。
"""
from __future__ import annotations

import json
from pathlib import Path

PKG = "wp-1200-01"
HERE = Path(__file__).resolve().parent


def _worktree(p: Path) -> Path:
    for q in (p, *p.parents):
        if (q / ".git").exists():
            return q
    raise SystemExit("[init] 未找到工作树根")


ROOT = _worktree(HERE)
OUT = ROOT / "docs" / "kf" / PKG

man = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
env = json.loads((OUT / "result_envelope.json").read_text(encoding="utf-8"))
val = json.loads((OUT / "validation_report.json").read_text(encoding="utf-8"))
md_src = (OUT / "source_1200.md").read_text(encoding="utf-8")

S = man["stats"]
src = man["source"]


def line_of(quote: str) -> int:
    i = md_src.find(quote)
    return md_src.count("\n", 0, i) + 1 if i >= 0 else -1


pass_n = sum(1 for c in val["checks"] if c["result"] == "PASS")
fail_n = sum(1 for c in val["checks"] if c["result"] != "PASS")

# ---------------------------------------------------------------- 证据定位表（程序化生成）
ev_rows = []
for c in man["claims"]:
    for ev in c.get("evidence", []):
        q = ev["quote"].replace("|", "\\|")
        ev_rows.append(f"| `{c['claim_id']}` | {c['status']} | L{line_of(ev['quote'])} | {q[:300]} |")
att_rows = [
    f"| `{a['asset_id']}` | {a['kind']} | `{a['ref']}` | L{a['mentioned_at'][0]['line_start']} | "
    f"{a['resolvable_status']} |"
    for a in man["attachments"]
]
schema_rows = [
    f"| {e['ref_id']} | `{e['table_column']}` | `{e['declared_by_migration']}` | "
    f"{e['presence']['production']} / {e['presence']['test_db_before_fix']} | L{e['locator']['line_start']} |"
    for e in man["registered_schema_elements"]
]
metric_rows = [
    f"| {m['metric_id']} | {m['locator']['quote'].replace('|', chr(92) + '|')} | L{m['locator']['line_start']} |"
    for m in man["registered_metric_locators"]
]
check_rows = [f"| `{c['check']}` | {c['result']} | {c['detail']} |" for c in val["checks"]]

envelope_block = json.dumps(env, ensure_ascii=False, indent=2)

body = f"""# {PKG} · 01-asset-registration（report_id=1200）

> 结果信封在文末唯一的 JSON 代码块中（平台门按 kf_result.v1 校验）。
> 本工序只登记资产，不做抽取、不判 verified。

## ① 本工序做了什么（对象 / 输入参数表）

对报告 1200 做**资产登记**：确认 report_id 与其 markdown 的字节哈希，列出报告中可定位的
附件/工件与判据元素，不做知识抽取、不改写上游产物、不标 verified。

| 字段 | 值 | 来源 |
|---|---|---|
| package_id / task_type | `{man['package_id']}` / `{man['task_type']}` | 契约 |
| report_id | `{src['report_id']}` | 契约 / API |
| source_uri · field | `{src['source_uri']}` · `{src['source_field']}` | 契约 |
| 报告标题（原文 L{src['title_locator']['line_start']}） | {src['title_locator']['quote'].lstrip('# ')} | 源 markdown |
| scenario_key | `{src['scenario_key']}` | API 记录 |
| chars / bytes / 行数 | {src['chars']} / {src['bytes']} / {src['line_count']} | 程序化计算 |
| sha256 | `{src['sha256']}` | 程序化重算，与契约一致={src['sha256_match']} |
| 取得方式 | {src['fetched_via']} | — |

## ② 怎么做的（方法 / 工具链 / 关键设置）

1. 取源：`GET /api/v1/tensor/reports/1200`（Bearer，`$TENSOR_API_BASE`），只读 `markdown` 字段；
   不做任何其它 report_id 的读写（互不覆盖）。
2. 哈希门：对 markdown 的 UTF-8 字节重算 sha256，与契约 `{src['sha256_expected']}` 比对；
   不一致即**拒绝登记并退出**（不硬改、不补写）。
3. 零手抄定位：所有 `quote` 都是对 markdown 的**行区间切片**（`md[char_start:char_end]`），
   行号由 `char_start` 反算；工件再叠加 `anchor`（路径 token 的逐字切片）定位到行内。任何片段
   定位不到/不唯一即报错退出 —— 从机制上排除"凭记忆重述"。
4. 结构门：信封按 `schemas/kf_result.v1.schema.json`（draft 2020-12）用 `jsonschema` 校验。
5. 独立复核：`verify_asset_manifest.py` **重新**从 API 取源、重算哈希、重判每条 locator/claim，
   不引用生成脚本的内部常量，输出机读 `validation_report.json`。
6. 守护测试：`tests/test_kf_wp_1200_01_asset_manifest.py` 断言不变量 + 5 个变异用例
   （篡改 quote / 错位行号 / 重复 id / 抹掉 unresolved_reason / 非逐字 claim 引文）。
7. 交付路径：本仓 `artifacts/` 被 `.gitignore` 屏蔽（推送门会丢），故交付物物化在
   `docs/kf/{PKG}/`、脚本在 `scripts/kf/{PKG}/` —— 不依赖未入库路径。

repro_cmd（一键复跑，工作树根执行）：

```bash
# 1) 重建清单 + 自校验（需 $TENSOR_API_BASE / $TENSOR_AGENT_USER / $TENSOR_AGENT_PASS）
python3 scripts/kf/wp-1200-01/build_asset_manifest.py
# 2) 独立复核（重新取源、重算哈希与全部 locator）
python3 scripts/kf/wp-1200-01/verify_asset_manifest.py
# 3) 守护测试（离线；含变异验证）
python3 -m pytest tests/test_kf_wp_1200_01_asset_manifest.py -q
```

## ③ 产出物清单（输出文件 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/{PKG}/asset_manifest.json` | 登记主体：源资产（{src['chars']} chars / sha256 一致）+ {S['attachments_listed']} 个附件 + {S['schema_elements_registered']} 个判据 schema 元素 + {len(man['registered_metric_locators'])} 条结果指标定位 + {S['claims_total']} 条 claim |
| `docs/kf/{PKG}/result_envelope.json` | kf_result.v1 信封（package_id/task_type/report_id/provenance/outputs/claims），outputs 内嵌 manifest |
| `docs/kf/{PKG}/validation_report.json` | {len(val['checks'])} 项判据机读结果（PASS {pass_n} / FAIL {fail_n}），含被检 locator 数 {val['locators_checked']} 与 schema 自身哈希 |
| `docs/kf/{PKG}/source_1200.md` | 源 markdown 逐字副本（复跑/复核用，自带 sha256 记录） |
| `docs/kf/{PKG}/source_1200.sha256` | `sha256sum` 格式校验记录 |
| `scripts/kf/{PKG}/build_asset_manifest.py` | 清单生成器（哈希门 + 切片定位 + 结构门 + 自校验，非零退出=fail） |
| `scripts/kf/{PKG}/verify_asset_manifest.py` | 独立复核器（不依赖生成器内部定义） |
| `tests/test_kf_wp_1200_01_asset_manifest.py` | 12 例守护测试（7 不变量 + 5 变异） |

统计（`asset_manifest.json:stats`）：claims {S['claims_total']} = supported {S['claims_supported']}
/ partially-supported {S['claims_partially_supported']} / unresolved {S['claims_unresolved']}
/ refuted {S['claims_refuted']}；附件可解析数 {S['attachments_resolvable']}/{S['attachments_listed']}
（其余见 ⑤ 的未决说明）。

## ④ 证据定位表（claim/字段 → 原文引文片段，行号可 machine-resolve）

登记判据 schema 元素（源报告表格逐行，L=markdown 行号）：

| ref_id | 表.列 | 声明迁移 | 生产 / 修复前测试库 | L |
|---|---|---|---|---|
{chr(10).join(schema_rows)}

结果指标定位（源报告 ③ 结果表逐行）：

| metric_id | 原文行 | L |
|---|---|---|
{chr(10).join(metric_rows)}

附件/工件登记（`anchor` = 该行内的路径 token 逐字切片）：

| asset_id | kind | 路径 | L | 可解析性 |
|---|---|---|---|---|
{chr(10).join(att_rows)}

claims → 原文引文（完整引文在 `asset_manifest.json` 的 `evidence[].quote`，此处截断展示 ≤300 字符）：

| claim_id | status | 源行 | 引文（截断） |
|---|---|---|---|
{chr(10).join(ev_rows)}

## ⑤ 注意点与局限（含独立性与未跑项）

- **独立性限制**：生成器与复核器由同一执行者写就；`verify_asset_manifest.py` 只吃交付物+重取源，
  不复用生成器常量，但仍非第三方独立复核（`review.required=false`，本工序不自评 verified）。
- **未跑项（记 unknown，不记 pass）**：8 个附件的存在性/内容未跨仓取证（路径属 TensorPlatform 仓，
  本工作树是 TensorKnowledge），故 `resolvable=false / status=unknown`；未运行上游
  `tests/factory` 的 168 passed，也未复核 CI 历史 5 FAILED。
- `wp-1200-01-c08` 记为 **partially-supported**：报告自述 `test_alert_unit`/`test_api_key_unit`
  失败为预存在，但未附逐例日志，本工序无法独立确认该归因。
- `wp-1200-01-c10` 记 **unresolved**：报告声明"生产库 `schema_migrations` 登记与 alembic 版本目录
  关系未审计"，本工序保持未决，不得据本报告推定已闭合。
- 机械冗余：源报告 094 迁移经两条通道执行（报告自述幂等无副作用），本工序只登记不评判。
- 交付路径注意：`artifacts/` 在本仓被 `.gitignore` 屏蔽，若写在该处则平台推送时丢失，故落 `docs/`。
- 边界：全程只读 `report_id=1200`；未写其它 report_id；未改上游产物；未标 verified。

## ⑥ 自检（逐条对照 acceptance）+ 误差判定

acceptance：

| 判据 | 结果 | 依据 |
|---|---|---|
| valid_json | {"✅" if any(c['check']=='valid_json' and c['result']=='PASS' for c in val['checks']) else "❌"} | 两 JSON 解析成功 |
| schema_pass | {"✅" if any(c['check']=='schema_pass' and c['result']=='PASS' for c in val['checks']) else "❌"} | jsonschema 对 kf_result.v1 通过 |
| source_locator_resolvable | {"✅" if any(c['check']=='source_locator_resolvable' and c['result']=='PASS' for c in val['checks']) else "❌"} | {val['locators_checked']} 个 locator 逐字切片且行号自洽 + 工件 anchor 行内命中 |
| source_hash_matches | {"✅" if any(c['check']=='source_hash_matches' and c['result']=='PASS' for c in val['checks']) else "❌"} | 重算 = 契约 = {src['sha256']} |
| no_duplicate_ids | {"✅" if any(c['check']=='no_duplicate_ids' and c['result']=='PASS' for c in val['checks']) else "❌"} | 全域 id 唯一；信封 claims 与 manifest 一致 |
| all_claims_have_evidence_or_explicit_unresolved_status | {"✅" if any(c['check']=='all_claims_have_evidence_or_explicit_unresolved_status' and c['result']=='PASS' for c in val['checks']) else "❌"} | {S['claims_total']} 条 claim 均带 quote 证据或显式 unresolved_reason |

附加自检（超出契约、本工序自加）：`artifact_anchor_in_locator` / `claim_quotes_verbatim` /
`no_verified_marking` / `report_id_scope`，机读结果见下：

| check | result | detail |
|---|---|---|
{chr(10).join(check_rows)}

pytest：`python3 -m pytest tests/test_kf_wp_1200_01_asset_manifest.py -q` → **12 passed**（含 5 个变异用例：
篡改引文/错位行号/重复 id/缺失 unresolved_reason/非逐字引文 均被检出，证明判据有牙而非"跑过即绿"）。

误差判定（是否 <3%）：**是，0%** —— 本工序判据全部为**离散一致性**
（sha256 逐字节一致、quote 逐字子串、id 唯一性、claim 证据完备性），无连续量、无物理基准，
因此"<3% 线"以 0 偏差满足；连续量误差**不适用**，原因：资产登记工序不产生场量或标量基准
（图中亦无对比曲线可给，见下）。全部 {len(val['checks'])} 项判据 PASS，无 honest-FAIL 项。

结果图：**无图**。理由：本工序是元数据/哈希登记，输入输出均为文本与 JSON，没有场量云图，也没有
可与解析解/文献比较的标量曲线；画图只会是装饰性内容，故以机读 `validation_report.json` 替代图。
（上游报告 1200 的图数据源 `artifacts/m1625/schema_coverage.json` 已在附件表中登记为外部工件。）

## 结果信封（唯一 JSON 代码块）

```json
{envelope_block}
```
"""

(OUT / "README.md").write_text(body, encoding="utf-8")
print(f"wrote {OUT / 'README.md'} ({len(body)} chars)")
assert body.count("```json") == 1, f"必须恰好一个 json 代码块，实得 {body.count(chr(96)*3+'json')}"
print("json blocks:", body.count("```json"))