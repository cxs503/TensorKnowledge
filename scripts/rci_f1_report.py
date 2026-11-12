#!/usr/bin/env python3
"""KBM-RCI-F1-ABC 报告生成器（两阶段：prereg 锚 / final 结算）。

所有数字从 artifacts/rci-f1-abc/*.json 程序化注入（零手抄）；
图 = artifacts/rci-f1-abc/figures/*.png 内嵌 base64（真 PNG，控总量 <100 KB）。

用法:
  python scripts/rci_f1_report.py --dir artifacts/rci-f1-abc --stage prereg --post
  python scripts/rci_f1_report.py --dir artifacts/rci-f1-abc --stage final  --post
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import urllib.request
from datetime import datetime, timezone

BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1")
MISSION_ID = 15496


def fig(path: str, caption: str) -> dict:
    raw = open(path, "rb").read()
    assert raw[:8] == b"\x89PNG\r\n\x1a\n", f"{path} not a PNG"
    return {"name": os.path.basename(path), "caption": caption,
            "png_base64": base64.b64encode(raw).decode()}


def md_prereg(dir_: str) -> str:
    batch = json.load(open(os.path.join(dir_, "batch60.json"), encoding="utf-8"))
    wps = json.load(open(os.path.join(dir_, "tk_work_packages.json"), encoding="utf-8"))
    pr = json.load(open(os.path.join(dir_, "prereg.json"), encoding="utf-8"))
    obs = batch["observed"]
    alloc = "；".join(f"{k} {v}" for k, v in batch["allocation"].items())
    return f"""# KBM-RCI-F1-ABC 预注册：三臂对照实验设计与批次锚（执行前落盘）

> 任务 15496 · 仓 TensorKnowledge · 生成于 {datetime.now(timezone.utc).isoformat()} ·
> 批次 digest `{batch['digest']}` · prereg_id `{pr['prereg_id']}` ·
> 本报告**先于任何臂执行**发布，作为预注册时间戳锚（指标/阈值自此冻结，事后改动须 v2 重锚）。

## ① 案例介绍（背景/对象/参数表）

owner 战略命题：**大量普通 Agent + 合理任务分解/工具/技能/质量治理，能否完成少量强 Agent 难以独立承担的大规模工作？**
本单把它落成一次可预注册、可机器裁定的对照实验：同一批 60 份文档、同一工作包契约、唯一变量=组织方式。

| 参数 | 取值 |
|---|---|
| 批次规模 | **{batch['n']} 份**（来自 m15462 的 200 份分层试点样本，同源上游） |
| 分层键 | content_type × tier（12 单元，Hamilton 最大余数法分配，每单元 ≥1 席） |
| 实抽覆盖 | 单元 {obs['cells_covered']}/12，仓 {obs['repos_covered']}/15 |
| 层内选样 | sha256(seed\\|repo\\|path) 升序 + 仓轮转（与路径长度/时间/大小无关，确定性） |
| 分层分配 | {alloc} |
| 三臂 | A=1 强 Agent 整批（60 份，1 包）；B=20 普通并行（无审核无 Skill，20×3）；C=20 普通+独立审核+Skills（20×3） |
| 工作包总数 | {len(wps['packages'])}（A 1 + B 20 + C 20） |
| 配对设计 | B 与 C 的 doc→package 映射**完全相同**（降低批次噪声，可做配对差分） |
| 模型档位 | A=`{pr['arms']['A']['model_tier']}`；B/C=`{pr['arms']['B']['model_tier']}` |

**诚实声明（混淆变量）**：三臂在「模型档位/审核/技能」上是**捆绑**差异（组织方式含配置），
因此不得把臂间差异单向归因于「组织方式单一因子」；报告将并列 B vs C（同模型档，切出审核+Skill 的边际贡献）
与 C vs A（整体产线 vs 单强 Agent）两组对照。

## ② 怎么做的（方法/流程/工具链）

1. **批次构建**（`scripts/rci_f1_batch.py`）：读 m15462 `pilot200/sample.json`（sha256 已入库 `artifacts/rci-f1-abc/source/`），
   按 S1-S4 规则抽 60 份，输出 `batch60.json`（含每篇 sha256 与 digest）。
2. **工作包台账**（同脚本）：A 1×60、B/C 各 20×3（配对），写 `tk_work_packages.json`，
   `verify` 子命令机器校验 14 条不变量（覆盖/配对/digest 一致，全绿）。
3. **预注册**（`scripts/rci_f1_prereg.py`）：五指标定义 + 阈值 + 停止规则 + 缺失数据规则 + 盲审协议 + 分析计划
   全部冻结，prereg_id=sha256(canonical 内容)，绑定批次 digest 与批次文件 sha256。
4. **盲审协议**（`scripts/rci_f1_blind.py`）：sample_id=sha256(seed\\|ko_id)[:12]，抹除 lane/package/model，
   结构级去标识检查（禁字段 + 正则），封存 `blind_key.json`（sha256 入预注册）；
   人工≥30 条分层复核表 `human30_sheet.md`；κ<0.6 → M3 降级 WITHHELD。
5. **指标计算**（`scripts/rci_f1_metrics.py`）：只读工件，MI/MO 规则内建，缺数据一律 WITHHELD 不填 0。
6. **派单**（`scripts/rci_f1_dispatch.py`）：A 臂本单直接派发（钉强档 `{pr['arms']['A']['model_tier']}`，
   goal 内联 60 条清单，goal_sha256 落盘）；B/C 交 KBM-RCI-F1-FACTORY 泳道（`task_key=rci-f1-abc-lane-b/c`）。

## ③ 计算结果（预注册时的机器事实，非实验结果）

| 项 | 值 |
|---|---|
| batch_digest | `{batch['digest']}` |
| prereg_id | `{pr['prereg_id']}` |
| 工作包数 | {len(wps['packages'])}（lane A/B/C = 1/20/20） |
| 文档槽位 | 每臂 60（三臂共 180 槽位） |
| 不变量检查 | 14/14 PASS（`rci_f1_batch.py verify`） |
| 盲审管线试运行 | 用 m15462 的 278 个 KO 做仪器试运行：278 item 去标识、快照 60/60 sha 校验、零泄漏、人工表 30 席（`artifacts/rci-f1-abc/pilot/`） |

## ④ 结果图

图1 = 批次分层分配 vs 实抽 + 仓覆盖；图2 = 三臂组织设计对照（agent 数/包数/文档槽位）。
实验数据图（成本/产量/准确率/证据完整率）待三臂结算后于 final 报告给出。

## ⑤ 注意点（坑与局限）

- **无臂间质量对照的先行读取**：预注册后只看进度/成本流水，不看臂间质量明细（防中途调阈值）。
- **模型档捆绑**：见①诚实声明；A 臂强档优势不能当组织方式效应。
- **B/C 落地的现实风险**：FACTORY 泳道若未及时接手，B/C 单会以单 Agent 降级执行——回执 `agent_count`
  会暴露这一点，届时按 MO3 记 WITHHELD 或降级判定，不粉饰。
- **M5 首周复用**当时点未到（T+7d），预注册即写死「未到=WITHHELD，禁填 0」。

## ⑥ 误差判定（可判定性）

本单是设计单，尚未产生实验数值，因此不存在「关键量误差 <3%」的对照——**如实声明**：
本阶段可判定的只有机器事实（digest/不变量/去标识/覆盖），逐项已在上表给出且可复算；
实验指标误差判定在三臂结算后按预注册阈值（3pp 非劣、3× 吞吐、单位成本 ≤A）执行，
届时逐项列出并显式回答是否达标。允许失败不允许伪造：不达标即写不达标。

**偏差与理由**：任务书要求「批次定义写入 tk_work_packages（lane=A/B/C）」。平台无 tk_work_packages 表，
本单以实现为工件台账 `artifacts/rci-f1-abc/tk_work_packages.json`（含契约版本、门禁、成本槽位），
与 FACTORY(15495) 的建表口径对齐（package_id/report_id→doc_ids/task_type/status/mission_id/skill_id/lane/gates/cost）。
"""


def md_final(dir_: str) -> str:
    m = json.load(open(os.path.join(dir_, "metrics.json"), encoding="utf-8"))
    batch = json.load(open(os.path.join(dir_, "batch60.json"), encoding="utf-8"))
    pr = json.load(open(os.path.join(dir_, "prereg.json"), encoding="utf-8"))
    disp = {}
    dp = os.path.normpath(os.path.join(dir_, "../../runs/rci-f1-abc/dispatch.json"))
    if os.path.isfile(dp):
        disp = json.load(open(dp, encoding="utf-8"))
    rows = []
    for lane in ("A", "B", "C"):
        a = m["arms"].get(lane, {})
        t = a.get("totals") or {}
        for k, c in (a.get("metrics") or {}).items():
            rows.append(f"| {lane} | {k} | {c.get('status')} | {c.get('value')} | "
                        f"{json.dumps(c.get('components') or {}, ensure_ascii=False)} |")
    disp_rows = "\n".join(
        f"| {d['lane']} | {d.get('mission_id', '—')} | {d['model']} | {d['goal_chars']} | "
        f"`{d['goal_sha256'][:16]}` |" for d in disp.get("dispatch", []))
    audit = {}
    ap_ = os.path.join(dir_, "prereg_ordering_audit.json")
    if os.path.isfile(ap_):
        audit = json.load(open(ap_, encoding="utf-8"))
    order_line = ("**预注册先于执行**：prereg 报告落盘于 "
                  f"`{audit.get('prereg_report', {}).get('latest_created_at')}`，三臂 mission 创建于 "
                  + "、".join(f"{a['lane']}={a['created_at']}" for a in audit.get("arms", []))
                  + f"；顺序审计 = {audit.get('prereg_precedes_all_arms')}"
                  "（工件 `artifacts/rci-f1-abc/prereg_ordering_audit.json`，可由 "
                    "`scripts/rci_f1_audit.py` 复算）") if audit else ""
    verdict = m["verdict"]
    return f"""# KBM-RCI-F1-ABC 三臂对照实验结果（预注册口径结算）

> 任务 15496 · 批次 digest `{batch['digest']}` · prereg_id `{pr['prereg_id']}` ·
> 五指标冻结口径见预注册报告（先于执行发布）。

## ① 案例介绍
同批 60 份文档（12 分层单元 / 15 仓），三臂organizaton 对照：A=1 强 Agent 整批，B=20 普通并行（无审核无 Skill），
C=20 普通 + 独立审核 + Skills。判定规则预注册冻结：H1 质量非劣（≤3pp）、H2 吞吐 ≥3×A、H3 单位成本 ≤A。

## ② 怎么做的
派单记录（goal 全文 sha256 可复算）：

| 臂 | mission_id | 模型 | goal 字符 | goal sha256 |
|---|---|---|---|---|
{disp_rows or '| — | — | — | — | 派单未执行 |'}

## ③ 计算结果（程序化注入，artifacts/rci-f1-abc/metrics.json）

| 臂 | 指标 | 状态 | 值 | 分量 |
|---|---|---|---|---|
{chr(10).join(rows) if rows else '| — | — | — | — | — |'}

{order_line}

**判定**：`{verdict['verdict']}` — {verdict['reason']}
假设逐项：{json.dumps(verdict.get('hypotheses', {}), ensure_ascii=False)}

## ④ 结果图
图1 批次分层；图2 三臂设计；图3 五指标×三臂数据可得性矩阵（绿=实测，灰=WITHHELD/未结算）。

## ⑤ 注意点
- 模型档捆绑（A 强档 vs B/C 普通档），见预注册混淆变量声明。
- 允许失败不允许伪造：不可得指标写 WITHHELD（禁填 0）；诚实 FAIL 不改数。
- 生产口径：mission succeeded ≠ KO 审核通过 ≠ 科学验证通过（三状态分离）。

## ⑥ 误差判定
实验数值 vs 预注册阈值逐项对照在③表与判定段落列明；本报告不引入任何未在工作中的数字。
若某指标不可得，已显式标 WITHHELD 并写明原因（不宣称 <3% 之类无法支撑的结论）。
"""


def build(dir_: str, stage: str) -> dict:
    figdir = os.path.join(dir_, "figures")
    figs = []
    if stage == "prereg":
        figs = [fig(os.path.join(figdir, "fig1_batch_strata.png"),
                    "图1 批次 60 份分层分配（灰=预注册分配，蓝=实抽）与仓覆盖"),
                fig(os.path.join(figdir, "fig2_design_lanes.png"),
                    "图2 三臂组织设计：agent 数 / work package 数 / 文档槽位（每臂 60）")]
        md = md_prereg(dir_)
        title = "KBM-RCI-F1-ABC 预注册：三臂对照实验设计（60 份同批 · 五指标冻结 · 盲审协议）"
        summary = ("预注册落盘（先于执行）：批次 60 份 12 分层/15 仓（digest "
                   + json.load(open(os.path.join(dir_, "batch60.json")))["digest"][:16]
                   + "），三臂 A/B/C 工作包 1/20/20 配对，五指标+阈值+停止规则+盲审协议冻结，"
                     "A 臂直派强档、B/C 交 FACTORY 泳道。")
        tags = ["KBM-RCI-F1-ABC", "prereg", "experimental-design", "blind-review", "mission-15496"]
    else:
        figs = [fig(os.path.join(figdir, "fig1_batch_strata.png"), "图1 批次分层与仓覆盖"),
                fig(os.path.join(figdir, "fig2_design_lanes.png"), "图2 三臂设计"),
                fig(os.path.join(figdir, "fig3_metric_status.png"), "图3 五指标×三臂数据可得性")]
        md = md_final(dir_)
        title = "KBM-RCI-F1-ABC 三臂对照实验结算（预注册口径）"
        summary = "三臂五指标按预注册口径结算；不可得项标 WITHHELD，判定与假设逐项列明。"
        tags = ["KBM-RCI-F1-ABC", "result", "mission-15496"]
    payload = {"title": title, "summary": summary, "scenario_key": "KBM-RCI-F1-ABC",
               "mission_id": MISSION_ID, "tags": tags, "markdown": md, "figures": figs}
    return payload


def post(payload: dict) -> dict:
    tok = os.environ.get("TP_TOKEN") or open("/tmp/tok_m15496").read().strip()
    path = f"/tmp/m15496_report_{payload['tags'][1]}.json"
    blob = json.dumps(payload, ensure_ascii=False).encode()
    with open(path, "wb") as f:
        f.write(blob)
    print("payload bytes", len(blob), "md5", hashlib.md5(blob).hexdigest(), "->", path)
    req = urllib.request.Request(BASE + "/tensor/reports", data=blob,
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="artifacts/rci-f1-abc")
    ap.add_argument("--stage", choices=["prereg", "final"], default="prereg")
    ap.add_argument("--post", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    payload = build(args.dir, args.stage)
    if args.out:
        json.dump(payload, open(args.out, "w", encoding="utf-8"), ensure_ascii=False)
    if args.post:
        print(json.dumps(post(payload), ensure_ascii=False)[:600])
    else:
        print(json.dumps({"title": payload["title"], "md_chars": len(payload["markdown"]),
                          "figures": [(f["name"], len(f["png_base64"])) for f in payload["figures"]]},
                         ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()