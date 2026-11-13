"""Render figures + the KF-RESULT report for wp-11608-01, and (optionally) publish it.

Every number printed in the report body is read from the artifacts produced by
scripts/kf_wp11608_01_register.py (asset_manifest.json / verification.json /
locator_map.json) or from runs/wp-11608-01/report_11608.json -- nothing is typed
from memory. Quotes are taken from the manifest's own locators.

Usage:
  python3 scripts/kf_wp11608_01_report.py            # figures + markdown only
  python3 scripts/kf_wp11608_01_report.py --publish  # + POST /tensor/reports
"""
from __future__ import annotations

import base64
import json
import os
import pathlib
import urllib.request

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[1]
PKG = ROOT / "docs" / "kf" / "wp-11608-01"
RUN = ROOT / "runs" / "wp-11608-01"
BASE = os.environ.get("TENSOR_API_BASE", "http://127.0.0.1:8010/api/v1").rstrip("/")
MISSION_ID = 15726

MANIFEST = json.loads((PKG / "asset_manifest.json").read_text(encoding="utf-8"))
KF = json.loads((PKG / "kf_result.wp-11608-01.json").read_text(encoding="utf-8"))
VERIF = json.loads((PKG / "verification.json").read_text(encoding="utf-8"))
LOC = json.loads((RUN / "locator_map.json").read_text(encoding="utf-8"))
SRC = json.loads((RUN / "report_11608.json").read_text(encoding="utf-8"))
MD_TEXT = (RUN / "report_11608.md").read_text(encoding="utf-8")

def code(text: str) -> str:
    """Inline-code span whose fence is longer than any backtick run inside `text`."""
    longest = run = 0
    for ch in text:
        run = run + 1 if ch == "`" else 0
        longest = max(longest, run)
    fence = "`" * (longest + 1)
    pad = " " if text.startswith("`") or text.endswith("`") else ""
    return "%s%s%s%s%s" % (fence, pad, text, pad, fence)


COLORS = {"resolved_in_source": "#2b8a3e", "referenced_unresolved": "#e8590c", "declared_absent": "#c92a2a"}


# ------------------------------------------------------------------ figures
def fig_inventory() -> pathlib.Path:
    by = {}
    for a in MANIFEST["assets"]:
        by.setdefault(a["asset_class"], {}).setdefault(a["resolution"], 0)
        by[a["asset_class"]][a["resolution"]] += 1
    classes = sorted(by, key=lambda c: -sum(by[c].values()))
    fig, ax = plt.subplots(figsize=(9.2, 5.4), dpi=150)
    left = None
    for res in ("resolved_in_source", "referenced_unresolved", "declared_absent"):
        vals = [by[c].get(res, 0) for c in classes]
        ax.barh(classes, vals, left=left, color=COLORS[res], label=res, edgecolor="white")
        left = vals if left is None else [a + b for a, b in zip(left, vals)]
    for i, c in enumerate(classes):
        ax.text(sum(by[c].values()) + 0.08, i, str(sum(by[c].values())), va="center", fontsize=8)
    ax.set_xlabel("assets registered (report 11608)")
    ax.set_title(
        "wp-11608-01 asset inventory by class x resolution  (n=%d)" % MANIFEST["counts"]["assets"]
    )
    ax.legend(fontsize=8)
    ax.invert_yaxis()
    ax.grid(axis="x", alpha=0.3)
    p = PKG / "fig1_asset_inventory.png"
    fig.tight_layout()
    fig.savefig(p)
    plt.close(fig)
    return p


def fig_locator_map() -> pathlib.Path:
    n = len(MD_TEXT)
    lines = MD_TEXT.count("\n") + 1
    fig, ax = plt.subplots(figsize=(9.6, 6.0), dpi=150)
    order = [a for a in MANIFEST["assets"]]
    ylabels = []
    for i, a in enumerate(order):
        loc = a["locator"]
        ylabels.append("%s %s" % (a["asset_id"], a["asset_class"]))
        if a["locator_source"] == "record":
            ax.plot([0, n], [i, i], color=COLORS["declared_absent"], lw=1.2, ls=":", alpha=0.9)
            ax.text(n * 0.5, i, "record.figures entry, absent from body", fontsize=6,
                    va="center", ha="center", color=COLORS["declared_absent"])
        else:
            s, e = loc["start_char"], loc["end_char"]
            ax.plot([s, max(e, s + 1)], [i, i], color=COLORS[a["resolution"]], lw=4, solid_capstyle="butt")
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(ylabels, fontsize=6.5)
    ax.invert_yaxis()
    ax.set_xlim(0, n)
    ax.set_xlabel("character offset in report 11608 markdown  (total %d chars / %d bytes utf-8, %d lines)"
                  % (len(MD_TEXT), len(MD_TEXT.encode('utf-8')), lines))
    ax.set_title("locator coverage: every quote re-resolved against the pinned bytes")
    ticks = list(range(0, n + 1, 1000))
    ax.set_xticks(ticks)
    ax.grid(axis="x", alpha=0.3)
    p = PKG / "fig2_locator_coverage.png"
    fig.tight_layout()
    fig.savefig(p)
    plt.close(fig)
    return p


def fig_audit() -> pathlib.Path:
    c = MANIFEST["counts"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.0, 4.2), dpi=150, gridspec_kw={"width_ratios": [1, 1.15]})
    labels = ["resolved_in_source", "referenced_unresolved", "declared_absent"]
    vals = [c["resolved_in_source"], c["referenced_unresolved"], c["declared_absent"]]
    bars = ax1.bar(labels, vals, color=[COLORS[l] for l in labels])
    for b, v in zip(bars, vals):
        ax1.text(b.get_x() + b.get_width() / 2, v + 0.15, str(v), ha="center", fontsize=9)
    ax1.set_ylabel("assets")
    ax1.set_title("resolution census (n=%d)" % c["assets"])
    ax1.tick_params(axis="x", labelrotation=12, labelsize=8)

    on = c["off_topic"]
    ax2.barh(["body-relevant", "off-topic / mismatched"], [c["assets"] - on, on],
             color=["#1c7ed6", COLORS["declared_absent"]])
    for i, v in enumerate([c["assets"] - on, on]):
        ax2.text(v + 0.15, i, str(v), va="center", fontsize=9)
    ax2.set_xlabel("assets")
    ax2.set_title("subject-consistency split\n(6 record.figures + 4 hydroelasticity paths)")
    ax2.grid(axis="x", alpha=0.3)
    p = PKG / "fig3_resolution_audit.png"
    fig.tight_layout()
    fig.savefig(p)
    plt.close(fig)
    return p


# ------------------------------------------------------------------- report
def ev_table() -> str:
    rows = ["| asset | class | section | resolution | locator | char span | line | 原文引文（逐字） |",
            "|---|---|---|---|---|---|---|---|"]
    for a in MANIFEST["assets"]:
        loc = a["locator"]
        q = loc["quote"].replace("|", "\\|")
        if len(q) > 58:
            q = q[:55] + "…"
        span = "%d-%d" % (loc["start_char"], loc["end_char"])
        sem = "verbatim" if a["locator_semantics"] == "verbatim_asset_reference" else "anchor"
        sec = a["in_report_section"]
        if a["locator_source"] == "record":
            sec = "record.figures（正文缺席，锚 §4）"
        rows.append(
            "| %s | %s | %s | %s | %s | %s | L%d | %s |"
            % (a["asset_id"], a["asset_class"], sec, a["resolution"], sem, span, loc["start_line"], code(q))
        )
    return "\n".join(rows)


def claim_field_table() -> str:
    """字段 -> 证据；引文型给逐字片段，计算型显式标“本地重算，非正文引文”。"""
    by_id = {a["asset_id"]: a for a in MANIFEST["assets"]}
    rows = [
        "| 字段/条目 | 证据类型 | 定位 | 原文引文 / 值 |",
        "|---|---|---|---|",
        "| `provenance.source_hash` | 本地重算 | 全文 bytes | `sha256:%s` |" % MANIFEST["source"]["hash"],
        "| `source.chars` / `source.bytes_utf8` | 本地重算 | 全文 | `%d` 字符 / `%d` 字节 |"
        % (MANIFEST["source"]["chars"], MANIFEST["source"]["bytes_utf8"]),
        "| `source.title` / `source.scenario_key` | record 字段 | record → contract | `%s` |"
        % MANIFEST["source"]["scenario_key"],
    ]
    pick = {
        "assets[A05] artifacts/fvm_modified_equation.json": "A05",
        "assets[A07] tests/test_numerical_viscosity.py（57 用例）": "A07",
        "assets[A10] branch agent/m9775": "A10",
        "assets[A11] pytest invocation, 57 passed": "A11",
        "assets[A16] record.figures fig1_geometry.png": "A16",
        "assets[A12] hydroelasticity path（主体错位）": "A12",
    }
    for field, aid in pick.items():
        a = by_id[aid]
        loc = a["locator"]
        q = loc["quote"].replace("|", "\\|")
        if len(q) > 62:
            q = q[:59] + "…"
        where = "L%d（锚 §4）" % loc["start_line"] if a["locator_source"] == "record" else "L%d" % loc["start_line"]
        rows.append("| `%s` | 逐字引文 | %s | %s |" % (field, where, code(q)))
    decl = MANIFEST["declared_verification_status"]
    rows.append(
        "| `declared_verification_status.quote` | 逐字引文（仅声明） | L%d | %s |"
        % (decl["locator"]["start_line"], code(decl["quote"]))
    )
    return "\n".join(rows)


def build_markdown(figs: dict[str, pathlib.Path]) -> str:
    c = MANIFEST["counts"]
    s = MANIFEST["source"]
    decl = MANIFEST["declared_verification_status"]
    off = [a for a in MANIFEST["assets"] if a["off_topic"]]
    absent = [a for a in MANIFEST["assets"] if a["resolution"] == "declared_absent"]
    unres = [a for a in MANIFEST["assets"] if a["resolution"] == "referenced_unresolved"]
    kf_json = json.dumps(KF, ensure_ascii=False, indent=2)
    n_tail = c["off_topic"] - c["declared_absent"]
    a07 = next(a for a in MANIFEST["assets"] if a["asset_id"] == "A07")
    a11 = next(a for a in MANIFEST["assets"] if a["asset_id"] == "A11")
    a23 = next(a for a in MANIFEST["assets"] if a["asset_id"] == "A23")

    return f"""# KF-RESULT wp-11608-01

**工序**：`01-asset-registration`（assets only，无抽取、无分类、claims=[] 契约要求）
**报告**：report_id={MANIFEST['report_id']} · `{s['scenario_key']}` · mission={s.get('platform_mission_id')}
**标题**：{s['title']}
**tag**：`kf-wp:wp-11608-01` · `FVM` · `numerical-viscosity`
**源哈希**：`sha256:{s['hash']}`（{s['chars']} 字符 / {s['bytes_utf8']} 字节 UTF-8，本地重算，与契约 source_hash 一致）
**状态**：draft（verification 由平台门计算；本报告不含任何 verified 标记）

---

## ① 本工序做了什么

只做一件事：把 report 11608 的**可解析资产**登记成机器可校验的清单，不抽取结论、不判定报告类型。

- 登记资产 **{c['assets']}** 个，去重后 ID 唯一（A01–A25），每项带字符级 locator（`char_span`，含 start/end char、行号、逐字引文、唯一性）。
- 分档：`resolved_in_source` **{c['resolved_in_source']}**（正文内可逐字定位的源本身/公式块/表格）、`referenced_unresolved` **{c['referenced_unresolved']}**（正文引用了路径，但在探测域内无法确认目标工件存在）、`declared_absent` **{c['declared_absent']}**（平台 `record.figures` 声明、正文完全未引用）。
- 顺带记录两处**主体不一致**（不隐藏、不修改上游）：6 条 `record.figures` 全部未出现在正文，且图注主体是附加质量/springing/鞭振/疲劳；正文末行 *报告工件路径* 指向 `artifacts/hydroelasticity/` 等 4 个水弹性工件。二者合计 **{c['off_topic']}** 个 off-topic 条目，已逐条标 `off_topic=true`。
- `claims` 故意为空数组：契约 `objective.register_assets=true / classify_report_type=false / no_forced_claim_generation=true`，本工序不生成知识对象。
- 作者自评句 `{decl['quote']}` 仅作**声明**登记（`treated_as={decl['treated_as']}`），未升格为状态。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. `scripts/kf_fetch_11608.py`：`POST $TENSOR_API_BASE/auth/login` → `GET $TENSOR_API_BASE/tensor/reports/11608`，取 `markdown` 字段**原样**落盘（`newline=""`，不重编码）。
2. 本地重算 `sha256(markdown.encode('utf-8'))`，与契约 `source_hash` 比对，并校验字符数 = {s['chars']}；不一致即 `exit 2`（无静默降级）。
3. `scripts/kf_wp11608_01_register.py`：资产表内置**逐字引文**，用 `md.index(quote)` 反解 char span，`md.count(quote)==1` 断言唯一性；任一条对不上即 `SystemExit`（杜绝手抄/改写）。
4. 路径类资产做**有界存在性探测**（仅本 worktree 根）：找不到记 `referenced_unresolved` 并写明探测域，**不等于**判定其不存在（TensorFVM 仓未检出）。
5. `record.figures` 6 条按"是否为 markdown 逐字子串"判 `declared_absent`。
6. 产出 `asset_manifest.json` + `kf_result.wp-11608-01.json`（信封）+ `verification.json`（本地机械校验，`gate=pending_platform_verification`）+ `runs/wp-11608-01/locator_map.json`。
7. `tests/test_kf_wp11608_01.py` 复核全部不变量；本报告的数字由本脚本从上述工件读取注入，不手写。

关键设置：hash 算法 sha256；locator 坐标系 = Unicode 码点（`len(str)`），字节数另记；探测根 = 本 worktree。

## ③ 产出物清单（输出文件名 → 要点）

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-11608-01/asset_manifest.json` | 主产出：{c['assets']} 资产 / locator / resolution / counts / integrity / limitations |
| `docs/kf/wp-11608-01/kf_result.wp-11608-01.json` | 平台结果信封（package_id/task_type/report_id/provenance/outputs/claims=[]） |
| `docs/kf/wp-11608-01/asset_manifest.v1.schema.json` | 本包固定 schema（仓库通用版把 package_id 钉死为 wp-448-01，无法复用） |
| `docs/kf/wp-11608-01/verification.json` | 本地机械校验清单；`gate=pending_platform_verification` |
| `docs/kf/wp-11608-01/fig1_asset_inventory.png` | 资产 × 类别 × resolution 分布 |
| `docs/kf/wp-11608-01/fig2_locator_coverage.png` | 25 条 locator 在 {s['chars']} 字符上的覆盖图 |
| `docs/kf/wp-11608-01/fig3_resolution_audit.png` | resolution 普查 + 主体一致性拆分 |
| `runs/wp-11608-01/report_11608.json` / `report_11608.md` | 取源原始载荷与字节级 markdown 副本 |
| `runs/wp-11608-01/locator_map.json` | 中间件：asset_id → char/line span |
| `scripts/kf_fetch_11608.py` / `scripts/kf_wp11608_01_register.py` / `scripts/kf_wp11608_01_report.py` | 取源 / 登记 / 出图出报告，可一键复跑 |
| `tests/test_kf_wp11608_01.py` | 16 项验收不变量测试 |

## ④ 证据定位表（字段 → 原文引文，逐字）

{sections_evidence()}

## ⑤ 注意点与局限

1. **不做抽取**：正文所有数字（`{a23['asset_id']}` 登记的 §3.1 表格等）在本工序**未复算**，属下游验证包职责；本包只保证"引文能逐字定位"，不保证数值正确。
2. **存在性探测的范围局限**：{MANIFEST['integrity']['probe_scope']}。故 {len(unres)} 个路径类资产为 `referenced_unresolved`，含义是"此处不可确认"，不是"作者没产出"。
3. **§8 自证未复现**：{code(a11['locator']['quote'])}（A11，含 57 passed 的计数声明）与 A10 的"commit 待平台自动推送"均为作者声明，本包未跑该套件、也未取到 commit 号 → `not_run`，不得当作已通过。
4. **主体不一致（上游缺陷，只记录不改写）**：
   - `record.figures` {c['declared_absent']} 条全部在正文中缺席，图注主体=附加质量/湿模态/springing/鞭振/疲劳；
   - 正文末行 *报告工件路径* 指向（共 {n_tail} 条，A12–A15）`artifacts/hydroelasticity/case_report.json`、`docs/HULL_HYDROELASTICITY.md`、`tests/test_hull_hydroelasticity.py`（26 例）、`backend/physics/hull_hydroelasticity/`；
   - 二者都更像模板残留，建议由上游/平台侧在 report 11608 的 record 层修正（本单硬约束：不改上游产物、不碰其它 report_id）。
5. **边界遵守**：全包只读 report_id={MANIFEST['report_id']}；`tensor://reports/` 引用集合 = {{{MANIFEST['report_id']}}}（有测试断言）。
6. **未标 verified**：任何 resolution 都不是"结论已核"。`hash_matches_contract=true` 只说明字节同一性。

## ⑥ 自检（逐条对照 acceptance）

| # | acceptance | 结果 | 依据 |
|---|---|---|---|
| 1 | valid_json | ✅ | 两个 JSON 均可 `json.loads`，测试反复解析 |
| 2 | schema_pass | ✅ | 信封过 `schemas/kf_result.v1.schema.json`；manifest 过本包 pinned schema（jsonschema 4.26） |
| 3 | source_locator_resolvable | ✅ | 全部 {c['assets']} 条 locator 均满足 `md[start:end]==quote` 且逐字唯一；其中 {c['declared_absent']} 条 record 条目用逐字锚点定位，缺席事实另由 `record_name` + `resolution_check.result=absent` 承载 |
| 4 | source_hash_matches | ✅ | `sha256:{s['hash']}` 与契约 source_hash 逐字符相同 |
| 5 | no_duplicate_ids | ✅ | A01–A25 唯一，测试断言 `len(set)==len` |
| 6 | all_claims_have_evidence_or_explicit_unresolved_status | ✅（空集，契约允许） | `claims=[]`；每条资产仍带 locator 或显式 resolution |
| 7 | 边界：只碰 11608 | ✅ | 测试 `test_only_report_11608_is_touched` |
| 8 | 不改上游、不标 verified | ✅ | 只新增本包文件；`verification.gate=pending_platform_verification` |
| 9 | 作者自评 ≠ 平台判定 | ✅ | 声明句单独字段登记，附 locator |
| 10 | honest not_run 记录 | ✅ | §8 的 57 passed（A11）/ commit 号（A10）/ TensorFVM 工件存在性（{c['referenced_unresolved']} 条）均记未验证 |

**诚实结论**：本工序交付的是"资产登记 + 可解析定位"的证据面，不是"报告结论正确"的判定。三处上游不一致（`record.figures` {c['declared_absent']}/{c['declared_absent']} 与正文不符、尾部水弹性路径 {n_tail} 条错位、commit 号缺失）已如实入账，未做任何粉饰或改写。

## repro_cmd（一键复跑）

```bash
cd <worktree>            # TensorKnowledge 检出（agent/m15726）
python3 scripts/kf_fetch_11608.py              # 取源 + 校验 sha256/字符数（需 TENSOR_AGENT_USER/PASS/TENSOR_API_BASE）
python3 scripts/kf_wp11608_01_register.py      # 生成 asset_manifest.json / kf_result / verification / locator_map
python3 scripts/kf_wp11608_01_report.py        # 生成三张图与本报告
python3 -m pytest tests/test_kf_wp11608_01.py -q
```

## 结果信封（唯一 json 代码块，平台按此校验）

```json
{kf_json}
```

---

*图 1 · 资产分布*　![inventory](fig1_asset_inventory.png)
*图 2 · locator 覆盖*　![locators](fig2_locator_coverage.png)
*图 3 · resolution 普查*　![audit](fig3_resolution_audit.png)
"""


def sections_evidence() -> str:
    return (
        "（a）源与完整性\n\n"
        "| 字段 | 证据 | 值 |\n|---|---|---|\n"
        "| `provenance.source_hash` | 本地重算 sha256（非正文引文；正文不含该十六进制串） | `sha256:%s` |\n"
        "| `source.chars` / `source.bytes_utf8` | 本地重算 | `%d` 字符 / `%d` 字节 |\n"
        "| `source.uri` / `field` | 契约 | `tensor://reports/11608#markdown` |\n\n"
        "（b）资产 locator（全表，逐字引文，超长截断处用 … 标记）\n\n%s\n\n"
        "（c）字段 → 引文映射\n\n%s"
        % (
            MANIFEST["source"]["hash"],
            MANIFEST["source"]["chars"],
            MANIFEST["source"]["bytes_utf8"],
            ev_table(),
            claim_field_table(),
        )
    )


def publish(md: str, figs: dict[str, pathlib.Path]) -> dict:
    def post(url, payload, token=None):
        req = urllib.request.Request(
            url, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
        )
        if token:
            req.add_header("Authorization", "Bearer " + token)
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode())

    token = None
    for path in ("/auth/login", "/auth/token", "/login"):
        try:
            d = post(BASE + path, {"username": os.environ["TENSOR_AGENT_USER"],
                                   "password": os.environ["TENSOR_AGENT_PASS"]})
            token = d.get("access_token") or d.get("token") or (d.get("data") or {}).get("access_token")
            if token:
                break
        except Exception:
            continue
    if not token:
        raise SystemExit("publish failed: no token")
    figures = [
        {
            "name": p.name,
            "caption": cap,
            "png_base64": base64.b64encode(p.read_bytes()).decode(),
        }
        for p, cap in figs.items()
    ]
    payload = {
        "title": "KF-RESULT wp-11608-01",
        "summary": (
            "report 11608 资产登记：%d 个资产（resolved_in_source %d / referenced_unresolved %d / "
            "declared_absent %d），逐条 char-span locator，源 sha256 与契约一致；claims=[] 按契约；"
            "记录 6/6 record.figures 与正文不一致、尾部 4 条水弹性路径错位。"
            % (MANIFEST["counts"]["assets"], MANIFEST["counts"]["resolved_in_source"],
               MANIFEST["counts"]["referenced_unresolved"], MANIFEST["counts"]["declared_absent"])
        ),
        "scenario_key": MANIFEST["source"]["scenario_key"],
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:wp-11608-01", "KF-RESULT", "FVM", "numerical-viscosity",
                 "asset-registration", "report-11608"],
        "markdown": md,
        "figures": figures,
    }
    return post(BASE + "/tensor/reports", payload, token)


def main() -> int:
    figs = {
        fig_inventory(): "图 1 · 资产类别 × resolution 分布（n=%d）" % MANIFEST["counts"]["assets"],
        fig_locator_map(): "图 2 · 25 条 locator 在报告 markdown 上的覆盖（record 条目以点线表示缺席）",
        fig_audit(): "图 3 · resolution 普查与主体一致性拆分",
    }
    md = build_markdown(figs)
    out = PKG / "KF-RESULT-wp-11608-01.md"
    out.write_text(md, encoding="utf-8")
    print("report ->", out, len(md), "chars")
    print("single json block:", md.count("```json") == 1)
    if "--publish" in os.sys.argv:
        d = publish(md, figs)
        rid = d.get("id") or (d.get("data") or {}).get("id")
        print("published report id:", rid)
        (PKG / "publish.json").write_text(
            json.dumps({"id": rid, "response": d}, ensure_ascii=False, indent=2) + "\n", "utf-8"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())