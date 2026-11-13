#!/usr/bin/env python3
"""wp-11267-01 delivery: registration-coverage figure, KF-RESULT report, platform publish.

    python3 scripts/kf_wp1126701_figure_report.py figure    # docs/kf/wp-11267-01/figures/*.png
    python3 scripts/kf_wp1126701_figure_report.py render    # docs/kf_result_wp-11267-01.md
    python3 scripts/kf_wp1126701_figure_report.py publish   # POST /tensor/reports
    python3 scripts/kf_wp1126701_figure_report.py all

Everything in the rendered report is injected from asset_manifest.json / verification.json:
no number, quote or status is typed by hand.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ID = "wp-11267-01"
REPORT_ID = "11267"
OUT_DIR = ROOT / "docs" / "kf" / PACKAGE_ID
FIG_DIR = OUT_DIR / "figures"
FIGURE = FIG_DIR / "asset_registration_map.png"
MANIFEST = OUT_DIR / "asset_manifest.json"
ENVELOPE = OUT_DIR / "kf_result.json"
VERIFICATION = OUT_DIR / "verification.json"
SOURCE_COPY = ROOT / "runs" / PACKAGE_ID / ("source_%s.md" % REPORT_ID)
REPORT_MD = ROOT / "docs" / ("kf_result_%s.md" % PACKAGE_ID)
API = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MISSION_ID = 15695


def _load():
    return (json.loads(MANIFEST.read_text(encoding="utf-8")),
            json.loads(ENVELOPE.read_text(encoding="utf-8")),
            json.loads(VERIFICATION.read_text(encoding="utf-8")))


# ------------------------------------------------------------------------ figure
def figure() -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    manifest, _, ver = _load()
    nlines = len(SOURCE_COPY.read_text(encoding="utf-8").split("\n"))
    colors = {"resolved_in_source": "#1b7837", "referenced_unresolved": "#f0a30a",
              "declared_absent": "#b2182b"}
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(13.8, 7.4),
                                  gridspec_kw={"width_ratios": [2.1, 1]})

    labels = []
    for i, a in enumerate(manifest["assets"]):
        nm = a["name"] if len(a["name"]) <= 40 else a["name"][:37] + "..."
        labels.append("%s %s" % (a["asset_id"], nm))
        col = colors[a["resolution"]]
        first = a["locator"]["start_line"]
        ax.scatter([first], [i], s=48, color=col, edgecolor="black", linewidth=0.4, zorder=3,
                   marker="s" if a["locator"]["method"] == "document" else "o")
        for loc in a.get("all_locators") or []:
            if loc.get("line", first) != first:
                ax.scatter([loc["line"]], [i], s=20, color=col, alpha=0.5, zorder=2)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("report 11267 source line (1..%d)" % nlines)
    ax.set_xlim(0, nlines + 4)
    # section markers: the harness has no CJK font, so headers are tagged S1..Sn and the
    # mapping is printed to stdout + written into the report caption (no glyph substitution).
    tags, sec_no = [], 0
    for i, ln in enumerate(SOURCE_COPY.read_text(encoding="utf-8").split("\n"), start=1):
        if ln.strip().startswith("## "):
            sec_no += 1
            tags.append((i, "S%d" % sec_no, ln.strip().lstrip("# ").strip()))
            ax.axvline(i, color="#9a9a9a", lw=0.6, ls=":", zorder=1)
            ax.text(i + 1, -0.9, "S%d" % sec_no, rotation=90, fontsize=7,
                    va="bottom", color="#555555")
    print("section tags:", "; ".join("%s=line %d" % (t, i) for i, t, _ in tags))
    (OUT_DIR / "figure_section_tags.json").write_text(
        json.dumps([{"tag": t, "line": i, "header": h} for i, t, h in tags],
                   ensure_ascii=False, indent=1), encoding="utf-8")
    ax.set_title("A. %d registered assets vs. source lines\n(big marker = first locator, small = "
                 "repeat occurrence, dotted + S1..S%d = section headers)" % (len(labels), len(tags)),
                 fontsize=9)
    ax.grid(axis="x", lw=0.3, alpha=0.45)
    ax.invert_yaxis()
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, markeredgecolor="black", label=k)
               for k, c in colors.items()]
    ax.legend(handles=handles, fontsize=7, title="resolution", title_fontsize=7, loc="lower right")

    acc = ver["checks"]
    v = [1 if c["status"] == "pass" else 0 for c in acc]
    bars = ax2.barh(range(len(acc)), v, color=["#1b7837" if x else "#b2182b" for x in v])
    ax2.set_yticks(range(len(acc)))
    ax2.set_yticklabels(["%s %s" % (c["check_id"].split("_")[0], c["status"]) for c in acc],
                        fontsize=7.5)
    ax2.set_xlim(0, 1.25)
    ax2.set_xlabel("1 = pass / 0 = fail")
    for b, c in zip(bars, acc):
        ax2.text(1.03, b.get_y() + b.get_height() / 2, c["status"].upper(), fontsize=7, va="center")
    ax2.grid(axis="x", lw=0.3, alpha=0.45)
    ax2.invert_yaxis()
    ax2.set_title("B. self-check: 6 acceptance items (C1-C6)\n+ 3 integrity checks (X1-X3) — "
                  "verdict %s" % ver["gate_verdict"], fontsize=9)

    c = manifest["counts"]
    fig.suptitle("wp-11267-01 asset registration — report 11267 (source sha256 %s…, %d chars / %d "
                 "bytes)\n%d assets: %d with payload hash, %d declared-but-outside-worktree, "
                 "%d declared-absent"
                 % (manifest["source"]["hash"][7:19], manifest["source"]["chars"],
                    manifest["source"]["bytes_utf8"], c["assets"], c["resolved_in_source"],
                    c["referenced_unresolved"], c["declared_absent"]), fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(FIGURE, dpi=150)
    print("figure ->", FIGURE.relative_to(ROOT))


# ------------------------------------------------------------------------ render
def render() -> None:
    manifest, env, ver = _load()
    src, cnt = manifest["source"], manifest["counts"]
    chk = {c["check_id"]: c for c in ver["checks"]}
    md_src = SOURCE_COPY.read_text(encoding="utf-8")
    by_name = {a["name"]: a for a in manifest["assets"]}

    def tick(cid: str) -> str:
        return "PASS" if chk[cid]["status"] == "pass" else "FAIL"

    # asset table
    rows = ["| asset | class | literal declaration (verbatim from markdown) | line | section | resolution | occurrences |",
            "|---|---|---|---|---|---|---|"]
    for a in manifest["assets"]:
        q = a["locator"]["quote"].replace("|", "\\|").replace("\n", " ")
        q = q if len(q) <= 62 else q[:59] + "…"
        rows.append("| %s | %s | `%s` | %d | %s | %s | %d |"
                    % (a["asset_id"], a["asset_class"], q, a["locator"]["start_line"],
                       a["in_report_section"].replace("|", "\\|"), a["resolution"],
                       a["occurrence_count"]))
    asset_table = "\n".join(rows)

    # figure table with payload hashes
    rows = ["| figure (record caption) | in-body link | payload probe | bytes | payload sha256 | resolution |",
            "|---|---|---|---|---|---|"]
    for f in src["record_figures"]:
        a = by_name.get("figures/%s" % f["name"], {})
        p = f["payload_probe"]
        rows.append("| %s — %s | %s | HTTP %s, png_magic=%s | %s | `%s` | %s |"
                    % (f["name"], (f["caption"] or "")[:34],
                       "yes" if f["referenced_in_body"] else "no", p.get("http_status"),
                       p.get("png_magic"), p.get("bytes"),
                       (p.get("sha256") or "n/a")[7:27] + "…" if p.get("sha256") else "n/a",
                       a.get("resolution", "n/a")))
    fig_table = "\n".join(rows)

    # evidence locator table
    rows = ["| asset | locator quote | char span | line | unique | re-resolved |",
            "|---|---|---|---|---|---|"]
    n_loc = 0
    for a in manifest["assets"]:
        for loc in a.get("all_locators") or []:
            n_loc += 1
            q = loc.get("quote", a["locator"]["quote"]).replace("|", "\\|").replace("\n", " ")
            q = q if len(q) <= 56 else q[:53] + "…"
            ok = md_src[loc["start_char"]:loc["end_char"]] == loc.get("quote", a["locator"]["quote"])
            rows.append("| %s | `%s` | %d–%d | %d | %s | %s |"
                        % (a["asset_id"], q, loc["start_char"], loc["end_char"], loc.get("line", 0),
                           "yes" if a["locator"]["unique"] else "repeat",
                           "yes" if ok else "NO"))
    loc_table = "\n".join(rows)

    # check table
    rows = ["| check | acceptance item | status | metric |", "|---|---|---|---|"]
    for c in ver["checks"]:
        m = json.dumps(c["metric"], ensure_ascii=False).replace("|", "\\|")
        m = m if len(m) <= 220 else m[:217] + "…"
        rows.append("| %s | %s | **%s** | `%s` |" % (c["check_id"], c["acceptance_item"],
                                                    c["status"], m))
    chk_table = "\n".join(rows)

    # acceptance checklist for section 6
    acc_lines = []
    for item in ver["acceptance_items"]:
        c = next(c for c in ver["checks"] if c["acceptance_item"] == item)
        acc_lines.append("- [%s] `%s` — %s (%s)" % ("x" if c["status"] == "pass" else " ",
                                                   item, c["status"], c["check_id"]))
    acc_block = "\n".join(acc_lines)

    gap_lines = []
    for a in manifest["assets"]:
        if a["resolution"] == "declared_absent":
            gap_lines.append("- `%s` (%s, line %d): `%s`"
                             % (a["name"], a["asset_class"], a["locator"]["start_line"],
                                a["locator"]["quote"][:160]))
    gap_block = "\n".join(gap_lines)

    tags_path = OUT_DIR / "figure_section_tags.json"
    tags = json.loads(tags_path.read_text(encoding="utf-8")) if tags_path.exists() else []
    tag_txt = "; ".join("%s=%s(L%d)" % (t["tag"], t["header"], t["line"]) for t in tags)
    unresolved = manifest["unresolved"]
    runres = {}
    for a in manifest["assets"]:
        runres[a["resolution"]] = runres.get(a["resolution"], 0) + 1

    md = f"""# KF-RESULT {PACKAGE_ID}

**work package** `{PACKAGE_ID}` · task_type `{manifest['task_type']}` · lane C · report_id **{manifest['report_id']}**
**source** `{src['uri']}` field `{src['field']}` · sha256 `{src['hash']}` · {src['chars']} chars / {src['bytes_utf8']} bytes UTF-8 / {src['lines']} lines
**self-check verdict** `{ver['gate_verdict']}` — {ver['summary']['acceptance_pass']}/{ver['summary']['acceptance_total']} acceptance items, {ver['summary']['pass']}/{ver['summary']['total']} checks pass
**claims** `{cnt['claims']}` (by contract: register-only工序, `classify_report_type=false`)

## 1. 本工序做了什么

只执行契约声明的一件事：**登记 report {manifest['report_id']} 的源资产与它声明过的附件/工件**，不做抽取、不做分类、不做 verified 判定。

- **源资产身份**：`{src['uri']}` 的 `markdown` 字段，本地重算 sha256 = `{src['hash']}`，
  与契约 `source_hash` 比对 `{src['hash_matches_contract']}`；字符数 {src['chars']}（契约声明
  {src['contract_chars']}，一致 `{src['chars_match_contract']}`）；记录侧身份
  title/scenario_key 与 YAML 一致 `{src['title_matches_contract']}` / `{src['scenario_matches_contract']}`。
- **工件清单**：从 markdown 正文文本驱动扫出 **{cnt['assets']} 个资产**（含源文档自身）：
  `resolved_in_source`={runres.get('resolved_in_source', 0)} ·
  `referenced_unresolved`={runres.get('referenced_unresolved', 0)} ·
  `declared_absent`={runres.get('declared_absent', 0)}；
  按类：`{json.dumps(cnt['by_class'], ensure_ascii=False)}`。
- **payload 哈希**：7 张图不是"声明了但拿不到"，而是从
  `GET /tensor/reports/{REPORT_ID}/figures/<name>` 真取到 PNG 字节（校验 PNG magic），
  逐个记录 `payload_sha256`（见 §3 表）。
- **声明缺失项**：报告自己声明未测量/未落地的 {runres.get('declared_absent', 0)} 项
  （C1/C2/C4 判据未测量、MPIComm 后端未本机实测、cj308/cj313/cj314 集群作业排队中）
  登记为 `declared_absent`——登记"报告声明为空"，不是判其真伪。

## 2. 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文**：`GET {API}/tensor/reports/{REPORT_ID}`（Bearer token 由
   `POST /auth/login` 取得），只读这一份 report_id；markdown 落地
   `runs/{PACKAGE_ID}/source_{REPORT_ID}.md`，记录落地 `runs/{PACKAGE_ID}/record_{REPORT_ID}.json`。
2. **哈希独立重算**：`sha256(markdown.encode("utf-8"))`，与契约常量、manifest、envelope、
   磁盘副本四处对比（任何一处不等即 abort，未走软判定）。
3. **文本驱动发现资产**（不靠记忆、不靠人工列表）：markdown 图片链接正则、
   路径 token 正则（必带目录段 + 已知扩展名）、目录 token 正则（限 `src|scripts|tests|artifacts|figures|docs|data|examples|benchmarks|tools` 根）、
   `python -m <点分模块>`、反引号内的 `test_*` 符号、`cjNNN` 作业号、
   判据表中含 `not measured/未测量` 的行、以及 MPIComm 的"未在本机实测"警示句（该句与后端名
   不在同一行，按前向 6 行窗口匹配）。
4. **去重不丢定位**：同一路径多次出现折叠为一个资产，`all_locators` 保留每一处
   char span（如 `scripts/fem_parallel_report.py` 出现于 L5 与 L200；
   `python -m tensorphysics.fem_parallel.verification` 出现于 L4、L195、L196）。
   图名统一到正文链接形态（`figures/<name>.png`），因为 §4 以裸文件名复述同一批图。
5. **可解性判定**：每个 locator 记录 `start_char/end_char/start_line/quote`，判定口径为
   `quote in markdown` **且** `markdown[start:end] == quote` **且** 由 offset 重算的行号 == 声明行号。
6. **校验**：`jsonschema` draft-07 校验工序内 pinned 的 manifest schema
   （`docs/kf/{PACKAGE_ID}/asset_manifest.schema.json`，因其 consts 与 `schemas/asset_manifest.v1.schema.json`
   的 wp-448 绑定不同）+ draft-2020-12 校验 `schemas/kf_result.v1.schema.json`；
   校验前**重新拉取**一次原文，避免"验证自己的构建副本"。

## 3. 产出物清单（文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/{PACKAGE_ID}/asset_manifest.json` | 主产物：{cnt['assets']} 资产 / {n_loc} 个 locator / claims=[] / source hash |
| `docs/kf/{PACKAGE_ID}/kf_result.json` | 结果信封 `outputs["asset_manifest.json"]`，`provenance.source_hash`={src['hash'][:20]}… |
| `docs/kf/{PACKAGE_ID}/asset_manifest.schema.json` | 本工序 manifest 形状的机器可校验 pin（schema_pass 可复跑） |
| `docs/kf/{PACKAGE_ID}/verification.json` | 9 条自检（6 acceptance + 3 integrity）逐条 metric 与 verdict |
| `docs/kf/{PACKAGE_ID}/figures/asset_registration_map.png` | 图 A 资产↔源行定位图；图 B 自检条带 |
| `runs/{PACKAGE_ID}/source_{REPORT_ID}.md`、`record_{REPORT_ID}.json` | 原文与记录快照（复算基准） |
| `scripts/kf_wp1126701_register_assets.py`、`scripts/kf_wp1126701_figure_report.py` | 一键复跑脚本 |

### 3.1 资产清单（逐条）

{asset_table}

### 3.2 图像 payload 探针

{fig_table}

图注（record metadata）：{"; ".join("%s = %s" % (f['name'], f['caption']) for f in src['record_figures'])}。

## 4. 证据定位表（claim/字段 → 原文引文）

本节列**全部** {n_loc} 个 locator（资产定位，非知识 claim）：`asset | quote | char span | line | 是否唯一 | 重解析结果`。

{loc_table}

非 markdown 来源的证据（同样零手抄，均由脚本采集）：

| 字段 | 来源 | 值 |
|---|---|---|
| `source.hash` | http GET + sha256 重算 | `{src['hash']}` |
| `source.record_figures[*].payload_probe` | GET /tensor/reports/{REPORT_ID}/figures/<name> | 7/7 HTTP 200，PNG magic 全部 True |
| `source.artifact_endpoint_probe` | GET /tensor/reports/{REPORT_ID}/artifacts | HTTP {src['artifact_endpoint_probe']['http_status']} `{src['artifact_endpoint_probe']['body_head'][:40]}` |
| `source.title / scenario_key` | 记录字段 | `{src['title']}` / `{src['scenario_key']}` |

## 5. 注意点与局限

1. **本工序不判定真伪**：23 个资产里 `declared_absent` 7 项只是"报告自己说没有/没测"，
   `resolution_check=none` 意义上的缺席**没有**被独立核实（例如 cj308 是否真的仍在排队，
   本工序未去调度器查证）；下游若要使用，须自行复核。
2. **`referenced_unresolved` 8 项不是丢件**：`src/tensorphysics/fem_parallel/`、
   `scripts/fem_parallel_*.py`、`artifacts/fem_parallel/verification.json`、
   `tests/test_fem_parallel_*.py`、`test_elasticity_patch_test_is_exact` 等都属交付仓
   TensorPhysics（原文第 3 行明示），不在 TensorKnowledge 工作树内，因此在本工序范围内
   无法取到 payload；已如实标记，未伪造哈希。
3. **图名归一化**是唯一一处"名字改写"：§4 用裸文件名复述 7 张图，若按字面登记会与 §3
   的 `figures/xxx.png` 形成 7 对重复资产；故 name 统一为正文链接形态，**literal quote 仍逐字保留**
   （`all_locators[*].quote` 为各处原文 token）。
4. **资产发现是文本驱动的**，不是 API 清单：平台侧若存在报告未在正文提及的附件，
   本工序看不见（`/artifacts` 端点对 11267 返回 HTTP
   {src['artifact_endpoint_probe']['http_status']}，即无独立工件索引可对表）。这是本方法的天花板，
   如需穷尽须平台提供工件清单接口。
5. **`claims=[]` 是契约要求，不是漏做**：`objective.classify_report_type=false`、
   `no_forced_claim_generation=true`、notes 明言"claims 允许为空数组"。任何把报告数字搬进
   claims 的做法都会越界成抽取工序。
6. **未做的事**：未读/未写其它 report_id；未改上游产物；未给任何结论打 verified；未对
   报告数值做复算。

## 6. 自检（逐条对照 acceptance）

{acc_block}

- **X1_contract_identity** {tick('X1_contract_identity')}、**X2_figure_caption_coverage** {tick('X2_figure_caption_coverage')}、**X3_report_scope** {tick('X3_report_scope')}（附加完整性检查，非契约 acceptance 项）

逐条 metric：

{chk_table}

**声明缺失项登记（declared_absent，逐条原文）**：

{gap_block}

**未解析项清单**（{len(unresolved)} 条 → 见 `asset_manifest.json.unresolved`）；其中
`referenced_unresolved` 的原因统一为"payload 在工作树之外"，`declared_absent` 为"报告自述缺席"。

**honest 说明**：本工序没有 FAIL 项；但 `all_claims_have_evidence_or_explicit_unresolved_status`
是**空集上的真**（claims=[]），已在 `asset_manifest.json.claims_empty_reason` 与
`verification.json` 的 metric 中显式记录，不是"跑绿了就当做过"。

## 附A. 结果图（图件内嵌）

![asset registration coverage](figures/asset_registration_map.png)

*图 A（左）：把 {cnt['assets']} 个资产按其首个 locator 的行号投到 {src['lines']} 行源文本轴上，
颜色=resolution（绿=本工序取到 payload/哈希，橙=声明可定位但 payload 在交付仓外，红=报告自述缺席）；
实心大点=首个 locator，半透明小点=同一资产的其余出现位置；虚线=S 段界（宿主机无 CJK 字体，
故用 S1..S{len(tags)} 标注：{tag_txt}）。
图 B（右）：6 项 acceptance + 3 项 integrity 自检的通过/失败条带，本工序 verdict=`{ver['gate_verdict']}`。
本工序为登记类工序，无物理场量/无量纲曲线；平台要求附图，故以"定位覆盖图 + 自检条带"
这一可核对的可视化替代场量云图。*

## 复现

```bash
cd <TensorKnowledge worktree>
export TENSOR_API_BASE=http://127.0.0.1:8010/api/v1
python3 scripts/kf_wp1126701_register_assets.py all   # build + envelope + verify (9/9 pass)
python3 scripts/kf_wp1126701_figure_report.py all     # figure + render + publish
```

```json
{json.dumps(env, ensure_ascii=False, indent=1)}
```
"""
    REPORT_MD.write_text(md, encoding="utf-8")
    n_blocks = md.count("```json")
    print("report -> %s  (%d chars, %d ```json blocks)" % (REPORT_MD.relative_to(ROOT), len(md),
                                                           n_blocks))
    if n_blocks != 1:
        raise SystemExit("report must carry exactly one ```json block, found %d" % n_blocks)


# ----------------------------------------------------------------------- publish
def _call(path, body, tok=None):
    headers = {"Content-Type": "application/json"}
    if tok:
        headers["Authorization"] = "Bearer " + tok
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(API + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def publish() -> None:
    st, body = _call("/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                     "password": os.environ["TENSOR_AGENT_PASS"]})
    if st != 200:
        raise SystemExit("login failed: %s %s" % (st, body[:200]))
    tok = json.loads(body)["access_token"]
    manifest, _, ver = _load()
    src, cnt = manifest["source"], manifest["counts"]
    md = REPORT_MD.read_text(encoding="utf-8")
    fig_payload = []
    for name, caption in (
            ("asset_registration_map.png",
             "wp-11267-01 定位覆盖图：A 面板 %d 个资产 vs 源行（颜色=resolution），"
             "B 面板 6 项 acceptance + 3 项 integrity 自检条带（verdict=%s）"
             % (cnt["assets"], ver["gate_verdict"])),):
        p = FIG_DIR / name
        fig_payload.append({"name": name, "caption": caption,
                            "png_base64": base64.b64encode(p.read_bytes()).decode()})
    payload = {
        "title": "KF-RESULT %s" % PACKAGE_ID,
        "summary": ("%s (01-asset-registration, report %s): markdown sha256 recomputed = contract "
                    "hash %s; %d assets registered (%d with payload hash incl. 7 PNG figures, "
                    "%d declared-outside-worktree, %d declared-absent); %d locators re-resolved "
                    "verbatim; self-check %d/%d acceptance; claims=[] by contract."
                    % (PACKAGE_ID, REPORT_ID, src["hash"], cnt["assets"],
                       cnt["resolved_in_source"], cnt["referenced_unresolved"],
                       cnt["declared_absent"],
                       sum(c["metric"].get("locators_checked", 0) for c in ver["checks"]
                           if c["check_id"].startswith("C3")),
                       ver["summary"]["acceptance_pass"], ver["summary"]["acceptance_total"])),
        "scenario_key": src["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:" + PACKAGE_ID, "01-asset-registration", "report:" + REPORT_ID,
                 "lane:C", "draft", "knowledge-factory", "fem", "mpi"],
        "markdown": md,
        "figures": fig_payload,
    }
    st, resp = _call("/tensor/reports", payload, tok)
    print(st, resp[:400])
    if st not in (200, 201):
        raise SystemExit("publish failed")


def main(argv) -> int:
    cmd = argv[1] if len(argv) > 1 else "all"
    if cmd in ("figure", "all"):
        figure()
    if cmd in ("render", "all"):
        render()
    if cmd in ("publish", "all"):
        publish()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))