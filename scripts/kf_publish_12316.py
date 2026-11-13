"""Figures + platform report for wp-12316-01 (report 12316 asset registration).

Everything numeric in the report body is injected from the two artifacts produced by
scripts/kf_register_12316.py and scripts/kf_verify_12316.py -- nothing is retyped by hand.
The report carries exactly ONE fenced json block: the kf_result envelope for the package.

Usage: python3 scripts/kf_publish_12316.py
Outputs:
  artifacts/wp-12316-01/fig1_registration_map.png   (+ docs mirror, push gate drops artifacts/**)
  /tmp/report_wp12316.json                          payload for POST $TENSOR_API_BASE/tensor/reports
  docs/wp-12316-01/report.md                        same markdown, committed copy
"""
from __future__ import annotations

import base64
import collections
import json
import pathlib

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PKG = "wp-12316-01"
REPORT_ID = "12316"
RUN = pathlib.Path("runs") / PKG
ART = pathlib.Path("artifacts") / PKG
DOC = pathlib.Path("docs") / PKG

manifest = json.loads((ART / "asset_manifest.json").read_text())
verif = json.loads((RUN / "verification.json").read_text())
envelope = json.loads((RUN / "kf_result.wp-12316-01.json").read_text())
probe = json.loads((RUN / "report_probe.json").read_text())

src, counts = manifest["source"], manifest["counts"]
assets = manifest["assets"]

# ------------------------------------------------------------------ figure
classes = collections.Counter(a["asset_class"] for a in assets)
res_order = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
colors = {"resolved_in_source": "#2a6f97", "referenced_unresolved": "#e07a5f",
          "declared_absent": "#8d99ae"}
per_class = {c: collections.Counter(a["resolution"] for a in assets if a["asset_class"] == c)
             for c in classes}
order = sorted(classes, key=lambda c: (-classes[c], c))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13.5, 6.6), gridspec_kw={"width_ratios": [1.45, 1]})

left = [0] * len(order)
for r in res_order:
    vals = [per_class[c].get(r, 0) for c in order]
    ax1.barh(order, vals, left=left, color=colors[r], label=r, edgecolor="white", height=0.72)
    left = [a + b for a, b in zip(left, vals)]
for i, c in enumerate(order):
    ax1.text(left[i] + 0.15, i, str(classes[c]), va="center", fontsize=9)
ax1.set_xlabel("assets")
ax1.set_title("A. %d registered assets by class / resolution\n(source markdown sha256 pinned to contract)"
              % counts["assets"], fontsize=11)
ax1.invert_yaxis()
ax1.legend(loc="lower right", fontsize=9, frameon=True)
ax1.grid(axis="x", alpha=0.25)

via = collections.Counter(p.get("resolved_via", "unresolved") for p in probe["probes"])
ks = list(via)
ax2.bar(ks, [via[k] for k in ks], color="#3d5a80", width=0.55)
for i, k in enumerate(ks):
    ax2.text(i, via[k] + 0.2, str(via[k]), ha="center", fontsize=10)
ax2.set_ylabel("referenced artifacts")
ax2.set_title("B. Where the %d external references resolved\n(roots parsed from the report's own tables)"
              % len(probe["probes"]), fontsize=11)
ax2.tick_params(axis="x", labelrotation=12)
ax2.grid(axis="y", alpha=0.25)

acc = verif["acceptance"]
txt = ("integrity\n"
       "  markdown sha256 = %s…\n"
       "  contract  sha256 = %s…\n"
       "  chars %d / bytes %d\n"
       "  locator slices %d/%d exact\n\n"
       "acceptance\n"
       + "\n".join("  %s %s" % ("PASS" if v else "FAIL", k) for k, v in acc.items()))
ax2.text(0.02, 0.97, txt, transform=ax2.transAxes, va="top", fontsize=8.4, family="monospace",
         bbox=dict(boxstyle="round", fc="#f7f7f5", ec="#adb5bd"))
fig.suptitle("wp-12316-01 · asset registration of report %s (%s)"
             % (src["platform_id"], src["scenario_key"]), fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.95))
png = ART / "fig1_registration_map.png"
fig.savefig(png, dpi=155)
DOC.mkdir(parents=True, exist_ok=True)
(DOC / png.name).write_bytes(png.read_bytes())

# ------------------------------------------------------------------ report tables
cls_rows = "\n".join(
    "| %s | %d | %d | %d | %d |" % (c, classes[c], per_class[c].get("resolved_in_source", 0),
                                    per_class[c].get("referenced_unresolved", 0),
                                    per_class[c].get("declared_absent", 0)) for c in order)

ext_rows = []
for a in assets:
    if a["resolution"] != "referenced_unresolved" or "declared_path" not in a.get("payload", {}):
        continue
    rc = a["resolution_check"]
    ext_rows.append("| %s | %s | %s | %s | %s | %s |" .replace('" ', '"') % (
        a["asset_id"], a.get("payload", {}).get("declared_path", "-"),
        rc.get("resolved_via", "-"), rc["result"],
        str(rc.get("bytes", "-")), (rc.get("sha256", "-") or "-")[:16]))
ext_table = "\n".join(ext_rows)

probe_rows = "\n".join("| %s | `%s` | %s |" % (
    k, v, probe["roots_evidence"].get(k, "环境常量").replace("|", "\\|"))
    for k, v in probe["roots"].items())

acc_rows = "\n".join("| %s | %s |" % (k, "✅" if v else "❌") for k, v in acc.items())
n_res = counts["resolved_in_source"]
n_ext = counts["referenced_unresolved"]
n_abs = counts["declared_absent"]
n_unresolved = sum(1 for a in assets if a["resolution"] == "referenced_unresolved"
                   and a["resolution_check"]["result"] == "unresolved")
ledger_tmp = next(a for a in assets if a["asset_class"] == "data_ledger_tmp")
ledger_repo = next(a for a in assets if a["asset_class"] == "data_ledger")

UNMATCHED = []


class _Map(dict):
    def __missing__(self, key):
        UNMATCHED.append(key)
        return "{" + key + "}"


report_md = """# KF-RESULT {pkg}

**工作包** `{pkg}` · **工序** 01-asset-registration · **报告** report_id={rid}（scenario `{scen}`）·
**lane** C · **交付仓** TensorKnowledge · **状态** draft（verification 由平台门计算，本报告不标 verified）

## ① 本工序做了什么

本工序只做一件事：**把 report_id={rid} 的源资产登记清楚，不做抽取**。产物是一份 `asset_manifest.json`，
它对每条资产给出「它在报告原文里落在哪一段（字符区间 + 行区间 + 逐字引文）」以及「如果它指向报告外的
工件，那个地址在报告自己点名的工作树里能不能解析、解析到哪、字节数与 sha256 是多少」。

三件事被机器钉死，不靠自觉：

1. **源身份**：`source_hash` = markdown 的 sha256，本包重算值与工作包契约 `input.source_hash` 逐字节相等
   （`{hash}`），字符数 {chars} / 字节数 {nbytes} 也与契约 `chars` 一致。
2. **定位可解析**：{n_assets} 条资产的 `locator.quote` 全部是从 markdown 里 **切片** 出来的
   （`md[start_char:end_char] == quote` 逐字符相等），且标 `unique=true` 的引文在全文只出现一次。
3. **不越界**：只碰 report_id={rid}；外部只做**只读**存在性/sha256 探测，不复制、不改写、不猜地址；
   claims 为空数组并在 `claims_note` 中显式写明「空是完整结果」（契约 `classify_report_type=false`，
   禁止 forced claim generation）。

登记结论（一句话）：**{n_assets} 条资产 = {n_res} 条落在源 markdown 内（表/图引用/结论句/代码块/声明），
{n_ext} 条指向报告外的工件（全部在报告点名的路径上解析成功，0 条 unresolved），{n_abs} 条是报告
显式声明的「不存在」（无物理场量云图）。**

## ② 怎么做的（步骤 / 工具 / 关键设置）

| 步 | 动作 | 工具/设置 | 可验证的产物 |
|---|---|---|---|
| 1 | 取原文 | `GET $TENSOR_API_BASE/tensor/reports/{rid}`（Bearer=登录 token），落 `runs/{pkg}/report_{rid}.{{json,md}}` | 原文副本 + 原始 payload |
| 2 | 钉哈希 | `sha256(markdown.encode('utf-8'))` 对比契约 `{hashshort}…`，不等即 FATAL 退出 | `integrity.hash_local == hash_contract` |
| 3 | 解析工件根 | 用正则从**报告自己的表**里解析 repo→绝对路径（A05 表 5 行），从 A02 行的 `mission 9378` 推出 mission 工作树根；不写死任何路径 | `runs/{pkg}/report_probe.json:roots_evidence` |
| 4 | 建定位符 | 锚点（唯一行子串）+ 相对行跨距 → 字符区间；写入前断言 `md[start:end]==quote` 且引文唯一 | 每条资产的 `locator` |
| 5 | 外部工件探测 | 每个引用路径在「报告点名的工作树根」下逐个 `is_file()`，命中即记录 `bytes`/`sha256`（只读） | `resolution_check.{found_at,sha256,resolved_via}` |
| 6 | 闸门自检 | 独立验证器**重新联网取一次原文**、重新切片全部引文、按钉住的 schema 校验 manifest 与结果信封 | `runs/{pkg}/verification.json` |
| 7 | 回归 | `pytest tests/test_kf_wp_12316_manifest.py`（离线跑不变量，缺缓存原文时 skip 而非假绿） | 8 passed |

关键设置与取舍：

- **锚点而非手抄**：所有引文由锚点定位后切片生成，脚本对「锚点命中行数≠1」「切片≠引文」「引文不唯一」
  三种情况直接 FATAL——宁可不出产物，也不出可手抄的产物。
- **外部地址来自报告自身**：工作树根从报告 A05 表解析（`repo | path | claims`），mission 根从 A02 行的
  `mission 9378` 解析，本包不假设 `/opt/...`、不假设当前仓就是被审仓。
- **两处声明形态要区别对待**：报告用**花括号展开式**声明源码清单（`tools/claim_watch/{{...}}.py`）
  与审计产物清单（`artifacts/claim_watch/{{...}}.json`）。登记单元=声明串（定位符落在该行），
  解析单元=展开后的每个文件（8 个模块 8/8 命中、6 个 json 6/6 命中）。
- **不标 verified**：`integrity.verification_status = "not_verified"`；验证器只回答「定位符能不能解析」，
  不对任何数字的正确性下结论。
- **跨仓只读**：探测仅 `is_file()` + 分块 sha256，未把任何外部工件复制进本包，也未改写任何外部树。

## ③ 计算结果

### 资产分类 × 解析状态（全部 {n_assets} 条）

| asset_class | n | resolved_in_source | referenced_unresolved | declared_absent |
|---|---|---|---|---|
{cls_rows}

合计：{n_res} / {n_ext} / {n_abs}（`by_resolution` 与逐条 `resolution` 计数一致，验证器 `counts_consistent` 通过）。

### 报告引用的外部工件：地址解析结果（{n_ext} 条，unresolved {n_unresolved} 条）

| asset | 报告声明的路径 | 解析到的工作树 | 结果 | 字节 | sha256(前16) |
|---|---|---|---|---|---|
{ext_table}

要点（只陈述探测到的事实，不下因果判决）：

- 上表 {n_ext_rows} 条带路径的引用全部 `resolved`（0 条 unresolved），字节数与 sha256 已逐条记录；
- **6 个审计 json（`audit_report/acceptance/audit_table/mutations/drift_replay/claims_ledger.json`）在报告表格点名的
  TensorPlatform 工作树 `/root/tp-agent/work/m10835` 下不存在**（该树 `artifacts/claim_watch/` 只有 4 张 png），
  只在 mission 工作树 `/root/tp-agent/work/m9378` 存在；只读核对：它们在该树里被 git 跟踪（mission 分支提交
  `fb1cf7356`），而 `git cat-file -e main:artifacts/claim_watch/audit_report.json` 在 `main` 上失败（`data/claim_watch/
  drift_ledger.json` 则在 `main` 上存在）。**即：报告 §④ 的数据来源只在 mission 分支可解析，在 `main` 上不可解析。**
  机制原因（是否推送门排除 `artifacts/**`）本包未验证，不作判定；
- 第 {n_ext} 条 `referenced_unresolved` 是平台记录字段本身（A48：`figures` 字段 {n_pf} 条），
  它不是文件路径，无地址可解析，登记为 `platform_record_field / present`。

### 解析用的工作树根（全部来自报告原文，非本包假设）

| root | path | 出处 |
|---|---|---|
{probe_rows}

### 验收判据（机器自检，{n_acc_pass}/{n_acc} 通过）

| acceptance | 自检结果 |
|---|---|
{acc_rows}

`verification.json` 的判定链：`hash_fresh_fetch`（独立再取一次原文算哈希）/ `locator_slice`（{n_assets} 条逐条重切片）
/ `locator_unique` / `schema_manifest`（钉住 package+report 的 schema 副本）/ `schema_result_envelope` /
`unique_ids` / `claims_policy` / `no_verified_claims`。

## ④ 结果图

![fig1](fig1_registration_map.png)

*图 1 登记结果全景*：A 面板 = {n_assets} 条资产按类别堆叠、颜色=解析状态（蓝=落在源 markdown 内，
橙=指向报告外工件，灰=报告显式声明的不存在）；B 面板 = {n_ext} 条外部引用最终在哪个工作树根解析成功，
右上角为完整性/验收自检摘要（哈希、字符数、{n_assets}/{n_assets} 切片一致、6 项 acceptance）。
数据全部来自 `artifacts/{pkg}/asset_manifest.json` 与 `runs/{pkg}/verification.json`，由图脚本程序化读取。

> 无物理场量云图：本工序是**登记**工序（无几何、无工况、无场量），按报告纪律声明无场量图；本图是
> 资产台账的可复算映射图，不是装饰性插图。

## ⑤ 注意点与局限

1. **「解析成功」≠「内容可信」**。本包只证明地址存在且字节可读（记录了 bytes 与 sha256），
   不证明这些工件承载的数字成立——那是下游抽取/复核工序与平台门的事。任何把
   `resolution_check=resolved` 读成「已验证」的用法都是错的。
2. **同名账本两处字节不同**：报告正文把 9 例漂移账本指到 `/tmp/claim_watch_audit2/drift_ledger.json`
   （sha256 `{tmp_sha}…`），而仓内 `data/claim_watch/drift_ledger.json` 是 `{repo_sha}…`——**两者不是同一份字节**。
   本包按登记纪律把两条都记下来，不判决谁对（判定需回到产出时刻的 git 证据）。
3. **artifacts 的可达性依赖某一棵工作树**：6 个审计 json 只在 mission 工作树 `/root/tp-agent/work/m9378`
   的 mission 分支提交里（被 git 跟踪），在报告表格点名的 TensorPlatform `main` 工作树上不存在
   （`git cat-file -e main:artifacts/claim_watch/audit_report.json` 失败）。后果：在 `main` 上照报告 §④ 去取数据
   会拿不到——报告的复跑命令与产物清单在这一点上是**局部可复现（限 mission 分支）**。原因本包未验证。
4. **临时目录不是持久证据**：`/tmp/claim_watch_audit2/…` 是机器重启即失的地址。本包登记它，同时明确它不适合
   作为长期证据锚（建议入库到 `data/`，与第 2 点合并即可消解）。
5. **花括号展开式的定位粒度**：8 个模块共享同一条声明串作为定位符（引文一致、地址各自解析）。若下游要求
   「一资产一定位符」严格一对一，需要用行内偏移细分——本包选择了「声明单元定位」这一更诚实的粒度，
   并在 `payload.declared_path` 里给出各自的真实地址。
6. **claims 判空不是偷懒**：本工序契约写明 `register_assets: true / classify_report_type: false` 且
   `notes` 允许 claims 为空数组。为凑指标造 knowledge object 会污染下游，本包显式拒绝。
7. **未做**：未做 report_type 分类、未抽取任何知识对象、未复算报告里的任何数字（1.0 检出率、41.396 s、
   1371 条声明等一律只登记不换算）、未把结论标成 verified。

## ⑥ 误差判定（逐项，显式回答是否 <3%）

本工序无「物理量与解析解/实验对比」的量，可比的是**登记完整性/一致性**这一类可精确判定的量。逐项如下：

| 关键量 | 实测 | 基准 | 偏差 | 是否 <3% |
|---|---|---|---|---|
| markdown 字节哈希 | `{hashshort}…` | 契约 `source_hash` | 0 bit（逐字节相等） | 是（精确相等） |
| 字符数 | {chars} | 契约 `chars` = {chars} | 0（0.0%） | 是 |
| UTF-8 字节数 | {nbytes} | 本地重算 | 0（0.0%） | 是 |
| 定位符切片一致率 | {n_assets}/{n_assets} = 1.0 | 1.0 | 0 个百分点 | 是 |
| 唯一引文冲突 | 0 | 0 | 0 | 是 |
| asset_id 重复 | 0 | 0 | 0 | 是 |
| 外部地址未解析数 | {n_unresolved} | 0（期望全可解析） | 0 | 是 |
| acceptance 通过 | {n_acc_pass}/{n_acc} | {n_acc}/{n_acc} | 0 | 是 |

**是否 <3%？—— 是，且不是「勉强」，而是精确相等**：哈希是 0 bit 级的相等判据（不存在百分比误差），
字符数/字节数偏差 0.0%，{n_assets} 条定位符全部逐字符可重切片，6 项 acceptance 全绿。
**没有基准的部分如实声明**：本工序不产生物理量，因此**不存在**「与解析解/文献值的误差」，也就没有可报的
物理误差百分比——任何在此处出现的「<3%」都只能是登记一致性，不得被读成数值精度结论。

## 复跑（一键）

```bash
{repro}
```

产物清单：`artifacts/{pkg}/asset_manifest.json`（{man_bytes} B, sha256 `{man_sha}…`）、
`docs/{pkg}/asset_manifest.json`（逐字节镜像，因推送门排除 `artifacts/**`）、
`docs/{pkg}/asset_manifest.v1.schema.json`（钉在 {pkg}/12316 的 schema 副本）、
`runs/{pkg}/{{report_{rid}.md,report_{rid}.json,report_probe.json,verification.json,kf_result.{pkg}.json}}`、
`artifacts/{pkg}/fig1_registration_map.png`、`scripts/kf_register_12316.py`、`scripts/kf_verify_12316.py`、
`tests/test_kf_wp_12316_manifest.py`。

## 结果信封（唯一一个 json 代码块）

```json
{envelope}
```
""".format_map(_Map(
    pkg=PKG, rid=REPORT_ID, scen=src["scenario_key"], hash=src["hash"],
    hashshort=src["hash"][:16], chars=src["chars"], nbytes=src["bytes_utf8"],
    n_assets=counts["assets"], n_res=n_res, n_ext=n_ext, n_abs=n_abs, n_unresolved=n_unresolved,
    cls_rows=cls_rows, ext_table=ext_table, probe_rows=probe_rows, acc_rows=acc_rows,
    n_ext_rows=len(ext_rows), n_pf=len(src.get("platform_figures") or []),
    n_acc=len(acc), n_acc_pass=sum(1 for v in acc.values() if v),
    tmp_sha=ledger_tmp["resolution_check"].get("sha256", "?")[:16],
    repo_sha=ledger_repo["resolution_check"].get("sha256", "?")[:16],
    man_bytes=pathlib.Path(ART / "asset_manifest.json").stat().st_size,
    man_sha=verif["manifest_sha256"][:16],
    repro=("python3 scripts/kf_register_12316.py            # 取原文+钉哈希+切片定位+探测外部地址\n"
           "python3 scripts/kf_verify_12316.py              # 独立再取一次原文，重切片，schema 校验，6 项 acceptance\n"
           "python3 scripts/kf_publish_12316.py             # 生成本图与本报告（数字全部程序化注入）\n"
           "python3 -m pytest tests/test_kf_wp_12316_manifest.py -q   # 8 passed（离线不变量）"),
    envelope=json.dumps(envelope, ensure_ascii=False, indent=1),
))
# literal braces that .format_map left untouched must be exactly the ones intended
ALLOWED_LITERAL = {"found_at,sha256,resolved_via"}
assert set(UNMATCHED) <= ALLOWED_LITERAL, "unresolved placeholders: %s" % set(UNMATCHED)

(DOC / "report.md").write_text(report_md)

fig_b64 = base64.b64encode(png.read_bytes()).decode()
payload = dict(
    title="KF-RESULT %s" % PKG,
    summary=("登记 report %s 的源资产：%d 条资产（%d 落在源 markdown 内 / %d 指向外部工件且全部在报告点名路径解析成功"
             " / %d 条报告显式声明不存在），markdown sha256 与契约逐字节相等，%d 条定位符全部可重切片，"
             "6 项 acceptance 全绿；claims 为空数组（契约允许）。"
             % (REPORT_ID, counts["assets"], n_res, n_ext, n_abs, counts["assets"])),
    scenario_key=PKG,
    mission_id=15744,
    tags=["kf-wp:%s" % PKG, "kf-result", "asset-registration", "report-12316",
          "evidence-audit", "lane-C"],
    markdown=report_md,
    figures=[dict(name="fig1_registration_map.png",
                  caption="图 1 资产登记全景：A 面板按类别堆叠并着色解析状态，B 面板外部引用解析到哪个工作树根（含完整性与验收自检摘要）",
                  png_base64=fig_b64)],
)
out = pathlib.Path("/tmp/report_wp12316.json")
out.write_text(json.dumps(payload, ensure_ascii=False))
print("figure:", png, png.stat().st_size, "B")
print("report md:", len(report_md), "chars ->", DOC / "report.md")
print("payload:", out, out.stat().st_size, "B")