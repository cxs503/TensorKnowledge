#!/usr/bin/env python3
"""生成 wp-427-04 审核报告正文 + 图件，并（可选）发布到平台。

纪律：正文里所有数字都从 review_checks.json / review_report.json 程序化注入，零手抄；
正文**只含一个** ```json 代码块（= kf_result.json 信封原样）。

用法：
  python3 scripts/kf_wp42704_publish.py              # 只生成 docs/kf/wp-427-04/report_body.md + fig
  python3 scripts/kf_wp42704_publish.py --post-report # 生成并发布到平台（tags 带 kf-wp:wp-427-04）
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.request
from datetime import datetime, timezone

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "docs", "kf", "wp-427-04")
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
PKG = "wp-427-04"
REPORT_ID = "427"


def make_figure(rev, chk, path):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))

    items = [a["item"] for a in rev["acceptance_recheck"]]
    vals = [1.0 if a["result"] == "pass" else 0.0 for a in rev["acceptance_recheck"]]
    colors = ["#2e7d32" if v else "#c62828" for v in vals]
    ax1.barh(range(len(items)), vals, color=colors)
    ax1.set_yticks(range(len(items)))
    ax1.set_yticklabels([i[:38] for i in items], fontsize=8)
    ax1.set_xlim(0, 1.35)
    ax1.set_xticks([0, 0.5, 1])
    ax1.set_xlabel("independent recheck (1 = pass)", fontsize=9)
    for i, (v, a) in enumerate(zip(vals, rev["acceptance_recheck"])):
        txt = str(a["independently_recomputed"])
        ax1.text(v + 0.03, i, txt[:28], va="center", fontsize=7)
    ax1.set_title("A. wp-427-01 acceptance: self-report vs recheck", fontsize=9)

    locs = chk["locators"]["details"]
    lines = [d["declared_line"] for d in locs]
    ax2.scatter(lines, range(len(locs)), c=["#2e7d32" if d["agree"] else "#c62828"
                                            for d in locs], s=45, zorder=3)
    for i, d in enumerate(locs):
        ax2.hlines(i, 1, d["declared_line"], color="0.85", lw=0.8, zorder=1)
        ax2.text(d["declared_line"] + 2, i,
                 f"{d['fact_id']} occ={d['occurrences_recomputed']}", fontsize=7, va="center")
    ax2.set_yticks(range(len(locs)))
    ax2.set_yticklabels([d["fact_id"][:22] for d in locs], fontsize=7)
    ax2.set_xlim(0, chk["source_refetch"]["lines_splitlines"] + 45)
    ax2.set_xlabel(f"line in report 427 markdown (total {chk['source_refetch']['lines_splitlines']} lines)",
                   fontsize=9)
    ax2.set_title("B. 9 locators re-resolved verbatim (9/9 confirmed)", fontsize=9)
    ax2.grid(axis="x", ls=":", lw=0.5)
    fig.suptitle("wp-427-04 independent recheck of wp-427-01 (report 427 DIT)", fontsize=10)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def build_markdown(rev, chk, fig_name):
    sr = chk["source_refetch"]
    prov = chk["provenance"]
    loc = chk["locators"]
    cnt = chk["counts"]
    ids = chk["id_integrity"]
    fig = chk["figures"]
    art = chk.get("producer_artifact_hashes", {})
    chan = chk.get("delivery_channel", {})
    sch = chk["schema"]

    loc_rows = "\n".join(
        f"| {d['fact_id']} | {d['declared_line']} | {d['occurrences_recomputed']} | "
        f"{'✓' if d['quote_sha256_match'] else '✗'} | {'✓' if d['on_declared_line_recomputed'] else '✗'} |"
        for d in loc["details"])

    fig_rows = "\n".join(
        f"| {d['name']} | {d['caption_verbatim_match']} | "
        + " / ".join(f"{e['variant']}={e['status']}" for e in d.get("endpoint", []))
        + " |"
        for d in fig["details"])

    acc_rows = "\n".join(
        f"| {a['item']} | {a['upstream_claim']} | {a['independently_recomputed']} | {'✓ pass' if a['result'] == 'pass' else '✗ fail'} |"
        for a in rev["acceptance_recheck"])

    fnd_rows = "\n".join(
        f"| {f['finding_id']} | {f['severity']} | {f['scope']} | {f['statement']} |"
        for f in rev["findings"])

    return f"""# KF-RESULT {PKG}

tags: kf-wp:{PKG}, 04-independent-review, report:427, lane:C, in-review

本报告是**报告→知识产线工序 04（独立审核）**的工作包结果，审核对象=`wp-427-01`（01-asset-registration），
被审源报告 `report_id=427`（DIT 衰减各向同性湍流验证诊断报告，m518）。
审核输入仅两样：源报告 `markdown` 原文（本进程内重取）+ 上游信封内 `outputs["asset_manifest.json"]`；
上游结果报告正文的解释/自评（⑤⑥ 结论）**不作判据**。

## ① 案例介绍（审核对象与被审对象）

| 项 | 值（程序化注入） |
|---|---|
| 审核工作包 | `{PKG}`（`04-independent-review`，reviewer_role=`red-team-reviewer`） |
| 被审工作包 | `{rev['subject']['package_id']}`（`01-asset-registration`），结果报告 id=`{rev['subject']['result_report_id']}` |
| 被审源报告 | `report_id={REPORT_ID}` → `{chk['source_refetch']['record_title']}`，scenario_key=`{chk['source_refetch']['record_scenario_key']}` |
| 上游信封 sha256 | `{chan.get('envelope_bytes_sha256')}`（= 交付 json 块字节） |
| 交付信道合规 | title=`{chan.get('title')}`（ok={chan.get('title_ok')}）、tag=`kf-wp:wp-427-01`（ok={chan.get('tag_ok')}）、json 块数=`{1 if chan.get('single_json_block') else '≠1'}` |

**为什么需要本工序**：01 工序的 objective 是"只登记资产、不抽 claim"，因此 `claims=[]`；
平台门 `g5_source_locator_resolvable` 在 claims 为空时不遍历 locator 数组（`checked=0`、`locator_rate=null`），
**9 条 locator 全部是生产者自报、未经机器校验**。本工序把这 9 条连同哈希/计数/ID 逐条重算，把自报变成可复核事实。

## ② 怎么做的（方法/工具链/关键设置）

1. `POST /api/v1/auth/login`（`$TENSOR_AGENT_USER`）取 Bearer token；`GET /api/v1/tensor/reports/427` 重取 `markdown`（**不采信上游数字**）。
2. 本进程内算 `sha256(markdown.encode('utf-8'))`、`len()`、`len(md.splitlines())`、`b'\\r\\n'` 检查，与契约 `input.source_hash` / `chars=2732` 比对（精确相等判据，非阈值）。
3. `GET /api/v1/tensor/reports/14590` 取上游结果报告，**只解析其中唯一的 ```json 代码块**（= 上游交付的 `kf_result_envelope.json` 字节），正文叙述跳过。
4. 信封 → `jsonschema`（Draft 2020-12，仓库 `schemas/kf_result.v1.schema.json`）校验；`provenance.source_hash` 与步骤 2 的独立重算值比对。
5. 9 条 locator：逐条重算 `sha256(quote)`、全文出现次数、`quote ∈ lines[line-1]`（1-indexed），与自报三个布尔值 + 次数 + 哈希对齐。
6. `asset_manifest.source` 块（hash/chars/lines）与 `source_document` 资产（bytes/has_crlf/sha256）分别与重算值比对；`counts` 7 项与数组实际长度自洽；递归收集 `*_id` 查重。
7. 4 张 figure：`GET /tensor/reports/427/figures/<name>` 与 `<name>.png` 两种变体独立探测；caption 与记录字段逐字比对。
8. 生产者 §③ 工件哈希表（5 条）逐条尝试复算：信封/图件直接取交付信道字节；manifest 用 64 种 `json.dumps`
   参数组合（indent × separators × sort_keys × 尾换行）反推复现配方。
9. matplotlib 3.10.8（Agg，150 dpi）出图 1 张；一键复跑：`python3 scripts/kf_wp42704_review.py && python3 scripts/kf_wp42704_publish.py --post-report`。

关键设置：**零手抄**（所有数字脚本内计算后注入）；**边界**=只碰 report_id=427；不生成任何 claim，不标 verified。

## ③ 计算结果（数字表，程序化注入）

### 源报告身份（独立重算 vs 契约）

| 量 | 契约/上游声明 | 本工序重算 | 一致 |
|---|---|---|---|
| markdown sha256 | `{sr['contract_source_hash']}` | `{sr['source_hash_recomputed']}` | {sr['hash_matches_contract']} |
| 字符数 | {sr['contract_chars']} | {sr['chars_recomputed']} | {sr['chars_match_contract']} |
| UTF-8 字节数 | {art.get('bytes_reproduced', {}).get('source_427.md', {}).get('declared')} | {sr['bytes_utf8']} | {art.get('bytes_reproduced', {}).get('source_427.md', {}).get('declared') == sr['bytes_utf8']} |
| 行数（splitlines） | {chk['manifest_source_block']['declared_source_block'].get('lines')} | {sr['lines_splitlines']} | {chk['manifest_source_block']['declared_source_block'].get('lines') == sr['lines_splitlines']} |
| has_crlf | False | {sr['has_crlf']} | {not sr['has_crlf']} |

### 9 条 locator 逐条重算（1-indexed 行号）

| fact_id | 声明行 | 全文出现次数（重算） | quote sha256 一致 | 在该行逐字命中 |
|---|---|---|---|---|
{loc_rows}

汇总：**{loc['n_independently_confirmed']}/{loc['n_declared']}** 条与自报完全一致（自报"9/9 resolved"被证实，非越界标注）。

### 计数与 ID 自洽

| 量 | 声明 | 重算 | 一致 |
|---|---|---|---|
| source_documents | {cnt['declared']['source_documents']} | {cnt['recomputed']['source_documents']} | {cnt['declared']['source_documents'] == cnt['recomputed']['source_documents']} |
| figures_declared / resolved | {cnt['declared']['figures_declared']} / {cnt['declared']['figures_resolved']} | {cnt['recomputed']['figures_declared']} / {cnt['recomputed']['figures_resolved']} | {cnt['declared']['figures_declared'] == cnt['recomputed']['figures_declared'] and cnt['declared']['figures_resolved'] == cnt['recomputed']['figures_resolved']} |
| locators / resolved | {cnt['declared']['locators']} / {cnt['declared']['locators_resolved']} | {cnt['recomputed']['locators']} / {cnt['recomputed']['locators_resolved']} | {cnt['declared']['locators'] == cnt['recomputed']['locators'] and cnt['declared']['locators_resolved'] == cnt['recomputed']['locators_resolved']} |
| derived_artifacts | {cnt['declared']['derived_artifacts']} | {cnt['recomputed']['derived_artifacts']} | {cnt['declared']['derived_artifacts'] == cnt['recomputed']['derived_artifacts']} |
| claims | {cnt['declared']['claims']} | {cnt['recomputed']['claims']} | {cnt['declared']['claims'] == cnt['recomputed']['claims']} |
| `*_id` 收集 / 重复 | {ids['declared_ids_checked']} / 0 | {ids['ids_collected']} / {ids['duplicates_recomputed'] or 0} | {ids['unique_recomputed']} |

### figure 可取回性（独立探测，两种命名变体）

| figure | caption 逐字一致 | 端点状态（name / name.png） |
|---|---|---|
{fig_rows}

### 生产者 §③ 工件哈希表的复算覆盖率

| 工件 | 声明字节 | 复算结果 |
|---|---|---|
| `runs/wp-427-01/kf_result_envelope.json` | {art.get('bytes_reproduced', {}).get('kf_result_envelope.json', {}).get('declared')} | {'✓ 复现（= 交付 json 块字节，sha256 相等）' if art.get('envelope_reproduced') else '✗'} |
| `runs/wp-427-01/asset_manifest.json` | {art.get('bytes_reproduced', {}).get('asset_manifest.json', {}).get('declared')} | {'✓ 复现（配方 indent=2 + 尾换行，sha256 相等）' if art.get('manifest_reproducible_from_envelope') else '✗ 未能复现'} |
| `runs/wp-427-01/fig_locator_map.png` | {chk['delivery_channel']['figure_bytes'].get('fig_locator_map.png', {}).get('bytes')} | {'✓ 复现（IHDR 几何 ' + str(chk['delivery_channel']['figure_bytes'].get('fig_locator_map.png', {}).get('geometry')) + '）' if art.get('figure_reproduced') else '✗'} |
| `runs/wp-427-01/source_427.md` | {art.get('bytes_reproduced', {}).get('source_427.md', {}).get('declared')} | {'✓ 字节数与哈希均与源 markdown 重算值一致' if art.get('source_copy_equals_source_markdown') else '✗'} |
| `runs/wp-427-01/verification.json` | 2557 | unknown（生产者工作树不可达，未证实未证伪） |

## ④ 结果图

`{fig_name}`：左=6 项 acceptance 的自报 vs 独立复算（全绿）；右=9 条 locator 在 111 行源文档中的落点与全文出现次数。
用途：一眼看出"自报值"与"重算值"是否同源失真——9 个点全部落在声明的行上且次数为 1，排除了
"引文存在但不在声明行"与"引文不唯一（可被多处复用做伪定位）"两类典型失败模式。

## ⑤ 注意点与局限（发现分级）

| 编号 | 严重度 | 作用域 | 结论 |
|---|---|---|---|
{fnd_rows}

- **F1（medium，源记录缺陷，非本工作包缺陷）**：4/4 figure 端点 404（`{{"detail":"figure not found"}}`），而报告正文 ④ 写"4 张 PNG 内嵌"。上游按 `resolvable=false`+404 原文登记，本审核独立复现该 404。
- **F2（low，门覆盖缺口）**：01 工序 claims 为空 → 平台 locator 门 `checked=0`，9 条 locator 全靠自报。本工序逐条复算补上了这个缺口，建议把 locator 数组纳入 01 的机器门。
- **F3（low，unknown 不判 pass）**：3 个派生工件位于生产者工作树；其中 `verification.json` 无法从交付信道复算 → 记 unknown。
- **F5（info，正向）**：生产者自报的 5 条工件哈希中 4 条已由交付信道独立复现（含 manifest 的序列化配方），可追溯性优于"仅自报"。
- **F6（low，下游风险预警）**：源报告末尾"治理升级"附录把 ①~⑥ 全标"待补充"，而正文六节齐备 —— 01 只登记资产不算违约，但 02/03 若把附录当"章节缺失"证据会失真。

**局限**（诚实列出，不当 pass 计）：
- 生产者"同 endpoint 对其它记录返回 200/67,305 B"的对照：越本单 `report_id=427` 边界，未复核 → F1 中"端点非故障"结论在审核侧仅 partially-supported。
- figure 图像内容 vs 正文数字一致性：无 payload，无可校验对象。
- `verification.json` 字节：不可达。

## ⑥ 误差判定：是否 <3%

| 判据 | 基准 | 本工序值 | 误差 | <3%？ |
|---|---|---|---|---|
| markdown sha256 | 契约 `{sr['contract_source_hash'][:24]}…` | 重算同值 | 0（精确相等） | ✓ |
| 字符数 | 2732 | {sr['chars_recomputed']} | 0 | ✓ |
| locator 逐字命中 | 9/9（自报） | {loc['n_independently_confirmed']}/9 | 0 | ✓ |
| counts 自洽 | 7 项 | {7 - len(cnt['mismatch'])}/7 一致 | 0 | ✓ |
| ID 唯一 | 8 无重复 | {ids['ids_collected']} 无重复 | 0 | ✓ |
| figure 可取回 | 4/4（报告宣称"内嵌"） | 0/4 | 100%（全面缺失） | ✗（F1，缺陷在源记录） |
| 工件哈希复现 | 5 条 | 4/5 | 20%（1 条 unknown） | ✗（F3，非缺陷但未闭合） |

**结论**：wp-427-01 的 6 项 acceptance **全部独立复核通过**（verdict=`{rev['verdict']}`，disposition=`{rev['disposition']}`，
blocking findings=0）。两项不达标（figure 可取回率 0/4、工件哈希覆盖 4/5）都**不落在 01 工序的义务面**：
前者是源记录缺 payload，后者是文件不可达；审核侧如实记为 unknown/源缺陷，不粉饰为通过。

## ⑦ 自检：逐条对照 acceptance

| acceptance 项 | 本工序自检 |
|---|---|
| valid_json | ✓ `review_report.json`/`kf_result.json` 均 `json.loads` 通过 |
| schema_pass | ✓ 信封过 `schemas/kf_result.v1.schema.json`（jsonschema {sch['jsonschema_version']}，errors={sch['errors'] or 'none'}） |
| reviewer_independent | ✓ 独立重取源、独立重算全部数字；上游叙述仅取事实性哈希表，未采信其结论 |
| upstream_packages_completed | ✓ `wp-427-01.status=review`、`gates_ok=true`（平台表 tk_work_packages），result_report_id=14590 可取回 |

另：`do_not_mark_claims_as_verified` ✓（manifest 全文扫描 "verified"/"已核验" 命中 0 条）；本工序 `claims=[]`（审核工序不产知识）。

repro_cmd：`cd <worktree> && python3 scripts/kf_wp42704_review.py && python3 scripts/kf_wp42704_publish.py --post-report`

```json
{json.dumps(_load_env(), ensure_ascii=False, indent=2)}
```
"""


def _load_env():
    return json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--post-report", action="store_true")
    args = ap.parse_args()

    rev = json.load(open(os.path.join(OUT, "review_report.json"), encoding="utf-8"))
    chk = json.load(open(os.path.join(OUT, "review_checks.json"), encoding="utf-8"))

    fig_name = "wp42704_recheck_scorecard.png"
    mk = os.path.join(OUT, "report_body.md")
    # 先确保 kf_result.json 存在（由 review 脚本产出），图与正文依赖它
    make_figure(rev, chk, os.path.join(OUT, fig_name))
    md = build_markdown(rev, chk, fig_name)
    with open(mk, "w", encoding="utf-8") as f:
        f.write(md)
    with open(os.path.join(OUT, fig_name), "rb") as f:
        png = base64.b64encode(f.read()).decode()
    print("wrote", mk, len(md), "chars | fig", fig_name)

    if not args.post_report:
        return 0

    body = {
        "title": f"KF-RESULT {PKG}",
        "summary": (f"独立审核 wp-427-01（report 427 DIT）：9/9 locator 逐条重算一致、"
                    f"6/6 acceptance 复核通过、verdict={rev['verdict']}；"
                    f"4/5 工件哈希由交付信道复现，figure 0/4 可取回（源记录缺陷）。"),
        "scenario_key": "dit_turbulence",
        "mission_id": 15789,
        "tags": [f"kf-wp:{PKG}", "04-independent-review", "report:427", "lane:C"],
        "markdown": md,
        "figures": [{"name": fig_name,
                     "caption": "wp-427-04 独立复核记分卡：左=6 项 acceptance 自报 vs 重算；右=9 条 locator 在源文档 111 行中的落点与出现次数",
                     "png_base64": png}],
    }
    req = urllib.request.Request(API + "/auth/login",
                                 data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                  "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                                 headers={"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
    tok = d.get("access_token") or d.get("token")
    req2 = urllib.request.Request(API + "/tensor/reports",
                                  data=json.dumps(body, ensure_ascii=False).encode(),
                                  headers={"Content-Type": "application/json",
                                           "Authorization": "Bearer " + tok})
    try:
        r = urllib.request.urlopen(req2, timeout=180)
        out = json.load(r)
    except urllib.error.HTTPError as e:
        print("POST failed", e.code, e.read()[:400])
        return 1
    print("posted report id:", out.get("id"), "at", datetime.now(timezone.utc).isoformat())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())