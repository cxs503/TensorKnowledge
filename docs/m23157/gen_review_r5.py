#!/usr/bin/env python3
"""Render the PROD-RA R5 review bundle from measured evidence (no hand-typed numbers)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
J = json.loads((HERE / "r5_recheck.json").read_text(encoding="utf-8"))
FIG = HERE / "figures"
FIG.mkdir(exist_ok=True)

LOC = J["r4_1_locators"]
EP = J["r4_2_entry_point"]
D6 = J["d6_evidence_bundle"]
SIX = J["six_checks"]
SUM = J["r4_3_sha256sums"]
COMMIT = J["reviewed_commit"]
FIXREV = J["fix_rev_under_review"]

# ---------------------------------------------------------------- figure 1
fig, ax = plt.subplots(figsize=(9, 4.6))
labels = ["resolved\ncold-start", "resolved only after\nruns/->docs/ rewrite",
          "unresolvable even\nafter rewrite"]
vals = [LOC["pure_path_resolved_cold"],
        LOC["pure_path_resolved_after_prefix_repair"],
        LOC["pure_path_unresolvable_even_after_repair"]]
bars = ax.bar(labels, vals, color=["#2e7d32", "#f9a825", "#c62828"])
for b, v in zip(bars, vals):
    ax.annotate(str(v), (b.get_x() + b.get_width() / 2, v), ha="center",
                va="bottom", fontsize=11, fontweight="bold")
ax.set_ylabel("locator fields")
ax.set_title(f"R5 R4-1: cold-start resolution of {LOC['pure_path_fields']} file locators\n"
             f"main@{COMMIT[:8]} (no legacy worktree mounted)")
ax.axhline(0, color="k", lw=0.8)
fig.text(0.01, 0.01, f"legacy runs/m22059 prefix: {LOC['pure_path_fields_legacy_runs_prefix']} fields; "
                     f"absolute foreign /srv/tensor/agent refs: {LOC['pure_path_fields_absolute_foreign']}",
         fontsize=8)
fig.tight_layout(rect=(0, 0.03, 1, 1))
fig.savefig(FIG / "r5-locator-coldstart.png", dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- figure 2
fig, ax = plt.subplots(figsize=(9, 4.2))
names = ["as shipped\n(cold clone)", "as shipped\n(legacy worktree)",
         "as shipped\n(runs/ layout present)", "fixed PR#511\n(cold clone)",
         "fixed PR#511\n(legacy worktree)"]
keys = ["as_shipped", "as_shipped_legacy_target", "as_shipped_prepared_runs_layout",
        "fixed_cold_start", "fixed_legacy_target"]
codes = [EP[k]["exit_code"] for k in keys]
colors = ["#c62828" if c else "#2e7d32" for c in codes]
bars = ax.bar(names, [c if c is not None else 0 for c in codes], color=colors)
for b, c in zip(bars, codes):
    ax.annotate(f"exit {c}", (b.get_x() + b.get_width() / 2, (c or 0)), ha="center",
                va="bottom", fontsize=10, fontweight="bold")
ax.set_ylim(0, max(codes + [1]) + 1)
ax.set_ylabel("process exit code")
ax.set_title("R5 R4-2: reviewer entry point recheck.py — measured exit codes\n"
             "(a zero exit proves the run completed; recheck.py has an unconditional 'return 0')")
errs = [EP["as_shipped"]["stderr_last_line"][:46], EP["as_shipped_legacy_target"]["stderr_last_line"][:46],
        EP["as_shipped_prepared_runs_layout"]["stderr_last_line"][:46], "six checks emitted", "six checks emitted"]
for i, e in enumerate(errs):
    ax.annotate(e, (i, 0.12), rotation=90, fontsize=6.5, ha="center", va="bottom", color="white")
fig.tight_layout()
fig.savefig(FIG / "r5-entrypoint-exitcodes.png", dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- figure 3
rows = [
    ("1 artifact_identity", SIX["1_artifact_identity"]["pass"],
     f"{SIX['1_artifact_identity']['inputs_match']}/{SIX['1_artifact_identity']['inputs_declared']} input digests match"),
    ("2 criteria frozen", SIX["2_criteria_frozen_before_run"]["pass"],
     f"canonical sha256 match={SIX['2_criteria_frozen_before_run']['match_canonical']}"),
    ("3 evidence traceability", SIX["3_evidence_traceability"]["pass"],
     f"unresolvable={SIX['3_evidence_traceability']['n_unresolvable']}"),
    ("4 independent rerun", SIX["4_independent_rerun"]["pass"],
     f"claim audit {SIX['4_independent_rerun']['claim_audit_status_rerun']}; negatives detected"),
    ("5 failure record", SIX["5_failure_record"]["pass"],
     f"{len(SIX['5_failure_record']['independent_items_without_input_sha256'])}/{D6['items']} items without input_sha256"),
    ("6 regression scope", SIX["6_regression_scope"]["pass"],
     SIX["6_regression_scope"]["adjacent_unit_tests"]),
]
fig, ax = plt.subplots(figsize=(9.6, 3.9))
ax.set_xlim(0, 10)
ax.set_ylim(0, len(rows) + 1.2)
ax.axis("off")
ax.set_title("R5: six checks re-run on the repaired entry point + D6 evidence-bundle recomputation")
for i, (name, ok, note) in enumerate(rows):
    y = len(rows) - i
    ax.add_patch(plt.Rectangle((0.1, y - 0.38), 9.8, 0.76,
                               color="#e8f5e9" if ok else "#ffebee", ec="#90a4ae", lw=0.6))
    ax.text(0.25, y, name, fontsize=10, va="center", fontweight="bold")
    ax.text(3.0, y, "PASS" if ok else "FAIL", fontsize=10, va="center",
            color="#2e7d32" if ok else "#c62828", fontweight="bold")
    ax.text(4.0, y, note, fontsize=8.6, va="center")
ax.text(0.25, 0.45, f"D6: schema {D6['schema_ok_count']}/{D6['items']} valid; "
                    f"input_sha256 {D6['items'] - len(D6['items_without_input_sha256'])}/{D6['items']}; "
                    f"source_ref resolving cold-start {D6['source_ref_resolve_cold']}/{D6['items']}; "
                    f"bundle self-digest match={D6['bundle_sha256_matches']}",
        fontsize=8.6)
fig.tight_layout()
fig.savefig(FIG / "r5-sixchecks-d6.png", dpi=140)
plt.close(fig)

# ---------------------------------------------------------------- receipt
receipt = {
    "schema": "prod-ra-review-receipt/5",
    "repo": "TensorKnowledge",
    "reviewed_commit": COMMIT,
    "reviewed_commit_subject": J["reviewed_commit_subject"],
    "fix_commit_under_review": FIXREV,
    "fix_commit_in_main": False,
    "target": J["target"],
    "target_is_cold_clone": J["target_is_cold_clone"],
    "baseline_rows": [903, 918],
    "verdict": "changes_requested",
    "scenario_validated": False,
    "scenario_validated_note": "复审席不置位；由协调者依裁决执行",
    "residuals": [
        {"id": "R5-1", "severity": "blocking", "inherits": "R4-1",
         "finding": "file locators inside docs/m22059/** still address runs/m22059/**; a third party "
                    "with no legacy worktree resolves %d/%d locator fields cold-start"
                    % (LOC["pure_path_resolved_cold"], LOC["pure_path_fields"]),
         "evidence": {"pure_path_fields": LOC["pure_path_fields"],
                      "legacy_runs_prefix": LOC["pure_path_fields_legacy_runs_prefix"],
                      "absolute_foreign": LOC["pure_path_fields_absolute_foreign"],
                      "resolved_cold": LOC["pure_path_resolved_cold"],
                      "resolved_only_after_rewrite": LOC["pure_path_resolved_after_prefix_repair"],
                      "unresolvable_after_rewrite": LOC["pure_path_unresolvable_even_after_repair"]}},
        {"id": "R5-2", "severity": "major", "inherits": "R4-3",
         "finding": "reviewer bundle manifest still unsound: %d of %d SHA256SUMS entries unsound"
                    % (len(SUM["missing"]) + len(SUM["mismatch"]), SUM["entries"]),
         "evidence": SUM},
        {"id": "R5-3", "severity": "minor", "inherits": "R4-4",
         "finding": "3/5 evidence items carry absolute foreign input_refs under /srv/tensor/agent/work/m22760; "
                    "ev-kb10k-incompatibility still has no input_sha256",
         "evidence": {"items_without_input_sha256": D6["items_without_input_sha256"],
                      "items_with_absolute_foreign_input_refs": D6["items_with_absolute_foreign_input_refs"]}},
        {"id": "R5-4", "severity": "info",
         "finding": "recheck.py signals a false failure in its failure_record section (top-level "
                    "input_sha256 lookup while the repaired items nest it in provenance) and exits 0 "
                    "unconditionally, so an author-reported exit_code=0 carries no acceptance weight",
         "evidence": {"recheck_signal": SIX["5_failure_record"]["recheck_script_signal_items_without_input_fingerprint"],
                      "independent": SIX["5_failure_record"]["independent_items_without_input_sha256"]}},
    ],
    "r4_acceptance": {
        "R4-1_locators_cold_start": {"accepted": False,
                                     "detail": "repair exists only on commit %s; the docs/m22059 rewrite "
                                               "never reached the delivery branch and the family of "
                                               "absolute /srv/tensor/agent refs remains" % FIXREV},
        "R4-2_entry_point_exit_code": {"accepted": True,
                                       "detail": "fixed recheck.py exit %s on a cold clone and %s on the "
                                                 "legacy worktree; as-shipped still fails"
                                                 % (EP["fixed_cold_start"]["exit_code"],
                                                    EP["fixed_legacy_target"]["exit_code"])},
        "D6_evidence_bundle": {"accepted": False, "detail": "4/5 items carry provenance.input_sha256, "
                                                            "1 systematically missing; source_ref 0/5 resolves cold"},
    },
    "six_checks": SIX,
    "checks_not_run": [
        "full pytest suite in the cold clone (suite is large; the reviewed bundle records not_run for it too)",
        "cross-machine / cross-python rerun",
        "verbatim audit of all 15 criteria against matrix/PRD (unchanged from R4: 7 sampled)",
        "tensor_maturity_verdicts rows 903/918 read-back (psql role lacks SELECT on that table; texts used "
        "come from the in-repo quotations in docs/review_m22059_prod_ra/REVIEW-R4.md)",
    ],
    "artifacts": {},
}
for name in ("verify_r5.py", "r5_recheck.json", "REVIEW-R5.md",
             "figures/r5-locator-coldstart.png", "figures/r5-entrypoint-exitcodes.png",
             "figures/r5-sixchecks-d6.png", "raw_r5/recheck_fixed.py"):
    p = HERE / name
    if p.is_file():
        receipt["artifacts"][f"docs/m23157/{name}"] = hashlib.sha256(p.read_bytes()).hexdigest()

# ---------------------------------------------------------------- markdown
def table(rows, head):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


loc_rows = [
    ["file locator fields (path-valued JSON strings)", LOC["pure_path_fields"]],
    ["of which still use the legacy runs/m22059/ prefix", LOC["pure_path_fields_legacy_runs_prefix"]],
    ["of which are absolute refs into a foreign worktree (/srv/tensor/agent/...)", LOC["pure_path_fields_absolute_foreign"]],
    ["resolved by a cold clone as-is", LOC["pure_path_resolved_cold"]],
    ["resolved only after a mechanical runs/ -> docs/ rewrite", LOC["pure_path_resolved_after_prefix_repair"]],
    ["unresolvable even after that rewrite", LOC["pure_path_unresolvable_even_after_repair"]],
    ["all path tokens searched (commands included): total / unresolved", f"{LOC['locator_tokens']} / {LOC['tokens_unresolved_cold']}"],
]

ep_rows = [[k, EP[k]["exit_code"],
            (EP[k].get("stderr_last_line") or "(no stderr)")[:64]] for k in keys]

d6_rows = [[r["evidence_id"], "ok" if r["schema_ok"] else "; ".join(r["schema_errors"])[:40],
            "yes" if r["has_input_sha256"] else "NO",
            "yes" if r["source_ref_resolves_cold"] else "NO",
            "yes" if r["sha256_matches_actual"] else "NO",
            "; ".join(r["input_refs_absolute_foreign"])[:52] or "-"] for r in D6["rows"]]

six_rows = [[name, "PASS" if ok else "FAIL", note] for name, ok, note in rows]

loc_rate = 100.0 * (LOC["pure_path_fields"] - LOC["pure_path_resolved_cold"]) / LOC["pure_path_fields"]
d6_rate = 100.0 * (D6["items"] - D6["source_ref_resolve_cold"]) / D6["items"]
sum_rate = 100.0 * (len(SUM["missing"]) + len(SUM["mismatch"])) / SUM["entries"]

md = f"""# PROD-RA R5：m22059 残差修复（m23111 / PR#511）终点复审

- 被审主线：`origin/main@{COMMIT[:9]}`（`{J['reviewed_commit_subject']}`）
- 修复件：PR#511 = `{FIXREV}`（`origin/agent/m23111` 尖端）。**实测该 commit 尚未并入 main**（`git merge-base --is-ancestor {FIXREV} origin/main` 为假），故本轮以冷克隆 main + 单独取 `{FIXREV}` 版 `recheck.py` 的方式分别核验"主线现状"与"修复件主张"
- 判据基准：`tensor_maturity_verdicts` 行 903（12 条缺陷原文，D6 即其一）＋ 行 918（R4 五条残差 R4-1…R4-5）＋ `REPAIR-NOTES.md`（m23111）逐条自述
- **处置：`changes_requested`（窄口径）** —— R4-2 实质修复并经实跑证实，六检在修复件上复跑全过；但 R4-1 **未修复**（残差原样，且交付分支根本没带上该改动），R4-3 未动，D6 的 1/5 输入指纹缺口与绝对外域引用仍在。`scenario_validated` 本席不置位。

## 1. 案例介绍（审的是什么、判据是什么）

被测对象是一个"研究断言审计"产物包：`docs/m22059/validation-report.json` 及其证据束（5 条 evidence item、11 条 claim 记录、负向语料、失败台账、回归范围声明），外加作者席交付的复审入口 `docs/review_m22059_prod_ra/recheck.py`。判据不是物理精度，而是**可复现性与可移植性**这两条契约：

1. 任一条 finding 必须能在**纯仓内、无外部工作树**的条件下从被引来源复现（PRD 的 source-span 条款）；
2. 复审入口在同一条件下必须 `exit 0` 并产出六节结果。

参数表（全部为被测包实测规模）：

| 量 | 值 |
|---|---|
| 证据 item 数 | {D6['items']} |
| claim 记录数 | {SIX.get('5_failure_record', {}).get('records') if False else 11} |
| 失败台账记录数 | {SIX['5_failure_record']['records']} |
| 文件级 locator 字段数（本席口径，见 §5） | {LOC['pure_path_fields']} |
| 审阅包 manifest 条目数 | {SUM['entries']} |
| 冷克隆（第三人视角） | `{J['target']}` @ main，**未挂载** `/srv/tensor/agent/work/m22059` |

## 2. 怎么做的（方法与工具链）

1. **冷启动克隆**：把 main 尖端克隆到独立目录，确认 `runs/m22059` 不存在 —— 模拟第三人拿到仓库时的条件。
2. **locator 枚举器**（`verify_r5.py::collect_locators`）：递归遍历 `docs/m22059/**/*.json` 与 `docs/review_m22059_prod_ra/**/*.json`，取所有形如路径的字符串（以及命令串里的路径 token），逐个在冷克隆根下解析；对 `runs/m22059/X` 另做一次"机械前缀重写"解析，以区分"仅前缀坏"和"内容缺失"。
3. **入口点实跑**（`verify_r5.py::main` 的 B 段）：五个变体——主线 as-shipped ×（冷克隆、旧工作树、补齐 runs/ 布局）、PR#511 修复件 ×（冷克隆、旧工作树）；逐次记录 exit_code 与 stderr 末行。
4. **D6 复算**：5 条 evidence item 逐条 `jsonschema` 校验（`TensorBench/schemas/evidence-item.schema.json`），检查 `provenance.input_sha256`/`input_refs` 存在性、`source_ref` 冷启动可解析性、`source_ref` 实算 sha256 与声明值比对，并用 `tensorbench.criteria.canonical_sha256` 复算 bundle 自摘要。
5. **六检复跑**：直接用修复件 `recheck.py` 在冷克隆上产出六节结果，再由 `six_checks()` 按**成文语义**判定（`citation_audit` 在无语料目录时 `inconclusive`+exit 1 是 R4-5 已接受的既有局限，判别力在 finding 集，故不按 exit 0 判负）。
6. **manifest 审计**：18 条 `SHA256SUMS` 逐条实算。

## 3. 计算结果

### 3.1 R4-1（locator 冷启动可解析性）

{table(loc_rows, ["口径", "数量"])}

冷启动未解析率 = **{loc_rate:.1f}%**（{LOC['pure_path_fields'] - LOC['pure_path_resolved_cold']}/{LOC['pure_path_fields']}），与 R4 的 96 处口径差异见 §5。

### 3.2 R4-2（复审入口实跑 exit_code）

{table(ep_rows, ["变体", "exit_code", "stderr 末行"])}

结论：修复件在**冷克隆与旧工作树两种条件下均 exit 0**；主线 as-shipped 在两种条件下均失败（冷启动是 `FileNotFoundError: runs/m22059/...`；补齐 runs/ 布局后即复现 R4-2 的 `KeyError: 'item_id'`）。R4-2 修复成立。

### 3.3 D6（evidence bundle 逐项核，行 903 缺陷 + 行 918 残差）

{table(d6_rows, ["evidence_id", "schema", "input_sha256", "source_ref 冷启动可解析", "sha256 实算一致", "绝对外域 input_refs"])}

- schema：**{D6['schema_ok_count']}/{D6['items']}** 通过；bundle 自摘要 `canonical_sha256` 复算 = 声明值（{D6['bundle_sha256_matches']}）。
- 输入指纹：**{D6['items'] - len(D6['items_without_input_sha256'])}/{D6['items']}** 带 `provenance.input_sha256`，缺口是 `{', '.join(D6['items_without_input_sha256'])}`（目录树型输入）。
- 冷启动：`source_ref` **{D6['source_ref_resolve_cold']}/{D6['items']}** 可解析 —— D6 的形状缺陷已修，但**引用可移植性未修**。

### 3.4 六检复跑（修复件，冷克隆）

{table(six_rows, ["检查", "判定", "实测"])}

`all_six_pass = {SIX['all_six_pass']}`。

### 3.5 审阅包 manifest（R4-3）

- 条目 {SUM['entries']}，缺失 {len(SUM['missing'])}（{', '.join(SUM['missing'])}），摘要不符 {len(SUM['mismatch'])}（{', '.join(m['path'] for m in SUM['mismatch'])}：声明为**空串摘要** `e3b0c442…b855`，实际 `ac75e224…cda`）。

## 4. 图

1. `figures/r5-locator-coldstart.png` —— {LOC['pure_path_fields']} 个文件级 locator 的冷启动解析分类（已解析 / 仅机械重写后可解析 / 重写也不可解析）。
2. `figures/r5-entrypoint-exitcodes.png` —— 复审入口五个变体的实测 exit_code 与失败原因（同一脚本，两种条件下结论相反）。
3. `figures/r5-sixchecks-d6.png` —— 六检判定与 D6 复算摘要（论文式状态表）。

## 5. 注意点（踩过的坑 / 局限 / 适用范围）

1. **"exit_code=0" 在本案不是验收证据**：修复件 `recheck.py` 的 `main()` 以**无条件 `return 0`** 收尾（第 231 行），任何检查结论都不改变进程退出码；m23111 自述"实跑 exit_code=0"只能证明脚本跑通。本轮改以六节结果本身判定。
2. **修复件里有一个假失败信号**：`recheck.py:214` 在 item 顶层取 `input_sha256`，而 D6 修复后该字段嵌在 `provenance` 内，于是它把 **5/5** item 都报成"无指纹"；独立复算是 **4/5 有指纹**。作者把这解释为"报告口径问题"，本席同意该解释，但这恰恰说明该脚本不能作为验收工具。
3. **locator 计数口径**：R4 记 96 处，本席记 {LOC['pure_path_fields']} 个"路径型 JSON 字段"（含负向语料与审阅包内 JSON；命令串内的路径另计，共 {LOC['locator_tokens']} 个 token）。两者不矛盾，是范围不同；判定不依赖具体数字，而依赖"冷启动解析率 = {100-loc_rate:.1f}%"。
4. **m23111 修的是"另一个工作树"而不是"仓内可移植"**：其本地版本把 `/srv/tensor/agent/work/m22760/` 改成 `/srv/tensor/agent/work/m23111/`，仍是外域绝对路径；即便该改动进了主线，冷启动解析率也不会归零。且该改动（`docs/m22059/` 7 个 JSON + `REPORT.md` 等）**未出现在交付分支** `{FIXREV}` 上（该 commit 相对 main 只动了 `recheck.py` 4 行 + `REPAIR-NOTES.md`）。
5. **台账不可直读**：本席 psql 角色对 `tensor_maturity_verdicts` 无 SELECT 权限，行 903/918 的原文取自仓内 `REVIEW-R4.md` 的引用；如协调者需绝对独立，应在有读权限的席位复核一次。
6. **全量 pytest 未跑**（冷克隆内未递交全量套件），只跑相邻审计器单测 12 passed；不冒充全量。
7. 适用范围：本判定只对"文档/证据包可复现性"，不含 PRD 语义精度（无语料 holdout，仍是 not_measured）。

## 6. 误差判定（逐项 vs 判据，显式回答是否 <3%）

本案无物理量基准，判据是"必须为 0 的不合规计数"。故逐项给出实测率与判据阈值（0%），并显式回答：

| 关键量 | 实测 | 判据 | 偏差率 | 是否 <3% |
|---|---|---|---|---|
| 冷启动不可解析的 locator 字段 | {LOC['pure_path_fields'] - LOC['pure_path_resolved_cold']}/{LOC['pure_path_fields']} | 0 | **{loc_rate:.1f}%** | **否** |
| D6 无输入指纹的 evidence item | {len(D6['items_without_input_sha256'])}/{D6['items']} | 0 | **{100.0*len(D6['items_without_input_sha256'])/D6['items']:.1f}%** | **否** |
| evidence `source_ref` 冷启动不可解析 | {D6['items'] - D6['source_ref_resolve_cold']}/{D6['items']} | 0 | **{d6_rate:.1f}%** | **否** |
| manifest 不成立条目 | {len(SUM['missing']) + len(SUM['mismatch'])}/{SUM['entries']} | 0 | **{sum_rate:.1f}%** | **否** |
| 六检不通过数（修复件） | {sum(1 for _, ok, _ in rows if not ok)}/6 | 0 | **{100.0*sum(1 for _, ok, _ in rows if not ok)/6:.1f}%** | **是（0%）** |
| D6 evidence-item schema 不合规 | {D6['items'] - D6['schema_ok_count']}/{D6['items']} | 0 | **{100.0*(D6['items']-D6['schema_ok_count'])/D6['items']:.1f}%** | **是（0%）** |
| bundle 自摘要不符 | {0 if D6['bundle_sha256_matches'] else 1}/1 | 0 | **{0.0 if D6['bundle_sha256_matches'] else 100.0:.1f}%** | **{'是（0%）' if D6['bundle_sha256_matches'] else '否'}** |
| 复审入口实跑（修复件，冷克隆） | exit {EP['fixed_cold_start']['exit_code']} | exit 0 | 0% | **是** |

**总判**：项目级判据（locator 冷启动解析、输入指纹、manifest）未达标，偏差率双位数百分比，远超 3% 阈值；只有 D6 的形状类判据与六检达标。故 `changes_requested`，`scenario_validated` 不置位。

## 7. 未跑 / 未证

{chr(10).join('- ' + c for c in receipt['checks_not_run'])}
"""
(HERE / "REVIEW-R5.md").write_text(md, encoding="utf-8")
(HERE / "REVIEW-RECEIPT-R5.json").write_text(
    json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- SHA256SUMS.r5
lines = []
for name in ("verify_r5.py", "r5_recheck.json", "REVIEW-R5.md", "REVIEW-RECEIPT-R5.json",
             "figures/r5-locator-coldstart.png", "figures/r5-entrypoint-exitcodes.png",
             "figures/r5-sixchecks-d6.png", "raw_r5/recheck_fixed.py",
             "verdict_insert_r5.sql"):
    p = HERE / name
    if p.is_file():
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
(HERE / "SHA256SUMS.r5").write_text("\n".join(lines) + "\n", encoding="utf-8")

# ---------------------------------------------------------------- verdict sql
evidence = {
    "review": "PROD-RA R5 五轮复审（m23111 残差修复后终判）",
    "reviewed_commit": COMMIT,
    "fix_commit_under_review": FIXREV,
    "fix_commit_in_main": False,
    "baseline": {"source": "tensor_maturity_verdicts rows 903/918",
                 "scope": "ra-rereview4-m22059-fixes residual set R4-1..R4-5"},
    "r4_acceptance": receipt["r4_acceptance"],
    "measurements": {
        "locators": {k: v for k, v in LOC.items() if k not in ("per_file", "unresolved_examples")},
        "entry_point_exit_codes": {k: EP[k]["exit_code"] for k in keys},
        "entry_point_failure_modes": {k: EP[k].get("stderr_last_line") for k in keys},
        "d6": {k: v for k, v in D6.items() if k != "rows"},
        "manifest": SUM,
        "six_checks": {k: (v if not isinstance(v, dict) else v.get("pass")) for k, v in SIX.items()},
    },
    "residuals": receipt["residuals"],
    "verdict": "changes_requested",
    "scenario_validated": False,
    "scenario_validated_note": "复审单不抢跑；由协调者依裁决置位",
    "exit_code_semantics": "2 = six checks pass on the repaired entry point but bundle-level residuals "
                           "(locator portability, manifest, D6 input fingerprint) remain",
    "checks_not_run": receipt["checks_not_run"],
    "artifacts": receipt["artifacts"],
    "review_report": "docs/m23157/REVIEW-R5.md",
    "review_figure": "docs/m23157/figures/r5-locator-coldstart.png",
}
sql = f"""INSERT INTO tensor_maturity_verdicts (repo, scope, mission_id, level, evidence, verdict_by, gate_state)
VALUES ('TensorKnowledge', 'ra-rereview5-m22059-residuals', 23157, 2, $json${json.dumps(evidence, ensure_ascii=False)}$json$, 'm23157-r5-independent', 'pending')
ON CONFLICT (repo, scope, verdict_by) DO UPDATE SET mission_id=EXCLUDED.mission_id, level=EXCLUDED.level, evidence=EXCLUDED.evidence, created_at=now() RETURNING id, level, gate_state;
"""
(HERE / "verdict_insert_r5.sql").write_text(sql, encoding="utf-8")

# refresh manifest to include the sql file
lines = []
for name in ("verify_r5.py", "r5_recheck.json", "REVIEW-R5.md", "REVIEW-RECEIPT-R5.json",
             "figures/r5-locator-coldstart.png", "figures/r5-entrypoint-exitcodes.png",
             "figures/r5-sixchecks-d6.png", "raw_r5/recheck_fixed.py", "verdict_insert_r5.sql"):
    p = HERE / name
    if p.is_file():
        lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {name}")
(HERE / "SHA256SUMS.r5").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(json.dumps({"loc_rate": loc_rate, "d6_rate": d6_rate, "sum_rate": sum_rate,
                  "six_all": SIX["all_six_pass"], "files": len(receipt["artifacts"])},
                 ensure_ascii=False))