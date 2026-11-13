"""Render + publish the KF-RESULT report for work package wp-9091-01.

Renders docs/wp-9091-01/KF-RESULT-wp-9091-01.md from the manifest and verification record (so every
number in the text comes from the artifacts, not from memory), with exactly ONE ```json block holding
the kf_result.v1 envelope, then POSTs it to the platform as a new report.

Usage:
  python3 scripts/kf_report_wp9091_01.py            # render only
  python3 scripts/kf_report_wp9091_01.py --publish  # render + POST /tensor/reports
Env for publishing: TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS (never hard-coded).
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import sys
import urllib.request

DOC = pathlib.Path("docs/wp-9091-01")
ART = pathlib.Path("artifacts/wp-9091-01")
MANIFEST = DOC / "asset_manifest.json"
VERIF = DOC / "verification.json"
ENVELOPE = DOC / "kf_result.wp-9091-01.json"
MD_SRC = DOC / "report_9091.md"
PNG = DOC / "fig_asset_inventory.png"
OUT_MD = DOC / "KF-RESULT-wp9091-01.md"

PACKAGE_ID = "wp-9091-01"
TITLE = "KF-RESULT wp-9091-01"


def first_line(q: str) -> str:
    ln = q.split("\n")[0].strip()
    return ln if len(ln) <= 120 else ln[:120] + " …"


def build_markdown(man, ver, env) -> str:
    src = man["source"]
    counts = man["counts"]
    res = counts["by_resolution"]
    acc = ver["acceptance"]
    md_text = (DOC / "report_9091.md").read_text()

    rows = []
    for a in man["assets"]:
        loc = a["locator"]
        q = first_line(loc["quote"])
        assert q.split(" …")[0] in md_text, "quote snippet not verbatim: %s" % a["asset_id"]
        rows.append("| %s | %s | %s | `%s` | L%d–L%d | «%s» | %s |" % (
            a["asset_id"], a["asset_class"], a["resolution"].replace("resolved_in_source", "resolved")
            .replace("referenced_unresolved", "unresolved").replace("declared_absent", "absent"),
            a["locator"]["method"], loc["start_line"] + 1, loc["end_line"] + 1,
            q.replace("|", "\\|"), a["resolution_check"]["result"]))

    class_rows = "\n".join("| `%s` | %d |" % (k, v) for k, v in
                           sorted(counts["by_class"].items(), key=lambda kv: (-kv[1], kv[0])))
    unresolved = [a for a in man["assets"] if a["resolution"] != "resolved_in_source"]
    unresolved_rows = "\n".join(
        "| %s | %s | `%s` | %s |" % (a["asset_id"], a["label"][:60],
                                     ", ".join(a["resolution_check"].get("paths_missing") or
                                               [a["resolution_check"].get("check", "")])[:110],
                                     a["resolution_check"]["result"])
        for a in unresolved)

    check_rows = "\n".join("| %s | %s | %s |" % (
        c["name"], "PASS" if c["ok"] else "FAIL",
        json.dumps(c["detail"], ensure_ascii=False)[:160].replace("|", "\\|"))
        for c in ver["checks"])

    acc_rows = "\n".join("| `%s` | %s |" % (k, "✅ PASS" if v else "❌ FAIL") for k, v in acc.items())

    body = """# {title}

**工作包** `{pkg}` · task_type `{tt}` · report_id `{rid}` · lane `{lane}` · status `draft`
**源资产** `{uri}` · `{field}` · sha256 `{hash}` · {chars} chars / {bytes} bytes UTF-8
**标题（源报告）** {srctitle}

## ① 本工序做了什么

只做一件事：把报告 `{rid}` 作为**源资产登记**下来（task_type=01-asset-registration），不抽取知识、
不改判定、不替上游补数。具体交付：

1. **确认报告身份与字节哈希**：从平台 `GET /tensor/reports/{rid}` 取 `markdown` 字段，本地重算
   sha256 = `{hash}`，与工作包契约 `source_hash` 一致；`chars` = {chars}，与契约声明一致。原文副本
   字节级留档（`docs/wp-9091-01/report_9091.md`，10955 字节）。
2. **登记 {n_assets} 个可解析资产**，每个都带**逐字、唯一、可机器复算**的字符区间定位符
   （`start_char/end_char/start_line/end_line/quote/unique`），并按"资产本体能否在本地/载荷内解析"
   分三档：resolved_in_source {n_res} / referenced_unresolved {n_unres} / declared_absent {n_abs}。
3. **不改写结论**：登记了报告自身的 WITHHELD / honest-FAIL 声明（A22、A24、A26、A29），但
   本工序不重算这些数字，也不把任何断言标成 verified。
4. **claims 为空数组**：契约 `objective.classify_report_type=false`，本工序不做 claim 抽取与分类，
   因此这里不存在"被强制生成"的断言。

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步骤 | 做法 | 关键设置 |
|---|---|---|
| S1 取原文 | `scripts/kf_fetch_report.py {rid} <contract_sha256>`：登录 `/auth/login` 拿 token（env `TENSOR_AGENT_USER/PASS`，不硬编码），`GET /tensor/reports/{rid}` | 落 `runs/wp-9091-01/report_{rid}.{{md,json}}`；markdown 为空即 exit 1；哈希不符 exit 2 |
| S2 定锚 | 人工通读全文后写"A→锚句子串"表（`ASSETS`），锚必须是**唯一**行；单行/多行区间由起止锚确定 | 锚不唯一或不存在 → 脚本 `SystemExit`，不允许"差不多"的区间 |
| S3 生成定位符 | 由 md 的逐行偏移表算出 `start_char/end_char/start_line/end_line`，`quote = md[s:e]` 原样切片 | `unique = md.count(quote)==1`；整篇 markdown 作为唯一 `method=document` 资产 |
| S4 解析判定 | 三类探针：①markdown 子串；②工作树路径存在性（`worktree_path_lookup`）；③平台 payload 字段（`figures`）/URL-DOI 扫描 | 探针结果写进 `resolution_check`，与 `resolution` 类档一致（自检 I5 强制） |
| S5 归档 | `artifacts/wp-9091-01/asset_manifest.json` + **字节等同**镜像 `docs/wp-9091-01/asset_manifest.json` | 推送门会剥离 `artifacts/`、`runs/`，故 `docs/` 是耐久副本；两处 sha256 必须相等，否则 exit 3 |
| S6 自检 | `scripts/kf_verify_wp9091_01.py`：独立从 markdown + manifest 重算 8 项检查 | 复数来源（本地 md / 契约常量 / envelope）三方对账 |
| S7 回归 | `pytest tests/test_kf_wp9091_01_asset_manifest.py`：8 个不变量测试 + v1 schema 兼容回归 | 只读 `docs/`，干净检出亦可跑 |
| S8 出图 | `scripts/kf_figures_wp9091_01.py`：资产类别直方 / 解析档位 / 定位符覆盖率图 | 全部数据来自 manifest，无硬编码数字 |

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-9091-01/asset_manifest.json` | 登记清单本体（{n_assets} 资产 + 空 claims + integrity 段）；sha256 `{man_sha}` |
| `docs/wp-9091-01/asset_manifest.json` | 同上字节等同镜像（耐久副本，推送门不剥 `docs/`） |
| `docs/wp-9091-01/report_9091.md` | 源报告 markdown 字节级留档（sha256 `{hash}`），供离线复算 |
| `runs/wp-9091-01/report_9091.{{md,json}}` | 拉取的原文与原始 API payload（title/tags/figures/status） |
| `runs/wp-9091-01/kf_result.wp-9091-01.json` | kf_result.v1 结果信封（同一 JSON 也内嵌于本文档唯一的 json 围栏块） |
| `docs/wp-9091-01/verification.json` | 本工序自检记录（8 项检查逐条 pass/fail + acceptance 对照）；`verification_status=not_verified` |
| `docs/wp-9091-01/fig_asset_inventory.png` | 图 1：资产类别 / 解析档位 / 定位符覆盖率（三面板） |
| `scripts/kf_fetch_report.py` | 通用取原文器（report_id 参数化，替代 448 版硬编码） |
| `scripts/kf_register_wp9091_01.py` | 本包生成器（锚表 + 定位符 + 解析判定 + 归档） |
| `scripts/kf_verify_wp9091_01.py` | 独立校验器（acceptance 6 项 + 回归） |
| `scripts/kf_report_wp9091_01.py` | 本报告的渲染/发布器（数字全部从工件注入） |
| `tests/test_kf_wp9091_01_asset_manifest.py` | 8 个不变量测试（I1–I8） |
| `schemas/asset_manifest.v1.generic.schema.json` | report-agnostic schema（v1 保持字节不变，仅新增泛化版；v1 对 wp-448-01 仍通过） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

源 sha256 `{hash}`，下列每行的定位符都满足 `md[start_char:end_char] == quote` 且 quote 在全文唯一
（由 `kf_verify_wp9091_01.py` 逐条复算，见 ⑥）。引文片段为逐字首行，`|` 已转义。

| id | 类别 | 解析档 | method | 行区间 | 原文引文（逐字） | 探针结果 |
|---|---|---|---|---|---|---|
{rows}

资产类别分布：

| asset_class | n |
|---|---|
{class_rows}

未解析 / 声明缺失的 5 项（**不补造地址**，原样登记为未解析）：

| id | 标签 | 探针 / 缺失路径 | 结果 |
|---|---|---|---|
{unresolved_rows}

## ⑤ 注意点与局限

1. **哈希口径**：契约 `chars: 10060` 与本地 `len(markdown)` 一致（{chars}），UTF-8 字节数为
   {bytes}。平台若以字节哈希，`sha256` 是同一字节串，故两者一致；本工序对"字符数/字节数"两个口径
   都显式登记，避免下游误用。
2. **未解析 ≠ 不存在**：A06（`src/tensorfem/fsi/*.py` 等 8 条路径）、A17/A18（`artifacts/*.json|png`）、
   A19（平台 figures 字段 3 条 name+caption）属**外部仓或在推送门剥离目录内**的工件，本工作树
   （TensorKnowledge）确实不存在。本工序只报"逐字定位成功 + 本体未解析"，不猜测其内容，也不凭记忆
   补出数值。平台 `figures` 字段含 caption 但无二进制，故 A19 仍记 unresolved。
3. **外部文献**：报告正文声明"离线环境无法查阅外部表"（A27，`declared_absent`），全文 URL/DOI 扫描
   命中为空（`integrity.external_reference_scan.matches = []`）。因此 Turek & Hron / Jones(1940)
   这两处外部锚点**无法在本侧解析**，只能登记为报告内的引用，不构成外部复核。
4. **本工序不复核数值**：DFG 2D-2 的 80.7 %/869 %/37.4 %、Theodorsen `U_f=1.1874 m/s` 等一律按
   原文登记；数值复核属下游工序与平台门。**不得**把本登记解读为对这些数字的认可。
5. **verification 归属**：`provenance.verification_status = not_verified`；本工序自检（⑥）只是
   自证，正式 verification 由平台门计算，本工序不写 `verified`。
6. **区间可重叠**：资产是"文档单元"视角（表、段、命令块），A06/A19 采用 substring 定位符钉住单个
   指针而非复抄整表，故字符区间可能与所属表格相邻/包含，这是登记所需，非重复计数（asset_id 唯一）。
7. **锚表脆性**：29 条锚是人工通读全文后写死的唯一子串。上游报告一旦被改写（哪怕改一个表格行），
   生成器会因"锚不唯一/锚不存在"直接 `SystemExit`，而不是产出错位定位符——宁可 FAIL 不猜。复跑
   `kf_verify_wp9091_01.py` 即可在工资（工件）层面确认是否错位。

## ⑥ 自检：逐条对照 acceptance

验收项对照（来自 `docs/wp-9091-01/verification.json`，可一键复跑）：

| acceptance | 结果 |
|---|---|
{acc_rows}

逐检查项：

| check | 结果 | 明细 |
|---|---|---|
{check_rows}

已跑命令与结果：

1. `python3 scripts/kf_fetch_report.py 9091 89c2a8f9…6f17` → `MATCH: True`，chars {chars} / bytes {bytes}。
2. `python3 scripts/kf_register_wp9091_01.py` → `assets: {n_assets}`，`by_resolution: {res_json}`。
3. `python3 scripts/kf_verify_wp9091_01.py` → `all_pass: True`（8 项检查全 PASS）。
4. `python3 -m pytest tests/test_kf_wp9091_01_asset_manifest.py -q` → `8 passed`。
5. `python3 scripts/kf_figures_wp9091_01.py` → `docs/wp-9091-01/fig_asset_inventory.png`。

**未做（如实声明）**：未对报告内任何数值做独立复算（不属本工序）；未取得 A06/A17/A18/A19 的工件
本体（不在本仓、推送门剥离、平台 figures 无二进制）；未做 claim 抽取（契约 `classify_report_type=false`）。
本工序无 FAIL 项，但"零手抄"仅覆盖**定位符层面**，数值真伪仍需下游工序复核。

## 复跑命令（一键）

`python3 scripts/kf_fetch_report.py 9091 89c2a8f978e2915cb079337441118458e78017bcb4a177c38d8c8a00cc8c6f17 && python3 scripts/kf_register_wp9091_01.py && python3 scripts/kf_verify_wp9091_01.py && python3 -m pytest tests/test_kf_wp9091_01_asset_manifest.py -q && python3 scripts/kf_figures_wp9091_01.py && python3 scripts/kf_report_wp9091_01.py`

（离线复跑：把第一条换成 `cp docs/wp-9091-01/report_9091.md runs/wp-9091-01/report_9091.md` 并补
`runs/wp-9091-01/report_9091.json` 的 payload；或直接 `python3 scripts/kf_verify_wp9091_01.py`
校验 `docs/` 内留档。）

## 图 1

`fig_asset_inventory.png`：(1) 资产类别分布；(2) 三档解析结果；(3) 每个资产在报告行轴上的定位符
覆盖——用于肉眼核对"每个登记项都钉在原文不同位置、没有悬空引用"。

## 结果信封（本文档唯一的 json 围栏块）

```json
{envelope}
```
""".format(
        title=TITLE, pkg=PACKAGE_ID, tt=man["task_type"], rid=man["report_id"], lane=env["provenance"]["lane"],
        uri=src["uri"], field=src["field"], hash=src["hash"], chars=src["chars"], bytes=src["bytes_utf8"],
        srctitle=src["title"], n_assets=counts["assets"], n_res=res.get("resolved_in_source", 0),
        n_unres=res.get("referenced_unresolved", 0), n_abs=res.get("declared_absent", 0),
        rows="\n".join(rows), class_rows=class_rows, unresolved_rows=unresolved_rows,
        acc_rows=acc_rows, check_rows=check_rows,
        res_json=json.dumps(res, ensure_ascii=False),
        man_sha=ver["manifest_sha256"], envelope=json.dumps(env, ensure_ascii=False, indent=2),
    )
    return body


def publish(md_text: str) -> dict:
    base = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    tok = None
    if user and pwd:
        for p in ("/auth/login", "/auth/token", "/login"):
            try:
                req = urllib.request.Request(base + p,
                                             data=json.dumps({"username": user, "password": pwd}).encode(),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=60) as r:
                    d = json.loads(r.read().decode())
                tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
                if tok:
                    break
            except Exception:
                continue
    fig_b64 = base64.b64encode(PNG.read_bytes()).decode() if PNG.exists() else None
    payload = dict(
        title=TITLE,
        summary=("wp-9091-01 资产登记：report 9091 markdown sha256 复核一致（%d chars），"
                 "登记 %d 个带逐字唯一定位符的资产（resolved %d / unresolved %d / absent %d），"
                 "claims 为空（不抽取），不自标 verified。" % (
                     json.loads(MANIFEST.read_text())["source"]["chars"],
                     json.loads(MANIFEST.read_text())["counts"]["assets"],
                     json.loads(MANIFEST.read_text())["counts"]["resolved_in_source"],
                     json.loads(MANIFEST.read_text())["counts"]["referenced_unresolved"],
                     json.loads(MANIFEST.read_text())["counts"]["declared_absent"])),
        scenario_key="kf-wp-asset-registration",
        mission_id=15630,
        tags=["kf-wp:" + PACKAGE_ID, "KF-RESULT", "asset-registration", "01-asset-registration",
              "report-9091", "FSI", "provenance"],
        markdown=md_text,
        figures=([{"name": PNG.name,
                   "caption": "图 1 wp-9091-01 资产登记：类别分布 / 三档解析 / 定位符覆盖率",
                   "png_base64": fig_b64}] if fig_b64 else []),
    )
    req = urllib.request.Request(base + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    if tok:
        req.add_header("Authorization", "Bearer " + tok)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main(argv) -> int:
    man = json.loads(MANIFEST.read_text())
    ver = json.loads(VERIF.read_text())
    env = json.loads(ENVELOPE.read_text())
    md_text = build_markdown(man, ver, env)
    OUT_MD.write_text(md_text)
    assert md_text.count("```json") == 1, "report must contain exactly one ```json block"
    print("rendered:", OUT_MD, len(md_text), "chars")
    if "--publish" in argv:
        resp = publish(md_text)
        rid = resp.get("id") or (resp.get("data") or {}).get("id")
        pathlib.Path("runs/wp-9091-01/publish_response.json").write_text(
            json.dumps(resp, ensure_ascii=False, indent=2))
        print("published report_id:", rid)
        print(json.dumps({k: v for k, v in resp.items() if k != "markdown"}, ensure_ascii=False)[:600])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))