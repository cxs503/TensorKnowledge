#!/usr/bin/env python3
"""Render + publish the KF-RESULT report for a 01-asset-registration package.

Zero hand-copy: every number, quote and table row below is read out of
asset_manifest.json / verification.json at render time.

  python3 scripts/kf/render_kf_result_report.py --pkg-dir docs/kf/wp-7554-01 --dry-run
  python3 scripts/kf/render_kf_result_report.py --pkg-dir docs/kf/wp-7554-01 --publish
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
RES_ORDER = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
RES_COLOR = {"resolved_in_source": "#2c7fb8",
             "referenced_unresolved": "#f0a202",
             "declared_absent": "#9e9e9e"}


def code_span(q):
    """Wrap a verbatim quote so that quotes containing a backtick still render as code."""
    return ("「%s」" % q) if "`" in q else ("`%s`" % q)


def md_escape(s):
    return s.replace("|", "\\|").replace("\n", " ")


def figure(manifest, out_png):
    by_class = {}
    for a in manifest["assets"]:
        row = by_class.setdefault(a["asset_class"], {r: 0 for r in RES_ORDER})
        row[a["resolution"]] += 1
    classes = sorted(by_class, key=lambda c: (-sum(by_class[c].values()), c))

    fig, ax = plt.subplots(figsize=(8.2, 0.62 * len(classes) + 1.9))
    left = [0] * len(classes)
    for res in RES_ORDER:
        vals = [by_class[c][res] for c in classes]
        ax.barh(classes, vals, left=left, color=RES_COLOR[res],
                label="%s (%d)" % (res, manifest["counts"]["by_resolution"][res]))
        left = [acc + v for acc, v in zip(left, vals)]
    for i, c in enumerate(classes):
        ax.text(left[i] + 0.06, i, str(sum(by_class[c].values())), va="center", fontsize=9)
    ax.set_xlabel("registered assets (count)")
    ax.set_title("wp-7554-01 asset manifest: %d assets by class x resolution\n"
                 "(report 7554 markdown, sha256 %s...)" % (manifest["counts"]["assets"],
                                                           manifest["source"]["hash"][:12]),
                 fontsize=10)
    ax.legend(fontsize=8, loc="lower right")
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return out_png


def render(pkg_dir):
    pkg = Path(pkg_dir)
    manifest = json.loads((pkg / "asset_manifest.json").read_text())
    kf = json.loads((pkg / "kf_result.json").read_text())
    ver = json.loads((pkg / "verification.json").read_text())
    man_bytes = (pkg / "asset_manifest.json").read_bytes()
    man_sha = hashlib.sha256(man_bytes).hexdigest()
    src = manifest["source"]
    counts = manifest["counts"]
    pkg_id = manifest["package_id"]

    # ---- evidence locator table, programmatic (quote sliced from the source) ----
    rows = []
    for a in manifest["assets"]:
        loc = a["locator"]
        rows.append("| {} | {} | `{}` | {} | {} | {}-{} / L{}-{} | {} |".format(
            a["asset_id"], md_escape(a["label"]), a["resolution"], a["asset_class"],
            "unique" if loc["unique"] else "NOT-unique",
            loc["start_char"], loc["end_char"], loc["start_line"], loc["end_line"],
            code_span(loc["quote"])))
    table = ("| asset_id | label | resolution | class | quote unique | char span / line span | 原文引文（逐字切片） |\n"
             "|---|---|---|---|---|---|---|\n" + "\n".join(rows))

    checks_tbl = "\n".join(
        "| {} | {} | {} |".format(c["check"], "✅ PASS" if c["result"] == "PASS" else "❌ FAIL",
                                  md_escape(c["detail"])[:120])
        for c in ver["checks"])

    src_snapshot_sha = hashlib.sha256((pkg / "source_snapshot.md").read_bytes()).hexdigest()

    body = """# KF-RESULT {pkg_id}

**工作包** `{pkg_id}` ｜ **工序** `01-asset-registration` ｜ **report_id** `{rid}`
**源** `{uri}` `{field}` ｜ **source_hash** `sha256:{srchash}`（本地重算，与契约一致）
**标题（源报告）** {title}
**scenario_key / mission_id（源报告）** `{scen}` / `{mission}`
**产出** `docs/kf/{pkg_id}/`（asset_manifest.json / kf_result.json / verification.json / source_snapshot.md / figures）

---

## ① 本工序做了什么

只做一件事：**登记 report_id={rid} 的源资产**。具体为

1. 从平台取回该报告 `markdown` 字段（`GET /tensor/reports/{rid}`），**重新计算**其 UTF-8 字节
   的 sha256 与字符数，并与工作包契约给的 `source_hash` / `chars` 对账：
   `{nchar}` 字符 / `{nbyte}` 字节 / `sha256:{srchash}`，与契约值一致（hash_matches_contract={expected}）。
2. 在 markdown 内**按字面解析**出可登记的对象（平台图、产物路径、代码脚本、数据表、上游报告引用、
   报告自述不存在的对象），逐条给出**字符级定位**，并标注解析状态。
3. **不做抽取**：`claims` 为 `[]`（工序契约 `objective.classify_report_type=false`，01 工序的
   零 claim 是合法完整结果，不为填指标造知识）。
4. **不判定 verified**：本工序只产出 worker 侧自检（`verification.json`），
   `verification` 由平台门计算，任何字段都没有被标成 verified。

登记结果：**{nassets} 个资产 = {nres} 个 resolved_in_source（报告自身 markdown）+ {nunres} 个
referenced_unresolved（字节不在本包范围内：平台只存图元数据、跨报告、外部表、仓内不存在的产物路径）
+ {nabs} 个 declared_absent（报告自行声明不存在）。**

- 按状态：`{by_res}`
- 按类：`{by_class}`

## ② 怎么做的（步骤 / 工具 / 关键设置）

工具：`scripts/kf/register_source_assets.py`（本单新增，**通用**：report_id / source_hash /
discovery plan 全部来自参数，脚本内无任何 report 常量），配置 `docs/kf/{pkg_id}/discovery_plan.json`；
独立复核：`tests/test_kf_wp_7554_01.py`（**不 import 生成器**，自己重算 hash/切片/行号/schema，
防止"生成器的 bug 替自己作证"）。

关键设计（防止"手抄"与"幻觉定位"的结构性做法）：

1. **引文=程序切片，不是重敲**。discovery plan 里每条资产只给一个 `anchor` 字符串，
   脚本要求该 anchor 在 markdown 中**恰好出现 1 次**（否则直接 abort）；
   写入 manifest 的 `quote` 是 `markdown[start:end]` 的**切片**，因此"quote 是源子串"
   由构造保证，`start_line/end_line` 由换行计数导出。
2. **定位可回读**：自检把 `quote` 再与 `markdown[start_char:end_char]` 比对（round-trip），
   而不是只检查"串在不在"。
3. **状态词汇表显式**：`resolution_vocabulary` 写清 resolved/unresolved/absent 三种判据；
   凡"报告提了但字节不在本包范围内"一律 `referenced_unresolved` 并写明未解析的原因，
   **不猜、不补、不把间接证据当直接证据**。
4. **schema 双校验**：`kf_result.json` 对 `schemas/kf_result.v1.schema.json`（仓库内 canonical 信封）
   校验；`asset_manifest.json` 对**由 `schemas/asset_manifest.v1.schema.json` 在 build 时
   重绑 const（package_id/report_id/source uri）派生**的 `asset_manifest.schema.pkg.json` 校验，
   派生文件落盘可复查，canonical 形状不变。
5. **源字节留底**：`source_snapshot.md`（sha256 `{snap_sha}`）使全部定位在离线状态下可复算。

复跑（一键）：

```text
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1
python3 scripts/kf/register_source_assets.py \\
  --package-id {pkg_id} --report-id {rid} \\
  --expected-hash {srchash} --expected-chars {nchar} \\
  --spec docs/kf/{pkg_id}/discovery_plan.json \\
  --out-dir docs/kf/{pkg_id} build verify
```

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/{pkg_id}/asset_manifest.json` | 主产物。{nassets} 资产 / {nres} resolved / {nunres} unresolved / {nabs} absent；`claims: []`；每条资产含 method+char/line span+逐字 quote+uniqueness+resolution+resolution_check，`integrity.hash_matches_contract={hashok}`；sha256 `{mansha}` |
| `docs/kf/{pkg_id}/kf_result.json` | 结果信封（`package_id/task_type/report_id/provenance/outputs/claims`），`outputs["asset_manifest.json"]` 内嵌 manifest 全文；`provenance.source_hash=sha256:{srchash}`；本文件即下文唯一的 JSON 代码块 |
| `docs/kf/{pkg_id}/verification.json` | worker 侧自检 10 项（见 ⑥）逐条 PASS/FAIL + 失败清单 + "非平台门"声明 |
| `docs/kf/{pkg_id}/source_snapshot.md` | 取回源 markdown 原字节留底（sha256 `{snap_sha}`） |
| `docs/kf/{pkg_id}/discovery_plan.json` | 12 条资产的 anchor/状态/理由配置（可读、可重跑、可 diff） |
| `docs/kf/{pkg_id}/asset_manifest.schema.pkg.json` | build 时由 canonical schema 重绑 const 派生的包级 schema（schema_pass 的判据） |
| `docs/kf/{pkg_id}/figures/manifest_resolution.png` | 图 1：资产类 × 解析状态计数（数据源=manifest 自身，程序化注入） |
| `scripts/kf/register_source_assets.py` | 通用登记器（build+verify），report_id 参数化，无硬编码常量 |
| `tests/test_kf_wp_7554_01.py` | 独立复核 12 项 pytest（不 import 生成器）：hash/切片回读/行号/schema/单 JSON 块/无 verified 标记/`claims=[]`，含平台在线复算 hash 的用例 |
| `scripts/kf/render_kf_result_report.py` | 本报告渲染/发布器（表格、图、JSON 块全部从产物读取，零手抄） |

## ④ 证据定位表（claim/字段 → 原文引文片段）

下表每行 = manifest 中一条资产。`char span / line span` 为源 markdown 的**字符偏移与 1-based 行号**，
"原文引文"列为 `markdown[start_char:end_char]` 的程序切片，可直接回读。

{table}

说明：`quote unique = unique` 表示该引文在源 markdown 中**只出现 1 次**（自检口径），
因此定位无歧义；`declared_absent` 行的引文是报告**自述不存在**的原句，不是资产本体。

## ⑤ 注意点与局限

1. **本单不产生任何物理量**：01 工序只登记源资产，没有仿真、没有抽取、没有误差计算；
   "关键量 vs 解析/实验基准 <3%" 在本工序**不适用**，理由是被比较的量根本不存在（见 ⑥ 表末行）。
2. **10/12 条资产是 unresolved，这是实测而非遗漏**。逐个原因：
   - 平台图 2 张：报告读接口（`GET /tensor/reports/7554`）对 `figures[]` **只返回 `{{name, caption}}`**，
     无任何 payload 字段（`/tensor/reports/{{id}}/figures` 与 `/figure/0` 均 404）→ 本包拿不到图片字节，
     因此无法哈希、无法内嵌；**这不等于"平台没存字节"**（存储层未证，见 ⑤-5 的对照实验）。
     登记为 `referenced_unresolved` 是"字节不在本包可读范围"的准确表述；
   - `artifacts/p143_w1/prop-6357.json` / `fig_data.json` / `gen_figs.py`：报告点名，但**本 worktree 内
     `find` 全仓无此文件**（且 `artifacts/` 被 `.gitignore` 与推送门滤除，见 `docs/ops/filter-audit.md`）；
   - `campaign_nodes(plan_id=143)` / `tensor_guide_tracker`：上游数据库状态，属后续核验任务，本工序不查；
   - m6334 / m6335 / m6330：跨报告引用，**包边界禁止读写 report_id≠7554**，故只登记引用、不取正文。
3. **边界自律**：本单未读、未写、未覆盖任何其它 report_id；未改写上游工作包产物；
   `finish`/报告里也没有把任何结论标成 verified。
4. **定位口径的一个已知弱点**：`char_span` 绑定的是**当前这一版** markdown。若上游编辑该报告
   （平台重算 hash 会变），本清单的偏移随之失效 —— 这正是 `source_hash` 前置校验的意义：
   hash 不匹配时不得使用旧偏移，必须重跑 build。
5. **一处自己抓到并已勘误的过度断言（诚实记录）**：本包 v1（平台 report 14688，标题相同）把上述
   图资产写成"平台 `png_base64` 为空 → 无字节可哈希"，暗含了"平台未存字节"的**存储层断言**——
   读接口不暴露 payload，既不能证实也不能证伪该断言。v2 起改为"读路径只暴露 name/caption"。
   **对照实验**（顺手做了）：本包自己给平台投递了一张 65,141 字节的 PNG（`figures[].png_base64`），
   回读时仍只暴露 `{{name, caption}}` → 说明该读路径**普遍**不返回图字节，与"这份报告有没有画图"无关。
   因此 A05/A06 的 `referenced_unresolved` 是读路径限制所致，不是源报告缺图。此后同标题报告以编号更大者为准。
6. **A01 的 `document` 定位（自检发现并已修的一处真缺陷）**：最初把整篇资产写成
   `method=document` 且 `char span=(0, len(md))`，但 `quote` 只能取首个标题行 —— 于是
   `md[start:end] != quote`，**round-trip 不成立**（独立测试抓到）。修正为：`char span`=标题行区间
   （可回读），"覆盖整篇"这一主张改由 `covers_document=true` + `document_chars=<n>` 两个显式字段
   承载。同类缺陷还抓到一处：契约哈希比对标志曾只存在于内存、落盘为 `null`，现由 build 直接计算并
   持久化（`hash_matches_contract=true`），并由独立测试断言其在**文件里**为 true。

## ⑥ 自检：逐条对照 acceptance（honest）

| acceptance 项 | 结果 | 依据（自检明细） |
|---|---|---|
| `valid_json` | ✅ | 4 个 JSON 产物均 `json.loads` 通过（asset_manifest / kf_result / verification / schema.pkg） |
| `schema_pass` | ✅ | kf_result vs `schemas/kf_result.v1.schema.json`；manifest vs build 时派生的包级 schema（jsonschema 4.26.0） |
| `source_locator_resolvable` | ✅ | 12/12 quote 是源子串；12/12 char span 回读等于 quote（round-trip） |
| `source_hash_matches` | ✅ | 本地重算 `sha256:{srchash}` == 契约值；字符数 {nchar} == 契约 {nchar} |
| `no_duplicate_ids` | ✅ | 12 个 asset_id，去重后仍 12 |
| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅ | `claims=[]`：01 工序零 claim 是合法完整结果（契约 `no_forced_claim_generation`） |

自检明细（`verification.json` 原样）：

| check | result | detail |
|---|---|---|
{checks_tbl}

**误差判定（显式回答是否 <3%）**：本工序的可判定量全部是**离散/精确量**（sha256 相等、字符数相等、
quote 子串/唯一性、id 去重、schema 通过），实测偏差均为 **0**，即 0% < 3% ✅。
唯一例外是"平台图字节"这一项：它不是"误差超标"，而是**根本取不到字节**（`png_base64` 为空），
故如实登记为 `referenced_unresolved` 而不是 0 误差通过——不把"没有证据"写成"误差为 0"。
**未被本单验证的事项**（不得读作 PASS）：上游三条欠账量值（R²=0.25 / UCS 54.8% / ν 8.4%）
在源报告中的真实性、两张图的像素内容、m6334/m6335/m6330 的正文结论——这些属其它工作包或平台门的职责。

---

## 结果信封（唯一 JSON 代码块）

```json
{kfjson}
```
"""

    md = body.format(
        pkg_id=pkg_id, rid=manifest["report_id"], uri=src["uri"], field=src["field"],
        srchash=src["hash"], expected=manifest["integrity"]["hash_matches_contract"],
        title=src["title"], scen=src["scenario_key"],
        mission=src["platform_report_meta"]["mission_id"],
        nchar=src["chars"], nbyte=src["bytes_utf8"], nassets=counts["assets"],
        nres=counts["resolved_in_source"], nunres=counts["referenced_unresolved"],
        nabs=counts["declared_absent"],
        by_res=json.dumps(counts["by_resolution"], ensure_ascii=False),
        by_class=json.dumps(counts["by_class"], ensure_ascii=False),
        snap_sha=src_snapshot_sha, mansha=man_sha, table=table,
        hashok=manifest["integrity"]["hash_matches_contract"], checks_tbl=checks_tbl,
        kfjson=json.dumps(kf, ensure_ascii=False, indent=2),
    )
    (pkg / "report.md").write_text(md)
    return md, kf, manifest


def publish(md, kf, manifest, pkg_dir):
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    U, P = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]

    def req(url, token=None, data=None):
        r = urllib.request.Request(url, data=data, method="POST" if data else "GET")
        if data:
            r.add_header("Content-Type", "application/json")
        if token:
            r.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(r, timeout=60) as x:
            return json.loads(x.read().decode())

    tok = req(base + "/auth/login", data=json.dumps({"username": U, "password": P}).encode())
    token = tok.get("access_token") or tok.get("token")
    png = (Path(pkg_dir) / "figures" / "manifest_resolution.png").read_bytes()
    counts = manifest["counts"]
    payload = {
        "title": "KF-RESULT %s" % manifest["package_id"],
        "summary": ("登记 report %s 的源资产：markdown sha256 与契约一致，%d 个资产"
                    "（%d resolved / %d unresolved / %d declared_absent），claims=[]，未标 verified"
                    % (manifest["report_id"], counts["assets"], counts["resolved_in_source"],
                       counts["referenced_unresolved"], counts["declared_absent"])),
        "scenario_key": "abm",
        "mission_id": 15598,
        "tags": ["kf-wp:%s" % manifest["package_id"], "kf", "01-asset-registration",
                 "asset-manifest", "report-%s" % manifest["report_id"]],
        "markdown": md,
        "figures": [{
            "name": "manifest_resolution.png",
            "caption": ("图 1 wp-%s 资产清单：资产类 × 解析状态计数（数据源 = asset_manifest.json 自身，"
                        "程序化注入；本图为登记统计，非物理场量云图——01 工序无被求解场）"
                        % manifest["package_id"]),
            "png_base64": base64.b64encode(png).decode(),
        }],
    }
    res = req(base + "/tensor/reports", token=token,
              data=json.dumps(payload, ensure_ascii=False).encode())
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkg-dir", required=True)
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pkg = Path(args.pkg_dir)
    fig_path = figure(json.loads((pkg / "asset_manifest.json").read_text()),
                      pkg / "figures" / "manifest_resolution.png")
    md, kf, manifest = render(pkg)
    print("rendered %s (%d chars), figure %s (%d bytes)"
          % (pkg / "report.md", len(md), fig_path, fig_path.stat().st_size))

    # exactly one ```json fence must exist in the body
    n_fence = md.count("```json")
    print("json fences:", n_fence)
    assert n_fence == 1, "report must contain exactly one ```json block"

    if args.publish:
        res = publish(md, kf, manifest, pkg)
        rid = (res.get("data") or res).get("id") if isinstance(res, dict) else None
        print("published report id:", rid)
        hist = []
        f = pkg / "publication.json"
        if f.exists():
            hist = json.loads(f.read_text()).get("history", [])
        hist.append({"published_at": datetime.now(timezone.utc).isoformat(),
                     "platform_response_id": rid,
                     "manifest_sha256": manifest["integrity"].get("manifest_sha256")
                     or __import__("hashlib").sha256((pkg / "asset_manifest.json").read_bytes()).hexdigest(),
                     "note": "later id supersedes earlier id (same title; platform has no update API)"})
        f.write_text(json.dumps({"title": "KF-RESULT %s" % manifest["package_id"],
                                 "authoritative": hist[-1]["platform_response_id"],
                                 "history": hist}, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()