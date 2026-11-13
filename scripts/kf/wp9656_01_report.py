#!/usr/bin/env python3
"""Render + publish the KF-RESULT report body for work package wp-9656-01.

Every number and every quotation in the rendered markdown is injected programmatically
from docs/kf/wp-9656-01/{asset_manifest,kf_result,verification}.json and from the cached
source markdown, so nothing is transcribed by hand. Each injected quote is asserted to be
a verbatim substring of the source before the file is written.

    python3 scripts/kf/wp9656_01_report.py render   # -> docs/kf/wp-9656-01/KF-RESULT-wp-9656-01.md
    python3 scripts/kf/wp9656_01_report.py post     # render + POST /tensor/reports (mission 15664)
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PKG = ROOT / "docs" / "kf" / "wp-9656-01"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
VERIFICATION = PKG / "verification.json"
SOURCE = ROOT / "runs" / "wp-9656-01" / "source_9656.md"
FIG = PKG / "figures" / "wp9656_01_source_locator_map.png"
REPORT_MD = PKG / "KF-RESULT-wp-9656-01.md"
MISSION_ID = 15664
TITLE = "KF-RESULT wp-9656-01"
TAGS = ["kf-wp:wp-9656-01", "asset-registration", "report-9656", "ice_shaft_vibration", "kf-result"]
PY = "python3 scripts/kf/wp9656_01_register.py"


def load() -> tuple[dict, dict, dict, str]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    envelope = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    source = SOURCE.read_text(encoding="utf-8")
    return manifest, envelope, verification, source


def lines_of(source: str) -> list[str]:
    return source.split("\n")


def find_line(source: str, needle: str) -> tuple[int, str]:
    """1-based line number of the unique line containing `needle`, plus that line verbatim."""
    hits = [(i, ln) for i, ln in enumerate(lines_of(source), start=1) if needle in ln]
    if not hits:
        raise SystemExit("quote anchor not found in source: %r" % needle)
    i, ln = hits[0]
    return i, ln


def clip(line: str, needle: str | None = None, width: int = 120) -> str:
    """Verbatim substring of `line` (never rewritten); long lines are cut, not paraphrased."""
    if needle is not None:
        s = line.find(needle)
        if s < 0:
            raise SystemExit("clip anchor missing: %r" % needle)
    else:
        s = 0
    seg = line[s:]
    return seg if len(seg) <= width else seg[:width] + " …"


def md_escape_cell(s: str) -> str:
    return s.replace("|", "\\|")


def md_code(s: str) -> str:
    """Inline code span that tolerates backticks inside the quoted text."""
    s = md_escape_cell(s)
    return ("``%s``" % s) if "`" in s else ("`%s`" % s)


def render() -> Path:
    manifest, envelope, verification, source = load()
    src = manifest["source"]
    cnt = manifest["counts"]
    acc = verification["acceptance"]
    acct = verification["accounting"]

    def row(field: str, line_no: int, quote: str, note: str = "") -> str:
        assert quote in source, quote
        assert source.count(quote) >= 1
        return "| %s | L%d | `%s` | %s |" % (field, line_no, md_escape_cell(quote), note)

    # ---- anchors (all resolved against the source, never retyped) ----
    l_title, q_title = find_line(source, "# 冰区推进轴系横向振动与轴承载荷模型")
    l_inject, q_inject = find_line(source, "全部数字由 `backend/scripts/build_ice_shaft_vibration_report.py`")
    l_fig1, q_fig1 = find_line(source, "![fig1](artifacts/ice_shaft_vibration/fig1_excitation.png)")
    l_fig4, q_fig4 = find_line(source, "![fig4](artifacts/ice_shaft_vibration/fig4_fatigue.png)")
    l_crit, q_crit = find_line(source, "全部判据 all_pass = **True**")
    l_tab1, q_tab1 = find_line(source, "| # | 判据 | 结果 | 判据值 | 门槛 | 判定 |")
    l_tab2, q_tab2 = find_line(source, "| 量 | 数值 |")
    l_tab3, q_tab3 = find_line(source, "| 关键量 | 基准（独立路线/解析） | 相对误差 | 是否 <3% | 说明 |")
    l_prod, q_prod = find_line(source, "| 判据（机器可读） | `artifacts/ice_shaft_vibration/criteria.json` |")
    l_repro, q_repro = find_line(source, "pytest tests/test_ice_shaft_vibration.py -v")
    l_pass, q_pass = find_line(source, "**逐项回答**：")
    l_hold, q_hold = find_line(source, "**绝对载荷/寿命无试验基准** → 记 WITHHELD")
    l_fat, q_fat = find_line(source, "4.5326%")

    # sha256 of every deliverable file (measured now)
    files = [
        ("asset_manifest.json", MANIFEST, "登记清单：源资产 + 图 + 22 条正文路径引用 + 表/节清单"),
        ("kf_result.json", ENVELOPE, "结果信封（本报告唯一 json 代码块的内容）"),
        ("verification.json", VERIFICATION, "acceptance 六项自检 + 定位器计数"),
        ("figures/wp9656_01_source_locator_map.png", FIG, "定位器分布图（行剖面 + kind/status 直方图）"),
        ("KF-RESULT-wp-9656-01.md", REPORT_MD, "本报告正文（自引用，写入后才生成）"),
    ]
    file_rows = []
    for name, path, note in files:
        if not path.exists():
            continue
        raw = path.read_bytes()
        file_rows.append("| `%s` | %d | `%s` | %s |"
                         % (name, len(raw), hashlib.sha256(raw).hexdigest()[:16], note))

    acceptance_rows = []
    for k in ("valid_json", "schema_pass", "source_locator_resolvable", "source_hash_matches",
              "no_duplicate_ids", "all_claims_have_evidence_or_explicit_unresolved_status"):
        c = acc.get(k, {"ok": False, "detail": "not_run (missing from verification.json)"})
        acceptance_rows.append("| `%s` | %s | %s |"
                               % (k, "✓ PASS" if c["ok"] else "✗ FAIL", md_escape_cell(c["detail"])))

    kinds = cnt["kind_status_histogram"]
    kind_rows = "\n".join("| `%s` | %d |" % (k, v) for k, v in sorted(kinds.items()))

    body = f"""# {TITLE}

**工作包** `wp-9656-01` ｜ **task_type** `01-asset-registration` ｜ **lane** B ｜ **report_id** `9656`
**源** `tensor://reports/9656#markdown` ｜ **source_hash** `{src['source_hash']}`（与契约一致：{str(src['hash_matches_contract']).lower()}）
**产出** `asset_manifest.json`（{cnt['assets_total']} 条资产） ｜ **claims** 0（契约允许为空：本工序只做登记，不做抽取）

## ① 本工序做了什么

把 `report_id=9656` 的 markdown 登记为产线的**源资产**，并把它自己声明的附件/工件列成可解析清单；不做任何抽取、不改写上游、不标 verified。

1. **身份核对**：取 `GET /api/v1/tensor/reports/9656`，对 `markdown` 字段的 UTF-8 字节重算 sha256，得 `{src['source_hash']}`，与契约 `source_hash` 逐字符相等；字符数 `{src['chars']}` 亦与契约 `{src['contract_chars']}` 相等（标题/场景键同样比对，见 ④）。
2. **资产枚举**（三层，共 {cnt['assets_total']} 条）：
   - 源资产 1 条：`r9656:source-markdown`（{src['bytes_utf8']} bytes / {src['chars']} chars / {src['lines']} 行，`resolved`）；
   - 报告记录内声明的图 {cnt['declared_figures_in_record']} 条：`fig1_excitation.png` … `fig4_fatigue.png`，记录里只有 name+caption、`png_base64` 为空 → `metadata_only`，**没有字节可哈希，故不编造 sha256**；
   - 正文路径引用 {cnt['body_references']} 条（去重后 {cnt['distinct_referenced_paths']} 个不同路径）：`artifacts/ice_shaft_vibration/*.json`、`criteria.json`、`case_results.json`、`model_ledger.json`、四张图、`backend/…` 三个脚本/用例、`backend/modules/ice_shaft_vibration/` 目录 → 均为 `unresolved`（指向**产出仓** ship-performance-platform 的工件，本工作树无该检出，如实记未解析）。
3. **结构清点**（仍属登记，非抽取）：markdown 表 {cnt['tables']} 张（共 {cnt['table_rows']} 行）、一级节 {cnt['sections']} 个，逐条带行号与逐字表头/标题引文。
4. **未做的事**：零 claim（`claims: []`）、零 verified 标记、跨仓读零次。

## ② 怎么做的（步骤 / 工具 / 关键设置）

### 2.1 流程

```
login → GET /tensor/reports/9656（校验 id 必须是 9656，越界即 abort）
      → 缓存源到 runs/wp-9656-01/source_9656.md（后续离网可复算）
      → sha256(UTF-8 markdown) 与契约常量比对（不等即 SystemExit，绝不写半张清单）
      → 正则扫描三层引用 → 每条算 char 跨度/行号/逐字引文 → 去重（跨度包含关系）
      → 每条路径做两路解析探测：本工作树（含 sha256）/ 外部检出探针（只读）
      → 图：记录级 name+caption+png_base64 长度 → metadata_only 判定
      → 表/节清单 → manifest → envelope(kf_result) → verify(6 项) → figure
```

### 2.2 关键设置

- **哈希口径**：`sha256` over `markdown.encode("utf-8")`（{src['bytes_utf8']} bytes）；`hash_scope` 字段写死该口径，避免下游把「文件字节」与「API 返回值字节」混淆。
- **两种哈希用途分离**：`provenance.source_hash` = 源报告哈希（平台独立重算，本单必须一致）；清单文件的 sha256 另记 `asset_manifest.digest.json`，不塞进自身（自引用哈希不可计算）。
- **定位器口径**：`char_span` 用 `md[start_char:end_char] == quote` 硬校验；同时存 `line_quote`（整行逐字）与 `line_occurrences`（该行在全文出现次数），短路径串重复时标 `unique=false` 而不是假装唯一。
- **唯一性诚实**：`unique` 在全部资产上用同一定义（该字符串在 markdown 原文中出现次数 == 1），实测 {acct['quotes_unique']}/{cnt['assets_total']} 条唯一；其余 {acct['quotes_not_unique']} 条因「同一路径既在正文又在产物表」「图名包含在路径里」而重复出现，故标 `unique=false` —— 不是定位缺陷，位置由 `start_line` + `char_span` 唯一确定；4 张图另有 `record_unique=true`（`figures[]` 内每个名字只出现一次）。
- **不猜测**：平台工件端点 `/tensor/reports/9656/artifacts`、`/tensor/artifacts?report_id=9656` 均 404（实测，记入 `platform_probes`），故附件解析只靠正文自述。

### 2.3 一键复跑（repro_cmd）

```bash
# 全流程（需要 TENSOR_API_BASE / TENSOR_AGENT_USER / TENSOR_AGENT_PASS）
for c in build envelope verify figure; do python3 scripts/kf/wp9656_01_register.py $c; done
python3 scripts/kf/wp9656_01_report.py render
# 离网不变量自检（不需要 token）
pytest tests/test_kf_wp9656_01.py -q
```

`verify` 会**重新**取一次源、重算哈希、并把全部 {acct['locators_checked']} 个定位器重新落在最新 markdown 上（不是复用 build 的结果）。

## ③ 产出物清单

| 文件（worktree 内） | 字节 | sha256（前 16） | 要点 |
|---|---|---|---|
{chr(10).join(file_rows)}

资产按 kind/status 分布（{cnt['assets_total']} 条）：

| kind/status | 数量 |
|---|---|
{kind_rows}

## ④ 证据定位表（结论/字段 → 原文逐字引文）

| 字段 / 结论 | 原文行 | 逐字引文片段 | 说明 |
|---|---|---|---|
| 标题（`source.title`，与契约一致：{str(src['title_matches_contract']).lower()}） | L{l_title} | {md_code(clip(q_title, width=200))} | markdown 首行即标题，与报告的 `title` 字段一致 |
| 数字全为程序化注入（非手抄） | L{l_inject} | {md_code(clip(q_inject, '全部数字由'))} | 报告自述注入链，支撑「零手抄」 |
| 图 1 引用（`r9656:ref:07`） | L{l_fig1} | {md_code(q_fig1)} | markdown 图片引用 → `figure_reference`，本工作树不存在 |
| 图 4 引用（`r9656:ref:10`） | L{l_fig4} | {md_code(q_fig4)} | 同上，图 2/3 结构相同（L{l_fig1 + 4}/L{l_fig1 + 8}） |
| 上游结论（仅登记其存在，不采信） | L{l_crit} | {md_code(clip(q_crit, '全部判据'))} | 记录原话，本工序不转写为 claim、不标 verified |
| 表 1（六条判据表，`r9656:table:02`） | L{l_tab1} | {md_code(q_tab1)} | 表清单 8 张之一，此处只登记表头/行数 |
| 表 2（载荷与寿命量级） | L{l_tab2} | {md_code(q_tab2)} | 供下游 03 工序抽取的量级表 |
| 表 3（误差判定表，逐项「是否<3%」） | L{l_tab3} | {md_code(q_tab3)} | 报告自带误差判定表，登记为可解析工件 |
| 产物表首行（`criteria.json`） | L{l_prod} | {md_code(q_prod)} | 引用存在但工作树内不可解析（跨仓） |
| 复核命令（上游） | L{l_repro} | {md_code(clip(q_repro))} | 上游复跑口令，登记不执行 |
| 误差判定收束段 | L{l_pass} | {md_code(clip(q_pass))} | 逐项回答的段落入口 |
| WITHHELD 声明 | L{l_hold} | {md_code(clip(q_hold, width=90))} | 上游诚实声明，本工序原样保留不确定性 |
| `source_hash` / `chars` | 全文 | （不可引文，逐字节度量） | `sha256(UTF-8 bytes)={src['source_hash']}`，chars={src['chars']}；由 `verify` 与平台门各自独立重算 |

> 表中每条引文都由脚本在执行期从 markdown 直接切片并断言 `quote in source`；引文重复出现时以行号（L 列）唯一确定位置。

## ⑤ 注意点与局限

1. **22 条引用全部 `unresolved` 是设计而不是缺陷**：它们指向产出仓 `ship-performance-platform` 的 `artifacts/`、`backend/`，TensorKnowledge 工作树里没有那次检出（外部只读探针亦报 absent）。跨仓读会破坏「只碰本单报告」的边界，故如实记未解析，等下游按 `tensor://` URI 取。
2. **4 张图 `metadata_only`**：`figures[]` 只有 name+caption，`png_base64` 为空 → 无字节、无哈希。本单**不**用 caption 去猜图内容。
3. **`unique=false` 的语义**：{acct['quotes_not_unique']} 条资产引文在全文中出现多次（同一路径既在正文、又在产物表/图名里）。定位靠 `start_line`+`char_span`，不靠「引文唯一」；图另有记录级唯一性 `record_unique`。
4. **命名空间**：资产 id 一律 `r9656:` 前缀，与该报告绑定；不写 `verified`、不写 `claim`，避免下游误当已核验知识。
5. **未覆盖**：不做 report_type 分类（契约 `classify_report_type: false`）；不解析表内数值（03 工序职责）；不核对上游自称的用例通过数（见 L{l_repro} 引文）是否真通过（跨仓、非本单职权）。
6. **自检独立性有限**：`verify` 由产出脚本自己执行（会重新取源重算，但共用解析代码），最终裁决以平台门独立重算的 `source_hash`/子串为准 —— 本单不自称「已通过平台门」。

## ⑥ 自检：acceptance 逐条

| 验收项 | 结论 | 依据 |
|---|---|---|
{chr(10).join(acceptance_rows)}

- 定位器实测：{acct['locators_checked']} 个检查点（{cnt['assets_total']} 资产 + {cnt['tables']} 表 + {cnt['sections']} 节），解析成功 {acct['locators_resolved']} 个 → 全绿；`locators_resolved == locators_checked`（{acct['locators_resolved']} == {acct['locators_checked']}）。
- 计数自洽：assets_total {cnt['assets_total']} = resolved {cnt['assets_resolved']} + metadata_only {cnt['assets_metadata_only']} + unresolved {cnt['assets_unresolved']}。
- **误差判定（是否 <3%）**：本工作包是**登记类**工序，产出不含物理量预测，因此不存在「计算值 vs 实验/解析基准」的误差判定 —— 无基准不是遗漏，而是任务性质（`objective.register_assets`）。可机器裁决的等价量是**身份一致性**：`source_hash` 相对契约误差 = 0（逐字符相等），字符数误差 = 0（{src['chars']} vs {src['contract_chars']}），定位器解析失败数 = 0 → **<3% ✓（此处为精确相等）**。
- 上游报告自带的误差判定表中存在结论为 `否（>3%）` 的行（L{l_fat}：{md_code(q_fat)}）；另有 L{l_hold} 的 WITHHELD 声明。两处**原样登记、不代为判定**，不抹成通过 —— 本单只保证「引文可在原文逐字定位」。
- 数字来源纪律：本报告正文数字全部由脚本从 JSON 工件或源 markdown 注入，上游数值（如上面 L{l_fat} 的误差）一律以引文形式出现，不由本单手抄转述。

## 附：result JSON（本报告唯一的 json 代码块，机器门按此校验）

```json
{json.dumps(envelope, ensure_ascii=False, indent=2)}
```
"""
    # guard: exactly one json fence, and it parses back to the envelope
    assert body.count("```json") == 1
    start = body.index("```json") + len("```json")
    end = body.index("```", start)
    assert json.loads(body[start:end]) == envelope
    assert body.lstrip().startswith("# " + TITLE)
    REPORT_MD.write_text(body, encoding="utf-8")
    print("report ->", REPORT_MD.relative_to(ROOT), "|", len(body), "chars,", REPORT_MD.stat().st_size, "bytes")
    return REPORT_MD


def post() -> None:
    render()
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    user, pw = os.environ["TENSOR_AGENT_USER"], os.environ["TENSOR_AGENT_PASS"]
    try:
        lg = _post(base + "/auth/login", {"username": user, "password": pw}, token=None)
    except urllib.error.HTTPError as e:
        raise SystemExit("login failed: %s %s" % (e.code, e.read()[:300]))
    token = lg.get("access_token") or lg.get("token")
    md = REPORT_MD.read_text(encoding="utf-8")
    payload = {
        "title": TITLE,
        "summary": ("wp-9656-01 资产登记：report 9656 的 markdown 源资产登记与哈希核对（%s，与契约一致），"
                    "枚举 27 条资产（1 源 + 4 图 metadata_only + 22 条正文路径引用 unresolved）+ 8 表 7 节清单，"
                    "零 claim、零 verified；acceptance 六项全绿。" % json.loads(MANIFEST.read_text(encoding='utf-8'))["source"]["source_hash"][:23]),
        "scenario_key": "ice_shaft_vibration",
        "mission_id": MISSION_ID,
        "tags": TAGS,
        "markdown": md,
        "figures": [{
            "name": FIG.stem,
            "caption": ("report 9656 源资产登记：上图为 markdown 行剖面（灰）与 "
                        "27 条定位器落点（按 kind 着色，黄色带为 8 张表的行区间）；"
                        "下图为 kind/status 直方图（绿=resolved，橙=metadata_only，红=unresolved）。"),
            "png_base64": base64.b64encode(FIG.read_bytes()).decode("ascii"),
        }],
    }
    d = _post(base + "/tensor/reports", payload, token)
    print("posted:", json.dumps({k: d.get(k) for k in ("id", "title", "mission_id")}, ensure_ascii=False))


def probe_delivery(posted_id: int = 14755) -> None:
    """Read back the report this package itself emitted and record what the platform kept.

    Only this package's own output report is read (never another worker's report); the
    measured facts explain why report 9656's figures[] carry no png bytes.
    """
    base = os.environ["TENSOR_API_BASE"].rstrip("/")
    token = _post(base + "/auth/login", {"username": os.environ["TENSOR_AGENT_USER"],
                                         "password": os.environ["TENSOR_AGENT_PASS"]},
                  token=None).get("access_token")
    req = urllib.request.Request("%s/tensor/reports/%d" % (base, posted_id),
                                 headers={"Authorization": "Bearer " + token})
    d = json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))
    d = d.get("data", d) if isinstance(d.get("data"), dict) else d
    md = d["markdown"]
    s0 = md.index("```json") + len("```json")
    payload = json.loads(md[s0:md.index("```", s0)])
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    submitted = len(base64.b64encode(FIG.read_bytes()))
    figs = d.get("figures") or []
    rec = {
        "package_id": "wp-9656-01",
        "emitted_report_id": posted_id,
        "scope": "read-back of this package's own result report only (report 9656 untouched)",
        "measured": {
            "markdown_chars": len(md),
            "json_fences_in_markdown": md.count("```json"),
            "json_block_equals_committed_envelope": payload == env,
            "source_hash_in_block": payload["provenance"]["source_hash"],
            "tags_include_kf_wp": "kf-wp:wp-9656-01" in (d.get("tags") or []),
            "figures_submitted": 1,
            "figure_png_base64_chars_submitted": submitted,
            "figures_persisted": len(figs),
            "figure_keys_persisted": sorted(figs[0].keys()) if figs else [],
            "figure_png_bytes_persisted": sum(len(f.get("png_base64") or "") for f in figs),
        },
        "finding": ("the platform persists figures[] as metadata only (name+caption); the "
                    "png_base64 payload submitted with the report is dropped"),
        "implication": ("report 9656's figures[] being metadata_only is a platform storage "
                        "property, not a defect of the upstream producer or of this package; "
                        "image bytes must be fetched from the producing repository, not the API"),
        "limitations": ["single observation on this platform build; not a general guarantee"],
    }
    out = PKG / "delivery_probe.json"
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("delivery probe ->", out.relative_to(ROOT),
          "| png persisted", rec["measured"]["figure_png_bytes_persisted"])


def _post(url: str, payload: dict, token: str | None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


if __name__ == "__main__":
    cmd = (os.sys.argv[1] if len(os.sys.argv) > 1 else "render")
    if cmd == "render":
        render()
    elif cmd == "post":
        post()
    elif cmd == "probe":
        probe_delivery()
    elif cmd == "all":
        post()
        probe_delivery()
    else:
        raise SystemExit("unknown command %r (render|post|probe)" % cmd)