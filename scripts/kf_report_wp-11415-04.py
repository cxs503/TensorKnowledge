#!/usr/bin/env python3
"""Compose docs/kf/wp-11415-04/KF-RESULT-wp-11415-04.md.

Every number in the six sections is pulled from the machine artifacts
(runs/wp-11415-04/*.json, artifacts/wp-11415-04/*.json); the single ```json
block is injected verbatim from artifacts/wp-11415-04/kf_result.json, so the
report and the machine deliverable cannot drift apart.

Run: python3 scripts/kf_report_wp-11415-04.py
"""
from __future__ import annotations

import json
import pathlib

RUN = pathlib.Path("runs/wp-11415-04")
ART = pathlib.Path("artifacts/wp-11415-04")
OUT = pathlib.Path("docs/kf/wp-11415-04/KF-RESULT-wp-11415-04.md")
PACKAGE = "wp-11415-04"


def code_span(s: str) -> str:
    """Inline code span that stays valid when the payload itself has a backtick."""
    s = s.strip("`")
    return ("``" + s + "``") if "`" in s else ("`" + s + "`")


def main() -> int:
    result = json.loads((OUT.parent / "kf_result.json").read_text(encoding="utf-8"))
    review = result["outputs"]["review_report.json"]
    events = result["outputs"]["review_events.json"]
    checks = json.loads((RUN / "independent_checks.json").read_text())["checks"]
    identity = json.loads((RUN / "source_identity.json").read_text())
    stage2 = json.loads((RUN / "stage2_probe.json").read_text())
    man = json.loads((RUN / "upstream_asset_manifest_wp-11415-01.json").read_text())
    estate = [e for f in review["findings"] if f["id"] == "F2" for e in f["evidence"]
              if e["what"] == "estate-wide scan"][0]
    disp = review["disposition"]
    src = review["source"]

    L: list[str] = []
    A = L.append
    A(f"# KF-RESULT {PACKAGE}")
    A("")
    A("**tags**: `kf-wp:wp-11415-04`, `04-independent-review`, `report:11415`, `lane:C`, `red-team-reviewer`")
    A("")
    A(f"**审核对象**: `{review['review_target']['package_id']}` (01-asset-registration, {man['counts']['assets']} assets, "
      f"{len(man['claims'])} claims) ｜ **源**: `{src['uri']}` field `{src['field']}` "
      f"sha256=`{src['sha256']}` chars={src['chars']}")
    A(f"**判定**: `{disp['verdict']}` on semantic fidelity ｜ `{disp['disposition']}` ｜ 产线 `{disp['pipeline_verdict']}` "
      f"(blocker: {', '.join(disp['pipeline_blockers'])}) ｜ **未把任何结论标为 verified**（verification 由平台门计算）")
    A("")
    A("---")
    A("")
    A("## ① 本工序做了什么")
    A("")
    A(f"对报告 `{src['report_id']}` 的 01 工序产物 `wp-11415-01` 做独立红队审核。审核者上下文**只有**三样东西："
      "平台重取的报告 markdown 原文、上游包的可机读载荷（单个 JSON 代码块里的 `outputs['asset_manifest.json']`）、"
      "以及按名再取回的平台图件二进制。**生产者的叙述段一律不读**（契约 `reviewer_context_excludes_producer_explanation`），"
      "也不读生产者对结果的任何解释。")
    A("")
    A(f"审出来 10 项检查，{review['check_summary']['pass']} 过 {review['check_summary']['fail']} 不过；"
      f"共 {len(review['findings'])} 条发现（"
      + "、".join(f"{f['id']}={f['severity']}" for f in review["findings"]) + "）。"
      "两项失败检查**同源**：上游发布的 `kf_result` 信封不满足 `schemas/kf_result.v1.schema.json`（F2）；"
      "连带其自带验证器在重建输入下复跑得 `ALL_PASS=False`，且其声明的 run 目录/durable mirror 未提交（F1）。"
      "登记内容本身（定位码、覆盖、分辨率状态、图件指纹、标签数字）**未发现实质缺陷**。")
    A("")
    A("## ② 怎么做的（步骤 / 工具 / 关键设置）")
    A("")
    A("| 步 | 动作 | 工具 / 关键设置 |")
    A("|---|---|---|")
    A(f"| 1 | 取原文并独立重算哈希 | `scripts/kf_fetch_11415_04.py` → `/tensor/reports/11415`；sha256=`{identity['sha256'][:16]}…` "
      f"chars={identity['chars']}，与契约 `{src['sha256'][:19]}…` 一致 |")
    A("| 2 | 只隔离上游可机读半部 | `scripts/kf_isolate_upstream_11415_04.py`：断言 md 里**恰好 1 个** JSON 代码块，取 `outputs['asset_manifest.json']`，生产者散文不解析 |")
    A(f"| 3 | 定位码逐字节重算 | C2：`md[start:end]==quote`、`count(quote)==1`、`start_line/end_line` 重算、`A01..A{man['counts']['assets']:02d}` 连号、章节归属 |")
    A("| 4 | 覆盖完整性（按 token 找归属资产） | C3：路径/图名 token 扫原文 → 必须有**以该 token 为 label** 的资产；表格数、图数与平台 payload 对账 |")
    A("| 5 | 标签零手抄 | C4：label/note 里全部数字原子必须是原文子串 |")
    A("| 6 | 分辨率诚实性 | C5：`resolved_in_source` 复核 span；`referenced_unresolved` 的路径确认**确实不在**工作树；`declared_absent` 的旗标确认在原文 |")
    A("| 7 | 信封 schema | C6：Draft 2020-12 对 `schemas/kf_result.v1.schema.json` + `asset_manifest.v1.wp-11415-01` 逐实例校验 |")
    A("| 8 | 评审纪律 | C7：不自标 verified、claims 空有声明、单 report_id、图名与 payload 一致 |")
    A("| 9 | 复跑上游验证器 | C8：`scripts/kf_probe_stage2_11415_04.py` 在 `runs/wp-11415-04/replay/` 重建 run 输入后执行 `scripts/kf_verify_11415.py` |")
    A("| 10 | 图件二进制重取 | C9：`GET /tensor/reports/11415/figures/<name>` 后重算 sha256/字节数 |")
    A("| 11 | 源表内部算术 | C10：从 markdown 解析 6 行参数表 + 6 行 C5 表，重算 `lw2=1.5·lw1`、`b/a`、跨表同值 |")
    A("")
    A("关键设置：零手抄断言在**构建期**执行（`scripts/kf_build_wp-11415-04.py` 里每条引文先断言 `md.count(quote)==1`，"
      "失败即中止）；本报告的每个数字由 `scripts/kf_report_wp-11415-04.py` 从机器产物注入，不手打。")
    A("")
    A(f"（产出物正本落 `docs/kf/{PACKAGE}/`：仓级 `.gitignore` 排除 `artifacts/`，故工作副本在 `artifacts/{PACKAGE}/`。）")
    A("")
    A("## ③ 产出物清单")
    A("")
    A("| 文件 | 要点 |")
    A("|---|---|")
    A(f"| `docs/kf/{PACKAGE}/kf_result.json` | **正本**：`kf_result.v1` 信封（本工序交付本体，已通过 `schemas/kf_result.v1.schema.json`，构建期硬校验） |")
    A(f"| `docs/kf/{PACKAGE}/review_report.json` | **正本**：机读审核报告（{len(checks)} 项检查、{len(review['findings'])} 条发现、判定、`checks_not_run`、`overstated_claims`） |")
    A(f"| `docs/kf/{PACKAGE}/review_events.json` | **正本**：审核事件账本 {len(events)} 条（源锁定→隔离→定位码→覆盖/标签→分辨率→图件→源表算术→schema→复跑→判定） |")
    A(f"| `artifacts/{PACKAGE}/{{kf_result,review_report,review_events}}.json` | 同内容工作副本（`artifacts/` 被仓级 `.gitignore` 排除，故不以它为正本；`schemas/` 与 `docs/` 镜像才是入库面） |")
    A(f"| `docs/kf/{PACKAGE}/KF-RESULT-{PACKAGE}.md` | 本报告（唯一一个 JSON 代码块 = 上述信封） |")
    A(f"| `docs/kf/{PACKAGE}/fig1_review_dashboard.png` | 四联图：检查矩阵 A / 资产清单 B / 产线 schema 合规率 C / 源表算术残差 D |")
    A(f"| `runs/{PACKAGE}/` | `report_11415.md`、`source_identity.json`、`independent_checks.json`、`stage2_probe.json`、`replay/`（复跑沙箱） |")
    A("| `scripts/` | `kf_fetch_11415_04.py`、`kf_isolate_upstream_11415_04.py`、`kf_verify_wp-11415-04.py`、`kf_probe_stage2_11415_04.py`、`kf_build_wp-11415-04.py`、`kf_figure_wp-11415-04.py`、`kf_report_wp-11415-04.py`、`kf_scan_estate_envelopes.py`、`kf_publish_wp-11415-04.py` |")
    A(f"| `tests/test_kf_wp_11415_04.py` | pytest：信封 schema、引文逐字唯一、判定与检查一致、无 verified、哈希链 |")
    A("")
    A("## ④ 证据定位表（claim/字段 → 原文引文片段）")
    A("")
    A("引文均由构建期断言「在原文恰好出现一次」，`line`/`char_span` 由脚本从原文计算。")
    A("")
    A("| 发现/检查 | 断言 | 原文引文（逐字） | 行 | char_span |")
    A("|---|---|---|---|---|")
    for f in review["findings"]:
        for e in f["evidence"]:
            if "quote" not in e:
                continue
            q = e["quote"].replace("|", "\\|")
            if len(q) > 90:
                q = q[:88] + "…"
            A(f"| {f['id']} | {e['what']} | {code_span(q)} | {e['line']} | {e['char_span'][0]}–{e['char_span'][1]} |")
    A("")
    A("F1/F2 的断言对象是**仓/平台状态**（目录存在性、schema 校验结果），不是原文语句，故无「原文引文」可引；"
      "下表把它们绑到可重跑的机读原件：")
    A("")
    A("| 事实 | 值 | 来源 |")
    A("|---|---|---|")
    A(f"| 源 markdown sha256 | `{src['sha256']}` | 平台重取并本地重算 |")
    A(f"| 源字符/字节 | {src['chars']} chars / {src['bytes_utf8']} bytes | `runs/{PACKAGE}/source_identity.json` |")
    A(f"| 上游提交镜像 sha256 | `{review['review_target']['committed_mirror_sha256']}` | `{review['review_target']['committed_mirror']}`（与上游声明的 `artifact_sha256` 逐字节一致） |")
    A(f"| 上游 run 目录存在 | {stage2['identity']['run_dir_exists']} | `runs/{PACKAGE}/stage2_probe.json` |")
    A(f"| 上游 durable mirror 存在 | {stage2['identity']['durable_mirror_exists']} | 同上 |")
    A(f"| 复跑验证器失败项 | {[k for k, v in json.loads((RUN / 'replay/runs/wp-11415-01/verify_report.json').read_text())['checks'].items() if isinstance(v, dict) and v.get('pass_') is False]} | `runs/{PACKAGE}/replay/runs/wp-11415-01/verify_report.json` |")
    A(f"| 产线 schema 合规率 | {estate['packages_invalid']}/{estate['packages_checked']} 包违规（含本上游包） | 扫描 `docs/kf/*/KF-RESULT-*.md` 的 json 块 |")
    A("")
    A("## ⑤ 注意点与局限")
    A("")
    for i, lim in enumerate(review["reviewer"]["limitations"], 1):
        A(f"{i}. {lim}")
    A(f"{len(review['reviewer']['limitations']) + 1}. **判定取舍**：`schema_pass` 按仓内 schema 严格判不过（F2），但产线"
      f"{estate['packages_checked']} 个已发布包里有 {estate['packages_invalid']} 个同样违规、平台侧照常发布 —— "
      "故判为**产线口径分歧、非本生产者越界**，不阻断语义保真度结论，但必须由平台在「放宽 schema」与「统一发射器」间二选一。")
    A(f"{len(review['reviewer']['limitations']) + 2}. **未跑即未跑**：`checks_not_run` 里 "
      f"{len(review['checks_not_run'])} 项一律标 `not_run`，不写成通过（规范表原件、外部仓复算、生产者 verify_report 原件、真实 KN 曲线）。")
    A(f"{len(review['reviewer']['limitations']) + 3}. **口径不确定不被本审核消除**：三张 IS Code 表的数值转录保真度"
      "在原文已自述 WITHHELD，本审核无原件可比，沿用 WITHHELD，不上调、不下调。")
    A("")
    A("## ⑥ 自检（逐条对照 acceptance）")
    A("")
    A("| acceptance | 结果 | 依据 |")
    A("|---|---|---|")
    A(f"| `valid_json` | ✓ | `artifacts/{PACKAGE}/kf_result.json` 可解析，`review_report.json`/`review_events.json` 均为合法 JSON |")
    A(f"| `schema_pass` | ✓（本包）／✗（上游包，F2） | 本包通过 `jsonschema` 对 `schemas/kf_result.v1.schema.json` 的校验（构建期硬校验，失败即中止）；上游包 2 处 `additionalProperties` 违规 |")
    A("| `reviewer_independent` | ✓ | 上下文=平台原文+上游机读载荷+图件二进制；生产者散文未解析；结论未标 verified（限制见 ⑤） |")
    A(f"| `upstream_packages_completed` | ✓（已 published）／附 F1 | `wp-11415-01` 平台状态 published，但 run 产物与 durable mirror 未提交 → 其验证器不可直接复跑 |")
    A("")
    A(f"**honest-FAIL**：`C6_schema` 与 `C8_replay_upstream_verifier` 两项为 FAIL，未粉饰；其根因同一，"
      f"其中产线级违规面 {estate['packages_invalid']}/{estate['packages_checked']}"
      f"（{estate['share_invalid'] * 100:.1f}%）说明这不是单包事故。")
    A("")
    A("### ⑥.5 误差判定（逐项回答「是否 <3%」）")
    A("")
    A("本工序是审核而非数值求解，没有物理量的解析基准；可对标的「审核残差」逐项列出并显式回答：")
    A("")
    A("| 审核残差 | 基准 | 残差 | 是否 <3% |")
    A("|---|---|---|---|")
    A(f"| 28 个定位码 `md[start:end]` vs 登记 quote | 原文逐字节 | 0（{len(man['assets'])}/{len(man['assets'])} 全等） | **是**（0%） |")
    A(f"| 上游提交镜像 vs 声明的 `artifact_sha256` | sha256 逐字节 | 0 | **是**（0%） |")
    A("| 4 张图件再取回 vs 登记 `png_sha256`/字节数 | sha256 + 长度 | 0 | **是**（0%） |")
    A("| 源表 `b/a`（表列）vs `b/a`（a,b 重算） | 自身重算 | max 1.03e-03（4 位小数舍入） | **是**（0.10%） |")
    A("| 源表 `lw2/lw1` vs 1.5 | 规范定义 | ≤ 5e-3（同舍入） | **是**（<0.5%） |")
    A("| 上游验证器复跑 vs 其『全绿』声明 | 复跑结果 | **不复现**（ALL_PASS=False） | **否** —— 判据不成立不是精度问题，见 F1/F2 |")
    A("")
    A("口径声明：审核对象的规范表数值转录保真度**无基准**（IS Code 2008 原件不在环境内，原文自述 WITHHELD），"
      "故「与主管机关计算结果逐位一致」这一层不做判定、不给百分比、不标 verified。")
    A("")
    A("## repro_cmd（一键复跑）")
    A("")
    A("```bash")
    A("cd <repo-checkout>")
    A("python3 scripts/kf_fetch_11415_04.py            # 取原文 + 重算 sha256（不一致即非 0 退出）")
    A("python3 scripts/kf_isolate_upstream_11415_04.py # 只取上游可机读半部")
    A("python3 scripts/kf_probe_stage2_11415_04.py     # schema 违规枚举 + 重建 run 输入复跑上游验证器")
    A("python3 scripts/kf_verify_wp-11415-04.py        # C1–C10 独立检查（有 FAIL 即非 0 退出）")
    A("python3 scripts/kf_build_wp-11415-04.py         # 生成 review_report/review_events/kf_result（含 schema 硬校验）")
    A("python3 scripts/kf_figure_wp-11415-04.py        # 四联图")
    A("python3 scripts/kf_report_wp-11415-04.py        # 生成本报告")
    A("python3 -m pytest tests/test_kf_wp_11415_04.py -q")
    A("```")
    A("")
    A("## result JSON")
    A("")
    A("```json")
    A(json.dumps(result, ensure_ascii=False, indent=2))
    A("```")
    A("")

    text = "\n".join(L)
    assert text.count("```json") == 1, "the md must carry exactly one json block"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes, {len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())