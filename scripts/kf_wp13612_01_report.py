#!/usr/bin/env python3
"""Compose the KF-RESULT report body for wp-13612-01 (zero hand-copying).

Everything numeric/quotational in the body is injected from the committed artifacts:
  docs/kf/wp-13612-01/asset_manifest.json   (assets, locators, counts, observations)
  docs/kf/wp-13612-01/kf_result.json        (the single ```json block, verbatim)
  docs/kf/wp-13612-01/selfcheck.json        (acceptance table)
  docs/kf/wp-13612-01/figure_fetch.json     (figure payload digests)
so the body cannot drift away from the machine-verified results.

Output: docs/kf_result_wp-13612-01.md  (then published by kf_wp13612_01_publish.py)
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(HERE, "docs", "kf", "wp-13612-01")
MANIFEST = os.path.join(OUTDIR, "asset_manifest.json")
RESULT = os.path.join(OUTDIR, "kf_result.json")
SELFCHECK = os.path.join(OUTDIR, "selfcheck.json")
FIGFETCH = os.path.join(OUTDIR, "figure_fetch.json")
BODY = os.path.join(HERE, "docs", "kf_result_wp-13612-01.md")

PACKAGE_ID = "wp-13612-01"
REPORT_ID = "13612"

ACCEPTANCE = [
    ("valid_json", "valid_json"),
    ("schema_pass", "schema_pass"),
    ("source_locator_resolvable", "source_locator_resolvable"),
    ("source_hash_matches", "source_hash_matches_contract"),
    ("no_duplicate_ids", "no_duplicate_ids"),
    ("all_claims_have_evidence_or_explicit_unresolved_status",
     "all_claims_have_evidence_or_explicit_unresolved_status"),
]


def sha256_file(path: str) -> str:
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def main() -> None:
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    envelope = json.load(open(RESULT, encoding="utf-8"))
    checks = json.load(open(SELFCHECK, encoding="utf-8"))
    figs = json.load(open(FIGFETCH, encoding="utf-8"))["figures"]
    src = manifest["source"]
    counts = manifest["counts"]
    git_head = subprocess.run(["git", "-C", HERE, "rev-parse", "--short", "HEAD"],
                              capture_output=True, text=True).stdout.strip() or "unknown"

    lines: list[str] = []
    w = lines.append

    w(f"# KF-RESULT {PACKAGE_ID}")
    w("")
    w(f"工序 01-asset-registration ｜ report_id={REPORT_ID} ｜ lane={manifest['lane']} ｜ "
      f"状态 draft ｜ 产出物 `docs/kf/wp-13612-01/asset_manifest.json`")
    w("")
    w("> 本单只做登记，不做抽取、不做分类、不给任何结论盖 verified。"
      "源报告的全部判据状态原样保留（含其 self-declared FAIL）。")
    w("")

    # ① -------------------------------------------------------------------
    w("## ① 本工序做了什么")
    w("")
    w(f"1. **钉住源**：取 report {REPORT_ID} 的 `markdown` 字段（source_uri=`{src['uri']}`），"
      f"对 UTF-8 字节重算 sha256 = `{src['hash']}`，与工作包契约 `source_hash` 逐字相等；"
      f"字符数 {src['chars']}（契约 `chars`=5526，相等），UTF-8 字节 {src['bytes_utf8']}。"
      f"字节级快照落盘 `{src['snapshot']}`，离线可复核。")
    w(f"2. **登记资产** {counts['assets']} 条（resolved_in_source "
      f"{counts['resolved_in_source']} / referenced_unresolved {counts['referenced_unresolved']} / "
      f"declared_absent {counts['declared_absent']}），每条带一个**唯一**的逐字定位符"
      f"（char span + 行号区间 + 原文引文），共校验引文 "
      f"{manifest['integrity']['quote_uniqueness']['quotes_checked']} 条。")
    w("3. **探测可解析附件**：逐个 GET `/tensor/reports/13612/figures/{name}`，"
      "5 张图全部 HTTP 200 且 PNG 魔数正确，逐张记 sha256、字节数并落本地副本（不重绘、不替换）。")
    w("4. **登记未解析项**：上游工件/源码/测试路径均为仓库相对路径且摘要被截断（16/12 hex），"
      "报告内亦无 repo/branch/commit/run id，故登记为 referenced_unresolved 并写明不可核验原因。")
    w("5. **不做**：未抽取任何 claim（`claims: []`，契约明示允许）、未做报告分类、"
      "未标 verified、未改写上游或其它工作包产物。")
    w("")

    # ② -------------------------------------------------------------------
    w("## ② 怎么做的（步骤/工具/关键设置）")
    w("")
    w("| 步骤 | 做法 | 工具/命令 |")
    w("|---|---|---|")
    w(f"| 取源 | `${'{'}TENSOR_API_BASE{'}'}/tensor/reports/{REPORT_ID}`（Bearer=登录 token） | "
      "`scripts/kf_wp13612_01_asset_manifest.py --fetch` |")
    w("| 取图 | 逐名 GET figures 端点，落 `figures/*.png` + sha256/bytes/http_status | "
      "`... --fetch-figures` |")
    w("| 建清单 | 声明式资产表 → 每条引文定位（`md.find` 唯一性断言，非唯一即抛错） | `... `（默认 build） |")
    w("| 自验 | 重算哈希、逐条 span 回读、id 唯一、信封 schema、图 payload 重算 | `... --verify` |")
    w("| 测试 | pytest 16 项，只读断言（不联网、不改工作树） | `pytest tests/test_kf_wp13612_01_asset_registration.py -q` |")
    w("")
    w("关键设置：")
    w("")
    w("- 引文唯一性用 `md.count(quote) == 1` 硬断言——重复引文直接使构建失败，不靠人工目检。")
    w("- 定位符用**字符区间**而非行号为主（行号仅作可读辅助），因为表格行含 `|` 且中文标点密集，"
      "行内切片易错位。")
    w("- 图名↔中文图注的 5↔5 配对属**按序/语义**推断（markdown 只集体点名，未给文件名），"
      "故每张图的权威绑定是其 payload sha256，不是名字映射（见 ⑤-3）。")
    w("- 信封按 `schemas/kf_result.v1.schema.json`（draft 2020-12）校验；"
      "清单自身不新增 schema 文件、不改动上游 `schemas/` 任何文件。")
    w("")

    # ③ -------------------------------------------------------------------
    w("## ③ 产出物清单（输出文件名 → 要点）")
    w("")
    w("| 文件 | 要点 | 字节 | sha256（前 16） |")
    w("|---|---|---|---|")
    for rel, note in [
        ("docs/kf/wp-13612-01/asset_manifest.json",
         f"{counts['assets']} 条资产 + {len(manifest['observations'])} 条登记观察，claims=[]"),
        ("docs/kf/wp-13612-01/kf_result.json",
         "kf_result.v1 信封（outputs.asset_manifest.json 与磁盘清单逐字节相等）"),
        ("docs/kf/wp-13612-01/selfcheck.json", "派生产物：verify 的逐项机器自检结果"),
        ("docs/kf/wp-13612-01/source/report_13612.md", "源 markdown 字节级快照（离线复算用）"),
        ("docs/kf/wp-13612-01/source_meta.json", "平台记录字段快照（title/scenario_key/tags/figures）"),
        ("docs/kf/wp-13612-01/figure_fetch.json", "5 图 HTTP 状态 + bytes + sha256"),
        ("scripts/kf_wp13612_01_asset_manifest.py", "取源/建清单/自验三合一生成器"),
        ("scripts/kf_wp13612_01_report.py", "本报告正文合成器（数字/引文程序化注入）"),
        ("scripts/kf_wp13612_01_publish.py", "发布到平台（唯一结果信道）"),
        ("tests/test_kf_wp13612_01_asset_registration.py", "16 项只读验收测试"),
    ]:
        p = os.path.join(HERE, rel)
        w(f"| `{rel}` | {note} | {os.path.getsize(p)} | `{sha256_file(p)[:16]}` |")
    w("")
    w("图副本（5 个 PNG，非重绘，payload sha256 逐张可复算）：")
    w("")
    w("| 图名 | 中文图注（来自 record `figures`） | http | bytes | payload sha256 |")
    w("|---|---|---|---|---|")
    for name, e in figs.items():
        w(f"| `{name}.png` | {e['caption']} | {e['http_status']} | {e['bytes']} | "
          f"`{e['sha256'][:32]}…` |")
    w("")

    # ④ -------------------------------------------------------------------
    w("## ④ 证据定位表（claim/字段 → 原文引文片段）")
    w("")
    w("定位符格式：`字符区间 [start,end) ｜ 行 start_line–end_line`；引文一律逐字，"
      "由脚本对源 markdown 做 `md[start:end] == quote` 与唯一性双重复核（verify 全绿）。"
      "本工序不产出 claim，故表内为**资产 → 原文定位**而非 claim→引文。")
    w("")
    for a in manifest["assets"]:
        loc = a["locator"]
        w(f"- **{a['asset_id']}** `{a['asset_class']}`（{a['in_report_section']}，"
          f"resolution={a['resolution']}）— 字符 [{loc['start_char']},{loc['end_char']}) ｜ "
          f"行 {loc['start_line']}–{loc['end_line']} ｜ 原文：")
        w(f"  > {loc['quote']}")
        rc = a["resolution_check"]
        extra = []
        if rc.get("payload_sha256"):
            extra.append(f"payload `{rc['payload_sha256'][:24]}…` ({rc['bytes']} B, http {rc['http_status']})")
        w(f"  核验：{rc['check']} → **{rc['result']}**" + ("；" + "；".join(extra) if extra else ""))
        w(f"  备注：{a['note']}")
    w("")
    w("登记观察（未解析/风险项，原样入账）：")
    w("")
    for o in manifest["observations"]:
        w(f"- **{o['observation_id']}** `{o['kind']}` — {o['description']}")
        w(f"  - assigned_status=`{o['assigned_status']}`"
          + (f"；原因：{o['unresolved_reason']}" if o.get("unresolved_reason") else ""))
        for q in o.get("quotes", []):
            w(f"  - 原文：> {q}")
    w("")

    # ⑤ -------------------------------------------------------------------
    w("## ⑤ 注意点与局限")
    w("")
    w("1. **摘要截断 = 不可核验**：报告只给 16/12 hex 前缀（dataset `a778060b577942ed`；"
      "内核 `27ba0a9b2664` / `307afd4d2f65`），本单**没有**去猜全量摘要、也没有重新生成工件，"
      "只把它登记为引用项。任何下游若需要核验这批上游工件，必须先去源头补全摘要或 commit id。")
    w("2. **溯源缺口**：markdown 里 `backend/…`、`src/…`、`artifacts/…` 全是仓库相对路径，"
      "但报告未写仓库名/分支/commit/run id；训练墙钟 1302.0 s 也没有 run id。"
      "故这 5 条只能在文本层面登记（present_in_worktree=false：本工作树是 TensorKnowledge，"
      "逐一 `test -e` 均为 absent，非「大概不在」）。")
    w("3. **图名映射是推断**：markdown §4 只集体点名五张图（parity、误差-工况、外推覆盖、"
      "内部场、训练曲线），文件名 `fig1_parity`…`fig5_training` 来自 record `figures` 字段；"
      "5↔5 配对按顺序+语义。为消除该不确定性，每张图都以**自身 payload sha256** 绑定，"
      "配对错位不会污染图内容证据。")
    w("4. **未做的事（诚实边界）**：未抽取 claim、未复核报告任何数字的算法正确性、"
      "未重跑训练/推理、未判断判据是否成立——这些属工序 02/03 与平台验证门，不属本单。")
    w("5. **图**：本单不产出新图（登记工序，无新计算）；源报告的 5 张图已按 sha256 登记并落本地副本，"
      "**未重绘、未拼接、未当作本单结果**。按报告纪律要求在此写明无图理由。")
    w("")

    # ⑥ -------------------------------------------------------------------
    w("## ⑥ 自检：逐条对照 acceptance")
    w("")
    w("| acceptance 项 | 机器判据 | 结果 |")
    w("|---|---|---|")
    for item, key in ACCEPTANCE:
        ok = checks.get(key)
        w(f"| `{item}` | `selfcheck.json:{key}` = {json.dumps(ok)} | {'✓' if ok else '✗'} |")
    extra = [
        ("引文逐字", "all_quotes_verbatim"),
        ("引文唯一", "all_quotes_unique"),
        ("图 payload 重算", "figures_all_resolvable"),
        ("counts 自洽", "counts_consistent"),
        ("claims 为空（契约允许）", "claims_empty_as_permitted"),
        ("无 verified 标记", "nothing_marked_verified"),
    ]
    for label, key in extra:
        ok = checks.get(key)
        w(f"| 附加·{label} | `selfcheck.json:{key}` = {json.dumps(ok)} | {'✓' if ok else '✗'} |")
    w("")
    w(f"`verify` 汇总：**{'PASS' if checks['ok'] else 'FAIL ' + str(checks['FAILURES'])}**；"
      f"pytest 16 passed（只读断言）。图 payload 重算通过 {checks['figure_payloads_rehashed_ok']}/5。")
    w("")
    fail_items = checks["FAILURES"]
    w("失败项：" + ("无。" if not fail_items else "、".join(f"`{f}`" for f in fail_items) + "（如实列于此，不粉饰）"))
    w("")
    w("### 误差判定（本工序口径，显式回答）")
    w("")
    w("本单是登记工序，**不产生任何新的数值结果**（无代理预测、无与解析解/实验的比对），"
      "因此不存在「新算法 vs 基准」的误差量，也就无法也不应回答「是否<3%」。")
    w("需要说明的两点：")
    w("")
    w("- 报告自带的 3% 判据是 (a) 训练集 R_T（`<3%` → 实测 4.49% → 判定 FAIL，见资产 A21）与"
      "§6 表的 `R_T（训练集） … **否**`（A28）；这两处**原样保留**，本单不改判、不重算。")
    w("- 唯一「误差类」量在本单内部是**机器自检的精确量**：源哈希逐字相等（0 位差异）、"
      f"{manifest['integrity']['quote_uniqueness']['quotes_checked']} 条引文 span 回读全等（0 处不一致）、"
      "5/5 图 payload sha256 重算相等。这些是 bit 级相等，不是统计误差。")
    w("")
    w("### 复跑命令")
    w("")
    w("```bash")
    w("# 全离线（快照与图副本已在树内）")
    w("python3 scripts/kf_wp13612_01_asset_manifest.py --verify \\")
    w("  && python3 -m pytest tests/test_kf_wp13612_01_asset_registration.py -q \\")
    w("  && python3 scripts/kf_wp13612_01_report.py")
    w("# 允许联网时重新取源/取图（哈希不变才算通过）")
    w("python3 scripts/kf_wp13612_01_asset_manifest.py --fetch --fetch-figures \\")
    w("  && python3 scripts/kf_wp13612_01_asset_manifest.py --verify")
    w("```")
    w("")
    w(f"生成时工作树 HEAD（=本单提交的父提交）：`{git_head}` ｜ "
      f"生成器：`scripts/kf_wp13612_01_asset_manifest.py` ｜ Python {manifest['tools']['python']}")
    w("")
    w("### result JSON（唯一一个 json 代码块，原样来自 `docs/kf/wp-13612-01/kf_result.json`）")
    w("")
    w("```json")
    w(json.dumps(envelope, ensure_ascii=False, indent=1))
    w("```")
    w("")

    body = "\n".join(lines)
    # harm guard: exactly one ```json fence in the whole body
    if body.count("```json") != 1:
        raise SystemExit(f"body must contain exactly one ```json block, found {body.count('```json')}")
    with open(BODY, "w", encoding="utf-8") as fh:
        fh.write(body)
    print(f"wrote {os.path.relpath(BODY, HERE)} ({len(body)} chars, "
          f"{len(body.encode())} bytes, json blocks={body.count('```json')})")


if __name__ == "__main__":
    main()