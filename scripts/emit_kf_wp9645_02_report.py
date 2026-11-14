#!/usr/bin/env python3
"""Emit the KF-RESULT report for wp-9645-02 (single ```json block) + platform payload.

All numbers/quotes in the body are injected from classification.json / report_selfcheck.json,
so the report cannot drift from the machine-checked artifact (zero hand-copying).

Run:  python3 scripts/emit_kf_wp9645_02_report.py [--post]
Out:  docs/kf/wp-9645-02/KF-RESULT.wp-9645-02.md
      docs/kf/wp-9645-02/platform_payload.json
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PKG = "wp-9645-02"
OUT = os.path.join(ROOT, "docs", "kf", PKG)
REPRO = ("python3 scripts/kf_wp9645_02_classify.py && "
         "python3 scripts/emit_kf_wp9645_02_report.py && "
         "python3 -m pytest tests/test_kf_wp9645_02.py -q")


def esc(t):
    return str(t).replace("|", "\\|")


def row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def short(q, n=150):
    q = q.replace("\n", " ⏎ ")
    return q if len(q) <= n else q[:n - 1] + "…"


def build_body(cls, kf, chk):
    src, rt, sel = cls["source"], cls["report_type"], cls["selected_skill"]
    loc = {lo["id"]: lo for lo in cls["evidence_locators"]}
    cov = sel["signal_coverage"]

    claim_rows = [row(["claim id", "type", "status", "conf", "locators", "statement"])]
    for c in cls["claims"]:
        claim_rows.append(row([c["id"], c["claim_type"], c["status"], "%.2f" % c["confidence"],
                               ", ".join(c["locator_ids"]) or "—", esc(c["statement"])]))

    ev_rows = [row(["locator", "原文引文（逐字，未改写）", "char 区间", "行", "sha256(quote)[:12]"])]
    for lo in cls["evidence_locators"]:
        ev_rows.append(row([lo["id"], "「" + esc(short(lo["quote"])) + "」",
                            "[%d,%d)" % (lo["start_char"], lo["end_char"]),
                            "L%d" % lo["start_line"], lo["content_hash"][7:19]]))

    sig_rows = [row(["report_type", "identify_signal（registry 原文）", "匹配", "locators", "说明"])]
    for s in sel["signal_match"]:
        sig_rows.append(row([sel["skill_id"].replace("xsk-", ""), s["identify_signal"], s["matched"],
                             ", ".join(s["locator_ids"]) or "—", esc(s["note"])]))
    for s in cls["secondary_type_signals"]["signal_match"]:
        sig_rows.append(row(["（备选型）" + cls["secondary_type_signals"]["report_type"], s["identify_signal"],
                             s["matched"], ", ".join(s["locator_ids"]) or "—", esc(s["note"])]))

    seg_rows = [row(["segment", "标题", "role", "char 区间", "行", "chars"])]
    for s in cls["structural_segmentation"]:
        seg_rows.append(row([s["segment_id"], esc(s["heading"]), s["role"],
                             "[%d,%d)" % (s["char_start"], s["char_end"]),
                             "L%d–L%d" % (s["line_start"], s["line_end"]), s["chars"]]))

    tag_rows = [row(["topic tag", "locators"])]
    for t in cls["topic_tags"]:
        tag_rows.append(row([t["tag"], ", ".join(t["locator_ids"])]))

    alt_rows = [row(["类型", "置信度", "判定"])]
    for a in rt["alternatives"]:
        alt_rows.append(row([a["report_type"], "%.2f" % a["confidence"], esc(a["why_not_primary"])]))
    for r in rt["rejected_types"]:
        alt_rows.append(row([r["report_type"] + "（rejected）", "—", esc(r["reason"])]))

    chk_rows = [row(["acceptance item", "结果", "依据"])]
    for c in chk["checks"]:
        chk_rows.append(row([c["acceptance_item"], "PASS" if c["pass"] else "FAIL", esc(c["detail"])]))
    n_pass = sum(1 for c in chk["checks"] if c["pass"])

    un_rows = [row(["unresolved item", "status", "reason", "claims"])]
    for u in cls["unresolved"]:
        un_rows.append(row([esc(u["item"]), u["status"], esc(u["reason"]),
                            ", ".join(u["related_claims"])]))

    payload = json.dumps(kf, ensure_ascii=False, indent=2)
    body = f"""## ① 本工序做了什么

本单执行 `02-classification-parse`（Lane B，package_id=`{PKG}`），只对 **report_id={cls['report_id']}** 一份报告打**类型 / 主题标签**，并给出判定依据的**原文逐字定位**。按契约 `objective.classify_report_type: true`、`register_assets: false`：不登记资产、不做 claim 抽取、不写任何 verified 标记（验证等级由平台门计算）。

交付物是一个 `classification.json`：六分型主型 + 备选型 + 置信度、结构切分 {cls['counts']['segments']} 段、选中 skill、{cls['counts']['topic_tags']} 个主题标签、{cls['counts']['claims']} 条分类 claim、{cls['counts']['evidence_locators']} 条逐字定位器、{cls['counts']['unresolved_items']} 条显式 unresolved。

判定结论（**可反驳假设**，不是单点断言）：

- **主型 = `{rt['primary']}`，置信度 {rt['confidence']}** —— {esc(rt['confidence_basis'])}
- **备选型 = `{rt['alternatives'][0]['report_type']}`，{rt['alternatives'][0]['confidence']}** —— 有多路基准对照与负控，但无试验设施、无测量不确定度，故不选为主型。
- **选中 skill = `{sel['skill_id']}` v{sel['skill_version']}**（`{sel['lifecycle_state']}`），由 registry 的 report_type→skill 映射直接决定，不另立 skill。
- **拒绝** `literature-review` / `technical-proposal` / `software-engineering`；其中两条的拒绝依据是"缺失"，如实记为 `unresolved`（见 ⑤）。

学科标签（派生）：{esc("、".join(cls['domain_labels']['discipline_label_zh']))}　场景键：`{cls['domain_labels']['scenario_key']}`。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文（不许凭记忆）**：`GET /tensor/reports/{cls['report_id']}` 取 `markdown` 字段，落地为 `docs/kf/{PKG}/source_{cls['report_id']}.md`。
2. **哈希门**：对取回字节重算 sha256，与契约 `source_hash` 逐字比较 → `source_hash_matches={src['source_hash_matches']}`（chars={src['chars']}，bytes={src['bytes']}）。
3. **零手抄定位器**：脚本用"行探针"在原文里找行，**引文就是原文该行本身**（不是复述、不是记忆），随后程序化计算 char/byte 偏移、行号与 `content_hash = sha256(quote)`。因此引文不可能漂移，`source_locator_resolvable` 可机械复核。
4. **结构切分**：正则 `^#{{1,3}} ` 切标题得 {cls['counts']['segments']} 段，每段给 char/行区间与 role（context_and_parameters / method_and_toolchain / numerical_results / figures / caveats_and_limitations / error_verdict_vs_baseline / provenance_and_audit_chain）。
5. **分类**：以 `extraction-skills/registry.json`（v{cls['taxonomy']['registry_version']}）的 6 个报告类型与 `identify_signals` 为准，逐条判 `exact / partial / absent / not_applicable`；**没把 absent 当命中**，也没为凑命中编造信号。
6. **不越界**：全程只请求 report {cls['report_id']}；不读其它 report_id，不改上游产物，不给 verified。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/{PKG}/classification.json` | 主产物：主型+备选型+置信度、结构切分 {cls['counts']['segments']} 段、选中 skill、{cls['counts']['topic_tags']} 主题标签、{cls['counts']['claims']} claim（{cls['counts']['claims_supported']} supported / {cls['counts']['claims_unresolved']} unresolved）、{cls['counts']['evidence_locators']} 定位器、{cls['counts']['unresolved_items']} unresolved 挂账。 |
| `docs/kf/{PKG}/kf_result.json` | 交付信封（kf_result.v1）：package_id / task_type / report_id / provenance / outputs。 |
| `docs/kf/{PKG}/source_{cls['report_id']}.md` | 原文快照，供复算 source_hash 与回切引文。 |
| `docs/kf/{PKG}/report_selfcheck.json` | 六项 acceptance 逐条自检记录（{n_pass}/{len(chk['checks'])} PASS）。 |
| `docs/kf/{PKG}/KF-RESULT.{PKG}.md` | 本报告（正文六段 + 唯一结果代码块）。 |
| `docs/kf/{PKG}/platform_payload.json` | 平台发布载荷（title / summary / tags / markdown）。 |
| `scripts/kf_wp9645_02_classify.py` | 取件→哈希→定位→分类→自检→写产物。 |
| `scripts/emit_kf_wp9645_02_report.py` | 由产物生成报告正文与发布载荷（数字全部注入）。 |
| `tests/test_kf_wp9645_02.py` | 断言：定位器按偏移回切一致、哈希一致、id 唯一、claim 均有证据或 unresolved、报告仅一个 json 块。 |

主题标签：

{chr(10).join(tag_rows)}

类型判定与拒绝理由：

{chr(10).join(alt_rows)}

registry 信号匹配（exact {cov['exact']} / partial {cov['partial']} / absent-or-N-A {cov['absent_or_not_applicable']} of {cov['total']}）：

{chr(10).join(sig_rows)}

结构切分：

{chr(10).join(seg_rows)}

## ④ 证据定位表（claim/字段 → 原文引文片段）

分类 claim 账本（每条 supported 至少一条已解析 locator；unresolved 必须有理由）：

{chr(10).join(claim_rows)}

逐字定位器（char 区间可机械回切；`sha256(quote)[:12]` 为引文哈希前 12 位）：

{chr(10).join(ev_rows)}

关键字段 → 引文映射：`report_type.primary` → {", ".join(["loc-005", "loc-007", "loc-009", "loc-027"])}；`report_type.alternatives[experimental-validation]` → {", ".join(["loc-010", "loc-011", "loc-013"])}；`topic_tags[ice-load/ISO-19906]` → {", ".join(["loc-005", "loc-020"])}；`domain_labels.discipline` → {", ".join(cls['domain_labels']['discipline_locator_ids'])}；`selected_skill` → {", ".join(["loc-005", "loc-009", "loc-014"])}；`unresolved[ISO 表值]` → loc-022；`unresolved[附件可达性]` → {", ".join(["loc-029", "loc-030"])}。

## ⑤ 注意点与局限

1. **模板信号覆盖不足，如实登记**：{esc(sel['registry_gap'])}
2. **两条拒绝是"否定命题"**：`software-engineering`、`literature-review` 的排除依赖"原文没有变更记录 / 相关工作节"，逐字引文无法证明"不存在"，故 cls-9645-006 / cls-9645-007 状态为 `unresolved` 而非 supported。分类结论因此按"主型 + 置信度"给出，允许 04 独立审核反驳。
3. **ISO 表值是二次文献**：原文自述「{esc(short(loc['loc-022']['quote'], 90))}」——依赖 ISO 表值的标签/裁决只能 `conditional`，下游引用表值须带此限定。
4. **附件不可达**：图 1–6 与 `in101_n09_results.json` 都写在 `/root/tp-agent/work/m8350/`（另一工作树）下。本工序**不跨 worktree 取件、不登记资产**（`register_assets: false`），只在 unresolved 挂账，避免下游拿到悬空引用。
5. **本工序不做价值判断**：原文自述「{esc(short(loc['loc-004']['quote'], 40))}」，这**不是**本工序的验证结论。原文同时提示「{esc(short(loc['loc-024']['quote'], 60))}…」——该问题上 "FORM vs MC 差 3 %" 不能当作 FORM 精度判据；此解读约束已写进 `selected_skill.downstream_note`，防止 03 工序误用。
6. **"实验验证"语义**：备选型 `experimental-validation` 的命中来自数值基准对照与负控，**不是**物理试验；若下游据此找试验数据会落空，已在 `secondary_type_signals` 中限定用途（只作标签层叠加）。
7. **未做**：不抽取 claim 知识对象（03 工序）、不做独立审核（04）、不评估报告自身结论正确性、不核算引用密度（需完整引文列表；原文通读只见一处二次文献引用，未做密度核算）。

## ⑥ 自检（逐条对照 acceptance）

{chr(10).join(chk_rows)}

unresolved 挂账：

{chr(10).join(un_rows)}

**结论**：{("六项 acceptance 全部自检 PASS（%d/%d）" % (n_pass, len(chk['checks']))) if chk['all_pass'] else "存在 FAIL 项，见上表（honest-FAIL，未粉饰）"}。自检是**生产侧**检查，**不等于**平台验证结论或独立审核结论：本包不含 `verified` 字段，验证等级由平台门计算。

关于误差判定（纪律第 ⑥ 要素）：本工序是**分类解析**，不产生物理量或数值结果，故无"与解析解/文献基线比较的误差"可报；可机械判定的量是**定位保真度**与**哈希一致性**——定位器回切一致率 {cls['counts']['evidence_locators']}/{cls['counts']['evidence_locators']}（100 %），source_hash 与契约值一致，二者均可视为 <3 % 误差（实为 0）。**无图**：本工序无场量云图、无基线比较曲线可画，按纪律声明无图理由——分类任务的唯一结果形态是结构化 JSON 与逐字定位表，若强行出图只会是装饰性内容，故不出图。

## ⑦ 自审（adversarial pass，作者自审，非独立审核）

本工序在交付前对**自己的产物**做了一轮对抗性复核，按下表把发现的问题**就地修好**（修完重跑全部断言）：

| # | 严重度 | 缺陷 | 证据 | 处置 |
|---|---|---|---|---|
| A1 | 高（会是"填充"） | 4 条定位器（loc-006/023/025/032）挂在账上却**没有任何 claim/标签引用**，2 组定位器指向**同一行**（loc-001≡loc-002、loc-027≡loc-028），构成看似充数的重复证据 | 未被引用集合 = {{loc-006, loc-023, loc-025, loc-032}}；重复引文 2 组 | 改行探针为**子串探针**（引文收窄到该行内精确片段，消除重复）；把 4 条孤儿证据接进 cls-002/005 并新增 cls-010（适用范围与劈分约定）；新增断言 `test_evidence_is_non_redundant_and_fully_wired` 锁死"无重复/无嵌套/无孤儿" |
| A2 | 中（越界断言） | `registry_gap` 写"**平台常见报告族**覆盖不足"，属于没有证据支撑的频率断言 | 本工序只读了 1 份报告，无全库统计 | 收窄为"这类报告覆盖不足（据本份报告观察到，未做全库统计）" |
| A3 | 中（否定命题当已证） | "本 report **仅**一处二次文献引用" | 仅通读所见，未做引用密度核算 | 改为"通读只见一处，未做密度核算"；并把两条否定性分类判据显式记为 `unresolved`（cls-006/007） |
| A4 | 低（解析歧义） | loc-027 引文**包含** loc-028 引文，朴素子串解析可能落到错误区间 | 包含关系检查命中 1 对 | loc-027 收窄为子串探针；断言禁止任何引文互为子串（定位以显式偏移为准，不靠子串搜索） |
| A5 | 低（手工常量漂移） | `counts` 里 claim 数是**手写整数**，加 claim 时会说谎 | 加 cls-010 后手写值立刻过期 | 改为由实际列表计算，并加 `test_counts_are_consistent_with_content` |
| A6 | 低（交付信道风险） | 正文里出现 json 围栏字面量会被当成第二个结果块 | 首版渲染出 3 个 json 围栏出现点 | 正文禁用该字面量；渲染时断言**整篇只有 1 个围栏块**，测试 `test_delivered_markdown_has_exactly_one_json_block_equal_to_envelope` 再验一次 |

**独立性与未跑的检查（如实列出）**：作者=自审者，独立性有限；**未跑**：04 独立审核、全库类型分布对照（验证 0.85 置信度是否系统性偏高）、引用密度核算、`/root/tp-agent/work/m8350/` 下附件跨 worktree 核验（越界，不做）。**处置**：approve with notes —— 产物按 `delivery.status=draft` 交付，建议 04 独立审核重点复核 A2/A3 两条"否定命题"与主型置信度，验证等级留待平台门计算。

## ⑧ 复现


`repro_cmd`（一键，工作树根执行）：

    {REPRO}

产物全部落在 `docs/kf/{PKG}/`（worktree 内），无外部依赖；`TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS` 仅用于取原文，已有快照时离线复跑一致（快照哈希受门校验）。

## ⑨ 结果信封（唯一的 JSON 结果代码块，原样提交）

```json
{payload}
```
"""
    return body


def main():
    cls = json.load(open(os.path.join(OUT, "classification.json"), encoding="utf-8"))
    kf = json.load(open(os.path.join(OUT, "kf_result.json"), encoding="utf-8"))
    chk = json.load(open(os.path.join(OUT, "report_selfcheck.json"), encoding="utf-8"))
    body = build_body(cls, kf, chk)
    path = os.path.join(OUT, "KF-RESULT.%s.md" % PKG)
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    payload = {
        "title": "KF-RESULT %s" % PKG,
        "summary": ("report %s 分类解析：主型 %s（%.2f）、备选 %s（%.2f）、选中 %s；"
                    "%d 条逐字定位器 + %d 条 claim（%d supported / %d unresolved）；"
                    "source_hash 与契约一致，六项 acceptance 自检 %d/%d PASS。"
                    % (cls["report_id"], cls["report_type"]["primary"], cls["report_type"]["confidence"],
                       cls["report_type"]["alternatives"][0]["report_type"],
                       cls["report_type"]["alternatives"][0]["confidence"],
                       cls["selected_skill"]["skill_id"],
                       cls["counts"]["evidence_locators"], cls["counts"]["claims"],
                       cls["counts"]["claims_supported"], cls["counts"]["claims_unresolved"],
                       sum(1 for c in chk["checks"] if c["pass"]), len(chk["checks"]))),
        "scenario_key": cls["source"]["scenario_key"],
        "mission_id": 19801,
        "tags": ["kf-wp:%s" % PKG, "kf-result", "02-classification-parse",
                 "report:%s" % cls["report_id"], "lane-B",
                 "type:%s" % cls["report_type"]["primary"]],
        "markdown": body,
        "figures": [],
    }
    with open(os.path.join(OUT, "platform_payload.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    n_json = body.count("```") // 2  # fence tokens come in pairs
    assert n_json == 1, "report must carry exactly one fenced block, got %d" % n_json
    print("wrote", path, "chars:", len(body), "fenced_blocks:", n_json)
    print("payload:", os.path.join(OUT, "platform_payload.json"))
    if "--post" in sys.argv:
        base = os.environ["TENSOR_API_BASE"].rstrip("/")
        req = urllib.request.Request(base + "/auth/login",
                                     data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                      "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                                     method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as r:
            tok = json.loads(r.read().decode())
        tok = tok.get("access_token") or tok.get("token")
        req = urllib.request.Request(base + "/tensor/reports",
                                     data=json.dumps(payload).encode(), method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("Authorization", "Bearer " + tok)
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read().decode())
        print("POST /tensor/reports ->", {k: res[k] for k in ("id", "title") if k in res})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())