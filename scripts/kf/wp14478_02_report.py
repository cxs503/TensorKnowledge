#!/usr/bin/env python3
"""wp-14478-02 报告生成 + 投递：由产物 JSON 程序化注入数字（零手抄），并 POST 到平台。

用法：
  python3 scripts/kf/wp14478_02_report.py            # 只生成本地 docs/kf/wp-14478-02/report.md
  python3 scripts/kf/wp14478_02_report.py --publish  # 另投递到 /tensor/reports（需 TENSOR_AGENT_USER/PASS）

报告里唯一的 ```json 代码块 = kf_result.json 原文（逐字节同 docs/kf/wp-14478-02/kf_result.json）。
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
import os
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "docs" / "kf" / "wp-14478-02"
FIG = OUT / "figures" / "classification_map.png"
PACKAGE_ID = "wp-14478-02"
MISSION_ID = 19808
SCENARIO_KEY = "kf-classify-wp-14478-02"
TAGS = [f"kf-wp:{PACKAGE_ID}", "KF-RESULT", "classification",
        "02-classification-parse", "case-cylinder-drag-fvm"]
REPRO = ("python3 scripts/kf/wp14478_02_classify.py --check "
         "--snapshot docs/kf/wp-14478-02/source/report_14478.md && "
         "python3 -m pytest tests/test_kf_wp14478_02.py -q && "
         "python3 scripts/kf/wp14478_02_report.py")


def load_checker():
    spec = importlib.util.spec_from_file_location(
        "wp14478_02_classify", REPO / "scripts" / "kf" / "wp14478_02_classify.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def param_rows(md: str) -> list[str]:
    """从源报告 §③ 参数表程序化取行（不重打任何数字）。"""
    lines = md.split("\n")
    out, on = [], False
    for line in lines:
        if line.startswith("| 量 | 符号 |"):
            on = True
        if on:
            if not line.startswith("|"):
                break
            out.append(line)
    return out


def code(text: str) -> str:
    """把逐字引文包成 inline code；引文自带反引号时自动加长栅栏，避免渲染破坏。"""
    import re as _re
    longest = max((len(m) for m in _re.findall(r"`+", text)), default=0)
    fence = "`" * (longest + 1)
    # 首尾各留一个空格：CommonMark 会去掉这层空格，且避免与引文自带的 run 粘连成更长的开栅栏
    return f"{fence} {text} {fence}"


def trunc(text: str, n: int) -> str:
    text = text.replace("|", "\\|")
    return text if len(text) <= n else text[:n - 1] + "…"


def build() -> tuple[str, dict]:
    cls = json.loads((OUT / "classification.json").read_text(encoding="utf-8"))
    kf = json.loads((OUT / "kf_result.json").read_text(encoding="utf-8"))
    md_src = (OUT / "source" / "report_14478.md").read_text(encoding="utf-8")
    mod = load_checker()
    checks = mod.self_check(md_src, cls, kf)

    n_loc = sum(len(r.get("evidence", [])) for r in cls["signals"] + cls["topics"])
    sig_by_rt: dict[str, list[dict]] = {}
    for s in cls["signals"]:
        sig_by_rt.setdefault(s["report_type"], []).append(s)
    tally = {rt: {v: sum(1 for s in ss if s["verdict"] == v)
                  for v in ("matched", "partial", "not_found")}
             for rt, ss in sig_by_rt.items()}
    secs = cls["structure"]["sections"]
    src = cls["source"]

    def tbl(rows: list[list[str]], head: list[str]) -> str:
        out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        out += ["| " + " | ".join(r) + " |" for r in rows]
        return "\n".join(out)

    signal_rows = []
    for s in cls["signals"]:
        if s.get("evidence"):
            loc = s["evidence"][0]
            q = trunc(loc["quote"], 78)
            where = f"{loc['start_offset']}–{loc['end_offset']}"
            extra = f"（共 {len(s['evidence'])} 条 locator）" if len(s["evidence"]) > 1 else ""
            signal_rows.append([s["id"], s["signal"], s["verdict"], where, f"{code(q)}{extra}"])
        else:
            signal_rows.append([s["id"], s["signal"], s["verdict"], "—",
                                "（无引文：显式 unresolved，见 classification.json）"])

    topic_rows = [[t["id"], t["tag"], t["scheme"],
                   f"{t['evidence'][0]['start_offset']}–{t['evidence'][0]['end_offset']}",
                   code(trunc(t["evidence"][0]["quote"], 62))]
                  for t in cls["topics"]]

    by_id = {s["id"]: s for s in cls["signals"]}

    def sig(sid: str) -> dict:
        return by_id[sid]

    sec_rows = [[s["id"], str(s["level"]), s["heading"].replace("|", "\\|"),
                 f"{s['start_offset']}–{s['end_offset']}", str(s["end_offset"] - s["start_offset"])]
                for s in secs]

    tally_rows = [[rt, str(t["matched"]), str(t["partial"]), str(t["not_found"]),
                   [c["verdict"] for c in cls["report_type"]["candidates"] if c["id"] == rt][0]]
                  for rt, t in tally.items() if not rt.startswith("(")]

    check_rows = [[k, "✅" if v["pass"] else "❌", v["detail"].replace("|", "\\|")[:110]]
                  for k, v in checks.items()]
    n_fail = sum(1 for v in checks.values() if not v["pass"])

    fig_b64 = base64.b64encode(FIG.read_bytes()).decode()
    json_block = json.dumps(kf, ensure_ascii=False, indent=1)

    md = f"""# KF-RESULT {PACKAGE_ID}

工作包 `{PACKAGE_ID}`（工序 02 分类解析，lane B，契约 1.0）对报告 `{cls['report_id']}` 的判定结果。
本工序只做**分类/解析**，不做抽取、不做证据定性、不盖 verified。

## ① 本工序做了什么

对报告 `{src['uri']}` 的 `markdown` 字段（{src['chars']} 字符 / {src['bytes_utf8']} 字节 UTF-8 /
{src['lines']} 行，重算哈希 `{src['recomputed_hash'][:19]}…` 与契约一致）做三件可机检的事：

1. **判类型**：按 `extraction-skills/<type>.md` §1 的 `identify_signals` 逐条判六分型，结论
   **`{cls['report_type']['id']}`**（置信 **{cls['report_type']['confidence']}**），选中 skill
   `{cls['report_type']['chosen_skill_id']}` v{cls['report_type']['skill_version']}
   （lifecycle `{cls['report_type']['skill_lifecycle_state']}`）；
2. **给主题标签**：{len(cls['topics'])} 条检索标签（学科域/方法/状态/平台/工具链），每条锚在原文逐字引文；
3. **切结构**：按行首 `#` 切成 {len(secs)} 段、首尾相接覆盖 `0–{secs[-1]['end_offset']}` 全文。

交付物 `classification.json` 中 {len(cls['signals'])} 条判定信号 + {n_loc} 个 locator（字符偏移 + 逐字引文 +
引文 sha256），**0 条无证据的判定**：无引文的项一律显式 `unresolved` 并写理由。

**本工序不产生任何物理结果数字**（无 C_D / C_L / p_diff 的 got），也不复制源报告的 got 数字。

### 案例背景（源报告自述，逐字引用；本工序不做二次叙述）

- 状态：`{sig('SIG-ST-01')['evidence'][0]['quote']}`
- 算例：`{sig('SIG-EV-01')['evidence'][0]['quote']}`
- 判定口径来自源报告而非本工序：`{sig('SIG-EV-02')['evidence'][0]['quote']}`

源报告 §③ 参数表（**程序化整行注入，未重打任何数字**）：

{tbl([[c.strip() for c in r.strip('|').split('|')] for r in param_rows(md_src)[2:]],
     [c.strip() for c in param_rows(md_src)[0].strip('|').split('|')])}

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文（不许凭记忆）**：`GET $TENSOR_API_BASE/tensor/reports/{cls['report_id']}` 取 `markdown`，
   落字节快照 `docs/kf/wp-14478-02/source/report_14478.md`（`{src['fetched_via']}`）；
   `psql` 直读被权限拒绝（`permission denied for table tensor_reports`），故走 API。
2. **源身份门**：`sha256(markdown.encode('utf-8'))` 重算 = `{src['recomputed_hash']}`，与契约
   `{src['contract_hash']}` **逐字节相等**，字符数 {src['chars']} = 契约 `chars`。
3. **逐条判定**：对六型共 6 组注册表信号写死 `signal` 文本（抄自 skill 文档 §1）+ 逐字 `quote`；
   生成器用 `md.index(quote)` 求偏移、断言 `md[s:e] == quote`、要求**全文唯一**（否则报错退出），
   并算 `sha256(quote)` 作为 `content_hash`（对齐 GATE-RULES E3/E5）。
4. **结构切分**：行首 `#` 行切段，断言相邻段 `end_offset == next.start_offset` 且末段到文末。
5. **schema 门**：产物对 `schemas/classification.v1.schema.json`（本仓新增）与
   `schemas/kf_result.v1.schema.json` 用 `jsonschema`(Draft 2020-12) 校验。
6. **确定性复跑**：pytest 里把生成器跑到 tmp 目录，断言两份 JSON 与入库版本**逐字段相等**。

一键复跑（工作树根）：

```bash
# 平台重取 + 全链路自检 + 测试 + 报告再生成
python3 scripts/kf/wp14478_02_classify.py --fetch --check
python3 -m pytest tests/test_kf_wp14478_02.py -q
python3 scripts/kf/wp14478_02_report.py
# 无平台凭据时的离线口径（用已入库的字节快照）
{REPRO}
```

关键设置：`unique=True`（引文必须唯一）、`Draft202012Validator`、`minLength` 约束（quote ≥1、
unresolved.reason ≥20 字符）、`epistemic_status=draft` / `assessment_status=unassessed`。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-14478-02/classification.json` | 工序 02 产物：类型 = **{cls['report_type']['id']}**（confidence {cls['report_type']['confidence']}）、{len(cls['signals'])} 条信号、{len(cls['topics'])} 条主题标签、{len(secs)} 段结构切分、{n_loc} 个 locator |
| `docs/kf/wp-14478-02/kf_result.json` | KF-RESULT 信封：`source_hash` = `{kf['provenance']['source_hash'][:19]}…`（=契约）、`chars` = {kf['provenance']['chars']} |
| `docs/kf/wp-14478-02/source/report_14478.md` | 源字节快照（{src['bytes_utf8']} 字节），哈希与平台一致，供离线复算 |
| `docs/kf/wp-14478-02/figures/classification_map.png` | 图：结构分段轴 + 信号命中位置 + 六分型信号命中分布 |
| `schemas/classification.v1.schema.json` | 工序 02 产物的可机检 schema（本仓新增，见 ⑤ 局限） |
| `scripts/kf/wp14478_02_classify.py` | 生成器 + acceptance 自检（`--check` 失败即非零退出） |
| `tests/test_kf_wp14478_02.py` | 14 项独立不变量测试（哈希/偏移/唯一性/schema/确定性/边界） |

### 六分型信号命中统计（程序化统计自 `classification.json`）

{tbl(tally_rows, ["候选类型", "matched", "partial", "not_found", "判定"])}

判定依据：`{cls['report_type']['decision_basis']}`

### 结构切分（{len(secs)} 段，覆盖全文）

{tbl(sec_rows, ["段 ID", "层级", "标题", "偏移", "长度"])}

## ④ 证据定位表（claim / 字段 → 原文引文片段）

偏移口径：UTF-8 解码后字符下标，0 基、end 开区间；`content_hash` = `sha256(quote)`，全部在
`classification.json` 内逐条给出。下表引文为**原文逐字片段**：表格内 `|` 按 Markdown 需转义为 `\|`、过长处截断并以 `…` 结尾——
转义/截断只发生在本表渲染层，**完整逐字引文与偏移以 `classification.json` 的 `quote` 字段为准**。

### 4.1 判定信号（{len(cls['signals'])} 条）

{tbl(signal_rows, ["信号 ID", "注册表信号", "判定", "字符偏移", "原文引文（逐字）"])}

### 4.2 主题标签（{len(cls['topics'])} 条）

{tbl(topic_rows, ["标签 ID", "标签", "体系", "字符偏移", "原文引文（逐字）"])}

### 4.3 图

![classification_map](attachment:classification_map.png)

图注：上半为源报告 {src['chars']} 字符的结构分段（竖线=段边界，标注段 ID 与标题）与分类信号命中位置
（▲ 绿=matched、橙=partial，竖排为信号 ID）；下半为六分型候选按注册表 `identify_signals` 的命中计数
（绿/橙/红=matched/partial/not_found）——`scientific-computation` 是唯一有 matched 的类型。
图由 `scripts/kf/wp14478_02_report.py` 从 `classification.json` 程序化生成，无手绘数字。

## ⑤ 注意点与局限

1. **信号判定是文本层判定，不是执行状态判定**：`SIG-SC-03`（convergence study）与 `SIG-SC-04`
   （mesh refinement）判 matched，指源报告**声明了**这两件事；源报告 §⑤ 自述“设计已完成、待数据即可出数”，
   并不表示已算出收敛阶。本工序不评价执行状态。
2. **竞争类型确实存在 matched 信号**：`experimental-validation` 的 `validation case` 也 matched
   （本算例本身就是一个基准算例），故 confidence 取 **medium** 而非 high；区分依据是该型三条定义性信号
   （test matrix / facility description / measurement uncertainty）全为 `not_found`，且对照侧是文献数值基准
   而非测量值。
3. **`governing equation` 与 `timing table` 只到 partial**：源报告未写出控制方程显式形式，也只有单点耗时
   陈述（无耗时表）。两项均记 `unresolved` + 理由 + “什么能解决它”，**未补写方程/耗时表**。
4. **schema 是自建的**：平台侧 `kf_result.v1.schema.json` 只把 `outputs.classification.json` 声明为无约束
   `object`，仓内没有官方 02 产物 schema，因此 `schema_pass` 由本次新增的
   `schemas/classification.v1.schema.json` 自查给出——这是自查，不等于平台认可的口径。
5. **结构解析器不做代码栅栏感知**：按行首 `#` 切段；本源文件代码块内无行首 `#`（段连续性断言已覆盖），
   但用于其它报告时可能误切。
6. **注册表本身未校准**：`extraction-skills/registry.json` 全部 skill 的生命周期是 `template-created`、
   `reuse_count = 0`，`citation density ≥ 5/1000` 这类阈值没被真实报告校准过；`SIG-LR-03` 是按可见条目
   人工判断，未做机器引文计数。
7. **零手抄的边界**：本报告所有数字/引文由脚本从 `classification.json` / `kf_result.json` / 源快照注入，
   没有一处凭记忆重述；正文里唯一的人工文字是判定理由与局限说明。
8. **不越界**：只读/写 `report_id={cls['report_id']}`；未读取其它报告、未改写上游产物、未把任何对象标为
   verified（`epistemic_status=draft`、`assessment_status=unassessed`、
   `verification_performed_by_producer=false`）。

### 误差判定（本工序口径，如实记）

本工序是文档分类工序，**不产生计算量**，因此没有“本工序结果 vs 基准”的误差可列；源报告的
5% 判据（`<5%`，见 4.1 中 `SIG-EV-02`）在其自身 ④ 对照表里**无 got**（`SIG-ST-02`），本工序不补、不估、
不引用任何历史数字。回答“是否 <3%”：**NOT_APPLICABLE — 无本工序计算量，且源报告无 got 值可判**。

### 对抗性自查（作者自审，不独立）

- 严重度 High：无（未发现可导致错分/伪证的未披露缺陷）；**Medium-1**：竞争类型 matched 信号未降级为
  unresolved，仅用 confidence + rationale 承载 → 处置：保留为 matched（文本确实存在）并下调 confidence，
  rationale 明写拒绝依据；**Medium-2**：`schema_pass` 自建 schema → 处置：在 ⑤.4 显式披露，交由平台门复核；
  **Low**：主题标签命名粒度为主观 → 已在 `uncertainty` 记录。
- 未做的检查：类型判定的**语义**正确性无机器判据（需 04 工序/人工）；未做跨报告引文密度机器计数。

## ⑥ 自检：逐条对照 acceptance

{tbl(check_rows, ["acceptance 项", "结果", "依据"])}

**失败项：{n_fail}**。{"全部通过（自检口径见上表）。" if n_fail == 0 else "见上表 ❌ 行，如实记录未粉饰。"}

补充说明（不含在 acceptance 但本单要求的纪律）：

- ✅ 本报告只有一个 JSON 代码块（围栏语言标记为 json）= `kf_result.json` 原文，逐字节同
  `docs/kf/wp-14478-02/kf_result.json`；标题 `KF-RESULT {PACKAGE_ID}`，tags 含 `kf-wp:{PACKAGE_ID}`；
- ✅ `provenance.source_hash` 与源报告 markdown 字节哈希一致（平台独立重算）；
- ✅ honest 项：源报告 ④ 无 got、`governing equation`/`timing table` 仅 partial、schema 自建——均已写在 ⑤。

## 附：kf_result.json（本报告唯一的 JSON 代码块）

```json
{json_block}
```
"""
    return md, {"title": f"KF-RESULT {PACKAGE_ID}", "tags": TAGS,
                "summary": summary(cls, checks, n_fail),
                "markdown": md, "figures": [{"name": "classification_map.png",
                                            "caption": "结构分段 + 信号命中位置 + 六分型命中分布",
                                            "png_base64": fig_b64}]}


def summary(cls: dict, checks: dict, n_fail: int) -> str:
    return (f"报告 {cls['report_id']} 分类解析：类型 = {cls['report_type']['id']}"
            f"（confidence {cls['report_type']['confidence']}，skill {cls['report_type']['chosen_skill_id']}），"
            f"{len(cls['signals'])} 条判定信号全部带逐字 locator 或显式 unresolved，"
            f"{len(cls['topics'])} 条主题标签、{len(cls['structure']['sections'])} 段结构切分；"
            f"acceptance 自检 {len(checks) - n_fail}/{len(checks)} 通过。")


def publish(payload: dict) -> dict:
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, pwd = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    req = urllib.request.Request(
        f"{base}/auth/login",
        data=json.dumps({"username": user, "password": pwd}).encode(),
        headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as fh:
        token = json.load(fh)["access_token"]
    body = {"title": payload["title"], "summary": payload["summary"],
            "scenario_key": SCENARIO_KEY, "mission_id": MISSION_ID,
            "tags": TAGS,
            "markdown": payload["markdown"], "figures": payload["figures"]}
    req = urllib.request.Request(
        f"{base}/tensor/reports", data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=60) as fh:
        return json.load(fh)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true")
    ap.add_argument("--out", type=Path, default=OUT / "report.md")
    args = ap.parse_args(argv)
    md, payload = build()
    args.out.write_text(md, encoding="utf-8")
    print(f"report -> {args.out} ({len(md)} chars)")
    if args.publish:
        rec = publish(payload)
        print(json.dumps({k: rec.get(k) for k in ("id", "title", "status", "created_at")},
                         ensure_ascii=False))
        (OUT / "published.json").write_text(json.dumps(rec, ensure_ascii=False, indent=1),
                                            encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())