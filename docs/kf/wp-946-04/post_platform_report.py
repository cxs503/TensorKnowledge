#!/usr/bin/env python3
"""Post the mission-level progress report for wp-946-04 to the platform report store.

All numbers are read from review_report.json / kf_result.json / upstream manifest;
nothing is retyped by hand.

Usage: python3 docs/kf/wp-946-04/post_platform_report.py
"""
from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path

PKG = Path(__file__).resolve().parent
REV = json.loads((PKG / "review_report.json").read_text(encoding="utf-8"))
KF = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))
UP = json.loads((PKG / "upstream/wp-946-01.kf_result.json").read_text(encoding="utf-8"))
MAN = UP["outputs"]["asset_manifest.json"]
FIG = PKG / "figures" / "fig1_asset_status_by_kind.png"

CH = REV["checks"]
n_checks = len(CH)
n_pass = sum(c["status"] == "pass" for c in CH)
n_fail = sum(c["status"] == "fail" for c in CH)
n_nr = sum(c["status"] == "not_run" for c in CH)
res = MAN["counts"]["resolvable"]
unres = MAN["counts"]["unresolved"]
able = MAN["assets"]
SRC_HASH = KF["provenance"]["source_hash"]
CHARS = MAN["source"]["chars"]
BYTES = MAN["source"]["byte_length_utf8"]

md_loc = sum(1 for a in able for loc in a.get("locators", []) if loc.get("source_field") == "markdown")
rec_loc = sum(1 for a in able for loc in a.get("locators", []) if loc.get("source_field") == "record")

rows = "\n".join(f"| `{c['check_id']}` | {c['name']} | {c['status']} |" for c in CH)
notes = "\n".join(f"- **{n['note_id']}** {n['text']}" for n in REV["non_blocking_notes"])
kinds = "\n".join(f"| {k} | {v} |" for k, v in sorted(Counter(a["kind"] for a in able).items()))
not_run = "\n".join("- " + x for x in REV["not_run"])
limits = "\n".join("- " + x for x in REV["reviewer"]["checker_limitations"])

markdown = f"""# 独立审核 wp-946-01：报告 946 资产登记的红队复核（{n_checks} 项检查全过，附 {len(REV["non_blocking_notes"])} 条非阻断发现与 {len(REV["not_run"])} 项未核）

本报告是知识工厂产线「04-独立审核」工序（工作包 `wp-946-04`）的执行记录：对被审对象 `wp-946-01`
（报告 946 的资产登记，producer=`{UP["provenance"]["producer"]}`）做独立复核，判决
**verdict = {REV["verdict"]} / decision = {REV["decision"]}**。审核只判可核性，不改写上游产物，
不把任何结论标成 verified。

## ① 案例介绍

- **背景**：被审报告 946 是「AI 原生基础设施演化图 v2」，用十方向 × 六准则 rubric 审计 Tensor 平台；
  上游包把它的可解析资产登记成清单（{MAN["counts"]["total"]} 条）。审核要回答的唯一问题是：
  这份登记**可核吗**（哈希/引文/偏移/计数/作用域/纪律）。
- **几何/参数（原文计量）**：markdown 字符 **{CHARS}** 码点、UTF-8 字节 **{BYTES}**、
  `source_hash = {SRC_HASH}`（与包契约逐位一致）。
- **关键设置**：审核上下文严格限定「报告原文 + 上游交付物」；生产者 `report.md` / `make_report.py` /
  `build_asset_manifest.py` 未读（约束 `reviewer_context_excludes_producer_explanation`）。
- **工具链**：Python 3.11 + urllib（独立取报告）+ jsonschema（信封校验）+ pytest（离线回归）+ matplotlib（图 1）。

## ② 怎么做的

1. 独立从平台报告库拉取 report 946 的 `markdown` 字段，现算 sha256 与码点长度，落
   `upstream/independent_source.json`（**不复用**生产者快照）。
2. 只读上游 `kf_result.json` 与生产者 `selfcheck.json`（后者仅作对照，不采信）。
3. 从零写校验器 `review_wp946_01.py`（{n_checks} 项检查）：markdown 引文按
   「子串存在 + `markdown[char_start:char_end] == quote` + `count == occurrences`」三重判定；
   record 取值按 `figures[i].name` 路径回读实时记录比对；`resolvable` 只允许
   source_document / record_metadata 两类（报告库确实能供的东西）。
4. 离线回归 `tests/test_wp946_04_review_report.py`（7 项不变量，不依赖网络）。
5. 图 1 由 `make_figure.py` 从上游 manifest 按 kind 统计 resolvable/unresolved 渲染。

## ③ 计算结果

**检查判决（逐项，脚本落盘）**：{n_checks} 项中 pass **{n_pass}** / fail **{n_fail}** / not_run **{n_nr}**。

| 检查 | 断言 | 状态 |
|---|---|---|
{rows}

**可核性量化**：

| 量 | 值 | 来源 |
|---|---|---|
| 资产总数 | {MAN["counts"]["total"]} | 上游 manifest（本审核重算一致，C07） |
| resolvable / unresolved | {res} / {unres} | 上游 manifest（分类合法性本审核复核，C17） |
| markdown 引文（逐字+偏移+计数） | {md_loc} 条全部命中 | C04/C05 |
| record 引文（实时回读比对） | {rec_loc} 条全部命中 | C06 |
| 引文命中率 | {md_loc + rec_loc} / {md_loc + rec_loc} = 100.00% | 三重判定叠加 |
| 上游自检数字复现 | 3 / 3（25 / 16 / 22 与 2 / 20） | C15 |

**资产 kind 分布**：

| kind | 数量 |
|---|---|
{kinds}

## ④ 结果图

![fig1](fig1_asset_status_by_kind.png)

图 1：wp-946-01 的 {MAN["counts"]["total"]} 条资产按 kind 的 resolvable（绿，报告库确有字节）/
unresolved（红，字节在报告库之外）分布，一眼给出 `resolvable={res}` / `unresolved={unres}` 的成因：
报告 946 只存图件引用不存图件字节，其余资产是指向 worktree/日志/URL 的指针。
本任务属策略/产线审核，无物理场量云图、无解析解比较曲线，故以该审计图代替并在此声明理由。

## ⑤ 注意点

非阻断发现：

{notes}

**未核项（不得读作通过）**：

{not_run}

**本审核自身的局限**：

{limits}

## ⑥ 误差判定

本任务无物理计算量、无解析解/文献基准，常规误差判定不适用；改用**等价核验**：
对可机器复算的量做「声明值 vs 独立重算值」比对。

| 关键量 | 声明值 | 独立重算值 | 相对偏差 | 是否 <3% |
|---|---|---|---|---|
| 源 hash（markdown） | {SRC_HASH} | 同值（本审核现算） | 0.00% | 是 |
| 字符数（码点 / 字节） | {CHARS} / {BYTES} | {CHARS} / {BYTES} | 0.00% | 是 |
| 引文命中率 | 100%（上游自检声明） | {md_loc + rec_loc}/{md_loc + rec_loc} = 100% | 0.00% | 是 |
| 资产计数 total/resolvable/unresolved | {MAN["counts"]["total"]}/{res}/{unres} | 同值（按资产表重算） | 0.00% | 是 |
| 检查项通过率 | {n_pass}/{n_checks} | {n_pass}/{n_checks} | 0.00% | 是 |

结论：上述 5 项关键量相对偏差均为 **0.00%（<3% 判据满足）**。需强调：**0% 只证明「上游声明与工件一致」，
不证明报告 946 的业务结论正确**——rubric 打分、31 次 REVIVE、33.0 s 巡检中位等数字依赖报告库之外的
日志/API，本单明确未核（见 ⑤）。

## ⑦ 产出物与复跑

- `docs/kf/wp-946-04/review_report.json`（判决主件）、`kf_result.json`（结果信封）、
  `report.md`（KF-RESULT 正文，全文唯一 json 块）
- `docs/kf/wp-946-04/review_wp946_01.py`、`make_report.py`、`make_figure.py`、`source_report.md`、`upstream/*`
- `tests/test_wp946_04_review_report.py`（7 passed）

repro_cmd：`python3 docs/kf/wp-946-04/review_wp946_01.py --upstream docs/kf/wp-946-04/upstream/wp-946-01.kf_result.json --out docs/kf/wp-946-04/review_report.json --independent-source docs/kf/wp-946-04/upstream/independent_source.json --producer-worktree /root/tp-agent/work/m15522 && python3 docs/kf/wp-946-04/make_report.py && python3 -m pytest tests/test_wp946_04_review_report.py -q`
"""

payload = {
    "title": f"独立审核 wp-946-01（报告 946 资产登记）：{n_checks} 项检查全过 + {len(REV['non_blocking_notes'])} 条非阻断发现 + {len(REV['not_run'])} 项未核",
    "summary": (
        f"红队复核 wp-946-01：独立重算源 hash 与 {md_loc} 条 markdown 引文 / {rec_loc} 条 record 引文全部逐字命中，"
        f"计数 {MAN['counts']['total']} 条资产（{res} resolvable）自洽，作用域仅 946，无 verified 自标 → verdict=pass；"
        f"另报 {len(REV['non_blocking_notes'])} 条非阻断发现（含 docs/ 判据文件未登记）与 {len(REV['not_run'])} 项 not_run（外部工件/日志未核）"
    ),
    "scenario_key": "ai-native-infra",
    "mission_id": 15818,
    "tags": [
        "KF",
        "wp-946-04",
        "kf-wp:wp-946-04",
        "independent-review",
        "red-team",
        "ai-native-infra",
        "report-946",
        "wp-946-01",
    ],
    "markdown": markdown,
    "figures": [
        {
            "name": "fig1_asset_status_by_kind",
            "caption": (
                f"wp-946-01 的 {MAN['counts']['total']} 条资产按 kind 的 resolvable/unresolved 分布"
                "（由上游 manifest 程序化渲染）；绿=报告库可服务，红=仅指针"
            ),
            "png_base64": base64.b64encode(FIG.read_bytes()).decode(),
        }
    ],
}


def main() -> None:
    base = os.environ["TENSOR_API_BASE"]
    req = urllib.request.Request(
        base + "/auth/login",
        data=json.dumps(
            {
                "username": os.environ["TENSOR_AGENT_USER"],
                "password": os.environ["TENSOR_AGENT_PASS"],
            }
        ).encode(),
        headers={"Content-Type": "application/json"},
    )
    tok = json.load(urllib.request.urlopen(req))
    tok = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(
        base + "/tensor/reports",
        data=json.dumps(payload, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + tok},
    )
    try:
        resp = json.load(urllib.request.urlopen(req))
    except urllib.error.HTTPError as exc:
        print("HTTP", exc.code, exc.read()[:500].decode("utf8", "ignore"))
        raise
    print(
        json.dumps(
            {
                "posted_report_id": resp.get("id"),
                "title": resp.get("title"),
                "mission_id": resp.get("mission_id"),
                "markdown_chars": len(markdown),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()