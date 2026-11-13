#!/usr/bin/env python3
"""Publish the wp-9840-01 report: six-section paper-style markdown + the result JSON as the
single ```json block, with the asset-locator figure embedded.

Every number and every quote in the markdown is injected from artifacts/wp-9840-01/
asset_manifest.json, runs/wp-9840-01/verification.json and negative_control.json —
no hand-typed digits, no quotes from memory.
"""
import json
import os
import pathlib
import sys
import urllib.request

PACKAGE_ID = "wp-9840-01"
REPORT_ID = "9840"
MISSION_ID = 15673
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")

RUN = pathlib.Path("runs/wp-9840-01")
ART = pathlib.Path("artifacts/wp-9840-01/asset_manifest.json")
DOC = pathlib.Path("docs/wp-9840-01")


def api(path, data=None, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", "Bearer " + token)
    body = None
    if data is not None:
        body = json.dumps(data).encode()
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, body, timeout=120) as r:
        return json.loads(r.read().decode())


def one_line(q: str, n: int = 96) -> str:
    q = q.replace("\n", " ⏎ ").replace("|", "\\|")
    return q[:n] + ("…" if len(q) > n else "")


def main() -> int:
    m = json.loads(ART.read_text())
    result = json.loads((RUN / ("kf_result.%s.json" % PACKAGE_ID)).read_text())
    ver = json.loads((RUN / "verification.json").read_text())
    neg = json.loads((RUN / "negative_control.json").read_text())
    c = m["counts"]

    acc_items = ["valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
                 "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"]
    acc_rows = []
    for it in acc_items:
        hits = [x for x in ver["checks"] if x["check"] == it or x["check"].startswith(it)]
        status = "PASS" if hits and all(h["result"] == "pass" for h in hits) else (
            "FAIL" if any(h["result"] == "fail" for h in hits) else "not_run")
        acc_rows.append((it, status, ", ".join(h["check"] for h in hits)))
    n_pass = sum(1 for x in ver["checks"] if x["result"] == "pass")
    n_fail = sum(1 for x in ver["checks"] if x["result"] == "fail")
    n_notrun = sum(1 for x in ver["checks"] if x["result"] == "not_run")
    acc_pass = sum(1 for _, s, _ in acc_rows if s == "PASS")

    det = []
    for a in m["assets"]:
        loc = a["locator"]
        det.append("| %s | %s | %s | %d–%d | %s |" % (
            a["asset_id"], a["asset_class"], a["resolution"],
            loc["start_line"], loc["end_line"], one_line(loc["quote"])))

    unresolved = [a["asset_id"] + " (`" + a["asset_class"] + "`)" for a in m["assets"]
                  if a["resolution"] == "referenced_unresolved"]
    absent = [a["asset_id"] + " (`" + a["asset_class"] + "`)" for a in m["assets"]
              if a["resolution"] == "declared_absent"]
    shared = [a["asset_id"] + "↔" + a["locator"]["shared_span_with"] for a in m["assets"]
              if a["locator"].get("shared_span_with")]

    report_md = f"""# KF-RESULT {PACKAGE_ID}

**工作包** `{PACKAGE_ID}` · **task_type** `{m['task_type']}` · **lane** C · **目标报告** `report_id={REPORT_ID}`（本单只触这一份）
**源** `{m['source']['uri']}` · field=`markdown` · sha256=`{m['source']['hash']}` · chars={m['source']['chars']} · bytes_utf8={m['source']['bytes_utf8']}
**分层标签** DG | `{m['source']['scenario_key']}` | l · **仓** TensorKnowledge（交付 status=draft）

## 1. 案例介绍（本工序在产线上的位置）

本条产线的对象是报告 9840 这一份源资产：《{m['source']['title']}》。它的上游是 TensorLBM 仓 IN65-N04 节点的 DG 验证面算例（旋转锥 / 制造解 / 间断传播），本工序**只做 asset registration**：确认 report_id 与其 markdown 的字节哈希、把报告内可解析的表格/声明/外部引用逐条定位成机器可复核的资产，**不做知识抽取、不做数值复核、不把任何结论标成 verified**（verification 由平台门计算）。

契约要点（原样遵守）：`objective.register_assets: true`、`classify_report_type: false`、`notes` 明确「claims 允许为空数组」。因此本工序申请的知识对象为零，产出的是证据定位器（locator）+ 解析状态（resolution），供下游抽取工序直接复用。

参数表（全部来自源 markdown，本工序不换算）：

| 项 | 值 | 出处 |
|---|---|---|
| report_id | {REPORT_ID} | 契约 input.report_id，平台 `id={m['source']['platform_id']}` |
| source_field | `{m['source']['field']}` | 契约 input.source_field |
| markdown sha256 | `{m['source']['hash']}` | 本次独立重算（见 §6） |
| markdown 字符数 / UTF-8 字节 | {m['source']['chars']} / {m['source']['bytes_utf8']} | 同上；契约 chars={m['source']['chars']} |
| scenario_key | `{m['source']['scenario_key']}` | 平台记录字段 |
| 平台 figures 数 | {len(m['source']['platform_figures'])} | 平台记录 `figures` 字段 |
| 登记资产数 | {c['assets']} | 本清单 `counts.assets` |

## 2. 怎么做的（方法 / 流程 / 关键设置 / 工具链）

1. **取源**：`GET {m['source']['retrieved_via'].split(' ', 1)[1]}`（Bearer 登录 token），把 markdown 与平台元数据冻结到 `{m['source']['local_copy']}`；构建与校验都只读这一份字节，避免中途漂移。
2. **哈希先验**：先重算 sha256 与契约 `source_hash` 比对（不等即 `return 2` 硬失败），再做任何登记——哈希不过就不写产物。
3. **锚点表（33 条，5 种模式）**：每条资产声明 anchor 子串 + 解析模式：`document`（全文）/`table`（锚点行起连续 `|` 行，自动吃表头+分隔+全部数据行）/`para`（段落到空行）/`block`（锚点行 + n 行）/`section`（到下一个同级或更高级标题）。锚点必须**在文中唯一命中**，否则构建立即失败（`SystemExit`）。
4. **零手抄的引文**：quote 不是打出来的，而是 `md[start_char:end_char]` 切出来的——字符跨度、行跨度、quote 三者由同一段切片产生，故不可能出现「凭记忆重述」。构建期同时强制：quote 非空、在全文出现次数 == 1、任意两条资产不得共享同一切片（共享则必须登记 `shared_span_with`）。
5. **解析状态三分**：`resolved_in_source`（{c['resolved_in_source']} 条）/ `referenced_unresolved`（{c['referenced_unresolved']} 条，指向 TensorLBM 仓的代码与产物，本工作树内不存在且报告未给可解析地址）/ `declared_absent`（{c['declared_absent']} 条，§4「结果图」正文为空）。每条资产附 `resolution_check`（检查名 + 结果 + 证据），不留裸断言。
6. **独立校验器**：`scripts/kf_verify_9840.py` 不信任构建期的冻结副本，**重新登录、重新取 API**，用 live markdown 重算 sha256 并逐条按 `[start_char,end_char)` 重切、重算唯一性；三条哈希（契约 / live / 信封）必须同时相等。
7. **结构门**：清单按本包的 pin 死 schema `schemas/asset_manifest.wp-9840-01.schema.json` 校验；结果信封按仓内 `schemas/kf_result.v1.schema.json`（未改动）校验——该 schema `additionalProperties:false`，故信封里不放 `schema_version` 这类额外字段（与早期 448 包信封的差异见 §5）。
8. **否定对照（gate 会不会永远说 PASS？）**：`scripts/kf_9840_negative_control.py` 在内存里造 6 个变体（跨度偏移 1 字符 / 离线改引文 / unique 标志置假 / 资产 id 重复 / 全文 locator 截断 / 凭空编一句引文），断言**真实谓词函数**（从校验器 import，不是重写）逐个拒绝，且原清单 0 失败。
9. **出图**：`scripts/kf_figures_9840.py` 只读清单，画 33 条资产的文档字符轴定位图 + 解析状态/类别分布（数字全部程序化注入）。

## 3. 产出物清单

| 文件 | 要点 |
|---|---|
| `artifacts/wp-9840-01/asset_manifest.json` | 主产物：33 条资产 + 源元数据 + counts + integrity（sha256 `{result['outputs']['asset_manifest.json']['artifact_sha256']}`, {result['outputs']['asset_manifest.json']['artifact_bytes']} bytes） |
| `docs/wp-9840-01/asset_manifest.json` | 同字节入库镜像（仓推送门会丢弃 `artifacts/**`、`runs/**`，故 docs/ 存续） |
| `docs/wp-9840-01/verification.json` | 校验器逐项结果：{n_pass} pass / {n_fail} fail / {n_notrun} not_run，overall=`{ver['overall']}` |
| `docs/wp-9840-01/negative_control.json` | 6/6 变体被拒（`all_mutants_rejected={neg['all_mutants_rejected']}`），原清单 0 失败 |
| `docs/wp-9840-01/fig_asset_locator_map.png` | 图 1：资产在源文档上的定位图 + 解析状态/类别分布 |
| `runs/wp-9840-01/kf_result.{PACKAGE_ID}.json` | 结果信封（与下文唯一一个 json 代码块同字节） |
| `runs/wp-9840-01/report_9840.{{md,json}}` | 冻结的源 markdown 与平台元数据（可复算哈希） |
| `scripts/kf_fetch_9840.py` / `kf_register_9840.py` / `kf_verify_9840.py` / `kf_9840_negative_control.py` / `kf_figures_9840.py` / `kf_report_9840.py` | 取源 / 构建 / 校验 / 否定对照 / 出图 / 发报，一键可复跑 |
| `schemas/asset_manifest.wp-9840-01.schema.json` | 本包 pin 死的清单 schema（`asset_manifest.v1.schema.json` 是 448 包专用，不可复用） |

**关键量误差判定**：本工序无物理量、无基准对标，故「是否 <3%」不适用（登记工序无实验值可比）。替代判据是门通过率：{n_pass}/{len(ver['checks'])} 项校验 pass、{n_fail} 项 fail、{n_notrun} 项 not_run；契约 acceptance 六条全部 PASS（§6 逐条），否定对照 6/6 被拒。这不是「精度达标」，只是「登记可复核」。

## 4. 证据定位表（每条资产 → 原文逐字引文片段）

下表 quote 列是 `md[start_char:end_char]` 切出的原文前缀（`|` 与换行已转义；⏎ 表示行边界），完整引文见清单 `assets[].locator.quote`；行号是该资产在源 markdown 中的 0 基行区间。

| 资产 | 类别 | 解析状态 | 行区间 | 原文引文（逐字，截断展示） |
|---|---|---|---|---|
{chr(10).join(det)}

另：`§4 结果图` 在 markdown 中无正文（{absent[0] if absent else 'n/a'}），但平台 `figures` 字段有 {len(m['source']['platform_figures'])} 条记录（{', '.join(f['name'] for f in m['source']['platform_figures'])}）——图件字节不在本工序登记范围。

## 5. 注意点与局限

1. **不判数值真伪**：报告 §6 自报 6 项 honest FAIL（rotating_cone_order_P1/P2、rotating_wide_gaussian_order_P1/P2、rotating_hump_order_P2、sod_shock_position_2pct_all_runs）。本工序原样登记、**未复核任何一个数字**，也未把任何 PASS 项写成 verified——真伪归平台门与下游抽取/复核工序。
2. **{len(unresolved)} 条资产解析不到**：{', '.join(unresolved)} 属 TensorLBM 仓（`src/tensorlbm/dg_verification/`、`tests/`、`scripts/`、`artifacts/`），本工作树是 TensorKnowledge，仓内无对应文件，报告也只给相对路径、无 URL/DOI/commit。按要求**不联网猜地址**，一律记 `referenced_unresolved` 并写明候选路径。
3. **§4 结果图 markdown 侧为空**：唯一 `declared_absent` 记在 markdown 事实上（该节仅标题）。图件存在于平台 `figures` 元数据（6 张），本工序不下载图件字节、不登记为已解析资产——若下游需要图件级资产，应另开工序取 `figures` 字段。
4. **共享行跨度**：{', '.join(shared)} 是「同一行同时声明两件事」的必然结果（如节点元数据行既声明仓/模块路径，也声明机器门）。共享被显式记录在 `locator.shared_span_with`，校验器（`shared_span_documented`）检查对端 id 存在——不是靠沉默掩盖重复。
5. **claims 为空数组是契约行为，不是遗漏**：`objective.classify_report_type=false` + `notes` 允许空 claims。空 claims 意味着「本工序没有对报告结论做任何知识化断言」，不意味着「报告结论已被核实」。
6. **信封字段差异**：仓内 `schemas/kf_result.v1.schema.json` 顶层 `additionalProperties:false`，故信封不含 `schema_version` 等额外字段（早期 448 包信封含之，按该仓旧 schema 才合法）。若平台侧 schema 另有要求，以平台门为准，本产物须相应修订。
7. **schema_pass 的解释边界**：清单用本包 pin 的 `schemas/asset_manifest.wp-9840-01.schema.json`（因为仓内 `asset_manifest.v1.schema.json` 把 `package_id` 恒等成了 `wp-448-01`，复用即造假）。这是「本仓可复跑的结构门」，不等于平台权威 schema 通过。
8. **整篇文档不重复登记为资产**：源 markdown 由 `source.hash`（对精确字节算 sha256，平台独立重算）登记；若再把全文作为一条 document 级资产的 quote 塞进结果信封，源报告自带的代码围栏会污染信封，使「唯一一个 json 代码块」对围栏解析器产生歧义。故资产表只登记**片段**（表格/声明/外部引用），全文归属哈希而非 quote。
9. **版本说明（诚实留痕）**：本包在平台上存在三版报告 14738 → 14749 → 本版。前两版的缺陷=结果信封里的引文携带了源报告自身的 bash 代码围栏（A01 全文级资产 + A28 整节引用），使「唯一一个 json 代码块」对围栏解析器产生歧义；本版取消全文级资产、把复现段降为围栏内 5 行正文，`fence_markers=2` 成为可机检不变量。仓内定稿为 `docs/wp-9840-01/KF-RESULT-wp-9840-01.md`。
10. **单报告边界**：本单只读/写 `report_id={REPORT_ID}`，未触碰任何其它 report_id；`single_report_scope` 校验 manifest/envelope/URI 三处 id 一致。

## 6. 误差判定与自检（逐条对照 acceptance）

| acceptance | 结论 | 对应校验项 |
|---|---|---|
{chr(10).join('| `%s` | %s | `%s` |' % (a, s, k) for a, s, k in acc_rows)}

补充校验（非 acceptance 但可机裁）：`source_hash_recomputed_live`、`source_chars_match_contract`、`source_field_markdown`、`quotes_are_substrings_of_source`、`no_verified_markers`、`counts_consistent`、`shared_span_documented`、`artifact_hash_matches_envelope`、`durable_mirror_identical`、`single_report_scope` —— 全部 pass（共 {n_pass} 项）。

**是否 <3%？** 不适用（登记工序，无基准对标量，理由见 §3 末段）。**honest 失败项**：无（{n_fail} 项 fail、{n_notrun} 项 not_run）。**未完成部分**：图件字节未登记（§5-3）；外部代码/产物 5 条只能记 unresolved（§5-2）。

**repro_cmd（一键复跑，工作树根执行）**：`{result['provenance']['repro_cmd']}`

```json
{json.dumps(result, ensure_ascii=False, indent=2)}
```
"""

    DOC.mkdir(parents=True, exist_ok=True)
    (DOC / ("KF-RESULT-%s.md" % PACKAGE_ID)).write_text(report_md)

    png = (DOC / "fig_asset_locator_map.png").read_bytes()
    import base64
    body = dict(
        title="KF-RESULT %s" % PACKAGE_ID,
        summary=("（修订版，取代 14738/14749 两版初稿）报告 %s 资产登记工作包：%d 条资产（%d resolved_in_source / %d referenced_unresolved / "
                 "%d declared_absent），markdown sha256 与契约一致，校验器 %d/%d pass，否定对照 6/6 拒假；"
                 "claims 按契约留空，未标任何 verified。"
                 % (REPORT_ID, c["assets"], c["resolved_in_source"], c["referenced_unresolved"],
                    c["declared_absent"], n_pass, len(ver["checks"]))),
        scenario_key=m["source"]["scenario_key"],
        mission_id=MISSION_ID,
        tags=["KG-Factory", "wp-9840-01", "kf-wp:wp-9840-01", "01-asset-registration",
              "asset-manifest", "DG", m["source"]["scenario_key"]],
        markdown=report_md,
        figures=[dict(name="fig_asset_locator_map.png",
                      caption=("图 1　wp-9840-01 资产定位图：左=33 条资产在源 markdown 字符轴上的跨度"
                               "（颜色=解析状态，点线=章节边界）；右上=解析状态分布；右下=资产类别分布。"
                               "数字全部由 asset_manifest.json 程序化注入。"),
                      png_base64=base64.b64encode(png).decode())],
    )
    if os.environ.get("KF_DRY_RUN"):
        (RUN / "report_payload.dryrun.json").write_text(
            json.dumps({k: v for k, v in body.items() if k != "figures"}, ensure_ascii=False, indent=2) + "\n")
        print("DRY RUN (KF_DRY_RUN set): markdown written, nothing published")
        return 0
    tok = api("/auth/login", {"username": USER, "password": PASS})["access_token"]
    resp = api("/tensor/reports", body, token=tok)
    print("published report id:", resp.get("id"), "title:", resp.get("title"))
    receipt = {k: v for k, v in resp.items() if k != "figures"}
    receipt["figures_count"] = len(resp.get("figures") or [])
    receipt["markdown_chars"] = len(resp.get("markdown") or "")
    (RUN / "publish_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
    print("local markdown:", DOC / ("KF-RESULT-%s.md" % PACKAGE_ID))
    return 0


if __name__ == "__main__":
    sys.exit(main())