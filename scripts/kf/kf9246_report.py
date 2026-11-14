"""wp-9246-02 报告 markdown 生成（数字全部由数据注入，零手抄）。"""

from __future__ import annotations

import json

import kf9246_spec as S


def _cell(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def _n_tests() -> int:
    """回归用例条数由测试文件自身统计，不手写。"""
    import re
    src = (S.REPO / "tests" / "test_kf_wp9246_02.py").read_text()
    return len(re.findall(r"(?m)^def test_", src))


def build_report(result: dict, classification: dict, checks: dict, png) -> str:
    src = classification["source"]
    rt = classification["report_type"]
    sig = classification["signals"]["per_type"]
    sf = classification["signals"]["step_fit"]
    probe = classification["probe_result"]
    secs = classification["structure"]["sections"]
    L: list[str] = []
    A = L.append

    A(f"# KF-RESULT {S.PACKAGE_ID}")
    A("")
    A(f"> 工作包 `{S.PACKAGE_ID}` · 工序 `{S.TASK_TYPE}` · lane {S.LANE} · mission {S.MISSION_ID} · "
      f"仓库 {S.DELIVERY_REPO}")
    A(f"> 源资产：`{S.SOURCE_URI}`（report_id={S.REPORT_ID}）· 源哈希 `{S.SOURCE_HASH}`")
    A("> 本报告是唯一结果信道：正文唯一一个 json 代码块 = 完整结果信封（`kf_result.json` 原样）。")
    A("")

    # ---------------- ① ----------------
    A("## ① 本工序做了什么")
    A("")
    A(f"对 `report_id={S.REPORT_ID}` 这**一份**报告做类型分类 + 结构切分：给报告打类型/主题标签、"
      "给出判定依据的原文逐字定位。**不抽 claim、不判真伪、不打 verified**"
      "（契约 `objective.classify_report_type: true`、`objective.register_assets: false`、notes「不做抽取」）。")
    A("")
    A("结论（可反驳的假设，不是裁定）：")
    A("")
    A("| 项 | 值 |")
    A("|---|---|")
    A(f"| `report_type.primary` | `{rt['primary']}` |")
    A(f"| `status` / `confidence` | `{rt['status']}` / `{rt['confidence']}` |")
    A(f"| 选中 skill | `{classification['selected_skill']['skill_id']}` "
      f"v{classification['selected_skill']['skill_version']}"
      f"（lifecycle=`{classification['selected_skill']['lifecycle_state']}`） |")
    A(f"| 声明备选类型 | {len(rt['declared_alternatives'])} 个，逐个给出不选理由 |")
    lv = {n: sum(1 for s in secs if s["level"] == n) for n in sorted({s["level"] for s in secs})}
    A(f"| 结构切分 | {len(secs)} 个标题段（" + " + ".join(f"h{n}×{c}" for n, c in lv.items()) + "） |")
    A(f"| 逐字证据 | {len(classification['evidence'])} 条 char-span 定位，"
      f"{len(classification['decision_basis'])} 条判断全部绑定证据 |")
    A(f"| 显式 unresolved | {len(classification['unresolved'])} 条（含两型相邻的争议点） |")
    A("")
    A(f"报告实际标题行（原文首行，证据 EV-01）：`{_cell(classification['evidence'][0]['locator']['quote'])}`；"
      f"契约 `input.title` 为 `{_cell(S.SOURCE_TITLE)}`。两者措辞不同，本包只登记差异、不改写任何一方。")
    A("")

    # ---------------- ② ----------------
    A("## ② 怎么做的（步骤 / 工具 / 关键设置）")
    A("")
    A("1. **取源**：`GET /tensor/reports/9246`（Bearer token 由 `/auth/login` 换取），只取 record 与 "
      "`markdown` 字段。本包只读这一个 report_id，脚本内 `scope_guard.report_ids_read` 只有 `9246`。")
    A(f"2. **源自证**：对 markdown 的 UTF-8 字节算 sha256，与契约 `input.source_hash` 比对；"
      f"现算 `{src['recomputed_source_hash']}`，字符数 {src['chars']}（契约 {src['declared_chars']}）。"
      "不一致则脚本以退出码 1 终止、不产出结果。")
    A("3. **信号探针**：读 `extraction-skills/registry.json` 的 `report_types`（6 类）与每个 skill 的 "
      "`identify_signals`，逐条编译成正则/派生量（citation density 用公式），统计命中次数与首次命中位置。")
    A("4. **决策规则**（打分前写定，未按结果回调）：R1 信号命中 ≥2 才合格 → R2 合格者中 registry "
      "skill 的**全部 steps 都能由原文满足**者为胜 → R3 打平看自述目的句 → R4 仍平则 `unclassified`（禁止硬猜）。")
    A("5. **逐字定位**：证据只登记「锚串」，真实 quote / 偏移 / `content_hash` 由脚本从原文切出；"
      "锚串必须在原文恰好出现一次，否则报错退出（不猜、不近似、不回述记忆）。")
    A("6. **结构切分**：按 1–6 级 ATX 标题行切段，逐段记 char/byte 偏移、行号区间与 sha256。")
    A("7. **自检**：`scripts/kf/kf9246_checks.py` 对 acceptance 逐条校验（JSON/ schema/ 哈希/ 定位/"
      " 去重/ 证据绑定/ 不标 verified/ 单 id 锁/ 唯一 json 块），结果落 `checks.json`。")
    A(f"8. **独立复核**：`scripts/kf/kf9246_verify_independent.py` 不复用 build 模块，独立重新取源、"
      f"重算哈希、回切每条 quote、复核 schema 与围栏数；回归用例 `tests/test_kf_wp9246_02.py`"
      f"（{_n_tests()} 项，离线，直接断言落盘产物的 acceptance 不变量）。")
    A("")
    A("关键设置：`min_quote_chars=12`；`report_type` 只允许 registry 6 类或 `unclassified`；"
      "`claims` 不产生（工序 02 不做抽取）。一键复跑见文末 `repro_cmd`。")
    A("")
    A("决策规则原文（`report_type.decision_trace.rule`）：")
    A("")
    A("| 规则 | 内容 |")
    A("|---|---|")
    for k, v in S.DECISION_RULE.items():
        A(f"| {k} | {_cell(v)} |")
    A("")
    A(f"本次实际使用：`{S.DECISION_RULE['used_in_this_package']}`"
      f"（R3_triggered={rt['decision_trace']['R3_triggered']}）。")
    A("")

    # ---------------- ③ ----------------
    A("## ③ 产出物清单（数字由脚本注入）")
    A("")
    A("| 文件 | 要点 |")
    A("|---|---|")
    A(f"| `docs/production/{S.PACKAGE_ID}/KF-RESULT-{S.PACKAGE_ID}.md` | 本报告（六段 + 唯一 json 块） |")
    A(f"| `docs/production/{S.PACKAGE_ID}/kf_result.json` | 结果信封（`schemas/kf_result.v1.schema.json` 校验通过） |")
    A(f"| `docs/production/{S.PACKAGE_ID}/classification.json` | 分类/结构/证据/unresolved 全部内容（信封 `outputs` 同一对象） |")
    A(f"| `docs/production/{S.PACKAGE_ID}/checks.json` | {len(checks['checks'])} 项自检逐条结果 |")
    A(f"| `docs/production/{S.PACKAGE_ID}/figures/classification_decision.png` | 判定输入可视化（信号命中矩阵 + step-fit） |")
    A(f"| `artifacts/{S.PACKAGE_ID}/` | 镜像：同上 JSON + 图 + `source_markdown.md`（取源快照，便于离线复算） |")
    A("")
    A("**信号命中（registry identify_signals × 6 类候选）**，右列 `hits/total`：")
    A("")
    A("| 候选类型 | 命中/总数 | 逐条信号 |")
    A("|---|---|---|")
    for t, row in sig.items():
        detail = "；".join(
            f"{s['signal']}={'hit' if s['hit'] else 'miss'}"
            + (f"({s['count']})" if s["kind"] == "regex" else f"(derived={s.get('value')})")
            for s in row["signals"])
        A(f"| `{t}` | {row['hits']}/{row['total']} | {_cell(detail)} |")
    A("")
    A("**step-fit（registry skill 的 steps 是否可由原文满足）**：")
    A("")
    A("| 候选类型 | 可满足/已评 | 逐 step |")
    A("|---|---|---|")
    for t, row in sf.items():
        detail = "；".join(f"{s['step_id']}={s['verdict']}" for s in row["steps"])
        A(f"| `{t}` | {row['satisfiable']}/{row['evaluated']} | {_cell(detail)} |")
    A("")
    A("**结构切分（标题段，偏移为 markdown 字符下标）**：")
    A("")
    A("| # | 级别 | 标题 | 行 | 字符区间 | chars |")
    A("|---|---|---|---|---|---|")
    for s in secs:
        A(f"| {s['index']} | h{s['level']} | {_cell(s['title'])} | "
          f"{s['line_start']}–{s['line_end']} | {s['start_offset']}–{s['end_offset']} | {s['chars']} |")
    A("")
    A("**选中 skill 的章节映射**：")
    A("")
    A("| skill.applies_to.sections | 命中的报告章节 | 状态 |")
    A("|---|---|---|")
    for m in classification["selected_skill"]["section_mapping"]:
        A(f"| {m['skill_section']} | {_cell(', '.join(m['matched_report_sections'])) or '—'} | {m['status']} |")
    A("")
    A("**自检探针（量级复算，不改报告结论）**：原文称 ε=0.8 处 Gidaspow 分支切换有 "
      f"{probe['report_claim_percent']:.0f}% 拖曳系数跳变。用原文 §2 逐字分支公式 + 原文自身参数"
      f"（μ={probe['inputs']['mu']} Pa·s、ρ_f={probe['inputs']['rho_f']} kg/m³、"
      f"d={probe['inputs']['d']} m、ε={probe['inputs']['epsilon']}）复算，两种 Re 约定都算"
      f"（原文写 `C_D(εRe)` 但未定义 Re）：")
    A("")
    A("| u [m/s] | c_Ergun | c_WenYu (Re 约定 A) | c_WenYu (Re 约定 B) | 跳变 A | 跳变 B |")
    A("|---|---|---|---|---|---|")
    for c in probe["cases"]:
        A(f"| {c['u']:.3g} | {c['c_ergun']:.6g} | {c['c_wenyu_A']:.6g} | {c['c_wenyu_B']:.6g} | "
          f"{c['jump_A_percent']:.2f}% | {c['jump_B_percent']:.2f}% |")
    A("")
    A(f"u ∈ [{probe['sweep']['u_min']:g}, {probe['sweep']['u_max']:g}] 取 {probe['sweep']['samples']} 点扫描："
      f"|跳变| ∈ [{probe['sweep']['abs_jump_min_percent']:.2f}%, "
      f"{probe['sweep']['abs_jump_max_percent']:.2f}%]，"
      f"是否覆盖原文的 {probe['report_claim_percent']:.0f}% = {probe['report_claim_inside_probe_range']}"
      f"（status=`{probe['status']}`）。")
    A("")
    A(f"读法：{_cell(probe['implication'])}")
    A("")
    A("**图**：`figures/classification_decision.png`（左：信号命中矩阵；右：命中数与 step-fit 比例，"
      "红色虚线为 R1 门槛 2）。说明：本工序是文档分类/解析，无场量可画云图，"
      "故给判定输入的可复核视图，而不是物理结果图。")
    A("")

    # ---------------- ④ ----------------
    A("## ④ 证据定位表（字段 → 原文逐字片段）")
    A("")
    A("所有 quote 由脚本从原文切出，`start_offset`/`end_offset` 为 markdown 字符下标，"
      "`content_hash` 是 quote 的 sha256；下表行号指 markdown 行号。")
    A("")
    A("| 证据 | 归属字段 | 行 | 原文逐字片段 |")
    A("|---|---|---|---|")
    for e in classification["evidence"]:
        loc = e["locator"]
        A(f"| {e['id']} | {_cell(e['field'])} | {loc['line_start']} | {_cell(loc['quote'])} |")
    A("")
    A("**判断 → 证据绑定（decision_basis）**：")
    A("")
    A("| 判断 | 绑定证据 | 陈述 |")
    A("|---|---|---|")
    for d in classification["decision_basis"]:
        A(f"| {d['id']} | {', '.join(d['evidence'])} | {_cell(d['statement'])} |")
    A("")
    A("**显式 unresolved**：")
    A("")
    A("| id | 问题 | 原因 | 建议处理 |")
    A("|---|---|---|---|")
    for u in classification["unresolved"]:
        A(f"| {u['id']} | {_cell(u['question'])} | {_cell(u['reason'])} | {_cell(u['suggested_handler'])} |")
    A("")

    # ---------------- ⑤ ----------------
    A("## ⑤ 注意点与局限")
    A("")
    ev = sig
    A(f"1. **主/备两型信号打平**：`scientific-computation` 与 `experimental-validation` 各命中 "
      f"{ev['scientific-computation']['hits']}/5 与 {ev['experimental-validation']['hits']}/5，"
      "胜负完全由事先声明的 R2（step-fit：`extract-uncertainty` 需逐字不确定度+包含因子，原文没有）决定。"
      "审核者若认为「数值误差来源」等价于不确定度声明，本结论应被复议（UR-01/UR-02）。")
    A("2. **探针是语义近似，不是原文元数据**：信号命中来自我按 registry 语义写的正则，"
      "命中计数可复核，但「正则是否等价于 registry 语义」本身需 04 审核判断。"
      "缺信号的证据只能是「探针 0 命中」，无法逐字引用「原文没有写 X」。")
    A("3. **skill 仍是 template-created**：`registry.note` 明示尚无真实代表性报告走通全链；"
      "本包只登记「选中」，不宣称该 skill 已被验证有效。")
    A("4. **标题措辞不一致**：平台 record 标题用「-」，原文标题行用「Minimum Verifiable Unit」表述；"
      "信封 `provenance.title` 抄契约值，原文标题另以 EV-01 定位，二者不混用。")
    A("5. **不做的事**：不抽 claim、不评估六个判据是否成立、不复算报告数值（除 ③ 末的跳变量级探针）、"
      "不把任何结论标 verified（verification 由平台门计算）。")
    A("6. **边界**：只读/只写 report_id=9246；未改上游 01 包与其它工作包产物；`claims` 为空是契约允许的完整结果。")
    A("")

    # ---------------- ⑥ ----------------
    A("## ⑥ 自检（逐条对照 acceptance）")
    A("")
    A("| acceptance | 结果 | 证据摘要 |")
    A("|---|---|---|")
    for c in checks["checks"]:
        mark = "✓" if c["status"] == "passed" else "✗ FAIL"
        evd = c["evidence"]
        summary = {k: evd[k] for k in list(evd)[:4]}
        A(f"| `{c['check'].split('.', 1)[1]}` | {mark} | `{_cell(json.dumps(summary, ensure_ascii=False))}` |")
    A("")
    A(f"总体：`checks.ok = {checks['ok']}`（{sum(1 for c in checks['checks'] if c['status'] == 'passed')}"
      f"/{len(checks['checks'])} 项 passed）。失败项如实列出，未粉饰。")
    A("")
    A("**honest-FAIL 与不适用声明**：")
    A("")
    A("- `all_claims_have_evidence_or_explicit_unresolved_status`：本工序**不产生 claims**，"
      "该项按「本包每条判断都绑定逐字证据或显式 unresolved」执行并校验为 passed；"
      "若下游理解为本包必须产 claim，则该理解与契约 notes「不做抽取」冲突——此点如实登记为口径差异，不予敷衍。")
    A("- 无独立的 A9 之外的外部校验：平台门会独立重算 sha256 与子串定位，本报告的 `checks.json` 是自检，不是平台裁定。")
    A("")

    A("## repro_cmd")
    A("")
    A("命令（复制即跑；正文不另开代码围栏，保证全文只有唯一一个 json 代码块）：")
    A("")
    A("    # 工作树根 = 仓库检出；需 TENSOR_AGENT_USER / TENSOR_AGENT_PASS / TENSOR_API_BASE")
    A("    python3 scripts/kf/kf9246_build.py               # 取源+构造+自检+出图+出报告")
    A("    python3 scripts/kf/kf9246_build.py --check-only  # 只重跑自检（读已落盘信封）")
    A("    cat docs/production/wp-9246-02/checks.json")
    A("")
    A("## 结果信封（唯一一个 json 代码块，原样提交）")
    A("")
    A("```json")
    A(json.dumps(result, ensure_ascii=False, indent=2))
    A("```")
    A("")
    return "\n".join(L)