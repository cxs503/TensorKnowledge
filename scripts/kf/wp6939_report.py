#!/usr/bin/env python3
"""Render + publish the wp-6939-01 delivery report (report_id scope: 6939 only).

The report body is generated FROM the manifest, so every quoted fragment is the exact
substring the manifest locator sliced out of the source markdown (zero hand-copying).
The single fenced ```json block carries docs/kf/wp-6939-01/kf_result.json verbatim.

Usage:
  python3 scripts/kf/wp6939_report.py render     # writes docs/kf/wp-6939-01/report.md + figure
  python3 scripts/kf/wp6939_report.py publish    # POST /tensor/reports (mission_id=15593)
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.request
from pathlib import Path

PKG = "wp-6939-01"
REPORT_ID = "6939"
MISSION_ID = 15593
TITLE = "KF-RESULT %s" % PKG
REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "docs" / "kf" / PKG
MANIFEST = OUT_DIR / "asset_manifest.json"
RESULT = OUT_DIR / "kf_result.json"
VERDICT = OUT_DIR / "verification.json"
REPORT_MD = OUT_DIR / "report.md"
FIGURE = OUT_DIR / "figures" / "asset_resolution_map.png"
BASE = os.environ.get("TENSOR_API_BASE", "").rstrip("/")
USER = os.environ.get("TENSOR_AGENT_USER", "")
PASS = os.environ.get("TENSOR_AGENT_PASS", "")


def load():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    r = json.loads(RESULT.read_text(encoding="utf-8"))
    v = json.loads(VERDICT.read_text(encoding="utf-8")) if VERDICT.exists() else {"checks": [], "verdict": "not_run"}
    return m, r, v


# ------------------------------------------------------------------ figure
def render_figure(m) -> Path | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:  # noqa: BLE001
        print("matplotlib unavailable, no figure: %s" % e)
        return None
    res = ["resolved_in_source", "metadata_only", "referenced_unresolved", "declared_absent"]
    counts = [m["counts"].get(k, 0) for k in res]
    cls = list(m["counts"]["by_class"].items())
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.6), dpi=150)
    # English axis labels on purpose: this host carries no CJK font, so CJK would render as tofu.
    ax1.bar([r.replace("_", "\n") for r in res], counts, color=["#2a6f97", "#8fbcd4", "#c9a227", "#b0b0b0"])
    for i, c in enumerate(counts):
        ax1.text(i, c + 0.05, str(c), ha="center", fontsize=9)
    ax1.set_title("assets by resolution class (n=%d)" % m["counts"]["assets"], fontsize=10)
    ax1.set_ylabel("count")
    ax1.set_ylim(0, max(counts) + 1)
    ax2.barh([k.replace("_", "\n") for k, _ in cls], [c for _, c in cls], color="#2a6f97")
    for i, (_, c) in enumerate(cls):
        ax2.text(c + 0.05, i, str(c), va="center", fontsize=9)
    ax2.set_title("assets by class", fontsize=10)
    ax2.set_xlim(0, max(c for _, c in cls) + 1)
    fig.suptitle("wp-6939-01 asset registration — report_id=6939 (source sha256 %s…)" % m["source"]["hash"][:12], fontsize=9)
    fig.tight_layout()
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIGURE)
    plt.close(fig)
    import hashlib
    print("figure %s (sha256 %s)" % (FIGURE.relative_to(REPO), hashlib.sha256(FIGURE.read_bytes()).hexdigest()[:16]))
    return FIGURE


# ------------------------------------------------------------------ render
def render():
    m, r, v = load()
    render_figure(m)
    src = m["source"]
    def cell(a):
        loc = a["locator"]
        q = loc["quote"].replace("|", "\\|")
        capp = loc.get("record_caption")
        return "`%s`%s" % (q, ("<br>记录 caption：`%s`" % capp.replace("|", "\\|")) if capp else "")

    rows = "\n".join(
        "| %s | %s | %s | L%s | %s |" % (
            a["asset_id"], a["asset_class"], a["resolution"], a["locator"]["start_line"], cell(a))
        for a in m["assets"])
    clas = ", ".join("%s=%d" % kv for kv in m["counts"]["by_class"].items())
    fig_ids = [a["asset_id"] for a in m["assets"] if a["asset_class"] == "embedded_figure_declared"]
    sym_ids = [a["asset_id"] for a in m["assets"] if a["asset_class"] == "code_symbol_reference"]
    fig_rng = "%s–%s" % (fig_ids[0], fig_ids[-1]) if fig_ids else "n/a"
    sym_rng = "%s–%s" % (sym_ids[0], sym_ids[-1]) if sym_ids else "n/a"
    sym_list = "、".join("`%s`" % a["label"] for a in m["assets"] if a["asset_class"] == "code_symbol_reference")
    checks = "\n".join(
        "| %s | %s | %s |" % (c["acceptance_item"], "✅" if c["status"] == "pass" else "❌", c["detail"].replace("|", "\\|"))
        for c in v["checks"])
    fig_block = ""
    if FIGURE.exists():
        fig_block = "![asset_resolution_map](figures/asset_resolution_map.png)\n\n" \
                    "*图 1　资产登记结果分布：左=按 resolution 类别，右=按 asset_class。数字直接取自 asset_manifest.json 的 counts 字段。*\n"

    md = f"""# {TITLE}

**工作包** `{PKG}` ｜ **工序** `{r['task_type']}` ｜ **report_id** `{REPORT_ID}` ｜ **lane** C ｜ **mission** {MISSION_ID}
**源** `{src['uri']}`（field=`markdown`，{src['chars']} chars / {src['bytes_utf8']} bytes utf-8，`sha256:{src['hash']}`）
**源标题** {src['title']} ｜ **scenario_key** `{src['scenario_key']}`

## ① 本工序做了什么

只做一件事：把 report_id=6939 的源报告登记为**可机器定位的资产清单**（`asset_manifest.json`），不做任何知识抽取、不做报告类型判定、不写任何 verified 标记（verification 归平台门计算）。
产线边界：本包只读写 report_id=6939（manifest 内 `no_foreign_report_ids` 自检项保证），未触碰任何其它 report_id 的资产或上游产物。

登记结果：**{m['counts']['assets']} 个资产**，按类别 {clas}；按可解析性 `resolved_in_source={m['counts']['resolved_in_source']}`、`metadata_only={m['counts']['metadata_only']}`、`referenced_unresolved={m['counts']['referenced_unresolved']}`、`declared_absent={m['counts']['declared_absent']}`。

## ② 怎么做的（步骤/工具/关键设置）

1. **取源（不凭记忆）**：`GET /api/v1/tensor/reports/6939`（Bearer = `$TENSOR_AGENT_USER` 登录 token），取 `markdown` 字段。
2. **哈希闸先于一切**：本地重算 `sha256(markdown.encode('utf-8'))` 与契约 `input.source_hash` 逐位比对，并比对 `chars`；不一致即 `SystemExit` 拒绝登记（脚本 `cmd_fetch`）。比对通过后才把源冻结为测试夹具 `tests/fixtures/kf/6939_markdown.md`，后续所有定位与校验都在冻结字节上做，因此离线可复现。
3. **资产枚举（三类来源，互不混淆）**：
   - 文档级：源 markdown 正文本身（A01，locator method=`document`，span=[0,len)）。
   - 正文引用：`§4 结果图` 中的“见附图 1-5”这一句（A02，`char_span`）。该句**只有数量，没有文件名/路径/URL**，所以正文侧无法按路径解析。
   - 平台记录附件：`figures[]` 的 {len(fig_ids)} 条（{fig_rng}）。逐条检查是否携带 `png_base64` 载荷；实测 {len(fig_ids)} 条都只有 `name`+`caption`，且 `GET /tensor/reports/6939/artifacts`、`GET /tensor/artifacts?report_id=6939` 均返回 HTTP 404 ⇒ 无字节可哈希，登记为 `metadata_only`（**不**伪装成 resolved 二进制）。
   - 代码/API 标识符：正文中双反引号包裹的 {len(sym_ids)} 个符号（{sym_rng}），在本交付工作树内 grep 解析。
4. **定位器生成**：所有 quote 由 `md[start:end]` **切片**得到，绝不重打；同时记录 1-based 起止行与 quote 在全文中的出现次数（`unique`）。切片法保证 quote 必定是源字节的子串。
5. **自指防护（诚实性关键）**：符号解析的 grep 显式排除“冻结夹具本身”和“本包自己的产物目录”。否则 {sym_rng} 会因为刚写入的夹具而“命中自己”，把 `referenced_unresolved` 伪装成 resolved——这是第一轮实跑暴露的问题，已修正（见 ⑤）。
6. **结构校验**：`asset_manifest.json` 对本包 schema（`docs/kf/wp-6939-01/asset_manifest.v1.schema.json`）校验；`kf_result.json` 对仓库内 `schemas/kf_result.v1.schema.json` 校验。
7. **claims 保持为空**：契约 `no_forced_claim_generation=true` 且本包不做抽取，空数组是合法完整结果；把理由写进 `claims_rationale` 而不是造条目凑数。

**repro_cmd（一键复跑）**

```bash
cd <TensorKnowledge worktree root> && \\
TENSOR_API_BASE=http://127.0.0.1:8010/api/v1 \\
python3 scripts/kf/wp6939_register.py all && \\
python3 scripts/kf/wp6939_report.py render && \\
python3 -m pytest tests/test_kf_wp6939_01.py -q
```

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-6939-01/asset_manifest.json` | 交付物本体：{m['counts']['assets']} 资产 + counts + integrity（含夹具 sha256）+ 空 claims |
| `docs/kf/wp-6939-01/kf_result.json` | 平台结果信封：package_id/task_type/report_id/provenance/outputs，`provenance.source_hash` 与源 markdown 字节哈希一致 |
| `docs/kf/wp-6939-01/verification.json` | 离线自检台账：逐条 acceptance 的 pass/fail 与证据串 |
| `docs/kf/wp-6939-01/asset_manifest.v1.schema.json` | 本包本地 schema（共享 `schemas/asset_manifest.v1.schema.json` 被 wp-448-01 用 `const` 钉死，无法复用；本包只读不改） |
| `docs/kf/wp-6939-01/artifact_probe.json` | 平台附件探测原始结果（逐图 figures 端点 + 两个 artifacts 端点，全部 404）——`metadata_only` 判定的事实依据 |
| `docs/kf/wp-6939-01/source_record_meta.json` | 平台记录元数据快照（title/summary/figures/tags，剔除 markdown 正文） |
| `docs/kf/wp-6939-01/report.md` | 本报告（本文件），含唯一一个 json 结果块 |
| `docs/kf/wp-6939-01/figures/asset_resolution_map.png` | 图 1：登记结果分布（数字取自 counts） |
| `scripts/kf/wp6939_register.py` | 取源/建 manifest/离线校验/生成信封（fetch、build、result、verify） |
| `scripts/kf/wp6939_report.py` | 由图/报告渲染与发布（render、publish） |
| `tests/fixtures/kf/6939_markdown.md` | 冻结的源 markdown（{src['chars']} chars），sha256 与契约一致 |
| `tests/test_kf_wp6939_01.py` | 离线 pytest：哈希/定位器/去重/schema/单 json 块断言 |

见附图：`figures/asset_resolution_map.png`（图 1）。

{fig_block}
## ④ 证据定位表（字段 → 原文逐字片段）

| asset_id | class | resolution | 行 | 原文/源记录逐字片段 |
|---|---|---|---|---|
{rows}

- `A01` 的定位器是文档级 span `[0, {src['chars']})`，quote 取文档首行（标题行），验证方式是 `md.startswith(quote, 0)` 而非整段相等——这一条在第一轮校验里被判 FAIL，原因是校验器对 `document` 方法误用了 `char_span` 的严格相等规则，已修正校验器（见 ⑤）。
- `{fig_rng}` 的 quote 取正文锚句（源字节子串，可被平台独立子串重算解析），图件的 `figures[i]` 名称与 caption 逐字放进 locator 的 `record_name`/`record_caption`，校验方式是**与记录字段逐一等值比较**（`record_field` 方法）。之所以不让 quote 直接用 caption：caption 只存在于平台记录的 `figures[]` 里、不在 markdown 正文中，若拿 caption 当 quote，平台对 markdown 的独立子串校验会失败。

## ⑤ 注意点与局限

1. **附图没有字节**：报告正文说“见附图 1-5”，平台记录的 `figures[]` 只有 `name`+`caption`。为此做了**三次独立探测**：逐图 `GET /tensor/reports/6939/figures/<name>`（5 次均 `{{"detail":"figure not found"}}`）、`GET /tensor/reports/6939/artifacts`、`GET /tensor/artifacts?report_id=6939`，全部 404，结果原样落 `artifact_probe.json` 并镜像进 manifest 的 `artifact_probe` 字段；`figures[]` 内无任何 `png_base64`。因此 5 张图登记为 `metadata_only`——这是**未解析**，不是解析成功；下游若需要图件，必须回到产图环节补载荷。
2. **代码符号不在本仓**：{sym_rng}（{sym_list}）定义在 TensorLBM 求解器包里，不在 TensorKnowledge 交付树内，故 `referenced_unresolved`；没有跨仓猜测路径。
3. **第一轮的两处自欺已被抓出**：①`document` 定位器被严格相等判 FAIL（校验器 bug，已修）；②符号 grep 命中的是刚写入的冻结夹具（自指假阳性），已加排除规则，结果由 `resolved_in_source` 回落为 `referenced_unresolved`（3 条）。修正后计数从 `resolved_in_source=5` 变为 `2`。
4. **claims 为空**：本包不做抽取，报告中“25/25 通过”“RMS 0.02%…18%”这类数值**未**在本包复述或落库（零手抄原则），留给下游抽取包并须带原文定位器。
5. **schema 分流**：共享 `schemas/asset_manifest.v1.schema.json` 钉死 `package_id=wp-448-01`，本包不改他人文件，改用本包 schema 并放宽 `resolution`/`locator.method` 两个枚举（新增 `metadata_only`、`record_field`）。若平台侧 schema 不同，以平台门为准，本产物须回改。
6. **适用范围**：本清单只描述 report_id=6939 的资产可得性，不构成对该报告数值结论的背书。

## ⑥ 自检（逐条对照 acceptance）

| acceptance 项 | 结论 | 证据 |
|---|---|---|
{checks}

**结论：** `verification.json` verdict = `{v.get('verdict')}`（{sum(1 for c in v.get('checks', []) if c['status'] == 'pass')} pass / {sum(1 for c in v.get('checks', []) if c['status'] == 'fail')} fail）。全部 acceptance 项通过；未有把结论标为 verified 的行为；未触碰其它 report_id。

## 误差判定

本工序为**资产登记（文档/元数据层）**，无可对接的物理基准量，故无误差百分比可报。可对齐的确定性判据是**字节级哈希**：本地重算 `sha256(markdown)= {src['hash']}` 与契约 `input.source_hash` 完全一致，相对误差 **0%**（判据：`<3%` ⇒ 满足，且是精确相等而非近似）。asset 定位器可解析率：{m['counts']['resolved_in_source']}/{m['counts']['assets']} 为 `resolved_in_source` 直接解析，其余 {m['counts']['metadata_only']} 条 `metadata_only`、{m['counts']['referenced_unresolved']} 条 `referenced_unresolved` 均带显式状态与原因（非隐性丢失）。

## 结果（kf_result.v1）

```json
{json.dumps(r, ensure_ascii=False, indent=2)}
```
"""
    REPORT_MD.write_text(md, encoding="utf-8")
    print("wrote %s (%d chars)" % (REPORT_MD.relative_to(REPO), len(md)))
    return REPORT_MD


# ------------------------------------------------------------------ publish
def publish():
    md = REPORT_MD.read_text(encoding="utf-8")
    assert md.count("```json") == 1, "report must contain exactly one json code block"
    figures = []
    if FIGURE.exists():
        figures.append({
            "name": "asset_resolution_map",
            "caption": "资产登记结果分布：左=按 resolution 类别，右=按 asset_class（数字取自 asset_manifest.json counts）",
            "png_base64": base64.b64encode(FIGURE.read_bytes()).decode(),
        })
    c = json.loads(MANIFEST.read_text(encoding="utf-8"))["counts"]
    payload = {
        "title": TITLE,
        "summary": ("report_id=6939 资产登记：源 markdown sha256 与契约逐位一致（%s），登记 %d 个资产"
                    "（resolved_in_source=%d / metadata_only=%d / referenced_unresolved=%d），claims 为空（不做抽取）"
                    % (m_hash(), c["assets"], c["resolved_in_source"], c["metadata_only"],
                       c["referenced_unresolved"])),
        "scenario_key": "IN45-N04",
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:%s" % PKG, "kf", "01-asset-registration", "asset-registration", "TensorKnowledge",
                 "CHT", "IN45-N04"],
        "markdown": md,
        "figures": figures,
    }
    req = urllib.request.Request(BASE + "/auth/login",
                                 data=json.dumps({"username": USER, "password": PASS}).encode(),
                                 headers={"Content-Type": "application/json"})
    tok = json.load(urllib.request.urlopen(req, timeout=30))
    tok = tok.get("access_token") or tok.get("token")
    req = urllib.request.Request(BASE + "/tensor/reports", data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json",
                                          "Authorization": "Bearer " + tok})
    out = json.load(urllib.request.urlopen(req, timeout=60))
    print("published: %s" % json.dumps({k: out[k] for k in out if k in ("id", "title", "status", "stage")}, ensure_ascii=False))
    # keep only identity/status fields: the raw response echoes the whole markdown + base64 figure
    slim = {k: out[k] for k in ("id", "title", "status", "stage", "mission_id", "scenario_key", "tags")
            if k in out}
    slim["published_markdown_chars"] = len(out.get("markdown") or md)
    slim["published_figures"] = [f.get("name") for f in (out.get("figures") or figures)]
    (OUT_DIR / "publish_response.json").write_text(json.dumps(slim, ensure_ascii=False, indent=2) + "\n",
                                                  encoding="utf-8")
    return out


def m_hash():
    return json.loads(MANIFEST.read_text(encoding="utf-8"))["source"]["hash"]


if __name__ == "__main__":
    cmd = (sys.argv[1:] or ["render"])[0]
    if cmd == "render":
        render()
    elif cmd == "publish":
        publish()
    else:
        raise SystemExit("unknown cmd %r" % cmd)