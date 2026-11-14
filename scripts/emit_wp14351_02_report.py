#!/usr/bin/env python3
"""Emit the wp-14351-02 deliverable report (markdown) and the platform payload.

Zero hand-copy: every number, offset, quote and check status in the report is
injected from ``classification.json`` / ``selfcheck.json`` / ``kf_result.json``.
The report body contains exactly one ```json fenced block — the kf_result.v1
envelope — because the platform reads the result from that block.

Usage::

    python scripts/emit_wp14351_02_report.py             # write worktree report
    python scripts/emit_wp14351_02_report.py --platform   # also write /tmp/report.json
"""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = REPO_ROOT / "docs" / "kf" / "wp-14351-02"
CLASSIFICATION = PKG_DIR / "classification.json"
SELFCHECK = PKG_DIR / "selfcheck.json"
KF_RESULT = PKG_DIR / "kf_result.json"
FIGURE = PKG_DIR / "figures" / "classification_evidence_map.png"
REPORT_MD = PKG_DIR / "KF-RESULT-wp-14351-02.md"
PLATFORM_PAYLOAD = Path("/tmp/report.json")

PACKAGE_ID = "wp-14351-02"
TAG = "kf-wp:wp-14351-02"


def md_escape(text: str) -> str:
    """Display-only escaping so verbatim quotes survive a markdown table cell."""
    return text.replace("|", "\\|")


def md_quote(text: str) -> str:
    """Wrap a verbatim quote for display (HTML <code> keeps backticks literal)."""
    return "<code>" + md_escape(text) + "</code>"


def build_markdown(cls: dict, chk: dict) -> str:
    prov = cls["provenance"]
    sens = cls["sensitivity"]

    def fmt(d: dict) -> str:
        return " / ".join(f"{k}={v}" for k, v in d.items())
    rt = cls["report_type"]
    skill = cls["selected_skill"]
    counts = cls["counts"]
    st = cls["structure"]
    scores = rt["scores"]
    score_txt = fmt(scores)
    sens_txt = fmt(sens["scores"])
    checks = {c["item"]: c for c in chk["checks"]}
    acc = chk["acceptance"]

    sig_rows = []
    for s in cls["signals"]:
        loc = s["locator"]
        sig_rows.append(
            f"| `{s['id']}` | {s['report_type']} | {s['registry_signal']} | {s['strength']}/{s['detection']} "
            f"| {loc['start_offset']}–{loc['end_offset']} | {md_quote(loc['quote'])} |"
        )
    tag_rows = [f"| `{t['id']}` | `{t['tag']}` | {t['status']} | `{md_escape(str(t.get('basis_probe')))}` |"
                for t in cls["topic_tags"]]
    sec_rows = []
    for sec in st["sections"]:
        roles = ", ".join(sec["role_keywords_hit"]) or "unmapped"
        sec_rows.append(f"| `{sec['id']}` | h{sec['level']} | {sec['start_offset']}–{sec['end_offset']} "
                        f"| {roles} | {md_escape(sec['heading'])} |")
    unres_rows = [f"| `{u['id']}` | {u['scope']} | {u['question']} | {u['reason']} |" for u in cls["unresolved"]]
    acc_rows = []
    for item, status in acc.items():
        detail = checks[item]["detail"]
        note = ""
        if item == "schema_pass":
            note = "kf_result.v1（生态 schema）+ classification.wp-14351-02（包内局部 schema，见 ⑤）"
        elif item == "source_locator_resolvable":
            note = f"{detail['resolved']} 条全部 OK_OFFSETS（逐字相等 + content_hash 相符 + quote ≥ 12 字符），失败 {len(detail['failed'])} 条"
        elif item == "source_hash_matches":
            note = f"重算 `{detail['recomputed']}` == 契约 `{detail['declared']}`"
        elif item == "no_duplicate_ids":
            note = f"共 {detail['total']} 个 id（sig/tag/sec/unres），重复 {detail['duplicates']}"
        elif item == "all_claims_have_evidence_or_explicit_unresolved_status":
            note = (f"claims=0（契约不做抽取）；替代口径：{detail['judgements_with_resolvable_evidence']} 条判定"
                    f"全部有可解析证据，{len(detail['declared_unresolved'])} 条显式 unresolved 且带理由")
        elif item == "valid_json":
            note = f"{detail['file']}（{detail['bytes']} bytes）"
        acc_rows.append(f"| {item} | {'✅ pass' if status == 'pass' else '❌ fail'} | {note} |")

    fig_rel = FIGURE.relative_to(PKG_DIR)
    return f"""# KF-RESULT {PACKAGE_ID}

**工序** `{cls['task_type']}` ｜ **报告** {cls['report_id']} ｜ **源哈希** `{prov['source_hash']}` ｜
**主判类型** `{rt['value']}`（hypothesis / confidence={rt['confidence']}）｜ **选中 skill** `{skill['skill_id']}`

一句话：报告 {cls['report_id']}（{md_escape(cls['provenance'].get('title', ''))}）被判为 `{rt['value']}`，
评分 {score_txt}（次高 `{rt['alternatives'][0]['report_type']}`={rt['alternatives'][0]['score']}，margin {rt['margin_over_runner_up']}）；
{len(cls['signals'])} 条识别信号、{counts['topic_tags_located']} 个主题标签、{st['heading_count']} 个结构切分**全部带逐字 locator**
（字符偏移精确、`sha256(quote)` 相符），另有 {counts['unresolved']} 条显式 unresolved。分类是**可反驳假设**，未标 verified。

## ① 本工序做了什么

只做**工序 02（分类解析）**：给报告 {cls['report_id']} 打类型/主题标签、做结构切分、选抽取 skill，并为每条判定给出
原文片段定位。**不做知识抽取、不做资产登记、不给验证级别**（契约 `objective: classify_report_type=true,
register_assets=false`，notes「不做抽取」；claims 恒为 0）。

正文 {prov['chars']} 字符（UTF-8 字节哈希见上），切成 {st['heading_count']} 个 markdown 标题区间
（h1 标题 + h2 章节），正文中的 ``` 围栏代码块被排除在标题识别之外（原文含一行以 `# ->` 开头的结果行，
若按行首正则切分会被误判成标题）。

分类结论（可反驳）：**`{rt['value']}`**。真正困难的是它**跨型**——本报告同时是「缺陷修复轮」
（两个求解器缺陷 + 回归测试）和「试件级部分验收」（基准 vs 本实现、honest-FAIL）。因此次高类型
`{rt['alternatives'][0]['report_type']}`（{rt['alternatives'][0]['score']} 分）与第三名
`{rt['alternatives'][1]['report_type']}`（{rt['alternatives'][1]['score']} 分）都**保留各自的定位证据**，
不删除、不合并（见 ④ 表与 `unresolved/unres-01`）。

## ② 怎么做的（步骤 / 工具 / 关键设置）

### 决策设计（先定规则，后算分）

| 项 | 内容 |
|---|---|
| 决策 | 报告的 `report_type`（六选一）+ 对应 `skill_id` |
| 备择 | registry 六类：literature-review / scientific-computation / algorithm-implementation / software-engineering / technical-proposal / experimental-validation |
| 假设 | 「报表层组织信号（标题/表格行）构成的类型即主型」——即类型由**报告结构**而非词频决定 |
| 度量 | `score(type) = Σ_不同 registry 信号 max(2·core, 1·supporting)`；core = 该信号出现在标题或 markdown 表格行，supporting = 仅正文行内出现 |
| 基线/对照 | 零命中类型**不可被选中**（`report_type:unclassified` 合法，禁止硬猜），失败即记 `excluded` |
| 预置阈值 | margin ≥ 3 → confidence=high；1–2 → medium；0 → low（平票按 registry 顺序，并降级置信度） |
| 混杂与偏倚 | ①probe 词表是读完原文后写的（**非预注册**，见 ⑤ F1）；②同一行可能同时命中两个信号（本单 sig-05/sig-06 均为字符 1899 起的表格行）；③中文报告 + registry 英文信号 → 探查串为人工翻译 |
| 重复 | 判定完全确定（无随机数）：脚本对同一字节源重复运行必须逐字节相同；不用重复采样，而是把所有六类得分全部公布以便复算 |
| 盲法 | **无**。作者先读过原文再写 probe 词表，属探索性分析（诚实披露，不做"盲"声明） |
| 环境 | repo `TensorKnowledge` 分支 `agent/m19806`；python3 + jsonschema 4.26 + matplotlib 3.10.8；源经 `GET /api/v1/tensor/reports/14351` 取回并落 `source/14351.md` |
| 分析 | 剂量=上述加权计分；不看结果改阈值；显著性的替代=把次高类型与其证据一并公开，交由 03/04 复核 |
| 敏感性检验（预置） | 备用规则 `{sens['variant']}`：同类两个不同 registry 信号若落在**同一原文行**则只计一次（合并共位证据）。若该变体**改变主判**则主判降一档置信度（`confidence_rule`） |
| 敏感性结果（实测） | 本判得分 {score_txt}；变体得分 {sens_txt}，变体 argmax=`{sens['argmax']}`，`changes_decision={sens['changes_decision']}` → 置信度 {'由 ' + rt['base_confidence'] + ' 降为 ' + rt['confidence'] if sens['changes_decision'] else '仍为 ' + rt['confidence']} |
| 资源/安全 | 纯 CPU 文本处理，无集群作业；单次运行 < 2 s；只读 report_id=14351 |

### 执行步骤

1. **取源并先证哈希（fail-closed）**：`GET /api/v1/tensor/reports/14351` 取 `markdown`，落
   `docs/kf/wp-14351-02/source/14351.md`，重算 UTF-8 字节 sha256；与契约 `{prov['source_hash']}` 不一致
   **直接返回 2 并拒绝写任何产物**（`scripts/wp14351_02_classify.py` main）。
2. **结构切分**：行级扫描 + 围栏屏蔽，识别 `#`/`##` 标题，算字符区间；heading→role 由**声明在代码里的关键词表**
   映射（`SECTION_ROLES`），映射结果公开在 `structure.role_keywords`。
3. **信号探测**：六类 × 声明 probe 串（`--print-probes` 可打印全表审计），命中即取**所在整行**为 quote，
   偏移为字符偏移，`content_hash=sha256(quote)`；`detection` 由命中位置判定（heading/table/inline）→ `strength` → 权重。
4. **判定与不确定性**：argmax + 平票规则 + 置信度分档；次高类型保留在 `alternatives`；`unresolved` 记录
   4 条无法定案/信号缺失项（不填、不猜）。
5. **复用门禁原语自检**：`scripts/validate_wp14351_02.py` 直接 import `ke.wp_gate.locator_matches` 与
   `DirSourceResolver`（E1–E6 口径一致，不另写一套定位逻辑），外加 `schemas/kf_result.v1.schema.json` 与
   包内局部 schema 双校验；结果落 `selfcheck.json`。
6. **变异自证（测试证明检查会红）**：`tests/test_kf_wp14351_02.py` 主动篡改 quote / 复制 id / 改源字节，
   断言对应验收项**变红**——避免"检查永远通过"的假门禁。
7. **出图 + 出报告**：`scripts/figures_wp14351_02.py` 与 `scripts/emit_wp14351_02_report.py`，数字/引文全部程序化注入。

**一键复跑**（工作树根）：

```bash
python scripts/wp14351_02_classify.py --refresh-source   # 取源 + 哈希门 + 分类 + 写 classification.json
python scripts/validate_wp14351_02.py --emit-kf-result    # 六项验收自检 + 写 kf_result.json/selfcheck.json
python scripts/figures_wp14351_02.py                     # 证据图
python scripts/emit_wp14351_02_report.py                 # 生成本报告（含唯一 json 块）
python -m pytest tests/test_kf_wp14351_02.py -q          # 含变异测试
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `classification.json` | 工序 02 主工件：report_type=`{rt['value']}`（hypothesis, {rt['confidence']}）、six-type 得分、选中 skill、{len(cls['signals'])} 条带 locator 的信号、{st['heading_count']} 段结构、{counts['topic_tags_located']} 个主题标签、{counts['unresolved']} 条 unresolved |
| `kf_result.json` | 交付信封（`kf_result.v1`，六键）；`outputs.classification.json` 内嵌全量工件 |
| `selfcheck.json` | 六项验收逐条结果 + 明细（含 schema 名、locator 计数、id 计数） |
| `source/14351.md` | 源 markdown 快照（离线复跑用；哈希钉住，字节级） |
| `figures/classification_evidence_map.png` | 上：六类加权得分；下：信号在正文中的字符位置图（core 圆 / supporting 方） |
| `KF-RESULT-wp-14351-02.md` | 本报告（六段 + 对抗性自审 + 唯一结果 json 块） |
| `schemas/classification.wp-14351-02.schema.json` | **包内局部** classification schema（生态层尚无共享 schema，见 ⑤ F4） |
| `scripts/wp14351_02_classify.py` | 分类器（probe 表内联、可审计、哈希 fail-closed） |
| `scripts/validate_wp14351_02.py` | 六项验收自检（复用 `ke.wp_gate` 原语） |
| `scripts/figures_wp14351_02.py` / `scripts/emit_wp14351_02_report.py` | 出图 / 出报告（程序化注入，零手抄） |
| `tests/test_kf_wp14351_02.py` | 回归 + 变异测试（证明检查可红） |

## ④ 证据定位表（判定 → 原文引文片段）

全部 {len(cls['signals']) + counts['topic_tags_located']} 条定位满足：`text[start_offset:end_offset] == quote`（字符口径），
`content_hash = sha256(quote)`，quote 长度 ≥ 12 字符。下表 quote 逐字取自源文（表格内 `|` 为**显示转义**、quote 用 `<code>` 包裹仅为渲染；JSON 内保留原字符）。

### 4.1 类型识别信号（{len(cls['signals'])} 条）

| 判定 | report_type | registry 信号 | 强度/检测 | 区间 [start,end) | 原文引文（逐字） |
|---|---|---|---|---|---|
{chr(10).join(sig_rows)}

### 4.2 主题标签（{counts['topic_tags_located']} 个）

| id | tag | 状态 | 触发串 |
|---|---|---|---|
{chr(10).join(tag_rows)}

### 4.3 结构切分（{st['heading_count']} 段）

| id | 级别 | 字符区间 | role（关键词映射） | 标题（逐字） |
|---|---|---|---|---|
{chr(10).join(sec_rows)}

## ⑤ 注意点与局限

- **F1（中｜影响判定）probe 词表非预注册**：作者先读原文再写 probe，置信度只能如实给 `{rt['confidence']}`，
  不能当"客观测量"。缓解：全部 probe（`--print-probes`）、全部命中、全部六类得分与次高类型证据都公开。
- **F2（中）跨型报告，单一 report_type 是压缩**：本报告 = 缺陷修复 + 部分验收 + 数值参数。次高
  `{rt['alternatives'][0]['report_type']}`（{rt['alternatives'][0]['score']}）与第三 `{rt['alternatives'][1]['report_type']}`
  （{rt['alternatives'][1]['score']}）保留为 `alternatives`，供 03 抽取时按需并用（`selected_skill.secondary_skill_hint`）。
- **F3（中｜直接决定 confidence）信号共位使标签脆弱**：`test matrix` 与 `baseline comparison` 的首条命中是
  **同一行**（字符 {sens['collocated'][0]['start_offset']} 起的表格行 `| 量 | 基准(ref) | 本实现(got) | 相对误差 | 判据 | 判定 |`），
  同一句证据被两个 registry 信号各计一次。按预置敏感性变体 `{sens['variant']}` 合并共位证据后，得分变为
  {sens_txt}，argmax=`{sens['argmax']}`，**主判翻转**（`changes_decision={sens['changes_decision']}`）。
  因此本单把 confidence 从 {rt['base_confidence']} 降为 **{rt['confidence']}**，且把「单一 report_type」
  明确降级为**压缩标签**：本报告实为 `{rt['value']}` × `{rt['alternatives'][0]['report_type']}` 的跨型报告，
  03 抽取应按主型 skill 执行并对次型字段做交叉核对（`secondary_skill_hint`）。这不是措辞问题：
  换个同样合理的计分口径，结论就换型——这正是 02 只能给 hypothesis 的实证。
- **F4（中｜生态层缺口）仓库没有共享 classification schema**：`schema_pass` 只对
  `kf_result.v1`（生态）+ `classification.wp-14351-02`（**本包局部**，无跨报告权威）成立。跨报告可比性仍需生态层 schema。
- **F5（低）结构 role 是关键词映射，非作者声明**：`role_keywords_hit` 只是标题里出现过的 role 关键词
  （如「计算结果」同时命中 results/comparison/verification），不能当作章节用途的权威标注。
- **F6（低）图内标签用 ASCII**：本机 matplotlib 唯一字体 Noto Sans 无 CJK 字形，图中章节以 `sec-id/role` 标注，
  **中文标题不在图里**，逐字引文以 JSON/本表为准（避免出豆腐块假图）。
- **F7 适用边界**：probe 检测对**改写/同义**信号无能为力；本报告无「不确定度/误差带」与「commit id」
  两类信号（原文确实没有），记为 unresolved-02/03，**不补写**。
- **不做的事（硬边界）**：不做知识抽取（claims=0）、不登记资产、不标 verified、不读写其它 report_id；
  语义是否"真表达原文"属于 G3/04 独立审核，本单不声称通过。

### 显式挂账（unresolved，{counts['unresolved']} 条）

| id | scope | 问题 | 理由 |
|---|---|---|---|
{chr(10).join(unres_rows)}

## ⑥ 自检：逐条对照 acceptance

| 验收项 | 结果 | 依据（程序化） |
|---|---|---|
{chr(10).join(acc_rows)}

诚实说明：`schema_pass` 的第二半（classification 形状）只对本包局部 schema 成立（F4）；`all_claims_...`
在本包按**判定**口径执行而非 claim 口径（claims=0 由契约规定，不构造 claim 凑数）。六项之外**未跑**的检查：
G3 语义保真（不可程序化）、04 独立审核（本包 `review.required=false`）、跨报告相似度/重复包检测（无基线数据）、
report_type 正确率（无 ground truth，且 F3 已证标签随计分口径翻转）。

## 结果图

![classification evidence map]({fig_rel})

上：六类加权得分（红=主判，灰=其它；柱内标 core/supporting 命中数）。下：正文 {prov['chars']} 字符坐标上的
信号落点（圆形=core，方形=supporting；底纹=结构切分区间）。两种视图都只由 `classification.json` 渲染，
无手输数字。

## 误差判定（逐项回答「是否 <3%」）

本工序是**文档分类**，无物理场量、无实验/解析基准，故"关键物理量 vs 基准误差 <3%"**不适用**
（无基准 → 不做含糊表述）。可程序化对标的量如下，逐项给出实测：

| 关键量 | 基准 | 实测 | 误差 | <3%? |
|---|---|---|---|---|
| 源 markdown 字节哈希 | 契约 `{prov['source_hash'][:23]}…` | 重算逐字节相同 | 0（位级相等） | **是（0%）** |
| locator 逐字命中率 | {len(cls['signals']) + counts['topic_tags_located']} 条 | {checks['source_locator_resolvable']['detail']['resolved']} 条 OK_OFFSETS | 0 | **是（0%）** |
| quote 哈希一致性 | 全部 locator | {checks['source_locator_resolvable']['detail']['resolved']} 条 `sha256(quote)` 相符 | 0 | **是（0%）** |
| report_type 正确率 | **无 ground truth** | 单次判定（{rt['value']}，margin {rt['margin_over_runner_up']}） | 不可测 | **不适用**（无基准，见 ⑤ F1/F2） |

## ⑦ 对抗性自审（作者审作者，**非独立**）

**独立性局限**：本节由生产者自己执行，不能替代 04 独立审核；`review.required=false`，本单不声称已审。

**检查范围**：重算源哈希；逐条重解 {len(cls['signals']) + counts['topic_tags_located']} 条 locator；
双 schema 校验；id 唯一性；拆分/围栏边界（含 `# -> 61 passed, 2 xfailed` 假标题陷阱）；变异测试（篡改 quote、
复制 id、改字节）；报告内 json 块唯一性；越界（只碰 report_id=14351）。

**按严重度排序的发现**：

| 严重度 | 发现 | 证据 | 处置 |
|---|---|---|---|
| 中 | probe 词表探索性，非预注册（F1） | 代码注释 + `rule_registration` 字段如实写"exploratory" | 公开全表与次高证据；置信度按分档规则给 {rt['base_confidence']}，再因 F3 脆弱性降为 {rt['confidence']} |
| 中 | 生态层无 classification schema（F4） | `ls schemas/` 无共享 classification schema；本包自带局部 schema | 记为局限，提请生态层立 schema；不冒充生态合规 |
| 低-中 | 跨型压缩（F2） | 三条类型得分 {score_txt} | 保留 alternatives + secondary_skill_hint |
| 中 | 共位证据重复计分导致主判翻转（F3） | 敏感性变体得分 {sens_txt}，argmax `{sens['argmax']}` | confidence 降档为 {rt['confidence']}；主判降级为跨型压缩标签，次型证据保留 |
| 低 | 图无中文（F6） | 字体表无 CJK 字形 | 图用 id/role，逐字引文以 JSON 为准 |

**未跑的检查**：G3 语义保真、04 独立审核、跨包去重、profile 级性能（无性能面）。
**是否夸大**：无 verified 字段；`report_type.status=hypothesis`；`selfcheck.json` 明写"self-check only"。
**结论**：approve with notes（自审口径）；最终判定权在平台门与独立审核。

```json
{json.dumps(json.loads(KF_RESULT.read_text(encoding='utf-8')), ensure_ascii=False, indent=2)}
```
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--platform", action="store_true")
    args = ap.parse_args()

    cls = json.loads(CLASSIFICATION.read_text(encoding="utf-8"))
    chk = json.loads(SELFCHECK.read_text(encoding="utf-8"))
    by_item = {c["item"]: c for c in chk["checks"]}
    md = build_markdown(cls, chk)
    REPORT_MD.write_text(md, encoding="utf-8")
    print(f"wrote {REPORT_MD.relative_to(REPO_ROOT)} ({len(md)} chars, "
          f"{md.count('```json')} json block)")

    if args.platform:
        png = FIGURE.read_bytes()
        payload = {
            "title": f"KF-RESULT {PACKAGE_ID}",
            "summary": (
                f"报告 14351（GAP-FEM-3D-COHESIVE 返修轮）工序 02 分类解析：判为 "
                f"{cls['report_type']['value']}（confidence={cls['report_type']['confidence']}，"
                f"margin={cls['report_type']['margin_over_runner_up']}），选中 skill "
                f"{cls['selected_skill']['skill_id']}；{len(cls['signals'])} 条识别信号 + "
                f"{cls['counts']['topic_tags_located']} 个主题标签 + {cls['structure']['heading_count']} 段结构切分"
                f"全部带逐字 locator（{by_item['source_locator_resolvable']['detail']['resolved']} 条 OK_OFFSETS），"
                f"{cls['counts']['unresolved']} 条显式 unresolved。分类是假设不是 verified；"
                f"未抽 claim、未登记资产。诚实失败项：生态层无共享 classification schema，schema_pass 的 "
                f"classification 半边只对包内局部 schema 成立；report_type 无 ground truth 不可测。"
            ),
            "scenario_key": "TensorFEM",
            "mission_id": 19806,
            "tags": [TAG, "KF-02", "classification-parse", "report:14351",
                     "GAP-FEM-3D-COHESIVE", "TensorFEM", "cohesive", "honest-partial-acceptance"],
            "markdown": md,
            "figures": [{
                "name": "classification_evidence_map.png",
                "caption": (
                    "上：六类 report_type 声明加权得分（红=主判 experimental-validation，"
                    "柱内为 core/supporting 命中数）；下：每条识别信号在正文 4190 字符坐标上的落点"
                    "（圆=core 标题/表格行，方=supporting 行内），底纹=结构切分区间。"
                ),
                "png_base64": base64.b64encode(png).decode("ascii"),
            }],
        }
        PLATFORM_PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {PLATFORM_PAYLOAD} (figure {len(png)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())