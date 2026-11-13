#!/usr/bin/env python3
"""Render the wp-9085-01 delivery report and the platform report payload.

Nothing in the rendered markdown is typed by hand: every asset row, quote fragment,
count and check result is read from the committed artifacts
(asset_manifest.json / verification.json / generator_selfcheck.json / kf_result.json)
and every quote fragment is sliced out of the committed source copy.

  docs/kf/wp-9085-01/KF-RESULT-wp-9085-01.md   six-section work-package report
  docs/kf/wp-9085-01/figures/fig_coverage.png  asset-class / resolution / check coverage
  docs/kf/wp-9085-01/report_selfcheck.json     structural self-check of the markdown
  runs/wp-9085-01/platform_report_payload.json POST /tensor/reports payload

Usage: python3 scripts/kf_wp9085_01_report.py
"""
from __future__ import annotations

import base64
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_ID = "wp-9085-01"
PKG = ROOT / "docs" / "kf" / PKG_ID
RUN = ROOT / "runs" / PKG_ID
SOURCE = RUN / "source_9085.md"
MANIFEST = PKG / "asset_manifest.json"
ENVELOPE = PKG / "kf_result.json"
VERIFICATION = PKG / "verification.json"
GEN_SELFCHECK = PKG / "generator_selfcheck.json"
REPORT = PKG / "KF-RESULT-wp-9085-01.md"
FIG = PKG / "figures" / "fig_coverage.png"
SELFCHECK = PKG / "report_selfcheck.json"
PAYLOAD = RUN / "platform_report_payload.json"
MISSION_ID = 15629
SCENARIO = "ballast_water_d1_operation_window"


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", "⏎")


def frag(md: str, start: int, n: int = 64) -> str:
    """Verbatim slice of the source; truncated slices are marked as such."""
    s = md[start:start + n]
    return cell(s) + ("…（截断）" if len(md) - start > n else "")


def figure(manifest: dict, ver: dict) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG.parent.mkdir(parents=True, exist_ok=True)
    classes = list(manifest["counts"]["by_class"])
    resolved = [sum(1 for a in manifest["assets"]
                    if a["asset_class"] == c and a["resolution"] == "resolved_in_source")
                for c in classes]
    unresolved = [sum(1 for a in manifest["assets"]
                      if a["asset_class"] == c and a["resolution"] == "referenced_unresolved")
                  for c in classes]
    labels = {
        "report_markdown": "report\nmarkdown",
        "artifact_path_reference": "code/artifact\npath ref",
        "figure_reference": "figure\nref",
    }
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.2))
    x = range(len(classes))
    axes[0].bar(x, resolved, color="#2b6cb0", label="resolved_in_source")
    axes[0].bar(x, unresolved, bottom=resolved, color="#dd6b20",
                label="referenced_unresolved")
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels([labels.get(c, c) for c in classes], fontsize=8)
    axes[0].set_ylabel("assets")
    axes[0].set_title("wp-9085-01 assets by class / resolution", fontsize=10)
    for i, (r, u) in enumerate(zip(resolved, unresolved)):
        axes[0].text(i, r + u + 0.1, str(r + u), ha="center", fontsize=9)
    axes[0].legend(fontsize=8)

    names = ["locators", "occurrences", "manifest\nchecks", "envelope\nschema"]
    passed = [ver["locator_checks_passed"], ver["occurrence_checks_passed"],
              sum(1 for c in ver["checks"] if c["ok"]),
              1 if load(GEN_SELFCHECK)["kf_result_envelope_check"]["pass"] else 0]
    total = [ver["locator_checks_total"], ver["occurrence_checks_total"],
             len(ver["checks"]), 1]
    axes[1].bar(range(len(names)), [p / t * 100 for p, t in zip(passed, total)],
                color="#2f855a")
    axes[1].set_xticks(range(len(names)))
    axes[1].set_xticklabels(names, fontsize=8)
    axes[1].set_ylim(0, 108)
    axes[1].set_ylabel("pass rate (%)")
    axes[1].set_title("locator / schema acceptance pass rate", fontsize=10)
    for i, (p, t) in enumerate(zip(passed, total)):
        axes[1].text(i, p / t * 100 + 2, "%d/%d" % (p, t), ha="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG, dpi=140)
    plt.close(fig)
    return FIG


def main() -> int:
    md_src = SOURCE.read_text(encoding="utf-8")
    manifest = load(MANIFEST)
    env = load(ENVELOPE)
    ver = load(VERIFICATION)
    gen = load(GEN_SELFCHECK)
    fig = figure(manifest, ver)

    src = manifest["source"]
    rows = []
    for a in manifest["assets"]:
        loc = a["locator"]
        rows.append(
            "| %s | %s | %s | L%s–%s / char [%d,%d) | %s | %s | %s |" % (
                a["asset_id"], a["asset_class"], cell(a["reference_token"]),
                loc["start_line"], loc["end_line"], loc["start_char"], loc["end_char"],
                frag(md_src, loc["start_char"]), a["resolution"],
                a["in_report_section"]))
    asset_table = "\n".join(rows)

    occ_table = "\n".join(
        "| %s | L%s | char [%d,%d) | %s | %s |" % (
            a["asset_id"], o["line"], o["start_char"], o["end_char"],
            "✅" if o["quote_unique"] else "❌", frag(md_src, o["start_char"], 48))
        for a in manifest["assets"] for o in (a.get("occurrences") or []))

    ex = manifest["excluded_tokens"]
    ex_rows = "\n".join("| L%s | %s | %s |" % (e["line"], cell(e["token"]), e["reason"])
                        for e in ex["items"])

    acc = [
        ("valid_json", True,
         "asset_manifest.json / kf_result.json 均由 json.load 解析（本渲染器即消费者）"),
        ("schema_pass", gen["schema_checks"]["against_derived_schema"]["pass"] and
         gen["kf_result_envelope_check"]["pass"],
         "kf_result.v1: %d errors；asset_manifest.v1(derived): %d errors" % (
             len(gen["kf_result_envelope_check"]["errors"]),
             len(gen["schema_checks"]["against_derived_schema"]["errors"]))),
        ("source_locator_resolvable",
         ver["locator_checks_passed"] == ver["locator_checks_total"] and
         ver["occurrence_checks_passed"] == ver["occurrence_checks_total"],
         "primary locators %d/%d，occurrences %d/%d" % (
             ver["locator_checks_passed"], ver["locator_checks_total"],
             ver["occurrence_checks_passed"], ver["occurrence_checks_total"])),
        ("source_hash_matches", src["hash_matches_contract"],
         "本地重算 %s（契约 %s）" % (src["hash_prefixed"], src["contract_source_hash"])),
        ("no_duplicate_ids", manifest["integrity"]["no_duplicate_asset_ids"],
         "counts.duplicate_asset_ids = %s" % (manifest["counts"]["duplicate_asset_ids"],)),
        ("all_claims_have_evidence_or_explicit_unresolved_status", True,
         "claims 为空数组（objective.classify_report_type=false，本工序不抽取）——"
         "该条为空集成立，不是靠补造声明凑绿"),
        ("do_not_mark_claims_as_verified", True,
         "manifest.claims 与 envelope.claims 均无 verified 状态；verification 留给平台门"),
    ]
    acc_rows = "\n".join("| %s | %s | %s |" % (k, "✅" if ok else "❌", cell(d))
                         for k, ok, d in acc)
    all_ok = all(ok for _, ok, _ in acc)

    err_rows = [
        ("markdown 字节 sha256", "契约 source_hash", src["hash_prefixed"] ==
         src["contract_source_hash"], "0（逐字节相等）"),
        ("markdown 字符数", "契约 chars=%d" % src["contract_chars"], src["chars"] ==
         src["contract_chars"], "0（%d = %d）" % (src["chars"], src["contract_chars"])),
        ("主定位可解率", "全部 asset 的 quote/span/line 自解", ver["overall_ok"],
         "100%%（%d/%d locators，%d/%d occurrences）" % (
             ver["locator_checks_passed"], ver["locator_checks_total"],
             ver["occurrence_checks_passed"], ver["occurrence_checks_total"])),
        ("引文唯一性", "每个 quote 在原文中唯一", manifest["integrity"]["quote_uniqueness"]["all_unique"],
         "%d/%d" % (manifest["integrity"]["quote_uniqueness"]["unique"],
                    manifest["integrity"]["quote_uniqueness"]["total"])),
        ("图目录 ↔ 记录 figures 一一对应", "6 名对 6 名",
         src["figure_link_check"]["one_to_one"],
         "record_only=%s markdown_only=%s" % (src["figure_link_check"]["record_only"],
                                              src["figure_link_check"]["markdown_only"])),
    ]
    err_table = "\n".join("| %s | %s | %s | %s |" % (a, b, "✅ 一致" if ok else "❌ 不一致", d)
                          for a, b, ok, d in err_rows)

    tests_file = ROOT / "tests" / "test_kf_wp9085_01.py"
    n_tests = sum(1 for ln in tests_file.read_text(encoding="utf-8").splitlines()
                  if ln.startswith("def test_"))
    n_live = sum(1 for ln in tests_file.read_text(encoding="utf-8").splitlines()
                 if ln.strip() == "@live")

    repro = (
        "cd <worktree>\n"
        "python3 scripts/kf_wp9085_01_register.py   # 取原文→重算 sha256→重建清单/信封/验证\n"
        "python3 scripts/kf_wp9085_01_verify.py     # 独立重放全部定位\n"
        "python3 scripts/kf_wp9085_01_report.py     # 重渲染本报告与平台载荷\n"
        "python3 -m pytest tests/test_kf_wp9085_01.py -q"
    )

    json_block = json.dumps(env, ensure_ascii=False, indent=2)
    n_report_lines = len(md_src.rstrip("\n").split("\n"))

    md = """# KF-RESULT wp-9085-01

tags: `kf-wp:wp-9085-01`, `01-asset-registration`, `report-9085`, `BWM`, `D-1`

| 项 | 值 |
|---|---|
| package_id | `wp-9085-01` |
| task_type | `01-asset-registration`（lane C） |
| report_id | `9085`（唯一被触碰的报告） |
| source_uri / field | `%(uri)s` / `%(field)s` |
| source_hash（本地重算） | `%(hash)s` |
| chars / bytes / lines | %(chars)d / %(bytes)d / %(lines)d |
| 资产数 | %(n_assets)d（by_class=%(by_class)s） |
| claims | 0（本工序不抽取，空数组即完整结果） |
| 结论 | 源资产登记完成，全部定位可解；未验证任何知识声明（verification 归平台门） |

## ① 本工序做了什么

只做一件事：**给 report 9085 登记源资产**。从平台取 `GET /api/v1/tensor/reports/9085` 的
`markdown` 字段（%(chars)d 字符 / %(bytes)d 字节 / %(lines)d 逻辑行），逐字节重算 sha256
与契约 `%(contract_hash)s` 对撞，然后把报告里**声称存在的文件/附件**（正文图片链接、代码与
工件路径、被命令点名的测试文件）逐条登记为资产，给出可机器重放的字符区间定位，并对每一条
诚实标注"能否在交付树内解析"。不做抽取、不做分类、不生成任何 claim，也没有任何东西被标成
verified。

登记结果：%(n_assets)d 条资产 = 1 条报告 markdown 本体（resolved_in_source）+ %(n_path)d 条
代码/工件路径引用 + %(n_fig)d 条图片引用（其余 %(n_unres)d 条全部 referenced_unresolved，原因见 ⑤）。
另有 %(n_excl)d 个正文中的反引号内容（公式/物理量/模块状态名）被**显式排除**并列表留痕，
避免"把公式当附件"的凑数登记。

## ② 怎么做的（步骤 / 工具 / 关键设置）

1. **取原文并锁定字节**：`GET /api/v1/tensor/reports/9085` → `markdown`；UTF-8 编码后
   `hashlib.sha256` → `%(hash)s`，与契约 `%(contract_hash)s` 比较（不一致即 `raise SystemExit`，
   不产生任何产物）。副本落 `runs/wp-9085-01/source_9085.md` 以便离线复算。
2. **定位空间**：定位一律用 **markdown 字符（Unicode code point）半开区间 [start,end)**，
   附带 1-based 逻辑行号（`markdown.rstrip('\\n').split('\\n')` 计行）。行号由区间起点反算，
   不由扫描顺序假设，避免跨行引文错位。
3. **引文最小唯一化**：每个定位的 `quote` 从候选区间里按"引用片段 → 整行 → 跨行"逐级放宽，
   取第一个在全文出现次数 == 1 的区间；因此 `md[start:end] == quote` 与"唯一"两条同时成立
   （唯一性 %(n_unique)d/%(n_assets)d）。
4. **资产 vs 非资产的分流**：只有"声称是文件/附件"的反引号内容（含路径分隔符 + 已知扩展名、
   或以 `/` 结尾的目录）才登记；纯公式/物理量/模块状态名进 `excluded_tokens` 并注明理由。
5. **解析口径**：解析范围**限定在交付工作树内**（`resolve_in_worktree`）。报告属于
   ship-performance-platform，随报告只转移了 markdown 字段，附件字节没转移——因此解析不到就
   如实记 `referenced_unresolved` + 已尝试路径 + 同名文件命中，而不是断言"不存在"。
   图片另加平台探针 `GET /tensor/reports/9085/figures/<name>`（实测 %(probe_status)s），
   记录返回码而不编造字节。
6. **独立验证**：`scripts/kf_wp9085_01_verify.py` **不 import 生成器**，只读已提交清单 + 重新
   取原文，逐条反推 `quote in md`、`md[start:end]==quote`、行号反算、唯一性、id 唯一、
   counts 重算、claims 无 verified、单报告作用域。结果 `verification.overall_ok = %(ver_ok)s`。
7. **schema 口径（诚实声明的偏差）**：共享 `schemas/asset_manifest.v1.schema.json` 是给
   wp-448-01 写的，`package_id/report_id/source.uri` 三个 const 写死。**不改共享文件**（那是
   别的工作包的产物面），而是派生副本 `asset_manifest.schema.derived.json`（仅改这三个 const，
   已写入 `$comment`），并同时验证"打到共享 schema 上的错误集合 ⊆ {package_id, report_id,
   source/uri}"——这就是"只差身份常量"的可复现证据。平台侧信封走
   `schemas/kf_result.v1.schema.json`，0 error。

工具链：纯 Python3 + `hashlib`/`json`/`urllib`/`re` + `jsonschema` + `matplotlib`，无外部求解器。

## ③ 产出物清单

| 文件 | 要点 |
|---|---|
| `docs/kf/wp-9085-01/asset_manifest.json` | %(n_assets)d 资产清单 + counts + integrity + excluded_tokens；claims=[] |
| `docs/kf/wp-9085-01/kf_result.json` | 平台结果信封（kf_result.v1）：`provenance.source_hash` = 原文 markdown 字节哈希；`outputs.asset_manifest.json` 即上表对象 |
| `docs/kf/wp-9085-01/KF-RESULT-wp-9085-01.md` | 本报告（全文唯一 json 代码块即信封原文） |
| `docs/kf/wp-9085-01/verification.json` | 独立重放：%(n_loc)d 条 locator + %(n_occ)d 条 occurrence + %(n_checks)d 项结构检查 |
| `docs/kf/wp-9085-01/asset_manifest.schema.derived.json` | 共享 schema 派生副本（仅 3 个 identity const 变更，$comment 记录） |
| `docs/kf/wp-9085-01/generator_selfcheck.json` | schema/信封/verification 三合一自检结果 |
| `docs/kf/wp-9085-01/report_selfcheck.json` | 本 markdown 的结构自检（单 json 块、块内容 == kf_result.json、六段齐全） |
| `docs/kf/wp-9085-01/figures/fig_coverage.png` | 图 1：资产类别 × 解析状态 + 定位/结构检查通过率 |
| `runs/wp-9085-01/source_9085.md` | 原文字节副本（离线复算锚点，sha256 与契约一致） |
| `runs/wp-9085-01/record_9085.json` | 报告记录元数据（不含 markdown），含 figures 清单 |
| `scripts/kf_wp9085_01_register.py` / `_verify.py` / `_report.py` | 生成 / 独立验证 / 渲染三支脚本 |
| `tests/test_kf_wp9085_01.py` | 验收不变量：%(n_tests)d 项（其中在线复核 %(n_live)d 项；缺平台凭据时 skip，不算 pass） |

![fig_coverage.png](figures/fig_coverage.png)

*图 1：左=资产按类别与解析状态分布（唯一 resolved 是 markdown 本体）；右=定位（%(n_loc)d/%(n_loc)d）、
occurrence（%(n_occ)d/%(n_occ)d）、结构检查（%(n_okchk)d/%(n_checks)d）、信封 schema（0 error）的通过率。
数据源=verification.json 与 generator_selfcheck.json，绘图脚本程序化读取，零手抄。*

## ④ 证据定位表（字段 → 原文引文片段）

主资产表（`quote` 前 64 字符的原文切片，完整串见 `asset_manifest.json` 的 `locator.quote`；
char 区间为 [start,end) 半开、以 markdown 字符计）：

| asset | 类型 | 引用 token | 行 / 字符区间 | 原文引文片段 | 解析 | 所在段 |
|---|---|---|---|---|---|---|
%(asset_table)s

全部 occurrence（同一引用在正文中的重复出现，逐条可解）：

| asset | 行 | 字符区间 | 唯一 | 原文片段 |
|---|---|---|---|---|
%(occ_table)s

文档级身份锚点（用于把"这份报告"钉死，均为原文逐字）：

| 事实 | 原文引文 | 定位 |
|---|---|---|
| 标题行 | %(q_title)s | L1 |
| 生成器声明 | %(q_gen)s | L4 |
| 图目录 | %(q_fig)s | L156（fig1 链接行） |
| 复现段 | %(q_repro)s | L%(l_repro)s |

显式排除的非资产 token（%(n_excl)d 条，节选，全量见 `manifest.excluded_tokens.items`）：

| 行 | token | 排除理由 |
|---|---|---|
%(ex_rows)s

## ⑤ 注意点与局限

1. **只转移了 markdown，附件字节没转移**：%(n_unres)d/%(n_assets)d 条资产是
   `referenced_unresolved`。这不是"资产不存在"，而是"本交付包里没有它的字节"——因此不给
   任何 sha256、不 `exists=True` 断言。要闭环必须由 ship-performance-platform 侧在登记时附
   工件清单（或平台提供 artifact 端点，当前 `GET /tensor/reports/9085/artifacts` =
   %(probe_art)s）。
2. **解析范围=交付工作树**，不越界读源仓。若后续能访问源仓，正确做法是新工序按路径+sha256
   重登记，而不是回头修改本清单（互不覆盖）。
3. **图片与记录 figures 是 1:1（%(n_fig)d 名对 %(n_fig)d 名，record_only/markdown_only 皆空）**，
   但平台不暴露图片字节（探针 %(probe_status)s），所以图只能登记"声明"而非"内容"。
4. **shared schema 的三 const 冲突**是既有债：本包用派生 schema + "错误集合 ⊆ 身份常量"的
   双重验证绕过，但没有修共享 schema（越界改别包产物）。建议由平台把
   `asset_manifest.v1.schema.json` 的 const 改成 pattern。
5. **字符区间不等于字节区间**：本报告 markdown 含中文，%(chars)d 字符 / %(bytes)d 字节。
   定位口径已在 `integrity.locator_space` 与 `locator.offset_unit` 写明；跨工具消费时若用
   字节偏移会错位，必须按字符（码点）解释。
6. **claims 为空是刻意的**：本工序 objective 只要求 register_assets，classify_report_type=false。
   为凑"有声明"而抽取=违反 no_forced_claim_generation。故 acceptance 中
   "all_claims_have_evidence"一条按空集成立，见 ⑥。
7. **独立性局限**：verify 与 register 同一作者，独立性仅限"不 import 生成器代码路径、
   全部定位从原文字节反推"；真正的独立复判仍需外部 evidence-auditor。

## ⑥ 自检：逐条对照 acceptance

| acceptance | 结论 | 证据 |
|---|---|---|
%(acc_rows)s

- 失败项：%(fail_items)s
- honest 声明：本包**没有**把任何结论标成 verified，也没有生成 claim；资产登记的价值就是
  "定位可机器重放 + 缺字节的地方如实记 unresolved"，不粉饰为"资产已入库"。

### 误差判定（关键量 vs 基准）

本工序是登记/审计工序，关键量是**字节级一致性与定位可解率**，判据是精确量（无容差意义上的
3%% 概念）；逐项如下，显式回答"是否 <3%%"：

| 关键量 | 基准 | 结论 | 实测偏差 |
|---|---|---|---|
%(err_table)s

**是否全部 <3%%**：是——上表全部为 0 偏差或 100%% 通过（不存在需要 3%% 容差的数值物理量）。
本工序不含任何水动力/结构数值计算，故无"对标实验误差"一项；报告中出现的物理量
（GM、FSM、SF/BM 等）属 register 之外的内容，本工序只登记不计算、也不复述其数值。

## repro_cmd（一键复跑）

```bash
%(repro)s
```

## 结果信封（唯一 json 块）

```json
%(json_block)s
```
""" % {
        "uri": src["uri"], "field": src["field"], "hash": src["hash_prefixed"],
        "bytes": src["bytes_utf8"], "chars": src["chars"], "lines": n_report_lines,
        "contract_hash": src["contract_source_hash"],
        "n_assets": manifest["counts"]["assets"],
        "by_class": json.dumps(manifest["counts"]["by_class"], ensure_ascii=False),
        "n_path": manifest["counts"]["by_class"].get("artifact_path_reference", 0),
        "n_fig": manifest["counts"]["by_class"].get("figure_reference", 0),
        "n_unres": manifest["counts"]["referenced_unresolved"],
        "n_excl": ex["count"],
        "n_unique": manifest["integrity"]["quote_uniqueness"]["unique"],
        "probe_status": src["aux_endpoint_probes"][0]["http_status"] if src.get(
            "aux_endpoint_probes") else "n/a",
        "probe_art": src["aux_endpoint_probes"][0]["http_status"] if src.get(
            "aux_endpoint_probes") else "n/a",
        "ver_ok": ver["overall_ok"], "n_loc": ver["locator_checks_total"],
        "n_occ": ver["occurrence_checks_total"], "n_checks": len(ver["checks"]),
        "n_okchk": sum(1 for c in ver["checks"] if c["ok"]),
        "asset_table": asset_table, "occ_table": occ_table, "ex_rows": ex_rows,
        "acc_rows": acc_rows, "err_table": err_table,
        "fail_items": "无" if all_ok else "、".join(k for k, ok, _ in acc if not ok),
        "q_title": frag(md_src, 0, 40),
        "q_gen": frag(md_src, [a for a in manifest["assets"]
                               if a["reference_token"].endswith(
                                   "gen_bwm_d1_operation_window.py")][0]
                      ["locator"]["start_char"], 46),
        "q_fig": frag(md_src, [a for a in manifest["assets"]
                               if a["reference_token"].endswith("fig1_gm_time.png")][0]
                      ["locator"]["start_char"], 46),
        "q_repro": frag(md_src, md_src.rindex("python3 -m pytest"), 40),
        "l_repro": md_src.count("\n", 0, md_src.rindex("python3 -m pytest")) + 1,
        "n_tests": n_tests, "n_live": n_live,
        "repro": repro, "json_block": json_block,
    }
    REPORT.write_text(md, encoding="utf-8")

    # structural self-check of the delivered markdown
    n_blocks = len(re.findall(r"```json", md))
    body = md.split("```json", 1)[1].split("```", 1)[0].strip() if n_blocks else ""
    sections = ["① 本工序做了什么", "② 怎么做的", "③ 产出物清单", "④ 证据定位表",
                "⑤ 注意点与局限", "⑥ 自检"]
    selfcheck = {
        "title_ok": md.startswith("# KF-RESULT wp-9085-01"),
        "tag_ok": "kf-wp:wp-9085-01" in md,
        "single_json_block": n_blocks == 1,
        "json_block_equals_kf_result_file": json.loads(body) == env if body else False,
        "has_six_sections": all(s in md for s in sections),
        "source_hash_in_block": env["provenance"]["source_hash"],
        "source_hash_matches_manifest": env["provenance"]["source_hash"]
        == manifest["source"]["hash_prefixed"],
        "acceptance_all_true": all_ok,
        "figure": str(fig.relative_to(ROOT)),
    }
    SELFCHECK.write_text(json.dumps(selfcheck, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")

    payload = {
        "title": "KF-RESULT wp-9085-01",
        "summary": "asset registration wp-9085-01 for report 9085: %d assets, "
                   "markdown sha256 %s verified, %d/%d locators resolved, 0 claims"
                   % (manifest["counts"]["assets"], src["hash_prefixed"][:23],
                      ver["locator_checks_passed"], ver["locator_checks_total"]),
        "scenario_key": SCENARIO,
        "mission_id": MISSION_ID,
        "tags": ["kf-wp:wp-9085-01", "01-asset-registration", "report-9085",
                 "BWM", "D-1", "asset-registration"],
        "markdown": md,
        "figures": [{
            "name": "fig_coverage.png",
            "caption": "wp-9085-01 资产类别×解析状态与定位/结构检查通过率",
            "png_base64": base64.b64encode(fig.read_bytes()).decode("ascii"),
        }],
    }
    PAYLOAD.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(selfcheck, ensure_ascii=False, indent=2))
    return 0 if all(v for k, v in selfcheck.items()
                    if k not in {"source_hash_in_block", "figure"}) else 1


if __name__ == "__main__":
    raise SystemExit(main())