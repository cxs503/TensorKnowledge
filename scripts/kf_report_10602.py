"""Build and publish the mission report for work package wp-10602-01 (report 10602).

Zero hand-copy: every number in the prose, the asset inventory table, the evidence-locator table, the
self-check table and the fenced result block are formatted from the manifest / envelope / the verifier's
own output at build time. The only literal text is the prose itself.

  * writes docs/wp-10602-01/KF-RESULT-wp-10602-01.md  (report body, exactly one fenced json block)
  * embeds docs/wp-10602-01/fig1_asset_coverage.png as base64
  * POSTs to the platform /tensor/reports (title 'KF-RESULT wp-10602-01', tags kf-wp:wp-10602-01,
    mission_id 15686) unless --no-post is given

Usage: python3 scripts/kf_report_10602.py [--no-post]
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import subprocess
import sys
import urllib.request

PACKAGE_ID = "wp-10602-01"
REPORT_ID = "10602"
MISSION_ID = 15686
DOCS = pathlib.Path("docs/wp-10602-01")
MANIFEST = json.loads((DOCS / "asset_manifest.json").read_text())
ENVELOPE = json.loads((DOCS / "kf_result.wp-10602-01.json").read_text())
FIG = DOCS / "fig1_asset_coverage.png"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")

C = MANIFEST["counts"]
S = MANIFEST["source"]
I = MANIFEST["integrity"]
ASSETS = MANIFEST["assets"]


def verifier_lines() -> list[str]:
    """Run the independent verifier (fresh API fetch) and return its PASS/FAIL lines."""
    out = subprocess.run([sys.executable, "scripts/kf_verify_10602.py"],
                         capture_output=True, text=True)
    lines = [ln for ln in out.stdout.splitlines() if re.match(r"^(PASS|FAIL)\s", ln)]
    if not lines:
        sys.exit("verifier produced no verdict lines:\n" + out.stdout + out.stderr)
    return lines


def inventory_table() -> str:
    rows = ["| asset_id | asset_class | resolution | 位置（char span / line） | label |",
            "|---|---|---|---|---|"]
    for a in ASSETS:
        loc = a["locator"]
        pos = ("0-%d（全文）" % loc["end_char"]) if loc["method"] == "document" \
            else "%d-%d / L%d-%d" % (loc["start_char"], loc["end_char"], loc["start_line"], loc["end_line"])
        rows.append("| %s | %s | %s | %s | %s |" % (
            a["asset_id"], a["asset_class"], a["resolution"], pos,
            a["label"].replace("|", "\\|")))
    return "\n".join(rows)


def evidence_table() -> str:
    rows = ["| 登记项（asset_id / 字段） | 原文引文片段（逐字，单行前缀） | char span | 解析结果 |",
            "|---|---|---|---|"]
    for a in ASSETS:
        loc = a["locator"]
        qlines = loc["quote"].split("\n")
        q = qlines[0].replace("|", "\\|").strip()
        if len(q) > 70:
            q = q[:70] + "…"
        if len(qlines) > 1:
            q += " ⟨+%d 行⟩" % (len(qlines) - 1)
        span = "0-%d" % loc["end_char"] if loc["method"] == "document" else "%d-%d" % (
            loc["start_char"], loc["end_char"])
        rows.append("| %s | %s | %s | %s/%s |" % (
            a["asset_id"], q, span, a["resolution"], a["resolution_check"]["result"]))
    return "\n".join(rows)


def probe_table() -> str:
    rows = ["| asset_id | 引用路径（原文） | 探测根 | 结果 |", "|---|---|---|---|"]
    for a in ASSETS:
        chk = a["resolution_check"]
        if "probe" not in chk:
            continue
        roots = "<br>".join("%s → exists=%s" % (p["path"], p["exists"]) for p in chk["probe"])
        rows.append("| %s | %s | %s | %s |" % (
            a["asset_id"], str(chk.get("searched", "")).replace("|", "\\|"), roots, chk["result"]))
    return "\n".join(rows)


def build_markdown() -> str:
    vlines = verifier_lines()
    vtable = "\n".join(
        "| %s | %s |" % (ln.split()[0],
                          re.sub(r"\s{2,}", " ", ln.split(None, 1)[1]).replace("|", "\\|"))
        for ln in vlines)
    all_pass = all(ln.startswith("PASS") for ln in vlines)
    fig64 = base64.b64encode(FIG.read_bytes()).decode()
    result_json = json.dumps(ENVELOPE, ensure_ascii=False, indent=2)

    md = f"""# KF-RESULT {PACKAGE_ID}

**工序** 01-asset-registration ｜ **report_id** {REPORT_ID} ｜ **package_id** {PACKAGE_ID} ｜ **lane** C ｜ **mission** {MISSION_ID}
**源** `{S['uri']}` · field=`{S['field']}` · sha256=`{S['hash']}` · chars={S['chars']} · bytes_utf8={S['bytes_utf8']}
**源报告标题** {S['title']} ｜ **scenario_key** `{S['scenario_key']}` ｜ **平台 mission_id** {S['platform_mission_id']} · status={S['platform_status']}

## 一、本工序做了什么

只做一件事：把 report_id={REPORT_ID} 的**源资产登记成册**（asset registration），不做抽取、不做分类、不做核验。
本包只读写 report 10602 这一份报告，未触碰任何其它 report_id。

- 登记资产 **{C['assets']}** 项：其中 markdown 内可原文定位 **{C['resolved_in_source']}** 项（`resolved_in_source`）、
  报告点名但本体不在 payload 内 **{C['referenced_unresolved']}** 项（`referenced_unresolved`）、
  报告**自行声明不做/未含** **{C['declared_absent']}** 项（`declared_absent`）。
- `claims` 数组**为空**：契约 `objective.register_assets=true` / `objective.classify_report_type=false`，
  且 `no_forced_claim_generation=true`——本工序不生成知识对象，不为凑指标造 claim。
- **没有任何条目被标成 verified**：`resolution` 只描述「定位/资产能否解析」，不代表报告结论为真；
  报告里 C1-C8「全部 PASS」是**报告作者的判定（claim）**，由平台门计算 verification，本包只登记其原文位置（A03 / A15）。
- 内容覆盖率：markdown 字符被「内联资产 span」覆盖 **{I['content_span_coverage'].split(' ')[0]}**（A02-A30；A01=全文本身不计）。

## 二、怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET $TENSOR_API_BASE/tensor/reports/{REPORT_ID}`（Bearer 登录 token），只取 `markdown` 字段，
   落盘为 `runs/wp-10602-01/report_10602.md`；同时保存整份 payload 供 figures/tags/mission 元信息登记。
2. **哈希门**：本地重算 `sha256(markdown.encode('utf-8'))` = `{S['hash']}`，与契约 `source_hash`
   **逐字符相等**；`chars={S['chars']}` 与契约 `chars: 6037` 相等。不等则脚本直接退出（不发任何产物）。
3. **零手抄定位**：每个资产给一个**唯一锚点串**，脚本在 markdown 行索引里查锚点（要求命中数 = 1，否则硬失败），
   再按行偏移切出 `quote`，用 `md.find(quote)` 求 `start_char/end_char`，"unique" 由 `md.count(quote)==1` 程序判定。
   → 引文全部是**运行时切出来的字节**，不是人写的字符串。
4. **外部资产探测**（只读、有界）：对被点名的文件/代码路径在固定根
   `/root/ship-performance-platform`、`/root/tp-agent/work/m9073` 做存在性探测，并另外做过一次
   `find /root -maxdepth 4 -type d -name eedi_opt`（无命中）。探测明细逐项写进 `resolution_check.probe`。
5. **结构门**：envelope 用它自己的 `schemas/kf_result.v1.schema.json` 校验；manifest 用本包新增的
   `schemas/asset_manifest.v1.1.schema.json`（把 v1 里写死的 `wp-448-01`/`448` 常量换成 pattern，其余同形，
   v1 不动、不影响别的包）。
6. **独立复核**：`scripts/kf_verify_10602.py` **重新从 API 取一次 markdown**（不信任产物缓存），
   逐项重算哈希、逐条 `md[start:end]==quote`、行号与字符偏移互校、id 唯一性、claims 纪律、计数自洽。

## 三、产出物清单

| 文件 | 要点 |
|---|---|
| `docs/wp-10602-01/asset_manifest.json` | 本工序正式产物：{C['assets']} 项资产 + source 元信息 + counts + integrity；`claims=[]` |
| `docs/wp-10602-01/kf_result.wp-10602-01.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims），即下方唯一 json 块 |
| `docs/wp-10602-01/fig1_asset_coverage.png` | 图 1：资产 span 沿源文本分布 + 按 asset_class 计数（统计数字由 manifest 程序化注入） |
| `docs/wp-10602-01/KF-RESULT-wp-10602-01.md` | 本报告正文（唯一 json 块 = 结果信封） |
| `scripts/kf_fetch_10602.py` | 取原文 + 哈希校验（凭据只走环境变量） |
| `scripts/kf_register_10602.py` | 登记器：锚点定位/唯一性断言/外部探测/schema 校验/落盘 |
| `scripts/kf_verify_10602.py` | 独立复核器：重取原文后逐项复验验收条目，输出 PASS/FAIL |
| `scripts/kf_report_10602.py` | 本报告生成器（正文数字与表格全部由 manifest/verifier 输出格式化） |
| `schemas/asset_manifest.v1.1.schema.json` | 新增**可复用**（package-agnostic）资产册 schema |

可复用增量说明：仓内既有 `schemas/asset_manifest.v1.schema.json` 把 `package_id`/`report_id`/`uri` 写成
本包专属 `const`（只服务 wp-448-01）；本包新增 v1.1 为同形但用 pattern 泛化，后续 01 工序可直接复用，且不改动 v1。

## 四、证据定位表（claim/字段 → 原文引文片段）

下表每行的引文都是运行时从 markdown 切出的**逐字片段**（长行取单行前缀，末尾 `…` 为截断标记，非原文）；
完整 `quote`（含多行）与精确 `start_char/end_char` 见 `docs/wp-10602-01/asset_manifest.json` 对应 asset 的 `locator`。
表中 span 列可独立复算：`md[start:end] == quote`。

{evidence_table()}

### 4.1 资产册全量清单

{inventory_table()}

### 4.2 外部引用探测明细（只读）

{probe_table()}

## 五、注意点与局限

1. **图二进制不可解析（登记发现）**：报告正文声明「5 张内嵌图」，但平台 payload 的 `figures` 只有
   `name` + `caption` 两条元数据（fig1_pareto_front / fig2_convergence / fig3_surrogate_error /
   fig4_sensitivity / fig5_constraint_shift），**没有 png 字段**；markdown 里也没有内联图引用。
   → 5 张图登记为 `referenced_unresolved`（A42，metadata present / binary unresolved）。
2. **被点名的工件与代码在本登记环境不可达（登记发现，非报告错误）**：A31-A41 共 11 项
   （`artifacts/m9073_eedi_opt/*`、`scripts/eedi_opt_m9073.py`、`tests/test_eedi_optimization_m9073.py`、
   `backend/physics/eedi_opt/`、`backend/api/eedi_optimization.py`、`backend/physics/holtrop.*`、`src/b_series`）
   在两个探测根下**均不存在**，`find /root -maxdepth 4 -name eedi_opt` 亦无命中。
   影响：下游抽取工序（02/03）无法取到 Pareto 逐解明细/判据 JSON/测试文件来交叉核对，
   这类交叉核对只能标 `unresolved`，**不得**凭正文数字重述为已验证。
3. **登记过程中观察到一处报告内部不自洽（只登记，不判定）**：A21 引文里一阶 Sobol 指数
   `Cb: 1.902`，而方差分解的一阶指数定义域为 [0,1]、一阶指数和 ≤ 1；同段文字又写「一阶指数和 = 1.902
   （<1 说明变量间存在交互作用）」，与数值方向相反。本包容量为登记：已把该段原文位置固定（A21），
   该数值是否成立由平台门/领域复核决定，本包**不**给结论、不标 verified。
4. **`declared_absent` 三项是给下游的护栏**：EEDI 修正项（P_AE/f_j/f_i/f_w/创新技术抵扣，A43）、
   船级社规范计算 + IS Code 2008 六项衡准与天气衡准（A44）、破舱稳性与纵倾/吃水差耦合（A45）——
   报告自己声明「未含/域外」。下游抽取若越界生成这些结论，即为越过报告能力边界。
5. **「PASS」不是本包的结论**：A03/A15 登记的是报告作者的判据判定文字，本包只保证「这句话在原文这个位置」。
   本包自己也**没有任何 verified 标记**（`integrity.verified_claims = {I['verified_claims']}`）。
6. **探测有界**：外部存在性只在 2 个固定根 + 一次 `maxdepth 4` 的 find 内做过，未做全盘扫描；
   若这些工件存在于其它机器/分支，A31-A41 的 `unresolved` 应被更新（`resolution_check.probe` 保留了我探测过的每个路径）。
7. **边界**：只碰 report 10602；未改上游产物、未改 `schemas/asset_manifest.v1.schema.json`、未 push。

## 六、自检（逐条对照 acceptance）

自动复核器 `scripts/kf_verify_10602.py`（重新取原文后独立复验）输出：

| verdict | 检查项与实测细节 |
|---|---|
{vtable}

- `valid_json`：envelope 与 manifest 均可解析 → **{'PASS' if all_pass else 'FAIL'}**
- `schema_pass`：envelope vs `kf_result.v1`、manifest vs `asset_manifest.v1.1`（含 envelope 内嵌 manifest 与独立文件字节一致）→ **{'PASS' if all_pass else 'FAIL'}**
- `source_locator_resolvable`：{len(ASSETS)}/{len(ASSETS)} 条 locator 在**重取**的原文上 `md[start:end]==quote` 且 unique 成立 → **{'PASS' if all_pass else 'FAIL'}**
- `source_hash_matches`：`{S['hash']}` = 契约 = manifest = envelope provenance.source_hash → **{'PASS' if all_pass else 'FAIL'}**
- `no_duplicate_ids`：{C['assets']} 个 id 唯一且连续 A01..A{C['assets']:02d} → **{'PASS' if all_pass else 'FAIL'}**
- `all_claims_have_evidence_or_explicit_unresolved_status`：claims 为空（契约允许），无缺失证据项 → **{'PASS' if all_pass else 'FAIL'}**

**如实声明的未完成/不可完成部分**：① 5 张图的二进制、② 11 个被点名工件与代码
（A31-A41）在本环境不可解析，登记为 `referenced_unresolved` 并附探测记录——这是**已知未闭合项**，
不是 PASS；下游若需这些资产须另行从源仓（ship-performance-platform, mission 9073）取回后再登记。

## 七、repro_cmd（一键复跑）

**repro_cmd**: `cd <worktree> && python3 scripts/kf_fetch_10602.py && python3 scripts/kf_register_10602.py && python3 scripts/kf_verify_10602.py && python3 scripts/kf_report_10602.py`

- 前置：环境变量 `TENSOR_API_BASE` / `TENSOR_AGENT_USER` / `TENSOR_AGENT_PASS`（不落盘、不写进任何产物）。
- 期望：fetch 打印的 sha256 = `{S['hash']}`；register 打印 assets={C['assets']}、哈希匹配；
  verify 全部 {len(vlines)} 项 PASS 且退出码 0；report 重建同一份 markdown（含同一 json 块）。
- 注：`artifacts/` 与 `runs/` 会被仓推送门禁过滤，`*.png` 亦被过滤——故正式副本落在
  `docs/wp-10602-01/`，图 1 同时以 base64 内嵌在本报告 `figures` 字段。

## 图

内嵌 1 张（`fig1_asset_coverage`）：左图 = 每项资产的 locator span 沿源文本字符轴的分布
（斜线填充 = 本体不在 payload 的 `referenced_unresolved`/`declared_absent`），右图 = 按 asset_class 计数。
图中所有数字由 `docs/wp-10602-01/asset_manifest.json` 程序化注入。
（本工序为登记/文档工序，唯一有意义的可视图是「资产覆盖图」；报告物理结果图属上游 10602 的能力，
且其二进制本次不可解析——见第五节 1/2，故不重绘、不臆造。）

## 结果信封（唯一 json 块）

```json
{result_json}
```
"""
    return md


def post(md: str) -> None:
    fig64 = base64.b64encode(FIG.read_bytes()).decode()
    title = "KF-RESULT " + PACKAGE_ID
    payload = {
        "title": title,
        "summary": (
            f"report {REPORT_ID} 资产登记完成：{C['assets']} 项（resolved_in_source={C['resolved_in_source']} / "
            f"referenced_unresolved={C['referenced_unresolved']} / declared_absent={C['declared_absent']}），"
            f"claims=[]（契约允许），source_hash 与契约逐字符相等，{len(ASSETS)}/{len(ASSETS)} 条 locator 在重取的原文上可复算，"
            "零手抄、无 verified 标记。"),
        "scenario_key": S["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "kf", "asset-registration", "report-" + REPORT_ID,
                 "knowledge-factory", "lane-C"],
        "markdown": md,
        "figures": [{
            "name": "fig1_asset_coverage",
            "caption": (f"Asset registration coverage for report {REPORT_ID}: left = char span of each of the "
                        f"{C['assets']} registered assets along the source markdown (hatched = assets outside the "
                        f"payload: referenced_unresolved/declared_absent), right = assets per asset_class. "
                        f"Counts injected programmatically from asset_manifest.json."),
            "png_base64": fig64,
        }],
    }
    tok = None
    req = urllib.request.Request(BASE + "/auth/login",
                                data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                 "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                                headers={"Content-Type": "application/json"})
    tok = json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]
    req = urllib.request.Request(BASE + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = json.loads(r.read().decode())
    print("posted report id:", body.get("id") or body.get("data", {}).get("id") or body)


def main() -> None:
    md = build_markdown()
    out = DOCS / "KF-RESULT-wp-10602-01.md"
    out.write_text(md, encoding="utf-8")
    fences = md.count("```")
    print("wrote", out, "chars=", len(md), "fence markers=", fences)
    assert fences == 2, "report must contain exactly one fenced block"
    if "--no-post" not in sys.argv:
        post(md)


if __name__ == "__main__":
    main()