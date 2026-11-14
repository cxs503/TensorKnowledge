#!/usr/bin/env python3
"""Emit the `KF-RESULT wp-14445-02` report (markdown + platform payload).

Every number and quote inside the report is injected from
``docs/wp-14445-02/classification.json`` / ``kf_result_wp-14445-02.json`` at
render time — nothing is retyped, so the report cannot drift from the artifact.

Outputs
  reports/KF-RESULT-wp-14445-02.md                              report body (one ```json block)
  figures/wp-14445-02/fig_wp14445_02_classification.png          figure ④
  /tmp/report_wp-14445-02.json                                  POST /tensor/reports payload
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ID = "wp-14445-02"
CLASSIFICATION = REPO_ROOT / "docs" / PACKAGE_ID / "classification.json"
ENVELOPE = REPO_ROOT / f"kf_result_{PACKAGE_ID}.json"
SOURCE_COPY = REPO_ROOT / "docs" / PACKAGE_ID / "source" / "14445.markdown"
FIG_DIR = REPO_ROOT / "figures" / PACKAGE_ID
REPORT_MD = REPO_ROOT / "reports" / f"KF-RESULT-{PACKAGE_ID}.md"
PAYLOAD = Path(f"/tmp/report_{PACKAGE_ID}.json")  # never /tmp/report.json: shared /tmp collides across lanes
MISSION_ID = 19807
SCENARIO_KEY = "gap_pp5_cpu_baseline"

KIND_COLOR = {
    "contract_section_zh": "#2b6cb0",
    "appendix": "#805ad5",
    "appendix_section_en": "#38a169",
}


def make_figure(cls: dict, fig_path: Path) -> tuple[str, str]:
    secs = cls["structure"]["sections"]
    rows = cls["signals"]["per_skill"]
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(13.0, 4.6))

    for sec in secs:
        y = sec["level"]
        ax0.barh(
            y,
            sec["chars"],
            left=sec["start_char"],
            height=0.55,
            color=KIND_COLOR.get(sec["kind"], "#a0aec0"),
            edgecolor="white",
        )
    ax0.set_yticks([1, 2, 3])
    ax0.set_yticklabels(["# H1", "## H2", "### H3"])
    ax0.set_xlabel("character offset in source markdown")
    ax0.set_title(
        "① structure segmentation: %d headings, %d chars"
        % (len(secs), cls["source"]["chars"])
    )
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=c)
        for c in KIND_COLOR.values()
    ]
    ax0.legend(
        handles,
        list(KIND_COLOR),
        loc="lower right",
        fontsize=7.5,
        title="section kind",
    )
    ax0.invert_yaxis()

    names = [r["report_type"] for r in rows]
    lit = [r["signals_matched"] for r in rows]
    sem = [
        sum(1 for m in cls["signals"]["semantic_signal_map"] if m["report_type"] == n)
        for n in names
    ]
    idx = range(len(names))
    ax1.barh([i - 0.2 for i in idx], lit, height=0.38, color="#c53030", label="literal registry hits")
    ax1.barh([i + 0.2 for i in idx], sem, height=0.38, color="#2f855a", label="semantic mapping")
    ax1.set_yticks(list(idx))
    ax1.set_yticklabels(names, fontsize=8.5)
    ax1.set_xlabel("matched identify_signals")
    ax1.set_title(
        "② six-type signal evidence — primary=%s" % cls["report_type"]["primary"]
    )
    ax1.legend(fontsize=8)
    ax1.grid(axis="x", alpha=0.3)
    ax1.invert_yaxis()

    fig.suptitle(
        "wp-14445-02 classification parse — report 14445 (source sha256 %s…)"
        % cls["source"]["hash"][:12],
        fontsize=10,
    )
    fig.tight_layout()
    fig_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fig_path, dpi=150)
    plt.close(fig)
    caption = (
        "左：源报告结构切分（%d 个标题、按字符偏移落位；蓝=①–⑥ 中文正题、紫=附录标题、绿=英文 §1–§7）；"
        "右：六分型 identify_signals 命中（红=registry 字面命中、绿=语义映射命中），"
        "primary 判定为 %s。" % (len(secs), cls["report_type"]["primary"])
    )
    return fig_path.name, caption


def evidence_rows(cls: dict) -> list[tuple[str, str, str, str, str]]:
    """(id, kind, char span, line span, quote) — all straight from the artifact."""
    groups = [
        ("type", cls["evidence_for_classification"]),
        ("topic", cls["topic_locators"]),
    ]
    notes = {lid for n in cls["parse_notes"] for lid in n["locator_ids"]}
    disc = [rec for rec in cls["parse_note_locators"]]
    rows = []
    for kind, recs in groups:
        for rec in recs:
            rows.append(
                (
                    rec["locator_id"],
                    kind,
                    "%d–%d" % (rec["start_char"], rec["end_char"]),
                    "%d" % rec["start_line"],
                    rec["quote"],
                )
            )
    for rec in disc:
        rows.append(
            (
                rec["locator_id"],
                "parse-note",
                "%d–%d" % (rec["start_char"], rec["end_char"]),
                "%d" % rec["start_line"],
                rec["quote"],
            )
        )
    assert notes <= {r[0] for r in rows}, "a parse note points at a missing locator"
    return rows


def build_markdown(cls: dict, envelope: dict, fig_name: str, fig_caption: str) -> str:
    src = cls["source"]
    rows = evidence_rows(cls)
    per_skill = cls["signals"]["per_skill"]
    secs = cls["structure"]["sections"]
    notes = cls["parse_notes"]
    block = json.dumps(envelope, ensure_ascii=False, indent=2)
    n_loc = len(rows)

    def esc(text: str) -> str:
        return text.replace("|", "\\|").replace("\n", " ")

    signal_lines = "\n".join(
        "| %s | %d/%d | %s |"
        % (
            r["report_type"],
            r["signals_matched"],
            r["signals_total"],
            ", ".join(
                "%s×%d" % (s["signal"], s["literal_occurrences"])
                for s in r["signals"]
                if s["matched"]
            )
            or "—",
        )
        for r in per_skill
    )
    ev_lines = "\n".join(
        "| %s | %s | %s | %s | `%s` |" % (rid, kind, span, line, esc(q))
        for rid, kind, span, line, q in rows
    )
    note_lines = "\n".join(
        "- **%s**（%s）：%s；定位 %s；处置：%s"
        % (
            n["note_id"],
            n["kind"],
            n["summary"],
            "/".join(n["locator_ids"]),
            n["disposition"],
        )
        for n in notes
    )
    sec_lines = "\n".join(
        "| %d | %s | %d | %d | %s |"
        % (s["index"], s["kind"], s["start_char"], s["chars"], esc(s["title"])[:60])
        for s in secs
    )
    sem_lines = "\n".join(
        "| %s | %s | %s | %s | %s | `%s` |"
        % (
            m["map_id"],
            m["report_type"],
            m["registry_signal"],
            m["locator_id"],
            m["strength"],
            esc(m["quote"]),
        )
        for m in cls["signals"]["semantic_signal_map"]
    )
    absent_lines = "\n".join(
        "| %s | %s | %s | %s | `%s` |"
        % (a["map_id"], a["report_type"], a["registry_signal"], a["locator_id"], esc(a["quote"]))
        for a in cls["signals"]["absent_signal_evidence"]
    )
    alt_lines = "\n".join(
        "| %s | %s | %s |"
        % (
            a["report_type"],
            ", ".join(a["supporting_locator_ids"]) or "—",
            esc(a["why_not_primary"]),
        )
        for a in cls["report_type"]["alternatives_considered"]
    )
    tags = ["kf-wp:" + PACKAGE_ID, "kf-stage:02", "lane:B", "GAP-PP-5", "classification"]
    rt = cls["report_type"]

    md = f"""# KF-RESULT {PACKAGE_ID}

**package_id**: {PACKAGE_ID}
**task_type**: {cls["task_type"]}
**report_id**: {cls["report_id"]}
**tags**: {", ".join(tags)}
**status**: draft

---

## ① 本工序做了什么

**对象（案例介绍）**：report_id={cls["report_id"]}，标题 `{src["title"]}`，scenario_key=`{src["scenario_key"]}`，源 `{src["uri"]}` 的 `{src["field"]}` 字段共 {src["chars"]} 字符 / {src["bytes_utf8"]} bytes。该报告本身是"GAP-PP-5 可微路径设备口径（CPU 基线 + tensor-tau 梯度回归 A/B）"的一轮计算报告（双层结构：①–⑥ 中文正题 + 英文附录 §1–§7）。

本工序只做 **02-classification-parse**：

- 取源并**独立重算**字节哈希 → `{src["hash_with_prefix"]}`，与契约 `source_hash` 逐位一致，`chars`={src["chars"]}（契约 {src["declared_chars"]}）；
- 按 `extraction-skills/registry.json` 的六分型给出**可反驳**分类假设：primary=`{rt["primary"]}`，secondary=`{", ".join(rt["secondary"])}`，confidence=`{rt["confidence"]}`；六类逐类给出"为何不作为 primary"的裁决（③.3）；
- 选中 skill：`{cls["skills"]["selected_skill_id"]}`（次要 `{", ".join(cls["skills"]["secondary_skill_ids"])}`）；
- 结构切分：{len(secs)} 个标题全部按字符偏移落位，覆盖整篇（首节 start_char=0，末节 end_char={secs[-1]["end_char"]} = len−1）；
- {len(cls["topic_tags"])} 个主题标签，每标签绑定一条逐字 locator；
- **不做**抽取、不登记资产、不标 verified：`claims_extracted={cls["non_actions"]["claims_extracted"]}`、`assets_registered={cls["non_actions"]["assets_registered"]}`、`marked_verified={cls["non_actions"]["marked_verified"]}`、`other_reports_touched={cls["non_actions"]["other_reports_touched"]}`。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源**：`GET $TENSOR_API_BASE/tensor/reports/{cls["report_id"]}`（Bearer 登录令牌），只读 `markdown` 字段；原文逐字节副本落 `docs/{PACKAGE_ID}/source/{cls["report_id"]}.markdown`，供离线复算 locator（`sha256sum` 复核 = `{src["hash"]}`）。
2. **哈希门**：`hashlib.sha256(md.encode("utf-8"))` 与契约常量比对，不等即 `SystemExit`——不允许在错源上分类。
3. **零手抄定位**：脚本只声明**短锚串**，quote 一律 `md[start:end]` 运行时切片，记录 `start_char/end_char/start_line/end_line/quote_sha256/occurrences`；锚串非唯一即构建失败（唯一性=可解析性）。
4. **信号扫描**：对 registry 每个 skill 的 `identify_signals` 做**词边界**、大小写不敏感计数（不用裸子串：否则 `plan` 命中 `control plane`，凭空造出 technical-proposal 证据）；开放式匹配器（如 `O(n`）按字面计。
5. **语义映射与反向证据**：registry 短语与报告用词不一致时（报告写 `Wall-clock / throughput table`，registry 写 `timing table`）登记为 `semantic_signal_map`（标 strength），并另记 `absent_signal_evidence`——**信号真不满足就写不满足**，不把沉默当支持。
6. **结构切分**：行首标题正则（`#{{1,3}}`）+ ①–⑥ 标记；每节记 `start_char/chars/kind`，并断言相邻节无缝、覆盖全文。
7. **渲染**：本页所有数字、字符跨度、引文由 `scripts/kf/wp14445_02_emit_report.py` 从 `classification.json` / `kf_result_{PACKAGE_ID}.json` 注入（零手抄）；`figures/` 图由 matplotlib 从同一产物生成。
8. **机检**：`pytest tests/test_wp14445_02_classification.py`（21 项）。

工具链：Python 3 + 标准库（urllib/hashlib/json/re）+ jsonschema + matplotlib。**参数表**：本工序无数值参数（不是物理算例）——唯一"参数"是分型阈值口径（字面 vs 语义），已在 ③.2/③.3 与 `report_type.signal_policy` 明示。

## ③ 产出物清单（含结果图）

### ③.1 交付文件

| 输出文件 | 要点 |
|---|---|
| `docs/{PACKAGE_ID}/classification.json` | 分型判定（primary/secondary/confidence/五类替代裁决）+ {len(secs)} 节结构切分 + {len(cls["topic_tags"])} 主题标签 + {n_loc} 条 locator + {len(notes)} 条 parse note |
| `kf_result_{PACKAGE_ID}.json` | kf_result.v1 信封；本页 JSON 块与之**字节一致**（测试断言） |
| `docs/{PACKAGE_ID}/source/{cls["report_id"]}.markdown` | 源报告逐字节副本（{src["bytes_utf8"]} bytes），离线复核 locator |
| `figures/{PACKAGE_ID}/{fig_name}` | 图：结构切分 + 六分型信号证据（双面板） |
| `reports/KF-RESULT-{PACKAGE_ID}.md` | 本页 |
| `scripts/kf/wp14445_02_classify.py` / `scripts/kf/wp14445_02_emit_report.py` | 分类器 / 渲染器（一键复跑） |
| `tests/test_wp14445_02_classification.py` | 机器门 21 项：schema、哈希、locator 逐字可解析、ID 唯一、结构无缝、无悬空引用、单 json 块 |

### ③.2 六分型信号扫描结果（字面口径，词边界计数）

| report_type | 命中 | 命中的 signal |
|---|---|---|
{signal_lines}

字面口径领先者 = `{rt["signal_policy"]["literal_scan_leader"]}`。本工序 primary **不是**按字面计数选的（规则与证伪条件见 `report_type.decision_rule` / `signal_policy.falsifier`），差异如实留在产物里。

### ③.3 语义映射 / 反向证据 / 逐类裁决

**语义映射（只登记经得起反驳的映射，逐条带 strength）**

| id | report_type | registry signal | locator | 强度 | 原文引文 |
|---|---|---|---|---|---|
{sem_lines}

**反向证据（信号确实不满足）**

| id | report_type | registry signal | locator | 原文引文（逐字） |
|---|---|---|---|---|
{absent_lines}

**六类逐类裁决（为什么不是别的类）**

| report_type | 支撑 locator | 为何不作为 primary |
|---|---|---|
{alt_lines}

### ③.4 结果图

![{fig_name}](../figures/{PACKAGE_ID}/{fig_name})

{fig_caption}

## ④ 证据定位表（claim/字段 → 原文引文片段）

全部 quote 为运行时切片（`quote_sha256` 逐条留存），`start_char` 可直接在 `docs/{PACKAGE_ID}/source/{cls["report_id"]}.markdown` 上复算；测试对 {n_loc} 条逐条断言 `source[start:end] == quote` 且 sha256 相符、行号与偏移一致。

| locator | 用途 | 字符跨度 | 行 | 原文引文片段（逐字） |
|---|---|---|---|---|
{ev_lines}

### ④.1 结构切分（{len(secs)} 节，覆盖 {src["chars"]} 字符）

| # | kind | start_char | chars | 标题 |
|---|---|---|---|---|
{sec_lines}

### ④.2 解析备注（记录，不裁决）

{note_lines}

## ⑤ 注意点与局限

- **分类是可反驳假设，不是事实**：primary 依赖"报告想交付什么"的实质判断，而 registry 字面命中给出的是另一类（③.2 表 + falsifier）。若平台 02 政策是"纯字面信号"，本单 primary 应改判——错误在分类器，不在原文。
- **两条原文内部不一致已记录未裁决**（N1：正题写 `<0.01%` 与附录 §4.3 表最大 4.8824% 无法用文本自洽；N2：宿主架构 loongarch64 与 x86_64 两说）。本工序不做抽取与裁定，按 `preserve_uncertainty` 原样保留。
- **N3 结构重复呈现**（正题① ↔ 附录 §5 同一交付物；附录自述"程序化生成的表格"）：若 03 不按 value+context 去重，会重复计数。
- **踩坑（共享 /tmp）**：发布载荷原用 `/tmp/report.json`，该路径全机共享，本轮观察到被另一 lane 的载荷占用/覆盖；本单改用 `/tmp/report_{PACKAGE_ID}.json` 并在发布前逐字段核对 `title/tags/markdown 首行`。本单**未访问平台侧任何其它 report_id 的报告记录**，也未读写其它工作包的产物；`/tmp` 里撞见的其它 lane 载荷既未使用也未修改（我既不引用其内容，也不覆盖其路径）。
- **独立性局限**：本单 `review.required=false`、`independent_reviewer=false`，我是**生产者**，所有自检是自证；真正独立性来自平台门与 04 审核。
- **本工序不产出知识**：`source_hash_matches=true` 只是哈希事实，不是知识验证；产物内无 claim、无 `verified` 标记。

## ⑥ 自检（逐条对照 acceptance）/ 误差判定 / 复跑

| # | acceptance | 结果 | 依据（可机器复现） |
|---|---|---|---|
| 1 | valid_json | **PASS** | `json.load` 成功；`jsonschema.validate(envelope, kf_result.v1)` 通过（`test_envelope_validates_against_kf_result_schema`） |
| 2 | schema_pass | **PASS** | 信封 required 四字段齐全、`additionalProperties:false`；`outputs` 只含 `classification.json` 且为对象 |
| 3 | source_locator_resolvable | **PASS** | {n_loc}/{n_loc} 条 locator 按 `start_char:end_char` 逐字复现 + `quote_sha256` 相符 + 行号与偏移自洽（2 个测试逐条断言） |
| 4 | source_hash_matches | **PASS** | 独立重算 `{src["hash_with_prefix"]}` == 契约 == `provenance.source_hash`；`sha256sum` 对落盘副本复算一致 |
| 5 | no_duplicate_ids | **PASS** | locator_id({n_loc}) / note_id({len(notes)}) / tag({len(cls["topic_tags"])}) / 节索引 域内全唯一；`counts` 与实体逐项相符 |
| 6 | all_claims_have_evidence_or_explicit_unresolved_status | **PASS（N/A 已说明）** | 本工序不产 claim；所有判断项均带 locator；无法自洽的两处显式标 `internal_discrepancy_observed` + `unresolved` 处置，不粉饰 |

**附加机检（超出 acceptance 的自我挑战）**：结构无缝覆盖全文（`a.end_char+1 == b.start_char`，末节到 `len−1`）；产物内 `L*/T*/D*` 引用无悬空；语义映射不含无文本支持的类（literature-review / algorithm-implementation / technical-proposal）；字面命中不得由裸子串造成（`plan`/`plane` 陷阱回归测试）；报告唯一 json 块 == 信封文件字节；报告表格里的每个字符跨度都能在产物中找到。

**误差判定（关键量 vs 基准，是否 <3%）**：本工序**无数值计算**，故无"对物理/解析基准的误差"可列——这是文档结构工序，按 owner 规定写明理由而非含糊。可机检替代指标（全部为计数，无插值）：locator 逐字可解析率 = {n_loc}/{n_loc} = **100%**；源哈希一致性 = **1/1**；ID 重复 = **0**；悬空引用 = **0**；结构覆盖 = **{src["chars"]}/{src["chars"]} 字符**。分类本身**无真值基准**，故不宣称任何"分类正确率"百分比（honest：不可算）。

**未跑的检查（如实标 unknown/not_run）**：平台侧哈希与 locator 二次确认（由平台门算，本单未跑）；03 抽取阶段的实际去重行为（下游）；分类正确性的外部标注（不存在）。

**repro_cmd（一键复跑）**

```
cd <worktree> && python3 scripts/kf/wp14445_02_classify.py \\
  --source-file docs/{PACKAGE_ID}/source/{cls["report_id"]}.markdown \\
  && python3 scripts/kf/wp14445_02_emit_report.py \\
  && python3 -m pytest tests/test_wp14445_02_classification.py -q
```

（在线复核：去掉 `--source-file`，脚本重新从平台取源并重算哈希。）

---

## 结果 JSON（唯一 json 块）

```json
{block}
```
"""
    return md


def build_summary(cls: dict) -> str:
    """One-line summary; every count is derived, never typed."""
    n_loc = (
        len(cls["evidence_for_classification"])
        + len(cls["topic_locators"])
        + len(cls["parse_note_locators"])
    )
    return (
        "report %s 分类解析：primary=%s / secondary=%s，选中 %s；%d 节结构切分、%d 条逐字 locator、"
        "%d 条未裁决解析备注；不含抽取、未标 verified。"
        % (
            cls["report_id"],
            cls["report_type"]["primary"],
            "+".join(cls["report_type"]["secondary"]),
            cls["skills"]["selected_skill_id"],
            len(cls["structure"]["sections"]),
            n_loc,
            len(cls["parse_notes"]),
        )
    )


def main() -> int:
    cls = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))

    # expose parse-note locators for the report renderer
    note_ids = {lid for n in cls["parse_notes"] for lid in n["locator_ids"]}
    known = {
        rec["locator_id"]: rec
        for rec in cls["evidence_for_classification"] + cls["topic_locators"]
    }
    known.update({rec["locator_id"]: rec for rec in cls["parse_note_locators"]})
    missing = note_ids - set(known)
    if missing:
        raise SystemExit(f"parse note references unknown locator(s): {sorted(missing)}")

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig_name, fig_caption = make_figure(cls, FIG_DIR / f"fig_{PACKAGE_ID}_classification.png")

    md = build_markdown(cls, envelope, fig_name, fig_caption)
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(md, encoding="utf-8")

    png = base64.b64encode((FIG_DIR / fig_name).read_bytes()).decode()
    payload = {
        "title": f"KF-RESULT {PACKAGE_ID}",
        "summary": build_summary(cls),
        "scenario_key": SCENARIO_KEY,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "kf-stage:02", "lane:B", "GAP-PP-5", "classification"],
        "markdown": md,
        "figures": [
            {
                "name": fig_name,
                "caption": fig_caption,
                "png_base64": png,
            }
        ],
    }
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {REPORT_MD.relative_to(REPO_ROOT)} ({len(md)} chars)")
    print(f"wrote {FIG_DIR.relative_to(REPO_ROOT)}/{fig_name}")
    print(f"wrote {PAYLOAD} (markdown sha256 {hashlib.sha256(md.encode()).hexdigest()[:16]}…)")
    return 0


if __name__ == "__main__":
    sys.exit(main())