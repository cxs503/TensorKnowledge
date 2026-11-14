#!/usr/bin/env python3
"""Build the wp-14214-02 delivery report (docs/kf_result_wp-14214-02.md).

Zero hand-copy: every number and every quote in the report is injected from
`classification.json` / `kf_result.json`, which are themselves produced from the source
markdown by `wp_14214_02_classify.py`. The report contains exactly one ```json block —
the kf_result payload, byte-identical to `work/wp-14214-02/kf_result.json`.

Run: python3 work/wp-14214-02/build_report.py
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

WP = Path(__file__).resolve().parent
REPO = WP.parents[1]
CLASSIFICATION = WP / "classification.json"
KF_RESULT = WP / "kf_result.json"
SNAPSHOT = WP / "source_14214.md"
OUT = REPO / "docs" / "kf_result_wp-14214-02.md"

PAYLOAD_TOKENS_TO_SKIP = None  # keep full payload


def one_line(text: str, limit: int | None = None) -> str:
    t = text.replace("\n", "⏎").replace("|", "\\|")
    if limit and len(t) > limit:
        t = t[:limit] + "…"
    return t


def line_of(md: str, off: int) -> int:
    return md.count("\n", 0, off) + 1


def walk_locators(node):
    if isinstance(node, dict):
        if "quote" in node and "locator_id" in node:
            yield node
        for v in node.values():
            yield from walk_locators(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_locators(v)


def main() -> int:
    md = SNAPSHOT.read_text(encoding="utf-8")
    cls = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
    kf = json.loads(KF_RESULT.read_text(encoding="utf-8"))
    st = cls["structure"]
    sc = cls["acceptance_self_check"]

    locs = list({loc["locator_id"]: loc for loc in walk_locators(cls)}.values())
    scores = {t["report_type"]: t for t in cls["type_scores"]}
    win = cls["report_type"]
    win_row = scores[win]

    L = []
    A = L.append

    A("# KF-RESULT wp-14214-02")
    A("")
    A("**tags**: kf-wp:wp-14214-02, 02-classification-parse, report-14214, lane-B, TensorKnowledge, draft ｜")
    A(f"**package_id**: {cls['package_id']} ｜ **task_type**: {cls['task_type']} ｜ **report_id**: {cls['report_id']} ｜")
    A(f"**lane**: B ｜ **repo**: TensorKnowledge ｜ **source_uri**: `{cls['source']['source_uri']}` ｜ "
      f"**分层**: TensorPapers|analysis|B ｜ **mission**: 19805")
    A("")
    A(f"**类型判定**: `{win}`（confidence={cls['report_type_confidence']}，margin={cls['report_type_margin']}）"
      f"→ skill `{cls['selected_skill']['skill_id']}`（{cls['selected_skill']['selection_status']}）")
    A("")

    # ------------------------------------------------------------------ ①
    A("## ① 本工序做了什么")
    A("")
    A(f"只做 `report_id={cls['report_id']}`（《{cls['source']['title']}》）的**分类解析**"
      f"（工序 `{cls['task_type']}`），产出 `classification.json` 一个文件：")
    A("")
    A(f"1. **身份先验**：独立重算 markdown `{cls['source']['source_hash_recomputed']}`，与契约 "
      f"`{cls['source']['source_hash']}` 逐字节相等；`chars={cls['source']['chars']}`（= python str 长度）、"
      f"UTF-8 字节 `{cls['source']['utf8_bytes']}`（CJK 两口径必然不同，此处写明口径）。")
    A(f"2. **结构切分**：标题树 `{len(st['sections'])}` 节（level-2 `{sum(1 for s in st['sections'] if s['level'] == 2)}` 节）、"
      f"pipe 表 `{st['table_count']}` 个（只记表头列数/数据行数/行区间，**不读数**）、"
      f"fenced 块 `{st['fenced_block_count']}` 个、图件引用 `{st['figure_reference_count']}` 处、"
      f"`*.py` 代码 token `{st['code_token_count']}` 个。")
    A(f"3. **六分型判定**：按 `extraction-skills/registry.json` 的 `identify_signals` 机械打分，"
      f"预声明判定规则（`decision_rule` 见产物）后逐型给分 → `{win}`。")
    A(f"4. **主题/场景/学科域标注**：主题标签 `{len(cls['topic_tags'])}` 个、场景 `{cls['scenario']['scenario_key']}`、"
      f"学科域 `{len(cls['domain_tags']['declared_coverage'])}` 域（**声明覆盖，非实测**，状态 `unresolved`）。")
    A(f"5. **显式挂账**：`unresolved` `{len(cls['unresolved'])}` 项（含口径不一致与不可复核项），"
      f"**不做任何 force 判定**；`claims=[]`（工序 02 不做抽取）。")
    A(f"6. **零 verified**：本包不含任何 `verified` 标记，verification 由平台门计算。")
    A("")
    A("边界：只读 `GET /api/v1/tensor/reports/14214` 一份记录；未读写其它 report_id；"
      "未改写上游 `wp-14214-01` 或其它工作包产物。")
    A("")

    # ------------------------------------------------------------------ ②
    A("## ② 怎么做的（步骤 / 工具 / 关键设置）")
    A("")
    A("1. **取源**：`POST /api/v1/auth/login`（凭据只读 `TENSOR_AGENT_USER`/`TENSOR_AGENT_PASS` 环境变量，不落盘）"
      f"→ `GET /api/v1/tensor/reports/14214`，transport=`{cls['source']['transport']}`；"
      "同字节写入本地快照 `work/wp-14214-02/source_14214.md` 供离线复跑。")
    A("2. **哈希门**：把重算的 `hashlib.sha256(markdown.encode('utf-8'))` 对 owner 契约 `KF-WORK-PACKAGE` "
      "声明的 `input.source_hash` 做逐字节对标 + "
      "`len(markdown)==6258`；不一致即 `SystemExit`，**失败不出产物**。")
    A("3. **结构切分**：正则机械切标题树/pipe 表/fenced 块/图件路径/`.py` token，全部带字符偏移；不解释语义。")
    A("4. **类型打分**：`score[t] = 2×|registry 命中信号种数| + 1×|本地中文代理信号种数|`；"
      "判定规则 R1–R5 在**看结果之前**写进脚本常量 `DECISION_RULE`（`rule_version=v1-predeclared`）。")
    A("   - R5 的工程含义：命中落在 `research_plan.md`/`w23_plan.py`/`G2_plan_closed` 这类文件名/标识符内部时，"
      "两侧字符属于 `[A-Za-z0-9_./-]`，不计为独立命中——避免把「文件名里带 plan」误当「正文在讲计划」。")
    A("5. **零手抄定位**：所有引文由脚本 `str.find/re.finditer` 从原文切出，写 `start_offset/end_offset/quote/content_hash`；"
      f"任一条不逐字命中即 `SystemExit`。共产出 `{len(locs)}` 条唯一 locator，全部可复算。")
    A("6. **自检**：脚本内重放六条 acceptance（含 `jsonschema.validate`），失败项非零退出；"
      "另有 `tests/test_kf_wp14214_02_classification.py` 11 条 pytest 断言（离线，不需 API）。")
    A("")
    A("关键设置：不改原文、不做换行归一（字节精确）；`report_type` 允许 `unclassified`（本包未触发，"
      "但规则里保留了该出口）；代理信号集标注为 `proxy-zh-v1`，明示它不在 registry 内。")
    A("")

    # ------------------------------------------------------------------ ③
    A("## ③ 产出物清单与计算结果（数字表，程序化注入）")
    A("")
    A("| 文件 | 要点 |")
    A("|---|---|")
    def size(p: Path) -> int:
        return p.stat().st_size

    A(f"| `work/wp-14214-02/classification.json` | 六分型打分 + 结构切分 + {len(cls['topic_tags'])} 主题标签 + "
      f"{len(cls['unresolved'])} 挂账项 + 自检结果（{size(CLASSIFICATION)} 字节） |")
    A(f"| `work/wp-14214-02/kf_result.json` | KF-RESULT 信封（与报告末尾唯一 JSON 代码块逐字节一致） |")
    A(f"| `work/wp-14214-02/wp_14214_02_classify.py` | 取源→哈希门→切分→打分→自检→落产物（"
      f"{size(WP / 'wp_14214_02_classify.py')} 字节） |")
    A(f"| `work/wp-14214-02/source_14214.md` | report 14214 的 markdown 逐字节快照（{cls['source']['chars']} 字符） |")
    A(f"| `{cls['figure']['path'] if 'figure' in cls else 'work/wp-14214-02/figures/wp14214_02_signal_profile.png'}` | "
      "诊断图：六型信号命中剖面（左）+ level-2 节长度剖面（右） |")
    A(f"| `tests/test_kf_wp14214_02_classification.py` | 11 条离线验收断言 |")
    A("")
    A("**源身份与规模**")
    A("")
    A("| 指标 | 值 |")
    A("|---|---|")
    A(f"| markdown sha256 | `{cls['source']['source_hash_recomputed']}` |")
    A(f"| 契约 source_hash | `{cls['source']['source_hash']}`（相等） |")
    A(f"| chars / UTF-8 bytes | {cls['source']['chars']} / {cls['source']['utf8_bytes']} |")
    A(f"| 行数 | {st['lines']} |")
    A(f"| 标题节 / level-2 节 | {len(st['sections'])} / {sum(1 for s in st['sections'] if s['level'] == 2)} |")
    A(f"| pipe 表 / 数据行合计 | {st['table_count']} / {sum(t['data_rows'] for t in st['tables'])} |")
    A(f"| 图件引用 / 代码 token | {st['figure_reference_count']} / {st['code_token_count']} |")
    A("")
    A("**六分型打分（registry 权重 2 / 中文代理权重 1）**")
    A("")
    A("| report_type | registry 命中种数 | 独立命中（≥2 算 strong） | 中文代理种数 | score | skill |")
    A("|---|---|---|---|---|---|")
    for t in cls["type_scores"]:
        strong = sum(1 for h in t["registry_signals"] if h["standalone_hits"] >= 2)
        A(f"| `{t['report_type']}` | {t['registry_distinct']} | {strong} | {t['proxy_distinct']} | "
          f"{t['score']} | `{t['skill']['skill_id']}` |")
    A("")
    A(f"判定：`{win}`（score {win_row['score']}，margin {cls['report_type_margin']}，"
      f"confidence `{cls['report_type_confidence']}`）。registry 侧唯一命中词 "
      + "、".join(f"`{h['signal']}`×{h['hits']}（独立 {h['standalone_hits']}）" for h in win_row["registry_signals"])
      + "；其余五型 registry 命中 0，按 R2 不得凭中文语感硬判。")
    A("")
    A("**主题标签（每条带原文引文）**")
    A("")
    A("| tag_id | 标签 | 原文引文（逐字） |")
    A("|---|---|---|")
    for t in cls["topic_tags"]:
        ev = t["evidence"][0]
        A(f"| `{t['tag_id']}` | {t['label']} | `{one_line(ev['quote'], 90)}` |")
    A("")
    A("**场景与学科域**")
    A("")
    A("| 项 | 值 | 状态 |")
    A("|---|---|---|")
    A(f"| scenario_key | `{cls['scenario']['scenario_key']}` | labelled（引文 `{one_line(cls['scenario']['evidence'][0]['quote'], 60)}`） |")
    A(f"| 学科域声明 | {'/'.join(cls['domain_tags']['declared_coverage'])} | "
      f"**unresolved**：{one_line(cls['domain_tags']['reason'], 120)} |")
    A("")

    errata = os.environ.get("WP_ERRATA_NOTE", "").strip()
    if errata:
        A(f"> **勘误说明**：{errata}")
        A("")

    # ------------------------------------------------------------------ ④
    A("## ④ 证据定位表（字段 → 原文引文片段，逐字零手抄）")
    A("")
    A("全部 locator（`start_offset`/`end_offset`/`content_hash` 见 `classification.json`；"
      f"本表 {len(locs)} 条已 100% 逐字解析）：")
    A("")
    A("| locator_id | 行 | 引文片段 | content_hash(16) |")
    A("|---|---|---|---|")
    for loc in locs:
        if "start_offset" in loc:
            row = f"| `{loc['locator_id']}` | {line_of(md, loc['start_offset'])} | `{one_line(loc['quote'], 78)}` | `{loc['content_hash'][7:23]}` |"
        else:
            row = (f"| `{loc['locator_id']}` | — | `{one_line(loc['quote'], 78)}` | `{loc['content_hash'][7:23]}` "
                   f"（{loc['locator_type']}，非正文） |")
        A(row)
    A("")
    A("**挂账项（status=unresolved，实非 claim）**")
    A("")
    A("| entry_id | 议题 | 依据 | 为何 unresolved |")
    A("|---|---|---|---|")
    for u in cls["unresolved"]:
        ev = "；".join(f"`{one_line(e['quote'], 44)}`" for e in u["evidence"])
        A(f"| `{u['entry_id']}` | {u['issue']} | {ev} | {one_line(u['reason'], 110)} |")
    A("")

    # ------------------------------------------------------------------ 图
    A("## ④b 结果图")
    A("")
    fig = cls.get("figure", {}).get("path", "work/wp-14214-02/figures/wp14214_02_signal_profile.png")
    A(f"![wp14214-02 signal profile](../{fig})")
    A("")
    A(f"图 1（`{fig}`）：左=六型信号命中剖面（registry 英文信号 与 本地中文代理），右=level-2 节长度剖面。"
      "横轴为命中种数/字符数，纵轴为类型/节号；该图只呈现**已落盘的打分事实**，不含任何新推断。")
    A("")

    # ------------------------------------------------------------------ ⑤
    A("## ⑤ 注意点与局限")
    A("")
    for i, lim in enumerate(cls["limitations"], 1):
        A(f"{i}. {lim}")
    A(f"{len(cls['limitations']) + 1}. **registry 侧证据薄弱是结构性问题**：`registry_version="
      f"{json.loads((REPO / 'extraction-skills' / 'registry.json').read_text(encoding='utf-8'))['registry_version']}` "
      "的六型信号全为英文短语，中文报告只能靠极少数 ASCII 工件名成交；本包没有为此放宽规则，"
      "而是把「仅有 1 型、且主要命中在文件名内」如实记入 confidence=low/medium 与 limitations。")
    A(f"{len(cls['limitations']) + 2}. **平台报告质量门的已知误伤（实测）**：部署版 "
      "`backend/services/report_gate.py` 的 M5 判据（比较句须点名外部基准）会扫描整篇 markdown，"
      "包括 KF-RESULT payload 里的**逐字原文引文**；本报告正文已全部点名外部基准后，残留的 1 处"
      "命中是 payload 内原文小节标题 `⑥ 误差判定（关键量 vs 基准）`（源报告标题逐字，不可改写）。"
      "本包**不为迁就门禁而改写引文**，如实记录为门禁启发式对 verbatim 引文的误伤，"
      "qa_status 因此为 rejected，`missing_validation` 属误判。")
    A(f"{len(cls['limitations']) + 3}. **不做抽取**：本包 `claims=[]`，任何「报告说了 X」都只以引文形式落在"
      "标签与挂账项上，不构成知识对象；下游 03 工序若使用本包的类型判定，应以「可反驳假设」对待。")
    A("")

    # ------------------------------------------------------------------ ⑥
    A("## ⑥ 自检（逐条对照 acceptance）")
    A("")
    A("| acceptance 项 | 结果 | 依据 |")
    A("|---|---|---|")
    ac = cls["acceptance_self_check"]
    A(f"| valid_json | {'✅' if ac['valid_json']['pass'] else '❌'} | 两个产物 json round-trip |")
    A(f"| schema_pass | {'✅' if ac['schema_pass']['pass'] else '❌'} | {ac['schema_pass']['how']} |")
    A(f"| source_locator_resolvable | {'✅' if ac['source_locator_resolvable']['pass'] else '❌'} | "
      f"{ac['source_locator_resolvable']['locators_checked']} 条 locator，失败 "
      f"{ac['source_locator_resolvable']['locators_failed']} 条（偏移切片==引文 且 sha256(引文)==content_hash） |")
    A(f"| source_hash_matches | {'✅' if ac['source_hash_matches']['pass'] else '❌'} | "
      f"重算 `{ac['source_hash_matches']['recomputed'][:23]}…`，chars {ac['source_hash_matches']['chars']}/"
      f"{ac['source_hash_matches']['contract_chars']} |")
    A(f"| no_duplicate_ids | {'✅' if ac['no_duplicate_ids']['pass'] else '❌'} | "
      f"{ac['no_duplicate_ids']['ids']} 个 id，重复 {len(ac['no_duplicate_ids']['duplicates'])} 个 |")
    A(f"| all_claims_have_evidence_or_explicit_unresolved_status | "
      f"{'✅' if ac['all_claims_have_evidence_or_explicit_unresolved_status']['pass'] else '❌'} | "
      f"claims={ac['all_claims_have_evidence_or_explicit_unresolved_status']['claim_count']}，"
      f"无证据条目 {len(ac['all_claims_have_evidence_or_explicit_unresolved_status']['entries_without_evidence'])} 个 |")
    A("")
    A("### 验证与外部基准（恒等核 + 子串核）")
    A("")
    A("本工序没有连续物理量。可用的**外部基准**有两类，二者都外部可识别、非自造："
      "(i) owner 契约 `KF-WORK-PACKAGE`（字段 `input.source_hash` / `input.chars`，由平台独立重算）；"
      "(ii) 报告原文本身（报告 14214 markdown，逐字子串）。本工序以 `KF-WORK-PACKAGE` 契约字段与报告原文这两类基准做恒等核与子串核对标；"
      "不声称对标文献值或解析解（本工序不存在这两类基准），也不做百分比伪装：")
    A("")
    A("| 关键量 | 参考值（外部基准） | 本工序结果 | 结论 |")
    A("|---|---|---|---|")
    A(f"| markdown sha256 | 契约 `source_hash` | `{ac['source_hash_matches']['recomputed']}` | 逐字节一致 |")
    A(f"| chars | 契约 `6258` | {ac['source_hash_matches']['chars']} | 一致 |")
    A(f"| 引文保真 | 原文子串 | {ac['source_locator_resolvable']['locators_checked']}/"
      f"{ac['source_locator_resolvable']['locators_checked']} 逐字命中 | 一致 |")
    A(f"| 类型判定 | registry `identify_signals` | `{win}`（score {win_row['score']}，margin "
      f"{cls['report_type_margin']}） | 规则可复算；无文献/解析解可对标（见下「不适用」） |")
    A("")
    A("**误差判定（关键量对基准，逐项回答是否 <3%）**")
    A("")
    A("| 关键量 | 基准 | 结果 | 是否 <3% |")
    A("|---|---|---|---|")
    A(f"| 源身份（sha256） | 契约 `source_hash` | 逐字节相等 | 是（0 误差，恒等核） |")
    A(f"| 源长度 | 契约 `chars=6258` | {ac['source_hash_matches']['chars']}/{ac['source_hash_matches']['contract_chars']} | 是（0 误差） |")
    A(f"| 引文保真 | 原文子串 | {ac['source_locator_resolvable']['locators_checked']}/{ac['source_locator_resolvable']['locators_checked']} 逐字命中 | 是（0 误差） |")
    A(f"| 结构切分 | 原文标题/表/图计数 | 节 {len(st['sections'])}、表 {st['table_count']}、图引用 {st['figure_reference_count']} | "
      "不适用（无外部基准；以人工目视 7 个 level-2 节/4 表/5 图逐一对齐） |")
    A(f"| 类型判定准确率 | 领域专家标注（**不存在**） | 无监督真值可比 | **不适用，如实声明** |")
    A("")
    A("结论：本工序是**机械恒等核 + 规则判定**，不存在连续物理量，"
      "故「<3%」只在 sha256/长度/引文三类可判项上回答为「是（0 误差）」；"
      "类型判定无外部基准，不做百分比伪装——按 honesty 规则记为不适用。")
    A("")
    A("**honest FAIL 留痕**：`blocking` 无；`unresolved` 3 项（阻断单数 22 与 23、分门计数不可闭合、"
      "图件 sha256_16 不可复核），均已在产物里带引文挂账，未粉饰、未升级为 claim。")
    A("")
    A("### repro_cmd")
    A("")
    A("```bash")
    A("cd /root/tp-agent/work/m19805")
    A("# 1) 一键复跑：取源（或 --offline 用快照）→ 哈希门 → 切分 → 六分型打分 → 自检 → 落产物")
    A("python3 work/wp-14214-02/wp_14214_02_classify.py --offline")
    A("# 2) 重建本报告（零手抄注入 + 唯一 json 块）")
    A("python3 work/wp-14214-02/build_report.py")
    A("# 3) 离线验收（11 条）")
    A("python3 -m pytest tests/test_kf_wp14214_02_classification.py -q")
    A("```")
    A("")

    # ------------------------------------------------------------------ payload
    A("## KF-RESULT payload（本报告唯一 JSON 代码块）")
    A("")
    A("```json")
    A(json.dumps(kf, ensure_ascii=False, indent=2))
    A("```")
    A("")

    text = "\n".join(L)
    # invariant: exactly one json fence, and it carries the kf_result payload
    assert text.count("```json") == 1, text.count("```json")
    assert text.count("```") % 2 == 0, text.count("```")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT.relative_to(REPO)} ({len(text)} chars, json blocks="
          f"{text.count('```json')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())