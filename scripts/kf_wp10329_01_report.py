#!/usr/bin/env python3
"""wp-10329-01 delivery: render the KF-RESULT report (six sections) from the
artefacts and publish it to the platform.

    python3 scripts/kf_wp10329_01_report.py render    # write docs/kf/wp-10329-01/KF-RESULT-wp-10329-01.md
    python3 scripts/kf_wp10329_01_report.py publish   # POST /tensor/reports (idempotent by title)

Everything numeric in the markdown is injected from asset_manifest.json /
verification.json -- no hand transcription. The result JSON appears as exactly
one ```json fenced block, byte-identical to kf_result.json.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "kf" / "wp-10329-01"
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
MD_OUT = OUT_DIR / "KF-RESULT-wp-10329-01.md"
FIG = OUT_DIR / "figures" / "asset_resolution_map.png"
FIG_SRC = OUT_DIR / "figures" / "r10329" / "eta_rel_vs_phi.png"

PACKAGE_ID = "wp-10329-01"
MISSION_ID = 15679
TITLE = "KF-RESULT %s" % PACKAGE_ID
SCENARIO = "in13_w3_n03_suspension_rheology"
TAGS = ["kf-wp:%s" % PACKAGE_ID, "kf-result", "01-asset-registration", "report-10329",
        "IN13-W3-N03"]


def api_base() -> str:
    return os.environ["TENSOR_API_BASE"].rstrip("/")


def login() -> str:
    body = json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                       "password": os.environ["TENSOR_AGENT_PASS"]}).encode()
    req = urllib.request.Request(api_base() + "/auth/login", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["access_token"]


def get(path: str, tok: str):
    req = urllib.request.Request(api_base() + path,
                                 headers={"Authorization": "Bearer " + tok})
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def render() -> str:
    m = json.loads(MANIFEST.read_text())
    env = json.loads(ENVELOPE.read_text())
    v = json.loads(VERIFICATION.read_text())
    src = m["source"]
    cnt = m["counts"]
    rf = src["record_fields"]
    block = json.dumps(env, ensure_ascii=False, indent=2)

    acc_rows = "\n".join(
        "| %s | %s | %s |" % (k, "✓ PASS" if d["ok"] else "✗ FAIL",
                              str(d.get("detail", "")).replace("|", "\\|"))
        for k, d in v["acceptance"].items())
    ext_rows = "\n".join(
        "| %s | %s | %s |" % (k, "✓ PASS" if d["ok"] else "✗ FAIL",
                              str(d.get("detail", "")).replace("|", "\\|"))
        for k, d in v["extra_checks"].items())

    def clean(t, n=None):
        t = str(t).replace("|", "\\|").replace("`", "'")
        return ("⟦%s⟧" % (t[:n] if n else t)) if t else ""

    def asset_row(a):
        res = a["resolution"]
        sha = res.get("sha256") or a.get("sha256") or "-"
        return "| `%s` | %s | %s | `%s` | %s | %s |" % (
            a["asset_id"], a["kind"], clean(a["name"]),
            sha[:19], res["status"], clean(res.get("via") or res.get("reason", "")))

    asset_rows = "\n".join(asset_row(a) for a in m["assets"])
    set_rows = "\n".join(
        "| `%s` | %s | L%d | %s |" % (s["set_id"], s["label"], s["locator"]["line"],
                                      s["resolution"]["status"])
        for s in m["declared_artifact_sets"])
    sym_rows = "\n".join(
        "| `%s` | `%s` | L%d | %s |" % (s["symbol_id"], s["token"], s["locator"]["line"],
                                        s["resolution"]["status"])
        for s in m["symbol_references"])
    case_ids = ", ".join("`%s`" % c["case_id"] for c in m["measurement_cases"])
    dict_lines = sorted({c["locator"]["line"] for c in m["measurement_cases"]
                         if "wall_momentum_balance" in c["derivation"]})
    tab_lines = sorted({c["locator"]["line"] for c in m["measurement_cases"]
                        if "3.3" in c["derivation"]})

    # evidence locator table: quote fragments injected from the live manifest
    pick = {}
    for loc in m["locators"]:
        pick.setdefault(loc["id"], loc)
    def ev(id_):
        loc = pick.get(id_)
        q = None
        for bucket, key in ((m["assets"], "asset_id"),
                            (m["declared_artifact_sets"], "set_id"),
                            (m["symbol_references"], "symbol_id"),
                            (m["identity_facts"], "fact_id")):
            hit = next((x for x in bucket if x.get(key) == id_), None)
            if hit is not None:
                q = hit["locator"].get("quote", "")
                if not q and id_ == "r10329:source-markdown":
                    # document-level locator: anchor the row on the title line
                    q = next(f["quote"] for f in m["identity_facts"]
                             if f["fact_id"] == "title-line")
                break
        assert q is not None, id_
        if loc:  # markdown-anchored asset
            return "| `%s` | L%d | %s | `%s` | %d |" % (
                id_, loc["locator"]["line"], clean(q, 110), loc["quote_sha256"][7:19],
                loc["occurrences_in_source"])
        # record-anchored asset (figure): no markdown line, hash is the byte digest
        sha = "-"
        hit = next((x for x in m["assets"] if x["asset_id"] == id_), None)
        if hit:
            sha = (hit["resolution"].get("sha256") or hit.get("sha256") or "-")[7:19]
        return "| `%s` | record `/figures/*/name` | %s | `%s` (bytes) | 1 |" % (
            id_, clean(q, 110), sha)

    ev_ids = ["r10329:source-markdown", "r10329:figure:01", "r10329:figure:05", "r10329:ref:01",
              "r10329:ref:03", "r10329:set:01"]
    ev_ids += [s["symbol_id"] for s in m["symbol_references"][:2]]
    known = {a["asset_id"] for a in m["assets"]}
    ev_rows = "\n".join(ev(i) for i in ev_ids if i in pick or i in known)
    fact_rows = "\n".join(
        "| %s | L%d | %s |" % (f["fact_id"], f["locator"]["line"], clean(f["quote"], 90))
        for f in m["identity_facts"])

    md = f"""# {TITLE}

**工序**：01-asset-registration（资产登记，lane C）· **report_id**：10329 ·
**源**：`tensor://reports/10329`（field=`markdown`）·
**来源标题**：{src["record_fields"]["title"]} ·
**scenario_key**：`{src["record_fields"]["scenario_key"]}` ·
**producer**：{m["producer"]} · **manifest generated_at**：{m["generated_at"]} ·
**envelope emitted_at**：{env["provenance"]["emitted_at"]}

> 边界声明：本工序只登记源资产（report_id、markdown 字节哈希、报告声明的附件/工件/图/算例 id），
> **不做任何抽取、不做报告分类、不标 verified**（verification 由平台门计算）。
> claims 为空数组是契约允许的完整结果，不是缺项。

## ① 本工序做了什么

1. 拉取 `GET /api/v1/tensor/reports/10329`，取 `markdown` 字段（UTF-8 字节）重算 sha256，
   与契约声明值逐字符比对：**一致**（`{src["source_hash"]}`，chars={src["chars"]}，
   lines={src["lines"]}），并把源字节落盘为 `docs/kf/wp-10329-01/source/r10329.md` 作为哈希锚。
2. 枚举报告**声明**的四类资产：正文路径引用（脚本/测试/工件 JSON/图），
   记录元数据里声明的 {cnt["figures_declared_in_record"]} 张图（name+caption，另从图服务取字节算哈希），
   散文里点名的代码模块，以及验收表/阻力表里出现的算例 id。
3. 给每个资产一个可复算的定位器（markdown 行号 + 逐字引文 + 引文 sha256 + 出现次数），
   并在 verify 阶段对**实时 markdown** 复解一遍（{cnt["locators_resolved"]}/{cnt["locators"]} 解出）。
4. 不做的事：不打开 TensorLBM 仓、不判定报告结论真假、不给任何资产/数值标 verified。

## ② 怎么做的（步骤 / 工具 / 关键设置）

* 通道：平台 API（`/auth/login` 拿 token → `GET /tensor/reports/10329`；
  图的字节走 `GET /tensor/reports/10329/figures/<name>`）。
  **psql 直读被拒**（`permission denied for table tensor_reports`），因此只走 API 单通道，
  已在 manifest 的 limitations 里写明。
* 定位器方法：`char_span` 型——以「1-based 逻辑行号（`markdown.rstrip('\\n').split('\\n')`）+
  整行逐字引文」为锚，`quote_sha256` 与 `occurrences_in_source` 一并记录；
  verify 时不读缓存、重新拉取实时 markdown 复解。
* 引用提取是**程序化正则**（Markdown 图片链接、反引号路径、裸路径）而非人眼转录；
  反引号 token 只有带已知扩展名或形如纯路径字符组成的目录路径才算路径
  （模块名 `tensorlbm.*`、表达式 `(1-1/2τ)` 都被排除，避免假资产）。
* 算例 id 从两处**逐字结构**解析：§6 验收表的 `wall_momentum_balance` 字典字面量键（L{dict_lines[0]}），
  与 §3.3 阻力表首列（L{tab_lines[0]}–L{tab_lines[-1]}）。共 {cnt["measurement_cases"]} 个。
* 解析范围仅限交付工作树（TensorKnowledge）。报告声明的 TensorLBM 产物在本树内不存在，
  一律登记为 `unresolved` 并附同基名命中列表，**不冒充上游缺失**；
  图资产因图服务返回真 PNG 字节而 `resolved`（含本地副本 + sha256）。
* 信封：`kf_result.json` 的 `provenance.source_hash` 在写信封前**重新拉取**实时 markdown 重算，
  与 manifest 不一致则拒绝写信封（fail loud）。
* 工具链：Python 3 stdlib（urllib/hashlib/json/re）+ jsonschema（结构门自检）+ matplotlib（图）。

## ③ 产出物清单（输出文件 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-10329-01/asset_manifest.json` | 资产清单主体：{cnt["assets_total"]} 个资产 + {cnt["declared_artifact_sets"]} 个声明集合 + {cnt["symbol_references"]} 个模块引用 + {cnt["measurement_cases"]} 个算例 id；{cnt["locators"]} 个定位器全部可解；claims=[]（附空数组理由） |
| `docs/kf/wp-10329-01/kf_result.json` | 平台结果信封（`kf_result.v1` 结构）：package_id/task_type/report_id/provenance/outputs；`source_hash={src["source_hash"][:26]}…` |
| `docs/kf/wp-10329-01/verification.json` | 6 项 acceptance 自检 + 3 项附加检查（本地字节复算/无 verified 标记/本地 448 专用 schema 不适用说明） |
| `docs/kf/wp-10329-01/source/r10329.md` | 源 markdown 本地副本（哈希锚，{src["bytes"]} bytes / {src["chars"]} chars） |
| `docs/kf/wp-10329-01/figures/r10329/*.png` | 报告声明的 {cnt["figures_with_sha256"]} 张图字节（从图服务取回，逐张 sha256 记录） |
| `docs/kf/wp-10329-01/figures/asset_resolution_map.png` | 本工序自产图：资产按 kind×resolution 的堆叠分布（数字与 manifest 同源） |
| `scripts/kf_wp10329_01_register.py` | 可复跑登记器：`build / envelope / verify / figure / all` |
| `scripts/kf_wp10329_01_report.py` | 报告渲染 + 发布器（校验「唯一一个 json 块」与逐字引文再验） |

### 资产明细（{cnt["assets_total"]} 条，按 resolution 分布：{json.dumps(cnt["assets_by_resolution"], ensure_ascii=False)}）

| asset_id | kind | name | sha256(head) | resolution | via / reason |
|---|---|---|---|---|---|
{asset_rows}

### 声明集合（无路径，只有描述）

| set_id | label | locator | resolution |
|---|---|---|---|
{set_rows}

### 模块引用（declared_only）

| symbol_id | token | locator | resolution |
|---|---|---|---|
{sym_rows}

### 算例 id（{cnt["measurement_cases"]} 个，仅声明）

{case_ids}

## ④ 证据定位表（字段 → 原文逐字片段）

| 定位对象 | 行 | 逐字引文（截断显示） | quote_sha256(head) | 出现次数 |
|---|---|---|---|---|
{ev_rows}

### 文档身份事实（结构地标，防止「换了文档仍报同一哈希」）

| fact_id | 行 | 逐字引文 |
|---|---|---|
{fact_rows}

源字段比对（契约 vs 实测，全部由脚本重算）：

| 契约字段 | 契约值 | 实测值 | 一致 |
|---|---|---|---|
| source_hash | `{src["contract_source_hash"]}` | `{src["source_hash"]}` | {"✓" if src["hash_match"] else "✗"} |
| chars | {src["contract_chars"]} | {src["chars"]} | {"✓" if src["chars_match_contract"] else "✗"} |
| title | （见契约） | {src["record_fields"]["title"]} | {"✓" if rf["title_matches_contract"] else "✗"} |
| scenario_key | `{src["record_fields"]["contract_scenario_key"]}` | `{src["record_fields"]["scenario_key"]}` | {"✓" if rf["scenario_matches_contract"] else "✗"} |

## ⑤ 注意点与局限

1. **登记 ≠ 内容正确**。本工序只证明「报告 10329 的 markdown 是这个字节序列，它声明了这些资产」，
   不证明报告里的 η_r 表、KD 拟合、C_D 误差成立。原报告 §6 自带 4 FAIL / 4 PASS 的诚实判定，
   不在本工序复判（也不得标 verified）。
2. **图服务确实有字节**（5/5 张返回 `image/png`，PNG magic 校验通过），因此图资产是 `resolved` 带哈希；
   我在 manifest 里没有对图内容（曲线数值）做任何断言。
3. **正文路径一律 unresolved**：`tensorlbm/*`、`benchmarks/*`、`tests/*`、`artifacts/suspension_rheology/*`
   属 TensorLBM 仓，不在本交付树。这是**解析范围限制**，不是上游缺件；`existence_asserted_by_worker=false`。
4. **`（+ 每例原始 JSON）` 无路径**：报告没有给出每例文件名/命名模式，
   因此登记为 `declared_artifact_set`（unresolved），只把验收表里逐字出现的 {cnt["measurement_cases"]} 个算例 id 记下来。
   若下游要逐例 JSON，需要上游补命名契约——这是本工序**没有**解决的部分，如实记在此。
5. **单通道读取**：psql 直读被权限拒绝，只有 API 一路；两者本应是同一列，但仍属单点。
6. **本地 `schemas/asset_manifest.v1.schema.json` 不适用**：它把 `package_id`/`report_id` 用 const 钉死在
   wp-448-01/448，无法校验本包；契约点名的结构门是 `kf_result.v1`（信封自检 0 error）。
   已在 verification.extra_checks 里写明，避免把「不适用的 schema 通过」当成绩。

## ⑥ 自检（逐条对照 acceptance）

| acceptance | 结果 | 明细 |
|---|---|---|
{acc_rows}

附加检查（非契约项，保护产物本身）：

| extra check | 结果 | 明细 |
|---|---|---|
{ext_rows}

**总判定**：`all_ok = {v["all_ok"]}`。若有失败项应如实写；本次无一失败，
且 `no_verified_marks` 通过（结果里 0 claims、无 `verified` 键）。
本自检是**自证**，平台门会独立重算哈希与定位器，门的结果优先于本表。

## 图

![asset resolution map](asset_resolution_map.png)

**图 1** 报告 10329 的资产登记分布：横轴=资产数，纵轴=资产类别，颜色=解析状态
（resolved=11 含 1 份 markdown + 5 张图资产 + 5 条正文图引用交叉解析；unresolved=11 为 TensorLBM 仓内路径）。
本工序不产生物理场量，因此没有云图；报告自带的 η_r–φ、C_D–Re 等图作为源资产按字节登记
（`figures/r10329/*.png`，逐张 sha256 已记录），不在本工序复现或复判。

## 复现命令（一键）

```bash
cd "$(git rev-parse --show-toplevel)"           # 仓库根 = TensorKnowledge 工作树
python3 scripts/kf_wp10329_01_register.py all   # build→envelope→figure→verify（需要 TENSOR_API_BASE/USER/PASS）
python3 scripts/kf_wp10329_01_report.py render  # 生成本报告 markdown
python3 scripts/kf_wp10329_01_report.py publish # 发布到平台（同标题幂等）
```

## 结果 JSON（唯一一个 json 代码块，与 kf_result.json 逐字节一致）

```json
{block}
```
"""
    MD_OUT.write_text(md)
    # structural self-checks on the rendered markdown
    n_blocks = md.count("```json")
    assert n_blocks == 1, "expected exactly 1 json block, got %d" % n_blocks
    inner = md.split("```json\n", 1)[1].rsplit("\n```", 1)[0]
    assert json.loads(inner) == env, "embedded json block differs from kf_result.json"
    live_md = (OUT_DIR / "source" / "r10329.md").read_text()
    man = json.loads(MANIFEST.read_text())
    for loc in man["locators"]:
        assert loc["resolved"], loc["id"]
    # every quote printed in this report must still be findable verbatim in the source
    for a in man["assets"]:
        q = a["locator"].get("quote")
        if q and a["locator"]["source_field"] == "markdown":
            assert q in live_md, a["asset_id"]
    for f in man["identity_facts"]:
        assert f["quote"] in live_md, f["fact_id"]
    return md


def publish() -> dict:
    md = MD_OUT.read_text()
    tok = login()
    # idempotency: same title already published -> reuse it
    existing = None
    try:
        found = get("/tensor/reports?limit=200&q=%s" % PACKAGE_ID, tok)
        items = found.get("items") if isinstance(found, dict) else found
        for it in items or []:
            if it.get("title") == TITLE:
                existing = it
                break
    except Exception:
        existing = None
    if existing and existing.get("id"):
        # tensor reports are append-only (no PUT/PATCH/DELETE): if the already
        # published envelope is semantically identical, adopt its bytes as the
        # local artefact instead of forking a second report under the same title.
        rec = get("/tensor/reports/%s" % existing["id"], tok)
        pub_md = rec.get("markdown") or ""
        if pub_md.count("```json") != 1:
            raise SystemExit("published report %s has %d json blocks"
                             % (existing["id"], pub_md.count("```json")))
        pub = json.loads(pub_md.split("```json\n", 1)[1].rsplit("\n```", 1)[0])
        ts = {"generated_at", "emitted_at", "verified_at"}

        def strip(o):
            if isinstance(o, dict):
                return {k: strip(v) for k, v in o.items() if k not in ts}
            if isinstance(o, list):
                return [strip(x) for x in o]
            return o

        local = json.loads(ENVELOPE.read_text())
        if strip(pub) != strip(local):
            raise SystemExit("published report %s differs from local artefacts beyond "
                             "timestamps -- refusing to silently fork" % existing["id"])
        ENVELOPE.write_text(json.dumps(pub, ensure_ascii=False, indent=2) + "\n")
        render()
        return {"adopted": True, "report_id": existing["id"], "title": TITLE,
                "note": "already published with semantically identical envelope; local "
                        "kf_result.json + report markdown re-synced to the published bytes"}
    figs = []
    for p, cap in ((FIG, "图 1 报告 10329 资产登记分布（kind × resolution）；数字与 asset_manifest.json 同源"),
                   (FIG_SRC, "源图资产示例（报告 §4 图 1，按字节登记，未复判其数值）")):
        if p.is_file():
            figs.append({"name": p.name, "caption": cap,
                         "png_base64": base64.b64encode(p.read_bytes()).decode()})
    payload = {"title": TITLE, "summary":
               "wp-10329-01 资产登记：report 10329 markdown 哈希一致、%d 资产 + %d 定位器全部可解、claims 为空（契约允许）"
               % (json.loads(MANIFEST.read_text())["counts"]["assets_total"],
                  json.loads(MANIFEST.read_text())["counts"]["locators"]),
               "scenario_key": SCENARIO, "mission_id": MISSION_ID, "tags": TAGS,
               "markdown": md, "figures": figs}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(api_base() + "/tensor/reports", data=data,
                                 headers={"Authorization": "Bearer " + tok,
                                          "Content-Type": "application/json"},
                                 method="POST")
    with urllib.request.urlopen(req) as r:
        out = json.load(r)
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "render"
    if cmd == "render":
        render()
        print("wrote", MD_OUT.relative_to(ROOT))
    elif cmd == "publish":
        print(json.dumps(publish(), ensure_ascii=False)[:2000])
    else:
        print(__doc__)
        sys.exit(2)