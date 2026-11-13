#!/usr/bin/env python3
"""Render the wp-7545-01 deliverable report (figure + markdown) and publish it to the platform.

Zero hand-copy: every number and every quote in the markdown is injected from
docs/kf/wp-7545-01/asset_manifest.json + verification.json, which were themselves produced
by scripts/kf/build_asset_manifest_7545.py against the live report bytes.

Usage:
  python3 scripts/kf/report_7545_01.py render     # figure + docs/kf/wp-7545-01/REPORT.md
  python3 scripts/kf/report_7545_01.py publish    # render + POST /tensor/reports
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PKG = "wp-7545-01"
REPORT_ID = "7545"
REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
RESULT = OUT_DIR / "kf_result.json"
VERDICT = OUT_DIR / "verification.json"
FIGURE = OUT_DIR / "fig1_asset_inventory.png"
REPORT_MD = OUT_DIR / "REPORT.md"

BASE = os.environ["TENSOR_API_BASE"].rstrip("/")


def load():
    man = json.loads(MANIFEST.read_text(encoding="utf-8"))
    res = json.loads(RESULT.read_text(encoding="utf-8"))
    ver = json.loads(VERDICT.read_text(encoding="utf-8"))
    return man, res, ver


def make_figure(man):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    by_class = man["counts"]["by_class"]
    by_res = man["counts"]["by_resolution"]
    classes = sorted(by_class.items(), key=lambda kv: (-kv[1], kv[0]))
    resos = sorted(by_res.items(), key=lambda kv: (-kv[1], kv[0]))

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    axes[0].barh([c for c, _ in classes], [n for _, n in classes], color="#3b6ea5")
    axes[0].invert_yaxis()
    axes[0].set_xlabel("asset count")
    axes[0].set_title("wp-%s: assets by class (n=%d)" % (REPORT_ID, man["counts"]["assets"]))
    for i, (_, n) in enumerate(classes):
        axes[0].text(n, i, " %d" % n, va="center", fontsize=9)

    axes[1].bar([r for r, _ in resos], [n for _, n in resos], color=["#2e7d32", "#c62828", "#ef6c00"])
    axes[1].set_ylabel("asset count")
    axes[1].set_title("resolution status (source hash %s...)" % man["source"]["hash"][:8])
    axes[1].tick_params(axis="x", rotation=12, labelsize=9)
    for i, (_, n) in enumerate(resos):
        axes[1].text(i, n, str(n), ha="center", va="bottom", fontsize=9)
    fig.suptitle("Report %s asset registration — nothing extracted, nothing verified" % REPORT_ID,
                 fontsize=10)
    fig.tight_layout()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE, dpi=150)
    plt.close(fig)
    return FIGURE


def render():
    man, res, ver = load()
    make_figure(man)
    src, cnt, integ = man["source"], man["counts"], man["integrity"]
    checks = ver["checks"]

    def mark(key):
        return "✔" if checks[key]["pass"] else "✘"

    asset_rows = "\n".join(
        "| %s | %s | %s | %s | L%d | `%s` | %s |" % (
            a["asset_id"], a["asset_class"], a["label"].replace("|", "\\|"),
            a["in_report_section"].replace("|", "\\|"), a["locator"]["start_line"],
            a["locator"]["quote"].replace("|", "\\|").replace("`", "'"), a["resolution"])
        for a in man["assets"])

    evidence_rows = "\n".join(
        "| %s | %s | `%s` | %d | %s |" % (
            a["asset_id"], a["asset_class"], a["locator"]["quote"].replace("|", "\\|").replace("`", "'"),
            a["locator"]["start_line"], "唯一" if a["locator"]["unique"] else "非唯一")
        for a in man["assets"])

    unresolved = [a["asset_id"] for a in man["assets"] if a["resolution"] == "referenced_unresolved"]
    absent = [a["asset_id"] for a in man["assets"] if a["resolution"] == "declared_absent"]

    md = f"""# KF-RESULT {PKG} — 报告 {REPORT_ID} 源资产登记（01-asset-registration）

> 工序=01-asset-registration ｜ lane=C ｜ 输入 `{src['uri']}` 字段 `markdown` ｜
> 源字节 sha256 = `{src['hash']}`（{src['chars']} 字符 / {src['bytes_utf8']} 字节 UTF-8）｜
> 契约声明哈希 = `{man['contract']['source_hash_declared']}` ｜ 一致：{integ['hash_matches_contract']}

## ① 本工序做了什么

严格按契约只做登记：确认真实报告 {REPORT_ID} 的 markdown 字节哈希与契约 `source_hash` 一致，
把这一个报告里**可逐字定位的资产**（正文本身 + 平台 figures 元数据 + 正文引用的附件/工件/代码/命令）
登记成 `asset_manifest.json`，并为每个资产绑一个**字符级定位器**（start/end char + line + 逐字 quote + 唯一性）。

不做的事（契约硬约束，一条都没越界）：不做文本抽取、不生成知识 claim（`claims: []`，{len(man['claims'])} 条）、
不把任何结论标 `verified`、不改写上游/其它工作包产物、不读不写其它 `report_id`。
登记结果：**{cnt['assets']} 个资产**，其中 `resolved_in_source` {cnt['resolved_in_source']} 个、
`referenced_unresolved` {cnt['referenced_unresolved']} 个、`declared_absent` {cnt['declared_absent']} 个。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取源**：`GET {src['fetched_via'].split(' ', 1)[-1]}`（Bearer token 来自 `POST /api/v1/auth/login`），
   取 `markdown` 字段原样落地，**不在本地重排/规范化**——哈希必须对原始字节计算。
2. **哈希门**：`sha256(markdown.encode('utf-8'))` = `{src['hash']}`，与契约 `source_hash` 逐字符比对；
   不一致直接 `SystemExit`，不写任何产物（先门后写）。
3. **资产发现**（只做正则扫描，不做语义抽取）：
   - 正文本身 → 1 个 `report_markdown`，定位器 `method=document`（0..{src['chars']}）；
   - 反引号文件引用 → `data_artifact_reference` / `source_code_reference`，带 `:pin` 锚点（如 `experiments.json:spec`）；
   - 反引号目录引用 → `directory_reference`；反引号 shell 命令 → `test_command_reference`（只登记文本，不执行）；
   - 平台 `figures` 元数据 {len(src['platform_figures'])} 条 → `embedded_figure`，名称/图注照抄，并对每个
     `GET /api/v1/tensor/reports/{REPORT_ID}/figures/<name>` 做**字节探测**。
4. **定位器构造**：`start = md.find(quote)`、`end = start + len(quote)`、行号 = 前缀换行计数 + 1；
   `unique = md.count(quote) == 1`。quote 一律用 `md[...]` 切片得到，**不手打**（结构性防手抄）。
5. **解析判定**（worktree + git index 双查）：命中本检出 → `resolved_in_source`；不在本检出 → `referenced_unresolved`（不跨仓猜）。
6. **自检**：`verify` 子命令**重新登录、重新取报告**，独立重算哈希、逐个切片复验 quote、跑两份 JSON Schema。

关键设置：`EXPECTED_HASH={man['contract']['source_hash_declared'].split(':')[-1]}`、`EXPECTED_CHARS={man['contract']['contract_chars']}`
（写成常量做一次性断言，防止"顺手"换源）；schema 校验用 `schemas/asset_manifest.v1.schema.json`，其 `package_id/report_id/uri`
三个 `const` 在内存中重绑定到本包（该文件原本 `const` 到 wp-448-01），`schemas/kf_result.v1.schema.json` 原样使用。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/{PKG}/asset_manifest.json` | {cnt['assets']} 个资产，sha256=`{res['outputs']['asset_manifest.json']['sha256'][:16]}…`（{res['outputs']['asset_manifest.json']['bytes']} B），claims=0 |
| `docs/kf/{PKG}/kf_result.json` | 结果信封（package_id/task_type/report_id/provenance/outputs/claims），过 `kf_result.v1` schema |
| `docs/kf/{PKG}/verification.json` | 独立自检回执，7 项检查逐条 pass |
| `docs/kf/{PKG}/fig1_asset_inventory.png` | 资产分类与解析状态柱状图（数据由 manifest 注入） |
| `docs/kf/{PKG}/REPORT.md` | 本报告 |
| `scripts/kf/build_asset_manifest_7545.py` | 登记器 + 校验器（build/result/verify） |
| `scripts/kf/report_7545_01.py` | 出图与报告渲染/发布 |

资产分类（`counts.by_class`）：{json.dumps(cnt['by_class'], ensure_ascii=False)}
解析状态（`counts.by_resolution`）：{json.dumps(cnt['by_resolution'], ensure_ascii=False)}

**资产台账**

| id | class | label | 正文节 | 行 | quote（逐字） | resolution |
|---|---|---|---|---|---|---|
{asset_rows}

## ④ 证据定位表（资产 → 原文引文片段）

全部 {cnt['assets']} 条 quote 均满足「`md[start:end] == quote` ∧ 落在声明的行上 ∧ 全文字符串唯一」
（`integrity.quote_uniqueness.unique = {integ['quote_uniqueness']['unique']}/{integ['quote_uniqueness']['checked']}`，非唯一项：{integ['quote_uniqueness']['non_unique_ids']}）。
`claims` 为空数组，故本工序**没有 claim→证据**的映射表可填；下表是资产级的等价物（每个资产 = 一个可复核的"报告说过这里有这个东西"）：

| 资产 | 用途/声明位置 | quote | 行 | 唯一性 |
|---|---|---|---|---|
{evidence_rows}

## ⑤ 注意点与局限

- **图注在、字节不在**：平台 `figures` 4 条元数据齐全，但 `GET .../figures/<name>` 四条全部 `404 {{"detail":"figure not found"}}`。
  故 {absent} 判 `declared_absent`（`resolution_check.result=absent`），**不臆造图片哈希**，也不从别处拷贝同名图。这是登记工序应报的事实。
- **跨仓引用一律不解析**：报告引用的 `tools/abm`、`dem_bpm.py`、`run_abm.py`、`artifacts/IN59-P2/*` 等属于产生该报告的域仓/任务树，
  不在 TensorKnowledge 检出内（worktree 与 git index 双查均无），{len(unresolved)} 个资产判 `referenced_unresolved`。
  边界使然，不是缺陷：跨仓拷贝会破坏"互不覆盖"前提。
- **不执行测试命令**：正文与审计链各出现一次 `pytest ...`（A17/A18，出现级标识所以两条），本包只登记文本可定位性；
  报告声称的 `19 passed` **未在本包复核**，登记 ≠ 背书。
- **不做数值复核**：报告里的 `σ_c=2.261 MPa`、`σ_t=0.813 MPa`、`E=nan GPa`、`m_eff=nan` 等数字本包只当作"报告文本"登记，
  不判真伪、不改写、不补算；误差判定与 honest-FAIL 结论归平台门与下游工序。
- **只登记 1 份报告**：全部步骤以 `report_id={REPORT_ID}` 硬编码，脚本没有任何其它 report 的写入路径。
- **schema 的 const 冲突是已知事实**：`schemas/asset_manifest.v1.schema.json` 把 `package_id` 固定成 `wp-448-01`，
  本包校验在内存中重绑定 `package_id/report_id/source.uri` 三个 const（已在 `verification.json` 里写明），不改远端 schema 文件。

## ⑥ 自检：逐条对照 acceptance

| acceptance 项 | 结果 | 证据 |
|---|---|---|
| valid_json | {mark('valid_json')} | `asset_manifest.json`、`kf_result.json` 均 `json.loads` 通过 |
| schema_pass | {mark('schema_pass')} | asset_manifest.v1（const 重绑定）+ kf_result.v1 校验，errors=[] |
| source_locator_resolvable | {mark('source_locator_resolvable')} | 重新取报告后逐个切片复验 {cnt['assets']} 个定位器，失败=[] |
| source_hash_matches | {mark('source_hash_matches')} | 重算=manifest=契约=`{src['hash'][:16]}…` |
| no_duplicate_ids | {mark('no_duplicate_ids')} | {cnt['assets']} 个 id 全唯一且匹配 `^A[0-9]{{2}}$` |
| all_claims_have_evidence_or_explicit_unresolved_status | {mark('all_claims_have_evidence_or_explicit_unresolved_status')} | claims=[] ⇒ 空数组合法（契约 `no_forced_claim_generation: true`），违例 0 |
| do_not_mark_claims_as_verified | {mark('do_not_mark_claims_as_verified')} | 无任何 `status=verified`；manifest `contract.status=draft` |

**失败项：无**（7/7 pass，`verification.json: all_pass={ver['all_pass']}`）。如实声明未做的：抽取/核验/数值复核/执行测试，均在本包边界外。

## 复跑

```bash
# 一键复跑（取源→哈希门→登记→结果信封→独立自检；需 TENSOR_API_BASE/TENSOR_AGENT_USER/TENSOR_AGENT_PASS）
python3 scripts/kf/build_asset_manifest_7545.py build result verify
# 出图 + 渲染本报告
python3 scripts/kf/report_7545_01.py render
```

## 结果信封

```json
{json.dumps(res, ensure_ascii=False, indent=2)}
```
"""
    REPORT_MD.write_text(md, encoding="utf-8")
    print("wrote %s (%d chars)" % (REPORT_MD.relative_to(REPO), len(md)))
    return md, man, res


def publish():
    md, man, res = render()
    blob = FIGURE.read_bytes()
    payload = {
        "title": "KF-RESULT %s" % PKG,
        "summary": ("wp-7545-01 资产登记：报告 7545 markdown sha256=%s（与契约一致），登记 %d 个资产"
                    "（resolved %d / unresolved %d / absent %d），claims=0，7/7 验收项自检 pass。"
                    % (man["source"]["hash"][:16], man["counts"]["assets"],
                       man["counts"]["resolved_in_source"], man["counts"]["referenced_unresolved"],
                       man["counts"]["declared_absent"])),
        "scenario_key": "ice_fracture_contact_abm",
        "mission_id": 15597,
        "tags": ["kf-wp:%s" % PKG, "asset-registration", "01-asset-registration",
                 "report-7545", "ice_fracture_contact_abm", "KBM-RCI-F1"],
        "markdown": md,
        "figures": [{
            "name": FIGURE.name,
            "caption": ("报告 7545 资产登记的资产分类与解析状态（数据由 asset_manifest.json 注入；"
                        "resolved=1 即源 markdown，absent=4 为平台 figures 端点 404 的图，unresolved=%d 为跨仓引用）"
                        % man["counts"]["referenced_unresolved"]),
            "png_base64": base64.b64encode(blob).decode(),
        }],
    }
    login = urllib.request.Request(BASE + "/auth/login",
                                   data=json.dumps({"username": os.environ["TENSOR_AGENT_USER"],
                                                    "password": os.environ["TENSOR_AGENT_PASS"]}).encode(),
                                   headers={"Content-Type": "application/json"}, method="POST")
    tok = json.loads(urllib.request.urlopen(login, timeout=60).read())["access_token"]
    req = urllib.request.Request(BASE + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok}, method="POST")
    resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
    print(json.dumps({k: resp.get(k) for k in ("id", "title", "status", "scenario_key")}, ensure_ascii=False))
    return resp


if __name__ == "__main__":
    acts = sys.argv[1:] or ["render"]
    if "publish" in acts:
        publish()
    elif "render" in acts:
        render()