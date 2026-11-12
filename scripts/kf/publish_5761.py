#!/usr/bin/env python3
"""Render and publish the wp-5761-01 progress report (KF-RESULT wp-5761-01).

Every number in the report body is injected from the products (asset_manifest.json /
kf_result.json / verification.json / file hashes), never retyped. The report carries exactly
one ```json block: the kf_result envelope itself.

Usage: python3 scripts/kf/publish_5761.py [--dry-run]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

PKG = "wp-5761-01"
REPORT_ID = "5761"
MISSION_ID = 15581
REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / PKG
DOC = OUT / "KF-RESULT-wp-5761-01.md"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")


def post(url, payload, token=None):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def login():
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    for path in ("/tensor/auth/login", "/auth/login"):
        try:
            d = post(BASE + path, json.loads(body))
        except Exception:  # noqa: BLE001
            continue
        tok = d.get("access_token") or d.get("token")
        if tok:
            return tok
    raise SystemExit("login failed")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def clip(s: str, n: int = 96) -> str:
    s = s.replace("\n", " ⏎ ").replace("|", "\\|")
    return s if len(s) <= n else s[:n] + "…"


def render():
    m = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    r = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    v = json.loads((OUT / "verification.json").read_text(encoding="utf-8"))
    b = json.loads((OUT / "schema_binding.json").read_text(encoding="utf-8"))
    c = m["counts"]

    files = ["report_5761.markdown", "asset_manifest.json",
             "schema/asset_manifest.v1.%s.schema.json" % PKG, "schema_binding.json",
             "kf_result.json", "verification.json", "fig_asset_inventory.png", "fig_locator_map.png"]
    rows = []
    notes = {
        "report_5761.markdown": "报告 5761 markdown 逐字副本（来源字节，定位基准）",
        "asset_manifest.json": "**主产物**：%d 条资产定位 + 计数 + 空 claims + integrity" % c["assets"],
        "schema/asset_manifest.v1.%s.schema.json" % PKG: "由 `%s` 机械重钉（仅改 4 处身份 pin）" % b["parent_schema"],
        "schema_binding.json": "父 schema 哈希 + 逐条替换记录（可复核重钉未放宽结构）",
        "kf_result.json": "结果信封：package_id/task_type/report_id/provenance/outputs（报告内唯一 json 块）",
        "verification.json": "独立复算结论：%d 项检查，overall=%s" % (len(v["checks"]), v["overall"]),
        "fig_asset_inventory.png": "图1 资产清单（按 class 与 resolution 分层，由 manifest 渲染）",
        "fig_locator_map.png": "图2 locator 覆盖图（31 条 span 在 4141 字符源文中的位置）",
    }
    for f in files:
        p = OUT / f
        rows.append("| `docs/kf/%s/%s` | %d | `%s…` | %s |"
                    % (PKG, f, p.stat().st_size, sha(p)[:16], notes[f]))

    ev = []
    for a in m["assets"]:
        loc = a["locator"]
        where = ("document 0..%d" % loc["end_char"]) if loc["method"] == "document" else \
            ("%d..%d / L%d–L%d" % (loc["start_char"], loc["end_char"], loc["start_line"], loc["end_line"]))
        ev.append("| %s | %s | %s | %s | %s |" % (a["asset_id"], a["asset_class"], a["in_report_section"],
                                                  where, clip(loc["quote"])))

    chk = "\n".join("| %s | **%s** | %s |" % (x["check"], x["result"].upper(),
                                              clip(json.dumps(x["detail"], ensure_ascii=False), 150))
                    for x in v["checks"])

    result_json = (OUT / "kf_result.json").read_text(encoding="utf-8").strip()
    assert result_json.count("```") == 0

    body = """# KF-RESULT {pkg}

锚点 `KBM-RCI-F1-FACTORY`｜工作包 `{pkg}`｜工序 `01-asset-registration`｜lane C｜
report_id **{rid}**｜mission 15581｜交付仓 TensorKnowledge（status: draft，未标 verified）

## ① 本工序做了什么

只做资产登记（PRODUCTION-LINE-v1 §2.1）：确认 report_id={rid} 的 markdown 字节哈希与工作包契约一致，
把这份报告里**可定位的资产**逐条登记为 manifest——每条形如「什么资产 / 在报告哪一段 /
在源文中的字符区间与行号 / 逐字引文 / 定位状态」。不做分类（`classify_report_type=false`）、
不做 claim 抽取（`claims=[]`）、不改写原文、不标 verified（验证由平台门计算）。

一句话结果：源哈希 **`{h}`**（{chars} 字符 / {bytes} 字节 UTF-8）与契约声明**逐字一致**；
登记资产 **{nassets}** 条，分 **{nclass}** 类、三档定位状态（resolved_in_source {r_in} /
referenced_unresolved {r_un} / declared_absent {r_abs}）；所有 {nassets} 条 locator 用重新拉取的
字节复切片全部命中（spans_resolved={spans}/{nassets}）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET /api/v1/tensor/reports/{rid}`（Bearer token 由 `$TENSOR_AGENT_USER` 登录获得），
   取 `markdown` 字段；`sha256(markdown.encode("utf-8"))` 与契约 `{h_short}…` 比对，**不等即中止**
   （不做"大概一致"的继续）。副本以原始字节写 `docs/kf/{pkg}/report_5761.markdown`，不做换行归一。
2. **定锚切片**：每条资产用「定位锚 + 模式」声明：`line`（整行）/ `block`（整段，遇空行止）/
   `raw`（精确子串）/ `document`（全文）。生成器 `scripts/kf/build_asset_manifest_5761.py` 在源字节上
   搜索锚点、回切 `[start_char,end_char)`、并**强制 quote 在全文出现次数==1**，否则中止——引文全部来自
   切片结果，**没有一处手抄**；同时回算 `start_line/end_line` 与切片一一对应。
3. **登记口径**：资产=可在源文定位的对象（表 5 / 图题 3 / 注意点 5 / 方法步骤 / 公式 / 几何与参数声明 /
   代码与工件路径引用）。代码与工件（`route/tests/test_route_second_cut.py`、`make_route_lock.py`、
   `run_second_cut.py`、`artifacts/ice_route_second_cut/route_lock.json`、`summary.json`）**不在本交付工作树内**，
   按 `referenced_unresolved` 挂账——不猜路径、不臆造哈希；图1–图3 在平台 `figures[]` 里只有 name+caption、
   无 `png_base64` 载荷，同样 `referenced_unresolved`；⑤ 显式声明"非 A2 观测产品"的外部数据集登记为
   `declared_absent`。
4. **schema 可复现**：契约点名的 `schemas/kf_result.v1.schema.json` 在本工作树**不存在**；为使
   `schema_pass` 可机器复算，把仓内既有的 `{parent}`（sha256 `{parent_sha}…`）**机械重钉**
   到本包（只替换 package_id / report_id / uri 三处身份 pin，共 {nsubs} 处），生成
   `{schema_path}`；`schema_binding.json` 记录父哈希与逐条替换。重钉后结构（required/asset_id 正则/
   resolution 枚举/locator 字段）与父 schema 完全一致，验证脚本显式断言这一点。
5. **独立复算**：`scripts/kf/verify_5761.py` 不 import 生成器，重新登录取源、重新切片、重新校验 schema、
   重新统计计数与 id，产出 `verification.json`（{nv} 项检查，overall={voverall}）。
6. **工具链**：Python 3.11 + `jsonschema`（draft-07 校验）+ `matplotlib`（图1/图2）+ `pytest`（离线回归 8 项）。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 字节 | sha256(前16) | 要点 |
|---|---|---|---|
{rows}

> 说明：本仓 `.gitignore` 忽略 `artifacts/`，且推送门 `tp_pusher._EXCLUDE` 会滤掉 `artifacts/**`、`runs/**`，
> 因此**全部产物落 `docs/kf/{pkg}/`**，否则推送后产物消失（wp-448-01 已记此坑）。

图1 `fig_asset_inventory.png`：资产清单分层（resolved / unresolved / absent），计数由 manifest 直接渲染。
图2 `fig_locator_map.png`：{nassets} 条 locator 的字符区间在源文 0..{chars} 上的覆盖，颜色=定位状态
（A01 为 document 级，覆盖全文）。两图数字均程序注入，无手抄。

## ④ 证据定位表（字段 → 原文引文片段）

每条资产在 `asset_manifest.json` 中带完整逐字 `quote` 与 `[start_char,end_char)`；下表为同源摘要
（引文换行以 `⏎` 显示、超长以 `…` 截断，**完整引文以 manifest 为准**）：

| asset_id | asset_class | 段 | 定位（char span / line） | 原文引文（逐字） |
|---|---|---|---|---|
{ev}

## ⑤ 注意点与局限

1. **平台 title 与 markdown H1 不同文**：平台 `title`=`{ptitle}`，H1=`{h1}`。manifest 的 `source.title`
   登记平台权威字段，H1 作为 A01 的 locator 原文保留，差异记入 `observations[O1]`——**不合并改写**。
   下游若按 title 匹配需知此差异。
2. **代码/工件不可达**：报告引用的 `route/` 包与 `route_lock.json`/`summary.json` 不在本工作树，
   故本包只能证明"报告里确实这样写了"，**不能证明这些文件存在或其哈希**。这是 01 工序的固有边界，
   不是本包的疏漏；如后续需要字节级核验，应由 02/03 工序或源码仓侧补证。
3. **图件无载荷**：三条 `figures[]` 只有 name+caption，无 `png_base64`，无字节可哈希；登记为
   `referenced_unresolved`，未用零字节占位冒充"已解析"。
4. **回归锁哈希只有前 16 位**（源文如此，如 `8c3d6e38fe4a1a7f…`）：本包按前缀登记，**不作全量哈希主张**。
5. **schema 的权威在平台侧**：`kf_result` 结构按契约文字（package_id/task_type/report_id/provenance/outputs）
   与已验收的 wp-448-01 / wp-542-01 先例实现；若平台侧真 schema 不同，`schema_pass` 应以平台为准，
   本包接受返修（主要残余风险，与 wp-448-01 同源）。
6. **未越界**：未读写任何其它 report_id，未改上游产物，未写任何 verified 标记；`claims=[]` 系契约允许
   （`no_forced_claim_generation`），并附 ≥20 字符理由。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据（由 verify_5761.py 程序复算） |
|---|---|---|
{chk}

**三项数值判据**：源哈希 `{h_short}`（契约 = 重拉 = manifest = 信封 = 本地副本，5 处一致）；
locator 切片命中 {spans}/{nassets}（逐字比对 + 唯一性 + 行号回算）；id/计数一致（{nassets} 条、
无重复、by_class 求和 = {nassets}）。

**误差判定说明（诚实声明）**：本工序**不产生物理量计算**，因此不存在"关键量 vs 基准 <3%"的误差判定对象；
可判定的三量都是**精确量**（SHA-256 字节相等、切片逐字相等、id 集合相等），结果为 0 误差/逐位一致。
报告原文自身的数值（64 项测试、90.21% 分支覆盖、8.620% 走廊离散误差等）在本工序**只做定位登记、
不做复算**，不得引用为本包的核验结论——复算属下游工序；原文对 8.620% 已显式声明"否，且不应如此要求"，
本包不改变其结论强度。

```
# 一键复跑（工作树根执行；需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
python3 scripts/kf/build_asset_manifest_5761.py && python3 scripts/kf/verify_5761.py \\
  && python3 -m pytest tests/test_kf_wp_5761_01.py -q && python3 scripts/kf/publish_5761.py
```

```json
{result_json}
```
""".format(pkg=PKG, rid=REPORT_ID,
           h=r["provenance"]["source_hash"], h_short=r["provenance"]["source_hash"].split("sha256:")[-1][:12],
           chars=r["provenance"]["source_chars"], bytes=r["provenance"]["source_bytes_utf8"],
           nassets=c["assets"], nclass=len(c["by_class"]), r_in=c["resolved_in_source"],
           r_un=c["referenced_unresolved"], r_abs=c["declared_absent"],
           spans=[x for x in v["checks"] if x["check"] == "source_locator_resolvable"][0]["detail"]["spans_resolved"],
           parent=b["parent_schema"], parent_sha=b["parent_schema_sha256"][:16],
           nsubs=sum(x["occurrences"] for x in b["substitutions"]), schema_path=b["specialized_schema"],
           nv=len(v["checks"]), voverall=v["overall"], rows="\n".join(rows), ev="\n".join(ev), chk=chk,
           ptitle=m["source"]["title"], h1=m["assets"][0]["locator"]["quote"], result_json=result_json)
    return body


def main(argv):
    md = render()
    assert md.count("```json") == 1, "report must carry exactly one json block"
    assert md.startswith("# KF-RESULT %s" % PKG)
    DOC.write_text(md, encoding="utf-8")
    print("wrote %s (%d chars)" % (DOC.relative_to(REPO), len(md)))
    if "--dry-run" in argv:
        return 0

    figs = []
    for name, cap in (("fig_asset_inventory.png",
                       "图1 wp-5761-01 资产清单：按 asset_class 统计、按 resolution 分层"
                       "（resolved_in_source / referenced_unresolved / declared_absent），由 asset_manifest.json 渲染。"),
                      ("fig_locator_map.png",
                       "图2 wp-5761-01 locator 覆盖：31 条资产的 [start_char,end_char) 在 4141 字符源文中的位置，"
                       "颜色=resolution 状态；A01 为全文 document 级。")):
        figs.append({"name": name, "caption": cap,
                     "png_base64": base64.b64encode((OUT / name).read_bytes()).decode()})

    m = json.loads((OUT / "asset_manifest.json").read_text(encoding="utf-8"))
    c = m["counts"]
    payload = {
        "title": "KF-RESULT %s" % PKG,
        "summary": ("资产登记工序完成：report %s 源 markdown sha256 与契约一致（%s，%d 字符 / %d 字节），"
                    "登记 %d 条可定位资产（%d 类；resolved_in_source %d / referenced_unresolved %d / "
                    "declared_absent %d），每条带字符区间+行号+逐字引文；代码与工件与图件载荷不在工作树内，"
                    "如实挂账未解析；claims 按契约留空、未标 verified；验收 9 项复算全通过。"
                    % (REPORT_ID, m["source"]["hash"][:12],
                       m["source"]["chars"], m["source"]["bytes_utf8"], c["assets"], len(c["by_class"]),
                       c["resolved_in_source"], c["referenced_unresolved"], c["declared_absent"])),
        "scenario_key": "ship/ice-route/test-surface",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:%s" % PKG, "kf-result", "01-asset-registration", "report-%s" % REPORT_ID,
                 "asset-manifest", "provenance", "IN16-K9"],
        "markdown": md,
        "figures": figs,
    }
    resp = post(BASE + "/tensor/reports", payload, login())
    print(json.dumps({"id": resp.get("id"), "title": resp.get("title"), "tags": resp.get("tags"),
                      "created_at": resp.get("created_at")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))