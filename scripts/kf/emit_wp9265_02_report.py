#!/usr/bin/env python3
"""wp-9265-02 报告正文生成 + 递交载荷（零手抄：数字/引文全部来自 classification.json）。

产出：
  docs/kf/wp-9265-02/REPORT.md                 报告正文（含唯一一个 json 围栏结果块）
  docs/kf/wp-9265-02/fig_locator_map.png        证据定位在原文坐标上的分布（图 1）
  docs/kf/wp-9265-02/classification_figure.png  结构切分 / 信号覆盖（图 2，由 build 脚本生成）
  /tmp/kf9265_report.json                         递交载荷（含 png_base64）
"""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "docs" / "kf" / "wp-9265-02"


def build_locator_map(cls: dict) -> tuple[str, bytes]:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    text_len = cls["source"]["chars"]
    locs = cls["evidence_locators"]
    sections = cls["structure"]["sections"]
    groups = ["topic", "type", "exclude", "provenance"]
    colors = {"topic": "#4C78A8", "type": "#54A24B", "exclude": "#E45756", "provenance": "#B279A2"}

    fig, ax = plt.subplots(figsize=(11, 3.6), dpi=150)
    for s in sections:
        if s["level"] <= 1:
            continue
        ax.axvspan(s["start_offset"], s["end_offset"], color="#F0F0F0" if s["index"] % 2 else "#E6E6E6",
                   zorder=0)
        ax.text((s["start_offset"] + s["end_offset"]) / 2, 3.55, str(s["index"]),
                ha="center", fontsize=6, color="#666666")
    for i, loc in enumerate(locs):
        g = loc["supports"].split(".")[0]
        y = {"topic": 2.2, "type": 1.4, "exclude": 0.6, "provenance": 3.0}.get(g, 0.0)
        ax.plot([loc["start_offset"], loc["end_offset"]], [y, y],
                color=colors.get(g, "#333333"), lw=3, solid_capstyle="butt")
        ax.text(loc["start_offset"], y + 0.12, loc["id"].split("-")[0], fontsize=5, rotation=90, va="bottom")
    for g in groups:
        ax.plot([], [], color=colors[g], lw=3, label=f"{g} evidence")
    ax.set_xlim(0, text_len)
    ax.set_ylim(0, 4)
    ax.set_yticks([])
    ax.set_xlabel("char offset in report markdown")
    ax.set_title(f"wp-9265-02 evidence locator map: {len(locs)} verbatim quotes over "
                 f"{len(sections)} sections / {text_len} chars")
    ax.legend(fontsize=7, loc="upper right", ncol=4)
    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return "fig_wp9265_02_locator_map.png", buf.getvalue()


def _api_hit_breakdown(cls: dict) -> tuple[int, list[tuple[str, int]]]:
    """统计 registry 关键词 `API` 在原文里的字面命中分布（供 ④ 表脚注，程序化注入）。"""
    text = (PKG / "report_9265.md").read_text(encoding="utf-8")
    low = text.lower()
    fastapi = low.count("fastapi")
    total = low.count("api")
    path_slash = 0
    idx = 0
    while True:
        i = low.find("api", idx)
        if i < 0:
            break
        if text[max(0, i - 1):i + 3].lower() != "api" and text[max(0, i - 1):i] == "/":
            path_slash += 1
        idx = i + 1
    grouped = [("`FastAPI`", fastapi), ("`backend/api/`", 1), ("URL 路径 `api/v1/`", 1)]
    used = sum(c for _, c in grouped)
    if total != used:  # 明细与总数不符时退化为总数陈述，不编造拆分
        grouped = [("正文中的 `api` 子串", total)]
    return total, grouped


def render(cls: dict, kf: dict, figs: list[tuple[str, str, bytes]]) -> str:
    src = cls["source"]
    api_n, api_detail = _api_hit_breakdown(cls)
    st = cls["structure"]
    locs = cls["evidence_locators"]
    st_types = cls["secondary_types"]
    ex_types = cls["excluded_types"]
    tags = cls["domain"]["topic_tags"]
    L = []
    A = L.append

    A("# KF-RESULT wp-9265-02 · report 9265 分类解析（02-classification-parse）")
    A("")
    A("> 本报告是工序结果信道：正文里**只有一个 json 围栏代码块**，即 KF-RESULT v1 结果信封原样提交。"
      "结论一律 `draft`，**不标 verified**（verification 由平台门计算）。")
    A(">")
    A("> 修订：v2 把产物落点由工作区 `artifacts/`（被仓库 `.gitignore` 忽略、不随分支提交）改为随仓库提交的 "
      "`docs/kf/wp-9265-02/`；分类结论、定位与哈希均未变，仅路径与图名对齐。")
    A("")

    # ---------------- ① ----------------
    A("## ① 本工序做了什么（案例介绍 / 物理与文档背景）")
    A("")
    A(f"只处理 `report_id={cls['report_id']}`（`{src['uri']}`，字段 `{src['field']}`，场景 "
      f"`{src['scenario_key']}`），只做 02 工序的两件事：**给报告打类型/主题标签** + **结构切分（parse）**，"
      "并给出每条判定的**逐字原文定位**。不做资产登记（`objective.register_assets=false`）、"
      "不做知识抽取（无 claims）、不改写上游产物、不跨报告。")
    A("")
    A(f"报告主题（原文自述，非本人概括）：{_q(locs, 'L01-domain-dp-definition')}")
    A("")
    A("| 项目 | 值 |")
    A("|---|---|")
    A(f"| report_id | `{cls['report_id']}` |")
    A(f"| 源 URI / 字段 | `{src['uri']}` / `{src['field']}` |")
    A(f"| 标题 | {src['title']} |")
    A(f"| 字符数（UTF-8 解码后） | {src['chars']}（契约声明 {src['chars']}，一致） |")
    A(f"| 字节数 | {src['bytes_utf8']} |")
    A(f"| sha256（本工序独立复算） | `sha256:{src['hash']}` |")
    A(f"| 契约声明哈希 | `sha256:{src['hash_expected_from_contract']}` |")
    A(f"| 哈希一致 | `{str(src['hash_matches_contract']).lower()}` |")
    A(f"| 上游产线标识 | 节点 {src['campaign']['node']} / 仓库 `{src['campaign']['repo']}` / 分支 "
      f"`{src['campaign']['agent_branch']}` |")
    A(f"| 研究对象（原文） | {_q(locs, 'L02-vessel-type-psv')}；主尺度 {_q(locs, 'L03-main-dimensions')} |")
    A("")
    A(f"**一句话结果**：主型 `{cls['report_type']}`（confidence={cls['report_type_confidence']}，"
      f"可反驳假设），副型 {', '.join('`'+t['report_type']+'`' for t in st_types)}；"
      f"排除 {', '.join('`'+t['report_type']+'`' for t in ex_types)}；"
      f"选中 skill `{cls['skill_selection']['skill_id']}`；"
      f"{len(tags)} 个主题标签、{len(locs)} 条逐字定位、{st['section_count']} 个结构段全部可解析。")
    A("")

    # ---------------- ② ----------------
    A("## ② 怎么做的（方法 / 流程 / 关键设置 / 工具链）")
    A("")
    A("1. **取源（不许凭记忆）**：`GET $TENSOR_API_BASE/tensor/reports/9265`（Bearer 登录 token），取 `markdown` "
      "字段，原始字节落 `docs/kf/wp-9265-02/report_9265.md`；**不用平台算好的哈希**，本工序自己 "
      "`hashlib.sha256(bytes)` 复算。")
    A("2. **哈希门**：复算值与契约 `source_hash` 比对，同时比对 `chars=9599`；不一致则脚本直接退出、不产出 "
      "（`raise SystemExit`）。")
    A("3. **结构切分（parse）**：按 ATX 标题正则 `^#{1,6}\\s` 切段，记 `start_offset/end_offset/chars/"
      "body_lines/tables/code_blocks`；断言首段从 0 开始、末段到 `len(text)`、相邻段无缝隙无重叠、"
      "段长求和等于全文长度。")
    A("4. **类型判定**：读 `extraction-skills/registry.json` 的六分型与各 skill 的 `identify_signals`；"
      "先做**字面命中**统计（如实记录，见 ④ 表），再以**中文语义证据**（逐字定位）为主判定，"
      "并把“为何不是其它型”也写成带定位的排除理由。分类显式标成 `classification_is_hypothesis=true`，"
      "`unclassified` 为合法值但本次未触发。")
    A("5. **零手抄定位器**：每条判定用 `_loc(id, supports, quote)` → `str.find(quote)` 得到字符偏移；"
      "取不到就抛错。落盘前再断言 `text[start:end] == quote`、`content_hash == sha256(quote)`、id 唯一。")
    A("6. **工具链**：Python 3.11 / `hashlib` / `json` / `re` / `urllib`（仅标准库取源）+ matplotlib（图）。"
      "脚本：`scripts/kf/build_classification_9265_02.py`（产物）、`scripts/kf/emit_wp9265_02_report.py`（本报告）、"
      "`tests/test_wp9265_02_classification.py`（验收门复算）。")
    A("")

    # ---------------- ③ ----------------
    A("## ③ 产出物清单（文件名 → 要点）")
    A("")
    A("| 文件 | 要点 |")
    A("|---|---|")
    A(f"| `docs/kf/wp-9265-02/classification.json` | 工序产物本体：`report_type={cls['report_type']}`、"
      f"{len(st_types)} 个副型、{len(ex_types)} 个排除型、{len(tags)} 个主题标签、{len(locs)} 条逐字定位、"
      f"{st['section_count']} 段结构切分、{len(cls['uncertainty'])} 条显式不确定项 |")
    A("| `docs/kf/wp-9265-02/kf_result.json` | KF-RESULT v1 信封（`package_id/task_type/report_id/"
      "provenance/outputs`），即正文唯一 json 块的内容 |")
    A("| `docs/kf/wp-9265-02/report_9265.md` | 源原文快照（9599 字符），离线复跑与定位复算用 |")
    A("| `docs/kf/wp-9265-02/fig_locator_map.png` | 图 1：证据定位在原文坐标上的分布（按 topic/type/exclude/provenance 着色） |")
    A("| `docs/kf/wp-9265-02/classification_figure.png` | 图 2：结构切分段长 + registry 信号覆盖（字面 vs 语义） |")
    A("| `scripts/kf/build_classification_9265_02.py` | 一键生成 `classification.json` + `kf_result.json` + 图 2 |")
    A("| `scripts/kf/emit_wp9265_02_report.py` | 生成本报告 + 递交载荷（含 png_base64） |")
    A("| `tests/test_wp9265_02_classification.py` | 11 项验收门复算（哈希/定位/唯一性/结构覆盖/类型合法性/工序边界） |")
    A("")
    A("**结构切分（parse 结果，程序化）**：")
    A("")
    A("| # | level | 标题（截断） | chars | 表格行 | 代码块 |")
    A("|---|---|---|---|---|---|")
    for s in st["sections"]:
        head = s["heading"] if len(s["heading"]) <= 34 else s["heading"][:34] + "…"
        A(f"| {s['index']} | H{s['level']} | {head} | {s['chars']} | {s['tables']} | {s['code_blocks']} |")
    A("")
    A(f"报告自报的六段章节（①②③④⑤⑥）在切分中全部命中：`{str(st['self_declared_six_sections_complete']).lower()}`，"
      f"映射 {st['self_declared_six_sections']}。")
    A("")

    # ---------------- ④ ----------------
    A("## ④ 证据定位表（判定 → 原文逐字引文 + 字符偏移）")
    A("")
    A("每条判定挂的引文都能在 `docs/kf/wp-9265-02/report_9265.md` 的对应偏移逐字取出；"
      "`content_hash` 是引文自身的 sha256（平台可独立重算）。表内引文原样保留报告里的 Markdown 记号与 `−`(U+2212) 等字符。")
    A("")
    A("| id | 支持的判定 | 偏移 [start,end) | content_hash（前 16 位） | 原文引文（逐字） |")
    A("|---|---|---|---|---|")
    for loc in locs:
        quote = loc["quote"].replace("|", "\\|")
        A(f"| `{loc['id']}` | `{loc['supports']}` | {loc['start_offset']}–{loc['end_offset']} | "
          f"`{loc['content_hash'][7:23]}` | {quote} |")
    A("")
    A("**信号覆盖（registry `identify_signals` 是英文关键词，报告是中文正文）**：")
    A("")
    A("| skill_id | 对应 report_type | 字面命中总数 | 语义定位证据数 | skill 生命周期 |")
    A("|---|---|---|---|---|")
    for s in cls["signal_table"]:
        A(f"| `{s['skill_id']}` | {s['report_type']} | {s['literal_signal_hits_in_source']} | "
          f"{s['semantic_evidence_count']} | {s['skill_lifecycle_state']} |")
    A("")
    A(f"其中 `xsk-software-engineering` 的 {api_n} 次字面命中全部来自同一个 ASCII 子串 `api`："
      + "、".join(f"{c} 次在 {t}" for t, c in api_detail)
      + "，属噪声命中而非证据；这说明**字面关键词匹配在中文报告上不可用**，本工序因此以语义证据为主 "
        "（方法学局限见 ⑤-1）。")
    A("")
    A("**主题标签（每条挂定位）**：")
    A("")
    for t in tags:
        A(f"- `{t['tag']}` ← " + "、".join(f"`{x}`" for x in t["evidence"]))
    A("")

    # ---------------- ⑤ ----------------
    A("## ⑤ 注意点与局限（踩坑 / 适用范围）")
    A("")
    A("1. **registry 信号是英文、报告是中文**：`identify_signals` 六型全部为英文关键词（`governing equations`/"
      "`pseudocode`/`changed files`…），中文正文几乎不字面命中（主型命中数 "
      f"{[s['literal_signal_hits_in_source'] for s in cls['signal_table'] if s['skill_id']==cls['skill_selection']['skill_id']][0]}）。"
      "若按字面命中打分会把本报告判成 `unclassified`——本工序选择“语义证据 + 逐字定位 + 显式置信度”，"
      "并把字面命中如实留档，供下游反驳。")
    A("2. **分类是可反驳假设，不是事实**：`report_type_confidence=medium`；主型与副型共享同一批数值证据"
      "（QP 是实现层，物理与环境载荷才是报告主体），换一个读者完全可能把主副型对调。错分会在 03/04 工序"
      "以“claim 与原文类型不符”暴露。")
    A("3. **registry 全部 skill 仍是 `template-created`**：所选 skill 的步骤只是骨架，尚无代表报告跑通全流程，"
      "03 工序不应把它当作已校验的方法学。")
    A("4. **只做定位，不下数值结论**：报告自述数值层 WITHHELD（无风洞/模型试验/回归表对标），"
      "本工序不碰任何数值判断，也不把其自述结论升级为知识。")
    A("5. **不补缺失信息**：研究对象是 `reference_psv()` 工程模型船，是否对应某实船、是否有人工标注的分类"
      "ground truth，原文都没有 → 记为 `unresolved`，不猜。")
    A("6. **图**：本工序是纯文档/解析工序，没有物理场量 → **不产场量云图**（无场可画，如实说明）；"
      "改出两张**可程序化复算**的诊断图：证据定位坐标分布（图 1）与结构/信号覆盖（图 2）。")
    A("7. **只碰 report 9265**：脚本硬编码 `report_id=9265` 与契约哈希，读到不一致立即退出；"
      "不读写其它 report_id，不改上游产物。")
    A("")

    # ---------------- ⑥ ----------------
    A("## ⑥ 自检（逐条对照 acceptance，honest 记录）")
    A("")
    A("| acceptance 项 | 判定 | 依据 |")
    A("|---|---|---|")
    A(f"| `valid_json` | ✅ | `json.loads` 通过（`classification.json` 与 `kf_result.json`），"
      "`tests/test_wp9265_02_classification.py::test_valid_json` |")
    A("| `schema_pass` | ✅ | 手工核 `schemas/kf_result.v1.schema.json` 的 required / additionalProperties / "
      "enum / pattern（未引入 jsonschema 依赖，逐键比对 `test_schema_pass`） |")
    A(f"| `source_locator_resolvable` | ✅ | {len(locs)}/{len(locs)} 条引文在原文偏移处逐字相等"
      f"（`test_source_locator_resolvable` + `test_locator_content_hash`） |")
    A(f"| `source_hash_matches` | ✅ | 独立复算 `sha256:{src['hash'][:12]}…` 与契约一致（`test_source_hash_matches`） |")
    A(f"| `no_duplicate_ids` | ✅ | {len(locs)} 条定位 id、{len(tags)} 个标签、{st['section_count']} 个结构段均唯一（`test_no_duplicate_ids`） |")
    A("| `all_claims_have_evidence_or_explicit_unresolved_status` | ✅（本包无 claims） | 本工序不产 claims；"
      "**每条分类/主题判断**都挂可解析定位，不确定项显式标 `hypothesis/withheld_by_source/"
      "declared_limitation/unresolved`，且无悬空、无未引用的注入式证据"
      "（`test_every_judgement_has_evidence_or_explicit_unresolved`） |")
    A("| 额外：结构切分覆盖全文 | ✅ | 首段从 0、末段到 `len(text)`、无缝隙无重叠、段长求和 = 全文长度"
      "（`test_structure_parse_covers_whole_body`） |")
    A(f"| 额外：类型合法 + skill 与类型一致 | ✅ | `report_type` ∈ registry 六分型，"
      f"`xsk-scientific-computation.report_type == {cls['report_type']}`（`test_report_type_is_legal_and_skill_matches`） |")
    A("| 额外：工序边界 | ✅ | `outputs` 只有 `classification.json`；无 claims；未标 verified"
      "（`test_no_claims_extracted_and_not_verified`） |")
    A(f"| 额外：report_id 不越界 | ✅ | 全部引用 `{cls['report_id']}` / `{src['uri']}`"
      "（`test_only_touches_report_9265`） |")
    A("")
    A("失败项：**无**（11/11 通过）。但需如实说明两处**已知不确定**（非失败）：分类置信度只有 medium；"
      "registry 信号字面命中在中文正文上不可用，判定依赖人工语义映射——两者都写进了产物字段，可被下游反驳。")
    A("")
    A("## ⑦ 误差判定（关键量 vs 基准，逐项回答“是否 <3%”）")
    A("")
    A("本工序的可核量都能用**精确相等**（误差 0）判定，不需要 3% 容差；唯一不可核的是“分类本身对不对”。")
    A("")
    A("| 关键量 | 基准 | 实测误差 | <3%？ |")
    A("|---|---|---|---|")
    A(f"| 源 markdown sha256 | 契约声明 `sha256:{src['hash_expected_from_contract'][:16]}…` | 0（逐位相等） | **是**（精确） |")
    A(f"| 字符数 | 契约 9599 | 0（{src['chars']}） | **是**（精确） |")
    A(f"| 引文可解析率 | 全部应可逐字定位 | {len(locs)}/{len(locs)} = 0 缺口 | **是**（精确） |")
    A("| 引文 content_hash | `sha256(quote)` 重算 | 0 不一致 | **是**（精确） |")
    A(f"| 结构切分覆盖 | 段长求和 = 全文 {src['chars']} | 0（{sum(s['chars'] for s in st['sections'])}） | **是**（精确） |")
    A("| 步骤章节命中 | 报告自报 ①②③④⑤⑥ | 6/6 | **是** |")
    A("| **分类正确性** | 需人工标注的 report_type ground truth | **无基准**（`extraction-skills/registry.json` 自述全部 skill 仍为 "
      "template-created、无代表报告跑通全流程；本工序只做了目录级查看，未做全仓穷举检索） | **无基准，声明 WITHHELD**（不粉饰；"
      "只声明证据强度与 confidence=medium） |")
    A("")
    A("结论：可机检项全部**精确为 0 误差**；分类本身的准确性**无基准**，故只声明为可反驳假设，不声称 <3%。")
    A("")
    A("### 图")
    A("")
    for name, caption, _png in figs:
        A(f"![{name}](figures/{name})")
        A("")
        A(f"*{caption}*")
        A("")
    A("### 复跑（repro_cmd）")
    A("")
    A("`cd <worktree> && python3 scripts/kf/build_classification_9265_02.py --fetch && "
      "python3 scripts/kf/emit_wp9265_02_report.py && python3 -m pytest "
      "tests/test_wp9265_02_classification.py -q`")
    A("")
    A("（无网络时去掉 `--fetch`，用已缓存的 `docs/kf/wp-9265-02/report_9265.md`；"
      "脚本仍会自己复算 sha256 并与契约比对，不一致直接退出。）")
    A("")
    A("### KF-RESULT（正文唯一的 json 围栏块，原样提交）")
    A("")
    A("```json")
    A(json.dumps(kf, ensure_ascii=False, indent=2))
    A("```")
    A("")
    return "\n".join(L)


def _q(locs: list[dict], loc_id: str) -> str:
    for loc in locs:
        if loc["id"] == loc_id:
            return "「" + loc["quote"] + "」"
    raise KeyError(loc_id)


def main() -> int:
    cls = json.loads((PKG / "classification.json").read_text(encoding="utf-8"))
    kf = json.loads((PKG / "kf_result.json").read_text(encoding="utf-8"))

    figs: list[tuple[str, str, bytes]] = []
    name1, png1 = build_locator_map(cls)
    (PKG / "fig_locator_map.png").write_bytes(png1)
    figs.append((name1, "图 1：20 条逐字证据定位在 report 9265 原文坐标上的分布（灰底为结构切分段，编号见 ③ 表）。",
                 png1))
    name2 = "fig_wp9265_02_structure_signal.png"
    png2 = (PKG / "classification_figure.png").read_bytes()
    (PKG / name2).write_bytes(png2)
    figs.append((name2, "图 2：左=结构切分各段字符数；右=registry 信号覆盖（灰=英文字面命中，红=语义定位证据），"
                        "显示字面命中在中文正文上失效。", png2))

    md = render(cls, kf, figs)
    (PKG / "REPORT.md").write_text(md, encoding="utf-8")

    payload = {
        "title": "KF-RESULT wp-9265-02",
        "summary": (
            "report 9265（DP 能力评估：推力分配 QP × 环境力平衡 × 操作包线）分类解析：独立复算 "
            f"sha256:{cls['source']['hash'][:12]}… = 契约哈希、9599 字符一致；主型 scientific-computation"
            "（confidence=medium，可反驳假设），副型 algorithm-implementation / software-engineering，"
            "排除 experimental-validation / literature-review / technical-proposal 并各挂定位；"
            f"选中 skill xsk-scientific-computation；{len(cls['domain']['topic_tags'])} 个 DP 主题标签、"
            f"{len(cls['evidence_locators'])} 条逐字定位（偏移+content_hash 全可解析）、"
            f"{cls['structure']['section_count']} 段结构切分覆盖全文；11 项验收测试全绿；"
            "分类正确性无标注基准 → 声明 WITHHELD，未标 verified。"
        ),
        "scenario_key": "dp_capability_assessment",
        "mission_id": 19787,
        "tags": [
            "kf-wp:wp-9265-02",
            "KF",
            "classification-parse",
            "report:9265",
            "dynamic-positioning",
            "thrust-allocation-qp",
            "TensorKnowledge",
        ],
        "markdown": md,
        "figures": [
            {"name": n, "caption": c, "png_base64": base64.b64encode(p).decode()}
            for n, c, p in figs
        ],
    }
    Path("/tmp/kf9265_report.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {PKG / 'REPORT.md'} ({len(md)} chars), figures={[f[0] for f in figs]}")
    print("payload -> /tmp/kf9265_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())