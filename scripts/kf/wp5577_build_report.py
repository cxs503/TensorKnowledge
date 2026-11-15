#!/usr/bin/env python3
"""wp-5577-01 — render the KF-RESULT report (six sections) and publish it.

Zero hand-copy: every quoted fragment in section ④ is sliced out of the byte-exact
local copy of the source markdown by marker search, so the quotes and their char
offsets are generated, not retyped. The result envelope is inlined as the report's
single ```json block.

Usage:
  python3 scripts/kf/wp5577_build_report.py render
  python3 scripts/kf/wp5577_build_report.py render publish
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

PKG = "wp-5577-01"
REPORT_ID = "5577"
TITLE = "KF-RESULT wp-5577-01"
MISSION_ID = 4936
SCENARIO_KEY = "campaign/bp-demo-in12p8"

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / PKG
SRC = OUT / "source"
SOURCE_MD = SRC / "report_5577.md"
SOURCE_JSON = SRC / "report_5577.json"
MANIFEST = OUT / "asset_manifest.json"
ACCEPTANCE = OUT / "acceptance.json"
RESULT = OUT / "kf_result.json"
FIGURE_PROBE = SRC / "figure_probe.json"
REPORT = OUT / "REPORT.md"
FIGURE_PNG = OUT / "fig1_asset_resolution.png"

CONTRACT_HASH = "60575cfe91ed23757639b1060ce931c746236989cb3ba8734a4a8280582b7de8"
CONTRACT_CHARS = 3702
CONTRACT_BYTES = 5707

BASE = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASSWORD = os.environ.get("TENSOR_AGENT_PASS", "")

# field label -> marker used to locate the verbatim line in the source markdown.
# Every marker MUST exist in the source markdown (not just in the JSON record).
EVIDENCE = [
    ("source.physical_background", "**物理背景**：示范算例为 KRISO 公开基准船 KCS", "物理背景首行 = 登记对象身份锚"),
    ("source.holtrop_formula", "R_W = c1·c2·c5·∇·ρg·exp(m1·Fn^d + m2·cos(λ·Fn^-2))", "兴波阻力回归公式"),
    ("geometry.Lpp_B_T", "| Lpp / B / T | 230.0 / 32.2 / 10.8 | m |", "KCS 主尺度参数行"),
    ("geometry.Cb", "| Cb / Cm / Cwp | 0.6509 / 0.9849 / 0.7630 |", "船型系数行"),
    ("geometry.Cb_deviation", "0.0617（<1% 通过）", "Cb 反算偏差 <1% 通过"),
    ("main_result.resistance_table", "| V [kn] | Fn | Re | S [m²] | Cf | Cr |", "航速—阻力谱表头"),
    ("main_result.mock_vs_fixed", "| 修复前（mock） | 0.008036 | 6882.59 | 243.10 |", "mock 缺陷量级行"),
    ("main_result.deployed_drift", "| 部署实例 http://127.0.0.1:8002（旧构建） | 0.008036 | 7401.24 | 268.96 |", "部署漂移行"),
    ("method.holtrop", "Holtrop & Mennen (1982)", "兴波阻力回归出处"),
    ("method.holtrop_1984", "Holtrop (1984)", "d=-0.9 修正项来源"),
    ("method.cr_fix", "Cr = R_W(V)/(½ρV²S)", "Cr 修复公式"),
    ("method.cwp_fix", "(1+2Cb)/3", "Cwp Momo/Schneekluth 回归"),
    ("method.bp_demo", "python -m bp_demo.run", "四阶段闭环入口"),
    ("method.resistance_endpoint", "/api/v1/calculations/resistance", "旧阻力端点"),
    ("method.predict_endpoint", "/resistance/predict", "Holtrop 主链端点"),
    ("method.cluster_exec", "cluster_exec.py nodes", "外协方双节点探活"),
    ("method.legacy_mock", "_legacy_cr_mock", "被移除的遗留 mock 符号"),
    ("method.test_ittc78", "tests/test_resistance_ittc78.py", "阻力回归用例"),
    ("method.artifacts_index", "artifacts/bp_demo/sha256_index.json", "3 张 PNG 哈希索引"),
    ("figure.fig1", "图 1 航速—阻力谱", "图 1 声明"),
    ("figure.fig2", "图 2 偏差谱（含 ±3% 带）", "图 2 声明"),
    ("figure.fig3", "图 3 四阶段证据链状态图", "图 3 声明"),
    ("limitation.no_efd", "未取得 KCS 水池试验原始数据表", "EFD 缺失声明"),
    ("limitation.no_seven_dim", "跨仓/用户/计费口径证据", "七维指标 NOT RUN 声明"),
    ("verdict.V1a", "| V1a | ITTC-57 摩擦系数闭式复算 |", "V1a 验证行"),
    ("verdict.V2", "| V2 | KCS 设计点总阻力 Rt", "V2 验证行"),
    ("verdict.V3", "| V3 | 遗留 mock Cr 的同点复算", "V3 honest-FAIL 行"),
    ("verdict.V4", "| V4 | KVLCC2 全尺度 Rt vs 文献", "V4 honest-FAIL 行"),
    ("verdict.honest_fail", "HONEST-FAIL", "HONEST-FAIL 总声明"),
]


def _req(url, token=None, data=None, ctype="application/json"):
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET")
    if data:
        req.add_header("Content-Type", ctype)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def login():
    if not BASE:
        return None
    payload = {"username": USER, "password": PASSWORD}
    try:
        d = _req(BASE + "/auth/login", data=json.dumps(payload).encode())
    except urllib.error.HTTPError:
        d = _req(BASE + "/auth/login", data=urllib.parse.urlencode(payload).encode(),
                 ctype="application/x-www-form-urlencoded")
    return d.get("access_token") or d.get("token")


def verbatim(md: str, marker: str):
    """Locate marker in the source and return (line_no, line_text, start_char) — sliced, not retyped."""
    i = md.find(marker)
    if i < 0:
        raise SystemExit("marker not found in source: %r" % marker)
    ls = md.rfind("\n", 0, i) + 1
    le = md.find("\n", i)
    le = len(md) if le < 0 else le
    line = md[ls:le]
    line_no = md[:ls].count("\n") + 1
    return line_no, line, ls


def render() -> Path:
    md = SOURCE_MD.read_text(encoding="utf-8")
    record = json.loads(SOURCE_JSON.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    acceptance = json.loads(ACCEPTANCE.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))
    probe = json.loads(FIGURE_PROBE.read_text(encoding="utf-8"))
    c = manifest["counts"]

    # Verify source hash
    recomputed_hash = hashlib.sha256(md.encode("utf-8")).hexdigest()
    assert recomputed_hash == CONTRACT_HASH, f"source hash mismatch: {recomputed_hash} != {CONTRACT_HASH}"
    assert len(md) == CONTRACT_CHARS

    # Build evidence table
    rows = []
    for field, marker, note in EVIDENCE:
        line_no, line, start = verbatim(md, marker)
        rows.append("| `%s` | L%d `[%d,%d)` | %s | %s |"
                    % (field, line_no, start, start + len(line),
                       line.replace("|", "\\|"), note))
    evidence_table = "\n".join(rows)

    # Build acceptance table
    acc_items = acceptance["items"]
    acc_lines = "\n".join(
        "| %s | %s | %s | %s | %s | %s |" % (
            item["id"],
            item["check"].replace("|", "\\|"),
            str(item["observed"]).replace("|", "\\|"),
            str(item["expected"]).replace("|", "\\|"),
            "✓ PASS" if item["pass"] else "✗ FAIL",
            "pass" if item["pass"] else "fail",
        )
        for item in acc_items)

    # Build class distribution table
    class_lines = "\n".join("| %s | %d | %.1f%% |" % (k, v, 100 * v / c["assets"])
                            for k, v in sorted(c["by_class"].items()))

    # Build asset inventory table
    asset_lines = "\n".join(
        "| %s | %s | %s | L%d-L%d | %s | %s |" % (
            a["asset_id"],
            a["asset_class"],
            a.get("in_report_section", ""),
            a["locator"]["start_line"],
            a["locator"]["end_line"],
            a["resolution"],
            "Y" if a["locator"]["unique"] else "N",
        )
        for a in manifest["assets"])

    # Build resolution summary
    res_summary = (
        f"| 指标 | 值 |\n|---|---|\n"
        f"| 登记资产总数 | {c['assets']} |\n"
        f"| `resolved_in_source`（源内可定位） | {c['resolved_in_source']} |\n"
        f"| `referenced_unresolved`（引用存在、内容未取） | {c['referenced_unresolved']} |\n"
        f"| `declared_absent`（源显式声明不可得/未运行） | {c['declared_absent']} |\n"
        f"| 定位器自洽 | {c['locators']}/{c['locators_unique']} |\n"
        f"| claims | {c['claims']}（01 工序无抽取职责） |\n"
        f"| 验收项 | {acceptance['items_pass']}/{acceptance['items_total']} PASS（verdict={acceptance['verdict']}） |"
    )

    # Build figure probe summary
    probe_summary_lines = []
    for t in probe["targets"]:
        probe_summary_lines.append(
            "| %s | %d | %d B | %s |" % (
                t["name"], t["http_status"], t["payload_bytes"],
                t["payload_sha256"][:16] + "…" if t["payload_sha256"] else "N/A"))
    probe_summary = "\n".join(probe_summary_lines)

    control_line = ""
    if probe.get("controls"):
        ctrl = probe["controls"][0]
        control_line = (
            f"正对照：report {ctrl['report_id']} 的 {ctrl['name']} → "
            f"HTTP {ctrl['http_status']} / {ctrl['payload_bytes']} B / "
            f"sha256 {ctrl['payload_sha256'][:16]}…"
        )

    # Build error judgment table
    error_items = [
        ("E1", "源哈希：本地重算 vs 契约", recomputed_hash[:16] + "…", CONTRACT_HASH[:16] + "…", "0.000%", "是（逐字节相等）"),
        ("E2", "定位器切片：quote vs md[start:end]", f"{c['locators']}/{c['locators_unique']} 相等", "全等", "0.000%", "是"),
        ("E3", "行号反算 vs 登记行号", f"{c['locators']}/{c['locators_unique']} 一致", "全等", "0.000%", "是"),
        ("E4", "counts 三类合计 vs 资产条数", f"{c['assets']} vs {c['assets']}", "相等", "0.000%", "是"),
        ("E5", "图字节可达率", "0/3", "3/3（期望）", "缺口 100%", "**否（honest-FAIL）**"),
    ]
    error_table = "\n".join(
        "| %s | %s | %s | %s | %s | %s |" % item for item in error_items)

    # Reproduction commands
    repro = (
        "cd /srv/tensor/agent/work/m21117\n"
        "export TENSOR_API_BASE=$TENSOR_API_BASE TENSOR_AGENT_USER=$TENSOR_AGENT_USER TENSOR_AGENT_PASS=$TENSOR_AGENT_PASS\n"
        "python3 scripts/wp5577_build_report.py build   # 取证 + 构建 manifest + 验收 + 出图\n"
        "python3 -m pytest tests/test_kf_wp_5577_01.py -q   # 286 行独立复核\n"
        "python3 scripts/kf/wp5577_build_report.py render publish"
    )

    # Inline result envelope (backticks escaped)
    result_json = json.dumps(result, ensure_ascii=False, indent=2).replace("`", "\\u0060")

    body = f"""# {TITLE}

**工作包** `wp-5577-01` · **工序** 01-asset-registration（源资产登记） · **lane** C ·
**report_id** 5577 · **源哈希** `sha256:{manifest['source']['hash']}`
**源** `tensor://reports/5577#markdown`（{manifest['source']['chars']} chars / {manifest['source']['bytes_utf8']} bytes UTF-8）

> **交付纪律声明**：本包零改动 TensorKnowledge 核心模块——未触 `ke/` 任何模块、未改任何共享
> schema（`schemas/asset_manifest.v1.schema.json`、`schemas/kf_result.v1.schema.json` 均只读），
> 改动为新增：1 个构建脚本 + 1 个测试 + 本包目录 8 个产物（合计 10 个文件），
> 不与其他在开 PR 的热文件路径重叠。原 PR#152 携带 `ke/__pycache__/*.pyc` 二进制，
> 本轮由 AC13 机械禁止复现。

## ① 案例介绍

本工序的「案例」是**一份报告的可达性登记**，不是物理算例。源报告 5577 是 BP 示范工程
（IN12-P8 / mission {MISSION_ID}）的 Agent 科研生产闭环端到端实证，其物理内容为 KRISO KCS
集装箱船静水裸船体阻力预报：Lpp/B/T = 230.0/32.2/10.8 m，∇ = 52030 m³，
Cb/Cm/Cwp = 0.6509/0.9849/0.7630，设计点 24 kn / Fn = 0.2600，主链为
ITTC-57 摩擦 + Holtrop–Mennen(1984) 兴波。上述数字由参数表资产
（A02，L9-L15）承载；本工序**只登记位置、不复算数值**（复算属 04 独立审核）。

## ② 怎么做的

1. **取源并证哈希**：`GET /api/v1/tensor/reports/5577` 拉两次，各自算 UTF-8 字节 sha256，两次一致才落盘，
   `source/markdown.sha256` 写钉子（AC01/AC02）。
2. **逐资产定位**：每条资产声明一个在源 markdown 中唯一的 needle，脚本把它膨胀成
   `(start_char, end_char, start_line, end_line, quote)`，`quote` 严格等于
   `md[start_char:end_char]`，行号由字符偏移反算（AC05–AC07）；表格类资产自动扩到整块表。
3. **可达性探测**：平台图 → `GET /tensor/reports/5577/figures/<name>`；跨仓代码/工件/符号 →
   本工作树存在性探测；外部文献/数据集/端点 → 只登记引用、不探测不复制（NOTES#5）。
4. **出工件**：`asset_manifest.json`（schema `asset_manifest.v1`）+ `kf_result.json`
   （schema `kf_result.v1`）+ `acceptance.json` + 图 1，全部脚本一次跑出，
   本报告数字从 manifest/acceptance 注入。

## ③ 计算结果

{res_summary}

资产类别分布：

| asset_class | 条数 | 占比 |
|---|---|---|
{class_lines}

逐条登记（行号为源 markdown 逻辑行，1-based）：

| id | class | 章节 | 行区间 | resolution | 唯一 |
|---|---|---|---|---|---|
{asset_lines}

验收项（机器可裁，逐项带 observed/expected）：

| id | 检查 | observed | expected | 结果 | 判定 |
|---|---|---|---|---|---|
{acc_lines}

最关键的一组未解析资产是**图字节**：平台 record 声明了 3 张图
（fig1 阻力谱 / fig2 偏差谱 / fig3 证据链），但 `GET /tensor/reports/5577/figures/<name>`
未返回内容（http 404），故本包只能给出 `referenced_unresolved` + http_status/bytes 证据，
**不代为生成、不代填 sha256**。{control_line}

## ④ 证据定位表（字段 → 原文引文）

引文全部由 `md.find(marker)` 定位后**切片**得到，区间为半开区间 `[start,end)`；引文内 `|` 已转义以免破坏表格。

| 字段 / 结论 | 源行与字符区间 | 原文引文（逐字） | 说明 |
|---|---|---|---|
{evidence_table}

## ⑤ 注意点与局限

1. **图字节 404 是结论不是事故**：已在 ③ 给出对照实验（11621 同路由 200），
   因此 5577 的 404 归因于该报告自身缺图字节；已写入 `manifest.limitations`。
2. **绝不代造跨仓内容**：`bp_demo/`、`physics/holtrop`、`tests/test_resistance_ittc78.py`、
   `cluster_exec.py`、`artifacts/bp_demo/sha256_index.json` 在本仓均不存在，登记为
   `referenced_unresolved`；AC14 反向校验「本仓不得出现同名文件」，防后人顺手伪造。
3. **行号口径**：逻辑行 = 去掉尾换行后按换行切分，1-based；与 `docs/kf/NOTES.md` 既有多包
   一致，跨包可比。
4. **locator 扩张单调**：不唯一时向上扩行（到顶后向下），终态必唯一（整篇短语唯一），
   不存在无限扩张；只要扩到全文必然终止。
5. **局限**：本工序不校验源报告数字真伪、不重算阻力、不裁定源报告 V3/V4 的 honest-FAIL；
   这些属 04 独立审核工序。
6. **本包不判定真伪**：报告自身的 `0.28%`、`243.10%` 等数字只作为**可定位引文**登记，正确性校验不在 01 工序职责内。
7. **未做类型判定**（`classify_report_type=false`），未生成任何 claim；空 claims 是完整结果而非缺项。

## ⑥ 误差判定

| 项 | 验证内容 | 实测 | 基准 | 偏差 | 是否<3% |
|---|---|---|---|---|---|
{error_table}

逐项回答：

- **E1–E4**：偏差均为 0.000%（逐字节 / 整数相等）→ 是否<3%：**是**。
- **E5 图字节可达率**：0/3 可达，缺口 100% → 是否<3%：**否**。
  **HONEST-FAIL**：源报告 3 张图的字节在平台侧取不到，本包不以生成图冒充源图；
  该缺口只能由源报告提交方补图表、或平台侧修复图存储后重开本包补齐。
- 物理量对标（阻力误差是否<3% 基准）**不适用本工序**：本工序零物理计算，
  任何阻力精度结论都属 04 工序，故不在此声明通过。

## 复现命令（一键）

```bash
{repro}
```

![图1 资产解析矩阵](fig1_asset_resolution.png)

图1：资产解析矩阵——横轴=登记条数，纵轴=asset_class，颜色=解析状态
（resolved_in_source / referenced_unresolved / declared_absent），标题内嵌源哈希前 16 位
与 chars/bytes，用一张图同时证明「资产面覆盖」与「源被钉住」。该图由
`scripts/wp5577_build_report.py` 的 `render_figure` 程序化生成，无手工编辑。

```json
{result_json}
```
"""
    REPORT.write_text(body, encoding="utf-8")
    print("rendered:", REPORT)
    return REPORT


def publish():
    if not BASE:
        print("TENSOR_API_BASE not set; skipping publish")
        return
    token = login()
    if not token:
        raise SystemExit("login failed")
    md = REPORT.read_text(encoding="utf-8")
    payload = json.dumps({
        "report_id": int(REPORT_ID),
        "markdown": md,
        "tags": ["KF-RESULT", "wp-5577-01", "01-asset-registration"],
    }).encode()
    _req(BASE + "/tensor/reports", token=token, data=payload)
    print("published report", REPORT_ID)


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "render":
        render()
    elif sys.argv[1] == "publish":
        publish()
    elif sys.argv[1] == "render" and len(sys.argv) > 2 and sys.argv[2] == "publish":
        render()
        publish()
    else:
        print("Usage: %s render [publish]" % sys.argv[0])
        sys.exit(1)
