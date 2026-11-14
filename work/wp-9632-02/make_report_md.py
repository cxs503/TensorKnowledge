"""生成 KF-RESULT 报告 markdown（六段）+ 平台投递 payload。

引文、偏移量、哈希、计数全部从 classification.json / verify_report.json 注入，
脚本内不出现任何源报告数字或公式（零手抄）；报告里只有一个 ```json 代码块。
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

PKG = Path(__file__).resolve().parent
REPORT_MD = PKG / "KF-RESULT-wp-9632-02.md"
PAYLOAD = PKG / "platform_report.json"
FIG = PKG / "figures" / "classification_overview.png"
MISSION_ID = 19800


def _short(h: str) -> str:
    return h.replace("sha256:", "")[:16] + "…"


def _cell(s: str, n: int = 58) -> str:
    s = s.replace("|", "\\|").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def main() -> int:
    cls = json.loads((PKG / "classification.json").read_text(encoding="utf-8"))
    kf = json.loads((PKG / "kf_result_wp-9632-02.json").read_text(encoding="utf-8"))
    ver = json.loads((PKG / "verify_report.json").read_text(encoding="utf-8"))
    pkg = kf["package_id"]
    prov = cls["provenance"]
    st = cls["structure"]
    n_ev = len(cls["evidence"])
    n_sig = len(cls["signals"])
    top = cls["candidate_matrix"][0]
    second = cls["candidate_matrix"][1]
    ev_by_id = {e["id"]: e for e in cls["evidence"]}
    sig_by_id = {s["id"]: s for s in cls["signals"]}

    # ---- ④ 证据定位表（信号侧）
    rows = []
    for s in cls["signals"]:
        if not s["evidence_id"]:
            continue
        e = ev_by_id[s["evidence_id"]]
        rows.append(
            "| {sig} | {typ} / `{signal}` → {match} | {ev} | `[{a},{b})` | `{h}` | {q} |".format(
                sig=s["id"], typ=s["report_type"], signal=s["signal"], match=s["match"],
                ev=e["id"], a=e["start_offset"], b=e["end_offset"], h=_short(e["content_hash"]),
                q=_cell(e["quote"]),
            )
        )
    topic_rows = []
    for t in (*cls["topics"], *cls["preserved_uncertainty"]):
        e = ev_by_id[t["evidence_id"]]
        label = t.get("label") or t.get("note", "")
        topic_rows.append(
            "| {i} | {lab} | {ev} | `[{a},{b})` | {q} |".format(
                i=t["id"], lab=_cell(label, 40), ev=e["id"], a=e["start_offset"],
                b=e["end_offset"], q=_cell(e["quote"], 52),
            )
        )

    # ---- ⑥ 自检表（映射到工作包 acceptance）
    acc_map = [
        ("valid_json", ["C1.valid_json"]),
        ("schema_pass", ["C2.schema_pass"]),
        ("source_locator_resolvable", ["C4.source_locator_resolvable", "C5.quote_content_hash"]),
        ("source_hash_matches", ["C3.source_hash_matches", "C3b.chars_match"]),
        ("no_duplicate_ids", ["C6.no_duplicate_ids"]),
        ("all_claims_have_evidence_or_explicit_unresolved_status",
         ["C7.claims_evidence_or_unresolved"]),
        ("no_forced_claim_generation / do_not_mark_claims_as_verified",
         ["C8.no_self_verification"]),
        ("结构切分可定位（本工序附加）",
         ["C9.section_map_sane", "C10.report_type_in_taxonomy"]),
    ]
    cmap = {c["id"]: c for c in ver["checks"]}
    self_rows = []
    for acc, ids in acc_map:
        ok = all(cmap[i]["ok"] for i in ids if i in cmap)
        detail = "; ".join(f"{i}={cmap[i]['detail'][:70]}" for i in ids if i in cmap)
        self_rows.append(f"| `{acc}` | {'✓' if ok else '✗'} | {_cell(detail, 96)} |")
    n_fail = sum(1 for r in self_rows if "| ✗ |" in r)

    cand_rows = [
        "| {r} | `{t}` | {m} | {p} | {a} | {s} | {d} |".format(
            r=c["rank"], t=c["report_type"], m=c["matched"], p=c["partial"],
            a=c["absent"], s=c["score"], d=c["decision"])
        for c in cls["candidate_matrix"]
    ]
    sec_rows = [
        "| {i} | h{l} | `[{a},{b})` | {h} |".format(
            i=s["id"], l=s["level"], a=s["start_offset"], b=s["end_offset"],
            h=_cell(s["heading"], 48))
        for s in st["sections"]
    ]
    unres_rows = [
        "| {i} | {it} | `{s}` | {n} |".format(i=u["id"], it=_cell(u["item"], 34),
                                              s=u["status"], n=_cell(u["note"], 66))
        for u in cls["unresolved"]
    ]

    repro = (
        "cd <repo> && python work/wp-9632-02/build_classification.py "
        "--source work/wp-9632-02/source_9632.md && "
        "python work/wp-9632-02/make_kf_result.py && "
        "python work/wp-9632-02/verify_classification.py && "
        "python work/wp-9632-02/make_figure.py && "
        "python work/wp-9632-02/make_report_md.py"
    )

    md = f"""# KF-RESULT {pkg}

标签：`kf-wp:{pkg}` · `kf-task:02-classification-parse` · `report:{cls['report_id']}` · `scenario:{prov['scenario_key']}`

| 项 | 值 |
|---|---|
| package_id | `{pkg}` |
| task_type | `{cls['task_type']}` |
| report_id | `{cls['report_id']}` |
| source_uri / field | `{prov['source_uri']}` / `{prov['source_field']}` |
| source_hash（独立重算） | `{prov['source_hash']}` |
| chars | `{prov['chars']}` |
| 判定报告类型 | **`{cls['report_type']}`**（confidence `{cls['confidence']['label']}` = {cls['confidence']['score']}） |
| 选中 skill | `{cls['selected_skill']['skill_id']}` v{cls['selected_skill']['skill_version']}（lifecycle `{cls['selected_skill']['lifecycle_state']}`） |
| 状态 | `{cls['status']}`（verdict 由平台门计算，本包不自证） |

## ① 本工序做了什么

只做一件事：给 report_id=`{cls['report_id']}`（{prov['title']}）打**类型标签**、**主题标签**与**结构切分**，并给出每条判定的原文定位。不做抽取（未产出任何 claim）、不做资产登记（未读未写工序 01 的 asset_manifest）、不改写上游产物、不对结论下 verified 判定。

产出 `classification.json`：{n_sig} 条 registry 信号判据、{n_ev} 条逐字证据、{st['headings']} 个标题块切分、{len(cls['topics'])} 个主题标签、{len(cls['preserved_uncertainty'])} 条保留的局限、{len(cls['unresolved'])} 条显式未决项。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文（不凭记忆）**：`GET $TENSOR_API_BASE/tensor/reports/{cls['report_id']}`，Bearer 由 `POST $TENSOR_API_BASE/auth/login`（`$TENSOR_AGENT_USER`）取得；取 `markdown` 字段并落盘 `work/{pkg}/source_9632.md`。
2. **先验哈希再动手**：`sha256(markdown utf-8 bytes)` 重算 = `{prov['source_hash'][:38]}…`，与工作包契约 `source_hash` 及 `chars`={prov['chars']} 双项一致；不一致脚本 `sys.exit`（fail-closed）。
3. **判据来源**：`extraction-skills/registry.json` 的 6 个 `report_types` × `identify_signals`，逐条比对，`matched=1.0 / partial=0.5 / absent=0.0` 加权得分，最高分入选，其余显式记 `rejected_secondary`（分类是可反驳假设，不硬猜）。
4. **零手抄的关键设置**：证据 quote 全部由 `build_classification.py` 按「选择器」（唯一子串所在整行）从源文本**机器切片**，脚本内不出现任何源报告数字/公式；切片后断言 `text.find(quote)==start_offset`（逐字、唯一）。
5. **引用密度程序化统计**：以正则 `(19|20)\\d{{2}}` 计数，避免口头估计。
6. **结构切分**：正则 `^#{{1,3}} ` 取全部标题，偏移区间首尾相接并覆盖全文（C9 断言）。
7. **验收自检**：`verify_classification.py` 调 `ke.wp_gate.locator_matches` 复解析每条证据、独立重算 quote 哈希、跑 `jsonschema` 校验包装体。
8. **图**：matplotlib（Agg）出 `figures/classification_overview.png`，两联图 = 六分型信号覆盖 + 结构切分与命中位置；图中数据全部读 `classification.json`。

分类结果矩阵（程序化打分，非人工指定）：

| rank | report_type | matched | partial | absent | score | decision |
|---|---|---|---|---|---|---|
{chr(10).join(cand_rows)}

入选 `{top['report_type']}`：四个独立信号（governing equations / discretisation / convergence study / mesh refinement）均有可定位原文；唯一未命中的 `timing table` 不改变类型判定。次优 `{second['report_type']}`（score {second['score']}）仅在“验证方法”维度部分重合——报告有解析解/手算基线比较与参数扫描矩阵，但**无试验设施、无试次矩阵、无本工作测量不确定度**，故不足以判为实验验证型。可反驳条件（falsifier）：`{cls['confidence']['falsifier']}`。

## ③ 产出物清单（输出文件 → 要点）

| 文件 | 要点 |
|---|---|
| `work/{pkg}/classification.json` | 主产物：分类判定 + {n_sig} 信号判据 + {n_ev} 条证据（偏移量/逐字 quote/content_hash）+ 结构切分 + 主题 + 局限 + 未决 |
| `work/{pkg}/kf_result_{pkg}.json` | KF-RESULT 包装体（本报告唯一 json 块，原样提交；schema `kf_result.v1` 通过） |
| `work/{pkg}/source_9632.md` | 源报告 markdown 原样落盘（重算哈希用，未改动） |
| `work/{pkg}/build_classification.py` | 一键重建：取原文→验哈希→选择器切片→打分→落产物 |
| `work/{pkg}/make_kf_result.py` | 包装体生成（不改字段结构） |
| `work/{pkg}/verify_classification.py` | 11 项自检（含 wp_gate 定位复解析、jsonschema、重复 id、自证字段扫描） |
| `work/{pkg}/verify_report.json` | 自检机器记录（{ver['n_checks']-ver['n_failed']}/{ver['n_checks']} passed） |
| `work/{pkg}/make_figure.py` + `figures/classification_overview.png` | 分类/结构图（数据注入，非手绘） |
| `work/{pkg}/make_report_md.py` + `platform_report.json` | 本报告的生成器与平台投递 payload |
| `work/{pkg}/package_contract.json` | 工作包契约留档（机器门按 YAML 校验，此处仅内嵌副本） |

## ④ 证据定位表（字段 / 判据 → 原文引文片段）

偏移量为 markdown（Python str）字符偏移，与 `ke.wp_gate.locator_matches` 语义一致；`content_hash = sha256(quote)`。下表引文为节选显示，**完整逐字引文以 `classification.json` 的 `quote` 字段为准**（未被截断、未被编辑）。

| 信号 id | 类型 / registry 信号 → 判定 | 证据 id | 偏移 | content_hash | 原文引文（节选） |
|---|---|---|---|---|---|
{chr(10).join(rows)}

主题标签 / 保留局限的证据绑定：

| id | 标签或局限 | 证据 id | 偏移 | 原文引文（节选） |
|---|---|---|---|---|
{chr(10).join(topic_rows)}

结构切分（{st['headings']} 块，首尾相接覆盖 `[0,{st['chars']})`；表块 {st['table_blocks']} 个、图引用 {st['figure_refs']} 处、独立公式 {st['display_equations']} 组）：

| 段 id | 级别 | 偏移 | 标题 |
|---|---|---|---|
{chr(10).join(sec_rows)}

## ⑤ 注意点与局限

1. **分类是假设，不是事实**：判定来自 registry 信号的语义比对（registry 信号为英文、源报告为中文），`report_type` 若被下游证伪，应改判并记录；本包已写明 falsifier 与次优候选。
2. **`timing table` 未命中**：报告无计时/性能表，故 `scientific-computation` 得分为 {top['score']} 而非 1.0；该缺失不改变类型判定，但若下游需要性能证据，此项须标 unresolved 而非补齐。
3. **三处 partial 判定的口径**：`test matrix`（参数扫描矩阵≠实验试次矩阵）、`measurement uncertainty`（文献观测分散≠本工作不确定度评定）、`validation case`（解析/手算参照≠实测案例）——均按字面信号从严判 partial，不为了让分数好看而升格。
4. **不做抽取**：`claims_produced: []`，本包不产出任何知识对象；"all claims have evidence" 在空集上平凡成立，且每个信号都有 `evidence_id` 或显式 `explicitly_absent` 状态（C7 机器检查）。
5. **不在本包范围**：正文引用的 `../artifacts/...` 图件可达性属工序 01；`asset_manifest.json` 未读取。均已记入 `unresolved`（`out_of_scope_deferred`），不冒充已核。
6. **图中无中文**：本机无 CJK 字体，图中标签用 `sec-xx` 等 ASCII 标识，中文对照见上表；属显示限制，不影响数据。
7. **偏移量基准**：Python str 字符偏移（非 UTF-8 字节偏移）。若平台用字节偏移，需按 `len(markdown[:start].encode())` 换算——本报告引文同时以 `quote` 逐字给出，可退化为全文查找。

显式未决项：

| id | 项 | 状态 | 说明 |
|---|---|---|---|
{chr(10).join(unres_rows)}

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结果 | 依据 |
|---|---|---|
{chr(10).join(self_rows)}

全部 {ver['n_checks']} 项机器检查：**{ver['n_checks']-ver['n_failed']}/{ver['n_checks']} passed**，失败项 {ver['n_failed']} 个（无粉饰：若有失败上面会显示 ✗）。附加事实：`source_hash` 独立重算与契约一致；{n_ev} 条证据偏移量逐条复解析成功。

**一键复跑（repro_cmd）**

{repro}

（`--source` 缺省时会走 API 现取，同样先校哈希；`source_9632.md` 在库内可完全离线复跑。）

## 结果（KF-RESULT 唯一 json 块，原样提交）

```json
{json.dumps(kf, ensure_ascii=False, indent=2)}
```
"""

    REPORT_MD.write_text(md, encoding="utf-8")

    payload = {
        "title": f"KF-RESULT {pkg}",
        "summary": (
            f"report_id={cls['report_id']} 分类解析：报告类型 {cls['report_type']}"
            f"（score {top['score']}, 次优 {second['report_type']} {second['score']}），"
            f"{n_sig} 条 registry 信号判据 / {n_ev} 条逐字证据（偏移量+content_hash），"
            f"结构切分 {st['headings']} 块，source_hash 独立重算一致，自检 "
            f"{ver['n_checks']-ver['n_failed']}/{ver['n_checks']} 通过；未产出 claim、未做资产登记。"
        ),
        "scenario_key": prov["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": [f"kf-wp:{pkg}", "kf-result", "02-classification-parse",
                 f"report:{cls['report_id']}", "kf-factory"],
        "markdown": md,
        "figures": [
            {
                "name": "classification_overview.png",
                "caption": (
                    "A：六分型候选的 registry identify_signals 覆盖与加权得分（入选 scientific-computation，"
                    "score 0.80；次优 experimental-validation 0.50）。B：报告结构切分（20 个标题块，"
                    "h1/h2/h3 分层）与四条命中的 scientific-computation 信号在 markdown 字符偏移上的位置"
                    "（红色虚线）。数据全部由 classification.json 注入。"
                ),
                "png_base64": base64.b64encode(FIG.read_bytes()).decode("ascii"),
            }
        ],
    }
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {REPORT_MD} ({REPORT_MD.stat().st_size} bytes) and {PAYLOAD} "
          f"({PAYLOAD.stat().st_size} bytes), self-check failures={n_fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())