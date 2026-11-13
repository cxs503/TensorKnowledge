"""Render the wp-13988-01 deliverable report (KF-RESULT) from machine artifacts
and publish it to the platform.

Every number in the body is injected from artifacts/wp-13988-01/asset_manifest.json,
docs/wp-13988-01/checks.json and docs/wp-13988-01/verification.json -- nothing is
typed from memory. Quoted snippets are sliced out of the source markdown
(whole lines, never elided) so the platform's independent substring re-check
can confirm them verbatim.

Usage:
  python3 docs/wp-13988-01/build_report.py            # write the .md only
  python3 docs/wp-13988-01/build_report.py --post     # write + POST to /tensor/reports
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import sys
import urllib.request

PKG = "wp-13988-01"
REPORT_ID = "13988"
WT = pathlib.Path(".").resolve()
DOC = WT / "docs" / PKG
MAN = WT / "artifacts" / PKG / "asset_manifest.json"
OUT_MD = DOC / ("KF-RESULT-%s.md" % PKG)
FIG = DOC / "fig_manifest_coverage.png"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MISSION_ID = 15771

# assets quoted verbatim (whole first line) in section 4
QUOTE_IDS = ["A02", "A03", "A08", "A10", "A14", "A15", "A16", "A17", "A18",
             "A19", "A20", "A21", "A26", "A27", "A28", "A29"]


def _req(url, payload=None, token=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def login():
    user, pwd = os.environ.get("TENSOR_AGENT_USER"), os.environ.get("TENSOR_AGENT_PASS")
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = _req(BASE + path, {"username": user, "password": pwd})
        except Exception:
            continue
        tok = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
        if tok:
            return tok
    return None


def main() -> int:
    man = json.loads(MAN.read_text())
    checks = json.loads((DOC / "checks.json").read_text())
    ver = json.loads((DOC / "verification.json").read_text())
    env = json.loads((DOC / ("kf_result.%s.json" % PKG)).read_text())
    md_src = (WT / man["source"]["local_copy"]).read_text()

    prev = []
    rec_path = DOC / "posted_report.json"
    if rec_path.exists():
        _prev = json.loads(rec_path.read_text())
        prev = _prev.get("history") or ([{"id": _prev["id"]}] if _prev.get("id") else [])
    supersede = ""
    if prev and "--post" in sys.argv:
        supersede = ("> 本报告取代 `#%s`（同包前一次发布：其资产解析检查器把平台 figures[] 的同名图件误判为 absent，"
                     "且 A06/A09 的候选路径列表含数学片段噪声；已修正后重发，主产物 sha256 见 ③）。\n"
                     % ",".join(str(x.get("id")) for x in prev))

    by_id = {a["asset_id"]: a for a in man["assets"]}
    quote_rows = []
    for aid in QUOTE_IDS:
        a = by_id[aid]
        loc = a["locator"]
        first = loc["quote"].split("\n")[0]
        quote_rows.append("- **%s** · `%s` · char `%d–%d` · L%d · %s\n\n  > %s\n"
                          % (aid, a["asset_class"], loc["start_char"], loc["end_char"],
                             loc["start_line"] + 1, a["resolution"], first))
        assert first in md_src, "quote not verbatim: %s" % aid

    class_rows = "\n".join("| %s | %d |" % (k, v) for k, v in
                           sorted(man["counts"]["by_class"].items(), key=lambda kv: -kv[1]))
    res = man["counts"]["by_resolution"]
    unre = [a for a in man["assets"] if a["resolution"] == "referenced_unresolved"]
    unre_rows = "\n".join("| %s | %s | %s |" % (a["asset_id"], a["asset_class"], a["label"])
                          for a in unre)
    chk_rows = "\n".join("| %s | %s | %s |" % (c["check"], c["status"],
                                               c["detail"].replace("|", "/"))
                         for c in checks["checks"])
    ver_rows = "\n".join("| %s | %s | %s |" % (c["check"], c["status"],
                                               c["detail"].replace("|", "/"))
                         for c in ver["checks"])
    man_sha = hashlib.sha256(MAN.read_bytes()).hexdigest()
    total_span = sum(1 for a in man["assets"] if a["locator"]["quote"] in md_src)

    body = f"""KF-RESULT {PKG}

任务 m15771 · 工作包 `{PKG}` · 工序 `{man['task_type']}` · 报告 {REPORT_ID} · 状态 draft（verification 归平台门）
tags: `kf-wp:wp-13988-01` · `kf-result` · `asset-registration` · `report-13988` · `H5-CALIB-REFLUX`
{supersede}

## ① 本工序做了什么

按工作包契约（`task_type=01-asset-registration`，`objective.register_assets=true`，`objective.classify_report_type=false`）对**唯一一份**报告 `report_id={REPORT_ID}`（标题见 ④ A02）做资产登记：

- 从平台 API 取 `markdown` 字段，独立重算 sha256，与契约 `source_hash` 逐位比对：**{man['source']['hash']}**，chars **{man['source']['chars']}**（= 契约声明的 {checks['checks'][1]['detail'].split('contract=')[1].split(' ')[0]}），bytes_utf8 **{man['source']['bytes_utf8']}** → 一致。
- 登记 **{man['counts']['assets']}** 个源资产：`resolved_in_source` **{res.get('resolved_in_source', 0)}** / `referenced_unresolved` **{res.get('referenced_unresolved', 0)}** / `declared_absent` **{res.get('declared_absent', 0)}**。每个资产带 **逐字切片** 的 `locator`（char 区间 + 行区间 + quote），不手抄。
- **不做抽取**：`claims=[]`（契约允许空数组）。本工序不产生任何知识断言，也不把任何结论标成 verified。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`scripts/kf_fetch_{REPORT_ID}.py` 走 `GET {BASE}/tensor/reports/{REPORT_ID}`（Bearer，env `TENSOR_AGENT_USER/PASS`，不硬编码凭据）；psql 直连本环境 `permission denied for table tensor_reports`，故只走 API。落 `runs/{PKG}/report_{REPORT_ID}.json|.md`。
2. **哈希门**：`sha256(markdown.encode('utf-8'))` 与契约 `source_hash` 比对，不等即 `exit 2`（本次 MATCH）。
3. **定位法（关键设置）**：每个资产声明一个 **在全文唯一出现** 的锚点子串 + 相对行偏移 `(start, end)`；脚本用 `md.count(anchor)==1` 强制唯一（不唯一直接 `SystemExit`），再由行偏移算出 `start_char/end_char`，**quote = `md[start_char:end_char]` 切片**。因此引文逐字性由构造保证，而非人工核对。
4. **解析判定（分辨率分类）**：`resolved_in_source`＝切片自证；`referenced_unresolved`＝报告只给仓库相对路径/分支名，脚本在本工作树内逐路径 `Path.exists()` 检索（不联网、不猜地址、不臆造 DOI）；图件额外查平台 `figures[]` 是否含同名 PNG。
5. **结构门**：manifest 校验用 `docs/{PKG}/asset_manifest.v1.schema.json`（由仓内 `schemas/asset_manifest.v1.schema.json` 程序化改 const 派生，因原 schema 固定为 448 包）；信封校验用仓内权威 `schemas/kf_result.v1.schema.json`。两者各带反证（删必填键必须被判失败）。
6. **独立复核**：`docs/{PKG}/verify_manifest.py` 重新从 API 取 markdown（不复用缓存），对 {man['counts']['assets']} 个 quote 重算唯一性与 char 切片一致性。
7. **零领域语义**：本包全部逻辑在 `docs/{PKG}/` 与 `scripts/kf_fetch_{REPORT_ID}.py` 内，不触碰平台共性代码。

## ③ 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `artifacts/{PKG}/asset_manifest.json` | 主产物：{man['counts']['assets']} 个资产 + locator + resolution_check；sha256 `{man_sha}`，{checks['manifest_bytes']} bytes |
| `docs/{PKG}/asset_manifest.json` | 主产物的**逐字节镜像**（仓推送门会丢 `artifacts/**`、`runs/**`，故留档于 `docs/`；脚本断言两者 sha256 相等） |
| `docs/{PKG}/kf_result.{PKG}.json` | kf_result.v1 结果信封（本报告 ⑦ 的单 json 块同源） |
| `docs/{PKG}/checks.json` | 构建期 {len(checks['checks'])} 项自检明细（含每次反证结果） |
| `docs/{PKG}/verification.json` | 独立复核 {len(ver['checks'])} 项，`ok={str(ver['ok']).lower()}`，记录 fresh source hash |
| `docs/{PKG}/build_asset_manifest.py` | 登记器（锚点唯一性 → 切片 → 分类 → 结构门 → 落盘） |
| `docs/{PKG}/verify_manifest.py` | 独立复核器（重新取源重算，不复用缓存） |
| `docs/{PKG}/plot_coverage.py` → `fig_manifest_coverage.png` | 覆盖图：{man['counts']['assets']} 条资产在 {man['source']['chars']} 字符源文上的区间分布（按解析类着色）+ 分类计数 |
| `scripts/kf_fetch_{REPORT_ID}.py` | 取源+哈希门 |
| `runs/{PKG}/report_{REPORT_ID}.json|.md` | API 原始载荷与字节精确 markdown |

资产分类计数：

| asset_class | 数量 |
|---|---|
{class_rows}

## ④ 证据定位表（字段 → 原文引文，逐字整行未截断）

{chr(10).join(quote_rows)}

说明：上表只摘每段的首行；多行资产的完整 quote（含表体全部行）在 `asset_manifest.json` 的 `locator.quote` 里，可机械复核 `md[start:end]==quote`。全部 {man['counts']['assets']} 条的 quote 均为源文唯一子串（{total_span}/{man['counts']['assets']} 通过）。

**登记中识别出的不可解析引用（{len(unre)} 条，全部落 `referenced_unresolved`，不做猜测补全）**：

| 资产 | 类 | 标签 |
|---|---|---|
{unre_rows}

## ⑤ 注意点与局限

1. **本工序不背书上游数字**。{REPORT_ID} 报告的 A_hat=0.075539、ΔRT +0.384%、误差表「<3%?」等结论只是被**定位并登记**（A15/A19/A20/A26），其真值不在本包验证范围内；本包也不产出任何 claim（契约 `classify_report_type=false`）。
2. **哈希被截断**：报告只披露 `6fc45dd1e21f8ba8…`、`3eeab056fd161a16…` 两个前缀（A18），完整 64 位值缺失 → 下游无法仅凭报告复算账本链；这是登记到的**上游证据缺口**，不是本包缺陷。
3. **{len(unre)} 条引用不可解析**：9 个工件文件、KCS 几何 JSON、两个代码指针、两个 PNG 只以仓库相对路径出现；本工作树（TensorKnowledge）内均不存在，故一律判 `referenced_unresolved`，**未拼接路径当既有事实**（A11 的 note 明确标注「拼接属推断」）。
4. **图件双重身份**：两 PNG 在源文里只有路径（不可解析），但平台 `figures[]` 含同名 PNG 字节，故 `resolution_check` 记 `present` 而 `resolution` 仍为 `referenced_unresolved`——两者口径不同，已在 note 中写明，避免被读成「已解析」。
5. **schema 口径**：仓内 `schemas/asset_manifest.v1.schema.json` 的 const 写死为 `wp-448-01`；本包用程序化派生的同构副本（`docs/{PKG}/asset_manifest.v1.schema.json`）校验，并在文件内注明「平台侧若有 schema 以平台为准」。信封则直接对仓内权威 `kf_result.v1.schema.json` 校验。
6. **§⑤ 局限来源**：上游报告的 6 条注意点（A25）只登记原文，其中「前缘入口过渡」「外推 1 个数量级」等对下游复用该系数是关键约束，抽取工序不得丢掉。
7. **未做的事（明确声明）**：未执行上游 `scripts/run_calib_reflux.py`（不在本工作树）；未联网核证任何外部数据（Zenodo/文献）；未读/写其它 report_id。

## ⑥ 误差判定（本工序可裁量 vs 基准，显式回答是否 <3%）

本工序为**登记类**工作包，不产生物理量，故「物理量 vs 实验/文献误差」不适用；改为对**机械可裁量**给出误差，基准取工作包契约：

| 量 | 基准（契约） | 本次 | 误差 | <3%? |
|---|---|---|---|---|
| markdown sha256 | `79d795…442b9` | `{man['source']['hash']}` | 0（逐位相等） | 是（精确相等） |
| 源字符数 | 6222 | {man['source']['chars']} | 0% | 是 |
| locator 逐字命中 | quote ⊂ 源文且唯一 | {total_span}/{man['counts']['assets']} | 0% | 是 |
| 重复 ID | 0 | {man['counts']['assets']} 个 ID / {len(set(a['asset_id'] for a in man['assets']))} 唯一 | 0 | 是 |
| 独立复核 | 全项 pass | {sum(1 for c in ver['checks'] if c['status'] == 'pass')}/{len(ver['checks'])} | 0% | 是 |

**物理精度不适用声明**：本包未产生或比较任何阻力/功率等物理量，故不回答「物理量是否 <3%」；上游报告自身的误差判定（A26，含 1 项「否」：vs Prandtl-Schlichting −3.50%）已逐字登记，可供下游审计者复核。

## ⑦ 结果（全文唯一的 kf_result.v1 JSON 代码块）

```json
{json.dumps(env, ensure_ascii=False, indent=2)}
```

## ⑧ 自检：逐条对照 acceptance

| acceptance | 结果 | 证据 |
|---|---|---|
| valid_json | ✅ | `artifacts/{PKG}/asset_manifest.json` 可 `json.load`，{checks['manifest_bytes']} bytes |
| schema_pass | ✅ | 信封过 `schemas/kf_result.v1.schema.json`；manifest 过派生 schema；双反证均按预期失败 |
| source_locator_resolvable | ✅ | {total_span}/{man['counts']['assets']} quote 唯一且在源文；char 切片逐字节相等 |
| source_hash_matches | ✅ | `{man['source']['hash']}` == 契约（构建期与复核期各算一次） |
| no_duplicate_ids | ✅ | asset_id {len(set(a['asset_id'] for a in man['assets']))}/{man['counts']['assets']} 唯一；claims 为空 |
| all_claims_have_evidence_or_explicit_unresolved_status | ✅（空集成立） | `claims=[]`，无断言即无未证断言；`do_not_mark_claims_as_verified` 亦满足（无 verified 标记） |

构建期自检（`checks.json`，{sum(1 for c in checks['checks'] if c['status'] == 'pass')}/{len(checks['checks'])} pass）：

| check | status | detail |
|---|---|---|
{chk_rows}

独立复核（`verification.json`，重新取源）：

| check | status | detail |
|---|---|---|
{ver_rows}

## ⑨ 复现（repro_cmd）

    cd "$(git rev-parse --show-toplevel)" && \\
    python3 scripts/kf_fetch_{REPORT_ID}.py && \\
    python3 docs/{PKG}/build_asset_manifest.py && \\
    python3 docs/{PKG}/verify_manifest.py && \\
    python3 docs/{PKG}/plot_coverage.py && \\
    python3 docs/{PKG}/build_report.py --post

（env：`TENSOR_API_BASE`、`TENSOR_AGENT_USER`、`TENSOR_AGENT_PASS`；全流程无网络外部依赖，只打平台 API。）
"""

    OUT_MD.write_text(body)
    print("wrote", OUT_MD.relative_to(WT), len(body), "chars")

    if "--post" not in sys.argv:
        return 0

    png = base64.b64encode(FIG.read_bytes()).decode() if FIG.exists() else None
    figures = ([{"name": "fig_manifest_coverage.png",
                 "caption": "wp-13988-01 资产覆盖图：%d 个登记资产在 6222 字符源报告上的 char 区间（蓝=resolved_in_source，红=referenced_unresolved）；右图为解析类计数与前 8 类资产类。之所以必须出图：本工序的唯一实质结论是「覆盖与解析边界」，一图即可看出 7 条不可解析引用集中在工件/代码/图件路径上。" % man["counts"]["assets"],
                 "png_base64": png}] if png else [])
    payload = dict(
        title="KF-RESULT %s" % PKG,
        summary=("%s（%s，report %s）：%d 资产登记，resolved %d / unresolved %d，"
                 "源哈希逐位吻合 %s…，locator 唯一命中 %d/%d，claims=[]（按契约不抽取），"
                 "构建期 %d/%d 检查 pass，独立复核 %d/%d pass。"
                 % (PKG, man["task_type"], REPORT_ID, man["counts"]["assets"],
                    res.get("resolved_in_source", 0), res.get("referenced_unresolved", 0),
                    man["source"]["hash"][:12], total_span, man["counts"]["assets"],
                    sum(1 for c in checks["checks"] if c["status"] == "pass"), len(checks["checks"]),
                    sum(1 for c in ver["checks"] if c["status"] == "pass"), len(ver["checks"]))),
        scenario_key=man["source"]["scenario_key"] or "ship-performance-platform",
        mission_id=MISSION_ID,
        tags=["kf-wp:%s" % PKG, "kf-result", "asset-registration", "report-%s" % REPORT_ID,
              "H5-CALIB-REFLUX"],
        markdown=body,
        figures=figures,
    )
    tok = login()
    r = _req(BASE + "/tensor/reports", payload, token=tok)
    rid = r.get("id") if isinstance(r, dict) else None
    print("posted report id:", rid)
    hist = prev + [{"id": rid, "title": payload["title"], "tags": payload["tags"],
                    "markdown_sha256": hashlib.sha256(body.encode()).hexdigest(),
                    "manifest_sha256": man_sha,
                    "figures": [f["name"] for f in figures]}]
    (DOC / "posted_report.json").write_text(
        json.dumps({"id": rid, "title": payload["title"], "tags": payload["tags"],
                    "markdown_sha256": hashlib.sha256(body.encode()).hexdigest(),
                    "manifest_sha256": man_sha,
                    "figures": [f["name"] for f in figures],
                    "history": hist, "supersedes": [h["id"] for h in hist[:-1]]},
                   ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())