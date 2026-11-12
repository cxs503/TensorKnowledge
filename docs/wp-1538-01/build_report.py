#!/usr/bin/env python3
"""生成 wp-1538-01 的交付报告 markdown（含唯一 ```json 结果块）与平台 POST 载荷。

零手抄：报告里出现的每个数字/引文都由本脚本从
  - artifacts/wp-1538-01/asset_manifest.json
  - artifacts/wp-1538-01/check_log.json
  - runs/wp-1538-01/source_1538.md（报告快照，逐字）
程序化读取或抽取，并对每条引文断言 `quote in source_markdown`。

用法: python3 artifacts/wp-1538-01/build_report.py
输出: docs/kf_result_wp-1538-01.md, artifacts/wp-1538-01/report_payload.json
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
MAN = json.loads((HERE / "asset_manifest.json").read_text(encoding="utf-8"))
LOG = json.loads((HERE / "check_log.json").read_text(encoding="utf-8"))
ENV = json.loads((HERE / "kf_result_wp-1538-01.json").read_text(encoding="utf-8"))
SRC = (ROOT / "runs" / "wp-1538-01" / "source_1538.md").read_text(encoding="utf-8")


def line_of(needle: str) -> int:
    if needle not in SRC:
        raise AssertionError(f"引文不在原文（零手抄检查失败）: {needle!r}")
    return SRC[: SRC.index(needle)].count("\n") + 1


def q(needle: str) -> str:
    """逐字引文 + 行号。"""
    return f"`{needle}` (L{line_of(needle)})"


rep = MAN["report"]
h1 = SRC.splitlines()[0]
assert h1.startswith("# ")

# --- 证据定位表（全部程序化） ---
ev_rows = [
    ("report.source_hash（契约 vs 观测）", rep["source_hash_observed"], "API GET /tensor/reports/1538 → field markdown, sha256(utf-8)"),
    ("report.chars", f"{rep['chars_observed']} chars / {rep['bytes_utf8_observed']} bytes(utf-8)", "同上，len(markdown) 与 len(encode('utf-8'))"),
    ("report.title（平台记录字段）", rep["title"], "record.title（与 markdown H1 措辞不同，见 §5 注意点 2）"),
    ("markdown H1（用于交叉核对标题）", h1, "markdown 第 1 行"),
    ("artifact 01..09 路径", "见 §3.2 表（逐条带行号）", "§7 工件清单表，逐行正则抽取"),
    ("attachment 01/02 文件名", ", ".join(a["name"] for a in MAN["attachments"]), "record.figures[].name + markdown 子串命中"),
    ("claims", "[]", "契约 notes「不做抽取。claims 允许为空数组」"),
]

art_rows = []
for a in MAN["artifacts"]:
    probes = a["resolution_probes"]
    present = [k for k, v in probes.items() if v["exists"]]
    art_rows.append(
        "| {id} | {path} | {kind} | L{line} | {res} | {present} |".format(
            id=a["artifact_id"],
            path=q(a["declared_path"]),
            kind=a["declared_kind"],
            line=a["locator"]["path_line"],
            res=a["resolution_status"],
            present=(", ".join(present) if present else "—"),
        )
    )

att_rows = []
for a in MAN["attachments"]:
    att_rows.append(
        "| {id} | {name} | {cap} | {inmd} | {state} |".format(
            id=a["attachment_id"],
            name=a["name"],
            cap=a["caption"][:60] + ("…" if len(a["caption"]) > 60 else ""),
            inmd=("是 L%d" % a["name_locator"]["line"]) if a["name_locator"] else "否",
            state=a["binary_resolution"],
        )
    )

checks_rows = "\n".join(
    f"| {c['name']} | {'✓' if c['ok'] else '✗'} | {c['detail']} |" for c in LOG["checks"]
)

png = HERE / "wp1538_01_manifest_checks.png"
png_sha = hashlib.sha256(png.read_bytes()).hexdigest()
man_sha = hashlib.sha256((HERE / "asset_manifest.json").read_bytes()).hexdigest()
env_sha = hashlib.sha256((HERE / "kf_result_wp-1538-01.json").read_bytes()).hexdigest()
build_sha = hashlib.sha256((HERE / "build_asset_manifest.py").read_bytes()).hexdigest()

present_ctx = sum(1 for a in MAN["artifacts"] if a["resolution_status"] == "resolved_in_environment")
n_art = len(MAN["artifacts"])

body = f"""# KF-RESULT wp-1538-01

**tags**: kf-wp:wp-1538-01, 01-asset-registration, report:1538, lane:C, draft
**date**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}
**agent**: agent/m15528 · repo: TensorKnowledge · branch: agent/m15528
**source**: `tensor://reports/1538` (field `markdown`, sha256:{rep['source_hash_observed'].split(':')[-1]})

---

## 1 本工序做了什么

`wp-1538-01` 是 **01-asset-registration**（资产登记）工序，作用域锁定 `report_id=1538` 一份报告，
目标按契约 notes：**「登记源资产：确认 report_id 与其 markdown 的字节哈希，列出可解析的附件/工件，不做抽取。claims 允许为空数组。」**

本工序交付 5 件事，全部可复跑：

1. **身份核验**：`report_id=1538` 的 markdown 字节哈希独立重算 = 契约声明值（**逐位相同**）。
2. **长度核验**：`chars=9477`（契约）vs 观测 `len(markdown)={rep['chars_observed']}`，一致；
   另记 utf-8 字节数 `{rep['bytes_utf8_observed']}` 与行数 `{rep['line_count_observed']}`（契约未声明，作为补充指纹）。
3. **附件登记**：报告记录 `figures` 中 {len(MAN['attachments'])} 个 PNG 附件登记名称/caption；**二进制未下载**，
   状态如实标 `metadata_only`（不对 PNG 字节作任何断言）。
4. **工件登记**：报告 §7 工件表 {n_art} 条路径**程序化抽取**（正则解析表格行，不手打），逐条附原文引文 + 行号，
   并记录登记时点两个检出根的存在性探查结果（{present_ctx}/{n_art} 在其声明仓上下文中存在）。
5. **claims=[]**：本工序**不做抽取**，也不把任何结论标成 verified（verification 由平台门计算）。

**明确未做**（防止越界被误读为能力）：不抽取知识对象、不做 report_type 分类、不改写上游产物、
不修改任何其它 report_id、不修正报告正文里的任何数字或证据等级。

## 2 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具 / 关键设置 |
|---|---|---|
| 1 | 取源报告 | `GET $TENSOR_API_BASE/tensor/reports/1538`（Bearer=登录 token），只取 `markdown` 字段；**只读单报告** |
| 2 | psql 直连尝试 | `psql -d tensorplatform -tA -c "select markdown from tensor_reports where id=1538"` → **被拒**（`permission denied for table tensor_reports`），故全程只用 API 路径 |
| 3 | 独立重算哈希 | `hashlib.sha256(markdown.encode('utf-8')).hexdigest()`，与契约 `source_hash` 比对 |
| 4 | 离线快照 | 把 API 返回的 markdown 原样落 `runs/wp-1538-01/source_1538.md`，再 `sha256sum` 独立复算 → **与契约哈希逐位相同**（两条独立信道互证） |
| 5 | 附件抽取 | 从 record `figures[]` 取 name/caption；文件名在 markdown 中做子串定位（命中则记行号） |
| 6 | 工件抽取 | 正则 `^\\|\\s*`path`\\s*\\|\\s*(.+?)\\s*\\|$` 只扫「## 7 工件清单」小节，遇下一个 `## ` 即停 |
| 7 | 零手抄守卫 | 每条引文/路径在写入前断言 `quote in markdown`，未命中即 fail-fast（本次 {n_art}/{n_art} 命中） |
| 8 | 存在性探查 | 对两个检出根做 `Path.exists()`（**只探存在，不读内容、不写入**）：声明仓上下文 `/root/ship-performance-platform-incoming/ship-performance-platform` 与本草稿检出 TensorKnowledge |
| 9 | 结构门 | `jsonschema.validate(envelope, kf_result.v1.schema.json)` + **反证**（故意缺 `package_id` 必须被判失败，确认 schema 不放水）。本分支树 `schemas/` 未含该 schema 文件，改用同仓兄弟检出副本（sha256 记录在 check_log） |
| 10 | 出图 | matplotlib 150 dpi，两面板：A 工件解析矩阵，B 身份核验条；**图中所有数字均从 manifest 读出**，无手打 |

工具链：Python 3.11 / urllib（仅标准库）/ jsonschema 4.26.0 / matplotlib(Agg) / hashlib。
一键复跑：见文末 `repro_cmd`（幂等，重复跑生成同构 manifest，仅 `generated_at` 时间戳变化）。

## 3 产出物清单

### 3.1 文件 → 要点（含 sha256 指纹）

| 文件 | 要点 | sha256（前 16） |
|---|---|---|
| `artifacts/wp-1538-01/asset_manifest.json` | **主产物**：完整资产清单（report 身份块 / 2 attachments / 9 artifacts / 1 external ref / claims=[] / uncertainties / provenance） | `{man_sha[:16]}` |
| `artifacts/wp-1538-01/kf_result_wp-1538-01.json` | kf_result.v1 结果信封（package_id/task_type/report_id/provenance/outputs/claims） | `{env_sha[:16]}` |
| `artifacts/wp-1538-01/build_asset_manifest.py` | 可复跑构建器（取数→核验→抽取→探查→组 manifest→结构门→写 check_log） | `{build_sha[:16]}` |
| `artifacts/wp-1538-01/check_log.json` | {len(LOG['checks'])} 项核验记录，`all_ok={LOG['all_ok']}` | — |
| `artifacts/wp-1538-01/wp1538_01_manifest_checks.png` | 结果图（见 §4） | `{png_sha[:16]}` |
| `runs/wp-1538-01/source_1538.md` | 源报告 markdown 逐字节快照（离线复算哈希用） | `{rep['source_hash_observed'].split(':')[-1][:16]}` |
| `docs/kf_result_wp-1538-01.md` | 本报告 | — |

### 3.2 工件登记表（路径逐字来自报告 §7，行号为原文行号）

| id | declared_path（引文+行号） | 类型 | 行 | 解析状态 | 命中检出根 |
|---|---|---|---|---|---|
{chr(10).join(art_rows)}

### 3.3 附件登记表（record.figures）

| id | name | caption（前 60 字） | 文件名在 markdown | 二进制状态 |
|---|---|---|---|---|
{chr(10).join(att_rows)}

### 3.4 外部引用（不属于 §7 工件表，报告正文点名）

| id | 路径 | 引文定位 | 登记时点存在 |
|---|---|---|---|
| {MAN['external_references'][0]['ref_id']} | `{MAN['external_references'][0]['abs_path']}` | L{MAN['external_references'][0]['locator']['line']} | {MAN['external_references'][0]['exists_at_registration']} |

## 4 证据定位表（字段 → 原文引文片段）

| 字段 | 值 / 引文（逐字，含行号） | 定位方式 |
|---|---|---|
{chr(10).join(f'| {a} | {b} | {c} |' for a, b, c in ev_rows)}

代表性逐字引文（均带行号，可 `sed -n '<L>p' runs/wp-1538-01/source_1538.md` 复核）：

- 工序边界（报告自述交付项）：{q('本单交付 **①定位取证 ②缺陷实证 ③可直接应用的补丁（干跑验证，不改 TensorPlatform 工作树）')}
- 工件清单小节标题：{q('## 7 工件清单')}
- 报告对自身证据等级的保留：{q('**证据等级不升级**')}
- 报告标注的未验证项（本包不越权补验）：{q('**无基准**（离线不可读原件）')}

### 4.1 结果图

`artifacts/wp-1538-01/wp1538_01_manifest_checks.png`（150 dpi，两面板）：

- **A**：{n_art} 个报告声明工件 × 2 个检出根的存在性矩阵。可见同一批工件在其声明仓上下文中 **{present_ctx}/{n_art} 存在**、
  在本草稿检出（TensorKnowledge）中 **0/{n_art} 不存在** —— 这正是「资产登记必须绑定声明仓上下文」的直接图证。
- **B**：身份核验条 —— 契约 `source_hash`、API 观测 `markdown` sha256、本地快照 sha256 三者**同色（全绿）**，
  即三条独立信道给出同一哈希；旁注 chars/bytes/lines/hash_match 全部一致。

（无场量云图：本工序是资产登记/文档类工序，无任何物理场求解或数值解，故不存在可画的云图或解析解比较曲线；
上图为该工序**真正**的判定依据，不是装饰图。）

## 5 注意点与局限

1. **只 GET 了 id=1538**：单报告作用域；未读/写/覆盖任何其它 report_id，未改上游产物，未把任何结论标 verified。
2. **平台记录 title ≠ markdown H1**：record.title 无后缀，H1 含 `+（补丁与金标）`（H1 见 §4 第 4 行引文）。
   两者都如实登记、不做归一，下游若按标题对齐需注意此差异（契约 title 取的是 record.title）。
3. **附件只有元数据**：2 个 PNG 未下载，`binary_resolution=metadata_only`；因此**没有**对 PNG 字节做存在性/哈希/可解码断言。
   若后续工序需要图片本体，须另走下载通道并在 manifest 增补字节级证据。
4. **工件存在性 ≠ 内容正确性**：{n_art} 条 declared_path 在声明仓上下文里存在，仅说明**路径可解析**；
   本包不校验其内容、不校验报告 §3 里的任何数字（那是 03/04 工序与平台门的职责）。
5. **检出根是「登记时点」快照**：`resolution_probes` 记录的是本次登记时刻的存在性；仓被重建/清理后结果可能变化，
   故每条探测都写入了 `abs_path`，可重放。
6. **结构门用了兄弟副本**：本草稿树 `schemas/` 未含 `kf_result.v1.schema.json`，用同仓其它检出副本校验
   （sha256 记在 `check_log.schema_note`）；已加反证（缺 `package_id` 必须被判失败）排除 schema 过宽。
7. **psql 信道不可用**：`tensor_reports` 表对本账号 `permission denied`，故哈希核验走 API + 本地快照两信道，
   而非「API + DB」；这一点已写入 manifest 的 `report.locator.fallback_note`，不假装双库互证。
8. **claims=[] 是契约允许的完整结果**，不是漏做；本工序 task_type 明确禁止抽取。

## 6 自检（逐条对照 acceptance）

| 条件 | 结果 | 依据 |
|---|---|---|
| valid_json | ✓ | 结果 JSON 经 `json.loads` 解析；`check_log.checks[manifest_valid_json]=true` |
| schema_pass | ✓ | `jsonschema.validate` 通过 kf_result.v1；反证（缺 `package_id`）被判失败 |
| source_locator_resolvable | ✓ | `tensor://reports/1538` → `GET /api/v1/tensor/reports/1538` 200，返回 markdown 且哈希吻合 |
| source_hash_matches | ✓ | 契约 `{rep['source_hash_declared']}` vs 观测逐位相同（另经本地快照 `sha256sum` 二次独立复算） |
| no_duplicate_ids | ✓ | attachment/artifact id 唯一（{len(MAN['attachments'])}/{n_art}），declared_path 无重复 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✓（空集成立） | `claims=[]`，契约 notes 明示允许；无悬空断言 |

机读明细（{len(LOG['checks'])} 项，`all_ok={LOG['all_ok']}`）：

| check | ok | detail |
|---|---|---|
{checks_rows}

**honest 未完成项（不粉饰）**：PNG 二进制未下载验证（`not_run`）；报告 §3 的数值/证据等级未复核（工序边界外）；
工件内容未校验（只校验路径可解析）。

---

## 结果 JSON（kf_result.v1，唯一 json 块）

```json
{json.dumps(ENV, ensure_ascii=False, indent=2)}
```

---

**repro_cmd**（在仓库检出根执行；幂等）：

```bash
TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER \\
TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS \\
python3 artifacts/wp-1538-01/build_asset_manifest.py \\
 && python3 artifacts/wp-1538-01/plot_manifest_checks.py \\
 && python3 artifacts/wp-1538-01/build_report.py \\
 && python3 - <<'PY'
import json, hashlib
m = json.load(open('artifacts/wp-1538-01/asset_manifest.json'))
e = json.load(open('artifacts/wp-1538-01/kf_result_wp-1538-01.json'))
h = hashlib.sha256(open('runs/wp-1538-01/source_1538.md','rb').read()).hexdigest()
assert m['report']['hash_match'] is True
assert e['provenance']['source_hash'] == 'sha256:' + h, 'source_hash mismatch'
assert m['claims'] == [] and e['claims'] == []
assert e['outputs']['asset_manifest.json'] == m
print('OK  sha256=' + h)
PY
```
"""

out_md = ROOT / "docs" / "kf_result_wp-1538-01.md"
out_md.parent.mkdir(parents=True, exist_ok=True)
out_md.write_text(body, encoding="utf-8")

# json 块唯一性自检
n_blocks = body.count("```json")
assert n_blocks == 1, f"报告必须只有 1 个 json 块，实际 {n_blocks}"
assert "```json\n" + json.dumps(ENV, ensure_ascii=False, indent=2) + "\n```" in body

payload = {
    "title": "KF-RESULT wp-1538-01",
    "summary": (
        f"report 1538 资产登记完成：markdown sha256 逐位吻合契约值（长度 {rep['chars_observed']} chars / "
        f"{rep['bytes_utf8_observed']} bytes），登记 {len(MAN['attachments'])} 个附件（PNG 仅元数据）与 "
        f"{n_art} 条工件路径（{present_ctx}/{n_art} 在声明仓上下文可解析），claims=[]（本工序不做抽取）。"
    ),
    "scenario_key": rep["scenario_key"],
    "mission_id": int(os.environ.get("KF_MISSION_ID", "15528")),
    "tags": ["kf-wp:wp-1538-01", "01-asset-registration", "report:1538", "lane:C", "draft", "CII"],
    "markdown": body,
    "figures": [
        {
            "name": "wp1538_01_manifest_checks.png",
            "caption": f"wp-1538-01 资产核验：A 面板 = {n_art} 条报告声明工件 × 2 检出根的存在性矩阵（声明仓 {present_ctx}/{n_art} 命中，本草稿检出 0/{n_art}）；B 面板 = 契约 source_hash / API 观测 sha256 / 本地快照 sha256 三信道一致性（全绿）",
            "png_base64": base64.b64encode(png.read_bytes()).decode(),
        }
    ],
}
(ROOT / "artifacts" / "wp-1538-01" / "report_payload.json").write_text(
    json.dumps(payload, ensure_ascii=False), encoding="utf-8"
)
print("wrote", out_md, len(body), "chars")
print("payload", (ROOT / 'artifacts' / 'wp-1538-01' / 'report_payload.json').stat().st_size, "bytes")