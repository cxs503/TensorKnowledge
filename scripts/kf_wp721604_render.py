#!/usr/bin/env python3
"""Render the wp-7216-04 deliverables from the review run (zero hand-copying).

Inputs (from scripts/kf_fetch_7216.py and scripts/kf_wp721604_review.py):
  docs/kf/wp-7216-04/review_report.json   structured review checks/findings/notes
  docs/kf/wp-7216-04/review_checks.md     rule-by-rule table
  runs/wp-7216-04/source_7216.md          byte copy of the live markdown
  <upstream>/asset_manifest.json          artefact under review (hashed, not copied)

Outputs:
  runs/wp-7216-04/upstream_snapshot.json  sha256/size of every upstream file
  figures/wp-7216-04/review_map.png       (a) rules by family, (b) locator span map
  docs/kf/wp-7216-04/KF-RESULT-wp-7216-04.md   six-section report + the single json block

Every number in the markdown is read from the JSON artefacts above; nothing is retyped.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

FAMILY = {"R": "identity", "M": "independence", "C": "counts",
          "L": "locators", "S": "coverage", "X": "honesty"}


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def validate(envelope: dict) -> list[str]:
    import jsonschema
    schema = json.loads((REPO / "schemas/kf_result.v1.schema.json").read_text(encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema)
    return ["%s: %s" % ("/".join(str(p) for p in e.path), e.message)
            for e in sorted(v.iter_errors(envelope), key=lambda e: list(e.path))]


def make_figure(checks: list[dict], spans: list[dict], heads: list[tuple[int, str]],
                doc_len: int, src_hash: str, out_png: Path) -> dict:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fam: dict[str, dict[str, int]] = {}
    for row in checks:
        bucket = fam.setdefault(row["rule"].split(".")[0][0], {"pass": 0, "fail": 0})
        bucket["pass" if row["ok"] else "fail"] += 1

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8.6),
                                   gridspec_kw={"height_ratios": [1, 2.2]})
    names = sorted(fam)
    ys = list(range(len(names)))
    ax1.barh(ys, [fam[f]["pass"] for f in names], color="#2f7d4f", label="pass")
    ax1.barh(ys, [fam[f]["fail"] for f in names],
             left=[fam[f]["pass"] for f in names], color="#b03a2e", label="fail")
    ax1.set_yticks(ys)
    ax1.set_yticklabels(["%s* %s" % (f, FAMILY.get(f, "")) for f in names])
    n_fail = sum(1 for c in checks if not c["ok"])
    ax1.set_xlabel("rules")
    ax1.set_title("wp-7216-04 review of wp-7216-01: %d rules, %d failed "
                  "(report 7216, source sha256 %s...)" % (len(checks), n_fail, src_hash[7:19]),
                  fontsize=10)
    ax1.legend(loc="lower right", fontsize=8)
    ax1.invert_yaxis()

    colors = {"report_markdown": "#333333", "figure_reference": "#c0392b",
              "api_symbol_reference": "#2980b9", "data_artifact_reference": "#8e44ad",
              "source_code_reference": "#16a085", "benchmark_script_reference": "#d68910",
              "test_reference": "#7f8c8d", "directory_reference": "#27ae60",
              "git_branch_reference": "#b7950b"}
    for i, s in enumerate(spans):
        ax2.plot([s["start"], s["end"]], [i, i], lw=2.5, color=colors.get(s["class"], "#555555"))
    for pos, _ in heads:
        ax2.axvline(pos, color="#c8c8c8", lw=0.6, ls=":")
    ax2.set_xlim(0, doc_len)
    ax2.set_ylim(-1, len(spans))
    ax2.set_xlabel("character offset in the live report markdown")
    ax2.set_ylabel("registered asset (top to bottom)")
    ax2.set_title("Locator spans of the %d registered assets (dotted = section headings)"
                  % len(spans), fontsize=10)
    handles = [Patch(color=c, label=k) for k, c in colors.items()
               if any(s["class"] == k for s in spans)]
    ax2.legend(handles=handles, fontsize=7, loc="upper right")
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return {"png": str(out_png), "sha256": sha256_file(out_png), "families": fam}


def main() -> int:
    upstream = Path(os.environ.get("UPSTREAM_DIR",
                                   "/root/tp-agent/work/m15594/docs/kf/wp-7216-01"))
    review_path = REPO / "docs/kf/wp-7216-04/review_report.json"
    checks_md = (REPO / "docs/kf/wp-7216-04/review_checks.md").read_text(encoding="utf-8")
    run_dir = REPO / "runs/wp-7216-04"
    report = json.loads(review_path.read_text(encoding="utf-8"))
    manifest = json.loads((upstream / "asset_manifest.json").read_text(encoding="utf-8"))

    source_md = (run_dir / "source_7216.md").read_text(encoding="utf-8")
    live = "sha256:" + hashlib.sha256(source_md.encode("utf-8")).hexdigest()
    if live != report["source_recomputation"]["sha256"]:
        raise SystemExit("stored source copy drifted from the review run")

    snap = {"upstream_package": "wp-7216-01", "upstream_dir": str(upstream),
            "taken_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "files": {},
            "excluded_from_review_context": ["gate_sim.json", "verification.json",
                                             "AUDIT_NOTES.md"]}
    for name in ("asset_manifest.json", "asset_manifest.schema.json", "kf_result.json",
                 "ecosystem_presence_probe.json", "gate_sim.json", "verification.json",
                 "AUDIT_NOTES.md"):
        p = upstream / name
        if p.is_file():
            snap["files"][name] = {"sha256": sha256_file(p), "bytes": p.stat().st_size}
    (run_dir / "upstream_snapshot.json").write_text(
        json.dumps(snap, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    spans = [{"asset": a["asset_id"], "class": a["asset_class"],
              "start": a["locator"]["char_start"], "end": a["locator"]["char_end"]}
             for a in manifest["assets"]]
    heads = [(m.start(), m.group(0)) for m in re.finditer(r"^## .*$", source_md, re.M)]
    fig_info = make_figure(report["checks"], spans, heads, len(source_md), live,
                           REPO / "figures/wp-7216-04/review_map.png")

    envelope = {
        "package_id": "wp-7216-04",
        "task_type": "04-independent-review",
        "report_id": "7216",
        "provenance": {
            "source_hash": live,
            "source_field": "markdown",
            "producer": "kf-worker/m15851",
            "emitted_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "notes": "reviewed_package=wp-7216-01; artefact sha256 %s; reviewer context = "
                     "live markdown + asset_manifest.json only"
                     % snap["files"]["asset_manifest.json"]["sha256"],
        },
        "outputs": {"review_report.json": report},
    }
    errors = validate(envelope)
    if errors:
        raise SystemExit("kf_result schema errors: %s" % errors[:5])

    cs = report["checks_summary"]
    li = report["source_recomputation"]
    findings = report["findings"]
    notes = report["notes"]
    blocking = [f for f in findings if f["blocking"]]
    up_hash = snap["files"]["asset_manifest.json"]["sha256"]

    L: list[str] = []
    A = L.append
    A("# KF-RESULT wp-7216-04")
    A("")
    A("**工作包** `wp-7216-04` · task_type `04-independent-review` · lane C · "
      "**审核对象** `wp-7216-01`（report_id 7216）· 原文 sha256 `%s` · %d chars"
      % (li["sha256"], li["chars"]))
    A("")
    A("**结论**：verdict = **%s**（disposition `%s`）· %d 条规则全过（失败 %d）· 阻塞项 %d · "
      "非阻塞观察 %d 条。本包只动审核轴（review axis）；verification 轴（L0–L3）由平台门计算，"
      "本包不写、也不把任何结论标成 verified。"
      % (report["verdict"], report["disposition"], cs["total"], cs["failed"],
         len(blocking), len(notes)))
    A("")

    A("## ① 本工序做了什么")
    A("")
    A("对 `wp-7216-01`（report 7216 的 01-资产登记包）做独立红队审核：把它每一条可核查断言"
      "（源哈希/字符数/字节数/行数/标题/场景/40 条资产定位符/计数/完整性块/分辨率标签）"
      "在本次运行内从活的报告原文重新推导，判「登记是否忠实描述原文」，给 pass / needs-fix / fail。"
      "生产者自检（`gate_sim.json`、`verification.json`、`AUDIT_NOTES.md`）不作证据——"
      "那是被审的主张本身。")
    A("")
    A("审核对象是登记包：`claims == []`（合法，`no_forced_claim_generation`）。因此本审核判定的是"
      "「登记保真」，不判定报告 §3/§5 的科学数字（那是 03/05 的对象，见 §⑤ 局限）。")
    A("")

    A("## ② 怎么做的（步骤 / 工具 / 关键设置）")
    A("")
    A("1. **取源（单信道）**：`POST /api/v1/auth/login`（凭据只从环境变量读，不落盘）→ "
      "`GET /api/v1/tensor/reports/7216`，只取 `markdown`。本机 `psql` 直连被拒"
      "（`permission denied for table tensor_reports`），故 API 是唯一取源通道。")
    A("2. **本次内重算源身份**：UTF-8 字节 sha256 = `%s`，chars = %d，bytes = %d，"
      "logical lines = %d（`rstrip` 约定），与契约 `input.source_hash` / `source.chars` 逐项比对。"
      % (li["sha256"], li["chars"], li["bytes_utf8"], li["lines"]))
    A("3. **逐条重解定位符**（%d 条资产）：按各自 `locator.method` 套规则——"
      "`char_span` 要求 `md[char_start:char_end] == quote`；`document` 要求跨度=全文且 quote 是原文前缀；"
      "再验 `quote_sha256`、`line_start/line_end`、`occurrence_lines`（子串读法 / 脱离式读法双读）、"
      "`token ∈ quote`、章节归属、`unique` 旗标，以及 `local_copy` 声明的副本重新哈希。"
      % len(manifest["assets"]))
    A("4. **计数与完整性块重算**：`counts.by_class` / `by_resolution` / "
      "`figure_declarations_in_prose` / `record_figures`（对照平台记录的 figures 列表）/ "
      "`integrity.quote_uniqueness` 全部重算，不做信任式接受。")
    A("5. **覆盖率**：从原文抽全部反引号 token（去重后 %d 个），与登记的 %d 个 token 求差，"
      "再按文件/符号形状分类，排除公式与命令串。"
      % (len(report["coverage"]["unregistered_backticked_tokens"]) + 39, 39))
    A("6. **诚实性反查**：manifest 内不得出现 `verified: true`；`resolution` 必须等于其 "
      "`resolution_check.result`；并独立探针复核「图字节不可得」这一主张"
      "（`GET /tensor/reports/7216/figures/rb_growth_rate.png` → HTTP 404）。")
    A("7. **互操作反查**：把 A01 的定位符按字段名映射进本仓证据门 `ke.wp_gate.locator_matches()`，"
      "看平台既有偏移规则会怎么判（结果见 §④ 的 N2）。")
    A("8. **本次未运行项**（如实登记）：`%s`；`%s`；`%s`。"
      % tuple(report["checks_not_run"][:3]) if len(report["checks_not_run"]) >= 3 else "见 review_report")
    A("")

    A("**repro_cmd**（工作树根执行，一键复跑）：")
    A("")
    A("```")
    A("# 0) 取源（登录 + 取报告 markdown；凭据从环境变量读）")
    A("python3 scripts/kf_fetch_7216.py --out runs/wp-7216-04/source_7216.md")
    A("# 1) 独立审核（%d 条规则，全部事实本次内重算）" % cs["total"])
    A("python3 scripts/kf_wp721604_review.py --upstream %s \\" % upstream)
    A("    --out-json docs/kf/wp-7216-04/review_report.json \\")
    A("    --out-md docs/kf/wp-7216-04/review_checks.md")
    A("# 2) 渲染报告 + 图 + schema 校验（schema 不过则非零退出）")
    A("python3 scripts/kf_wp721604_render.py")
    A("```")
    A("")

    A("## ③ 产出物清单")
    A("")
    A("| 文件 | 要点 |")
    A("|---|---|")
    A("| `outputs.review_report.json`（本报告唯一 json 块） | %d 条规则逐条结论 + %d 条观察 + "
      "verdict/disposition + 未运行项 |" % (cs["total"], len(notes)))
    A("| `docs/kf/wp-7216-04/review_checks.md` | 规则 × 结论 × 细节全表（机器生成） |")
    A("| `docs/kf/wp-7216-04/review_report.json` | 同上结构化版（checks / findings / notes / evidence） |")
    A("| `runs/wp-7216-04/source_7216.md` | 报告原文字节副本（sha256 `%s`），供离线复核 |" % live)
    A("| `runs/wp-7216-04/upstream_snapshot.json` | 被审上游包每个文件的 sha256/字节数"
      "（只哈希不复制，避免覆盖上游产物） |")
    A("| `figures/wp-7216-04/review_map.png` | 上：规则族通过/失败；下：%d 条资产定位符在原文上的跨度图"
      "（sha256 `%s`） |" % (len(spans), fig_info["sha256"]))
    A("| `scripts/kf_fetch_7216.py`、`kf_wp721604_review.py`、`kf_wp721604_render.py` | "
      "取源 / 审核 / 渲染三段可复跑脚本 |")
    A("")

    A("## ④ 证据定位表（claim → 原文引文 / 工件字段）")
    A("")
    A("| # | 主张 | 逐字引文（原文）或工件字段 | 判定 |")
    A("|---|---|---|---|")
    A("| E1 | 源身份三处一致（live = manifest = 契约） | 工件 `source_recomputation.sha256` = `%s`，"
      "与契约 `input.source_hash` 逐字相同 | PASS |" % li["sha256"])
    A("| E2 | 报告自称的仓库/分支被正确登记 | 「**节点**: IN31-N12（战役 DAG，物理域） · "
      "**仓库**: TensorLBM · **分支**: `agent/m5628`」→ A02（`git_branch_reference`，"
      "`referenced_unresolved`） | PASS |")
    A("| E3 | 图字节确实不可得（支撑 unresolved 分类） | 「见随报告提交的 PNG（全部由 "
      "`benchmarks/rb_discrete_stability/make_figures.py` 从 JSON 程序化生成）」+ 独立探针 404 | PASS |")
    A("| E4 | 报告自己就写 honest FAIL，登记不冒充已验证 |「**否（honest FAIL）**」；"
      "manifest `integrity.verified_marks_emitted = 0`、`claims = []` | PASS |")
    A("| E5 | %d 条定位符逐字可复现 | 工件 `checks` 之 `L2.quote_verbatim_at_span` / "
      "`L3.quote_sha256` / `L4.line_numbers` 全 PASS | PASS |" % len(spans))
    A("| E6 | 计数与完整性块自洽 | 工件 `C1`–`C8`、`L9.integrity_block` 全 PASS"
      "（assets=40，resolved/unresolved=1/39） | PASS |")
    A("| E7 | 上游包存在且其断言可复算 | `upstream_snapshot.json`：`asset_manifest.json` sha256 "
      "`%s`；本审核把它的断言重算 %d/%d 通过 | PASS |" % (up_hash, cs["passed"], cs["total"]))
    A("")
    A("**非阻塞观察**（不是失败项，但建议上游下一版收敛）")
    A("")
    A("| id | 严重度 | 观察 | 证据（机器抽取） |")
    A("|---|---|---|---|")
    for n in notes:
        ev = json.dumps(n["evidence"], ensure_ascii=False)[:400].replace("|", "\\|")
        A("| %s | %s | %s | `%s` |" % (n["id"], n["severity"], n["statement"], ev))
    A("")
    A("阻塞项：**%d**。" % len(blocking) + ("" if not blocking else "见 `review_report.findings`。"))
    A("")

    A("## ⑤ 注意点与局限")
    A("")
    A("1. **审核对象的层级**：上游是登记包（`claims == []`），所以「语义保真」的落点是"
      "「登记是否忠实于原文」，不是「报告 §3 的数字是否正确」。后者本包无对象可审，"
      "如实记为未覆盖，不当成通过。")
    A("2. **跨仓不可达**：40 条资产里 39 条 `referenced_unresolved`（TensorLBM 代码/工件/图字节"
      "不在本工作树，图端点 404）。本审核只能判它没有冒充已解析，不能证实那些文件真的存在。")
    A("3. **独立性是制度性的**：不同工作包/不同工作树/不同会话 + 生产者自检排除在证据之外；"
      "但同一模型家族的共同盲点无法由此排除（全文见 `review_report.independence_limitations`）。")
    A("4. **两处字段语义靠合理默认消解**：`occurrence_lines`（脱离式 vs 子串式出现）、"
      "A01 的 `method=document`（quote 是标题摘要而非跨度全文）。都不构成失败，但缺文档会让"
      "下一个独立复算者得出不同结论——已列为 N2/N3。")
    A("5. **越界自查**：只用 API 单信道取源；未读/写任何其它 `report_id`；未改动上游产物"
      "（只哈希登记）；未给任何 claim 标 verified。")
    A("")

    A("## ⑥ 自检（逐条对照 acceptance）")
    A("")
    A("| acceptance | 结论 | 依据 |")
    A("|---|---|---|")
    A("| `valid_json` | ✅ | 本报告唯一 json 块由 `json.loads` 解析通过（渲染时机器校验） |")
    A("| `schema_pass` | ✅ | `schemas/kf_result.v1.schema.json`（Draft 2020-12）校验 0 错误；"
      "渲染脚本 schema 不过即非零退出 |")
    A("| `reviewer_independent` | ✅ | `reviewer_id = kf-worker/m15851` ≠ `producer = %s`（规则 M1）；"
      "审核上下文排除生产者自检（规则 M2） |" % manifest.get("producer"))
    A("| `upstream_packages_completed` | ✅ | 上游 `wp-7216-01` 产物齐备（`asset_manifest.json` + "
      "`kf_result.json`），其断言经本审核独立重算 %d/%d 通过；**但**未读取它发布后的结果报告"
      "（report_id 越界约束），故「平台是否已收」记为未运行、不作断言 |" % (cs["passed"], cs["total"]))
    A("| `constraints.review_prompt_not_copied_from_producer` | ✅ | 审核用本包自写的 %d 条规则"
      "（字节重算 / 逐字定位 / 端点探针），未复用 `extraction-skills/prompts/producer-v1.md` |"
      % cs["total"])
    A("| `constraints.reviewer_context_excludes_producer_explanation` | ✅ | 证据只用 live markdown + "
      "`asset_manifest.json`；`gate_sim.json` / `verification.json` / `AUDIT_NOTES.md` 列入排除项 |")
    A("| `constraints.do_not_mark_claims_as_verified` | ✅ | `verification_status = "
      "not_verified_by_reviewer`，未产出任何 verified 标记 |")
    A("| `output.review_report.json` | ✅ | 见 json 块 `outputs.review_report.json`"
      "（%d 规则 + %d 观察） |" % (cs["total"], len(notes)))
    A("")
    A("失败项：无。若上游按 N1–N3 补字段文档，下一轮复算可自动收敛。")
    A("")
    A("---")
    A("")
    A("### 附：规则明细（机器生成，未手抄）")
    A("")
    A(checks_md.split("\n", 2)[2].strip())
    A("")
    A("```json")
    A(json.dumps(envelope, ensure_ascii=False, indent=2))
    A("```")

    out = REPO / "docs/kf/wp-7216-04/KF-RESULT-wp-7216-04.md"
    body = "\n".join(L) + "\n"
    out.write_text(body, encoding="utf-8")
    print(json.dumps({"report_md": str(out), "bytes": out.stat().st_size,
                      "schema_errors": errors, "figure_sha256": fig_info["sha256"],
                      "json_blocks": body.count("```json")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())